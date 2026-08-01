# Terrain Studio — progress

Where the work stands. **`BACKLOG.md` holds findings, decisions and defects; this file holds
position** — what shipped, what the gates measured, what is next.

Updated as work lands. If this disagrees with a commit message, the commit wins.

---

## Suite coverage — corrected 2026-07-31

`npm run verify` runs **12 of 75** oracle files (it points at `_verify_all_canyon.js`, the Canyon
suite). Use `node scripts/sweep-oracles.mjs` for all of them.

    node scripts/sweep-oracles.mjs                  every oracle, one line each
    node scripts/sweep-oracles.mjs _verify_x.js     a subset

Current record: **74/74 standalone oracles green** on 2026-07-31
(`_verify_all_canyon.js` is the one aggregate file excluded by the sweep). The all-oracle run first
reported 71/74: the production PWA gate had reused a stale test-mode preview, shape scan found two
misplaced annotations in the hydraulic apron, and deep zoom exposed an unconditional global-height
camera guard. A fresh production preview plus targeted reruns closed all three; the hydraulic
camera-guard load gate was rerun separately after the zoom correction. Failing output is retained
in `.sweep-logs/`.

## Now

**Sprint 10 cook-free runtime heightfield / Extreme Detail — canonical plan grounded, technical
refinement/Ready BLOCKED on S10.R0 calibration, implementation NOT STARTED, 2026-08-01.**

- Added the exactly 60-point Sprint 10 packet and accepted ADR 008. The ten-sprint programme is now
  **386 points** (`326 + 60`). `ExtremeCapability/1` requires secure context, `navigator.gpu`, a
  non-null adapter/device, no optional features, WebGPU guaranteed-default minimum limits, and
  validated core format usages. Standard requires WebGL2 plus `EXT_color_buffer_float`.
- Capability wording is **“No supported graphics capability,”** not “no GPU.” Browser APIs do not
  reliably prove physical GPU versus SwiftShader/software or report VRAM. Headless SwiftShader is a
  valid endpoint when requirements pass. Persisted preference cannot bypass a fresh probe;
  insecure-context/API-absent/adapter-null/device-reject/device-lost diagnostics remain distinct,
  while timestamp queries are diagnostics only.
- Extreme pages have profile-authored power-of-two core cells, `coreCells+1` posts, `coreCells`
  shared-edge stride, declared aprons, explicit parent/downsample registration, and persisted
  conservative min/max/error headers. Local edits create a `surfaceVersion` and invalidate leaves,
  apron dependants, ancestors, and caches; domain/GLOBAL edits invalidate broadly. S10.2 owns pinned
  roots, ancestor fallback, cancellation, old-front retention, and atomic promotion.
- Geometry is pure fixed-topology clipmap rings. Error metadata prioritizes residency/quality labels
  only. Overlapping toroidal motion uploads exposed strips; a teleport beyond the logical span uses
  budgeted multi-frame full logical refill while an ancestor renders. CPU texture scrolling and
  unbudgeted same-frame refill are forbidden.
- WebGPU compacts visible records into one instance buffer and issues exactly one `drawIndexedIndirect` per
  fixed pass/material/index-pattern bucket with `instanceCount=visible patches` and
  `firstInstance=0`. Shader `instance_index` addresses compacted records; CPU encoding is O(fixed
  buckets), and `indirect-first-instance` is not required.
- S10.5 owns scaled asynchronous feedback, real eviction, the complete byte plateau, and analytic
  camera-relative precision `<=1 mm` at 100 km. Platform frame/memory budgets are authored inputs.
  Software depth/patch-ID controls are byte-identical; GPU parity uses a one-ULP mismatch formula.
  Visual displacement is identical in main/depth/shadow/velocity, and dependent surface consumers
  declare authoritative-height or visual-displacement use.
- Anti-tiling still lacks measured periodic/decorrelated autocorrelation controls. The zero-point
  S10.R0 readiness-only story must freeze that bound and the GPU parity bound between measured red/green
  controls; until then Sprint 10 is not technically refined or Ready.
- Mission traceability adds future roadmap bundles `MC-S25`–`MC-S28`; `MC-S20` must eventually wait
  for `MC-S28`. No Mission Control SQLite/runtime item or dependency was created by this documentation
  change. Export waits for the Sprint 6 and Sprint 9 manifest owners and remains height, auxiliary,
  and domain/region pages only; runtime caches regenerate after import.

**Sprint 9 large worlds — canonical plan grounded/refined, implementation NOT STARTED, 2026-08-01.**

- Added the 61-point large-world packet and accepted ADR 007: versioned independent-width/height
  world domains, m/km/mi/ft input with internal metres, vertex/legacy posting, vertical datum/range,
  allocation-free New Terrain preflight, and import metadata with explicit embedded/inferred/override
  provenance. Sprint 9 brought the then-current programme to **326 points** (`265 + 61`); Sprint 10
  is followed by the Sprint 10 total recorded above.
- The selected architecture is one authored/derived full-domain substrate for GLOBAL nodes plus
  deterministic LOCAL/NEIGHBOURHOOD evaluation regions with transitive support-radius aprons. Global
  results are sampled into regions; cosmetic seam crossfade is not correctness. Preview keeps a
  byte-bounded active hierarchy with cancellation, eviction, and camera-relative rendering rather
  than materializing a 40-billion-sample graph.
- Canonical arithmetic is fixed: 100 km at 0.5 m `cellSizeM` is `200001` square vertex samples per axis,
  approximately 40.0 B samples / 160.0 GB for one R32F field; equal-cell hex is approximately
  46.2 B / 184.8 GB. An illustrative 5 km evaluation partition is `100/5=20` per axis and **400
  regions** total; actual evaluation regions and streaming chunks are much smaller and budget-derived.
- Mission Control traceability extends to `MC-S21`–`MC-S24`. These are future implementation
  bundles in the roadmap only; no Mission Control runtime item/state was created or changed.
  Domain/dialog/import may start early; tiled evaluation waits on `MC-S02`, manifest integration on
  `MC-S14`, and reusable-definition constraints on `MC-S19`.
- The plan names a user-selected 100 km-class target and makes no unsourced claim about the actual
  dimensions of *Star Wars Outlaws*. GeoTIFF decoding remains a separate future codec/library story.

**Sprint 1 implementation — S1.0 and S1.1 DONE (`da2e583`, `8a83bcf`), 2026-08-01.**

- Added the ninth palette family and reclassified Rock Fracture from Erosion; Thermal remains
  Erosion. Toolbox search and drag-out quick-create expose the new family without evaluator changes.
- Focused Surface-family oracle, toolbox, quick-create, 61/61 digest, plugin/bridge checks, and
  production build are green. The broader sprint-grounding ledger remains open; only grounded,
  independently gated stories may enter implementation.
- MC-S31 integrated Surface Detail plus the initial landform pack with seed lifecycle, direct/CJS
  68/68 digest, 32 armed mutations, full source/built 45° visual matrices, FOV state preservation,
  plugin/bridge/exact/hex/build gates, and clean independent review. This closes **S1.1 only**.
- **S1.2 Volcano correction is mandatory before completion:** the current isolated implementation
  now integrated exposes only a pointed `stratovolcano` profile and rejects `shield`. The plan requires distinct
  shield (2–10° broad dome) and stratovolcano (20–35° summit-steepening, crater + barrancos) modes,
  each with analytic and two-distance visual evidence. S1.2 remains **IN PROGRESS** and MUST NOT be
  marked DONE until dependent MC-S32 passes and publishes.

**Sprint 4 scope expanded — AAA hybrid Gerstner water accepted locally, 2026-07-31.**

- ADR 006 keeps hydrology still and renderer motion separate, then adds shared displaced Gerstner
  geometry, analytic normals, GGX/Fresnel/Beer-Lambert optics, flow-driven rivers, causal foam,
  shore/ice regimes, supplied-reference captures, pass parity, temporal and frame-budget gates.
- Sprint 4 now carries S4.7–S4.10 as separately routable renderer stories; no wave or foam data is
  baked into terrain fields or export products.

**Sprints 1–8 — grounding audit reopened, NOT DONE, 2026-07-31.**

- The first refinement pass added contracts, cut order, verification matrices, and Ready conditions,
  but an audit found that some “locked” defaults and runtime choices had no corpus, measured-code, or
  accepted-ADR evidence. That pass is not complete and must not be used to start a sprint.
- Mission Control investigation `INV-SPRINT-GROUNDING` owns the correction. Completion requires a
  claim-level grounding ledger, accepted ADRs for S2/S6/S8, removal or replacement of unsupported
  mechanics, fixed pre-implementation thresholds, and an independent rubber-duck review with no
  valid blocking finding.
- Until that gate closes, every sprint remains **Not Ready** regardless of dependency position.

**Separate GPU Rock Fracture node — done locally, 2026-07-31.**

- Added an erosion-family **Rock Fracture** node instead of folding cracks into Thermal. It carves
  deterministic warped Worley/Voronoi `F2−F1` joint boundaries at up to five scales. Fine sets become
  shallower and narrower, avoiding the nearly uniform lowering produced by reusing the broadest
  crack and shoulder at every octave.
- **Fracture network** and **Edge weathering** are independently switchable, collapsible inspector
  panels. Spacing, crack width, cut depth, warp scale, and shoulder width are authored in metres;
  terrain scale/relief edits correctly dirty the node. The intended stack is
  `Rock Fracture → Thermal`: joints first, talus transport second.
- Square terrain runs a one-pass WebGL2 gather kernel with one readback. Hex and systems without
  float render targets use the deterministic CPU compatibility path. Measured square CPU/GPU error:
  max `5.25e-6`, RMS `4.71e-7`.
- The procedural field continues beyond the rectangle rather than sampling a clamped border. The
  focused gate measured edge/interior fracture dose `1.09`, 128²↔256² RMS drift `4.08e-4`, exact
  disabled/masked identity, finite unbounded negative/>1 heights, seed determinism, strict `[0,1]`
  masks, hex fallback, toolbox registration, GPU badges, and collapse-state purity.
- Visual evidence on a deliberately smooth mountain shows connected multiscale rock joints rather
  than thermal ribbing. A heightfield limitation is stated in the inspector: grooves and breakup
  are representable; true separated blocks, undercuts, and open fissure voids are not.

**GPU hydraulic spikes and edge tears — fixed locally, 2026-07-30.**

- Removed the synchronized end-of-lifetime sediment dump that turned every surviving droplet into a
  narrow cone. Lifetime is now a work cap; unresolved load is named `exportedOrSuspended`.
- Fixed the separate high-density runaway. Particle cohorts cap stale-read scatter density at 0.1
  particle/cell; speed is bounded; above 0.5 particle/cell, water/sediment parcel weight shrinks so
  additional particles refine coverage without multiplying strength or breaking the terrain ledger.
  The previous 30k UI / 120k actual case reached finite values around 10²¹.
- Fixed the pipe solver’s self-deepening minima: transport capacity now uses a signed downhill outlet,
  vector speed, and a shallow-water ramp. The post-output fade was removed. Pipe runs on a
  border-continuation apron with an explicit closed outer wall and crops back to the authored field.
  At 279 iterations / Deposit 0.48, edge p99/max are 0.00384/0.00454 versus input
  0.00749/0.00849.
- Droplets spawn inside a full-brush guard and export before reaching a partial edge brush. The
  viewport also keeps the inspection eye above the open heightfield so back-facing mesh triangles
  cannot masquerade as erosion spikes at grazing angles.
- `_verify_hydraulic_dual_gpu` now has armed upward and downward controls and runs the real 512²
  Interactive path: the reported 14,389 × 71 case, 30k, the 60k UI / 240k actual maximum, and exact
  combined Pipe 279 → Droplet 57,670 × 48. All are finite with zero peaks or pits above 0.02. Focused
  verification, the camera-guard rerun, and the current 74/74 standalone-oracle record are green.

**Composable GPU hydraulic erosion — done locally, 2026-07-30.**

- Hydraulic now has independent Pipe / grid and Droplet / particle switches with collapsible,
  model-specific controls. Switches are saved and undoable; expansion state is UI-local.
- Square-lattice WebGL2 runs both mechanisms on the GPU. Pipe state feeds Droplet state in the
  fixed order Pipe → Droplet and the combined node reads back once. The droplet stage uses particle
  textures, MRT updates, additive float point-rasterisation, and a terrain gather/apply pass.
- Old `engine` documents migrate to the two-switch schema. Hex and contexts without
  `EXT_float_blend` retain an explicitly labelled CPU compatibility path.
- `_verify_hydraulic_dual_gpu` gates same-seed repeatability, seed variation, finite output,
  erosion and deposition, mass closure, combined stage order, one readback, inspector UI,
  collapsible-state purity, switch history, and saved-graph migration.

**Graph authoring UX — done locally, 2026-07-30.**

- Releasing an output connection on empty graph space opens a focused, searchable node picker
  containing only node types with an input. Selection creates the node at the release point and
  connects slot 0; create + connect is one undo record, and Escape is a no-op.
- The stacked/vertical workspace has an accessible horizontal splitter. The graph's preferred pixel
  height persists across reloads and display growth. CSS and JavaScript independently preserve a
  220 px terrain viewport by shrinking the graph only when the window is constrained.
- Focused gates green: `_verify_quick_create`, `_verify_workflow`, `_verify_toolbox`,
  `_verify_edges`, `_verify_digest`; production `vite build` green. The subsequent full standalone
  sweep is 72/72 green.

**Programme:** modularisation toward React + plugin nodes + PWA, per
`~/.claude/plans/quiet-wishing-harbor.md` (adversarially reviewed before execution; seven blocking
issues found and folded in).

**Phase B — the original 60 of 60 node types became plugins.** Rock Fracture was then added directly
as plugin 61. legacy.js 7,406 → 6,561 lines during the extraction.

**Phase A — become a module, extract GPU, ship the PWA shell.**

| Step | State | Commit |
|---|---|---|
| A0 · make the four source-text instruments module-aware | **done** | `ca72036` `4d82644` `fe9c8b8` `58659ba` |
| A1 · app becomes an ES module | **done** | `d67e9f8` (blocker `21953aa`) |
| A1b · `--preview` builds with `--mode test` | **done** | `442564a` |
| A2 · extract `src/core/gpu.js` + `gl-util.js` | **done** | `61ca297` |
| A3 · PWA shell | **done** | `ab0a322` |
| A4 · single-file artifact decided (multi-file accepted) | **done** | this commit |

## Gate readings, current

Run from `apps/terrain-studio/`. Everything is HTTP now; `--file` died with A1.

```
npm run verify -- _verify_digest.js     61 node types bit-identical at 256²; skipped 0
npm run verify -- --preview _verify_digest.js   same, against the BUILT bundle
npm run bridge:check                    202 symbols, unbridgeable 0
npm run plugins:check                   61 modules: imports resolve, exports exist, no TDZ
npm run verify -- _verify_blur_isotropy.js   square 1.0000, hex 1.0000 (was 1.185)
npm run verify -- _verify_layers.js     L0 13/13 both lattices; roughness 0.0290/0.0286
npm run verify -- _verify_hillslope_isotropy.js  9/9; hex sigma 3.873/3.873 = square exactly
npm run verify -- _verify_flow_facets.js  12/12; facets 1.0114/1.0220 (single-receiver floor was 1.81/1.67)
node tests/legacy/_verify_shapescan.js  3 files, 8554 lines scanned
npm run verify -- _verify_gpu.js        hasWebGL2Float=true init=true gpuReady=true
                                        fbm@512: 16ms GPU vs 231ms CPU
npm run verify -- _verify_hydraulic_dual_gpu.js
                                        GPU droplets + Pipe→Droplet, one readback, UI/migration green
npm run verify -- _verify_wireframe.js  6/6   (gl.drawElements monkey-patch still takes)
npm run verify -- _verify_hex_deferred.js  4/4
npm run verify -- _verify_erosion_mass.js  9/9
npm run verify -- _verify_glsl_probe.js  maxDiff 0.000e+0 (tol 1e-5)
npm run verify -- --preview-prod _verify_pwa.js   6/6, incl. offline with the network cut
```

Run the app: `.\run-studio.ps1` (dev, :5173) · `-Mode pwa` (build + preview, :4173) · `-Mode build`.

## Shape of the app today

```
index.html          79 KB — markup, <style>, one <script type="module">
src/legacy.js       6,905 lines — the app, + the test bridge spliced in at the end
src/core/gpu.js     GPU, GLSL kernels, gpu* wrappers, gpuReady, hydroMassDiag
src/core/gl-util.js makeProg, u, setGL
src/testing/        bridge-block.js (generated, 191 symbols / 28 writable)
tests/legacy/       73 oracle files + bridge-surface.json (the frozen contract)
tests/e2e/          4 Playwright specs
```

## Phase B — plugin extraction

| Batch | Nodes | State | Commit |
|---|---|---|---|
| prerequisite · param DSL to `src/core/params.js` | — | **done** | `d85b84f` |
| registry + `comb` | 6 | **done** | this commit |
| `mask` | 4 | **done** | this commit |
| `filt` | 11 | **done** | `2b6d1c8` |
| `gen` | 12 | **done** | this commit |
| `ero` | 5 | **done** | this commit |
| `effect` | 7 | **done** | local history |
| `data` | 14 | **done** | local history |
| `out` | 1 | **done** | local history |

Original extraction total: 60. Rock Fracture later became plugin 61. Digest green per batch, so a
bad extraction bisects to one node.

## D7 layered cake

| Layer | State |
|---|---|
| L0 bedrock + blends + masks | **done** — hexBlur 1.185→1.0000; L0 is the opening document, 13/13 on both lattices |
| L1 erosion (MC-3 D6 constants, MC-5 MFD6) | **done** — hillslope Laplacian was advecting on hex (1.1595->1.0000); flow drained diagonally always; MFD6 Freeman p=1.1 facets 1.81/1.67 -> 1.01/1.02 |
| L2 cover · L3 water · L4 climate/snow · L5 dressing | |

## Next, in order

1. **Finish `MC-S03`** — S1.1 Surface and S1.2 landforms are building in the isolated worktree;
  complete focused red/green, built-PWA, review, and merge gates.
2. **Route approved `MC-S01` and `MC-S04`** — typed-DAG foundation and the remaining Sprint 1
  filters/coordinate/aspect bundle are approved and independently leasable.
3. **Advance dependency queue** — canonical Mission Control status has 17 open items beginning with
  `MC-S02`, `MC-S05`, `MC-S06`, `MC-S07`, and `MC-S12`; route them only as their immediate
  producing dependencies exit. Sprint 9/10 bundles remain roadmap traceability, not current mission
  runtime items.

## Open, carried

- `_verify_realtime.js` reports 0 PASS / 0 FAIL — a report-style probe with no assertions, so it
  cannot fail. Same family as `_verify_glsl_probe` before it was gated.
- `lift-glsl-source.js` considers only the **first** occurrence of a signature per file, so a decoy
  in an HTML comment ahead of the live definition would win; and a `src/` file the page never
  imports could be the sole lift source. Both need the import graph to close properly.
- C11 square-shape audit: 8 sites still open in `_verify_hex.js` (measured domain-restricted, not
  corrupted), `_verify_hex_sampling.js`, `_verify_hex_dem.js`; plus 117 latent sites in square-only
  oracles.
- **69 commits are not on the remote.** `origin/<branch>` sits at `346c6c6`, a full session behind.
  Push has never been authorised.
