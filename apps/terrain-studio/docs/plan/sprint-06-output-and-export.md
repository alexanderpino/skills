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

**Architecture gate:** accept the pure sink/emitter ADR named in the roadmap before S6.1.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S6.1 | Declarative Export sink + explicit execution | `[E]` | 5 | no side effects in `eval`; build command executes each sink once |
| S6.2 | Physical format writers + round-trip matrix | `[K]` | 8 | R32F raw, RAW/R16, PNG16; EXR library spike then implementation |
| S6.3 | Export profiles + complete manifest | `[E]` | 5 | target→map set; lens/units/ranges/epoch/drivers/world metadata |
| S6.4 | Tile export after global evaluation | `[E]` | 8 | shared edges/aprons; never run GLOBAL hydrology independently per tile |
| S6.5 | Bake-boundary validator | `[E]` | 5 | bake set closed under predecessors; names offending edge |
| S6.6 | Preview/classification firewall | `[C]` | 3 | metadata-driven; includes `d_texture` and future classifiers |

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

Implement pure byte encoders for little-endian R32F raw, RAW/R16, and true grayscale PNG16. Preserve
physical range in the manifest; quantize once, after all derivatives. Before EXR implementation,
spike maintained browser-compatible JS/WASM writers against bundle size, R32F channel support,
license, deterministic bytes, and offline PWA operation. Record the choice in the emitter ADR; if no
candidate passes, mark EXR **blocked with evidence** while R32F remains the lossless production path.
Do not write a partial EXR encoder.

**Acceptance gate** — `tests/legacy/_verify_export_formats.js` plus browser oracle:
- R32F raw round-trips Float32 source bytes exactly with explicit endian/shape metadata.
- Parse PNG IHDR and assert bit depth **16**, color type grayscale; dequantization uses `/65535`.
  On a deliberately half-quantum analytic ramp, max error is at most half a quantum plus float
  epsilon and is non-zero; an 8-bit canvas export fails both the header and error oracle.
- RAW/R16 byte length is `2·width·height`, endian is declared/tested, and values round-trip to the
  same PNG16 quantization oracle.
- EXR, when selected, round-trips an R32F channel and remains available offline in the production PWA.

---

### S6.3 — Profiles + complete manifest · `[E]` · 5 pts
**User story:** As an engine integrator, I select one target profile and receive exactly the physical
products and metadata needed to reconstruct them.

A profile is *target → map set*, not a node per engine. The package manifest includes schema version,
graph/substrate hash, root seed, world origin/extent, lattice, resolution, cell size, vertical datum,
height range, and per product: stable name, value/field type, unit, declared/observed range, format,
lens, dependencies, initial/final state, epoch and drivers for continued state. Emitters may adapt
resolution/encoding but may not introduce upstream classifications.

**Acceptance gate** — `tests/legacy/_verify_export_profile.js`: a fixture profile missing one required
product/driver fails; one leaking an undeclared product fails; valid profile emits exactly the
contract. Every continued-state product has non-empty epoch and all declared drivers. Parse the
manifest and reconstruct height from each supported format under S6.2 tolerances.

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
classification` (or ADR equivalent) to descriptors. Profiles reject any transitive preview-only or
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
- Export the L4 default under a real profile, re-import every height encoding, and meet declared
  precision. No preview/classification product appears in the package.
- Production PWA works offline with selected writers; plugin/bridge checks, built-bundle digest, and
  full sweep are green; digest skipped = 0.
- Mesher/LOD and point-cloud emitters remain a named follow-up after the raster contract stabilizes;
  they are not silently included in this sprint.
