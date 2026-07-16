# Noise

Contents: [Choosing](#choosing) · [Perlin](#perlin-1985--improved-perlin-2002) ·
[Simplex](#simplex-noise) · [OpenSimplex2](#opensimplex2) · [Value](#value-noise) ·
[Worley/Voronoi](#worley--voronoi) · [FBM](#fbm) · [Ridged](#ridged-multifractal) ·
[Multifractal](#hybrid-multifractal) · [Domain warp](#domain-warp) · [Curl](#curl-noise) ·
[Terrain pitfalls](#terrain-specific-pitfalls)

## Choosing

| Want | Use |
|---|---|
| 2D heightfield base, CPU | Improved Perlin or OpenSimplex2 |
| 3D/4D (animated, or 3D density for caves/overhangs) | OpenSimplex2 or Simplex |
| Cell/crack structure, rocks, dry lakebeds | Worley F2−F1 |
| Mountains with sharp ridgelines | Ridged multifractal |
| Varied relief (plains next to mountains) | Hybrid multifractal |
| Believable meander/flow-like structure without simulation | Domain warp |

Noise is an **initial condition**, not a landform. It has no memory of water, so it cannot
produce a drainage network. Ridged FBM makes ridges that *look* like mountains at a glance and
fail immediately under a flow accumulation check, because the "valleys" don't connect.

## Perlin (1985) / Improved Perlin (2002)

Gradient noise on an integer lattice. Value at a lattice point is always 0 — this matters,
see pitfalls.

```
perlin2(x, y):
    X = floor(x) & 255;  Y = floor(y) & 255
    xf = x - floor(x);   yf = y - floor(y)
    u = fade(xf);        v = fade(yf)

    aa = P[P[X  ] + Y  ];  ab = P[P[X  ] + Y+1]
    ba = P[P[X+1] + Y  ];  bb = P[P[X+1] + Y+1]

    x1 = lerp(grad(aa, xf,   yf  ), grad(ba, xf-1, yf  ), u)
    x2 = lerp(grad(ab, xf,   yf-1), grad(bb, xf-1, yf-1), u)
    return lerp(x1, x2, v)                       // range ~[-1, 1]
```

**Fade function.** Original 1985: `3t² − 2t³`. Improved 2002: `6t⁵ − 15t⁴ + 10t³`.
The improvement matters: the original's second derivative is non-zero at the lattice points,
which produces visible creases along the grid lines under any lighting that uses the second
derivative — i.e. under curvature-based masks and under normal maps. **Always use the quintic
fade for terrain.** The cost difference is two multiplies.

**Gradients.** The 2002 improvement replaced random gradients with the 12 vectors pointing to
the edge midpoints of a cube: `(±1,±1,0), (±1,0,±1), (0,±1,±1)`. This removes the directional
bias of random gradients and lets `grad()` be implemented with adds only, no multiplies:

```
grad(hash, x, y, z):
    h = hash & 15
    u = h < 8 ? x : y
    v = h < 4 ? y : (h == 12 || h == 14 ? x : z)
    return ((h & 1) ? -u : u) + ((h & 2) ? -v : v)
```

**Permutation table.** `P` is a 256-entry shuffle of 0..255, duplicated to 512 to avoid
bounds checks. Seeding = shuffling P with the seed. **Do not** seed by offsetting the input
coordinates — that gives correlated "seeds" that are just translations of one pattern.

**Range.** 2D Perlin's theoretical range is ±√(N/4) = ±0.707 for 2D, ±0.866 for 3D, but the
practical distribution is much tighter and roughly Gaussian. Never assume [−1,1] is filled;
if you normalise by the theoretical max you will get a washed-out, low-contrast field.
Measure the actual range for your octave stack.

## Simplex noise

Simplex tessellates the domain into simplices (triangles in 2D, tetrahedra in 3D) instead of
hypercubes, so the corner count is N+1 instead of 2^N. In 2D that is 3 corners vs 4 — a
modest win. In 4D it is 5 vs 16 — a large one. **For 2D heightfields Simplex is not
meaningfully faster than Perlin**; the reason to use it is the lack of axis-aligned artefacts.

```
F2 = 0.5 * (sqrt(3) - 1)        // ≈ 0.3660254   skew
G2 = (3 - sqrt(3)) / 6          // ≈ 0.2113249   unskew

simplex2(x, y):
    s = (x + y) * F2                     // skew input space to lattice
    i = floor(x + s);  j = floor(y + s)
    t = (i + j) * G2
    x0 = x - (i - t);  y0 = y - (j - t)  // displacement from cell origin

    if x0 > y0: i1, j1 = 1, 0            // lower triangle
    else:       i1, j1 = 0, 1            // upper triangle

    x1 = x0 - i1 + G2;      y1 = y0 - j1 + G2
    x2 = x0 - 1 + 2*G2;     y2 = y0 - 1 + 2*G2

    n = 0
    for (dx, dy, gi) in [(x0,y0,hash(i,j)), (x1,y1,hash(i+i1,j+j1)), (x2,y2,hash(i+1,j+1))]:
        t = 0.5 - dx*dx - dy*dy
        if t > 0:
            t *= t
            n += t * t * dot(grad2[gi & 7], dx, dy)
    return 70.0 * n                      // 70 scales to ≈[-1, 1]
```

The `0.5` is the squared radius of the attenuation kernel. Some implementations use `0.6`,
which produces a slightly different (and non-standard) look with visible bumps — 0.5 is
Gustavson's. The `70` is the empirical normalisation for 2D with the 8-gradient set; it
changes if you change the gradient set or the radius.

**Patent note.** Perlin's US 6,867,776 covered simplex-type gradient noise in 3D and higher.
It expired in January 2022, so Simplex is now unencumbered. OpenSimplex exists because of that
patent; it is still worth using on merit, but "avoiding the patent" is no longer a reason.

## OpenSimplex2

KdotJPG's redesign. Two variants:

- **OpenSimplex2 (Fast)** — uses the same simplex lattice but with a rotated/re-oriented
  lattice and a different kernel; visually similar to Simplex, faster, no directional bias.
- **OpenSimplex2S (Smooth)** — larger kernel radius, smoother, closer to the original
  OpenSimplex look. Slower. Better for terrain where you don't want kernel bumps showing
  through under high-contrast remapping.

The key trick in both is **lattice rotation**: for 3D noise sampled on a 2D plane (the common
terrain case — you sample `noise3(x, y, 0)` to get an animatable or layered field), the naive
simplex lattice has a face aligned with the sampling plane, producing obvious repeated
structure. OpenSimplex2 offers `noise3_ImproveXY` / `noise3_XZBeforeY` variants that rotate
the lattice so the sampling plane cuts it obliquely.

**If you sample 3D noise on an axis-aligned plane, you must use a lattice-rotated variant, or
you will get visible diagonal banding.** This catches people constantly.

Don't reimplement OpenSimplex2 from memory — the lattice and gradient tables are long and the
reference implementation (public domain) is short. Specify "use the reference OpenSimplex2
implementation, `noise2` or `noise3_ImproveXY`" and move on.

## Value noise

Interpolate hashed random values at lattice points rather than gradients. Cheaper, but the
extrema sit *on* the lattice points, so the grid is far more visible than in Perlin. Usable
as a cheap component inside an FBM stack where the grid is masked by other octaves; not
usable alone for terrain.

## Worley / Voronoi

```
worley2(x, y):
    cell = floor(p)
    f1 = f2 = INF
    for each of 9 neighbouring cells c:
        featurePoint = c + hash2(c)          // 1 point per cell (Worley's variant: Poisson count)
        d = distance(p, featurePoint)
        if d < f1: f2 = f1; f1 = d
        elif d < f2: f2 = d
    return f1                                 // or f2 - f1, etc.
```

Useful outputs:
- `F1` — cellular blobs. Good for boulder fields.
- `F2 − F1` — ridges at cell boundaries, zero at boundaries. This is the crack/mud-flat one.
- `1 − F1` — inverted cones. Reasonable crater fields.

Distance metric changes character entirely: Euclidean → organic, Manhattan → blocky/urban,
Chebyshev → square cells. For terrain, Euclidean unless you are making something artificial.

Worley (1996) specifies a Poisson-distributed number of feature points per cell; the
one-point-per-cell simplification is near-universal in graphics and looks fine, but it makes
the cells more regular than true Worley.

## Gabor noise (Lagae et al. 2009)

*Procedural Noise using Sparse Gabor Convolution*, ACM TOG 28(3). Sparse convolution of a
Poisson point process with a Gabor kernel — a Gaussian envelope times a sinusoid.

```
gaborKernel(x, y, K, a, F0, omega0):
    return K * exp(-π * a² * (x² + y²)) * cos(2π * F0 * (x*cos(omega0) + y*sin(omega0)))

gaborNoise(p, ...):
    sum = 0
    for each cell c in the 3x3 neighbourhood of p:
        seed = hash(c)
        n = poissonCount(seed, impulseDensity)            # number of impulses in this cell
        for i in 0..n-1:
            xi = randomPointIn(c, seed, i)
            w  = randomWeight(seed, i)                     # ±1
            d  = (p - xi) / kernelRadius
            sum += w * gaborKernel(d.x, d.y, K, a, F0, omega0(seed, i))
    return sum
```

**Why it exists:** it gives you **direct, local control of the power spectrum**. `F0` sets the
frequency, `a` sets the bandwidth, `omega0` sets the orientation — and all three can vary
spatially. Perlin/Simplex give you one fixed spectrum per octave and no orientation control at
all.

**For terrain that means anisotropy.** Set `omega0` from a direction field and you get noise
that's stretched along structure — ridges aligned to a tectonic trend, scour aligned to flow,
dune ripples aligned to wind. Isotropic noise cannot do that, and faking it by stretching the
sample coordinates stretches the *feature size* too, which is the wrong effect.

**Cost:** expensive — many kernel evaluations per sample. It is not a base-terrain noise. Use it
where the anisotropy earns its keep: detail layers, material patterns, ripple fields. The
`setup/evaluate` split in the paper (precompute the spectrum, evaluate cheaply) is what makes it
practical.

Lagae's **2010 survey** (*A Survey of Procedural Noise Functions*, CGF 29(8)) is the best single
source for the whole noise landscape and worth reading before choosing anything.

## Wavelet noise (Cook & DeRose 2005)

*Wavelet Noise*, ACM TOG 24(3). Solves a problem the others don't acknowledge: **Perlin noise is
not band-limited.** Its spectrum leaks, so when you minify it you get aliasing, and when you
magnify it you get detail that shouldn't be there. Wavelet noise constructs a genuinely
band-limited tile by downsampling and upsampling a random image and taking the difference.

For terrain this matters mostly at **LOD boundaries**: a non-band-limited FBM shimmers as the
camera moves because octaves near the Nyquist limit alias. If you're generating noise
per-frame at varying LOD, band-limiting is worth it. For a baked heightfield, the export
resolution has already band-limited everything and this is moot.

The practical takeaway if you're not implementing it: **drop octaves whose wavelength falls
below ~2 cells** (see FBM below). That's the poor-man's band-limiting and it's most of the
benefit.

**Sparse convolution noise** — **Lewis 1989**, *Algorithms for Solid Noise Synthesis*, SIGGRAPH
— is the ancestor of both Gabor and wavelet noise. Convolve a Poisson point process with an
arbitrary kernel. Cite Lewis if the question is about the family; cite Lagae for Gabor
specifically.

## Diamond-square / midpoint displacement

**Fournier, Fussell & Carpenter 1982**, *Computer Rendering of Stochastic Models*, CACM 25(6).
The original procedural terrain algorithm, and the reason a generation of programmers thinks
terrain is a solved problem.

```
diamondSquare(h, size, roughness):                  # size = 2^n + 1
    h[corners] = random()
    step = size - 1
    scale = 1.0
    while step > 1:
        half = step / 2
        # diamond: centre of each square = mean of 4 corners + noise
        for y, x in grid(step):
            h[y+half][x+half] = mean(4 corners) + rand(-scale, scale)
        # square: centre of each diamond = mean of 4 edge-adjacent points + noise
        for each diamond centre:
            h[...] = mean(available neighbours) + rand(-scale, scale)
        step = half
        scale *= pow(2, -roughness)                  # roughness = Hurst exponent H
    return h
```

**Do not use it.** Two structural defects, both well known and neither fixable:

1. **Visible axis-aligned creases.** The diamond and square passes use different neighbour sets,
   so the variance is anisotropic and the grid axes print through as faint ridges. It's the
   signature look of 1990s terrain.
2. **It is not a continuous function.** `h(x,y)` doesn't exist — only the grid does. You cannot
   sample it at an arbitrary point, cannot evaluate it lazily per-tile, cannot change resolution
   without regenerating everything, and cannot make it tile. FBM over Perlin/OpenSimplex2 gives
   you all of that for the same cost.

It is here because it will come up, it has a real paper, and the honest answer is "yes, that's
the 1982 original, and it's obsolete for a reason". Its one remaining virtue is that it's
`O(n²)` total with no per-sample cost — irrelevant on any hardware built this century.

## FBM

```
fbm(p, octaves, lacunarity=2.0, gain=0.5):
    sum = 0;  amp = 1.0;  freq = 1.0;  norm = 0
    for i in 0..octaves-1:
        sum  += amp * noise(p * freq)
        norm += amp
        freq *= lacunarity
        amp  *= gain
    return sum / norm          // normalise, else amplitude depends on octave count
```

- **Lacunarity** ≈ 2.0. Exactly 2.0 makes octaves align on the lattice, which can produce
  faint reinforcement artefacts; 1.97 or 2.01 breaks the alignment for free.
- **Gain** (persistence) ≈ 0.5. Relates to fractal dimension: `gain = 2^(-H)` where H is the
  Hurst exponent. H=1 (gain 0.5) is the standard "smooth-ish" terrain; H=0.5 (gain ≈0.707)
  is rougher, more like real eroded topography at small scales.
- **Octave count.** Stop when the octave's wavelength drops below ~2 cells — beyond that you
  are just adding aliasing. `octaves = log2(resolution / baseWavelengthInCells)`.
  Adding octaves "for more detail" past the Nyquist limit is pure noise in the pejorative
  sense and it will shimmer under LOD.
- **Offset each octave** by a large per-octave vector, else all octaves have a zero crossing
  at the same lattice points and you get a faint grid of pinch points.

## Ridged multifractal

Musgrave — the 1993 Yale thesis and his *Texturing & Modeling* chapters (`00`; the 1989 SIGGRAPH
paper is the erosion one, not this). The naive version:

```
ridged(p, octaves, lacunarity=2.0, gain=0.5):
    sum = 0; amp = 0.5; freq = 1.0
    for i in 0..octaves-1:
        n = 1.0 - abs(noise(p * freq))       // fold: creates the ridge crease
        n = n * n                            // sharpen
        sum += n * amp
        freq *= lacunarity; amp *= gain
    return sum
```

Musgrave's actual formulation adds **weight feedback**, which is what makes it look like
mountains rather than crumpled paper — high previous octaves suppress the next octave, so
detail concentrates on the ridges and valleys stay smooth:

```
ridgedMF(p, octaves, lacunarity=2.0, gain=2.0, offset=1.0, H=1.0):
    signal = offset - abs(noise(p))
    signal = signal * signal
    result = signal
    weight = 1.0
    freq = 1.0
    for i in 1..octaves-1:
        freq *= lacunarity
        weight = clamp(signal * gain, 0, 1)          // feedback
        signal = offset - abs(noise(p * freq))
        signal = signal * signal
        signal = signal * weight                      // suppress where prev octave was low
        result += signal * pow(freq, -H)
    return result
```

`abs()` has a discontinuous derivative at zero. That crease is the ridge — it is the point —
but it means **ridged noise is not differentiable at the ridgeline**. Analytic normals will be
wrong there; use finite differences on the final heightfield instead.

## Hybrid multifractal

Musgrave — same provenance as ridged, above (1993 thesis / *Texturing & Modeling*, `00`). The
reason to reach for it: FBM has the same roughness everywhere, which
reads as artificial across a large map. Hybrid multifractal multiplies each octave by the
accumulated value so far, so low areas stay smooth (plains) and high areas get rough
(mountains) — the correlation you actually see in real topography.

```
hybridMF(p, octaves, lacunarity=2.0, H=0.25, offset=0.7):
    // exponent array precomputed: exps[i] = pow(lacunarity, -i*H)
    result = (noise(p) + offset) * exps[0]
    weight = result
    freq = 1.0
    for i in 1..octaves-1:
        freq *= lacunarity
        weight = min(weight, 1.0)                     // clamp: unbounded weight explodes
        signal = (noise(p * freq) + offset) * exps[i]
        result += weight * signal
        weight *= signal                              // the multifractal coupling
    return result
```

The `min(weight, 1.0)` is not optional — without it the product diverges and you get isolated
spikes to absurd heights. Range is not normalised; measure and remap.

## Domain warp

Quilez's formulation. Cheap, and the single highest ratio of visual improvement to
implementation cost in the whole noise section.

```
warp1(p):  return fbm(p + K * vec2(fbm(p + O1), fbm(p + O2)))

warp2(p):                                        // "fbm of fbm of fbm"
    q = vec2(fbm(p + O1), fbm(p + O2))
    r = vec2(fbm(p + K1*q + O3), fbm(p + K1*q + O4))
    return fbm(p + K2*r)
```

`K` is the warp amplitude in the same units as `p`. As a rule of thumb, start with K ≈ the
wavelength of the largest FBM octave; a warp much smaller than the feature size does nothing
visible, and much larger dissolves the structure into soup.

Returning `q` and `r` alongside the height is worth doing: they make excellent free masks
(they correlate with the warp structure, so materials placed by them follow the terrain's
apparent flow direction).

**Warping is not erosion.** It produces the *appearance* of flow-aligned structure with none
of the connectivity. If the deliverable needs rivers, warp is a look, not a substitute.

## Curl noise

Bridson et al. (2007). Divergence-free vector field from the curl of a potential:

```
curl2(p, eps):
    // 2D: potential is a scalar ψ, curl is the perpendicular gradient
    dpdy = (psi(p + (0, eps)) - psi(p - (0, eps))) / (2*eps)
    dpdx = (psi(p + (eps, 0)) - psi(p - (eps, 0))) / (2*eps)
    return vec2(dpdy, -dpdx)                    // ∇×ψ, divergence-free by construction
```

For terrain its use is as a **warp vector field** rather than a height source: warping by a
divergence-free field preserves area, so it swirls without pinching or tearing. Set `eps` to
roughly one cell; too small and you amplify float error, too large and you smooth away the
field you're sampling.

## Terrain-specific pitfalls

- **World-space, always.** `noise(uv)` per tile = a different pattern per tile = seams.
  `noise(worldPos * frequency)` is the only correct call. See `08-output-contract.md`.
- **Float precision at large world coordinates.** At 100 km out, fp32 has ~8 mm of resolution;
  a noise call at frequency 100 there is computing on garbage low bits, producing visible
  quantised terracing far from the origin. Fix: keep noise coordinates near the origin by
  subtracting a per-region offset that is an exact multiple of the noise period, or use
  double for the coordinate transform and cast to float per-octave after the multiply.
- **Perlin's zero at lattice points.** If you build a mask by thresholding raw Perlin near 0,
  you get a mask that outlines the lattice grid. Any thresholding of gradient noise near zero
  reveals the grid. Threshold FBM output instead, or offset the threshold away from 0.
- **Don't normalise to [0,1] with `n*0.5+0.5` and then remap with a curve.** The curve's knee
  lands in a different place than you expect because the distribution is Gaussian, not
  uniform — most of your terrain is clustered near 0.5 and the curve's tails do nothing.
  Histogram-match to the distribution you want, or use the curve on the measured range.
