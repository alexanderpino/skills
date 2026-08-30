---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Reference
title: "Primitives, Operators, Filters & Warps"
description: The SDF and gradient primitives, the combiners, and the three distinct roles a curve plays — the distinction that costs the most rebuilds when missed.
tags: [primitives, sdf, filters, warp]
status: stable
generated: { by: process:claude-code, at: 2026-08-05T18:35:04Z }
# --- end okf v0.2 ----------------------------------------------------
---
# Primitives, Operators, Filters & Warps

The "boring" nodes. They have no papers, which is exactly why they ship broken — nobody
reviews them. Most of the damage in a terrain graph is done here, quietly.

Contents: [Primitives](#primitives) · [SDF](#distance-fields-frisken-et-al-2000) ·
[Heightfield operators](#heightfield-operators) · [Smooth min/max](#smooth-min--max) ·
[Sculpting](#sculpting) · [Curve-driven landforms](#curve-driven-landforms) ·
[Filtering](#filtering) · [Bilateral](#bilateral-tomasi--manduchi-1998) ·
[Guided](#guided-filter-he-sun--tang-2010) · [Anisotropic diffusion](#anisotropic-diffusion-perona--malik-1990) ·
[Morphology](#morphology-serra-1982) · [Warps](#warps)

## Primitives

No papers. Sub-one-line each. The only thing that matters is that they are evaluated in
**world space** with **metre outputs**, like everything else.

```
plane(p)           = 0
gradient(p, dir)   = dot(p - origin, normalize(dir)) * scale
radialGradient(p)  = 1 - clamp(|p - centre| / radius, 0, 1)
cone(p)            = height * max(0, 1 - |p - centre| / radius)
hemisphere(p)      = d = |p - centre| / radius
                     d < 1 ? height * sqrt(1 - d*d) : 0
pyramid(p)         = q = abs(p - centre) / halfWidth
                     height * max(0, 1 - max(q.x, q.y))          // Chebyshev → square base
```

The falloff on a radial gradient is where these go wrong. A linear falloff has a C1
discontinuity at the rim — a visible crease ring under any lighting. Use `smoothstep`:

```
radialGradient(p) = 1 - smoothstep(0, radius, |p - centre|)
```

Same applies to the cone: a mathematical cone has a crease at the apex and a crease at the
base. Real hills have neither. If a primitive is going to be the base of a mountain, put a
`smoothstep` on it or run thermal erosion (`05`) afterward — the latter is more honest and
gives you a repose-angle profile for free.

### Build the mass first, dissect it after

The single most expensive mistake in this whole file, measured in rebuilds. Feature primitives are
almost always written as **envelope × texture**:

```
h(p) = envelope(|p - centre|) * detail(p)          // <-- the trap
```

If the envelope is a function of **radius alone** — `(1-r)^k`, a bell, a cone, a Gaussian — the
result is a **solid of revolution**, and multiplying it by texture does not change that. The
silhouette stays revolved however good the texture is. It renders as a tipi tent. Starting with a
cone and cutting radial grooves into it leaves a tent no matter how good the grooves are.

This is hard to catch because it hides from the obvious checks. A smooth cone satisfies *all* of:
relief within the requested range, exactly one dominant summit, summit well above the mean, margins
below the mean, monotone radial descent, deep interior incision. Those are the assertions a
mountain primitive naturally attracts, and every one of them passes.

**The fix is an ordering, not a parameter.** Build an *asymmetric mass* first — a wandering
crest-line polyline SDF, several unioned sub-masses, saddles, faces of unequal steepness — and only
then dissect it with the Voronoi/drainage network. The mass carries the anisotropy; the dissection
adds relief within it. Reversing the two cannot work, because dissection is a local operation and
cannot introduce a large-scale asymmetry the envelope did not have.

**Two metrics that separate the cases**, both cheap, both needing a cone as the control:

| Metric | Cone | Pure noise | `landforms.mountain` |
|---|---|---|---|
| Rotational correlation about the summit (mean over 30–150°) | 1.000 | 0.092 | 0.073–0.337 |
| Variance a best-fit radial profile leaves unexplained | 0.022 | 0.965 | 0.79–0.91 |

Measure both against a cone every time; a bare threshold with no control is how the tent shipped
twice. `landforms.mountain` uses the polyline envelope for exactly this reason, pinned by
`tests/test_landforms.py::test_mountain_is_not_a_solid_of_revolution`.

The same trap applies to any radially-enveloped primitive — volcanoes, craters, hills, islands. A
volcano genuinely *is* close to a solid of revolution, so there it is fine; a mountain is not, and
neither is an island.

## Distance fields (Frisken et al. 2000)

*Adaptively Sampled Distance Fields*, SIGGRAPH 2000 — the canonical ADF reference. For
terrain, the useful part is not the adaptive sampling but the **exact 2D SDF primitives** and
their combination operators (Quilez's articles are the practical catalogue).

```
sdCircle(p, r)     = |p| - r
sdBox(p, b)        = d = abs(p) - b
                     |max(d, 0)| + min(max(d.x, d.y), 0)
sdSegment(p, a, b) = pa = p - a;  ba = b - a
                     h = clamp(dot(pa, ba) / dot(ba, ba), 0, 1)
                     |pa - ba * h|
sdConvexPolygon(p, normals[], offsets[])         # a block as the intersection of half-planes;
                   = max_k( dot(normals[k], p) - offsets[k] )   #   the generalisation of sdBox.
```                                              # Exact on the faces; slight underestimate at exterior
                                                 # corners (the max-of-half-planes). Behind fault-block
                                                 # buttes (11): outline the polygonal joint-controlled footprint.

Why this matters for terrain: an SDF gives you **distance**, and distance is what you want for
falloffs, road corridors, river authoring, spline deformation, and uplift masks (`02`). A mask
built from a distance field has a controllable, continuous profile; a mask built from a
rasterised shape has stair-stepped edges you will fight forever.

`sdSegment` is the workhorse: splines are polylines, and the distance to a polyline is the min
over segments. Build a distance field once, then remap it with a profile curve to get a
valley, a ridge, a road, or an uplift band.

## Heightfield operators

Trivial, and there are exactly four ways they hurt you.

```
add(a, b)        = a + b
sub(a, b)        = a - b
mul(a, b)        = a * b
min(a, b)        = min(a, b)
max(a, b)        = max(a, b)
blend(a, b, t)   = a + (b - a) * t
clamp(a, lo, hi) = min(max(a, lo), hi)
curve(a, f)      = f(a)                       // f = spline / LUT
normalize(a)     = (a - min(a)) / (max(a) - min(a))
```

**1. `normalize` is the cardinal sin.** It destroys world-space units. After `normalize`, the
field is in [0,1] and every downstream parameter expressed in metres — talus thresholds,
erosion rates, cell size relationships — is meaningless. It also makes the graph
**non-composable**: the output now depends on the global min/max of *this particular*
evaluation, so a tile normalised alone differs from the same tile normalised as part of a
larger domain. **That is a guaranteed seam.**

Use `normalize` only inside the export node, or never. If you need a [0,1] field, use an
explicit `remap(a, knownMin, knownMax)` with constants you wrote down.

**Tonal family (the "Levels/Curve/Equalize/Sharpen" nodes).** `curve` (above) is the general
value-remap; `levels(a, inLo, inHi, gamma)` = clip to a written range + a midtone gamma (the
composable Levels); `sharpen`/`unsharp = a + amount·(a − blur(a))` boosts sub-`sigma` detail (the
honest inverse of `gaussian`, which softens). `equalize` maps each value to its **CDF** so every
band gets equal area — maximal contrast, but it is **data-dependent like `normalize`** (it reads the
whole field's histogram), so it **seams**: a final-look / mask op, never mid-graph. `gradient` and
`radialGradient` are the two ramps everything else masks against.

*Runnable reference: `reference-impl/ops_filters.py` — `linear_gradient`, `curve`, `levels`,
`histogram_equalize`, `unsharp` (verified in `tests/test_ops_filters.py`: gradient monotone & clamped,
curve==remap at 2 points & order-preserving, levels clips/gammas, equalize flattens the histogram &
never inverts, unsharp is identity at amount 0).*

**2. `max` and `min` create creases.** `max(mountainA, mountainB)` produces a C1 discontinuity
along the intersection curve — a hard crease that reads as obviously CG, and which produces a
line of infinite curvature that will wreck any curvature-driven mask (`06`). Use smooth
min/max (below).

**3. `mul` for masking assumes [0,1].** `height * mask` where height is in metres and mask is
in [0,1] scales the *absolute elevation*, not the relief. Multiplying a terrain at 1000 m by a
0.5 mask gives 500 m — you moved the whole thing down, you didn't flatten it. What you almost
always want is `blend(baseLevel, height, mask)`.

**4. `curve` on Gaussian data does nothing you expect.** See `01` — noise is Gaussian-ish, not
uniform, so most of your data is clustered in the middle of the curve and the tails are empty.
Histogram-match, or apply the curve to a measured range.

## Smooth min / max

Quilez's polynomial smooth min. Costs three ops and removes every crease in the graph.

```
smin(a, b, k):                          # k = blend width, in the SAME UNITS as a, b (metres)
    h = clamp(0.5 + 0.5 * (b - a) / k, 0, 1)
    return lerp(b, a, h) - k * h * (1 - h)

smax(a, b, k) = -smin(-a, -b, k)
```

`k` is a world-space distance, so it must be re-derived if the vertical scale changes. `k ≈ 5%
of the relief` is a sane start. `k → 0` recovers hard `min`/`max`.

The subtraction term `k·h·(1−h)` is what makes it smooth rather than just a lerp; leaving it
out gives you a linear crossfade with two new creases instead of one.

## Sculpting

```
flatten(h, mask, target)  = lerp(h, target, mask)
                            # target = a constant, or mean(h) under the mask
smooth(h, mask, k)        = lerp(h, gaussian(h, k), mask)
raise(h, mask, amount)    = h + mask * amount
stamp(h, stamp, xform, mode)
spline(h, curve, profile)
```

**Stamp.** The three things that go wrong:
- **World-space anchoring.** A stamp placed in tile-local UV moves when tiles change.
- **Blend mode.** `add` stacks stamps into towers; `max` creases; `smax` is right.
- **Height units.** A stamp authored in [0,1] must be scaled to metres at placement, with an
  explicit amplitude. A stamp that carries absolute metres cannot be reused at another scale.

**Spline deform.** Build an SDF from the polyline (`sdSegment`, above), then:

```
d = sdPolyline(p, curve)                  # metres
t = clamp(d / width, 0, 1)
h = lerp(curveElevationAt(p), h, smoothstep(0, 1, t))
```

`curveElevationAt` interpolates elevation along the spline (arc-length parameterised, or the
spacing is uneven and the valley floor undulates). This is how roads, riverbeds, and authored
valleys get cut. Note it is a *hard authored constraint* — run it before erosion and erosion
will remove it; run it after erosion and it will cut across the drainage. Usually: before, and
then re-cut a shallow version after. The full doctrine for curve-authored landforms — mountain
ranges and gorges included — is the next section.

## Curve-driven landforms

The spline deform above is a *mechanism*; this section is the discipline around it, because the
curve is the single most-used art-direction handle in terrain ("a range along here, a gorge through
there") and the one most likely to produce terrain that reads as drawn. Engines have converged on the
same primitive from the other side — Unreal's Landscape Splines deform height and paint weights along
a curve from per-control-point **width and falloff** with a cosine-blended edge, and Landmass custom
brushes build a *landmass from a spline* with a falloff angle, a blend mode, capped/uncapped tops and
optional erosion/noise effects, all writing non-destructively into an edit layer. So the vocabulary
below is shared across the tool/engine boundary (terrain-renderer `03`, `27`), which makes getting it
right on this side worth more than usual.

### Three directions a curve can cross the pipeline

The recurring mistake is treating every curve the same. There are three roles, and **the role
determines what the curve is allowed to contain**:

| Role | The curve is | Carries | Right for |
|---|---|---|---|
| **`CAUSE_SEED`** — input, *before* the solve | A seed for a **driver field**: an uplift ridge or fault trace (`02`), a discharge injection or base-level line (`03`), a weakness line in `strataHardness` (`11`), a glacier flowline (`12`) | Position + the magnitude of a *process parameter*. **Never final height** | Anything a process makes: ranges, gorges, valleys, canyons, escarpments |
| **`POST_SOLVE_STAMP`** — *after* the solve | A direct height edit with a cross-section | Literal metres | Features no natural process made: roads, terraces, canals, levees, quarries, earthworks, gameplay flattening |
| **`SOLVE_PROJECTION`** — output, *after* the solve | A trace of what the simulation produced | Position + *measured* attributes (channel width from hydraulic geometry, depth, velocity) | The handoff — engine water bodies and spline landforms (`27`) |

A curve entering the solve carries **causes**; a curve leaving it carries **measurements**; only a
curve applied after the solve carries **height**, and then only for features that were built rather
than eroded. Nearly every "my spline mountains look fake" complaint is a `CAUSE_SEED` landform
authored as a `POST_SOLVE_STAMP`.

### The ordering rule

This is the Legal Order (`SKILL.md`) applied to curves, and it decides the result more than any
profile parameter:

```
range   : curve -> uplift field U(x)          -> stream power + diffusion   # valleys are PRODUCED
gorge   : curve -> channel seed + base-level  -> bedrock incision           # walls are PRODUCED
         (or) curve -> strataHardness weakness -> erosion exploits it       # fault/joint-guided
glacial : curve -> flowline + ice thickness   -> SIA + abrasion (12)        # U-profile is PRODUCED
road    : erosion -> curve stamp -> re-derive normals/AO/curvature (06, 08)
```

Two consequences worth stating outright: a `CAUSE_SEED` curve **must run before erosion**, or the
process it seeds never happens; and any `POST_SOLVE_STAMP` **invalidates every derived map** —
normals, AO, curvature, insolation, flow — so it either runs before the derived-map bake or the bake
runs again. The "cut, erode, re-cut shallow" compromise above is legitimate, but the re-cut must be
shallow and feathered, and it pays the re-derive cost.

### A range is a divide, not a ridgeline

Extruding a curve into a Gaussian ridge produces a **smooth wall**. It technically *is* a divide —
water runs off both flanks — but it is the wrong kind: no valleys, no spurs, and a crest line that
runs exactly where the curve was drawn instead of wandering where competing headward erosion put it.
A real divide is an emergent, sinuous boundary between two growing networks. The fix is already in
`02` — put the curve
into the uplift field (`U = A·exp(-d²/2σ²)` along the polyline) and let stream power and hillslope
diffusion dissect it. The valley network is the product; the curve only says *where the rock came up*.

Per-station attributes a range curve should carry, and the tells if it doesn't:

| Attribute | What it does | Tell when missing |
|---|---|---|
| `amplitude` (uplift `A`, not crest height) | Sets relief through the erosion budget | Crest elevation authored directly → constant-height ridge with no relief hierarchy |
| `halfWidth` (σ) | Range width, and with `A` the flank gradient | A range the same width along its whole length |
| `asymmetry` | Vergence: thrust belts are steep on one flank, long-sloped on the other | Symmetric range — the "extruded Gaussian" giveaway |
| `plunge` at the ends | Ranges die out into their foreland | A range chopped flat at the domain edge or ending mid-plain |
| segmentation / en-echelon offset | Real ranges are segmented, not one smooth arc | A single continuous sweep with no structural junctions |

Three couplings a curve-placed range must also honour, because they are what make it read as
*present in the world* rather than pasted onto it:

- **Its effect on existing drainage is decided, not ignored.** Plenty of real ranges are clean
  divides that nothing crosses, so a range without a water gap is not automatically wrong — but a
  range dropped into a domain that *already has a trunk river* has to resolve what happened to it.
  Two legitimate outcomes: the river is defeated and diverted along the front, or it holds its course
  through the rising rock and leaves a **water gap** (the antecedent case; an abandoned one leaves a
  **wind gap** notched in the divide — `20`). The defect is the third outcome, where the uplift is
  stamped and the exported flow field still shows the old river running straight through a solid
  ridge.
- **It casts a rain shadow.** Place the range in the climate solve too, or the leeward side stays as
  wet as the windward one and the vegetation, snow line and erosion rates all disagree with the
  topography (`13`).
- **Its drainage density sets its spur spacing.** Ridge-to-ridge spacing on the flanks comes out of
  the erosion solve; if it was authored, it will be uniform, and uniform spur spacing is visible from
  a kilometre away.

### A gorge is an incision history, not a trench

Same failure one process over: subtracting a swept prism gives uniform width, uniform wall angle, a
flat floor, no talus, no benching and no tributaries. Which gorge is wanted decides which cause to
seed — the geology of each lives in the chapters routed below, and this table is the *authoring*
crosswalk:

| Gorge kind | Cause to seed | Cross-section | Route |
|---|---|---|---|
| Fluvial canyon / **entrenched meander** | Channel path + discharge, with uplift or base-level fall | V; and the bends are a *fossil planform* — set when the river was free to migrate on a floodplain, then incised vertically into rock, so the walls are rock rather than cutbanks (`20`) | `03`, `04`, blueprint in `20` |
| **Slot canyon** | Path along a joint set; flash-flood abrasion in massive rock | Width an order of magnitude or two below depth (metres against tens of metres); scalloped, overhanging walls — the overhang is non-heightfield (`11`) | `20`, `16` |
| **Fault / joint-guided gorge** | A weakness line in `strataHardness`, *not* a height cut | Straight runs with abrupt angular bends at joint intersections | `11` |
| **Glacial trough** | Ice flowline + thickness | **U**, with hanging tributaries and truncated spurs | `12` |
| **Box canyon / sapping** | A spring line at the head | Theatre-headed amphitheatre terminus, no tributary network above it | `11`, `20` |

Five invariants apply to all of them, and each is a cheap assertion:

1. **It has an inlet and an outlet.** A gorge that starts and ends in flat ground is the "canyon
   carved by nothing" tell (`20`); its floor must connect to the drainage network at both ends.
2. **The floor is monotone downstream.** Same defect, and same check, as the uphill river of `27`.
3. **Two widths, not one.** The channel on the floor is sized by hydraulic geometry (`03`); the
   *gorge* is sized by wall retreat over the incision history. Ship both. Collapsing them to one
   number gives a river that exactly fills its canyon at every station — the single clearest tell
   that the gorge was swept rather than incised.
4. **The walls record the rock.** Strata benching where resistance alternates (`11`), talus at repose
   at the base (`05`), caprock overhangs. Constant-slope unbenched walls are an extruded profile.
5. **Whether a tributary hangs follows from its own power, not from taste.** A trunk incising faster
   than a tributary can keep up leaves that tributary perched, with a waterfall at the junction
   (`04`). Since incision scales with discharge, the realistic pattern is *graded*: small tributaries
   hang, large ones keep pace and meet at grade, in the same gorge. The defect is hanging assigned
   arbitrarily — a big tributary perched above a trickle that meets at grade is telling two
   histories.

### The cross-section vocabulary

One record covers ranges, gorges, valleys, roads and levees — and it is deliberately close to what
engine brushes expose, so a `SOLVE_PROJECTION` export drops straight into them (`27`):

```
curve_landform:
  kind                 # range | gorge | valley | escarpment | terrace | road | levee | ...
  role                 # CAUSE_SEED | POST_SOLVE_STAMP | SOLVE_PROJECTION   (above)
  vertices[]:
    xy
    z                  # STAMP / PROJECTION only: crest elevation (range) or floor elevation
                       #   (gorge, valley, road). A CAUSE_SEED range MUST NOT carry a crest
                       #   elevation - the crest is an erosion product; use amplitude instead
    halfWidth_m        # the feature's own half-width at this station
    amplitude_m        # CAUSE_SEED: the process magnitude (uplift A, incision rate, ice thickness)
                       # STAMP:      metres above / below the surrounding surface
    asymmetry          # [-1,1]: which flank is steeper
  falloff              # ANGLE (extend the flank at a slope until it meets terrain) | WIDTH (fixed)
  profile              # V | U | slot | box | flat | authored 1D cross-section curve
  blend                # min | max | add | alpha | smax          (Stamp, above)
  edgeOffset_m         # flat shelf before the falloff starts (berm, shoulder, shore shelf)
  cap                  # capped (plateau / mesa top) | uncapped (peak)
```

Three of those get chosen wrongly often enough to call out:

- **`falloff` by angle, not by width, for natural landforms.** An angle falloff extends the flank at
  a *slope* until it meets the existing surface, so the same range is narrow in a valley and wide on
  a plain — which is the graded-slope behaviour real terrain has (`05`, repose) and the reason engine
  brushes offer it. Fixed-width falloff is for engineered features, where a constant footprint is the
  point.
- **`blend`: `alpha` replaces, and replacing destroys.** An alpha-blended stamp over eroded terrain
  flattens exactly the high-frequency detail the erosion solve produced. Cut with `min`, raise with
  `add` or `smax`, and the detail survives inside the feature. This is the same rule as `27`'s
  double-carve defect, one level up.
- **`profile` is not free.** V, U, slot and box each name a *process*; picking one that contradicts
  the cause seeded (a V-shaped "glacial valley", a U-shaped flash-flood slot) is a claim the terrain
  will contradict everywhere else — the hanging tributaries, the talus, the drainage.

### Failure catalogue

- **The wall** — a range as an extruded Gaussian: smooth flanks, no valleys, no spurs. Seed uplift
  and run erosion.
- **The trench** — a gorge as a subtracted prism: uniform width and wall angle, flat floor, no talus,
  no benching, no tributaries.
- **The orphan** — a gorge or valley connected to no drainage at either end.
- **The uphill gorge** — floor not monotone downstream.
- **The chopped range** — ends abruptly instead of plunging into its foreland.
- **Corner-cutting** — polyline resampled coarser than the falloff width, so the swept profile
  short-cuts every bend and the feature leaves its own curve.
- **Terraced walls** — a stamp evaluated into quantised height instead of R32F (`08` precision).
- **Detail erased** — alpha-blend stamping over eroded terrain (above).
- **The dry lee that isn't** — a range added after the climate solve: no rain shadow, no asymmetric
  vegetation or snow line (`13`).
- **The smooth saddle** — two overlapping range curves blended into a gentle col; real ranges meet in
  structural junctions, and the saddle between them is a drainage divide with valleys climbing to it.

## Filtering

The general rule: **Gaussian blur is wrong for terrain.** It smooths ridges and cliffs — the
exact features you want to keep — and leaves the noise you wanted to remove roughly where it
was. Everything below is a better default.

**Sigma must be in world units.** `gaussian(h, sigma_metres / cellSize)`. A blur node
parameterised in pixels produces a different result at every resolution, which is one of the
most common ways a graph fails to survive a resolution change.

Gaussian is separable — two 1D passes, O(k) not O(k²). Any implementation doing a 2D kernel is
wasting time.

### Median (Tukey)

```
median(h, r) = for each cell: the median of the (2r+1)² window
```

Removes **spikes** (salt-and-pepper) while preserving step edges exactly. This is what you want
after any process that can produce isolated bad cells — a NaN-adjacent pipe erosion, a bad
import, a droplet that dumped its whole load in one cell.

Naive is O(r² log r) per cell. Use the histogram-sliding method (O(r) or O(1) amortised) if `r`
is large; for `r ∈ {1, 2}` — which is all you need for despiking — the naive sort of 9 or 25
values is faster than the machinery.

**Median does not remove noise, it removes outliers.** Don't reach for it as a smoother.

### Bilateral (Tomasi & Manduchi 1998)

*Bilateral Filtering for Gray and Color Images*, ICCV 1998. Edge-preserving smoothing: weight
neighbours by both spatial distance and value difference.

```
bilateral(h, p, sigma_s, sigma_r):
    num = 0;  den = 0
    for q in window(p, radius ≈ 2*sigma_s):
        w_s = exp(-|q - p|²      / (2 * sigma_s²))      # spatial, metres
        w_r = exp(-(h[q] - h[p])² / (2 * sigma_r²))     # range, METRES of height
        w   = w_s * w_r
        num += w * h[q];  den += w
    return num / den
```

**`sigma_r` is the parameter that matters, and it is in metres of elevation.** It is the answer
to "how big a height difference counts as a real feature rather than noise?" Set it just above
your noise amplitude and just below your smallest real cliff. Get it right and you smooth
hillslope noise while cliffs stay razor-sharp. Get it wrong in one direction and it's a
Gaussian; the other and it does nothing.

Not separable (the range weight breaks separability). O(r²) per cell. Expensive at large `r` —
which is why:

### Guided filter (He, Sun & Tang 2010)

*Guided Image Filtering*, ECCV 2010. Edge-preserving, **O(1) per cell regardless of radius**,
built entirely from box filters (which are O(1) via summed-area tables).

```
guided(p, I, r, eps):                   # p = input, I = guide (often = p for self-guided)
    mean_I  = boxFilter(I, r);        mean_p  = boxFilter(p, r)
    corr_I  = boxFilter(I*I, r);      corr_Ip = boxFilter(I*p, r)
    var_I   = corr_I - mean_I*mean_I
    cov_Ip  = corr_Ip - mean_I*mean_p

    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I

    mean_a = boxFilter(a, r);  mean_b = boxFilter(b, r)
    return mean_a * I + mean_b
```

`eps` plays the role of `sigma_r²` — it's the variance threshold below which a region is
treated as flat and smoothed. So `eps ≈ (noiseAmplitude_metres)²`.

**For terrain this is strictly better than bilateral in most cases**: same edge preservation,
constant time, no gradient-reversal artefacts near strong edges (bilateral has them). Use a
*separate guide* to do something bilateral can't — e.g. smooth the material mask using the
*height* as the guide, so the mask edges snap to terrain features.

### Anisotropic diffusion (Perona & Malik 1990)

*Scale-space and edge detection using anisotropic diffusion*, IEEE PAMI 12(7). Diffusion whose
conductivity drops where the gradient is high — so it smooths *within* regions and not
*across* edges.

```
perona_malik_step(h, K, lambda):        # lambda <= 0.25 for stability with 4 neighbours
    for each cell:
        for n in 4 neighbours:
            d = h[n] - h[c]
            c_n = exp(-(d / K)²)                    # or 1 / (1 + (d/K)²)
            Δ[c] += lambda * c_n * d
    h += Δ                                           # double-buffer
```

`K` is the gradient threshold in metres — same role as bilateral's `sigma_r`. Iterate 5–50
times.

**Notice the shape.** This is slope-limited diffusion. It is *the same object* as thermal
erosion (`05`) and as the `D·∇²h` hillslope term in stream power (`04`), with a different
conductivity function. If you already run thermal, you are already running an anisotropic
diffusion and adding a Perona–Malik node is redundant. That's a graph-review finding worth
making.

### Morphology (Serra 1982)

*Image Analysis and Mathematical Morphology*. Greyscale morphology on a heightfield:

```
dilate(h, SE) = max over the structuring element        # grows peaks, fills pits
erode(h, SE)  = min over the structuring element        # shrinks peaks, deepens pits
open(h, SE)   = dilate(erode(h, SE), SE)                # removes peaks smaller than SE
close(h, SE)  = erode(dilate(h, SE), SE)                # fills pits smaller than SE
tophat(h, SE) = h - open(h, SE)                         # isolates small peaks → mask
bothat(h, SE) = close(h, SE) - h                        # isolates small pits → mask
```

Two genuinely useful terrain applications:

1. **`tophat` is a free "small features" mask.** Everything smaller than the structuring
   element, isolated from the large-scale terrain. Excellent for placing detail materials
   (scree, boulders) or for a high-pass that doesn't ring like a Gaussian difference.
2. **`close` is a poor man's depression fill.** It fills every pit smaller than the SE — which
   is nearly all of them. It is *inferior to Priority-Flood* (`03`) because it fills by SE
   size rather than by hydrological connectivity, so it will fill a genuine basin that's
   smaller than the SE and miss a shallow wide one. **Do not substitute it for `03`.** It is
   worth knowing that a graph using morphological close where it should use priority-flood
   will *look* fine and route flow wrong.

Greyscale dilate/erode with a flat SE is separable for rectangular SEs, and O(1) per cell with
the van Herk / Gil–Werman algorithm for arbitrary 1D runs. A max-filter mip chain (`08`) is
just repeated dilation.

## Warps

`domainWarp` and `curl` are in `01` — they're noise-driven and belong there. The
authored-deformation warps live here. All of them are coordinate transforms applied before
sampling:

```
vectorWarp(p, V, amp) = sample(p + amp * V(p))          # V = any 2D vector field
twist(p, centre, k)   = q = p - centre
                        a = k * |q|                      # rotation grows with radius
                        centre + rot(q, a)
bend(p, k)            = (p.x, p.y + k * p.x²)            # or any profile function of p.x
```

Two rules:

- **Warp the sample coordinate, not the output.** `sample(warp(p))` is a deformation.
  `warp(sample(p))` is a value remap wearing a deformation's name.
- **Warping after erosion invalidates the erosion.** The drainage network was computed on the
  pre-warp geometry; warp it and the rivers no longer run downhill. Every warp belongs
  upstream of step 4 in the Legal Order. A `twist` node downstream of stream power is a bug,
  and it is the kind of bug that looks great in a hillshade and fails the flow accumulation
  check (`09`) instantly.

## Placement & masking: making a procedural terrain art-directable

A generator that only produces terrain *everywhere* cannot be directed. Two operations turn a
procedural graph into something an artist can lay out, and every terrain tool converges on the same
pair (`reference-impl/placement.py`):

**Place** — build a coverage mask from an SDF positioned in **world coordinates**: `disc`, `rect`,
`capsule` (a thick segment, for a river corridor or ridgeline), `polygon`, `path_mask` (a polyline
corridor). The SDF primitives themselves are the `sd_*` functions above; placement adds the
transform (centre, rotation) and the distance→coverage step.

**Mask** — `apply_masked(base, modified, mask)` applies an effect *only where the mask is bright*:
`base + (modified − base) · mask`. This is the universal "mask input" — erode this valley, leave
that plateau; warp here, not there. Note it is a **post-process**: the effect runs, then the mask
selects. Changing the mask therefore does not re-run the effect, which is what makes laying out a
composition interactive. Gaea makes the same distinction explicitly, warning that masking a node
*directly* forces a full rebuild while a separate mask node is "extremely fast".

Two rules that are easy to get wrong:

- **Author placements in metres, never cells** (08). A layout keyed to cell indices slides across
  the terrain the moment the build resolution changes. `placement` takes `cellsize` and world-space
  centres/radii for exactly this reason, and the invariance is pinned by a test.
- **Never ship a binary mask.** A hard 0/1 edge prints its staircase through every downstream blend,
  so `coverage()` clamps the soft edge to at least one cell even when `falloff=0`.

A placement mask is also a **shape**: the same disc that confines an erosion can be treated as a
heightfield and eroded into a landform. That dual use — mask *or* primitive — is why the shape
belongs in the graph rather than in a brush tool.

### Place before you sample, not after

There are two ways to move a feature, and only one is free.

**Coordinate transform (before sampling).** A procedural generator is a *function of position*, so
evaluating it at shifted coordinates moves the feature **exactly** — it is the same function, sampled
somewhere else. `placement.place_coords(xx, yy, shape, cellsize, center=, rotation=, scale=)`
transforms a generator's own coordinate grid, and `landforms.mountain/ridge/canyon` take a `place=`
argument that applies it. Placing at the native centre is the identity; placing elsewhere lands the
crest at exactly the requested offset.

**Raster transform (after sampling).** Moving the *output* resamples it, and bilinear resampling is a
low-pass filter. Measured on 6-octave fBm with a non-integer offset, scored as **mean |laplacian|**:
**one move loses ~24% of the fine detail, four chained moves ~53%** — the losses compound, because
each hop filters the already-filtered result. Coordinate placement loses none of it at any depth. Use
a raster transform only for fields you cannot re-evaluate — an imported DEM, or the output of an
erosion simulation — which is exactly what a Transform node is for.

**Always quote the metric with the number.** The same experiment scored on high-frequency band energy
(field minus a σ=2 gaussian) reads ~9% and ~26% instead. Neither is wrong; a bare percentage is.
`tests/test_placement.py::test_raster_transform_loses_detail_that_placement_keeps` pins these so the
prose cannot drift from the code, and the Terrain Studio's independent JS implementation measures
24.7% / 53.8% on the same metric — two implementations, one number.

A second measurement trap sits inside this one: coordinate placement lands on a *different window* of
the same fBm, and detail energy genuinely varies window to window (±6% at 192²). Read that variance as
"placement lost detail too" and you have measured your own sampling noise. The invariant that survives
is **no systematic decline with depth**, not equality.

One honest caveat: a generator that normalises by its **own** extremes is not perfectly
translation-invariant, because moving it changes what is in frame. Measured on `ridge`, that shows up
as a global scale factor of 1.0006 and a mean difference of 0.013% of relief — negligible, but it is
why the test asserts "the same terrain, moved" within a tolerance rather than bit-equality.

#### It is an affine matrix — and sampling uses its inverse

The placement above is a standard **affine transform**, and `placement.affine(center, rotation,
scale, shear, pivot)` builds it explicitly as a 3x3 homogeneous matrix:

    M = T(center) . R(rotation) . Sh(shear) . S(scale) . T(-pivot)

The subtlety worth stating plainly: **you sample with the inverse.** You iterate over *destination*
pixels and need the *source* coordinate feeding each one, so the sampler applies `M^-1`
(`sample_coords`) while the feature moves by `M` (`transform_coords`). Getting that backwards moves
everything the wrong way — the classic sign error in every texture transform. `place_coords` is
exactly this inverse, hand-decomposed for the common translate/rotate/uniform-scale case; the tests
assert the two agree.

Two things the matrix form buys: **non-uniform scale and shear**, which the decomposed version
cannot express, and **composition** — `compose(A, B, C)` collapses a chain into one transform. For a
generator that is merely tidier (sampling is exact either way), but for a **raster** it is a real
quality win: each extra resample is another low-pass filter, so collapsing four moves into one avoids
the ~53% detail loss measured above.
