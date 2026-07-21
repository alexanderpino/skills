#pragma once

/**
 * @file engine_module_template.h
 * @brief Scaffold for a self-contained engine module (subsystem + components + systems).
 *
 * Replace the `foo` namespace and the `Foo*` identifiers with your module name
 * (e.g. `engine::animation`, `engine::physics`, `engine::audio`). A module owns:
 *   - A singleton subsystem object with Init/Shutdown/Tick lifecycle.
 *   - One or more plain-data Component structs (trivially copyable, standard-layout).
 *   - One or more System classes implementing ISystem::Update(World&, float).
 *
 * Engine-wide rules enforced by this scaffold:
 *   - C++23 only. No exceptions. Fallible APIs return std::expected<T, EngineError>.
 *   - No heap allocations in hot paths. Use tier allocators from <engine/memory/Allocators.h>.
 *   - Every hot function opens with `ZoneScoped;` for Tracy.
 */

#include <cstddef>
#include <cstdint>
#include <expected>
#include <span>
#include <string_view>
#include <type_traits>

#include <engine/core/EngineError.h>   // enum class EngineError : uint32_t { ... }
#include <engine/core/ISystem.h>        // struct ISystem { virtual void Update(World&, float) = 0; ... }
#include <engine/ecs/World.h>           // class World; component views, entity handles
#include <engine/memory/Allocators.h>   // g_persistentAllocator, g_frameAllocator, LinearAllocator
#include <engine/profiling/Tracy.h>     // ZoneScoped, ZoneScopedN

namespace engine::ecs  { class World; }
namespace engine::core { enum class EngineError : std::uint32_t; }

namespace engine::foo {

/// Stable integral identifier assigned by the Foo module to its internal resources.
/// 0 is reserved as "invalid". Handles are opaque and must not be dereferenced by callers.
enum class FooHandle : std::uint32_t { Invalid = 0 };

/**
 * @brief Plain-data component describing a Foo on an entity.
 *
 * Components are POD-adjacent: trivially copyable, standard-layout, no virtuals,
 * no owning pointers. They are stored in SoA archetype chunks by the ECS and may
 * be memcpy'd across threads and serialized bit-for-bit on a single platform.
 */
struct FooComponent
{
    FooHandle  handle   {FooHandle::Invalid}; ///< Back-reference into the module's resource table.
    float      strength {1.0f};               ///< Arbitrary per-instance scalar parameter.
    float      phase    {0.0f};               ///< Accumulated phase in seconds, [0, 2pi).
    std::uint32_t flags {0u};                 ///< Bitfield of FooFlagBits (see below).
};

/// Bit flags packed into FooComponent::flags.
enum FooFlagBits : std::uint32_t
{
    FooFlag_None      = 0u,
    FooFlag_Active    = 1u << 0,
    FooFlag_Dirty     = 1u << 1,
    FooFlag_Simulated = 1u << 2,
};

static_assert(std::is_trivially_copyable_v<FooComponent>,
              "FooComponent must be trivially copyable for ECS chunk storage and job serialization.");
static_assert(std::is_standard_layout_v<FooComponent>,
              "FooComponent must be standard-layout for stable C-ABI reflection and tooling.");
static_assert(sizeof(FooComponent) <= 32,
              "FooComponent should fit in half a cache line; reconsider fields if it grows.");

/**
 * @brief Module-level subsystem singleton.
 *
 * Owned by the engine Kernel. Lifetime is bounded by Init/Shutdown. All persistent
 * allocations must be routed through g_persistentAllocator; per-frame scratch must
 * use g_frameAllocator. Never call `new`, `malloc`, or throw.
 */
class FooModule
{
public:
    /// Construction is cheap; real work happens in Init(). Copy/move are disabled
    /// because the module is a singleton owned by the Kernel.
    FooModule() noexcept = default;
    ~FooModule() noexcept = default;

    FooModule(const FooModule&)            = delete;
    FooModule& operator=(const FooModule&) = delete;
    FooModule(FooModule&&)                 = delete;
    FooModule& operator=(FooModule&&)      = delete;

    /**
     * @brief One-time startup. Allocates persistent buffers, registers systems with the scheduler.
     * @param world ECS world that this module attaches components and systems to.
     * @return Ok on success; EngineError::OutOfMemory or EngineError::AlreadyInitialized on failure.
     */
    [[nodiscard]] std::expected<void, core::EngineError>
    Init(ecs::World& world) noexcept;

    /**
     * @brief Per-frame tick called by the Kernel on the main thread before parallel system updates.
     * @param dt Variable delta time in seconds. Fixed-step work should be routed via a FixedTick system.
     * @return Ok on success; EngineError::InvalidState if Tick is called before Init or after Shutdown.
     */
    [[nodiscard]] std::expected<void, core::EngineError>
    Tick(float dt) noexcept;

    /**
     * @brief Release all module-owned resources. Idempotent; safe to call twice.
     * @return Ok on success, including when already shut down; otherwise the
     *         first scheduler/component-unregistration error.
     */
    [[nodiscard]] std::expected<void, core::EngineError>
    Shutdown() noexcept;

    /// @return True if Init() has completed successfully and Shutdown() has not been called.
    [[nodiscard]] bool IsInitialized() const noexcept { return m_initialized; }

    /// @return Count of live FooHandles, or zero before Init/after Shutdown.
    [[nodiscard]] std::size_t LiveHandleCount() const noexcept { return m_liveCount; }

private:
    bool           m_initialized {false};
    bool           m_systemRegistered {false};
    bool           m_componentRegistered {false};
    std::size_t    m_liveCount   {0};
    ecs::World*    m_world       {nullptr}; ///< Non-owning. Cleared in Shutdown().
    // Reserved once from the Kernel arena and retained across Shutdown()/Init()
    // cycles because a monotonic persistent allocator cannot free this slab.
    std::byte*     m_persistent  {nullptr}; ///< Non-owning view; Kernel owns storage.
    std::size_t    m_persistentBytes {0};
};

/**
 * @brief System that advances FooComponent state each frame.
 *
 * Registered by FooModule::Init with the World's scheduler. Runs on the job
 * system; must be thread-safe with respect to the components it reads/writes
 * (declared via GetReadSet/GetWriteSet overrides, not shown here).
 */
class FooSystem final : public core::ISystem
{
public:
    FooSystem() noexcept = default;
    ~FooSystem() noexcept override = default;

    /**
     * @brief Update all FooComponents in the given World.
     * @param world Live ECS world. Implementation iterates an archetype view.
     * @param dt    Delta time in seconds for this frame.
     *
     * This method is `noexcept` by contract. Errors are reported via the world's
     * diagnostic sink; this signature returns void to match ISystem.
     */
    void Update(ecs::World& world, float dt) noexcept override;

    /// Human-readable name used by the profiler and scheduler graph.
    [[nodiscard]] std::string_view Name() const noexcept override { return "FooSystem"; }
};

/// Global accessor for stable singleton storage. Always non-null; call
/// IsInitialized() before using lifecycle-dependent state.
[[nodiscard]] FooModule* GetFooModule() noexcept;

} // namespace engine::foo
