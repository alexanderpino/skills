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

C++23 is the preferred source-language level, but compiler and standard-library support are separate capability axes. Gate every non-core facility with its feature-test macro and the actual shipping SDK:

| Facility | Practical minimums / caveats |
|----------|------------------------------|
| `std::expected` | Broadly available in current desktop libraries; verify console SDK library |
| deducing `this` | Clang 18+, GCC 14+, recent MSVC |
| `std::mdspan` | GCC 14+, libc++ 17+, recent MSVC; gate with `__cpp_lib_mdspan` |
| `<stacktrace>` | Available in libstdc++ and MSVC STL with implementation/link caveats; not a portable libc++ assumption |
| multidimensional `operator[]` | Gate with `__cpp_multidimensional_subscript` |

Keep engine fallbacks for every facility required by a lagging platform SDK.

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
enum class GridError { InvalidExtent, SizeOverflow, OutOfBounds };

class Grid3D {
    std::vector<float> data_;
    std::size_t nx_{}, ny_{}, nz_{};

    Grid3D(std::size_t nx, std::size_t ny, std::size_t nz, std::size_t count)
        : data_(count), nx_(nx), ny_(ny), nz_(nz) {}
public:
    Grid3D(const Grid3D&) = delete;
    Grid3D& operator=(const Grid3D&) = delete;
    Grid3D(Grid3D&&) noexcept = default;
    Grid3D& operator=(Grid3D&&) noexcept = default;

    [[nodiscard]] static std::expected<Grid3D, GridError>
    create(std::size_t nx, std::size_t ny, std::size_t nz) {
        if (nx == 0 || ny == 0 || nz == 0)
            return std::unexpected(GridError::InvalidExtent);
        if (ny > std::numeric_limits<std::size_t>::max() / nx)
            return std::unexpected(GridError::SizeOverflow);
        const auto plane = nx * ny;
        if (nz > std::numeric_limits<std::size_t>::max() / plane)
            return std::unexpected(GridError::SizeOverflow);
        return Grid3D(nx, ny, nz, plane * nz);
    }

    // Unchecked hot-path access: the caller must establish the bounds invariant.
    float& operator[](std::size_t x, std::size_t y, std::size_t z) noexcept {
        return data_[x + nx_ * (y + ny_ * z)];
    }

    [[nodiscard]] std::expected<std::reference_wrapper<float>, GridError>
    at(std::size_t x, std::size_t y, std::size_t z) noexcept {
        if (x >= nx_ || y >= ny_ || z >= nz_)
            return std::unexpected(GridError::OutOfBounds);
        return std::ref((*this)[x, y, z]);
    }
};

auto grid = Grid3D::create(32, 32, 32);
if (!grid) return std::unexpected(grid.error());
auto cell = grid->at(4, 5, 6);
if (!cell) return std::unexpected(cell.error());
cell->get() = 1.0f;
```

Use for: voxel grids, 3D LUTs, matrix views, texture tile access.

### `std::mdspan` — non-owning multi-dim views

`std::mdspan` is customizable for row-major, column-major, and strided layouts, but **does not perform bounds checking by default**. Validate extents at the API boundary; use a project checked accessor if every individual access must be diagnosed.

```cpp
using Extents2D = std::dextents<std::size_t, 2>;
using ImageView = std::mdspan<float, Extents2D, std::layout_right>;
using ConstImageView = std::mdspan<const float, Extents2D, std::layout_right>;

enum class BlurError { ExtentMismatch, ImageTooSmall };

[[nodiscard]] std::expected<void, BlurError>
blur3x3(ConstImageView src, ImageView dst) noexcept {
    const auto h = src.extent(0);
    const auto w = src.extent(1);
    if (dst.extent(0) != h || dst.extent(1) != w)
        return std::unexpected(BlurError::ExtentMismatch);
    if (h < 3 || w < 3)
        return std::unexpected(BlurError::ImageTooSmall);

    for (std::size_t y = 1; y < h - 1; ++y)
    for (std::size_t x = 1; x < w - 1; ++x) {
        float sum = 0.0f;
        for (std::size_t yy = y - 1; yy <= y + 1; ++yy)
        for (std::size_t xx = x - 1; xx <= x + 1; ++xx)
            sum += src[yy, xx];
        dst[y, x] = sum / 9.0f;
    }
    return {};
}
```

### `<stacktrace>` — optional crash reporter integration

```cpp
#if defined(__cpp_lib_stacktrace) && __cpp_lib_stacktrace >= 202011L
void report_assert_failure(const char* cond, const char* file, int line) {
    auto st = std::stacktrace::current(/*skip*/1);
    crash_report::submit({
        .condition = cond,
        .file      = file,
        .line      = line,
        .stack     = std::to_string(st),
    });
}
#else
// Route through the platform crash layer (DbgHelp, backtrace/unwind,
// Crashpad, or the console SDK) and symbolize out of process.
#endif
```

Stack capture still requires platform unwinding support, and useful reports require matching symbols and build IDs. Never make `<stacktrace>` the only crash path.

### `if consteval` and extended constexpr

```cpp
constexpr float portable_sqrt(float x) noexcept {
    if consteval {
        if (x < 0.0f) return std::numeric_limits<float>::quiet_NaN();
        if (x == 0.0f) return 0.0f;
        float guess = x >= 1.0f ? x : 1.0f;
        for (int i = 0; i < 32; ++i)
            guess = 0.5f * (guess + x / guess);
        return guess;
    } else {
        // Portable runtime path; the implementation may select a hardware sqrt.
        return std::sqrt(x);
    }
}
```

Most `<cmath>` overloads are not required to be `constexpr` until C++26. In a C++23 baseline, use a bounded compile-time algorithm such as the one above, generate tables at build time, or gate the C++26 library path with its actual library feature-test macro.

### `constexpr` containers

`constexpr std::vector` and `std::string` are C++20 library features and are available in the C++23 baseline where the library implements them. Allocations generally cannot escape constant evaluation into persistent runtime objects; use generated arrays or fixed-capacity containers when that is required.

---

## C++26 — Horizon Only (gated)

**Every C++26 usage below must be feature-test-macro guarded with a working C++23 fallback.** Consoles will not support these for 12-24 months after desktop lands them.

### Static Reflection

The single most impactful feature coming. Replaces hand-written `ComponentTraits`, serialization visitors, RPC descriptors. Until it ships on all target SDKs, the engine uses a codegen tool (Python + libclang) that emits equivalent templates — the *shape* of `ComponentTraits` stays identical, so adopting reflection later is a mechanical swap.

```cpp
// PSEUDOCODE — illustrative P2996-era syntax. The adopted spelling, header,
// feature-test macro, and compiler support must be checked in the target SDK.
template<class T> struct ComponentTraits {
    static constexpr std::string_view name = [:name_of(^^T):];
    static constexpr auto fields = []{
        return std::apply([]<auto... ms>(){
            return std::tuple{ Field{ [:name_of(ms):], ms }... };
        }, nonstatic_data_members_of(^^T));
    }();
};
```

The production C++23 interface is ordinary, compile-ready C++ and is filled by generated specializations:

```cpp
template<class T> struct ComponentTraits;        // primary = undefined
// tools/gen_reflection.py emits specializations into *.generated.hpp
```

Do not invent a feature-test macro in production code. Add the real macro only after the shipping compiler publishes one. Both implementations must expose the identical API (`name`, `fields`).

### Contracts

```cpp
// PSEUDOCODE — C++26 contract spelling/evaluation semantics remain toolchain
// gated. Never make a contract the only runtime validation for untrusted input.
float divide_assuming_valid(float a, float b)
    pre(b != 0.0f)
    post(r: std::isfinite(r))
{
    return a / b;
}
```

The C++23 fallback is safe even when development assertions compile out:

```cpp
enum class MathError { DivisionByZero, NonFiniteResult };

[[nodiscard]] std::expected<float, MathError>
safe_divide(float a, float b) noexcept {
    if (b == 0.0f)
        return std::unexpected(MathError::DivisionByZero);
    const float result = a / b;
    if (!std::isfinite(result))
        return std::unexpected(MathError::NonFiniteResult);
    return result;
}
```

Contract violation handlers integrate with the crash reporter the same way asserts do. Contracts don't replace asserts — they add a declarative layer the compiler can exploit for optimization and static analysis.

### Pattern Matching (`inspect`) — NOT in C++26

Pattern matching (P2688/P2392, `inspect`) was **not adopted into C++26** — it has no standard feature-test macro and no shipping compiler. Treat it as post-C++26 horizon only; the `std::visit` + `overloaded` fallback below is the actual production approach today and for the foreseeable future. The speculative branch is shown purely to illustrate the eventual shape and will never compile (the guard is permanently false until/unless the proposal lands and a real FTM is assigned).

```cpp
#if defined(__cpp_pattern_matching)   // hypothetical — no such macro exists yet (post-C++26)
// PSEUDOCODE — speculative syntax; this branch is intentionally non-production.
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

---

## EASTL & Container Strategy

`std::` containers have trade-offs that matter in some engine runtimes:

1. **Allocator model is baked into the type.** `std::vector<T, A>` and `std::vector<T, B>` are different types. Moving across allocator boundaries requires element-wise copy. Engine code needs stateful allocators that compare equal structurally — `std::` forbids this cleanly.
2. **Exception and ABI policy.** Standard-library behavior in exceptions-off builds is implementation-specific, particularly with MSVC STL. Measure binary impact and avoid relying on unsupported library modes.

Choose EASTL, a project-owned equivalent, `std::pmr`, or standard containers per module. Do not introduce a second container ecosystem without a demonstrated allocator, ABI, determinism, or binary-size need.

```cpp
#include <EASTL/vector.h>
#include <EASTL/hash_map.h>
#include <EASTL/functional.h>

// EASTL hash_map parameters are Key, T, Hash, Predicate, Allocator.
using FrameEntities = eastl::vector<Entity, FrameAllocator>;
using AssetLookup = eastl::hash_map<
    AssetId,
    Asset*,
    AssetIdHash,
    eastl::equal_to<AssetId>,
    ScratchAllocator>;

FrameEntities per_frame_entities{FrameAllocator{frame_arena}};
AssetLookup lookup{ScratchAllocator{scratch_arena}};
```

Custom allocators must implement the allocator interface required by the pinned EASTL version (including its copy/equality/name/alignment behavior). Do not pass an allocator in the `Hash` position or assume a standard-library allocator satisfies EASTL unchanged.

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
    uint64_t h = 14695981039346656037ull;
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
// PSEUDOCODE for a C++26 constexpr-cmath path. std::pow is not guaranteed
// constexpr in the C++23 baseline.
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

For C++23 production, run the same formula in a checked build-time generator and emit a `constexpr std::array<float, 256>` header (plus generator version/input hash), or provide and test a project constexpr `pow` implementation. Do not label a `std::pow` call C++23 compile-time computation.

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

// Every engine allocator exposes a fallible, aligned Allocate and bulk Reset.
// Bump tiers (Linear/Stack) reclaim only in bulk (Reset / Rewind(Marker)) and
// intentionally have NO per-allocation free — see linear_allocator_template.h.
template<class A>
concept Allocator = requires(A a, size_t n, size_t align) {
    { a.Allocate(n, align) } -> std::same_as<std::expected<void*, EngineError>>;
    { a.Reset() } noexcept;
};

// Free-list tiers (Pool, TLSF) refine it with individual free + ownership query.
template<class A>
concept FreeListAllocator = Allocator<A> && requires(A a, void* p, size_t n) {
    { a.Deallocate(p, n) } noexcept;
    { a.Owns(p) } -> std::convertible_to<bool>;
};

template<class T>
concept Serializable = requires(const T& v, BinaryWriter& w, BinaryReader& r) {
    { serialize(v, w) } -> std::same_as<std::expected<void, SerializeError>>;
    { deserialize(r) } -> std::same_as<std::expected<T, SerializeError>>;
};

// Unary folds require a nonempty pack; state that contract explicitly.
auto sum(std::integral auto first, std::integral auto... rest) {
    return (first + ... + rest);
}

// Requires clause — preferred when constraints are compound:
template<class T> requires Component<T> && Serializable<T>
void register_component();
```

Concepts matter most in templated code humans read. The compile-error delta between a constrained and unconstrained template on failure is worth the initial investment by itself.

---

## Coroutines for Async

C++20 coroutines are usable in a C++23 engine, but the language does not supply ownership, scheduling, cancellation, or error propagation. A coroutine frame must outlive every queued resume and must not come from a frame arena that resets while the operation is suspended.

```cpp
// PSEUDOCODE — abbreviated scheduler/promise protocol, not a drop-in task type.
class AsyncTask {
public:
    struct promise_type {
        std::expected<void, AsyncError> result{};
        Scheduler* owner{};

        AsyncTask get_return_object();             // wraps handle_from_promise(*this)
        std::suspend_always initial_suspend() noexcept;
        RetireAtSchedulerBarrier final_suspend() noexcept;
        void return_value(std::expected<void, AsyncError> r) noexcept {
            result = std::move(r);
        }
        void unhandled_exception() noexcept { std::terminate(); } // exceptions-off invariant

        // Long-lived coroutine pool, never the per-frame allocator.
        void* operator new(std::size_t n);
        void operator delete(void* p, std::size_t n) noexcept;
    };

private:
    std::coroutine_handle<promise_type> handle_; // owned until start()

public:
    ~AsyncTask(); // destroys only an unstarted frame still owned by this object
    void start(Scheduler& scheduler) &&; // transfers the handle to scheduler
};

AsyncTask load_level(std::string name) {
    auto manifest = co_await read_file_async(name);
    if (!manifest)
        co_return std::unexpected(map_async_error(manifest.error()));

    auto parsed = co_await parse_async(*manifest);
    if (!parsed)
        co_return std::unexpected(map_async_error(parsed.error()));

    auto meshes = co_await load_meshes(parsed->mesh_refs);
    if (!meshes)
        co_return std::unexpected(map_async_error(meshes.error()));

    auto uploaded = co_await upload_to_gpu(std::move(*meshes));
    if (!uploaded)
        co_return std::unexpected(map_async_error(uploaded.error()));

    co_await scene_ready_barrier();
    emit_event("LevelLoaded"_id);
    co_return std::expected<void, AsyncError>{};
}
```

The scheduler becomes the sole frame owner at `start()`. A queued resume holds that ownership; cancellation marks the promise and still resumes or retires it through the scheduler. `final_suspend` publishes the result to the awaiting parent/supervisor and queues destruction at a scheduler safe point. Never self-destroy in `return_void`, never retain a second owning handle, and never fire-and-forget without a supervisor that consumes the error.

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

The workhorse. A `Handle<Entity>` or `Handle<Texture2D>` is a 64-bit POD: `{ uint32_t index; uint32_t generation; }`. The fixed-capacity reference registry below has stable element addresses, reserves index zero for null, reports exhaustion, and permanently retires a slot before its generation can wrap.

```cpp
template<class Tag>
struct Handle {
    uint32_t index      = 0;
    uint32_t generation = 0;
    constexpr bool is_null() const noexcept { return index == 0 && generation == 0; }
    friend auto operator<=>(Handle, Handle) = default;
};

enum class HandleError { Null, OutOfRange, Stale, Destroyed, Full };

template<class T, class Tag, std::size_t Capacity>
requires std::is_nothrow_destructible_v<T>
class Registry {
    struct Slot {
        std::uint32_t generation{1};
        std::optional<T> value;
        bool retired{false};
    };
    std::array<Slot, Capacity + 1> slots_{}; // slot 0 is permanently null
    std::array<std::uint32_t, Capacity> free_{};
    std::size_t free_count_{Capacity};

public:
    Registry() noexcept {
        for (std::size_t i = 0; i < Capacity; ++i)
            free_[i] = static_cast<std::uint32_t>(Capacity - i);
    }

    template<class... Args>
    requires std::is_nothrow_constructible_v<T, Args...>
    [[nodiscard]] std::expected<Handle<Tag>, HandleError>
    create(Args&&... args) noexcept {
        if (free_count_ == 0)
            return std::unexpected(HandleError::Full);
        const auto index = free_[--free_count_];
        Slot& slot = slots_[index];
        slot.value.emplace(std::forward<Args>(args)...);
        return Handle<Tag>{index, slot.generation};
    }

    [[nodiscard]] std::expected<void, HandleError>
    destroy(Handle<Tag> h) noexcept {
        auto value = resolve(h);
        if (!value) return std::unexpected(value.error());
        Slot& slot = slots_[h.index];
        slot.value.reset();
        if (slot.generation == std::numeric_limits<std::uint32_t>::max()) {
            slot.retired = true; // do not wrap and resurrect an ancient handle
        } else {
            ++slot.generation;
            free_[free_count_++] = h.index;
        }
        return {};
    }

    [[nodiscard]] std::expected<T*, HandleError>
    resolve(Handle<Tag> h) noexcept {
        if (h.index == 0)                              return std::unexpected(HandleError::Null);
        if (h.index >= slots_.size())                   return std::unexpected(HandleError::OutOfRange);
        if (slots_[h.index].generation != h.generation) return std::unexpected(HandleError::Stale);
        if (!slots_[h.index].value)                     return std::unexpected(HandleError::Destroyed);
        return std::addressof(*slots_[h.index].value);
    }
};
```

Pointers returned by this fixed-capacity registry remain stable until that slot is destroyed; they must not escape a synchronization interval in which destruction can occur. Handles can be serialized only with the registry identity and slot/generation state, or remapped from stable GUIDs on load. A bare runtime handle does not automatically survive save/load or process restart.

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
