/**
 * @file engine_module_template.cpp
 * @brief Reference implementation for the Foo module scaffold.
 *
 * Matches engine_module_template.h. Demonstrates:
 *   - Lifecycle: Init / Tick / Shutdown returning std::expected<void, EngineError>.
 *   - Zero-heap: persistent slab from g_persistentAllocator, frame scratch from g_frameAllocator.
 *   - Tracy zones on every non-trivial function.
 *   - SoA iteration over an archetype component view.
 *   - Exception-free error plumbing via std::unexpected.
 */

#include "engine_module_template.h"

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <new>          // std::launder, placement new (not operator new)
#include <numbers>

#include <engine/ecs/Archetype.h>
#include <engine/ecs/View.h>
#include <engine/core/Log.h>

namespace engine::foo {

namespace {

/// File-scope singleton instance. Constructed in zero-initialized storage;
/// no global heap allocation. Accessed only via GetFooModule().
constinit FooModule g_fooModule{};

/// Persistent slab size: enough for expected resource table entries.
/// 64 KiB = 2048 * 32B = room for 2048 FooComponents plus headroom.
constexpr std::size_t kFooPersistentBytes = 64u * 1024u;

/// Aligns `x` up to a power-of-two `a`. Precondition: a is a power of two.
[[nodiscard]] constexpr std::size_t AlignUp(std::size_t x, std::size_t a) noexcept
{
    return (x + (a - 1u)) & ~(a - 1u);
}

} // namespace

FooModule* GetFooModule() noexcept { return &g_fooModule; }

std::expected<void, core::EngineError>
FooModule::Init(ecs::World& world) noexcept
{
    ZoneScoped;

    if (m_initialized) [[unlikely]]
    {
        core::LogError("FooModule::Init called twice");
        return std::unexpected(core::EngineError::AlreadyInitialized);
    }

    // Reserve a persistent slab for the module's private tables.
    // Never call `new` or `malloc`; the persistent allocator owns engine-lifetime memory.
    auto slab = memory::g_persistentAllocator->Allocate(kFooPersistentBytes, alignof(std::max_align_t));
    if (!slab) [[unlikely]]
    {
        return std::unexpected(slab.error()); // EngineError::OutOfMemory
    }

    m_persistent      = static_cast<std::byte*>(*slab);
    m_persistentBytes = kFooPersistentBytes;
    std::memset(m_persistent, 0, m_persistentBytes);

    // Register the system with the world's scheduler. World::RegisterSystem
    // is expected to return std::expected; propagate errors verbatim.
    if (auto r = world.RegisterSystem<FooSystem>(); !r) [[unlikely]]
    {
        return std::unexpected(r.error());
    }

    // Register the component type so archetypes can include it.
    if (auto r = world.RegisterComponent<FooComponent>(); !r) [[unlikely]]
    {
        return std::unexpected(r.error());
    }

    m_world       = &world;
    m_liveCount   = 0;
    m_initialized = true;
    return {};
}

std::expected<void, core::EngineError>
FooModule::Tick(float dt) noexcept
{
    ZoneScoped;

    if (!m_initialized) [[unlikely]]
    {
        return std::unexpected(core::EngineError::InvalidState);
    }

    // Per-frame scratch example: build a transient dirty list in frame memory.
    // The frame allocator is reset by the Kernel at end-of-frame, so no free is required.
    const std::size_t maxDirty = m_liveCount;
    auto scratch = memory::g_frameAllocator->Allocate(
        maxDirty * sizeof(FooHandle), alignof(FooHandle));
    if (!scratch) [[unlikely]]
    {
        return std::unexpected(scratch.error());
    }

    // Suppress unused warnings without side effects; in a real module this buffer
    // would be filled during the SoA iteration below and consumed by a follow-up system.
    auto* dirty = static_cast<FooHandle*>(*scratch);
    (void)dirty;
    (void)dt;

    return {};
}

std::expected<void, core::EngineError>
FooModule::Shutdown() noexcept
{
    ZoneScoped;

    if (!m_initialized)
    {
        // Idempotent: return success if already shut down.
        return {};
    }

    // Persistent allocator is bulk-reset by the Kernel at engine teardown.
    // We null our view of it and let the Kernel reclaim the whole arena.
    m_persistent      = nullptr;
    m_persistentBytes = 0;
    m_world           = nullptr;
    m_liveCount       = 0;
    m_initialized     = false;
    return {};
}

// -----------------------------------------------------------------------------
// FooSystem
// -----------------------------------------------------------------------------

void FooSystem::Update(ecs::World& world, float dt) noexcept
{
    ZoneScoped;

    // SoA iteration: request contiguous arrays of FooComponent across all archetypes
    // that contain it. `view.ForEachChunk` passes cache-friendly spans to the lambda.
    auto view = world.View<FooComponent>();

    constexpr float kTwoPi = 2.0f * std::numbers::pi_v<float>;

    view.ForEachChunk([dt](std::span<FooComponent> chunk) noexcept
    {
        ZoneScopedN("FooSystem::Chunk");

        // Hot inner loop: branchless, auto-vectorizable on clang/MSVC at -O2.
        // Writes are confined to this chunk; no aliasing with other systems.
        for (FooComponent& c : chunk)
        {
            const bool active = (c.flags & FooFlag_Active) != 0u;
            const float step  = active ? (c.strength * dt) : 0.0f;

            float p = c.phase + step;
            // fmodf is faster than fmod for single-precision; keep phase in [0, 2pi).
            if (p >= kTwoPi) { p = std::fmod(p, kTwoPi); }

            c.phase = p;
            c.flags |= FooFlag_Dirty;
        }
    });
}

} // namespace engine::foo
