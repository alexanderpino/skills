# Performance and Profiling

Reference document for shipping-grade performance engineering in AAA engines. Audience: senior performance engineers who already know that "premature optimization" was a reminder to measure, not a license to write slow code. Numbers, budgets, tools. No platitudes.

## Table of Contents

- Frame Budget Breakdown
- CPU Optimization
- GPU Optimization
- Memory Optimization
- Threading Optimization
- Profiling Infrastructure
- External Profiler Integration
- Performance Regression Testing
- Draw Call Optimization

---

## Frame Budget Breakdown

Hard numbers. Miss by 10% and you ship 50 fps with stutters.

**60 Hz target: 16.67 ms frame**

| Stage | Budget (ms) | Notes |
|-------|-------------|-------|
| Simulation (gameplay, physics, AI) | 2.0 | Fixed timestep, subset of available threads |
| Render prep (culling, material sort, cmd build) | 4.0 | Usually parallel with sim-next-frame |
| GPU render (opaque + shadows + transparents) | 6.0 | Longest bar in profiler |
| GPU post (TAA/upscale/tonemap/bloom) | 2.0 | Can overlap opaque via async compute |
| Present + driver overhead | 2.0 | OS compositor, pageflip, driver submit |
| **Slack** | 0.67 | Variance absorption — do not fill |

**120 Hz target: 8.33 ms** — halve all of the above, or render at lower internal resolution and upscale. 120 Hz is realistic only at 1080p-internal with DLSS/FSR Quality for most AAA content.

**CPU/GPU overlap model:** frame N CPU runs concurrently with frame N-1 GPU. `FRAMES_IN_FLIGHT = 2` is standard; 3 reduces stutter susceptibility at +1 frame input latency. Higher than 3 is a crime against input feel.

```cpp
// Ring buffer indexing
uint32_t frameIdx = g_frameCounter % FRAMES_IN_FLIGHT;
WaitForFenceValue(frameFences[frameIdx]);  // GPU frame N-2 done
auto& cmdBuf = cmdBufs[frameIdx];
// ... record frame N ...
Submit(cmdBuf, frameFences[frameIdx] = ++fenceValue);
```

Stutter diagnosis rule: if `frameTime` spikes but `gpu_busy_time` is flat, it's CPU or present. If both spike, it's GPU. If `frameTime` is fine but input feels laggy, your FRAMES_IN_FLIGHT is too high.

---

## CPU Optimization

**SoA over AoS.** Archetype-based ECS (Bitsquid, Flecs, EnTT) stores components contiguously per archetype. Iteration becomes linear prefetch-friendly scan. Expected speedup over naive AoS object iteration: 3-8x for cache-bound workloads. (Storage internals — chunk layout, archetype graph, query matching, change detection — in `ECS_AND_DATA_ORIENTED.md`; this section is the perf-tuning angle.)

```cpp
// Archetype storage: one contiguous array per component type per archetype
struct Archetype {
    std::vector<Entity>       entities;     // 8 B each
    std::vector<Position>     positions;    // 12 B each
    std::vector<Velocity>     velocities;   // 12 B each
    // Same length, same order. Iterate via zip.
};

// Cache line = 64 B → 5 Positions per line, 5 Velocities per line
// 10M entities sim: ~4 ms with SIMD integration, <1 ms scalar prefetch
```

**SIMD intrinsics:** baseline by target.
- x86-64: SSE4.2 floor, AVX2 standard, AVX-512 opt-in (check `cpuid`)
- ARM64: NEON mandatory, SVE2 on modern mobile / Grace / Apple
- Console: PS5/XSX = AVX2 available

Write `<simd.h>`-style wrapper types once. Don't scatter intrinsics through gameplay code.

```cpp
// Portable 4-wide float
struct f32x4 {
    #if defined(__AVX2__)
    __m128 v;
    #elif defined(__ARM_NEON)
    float32x4_t v;
    #endif
    // ... ops ...
};
```

**Branch prediction:** `[[likely]]` / `[[unlikely]]` (C++20) or `__builtin_expect`. Mispredict on modern CPUs ≈ 15-20 cycles. In hot inner loops, branchless code (select via mask) often wins.

**LTO + PGO:** link-time optimization mandatory for ship. Profile-guided optimization on critical binaries — instrument, run a 30-minute profile of typical gameplay, rebuild. Typical win: 5-15% on CPU-bound frame time.

**constexpr / consteval:** push everything that can move to compile time there. Reflection data, shader permutation tables, material parameter tables. C++23 `consteval` for strictly-compile-time; C++26 reflection (when available, guarded) will eliminate most hand-rolled codegen.

```cpp
#if defined(__cpp_reflection) && __cpp_reflection >= 202506L
    // C++26 reflection path (P2996; real FTM is __cpp_reflection)
#else
    // C++23 macro + consteval fallback
#endif
```

---

## GPU Optimization

**Occupancy:** wavefronts in flight per CU / SM. On RDNA2 (PS5/XSX): 32 waves max per CU, practical 16-24 given register/LDS budgets. On NVIDIA Ampere: 48 warps per SM max, practical 24-32.

Register pressure rules of thumb:
- 32 VGPRs per thread → full occupancy
- 64 VGPRs → ~50% occupancy
- 128 VGPRs → ~25% occupancy, usually only acceptable for RT / heavy compute kernels

LDS (AMD) / shared memory (NVIDIA): 64 KB per CU on RDNA2, 100 KB on Ampere. Split across groups in flight. A 16 KB shared alloc limits to 4 groups/CU.

**Bandwidth vs compute bound:** measure with roofline analysis (Nsight, GPA). A modern console at 448 GB/s with ~10 TFLOPS hits arithmetic intensity breakeven at ~22 FLOP/byte. Post-FX passes are usually BW-bound; deferred lighting is compute-bound. Pack G-buffer aggressively to unlock BW for lighting.

**Wave/warp divergence:** branch in a wave → both sides execute, masked. Cost = sum of both sides. Avoid via:
- Wave-uniform branches (guaranteed same across lane via `WaveReadLaneFirst` or known-uniform CB value)
- Material sort: sort pixels by material ID before shading so each wave is homogeneous
- `WaveActiveAnyTrue` / `WaveActiveAllTrue` for early-out on wave granularity

```hlsl
// Material dispatch: one thread group per material ID, over list of classified pixels
[numthreads(64, 1, 1)]
void CS_ShadeMaterial(uint tid : SV_DispatchThreadID) {
    uint pixelIdx = materialPixelList[tid];
    // All threads in wave shade same material → zero divergence
}
```

**Async compute:** run shadow map generation or SSAO on compute queue in parallel with opaque G-buffer on graphics queue. Typical savings 15-25% GPU frame time. Requires careful fence/barrier design — it is easy to create hazards. Always validate with GPU capture diff.

**Indirect drawing:** `ExecuteIndirect` (DX12) / `vkCmdDrawIndexedIndirectCount` (Vulkan). GPU-built command lists from compute-culled visible set. Eliminates CPU draw call overhead entirely. Two-phase cull (prev-frame HZB, new-frame HZB) prevents disocclusion popping.

---

## Memory Optimization

**Allocator tiers (strict):**

| Tier | Lifetime | Use | Allocator |
|------|----------|-----|-----------|
| Persistent | Level load → unload | Textures, meshes, audio banks | TLSF |
| Frame-scratch | Current frame | Cmd buffers, transient RTs, lighting structs | Linear bump |
| Transient | Micro-ops (per-system) | Stack-allocated / std::pmr monotonic | Arena |

Zero heap allocations in hot paths. Every hot-path `new` / `malloc` is a bug. Enforce via assertion on the general allocator during `frame begin → frame end` window in dev builds.

```cpp
// Frame-scratch allocator, thread-local bumps
struct FrameAllocator {
    std::byte* base;
    std::atomic<size_t> offset;
    size_t capacity;

    void* alloc(size_t bytes, size_t align) noexcept {
        size_t o = offset.load(std::memory_order_relaxed);
        size_t aligned;
        do {
            aligned = (o + align - 1) & ~(align - 1);
            assert(aligned + bytes <= capacity);
        } while (!offset.compare_exchange_weak(o, aligned + bytes));
        return base + aligned;
    }

    void reset() noexcept { offset.store(0); }  // at frame end
};
```

**Write combining:** upload heap / staging buffer memory is write-combined on DX12 / Vulkan. Use `_mm_stream_ps` (MOVNT) for bulk writes to avoid polluting L1/L2. Read-back from WC memory is ~10x slower than regular — never do it.

```cpp
// Non-temporal store of a 16-byte vector
_mm_stream_si128(reinterpret_cast<__m128i*>(dst), value);
// After bulk write, fence to order subsequent ops
_mm_sfence();
```

**Cache-friendly access:** prefetch (`_mm_prefetch` T0/T1/NTA) one iteration ahead in tight loops. 64-byte cache line — align hot structs to it. Pad hot atomic variables to 64 B to prevent false sharing.

**Fragmentation:** TLSF (Two-Level Segregated Fit) allocator — O(1) alloc/free, low fragmentation, deterministic. Mandatory for persistent tier. Do not use `malloc` / `new` directly in engine code; wrap.

**VRAM monitoring:** `IDXGIAdapter3::QueryVideoMemoryInfo` (DX12) / `VK_EXT_memory_budget` (Vulkan) report current budget + usage. Run residency manager in background — evict LRU streaming textures when `CurrentUsage > Budget * 0.9`. Hitting budget means OS paging to system RAM over PCIe ≈ 30 ms pageflip spike. Unacceptable.

---

## Threading Optimization

**Job system:** work-stealing deques (Cilk/TBB style) per worker thread. N workers = hardware concurrency - 2 (reserve for main + audio). Jobs as stackless coroutines or function-pointer + data.

```cpp
struct Job {
    void (*entry)(void* data);
    void* data;
    std::atomic<int>* counter;  // decrement on complete
};

// Steal-from-random-victim on empty local queue
Job* TrySteal() noexcept {
    uint32_t victim = rng.next() % workerCount;
    if (victim == self) return nullptr;
    return workers[victim].deque.steal();
}
```

**Lock-free MPMC queue:** Vyukov bounded MPMC — CAS-free on common path, bounded capacity, cache-line padded. Handles job submission from gameplay threads to worker pool.

**False sharing:** two atomics in the same 64-byte line contend. Pad.

```cpp
struct alignas(64) PaddedAtomic {
    std::atomic<uint64_t> v;
    char pad[64 - sizeof(std::atomic<uint64_t>)];
};
```

**Fibers:** useful for coroutine-style tasks that need to yield on I/O or GPU wait. Context switch ~200 cycles (vs thread switch ~3000-10000 cycles). Naughty Dog / id Tech use fibers heavily. Downside: harder to profile, thread-local storage needs care, stack size fixed.

**Thread affinity:** pin audio thread to a dedicated core. Pin main thread. Let worker threads float across remaining cores. On heterogeneous CPUs (big.LITTLE, Intel P/E cores), pin latency-critical work to performance cores.

---

## Profiling Infrastructure

**RAII scope macros:**

```cpp
#define PROFILE_SCOPE(name) ProfileScope _ps_##__LINE__(name, __FILE__, __LINE__)

struct ProfileScope {
    const char* name;
    uint64_t startTsc;
    ProfileScope(const char* n, const char*, int) noexcept
        : name(n), startTsc(__rdtsc()) {}
    ~ProfileScope() noexcept {
        ProfilerEmit(name, startTsc, __rdtsc());
    }
};
```

Zero cost in shipping build (compile out via macro). `__rdtsc` is ~6 cycles. Emit to a thread-local ring buffer; consolidate at frame end.

**GPU timestamps:** `ID3D12QueryHeap` (DX12 `QUERY_TYPE_TIMESTAMP`), `vkCmdWriteTimestamp2` (Vulkan). Pair (begin, end) per GPU scope, resolve 2-3 frames later when readback is safe. GPU tick frequency from `ID3D12CommandQueue::GetTimestampFrequency`.

```cpp
cmdList->EndQuery(queryHeap, D3D12_QUERY_TYPE_TIMESTAMP, queryIdxBegin);
// ... GPU work ...
cmdList->EndQuery(queryHeap, D3D12_QUERY_TYPE_TIMESTAMP, queryIdxEnd);
cmdList->ResolveQueryData(queryHeap, ..., readbackBuffer, ...);
// Read back on CPU 2 frames later
```

**Memory tracking:** every allocator tagged with category (`Render`, `Audio`, `Gameplay`, `Streaming`, ...). Per-category current + peak. Visualize in-game via debug HUD.

**Hitch detection:** log every frame where `frameTime > avgFrameTime * 1.5` with full scope trace + GPU timeline. Most stutters are invisible in aggregate metrics. Track hitch P99.9 / P99.99 on automated test runs.

---

## External Profiler Integration

Integrate all of these; they complement each other.

**Tracy:** single best CPU+GPU+lock+memory profiler for C++ real-time work. Low overhead (~1% CPU), frame-graph visualization, zone callstacks, GPU zones. Instrument via `ZoneScoped` / `ZoneScopedN`. Tracy server runs on separate machine — no perf impact on game.

```cpp
#include <tracy/Tracy.hpp>
void UpdateParticles() {
    ZoneScopedN("UpdateParticles");
    // ...
}
```

**PIX on Windows:** Microsoft's DX12 GPU capture + analysis tool. Full GPU timeline, shader step-through, resource lifetime, barrier validation. Annotate with `PIXBeginEvent` / `PIXSetMarker`. Use for every GPU perf investigation on Xbox/PC DX12.

**NSight Graphics (NVIDIA):** GPU capture for RTX hardware. Range profiler gives SM occupancy, memory throughput, warp stall reasons. Essential for NVIDIA-specific tuning.

**NSight Systems:** system-wide timeline (CPU threads + CUDA + graphics). Good for seeing CPU-GPU overlap.

**Superluminal:** sampling CPU profiler, Windows + Xbox. 10 KHz sample rate, full callstacks. Zero instrumentation required. Use it to find hot functions in third-party / engine code you can't instrument.

**RenderDoc:** frame debugger — resource inspection, shader debugging, pipeline state. Slower than PIX for capture but cross-vendor and cross-platform (DX12, Vulkan, GLES, Metal via wrappers). Essential for graphics bug diagnosis.

Profiler hierarchy: Tracy for always-on dev monitoring, Superluminal for CPU hotspot hunting, PIX/NSight for GPU deep-dive, RenderDoc for "why does this pixel look wrong".

---

## Performance Regression Testing

Measure every build. Untested performance regresses.

**Automated benchmarks:** Google Benchmark for micro (allocator, math, hot functions). Custom harness for whole-engine benchmarks (ingame canned demos, deterministic replay).

```cpp
#include <benchmark/benchmark.h>
static void BM_FrameAllocator(benchmark::State& state) {
    FrameAllocator fa(16 * 1024 * 1024);
    for (auto _ : state) {
        fa.reset();
        for (int i = 0; i < 10000; ++i)
            benchmark::DoNotOptimize(fa.alloc(64, 16));
    }
}
BENCHMARK(BM_FrameAllocator);
```

**Visual regression:** screenshot at deterministic camera positions, perceptual diff (SSIM, FLIP) vs golden. Alert on changes > threshold. Catches shader bugs, LOD pops, precision issues.

**Deterministic replay:** fixed RNG seed, fixed timestep, fixed input stream. Record reference inputs, replay on every build, assert frame-by-frame game state hash equal. Non-determinism is a bug — it also ruins netcode.

**Statistical tests:** frame times are not normal. Use non-parametric tests. Mann-Whitney U on per-frame samples between baseline and new build — flag if p < 0.01 and effect size meaningful (Cliff's delta > 0.2). Do not trust "average FPS went down 2%" — look at distribution.

Run on actual target hardware. PC dev box perf does not reliably predict console perf.

---

## Draw Call Optimization

**Instancing:** per-instance data in a structured buffer, index via `SV_InstanceID`. Single draw call for 10k instances of the same mesh. CPU cost: one `DrawIndexedInstanced` call (~1 microsecond). GPU cost: proportional to total vertices. Use for foliage, debris, rubble, characters with same skeleton.

```hlsl
StructuredBuffer<InstanceData> instances;
PSInput VSMain(VSInput v, uint instanceId : SV_InstanceID) {
    InstanceData id = instances[instanceId];
    // transform by id.worldMatrix
}
```

**Auto-batching:** runtime merges draws that share state (material, shader, vertex layout). Typical savings 2-5x draw call reduction. Requires stable sort key: shader hash → material hash → mesh hash → depth. Expensive per-frame sort is worth it — 10k draws sort in ~0.3 ms.

**GPU culling:** frustum + occlusion cull on compute, emit visible instance list to indirect draw buffer. Eliminates all CPU draw-call cost for culled geometry. Two-phase occlusion prevents disocclusion popping.

**Visibility buffer:** single-pass rasterization writes `(clusterId, triId)` per pixel. Deferred material resolve dispatches compute per material, reads visibility buffer, shades exactly once per pixel. Eliminates overdraw entirely. Best for Nanite-style micro-triangle content; overkill for simple scenes.

Target: <3000 draw calls per frame pre-batching on current-gen consoles. With GPU-driven pipeline and mesh shaders, draw call count is no longer a meaningful metric — meshlet / instance count is.

---

## See Also

- `RENDERING_AND_GRAPHICS.md` — rendering algorithms whose cost determines the GPU portion of the frame budget
- `CROSS_PLATFORM_AND_CONSOLE.md` — platform-specific backend details, GPU architecture per console, platform-specific profilers
