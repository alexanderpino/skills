# Water Rendering

Water on terrain — oceans, rivers, lakes — arrives from the generation side as *still data*: flat
surface datums, a depth field, a flow field. Everything that moves is made here. This chapter owns
the **engine side** of that handoff: water surface geometry and its LOD (meshed or the meshless
screen-space pass), ambient wave synthesis (Gerstner and FFT), the shore-wave band and its tier
ladder, flow-driven river surfaces, local interactive simulation, distance and filtering,
shoreline integration, the transparency/pass-ordering discipline water forces on the frame, what
to pre-cook, and engine-native water systems read as architecture.

⚠️ **The physics lives in a sibling skill, and this chapter routes to it rather than restating
it.** Optics and the interface, IOPs and where a body's colour comes from, glitter, caustics,
aerated water, shoaling and breaking, diffraction, the wave-height population, the pool as an
optics laboratory — all of that is **`water-physics`**, chapter
[`12-water-physics.md`](../../water-physics/references/12-water-physics.md), with its derivations
in that skill's `12a` and its provenance in its `12b`. Every number this chapter quotes is stated
here with its route, so a reader can act without leaving and verify without guessing.

What stays here is what a renderer does: **the diagnostic index below is the router** — symptom on
screen → mechanism → where the mechanism is written up, in either skill — and the pitfall catalogue
at the end is the same map read the other way round. Deep BRDF/scattering math routes to
`physically-based-rendering`; generating water bodies, routing and flow fields routes to
`terrain-architect` (its `03`/`04` hydrology and the `08`/`27` output contract).

Contents: [**Diagnostic index**](#diagnostic-index-symptom-to-mechanism) ·
[The handoff, seen from the render side](#the-handoff-seen-from-the-render-side) ·
[Surface geometry & LOD](#surface-geometry--lod) ·
[Screen-space water: the fullscreen-triangle pass](#screen-space-water-the-fullscreen-triangle-pass) ·
[Ambient waves: Gerstner and FFT](#ambient-waves-gerstner-and-fft) ·
[Shallow water: shoaling, refraction, and breakers](#shallow-water-shoaling-refraction-and-breakers) ·
[Rivers: flow-driven surfaces](#rivers-flow-driven-surfaces) ·
[Interactive simulation patches](#interactive-simulation-patches) ·
[Distance and filtering: why far water turns to plastic](#distance-and-filtering-why-far-water-turns-to-plastic) ·
[Shoreline integration](#shoreline-integration) ·
[Transparency & pass ordering](#transparency--pass-ordering) ·
[What to pre-cook, and what to recompute](#what-to-pre-cook-and-what-to-recompute) ·
[Engine-native water: the UE Water plugin, read as architecture](#engine-native-water-the-ue-water-plugin-read-as-architecture) ·
[Stylized water: same contracts, different bands](#stylized-water-same-contracts-different-bands) ·
[**Pitfalls**](#pitfalls) ·
[Sources & provenance → `water-physics` `12b`](../../water-physics/references/12b-water-provenance.md)

---

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
| Glitter is a broad pale road instead of isolated blinding points | The environment's sun is a **fitted lobe, not a disc**: peak, width and flux were never made to land on the sun together, and the sky lobes carry the direct beam short by a factor of tens. Presents as a tuning problem; is not one | [Sun glitter](../../water-physics/references/12-water-physics.md#sun-glitter-the-sparkle-path) |
| One blown-out highlight instead of a glitter path | The opposite error, in the *lobe* rather than the source: a sharp specular NDF where the slope distribution is tens of degrees wide | [Sun glitter](../../water-physics/references/12-water-physics.md#sun-glitter-the-sparkle-path) |
| A glitter path with the **right width and the right brightness** that is nonetheless a smooth slab — no isolated facets, no dark water between them, and no exposure makes it granular | The slope **pdf** evaluated once per pixel. It is the *ensemble mean* of the glint, so using it declares every pixel to contain the whole ensemble. The width law, the Jacobian and the shadowing can all be exactly right and this will still happen, which is why it reads as a tuning problem and is not one | [Every equation above is about the ensemble](../../water-physics/references/12-water-physics.md#every-equation-above-is-about-the-ensemble-and-a-pixel-is-not-one) |
| Saturated coloured speckle along a refracted silhouette — a step nosing, a ladder rail | Three IORs are **three delta wavelengths**, and a step edge at the dispersion scale resolves as a three-tooth comb. It is aliasing *of* dispersion, not dispersion | [A channel is a band](../../water-physics/references/12-water-physics.md#a-channel-is-a-band-not-a-wavelength) |
| Far water reads flat and plastic *after* filtering was added | The slope variance was correctly removed from the field and **never given a receiver** — or handed over as a scalar, when what was removed is a tensor | [Pick the kernel](#pick-the-kernel-on-purpose-and-give-the-variance-a-receiver) |
| The far surface breaks into a coarse moiré | The other end of the same trade: **no distance-dependent narrowing of the slope distribution**, so a band is still sampled at a footprint wider than itself. The fix narrows the distribution per component; it cannot be applied to the shaded result afterwards, because shading is nonlinear in slope | [Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic) |
| A moiré that *beats* slowly with distance — a band fades, returns, fades again | The footprint filter is a **box**: its sinc has negative lobes to −0.217, so the band comes back phase-inverted as the footprint grows. Gaussian at `σ = 0.3748·fp`, which is the only kernel positive and monotone | [Pick the kernel](#pick-the-kernel-on-purpose-and-give-the-variance-a-receiver) |
| Caustic cell interiors too dark **and** an occluder's shadow too bright, in one frame | One flat ambient standing in for a **directional inter-reflection**: it under-fills where a lit surface should be bouncing and over-fills where nothing should. Errors of opposite sign in one frame are a missing transport path, never a constant that needs raising | [The masking contract](../../water-physics/references/12-water-physics.md#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| The seen bottom reads bright against the sky reflected in the same pixel, and no exposure fixes both at once | **Radiance is not conserved across a refracting interface** — `L/n²` is. The reflected column is air-side and right; the transmitted one is an in-water radiance shipped without its `1/n²`, so it is 1.78× hot. A *relative* error inside one pixel, which is why a grade cannot absorb it | [Radiance is not conserved](../../water-physics/references/12-water-physics.md#radiance-is-not-conserved-across-the-interface) |
| A submerged wall is too dark, and adding more bounce does not help | The refracted sun does not reach it. A surface lit only by a neighbouring diffuse one is capped at **half its own albedo** times that neighbour's radiance — the form factor to an adjoining infinite plane is exactly ½ — so a floor-lit wall is *necessarily* darker than the floor and no gather can be tuned past it | [The masking contract](../../water-physics/references/12-water-physics.md#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| A submerged step's riser, or a shaded wall face, renders flat and near-neutral grey | The third symptom of that same missing leg: the receiver gets **no direct sun and one flat ambient**, so a grazing sky reflection wins by default and the bounce that should carry both colour and the caustic net is absent | [The masking contract](../../water-physics/references/12-water-physics.md#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| A shadowed region on the bed is a dark hole | Two mechanisms, and the second is the bigger one. The sun-visibility gate treated as **binary** when the occluder is fabric or foliage (shade cloth transmits ~15–30% *diffusely*) — and, for **any** occluder including a fully opaque one, the refracted beam's own wander under the slope field, worth 87 mm against a 221 mm shadow at a 21° sun | [The masking contract](../../water-physics/references/12-water-physics.md#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| An **opaque** object's shadow on the bed reads as a reduction rather than a hole, and translucency is reached for to explain it | The **surface**, not the occluder. A facet tilted by `ε` swings the transmitted ray by `\|1 − cos θ_i/(n cos θ_t)\|·ε` — 0.6241 at a 21° sun against 0.2508 at noon — so the field that writes the caustic net smears the shadow's edges into its own interior. The umbra's core really is zero; the fill is transport | [The masking contract](../../water-physics/references/12-water-physics.md#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| The caustic pattern plays across a shadow on the bed | The same gate missing altogether, or sampled at the **receiver** instead of at the surface entry point — metres apart at low sun. Nothing else announces "this is a scrolling texture" so loudly | [The masking contract](../../water-physics/references/12-water-physics.md#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped) |
| Caustics keep moving after the water has gone calm | An authored or cell-noise caustic, **uncorrelated with the surface above it**. A flat surface has a constant Jacobian and produces no caustic structure at all | [The tier ladder](../../water-physics/references/12-water-physics.md#the-tier-ladder) |
| The caustic net fades while the water still looks perfectly clear | Rising `b`, and this is scattering's **first** symptom: contrast along the sun path halves at `b ≈ 0.35 m⁻¹`, where Secchi depth is still ~3 m. A body colour is the *fourth* symptom, not the first | [Water-body optical identity](../../water-physics/references/12-water-physics.md#water-body-optical-identity-where-the-iops-come-from) |
| A caustic net still pin-sharp at 20 m, or blurred away in a 1.5 m pool | A penumbra kernel **computed at one depth and reused**. The sun's disc sets ~0.7 cm of blur per metre; every depth-derived quantity is a *function* the moment the body has a slope, a step or a bench | [Caustics](../../water-physics/references/12-water-physics.md#caustics-the-other-half-of-the-light-path) |
| The submerged bed reads far murkier than the water column above it, or the column far clearer than the bed | **One extinction coefficient driving both paths.** The sightline through the bed is beam attenuation `c`; the depth-tinted column is diffuse attenuation `K_d`; they differ by 5–20×, so a single constant has one of the two wrong by that factor and no value of it is right | [Shading and optics](../../water-physics/references/12-water-physics.md#shading-and-optics) |
| Water uniformly coloured whatever the depth | The depth field ignored — absorption run off a **constant instead of the bathymetry**, so the shallow→deep ramp, the strongest realism cue water has, never happens | [Shading and optics](../../water-physics/references/12-water-physics.md#shading-and-optics) |
| Deep clear water rendered bright cyan | Reflectance goes as `b_b/a`, and in clear water `b_b` is molecular and tiny: deep clear water is **near-black**. Bright cyan is *shallow* water over a bright bottom | [Water-body optical identity](../../water-physics/references/12-water-physics.md#water-body-optical-identity-where-the-iops-come-from) |
| A pool that looks the same over every liner, and at every depth | Its colour was art-directed into the **scatter term**. Treated water has `b_b ≈ 0` and no body colour of its own; what is seen is bottom albedo attenuated over the down-and-back path | [Pool optics](../../water-physics/references/12-water-physics.md#pool-optics-the-colour-is-the-bottom-not-the-water) |
| A pool reads brand-new — one flat liner colour from the coping to the floor — and no amount of caustic or ripple detail rescues it | The liner authored as a **single `base_color`** where a body in service is an albedo **field**, organised around the waterline. The uniformity is the tell, and it is always in the same place | [A liner in service is an albedo field](../../water-physics/references/12-water-physics.md#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate) |
| Weathering visible everywhere else, but the waterline itself is a clean geometric edge with no tide line | The mask is **multiplicative only**. Scale is a *deposit*: it covers the liner and brings its own albedo, so it composes as a coverage lerp — and no multiple of a dark liner is white. The highest-contrast feature on an aged pool is the one a multiply-only pipeline is structurally unable to draw | [A liner in service is an albedo field](../../water-physics/references/12-water-physics.md#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate) |
| A weathering or dirt mask lands at the wrong strength — and by a different amount over a pale bottom than a dark one | The trapped series. Apparent bed brightness is `ρ/(1 − ρ·G_rt)`, whose **elasticity in `ρ` is the gain itself**, so a mask authored in albedo space arrives amplified by a factor that depends on the albedo it acts on, per channel. Contrast up, level down, and a neutral change does not stay neutral. Tuning it against the picture is inverting that by eye | [Where a weathering profile is allowed to come from](../../water-physics/references/12-water-physics.md#where-a-weathering-profile-is-allowed-to-come-from-and-what-the-water-does-to-it) |
| A beach whose wet band fades smoothly into the dry sand, with no boundary anywhere — while the wet/dry albedos check out | The run-up **distribution** painted where its **realisation** belongs. `exp(−(z/σ)²)` is the share of swash cycles reaching a level, so blending by it draws the beach's *time-average*, and an average has no edge: measured, 4/255 across 48 px of face where the realisation gives 36/255 in one row. Same defect class as glitter drawn as its slope pdf and foam drawn as its own mean | [`12a` §10, where the band ends](../../water-physics/references/12a-water-derivations.md#where-the-band-ends--a-distribution-is-not-a-surface-and-it-is-two-masks-not-one) |
| Wet sand reads **brighter** than dry, and moving the albedos does not fix it | One wetness field driving **both** the diffuse darkening and the specular lobe, which puts a mirror on merely *damp* sand. Pore water darkens for minutes; free water reflects and leaves with the swash sheet. Measured, the misplaced lobe was 1.28 against a 1.39 diffuse term over 3.19% of a whole frame — enough to invert the pair on its own | [`12a` §10, where the band ends](../../water-physics/references/12a-water-derivations.md#where-the-band-ends--a-distribution-is-not-a-surface-and-it-is-two-masks-not-one) |
| No bright line where the water meets a wall, a jetty or a stone | The meniscus modelled as an **ambient or roughness lift** rather than a specular strip. A few millimetres of fillet holds every facet orientation, which is why that line survives sun-and-camera geometry nothing else in the frame can reach | [The meniscus line](../../water-physics/references/12-water-physics.md#the-meniscus-line-where-reachability-cannot-fail) |
| Objects above the water smear into it — a dock post, a torso, the coping | The refracted sample was **not depth-rejected**, so it landed on geometry nearer than the water surface | [Shading and optics](../../water-physics/references/12-water-physics.md#shading-and-optics) |
| Fine ripples and long waves drift in lockstep | One scrolled texture advects every scale at **one velocity** by construction. Real water is dispersive — across a pool-sized band the long components outrun the short by roughly 4:1 | [Sun glitter](../../water-physics/references/12-water-physics.md#sun-glitter-the-sparkle-path) |
| Sparkle convincing in a screenshot, obviously wrong on a pan | Noise-perturbed specular is **not a function of the slope field**, so its glints ride nothing; real ones ride crests and stay trackable for a second of footage. The test for glitter is temporal | [Sun glitter](../../water-physics/references/12-water-physics.md#sun-glitter-the-sparkle-path) |
| A wake or a jet train reads as a **seam** up the frame rather than as water | Its axis in *plan* sits within a few degrees of the camera azimuth, so a long ordered train projects as a near-vertical stripe. Obliquity in plan is the control; amplitude is not | [The wave field is a driven basin](../../water-physics/references/12-water-physics.md#the-wave-field-is-a-driven-basin-not-a-spectrum) |
| Swell crossing shallow water at the wind angle, hitting the beach diagonally | Wave phase taken from the **wind** rather than from a depth-driven travel-time field, so nothing refracts. Crests parallel to every shore is the cue the eye checks first | [Shallow water](#shallow-water-shoaling-refraction-and-breakers) |
| My water is the wrong colour against a reference photograph, and no constant fixes it without breaking something else | The **photograph's sun was never computed**, so the illuminant is an unpinned free variable soaking up the residual. From a place, a date and a time it is fully determined — and its elevation alone moves the transmitted share (87.8→97.8%) and the slant path to the bed (1.96→1.53 m) between two ordinary afternoon suns | [The illuminant is part of the comparison](../../water-physics/references/12-water-physics.md#the-illuminant-is-part-of-the-comparison-what-cancels-and-what-does-not) |
| Shadows in the render point plausibly but disagree with the reference by tens of degrees, while the sun's *height* is clearly right | The azimuth's `acos` branch, taken from the wrong one of two conventions. Elevation comes from `cos ζ`, which has no branch, so it stays correct and every other check still passes — a 72° error that reads as a shading problem | [`10`, the quadrant trap](10-lighting-shadows.md#the-quadrant-trap-and-why-the-elevation-stays-right) |
| A water-to-deck ratio disagrees with the reference, and the low sun is offered as the explanation | Both are **horizontal receivers**, so `sin h` and the air-mass attenuation are identical on them and cancel exactly in the ratio. What does *not* cancel is only the Fresnel entry share and the slant path — 1.25× between a 21° and a 57° sun, and nothing beyond that is available | [The illuminant is part of the comparison](../../water-physics/references/12-water-physics.md#the-illuminant-is-part-of-the-comparison-what-cancels-and-what-does-not) |
| Absolute sRGB triples read off a reference photograph will not reconcile with the render, and the disagreement changes between frames of the same pool | The camera, not the renderer: automatic white balance rescales chromaticity toward neutral hardest where the subject is most saturated, a display tone curve rescales level non-uniformly, and a Display P3 file read as sRGB shifts a water pixel's R/B by 28–52% while leaving the stone beside it near-untouched | [`11`, seven ways](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one) |
| Every vertical surface under the water is streaked with fine vertical bars that do not change up the face — walls, risers, pilings, a hull | The caustic map sampled at the receiver's own world `(x, y)`, with **no height term**. A bed pattern with structure at its texel scale and none in `z` is a comb. Not a resolution problem: quadrupling the map and the gather moved it by 0.7% | [A caustic on a vertical face](../../water-physics/references/12-water-physics.md#a-caustic-on-a-vertical-face-is-not-the-beds-pattern-at-that-faces-own-position) |
| A pool interior is too dark by a factor of two to seven, or washed out, and every constant that fixes it breaks the surface | **"Surface reflection" taken in the wrong sense.** One interface carries two diffuse constants: `R_ext = 6.669%`, a loss on the way in, and `R_int = 47.617%`, a trap on the way out. They differ by **7.14×**; swapping both is **2.37×** of darkness, and swapping only the internal one desaturates while passing every luminance check | [Surface reflection names two opposite things](../../water-physics/references/12-water-physics.md#surface-reflection-names-two-opposite-things-a-loss-and-a-trap) |
| Everything near the rim of Snell's window is mush in an underwater shot while the zenith is fine — the shoreline, a jetty, a person standing at the edge | The environment indexed from **below**. Snell's Jacobian `cos θ_a/(n² cos θ_w)` vanishes at grazing, so the entire air world under 10° of elevation lands inside **3.75%** of the window's solid angle. A `θ_w`-uniform lookup starves that annulus 8.5× and over-serves the zenith 7.6×. Index by the air-side cosine instead | [What the window actually contains](../../water-physics/references/12-water-physics.md#what-the-window-actually-contains-and-why-the-rim-is-where-the-world-is) |
| An overhead occluder — a shade sail, a canopy, a hull — expected to fill Snell's window and barely appearing in it | The same Jacobian, run forwards. A panel 8–12 m away and 2.4 m up sits at **72–77° from the vertical**, which Snell compresses into **1.44°** of polar angle. What dominates a window instead is whatever stands at the observer's own edge, seen at grazing all the way round | [What the window actually contains](../../water-physics/references/12-water-physics.md#what-the-window-actually-contains-and-why-the-rim-is-where-the-world-is) |
| A floating body shows no refracted split at its waterline, and the refraction is checked and correct | Its own **meniscus** hides it. The split needs `R(1 − sin(β + θ_w)) > z_w·sin θ_w`; on a 221 mm ball a 2.31 mm climb beats the left-hand side by 22.6×. "No split" is a prediction with a threshold — and with `z_w = 0` the threshold is still a draught over **12.55%** of the diameter, which no inflatable reaches | [`12a` §3](../../water-physics/references/12a-water-derivations.md#a-floating-body-and-the-split-its-own-meniscus-hides) |
| One surface in the frame is off by a factor near 3.14 and everything around it is right | An **irradiance used as a radiance**. `E` and `L` differ by π and a shading term, and nothing in a shader's types says which a triple holds. A bare constant near 3.14 or 0.318 in a shading term with no derivation beside it is this bug | [`11`, an irradiance used as a radiance](11-verification-failures.md#an-irradiance-used-as-a-radiance) |
| A submerged wall reads sky-coloured and structureless while its level looks about right | The upper half of a vertical face's hemisphere filled with sky. It is **22% Snell window and 78% mirror**; a flat `0.5` over-gives the sky by ×1.96 and under-gives the pool's own upwelling field by the same partition, so level survives while hue and caustic structure do not | [What a submerged vertical face sees of the sky](../../water-physics/references/12-water-physics.md#what-a-submerged-vertical-face-sees-of-the-sky) |
| Water is subtly dark after a lookup table replaced a computed transport, and no index or format bug explains it | An integral **split into two tables and multiplied**. Attenuation and escape share the water-side cosine and are correlated `+0.76`, so the product of the means understates by 19.4% in red; the trapped leg is correlated the other way, so the composed result moves only 2.8% and hides it | [Attenuation and escape do not factorise](../../water-physics/references/12-water-physics.md#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them) |
| The suite is green, has been green for months, and the picture is visibly wrong in the quantity the suite is named after | A test that **borrows one name and writes the rest itself**: its own inputs, its own transport, a physics identity for a right-hand side. It exercises one function and certifies a law that would hold for almost any implementation | [`11`, the eighth way](11-verification-failures.md#the-eighth-way-is-about-the-test-not-the-measurement) |
| Every wall at a waterline is lit identically from the sky, on the sunny side and the shaded side alike | One "sky ambient" handed to receivers of different orientation. A horizontal face weights the sky by `cos θ sin θ`, a vertical one by `sin² θ`; they agree at exactly ½ for a uniform sky and nowhere else, and the aureole gives the vertical case an **azimuth** a constant cannot carry — 1.23× between a sun-facing and a sun-averted band of one pool | [An illuminant per receiver](../../water-physics/references/12-water-physics.md#an-illuminant-per-receiver-and-what-that-costs-at-a-waterline) |
| A dry band above the water reads flat and slightly cold, and no ambient value fixes both it and the deck | Its **lower half** was given the pool's upwelling and not the *sky reflected in the water*. The `sin²θ` weight peaks at the horizon, where a water surface reflects **0.2112** rather than the 0.0206 of normal incidence — a factor of 10.3, and 23% of what that half receives in green | [An illuminant per receiver](../../water-physics/references/12-water-physics.md#an-illuminant-per-receiver-and-what-that-costs-at-a-waterline) |
| The pool reads *desaturated* rather than dark — the liner's colour is weak but the level is plausible | The interreflection series **truncated at one bounce**. The error is chromatic because bed albedo is: 7.8% in green and 10.5% in blue against 1.1% in red on this liner, so it washes the colour out while surviving every luminance check. The second bounce buys back three quarters of it | [The upgoing half, traced](../../water-physics/references/12-water-physics.md#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point) |
| A submerged wall's level looks right, and correcting a term you know is wrong barely moves it | The **sky and the mirror are two halves of one hemisphere**, so over-giving one under-gives the other and any measurement of the total is blind by construction. Zero the sky: the face must fall to **77.7%**, not to zero and not to half | [The upgoing half, traced](../../water-physics/references/12-water-physics.md#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point) |
| An aged pool's dirt is all in the shade | A grime mask driven by **ambient occlusion**. Biofilm needs stagnation; photosynthetic algae need stagnation *and light*, so the worst place is the **sunlit stagnant** corner. One accessibility mask is right for one mechanism and exactly backwards for the other | [Fouling in the corners](../../water-physics/references/12-water-physics.md#fouling-in-the-corners-from-an-algorithm-rather-than-from-a-texture) |
| Weathering present but perfectly even — an aged surface that is uniformly grey rather than blotchy | Patchiness is **feedback, not noise**: deposit roughens, roughness holds more deposit, and above a threshold coupling the uniform state is linearly unstable. A few iterations give it; a noise octave fakes it and has to be re-authored per basin | [Fouling in the corners](../../water-physics/references/12-water-physics.md#fouling-in-the-corners-from-an-algorithm-rather-than-from-a-texture) |
| An outdoor pool with a geometrically clean waterline and no band at all | The `neglect` control shipped at a **zero default**. Most pools in service carry a band, so a pristine liner is the special case; a renderer defaulting to zero age reads as CG by default, and the same holds for every persistent liquid line — tanks, locks, harbour walls, hulls | [Fouling in the corners](../../water-physics/references/12-water-physics.md#fouling-in-the-corners-from-an-algorithm-rather-than-from-a-texture) |
| The sea is green everywhere, or blue everywhere, whatever the wave is doing | A tint on the water **body**. One backlit breaking wave refutes it in a single exposure: the face reads saturated green while the same water two metres away reads grey-blue, so the colour is the **path** and must vanish when the path does | [The surf zone](../../water-physics/references/12-water-physics.md#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot) |
| The saturated green backlit face never appears in the surf, however tall or steep the wave field is made | **Not a tuning shortfall — a bar on the representation.** A sightline through a wave crosses the surface twice, so the entry and exit inclinations must sum to `2(90° − θ_c)` = **82.96°**; Stokes' 120° corner caps a wave of permanent form at 30° a face, so its best sum is 60°. No single-valued height field of a steady wave reaches it, at any height, order or grid | [The 30° ceiling](../../water-physics/references/12-water-physics.md#the-30-ceiling-a-single-valued-crest-cannot-be-read-lengthwise) |
| The whole nearshore is one continuous soft grey band with a smooth cross-shore hump, both of its edges continuous curves, and no bubble texture or alongshore break-up at any scale | The foam **coverage** painted where its **realisation** belongs. `1 − exp(−m)` is the void probability of a Boolean model, so alpha-blending by it draws `E[χ]` and never `χ` — and an expectation that varies smoothly in `x` *is* an airbrush gradient. Measured: correlation length 2.25 % of the patch width against 0.3–0.8 % in photographs, and clot runs of 328 px in a 500 px box against 8–52 px. Fourth instance of this defect class in this chapter | [`12a` 12a·13](../../water-physics/references/12a-water-derivations.md#13--the-foam-is-a-boolean-model-and-a-coverage-is-its-first-moment) |
| Foam that sits *seaward* of where the wave visibly breaks, and is far too thin through the saturated surf zone | The deck laid from a **random-sea exceedance** (`Q_b`) handed a monochromatic train — a category error, because there is no height distribution for the closure to operate on. The two statements differ in **placement**, not only in level: an exceedance peaks where `H/d` *approaches* `γ`, the dissipation where the wave *is* breaking. Measured: the exceedance's maximum lands on the first breaking cell at every cut, the roller's 41–68 cells shoreward | [`12a` 12a·13](../../water-physics/references/12a-water-derivations.md#which-breaking-statement-lays-the-deck-and-the-two-differ-in-placement) |
| One long unbroken line of surf running the length of the beach, arriving on a metronome, with every wave the same size | **The waves have no height distribution.** `η = (H/2)cos φ` reads one `H` field, so the crest-to-crest CV at a point is machine zero against a Rayleigh sea's **0.5227**. It is not short-crestedness: refraction *straightens* crests (Snell conserves `k_y`, so alongshore spread is invariant) — what breaks a line up is that individual waves break at different **depths** because they have different heights | [A surf line breaks up](../../water-physics/references/12-water-physics.md#a-surf-line-breaks-up-because-the-waves-are-not-the-same-height) |
| A component sum was built for exactly this, and the surf line is still a metronome | The components were spent on **directions instead of frequencies**. At a fixed point every component sharing a frequency keeps a fixed relative phase forever, so `n_θ` of them collapse into one quasi-monochromatic contribution. `n_f = 1 × 256 directions` gives a crest CV of **exactly zero** — short-crested and monochromatic at once | [A surf line breaks up](../../water-physics/references/12-water-physics.md#a-surf-line-breaks-up-because-the-waves-are-not-the-same-height) |
| One line of surf on a bed that has a bar, or a bar built and only one line of white on it | **The count of surf lines belongs to the offshore boundary condition, not to the bed.** One offshore partition has one depth where `H → γd` and builds one bar however long the loop runs; a swell plus a wind sea builds two. And if the bed grows two while the shader lays foam from the carrier alone, every physics test passes and no pixel shows it | [Shoal awareness](#shoal-awareness-is-depth-awareness-not-distance-awareness) |
| Open water that carries a faint permanent haze of whitecaps at any wind, including none | A foam **floor**, or a wind-independent whitecap constant. `W(0) = 0` exactly — Monahan's law has no offset — so a calm-sea control must show **zero** open-water foam pixels while the shore keeps its surf. Also check the composition: coverages do not add, **covering measures** do, and a clamped sum hides the error instead of fixing it | [Where the white comes from](../../water-physics/references/12-water-physics.md#where-the-white-comes-from-two-sources-one-field-and-coverages-do-not-add) |
| Surf built as one particle system, and it reads as confetti over glass | **Three whites, three materials**: the blanket behind a break is a *coverage mask*, the opacity inside the wave mouth is a *participating medium*, the spray is *particles* — and the particles are the **smallest** share. All three are built on the same `1 − 1/n²` wall reflectance and share nothing else — and none of them whitens *because* of it: a bubble backscatters `b_b/b = 0.023`, so the white is multiple scattering | [Aerated water](../../water-physics/references/12-water-physics.md#aerated-water-foam-spray-and-whitewater) |
| Water is right in the near field and goes black — or absurdly saturated — toward the horizon, and no fog or exposure setting fixes both halves | **The straight ray used as the traversal distance.** `d/cos θ_a` diverges at grazing; the transmitted ray refracts and `d/μ_w` is bounded by `1.33 d`. Median 12.1%, p95 46.5% on a measured frame, fixed by one `sqrt` | [Screen-space water, step 4](#screen-space-water-the-fullscreen-triangle-pass) |
| Volumetric foam or a bubble plume that goes bright white but you can still see the bed through it | `1 − 1/n²` spent as a **backscatter fraction** instead of a wall reflectance — 19× too much return, and the transmittance that should have fallen with it never does. A conservative slab has `R = τ'/(1 + τ')` and `T = 1 − R`; whitening without hiding means the model has `R` and not `T` | [Aerated water](../../water-physics/references/12-water-physics.md#aerated-water-foam-spray-and-whitewater) |
| A white plume after a wave hits rock that either vanishes leaving nothing or lingers white far too long | **Two clouds with one decay curve.** Entrained air rises and bursts in seconds; suspended sediment settles over minutes and advects. They overlap in space and are separated by *lifetime*, not appearance | [The surf zone](../../water-physics/references/12-water-physics.md#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot) |
| The bed disappears convincingly inside the break but stays visible everywhere else in the surf zone, and turning the foam up does not fix it | **The entrained air credited for the suspension's work.** Both hide a bed and they are four orders of magnitude apart — a measured `2.76×10⁻⁵` for the suspension against `0.152` for the plume, with the plume simply *absent* below its own depth. Model both, and check each absolutely rather than as a ratio | [The surf zone](../../water-physics/references/12-water-physics.md#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot) |
| Water in the surf zone that is exactly as clear on every frame while the waves break through it | `b` treated as a **material constant** where it is a state variable produced by the dynamics: the waves suspend the bed, the backwash erodes, turbidity pulses at the wave period. The one optical property a still frame cannot verify | [Water-body optical identity](../../water-physics/references/12-water-physics.md#water-body-optical-identity-where-the-iops-come-from) |
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
| `liquidBody[i]` | Per-body record (terrain-architect `28`, registered in its `08`/`27`): `bodyType` (sea / lake / pond / river / stream / estuary / wetland), `ior`, derived optics (`a_RGB`, `b_b_RGB`, `c_RGB`, `K_d_RGB`, scatter colour), the fetch/exposure field for enclosed water, causal state, QA fields (Secchi, Jerlov/Forel-Ule class) | **`bodyType` selects the surface model**: sea gets swell + tide + nearshore circulation; a lake gets **fetch-limited wind waves only** — no swell, no current (suppress the residual-swell component of [Calm water](../../water-physics/references/12-water-physics.md#calm-water-the-low-energy-regime) on lakes, and scale the wave spectrum by the fetch field); rivers get flow. Also **the source of the medium's IOPs and of the surface's `specular_ior`** — see [Water-body optical identity](../../water-physics/references/12-water-physics.md#water-body-optical-identity-where-the-iops-come-from), and [the vocabulary rule](../../water-physics/references/12-water-physics.md#the-vocabulary-and-which-half-of-it-you-can-look-up) for why the record's own field names are kept while what they feed is named in OpenPBR and IOP terms. `ior` populates `specular_ior`, which drives surface Fresnel and refraction bending (never hardcode 1.33); beam attenuation `c` drives sharp sightlines; `K_d` drives the diffuse depth column |

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
4. **Shade**: everything in [Shading and optics](../../water-physics/references/12-water-physics.md#shading-and-optics) applies unchanged at the
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
[Shading and optics](../../water-physics/references/12-water-physics.md#shading-and-optics) still owns the crossing frame.

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
  ([below](../../water-physics/references/12-water-physics.md#diffraction-is-not-refraction-and-nothing-above-contains-any-of-it)).
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
  ([A peaked crest is not a steep face](../../water-physics/references/12-water-physics.md#a-peaked-crest-is-not-a-steep-face-one-harmonic-two-moments)).
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
beach. Double surf lines over bars are a signature of real coasts, and they are *impossible*
when the surf system is keyed to the shoreline distance field. Shore distance drives only what
genuinely belongs to the waterline: run-up, wet sand, and the final foam edge.

⚠️ **They do not, however, "fall out for free" from the bathymetry, and this chapter said so for
several revisions.** Depth awareness is *necessary* and it is not sufficient: **the number of surf
lines belongs to the offshore boundary condition, not to the bed.** Run a morphodynamic loop under
one offshore partition and it builds **one** bar, however long you run it and whatever the profile —
one wave height and one period have one depth at which `H → γd`, and the loop's own feedback parks
the bar there. Give the same bed **two** partitions — a swell and a locally generated wind sea, e.g.
`(0.5, H₀ = 1.50 m, T = 9.0 s)` and `(0.5, H₀ = 0.89 m, T = 4.4 s)`, the weights being each system's
share of the transport moment — and it builds two, each at its own `H_b/γ`. On the shipped scene the
two lines sit at `x` = **611 m** and **683 m**, and both carry foam in the frame.

**The control is what makes this a finding rather than a coincidence, and it belongs to the
generator side.** A **bare monotone Dean ramp with no bar on it at all** carries **two breakpoints**
under a two-partition sea, because two partitions break at two depths on *any* profile. So the
**count** is the boundary condition's; what the **bed** contributes is the **separation** (×1.94 on
one measured pair), and the criterion for "two and not one" is the Dally length
`|x_b1 − x_b2| > (d_b1 + d_b2)/(2K)` — 48.5 m measured against 11.7 m needed, holding under ±50% in
`H_s` and ±40% in `T_p` and failing correctly at `H_s × 2`, where the "wind sea" is the same size as
the swell and breaks in the same water. The full derivation, its sweep and the quadrature trap it
rules out are in
[terrain-architect `12`](../../terrain-architect/references/12-glacial-coastal.md).

The consequences are worth stating separately because they pull in opposite directions from the
usual intuition:

- **Sweeping the partition weights moves the bars' amplitudes and not their depths.** Each crest
  depth is set by its own partition's `H_b/γ`; amplitude is what transport pays for. So "how much
  wind sea" is a *contrast* control, not a *position* control.
- **A single-partition run is the correct control and must stay reachable**, arithmetically
  identical to the no-climate path. Otherwise every number measured on the one-bar bed silently
  stops being comparable the day the second partition arrives.
- **The renderer has to lay foam from the union of every partition's roller**, not from the
  carrier's alone — `1 − Π(1 − f_p)`, since two rollers from independent wave systems overlap at
  random. Summing them exceeds 1 where the surf zones overlap and puts more white on the water than
  there is water. A bed that grows two bars while the shader whitens one is the
  [derived-and-never-drawn](../../water-physics/references/12-water-physics.md#the-30-ceiling-a-single-valued-crest-cannot-be-read-lengthwise) failure
  in its most photogenic form: every physics test passes and no pixel shows it.

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
or dead-calm water still produces a Dirac (see [Calm water](../../water-physics/references/12-water-physics.md#calm-water-the-low-energy-regime)).

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
| **Per frame, full** | every frame | the wave field; the caustic map as [tier 2](../../water-physics/references/12-water-physics.md#the-tier-ladder) |
| **Per pixel** | never stored | Fresnel; the sun lobe; the roughness correction |

Two consumption tests sit beside the cadence one, and they are why things get baked that are not
expensive:

- **Fusion.** The Water Info Texture is not tabulated because its parts are costly — they are not.
  It is tabulated because it replaces many scattered lookups with one coherent sample. A rule that
  prices only per-sample cost cannot see this.
- **Divergence.** A term confined to a thin screen-space curve — the waterline, a shoreline — is
  **divergence-bound, not ALU-bound**: it clips a few lanes of many warps and masks the rest. A
  table does not fix that; running the term on a coherent band does, which is why the chapter puts
  the meniscus on [a decal or a junction shader](../../water-physics/references/12-water-physics.md#the-meniscus-line-where-reachability-cannot-fail)
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
  none. This is the same failure the [interface's `1/n²`](../../water-physics/references/12-water-physics.md#radiance-is-not-conserved-across-the-interface)
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
[count of free parameters](../../water-physics/references/12-water-physics.md#water-body-optical-identity-where-the-iops-come-from) the
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
  `28` exports, what [the vocabulary rule](../../water-physics/references/12-water-physics.md#the-vocabulary-and-which-half-of-it-you-can-look-up)
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
  never one; see [the constituent model](../../water-physics/references/12-water-physics.md#water-body-optical-identity-where-the-iops-come-from).
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
  [the masking contract](../../water-physics/references/12-water-physics.md#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped).
- **Caustics added to albedo**: they then survive into shadow, into ambient-only lighting and into
  fog, and stop responding to exposure. Caustics multiply the sun term; they are irradiance.
- **Caustics projected onto terrain only**: the bed lights up and every swimmer, step, ladder and
  prop in the water stays conspicuously unlit by the brightest thing in the scene. Project in world
  space onto whatever the pass finds below the water plane.
- **Scrolled-texture water, revealed by dispersion**: every scale on the surface drifts at one
  speed, so fine ripples and long waves move in lockstep. Real water is dispersive and the long
  components outrun the short ones (~4:1 across a pool-sized band). Costs two seconds of footage
  to catch and no amount of still-frame polish hides it — see
  [Sun glitter](../../water-physics/references/12-water-physics.md#sun-glitter-the-sparkle-path).
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
  [Man-made water](../../water-physics/references/12-water-physics.md#man-made-water-pools-tanks-and-channels).
- **A pool driven by a wind spectrum**: statistically homogeneous ripple everywhere, no source, no
  reflections, no standing structure. Plausible in isolation and obviously wrong beside a
  photograph, because real pool water is organised by the return jets and the walls. Model the
  basin response, not a sea — [The wave field is a driven
  basin](../../water-physics/references/12-water-physics.md#the-wave-field-is-a-driven-basin-not-a-spectrum).
- **Sim patch faded out at a wall**: the open-water edge contract applied inside a basin, so wakes
  and jet trains dissolve exactly where they should bounce. In a closed body the domain edge is
  physical — reflect, do not fade.
- **A shader parameter called `waterColor`, or any colour-without-a-distance**: the name is the
  bug, because a colour multiplied into a medium cannot know how far the light travelled. The
  symptoms are three and a photograph refutes each: it stays coloured in shadow, it does not deepen
  with depth, and a white bottom cannot make it pale. Author `transmission_color` **with**
  `transmission_depth`, which is a pair precisely so the mistake is unsayable — see
  [Saying it in OpenPBR](../../water-physics/references/12-water-physics.md#saying-it-in-openpbr-and-where-the-mapping-stops).
- **Pool colour art-directed into the scatter term**: `L_scatter` is a *result* — an AOP — and
  treated water has `b_b ≈ 0`, so it has no body colour of its own; the cyan comes from bottom albedo attenuated over the down-and-back path. A pool
  tinted through the scattering term reads identically over every liner and at every depth, which
  is exactly the tell.

## Known gaps in the physics, and where to read them

`water-physics` keeps a register of what it does **not** cover, each with a verified primary
source: [`12c-uncovered.md`](../../water-physics/references/12c-uncovered.md). Six entries, and
several are things a terrain renderer asks for by name — **ice** (frozen lakes, glaciers, sea ice:
optically scattering-dominated, not tinted water), the **free jet in air** (fountain, hose, water
pistol — one phenomenon along a Weber axis the chapters derive the endpoint of but not the
parameter), **water entry** (the splash crown, the cavity, and the Worthington jet that fires
*after* the impact burst most renderers stop at), **thin-film iridescence** (oil sheen),
the **hydraulic jump** (rapids and weirs as standing structure rather than travelling waves), and
**vortex structure**.

Read it before assuming an absence is an oversight. It also records the pattern that found them:
the subject was usually present and the *unifying axis* was missing.

## Sources & provenance

Every tier, citation and `?` behind the water material — this chapter's and the physics it routes
to — lives in one place: **`water-physics`'s
[`12b-water-provenance.md`](../../water-physics/references/12b-water-provenance.md)**. Read it
before citing anything from either chapter. The engine-native section's claims are `D`/`N`-tier
vendor documentation and drift by release; re-verify constants at time of use.
