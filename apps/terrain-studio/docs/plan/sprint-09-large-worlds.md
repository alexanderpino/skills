# Sprint 9 - Large worlds: domain, bounded evaluation, and streaming preview `[E]`

**Planning status:** grounded and technically refined. **Implementation status:** NOT STARTED.

**Goal.** Let an author describe an independent-width/height world in physical units, see the real
cost before anything is allocated, and author a user-selected 100 km-class target through one
global substrate plus deterministic high-detail evaluation regions. The browser keeps only a
bounded active set of budget-derived streaming chunks;
it never constructs a 40-billion-sample in-memory graph.

**Depends on:** the domain schema, New Terrain dialog, and import-provenance slice may start from the
current baseline. Bounded graph scheduling depends on Sprint 2 typed ports/evaluation context. World
manifest export/import depends on Sprint 6. Reusable preset/subgraph constraints depend on Sprint 8
and are limited to the compatibility metadata that large-world reuse actually needs.

**Architecture gate:** [ADR 007](../adr-007-large-world-domain-and-tiling.md) is accepted and
normative. It extends, rather than replaces, [ADR 003](../adr-003-pure-export-emitter.md): Sprint 6
still owns pure emitters and package validation; Sprint 9 adds a globally evaluated substrate and a
bounded region schedule before those results are emitted.

**Target naming.** This plan specifies a **user-selected 100 km-class target**. It makes no claim
about the actual dimensions of *Star Wars Outlaws* or any other shipped game.

---

## Measured starting point

- `src/legacy.js` has one global width, `RES=512`; `fieldW()` returns `RES`, while `fieldH()` is
  `RES` for square and `round(RES*2/sqrt(3))` for pointy odd-r hex. Many kernels read those globals.
- `terrainDef` has one horizontal `scale` for both axes, one vertical `height`, `baseElevation`, and
  `lattice`. `cellSizeM()` is currently `terrainDef.scale/RES`.
- clean, default, and Canyon creation call `newTerrainDocument(...)`, reset `terrainDef`, construct
  and evaluate the graph immediately, and expose only a destructive-confirm prompt. There is no
  dimension or allocation preflight.
- Import supports browser-readable images and square little-endian 16-bit raw data. It resamples
  immediately to the active field and retains no filename, format, source dimensions, bit depth,
  physical extent, spacing, datum, or provenance classification in a stable metadata record.
- CPU fields are `Float32Array`; GPU render targets are cached by key/resolution and currently are
  not evicted. The browser therefore has neither a bounded streaming-chunk residency set nor a meaningful
  100 km-class allocation path.
- Existing Sprint 6 plans monolithic GLOBAL evaluation followed by export slicing. Sprint 9 does not
  weaken that rule: GLOBAL nodes evaluate once on the authored or derived full-domain substrate;
  only their completed result is sampled into bounded evaluation regions.

These are source constraints, not implementation commitments. In particular, replacing global
`RES` and `terrainDef.scale` is a versioned migration, not a local UI rename.

---

## Feasibility arithmetic

New height domains are vertex-posted. For axis extent `L` and exact spacing `s`, an integral domain
has `L/s + 1` samples; the `+1` is the shared terminal vertex. R32F bytes are
`sampleWidth * sampleHeight * 4`. Decimal MB/GB are used in the UI, with MiB/GiB available in the
details view. Hex equal-cell deployment uses the declared global hex basis and approximately
`2/sqrt(3)` times the square sample count for the same rectangular footprint and centre spacing.

| Scenario | Square vertex samples | Square R32F field | Equal-cell hex field | Required recommendation |
|---|---:|---:|---:|---|
| 1 km at 0.5 m | `2001 x 2001 = 4,004,001` | `16,016,004 B` (~16.0 MB) | ~4.62 M / ~18.5 MB | monolithic only if the active-cone budget passes |
| 10 km at 2 m | `5001 x 5001 = 25,010,001` | `100,040,004 B` (~100.0 MB) | ~28.9 M / ~115.5 MB | device/budget dependent; bounded evaluation available |
| 64 km at 2 m | `32001 x 32001 = 1,024,064,001` | `4,096,256,004 B` (~4.10 GB) | ~1.18 B / ~4.73 GB | bounded evaluation; monolithic rejected |
| 100 km at 0.5 m `cellSizeM` | `200001 x 200001 = 40,000,400,001` | `160,001,600,004 B` (~160.0 GB) | ~46.2 B / ~184.8 GB | bounded evaluation; monolithic rejected |

Here, `0.5 m` is the authored square-cell size/sample spacing: adjacent vertex posts are 0.5 m
apart. It is not a streaming-chunk, build-patch, page, or evaluation-region size.

For arithmetic only, partitioning the selected 100 km target into illustrative 5 km evaluation
regions gives:

- `100 km / 5 km = 20` regions per axis, therefore **400 regions**, not 25 or 100;
- each square region has `10001 x 10001` vertex samples including its terminal shared edge and one
  R32F field is `400,080,004 B` (~400.1 MB);
- equal-cell hex storage is approximately 15.47% larger, about 462 MB per field before aprons;
- these are **one-field** costs. A graph with height, water, sediment, masks, scratch buffers, GPU
  textures, encoder staging, and in-flight regions must preflight the whole active cone.

The 5 km partition is deliberately too large to be a default and is not a runtime recommendation.
Actual evaluation regions, streaming chunks, and later build patches are separate implementation
units, much smaller in normal operation, and selected from measured CPU, GPU, staging, IO, and
latency budgets.

No threshold in the product is inferred from the examples alone. The recommendation engine uses
enumerated CPU/GPU/build terms, runtime API limits, and authored session/package budgets. A device
whose limits are unknown is not labelled safe.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---:|---|
| S9.1 | Versioned world-domain schema + legacy migration | `[E]` | 8 | independent axes, units, posting, square/hex, vertical frame |
| S9.2 | New Terrain dialog + hard feasibility preflight | `[E]` | 8 | required before clean/default/template creation; no allocation before confirm |
| S9.3 | Imported-height metadata and provenance sidebar | `[C]` | 5 | embedded vs inferred vs authored override; current formats first |
| S9.4 | Global substrate + deterministic bounded evaluator | `[K]` | 13 | GLOBAL once; LOCAL/NEIGHBOURHOOD regions with support-radius aprons |
| S9.5 | Hierarchical preview, precision, residency, and cancellation | `[E]` | 8 | bounded streaming chunks; camera-relative rendering; byte-budgeted eviction |
| S9.6 | World manifest export/import integration | `[E]` | 8 | after S6; region/substrate identity and package reconstruction |
| S9.7 | Large-world constraints on reusable presets | `[C]` | 3 | after S8; compatibility metadata only, no duplicate world ownership |
| S9.8 | Armed large-world acceptance matrix | `[E]` | 8 | arithmetic, seams, memory, UI, import, built PWA |
| | **Sprint 9 total** | | **61** | |

---

## Technical refinement

### Locked world-domain contract

`WorldDomain/1` is saved with the graph and is the authoritative horizontal/vertical frame:

```text
WorldDomain/1
  originM:                 { x, y }                         finite metres
  extentM:                 { width, height }                positive, independent
  authoringUnits:          { horizontal, vertical }         m | km | mi | ft
  lattice:                 square | hex-pointy-odd-r
  posting:                 vertex | legacy-cell
  resolution:
    mode:                  spacing | explicit-samples
    requestedSpacingM?:    { x, y }                         positive
    sampleCount?:          { columns, rows }                integers >= 2
    actualSpacingM:        { x, y }                         derived, persisted
  hexBasisM?:              [[b00,b01],[b10,b11]]            hex only
  vertical:
    datum:                 { kind, name?, offsetM }
    rangeM:                { min, max }                     finite, min < max
```

- UI values may be entered/displayed in metres, kilometres, miles, or feet; persistence and all
  evaluator contexts use metres. Unit conversion changes representation, never the world.
- Spacing mode derives integral sample counts and reports the resulting actual spacing. Explicit-
  samples mode derives spacing. The dialog never silently rounds while continuing to display the
  requested value as if exact.
- For square terrain, authored `cellSizeM` is the persisted `actualSpacingM`: the distance between
  adjacent vertex posts and therefore the width of one authored quad. It does not name any
  streaming, build, page, or evaluation unit.
- New heightfields are vertex-posted. Existing documents migrate to `WorldDomain/1` with
  `posting: legacy-cell`, `width=height=terrainDef.scale`, the current `RES`/hex row count, and
  actual legacy spacing `scale/RES`. This preserves current numerical output. Conversion from
  legacy-cell to vertex posting is a separate explicit resample, never an automatic load mutation.
- `terrainDef.height` and `baseElevation` migrate to the vertical range/datum without inventing an
  external geodetic datum. Unknown is represented as unknown, not silently called sea level.
- Square and hex use one global index-to-world transform. Hex region rows retain the global odd-r
  parity; no region restarts parity at local row zero.

### Locked creation and feasibility contract

Every clean, default, and template command first opens the same New Terrain dialog. The current
document remains intact while the dialog is open. No graph, field, GPU texture, region, worker, or
encoder staging buffer is allocated before the user confirms a passing configuration.

The dialog updates these values live using integer-safe arithmetic:

- actual sample dimensions, logical cell/face count, and R32F bytes per field;
- estimated active-map CPU bytes from the scheduler's declared live field/scratch counts;
- estimated GPU bytes from declared texture formats, dimensions, simultaneous render targets,
  upload staging, and in-flight count;
- estimated build storage/staging from ADR 003's decoded working bytes, encoder worst-case bytes,
  manifest/container overhead, product count, region count, and authored `maxStagingBytes`;
- monolithic/bounded recommendation and, for bounded mode, the proposed evaluation partition, core
  samples, apron samples, substrate dimensions, and bounded active-set estimate.

Hard preflight rejects before confirmation when any checked integer/byte product is unsafe, an axis
exceeds browser typed-array/index limits, a required GPU texture/renderbuffer dimension exceeds the
queried WebGL limit, the declared CPU/GPU active budget is exceeded, or ADR 003 staging exceeds the
profile budget. Unknown GPU memory capacity cannot be guessed from `MAX_TEXTURE_SIZE`; the dialog
requires an authored/session budget and labels unmeasured headroom. Bounded mode is not a bypass:
one evaluation region plus its apron and active scratch set must pass the same checks.

### Imported-height metadata and provenance

Each retained source gets immutable source facts plus separately authored interpretation:

```text
HeightSourceMetadata/1
  source:       filename, format, byteLength, checksum
  raster:       sampleWidth, sampleHeight, bitDepth, channel/endianness
  physical:     extentM?, spacingM?, datum?
  provenance:   per physical field = embedded | inferred-default | user-override | unknown
  override:     authored values plus the source values they supersede
```

The sidebar shows source and effective values together. Embedded metadata is read-only evidence;
inferred defaults are visibly labelled assumptions; an authored override is editable and never
rewrites the embedded record. PNG and headerless RAW/R16 normally provide sample dimensions and bit
depth but **not** physical extent, spacing, or datum. GeoTIFF and SRTM may carry or imply more, but
Terrain Studio currently has no GeoTIFF decoder. GeoTIFF raster/metadata implementation is a named
follow-up requiring its own codec/library story and is not promised by Sprint 9. A Sprint 6 manifest
import may supply embedded Terrain Studio world metadata when its schema validates.

### Locked large-world evaluation contract

1. Build or derive one full-domain **global substrate** whose spacing and active-cone byte cost pass
   preflight. GLOBAL nodes evaluate on that substrate over the complete rectangular domain. A
  cropped or per-region GLOBAL request is rejected before evaluation.
2. Cache the completed global outputs by domain, graph, substrate, root-seed, and node hashes.
3. For each demanded evaluation region, sample the global result in world metres into the region
  core plus the transitive support-radius apron. Run LOCAL nodes on the expanded region and
   NEIGHBOURHOOD(radius) nodes only when the declared apron covers that radius. Crop only after the
   final dependent node.
4. GLOBAL data is sampled into evaluation regions; regions do not independently recreate global
   drainage, stream power, climate, or any future GLOBAL field.
5. Correctness comes from identical world-coordinate sampling, global hex parity, exact shared-
   boundary ownership/copying, and sufficient aprons. Cosmetic height crossfade is forbidden as a
   seam fix. Renderer LOD morphing may manage a representation transition but cannot hide a
   generation mismatch.

Evaluation-region identity is canonical `(level, x, y)` within `WorldDomain/1`; each region records its double-
precision origin, metre extent, core sample rectangle, apron, global-row parity for hex, and content
hash. Position-pure stochastic generators hash `(rootSeed,nodeId,globalSampleCoordinate)` so the
same world sample agrees from either neighbouring region. A region-index stream
`hash(rootSeed,nodeId,level,x,y,phase)` is permitted only for work wholly owned by that region core;
it cannot author a shared edge or apron value.

Rectangular domains use independent column/row counts and partial terminal regions. Square shared
vertex rows/columns are copied bit-identically. Hex regions use the global basis and odd-r row number;
neighbour lookup and apron dilation are D6 in the global lattice metric.

### Locked preview and residency contract

- The full world is represented by a hierarchy whose root/global substrate remains renderable. The
  viewport displays the finest currently resident streaming chunks and labels substrate-only, stale, and final
  states; it never blocks a frame waiting for a detail cook.
- CPU and GPU residency are byte-budgeted. At most the configured active chunks, apron buffers,
  in-flight requests, and pinned ancestors may be resident. Eviction is priority-aware LRU over
  evictable entries; cache accounting asserts measured bytes, not object count.
- Requested/loading/resident/renderable/evictable states support cancellation. A generation counter
  discards late results after domain, graph, quality, or camera intent changes. Cancelled work cannot
  upload or enter the cache.
- Authoritative region origins and camera positions are Float64 on CPU. Rendering subtracts the camera
  in Float64, then uploads region/camera-relative Float32 coordinates. No shader receives a 100 km
  absolute position for near-field geometry.
- Preview traversal and editing never materialize all 400 regions from the illustrative partition,
  all hierarchy levels, or a 40-billion-sample adjacency graph. Actual streaming chunks are much
  smaller and budget-derived. A cold teleport may show the pinned coarse ancestor, never a hole or
  an unbounded allocation burst.
- Sprint 9 owns authoring/evaluation chunks and their content identity. Sprint 10's renderer-facing
  `FieldPageProfile/1` separately authors power-of-two core cells, `coreCells+1` vertex posts,
  `coreCells` shared-edge stride, consumer aprons, explicit parent registration, deterministic 2x
  downsample, and persisted conservative min/max/error headers. Error metadata prioritizes
  residency/quality labels only, never renderer topology.
- A terrain edit creates a new `surfaceVersion`: bounded local edits invalidate intersecting leaves,
  apron dependants, and the ancestor chain; domain/GLOBAL changes invalidate broadly. S10.2, not
  S10.5, owns renderer-page root pinning, ancestor fallback, generation cancellation, retention of
  the old complete front, and atomic version promotion.

### Integration boundaries

- **After Sprint 6:** extend the normative export manifest through a versioned compatible change
  carrying `WorldDomain/1`, substrate identity, evaluation-region hierarchy, core/apron rectangles,
  canonical origins/indices, posting, shared-edge ownership, product hashes, and per-region artifacts. Export
  remains an explicit cancellable command. Import validates the complete manifest before creating
  a document and reconstructs the same domain/region identity; missing or mixed hashes are errors.
- **After Sprint 8:** reusable definitions remain domain-independent by default. A preset/subgraph
  may declare only required lattice, evaluation scope, support radius, and minimum/maximum spacing
  constraints. Instantiation validates those constraints against `WorldDomain/1`; it does not embed,
  mutate, or silently replace the document's world domain. Presets that need no such constraints
  gain no Sprint 9 metadata.

### Owning surfaces and cut order

1. **R0:** freeze old-document/default/import fixtures; capture current `scale/RES`, immediate-new
   allocation, missing provenance, and unbounded render-target behavior as measured red controls.
2. **S9.1:** land schema, integer-safe derivation, migration, undo/save/load, and compatibility
   accessors while preserving legacy document bytes/output.
3. **S9.2:** place the dialog before all creation commands; add live estimates and allocation spies.
4. **S9.3:** retain source facts and render the provenance-aware sidebar for currently supported
   PNG/image, RAW/R16, and valid Terrain Studio manifest imports.
5. **S9.4:** after S2, add evaluation context, global-substrate scheduling, world-coordinate region
  sampling, square/hex aprons, shared boundaries, and deterministic region identity.
6. **S9.5:** add the bounded streaming hierarchy, residency accounting, cancellation, eviction, and
   camera-relative viewport path.
7. **S9.6:** after S6, version the world manifest integration and round-trip monolithic/partitioned worlds.
8. **S9.7:** after S8, add only the reusable-definition compatibility declarations above.
9. **S9.8:** run the complete red/green matrix, production build, built-PWA tests, and memory probes.

---

## Story acceptance gates

### S9.1 - Versioned world-domain schema - 8 pts

**User story:** As a terrain author, I can define a rectangular world in familiar units without
losing the exact metre-space and sample-posting contract when I save or share it.

**Acceptance gate:** `tests/legacy/_verify_world_domain.js` derives the four feasibility examples
above exactly, round-trips m/km/mi/ft without changing persisted metres, covers independent axis
sizes, both resolution modes, vertical datum/range, square and hex transforms, and migrates old
`terrainDef.scale/RES` fixtures with bit-identical legacy output. Mutations that drop the terminal
vertex, force a square extent, or reinterpret legacy `scale/RES` as vertex spacing are red.

### S9.2 - New Terrain dialog and preflight - 8 pts

**User story:** As a terrain author, every new clean/default/template world tells me what it will
cost and refuses an impossible allocation before replacing my current work.

**Acceptance gate:** Playwright exercises clean, default, and Canyon/template entry points; live
sample/cell/R32F/CPU/GPU/build figures match the independent arithmetic oracle; 1 km at 0.5 m,
10 km at 2 m, 64 km at 2 m, and 100 km at 0.5 m `cellSizeM` receive the required recommendations. Cancel keeps
the original graph/history intact. Allocation/worker/emitter spies remain zero until confirmation.
Over-limit browser/GPU/package fixtures disable confirmation and name the failing term. Removing the
preflight or allocating the default graph behind the modal is red.

### S9.3 - Import metadata and provenance sidebar - 5 pts

**User story:** As a terrain author, I can see what an imported height source actually knows and
distinguish that evidence from Terrain Studio defaults and my override.

**Acceptance gate:** import fixtures for PNG, RAW/R16, and a valid Sprint 6 manifest assert filename,
format, source dimensions, bit depth, byte/checksum identity, known/unknown extent, spacing, datum,
and field-level provenance. PNG/RAW physical values remain unknown until an explicitly labelled
inferred default or user override is supplied. Save/load/undo retain source and override separately.
A mutation that labels a default as embedded metadata is red. GeoTIFF files report unsupported
format in this sprint rather than fabricated geospatial facts.

### S9.4 - Global substrate and bounded evaluator - 13 pts

**User story:** As a large-world author, global terrain structure remains coherent while bounded
high-detail evaluation regions add local process detail without seams or load-order drift.

**Acceptance gate:** `tests/legacy/_verify_large_world_regions.js` proves monolithic equals a one-region
schedule bit-for-bit, shared square posts are bit-identical, global odd-r parity/D6 neighbours remain
correct on hex, and evaluating regions in forward/reverse/random order yields identical core hashes.
Analytic NEIGHBOURHOOD fixtures pass only when apron width covers the declared transitive radius.
The scheduler rejects GLOBAL-per-region, insufficient-apron, mixed-domain, and noncanonical-origin
requests before kernel dispatch. Red mutations remove the apron, reset hex parity, seed a shared
edge by region index, and schedule flow accumulation per evaluation region.

### S9.5 - Hierarchical bounded preview - 8 pts

**User story:** As a terrain author, I can navigate a large world while the viewport refines around
me without holes, coordinate jitter, stale uploads, or memory growth proportional to world size.

**Acceptance gate:** a deterministic camera path and cold teleports assert a complete renderable
front, bounded active/in-flight/evictable byte counts, actual eviction, cancellation of obsolete
requests, and no upload from cancelled generations. A 100 km coordinate fixture remains stable under
camera-relative rendering. Peak CPU and GPU bytes stay within authored budgets with non-empty active
chunks; an unbounded-cache mutation and Float32 absolute-position mutation are red.

This gate covers Sprint 9 authoring/evaluation chunks. S10.3 may rely only on the stricter
renderer-page root/fallback/promotion/cancellation gate after S10.2 has passed it.

### S9.6 - World manifest export/import - 8 pts

**User story:** As an engine integrator, I can export and re-import a partitioned world with enough
domain, substrate, region, posting, and provenance data to reconstruct the same fields and boundaries.

**Acceptance gate:** schema plus semantic validation round-trips one monolithic and one partitioned package,
including rectangular square and hex-working-grid fixtures. Stitching cropped region cores reproduces
the exported source within the selected format bound; shared R32F posts are exact; origins advance by
declared metre extents; global products carry one substrate hash and are sampled/sliced, not re-run.
Missing region, mixed hash, unsafe path, posting mismatch, and partial cancellation packages are red.

### S9.7 - Reusable preset constraints - 3 pts

**User story:** As a graph author, a reusable definition either works in my world domain or explains
its lattice/spacing/scope incompatibility before evaluation.

**Acceptance gate:** after S8, constrained and unconstrained definitions save/import with their
pinned identity; only declared constraints participate in validation/cache identity. Reusing a
GLOBAL-containing definition preserves global scheduling, while a required-hex or spacing-bound
definition rejects an incompatible domain. A preset that embeds or mutates `WorldDomain/1` is red.

### S9.8 - Armed large-world acceptance matrix - 8 pts

**User story:** As a maintainer, the large-world promise is protected by gates observed failing on
the broken paths and passing on the production built PWA.

**Acceptance gate:** run every focused gate above plus plugin/bridge checks, production build,
built-bundle digest, dialog and import-sidebar Playwright suites, region seam/shared-boundary/apron
oracles, GLOBAL-node rejection, monolithic-equals-single-region, cancellation/eviction, and measured
CPU/GPU/staging peaks. Each printed sample count, region count, byte count, active count, and peak has
an assertion. Empty inventories are red. Record at least these deliberate failures: missing `+1`,
100 km/5 km illustrative partition miscounted as 100 regions, skipped preflight, per-region GLOBAL
dispatch, zero apron, region-local hex parity, stale cancelled upload, unbounded residency, and inferred import metadata
mislabelled embedded.

---

## Verification matrix and Ready condition

| Contract risk | Passing endpoint | Mutation that must be red |
|---|---|---|
| off-by-one/domain math | exact four-scenario dimensions and bytes | `extent/spacing` samples without `+1` |
| destructive creation | no allocation or document replacement before confirm | eager default/template evaluation |
| provenance laundering | embedded/inferred/override remain separate | default labelled embedded |
| global science split | one full-domain substrate evaluation | GLOBAL once per evaluation region |
| geometric/attribute seam | exact shared posts plus sufficient apron | no apron or cosmetic crossfade |
| hex region drift | global basis and row parity | parity restarted at each region |
| nondeterministic detail | same core hashes in any schedule order | shared edge seeded by region index |
| browser OOM | measured peak within non-empty active-set budget | cache with eviction disabled |
| stale viewport | cancelled generation never uploads | late completion enters cache |
| package drift | validated manifest reconstructs domain/region hashes | mixed substrate/region versions |

Sprint 9 planning is **grounded and technically refined**. Implementation is **NOT STARTED**. The
whole sprint is not Ready until Sprint 2, Sprint 6, and Sprint 8 dependency gates required by the
owning stories have exited and each first mutation has been observed red. The S9.1-S9.3 early slice
may enter its own R0/R1 work independently once its old-document and allocation-spy controls are red.

## Exit gate

- All eight story gates have measured red and green endpoints; no report-only or zero-fixture gate.
- The four feasibility examples and illustrative 20 x 20 = 400 region derivation match the canonical table.
- No path allocates terrain resources before New Terrain confirmation.
- GLOBAL nodes never dispatch per evaluation region; one-region bounded output equals monolithic output.
- Square shared posts, hex parity, transitive aprons, deterministic seeds, and rectangular terminal
  regions pass in the production bundle.
- Import provenance stays explicit and GeoTIFF support is not implied.
- Peak CPU, GPU, in-flight, cache, and build-staging bytes are measured and asserted below authored
  budgets with a non-empty active set.
- Export/import manifests validate and reject incomplete or mixed-version worlds atomically.
- Production PWA, built-bundle digest, plugin/bridge checks, focused Playwright, and standalone sweep
  are green with digest `skipped = 0`.
