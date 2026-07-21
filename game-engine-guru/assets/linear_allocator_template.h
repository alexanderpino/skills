#pragma once

/**
 * @file linear_allocator_template.h
 * @brief Zero-heap bump/arena allocator for the engine's frame and scratch memory tiers.
 *
 * Three-tier memory model
 * -----------------------
 *  1. Persistent tier: lifetime == engine lifetime. Allocated once at boot from
 *     an OS-level reservation. Never freed individually; torn down in bulk at
 *     shutdown. Examples: asset tables, device objects, module singletons.
 *
 *  2. Frame tier: lifetime == one rendered frame. Reset atomically at the
 *     end-of-frame barrier. Used for per-frame scratch structures: command
 *     lists, culling results, transient UBO staging. Must be used only by
 *     work that completes within the frame that allocated it.
 *
 *  3. Scratch tier: lifetime == one lexical scope / job. Reset via Marker
 *     checkpoint on scope exit. Typically one LinearAllocator per worker
 *     thread, fed from a per-thread slab carved from the persistent tier.
 *
 * This class targets tiers 2 and 3. It does NOT own its buffer: the caller
 * supplies a pre-reserved byte range (commonly from a virtual-memory reservation
 * backed by 2 MiB huge pages). When exhausted, Allocate returns
 * `std::unexpected(EngineError::OutOfMemory)`; there is no heap fallback.
 *
 * Thread-safety
 * -------------
 * LinearAllocator is **single-threaded by design**. Every mutation updates a
 * plain size_t without synchronization. For the scratch tier, instantiate one
 * LinearAllocator per worker thread. For the frame tier, use one instance per
 * logical producer (main thread, render thread, job worker) and fan results
 * into the final frame buffer through lock-free queues, not shared allocators.
 */

#include <bit>
#include <cstddef>
#include <cstdint>
#include <expected>
#include <limits>
#include <type_traits>

#include <engine/core/EngineError.h>  // enum class EngineError

namespace engine::memory {

/**
 * @brief Bump allocator over a caller-provided byte buffer.
 *
 * Allocation is O(1): align the current offset, check capacity, return the
 * aligned pointer, advance the offset. Deallocation is not supported at the
 * individual allocation level; use Reset() or Rewind(Marker) to reclaim
 * memory in bulk.
 */
class LinearAllocator
{
public:
    using TaggedAllocationHook =
        void (*)(void* allocation, std::size_t size, const char* tag) noexcept;

    /**
     * @brief Opaque checkpoint for nested-scope reclamation.
     *
     * Obtain with GetMarker(), restore with Rewind(). Markers are stable only
     * against the same allocator instance and only forward in time: rewinding
     * past an older marker invalidates the newer one.
     */
    struct Marker
    {
        const LinearAllocator* owner;
        std::size_t offset;
        std::uint64_t epoch;
    };
    static_assert(std::is_trivially_copyable_v<Marker>,
                  "Marker must be trivially copyable to survive across job boundaries.");

    /**
     * @brief Construct over an externally-owned buffer.
     * @param buffer   Start of the writable byte range. Must remain valid for the
     *                 lifetime of this allocator. Not owned.
     * @param capacity Size in bytes of `buffer`. A null buffer or zero capacity
     *                 creates an inert allocator whose allocations fail.
     * @param taggedAllocationHook Optional debug observer; the default no-op
     *                 keeps ENGINE_MEMORY_DEBUG builds self-contained.
     *
     * The allocator performs no internal malloc/new. Typical wiring: reserve a
     * 2 MiB VirtualAlloc / mmap page, pass (ptr, size) here.
     */
    constexpr LinearAllocator(
        std::byte* buffer,
        std::size_t capacity,
        TaggedAllocationHook taggedAllocationHook = nullptr) noexcept
        : m_buffer{buffer},
          m_capacity{capacity},
          m_offset{0},
          m_markerEpoch{1}
#if defined(ENGINE_MEMORY_DEBUG) && ENGINE_MEMORY_DEBUG
        , m_taggedAllocationHook{taggedAllocationHook}
#endif
    {
#if !defined(ENGINE_MEMORY_DEBUG) || !ENGINE_MEMORY_DEBUG
        (void)taggedAllocationHook;
#endif
    }

    LinearAllocator(const LinearAllocator&)            = delete;
    LinearAllocator& operator=(const LinearAllocator&) = delete;
    LinearAllocator(LinearAllocator&&)                 = delete;
    LinearAllocator& operator=(LinearAllocator&&)      = delete;

    /// @return true when the allocator has a nonempty backing range.
    [[nodiscard]] bool IsValid() const noexcept
    {
        return m_buffer != nullptr && m_capacity != 0u;
    }

    /**
     * @brief Allocate `size` bytes aligned to `align`.
     * @param size  Number of bytes to reserve.
     * @param align Alignment in bytes. Must be a power of two and >= 1.
     * @return Pointer to the reserved bytes, or EngineError::OutOfMemory when the
     *         remaining capacity is insufficient, or EngineError::InvalidArgument
     *         when `size` is zero, the allocator is inert, or `align` is not a
     *         power of two.
     *
     * @note The returned memory is uninitialized. Callers must construct objects
     *       in place via placement-new if they need non-trivial initialization.
     */
    [[nodiscard]] std::expected<void*, core::EngineError>
    Allocate(std::size_t size, std::size_t align) noexcept
    {
        if (m_buffer == nullptr || m_capacity == 0u || size == 0u ||
            align == 0u || (align & (align - 1u)) != 0u) [[unlikely]]
        {
            return std::unexpected(core::EngineError::InvalidArgument);
        }

        const auto base = reinterpret_cast<std::uintptr_t>(m_buffer);
        constexpr auto maxAddress = std::numeric_limits<std::uintptr_t>::max();
        if (m_offset > m_capacity || base > maxAddress - m_offset) [[unlikely]]
        {
            return std::unexpected(core::EngineError::OutOfMemory);
        }
        const auto current = base + m_offset;
        if (current > maxAddress - (align - 1u)) [[unlikely]]
        {
            return std::unexpected(core::EngineError::OutOfMemory);
        }
        const auto aligned = (current + (align - 1u)) &
                             ~static_cast<std::uintptr_t>(align - 1u);
        const auto paddingAddress = aligned - current;
        if (paddingAddress > std::numeric_limits<std::size_t>::max()) [[unlikely]]
        {
            return std::unexpected(core::EngineError::OutOfMemory);
        }
        const auto padding = static_cast<std::size_t>(paddingAddress);

        if (padding > m_capacity - m_offset) [[unlikely]]
        {
            return std::unexpected(core::EngineError::OutOfMemory);
        }
        if (size > m_capacity - m_offset - padding) [[unlikely]]
        {
            return std::unexpected(core::EngineError::OutOfMemory);
        }
        const std::size_t newOffset = m_offset + padding + size;

        void* p  = m_buffer + m_offset + padding;
        m_offset = newOffset;
        return p;
    }

#if defined(ENGINE_MEMORY_DEBUG) && ENGINE_MEMORY_DEBUG
    /**
     * @brief Debug-only tagged allocation hook.
     *
     * Records the allocation with a human-readable `tag` so heap profilers
     * (Tracy, RAD Telemetry, Superluminal) can attribute bump usage back to
     * call sites. Tag strings must have static storage duration.
     *
     * In release builds this overload is omitted entirely; use Allocate().
     */
    [[nodiscard]] std::expected<void*, core::EngineError>
    AllocateTagged(std::size_t size, std::size_t align, const char* tag) noexcept
    {
        auto r = Allocate(size, align);
        if (r) { OnTaggedAllocation(*r, size, tag); }
        return r;
    }
#endif

    /// @return Snapshot of the current bump offset, usable with Rewind.
    [[nodiscard]] Marker GetMarker() const noexcept
    {
        return Marker{this, m_offset, m_markerEpoch};
    }

    /**
     * @brief Rewind to a previously captured marker.
     * @param m Marker obtained from GetMarker() on this same instance.
     *
     * All allocations made after `m` become invalid. A marker from another
     * allocator, from before Reset(), or beyond the current offset is rejected.
     * Markers invalidated by a rewind must not be reused after the arena grows
     * again; markers are linear capabilities, not reusable bookmarks.
     * @return true when the marker was accepted.
     */
    [[nodiscard]] bool Rewind(Marker m) noexcept
    {
        // DEV_ASSERT(m.owner == this && m.epoch == m_markerEpoch &&
        //            m.offset <= m_offset, "invalid allocator marker");
        if (m.owner != this || m.epoch != m_markerEpoch || m.offset > m_offset)
        {
            return false;
        }
        m_offset = m.offset;
        return true;
    }

    /// @brief Reset the allocator to an empty state. Typically called at end-of-frame.
    void Reset() noexcept
    {
        m_offset = 0u;
        ++m_markerEpoch;
        if (m_markerEpoch == 0u) { m_markerEpoch = 1u; }
    }

    /// @return Bytes currently allocated (including alignment padding).
    [[nodiscard]] std::size_t BytesUsed() const noexcept { return m_offset; }

    /// @return Bytes still available before the next allocation may fail.
    [[nodiscard]] std::size_t BytesRemaining() const noexcept { return m_capacity - m_offset; }

    /// @return Total capacity of the backing buffer in bytes.
    [[nodiscard]] std::size_t Capacity() const noexcept { return m_capacity; }

private:
#if defined(ENGINE_MEMORY_DEBUG) && ENGINE_MEMORY_DEBUG
    void OnTaggedAllocation(void* p, std::size_t size, const char* tag) noexcept
    {
        if (m_taggedAllocationHook != nullptr)
        {
            m_taggedAllocationHook(p, size, tag);
        }
    }

#endif

    std::byte*  m_buffer;   ///< Non-owning pointer to the backing slab.
    std::size_t m_capacity; ///< Total bytes in m_buffer.
    std::size_t m_offset;   ///< Bytes consumed so far (monotonic until Rewind/Reset).
    std::uint64_t m_markerEpoch; ///< Invalidates markers across Reset().
#if defined(ENGINE_MEMORY_DEBUG) && ENGINE_MEMORY_DEBUG
    TaggedAllocationHook m_taggedAllocationHook;
#endif
};

/**
 * @brief RAII scope guard that captures a Marker and Rewinds on destruction.
 *
 * Use in functions that allocate scratch memory but must not leak it to the
 * surrounding frame allocator:
 *
 * @code
 * auto& a = GetScratchAllocator();
 * ScopedMarker _{a};
 * auto tmp = a.Allocate(4096, 16);
 * if (!tmp) return std::unexpected(tmp.error());
 * auto* bytes = static_cast<std::byte*>(*tmp);
 * // tmp is automatically reclaimed at scope exit.
 * @endcode
 */
class ScopedMarker
{
public:
    explicit ScopedMarker(LinearAllocator& a) noexcept
        : m_alloc{a}, m_marker{a.GetMarker()} {}
    ~ScopedMarker() noexcept { (void)m_alloc.Rewind(m_marker); }

    ScopedMarker(const ScopedMarker&)            = delete;
    ScopedMarker& operator=(const ScopedMarker&) = delete;
    ScopedMarker(ScopedMarker&&)                 = delete;
    ScopedMarker& operator=(ScopedMarker&&)      = delete;

private:
    LinearAllocator&         m_alloc;
    LinearAllocator::Marker  m_marker;
};

} // namespace engine::memory
