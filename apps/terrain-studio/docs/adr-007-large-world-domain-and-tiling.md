# ADR 007 - Versioned world domain and bounded global-substrate evaluation

**Status:** accepted
**Date:** 2026-08-01

## Context

Terrain Studio currently treats a world as one globally sized field. `RES` is the field width,
`terrainDef.scale` is both horizontal extents, `cellSizeM()` is `scale/RES`, and hex height is
derived from the same width. Clean, default, and template creation reset this state and evaluate a
graph immediately. Imported PNG/image and RAW/R16 sources are resampled to the active field without a
stable physical-metadata or provenance record. CPU fields and GPU render targets are monolithic; GPU
render-target caches currently have no streaming-chunk residency/eviction contract.

The user-selected target is a 100 km-class rectangular world at author-controlled detail, including
0.5 m `cellSizeM`/sample spacing: adjacent vertex posts are 0.5 m apart and each authored square
cell/quad is 0.5 m across. This is not a claim about the actual dimensions of any shipped game. A
100 km square at 0.5 m vertex spacing has `200001` samples per axis: `40,000,400,001` samples and
`160,001,600,004` bytes for one square R32F field. Equal-cell hex deployment is approximately
46.2 billion samples and 184.8 GB for one field. An illustrative 5 km evaluation partition is 20
regions per axis, or 400 regions. It is arithmetic, not a default: real evaluation regions,
streaming chunks, build patches, and pages are separate, much smaller units selected from measured
budgets. Neither the whole high-detail field nor its graph intermediates can exist in browser memory.

Terrain Architect chapters 08 and 14 make two constraints architectural rather than optional:
GLOBAL nodes such as flow accumulation and stream power require a complete domain, while LOCAL and
NEIGHBOURHOOD nodes can evaluate in bounded regions only when the latter receive an apron at least as wide as
their transitive support radius. Terrain Renderer chapters 06, 09, and 16 require bounded residency,
cancellation, an always-renderable coarse ancestor, and camera-relative coordinates for large
worlds. ADR 003 already requires pure export requests, explicit emitters, full package preflight,
and GLOBAL evaluation before export slicing.

## Decision drivers

- Express independent width and height in physical units without making display units evaluator
  state.
- Preserve existing documents and numerical behavior while moving new heightfields to an explicit
  vertex-posted contract.
- Reject impossible browser/GPU/build requests before allocating or replacing the open document.
- Keep drainage and other GLOBAL structure coherent across the entire authored world.
- Make square and pointy odd-r hex regions deterministic under arbitrary scheduling order.
- Bound CPU/GPU memory by the active preview/build set, not total world sample count.
- Keep import evidence distinguishable from defaults and user-authored interpretation.
- Extend Sprint 6 manifests and Sprint 8 reusable definitions without duplicating their ownership.

## Considered options

### A. Increase `RES` and keep one monolithic field

This is the smallest code change and fails the target by orders of magnitude. One square R32F height
field is about 160 GB before graph intermediates, GPU copies, auxiliary fields, history, or export
staging. Browser texture dimensions and typed-array/index limits fail earlier. Rejected.

### B. Evaluate the complete graph independently in each high-detail region

This bounds one allocation but changes the terrain science. GLOBAL drainage loses upstream area at
region edges; NEIGHBOURHOOD nodes without sufficient aprons lose support; region-local seeds and hex
parity create boundary drift. A cosmetic seam crossfade can conceal some height discontinuities but
cannot repair drainage, mass transport, normals, masks, or shared vertex identity. Rejected.

### C. One full-domain global substrate plus deterministic high-detail regions - selected

Represent the world with a versioned metre-space domain. Evaluate GLOBAL nodes once over an authored
or preflight-derived full-domain substrate. Sample completed global results into deterministic detail
regions in world coordinates, then evaluate LOCAL and finite-NEIGHBOURHOOD detail over region cores plus
declared aprons. Keep only a bounded hierarchical active set and export/import the hierarchy through
a versioned manifest.

### D. Backend-only distributed generation

A service could hold larger global arrays and parallelize evaluation regions, but it does not solve the
authoring, schema, import provenance, preview precision, determinism, or offline-PWA contracts. It
would also add an external dependency to a runtime that currently has none. A later backend may
execute the same contracts; it is not the Sprint 9 foundation.

## Decision

### World domain and posting

Saved graphs own `WorldDomain/1`:

- Float64 CPU origin in internal metres and independent positive width/height in metres;
- authoring/display units `m | km | mi | ft`, which never enter evaluator/cache identity except
  through their converted metre values;
- square or pointy odd-r hex lattice with an explicit global index-to-world basis;
- resolution authored as requested spacing or explicit sample counts, with actual sample counts and
  actual spacing derived, displayed, and persisted;
- explicit posting (`vertex` for new heightfields, `legacy-cell` for migrated current documents);
- vertical datum descriptor and finite metre range, with unknown external datum kept unknown.

For vertex-posted height on an integral axis, `samples = extent/spacing + 1`. Explicit sample mode
uses `spacing = extent/(samples-1)`. Any rounding needed to make an integral grid is reported as
requested versus actual; no UI rounds silently.

For square terrain, the resulting persisted sample spacing is `cellSizeM`: the distance between
adjacent vertex posts and width of one authored quad. `cellSizeM` never denotes an evaluation
region, streaming chunk, build patch, cluster page, or world partition.

Legacy documents migrate without a numerical reinterpretation: `scale` becomes both extents,
current `RES` and the current global hex row derivation become explicit sample counts, and actual
legacy spacing remains `scale/RES` under `posting: legacy-cell`. Existing vertical `height` and
`baseElevation` become the local vertical frame. Converting a migrated document to vertex posting is
an explicit resample/version action, not load-time cleanup.

### Creation and feasibility

All clean, default, and template creation routes open one New Terrain dialog before document reset or
resource allocation. The dialog computes, with overflow-safe integer arithmetic:

- sample dimensions, logical cells/faces, and exact R32F bytes per field;
- active CPU map/scratch bytes from scheduler declarations;
- active GPU texture/render-target/upload bytes from format and simultaneous-resource declarations;
- build output and staging bytes under ADR 003;
- monolithic or bounded recommendation, evaluation partition, aprons, global substrate, and bounded active set.

Confirmation is disabled when an axis or byte product is unsafe, required dimensions exceed queried
browser/WebGL limits, or authored CPU/GPU/build budgets are exceeded. `MAX_TEXTURE_SIZE` is not
treated as VRAM capacity. Unknown headroom remains unknown and requires an authored/session budget.
Bounded mode must prove one expanded evaluation region and its whole active cone fit; it is not an exemption.

No graph, field, texture, worker, region, or emitter staging allocation occurs until a passing dialog
is confirmed. Cancel leaves the current document and history unchanged.

### Import facts and authored interpretation

Imported height sources store `HeightSourceMetadata/1`: filename, format, bytes/checksum, sample
width/height, bit depth/channel/endianness, optional physical extent/spacing/datum, and field-level
provenance `embedded | inferred-default | user-override | unknown`. Embedded facts are immutable;
inferred defaults and authored overrides remain separate records and the sidebar displays both source
and effective values.

PNG and headerless RAW/R16 normally do not contain physical extent, spacing, or datum. GeoTIFF and
SRTM may carry or imply those values, but current Terrain Studio does not decode GeoTIFF. ADR 007 does
not promise that codec. A later codec/library story must add it explicitly. A validated Sprint 6
Terrain Studio manifest may provide embedded world metadata.

### Global substrate and evaluation regions

GLOBAL nodes evaluate once on the complete rectangular global substrate. Its spacing is authored or
derived by a preflight that accounts for the global active cone; the actual spacing and approximation
tier are visible and persisted. A GLOBAL request scoped to one evaluation region is rejected before kernel
dispatch. Completed global outputs are sampled into each evaluation region in metre-space.

LOCAL nodes evaluate over the region core plus any downstream-required apron. A
NEIGHBOURHOOD(radius) node may run only when the expanded region covers its declared transitive
support. Aprons are cropped after the final dependent result, not after each node. Finite-detail
tiling cannot be used for unbounded transport.

Correct region boundaries are constructed, not blended:

- position-pure generators use global metre/lattice coordinates;
- adjacent square regions share one copied bit-identical vertex row/column;
- pointy odd-r hex regions retain the global row index/parity and D6 metric across region edges;
- region identity is canonical `(level,x,y)` with Float64 origin, metre extent, core/apron rectangle,
  posting, parity where applicable, and content hash;
- position-pure stochastic fields hash `(rootSeed,nodeId,globalSampleCoordinate)`;
- region-index RNG streams are allowed only for work wholly owned by the region core and cannot author
  shared edges or apron values.

Cosmetic crossfade is not a correctness mechanism. Rendering may morph between valid LOD
representations, but generation, attributes, and global fields must already satisfy the boundary
contract.

### Hierarchical preview and bounded memory

The browser holds a streaming hierarchy with a pinned renderable global/root representation and a
bounded set of budget-derived chunks. Requested, loading, resident, renderable, and evictable states are byte-accounted.
Eviction is priority-aware LRU over evictable entries; in-flight work and pinned ancestors count
against explicit budgets. Parent/root coverage remains renderable until the complete replacement is
ready, so cold regions are coarse rather than absent.

Evaluation and upload carry a generation counter. Camera/domain/graph/quality changes cancel obsolete
requests; late completions are discarded and cannot upload or enter the cache. A 100 km world never
materializes all regions from the illustrative 5 km partition, all hierarchy levels, or a
40-billion-sample graph. Actual chunks are much smaller and selected by the active byte/time budget.

ADR 008's renderer-facing `FieldPageProfile/1` refines this hierarchy without changing Sprint 9's
evaluation-region ownership. Each profile authors power-of-two core cells per axis, stores
`coreCells+1` vertex posts, advances adjacent pages by the shared-edge stride `coreCells`, declares
consumer aprons, registers every child with an aligned parent, and names the deterministic 2x
downsample filter. Conservative min/max/error headers are persisted field-page metadata; error is
for residency priority/quality labels, never geometry topology.

A terrain edit creates a new monotonic `surfaceVersion`. Bounded local edits invalidate intersecting
leaf cores, apron dependants, and registered ancestors; domain or GLOBAL changes invalidate the
affected hierarchy broadly. ADR 008 S10.2 owns renderer-page root pinning, finest-resident-ancestor
fallback, generation cancellation, and atomic promotion while the old complete front remains
renderable. These runtime-page obligations are not deferred to feedback/eviction work.

Authoritative world and camera positions are Float64 on CPU. Each draw subtracts the camera in
Float64 and uploads local Float32 coordinates. Near-field shaders do not receive large absolute world
positions.

### Export/import and reusable definitions

After Sprint 6, the normative export manifest gains a versioned world-domain/region-hierarchy branch:
domain/posting/basis, substrate identity, canonical region indices/origins/extents, core/apron
rectangles, shared-edge ownership, content hashes, product artifacts, and approximation/quality
metadata. ADR 003's purity, complete-package validation, path checks, staging budget, cancellation,
and one explicit emitter action remain unchanged. Import validates the whole package and all hashes
before creating a document; mixed or missing region/substrate versions are errors.

After Sprint 8, reusable definitions may declare only compatibility requirements that affect
evaluation: lattice, LOCAL/NEIGHBOURHOOD/GLOBAL scope, support radius, and spacing bounds. A
definition remains world-domain independent and cannot embed, mutate, or replace its containing
document's `WorldDomain/1`. Definitions without a real domain constraint gain no metadata.

## Consequences and gates

- Current `RES`/`terrainDef.scale` access cannot be replaced in one unversioned rewrite. Compatibility
  accessors and old-document fixtures remain until every owner reads `WorldDomain/1` context.
- A 100 km at 0.5 m `cellSizeM` target becomes authorable/buildable as bounded work, not monolithic
  work. The illustrative 5 km partition is exactly 20 by 20, or 400 evaluation regions, but does
  not set the implementation's region, chunk, patch, or page size.
- Global substrate resolution is an explicit approximation choice. The viewport and manifest label
  it; evaluation regions cannot imply full-resolution GLOBAL science.
- Square, hex, rectangular terminal regions, source provenance, cache identity, cancellation, and
  memory accounting become persistent contracts with migration cost.
- GeoTIFF remains unsupported until a separate codec/library decision and implementation story.
- Distributed/backend execution remains possible because domain, region, seed, cache, and manifest
  identity are executor-independent.

Required gates are the Sprint 9 plan's exact four-scenario arithmetic, no-allocation-before-confirm
spies, legacy migration identity, import-provenance fixtures, monolithic-equals-single-region oracle,
GLOBAL-per-region rejection, shared-boundary/apron/hex-parity mutations, schedule-order determinism,
bounded non-empty memory peaks, cancellation with no late upload, manifest round-trip, and production
built-PWA validation.

## Grounding sources

- Installed Terrain Architect `references/08-output-contract.md`: vertex/pixel posting, physical
  manifest, R32F working precision, GLOBAL-first bounded evaluation, support-radius aprons, shared edge floats,
  hex basis/parity, camera/region-relative coordinates.
- Installed Terrain Architect `references/14-graph-runtime.md`: evaluation context, LOCAL /
  NEIGHBOURHOOD / GLOBAL declarations, full-domain GLOBAL preview, content-addressed cache, byte-LRU,
  resolution pyramid, cancellation, and out-of-core scheduling.
- Installed Terrain Renderer `references/06-tiled-streaming.md`: hierarchy, residency states,
  cancellation, complete renderable front, byte budgets, priority-aware eviction, and seam contract.
- Installed Terrain Renderer `references/09-planetary-precision.md`: Float64 authority and
  camera-relative Float32 rendering for worlds beyond approximately 10 km.
- Installed Terrain Renderer `references/16-tool-viewports.md`: asynchronous labelled preview tiers,
  stale-state honesty, dirty-region uploads, and export parity.
- Current `src/legacy.js`, `src/core/gpu.js`, and `src/plugins/gen/import.js`: global `RES`,
  `terrainDef.scale`, immediate new-document evaluation, monolithic fields/render targets, current
  PNG/image and RAW/R16 import behavior, and missing import provenance.
