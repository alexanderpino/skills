# Glacial, Coastal & Marine

Contents: [Glacial: why it matters](#glacial-why-it-matters) · [Mass balance](#mass-balance) ·
[Glen's flow law & SIA](#glens-flow-law--the-shallow-ice-approximation) ·
[Glacial erosion](#glacial-erosion) · [Landforms](#glacial-landforms) · [Glacial deposition](#glacial-deposition) ·
[Outburst floods & megafloods](#glacial-outburst-floods--megafloods) ·
[Coastal: be honest](#coastal-be-honest) · [Wave exposure](#wave-exposure) ·
[Cliff retreat & beaches](#cliff-retreat--beaches) ·
[Lacustrine (lake) shores](#lacustrine-lake-shores) ·
[Marine: the honest frame](#marine-the-honest-frame) ·
[Longshore drift & depositional landforms](#longshore-drift--depositional-landforms) · [Coastal dunes & foredunes](#coastal-dunes--foredunes) ·
[Marine terraces](#marine-terraces) · [Deltas, estuaries, rias](#deltas-estuaries-rias) ·
[Wave base & the submarine profile](#wave-base--the-submarine-profile) ·
[Tides & the intertidal zone](#tides--the-intertidal-zone) · [Biogenic muddy coasts](#biogenic-muddy-coasts--mangroves--cheniers) · [Coral reefs & atolls](#coral-reefs--atolls) ·
[Seafloor, ridges & submarine processes](#seafloor-ridges--submarine-processes)

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

**The `H^(n+1)` is the whole character of the model.** With `n = 3` the depth-averaged *velocity*
scales as `H⁴` — and the ice *flux* `ū·H` as `H⁵`. Thick ice flows enormously faster than thin
ice, so glaciers self-organise into fast trunk streams in valleys and near-stationary ice on the
interfluves. That's why glaciers carve valleys and leave arêtes between them.

**Numerics:**
- **This is a diffusion equation and it is stiff.** Explicit timestepping needs
  `Δt < cellSize² / (2·D_max)` where `D` is the effective diffusivity of the *flux*,
  `D = (2A/(n+2))·(ρg)^n · H^(n+2) · |∇s|^(n−1)` — which blows up under thick ice. Use an
  implicit or semi-implicit solve, or subcycle adaptively (`15` prefers subcycling on GPU). If
  someone reports "my glacier sim explodes where the ice is thick", this is it.
- **Compute `∇s` on the surface, not the bedrock.** This is the coupling that makes ice flow
  downhill along the *ice* surface, which can differ from the bedrock slope. Getting it wrong
  gives ice that flows uphill out of overdeepenings — which real glaciers do, and a bedrock-slope
  implementation cannot.
- Guard `H → 0` at the margins; the exponents make the terms singular.

**The step loop** — the implementable form, in the `04`/`19` pattern (double-buffered):

```
glacierStep(bed, H, Δt):
    # 1. Mass balance (climate, 13): accumulate above the ELA, melt below
    s  = bed + H
    H += clamp(β * (s − ELA), −∞, bMax) * Δt ;  H = max(H, 0)
    melt = the negative part → a WATER SOURCE for 03's discharge (the coupled loop, below)

    # 2. SIA diffusivity on the ICE SURFACE gradient (numerics above)
    D  = (2A/(n+2)) * (ρ_ice g)^n * H^(n+2) * |∇s|^(n−1)      # zero where H ≈ 0

    # 3. Ice transport — adaptive explicit subcycling (stable Δt' = 0.25 cellSize² / max(D))
    repeat until Δt consumed:  H += ∇·(D ∇s) * Δt'

    # 4. Erosion at the bed
    u_b  = f * ū                                # sliding fraction; 0 where cold-based
    bed -= K_g * |u_b|^l * Δt                    # + plucking where steep & fractured
    # eroded volume → a moraine/sediment field at margins and terminus (the mass budget)
```

**The coupled fluvial–glacial loop.** "Glacial runs alongside fluvial" (the Legal Order's 6b) has
a concrete shape: an outer loop where `glacierStep` erodes under the ice, the mass-balance melt
feeds `03`'s discharge as a source term (proglacial rivers are melt-fed — it's why they surge in
summer, `03`), and the fluvial backbone (`04`) erodes the ice-free terrain. Timesteps differ by
orders of magnitude — ice wants years, stream power tolerates millennia (`04`) — so run the fluvial
solve every N glacier steps, not in lockstep.

**Glacier parameter reference** (order-of-magnitude starts; tune against the U-valley/ELA checks):

| Parameter | Start | Notes |
|---|---|---|
| `A` (Glen) | ~2.4×10⁻²⁴ Pa⁻³ s⁻¹ at 0 °C | The Cuffey & Paterson 2010 recommended value; Arrhenius `A₀·exp(−Q/RT)`, colder ice stiffer |
| `n` | 3 | Glen's exponent |
| `ρ_ice` | 917 kg/m³ | |
| `β` (mass balance) | 0.005–0.01 /yr | m of ice per m of elevation |
| `bMax` | ~0.5–2 m/yr | Accumulation cap — precipitation is finite (couple to `13`) |
| `ELA` | **the master parameter** | Author its *history*, not the ice |
| `f` (sliding fraction) | ~0.5 | 0 where cold-based (no erosion) |
| `K_g`, `l` (abrasion) | ~1e-4, l ≈ 1 | `05`-style erosion constant |
| `Δt` | years–decades | With subcycling from the CFL above |

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

## Glacial deposition

Erosion (above) carves the valleys; the material it removes has to go somewhere, and where it lands is
the **diagnostic** half of a glacial landscape. A U-valley in cross-section can be mistaken for a big
fluvial one — but nothing except ice leaves **drumlins, eskers and erratics**, so the deposits, not
the troughs, are what say "ice was here". They all draw on one budget: the volume eroded by
`glacierStep` (above) *is* the sediment supply, so `Σ deposited = Σ eroded` — the same
mass-conservation discipline as fluvial (`SKILL.md`). Don't let a deposition node mint sediment the
ice never excavated. Two families, split by whether **water sorted the load**.

**Ice-laid (till — unsorted, dumped directly by the ice):**

| Landform | Recipe |
|---|---|
| **Moraine** (already noted) | The eroded load released at the ice margin: **terminal** at the snout, **lateral** on the flanks, **medial** where two glaciers merge, **ground** under the sole. A terminal moraine dams a proglacial lake (`03` — a real basin). |
| **Drumlin** | Streamlined till hill, **blunt up-ice, tapered down-ice**, in swarms under fast ice. Author the *form*, not the genesis (below): streamline a till field along the ice-flow vector, sized by Clark et al. 2009. |
| **Till plain / ground moraine** | The low-relief till sheet smeared under the sole — a thickness blanket that mutes the underlying relief, not a feature in its own right. |
| **Erratic** | A boulder carried far from source and dropped. Pure `07` scatter of **out-of-lithology** clasts (`11` material tag ≠ local bedrock) — the cheapest, most legible ice fingerprint there is. |

**Meltwater-laid (glaciofluvial — sorted, kin to the outburst floods below):**

| Landform | Recipe |
|---|---|
| **Esker** | A sinuous sand-and-gravel ridge — the cast of a subglacial meltwater tunnel. Route it, but *not* on the bed (see the Shreve callout). |
| **Kame** | An ice-contact stratified mound — a delta or fan built against or on top of stagnant ice, left standing when the ice melts out. |
| **Kettle** | A pit where a buried ice block melted out. **A closed basin — it joins the `03` no-fill list** (with overdeepenings and karst); it usually holds a pond. Kame-and-kettle country is hummocky ice-stagnation terrain. |
| **Outwash plain / sandur** | Braided meltwater deposits fanning beyond the terminus — the `03` braided-river / `16` fan process driven by the mass-balance melt discharge, fining downstream. |
| **Tunnel valley** | A large subglacial meltwater channel, cut then often part-infilled; kin to the esker and the jökulhlaup below. Frequently overdeepened → a lake chain (another `03` no-fill case). Genesis debated — steady vs outburst drainage (Kehew et al. 2012). |

**The esker routing insight (Shreve 1985).** An esker is a river deposit, but it does *not* obey the
bed's topography — so a heightfield router (`03`) run on the bed places it wrong. In a water-filled
subglacial tunnel the water pressure ≈ the ice overburden, so flow follows the gradient of the
**hydraulic potential** φ = ρ_i·g·s + (ρ_w − ρ_i)·g·b, where `s` is the ice surface and `b` the bed.
Because ρ_i ≈ 11·(ρ_w − ρ_i), the **ice-surface slope outweighs the bed by ~11×**: route on
`(11·s + b)`, essentially the ice surface. The visible consequence, and the tell that sells it, is
that eskers **run uphill over the bed and cross divides at low passes**, trending with ice flow rather
than down the local slope. A router on the bare bed pools them in hollows — exactly wrong.

**Drumlin genesis is unresolved — so don't claim it (`?`).** Whether drumlins form by a deforming
bed, a subglacial instability, or catastrophic meltwater floods is a genuine, decades-old debate with
no winner. The honest move is the skill's standard one: author the **form** — blunt-up-ice till ridges
aligned to the ice-flow field, elongation ~2–4 and length 250–1000 m, obeying Clark et al. 2009's
`E_max ≈ L^(1/3)` limit — and make **no mechanism claim**. Anyone selling a "drumlin algorithm" with a
physical story is backing one side of an open argument.

**Alignment is machinery you already have.** Drumlins and eskers both trend with **ice flow**, exactly
as dunes trend with wind (`05`): the SIA surface gradient `∇s` (above) is a ready-made direction field
that orients both. And their closed basins — kettles, tunnel valleys — join overdeepenings and fjords
on the `03` no-fill list; a fill node run after glaciation with no mask erases them.

**Tier.** All **L** compositions over the erosion budget, with three anchors: **Shreve 1985** (esker
tunnel routing, **P**), **Clark et al. 2009** (drumlin morphometry & scaling, **P**), **Kehew et al.
2012** (tunnel valleys, **P** review); drumlin *genesis* is **?**. The synthesis reference for the
whole suite is **Benn & Evans 2010**, *Glaciers and Glaciation*. **The tell:** deposits align to ice
flow, erratics sit on foreign bedrock, and the deposited volume balances the eroded troughs — reverse
the flow direction and the drumlins point the wrong way.

## Glacial outburst floods & megafloods

The largest freshwater floods in Earth's history were not rain — they were **water released
catastrophically from behind or beneath ice**. Two source mechanisms, one landform signature:

- **Jökulhlaup (subglacial outburst)** — meltwater or a subglacial lake escapes through a tunnel in
  the ice, and the tunnel **enlarges by frictional melting as flow rises, in a runaway feedback**
  (Nye 1976): more discharge melts a wider tunnel, which carries more discharge. The hydrograph is the
  tell — a **slow exponential rise over days, then an abrupt cutoff** as the lake empties and the
  tunnel creeps shut:
  ```
  dS/dt = m/ρ_ice − creepClosure(S, p_ice − p_water)     # melt-open minus Glen-law closure
  Q     = (S/n) · R_h^(2/3) · √(hydraulicGradient)        # Manning; grows as the tunnel S grows
  # lake mass balance closes the loop: dV_lake/dt = Q_in − Q,  a runaway until V_lake → 0
  ```
  Nye 1976; extended by Clarke 1982, 2003; Icelandic type locality Björnsson 2003. Walder & Costa
  1996 note that *non-tunnel* drainage (an ice dam failing bodily) gives a **higher, sharper** peak
  than tunnel drainage.
- **Glacial-lake-outburst flood (ice-dam failure)** — an ice-dammed lake fails and empties in days.
  Glacial Lake Missoula doing exactly this is the **Channeled Scabland** source (Bretz 1923, 1969 —
  the once-ridiculed "outrageous hypothesis", later vindicated; Baker 1973; Baker & Nummedal 1978).

Route the released hydrograph over the DEM as an **extreme-discharge flood** (`03` routing, `04`
erosion at very high shear stress) and the **megaflood landform suite** falls out — all L-tier
composition targets, not algorithms:

| Landform | How it forms |
|---|---|
| **Scabland** | Basalt stripped of its loess/soil cover where shear stress exceeds threshold; anastomosing scoured channels |
| **Coulee** | A large flood-cut canyon, often now dry (Grand Coulee) |
| **Giant current ripples** | Gravel dunes, wavelength ~20–200 m, transverse to flow — bedforms scaled to flood *depth*, not to a normal river |
| **Streamlined residual island** | A teardrop hill of pre-flood loess, blunt upstream and tapered downstream, left where shear stayed below threshold |
| **Cataract & plunge pool** | A recessional knickpoint (Dry Falls) with a deep scour basin — a waterfall (`04`) at megaflood scale |
| **Loess island** | An uneroded silt upland isolated between scoured tracts |

```
megaflood(h, hydrograph):
    for Q in hydrograph:                              # the Nye / Missoula release curve
        route Q over the DEM (shallow water; 03)
        τ = ρ_water · g · depth · slope               # bed shear stress
        if τ > τ_c(material):  h -= K_e·(τ − τ_c)·Δt  # strip loess → scabland; cut coulees
        deposit gravel where velocity drops (eddies, expansions) → giant-ripple field
        retreat knickpoints headward at scarps        → cataracts / Dry Falls (04)
    # cells that never exceed τ_c survive as streamlined loess islands
```

**Watch for** treating these as ordinary river valleys — the diagnostic is **scale mismatch**: ripples
and bars sized to a flood hundreds of metres deep, dry coulees far too big for any current stream, and
cataracts with no river above them. On a dry world (Mars' outflow channels, `20` entry 29; Beggar's
Canyon) the *same* suite with the water switched off is the signature of a vanished catastrophic
flood.

**Verify.** The outburst hydrograph rises exponentially then cuts off abruptly (not a slow symmetric
bump), and every landform is scaled to a flood hundreds of metres deep — dry coulees, giant ripples,
streamlined loess islands; **scale mismatch is the signature** (`09`, *Checks for the extended
families*).

**Tier.** The jökulhlaup tunnel-enlargement physics and hydrograph are P (Nye 1976; Clarke 1982,
2003; Walder & Costa 1996; Björnsson 2003); the Missoula-flood interpretation of the Scabland is P
(Bretz 1923, 1969; Baker 1973). The individual megaflood landforms are L compositions over
extreme-discharge `03`/`04`.

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

One refinement the sweep misses: real waves **refract** — shoaling bends crests toward shallow
water, *focusing* energy onto headlands and spreading it in bays, which sharpens the same
asymmetry. Fold it in as an exposure multiplier from coastline convexity (shore-plan curvature,
`06`) rather than simulating waves.

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

## Lacustrine (lake) shores

The coastal loop is **water-body-agnostic**. A large lake has fetch, waves, and a shoreline, so
`coastalStep` runs unchanged with `waterSurface = lakeLevel` and the `fetch` sweep taken over the
lake instead of the ocean (`isOcean → isWater`). The mountain lakes of `03` are not just flat
plates — given enough fetch they erode their own shores. What you get:

- **A wave-cut bench at lake level** — the lacustrine wave-cut platform, planed at the lake
  surface exactly as the marine one is planed at sea level.
- **Lake terraces from a lake-LEVEL history** — the freshwater twin of *Marine terraces* below.
  Run the loop across a sequence of lake stands; each stand planes a bench, then the level drops
  (outlet incision, a drying climate) and strands the bench above the modern shore. The
  foundational study is **Gilbert 1890** (*Lake Bonneville*, USGS Monograph 1); the Bonneville and
  Provo shorelines ringing the Utah basins are the type example — and they are *horizontal* (a
  dead-flat contour wrapping the topography), which is the tell that a bench is an old shoreline
  and not a structural bed (`11`).
- **Beaches, spits, and bay bars** from lake longshore drift (small lakes have too little fetch —
  skip it; a tarn is a mirror, not a wave machine).
- **Deltas prograding into the lake** where a river enters — the classic **Gilbert delta**
  (topset / foreset / bottomset beds), named for the same G.K. Gilbert. The lake case of the delta
  recipe in *Deltas, estuaries, rias* below.

**Lake level is not authored free-hand** — it is the spill elevation from depression handling
(`03`). Lower the outlet and the whole shoreline suite drops, leaving the terrace flight above:
the same *notch → collapse → deposit across a level history* machinery as marine terraces, pointed
at an inland basin instead of the sea.

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

## Coastal dunes & foredunes

A **coastal dune** is what onshore wind does with a sandy beach — the humid-coast cousin of the desert
erg, and the defining landform of the Dutch, Danish and Atlantic sandy shores (and the crest of every
barrier island, above). Three things make it a *different* problem from a Namib dune (`05`): the **sand
source is the beach** (marine sand kept supplied by longshore drift, above — not deflated off a basin
floor), the **wind is onshore**, and **vegetation is a first-class control**, not the rare gate it is
in the desert. Marram / *Ammophila* grass grows up *through* burial and traps saltating sand, so the
plants build the dune and the dune feeds the plants — a biotic feedback the desert model lacks.

**The sequence.** Dry backshore sand → onshore wind → sand caught by pioneer plants on the upper beach
→ an **incipient foredune** → an established **foredune ridge** running *parallel to the shore* → a
**dune belt** landward, breaking into **blowouts and parabolic dunes** (`05`) where the cover fails or
supply is high. Which incipient form appears is set by the *vegetation pattern*, not the wind:
scattered plants make shadow-dune hummocks, continuous pioneer cover makes a laterally-continuous
ridge — **Hesp 1989** distinguishes four incipient-foredune types on exactly that basis.

**The implementable model — DECAL (Baas 2002).** Werner's bare-sand slab CA (`05`) has no plants, so it
cannot make a foredune. The coastal analogue is **Baas 2002's DECAL**: the same slab transport plus a
**vegetation field that grows under moderate burial, dies under erosion or too-deep burial, and locally
raises the deposition probability**. That one feedback self-organises foredunes, blowouts, parabolic
dunes and nebkhas out of the plant–sand coupling — it is "Werner for a vegetated coast", reusing the
shadow-zone and availability-mask machinery you already have (`05`) under the onshore wind field (`13`).

**What caps the height (Durán & Moore 2013).** A foredune does not grow without limit: its **maximum
size is set by vegetation, not wind** — the dune rises until plant growth can no longer keep pace with
the burial rate, so height is a **growth-rate-vs-sand-supply balance**. Expose vegetation vigour and
sand supply and the dune ceiling falls out instead of being authored.

**The Dutch coast as a composite.** The classic North Sea stack is these pieces in a row: a wide
dissipative **beach** (above) → a **foredune ridge** and **dune belt** (here) → behind them the
**Wadden barrier islands** (above) and **tidal flats** (below) → and, reclaimed inland, **polders and dikes**
(the anthropogenic surface, `20`). Every rung was already in the skill; the coastal dune was the
missing one.

**Tier.** All **L** as generated landforms — beach sand budget + onshore wind + a vegetation feedback —
grounded by **P** sources: Hesp 1989, 2002 (foredune initiation and form), Baas 2002 (the DECAL
vegetated-dune model), Durán & Moore 2013 (vegetation sets the size ceiling). **The tell:** the dunes
run *parallel* to the shore, *anchored* by vegetation, fronted by the beach that feeds them — kill the
vegetation feedback and you get bare migrating desert dunes, which is the wrong coast.

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

## Tides & the intertidal zone

Sea level is not a constant — it **oscillates** with the tide, and the band swept between high and
low water is the **intertidal zone**, one of the most distinctive coastal strips. This is the clean
example of the doctrine that water is a **fluid layer with a moving surface** (`08` layer stack),
not solid ground: the geometry underneath doesn't change, the *water* rises and falls over it. For
terrain the tide is an **authored oscillation of the water plane**, not a simulation — the astronomy
(the gravitational pull of Moon and Sun) is a look here.

```
waterSurface(t) = meanSeaLevel + 0.5 * tidalRange * tidalCurve(t)    # tidalCurve ∈ [−1,1], ~semidiurnal
intertidalWidth = tidalRange / tan(shoreSlope)                       # wide on flat coasts, narrow on steep
intertidalMask  = solidTop in [meanSeaLevel − 0.5*range, meanSeaLevel + 0.5*range]
```

What falls out of the range and the shore slope:

- **Tidal flats** — a large range over a gentle shore exposes broad flats of mud/sand at low water
  (a near-flat depositional surface just below high tide). A steep shore gives a narrow intertidal
  band; a flat shore gives a wide one — the width is `range / slope`.
- **The intertidal is a material/ecology band, not a new height.** Mark `intertidalMask` (`06`) for
  wet-sand, mud, and salt-marsh materials and scatter (`07`); the geometry is the same shoreface —
  only the water moves across it, drowning the flat and draining it twice a day.
- **Tides drive the water layer's dynamics.** A boat floats, the flat drowns and dries on a cycle,
  and none of it touches the solid collision height (`08`) — which is exactly why water must be
  emitted as its own dynamic surface, not baked into the terrain.

Honest tier: **F-tier**, a look. Real tides are astronomy; for terrain you author the range and the
curve, and the geomorphic products — tidal flats, salt marshes, the intertidal zone — are
compositions on top of the shoreface.

## Biogenic muddy coasts — mangroves & cheniers

The intertidal section above is the *physical* muddy coast; two features make it a **biological** one,
and both are progradation engines.

**Mangroves** are the tropical intertidal counterpart of the salt marsh (above): a **biogenic
geomorphic agent**, not just vegetation on a shore. Prop-roots and canopy impede the tidal flow, so
fine cohesive mud flocculates and settles — a mangrove forest **traps ~80% of the suspended sediment**
a spring flood tide carries in and raises the bed ~0.1 cm/yr (Furukawa, Wolanski & Mueller 1997) —
while the same drag **damps waves and currents**, so the forest builds intertidal mudflats and
**progrades a tropical muddy shoreline** (Woodroffe 1992). Surface elevation is held by **both** mineral
sedimentation and **belowground root/peat accumulation**, which is how mangrove soils **keep pace with
sea-level rise** — the control on whether the coast progrades, holds or drowns (Alongi 2008). Implement
it as a biogenic mask on tropical intertidal cells (`13` biome + `06` intertidalMask) that (a) raises
fine-sediment deposition, (b) attenuates incident wave energy (`12` wave exposure), and (c) adds an
organic elevation term — the mangrove counterpart of the marsh, kin to the nebkha's
vegetation-traps-sediment logic (`13`).

**Cheniers** are the coarse punctuation on such a coast: **isolated sand or shell ridges resting on,
and separated by, mudflat** (Otvos & Price 1979). The diagnostic is exactly that — a coarse ridge on a
**muddy** substrate — and it forms when a **lull in mud supply** lets episodic wave reworking winnow and
pile the coarse fraction into a beach ridge; renewed mud supply then buries its flanks and pushes the
shoreline seaward again (Augustinus 1989). So each ridge is a **former shoreline and a pause**, and a
**chenier plain** (alternating ridges and mudflats) is a stratigraphic record of episodic progradation.
Build it as mud progradation (mangrove / tidal flat) **stamped with coarse longshore ridges** (`12`
longshore) during supply lulls. **The tell** that it's a chenier and not a beach-ridge strand plain is
the substrate: mud beneath and between the ridges, not a continuous sand body (Otvos 2000).

**Tier.** Both **P**: mangroves (Woodroffe 1992; Furukawa et al. 1997; Alongi 2008), cheniers (Otvos &
Price 1979; Augustinus 1989). As *generated* landforms both are **L** — compositions over the shoreface,
sediment supply and a biogenic/longshore mask — grounded by those P sources.

## Coral reefs & atolls

An atoll is the one marine landform that is **built up, not carved**. It is Darwin's subsidence
sequence (**Darwin 1842**, *The Structure and Distribution of Coral Reefs* — confirmed a century
later by drilling to volcanic basement at Enewetak): a volcanic island subsides while reef-
building coral grows *upward* to stay in the sunlit shallows, so the reef outlives the island
that seeded it.

```
volcano → fringing reef → barrier reef + lagoon → atoll (ring, no island)
          reef hugs shore   island subsides,        island gone; the reef ring
                            a lagoon opens behind    keeps pace with sea level
```

The mechanism is a race between subsidence and coral accretion — cheap to model as a height
update:

```
reefStep(h, seaLevel, subsidence, Δt):
    # 1. The volcanic edifice sinks
    h -= subsidence * Δt                                   # the whole island subsides

    # 2. Coral grows upward toward the light — only in the photic zone, faster in moving water
    depth  = seaLevel - h
    growth = coralRate * inPhotic(depth) * waveEnergy(exposure)    # exposure/fetch from above
    #   inPhotic(depth): ~1 just below the surface, → 0 below ~50 m and above the waterline
    h += growth * Δt
    h  = min(h, seaLevel + reefCrestHeight)               # coral can't grow into the air

    # 3. Lagoon fill: dead coral + carbonate sand accumulate to a shallow flat floor
    inLagoon = enclosedBy(reefRing) and depth > lagoonDepth
    h += lagoonFill * inLagoon * Δt
```

**What each detail buys:**
- **The photic-zone gate is what pins the crest at sea level.** Coral grows only where light
  reaches — a few metres down to ~50 m. Too deep and growth stops, so the reef can only ever
  *catch up* to the surface as the island sinks, never overshoot. That is the whole trick.
- **Wave-energy weighting (`12` exposure).** Reefs build fastest on the windward, wave-washed
  rim, so a real atoll ring is *asymmetric* — wider and shallower to windward, often breached to
  leeward. Uniform growth gives a suspiciously perfect ring.
- **The lagoon is a flat, not a bowl.** Do not let flow routing (`03`) treat it as a pit to
  drain — it is a closed marine basin at sea level, the same skip-the-fill case as a crater lake.

**Fringing vs barrier vs atoll is one parameter: cumulative subsidence.** A little → fringing
reef; more → the lagoon opens to a barrier reef; enough to drown the island → atoll. You author
the stage by choosing how far the edifice has sunk, exactly as ELA authors a glacier and the
water table authors tower karst (`11`).

**Tier.** No graphics paper — atolls are **L-tier**, a composition of a volcanic primitive
(`02`/`11`), subsidence, photic-zone coral accretion, and wave exposure. The subsidence theory is
Darwin 1842; the recipe above is the honest way to realise it in a heightfield.

### Coral as an ecosystem — growth forms & zonation

`reefStep` above treats the reef as an **accreting height** — right for the atoll's *shape*, but a
real reef surface is a **living cover**, and it is placed like one: the marine sibling of the
vegetation ecosystem in `13`/`07`. Coral really is a kind of foliage — a benthic community whose
**growth forms zone by light and wave energy**, which is exactly the constraint-based scatter of `07`
driven by masks from `06`. Two environmental drivers set everything:

- **Light falls off with depth** (Beer–Lambert), and coral growth saturates with it (a
  photosynthesis–irradiance curve):
  ```
  I(z) = I₀ · exp(−K_d · z)          # K_d ≈ 0.03–0.06 /m clear water, 0.1–0.2 /m turbid
  growth ∝ tanh(I(z) / I_k)          # saturates above I_k; → 0 near the compensation depth
  ```
  This is the same photic gate that pins `reefStep`'s crest at sea level — here it also selects
  *form*. **Graus & Macintyre 1976** (*Science*) showed by computer simulation that light alone
  controls colony growth form.
- **Wave energy** falls off with depth too (near-bed orbital velocity, linear wave theory) and rises
  on the exposed rim — the `12` exposure/fetch sweep is the cheap proxy. **Chappell 1980** ties coral
  morphology to the *combination* of light and mechanical wave stress.

Growth form is then a **lookup on (light, energy)** — the reef-zonation pattern (Done 1982, 1983):

| Zone | Light | Wave energy | Dominant form |
|---|---|---|---|
| Reef crest / very shallow | high | high | robust branching, encrusting, low massive |
| Reef flat / back-reef | high | low–moderate | massive, hemispherical, digitate |
| Upper fore-reef | high | moderate | tabular / table corals, arborescent |
| Mid–deep fore-reef | moderate → low | low | foliose, plate/laminar (maximise light capture) |
| Near photic limit | low | low | thin plate → encrusting; growth → 0 |

Within a form, **flow sets branch openness** — the accretive-growth models of **Kaandorp et al. 1996**
(*Phys. Rev. Lett.*), **Merks et al. 2003** (*J. Theor. Biol.*) and **Kaandorp & Kübler 2001** show it
as a diffusion-versus-flow competition (a Péclet number `Pe = U·L/D`): strong flow → compact, thick
colonies; weak flow → open, thin branches.

```
coralCover(cell):
    if cell.depth ≤ 0 or cell.depth > photicDepth: return none       # subaerial or aphotic → no coral
    L = tanh(I(cell.depth) / I_k)                                     # light mask (06)
    E = exposure(cell)                                               # wave-energy mask (12 fetch sweep)
    density = L · gaussian(E, E_opt, E_σ) · hardSubstrate(cell)       # colonies/m²; peaks at mid energy
    form    = lookupForm(L, E)                                       # the zonation table above
    openness = clamp(1 − Pe(cell)/Pe_ref, 0, 1)                      # low flow → open branching
    instances = poissonDisk(cell, density, r = colonyRadius(form))   # 07 scatter
    orient branching/tabular colonies into the swell (a 07 direction field)
```

**Spur-and-groove** — the ribbed fore-reef of shore-normal coral ridges (spurs) and sand-floored
grooves — is the reef's most distinctive meso-texture, and it self-organises with the **grooves
pointed into the dominant swell** (Shinn 1963; Storlazzi et al. 2003; **Duce et al. 2016**, who found
groove length and orientation track wave exposure across thousands of grooves). Realise it as a
ridge–valley mask on the fore-reef band (`06` curvature) oriented by swell direction, modulating both
the reef height and the `coralCover` density.

**Verify.** Growth-form zonation is **monotone** with depth and wave energy (branching/encrusting on
the high-energy crest → massive on the flat → plate/foliose deep), and cover **stops** above the
waterline and below the compensation depth — coral on the abyssal plain means the photic gate is off
(`09`, *Checks for the extended families*).

**Tier.** Growth-form-controlled-by-light is P (Graus & Macintyre 1976; Chappell 1980); the
accretive-growth morphogenesis is P (Kaandorp et al. 1996; Merks et al. 2003; Kaandorp & Kübler
2001); zonation is P (Done 1982, 1983); spur-and-groove is P (Shinn 1963; Duce et al. 2016). Placing
the community as density-and-form scatter over `06` masks is the F/L realisation — coral as the
seafloor's foliage layer (`07`), not a new algorithm.

## Seafloor, ridges & submarine processes

*Runnable reference: `reference-impl/analytic.py` (age–depth `d₀+C√age`, GDH1), verified by
`tests/test_analytic.py` — matches the law and flattens for old crust (`09`).*

The atoll that keeps subsiding past the photic zone doesn't stop — it drowns, and its dead flat top
sinks into deep water as a **guyot**. That is the hand-off from the shallow marine story to the deep
one: the ocean floor is terrain too, and it has its own shape-makers. Three matter.

**1. Ridge age–depth subsidence — why ocean basins deepen away from the ridge.** New seafloor is born
hot at a mid-ocean ridge and *sinks as it cools and contracts* with age, following a **√age** law
(half-space cooling; **Parsons & Sclater 1977**):

```
d(t) = d₀ + C · √t          # t = crustal age [Myr];  d₀ ≈ 2500 m, C ≈ 350 m/√Myr  (valid t ≲ 70 Myr)
```

For old crust the curve flattens to a plateau (~5–6 km); the **plate model** GDH1 (**Stein & Stein
1992**) captures both regimes. In a graph this is a **remap of a seafloor-age field to depth** — not
an erosion pass — and it is the correct way to get the ridge-crest-to-abyssal-plain profile that the
margin note in `02` only sketched. The ridge itself is a `02` divergent boundary; the age field grows
outward from it.

**2. Hotspot tracks, seamounts & guyots.** A stationary mantle hotspot under a moving plate builds an
**age-progressive chain** of volcanoes (Wilson 1963; Morgan 1971 — the mantle-plume hypothesis, still
actively debated, so attribute it as a hypothesis, not settled fact). Each edifice ages and subsides
on the same √age curve as it rides away from the source; an emergent volcano truncated flat by waves
and then carried down becomes a **flat-topped guyot** (**Hess 1946**). This is the same `11`-edifice +
subsidence machinery as Darwin's atoll sequence — a guyot is what an atoll becomes when subsidence
outruns coral.

```
for edifice i along the plate-motion line:
    age_i = distanceFromHotspot_i / plateSpeed         # plateSpeed ~ 0.05–0.10 m/yr
    build cone (11);  crest -= subsidence(age_i)        # the same √age subsidence
    if crest ever rose above sea level: planeFlatAtWaveBase → guyot (Hess 1946)
```

**3. Submarine canyons & turbidity currents — the one real deep-water sim.** Below wave base the sea
does not carve (the honesty frame above) — *except* where a **turbidity current** runs: a dense,
sediment-laden underflow that races down the continental slope, cuts submarine canyons, and builds
deep-sea fans. It is a **gravity/density current**, the underwater sibling of the fluvial machinery,
and it has a real layer-averaged model (**Parker, Fukushima & Pantin 1986**; review: **Meiburg &
Kneller 2010**). The three conserved quantities are water, suspended sediment, and momentum:

```
d(U·h)/dx    = e_w · U                        # entrains ambient water (the current grows downslope)
d(U·h·C)/dx  = v_s · (E_s − r₀·C)             # picks sediment up / drops it at the bed
d(U²·h)/dx   = R·g·C·h·S − drag               # driven by excess density × slope
#   U = velocity, h = thickness, C = concentration, R = submerged specific gravity, S = slope
#   Ri = R·g·C·h / U²   (bulk Richardson number)
```

The paper's result is **autosuspension**: when the current entrains more bed sediment than it drops,
`C` and `U` grow downslope — a self-accelerating runaway, and exactly why a turbidity current can run
hundreds of km and carve a canyon. The deposit it leaves fines upward as the flow wanes — the **Bouma
sequence** (Bouma 1962; Middleton 1993).

```
turbidityRun(h, path):                                 # path = steepest descent below the shelf break
    U, C, thick = ignite()
    for step ds along path:
        Ri = R·g·C·thick / U²
        integrate the three equations (RK4) → update U, C, thick
        net = v_s·(E_s − r₀·C)
        if net < 0:  h -= erode(U)      → carves the submarine CANYON
        else:        h += deposit(net)  → builds the FAN lobe; stamp a Bouma bed
```

**Verify.** Seafloor depth tracks `d₀ + C·√age` (flattening for old crust); the turbidity current
self-accelerates then wanes, leaving a deposit that **fines upward** (Bouma) — a flat uniform abyss or
a current that dies on the slope is a missing law or missing entrainment (`09`, *Checks for the
extended families*).

**Tier.** Age–depth subsidence is P (Parsons & Sclater 1977; Stein & Stein 1992). The hotspot/plume
origin of chains is a P-tier *hypothesis* (Wilson 1963; Morgan 1971); guyot truncation is Hess 1946
(P). The turbidity-current model is P (Parker, Fukushima & Pantin 1986; Meiburg & Kneller 2010);
seamounts, guyots, canyons and fans as *landforms* are L compositions over it.
