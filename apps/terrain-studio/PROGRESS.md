# Terrain Studio — progress

Where the work stands. **`BACKLOG.md` holds findings, decisions and defects; this file holds
position** — what shipped, what the gates measured, what is next.

Updated as work lands. If this disagrees with a commit message, the commit wins.

---

## Suite coverage — corrected 2026-07-30

`npm run verify` runs **12 of 73** oracle files (it points at `_verify_all_canyon.js`, the Canyon
suite). Use `node scripts/sweep-oracles.mjs` for all of them.

    node scripts/sweep-oracles.mjs                  every oracle, one line each
    node scripts/sweep-oracles.mjs _verify_x.js     a subset

Current full-sweep record: **72/72 standalone oracles green** on 2026-07-30
(`_verify_all_canyon.js` is the one aggregate file excluded by the sweep). This includes
`_verify_build_progress`, production-mode `_verify_pwa`, the graph-authoring gates, and the new
dual-GPU hydraulic gate. Failing output is retained in `.sweep-logs/`.

## Now

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

**Phase B — 60 of 60 node types are plugins.** legacy.js 7,406 → 6,561 lines.

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
npm run verify -- _verify_digest.js     60 node types bit-identical at 256²
npm run verify -- --preview _verify_digest.js   same, against the BUILT bundle
npm run bridge:check                    202 symbols, unbridgeable 0
npm run plugins:check                   60 modules: imports resolve, exports exist, no TDZ
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
| `effect` | 7 | | — |
| `data` | 14 | | — |
| `out` | 1 | | — |

60 total. Digest green per batch, so a bad extraction bisects to one node.

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
3. **Phase B** — 60 node types → 60 plugin modules. The first genuinely parallel slice; this is
   where mission-control earns its keep (see its agenda #11).
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
