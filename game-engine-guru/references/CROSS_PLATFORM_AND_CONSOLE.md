# Cross-Platform and Console Architecture

Reference document for multi-platform AAA engine design: HAL/GAL abstraction, graphics backend implementations, console-specific hardware, mobile TBDR, shader cross-compilation, and VR/XR. Audience: senior platform and graphics engineers shipping across PS5, Xbox Series X|S, Switch 2, Windows, macOS/iOS, Linux, Android, and OpenXR HMDs.

## Table of Contents

- HAL/GAL Design
- Vulkan Backend
- DX12 Backend
- Metal Backend
- Console: PS5
- Console: Xbox Series X|S
- Console: Switch 2
- Mobile (iOS / Android)
- Shader Cross-Compilation
- VR/XR

---

## HAL/GAL Design

Two abstraction layers, not one. HAL (Hardware Abstraction Layer) wraps OS/filesystem/threading/input, as well as `INeuralBackend` for Neural Processing Units (NPUs/Tensor cores). GAL (Graphics Abstraction Layer) wraps the graphics API. Never conflate them — a rendering engineer should be able to port to a new GPU driver without touching file I/O.

GAL design rule: expose the *most restrictive* modern API shape (explicit sync, bindless descriptors, explicit resource state) and emulate on weaker backends. Never abstract down to DX11 / OpenGL — that era is dead.

```cpp
// GAL handle model: opaque 32/64-bit handles, not pointers
struct BufferHandle { uint32_t idx : 24; uint32_t gen : 8; };
struct TextureHandle { uint32_t idx : 24; uint32_t gen : 8; };

// Fallible APIs return std::expected, never throw
[[nodiscard]] std::expected<BufferHandle, GfxError>
    CreateBuffer(const BufferDesc& desc) noexcept;
```

**Capability queries** happen once at device init, cached in a `GpuCaps` struct:

```cpp
struct GpuCaps {
    bool meshShaders;          // SM 6.5 / VK_EXT_mesh_shader / Metal 3
    bool hardwareRT;           // DXR 1.1 / VK_KHR_ray_tracing_pipeline
    bool bindlessTier3;        // D3D12_RESOURCE_BINDING_TIER_3 / descIdx
    bool waveOps;              // SM 6.0 wave intrinsics
    bool variableRateShading;  // Tier 2 = per-primitive
    bool samplerFeedback;      // SFS on XSX, D3D12 SF
    uint32_t waveLaneMin, waveLaneMax;  // NV = 32 fixed; AMD RDNA = 32 or 64 (Wave32/Wave64); Intel = 8/16/32 (SIMD8/16/32)
    uint64_t vramBudget;
};
```

On DX12: `CheckFeatureSupport(D3D12_FEATURE_D3D12_OPTIONS7)` for mesh shaders, `OPTIONS5` for DXR, `OPTIONS12` for enhanced barriers. On Vulkan: `vkGetPhysicalDeviceFeatures2` chain with the relevant `*Features` structs.

**Graceful degradation matrix:** the GAL exposes a capability; the renderer has 2-3 implementations for each key feature. Example: virtual shadow maps require mesh shaders + atomic64. If absent, fall back to CSM. If compute indirect is missing (it isn't, on any supported platform), fail hard at boot.

Never do runtime capability branching inside hot shaders — select the permutation at PSO creation.

---

## Vulkan Backend

Used on: Windows, Linux, Android, some Switch 2 paths (via NVN2 underlay, but NVN2 native is preferred there).

**Instance/device/queues:**
- Instance: enable `VK_EXT_debug_utils` in dev, strip in ship
- Physical device: pick by VRAM + feature support, not vendor
- Queue families: graphics (+compute +transfer), async compute (compute-only), transfer (DMA-only, for upload heap)

Three queue submission model:
```cpp
VkQueue gfxQueue;       // main render, present
VkQueue asyncQueue;     // shadow, post-FX, particles overlapping gfx
VkQueue transferQueue;  // BAR uploads, avoids stalling gfx
```

**Descriptors:** descriptor indexing (VK 1.2 core, `VK_DESCRIPTOR_BINDING_PARTIALLY_BOUND`, `VK_DESCRIPTOR_BINDING_UPDATE_AFTER_BIND`). One giant bindless set per frame: ~500k SRV slots, ~100k UAV slots (D3D12 caps the shader-visible CBV/SRV/UAV heap at 1,000,000 on Tier 2/3; Vulkan limits come from `maxDescriptorSet*` / `maxPerStageDescriptorUpdateAfterBind*` — query them). **Samplers are the exception:** the D3D12 shader-visible sampler heap is hard-capped at **2048**, so use a small static sampler table (or static samplers in the root signature), not a 10k bindless sampler array. Textures addressed by 32-bit handle in push constants. Never use legacy `VkDescriptorSet` per draw — the bind cost dominates.

**Render passes:** dynamic rendering (VK 1.3 core, `vkCmdBeginRendering`). Classic `VkRenderPass` is useful only on tile-based mobile where subpasses preserve on-chip tile memory — keep that path for Mali/Adreno/Apple.

**Synchronization:** timeline semaphores (VK 1.2 core). Monotonic 64-bit counter per queue, no more binary semaphores. Frame-pacing becomes trivial.

```cpp
VkTimelineSemaphoreSubmitInfo ts{};
ts.sType = VK_STRUCTURE_TYPE_TIMELINE_SEMAPHORE_SUBMIT_INFO;
uint64_t signalValue = frameIdx + FRAMES_IN_FLIGHT;
ts.pSignalSemaphoreValues = &signalValue;
// Wait on CPU: vkWaitSemaphores with value = frameIdx
```

**Memory:** VMA (Vulkan Memory Allocator) is the right answer. Fight it only if you have a specific reason. Custom pools for: render targets (lazy-allocated on TBDR), streaming textures, uniform rings.

---

## DX12 Backend

Used on: Windows, Xbox Series X|S (DX12-X variant). Xbox DX12 is *not* identical to PC DX12 — it's an Xbox-specific flavor (`D3D12XBOX_*` APIs) with console-only features.

**Root signatures (SM 6.6 bindless):**

```hlsl
// Shader Model 6.6 directly-indexed bindless
Texture2D tex = ResourceDescriptorHeap[pushConst.texIdx];
RWStructuredBuffer<Foo> buf = ResourceDescriptorHeap[pushConst.bufIdx];
```

Root sig specifies `CBV_SRV_UAV_HEAP_DIRECTLY_INDEXED | SAMPLER_HEAP_DIRECTLY_INDEXED`. One shader-visible descriptor heap per frame in flight (~1M descriptors, ~32 MB). Push constants (root CBV / 32-bit constants) carry handles.

**Enhanced barriers (D3D12 Agility SDK):** replace legacy `D3D12_RESOURCE_BARRIER` with `D3D12_BARRIER_GROUP`. Explicit access + sync + layout, matches Vulkan model. Elimitates split-barrier wrangling.

```cpp
D3D12_TEXTURE_BARRIER tb {
    .SyncBefore = D3D12_BARRIER_SYNC_RENDER_TARGET,
    .SyncAfter  = D3D12_BARRIER_SYNC_PIXEL_SHADING,
    .AccessBefore = D3D12_BARRIER_ACCESS_RENDER_TARGET,
    .AccessAfter  = D3D12_BARRIER_ACCESS_SHADER_RESOURCE,
    .LayoutBefore = D3D12_BARRIER_LAYOUT_RENDER_TARGET,
    .LayoutAfter  = D3D12_BARRIER_LAYOUT_SHADER_RESOURCE,
    .pResource = tex,
    .Subresources = {0, 1, 0, 1, 0, 1},
    .Flags = D3D12_TEXTURE_BARRIER_FLAG_NONE,
};
```

**PIX markers:** `PIXBeginEvent` / `PIXEndEvent` with color-coded categories. Cheap (~100 ns) but strip in ship builds with a compile-time flag.

**DRED (Device Removed Extended Data):** enable in debug and internal ship (not retail — performance cost). When device is removed (`DXGI_ERROR_DEVICE_REMOVED`), DRED gives you auto-breadcrumbs of the last successful GPU op and page-fault VA. Without it, GPU hangs are black boxes.

```cpp
ID3D12DeviceRemovedExtendedDataSettings1* dred;
D3D12GetDebugInterface(IID_PPV_ARGS(&dred));
dred->SetAutoBreadcrumbsEnablement(D3D12_DRED_ENABLEMENT_FORCED_ON);
dred->SetPageFaultEnablement(D3D12_DRED_ENABLEMENT_FORCED_ON);
```

---

## Metal Backend

Used on: macOS, iOS, iPadOS, tvOS, visionOS. Apple Silicon GPU is TBDR — design matters.

**MTLDevice + command queue:** one device per GPU (Mac Pro can have discrete + integrated). Command queue per engine (render, compute, blit). Command buffers are lightweight — allocate per-pass, not per-frame.

**Argument buffers (Tier 2 = bindless-equivalent):** encode resource references into a buffer, pass one buffer to shader. Tier 2 supports ~1M resources per arg buffer. Equivalent to DX12 bindless.

```objc
id<MTLArgumentEncoder> enc = [device newArgumentEncoderWithArguments:descriptors];
id<MTLBuffer> argBuf = [device newBufferWithLength:enc.encodedLength ...];
[enc setArgumentBuffer:argBuf offset:0];
[enc setTexture:tex atIndex:0];
```

**Metal 3 mesh shaders:** `MTLMeshRenderPipelineDescriptor`, task + mesh stages, matches DX12/Vulkan mesh shader model. Only on Apple Silicon M3+ and A17+.

**Metal Performance Shaders (MPS):** prebuilt fast paths for FFT, convolution, matrix multiply, BVH build. Use for cloth sim, ocean FFT, ML inference — hand-rolling on Metal rarely beats MPS.

**Memoryless render targets:** crucial on TBDR. Depth / G-buffer that are consumed within the tile never touch DRAM. Bandwidth savings of 30-60%. Set `MTLStorageModeMemoryless` and ensure load/store actions are `DontCare` at pass boundaries.

---

## Console: PS5

**Hardware:** AMD RDNA2, 36 CUs @ 2.23 GHz, 10.28 TFLOPS FP32. 16 GB GDDR6 shared @ 448 GB/s. Custom SSD @ 5.5 GB/s raw, ~8-9 GB/s with Kraken/Oodle decompression.

**Graphics API:** Sony-proprietary (not public). Closer to Vulkan in explicitness, with PS5-specific extensions. Everything below is from public Sony dev talks / SDK docs.

**Hardware RT:** Intersection Engine in each CU — BVH traversal in fixed function, shaders handle any-hit / closest-hit. ~3-4x faster than equivalent RDNA2 PC part for BVH build; traversal comparable.

**Kraken SSD decompression:** dedicated hardware block, zero CPU cost. Stream assets at ~8 GB/s sustained. Design streaming around this — 1-2 frame prefetch of next area is feasible.

**GPU compute priority:** async compute on separate queue with high priority for shadows / post while graphics does opaque. Non-trivial scheduling — see Sony's "Async Compute: Deep Dive" GDC talks.

**Certification (TRC):** Technical Requirements Checklist. Non-negotiable items include: controller disconnect handling (<1s grace), suspend/resume state preservation, region-specific content, save data integrity under power loss. Budget 2-4 weeks pre-submission for TRC fixes. Failed submission = 2+ week resubmit cycle.

**Memory layout:** unified GDDR6 — CPU and GPU share address space. No PCIe upload staging. `write-combined` vs `coherent` allocation still matters for CPU access patterns. Avoid CPU reads from GPU-written memory unless absolutely necessary (uncached read = 200+ cycles).

---

## Console: Xbox Series X|S

**Hardware (Series X):** AMD RDNA2, 52 CUs @ 1.825 GHz, 12.15 TFLOPS. 16 GB GDDR6 split: 10 GB @ 560 GB/s (GPU-optimal) + 6 GB @ 336 GB/s (CPU-optimal). SSD 2.4 GB/s raw, ~4.8 GB/s with hardware GDeflate.

**Series S:** 20 CUs @ 1.565 GHz, 4 TFLOPS. 10 GB total. Target 1440p internal, upscale to 4K. The Series S is the floor for current-gen — design content with 2x VRAM differential to Series X in mind.

**API:** DX12-X (Xbox GDK variant). Same shader compiler (DXC), same root signature model as PC DX12, plus console-only extensions (`D3D12XBOX_*`).

**DirectStorage with GDeflate:** `DSTORAGE_REQUEST_DESTINATION_TEXTURE_REGION` streams compressed texture directly to VRAM. Decompression on GPU. Saves CPU cycles, avoids staging buffer. 4.8 GB/s sustained.

**Smart Delivery:** single SKU, platform-specific binaries + assets auto-delivered. Maintain Series X and Series S asset tiers in build pipeline.

**SFS (Sampler Feedback Streaming):** hardware tracks which mip/tile the sampler actually fetched. Stream only touched tiles. 2-3x texture memory savings on large virtual textures. Requires `MIN_MIP_FEEDBACK` + `MIP_REGION_USED_FEEDBACK` samplers.

**Velocity Architecture:** marketing umbrella — combines NVMe SSD, DirectStorage, SFS, BCPack texture compression. Real effect: the streaming pipeline can actually keep up with 30 FPS camera teleports at 4K if you use it end-to-end.

---

## Console: Switch 2

**Hardware (public/leaked as of 2026):** custom NVIDIA chip, Ampere-class mobile GPU (~1-1.5 TFLOPS docked, ~500 GF handheld), LPDDR5 memory. DLSS integration at silicon level.

**GPU architecture:** technically IMR (immediate mode) like desktop NVIDIA, *not* TBDR. But with mobile power envelope, it behaves closer to TBDR-equivalent in terms of bandwidth sensitivity. Treat bandwidth as precious — the LPDDR5 bus is the bottleneck, not compute.

**ASTC compression:** 4x4 (8 bpp) through 12x12 (0.89 bpp). Use 6x6 or 8x8 as default for albedo, 4x4 for normals, 12x12 for distant LOD backgrounds. Never ship uncompressed textures.

**NVN2 API:** NVIDIA's console API, successor to NVN. Vulkan-like explicit API with switch-specific fast paths. Port guide from Vulkan is ~80% mechanical.

**DLSS integration:** native SDK hook. Use 1080p internal → 4K docked, 540p → 1080p handheld. Frame gen likely unavailable on this class of silicon.

**Thermal throttling:** sustained load drops clocks ~15% in handheld mode after 5-10 minutes. Test with `perf_thermal_sustained` soak tests. Design dynamic resolution floor for this state.

---

## Mobile (iOS / Android)

Universal mobile rules:

- **TBDR first.** Apple Silicon, Adreno, Mali, PowerVR all bin primitives into tiles and shade per-tile. Avoid mid-frame depth resolves. Never copy G-buffer to compute shader — use `VK_ATTACHMENT_LOAD_OP_LOAD` within the same render pass / subpass.
- **ASTC everywhere.** 4x4 to 12x12, HDR variants supported. Metal and Vulkan both expose full tier. No BC formats on mobile.
- **Half-precision (`mediump` / `half`):** 2x ALU throughput on most mobile GPUs. Lighting math, post, particles → half. Depth linearization → full. Shadow comparisons → full.
- **Thermal budget:** sustained power envelope for phones ~3-5 W (whole SoC), ~2-3 W for GPU alone. Peak burst can be 2x sustained for ~30 s. Profile after 10-minute soak, not cold-boot.
- **Vulkan 1.3 (Android) / Metal 3 (Apple):** dynamic rendering, timeline semaphores, descriptor indexing (mobile-tier). Don't target OpenGL ES — EOL everywhere except ultra-low-end.

**Memory:** mobile shares CPU/GPU memory. 4-8 GB total typical, 1-2 GB for game. Streaming budget is brutal — compression + residency tracking is mandatory.

**Variable rate shading:** Tier 1 (per-draw) on most 2023+ mobile, Tier 2 (per-primitive) on Apple A16+ and recent Adreno. Use for post, peripheral VR view, motion-blurred regions.

---

## Shader Cross-Compilation

Pipeline: HLSL (source) → DXC → DXIL (DX12) / SPIR-V (Vulkan) → SPIRV-Cross → MSL (Metal) / GLSL (ES/legacy).

**HLSL as source of truth:** best tooling (VS Code extension, PIX integration, offline reflection), mature compiler. GLSL-as-source is a dead end for cross-platform AAA.

**DXC:** produces DXIL directly, SPIR-V via `-spirv`. SM 6.6 bindless, wave intrinsics, 16-bit types — all supported.

```cpp
// Pseudo-invocation of offline shader build
dxc -T ps_6_6 -E PSMain -Fo out.dxil shader.hlsl
dxc -T ps_6_6 -E PSMain -spirv -Fo out.spv shader.hlsl
```

**SPIRV-Cross:** SPIR-V → MSL or GLSL. MSL output is production-quality. Argument buffer emission for Metal requires `--msl-argument-buffers`.

**Permutation management:** shader variants explode fast. Track permutations as a hash of defines + target. Cache by hash. Build with deterministic defines list; fail the build if perms exceed a threshold (typically 4k-16k per shader family).

**Offline PSO caching:** build PSOs at install time per-device. DX12 `ID3D12PipelineLibrary`, Vulkan `VkPipelineCache`, Metal binary archives. Shipping without this = 30 s of compilation stutter on first load of each shader.

Ship a PSO precache file per GPU family per platform. On first boot, enumerate GPU, load matching cache. Generate missing PSOs in background thread with low priority.

---

## VR/XR

**Motion-to-photon budget:** <20 ms total. Typical frame budget 11 ms at 90 Hz. Anything slower and users vomit.

**Stereo rendering:**
- **Instanced stereo:** one draw call, `SV_RenderTargetArrayIndex` selects left/right. ~1.4x cost vs mono (vs 2x for naive double-draw).
- **Multiview (VK_KHR_multiview / D3D12 ViewInstancing):** driver-level stereo broadcast. Similar perf to instanced, less engine code. Prefer this.

**Foveated rendering:**
- **Fixed foveation:** VRS Tier 2 shading rate image, center full rate, edges 2x2 or 4x4. ~20-30% GPU savings at no visible cost on HMD optics.
- **Eye-tracked foveation:** VRS SRI updated per frame from eye tracker. 40-50% savings but requires eye-tracking HMD (Quest Pro, PSVR2, Vision Pro).

**OpenXR:** runtime abstraction. `xrCreateSession`, `xrBeginFrame` / `xrEndFrame`, `xrWaitFrame` for predicted display time. Swapchains are OpenXR-managed — do not create your own. Supports DX12, Vulkan, Metal (visionOS via compositor services).

```cpp
XrFrameState frameState{XR_TYPE_FRAME_STATE};
xrWaitFrame(session, nullptr, &frameState);
xrBeginFrame(session, nullptr);
// Render using frameState.predictedDisplayTime
// Acquire swapchain image, render, release
xrEndFrame(session, &frameEndInfo);
```

**Quad views (Meta extension):** render 4 viewports per eye — high-res center, low-res periphery. Composites to final image. ~40% savings on Quest 3 at equivalent perceived quality. Still platform-specific; wrap behind a GAL capability.

**PSVR2:** dedicated HMD features — eye tracking, haptic feedback in headset, foveated rendering mandatory for perf targets. Separate codepath in OpenXR abstraction.

---

## See Also

- `RENDERING_AND_GRAPHICS.md` — PBR, GI, shadows, post-processing — the actual rendering algorithms that run on top of the backends above
- `PERFORMANCE_AND_PROFILING.md` — frame budgets, GPU-driven pipeline, profiler integration per platform
