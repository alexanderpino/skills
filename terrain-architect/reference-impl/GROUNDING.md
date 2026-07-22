# Sandbox grounding & provenance

Where each node in the graph demo comes from, what tested library it is grounded in, under
what licence, and which check compares it to that library. This is the sandbox-scoped view
of the skill's full ledger in `references/22-open-source-grounding.md` (machine-readable:
`references/open-source-grounding.json`) — read that for the exact adopted behaviour,
deliberate deviations and engine-native translations. Revisions below are the pinned
upstreams inspected 2026-07-20.

**Grounding is not copying permission.** The licence column records what was *inspected and
compared against*, not a grant to paste code into a product. MIT / CC0 upstreams are safe
wells to lift from; the **GPL-3.0** ones (RichDEM, pysheds, fastscapelib) are fine to read
and diff against in test-only optional dependencies, but copying their code into a
permissively-licensed engine is a licence event. Reuse follows *your* project policy.

## Grounding states

Same scale as `references/22-open-source-grounding.md`:

- **cross-validated** — the module is compared *by test* against an independent library's output.
- **source-grounded** — an upstream revision was inspected and its behaviour adopted, but no
  library is wired as a running comparison (often because the reference is a GPU/engine project
  with no importable Python).
- **skill-stricter** — public implementations exist, but the skill deliberately adopts a
  stronger invariant than the inspected one.
- **demo-only** — a stand-in for illustration, not a verified mirror of any reference chapter.

## The graph-demo nodes

| Sandbox node | Module | Reference library @ rev | Licence | Grounding | Compared by |
|---|---|---|---|---|---|
| `base` (noise) | `noise.py` | Perlin 2002 · Musgrave · Bridson 2007 · Worley 1996 (OpenSimplex2 `4cd120d3` · FastNoiseLite `785f37a9` for the API/variants) | papers; CC0 · MIT | **paper-grounded** (analytic oracles: lattice-zero, zero-divergence, single-octave identity) | `test_noise.py` |
| `fluvial` (droplet) | `erosion_droplet.py` | SebLague/Hydraulic-Erosion `f245576d` | MIT | **source-grounded** | `09` oracles (`test_droplet.py`) |
| `fluvial` (stream power) | `erosion_streampower.py` | **Landlab** FastscapeEroder `0b0ef086` · fastscapelib `b85cc6b1` | **MIT** · GPL-3.0 | **cross-validated** | `test_crossvalidate_landlab.py::test_streampower_slope_area_exponent_matches_landlab` |
| `relaxed` (thermal) | `erosion_thermal.py` | bshishov/UnityTerrainErosionGPU `0e59f7c4` | MIT | **skill-stricter** (8-neighbour distance-correct; upstream 4-dir bug not ported) | `09` radial-anisotropy oracle (`test_thermal.py`) |
| `filled` (fill) | `flow.py` | **RichDEM** FillDepressions `9a1c97bb` | GPL-3.0 | **cross-validated** | `test_crossvalidate.py::test_priority_flood_matches_richdem` |
| `area` (D8 accumulation) | `flow.py` | **pysheds** `1949ce1d` · **Landlab** FlowAccumulator `0b0ef086` | GPL-3.0 · MIT | **cross-validated** | `test_crossvalidate.py::test_d8_accumulation_matches_pysheds` · `test_crossvalidate_landlab.py::test_d8_accumulation_matches_landlab` |
| `slope`, `materials` (analysis/masks) | `analysis.py` | Zevenbergen & Thorne 1987 · Beven & Kirkby 1979 (GDAL/GRASS implement the same) | papers | **paper-grounded** (analytic oracles) | `test_analysis.py` |
| `scatter` (boulders) | `scatter.py` | Bridson 2007 (tph_poisson `e436117b` for grid/active-list hardening) | paper; MIT | **paper-grounded** (min-distance oracle) | `test_scatter.py` |

Adjacent module the sandbox can wire (a drop-in extra hillslope node), cross-validated too:

| Module | Reference library @ rev | Licence | Grounding | Compared by |
|---|---|---|---|---|
| `diffusion.py` (Culling) | **Landlab** LinearDiffuser `0b0ef086` | **MIT** | **cross-validated** | `test_crossvalidate_landlab.py::test_hillslope_diffusion_matches_landlab` |

The **render modes** (`render.py`) are standard cartographic transforms (hillshade, slope
shade, `log(A)` overlay); the usual references are GDAL / RichDEM / matplotlib hillshade.
They modify no terrain and carry no pinned upstream — sanity-check the hillshade against
GDAL's if it matters.

The **toolbox** (`ops_filters.py` — SDF primitives, smooth min/max, Gaussian/median/bilateral/
guided/Perona–Malik filters, morphology, warps) is drawn on ad hoc rather than wired as a fixed
graph node. **paper-grounded** (Frisken 2000, Quilez, Tomasi & Manduchi 1998, He et al. 2010,
Perona & Malik 1990, Serra 1982) with property oracles in `test_ops_filters.py`.

The **geological landforms** (`landforms.py` — impact craters, strata/terracing, folding,
karst sinkholes) are likewise a toolbox, not a fixed node. **paper-grounded** (Pike 1977,
Melosh 1989; Beneš & Forsbach 2001 strata; Ford & Williams 2007 karst) with oracles in
`test_landforms.py`. Landforms without a standalone deterministic oracle — salt diapirs, tower
karst, relief inversion — stay as reference pseudocode, not code here.

The **illustrative sims** (`sims_illustrative.py` — lava CA, SIA glacier, coastal retreat,
tides) sit at a distinct, weaker tier: **invariant-checked only, NOT cross-validated or
oracle-verified.** These are the regimes the coverage boundary excludes because they have no
decisive oracle; they are included to run, held to invariants (finite, mass/energy budget,
monotone trends) in `test_sims_illustrative.py`, and must not be read as verified numbers. This
tier is deliberately outside the grounding scale above.

## What the cross-checks assert

Comparisons are on **physical signatures**, not raw fields — grid conventions and boundary
handling differ between any two implementations, so equality is the wrong bar:

- **Stream power** — both our Braun–Willett solver and Landlab's FastscapeEroder must recover
  the steady-state slope–area exponent `-m/n` (the decisive `09` oracle), and agree to <0.1.
- **D8 accumulation** — our drainage area correlates >0.9 with Landlab's (and with pysheds').
- **Hillslope diffusion** — a single Fourier mode decays by the same factor under our explicit
  Culling step and Landlab's LinearDiffuser (both match the analytic decay).

Run them with `pip install -r requirements-crossvalidate.txt && pytest -q`; without those
optional libraries the checks skip and the numpy-only core suite still runs green.

## Nodes with no wired library comparison

Droplet and thermal are **source-grounded** but not cross-validated here: their canonical
references are GPU/engine projects (SebLague, the Unity pipe/thermal) with no importable
Python to diff against, and the skill deliberately runs *stricter* than the inspected thermal
(distance-correct 8-neighbour vs the upstream's 4-directional non-square-cell bug). They are
held to their `09` oracles instead — determinism, mass conservation, and radial isotropy on a
cone. If you port either to a new engine, re-ground against the pinned revision and keep the
deviations in `references/22-open-source-grounding.md` beside the code.
