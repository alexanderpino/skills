---
type: Technique
title: Driver fields — temperature, sun, shadow and flow
description: "The non-height fields a terrain graph carries: why one horizon sweep produces both the solar and the wind-shelter field, what the lapse rate is actually worth, and why these fields need a halo measured in kilometres."
tags: [architecture, tooling, climate, wind, insolation, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: winstral2002, tier: P, locator: "§3 p.528-529, the sentence immediately after Eq. 1 stating that maximum-shelter selection is analogous to solar shading in the horizon function; Eq. (1) defining Sx with a 5 degree azimuth increment; Eqs. (3)-(5) for Sb; §4 p.531 for the search-distance comparison and the significance of Sx100 against elevation, radiation and slope" }
  - { id: dozier2022, tier: P, locator: "§I p.1 for the O(N^2) origin, the order-N method and its attribution; §II-A Eq. (1) and Fig. 2 for the algorithm; §III-C for the tile-halo requirement; §III-E for the measured per-azimuth timing" }
  - { id: minder2010, tier: P, locator: "Abstract — the 6.5 degrees per km assumption named as an assumption, against measured windward annual means of 3.9-5.2" }
  - { id: reda2004, tier: P, locator: "NREL/TP-560-34302 rev. January 2008 — the stated uncertainty of the algorithm and its validity range" }
  - { id: furich2002, tier: P, locator: "the geometric solar radiation model: the viewshed-based occlusion term and the direct/diffuse split it feeds" }
  - { id: forthofer2014, tier: P, locator: "the three-approach comparison — mass-consistent, and the cost against accuracy result across them" }
  - { id: stendardo2020, tier: P, locator: "Abstract p.1 for the 3.4 km at 0.5 m in up to two hours figure; §3.2 Code Listings 1-3 pp.8-9 for the per-point DDA march and the coarse-DTM substitution beyond the tile, taking the minimum of the two results" }
  - { id: minderroe, tier: F, locator: "the 'Fundamentals' section, Eq. (1) — the upslope model's vertically integrated condensation source as moisture flux (rho*q_v) times the topographic slope in the airflow direction — and the sentence that moist ascent over topography alone is typically insufficient, so orographic effects 'mainly modify precipitation during preexisting storms'; Eq. (2) for the Brunt-Vaisala frequency and the dry adiabatic lapse rate of -9.8 K/km; the 'Observations' section for the dense southwestern Olympics gauge network showing precipitation maximising on RIDGE-TOPS over scales of a few kilometres, 'distinct from the rain shadow predicted by the upslope model', attributed to the seeder-feeder mechanism; the Alps paragraph, where storms from a wide range of directions erase 'any simple rain shadow' and produce maxima on both sides; the 'Models' section for what Smith and Barstad (2004) add to the upslope model. An encyclopedia review article, not peer-reviewed primary research — graded on what it is" }
  - { id: ta_graph_runtime, tier: F, locator: "§Side-channel masks & the accumulator pattern — the observation that simulations emit more than their primary field" }
---
# Driver fields — temperature, sun, shadow and flow

A terrain graph carries more than a heightfield. It carries **driver fields**: temperature,
insolation, shadow, and the flow fields for water and wind. These are what make erosion, snow and
vegetation respond to *where* they are rather than uniformly, and they behave differently from
heightfields in ways the runtime has to know about.

This document exists because Gaia had a hole: `thermal-and-aeolian-erosion.md` states that an
aeolian pass "needs a wind field computed first", and nothing produced one.

**Boundary.** `terrain-analysis-masks.md` owns computing slope, curvature, occlusion and wetness as
*masks*. This document owns the same geometry used as *physical drivers*, and the fields that have
no mask analogue. Shadow appears twice on purpose: here it is an input to temperature; drawing
shadows is `lighting-and-shadows`. `flow-routing.md` owns routing water over a heightfield; this
document owns what is different about a **vector field** with direction and magnitude.
`heightfield-raymarching.md` owns the max-mip marcher, which is one of the ways the occlusion
below can be evaluated.

## Use this

**Compute one horizon field by the order-N sweep, and drive both insolation and wind shelter from
it** [winstral2002] [dozier2022].

That is the organising fact of this axis and it is not folklore. [winstral2002] §3 states it
outright: *"The selection of a maximum shelter-producing pixel based on slope is analogous to the
determination of solar shading within the horizon function used in radiation modeling."* The
maximum upwind slope that decides whether a cell is sheltered from wind is the same quantity as the
horizon angle that decides whether it is shaded from sun. One sweep, two fields.

**Why it wins.** The horizon field is **sun-independent**. It is a property of the terrain alone, so
one bake serves every sun position, every hour of every day, and — per the sentence above — the wind
field as well. Nothing else in this document has that property, and it is what makes a driver-field
pass affordable at all.

**What it beats.** *Per-cell ray marching over the heightfield* — the obvious implementation, and
measurably the wrong one, quantified below. *A full CFD solve for wind* — the most accurate of the three, and
slower, but not as far outside an authoring budget as its reputation: [forthofer2014] reports
30–90 minutes per simulation on a laptop [forthofer2014]. *Aspect alone as a proxy for insolation* — cheap and blind: it
knows which way a slope faces and not whether the ridge across the valley blocks it, which is the
whole point of a horizon.

**And compute precipitation, because it is nearly free and it is what erosion actually wants.** One
dot product against the wind field you already have, clamped and renormalised, turns `stream-power.md`'s
drainage area `A` into a real discharge `Q` — see `## Precipitation, the field that decides where
the water is` below. Every erosion document in this corpus assumes uniform rainfall until you do.

⚠️ **The two fields want the same sweep and very different search distances.** Wind shelter is
useful at **100–300 m** — [winstral2002] §4 found `Sx` at 100 m the strongest predictor of snow
depth, and tested 50 m to 2000 m. The insolation horizon needs **kilometres**. Same algorithm, same
code path, two parameterisations; running one and reusing it for the other at the wrong distance is
a real and easy mistake. [winstral2002] Fig. 4 shows why it matters: at 300 m the shelter-defining
pixel lies across the valley and a cell reads sheltered; at 100 m the search never crosses and the
same cell reads exposed. **The search distance chooses which landform does the sheltering.**

## The horizon sweep, and who actually invented it

The method is: for each azimuth, sweep the grid in that direction maintaining the horizon's
**upper convex hull** incrementally, which gives each cell's horizon in amortised constant time
[dozier2022] §II-A. The naive alternative — comparing every cell against every other — is O(N²) and
is what the field did first.

⚠️ **It is a hull, not a running maximum of the angle, and the difference is not cosmetic.** An
elevation angle is measured *from the observer*, so it cannot be carried from one cell to the next:
the horizon at cell `i` is `max over j>i of (z_j − z_i)/(j − i)`, and every denominator changes when
`i` moves. Carrying a running max of the angle instead: on a flat profile with a single 5-unit peak
ten cells away, the true horizon rises `0.50, 0.56, 0.63 … 5.00` toward the peak, the hull sweep
reproduces it **exactly** (error 0.0), and the running-max-of-angle returns **5.0 at every cell** —
a 10× overestimate that reports an entire flat plain as shadowed. `terrain-analysis-masks.md` states
this correctly; an earlier revision of this document did not.

⚠️ **Attribution correction, now applied in both places.** Gaia credited the sweep to a 2010 paper;
`terrain-analysis-masks.md` carries the corrected lineage as of the same change that added this
document. [dozier2022] §I records it: the order-N horizon method is **Dozier, Bruno & Downey
(1981)**, *Computers & Geosciences* 7(2), 145–151, and "many, if not most, radiation calculations
over mountains now use that method". Twenty-nine years earlier than the citation Gaia carried. The
1981 paper itself could not be obtained here, so it is **named and not cited** — the tier rules
forbid manufacturing a locator for a paper nobody has opened.

## Ray marching is not the modern answer, and the numbers are not close

The tempting 2026 move is to replace the sweep with hardware ray tracing. The evidence does not
support it, and the reason is structural rather than generational.

| Method | Hardware | Problem size | Time |
|---|---|---|---|
| Hull sweep [dozier2022] §III-E | 16 CPU cores | 3601² ≈ 13 Mcell, **per azimuth** | **~2 s** |
| Per-point DDA ray march [stendardo2020] | GPU (CUDA) | ≈ 46 Mcell, **580 directions** | **1–2 hours per tile** |

⚠️ **Those two rows are not a like-for-like comparison, and reading them as one is a trap this
document nearly set.** Normalise: the sweep on the larger grid at the same 580 directions is
`3.566 × 580 × 2 s ≈ 4136 s ≈ 1.15 h` — *inside* the band it would appear to beat. The apparent
thousandfold gap is the **direction count**, not the algorithm. This document's own rule two
sections down — a number quoted without saying what consumes it is meaningless — applies to its
author first.

**What actually survives, and it is enough.** Both methods cost roughly `directions × O(cells)`, so
per direction they are comparable. The sweep wins for two structural reasons instead:

- **A terrain horizon needs 8–16 azimuths, not 580.** The 580 figure is an urban solar cadaster
  resolving a sky vault [stendardo2020]; a terrain shelter or shading field is not that problem. At
  16 azimuths the same sweep on the same grid is about **2 minutes**.
- **The horizon field is sun-independent.** One bake serves every sun position and every hour, and
  per [winstral2002] the wind field as well. Marching per sun position buys nothing back.

⚠️ **The baseline above is a NAIVE marcher, and that limits what it can be used to dismiss.**
[stendardo2020]'s method is a per-point DDA through the raster, one step at a time
(§3.2, Listings 1–3). It is not the hierarchical maximum-mip traversal that
`heightfield-raymarching.md` recommends — and that document explicitly names "sun shadows,
long-range occlusion" among the things its one shared kernel serves. Beating a per-point DDA does
not beat a max-mip marcher, and this document does not claim it does. If you already ship that
kernel, using it here is reasonable; what it will not give you is the sun-independence below.

⚠️ **No peer-reviewed comparison of a hardware-RT bake against a horizon sweep on a heightfield
could be found.** A direct search returned vendor and blog material only, which this skill does not
cite. So the honest position is: **the sweep is the recommendation, the RT crossover is an open
question**, and the reason to suspect RT could compete is that a BVH over a 4k heightfield's ~33 M
triangles is the real obstacle — which displaced-micro-mesh hardware exists to address. That lead
was not read here and is not cited.

**The long-baseline problem has a cheap shipping answer that is not a longer ray.**
[stendardo2020] evaluates distant obstruction on a **100× coarser** heightfield — 50 m instead of
50 cm — marching the coarse grid only outside the tile, since inside it the fine model is better
information. A mip of the terrain, not a longer ray. It composes with [dozier2022] §III-C's
tile-halo requirement: a wide halo or a coarse far field, pick one.

⚠️ **Combine the two resolutions with a disjunction, not a minimum** — and note the obvious choice
is the one the source rejects. Taking the minimum of fine and coarse is [stendardo2020]'s *earlier*
method (§2); §3.2 discards it because it "does not give the correct result when local obstacles …
are not situated in the same direction as remote relief features", since cumulative shadowing from
both "should be considered … instead of merely taking the minimum of both SVFs". The shipped method
tests both resolutions **inside the marching loop** in a given direction and takes "the disjunction
of both results". An earlier revision of this document cited §3.2 for the minimum — the section
that exists to refute it.

⚠️ **Direction count is set by what the field feeds, not by the geometry.** Production values in the
sources span **8–16** azimuths for a terrain mask, **32–64** for a view factor [dozier2022], and
**137 then 580** for an urban solar cadaster [stendardo2020]. A number quoted without saying what
consumes it is meaningless.

## Temperature, and a constant that is a convention

Temperature falls with elevation, and the number every tool uses is 6.5 °C/km. It is worth knowing
what that number is.

⚠️ **It is a standard-atmosphere convention, not a measurement of the terrain you are modelling.**
[minder2010] measured surface lapse rates over the Cascades and found annual means of **3.9–5.2
°C/km on the windward side** — "substantially smaller" than the conventional value, which the paper
names explicitly as an assumption that gridded climate models rely on.

For a terrain tool this matters in one specific way: **the snow line is the T = 0 isotherm**, so an
over-steep lapse rate puts the snow line too low and does it consistently. If you want snow at a
particular elevation, tune the lapse rate to put it there and say that you did — do not cite 6.5 as
though it were measured for your mountain.

The second term is insolation: a slope facing the sun is warmer than one facing away, and a slope
whose horizon is high is colder than its aspect alone suggests. [furich2002] is the peer-reviewed
model behind ArcGIS's solar radiation tool and couples the two — viewshed-based occlusion feeding a
direct/diffuse split — which is the chain from the horizon field to a temperature offset.

⚠️ **Do not oversell that chain.** [winstral2002] §4 found that in an alpine basin net potential
radiation was **not** a significant predictor of snow depth (p = 0.38), nor was elevation (p = 0.88),
while wind redistribution was. Winstral's own hedge is that "complex process interactions can
diminish measures of statistical significance taken from individual parameter tests", and the
quantities differ — [furich2002] models temperature, [winstral2002] models accumulation rather than
melt. But a document claiming insolation drives the snow line should not pretend that result does
not exist. **Where wind moves snow, wind wins.**

## Sun position is a parameter, not a field

Worth stating because it decides where it lives in the graph: the sun's position is two scalars —
azimuth and elevation — derived from latitude, date and time. It is a **scene parameter**. The
fields are what it produces when crossed with the horizon.

[reda2004] is the citable algorithm. Its uncertainty is far below anything terrain rendering can
perceive, so the practical rule is simply not to invent an approximation: use the published one,
and spend the attention on the horizon field instead, which is where the cost and the error are.

The runtime consequence is the interesting part. A sun-position change invalidates **every field
downstream of it** — insolation, temperature, snow cover, vegetation — which is a large cone, and
it is why the sun-independence of the horizon field matters so much. Structure the graph so the
expensive sweep sits *above* the sun parameter and only the cheap projection sits below it. That is
the same move `layering-filters-and-masks.md` makes with masks, for the same reason.

## Flow fields for water and wind

A flow field is a **vector** field — a direction and a magnitude per cell — and that alone
distinguishes it from anything else in the graph. `flow-routing.md`'s receivers are a routing
*decision* over a heightfield; a wind field has no heightfield to descend.

[forthofer2014] compares three approaches for fine-scale surface wind: a coarse weather model, a
mass-conserving solver, and a momentum-conserving (CFD) one. Both of its models were "designed to
be run by casual users on standard personal computers", with the CFD one at 30–90 minutes per
simulation on a laptop — so the gap is real but smaller than folklore suggests.

⚠️ **Take the paper's caveat with its recommendation, because it lands where this document goes
next.** [forthofer2014] found that *both* models had reduced accuracy **on the lee side**, and that
the momentum-conserving model did better there. Lee-slope deposition is exactly what `Sb` below is
for, so the cheap option is weakest at the feature you most want from it.

**But there is a third option that fits a node graph better, and it is peer-reviewed.**
[winstral2002] derives the wind field's *magnitude* from terrain geometry alone, with no flow solve
at all: `Sx`, the maximum upwind slope within a search distance, read directly as a shelter
parameter. Increasingly negative `Sx` means constriction and higher speed; increasingly positive
means shelter and lower speed [winstral2002] §3. It is the same sweep as the horizon field, so a
graph that already computes horizons gets a defensible wind magnitude for almost nothing.

[winstral2002] Eqs. (3)–(5) add `Sb`, an upwind *break in slope* that detects flow separation and
marks lee-slope deposition zones. That is peer-reviewed grounding for the lee-shadow step that
terrain tools usually carry as folklore.

## Precipitation, the field that decides where the water is

Every erosion document in this corpus takes water as given. `stream-power.md` uses drainage area
`A` as the stand-in for discharge, and `flow-routing.md` accumulates one unit per cell. That is a
**uniform-rainfall assumption**, stated nowhere, and precipitation is the driver field that removes
it. It matters more than temperature does: temperature decides where snow and vegetation go,
precipitation decides where the erosion happens at all.

**The upslope model is the whole of the cheap version.** Condensation rate is the moisture flux
times the terrain slope **in the direction of the airflow** — `S ∝ ρ · q_v · (v · ∇h)`
[minderroe] Eq. (1). Three things fall out of that one expression and they are the three things an
authoring tool needs:

- It is `v · ∇h`, a **directional derivative**, not `|∇h|`. A slope facing the wind condenses; the
  same slope facing away does not. Steepness alone is the wrong input, and it is the mistake a
  slope mask invites.
- The lee is **negative** and that is the rain shadow: descending air warms and dries, and both
  cloud and precipitation evaporate [minderroe].
- You already have the wind direction. This section costs one dot product against the field
  `## Flow fields for water and wind` above already computes, which is why precipitation is the
  cheapest driver field in this document and the one most often left out.

⚠️ **Clamp at zero and then re-normalise, or your continent loses half its water.** `v · ∇h`
integrates to zero over any terrain that comes back to its own level — every windward slope has a
lee. Measured, 256², central differences: on smoothed noise and on an isolated Gaussian ridge the
sum is zero to −3.4e-05 of `Σ|v · ∇h|` (to machine precision if the domain wraps), and **49.6% to
50.1% of cells carry a negative value** at every wind direction tried. So an unclamped field hands
negative rainfall to half your map, and clamping alone then delivers **0.50×** the mean magnitude
you asked for — the base rate silently halves. Clamp, then rescale so the domain total matches the
rate you intended. The base rate is the parameter an artist wants; the pattern is what the terrain
computes.

The one terrain where this does not bite is the one with no lee: a full-width monotonic ramp
measures **0.0%** negative cells and a normalised sum of exactly `+1.0`. If your test scene is a
tilted plane you will not see this bug, and every real heightfield will trip it.

### Three ways the cheap model is wrong, in the direction that matters here

The upslope model is a teaching tool, and this corpus's rule is to say where a recommendation
breaks before recommending it.

**It has no timescales, so the pattern is pinned to the wrong place.** Condensate does not fall
where it forms — it is advected downwind while it converts to precipitation and while it falls. The
standard fix is the linear theory of Smith and Barstad (2004), which [minderroe]'s *Models* section
describes as building on the upslope model by adding linearized mountain-wave airflow dynamics,
**microphysical conversion and fallout timescales**, and lee-side evaporation. ⚠️ That paper is
named here and **not cited**: it is behind the AMS paywall and was not opened, so the description
above is [minderroe]'s and the two conversion/fallout timescales it introduces are not quoted,
because quoting a constant from a paper nobody here read is exactly what this skill refuses to do.
If you implement it, read it. Practically: the missing timescales are why an upslope field puts the
maximum on the windward face and a real one puts it further downwind, often past the crest.

**At the resolution a terrain tool works at, the observed pattern is not the modelled one.**
[minderroe] reports a dense gauge network in the southwestern Olympics measuring large differences
in annual mean precipitation over **scales of a few kilometres, maximising on ridge-tops** — and
states plainly that this "is distinct from the rain shadow predicted by the upslope model". The
mechanism is seeder-feeder: precipitation falling from aloft through low-level orographic cloud
grows by collecting droplets. **A few kilometres is your grid.** So the upslope model is defensible
for the range-scale windward/lee contrast and is *measured wrong* at the scale where you place
individual ridges — and the correction, ridge-tops wetter than the model says, is one you can apply
as a curvature-weighted term without pretending it came from the physics.

**One wind direction is what makes a rain shadow sharp.** [minderroe]'s Alps paragraph is the
control experiment: that range receives storms from a much wider range of directions, which erases
"any simple rain shadow" and produces precipitation maxima on **both** sides. A tool with a single
authored wind vector will always produce a cleaner windward/lee split than a real range of the same
shape. If the scene wants an Alpine look rather than a Cascades look, **average the field over a
few weighted directions** — it is the same dot product run three or five times, and it is the
difference between a coast range and an interior massif.

⚠️ **And the field is a modifier, not a generator.** [minderroe] states that moist ascent over
topography alone is typically insufficient to generate precipitation, and that orographic effects
"mainly modify precipitation during preexisting storms". So the honest form of the parameter is a
**base rate times a terrain multiplier**, not a rate the terrain produces. A tool that lets the
multiplier reach zero has invented a desert that the physics does not support.

### What it costs downstream, which is the reason to bother

Precipitation enters erosion as **discharge**, not as area: `Q = Σ(P · cellArea)` over the
contributing cells, accumulated by exactly the machinery `flow-routing.md` already describes — the
accumulation is a weighted sum instead of a count, and nothing else about it changes. Substituting
`Q` for `A` in the stream-power law is a one-line change to `stream-power.md`'s update and it is the
single highest-value use of any field in this document, because it is what makes the wet side of a
range incise and the dry side keep its relief.

⚠️ **It is also a global field with a non-local dependence, so it breaks tiling the same way flow
accumulation does** — see `## Fetch, which is the same sweep and a different accumulator

⚠️ **Two documents route here for fetch and this section exists because they were routing to
nothing.** `coastal-erosion.md` calls exposure "the input that matters" and `sea-ice.md` needs a
wind field over water; both pointed at the horizon sweep above. That was wrong, and the reason is
worth stating because it is the general trap with reusing a sweep.

**Fetch is the over-water distance the wind has blown before it reaches a cell** — the quantity
that sets wave height. The horizon sweep computes an **angle**; fetch is a **distance**. They run
the same traversal and accumulate different things, and one cannot be recovered from the other:

- **The angle saturates where fetch does not.** Land 10 m high at 50 km subtends a horizon angle of
  **0.0115°**, and 10 m high at 5 km subtends **0.1146°** — a tenfold change in fetch buys a tenth
  of a degree, which is inside any threshold you would set on `Sx` and inside the quantisation of a
  heightfield stored at metre precision. Meanwhile 1000 m of land at 20 km gives **2.86°**, so a
  distant mountain reads as more sheltering than a near sandbar, which is backwards for waves: the
  sandbar blocks the fetch and the mountain does not.
- **The search distances are an order of magnitude apart.** `Sx` is useful at 100–300 m
  [winstral2002] §4 and the insolation horizon at kilometres; wave fetch matters at **tens of
  kilometres**, because that is the scale over which wind does work on a sea surface.

**So run the same per-azimuth traversal and accumulate a first-hit distance instead of a maximum
angle**: march from each water cell into the wind, stop at the first cell above sea level, record
the distance, cap it at a maximum fetch. It is the same `O(N)` sweep per direction, the same halo
argument, the same cache position above the wind parameter — everything the horizon section says
about cost and invalidation carries over unchanged. What does not carry over is the *value*, and
reusing the baked horizon field because the code is shared is the mistake this section is here to
stop.

⚠️ **No canonical source; standard practice is** to average the fetch over a small arc of azimuths
rather than take a single ray, because a one-ray fetch flickers between a gap and a headland as the
wind rotates by one azimuth step. The arc width is a tuning constant and no source read here fixes
it. Effective-fetch methods of this shape are standard in coastal engineering, and nothing in this
corpus's bibliography was opened for them, so nothing here is cited for it.

## What these fields do to the runtime` below. Worse than the horizon
sweep, in fact: the horizon's dependence has a bounded search distance, and an advected
precipitation field's does not. Compute precipitation whole-domain at a coarse resolution and
upsample it, rather than trying to tile it; the field is smooth at the scale that matters and the
error from upsampling is far smaller than the error from a seam.

## What these fields do to the runtime

Driver fields are not heightfields, and three properties follow:

- **They are global, or nearly so.** A horizon at kilometre baselines reaches far outside any tile.
  [dozier2022] §III-C states the halo requirement directly, and it is large. In
  `node-graph-runtime.md`'s classification these are **local operators with an enormous support
  radius**, not global-ordered ones — an important distinction, because that means a halo *does*
  work, it is just expensive, and the coarse-far-field trick above is the way to shrink it.
- **They are shared by many consumers.** [ta_graph_runtime] observes that simulations emit more than
  their primary field, and driver fields are the upstream version of the same thing: one horizon
  field feeds insolation, temperature, snow, vegetation and wind. That fan-out is exactly the case
  where the union rule in `layering-filters-and-masks.md` and early cutoff in
  `node-graph-runtime.md` pay off most.
- **They are vector or multi-channel.** A wind field is two components; a horizon field is one value
  per azimuth. The port model must carry that, and a runtime that assumes every edge is a scalar
  heightfield will force these into side channels, which is where undeclared inputs start.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Shaded north slopes still melt out first | Aspect used as the insolation proxy; it cannot see the ridge across the valley | Compute the horizon field and drive insolation from it [furich2002] |
| The snow line sits consistently too low | 6.5 °C/km taken as measured when it is a standard-atmosphere convention; real windward means are 3.9–5.2 [minder2010] | Tune the lapse rate to place the snow line, and say that is what you did |
| Snow accumulates evenly across a ridge that should scour and drift | No wind field; only melt is modelled | Add `Sx` shelter from the same sweep [winstral2002]; where wind moves snow it beats radiation |
| The wind shelter field marks the wrong cells | Search distance chosen without reference to the landform — at 100 m the search never crosses the valley, at 300 m it does [winstral2002] Fig. 4 | Choose `dmax` by which landform should do the sheltering; 100–300 m is the measured useful range |
| Reusing the insolation horizon for wind gives nonsense | Same algorithm, but the insolation baseline is kilometres and the wind baseline is hundreds of metres | Run the sweep twice with different `dmax`; the code is shared, the parameter is not |
| The occlusion bake takes hours | Per-cell, per-direction ray marching — 1–2 hours per tile on a GPU against ~2 s per azimuth for the sweep on CPU [stendardo2020] [dozier2022] | Use the order-N sweep; it is O(N) and sun-independent |
| Changing the time of day rebuilds everything | The horizon sweep sits below the sun parameter in the graph | Put the sun-independent sweep above the sun parameter; only the projection is downstream |
| Rivers run out of dry valleys, or half the map is a desert | An unclamped upslope field: 49.6–50.1% of cells measure negative, and clamping alone then halves the base rate | Clamp at zero, then rescale so the domain total matches the intended base rate |
| Erosion is identical on both sides of a range | Discharge taken as drainage area `A`, which assumes uniform rainfall | Accumulate `Q = Σ(P·cellArea)` with the same router and substitute `Q` for `A` [minderroe] |
| The rain shadow is sharper than any real range | A single authored wind direction; the Alps' storms arrive from many, which erases the simple shadow [minderroe] | Average the dot product over three to five weighted directions |
| The wet band sits on the windward face and looks pasted on | The upslope model has no conversion or fallout timescale, so nothing is advected downwind | Named fix is Smith and Barstad's linear theory — read it before implementing; the cheap partial fix is to advect the clamped field downwind before accumulating |
| Ridge-tops are drier than the reference imagery | The upslope model's known failure at kilometre scale — measured maxima sit on ridge-tops via seeder-feeder [minderroe] | Add a curvature-weighted term and label it a correction, not physics |
| Tiled driver-field bake seams at kilometre scale | Halo sized for a local filter, not for a kilometre horizon [dozier2022] §III-C | Widen the halo, or evaluate the far field on a coarse grid and take the minimum [stendardo2020] |
