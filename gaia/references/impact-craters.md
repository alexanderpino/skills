---
type: Technique
title: Impact craters — the depth law, the rim, and the field
description: "Stamping craters whose geometry is measured rather than invented: the two-branch depth-to-diameter law, the transition diameter that moves with gravity, the ejecta falloff, and the size-frequency distribution and draw order that make a field read as a history."
tags: [generation, craters, morphometry, ejecta, planetary, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: pike1977, tier: P, locator: "Table 1 p. 491 and eqs. (1)–(4) p. 492 — depth R_i = 0.196 D_r^1.010 (<15 km, N=171) and R_i = 1.044 D_r^0.301 (>15 km, N=33), intersecting 'at a crater diameter of about 10.6 km'; rim height R_e = 0.036 D_r^1.014 and R_e = 0.236 D_r^0.399, intersecting 'at a diameter of about 21.3 km', with the note that 'the slope of Eq. (3) is now essentially 1.0, the value expected from dimensional theory'; eqs. (8)–(9) p. 494, rim-flank width W_e = 0.257 D_r^1.011 and W_e = 0.467 D_r^0.836, whose fits intersect at about 30.4 km; Fig. 1 p. 490 for the six measured dimensions; the abstract p. 489 for the eleven shape changes spanning 10–30 km, average 17.5 km. All variables in km" }
  - { id: silber2017, tier: P, locator: "§1 Introduction p. 2 — 'the transition from simple to complex structures is a function of surface gravity (g), with a roughly 1/g dependence'; p. 3, the average lunar transition diameter 'is about 19 km'; §5 discussion, Mars and Mercury at 3.72 and 3.70 m/s² nevertheless transition at notably different diameters" }
  - { id: austin2024, tier: P, locator: "eq. (1), t = T·(r/R)^−B for ejecta thickness against range in crater radii, with a measured B_avg = 2.8 ± 0.1 against the B = 3.0 that McGetchin et al. (1973) inferred 'for ejecta blankets of all sizes'; §6.2 for the rim thickness fit, coefficient 0.14 ± 0.062 and exponent 0.77 ± 0.080; continuous ejecta to about 3–4 crater radii" }
  - { id: minton2019, tier: P, locator: "§1.1 eqs. (1)–(2) — cumulative production n_p,>r ∝ r^−η and equilibrium n_eq,>r ∝ r^−β, with β ≈ 2 for any steep-sloped (η > 2) production population; Fig. 1 and its caption for Gault's geometric saturation n_geom,>r = 0.385 r^−2 and for equilibrium sitting at ~2% of it; p. 5, the Neukum production slope η ≈ 3 for r ≲ 2 km, the multi-sloped lunar production function that is shallow (η < 2) for about 2 km < r < 30 km and steep again above it, and the remark that a slope-2 surface makes image scale hard to judge" }
  - { id: melosh1989, tier: F, locator: "ch. 2 Crater Morphology and ch. 6 Ejecta Deposits — the standard synthesis of the simple/complex distinction and of ejecta emplacement. A textbook, not a peer-reviewed paper, and no numbered equation is quoted from it here" }
---
# Impact craters — the depth law, the rim, and the field

A crater is the one landform in this skill whose geometry has been **measured to three
significant figures** and published as a regression. Almost everything else here is a process
whose output you argue about; a fresh crater's depth, rim height and rim width are each a power
law in its diameter, fitted to hundreds of craters [pike1977]. So the failure mode is not
"my crater looks wrong" — it is "my crater is not the shape a crater is", and that is checkable
against numbers rather than against taste.

The second half of the subject is that **one crater is not the interesting object.** A field is,
and a field is defined by two things a single crater cannot express: how many craters there are
at each size, and which ones cut which.

## Use this

**Stamp an authored radial profile whose depth, rim height and rim width come from the
morphometric power laws, choosing the simple or the complex branch by comparing the diameter
against a transition diameter you scaled to your world's gravity — blending the two branches
across 0.53–1.58 × `D*` if the scene shows craters near it, which the body argues is the faithful
form; then lay the field down in age order, oldest first, so later craters overwrite earlier ones.** Everything that makes a
crater field read correctly is in that sentence: the profile is measured, the branch is chosen
by a gravity-dependent threshold, and the history is carried by draw order.

Nothing here is simulated. There is **no canonical source for the procedural recipe** — no paper
tells a tool builder how to stamp a crater into a heightfield; standard practice is to author a
radial profile and fit it to the published morphometry, and the physics behind that morphometry
is a textbook subject [melosh1989]. What *is* published, and what this document is for, is every
number the profile has to hit.

**What it beats.** *A subtracted paraboloid* — the commonest crater node there is, and it has no
rim, so it reads as a dent; the raised rim is roughly 18% of the crater's depth — most of that
uplift rather than deposit — and it is the feature the eye uses to identify the landform. *Radially-warped noise* — a texture, with no
depth law, so it does not change shape as it changes size. *An impact hydrocode* (iSALE and
relatives) — the right tool for asking why the transition diameter is where it is, and orders of
magnitude too expensive to place a thousand craters; use its published outputs, which is what
the morphometry already is. *Gaea's `Crater`, `CraterField` and `Pockmarks`* — UI branding over
exactly this stamping operation; the node names are not algorithms, and the question to ask of
any of them is which of the numbers below it actually hits.

## The depth-to-diameter law, and where it breaks

`R_i` is depth below the rim crest, `D_r` the rim-crest diameter, both in km [pike1977]:

| Regime | Depth below rim crest | Rim height above the plain | Rim-flank width |
|---|---|---|---|
| **Simple**, `D` below the transition | `0.196·D^1.010` | `0.036·D^1.014` | `0.257·D^1.011` |
| **Complex**, `D` above it | `1.044·D^0.301` | `0.236·D^0.399` | `0.467·D^0.836` |
| *Fits intersect at* | *10.6 km* | *21.3 km* | *30.4 km* |

The exponents are the whole story. Every simple-crater exponent is within 1.5% of **1.0** —
1.010, 1.014, 1.011 — and [pike1977] says of the rim-height fit that its slope "is now
essentially 1.0, the value expected from dimensional theory". A simple crater is therefore
*geometrically similar* at every size: its depth-to-diameter ratio is a constant, near 1:5, and
one profile scales to any diameter. The complex exponents
are not 1, so a complex crater is a **different shape** at every size, growing shallower as it
grows: 1:8 at 20 km, 1:45 at 250 km. A crater node with one profile and a size slider is
implicitly claiming the whole world is simple craters.

Transcribing the two depth fits and solving for their intersection numerically over
`D ∈ [1, 100]` km gives **10.583 km**, against the "about 10.6 km" the paper states; the same
solve on the two rim-height fits gives **21.273 km** against its "about 21.3 km". Both were run.
That agreement is worth the two minutes because it is the cheapest possible check that you
transcribed four coefficients and four exponents correctly — get one digit wrong and the
crossing moves visibly.

Measured over `D ∈ [0.1, 15]` km, the simple-branch depth/diameter ratio runs 0.1915 to 0.2014,
a spread of 5.1%; the rim-height-to-depth ratio runs 0.1820 to 0.1857 against the ratio of the
two intercepts, 0.036/0.196 = 0.1837. **Treat both as constants and you are inside the fit's
own scatter.** So for the simple branch, the practical form is: depth `= D/5`, rim crest
`= 0.18·depth` above the pre-impact surface, rim flank out to about `0.26·D` beyond the crest.

⚠️ **There is no single diameter at which a crater becomes complex, and the paper says so three
separate times.** Pike's depth fits intersect at about 10.6 km, his rim-height fits at about
21.3 km, and his rim-flank-width fits at about 30.4 km — and of that last one he notes that
"visually the inflection seems closer to 20 km". The abstract puts all eleven shape changes
across a **10–30 km** band averaging 17.5 km [pike1977]. So a generator with one threshold has
collapsed a transitional band into a step. That is a legitimate simplification; it is not a
faithful one. Blending the two branches across the band instead costs a lerp and gives you
transitional craters — flat-floored but peakless — for free, which is what the band physically
is.

## The transition diameter is a property of the planet, not of the crater

This is the part that matters to anyone building a world that is not Earth. The simple-to-complex
transition happens when the transient cavity can no longer hold itself up, so it goes as **roughly
`1/g`** [silber2017]. The lunar value is about 19 km, so anchoring the product `D* · g` there
gives 30.8 km·m/s² and:

| Body | `g` (m/s²) | `D*` predicted from `D*·g = 30.8` |
|---|---|---|
| Moon | 1.62 | 19.0 km (the anchor) |
| Mars | 3.71 | 8.3 km |
| Earth | 9.81 | 3.1 km |
| Ceres | 0.28 | 110 km |

Those were computed, not quoted, and **only the lunar row rests on a source read here.** Treat
the rest as what the scaling law predicts, not as observations — the values in the literature for
Earth and Mars are of the same order, but this document has not verified them and does not assert
them. The direction is the usable part, and it is not in doubt: **halve your world's gravity and
every crater above about 10 km changes shape.** A low-gravity moon is a world of
deep bowls where Earth would have terraced, flat-floored, central-peaked basins, and that single
threshold does more for "this is not Earth" than any amount of palette work.

Do not oversell it. [silber2017] is explicit that gravity does not fix `D*` on its own: Mars and
Mercury have essentially the same surface gravity, 3.72 and 3.70 m/s², and transition at
noticeably different diameters, because target strength, porosity and layering all move the
threshold. `1/g` is the scaling you should expose as a knob's default, not a law you should
hard-code.

## Rim and ejecta

The rim is **not a pile of ejecta**, and modelling it as one is the second-commonest crater error
after leaving it off. Two things make a rim: target rock the impact structurally uplifted, and a
blanket of ejecta laid on top of it. Both are measured, separately.

The blanket thins with range as a steep power law [austin2024]:

```
t(r) = T * (r / R) ** -B          # ejecta thickness, r >= R, r measured from the centre
B    = 2.8                        # measured; McGetchin et al. (1973) inferred 3.0
T    = 0.14 * R ** 0.77           # EJECTA thickness at the rim; T and R in metres
```

`T` is the ejecta contribution alone. The **total** rim height above the pre-impact plain is
Pike's `0.036·D^1.014` km, and it is bigger. Evaluating both across the size range where each fit
applies:

| `D` | ejecta at the rim, `T` | total rim height | `T` / rim height |
|---|---|---|---|
| 0.5 km | 9.8 m | 17.8 m | 0.55 |
| 1 km | 16.8 m | 36.0 m | 0.47 |
| 2 km | 28.6 m | 72.7 m | 0.39 |
| 5 km | 57.9 m | 184 m | 0.31 |
| 10 km | 98.7 m | 372 m | 0.27 |

So **45% to 73% of the rim is uplift rather than deposit, rising with diameter, and the deposited
share falls as the crater grows.** That is a modelling instruction, not trivia: only the ejecta
part continues outward as the blanket, so a profile that extrudes the whole rim height outward
under the falloff law puts two to four times too much material on the surrounding ground. Build
the rim as a structural bulge with the ejecta curve laid over it. (The unit convention above is
[austin2024]'s — metres, matching the McGetchin form it is compared against — while Pike's fits
are in km. Getting those two into the same units is where this is most often silently wrong.)

`B` near 3 is a violently steep falloff, and it is what makes the blanket end on its own. At
`B = 3` the thickness is **1/8** of the rim value at two crater radii, **1/64** at four and
**1/1000** at ten; at the measured `B = 2.8` it is 1/7, 1/49 and 1/631. You do not need a separate
rule for where the blanket stops — the exponent stops it, and the continuous blanket duly ends at
about 3–4 radii, with only rays and isolated patches beyond [austin2024]. A blanket drawn with a
linear or `1/r` falloff spreads a visible pedestal across the whole domain and reads as a stain.

**Mass balance, as a sanity check on your own profile.** Integrating `2πr·t(r)` against a
paraboloidal cavity of Pike's depth, the blanket carries **26.6%** of the cavity volume out to
four radii for a 2 km crater at `B = 3.0`, and 37.1% for a 0.5 km one; even integrated to a
hundred radii it reaches only 35% and 49%. The cavity model there is this document's own
construction, not Pike's, so read it as an order check rather than a result — but the order is
right, and it tells the same story as the rim table: **most of the displaced material never
leaves as a blanket.** It goes into structural uplift, into the breccia lens on the floor, and
into distal rays. A blanket that integrates to 300% of the cavity means your `T`, your falloff or
your depth disagree with each other, and that test costs one integral.

Two implementation notes that decide whether it looks right. **Make the cavity, the rim and the
blanket one radial profile** — a crater whose rim is a separate additive ring shows a seam at the
crest wherever the two disagree. And **the ejecta is deposited on top of whatever was there,
while the cavity is a replacement**: treating the whole crater as one additive stamp buries the
floor of anything it lands in, and treating it as one replacement erases the terrain the blanket
should be draping.

## Placing a field: the size-frequency distribution

One crater is a prop. A field is a population, and the population has a published shape: the
cumulative number of craters larger than radius `r` per unit area goes as `r^-η`, with a
production slope `η ≈ 3` for the small end of the lunar record [minton2019].

A cumulative power law has the same exponent in radius and in diameter, so `η` transfers
between the two unchanged and only the coefficient moves — which is worth saying because the
literature works in radius and every tool works in diameter.

⚠️ **`η ≈ 3` is the small end only.** [minton2019] is explicit that the lunar production
population is *multi-sloped*: steep for `r ≲ 2 km`, then **shallow, `η < 2`,** between roughly 2
and 30 km radius, and steep again for basins. A single exponent across four decades of diameter
is therefore wrong at both ends, and wrong in the direction that matters — it produces far too
few large craters. If your field spans more than about two decades, break it into segments and
give each its own slope.

Sample it by inverse transform from a truncated power law between an explicit `D_min` and
`D_max`. **`D_min` is not a performance setting — it decides what the field looks like.** With
`η = 3`, half of all cratered *area* lies in craters below 0.020 km when the range runs
0.01–10 km, and below 0.198 km when it runs 0.1–10 km: in both cases the smallest ~10–15% of the
log-diameter range owns half the ground. Measured, over the same integral, at `η = 2` the area is
spread **exactly evenly per decade** — half the area below the geometric mean of the range, at
every range tested. So:

- **`η ≈ 3`** is a young surface: a few big craters on a ground that is mostly fine pitting. The
  look is controlled by `D_min`, and lowering it does not add background texture, it *replaces*
  the field's character. Set it from your cell size and say so.
- **`η ≈ 2`** is a saturated one. [minton2019] gives the reason it looks the way it does: a slope
  of 2 makes the cumulative coefficient dimensionless, the surface is scale-free, and the paper
  notes it is then hard to judge the scale of an image of it at all. That is precisely the
  "airless, ancient, no sense of size" look, and it is one number.

The empirical ceiling is worth carrying: an equilibrium surface sits at roughly **2%** of
geometric saturation, `n_geom,>r = 0.385 r^-2` [minton2019] — cumulative count per unit area, so `n` is `1/L²` and `r^-2` is `1/L²` and **0.385 is dimensionless**: it ports to any unit unchanged. (An earlier revision of this line said the opposite, that the coefficient carries units — contradicting the bullet five lines above, which gives being dimensionless at slope 2 as the whole reason the surface is scale-free.) Past that you are not making an
older surface, you are making mush — which is what a naive "just add more craters" loop produces.

## Superposition is the history

Craters do not blend. A later crater **destroys** the part of an earlier one it lands on, and
that single asymmetry is what separates a field that reads as a chronology from a field that
reads as scattered dents.

The implementation is almost free: **assign each crater an age, sort oldest-first, and stamp in
that order.** Every crater then cuts the accumulated surface, its rim truncates the rims it
crosses, and its ejecta buries what it lands on. Three consequences to keep:

- **Do not blend or average overlapping craters.** A max/min or a soft-union of two rims gives a
  smooth figure-of-eight that exists nowhere in nature; the correct result is one rim cutting
  through the other's, with a hard edge.
- **Degrade with age.** The oldest craters should be softened before the younger ones land on
  them. A cheap and defensible model is one diffusion pass per age band — [minton2019] finds
  steady diffusive degradation, driven mostly by distal ejecta impacts, to be the mechanism that
  actually sets the equilibrium distribution, so diffusion is not a stand-in here, it is the
  process.
- **Size and age are independent.** Correlating them ("big ones are old") produces a legible,
  wrong pattern. Draw diameter from the SFD and age uniformly.

## Where this sits in the pipeline

Craters are **authoring-time, and they go into height**, which is the opposite of this skill's
usual instruction. `tectonic-uplift.md` insists that a range be authored into `U` and cut by
erosion, because a range *is* an erosion product. A crater is not: it is excavated in seconds
and the landform is the excavation. Stamp it.

But stamp it **before** the erosion and flow-routing passes, not after. A crater rim is a closed
ring, so it is a drainage divide and its floor is a depression; run it through `flow-routing.md`
and the depression handling and you get an interior lake or an outlet breach at the low point of
the rim, which is exactly what a real crater lake is. Stamp craters after erosion and they sit on
the terrain as decals, with no drainage consequence at all. The ejecta blanket has the same
argument: it is material added to slopes, so it should be there before the material is moved.

## The crossover that changes the answer

| Situation | Do | Because |
|---|---|---|
| One hero crater, art-directed | Author the profile directly; ignore the SFD | The population statistics say nothing about a single object |
| A field on a planet, any airless body | SFD sampling + age-ordered stamping | Both the count and the cut-order are what make it read as history |
| Diameters straddling the transition | Blend the two branches across **0.53–1.58 × `D*`** | The transition is a band, not a threshold [pike1977]. ⚠️ Pike's 10–30 km is the **lunar** band; expressed against the lunar `D*` of 19 km it is 0.53–1.58 × `D*`, and in that form it scales with gravity like `D*` does. On Earth's predicted `D* = 3.1 km` that is **1.7–5.0 km** — blending across 10–30 km there would blend entirely inside the complex regime, at 3× to 10× `D*` |
| A world that is not Earth or Moon | Scale `D*` by `1/g` first, then everything else | The branch choice moves before any coefficient does [silber2017] |
| An old, saturated surface | Drive `η` toward 2 and cap at ~2% of geometric saturation | Past the cap, more craters make mush, not more age [minton2019] |
| Craters on a world with water and weather | Stamp, then erode — never the reverse | The rim is a divide and the floor is a lake; `flow-routing.md` owns the rest |

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Craters read as dents, not craters | No raised rim — a subtracted paraboloid | Rim crest at ~0.18 of the depth above the pre-impact surface [pike1977] |
| Big craters look like scaled-up small ones | One profile for every diameter; the complex branch never used | Switch to `1.044·D^0.301` above the transition; the exponent is 0.301, not 1 |
| Large craters are implausibly deep | Simple-branch depth extrapolated past the transition | At 250 km the simple law gives ~52 km of depth against the complex law's ~5.5 km |
| Every crater on an alien world is the same shape as the Moon's | `D*` hard-coded at a lunar value | Scale by `1/g`; then expose it, because target strength moves it too [silber2017] |
| Ejecta reads as a wide stain or a pedestal | Falloff exponent far below 3 | `t ∝ (r/R)^−2.8`; thickness is 1/7 at 2R and 1/49 at 4R [austin2024] |
| Far too much material heaped around the crater | The whole rim height extruded outward as ejecta | Only the ejecta share travels: `T = 0.14·R^0.77` m, 0.55 of the rim height at D = 0.5 km falling to 0.27 at 10 km [austin2024] |
| A visible seam or ring at the rim crest | Cavity and rim authored as two stamps that disagree there | One radial profile covering cavity, crest and blanket |
| Craters landing in a basin float above its floor | The whole stamp added to existing height | Cavity replaces, ejecta adds |
| The field is all tiny pits and one big hole | `D_min` set from performance, with `η ≈ 3` | Half the cratered area lives in the smallest tenth of the log range; choose `D_min` deliberately |
| No sense of scale in the render, and that was not wanted | `η` near 2 — a scale-free, saturated surface | A slope-2 population is dimensionless by construction [minton2019] |
| Adding craters stops making the surface look older | Past equilibrium, each new crater destroys one old one | Cap the density near ~2% of geometric saturation [minton2019] |
| Overlaps look like smooth figure-of-eights | Craters blended, max'd or soft-unioned | Stamp in age order; later cuts earlier, with a hard edge |
| Every crater equally crisp, so the field has no history | No age-dependent degradation | Diffuse by age band before the younger craters land [minton2019] |
| Crater floors are dry and the drainage ignores them | Craters stamped after erosion and routing | Stamp first; the rim is a divide and the floor is a depression |
