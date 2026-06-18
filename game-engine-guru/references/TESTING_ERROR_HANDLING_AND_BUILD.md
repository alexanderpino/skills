# Testing, Error Handling, and Build

Exceptions are banned in AAA engines. Asserts are tiered. Tests are mandatory. Coverage is measured. Sanitizers run every PR. If a change isn't tested, it doesn't exist.

## Table of Contents
- [Error Handling Philosophy](#error-handling-philosophy)
- [Assertion Tiers](#assertion-tiers)
- [Crash Reporting](#crash-reporting)
- [Graceful Degradation](#graceful-degradation)
- [TDD Workflow](#tdd-workflow)
- [GoogleTest Patterns](#googletest-patterns)
- [Code Coverage](#code-coverage)
- [Degenerate Input Testing](#degenerate-input-testing)
- [Integration Testing](#integration-testing)
- [Visual Regression Testing](#visual-regression-testing)
- [Performance Regression Testing](#performance-regression-testing)
- [Deterministic Testing](#deterministic-testing)
- [Sanitizer Strategy](#sanitizer-strategy)
- [Static Analysis](#static-analysis)
- [Build System](#build-system)
- [See also](#see-also)

---

## Error Handling Philosophy

**Exceptions are off.** `-fno-exceptions` / `/EHs-c-` is set engine-wide. Reasons:

1. Unwinding cost is unpredictable; frame-time jitter kills.
2. `throw` across DLL boundaries is undefined or platform-specific.
3. Console toolchains historically mishandle EH tables (Switch prior to SDK 18, PS5 older Clang).
4. The "happy path" branch prediction assumption is false in error-heavy code like asset loading.

Replace with `std::expected<T, E>` (C++23). Every fallible API returns a value or a typed error. `[[nodiscard]]` is mandatory.

```cpp
enum class LoadError : uint8_t {
    NotFound,
    Corrupt,
    VersionMismatch,
    OutOfMemory,
    IoError,
};

[[nodiscard]] std::expected<Texture, LoadError>
load_texture(std::string_view path) noexcept;

// Caller:
if (auto tex = load_texture("hero_albedo.tex"); tex) {
    renderer.bind(*tex);
} else {
    log_error("load failed: {}", to_string(tex.error()));
    return std::unexpected(tex.error());   // propagate
}
```

**Typed error enums, not integer codes.** The compiler catches exhaustiveness when you `switch` on them; `int32_t` error codes rot into `-17 means what again?`. Group per-subsystem: `LoadError`, `CookError`, `RenderError`. When you need to aggregate, wrap in `std::variant<A, B, C>` or a tagged union.

**Never silently swallow.** `.value_or(...)` is a tool for trivial defaults (color fallback, missing optional field), not for production error paths. Real errors must propagate to a logging boundary.

---

## Assertion Tiers

Three tiers, three budgets, three audiences.

```cpp
// Tier 1: dev-only. Compiled out in ship. Fires on impossible states.
#if ENGINE_CONFIG_DEV
  #define DEV_ASSERT(cond, ...) \
    do { if (!(cond)) { \
        detail::report_dev_assert(#cond, __FILE__, __LINE__, \
                                  std::stacktrace::current()); \
        ENGINE_DEBUGBREAK(); \
    }} while(0)
#else
  #define DEV_ASSERT(cond, ...) ((void)0)
#endif

// Tier 2: always on. Logs + telemetry, does NOT crash. For recoverable
// invariant breaches we want to know about in the field.
#define SHIP_ASSERT(cond, ...) \
    do { if (!(cond)) { \
        detail::report_ship_assert(#cond, __FILE__, __LINE__, \
                                   std::stacktrace::current(), \
                                   __VA_ARGS__); \
    }} while(0)

// Tier 3: always on. Crashes with minidump. For unrecoverable corruption.
#define FATAL_ASSERT(cond, ...) \
    do { if (!(cond)) { \
        detail::report_fatal_assert(#cond, __FILE__, __LINE__, \
                                    std::stacktrace::current(), \
                                    __VA_ARGS__); \
        detail::write_minidump(); \
        std::abort(); \
    }} while(0)
```

Use DEV_ASSERT for the vast majority of invariant checks — indexing, null pointers, argument validation on hot paths. It's free in ship.

Use SHIP_ASSERT where graceful degradation is possible but the state is unexpected — "material slot count exceeded, clamping." Users keep playing, telemetry captures.

Use FATAL_ASSERT where continuing would corrupt save data, leak security, or crash deterministically in three frames — "descriptor heap overflow," "allocator double-free detected."

**`<stacktrace>` from C++23** is the single best addition to error handling in a decade. Capture on assert, ship it with the telemetry payload. No more "call stack: [optimized out]".

---

## Crash Reporting

**Symbolicated minidumps** are the currency of live ops.

- **Google Breakpad / Crashpad** — open source, cross-platform, used by Chrome/Firefox/most engines. Crashpad is the newer architecture (out-of-process handler, crash-while-crashing resistant).
- **Custom minidump writers** — for specialty console requirements; every platform SDK ships one.

```
[client crash]
  → Crashpad handler captures dump + annotations (build id, level, user id)
  → uploads to ingest service (TLS, rate-limited)
  → symbolicate with stored .pdb / .debug archive keyed by build id
  → dedupe by top-5 frame hash
  → insert into Sentry / self-hosted dashboard
```

**GPU crashes need special handling.** The CPU is usually fine; the GPU is hung. Standard crash reporting misses them.

- **DX12 DRED** — Device Removed Extended Data. Enable via `ID3D12DeviceRemovedExtendedDataSettings1`; on TDR, `GetAutoBreadcrumbsOutput1` gives you the last ~1000 rendering commands submitted. Invaluable for "what draw call killed the GPU."
- **NVIDIA Aftermath** — SDK, integrates with Vulkan + DX12. Produces `.nv-gpudmp` files with shader-level fault info. Ship in dev builds, optionally in retail.
- **Vulkan VK_NV_device_diagnostic_checkpoints** — equivalent breadcrumb support across vendors.

**Telemetry pipeline:** client (batching, offline retry) → ingest (load-balanced, back-pressure) → dedupe (hash of normalized stack) → symbolicate (S3 of pdbs, keyed by GUID) → dashboard (top crashes, % sessions affected, first seen/last seen, assignee).

Budget: one top-10 crash per sprint has to be fixed, or you've lost control. That's the metric.

---

## Graceful Degradation

**Capability-based feature toggling.** On startup, query the platform: RT cores? Mesh shaders? SM 6.6? Adjust pipeline based on answers, not on hard-coded platform IDs.

```cpp
struct RenderCaps {
    bool supports_mesh_shaders;
    bool supports_raytracing;
    bool supports_bindless;
    bool supports_directstorage;
    uint32_t max_descriptor_heap;
};

RenderPipeline select_gi_backend(const RenderCaps& caps) {
    if (caps.supports_raytracing && caps.max_descriptor_heap >= 1'000'000)
        return RenderPipeline::LumenHW;
    if (caps.supports_mesh_shaders)
        return RenderPipeline::LumenSW;
    if (caps.supports_bindless)
        return RenderPipeline::SSGI;
    return RenderPipeline::BakedGI;
}
```

**LOD fallbacks:** GI is the canonical example — Lumen HW RT → Lumen SW (signed distance fields) → Screen-Space GI → baked lightmaps → ambient. Each layer must produce a playable experience; the delta between adjacent layers is quality, not correctness.

**Null backends** for automated testing:
- `NullRenderer` — accepts all commands, records counts, produces a hash. Used in headless CI to verify draw submission without a GPU.
- `NullAudio` — same for audio; verify bus routing and voice count.
- `NullInput` — deterministic scripted input for replay tests.

Null backends are production code, tested, shipped in dev builds. They're how you run 10,000 tests in 30 minutes on a CI box without a display.

---

## TDD Workflow

**Red → Green → Refactor.** Standard. In engine work specifically:

1. **Red** — write the failing test against the API you wish existed. Don't look at the existing implementation.
2. **Green** — smallest change to make it pass. Ugly is fine. Globals are fine temporarily.
3. **Refactor** — clean up without changing behavior. Tests guard you.

**Testable engine code:**

- **Interfaces at seams.** `IRenderBackend`, `IAllocator`, `IFileSystem` — swappable. Runtime uses D3D12, tests use Null.
- **Dependency injection.** No `Renderer::get()` singletons in hot paths. Pass the renderer into constructors. "Service locator" is a test anti-pattern; it couples tests to global state.
- **Pure functions where possible.** Math, data transformations, algorithms. They're trivially testable. The stateful parts shrink to a thin surface.
- **Avoid `static` state.** `static` locals in function bodies are landmines in parallel tests.

```cpp
// Bad: uses singleton, untestable without full engine init
void apply_damage(EntityId e, float amt) {
    auto* world = World::instance();
    auto* health = world->get<Health>(e);
    health->hp -= amt;
    AudioSystem::instance().play("damage.wav");
}

// Good: injected, pure-ish, tested in 20 lines
void apply_damage(World& w, IAudio& audio, EntityId e, float amt) {
    if (auto* health = w.get<Health>(e)) {
        health->hp -= amt;
        audio.play("damage.wav"_hash);
    }
}
```

---

## GoogleTest Patterns

**Arrange / Act / Assert** blocks, visually separated:

```cpp
TEST(Transform, CompositionIsAssociative) {
    // Arrange
    Transform a = Transform::translation({1, 0, 0});
    Transform b = Transform::rotation_y(1.5708f);
    Transform c = Transform::scale(2.0f);
    Vec3 p{1, 2, 3};

    // Act
    Vec3 lhs = (a * (b * c)).apply(p);
    Vec3 rhs = ((a * b) * c).apply(p);

    // Assert
    EXPECT_NEAR(lhs.x, rhs.x, 1e-5f);
    EXPECT_NEAR(lhs.y, rhs.y, 1e-5f);
    EXPECT_NEAR(lhs.z, rhs.z, 1e-5f);
}
```

**Parameterized tests** for sweep coverage:

```cpp
class QuantizeTest : public ::testing::TestWithParam<int> {};

TEST_P(QuantizeTest, RoundTripPreservesValue) {
    float original = static_cast<float>(GetParam()) / 100.0f;
    uint16_t q = quantize_unorm16(original);
    float restored = dequantize_unorm16(q);
    EXPECT_NEAR(original, restored, 1.0f / 65535.0f);
}

INSTANTIATE_TEST_SUITE_P(UnormSweep, QuantizeTest,
    ::testing::Range(0, 101, 1));
```

**Typed tests** for templates:

```cpp
template <typename T> class AllocatorTest : public ::testing::Test {};
using AllocatorTypes = ::testing::Types<
    LinearAllocator, StackAllocator, PoolAllocator<64>, TLSFAllocator>;
TYPED_TEST_SUITE(AllocatorTest, AllocatorTypes);

TYPED_TEST(AllocatorTest, AllocatedPointersAreAligned) {
    TypeParam a(1024 * 1024);
    for (size_t align : {8, 16, 32, 64, 128, 256}) {
        void* p = a.allocate(128, align);
        ASSERT_NE(p, nullptr);
        EXPECT_EQ(reinterpret_cast<uintptr_t>(p) % align, 0u);
    }
}
```

**ECS fixtures** — fresh world per test, never share:

```cpp
class EcsTest : public ::testing::Test {
protected:
    World world;
    void SetUp() override { world = World{}; }
};

TEST_F(EcsTest, AddRemoveComponentChangesArchetype) {
    auto e = world.create();
    EXPECT_EQ(world.archetype_of(e), Archetype::empty());
    world.add<Transform>(e);
    EXPECT_NE(world.archetype_of(e), Archetype::empty());
}
```

**Death tests** for `FATAL_ASSERT`:

```cpp
TEST(HandleDeath, DereferencingStaleHandleFatals) {
    Registry r;
    auto h = r.create();
    r.destroy(h);
    ASSERT_DEATH({ r.resolve(h); }, "stale handle");
}
```

---

## Code Coverage

**Targets:**
- 85% line coverage for pure / math / data-structure code.
- 80% for systems with I/O or GPU dependencies.
- 70% minimum for any production code; below that blocks merge.

**Tooling:**
- Clang/GCC: `--coverage` → `llvm-cov gcov` / `lcov`.
- MSVC: OpenCppCoverage or Visual Studio's built-in instrumentation.
- Reporting: Codecov/Coveralls SaaS, or self-hosted `lcov` + `genhtml` for on-prem.

**CI gates:** coverage *delta* must not regress. Raw 80% with a 5% drop is worse than raw 78% with a 0.1% drop.

**Exclusions** (via `.codecov.yml` or source pragmas):
- Platform-specific shims (`platform/ps5/*.cpp`) run only in console CI.
- Auto-generated code (reflection tables, shader headers).
- DCC plugins (Maya/Houdini) tested via their host apps.
- Debug-only visualizers.

```yaml
# .codecov.yml excerpt
coverage:
  status:
    project:
      default:
        target: 80%
        threshold: 0.5%   # allow 0.5% drop before failing
  ignore:
    - "third_party/**"
    - "**/*.generated.cpp"
    - "platform/ps5/**"
    - "platform/xsx/**"
```

---

## Degenerate Input Testing

**Mandatory input classes for every numeric API:**

| Class          | Values                                                     |
|----------------|------------------------------------------------------------|
| Zero           | `0`, `0.0f`, `{}` (default-constructed)                   |
| Empty          | empty container, empty string, null span                   |
| Null           | `nullptr`, invalid handle, dangling weak_ptr               |
| NaN / Inf      | `NaN`, `+Inf`, `-Inf`, `-0.0f`                            |
| Overflow       | `INT_MAX`, `INT_MIN`, `SIZE_MAX`, `FLT_MAX`               |
| Negative       | `-1`, `-0.001f` on unsigned-expected inputs               |
| Boundary       | `size-1`, `size`, `size+1` off-by-one positions           |
| Large          | 10M-element container, 4GB allocation request             |

If the function doesn't handle these, **it's incomplete**. Return `std::unexpected(InvalidArg)`, clamp to a valid range, or `DEV_ASSERT` with a clear message. Pick one; document which.

```cpp
TEST(Vec3, NormalizeOfZeroReturnsError) {
    auto r = Vec3{0, 0, 0}.try_normalize();
    ASSERT_FALSE(r.has_value());
    EXPECT_EQ(r.error(), MathError::DegenerateInput);
}

TEST(Allocator, ZeroSizeRequestReturnsValidPointer) {
    // C malloc tradition: zero size returns non-null, distinct from null.
    LinearAllocator a(1024);
    void* p = a.allocate(0, 16);
    EXPECT_NE(p, nullptr);
}
```

---

## Integration Testing

Unit tests don't catch the `A-to-B-to-C` bugs. Integration tests do.

- **ECS query integration** — spawn 10k entities across 30 archetypes, run a real system, verify `Position + Velocity` query matches expected set.
- **Render pass integration** — null backend + real scene, verify draw-call count, descriptor table correctness, render-graph edge validation.
- **Physics step** — spawn rigid bodies, step simulation, assert positions after N steps match golden reference.
- **Audio routing** — post events, assert correct bus mixing, voice-stealing policy behavior under oversubscription.
- **Save/load** — serialize world, reload, deep-compare structural equality.

These run in a nightly CI job (15-30 min budget) separate from per-PR tests (3-5 min budget).

---

## Visual Regression Testing

Screenshot compare is the only sane way to catch renderer regressions.

**Pipeline:**
1. Canonical test scenes checked in, each with camera trajectory.
2. Nightly CI renders each scene on each target platform, 1080p, deterministic seed.
3. Compare against per-platform golden image.
4. Metric: **FLIP** (NVIDIA, perceptual, handles exposure better than SSIM) or **ΔE2000** for HDR. SSIM acceptable for LDR.
5. Fail if >1% of pixels exceed tolerance, or if FLIP mean > 0.05.

**Golden image management:**
- Stored in Git-LFS / Perforce, **per platform** (PC-Vulkan, PC-DX12, PS5, XSX, Switch differ; don't share).
- Rotation policy: 30-day retention for failing diffs, permanent for goldens.
- Update process: developer proposes new golden → art/tech-art review → merged with justification in commit message.

**Tolerance tuning:** 1% pixel delta catches 95% of real bugs. TAA and noise-based effects blow this up; mask them with stable-frame policies (disable TAA, fixed RNG seed) in test scenes.

---

## Performance Regression Testing

Optimize under measurement or not at all.

**Google Benchmark** for micro:

```cpp
static void BM_TransformCompose(benchmark::State& state) {
    Transform a = Transform::translation({1, 2, 3});
    Transform b = Transform::rotation_y(0.5f);
    for (auto _ : state) {
        Transform c = a * b;
        benchmark::DoNotOptimize(c);
    }
}
BENCHMARK(BM_TransformCompose);
```

**Frame-time benchmarks** for end-to-end:
- Deterministic replay: fixed seed, fixed input stream, fixed camera path.
- Record `cpu_ms`, `gpu_ms`, `frame_ms`, peak VRAM, peak heap per frame.
- Run 5 iterations, discard warmup, aggregate percentiles (p50, p95, p99).

**Statistical comparison:** Mann-Whitney U test (non-parametric, doesn't assume normality). Alert if new median shifts by >2% at p<0.01. Plain mean diff is noisy; percentile diffs catch tail regressions (hitches).

**CI alerts:** post to Slack/Teams on regression, assign to the PR author. Performance is a gate, not a suggestion.

---

## Deterministic Testing

Determinism is a feature. Design it in.

- **MockClock** — injectable time source. Tests advance time manually; no `std::chrono::system_clock::now()` in production code except behind the clock interface.
- **MockRandom** — seeded PRNG, swappable per-test. Production uses `pcg64` or `xoshiro256**`; tests use the same with known seeds.
- **NullDevice** — deterministic file system for fixture data.

**Replay-based testing:**

```cpp
// Record
Replay r;
r.seed(0xDEADBEEF);
for (int i = 0; i < 1000; ++i) {
    r.capture_input(pad.sample());
    world.tick(16.67f / 1000.f);
}
r.save("replay.bin");

// Replay
Replay r = Replay::load("replay.bin");
World w;
w.seed(r.seed());
for (auto& frame : r.frames()) {
    w.inject_input(frame.input);
    w.tick(frame.dt);
}
FATAL_ASSERT(w.state_hash() == r.expected_final_hash());
```

**Cross-platform bit-exact verification** — same replay on PS5 / XSX / PC should produce identical state hashes. Floating-point determinism requires: `/fp:strict` (MSVC) or `-ffp-model=strict` (Clang), no `--fast-math`, identical SIMD paths (no AVX-only shortcuts), fixed libm (don't use platform-specific `sinf`). Expensive but worth it for gameplay simulation, replays, and rollback netcode.

---

## Sanitizer Strategy

Run every PR. Different sanitizers catch different bugs; none is optional.

| Sanitizer | Catches                                              | When                         |
|-----------|------------------------------------------------------|------------------------------|
| **ASAN**  | Heap/stack out-of-bounds, use-after-free, leaks      | Every PR, unit+integration   |
| **UBSAN** | Signed overflow, null deref, invalid shift, UB       | Every PR, combined with ASAN |
| **TSAN**  | Data races, deadlocks                                | Nightly, threaded subsystems |
| **MSAN**  | Reads of uninitialized memory (Linux/Clang only)     | Nightly where supported      |

**Build flags** (Clang):
```
-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all
```

**Suppression files** — every suppression must have an attached bug ID and owner. Unchecked suppressions rot. Audit quarterly.

```
# asan_suppressions.txt
leak:third_party/fmod/.*       # BUG-1234, fmod known leak, fixed in 2.03
race:third_party/imgui/.*      # BUG-1250, investigating
```

**TSAN caveats:** doesn't play well with some kernel drivers, custom page faults, coroutines with stack switching. Mark bespoke sync primitives with annotations (`__tsan_acquire`, `__tsan_release`) or TSAN won't understand them and will false-positive.

---

## Static Analysis

**clang-tidy** — run on every PR, fail on new warnings:

```yaml
# .clang-tidy
Checks: >
  -*,
  bugprone-*,
  performance-*,
  readability-*,
  modernize-*,
  cert-*,
  cppcoreguidelines-*,
  -modernize-use-trailing-return-type,
  -readability-identifier-length,
  -cppcoreguidelines-avoid-magic-numbers
WarningsAsErrors: "bugprone-*,performance-*,cert-*"
```

**PVS-Studio** — commercial, deeper dataflow than clang-tidy. Licensing per engineer is cheaper than one late-project crash bug. Run nightly, not per-PR (slow).

**Custom clang AST checks** — when you need project-specific rules ("no `new` outside allocators," "`SHIP_ASSERT` arg must be side-effect free," "no global mutable state"). Worth writing once the team is >20 engineers.

**CI gating:** diff new warnings from base branch. Zero new warnings on the touched files. Old warnings tracked as a debt ledger, burned down quarterly.

---

## Build System

**CMake 3.25+** is the lingua franca. Alternatives (Bazel, Meson, SCons, custom) have niches but lose on ecosystem. Targets over directories. `target_*` everything.

```cmake
cmake_minimum_required(VERSION 3.28)
project(engine CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(engine.core STATIC
    src/core/allocator.cpp
    src/core/handle.cpp
    src/core/stacktrace.cpp
)
target_include_directories(engine.core PUBLIC include)
target_compile_features(engine.core PUBLIC cxx_std_23)
target_compile_options(engine.core PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX /permissive- /EHs-c- /Zc:preprocessor>
    $<$<CXX_COMPILER_ID:Clang,GCC>:-Wall -Wextra -Werror -fno-exceptions -fno-rtti>)
target_link_libraries(engine.core PUBLIC fmt::fmt eastl::eastl)
```

**CMakePresets.json** — capture per-platform, per-config presets so the team runs identical builds:

```json
{
  "version": 6,
  "configurePresets": [
    {
      "name": "pc-x64-dev",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/out/pc-x64-dev",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "RelWithDebInfo",
        "ENGINE_CONFIG_DEV": "ON",
        "ENGINE_ENABLE_ASAN": "ON"
      }
    },
    {
      "name": "pc-x64-ship",
      "inherits": "pc-x64-dev",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "ENGINE_CONFIG_DEV": "OFF",
        "ENGINE_ENABLE_ASAN": "OFF",
        "ENGINE_LTO": "ON"
      }
    }
  ]
}
```

**Distributed builds:**
- **FASTBuild** — open, fast, BFF config (dedicated DSL); integrates with Visual Studio via vcxproj generator. Scales linearly to ~40 agents.
- **IncrediBuild** — commercial, MSBuild-native; easier drop-in, more expensive.
- **sccache** — content-addressed compiler cache; shared across CI and devs; pairs with either.

**Shader compilation in the build:**

```cmake
function(compile_shader STAGE HLSL ENTRY OUT)
    add_custom_command(
        OUTPUT ${OUT}
        COMMAND ${DXC_PATH}
                -T ${STAGE}_6_6
                -E ${ENTRY}
                -Fo ${OUT}
                -Zi -Qembed_debug
                ${HLSL}
        DEPENDS ${HLSL}
        COMMAND_EXPAND_LISTS
        VERBATIM)
endfunction()
```

**CI/CD pipeline** (generic, platform-appropriate variants):
1. Lint (clang-format check, clang-tidy changed-files).
2. Build (all presets in parallel).
3. Unit + integration tests (all targets with null backends).
4. Sanitizer builds (ASAN+UBSAN per PR; TSAN nightly).
5. Cook assets (incremental against DDC).
6. Runtime smoke + perf regression.
7. Artifact upload (symbolicated binaries, cooked paks).

Gate merge on 1-4. Nightly on 5-7.

---

## See also

- `ASSET_PIPELINE_AND_COOKER.md` — cooker uses `std::expected`, CI cooks assets against DDC, visual regression scenes.
- `EDITOR_AND_TOOLING.md` — integration tests cross the C ABI boundary, editor also runs under sanitizers.
- `CPP23_26_AND_MODERN_PATTERNS.md` — `std::expected` idioms, `<stacktrace>` usage in asserts, C++23 compiler flag selection.
