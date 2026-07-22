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
pytest -q                            # 60 pass; 2 optional cross-checks skip

# optional: cross-validate against mature libraries (RichDEM, pysheds).
pip install -r requirements-crossvalidate.txt
pytest -q                            # the 2 cross-checks now run instead of skipping
```

## What's here, and how each is verified

The verification design is **layered**: use the strongest oracle available per algorithm —
a closed-form value where one exists, otherwise `09`'s invariants (determinism, no NaN, mass
conservation, radial symmetry) and quantitative signatures, plus an optional cross-check
against an independent library.

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
| `erosion_pipe.py` — virtual-pipe water | `04` Mei et al. 2007 | depth ≥ 0 (step-3 scaling) & finite on steep terrain; water conserved; 8-pipe more radial than 4-pipe |
| `erosion_streampower.py` — stream power | `04` Braun & Willett 2013; Cordonnier 2016 | **slope–area exponent = −m/n** at steady state |
| `dunes.py` — Werner slab CA | `05` Werner 1995 | slabs conserved; instability (`p_sand>p_bare`) sweeps ground bare; deterministic |
| `winds.py` — mass-consistent wind | `13` Sherman 1978 | corrected field's divergence → 0 (Helmholtz–Hodge projection); solenoidal field passes through |
| `runout.py` — Voellmy runout | `05` Voellmy 1955 | runout length on a ramp matches `L = H/tan(α)`; more friction → shorter |

## Sandbox: run a graph and look at it

The modules above are *nodes*; `graph_demo.py` is a tiny sandbox that wires them into a
**terrain graph** you can run and render — the place to drop a new algorithm in during
development and actually see what it does. It has no dependencies beyond the numpy the rest
of `reference-impl` already needs.

```bash
python graph_demo.py                          # droplet backbone, 96² -> six PNGs in out/
python graph_demo.py --backbone streampower --size 128 --extent-km 120
python graph_demo.py --seed 7 --sun-sweep 8   # rotating-light frames (09's sun sweep)
python graph_demo.py --cache-demo             # watch the content-addressed cache
```

Two files, both deliberately small:

- **`graph_demo.py`** — a scale model of the substrate in `14-graph-runtime.md`: nodes are
  pure `fn(params, inputs, ctx)` functions with a declared locality
  (LOCAL / NEIGHBOURHOOD / GLOBAL) and preview class, edges are world-space fields, and the
  DAG is **content-addressed cached** (change one node, only its downstream cone recomputes —
  that is what makes it usable for iteration). The sample pipeline walks the **Legal Order**:
  fBm noise → fluvial erosion (droplet < 2 km, stream power > 50 km, per the design
  procedure) → thermal *after* hydraulic → depression fill → drainage area, with the analysis
  computed on the **final** geometry. It prints the `09` checks it should pass (trunk drainage
  exits at the edge; slope capped at the repose angle; the erosion budget).
- **`render.py`** — the `09` "visual review modes" as pure-numpy functions returning RGB
  arrays, plus a zero-dependency PNG writer: greyscale height, hillshade, slope shade,
  `log(A)` flow overlay, hypsometric tint, and a false-colour clip that flags NaN/Inf. Import
  it directly to render any heightfield from the other modules.

The fBm noise base is a **demo initial condition**, not a verified `01` mirror (noise is the
initial condition, not the answer). Everything downstream is a thin adapter over the verified
modules; `tests/test_graph_demo.py` checks the wiring, the cache, and the `09` invariants.

## Coverage boundary and production paths

- **These modules are executable specifications, not production dependencies.** Port the
  paper-derived contracts and `09` oracles into the engine's own C++, Rust, C#, HLSL or compute
  stack. Landlab, fastscapelib, RichDEM and pysheds are useful independent comparison targets when
  project policy permits test-only dependencies; only RichDEM and pysheds are wired here.
- **D-infinity** (Tarboton 1997) — implement from the paper when needed. The D8/MFD pair here
  demonstrates the single-receiver-artefact vs dispersive contrast and supplies shared fixtures.
- **The pipe sediment/erosion coupling** — the water solver (where the documented NaN failure
  lives) is the verified core; implement the transport-capacity + semi-Lagrangian advection layer
  from `04` and validate mass conservation before moving it to the GPU.
- **"Look, not a sim" processes** (coastal cliff/longshore, tides), the full MAGFLOW lava CA,
  the transient SIA glacier, and learned/ML synthesis are **excluded** — they have no decisive
  deterministic oracle, so they stay as paper-derived pseudocode and verification requirements
  rather than being presented here as complete code.
