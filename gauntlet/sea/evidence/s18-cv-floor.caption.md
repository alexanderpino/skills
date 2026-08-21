# s18-cv-floor — the granularity is a consequence, and this is the derivation

The companion to `s18-glitter-1to1`, and the reason that figure is allowed to exist. A render can be
made granular by a noise texture in ten minutes; standing ruling 3 says the structure has to come
from the derived spectrum or it does not ship. **This figure is the check that it did.**

## Left — the coefficient of variation the partition *requires*

Split the facet slope into what a pixel's footprint resolves and what it does not. They are disjoint
bands of one spectrum, so they are independent, and at the path's centre the radiance goes as
`p_sub(z* − z_res)` with `z_res` drawn. Writing `ρ = r/a` for the ratio of resolved to residual
variance in each wind axis, and using `E[exp(−t z²)] = (1 + 2tr)^{−1/2}`:

```
CV²  =  (1 + ρ_u)(1 + ρ_c) / √((1 + 2ρ_u)(1 + 2ρ_c))  −  1
```

**Every point on the black curve is that expression**, with `ρ` obtained by sampling
`SlopeRealisation` on 40 000 world points at that footprint and reading the variance it carried.
Nothing is fitted, nothing is a photograph, and there is no free parameter anywhere in it. The
closed form was checked against 4 × 10⁶ Monte Carlo draws and agrees to four decimals; that check is
a suite row, not a claim in this caption.

**Read the left end and the right end together.** At a 5 cm footprint the partition *requires*
CV ≈ 1.08; at 20 m it requires 0.004. The curve going to zero is not a failure of the model — it is
the ensemble mean being the **correct** answer for a pixel the size of the ensemble. Waves 4–17 sat
at the bottom of this curve at every distance, including 10 cm.

**The dots are frame K's own row-bands**, measured scene-linear off the radiance buffer, plotted at
each band's 90th-percentile footprint — the same convention the guard row uses, because the floor a
band must clear is set by its *coarsest* pixels. Orange is the realisation on, blue is waves 4–17.

⚠️ **The dots are not expected to sit *on* the curve, and the guard does not ask them to.** The
render also carries the swell's own slope and a real spread of `z*` across the strip's width, both of
which add variance the closed form does not count. The suite therefore subtracts the two frames **in
quadrature** — the variance the realisation *added*, over what the same strip of the same frame had
without it — and requires that to clear the floor by a factor between 1 and 6. The upper bound is
the important half: granularity far above the floor would mean it is arriving from somewhere the
spectrum does not account for, which is the failure this round was one step away from.

The coarsest band, near the horizon, is where the floor drops below 0.05 and stops saying anything.
The suite names that band as vacuous and excludes it, rather than counting `0 ≥ 0` as a pass.

## Right — where the split actually is, and why it moves so slowly

The share of the wind sea's slope variance a pixel can draw, sampled (solid) against `(R3)`'s
sharp-cutoff form `ln(k_res/k_lo)/ln(k_hi/k_lo)` (dashed). **The split is logarithmic**, which is
what a `k⁻⁴` saturation range means: equal slope variance per octave. Halving the footprint buys one
octave, and one octave is 1/7.5 of the whole range at this wind.

The sampled curve sits **8% under** the sharp-cutoff form across the resolvable range, and that gap
is the true filter rather than an error: a box average is a `sinc`, which lets a little through above
`k = π/L` and takes a lot away below it, and on a spectrum with equal variance per octave the second
wins. Use the dashed line to reason about scales and the solid one to budget.

**The blue dashed line is what the resolved geometry carried before this wave** — the swell, and
nothing else, at 8% of the wind sea's slope variance. It is flat because a swell 90 m long is
resolved by every pixel in the frame; the whole of the curve above it is the band that had no
representation in the surface at all.

## Provenance

`D` for the closed form and the arithmetic; `P` for Cox & Munk's two variances and for the
Pierson–Moskowitz peak that sets `k_lo`; `P (attribution)` for ECKV, whose agreement with the flat
Phillips model at every one of these footprints is wave 17's result and the reason this figure may
use the cheaper spectrum. `k_hi` is derived, not declared: the gravity–capillary wavenumber of
minimum phase speed, `√(ρg/σ)` = 372 rad/m.

Scene-linear throughout. Nothing in this figure is read back out of any image.

*Drawn by `terrain-renderer/reference-impl/glitter_evidence.py`, which calls `beach_optics`'s
shipped `SlopeRealisation` and the suite's own `_cv_partition` — the same objects the render and the
guard use, not a re-derivation.*
