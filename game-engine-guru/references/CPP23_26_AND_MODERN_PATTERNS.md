# C++23/26 and Modern Patterns

> **C++23 = Production Standard. C++26 = Horizon Only.**
>
> Console toolchains (PS5 Clang SDK, Switch NVN/Clang, Xbox GDK MSVC) trail desktop by 1-2 standards. C++26 features MUST be feature-test-macro-gated with a working C++23 fallback path — otherwise console builds break. Treat C++26 as design-aware, deployment-forbidden until SDK support lands.

## Table of Contents
- [C++23 — Production Standard](#c23--production-standard)
- [C++26 — Horizon Only (gated)](#c26--horizon-only-gated)
- [EASTL & Container Strategy](#eastl--container-strategy)
- [Compile-Time Computation](#compile-time-computation)
- [Modules vs Headers](#modules-vs-headers)
- [Concepts & Constraints](#concepts--constraints)
- [Coroutines for Async](#coroutines-for-async)
- [Smart Pointer Strategy](#smart-pointer-strategy)
- [See also](#see-also)

---

## C++23 — Production Standard

C++23 is what ships. Everything here is in MSVC 19.38+, Clang 17+, GCC 13+, and — critically — in the current PS5 SDK Clang, GDK MSVC, and Switch NVN/Clang toolchains. Use it freely.

### `std::expected<T, E>` — error handling backbone

The foundation. Replaces exception-based error paths across the engine. See also `TESTING_ERROR_HANDLING_AND_BUILD.md` for the full discipline.

```cpp
[[nodiscard]] std::expected<Mesh, LoadError>
load_mesh(std::string_view path) noexcept {
    auto file = open_file(path);
    if (!file) return std::unexpected(LoadError::NotFound);

    auto header = read_header(*file);
    if (!header) return std::unexpected(header.error());
    if (header->magic != MESH_MAGIC)
        return std::unexpected(LoadError::Corrupt);

    return parse_mesh_body(*file, *header);   // expected<Mesh, LoadError>
}

// Monadic composition:
auto result = load_mesh("hero.mesh")
    .and_then([](Mesh m) { return upload_to_gpu(std::move(m)); })
    .transform([](GpuMesh g) { return g.handle; })
    .or_else([](LoadError e) -> std::expected<MeshHandle, LoadError> {
        log_warn("mesh load failed: {}, using placeholder", to_string(e));
        return placeholder_mesh();
    });
```

### Deducing `this` — CRTP without the pain

```cpp
// Before C++23 (CRTP boilerplate):
template<class Derived>
struct Printable {
    void print() const { static_cast<const Derived*>(this)->print_impl(); }
};
struct MyType : Printable<MyType> {  // ugly, infectious
    void print_impl() const;
};

// C++23:
struct MyType {
    void print(this auto const& self) { self.print_impl(); }
    void print_impl() const;
};
```

Use for: fluent builders, container method chaining, policy-based design, `operator[]` and `operator()` that preserve ref-qualifiers without triplicating overloads.

### Multidimensional subscript `operator[](a, b, c)`

```cpp
class Grid3D {
    std::vector<float> data_;
    size_t nx_, ny_, nz_;
public:
    constexpr float& operator[](size_t x, size_t y, size_t z) noexcept {
        return data_[x + nx_ * (y + ny_ * z)];
    }
    constexpr float  operator[](size_t x, size_t y, size_t z) const noexcept {
        return data_[x + nx_ * (y + ny_ * z)];
    }
};
Grid3D g(...);
g[4, 5, 6] = 1.0f;   // natural; no more g(4,5,6) or g[4][5][6]
```

Use for: voxel grids, 3D LUTs, matrix views, texture tile access.

### `std::mdspan` — bounds-safe multi-dim views

Non-owning view over N-dim data. Customizable layout (row-major, col-major, strided, tiled). Free in release, bounds-checked in debug with custom accessors.

```cpp
void blur3x3(std::mdspan<float, std::extents<size_t, std::dynamic_extent, std::dynamic_extent>> img) {
    const auto h = img.extent(0), w = img.extent(1);
    for (size_t y = 1; y + 1 < h; ++y)
    for (size_t x = 1; x + 1 < w; ++x) {
        float s = 0;
        for (int dy = -1; dy <= 1; ++dy)
        for (int dx = -1; dx <= 1; ++dx)
            s += img[y + dy, x + dx];
        img[y, x] = s / 9.f;
    }
}
```

### `<stacktrace>` — first-class crash reporter integration

```cpp
void report_assert_failure(const char* cond, const char* file, int line) {
    auto st = std::stacktrace::current(/*skip*/1);
    crash_report::submit({
        .condition = cond,
        .file      = file,
        .line      = line,
        .stack     = std::to_string(st),
    });
}
```

Zero dependencies on platform PDB magic for the capture — you still need symbol servers to symbolicate after ingest, but capture is standard.

### `if consteval` and extended constexpr

```cpp
constexpr float fast_sqrt(float x) noexcept {
    if consteval {
        // compile-time path: use a slow-but-exact Newton iteration
        return compile_time_newton_sqrt(x);
    } else {
        // runtime: hardware intrinsic
        return _mm_cvtss_f32(_mm_sqrt_ss(_mm_set_ss(x)));
    }
}
```

C++23 adds `<cmath>` constexpr for most functions — bake LUTs and curves at compile time instead of on first boot.

---

## C++26 — Horizon Only (gated)

**Every C++26 usage below must be feature-test-macro guarded with a working C++23 fallback.** Consoles will not support these for 12-24 months after desktop lands them.

### Static Reflection

The single most impactful feature coming. Replaces hand-written `ComponentTraits`, serialization visitors, RPC descriptors. Until it ships on all target SDKs, the engine uses a codegen tool (Python + libclang) that emits equivalent templates — the *shape* of `ComponentTraits` stays identical, so adopting reflection later is a mechanical swap.

```cpp
#if defined(__cpp_reflection) && __cpp_reflection >= 202506L
// C++26 path (P2996): reflect directly on the type. FTM is __cpp_reflection.
template<class T> struct ComponentTraits {
    static constexpr std::string_view name = [:name_of(^^T):];
    static constexpr auto fields = []{
        return std::apply([]<auto... ms>(){
            return std::tuple{ Field{ [:name_of(ms):], ms }... };
        }, nonstatic_data_members_of(^^T));
    }();
};
#else
// C++23 fallback: codegen emits explicit specializations
// (see tools/gen_reflection.py; run as CMake pre-build step)
template<class T> struct ComponentTraits;        // primary = undefined
// specializations generated per reflected type in *.generated.hpp
#endif
```

Both branches expose the identical API (`name`, `fields`). Downstream code — property inspector, serializer, network marshaller — is written once against that API and doesn't care which branch compiled.

### Contracts

```cpp
#if defined(__cpp_contracts)   // P2900 contracts (FTM __cpp_contracts); pre/post are
                               // function-contract specifiers, NOT the contract_assert statement
float safe_divide(float a, float b)
    pre(b != 0.0f)
    post(r: std::isfinite(r))
{
    return a / b;
}
#else
float safe_divide(float a, float b) noexcept {
    DEV_ASSERT(b != 0.0f, "division by zero");
    float r = a / b;
    DEV_ASSERT(std::isfinite(r), "non-finite result");
    return r;
}
#endif
```

Contract violation handlers integrate with the crash reporter the same way asserts do. Contracts don't replace asserts — they add a declarative layer the compiler can exploit for optimization and static analysis.

### Pattern Matching (`inspect`) — NOT in C++26

Pattern matching (P2688/P2392, `inspect`) was **not adopted into C++26** — it has no standard feature-test macro and no shipping compiler. Treat it as post-C++26 horizon only; the `std::visit` + `overloaded` fallback below is the actual production approach today and for the foreseeable future. The speculative branch is shown purely to illustrate the eventual shape and will never compile (the guard is permanently false until/unless the proposal lands and a real FTM is assigned).

```cpp
#if defined(__cpp_pattern_matching)   // hypothetical — no such macro exists yet (post-C++26)
auto describe(const Shape& s) -> std::string {
    return inspect (s) {
        <Circle>    [r]          => std::format("circle r={}", r);
        <Rectangle> [w, h]       => std::format("rect {}x{}", w, h);
        <Polygon>   [verts] if (verts.size() == 3) => "triangle";
        _                        => "unknown";
    };
}
#else
auto describe(const Shape& s) -> std::string {
    return std::visit(overloaded{
        [](const Circle& c)    { return std::format("circle r={}", c.r); },
        [](const Rectangle& r) { return std::format("rect {}x{}", r.w, r.h); },
        [](const Polygon& p)   {
            return p.verts.size() == 3 ? std::string{"triangle"} : "polygon";
        },
    }, s);
}
#endif
```

### `std::execution` (Senders/Receivers)

Composable async. Replaces most bespoke future/promise code.

```cpp
#if defined(__cpp_lib_senders)   // P2300 std::execution. FTM is __cpp_lib_senders —
                                 // NOT __cpp_lib_execution (that's C++17 parallel-algorithm policies)
namespace ex = std::execution;
auto work = ex::schedule(io_sched)
          | ex::then ([]{ return load_file("a.bin"); })
          | ex::then ([](auto f){ return parse(f); })
          | ex::continues_on(gpu_sched)
          | ex::then ([](auto p){ return upload(p); });
auto handle = ex::start_detached(std::move(work));
#else
// Fallback to in-house job system. Same task graph shape.
auto h = jobs.schedule(JobPriority::IO, []{ return load_file("a.bin"); })
             .then(JobPriority::CPU, parse)
             .then(JobPriority::GPU, upload);
#endif
```

### constexpr Containers

`std::vector`, `std::string` in constant expressions. Usable for compile-time string-table construction, test-data builders, build-time level validation. C++23 fallback: `std::array` + hand-rolled `constexpr_vector<T, N>`.

---

## EASTL & Container Strategy

`std::` containers have two critical defects for AAA:

1. **Allocator model is baked into the type.** `std::vector<T, A>` and `std::vector<T, B>` are different types. Moving across allocator boundaries requires element-wise copy. Engine code needs stateful allocators that compare equal structurally — `std::` forbids this cleanly.
2. **Exception guarantees.** `std::vector::push_back` requires strong exception safety; even with `-fno-exceptions`, some implementations emit dead EH tables. Size bloat.

Solution: **EASTL** (or a homegrown equivalent — Unreal's `TArray`, Frostbite's `eastl`-derived containers).

```cpp
#include <EASTL/vector.h>
#include <EASTL/hash_map.h>

using eastl::vector;
using eastl::hash_map;

vector<Entity, FrameAllocator> per_frame_entities;   // resets every frame
hash_map<AssetId, Asset*, ScratchAllocator> lookup;  // thread-local scratch
```

Engine aliases (thin wrappers or `using`) live in `core/containers.h`. Migration path from `std::`:
1. Introduce `engine::vector = eastl::vector` alongside existing `std::vector` usage.
2. Convert hot-path data structures first (ECS storage, render queues, scene graph).
3. Leave `std::` for interop boundaries (filesystem APIs, third-party SDK parameters).
4. Never bridge via `reinterpret_cast` between `std::vector` and `eastl::vector` — their layouts are ABI-distinct. Copy or move element-by-element.

**Compile-time type-punning disabled:** `if constexpr (std::is_trivially_copyable_v<T>)` inside copy loops lets the compiler pick `memcpy`, which is safe; bit-cast between distinct container shells is not.

---

## Compile-Time Computation

Move work from boot to compile. Builds are slow once; boots are slow forever.

**Hashing at compile time:**

```cpp
constexpr uint64_t fnv1a_64(std::string_view s) noexcept {
    uint64_t h = 1469598103934665603ull;
    for (char c : s) { h ^= uint8_t(c); h *= 1099511628211ull; }
    return h;
}
constexpr uint64_t operator""_id(const char* s, size_t n) noexcept {
    return fnv1a_64({s, n});
}

switch (evt.type_id) {
    case "OnDeath"_id:   handle_death();   break;
    case "OnDamage"_id:  handle_damage();  break;
    // compiler evaluates the hash at compile time; runtime is pure integer compare
}
```

For stronger hashes (collision-resistant event IDs, asset GUIDs) use constexpr xxHash or BLAKE3 — the critical property is that they run in `consteval` contexts.

**LUT generation:**

```cpp
constexpr auto build_srgb_to_linear() {
    std::array<float, 256> t{};
    for (size_t i = 0; i < 256; ++i) {
        float s = float(i) / 255.f;
        t[i] = s <= 0.04045f ? s / 12.92f
                             : std::pow((s + 0.055f) / 1.055f, 2.4f);
    }
    return t;
}
inline constexpr auto SRGB_LUT = build_srgb_to_linear();
```

**Frozen maps for type registration:** `frozen::unordered_map` or a hand-rolled `constexpr` perfect-hash — zero runtime construction.

---

## Modules vs Headers

Support matrix as of 2026:

| Compiler   | Status                            | Build-system integration                 |
|------------|-----------------------------------|------------------------------------------|
| MSVC       | Solid, ship-ready                 | Full (MSBuild, CMake 3.28+)              |
| Clang 18+  | Usable, minor bugs                | CMake 3.28+ with Ninja 1.11+             |
| GCC 14+    | Partial, header units incomplete  | CMake experimental                       |
| PS5 Clang  | **Follow SDK** — may lag Clang 17 | May need to disable                       |
| Switch     | Not validated                      | Disable                                  |
| Xbox GDK   | Follows MSVC                       | Enable cautiously                        |

**Pragmatic adoption:** start with leaf libraries (math, containers, small utility modules). Don't modularize the engine root until every target toolchain is green. Provide both `.ixx`/`.cppm` and traditional headers during transition — CMake `CXX_MODULE_SETS` can emit both.

**Build implications:**
- BMI (binary module interface) files are compiler-specific and not distributable across vendors.
- Distributed builds (FASTBuild, IncrediBuild) need explicit module graph support — check your version.
- Incremental builds become finer-grained (touching a `.cpp` doesn't force rebuild of dependents like a header does). But editing the interface unit of a hot-path module rebuilds the world.
- `include` translation inside modules is slow; migrate to `import` over time.

**When NOT to use modules yet:**
- Any code that must ship to all three current-gen consoles this year.
- Any code depending on macros exported across boundaries (modules don't export macros; refactor to constants first).
- Any team without tight build-system ownership — modules are where build systems go to die.

---

## Concepts & Constraints

Concepts replace SFINAE and enable legible error messages.

```cpp
template<class T>
concept Component = std::is_trivially_copyable_v<T>
                 && std::is_standard_layout_v<T>
                 && sizeof(T) <= 256;       // archetype storage constraint

template<class A>
concept Allocator = requires(A a, size_t n, size_t align) {
    { a.allocate(n, align) } -> std::same_as<void*>;
    { a.deallocate(nullptr, n) } noexcept;
    { a.owns(nullptr) } -> std::convertible_to<bool>;
};

template<class T>
concept Serializable = requires(const T& v, BinaryWriter& w, BinaryReader& r) {
    { serialize(v, w) } -> std::same_as<std::expected<void, SerializeError>>;
    { deserialize(r) } -> std::same_as<std::expected<T, SerializeError>>;
};

// Terse syntax — prefer for simple cases:
auto sum(std::integral auto... xs) { return (xs + ...); }

// Requires clause — preferred when constraints are compound:
template<class T> requires Component<T> && Serializable<T>
void register_component();
```

Concepts matter most in templated code humans read. The compile-error delta between a constrained and unconstrained template on failure is worth the initial investment by itself.

---

## Coroutines for Async

C++20 coroutines, mature by C++23. Custom promise types let us frame-bind, pool allocate, and prioritize.

```cpp
struct FrameTask {
    struct promise_type {
        FrameTask get_return_object() { return FrameTask{this}; }
        std::suspend_never initial_suspend() noexcept { return {}; }
        FinalAwaiter       final_suspend()   noexcept { return {}; }
        void return_void() noexcept {}
        void unhandled_exception() noexcept { FATAL_ASSERT(false, "throw in coro"); }

        // Frame-affine scheduling: resume on owning frame's scheduler.
        void* operator new(size_t n) { return FrameAllocator::instance().alloc(n); }
        void  operator delete(void* p, size_t) noexcept { /* reset at frame end */ }
    };
    ...
};

FrameTask load_level(std::string_view name) {
    auto manifest = co_await read_file_async(name);
    if (!manifest) { log_error("manifest load failed"); co_return; }

    auto parsed = co_await parse_async(*manifest);
    auto meshes = co_await load_meshes(parsed->mesh_refs);
    co_await upload_to_gpu(std::move(meshes));

    co_await scene_ready_barrier();
    emit_event("LevelLoaded"_id);
}
```

Use cases:
- **Async I/O** — wait on file reads without thread-pool overhead.
- **Animation sequences** — `co_await anim.notify("footstep")` is more readable than notify tracks with callbacks.
- **Dialogue trees** — state machines collapse into straight-line coroutines.
- **Scripted sequences** — cutscenes, tutorial beats, multi-frame game logic.

**Custom promise type essentials:** `operator new`/`delete` on a pool allocator (default heap is catastrophic for thousands of concurrent coros), exception policy (we fatal — exceptions are off), and the awaiter set that hooks into the engine's scheduler.

---

## Smart Pointer Strategy

Four categories, rigidly enforced via lint and review:

**1. `std::unique_ptr<T>` — default for singular ownership.**
Any time you `new`, it goes into a `unique_ptr`. No exceptions. Near-zero overhead, move-only, clear semantics.

```cpp
std::unique_ptr<IRenderBackend> backend = make_backend(caps);
```

**2. `std::shared_ptr<T>` — only when shared ownership is actually real.**
Rare in engine code. Legitimate uses: reference-counted asset refs at the *editor layer* (not runtime), third-party SDK handoffs that require it. Every `shared_ptr` in a review needs to justify itself. Control block allocates separately (unless `make_shared`); refcounts are atomic; cacheline pressure on hot paths is meaningful.

**3. Raw `T*` — non-owning observer.**
Strictly non-owning. Points into data owned elsewhere (arena, container, ECS storage). Lifetime guaranteed by context. Document the owner in a comment.

```cpp
void render_system(World* world, IRenderBackend* backend) noexcept;
// both non-owning; engine owns both for lifetime of the frame
```

**4. `Handle<Tag>` — generational index for gameplay references.**

The workhorse. A `Handle<Entity>` or `Handle<Texture2D>` is a 64-bit POD: `{ uint32_t index; uint32_t generation; }`. Resolves through a registry; stale handles detect automatically.

```cpp
template<class Tag>
struct Handle {
    uint32_t index      = 0;
    uint32_t generation = 0;
    constexpr bool is_null() const noexcept { return index == 0 && generation == 0; }
    friend auto operator<=>(Handle, Handle) = default;
};

template<class T, class Tag>
class Registry {
    struct Slot { uint32_t generation; T value; bool alive; };
    std::vector<Slot> slots_;
    std::vector<uint32_t> free_;
public:
    Handle<Tag> create(T v) {
        uint32_t idx;
        if (!free_.empty()) { idx = free_.back(); free_.pop_back(); }
        else { idx = slots_.size(); slots_.push_back({1, {}, false}); }
        slots_[idx].value = std::move(v);
        slots_[idx].alive = true;
        return { idx, slots_[idx].generation };
    }
    void destroy(Handle<Tag> h) {
        if (!valid(h)) return;
        slots_[h.index].alive = false;
        ++slots_[h.index].generation;    // invalidates outstanding handles
        free_.push_back(h.index);
    }
    std::expected<T*, HandleError> resolve(Handle<Tag> h) noexcept {
        if (h.index >= slots_.size())                   return std::unexpected(HandleError::OutOfRange);
        if (slots_[h.index].generation != h.generation) return std::unexpected(HandleError::Stale);
        if (!slots_[h.index].alive)                     return std::unexpected(HandleError::Destroyed);
        return &slots_[h.index].value;
    }
    bool valid(Handle<Tag> h) const noexcept {
        return h.index < slots_.size()
            && slots_[h.index].generation == h.generation
            && slots_[h.index].alive;
    }
};
```

Handles survive serialization, hot-reload, save/load. They're the default reference for any cross-system gameplay link.

**5. `StrongID<Tag>` — phantom-typed identifier.**
Not a pointer at all — a wrapper around a stable ID (hash, GUID, 64-bit integer). Tag prevents mixing.

```cpp
template<class Tag>
struct StrongID {
    uint64_t value;
    friend auto operator<=>(StrongID, StrongID) = default;
};
using AssetId    = StrongID<struct AssetTag>;
using EntityGuid = StrongID<struct EntityTag>;
using EventId    = StrongID<struct EventTag>;

void f(AssetId a, EntityGuid e);
f(a, e);          // ok
f(e, a);          // compile error — phantom types catch mis-ordering
```

Use for: content-addressable asset references, stable GUIDs that outlive runtime handles, network-serializable identifiers.

---

## See also

- `TESTING_ERROR_HANDLING_AND_BUILD.md` — full `std::expected` discipline, assertion tiers, sanitizer strategy, build presets.
- `ASSET_PIPELINE_AND_COOKER.md` — `StrongID<AssetTag>` and content-addressed storage, cooker error model.
- `EDITOR_AND_TOOLING.md` — `ComponentTraits` reflection pattern (codegen today, static reflection horizon), `Handle<Tag>` across the editor C ABI.
