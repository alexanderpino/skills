# Primitives, Operators, Filters & Warps

The "boring" nodes. They have no papers, which is exactly why they ship broken — nobody
reviews them. Most of the damage in a terrain graph is done here, quietly.

Contents: [Primitives](#primitives) · [SDF](#distance-fields-frisken-et-al-2000) ·
[Heightfield operators](#heightfield-operators) · [Smooth min/max](#smooth-min--max) ·
[Sculpting](#sculpting) · [Filtering](#filtering) · [Bilateral](#bilateral-tomasi--manduchi-1998) ·
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
```

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
then re-cut a shallow version after.

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
