# Geological Formation

Contents: [The central claim](#the-central-claim) · [Strata](#strata) · [Terracing](#terracing) ·
[Folding](#folding) · [Lithology & erodibility](#lithology--erodibility) ·
[Outcrops, mesas, badlands](#outcrops-mesas-badlands) · [When the heightfield fails](#when-the-heightfield-fails) ·
[Karst & caves](#karst--caves) · [Weathering & soil production](#weathering--soil-production) ·
[Volcanic landforms](#volcanic-landforms) · [Impact craters](#impact-craters)

## The central claim

**Strata are a material field, not a height operator.**

This is the whole chapter. Real stratified landscapes — mesas, badlands, the Grand Canyon,
hoodoos — are not produced by carving steps into a height field. They are produced by
**erosion acting on rock of varying hardness**. Hard beds resist and form cliffs and caprock;
soft beds retreat and form slopes. The steps are an *output*.

Almost every terrain tool ships a "Terrace" node that quantises height directly. It is a fake,
it is often good enough, and you should know it's a fake, because the two approaches fail
differently:

| | Terrace node (height op) | Layered `K` (material field) |
|---|---|---|
| Cost | One node | Erosion must run |
| Steps follow | Absolute elevation | The bed geometry — so they *fold*, *tilt*, *pinch out* |
| At a valley | Steps cut across it, unrelated to the drainage | Caprock forms a rim, slopes below — correct |
| Overhangs | Impossible | Possible (with the right representation) |
| Reads as | Contour lines on a model | Geology |

Use the terrace node when it's a look. Use layered `K` when the brief says "badlands" or
"mesa" and means it.

## Strata

The material at a point depends on its **stratigraphic coordinate** — its depth within the
bed sequence — not on its current elevation.

```
stratCoord(p, h):
    s = h                                        # horizontal beds: strat coord = elevation
    s += tilt.x * p.x + tilt.y * p.y             # tilted beds (regional dip)
    s += foldAmp * sin(dot(p, foldDir) * foldFreq)   # folded beds — see below
    s += warpAmp * fbm(p * warpFreq)             # irregularity; beds are never planar
    return s

layerAt(s, bedTable):
    # bedTable = ordered list of (thickness, hardness, colour, ...)
    # Bed thickness must vary — uniform beds are the tell-tale of a fake.
    return bedTable[lookup(s mod totalThickness)]

K(p, h)     = layerAt(stratCoord(p, h), bedTable).erodibility
talus(p, h) = layerAt(stratCoord(p, h), bedTable).reposeAngle
```

Then feed `K` into stream power (`04`) or the pipe model's erodibility, and `talus` into
thermal (`05`). Erosion produces the landform.

**Bed thickness must be non-uniform.** A `sin` or a uniform modulo gives evenly-spaced steps,
which is exactly what a terrace node gives — you've done the expensive thing and got the cheap
result. Use an authored table, or a noise-driven thickness sequence with a plausible
distribution (log-normal is a reasonable stand-in for real bed thicknesses).

**Provenance:** the layered-representation idea is **Beneš & Forsbach 2001**, *Layered Data
Representation for Visual Simulation of Terrain Erosion* (SCCG). **Št'ava et al. 2008** (`04`)
carries it into the pipe model with bedrock/regolith separation. Musgrave's strata (in *Texturing
& Modeling*) is the height-op version. There is no canonical paper for the specific formulation
above — it's the obvious synthesis.

## Terracing

The height op. Fine when you want the look.

```
terrace(h, levels, sharpness):
    q = h * levels
    f = fract(q)
    f = smoothstep(0, 1, pow(f, sharpness))      # sharpness > 1 → flat treads, sharp risers
    return (floor(q) + f) / levels
```

Two fixes that cost nothing and remove most of the fakeness:

1. **Warp `h` before quantising**, not after: `terrace(h + amp*fbm(p), ...)`. The steps now
   wander rather than following perfect contours.
2. **Non-uniform levels.** Replace `floor(q)` with a lookup into an authored level table. Real
   beds are not equally thick.

**Do not run terrace after erosion.** It quantises the height field, which destroys the
drainage geometry — the rivers now run through steps rather than down. It's a `?`-shaped
question in the Legal Order: it belongs upstream, before flow routing, or it belongs only in
the material field where it doesn't touch height at all.

## Folding

Anticlines (up-folds) and synclines (down-folds). Purely a coordinate transform on the
stratigraphic coordinate — the beds fold, the topography follows only after erosion cuts into
them.

```
fold(p, h):
    # a simple sinusoidal fold train
    s = h + amp * sin(dot(p, dir) * freq + phase)
    # a single anticline
    s = h + amp * exp(-dot(p - axis, n)² / (2*sigma²))
    return s
```

The interesting result: fold the beds, then erode. Erosion cuts through the anticline crest
and exposes the *older* (deeper) beds in the middle, surrounded by concentric outcrops of
younger beds. That bullseye pattern is the classic breached-anticline map view, and you get it
for free — it is not something you could author. This is the strongest argument for the
material-field approach.

No canonical paper. It's structural geology applied as a warp.

## Lithology & erodibility

`K` is the single most useful material property, and it's a scalar.

| Rock | Relative `K` | Notes |
|---|---|---|
| Unconsolidated sediment / regolith | 5–20× | Erodes first, always |
| Shale, mudstone | 2–5× | Forms slopes |
| Sandstone | 1× | The reference; forms cliffs and caprock |
| Limestone | 0.5–2× | Depends on water chemistry — dissolves, doesn't abrade |
| Granite, basalt | 0.1–0.3× | Forms resistant highs |

These are ratios, not absolutes — the absolute `K` is calibrated once against the desired
relief in `04`. Spatially varying `K` costs one texture fetch in the erosion loop and buys:
differential erosion, caprock, outcrops, structural valleys, resistant ridges. **It is the
highest value-per-cost addition to any erosion node**, and most implementations omit it.

**Faults** (`02`) belong here, not in the height field: a fault is a line of *weakened rock*,
so implement it as a local reduction in `K`. Erosion then exploits it and cuts a valley along
the fault — which is what real faulted terrain looks like. Displacing height directly gives you
a step that erosion has no reason to respect.

## Outcrops, mesas, badlands

All **L-tier** — landforms, not algorithms (`00-index.md`). The recipes:

```
Mesa / butte      = hard caprock bed over soft beds + fluvial erosion + thermal
                    The caprock protects; the soft rock retreats; cliffs form at the caprock edge.
                    Butte = a mesa that has retreated until it's small. Same node graph.

Badlands          = high uplift + soft, uniform, poorly-consolidated rock + high drainage density
                    + minimal vegetation (so no soil cohesion)
                    The signature is drainage density: badlands are what you get when EVERY
                    hillslope is channelised. Push the channelisation threshold down (03).

Outcrop           = rockMask from (slope > tan 40°) ∪ (regolithDepth ≈ 0) ∪ (convex curvature)
                    Emerges automatically if you run layered K — you don't author it.

Cuesta / hogback  = tilted beds + differential erosion. Set `tilt` in stratCoord. Asymmetric
                    ridges: gentle dip slope, steep scarp. Free.
```

Nobody has published "the mesa algorithm" and nobody will. If asked for a paper, say so.

## When the heightfield fails

A heightfield is a function `h(x,y)` — one height per column. This makes **overhangs,
arches, hoodoo caps, sea caves, and karst impossible by construction.** No amount of
cleverness in the erosion loop changes that.

This is a principal-level call and it must be made early, because the representation decision
is not reversible cheaply:

| Need | Representation |
|---|---|
| Terrain with slopes, cliffs, valleys | Heightfield. Cheap, fast, tools exist. |
| Overhangs, arches, natural bridges | **Layered material stack** per column (Peytavie et al. 2009, *Arches*, CGF 28(2)) — a column stores an ordered list of (material, thickness) including air gaps |
| Caves, karst, full 3D | Volume / SDF. Marching cubes or dual contouring to mesh (`08`). |

**Peytavie's Arches** is the right middle ground and it's under-used: it keeps the
column-based structure (so erosion, flow routing, and analysis mostly still work) but permits
voids. If the brief is "cliffs with a few arches", this is the answer, not a full voxel
terrain.

If someone asks for arches in a heightfield pipeline, the honest answer is that the
representation forbids it — and then offer the two ways out. Agreeing to try is worse than
useless.

## Karst & caves

Dissolution, not abrasion. Limestone dissolves along fractures; the drainage goes underground;
the surface collapses into sinkholes (dolines) and the caves become a network.

**Provenance:** **Paris et al. 2021**, *Synthesizing Geologically Coherent Cave Networks* (CGF)
is the real reference for the cave network. The surface expression (sinkholes, poljes,
disappearing streams) has no canonical paper.

Surface-only approximation, if you don't need the caves:

```
karstSurface(h, solubleMask):
    sinkholes = poissonDisk(domain, r) filtered by solubleMask        # 07
    for each sinkhole:
        h -= depth * radialFalloff(d / radius)                        # inverted cone
    # Route flow (03) — the sinkholes are now pits.
    # Do NOT fill them. This is the one case where a pit is correct:
    # the water genuinely goes underground and leaves the surface network.
```

That last note is the interesting one: karst is the exception to the mandatory depression
handling in `03`. In karst, sinks are real. Fill them and you've destroyed the landform. Mark
them with a mask so the fill node skips them.

### Tower & cone karst

The dramatic karst *mountains* — the towers of Guilin and Halong Bay (**fenglin**), the cone
clusters of the wet tropics (**fengcong**) — are dissolution in thick, pure limestone under a
high water table. The mechanism is **differential vertical lowering to a base level**: corrosion
concentrates at the water table, so the soluble surface is planed down toward it while the most
massive, least-fractured rock survives as near-vertical towers standing out of a flat, alluviated
plain.

```
towerKarst(h, solubleMask, waterTable):
    # Towers survive where the rock is massive (low fracture density); everything
    # else dissolves down toward the water table (Ford & Williams 2007).
    fracture   = fbm(p * freq)                        # 01/07 — low fracture = massive = future tower
    resistance = smoothstep(hi, lo, fracture) * solubleMask
    lower      = (1 - resistance) * max(0, h - waterTable)
    h -= rate * lower                                  # massive columns barely lower → towers
    # The inter-tower plain alluviates to a flat base level, giving the steep tower/plain contact:
    h  = max(h, waterTable)  where not resistance
```

Two honesty notes, both straight from the central claim of this file:

- **Base level is the master parameter**, exactly as ELA is for glaciers (`12`). Lower the water
  table and the towers grow taller and steeper; raise it and they drown to a plain. You author
  tower karst by choosing the base level, not by sculpting towers.
- **A heightfield gets the towers but not the truth.** Mature tower karst is undercut, cave-
  riddled, and overhanging — the voids the heightfield forbids (see *When the heightfield fails*
  above). You get the steep-tower-and-flat-plain silhouette; for the notched bases and through-
  caves you need Peytavie's Arches or a volume. There is **no canonical graphics paper for tower-
  karst surface morphology** — the cave network is Paris et al. (2021), the surface is the
  composition above grounded in **Ford & Williams (2007)**.

## Weathering & soil production

The erosion models take erodibility `K` and regolith depth as *given*. Where does the regolith come
from? **Bedrock weathers into soil at a rate that falls exponentially as the soil above it
thickens** — the **soil production function** (**Heimsath, Dietrich, Nishiizumi & Finkel 1997**,
*The soil production function and landscape equilibrium*, Nature 388, measured with cosmogenic
¹⁰Be/²⁶Al):

```
soilProduction(soilDepth):
    return P0 * exp(-soilDepth / h_star)     # P0 ~ 0.05–0.3 mm/yr on bare rock; h_star ~ 0.3–0.5 m
```

Why it matters for terrain:

- **Bare rock weathers fastest; thick soil insulates the rock beneath it.** A freshly stripped
  ridge (thin soil) produces regolith fast; a stable footslope (thick soil) produces almost none.
  This closes a loop: erosion thins soil → speeds production → limits how bare a slope can get.
- **It is the field that feeds `K` and vegetation.** Regolith depth *is* the erodible layer
  (Št'ava's regolith/bedrock split, `04`); it gates rooting and the material masks (`06`). Track it
  as `∂(soil)/∂t = production − erosion` (in rock-equivalent thickness) and soil comes out thick in
  hollows and thin on noses — which is both correct and the reason hollows are green and noses rocky.

This is the **production** side of the regolith the whole erosion pipeline consumes, and most
graphs simply assume regolith exists. Adding it is one exponential, and it makes every
soil-depth-driven mask physical instead of painted.

## Volcanic landforms

The catalogue lists "volcanic cones, calderas, craters" as **F/L-tier** — primitive + noise +
erosion. What the primitive must get right is the **edifice shape**, which is set by eruption style;
the dimensions are catalogued in **Pike & Clow 1981** (*Revised classification of terrestrial
volcanoes and catalog of topographic dimensions*, USGS Open-File Report 81-1038 — height, flank
width, and summit-depression size for 697 volcanoes).

| Edifice | Shape | Flank slope | Built by |
|---|---|---|---|
| **Shield** | Broad, low dome | 2–10° | Fluid basaltic lava flows (Stora 1999) |
| **Stratovolcano** | Steep cone, concave-up | 20–35° | Alternating lava + tephra; steepens to the summit |
| **Cinder/scoria cone** | Small steep cone | ~30–33° | Ballistic tephra — a pile at the repose angle (`05`) |
| **Caldera** | Collapse basin | — | Roof collapse after a large eruption — a closed depression |
| **Lava dome** | Bulbous mound | steep | Viscous lava piling at the vent |

```
volcano(style):
    base = cone/dome primitive (10) with the flank slope from the table (Pike & Clow 1981)
    if stratovolcano: profile is CONCAVE-UP (steep summit, gentle base) — not a straight cone
    summitCrater/caldera = inverted cone at the top (closed basin — mask it from the 03 fill)
    lava flows (Stora 1999) run down channels; a tephra mantle (05 aeolian deposit) thins outward
    then fluvial erosion (04) cuts radial BARRANCOS — deep radial gullies
```

The detail that ages a volcano: **radial barrancos** — fluvial erosion of an unconsolidated cone
cuts deep radial gullies, so a young cone is smooth and an old one is deeply rilled. Run erosion
(`04`) on the cone and they fall out; a perfectly smooth cone reads as brand new.

### Lava flows, fields & lakes

Lava is the one material that **changes stack role**: it arrives as a *fluid* layer (`08`) and
freezes into *new bedrock* (fresh basalt, low `K`). The graphics simulation is **Stora et al. 1999**
(`00`); the morphology physics is **Hulme 1974** (*The Interpretation of Lava Flow Morphology*,
GJRAS 39): lava is a **Bingham fluid — it has a yield stress** — and that one property explains the
landforms. A Newtonian fluid would spread into a thin sheet; a yield-stress fluid stops when the
driving stress drops below yield, so flows have **steep snouts, finite thickness, and levées**.

```
lavaFlow(h, vent, supply, yieldStress):
    while supply:
        route a pulse down steepest descent (03) from the vent
        stop where driving stress < yield:  τ = ρ g t sinθ < τ_y      # Hulme 1974
        thickness t ≈ τ_y / (ρ g sinθ)              # THICKER on gentle slopes — inverse of water
        deposit more at the pulse margins → LEVÉES; later pulses channelise between them
        if crusted (old surface): tube-fed — the flow extends far with little heat loss
        h += deposit                                 # freezes into new bedrock: low K (above)
    surface texture from viscosity & strain rate     # Macdonald 1953 → the 18 material:
    #   pahoehoe (fluid, slow strain)  = smooth, ropey sheets
    #   ʻaʻā     (viscous, fast strain) = clinkery rubble over a molten core
    #   block    (most viscous)         = smooth-faced angular blocks
```

**Sources: vents and fissures.** Lava issues from a **point source** (a volcano's vent — the
edifices above) or a **line source**: a *fissure* along a rift or fault (`02` — a fault is a crack,
and eruptive fissures follow them), the "curtain of fire" that feeds Iceland- and Hawaiʻi-style
eruptions. This is the same source-term pattern as water (`03`): vent : fissure :: spring :
boundary inflow. A fissure feeds many lobes at once across its whole length, so it builds **broad
flow fields with no cone** — and at the largest scale, stacked fissure-fed flows build **flood
basalts** (the Deccan and Columbia River traps): a basalt *plateau*, hundreds of flows thick, whose
later fluvial dissection gives the stepped "trap" landscape via the caprock/mesa machinery above.
L-tier — a composition of the flow node along a `02` fault line, stacked.

What falls out: a **lava field** is stacked, overlapping flow lobes with levéed channels — a
composition of this one node, run per eruption pulse, exactly the scale-recursion pattern. A
**lava lake** is ponded lava in a pit crater — a *fluid surface at a level in a closed basin*, the
same spill-plane machinery as a water lake (`03`), on the no-fill list, with a crusted surface of
dark plates and incandescent cracks (the `08` emissive material below).

**Lava worlds (the Mustafar brief).** A planet-scale lava landscape is the multi-biome composition
(`13`) plus the layer stack (`08`) with the **fluid layer's fluid swapped**: "sea level" becomes
*lava level*, coasts become lava shores, rivers are lava routed by `03` at Bingham rheology
(levéed, thick, slow), lakes are lava lakes — and the whole `12` shoreline machinery reads across
once you substitute the fluid. Tier: the rheology is P (Hulme 1974), the world is an L-tier
composition; there is no "lava planet paper" and none is needed.

## Impact craters

Only a "crater" primitive exists today, but real craters have a well-constrained morphology that
**changes with size** (**Melosh 1989**, *Impact Cratering: A Geologic Process*, Oxford Univ. Press;
**Pike 1977**, *Size-dependence in the shape of fresh impact craters on the Moon*). Two regimes,
with a transition around **~3 km on Earth and ~15 km on the Moon** — the transition diameter
scales as **~1/g** (Melosh 1989), so it is *smaller* where gravity is stronger:

- **Simple crater** (small): a bowl. Raised, overturned **rim**; **ejecta blanket** draping outward
  ~1 crater radius and thinning roughly as `r⁻³`; depth ≈ 1/5 of diameter.
- **Complex crater** (large): shallower, with a **central peak** (rebound uplift), **terraced walls**
  (slumped rim), and a flat floor. Depth-to-diameter *decreases* with size (Pike 1977).

```
crater(D):
    R = D/2
    profile(r):                                   # radial
        if r < R:  bowl (paraboloid) to depth d(D)          # d/D ~0.2 simple, less if complex
        else:      rim uplift + ejecta * (r/R)^-3           # ejecta thins outward
    if D > D_complex:                             # ~3 km Earth / ~15 km Moon — scales ~1/g (Pike 1977; Melosh 1989)
        add centralPeak (rebound) near r = 0
        terrace the inner walls (slump blocks)
        flatten the floor; the crater is shallower
    rimCrest ~ 0.04·D above the surroundings (Pike 1977 ratios)
    secondary craters + rays: scatter (07) smaller craters + high-albedo radial streaks
```

Melosh's ejecta scaling and Pike's depth/diameter and rim-height ratios are the numbers to hit. A
crater that is a plain Gaussian dimple — no raised rim, no ejecta, no central peak at size — reads
as a golf divot, not an impact. Crater size also scales with **gravity** (Melosh's π-group scaling),
which matters off-Earth — see the planetary doctrine in `SKILL.md`.
