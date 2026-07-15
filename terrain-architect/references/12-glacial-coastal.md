# Glacial & Coastal

Contents: [Glacial: why it matters](#glacial-why-it-matters) · [Mass balance](#mass-balance) ·
[Glen's flow law & SIA](#glens-flow-law--the-shallow-ice-approximation) ·
[Glacial erosion](#glacial-erosion) · [Landforms](#glacial-landforms) ·
[Coastal: be honest](#coastal-be-honest) · [Wave exposure](#wave-exposure) ·
[Cliff retreat & beaches](#cliff-retreat--beaches)

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
