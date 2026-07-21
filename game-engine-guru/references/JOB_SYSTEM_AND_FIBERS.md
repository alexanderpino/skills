# Job System & Fiber Scheduler

Reference document for the threading spine of the engine — Pillar 4. Audience: senior systems engineers. Every other subsystem (frame graph, ECS systems, physics islands, asset cooking, animation evaluation) is a *consumer* of this layer. Get it wrong and no amount of per-system optimization saves the frame.

## Table of Contents

- Design Goals & Why Fibers
- Worker Threads & Affinity
- Work-Stealing Deques
- Jobs, Counters & Dependency DAG
- Fiber Scheduling & Wait Semantics
- The `Wait()`-in-render-path Ban
- Blocking I/O & GPU Waits
- Memory: Per-Thread Allocators & False Sharing
- Determinism & Debugging
- Lock-Free Building Blocks

---

## Design Goals & When to Use Fibers

Set task count and scheduling overhead from the frame DAG and measured granularity. A good scheduler scales across the supported core topologies without assuming linear speedup. Two baseline constraints drive the design:

1. **No OS thread per task.** `std::thread`/`std::async` cost thousands of cycles to spawn and rely on the OS scheduler — useless at this granularity. You spawn N worker threads *once* and feed them tiny jobs.
2. **Dependency waits must not block a worker.** Prefer continuations or stackless coroutines for new asynchronous code. Fibers are valuable when synchronous call stacks must suspend: a waiting fiber parks and the worker runs other work.

Naughty Dog's "Parallelizing the Naughty Dog Engine Using Fibers" (Christian Gyrling, GDC 2015) is an important fiber design reference, not proof that every engine should adopt the same scheduler.

Fiber and OS context-switch costs vary by ABI, security features, stack handling, and hardware; benchmark the real implementation. Fibers complicate profiling, thread-local state, sanitizer integration, migration, and stack sizing, so adopt them only when suspension semantics justify that cost.

---

## Worker Threads & Affinity

- **Worker count is topology- and workload-dependent.** Start near available physical cores, reserve dedicated real-time/platform threads, and tune for SMT and heterogeneous cores. Do not derive console policy from `std::thread::hardware_concurrency()`.
- **Pin workers to cores** where the platform allows (consoles: yes, mandatory and reliable; desktop: soft affinity, the OS may override). Pinning keeps per-core caches warm and makes profiling legible.
- **The main thread is a worker too** — it runs jobs while waiting at sync points instead of spinning idle.
- **Heterogeneous cores** (mobile big.LITTLE, desktop P/E cores): tag jobs that are latency-critical to prefer P-cores; let throughput jobs land anywhere. Don't pin a frame-critical job to an E-core.

---

## Work-Stealing Deques

Each worker owns a **double-ended queue** (Chase-Lev style, lock-free):

- The **owner** pushes/pops at the *bottom* (LIFO — newest job first → best cache locality, the data it just produced is still hot).
- **Thieves** steal from the *top* (FIFO — oldest job, most likely to have its own children and spread work).

```cpp
// top and bottom are atomic indices. Slots remain valid until no thief can
// observe their generation; production code must also implement safe growth.
void push(Job* j) {
    const size_t b = bottom.load(std::memory_order_relaxed);
    slots[b & MASK].store(j, std::memory_order_relaxed);
    std::atomic_thread_fence(std::memory_order_release);
    bottom.store(b + 1, std::memory_order_relaxed);
}
Job* pop() {
    // Follow the published Chase-Lev algorithm exactly, including restoring
    // bottom and resolving the final-item race with a CAS on top.
    /* full implementation intentionally omitted */
}
// Thief side: steal from top via CAS on `top`.
Job* steal() {
    size_t t = top.load(std::memory_order_acquire);
    std::atomic_thread_fence(std::memory_order_seq_cst);
    const size_t b = bottom.load(std::memory_order_acquire);
    if (t < b) {
        Job* j = slots[t & MASK].load(std::memory_order_relaxed);
        if (top.compare_exchange_strong(t, t + 1,
                std::memory_order_seq_cst, std::memory_order_relaxed)) return j;
    }
    return nullptr;     // empty or lost the race
}
```

Do not reconstruct the omitted `pop`/resize/reclamation paths from this sketch. Reuse a reviewed implementation or the published algorithm and prove it with TSAN, stress tests, and weak-memory targets.

**Victim selection:** random victim is good enough and avoids convoying; bias toward a NUMA-local or same-cluster victim on big machines. A worker that finds its own deque empty steals; if all steals fail, it backs off (spin → pause → short sleep) rather than burning a core.

---

## Jobs, Counters & Dependency DAG

A **job** is a function pointer + a small payload (fits in a cache line — copy the data in, don't chase pointers). Dependencies are expressed with **atomic counters**, not by storing parent/child pointers everywhere.

```cpp
inline constexpr std::size_t CACHE_LINE = 64;   // 128 on Apple M-series; size to target

// Both pointers go first so the payload starts 16-aligned and the whole struct
// is exactly one line. Putting `data` between them (with alignas(16)) would pad
// fn up to offset 16 and push the trailing pointer past 64 B — 80 B in practice.
struct alignas(CACHE_LINE) Job {
    void    (*fn)(void* data);       // 8 B
    Counter*  decrementOnComplete;   // 8 B — signaled when this job finishes
    std::byte data[CACHE_LINE - 2 * sizeof(void*)];   // 48 B payload, 16-aligned
};
static_assert(sizeof(Job)  == CACHE_LINE);
static_assert(alignof(Job) == CACHE_LINE);

// A Counter holds the number of outstanding jobs in a group.
// Waiting on a counter == waiting for all jobs that decrement it.
JobHandle Schedule(Job j, Counter* deps = nullptr);     // runs when deps hits 0
void      WaitForCounter(Counter* c, int target = 0);   // parks the calling fiber
```

- **`JobHandle` is a dependency token.** Build a DAG by scheduling job B with A's counter as its dependency (`ScheduleAfter`). The scheduler only makes B stealable once A's counter reaches zero.
- **Fan-out/fan-in.** Split a loop into K jobs sharing one counter initialized to K; a continuation waits on that counter. This is your `parallel_for`.
- **Counters live in the frame arena**, reset each frame. No heap allocation in the schedule path.
- Prefer **counters over per-job futures** — a future implies an allocation and a shared state; a counter is one atomic int.

---

## Fiber Scheduling & Wait Semantics

The core loop. A worker runs a fiber until that fiber either completes or calls `WaitForCounter`:

```
worker loop:
  fiber = pick_runnable_fiber()        // resumable waiter whose counter hit 0,
                                        // else a fresh fiber bound to a stolen/popped job
  switch_to(fiber)
  ── fiber runs ──
     on WaitForCounter(c):
        if c == 0: continue            // fast path, no switch
        register this fiber on c's wait-list
        switch back to the worker's scheduler fiber   // PARK — do not block the thread
     on completion:
        decrement the job's counter (may make waiters runnable)
        free the fiber back to the pool
```

- **A parked fiber holds its stack** until resumed. That's why the fiber pool is finite and stacks are pre-sized — running out of fibers deadlocks, so size the pool for the deepest concurrent wait chain and assert on exhaustion.
- **When a counter hits zero, its wait-list fibers become runnable** on *any* worker — a job can finish on a different thread than it started. Hence: never assume thread identity across a wait, and put per-thread scratch behind the allocator API, not raw TLS captured before the wait.
- **Resumed fibers get priority** over fresh jobs (they're closer to completing and freeing resources — drains the system instead of fanning it out unboundedly).

---

## The `Wait()`-in-render-path Ban

**CRITICAL (SKILL.md §Job System).** The main render-dispatch thread must **never** call a blocking `Wait()` in the hot path. Blocking there stalls submission and bubbles the GPU.

- The dispatch thread **builds the dependency DAG and submits it**, then keeps recording the next command lists / passes — it does not sit on a `WaitForCounter`.
- Where a result is genuinely needed before proceeding, schedule a **continuation** job that depends on the result, rather than blocking. Continuation-passing, not blocking.
- The *only* sanctioned blocking wait is the frame boundary sync (and even there, prefer letting the main thread run jobs while it waits).
- Enforce it: a `RenderHotPathScope` guard that asserts in debug if `WaitForCounter` is called on the dispatch thread. Same spirit as the no-heap-alloc guard.

---

## Blocking I/O & GPU Waits

Fibers solve *dependency* waits, not *kernel* waits.

- **Blocking syscalls (file read, socket, mutex into the kernel) go to a dedicated I/O thread pool**, never onto a worker. A worker that blocks in the kernel can't run other fibers — it's a parked thread, the thing you built fibers to avoid.
- Pattern: a job that needs file data schedules the read on the I/O pool with a completion counter, then *parks* (fiber wait) on that counter. The worker stays busy; the I/O thread does the blocking read; completion wakes the fiber.
- **GPU waits** are the same shape: park on a fence-completion counter signaled by a thin GPU-progress thread (or an OS fence callback), don't spin a worker on `fence.GetCompletedValue()`.
- DirectStorage / async asset streaming integrate here — the cooker and loader (see `ASSET_PIPELINE_AND_COOKER.md`) submit to the I/O pool and signal counters.

---

## Memory: Per-Thread Allocators & False Sharing

- **Each worker has its own scratch/linear allocator** (see `assets/linear_allocator_template.h`). Jobs allocate from the *current worker's* arena — but because a fiber can migrate, resolve "current worker" through the scheduler at allocation time, never cache it across a wait.
- **Frame arena** is shared but bump-allocated lock-free (atomic fetch-add on the offset) for small transient allocations; reset at frame end after GPU fence.
- **False sharing is the silent killer.** Pad per-worker mutable state — deque control words, counters that different threads hammer — to a full cache line (64 B; **128 B on Apple M-series** where the effective sharing granularity is larger). One unpadded hot atomic shared across cores can cost more than the work it guards.
- **No `std::shared_ptr` across jobs** for ownership — atomic refcount ping-pong. Use a `Handle<T>` or transfer ownership explicitly via the job payload.

---

## Determinism & Debugging

- **Deterministic mode** (mandatory for physics & netcode repro, SKILL.md §Job System): a debug scheduler that runs jobs in *registration order on a single thread*. If a bug reproduces in deterministic mode it's a logic bug; if it vanishes, it's a race — diff the dependency edges.
- **Profiling across fiber migration:** Tracy supports fiber-aware zones — emit a fiber-enter/leave event on every context switch so a job's timeline stitches together even though it hopped threads. Without this, captures are unreadable.
- **Job-graph dump:** record the DAG (jobs, counters, edges) and visualize it; a missing edge or an accidental serialization (everything depending on one counter) jumps out.
- **Sanitizers:** TSAN is **mandatory** here — it's the one subsystem where a data race is guaranteed to exist if you got a fence wrong. Run the deque and counter code under TSAN in CI.
- **Stack-overflow detection:** guard pages on fiber stacks; a job that overflows its fiber stack corrupts a neighbor silently otherwise.

---

## Lock-Free Building Blocks

- **MPMC queue:** Vyukov bounded queue for cross-thread job submission where a deque isn't the right shape (e.g. main→worker handoff). Bounded + array-based = cache-friendly and no allocation.
- **SPSC ring** for the I/O-completion and GPU-progress handoffs.
- **Atomics discipline:** default to `acquire`/`release`; reach for `seq_cst` only where you've proven you need it (the deque's bottom/top race is the classic case). Document the happens-before for every non-`seq_cst` pair — "obvious" memory ordering is how races ship.
- **Hazard pointers / epoch reclamation** only if you have lock-free structures with reclamation (rare in a frame-arena world — prefer "allocate from arena, never free mid-frame," which sidesteps the reclamation problem entirely).
- **ABA:** the deque CAS is ABA-safe via monotonic indices (top/bottom only ever increase within a frame). Don't reintroduce ABA by recycling raw pointers in a lock-free stack.

---

## See Also

- `FRAME_GRAPH_AND_GPU_DRIVEN.md` — the frame graph's setup phase parallelizes across these workers; command-list recording is per-pass jobs
- `ECS_AND_DATA_ORIENTED.md` — systems run as `parallel_for` over archetype chunks on this scheduler
- `PERFORMANCE_AND_PROFILING.md` — frame budget, false-sharing analysis, Tracy fiber instrumentation
- `PHYSICS_MATH_AND_SIMULATION.md` — physics islands scheduled as jobs; determinism requirements
- `CPP23_26_AND_MODERN_PATTERNS.md` — coroutines as an alternative task representation, `Handle<T>`, atomics
