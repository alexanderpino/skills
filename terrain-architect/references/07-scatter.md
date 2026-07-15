# Object Distribution

Contents: [Bridson](#poisson-disk-bridson-2007) · [Variable density](#variable-density--the-terrain-case) ·
[Blue noise alternatives](#blue-noise-alternatives) · [Tiling scatter](#tiling-scatter) ·
[Rule-based](#rule-based-scatter) · [Clasts (rocks & pebbles)](#clasts-rocks-cobbles-pebbles)

## Poisson disk (Bridson 2007)

*Fast Poisson Disk Sampling in Arbitrary Dimensions.* O(N), and short enough that there's no
excuse for using dart-throwing.

```
poissonDisk(domain, r, k = 30):
    cellSize = r / sqrt(2)                       # ← r/sqrt(n) for n dimensions
                                                  #   guarantees ≤1 sample per grid cell
    grid = array of index, initialised to -1
    samples = []
    active = []

    p0 = randomPointIn(domain)
    samples.append(p0); active.append(0)
    grid[gridCoord(p0)] = 0

    while active not empty:
        idx = active[randomInt(0, len(active))]
        found = false

        for attempt in 0..k-1:
            p = randomInAnnulus(samples[idx], r, 2*r)
            if p not in domain: continue
            if isFarEnough(p, grid, samples, r):
                samples.append(p)
                active.append(len(samples) - 1)
                grid[gridCoord(p)] = len(samples) - 1
                found = true
                break

        if not found:
            active.remove(idx)                   # swap-with-last removal — order doesn't matter

    return samples

isFarEnough(p, grid, samples, r):
    c = gridCoord(p)
    for each cell q in the 5x5 neighbourhood of c:      # 2 cells out — see note
        if grid[q] >= 0 and distance(samples[grid[q]], p) < r:
            return false
    return true
```

**Details that matter:**

- **`cellSize = r / √n`** (so `r/√2` in 2D). This is chosen precisely so that a grid cell's
  diagonal is `r`, guaranteeing at most one sample per cell — which is what makes the grid a
  valid O(1) lookup structure. Using `r` or `r/2` breaks the invariant and the neighbour
  search silently misses conflicts.
- **The 5×5 neighbourhood.** With `cellSize = r/√2`, a conflicting sample can be up to 2 cells
  away. Checking only 3×3 misses conflicts near cell corners and produces occasional pairs
  closer than `r`. Cheap bug, subtle symptom.
- **Annulus sampling must be area-uniform.** The naive version:

```
    # WRONG — biases toward the inner radius
    radius = r * (1 + random())
    angle  = 2π * random()
```

```
    # RIGHT — uniform by area over the annulus [r, 2r]
    radius = r * sqrt(1 + 3 * random())          # sqrt(r² + random()*(4r² - r²)) / r
    angle  = 2π * random()
    p = centre + radius * (cos angle, sin angle)
```

  Bridson's paper says "uniformly from the spherical annulus"; a great many implementations
  get this wrong. The bias is mild — you get slightly tighter clumping — but it's free to fix.
- **`k = 30`** is Bridson's value. Lower `k` = faster but leaves gaps (the distribution stops
  being maximal). Higher `k` = diminishing returns. Keep 30.

## Variable density — the terrain case

Terrain scatter is never uniform: trees are dense in valleys, sparse on ridges, absent above
the treeline. Two approaches.

**A. Rejection against a density map (recommended).** Generate at the *minimum* spacing, then
reject:

```
r_min = spacingAt(maxDensity)
candidates = poissonDisk(domain, r_min)
result = [p for p in candidates if random() < density(p) / maxDensity]
```

Simple, correct, keeps Bridson unmodified. Cost: you generate `maxDensity/meanDensity` times
more points than you keep. For terrain that ratio is usually 2–5×, which is fine.

**Loses the blue-noise property in the sparse regions**, though — after rejection, the sparse
areas are Poisson-random, not blue-noise. If that matters (it often doesn't for trees; it does
for grass cards at low density where clumping is visible), use B.

**B. Variable-radius Poisson.** Let `r` vary spatially:

```
    r(p) = spacingFromDensity(density(p))
    cellSize = r_min / sqrt(2)                   # grid sized by the SMALLEST radius
    isFarEnough(p): check distance < max(r(p), r(sample))     # ← symmetric test
```

The `max()` in the conflict test is what makes it symmetric and therefore correct — without
it, whether two points conflict depends on which was generated first, and you get density
artefacts along the generation frontier. The neighbourhood search must now extend
`ceil(r_max / cellSize) + 1` cells, which gets expensive if `r_max/r_min` is large. Cap the
ratio at ~4 or use a hierarchical grid.

## Blue noise alternatives

- **Best-candidate (Mitchell 1991).** Generate `m` candidates, keep the one farthest from all
  existing samples. O(N² m) naive. Simple, decent spectrum, too slow at scale. Its virtue:
  you can stop at any count and get a good distribution of exactly that many points — Bridson
  gives you however many fit.
- **Blue-noise / void-and-cluster tiles (Ulichney 1993).** Precompute a tileable blue-noise
  mask; threshold it against the density map. **O(1) per cell, trivially tileable, no seams,
  no state.** For grass and small props at high counts this is the right answer and Bridson
  is over-engineering.
- **Sample elimination (Yuksel 2015).** Start with many random points, greedily remove until
  the target count, using a weighted heap. Produces excellent spectra and hits an exact count.
  This is what to use when the artist says "exactly 5000 trees".
- **Parallel/GPU (Ebeida et al. 2011, Wei 2008).** Grid-based, phase-group parallelism. Worth
  it only at very large N.

**Recommendation for terrain:** Ulichney tiles for ground cover (grass, rocks, debris — high
count, tileable, per-cell), Bridson + rejection for props (trees, boulders — moderate count,
needs real spacing).

## Tiling scatter

Same problem as erosion: a scatter run per tile independently will place samples right up
against the tile edge on both sides, producing a visible seam of doubled density.

```
scatterTile(tile):
    # Deterministic: seed from tile coordinate, not a global counter
    seed = hash(rootSeed, tileX, tileY)

    # Generate over the tile PLUS an apron of width 2*r_max
    region = expand(tile.bounds, 2 * r_max)
    samples = poissonDisk(region, r, seed)

    # Keep only samples inside the tile proper
    return [p for p in samples if p in tile.bounds]
```

**This does not fully work**, and it's worth being honest about why: the apron samples
generated for tile A and those generated for tile B are different random sets, so they don't
agree across the boundary and conflicts can still occur. Options:

1. **Ulichney tiles** — no problem exists; the mask is tileable by construction. Preferred.
2. **Deterministic per-cell jitter (stratified/jittered grid)** — `p = cellCentre + hash(cell) * jitter`.
   Trivially tileable, deterministic, seamless. Not true blue noise but for dense ground cover
   nobody can tell.
3. **Generate globally, then partition.** Correct, but requires the whole domain at once,
   which defeats streaming.
4. **Boundary-first generation.** Generate the shared edge samples deterministically from the
   edge's hash (both tiles compute the same edge set), then fill interiors. Correct and
   streamable, but fiddly.

For most terrain: option 2 for ground cover, option 3 for props (there are few enough props
that generating them globally is cheap), option 4 only if you genuinely need streamed
blue-noise props.

## Rule-based scatter

The layer above the sampler. The sampler gives you positions; the rules decide what survives
and what it looks like.

```
for each sample p:
    h     = height(p)
    s     = slope(p)
    twi   = wetness(p)
    a     = aspect(p)

    # Hard gates
    if s > tan(maxSlope): reject                      # trees don't grow on cliffs
    if h > treeLine: reject
    if riverMask(p) > 0.5: reject                     # not in the water
    if not densityMask(p): reject

    # Species selection from environment, not from random()
    species = selectByWeights(p, [
        (pine,   f_pine(h, twi, a)),
        (oak,    f_oak(h, twi, a)),
        (birch,  f_birch(h, twi, a)),
    ])

    # Per-instance variation
    scale    = baseScale * lerp(0.7, 1.3, hash(p))
                         * healthFromEnvironment(twi, h)     # ← not just random
    rotation = random yaw
    tilt     = align to normal, blended: lerp(up, normal, alignFactor)
```

**The thing that separates good scatter from obvious scatter:**

- **Derive variation from the environment, not from `random()`.** Trees near water are taller
  and greener; trees near the treeline are stunted and sparse. That gradient is what makes a
  forest read as a forest and not as a stamp field. `scale = f(twi)` costs nothing and does
  more than any amount of random variation.
- **Don't fully align to the terrain normal.** Trees grow toward the light, i.e. mostly
  vertical, on slopes up to quite steep. `alignFactor ≈ 0.2–0.3` for trees, `1.0` for rocks
  and debris. Fully-aligned trees on a 30° slope look like they were pushed over.
- **Cluster.** Real vegetation clumps — seed dispersal is local. Multiply the density map by a
  mid-frequency noise before scattering (`density *= 0.5 + 0.5*fbm(p * clusterFreq)`). Pure
  blue noise reads as *too* even, which is its own kind of artificial.
- **Sink into the ground.** Offset each instance down by a few cm so the base isn't floating
  on any slope. Cheaper than the alternative of everyone noticing.

## Clasts (rocks, cobbles, pebbles)

Scattering rock is still scattering — but the size and placement come from the **grain-size (D50)
field** (`04`), not from `random()`. That field already says boulders in the steep headwaters and
rapids, cobbles in the bends, pebbles on the pool beaches; the scatter just realises it.

```
for each sample p:      # Ulichney tiles for a pebble beach (very high count); Bridson for boulders
    D50 = grainSize(p)                          # the 04 caliber field
    if D50 < pebbleThreshold and not onBar(p): reject     # pebbles only where bedload deposits
    size  = drawFromDistribution(D50)           # a spread around D50, not a constant
    round = roundness(distanceDownstream(p))    # angular near the source → rounded far (Sternberg, 04)
    tilt  = imbricate(flowDir(p))               # dip UPSTREAM (04), NOT aligned to the ground normal
```

Two rules specific to river clasts:

- **Pebble beaches are extreme-count ground cover, not props.** A gravel bar is thousands of
  clasts per square metre — use Ulichney tiles or an instanced scatter shader, never per-object
  Poisson. Model the *bar surface* as a material (`06`) and scatter representative clasts on top;
  the "millions of pebbles" are a texture-plus-instancing problem, not a million transforms.
- **Orientation carries the process.** Imbrication (upstream dip) and long-axis alignment to flow
  are what make a bar read as water-laid instead of a dumped rubble pile — the same "variation
  from the environment, not from `random()`" rule as vegetation above. Fully normal-aligned
  pebbles (`alignFactor = 1`) are right for a *scree* slope (`05` talus), wrong for a river bar.
