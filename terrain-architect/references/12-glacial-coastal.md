# Glacial, Coastal & Marine

Contents: [Glacial: why it matters](#glacial-why-it-matters) · [Mass balance](#mass-balance) ·
[Glen's flow law & SIA](#glens-flow-law--the-shallow-ice-approximation) ·
[Glacial erosion](#glacial-erosion) · [Landforms](#glacial-landforms) ·
[Coastal: be honest](#coastal-be-honest) · [Wave exposure](#wave-exposure) ·
[Cliff retreat & beaches](#cliff-retreat--beaches) ·
[Marine: the honest frame](#marine-the-honest-frame) ·
[Longshore drift & depositional landforms](#longshore-drift--depositional-landforms) ·
[Marine terraces](#marine-terraces) · [Deltas, estuaries, rias](#deltas-estuaries-rias) ·
[Wave base & the submarine profile](#wave-base--the-submarine-profile)

## Glacial: why it matters

**The diagnostic is the valley cross-section.** Fluvial erosion cuts **V**-shaped valleys —
incision concentrates at the channel. Glacial erosion cuts **U**-shaped valleys — erosion is
proportional to basal sliding velocity, which is distributed across the full width of the ice.

That single difference is why glaciated terrain reads as glaciated. If your brief says "alpine"
and you only ran fluvial erosion, the valleys are V-shaped and it will read as wrong to anyone
who has seen a mountain, even if they can't say why.

**Provenance:** **Argudo et al. 2020**, *Simulation, Modeling and Authoring of Glaciers*, ACM
TOG 39(6) (SIGGRAPH Asia). The underlying physics — Glen's flow law and the Shallow Ice
Approximation — is standard glaciology, not graphics.

## Mass balance

Ice accumulates above the **ELA** (equilibrium line altitude) and melts below it.

```
massBalance(z, ELA):
    b = beta * (z - ELA)                        # beta ≈ 0.005–0.01 /yr (m ice per m elevation)
    return min(b, bMax)                          # accumulation saturates; melt does not
```

`bMax` caps accumulation (precipitation is finite — couple it to `13` if you have an orographic
model; the windward side of a range accumulates far more, which is real and visible).

**ELA is the master parameter.** Lower it and glaciers advance and fill the valleys; raise it
and they retreat to cirques. A glacial landscape is authored by choosing an ELA history, not by
painting ice.

## Glen's flow law & the Shallow Ice Approximation

Glen's flow law: ice deforms with strain rate proportional to stress cubed.

```
ε̇ = A · τⁿ            with n = 3, A ≈ 2.4e-24 Pa⁻³ s⁻¹ at 0 °C (temperature-dependent)
```

The SIA integrates this through the ice column, assuming the ice is thin relative to its extent
and that shear stress is dominated by the surface slope. The result is a depth-averaged
velocity:

```
s = h + H                                        # surface = bedrock + ice thickness

ū = -(2A / (n+2)) · (ρ_ice · g)ⁿ · H^(n+1) · |∇s|^(n-1) · ∇s
```

with `ρ_ice ≈ 917 kg/m³`. Then ice thickness evolves by mass conservation:

```
∂H/∂t = -∇·(ū H) + b(z)
```

**The `H^(n+1)` is the whole character of the model.** With `n = 3` that's `H⁴` — flux scales
with thickness to the fourth power. Thick ice flows enormously faster than thin ice, so
glaciers self-organise into fast trunk streams in valleys and near-stationary ice on the
interfluves. That's why glaciers carve valleys and leave arêtes between them.

**Numerics:**
- **This is a diffusion equation and it is stiff.** Explicit timestepping needs
  `Δt < cellSize² / (2·D_max)` where `D` is the effective diffusivity `∝ H^(n+1)|∇s|^(n-1)` —
  which blows up under thick ice. Use an implicit or semi-implicit solve, or subcycle
  adaptively. If someone reports "my glacier sim explodes where the ice is thick", this is it.
- **Compute `∇s` on the surface, not the bedrock.** This is the coupling that makes ice flow
  downhill along the *ice* surface, which can differ from the bedrock slope. Getting it wrong
  gives ice that flows uphill out of overdeepenings — which real glaciers do, and a bedrock-slope
  implementation cannot.
- Guard `H → 0` at the margins; the exponents make the terms singular.

## Glacial erosion

```
ė = K_g · |u_b|^l                                # abrasion; l ≈ 1, K_g ≈ 1e-4
```

`u_b` is the **basal sliding velocity**, not the depth-averaged velocity — erosion happens at
the bed. In a simple model, `u_b = f · ū` with `f ≈ 0.5`, or zero where the bed is frozen
(cold-based ice does not erode; this is why some plateaux survive glaciation untouched — a
detail worth knowing and mostly ignorable).

Add plucking (quarrying) if you want cirque headwalls to work — it scales with the same
velocity but concentrates where the bed is steep and fractured:

```
ė_pluck = K_p · |u_b| · fractureDensity
```

**In the graph:** glacial erosion runs *alongside* fluvial (`04`), not after. A landscape with
glacial history has both — fluvial valleys that were later occupied and reshaped by ice, and
tributaries that weren't. The characteristic **hanging valley** (a tributary whose floor sits
high above the trunk) is exactly what you get when the trunk was glaciated harder than the
tributary. You don't author it; it falls out.

## Glacial landforms

All **L-tier**. The recipes:

| Landform | Falls out of |
|---|---|
| **U-shaped valley** | Distributed basal erosion under a trunk glacier |
| **Cirque** | Plucking at the head of a small glacier, near the ELA. Armchair-shaped hollow. |
| **Arête** | The interfluve between two cirques/valleys, eroded from both sides |
| **Horn** | Three or more cirques meeting. The Matterhorn. |
| **Hanging valley** | Tributary eroded less than the trunk |
| **Overdeepening** | Ice eroding below the outlet — a closed basin the ice could climb out of. **Becomes a lake.** Do not fill it in `03`; it's real. |
| **Fjord** | Overdeepened glacial valley + sea-level rise |
| **Moraine** | Deposition of the eroded load at the margins and terminus. Track it as a sediment field. |

Note that **overdeepenings and fjords are both cases where a genuine closed basin is correct** —
the second exception (after karst, `11`) to the mandatory-fill rule in `03`. Glacial erosion
*creates* depressions, which is why glaciated terrain is full of lakes and fluvial terrain
isn't. If your fill node runs after glacial erosion with no mask, you have erased the most
recognisable signature of the process.

## Coastal: be honest

**There is no canonical graphics paper for coastal erosion.** The catalogue entry "Coastal
Erosion — Various" is correct, and saying so is better than inventing a citation.

What exists: coastal engineering, which is about protecting infrastructure over decades, not
about carving landforms over millennia. **Bruun 1962** (*Sea-level rise as a cause of shore
erosion*, J. Waterways & Harbors Div., ASCE) gives the Bruun rule for shoreline retreat under
sea-level rise. The CERC formula gives longshore transport. Neither is what you want.

**In practice, coastal erosion in terrain tools is a look, not a simulation.** Be upfront about
that. The look is achievable and cheap; it just isn't physics.

## Wave exposure

The one part that's genuinely worth computing, because it's what makes the coastline *vary*
instead of being uniformly eroded.

```
fetch(p, dir, maxDist):
    # how far can wind blow over open water before reaching p?
    d = 0
    while d < maxDist and isOcean(p - dir * d):
        d += cellSize
    return d

exposure(p):
    e = 0
    for i in 0..N-1:
        φ = 2π * i / N
        w = max(0, dot((cos φ, sin φ), prevailingWind))      # weight by wind rose
        e += w * sqrt(fetch(p, (cos φ, sin φ), maxDist))     # wave energy ~ sqrt(fetch)
    return e / N
```

This is structurally the same sweep as horizon AO (`06`) — and it can use the same
Timonen & Westerholm O(1) machinery. Exposed headlands get high fetch, sheltered bays get low.
That asymmetry drives everything.

## Cliff retreat & beaches

```
coastalStep(h, seaLevel, exposure):
    # 1. Erode a band around sea level, weighted by exposure
    band = exp(-(h - seaLevel)² / (2 * notchHeight²))        # a notch AT sea level
    h -= K_coast * exposure * band * hardness⁻¹

    # 2. Thermal (05) collapses the undercut cliff above the notch
    thermal(h, talusAngle=rockRepose)

    # 3. Deposit the eroded material in sheltered areas as beaches
    beach = (1 - exposure) * nearShore * (h < seaLevel + beachHeight)
    h += K_deposit * beach * sedimentBudget
```

The three-step loop — **notch, collapse, deposit** — is what produces the whole coastal suite:
the notch undercuts, thermal collapses the overhang into a cliff face, and the debris either
armours the base (slowing retreat) or gets carried to a bay. Iterate it and headlands retreat
faster than bays, which is correct and self-reinforcing until the coast straightens.

**Wave-cut platform.** The flat bench at sea level is the signature. It emerges if `band` is
narrow and `K_coast` is high — the terrain is planed off at exactly `seaLevel` and can go no
lower. If you're not getting one, `notchHeight` is too large.

**Sea stacks and arches** are `L`-tier and **need `11`'s representation warning**: an arch
cannot exist in a heightfield. A sea *stack* can (it's just an isolated column), and it emerges
naturally where a hard bed survives while the softer rock around it retreats — so it requires
spatially varying hardness. With uniform rock you get a straight cliff and nothing else, which
is the usual reason a coastal graph looks boring.

## Marine: the honest frame

"Oceanic erosion" sounds like the sea grinding down the seabed. It mostly doesn't. Wave energy
does work in a narrow band **at and just below sea level**; below **wave base** (~½ the
wavelength — tens of metres for ordinary swell) the water barely stirs the bottom and the seabed
is **depositional**, not erosional. So marine processes in a terrain graph are three things, none
of them "carve the abyss":

1. **The shoreline band** — cliff retreat and wave-cut platform, the `notch → collapse → deposit`
   loop above.
2. **Longshore redistribution** — moving the freed sediment *along* the coast.
3. **Marine deposition** — deltas, beaches, spits, and the smooth equilibrium profile of the
   shoreface.

Same honesty as coastal: **no canonical graphics paper** (`00`, F-tier). What follows is a look
built from the same fetch/exposure sweep, not physics — say so.

## Longshore drift & depositional landforms

Cliff retreat frees a sediment budget (the `beach` term above). Waves approaching the shore at an
angle drive that sediment *along* the coast — longshore (littoral) drift. The transport rate is
classically CERC-shaped:

```
Q_long ∝ sin(2 * (waveAngle − shorelineNormal))       # CERC / littoral drift; peaks near 45° approach
```

The `sin(2·angle)` dependence is the measured basis of the CERC formula (**Komar & Inman 1970**,
*Longshore sand transport on beaches*, JGR 75(30)) — coastal engineering, not graphics.

Route the freed budget downdrift along the shoreline and deposit it where the coast turns away
from the flow or shelters (low `exposure`). What falls out:

| Landform | Where it deposits |
|---|---|
| **Spit** | Sediment carried past a change in coast direction, building into open water |
| **Recurved spit / hook** | A spit whose tip curls landward where refracted waves wrap in |
| **Tombolo** | A spit that reaches an offshore island and ties it to the mainland |
| **Bay-mouth bar** | A spit grown across a bay, sealing a lagoon behind it |
| **Barrier island** | An offshore sediment ridge parallel to a low, sediment-rich coast |
| **Cuspate foreland** | Deposition where two opposing drift directions meet |

All **L-tier** — compositions of drift + deposition + sheltering, not algorithms. `00` carries the
caveat: CERC is coastal engineering, the graphics version is authored. The one quantity worth
actually computing is the drift *direction* from the wave-approach angle relative to the local
shoreline normal — that asymmetry is what makes spits point the right way instead of being
symmetric blobs.

## Marine terraces

Run the shoreline loop (notch → collapse → deposit) not at one sea level but across a **sea-level
or uplift history**. Each stillstand planes a bench at its own level; tectonic uplift (or a
sea-level fall) then lifts that bench clear, and the next stillstand cuts a new one below it. The
result is a **flight of marine terraces** — a staircase of old wave-cut platforms climbing inland,
the signature of an uplifting coast (the Californian and New Zealand coasts are the textbook
cases).

```
for stand in seaLevelHistory:            # each (level, duration)
    repeat ∝ stand.duration:  coastalStep(h, stand.level, exposure)
    h += upliftField * dt                # tectonics between stands lifts the finished bench
```

The single-stand case is the wave-cut platform above; the *sequence* is how you author an
uplifted coast — one stand for one clean terrace, several for the staircase. Do **not** fill the
flat benches in `03`; like glacial overdeepenings they are real, deliberate flats.

## Deltas, estuaries, rias

Where a river (`03`, `04`) meets the sea it drops its load — fluvial transport capacity collapses
in standing water. This is **deposition-dominant hydraulic erosion at a base level** (`00`, L-tier
"Deltas, alluvial fans"): keep the erosion model running with sea level as the base and let
sediment accumulate at the mouth. Delta *shape* is a competition — river supply vs wave
redistribution (above) vs tide — so the same longshore machinery decides whether you get a
bird's-foot delta (river wins) or a smooth arcuate one (waves win).

The drowned cases are the marine counterpart to the glacial **fjord** above:

- **Ria** — a river valley drowned by sea-level rise. A dendritic, branching inlet (it's a flooded
  *fluvial* network), where a fjord is U-shaped and straight (a flooded *glacial* one). Same
  operation as the fjord — valley plus sea-level rise — applied to a different valley.
- **Estuary** — the tidal, brackish reach of a drowned river mouth. For a heightfield it's just the
  flooded lower valley via the sea-level flood fill of `03`, never a bare height threshold.

## Wave base & the submarine profile

The reason not to model the seabed as eroded: below **wave base** the sea does not carve. Two
practical consequences:

- **Don't run cliff-retreat erosion below wave base.** Gate the `band` term above to a few metres
  around sea level; deeper than that, waves don't reach the bottom and any erosion you apply is
  fiction that flattens bathymetry you wanted to keep.
- **Shape the nearshore as an equilibrium profile, not a carved one.** The shoreface settles into a
  smooth concave-up curve — depth ∝ distance^⅔, the **Dean (1991)** equilibrium beach profile
  (coastal engineering, not graphics). Author it as a graded ramp from shoreline to shelf break,
  then let deposition (deltas, longshore) modify it. This reads correctly and costs nothing;
  trying to *erode* a seabed into shape does not.
