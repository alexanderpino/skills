# Reference implementations

Runnable, **numpy-only, pytest-verified** mirrors of the simulation pseudocode in the
`terrain-architect` references. Every module is small and reads like its pseudocode block;
every module ships a test that asserts the *exact oracle* the skill's verification chapter
(`09-verification.md`) already specifies for it. Nothing here is production code — it exists
so a reader can **run the skill's own algorithms and watch `09`'s checks pass**, and so the
claims in the references are executable rather than merely asserted.

This repository currently provides no separate licence grant for these files. Treat them as
executable evidence, not code that may automatically be copied into a product. Engine
implementations consume the neutral pseudocode, grounding decisions and oracles from the
references; any reuse of repository code requires an applicable project licence or explicit
permission.

## Run

```bash
cd terrain-architect/reference-impl
pip install -r requirements.txt      # numpy, pytest
pytest -q                            # 129 pass; 15 optional checks skip (see below)

# optional independent checks (validity evidence beyond the numpy-only oracles):
pip install -r requirements-crossvalidate.txt   # RichDEM/pysheds/Landlab -> 5 cross-validation tests
pip install -r requirements-validate.txt        # pint -> 10 dimensional-consistency tests
pytest -q                            # 144 pass; all optional checks now run
```

## What's here, and how each is verified

The verification design is **layered**: use the strongest oracle available per algorithm —
a closed-form value where one exists, otherwise `09`'s invariants (determinism, no NaN, mass
conservation, radial symmetry) and quantitative signatures, plus an optional cross-check
against an independent library.

**On what "verified" means here:** most oracles prove the code *solves the stated equation
correctly* (internal consistency), not that the equation is *right* (validity). The evidence
that separates the two — dimensional consistency, independent-library agreement, published
benchmarks, primary-source audit — is tracked in **`VALIDATION.md`**.

| Module | Mirrors | Verified by (the oracle) |
|---|---|---|
| `analytic.py` — tephra thinning | `11` Pyle 1989 | `log(thickness)` linear in distance, slope `−k` |
| `analytic.py` — seafloor age–depth | `12` Parsons & Sclater 1977; Stein & Stein 1992 | matches `d₀+C√age`; GDH1 continuity + old-crust plateau |
| `analytic.py` — PDC energy cone | `11` Malin & Sheridan 1982 | runout `= Hc/μ`; inundates within runout, blocked by a ridge |
| `analytic.py` — avulsion criterion | `03` Mohrig et al. 2000 | fires at `SE≈1` with a trigger, not otherwise |
| `isostasy.py` — Airy + flexure + rebound | `02` Turcotte & Schubert; Watts; Molnar & England | exact single Fourier mode; Airy limit; analytic line-load kernel; `ρc/ρm` |
| `flow.py` — priority-flood fill | `03` Barnes et al. 2014 | no interior pit remains; fill never lowers · *xval: RichDEM* |
| `flow.py` — D8 / MFD + accumulation | `03` O'Callaghan & Mark 1984; Freeman 1991 | constant-slope routes downhill; Σarea conserved; MFD less grid-biased on a cone · *xval: pysheds* |
| `diffusion.py` — hillslope diffusion | `04`/`05` Culling 1960 | exact discrete single-mode decay; mass conserved |
| `erosion_thermal.py` — talus | `05` Musgrave et al. 1989 | converges below repose; distance-correction cuts grid bias; deterministic |
| `erosion_droplet.py` — droplet | `04` Beyer 2015 | deterministic; mass conserved; ensemble mean is radial (gullies are random, not grid) |
| `erosion_pipe.py` — virtual-pipe water **+ coupled erosion** | `04` Mei et al. 2007 | `pipe_water`: depth ≥ 0 (step-3 scaling) & finite on steep terrain, water conserved, 8-pipe more radial than 4-pipe. `pipe_erode`: the full loop — flow → sediment capacity → **erode/deposit** (fans, deltas, valley fill) → conservative sediment transport; closed basin conserves bed mass, slopes erode & basins deposit, stable on steep terrain. `python erosion_pipe.py` → before/after `erosion_pipe.png` |
| `erosion_streampower.py` — stream power | `04` Braun & Willett 2013; Cordonnier 2016 | **slope–area exponent = −m/n** at steady state |
| `dunes.py` — Werner slab CA | `05` Werner 1995 | slabs conserved; instability (`p_sand>p_bare`) sweeps ground bare; deterministic |
| `winds.py` — mass-consistent wind | `13` Sherman 1978 | corrected field's divergence → 0 (Helmholtz–Hodge projection); solenoidal field passes through |
| `runout.py` — Voellmy runout | `05` Voellmy 1955 | runout length on a ramp matches `L = H/tan(α)`; more friction → shorter |
| `noise.py` — procedural noise | `01` Perlin (Improved 2002), value, Worley, fBm, ridged/hybrid multifractal, domain warp, curl | Perlin **= 0 on the lattice**; single-octave fBm **= the base noise**; curl noise **divergence = 0**; fractal sums finite & bounded |
| `analysis.py` — analysis & masks | `06` slope/aspect, Zevenbergen–Thorne curvature, horizon AO, Beven–Kirkby TWI, selectors, masks→materials | slope of a plane = its gradient; discrete Laplacian of a paraboloid = `−2/R`; AO 0 on flat, >0 in a pit; TWI finite on flats; material masks **partition** (Σ ≤ 1) |
| `ops_filters.py` — primitives/ops/filters | `10` SDF primitives, smooth min/max, Gaussian/median/bilateral/guided/Perona–Malik, morphology, warps | SDF exact & signed; `smin ≤ min`; median kills a spike & keeps a step; bilateral/guided/PM keep a step where Gaussian smears it; `dilate ≥ h ≥ erode`, opening idempotent, closing fills a pit |
| `scatter.py` — object distribution | `07` Bridson Poisson-disk, density rejection, jittered-grid (tileable), rule-based gates | **every pair ≥ r apart** (blue noise); density-rejection follows the field; jittered grid deterministic & seamlessly tileable; gates reject cliffs/treeline/water |
| `landforms.py` — geological landforms | `11` impact craters (Pike/Melosh), strata & terracing, folding, karst sinkholes, **fault-block buttes**, and the **Mountain / Ridge / Volcano / Canyon** landform generators | crater `depth/D ≈ 0.2`, rim raised, ejecta `∝ r⁻³`, central peak when complex, diameter `∝ g` inversely; strata periodic; terrace snaps to treads; fold is a sinusoid; karst carves pits **only** on soluble rock (the `03` do-not-fill exception). The landform *generators* are **feature primitives** (Génévaux 2015 / Guérin 2016) — the Gaea-style nodes you place, combine and erode: **`mountain(style=…)`** built like Gaea's Mountain node (modulated-Voronoi ridge network + distortion, Basic/Eroded/Old/Alpine/Strata presets that bake the weathering — an organised massif, **not** noise on a lump), **`ridge`** (asymmetric hogback), **`volcano`** (strato/shield + summit crater + barrancos), **`canyon`** (plateau incised by a meandering gorge). `python landforms.py` → `landforms.png` (Mountain styles + Erode/Ridge/Volcano/Canyon) |
| `crater.py` — parameterised impact | `11` size + **angle**: Collins/Melosh/Marcus 2005 π-scaling, Gault–Wedekind obliquity | `D_tc ∝ L^0.78 v^0.44 g^(−0.22) (sinθ)^(1/3)` (exponents exact); transition `∝ 1/g`; simple↔complex; circular above ~12°, elongated below; **mass-conserving** ejecta pushed downrange (up-range forbidden zone / butterfly) |
| `crater_demo.py` — natural render (presentation) | composites the `crater.py` physics with `noise.py` (01) | smooth circular cavity + distinct raised **rim ring** (Pike), irregular rim/ejecta outline, terraced walls, defined central **massif**, hummocky **downrange** ejecta apron; grazing → irregular furrow (deeper up-range); hillshaded → `crater_matrix.png`. A *look*, not oracle-verified |
| `crater_anatomy.py` — grazing anatomy figure | labels the corrected grazing morphology | map + trajectory cross-section → `crater_anatomy.png`: deeper up-range floor, up-range forbidden rim, transverse butterfly wings, downrange ejecta. Needs Pillow for the labels (terrain is numpy-only) |
| `sims_illustrative.py` — **⚠ illustrative** sims | `12`/`19` lava CA, SIA glacier, coastal cliff retreat, tides | **INVARIANTS ONLY, no decisive oracle** — lava conserves mass (erupted = molten + frozen), glacier transport conserves ice & H ≥ 0, coastal erosion removes mass monotonically, tide bounded & solid untouched. Sketches to watch move, **not** verified numbers |
| `archetypes.py` — **province** compositions | `20` — **16** archetypes across Groups A–L as diffs from the baseline (alpine, appalachian, canyon, mesa, erg, basin&range, badlands, tower karst, stratovolcano, caldera, fjord, sea cliffs, ag terraces, lunar cratered, maria, mars) | one recognisable *place* per tile, dominant agent switched; each carries its `09` signature; **labelled** montage → `archetypes.png` (full coverage ledger incl. what's *not* renderable in `ARCHETYPES.md`). Resolution-parametric; tier L — compositions, not new algorithms |
| `screen_worlds.py` — **screen worlds** | `20` "Screen worlds": 8 fictional planets as re-dressed archetypes (Arrakis, Monument Valley, Pandora, Hoth, Skull Island, Beggar's Canyon, Crait, Miller's world) | each names its real filming location + the archetype it decomposes to; only the *dressing* (render / sea level / material) changes → `screen_worlds.png` |
| `shallow_water.py` — **flow sim** | `05` Mei, Decaudin & Hu 2007 virtual-pipe shallow water | water is a real mass-conserving VOLUME: a rainfall/​spring **source**, depth as state, pipe flux by head gradient, water leaves at the edges; **discharge in m³/s** that grows downstream. Invariants: depth ≥ 0, closed basin conserves rain, open domain balances rain = out + stored |
| `hydrology.py` — **water surface + translucent render** | Leopold & Maddock 1953 hydraulic geometry + priority-flood; Beer–Lambert | turns a **discharge** field (m³/s, from the flow sim or the `rain·area` proxy) into a water LEVEL (lakes to spill level, rivers a discharge-scaled depth), and composites water as a **translucent** stage (`water_over_land`: `T=exp(−k·depth)` — the bed shows through shallow water, deep water goes blue). The rendering layer over the real flow |
| `hero.py` — **3D hero view** | a pure-numpy software rasteriser (perspective camera + z-buffer) | projects the heightfield as a mesh, lights it in 3D (sun+sky + AO), draped with substance colour + water from a real **`shallow_water`** flow (rendered via `hydrology`), sky + depth fog + supersampled AA → `hero.png`. `from_graph()` renders terrain **straight from the node graph** (uplift → stream-power erosion → thermal → shallow-water flow), no hand-sculpting. The angled 3/4 "viewport" view; no 3D deps |

## Sandbox: run a graph and look at it

The modules above are *nodes*; `graph_demo.py` is a tiny sandbox that wires them into a
**terrain graph** you can run and render — the place to drop a new algorithm in during
development and actually see what it does. It has no dependencies beyond the numpy the rest
of `reference-impl` already needs.

```bash
python graph_demo.py                          # droplet backbone, 96² -> eight PNGs in out/
python graph_demo.py --backbone streampower --size 128 --extent-km 120
python graph_demo.py --noise ridged           # base noise family (01): perlin/value/ridged/hybrid/warp
python graph_demo.py --seed 7 --sun-sweep 8   # rotating-light frames (09's sun sweep)
python graph_demo.py --cache-demo             # watch the content-addressed cache
python graph_demo.py --scene mesa             # a mesa ARCHETYPE as a DAG, the way Gaea/WM/Houdini do it
```

The `--scene mesa` path is the answer to "build effects the way Gaea / World Machine / Houdini do":
a recognisable archetype assembled as an explicit node DAG — noise **generator** → fault-block
**feature primitive** (`landforms.fault_block_butte`, itself `ops_filters.sd_convex_polygon`) →
**strata** → **thermal** talus → flow/slope/**materials** → **photoreal** colorize. `GROUNDING.md`'s
*"How this maps to Gaea / World Machine / Houdini"* section tabulates every node category against the
tool it mirrors and the paper it is grounded in, and discloses where we diverge (our droplet erosion
is Lagrangian where the tools are Eulerian grid; Gaea/WM algorithms are proprietary; SDF-primitive
placement is the academic route). Grounded in the construction-tree literature: Génévaux et al. 2013 /
2015, Guérin et al. 2016, Galin et al. 2019.

Two files, both deliberately small:

- **`graph_demo.py`** — a scale model of the substrate in `14-graph-runtime.md`: nodes are
  pure `fn(params, inputs, ctx)` functions with a declared locality
  (LOCAL / NEIGHBOURHOOD / GLOBAL) and preview class, edges are world-space fields, and the
  DAG is **content-addressed cached** (change one node, only its downstream cone recomputes —
  that is what makes it usable for iteration). The sample pipeline walks the **Legal Order**:
  fBm noise → fluvial erosion (droplet < 2 km, stream power > 50 km, per the design
  procedure) → thermal *after* hydraulic → depression fill → drainage area → slope → masks →
  materials → scatter, with all analysis computed on the **final** geometry. It prints the `09`
  checks it should pass (trunk drainage exits at the edge; slope capped at the repose angle; the
  erosion budget).
- **`render.py`** — the `09` "visual review modes" as pure-numpy functions returning RGB
  arrays, plus a zero-dependency PNG writer: greyscale height, hillshade, slope shade,
  `log(A)` flow overlay, hypsometric tint, a false-colour clip that flags NaN/Inf, a
  material splatmap (partitioned `06` masks blended by weight), a boulder scatter overlay, a
  **SatMap** CLUT (`satmap`: an elevation-driven curated colour gradient, à la Gaea's SatMaps —
  a toolbox node) + `splat_blend` compositor, and the **photoreal composite** (`sun_sky_shade` +
  `photoreal`: material colour × sun+sky × ambient occlusion + rivers + aerial perspective — Stage 1
  of `HYPERREALISM.md`, the render behind both montages). The montages colour by **substance**
  (`analysis.derive_substances` — snow/rock/scree/sediment/vegetation placed by physics, coloured by
  material) rather than by elevation, and those substances **pile up and fill crevices**
  (`analysis.deposit_fill`) into a surface smoother than the bedrock. Import it directly to render any
  heightfield from the modules.

The base node normalises the chosen `01` noise family to [0,1] for the demo, but the noise
itself is the verified `noise.py` module (noise is the initial condition, not the answer).
Everything downstream is a thin adapter over the verified modules; `tests/test_graph_demo.py`
checks the wiring, the cache, and the `09` invariants. For a by-eye pass over **every**
algorithm on one shared base — the visual complement to the oracles, with a numeric range trace
that catches blow-ups the normalised renders hide — run `python gallery.py` (see `GALLERY.md`).
For
where each node comes from — reference library, pinned revision, licence, grounding state and
which cross-check covers it — see **`GROUNDING.md`**. For how far these tiles could be pushed
toward photoreal — the shared render pipeline (Stage 1, now driving both montages), the
per-archetype geomorphology each landform still needs, and where the numpy sandbox honestly tops
out — see **`HYPERREALISM.md`**. For whether each *simulation* is best-in-class — a per-process SOTA
scorecard (ours vs Gaea/WM/Houdini vs the academic frontier), the objective realism metrics that tell
you, and the prioritised gaps — see **`SIMULATION-AUDIT.md`**.

## Coverage boundary and production paths

- **These modules are executable specifications, not production dependencies.** Port the
  paper-derived contracts and `09` oracles into the engine's own C++, Rust, C#, HLSL or compute
  stack. Landlab, fastscapelib, RichDEM and pysheds are useful independent comparison targets when
  project policy permits test-only dependencies; **RichDEM, pysheds and Landlab are wired** as
  cross-validation here (fastscapelib is not) — RichDEM/pysheds for the flow ops
  (`tests/test_crossvalidate.py`) and Landlab (MIT) for stream power, D8 accumulation and hillslope
  diffusion (`tests/test_crossvalidate_landlab.py`). See `GROUNDING.md` for the node-by-node map.
- **D-infinity** (Tarboton 1997) — implement from the paper when needed. The D8/MFD pair here
  demonstrates the single-receiver-artefact vs dispersive contrast and supplies shared fixtures.
- **The pipe sediment/erosion coupling** — the water solver (where the documented NaN failure
  lives) is the verified core; implement the transport-capacity + semi-Lagrangian advection layer
  from `04` and validate mass conservation before moving it to the GPU.
- **The un-oracled sims** (coastal cliff retreat, tides, the lava CA, the transient SIA glacier)
  have **no decisive deterministic oracle** — so they live in `sims_illustrative.py`, segregated
  and held only to *invariants* (finite, mass/energy budget, monotone trends). They are sketches
  you can run and watch, **not** verified numbers; validate against real morphometry before any
  use. **Learned / ML synthesis** stays out entirely (frontier, unstable metadata).
