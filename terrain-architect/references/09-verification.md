# Verification

Terrain is judged by eye, which makes it uniquely vulnerable to **plausible wrongness**: a
result that looks fine in a hillshade and is structurally broken. The whole point of this file
is that a handful of cheap, quantitative checks catch things that no amount of looking will.

Contents: [Validation suite](#validation-suite) · [The five checks](#the-five-checks) ·
[Visual review modes](#visual-review-modes) · [Failure catalogue](#failure-catalogue) ·
[Review checklist](#review-checklist)

## Validation suite

Before the visual checks, run every node against synthetic inputs whose correct output you can
state in advance. This is the difference between "looks plausible" and "is correct", and it is
cheap — these are a dozen lines of setup each.

**Canonical test inputs.** Each one is chosen because it breaks a specific class of node:

| Input | Catches |
|---|---|
| **Flat plane** | Division by zero in slope/TWI; erosion that creates relief from nothing; NaN from `atan2(0,0)` |
| **Constant slope** | Flow routing that doesn't route; D8 diagonal bias; erosion that doesn't incise |
| **Cone** | Radial symmetry — output must stay radially symmetric. Catches the thermal per-neighbour distance bug (`05`) instantly: you get a plus shape. |
| **Inverted cone** | A single pit. Depression handling must resolve it. |
| **Ridge / valley** | Sign conventions in curvature and aspect |
| **Step** | Edge-preserving filters (bilateral, guided) must keep it; Gaussian must not |
| **Terrace** | Quantisation artefacts; derivative combs |
| **Closed basin** | Fill vs breach policy; must not leak |
| **Basin with a spill point** | Priority-Flood correctness — flow must exit via the spill, not the lowest rim cell |
| **Two connected basins** | Lake graph / spill cascade. The classic case that naive filling gets wrong. |
| **Plateau** | Flat resolution — epsilon fill; catches the parallel-lines artefact |
| **Coastline** | Sea-level flood fill vs threshold (`03`) |
| **Cross-tile river** | Tiling. A river authored to cross a tile boundary must arrive with the same `A` on both sides. |
| **Extreme height range** (0–20 km) | Precision. R16 terracing shows up here and nowhere else. |
| **One-pixel spike** | Median/despike; erosion stability; capacity singularities |
| **One-pixel pit** | Depression handling; the `?` case where breach and fill disagree |

**Invariants to assert.** These are machine-checkable and they belong in CI, not in an artist's
eyeballs:

| Invariant | How |
|---|---|
| **Determinism** | Run twice, same seed → bit-identical. Then run threaded → still bit-identical. This is the double-buffering check (`04`, `05`) and it fails loudly. |
| **No NaN / Inf** | Assert after every sim step, not at the end. The step that first produces NaN is the bug; by the end it's spread. |
| **No invalid negatives** | `waterDepth ≥ 0`, `sediment ≥ 0`, `A ≥ cellArea`. Negative water is the missing pipe-model scaling factor (`04`). |
| **Mass conservation** | Where applicable: `Σ(bedrock + sediment)` constant under pure transport (no uplift, no sources). Erosion models leak mass at boundaries and at every clamp; measure the leak and know it. **This is the single most under-used terrain assertion.** |
| **Tile continuity** | Height, normals, and `A` match across a shared edge to within float epsilon |
| **Monolithic vs tiled equivalence** | Run the graph whole; run it tiled; diff. Should be ~0 for local ops, provably non-zero for stream power (`08`) — **and knowing which is which is the point of the test.** |
| **CPU/GPU tolerance** | Same graph both paths, diff within tolerance. Establish the tolerance; don't discover it. |
| **Long-run stability** | 10× the intended iteration count. Should converge or plateau, not drift or explode. |
| **Resolution consistency** | Same world extent at 1k/2k/4k. Large-scale structure must match; only detail should differ. **If the mountains move, a parameter is in cells instead of metres** (`SKILL.md` invariants). |

The resolution-consistency test deserves emphasis: it is the cheapest possible detector of the
most pervasive defect in terrain graphs. Run it first.

## The five checks

Run these before declaring a terrain graph correct. Together they cost minutes and they catch
almost everything.

### 1. Flow accumulation render

Render `log(A)` as an image. This is the highest-value diagnostic in the whole pipeline.

**Must show:** a connected, branching, dendritic network; every channel reaching either the
domain edge or a lake; tributaries joining at acute angles pointing downstream.

**Diagnoses:**

| What you see | Cause |
|---|---|
| Scattered confetti, no connectivity | No depression handling (`03`) |
| Channels stop mid-slope | Unfilled pits |
| Parallel straight lines on hillslopes | D8 artefact — use D∞/MFD (`03`) |
| Everything at 45° | Missing diagonal distance weighting in D8 |
| Fan of lines radiating from filled basins | Filled without epsilon — flat surfaces have no direction |
| Network exists but doesn't match the visible valleys | Analysis ran before erosion, or you're rendering `A` from a stale DEM |

### 2. Slope histogram

Plot the distribution of `atan(slope)` in degrees.

**Must show:** after thermal erosion, a distribution that *ends* near the repose angle — a
soft peak at 30–40° and essentially nothing above 45° (unless you have authored rock faces).

**Diagnoses:**

- **A spike at 0°** — over-deposition, or the terrain is mostly flat and you have a masking
  problem, or filling replaced your terrain with plateaux.
- **A long tail past 60°** — thermal never ran, or ran before hydraulic, or the talus angle is
  wrong, or (very common) the per-neighbour distance correction is missing so diagonals were
  never relaxed.
- **A spike at exactly 90°** — NaN or Inf in the height field. Check the pipe model's scaling
  factor (`04`).
- **Bimodal with a gap** — usually a mask threshold has been applied to height somewhere it
  shouldn't have been.

### 3. Slope–area plot (stream power only, and it's decisive)

For channel cells (`A` above the channelisation threshold), plot `log(S)` against `log(A)`.

**Must show:** a straight line with slope `−m/n`. With the standard `m=0.5, n=1`, that's
**−0.5**.

This is a direct test of whether the stream power implementation is correct. It comes from the
equilibrium condition `U = K·A^m·S^n` → `S = (U/K)^(1/n) · A^(−m/n)`. If your line isn't
straight, or its slope isn't `−m/n`, the solver is wrong — most likely the stack ordering, or
you're traversing the stack backward.

Nothing about eyeballing a hillshade will ever catch a subtly wrong stream power solver. This
plot catches it in one look. It is the single best argument for the "compiler-as-oracle"
approach applied to terrain: find the measurement that makes the bug loud.

### 4. Long profile

Plot elevation against distance downstream along the main channel.

**Must show:** a **concave** profile — steep at the head, flattening toward the mouth. This is
one of the most robust observations in geomorphology.

**Diagnoses:**

- **Convex** — uplift is winning; not enough erosion time, or `K` too low.
- **Straight** — you're looking at noise, not an eroded landscape. If this is a "realistic
  eroded mountains" brief, the erosion isn't doing anything.
- **Stepped** — either real (knickpoints, which are legitimate and interesting) or unfilled
  pits. Check `A` for connectivity to tell which.

### 5. Two-scale hillshade

Render a hillshade at full extent and at a 10× zoom on a representative patch.

**Must show:** structure at both. Terrain that reads well zoomed out and turns to mush zoomed
in has insufficient octaves or over-smoothing. Terrain that reads well zoomed in and looks
like noise zoomed out has no macro structure — it needs `02`.

**The bilinear filter test:** zoom in until you can see individual cells. If you see the
diamond-shaped bilinear interpolation pattern, your export resolution is below your detail
frequency and you're storing noise you can't represent.

## Visual review modes

The five checks are quantitative — each catches a *specific* bug. This is the complementary
palette: the render modes you flip between to judge a heightfield by eye. The discipline is
**match the view to the artefact**. No single view is sufficient, and the most common review
mistake is signing off from one pretty hero shot — which hides exactly the defects a plan view
or a raking light would show.

Everything here renders one of the `06`/`08` fields; none of it modifies the terrain. Bake all
of it from **R32F** (`08`) — a review render off the quantised R16 shows you the quantisation,
not the terrain.

| Mode | Renders | Reads / catches | Blind to |
|---|---|---|---|
| **Greyscale height** | `height`, per-view normalised | Absolute range, clipping, sea level, gross blunders | Shape — the eye can't read relief off a flat ramp; a canyon and a shallow dip look identical. Overlay contour lines to recover it |
| **Hillshade** | Lambert of the normal vs a low sun | Relief, drainage texture, the overall read | Anything parallel to the sun; a single azimuth hides ridges aligned with it |
| **Sun sweep** | hillshade animated through 360° of azimuth | Grid-aligned artefacts, terracing, D8 stripes — they *strobe* as the light rotates | — the single highest-value qualitative check |
| **Slope shade** | `atan(slope)` on a ramp | Steepness directly; pairs with the slope histogram (check 2); cliffs and repose faces | Convex vs concave — slope is unsigned |
| **Normal RGB** | `normal` as RGB (or aspect as hue) | Faceting, quantisation combs, lighting seams between tiles — the "normals view" | Macro shape; it's a derivative, all high-frequency |
| **Curvature** | profile/plan curvature, *diverging* ramp centred at 0 | Ridge vs valley structure, deposition zones, mask inputs; speckle = quantisation (`06`) | Absolute height and slope |
| **AO** | long-radius horizon AO (`06`) | Macro relief — valleys darken, peaks catch light; concentric rings = R16 (`08`) | Fine detail at large radius |
| **Flow / wetness overlay** | `log(A)` or TWI over hillshade | Connectivity, channel network, where water lingers (check 1) | — |
| **Diff / A–B** | two fields subtracted, diverging ramp | Before/after erosion; monolithic vs tiled; CPU vs GPU — must match where the invariants say it must | — |
| **False-colour clip** | height with out-of-range flagged | NaN/Inf (flag magenta), below sea, above cap — *before* they spread | Everything else |

**Top (plan) view vs hero (perspective) view — use both, deliberately.**

- **Plan / orthographic (straight down)** is for *structure*: drainage connectivity, mask
  layout, scatter distribution, tiling seams, whether the network is actually dendritic. Every
  seam and every masking error is visible from directly above and nearly invisible in
  perspective. This is where you catch that the graph is *wrong*.
- **Hero / perspective (grazing camera, low sun)** is for *silhouette and read*: does it look
  like a place, does the LOD hold, do distant mountains keep their height (`08`), does terracing
  show under raking light. This is where you catch that the graph is *ugly* — and where a client
  signs off. A hero shot alone will pass a terrain whose rivers stop mid-map, because at a
  grazing angle you never see the drainage.

The rule: **plan view to verify it's correct, hero view to verify it's convincing, and never
substitute one for the other.** A rotating sun over a plan-view hillshade plus one `log(A)`
render catches more real defects in thirty seconds than any amount of turntable-ing the hero
shot.

## Failure catalogue

Symptom → mechanism → minimal fix. Ordered roughly by how often they occur.

| Symptom | Mechanism | Fix |
|---|---|---|
| Rivers stop mid-map; `A` is confetti | No depression handling | Insert epsilon priority-flood before routing (`03`) |
| Hard seams between tiles | Noise in tile-local UV | Evaluate noise in world space (`01`) |
| Soft seams / ridge at tile edges | Erosion run per-tile without apron | Apron ≥ max transport distance, or erode globally (`08`) |
| Materials in the wrong places, subtly | Analysis upstream of erosion | Move all of `06` downstream of the last height write (`06`) |
| Terracing on gentle slopes | R16 quantised too early | Work R32F, quantise at export (`08`) |
| Faceted normals / ringed AO | Baked from quantised height | Bake from R32F (`06`, `08`) |
| Speckled curvature mask | 2nd derivative of noisy/quantised field | Pre-smooth σ≈1 cell; compute from R32F (`06`) |
| Pipe erosion → NaN spikes | Missing outflow scaling factor `K` | Add step 3 of the pipe model (`04`) |
| Droplet erosion → 1px scratches | Eroding point-wise instead of with a brush | Erode with disc radius 2–4 (`04`) |
| Droplet erosion → mushy, silted | Depositing with a brush instead of point-wise | Deposit bilinear to 4 cells (`04`) |
| Terrain grows tumours / spikes uphill | Droplet speed sign convention | `speed = sqrt(speed² + (−Δh)·g)` (`04`) |
| Stream power explodes | Explicit solver | Use Braun–Willett implicit; it's 3 lines (`04`) |
| Stream power → knife-edge ridges | No hillslope diffusion term | Add `D·∇²h`, or a thermal pass (`04`, `05`) |
| Plus-shaped artefacts on cones | Thermal without per-neighbour distance | `dLimit = tan(α) * dist_n` (`05`) |
| Thermal result changes when threaded | In-place neighbour updates | Double-buffer (`05`) |
| Dunes never form; flat sand sheet | `p_sand == p_bare` in Werner | `p_sand > p_bare`; the feedback IS the instability (`05`) |
| Dunes don't migrate | No shadow zone | Implement the 15° lee capture (`05`) |
| Wetness index → Inf | `tan(slope) → 0` on flats | Clamp slope ≥ 0.001 (`06`) |
| Wetness index → stripes | Computed from D8 | Use MFD (`03`, `06`) |
| Scatter has a doubled-density line | Per-tile scatter without shared edges | Ulichney tiles or jittered grid (`07`) |
| Scatter has pairs closer than `r` | 3×3 neighbourhood instead of 5×5 | Check 2 cells out (`07`) |
| Distant mountains shrink | Box-filtered height mips | Max-filter or proper decimation (`08`) |
| Distant terrain looks like wet plastic | Box-filtered normal mips | Toksvig / LEAN mapping (`08`) |
| Cracks between LOD levels | T-junctions | Skirts, or morph the fine edge (`08`) |
| Half-cell offset between height and materials | Vertex- vs pixel-centred grids | Pick a convention; offset the sample (`08`) |
| Everything below sea level is ocean, including inland basins | Threshold instead of flood fill | Flood fill from domain edge (`03`) |
| Lakes are flat plates of terrain | Filled DEM used as the terrain | Keep both DEMs; route on filled, render original (`03`) |
| Terrain looks fine but "procedural" | Hard thresholds on masks | Noise-perturb every threshold (`06`) |
| Forest reads as a stamp field | Variation from `random()` only | Derive scale/species from environment (`07`) |
| Jitter in terrain 100 km from origin | fp32 mantissa exhausted | Camera-relative or tile-relative coords (`01`, `08`) |
| Diagonal banding in 3D-noise-on-a-plane | Lattice aligned with the sampling plane | Use `noise3_ImproveXY` (`01`) |
| Grid of pinch points in FBM | All octaves share zero crossings | Offset each octave (`01`) |
| Hybrid multifractal → isolated absurd spikes | Missing `min(weight, 1)` | Clamp the weight (`01`) |
| Creases along grid lines under lighting | Original Perlin cubic fade | Use quintic `6t⁵−15t⁴+10t³` (`01`) |
| Mask outlines the noise lattice | Thresholding gradient noise near 0 | Threshold FBM, or offset from 0 (`01`) |

## Review checklist

For reviewing an existing graph. Ordered by expected yield.

- [ ] Depression handling present, and before flow routing?
- [ ] Is it the epsilon variant?
- [ ] Legitimate closed basins masked out of the fill? (the no-fill list in `03`: karst, glacial overdeepenings, craters, playas, thermokarst, oxbows, lagoons)
- [ ] All analysis nodes downstream of the last height write?
- [ ] Noise evaluated in world space?
- [ ] Erosion backbone matched to world extent? (droplet <2 km, pipe 2–50, stream power >50)
- [ ] Parameters in world units, not magic numbers tuned at one resolution?
- [ ] Thermal downstream of hydraulic?
- [ ] `A` reported in m², not cell counts?
- [ ] MFD (not D8) feeding any hillslope quantity (wetness, dispersive masks)?
- [ ] Quantisation to R16 after all derivatives?
- [ ] Normals and AO baked from R32F?
- [ ] Apron on tiled erosion ≥ max transport distance? (Or: is stream power being tiled? It can't be.)
- [ ] Boundary condition stated explicitly?
- [ ] Seed derived from a documented root-seed rule?
- [ ] Double-buffering in every grid simulation?
- [ ] Masks partition to 1?
- [ ] Every hard threshold noise-perturbed?
- [ ] Vertex- vs pixel-centring documented and consistent?

**Report findings as: symptom → mechanism → minimal fix.** A graph with one misordered node
needs one node moved, not a rewrite. Minimal diffs are reviewable; rewrites are not.
