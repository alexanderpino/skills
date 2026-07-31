# ADR 002 — Typed multi-output DAG

**Status:** accepted
**Date:** 2026-07-31

## Context

Terrain Studio currently has one scalar result per node. Edges are `{from,to,slot}`, the three
evaluators cache `nd._field`, and graph snapshots persist destination slot indices. This is measured in
`src/legacy.js` under **GRAPH MODEL**, `evalGraph`, `evalGraphProgressive`, and `evalExact`.
Chapter 14 of the Terrain Architect corpus requires pure nodes, typed input/output ports,
demand-driven evaluation, stable versioned type IDs, world-unit parameters, and content-addressed
cache keys. Chapters 08 and 27 require vector, categorical, state, and continued-state products that
a single `Float32Array` cannot identify safely.

The current semantic side channels are also measured, not inferred:

| Plugin | Mutable semantic side channel | Typed owner |
|---|---|---|
| `d_sunshadow` | `_solarShadow`, `_solarExposure` | S2.6 |
| `d_temperature` | `_temperatureC`, `_solarShadow`, `_solarExposure` | S5.1 |
| `d_heat` | `_temperatureC`, `_solarShadow`, `_solarExposure` | S5.1 |
| `d_wind` | `_wind` | S2.6 |
| `d_windmodify` | `_wind` | S5.1 |
| `snow` | `_snowLayer` | S5.3 |

`_inputError`, `_thumb`, `_xfMode`, and renderer-only SatMap/effect fields are UI state, not graph
values. They may remain outside semantic cache identity, but they may not be read as typed graph data.

## Decision drivers

- Preserve every existing primary result and saved document through a deterministic migration.
- Make field type, unit, range, lifecycle, and source-port identity mechanically checkable.
- Allocate and compute only demanded outputs while allowing one physical solve to emit an atomic set.
- Preserve exact downstream invalidation and reproducible cache identity.
- Keep the current synchronous browser runtime and GPU/CPU capability behavior.

## Considered options

### A. Eager object result per node

Every evaluator returns one plain object containing every output, and the node owns one cache entry.
This is simple, but it allocates all field-sized auxiliaries even when disconnected and cannot prove
per-output demand or invalidation.

### B. Typed per-output values with declared atomic groups — selected

Descriptors declare stable ports. Evaluation is requested by output ID or atomic group and returns a
runtime `Map<portId, value>`. Independent outputs remain lazy; a solve that necessarily produces
several values declares an atomic group and computes/caches it once.

### C. Keep one scalar edge and expose auxiliaries through selector nodes/global lookup

This minimizes runtime change but preserves hidden state, makes source identity ambiguous, and violates
chapters 14 and 27. It is rejected.

## Decision

### Descriptor and value contract

A plugin declares `inputs[]` and `outputs[]`. Every port has a stable plugin-local ASCII `id`, display
name, value kind, semantic field type, unit, storage format, range/finiteness policy, and required or
optional policy. Display names and array positions are never identifiers.

The initial closed value-kind set is:

- `scalarRaster`
- `vectorRaster`
- `labelRaster`
- `scalar`
- `featureSet`

This set covers the chapter-08/27 raster fields, world-space vectors, categorical basin IDs, scalar
controls, and authored source/guide features required by S2–S6. A new value kind changes the schema
and requires a later ADR/version.

Connections require equal value kind, dimensionally equal units, and equal semantic type unless the
destination explicitly declares a safe generic such as `anyScalarRaster`. There are no implicit
vector/scalar, label/continuous, normalization, visualization, or unit conversions.

Typed evaluators return `{ values: Map<portId, value> }`. One output may be marked `primary` only for
legacy compatibility. Existing evaluators adapt their `Float32Array` to that one declared output; new
plugins may not use the adapter.

### Edge and document migration

Document schema v2 stores edges as `{from,fromPort,to,toPort}`. An unversioned document is v1 and
migrates its source to the source plugin's primary output and its destination `slot` to the destination
port at that legacy index. Migration is idempotent. Unknown port IDs are load errors, never best-effort
rewiring. Undo, copy/paste, quick-create, cycle detection, dirty propagation, and test bridges use the
same stable IDs.

### Evaluation and cache ownership

The cache key is:

```text
hash(plugin type/version,
     canonical parameters,
     effective seed,
     relevant evaluation context and substrate version,
     demanded output or atomic-group ID,
     ordered upstream source-port cache keys)
```

The node instance ID is excluded except through the effective seed, matching chapter 14. Device is
excluded only for plugins that promise CPU/GPU tolerance equivalence; a device-specific plugin must
encode that restriction in its descriptor/version. Independent outputs allocate only on demand.
Atomic-group members compute, retain, and evict together. `_field` remains a temporary read-only alias
to the primary scalar raster; semantic data lives only in the output cache.

The three existing evaluation paths are migrated together so recursive, progressive, and exact
execution cannot disagree about port demand. The Legal Order validator runs after edit/load and before
evaluation; registration validates declarations, while graph validation rejects a derived-geometry
path that later crosses a height-writing output.

### Hydraulic atomic outputs

ADR 001's current one-readback height path remains valid when only height is demanded. When S3 demands
hydraulic state, one atomic GPU group emits `solidTop`, `soilDepth`, `sedimentDepth`, and Pipe velocity
`(u,v)`. Five channels cannot fit one RGBA texel. The selected representation is a two-texel-per-cell
`RGBA32F` atlas read by one `readPixels` call; unused channels are reserved and zeroed. The first texel
stores `solidTop`, `soilDepth`, `sedimentDepth`, and `velocityU`; the second stores `velocityV` and
reserved zeros. This costs 32 bytes/cell during readback versus 16 bytes/cell for one RGBA value, but
keeps one synchronization point.

Droplet actions separate erosion and deposition in two action channels before gather/apply. Capacity-
driven deposition increments `sedimentDepth`; erosion decrements loose cover before bedrock. Remaining
load at the lifetime cap remains `exportedOrSuspended` per ADR 001 and is never terminally dumped.
This makes state attribution measurable without changing the accepted terminal policy.

The atlas is a rectangular texture `2*fieldWidth` by `fieldHeight`. Cell `(x,y)` maps to texels
`(2*x,y)` and `(2*x+1,y)`, and readback uses that exact rectangle. Before allocation, require
`2*fieldWidth <= MAX_TEXTURE_SIZE`, `fieldHeight <= MAX_TEXTURE_SIZE`, both dimensions within
`MAX_VIEWPORT_DIMS`, framebuffer completeness, and `8*cellCount` Float32 elements (32 bytes/cell)
within the evaluator memory budget. If any check fails, the node reports the reason and uses the
existing deterministic CPU compatibility path; it never drops a channel or silently performs extra
GPU readbacks. Rectangular render-target/readback helpers are part of S3.1 because current helpers are
square-only.

## Consequences and gates

- A frozen v1 document must migrate v1→v2→v2 with identical topology, parameters, and primary bytes.
- Every pre-existing plugin at sprint-start count remains digest-identical with `skipped = 0`.
- An undemanded independent output records zero evaluator calls and zero field allocations.
- Requesting either atomic-group member computes the group once; requesting its sibling does not
  recompute it.
- Editing one source port invalidates only output cones that depend on that source port.
- Hydraulic height-only demand keeps one 16-byte/cell RGBA readback; state demand performs one
  32-byte/cell atlas readback. Tests assert one `readPixels` call in both cases.
- Atlas mapping and every capability preflight are tested; forcing each limit below the requested
  rectangle selects the labelled CPU path without changing the requested output set.
- The side-channel table above is the complete semantic migration debt at acceptance. Its rows may
  only be removed by their owner stories; new semantic side channels fail registration/review.

The cost is a schema migration and a coordinated evaluator/UI rewrite. The benefit is that later
state, hydrology, export, variables, and subgraphs build on one explicit contract rather than adding
new hidden channels.
