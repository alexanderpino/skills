# ADR-NNNN: {Short, imperative title}

> Engine ADR template. Use Michael Nygard format plus the engine-specific
> sections below. Every architecturally significant change (new subsystem,
> cross-cutting contract, platform expansion, perf-critical data layout) MUST
> land an ADR in `/docs/adr/` before the implementation PR is merged.

## Status

`Proposed` | `Accepted` | `Superseded by ADR-XXXX` | `Deprecated`

## Date

`YYYY-MM-DD` (ISO 8601). Update when the status changes.

## Context

What is the forcing function? Describe the problem, the constraints (platform,
perf budget, team size, ship date), and the current behavior. Link to the
issue tracker, design docs, and any prior art. Two to four paragraphs.

## Decision

One or two paragraphs stating the chosen approach in the active voice ("We
will ..."). Name the specific APIs, data structures, and ownership model.
Identify the engine-wide invariants that are added or changed.

## Consequences

### Positive

- Enumerated wins: perf, clarity, compile time, tool ergonomics, platform reach.

### Negative

- Costs: migration work, new invariants developers must remember, increased
  complexity in some subsystem. Be honest; future readers rely on this.

### Neutral

- Side effects that are neither wins nor losses: renames, dependency bumps,
  doc updates.

## Performance Impact

Required for any change touching the render, simulation, or memory tiers.

| Metric               | Before    | After     | Delta     | Capture            |
| -------------------- | --------- | --------- | --------- | ------------------ |
| Frame time (ms, P50) |           |           |           | tracy://...        |
| Frame time (ms, P99) |           |           |           |                    |
| CPU main thread (ms) |           |           |           |                    |
| CPU worker avg (ms)  |           |           |           |                    |
| GPU frame (ms)       |           |           |           | PIX .wpix / RGP    |
| Persistent mem (MiB) |           |           |           |                    |
| Per-frame mem (MiB)  |           |           |           |                    |
| Bandwidth (GiB/s)    |           |           |           |                    |

Include the hardware and scene used (e.g. "PS5 devkit, Sponza + 4k dynamic
agents, Release config, PGO on"). Captures MUST be reproducible from source.

## Platform Compatibility

| Platform | Supported | Notes                                               |
| -------- | --------- | --------------------------------------------------- |
| PS5      | Yes/No    |                                                     |
| Xbox SX  | Yes/No    |                                                     |
| Switch 2 | Yes/No    |                                                     |
| Windows  | Yes/No    | D3D12 / Vulkan matrix                               |
| macOS    | Yes/No    | Metal 3, Apple Silicon minimum                      |
| Linux    | Yes/No    | Vulkan 1.3                                          |
| iOS      | Yes/No    |                                                     |
| Android  | Yes/No    | Vulkan 1.1 min spec                                 |
| VR       | Yes/No    | Quest 3 / PSVR2 specifics                           |

Any "No" row must be justified with a migration plan or a date for follow-up.

## Profiler Evidence

- Flamegraph (before): `/profiling/adr-NNNN/before.svg`
- Flamegraph (after):  `/profiling/adr-NNNN/after.svg`
- Tracy capture: `/profiling/adr-NNNN/*.tracy`
- GPU capture:   `/profiling/adr-NNNN/*.rdc` (RenderDoc) or `*.wpix` (PIX)
- Memory capture: `/profiling/adr-NNNN/*.pmlx` (WPA) or heaptrack session

## Alternatives Considered

### Alternative A: {name}

Summary, why rejected. At minimum: perf characteristic, risk, migration cost.

### Alternative B: {name}

Summary, why rejected.

(Include more as needed; at least two alternatives are required so reviewers
can confirm the chosen option is actually better than the near-misses.)

---

# Worked example

## ADR-0001: Adopt archetype-based ECS over OOP hierarchy

### Status

Accepted

### Date

2024-11-03

### Context

The legacy gameplay layer used a deep `GameObject` class hierarchy with virtual
dispatch on `Tick` and per-component `shared_ptr`. Profiling on PS5 showed 4.3
ms/frame spent in `GameObject::Tick` virtual calls alone at 6k active actors,
with L2 miss rates above 18 % in the simulation stage. Memory fragmentation in
the persistent heap grew unbounded during long play sessions, and the mobile
target could not hit 60 Hz on any device in our test matrix.

We also need to support data-oriented workflows that align with the job system
roadmap (work-stealing, structured parallelism) and with the new animation and
physics solvers, both of which are written against contiguous SoA storage.

Team size: 9 gameplay engineers, 4 systems engineers. Ship date: 14 months.

### Decision

We will adopt an archetype-based ECS (entities keyed by composition of
components, stored as SoA chunks of 16 KiB) as the canonical runtime
representation for gameplay state. Entity ids are 64-bit opaque handles
(32-bit index + 32-bit generation). Systems are stateless functors taking a
`World&` and a `float dt`, registered with the scheduler and invoked on worker
threads. The existing `GameObject` facade is kept as a thin compatibility
shim for one release, then removed.

Tooling changes: editor inspector and serializer reflect components via the
new `EngineReflect` macro set; save games gain a version-salted format.

### Consequences

#### Positive

- Simulation stage dropped from 4.3 ms to 1.1 ms at 6k agents on PS5.
- L2 miss rate in `TransformSystem` fell from 18 % to 3 %.
- Mobile (Pixel 6a) now holds 60 Hz at 3k agents, previously 42 Hz.
- Job system utilization rose from 48 % to 81 % on an 8-worker config.
- Removes 14k lines of virtual-dispatch scaffolding.

#### Negative

- All gameplay code migrates to the new component API; estimated 3 engineer-
  months of porting.
- Debugger visualizers must be rewritten (natvis for archetype chunks).
- Hot-reload story regresses for one release while we rebuild the watcher.
- Save-game compatibility breaks; migration tool required.

#### Neutral

- Renames: `Actor` -> `Entity`, `Component` (OOP) -> `LegacyComponent`.
- New dependency on the `engine::reflect` library (already in-tree).

### Performance Impact

| Metric               | Before    | After     | Delta     | Capture                         |
| -------------------- | --------- | --------- | --------- | ------------------------------- |
| Frame time (ms, P50) | 17.8      | 12.4      | -5.4      | tracy://sim-scene-alpha         |
| Frame time (ms, P99) | 22.1      | 14.9      | -7.2      | tracy://sim-scene-alpha         |
| CPU main thread (ms) | 9.6       | 5.2       | -4.4      | /profiling/adr-0001/main.tracy  |
| CPU worker avg (ms)  | 6.2       | 4.8       | -1.4      |                                 |
| GPU frame (ms)       | 6.1       | 6.1       | 0.0       | unchanged (render pass-through) |
| Persistent mem (MiB) | 612       | 548       | -64       | heaptrack capture attached      |
| Per-frame mem (MiB)  | 38        | 31        | -7        |                                 |
| Bandwidth (GiB/s)    | 11.2      | 7.4       | -3.8      | PIX counters, PS5 devkit        |

Scene: Sponza + 6k AI agents + 200 physics bodies, Release config, PGO on,
PS5 devkit (16 GB), single 4k render target.

### Platform Compatibility

| Platform | Supported | Notes                                                    |
| -------- | --------- | -------------------------------------------------------- |
| PS5      | Yes       | Primary target; all perf numbers above                   |
| Xbox SX  | Yes       | Parity verified, within 3 % of PS5                       |
| Switch 2 | Yes       | 60 Hz at 2k agents; 30 Hz mode at 4k agents              |
| Windows  | Yes       | D3D12 and Vulkan paths validated                         |
| macOS    | Yes       | Apple M2 or newer; M1 falls back to reduced agent budget |
| Linux    | Yes       | Vulkan 1.3; CI runs Ubuntu 24.04                         |
| iOS      | Yes       | A15+; older devices disabled in store manifest           |
| Android  | Yes       | Pixel 6 / SD 8 Gen 2 baseline; lower devices reduced LOD |
| VR       | Yes       | Quest 3 and PSVR2 both hit 90 Hz at 1.5k agents          |

### Profiler Evidence

- Flamegraph (before): `/profiling/adr-0001/before.svg`
- Flamegraph (after):  `/profiling/adr-0001/after.svg`
- Tracy captures:      `/profiling/adr-0001/ps5-before.tracy`,
                       `/profiling/adr-0001/ps5-after.tracy`
- PIX capture:         `/profiling/adr-0001/ps5-after.wpix`
- Heaptrack sessions:  `/profiling/adr-0001/heap-before.zst`,
                       `/profiling/adr-0001/heap-after.zst`

### Alternatives Considered

#### Alternative A: Retain OOP hierarchy, add SoA caches ad-hoc

Add parallel SoA arrays for the hottest components (Transform, AIBrain) while
keeping the `GameObject` tree authoritative. Rejected: the dual-representation
synchronization cost measured at 1.4 ms/frame and the model bleeds complexity
into every new component. It also does not unblock the job-system roadmap.

#### Alternative B: Entity-component "sparse set" ECS (EnTT-style)

A registry of sparse sets per component type, no archetype chunking. Simpler
to implement and retrofit. Rejected because iteration performance on our
reference scene was 1.8x slower than archetype chunks, and our simulation is
iteration-bound. Sparse sets also complicate the deterministic replay story
because iteration order depends on insertion history.

#### Alternative C: Data-driven scripting VM (Lua-like) as the entity model

Model entities as scripted tables and JIT-compile hot paths. Rejected: the
team has no VM expertise, and initial spike showed 7 ms/frame overhead in the
interpreter alone before any JIT work. Too risky for the ship window.
