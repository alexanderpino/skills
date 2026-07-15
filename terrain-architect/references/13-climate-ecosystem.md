# Climate & Ecosystem

Contents: [Why climate is in the graph](#why-climate-is-in-the-graph) · [Temperature](#temperature) ·
[Orographic precipitation](#orographic-precipitation-smith--barstad-2004) · [Rain shadow](#the-rain-shadow-result) ·
[Snow & avalanches](#snow--avalanches-cordonnier-et-al-2018) · [Moisture](#moisture--soil-water) ·
[Biomes](#biome-classification) · [Ecosystem simulation](#ecosystem-simulation-deussen-et-al-1998) ·
[Multi-biome worlds](#multi-biome-worlds-regional-composition)

## Why climate is in the graph

Two reasons, and only the second is interesting.

1. Climate fields drive **material and vegetation masks** (`06`, `07`). Obvious, cheap, useful.
2. Climate **couples back into erosion**. Precipitation is the `K`/rainfall term in every
   hydraulic model (`04`). A range with a wet windward side and a dry leeward side erodes
   *asymmetrically* — the wet side incises faster, the drainage divide migrates toward the dry
   side, and the whole range becomes lopsided.

That second effect is real, well-documented (the Southern Alps of New Zealand are the textbook
case), and almost never implemented. It costs one 1D advection pass and it produces a
large-scale asymmetry no noise stack will give you.

If you only need masks, compute climate after erosion. If you want the coupling, it goes inside
the erosion loop — which is what Cordonnier et al. 2017 do for vegetation.

## Temperature

```
T(z, lat) = T_sea(lat) - Γ * z
```

`Γ` = lapse rate:

| Lapse rate | Value | Use |
|---|---|---|
| Environmental (average) | **6.5 °C/km** | The default. Use this. |
| Dry adiabatic | 9.8 °C/km | Unsaturated rising air |
| Saturated adiabatic | ~5 °C/km | Rising air that's condensing (i.e. on the windward slope) |

`T_sea(lat)` ≈ 30 °C at the equator falling to −20 °C at the poles, roughly cosine. For a
single map, a constant plus a linear latitude gradient is plenty.

Add **aspect**: south-facing slopes (northern hemisphere) receive more insolation. A few °C of
difference, and it's the reason the snow and treeline are visibly higher on sunny slopes than
shaded ones. `T += insolationAmp * northness` where `northness = -cos(aspect)` (`06`). Cheap,
and it's one of those details that makes a landscape read as real without anyone noticing why.

**Snow line** = the elevation where `T = 0`. **Permafrost** = where the *annual mean* stays
below 0. Both are thresholds on this field, not separate algorithms.

## Orographic precipitation (Smith & Barstad 2004)

*A Linear Theory of Orographic Precipitation*, J. Atmos. Sci. 61. The canonical model, a linear
transfer function in Fourier space coupling terrain to precipitation via advection, condensation
and fallout timescales. It's implementable and it's the right citation.

**The practical approximation** — a 1D march along the wind — captures the effect for a fraction
of the work:

```
orographicPrecip(h, windDir, moisture0):
    precip = zeros
    # march along wind direction, ray by ray across the domain
    for each ray entering the upwind boundary:
        m = moisture0                                    # kg/m² of water vapour
        p = rayStart
        while p in domain:
            lift = max(0, dot(windDir, gradient(h, p)))  # forced ascent: m rise per m travelled
            # condensation ∝ uplift rate × available moisture
            dP = min(m, k_cond * lift * m)
            precip[p] += dP
            m -= dP
            m += evapRate * isWater(p) * cellSize        # re-charge over ocean/lakes
            m += baseEvap * cellSize                     # background evapotranspiration
            p += windDir * cellSize
    return precip
```

**The details:**
- **`lift` is the *along-wind* gradient**, not the slope magnitude. Air rising over a slope
  perpendicular to the wind doesn't rise. `dot(windDir, ∇h)` is the whole model.
- **Moisture depletes.** That's the mechanism — without `m -= dP` you get precipitation on every
  slope and no rain shadow, which is the entire point.
- **Fallout lag.** Smith & Barstad's real contribution is that condensed water doesn't fall
  instantly — it advects downwind for a characteristic time `τ` (~500–2000 s) before falling.
  This shifts the precipitation maximum *past* the crest, which is observed. Approximate it by
  blurring `precip` downwind by `windSpeed × τ` metres. Skipping it puts maximum rain exactly on
  the ridgeline, which is subtly wrong.
- Run it at low resolution (500 m–1 km cells). Precipitation fields are smooth; there's no
  reason to march at 1 m.

## The rain shadow result

```
K_effective = K_base * pow(precip / precipRef, e)         # e ≈ 0.5–1.0
```

Feed that into stream power (`04`) and run to equilibrium. What you get:

- Windward: high precip → high `K` → steeper incision → deeper valleys, lower relief
- Leeward: low precip → low `K` → slow incision → a high, undissected, arid plateau
- The **drainage divide migrates toward the dry side** — because the wet side erodes headward
  faster. Over long runs the divide is nowhere near the topographic centre of the uplift.

This is a genuine emergent geomorphic result, and it is impossible to author by hand because
nobody would think to put the divide off-centre.

## Snow & avalanches (Cordonnier et al. 2018)

*Interactive Generation of Time-evolving, Snow-Covered Landscapes with Avalanches*, CGF 37(2).
The real reference.

The practical core is short, because **avalanching is thermal erosion on the snow layer**
(`05`) — the same code, a different field, a lower talus angle:

```
snowStep(h, snowDepth, T, precip):
    # 1. Accumulate where it's cold
    snowDepth += precip * (T < 0) * dt

    # 2. Melt where it's warm  (degree-day model — crude and standard)
    snowDepth -= max(0, meltFactor * T) * dt
    snowDepth = max(snowDepth, 0)

    # 3. Snow doesn't stick to steep ground
    snowDepth *= (1 - smoothstep(tan(50°), tan(60°), slope(h)))

    # 4. Avalanche: thermal erosion on the SNOW layer, over the terrain surface
    thermal(field=snowDepth, base=h, talusAngle=snowRepose)     # snowRepose ≈ 35–40°
```

Step 4 is the one that matters. Snow relaxed on `h + snowDepth` slides off steep faces and
accumulates in gullies and at the base of slopes — which is where snow actually is. Without it,
snow is a slope-thresholded mask painted uniformly, which reads as fake instantly because it
ignores that snow *moves*.

**Wind redistribution** is the other half: snow scours from windward crests and deposits in the
lee — the same shadow-zone logic as dunes (`05`). Reuse Werner's shadow-zone test with a snow
field. Cornices are lee-side deposits at a crest.

## Moisture & soil water

Don't build a groundwater model. Use TWI (`06`), which is a moisture proxy derived from
topography and is exactly what it's for:

```
soilMoisture = normalize(TWI) * precipFactor * (1 - drainageFactor(permeability))
```

`permeability` comes from the material field (`11`) — sand drains, clay holds. Add distance to
water bodies if you have them.

**Evapotranspiration** and the rest of the water balance: `F`-tier, no canonical source worth
citing for terrain purposes. A threshold on temperature and moisture is as much as any terrain
graph has ever needed.

## Biome classification

Two real references, and both are lookup tables rather than algorithms:

- **Whittaker's biome diagram** (Whittaker 1975): biome as a function of mean annual
  temperature and precipitation. A 2D lookup. This is the one to use — it's exactly a
  `(T, precip) → biome` texture fetch, which is what you want in a graph.
- **Köppen–Geiger** (Köppen 1900; **Peel et al. 2007** for the modern gridded map): a decision
  tree on temperature and precipitation *seasonality*. More precise, needs monthly data, more
  than a terrain graph usually has.

```
biome(T, precip) = whittakerLUT[T, precip]
```

**Ecotones** — the transitions — matter more visually than the classes. Never snap to a hard
biome boundary; blend over a band, and perturb the boundary with noise (`06`). A hard biome
edge across a hillside is the most obvious possible tell.

## Ecosystem simulation (Deussen et al. 1998)

*Realistic Modeling and Rendering of Plant Ecosystems*, SIGGRAPH 98. The canonical reference.
Follow-ups: **Lane & Prusinkiewicz 2002** (Graphics Interface) for multilevel plant community
distributions; **Makowski et al. 2019** (ACM TOG 38(4)) for multi-scale ecosystems;
**Cordonnier et al. 2017** for coupling to erosion; **Měch & Prusinkiewicz 1996** for open
L-systems (plants interacting with their environment).

The shared core across all of them is **iterative competition with self-thinning**:

```
ecosystem(env, iterations):
    plants = []
    for it in 0..iterations:
        # 1. Colonisation — seed proportional to viability
        for each candidate p from a scatter (07):
            v = viability(species, env(p))              # from T, moisture, slope, soil
            if random() < v * seedRate:
                plants.append(Plant(p, species, age=0, r=r0))

        # 2. Growth
        for plant in plants:
            plant.r += growthRate(plant.species, env(plant.p)) * (1 - plant.r / rMax)
            plant.age += 1

        # 3. Competition — the part that matters
        for each pair (a, b) with |a.p - b.p| < a.r + b.r:
            dominant = (a.r > b.r) ? a : b               # bigger wins; or use a shade-tolerance rank
            weaker   = (a.r > b.r) ? b : a
            weaker.vigour -= overlapAmount * dominanceFactor
            if weaker.vigour <= 0: kill(weaker)

        # 4. Mortality
        for plant in plants:
            if plant.age > maxAge(species) or random() < mortality(env, plant): kill(plant)
```

**Why this beats a density mask.** A scatter driven by a density mask (`07`) gives you plants
where conditions are good. An ecosystem sim gives you *history*: mature trees with clearings
around them, saplings crowded into gaps, a treeline that thins gradually because competition
plus marginal viability produces exactly that, and species zonation with fuzzy ecotones because
the shade-tolerant species won in the shade.

**The self-thinning law** (Yoda's −3/2 power law): as a stand grows, density falls as
`density ∝ biomass^(-3/2)`. Use it as a validation check — if your simulated stand doesn't obey
it, competition is mis-tuned. It's a cheap quantitative oracle for a subjective output.

**Coupling back to erosion (Cordonnier et al. 2017):** vegetation stabilises soil, so
`K_effective *= (1 - vegetationCover * stabilisation)`. Then the loop closes: erosion shapes
terrain → terrain shapes climate → climate shapes vegetation → vegetation resists erosion. It
is the only part of the pipeline that's genuinely a cycle rather than a DAG, and it needs a
fixed number of outer iterations rather than a convergence criterion.

**Output.** An ecosystem sim's product is a `PointSet` with species, size and age — it *replaces*
the scatter node's density mask rather than feeding it. That's a graph-shape change, not a node
swap, so decide before building `07`.

## Multi-biome worlds (regional composition)

"Build me Hyrule / Middle-earth" — one map with a snowy massif, a desert, a swamp, a volcano, a
forest — is the most common large request and the most common way to get it wrong. The wrong way
is to **generate each region separately and mask the terrains together**. It fails the same way
every time: seams at every boundary, rivers that die at the biome edge, a coastline unrelated to
the drainage, materials that change on a line no water would respect. Independent per-region
terrains do not share a hydrology, and a shared hydrology is what makes a world read as one place.

**The rule: one substrate, one hydrology; masks vary parameters — not geometry.**

```
1. ONE macro layer for the whole world (02)
   - Author the coastline and mountain ranges as uplift (splines / painted U, 02). For a named
     map (Middle-earth) these are CONSTRAINTS you match, not noise you accept.
   - Lay the regions out as a PARTITION: Voronoi over authored centres, painted, or derived
     from climate (below). This is your world map / region graph.

2. ONE global hydrology + erosion pass (03, 04)
   - Depression handling, flow routing, and the erosion backbone run ONCE over the whole domain,
     so drainage is coherent: rivers cross regions, divides sit where uplift + climate put them,
     the coastline falls out of the drainage (02).

3. Regions modulate PARAMETERS of that shared pass, through masks (06):
     regionMask[i] ─▶ K, erosion backbone     (arid → aeolian 05; wet → fluvial 04)
                   ─▶ precip, temperature      (13 → the biome, via Whittaker)
                   ─▶ material / splat         (06)
                   ─▶ scatter / ecosystem      (07, 13)
                   ─▶ region-local detail      (biome-specific noise / stamps INSIDE the mask)

4. Biomes are then mostly EMERGENT, not painted:
     climate (13) + material + ecosystem give biome(T, precip). Paint a region mask to FORCE a
     biome where a story demands one; let climate produce the rest.
```

**Two ways to drive the region layout — you usually blend them:**

- **Climate-first (emergent).** Let temperature and precipitation fall out of latitude, elevation,
  and the orographic rain shadow (above), then read biomes off the Whittaker LUT. This gives a
  *geographically honest* world for free — deserts in the rain shadow, jungle on the windward
  coast, tundra up high. Mordor reads right precisely because it sits in a rain shadow.
- **Authored-first (art-directed).** A game world (Hyrule) has a designer's map: named regions in
  fixed places for gameplay, not climate. Paint the partition and force each region's
  climate/material/erosion parameters. The substrate and hydrology stay global and shared — that
  is what keeps a *designed* layout coherent instead of looking assembled.

**Ecotones are mandatory** (the biome-boundary note above): never snap region masks to hard
edges. The masks must partition to 1 (`06`) and blend over a band, perturbed with noise. A hard
biome line across a hillside is the single most obvious tell that a world was built from parts.

**Per-region erosion backbone.** A desert and a rainforest are not the same erosion. Within the
one global pass, let the mask pick the process: high fluvial `K` and drainage density in the wet
region (`04`), aeolian dunes in the arid one (`05`), frost-shattering thermal up high (`05`/`13`),
coastal in the littoral band (`12`). The *height field* stays global and continuous; only the
*process weights* change across the mask — which is the whole discipline in one sentence.

**References.** The map of this design space is the survey **Galin et al. 2019**, *A Review of
Digital Terrain Modeling* (CGF 38(2)) — read it before committing an architecture for a world. For
composing terrain from named feature primitives (peaks, ridges, rivers, cliffs placed on a map),
**Génevaux et al. 2015**, *Terrain Modelling from Feature Primitives* (CGF 34(6)); for
example-based authoring of the *distributions* of world elements ("scatter this region like that
one"), **Emilien et al. 2015**, *WorldBrush* (ACM TOG 34(4)); for sketch-to-terrain of a region,
**Guérin et al. 2017** (`00`). None of these is "the multi-biome algorithm" — there isn't one. A
world is a composition, and the discipline is keeping the substrate and hydrology global while the
masks do the regional work.
