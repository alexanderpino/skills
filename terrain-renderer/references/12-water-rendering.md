# Water Rendering

Water on terrain — oceans, rivers, lakes — arrives from the generation side as *still data*: flat
surface datums, a depth field, a flow field. Everything that moves is made here. This chapter owns
the engine side of that handoff: water surface geometry and its LOD (meshed or the meshless
screen-space pass), ambient wave synthesis
(Gerstner and FFT), shoal- and shore-aware shallow-water waves (shoaling, refraction, breakers,
run-up), flow-driven river surfaces, local interactive simulation, man-made bodies (pools, tanks,
canals), water shading composition, caustics, shoreline integration, and the
transparency/pass-ordering discipline water forces on the frame. Deep BRDF/scattering math routes to the physically-based-rendering skill; generation of
water bodies, routing, and flow fields routes to terrain-architect (its `03`/`04` hydrology and the
`08`/`27` output contract).

Contents: [Where the rest of this chapter lives](#where-the-rest-of-this-chapter-lives) ·
[Diagnostic index](#diagnostic-index-symptom-to-mechanism) ·
[The handoff, seen from the render side](#the-handoff-seen-from-the-render-side) ·
[Sea states: the energy ladder](#sea-states-the-energy-ladder) ·
[Surface geometry & LOD](#surface-geometry--lod) ·
[Screen-space water: the fullscreen-triangle pass](#screen-space-water-the-fullscreen-triangle-pass) ·
[Ambient waves: Gerstner and FFT](#ambient-waves-gerstner-and-fft) ·
[Calm water: the low-energy regime](#calm-water-the-low-energy-regime) ·
[Shallow water: shoaling, refraction, and breakers](#shallow-water-shoaling-refraction-and-breakers) ·
[Aerated water: foam, spray and whitewater](#aerated-water-foam-spray-and-whitewater) ·
[Rivers: flow-driven surfaces](#rivers-flow-driven-surfaces) ·
[Interactive simulation patches](#interactive-simulation-patches) ·
[Man-made water: pools, tanks and channels](#man-made-water-pools-tanks-and-channels) ·
[Shading and optics](#shading-and-optics) ·
[Caustics: the other half of the light path](#caustics-the-other-half-of-the-light-path) ·
[Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic) ·
[Shoreline integration](#shoreline-integration) ·
[Transparency & pass ordering](#transparency--pass-ordering) ·
[What to pre-cook](#what-to-pre-cook-and-what-to-recompute) ·
[Engine-native water](#engine-native-water-the-ue-water-plugin-read-as-architecture) ·
[Stylized water](#stylized-water-same-contracts-different-bands) · [Pitfalls](#pitfalls) ·
[Sources & provenance → `12b`](12b-water-provenance.md)

## Where the rest of this chapter lives

This file is the doctrine and the mechanisms. Three other places carry the rest of it, and a
question this chapter answers in a sentence is usually answered in full by one of them:

| Where | What is there | Go there when |
|---|---|---|
| [`12a-water-derivations.md`](12a-water-derivations.md) | The **mathematics and the pseudocode** — the derivations behind results this chapter quotes as one line, worked rather than asserted | A number here has to be re-derived, re-checked, or carried to different constants |
| [`12b-water-provenance.md`](12b-water-provenance.md) | **Sources & provenance** for all of `12`: every tier, every citation, every `?`, and the `P/T/D/F/N/?` convention itself | Anything here is about to be cited, or a figure is about to be quoted outside this skill |
| `reference-impl/` | The **executable form**: `field.py` (the surface), `wake.py` (the jet's eikonal wake), `render.py` (the light), and `validate.py` as the arbiter | A claim here is disputed, or a new one needs somewhere to be falsified |
| [`figures/`](figures/) | The **pictures**, and [`figures/make_figures.py`](figures/make_figures.py), the one script that draws every one of them | A claim here is about a *shape* and the words are not carrying it |

The provenance appendix moved out of this file rather than shrinking: nothing was removed, and the
tier markers scattered through the prose (`P`, `D`, `?` …) all resolve against `12b`.

**The figures are generated, never pasted.** Every image in `12` and `12a` — and every image in the
rest of `references/`, which the same script now draws — comes from `figures/make_figures.py`, which
imports the reference implementation **read-only** and writes no physics of its own, so a figure
cannot drift from the code that ships. Each carries its provenance mark and the function that drew it
in the caption *beside* the image — never inside the pixels, where it cannot be diffed and cannot be
corrected. `00`'s figure table lists the whole set, and the chapters that deliberately have none.
Regenerate with:

```
python3 terrain-renderer/references/figures/make_figures.py             # redraw all thirteen
python3 terrain-renderer/references/figures/make_figures.py --selftest  # prove the guard can fail
```

It re-derives every headline number by a second, non-shared route before drawing a pixel and exits
non-zero if any of them has moved: Walsh's relation on independently quadratured index pairs, the
`μ_c`-split integral against `optics.py`'s own midpoint-plus-Walsh route, `K_d(0)`, the Cornu
limits, Hunt's reading of `R`, and Cox & Munk's two components against the separately fitted total.
And because **a guard that has never been seen to fail is not known to be a guard** —
[`11`'s fourteenth way](11-verification-failures.md#the-fourteenth-way-two-instruments-agree-and-could-not-have-disagreed),
with the sign flipped — `--selftest` fires it at **fifteen** deliberately broken inputs, six of them
this chapter's (including the softened total-internal-reflection branch and the run-up misreading
waves 4–11 actually shipped) and nine belonging to the figures the same script draws for `09`, `10`
and `19`. All fifteen are caught; a figure whose guard goes blind is caught by the run that says so.
This chapter's six figures, and the claim each one exists to make:

| Figure | Where | The claim it carries, which is a shape |
|---|---|---|
| `fresnel-two-sides` | [12·1](#surface-reflection-names-two-opposite-things-a-loss-and-a-trap) | one interface has two reflectances; the internal one is pinned to 1 past `θ_c`, and 92% of it is geometry |
| `lut-factorisation` | [12·2](#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them) | the two factors of the exit transport rise together, so their product is not their joint |
| `trapped-series` | [12·3](#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point) | truncation and the wrong constant are additive; and `1/(1 − ρR_int)` is a **bound**, not a gain |
| `sommerfeld-half-plane` | [12·4](#diffraction-is-not-refraction-and-nothing-above-contains-any-of-it) | `K_d = ½` on the boundary exactly, the lit side rings, and the Cornu chord is why |
| `glitter-path-narrowing` | [12·5](#sun-glitter-the-sparkle-path) | the path's width is a *function* of view elevation, so no spread parameter can be it |
| `runup-distribution-vs-realisation` | [`12a` 12a·1](12a-water-derivations.md#where-the-band-ends--a-distribution-is-not-a-surface-and-it-is-two-masks-not-one) | a distribution has no edge and a realisation does; the same defect as glitter drawn as its pdf |

`validate.py` is what makes the reference implementation evidence rather than an illustration — it
checks the renderer against things it did not write (closed forms, published measurements,
independent methods). It **exited non-zero on eight rows** for several rounds — three absorption,
two Fresnel, one missing total-internal-reflection branch, two on the vertical-face internal-return
ratio — and those eight are now closed with no tolerance widened; four were *tightened*, because the
quantity they cover became an identity rather than an approximation. They were recorded findings
while they stood, not neglect. Every row prints expected, measured and tolerance, and every tolerance is
justified from the *estimator's* own error or a published uncertainty, never from the disagreement
it is being asked to excuse — so a FAIL means the number is outside what the measurement itself can
explain, and the next question is which of the two sides is wrong, never whether the tolerance can
move. A suite that passes because its tolerances were widened proves nothing — and one that passes
because its rows were transcribed from the sentence beside the constant proves less than nothing,
which is what happened to two of those eight (see `11`, *[Seven ways a measurement lies while looking
like one](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one)*). **A test and the code it checks must not share a premise** — and its converse, learned in the same file
one round later: **a test that shares almost nothing with the code tests almost nothing**, which is
[`11`'s eighth way](11-verification-failures.md#the-eighth-way-is-about-the-test-not-the-measurement)
and cost this suite a row called *closed energy audit of the whole pool* that was neither. The file
also ends with a
list of what is not tested *at all*, which is as much the deliverable as the tests are.

## Diagnostic index: symptom to mechanism

A reader arrives at water rendering with a picture, not with a section name. This table runs the
opposite way from the rest of the chapter — from what is on the screen to the mechanism that put it
there — and every row names the section that explains it. What earns a row is that the symptom does
*not* contain its own cause: "the surf is diagonal" nowhere says *refraction*, and anyone who knew
it did would not need the table. [Pitfalls](#pitfalls) is the exhaustive list of ways water goes
wrong; this is the routing layer over it, and each row below was earned by something measured on
the reference implementation or read off a photograph, not supposed.

| Symptom on screen | Mechanism | Where |
|---|---|---|
| Glitter is a broad pale road instead of isolated blinding points | The environment's sun is a **fitted lobe, not a disc**: peak, width and flux were never made to land on the sun together, and the sky lobes carry the direct beam short by a factor of tens. Presents as a tuning problem; is not one | [Sun glitter](#sun-glitter-the-sparkle-path) |
| One blown-out highlight instead of a glitter path | The opposite error, in the *lobe* rather than the source: a sharp specular NDF where the slope distribution is tens of degrees wide | [Sun glitter](#sun-glitter-the-sparkle-path) |
| Saturated coloured speckle along a refracted silhouette — a step nosing, a ladder rail | Three IORs are **three delta wavelengths**, and a step edge at the dispersion scale resolves as a three-tooth comb. It is aliasing *of* dispersion, not dispersion | [A channel is a band](#a-channel-is-a-band-not-a-wavelength) |
| Far water reads flat and plastic *after* filtering was added | The slope variance was correctly removed from the field and **never given a receiver** — or handed over as a scalar, when what was removed is a tensor | [Pick the kernel](#pick-the-kernel-on-purpose-and-give-the-variance-a-receiver) |
| The far surface breaks into a coarse moiré | The other end of the same trade: **no distance-dependent narrowing of the slope distribution**, so a band is still sampled at a footprint wider than itself. The fix narrows the distribution per component; it cannot be applied to the shaded result afterwards, because shading is nonlinear in slope | [Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic) |
| A moiré that *beats* slowly with distance — a band fades, returns, fades again | The footprint filter is a **box**: its sinc has negative lobes to −0.217, so the band comes back phase-inverted as the footprint grows. Gaussian at `σ = 0.3748·fp`, which is the only kernel positive and monotone | [Pick the kernel](#pick-the-kernel-on-purpose-and-give-the-variance-a-receiver) |
| Caustic cell interiors too dark **and** an occluder's shadow too bright, in one frame | One flat ambient standing in for a **directional inter-reflection**: it under-fills where a lit surface should be bouncing and over-fills where nothing should. Errors of opposite sign in one frame are a missing transport path, never a constant that needs raising | [The masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| The seen bottom reads bright against the sky reflected in the same pixel, and no exposure fixes both at once | **Radiance is not conserved across a refracting interface** — `L/n²` is. The reflected column is air-side and right; the transmitted one is an in-water radiance shipped without its `1/n²`, so it is 1.78× hot. A *relative* error inside one pixel, which is why a grade cannot absorb it | [Radiance is not conserved](#radiance-is-not-conserved-across-the-interface) |
| A submerged wall is too dark, and adding more bounce does not help | The refracted sun does not reach it. A surface lit only by a neighbouring diffuse one is capped at **half its own albedo** times that neighbour's radiance — the form factor to an adjoining infinite plane is exactly ½ — so a floor-lit wall is *necessarily* darker than the floor and no gather can be tuned past it | [The masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| A submerged step's riser, or a shaded wall face, renders flat and near-neutral grey | The third symptom of that same missing leg: the receiver gets **no direct sun and one flat ambient**, so a grazing sky reflection wins by default and the bounce that should carry both colour and the caustic net is absent | [The masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| A shadowed region on the bed is a dark hole | Two mechanisms, and the second is the bigger one. The sun-visibility gate treated as **binary** when the occluder is fabric or foliage (shade cloth transmits ~15–30% *diffusely*) — and, for **any** occluder including a fully opaque one, the refracted beam's own wander under the slope field, worth 87 mm against a 221 mm shadow at a 21° sun | [The masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| An **opaque** object's shadow on the bed reads as a reduction rather than a hole, and translucency is reached for to explain it | The **surface**, not the occluder. A facet tilted by `ε` swings the transmitted ray by `\|1 − cos θ_i/(n cos θ_t)\|·ε` — 0.6241 at a 21° sun against 0.2508 at noon — so the field that writes the caustic net smears the shadow's edges into its own interior. The umbra's core really is zero; the fill is transport | [The masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| The caustic pattern plays across a shadow on the bed | The same gate missing altogether, or sampled at the **receiver** instead of at the surface entry point — metres apart at low sun. Nothing else announces "this is a scrolling texture" so loudly | [The masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| Caustics keep moving after the water has gone calm | An authored or cell-noise caustic, **uncorrelated with the surface above it**. A flat surface has a constant Jacobian and produces no caustic structure at all | [The tier ladder](#the-tier-ladder) |
| The caustic net fades while the water still looks perfectly clear | Rising `b`, and this is scattering's **first** symptom: contrast along the sun path halves at `b ≈ 0.35 m⁻¹`, where Secchi depth is still ~3 m. A body colour is the *fourth* symptom, not the first | [Water-body optical identity](#water-body-optical-identity-where-the-iops-come-from) |
| A caustic net still pin-sharp at 20 m, or blurred away in a 1.5 m pool | A penumbra kernel **computed at one depth and reused**. The sun's disc sets ~0.7 cm of blur per metre; every depth-derived quantity is a *function* the moment the body has a slope, a step or a bench | [Caustics](#caustics-the-other-half-of-the-light-path) |
| The submerged bed reads far murkier than the water column above it, or the column far clearer than the bed | **One extinction coefficient driving both paths.** The sightline through the bed is beam attenuation `c`; the depth-tinted column is diffuse attenuation `K_d`; they differ by 5–20×, so a single constant has one of the two wrong by that factor and no value of it is right | [Shading and optics](#shading-and-optics) |
| Water uniformly coloured whatever the depth | The depth field ignored — absorption run off a **constant instead of the bathymetry**, so the shallow→deep ramp, the strongest realism cue water has, never happens | [Shading and optics](#shading-and-optics) |
| Deep clear water rendered bright cyan | Reflectance goes as `b_b/a`, and in clear water `b_b` is molecular and tiny: deep clear water is **near-black**. Bright cyan is *shallow* water over a bright bottom | [Water-body optical identity](#water-body-optical-identity-where-the-iops-come-from) |
| A pool that looks the same over every liner, and at every depth | Its colour was art-directed into the **scatter term**. Treated water has `b_b ≈ 0` and no body colour of its own; what is seen is bottom albedo attenuated over the down-and-back path | [Pool optics](#pool-optics-the-colour-is-the-bottom-not-the-water) |
| A pool reads brand-new — one flat liner colour from the coping to the floor — and no amount of caustic or ripple detail rescues it | The liner authored as a **single `base_color`** where a body in service is an albedo **field**, organised around the waterline. The uniformity is the tell, and it is always in the same place | [A liner in service is an albedo field](#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate) |
| Weathering visible everywhere else, but the waterline itself is a clean geometric edge with no tide line | The mask is **multiplicative only**. Scale is a *deposit*: it covers the liner and brings its own albedo, so it composes as a coverage lerp — and no multiple of a dark liner is white. The highest-contrast feature on an aged pool is the one a multiply-only pipeline is structurally unable to draw | [A liner in service is an albedo field](#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate) |
| A weathering or dirt mask lands at the wrong strength — and by a different amount over a pale bottom than a dark one | The trapped series. Apparent bed brightness is `ρ/(1 − ρ·G_rt)`, whose **elasticity in `ρ` is the gain itself**, so a mask authored in albedo space arrives amplified by a factor that depends on the albedo it acts on, per channel. Contrast up, level down, and a neutral change does not stay neutral. Tuning it against the picture is inverting that by eye | [Where a weathering profile is allowed to come from](#where-a-weathering-profile-is-allowed-to-come-from-and-what-the-water-does-to-it) |
| A beach whose wet band fades smoothly into the dry sand, with no boundary anywhere — while the wet/dry albedos check out | The run-up **distribution** painted where its **realisation** belongs. `exp(−(z/σ)²)` is the share of swash cycles reaching a level, so blending by it draws the beach's *time-average*, and an average has no edge: measured, 4/255 across 48 px of face where the realisation gives 36/255 in one row. Same defect class as glitter drawn as its slope pdf and foam drawn as its own mean | [`12a` §10, where the band ends](12a-water-derivations.md#where-the-band-ends--a-distribution-is-not-a-surface-and-it-is-two-masks-not-one) |
| Wet sand reads **brighter** than dry, and moving the albedos does not fix it | One wetness field driving **both** the diffuse darkening and the specular lobe, which puts a mirror on merely *damp* sand. Pore water darkens for minutes; free water reflects and leaves with the swash sheet. Measured, the misplaced lobe was 1.28 against a 1.39 diffuse term over 3.19% of a whole frame — enough to invert the pair on its own | [`12a` §10, where the band ends](12a-water-derivations.md#where-the-band-ends--a-distribution-is-not-a-surface-and-it-is-two-masks-not-one) |
| No bright line where the water meets a wall, a jetty or a stone | The meniscus modelled as an **ambient or roughness lift** rather than a specular strip. A few millimetres of fillet holds every facet orientation, which is why that line survives sun-and-camera geometry nothing else in the frame can reach | [The meniscus line](#the-meniscus-line-where-reachability-cannot-fail) |
| Objects above the water smear into it — a dock post, a torso, the coping | The refracted sample was **not depth-rejected**, so it landed on geometry nearer than the water surface | [Shading and optics](#shading-and-optics) |
| Fine ripples and long waves drift in lockstep | One scrolled texture advects every scale at **one velocity** by construction. Real water is dispersive — across a pool-sized band the long components outrun the short by roughly 4:1 | [Sun glitter](#sun-glitter-the-sparkle-path) |
| Sparkle convincing in a screenshot, obviously wrong on a pan | Noise-perturbed specular is **not a function of the slope field**, so its glints ride nothing; real ones ride crests and stay trackable for a second of footage. The test for glitter is temporal | [Sun glitter](#sun-glitter-the-sparkle-path) |
| A wake or a jet train reads as a **seam** up the frame rather than as water | Its axis in *plan* sits within a few degrees of the camera azimuth, so a long ordered train projects as a near-vertical stripe. Obliquity in plan is the control; amplitude is not | [The wave field is a driven basin](#the-wave-field-is-a-driven-basin-not-a-spectrum) |
| Swell crossing shallow water at the wind angle, hitting the beach diagonally | Wave phase taken from the **wind** rather than from a depth-driven travel-time field, so nothing refracts. Crests parallel to every shore is the cue the eye checks first | [Shallow water](#shallow-water-shoaling-refraction-and-breakers) |
| My water is the wrong colour against a reference photograph, and no constant fixes it without breaking something else | The **photograph's sun was never computed**, so the illuminant is an unpinned free variable soaking up the residual. From a place, a date and a time it is fully determined — and its elevation alone moves the transmitted share (87.8→97.8%) and the slant path to the bed (1.96→1.53 m) between two ordinary afternoon suns | [The illuminant is part of the comparison](#the-illuminant-is-part-of-the-comparison-what-cancels-and-what-does-not) |
| Shadows in the render point plausibly but disagree with the reference by tens of degrees, while the sun's *height* is clearly right | The azimuth's `acos` branch, taken from the wrong one of two conventions. Elevation comes from `cos ζ`, which has no branch, so it stays correct and every other check still passes — a 72° error that reads as a shading problem | [`10`, the quadrant trap](10-lighting-shadows.md#the-quadrant-trap-and-why-the-elevation-stays-right) |
| A water-to-deck ratio disagrees with the reference, and the low sun is offered as the explanation | Both are **horizontal receivers**, so `sin h` and the air-mass attenuation are identical on them and cancel exactly in the ratio. What does *not* cancel is only the Fresnel entry share and the slant path — 1.25× between a 21° and a 57° sun, and nothing beyond that is available | [The illuminant is part of the comparison](#the-illuminant-is-part-of-the-comparison-what-cancels-and-what-does-not) |
| Absolute sRGB triples read off a reference photograph will not reconcile with the render, and the disagreement changes between frames of the same pool | The camera, not the renderer: automatic white balance rescales chromaticity toward neutral hardest where the subject is most saturated, a display tone curve rescales level non-uniformly, and a Display P3 file read as sRGB shifts a water pixel's R/B by 28–52% while leaving the stone beside it near-untouched | [`11`, seven ways](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one) |
| Every vertical surface under the water is streaked with fine vertical bars that do not change up the face — walls, risers, pilings, a hull | The caustic map sampled at the receiver's own world `(x, y)`, with **no height term**. A bed pattern with structure at its texel scale and none in `z` is a comb. Not a resolution problem: quadrupling the map and the gather moved it by 0.7% | [A caustic on a vertical face](#a-caustic-on-a-vertical-face-is-not-the-beds-pattern-at-that-faces-own-position) |
| A pool interior is too dark by a factor of two to seven, or washed out, and every constant that fixes it breaks the surface | **"Surface reflection" taken in the wrong sense.** One interface carries two diffuse constants: `R_ext = 6.669%`, a loss on the way in, and `R_int = 47.617%`, a trap on the way out. They differ by **7.14×**; swapping both is **2.37×** of darkness, and swapping only the internal one desaturates while passing every luminance check | [Surface reflection names two opposite things](#surface-reflection-names-two-opposite-things-a-loss-and-a-trap) |
| Everything near the rim of Snell's window is mush in an underwater shot while the zenith is fine — the shoreline, a jetty, a person standing at the edge | The environment indexed from **below**. Snell's Jacobian `cos θ_a/(n² cos θ_w)` vanishes at grazing, so the entire air world under 10° of elevation lands inside **3.75%** of the window's solid angle. A `θ_w`-uniform lookup starves that annulus 8.5× and over-serves the zenith 7.6×. Index by the air-side cosine instead | [What the window actually contains](#what-the-window-actually-contains-and-why-the-rim-is-where-the-world-is) |
| An overhead occluder — a shade sail, a canopy, a hull — expected to fill Snell's window and barely appearing in it | The same Jacobian, run forwards. A panel 8–12 m away and 2.4 m up sits at **72–77° from the vertical**, which Snell compresses into **1.44°** of polar angle. What dominates a window instead is whatever stands at the observer's own edge, seen at grazing all the way round | [What the window actually contains](#what-the-window-actually-contains-and-why-the-rim-is-where-the-world-is) |
| A floating body shows no refracted split at its waterline, and the refraction is checked and correct | Its own **meniscus** hides it. The split needs `R(1 − sin(β + θ_w)) > z_w·sin θ_w`; on a 221 mm ball a 2.31 mm climb beats the left-hand side by 22.6×. "No split" is a prediction with a threshold — and with `z_w = 0` the threshold is still a draught over **12.55%** of the diameter, which no inflatable reaches | [`12a` §3](12a-water-derivations.md#a-floating-body-and-the-split-its-own-meniscus-hides) |
| One surface in the frame is off by a factor near 3.14 and everything around it is right | An **irradiance used as a radiance**. `E` and `L` differ by π and a shading term, and nothing in a shader's types says which a triple holds. A bare constant near 3.14 or 0.318 in a shading term with no derivation beside it is this bug | [`11`, an irradiance used as a radiance](11-verification-failures.md#an-irradiance-used-as-a-radiance) |
| A submerged wall reads sky-coloured and structureless while its level looks about right | The upper half of a vertical face's hemisphere filled with sky. It is **22% Snell window and 78% mirror**; a flat `0.5` over-gives the sky by ×1.96 and under-gives the pool's own upwelling field by the same partition, so level survives while hue and caustic structure do not | [What a submerged vertical face sees of the sky](#what-a-submerged-vertical-face-sees-of-the-sky) |
| Water is subtly dark after a lookup table replaced a computed transport, and no index or format bug explains it | An integral **split into two tables and multiplied**. Attenuation and escape share the water-side cosine and are correlated `+0.76`, so the product of the means understates by 19.4% in red; the trapped leg is correlated the other way, so the composed result moves only 2.8% and hides it | [Attenuation and escape do not factorise](#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them) |
| The suite is green, has been green for months, and the picture is visibly wrong in the quantity the suite is named after | A test that **borrows one name and writes the rest itself**: its own inputs, its own transport, a physics identity for a right-hand side. It exercises one function and certifies a law that would hold for almost any implementation | [`11`, the eighth way](11-verification-failures.md#the-eighth-way-is-about-the-test-not-the-measurement) |
| Every wall at a waterline is lit identically from the sky, on the sunny side and the shaded side alike | One "sky ambient" handed to receivers of different orientation. A horizontal face weights the sky by `cos θ sin θ`, a vertical one by `sin² θ`; they agree at exactly ½ for a uniform sky and nowhere else, and the aureole gives the vertical case an **azimuth** a constant cannot carry — 1.23× between a sun-facing and a sun-averted band of one pool | [An illuminant per receiver](#an-illuminant-per-receiver-and-what-that-costs-at-a-waterline) |
| A dry band above the water reads flat and slightly cold, and no ambient value fixes both it and the deck | Its **lower half** was given the pool's upwelling and not the *sky reflected in the water*. The `sin²θ` weight peaks at the horizon, where a water surface reflects **0.2112** rather than the 0.0206 of normal incidence — a factor of 10.3, and 23% of what that half receives in green | [An illuminant per receiver](#an-illuminant-per-receiver-and-what-that-costs-at-a-waterline) |
| The pool reads *desaturated* rather than dark — the liner's colour is weak but the level is plausible | The interreflection series **truncated at one bounce**. The error is chromatic because bed albedo is: 7.8% in green and 10.5% in blue against 1.1% in red on this liner, so it washes the colour out while surviving every luminance check. The second bounce buys back three quarters of it | [The upgoing half, traced](#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point) |
| A submerged wall's level looks right, and correcting a term you know is wrong barely moves it | The **sky and the mirror are two halves of one hemisphere**, so over-giving one under-gives the other and any measurement of the total is blind by construction. Zero the sky: the face must fall to **77.7%**, not to zero and not to half | [The upgoing half, traced](#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point) |
| An aged pool's dirt is all in the shade | A grime mask driven by **ambient occlusion**. Biofilm needs stagnation; photosynthetic algae need stagnation *and light*, so the worst place is the **sunlit stagnant** corner. One accessibility mask is right for one mechanism and exactly backwards for the other | [Fouling in the corners](#fouling-in-the-corners-from-an-algorithm-rather-than-from-a-texture) |
| Weathering present but perfectly even — an aged surface that is uniformly grey rather than blotchy | Patchiness is **feedback, not noise**: deposit roughens, roughness holds more deposit, and above a threshold coupling the uniform state is linearly unstable. A few iterations give it; a noise octave fakes it and has to be re-authored per basin | [Fouling in the corners](#fouling-in-the-corners-from-an-algorithm-rather-than-from-a-texture) |
| An outdoor pool with a geometrically clean waterline and no band at all | The `neglect` control shipped at a **zero default**. Most pools in service carry a band, so a pristine liner is the special case; a renderer defaulting to zero age reads as CG by default, and the same holds for every persistent liquid line — tanks, locks, harbour walls, hulls | [Fouling in the corners](#fouling-in-the-corners-from-an-algorithm-rather-than-from-a-texture) |
| The sea is green everywhere, or blue everywhere, whatever the wave is doing | A tint on the water **body**. One backlit breaking wave refutes it in a single exposure: the face reads saturated green while the same water two metres away reads grey-blue, so the colour is the **path** and must vanish when the path does | [The surf zone](#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot) |
| The saturated green backlit face never appears in the surf, however tall or steep the wave field is made | **Not a tuning shortfall — a bar on the representation.** A sightline through a wave crosses the surface twice, so the entry and exit inclinations must sum to `2(90° − θ_c)` = **82.96°**; Stokes' 120° corner caps a wave of permanent form at 30° a face, so its best sum is 60°. No single-valued height field of a steady wave reaches it, at any height, order or grid | [The 30° ceiling](#the-30-ceiling-a-single-valued-crest-cannot-be-read-lengthwise) |
| Surf built as one particle system, and it reads as confetti over glass | **Three whites, three materials**: the blanket behind a break is a *coverage mask*, the opacity inside the wave mouth is a *participating medium*, the spray is *particles* — and the particles are the **smallest** share. All three are built on the same `1 − 1/n²` wall reflectance and share nothing else — and none of them whitens *because* of it: a bubble backscatters `b_b/b = 0.023`, so the white is multiple scattering | [Aerated water](#aerated-water-foam-spray-and-whitewater) |
| Water is right in the near field and goes black — or absurdly saturated — toward the horizon, and no fog or exposure setting fixes both halves | **The straight ray used as the traversal distance.** `d/cos θ_a` diverges at grazing; the transmitted ray refracts and `d/μ_w` is bounded by `1.33 d`. Median 12.1%, p95 46.5% on a measured frame, fixed by one `sqrt` | [Screen-space water, step 4](#screen-space-water-the-fullscreen-triangle-pass) |
| Volumetric foam or a bubble plume that goes bright white but you can still see the bed through it | `1 − 1/n²` spent as a **backscatter fraction** instead of a wall reflectance — 19× too much return, and the transmittance that should have fallen with it never does. A conservative slab has `R = τ'/(1 + τ')` and `T = 1 − R`; whitening without hiding means the model has `R` and not `T` | [Aerated water](#aerated-water-foam-spray-and-whitewater) |
| A white plume after a wave hits rock that either vanishes leaving nothing or lingers white far too long | **Two clouds with one decay curve.** Entrained air rises and bursts in seconds; suspended sediment settles over minutes and advects. They overlap in space and are separated by *lifetime*, not appearance | [The surf zone](#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot) |
| The bed disappears convincingly inside the break but stays visible everywhere else in the surf zone, and turning the foam up does not fix it | **The entrained air credited for the suspension's work.** Both hide a bed and they are four orders of magnitude apart — a measured `2.76×10⁻⁵` for the suspension against `0.152` for the plume, with the plume simply *absent* below its own depth. Model both, and check each absolutely rather than as a ratio | [The surf zone](#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot) |
| Water in the surf zone that is exactly as clear on every frame while the waves break through it | `b` treated as a **material constant** where it is a state variable produced by the dynamics: the waves suspend the bed, the backwash erodes, turbidity pulses at the wave period. The one optical property a still frame cannot verify | [Water-body optical identity](#water-body-optical-identity-where-the-iops-come-from) |
| A real-time approximation passes every image comparison and is 5–25% off on the quantities it approximates | The bar is still a **photograph** when the target is an approximation. 5% scene-linear is ~2.7 encoded levels of 255 at mid grey; the errors that matter are selected for invisibility. The bar has to become the reference plus a per-channel metric on named quantities | [`11`, the bar changes kind](11-verification-failures.md#when-the-target-is-an-approximation-the-bar-changes-kind) |

Two habits make the table worth more than the sum of its rows. **Read pairs, not symptoms** — the
dark-interiors/bright-shadows row is diagnostic only as a pair, because either half alone reads as
a constant that needs nudging. And **read the order symptoms arrive in**: rising turbidity, a
sinking sun, a growing pixel footprint each produce a *sequence*, and the position in that sequence
identifies the mechanism more sharply than any single frame does.

## The handoff, seen from the render side

Terrain-architect's hydrology handoff (its `08`, "caused, not carved") gives this chapter four
inputs, and the doctrine is that they are *sufficient*:

| Input | Form | What the renderer does with it |
|---|---|---|
| `waterSurface` | Flat elevation per body (sea level for oceans, spill level per lake, a downstream-monotone profile per river) | The datum every wave displaces from; the gameplay swim/buoyancy surface |
| Water depth | Scalar field: `waterSurface - solidTop`, 0 on dry land | Absorption ramp, shoaling, shoreline fade, sim boundary |
| Flow / velocity | 2D vector field (m/s), from routing + discharge, plus the nearshore surface circulation — longshore current, rip jets, inlet/river-mouth jets (terrain-architect `12`) | Flow-map advection, foam alignment, particle steering, sim boundary inflow, wave–current interaction |
| Shore distance | Signed/unsigned distance to the waterline | Shoreline foam bands, wet-sand band (`13`/`14`), LOD bias near the line |
| `liquidBody[i]` | Per-body record (terrain-architect `28`, registered in its `08`/`27`): `bodyType` (sea / lake / pond / river / stream / estuary / wetland), `ior`, derived optics (`a_RGB`, `b_b_RGB`, `c_RGB`, `K_d_RGB`, scatter colour), the fetch/exposure field for enclosed water, causal state, QA fields (Secchi, Jerlov/Forel-Ule class) | **`bodyType` selects the surface model**: sea gets swell + tide + nearshore circulation; a lake gets **fetch-limited wind waves only** — no swell, no current (suppress the residual-swell component of [Calm water](#calm-water-the-low-energy-regime) on lakes, and scale the wave spectrum by the fetch field); rivers get flow. Also **the source of the medium's IOPs and of the surface's `specular_ior`** — see [Water-body optical identity](#water-body-optical-identity-where-the-iops-come-from), and [the vocabulary rule](#the-vocabulary-and-which-half-of-it-you-can-look-up) for why the record's own field names are kept while what they feed is named in OpenPBR and IOP terms. `ior` populates `specular_ior`, which drives surface Fresnel and refraction bending (never hardcode 1.33); beam attenuation `c` drives sharp sightlines; `K_d` drives the diffuse depth column |

The solid terrain below the water is real terrain — bathymetry generated to dry-land standards —
and it is the collision floor, the refraction target, and the depth source. Two hard rules fall
out of the contract, and both are load-bearing:

- **Never displace the terrain heightfield to fake water.** Water carved into `solidTop` is the
  "solid ocean" defect from the generation side, reproduced renderer-side: no swim volume, no
  tide, no transparency, and the material system now has to pretend rock is liquid. Water is a
  *separate surface* drawn over real bathymetry, always.
- **Never bake waves into any input.** If waves, ripples, or foam appear pre-painted in the
  height, normal, or color data, the pipeline is broken upstream — a baked wave cannot respond to
  wind, time, interaction, or camera, and it aliases under every condition the real synthesis
  handles. If an input arrives with waves in it, the fix is upstream (terrain-architect `08`),
  not a renderer workaround.

When the renderer needs something the contract lacks (per-body bounding volumes, max wave
amplitude for conservative culling bounds, river width fields), extend the contract; do not
derive hydrology renderer-side.

## Sea states: the energy ladder

Water is not one rendering problem. A mirror-calm lake and a storm sea share a surface model and
almost nothing else: which techniques matter, which dominate the frame, and which can be switched
off entirely all change with energy. The Beaufort scale — long since given standard wind-speed and
sea-state equivalents by the meteorological bodies — is the right spine, because its descriptors
are *visual observations* and therefore map directly onto rendering features.

| Bft | Wind (kt) | Observed sea (NOAA/WMO wording) | What the renderer must switch on |
|---|---|---|---|
| 0 | <1 | "Sea surface smooth and mirror-like" | Reflection fidelity is everything; **minimum slope-variance clamp** or the sun becomes a Dirac |
| 1 | 1–3 | "Scaly ripples, no foam crests" | Capillary detail only — normal-map band, no displacement |
| 2 | 4–6 | "Small wavelets, crests glassy, no breaking" | Displacement begins; still no foam anywhere |
| **3** | **7–10** | "Large wavelets, crests begin to break, **scattered whitecaps**" | **Foam turns on here** — the Jacobian/coverage path starts contributing |
| 4 | 11–16 | "Small waves, numerous whitecaps" | Whitecap coverage climbs steeply; glitter path widens |
| **5** | **17–21** | "Moderate waves, many whitecaps, **some spray**" | **Spray particles turn on**; foam becomes a major albedo term |
| 6 | 22–27 | "Larger waves, whitecaps common, more spray" | Aerated water is now a first-class material, not a decal |
| **7** | **28–33** | "Waves 13–19 ft, **white foam streaks off breakers**" | **Streaked, advected foam** — orientation along wind matters |
| 8 | 34–40 | "Edges of crests begin to break into **spindrift**, foam blown in streaks" | Wind-torn spray leaving the crest; strong aerial perspective |
| 9–11 | 41–63 | "Dense streaks of foam, spray may reduce visibility" → "foam patches cover sea" | Spray becomes atmospheric — a participating medium, not sprites |
| 12 | 64+ | "Sea completely white with driving spray" | Foam coverage saturates; the surface is barely water any more |

Three transitions are worth hard-coding as feature gates, because they are observational facts
rather than art direction: **whitecaps begin at Force 3**, **spray begins at Force 5**, and **foam
streaks begin at Force 7**. They also cross-validate the coverage model in
[Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic): Monahan's
`W = 3.84e-6·U^3.41` puts whitecap coverage at essentially zero around 5 m/s (~0.1%) and
conspicuous by 15 m/s (~4% of the surface), and Force 3 is 7–10 kt ≈ 3.6–5.1 m/s. An empirical formula and a 19th-century observational scale
agreeing on where foam starts is a good sign both are right — and a strong argument for driving
foam from wind rather than from a hand-tuned constant.

The **WMO sea state code** (built on the Douglas scale) is the parallel system, and
it classifies the *sea* rather than the *wind* — useful when swell arrives from a distant storm and
local wind does not explain the surface. Significant wave height `H_s` (the mean of the highest
third, and `≈ 4·sqrt(m₀)` from the spectrum's zeroth moment) is its currency and the natural
parameter to expose in a wave-spectrum UI.

**One wind, every consumer.** The same wind speed must drive the wave spectrum, the whitecap
coverage, the glitter slope variance, the spray rate and the foam streak direction. Wiring them
separately is how you get a mirror-calm sea covered in foam, or a gale with a needle-sharp sun
highlight — both instantly wrong, and both common.

## Surface geometry & LOD

The water surface is a displaced plane (per body), and the geometry question is the same question
as `01`: how to spend vertices where projected error is visible. Two families:

| Scheme | Mechanism | Wins | Loses |
|---|---|---|---|
| Projected grid (Johanson) | Screen-space regular grid projected onto the water plane; vertex density automatically ∝ screen area | Near-perfect vertex distribution; one mesh for an infinite ocean; no LOD machinery | Vertices swim/flicker at the horizon edge as the camera turns; detail density is view-coupled and hard to art-direct; degenerate at near-vertical look-down; per-body clipping is awkward |
| World-space grid (clipmap / quadtree rings on the plane) | Reuse `01`'s LOD machinery flattened onto the water datum; concentric rings or SSE-refined quads | Stable world-anchored vertices (no reprojection swim); same crack/morph contracts as terrain; trivially clips to body extents; plays with `06` streaming | Needs the full LOD controller; wasted vertices at grazing angles that a projected grid gets free |

Production default in 2026 is the **world-space grid**: the reprojection instability of projected
grids under TAA and their poor authorability outweigh their elegance, and the LOD machinery is
already paid for by the terrain. Projected grids remain defensible for a single infinite ocean
with no other water bodies and a camera that never looks straight down. Whichever is chosen:

- **Near field**: tessellate or pre-subdivide to carry actual wave *displacement* (not just
  normals) out to the distance where displacement drops below ~1 px of parallax; beyond that,
  waves live in the normal/material band only (the three-bands doctrine, applied to water).
- **Far field**: an infinite-ocean skirt ring — a coarse annulus extended to the horizon at the
  sea datum, normal-mapped only. It must share the datum and the far fog/aerial-perspective path
  with terrain (`10`) or the sea/sky junction band mismatches the land horizon. "Share" means
  one atmosphere LUT/state and the same view-depth coordinate; a private water fog color creates
  a blue/orange seam at sunset precisely where water, land, and sky should agree.
- **Lakes and rivers** are finite meshes streamed with their tiles under the same residency
  contract as `06` — a lake tile's water mesh loads/evicts with the terrain tile, carries `e(tile)`
  and SSE-refines in the same currency, and matches terrain tile LOD at the shoreline (see
  [Shoreline integration](#shoreline-integration)).
- **Planet-scale oceans** live on the cube-sphere as sphere-datum patches (`09`): patch-local
  frames, camera-relative wave displacement, and the wave textures sampled in a local tangent
  frame — world-space UV math at planetary coordinates shreds into precision noise long before
  the terrain does, because wave frequencies are centimetre-scale.

Culling note: wave displacement moves geometry outside its static bounds. Bounds submitted to
`08`'s culling must be inflated by max amplitude + max horizontal chop, per cascade settings —
un-inflated bounds cause tiles that pop at screen edges exactly when the sea is roughest.

## Screen-space water: the fullscreen-triangle pass

There is a third geometry answer for flat-datum water: draw no water geometry at all. A single
fullscreen triangle covers the screen; the pixel shader builds a per-pixel view ray, intersects
it analytically with the water plane, and shades water wherever the hit survives the depth
buffer. The entire surface-geometry problem — LOD, cracks, morphing, culling, horizon skirts —
evaporates because there is nothing to tessellate, and the horizon is pixel-exact by construction.

One *triangle*, not a quad — community canon with a real reason: a quad is two triangles whose
shared diagonal cuts 2×2 pixel quads in half, so the rasterizer runs partially-covered quads and
redundant helper lanes twice along the seam, and sets up interpolants for two primitives instead
of one. The triangle needs no vertex or index buffer; the vertex shader emits three oversized
verts straight from `SV_VertexID`:

```hlsl
// Draw(3), nothing bound; the oversized tri clips to exactly the screen
float4 FullscreenVS(uint id : SV_VertexID, out float2 uv : TEXCOORD0) : SV_Position {
    uv = float2((id << 1) & 2, id & 2);               // (0,0) (2,0) (0,2)
    return float4(uv.x * 2 - 1, 1 - uv.y * 2, 0, 1);  // spans NDC (-1,1)..(3,-3)
}
```

The pixel shader is the whole system:

1. **Ray**: unproject the pixel through the inverse view-projection (near/far points), or build
   `rayDir` from the camera basis and pixel NDC. Origin is the camera; keep everything
   camera-relative (`09`).
2. **Analytic hit**: for a horizontal datum at `h_water`,
   `t = (h_water - camPos.y) / rayDir.y`. Guard the degenerate cases explicitly: `|rayDir.y| < ε`
   (ray parallel to the plane — no hit), `t < 0` (plane behind the camera), and the sign flip
   when the camera is below the datum (underwater, below).
3. **Depth reject**: reconstruct the opaque scene's world position from the depth buffer along
   the same ray; if the scene hit is nearer than `t`, terrain or props occlude the water — output
   nothing. The reconstruction must use the frame's actual depth convention (reversed-Z, jitter).
4. **Shade**: everything in [Shading and optics](#shading-and-optics) applies unchanged at the
   hit point — traversal distance **`d/μ_w`, with `μ_w` the *Snell* cosine of the view angle and
   `d` the vertical water column**, shore fade from the depth field, normal detail from
   scrolling/FFT normal cascades sampled at the hit's world XZ, SSR/cubemap reflection, refraction
   from the scene-color copy.

   ⚠️ **This step used to read "traversal distance from scene depth vs `t`", and that is the
   straight ray.** The transmitted ray *refracts* — the same clause that says "refraction from the
   scene-color copy" a line later. The two lengths are `d/cos θ_a` and `d/μ_w`, and

   ```
   mu_w = sqrt(1 - (sin theta_a / n)^2) >= 1/n = 0.749   for EVERY air-side angle, however grazing
   cos theta_a -> 0                                      at the horizon
   ```

   so the straight length **diverges** exactly where the true one is bounded by `1.33 d`. Measured
   against a per-pixel offline reference over 157 641 water pixels, the literal reading costs a
   **median of 12.1% and 46.5% at p95** in scene-linear radiance, against `4.1×10⁻⁵` median for
   `d/μ_w` — **it is fixed by one `sqrt`** (`D`, `raster-impl/`, reproduced here). This is not a
   subtlety about a hard case: it is the whole far half of any water frame with a horizon in it,
   and it is the sentence a shader author implements.

   `d/μ_w` is a *flat-datum* rule and it still assumes the refracted ray lands on the bed patch the
   straight ray found. Re-projecting along the refracted ray and re-tapping the depth buffer buys
   the p95 back — 33.1% → 1.6% on the same frame with six taps — and cannot go further, because a
   depth buffer cannot answer for a bed patch the straight ray never looked at. At the *median* the
   two rules are indistinguishable and both sit on the physics floor: **the screen-space depth error
   is a tail, not a level.**

The geometry of the pass, in section view:

```
 C  camera — one fullscreen triangle, one view ray per pixel
  \\
   \ \_____ ray B                             ____
    \      \_____                           _/    \_
     \ ray A     \_____                   _/        \_    terrain surface
      \                \_____           _/            \   from the depth
       \                     \_____   _/               \  buffer
        \                          \_X                  \
 ~~~~~~~~*~~~~~~~~~~~~~~~~~~~~~~~~~~/~~~~~~~~~~~~~~~~~~~~\~~~ water datum y = h_water
   ______________                  /
  /   sea floor  \_________________/
  * = ray A's plane hit, t = (h_water - camPos.y)/rayDir.y; the scene hit (sea
      floor) lies beyond t -> ACCEPT: shade water there, absorb over sceneHit - t
  X = ray B's scene hit is nearer than its t -> REJECT: terrain occludes the water
```

**Waves on the analytic plane: layered normal cascades.** The flat datum reads as glass until it
carries wave detail, and on this pass the cheap tier is entirely in shading: perturb the plane
normal at the hit's world XZ with **two to four scrolling layers** at decade-spaced scales. Two
layers is the floor (swell + chop); three reads as open water; the fourth (fine ripple) exists
mainly near the camera and must fade with distance or it aliases into shimmer:

```hlsl
// world-XZ uv at the ray hit; layers decorrelated by scale, direction, AND speed
float3 n = float3(0, 1, 0);                                       // start at the datum normal
n = blend(n, sampleNormal(uv * 0.045 + dir0 * t * 0.35));         // swell   ~20 m
n = blend(n, sampleNormal(uv * 0.21  - dir1 * t * 0.60));         // chop    ~4 m
n = blend(n, sampleNormal(uv * 1.15  + dir2 * t * 0.95) * fade);  // ripple  ~1 m, distance-faded
```

`blend` is a real normal combine — RNM or whiteout from `07`, never a lerp. The layers can be
tiling noise-derived normal maps (indie tier), or the FFT cascades' normal outputs
([Ambient waves](#ambient-waves-gerstner-and-fft)) sampled as textures — the fullscreen pass
consumes either identically. Decorrelation rules: non-parallel directions, scale ratios off
integer multiples, speed ratios irrational-ish — any two layers that line up periodically
produce a visible beat pattern marching across the sea. An analytic Gerstner normal sum
(evaluate ∂h/∂x, ∂h/∂z of 3-6 Gerstner terms at the hit) substitutes for the texture layers
when fetch-bound; derive the foam/whitecap mask from the combined slope either way. None of
this moves the silhouette — crests do not rise, the horizon stays a line — which is exactly the
boundary where the next paragraph takes over.

**Displaced surfaces: per-pixel raymarching.** The analytic plane carries waves in normals only —
flat silhouette, no parallax between crests. To show real displacement, march the ray against the
displaced height: start at the analytic hit of a crest-inflated plane, take fixed steps sampling
the summed cascades until the ray crosses the surface, then binary-refine 4–6 iterations. Cost
doctrine: that is N cascade fetch+sums per water pixel, and N grows brutally at grazing angles
where the ray travels far between height crossings — cap the step count and fall back to the
analytic plane beyond a distance. Raymarching is worth it for hero close-ups with no mesh budget;
the moment displacement must read everywhere on screen, a mesh is cheaper.

**Underwater is the same triangle.** `camPos.y < h_water` flips the intersection's sign logic and
the pass becomes a fullscreen underwater volume: every pixel starts in water, extinction fog runs
over the distance to the scene hit or the surface exit point, the datum seen from below gets
total internal reflection outside Snell's window, and the bright overhead circle comes from the
same ray-plane math. Same triangle, different branch — the underwater state machine in
[Shading and optics](#shading-and-optics) still owns the crossing frame.

Honest trade-off against meshed water:

| | Fullscreen-triangle pass | Mesh / projected grid |
|---|---|---|
| Horizon & LOD | pixel-exact plane; zero LOD/crack/skirt machinery | vertex-quantized; full crack/morph discipline |
| Displacement | raymarch-only; silhouettes cost per-pixel marching | free in the vertex shader; cheap silhouettes |
| Motion vectors | none rasterized — derive analytic velocity or TAA ghosts | rasterized like any other geometry |
| Multiple bodies | per-body planes + screen bounds; cost per body drawn | meshes clip to body extents naturally |
| Transparency | composites at one depth per pixel; other transparents need explicit ordering | sorts as ordinary transparent geometry |

Where it wins: indie flat oceans, single-datum seas, and tool viewports (`16`) that need "sea
level" visualized without buying the LOD apparatus. Where it strains: lakes and rivers at many
elevations (each body needs its own plane and screen-space bounds, and the depth-reject must pick
the nearest surface per pixel — the per-body sorting rule of
[Transparency & pass ordering](#transparency--pass-ordering) applies unchanged), and any frame
where wave silhouettes matter more than the saved machinery. The pass raises three traps of its
own — grazing-angle ray-plane precision, reversed-Z reconstruction mismatch, and the missing
motion vectors — catalogued in [Pitfalls](#pitfalls).

## Ambient waves: Gerstner and FFT

Ambient (wind-driven) waves are pure synthesis on top of the flat datum. Two families, honestly
compared:

| | Gerstner / trochoidal sum | Spectral FFT (Tessendorf) |
|---|---|---|
| Mechanism | Sum of 4–16 analytic trochoids; horizontal + vertical displacement per wave | Sample an oceanographic spectrum (Phillips, JONSWAP) into a frequency grid; inverse FFT per frame → displacement map |
| Look | Sharp, tunable crests; readable at low counts; visibly periodic and "gel-like" as counts drop | Full spectrum, statistically ocean-like; the AAA standard for open sea |
| Cost | Vertex-shader ALU, scales with wave count | 2–4 compute FFTs (e.g. 256²–512²) per frame; amortizable, cacheable |
| Authoring | Direct per-wave control — good for stylized/hero waves | Spectrum parameters (wind speed/direction, fetch); less direct |
| Outputs | Displacement + analytic normal | Displacement, normal, **and Jacobian** maps |

**Gerstner** is the right tool for stylized seas, small budgets, and gameplay-authored swells; its
loop artifact (the whole surface visibly repeating its motion) is inherent — mitigate with
irrational frequency ratios and per-wave phase, never expect it to vanish. **FFT** is the open-sea
default. Run **2–4 cascades** at different world-space patch sizes (e.g. ~400 m, ~60 m, ~10 m) and
sum them: a single tile visibly repeats from any altitude; overlapping cascades at co-prime-ish
sizes push the repeat beyond notice — but verify from max gameplay altitude (`11`), because
cascade tiling *returns* at height as the small cascades mip away and the large one dominates.

**The Jacobian is a free product; use it.** The horizontal displacement field's Jacobian
determinant measures local surface compression: `J = (1+∂Dx/∂x)(1+∂Dy/∂y) − (∂Dx/∂y)(∂Dy/∂x)`.
`J ≤ 0` means the surface self-intersects — a folding crest. Threshold slightly above zero
(practice: 0.5–0.9, tuned) → whitecap/foam mask, accumulated with decay so foam persists briefly
behind the crest. This is *the* whitecap signal; painting whitecaps any other way fights the
displacement. **Choppiness** (the horizontal displacement scale) sharpens crests toward trochoids
— and past ~1.0 it drives `J` negative over large areas, which reads as geometry
self-intersection shimmer. Clamp choppiness so folding stays rare-and-foamed, not constant.

Ambient synthesis as described above is a *deep-water* model: it assumes the bottom is
infinitely far away. The moment the exported depth field says otherwise,
[Shallow water](#shallow-water-shoaling-refraction-and-breakers) owns the waves — and at the
opposite end of the energy ladder, the low-wind case has its own failure modes.

## Calm water: the low-energy regime

Beaufort 0–2 is not "the easy case with the waves turned down". It is a distinct regime that
breaks several assumptions the rest of this chapter relies on, and it is where a water renderer
most often looks *obviously* synthetic — because there is nothing left to hide behind. The
classic failure on a millpond is one of two: the sea goes to patent leather, or to a black void
with one searing highlight.

**There is a smallest possible wave, and it is not zero.** Including surface tension, the
dispersion relation is

```
omega^2 = ( g*k + (sigma/rho)*k^3 ) * tanh(k*h)      # sigma = surface tension, rho = density
```

The `k³` term means phase speed *rises* again for very short waves, so it has a **minimum**, and
both halves of that minimum come from **one** surface tension:

```
sigma = 0.0728 N/m, rho = 1000 kg/m^3, g = 9.81 m/s^2      # reference-impl/wake.py: SIG, RHO, G
c_min    = (4 g sigma / rho)^(1/4)  = 0.23119 m/s = 23.12 cm/s
k_min    = sqrt(rho g / sigma)                              # the same k minimises c and c_g
lam_min  = 2 pi sqrt(sigma / (rho g)) = 0.017116 m = 1.712 cm
```

⚠️ **Quote the pair from one `σ` or do not quote it as a pair.** This chapter carried
**23.1 cm/s at 1.73 cm** for its whole run and
[`00`'s ledger](00-index.md#least-confident-claims-ledger) recorded the
two as *verified together*. They are not consistent: 23.1 cm/s inverts to `σ = 0.07256 N/m` and
1.73 cm to `σ = 0.07437 N/m` — **2.5% apart in `σ`**, 1.1% in `λ`. Both are inside the ordinary
spread of published clean-water values, which is exactly why the mismatch survived being checked:
each number is defensible alone and the *pair* is not. Nothing downstream moves at this precision,
so it is a **provenance defect rather than a numerical one** — and this project treats that as the
worse kind, because a pair marked verified that cannot both be right is a claim whose check has
been spent without being made. The rule that prevents the recurrence is the one used for `c` versus
`K_d` and for per-axis versus total slope: **declare the constant once, upstream, and derive every
consequence from it at the point of use.** `σ` is the declaration above; `c_min` and `λ_min` are
two lines of it. (`D` for both closed forms from `σ`; `P/?` for `σ` itself, whose published
clean-water values at 20 °C span roughly 0.0724–0.0729 N/m and which
[the meniscus](#the-meniscus-line-where-reachability-cannot-fail) reads at `ρ = 998`.)

Below that wavelength you are in the capillary
regime (surface tension restoring), above it the gravity regime. Two consequences: a spectrum has
a natural high-frequency cutoff around a couple of centimetres — ripples finer than the minimum
are *damped out rather than supported*, so a renderer that keeps adding finer normal-map octaves
to "sharpen" calm water is fabricating detail the physics forbids, and will alias for its
trouble — and wind cannot raise waves at all until it can push past that minimum
speed, which is why a breeze produces *patches* of ripple ("cat's paws") separated by glassy
water rather than uniform texture.

**One slope convention, fixed for the whole chapter.** `s` is the **total** rms slope,
`s = √⟨|∇h|²⟩ = √(σ_x² + σ_y²)`; *slope variance* and *mean-square slope* mean `s²`. The per-axis
`σ = s/√2` is equally standard and is what Gaussian and Rayleigh tail arithmetic takes, so where a
formula needs it the relation is written at the point of use and the unit never switches silently.
The mix is cheap to make and expensive to find: `/2` is the `⟨cos²⟩ = ½` of a plane-wave sum in one
place and a per-axis split in another, so every band stays individually defensible while the budget
summing them is wrong by `√2` on whichever band was restated. Quote the convention with every slope
figure, and read `σ` from its label — it also carries surface tension, frequency and extinction.

**Dead calm is genuinely hard, for a specific reason.** As slope variance → 0, a microfacet
specular lobe collapses toward a Dirac, and energy conservation makes what survives brighter as it
narrows. The result is a single blown-out pixel-ish highlight instead of a sun reflection with
finite extent. The fix is the same one that saves distant water: **clamp the slope variance to a
minimum corresponding to the solar disc** (0.53°), so even a perfectly still surface produces a
sun image of the right angular size — Bruneton et al. state the clamp explicitly. This is the
low-energy end of the same machinery described in
[Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic), and the symmetry
is exact: the far sea is calm *in the pixel footprint*. Variance is the common currency at both
extremes.

**What actually sells calm water is reflection fidelity, not the surface.** With slope variance
near zero the water is a mirror, so every reflection error is presented at full strength and
undamped: SSR dropout at screen edges, missing off-screen geometry, a low-resolution cubemap
fallback, a reflection that disagrees with the real scene. Rough water hides all of these; calm
water audits them. Budget accordingly — for a still lake, planar reflection is often the honest
choice precisely because it is the case where SSR's failure modes are most visible.

**Slicks and wind shadows are variance features.** Surface films damp capillary and short gravity
waves — Cox & Munk measured slicked water at **2–3× lower** total mean-square slope than clean sea
(per [Sun glitter](#sun-glitter-the-sparkle-path)) — so an oil slick, a wind shadow behind an
island or a current convergence line renders as a
**smooth mirror patch against rougher water**, not as a dark decal. Modulate the local
slope-variance field; the albedo barely changes. This is also why calm water is rarely uniformly
calm: real still water is a patchwork of glassy and faintly-textured regions — much of what makes
a real calm sea look alive rather than like a plane — and a perfectly
uniform mirror reads as fake almost as strongly as a uniformly rough one.

**Residual swell survives dead calm — on the sea.** Long-period swell is generated by distant
weather and propagates for thousands of kilometres, so a glassy ocean still rises and falls on a
long, very low-amplitude undulation. Killing all displacement at low wind gives a rigid sheet;
keep a long-wavelength, low-amplitude component alive and **decouple it from local wind**, or
moored boats and shorelines stop breathing. (This is also the case the WMO sea-state code exists
for — sea classified by the *sea*, not the wind — see
[Sea states](#sea-states-the-energy-ladder).) **This is gated by `bodyType`**: a lake has no
distant storm feeding it, so it gets *no* residual swell — dead calm on a lake really is a mirror,
and its only waves are local, fetch-limited wind waves. Swell on a mountain tarn is a classic
misclassification tell (the handoff table above; terrain-architect `03`).

**Bands that vanish, and one that does not.** In this regime foam is *absent* (below Force 3),
spray is absent (below Force 5), whitecap machinery contributes nothing, and displacement is
negligible — so the geometry and foam budgets collapse and can be spent on reflection quality
instead. What does *not* vanish is the water-body optics of
[Water-body optical identity](#water-body-optical-identity-where-the-iops-come-from):
with no surface agitation to scatter light, depth-dependent absorption and the bottom return are
the entire look of a calm shallow lake.

## Shallow water: shoaling, refraction, and breakers

Deep-water synthesis is wrong wherever the bottom matters, and the surf zone is exactly where
players judge water hardest — everyone has stood on a beach; almost no one has floated
mid-ocean. Real waves entering shallow water shorten, slow, steepen, bend until their crests
parallel the depth contours, grow just before they break, break where height outruns depth, and
run up the beach as foam. Every one of those cues is drivable from the exported depth field, and
a sea that ignores them — wind-aligned swell marching diagonally through knee-deep water onto
the sand — is the single most common realism failure in shipped water. Doctrine unchanged from
the ambient section: everything here is a *plausibility approximation driven by data*, not a
fluid simulation, and reviews should name the tier honestly so bug reports route correctly.

### The physics worth stealing

Linear (Airy) wave theory is coastal-engineering canon, cheap enough to evaluate per vertex,
and supplies the entire cue list:

- **Dispersion**: `ω² = g·k·tanh(k·h)` relates frequency ω, wavenumber `k = 2π/L`, and local
  depth `h`. Deep limit (`h > L/2`): `c ≈ sqrt(g/k)` — long waves travel faster. Shallow limit
  (`h < L/20`): `c ≈ sqrt(g·h)` — celerity depends on depth alone.
- **Period is conserved; wavelength is not.** A wave train keeps its ω as it crosses depth
  changes, so as `h` drops, `k` must rise: wavelengths compress and crests bunch toward shore.
  Solve `k(ω, h)` (a few Newton iterations) offline into a small 2D LUT — never per frame.
- **Shoaling**: energy-flux conservation through the slowdown pumps amplitude up; the shallow
  asymptote is Green's law, `a ∝ h^(-1/4)`. The visual: waves visibly *grow* just before
  breaking, then die. Amplitude ramps monotonically *up* then cuts — never a plain fade.
- **Refraction**: the end of a crest sitting in deeper water outruns the end in shallower
  water, so crests rotate toward alignment with depth contours — surf arrives near
  shore-parallel regardless of wind direction, wraps around headlands, and focuses on points.
  This is the strongest single cue in the list. It is *not* what bends a crest round an **isolated**
  rock — that is diffraction, it is a different equation, and no model in this section has any of it
  ([below](#diffraction-is-not-refraction-and-nothing-above-contains-any-of-it)).
- **Breaking**: a wave breaks when its height reaches roughly the local depth —
  `H ≈ 0.78·h` (the McCowan-type criterion). *How* it breaks is classified by the
  surf-similarity (Iribarren) number `ξ = tanβ / sqrt(H/L₀)` (β = beach slope, L₀ = deep-water
  wavelength): low ξ → **spilling** (foam crumbling down the face — flat sandy beaches), mid ξ
  → **plunging** (the curling tube — steeper beaches, reef edges), high ξ → **surging /
  collapsing** (no real break, water sloshing up rock). Slope and depth are both in the
  handoff, so *breaker character per shore is data-driven authoring*, not a global setting.

| Visible cue | Physics | Real-time treatment | Driving data |
|---|---|---|---|
| Crests bunch and slow near shore | Dispersion, ω conserved | Wavelength/phase-speed from a `k(ω,h)` LUT | Filtered depth |
| Waves grow just before the break | Green's-law shoaling | `h^(-1/4)`-style amplitude gain, clamped, then cut at break | Filtered depth |
| Surf parallel to every shoreline | Refraction | Travel-time (eikonal) phase field; or blend wave direction toward −∇(shore distance) by shallowness | Depth + shore distance/normal |
| A line of breakers, type varies by coast | `H ≈ 0.78·h`; Iribarren ξ | Break mask where amplitude/depth crosses threshold; breaker profile (spill/plunge/surge) chosen by slope mask | Depth + beach-slope mask |
| Foam born at the break, dying up the beach | Turbulent bore, swash | Foam lifecycle keyed to break mask + phase; decays into run-up streaks | Break mask, shore distance |
| Wet dark sand band that follows the surf | Run-up / swash envelope | Max-recent-run-up envelope feeds the wetness overlay (`13`/`14`) — **an envelope, i.e. a realisation of the run-up maximum, and not its distribution**; see below | Run-up height, shore distance |
| Steep breaking chop at river mouths; rips cut smooth lanes through the surf | Wave–current interaction (Doppler-shifted dispersion) | Modulate amplitude, steepness, and break threshold by opposition `dot(waveDir, −flow)`; force chop where opposing flow approaches group speed | Flow field + depth |

### Diffraction is not refraction, and nothing above contains any of it

The refraction bullet says crests "wrap around headlands". That is true of a **headland**, which is
a depth gradient, and it is what every tier below computes. It is *not* what happens behind an
isolated rock, a stack, a jetty head or a breakwater, and the difference is not a matter of degree:

- **Refraction** is eikonal turning of a ray where the wave speed varies. It is in every model in
  this section — the `k(ω,h)` LUT, the travel-time phase field, the per-wave depth response — and
  it is verifiable. On the reference implementation, a marching transform given a plane bed whose
  contours run at 10 / 20 / 30° to its own grid, and never told the rotation, reproduces Snell about
  the rotated normal to **0.186 / 0.310 / 0.277°** (`D`, recomputed here). The mechanism works.
- **Diffraction** is energy spreading *into a geometric shadow*. **It is not in the ray description
  at all** — not approximated badly, not present at low accuracy: a ray carries energy along a path
  and there is no path into the shadow. Adding depth resolution, ray count or LUT precision does not
  produce a single quantum of it.

**What it costs, in one exact number.** For a plane wave past a straight edge the field on the
geometric shadow boundary is the Sommerfeld half-plane result, and it is exactly **half the incident
amplitude** — a quarter of the energy — falling to `K_d` = 0.31, 0.20, 0.11 at Fresnel parameters
`v` = 0.5, 1, 2 into the shadow (`D`, Fresnel integrals evaluated here; `K_d(0) = 0.5000`). A ray
model says **zero** at all four. That is the size of the term, and it is the term that makes a real
lee look like water rather than like a hole.

**The controlling parameter is the obstacle's width over the wavelength, and it decides how far the
shadow reaches before it closes.** Behind an obstacle of width `W`, the lee fills in over a distance
of order `W²/λ` — the distance at which the Fresnel zone grows wider than the obstacle. Computed on
the lee centre line (Fresnel–Kirchhoff, incident amplitude 1, `D`):

| distance behind, in `W²/λ` | 0.1 | 0.25 | 0.5 | 1 | 2 | 4 | 10 |
|---|---|---|---|---|---|---|---|
| amplitude on the centre line | 0.20 | 0.31 | 0.41 | **0.51** | 0.62 | 0.71 | 0.80 |

So `W/λ` is the whole story, because `W²/λ = λ·(W/λ)²`:

- **`W/λ ≫ 1`** — a long island, a full breakwater. The shadow is real and persists for
  `(W/λ)²` wavelengths. Ray optics is a good approximation and diffraction is a soft edge on it.
- **`W/λ ≪ 1`** — a pier piling. The lee closes within a fraction of a wavelength; there is no
  shadow, but there is also almost no feature, so nobody notices the model's.
- **`W/λ ≈ 1`** — an isolated rock in ordinary swell, which is the common case on a rocky coast.
  ⚠️ **This is where ignoring diffraction is worst**: the obstacle is large enough to be a visible
  feature in frame, and the shadow it "should" cast closes within about one wavelength, so a model
  that carves one is wrong across the whole of it. Photographs of surf past an isolated rock show
  the crests bending round and **closing again in the lee within a wave or two**; a ray model does
  not.

**And the failure is not always a shadow — which is the part worth checking before assuming.** A
ray/eikonal transform has no boundary condition for an emergent obstacle at all, so what it does
with one depends on how the depth field is floored. Put a 40 m rock standing 1 m out of the water
into the reference implementation's plan-view march on a flat 8 m shelf (`λ = 74 m`, so
`W/λ = 0.54`) and the rock becomes a `D_MIN` **shoal**, not a boundary: the march refracts rays into
it, focuses them, and delivers a lee centre-line wave height of **3.66 m against a 1.48 m ambient —
2.5× too high, where the truth is a filled-in shadow at roughly ambient** (`D`, measured here). A
different implementation that masks the rock as land and stops propagation gives the opposite
error, a hard-edged hole. **Neither is diffraction, and the two look nothing alike**, so "does the
model have diffraction" cannot be answered by looking at the lee and deciding whether it seems dark
enough.

**The test is one object and it is cheap.** Put an isolated obstacle a wavelength or so across into
the scene and look at what is behind it. For any ray, eikonal or travel-time model the answer is
*no diffraction*, by construction — the value of the test is that it converts a structural fact into
something a reviewer can see in one frame, and it forces the question of whether this scene has any
isolated obstacles in it. If it does not — an open beach, a smooth bay — the term is genuinely
absent from the shot and nothing is owed. If it does, say which of the two errors above the
implementation makes, because they need different fixes: the shoal-focus artefact is fixed by
handling emergent cells as boundaries, and the hard shadow needs an actual diffraction term
(a Sommerfeld/Penney–Price edge solution stamped per obstacle, or a spectral model that carries
directional spreading) rather than a wider filter on the depth field. **Blurring the shadow is not
modelling the diffraction**; it happens to look better and it gets `W/λ` wrong in both directions.

#### K_d is half the solution. The other half is a DIRECTION, and it is what a bay is held by

Everything above prices diffraction as an **amplitude** — `K_d`, a number between 0 and 1 that says
how much wave is in the lee. That is the half a coastal-engineering chart gives you and it is the
half a renderer least needs, because a wave field is a direction as well as a height and the
direction is what turns crests. **The same solution carries both**, and taking only the amplitude
from it is the reason the term keeps getting described as "a soft edge on the shadow".

**The solution, in the form Penney & Price (1952) applied to water waves.** Sommerfeld (1896) solved
the half-plane exactly — the first exact solution of any diffraction problem. With `e^{−iωt}`, a
screen along `φ = ±π` from the edge, and a unit plane wave arriving **from** direction `φ₀`:

```
u(r, φ) = U(r, φ − φ₀)  +  s · U(r, 2π − φ − φ₀)

U(r, ψ) = (1/√2)·e^{−iπ/4}·[ (1+i)/2 + C(X) + i·S(X) ]·e^{−i k r cos ψ},
X(r, ψ) = 2·√(kr/π)·cos(ψ/2)
```

`C`, `S` are the Fresnel integrals; `s = +1` for a **rigid (Neumann)** screen, which is the
water-wave case — no flow through a breakwater or a headland — and `−1` for pressure release. The
first term is the incident wave switched off across the **geometric shadow** boundary; the second is
the reflected wave switched off across the **reflection** boundary. Each switches through exactly
`1/2` at its own boundary because `X = 0` there and `F(0) = 0` exactly — *that* is where this
section's `K_d(0) = 0.5000` comes from, and it holds at every range rather than asymptotically.
**`P` for the two papers; `D` for the form as written, which was verified here rather than
transcribed.**

> **The second term's argument is `2π − φ − φ₀`, not `φ + φ₀`.** Both give the same plane wave —
> `cos(2π − φ − φ₀) = cos(φ + φ₀)` — but they switch it on in **complementary** regions, and
> `φ + φ₀` stands the reflected wave at full strength *inside* the geometric shadow. `U` is
> **4π-periodic**, so `2π − ψ` is the other sheet of the same function, which is the whole content
> of "the half-plane lives on a two-sheeted Riemann surface". The reference implementation shipped
> `φ + φ₀` first and it drew a completely convincing lee; what caught it was the `1/2` on the shadow
> boundary reading **1.106 / 0.615 / 1.323** instead. **`D`, and recorded because the picture cannot
> find it.**

**The direction is `grad(arg u)`.** `u` is complex, so `k_vec = ∇(arg u) = Im(∇u / u)` is the local
wavenumber vector, and it is an **output** of the wave solution with nothing per-station stated
anywhere in it. Measured on the reference implementation (`D`):

- **Deep in the geometric shadow the orthogonal is RADIAL from the tip**, to **0.10°** at ranges of
  0.6–2 km on a 126 m swell, with `|k_vec|/k = 1.000` to 7×10⁻⁴. Nothing radial is put in: the field
  is two Fresnel integrals of a plane wave. So "the fan converges on the diffraction point" is a
  **result**, not the ansatz a plan-form construction has to assume it is.
- **Far in the lit region it is the incident direction**, to 0.02° at 12 km.
- **Near the shadow boundary it is neither, and it rings** — `K_d = 0.980` and the orthogonal
  **0.89°** off the incident direction at Fresnel parameter `v = −5.4`. The lit side of an edge
  overshoots; a model that returns a clean 1.0 and 0.0 there has smoothed the physics away, which is
  the same failure as blurring the shadow seen from the other side.

**What this section's own numbers survived.** An independent implementation (no scipy in the
container; Fresnel integrals built from a power series, Gauss–Legendre quadrature and an asymptotic
series, cross-checked against each other) reproduces `K_d(0) = 0.50000` and `0.30783 / 0.20267 /
0.11103` against the `0.31 / 0.20 / 0.11` above, and **all seven columns** of the lee centre-line
table to ≤ 0.005. **`D`, and the table's convention is now stated because it was not obvious:** the
centre-line values are the **coherent sum of two half-plane edge fields**, `2·K_d(v)` with
`v = (W/2)·√(2/(λr))`, the two edges being equidistant on the centre line and therefore in phase. A
Fresnel–Kirchhoff integral over the *aperture* on the same geometry gives 0.431 at `r = W²/λ`, not
0.51, so a reader reconstructing the table from the words alone would have missed it.

![The knife-edge diffraction coefficient across the shadow boundary, and the Cornu spiral beside it](figures/sommerfeld-half-plane.png)

> **Figure 12·4 — the half on the shadow boundary, and why it is a half.** `D`. Drawn by
> [`figures/make_figures.py`](figures/make_figures.py) (`fig_sommerfeld`) from
> `reference-impl/beach_diffract.py`'s own `knife_edge_kd`, `fresnel` and `cornu_limit` — the
> same Fresnel integrals the suite checks, not a second implementation. Scene-linear; `K_d` is an
> amplitude ratio. **Left:** `K_d(v)` with `v > 0` into the geometric shadow. Three things a ray
> model gets wrong are all in the shape. `K_d(0) = 0.5000` **exactly**, at every `kr`, with no
> asymptotics in it. The **lit side overshoots and rings** — 1.122 at `v = −1`, still 1.052 at
> `v = −3`, decaying as the Cornu spiral winds in — so a model that returns a clean 1.0 outside the
> shadow has smoothed the physics away in the same way, and for the same reason, as one that
> returns a clean 0.0 inside it. And the shadow side has **no edge at all**: it decays smoothly
> through the chapter's own 0.30783 / 0.20267 / 0.11103 at `v = 0.5 / 1 / 2` (marked). **Right,
> the Cornu spiral, which is the argument rather than an illustration:** `K_d` is `1/√2` times the
> **chord** from the current point `(C(v), S(v))` to the upper eye. The three marked points are
> **collinear** — `(−½, −½)`, the origin, `(+½, +½)` — so the chord from the origin is exactly half
> the chord from the far eye, and `K_d(0) = ½` follows from `C(±∞) = S(±∞) = ±½` and nothing else.
> That is the whole of "the half is a half and not something else", and it is one look.

**Three checks that can actually fail, and what each one cannot see.**

| check | what it says | what it is blind to |
|---|---|---|
| `(∇² + k²)u = 0` on a 4th-order stencil | residual 1.4×10⁻⁶, and it falls as `h⁴` (5.056 / 5.060 against the stencil's 5.0625), so it is truncation | **almost everything.** A *sum* of solutions is a solution, so the PDE constrains nothing about the boundary conditions: of seven deliberate defects it caught only the one that broke the arithmetic |
| `K_d = 1/2` on the geometric shadow boundary | 0.529 / 0.514 / 0.507 / 0.504 at `kr` = 25 / 99 / 398 / 1591, and `(K_d − ½)·√(kr)` is **constant to 0.005** — the departure is the reflected term, not an error | nothing much: it caught 3 of the 7 |
| energy across two downwave lines | equal to 3×10⁻⁴; and split at the shadow boundary, the **gain** in the geometric shadow is **0.98** of the **deficit** on the lit side | a scale error common to both sides |

**The energy statement is the one worth quoting to a reviewer**, because it is the answer to "where
did the wave in the lee come from": exactly as much flux appears where a ray model puts none as goes
missing from the side that was lit. A model that fills the lee by widening a filter cannot make that
statement, and a model that masks the obstacle and stops propagation fails it outright.

### The shoreline is part of the wave field, and a straight one is a test that cannot fail

Everything above turns *crests* onto contours. Nothing above asks where the **contours** came from,
and on a coast that matters, because the strongest and cheapest verification a reviewer has is
"do the surf lines follow the curve of the bay" — and **on a straight shore that test passes by
construction**. A straight shoreline plus a shore-keyed ramp gives straight contours, and crests
that arrive already parallel to them have proved nothing about the refraction. The test only has
teeth if the shore curves.

So the plan-form has to come from somewhere, and there are only two honest sources: a drawn
coastline (unverifiable) or a **form**. The form exists and it is coastal-engineering canon.

**The static-equilibrium (headland-)bay.** A sandy shore between two rock control points, worked by
a persistent oblique swell, migrates until the **longshore sediment transport is zero everywhere
along it**. That state has two published closed forms — the **logarithmic spiral** (Krumbein 1944;
Yasso 1965; Silvester 1970) and the **parabolic bay-shape equation** (Hsu & Evans 1989) — and one
testable property, which is the reason to prefer it to any drawn curve:

> At static equilibrium the wave orthogonal is normal to the shoreline at every station, so the
> CERC transport `Q ∝ H_b^(5/2)·sin(2·θ_loc)` is zero all along the bay.

That is a claim with a number attached, and it can be *fired at the shore you built* rather than
asserted about it. **`P/D`**

**Only one member of the family is derivable, and it is the circle.** If the orthogonals radiate
from a pole — the diffraction point of the sheltering headland, or more generally the virtual
source the fan converges on — then the radius vector *is* the orthogonal, "shore normal to the
orthogonal" reads "shore normal to the radius", and the curve is a **circular arc about the pole,
exactly**. If the orthogonal is rotated off the radius by a *constant* δ, the tangent makes the
constant angle `α = 90° − δ` with the radius, and a constant tangent-to-radius angle is the
logarithmic spiral's own definition and nothing else's. That is *why* the spiral, rather than a fit
to four coastlines — the algebra is in
[`12a` §11](12a-water-derivations.md#11-the-static-equilibrium-bay). What is **not** derivable is δ.
Silvester's published α for real bays is 30–50°, i.e. δ = 40–60°, an order above anything refraction
leaves at the break point; that is an empirical fit and must not be confused with a computed
residual obliquity. **`P` for the forms, `D` for the derivation of the circular member, `?` for δ.**

**The parabolic form is not implemented in `reference-impl/` and the reason is provenance, not
preference.** Hsu & Evans' `C₀/C₁/C₂` are three quartic polynomials in β — fifteen fitted
coefficients from a least-squares fit to 27 prototype and model bays — and a fifteen-coefficient fit
has no internal consistency check that would catch a wrong digit. Writing them from memory would
manufacture a citation. The log spiral has **one** parameter and a defining geometric property that
checks itself, so it is the form built. **`?` on the parabolic coefficients: do not cite them from
this chapter, because this chapter does not carry them.**

#### The result that matters to a renderer: a bay is not a property of a shoreline

Impose zero transport on a wave field with **plane offshore crests and shore-parallel contours**
and integrate. Snell is `sin θ = (c/c₀)·sin θ₀` with θ measured from the *local* shore normal, and
`c/c₀` is never zero, so `θ_b = 0` requires `θ₀,local = 0`: the shore normal must lie along the
**deep-water** direction, at every station. Integrating `φ_s = −θ₀` gives

```
x_s(y) = x_ref − tan(θ₀)·(y − y_mid)          # a STRAIGHT coast, rotated to face the swell
```

— one straight line, and **any curvature raises the transport**. terrain-architect `12`'s coastal
loop says the same thing in words ("headlands retreat faster than bays … until the coast
**straightens**") and it is *right* for the wave field it assumes. A curved static-equilibrium bay
is therefore **not** a property of a shoreline. It is a property of a shoreline **and** the headland
that shelters it: the bay exists only where the wave orthogonal **fans** alongshore, and the fan is
diffraction plus refractive focusing at the headland — the term
[the section above](#diffraction-is-not-refraction-and-nothing-above-contains-any-of-it) says no ray
model contains. The two sections are one statement seen from two ends.

**Measured on the reference implementation** (`beach.py`, 1408 m of coast, 89 alongshore stations,
one offshore spectrum `H₀ = 1.5 m, T = 9 s, θ₀ = 20°`, one Dean ramp, one 2-D energy-flux march, one
CERC closure — the only thing that differs between rows is the array `x_s(y)`; `D`):

| shoreline | mean \|θ_loc\| at breaking | `Q` rms, m³/s | vs straight |
|---|---|---|---|
| straight, plane crest | 6.469° | 9.233 × 10⁻² | — (the control) |
| **the closed-form zero-transport coast** (rotated 20°) | **0.202°** | **5.127 × 10⁻³** | **18× down** |
| the log-spiral bay, plane crest | 5.595° | 1.875 × 10⁻¹ | **2× UP** |
| the log-spiral bay, under the fan its own pole implies | 2.801° | 7.921 × 10⁻² | 1.2× down (3.5× over the spiral span) |
| the same bay, ramp keyed **concentrically** about the pole | 2.759° | 6.437 × 10⁻² | the two-line change, and it buys 0.04° |
| **the same bay, ramp keyed to the NORMAL distance to the shore** | **2.448°** | **7.176 × 10⁻²** | 12 % of the residual, and it is the general form |
| the bay, under a **DIFFRACTED** fan — direction only, `H₀` uniform | 3.081° | 6.256 × 10⁻² | `2.10 × 10⁻²` over the spiral span |
| **the bay, under a DIFFRACTED fan — direction AND `K_d`** | **1.875°** | **7.629 × 10⁻³** | **`3.94 × 10⁻³` over the spiral span, 2.2× the floor** |

Read the second row first. **A near-zero reading is worthless until zero has been shown to be
reachable** — that is the fourteenth way a measurement lies (`11`) with the sign flipped, two
instruments agreeing because neither could have said anything else. The rotated coast is the
calibration, and it costs one line.

**And calibrating it found a defect in the transform that eight waves of surf work had not.** The
2-D march's offshore boundary conserved the wavenumber component along the **grid's** alongshore
axis. The Snell invariant is the component along the **contour**. The two agree only for a coast
whose contours are the grid's rows — which every scene in this project had been until the shore
curved. On the closed-form zero-transport coast, which must break at exactly `θ = 0`, the grid-axis
boundary left **4.89°** of residual obliquity and 76 % of the straight coast's transport; against
the local contour it leaves **0.20°**. **If your transform takes a scalar offshore direction and
applies Snell against the grid, it is exact only for a straight coast, and it will be silently wrong
on any bay you give it.** `D`

#### A shore-attached headland does not shelter its own bay, and the geometry says so first

The obvious place to stand the edge is the **updrift headland tip**, and on this coast it delivers
nothing — for a reason that needs no wave theory at all. An edge modifies the field where it
**blocks** something, so before computing a diffracted field, cast the straight ray from each
shoreline station back along the incident direction and ask whether it meets land. On the reference
scene, whose headland protrudes **91 m** seaward at a deep-water obliquity of **20°**, the geometric
shadow is **250 m** of coast — `5` of `89` shoreline stations, and **1** of the bay's `66`, all of
them on the **headland's own updrift face**. `D`

```
alongshore reach of a shore-attached headland's shadow  ≈  protrusion / tan(θ₀)
```

**That is a criterion, and it is cheap.** A headland shelters a bay only if `protrusion / tan θ₀` is
comparable with the bay's own length. Here it is 250 m against 1409 m, i.e. **18 %**, and the bay
the closed form builds is **2.46× more indented than the photograph** — which is the same fact seen
from the other end. **The closed form is building a bay that needs a shelter this coast does not
have**, and the honest reading of the over-prediction is not that the spiral is wrong but that the
frame is not one whole bay between one diffraction point and one control point. `D`

The pole the two-condition solve returns sits **1441 m** from the updrift anchor and **773 m
seaward of the domain**, and it *does* shelter the bay — 55 of its 66 stations. But there is no
barrier there: `D` is a **virtual** source, so the direction its screen extends in has no geometry
behind it. That is the one free parameter in this construction and it is priced rather than hidden:
**rotating the screen through 80° moves the measurement by 0.051° out of 1.90°**, and changing the
wavenumber the edge diffracts at across 4 m, 8 m and deep water moves it by **0.034°** — because the
deep-shadow direction is radial whatever `k` is, so `k` sets the width of the transition and the
spacing of the Fresnel ripples, not the fan. **A constant chosen to make a picture right does not
behave like that.** `?` on the bearing; `D` on both sensitivities.

#### The fan is an OUTPUT, and making it one overturns the attribution above

The last two rows of that table replace the *stated* per-row offshore direction with `grad(arg u)`
of a Sommerfeld edge stamped at the plan-form's own pole — the point `12a` §11 already calls "the
diffraction point, or more generally the virtual source the fan converges on", so standing a real
edge there turns an assertion into a measurement. Nothing per-station is stated: the field still
arrives from outside with one spectrum (`H₀ = 1.5 m, T = 9 s, θ₀ = 20°`) and everything shoreward of
the boundary stays the transform's output. **`D`**

**Read the direction-only row and the full row as two different claims.** `Q ∝ H_b^{5/2}`, so a
shadow that halves the height cuts the transport by 5.7× whether or not the shoreline is an
equilibrium — which is a way a measurement lies, and it is why the third meter below exists:

| meter | straight | the floor | bay, plane crest | bay, stated fan | bay, DIFFRACTED |
|---|---|---|---|---|---|
| mean \|θ_loc\| | 6.469° | **0.202°** | 5.595° | 2.801° | **1.875°** |
| `Q` rms over the spiral span | 9.233×10⁻² | **1.780×10⁻³** | 1.333×10⁻¹ | 2.650×10⁻² | **3.935×10⁻³** |
| rms `sin(2θ_loc)` — the closure with its height and its coefficient divided out | 2.239×10⁻¹ | **4.101×10⁻³** | 2.311×10⁻¹ | 8.907×10⁻² | **5.549×10⁻²** |

**The two meters disagree by an order and the height-free one is the honest one.** `Q` reaches
**2.2×** the floor; `sin(2θ)` is still **13.5×** it. `K_d` falls to **0.073** at the sheltered end,
so the updrift limb of this bay carries an 0.11 m wave and its transport is near zero for a reason
that has nothing to do with the shoreline. **The bay is smaller, not zero, and part of the fall in
`Q` is bought by the shelter rather than by the plan-form.** `D`

**And the fan is not what a stated radial fan is.** In the geometric shadow the diffracted direction
and the radius from the tip agree to **1.07° rms**; over the whole boundary they differ by **11.4°**,
because outside the shadow the field is the incident wave and knows nothing about the tip. A stated
radial fan applies the fan everywhere. **A diffracted field applies it only where the edge blocks
something, and the shadow boundary is where it stops** — that boundary is the thing an assumed fan
cannot have.

**This overturns the residual decomposition below, and the overturn is a measurement.** That
decomposition attributes 0.71° to the ramp's keying and 1.46° to the march meeting curvature, both
measured with **exactly radial** incidence on the circular bay, which puts the "attributed floor" at
**2.371°**. Take one shoreline, one bed, one transform and change only the incidence:

| incidence on the circular bay, cartesian ramp | mean \|θ_loc\| |
|---|---|
| exactly radial from the pole | 2.371° |
| **Sommerfeld's diffracted field from the same pole** | **1.278°** |
| exactly radial, concentric ramp | 1.661° |
| Sommerfeld, concentric ramp | 0.998° |

The diffracted field gets under the attributed floor **with the ramp and the march untouched**, and
it survives grid refinement — at `dx` = 8 / 4 / 2 / 1 m the first pair reads 2.475/1.403,
2.371/1.278, 2.320/1.219, 2.295/1.190, both converging and the gap not closing — so it is not the
column march's discretisation. **The two contributions are therefore not independent of the
incidence and must not be quoted as an additive floor.** The mechanism is that a stated radial fan
is radial *at the shoreline station*, while the physical field is radial *at the point it is
evaluated at*; on concentric contours the second is normal to every contour it crosses and the first
is not. `D`

#### Where the residual goes, and the honest answer

The bay under its own fan is **small and not zero**: `2.65 × 10⁻²` m³/s over the spiral span against
a meter floor of `1.78 × 10⁻³` — about **15× the floor**. It decomposes, and the decomposition is
the useful part:

- **The ramp is keyed along the grid's axis rather than to the shoreline curve** — worth **0.71°**
  on a circular bay at radial incidence and **0.25°** on the bay actually built. `D`, and the gap
  between those two numbers is a finding in its own right; see below.
- **1.46° — the solver, on a curved bed.** A column-marched transform carries the ray's alongshore
  drift only through its `∂k/∂y` terms. At 20° the drift is 0.36 of a cell per step, not the 0.015
  the near-normal case gives, and on straight contours at the same obliquity the same march leaves
  only 0.20°. So the extra is the march meeting curvature, not physics. `D`
- **The declared residual obliquity `δ`**, which neither of the two above named and which turns out
  to dominate the built bay: **+1.40°** of the +1.42° the bay actually carries. `M`

Neither of the first two is a tolerance and neither was widened. **The claim that survives is the
mechanism** — that a bay's equilibrium is a statement about the shoreline *and* its sheltering
headland together — and the claim that does not is "the built bay carries zero transport", which it
does not, by a factor that is now attributable rather than absorbed.

#### The cross-shore distance is a distance to a CURVE, and this is where a renderer gets it wrong

`d = A·(x_s(y) − x)^(2/3)` is not the Dean profile on a curved coast. It is the Dean profile
*composed with an offset along the grid's x axis*, and that generates the family of **translates**
of the shoreline; the profile's own sentence — "depth ∝ distance from the shoreline" — generates the
family of **normal offsets**. The two agree if and only if the shore runs parallel to the grid's
alongshore axis, which is every straight-coast scene ever shipped. Three things follow, and the
algebra is in [`12a` §11](12a-water-derivations.md#what-cross-shore-distance-means-on-a-curved-coast--and-why-an-axis-offset-is-not-a-normal-offset). **`D`**

- **A normal offset shares its normal lines with the shoreline**, so a ray launched normal to the
  shore is normal to every contour it crosses and Snell is the identity along it. A translate does
  not: after travelling `s` the ray meets the contour belonging to station `y + s·sin φ_s`, whose
  normal has turned by `Δθ = −(dφ_s/dy)·s·sin φ_s` to first order — curvature × offset × the sine of
  the shore's obliquity **to the grid**. Measured off the bed at the 2 m contour: 0.397° axis-keyed,
  0.0008° normal-keyed, 0.397° from the formula.
- **The translate family's perpendicular contour spacing varies as `cos φ_s`** — 5.4 % of crowding
  across this bay — so *rotating the grid changes the bathymetry*. That is disqualifying for a
  landform claim on its own, before any wave touches it.
- **"Key the ramp concentrically about the pole" is the special case for a circular shore.** Keying
  it to the distance to the curve needs no pole and is right for a composite coast — headland,
  spiral, tangential beach — of which only the middle third is an arc about anything. Its one limit
  is the shoreline's **medial axis**, where normal offsets fold and `min` creases the bed: 0 % of the
  ramp on the analytic bay, 0.25 % on the same scene's rough rock shoreline, which is the signal
  that a 90 m-radius wiggle is too sharp for a 483 m ramp to be keyed to.

**Measured on the built bay under the same fan, the same transform and the same CERC closure — one
field changed:** mean `|θ_loc|` **2.801° → 2.448°** and `Q` rms over the spiral span
**2.650 × 10⁻² → 2.454 × 10⁻²** m³/s, against a floor of `1.780 × 10⁻³` that the keying does not
move (the zero-transport coast is straight, so both keyings give it the same contour *directions*
and differ only in the depth they assign). The concentric ramp instead gives 2.759° and
**3.189 × 10⁻²** — lower angle, *higher* transport, because `Q ∝ H_b^(5/2)` and a different bed
shoals differently. **`M`**

#### The attribution failed, and it failed in the statistic

The 0.71° above was measured on a circle and quoted against a bay. It reproduces exactly on the
circle and removes 0.041° of the bay's whole-domain mean. The reason is worth more than the fix:
**every number in that attribution is a mean of `|θ_loc|`, and `mean|·|` is not additive.** The
keying error is antisymmetric about the bay's apex (`sin φ_s` changes sign there), so it is
**scatter, not drift** — 0.710° in `mean|θ|` and 0.05° in the signed mean. Hold the geometry exactly
fixed and sweep only the incidence obliquity and the ramp term falls 0.710° → 0.111° while the
signed term does not move: the two "independent" terms are not independent **in that statistic**.
In the signed mean the four terms sum to +1.375° against +1.420° measured, and the physics
decomposes fine. **Attribute in a statistic that adds; report in whichever one the reader needs.**
`M`

#### For the reviewer

- **If the scene has a curved shore, ask where the curve came from.** A drawn one is authoring and
  should be labelled as such; it is not wrong, it just cannot be verified and must not be presented
  as an output.
- **If the shore is straight, the refraction check is void** and a different one is owed — a rotated
  test bed, or the isolated-obstacle test above.
- **If a bay is claimed to be sheltered, ask which object shelters it and how long its shadow is.**
  `protrusion / tan θ₀` against the bay's length, before any wave model. A shore-attached headland
  at a small obliquity shelters almost nothing, and a "diffraction point" that turns out to be a
  virtual source a kilometre offshore is a fitted parameter wearing a physical name.
- **If a diffraction term is claimed, ask for the direction field and not only for `K_d`.** An
  amplitude chart is half the solution and it is the half that does not turn crests. Ask also what
  the model does on the *lit* side of the shadow boundary: the real field overshoots and rings
  there, and a clean 1.0 is the same defect as a blurred shadow.
- **If a transport residual is decomposed, ask whether the pieces were measured at the same
  incidence.** Two contributions measured under one boundary condition do not add to a floor under a
  different one; on this scene a decomposition that looked additive was got under by 0.5° once the
  incidence became an output.
- **If the plan-form is claimed as an equilibrium, ask for the transport profile and for the
  meter's floor.** Two numbers, and the second is the one that gets left out.
- **The bay's indentation is the one number to compare against a photograph, and it must not be
  fitted to one.** On this scene the closed form gives **122.8 m over 1409 m** where the owner's
  overview photograph gives roughly **50 m over 1408 m** — 2.46×, reported and not corrected.
  Inverting the same closed form instead, the deep-water obliquity that *would* produce 50 m is
  **8.45°** against the scene's declared 20°: a measurement of the offshore spectrum out of a
  plan-form, which is a result worth having and a calibration worth refusing.

**Gap reported to the sibling skill.** terrain-architect `12-glacial-coastal.md` carries the coastal
loop, longshore drift, spits, the Dean profile and the surf-zone morphodynamics, and **neither
plan-form closed form**. Its only statement about coastal plan-form equilibrium is the "until the
coast straightens" clause — which this section shows is exactly right *and* exactly why a bay needs
a term that chapter does not have. The log-spiral and parabolic bays belong there, next to the
coastal loop that cannot produce them.

### Tier 1 — depth-modulated ambient synthesis

The baseline that every water system should ship: keep the FFT/Gerstner cascades and modulate
them by the depth field at sample time — amplitude attenuated toward zero as depth → 0 (with
the shoaling bump first: gain, then cut), wavelength compressed by sampling the cascades
through a depth-driven UV warp or by cross-fading to a pre-generated "shallow" spectrum
variant, and chop/steepness raised as `a/h` grows so near-shore crests sharpen. For Gerstner
sums, per-wave depth response is direct: evaluate each wave's `k(ω,h)` and Green's gain at the
vertex. Honest limits, stated in review: phases stay wind-aligned (no true refraction — the
diagonal-surf tell survives anywhere the shore is visible), nothing breaks, and depth-warped
UVs shear the cascade textures if pushed hard. Tier 1 alone is acceptable only where the
camera never lingers on a beach.

### Tier 2 — the shore-wave band (production default)

The look players call "realistic waves" is a **separate, authored wave train owned by the surf
zone**, cross-faded with the ambient sea over a blend band offshore. Its components:

- **Phase from travel time, not from wind.** Precompute (at import/cook, from the bathymetry)
  a wave-travel-time field `τ(x)`: the arrival time of a wavefront propagating shoreward at
  depth-dependent speed `c(h) = sqrt(g·h)` (an eikonal/fast-marching solve, seeded from deep
  water). Iso-lines of τ *are* refracted wavefronts — crests wrap headlands, focus on points,
  and align to every shore for free. The cheap fallback — phase straight from the
  shore-distance field — is acceptable for simple coasts but cannot focus or wrap correctly;
  say which one shipped. Animate `phase = τ/T − t/T` and the crests march shoreward forever.
- **Profile, not sine.** Displace a crest profile (authored 1D shape or steepened Gerstner)
  along the phase; steepen it as `a/h` rises; asymmetrize it (steep front face, long back)
  approaching the break. ⚠️ Those are **two** operations on one harmonic and only the second reaches
  the face — steepening at zero phase buys a *peaked crest* and 1.299× of face slope at its own
  validity limit, against 2.000× for the rotation
  ([A peaked crest is not a steep face](#a-peaked-crest-is-not-a-steep-face-one-harmonic-two-moments)).
  Where the `H ≈ 0.78·h` mask trips, hand over to the breaker
  treatment: spilling = foam front crawling down the face (profile + animated foam, cheap,
  right answer for most beaches); plunging = an authored curl — flipbook, skinned mesh, or
  particle sheet — placed along the break line (hero-tier, budget it); surging = no break,
  boosted run-up against the slope mask that says "rock".
- **Sets and groupiness.** One global period reads as a metronome. Superpose two or three
  periods (7–14 s band) with a slow group envelope so big sets arrive irregularly, and jitter
  phase slightly along-shore. The group envelope is also the run-up driver: big set → big
  run-up → wet-sand band advances (`13`).
- **Foam lifecycle.** Foam is born on the break mask, advected shoreward with the bore, decays
  exponentially into streaks in the swash, and is dragged back by an ebb phase — one
  accumulating foam target with decay, exactly the machinery of the Jacobian whitecap
  accumulator, reused. Hand the *final* foam edge to the shoreline-foam band of
  [Shoreline integration](#shoreline-integration); they must share phase or the surf and the
  shore argue.
- **Energy bookkeeping in the blend band.** Cross-fade ambient cascades *down* as the
  shore-wave band fades *in* (by depth or τ), never add them — added energy doubles wave
  height exactly where shoaling is also boosting it, and the blend band becomes a wall of
  water.

```hlsl
// Shore-wave band evaluation, per vertex/pixel; all fields from the handoff + cook
float  h     = FilteredDepth(xz);                  // bathymetry smoothed at ~L scale
float  tau   = WaveTravelTime(xz);                 // eikonal precompute, speed sqrt(g*h)
float  A     = A0 * GroupEnvelope(tau, t)          // sets: slow multi-period envelope
             * ShoalGain(h)                        // Green's-law bump, clamped
             * saturate(h / hFade);                // and the final cut at the sand
float  phase = frac(tau / T - t / T);              // crests march shoreward
float  brk   = smoothstep(0.70, 0.85, A * profilePeak / max(h, 1e-3)); // H ~ 0.78 h
float  disp  = A * CrestProfile(phase, /*steepen by*/ A / max(h, 1e-3));
// brk gates the breaker treatment (spill foam / plunge construct / surge run-up by slope mask)
```

### Tier 3 — wave particles and packets

The simulation-grade tier: Lagrangian carriers of wave energy advected over the bathymetry and
rasterized into a displacement field each frame. **Wave particles** (Yuksel et al.) made it
real-time — each particle a small wavefront segment that subdivides as fronts spread. Production
water systems of that era are documented in Gonzalez-Ochoa's GDC 2012 *Uncharted* talk (ocean
mesh LOD, wave generation, flow shader); that the shipped technique was specifically wave
particles is commonly repeated but **not confirmed** against the talk — treat it as `?` and do
not cite it as the shipped implementation. **Wave packets / water surface wavelets** (Jeschke & Wojtan and successors) carry a
full dispersive wave *group* per carrier, so refraction, dispersion, and shoaling over
arbitrary bathymetry emerge rather than being painted. Cost honesty: this tier buys emergent
shore behavior and object interaction with research-grade machinery — tens of thousands of
carriers, a rasterization pass, careful LOD — and in production it is usually *targeted*
(wakes, a hero cove) while Tiers 1–2 still carry the open sea. It does not replace the
interactive sim patch: particles carry traveling waves; the patch owns local
splash-and-ripple response. They can share the rasterize-to-overlay stage.

### Shoal awareness is depth awareness, not distance awareness

Key the system off **depth**, never off distance-to-shore alone. An offshore sandbar or reef
must brighten the water color ramp, steepen and break its own line of surf — hundreds of
meters from any shoreline — and let the reformed, smaller wave travel on to break again at the
beach. Double surf lines over bars are a signature of real coasts, and they fall out for free
when shoaling, breaking, and the travel-time solve all read bathymetry; they are *impossible*
when the surf system is keyed to the shoreline distance field. Shore distance drives only what
genuinely belongs to the waterline: run-up, wet sand, and the final foam edge.

### Wave–current interaction: the flow field's part

The fourth handoff input — the flow field — modifies shallow-water waves, and the shore-wave
band must read it or the two water systems of this chapter visibly ignore each other where
they meet. The physics: in a current `U`, the observed frequency Doppler-shifts,
`ω = σ + k·U`, with the intrinsic frequency still obeying `σ² = g·k·tanh(k·h)`. Waves running
*against* a current shorten and steepen (energy piles into a slower-advancing train); when the
opposing current approaches the wave group speed, the waves are **blocked** — they cannot
propagate upstream and must steepen until they break. Waves riding a *following* current
lengthen and flatten. The visible cases are exactly the seams between this section and the
rivers section: a river mouth at outflow (a line of steep, breaking, directionless chop over
the bar, even in a mild sea), tidal inlets, and rip currents — narrow outbound flows that
block incoming surf locally and read as smooth dark lanes cutting through the breaker line,
with their foam streaked *seaward*.

The real-time treatment is modulation, not simulation — same doctrine as the rest of the
section. From the shore band's own quantities: wave direction is `normalize(∇τ)`, opposition
is its dot with the negated flow, and everything keys off that scalar:

```hlsl
float2 U    = DecodeFlow(FlowField.Sample(s, uv));        // handoff flow field, m/s
float  cg   = sqrt(9.81 * max(h, hMin));                  // shallow-water group speed: c_g = c
                                                          // (NO 1/2 — that is the deep-water
                                                          //  c_g = c/2 relation, wrong here)
float  opp  = dot(normalize(gradTau), -U) / cg;           // 1 ~ blocking
A          *= 1.0 + kSteepen * saturate(opp);             // shorten/steepen against flow
brk         = max(brk, smoothstep(0.8, 1.2, opp));        // blocked -> forced break/chop
// opp < 0 (following current): mild lengthen/flatten — scale A and steepness down slightly
```

Where `opp` crosses the blocking range, stop drawing a coherent marching wave train at all:
replace the band locally with steep short chop plus a persistent foam patch (the
river-mouth-bar look), and let the rivers section's flow-mapped surface own the water inside
the outflow. Foam in the surf zone advects by the *sum* of bore motion and the flow field, so
rip and outflow foam streaks point seaward for free. Two refinements, both honestly optional:
fold `U` into the travel-time solve as an anisotropic speed term (`c(h) + U·dir`) so current
refraction lands in the precompute — valid only for static flows like river mouths, since τ is
baked; and modulate at runtime for tidal flows if the game has them. State the limits in
review: this is Doppler-flavored amplitude/steepness shaping — there is no momentum exchange,
no actual blocking dynamics, and rip currents must exist in the exported flow field to appear
(inventing them renderer-side violates the handoff doctrine — route to terrain-architect).

### Data contract additions

Per the chapter's rule — extend the handoff, don't derive hydrology renderer-side — the
shore-wave system asks the pipeline for: **filtered depth** (bathymetry smoothed at roughly
the wavelength being modulated; raw bathymetry noise makes wave response flicker and the break
line dither), a **beach-slope / breaker-class mask** (from the generator's slope analysis —
this is what keeps spilling foam off cliff faces), the **shore normal** (gradient of the shore
distance field, for run-up direction and foam advection), and the **travel-time field** τ
(derived data, baked at import/cook from bathymetry — cheap to store, one R16 channel).
Wave–current interaction needs *no* new data — the flow field is already in the handoff; the
only optional addition is baking static flow into the τ solve as above.
Max shore-wave amplitude joins max ambient amplitude in the culling-bounds inflation.

### The surf zone: what a pool reference lends the sea, and the one thing it cannot

A treated pool is the cleanest optics laboratory a water renderer has — flat datum, known bed,
known depth, `b_b ≈ 0` — and the temptation after doing that work is to assume the sea is the same
physics at larger numbers. **Most of it is.** The exception is a single one, it is the one that
decides the colour, and knowing which is which is worth more than any individual sea constant.

| what transfers from a pool **unchanged** | why |
|---|---|
| external Fresnel, and internal Fresnel with its critical angle | properties of one interface and one IOR; the ocean's `n` is 1.339 against fresh water's 1.333 — a 0.4% shift, worth 0.02% on the transmitted share |
| the `1 − 1/n²` partition, and `L/n²` across the interface | [radiance is not conserved](#radiance-is-not-conserved-across-the-interface); geometry and IOR only |
| Beer–Lambert along every leg | the law, not the coefficient |
| the trapped series, wherever there is a bottom in reach | [the two materials a pool has](#the-two-materials-a-pool-actually-has-and-neither-is-water) |
| dispersion, and [a channel is a band](#a-channel-is-a-band-not-a-wavelength) | `n(λ)` is Cauchy in both |
| the meniscus, the glitter path, the caustic Jacobian | surface mathematics |
| **the IOPs** | **nothing transfers. `b_b ≈ 0` is the pool's degenerate case and it is false everywhere in the sea** |

**One exposure refutes the `waterColor` category error outright, and it needs no measurement.** In a
frame of a breaking wave shot into the light, the wave *face* reads a saturated translucent green
while the same water two metres away reads grey-blue. **The same liquid shows two colours at once**,
so the green cannot be a tint on the water body: it is a **path-length effect**, present only where
the column is thin *and* backlit and absent everywhere else in the same frame. That is the sharpest
available statement of the rule this chapter already gives — **the colour is the path, so it must
vanish when the path does** — and a renderer whose sea is green everywhere has tinted it. This is
the falsification a `waterColor` parameter cannot survive, and it is a photograph anybody can take.

**A breaking wave is a wedge, which makes it a variable-path cuvette, which makes it an
instrument.** Thin at the lip, thick toward the trough, with the colour grading continuously across
it. (⚠️ It is an instrument for a *photograph*. As a **criterion on a height-field renderer** the
same face is unreachable, and that is a theorem rather than a budget —
[below](#the-30-ceiling-a-single-valued-crest-cannot-be-read-lengthwise).) Two points on one backlit
face at estimated thicknesses `L₁` and `L₂` invert directly:

```
T(lambda, L) = exp(-c(lambda) L)          # c = a + b, beam attenuation along the transmitted path
=>  c(lambda) = -ln( T_2 / T_1 ) / (L_2 - L_1)
```

The ratio kills the source spectrum, the surface transmission at entry and exit, the camera's
exposure and any constant gain — **everything that is not the path** — which is why a *within-frame*
pair works where absolute triples do not, exactly as `11`'s
[seven ways](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one)
requires. The thicknesses come from the wave geometry, so the whole measurement is one frame plus a
crest profile. **A breaking wave is a free spectrophotometer pointed at precisely the unknown**, and
the unknown is the only quantity in the table above that the pool work cannot lend.

**How far off the pool's own water is, in a number.** Pure water over a 2 m path transmits
`(0.593, 0.899, 0.980)` (`D`, recomputed at the band means `a = (0.2617, 0.05299, 0.01022) m⁻¹`) —
a mild shift toward blue-green, and **not** the saturated green a coastal wave face shows. That
green is CDOM and chlorophyll taking the blue and leaving a window near 550 nm: not an extra effect,
[different IOPs](#water-body-optical-identity-where-the-iops-come-from), and the same machinery run
from the other end.

**A confusable pair, with the discriminator, because both are in every coastal frame.**

| | mechanism | how to tell |
|---|---|---|
| **shallow bottom** | you see the bed through the column; bright for exactly the reason a pool is | it **reveals** structure, and that structure **stays put** |
| **suspended sediment** | a scattering veil *in* the column | it **hides** the bed, **moves with the water**, and **pulses** with the wave |

The discriminator is temporal and it costs nothing: **watch it while the water moves.** A bed does
not move; a veil does. The same test settles the corresponding question at a pool — whether a dark
patch is weathering on the liner or something in the water — and it is more reliable than any
single-frame reading because it uses the one axis a photograph does not have.

**The cloud left after a wave breaks on rock is two clouds, and they are separated by decay rather
than by appearance.**

| | lifetime | behaviour |
|---|---|---|
| **entrained air** | **seconds** — bubbles rise and burst | the bright white plume that visibly shrinks; buoyant, so it goes *up* and out |
| **suspended sediment** | **minutes** — settles, and advects with the current | the stain that stays; denser than water, so it goes *down* and along |

They overlap in space and look alike in a still. **One decay curve fits neither**, and the tell is a
plume that either vanishes too fast to leave a stain or lingers too white for too long. This is the
same one-white-several-mechanisms error [Aerated water](#aerated-water-foam-spray-and-whitewater)
records for foam and spray — now with a *temporal* separator instead of a spatial one, which is
worth noticing on its own: **when two mechanisms are inseparable in space, look for an axis on which
they are not**, and lifetime is the cheapest one to instrument.

⚠️ **And there is a third confusion on top of those two: both of them hide the bed, and a render may
not credit one for the other.** In a measured surf scene they are not remotely comparable. Over
50 713 pixels at 1.5–3 m depth, per-band medians (`D`, recomputed here off the scene-linear buffer):

| depth band | the **suspension**'s own transmittance | the **plume**'s, `T²/(1 − R·R_sub)` |
|---|---|---|
| 1.5 – 3 m | **2.76×10⁻⁵** | **0.152** |
| 3 – 6 m | 1.29×10⁻⁵ | 1.000 — no plume at this depth in this frame |
| > 6 m | 1.40×10⁻² | 1.000 — likewise |

**The suspension beats the entrained air by four orders of magnitude**, and the depth dependences are
not even the same shape: the suspension's is Beer–Lambert on a column that grows with depth, while
the plume's is set by the *plume's own* thickness — of order `H/2` at the surface — and is simply
**absent** below it. So a render carrying only the entrained air would still hide the bed in the
breaking band, **for the wrong reason, with the wrong depth dependence, and on the wrong clock**
(seconds against minutes, per the table above). It would then fail everywhere the plume is not, which
is most of the water.

**Measure each one absolutely and never as a ratio of the two.** The obvious guard — bed radiance
seen over bed radiance emitted — is blind here, because in the breaking band the suspension has
already driven *both* terms to the floor and the quotient of two near-zeros carries no information:
that guard reported `1.6×10⁻⁴` for a control run with the plume switched **off**, where the answer is
`1` by construction. The absolute row is the one that works — the bed's radiance out of the water is
`3.50×10⁻⁸` with the plume and `3.86×10⁻⁶` without, in the same scene-linear units as everything else
in the frame. Same disease as
[`11`'s tenth way](11-verification-failures.md#the-tenth-way-a-ratio-cannot-see-a-common-factor), met
in a new place: **one absolute row per quantity, and the ratio only ever computed forward.**

**And the structural obstacle, which is not an extension of anything above.** A plunging breaker
throws its lip forward over an air tube, so for the duration of the overturn the free surface is
**multivalued** — there is water above air above water on one vertical line. That is the moment
`z = f(x, y)` stops existing, and with it goes the height field, the caustic pass's Jacobian, the
surface-intersection route and every LOD scheme in [Surface geometry](#surface-geometry--lod). It is
a **different representation** — a parametric sheet, a particle/level-set hybrid, or a genuinely
volumetric surface — and it is the real work in surf. Everything else in this section is arithmetic
on machinery that already exists; this one is not, and the honest planning move is to price it as a
representation change rather than to schedule it as a feature (`?`). **And it is not the only thing
on the far side of that line** — the backlit face two paragraphs up is there too, for a reason that
turns out to be the same one at an earlier instant
([below](#the-30-ceiling-a-single-valued-crest-cannot-be-read-lengthwise)).

**The reference gap, named.** Nine frames of surf and coast supported the paragraphs above — an
unbroken wave face, a coastline from a cliff, a rock break, two breaking lines with persistent foam,
a backlit face, a mid-break lip. **None of them catches the backwash lifting sand**: the swash
retreating down a beach face with the sheet flow visibly loaded is the one frame that would pin the
erosive half of the cycle, and it is missing. Written down because a marked gap in a reference set
is worth more than a confident inference from the frames that are there.

### The 30° ceiling: a single-valued crest cannot be read lengthwise

The cuvette above is the sharpest optical criterion in this chapter, and it is the one criterion
here that **a height-field renderer is not merely failing but is barred from meeting**. That is a
theorem, it has no depth, wavelength, wave height, grid, sea state or shader in it, and it is worth
more than the phenomenon it forbids — because a limit of the *representation* survives every
improvement to the implementation, and the alternative is a team steepening waves forever.

**Half of it is Stokes' corner (1880), and it is four lines.** At the crest of the **limiting** wave
of permanent form the fluid is at rest in the frame moving with the wave, so the crest is a
stagnation point and Bernoulli on the free surface, measured downward from it, is `q²/2 + gz = 0`
— hence `q ~ (2g|z|)^½ ~ r^½` near the corner. A potential flow in a wedge of interior angle `2α`
has `q ~ r^(π/2α − 1)`. Matching the exponents:

```
pi/(2 alpha) - 1 = 1/2     =>     2 alpha = 2 pi / 3 = 120 deg
```

so **the free surface leaves the crest at 30° to the horizontal**, and *nothing entered the
derivation except the stagnation condition and the wedge*: it is the same 120° for the limiting
deep-water Stokes wave at any order, the limiting cnoidal wave and the limiting solitary wave.
(Longuet-Higgins & Fox 1977 put the maximum inclination of the *almost*-highest wave slightly above
the corner value, near **30.37°**, attained just off the crest — `P`, cited and not reproduced here.
Use 30.4° as the cap if a margin matters; nothing below turns on the difference.)

**The other half is two Snell cones, and it is the half worth restating** — the criterion has been
carried in this project as "the face must be steeper than `90° − θ_c` = 41.48°", which is right for
a symmetric crest and is *not* the reason. The reason is that a sightline through a wave crosses the
surface **twice**, and each crossing costs a cone:

- entering, the refracted ray lies within `θ_c` of the **inward** normal at the entry point;
- leaving, it must lie within `θ_c` of the **outward** normal at the exit point, or it is totally
  internally reflected and there is no path at all.

The ray between them is straight, so one direction has to sit inside both cones. If the surface
inclinations from horizontal at the entry and exit points are `α₁` and `α₂`, the inward entry normal
and the outward exit normal are separated by **at least** `180° − (α₁ + α₂)` (spherical triangle
inequality — so this holds in 3-D, for a ray in any azimuth, not only in the wave's cross-section),
and two cones of half-angle `θ_c` overlap only when that separation is `≤ 2θ_c`. Hence, for **any**
single-valued surface, whatever its shape between the two points:

> **`α₁ + α₂  ≥  2·(90° − θ_c)`** — **82.69 / 82.96 / 83.46°** on this chapter's IOR triple
> (`D`, and the symmetric case is the familiar 41.34 / 41.48 / 41.73° per face).

**Put the two halves together.** A wave of permanent form caps *each* inclination at 30° (30.4°),
so its best possible sum is **60°** — **23° short**, and no split of the budget helps, because the
condition is on the sum. A face at the corner's own 30° would need its partner at **52.96°**, which
is 23° past what any steady wave has anywhere on it.

**Verified two ways rather than argued.** The condition was checked by shooting the full incidence
hemisphere at a wedge and marching the refracted ray (`D`, here): zero rays enter and leave at
`α₁+α₂` = 16.5, 31.6, 41.5, 60.0, 60.7 and **82.96°**, the first survivors appear at 83.10°, and
the threshold is insensitive to the split — 30+53.1, 20+63.1 and 10+73.1 all open at the same sum
and pass the same 83 rays. And on the reference implementation's own bay, `beach_render.py`'s
`through_face` marches the refracted view ray until the free surface comes back down to meet it:
over ~70 000 water pixels the fraction that leave the far side of a crest is **0.0000** at a linear
surface (steepest face **8.23°**) and **0.0000** at a second-order Stokes surface (**15.78°**, a
×1.95 steepening that bought exactly nothing here) — `D`, both recomputed.

**And the geometric wall is not the operative one, which is the practical half.** Even where the
cones just overlap, both crossings are at near-grazing incidence and Fresnel collapses: at
`α₁=α₂=41.6°` the best two-crossing transmittance any ray achieves is **0.098**, and the share of
intercepted flux that gets through is **1.5 × 10⁻⁴** (`D`). It takes **≈50°** faces to pass a
tenth of the intercepted flux and **≈55°** to pass a fifth. So 82.96° is a hard floor and the
phenomenon lives well above it.

| `α₁ = α₂` | 41.6° | 43° | 45° | 50° | 55° | 60° | 70° |
|---|---|---|---|---|---|---|---|
| best `T_in · T_out` | 0.098 | 0.532 | 0.735 | 0.890 | 0.933 | 0.949 | 0.958 |
| share of intercepted flux through | 0.0002 | 0.011 | 0.038 | 0.126 | 0.228 | 0.339 | 0.571 |

⚠️ **What this changes about the criterion, stated plainly, because it is easy to over-read.** The
two-colour backlit wave remains a **valid falsification of a `waterColor` tint** — it needs only a
photograph, and the [diagnostic row](#diagnostic-index-symptom-to-mechanism) that uses it stands
untouched. What it is **not** is a criterion a single-valued surface can be asked to *reproduce*.
The face that shows it is at or past the overturn, which is exactly the
[multivalued instant](#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot)
priced above as a representation change: **the backlit face and the plunging lip are one criterion
at two moments**, and the 23° of summed inclination between a steady wave's best and the two-cone
floor is the width of the gap. A renderer that wants the green face must **author** it — a shader
term keyed to the breaking mask, a bespoke lip mesh, a particle sheet — and say so, because it is
not going to emerge from a taller wave. The honest budget line is *"needs the overturn
representation"*, not *"needs more steepness"*.

### A peaked crest is not a steep face: one harmonic, two moments

The ceiling above says how far a steady wave can go. This says which lever moves it, and the obvious
lever is the wrong one — which matters because the wrong one is what a shoaling model already has
lying around, and reaching for it feels like reuse rather than like a guess.

**The setup, which is standard and is the whole apparatus.** A shoaling wave is a primary plus a
**bound second harmonic**, and one shape parameter and one phase describe it:

```
eta = a [ cos(phi)  +  r cos(2 phi + psi) ],     a = H/2,   r = b/a
```

In shallow water `r → 2·Ur` exactly with `Ur = (3/16)·H·k/(kd)³` — so **any model already carrying
an Ursell number is already carrying `r`**, and the only free thing is `ψ`.

**Both third moments are closed forms of the same two numbers, and that is the finding.** With
`H(cos nφ) = sin nφ`:

```
Sk = <eta^3>/sigma^3   = +(3/4) r cos(psi) / ((1 + r^2)/2)^(3/2)
As = <H(eta)^3>/sigma^3 = -(3/4) r sin(psi) / ((1 + r^2)/2)^(3/2)

    =>   Sk^2 + As^2 = (9/16) r^2 / ((1 + r^2)/2)^3       -- a function of r ALONE
```

(`D`, verified here against a direct numerical quadrature of both moments at four `(r, ψ)` pairs.)
So `r` sets **how much** third moment the shape has and `ψ` only says **which of the two it is
in**. `ψ = 0` is the peaked, fore–aft symmetric crest of a shoaling wave; `ψ = −π/2` is the
pitched-forward sawtooth of a bore. Nothing in between creates or destroys the moment; it rotates.

**Now the slope, which is the quantity a backlit face is about, and the two limits are exact.**
Write the face-slope gain as `max|dη/dφ| / a`, which is 1 for a sinusoid by construction. Each shape
has its own **validity limit**, the `r` at which the surface grows a false crest inside its own
trough (still single-valued, and still wrong) — derived, not chosen:

| shape | why the limit is there | its `r` | slope gain at it |
|---|---|---|---|
| pure **skewness**, `ψ = 0` | `dη/dφ = −sin φ (1 + 4r cos φ)` factorises; the extra root arrives at `cos φ = −1/(4r)` | **1/4** | **3√3/4 = 1.29904** |
| pure **asymmetry**, `ψ = −π/2` | the derivative is a quadratic in `sin φ` whose second root leaves `[−1, 1]` | **1/2** | **2** exactly (`1 + 2r`) |

⚠️ **The same harmonic buys 30% of face slope in one moment and 100% in the other, and the reason is
one line.** At `ψ = 0` the harmonic's slope contribution is `2r sin 2φ`, which **vanishes at the
primary's own steepest point** (`sin φ = ±1 ⇒ sin 2φ = 0`) — so it only reaches the face at *second*
order in `r`, and meanwhile it is spending its whole budget sharpening the crest, where the slope is
zero and nobody is looking through it. At `ψ = −π/2` the two terms add directly at `φ = π/2`, giving
`1 + 2r` at *first* order.

**So "use the skewness" is the right quantity at the wrong moment.** A wave that is merely *skewed*
is **peaked**, not steep. What steepens a face is the rotation, and the rotation is free — it is a
phase, not an amplitude, and it costs nothing in validity: the pitched shape tolerates **twice** the
harmonic the peaked one does, so rotating buys headroom rather than spending it.

This is what [Tier 2](#tier-2--the-shore-wave-band-production-default)'s *"steepen it as `a/h` rises;
asymmetrize it approaching the break"* is two separate instructions **about**, and the table is which
is which: the first is `r`, the second is `ψ`, and only the second reaches the face.

**And the family's own ceiling, swept rather than assumed.** Along the validity boundary the gain is
monotone in `ψ` — 1.299 at 0°, 1.480 at −10°, 1.710 at −30°, 1.927 at −60°, **1.99999 at −90°**
(`D`, `stokes2_crest_limit` bisected at each `ψ`). **×2.000 is the ceiling of the entire
second-order family**, at any `r`, any `ψ`, any depth. Measured against the reference bay, whose
linear steepest face is 8.23°: `×2` on that slope is **16.13°**, and the bay's second-order surface
reached **15.78°** — **97.7% of the ceiling of the whole family**. Second order was not
under-exploited there; it was spent. Combined with [the 30° ceiling](#the-30-ceiling-a-single-valued-crest-cannot-be-read-lengthwise)
above, the ordering of the two limits is the useful part: **the shape family runs out first, the
representation runs out second, and neither runs out because of the implementation.**

## Aerated water: foam, spray and whitewater

When a wave breaks, a fall lands, or a rapid churns, air is entrained and the result is **not water
with foam painted on it — it is a different material**. Treating it as a texture on a transparent
surface is the single most common reason breaking waves, rapids and waterfalls read as wet plastic:
the surface underneath keeps doing Fresnel and refraction when physically there is nothing left to
see through.

**The physics, and the numbers that matter.** Whitecaps and foam are weakly-absorbing,
strongly-scattering two-phase media. Measured **void fractions run 60–99%** in surface whitecaps —
i.e. liquid water is only ~1–40% of the volume — with **mean bubble diameters of 0.16–1 mm**.
Whiteness comes from **multiple scattering across thousands of air–water interfaces**, not from
pigment, which is why foam is broadband white in the visible where water barely absorbs.

**One constant runs the mirror under the surface and every bubble wall in a foam** (~~and the
whiteness of foam~~ — struck; the whiteness is multiple scattering, and the correction is two
paragraphs down). An air bubble seen
from the water side presents the same water→air interface as the surface seen from below, so it has
the same critical angle, and the cosine-weighted flux beyond it is `1 − 1/n²` = **43.72%** at
`n = 1.333` and **43.874%** at this chapter's own green IOR of 1.3348 (`D`, recomputed; it runs
43.64 / 43.87 / 44.31 % across the IOR triple, so it is barely chromatic and one figure is honest).
That is the *geometric* part of the internal reflectance and not the whole of it: the full diffuse
`R_int` is **47.617%**, of which `1 − 1/n²` is 92.1% and partial Fresnel inside the cone is the
remaining **3.743%**. Use `1 − 1/n²` for a bubble wall, which is a per-direction mirror, and `R_int`
for a hemispherical average — [both, and the loss neither of them is](#surface-reflection-names-two-opposite-things-a-loss-and-a-trap).
Every bubble wall mirrors that share of everything striking it: one bubble reads silvered, a cloud
of them reads white and opaque. A renderer that gets Snell's window right and takes foam whiteness
from a painted albedo has special-cased one of the two faces of a single number.

⚠️ **The constant is right and one reading of it is wrong: `1 − 1/n²` is a *reflectance*, not a
backscatter fraction, and this chapter said so loosely enough to be read the other way.** The
sentence above — *"every bubble wall mirrors that share"* — is exactly true and says nothing about
*where* the mirrored light goes. Trace it. A ray reflected off a sphere at incidence `θᵢ` leaves
deviated by

```
Theta_0 = pi - 2 theta_i          the p = 0 (external reflection) branch for a sphere
theta_i > theta_c = 48.52 deg     is what "totally internally reflected" MEANS
=> Theta_0 < 82.96 deg            EVERY totally reflected ray, without exception
```

so not one of the 43.874% comes back toward the source: they all leave **forward of the
perpendicular**. A geometric-optics trace over the bubble's disc — area-uniform impact parameter,
Fresnel by reciprocity, forty orders, energy closing to `1 ± 8×10⁻⁷` — returns a backscatter ratio
of **`b_b/b = 0.023`** and an asymmetry parameter of **`g = 0.688`** (`D`, recomputed here; the
traced pair is `0.0228 / 0.0230 / 0.0235` and `0.691 / 0.688 / 0.684` across the IOR triple).
**Twenty times smaller than the reflectance.** A bubble is a *side* scatterer, not a retroreflector,
and it is why the asymmetry is 0.69 rather than negative.

**So surf is white by *multiple* scattering in a medium of single-scattering albedo ≈ 1, not because
each bubble returns 44% of the light to the eye** — which is what the paragraph above already says
about thousands of interfaces, and what a renderer loses the moment it spends the 43.874% as an
albedo. The operational form is the similarity scaling and not the constant: `τ' = (1 − g)τ`, then
`R = τ'/(1 + τ')` and `T = 1/(1 + τ')` for a conservative slab, which is where a foam layer's
*opacity* and its *whiteness* come from together. Using `1 − 1/n²` as `b_b/b` in a volumetric foam
inflates the backscatter by 19× and gives a plume that whitens without hiding what is behind it —
a defect that reference-impl now carries deliberately (`foam-backscatter-is-tir`) precisely because
it reads as plausible.

**And the constant survives the trace, from the other end.** The same run recovers
`0.4364 / 0.4387 / 0.4431` for the totally-reflected share **without ever evaluating `1 − 1/n²`** —
it is measuring the area of the disc beyond the critical angle, which *is* what the formula is. With
the Fresnel evaluated per channel rather than at the red band's refracted cosine, the trace's full
disc-average reflectance recovers `R_int = 0.47371 / 0.47617 / 0.48068` to six digits as well, from
a ray trace against a quadrature that shares no code with it (`D`, recomputed here). Two
independent routes to both numbers; the arithmetic was never the problem, the noun was.

And **foam is
white rather than tinted because the paths are short**: transmission over 5 mm of water is 0.999 in
red, so light bouncing between bubble walls never accumulates enough path to pick up the water's
colour or the bed's. **Foam is many short paths where blue water is one long one** — which is why
foam over a blue liner and foam over sand are the same white, and why tinting foam toward the body
colour is wrong in every water.

**A single frame of a beach break holds *three* whites, they are three different materials, and
collapsing them into one particle system is the standard reason CG surf reads wrong.**

| what | what it actually is | not | share of the white |
|---|---|---|---|
| the blanket left behind a break | a **coverage mask on the surface** — a bubble layer of high albedo, advected with the surface flow and decaying | not particles, and not a volume | the largest |
| the opacity *inside* the wave mouth | a **participating medium** in the water, high scattering albedo — you stop seeing the bottom through it | not a surface layer | the one that carries the wave's form |
| spray thrown clear along the crest | **water in air** — a droplet size distribution, ballistic, decoupled from the fluid | this one *is* particles | **the smallest** |

They are built on the same `1 − 1/n²` wall reflectance — and, per the correction above, they *whiten*
by multiple scattering rather than by that number — and share nothing else: different carrier (surface / volume /
air), different advection (surface flow / fluid velocity / ballistics), different decay (seconds /
the break itself / sub-second), different rendering (coverage lerp that kills Fresnel beneath it /
`a`,`b`,`g` medium / sprites, becoming a medium at high wind). **The one that gets over-built is the
smallest of the three**, because it is the one that looks like a particle system in a photograph —
and the two that carry most of the white are a mask and a medium, neither of which a particle system
can produce. `19` owns the simulation side; the rendering split is the row above.

**"Aerated water" is two mechanisms that share only that constant**, and merging them is why
jacuzzi water and surf usually get the same wrong effect:

| | Surf, a fall, a breaking crest | An injected plume (jacuzzi, aeration jet) |
|---|---|---|
| Air enters | at the **surface**, folded in by the break | at **depth**, through an orifice under pressure |
| Where it lives | a **skin**, optically thick within centimetres | a **volume** — a buoyant plume through the bulk |
| Time | **transient**: each patch decays in seconds | **steady** while the pump runs |
| Bubble sizes | very wide, microns to centimetres | narrow, set by the nozzle and the shear |
| Renders as | a **coverage mask** you cannot see into | a **participating medium** you see partly through |
| Also throws | **spray** — water in air, a third medium | nothing |

The plume case is the one that needs the `a`/`b`/`g` split rather than a collapsed `sigma`, and it
is the same machinery as [turbid water](#water-body-optical-identity-where-the-iops-come-from)
run to its high end. Note also which fittings do this: a pool's filtration return is submerged and
pumps *water*, so it does not foam; a jacuzzi fitting deliberately aspirates air, which is a
different fitting rather than a stronger one.

**Foam albedo is a decay curve, not a constant** — and this is the most useful single fact here:

| State | Visible reflectance | Reads as |
|---|---|---|
| Fresh, intense breaking | **~50%** | Brilliant white, the moment of the break |
| Active whitecap | **~40%** | The body of the foam |
| Thin residual foam / bubble plume | **~18%** | The dissipating streak behind the crest |

The widely-quoted **~22% (Koepke 1984)** is a *time-averaged effective* whitecap reflectance
derived from film density, and it under-represents fresh foam — it is the right number for
averaging a whole sea over time, and the wrong number for a hero breaking wave. Ship the decay,
not the average: foam should be born bright and fade to a dim streak, with reflectance falling as
the bubble plume thins. A constant-albedo foam texture is why most game foam looks like paint.

⚠️ **And the reason it looks like paint even when the decay *is* shipped: 0.22 is not a foam albedo
at all, so a renderer that models the decay and also uses 0.22 has counted it twice.** Koepke's
number is averaged over the whitecap's **life** *and* over its **area** — it already contains
everything the decay curve above is there to produce. Two ingredients, one number:

- **Coverage.** A whitecap occupies a fraction of the cell and that fraction falls with age.
- **Reflectance.** What the foam that *is* there returns, which also falls with age — Koepke's own
  measurement runs **0.20–0.55 at first breaking to 0.03–0.10 after ten seconds**.

`0.22` is the product of the two, integrated. A model with an explicit coverage mask `W(t)` and an
explicit `R(age)` supplies both, and then multiplying by 0.22 supplies them a second time. **The
symptom is grey foam that no exposure fixes**, because the error is a factor on one material inside
the frame.

**What the fresh foam actually returns, two ways, and neither is 0.22.** A raft a few centimetres
thick is seventy-odd walls of a non-absorbing scatterer. Stokes' pile of plates,
`R_N = Nρ/(1 + (N−1)ρ)` with `ρ` the bubble wall's own `1 − 1/n²`, and a two-stream
`R = τ'/(1 + τ')` with `τ' = (1 − g)·b·h` that never sees that constant, land on **0.983 and 0.985 —
0.21% apart** at `N = 73` walls (`D`, recomputed here). A soap foam is that white and so is fresh
surf. Meanwhile `1 − 1/n²` = 0.4387 sits **inside Koepke's own 0.20–0.55 fresh-whitecap band**: a
published bracket on a derived constant, recorded as **survived**.

**So the numbers on the decay curve above are the ones to ship, and 0.22 is a sea-average
radiometry figure that belongs in a satellite forward model and nowhere in a frame.** What is still
`?` is the shape of `R(age)` between the endpoints — closing it needs Koepke's time-resolved bins,
which are not in hand here.

**Foam is not spectrally flat.** Reflectance drops sharply into the near-infrared, with troughs at
roughly **750, 980 and 1200 nm** corresponding to liquid-water absorption bands — bubbles lengthen
the path through water and *enhance* its absorption. Visible-band rendering can treat foam as
white, but any NIR-sensitive pass (some sensor/thermal views, certain stylised looks) must not.

**Three classes, one seeding criterion.** Production splits aerated water into sets that behave
differently and cost differently — see `19` for the simulation side:

| Class | Where | Motion | Cheapest honest rendering |
|---|---|---|---|
| **Spray** | Above the surface | Ballistic — gravity + drag, decoupled from the fluid | Bright short-lived sprites; at high wind becomes a *participating medium*, not sprites |
| **Foam** | On the surface | Advected with the surface flow, decaying | Albedo layer that **kills the Fresnel term beneath it** |
| **Bubbles** | Below the surface | Buoyant, advected, rising to feed foam | Density term in the water volume; brightens *and* opacifies from below |

Seed all three from the same criterion — the Jacobian/folding signal of
[Ambient waves](#ambient-waves-gerstner-and-fft) offshore, the break mask of
[Shallow water](#shallow-water-shoaling-refraction-and-breakers) inshore, and turbulence
intensity in rivers — so the classes stay consistent with each other and with the wave that made
them.

**Aerated water changes the water's own optics, not just its albedo.** Where bubble density is
high, scattering swamps absorption: the body colour washes out toward white, transparency
collapses, and the depth-based colour ramp of
[Water-body optical identity](#water-body-optical-identity-where-the-iops-come-from)
stops applying. Practically, blend the IOPs toward a high-albedo, high-scattering,
short-mean-free-path set as the aeration mask rises, and drive Fresnel to zero underneath. Foam
that still reflects the sky is an instant tell.

**Backlit crests.** A thin, sunlit-from-behind wave face glows green-turquoise because light is
transmitted through a thin water sheet carrying suspended scatterers. The standard cheap
approximation is view-dependent translucency (Barré-Brisebois & Bouchard, GDC 2011 / GPU Pro 2 —
shipped in Frostbite): compute transmitted light from `dot(V, −L)` distorted along the normal, and
scale it by a **thickness** proxy. For waves the thickness proxy is free: crest height above the
mean plane, or the inverse of the wave's local thickness at the crest. Gate it on the sun being
*behind* the wave relative to the camera, or every crest glows all day.

**Waterfalls are a construct, and the physics tells you how to build it.** A falling sheet does
not stay a sheet: aerodynamic waves grow on its surface until the sheet ruptures, fragments
contract into ligaments (Rayleigh–Taylor), and the ligaments break into droplets by the
**Rayleigh–Plateau** instability, whose most unstable mode for an inviscid column is around
**9× the radius**. So the correct visual cascade down a fall is
**coherent sheet → perforated/streaky sheet → ligaments → droplets and mist**, and the transition
distance shortens as discharge falls. Build a fall as that progression, not as one scrolling
texture:

```
lip        : coherent sheet - the nappe. Scrolling normals, high transparency, sharp edge
upper fall : sheet perforating - streaks and holes appear, foam mask climbs
lower fall : ligaments/droplets - switch to particle-dominated, sheet mesh fades out
impact     : maximum aeration - opaque white, ~50% albedo, Fresnel killed
plunge pool: bubble plume rising, foam disc advecting outward and decaying to ~18%
mist       : lit volumetric column; wets surrounding rock (13) and can carry a rainbow
```

All of it *steered* by the generator's exported discharge and drop height, none of it in the
export. Two consequences follow: a tall fall must be **particle-dominated at the bottom and
sheet-dominated at the top** (a single sheet mesh all the way down is the classic wet-ribbon
look), and the mist plume is a **lit participating medium**, not a billboard disc — it is the
element that grounds the fall in the scene, because it scatters sunlight and shadows the rock
behind it. The recurring structural defect remains the one in
[Rivers](#rivers-flow-driven-surfaces): a fall authored where the flow field does not support it.

## Rivers: flow-driven surfaces

Rivers cannot use ambient synthesis — their motion is *directed*, and the direction is exactly
what the generator's flow field encodes. The core technique is **flow mapping** (Vlachos, Portal
2): advect the surface detail UVs along the flow vector, and hide the inevitable UV stretch by
crossfading two phase-offset samples:

```hlsl
float2 flow   = DecodeFlow(FlowField.Sample(s, uv));      // m/s, world-aligned, from the generator
float  phase0 = frac(t / period);
float  phase1 = frac(t / period + 0.5);
float3 n0 = SampleDetailNormal(uv - flow * phase0 * advectScale);
float3 n1 = SampleDetailNormal(uv - flow * phase1 * advectScale);
float  w0 = 1 - abs(2 * phase0 - 1);      // 0 exactly when sample 0's UVs snap back
float3 n  = normalize(lerp(n1, n0, w0));  // each layer hidden at its own reset
```

Each sample's UVs periodically snap back to their origin; the triangle-wave blend guarantees a
sample has zero weight at its snap. The visible failure mode is **pulsing** — the surface appears
to breathe at `period` — worst where flow is fast and `advectScale·|flow|·period` approaches the
detail texture's feature size; shorten the period or scale advection down in fast reaches. Add a
per-pixel phase offset (noise) to break the global synchrony of the pulse.

Build the rest of the river surface from the same field: **flow-aligned foam** (advect a foam
texture the same way, masked by the generator's constriction/gradient masks — rapids foam where
the *cause* data says rapids exist), **speed-driven detail** (blend calm→rippled→turbulent normal
sets by `|flow|`), and small downstream normal-map scrolling as the cheapest baseline motion.

**River geometry** is either spline-swept ribbon meshes (the production default: explicit width,
banks, and UVs parameterized along-flow — best when the generator exports river centerlines) or
water quads carried in the terrain tiles (simpler, follows `06` streaming for free, but along-flow
UVs must be derived from the flow field). Ribbons LOD by spline subdivision against the same SSE
currency; their far LOD must not drop below the terrain tile's ability to hold the riverbed
silhouette, or distant rivers detach from their valleys.

**Waterfalls** are constructs, not surfaces: at a knickpoint (the generator marks these — its
`04`), the flow field ends on one level and resumes below. The renderer assembles a fall from a
mesh sheet (scrolling normals + foam, UV-parameterized top-to-bottom), particle spray at base and
lip, and a foam/mist pool disc — all *steered* by the exported discharge and drop height. None of
this is in the export; all of it is driven by it. The recurring defect is a waterfall authored
where the flow field doesn't support it — the river above visibly refuses to feed it. Fix the
generation graph, not the particles.

## Interactive simulation patches

Ambient synthesis and flow maps do not react to the player. Reaction comes from a **local
simulation patch**: a GPU heightfield fluid sim (pipe/virtual-pipe model or linearized
shallow-water — Kass–Miller lineage) over a small moving domain centered on the camera.

- **Domain**: a ring-buffer (toroidally addressed) grid, typically 256²–512² covering 30–100 m,
  that follows the camera in whole-texel steps (same discipline as clipmap ring updates, `01`).
  Content scrolls by offset, not copy; newly exposed texels initialize to rest + inflow from the
  flow field.
- **Injection**: characters, projectiles, and boats add impulses/displacement at their footprint
  each step. Keep injection in the sim's units (velocity or height delta), not "spawn a ripple
  sprite" — sprites don't interfere, reflect off banks, or advect with flow.
- **Coupling is one-way, by doctrine.** The sim *reads* terrain depth (banks and bed shape the
  ripples, waves reflect off shores) and *writes* surface detail (a displacement/normal overlay
  composited on top of ambient waves within a blend radius). It never modifies terrain, never
  moves the water datum, and never feeds gameplay height. Requests for the sim to erode banks or
  re-route rivers are generation-side fantasies — route them to terrain-architect.
- **Budget doctrine**: quarter-ish resolution relative to screen density, fixed timestep
  (decoupled from frame rate, accumulate-and-step) or the sim's stability constant changes with
  frame rate, explicit damping so energy dies in seconds, and clamp per-step injection so a
  physics glitch cannot detonate the surface. The whole patch should cost a fraction of a
  millisecond; it is a detail layer, not a fluid solver.
- **Edge contract**: fade the sim's contribution to zero over the outer ~15% of the domain. A
  hard edge where wakes stop existing is one of the most-reported water artifacts; the fade is
  the contract, not a cover-up, because the domain boundary is a budget decision the player must
  not see.

## Man-made water: pools, tanks and channels

A swimming pool, a fountain basin, a lock chamber, a reservoir, an irrigation canal, an industrial
tank. These bodies never arrive from the generation handoff — terrain-architect *classifies*
`bodyType` from the fill mask and flow accumulation (its `03`), and no classifier turns a gunite
shell into a lake. They arrive **authored**, exactly as the engine-native water bodies do
([Bodies are splines](#bodies-are-splines-and-the-splines-carve-the-terrain)), the enum extends
renderer-side, and nearly every default in this chapter is wrong for them — structurally, not by a
tuning margin. The contracts hold (depth field, `liquidBody` optics, pass ordering, one wave
evaluator); most of the bands gate off.

```
bodyType += pool | basin | tank | canal | reservoir     # authored; never classified
```

| Machinery | Natural body | Man-made body |
|---|---|---|
| Shore distance, foam band, wet sand | The strongest shoreline cue there is | **Degenerate** — the waterline is a hard edge on a vertical wall. Gate shoreline foam and wet sand off; a static wet band and a meniscus on wall and coping replace them |
| Shoaling, refraction, breakers, run-up | Tier 2 shore band, the production default | **Off.** No sloping bed, no surf zone. A pool with breakers is an ungated body type, not a storm |
| Whitecaps (Jacobian foam) | Wind-driven, from Force 3 up | **Off.** No fetch reaches the breaking threshold across 10 m of water |
| Ambient wind-wave spectrum | Fetch-limited wind sea, or full swell | Fetch is *metres*, so the wind-driven part collapses onto the capillary–gravity floor ([Calm water](#calm-water-the-low-energy-regime)) — the **smallest** term on a sheltered pool, not the model |
| Wave sources | Wind, swell, current | **The return jets, then the walls** — a driven, reverberant basin response, not a spectrum: [The wave field is a driven basin](#the-wave-field-is-a-driven-basin-not-a-spectrum) |
| Sim-patch edge contract | Fade to zero over the outer ~15% | **Inverted** — the domain edge is a real wall. Reflect it, and keep the fade only where a sim domain ends inside a larger body |
| Depth ramp | The single strongest realism cue water has | 1–3 m of range, almost no dynamic range to spend. What reads instead is the wall/floor junction and the refracted straight-line grid |
| Reflection | Planar is a hero-body-only luxury | One small flat body: **planar reflection is genuinely affordable**, and SSR behaves unusually well because the reflected geometry is close and on screen |
| Caustics | A detail on the bed | **The dominant visual event** |
| Single-depth-layer limit | A real architectural constraint | A non-issue — one surface, nothing stacked |

The net effect is an inverted budget. On an ocean you spend on the surface and economize on the
bottom; on a pool you spend on the bottom — caustics, bed albedo, refraction fidelity — and the
surface is a nearly flat sheet with ripples on it.

### The wave field is a driven basin, not a spectrum

A directional wind spectrum on a sheltered pool is plausible and wrong in a way a photograph
exposes immediately. Pool water is organised by the plumbing and the walls. "**Driven basin**" is
this chapter's phrase for that, not a term of art (`?`); the construction under it is standard room
acoustics, and the physics is the ordinary capillary–gravity kind.

- **The source is the filtration return; the walls send it all back.** The inlet jets inject a
  narrow band of gravity waves — order 10–30 cm — continuously from a fixed point whenever the pump
  runs, with swimmer transients on top; wind over metres of fetch is the smallest contributor. A
  tiled wall is a near-total reflector at these wavelengths — argued from the physics, with no
  reflection coefficient measured (`?`) — so the result is a **reverberant basin response**: the
  field is **not statistically homogeneous**, the pattern is **stationary in the basin frame** (the
  same structure sits in the same place every day), and a train can be traced from the inlet to the
  far wall and back.
- **Damping sorts the field into two bands, and forcing sorts it the same way.** Deep-water viscous
  decay `α = 2νk²` (Lamb) against the group speed gives an e-folding distance `c_g/α` of ~90 m at
  16.5 cm — eleven lengths of an 8 m pool — but only ~2.1 m at 3 cm, which dies before the far wall.
  A surface film (sunscreen, body oils) shortens the short end by roughly 3–9× again — the
  inextensible-film limit `α ≈ 0.35·k·√(νω)` against the clean-surface `2νk²`, prefactor unconfirmed
  (`P/?`), so the factor is indicative — and leaves the long end alone, because long waves stretch
  the film and see a clean surface. Wind cannot force long waves at metre-scale fetch either, so
  forcing limit and damping limit land in the same place: a pool surface is **two superposed fields,
  not one spectrum**.

| | Long band (≳10 cm) | Short band (≲5 cm) |
|---|---|---|
| Source | Return jets, swimmers — a fixed point | Wind, over the whole surface |
| Structure | Coherent, reverberant, basin-modal, stationary in the basin frame | Incoherent, statistically homogeneous |
| Reach | Rings around the basin many times | Dies in ~2 m; never reflects |
| Carries | The visible undulation, the trackable motion, and — once the film has eaten the short end — most of the slope | Sparkle and fine bed texture, on under a tenth of the slope variance |
| Local shelter | **Unaffected** — passes straight through a lee | **Strongly modulated** — this is what a lee removes |

Shading sees slope, and a single wave's slope is `2πa/λ`, so equal slope costs amplitude
proportional to wavelength: a 1.5 mm ripple at 5 cm out-slopes a 3 mm jet wave at 16.5 cm, ≈0.19
against ≈0.11. **Never budget the two bands by wave height.** Those two figures are *single-wave*
slopes at one illustrative amplitude, though, not the *band rms slope* the focusing number takes;
substituting one for the other is how an `F` nobody can reproduce gets published. The band figures,
read off the reference implementation's far field away from the jet (`reference-impl/field.py`) as
total rms slope, are `s ≈ 0.016` at `λ ≈ 3 cm` (`k ≈ 210 m⁻¹`) short and `s ≈ 0.055` at `λ ≈ 18 cm`
(`k ≈ 35 m⁻¹`) long — both **chosen inputs to that implementation, not measurements of water** (`?`),
so read them as a budget and never as evidence for themselves. Over the reference pool's 1.40 m
floor `F = 0.25·d·s·k` ([The focusing number](#the-focusing-number-which-regime-the-bed-is-in)) puts
them at `F ≈ 1.2` and `F ≈ 0.7`. Which is why the short band must not own the bed pattern: it is
*at* focus, but onto a 3 cm cell, and it holds under a tenth of the slope variance — it stipples the
bed, while the long band sits between fold onset and focus, where the soft, low-contrast net lives.

- **Shelter modulates the short band only.** In the wind shadow of a sail or a hedge the surface
  goes glassy *but keeps undulating*: the lee kills the wind band while the jet waves cross it
  untouched. Multiply a lee mask into the whole field and long waves stop dead at the shadow line,
  which no water does.

```hlsl
// Pool surface in a raster pass: two band fetches, one baked-wake fetch, one mask.
float3 nLong   = BasinNormal(uv, t);         // >=10 cm: FFT cascade (flat spread) + image trains
float3 nShort  = WindRippleNormal(uv, t);    // <=5 cm: the existing short-wave detail set
float  shelter = SampleShelter(uv);          // painted/baked lee mask; 1 = exposed, 0 = full lee

// Combine as SLOPES, not normals: slopes add, and the short band is the slope budget.
float2 sLong   = nLong.xy  / max(nLong.z,  1e-4);
float2 sShort  = nShort.xy / max(nShort.z, 1e-4);

// The wake is a bake, one fetch in the fitting's frame. .xy = slope, .z = the forcing envelope.
float3 wake    = WakeAtlas.SampleLevel(smp, WakeUV(worldPos, fitting), 0).xyz;
float3 N       = normalize(float3(-(sLong + shelter * sShort + wake.xy), 1));

// Same masks into the filtered-variance path, or distance filtering re-adds the sparkle the lee
// removed. Slope scales linearly with a mask, so variance scales with its square. mss = total s^2.
float mssShort = shelter * shelter * mssShortBase + wake.z * wake.z * mssJetBase;
```

- **A return jet, taken from the jet and not from an authored lobe.** A submerged round jet spreads
  linearly and decays as `1/s`, and cannot force the surface until it has spread far enough to reach
  it, so the disturbed patch is elongated along the aim and **starts downstream of the fitting
  rather than at it** — ~0.9 m downstream for a 20 mm restricted eyeball at ~13 m³/h set 15 cm deep,
  half-length ~0.7 m, local rms slope roughly **twice** the far field — total `0.122` against
  `0.053–0.058`, ratio **2.1–2.3**, on the reference implementation. The ratio is the claim, not the levels:
  `η ~ C·u'²/g` carries an unknown O(1) constant (`?`) and both levels inherit the chosen bands (`?`).
  Its wake is a **narrow downstream band, not rings and not a Kelvin wedge**: the drift it drives,
  of order 1 m/s (0.8 bar through that eyeball is an 11.6 m/s jet), is strongly supercritical
  against water's minimum phase speed of 0.231 m/s ([Calm
  water](#calm-water-the-low-energy-regime)), so nothing propagates upstream — a ring system needs a
  source at rest in still water — and because energy travels with the current (`c_g ≤ U/2`) the fan
  is only **±19°** about the axis. The ship case, source moving through still water, is the mirror
  image and its wedge does not transfer. Three checks a reference photograph gives free: the pattern
  is **steady** in the pool frame (one that animates outward is a wrong model), its crest arcs are
  centred a metre or so **out in the water** because the forcing region is a stretch of the axis
  rather than the outlet, and what it launches fades out around **3 m in an 8 m pool**. Forcing
  scales as `(U0·d)²`, so what you calibrate against an observed roughness contrast is the **flow
  rate through the fitting**, not a shape exponent.
- **Then it has to be *aimed*, and that is a composition decision rather than a plumbing one.** The
  wake is the one long, ordered, repeating structure in a pool frame, so its angle **in plan**
  against the camera decides whether it reads as water at all: with the axis within a few degrees of
  the camera azimuth it projects as a near-vertical stripe up the middle of the frame and reads as a
  **seam**. On the reference scene 3.4° off the camera azimuth was not obliquity and 11.9° was
  (`D`, that camera and that basin). Obliquity in plan is what turns a periodic train into a pattern
  crossing the frame; amplitude is not the control and lowering it only makes a fainter seam. The
  rule is not specific to jets — a boat wake, a swell train and a rip lane all carry it — and it is
  the layout half of the argument [Sun glitter](#sun-glitter-the-sparkle-path) makes about where a
  camera may stand: both say the frame is decided before the shader is.
- **What ships at frame rate.** Every band maps onto an evaluator this chapter already has, so
  nothing new runs in the frame. The **diffuse tail** is random-phase and isotropic — an FFT cascade
  with a flat directional spread, or a short Gerstner sum with scattered directions. The **early
  wall reflections** are the direct train plus its first-order mirror images across the walls
  (`1/√r` spreading, damping as above) — a handful of extra trains in the same sum; pushing the
  image count up instead buys a coherent lattice no basin shows and costs more. The **wind band** is
  the existing short-wave detail set. The **jet wake**, being stationary, is a bake: solve it once
  offline per fitting, store slope and forcing envelope in a small texture in the fitting's frame,
  and sample it — one fetch, no solver in the pass, and it rotates and tiles with the fitting. The
  **lee** is a painted or baked mask. A **height-field** sim patch with reflecting walls and a
  driven source cell buys swimmer transients at the usual patch cost ([Interactive simulation
  patches](#interactive-simulation-patches)); the steady field does not need it. The bed pattern
  then goes through the same caustics ladder as any other body ([The tier ladder](#the-tier-ladder))
  — the driven basin changes which band feeds it, not the technique. And the tail's near-isotropy is
  a review test in its own right: a wind sea writes streaky, direction-aligned caustics; a
  reverberant tail writes isotropic cells.

### Pool optics: the colour is the bottom, not the water

The optical identity machinery in this chapter is built from oceanography — Jerlov types,
Forel-Ule index, chlorophyll and CDOM — and **a treated pool belongs to none of those classes**.
Filtration and flocculation remove precisely the particles that scatter: `b_b → ≈ 0`, `c → a`, and
Secchi depth exceeds the body depth by design. With `b_b ≈ 0` the **scatter-colour term is
essentially zero** — a pool has no body colour of its own, and a shader that derives its colour
from `L_scatter` is structurally incapable of rendering one.

**What the treatment actually puts in, and why none of it shows.** "Treated water" is doing real
work in that sentence, and it is the first thing a sceptical reader challenges:

- **Chlorine is a UV absorber, not a visible one.** Hypochlorite peaks at **292 nm**
  (`ε ≈ 300–380 M⁻¹cm⁻¹`), hypochlorous acid at 235 nm; at a pool dose of 1–3 mg/L that is an
  absorbance of roughly **0.5–1.5 per metre in the UV** — real, and why chlorine burns off in
  sun — while by 450 nm the band has decayed far below water's own `a(450) = 0.0092 m⁻¹`. Chlorine
  does not colour pool water at any dose anyone swims in.
- **Dissolved calcium is colourless; *precipitated* calcium is not.** Ca²⁺ and carbonate absorb
  nothing visible, but past roughly pH 7.8 the calcium leaves solution as microscopic CaCO₃ that
  stays in suspension. That is **scattering**, and it is the one ordinary impurity that genuinely
  breaks `b_b ≈ 0` — the standard milky pool.
- **The two are told apart by the sign of the error, and that is the diagnostic to ship.**
  Absorption only subtracts, so it darkens and shifts hue with path length; scattering **adds** — a
  veiling glow, lifted shadows, hazed distance, and **blurred caustics**. A pool that has gone
  cloudy loses its caustic net well before it looks obviously milky.
- **Which means a photograph measures its own scattering.** A crisp caustic net at 1.40 m bounds
  `b_b` directly: the net's blur is already accounted for by the sun-disc penumbra (6.8 mm at that
  depth and that sun), so anything scattering appreciably more than that would show as a softer
  net. Read off the artefact rather than assumed — no numeric bound was extracted this way (`?`).
- **Two impurities that *would* recolour the water, so the exception is bounded:** dissolved
  **copper**, from an algaecide or a corroding heat exchanger, which really does tint water
  blue-green, and **CDOM** from leaf litter, which absorbs blue and pushes it yellow-green. Both
  are absorbers, so both fit the machinery already here — they change `a`, never `b`.

The colour is **bottom albedo attenuated over the down-and-back path**. For a near-vertical view of
a 1.5 m floor the light crosses ~3.0 m of water, and pure-water absorption at this chapter's RGB
sample points ([Water-body optical
identity](#water-body-optical-identity-where-the-iops-come-from)) does the rest:

```
depth 1.5 m -> round trip 3.0 m,  transmittance = exp(-a * 3.0)
  a(610 nm) = 0.2644 m^-1  ->  0.45    red     more than halved
  a(550 nm) = 0.0565 m^-1  ->  0.84    green   barely touched
  a(450 nm) = 0.0092 m^-1  ->  0.97    blue    untouched
```

A white liner at ~0.8 albedo therefore returns roughly `(0.36, 0.68, 0.78)` before any sky
reflection is composited on top: bright, cyan-leaning, and **desaturated** — because with `b_b ≈ 0`
the column is a pure Beer-Lambert filter that can only subtract. The deeply saturated turquoise
most people picture comes from a **blue liner**: a mid-blue PVC at roughly `(0.24, 0.54, 0.70)`
returns about `(0.11, 0.46, 0.68)`, far more saturated and about a third darker. Start a modern
domestic pool from a blue liner, not white plaster, and let the water *darken* it rather than
colour it; reaching for a saturation or tint control instead is compensating for a bottom albedo
that was never authored. Two consequences, both checkable against reference photography: **change
the liner and the water changes completely** (sand → green-teal, the fashionable dark-grey liner →
near-black, since nothing fills the column and only the Fresnel sky survives — a pool that looks
the same over every liner has no bottom-albedo term), and **colour is nearly depth-independent
within one pool**, since across 1–3 m blue hardly moves, green moves little, and red carries almost
all of the change. A strong hue shift across a pool floor is an artifact, not a depth cue.

### The two materials a pool actually has, and neither is "water"

A pool is a **boundary** and a **medium**, and a renderer needs both stated. The medium is the
`a`/`b`/`g` this chapter already demands from
[`liquidBody`](#water-body-optical-identity-where-the-iops-come-from); in treated water it
is pure water and nothing else, so it is not a choice — the same three inherent optical properties
under the [vocabulary rule](#the-vocabulary-and-which-half-of-it-you-can-look-up), never a tint. **The boundary is the choice, and it is the
one that decides what the pool looks like** — because with `b_b ≈ 0` the water can only subtract,
so every photon that reaches the eye from below has been off the liner.

So the contract is two lines, and the second is the interesting one:

    medium : a(lambda), b(lambda), g                        # IOPs -- pure water, for a treated pool
    liner  : base_color, base_weight, specular_roughness    # the boundary -- albedo, and wet vs dry

**Liner albedo is not proportional to what you see, and that surprises people.** Light that returns
from the liner meets the underside of the surface, where the diffuse **internal** reflectance
`R_int = 0.47617` sends about half of it back down for another bounce — the *trap* sense of
"surface reflection", 7.14× the 6.669% loss the same surface applies on the way in, and the two are
told apart in [their own section](#surface-reflection-names-two-opposite-things-a-loss-and-a-trap). That trapped series — the
ordinary geometric interreflection sum, under a name that is this chapter's own — is
`1/(1 − ρ·R_int)`, so its *gain* rises with the albedo — and a dark liner therefore loses twice,
once on each return and again on the bounces it never gets:

⚠️ **The gain column below is `1/(1 − ρ·R_int)`, which is the trap with the column's absorption
removed — an upper bound and not the gain of any particular pool.** It is the right object for the
argument being made here (a dark liner loses twice, and the mechanism is depth-free); it is the
wrong object for pricing a basin, because the returned light crosses the water twice and
`G_rt(a·d) ≤ R_int` with equality only at `τ = 0`. On this chapter's own 1.40 m the bound overstates
by 24.7% in red at ρ = 0.50. Priced, drawn and cross-checked in [figure
12·3](#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point).

| Liner | ρ (green) | Trapped gain, `τ = 0` | Apparent | Against white |
|---|---|---|---|---|
| White | 0.80 | **1.61×** | 1.21 | 1.00 |
| Light blue | 0.65 | 1.45× | 0.88 | 0.73 |
| Sand / beige | 0.55 | 1.35× | 0.70 | 0.58 |
| Mid blue *(this chapter's default)* | 0.50 | 1.31× | 0.61 | 0.51 |
| Dark grey | 0.15 | 1.08× | 0.15 | 0.13 |
| Anthracite / black | 0.05 | 1.02× | 0.05 | **0.04** |

A black liner returns **4%** of what a white one does where its albedo is 6% of it (`D`). That is
why an anthracite pool reads almost as a mirror — with nothing coming back from below, the
**external** reflection `R_ext` is all that is left (6.669% diffuse, 2.06% at normal incidence and
rising steeply toward grazing), and the body goes near-black. It is also why the same water, the
same sun and the same depth can look like the Caribbean or like a slate tank: **you are choosing
the pool's colour when you choose its lining, not when you tint its water.**

Two consequences for how a scene is authored:

- **Tinting the medium to get a colour is the error this section exists to prevent.** It produces
  water that stays coloured in a shadow, does not deepen with depth, and cannot be made pale by a
  white bottom — three things a photograph refutes immediately.
- **Wet is not dry.** The liner above the waterline and the same liner below it are one pigment,
  but the wet one reads `(0.85, 0.79, 0.82)` of the dry (`D`), because the water film adds an
  internal reflection — `R_int` again, the trap sense — that the dry surface does not have. That makes the dry band a **free calibration
  target**: it is the pigment with no water path, no interface and no `n²` between it and the eye,
  so it pins `rho` on its own — and the ratio between it and the submerged bed then pins the
  absorption path. Two measurements from one photograph, and neither needs a reference chart. That
  last step assumes one pigment above and below, which is true of a liner on the day it was fitted
  and of no other day: [A liner in service is an albedo
  field](#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate).

### Saying it in OpenPBR, and where the mapping stops

The two-material contract above is not this chapter's invention — it is what a standard surface
model already asks for, so state it in those terms and a reader can author it in a DCC tool without
translating. In **OpenPBR Surface** the medium's absorption is carried by a transmission depth and
colour that *are* Beer–Lambert: `transmission_depth` `λ_T` is the distance at which white light
becomes exactly `transmission_color` `T`, so

    a(lambda) = -ln(T) / lambda_T          and        T = exp(-a * lambda_T)

This chapter's pool, written out (`D`, from `a = (0.2617, 0.05299, 0.01022) m⁻¹`):

    base_color            (0.24, 0.54, 0.70)     # the liner -- the choice that sets the colour
    base_weight           1.0
    specular_ior          1.333                  # water; never the generic dielectric 1.5
    transmission_depth    1.0                    # metres; the scale is free, T follows
    transmission_color    (0.770, 0.948, 0.990)  # ... or (0.351, 0.809, 0.960) at depth 4.0
    transmission_scatter  (0, 0, 0)              # b ~ 0 in treated water
    transmission_scatter_anisotropy  g           # only once the water is not treated

Note what that makes visible: **`transmission_scatter` is the turbidity axis** — it is `b`, with
`transmission_scatter_anisotropy` carrying `g` — and setting it non-zero is the same act as leaving
Case 1 water: it is where a pool becomes a lake.

**There is no `waterColor` in that list, and the absence is the doctrine.** A parameter with that
name invites precisely the error the section above exists to prevent, because a colour multiplied
into a medium is not a distance and knows nothing about one: it gives water that stays coloured in
shadow, does not deepen with depth, and cannot be made pale by a white bottom. The transmission
*pair* cannot express that mistake — `transmission_color` means nothing without
`transmission_depth`, which is the entire reason it is written as two values and not one swatch.

**Where the mapping stops, and it stops early.** A standard surface model describes *one material
with a homogeneous interior bounded by its own surface* — MaterialX draws the same picture from the
other end, layering a transmissive BSDF over a volume distribution function whose own documented
example is "colored glass or turbid water" (`P`). A body of water is not that. It is a **medium
bounded by two different materials** — the wave surface above and the liner below — and several of
this chapter's central problems live in the gap:

- **The bed is not the material's own back face.** Its depth varies, and the medium's path length is
  a field over the surface, not a thickness of the object.
- **Caustics are transport, not material.** No surface parameter produces them; they are the
  Jacobian of a refracted ray map ([tier ladder](#the-tier-ladder)), and a rasteriser has to build
  them as a pass whatever its material model says.
- **The trapped series is geometry.** A path tracer recovers `1/(1 − ρ·R_int)` by bouncing; a
  surface model with a single transmission event does not, and a fullscreen-triangle pass must carry
  it explicitly or a white-bottomed pool comes out 60% dark.
- **The camera may be inside the medium.** Every standard surface model assumes it is outside
  looking in. [Snell's window and the split shot](#the-view-from-inside-and-the-split-shot) are not
  material states at all.

So: take the *material* half from OpenPBR and let it be authored the way everything else in the
scene is; keep the *transport* half here. The division is exactly this chapter's tier ladders — and
a project that expects its material model to deliver the second half will discover the shortfall at
the point where the water starts to matter.

### The vocabulary, and which half of it you can look up

That division is also the naming rule, and this chapter takes **both** halves from existing
standards rather than coining a house style. The point of borrowing a vocabulary is that a reader
can look a term up; a coined name that merely *looks* borrowed defeats it, and sends someone
hunting through a material browser for a quantity that was never going to be there.

- **The interface is OpenPBR** (`P`): `base_color`, `base_weight`, `specular_ior`,
  `specular_roughness`, `transmission_color`, `transmission_depth`, `transmission_scatter`,
  `transmission_scatter_anisotropy`. A name from that list means what OpenPBR says it means and is
  authorable in a material editor.
- **The medium is IOPs** — ocean optics' *inherent* optical properties, so called because they
  belong to the water alone and not to the light falling on it: absorption `a`, scattering `b`,
  backscattering `b_b`, beam attenuation `c = a + b`, and the phase function with its asymmetry
  `g`, the coefficients in m⁻¹. These are measurable, they are what the literature tabulates, and
  they are what [Water-body optical
  identity](#water-body-optical-identity-where-the-iops-come-from) spends its length on.
- **What a renderer computes from them are AOPs** — *apparent* optical properties, which depend on
  the medium **and** on the illumination geometry: diffuse attenuation `K_d`, reflectance, the
  radiance a column returns. An IOP can be authored; an AOP is a result, and authoring one directly
  is the same category error as `waterColor`.

The IOP/AOP split is Preisendorfer's and is the standard division in the field (`P`) — the same
material/transport line, drawn decades before anyone was rendering water by people who were
measuring it. So no house prefix and no invented parameter names are needed anywhere:
**OpenPBR names the boundary, IOPs name the medium, AOPs name what comes back, and everything left
over is a pass.**

**Three terms in this chapter are its own coinage, and are labelled so you do not go looking for
them.** A coinage that reads like a standard is worse than one that admits it:

| Term | Status |
|---|---|
| **Focusing number** `F = 0.25·d·s·k` | **Ours.** Every ingredient is standard — ray deflection, the Jacobian, catastrophe theory's folds and cusps — but the dimensionless group and its four rungs are assembled here, and no established name for it was found (`?`). Useful enough to keep; never cite it as literature |
| **Driven basin**, for pool waves as a forced reverberant response rather than a spectrum | **Ours.** The construction is carried over from room acoustics, where early-reflections-plus-diffuse-tail is standard practice; the phrase is not a term of art in water rendering (`?`) |
| **Trapped series**, for the interreflection sum `1/(1 − ρ·R_int)` | **Ours** as a *name* only. The sum is the ordinary geometric interreflection series and `R_int ≈ 0.476` is a standard internal-reflectance figure |

Everything else that reads like jargon is standard, and knowing the field it comes from is what
lets you check it. **Radiance, irradiance and radiant intensity** are SI radiometry and are used
here *exactly*: the `1/n²` factors in the caustic budget, on [the transmitted
column](#radiance-is-not-conserved-across-the-interface) and in
[Underwater, a load-time constant is two
constants](#underwater-a-load-time-constant-is-two-constants) are radiance-conservation
bookkeeping and nothing else, and a renderer that treats radiance as a synonym for brightness drops
them silently. **Form factor** is standard radiative-transfer too, and is used here exactly. **BSDF/BRDF/BTDF**, **Fresnel reflectance and transmittance**, the **critical angle**
and **Snell's window** are optics; **mean square slope** is Cox & Munk's own term; **capillary
length** and **Young–Laplace** are surface physics; **eikonal**, **Hamiltonian** and **wave action**
are wave mechanics; **optical depth**, **single-scattering albedo**, **Secchi depth**, **Jerlov
type** and **Case 1 / Case 2 water** are ocean optics. **Turbidity** is standard as well — as a
*water-quality* measure in NTU — which is exactly why it is the wrong shader parameter: one
nephelometric scalar cannot carry two independent axes, and the pitfall list has two entries about
what happens when it is asked to.

A third kind of name appears in the [UE Water plugin
section](#engine-native-water-the-ue-water-plugin-read-as-architecture) — `Water Zone`, `Water Info
Texture`, `Single Layer Water`, `PhaseG`, `Tile Size`, `N Points Per Frame`. **Those are Epic's
names for Epic's things**, quoted verbatim so the section can be checked against the documentation,
and deliberately not translated. The same holds for `liquidBody[i]` and its fields, which are
terrain-architect's export names, not this chapter's.

### A liner in service is an albedo field, and the waterline is its coordinate

The contract above gives the liner one `base_color`. That is right for the day it was fitted and
wrong for every day after it, and the project owner's ruling on this is a statement about the
*class* rather than about one pool: *"We moeten rekening houden met dat niet ieder zwembad net
aangelegd is en kalk aantasting of andere bleking heeft ondergaan"* — not every pool is newly laid,
and the ones that are not have taken scale attack or some other bleaching. A perfectly uniform liner
reads as CG immediately, and the tell is always in the same place.

Nothing here needs new vocabulary, which is the point of putting it directly after
[the vocabulary rule](#the-vocabulary-and-which-half-of-it-you-can-look-up). A weathering field is
`base_color` as a function of position — that is what a texture is — and the mechanisms under it are
ordinary chemistry. The only thing that is not obvious is the **organising coordinate**, and it is
not the one an author reaches for.

```
h(x) = x.z - z_water          # signed height above the free surface, metres
```

Everything below keys off `h`. World height is wrong, because a pool with a step, a bench or a
sloping floor has one waterline and many bed elevations. A painted texture is wrong, because
`z_water` moves — a pool being drained or filled, a tank whose level is gameplay state — and the
profile has to move with it.

**It decomposes, and the two kinds of weathering do not compose the same way.**

```
rho(x) = lerp( lerp( rho_0 * w(h) * m(x),  rho_scale, c(h) ),  rho_bio, m_dep(x) )

  rho_0       pristine liner albedo -- the base_color of the two-material contract, per channel
  w(h)        MODIFICATION of the pigment in place: UV bleach, oxidative attack. MULTIPLIES.
  m(x)        the same, geometry-selective: abrasion on treads and nosings. NOT a function of h.
  c(h)        COVERAGE by a layer deposited on top: carbonate scale and the oils bound into it. LERPS.
  m_dep(x)    the same, geometry-selective: biofilm in dead corners and shade. NOT a function of h.
  rho_scale   the deposit's OWN albedo and spectrum -- pale, near-neutral, nothing to do with rho_0
  rho_bio     the other deposit's own -- dark and green-shifted, and it is why one lerp is not enough

  Nesting order is DEPOSITION order: biofilm settles onto scale, not the other way round.
```

That distinction is load-bearing and it is the one most often collapsed into a single multiply. A
modification can only scale the pigment already there; a deposit *replaces* it over a coverage
fraction and brings its own albedo, its own hue and its own roughness. **A multiplicative weathering
mask can never draw a dark liner's tide line**, because white is not a multiple of dark blue — so the
highest-contrast feature on an aged pool is precisely the one a multiply-only pipeline is
structurally unable to produce.

| Zone | Band | Mechanism | Kind | ρ | Hue | Clock |
|---|---|---|---|---|---|---|
| **Dry band / freeboard** | above the splash reach, up to the bead track | **UV photodegradation** of pigment and plasticiser. No water column over it, so it takes the highest solar UV dose of any part of the liner, and it dries between wettings | modification | **↑ lightens**, and chalking raises roughness with it | desaturates toward the pale substrate; on a blue liner red rises fastest because it started lowest | slow, monotone, years (`?`) |
| | | *and* airborne soil, pollen and dust settle on the same band | deposit | ↓ | site-dependent | — |
| **Tide line** | a *narrow* band on the **long-term mean** level, order 1–5 cm (`?`) | **Carbonate scale**: evaporation concentrates the surface microlayer exactly at the line, and CaCO₃ leaves solution past the saturation index onto the strip that is wetted and dried over and over. Plus **body oils, sunscreen and dust** bound into it | **deposit** | **↑↑ strongly, over a narrow band** — the highest-contrast feature on an aged liner, and the reason it reads as a *line* rather than a gradient | near-neutral white where scale dominates, grey-brown where the organic film does. Two deposits, two colours, one band | months; removed in an afternoon with acid |
| **Splash zone** | just above and below, order ±10 cm | repeated wetting and drying: partial scale, and the **optical** wet-film darkening in the same place | both — *and one of them is not weathering at all* | ↑ material, ↓ optical | — | the optical half is instantaneous and closed form ([`12a`](12a-water-derivations.md#the-companion-why-a-wet-band-is-darker-with-no-free-parameter)); the material half is permanent |
| **Submerged wall and bed** | `h < 0`, graded with depth | **Oxidative attack by free chlorine** on the pigment, running continuously for as long as the pool is sanitised, plus the UV that survives the column — UV-B is stripped in the top decimetres and UV-A goes further, so the photolytic dose falls with depth | modification | **↑ lightens, graded, strongest just under the line** | toward the substrate, as the dry band | dose-like in concentration × time (`?`) |
| **Corners, coves, behind ladders, shaded runs, the lee of steps** | **not** a function of `h` | **Biofilm and algae**, where circulation is dead and the sanitiser residual is lowest. Corners are dead precisely *because* the return jets sweep the open water ([driven basin](#the-wave-field-is-a-driven-basin-not-a-spectrum)) | deposit | **↓↓ darkens** — the counterexample | green to blue-black: pulls red hardest, blue next, green least | days to establish, hours to kill |
| **Treads, step nosings, the shallow end, the entry** | geometry-selective, `h`-adjacent | **Abrasion** — feet, brushes, the vacuum head | modification | ↑ on a pigmented liner: the top layer goes first | little hue change | use-driven; roughness is usually the more reliable cue than albedo (`?`) |

**Say which way each one goes, because a reader who assumes weathering bleaches will get the corners
backwards** — and the corners are what sells the picture. An old pool is *pale in the middle and dark
in its corners at the same time*, and a mask that only lightens produces a pool that has been left
in the sun rather than one that has been swum in.

**The mechanisms do not move together, so age is not a scalar.** A pool that was acid-washed last
spring has no tide line at all and a fully bleached submerged wall. A brand-new pool with a failed
chlorinator has algae in the corners, no tide line, and pristine albedo everywhere else. A new pool
filled with hard water and run at pH 8.2 grows a tide line within a season and nothing else. **One
"age" slider produces combinations no pool has**, and a wrong combination is more visible than no
weathering, because each zone runs on its own clock and a viewer has seen all of them.

**Inference rules, from the picture back to the mechanism.** Each is also a constraint on what a
profile is *allowed* to claim:

```
R1  narrow, high-contrast, centred on the mean level, lighter than its surroundings
        -> DEPOSIT.  A pigment change cannot be that narrow; no dose gradient has that edge.
R2  graded monotonically in |h| below the line, no edge anywhere in it
        -> DOSE-LIMITED MODIFICATION (oxidant or UV). Not a deposit.
R3  geometry-selective, darkening, green-shifted, indifferent to h
        -> BIOFILM.  Key it to circulation and shade, never to height.
R4  present on every wall regardless of aspect
        -> MATERIAL, not shading.  Orientation-independence is what rules a lighting explanation
           out, and it is the entire content of the reference observer's "rondom donkerder".
R5  the SIGN of the change differs above and below the line
        -> TWO mechanisms, therefore two profiles.  One mask with a sign flip inside it is a
           curve fit; two mechanisms on two clocks is a model.
R6  a deposit reads the same colour above the line and on the bed
        -> TRANSPORT MISSING, not material.  Same carbonate, different path length: next section.
```

**And the numbers are deliberately not here.** Deposition rates, bleaching rates, the albedo and
spectrum of pool scale, the albedo of a two-year-old liner against a new one — none of these were
measured in this run or chased to a source, and every one of them is marked `?` in
[`12b`](12b-water-provenance.md). That is the more useful state to leave them in: a reader handed a
figure stops measuring, and a reader handed a marked gap goes and swabs the wall. What is durable
here is the **set of zones, the mechanism in each, and the sign** — and the signs are checkable
against a photograph of any pool that has been in service.

### Where a weathering profile is allowed to come from, and what the water does to it

**Light transport is derived; material parameters are stated.** Given geometry, an illuminant and
materials, every radiance in the frame follows and nothing in it is free — that is what the tier
ladders in this chapter are ladders *of*. Material parameters are the other kind: inputs, from
outside the render, that no amount of transport work will produce. [OpenPBR draws exactly this
line](#saying-it-in-openpbr-and-where-the-mapping-stops) — the BSDF is physics the renderer
evaluates, `base_color` is a number the author supplies, and the specification has nothing whatever
to say about where that number came from.

A weathering profile is on the stated side. It is therefore legitimate input on exactly the terms any
material parameter is: **it came from a measurement of the surface, or from a stated typical value
with its source named and its uncertainty carried.** It becomes illegitimate the moment it is
adjusted until the picture is right — not because the mechanism is fake, but because at that point it
has stopped being a statement about the pool and become a residual wearing a physical name, and a
residual absorbs whatever error is nearest to hand, including the errors that belong to the
transport.

**The test is one question:** *would you have written the same profile if you had never seen the
render?* Three things follow, and they are what make the question usable rather than rhetorical:

- A profile from a measurement passes by construction, because the measurement predates the render.
- A profile from a typical value passes **only while the value stays typical**. Nudging it off the
  published figure to close a gap fails, and its having started as a citation does not launder it —
  a cited number moved by 30% is an uncited number with a footnote.
- Enforceability is procedural: **write the profile down, freeze it, then render**, and report the
  resulting ordering as an *output*. A material split only measures something for as long as it is
  reported rather than fitted; the moment it is fitted the render stops being an instrument.

**Weathering is dangerous specifically because it is real.** A tint has no argument behind it and is
easy to refuse. Every mechanism in the table above is genuine chemistry, so a weathering term arrives
with an excuse ready for any value it is given — and, uniquely, for values in *either direction*,
since the zone table supplies both lightening and darkening. A parameter that can be argued for both
ways is the one to watch, and it is the one whose justification has to be written before its value is
chosen.

**What the water then does to it is not a constant.** The bed's apparent brightness under the
[trapped series](#the-two-materials-a-pool-actually-has-and-neither-is-water) is

```
A(rho) = rho / (1 - rho * R_int)          # radiance factor AT the bed, per unit irradiance there
G(rho) = 1   / (1 - rho * R_int)          # the trap gain

dlnA/dlnrho = 1 + rho*R_int/(1 - rho*R_int) = 1/(1 - rho*R_int) = G(rho)      # exact
```

**The elasticity of apparent brightness with respect to albedo is the trap gain itself.** A 1% change
in liner albedo is a `G`% change in what the picture shows — and `G` is not a constant, it is a
function of the very quantity being changed. At the diffuse constant `R_int = 0.47617` (green;
this is the `τ → 0` limit, which matters below):

| ρ_bed | trap gain `G` | apparent `A = ρ·G` | elasticity `dlnA/dlnρ` |
|---|---|---|---|
| 0.40 | 1.23528 | 0.49411 | 1.235 |
| 0.51 | 1.32074 | 0.67358 | 1.321 |
| 0.60 | 1.39998 | 0.83999 | 1.400 |
| 0.70 | 1.49997 | 1.04998 | 1.500 |

(`D`, recomputed here; all four rows reproduce to the digits printed.) Between the first two rows,
**+27.5% in albedo comes out as +36.3% in apparent brightness** — a finite-step amplification of
1.321, which sits between `G(0.40)` and `G(0.51)` as it must. `A` passing 1 at high albedo is not an
error to clamp: it is a radiance factor at the bed relative to the irradiance delivered *there*, and
the trapped series legitimately returns more than one bounce's worth to the bed. What escapes is `A`
with the escape leg on it, which is where `1 − R_int` and the [`1/n²`](#radiance-is-not-conserved-across-the-interface) live.

**But `R_int` is the wrong constant for a bed at depth — it is an upper bound, and a chromatic one.**
The reflectance that closes the series for a *submerged* bed is not the diffuse **internal** constant
but the round-trip return `G_rt(τ)` of [Attenuation and escape do not
factorise](#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them): the
light must cross the column **twice** before it is back on the bed, so the denominator is
`1 − ρ·G_rt(τ)`, and `G_rt → R_int` only as `τ → 0`. On this chapter's own pool
(`τ = a·d = 0.3664 / 0.0742 / 0.0143` at 1.40 m, `G_rt = 0.0965 / 0.3277 / 0.4445`):

| ρ_bed | gain, red | gain, green | gain, blue |
|---|---|---|---|
| 0.40 | 1.0401 | 1.1509 | 1.2162 |
| 0.51 | 1.0518 | 1.2007 | 1.2932 |
| 0.60 | 1.0615 | 1.2447 | 1.3637 |
| 0.70 | 1.0724 | 1.2977 | 1.4517 |

(`D`, recomputed here from this chapter's own `G_rt`.) **Red barely traps at all** — 1.07 at ρ = 0.70
against the 1.50 the diffuse constant promises — because a red photon sent back down mostly does not
return. So the amplification is real and monotone in albedo, but on a 1.40 m pool it runs **1.04–1.45
across the channels**, not the 1.24–1.50 of the `τ → 0` table. Use the diffuse constants as a bound
and `G_rt` for a body that has depth.

**The consequence runs two ways at once, on two different quantities.** Take a mask authored on a dry
sample — a swatch, a material-editor preview, a photograph of the liner out of the water — and put
the same material under 1.40 m of pool:

- **Contrast is amplified, by exactly the gain** — `G` above, taken with `G_rt` for a bed at depth.
  The ratio between two weathered patches is `A(ρ₂)/A(ρ₁)`, and every constant on the exit path
  cancels out of it. A 10% albedo step on the swatch is a **10.4–14.5%** radiance step on this
  pool's bed, the low end in red and the high end in blue over a pale liner.
- **Level is attenuated, by exactly the round trip, per channel.** At 1.40 m the round trip is 2.80 m
  and `exp(−a·2.80)` on the reference implementation's band means is **0.4806 / 0.8621 / 0.9718**
  (`D`). The same mask therefore lands *fainter in absolute radiance and higher in contrast* than it
  was authored — a combination nobody tunes their way out of by eye.
- **A neutral change does not stay neutral.** Because that transmittance is 0.48 in red against 0.97
  in blue, a **colour-neutral** weathering step on the bed reaches the eye with roughly **half the red
  swing it has in blue** (ratio 0.494). So the tide line and the scale on the floor can be the same
  carbonate and must *not* be the same colour in the frame: above the line the deposit reads as
  itself, on the bed it reads cyan-shifted. That is R6, and it is a review test — if scale above and
  below the waterline comes out the same colour, what is missing is transport, not material.

**Which is why a weathering mask cannot be tuned against the final image.** Anyone doing it is
inverting `A = ρ/(1 − ρ·G_rt)` by eye, through a gain that depends on the value being solved for,
separately per channel, composited under a Fresnel sky share that varies across the frame with view
angle. Whatever comes out of that is not a material statement, which puts it straight back on the
test above. **Author the profile in albedo space against the material; read the picture to check it,
never to set it.**

**Driving it at runtime, and the whole of it is one line: there are two `z_water`.**

```hlsl
// Waterline weathering: one 1-D LUT in h, one two-channel stamp in the body's frame.
// Every constant below is a STATED input. None of them is a place to close a residual,
// and RHO_SCALE / RHO_BIOFILM are marked `?` in 12b because nobody measured them here.
float  hDatum = worldPos.z - WaterDatumZ(bodyId);          // liquidBody[i].waterSurface -- the MEAN level
float  hInst  = worldPos.z - WaterSurfaceZ(worldPos.xy);   // the displaced surface, this frame

float4 prof   = WaterlineLUT.SampleLevel(smpClamp, ProfileU(hDatum), 0);   // .rgb = w(h), .a = c(h)
float2 stamp  = WeatherStamp.SampleLevel(smpBody, BodyUV(worldPos), 0).rg; // .r = m(x)     wear
                                                                          // .g = m_dep(x) biofilm cover

float3 base   = rho0 * prof.rgb * stamp.r;                 // pigment modification -- MULTIPLIES
       base   = lerp(base, RHO_SCALE,   prof.a);           // scale + oils  -- COVERS, own albedo, PALE
       base   = lerp(base, RHO_BIOFILM, stamp.g);          // algae         -- COVERS, own albedo, DARK
float  rough  = lerp(rough0, ROUGH_DEPOSIT, max(prof.a, stamp.g));   // both deposits are rougher

// The wet film is OPTICAL and instantaneous, in the same place and on the other clock.
base          = lerp(base, WetAlbedo(base), WetFraction(hInst));   // a_wet, closed form, 12a
```

- **The tide line uses the datum; the wet band uses the instantaneous surface.** A deposit laid down
  over months sits at the *mean* level and must not wobble with 3 mm of ripple; the water film does
  wobble, because it is water. One `z` each. A pipeline carrying only one of them has either a tide
  line that breathes or a wet band that is frozen, and both are immediately visible.
- **`h` comes from the field everything else reads** — `liquidBody[i].waterSurface` from
  [the handoff](#the-handoff-seen-from-the-render-side), or the [Water Info
  Texture](#the-water-info-texture-fuse-the-handoff-into-one-sampleable-field) where the architecture
  is that shape. Never a second copy of the level: a drained pool with its tide line still at the old
  height is the tell, and a texture baked at a fixed level guarantees it.
- **Never into RVT/VT pages.** The profile is a function of a time-varying global, so it composes
  *over* the resolved base material — `13`'s [state-layer
  doctrine](13-snow-weather-surface-state.md#static-says-possible-runtime-says-current), and the same
  rule that keeps snow amount out of page generation keeps water level out. Draining a pool must not
  dirty the cache.
- **It is one-dimensional, so it is a 1-D texture — and the parameterisation is the whole cost.**
  Only the geometry-selective term needs a 2-D map, and being stationary in the basin that is a bake
  in the body's frame exactly like the [jet
  wake](#the-wave-field-is-a-driven-basin-not-a-spectrum). But a *linear* 1-D LUT over ±2 m at 256
  texels is 15.6 mm per texel against a tide line 10–50 mm wide (`?`) — the highest-contrast feature
  in the frame landing on one to three texels. Spend texels where the derivative is: an `asinh`-like
  or piecewise `ProfileU(h)` with most of its range inside ±10 cm.
- **It writes `base_color` and `specular_roughness`, and nothing else.** In particular it must not
  touch `transmission_color` or `transmission_depth`: those are the medium, and the medium does not
  weather. Reaching for them to make an old pool look tired is modelling a carbonate deposit as a
  change in the water — the `waterColor` category error arriving through a new door.

**What this does to the open finding this project is currently stuck on.** Its bar records it in
sections J and K: the reference pool's submerged wall reads *lighter* than its dry band, on every
side, and two waves of derived transport failed to produce that ordering. The render stalls at a
wall:band ratio of 0.513 where the observation requires greater than 1, which prices the albedo ratio
submerged:dry at **≥ 1.95** and, since albedo cannot exceed 1, constrains *both* sides at once.

Weathering makes that ordering **reachable as a material fact rather than an optical one**, and it
gets there through the rules above rather than by assumption: a sign difference across the line is
R5 (chlorine attack below, a dry band whose pigment is intact or soiled above), and the
orientation-independence the observer reports — *"de rand is rondom donkerder"* — is R4, which is what
removes the shading explanation.

**It is a hypothesis under test in that project, not a settled result, and this section is not a
licence for it.** Three reasons it is not yet earned, and the first is the one that matters:

1. **The cheaper explanation has not been eliminated.** A dry band that is simply over-*lit*
   reproduces both orderings with no material difference at all. The instrument that separates them —
   band against water, in scene-linear, a within-frame pair close enough in level to survive every
   camera failure that bar catalogues — has not been read.
2. **The profile has no measurement behind it.** K's albedo table is the set of values the ordering
   *requires*: that is the inverse of a stated input, derived from the target. Under the test above it
   is a fit wearing a mechanism's name, and the mechanism being real is exactly what makes it hard to
   see as one.
3. **The required albedo ratio and the required apparent ratio are not the same number.** By the
   amplification above they differ by a per-channel gain that depends on the albedos being solved for,
   so a profile fitted against the picture is not the profile a reflectance measurement of the actual
   liner would return — and the two will disagree even in the case where the ordering comes out right.

What closes it is a measurement of the real liner above and below the line, which turns the profile
from a fit into a statement and makes the ordering an **output**. Short of that the row stays open —
and an open row that says so is worth more than one closed by choosing a number. Reaching for
weathering to explain a discrepancy is precisely the move the test in this section exists to catch.

### Fouling in the corners, from an algorithm rather than from a texture

The zone table above is organised by `h` because most of a liner's weathering is. **The corners are
the row that is not**, and they are the row that sells the picture: an old pool is pale in the
middle and dark in its corners *at the same time*. This section is the algorithm for that darkening,
and it is worth having as an algorithm because the obvious substitutes — a painted mask, or a grime
term driven by ambient occlusion — are wrong in a way that is specific and diagnosable rather than
merely approximate.

**Three driver fields, none of them authored.**

| field | what it is | where it comes from |
|---|---|---|
| `h = z − z_water` | the zone coordinate | [the albedo field](#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate) — already specified, already runtime |
| `E` | irradiance at the surface point | the renderer computes it for shading anyway; reuse the value, do not re-derive a proxy |
| `σ` | **stagnation** | the only new physics, and it is one Laplace solve |

**`σ` needs no CFD, and the reason it does not is the load-bearing part.** Deposit does not collect
in corners because corners are dark. It collects because **the water does not move there**. A pool
has a return fitting at a known position and aim and a skimmer opposite it, so the first
approximation is the classical one — incompressible, irrotational, plan view:

```
# Stagnation from one Laplace solve. Deterministic, mesh-free in the authoring sense,
# and the same field every run -- which is what makes it an input rather than an effect.

solve   grad^2 phi = 0                on the basin's plan polygon
with    dphi/dn = 0                   on every wall            (no flux through a solid)
        dphi/dn = +Q  at the return   (source, or a short segment for a wall jet)
        dphi/dn = -Q  at the skimmer  (sink; the two must sum to zero or there is no solution)

u       = grad phi                    # plan velocity
sigma   = 1 - smoothstep(u_lo, u_hi, |u|)      # stagnation in [0,1], NOT 1/|u|
```

A few hundred iterations of Gauss–Seidel on a 2-D grid, or a direct sparse solve; it is cheaper
than one frame of the render it feeds, and it is *classical* — the first thing a hydrodynamicist
would write down, not an art trick reverse-engineered from a photograph.

**Its limits belong beside it, and one of them is not a caveat but a warning.**

- No viscosity, so no boundary layer and no separation: a real return jet separates off the wall it
  runs along and the recirculation behind that separation is where a real pool's dead water is.
- A pool return is a **wall jet**, not a point source. Model it as a short segment with an aim if
  the geometry is known; a point source puts the momentum in the wrong place.
- **Potential flow gives *exactly* zero velocity at a sharp corner, and that is precisely where the
  effect is wanted.** In a corner of interior angle `α` the admissible solution is
  `φ = A·r^(π/α)·cos(πθ/α)` — it satisfies `∇²φ = 0` and `∂φ/∂n = 0` on both walls by construction —
  so

  ```
  |u|  ~  r^(pi/alpha - 1)
       alpha =  90 deg  (a square corner)      ->  |u| ~ r^1      -> zero AT the corner
       alpha = 120 deg  (a chamfered corner)   ->  |u| ~ r^0.5    -> still zero, less sharply
       alpha = 270 deg  (a re-entrant corner,  ->  |u| ~ r^-1/3   -> SINGULAR: the model
                         the outside of a step)                       predicts infinite speed
  ```

  (`D`, derived here.) So the approximation **flatters the result in exactly the place the feature
  lives**, and it does so with an exponent that depends on the corner angle — a chamfered corner
  gets less fouling than a square one for a reason the solve supplies rather than an author. Give
  `σ` a floor and clamp `|u|` from below, and say that you did; an unclamped `1/|u|` is a
  singularity waiting for a step nosing. This is the loudest `?` in the section: the *field* is
  classical, its behaviour at the corner is a known artefact of dropping viscosity, and no part of
  this predicts a rate.

**The two fields are not aligned, and that is the whole diagnostic value of the section.** Biofilm
needs **stagnation**. Photosynthetic algae need stagnation **and light**. So

```
cover_biofilm  =  f( sigma,        h )          # dark, indifferent to E
cover_algae    =  f( sigma * E',   h )          # dark, green-shifted, needs BOTH
                                                #   E' = irradiance normalised over the basin
```

and the worst place in a real pool is therefore not the darkest corner but the **sunlit stagnant**
one. **The standard move — drive a grime mask from ambient occlusion — is the correct answer for
one mechanism and exactly backwards for the other**, because AO is high where light is low, and one
of the two organisms needs the light. A single accessibility mask cannot represent two unaligned
drivers, whatever it is multiplied by; the tell is a pool whose dirt is all in the shade, and it
generalises to every AO-driven dirt term in a renderer. (Which organism dominates in which
conditions is `?` and is not a renderer's to assert.)

**Patchiness comes from feedback, not from noise.** Deposit roughens the surface; a rougher surface
holds more deposit. That coupling is **positive**, and it is why aged surfaces are blotchy rather
than evenly grey:

```
d_{k+1} = d_k + dt * S(sigma, E, h) * (1 + kappa * d_k) * (1 - d_k)    # k = 3..5 is enough
rough   = lerp(rough_0, ROUGH_DEPOSIT, d)
```

Linearise about a uniform state `d̄`: a perturbation grows at `∂ḋ/∂d = S·(κ(1 − 2d̄) − 1)`, which is
**positive** for `κ > 1/(1 − 2d̄)` — so above a threshold roughness feedback the uniform state is
unstable and any heterogeneity the geometry already supplies amplifies into blotches, while the
`(1 − d)` saturation bounds them. **The pattern is the instability, not a texture.** A few
iterations give it for free, and it keeps the useful property that nothing in the mask is authored
— no noise, no cellular texture, nothing that has to be re-authored when the basin changes shape.
Seed the heterogeneity from the fields already present (`σ`, `E`, `h`, and the surface's own
roughness map), never from a noise octave: a noise texture here would be the first authored thing
in the chain and it would be authored into the one place where a real mechanism is available.

**Composition is the albedo field's, unchanged, and two of its rules bite hardest here.** Biofilm is
a **deposit**, so it lerps toward `RHO_BIOFILM` and never multiplies — a multiplicative mask cannot
darken toward a green-black that is not a multiple of the liner. And the same deposit above and
below the line must **not** be the same colour in frame: the round trip at 1.40 m is
`(0.4806, 0.8621, 0.9718)`, so a colour-neutral deposit on the bed arrives with roughly half the red
swing it has in blue (`D`, recomputed). If it renders identical either side of the waterline, what
is missing is [transport, not
material](#where-a-weathering-profile-is-allowed-to-come-from-and-what-the-water-does-to-it).

**Rates are not renderable. Susceptibility is, and it is two numbers per material.** A weathering
*rate* is chemistry and service history — water hardness, sanitiser regime, cumulative UV dose, the
polymer's formulation and plasticiser — and **none of it is renderable input**. A renderer that
computed it would be inventing every term, which is the exact class of constant this chapter spends
its length removing. **You state the state; you do not derive it.** What *is* renderable is how
readily a material takes each of the two mechanisms the albedo field already separates:

| | modification (pigment) — *multiplies* | deposition — *lerps to its own albedo* |
|---|---|---|
| **PVC liner** | high — chlorine and UV attack the pigment | high |
| **glazed ceramic** | ≈ 0 — the glaze is glass | low on the glaze, **high in the grout** |
| **fair-faced concrete / render** | low | high, and it wicks (`?`) |

(`?` throughout — these are orderings a materials scientist would recognise, not measurements, and
`12b` marks them as such. The *orderings* are what the section rests on; the numbers are not stated
because nobody measured them here.)

**The payoff is that the signature changes shape for free.** On a tiled pool the weathering moves
from a **band** to a **grid**: the glaze stays clean while the grout limes and holds biofilm, being
porous and rough. One algorithm, one control, two susceptibility pairs — and a qualitatively
different picture, which is what a real tiled pool shows and what a second hand-authored mask is
usually written to fake.

**Where the parameters live, because the wrong placement is what forces a second algorithm later.**

- **Susceptibility is a *material* property.** It sits beside `base_color` and
  `specular_roughness`, travels with the material into every scene, and is two numbers.
- **The `neglect` path is a *scene* (instance) property.** One control from *newly commissioned* to
  *years badly maintained*, implemented as a **curve through** the individual dimensions rather than
  as a dimension itself — because [age is not a
  scalar](#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate) and one slider
  over the raw space produces combinations no pool has. A path through a space is one number that
  keeps the space addressable; a slider *replacing* the space is one number that destroys it.
- Put susceptibility on the instance and every material needs its own copy of the curve. Put the
  path on the material and a scene cannot age two pools differently. Both mistakes end in a second
  algorithm.

**And the default is not zero.** Most outdoor pools in service carry a waterline band, so **a
pristine liner is the special case** and a renderer whose neutral setting is zero age reads as CG by
default — a perfectly clean waterline is a synthetic tell, and unlike most tells it is present in
every outdoor pool ever framed. Ship `neglect` at a non-zero default and let `0` mean *newly
commissioned*, which is then a deliberate choice rather than the absence of one.

**Generalise it, because the pool is the least of it.** Any surface with a persistent liquid line
accumulates at that line: tanks, locks, harbour walls, canal revetments, weirs, a boat's hull, a
water butt, a reservoir drawdown zone. In every one of them the *default state of a real one is not
the state of a new one*, and rendering the new one is the exception that needs justifying. The
machinery is identical — `h` against the body's own datum, a stagnation field from whatever drives
the flow, a susceptibility pair per material — and only the datum's stability changes: a lock's
level cycles daily and writes a *wide* band, a reservoir's seasonally and writes a wider one, a
pool's barely at all and writes the narrow high-contrast line this chapter measures.

### The rest of the man-made checklist

- **Straight lines are the fidelity test.** Tiled walls and rectangular coping hand the viewer a
  known-straight reference that the refracted surface visibly bends. It is also where the depth
  reject in [Shading and optics](#shading-and-optics) earns its place: deck, coping and everything
  standing on them sit *directly* adjacent to the water in screen space, so an unrejected
  refraction sample smears them into the pool every frame.
- **The waterline is geometry, not a fade.** On a vertical wall the shore-distance field carries no
  information. Author the band: wet tile below the line, a damp gradient above from splash, the static
  scale line at the tile course, a specular [meniscus](#the-meniscus-line-where-reachability-cannot-fail).
  All of it keys off `h = z − z_water` and none of it is paintable at a fixed level —
  [A liner in service is an albedo
  field](#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate).
- **Inflows are the flow field.** Return jets and skimmer draw are the only steady flow, and they
  are small and local — author them as sim-patch injections rather than exporting a flow raster for
  a 10 m body.
- **The gameplay surface is trivially correct here** — flat datum plus a centimetre of ripple — so
  there is no excuse for the swim-volume mismatch in [Pitfalls](#pitfalls).

## Shading and optics

BRDF math routes to physically-based-rendering; what this skill owns is the *composition* — which
signals feed the water shader and where each comes from. The water pixel is:

```
color = lerp(refracted_underwater, reflected_environment, Fresnel(NdotV))
      + foam + sun_glint
```

- **Fresnel** is the blend, and its `F0` comes from the body's index of refraction — a
  **per-body** value, not a constant. It is the **external** reflectance, the one a camera in air
  meets; the same interface returns 7.14× as much to light arriving from *inside*, and conflating
  the two is [its own failure](#surface-reflection-names-two-opposite-things-a-loss-and-a-trap). Fresh water is IOR 1.33 → `F0 = ((1.33−1)/(1.33+1))² ≈ 0.02`,
  **half** the generic dielectric default of 0.04 (which is IOR 1.5, glass/plastic); ship the
  default and calm water reads too reflective and faintly plastic even before the
  distance-filtering problems compound it. But natural liquids span IOR ~1.31–1.47 (ice → seawater
  → brine → oil), i.e. `F0` from ~0.018 to ~0.036 — a **2× reflectance spread**, so a brine pool
  reflects visibly more than the lake beside it. Take `ior` from the `liquidBody` descriptor
  (terrain-architect `28`) into `specular_ior` rather than hardcoding 1.33. Use the roughness-aware
  form of [Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic) at
  grazing angles; the `F0 = ((n−1)/(n+1))²` derivation and the amplitude-Fresnel details route to
  physically-based-rendering.
- **Reflection** is a fallback hierarchy, never a single source: SSR first (correct for local
  objects), planar reflection for the hero body when budget allows (see
  [Transparency & pass ordering](#transparency--pass-ordering)), distant cubemap/sky capture
  last. Blend by SSR confidence — SSR *will* drop out at grazing angles and screen edges (the
  reflected ray leaves the screen exactly where water is most reflective), and the fallback must
  match the SSR result in brightness or the dropout draws a line. Grazing-angle Fresnel makes
  water the most brutal SSR-consistency test in the frame.
- **Refraction**: the normal-driven UV distortion below is a **screen-space approximation of
  Snell's-law bending** at the surface (`n_air·sinθ_i = n_water·sinθ_t`, water IOR ≈ 1.33) — it
  offsets the lookup by the surface normal rather than tracing the bent ray, which is why it is
  cheap and why it cannot handle a surface steep enough to see *around* an obstacle. Sample the
  scene-color copy, clamped by view depth so near-surface distortion doesn't grab pixels metres
  away. The canonical artifact:
  a distorted sample lands on an object *above* the water (a dock post, a character's torso),
  smearing it into the water. The fix is a depth reject — if the refracted sample's scene depth
  is closer than the water surface, fall back to the undistorted UV:

```hlsl
float2 uvR = uv + n.xz * distortStrength / viewDepth;
if (LinearEyeDepth(SceneDepth.Sample(s, uvR)) < waterViewDepth) uvR = uv;  // sample was above water
float3 refracted = SceneColor.Sample(s, uvR).rgb;
```

- **Absorption and scattering with depth**: extinguish the refracted color per channel with the
  water-traversal distance — Beer–Lambert on `c`, whose red component exceeds green exceeds blue
  for natural water — and add the column's own returned radiance as that transmission saturates.
  The traversal distance is the vertical column divided by the **Snell** cosine — *not* the
  straight-ray length from scene depth vs surface depth, which
  [diverges at grazing incidence where the refracted one cannot](#screen-space-water-the-fullscreen-triangle-pass) —
  and the vertical component comes from the exported depth field; the shallow→deep color ramp is the
  single strongest realism cue water has, and it is entirely a function of the generator's
  bathymetry. Flat-colored water is almost always a missing/ignored depth field.

```hlsl
float verticalDepth = WaterDepth(worldXZ);                                     // bathymetry field

// The refracted path, not the straight one. cos(theta_a) goes to zero at the horizon; mu_w
// cannot go below 1/n = 0.749, so this length is bounded by 1.33 * verticalDepth and the
// straight-ray version is not. Taking `SceneLinearDepth - waterLinearDepth` here instead costs
// a median of 12.1% and 46.5% at p95 over a measured frame -- one sqrt.
float  sinA         = sqrt(saturate(1.0 - cosA * cosA));                       // cosA = view . up
float  mu_w         = sqrt(saturate(1.0 - (sinA / n) * (sinA / n)));           // Snell cosine
float rayDistance   = verticalDepth / max(mu_w, 1e-4);                         // metres in water

float3 T_beam  = exp(-c_RGB   * rayDistance);    // beam attenuation: the bed's OWN radiance
float3 T_diff  = exp(-K_d_RGB * verticalDepth);  // diffuse attenuation: the light column
float3 L_water = refracted * T_beam + L_scatter * (1.0 - T_diff);

shoreMask   = saturate(verticalDepth / shoreFadeDepth);
causticMask = 1.0 - saturate(verticalDepth / causticFadeDepth);
```

Three things about that block. `rayDistance` controls extinction along the camera path;
`verticalDepth` controls the shore regime, caustic survival, and shallow-wave response — related by
exactly one factor `1/μ_w ∈ [1, 1.33]`, and never interchangeable. The two terms are **not** a lerp and their weights do not sum to one: they
are two transport paths, not two ends of a blend. And **`c` and `K_d` are two coefficients, not
one** — the trap named in
[Water-body optical identity](#water-body-optical-identity-where-the-iops-come-from) below, easy to
ship because one lumped extinction looks reasonable until someone measures it. `c` runs 5–20×
larger than `K_d`, so whichever of the two a single constant was fitted to, the other term is wrong
by that factor. `L_scatter` is the radiance the column returns: an **AOP**, computed from `b_b`,
`K_d` and the incident irradiance, never an authored swatch. All of it belongs to the water-body
descriptor — ocean, clear lake, and turbid river must not share one global constant.
- **Foam** is three masks with one compositor: shoreline foam (depth + shore distance, advected
  along shore tangent), whitecaps (Jacobian, above), flow foam (rivers, above). Composite as an
  opaque-ish albedo layer that *kills* the Fresnel reflection under it — foam is scattering
  froth, not glossy water, and reflective foam is an instant fake tell.
- **Caustics** are the light that got *through* the surface and focused on the bed. They carry
  their own pass, tier ladder and masking contract — see
  [Caustics](#caustics-the-other-half-of-the-light-path). The one-line version: caustic brightness
  is the inverse Jacobian of the refracted-ray map, it multiplies the sun term rather than the
  albedo, and it is gated by sun visibility **at the surface**, not at the receiver.
- **Underwater camera state** is a real state machine, not a fog tweak: on submersion switch to
  underwater fog (aggressive, chromatic, from the same IOPs), render the surface from below
  (total internal reflection outside **Snell's window** — for water→air the critical angle is
  `arcsin(1/1.33) ≈ 48.6°`, so the whole above-water world compresses into a ~97°-wide bright
  circle overhead and everything outside it mirrors the bottom; a cheap, high-value cue), and
  handle the half-submerged frame explicitly. The waterline crossing is
  either a hard cut (acceptable, hide with a droplet/meniscus overlay for a frame or two) or a
  true split-screen meniscus (render both states, mask by the wave-displaced waterline in screen
  space — expensive, hero-camera only). The untreated version — one frame of neither-state
  garbage at the crossing — is a certified review catch.

### Surface reflection names two opposite things: a loss and a trap

Everything above says "Fresnel", "surface reflection" or "reflectance" and means one of **two**
numbers. They are the same interface read from its two sides, they differ by **7.14×**, and they push
a pool's interior in opposite directions. This chapter used both senses under one word for its whole
run; a reader who takes the wrong one is out by that factor, in the direction that makes the water
too dark. Fix the vocabulary before quoting any transport figure below.

| | seen from **above** — `R_ext` | seen from **below** — `R_int` |
|---|---|---|
| what it is | light arriving from the air that **never enters** the water | light arriving from the water that is **turned back into** it |
| it behaves as | a **loss**: subtract it once, on the way in | a **trap**: it multiplies, `1/(1 − ρ·R_int)` |
| diffuse constant at `n = 1.3348` | **6.669%** | **47.617%** |
| at normal incidence | 2.056% | — (the whole cone is sub-critical; use `R(θ)`) |
| at 32.78° incidence — a 57.22° sun | **2.217%** | — |
| at 68.98° incidence — a 21.02° sun | **12.241%** | — |
| past `θ_c` = 48.519° | no critical angle exists from the thin side | **exactly 1** — total internal reflection |
| where it belongs | the entry fee on the sun and on the sky; the reflected column of a water pixel; the sky a poolward band sees *in* the water (`sin²θ`-weighted mean **0.2112**) | the denominator of the trapped series; the diffuse escape `1 − R_int`; the mirror outside Snell's window, which fills 78% of a submerged vertical face's upper half |

(`D`, exact unpolarised Fresnel and 2000-node quadratures recomputed here on this chapter's IOR
triple; the derivation, the per-channel spread and the discontinuity that has to be split out of the
internal integral are [`12a` §7](12a-water-derivations.md#one-interface-two-diffuse-reflectances).)

![The two directional Fresnel curves of one water surface, and the exact decomposition of the internal one](figures/fresnel-two-sides.png)

> **Figure 12·1 — one interface, two reflectances, and where the larger one comes from.** `D`.
> Drawn by [`figures/make_figures.py`](figures/make_figures.py) (`fig_two_sides`), green band,
> `n = 1.3348`, from `reference-impl/optics.py`'s own `fresnel` and `r_int_at` — no constant is
> retyped. Scene-linear (both axes are dimensionless ratios; no transfer curve anywhere).
> **Left:** the same boundary read from its two sides. The air→water curve has **no critical
> angle** and climbs smoothly to 1 only at grazing; the water→air curve is **pinned to exactly 1**
> past `θ_c = 48.52°` and is flat there for 41.5° of the hemisphere. That single discontinuity is
> the whole reason the two hemispherical means differ by 7.14×, and the symmetric-looking formula
> `R = ½(r_s + r_p)` does not show it. **Right:** the cosine-weighted integrand `2μ R(μ)`, whose
> **areas are the three constants**. The pale block left of `μ_c` is `∫₀^{μ_c} 2μ dμ = cos²θ_c =
> 1 − 1/n² = 0.43874`, which contains **no Fresnel evaluation at all** — it is geometry. The narrow
> block right of it is the partial Fresnel remnant, 0.03743, and the two sum to `R_int = 0.47617`.
> The third, flattest area is `R_ext = 0.06669` on the same scale: the entire external loss is the
> sliver. Read the picture and the reason `1 − 1/n²` gets used *as* `R_int` is immediate — they are
> the same region minus a shape that is hard to see and worth 3.74 points.

**The two are tied, so getting one right does not license guessing the other.** Walsh's relation

```
n^2 (1 - R_int) = 1 - R_ext          0.933310 vs 0.933310 at n = 1.3348
```

holds on independent quadratures of the two index pairs to **6×10⁻¹¹**. It is the same identity that
[pins the `1/n²`](#radiance-is-not-conserved-across-the-interface) on light leaving the medium, and
it is a guard rather than a definition precisely because neither side is computed from the other.

**The internal one decomposes exactly, and its larger piece is not Fresnel at all.**

```
R_int  =  (1 - 1/n^2)   +   partial Fresnel inside the cone
       =    43.874%     +        3.743%       =  47.617%
```

**92.1% of the internal return is total internal reflection** — pure geometry, `cos²θ_c`, no Fresnel
evaluation in it — and 7.9% is the partial reflection of sub-critical rays. That is why `1 − 1/n²`
gets used *as* `R_int`: the two are 3.74 points apart, small enough to hide and large enough to cost
1.9% of a red trap and 12.2% of a blue one
([the truncation table](#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point)).

**And `1 − 1/n²` is the same constant that whitens foam.** An air bubble seen from the water side
presents the same water→air interface as the surface seen from below, so it has the same critical
angle and mirrors the same 43.874% of everything striking it. One number runs the mirror outside
Snell's window and the opacity of whitewater — see
[Aerated water](#aerated-water-foam-spray-and-whitewater), where it arrives from the other end. A
renderer that derives one face of it and paints the other has split a single constant in two.

⚠️ **`mirrors` is the whole of the claim and `toward you` is no part of it.** Reflection off a
*sphere* deviates a ray by `π − 2θᵢ`, and total internal reflection is the statement `θᵢ > θ_c`, so
every one of those rays turns by **less than `π − 2θ_c` = 82.96°** — forward of the perpendicular,
every time. A traced bubble backscatters **`b_b/b = 0.023`** against its own 43.874% reflectance,
with `g = 0.688` (`D`). The constant is a per-direction mirror strength and never a return fraction;
[Aerated water](#aerated-water-foam-spray-and-whitewater) carries the trace, the similarity scaling
that replaces the misreading, and what confusing the two costs.

**What the confusion costs, priced.** On this chapter's liner (`ρ_bed = 0.222 / 0.585 / 0.681`):

| the wrong sense | what it does |
|---|---|
| `R_ext` (6.669%) used as the internal return | the trapped gain falls `1.386 → 1.041` in green: **−9.2 / −24.9 / −29.2 %** per channel. Chromatic, so it **desaturates** rather than darkens, and survives a luminance check |
| `R_int` (47.617%) used as the external loss | the surface rejects 47.6% of the sun instead of 6.7% — the water takes **0.561×** the light, flatly and achromatically |
| both, which is what one symbol produces | **0.421×** in green — the interior is **2.37× too dark**, and no exposure fixes it because the reflected column of the same pixel is untouched |

(`D`, arithmetic here on the constants above.) The rule that prevents it is the same one this chapter
applies to `c` versus `K_d` and to per-axis versus total slope: **name the convention once, upstream
of every consumer.** Two symbols, `R_ext` and `R_int`, never one `R_surface`; and where a number is
quoted, say which side of the boundary the light was on and whether it is a hemispherical mean or a
`R(θ)`.

### Radiance is not conserved across the interface

The composition at the top of [Shading and optics](#shading-and-optics) reads as a blend of two
radiances, and it is not one.
The reflected term is measured in **air**; the refracted term — bottom albedo times the irradiance
that got through the surface — is measured in **water**, and radiance does not survive a change of
index. What is invariant along a pencil is **`L/n²`**, because the étendue `n² dA dΩ` is. So the
transmitted column leaves the water as

```
L_air = T(theta_v) * L_in / n^2,     n^2 = 1.774 / 1.782 / 1.796 on an IOR triple of 1.3320/1.3348/1.3400
```

and a shader that omits the divisor renders the bed **1.78× too bright** — 0.827 to 0.844 stops.

**No exposure setting absorbs it, because it is a *relative* error inside one pixel.** The sky term
is air-side and already correct, so the two columns of the same `lerp` disagree by `n²`. That is
exactly the reflected-versus-transmitted ratio a water body is judged on, and a grade cannot move
one half of a pixel. This project shipped the omission for its whole run.

**The diffuse form, and the trap that follows it.** For a Lambertian source under the surface the
same transport integrates to `(1 − R_ext)/n² = 1 − R_int` — **0.526 / 0.524 / 0.519** on those
IORs, Walsh's relation, and the same `R_int = 0.47617` that drives the [trapped
series](#the-two-materials-a-pool-actually-has-and-neither-is-water). Note which reflectance is on
which side of it: the numerator's is the **external** 6.669% and the result's is the **internal**
47.617%, and [they are not the same number](#surface-reflection-names-two-opposite-things-a-loss-and-a-trap). A renderer will happily carry
that on **one** route out of the interface and not on another: `reference-impl` had a hand-written
`0.5` on the diffuse route (upwelling radiance onto the surrounding stone) while the camera's own
route through the `lerp` had nothing at all. Two exits from one interface disagreeing by `n²`, with
nothing in the file comparing them. Enumerate every place light leaves the medium and check that
they all divide by the same thing.

**Fitted constants do not launder it, but you need something to prove that with.** The standard
objection is that albedos and exposure were fitted to a photograph with the factor absent and may
be compensating for it, so applying the divisor and raising exposure to compensate would only move
the error. What breaks that circle is a calibration target with **no water path**: here, the [dry
liner band](#the-two-materials-a-pool-actually-has-and-neither-is-water) above the waterline — same
pigment, no absorption, no interface and no `n²` between it and the eye, so its radiance over its
own irradiance reads the albedo directly. A pigment secretly carrying a missing 1.78 would have to
sit 78% off a published PVC value; measured, it was within 8%, and neither the liner tint nor the
exposure moved when the divisor went in. Absent such a target, fix the physics and *state* that the
constants fitted around it are now suspect — do not raise exposure to put the brightness back.

**Two guards, and neither could have been written from the derivation.** Walsh's relation
`n²(1 − R_int) = 1 − R_ext`, with both sides quadratured independently, pins the **exponent** and
not merely the presence of a factor — at `n¹` the two sides part by 25% and at `n³` by 33%. And a
closed energy audit: a body with a perfect white Lambertian bed and no absorption must have an
apparent albedo of **exactly 1**; composed with the divisor it is 1, without it **1.73**, with a
`1/n` instead **1.31**. Neither guard contains a constant of the renderer. Why a large suite of
Fresnel tests could not see any of this — and why that generalises past water — is
[`11`](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one).

**And then read what that audit *borrows*, because it is one name.** It catches the divisor and it
catches nothing else: it writes its own irradiance and its own in-water radiance, closes the
interreflection series itself, has no absorption (every path length exactly 1) and no basin. So it
passed throughout while the transport it was named after was wrong in three separate factors. The
replacement is a **pair** — a lossless limit that pins the series' shape, and a photon walk at the
medium's own absorption that pins its path lengths — chosen so each sees where the other is blind,
and both fired at deliberately reintroduced bugs. That discipline, and why the title of a test is
the most dangerous thing about it, is [`11`'s eighth
way](11-verification-failures.md#the-eighth-way-is-about-the-test-not-the-measurement).

### What a submerged vertical face sees of the sky

The same interface, read by a receiver that is not the bed. A submerged wall, a step riser, a
piling, a ladder stringer, a swimmer's flank — every vertical face under the water — has an upper
half-hemisphere, and a renderer will fill it with the sky. **It is not the sky.** It is the
underside of the surface, and the underside is two different things either side of the critical
angle: inside the Snell cone the transmitted sky, compressed into `asin(1/n)` about the **vertical**
— the worst possible placement for a receiver whose normal is horizontal — and outside it, over
`1 − 1/n²` of the directions, a perfect mirror showing the pool's own upwelling field.

**Split the half-hemisphere and both numbers fall out.** Take a uniform in-water radiance `L`, let
`θ_c = asin(1/n)`, and normalise everything to what a *horizontal* face at the same depth collects
from the whole hemisphere. The three ratios, and the partition identity that ties them, are
[`12a` §7's](12a-water-derivations.md#the-window-and-the-mirror-two-halves-of-one-hemisphere):

```
E_vert / E_horiz  over the FULL hemisphere       = tir_vert(0)          = 0.500
E_vert / E_horiz  over the mirror cone t > tc    = TIR_VERT             = 0.885
E_horiz(cone)     / E_horiz(hemisphere)          = 1 - 1/n^2 = TIR_FRAC = 0.439

    tir_vert(tc) = ( pi/2 - tc + sin tc cos tc ) / ( pi cos^2 tc )

=> mirror's share of the vertical face      = TIR_VERT * TIR_FRAC       = 0.388
   window's share of the vertical face      = 0.5 - 0.388               = 0.112
   ...and against the BED's own sky, which arrives through the same window and is 1/n^2 of
   that bed's hemisphere:                     0.112 * n^2               = 0.199
```

Three things to take from those lines (`D`, recomputed here at `n = 1.3348`; per channel the
window share runs 0.1995 / 0.1988 / 0.1976 on this chapter's IOR triple, so one figure is honest):

- **`0.5` is a correct partition and a wrong description.** A vertical face does collect exactly
  half of what a horizontal one does under a uniform hemisphere — that is the ½ every riser gather
  closes on — but of that half, **77.7% is mirror and only 22.3% is window**. Filling the whole
  upper half with sky is not a small approximation of the split; it is the other end of it.
- **A submerged vertical face's sky share is `0.199` of a horizontal face's at the same depth**, not
  `0.5`. The reference implementation handed it `WALL_SKY × WAO = 0.50 × 0.78 = 0.390`, **over-giving
  the sky by ×1.96** — a factor of two on a term, arrived at by using the partition as the value.
- **Over-giving the sky necessarily under-gives the mirror**, because they are two halves of one
  hemisphere and the partition is fixed. The upwelling field that should fill the other 77.7% is the
  pool's own trapped return, which a one-bounce truncation already under-delivers. So the wall
  arrives at roughly the right *level* by two errors of opposite sign, and **a wall lit right for
  the wrong reason is the failure mode.**

**How to separate them, because any measurement of the total is blind by construction.** Three
instruments, in increasing order of what they cost to set up:

- **Colour.** The window carries the *sky's* spectrum and the mirror carries the *bed's*, filtered
  by two more legs of water. They are far apart: a blue-dominant hemisphere against a liner-coloured
  upwelling field that has crossed the column twice. A vertical face whose hue tracks the sky rather
  than the liner is over-window-ed, whatever its level.
- **Structure.** The mirror carries the caustic net — folded, doubled and softened, but present and
  *moving with the surface*. The window carries none. A submerged face with the right brightness and
  no moving structure on it has had the mirror replaced by a constant.
- **Turn one off.** Zero the sky and the face must fall to 77.7% of its upper-half irradiance, not
  to zero and not to half. That single ratio separates the two terms with no photograph and no
  reference, and it is the row to add to a suite before either constant is touched.

**This is a different claim from the floor-lit-wall ceiling and the two must not be merged.** The
ceiling in [the masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped)
— `L_wall ≤ ρ_wall·L_floor/2` — compares a wall against **the floor**, and it is about the *lower*
half of the wall's hemisphere: a form factor of exactly ½ to an adjoining diffuse plane, which is
why adding gather strength cannot rescue a dark wall. This section is about the **upper** half and
compares a wall against **the sky through the surface**. One bounds what the bed can give a wall;
the other says what the surface can. Conflating them produces the confident wrong move of raising a
gather multiplier to fix a sky term, and the two halves sum to the whole hemisphere, so an error in
either shows up as the same symptom.

**Where it stands in the reference implementation: measured, both halves now derived, and still
open.** The submerged wall read **0.470** of the dry liner band over its first 100 mm and **0.581**
over the next 150 mm; with the receiver's whole hemisphere traced those became **0.518** and
**0.616**, and with the band's own illuminant derived as well, **0.513** and **0.621** — against an
observation of the real pool that puts them above 1 (`D`, three successive rounds). Beer–Lambert
over those centimetres of water is worth 0.971–0.995, so the path is not the cause; binned by traced
leg the ratio *rises*, because a deeper texel sees more of the bed, which means the bins are reading
depth and not absorption. The entry fee alone — an in-water radiance seen from the air takes the
`1/n²` while the dry band 10 cm above it takes nothing — means the wall must be **1.78× brighter
than the band below the surface merely to draw level with it above the surface**. Closing it needed
both halves at once, and both have now been closed: the window's `0.199` in place of `0.5`, *and*
the mirror's missing bounces, which is the section below. **The ordering still did not emerge**, and
the remaining factor of ~1.95 is now attributed to neither the receiver nor the source but to what
is missing from both — a located fault, not a fixed one (`?`).

### The upgoing half, traced: the return leg, the mirror, and the fixed point

The partition above says what the two halves of a submerged vertical face's upper hemisphere *are*.
This section is how to evaluate them, and it exists because the shape of the integral is what
renderers get wrong, not the constants in it. **Do not resolve the window and the mirror into two
terms and multiply each by a constant.** Gather the half-hemisphere and let the trace decide which
of the two any given direction is:

```
# The upgoing half of ANY submerged face's hemisphere -- bed, wall, riser, hull, ladder.
# One function, so the renderer cannot hold two opinions about what is above a submerged surface.

E_up/pi  =  (1/pi) INT_{w.n > 0, w_z > 0}  L(w) (w.n) dw

L(w):
    hit = trace_up(x, w)                       # an UP-GOING intersector -- see the note below
    if hit is a solid before the surface:
        return radiance_map[hit]               # THE RETURN LEG: wall -> bed, wall -> wall, riser
    t   = angle(w, surface_normal)             # incidence on the underside, from inside
    if t >= t_c:  return L(reflect(w))         # past the critical angle the mirror is PERFECT
    R   = r_int_at(t)                          # exact internal Fresnel, per direction, no cone mean
    return (1 - R) * sky_through_window(w) + R * L(reflect(w))
```

Three properties of that fragment are the whole content, and each is a thing production renderers
routinely lack.

- **`trace_up` is usually missing.** A water renderer's scene intersector is built for the *down*
  legs — camera to surface, surface to bed, sun to bed — and is frequently direction-restricted or
  depth-buffer-backed, neither of which can answer "what solid is above and to the side of this
  wall texel". Without it, the wall→bed leg cannot exist and the bed's ambient gets a constant over
  the third of its hemisphere that is wall. On this chapter's reference basin that share is
  **35.3%** of the bed's hemisphere, and the wall it stands for runs `(0.335, 0.920, 1.186)` at the
  waterline to `(0.125, 0.759, 1.131)` at its foot (`D`) — a factor of 2.7 in red across the
  receiver, so no constant is right for it.
- **`r_int_at(t)` must be the *external* Fresnel read at the conjugate air-side angle** — Stokes
  reversibility — and not a cone-averaged `R_int`. The diffuse constant `R_int = 0.47617` is a
  hemispherical mean and is correct only for the hemispherical quantity; used per direction it is
  wrong everywhere, too high inside the window and too low outside it, and the two errors do not
  cancel because the window and the mirror carry different sources.
- **Walls are emitters as well as receivers.** In a shooting formulation the fraction of the trap
  that meets a wall on its way up is a *loss*; in a gather those directions simply **are** wall hits
  and bring the wall's own radiance back. Same geometry, opposite bookkeeping — and the shooting
  version silently deletes it. On this basin that fraction was 58% (`D`).

**A bed point's own window is occluded by the basin, which is not obvious and runs the other way.**
The sky arrives through a 48.5° cone about the vertical, so a wall near the horizon cannot reach
into it — the naive expectation is therefore that walls cost the bed nothing in sky. They do,
through aspect ratio: a bed point at depth `d` sends its window rays out to `d·tan(48.5°)` of
horizontal run — 1.58 m at 1.40 m — so in an 8 × 4 m basin **87% of the floor has part of its own
window behind a wall**, and the part behind it is the *outer* window, which a horizontal face
weights by `cos t sin t` and therefore weights most. Measured: the window's sky on the deep floor
falls **17% in green** while the mirror-plus-wall term rises by a factor of ~8 (`D`):

| the deep floor's ambient, same units | window sky | mirror **and wall** | together |
|---|---|---|---|
| one bounce, flat constant over the wall share | `(0.248, 0.629, 1.085)` | `(0.006, 0.054, 0.082)` | `(0.254, 0.683, 1.167)` |
| traced, iterated to a fixed point | `(0.225, 0.521, 0.890)` | `(0.046, 0.426, 0.720)` | `(0.271, 0.947, 1.610)` |

**+39% in green on the bed's ambient**, and the two-symptom prediction it closes is the one in the
[masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped):
caustic interiors too dark *and* an occluder's shadow too bright, in one frame. The occluder's
shadow now arrives at **92%** of its own depth against 91% (`D`) — the shadow barely moved while the
interiors filled, which is exactly what a *directional* return does and a raised ambient cannot.

**Truncating the trap at one bounce is a real error with a computable size, and it is not small.**
The closed geometric series and its truncations, at the diffuse constant and at the wrong cone:

| bed albedo ρ | exact `1/(1 − ρ·R_int)` | one bounce | two bounces | one bounce over `1 − 1/n²` |
|---|---|---|---|---|
| 0.222 (this liner, red) | 1.1182 | 1.1057 (−1.1%) | 1.1169 (−0.1%) | 1.0974 (−1.9%) |
| 0.400 (luminance) | 1.2353 | 1.1905 (−3.6%) | 1.2267 (−0.7%) | 1.1755 (−4.8%) |
| 0.585 (this liner, green) | 1.3861 | 1.2786 (**−7.8%**) | 1.3562 (−2.2%) | 1.2567 (−9.3%) |
| 0.681 (this liner, blue) | 1.4799 | 1.3243 (**−10.5%**) | 1.4294 (−3.4%) | 1.2988 (−12.2%) |

![The trapped series, its truncations, and the lossless bound against the real absorbing column](figures/trapped-series.png)

> **Figure 12·3 — the trapped gain: three errors in one quantity, and one of them is the chapter's
> own.** `D`. Drawn by [`figures/make_figures.py`](figures/make_figures.py)
> (`fig_trapped_series`) from `reference-impl/optics.py`'s `R_INT`, `slab_trap` and `IOR`.
> Scene-linear; a gain is dimensionless. **Left:** the closed series against its truncations, with
> this liner's three albedos marked. The error grows *superlinearly* in `ρ`, which is why one
> curve read at three albedos produces a **chromatic** error — the truncation is a function of `ρ`
> alone and the chromaticity is entirely the liner's. The wrong-constant curve
> `1/(1 − ρ(1 − 1/n²))` sits just below one bounce for every `ρ`, so the two mistakes are
> **additive and easy to make together**. **Right, and this is the finding the picture forced:**
> the gain the table above quotes is `1/(1 − ρ·R_int)`, which assumes the returned light **crosses
> the column twice for free**. It does not. The real round trip is `G_rt(τ)`, the same integral the
> LUT section [refuses to factorise](#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them),
> and at this pool's own 1.40 m it is `0.0965 / 0.3277 / 0.4445` against `R_int = 0.476` flat. So
> at ρ = 0.50 the quoted **1.31× gain is really 1.05× in red** — the lossless form overstates by
> **24.7 / 9.7 / 2.4 %** — and on this liner's own triple by **9.4 / 12.0 / 3.7 %** (`D`,
> recomputed here). **`1/(1 − ρ·R_int)` is an upper bound, not the gain**, and it is tight only as
> `τ → 0`. The trapped-gain table in [The two materials a pool actually
> has](#the-two-materials-a-pool-actually-has-and-neither-is-water) is therefore a **depth-free**
> statement and now says so; use it to reason about *why a dark liner loses twice*, and use
> `1/(1 − ρ·G_rt(a·d))` to price a specific pool. The two errors on this page run opposite ways —
> truncation makes the trap too weak, the lossless constant makes it too strong — which is one
> more instance of the rule the LUT section states: **compose the error, do not reason term by
> term.**

(`D`, recomputed here at `R_int = 0.47617`, `1 − 1/n² = 0.43874`.) **The error is chromatic**,
because ρ is, so a one-bounce truncation does not darken a pool — it *desaturates* it, by 7–10% in
the channels the liner is bright in and 1% in the one it is dark in. That is why it survives a
luminance check and why the symptom is read as a washed-out liner colour rather than as missing
transport. And the second bounce buys back three quarters of it for one more pass, which is the
cost argument: **truncation at one is never the cheap choice, it is the choice that leaves the
largest single increment on the table.**

**The fixed point is cheap, and its residual is a bound rather than an assumption.** The transfer is
linear, so iterate it and measure its own gain:

```
L_0 = seed                                     # anything; the previous frame's maps are ideal
L_{k+1} = E_direct + K L_k                     # K = the traced gather above, applied to every
                                               #     submerged emitter (bed, walls, risers)
d_k = |L_k - L_{k-1}|                          # the increment, per channel
r   = d_k / d_{k-1}                            # the operator's MEASURED spectral gain
tail <= d_k * r / (1 - r)                      # geometric bound on everything after pass k
```

Two things make this worth doing rather than picking a bounce count. **Seed from the previous
solution and the first increment is exactly the size of the defect** — which is a free measurement
of what the truncation was costing, taken on the way to fixing it. And `r` is *measured*, not
assumed, so the residual is bounded rather than hoped for: on this basin `r = 0.335 / 0.442` on the
bed and `0.378 / 0.475` on the wall (green / blue), giving a tail of **0.50× and 0.79×** the last
increment on the bed and **0.61× and 0.90×** on the wall, i.e. **0.012% and 0.033% of the converged
level in green** (`D`, the ratio `r/(1−r)` recomputed here). That is under the lattice's own
quadrature error. **Guard the pass count with a row that fails at fewer passes** — run the same
operator for exactly `N` passes from black against the closed series and check that `N−1` FAILs,
or the constant is back.

**Do not expect the fixed point to reach the infinite-basin series, and say why in the same
breath.** That series has no walls to absorb; a real basin loses `(0.754, 0.352, 0.246)` of every
bounce to a liner over a third of a bed point's hemisphere. A solve that *does* reach ×1.2354 in a
walled basin has a leak in it. Print both and the gap between them is the basin.

**How to separate the sky from the mirror, quantitatively — because the total is blind by
construction.** The three qualitative instruments are
[above](#what-a-submerged-vertical-face-sees-of-the-sky); this is the arithmetic that makes the
blindness precise. In the reference implementation the sky was over-given by **×1.96** and the
mirror under-given by roughly the same partition, and the two very nearly cancelled on the wall:
correcting both moved the wall's own radiance **+9.5% in green, +15.3% in blue and −6.2% in red**
(`D`) — **less than either error, in a different direction per channel.** On the step risers, whose
sky share is smaller and whose mirror sees the bed at a metre rather than at four, the same two
corrections gave **+39%** on the face. One scene, one pair of errors, and a factor of four between
what they did to two surfaces.

So: **the measurement that cannot separate them is the one everybody takes.** Three that can, in
increasing cost —

1. **Zero the sky and check the survivor.** The face must fall to **77.7%** of its upper-half
   irradiance. Not to zero, not to half. One row, no reference, no photograph.
2. **Read the two channels apart.** The correction's *sign flips between red and blue* on the wall
   above, because the window carries the sky's spectrum and the mirror carries the liner's after two
   more crossings of the column. A per-channel report distinguishes them where a luminance report
   cannot; a change that moves all three channels the same way is not this pair.
3. **Read a second receiver with a different partition.** A riser at a metre and a wall at four have
   different mirror path lengths and different sky shares, so one pair of errors produces two
   different total shifts. **Two receivers, one correction, two answers** — and if the two answers
   are consistent with a single sky error and a single mirror error, the pair is identified. This is
   the same argument as `11`'s [eighth
   way](11-verification-failures.md#the-eighth-way-is-about-the-test-not-the-measurement), run
   forwards: a test's power is the surface area it shares, and two receivers share more of the
   partition than one does.

**What stays approximate here, named rather than buried.** The mirror leg reflects in the **still**
plane: the wave field is not on it. Over a leg of metres against a slope rms of 0.05–0.12 that
smears a source by a few degrees inside an integral that is already a hemisphere average, which is
why the mirror reads as a *lift* and not as a second caustic net — defensible, and an approximation
(`?`). And a face whose own reflection is in the gather (a riser built from the wall map) needs a
pass of its own or it contributes zero; on this basin that is 4.9% of the lower half and 1.4% of the
upper (`D`), which is the size of the hole a "consumers are not emitters" shortcut leaves.

### The illuminant is part of the comparison: what cancels and what does not

A render is compared to a photograph by holding everything but the renderer fixed, and the largest
thing that is usually *not* held fixed is the sun. A frame that arrives with a place, a date and a
clock time carries a fully determined illuminant — elevation, azimuth and relative optical air mass
are a computation, not an estimate, and `10` gives the algorithm and its
[one dangerous branch](10-lighting-shadows.md#the-quadrant-trap-and-why-the-elevation-stays-right).
Compute it before arguing about water. Until it is known, every discrepancy has a free variable to
hide behind, and "the light was different" is unfalsifiable rather than merely unproven.

What the elevation does to water, on the two suns this chapter's reference pool was photographed
under (Aljezur; the position mathematics and the full table are in
[`10`](10-lighting-shadows.md#computing-the-illuminant-from-a-place-and-a-time)):

| | 18:41, elevation 21.02° | 15:28, elevation 57.22° |
|---|---|---|
| incidence at the surface `θ_i = 90 − h` | 68.98° | **32.78°** |
| transmitted share `1 − R(θ_i)`, unpolarised, `n = 1.3348` | **87.76%** | **97.78%** |
| refracted angle `θ_t` | 44.37° | 23.93° |
| slant path to a 1.40 m bed, `d/cos θ_t` | **1.959 m** | **1.532 m** |
| horizontal offset of the refracted beam at that bed | 1.370 m | 0.621 m |
| air mass | 2.771 | 1.189 |

All six are functions of **elevation alone** (`D`, recomputed here on the reference
implementation's IOR triple; the transmitted share moves by 0.1% across its three channels and by
0.02% between `n = 1.333` and `n = 1.3348`, so a single figure is honest at this precision).

**The cancellation rule, which is what decides whether a comparison means anything.** A deck and a
water surface are both **horizontal receivers**, so the `sin h` projection factor and the air-mass
attenuation of the beam are *identical* on the two of them and cancel exactly in any water-to-deck
ratio. Between these two suns that is a factor of 2.34 in `sin h` and another 1.10–1.38 per channel
in atmospheric transmittance — a combined 2.58 / 2.75 / 3.23 in RGB (`D`) — which is large enough
that it will be reached for as an explanation, and it explains nothing about a ratio. **A quantity
that cancels in the measurement may not be invoked to excuse a discrepancy in that measurement.**
The same argument disposes of the illuminant's *chromaticity* for such a ratio: to the extent both
receivers are dominated by the direct beam, `E(λ)` divides out per channel, and what is left is the
water's own absorption over its own path against the two albedos. This is the same structural point
as `11`'s [sixth way](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one)
read forwards instead of backwards: a ratio is blind to whatever multiplies both of its terms — a
liability when the thing you are testing is that factor, and an asset when it is the confound.

What does **not** cancel is exactly the two rows of the table that belong to the water and not to
the geometry of a horizontal plane:

- **the Fresnel share entering the surface**, because the deck takes the whole beam at any elevation
  while the water admits only `1 − R(θ_i)`: **1.114×** in the higher sun's favour;
- **the slant path to the bed**, because the beam's leg through the medium is `d/cos θ_t`: 1.532 m
  against 1.959 m, worth **1.118×** in red at `a(610) = 0.2644 m⁻¹`. Only the *down* leg moves — a
  near-vertical view's return leg is the depth itself in both cases — so this is the whole of it,
  not half of a round trip.

Together the two are **1.246×** in the red on a near-vertical view (`D`) — the whole of what a
high sun buys the water against the deck beside it, and the number a discrepancy in a water-to-deck
ratio has to be **smaller** than before the sun can be blamed for it. On this project's own
reference frames the measured gap is about twice that again, so the confound covers part of it and
does not close it (the measurement itself is still open, `?`).

**Air mass reddens the beam, and it can run either way against you — so state the direction and
check it.** The relation is `exp(−m·τ_Rayleigh(λ))`, the same inversion `10` uses to read an
[atmosphere back out of a sun colour](10-lighting-shadows.md#the-sky-must-be-the-atmosphere-the-beam-came-through):
a low sun is golden, a high sun is near-white, and a redder illuminant must give redder water,
because with `b_b ≈ 0` the column can only subtract from whatever fell on it. That makes a usable
**inference rule for signed discrepancies**: work out which way the illuminant difference pushes,
and a discrepancy that runs the *other* way is strengthened rather than explained. Worked here: the
reference implementation's `SUN_COL = (1.000, 0.892, 0.674)` inverts to air mass 2.77, i.e. a
red-to-blue ratio of **1.484**, against **1.184** for a genuine air-mass-1.189 illuminant at the
same band centres — so the render's sun is **1.253× redder** than the sun the 15:28 photograph was
shot under (`D`, recomputed here; the bare 1.484 figure compares the render's sun to a flat white
illuminant rather than to the photograph's, which overstates the confound by that same 1.253). The
render's water is nonetheless *less* red than the photograph's. A redder sun producing less red
water is a discrepancy the confound makes **worse**, and the finding survives it.

Two limits on all of the above, both worth stating before a number is quoted from it. The
cancellation is exact only for the direct beam: the sky's share of a receiver's irradiance rises as
the sun drops, and sky and beam have different chromaticities, so a low-sun frame carries an
ambient-to-direct mixture that a high-sun frame does not — which is precisely why the lit/shaded
pair below is a *separate* instrument from the water/deck one. And none of it survives a camera
that is not linear: what a photograph can support is in
[`11`](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one).

### An illuminant per receiver, and what that costs at a waterline

The section above is about holding the *sun* fixed between a render and a photograph. This one is
about what happens after that is done, and it is the more expensive of the two because it is
invisible in the frame that has no reference at all: **the ambient handed to the water and the
ambient handed to the stone beside it are two different integrals of one sky**, and a renderer that
ships one constant for both has quietly asserted that they are not.

`10` derives the general result — [an illuminant is a property of the receiver's
orientation](10-lighting-shadows.md#an-illuminant-is-a-property-of-the-receivers-orientation-not-of-the-scene),
the two weights are `cos θ sin θ` and `sin² θ`, and the aureole gives a vertical face an azimuth
that a halved deck constant cannot carry. A waterline is where a terrain frame collects the most
receiver orientations in the smallest space, so it is where the cost shows first:

| receiver, all within 150 mm of one another | what it sees | why one constant cannot serve it |
|---|---|---|
| **coping and deck**, horizontal, above the water | the whole sky, `cos θ sin θ` | the reference case — the only orientation a "deck illuminant" is right for |
| **the dry liner band**, vertical, poolward-facing | its *upper* half by `sin² θ`, weighted onto the horizon; the aureole only if the sun is in front of its plane | +23 / +10 / −3 % against half the deck value on this sky, and **1.23× between a sun-facing and a sun-averted wall of the same pool** (`D`) |
| **the same band's lower half** | the **water**: the pool's own upwelling *and* the sky reflected in that water at grazing incidence | the reflected-sky term is **23%** of what the band's lower half receives in green (`D`) and is the one most often absent entirely |
| **the submerged wall**, vertical, below the water | 22% Snell window, 78% mirror — [a different partition again](#what-a-submerged-vertical-face-sees-of-the-sky) | not an illuminant question at all: the interface has replaced the sky |

**The lower half is the term that gets left out, and grazing Fresnel is why it is not small.** A
poolward-facing strip a few centimetres above the water looks *down* at the surface over the whole
of its lower half, and the `sin²θ` weight puts most of that half near the horizon — which is
exactly where a water surface stops being a 2% reflector. The `sin²θ`-weighted mean unpolarised
external reflectance is **0.2112** against **0.0206** at normal incidence, a factor of **10.3**
(`D`, quadratured here at `n = 1.3348`). So a band over water is lit substantially by *sky it can
only see as a reflection*, and a renderer that gives it the pool's upwelling and stops has modelled
the smaller half of what the water returns to it.

**Both errors were live in this chapter's own reference implementation, and their signs are the
useful part.** Its band took `SKY_DECK × 0.50` for its sky and the pool's diffuse upwelling for the
water, with no reflected-sky term at all. Deriving the band's own hemisphere at its own azimuth
gives (`D`, per channel, `E/π`):

| the band's own irradiance, sun-averted wall | red | green | blue |
|---|---|---|---|
| its own sky, upper half | 0.3139 | 0.4016 | 0.6124 |
| the sky the **water reflects** into the lower half | 0.0838 | 0.0975 | 0.1291 |
| the pool's upwelling into the lower half | 0.0484 | 0.3242 | 0.4749 |
| direct sun (`N·L = −0.061`, clipped) | 0 | 0 | 0 |
| **sum of the terms above** | **0.4461** | **0.8233** | **1.2164** |

The reflected sky is **19 / 12 / 11 %** of the band's total and **63 / 23 / 21 %** of its lower half
(`D`, recomputed here). ⚠️ The run that produced these components prints a "total" of
`(0.4761, 0.9220, 1.3568)`, which is **not** the sum of its own rows — the difference is 6.7 / 12.0 /
11.5 % and is not a constant, so it is a different normalisation rather than a rounding. Both cannot
be right and this chapter does not know which is; the components are reproducible and the total is
marked `?` in [`12b`](12b-water-provenance.md). **Quote the terms, not the total.**

**The counterfactual that this replaces is worth keeping as a method warning.** Before the integral
existed, an earlier round reasoned: the band cannot see the aureole, the aureole is 68% of the deck
illuminant, therefore drop it and the wall-to-band ratio goes 0.518 → 0.78. Every step is
arithmetic and the conclusion is wrong, because it **subtracted one hand constant while keeping
another** — and the one it kept was 0.42× the integral it stood for. Against the derived integral
the band's sky half moves by about 5% in green, not 34%, and the ratio ends at **0.513** (`D`).
The category error was real; its *size* was an artefact of the decomposition it was computed in.
**A counterfactual evaluated inside a wrong decomposition inherits the decomposition's error, and it
inherits it with confidence**, because subtraction of a known term feels like a measurement.

**One thing an occluder over that band does not do, because the closed form is singular where it
matters.** A strip of height `H` under a ledge overhanging it by `w` keeps a fraction
`(α + sin α cos α)/π` of the upper half at depth `D` below the ledge, with `α = atan(D/w)` — exactly
`0.50`, the whole upper half, at `w = 0`. The trap is that this goes to **zero** as `D → 0`, so a
strip's *average* sky loss is dominated entirely by its top edge:

| overhang `w` | mean over a 100 mm band, as a fraction of the full half | at the band's foot (`D` = 100 mm) |
|---|---|---|
| 20 mm | 87.5% | 99.68% |
| 30 mm | 81.5% | 98.97% |
| 50 mm | 70.6% | 95.95% |

(`D`, integrated here.) ⚠️ A figure of "94% of its sky" for a 30 mm overhang has been quoted for
this geometry and does not reproduce — the value depends almost entirely on how far the band's top
sits below the ledge, which is a *section* question and not a lighting one. **An average sky-loss
number for a strip under a ledge is mostly a statement about where you put the top of the strip**,
so quote the profile or quote the foot; do not quote the mean.

**What it costs to reuse one illuminant, stated as a rule.** Halving a horizontal illuminant for a
vertical face is exact for a uniform sky and for nothing else; it is wrong by the sky's own
horizon-to-zenith contrast in the channels where that contrast exists, and it is wrong by the
aureole's whole azimuth structure on every face the sun is not in front of. Neither error is
visible in a single frame, both are visible the moment the sun moves, and both are cheaper to fix
than to detect: the integral is a few thousand directions against an environment already resident.

### The view from inside, and the split shot

The submerged view is the same water and the same code seen from the other side, which makes it the
strongest verification instrument a water renderer has: every above-water shortcut that survives by
being invisible from a downward view becomes visible from underneath. Three things invert.

- **Snell's window is the composition, and its rim is dispersive.** The whole above-water world
  compresses into a cone of half angle `asin(1/n)` — 48.5° at green, 97° across — and outside it the
  surface is a **perfect mirror**, reflectance exactly 1, showing the bed and walls folded back
  down. There is no partial regime out there, which makes the rim the hardest edge in the frame.
  On an IOR triple of 1.3320/1.3348/1.3400 the critical angle runs 48.655°/48.519°/48.268°, a
  **0.39° fringe** with red outside blue (`D`) — the same three constants that fringe the caustics,
  now landing on a hard edge instead of a soft one.
- **Absorption acts along the *view* path for the first time**, so it reads as aerial perspective:
  at `a = (0.264, 0.0565, 0.0092) m⁻¹` transmission over 5 m is `(0.27, 0.75, 0.96)`, and far
  geometry loses three quarters of its red with contrast falling as it goes. That bounds this
  chapter's own [pool-optics claim](#pool-optics-the-colour-is-the-bottom-not-the-water): *the
  colour is the bottom, not the water* is a statement about a view from above, and from inside it
  is false.
- **Anything touching the surface from below carries a mirrored twin**, because the underside is a
  mirror right up to the waterline: a wall, a step or a float meets its own image there,
  corrugations and all. It is the most recognisable underwater cue after the window itself, and it
  comes free from the same surface that writes the caustics.

**The split shot — half in, half out — is a property of the port, not of the camera.** A
mathematical point aperture at the datum gives a straight, degenerate split; a real front element of
finite radius gives the waterline **traced across the port**, a curve that undulates with the
passing waves and rides up and down them. So the port must be modelled explicitly, and which port
is visible in the result: a **flat port** refracts, so the submerged half reads at `d/n` — 25%
closer, 33% larger, field narrowing from 46° to ≈34° — while a **dome** restores the submerged half
and narrows the **air** half instead. **No port leaves both halves native.** That yields the
cheapest hard check in underwater rendering: one straight edge crossing the waterline — a wall, a
coping, a mooring line — must **step in scale** through a flat port and run **unbroken** through a
dome. A frame whose halves match while claiming a flat port has not chosen a port at all. And the
magnification is the *interface*, not the water: a camera fully submerged with no port sees none,
because nothing refracts between it and the subject.

### What the window actually contains, and why the rim is where the world is

The section above says the above-water world compresses into a 97°-wide cone. This one says **where
inside that cone it lands**, because that is not uniform, and the non-uniformity decides how an
underwater frame is sampled and what an overhead occluder is worth. The map is Snell's law
differentiated, and it is derived in
[`12a` §7](12a-water-derivations.md#the-window-from-below-snells-jacobian-and-where-the-horizon-goes):

```
dOmega_w / dOmega_a  =  cos(theta_a) / ( n^2 cos(theta_w) )        theta_a = angle in AIR
                                                                   theta_w = angle in WATER
INT over the air hemisphere  =  2 pi (1 - cos theta_c)  =  2.12139 sr        at n = 1.3348
```

**The law: refraction crushes the whole low-elevation air world into a narrow annulus just inside
the rim.** The numerator vanishes at grazing, so the concentration diverges there:

| air, `θ_a` from vertical | elevation | lands at `θ_w` | share of the **air hemisphere** beyond it | share of the **window** beyond it |
|---|---|---|---|---|
| 60° | 30° | 40.45° | 50.00% | 29.20% |
| 70° | 20° | 44.75° | 34.20% | 14.17% |
| 80° | 10° | 47.54° | 17.36% | **3.75%** |
| 85° | 5° | 48.27° | 8.72% | **0.95%** |
| 89° | 1° | 48.51° | 1.75% | **0.04%** |

(`D`, closed form recomputed here.) Half the sky sits in the outer 29% of the window; everything
under 10° of elevation — which is where a shoreline, a jetty, a hull, a person at the pool edge and
the horizon itself all live — is inside **3.75%** of it.

**So an environment lookup indexed naively from below is wrong in a specific direction.** Spread
samples uniformly in `θ_w`, or uniformly across the window disc, or over an equal-area map of the
*water-side* hemisphere, and the resolution follows `dΩ_w`, which is the wrong measure by exactly
that Jacobian. Priced on a `θ_w`-uniform radial map: the innermost 10° of `θ_w` takes **20.6%** of
the radial samples for **2.72%** of the air hemisphere (over-served 7.6×, and it is the zenith, where
a sky is smooth and slowly varying), while the outermost 1° takes **2.06%** for **17.58%**
(starved 8.5×, and it is where the entire horizon is stacked). The correct radial variable is the
**air-side cosine**, `v = cos θ_a = √(1 − n² sin²θ_w)`, which runs 1 at the centre to 0 at the rim
and is uniform in air solid angle by construction. The operational form is shorter than the algebra:
**refract first, look up second** — index the environment by the air direction and let Snell's law
choose the sample. A cached window-space disc is only defensible if its radial coordinate is `v`.

**What is actually up there, measured two ways.** On this chapter's reference pool — a basin under a
shade sail, with a coping, a deck and a float — the window's solid angle divides as (`D`):

| what a refracted ray finds above the water | route 1 · off the frame | route 2 · off the hemisphere |
|---|---|---|
| the pool's own edge — band, bead, bullnose, in section | 0.4520% | **0.9888%** |
| the shade sail | 0.3025% | **0.0660%** |
| a float on the surface | 0.2406% | **0.0697%** |
| still sky | 99.0049% | **98.8755%** |

Route 1 weights every transmitting subsample of a rendered underwater frame by the solid angle a
rectilinear pixel subtends (`cos³` of the angle off the optical axis). Route 2 never touches a
camera: it samples the **air** hemisphere stratified in `cos θ_a` from points on the surface and
weights each direction by the Jacobian above — the estimator closing on **2.12138 sr** against the
window's own **2.12139 sr**, which is what makes those percentages shares *of* something.

**Two things fall out, and the second is the one nobody predicts.** The sail was expected to be a
large dark shape overhead and is not: it stands 8–12 m away and 2.4 m up, and subtends **72–77° from
the vertical in air** (measured across the panel; a bare `atan(2.4 / 8…12)` from a point *on* the
surface gives 73.3–78.7°, and the degree between them is the observer's own depth). Snell compresses
that whole band into **1.44°** of polar angle just inside the rim. It is a
real dark shape, it is legible in the frame, and it is a **fifteenth of a percent** of the window.
What dominates instead is **the basin's own edge section, seen at grazing all the way round** — the
freeboard band, the bead and the bullnose, in section, at 15× the sail. The general form of that is
the law above: at 72° in air a receiver is already inside the outer 12% of the window, and *every*
horizontal direction the observer has is stacked there.

**And the deck is not reachable from below at all**, which is the shape of the answer rather than a
detail. An upgoing ray in air that has cleared the coping never comes back down, and one that has not
cleared it met the vertical face first — so a poolside window contains the coping **in section** and
no paving, whatever the paving is made of. That is a geometric statement about any raised edge, and
on the reference implementation it is asserted against a 0.2 mm march of the edge profile rather than
argued (`D`).

**The two routes disagree by up to 4.6× on individual entries and agree on the total to 0.13
percentage points, and that is not a discrepancy.** A frame samples what its camera happens to see —
here the sail and the float are both in shot and most of the far coping is not — so route 1 answers
*what is this picture spending its window on*, a cost and visibility question. Route 2 samples the
hemisphere, so it answers *what does the window contain*, a property of the scene and the interface
with no camera in it. **Quote route 1 for a budget, route 2 for the physics, and never take an entry
from one against a total from the other.** That generalises past water: any percentage measured by
binning a render is conditioned on the framing, and the fix is not a better frame but a second
estimator that has no frame at all.

`?` What is still open on the reference implementation's own audit: **neither route guards the
other** — they are two reports, not a check — and the only guarded quantity in the pair is the
Jacobian's closure. A binning error common to both would not show.

### Water-body optical identity: where the IOPs come from

Most water shaders expose one lumped `sigma` and a scatter colour as art-directed swatches. Both
are the wrong shape: the quantities underneath are **inherent optical properties**, they are
measured rather than picked, and taking them from oceanography instead of from a colour picker is
the cheapest realism win in the whole chapter — it is what separates "blue-tinted glass" from
*this specific water*. (`sigma` is also worth retiring on its own account: this chapter needs the
symbol for surface tension and for per-axis rms slope, both standard uses, and a third meaning
invented for extinction collides with both.) The generation-side producer of this descriptor is
terrain-architect's liquid property bundle (its `28`, exported as `liquidBody[i]` in its
`08`/`27` contract) — when the pipeline ships it, consume it rather than re-authoring; this
section is the theory for reviewing those values and the fallback for pipelines that lack them.

**Pure water is blue for a spectroscopic reason.** Its visible absorption is the high-order
overtone band of the O–H stretch — vibrational, not electronic — which is why absorption is
minimal in the blue and climbs steeply into the red. Pope & Fry's measurements put the minimum
at **0.0044 m⁻¹ at 418 nm**, against **0.62 m⁻¹ at 700 nm**: red is ~140× more strongly absorbed
than blue-violet. In practice red is gone by ~5 m, orange by ~10 m, yellow by ~20 m, green by
~40 m. That single ratio is the entire shallow→deep colour ramp, and it is *not* sky reflection.

```
c_RGB     =  (a + b) evaluated at ~610 / ~550 / ~450 nm     # beam attenuation, the IOP
a_water   ~= (0.264, 0.0565, 0.0092) m^-1   # pure water at 610/550/450 nm, Pope & Fry 1997
#   the absolute minimum is 0.0044 m^-1 at 418 nm - deep violet, below a typical B channel
#   THE WAVELENGTHS ARE PART OF THE CONSTANT. a climbs 4% per 10 nm on the red shoulder and
#   19% per 10 nm on the green one, so the SAME water at 620/545/460 nm is
#   (0.2755, 0.0511, 0.0098). Quote the sample points with the numbers, always
```

**And a sampling point is not the only defensible reading of that curve.** A camera channel is a
*band*, not a wavelength, so the quantity a renderer wants is `a` averaged over the band it actually
integrates. Over the Voronoi cells of 620/545/460 nm — 582.5–657.5, 502.5–582.5, 417.5–502.5 nm,
tiling with no gap and no overlap — the same Pope & Fry table gives

```
a_band ~= (0.2617, 0.05299, 0.01022) m^-1     # Pope & Fry 1997, averaged over the three bands
```

which is what `reference-impl/render.py` ships, and which differs from the point sample at those same
nominal wavelengths by 5.0% / 3.7% / 4.4%, with the red sign opposite to the green and blue. Take
whichever matches how the rest of the renderer samples spectrum — a three-delta model wants the point
values, a band model wants these — but **take one, say which, and never present the two triples as
competing waters.** They are one measurement read two ways, and the difference between them is the
curvature of `a(λ)`, not a disagreement about water. (A band mean of `a` is itself an approximation:
Beer–Lambert over a band is `−ln⟨exp(−a(λ)L)⟩`, not `⟨a⟩L`, and the two separate by ~1% of the red
channel's transmittance over a 4 m path. It is first-order right where a point sample is not.)

**A natural water is four optically significant components, and they add.** Pure water is always
present and never varies; the other three are the shader's actual authoring dials, because each has
a *distinct* visual signature:

| Constituent | Absorbs | Scatters | Reads as |
|---|---|---|---|
| **Pure water** | strongly in red, `a(610) = 0.264 m⁻¹` | molecularly, of order 10⁻³ m⁻¹ (`?`, not verified here) | The cyan. The floor of every water |
| **Chlorophyll** (phytoplankton) | blue (~440 nm) *and* red (~675 nm), leaving a window at 550–570 nm | by the cells | Green. Productive lakes, coastal blooms; pea-soup opaque at high load |
| **CDOM** / tannins / "gelbstoff" | steeply toward blue, `a(λ) = a₄₄₀·exp[−S(λ−440)]`, `S ≈ 0.012–0.022 nm⁻¹` | **nothing at all** — it is dissolved | Transparent but *dark*. Tea/amber shallow, near-black deep |
| **Non-algal particles** (mineral sediment) | weakly, a similar exponential | **strongly**, near spectrally *flat* (`b_b ∝ λ^−0.5…−1` vs λ^−4.3 for water molecules) | Turbidity, haze, milkiness. Turquoise → green → ochre as load climbs |

The critical distinction for a shader author: **CDOM darkens, sediment brightens.** They are not
interchangeable "murkiness" sliders — they are two independent axes that look nothing alike, brown
and *clear* (a peat river: you can see the bottom, it is just brown) against pale and *opaque* (a
stirred estuary). Blackwater (Rio Negro, `a_CDOM(440) ≈ 9 m⁻¹`) kills blue within ~11 cm but passes
red to ~1.4 m — so it reads amber in the shallows and, because CDOM contributes *no* backscatter,
near-black and mirror-like over the channel. Collapsing the two into one turbidity slider is the
single most common way to make water look wrong, and it produces mud in both directions.

**The Case 1 / Case 2 split is a count of free parameters, not a taxonomy.** *Case 1* waters — the
open ocean — have everything covarying with chlorophyll, so **one number** describes them. *Case 2*
— coastal, lake, river, estuary — have CDOM and particles varying independently of the plankton and
of each other, so **three**. A treated swimming pool is the degenerate point where all three are
≈ 0, which is exactly why the `b_b ≈ 0` of
[Pool optics](#pool-optics-the-colour-is-the-bottom-not-the-water) holds there and nowhere else.
Deciding which case a body is in decides how many dials its descriptor needs, before any spectrum
is picked.

**So take concentrations, not coefficients.** `a`, `b` and `g` are nine numbers across RGB and most
of their combinations correspond to no water that exists; three or four constituent loads are fewer
numbers, and **every** combination of them is a water that does. The spectra are literature rather
than art direction. The `a`/`b`/`g` split this chapter asks of `liquidBody` is what a constituent
model should *feed*; it is not what should be handed to an author.

**The number that makes the case.** At this chapter's own three sample points, a modest CDOM load
of `a_g(440) = 0.20 m⁻¹` on the standard exponential (`S = 0.014 nm⁻¹`) adds:

| m⁻¹ | R 610 | G 550 | B 450 |
|---|---|---|---|
| pure water | 0.2644 | 0.0565 | 0.0092 |
| + that CDOM | +0.0185 | +0.0429 | **+0.1739** |

It multiplies **blue** absorption by **20×** and raises red by 7%. That is the whole difference
between a peaty lake and a swimming pool — the same mechanism run from the other end. A pool
subtracts red and reads cyan; a lake subtracts blue and reads brown. Nothing else needs to change,
and a renderer reaching for a brown *tint* has abandoned machinery it already has.

**It also sharpens the band warning above.** These spectra are far steeper than pure water's — an
exponential in CDOM, narrow peaks in chlorophyll — so sampling them at three delta wavelengths is
worse here than anywhere else in this chapter, and for the reason
[A channel is a band](#a-channel-is-a-band-not-a-wavelength) gives: **a channel is a band, and the
steeper the spectrum the more that matters.**

**Glacial turquoise is not Rayleigh scattering.** This is stated all over the web and is
physically impossible: rock flour is 2–65 µm, 10–100× the wavelength, firmly in the Mie/geometric
regime where scattering is nearly *wavelength-independent*. The real mechanism is a two-step:
flat-spectrum backscatter shortens the mean photon path to order a metre, and over that short
path `a_water` still removes red efficiently while barely touching blue-green. Concentration is
therefore the *hue* knob — more flour shifts it paler and greener, less goes deeper blue — which
is exactly why proglacial lake chains get bluer downstream as flour settles out, and why the same
lake drifts in hue across the melt season.

**Authoring handle: Secchi depth.** The cleanest bridge between an artist-legible dial and the
shader is `Z_SD ≈ 1 / min_λ K_d` (Lee et al. 2015) — "you can see four metres down" fixes the
minimum of the diffuse attenuation spectrum, and *which wavelength* that minimum sits at is the
water's hue. Author clarity plus a water class; solve for the IOPs.

**One trap worth stating:** `c = a + b` (beam attenuation) and `K_d` (diffuse attenuation) are
different coefficients, and `c` is typically 5–20× larger because forward scattering dominates
(`b_f` ≳ 50·`b_b`). Use `c` for a *sharp sightline* — how fast a submerged object's own radiance
is lost, i.e. refracted lookthrough — and `K_d` for the *diffuse light column*, i.e. depth-tinted
volumetric fog. Driving both from one constant makes water look far murkier than it is.

**And a transmitted path is an instrument, so the trap has a second half: the forward glow is not
Beer–Lambert, and reading `c` off a path that contains it is biased low by a quarter.** The way
anyone recovers `c` from a picture or a buffer is the cuvette relation
`c = −ln(T₂/T₁)/(L₂ − L₁)` — two thicknesses of the same water, everything multiplicative
cancelling. It is exact, and it is exact only on the *transmitted* term. A single-scattering source
inside the slab integrates to something with a different shape entirely:

```
L_glow = ∫₀^L  b·p(Θ)·E · e^{−c(L−s)} · e^{−cs} ds  =  b·p(Θ)·E · L · e^{−cL}
#                    \_______/  \_____/
#                     in to s   out from s      -- the two exponentials multiply to e^{-cL},
#                                                  independent of s, so the integral is just L
```

**Linear in `L` times the exponential, not the exponential.** It rises out of zero, peaks at
`L = 1/c` and falls — so it is *brightest* where a naive reading assumes the signal is weakest, and
the cuvette picks up an extra term that depends only on the two thicknesses:

```
−ln(T₂/T₁)/(L₂−L₁)  =  c  −  ln(L₂/L₁)/(L₂−L₁) · (the glow's share of the signal)
#   at L1 = 1 m, L2 = 3 m the bias coefficient is ln(3)/2 = 0.5493 m^-1, and it is SUBTRACTED
```

Measured on the reference implementation's backlit wedge, where the glow is **5.07% of the pixel**
and every other term is the scene's own (`D`, `beach_render.py`, from the scene-linear buffer):

| what is in the signal | `c` red | `c` green | `c` blue | error |
|---|---|---|---|---|
| put in (`a + b`) | 0.28356 | 0.08560 | 0.16191 | — |
| **transmitted only** | 0.28356 | 0.08560 | 0.16191 | **0.0 / 0.0 / 0.0 %** |
| **+ the forward glow** | 0.26822 | 0.06480 | 0.13630 | −5.4 / **−24.3** / −15.8 % |
| **+ the front face's own reflection** | 0.26263 | 0.06386 | 0.13367 | −7.4 / −25.4 / −17.4 % |

⚠️ **Five per cent of forward-scattered light costs a quarter of the green coefficient** — and green
is the band the whole colour argument of this section lives in, so the error lands where it does the
most damage. Read the table in absolute terms and it is clear why green loses: the bias subtracted
is **0.0153 / 0.0208 / 0.0256 m⁻¹** in red / green / blue — the same order in all three — while `c`
itself spans 0.28 to 0.086. **A roughly band-independent subtraction from a strongly band-dependent
quantity is largest, in relative terms, wherever the water is clearest**, and for water that is
green. Three consequences, and the third is the one that generalises:

1. **Separate the glow before inverting.** Two thicknesses give one equation; a scattering
   contaminant makes it two unknowns. Either measure where the glow is identically zero — the same
   wedge front-lit reads **0.00%** glow, because the sun cannot reach the back face at all — or
   model `L·e^{−cL}` and fit both.
2. **`b_f ≳ 50·b_b` is what makes this unavoidable.** The same inequality that makes `c` 5–20×
   `K_d` puts nearly all the scattered light *forward*, i.e. into the transmitted sightline. There
   is no water for which the glow is small because the scattering is.
3. **Any transmitted path used as a measurement inherits this**, not just a cuvette: a sun shaft
   read for optical depth, a backlit wave face read for a green grade, a submerged object's contrast
   read for visibility. If the path is backlit, the glow *is* the picture, and the instrument is
   measuring something other than what it is named after until the glow is taken out of it.

**Clear does not mean bright.** Reflectance goes as `b_b/a`; in the clearest water `b_b` is
molecular only and tiny, so deep clear water returns almost nothing and reads **near-black with a
blue cast**, with all apparent brightness coming off the surface. Shallow clear water over bright
sand is luminous cyan because the *bottom* is the return path. A shader that maps "clear →
bright cyan" gets the tropical shallows right and the drop-off catastrophically wrong; the reef
edge is exactly where `b_b` stops being bottom-dominated and becomes molecular.

**Turbidity is a missing axis, not a missing feature — and its symptoms arrive out of order.**
Everything above treats `b` as a stated near-zero, and it is the one parameter a pool, a lake, a
river mouth and a stirred estuary genuinely differ by. It is `b` and `g` — `transmission_scatter`
and `transmission_scatter_anisotropy` on the material side — and never a single scalar, whatever
the NTU meter reads. Author it as a **visibility distance rather than as a coefficient**: nobody knows what `b = 0.35 m⁻¹` looks like, everybody knows "you can just
see the bottom". Bracketed at green (`a = 0.0565 m⁻¹`), with Secchi from `Z ≈ 1.44/(c + K_d)` and a
crude `K_d ≈ a + 0.02·b` (`?` — the backscatter ratio is a placeholder, and the Secchi column moves
with it):

| `b` m⁻¹ | reads as | `ω₀ = b/(a+b)` | Secchi (`?`) | caustic contrast |
|---|---|---|---|---|
| 0 | a treated pool | 0.00 | 12.7 m | 1.00 |
| 0.15 | faintly hazy | 0.73 | 5.4 m | 0.75 |
| **0.35** | **caustics half gone** | 0.86 | 3.1 m | **0.50** |
| 0.90 | bottom lost at 1.4 m | 0.94 | 1.4 m | 0.17 |
| 3.0 | milky | 0.98 | 0.45 m | 0.00 |

Caustic contrast is the unscattered fraction along the *sun* path, `exp(−b·L)` — here the 1.96 m
slant of a 1.40 m pool under a 21° sun — so it **halves at `b ≈ 0.35 m⁻¹`**, where the Secchi depth
is still three metres and the bottom is perfectly visible. The order that produces is not the order
a reader expects:

1. **the caustic net fades first**, while the water still looks clear;
2. then shadows lift, because scattering *adds* where absorption only subtracts;
3. then distance hazes and the bed loses contrast;
4. then the water takes on a body colour and reads milky rather than tinted;
5. and from below, Snell's window loses its rim.

A renderer that reaches for a white tint at step 4 has skipped the three steps that actually sell
it — and steps 1–3 are cheap: a contrast multiplier on the existing caustic pass plus a
depth-dependent haze, no volumetric integration at all. That is the low tier of the ladder; the
high tier is the same single-scattering machinery a submerged lamp or a bubble plume needs. Note
also where `ω₀` sits by the time the water is only *faintly* hazy: 0.73. **Scattering takes over the
light budget long before it takes over the look**, which is why "treated water barely scatters"
describes a very narrow regime and should be written as one.

**In the surf zone an IOP stops being a material input and becomes a state variable.** Everything
above treats `a`, `b` and `g` as a description of *the water*: constants of a body, authored or
measured once, uniform over it. That is true of a pool, true of a lake, true of the open ocean —
and **false in the swash zone**, where the waves suspend the bed, the **backwash** is the erosive
half of the swash cycle, and turbidity therefore **pulses with each wave**. The IOPs become a field
produced by the dynamics that also produce the surface:

```
db/dt  +  u . grad b   =   E(tau_bed, ...)  -  w_s * b / d          # suspend, advect, settle
                            \___________/      \________/
                             entrainment,       settling at
                             set by bed shear   the fall velocity
```

**This is a change in what kind of quantity an IOP is, not an extra term**, and it has three
consequences a renderer feels before it feels the equation. `b` is now **coupled to the wave field**
rather than authored beside it, so a shader reading a constant is reading a quantity that no longer
exists. It is **spatially structured** — a turbid band along the break line against clear water
outside it, which is a strong composition cue and unreachable from any single value. And it is
**periodic at the wave period**, so it is the one optical property a still frame cannot verify and a
two-second clip settles immediately. The pool sits at the degenerate end of the same equation with
`E = 0`, which is exactly why `b_b ≈ 0` holds there and nowhere in the surf; the
[confusable pair](#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot)
under Shallow water is how to tell the resulting veil from a shallow bottom in a frame. (The
entrainment law and the fall velocity are sediment transport, not rendering, and both are `?` here.)

**Presets.** Jerlov's water types (oceanic I, IA, IB, II, III; coastal 1C–9C) are the standard
classification, defined by the spectral shape of `K_d`, and Morel's chlorophyll ladder maps them
to a look (type I ≈ 0–0.01 mg/m³, deepest blue; III ≈ 1.5–2.0, green and productive). Ship them
as named presets rather than as sliders. Honest caveat: the numeric `K_d(λ)` tables live in
Jerlov (1976) Tables XXVI–XXVII and Solonenko & Mobley (2015), both paywalled — the values
circulating in blog posts and asset packs are mostly untraced. Either extract them from the
source, or generate the oceanic series by running the Solonenko & Mobley `K_d(a,b)` relation
forward from the chlorophyll ladder, and say which you did.

### Sun glitter: the sparkle path

`sun_glint` in the composition formula above is not a decorative extra — it is the single
brightest thing on a sunlit sea, and getting it wrong is the most common reason ocean renders
read as vinyl. The failure is structural, not a tuning problem.

**The physics.** The sun's disc subtends **0.53°** — about 1/8000 of the hemisphere. The
sea-surface slope distribution is enormously wider: Cox & Munk photographed sun glitter from
aircraft and fitted mean-square slope against wind speed,

```
sigma_c^2 = 0.003 + 1.92e-3 * W        # crosswind component   -- PER-AXIS variance
sigma_u^2 = 0.000 + 3.16e-3 * W        # up/downwind component -- PER-AXIS variance
sigma_c^2 + sigma_u^2 = s^2 = 0.003 + 5.12e-3 * W       # the TOTAL mss; s = rms slope
#   W = wind speed in m/s AT 12.5 m (not the 10 m of standard wind data — convert)
#   valid 1-14 m/s; at 14 m/s s^2 ~= (tan 16 deg)^2, i.e. total rms slope s ~= 0.28
```

so the reflected-direction spread is **tens of degrees** while the source is a fraction of one.
The distribution is *anisotropic* — `sigma_u^2/sigma_c^2` averages about 1.34, ranging 1.0–1.8
with steadier wind giving stronger anisotropy — so the glitter pattern is an ellipse elongated
along the wind, not a disc.

**Why the naive version inverts the physics.** A sharp specular lobe (high Blinn-Phong exponent,
low GGX alpha) on a normal-mapped surface produces one small blown-out highlight where the mirror
direction lands. Reality is the opposite: a *glitter path* stretching tens of degrees toward the
observer, made of thousands of individually resolvable facets winking on and off. A tight lobe is
not "glitter that needs more contrast" — it is the wrong shape of function.

**And the *source* has to be a disc, or there is nothing to glitter with.** The lobe shape is only
half the problem; the other half is what the environment says the sun is, and a `cos^n` "sun"
fitted by eye is an **aureole, not a disc**. The error is enormous rather than marginal: audited on
a reference implementation, the hand-fitted lobe peaked **1563× below** the sun's own radiance over
a solid angle **7.8× too wide**, and all three sky lobes together carried **0.695 against a direct
beam of 24.1** — a factor of 35 short (`D`). The symptom is not a dim sun. It is that glitter comes
out as a **broad pale smear** where the physics has small blinding points, which presents as a
tuning problem and is not one.

Constrain it so nothing is left to choose. A `cos^n` lobe carries `2π/(n+1)` over the hemisphere,
so `n = 2/θ_s² − 1` makes that flux identically `Ω_sun = π·θ_s²`; giving the lobe a peak of
`L_sun = E_n/Ω_sun` then makes its flux equal the direct beam exactly. Peak, width and flux land on
the sun together and there is no amplitude left to pick. At the solar angular radius
`θ_s = 0.265°` that is `n ≈ 93 500` and `Ω_sun = 6.72×10⁻⁵ sr` (`P`, arithmetic recomputed here).
The environment's sun and the directional light that casts the shadows then become **one quantity**,
which is the property a glitter path needs and a fitted lobe cannot have.

The rest of that argument belongs to `10` and is worth reading before building any sky for water to
reflect: the environment must be **the atmosphere the beam came through**, and a sun colour already
encodes its own air mass.

**Three tiers, and the first two are not alternatives.**

| Tier | Mechanism | Use |
|---|---|---|
| Statistical BRDF | Evaluate a microfacet BRDF whose NDF **is** the Cox–Munk anisotropic Gaussian, with Smith masking. Ross et al. 2005 is the standard analytic form; it is what Bruneton's ocean uses | **The base. Always.** Correct energy and lobe width at every distance |
| Discrete glints | Count actual facets reflecting toward the eye within the pixel footprint — Deliot & Belcour's binomial-law method is the current real-time state of the art | Near-to-mid field, where individual sparkles resolve |
| Noise-perturbed specular | Scroll a noise texture through the specular term | Indie tier. Cheap, reads acceptably, physically unfounded |

Tier 1 gives correct *statistics*; tier 2 gives correct *granularity*. Shipping tier 2 alone
gives sparkle that does not integrate to the right brightness; shipping tier 1 alone gives a
correct but slightly too-smooth glitter path in the near field. Production is tier 1 everywhere
plus tier 2 within a fade radius.

**And all three tiers are single-bounce, which at a low sun loses a tenth of the light the surface
intercepts.** This is not a tier — it is a term missing from every one of them, and it is
measurable. Integrate the flux the tilted facets intercept from the beam,
`∫ ρ_F(ω) cos ω · p(z)/cos β dz` over slope space, and integrate the radiance a Cox–Munk glitter
model *produces* over the upward hemisphere: the two share nothing but the slope pdf and they agree
to **7×10⁻⁵ relative** (`D`, and that agreement is the Jacobian `dω_v = 4 cos ω cos³β dz` and
nothing else) — **but only after restricting the first to facets whose mirror direction points
up.** The rest is real light going somewhere:

| sun elevation | `U₁₂.₅` = 3 m/s | 6 m/s | 12 m/s |
|---|---|---|---|
| 10° | 10.4% | 12.1% | 12.5% |
| **21°** | 3.7% | **10.3%** | 18.0% |
| 30° | 0.5% | 4.1% | 13.3% |
| 45° | 0.00% | 0.2% | 3.1% |
| 60° | 0.00% | 0.00% | 0.2% |

Facets tilted far enough away from a low sun send their specular lobe **below the horizon** — into
the sea, or into the back of the next wave. A single-bounce model drops that light entirely, and it
is exactly the light a multiple-surface-bounce model puts back as the **faint filling between the
glints**: the reason a real glitter path has a floor between its sparkles and a rendered one has
black. Read the table's shape rather than any one cell — the loss is a **low-sun, high-wind**
phenomenon and it is *negligible above about 45°*, which is a scheduling fact as much as a physical
one. The shots that want a glitter path are exactly the shots where the term is largest.

**Check reachability before budgeting for glitter at all.** A glint needs the surface to supply the
normal that bisects sun and eye, and the surface can only supply what its slope distribution
contains. One half-vector settles it: `tilt = angle(normalize(L + V), up)`, read against the
**per-axis** rms slope `sigma = s/sqrt(2)` — this tail is Rayleigh in `sigma`, not in the total `s`.

```
tilt < ~2 sigma   a glitter path -- the classic shimmering road
tilt ~  3 sigma   sparse isolated glints; |grad h| of a 2D Gaussian slope field is Rayleigh,
                  so P(|grad h| > 3 sigma) = exp(-9/2) ~= 1%, far less of it aimed the right way
tilt > ~4 sigma   nothing. What the water shows there is sky reflection, not sun
```

**At low sun the test is brutally azimuth-sensitive — and that makes it invertible.** With the sun
low, both `L` and `V` are near-horizontal, so an azimuth miss translates almost fully into required
tilt. Holding the eye at the mirror elevation, an 18.75° azimuth error costs **23° of tilt at a 21°
sun, 7.8° at 50°, and 3.4° at 70°**: low-sun sparkle is pinned inside a narrow azimuth wedge, while
a high sun forgives a lot. Run the test backwards and a photograph becomes a **measurement**. The
geometry fixes the tilt the surface must supply, so the mere presence of sparkle puts a floor under
the local total rms slope, quoted beside the per-axis `sigma = s/sqrt(2)` the tail actually eats:

```
required tilt 17.8 deg (measured sun + measured camera bearing)
  s = 0.078  (sigma 0.055)  ->  5.7 sigma  ->  0.000 %  -> nothing visible
  s = 0.127  (sigma 0.090)  ->  3.5 sigma  ->  0.25  %  -> a sparse scatter of glints
  s = 0.156  (sigma 0.110)  ->  2.8 sigma  ->  1.8   %  -> a well-populated patch
```

So a sparkle patch beside glassy water is not a lighting accident: it localizes water roughly twice
as rough as its surroundings — a jet-stirred or gust-ruffled patch, and a calibration handle rather
than a knob.

The common trap is a **low sun with a high camera**, because the two constraints multiply: the
mirror elevation equals the sun's, *and* the observer must be near the anti-solar azimuth. A 21° sun
viewed from a balcony 40° up and 70° off that azimuth needs ~47° of tilt — fifteen sigma at the
table's top row, which is not "rare" but *never*. Move the same camera into the anti-solar azimuth
and the requirement drops to ~9.5°, 3 sigma, and sparse glints appear. Two payoffs: do not spend a
glitter tier on a shot that cannot show one, and when matching reference photography, the
**presence, sparsity or absence of sparkle reads back the camera's azimuth relative to the sun** — a
free forensic check on a plate before you start tuning anything.

**Read as a layout constraint it is stronger still, and cheaper than anything it decides.** All
specular structure lies on **one line in plan** — the sun's bearing through the eye — so the test
constrains where a camera may *stand*, not merely what it will see:

- **The mirror point cannot be removed.** Where the required tilt is zero, the mean surface itself
  mirrors the sun, and zero is the mode of every slope distribution — so no amount of roughness,
  filtering or lobe amplitude deletes a broad road there. If it is in frame it is in the picture,
  and the only control is the aim.
- **A rough patch's glint window is a window, not a point.** A rougher patch only out-glints calm
  water past a contrast ratio, so its visible band sits at a *finite offset* either side of the
  mirror direction — a steep branch and a grazing one. On the reference pool that is
  `|θ_v − 21°|` between 15.3° and 18.5° for 10×–100× contrast (`D`): the sparkle sits beside the
  mirror band, never on it, which is why "put the camera on the highlight" finds nothing.
- **So the sun and the feature fix where the photographer may stand**, to within about half a metre
  laterally. That is the difference between a shot criterion being satisfiable and not, and it
  costs a page of arithmetic against a scene that costs weeks.

**Glitter is a filter applied to the wave field, not a texture applied to the water.** Note what
separates tiers 1 and 2 from tier 3: the first two are *functions of the slope field*, the third
is not. That is the whole distinction, and it is the same structural argument the Voronoi caustic
fails ([Caustics](#caustics-the-other-half-of-the-light-path)) — applied above the surface instead
of below it. A glint appears exactly where the surface normal is the half-vector between sun and
eye, which is a **level set of the slope field**: the sparkle sits on crest and trough lines, not
at independent random points. Four things follow, and each is a review test:

1. **It is trackable.** Individual glints ride specific crests and travel with them. Over a second
   of footage a viewer can follow one crest across the glitter path. Cell noise has no crests to
   follow. Freeze a frame and the fake and the real thing look alike — which is precisely why a
   noise-perturbed specular survives a screenshot review and dies on video. **The test for glitter
   is temporal, not spatial**; judge it on a pan, never on a still.
2. **It is dispersive, and that is the cheapest tell in the frame.** The field carries many scales
   at once and each moves at its own speed: `c = ω/k` from `ω² = (gk + (σ/ρ)k³)·tanh(kh)`, with the
   minimum at 23.12 cm/s / 1.712 cm — both derived from one `σ`, see
   [Calm water](#calm-water-the-low-energy-regime) — and rising in
   *both* directions from there. Across a pool-sized band — say 3 cm to 55 cm, entirely on the
   gravity side of that minimum — the long components outrun the short ones by roughly **4:1**
   (~0.25 m/s against ~0.93 m/s), so the eye sees fine ripples crawling while a longer swell
   sweeps through them. A scrolled texture — noise, Voronoi, authored caustic sheet — advects
   every scale at one velocity by construction and can never show this. Watch two scales at once
   for two seconds; that is the entire test.
3. **It is phase-locked to the caustics.** One slope field, two consumers: the same surface
   curvature that makes the glint above the water makes the fold below it. Drive glitter from a
   noise texture and the sparkle stops sitting above the bright line it caused — a mismatch that
   reads as wrong long before anyone can say why. This is the one-evaluator rule (`19`) applied to
   optics rather than to physics.
4. **The "cells" are interference, not cells.** With a single wave train the glitter is a set of
   parallel bands along the crests and the bed caustic is parallel stripes. Add trains from other
   directions and both become a mosaic that photographs like a cell tessellation. Nothing turned
   into noise — the components are all still there, still separable, still individually
   followable. Reading that mosaic as "a Voronoi pattern" and reaching for cell noise inverts
   cause and effect: the tessellated *look* is the output of a directional wave spectrum, and cell
   noise reproduces the look while discarding everything that generated it.

**Wind is a rendering parameter here, not just an animation one.** Because mean-square slope is a
function of wind speed, the glitter path *widens and dulls* as wind rises, and *narrows and
intensifies* as it drops. Wire the same wind that drives the wave spectrum into the glitter
variance or the two disagree — a mirror-calm sea with a wide glitter path is an instant tell.

**Stronger, and it is the reason the previous paragraph is not a matter of taste: the path's
angular width is a *readout* of the mean-square slope.** Not "related to" — proportional to its
square root, and tightly. Measured on `reference-impl/beach_optics.py`, where there is no spread
parameter to have chosen: `ρ_F` is the shared `optics.fresnel`, `E_n` is the shared atmosphere's
solar beam, `p` is the Cox–Munk slope pdf above, and the rest is the Jacobian
`dω_v = 4 cos ω · cos³β dz`, giving `L = ρ_F E_n p(z)/(4 cos⁴β cos θ_v)`. Sun at 21.02°, the eye at
10° of elevation, the full width at half maximum taken in view **azimuth** on the green band:

| `U₁₂.₅` | mss | rms slope `s` | path FWHM | FWHM / `s` |
|---|---|---|---|---|
| 3 m/s | 0.01824 | 0.1351 | 7.230° | **53.53** |
| 6 m/s | 0.03348 | 0.1830 | 9.792° | **53.52** |
| 10 m/s | 0.05380 | 0.2319 | 12.467° | **53.75** |
| 16 m/s | 0.08428 | 0.2903 | 15.802° | **54.43** |

**Constant to 1.7% over a factor of 5.3 in wind** (`D`, recomputed here). That constancy is the
whole argument: it makes the width a *measurement* of the wind rather than a look, and it is the
one thing a chosen spread parameter cannot reproduce, because a chosen number has no reason to
track `√mss` when the wind changes. Run it backwards and a photograph with a measurable glitter
width and a known sun and camera geometry yields a wind speed — the inverse of the regression
above, `U = (mss − 0.003)/5.08×10⁻³`, which is the same forensic move the reachability table makes
with sparsity, only continuous. (`5.08` rather than the `5.12` in the code block above is not a
typo and not a correction: the two **components** sum to `0.003 + 5.08×10⁻³ W`, while `5.12` is the
paper's *separately fitted* combined slope. They differ by 0.8% at any wind, inside Cox & Munk's own
±0.004 / ±0.002 — but a file that quotes both as if one implied the other has misread the source.
Invert with whichever one the forward model used.)

**And the path's *shape* is diagnostic too: it narrows toward the horizon while it brightens.** Same
sun, same wind (6 m/s), sweeping the view elevation down to the horizon:

| view elevation | FWHM in azimuth `Δφ` | as an angle on the sky `Δφ·cos θ` | peak radiance (green) | facet tilt at the half-max |
|---|---|---|---|---|
| 25° | **14.96°** | 13.56° | 13.6 | 8.9° |
| 21.02° (the mirror elevation) | 13.54° | 12.64° | 19.7 | 8.7° |
| 15° | 11.46° | 11.07° | 33.2 | 9.2° |
| 10° | 9.79° | 9.64° | 51.8 | 10.3° |
| 6° | 8.49° | 8.44° | 79.5 | 11.5° |
| 3° | 7.52° | 7.51° | 119.5 | 12.5° |
| 1.5° | 7.04° | 7.04° | 152.5 | 13.0° |
| 0.5° | 6.72° | 6.72° | 182.7 | 13.4° |
| 0.2° (the horizon) | **6.63°** | 6.63° | 193.4 | 13.5° |

**A factor of 2.26 narrower and 14.2× brighter, from the horizon to the near field, with one slope
distribution and one wind** (`D`). The last column is the mechanism stated as a number: the facet
tilt the path's own half-maximum asks for moves by only **1.55×** across that sweep while the
azimuth it occupies falls by **2.26×**. The same slopes are still there; they simply subtend a
different range of specular direction. Two pieces of geometry do it, and both are one line:

- **At the centre of the path the required facet tilt is `β₀ = |θ_sun − θ_view|/2`** — half the
  elevation difference, because the facet has to bisect them. It is 0 at the mirror elevation and
  climbs to 10.4° at the horizon, which is what walks the path's centre out onto the flank of the
  slope pdf.
- **The azimuth-to-tilt map steepens toward grazing.** Off-azimuth by `Δφ`, the half-vector
  acquires a horizontal component `≈ Δφ cos θ_view` against a vertical one `≈ sin θ_sun + sin
  θ_view`, so the denominator shrinks as the eye drops and a smaller azimuth excursion carries the
  facet through the same range of tilt. Fewer degrees of azimuth for the same slopes: a narrower
  path.

The brightening is the same geometry read on the other axis, and it does **not** decompose into one
term — worth saying, because the tempting single explanation is off by an order of magnitude. From
25° to 0.2°: the `1/cos θ_v` projection alone contributes **121×**, Fresnel at the steeper facet
**3.2×**, `1/cos⁴β` **1.07×** — and against them the slope pdf at the walked-out centre falls to
**0.37×** and Smith shadowing at a 0.2° view to **0.091×**. The product is 13.9, against 14.2
measured on the full profile (the residual is the peak not sitting exactly at `Δφ = 0`). Quote the
`1/cos θ_v` on its own and the path comes out **8.5× too bright** at the horizon.

![Five peak-normalised azimuth profiles of the glitter path, and its FWHM and peak against view elevation](figures/glitter-path-narrowing.png)

> **Figure 12·5 — the path's width is a function, and one number cannot be it.** `D`, and the
> underlying slope statistics are `P` (Cox & Munk 1954). Drawn by
> [`figures/make_figures.py`](figures/make_figures.py) (`fig_glitter_path`) by calling
> `reference-impl/beach_optics.py`'s `glitter_radiance` directly — the shipped Cox–Munk BRDF with
> its Smith shadowing, not a re-derivation. **Scene-linear radiance throughout**; the right panel's
> axis is the radiance itself, with no exposure and no tone curve, which is the only way the 14×
> is readable as a number rather than as a look. Green band, `U₁₂.₅ = 6 m/s`, sun at 21.02°.
> **Left:** five azimuth cuts, each normalised to **its own** peak, so the only thing the panel
> shows is *shape*. The path narrows monotonically as the eye drops, and it does so with **one
> slope distribution and one wind** — nothing in the model changes between the curves except where
> the camera is. **Middle and right:** the two columns of the table above, as two curves that go
> **opposite ways** — FWHM 14.90° → 6.60° (**2.258×** narrower) while the peak runs 13.6 → 193.4
> (**14.18×** brighter), reproducing the printed 2.26 and 14.2 from the implementation itself. A
> spread parameter is a single number and can be neither of these curves; that is the argument,
> and the two panels together are it.

⚠️ **So a glitter path of uniform width is wrong, and it is the default.** Anything that draws the
path as a stretched blob, a scrolled mask, or a lobe with one width applied along its length is
making a claim about the surface statistics that the surface statistics contradict — and it is
wrong in a way that is obvious once stated and almost never modelled, because the error is a shape
rather than a level and no exposure check sees it. The rule falls out of the two tables together:
**the path must come from the slope pdf and never from a spread parameter**, because a spread
parameter is a single number and the path's width is a *function* — of the wind through `√mss`, and
of the view elevation through the geometry above. One number cannot be both.

**Slicks are a slope-variance effect, not a colour effect.** Cox & Munk also measured oil-slicked
water: films damp capillary and short gravity waves, cutting total mean-square slope by a factor
of **2–3** and eliminating the skewness entirely. So an oil slick, a wind shadow behind an island,
or a current-convergence line should be rendered as a **local reduction of the slope-variance
field** — which makes it appear as a smooth mirror-like patch against rough sea — not as a dark
albedo decal. This is the mechanism behind every "glassy streak" on a real ocean.

### The meniscus line: where reachability cannot fail

Water climbs a wetted solid to `h = a·√(2(1 − sin θ))` on the capillary length `a = √(σ/ρg)` =
**2.73 mm** (clean water at 20 °C, `σ = 0.0728 N/m`, `ρ = 998 kg/m³`): **3.86 mm** of rise at
perfect wetting, 2.73 mm at a 30° contact angle (`?`, unmeasured). The fillet is a few capillary
lengths across, so over roughly **5–10 mm** the tilt runs continuously from 90° at the wall to 0° at
the flat surface, and that strip therefore holds **every** facet orientation — the specular
condition is met inside it for any light in the sky at any sun elevation. It is the one exception to
the reachability test above. On the open surface a far-field `s ≈ 0.056` (per-axis `s/√2` = 2.27°)
puts the 17.8° the measured sun-and-camera geometry above asks for at **7.8σ**, and the 34.5° a
straight-down view asks for at **15σ**: never, not rare. Hence a bright line at the waterline in nearly
every pool photograph, glassy open water included — and wherever a river meets stone or a lake a jetty.

That `s` is the *ensemble* figure — the quadrature sum of the band constants — and it is quoted
that way on purpose. Any 2 m patch of the same field measures **0.053 to 0.058** depending on where
it is taken, because a band synthesised from a few dozen discrete components has real sampling
spread and the shelter mask varies underneath it (`D`). Quote the ensemble, treat a patch reading as
one draw from it, and check that the conclusion survives the spread before publishing either: here
17.8° runs 7.6σ–8.3σ and 34.5° runs 14.7σ–16.1σ across the whole range, which is "never" throughout.
A doctrine that flips inside the sampling spread of its own measurement was never load-bearing.

**It is the bevel highlight, not inverse ambient occlusion.** Both promote a sub-pixel feature to a
shading term at a junction, but AO answers a *visibility* question and is an approximation, while
this answers an *orientation* question and is real geometry merely left unresolved. The relative is
the hard-surface edge highlight: a zero-radius edge never catches light and reads as fake, a
fraction of a millimetre of chamfer glints, because a swept edge passes through all normals. Both
are signs of one quantity, **curvature** — concave loses hemisphere and darkens, swept sweeps
normals and glints — and a meniscus is both, so a dark band against the wall carries a thin bright
line inside it. In the reference frames that band is probably dominated by the wall's **cast
shadow** at a 21° sun rather than by occlusion; both contribute, ratio unmeasured (`?`).

**Real-time form.** A thin strip on a known contour is a decal or a junction shader term, never a
simulation: walk the wetted contour, shade a band a few millimetres wide as **specular** catching sun
and sky, and below ~1 px clamp the screen width while scaling intensity by the same ratio, or it
aliases into a dashed line. An ambient or roughness lift is the standard miss — wrong category, and
it reads as a softened edge rather than the corner it is.

## Caustics: the other half of the light path

Sun glitter is the light that bounced *off* the surface; caustics are the same focusing mechanism
applied to the light that went *through* it. On open ocean they are a detail nobody looks at. On
any clear shallow body — a reef flat, a river bed, a pool — they are the most recognizable thing
water does, and the budget inverts accordingly ([Man-made water](#man-made-water-pools-tanks-and-channels)).

**The physics, in one equation.** Refraction maps each surface point `p` to the point `q(p)` it
illuminates on the bed. Flux is conserved along the ray tube, so receiver brightness is the
inverse of how much that map stretches area:

```
i      = -L                                    # propagation direction of the sunlight, z up
t(p)   = refract(i, n(p), 1.0/ior)             # Snell at the surface;  t.z < 0, heading down
q(p)   = p.xy + t(p).xy * (d(p) / -t(p).z)     # where that ray meets the bed, d = depth below p
E(q)   = E_sun / |det( dq/dp )|                # the caustic
```

Two consequences fall straight out, and both are load-bearing:

- **Caustics are a curvature quantity, not a normal quantity.** `dq/dp` contains `dn/dp` — the
  *second* derivative of the wave field, where surface shading is driven by the first. That is
  why a normal map with no coherent height behind it produces caustics that visibly do not belong
  to the surface above them, and why a normal map filtered one mip too far yields caustics that
  are far too smooth while the surface itself still looks fine.
- **The bright lines are where `det dq/dp` passes through zero** — the fold set of the map. This
  is catastrophe optics, and it fixes the *shape* of a real caustic network: for a map from a
  surface to a plane the only structurally stable singularities are **folds** (curves) and
  **cusps** (isolated points where two fold branches meet tangentially). A caustic network is
  therefore smooth bright curves that close, run off, or terminate in cusps. It is not a cell
  tessellation — which is the specific reason the Voronoi fake reads wrong.

### Caustics above the waterline, and why they are the sharper ones

Water throws caustics **upward** as well as down — onto a coping, a wall, a hull, a harbour arch,
the underside of a jetty. They are among the most recognisable things water does and they arrive by
**two different paths**, which must not be collapsed into one term.

- **Reflected.** The wavy surface is a curved *mirror*. It focuses exactly as a lens does — same
  ray-map Jacobian, same folds and cusps — and it costs one Fresnel reflection.
- **Transmitted (the water-out path).** Light that entered, lit the bed, came back up and refracted
  out. It carries the bed's own caustic net outward, and it costs `T · albedo · T / n²` plus the
  absorption of the round trip.

**The reflected path focuses eight times harder, and that is the number to remember.** A surface
slope `s` turns a refracted ray by `s(1 − 1/n) = 0.25s`, but a mirror tilted by `s` deflects by
`2s`. So against the bed's `F = 0.25·d·s·k` the reflected caustic runs

    F_reflected = 2·L·s·k          L = path from the water to the receiving surface

a ratio of **7.97** at water's IOR (`D`). At this chapter's own far-field figures — `s = 0.058`,
`λ_dom = 17 cm` — that puts a wall **0.30 m** from the water at the same focus the bed reaches at
**1.40 m**.

Three consequences follow, and the first is the one that gets rendered wrong:

- **Above-water caustics go past focus almost immediately.** At `L = 1 m`, `F_reflected ≈ 4.2` —
  the [unresolvable-wash rung](#the-focusing-number-which-regime-the-bed-is-in). So a crisp net on
  stone exists only within a few tens of centimetres of the water; beyond that it is a **wash of
  moving light with no cell structure**, and a renderer that projects the bed's net onto a distant
  wall is showing a pattern that is two rungs too sharp for its own geometry.
- **The reflected path usually dominates**, because the geometry that puts a surface near water is
  also the geometry that makes the reflection grazing, where Fresnel runs from 0.3 to 1 — while the
  transmitted path is paying two transmissions, a liner albedo, `1/n²` and a round trip of
  absorption. Build the mirror path first; the water-out path is the *colour*, not the brightness.
- **A low sun makes them streaks, not cells.** The mirror sends the beam back up at the sun's own
  elevation, so at 21° it strikes nearby vertical surfaces at a shallow angle and stretches the
  pattern along the wall — the long ropes of light on a harbour wall, not the net on a pool floor.

**And the sun angle gates the whole effect — twice, in the same direction.** The mirror returns
the beam at the sun's own elevation, so the elevation decides *where it lands*; and the Fresnel
reflectance of a horizontal surface rises steeply as the sun drops, so it also decides *how much
goes up at all*. The two compound, which is why above-water caustics are a **morning-and-evening
phenomenon** and why a renderer that shows them at noon is showing something that is not there.

| Sun elevation | Fresnel off the water | Beam leaves at | Height on a wall 1 m away | Band height |
|---|---|---|---|---|
| 10° | **0.349** | 10° | 0.18 m | 0.24 m |
| 21° | 0.123 | 21° | 0.38 m | 0.27 m |
| 35° | 0.044 | 35° | 0.70 m | 0.35 m |
| 50° | 0.025 | 50° | 1.19 m | 0.58 m |
| 70° | **0.021** | 70° | 2.75 m | 2.22 m |

A 21° sun therefore puts **5.9×** the energy on a nearby wall that a 70° sun does, and puts it in a
band a quarter of a metre tall at knee height instead of smeared over two metres above head height
(`D`). At high sun the reflected beam still exists — it just goes nearly straight up, which is why
the surfaces that keep their caustics at noon are **undersides**: a jetty, an arch, a hull, a
ceiling.

The band's *height* is the third reading of the reachability argument: the beam's angular spread is
**twice** the surface's rms slope, `2s = 6.6°` at this chapter's far-field figure, so a wall's lit
band measures the roughness directly. Glassy water gives a hard-edged stripe; a chop widens it and
softens its edges. Same inversion as [glitter](#sun-glitter-the-sparkle-path) and the
[Snell window's rim](#the-view-from-inside-and-the-split-shot) — the pattern is a readout of the
slope distribution, not a decoration on top of it.

**Real time:** this is the [existing caustic map](#the-tier-ladder) run once more with the *mirror*
direction in place of the refracted one, projected from the water's plane onto the receiving
geometry. No new machinery, and it obeys the same
[four gates](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) — in
particular the fourth: it is **irradiance on the receiver**, added to its lighting, never a
multiplier on its albedo.

### The focusing number: which regime the bed is in

Whether a body shows a crisp caustic net, a soft wash, or nothing much is not a matter of taste,
and it has a one-line estimate. **The name is this chapter's**, not a standard dimensionless group
([the vocabulary rule](#the-vocabulary-and-which-half-of-it-you-can-look-up)) — the ingredients
below are all standard, the bundling is ours, and it should not be cited as literature. A surface slope `s` turns the refracted ray by `s·(1 − 1/n)`, so at
depth `d` the receiver point moves by `d·s·(1 − 1/n)`; focusing happens when that displacement's
*gradient* reaches unity. With `k` the dominant wavenumber and `s` the band's **total** rms slope —
not the per-axis `σ = s/√2`, and never a single wave's `2πa/λ`; either lands you a rung or two up:

```
F = d * (1 - 1/n) * s * k        # water: 1 - 1/1.333 = 0.25, so F ~= 0.25 * d * s * k
    F << 1   below focus  -> a soft, wide brightness modulation; no network
    F ~  0.5 fold onset   -> the net just appears: present, soft-edged, low-contrast
    F ~= 1   at focus     -> the crisp net, folds and cusps resolved
    F >> 1   past focus   -> branches overlap into an unresolvable wash
```

(Near-normal sun; at low sun an obliquity factor enters and the pattern stretches along the sun
azimuth.) The onset rung is measured from the Jacobian, not interpolated: the folded fraction of bed
area runs 0.0% at `F ≈ 0.3`, 0.4% at 0.5, 7% at 0.8 and 19% at 1.1 (`D`) — the net arrives abruptly
below focus, and that onset, not focus, is where a photographed pool sits. Three practical readings:

- **Cell size on the receiver is of the order of the dominant wavelength**, so measuring caustic
  cells against a photograph is a direct readout of the wave field that produced them — a cheap
  calibration check when matching reference.
- **Lengthening the waves at fixed slope moves you *down* the ladder**, because `k` falls. "Lower
  the wave frequency" alone does not give bigger caustics; it gives fainter ones.
- **Holding the look while lengthening the waves costs `s ∝ λ`, i.e. amplitude `a = s/k ∝ λ²`.**
  Big crisp caustics require genuinely big waves — going from 16 cm to 50 cm at constant `F` is a
  ~10× rise in amplitude. A calm body cannot have a large-celled sharp net, and art direction that
  asks for one is asking for a contradiction.

### The tier ladder

| Tier | Mechanism | Verdict |
|---|---|---|
| **0 · Authored texture** | One or two scrolling caustic textures at different scales and speeds to hide the loop | What most engines' starter water ships. Wrong in one specific and visible way: uncorrelated with the surface above it — when the water goes calm, the caustics keep churning |
| **1 · Worley / Voronoi (`F2−F1`)** | Cellular noise, two octaves, animated feature points, small per-channel offset | The community default, and what most people mean by "a caustics shader". Cheap, passable in motion at distance, structurally wrong — below |
| **2 · Caustic map from the real wave field** | Rasterize the refracted receiver positions from the light's view and accumulate; folds appear for free wherever several rays land in one texel | **The recommended default.** Shah, Konttinen & Pattanaik's caustics mapping and Wyman & Davis's image-space technique are the canonical formulations; GPU Gems 1 ch. 2 is the water-specific version. Costs one light-view pass over the wave grid |
| **3 · Ray-traced / photon-mapped** | Photons traced through the surface (DXR), splatted or resampled | Hero water on RT hardware. Correct including multi-branch folds and the secondary caustics from total internal reflection. Theory routes to physically-based-rendering (`caustics.md`) |

**Why it resembles a caustic at all.** The resemblance is not a coincidence, and naming it tells
you exactly where the approximation stops. Propagate a wavefront and two different singular sets
appear: the **focal set**, where neighbouring rays cross and the ray-map Jacobian degenerates, and
the **cut locus**, where fronts of equal travel time arrive at a point from two directions. A
caustic is the focal set. `F2−F1` is the gap between the nearest and second-nearest seed distance,
so its ridge set is precisely the **cut locus** of a family of circular fronts expanding from those
seeds — and circular fronts never focus (the evolute of a circle is a single point), so a cell-noise
field contains no focal set whatsoever. Both are bright-line networks born of front propagation;
that is the whole of the similarity. The junction difference then follows by classification rather
than by tuning: a planar cut locus generically meets in **triple junctions**, a focal set
generically meets in **cusps**.

**Which is why the approximation does not converge.** Adding octaves, jittering the seeds harder,
or animating the feature points moves the field around *within the family of cut loci*; no amount
of refinement produces a focal set. Compare the physical path, where adding wave components makes
the fold network strictly more correct because they enter the same Jacobian. Voronoi is a
legitimate approximation of the **appearance** and not a low-order approximation of the
**mechanism** — budget it as a stand-in with a fixed quality ceiling, never as a base to improve
on. If the shot needs better caustics than the fake gives, the move is to change tier, not to
add octaves.

**What separates it on screen — and how to ship it anyway.** Worley `F2−F1` gives a
network of bright lines around dark cells, which is why it convinces on a still frame. Three
things separate it from the real thing, all of them consequences of the fold/cusp classification:

1. **The wrong junctions.** A Voronoi edge network meets in *triple junctions* — three edges at a
   vertex. A caustic network has none: fold curves meet only in **cusps**, where two branches join
   tangentially, and fold curves may also simply end. The eye reads the difference as "cracked
   glass" rather than "focused light" long before it can name it.
2. **Uniform brightness along an edge.** Real fold lines vary strongly in intensity along their
   length and blow out at cusps, because `det dq/dp` varies along the fold. Cell noise has no such
   structure — every edge is as bright as every other.
3. **No coupling to anything.** The pattern knows nothing of wind direction, wave anisotropy, or
   depth. The most visible symptom is the one Tier 0 shares: **on mirror-calm water it keeps
   animating**, where the correct answer is that a flat surface has a constant Jacobian and
   therefore produces no caustic structure at all — just uniform light on the bed.

If the budget demands it, ship it — but label it a fake in the material, scale cell size with
depth so it respects at least that one law, and drive its animation amplitude from the wave
amplitude so calm water goes flat.

### The masking contract — four gates, and the third is the one that gets skipped

```hlsl
float3 caustic = SampleCausticMap(worldPos, time) * causticStrength;
caustic *= 1.0 - saturate(verticalDepth / causticFadeDepth);  // 1. depth fade
caustic *= exp(-c_RGB * lightPathLength);                     // 2. extinction along the LIGHT path
caustic *= SunShadow(surfaceEntryPoint);                      // 3. sun must reach the SURFACE
sunLighting += caustic;                                       // 4. irradiance, never albedo
```

1. **Depth fade on `verticalDepth`**, not on `rayDistance` — the distinction drawn in
   [Shading and optics](#shading-and-optics). Two mechanisms converge on the same fade: extinction,
   and the fact that the fold pattern spreads and overlaps into an unresolvable wash past the
   focal depth.
2. **Extinction along the *light* path**, on beam attenuation `c` because a caustic is what is
   left of a collimated beam, and a different distance from the camera path
   already computed for refraction: `verticalDepth / cos(theta_t)` from surface to bed, with
   `theta_t` the refracted sun angle. Reuse `rayDistance` here and caustics fade with camera angle
   instead of sun angle — subtly wrong in every frame, and obviously wrong the moment the camera
   moves while the sun does not.
3. **Sun visibility sampled at the surface entry point, not at the receiver.** The occluder — a
   shade sail, a parasol, a diving board, a tree, the pool wall at low sun — blocks the ray
   *before* it enters the water, so the shadow test belongs to `p`, not `q`. Sampling the cascaded
   shadow map at the receiver is the near-miss version: near-correct at high sun, visibly wrong at
   low sun where entry and receiver points sit metres apart. Skipping the test altogether is the
   classic bug — **caustics crawling through the shadow on the bottom**. Nothing else in the frame
   announces "this is a scrolling texture" so loudly.
   **And the gate is fractional, not binary, whenever the occluder is fabric or foliage.** Shade
   cloth transmits roughly 15–30%, leaf canopy more, and the transmitted light is **diffuse** — so
   it lifts the shadowed water without putting any caustic structure into it. That splits this gate
   in two: the caustic term is still gated hard to zero, because no collimated beam survives the
   fabric, while an **ambient** term is added underneath it. Drive that term from the solid angle
   the panel subtends rather than from its footprint — a point two metres to the side still sees
   most of it, and a `1/(1 + (d/R)²)` falloff about the centroid is enough. Ship the binary
   version and the shadowed water goes far too dark, losing the cue that actually reads: under a
   shade sail the caustics vanish while the water stays luminous.
   **And a shadow on the bed fills in even when the occluder is perfectly opaque, by a mechanism
   that is not the occluder's at all.** The same slope field that writes the caustic net swings the
   refracted beam: a facet tilted by `ε` moves the transmitted direction by
   `|1 − cos θ_i/(n cos θ_t)|·ε` — **0.2508** at normal incidence, which is the `1 − 1/n` of [the
   focusing number](#the-focusing-number-which-regime-the-bed-is-in), and **0.6241** at this
   chapter's 21° sun, so a low sun wanders a shadow 2.5× harder than a high one. Over the slant to
   the bed that is a *displacement*: a one-axis slope rms of 0.0712 over 1.96 m moves the beam's
   landing point **87 mm** rms, against a floating ball's shadow only **221 mm** wide across the
   beam. Measured on that shadow: the geometric umbra is 0.0800 m², the umbra the caustic map
   actually holds is 0.0131 m² — **84% of it is filled in** — with bed radiance **72.8%** of the
   open floor inside it and the net's own contrast still **61.5%**, i.e. legible (`D`). The umbra's
   core is genuinely zero: a rubber ball transmits nothing. So *a shadow under water is a reduction
   rather than a hole* is true of **opaque** occluders too, and attributing it to translucency
   installs a second, wrong mechanism on top of a real one. **The net inside the shadow and the
   softness of its edge are one mechanism, and it is the mechanism that writes the caustics.**
   Diagnostic consequence: if a shadow's fill does not respond to sun elevation and to slope
   variance, it is being painted rather than transported.
4. **Caustics are irradiance.** They multiply the sun's contribution to the receiver's BRDF; they
   are not added to albedo or to the final colour. Backwards, and they survive into shadow, into
   ambient-only lighting and into fog, and they stop responding to exposure.

**They fall on everything below the surface, not on the terrain.** Project in world space onto
whatever the pass finds under the water plane — bed, walls, steps, props, swimmers. A caustic
decal projected only onto the terrain heightfield leaves every object in the water conspicuously
unlit by the brightest thing in the scene. The above-water counterpart — surface-reflected light
dancing on a wall or a hull — is a second, weaker caustic on the reflection side, cheap from the
same map and a strong cue for pools and harbours.

**Interiors too dark and shadows too bright at once means a missing directional bounce.** Worth
naming as a diagnostic, because each symptom alone reads as a tuning error and only the pair
identifies the mechanism: a single flat ambient standing in for inter-reflection **under**-fills
where a nearby bright surface should be bouncing (caustic cell interiors on the bed come out too
dark) and **over**-fills where nothing should be (an occluder's shadow on the water comes out too
bright). Errors of *opposite sign in one frame* are a missing transport path, never a constant that
needs raising — and no better constant fixes it, because the source varies: on the reference pool
the wall runs 2.2× in red from waterline to foot. Priced there, the walls take **35% of the bed's
cosine-weighted hemisphere on average and 77% at the worst texel**, with a flat sky ambient applied
over all of it, and **58%** of the total-internal-reflection return off the underside of the surface
meets a wall before it can get back out (`D`). In an enclosed body — a pool, a tank, a canal, a
harbour — the walls are a first-class light carrier, not a boundary condition.

**The same missing leg has a third symptom, and it gets filed as a material bug.** A submerged
vertical face that catches no direct sun — a step riser, the shaded side of a wall — is lit by that
flat ambient and by nothing else, so it renders dead and near-neutral while a grazing sky
reflection wins the pixel by default. Reaching for the material is the wrong move twice over,
because direct sun is not the answer either: on the reference pool only about **6% of a riser's arc
is both lit and visible**, and nowhere on it does `min(N·L, N·V)` exceed 0.10 (`D`). What is
missing is one bounce off the sunlit tread and floor a few centimetres in front of the face, and it
does not merely brighten the receiver — it **moves its colour**, and it is the only one of the two
terms that carries the caustic net onto a vertical surface. A riser lit by a flat ambient is a
riser with no net moving on it, which is the cheapest way to spot the defect in a still frame.

**And that bounce has a hard ceiling, which is the other half of the same diagnostic.** A
Lambertian surface's radiance is **view-independent**, so a neighbouring surface cannot concentrate
its light — it can only re-emit what it absorbs. The form factor from a point on a wall to the
adjoining infinite floor is exactly **½** (the floor fills half the wall's cosine-weighted
hemisphere; everything above the floor plane fills the other half), so `E = ½·π·L_floor` and

```
L_wall = rho_wall * L_floor / 2
```

A surface lit *only* by a neighbouring diffuse surface is therefore **necessarily darker than it**
— at most `rho/2`, which on the reference pool's wall albedo `(0.25, 0.65, 0.75)` is **12 / 32 /
38 %** of the floor's radiance. This is not a pool fact: it bounds a cave wall beside a lit floor, a
canyon wall, the shaft of a light well, any receiver whose only source is a diffuse neighbour.

**That ceiling is about the wall's *lower* half-hemisphere, and there is a separate claim about its
upper one — keep them apart.** This bounds what the **floor** can give a wall. What the **surface**
can give it is [a different partition entirely](#what-a-submerged-vertical-face-sees-of-the-sky):
the upper half is 22% Snell window and 78% mirror, so a submerged face's *sky* share is 0.199 of a
horizontal face's at the same depth and not the ½ that appears in both arguments. The two halves are
additive and their ½s are the same half-hemisphere split seen from two sides; merging them produces
the confident wrong move of raising a gather multiplier to fix a sky term.

**The renderer rule that follows is a stop sign.** If a submerged wall renders too dark, *adding
bounce cannot fix it* and a multiplier on the gather is the wrong move — on the reference pool the
gather already sits at **0.77 / 0.83 / 0.87** of its own theoretical maximum, so there is no
headroom in the term at all. Check instead whether the **refracted sun reaches that wall**. When a
photograph shows a submerged wall reading *brighter* than the water beside it, that wall is
directly lit, and which wall is bright is decided by where the refracted beam lands — nothing else
in the transport can produce that ordering. In this scene the split is stark: the east wall carries
the refracted sun and reads **2.63 / 1.63 / 1.39×** the deep floor's radiance, while the north wall
— the one wall of four the refracted beam never reaches, direct caustic **0.000** — reads
0.34 / 0.57 / 0.72× the same floor, on the same liner at the same depth (`D`).

That last comparison is worth keeping as an instrument. The **ordering** between two surfaces at
the same depth, seen through the same water, is invariant to exposure, tone curve and white point —
it is a ratio of radiances in one frame — which makes it one of the very few checks a grade cannot
fake.

**Sharpness has a physical floor, and it scales with depth.** The sun is not a point: its disc
subtends **0.53°**, and refraction compresses that cone on entry by `cos(theta_i)/(n·cos(theta_t))`
— near normal incidence simply `1/n`, so ≈ 0.53°/1.33 ≈ 0.40° ≈ 7.0 mrad. The penumbra grows
linearly with depth:

```
blur ~= 7.0e-3 * depth   ->   ~0.7 cm per metre of depth (near-normal sun)
  1.5 m pool floor -> ~1 cm      5 m -> ~3.5 cm      20 m reef -> ~14 cm
```

So caustic lines in a shallow pool are genuinely crisp and in deep water genuinely cannot be. A
caustic map still pin-sharp at 20 m is over-resolved; one blurred to 5 cm at 1.5 m has thrown the
effect away. Off-normal the compression is anisotropic, so a low sun stretches the blur along the
sun azimuth. This is the same 0.53° that sets the glitter path above the surface — above the water
it makes the highlight too *wide*, below it makes the caustic too *soft*.

**And every other depth-derived quantity is a function too.** The penumbra is the easy case,
because `depth` is visibly in the formula. The expensive failures come from constants *derived* at
one depth and then applied everywhere: a penumbra kernel computed once at the deepest point and
reused put **7× too much blur** on a 205 mm shallow, and a wall attenuated per texel over the full
slant path dimmed a texel 200 mm under the waterline as though it sat under 1.96 m of water. State
the rule and grep the code against it: **if the scene has more than one depth, every depth-derived
quantity is a function, not a constant** — the extinction path, the slant, the penumbra and the
focusing number, all at once. A single `depth` constant in a renderer with a sloping floor, a step
flight or a bench is a bug list, not a parameter, and each of its symptoms will be diagnosed
separately.

**Dispersion is visible and cheap.** Water's index falls across the visible band — roughly 1.337
at 486 nm to 1.331 at 656 nm — so the three channels' fold sets do not coincide. The offset is
small, but it lands on the highest-contrast feature in the image, which is why real caustic edges
carry faint colour fringing. Refract per channel, or offset the sampled map per channel scaled
with depth, rather than shipping a grey caustic.

### A caustic on a vertical face is not the bed's pattern at that face's own position

The masking contract says caustics fall on *everything* below the surface, and every renderer that
takes that seriously immediately hits the question of how a **vertical** surface reads a map that
was rasterised for a horizontal one. The cheap answer — sample the caustic map at the receiver's own
world `(x, y)` — is wrong in a way that is diagnostic, and it is wrong on every vertical surface in
the scene at once: pool walls, step risers, pilings, ladders, a swimmer's body, a hull, a submerged
rock face.

**The signature, so a reader recognises it before diagnosing it: vertical streaking with no
variation along the height.** A bed caustic map has structure at its own texel scale — millimetres
in a pool, centimetres in open water — and a read with no `z` term smears whatever that map is doing
at one point up the entire face. A field with fine structure along the arc and *exactly none* in
`z` is a comb, and a comb convolved with a bilinear read is a set of vertical bars. On the
reference implementation's step unit the term carried **41% rms along the arc and zero up the
face — zero by construction, not by measurement** (`D`), while the bed-bounce term beside it carried
1.1% along the arc. That asymmetry is the tell: **a term whose variation collapses to zero along one
axis is not noisy, it is missing an argument.**

It is also why the obvious fix fails. Resolution does nothing to it, because it is not an
estimator problem: quadrupling the caustic map's arc bins **and** quadrupling the gather's directions
— 4× and 4×, both acting on that map and nothing else — moved the visible stripe rms on the frame's
near riser from **1.372 to 1.363** encoded levels (`D`, measured on the implementation). *A term that
can be quartered in noise without moving the artefact is not the artefact.*

**Where the read belongs, derived.** The refracted sun under the water is **one direction**, and
flux is conserved along it. The horizontal flux density crossing a plane at height `z` is the same
density that would cross the bed plane further along that beam — so the point on a vertical face at
height `z` is lit by the beam that, had the face not been there, would have landed at the beam's
own continuation to the **face's own foot**:

```
sample_xy(z) = face_xy  +  (z - z_foot) * T_sun.xy / (-T_sun.z)
             = face_xy  +  (z - z_foot) * tan(theta_t) * sun_azimuth_hat

    theta_t = the REFRACTED sun angle, from Snell at the surface -- not the incident one
    z_foot  = the height of the bed at the foot of THAT face, not a global datum
```

and the per-face-area conversion beside it is unchanged: `N·L / cos θ_t` turns flux per horizontal
area into flux per face area, and it was never the problem. Note what the correction is *not*: it is
not a blur, not a fade with height, and not a second noise term. It is the removal of a missing
variable, and it costs one bed-height lookup and two adds per sample.

On the reference implementation's sun (incidence 68.97°, refracted 44.37°, `tan θ_t = 0.978`) the
run is very nearly the height itself — **235 mm over the 240 mm riser, 249 mm over the 255 mm one,
and 685 mm over the 700 mm drop to the floor at the outer nosing** (`D`, recomputed here). Fixing
it took that frame's stripe rms from **1.372 to 0.816** encoded levels and the term's
height-to-arc structure ratio from **0 to 0.941** (`D`, measured on the implementation).

**The same trap in different clothes.** Two other ways to sample a caustic have exactly this bug
with a different-looking symptom:

- **A screen-space or projected caustic pass** projects the map down the world `z` axis onto
  whatever it finds. On a vertical face that projection is degenerate — the whole face maps to one
  line of the texture — so it produces the identical comb, and it will be blamed on projection
  aliasing rather than on the sample position. Project along the **refracted light direction**, which
  is what a shadow-map-style light-space projection does for free if it is built from the light and
  not from the axis.
- **A caustic decal projected onto the terrain heightfield only.** Named in the masking contract
  as a coverage bug; it is the same bug with the vertical surfaces omitted instead of mis-sampled.

**And the honest limit of the fix used here (`?`).** Reading the bed's map at the beam's
continuation is still a **proxy**, because that map is focused at each texel's *own* depth and the
face's point is at a different one; the fold pattern's focusing over that quarter-metre of run is
ignored. On this pool the folds move by less than their own width over that distance, so it is
below the artefact it replaces — but the correct answer is to **rasterise the vertical faces into
their own caustic map** in the pass itself, which is the same forward-splat with the receiver
geometry changed and no new physics. Filed as not-done rather than claimed.

### A channel is a band, not a wavelength

Refracting three channels with three IORs is not just an approximation of dispersion — it is a
**sampling scheme**, three delta wavelengths standing in for three broad sensor bands, and a
three-point quadrature is only as good as the integrand is smooth over the sample spacing. Which
part of the frame you are looking at decides whether it is:

- On a **caustic fold** the integrand *is* smooth over the dispersion scale, so three samples are
  plenty. That is why fold fringing always looks right, and why nobody suspects the scheme.
- On an **opaque silhouette** seen through the surface — a step nosing, a ladder rail, a wall — the
  integrand is a **step** at exactly that scale, and three deltas resolve a step as a **comb**:
  three separately-placed edges, so the pixel between them carries one primary with the other two
  missing. That is the saturated blue-and-yellow speckle on every refracted edge, and it is not
  dispersion, it is aliasing *of* dispersion. Measured at 1.40 m: the red and blue images of the
  bed land 9.8 mm apart, 2.1 output pixels, with 0.33% of water rays disagreeing about which
  surface they hit (`D`).

**The fix costs no extra rays.** `n(λ)` is already implicit in the constants you have — a
two-parameter Cauchy fit through the three `(λ, n)` pairs reproduces all three to 5×10⁻⁵, so the
three IORs were themselves drawn from one curve and the curve can be recovered from them. Give each
channel the **Voronoi cell of the three nominals** as its band, and let the existing subsample grid
carry the spectral integral: assign each subsample a different wavelength stratum inside its
channel's band, laid out as a **Latin square** over the grid so the spectral index is decorrelated
from sub-pixel position in *both* axes — otherwise the band integral comes out as a sub-pixel colour
ramp rather than a mean. The box filter that resolves subsamples into a pixel was already an
integral; it now performs the spectral one at the same time, for one multiply per ray.

**The light path is band-integrated too, and by more than the view path.** The sun's own refraction
spans each band, so every channel's fold is smeared before surface roughness or the sun disc enters:
≈3.5 mm on the red fold at 1.40 m against ≈9.4 mm on the blue, measured across the beam like the
6.8 mm sun-disc penumbra it sits beside (`D`, this sun and this depth). **Blue folds are physically
softer than red ones** — a statement three deltas cannot express at all, and one reason a
monochrome caustic map tinted per channel reads subtly wrong even when its offsets are right.

**Reusing the whitecap machinery — with one correction.** An FFT surface already computes a 2×2
Jacobian determinant per grid point for whitecap foam
([Aerated water](#aerated-water-foam-spray-and-whitewater)). That is **not** this Jacobian: the
foam one is the folding of the surface's own horizontal displacement map, this one is the folding
of the refracted-ray map onto the bed at depth `d`. Different maps, different fold sets. What
transfers is the machinery — the finite-difference stencil, the determinant, the clamp against the
`1/|det|` singularity, and the grid it runs on — so Tier 2 is usually a second dispatch over an
existing buffer rather than new infrastructure.

## Distance and filtering: why far water turns to plastic

Water that reads beautifully at 50 m routinely reads as shrink-wrapped perspex at 5 km — a
glossy, uniform dome with one hot highlight. This is not an art problem and it is not fixed by
better textures. It is a filtering failure with four distinct causes, and it is the single most
common complaint about otherwise-good ocean renderers.

**The core mechanism: thrown-away slope variance.** As distance grows, the number of waves inside
one pixel footprint grows without bound. Per-pixel normals computed from displaced geometry
converge to the *mean* normal — vertical — and all the slope variance those waves carried is
silently discarded. With near-zero variance the specular lobe collapses toward a Dirac; energy
conservation then makes the surviving highlight *brighter* as it narrows. One shading sample per
pixel hits or misses it essentially at random as the camera moves, so you get sparkling fireflies
at best and a mirror-flat plastic sheet everywhere else. MSAA does not help — the highlight is
smaller than the geometry it sits on.

**The fix is to move the variance rather than lose it.** Bruneton, Neyret & Holzschuch's ocean
model is built exactly around this: wave trains are attenuated out of the geometry as their
wavelength drops below the projected grid cell, out of the normal map as it drops below the pixel,
and everything removed is accumulated into a **2×2 slope-variance tensor in the wind frame** that
widens the BRDF lobe. Because it is the *same* quantity moved between representations, the
transition is seamless by construction — displaced geometry near, normal detail mid, statistical
BRDF far, with no popping and no discontinuity.

```
# per wave train i, with w_r = the fraction NOT resolved by geometry or normals:
sigma_x^2, sigma_y^2  =  SUM_i  (k_i,x^2, k_i,y^2)/||k_i||^2 * (1 - sqrt(1 - ||k_i||^2 * w_r^2 * h_i^2))
#   axes along/across wind = the Cox-Munk ellipse: PER-AXIS, and sigma_x^2 + sigma_y^2 = s^2 (total)
#   practical trick: total variance for ALL waves on the CPU, subtract the RESOLVED waves in the
#   shader, so shader cost scales with resolved wave count and is MINIMAL for distant views
```

Two details worth stealing verbatim: Nyquist argues the geometry cutoff should be 2 grid cells,
but that over-blurs in practice — Bruneton et al. use **N_min = 1.0, N_max = 2.5** with a
smoothstep between. And the variance must be **clamped to a minimum** matching the solar disc,
or dead-calm water still produces a Dirac (see [Calm water](#calm-water-the-low-energy-regime)).

**Cause two: Fresnel that ignores roughness.** Plain Schlick assumes a *smooth* surface. On a
rough surface at grazing incidence, microfacet masking means the effective reflectance is
substantially lower than Schlick predicts. Ship plain Schlick on a low-variance distant ocean and
the horizon band goes to near-100% mirror — that is precisely the chrome-dome look. The fix is
one line, fitted for `sigma_v < 0.5`:

```hlsl
float  sigma_v2 = sigma_x2*cos2Phi + sigma_y2*sin2Phi;        // ONE-DIRECTION variance, not s^2
float  sigma_v  = sqrt(sigma_v2);
float  F = R + (1.0-R) * pow(1.0-cosThetaV, 5.0)
             * exp(-2.69*sigma_v) / (1.0 + 22.7*pow(sigma_v, 1.5));   // Bruneton et al. 2010
```

Also make sure the Smith masking/shadowing term is present in the sun lobe — that is what stops
grazing-angle over-brightening, and with a statistical BRDF you get wave self-shadowing from it
for free rather than needing a shadow map.

**And check what the base curve is before blaming the roughness term.** The `pow(1-cosThetaV, 5)`
above is Schlick (1994) — a fit whose only argument is that it avoids two square roots, quoted in the
original as ~1% of `R` for common dielectrics. For **water it is far worse than that, and it changes
sign inside one frame**: against the exact Fresnel equations at `n = 1.3348`, `Schlick/exact − 1`
runs **−22.8% at 51.3°** and **+14.3% at 79°**, crossing zero at **67.1°** — and a shot from a normal
standing eye height spans both. That is the part to keep: a one-sided error might be absorbed into
some other constant, but this one makes the far water too mirror-like and the mid water not
mirror-enough at the same time, so no single multiplier fixes it. On a shipping game the trade is
still fine. On anything claiming to be a reference it is not, because the error lands on the specular
term, which is the brightest thing in a water frame. Evaluate
`R_s`, `R_p` and average them, and keep Bruneton's factor as a multiplier on the interface's grazing
*rise above F0* — `F = F0 + (R_exact − F0)·r` — so both limits still hold exactly. The guard to put on
it is the **Brewster identity**, `R(atan n) = ((n²−1)/(n²+1))²/2`, a closed-form number an
approximation cannot reach: Schlick misses it by 22% while looking perfectly plausible everywhere
else (`P`, `reference-impl`).

**Cause three: binary whitecaps.** A per-pixel Jacobian threshold (as in
[Ambient waves](#ambient-waves-gerstner-and-fft)) is correct up close and *disintegrates* at
distance: sub-pixel foam either aliases into shimmer or vanishes, so the far sea loses the
speckle that tells the eye it is rough. The prefilterable fix assumes the Jacobian is normally
distributed within the footprint and integrates the coverage in closed form:

```
W  ~=  0.5 + 0.5 * erf( (sqrt(2)/(2*sigma_A)) * (eps - mu_A) )
#   mu_A, sigma_A^2 = mean and variance of the Jacobian over the pixel footprint
#   BOTH are linearly prefilterable -> free hardware mipmapping and aniso filtering
```

Foam then has a correct *fractional coverage* at every distance instead of a binary mask.
Ground-truth the amount against Monahan & O'Muircheartaigh's whitecap–wind relation,
`W = 3.84e-6 * U^3.41` (U at 10 m): the exponent is steep enough that foam is essentially absent
at 5 m/s (~0.1% coverage) and conspicuous by 15 m/s (~4%), so coverage must be driven by wind,
not by a constant.

**Cause four: everything else that flattens distance.** Missing aerial perspective (the horizon
keeps full contrast and saturation and reads as a hard shell — share the atmosphere LUT with
terrain, per `10`); a constant sky tint instead of a *variance-filtered* environment fetch, which
throws away the sky gradient the reflection should carry; and missing water-leaving radiance
(`I_sea ≈ L_sea·(1 − F̄)`), without which the surface only reflects and never transmits, so it has
no volume at all — the literal shrink-wrap reading. A cheap trick worth knowing: put non-zero
radiance *below* the horizon in the environment map, since downward-reflected rays physically
re-reflect or refract; without it distant wave troughs go too dark.

### Pick the kernel on purpose, and give the variance a receiver

Two decisions live inside "move the variance rather than lose it", and both are usually taken by
default rather than made.

**The kernel.** A pixel integrates the field over its footprint, so a component of wavenumber `k`
survives at `a·W(k)` with `W` the kernel's transfer function. That is exact and assumes nothing
about the field, which means the only real choice is `w(r)`:

| Kernel | `W(k)` | Verdict |
|---|---|---|
| **Box** — the literal footprint | `sinc(k·fp/2)` | Zeros at `fp = λ`, negative lobes to **−0.217**: a band fades, **returns phase-inverted**, and fades again as the footprint grows with distance. A slow beat against distance — i.e. a moiré generator, which is the defect being removed |
| **Tent** | `sinc²(k·fp/2)` | Positive, but still zeroed, and decays only as `1/k²` |
| **Gaussian** | `exp(−k²σ²/2)` | Positive and monotone, so no band ever returns; the only kernel simultaneously separable *and* isotropic — all a scalar footprint with no orientation is entitled to assume — and it composes under convolution, so successive filters simply add variances |

Then scale it deliberately. The box of width `fp` has `σ = fp/(2√3) = 0.2887·fp`, but a Gaussian
that wide still passes **0.663** of the amplitude at the Nyquist wavenumber — 44% of the variance
straight into the fold. Pinning half *amplitude* at the Nyquist wavelength instead gives
`σ = √(2 ln 2)/π · fp = 0.3748·fp`, and the whole filter collapses to one checkable sentence:
**a component is half gone when the footprint reaches half its wavelength**, and 94% gone at one
wavelength (`P`, Fourier arithmetic recomputed here). Three rules go with it, each of which costs
something to learn the other way:

- **Attenuate amplitude, not variance.** Averaging is linear on the field, so the kernel acts on
  the field and the resolved variance falls as `W²` by itself. Applying `W` to a variance
  double-counts the filter.
- **Filter per component, not per band.** A band spanning 17–70 mm has no single `k`; one nominal
  wavenumber switches the band off where it should have narrowed it.
- **Pass the *output* pixel's footprint, not the subsample's.** Shading is nonlinear in slope, so a
  field left resolved to the subsample Nyquist still writes radiance harmonics above it.

**Filtering without a receiver trades moiré for plastic** — it is the plastic-sea failure at the
top of this section, arrived at one step earlier and on purpose. The removed variance has to go
somewhere, and two things about the hand-off are not obvious:

- **What was removed is a tensor, not a scalar.** A wind band is a spread about one azimuth and a
  wake is directional, so a lobe widened by the trace alone is visibly wrong *across* the wind.
  This is why Bruneton's 2×2 tensor is the right shape and a scalar roughness bump is not.
- **The map from slope covariance to reflected-lobe covariance is not the identity.** An in-plane
  slope perturbation swings the reflected ray by `2δ`, an out-of-plane one by `2δ·cos θ_v` with
  `θ_v` measured from the surface normal — so `C = J Σ Jᵀ` with `J = diag(−2, −2cos θ_v)` in the
  view-azimuth frame. The reflected ellipse is therefore **not similar to the slope ellipse**: a
  camera 33° above the horizontal (`θ_v = 57°`) stretches it **1.8×** along the view azimuth, an
  anisotropy the slope tensor never had. Checked against 400k Monte-Carlo perturbed reflections to
  4% on the major axis and 8% on the minor (`D`).

Convolving that into a `cos^n` lobe is closed-form and worth doing exactly rather than
approximately: two Gaussians convolve to a Gaussian, covariances add, the integral is conserved (so
the peak falls by `√(det Q₀/det Q)`), and writing the result back as a **directional** `n_eff` — the
summed Gaussian's variance along the offset to the light — keeps the anisotropy and degenerates
bit-for-bit to the unfiltered expression at zero variance. Insist on that last property: a filtered
path that does not reduce *exactly* to the unfiltered one is a second shading model, and it will
disagree with the first somewhere you are not looking.

**The unifying idea.** Cox & Munk's slope statistics, Bruneton's variance-fed BRDF, Toksvig and
LEAN and Kaplanyan-style NDF filtering, and prefilterable whitecap coverage are all the same
move: **carry a prefilterable statistic of unresolved sub-pixel surface variation alongside the
resolved geometry, and let the shading model consume it.** Build the pipeline around that one
principle and correct glitter, correct distant roughness, correct foam coverage and freedom from
specular aliasing all fall out together. Bruneton's analytic form is preferable where the
spectrum is known (no screen-space derivative error, exact at grazing angles); Kaplanyan/Tokuyoshi
geometric specular AA is the numerical fallback for residual curvature. Route the general
normal-variance-to-roughness math to physically-based-rendering.

## Shoreline integration

The waterline is where water rendering is actually judged, because it is where the water surface
meets `01`/`06` terrain at a shallow grazing angle — the worst case for every artifact class.

Historically, the shoreline was two polygons crossing: the water plane cut through terrain and
artists hid the z-fighting with a foam strip. The modern shoreline is data-driven. Bathymetry
defines the submerged shape and optical path; scene-depth difference softens the visible
intersection; shore distance/flow drive foam and run-up; the wetness overlay records the water's
reaction on land. A hard intersection ribbon is not a shoreline architecture.

- **Depth fade** ("soft intersection"): fade water opacity, distortion, and specular over the
  first few centimetres-to-metres of water depth, using scene-depth-vs-surface-depth (the "depth
  fade" node family in engine material editors). This removes the hard polygonal intersection
  line. It is a *cosmetic* fade — the swim volume still starts at the datum; do not let gameplay
  read the faded visual edge.
- **Wet-sand band**: drive a wetness band above the waterline from wave run-up (the max-recent
  run-up envelope of the shore-wave band —
  [Shallow water](#shallow-water-shoaling-refraction-and-breakers)) plus the exported wetness map — darkened albedo, boosted specular,
  handled by the surface-state system (`13`) consuming aux maps per `14`. The band must *move*
  with the waves' run-up envelope, lagging and drying, or the beach reads as painted.
- **Shoreline foam**: an advected foam texture in a band defined by shore distance, phase-driven
  so it pulses with the incoming wave cadence — tie its phase to the shore-wave band's
  travel-time phase (the same `τ/T − t/T`), or foam and waves visibly disagree; where a
  shore-wave foam lifecycle exists, this band is its final decay stage, not a second system.
- **LOD co-discipline**: the water mesh's LOD at the shoreline must be matched (or biased finer)
  relative to the terrain tile's LOD, and both must refine together, or the intersection line
  *crawls* on LOD transitions — a `11` catalogue symptom whose fix is contract (shared SSE
  currency, shoreline LOD bias), not blending. Terrain skirts at the shoreline must stay below
  the water surface minus max wave trough, or skirt walls surface at low tide.

## Transparency & pass ordering

Water is the classic hard transparency case, and the frame must be structured for it:

1. Render all opaque (terrain included) → copy scene color and depth. Water draws *after*
   opaque, reading the copies for refraction/absorption; it cannot refract what hasn't been
   drawn, and it cannot read the depth buffer it is about to write.
2. **Depth-write policy**: water writes depth (so later transparents and post-fog sort against
   it) *after* its own pass, or renders to depth in a prepass for particles to soft-clip
   against. Pick one, document it; ad-hoc per-effect choices produce spray that draws behind
   the surface it belongs on.
3. **Per-body sorting**: bodies at different datums (a lake above a river) sort back-to-front
   per body; the depth-reject refraction logic must use the *nearest* water surface per pixel or
   stacked bodies smear each other.
4. **TAA/upscalers**: refraction UVs computed from a jittered depth/scene buffer shimmer under
   TAA — sample with the current-frame jitter removed, and give water correct motion vectors
   for its *displaced* surface or the upscaler smears wave crests into ghosts. DLSS/FSR-era
   discipline: water normal detail that only exists at native resolution will boil; pre-filter
   the cascade mips (specular AA doctrine — route the math to physically-based-rendering).
5. **Planar reflection cost discipline**: a planar pass re-renders the scene — treat it as a
   scaled-down scene render (half-res, reduced LOD bias, terrain-only + hero set, no recursive
   water) with its own budget line. One planar body per frame is the classic ceiling; every
   additional body falls back to SSR + cubemap.
6. **Forward vs deferred**: water is effectively a forward pass even in a deferred renderer —
   it needs multiple light/environment sources, scene-color access, and a BRDF that doesn't fit
   the G-buffer. Budget it as forward: it pays full lighting cost per pixel, which is why water
   area on screen is a load-bearing profiling axis (`11`).
7. **The dedicated single-layer pass**: a structural alternative to sorting rather than a rule
   about it, and the route Unreal's Single Layer Water takes. Draw the water surface as *opaque*
   geometry into the G-buffer, let
   it receive ordinary deferred lighting and shadows, then run one dedicated pass — after
   lighting, before regular translucency — that integrates a homogeneous participating medium
   between the surface and the opaque scene behind it. Sorting disappears (water is opaque
   geometry), the surface gets the full deferred light set for free, and the volume integration
   is one screen-space pass. The price is absolute: **one water depth layer per pixel**, so no
   water can be seen through water. Choose it when the world has one water surface per sightline
   and choose per-body sorted transparency when it does not; the decision is made at
   architecture time because it decides the shading model, not a material setting. Worked
   example, with its inputs and limits, in
   [Engine-native water](#engine-native-water-the-ue-water-plugin-read-as-architecture).

## What to pre-cook, and what to recompute

The question that decides this is not *how expensive is it* — it is **how often does its input
change, and how is it consumed**. Cost decides whether the saving is worth having; **cadence**
decides whether a table is even correct, and **consumption** decides whether it helps. A rule
built on cost alone mis-files half of this chapter.

Cadence is a ladder, not a switch, and every rung is populated in a shipping water renderer:

| Rung | Rebuilt | This chapter's inhabitants |
|---|---|---|
| **Never** | offline, shipped as data | `k(ω,h)` from the dispersion relation ([shallow water](#the-physics-worth-stealing)) — Newton iterations that must never run per frame |
| **On load** | once `n`, the band edges and the body are fixed | `1 − 1/n²` and the vertical-receiver form; the diffuse Fresnel pair; band-integrated `a`. These are **uniforms**, not textures |
| **On a slow event** | when the body, the sun or the weather moves | the Water Info Texture; prefiltered reflections; anything with an **invalidation contract** |
| **Per frame, reduced** | every frame, at low resolution or ¼ rate with reprojection | the sky/atmosphere LUT; caustics in most shipping engines |
| **Per frame, full** | every frame | the wave field; the caustic map as [tier 2](#the-tier-ladder) |
| **Per pixel** | never stored | Fresnel; the sun lobe; the roughness correction |

Two consumption tests sit beside the cadence one, and they are why things get baked that are not
expensive:

- **Fusion.** The Water Info Texture is not tabulated because its parts are costly — they are not.
  It is tabulated because it replaces many scattered lookups with one coherent sample. A rule that
  prices only per-sample cost cannot see this.
- **Divergence.** A term confined to a thin screen-space curve — the waterline, a shoreline — is
  **divergence-bound, not ALU-bound**: it clips a few lanes of many warps and masks the rest. A
  table does not fix that; running the term on a coherent band does, which is why the chapter puts
  the meniscus on [a decal or a junction shader](#the-meniscus-line-where-reachability-cannot-fail)
  and why the natural table there is a **1-D profile across the decal's width**, not a 3-D lookup.

### The three that surprise people

**A gather is not a table, and the obvious factorisation destroys it.** Nondimensionalised, the
poolward gather over flat water is **scale-invariant** — a constant, not a surface — and the riser
gather's closure has a closed form of a handful of flops (`12a` §8). What is worth storing is not a
scalar form factor but the **radial kernel, self-similar in `ρ/q`**, one dimension after
nondimensionalisation, applied as a *filtered lookup of the bed*. The tempting factorisation —
form factor × mean bed radiance — is exact only for uniform `L`, and the gather's entire value is
that it is near-field-dominated: half its irradiance arrives from inside 30 cm, and it carries
11–18% of the bed's cell-scale contrast (`D`). Factor out a mean and you have thrown away exactly
the part you built it for.

**The caustic map is not a table, and tier 0 is the cautionary tale.** Tier 2 is a per-frame
render-to-texture — one light-view pass over the wave grid — not a precompute. The *tabulated*
alternative is tier 0, a scrolling authored texture, and the ladder already prices what that bake
costs: **the caustics keep churning when the water goes calm**, because what was baked out was the
coupling to the surface. That is the sharpest illustration in the chapter of the real risk — a bake
does not lose accuracy, it loses a *correlation*, and correlations are what the eye reads.

**The sun's disc must be rewritten — but not for the reason you would guess.** Pinning peak, width
and flux to the disc simultaneously gives `n = 2/θ_s² − 1 ≈ 9.3×10⁴` (`P`, `12a` §6). In **fp32
this is fine**: `pow(dot, n)` carries ~0.14% relative error across the lobe (`D`), and swapping it
for a Gaussian in `acos(dot)` buys **nothing** — measured at 0.138% against 0.137%. The problem is
elsewhere and it is twofold.

- **The angle, not the function.** `x ↦ xⁿ` at `x ≈ 1` has condition number `n`, so 1e-6 of
  sloppiness in `cosθ` — an unnormalised half-vector, a packed normal, an interpolated varying —
  becomes a median 6% error with a 50% tail (`D`). Take the angle from the **chord**,
  `‖H − L‖ = 2sin(θ/2)`, which keeps full relative precision: 0.0009% against 0.137%, a factor of
  500 (`D`). *Compute the angle from the difference of unit vectors, never from their dot product.*
- **fp16 is a genuine catastrophe.** The lobe's e-folding half-width is `1 − cosθ = 1/n = 1.07×10⁻⁵`,
  which is **0.022 of a single fp16 step below 1.0** (ulp = 2⁻¹¹). So `half(cos θ_s)` rounds to
  exactly 1, one step down evaluates to ~10⁻²⁰, and the sun becomes **binary**: full brightness or
  nothing, with no disc between. Half-precision varyings and packed normals are routine, which is
  what makes this the version of the claim that bites.

### Attenuation and escape do not factorise, and a LUT is where you will separate them

The three above are about *what* to bake. This one is about **how a baked quantity is allowed to be
written down**. The half-texel remap below is the most-*shipped* LUT bug; this is the one that
survives being looked for, because the table is built correctly, sampled correctly and interpolated
correctly, and holds the wrong number. It has nothing to do with water in particular — it is a
statement about products of correlated integrands, and water only supplies an unusually sharp
instance of it.

**The rule, first, because it is two lines of probability and it governs every table in this
section.** For any two quantities integrated over the same variable under a normalised measure,

```
<f g>  =  <f> <g>  +  Cov(f, g)                     # exact, always
<f g> / (<f> <g>)  -  1  =  r * CV_f * CV_g         # r = correlation, CV = coefficient of variation
```

So the product of the means equals the mean of the product **only** when the two are uncorrelated
over that measure. Storing `<f>` in one table and `<g>` in another and multiplying them at runtime
is the product of the means, and the error is not a rounding — it is `r·CV_f·CV_g`, which is
first-order in each factor's spread and carries the sign of the correlation.

**The water case, which is the exit transport of a submerged bed.** Light leaving a Lambertian bed
at depth `d` has to do two things before it reaches the air: cross the column, and get through the
underside of the surface. Both are functions of the **same** water-side cosine `μ`, and they are
strongly correlated — a steep ray is inside the Snell cone *and* takes the short path, a grazing
one is totally internally reflected *and* takes the long one. The correct objects are one integral
each, over that cosine, with both factors inside:

```
measure on the water-side cosine:   dP = 2 mu dmu,    INT_0^1 2 mu dmu = 1

T_esc(tau) = INT_0^1 2 mu exp(  -tau / mu) (1 - R_int(mu)) dmu     # escapes on this pass
G_rt (tau) = INT_0^1 2 mu exp(-2 tau / mu)      R_int(mu)  dmu     # returned, and back at the bed

    tau = a*d, the vertical optical depth;  R_int(mu) = 1 past the critical angle,
    the exact unpolarised Fresnel inside it -- NOT a diffuse constant

rho_water = (1 - R_ext(theta_sun)) * T_slant * rho_bed * T_esc / (1 - rho_bed * G_rt)
```

The separated pair a table-builder reaches for instead is an **absorption** term and a
**Fresnel/escape** term: `<T> = 2E₃(τ)`, the diffuse slab transmittance, times the diffuse exit
constant `1 − R_int`. Both are respectable quantities; their product is not the transport. On this
chapter's pool (`τ = a·d = 0.3664 / 0.0742 / 0.0143` at 1.40 m, `D`, recomputed here):

| Leg | Joint integral | Separated `<f>·<g>` | Separated form reads | Correlation `r` |
|---|---|---|---|---|
| Escape, `T_esc` | **0.3403 / 0.4795 / 0.5106** | 0.2850 / 0.4563 / 0.5050 | **16.2 / 4.8 / 1.1 % low** (the truth is 19.4 / 5.1 / 1.1 % above it) | **+0.76** in red |
| Round trip, `G_rt` | **0.0965 / 0.3277 / 0.4445** | 0.1389 / 0.3614 / 0.4546 | **43.9 / 10.3 / 2.3 % high** (the truth is 30.5 / 9.3 / 2.2 % below it) | **−0.85** in red |

![The two integrands of the escape leg over their shared cosine, and the factorisation error against optical depth](figures/lut-factorisation.png)

> **Figure 12·2 — why the product of the means is not the mean of the product.** `D`. Drawn by
> [`figures/make_figures.py`](figures/make_figures.py) (`fig_factorisation`) from
> `reference-impl/optics.py`'s `slab_esc`, `slab_trap`, `r_int_at` and `_e3`. Scene-linear;
> dimensionless throughout. **Left, the mechanism**, on this pool's own red column
> (`τ = 0.36638`): the two thin curves are the factors, and they **rise together** — a steep ray
> attenuates less *and* escapes, a grazing one attenuates more *and* is totally reflected. The
> thick solid curve is the joint integrand `2μ f g`, whose area is `T_esc = 0.3403`; the dashed
> straight line is the separated integrand `2μ ⟨f⟩⟨g⟩`, whose area is `0.2850`. **The two curves
> cross**, and the two tinted regions are the two halves of `Cov(f, g)`: the separated form
> over-counts below `μ_c` (where the true escape is *identically zero* and it still credits some)
> and under-counts above it by more. The net is the printed +19.4%. **Right, the size of it**:
> `joint/separated − 1` against `τ` for both legs, per band, with each band's own pool `τ` marked.
> Two things are visible that the tables below cannot show. The escape leg and the round trip have
> **opposite signs** at every `τ`, which is the cancellation that lets a chain-level check pass at
> 2.8% while a term inside is wrong by 19.4%. And the three bands **very nearly coincide** — the
> spread the correction below names is real but small, so the per-channel spread in the printed
> numbers comes almost entirely from the three bands sitting at *different `τ`*, not from
> `R_int(μ)` differing between them. That is a sharper statement than "the table needs a band
> label", and it is the one to carry: **re-run the row at your own `τ`, and do not expect the band
> label to be what moves it.**

⚠️ **And the round-trip row hides a second choice, where the *more* physical option is the *further*
off.** `(2E₃(τ))²` in the table is **two one-way diffuse legs**, which re-randomises the ray's
direction at the surface. A specular surface does no such thing: the down leg travels at the same
cosine as the up leg, so the direction-preserving transmittance is `2E₃(2τ)` — one leg of twice the
optical depth — and it is the better physics. It is also **worse**: `2E₃(2τ)·R_int` reads
`0.1502 / 0.3651 / 0.4549`, i.e. **+55.6 / +11.4 / +2.4 %** over the joint form against the squared
version's +43.9 / +10.3 / +2.3 %, so **fixing the direction error alone moves the red 8.1% away from
the truth** (`D`, recomputed here). The squared form was getting part of its accuracy from a
cancellation between its two decorrelations. **Partial corrections to a factorisation are not
monotone: "the more physical of two approximations" is not automatically the closer one**, and the
only way to know is to compose the error rather than reason term by term — which is also why a
half-finished migration off a separated LUT can ship a regression that reads as a bug in the new
code. **The table in this row is the `2E₃(τ)²` form; the scaling table below is the `2E₃(2τ)` one**,
and the four numbers that follow from the two forms crossed with the two directions of the ratio are
printed [there](#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them),
because carrying one of them without saying which is what produced two contradictory correct answers
in this project.

**The two errors have opposite signs, and that is the dangerous part.** The escape leg is
positively correlated and the separated form is dark; the round trip is negatively correlated and
the separated form is bright; the round trip sits in a *denominator*, so the two partly cancel in
the composed albedo. Written out on this pool the composed number moves by **−2.8% in luminance**
while the escape term inside it is wrong by **19.4% in red** (`D`). A chain-level comparison at that
tolerance passes. **Check the term, not the chain** — an end-to-end agreement of a few percent is
not evidence about a factor that is wrong by twenty, and a bake is exactly where term-level errors
get composed out of sight.

**This section is now MEASURED rather than predicted, and it survived.** Every figure above had been
derived and none of it had been run until a raster pass was built to run it. At this pool's own
`d = 1.40 m` the term-level errors reproduce as **+19.400 / +5.072 / +1.101 %** on the escape leg
against the printed 19.4 / 5.1 / 1.1, and the composed albedo moves **−2.833% in luminance** against
the printed −2.8 (`D`, `raster-impl/lut.py:factorisation_error` and `composed_albedo`, on a bed
albedo taken from `render.py` and the sun's own cosine — no table and no interpolation in the way).
Recorded as **survived**: the prediction was made from `r·CV_f·CV_g` and confirmed by a machine that
did not exist when it was written. What it did not carry is the next paragraph.

⚠️ **How much of a term-level error reaches the pixel is an architectural choice, and it is worth
more than the term.** The list below names *where the temptation arises*; it does not say that one of
those places is nearly immune. Same scene, same camera, same 128-texel table, same separated bake —
only the question of *where the angular average sits* differs, over 157 641 water pixels (`D`,
`raster-impl/evidence.py:fig_frame_factorisation`, reproduced here):

| where the upwelling comes from | whole frame, red / green / blue | worst binned red |
|---|---|---|
| **a column table**, `T[depth]·kExit` — the second bullet below, taken literally | **−9.27 / −4.68 / −0.76 %** | **−17.5 %** |
| **each ray attenuated over its own path**, the table read only for the sky's entry leg and the trap gain — the one place an angular average genuinely sits | **−0.84 / +0.65 / +0.58 %** | **−2.1 %** |

**A factor of eleven whole-frame in red, and 8.2 on the worst bin, from one decision the chapter did
not make for the reader.** Both rows carry the *same* wrong table. The actionable statement is
therefore not *"do not separate"* — it is: **separate only where the pixel's own `μ` is unknown.** A
pass that knows the view ray can attenuate along it and never asks the table for the thing the table
gets wrong, and the same defective bake then costs under a per cent. The error the section predicts
is smaller than the error a reader makes applying it in the wrong place.

**And the frame error is not monotone in `τ`, which the scaling table below cannot show.** It peaks
near `τ_red ≈ 0.4` and flattens, because the deepest water in this frame is also the most grazing and
a grazing water pixel is mostly surface reflection. **Optical depth alone does not price this error;
the view angle prices it too** — and the table below is tabulated against `τ` alone.

**How the error scales, so it can be priced before it is measured.** ~~It is a function of optical
depth alone~~ — **it is not** (struck; see the two corrections under the table) — and it is already
worth having at depths nobody thinks of as absorbing (`D`, quadrature here on the exact internal
Fresnel). **Round trip: `2E₃(2τ)·R_int`, read as `joint/sep − 1`. Green band.**

```
tau = a*d      0.05    0.10    0.20    0.37    0.50    1.00    2.00
escape leg    +3.6%   +6.6%  +12.0%  +19.4%  +24.6%  +39.6%  +58.4%    (joint over separated)
round trip    -7.3%  -13.2%  -22.9%  -35.5%  -43.6%  -64.2%  -83.2%    (2E3(2tau) form, joint over sep)
```

⚠️ **Correction one: that label is new, and its absence produced two builders who each measured a
different number and were each right.** The table above is **not** the same separated form as the
1.40 m table eight lines up — that one leads with `2E₃(τ)²·R_int` and this one is `2E₃(2τ)·R_int`.
The two differ by 12.4 pp in red at 1.40 m. A reader takes the two blocks as one quantity, and there
is a second fork on top of it: `1 − joint/sep` and `sep/joint − 1` are **the same fact and different
numbers**, 13 pp apart at 44%. Four cells, all defensible, none of them previously named. In red, at
this pool's `d = 1.40 m` (`D`, all four recomputed here):

| round-trip separated form | `1 − joint/sep` | `sep/joint − 1` |
|---|---|---|
| `2E₃(τ)²·R_int` — up leg × mirror × down leg, the product of the means taken **twice** | **30.52 %** | **43.94 %** |
| `2E₃(2τ)·R_int` — one table read at the round-trip depth, direction-preserving and the **better physics** | **35.74 %** | **55.63 %** |

The project has now confused two of these once each, in opposite directions, and both readings were
reported as "the" answer. **When a ratio between two approximations is quoted, the form and the
direction are part of the number.** State both or print all four.

⚠️ **Correction two: the scaling is *not* a function of optical depth alone.** The joint integrals
carry `R_int(μ)`, which is per band, so one `τ` gives three different errors — the three bands spread
by **0.63 pp at `τ = 2`** on the round-trip row and no single band reproduces every printed cell
(`D`, recomputed). Green matches six of seven; the `0.37` column is this pool's own
`τ_red = 0.36638`, where the escape row's +19.4% is red rather than green. **The table needs a band
label, which it now has** — and a reader carrying it to a different water should re-run it rather
than interpolate this one.

At `τ → 0` both collapse to the diffuse constants — `T_esc → 1 − R_int`, `G_rt → R_int` — and this
is the trap's second half: **a lossless check cannot see it.** Open water's absorption to zero and
the separated form becomes exact, so an energy-conservation row, a white-bed audit, or any test run
at `a = 0` passes every version of this. What catches it is a check at the medium's own absorption
with nothing averaged in it — a photon walk that attenuates each path over its own `1/μ` (`12a`
§10). That is a general property of this class of bug and it is why it belongs beside
[`11`'s eighth way](11-verification-failures.md#the-eighth-way-is-about-the-test-not-the-measurement).

⚠️ **And a note on computing these two integrals, because the obvious rule is the wrong one.**
`R_int(μ)` **pins to exactly 1 past the critical angle**, so the integrand has a **kink** at
`μ = cos θ_c` — and a smooth high-order rule spread across it converges algebraically, not
spectrally. Splitting the interval at `cos θ_c` and using 400 nodes a side reaches eight digits
where a single 2000-node Gauss–Legendre rule reaches four and a half (`D`; the shipped figures in
the table above are unaffected at the precision quoted, but the rule sits `+3.9 / −6.2 / +3.1 e-5`
relative away on `T_esc`). Baking these into a LUT hides the residual behind interpolation error,
which is why it is worth getting right in the generator; the episode, and the suite row whose
tolerance was exactly the size of it, are
[`11`'s thirteenth way](11-verification-failures.md#the-thirteenth-way-a-tolerance-the-size-of-the-thing-it-covers).

**Where the temptation arises in a real-time pipeline**, in rough order of how often it is taken:

- **The water shader's own composition.** `refracted * exp(-c * rayDistance) * (1 - F)` is the
  separated form written inline: an extinction and an exit Fresnel, multiplied. It is right for a
  *single* ray, whose `μ` is known, and wrong the moment either factor is standing in for an average
  over directions — which is exactly what a diffuse bed term, an irradiance cache or a prefiltered
  probe is.
- **A depth-indexed absorption table times a constant exit factor.** The most direct instance:
  `T[depth] * kExit`. Store `T_esc[τ]` and `G_rt[τ]` instead — one table, one fetch, two channels,
  identical cost. The trap is free to avoid and there is no performance argument on the other side
  of it. **This is the one that reaches the pixel**: it is the −9.27% row above, and the same bake
  read only where an angular average genuinely sits is the −0.84% row.
- **Splitting a table by "what changes and what does not".** `n` is fixed at load and `d` is a
  field, so the Fresnel half looks like a uniform and the Beer half like a texture. That reasoning
  is about *cadence* and it silently reorders an integral. Cadence decides where a term is
  evaluated; it may not decide whether a product is inside or outside an integral sign.
- **Any `mean(visibility) * mean(radiance)`** — a shadow term times an irradiance cache, an AO
  scalar times a probe, a caustic mean times a sun term. Same identity, same sign rule: if the
  occluder is correlated with the source direction, the separated product is wrong in whichever
  direction the correlation runs.

**The general statement to carry out of this section:** *a pre-computation may split a product only
across variables the integral does not run over.* Two factors that share an integration variable
are one table. And when a split is forced, price it: compute `r·CV_f·CV_g` once, offline, at the
extremes of the table's own domain, and either bound it or store the joint form.

**And the factorisation that does hold, with the cone it holds inside.** The useful converse, and
the one worth knowing because it saves a dimension: **a Lambertian bed under a flat surface emits a
near-Lambertian field into the air**, so a water-to-deck ratio is nearly view-independent and a
table over the bed does not need a view axis. The reason is that the only angular dependence on the
way out is the Fresnel transmittance, which is flat until it is not. Normalising by the
cosine-weighted mean gives the shape factor a directional read has to carry:

```
S(theta_a) = (1 - R(theta_a)) / (1 - R_ext_diff)        # 1.049 at nadir on this IOR triple
```

| View from vertical | 0° | 30° | 45° | 60° | 70° | 80° |
|---|---|---|---|---|---|---|
| `S(θ)`, green | 1.0494 | 1.0483 | 1.0413 | 1.0071 | 0.9280 | 0.6980 |
| … × the up leg's own `exp(−a·d/μ_w)`, red, against nadir | 1.000 | 0.971 | 0.929 | 0.855 | 0.761 | — |

So the emergent field is Lambertian to **0.4% in luminance inside a 40° cone** and 0.8% inside 45°,
and then it stops: **4.2% by 60°, 13.1% by 70°** on the Fresnel factor alone (`D`, all recomputed
here). Two corrections to the simplification, both signed, both easy to state:

- **The medium tilts it further, and per channel.** The last leg is `d/μ_w`, not `d`, so absorption
  adds its own obliquity: at 60° the emergent red is 0.855 of nadir against 0.955 in blue, which
  means **an oblique view of a pool reads more cyan than a nadir one for reasons that are not the
  water's colour**. Useful as a signed inference rule when a render and a photograph disagree at
  different camera heights.
- **A standing camera is not inside the cone.** Over the reference implementation's own whole-basin
  frame the water spans **44°–73°** from vertical, and across that span the shape factor alone
  varies by **17.6%** in luminance and the full emergent field by **21.2%**, rising to **29.3%** in
  red (`D`). "Near-Lambertian" is a nadir statement — an aerial or drone reference, or a closed form
  written for one — and quoting it at a poolside eye is worth a fifth of the answer.

### Format, precision, and the bug everyone ships once

- **A one-texel table is a uniform.** "Resolved on load" means a material constant; making it a
  texture costs a fetch to learn nothing.
- **unorm8 is 0.4% per step.** On a term multiplied by a solar radiance of order 10⁵ that terraces
  visibly. R16F is the floor for anything feeding a specular path.
- **The half-texel remap.** A bilinear table must be sampled over `[0.5/N, 1 − 0.5/N]`, or its
  endpoints are wrong by half a texel. This is the most-shipped LUT bug there is, and it silently
  violates this chapter's own requirement that a filtered path
  [degenerate exactly to the unfiltered one](#pick-the-kernel-on-purpose-and-give-the-variance-a-receiver)
  at the limit.

  ⚠️ **That sentence has two readings and only one of them is safe, and this chapter meant the safe
  one without saying so.** Two table designs satisfy it:

  | design | the sample coordinate | what happens at the ends | order |
  |---|---|---|---|
  | texels at the **centres** `τ_max(i+0.5)/n` | `x = nτ/τ_max − 0.5` | the domain's endpoints fall **half a texel outside** the table and a clamped sampler returns a constant | **first** in the interior's second |
  | texels at `linspace(0, τ_max, n)`, i.e. `u ∈ [0.5/N, 1 − 0.5/N]` | `x = (τ/τ_max)(n−1)` | **exact** at both ends | second everywhere |

  Both are "sampled over `[0.5/N, 1 − 0.5/N]`" in the sense a reader will take from the sentence;
  only the second is exact at the domain's edge. On `T_esc` with `n = 64` the centre design is wrong
  by **9.3×10⁻³ relative at `τ → 0`** against **4.4×10⁻⁵** in its own interior — a factor of **210**,
  and the endpoint error falls with a measured order of **−1.00** in `n` against the interior's
  **−2.00** (`D`, recomputed here over `n = 32…512`).

  **And the concentration is what makes it expensive here: the bad endpoint is `τ → 0`, which is the
  shoreline** — which is exactly where the factorisation error above goes to zero, so a clamped
  centre-design table *manufactures* an error precisely where the quantity it stands in for has
  none. This is the same failure the [interface's `1/n²`](#radiance-is-not-conserved-across-the-interface)
  audit has: an error that hides wherever the check is cheapest to run.

  **The order is the diagnostic, and it needs no access to the shader.** The actual remap bug —
  sampling at `u = τ/τ_max`, which is what `texture(lut, tau/tauMax)` compiles to — is **first order
  in `1/n` (measured slope −1.00)** where an honest interpolation error is **second (−2.01)**.
  *A table whose error only halves when you double its resolution has a remap bug and not a
  resolution problem.* Doubling the table and watching the error is a two-line experiment that
  distinguishes the two without reading a line of sampling code.
- **Index tables on quantities that are already prefiltered.** A table indexed by instantaneous
  slope aliases *in its own axis*, and its mip chain knows nothing about the pixel's footprint.
  Index on the **variance tensor**, not the slope — the same discipline the chapter applies to
  shading, applied to the table's argument.

### Underwater, a load-time constant is two constants

Every entry in the *on load* rung is medium-dependent, and the submerged view is not an exception
to be handled later — it changes the numbers. The solar disc **refracts**: its half-angle goes
0.265° → **0.199°**, so `Ω_sun` shrinks by exactly `n² = 1.782`, the peak radiance rises by the
same factor, and the lobe exponent rises to **1.67×10⁵** (`D`). A renderer that resolves these once
at load and reuses them below the surface is wrong by that factor everywhere.

### Generating them, and the trap

A table fitted to one body of water is not a table, it is a **bake**. Nondimensionalise wherever
the physics allows — the meniscus in capillary lengths `a = √(σ/ρg)`, the gathers in units of
depth — or it will not survive the move from a pool to the sea, and the failure will read as an art
problem rather than a parameterisation one.

**Scattering needs more than optical depth.** `τ` alone does not transfer: a treated pool and milk
at the same `τ` look opposite, because what separates them is the single-scattering albedo
`ω₀ = b/(a + b)`, 0.00 against 0.98. The transferable index is `(τ, ω₀, g)` plus the boundary
albedo — which is the same
[count of free parameters](#water-body-optical-identity-where-the-iops-come-from) the
chapter uses to separate Case 1 from Case 2 water. And take `τ` from the **right** coefficient: `c`
for a sharp sightline, `K_d` for the diffuse column, never one constant for both.

**Generate from a reference implementation, and close the loop.** A generated table is not finished
when it looks right; it is finished when it **reproduces the closed form at its sample points** and
its *interpolation* error is bounded against a tolerance justified from the estimator's own error —
the same standard this chapter applies to every other measurement. That check is what tells you
whether the parameterisation transferred, or whether you have shipped a bake.

## Engine-native water: the UE Water plugin, read as architecture

Most teams inside a licensed engine never assemble the machinery above from parts — they inherit a
water system and then discover its contracts the hard way. Unreal's Water plugin is the most widely
deployed of these, and it is worth reading not as a feature list but as **one complete, shipped set
of answers to this chapter's questions**: its answers are mostly the ones recommended here, which
is corroboration; where they differ, the differences are load-bearing and teach something. Tier is
D/N throughout (engine docs and branded feature names), the facts below were checked against Epic's
documentation in 2026-08, and Water has moved substantially across releases — verify constants
against the version you ship on.

### The five parts, and this chapter's name for each

| Part | What it is | Read as |
|---|---|---|
| **Water Zone** | A *bounded* actor owning water rendering over a region: zone extent, render-target resolution, the water mesh, the info texture, optional local-only tessellation in a sliding window around the view (**?** whether and how several zones compose in one world is version-sensitive — check your release) | The water surface's **paging/streaming unit** — the camera-following overlay doctrine (`13`, `14`) applied to water |
| **Water Body actors** | Ocean / Lake / River / Island / Custom — splines (or a static mesh) with per-point metadata | `bodyType` plus per-body geometry: terrain-architect's `liquidBody` record (`28`), *authored* rather than generated |
| **Water mesh** | A quadtree of tiles over the zone, LOD as concentric rings around the camera, tiles morphing between levels | The world-space grid of [Surface geometry & LOD](#surface-geometry--lod) |
| **Water Info Texture** | One top-down capture of every water body **and the ground beneath them**, into a render-target array everything downstream samples | A runtime-rasterized version of the generator's handoff fields |
| **Single Layer Water** | A shading model: opaque surface in the base pass + a participating-medium pass beneath it | Option 7 of [Transparency & pass ordering](#transparency--pass-ordering) |

### The water mesh confirms the world-space grid — including the skirt

Documented behavior: the quadtree is traversed each frame to produce the visible tile set; tiles are
generated **only where a body's spline says water exists**, so open land costs nothing; each LOD is a
concentric ring around the camera, each successive ring carrying half the vertices of the one inside
it; and transitions **morph** rather than swap — Epic's wording is that four quads become a single
quad when dropping a level, or become sixteen when gaining one.

Defaults worth knowing as orders of magnitude: `Tile Size` 2400 uu (24 m) and `Extent in Tiles` 64
as a radius from the centre, so an untouched zone reaches roughly 1.5 km out and ~3 km across. That
number is the useful one: a *bounded* water zone must be sized against the game's view distance, and
the default is smaller than most open worlds need. `LODScale` sets where morphing begins;
`Tessellation Factor` sets vertex density inside a tile, and Epic notes lakes and oceans benefit most
from raising it — they are the bodies carrying real displacement.

The **Far Distance Mesh** is the infinite-ocean skirt, shipped, complete with the failure it exists
to fix: Epic states that an ocean body can hit its maximum extent "without completely filling the
level, leaving a gap between the horizon line and the water". It uses its own material slot — the
near field and the horizon ring are *different materials*, i.e. the three-bands doctrine expressed in
asset structure rather than as a shader branch. That is a pattern worth copying: when the far field
must be normal-map-only, make it a separate material so nobody accidentally ships displacement to
the horizon.

### The Water Info Texture: fuse the handoff into one sampleable field

The zone renders its water bodies top-down into a render target (a texture **array** in current
versions; the single-target form is deprecated). Knobs that reveal the design: a half-precision
toggle choosing **16 or 32 bits per channel**, a **capture Z offset** that places the capture plane
above the highest water in the zone, a **velocity blur radius** applied in a "finalize water info"
pass, and an explicit rebuild/update path. Everything downstream — the surface material, shore fade,
flow, gameplay queries — samples that one texture.

The capture is not water-only: the zone registers **ground actors** (landscape proxies intersecting
its bounds can be auto-included) and carries a `GroundZMin`, so the terrain beneath the water
participates. Epic's documentation does not spell out the channel layout, and this chapter
deliberately does not guess it — what the API surface establishes is that **water and ground are
captured into one field together**, which is the load-bearing architectural fact. Treat any specific
channel packing you read elsewhere as unverified.

Name the technique independently of the engine: **rasterize the water layer stack into one
view-independent field, and let every consumer read it.** The virtues are the ones `14` argues for —
one surface truth, one coordinate frame, no consumer re-deriving hydrology — and the fact that the
capture holds *ground* alongside water is terrain-architect's layer stack (`08`) made concrete: water
surface and solid top in one field, depth being their difference. Any engine can build this; a
project with no generator handoff can build it *from* its authored water and get most of the
chapter's depth-driven cues immediately.

One tension to resolve deliberately, because it cuts against
[the handoff](#the-handoff-seen-from-the-render-side): rasterizing bodies into a capture is
*re-deriving* depth and flow that a generator may already have shipped. Both can be true — the
capture is the right *delivery mechanism* (one field, one frame, sampled by everyone), and the
generator's fields are the right *content*. Where the handoff exists, the capture should be populated
from the exported depth, flow and shore-distance rather than recomputed from spline geometry, or the
two disagree at exactly the shoreline. Re-derivation is the fallback for pipelines with no generator,
not the default.

The costs are the price of any texture-shaped truth, and each is a review question:

- **Resolution is a whole-zone budget, spent uniformly.** One render-target resolution spans the
  entire zone extent, so a 5 m river inside a 4 km zone gets a handful of texels across its width:
  thin bodies alias, banks quantize, and near-bank flow blurs toward the ground value. There is no
  per-body detail level. Measure **texels across the narrowest body that matters**, not zone size —
  if the answer is under ~8, either the zone shrinks or the resolution rises.
- **Precision is a visible choice.** Half precision saves memory and spends Z accuracy in exactly
  the channels that drive shore fade and the wave-attenuation ramp — the two places the eye is
  already looking.
- **It is a cache, so it needs an invalidation contract** (`SKILL.md` Part 3). Moving a body, moving
  the zone, or editing the terrain beneath it must dirty the capture; a stale capture is a river
  whose flow field points at last frame's channel. Anything rendering outside the normal frame loop —
  offline movie-render paths are the documented case — has to force the update explicitly.

### Waves as a data asset, evaluated twice

Waves live in a **Water Waves** asset assigned per water body: a Gerstner generator with `Num Waves`
(default 16), min/max wavelength and amplitude with falloff curves, a dominant wind angle plus
angular spread, small/large-wave steepness, and a seed with a randomness term — a *parameterized
band*, not a sampled spectrum. That is squarely the Gerstner column of
[Ambient waves](#ambient-waves-gerstner-and-fft), with the documented consequences: visible
periodicity over open water and cost linear in wave count. Custom generators derive from the same
base class, which is where an FFT backend would go.

The load-bearing detail is the **second evaluation**: buoyancy re-evaluates the same Gerstner sum on
the CPU. That is the one-evaluator rule of `19` implemented for you — and the technique that makes it
affordable is worth stealing wholesale. The buoyancy component exposes **`N Points Per Frame`** and
**`N Frames Pause`**: probe points update round-robin across frames, and a body can idle for N frames
between updates. Wave queries are the CPU cost of floating anything, so amortizing them across frames
— with rigid-body integration carrying the object between updates — is how a fleet of floating props
stays affordable. Declare the latency it buys: a fast boat in a heavy sea is where it shows, and the
fix there is more points per frame for the hero body only, not a global raise.

### Single Layer Water: what the shipped shader interface asks for

The surface is drawn opaque/masked in the base pass; a dedicated pass **after deferred lighting and
before regular translucency** integrates a homogeneous participating medium beneath it. Its material
inputs are the physical ones: **scattering coefficients**, **absorption coefficients** — separately,
not one lumped extinction — a **phase-asymmetry term** (`PhaseG`, forward-scattering toward the sun
at positive values, isotropic at zero), and a colour-scale multiplier on what is seen through the
water; opacity blends the volume's response against the surface BRDF.

Two lessons, and the first is corroboration from a shipped engine:

- **The a/b split with a phase term is the right shader interface.** A widely deployed engine asks
  its authors for `a` and `b` separately plus `g` — the IOPs, under their own names, and refusing
  the lumped extinction that most water shaders expose. That is exactly what terrain-architect's
  `28` exports, what [the vocabulary rule](#the-vocabulary-and-which-half-of-it-you-can-look-up)
  requires, and what this chapter's optics section derives. Where the pipeline has that descriptor, wire
  absorption and scattering to their own inputs instead of pre-summing them: the sum discards the
  forward-scattering behaviour that separates a bright-but-murky silty river from a
  dark-but-transparent tannin one (the CDOM-darkens/sediment-brightens rule).
- **The single depth layer is an architectural limit, not a quality setting.** One water surface per
  pixel means no water seen through water: a river under a bridge over a lake, a fall crossing a
  pool, a pond on an island viewed at a grazing angle across the sea. Where the frame needs stacked
  bodies, this pass cannot express them and per-body sorted transparency is the fallback. Low-end
  paths drop the volume integration and revert to plain translucency, so the look must survive that
  degrade — check it on the lowest tier before art-directing on the highest.

### Bodies are splines, and the splines carve the terrain

Rivers are **open** splines with per-point depth, width and velocity, free to change elevation along
their length; lakes are **closed** loops whose points must all sit at **one elevation**; oceans are
closed loops around a shoreline; **Island** bodies exist only to push terrain above water; **Custom**
bodies are static meshes and — a real trap — do *not* carve terrain and do not use the water mesh.
Carving runs through a Landmass landscape brush writing into a Landscape **edit layer**: it is
non-destructive, and Epic documents that it only edits the landscape when edit layers are enabled —
which is the requirement behind the classic "my river hovers above the ground" symptom (the
symptom→cause link is this chapter's, not Epic's). The brush exposes a depth
curve multiplied by each spline point's depth, falloff by angle or by fixed width, an edge offset
producing a flat shore shelf, and blend modes (alpha / min / max / additive — the last preserving the
underlying detail rather than replacing it).

Three consequences matter on the rendering side. The Landscape-contract half — brush ordering, edit
layers, collision, and the fact that this brush family is not water-specific — is `03`; the
generation-side half is terrain-architect's `27`:

- **The bathymetry the water reads was authored by the same spline that drew the water.** Depth is
  self-consistent by construction, so shore fade, shoaling and the colour ramp cannot disagree with
  the mesh. This is why engine-native workflows get a plausible shoreline nearly for free, and why a
  generator-driven pipeline must be at least as careful: if the depth field and the water surface
  come from different passes, they can drift.
- **A carve is a terrain edit with an owner.** Keeping it in its own edit layer is `07`/`13`'s
  overlay doctrine applied to the *source* data rather than the runtime composite — the same reason
  RVT must not bake transient state.
- **Exclusion volumes carve the volume, not the surface** — a region where gameplay behaves as
  though it were not underwater. That is the one thing a 2.5D depth field structurally cannot
  express (an air pocket under a lake, a dry cave beneath a river), and any water contract shipping
  only a depth raster needs the same escape hatch.

River-to-lake and river-to-ocean junctions get dedicated **transition materials**. Generalize it: the
boundary between two water bodies is a contract like a LOD seam, and it needs a declared owner and
blend — surface height, flow direction, foam phase and optics all change across it, and left
unhandled it reads as two shaders arguing along a line.

### What to check when inheriting a water system

1. Does the zone's extent cover the **worst view** in the game, or does the water end inside the
   draw distance? If it ends, is the far ring present and does it share the atmosphere state (`10`)?
2. **Texels across the narrowest body that matters** in the shared info capture — not zone size.
3. Does the physics/gameplay wave query use the **same evaluator** as the surface, and at what
   amortization latency?
4. Is there **stacked water** anywhere in the level? Find it before an artist does; a single-layer
   path cannot draw it.
5. Are terrain carves in their **own edit layer**, and does re-running generation preserve them?
6. Does the underwater state key off collision that the body actually generates?
7. Is the capture **invalidated** by everything that can move a body, the zone, or the terrain
   beneath it?
8. Instrument it: the engine ships a water-mesh stat (`stat watermesh`) — tile counts and mesh cost
   belong in the budget sheet (`11`) like any other terrain pass.

Honesty about tier: this section is engine documentation (D/N), not measurement, and Water has
changed shape across releases — single render target → texture array, and a single Water Mesh actor
(as documented in the UE4-era pages) → bounded Water Zones with local-only tessellation. Community
reports of version-specific breakage (notably water interaction under World Partition) are F-tier
and worth checking against your release. Treat every
constant above as a shipped default, not a law, and treat the *architecture* — one paged zone, one
fused info capture, a sparse morphing quadtree, one wave evaluator, an opaque-surface volume pass —
as the transferable part.

## Stylized water: same contracts, different bands

Everything in this chapter up to here derives the water's look from physics. A large class of
shipped water — Nintendo's above all — *authors* the look instead, and the doctrine for it is
one sentence: **stylization replaces the band content, never the contracts.** The three bands
(geometry, material, shading) get hand-authored patterns, ramps and flat colour instead of
spectra and BRDFs — but the depth field, shore distance, flow field, `bodyType`, LOD/streaming,
pass ordering and the authority contract are exactly the same machinery, consuming the same
generator handoff. Answer a "make Wind Waker water" request by swapping band content, not by
reaching for FFT cascades and Cox–Munk glitter — that is the name-the-paradigm rule applied to
style.

- **The Wind Waker** (community-documented; Nathan Gordon's graphics analysis is the canonical
  breakdown): a flat-colour sea with **scrolling foam-ring patterns**, layered and wiggled by a
  displacement map, coarser layers at distance. The load-bearing observation: those foam rings
  are a **shore-distance band** — the *same exported field* our realistic shoreline foam
  consumes, drawn as an authored ring texture instead of an advected froth mask. Standard
  recreations use a Voronoi pattern with flow-offset UVs plus intersection foam. Depth still
  drives the colour split; shores still drive the foam; only the *content* is authored.
- **Tears of the Kingdom**: the cel look is community-observed (no first-party rendering talk),
  but the water *physics* has a real one — Nintendo's GDC 2024 talk describes computing **water
  resistance from the projected area along an object's velocity**: probe-style buoyancy/drag,
  i.e. `19`'s machinery, now with a shipped first-party citation.
- **Mario Kart World / Wave Race lineage**: the most instructive case, because it is not a look
  at all — the water is a **drivable gameplay surface**. Vehicles ride the wave geometry, waves
  serve as trick ramps, and surface explosions *raise new waves players trick off* — dynamic
  displacement that is gameplay-authoritative. Consequences, both owned by `19`: the
  one-evaluator rule (physics and renderer sample the same wave function) is **absolute** here —
  on drivable water a mismatch is not a floating-boat artifact, it is a broken road — and
  interactive waves are **gameplay liquid state** under the fluid authority contract:
  deterministic, CPU/server-owned, and network-synchronized in a multiplayer racer. The
  stylized look rides on top of that contract, not instead of it.

Honesty: Nintendo publishes almost nothing about rendering internals — every mechanism claim
above except the TotK physics talk is community reconstruction or press/footage observation
(F-tier), and Mario Kart World's is from launch-window coverage. Say so when citing.

## Pitfalls

- **Baked-wave temptation**: waves painted into exported normals/height "to save runtime cost".
  They cannot respond to wind, shore, or time, alias at distance, and block every system in this
  chapter. Contract violation; fix upstream.
- **Terrain displaced to fake water**: the render-side solid-ocean defect. No swim volume, no
  transparency, no tide. Water is a separate surface, always.
- **Sim patch edge pop**: wakes vanish at an invisible wall. The domain-edge fade contract was
  skipped, or the ring buffer scrolls in fractional texels (must be whole-texel, as clipmaps).
- **FFT cascade tiling from altitude**: fine cascades mip away, the big tile repeats to the
  horizon. Verify from max flight height (`11`); add a cascade or break up with a large-scale
  spectrum/foam variation layer.
- **Choppiness self-intersection shimmer**: chop cranked past the folding limit; `J` negative
  everywhere; crests z-fight themselves. Clamp chop; spend `J` on foam instead.
- **Wind-aligned surf**: swell crosses shallow water at the wind angle and hits the beach
  diagonally — no shore-wave tier, or Tier 1 shipped where the camera lives on the coast. Add
  the shore-wave band; refraction (crests parallel to shore) is the cue the eye checks first.
- **Waves marching through the beach**: displacement still non-zero at depth 0; crests poke
  through the sand. The depth-attenuation ramp is missing or keyed to the wrong depth source
  (scene depth instead of the bathymetry field).
- **Metronome surf**: the whole coastline breaks in unison on one global period. Superpose 2–3
  periods with a group envelope and jitter phase along-shore; sets must arrive irregularly.
- **Sandbars and reefs stay glassy**: shoaling/breaking keyed to shore distance, so offshore
  shoals never shoal. Key everything off the (filtered) depth field; the double surf line over
  a bar should fall out for free.
- **Breakers on cliffs**: spilling foam crawling up rock faces — the break mask fired on depth
  alone. Gate breaker *type* by the beach-slope/breaker-class mask (Iribarren logic): steep
  shores surge, they don't spill.
- **Doubled energy in the blend band**: shore-wave band added on top of un-attenuated ambient
  cascades; a wall of water stands exactly where shoaling also boosts amplitude. Cross-fade
  energy between the systems, never sum them.
- **Break-line dither/flicker**: the `H ≈ 0.78·h` mask evaluated against raw bathymetry noise.
  Filter depth at the wavelength scale before it drives wave response.
- **Foam double-count in the surf zone**: Jacobian whitecaps and breaker foam both firing on
  the same crests. In the shore band, the breaker lifecycle owns foam; fade the Jacobian
  accumulator out with the ambient cascades.
- **One blown highlight instead of a glitter path**: a sharp specular lobe on water. The sun is
  0.53° wide; the sea-slope distribution is tens of degrees. The lobe shape is wrong, not its
  intensity — evaluate a Cox–Munk-width statistical BRDF and add discrete glints on top.
- **Glitter that ignores wind**: wave spectrum driven by wind speed, glitter variance hard-coded.
  Mean-square slope is a function of wind — a mirror-calm sea with a wide glitter path, or a gale
  with a needle highlight, both read as broken. One wind, both consumers.
- **Slicks painted as dark decals**: a surface film's real effect is halving-to-thirding the local
  mean-square slope, which makes it a *smooth mirror patch*, not a stain. Modulate the
  slope-variance field, not albedo.
- **Distant sea turns to plastic**: slope variance from sub-pixel waves discarded instead of being
  folded into BRDF roughness. The lobe collapses toward a Dirac and energy conservation brightens
  what survives. Track the variance tensor and feed it the leftovers (Bruneton).
- **A moiré that beats slowly with distance**: the footprint filter is a box — the literal pixel
  footprint — so each band fades, **returns phase-inverted** through a negative sinc lobe, and
  fades again as the footprint grows. Use a Gaussian at `σ = 0.3748·fp`; nothing else is positive
  and monotone.
- **Filtered water goes plastic instead of aliasing**: variance was removed from the field and
  never given to the BRDF, or given to it as a scalar. It is a tensor, and the reflected ellipse is
  not the slope ellipse — `C = J Σ Jᵀ`, `J = diag(−2, −2cos θ_v)`.
- **Saturated colour speckle on every refracted edge**: three IORs are three delta wavelengths, and
  a step edge at the dispersion scale resolves as a three-tooth comb. It is aliasing of dispersion,
  not dispersion; integrate each channel's *band* over the subsample grid.
- **Glitter comes out as a broad pale smear**: the environment's "sun" is an aureole fitted by eye,
  not a disc. Constrain `n = 2/θ_s² − 1` with a peak of `E_n/Ω_sun` so peak, width and flux all land
  on the sun, and make it the same quantity as the light that casts the shadows.
- **A depth-derived constant applied at every depth**: a penumbra kernel, a slant path or a focusing
  number computed once at the deepest point. Every one of them is a *function* of depth the moment
  the body has a slope, a step or a bench, and each wrong one is diagnosed as a separate bug.
- **CDOM and sediment behind one turbidity slider**: one absorbs and does not scatter, the other
  scatters and barely absorbs, and they produce brown-and-clear against pale-and-opaque. Two axes,
  never one; see [the constituent model](#water-body-optical-identity-where-the-iops-come-from).
- **A white tint reached for as soon as water should look dirty**: the caustic net fades first, then
  shadows lift, then distance hazes — a body colour is the *fourth* symptom of rising `b`, and the
  first three are a contrast multiplier and a haze term away.
- **Chrome-dome horizon**: plain Schlick Fresnel on a low-variance distant ocean drives grazing
  **external** reflectance to ~100%. Use the roughness-aware Fresnel fit and keep Smith masking in the sun lobe.
- **Whitecaps shimmer or vanish at distance**: a binary per-pixel Jacobian threshold cannot be
  filtered. Switch to prefilterable statistical coverage over the footprint's Jacobian mean and
  variance; ground the amount against `W = 3.84e-6·U^3.41`.
- **Deep clear water rendered bright cyan**: reflectance goes as `b_b/a`, and in clear water `b_b`
  is molecular and tiny — deep clear water is near-black. Bright cyan is *shallow* water over a
  bright bottom. Getting this backwards kills every reef drop-off.
- **Tannin-stained water modelled with a turbidity slider**: CDOM absorbs and does not scatter, so
  blackwater is transparent-but-dark (amber shallow, near-black deep). Raising scattering gives
  mud. They are opposite controls.
- **Clear tropical water looks washed out**: blue absorption taken from Smith & Baker (1981),
  which is ~3.4× too high there due to scattering contamination. Use Pope & Fry (1997) above
  380 nm.
- **Surf marches unchanged across the river mouth**: the shore-wave band reads only depth, so
  incoming waves ignore the outflow that should steepen, block, and break them — and rip
  currents in the flow field leave no lanes in the breaker line. Modulate the band by
  opposition to the flow field (wave–current interaction, above); where flow data shows no
  rip/outflow, the missing feature is generation-side — route to terrain-architect.
- **Water too reflective / faintly plastic even when calm**: Fresnel `F0` left at the generic
  dielectric 0.04 (IOR 1.5). Water is IOR 1.33 → `F0 ≈ 0.02`; the default doubles the **external**
  reflectance — the 6.669%-diffuse one, not the 47.617% the same surface shows from below.
- **Every liquid equally reflective**: `F0` hardcoded to water's value. Brine, oil and meltwater
  differ (IOR ~1.31–1.47, `F0` ~0.018–0.036); take `ior` from the `liquidBody` descriptor into
  `specular_ior`.
- **Refraction leaking objects above water**: missing depth reject on the distorted sample. The
  single most common shipped water bug; the fix is four shader lines (above).
- **SSR dropout at grazing/screen edge**: mirror-bright water goes flat exactly at the horizon
  and screen borders. Mandatory fallback chain with brightness-matched cubemap; never ship SSR-only.
- **Waterline crawl on LOD change**: water and terrain refine on different schedules; the
  intersection line steps visibly. Shared SSE currency + shoreline LOD bias (`11` symptom table).
- **Water/land horizon color seam**: water applies a private fog constant while terrain samples
  `10`'s Rayleigh/Mie aerial-perspective state. One atmosphere LUT, one view-depth convention,
  sampled by both paths.
- **Z-fighting of distant flat water vs flat terrain**: at km distance, a lake 20 cm above its
  bed fights the bed in depth. Reversed-Z + camera-relative transforms (`09`); if it persists,
  depth-bias the water or mask terrain under opaque-deep water via the watermask (`06` payload).
- **Swim volume vs visual surface mismatch**: gameplay reads the flat datum while the eye reads
  datum + waves; characters float above troughs and clip through crests. Gameplay queries datum
  plus a cheap CPU-evaluable displacement approximation (the Gerstner sum, or a low-order fit of
  the FFT cascades) — never a GPU readback of the visual mesh, and never raw datum alone in
  heavy seas.
- **Jittered-refraction shimmer under TAA**: refraction UVs built from jittered buffers; the
  water fizzes. De-jitter the sample and provide displaced-surface motion vectors.
- **Waterfall without a feeding flow field**: the construct exists, the river above ignores it.
  Generation-graph defect — route to terrain-architect, do not patch with particles.
- **Stacked water through a single-depth-layer pass**: a river under a bridge over a lake, a fall
  crossing a pool, a pond on an island seen across the sea — the second surface simply is not there.
  This is the shading model's structural limit, not a bug to tune; either the level avoids stacked
  bodies or those bodies go through sorted transparency instead.
- **Absorption and scattering collapsed into one extinction**: one lumped coefficient cannot
  distinguish bright-and-murky (sediment) from dark-and-clear (CDOM), and the phase asymmetry that
  aims scattering at the sun is gone with it. Wire `a`, `b` and `g` to their own inputs where the
  shader takes them, from the `liquidBody` descriptor (terrain-architect `28`).
- **One coefficient driving both the sightline and the light column**: `c` (beam attenuation) and
  `K_d` (diffuse attenuation) differ by 5–20×, so a shader with a single extinction has one of its
  two terms wrong by that factor — the refracted bed too murky, or the depth-tinted column too
  clear. Two coefficients, two paths; both are in the descriptor already.
- **Shared water capture sized to the zone, not the river**: one top-down info texture spanning
  kilometres gives a narrow river a handful of texels across, so banks quantize and flow smears into
  the ground value. Budget by texels-across-narrowest-body; shrink the zone or raise the resolution.
- **Stale water capture**: a body, the zone, or the terrain beneath moved, and nothing dirtied the
  top-down capture — flow points at last frame's channel and the shore fade sits off the bank. Every
  cached field needs its invalidation contract named, including this one; paths that render outside
  the frame loop must force the update.
- **Water hovering above the terrain it was supposed to carve**: the spline-driven brush is writing
  to a landscape edit-layer stack that is disabled, or to a layer the final composite doesn't
  include. Nothing about the water surface is wrong — the bathymetry under it was never written.
- **Two water bodies meeting with no junction contract**: river into lake, lake into sea. Surface
  height, flow, foam phase and optics all change across the line, and un-owned it reads as two
  shaders arguing. Declare a transition material and which side owns the boundary, exactly as for a
  LOD seam.
- **Every floating prop sampling waves every frame**: CPU wave queries are the real cost of buoyancy
  at fleet scale. Update probe points round-robin across frames and let rigid-body integration carry
  the object between samples; raise the rate for hero bodies only, and state the latency.
- **Ocean that stops short of the horizon**: a finite water body large enough to look infinite still
  ends, leaving a band of sky-coloured nothing between the water edge and the horizon line. That gap
  is what the far-distance ring exists for; it must share the datum and the atmosphere state (`10`).
- **Screen-space water: grazing-ray precision**: near the horizon `rayDir.y → 0` and `t`
  explodes; float error shreds the last pixel rows into stripes. Camera-relative math (`09`),
  clamp `t` against the far plane, and fade into the sky/fog band before the guards ever trip.
- **Screen-space water: depth-reconstruction mismatch**: the ray hit is compared against a world
  position rebuilt with the wrong depth convention (reversed-Z, ∞ far, jitter) — water pokes
  through hills or vanishes hugging geometry. One shared reconstruction helper for every
  screen-space pass; never a per-shader reimplementation.
- **Screen-space water: no motion vectors**: nothing was rasterized, so TAA/upscalers see zero
  velocity where waves move — crests ghost and smear. Write analytic velocity: reproject the hit
  point through the previous frame's view-projection (plus wave advection) into the velocity
  buffer.
- **Caustics crawling through a shadow**: the sun is occluded above the water — a shade sail, a
  tree, a diving board — and the caustic pattern plays across the shadow on the bed anyway. The
  sun-visibility gate is missing, or it was sampled at the receiver instead of at the surface
  entry point. Single most conspicuous caustics defect; see
  [the masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped).
- **Caustics added to albedo**: they then survive into shadow, into ambient-only lighting and into
  fog, and stop responding to exposure. Caustics multiply the sun term; they are irradiance.
- **Caustics projected onto terrain only**: the bed lights up and every swimmer, step, ladder and
  prop in the water stays conspicuously unlit by the brightest thing in the scene. Project in world
  space onto whatever the pass finds below the water plane.
- **Scrolled-texture water, revealed by dispersion**: every scale on the surface drifts at one
  speed, so fine ripples and long waves move in lockstep. Real water is dispersive and the long
  components outrun the short ones (~4:1 across a pool-sized band). Costs two seconds of footage
  to catch and no amount of still-frame polish hides it — see
  [Sun glitter](#sun-glitter-the-sparkle-path).
- **Glitter reviewed on a still**: a noise-perturbed specular is indistinguishable from real
  glitter in a screenshot and obviously wrong on a pan, because real glints ride crests and
  trackably travel with them. Judge sparkle on video, always.
- **Sparkle and caustics out of phase**: glitter driven from a noise texture, caustics from the
  wave field (or vice versa). The bright surface glint no longer sits above the bright fold it
  caused. One slope field feeds both, or neither is right.
- **Caustics that animate on flat water**: a Tier 0/1 fake with no coupling to the wave field. A
  flat surface has a constant Jacobian and produces *no* caustic structure — drive the pattern's
  amplitude from the wave amplitude, or the trick announces itself the moment the water settles.
- **A pool rendered with ocean defaults**: swell, whitecaps and a shoreline foam band on a 10 m
  body. The `bodyType` and fetch gates were never applied — see
  [Man-made water](#man-made-water-pools-tanks-and-channels).
- **A pool driven by a wind spectrum**: statistically homogeneous ripple everywhere, no source, no
  reflections, no standing structure. Plausible in isolation and obviously wrong beside a
  photograph, because real pool water is organised by the return jets and the walls. Model the
  basin response, not a sea — [The wave field is a driven
  basin](#the-wave-field-is-a-driven-basin-not-a-spectrum).
- **Sim patch faded out at a wall**: the open-water edge contract applied inside a basin, so wakes
  and jet trains dissolve exactly where they should bounce. In a closed body the domain edge is
  physical — reflect, do not fade.
- **A shader parameter called `waterColor`, or any colour-without-a-distance**: the name is the
  bug, because a colour multiplied into a medium cannot know how far the light travelled. The
  symptoms are three and a photograph refutes each: it stays coloured in shadow, it does not deepen
  with depth, and a white bottom cannot make it pale. Author `transmission_color` **with**
  `transmission_depth`, which is a pair precisely so the mistake is unsayable — see
  [Saying it in OpenPBR](#saying-it-in-openpbr-and-where-the-mapping-stops).
- **Pool colour art-directed into the scatter term**: `L_scatter` is a *result* — an AOP — and
  treated water has `b_b ≈ 0`, so it has no body colour of its own; the cyan comes from bottom albedo attenuated over the down-and-back path. A pool
  tinted through the scattering term reads identically over every liner and at every depth, which
  is exactly the tell.

## Sources & provenance

Moved, whole, to **[`12b-water-provenance.md`](12b-water-provenance.md)** — every entry, every
tier, every `?`, and the `P/T/D/F/N/?` convention restated there so the appendix reads alone.
Nothing was dropped in the move. The tier markers in the prose above resolve against that file;
the derivations they price live in [`12a-water-derivations.md`](12a-water-derivations.md).
