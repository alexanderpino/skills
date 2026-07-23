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
GDAL's if it matters. The **photoreal composite** (`sun_sky_shade` + `photoreal`: material
colour × two-light (sun+sky) × ambient occlusion + rivers + aerial perspective) is
**paper-grounded** in the standard real-time / cartographic pipeline: slope+altitude material
splatting (Andersson/DICE, *Terrain Rendering in Frostbite Using Procedural Shader Splatting*,
SIGGRAPH 2007); **horizon-based ambient occlusion computed on the height field itself** — Max
1988, *Horizon mapping* (The Visual Computer 4(2)), the geometry-native method, not screen-space
HBAO; and sky illumination + aerial perspective (Preetham et al. 1999; Bruneton & Neyret 2008).
It is a *look*, not a verified field (a non-flat-render smoke test only).

The **toolbox** (`ops_filters.py` — SDF primitives incl. `sd_convex_polygon`, smooth min/max,
Gaussian/median/bilateral/guided/Perona–Malik filters, morphology, warps) is drawn on ad hoc
rather than wired as a fixed graph node. **paper-grounded** (Frisken 2000, Quilez SDF & smooth-min,
Tomasi & Manduchi 1998, He et al. 2010, Perona & Malik 1990, Serra 1982) with property oracles in
`test_ops_filters.py`. `sd_convex_polygon` (a block as the intersection of half-planes) is the
generalisation of `sd_box` and the primitive behind the fault-block landform below.

The **geological landforms** (`landforms.py` — impact craters, strata/terracing, folding,
karst sinkholes, **`fault_block_butte`**) are likewise a toolbox, not a fixed node. **paper-grounded**
(Pike 1977, Melosh 1989; Beneš & Forsbach 2001 strata; Ford & Williams 2007 karst) with oracles in
`test_landforms.py`. `fault_block_butte` is a **feature-primitive construction-tree** node in the
Génévaux et al. 2015 (*Terrain Modelling from Feature Primitives*, CGF) / Guérin et al. 2016 (*Sparse
representation of terrains*, CGF) sense — a placeable SDF primitive (`ops_filters.sd_convex_polygon`)
combined by union and eroded — with its **joint/fault-controlled outline grounded in geomorphology**
(NPS Arches/Canyonlands *The Needles*; Li et al. 2021 orthogonal joints in quartz sandstone; Narr &
Suppe 1991 joint spacing; Wadi Rum sandstone geomorphology). Verified by profile oracles (flat top,
cliff, talus break, bounded footprint), not a physical simulation. Landforms without a standalone
deterministic oracle — salt diapirs, tower karst, relief inversion — stay as reference pseudocode.

The **parameterised impact** (`crater.py` — asteroid size/speed/density/gravity/angle → crater)
is two tiers: the **size** physics is **paper-grounded** with *decisive* oracles (Collins/Melosh/
Marcus 2005 π-scaling exponents — `L^0.78 v^0.44 g^(−0.22) (sinθ)^(1/3)` — and the 1/g transition,
verified in `test_crater.py`); the **shape under obliquity** (elongation, downrange/butterfly
ejecta) is **phenomenological**, matched to the oblique-impact experiments (Gault & Wedekind 1978;
Pierazzo & Melosh 2000; Collins et al. 2011), not a ballistic-ejecta simulation — though the ejecta
placement is held to a **mass-conservation invariant** (the excavated bowl volume is what the
blanket redeposits, so mass is *pushed forward*, not conjured; `test_ejecta_conserves_excavated_mass`).
The `crater_demo.py` `stamp_impact_natural` render (smooth circular cavity + raised rim ring,
irregular rim/ejecta outline, terraced walls, defined central massif, hummocky downrange ejecta
apron, grazing furrow deeper up-range) and the labelled `crater_anatomy.py` figure are **demo-only**
presentation — they dress the verified
`crater.py` skeleton with `noise.py` (01) detail for a hillshaded *look* and is deliberately outside
the grounding scale (not mass-conserving, not oracle-verified; only a determinism/texture smoke test).

The **illustrative sims** (`sims_illustrative.py` — lava CA, SIA glacier, coastal retreat,
tides) sit at a distinct, weaker tier: **invariant-checked only, NOT cross-validated or
oracle-verified.** These are the regimes the coverage boundary excludes because they have no
decisive oracle; they are included to run, held to invariants (finite, mass/energy budget,
monotone trends) in `test_sims_illustrative.py`, and must not be read as verified numbers. This
tier is deliberately outside the grounding scale above.

## How this maps to Gaea / World Machine / Houdini (node-graph parity)

The sandbox is the **same paradigm** these tools use: a DAG of pure field→field operators over a
heightfield, evaluated on demand (`graph_demo.py`; run `--scene mesa` to see an archetype built as a
DAG — noise → fault-block primitive → strata → thermal → flow/materials → photoreal). Gaea, World
Machine and Houdini heightfields are all confirmed node graphs with the workflow *Create → Modify →
Erode → Texture → Export*; the academic framing is the **construction tree** of Génévaux et al. 2013
(*Terrain from Hydrology*, SIGGRAPH) and 2015 (*Feature Primitives*, CGF), Guérin et al. 2016 (*Sparse
representation*, CGF), and the Galin et al. 2019 review (*A Review of Digital Terrain Modeling*, CGF).
Every effect we add is one of their node categories, grounded in the same literature:

| Node category | Our node(s) | Grounded in | How the pro tools do it |
|---|---|---|---|
| Generator | `noise` (Perlin/value/Worley/fBm/ridged) | Perlin 2002, Musgrave, Worley 1996 | noise/shape generators |
| Warp | `noise.domain_warp`, `ops_filters` twist/bend | Quilez *domain warping*; Musgrave | Warp/Perturb/Distort |
| Combiner | `ops_filters.smin/smax/blend`, `np.maximum` union | Quilez *smooth minimum*; Génévaux 2015 (Lipschitz operators) | Combine/Layer/math |
| Primitive placement | `landforms.fault_block_butte` (`sd_convex_polygon`) | Génévaux 2015 / Guérin 2016 feature-primitive tree; Quilez SDF | masks + project (academic: SDF primitives) |
| Erosion (hydraulic) | `erosion_droplet`, `erosion_streampower` | Krištof 2009, Chiba 1998, Beyer 2015 (droplet); Braun & Willett 2013 (stream power) | Erode/Hydro |
| Erosion (thermal) | `erosion_thermal` | **Musgrave, Kolb & Mace 1989** (angle-of-repose talus) | Thermal/Talus/Slump |
| Selector / mask | `analysis` slope/curvature/**horizon AO**/TWI/area | Zevenbergen & Thorne 1987; Max 1988 (AO) | Slope/Height/Flow masks |
| Colorizer / splat | `analysis.derive_substances` + `material_rgb` (default); `render.satmap`/`splat_blend` (toolbox); `photoreal` | **Andersson/Frostbite 2007** splat; **substance placement** by slope/aspect/curvature/flow | splatmap masks (SatMap CLUT also available) |

**Honest divergences (disclosed, not hidden):**

- **Hydraulic erosion is Lagrangian here, Eulerian there.** Our droplet model (particle over the
  heightfield) is literature-grounded — Krištof et al. 2009 (*Hydraulic Erosion Using SPH*, CGF, the
  peer-reviewed bridge showing particle ≈ grid physics) and Chiba et al. 1998 (velocity-field erosion);
  Beyer 2015 is the practical recipe but only a BSc thesis, so the *authority* is Krištof/Chiba. The
  pro tools use **Eulerian grid / virtual-pipe** erosion (Houdini confirmed; Mei et al. 2007 is the
  canonical model). We also ship a **grid fluvial path** (`erosion_streampower`, cross-validated vs
  Landlab) for the broad-valley regime, so both discretisations are represented — but a droplet result
  is a *known approximation* of the tools' grid erosion, best at fine dendritic channels.
- **Gaea and World Machine erosion algorithms are proprietary/undisclosed** — we can claim *node-level*
  parity (same category, same phenomenology, same repose-angle thermal) but **not algorithm-level
  parity**. Only Houdini's grid approach is documented.
- **SDF-primitive placement is the academic route.** `fault_block_butte` follows Génévaux/Guérin
  (place a primitive, combine, erode); the tools' *default* idiom is generators + selection masks +
  erosion. Both are valid; we do not claim primitive placement is how the tools default to it.
- **Hard-`max` union creases.** We union plateau blocks with `np.maximum` (the acceptable cliff/plateau
  case) and relax the seam with thermal downstream; `ops_filters.smax` is the crease-free (Lipschitz)
  combiner for general merges.
- **Colour is by SUBSTANCE, not by elevation.** The default tile colouriser is
  `analysis.derive_substances`: each cell is coloured by the *material* on it, and each material is
  placed where it physically accumulates — **snow** where it is cold enough (a lapse-rate temperature ∝
  elevation) AND the slope holds it AND wind loads it (poleward/shaded aspects + concave hollows collect,
  steep faces and convex ridges shed/scour); **rock** where the slope is too steep for anything to rest;
  **scree** at the repose angle below cliffs; **sediment** where flow deposits on gentle, concave lows;
  **vegetation** on gentle ground below the snowline (arid biomes have none). So snow is white because
  snow is *a white substance*, not because "high == white" — the snowline is an irregular, aspect- and
  shelter-dependent surface, not a contour. The per-material blend is the Frostbite-2007 splat; the
  elevation-gradient **SatMap** (`render.satmap`) stays as a toolbox node but is no longer the tile base.
  Still simpler than the pro tools' full Flow/Wear/Deposits layer set, but now materially honest.
- **Content-addressed caching** (Merkle key over params + upstream cone) is *our* mechanism — consistent
  with how these tools cache cooked nodes, but an implementation choice, not a documented parity claim.

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
