# Rendering and Graphics Architecture

Reference document for AAA-grade realtime rendering. Audience: senior graphics engineers. Assumes familiarity with GPU hardware, modern graphics APIs (DX12/Vulkan/Metal), and shader authoring in HLSL/SPIR-V.

## Table of Contents

- Deferred vs Forward+ Architecture
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

---

## Deferred vs Forward+ vs Adaptive Architecture

The rigid deferred/forward dichotomy is dead. Every shipping AAA renderer in 2026 utilizes a hybrid approach: **Visibility-buffer** for dense opaque geometry, **Adaptive GBuffers** for modular material evaluation, and **Clustered Forward+** for transparents, hair, and VR.

**Adaptive GBuffer (Variable Bitstream):**
The legacy fixed-layout G-buffer (e.g., BaseColor, Normal, Roughness) has been superseded by the Adaptive GBuffer (pioneered by UE 5.7 Substrate). Instead of fixed render targets, material data is stored as a variable bitstream. 
- **Dynamic Allocation:** A simple single-layer material (Slab) uses minimal bits. Complex layered closures (e.g., clearcoat over metallic with fuzz) expand the bitstream dynamically per-pixel.
- **Tile Classification:** A compute pass classifies tiles by material complexity, allowing the deferred lighting pass to optimize branching and unpack only the required data.
- **Visibility Buffer Resolve:** For Nanite-style dense geometry, the visibility buffer (R32 cluster ID | triangle ID) is resolved into the Adaptive GBuffer in a compute pass, ensuring zero overdraw during complex material evaluation.

**Legacy Fallback (Blendable/Compact G-buffer):**
For low-end hardware or Switch 2, a compact legacy G-buffer (3x RT8, ~24 bpp effective) is used as a fallback, trading complex layered closures for static performance predictability.

**Clustered Forward+ froxel grid:** 16x16 tile x 32 depth slices, logarithmic Z distribution:

```cpp
// slice = log2(depth/near) / log2(far/near) * numSlices
float k = numSlices / std::log2(farZ / nearZ);
uint32_t slice = uint32_t(std::log2(depth / nearZ) * k);
```

Light lists packed as uint32 bitmasks — 256 lights per view = 8x uint32 per cluster. With 16x16x32 = 8192 clusters, that's 256 KB for the light index grid. Negligible.

**When to pick what:**
- Visibility buffer + material resolve: opaque geometry, >100k instances, Nanite-style
- Deferred shading: moderate geometry (<50k draws), many lights, simple materials
- Forward+: translucents, hair, skin, wet surfaces, anything needing MSAA, VR (MSAA is mandatory)

On mobile TBDR (Apple Silicon, Adreno, Mali) deferred is a trap — the tile cache pays dearly for the wide G-buffer read. Use forward+ with on-chip depth-prepass resolve.

---

## PBR Material Model & OpenPBR

> **Scope split — read this first.** This section covers the *engine-integration* side of PBR: how closures are packed into the Adaptive GBuffer, resolved from the visibility buffer, and evaluated in the deferred/forward lighting pass. The **shading math itself** — the rendering equation, microfacet theory (GGX NDF, Smith height-correlated masking-shadowing, Fresnel/Schlick/F82-tint), diffuse/sheen models, energy conservation & multi-scattering compensation (Kulla-Conty / Fdez-Aguera), split-sum IBL and the BRDF integration LUT, LTC area lights, OpenPBR 1.1.1 slab layering and coat-darkening physics, energy/BRDF LUTs, and SSS/transmission/IOR — **is owned by the `physically-based-rendering` skill. Load it before deriving, debugging, or implementing any BSDF math.** Do not reconstruct those equations from this summary.

The 2026 standard dictates a shift away from hardcoded shading models (e.g., "Default Lit" vs "Clear Coat") toward **Modular BSDF Closures** and strict alignment with the **OpenPBR 1.1.1** specification (supported by Epic, Unity, and Adobe).

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
    uint32_t lightIdx;
    float   wSum;    // sum of weights
    float   W;       // 1/pdf at selected sample
    uint32_t M;      // samples seen
};
// Update: with prob w/(wSum+w) replace sample
```

Decision rule: if ray budget > 1 spp and BVH build fits in 2 ms/frame, use RT + ReSTIR. Otherwise SDF+DDGI. Never ship VXGI on new platforms — memory cost doesn't amortize.

---

## Shadow Pipeline

**Virtual Shadow Maps (UE5 model):** 16k x 16k virtual resolution, 128x128 physical pages, allocated on demand per-tile per-cascade. Only pages touching visible screen pixels rasterize. Page cache reuses pages across frames where light hasn't invalidated them. Roughly 1.5-2 ms for a scene with one sun + 4 spotlights casting shadows, scales with visible geometry not total map area.

**CSM fallback (4 cascades):** for hardware below VSM threshold (Switch 2, low-end PC). Cascade splits at log/linear hybrid:

```cpp
float lambda = 0.75f;
float uni = near + (far - near) * (i / N);
float log_ = near * std::pow(far / near, i / N);
splits[i] = lambda * log_ + (1.0f - lambda) * uni;
```

2048^2 per cascade = 64 MB at D32F. Stabilize by snapping to texel grid to eliminate shimmer.

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

**Area lights via LTC (Heitz 2016):** linearly transformed cosines, 64x64 LUT of 4x4 matrices (tabulated by NoV, roughness). Closed-form polygonal integration. Works for rect/disk/line lights.

```hlsl
// LTC evaluation for a quad light
float3x3 Minv = SampleLTC(NoV, roughness);
float3 L = LTC_Evaluate(N, V, pos, Minv, quadPoints);
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
    uint8_t  vertexCount, triangleCount;  // <=64 / <=128
};
```

**Runtime:** GPU-driven. Persistent thread compute pass walks BVH, evaluates screen-space error per cluster, emits visible meshlets to an indirect draw buffer. Mesh shader (SM 6.5 / VK_EXT_mesh_shader) rasterizes, writes visibility buffer (R32 cluster ID | triangle ID).

**Two-phase occlusion culling:**
1. Phase 1: draw last-frame visible meshlets, update HZB
2. Phase 2: test remaining meshlets against new HZB, draw newly visible

Eliminates false occlusion from camera motion without popping.

**Visibility buffer resolve:** material shading in a compute pass, one dispatch per material ID. Reconstruct attributes via barycentric interpolation from cluster index buffer. Avoids overdraw entirely — every pixel shades exactly once.

DirectX 12 Work Graphs (SM 6.9) and Mesh Nodes are mandatory for the absolute fast path in 2026, allowing the GPU to spawn pipelines without CPU intervention. Fallback for SM 6.5: Mesh Shaders. Fallback for SM 6.0: classic VS/PS with GPU-culled indirect draws, ~2x slower but functional. Switch 2 supports mesh shaders; older mobile does not — author a traditional LOD chain for those.

---

## Post-Processing Chain

Order matters. Standard chain at native render resolution:

1. **Motion vector generation** (included in G-buffer)
2. **TAA/TSR** — history reprojection, variance clipping (YCoCg space), neighborhood clamping. Blend factor 0.05-0.1 for static, 0.2+ when disocclusion detected
3. **SSAO/GTAO** — GTAO (ground-truth AO, Jimenez 2016) is strictly better than HBAO+. 16 samples, 1/2 res, bilateral upsample. ~0.4 ms
4. **SSR** — hierarchical depth (HiZ) ray march, 32 steps max, fallback to cubemap/DDGI on miss. Temporal accumulation for roughness > 0.1
5. **Upscaling + Ray Reconstruction** — DLSS 4 (transformer model) / FSR 4 (ML, RDNA4) / XeSS 2 / MetalFX depending on platform. All take motion vectors + depth + color + exposure. The 2026 floor folds the RT denoiser *into* the upscaler — DLSS Ray Reconstruction and the FSR 4 neural path replace separate hand-tuned denoise passes; a denoiser that cannot run a neural path is behind the floor (see Neural Rendering)
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

**Production floor (2026) — table stakes, not optional:**
- **Neural denoising / Ray Reconstruction.** DLSS Ray Reconstruction and the FSR 4 neural path are the production floor for any RT denoiser. The neural denoiser folds into the upscaler (see Post-Processing §5) and replaces separate hand-tuned SVGF/ReLAX passes for RT GI, reflections, and shadows. A denoiser pipeline that *cannot* run a neural path is behind the floor. Provide an `INeuralBackend` (DirectML / CoreML / console ML), stream model weights as cooked assets, and batch inference — never hardwire a classical-only denoiser.
- **DLSS 4 / FSR 4 / XeSS 2:** neural upscalers, production-hardened.
- **NVIDIA NTC (Neural Texture Compression):** 4-8x smaller than BC7 at comparable quality. Decoder inline in shader (~20 cycles per sample). Use for albedo/normal on distant LODs.

**2027 production trajectory — design for it, gate it behind capability + fallback:**
- **Neural Radiance Caching (NRC, Müller 2021):** integrated into experimental Lumen configs; converging but still drifts in some configs. Design the GI stack so an NRC tier can slot above the SDF/RT final gather.
- **Neural LOD / neural materials:** stream model weights as assets; expose the same `INeuralBackend`.

**Research / caution zone:**
- NeRF / Gaussian-splat level-of-detail — interesting for background props and photogrammetry, not a primary-geometry path yet.
- Neural BRDFs — research only; authoring and LOD are unsolved.

Disclaimer: outside the production-floor items above, the neural rendering hype curve runs ahead of QA. Ship what your QA team can repro-test, gate everything else behind a capability query with a working classical fallback, and defer true R&D to feature branches. "Neural" is not an architecture — it is a tool with an `INeuralBackend` seam; the *seam* is mandatory now, even where a given model is not.

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

**Color grading LUT:** 33x33x33 3D LUT in LogC or ACEScc space (log-encoded). Apply before tonemap curve. Artists author in Resolve/Nuke and export .cube. Runtime storage: 33^3 * 4 bytes RGBA16F = 144 KB.

---

## See Also

- **`physically-based-rendering` skill** — authoritative for all material/BRDF/BSDF math: rendering equation, GGX/Smith/Fresnel/F82, energy conservation & multi-scatter compensation, split-sum IBL, LTC area lights, OpenPBR 1.1.1 slabs, energy/BRDF LUTs, SSS/transmission/IOR, MaterialX, and path-tracing vs. real-time trade-offs. Load it whenever a rendering task crosses from engine integration into shading correctness.
- `CROSS_PLATFORM_AND_CONSOLE.md` — HAL/GAL design, platform-specific backends, shader cross-compilation
- `PERFORMANCE_AND_PROFILING.md` — frame budgets, GPU-driven pipeline optimization, profiler integration
