# s18-foam-edge-after

**1:1 crop of the foam edge, the realisation drawn.** Same camera, same bay,
same build, same crop box as `s18-foam-edge-before`. One render sample per
image pixel.

**Provenance: measured.** Rendered by `foam_evidence.py` with
`foam_realise = True` and `foam_roller = True`, the shipping values.

**What is different, and every part of it is a computed quantity.** The
coverage is now ONE REALISATION of the Boolean model whose void probability is
`coverage(m)`, drawn by `beach_foam.boolean_indicator`: a homogeneous
dominating Poisson germ field with per-germ marks thinned at the query point,
which reproduces `1 - exp(-m)` EXACTLY at every point. The grain size is the
local depth through `grain_radius` -- `r_g = d/2`, on the depth-limited
macroturbulence argument -- and the crossover to the mean is the pixel
footprint the renderer already computes for the slope band-limit. The deck's
source is `deck_source`, the transform's own dissipation lagged shoreward by
`ROLLER_LAG` local wavelengths. NOTHING HERE IS A NOISE FUNCTION: the germ
positions are the sampler of a stated point process, and the suite row
"realisation mean against 1 - exp(-m)" is what holds them to it.

**Display-referred**, through the same encode as the BEFORE half, for the same
reason.

**Measured on this crop, leftmost 500 px:** `l/W` = 0.62 %, acf 1/e =
3.12 px, run q90 = 25 px, gap median = 10 px,
against the photographs' 0.3-0.8 % and 8-52 px.
