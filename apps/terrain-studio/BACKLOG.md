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
nothing about whether the doctrine exists.

**That merge has now happened** (`a7cc8f8`). The repo copy carries `26-hexagonal-grids.md` and
`27-engine-data-handoff.md`, matching the installed one.

**Correction — there were TWO chapter 26 files, and the second one was ours.** Resolved in
`f8ddd62`; the history is kept because the mistake is repeatable. An earlier revision of this
section said `26-hexagonal-lattice.md` was "gone — never cite it". That was wrong, and wrong in a
way worth understanding rather than just patching:

- `26-hexagonal-lattice.md` was **never in main**. It was written on this branch. A merge cannot
  delete a file the other side never had — git simply carries ours through — which is exactly why it
  never appeared among the 45 conflicts. I read its absence from `origin/main` as evidence it had
  been *deleted*, when it was evidence it had never been *there*.
- It still exists (20 398 bytes), it is live, and `08-output-contract.md:287` links it **by
  filename**. It also already carries all three W7 citations in a `## Provenance spine` section —
  so the work W7 was scoped to do was, in substance, already done.
- Consequently the two `SKILL.md` edits I discarded during the merge were **valid**: they named a
  file that exists. I threw them away on a false premise. (Restoring them verbatim is still wrong —
  see below — but the reason is different from the one I gave.)

The real defect this exposed was worse than a missing citation: **two live files both answered to the
`26` token**, decorating the same claims with different tiers (ours: "P for the papers"; main's
chapter: nothing on these citations at all). A corpus whose whole purpose is provenance cannot have
one chapter number resolve to two files.

**Resolved** (`f8ddd62`): consolidated into `26-hexagonal-grids.md`, duplicate deleted, `08`'s
inbound link repointed, four citation families carried across with their attributions corrected
under review, three index rows added. There is now exactly one chapter 26.

Method note, because this is the second time in one session: **absence in one place is not evidence
of an event elsewhere.** `git ls-tree origin/main` told me what main has, not what happened to our
file. The check that would have caught it — `ls` on the working tree — cost one command.

---

## 1. Decisions taken

### D1 — A hex field is `RES × round(RES·2/√3)`, giving a square world · DONE
`512 × 591`. Equilateral cells, no squash, no crop. Costs **+15.5% cells** at equal `cellSize`,
which `26` names as the trap: the "13.4% fewer samples" saving only materialises if you take a ~15%
*coarser* cellSize, and carrying the square cellSize over makes it a memory *cost*. We took the
cost deliberately — a truthful square world is the product requirement.

Supersedes an earlier "squash or crop, no third option" framing that was written into the corpus.
That dilemma was an artefact of reusing the square array shape; giving hex its own row count
dissolves it.

**No longer outstanding, and not for the reason recorded.** This entry used to say "`26` still
carries the old framing and needs correcting". It doesn't: the surviving `26-hexagonal-grids.md`
has **zero** occurrences of squash/crop/"no third option" — that framing lived only in the branch's
own `26-hexagonal-lattice.md`, which is now deleted, so it went with it. The surviving chapter
independently agrees with the choice D1 made: *"at equal `cellSize` a hex grid has 15.5% more cells
per unit area"* and *"treat the 13.4% as the direction of the advantage, not a budget line"*.

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

### Both sides of the handoff, read against each other · researched

Read `terrain-architect/27` + `03` (producer) against `terrain-renderer/14` + `12` + `13`
(consumer). The two corpora agree on the water-source design and **both refuse the ice chain**.

**Authored water sources are better grounded than we assumed — `P`-tier, not folklore.**
`03:696-701` states the rule we arrived at independently: *"A spring is not a bump in the height
field — it is a **source term in the flow field**. Place it as discharge and let routing and erosion
carve the valley below it… Stamp a riverbed into the height instead and you get a channel that
ignores the hydrology and stops where you stopped drawing."* Authored sources are the **Št'ava 2008**
extension (`00:245`, **P**). Three consequences we should just adopt:

- **`discharge` is m³/s, seeded into the same accumulation stack as `A`** (`03:673-676`) — no new
  algorithm, only a different seed. Under uniform rain `Q ∝ A` and nothing changes; with sources
  they diverge, and **`Q` is the physically correct driver** (stream power `K·Q^m·S^n`, and river
  width/depth scale on `Q`). It is what lets a big river cross a desert without pretending the
  desert fed it — the Nile and the Colorado are exactly this (`03:678-683`).
- **The `kind` enum already exists**: distributed rain · boundary inflow · spring · karst
  resurgence · oasis · glacial/snowmelt (`03:687-694`), each with its placement rule.
- **Flat-at-spill is not a constraint we enforce — it is a consequence.** `lakeSurface = filledDem`,
  "flat, by construction" (`03:326-328`), out of priority-flood (**P**, `00:232`). D5's claim that
  designers *cannot* violate it is exactly right, and the reason is that they never touch it.

**The ice chain has no grounding. All three criteria fail, and the corpora were searched.**

| Our criterion | Status |
|---|---|
| salinity too high | **`salinity` does not exist** — no field, unit, port or source attribute in *either* skill. Verified by exhaustive grep. |
| water temperature too warm | **No water-temperature field.** Registry `temperature` is **air** temperature, latitude + 6.5 °C/km lapse rate (`27:145`). Water temp appears twice as prose (`12:374-380`, `20:783`), never as a map. |
| flow too fast | **No flow-speed criterion for ice anywhere.** The only speed-driven effect the corpus sanctions from `flowVelocity` is foam — and that is the *engine's*: *"The tool ships the vectors; it never ships the foam"* (`27:160`). |

The corpus's only freeze gate is `snowfall(p) = moisture(p) · freezeFraction(temperature(p))`
(`27:184`) — precipitation, on land, from air temperature. It is not a water-surface ice model.

**What to build instead — the representation is grounded even though the criterion is not.**
`12:353-359`: *"**Sea ice is not terrain, and the first rule is not to make it terrain.** It is a
transient solid crust on the water surface — the layer stack's `waterSurface` grows a lid. It never
enters `solidTop`, it carries no bathymetry, and baking it in is the sea-going version of baking
water into the height field."* So: ship `iceThickness` (m, `R32F`) as a transient field riding on
`waterSurface`, shaped like snow-over-land, with `iceFree(azimuth, season)` gating fetch
(`12:361-370`). **Mark it `F`/`?` in our own docs — it is our design, not a citation.** Do not
attach Cordonnier 2018 (that is avalanche) or the SIA (that is glacier flow) to it; neither covers
surface water freezing. And ship *initial state + drivers*, never a baked binary ice mask — the
Masking Doctrine again (`27:217-220`).

**The one salinity path that IS grounded**, and it is a good one: an **endorheic sink**
(`03:703-705`) with no outlet concentrates salt by evaporation, giving `P`-tier mineral zonation
with real units — carbonate → gypsum (~130–150 g/L) → halite (~300–350 g/L) → bittern salts — plus
the concentric saltern colour banding (`16:144-176`, `00:433`). So a `kind: sink` object plus an
evaporation term buys the salinity gradient honestly. g/L is the only unit the corpus uses; use it.
If we do add `salinity`, it classifies as **STATE** (`27:81-84`) — advected, mixed at confluences,
concentrated by evaporation — so **the co-evolution rule binds it**: every node that moves water
co-updates salinity in the same pass, or the information is destroyed unrecoverably.

**Four constraints that change the design:**

1. **Moving a source invalidates GLOBALLY, not regionally.** Flow accumulation and stream power are
   declared GLOBAL — *"they cannot be tiled, full stop"* (`14:48-53`), and discharge routing is the
   same machinery. Dragging a source in the viewport re-solves the whole watershed. Budget for it
   or declare a hydrological domain; region invalidation is for LOCAL/NEIGHBOURHOOD nodes only.
2. **We need a `sink` object and a no-fill flag, or endorheic designs are unrepresentable.**
   Depression handling is mandatory *except* for the no-fill list — playas, craters, tarns, dolines,
   thermokarst, oxbows, lagoons (`03:109-128`). Drop a source in one and filling erases the
   landform; a crater lake silently vanishes.
3. **Our propagation rule points the wrong way.** We said "if a node is simulated, everything
   downstream must be too". The corpus's rule is **upstream inheritance**: *"Give it the tiling
   contract of its worst upstream, not its own"* (`14:222-226`) — a node's *cone* sets its contract,
   not its body. Same answer on water; the corpus form catches the bug ours misses, namely a
   cheap-looking accumulator downstream of a sim that is not cheap. Note these are **two orthogonal
   flags**, not one: *global/path-dependent* forces SHIP (no pixel shader can see beyond its
   footprint), *runtime-simulated* forces SIMULATE. Ice sits downstream of flow accumulation, so it
   inherits GLOBAL and **cannot be a pixel-shader effect on any engine**.
4. **Profiles may vary resolution, format and mode — never names, units or semantics.**
   `27:235-237`: the registry names are **wire names**; the emitter is the only place engine
   conventions exist. And a profile must not bake water (`08:126-128`): *"solid covers (snow, soil,
   sand) can bake; water should not — bake the sea in and you get the wall you can't swim in."*

**The silent bug waiting for us in the ice chain.** `flowVelocity` is a *vector* map, and filtering
averages opposing vectors toward zero (`14:134-137`) — a mip of a converging valley reads as calm.
An ice rule that thresholds `length()` of a *filtered* flow vector will therefore **grow ice down
the middle of the fastest channels** at coarse LOD, which is precisely backwards. Read a separately
mipped **scalar speed** channel (`14:140-144`). This is the highest-probability defect in the whole
feature and it fails in the direction that looks plausible.

**Format floor, forced by our own thresholds.** Every input to the ice rule is thresholded, and
thresholded quantities may not be 8-bit — 8-bit temperature under a freeze threshold produces a
**terraced snowline**, the quantisation contours becoming isolines (`14:295-298`). That forces the
climate pack to `RGBA16F` (`14:91` conditions it on exactly this). Stricter still on our side:
simulation-consumed maps — `flowVelocity`, `waterDepth`, `windVector`, `snowDepth` — may **never**
drop below `R32F` (`27:228`). *Provenance caution:* the 8-vs-16-bit doctrine is **F**-tier
self-described sibling doctrine (`14:335`); only *"never quantise sim-consumed maps"* carries **D**
backing from `27`.

**Two audit rules to adopt verbatim**, because they make "a terrain is a set of maps" checkable:
*"every auxiliary map is a driver, not a decoration"* — a map with zero declared consumers is
deleted from the **shipping** manifest, not shipped "in case" (`14:22-28`); and *"every runtime
effect names the map that drives it"* — if no field says where, extend the generator's contract
rather than inventing renderer-side data (`14:30-37`). Both keep everything in the **tool** manifest
regardless (`14:28`) — Studio producing more maps than any engine ships is sanctioned.

**Registry gap to fix on our side:** `snowDepth`, `sedimentDepth`, `sandDepth` and `flowAccum` are
named as state maps and appear in `27`'s co-evolution, consumption and precision rules, but have
**no row in `27`'s four layer tables** — their units live in `08` (depths in m; `flowAccum` m²,
R32F). A registry generated from `27` alone drops all four. Also `shore distance` is a required
input in `12:33` with no row in `14`'s registry at all.

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

- `_verify_wireframe.js` W4 — **FIXED**. Now 6/6 on both lattices: square `512×512
  covered=784385/784385 missing=0 oob=0`, hex `512×591 covered=905571/905571 missing=0 oob=0`,
  W5 spun 130 288 diagonals so it is not vacuous.

  It was never an adjacency model, a re-count, or a re-pairing — I guessed all three before
  measuring, and all three were wrong. The whole defect was **one allocation**:

      const mask = new Uint8Array(n * n);     // vertex indices run to n * rows

  On square `rows === n` and it is correct. On hex `rows = round(n·2/√3) = 591`, so the mask can
  address rows 0..511 and **nothing else** — and an out-of-range `Uint8Array` write is *silently
  discarded*, no throw, no NaN, no warning. So the recorder dropped every edge whose lower endpoint
  lay in rows ≥ 512 and reported a believable shortfall instead of an error.

  The arithmetic identifies it beyond doubt. Restricting each edge family to rows 0..n−1:

      horizontal (n−1)·n  +  vertical n·n  +  diagonal n·(n−1)  =  785 408

  which is the observed `covered` **to the unit**. The `slot()` delta family `{1, n−1, n, n+1}` was
  already correct for hex (odd-r's row-parity neighbours land on `n−1`/`n` for even rows and
  `n`/`n+1` for odd), and `analyticEdges` already used `fieldH()`. Only the buffer was square.

  Correction to my earlier note here: the 13.27% uncovered **is** the same geometric constant as the
  13.4% — both are `1 − √3/2`, since the unaddressable rows are exactly `rows − n` out of `rows`.
  I had written it off as a misleading coincidence. It was the signature.

  Guard added so it cannot recur quietly: `indexOutOfRange` counts writes the mask could not
  accept, and `coverOk` now requires it to be zero — *a coverage number from a recorder that cannot
  address the whole field means nothing.* It earned its keep immediately, catching a second object
  (W5's stale-path record) that wasn't reporting the field at all.

  **The general lesson, and the reason this sat undiagnosed:** a typed-array OOB write is the
  perfect vacuity engine. It removes evidence without producing any. Prefer `n * rows` derived from
  the field contract over any `n * n` written from habit, and assert addressability before believing
  a count.
- `_verify_hex_sampling.js` S4/S5 — still open; closed form encodes the pre-flip warp world extent.
  The audit below adds three more sites in this file, including one that makes **S5 unfalsifiable**.
- `_verify_hex_deferred.js` G1/G2 — **FIXED** `3f63af3`, 4/4. I had this filed as harness debt
  caused by `GPU.upload()`/`GPU.prog()` being square-by-construction. The conclusion was right (the
  shader is correct — six decimals, `_verify_glsl_probe.js`) but the attribution was wrong, and a
  wrong attribution keeps a one-line defect classified as someone else's problem indefinitely.
  Actual cause: `rectTex` was declared `(key, w, h, data)` and called `rectTex(n, nh, f)`, so every
  argument shifted — `w=nh`, `h=`**the Float32Array**, `data=undefined`. It does not throw, which is
  why it survived: `w*h` is `number × Float32Array = NaN`, `new Float32Array(NaN*4)` is
  **zero-length**, and `i < NaN` is false on the first test so the copy loop never runs and never
  dereferences `data`. An empty texture uploaded in silence. `key` was never used in the body.

### C11 — Square-shaped buffers across the oracle suite · WIP

Generalised from the wireframe bug. 156 sites audited across 25 files: **16 BUG, 117 LATENT, 15
NOT_A_FIELD, 8 STAGING_OK**. Every BUG is in one of the five hex oracles — the gates that exist to
prove hex correctness were themselves square. The 117 LATENT are safe *today* only because those
files never leave the square lattice.

Two mechanisms, and they need different fixes:

- **Discarded writes** — a buffer too short for the field; out-of-range `TypedArray` stores vanish
  silently. This is the wireframe case.
- **Out-of-range reads** — a *correctly sized* square field handed to a hex kernel that iterates
  `fieldH()`. Reads past the end give `undefined → NaN`, and NaN then propagates somewhere that
  cannot detect it: a min-heap sift (`<=` against NaN is always false, so NaN sorts to the **top**)
  or a comparator (`(a,b) => g[b]-g[a]` with NaN keys is not a valid order). This is the hex_flow
  case, and it is the more dangerous of the two because the buffer looks right.

Fixed: `_verify_hex_flow.js` (`6179fdf`), `_verify_hex_deferred.js` (`3f63af3`).
**Still open — 8 sites in 3 files**, all adversarially UNVERIFIED (the workflow capped verification
at 3 per group and logged that it had):

| File | Sites | What the audit claims |
|---|---|---|
| `_verify_hex_sampling.js` | 80, 212, 241 | `mkRamp` allocates `n*n`; **S5 unfalsifiable** because `bakeThumb` is already converted and reaches row 216 of a 192-row ramp; `warpField` runs over an input built under `square` |
| `_verify_hex.js` | 139, 168, 278 | H4b's negative control, H2/H3's cone, and H6's paraboloid are all `n*n` while `terrainDef.lattice` is `'hex'`. **Measured, and less severe than filed** — see below |
| `_verify_hex_dem.js` | 77, 82 | D3's export probe is `n*n`; and the resample no longer matches the shipped `exportHeightmap`, which now applies `rowSpan = (fieldH()-1)/(RES-1) = 1.157` |

**`_verify_hex.js` measured, not assumed** — it was one of the 8 the workflow never got to verify, and
the file passes 8/8 with coherent discriminating numbers (H3 ring anisotropy 1.003, H6 hex/square
curvature agreeing to five digits, H7 `lastTouchedRow=221/221`), which is not what corrupted input
looks like. So I probed it directly at `RES=192`, hex, feeding `curvatureField` the same `n*n`
paraboloid the file builds:

```
fieldH=222  fieldLen=42624   probe=36864  shortfall=5760
nanCells=5952   firstNaNRow=191   lastAllFiniteRow=190
H6 annulus spans rows 20..172    annulusTouchesNaN=FALSE
```

Both halves matter. **The NaN is real** — 5952 output cells, 14% of the field — and it starts at row
**191**, one row before the allocation ends, because the curvature stencil at 191 reads its
neighbour at 192. `gAt` does not save you: it clamps `y` to `fieldH()-1 = 221`, the *logical*
height, then indexes an array that only has 192 rows. **And no gate looks there.** H6's annulus
spans rows 20–172, so the measurement is untouched.

These are therefore **domain-restricted, not corrupted** — the gates are honest about what they
sample, they just sample 86% of the field. That is a real gap for a lattice whose whole point is the
extra rows, and it needs fixing; but it is a different severity from `_verify_hex_flow.js`, where the
NaN reached a min-heap and corrupted the flood globally.

**The rework is simpler than it looks, because the flip already did the hard part.** Measured at
`n=192`:

```
world extent, square :  191 × 191
world extent, hex    :  191 × 191.4      ratio 1.0021
centre cy, square    :  95.5
centre cy, hex       :  95.7             they agree to 0.20 cells
```

The two lattices now have the **same world footprint** — that is what the square-world flip bought.
So the probe constants should *converge*, not diverge: one radius `r0 = (n-1)/2` fits both, and one
centre serves both. What the file has instead is `r0 = cy = (n/2)·√3/2 = 83.1`, the **pre-flip** hex
half-extent from when the hex world genuinely was 13.4% shorter. Carried forward, it sizes the cone
to a footprint that no longer exists and puts its centre **12.6 cells above** the field centre.

So the fix is: allocate `n × fieldH()`, fill every row, and replace the `·√3/2` geometry constants
with the shared ones. Re-baseline afterwards — H2/H3/H6 numbers will move, and the old values are
not the target.

**Do not rush this one.** `mkCone` takes a `hexGeom` flag that is deliberately independent of
`terrainDef.lattice`: both cones go through the *same* hex kernel, and the square-geometry one is
the control. Changing the row count changes what that control means, so read H2/H3's comparison
before touching it. This is a case where the shape fix is trivial and the *semantics* of the
negative control are the actual work.

**The lesson that generalises past this file.** `_verify_hex_flow.js` passed **6/6 before the fix**.
Every asserted quantity — pits, borderReach, terminalMass — is a count or a ratio, and the phantom
NaN border left all of them intact. The one number that moved was `overFill` (0.583 on a field of
range ~0.8, where a strictly descending cone requires 0), and it was **printed in the message and
omitted from the condition**. So: *a quantity worth printing is a quantity worth asserting.* If it
is diagnostic enough to report, it is diagnostic enough to fail on — otherwise it is decoration
that makes a broken gate look thorough.

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
| W7 | Corpus: one chapter 26 · **DONE** `f8ddd62` | Scoped as "re-author three lost citations"; the premise was wrong twice. Nothing was lost — `26-hexagonal-lattice.md` was **ours**, main never had it, and a merge cannot delete what the other side never had. The real defect was a **duplicate chapter 26**: two live files on the `26` token with divergent tiers. Consolidated into main-s `26-hexagonal-grids.md`, duplicate deleted, `08`-s inbound link repointed. Four citation families carried (verified absent from the **installed** corpus: Wang & Ai 0, Hasslacher 0, Sivaswamy 0, absence-record 0), plus three index rows. Attribution corrected under review: Wang & Ai 2018 does **not** introduce D6 (de Sousa 2006 predates); both papers are single-receiver drainage-*structure* results that ground routing and **nothing downstream** — they do not license hex erosion; six-fold is *smallest sufficient*, not necessary; HPP/FHP are P as physics, **F** as a transfer onto terrain. |
| W8 | Merge `origin/main` · **DONE** `a7cc8f8` | 45 conflicts, two classes. 43 studio paths were rename/delete (we moved, main deleted) — resolved to our version at the new path, staged bytes identical to pre-merge HEAD. `SKILL.md` + `00-index.md` taken from main. Digest 60/60 after. Note the merge commit message contains an error corrected in `33f17fe`: it says main *deleted* `26-hexagonal-lattice.md`. Main never had it. |
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
7. **A gate that never ran, and then reported success.** Two `_verify_digest.js` runs launched into
   the background were still alive ~22 hours later (pids 5184/24096, ~1300 min wall, **120 CPU
   seconds each, then 0.2% busy** — blocked, not spinning). The 120 s is the tell: it is exactly the
   runner's default 120 000 ms timeout. The runner timed out, its shell was reaped, and the orphaned
   `node` child blocked forever writing into a pipe with no reader.

   The instructive part came on cleanup. Killing the two orphans let their parent shells finally
   exit — and both tasks were then reported **completed, exit code 0**, with **zero bytes of
   output**. Their labels were "Square byte-identity gate" and "Verify square is still
   byte-identical", so at a glance the record showed two green byte-identity gates. There were
   none. The exit code belonged to the shell, not to the check.

   This is the worst form of the pattern in this list, because the other six at least fail
   *quietly*. This one **fabricates a pass**. No coverage was actually lost here — both were the
   digest, and a foreground run of it returned 60/60 at the merge commit — but that was luck. The
   green badge was available to be believed, and nothing except reading the empty output file
   distinguished it from a real one.

Entry 7 is the general form the first six are special cases of: **a gate only protects you if its
verdict is observed, and an exit code is not a verdict.** Wrong tolerance, unreachable sub-gate,
and never-returned-but-reported-zero all fail identically at the point of use. So: give a gate a
timeout longer than its honest runtime; redirect output to a file rather than a pipe that can fill;
**assert on the gate's own output, never on its exit status alone**; and treat an empty result as a
failure to re-run, never as tacit approval. A gate that cannot say *what* it checked did not
check it.

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
