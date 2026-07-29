# Terrain Studio — backlog and findings

Working notes for the app: decisions taken and why, defects that have been **measured** rather than
suspected, open work, and the verification lessons that keep being relearned.

Two rules for this file, because a backlog that lies is worse than none:

- **Numbers or it didn't happen.** A defect gets an entry when it has been measured, with the
  command that reproduces it. "Looks wrong" goes in *Open questions*, not *Confirmed*.
- **Provenance is marked.** `P` = verified paper, `F` = folklore/no canonical source, `?` = claimed
  but unverified. Never upgrade a tier to make an entry look stronger.

Status: **TODO** · **WIP** · **DONE** · **BLOCKED** · **WONTFIX**

**Which corpus is authoritative.** The **installed** skill
(`~/.claude/skills/terrain-architect/`) is the source of truth for doctrine, and every `27`/`26`
citation in this file is read from it. The copy under `terrain-architect/` in this repo lags on this
branch and catches up when `origin/main` is pulled in — so a chapter being absent *here* says
nothing about whether the doctrine exists. Two consequences worth remembering:

- Nothing in the auxiliary-map work is blocked on the merge; the doctrine is readable now.
- Chapter numbering differs between the two right now — the installed copy has `26-hexagonal-grids.md`
  (split) plus `27-engine-data-handoff.md`; this branch still has the older single
  `26-hexagonal-lattice.md`. **Author corpus corrections (W7) against the installed/main version**,
  after the merge, or they will be written into a file that main has already replaced.

---

## 1. Decisions taken

### D1 — A hex field is `RES × round(RES·2/√3)`, giving a square world · DONE
`512 × 591`. Equilateral cells, no squash, no crop. Costs **+15.5% cells** at equal `cellSize`,
which `26` names as the trap: the "13.4% fewer samples" saving only materialises if you take a ~15%
*coarser* cellSize, and carrying the square cellSize over makes it a memory *cost*. We took the
cost deliberately — a truthful square world is the product requirement.

Supersedes an earlier "squash or crop, no third option" framing that was written into the corpus.
That dilemma was an artefact of reusing the square array shape; giving hex its own row count
dissolves it. **`26` still carries the old framing and needs correcting** (see W7).

### D2 — The ragged hex rim is correct · DONE
Odd rows sit half a cell right, so the map boundary is serrated by `s/2`. A hex heightfield does not
have a straight edge. Do not sand it off.

### D3 — Node-per-plugin, React shell · WIP
`TYPES` (60 entries of `{cat, name, ins, params, eval}`) is already a plugin registry in embryo, so
this is an *extraction*, not a redesign. React chosen over Angular for React Flow (no Angular
equivalent for the graph editor) and lighter WebGL interop; Angular's DI would suit the registry but
not enough to outweigh that. **Not yet confirmed by the user.**

### D4 — The oracle suite is the gate of record, not the pipeline · DONE
Mission Control's *plan* gate earned its place — four review rounds, a real defect found in each.
Its build/merge chain (worktrees, sandboxes, CAS publish) caught nothing here, while a load test and
a digest caught an infinite-loop hang. Width is 1 and there is a single serial writer, so the
ceremony bought nothing. `.mission-control/` is gitignored.

### D5 — Water is authored through sources, not auto-generated · TODO
Auto-generated water lets the *algorithm decide intent* — priority-flood fills every basin over a
threshold and the designer gets on/off plus a slider. The fix is not less simulation; it is moving
the simulation downstream of the decision:

- **Designer owns intent** — which bodies exist, seeded where, how much water, what kind.
- **Simulation owns geometry** — surface elevation, extent, depth, velocity. Flat-at-spill and
  downhill-flow come out by construction, so they cannot be violated by hand.
- **Conflicts are surfaced, not silently corrected** — a river drawn uphill reports "needs 4 m of
  carve here" and offers to do it.

Sources are movable objects carrying `discharge`, `salinity`, `temperature`, `kind`. Their
properties **propagate**: a warm spring keeps the reach below it ice-free; a salt source makes a
salt lake. Auto-detection survives as a *proposal* ("found 47 basins, keep 5"), emitting the same
editable object type as a hand-placed body.

### D6 — The bake boundary is a cut in the DAG, and it is checkable · TODO
If a node is simulated at runtime, everything downstream of it must be too, or the baked downstream
map describes a state that no longer exists. Formally: **the bake set is closed under predecessors**
— bake X and every ancestor of X is baked. An illegal cut (a baked node with a live ancestor) is
mechanically detectable.

`27`'s Masking Doctrine is a special case of this: "ship moisture/temperature/soilDepth, not a baked
biome ID" is "the classifier is downstream of live climate, so push the cut upstream of it".

Three categories, only one of which is a judgement call:

| | |
|---|---|
| **Must bake** | path-dependent history the engine cannot recompute — `solidTop`, bathymetry, `soilDepth`, `sedimentDepth`, `strataHardness` |
| **Must stay live** | anything the engine changes — weather, season, tides, player edits |
| **Either** | `insolation`, `flowVelocity`, `wetness`, `snowDepth` — **the target engine decides** |

Consequence: **the exported map set is a function of the target, not a fixed list.** That argues for
export *profiles* (static / dynamic-climate / full-sim) rather than one export node, and it makes
one field name carry two contracts — `snowDepth` is *final* under a static profile and *initial
state at epoch T* under a dynamic one. The manifest must say which, and a driver-completeness check
must fail an initial-state map whose drivers are absent.

---

## 2. Auxiliary maps — the three lenses

`27` splits maps into **state** (path-dependent, carried, co-updated) and **derived** (pure
functions of final geometry, recomputed never patched). Snow, ice and water need a third lens:
**continued state** — the tool computes an epoch and *the same process continues at runtime*.
`27` hints at it by writing `snowDepth` **(initial state)** in its engine table.

| Lens | Lifecycle | Export means | Examples |
|---|---|---|---|
| Derived | recompute from final geometry | a finished answer | slope, curvature, ao, aspect, **insolation**, TWI |
| State | carried through, co-updated in-pass | a finished accounting | soilDepth, sedimentDepth, sandDepth, strataHardness |
| Continued | evolves in time | **initial condition + drivers** | snowDepth, waterSurface/Depth, flowVelocity, ice |

Two classification traps, both caught by review rather than by reading:

- **`insolation` is derived, not state.** It is a pure function of final geometry and sun arc, so it
  is *recomputed* after the last height write — never carried. Filing it under state attaches the
  wrong lifecycle and lets it go stale behind a height change.
- **`wetness` must be split, not averaged.** ch27 requires the state map (path-dependent saturation,
  written by hydraulic/glacial/snow) and the derived companion (TWI, recomputed from final height)
  to stay separate — *"the state map is evidence, the derived map is a prediction; do not average
  them in the tool and lose both meanings."* A plugin declaring one does not satisfy the other.

Continued state carries two obligations the others don't: an **epoch** (snow at *what date*?), and
**drivers as a hard dependency** (shipping `snowDepth` without `moisture`/`temperature`/
`insolation`/`windVector` is an effect with no cause).

### Enforcement opportunities — doctrine as registration errors
- **The Snow Rule** (`27`) — "no moisture = no new snow". A snow plugin not declaring `moisture` in
  its reads fails registration. Today's `simulateSnowLayer` is temperature-driven; real gap.
- **The Legal Order** — a plugin declaring `tier: 'derived'` placed upstream of a height write is a
  registration error, not a review-checklist item.
- **Co-evolution** (`27`) — `writes: ['height']` for a material-moving process without `coUpdates`
  fails. This is the rule that catches erosion discarding its mass budget.

### Ice is two different things — do not merge them
- **Glacial ice** (`12`) — SIA flow, 10¹–10³ yr, *erodes bedrock*, deposits moraines. Belongs to the
  solid story; modifies height. **Does not exist in the app at all.**
- **Sea/surface ice** (`12`, `08:137`) — a transient lid on `waterSurface`, never `solidTop`,
  "exactly like snow over land". This is what the app's `gIceSnow`/`iceSnowSurfaceY` currently is.

Ice is **not** cosmetic: `12` makes it a gate on the coastal loop —
`fetch' = fetch · iceFree(dir, season)`, `coastalStep *= openWaterFraction` — so it feeds back into
terrain and must resolve *before* coastal erosion. Sting in the tail: ice-bound coasts are **not**
protected on net; they are among the fastest-retreating on Earth, because thermal undercutting of
ice-rich permafrost replaces wave abrasion.

### Ice formation gates — tiered honestly
| Gate | Tier | Note |
|---|---|---|
| Temperature | P | via `13` lapse rate / snow line |
| Salinity depresses freezing point | **F here** | ≈ −0.054 °C/PSU (−1.9 °C at seawater 35) is standard oceanography but **not in this corpus**. Verify against primary source before shipping. |
| Flow prevents ice | **F here** | Real (rapids stay open; turbulent supercooling, frazil rather than sheet growth) but **no citable threshold velocity**. Implement as an explicitly tunable F-tier gate. |

### Salinity — a proposed registry extension, not doctrine
Not in `27`'s registry. The corpus has the *chemistry and landforms* at P-tier — evaporite zonation
and salt-crust polygons (Warren 2016; Eugster & Hardie 1978, `16`), saltern brine colour, the
brackish estuary reach (`12`) — but salinity as a carried field is an **extension**.

It earns a place because it **produces terrain**: evaporating brine in a closed basin deposits crust
(playas, salinas, sabkhas, salterns). It also gates sea-ice formation, reef viability (`12`) and
shoreline vegetation (`13`). Lens: continued state — authored at sources, advected on
`flowVelocity`, **concentrated by evaporation** (that concentration term is what makes a closed arid
basin produce evaporite rather than merely drying out).

---

## 3. Confirmed defects — measured

### C1 — GPU and CPU run *different erosion models* · TODO
[index.html:3877](index.html#L3877): `gpuReady() ? gpuHydraulicPipes(...) : hydraulicErode(...)`.
Virtual-pipe vs droplet — different physics selected by **what hardware you have**.

Measured: fbm/thermal/warp are **exact** GPU-vs-CPU (corr 1.000, 0% diff); the hydraulic node
correlates **0.854** (mean 9.1%, interior-dominated, so not a boundary bug). End-to-end the default
graph diverges at corr **0.910**, while two same-engine rebuilds are bit-identical.

Consequence: hex forces CPU (`gpuReady()` excludes it), so hex silently runs the droplet model while
square runs pipes. Fixing this is *correctness*, not performance.
Repro: `node tests/legacy/_verify_glsl_probe.js` and the diag in commit `d2f6769`.

### C2 — Both sims compute velocity and discard it · TODO
Pipe model computes per-cell speed at [index.html:1432](index.html#L1432); droplet model carries
per-droplet speed at [index.html:3887](index.html#L3887). `flowVelocity` appears **0 times** in the
file. `27` already has `flowVelocity` in its registry, so this is a missing *output*, not missing
science — and the pipe sim's version is better than a derived one because it is actual flux
direction rather than an inference from drainage area.

### C3 — Erosion's mass budget is computed and discarded · TODO
Same pattern as C2. This is what wires into `sedimentDepth`/`soilDepth` deposition under the
co-evolution rule. **This is the first change in the programme that legitimately moves the digest**
— height will change, deliberately — so it needs a stated baseline re-bless, not a surprise failure.

### C4 — Colour path has no hex branches · TODO
`colorErodeField`'s receiver search is a hardcoded square D8 table with **no `isHex()` branch** —
two of its eight offsets are not lattice neighbours on hex, and it misses part of the true D6 ring.
`boxBlurScalar` (colour diffusion, weathering height-smooth, creep) and `blurField` are
square-separable, so on hex the vertical footprint is `√3/2` of the horizontal.

### C5 — Square 5-point Laplacian on the hex path · TODO
`streamPowerErode` hillslope diffusion, and snow roughness. `08:353-358` names this exactly: the hex
form is `2/(3s²)`, not `1/s²`, and carrying the square constant over is a **silent 1.5× diffusivity**
that reads as a tuning problem rather than a bug.

### C6 — Snow physics on hex · TODO
`cellArea = cell²` should be `(√3/2)·cell²` (hex m³ currently over-stated by 15.5%); hold-slope and
wind-exposure gradients omit `√3/2` on the y term, so N–S slope reads 2/√3 too shallow; the
avalanche stencil is square D8 with no hex branch.

### C7 — Colour knobs: my "dead sliders" report was a measurement error · DONE (as a finding)
Recorded because the *method* matters more than the conclusion. A whole-image mean said every Color
Erosion slider was inert (span < 1/255). Wrong: Color Erosion deposits along **flow paths**, acting
on ~1–10% of cells, so the mean divided a real change by ~100× its area. On p99 the same sliders
span **12–14**.

A second error compounded it: "blend and hold only reach 0.5% of cells" was an artefact of measuring
distance-from-default at the sweep endpoint — both **default to 0.89**, so `t=1` *is* the default.

What survives: `scale` (3.15) and `creep` (1.39) are weak beside `amount` (12.71) — but **by
design**. `scale` is a wavelength control; strength belongs to `amount` and `dirt`, which ship at
0.26 and **0.01**. That is a *defaults* question, not an algorithm one.
Repro: `node tests/legacy/_verify_colorknobs.js [square|hex]`.

### C9 — `makeNode` does not clone parameter defaults · TODO
[index.html:4719](index.html#L4719): `def.params.forEach(pr => p[pr.key] = pr.def)` — assigned by
reference. Every `mountain` node therefore shares **one array instance** with the type descriptor
for its `skirt` curve (`P.curve("skirt", …, mountainSkirtDefault())`, `:4118`). Editing one node's
skirt curve mutates the default for every node created afterwards.

The reason this survived: the digest oracle's own `mk()` at `_verify_digest.js:154` **does** clone
(`cloneParams(pr.def)`). So the oracle never exercises the aliasing, and **fixing it would be
invisible to the digest** — green without evidence, the exact shape this project keeps tripping on.

Consequence for the plugin work: `definePlugin` must **preserve the aliasing verbatim** in Phase A.
A shim that quietly "tidies" default handling would fix a real bug with no gate able to see it.
Fix it as its own commit, gated by `_verify_undo.js` plus a new `_verify_param_defaults.js`.

### C10 — Bridge tooling cannot run, and its surface has drifted · TODO
`_verify_bridge.js --check` exits with `FATAL: acorn is not installed` — acorn is absent from both
`package.json` devDependencies and `node_modules`, and there is no `bridge:gen` script.

The recorded surface has also drifted from the generated block: `bridge-surface.json` has **189
symbols / 178 needsBridge**, while `src/testing/bridge-block.js` declares **161 (25 writable)** —
17 unaccounted for.

Related dead code: `.effect` is declared on 7 node types (`:4567, :4579, :4599, :4616, :4626, :4637,
:4645`) and read **zero** times.

### C8 — Oracle debt from the square-world flip · TODO
- `_verify_hex_sampling.js` S4/S5 — closed form encodes the pre-flip warp world extent.
- `_verify_wireframe.js` W0/W1/W3/W4 — edge-recovery walk validates against a **square adjacency
  model** (hex `covered=785408/905571`). Structural rework, not a retune.
- `_verify_hex_deferred.js` G1/G2 — harness built on `GPU.upload()`/`GPU.prog()`, which are
  square-by-construction (`upload` only makes `n×n`; `prog` caches by key and **ignores the
  source**). The shader itself is verified correct to six decimals by `_verify_glsl_probe.js`; this
  is test debt, not a product regression.

---

## 4. Open work

| | Item | Notes |
|---|---|---|
| W1 | Hex-native blur | 3-axis lattice-line Gaussian across 17 call sites. F-tier construction — `26:232` sanctions only 7-point Laplacian iteration or O(k²), both rejected with measured reasons. `σ_axis = σ·√(2/3)`; boundary renormalisation gated constant-in-constant-out ≤1e-6; ring anisotropy red ~1.155 → fixed ≤1.03. |
| W2 | **MFD6** | This is what actually delivers "smoother and more natural" — D6 alone does not. `26:143`: 6 directions at 60° is **coarser** than D8's 8 at 45° (max aspect error 30° vs 22.5°). Measured H3: hex facet concentration **1.413** vs corrected-D8 **1.17**. Freeman 1991 `p=1.1` (P); Quinn's contour-length term collapses on hex (`26:174`); `spReceivers` stays single-receiver. |
| W3 | GPU hex kernels + 6-pipe | Fixes C1. 6-pipe hydraulics are **F-tier** (`26:53-56` — do not imply a paper); re-derive the six-outflow CFL bound (`08:361`). Relax `gpuReady()` **last**. |
| W4 | Auxiliary-map registry | The three lenses above. Lazily materialised — 12 R32F maps at 4K is ~930 MB, so allocate only what a graph reads; `wetness` could be R8. |
| W5 | Water sources + flow field + ice chain | D5 + C2 + the ice node. |
| W6 | Export profiles + manifest | D6. Includes the final-vs-initial-state contract and driver-completeness check. |
| W7 | Corpus corrections — **after W8** | The squash-or-crop framing D1 dissolved; the 3-axis blur finding; the 6-pipe CFL derivation; salinity as a proposed registry extension. ⚠️ An earlier edit this session added an "authoring domain vs world metric" section to *this branch's* `26-hexagonal-lattice.md`. Main has since **split that chapter**, so that edit is both superseded (the square world dissolved the dilemma it described) and written into a file main replaced. Re-author against the merged `26-hexagonal-grids.md`; do not try to carry the old text across. |
| W8 | Merge `origin/main` | 26 commits: the `26` split and the new chapter `27`. Main's deletion of `terrain-architect/studio` now *agrees* with our move, so it should merge cleanly. **Not yet run.** Housekeeping, not a blocker — see the note below. |
| W9 | Weathering defaults | C7's real finding: `dirt` ships at 0.01, effectively off. Defaults change → digest re-bless. |

---

## 5. Verification lessons

Institutional knowledge, because the same failure recurred **six times** this session and was caught
by a different reviewer each time.

**The standing failure mode is the vacuous gate — a check that passes on the broken build.** Every
instance:

1. A tolerance set *above* the broken path's measured error.
2. A negative control that became sub-pixel after a contract change and read 0.999 for the very
   defect it existed to catch.
3. An acceptance set where all six criteria passed on the **unmodified file**.
4. A probe that `process.exit(0)`'d unconditionally, so an in-page throw read as a clean pass.
5. A sub-gate that could never go green (`buildWireIndex()` unreachable from `updateViewport()`), so
   it would have been waived — vacuity by the back door.
6. A gate collecting side-channel records *only if present*, so a build that stopped producing them
   still passed. Vacuity by **absence**.
7. **A gate whose result never arrived at all.** Two `_verify_digest.js` runs launched into the
   background were still alive ~22 hours later (pids 5184/24096, ~1300 min wall, **120 CPU seconds
   each, then 0.2% busy** — blocked, not spinning). The 120 s is the tell: it is exactly the tool's
   default 120 000 ms timeout. The runner timed out, its shell was reaped, and the orphaned `node`
   child blocked forever writing into a pipe with no reader. Their verdicts were lost — not red,
   not green, *absent* — and an absent verdict is indistinguishable from one nobody looked at.

Entry 7 is the general form the first six are special cases of: **a gate only protects you if its
verdict is observed.** Wrong tolerance, unreachable sub-gate, and never-returned all fail the same
way at the point of use. So: give a gate a timeout longer than its honest runtime, redirect output
to a file rather than a pipe that can fill, and treat "I never saw the result" as a failure to
re-run — never as tacit approval.

The countermeasures that worked:

- **Arm bounds between two MEASURED endpoints** — one on the broken path, one on the fixed. Never
  assert a bound from theory. A guessed 1.5 failed the *correct* build; the measured pair was
  1.000 / 1.313, so the bound went at 1.15.
- **Score the probe's own health** — boot failure, in-page throw, page errors, empty record set,
  wrong file under test. And make an empty red baseline a *failure*: finding nothing wrong with a
  known-broken build means the probe is blind.
- **Pin counts, not just values.** Absence of a record is not absence of a defect.
- **When a contract changes, re-derive its negative controls.** A control inherited from the
  superseded contract can start silently passing on the defect.
- **Match the statistic to the phenomenon.** A spatially concentrated effect (flow paths, ~1% of
  cells) is invisible to a whole-image mean. See C7.
- **Absence of a rejection is not approval.** A generated edit carrying `why: "PLACEHOLDER — do not
  apply this text"` was applied because the filter skipped only what a reviewer had explicitly
  rejected — and that region had received no verdict at all. It disabled a bounds check via operator
  precedence and hung the app in a silent infinite loop with zero page errors.

**Run cross-model review per phase, not at the end.** Reviewing with the same model found the
vacuity pattern three times; it took *different* models to find the fourth, fifth and sixth —
including a transposed noise domain (`ox` sampling `gnoise(du/nh, dv/n)` where `oy` correctly used
`du/n, dv/nh`) that was inert on square and so invisible to the digest.

Tooling note: `codex` is unusable locally (CLI pinned to a model version it cannot serve); `copilot`
is the working fallback. And `GPU.prog` caches by key while **ignoring the source** — it silently
returns a stale program when two call sites share a key.

---

## 6. Open questions

- **React or Angular?** D3 proposes React with reasoning. Unconfirmed.
- **Salinity** — accept as a registry extension, or keep it out of the DAG?
- **Ice flow threshold** — no citable number. Ship as a tunable F-tier gate, or leave ice
  velocity-independent until a source is found?
- **Weathering defaults** — `dirt` at 0.01 is effectively off. Change (and re-bless the digest), or
  is that deliberate art direction?
- **Does the skill still ship a single-file build?** Phase F of the architecture plan assumes yes.
