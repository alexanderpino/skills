# Asset Pipeline and Cooker

Asset pipelines are the silent bottleneck of AAA development. A pipeline that takes 40 minutes to iterate on a texture kills art; one that takes 5 seconds unlocks the team. Optimize for iteration speed first, throughput second, binary size third.

## Table of Contents
- [Pipeline Architecture](#pipeline-architecture)
- [Texture Compression](#texture-compression)
- [Mesh Processing](#mesh-processing)
- [Shader Compilation Pipeline](#shader-compilation-pipeline)
- [GPU Decompression](#gpu-decompression)
- [Audio Asset Processing](#audio-asset-processing)
- [Hot-Reload Pipeline](#hot-reload-pipeline)
- [Build Farm](#build-farm)
- [Content Validation](#content-validation)
- [See also](#see-also)

---

## Pipeline Architecture

Three stages, three currencies: **source** (human-authored, versioned in Perforce/Git-LFS), **intermediate** (normalized, platform-agnostic), **cooked** (platform-native binary, mmap-ready).

```
DCC (Maya/Blender/Substance/Houdini)
   └── .ma/.blend/.spp/.hip      [source, big, slow, human]
        → Importer (per-format)
           └── .asset (intermediate JSON+binary blob, normalized)
                → Cooker (platform-specific)
                   └── .pak entry (PS5/XSX/PC/Switch/Mobile cooked blob)
                        → DDC (Derived Data Cache, content-addressed)
```

**Content-addressed storage is non-negotiable.** The key for every cooked artifact is `BLAKE3(source_bytes || importer_version || cooker_version || platform_id || options_hash)`. Two workstations cooking the same asset produce the same hash and can share cache entries over S3/Azure Blob/local NAS. Without this, the build farm has nothing to distribute.

**Dependency graph is a DAG.** Materials reference textures, meshes reference skeletons, levels reference everything. Build the graph at import time, validate for cycles (cycles = design bug), topologically sort, cook in parallel within each topological layer. The cooker's inner loop looks like:

```cpp
struct CookJob {
    AssetId           id;
    std::vector<AssetId> dependencies;  // must be cooked first
    Hash              input_hash;        // BLAKE3 of inputs
    TargetPlatform    platform;
};

std::expected<CookedBlob, CookError>
cook(const CookJob& job, const DDC& cache) noexcept {
    if (auto hit = cache.lookup(job.input_hash, job.platform)) {
        return *hit;                      // cache hit = 0 work
    }
    auto result = dispatch_importer(job); // platform-specific cook
    if (!result) return std::unexpected(result.error());
    cache.insert(job.input_hash, job.platform, *result);
    return result;
}
```

Notice `[[nodiscard]] std::expected` — exceptions are off, and the caller must handle failure.

---

## Texture Compression

Block compression is mandatory. Uncompressed textures waste bandwidth and VRAM; they only exist for UI atlases and HDR LUTs.

| Format        | Bits/px | Target        | Notes                                              |
|---------------|---------|---------------|----------------------------------------------------|
| BC1           | 4       | Desktop RGB   | Opaque diffuse, legacy                             |
| BC3           | 8       | Desktop RGBA  | Mostly deprecated; use BC7                         |
| BC4/BC5       | 4/8     | Desktop       | Single/dual channel (normal maps, masks)           |
| BC6H          | 8       | Desktop HDR   | Signed/unsigned float cubemaps, skyboxes           |
| **BC7**       | 8       | Desktop RGBA  | Default for high-quality albedo, packed ORM        |
| **ASTC 4x4**  | 8       | Mobile/Switch | High quality                                       |
| ASTC 6x6      | 3.56    | Mobile        | Good ratio, acceptable artifacts                   |
| ASTC 8x8      | 2       | Mobile        | UI, large coverage                                 |
| ASTC 12x12    | 0.89    | Mobile        | Background / lightmap where quality allows        |
| ETC2          | 4/8     | Legacy Android| GLES 3.0 fallback only                             |
| Basis Univ.   | ~variable| Transcode    | Supercompressed source, transcode to BC/ASTC/ETC   |

**Basis Universal** (or KTX2+UASTC) is the modern answer to "one cooked asset, many platforms." Cook once to Basis/UASTC, transcode on load to the native block format. Loses quality vs. direct BC7, but saves 3-4x disk space.

**Mip chain generation:** always generate on cook. For normal maps, re-normalize per mip; for albedo in gamma space, convert to linear, downsample, convert back. For alpha coverage masks, use the Ignacio Castaño coverage-preserving downsample — otherwise alpha tests shrink as LOD falls.

**Virtual texturing:** tile size 128x128 (or 256x256 with 4px border for trilinear), cook tiles into a streaming-optimized layout, index via page table. The tile is the unit of I/O. UE's SVT and Granite are the reference designs.

---

## Mesh Processing

Meshes have four products off a single source: render LODs, collision proxies, meshlet clusters, and nav-mesh input. Cook all four in one pass.

**Meshlet generation:** use [meshoptimizer](https://github.com/zeux/meshoptimizer). Target 64-124 triangles/cluster (matches Mesh Shader / Nanite wave sizes). Each cluster carries its own bounding sphere + normal cone for cluster-level culling. Cluster data layout:

```cpp
struct Meshlet {
    uint32_t vertex_offset;
    uint32_t triangle_offset;
    uint8_t  vertex_count;
    uint8_t  triangle_count;  // <= 124
    float    bounds_center[3];
    float    bounds_radius;
    int8_t   cone_axis[3];    // quantized
    int8_t   cone_cutoff;
};
```

**LOD chain:** quadric error metric simplification (Garland-Heckbert), preserve UV seams and hard edges. Generate 4-6 LODs with ~50% tri reduction per step. Verify each LOD against reference with screen-space error metric — if LOD3 looks worse than 4 pixels different at screen coverage 32x32, something's wrong.

**Nanite-style continuous LOD:** cluster DAG where each parent is the simplification of its children, with consistent boundary edges (critical — cracks in geometry are the #1 Nanite porting bug). Runtime selects cut through the DAG based on screen-space error.

**Vertex cache optimization:** Tom Forsyth's linear-time algorithm (implemented in meshoptimizer as `meshopt_optimizeVertexCache`). Then `meshopt_optimizeOverdraw` (front-to-back within material), then `meshopt_optimizeVertexFetch` (reorder vertex buffer to match index order). Order matters.

**Vertex quantization:** positions to 16-bit with per-mesh scale/bias, normals to octahedral 2x16-bit, UVs to 16-bit, tangents to quaternion 4x8-bit. 2-3x memory savings with imperceptible quality loss.

---

## Shader Compilation Pipeline

**HLSL is the source of truth.** Write shaders once in HLSL (SM 6.6+), target every platform by cross-compilation. Slang is a viable successor but tooling is still maturing; for 2026 AAA, HLSL + DXC is the safe pick.

```
file.hlsl
  └── DXC (compile) ──┬── .dxil     (Direct3D 12 / GDK)
                      └── .spv       (Vulkan / PS5 / Switch via translation)
                             └── SPIRV-Cross ──┬── .msl  (Metal, macOS/iOS)
                                               └── .glsl (GLES 3.x legacy)
```

**Permutation management is the hardest part.** A modern PBR shader easily has 2^20 permutations (skinned/static, decal/no, shadow-receiver/caster, 4-layer blend variants...). Two strategies:

1. **Static permutations** — compile every combination, store in PSO cache. Fast runtime, explosion of cook time and disk.
2. **Dynamic branches** — `[branch]` / uniform-control-flow, single shader, predicated. Slower GPU, fast cook.

Rule of thumb: permute on features that change VGPR pressure or register allocation (shadow map count, layer count). Branch on toggles that are uniform per-draw (debug visualizers, feature flags).

**PSO caching:** serialize compiled pipeline state objects to disk. DX12: `ID3D12PipelineLibrary`. Vulkan: `VK_EXT_pipeline_cache`. On ship, pre-warm by replaying a recorded PSO list on first boot to avoid shader-stutter. This is the difference between "smooth" and "TLOU-PC at launch."

---

## GPU Decompression

**DirectStorage 1.2 + GDeflate** on PC/Xbox delivers NVMe → VRAM with decompression on the GPU. Throughput targets: 5-14 GB/s effective. The CPU is out of the loop.

Implementation gates:
- Asset must be GDeflate-compressed at cook time (RTX IO tooling or `gdeflate_compress`).
- Read via `IDStorageFactory::OpenFile` → `EnqueueRequest` → GPU decompression → upload to committed resource.
- Memory layout of cooked asset must match the layout expected on GPU (no CPU-side swizzle).

PS5 has an equivalent (Kraken + hardware decompressor on I/O complex). Switch 2 (NVIDIA silicon, NVN2) exposes GPU-side decompression; on the original Switch (no HW decompressor) fall back to zstd on CPU with a dedicated streaming thread. (The skill's baseline is Switch 2 — see `CROSS_PLATFORM_AND_CONSOLE.md`.)

**Compute decompression for BC textures** — when DirectStorage isn't available, upload the BC blocks as `ByteAddressBuffer`, decompress to `RWTexture2D` in a compute pass. Costs GPU cycles but saves disk bandwidth.

**mmap I/O for streaming:** `CreateFileMapping`/`mmap` the pak file, let the OS page in on demand. Works for desktop/mobile where VA space is plentiful. Don't try on consoles — no swap, VA space is precious.

---

## Audio Asset Processing

Audio is cheap to store, expensive to misconfigure. Loudness discipline matters more than bitrate.

| Format    | Use                                                         |
|-----------|-------------------------------------------------------------|
| WAV PCM   | Short UI stings, <1s; zero decode cost                      |
| ADPCM     | Legacy, fixed 4:1 ratio, cheap decode                       |
| XMA2      | Xbox native, hardware-decoded on older gens                 |
| Vorbis    | Music and long VO, desktop-friendly                         |
| **Opus**  | Default for VO and ambience; best quality/bitrate in 2026   |
| AT9 / MP3 | Platform-specific legacy                                    |

**LUFS normalization during cook** — measure integrated loudness (EBU R128 / ITU-R BS.1770 algorithm) and store it in metadata so runtime can apply gain without re-analysis. Target **games, not broadcast**: roughly **-16 to -18 LUFS** for the interactive mix is typical (and follow each platform's loudness cert guidance, e.g. ASWG-R001-style targets); **-23 LUFS is the EBU broadcast target, not a game default** — don't ship it for gameplay. Mixing engineers set relative levels, the cooker handles absolute.

**Ambisonics:** B-format (4-channel W/X/Y/Z) at cook, decode to HRTF / speaker array at runtime. Higher-order ambisonics (HOA3 = 16ch) for VR/critical scenes only — 4x the memory.

**Streaming format:** 4KB header (sample rate, channel map, loop points, cue markers) + chunked body (64-128KB chunks, each independently decodable). Decoder reads header once, mmap chunks. Music tracks over 10 MB must always stream; small SFX stay resident.

---

## Hot-Reload Pipeline

Iteration speed defines engine quality. Target: save texture in Photoshop → see change in running game in < 2 seconds.

**File watcher per platform:**
- Windows: `ReadDirectoryChangesW` (async, per-directory)
- Linux: `inotify` (per-file, but IN_MOVED_TO covers atomic writes)
- macOS: `FSEvents` (per-directory, coalesced)

Normalize events: Photoshop saves as `temp` → rename to `final`. You want a single "file changed" callback, debounced 100ms.

**Incremental re-cook:** hash diff triggers cook-of-one. The cooker emits the new blob and a hot-reload manifest:

```json
{
  "asset_guid": "7a2c-...",
  "old_hash":   "blake3:abc...",
  "new_hash":   "blake3:def...",
  "type":       "Texture2D",
  "payload":    "DDC://def..."
}
```

**Handle preservation:** every asset has a stable GUID assigned at import; references resolve GUID → current data pointer via an indirection table. On reload, swap the pointer — live `Handle<Texture2D>` instances see the new data automatically.

**Editor-runtime sync:** IPC via named shared memory (Windows: `CreateFileMapping`; POSIX: `shm_open`). Editor writes manifest to a ring buffer, runtime polls once per frame during the editor idle callback. Mutation must happen at a safe point (end of frame, before next tick).

---

## Build Farm

A single workstation cooks a AAA title in 40-80 hours. A build farm does it in 20-40 minutes. The farm is not optional.

**Distributed cooking:**
- Coordinator holds the DAG and DDC index.
- Workers pull cook jobs, write results back to DDC.
- Jobs are idempotent (content-addressed inputs = content-addressed outputs).
- Scale with cloud (AWS Batch, Azure Batch) or on-prem (100-500 node pools at major studios).

**C++ distributed compilation:**
- **FASTBuild** — open-source, excellent for engine-sized codebases, best pricing.
- **IncrediBuild** — commercial, mature, integrates with MSBuild/Visual Studio.
- **sccache** — content-addressed compiler cache, pairs with either.
- **distcc** — only for GCC/Clang, weaker on headers.

**CI/CD:** Jenkins/TeamCity for legacy shops, Buildkite/GitHub Actions for modern. Pipeline = lint → unit tests → package cook → runtime smoke → perf regression → artifact upload. Gate merge on green.

**Artifact caching:** content-addressable by input hash. Two developers triggering the same cook share the cache. Without this the farm's effective utilization is ~20%; with it, ~90%.

---

## Content Validation

Asset lint is cheap insurance. Run on every import; block commit on error.

**Static lint rules** (configurable per-project):
- Texture dimensions are power-of-2 (unless tagged `UI`).
- Texture max dimension <= 4096 (unless tagged `LargeVT`).
- Mesh triangle count within budget for its category (character ≤ 80k, prop ≤ 15k, FX ≤ 5k).
- Material slot count ≤ 8 per mesh (GPU binding table cost).
- Animation clips <= 60s (stream longer ones).
- Audio sample rate ∈ {22050, 44100, 48000}.
- No textures named `untitled`, `test`, `new_material_1`.

**Automated regression:** nightly cook of the full project. Fail if cook time regresses >10%, output size regresses >5%, or any asset fails to cook.

**Visual diff:** render a canonical scene with the new and old asset, compare screenshots with SSIM or ΔE2000. Surface deltas > 1% to the art director. Budget for this: one GPU per platform, 5 minutes per commit.

```python
# Simplified nightly diff harness
from pipeline import cook_project, render_canonical, compare_ssim

def validate(commit_hash: str) -> bool:
    baseline = load_golden("main")
    current  = cook_project(commit_hash) \
                 .and_then(render_canonical)
    if not current:
        return fail(current.error)
    score = compare_ssim(baseline, current.value)
    return score >= 0.995  # 0.5% tolerance
```

---

## See also

- `EDITOR_AND_TOOLING.md` — hot-reload integration with the editor, Python pipeline scripting, content validation UI.
- `TESTING_ERROR_HANDLING_AND_BUILD.md` — CI/CD gating, `std::expected` usage in cookers, visual regression pipeline.
- `CPP23_26_AND_MODERN_PATTERNS.md` — `std::expected<T,E>` contract, Handle<Tag> pattern used in hot-reload indirection.
