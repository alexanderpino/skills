# Climate & Ecosystem

Contents: [Why climate is in the graph](#why-climate-is-in-the-graph) · [Temperature](#temperature) ·
[Wind fields](#wind-fields) ·
[Orographic precipitation](#orographic-precipitation-smith--barstad-2004) · [Rain shadow](#the-rain-shadow-result) ·
[Snow & avalanches](#snow--avalanches-cordonnier-et-al-2018) · [Moisture](#moisture--soil-water) ·
[Biomes](#biome-classification) · [Ecosystem simulation](#ecosystem-simulation-deussen-et-al-1998) ·
[Biogenic landforms](#biogenic-landforms--life-as-a-geomorphic-agent) · [Fire & burned land](#fire--burned-land) ·
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

This is the *local* climate model, and it takes the base temperature and wind **direction** as inputs.
On a **whole planet** those inputs have a global structure — the three-cell circulation (trade winds,
westerlies, polar easterlies), the ITCZ, and the subtropical highs that put deserts at ~30° — which
should *drive* this model rather than be assumed. That global forcing is `references/25-planetary-spherical.md`;
feed its banded wind and latitude precipitation field into the orographic pass below.

Add **aspect**: south-facing slopes (northern hemisphere) receive more insolation. A few °C of
difference, and it's the reason the snow and treeline are visibly higher on sunny slopes than
shaded ones. `T -= insolationAmp * northness` where `northness = dot(aspectVec, north)` — +1 on
north faces (`06`'s downslope-aspect convention), which must therefore *cool* in the northern
hemisphere; flip the sign south of the equator. Cheap,
and it's one of those details that makes a landscape read as real without anyone noticing why.

**Snow line** = the elevation where `T = 0`. **Permafrost** = where the *annual mean* stays
below 0. Both are thresholds on this field, not separate algorithms.

## Wind fields

Wind is consumed by **four** systems — dunes (`05`), orographic precipitation (below), snow drift
and cornices (below), wave fetch (`12`) — so it deserves better than a constant vector, and real
CFD remains out of scope. The middle ground is a **terrain-adjusted wind field**: author the
regional wind (direction + speed, possibly a seasonal rose), then let the terrain modulate it.

```
windField(h, baseDir, baseSpeed):
    for each cell p:
        # 1. Speed-up over windward slopes and crests — Jackson & Hunt 1975:
        #    fractional speed-up scales with the hill's slope (Δu/u ∝ h/L), peaking at the crest
        s = 1 + k_su * max(0, upwindSlope(h, p, baseDir))       # cap; k_su gives ~1.5–2× at steep crests
        # 2. Lee shelter — Werner's dune shadow zone (05), at landscape scale
        if inShadowZone(h, p, baseDir, ~15°): s *= shelter       # ~0.2–0.5
        # 3. Channelling: rotate toward the valley axis where relief confines the flow
        dir = blend(baseDir, valleyAxis(p), confinement(p))      # confinement from relief across-flow
        wind[p] = s * baseSpeed * dir
    # 4. Optional cleanup: adjust to zero divergence — the "mass-consistent" wind-model family
    #    (Sherman 1978, MATHEW): least-squares project onto a divergence-free field, or build the
    #    field from a potential in the first place (curl, 01). Without it, wind piles up nowhere.
```

Every ingredient is machinery the skill already has: the upwind-slope term is the `dot(windDir, ∇h)`
of the orographic march below, the shadow zone is Werner's (`05`), and the sweep costs are the
`06`/`12` horizon machinery. What the consumers gain: dunes align to *deflected* wind (valley-floor
dune fields point along the valley, not the regional wind) and bank against obstacles as **anchored
dunes** — echo, climbing, falling, sand ramps (`05`, `16`); cornices form on the *actual* lee,
fetch responds to channelled winds down a fjord, and precipitation sees the speed-up. **Tier:** the
recipe is F — a look built from two P-tier anchors (Jackson & Hunt 1975 for the crest speed-up;
Sherman 1978 for mass-consistency). Real boundary-layer CFD stays out of scope, and say so.

### Mass-consistent adjustment (Sherman 1978, MATHEW)

Step 4 deserves its math, because "wind piles up nowhere" is a real defect: the terrain-adjusted
field $\vec{u}_0$ has spurious sources and sinks the terrain never put there. MATHEW is the fix —
find the field $\vec{u}$ closest to $\vec{u}_0$ (weighted least squares) that is also
divergence-free. Minimising

$$J = \int \tfrac{1}{2}\,\alpha^2\,\lVert \vec{u}-\vec{u}_0 \rVert^2 \, dA \quad\text{subject to}\quad \nabla\cdot\vec{u}=0$$

with a Lagrange multiplier $\lambda$ gives $\vec{u} = \vec{u}_0 - \nabla\lambda$ (the weight
$\alpha^2$ is absorbed into $\lambda$); imposing continuity turns it into a **Poisson equation** —
the Helmholtz–Hodge projection that strips the curl-free part:

$$\nabla\cdot\vec{u}=0 \;\Longrightarrow\; \nabla^2\lambda = \nabla\cdot\vec{u}_0$$

```
massConsistentWind(u0, v0, cellSize):
    # 1. divergence of the terrain-adjusted field (central differences)
    div = (u0[i,j+1] - u0[i,j-1] + v0[i+1,j] - v0[i-1,j]) / (2*cellSize)
    # 2. solve ∇²λ = div  for the scalar potential λ
    #    FFT (periodic): λ̂ = −div̂ / k²   (k from 02's wavenumber grid; set λ̂(0)=0)
    #    bounded domain: Jacobi/multigrid — open edge → λ=0 (Dirichlet, flow exits);
    #                    solid ridge → ∂λ/∂n=0 (Neumann, no normal flow)
    λ = solvePoisson(div, cellSize, bc)
    # 3. subtract the divergent part
    u = u0 - (λ[i,j+1] - λ[i,j-1]) / (2*cellSize)
    v = v0 - (λ[i+1,j] - λ[i-1,j]) / (2*cellSize)
    return u, v          # ∇·(u,v) ≈ 0 : streamlines wrap terrain instead of piling into it
```

Anisotropic precision moduli ($\alpha_1\neq\alpha_2$, horizontal vs vertical) make step 2 an
*anisotropic* Poisson — MATHEW's actual form. Still **F-tier**: it enforces continuity, not
momentum. Verify by re-checking $\nabla\cdot\vec{u}\to 0$ and that no streamline dead-ends into a
slope.

*Runnable reference: `reference-impl/winds.py`, verified by `tests/test_winds.py` — the corrected
field's divergence drops by orders of magnitude (`09`).*

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

**Wetlands (swamps, marshes, bogs)** are where this machinery saturates, and they are a **mask,
not a height**: flat ground + high TWI + an impermeable or frozen substrate (clay `18`, permafrost
`17`) → the water table sits at or above the surface. Realise it as a wetland mask driving peat/mud
material (`18`), a thin standing-water layer (`08` stack), and its own vegetation community
(`07`/ecosystem below). Salt marsh is the tidal case (`12` intertidal). L-tier — a composition of
the moisture machinery above, no new algorithm.

**Evapotranspiration** and the rest of the water balance: `F`-tier, no canonical source worth
citing for terrain purposes. A threshold on temperature and moisture is as much as any terrain
graph has ever needed.

## Biome classification

Three real references, and all are lookup tables rather than algorithms:

- **Whittaker's biome diagram** (Whittaker 1975): biome as a function of mean annual
  temperature and precipitation. A 2D lookup. This is the one to use — it's exactly a
  `(T, precip) → biome` texture fetch, which is what you want in a graph.
- **Köppen–Geiger** (Köppen 1900; **Peel et al. 2007** for the modern gridded map): a decision
  tree on temperature and precipitation *seasonality*. More precise, needs monthly data, more
  than a terrain graph usually has.
- **Holdridge life zones** (Holdridge 1947, 1967): the same idea with **altitude as a first-class
  axis**. Life zone from **biotemperature** (mean temperature with everything below 0 °C and above
  30 °C clipped out, so frost months don't count toward growth), annual precipitation and a PET
  ratio, arranged on a triangular chart whose rows are explicit **altitudinal belts** — basal →
  premontane → montane → subalpine → alpine → nival — running parallel to the latitudinal zones.
  Reach for this over Whittaker when you want the vegetation *belts up a single mountain* named and
  stacked (montane forest → treeline → alpine tundra → bare nival) rather than emerging implicitly
  from the lapse rate. Biotemperature is what encodes "cold months grow nothing", so a summit lands
  in the alpine/nival belt by construction — the reason a baobab can't spawn on a peak even if some
  authored species-weight forgot to gate on temperature.

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

## Biogenic landforms — life as a geomorphic agent

The ecosystem sim above places *vegetation on* terrain. Sometimes life **is** the terrain: organisms
build, trap and cement relief directly. Coral is the marine case (`12`); here are the rest, from a real
growth model to rule-based buildups.

- **Peat & bogs — the one with a growth law.** Peat accumulates where waterlogging stops decay, and its
  height is **self-limiting** (Clymo 1984): a thin aerobic **acrotelm** feeds mass `p` to the thick
  anaerobic **catotelm**, which decays slowly at rate `α`. Catotelm mass per area obeys
  ```
  dM/dt = p − α·M     →     M(t) = (p/α)·(1 − e^(−α·t)),   M_max = p/α
  surfaceHeight = z_mineral + M/ρ_b            # ρ_b = peat bulk density
  ```
  so a bog **domes toward an asymptote**, not linearly — the raised bog's convex profile *is* this
  equation. Gate `p` by wetness (`06` TWI) and it grows in waterlogged hollows and stalls on drained
  slopes. P-tier — a genuine accumulation model, the terrestrial sibling of coral's `reefStep`.
- **Microbialites / stromatolites** *(Grotzinger & Knoll 1999)* — layered microbial carbonate mounds in
  shallow sunlit water. No tidy ODE; realise them as **accretionary layered domes** (scatter nuclei on a
  shallow substrate, grow by light-gated accretion with wavy laminae) — the same photic gate as coral,
  one rung simpler. L / material: a laminated carbonate cap that can double as a local resistant unit
  (`11`).
- **Nebkha / coppice dunes** *(Tengberg & Chen 1998)* — vegetation-anchored sand mounds: a shrub raises
  the shear threshold, traps saltating sand (`05`), and a mound grows around it, capped by plant height
  and elongated downwind. The general rule is that **vegetation cover stabilises dunes** — the same
  `K_effective *= (1 − cover)` coupling, applied to the aeolian threshold — so cover fraction decides a
  stable nebkha field vs. mobile barchans (`16`). L.
- **Bioturbation mounds** *(termite & Mima mounds; Darwin 1881 on earthworms)* — animals move soil. Two
  modes: **regularly-spaced mounds** — termite (and the debated Mima) fields self-organise to a near-
  hexagonal spacing by inter-colony competition (Tarnita et al. 2017), realised as **inhibition scatter**
  (Poisson-disk / Lloyd relaxation, `07`) with a cone raised per colony; and **diffuse soil turnover** —
  earthworm/ant mixing as an added hillslope **diffusivity** `D_bio` on the creep term (`05`, Culling),
  smoothing micro-relief. The mounds are L; the analytic spacing law is `?` (a competition rule, not a
  closed form) and Mima-mound genesis is genuinely debated — say so.

**Tier.** Peat is P (Clymo 1984, a growth ODE); stromatolites, nebkha and bioturbation mounds are L
compositions (Grotzinger & Knoll 1999; Tengberg & Chen 1998; Tarnita et al. 2017; Darwin 1881), the
termite/Mima *spacing* honestly `?`. All couple into the ecosystem/erosion loop above rather than
standing apart from it.

## Fire & burned land

**Burned land is a disturbance state, not a landform** — it writes to *materials and foliage*,
barely to height. Get the scope right and it is cheap; get it wrong and you end up simulating
combustion for a black texture. Three parts, one of which is not just texture:

**1. The burn scar's shape — spread is slope- and wind-driven.** The canonical spread model is
**Rothermel 1972** (USDA Forest Service Research Paper INT-115 — the model still inside every
operational fire-behaviour system): spread rate through a fuel bed accelerates **upslope and
downwind**. For terrain you don't need the full fuel physics — a front march over a fuel field
gives the scar its recognisable anatomy:

```
burnScar(fuel, windField, h, ignition):        # fuel = vegetation density (ecosystem/07)
    front = {ignition}
    while front and fuel remains:
        spread rate ∝ fuel * (1 + a·max(0, upslope)) * (1 + b·downwind(windField, 13))
        advance the front (CA or level set); consume fuel; record burnSeverity
    # anatomy that falls out: scars ELONGATE downwind and uphill, run up drainages,
    # finger along fuel corridors, and leave UNBURNED ISLANDS where fuel or wind failed
```

Severity is a **mosaic**, not a bool — crown-fire kill at the core, scorch at the margins,
unburned islands inside — and the mosaic is the visible signature of a real burn.

**2. What it writes — materials and foliage (your instinct, made concrete).**
- **Materials (`18`, `08`):** char and ash by severity — blackened albedo over scorched mineral
  soil, an ash dusting that behaves as a *transient* cover (it blows and washes away within
  seasons, `08` stack). A still-smouldering edge can borrow the `08` emissive channel at low
  intensity; active flame is the engine's job, not the terrain's (the whitewater rule, `03`).
- **Foliage (`07`, ecosystem above):** by severity — remove canopy but leave **standing snags**
  (dead trunks: the same tree scatter, swapped model, no leaves) in high-severity zones; scorch
  survivors at margins. Then **succession is free**: the burn simply resets the ecosystem sim's
  local state, and recolonisation (grass → shrub → pioneer trees) falls out of the competition
  loop already above — a burn scar *ages* without any new machinery.

**3. The part that is not texture: the erosion response.** Fire is a *hydro-geomorphic event*
(**Shakesby & Doerr 2006**, Earth-Science Reviews 74 — the review): vegetation loss plus
fire-induced **soil water repellency** boosts runoff and strips the protection term the skill
already models — `K_effective *= (1 − vegetationCover · stabilisation)` (Cordonnier 2017, above)
with `vegetationCover` zeroed by the burn. The first wet season after a fire does years of erosion
in months: rilling on the slopes, and **post-fire debris flows** from the burned basins (`05`
runout, fed by the failure model's now-unprotected soil). If the brief says "years after the
fire", the scar should be *gullied*, not just black.

**Tier.** Spread: P (Rothermel 1972). Post-fire response: P (Shakesby & Doerr 2006). The burned
*look* — char, snags, mosaic — is an L-tier composition of materials + scatter + the ecosystem
reset; no graphics paper, none needed.

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
