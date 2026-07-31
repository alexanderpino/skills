# Sprint 6 — Output & export: pure sinks, emitters, profiles, tiles `[K]`+`[E]`

**Goal.** Turn Terrain Studio into a production emitter without making graph evaluation impure.
Export nodes declare products; an explicit Build/Export command evaluates each sink once and invokes
format writers outside `eval`. Profiles select target map sets, manifests carry the physical
contract, tile export slices a completed global build, and illegal bake cuts are rejected.

**Depends on:** Sprint 2 typed ports/persistence, Sprint 3 state maps, Sprint 4 hydrology, Sprint 5
continued climate/snow. **Implements:** `BACKLOG W6`, `BACKLOG D6`. **Maps to** Gaea Output while
retaining the doctrine cap in `GAEA-GAP §4.2`/`§4.3`.

**Measured starting point.** `exportHeightmap()` is a global button that normalizes the Output field
and writes an **8-bit RGB PNG** through canvas. It contributes square/hex interchange resampling and
browser download mechanics, but it is not an R32F/PNG16/RAW/EXR writer and it discards physical
height range. Do not describe format work as “reuse the existing writer.”

**Architecture gate:** [ADR 003](../adr-003-pure-export-emitter.md) and the normative
[manifest schema](../export-manifest.schema.json) are accepted; S6.1 must implement that boundary.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S6.1 | Declarative Export sink + explicit execution | `[E]` | 5 | no side effects in `eval`; build command executes each sink once |
| S6.2 | Physical format writers + round-trip matrix | `[K]` | 8 | scalar/vector/label raw, PNG16, scalar/feature JSON; no EXR |
| S6.3 | Export profiles + complete manifest | `[E]` | 5 | target→map set; lens/units/ranges/epoch/drivers/world metadata |
| S6.4 | Tile export after global evaluation | `[E]` | 8 | shared edges/aprons; never run GLOBAL hydrology independently per tile |
| S6.5 | Bake-boundary validator | `[E]` | 5 | bake set closed under predecessors; names offending edge |
| S6.6 | Preview/classification firewall | `[C]` | 3 | metadata-driven; includes `d_texture` and future classifiers |

---

## Technical refinement

### Locked emitter and package contract — [ADR 003](../adr-003-pure-export-emitter.md)

- The ADR fixes a pure `ExportRequest` value containing source node/port identity, unique stable
  product name, format/options, profile membership, and enabled state. Product names are authored
  ASCII slugs unique within a profile; node IDs remain provenance and are not public filenames.
- Explicit export evaluates all enabled requests, validates the complete package, encodes into a
  staging package, and exposes one download only after every product succeeds. Cancellation discards
  staging. Preview, progressive evaluation, and undo/redo cannot call an emitter.
- Every profile authors `maxStagingBytes`. Preflight sums decoded working bytes, encoder worst-case
  bytes, manifest bytes, and deterministic container overhead and fails before allocation if the
  authored budget would be exceeded; there is no device-independent default.
- R32F raw is little-endian IEEE-754. R16/PNG16 use one package-wide physical range per product:
  an authored profile range when present, otherwise the observed monolithic min/max recorded in the
  manifest. Never choose a range per tile. Constant fields encode with an explicit constant-value
  manifest path rather than divide by zero.
- EXR is outside Sprint 6. R32F is the lossless master; a later codec ADR with measured browser
  candidates may add EXR. No partial EXR encoder or placeholder profile is permitted.
- The graph is evaluated monolithically before interchange conversion or slicing. Vertex-posted
  raster tiles duplicate the shared boundary sample exactly and use core stride `tileSize - 1`.
  Aprons are copied from the monolithic result and cropped by manifest rectangle. Raw fields use zero
  overlap unless the profile requests it; normals use one source sample; other finite-neighbourhood
  products use their declared support radius. Hex-to-square resampling occurs once on the monolithic
  field, never independently per tile.
- Bake closure is port-level reachability. A baked `(node, outputPort)` requires every transitive
  source port it depends on to be baked, regardless of other outputs on those nodes. Continued-state
  products additionally require their driver ports and epoch in the same package.

### Owning code surfaces and cut order

1. **R0:** record the 8-bit `exportHeightmap` behavior, output-node assumptions, a fixture profile's
  explicit staging budget, and an illegal-bake fixture.
2. **S6.1:** add request values and explicit executor with a fake in-memory emitter; prove zero side
   effects from every evaluation path before adding browser writers.
3. **S6.2:** land R32F, R16, and PNG16 encoders independently with parser/round-trip tests.
4. **S6.3:** implement the accepted manifest JSON schema and profile fixtures, including naming, ranges, lenses,
   driver closure, hashes, and constant-field representation.
5. **S6.4:** add monolithic slicing/shared-post/apron logic and memory preflight. Per-tile GLOBAL
   evaluation is rejected by scheduler metadata, not merely compared after the fact.
6. **S6.5–S6.6:** validate port-level bake closure and export policy before encoding; remove the
  legacy 8-bit interchange path when PNG16 lands.

### Verification matrix and Ready condition

| Contract risk | Passing endpoint | Mutation that must be red |
|---|---|---|
| Impure sink | zero calls except one explicit export | download in `eval` |
| False 16-bit | IHDR 16-bit plus half-quantum error | 8-bit canvas writer |
| Tile seams | stitched cores equal monolith; shared posts bit-identical | per-tile resample/flow |
| Stale bake | closed predecessor set per source port | node-ID-only traversal |
| Driver loss | continued state includes epoch and all drivers | snow without moisture |
| Preview leak | raw causes accepted, classifier path rejected | missing policy defaults to raw |

Sprint 6 is Ready when S2–S5 exit, the ADR 003 request/schema and semantic-validator fixtures pass,
the over-budget/side-effect/8-bit writer mutations are red, and the L4 profile fixture has complete
drivers.

---

### S6.1 — Declarative Export sink · `[E]` · 5 pts
**User story:** As a terrain author, I can place named export products in the graph and rebuild or
preview without accidental repeated downloads.

An Export sink has typed input, product name, format/options, and profile membership. Its evaluation
is pure: it returns/records an immutable export request and performs no DOM click, download, file
write, or hidden graph lookup. The explicit Build/Export command discovers requested sinks, evaluates
their dependencies demand-first, validates requests, then invokes emitters once. Auto-preview,
thumbnails, undo/redo, and progressive evaluation never execute side effects.

**Acceptance gate** — `tests/legacy/_verify_export_sink.js`: repeated graph evaluation and preview
produce zero emitter calls; one explicit export invokes each enabled sink exactly once in stable
order; cancellation leaves no partial package; two sinks on different ports receive distinct typed
values. A fixture sink that downloads inside `eval` must fail the purity/side-effect spy.

---

### S6.2 — Physical format writers · `[K]` · 8 pts
**User story:** As a terrain author, I can export float masters and required 16-bit interchange files
without quantizing the working graph.

Implement pure byte encoders for little-endian R32F raw, RAW/R16, true grayscale PNG16,
RG32F/RGB32F vector raw, U32 label raw, JSON scalar, and JSON feature sets. Preserve physical range
and ordered vector components in the manifest; quantize once, after all derivatives. Do not add EXR.

**Acceptance gate** — `tests/legacy/_verify_export_formats.js` plus browser oracle:
- R32F raw round-trips Float32 source bytes exactly with explicit endian/shape metadata.
- Parse PNG IHDR and assert bit depth **16**, color type grayscale; dequantization uses `/65535`.
  On a deliberately half-quantum analytic ramp with range `R`, pre-store error is at most
  `R/(2*65535)`; add the oracle-computed Float32 rounding interval at the tested magnitude. Error is
  non-zero, and an 8-bit canvas export fails both the header and bound.
- RAW/R16 byte length is `2·width·height`, endian is declared/tested, and values round-trip to the
  same PNG16 quantization oracle.
- RG32F/RGB32F length and component order match the manifest; a swapped east/north fixture fails.
  U32 labels preserve the `noLabel` sentinel. Scalar and feature JSON round-trip stable IDs, kinds,
  world-metre coordinates, units, and attributes without raster metadata.

---

### S6.3 — Profiles + complete manifest · `[E]` · 5 pts
**User story:** As an engine integrator, I select one target profile and receive exactly the physical
products and metadata needed to reconstruct them.

A profile is *target → map set*, not a node per engine. The normative discriminated
[manifest schema](../export-manifest.schema.json) includes schema version,
graph/substrate hash, root seed, world origin/extent, lattice, vertical datum, authored staging
budget, and per-product value-kind metadata. Raster branches carry posting, resolution, cell size,
declared/observed range, format, and component order where relevant; scalar/feature branches carry
their own encodings without fabricated raster fields. Every product has a safe relative artifact
path, lens, state role, dependencies, and continued-state epoch/drivers where required.

**Acceptance gate** — `tests/legacy/_verify_export_profile.js`: a fixture profile missing one required
product/driver fails; one leaking an undeclared product fails; valid profile emits exactly the
contract. JSON Schema validation is followed by ADR 003's semantic validator: product names are
unique; dependency/driver names resolve; ranges are ordered and observed values stay declared;
vertex/pixel posting matches `extent/(N-1)` or `extent/N`; paths are relative/non-traversing; vector
format/component count agrees; constant fields have equal observed endpoints; continued state is
initial and has epoch/drivers. Parse the manifest and decode every supported format under S6.2 bounds.

---

### S6.4 — Tile export after global evaluation · `[E]` · 8 pts
**User story:** As an open-world integrator, I can export deterministic tiles with shared boundaries,
aprons, and world metadata without changing global hydrology.

Evaluate the requested graph/product over the full domain first. Only then slice tiles, add the
profile's generation/import apron policy, and emit a manifest with tile indices, origins, extents,
shared-edge convention, and crop rectangle. `GLOBAL` nodes (flow accumulation, stream power) may
never evaluate independently per tile; if full-domain memory is unavailable, export fails visibly
rather than silently changing science.

**Acceptance gate** — `tests/legacy/_verify_tile_export.js`: stitch exported tiles after removing
aprons and recover the monolithic product within format precision; shared vertex edges are identical;
world origins advance by the declared stride. A fixture that runs physical flow separately per tile
must differ from monolithic and be rejected by the scheduler. Test square and hex-to-square
interchange paths.

---

### S6.5 — Bake-boundary validator · `[E]` · 5 pts
**User story:** As an engine integrator, export rejects any baked product whose live ancestor would
make it stale at runtime.

**Implements:** `D6`. The bake set is closed under predecessors: bake X implies every ancestor of X is
baked. Validation runs on `(node, sourcePort)`, because one node may expose outputs with different
lenses. An illegal cut is an export build error, not a warning.

**Acceptance gate** — `tests/legacy/_verify_bake_boundary.js`: reject a baked product with a live
ancestor and name the offending source/destination ports; accept a closed bake set; reject a baked
classifier downstream of live climate. Fixtures cover multi-output nodes so checking only node IDs
fails.

---

### S6.6 — Preview/classification firewall · `[C]` · 3 pts
**User story:** As an engine integrator, production packages contain raw causes/drivers rather than a
preview color or frozen material decision.

**Implements:** guardrail 2 / `GAEA-GAP §4.2`–`§4.3`. Add `exportPolicy: raw | previewOnly |
classification` to descriptors. Profiles reject any transitive preview-only or
classification value. Backfill `satmap`, `satmapblend`, `colormixer`, `colorerosion`, and
**`d_texture`**; future preset classifiers default to restricted until explicitly reviewed. This is
metadata-driven, not a forever-growing hard-coded type list.

**Acceptance gate** — `tests/legacy/_verify_preview_firewall.js`: reject direct and transitive
`satmap`/`d_texture` products with the offending port path; accept raw moisture/soil/slope fields. A
new fixture classifier without policy must fail registration rather than bypass the firewall.

---

## Sprint 6 exit gate

- Sink purity, format round-trip, profile/manifest, tile, bake-boundary, and firewall gates are green
  with armed failing fixtures.
- Export the L4 default under a real profile, decode every height encoding through independent
  bounded decoders, and meet declared precision. The existing Import node is not expanded in S6;
  decoder tests consume manifest dimensions, endian, range, constants, and PNG16 samples directly.
  No preview/classification product appears in the package.
- Production PWA works offline with all S6 writers; plugin/bridge checks, built-bundle digest, and
  full sweep are green; digest skipped = 0.
- Mesher/LOD and point-cloud emitters remain a named follow-up after the raster contract stabilizes;
  they are not silently included in this sprint.
