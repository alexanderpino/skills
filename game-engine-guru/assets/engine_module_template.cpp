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
#include <limits>

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

} // namespace

FooModule* GetFooModule() noexcept { return &g_fooModule; }

std::expected<void, core::EngineError>
FooModule::Init(ecs::World& world) noexcept
{
    ZoneScoped;

    if (m_initialized || m_systemRegistered || m_componentRegistered) [[unlikely]]
    {
        core::LogError("FooModule::Init called twice");
        return std::unexpected(core::EngineError::AlreadyInitialized);
    }
    if (m_persistent == nullptr && memory::g_persistentAllocator == nullptr) [[unlikely]]
    {
        return std::unexpected(core::EngineError::InvalidState);
    }

    // Do all fallible registrations before consuming arena memory. Each step is
    // rolled back on failure so callers may safely retry Init().
    if (auto r = world.RegisterComponent<FooComponent>(); !r) [[unlikely]]
    {
        return std::unexpected(r.error());
    }

    if (auto r = world.RegisterSystem<FooSystem>(); !r) [[unlikely]]
    {
        if (auto rollback = world.UnregisterComponent<FooComponent>(); !rollback)
        {
            m_world = &world;
            m_componentRegistered = true;
            return std::unexpected(rollback.error());
        }
        return std::unexpected(r.error());
    }

    // A monotonic persistent arena cannot individually free this module's slab.
    // Reserve it once and reuse it across Shutdown()/Init() cycles.
    if (m_persistent == nullptr)
    {
        auto slab = memory::g_persistentAllocator->Allocate(
            kFooPersistentBytes, alignof(std::max_align_t));
        if (!slab) [[unlikely]]
        {
            if (auto rollback = world.UnregisterSystem<FooSystem>(); !rollback)
            {
                m_world = &world;
                m_systemRegistered = true;
                m_componentRegistered = true;
                return std::unexpected(rollback.error());
            }
            if (auto rollback = world.UnregisterComponent<FooComponent>(); !rollback)
            {
                m_world = &world;
                m_componentRegistered = true;
                return std::unexpected(rollback.error());
            }
            return std::unexpected(slab.error());
        }
        m_persistent      = static_cast<std::byte*>(*slab);
        m_persistentBytes = kFooPersistentBytes;
    }

    std::memset(m_persistent, 0, m_persistentBytes);

    m_world       = &world;
    m_liveCount   = 0;
    m_systemRegistered = true;
    m_componentRegistered = true;
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

    if (!std::isfinite(dt) || dt < 0.0f) [[unlikely]]
    {
        return std::unexpected(core::EngineError::InvalidArgument);
    }

    // Per-frame scratch example: build a transient dirty list in frame memory.
    // The frame allocator is reset by the Kernel at end-of-frame, so no free is required.
    const std::size_t maxDirty = m_liveCount;
    if (maxDirty == 0u)
    {
        return {};
    }
    if (memory::g_frameAllocator == nullptr) [[unlikely]]
    {
        return std::unexpected(core::EngineError::InvalidState);
    }
    if (maxDirty > std::numeric_limits<std::size_t>::max() / sizeof(FooHandle))
        [[unlikely]]
    {
        return std::unexpected(core::EngineError::OutOfMemory);
    }
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

    if (!m_initialized && !m_systemRegistered && !m_componentRegistered)
    {
        // Idempotent: return success if already shut down.
        return {};
    }

    if (m_systemRegistered)
    {
        if (auto r = m_world->UnregisterSystem<FooSystem>(); !r) [[unlikely]]
        {
            return std::unexpected(r.error());
        }
        m_systemRegistered = false;
    }

    if (m_componentRegistered)
    {
        if (auto r = m_world->UnregisterComponent<FooComponent>(); !r) [[unlikely]]
        {
            return std::unexpected(r.error());
        }
        m_componentRegistered = false;
    }

    // Retain the monotonic-arena slab for a later Init(). The Kernel owns and
    // bulk-resets it only after this module object can no longer be reinitialized.
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

    if (!std::isfinite(dt) || dt < 0.0f) [[unlikely]]
    {
        core::LogError("FooSystem::Update rejected invalid delta time");
        return;
    }

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
            if (!std::isfinite(c.phase))
            {
                c.phase = 0.0f;
                c.flags |= FooFlag_Dirty;
                continue;
            }

            const bool active = (c.flags & FooFlag_Active) != 0u;
            const float step  = active ? (c.strength * dt) : 0.0f;

            float p = c.phase + step;
            if (!std::isfinite(p))
            {
                p = 0.0f;
            }
            else
            {
                p = std::fmod(p, kTwoPi);
                if (p < 0.0f) { p += kTwoPi; }
            }

            c.phase = p;
            c.flags |= FooFlag_Dirty;
        }
    });
}

} // namespace engine::foo
