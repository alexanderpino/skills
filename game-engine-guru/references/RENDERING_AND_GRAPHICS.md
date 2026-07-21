# Rendering and Graphics Architecture

Reference document for AAA-grade realtime rendering. Audience: senior graphics engineers. Assumes familiarity with GPU hardware, modern graphics APIs (DX12/Vulkan/Metal), and shader authoring in HLSL/SPIR-V.

## Table of Contents

- Frame Graph & GPU-Driven (see `FRAME_GRAPH_AND_GPU_DRIVEN.md`)
- Deferred vs Forward+ Architecture
- Depth & Reverse-Z
- CPU↔GPU Shared Layout
- PBR Material Model
- Global Illumination Hierarchy
- Shadow Pipeline
- Lighting Architecture
- Virtual Geometry
- Post-Processing Chain
- Volumetric Rendering
- Special Surfaces
- GPU Particles
- Neural Rendering
- Tone Mapping and Color

> **Scope note.** The per-frame *pass scheduling* layer underneath everything here — render/frame graph, transient aliasing, automatic barriers, async compute, GPU-driven culling, two-phase occlusion, Work Graphs — lives in **`FRAME_GRAPH_AND_GPU_DRIVEN.md`**. This file is the catalog of *what each pass computes*; load that file for *where and when* the GPU runs them.

---

## Deferred vs Forward+ vs Adaptive Architecture

High-end renderers increasingly combine visibility buffers, deferred or adaptive material storage, and Clustered Forward+, but conventional deferred and forward pipelines remain valid. Select per pass and platform from measured geometry, material, bandwidth, MSAA, and tooling constraints.

**Adaptive GBuffer (Variable Bitstream):**
Adaptive material storage, including UE Substrate's production path, can encode variable closure payloads instead of a single fixed G-buffer layout.
- **Dynamic Allocation:** A simple single-layer material (Slab) uses minimal bits. Complex layered closures (e.g., clearcoat over metallic with fuzz) expand the bitstream dynamically per-pixel.
- **Tile Classification:** A compute pass classifies tiles by material complexity, allowing the deferred lighting pass to optimize branching and unpack only the required data.
- **Visibility Buffer Resolve:** For Nanite-style dense geometry, the visibility buffer (R32 cluster ID | triangle ID) is resolved into the Adaptive GBuffer in a compute pass, ensuring zero overdraw during complex material evaluation.

**Legacy Fallback (Blendable/Compact G-buffer):**
For low-end hardware or Switch 2, a compact legacy G-buffer (3x RT8, ~24 bpp effective) is used as a fallback, trading complex layered closures for static performance predictability.

**Clustered Forward+ froxel grid:** 16×16-pixel screen tiles × 32 depth slices, logarithmic Z distribution. The grid dimensions are `ceil(W/16) × ceil(H/16) × 32`, so the froxel count scales with resolution — at 1920×1080 that is 120×68×32 ≈ 261k clusters, **not** a fixed 8192 (16 and 16 are the tile *size* in pixels, not the tile *count*).

```cpp
// slice = log2(depth/near) / log2(far/near) * numSlices
float k = numSlices / std::log2(farZ / nearZ);
int   s = int(std::log2(depth / nearZ) * k);
uint32_t slice = uint32_t(std::clamp(s, 0, int(numSlices) - 1)); // clamp: depth < near or > far
```

Light lists packed as uint32 bitmasks — 256 lights per view = 8× uint32 (32 B) per cluster. At 1080p that is ~261k clusters × 32 B ≈ **8 MB** for the light index grid (a fixed 8192-cluster grid would be only 256 KB, but that undercounts a real screen by ~32×). Still cheap relative to the frame's other buffers.

**When to pick what:**
- Visibility buffer + material resolve: opaque geometry, >100k instances, Nanite-style
- Deferred shading: moderate geometry (<50k draws), many lights, simple materials
- Forward+: translucents, hair, skin, wet surfaces, anything needing MSAA, VR (MSAA is mandatory)

On mobile TBDR (Apple Silicon, Adreno, Mali) deferred is a trap — the tile cache pays dearly for the wide G-buffer read. Use forward+ with on-chip depth-prepass resolve.

---

## Depth & Reverse-Z

**Reverse-Z is the default, not an option.** Map the near plane to depth **1.0** and the far plane to **0.0**. This is mandatory for any modern renderer and effectively free; shipping a standard near=0/far=1 depth buffer in 2026 is a bug, not a choice.

**Why it works.** A perspective projection distributes post-projection depth hyperbolically (∝ 1/z) — values bunch up near the far plane. IEEE float32 distributes its precision the opposite way — most representable values cluster near 0. Put the far plane at 0 and the near plane at 1, and the two non-uniformities **cancel**, giving near-uniform *relative* precision across the entire view distance. Without reverse-Z you get catastrophic z-fighting in the distance; with it, distant z-fighting essentially disappears.

**Setup (all four steps, or it silently breaks):**
1. Build the projection to map near→1, far→0 (swap the near/far terms, or use the infinite-far reverse-Z form below).
2. **Clear depth to 0.0** (not 1.0).
3. Flip the depth test to `GREATER` / `GREATER_EQUAL` (was `LESS`/`LESS_EQUAL`).
4. Use a **floating-point depth format (`D32_FLOAT`)**. The entire precision win comes from float's exponent distribution — reverse-Z does **nothing** for `D24_UNORM`/integer depth, which is already uniform. (If you're stuck on D24 for bandwidth, reverse-Z is harmless but pointless.)

**Infinite far plane.** Reverse-Z lets you push the far plane to infinity at **zero precision cost** — the projection has a clean closed form and you never run out of distant precision. This is why open-world engines default to infinite-far reverse-Z; it removes far-plane clipping of distant geometry entirely.

**API notes.** D3D12/Vulkan/Metal NDC z is already `[0,1]`, the natural fit. Set viewport `minDepth/maxDepth` accordingly. Legacy OpenGL clip-space z is `[-1,1]` (wastes a bit and half the range) — call `glClipControl(GL_LOWER_LEFT, GL_ZERO_TO_ONE)` before relying on reverse-Z.

**Engine-wide ripple effects** — every depth consumer must adopt the reversed convention or it breaks subtly:
- **HZB / occlusion culling:** "closest" is now the **largest** depth, but a *conservative* occlusion HZB must store the **farthest** occluder so it never culls a visible object — and in reverse-Z the farthest surface is the **smallest** depth. So build the Hi-Z pyramid with **`min` reduction**, the mirror of standard-Z's `max` (see `FRAME_GRAPH_AND_GPU_DRIVEN.md` §Two-Phase Occlusion for build/test pseudocode). Getting the operator backwards either culls visible geometry or culls nothing — assert it in a unit test against a known-occluder scene.
- **Depth bias / slope-scaled bias:** signs flip relative to standard-Z.
- **Depth linearization:** the reconstruction changes form. **Finite-far reverse-Z:** `linearZ = near*far / (near + depth*(far - near))`. **Infinite-far reverse-Z** (`far → ∞`, the open-world default): it collapses to `linearZ = near / depth`. Note the standard-Z form `near*far / (far + depth*(near-far))` is *wrong* under reverse-Z — that mismatch is exactly the sign error to avoid. Centralize it in one shader include so every pass (SSAO, SSR, fog, decals, froxel-slice mapping) uses the same convention.
- **Anything reading the depth buffer** — SSAO/GTAO, SSR HiZ march, deferred decals, volumetric froxel depth slicing, particle soft-blend — must use the reversed comparison and linearization. A single pass left on standard-Z produces a class of "works near the camera, wrong in the distance" bugs.

---

## CPU↔GPU Shared Layout

Constant buffers, structured-buffer elements, and push/root constants are read by the CPU (which fills them) and the GPU (which consumes them). The two definitions must agree byte-for-byte, and a mismatch is a *silent* corruption — wrong matrices, garbage material params, no crash.

**Share, don't mirror.** Do not hand-maintain a C++ struct and an HLSL/GLSL struct in parallel. Author the layout **once** in a header compiled by both sides, with macros that alias the shader vector types (`float4`, `float4x4`, `uint`) to the engine math types in C++, leave them native in HLSL, and remap to `vec*`/`mat*` in GLSL. One source of truth → the sides cannot drift. Constants (descriptor slots, feature flags) and trivial helpers can be shared the same way. Scaffold: `assets/shader_interop_template.h`.

**Honor the packing rules or it desyncs across APIs:**
- **16-byte rows (HLSL cbuffer):** a field never straddles a 16-byte boundary. **Pad explicitly** — when a partial row isn't completed by a real field, add a *named* `float _padN;` rather than trusting the compiler. Padding should be visible in the source.
- **`float3`/`vec3` is the classic trap:** HLSL packs it as 12 B (next scalar fills the slot); GLSL **std140** rounds it to 16 B — they disagree. Avoid vec3 in shared blocks, or compile the GLSL side with `GL_EXT_scalar_block_layout` (`layout(scalar)`) to match HLSL/C++.
- **Never `bool`** in a shared block (HLSL cbuffer bool = 4 B, C++ bool = 1 B) — use `uint`. **Force one matrix majorness** everywhere (mismatched majorness transposes silently).
- **Vertex layouts share too, under different rules.** They are tightly packed (4-byte scalar alignment, no 16-byte rows), so they use *packed* (align-4) types — an `alignas(16)` engine `Vec4` would silently misalign a vertex struct. The packed struct is the source of truth for vertex *pulling* (`StructuredBuffer<Vertex>`); for the input-*assembler* path, derive the `D3D12_INPUT_ELEMENT_DESC` / `VkVertexInputAttributeDescription` offsets from `offsetof` so the IA layout can't drift either. Assert `alignof == 4` (not 16) to catch a SIMD type leaking in. (GLSL vertex SSBOs also need `layout(scalar)` — std140/std430 round vec3 to 16.)

**Assert the layout, including alignment.** On the C++ side, guard every shared struct with `static_assert` on **`alignof` (== 16), `sizeof` (a whole number of 16-byte rows), and key field `offsetof`s.** This turns a layout drift into a build failure instead of a rendering artifact. (The GLSL std140-vs-scalar choice has no compile-time guard — that one is enforced by discipline.)

---

## PBR Material Model & OpenPBR

> **Scope split — read this first.** This section covers PBR engine integration. The shading math itself is owned by the `physically-based-rendering` skill; read it before deriving, debugging, or implementing BSDF math.

Modern authoring increasingly favors modular BSDF closures. Use **OpenPBR 1.1** as an interchange vocabulary where it fits; do not assume its exact parameterization is the optimal runtime representation for every engine.

**Modular BSDFs (Substrate-style Slabs):**
Materials are authored and evaluated as a series of layered "Slabs" and "Operators" (blend, add, multiply). A single slab encompasses parameterized responses natively supporting **Mean Free Path (MFP)** for subsurface scattering, **F90 (glancing reflectivity)**, and procedural **Glints/Fuzz** without requiring secondary G-buffer passes.

```hlsl
// BSDF Evaluation is now driven by closure unpacking
FSubstrateClosure closure = UnpackAdaptiveGBuffer(pixelData);
float3 lighting = EvaluateSlab(closure.BaseSlab, L, V, N)
                + EvaluateSlab(closure.TopSlab, L, V, N);
```

**Energy Conservation & Multi-scattering:**
Energy conservation across complex layered slabs is handled intrinsically by the modular framework. For base slabs, multi-scatter compensation (Kulla-Conty/Fdez-Aguera split-sum LUTs) remains the baseline.

**OpenPBR Alignment:**
The engine's internal parameterization must align with OpenPBR to ensure 1:1 translation from authoring tools (Substance 3D, Blender 5.1). Specular-gloss is deprecated; the workflow is purely based on physical properties (Base Color, Roughness, Metallic, IOR, Transmission, Subsurface Weight).

---

## Global Illumination Hierarchy

No single GI solution wins. Tier by platform and content:

| Technique | Quality | Cost (ms) | Memory | Dynamic? | Platform Floor |
|-----------|---------|-----------|--------|----------|----------------|
| Lightmaps (baked) | High (static) | 0.1 | 50-500 MB | No | All |
| DDGI probes | Medium | 0.8 | 20-80 MB | Yes | PS5/XSX/PC |
| SDF GI (Lumen-SW) | High | 2-4 | 200 MB | Yes | PS5/XSX/PC |
| HW RT GI (Lumen-HW) | Very High | 3-6 | 100 MB | Yes | PS5/XSX/RTX |
| ReSTIR GI | Reference | 4-8 | 150 MB | Yes | RTX 3060+ |
| VXGI | Medium | 3-5 | 500 MB | Yes | Legacy |
| SSGI | Low | 0.5 | 0 | Yes | Fallback everywhere |

**Lumen-style hybrid:** software ray marching against mesh SDFs + global SDF (voxelized at 2 m / 40 cm / 5 cm cascades) as the cheap path, hardware RT BVH when available. Screen traces first for near contacts. Final gather at 1/16 rate with spatial+temporal reuse.

**DDGI:** 3D grid of probes, 8x8 irradiance octahedrons + 16x16 visibility (depth-squared Chebyshev). Probe relocation to avoid backfaces. 32x32x32 grid = 32k probes, 8 MB irradiance + 32 MB depth.

**ReSTIR DI/GI:** reservoir resampling — store 1 sample per pixel weighted by target PDF, reuse spatially (3x3 taps) and temporally (prev frame). Variance reduction equivalent to 32-64 samples/pixel for ~2 ms. Gold standard for direct lighting with thousands of lights; production-ready for GI as of 2024.

```cpp
struct Reservoir {
    uint32_t lightIdx;  // selected sample y
    float    wSum;      // running sum of RIS weights w_i = pHat(x_i) / p(x_i)
    float    W;         // unbiased contribution weight for the selected sample
    uint32_t M;         // candidate samples seen
};
// Stream insert (weighted reservoir sampling):
//   wSum += w; ++M; if (rand() < w / wSum) lightIdx = candidate;  // w/wSum == w/(oldSum+w)
// Finalize the contribution weight (it is NOT simply 1/pdf):
//   W = wSum / (M * pHat(lightIdx));   // == (1 / pHat) * (wSum / M)
```

Decision rule: if ray budget > 1 spp and BVH build fits in 2 ms/frame, use RT + ReSTIR. Otherwise SDF+DDGI. Never ship VXGI on new platforms — memory cost doesn't amortize.

---

## Shadow Pipeline

**Virtual Shadow Maps (UE5 model):** 16k x 16k virtual resolution, 128x128 physical pages, allocated on demand per-tile per-cascade. Only pages touching visible screen pixels rasterize. Page cache reuses pages across frames where light hasn't invalidated them. Roughly 1.5-2 ms for a scene with one sun + 4 spotlights casting shadows, scales with visible geometry not total map area.

**CSM fallback (4 cascades):** for hardware below VSM threshold (Switch 2, low-end PC). Cascade splits at log/linear hybrid:

```cpp
float lambda = 0.75f;
float f = float(i) / float(N);                 // float ratio; int i/N would truncate to 0
float uni  = near + (far - near) * f;
float log_ = near * std::pow(far / near, f);
splits[i] = lambda * log_ + (1.0f - lambda) * uni;
```

2048² at D32F = 16 MB per cascade → 64 MB for all four. Stabilize by snapping to texel grid to eliminate shimmer.

**PCSS:** blocker search 16 taps in a Poisson disk, penumbra = (receiver - blocker) / blocker * lightSize. Filter with 32-64 taps. Cost ~1 ms at 1080p — replace with RT shadows on capable platforms.

**Hardware RT shadows:** 1 spp + denoise (SVGF or ReLAX). Variable-rate: only trace pixels where VSM says "penumbra". Shadow denoisers are fragile — validate against ground truth (1024 spp reference).

**Contact shadows (screen-space ray march):** 8-16 steps in screen space, catches small-detail occlusion that shadow maps miss. 0.3 ms, always on.

**Platform tiers:**
- PS5/XSX: VSM + RT shadows for hero light
- PC (RTX 2060+): VSM + RT shadows optional
- PC low / Switch 2: CSM + PCSS + contact shadows
- Mobile: CSM 2-cascade + hard shadows, contact shadows optional

---

## Lighting Architecture

**Clustered forward+** already covered. Key detail: light culling in compute (one threadgroup per cluster, parallel sphere-vs-frustum test). 256 lights culled in ~0.2 ms.

**Area lights via LTC (Heitz 2016):** linearly transformed cosines. The clamped-cosine distribution is warped by a **3×3** transform `M` (evaluation uses its inverse `Minv`); by construction the matrix has only **four** non-trivial coefficients (the others are 0 or normalized to 1), so they pack into a single 64×64 RGBA LUT tabulated by (NoV, roughness). A **second** 64×64 LUT stores the BRDF **magnitude/norm** and the **Fresnel + geometric** term. Closed-form polygonal integration. Works for rect/disk/line lights.

```hlsl
// LTC evaluation for a quad light — Minv is 3x3, rebuilt from the 4 stored coefficients
float3x3 Minv = SampleLTC(NoV, roughness);       // LUT 1: 4 matrix coefficients
float2   mag  = SampleLTC_Mag(NoV, roughness);   // LUT 2: magnitude + Fresnel term
float3 L = LTC_Evaluate(N, V, pos, Minv, quadPoints) * mag.x;
```

Cost: ~50 ALU per light per pixel. Cheap. Replaces punctual-approximation hacks entirely.

**IES profiles:** 1D (symmetric) or 2D (asymmetric) photometric distributions, 128x64 R16 LUT per profile. Sample by spherical angle relative to light forward.

**Photometric units:** author in lumens (total flux) or candela (peak intensity). Convert to radiance at shading time. Real-world references:
- Sun at noon: ~120,000 lux on ground, ~1.6e9 cd/m^2 disk luminance
- Overcast sky: ~10,000 lux
- Office fluorescent: ~500 lux
- Full moon: ~0.25 lux

Exposure should be computed from log-average luminance — do not guess middle gray.

---

## Virtual Geometry

Nanite-style meshlet hierarchy. Offline: cluster mesh into ~128-tri groups, build BVH of clusters, compute LOD chain via quadric edge collapse on *group* boundaries (Karis's DAG preserving cross-group seams).

```cpp
struct Meshlet {
    float3 bboxMin, bboxMax;
    float  errorLOD;       // screen-space error at this LOD
    float  parentErrorLOD; // error of parent (coarser) meshlet
    uint32_t vertexOffset, triangleOffset;
    uint8_t  vertexCount, triangleCount;  // Nanite cluster: <=128 verts, <=128 tris
};
```

> **Meshlet vs cluster caps — keep them straight.** The mesh-shader *authoring* unit in `ASSET_PIPELINE_AND_COOKER.md` caps meshlets at **64 vertices / 124 triangles** (the meshoptimizer + NVIDIA hardware sweet spot). Nanite's software LOD-DAG **clusters** instead group **~128 triangles**; when rasterized through the HW mesh-shader path they stay within its 256-vertex / 256-primitive limits. The two numbers describe different pipeline stages, not a contradiction.

**Runtime:** GPU-driven. Persistent thread compute pass walks BVH, evaluates screen-space error per cluster, emits visible meshlets to an indirect draw buffer. Mesh shader (SM 6.5 / VK_EXT_mesh_shader) rasterizes, writes visibility buffer (R32 cluster ID | triangle ID).

**Two-phase occlusion culling:**
1. Phase 1: draw last-frame visible meshlets, update HZB
2. Phase 2: test remaining meshlets against new HZB, draw newly visible

Eliminates false occlusion from camera motion without popping.

**Visibility buffer resolve:** material shading in a compute pass, one dispatch per material ID. Reconstruct attributes via barycentric interpolation from cluster index buffer. Avoids overdraw entirely — every pixel shades exactly once.

DirectX 12 compute Work Graphs are an optional Shader Model 6.8 path for irregular GPU-generated workloads. Mesh Nodes require the Shader Model 6.9 preview path and an opt-in Agility SDK. Keep SM 6.5 Mesh Shaders and SM 6.0 classic VS/PS with indirect draws as fallbacks. Profile representative content on each target.

---

## Post-Processing Chain

Order matters. Standard chain at native render resolution:

1. **Motion vector generation** (included in G-buffer)
2. **TAA/TSR** — history reprojection, variance clipping (YCoCg space), neighborhood clamping. Blend factor 0.05-0.1 for static, 0.2+ when disocclusion detected
3. **SSAO/GTAO** — GTAO (ground-truth AO, Jimenez 2016) is strictly better than HBAO+. 16 samples, 1/2 res, bilateral upsample. ~0.4 ms
4. **SSR** — hierarchical depth (HiZ) ray march, 32 steps max, fallback to cubemap/DDGI on miss. Temporal accumulation for roughness > 0.1
5. **Upscaling + Ray Reconstruction** — DLSS 4 (transformer model) / FSR 4 (ML, RDNA4) / XeSS 2 / MetalFX depending on platform. All take motion vectors + depth + color + exposure. The 2026 floor folds the RT denoiser *into* the upscaler — DLSS Ray Reconstruction and the FSR 4 neural path replace separate hand-tuned denoise passes; a denoiser that cannot run a neural path is behind the floor (see [Neural Rendering](#neural-rendering))
6. **Depth of Field** — bokeh. Gather method: half-res, 49-tap disk, tile-based classification (near/far/focus). Scatter-as-gather for highlights
7. **Motion blur** — per-object using motion vectors, tile max 16x16, 8-16 samples along velocity
8. **Bloom** — downsample pyramid (13-tap Kawase or Call of Duty Siggraph 2014), 6-8 mip levels, upsample with tent filter
9. **Tonemap + color grade** — in HDR linear, apply LUT in log-space (ACEScc or LogC), then ACES/AgX curve to display space
10. **Film grain, chromatic aberration, vignette** — subtle, user-toggleable

**TAA history rejection:** YCoCg neighborhood clip, velocity weighting, disocclusion mask from depth derivative. Ghosting on thin geometry is the perpetual enemy — neighborhood *clip* (not clamp) and variance-based bounds are non-negotiable.

**Upscaling choice:**
- NVIDIA RTX: DLSS 4 (transformer super-resolution + Ray Reconstruction; multi-frame gen on 50-series)
- AMD / Xbox / PS5: FSR 4 (ML path on RDNA4; FSR 3.1 fallback on older GPUs and current consoles, with PS5 Pro PSSR as the platform ML option)
- Intel Arc: XeSS 2 (XMX path, with frame gen)
- Apple: MetalFX upscaling
- Always expose TSR/TAAU as fallback — do not ship without a vendor-neutral, ML-hardware-free path

---

## Volumetric Rendering

**Froxel fog:** 3D texture 160x90x128 (matching tile grid, 128 Z slices), store scattering+extinction+phase. Two compute passes: (1) material inject (participating media + lights), (2) raymarch accumulate front-to-back. Apply to lit frame via per-pixel 3D texture sample.

Memory: 160*90*128*8 bytes (RGBA16F) = 14.7 MB. Cost: ~0.8 ms at these dims.

```hlsl
// Scattering integration (Frostbite, Hillaire 2015)
float3 scatt = 0;
float transmittance = 1;
for (uint z = 0; z < 128; ++z) {
    float4 s = fogVolume[uint3(tile, z)];
    float3 sliceScatt = s.rgb * transmittance;
    float sliceTrans = exp(-s.a * sliceDepth);
    scatt += sliceScatt * (1 - sliceTrans) / max(s.a, 1e-4);
    transmittance *= sliceTrans;
}
```

**Clouds (Frostbite/Guerrilla):** 2-channel 3D noise (Perlin-Worley low freq + Worley high freq), raymarch 64-128 steps primary + 6 light steps per primary. Half-res with temporal reprojection 4x4 bayer across frames. ~2-3 ms.

**Atmospheric scattering:** Bruneton precomputed tables (transmittance, scattering, irradiance) — 256x64 transmittance LUT, 32x128x32 scattering LUT. Hillaire 2020 simplification is cheaper for realtime (~0.3 ms total) and preserves multi-scattering.

**God rays:** screen-space radial blur of occluded sun disk (cheap) or ray-marched participating media sampling shadow map (correct). Prefer the latter integrated into froxel fog.

---

## Special Surfaces

**FFT Ocean (Tessendorf 2001):** spectrum in frequency domain, IFFT per frame to get heightfield + slope. 512x512 IFFT = 0.5 ms on modern GPUs. Combine 3-4 cascades (world-space tiles: 4096m, 512m, 64m, 8m) for detail without repetition. Jonswap/Pierson-Moskowitz spectra.

**Terrain:** geometry clipmaps (Losasso/Hoppe) or CDLOD. Virtual texturing for material layers — 8k x 8k physical page cache, 128x128 pages, feedback buffer drives streaming. Indirect draws from GPU-culled patches.

**SSS (Burley 2015):** normalized diffusion profile, 3-gaussian fit. Separable screen-space pass (horizontal + vertical) or pre-integrated for skin. Transmission for ears/nostrils via shadow depth thickness lookup.

**OIT:**
- MBOIT (moment-based): 4 moments, 8 RT16F, stable and order-independent, ~2 ms at 1080p
- WBOIT (weighted blended): cheap (~0.3 ms), artifacts at high overlap, fine for particles
- Depth-peeling: reference only, 4-8 passes, not realtime

Choose WBOIT for particles, MBOIT for hero translucents (glass), forward+ with depth-sort for hair cards.

**Decals:** deferred decal pass — box-projected, reads G-buffer depth, writes back into G-buffer RTs (blend or replace per channel). Avoid forward decals; they re-shade expensively.

---

## GPU Particles

Full compute simulation. Per-emitter dispatch, atomic counters for alive count, indirect draw for rendering.

```cpp
// Double-buffered alive lists + dead list
buffer<uint> aliveIndicesA, aliveIndicesB, deadIndices;
// Compaction: each frame, alive particles survive -> aliveB, deaths -> dead
// Indirect dispatch count = aliveCount / 64
```

**Dead-alive compaction:** prefix sum (GPU scan) on alive mask, scatter survivors. Or use append/consume buffers (simpler but less deterministic). 1M particles sim + render in ~1 ms.

**Sort for transparency:** bitonic sort, log^2(N) passes. 1M particles = 400 dispatches of ~100k threads. ~1.5 ms. Or skip sort and accept WBOIT artifacts for smoke/sparks.

---

## Neural Rendering

**Shipping options in 2026:**
- **Neural denoising / Ray Reconstruction.** Use DLSS Ray Reconstruction and other vendor paths on supported hardware when image-quality and latency testing justify them. Retain classical denoisers such as ReLAX/ReBLUR/SVGF for unsupported platforms and as a diagnostic baseline.
- **DLSS 4 / FSR 4 / XeSS 2:** integrate through vendor-specific capability and quality tiers; do not imply feature parity across GPU vendors or consoles.
- **NVIDIA NTC (Neural Texture Compression):** 4-8x smaller than BC7 at comparable quality. Decoder inline in shader (~20 cycles per sample). Use for albedo/normal on distant LODs.

**2027 production trajectory — design for it, gate it behind capability + fallback:**
- **Neural Radiance Caching (NRC, Müller 2021):** integrated into experimental Lumen configs; converging but still drifts in some configs. Design the GI stack so an NRC tier can slot above the SDF/RT final gather.
- **Neural LOD / neural materials:** stream model weights as assets; expose the same `INeuralBackend`.

**Research / caution zone:**
- NeRF / Gaussian-splat level-of-detail — interesting for background props and photogrammetry, not a primary-geometry path yet.
- Neural BRDFs — research only; authoring and LOD are unsolved.

Ship only what QA can reproduce, gate neural features behind capabilities and validated fallbacks, and add an `INeuralBackend` seam when concrete roadmap features need one.

---

## Tone Mapping and Color

**ACES vs AgX:** ACES (RRT+ODT) is industry-standard film look but oversaturates and hue-shifts in bright reds/blues. AgX (Troy Sobotka) desaturates cleanly in highlights, preserves hue, reads as "modern". AgX is the right default for 2026 productions; expose ACES as a stylistic option.

**Auto-exposure:** histogram in log-luminance (256 bins over -10..+10 EV). Compute mean, adjust EV toward target over 1-2 s. Never use simple average luminance — sparse bright pixels dominate.

```hlsl
// Histogram bin from log luminance
float logLum = log2(max(luminance, 1e-4));
float t = saturate((logLum - minLogLum) / (maxLogLum - minLogLum));
uint bin = uint(t * 254.0) + 1;  // bin 0 = black pixels
```

**HDR output:** HDR10 (BT.2020, PQ EOTF, 1000 nit typical mastering), Dolby Vision dynamic metadata (MaxCLL/MaxFALL per scene). Tonemap in scene-referred linear, convert to PQ, output 10-bit. Do NOT tonemap twice. Respect `SDR whitepoint` UI slider (typically 100-300 nits paper-white).

**Color grading LUT:** 33x33x33 3D LUT in LogC or ACEScc space (log-encoded). Apply before tonemap curve. Artists author in Resolve/Nuke and export .cube. Runtime storage: RGBA16F is **8 bytes/texel**, so 33³ × 8 B = 287,496 B ≈ 281 KiB (~288 KB). (An RGBA8 LUT would halve that to ~144 KB, but banding in log space usually forces 16F.)

---

## See Also

- **`physically-based-rendering` skill** — authoritative for material/BRDF/BSDF math, OpenPBR 1.1, color management, and path-tracing trade-offs.
- `CROSS_PLATFORM_AND_CONSOLE.md` — HAL/GAL design, platform-specific backends, shader cross-compilation
- `PERFORMANCE_AND_PROFILING.md` — frame budgets, GPU-driven pipeline optimization, profiler integration
