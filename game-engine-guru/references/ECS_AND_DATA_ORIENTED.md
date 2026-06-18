# ECS & Data-Oriented Design

Reference document for the entity model — Pillar 5 and the data-oriented spine (Pillar 1). Audience: senior gameplay/engine engineers. This file is the implementation-level deep dive behind the authoritative rules in `SKILL.md` §"ECS Architecture Rules". Read those rules first; this file explains *how* to build the storage and query machinery that makes them hold.

## Table of Contents

- Why Archetypes
- Chunk Storage Layout
- The Archetype Graph (structural changes)
- Entities, Handles & Generations
- Queries & Iteration
- Entity Command Buffers (deferred structural change)
- Change Detection & Versioning
- Parallel Scheduling of Systems
- GameplayECS vs. VisualECS
- Singletons, Relationships & Anti-Patterns

---

## Why Archetypes

An **archetype** is the set of component types an entity has. All entities sharing an archetype are stored **together**, one contiguous array per component (SoA by construction). This is the archetype/chunk model used by Unity DOTS, Bevy, and Flecs — chosen over the alternatives because it makes the common operation (iterate every entity matching a component set) a **linear, prefetchable, branch-free stream**.

Contrast the storage models so you can defend the choice:

| Model | Iteration | Add/remove component | Random access by entity | Best for |
|-------|-----------|----------------------|-------------------------|----------|
| **Archetype (chunk)** | Fastest — contiguous SoA, cache-perfect | Moves entity to another archetype (copy) | Indirect (entity→chunk lookup) | Iteration-heavy simulation (the AAA default) |
| Sparse set (e.g. EnTT) | Fast — dense arrays per component | Cheap (no move) | O(1) | Many ad-hoc add/remove, editor tooling |
| Archetype + sparse hybrid | Tunable | Tunable | Tunable | Engines that want both (Flecs) |

The archetype model pays a **cost on structural change** (adding/removing a component physically moves the entity's data to a new archetype). You hide that cost by batching structural changes through an Entity Command Buffer (below). If your workload is structural-change-dominated rather than iteration-dominated, sparse-set is the honest choice — say so rather than cargo-culting archetypes.

---

## Chunk Storage Layout

An archetype's entities are stored in fixed-size **chunks** (16 KB is the typical sweet spot — fits comfortably in L1/L2 working sets and amortizes per-chunk overhead). Within a chunk, each component type gets its own tightly-packed sub-array (SoA):

```
Chunk (16 KB):
┌───────────────────────────────────────────────────────────┐
│ header: archetype id, entity count, per-type change version│
├───────────────────────────────────────────────────────────┤
│ Entity[]     e0 e1 e2 ... eN                                │  ← entity ids (for back-reference)
│ Position[]   p0 p1 p2 ... pN                                │  ← one stream per component
│ Velocity[]   v0 v1 v2 ... vN                                │
│ Mesh[]       m0 m1 m2 ... mN                                │
└───────────────────────────────────────────────────────────┘
capacity N = (chunkSize - header) / sum(sizeof(component))
```

- **Components are plain data** — `static_assert(std::is_trivially_copyable_v<T> && std::is_standard_layout_v<T>)` at registration (SKILL.md ECS rule 1). This is what makes "move entity = memcpy columns" legal.
- **Iteration is per-stream:** a system reading `Position`+`Velocity` walks two contiguous arrays in lockstep — the hardware prefetcher nails it, SIMD vectorizes it, zero pointer chasing.
- **Alignment:** align each component sub-array to its natural alignment (and SIMD-friendly 16 B for vector types) so loads don't straddle cache lines.
- **Chunk = the unit of parallelism** (below) and the unit of change-version tracking (below). Don't make chunks so large that one job's chunk doesn't fit in cache, nor so small that per-chunk overhead dominates.

---

## The Archetype Graph (structural changes)

Adding or removing a component changes an entity's archetype. Computing the destination archetype by hashing the new component set every time is wasteful; instead, cache the transitions as a **graph**:

```
Archetype{Position, Velocity}
   │  + Mesh   ──────────────▶  Archetype{Position, Velocity, Mesh}
   │  - Velocity ────────────▶  Archetype{Position}
```

Each archetype stores edges keyed by component type → resulting archetype, so "add `Mesh`" is one edge traversal, not a hash-set rebuild. Moving the entity then:

1. Allocate a slot in the destination archetype's chunk (or a new chunk).
2. `memcpy` each shared component column from source to destination.
3. Default-init added components; drop removed ones.
4. Swap-remove from the source chunk (move the last entity into the hole, fix its lookup), update both entities' entity→location records.

Swap-remove keeps chunks dense (no holes) at the cost of reordering — which is fine because **systems must never depend on intra-chunk order** (it changes as entities are added/removed).

---

## Entities, Handles & Generations

An entity is **not** a pointer or an object — it's a 64-bit handle (SKILL.md Forbidden Patterns: no `GameObject`, no `shared_ptr` for gameplay refs):

```cpp
struct Entity { uint32_t index; uint32_t generation; };   // 64-bit POD
```

- **Generation defeats use-after-free.** When an entity is destroyed, its slot's generation increments. A stale `Entity` (captured before destruction) fails the `generation == slots[index].generation` check on lookup → resolves to "dead," no dangling access. Same mechanism as `Handle<T>` everywhere else in the engine.
- **`index`** points into a slot table that maps the entity to its current `{archetype, chunk, row}`. Structural changes update this record; the `Entity` value held by gameplay code never changes.
- Resolving an entity to its components is therefore **indirect** (slot lookup → chunk → row). That's the deliberate trade: iteration is perfect, random by-entity access costs an indirection. Design gameplay to iterate, not to chase entities one at a time.

---

## Queries & Iteration

A query is a **compile-time-specified** component filter (SKILL.md ECS rule 5 — no runtime string lookups, no per-entity hash maps):

```cpp
// Filter resolved to an archetype mask at compile time.
world.Query<Position, Velocity, const Mesh>()
     .ForEach([](Position& p, Velocity& v, const Mesh& m) { /* ... */ });
```

- **Matching** = "which archetypes contain all of {Position, Velocity, Mesh}?" Computed once and **cached**; when a new archetype is created, incrementally test it against live queries and append matches. Steady-state iteration touches zero hashing.
- `const T` means read-only access — the scheduler uses this to parallelize (read-read doesn't conflict; see scheduling below).
- **Filters:** `With<T>`/`Without<T>` (presence/absence), `Changed<T>` (version filter, below), optional `Maybe<T>`. Keep filters archetype-resolvable so they prune whole chunks, not per-entity branches.
- **Iterate chunk-by-chunk, then row-by-row.** The outer loop is over matching chunks (often itself a `parallel_for`); the inner loop is the tight SoA stream. Hand the inner loop contiguous spans so it vectorizes.

---

## Entity Command Buffers (deferred structural change)

**Never add/remove components or create/destroy entities while iterating** (SKILL.md ECS rule 4) — it would move chunk memory out from under the loop and invalidate the very arrays you're walking. Instead, **record** structural changes into an Entity Command Buffer (ECB) on the worker, and **play them back** at a sync point:

```cpp
// On a worker, during iteration — record, don't mutate:
ecb.AddComponent(entity, Burning{ duration });
ecb.DestroyEntity(deadEntity);
ecb.CreateEntity(bulletArchetype, spawnData);

// At a system-boundary sync point on the main thread — apply:
ecb.Playback(world);   // now the structural changes happen, in recorded order
```

- **Per-worker ECBs** (no contention), merged deterministically at playback in a defined order (by system, then by record index) so the result is reproducible — critical for netcode/physics determinism.
- ECBs allocate from the **frame arena**; playback frees them with the frame reset. Zero heap churn.
- Batch like-changes at playback (all "add `Mesh`" to the same destination archetype move together) to amortize the archetype transition.
- Deferred creation returns a **placeholder entity** that playback remaps to a real one — gameplay can reference the not-yet-created entity within the same frame.

---

## Change Detection & Versioning

Skip work on data that didn't change (SKILL.md ECS rule 7). Maintain a **monotonic global version** bumped each system tick, and store **per-chunk, per-component a "last written" version**:

```cpp
// A system that writes Position bumps the chunk's Position version to the global tick.
// A downstream system filters Changed<Position> → skip chunks whose
// Position version < the consumer's last-seen version.
if (chunk.version<Position>() <= consumer.lastSeen) continue;   // whole chunk skipped
```

- **Granularity is the chunk**, not the entity — cheap (one version per component per chunk) and matches how data is touched. The trade-off: touching one entity marks the whole chunk dirty (false positives), which is the right call vs. per-entity bookkeeping overhead.
- **Write access marks dirty automatically** — a non-`const` component in a query bumps the version on iteration. Read-only (`const`) access never dirties. This is another reason to declare `const` correctly.
- Drives reactive systems (rebuild a transform hierarchy only for moved entities), GPU upload (re-upload only changed instance data — ties into GPU-driven rendering's persistent instance buffer), and netcode delta replication (serialize only changed components — SKILL.md §Networking).

---

## Parallel Scheduling of Systems

Systems are stateless transformations (SKILL.md ECS rule 3); the scheduler runs them concurrently when their data access doesn't conflict:

- **Access declaration:** each system declares the components it reads vs. writes (derived from its query types: `const T` = read, `T&` = write).
- **Conflict rule:** two systems can run in parallel unless one **writes** a component the other reads or writes (read-read is fine). This is a read-write dependency graph over component types → scheduled on the job system (`JOB_SYSTEM_AND_FIBERS.md`).
- **Intra-system parallelism:** a single system's chunk loop is a `parallel_for` over matching chunks — each job owns disjoint chunks, so no synchronization inside the system.
- **Structural changes are the sync point:** ECB playback happens between system batches, on the main thread, where no system is iterating. That's the one place the archetype layout is allowed to change.
- Determinism: with the same data, the same access graph yields the same schedule; ECB merge order is fixed. Combined with the job system's deterministic mode, the whole simulation is replayable.

---

## GameplayECS vs. VisualECS

SKILL.md Pillar 5 splits the ECS in two — design them differently:

- **GameplayECS (CPU-resident).** Complex logic, structural changes, relationships, the archetype machinery above. Sized for thousands–hundreds-of-thousands of gameplay entities. Optimized for flexible queries and change detection.
- **VisualECS (GPU-resident, in VRAM).** Millions of visual-only entities (instances, foliage, debris) whose data lives in GPU buffers and is consumed by GPU-driven culling/draw (`FRAME_GRAPH_AND_GPU_DRIVEN.md`). Don't run gameplay queries over these — they're a flat, GPU-owned instance stream. The bridge is one-way: gameplay writes spawn/despawn/transform deltas into the persistent instance buffer; the GPU never writes back into GameplayECS.

Keeping these separate is what lets the engine scale from Pong to a 15-billion-instance open world (SKILL.md §Scalability) without paying gameplay-ECS overhead per blade of grass.

---

## Singletons, Relationships & Anti-Patterns

- **Singletons are components on a singleton entity** for *gameplay* state (`world.GetSingleton<InputState>()`) — fine. But **core engine systems (`IGraphicsDevice`, `IJobSystem`) must never live in the ECS** (SKILL.md ECS rule 6); inject them, don't smuggle them in as components.
- **Relationships/hierarchy:** store parent as a component (`Parent{ Entity }`) and maintain child lists separately; or use a dedicated relationship store (Flecs-style). Don't rebuild a pointer-chasing scene graph — that's the OOP god-object the ECS exists to kill.
- **Forbidden** (SKILL.md): components with methods/virtuals/non-trivial ctors; mutating structure mid-iteration; `std::unordered_map<Entity, T>` as "component" storage in a hot path (cache-hostile — use a real archetype/sparse column); storing `shared_ptr` in components.
- **Right-sizing:** a tiny game doesn't need GPU VisualECS or change-version machinery active — these tick at ~0 when unused (zero-overhead principle). Don't force the full apparatus on content that doesn't need it.

---

## See Also

- `SKILL.md` §"ECS Architecture Rules (authoritative)" — the 7 rules this file implements
- `JOB_SYSTEM_AND_FIBERS.md` — the scheduler systems run on; `parallel_for` over chunks
- `FRAME_GRAPH_AND_GPU_DRIVEN.md` — VisualECS feeds GPU-driven culling; change detection drives instance re-upload
- `CPP23_26_AND_MODERN_PATTERNS.md` — `Handle<T>`/generations, concepts for component constraints, EASTL containers
- `NETWORKING_AND_MULTIPLAYER.md` — delta replication consumes change detection
