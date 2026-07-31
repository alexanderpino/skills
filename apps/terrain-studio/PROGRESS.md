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

**Sprint 1 started — S1.0 Surface / Geology palette family DONE (`da2e583`), 2026-07-31.**

- Added the ninth palette family and reclassified Rock Fracture from Erosion; Thermal remains
  Erosion. Toolbox search and drag-out quick-create expose the new family without evaluator changes.
- Focused Surface-family oracle, toolbox, quick-create, 61/61 digest, plugin/bridge checks, and
  production build are green. The broader sprint-grounding ledger remains open; only grounded,
  independently gated stories may enter implementation.

**Sprint 4 scope expanded — AAA hybrid Gerstner water accepted locally, 2026-07-31.**

- ADR 006 keeps hydrology still and renderer motion separate, then adds shared displaced Gerstner
  geometry, analytic normals, GGX/Fresnel/Beer-Lambert optics, flow-driven rivers, causal foam,
  shore/ice regimes, supplied-reference captures, pass parity, temporal and frame-budget gates.
- Sprint 4 now carries S4.7–S4.10 as separately routable renderer stories; no wave or foam data is
  baked into terrain fields or export products.

**All eight roadmap sprints — grounding audit reopened, NOT DONE, 2026-07-31.**

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

1. **A3 PWA shell** — `public/sw.js` (not `src/`: Vite emits nothing from there, so it 404s under
   preview), `manifest.webmanifest`, icons, per-build precache list, versioned cache +
   `skipWaiting`, registration behind `import.meta.env.PROD`.
2. **A4** — accept the multi-file `dist/` and drop the single-file claim from the docs. Today's
   single-file build is an accident of the script having been inline.
3. **Phase B** — original 60 node types → plugin modules, then Rock Fracture as plugin 61. The first
  genuinely parallel slice; this is where mission-control earns its keep (see its agenda #11).
4. **D7 layers** — L0 bedrock + blends + masks, then L1 erosion (MC-3 D6 constants, MC-5 MFD6),
   L2 cover, L3 water, L4 climate/snow, L5 dressing.

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
