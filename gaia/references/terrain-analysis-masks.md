---
type: Technique
title: Terrain analysis and masks — deriving fields from height
description: "Slope, curvature, occlusion and wetness computed the way that survives a resolution change, and the selector stack that turns them into materials."
tags: [generation, analysis, masks, curvature, materials, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: zevenbergen1987, tier: P, locator: "the 3x3 partial-quartic fit, and the profile and plan curvature expressions" }
  - { id: horn1981, tier: P, locator: "the Sobel-weighted 3x3 slope and aspect estimator" }
  - { id: beven1979, tier: P, locator: "the topographic index ln(a / tan beta)" }
  - { id: timonen2010, tier: P, locator: "the per-azimuth sweep with an incremental convex hull, O(1) per cell" }
  - { id: bavoil2008, tier: F, locator: "the sin(h) - sin(t) horizon weighting" }
  - { id: weiss2001, tier: F, locator: "the topographic position index at multiple radii" }
  - { id: he2010, tier: P, locator: "the local linear model with a, b from box filters; eps as the variance threshold" }
  - { id: tomasi1998, tier: P, locator: "§2.1 Example: the Gaussian Case — the product of the CLOSENESS function c(xi,x) and the SIMILARITY function s(phi,f), both Gaussian. Note the paper's own words: searching it for 'spatial' and 'range' will not find this" }
---
# Terrain analysis and masks — deriving fields from height

Analysis describes a terrain. Masks turn that description into material coverage. Both are cheap;
both are wrong in ways that look fine, which is what this document is about.

## Use this

**Run every analysis node downstream of the last node that modifies height.** Central differences
for slope on a clean R32F field, [horn1981] if it is noisy or quantised; the quartic fit
[zevenbergen1987] for curvature; the sweep [timonen2010] for occlusion; and selectors built as a
**priority stack in world units with noise-broken thresholds**, so coverage sums to ≤ 1 by
construction.

⚠️ The ordering rule is the second-commonest defect in a terrain graph, after unhandled
depressions, and it is harder to see: a snow mask built on pre-erosion slope paints snow onto the
walls of valleys that erosion has since cut, and the output looks superficially fine — the
materials are just subtly, inexplicably wrong. The one legitimate exception is analysis used as an
*input* to erosion, such as slope-dependent erodibility. Name it differently so nobody wires it
into the material graph by accident.

## Slope is a tangent; aspect points downhill

```
slope  = sqrt(dzdx² + dzdy²)          # tan θ — rise over run, dimensionless
aspect = atan2(-dzdy, -dzdx)          # DOWNSLOPE direction
```

**Keep slope as `tan`.** Every downstream comparison is then a float compare against `tan(35°)`,
and it composes directly with the repose-angle table in `thermal-and-aeolian-erosion.md`. Convert
to degrees for UI only.

⚠️ **Never write `sin(slope)`, `tan(slope)` or `cos(slope)`.** They apply a trig function to a
ratio. `θ = atan(slope)` recovers the angle; `sin θ = slope / sqrt(1 + slope²)` stays in the
tangent. A *threshold* is the other way round — `tan(35°)` is right, because there the angle is the
literal. Feeding a tangent into the infinite-slope criterion understates the factor of safety by up
to a third, quietly.

**The negations in `aspect` are the point.** The raw gradient points uphill; aspect everywhere else
in terrain work means steepest descent — the way the slope faces, the way water leaves. Use the
uphill form and every orientation-driven mask flips 180°: snow on the sunny side, rain shadow on
the windward flank, and nothing wrong enough to catch by eye.

**Slope is resolution-dependent.** The same terrain at 1 m/px and 8 m/px gives different slopes,
because the coarse sampling averages the steep bits away. State the resolution beside any slope
threshold, or it will not transfer.

## Curvature, and what each one selects

The quartic fit over the 3×3 window [zevenbergen1987] gives both curvatures from the same five
coefficients. Label the window `Z1 Z2 Z3 / Z4 Z5 Z6 / Z7 Z8 Z9`, rows north to south, `L` the cell
size:

```
D = ((Z4 + Z6)/2 - Z5) / L²        # = Zxx / 2      G = (Z6 - Z4) / (2L)     # = dz/dx
E = ((Z2 + Z8)/2 - Z5) / L²        # = Zyy / 2      H = (Z2 - Z8) / (2L)     # = dz/dy, +y NORTH
F = (Z3 + Z7 - Z1 - Z9) / (4L²)    # = Zxy

p = G² + H²                                    # squared slope
profile = 2*(D*G² + F*G*H + E*H²) / p          # d²z/ds² along steepest descent
plan    = 2*(D*H² - F*G*H + E*G²) / p          # contour curvature × |grad z|
```

The fit has nine coefficients; the other four (the `x²y²`, `x²y`, `xy²` terms, and the constant
`Z5`) cancel out of both curvatures — which is what "the same five" means. `G` and `H` are the
first derivatives, so the guard below is a guard on slope.

**Both expressions are checkable in closed form, and worth checking.** They are exact to twelve
digits on any quadratic surface, and second-order on anything else: on a Gaussian hill, halving `L`
quarters the error against the analytic `f''(r)` and `f'(r)/r`. The sharpest single test is that
`plan / sqrt(p)` is the contour's own curvature — on a radially symmetric hill it reproduces `1/r`
to seven digits at every radius, so a wrong sign or a dropped `L` shows up immediately.

- **Profile** (along steepest descent) — negative where the slope steepens downhill (ridges, cliff
  lips), positive where it flattens (valley floors, slope bases). This is the erosion/deposition
  mask.
- **Plan** (across it) — negative on diverging spurs, positive in converging hollows. This is the
  **flow-convergence proxy**, and it is far cheaper than real flow accumulation.
- **Laplacian**, `(Z2 + Z4 + Z6 + Z8 − 4·Z5)/L²` — one op, not slope-normalised, and usually what
  people actually want from a "convexity" node. If the mask feeds a blend, use this.

Guard `p < eps`: curvature is undefined on a flat. `p` is a *squared slope*, so like every slope
threshold in this document the value moves with the resolution — it is not a length.

⚠️ **Sign conventions differ between tools** — ArcGIS, GRASS and Houdini do not all agree on the
sign of profile curvature, and neither the block above nor any of them is canonical. The signs
printed above are the ones that match the bullets above them, verified on parabolic ridge and
valley surfaces: profile −0.0027 and plan −0.037 on the ridge, exactly the opposites in the valley.
Render it once over a known ridge with a diverging ramp and write the convention into the node.

**Curvature is a second derivative, so it amplifies quantisation brutally.** On an R16 field it is
a picture of the staircase. Compute it on R32F before export, and pre-smooth with σ ≈ 1 cell if the
field is noisy, or the mask is speckle.

## Occlusion: the cos² integral, and the sweep

For `N` azimuths, march out and track the maximum horizon elevation angle, then

```
visibility = (1/N) Σ cos²(θᵢ)          # cosine-weighted hemisphere, up normal, horizon at θ
```

which is the correct integral for a **baked terrain AO map with an up normal**, and gives 1 for
fully open ground. HBAO [bavoil2008] — a SIGGRAPH talk rather than a peer-reviewed paper, graded
`F` like every other talk in this bibliography — uses `sin h − sin t` instead; that is a
screen-space weighting derived for a real per-pixel normal, and substituting it into a baked
terrain map is a different quantity.

**`maxDist` is the parameter that matters.** A small radius gives a crevice map that reads as dirt;
a large radius darkens valleys and lets mountains catch light, which is what actually sells
terrain. Start at 2–5% of the domain extent, `N = 8–16` azimuths — the horizon varies smoothly.

Naive marching is O(N · maxDist/cellSize) per cell. [timonen2010] sweeps each azimuth across the
field maintaining the horizon's convex hull incrementally, O(1) per cell: the difference between
seconds and hours for a 4k bake at kilometre radius. It is also the substrate for insolation —
horizon angle depends on azimuth, not on the sun, so a precomputed per-azimuth horizon makes every
sun sample a table lookup. **Insolation is not AO**: a pole-facing wall can be wide open to the sky
and never see the sun, so substituting one for the other puts melt in shaded ravines.

## Wetness

`TWI = ln(A_specific / slope)` [beven1979], with two mandatory guards: `slope` clamped to ~0.001,
because flats — lake beds, floodplains, exactly where the mask is wanted — send it to infinity; and
`A_specific` in m²/m, at least one cell's worth.

The paper writes it as `ln(a / tan β)` for a slope **angle** `β`. Here `slope` is already the
tangent, so the division is by `slope` itself; `tan(slope)` biases TWI low by 0.08–0.44 nats across
25–45°, which silently moves every downstream threshold.

**TWI needs multi-receiver routing, not D8** (`flow-routing.md`). It is a hillslope quantity, and
D8's parallel-lines artefact prints straight into it as stripes. This is the canonical reason to
have MFD in the graph at all.

## Selectors, and the stack that keeps them honest

```
heightSel(h, lo, hi, w) = smoothstep(lo-w, lo+w, h) * (1 - smoothstep(hi-w, hi+w, h))
slopeSel(s, lo, hi, w)  = ...                      # s is tan, not degrees
aspectSel(a, dir, wid)  = smoothstep(cos(wid), 1, dot(aspectVec(a), dir))
```

Four rules make a selector correct rather than a tell:

- **Thresholds carry world units, never a normalised range.** "Above 2000 m" is `2000`. The moment
  a selector reasons in [0,1] it breaks when the terrain's min/max change and it stops tiling —
  the same defect as normalising a heightfield mid-graph.
- **Soft edges, always, and noise-perturb the threshold**:
  `smoothstep(t-w, t+w, field + noiseAmp·fbm(p))`. A hard `h > 2000` is a mathematically perfect
  contour, and nothing in nature has one. This is the cheapest single step from "procedural" to
  "photographed".
- **Compose with products and maxima**: AND is `a*b` or `min`, OR is `max`, NOT is `1−a`. Use the
  smooth forms when the combined mask drives geometry, so it has no crease lines.
- **Build materials as a priority stack**, each mask multiplied by `(1 − Σ previous)`. That yields
  `Σ ≤ 1` by construction; the shortfall is the bare base material. Assert `Σ ≤ 1` at the mask
  fan-in, and `Σ = 1` at the point where you close the stack by emitting the base as its own
  channel. Over-subscription is a real bug whose visibility depends entirely on the compositor
  downstream — an ordered over-composite hides it completely, a base-less weighted sum clips it to
  white — which is exactly why the assertion belongs at the producer.

Two details worth the line each: **`northness = dot(aspectVec(aspect), northDir)`** costs one term
and is what makes people say terrain "feels real" — but on a standard north-up raster the row index
increases southward, so it is `−sin(aspect)`; the naive `+sin` silently moves snow to the sunny
side. And **use the erosion's deposition field, not a slope proxy, for sediment materials** — it
puts sand where sand actually went.

**Loose material has depth.** Snow, sand and scree fill the hollows of the rock beneath, so the
shaded surface is smoother than the bedrock. `depositFill(h, r) = max(closing(h, r) − h, 0)` gives
that pile depth for free: deep in hollows, ~0 on ridges.

**What it beats.** *[horn1981] for everything* — more robust on noisy or quantised data, slightly
smoothed on clean R32F; pick by input quality, not by habit. *Topographic position index*
[weiss2001] — no peer review; a multi-radius neighbourhood-mean difference that classifies
ridge/slope/valley, useful, but curvature already gives the same signal with a defensible
derivation. *Bilateral filtering* [tomasi1998] for smoothing a mask — O(r²), not separable, and it
reverses gradients near strong edges; the **guided filter** [he2010] is O(1) per cell at any
radius, has no gradient reversal, and takes a *separate guide*, so you can smooth a material mask
with the **height** as guide and have the mask edges snap to terrain features. *Gaussian blur* —
smooths the ridges and cliffs you wanted to keep. *Morphological closing as a depression fill* — it
fills by structuring-element size rather than hydrological connectivity, so it drowns small real
basins and misses wide shallow ones; it looks fine and routes flow wrong.

**Time budget.** Slope, aspect, normals, Laplacian and every selector over them are single-pass
3×3 stencils — per-frame operations, safe to compute in a shader from a sampled heightfield.
Curvature is too, with the caveat that it wants R32F input, which a runtime often does not have.
Everything with a long baseline — horizon occlusion, insolation, TWI and anything consuming
drainage area — is a bake: even the O(1) sweep is a whole-field sequential pass per azimuth, and
the terrain is not changing per frame. The line is the baseline length, not the arithmetic.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Materials subtly wrong everywhere, geometry fine | Analysis computed before the last height write | Move it downstream of erosion |
| Snow on sunny faces; rain shadow on the wrong flank | Aspect taken uphill, or `+sin` northness on a north-up raster | Negate the gradient; `−sin(aspect)` |
| A slope mask that was right at 1 m/px and wrong at 8 | Slope is resolution-dependent | State the resolution with the threshold; re-tune per LOD |
| Factor of safety, TWI or wetness biased low | `tan(slope)` applied to a value that is already a tangent | Divide by `slope` bare |
| Curvature mask is speckle, or shows concentric rings | Second derivative of a quantised field | Compute on R32F, pre-smooth σ ≈ 1 cell |
| Curvature mask selects ridges where it should select valleys | Sign convention differs from the tool you learned it in | Render over a known ridge and document the convention |
| AO reads as dirt in the crevices, mountains unlit | `maxDist` far too small | 2–5% of domain extent |
| AO bake takes hours at 4k | Naive per-cell marching | The sweep [timonen2010] |
| Melt appearing in shaded ravines that are open overhead | AO substituted for insolation | Integrate over the sun's arc, reusing the horizon maps |
| TWI is infinite on floodplains | `slope → 0` | Clamp `slope`, and `A_specific` to one cell |
| Wetness in one-cell stripes with dry gaps | D8 used for a hillslope field | Route MFD |
| Perfect contour lines along a mask edge | Hard threshold, no noise breakup | `smoothstep` over a band on a noise-perturbed field |
| A mask that breaks when the terrain's height range changes | Threshold in a normalised range | World units |
| Splat weights clipping to white, or a material 30% weak | Coverage over-subscribed; `Σ > 1` | Priority stack with `(1 − Σ previous)`; assert at the fan-in |
