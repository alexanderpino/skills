# Canon Comparison — every atom vs its canonical online counterpart

A verification rung that complements the numeric benchmarks (Halfar, Landlab, RichDEM, Pike,
Hack's law): put each atom's render **side-by-side with a canonical online example** and judge it.
Two canon classes, both used:

1. **Algorithm canon** — a published output of the *same algorithm* (a paper figure, a reference
   implementation's render, the author's own article image). The strictest visual check: same math,
   same top-down presentation.
2. **Landform canon** — real imagery of the landform the atom models (satellite/aerial, mostly
   Wikimedia Commons; NASA imagery is public domain). Judged at the skill's stated **node-level
   parity** bar (does it reproduce the *kind* of landform), the same bar as Gaea / World Machine /
   Houdini.

How to refresh: fetch the canon listed below (Commons API search → `Special:FilePath`/thumburl;
raw README images for the reference repos), render the matching tile from `capability_grid.py`,
and compare. Two review rounds + one algorithm round were run in 2026-07; verdicts below.

## Research-paper figure canon (the strictest: the figure from the paper we cite)

The most defensible comparison — our render beside the actual figure in the grounding publication
(figures not redistributed here; fetch the open-access PDFs below and extract with any PDF tool).

| Atom | Paper + figure | Verdict |
|---|---|---|
| `erosion_streampower` / Mountain(eroded) / Differential erosion | **Cordonnier et al. 2016**, *Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion* (CGF; open PDF at cs.purdue.edu/cgvlab, hal.inria.fr) — the top-down eroded-terrain + drainage-network figures | ✅ **same algorithm** (stream-power incision, Braun–Willett solver — which our `tests/test_crossvalidate_landlab.py` also validates numerically): same dendritic branching drainage incised into the massif. Honest deltas: theirs is higher-res and more mature (smoother trunk valleys, larger domain); ours is grainier at 96–180 px; our differential-erosion tile is the *anisotropic* tilted-K case (strike ridges), so it reads structural by design, not isotropic like their figure |
| `aeolian.yardang` | **Kok et al. 2012**, *The physics of wind-blown sand and dust* (Rep. Prog. Phys.; arXiv 1201.4353), yardang-field panels | ✅ ours matches the **mega-yardang lineation** panel (parallel wind-aligned ridges, ~50 km scale); the discrete 1:4 **teardrop/whaleback** yardangs (individual-scale panels) are the documented open gap (follow-up 5) |
| `aeolian.yardang` bottom-weighted abrasion | Kok et al. 2012, saltation-trajectory plots (height vs distance, by grain size) | ✅ grounds the `saltation_h` weighting: hop heights are a few cm, concentrated LOW — exactly the bottom-weighted (undercut) abrasion the atom applies |

Not obtained (paywalled / no open figure): Werner 1995 (Geology), Blair & McPherson 1994, Braun &
Willett 2013 originals, Argudo 2020 thesis — the algorithm itself is still grounded (constants
audited in `99-papers.md`) and, for stream power and SIA, numerically cross-validated in the suite.

## Algorithm canon (same algorithm, published output)

| Atom | Canon | Verdict |
|---|---|---|
| `noise.perlin` / fBm | Wikipedia/Commons "Perlin noise" sample; published fBm surface plots | ✅ same isotropic lattice-free character (ours shown as multi-octave fBm hillshade) |
| `noise.worley` | Commons Worley/Voronoi renders | ✅ same cellular web (variant/colormap differ: ours F2−F1) |
| `noise.domain_warp` | **Quilez, iquilezles.org/articles/warp** (his own render) | ✅ after fix: low base frequency + value render shows the signature large marble swirls (tile previously read as high-frequency chop — same algorithm, wrong showcase) |
| `ops_filters.smin` | Quilez articles/smin figures | ✅ smooth crease-free union (his figures demo it on models; ours on two shapes) |
| `scatter.poisson_disk` | Commons Poisson-disk diagrams | ✅ same blue-noise spacing with exclusion radii |
| `capability_grid.lic` (flow-vis) | Cabral & Leedom-style classic LIC images | ✅ indistinguishable technique |
| `flow.d8_accumulation` | GIS flow-accumulation maps | ✅ dendritic converging web. Honest note: long lattice-straight trunks are **D8's documented 8-direction bias** — the reason MFD exists (and our MFD tile shows the softer version) |
| `analysis.twi` | published TWI maps | ✅ wet dendritic valley floors, dry ridges |
| `erosion_droplet` | Sebastian Lague's Hydraulic-Erosion renders | ✅ same converging gully character (ours grainier at tile resolution) |
| `dunes.werner_dunes` | Werner-CA reference repos' output heightmaps (e.g. LEMettler/sand-dunes) | ✅ same transverse wave pattern; ours shows more swept-bare interdune floor (supply/p_bare differences) |
| `shallow_water.simulate` | SWE dam-break paper panels | ⚠️ same equations, different scenario (ours: rain ponding on a volcano) — algorithm canon is the mass-budget test, not the picture |
| `sims.glacier_sia` | **Halfar analytic solution** (also plotted in PISM docs) | ✅ the tile *is* the Halfar dome; profile verified to ~1% in tests |
| `erosion_streampower` | Landlab SPL outputs | ✅ cross-validated numerically (tests); visually shows slight lattice grain inherent to D8-receiver solvers at 96px |

## Landform canon (real imagery, node-level bar)

| Atom / tile | Canon | Verdict |
|---|---|---|
| Volcano (strato) | Mt Fuji satellite (straight down) | ✅ **best match of the set**: radial barrancos, summit crater, concave sweep |
| Dunes (full Werner) | Rub' al Khali, Terra/ASTER (NASA, PD) | ✅ sinuous barchanoid-transverse ridges ⊥ wind, bare corridors, Y-junctions |
| Snowpack | Tuckerman Ravine | ✅ snowfields on gentle ground, bare steep faces, gullies filled |
| Differential erosion (spatial-K) | cuesta escarpments (aerial) | ✅ structure-controlled strike ridges |
| Meander belt | oxbow river aerial | ✅ loops/point bars/oxbow; seed is now a **disturbed periodic** (Ferguson 1975: fbm-perturbed wavelength + amplitude) → irregular varying-size loops, not a uniform sine train |
| Glacial carve | Arrigetch U-valley | ✅ trunk ice in sinuous valleys; U cross-section is test-verified (V→U metric) |
| Ridge (hogback) | Dakota Hogback | ✅ linear asymmetric crest, wandering strike |
| Canyon | Grand Canyon | ✅ plateau-dominant meandering slot with benches |
| Impact crater | Meteor Crater aerial | ✅ numerics are the canon (Pike/Melosh tested); ⚠️ analytic bowl hillshades glassy — real rims are ragged (accepted: minimal primitive) |
| Yardangs | Qaidam yardangs / Lut mega-yardangs | ⚠️ ours = Lut-style parallel lineation; discrete 1:4 teardrop hulls (Ward & Greeley) are a gap |
| Alluvial fans (bajada) | Death Valley bajada aerial | ⚠️ deposition correct (tested) but cone convexity barely legible; apex stamps read as spikes |
| Lava CA | channelised ʻaʻā tongue | ✅ Bingham tongue + steep snout (exists only because heat is advected, per SCIARA); levées absent (needs margin-vs-core cooling asymmetry — documented in `19`) |
| Volcano (shield) | Mauna Loa | ✅ after fix: young shields are barely gullied → barranco amplitude at the atom default (my 0.30 override over-dissected it) |
| Mountain (eroded) | Grand Teton / alpine aerials | ✅ organised ridge-valley fabric |
| Fault-block butte | Monument Valley | ✅ now **isolated + size-varied** flat-topped blocks (sharper corners, jaggier joint faces). Vertical cliff **fluting** is an oblique-view feature — invisible top-down — so it's deferred to the 3D/oblique render, not a top-down gap |
| Fault scarps | Basin & Range satellite | ✅ now **sharp range-front traces** (feather 6→2.5, quieter base, dominant first fault) cutting the terrain into blocks — Stewart 1978 range-bounding normal faults |
| Karst sinkholes | doline imagery | ✅ dolines now carry a **lognormal size distribution** (`size_var`; Williams 1972) instead of one radius |
| Coastal retreat | sea cliff + wave-cut platform | ⚠️ platform/cliff correct but washes out in hillshade |
| Plate uplift | world hypsometry (ETOPO-style) | ✅ continents/oceans/orogens at convergent margins; orogen belts thinner than Earth's, interiors featureless |
| Thermal (talus) | scree below crags | ✅ minimal cone-at-repose demo (a talus cone genuinely is a smooth cone); the crag-and-apron scene is a composition, not the atom |
| Hillslope diffusion | rolling soil-mantled downs | ✅ (landform form; the tile's impulse→Gaussian is the Green's-function canon) |
| Substances (splatmap) | Mt Fuji zonation (snow/rock/forest) | ✅ elevation-and-aspect zonation matches |
| SatMap (`extract_satmap`) | the NASA Terra image itself | ✅ by construction: the ramp is extracted from the canon (gamut ⊆ source, luminance-monotone, tested) |

Canon fetches that failed (book covers/documents, not comparisons): pipe-erosion gully systems and
river terraces — both share family canon above (badlands / canyon benches) and have numeric oracles.

## Standing follow-ups the comparison surfaced

Done (2026-07):
1. ✅ Basin & Range-crisp fault scarps — sharp feather + dominant range-front fault (Stewart 1978).
2. ◑ Butte isolation + varied footprints (done); **fluted cliffs** deferred to oblique/3D render.
3. ✅ Karst radius/depth variation — lognormal `size_var` (Williams 1972), atom + oracle.
4. ✅ Meander irregularity — disturbed-periodic seed (Ferguson 1975).

Open:
5. Discrete teardrop yardang hulls (Ward & Greeley 1:4) alongside the lineation field — a new
   landform representation, not a parameter (would need its own atom + oracle).
6. Lava levées via margin-vs-core cooling asymmetry (documented in `19`, unimplemented) — a sim
   change to `lava_flow` (freeze margins faster than the core so walls emerge and the flow channelises).
7. Alluvial-fan cone convexity legibility; butte cliff fluting (needs oblique render, item 2).
