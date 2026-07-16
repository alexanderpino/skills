# Analysis & Masks

Contents: [Ordering rule](#ordering-rule) · [Slope & aspect](#slope--aspect) ·
[Curvature](#curvature-zevenbergen--thorne-1987) · [Horizon AO](#horizon-based-ambient-occlusion) ·
[Wetness](#wetness-index-beven--kirkby-1979) · [Normals](#normals) ·
[Selectors](#selectors--masks-from-the-analysis-fields) · [Masks → materials](#masks--materials)

## Ordering rule

**Every node in this file must be downstream of the last node that modifies height.**

Analysis describes the terrain. If it runs before erosion, it describes a terrain that no
longer exists. A snow mask built on pre-erosion slope paints snow on the walls of valleys that
erosion has since cut. This is the second-most-common defect after missing depression handling,
and it is harder to spot because the output looks superficially fine — the materials are just
subtly, inexplicably wrong.

The one legitimate exception is analysis used as *input* to erosion (e.g. slope-dependent
erodibility). Name it differently so nobody wires it into the material graph by accident.

## Slope & aspect

```
gradient(h, i, j):
    dzdx = (h[i+1, j] - h[i-1, j]) / (2 * cellSize)
    dzdy = (h[i, j+1] - h[i, j-1]) / (2 * cellSize)
    return (dzdx, dzdy)

slope  = sqrt(dzdx² + dzdy²)                 # tan(angle) — rise over run
aspect = atan2(dzdy, dzdx)                   # radians; compass-convert if the artist expects it
```

**Keep slope as `tan`, not degrees.** Every comparison downstream (`slope > tan(35°)`) is
then a cheap float compare, and it composes with the repose-angle table in `05` directly.
Convert to degrees for UI only.

The central difference above is fine. Horn's method (the 3×3 Sobel-weighted version used by
ArcGIS and most GIS tools) is more robust to noise:

```
dzdx = ((h[i+1,j-1] + 2*h[i+1,j] + h[i+1,j+1]) - (h[i-1,j-1] + 2*h[i-1,j] + h[i-1,j+1])) / (8*cellSize)
dzdy = ((h[i-1,j+1] + 2*h[i,j+1] + h[i+1,j+1]) - (h[i-1,j-1] + 2*h[i,j-1] + h[i+1,j-1])) / (8*cellSize)
```

Use Horn if the height field is noisy or quantised, central differences if it's clean R32F.

**Slope is resolution-dependent.** The same terrain sampled at 1 m/px and 8 m/px gives
different slopes — the coarse one averages away the steep bits. A slope mask tuned at one
resolution will not transfer. State the resolution alongside any slope threshold.

## Curvature (Zevenbergen & Thorne 1987)

Fit a partial quartic to the 3×3 window. Numbering:

```
    Z1  Z2  Z3
    Z4  Z5  Z6          Z5 = centre
    Z7  Z8  Z9
```

```
L = cellSize

D = ((Z4 + Z6) / 2 - Z5) / L²                # ∂²z/∂x² / 2
E = ((Z2 + Z8) / 2 - Z5) / L²                # ∂²z/∂y² / 2
F = (-Z1 + Z3 + Z7 - Z9) / (4 * L²)          # ∂²z/∂x∂y
G = (-Z4 + Z6) / (2 * L)                     # ∂z/∂x
H = (Z2 - Z8) / (2 * L)                      # ∂z/∂y

p = G² + H²
if p < eps:  profile = plan = 0              # flat — curvature undefined, guard it
else:
    profile = -2 * (D*G² + E*H² + F*G*H) / p     # curvature ALONG the slope
    plan    =  2 * (D*H² + E*G² - F*G*H) / p     # curvature ACROSS the slope
```

**Which one you want:**

- **Profile curvature** — along the direction of steepest descent. Negative = slope steepens
  downhill (convex, ridges, cliff lips); positive = flattens (concave, valley floors, the
  base of a slope where deposition happens). This is your deposition/erosion mask.
- **Plan curvature** — perpendicular. Negative = diverging flow (ridge noses, spurs); positive
  = converging flow (hollows, channel heads). This is your **flow convergence** proxy, and
  it's much cheaper than actual flow accumulation.
- **Mean curvature** — if you just want a generic "convex vs concave" mask:

```
H_mean = ((1 + G²)*E*2 - 2*G*H*F + (1 + H²)*D*2) / (2 * pow(1 + G² + H², 1.5))
```

- **Laplacian** — the cheap one, `∇²h = (Z2 + Z4 + Z6 + Z8 - 4*Z5) / L²`. Not a true curvature
  (it isn't slope-normalised) but it's one op and it's usually what people actually want from a
  "convexity" node. If the mask is going into a blend, use this.

**Sign conventions differ between tools.** Zevenbergen & Thorne, ArcGIS, GRASS, and Houdini
do not all agree on the sign of profile curvature. Do not assume — render it once with a
diverging colour ramp over a ridge and check which way is up. Document the convention in the
node.

**Curvature is a second derivative, so it amplifies noise and quantisation brutally.** On a
quantised R16 field, curvature is essentially a picture of the quantisation staircase. Compute
it on R32F, before export. If the field is noisy, pre-smooth with a small Gaussian (σ ≈ 1 cell)
— the alternative is a mask made of speckle.

## Horizon-based ambient occlusion

For each of `N` azimuth directions, march outward and track the maximum horizon elevation
angle.

```
horizonAngle(h, p, dir, maxDist):
    maxTan = 0
    d = cellSize
    while d < maxDist:
        q = p + dir * d
        t = (sample(h, q) - h[p]) / d           # tangent of elevation angle
        maxTan = max(maxTan, t)
        d *= stepGrowth                          # ~1.1 — exponential steps, cheap and adequate
    return atan(maxTan)

ao(h, p, N, maxDist):
    v = 0
    for i in 0..N-1:
        φ = 2π * i / N
        θ = horizonAngle(h, p, (cos φ, sin φ), maxDist)
        v += cos(θ)²                             # ← see derivation below
    return 1 - v / N                             # occlusion; visibility = v/N
```

**Where `cos²θ` comes from.** Cosine-weighted visibility over the hemisphere with an up-facing
normal, with the horizon at elevation `θ` blocking everything below it:

```
V = (1/π) ∫₀^2π ∫₀^(π/2 − θ) cos·sin dθ' dφ  =  (1/2π) ∫₀^2π cos²(θ(φ)) dφ
```

so `V ≈ (1/N) Σ cos²(θᵢ)`. Fully open (θ=0) gives V=1. ✔

**HBAO (Bavoil et al. 2008) uses `1 − (1/N)Σ(sin h − sin t)`** instead, where `t` is the
tangent angle. That's a different weighting derived for screen-space use with a real normal.
For a terrain AO map baked with an up normal, the `cos²` form above is the correct integral.
If you want the AO to account for the surface normal (you usually do — a cliff face shouldn't
be treated as up-facing), use the tangent-angle form: clamp the horizon to the tangent plane
and subtract.

**Scalable version.** Naive marching is O(N · maxDist/cellSize) per cell — expensive at large
`maxDist`. **Timonen & Westerholm (2010), "Scalable Height Field Self-Shadowing"** gives an
O(1)-per-cell sweep: for each azimuth, sweep a line across the field maintaining the convex
hull of the horizon incrementally. This is the AAA-grade approach and it makes large-radius
terrain AO practical. If someone is baking AO at 4k with a 2 km radius, this is the difference
between seconds and hours.

**`maxDist` is the parameter that matters.** Small radius = a crevice map (looks like dirt).
Large radius = valleys darken and mountains catch light, which is what actually sells terrain.
Start at ~2–5% of the domain extent. `N = 8–16` azimuths is plenty for terrain; the horizon
varies smoothly.

Compute AO **before quantisation** (`08`). A second derivative it is not, but it samples height
differences over long baselines, and R16 terracing shows up as concentric rings.

## Wetness index (Beven & Kirkby 1979)

Topographic wetness index — where water lingers.

```
TWI = ln( A_specific / tan(slope) )

A_specific = A / contourWidth ≈ A / cellSize     # specific catchment area, m²/m
```

```
twi(A, slope):
    a = max(A / cellSize, cellSize)              # guard: at least one cell's worth
    s = max(slope, 0.001)                        # guard: flats → tan → 0 → ln(∞)
    return log(a / s)
```

**Both guards are mandatory.** `slope → 0` on any flat area (lake beds, floodplains — exactly
where you most want the mask) sends TWI to infinity. `A` is fine because it's at least one
cell, but only if you're in m²; in cell counts, `A=1` and `ln` of a small number goes very
negative.

TWI needs **MFD**, not D8 (`03`). TWI is a hillslope quantity and D8's parallel-lines artefact
prints straight into it as stripes. This is the canonical reason to have MFD in the graph at
all.

Typical range 3–20. Remap with a measured histogram, not an assumed range.

## Normals

```
normal = normalize( (-dzdx, -dzdy, 1) )          # for a z-up heightfield
```

Note the negation and that the z component is 1, not `cellSize` — the gradients already have
`cellSize` in their denominator, so the vector is already in world proportions. Getting this
wrong gives normals that are correct in direction but wrong in magnitude of tilt, which reads
as a terrain that's uniformly too flat or too steep under lighting and is maddening to
diagnose.

Sobel is the standard for normal maps (more robust than central differences), same kernels as
Horn's slope above.

**Bake normals from R32F, always.** This is the single clearest case for the precision rule:
a normal map derived from an R16 heightfield across a large vertical range shows visible
faceting on every gentle slope, because the derivative of a staircase is a comb.

## Selectors — masks from the analysis fields

The workhorse node of any terrain graph: take an analysis field (height, slope, aspect, curvature,
wetness) and turn it into a **`MaskField` in [0,1]** that *any* downstream node can consume. "Select
everything above 2000 m", "select slopes over 30°", "select convex ridges" — each is a one-line
remap, and the output feeds the four mask roles in `SKILL.md`'s mask semantics (effect / process /
material / boundary). This is the graph's main composition mechanism, so it has to be built right.

```
heightSel(h, lo, hi, w)  = smoothstep(lo-w, lo+w, h) * (1 - smoothstep(hi-w, hi+w, h))   # a height band
slopeSel(s, lo, hi, w)   = smoothstep(lo-w, lo+w, s) * (1 - smoothstep(hi-w, hi+w, s))   # s = tan, not degrees
aspectSel(a, dir, width) = smoothstep(cos(width), 1, dot(aspectVec(a), dir))             # faces a direction
curveSel(c, lo, hi, w)   = smoothstep(lo-w, lo+w, c) ...        # profile/plan curvature: ridges vs hollows
```

Four rules make a selector correct rather than an obvious tell:

- **Thresholds carry world units, never [0,1].** "Above 2000 m" is `2000`, in metres — not `0.6` of
  a normalised height. The moment a selector reasons in a normalised range it breaks when the
  terrain's min/max change (the `normalize` defect, `10`), and it stops tiling. Slope thresholds are
  `tan` (`slope > tan(30°)`), and **slope is resolution-dependent** (above), so state the resolution
  beside any slope selector or it won't transfer.
- **Soft edges, always.** A hard `h > 2000` gives a mathematically perfect contour that nothing in
  nature has. Use `smoothstep` over a band `w`, and **noise-perturb the threshold** —
  `smoothstep(t-w, t+w, field + noiseAmp*fbm(p))` — the single cheapest step from "procedural" to
  "photographed" (same rule as *Masks → materials*, below).
- **Compose with min/max = AND/OR.** `A AND B = A*B` (or `min`); `A OR B = max(A,B)`; `NOT A = 1−A`.
  "Grass on gentle, wet, low ground" is `slopeSel * wetSel * heightSel`. Use smooth `min`/`max`
  (`10`) when the combined mask itself drives geometry, so the mask has no crease lines.
- **Selectors are `06`, so they run after the last height write.** A slope selector computed before
  erosion selects slopes that no longer exist (the ordering rule at the top). The one exception is a
  selector used as an *input* to erosion (slope-dependent `K`) — name it so nobody wires it into the
  material graph by accident.

**N-tier caveat.** "Select Height", "Selective", "Slope", "Convexity" and friends in Gaea / World
Machine / Houdini are all exactly this — a threshold-and-smoothstep over one analysis field. The
node is branding; the algorithm is one line. When someone asks what a tool's selector "really does",
this is the answer.

## Masks → materials

Derivation order: `height → analysis → masks → materials → scatter`. And what each mask *selects*
is a material in the full sense of `18` — a property bundle (erodibility, repose, permeability,
appearance, stack role), not just a splat colour.

```
snowMask   = smoothstep(snowLine - w, snowLine + w, height)
           * (1 - smoothstep(tan(40°), tan(50°), slope))       # snow doesn't stick to cliffs
           * (0.5 + 0.5 * northness)                            # aspect: shaded slopes hold snow
           * noiseBreakup

rockMask   = smoothstep(tan(35°), tan(45°), slope)              # steep = exposed rock
           + curvatureConvex * 0.3                              # ridges are scoured
           - regolithDepth * k                                   # unless covered

sandMask   = (1 - smoothstep(tan(5°), tan(15°), slope))         # flat only
           * smoothstep(low, high, deposition)                   # where sediment landed
           * (1 - riverMask)

grassMask  = (1 - rockMask) * (1 - snowMask) * (1 - sandMask)
           * smoothstep(twiLow, twiHigh, wetness)                # needs moisture
           * (1 - smoothstep(treeLine - w, treeLine + w, height))

riverMask  = smoothstep(A_channel * 0.5, A_channel, A)           # A from 03, in m²
```

**Principles:**

- **Every hard threshold needs noise breakup.** A `slope > 0.7` mask has a mathematically
  perfect edge, and nothing in nature does. Multiply the threshold by low-amplitude noise:
  `smoothstep(t - w, t + w, slope + noiseAmp * fbm(p))`. This is nearly free and it's the
  difference between "procedural" and "photographed".
- **Masks must partition.** If your masks sum to 1.3 in places, the splatmap normalisation
  will silently rescale and your carefully tuned rock will be 30% weaker on steep slopes than
  you specified. Either build them as an explicit priority stack (snow beats rock beats
  grass — each subsequent mask multiplied by `(1 − Σ previous)`), or normalise explicitly and
  know that you did.
- **Aspect matters and is cheap.** `northness = -cos(aspect)` in the northern hemisphere.
  Snow lingers on north faces, vegetation differs between north and south slopes. One term,
  large payoff, and it's the kind of thing that makes people say the terrain "feels real"
  without knowing why.
- **Use `deposition`, not just slope, for sediment materials.** If your erosion model tracks
  where it deposited (all three in `04` can), that field is far better than any slope-based
  proxy — it puts sand where sand actually went.
