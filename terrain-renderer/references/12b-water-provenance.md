# Water Rendering — Sources & Provenance

The provenance appendix to [`12-water-rendering.md`](12-water-rendering.md). It was that
chapter's last section until it stopped being a section: 428 lines, the fastest-growing part of
the file, and the part a reviewer opens on its own rather than after reading everything above it.
The move removed nothing — every entry below stood in `12` and says what it said there. Four
changes are the whole of the difference, and they are named rather than left to be discovered: the
entries' section links now carry the file name they used to imply; and the **wall as a light
carrier** and **wake geometry** entries each grew one clause, because `12` gained two claims in the
same pass that they are the right home for — a submerged riser's grey, and a wake's aim against the
camera azimuth. Both clauses price *that* basin, like everything else those two entries carry.

Three files, one chapter: `12` is the doctrine and the mechanisms, `12a-water-derivations.md` is
the mathematics and pseudocode behind the results it quotes, and this file is where the numbers in
both say where they came from. Read it before citing anything out of that chapter, and read it
*first* for anything the chapter marks `?` — the marker means this run could not close the claim,
and repeating the number without the marker is exactly how an unverified figure becomes a cited
one.

## Provenance tiers

The convention is `00-index.md`'s, restated here so the appendix reads on its own:

| Tier | Meaning | How to talk about it |
|---|---|---|
| **P** | **Paper/book.** Peer-reviewed or formally published, widely known to contain the technique. | Cite it directly — but check whether the entry verified the *content* or only the attribution. |
| **T** | **Talk.** GDC / SIGGRAPH Advances / vendor conference presentation. | "Presented in <talk>"; never dress as peer review. Slides may be offline; the idea is the citation. |
| **D** | **Docs, or measured here.** Official vendor/engine documentation — or a figure measured on `reference-impl/`. | Cite the docs and flag that engine docs drift by release; for a measured figure, name what it was measured on. |
| **F** | **Folklore.** Universal practice with no canonical source; a blog post, a repo, or nothing. | "No canonical paper; standard practice is…" Naming a blog is fine — as a blog. |
| **N** | **Named feature.** An engine's or game's branding over one or more techniques. | Name the underlying technique family. |
| **?** | **Claimed but unverified.** Plausible, commonly repeated, not confirmed. | **Do not cite.** Say it needs checking, and search if you can. |

Two local extensions, both load-bearing in a chapter this measurement-heavy:

- **`D` does double duty** — engine documentation *and* a quantity measured on the reference
  implementation. The two are told apart by the entry, which always says which; a measured `D` is
  a property of *that* pool, that sun and that basin, and what transfers is the mechanism it
  prices, never the number.
- **Composite tiers mean the halves are true of different parts of the claim.** `P/D` is published
  physics with a figure measured here; `P/?` is a structure that is standard carrying a constant
  that is not; `D/F` is a documented feature with an undocumented practice around it; `P/synthesis`
  is a first-principles chain assembled here from published pieces. Split them when quoting: cite
  the `P` half, flag the other.

**Never upgrade a tier to satisfy a question, and never fabricate a citation.** If a claim lands on
`?`, say so and offer to search. The consolidated list of what this chapter is least sure of — the
entries a reviewer should spend verification effort on first — is the `12` block of the
least-confident-claims ledger in `00-index.md`.

## Sources & provenance

- **P** — Gerstner trochoidal waves: classical fluid mechanics (19th-century); the closed-form
  crest-sharpening wave sum used across the industry.
- **P** — Tessendorf, "Simulating Ocean Water" (SIGGRAPH course notes, early 2000s): the FFT
  ocean — spectrum sampling, inverse-FFT displacement, choppiness, Jacobian folding. The canon
  for every spectral ocean shipped since. 2004 revision:
  [coursenotes2004.pdf (Clemson)](https://people.computing.clemson.edu/~jtessen/reports/papers_files/coursenotes2004.pdf).
- **P** — Phillips and JONSWAP spectra: oceanography literature, imported into graphics via
  Tessendorf's notes; parameter details in graphics use are simplified from the originals.
- **T** — Vlachos, "Water Flow in Portal 2" (SIGGRAPH 2010, Advances in Real-Time Rendering
  course): flow mapping — dual phase-offset samples with triangle-wave blend; the canonical
  river-surface technique.
  [Slides PDF (Valve)](https://cdn.akamai.steamstatic.com/apps/valve/2010/siggraph2010_vlachos_waterflow.pdf).
- **P** — Bruneton, Neyret & Holzschuch, "Real-time Realistic Ocean Lighting using Seamless
  Transitions from Geometry to BRDF" (Computer Graphics Forum 29(2), 2010): the principled
  treatment of wave detail crossing from geometry band to shading band — the slope-variance
  tensor, the roughness-aware Fresnel fit, and the variance-filtered environment fetch used in
  [Distance and filtering](12-water-rendering.md#distance-and-filtering-why-far-water-turns-to-plastic).
  [HAL open access](https://inria.hal.science/inria-00443630).
- **P** — Cox & Munk, "Measurement of the Roughness of the Sea Surface from Photographs of the
  Sun's Glitter" (Journal of the Optical Society of America 44(11), 838–850, 1954): the
  sea-surface slope distribution and its wind-speed regressions; the foundation of every
  statistical glitter model. Wind speed is referenced at **12.5 m**, and the fit is calibrated
  only over 1–14 m/s — do not extrapolate to storm winds. Verified 2026-08 against the paper.
  [DOI 10.1364/JOSA.44.000838](https://doi.org/10.1364/JOSA.44.000838).
- **P** — Ross, Dion & Potvin, "Detailed analytical approach to the Gaussian surface
  bidirectional reflectance distribution function specular component applied to the sea surface"
  (JOSA A 22(11), 2442–2453, 2005): the Gaussian-slope microfacet BRDF with Smith masking that
  Bruneton's model evaluates. The analytic base tier for glitter.
- **P** — Discrete-glint rendering lineage: Jakob, Hašan, Yan, Lawrence, Ramamoorthi & Marschner,
  "Discrete Stochastic Microfacet Models" (ACM TOG 33(4), SIGGRAPH 2014); Yan, Hašan, Jakob,
  Lawrence, Marschner & Ramamoorthi, "Rendering Glints on High-Resolution Normal-Mapped Specular
  Surfaces" (ACM TOG 33(4), 2014); Yan, Hašan, Marschner & Ramamoorthi, "Position-Normal
  Distributions for Efficient Rendering of Specular Microstructure" (ACM TOG 35(4), 2016);
  Zirr & Kaplanyan, "Real-time Rendering of Procedural Multiscale Materials" (I3D 2016);
  Chermain, Sauvage, Dischler & Dachsbacher (CGF 39(7), Pacific Graphics 2020) and Chermain,
  Lucas, Sauvage, Dischler & Dachsbacher (I3D 2021) for real-time procedural glints;
  **Deliot & Belcour, "Real-Time Rendering of Glinty Appearances using Distributed Binomial Laws
  on Anisotropic Grids" (HPG 2023, Best Paper; CGF 42(8))** — the current real-time state of the
  art. Author lists verified 2026-08.
- **P** — Dupuy & Bruneton, "Real-time Animation and Rendering of Ocean Whitecaps" (SIGGRAPH Asia
  2012 Technical Briefs, Article 15): the prefilterable statistical whitecap coverage
  (`W ≈ ½ + ½·erf(...)` over the Jacobian's footprint mean and variance). The direct sequel that
  fills the gap Bruneton et al. 2010 explicitly left open — that paper states it does **not**
  handle whitecaps. [Code](https://github.com/jdupuy/whitecaps).
- **P** — Monahan & O'Muircheartaigh, "Optimal Power-Law Description of Oceanic Whitecap Coverage
  Dependence on Wind Speed" (Journal of Physical Oceanography 10(12), 2094–2099, 1980):
  `W = 3.84×10⁻⁶·U^3.41` (U at 10 m). The oceanographic ground truth for how much foam a given
  wind should produce.
- **P** — Pope & Fry, "Absorption spectrum (380–700 nm) of pure water. II. Integrating cavity
  measurements" (Applied Optics 36(33), 8710–8723, 1997): the modern pure-water absorption
  spectrum; minimum **0.0044 m⁻¹ at 417.5 nm**, 0.624 m⁻¹ at 700 nm, a ratio of 141. Use this
  above 380 nm.
  **The published table was read directly, 2026-08**, from the tabulated Pope & Fry spectrum
  ([omlc.org](https://omlc.org/spectra/water/data/pope97.dat), 2.5 nm steps, quoted in cm⁻¹), and
  the chapter's triple is now taken off it rather than from model knowledge: **a(610) = 0.2644,
  a(550) = 0.0565, a(450) = 0.00922 m⁻¹**. This corrects a long-standing 0.25 in the red — 5.4%
  low — and settled a disagreement with the reference implementation, which then carried
  `(0.2750, 0.0546, 0.0145)`. **Neither triple was wrong wholesale, and the reason is that they are
  quoted at different wavelengths**: the implementation samples 620/545/460 nm, where Pope & Fry
  give `(0.2755, 0.0511, 0.00979)`. Scored against its own sample points its red was right to 0.2%,
  its green 7% high, and its **blue 48% high and simply wrong** — no source in this chapter
  supported 0.0145 at 460 nm, and it is Smith & Baker's 450 nm value to the digit. Scored against the
  chapter's 610/550/450 the green and blue were exact and only the red needed the fix. Two lessons
  kept as doctrine in the text: the sample wavelengths are part of the constant, and a triple that
  disagrees with another triple may be disagreeing about where it was sampled rather than about the
  water.
  **Closed 2026-08 in the implementation**, which now carries the same table **averaged over its own
  channel bands** (582.5–657.5 / 502.5–582.5 / 417.5–502.5 nm): `a = (0.2617, 0.05299, 0.01022) m⁻¹`.
  That is a third reading of one measurement, not a third water — a band model wants the band mean,
  a three-delta model wants the point values, and the chapter's own triple remains the point sample
  at 610/550/450. All three are checked against this same transcribed table in `validate.py`, so no
  one of them can drift without a row moving.
  ⚠️ **Do not use Smith & Baker (1981) for blue absorption** — that era's measurements were
  scattering-contaminated and give `a(420)` ~3.4× too high, which desaturates clear water.
  Smith & Baker remains correct for UV (<380 nm) and for `K_d`.
- **P** — Braun & Smirnov, "Why is water blue?" (Journal of Chemical Education 70(8), 612, 1993):
  water's visible absorption is vibrational O–H overtone spectroscopy, not sky reflection.
- **P** — Lee et al., "Secchi disk depth: A new theory and mechanistic model for underwater
  visibility" (Remote Sensing of Environment 169, 139–149, 2015): shows the classical Secchi
  relation is not derivable from radiative transfer and replaces it with `Z_SD ≈ 1/min_λ K_d` —
  the artist-dial-to-IOP bridge. The classical `K_PAR = 1.44/Z_SD` constant is Holmes (1970),
  the best-performing of ~13 published constants spanning 1.27–1.86.
- **P** — Jerlov, *Marine Optics* 2nd ed. (Elsevier, 1976), Tables XXVI–XXVII; Solonenko & Mobley,
  "Inherent optical properties of Jerlov water types" (Applied Optics 54(17), 5392–5401, 2015);
  Morel (1988) for the Jerlov↔chlorophyll ladder. The water-type presets.
  ⚠️ **The numeric `K_d(λ)` tables in all three are paywalled and were NOT obtained** — values
  circulating in blog posts and asset packs are largely untraced. Either extract from source or
  generate the oceanic series from the Solonenko & Mobley `K_d(a,b)` relation, and say which.
- **P** — Babin, Morel, Fournier-Sicre, Fell & Stramski (Limnology & Oceanography 48(2), 843–859,
  2003): mass-specific scattering, ≈0.5 m²/g for mineral-dominated suspended matter at 555 nm —
  the concentration-to-optics bridge.
- **P/synthesis** — **Glacial-flour turquoise.** The popular Rayleigh/Tyndall explanation is
  physically wrong (rock flour is 2–65 µm, 10–100× the wavelength — Mie/geometric regime, where
  scattering is nearly wavelength-independent). The mechanism given in this chapter — flat
  backscatter shortens the photon path, over which `a_water` still removes red — is corroborated
  by measured-reflectance limnology: glacial-lake reflectance studies relate colour to suspended
  sediment and report that **finer grains at fixed concentration shift the reflectance peak
  shorter and brighten the water** (Everest-region in-situ + satellite study, *Mountain Research
  and Development* 37(1), 2017; high-elevation U.S. Rocky Mountain lakes, *Environmental Research
  Letters* 17, 2022). The full first-principles chain is assembled here rather than quoted from a
  single proglacial-lake IOP study; the mechanism is sound and now grounded.
- **D** — Beaufort wind force scale with its standard sea descriptions: the observational ladder
  used for [Sea states](12-water-rendering.md#sea-states-the-energy-ladder). Descriptor wording taken verbatim from
  NOAA's Storm Prediction Center table (fetched 2026-08) — whitecaps first at Force 3, spray at
  Force 5, foam streaks at Force 7, spindrift at Force 8, "sea completely white" at Force 12.
  [NOAA SPC](https://www.spc.noaa.gov/faq/tornado/beaufort.html). The **WMO sea state code** (built
  on the Douglas scale) is the parallel sea-based classification; `H_s` as the mean of the highest
  third and `≈ 4·sqrt(m₀)` is standard oceanography. Adoption dates for the Douglas scale and the
  WMO codes conflict across secondary sources (Douglas 1921/1929; WMO wave codes 1946/1947/1970)
  and are deliberately **not** stated as fact here — only the NOAA descriptor wording is
  authoritative in this section.
- **P** — Capillary–gravity dispersion `ω² = (gk + (σ/ρ)k³)·tanh(kh)` and its **minimum phase speed
  ≈ 23.1 cm/s at ≈ 1.73 cm wavelength** — the hard short-wavelength bound used in
  [Calm water](12-water-rendering.md#calm-water-the-low-energy-regime). Classical fluid mechanics; the constants were
  web-verified 2026-08 against standard references, the original derivation was not chased.
- **P** — Whitecap and foam optics: **void fraction 60–99%**, **mean bubble diameter 0.16–1 mm**,
  visible reflectance **~50% fresh breaking / ~40% active whitecap / ~18% thin residual foam**, and
  NIR reflectance troughs at **~750, 980, 1200 nm** from liquid-water absorption enhanced by
  multiple passes through bubble walls. Dierssen, H.M., "Hyperspectral Measurements,
  Parameterizations, and Atmospheric Correction of Whitecaps and Foam From Visible to Shortwave
  Infrared for Ocean Color Remote Sensing", *Frontiers in Earth Science* 7:14 (2019), fetched and
  extracted 2026-08; sole author verified 2026-08.
  [Open access](https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2019.00014/full).
  **Koepke (1984)'s ~22%** is a *time-averaged effective* whitecap reflectance from film-density
  measurements and under-represents fresh foam — correct for sea-average radiometry, wrong for a
  hero breaking wave. Earlier spectral work: Frouin et al. (JGR Oceans, 1996); Kokhanovsky
  (JGR Oceans, 2004).
- **T** — Barré-Brisebois & Bouchard, "Approximating Translucency for a Fast, Cheap and Convincing
  Subsurface Scattering Look" (GDC 2011; also GPU Pro 2; shipped in Frostbite 2): the
  view-dependent `dot(V, −L)` + thickness translucency approximation used for backlit wave crests.
  Verified 2026-08. [Frostbite](https://www.ea.com/frostbite/news/approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look).
- **P** — Liquid-sheet breakup cascade behind the waterfall progression: aerodynamic wave growth
  ruptures the sheet, fragments contract into ligaments (Rayleigh–Taylor), ligaments break into
  droplets by the **Rayleigh–Plateau** instability, most-unstable mode ≈ **9× the column radius**
  for an inviscid jet. Classical instability theory; mechanism chain web-verified 2026-08, no
  single canonical citation chased for the waterfall application specifically.
- **F** — The waterfall build (nappe → perforated sheet → ligaments → droplets → plunge-pool plume
  → lit mist), the three-class spray/foam/bubble split, and the sea-state feature gates as
  *rendering* triggers: production practice assembled over the physics above. The physics is P/D;
  the mapping to render features is this skill's composition.
- **P** — Specular-aliasing / normal-variance-to-roughness lineage: Toksvig, "Mipmapping Normal
  Maps" (Journal of Graphics Tools 10(3), 65–71, 2005); Olano & Baker, "LEAN Mapping" (I3D 2010,
  181–188); Kaplanyan, Hill, Patney & Lefohn, "Filtering Distributions of Normals for Shading
  Antialiasing" (HPG 2016); **Tokuyoshi & Kaplanyan, "Improved Geometric Specular Antialiasing"
  (I3D 2019)** — the current default, and specifically better at grazing angles, which is where
  a water horizon lives. The math routes to physically-based-rendering.
- **P** — Johanson, "Real-time water rendering — introducing the projected grid concept" (MSc
  thesis, Lund University, 2004): the screen-space grid concept and its horizon-edge behavior,
  as compared in the geometry table.
  [Thesis PDF (Lund)](https://fileadmin.cs.lth.se/graphics/theses/projects/projgrid/projgrid-lq.pdf).
- **P** — Kass & Miller, "Rapid, Stable Fluid Dynamics for Computer Graphics" (SIGGRAPH 1990):
  the lineage behind interactive heightfield ripple sims; pipe-model variants are later
  community practice. [ACM DL](https://dl.acm.org/doi/10.1145/97880.97884).
- **P** — Finch, "Effective Water Simulation from Physical Models" (GPU Gems ch. 1, 2004): the
  standard practical Gerstner implementation reference.
  [Chapter online (NVIDIA)](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models).
- **F** — Cascade counts and sizes (2–4 cascades, ~400/60/10 m), Jacobian foam thresholds
  (0.5–0.9), sim patch sizes (256²–512² over 30–100 m), choppiness limits: standard-practice
  ranges from shipped-title talks and community writeups; tune per title, verify per `11`.
- **T** — Bilodeau, "Vertex Shader Tricks" (GDC 2014, AMD): the `SV_VertexID` fullscreen
  triangle among other bufferless draws.
  [Slides (SlideShare)](https://www.slideshare.net/DevCentralAMD/vertex-shader-tricks-bill-bilodeau).
- **F** — One fullscreen triangle over a two-triangle quad (diagonal partial-quad/helper-lane
  waste, double interpolant setup): community canon —
  [Wallis, "Optimizing Triangles for a Full-screen Pass"](https://wallisc.github.io/rendering/2021/04/18/Fullscreen-Pass.html);
  [d7samurai, minimal D3D11 fullscreen triangle](https://gist.github.com/d7samurai/5915956fb8ce6a63503cf8c85ffd1e84);
  [30fps.net, "Full screen triangle optimization"](https://30fps.net/pages/twotris/).
- **F** — Water as a fullscreen ray-plane/ray-heightfield pass: long-running community
  technique, no canonical paper —
  [GameDev.net, "Rendering Water as a Post-process Effect"](https://www.gamedev.net/articles/programming/graphics/rendering-water-as-a-post-process-effect-r2642/).
- **D** — Underwater as a fullscreen volume pass in shipped tooling:
  [Crest Ocean System underwater docs](https://crest.readthedocs.io/en/latest/user/underwater.html)
  (fullscreen effect between transparents and post, meniscus handling).
- **F** — Depth-reject refraction fix, SSR fallback hierarchy, underwater state machine, planar
  one-body ceiling: ubiquitous production practice; no single canonical citation.
- **P** — Optical refraction constants for water: IOR ≈ 1.33 → Fresnel `F0 = ((n−1)/(n+1))² ≈ 0.02`
  and Snell's-window critical angle `arcsin(1/1.33) ≈ 48.6°`. Standard optics (Snell, Fresnel);
  arithmetic verified 2026-08. IOR is a **per-body** property from `liquidBody` (terrain-architect
  `28`), not a constant: natural liquids span ~1.31–1.47 (`F0` ~0.018–0.036). Seawater/brine values
  (1.341 at 35 ‰ rising to 1.397 at 240 ‰) from Maykut & Light, "Refractive-index measurements in
  freezing sea-ice and sodium chloride brines", *Applied Optics* 34, 950–961 (1995); verified
  2026-08. The screen-space UV-distortion refraction is an approximation of
  Snell bending, not the ray-traced result — the amplitude-Fresnel and Snell derivations live in
  physically-based-rendering (`pbr-fundamentals`, `volumes-and-sss`).
  **The exact equations, and what an approximation of them costs.** `R_s`/`R_p` as used in
  `reference-impl` are Born & Wolf, *Principles of Optics*, §1.5.2 (`P`, standard optics, re-derived
  and checked here). Schlick, "An Inexpensive BRDF Model for Physically-based Rendering",
  *Computer Graphics Forum* 13(3) 233–246 (1994) is the fit that was replaced there; it is quoted in
  the original as ~1% of `R` for common dielectrics, and measured against the exact equations at
  `n = 1.3348` it runs **+11.4% at 83.8°** and **+14.3% over the 38–79° incidence range the reference
  frame spans** (`D`, 2026-08). The closed-form check that separates them with no quadrature is the
  Brewster value `R(atan n) = ((n²−1)/(n²+1))²/2` — 0.03894/0.03948/0.04050 on this file's three
  IORs, against Schlick's 0.0303/0.0306/0.0314, i.e. **22% low** (`P`, arithmetic).
- **P/D** — [The view from inside, and the split shot](12-water-rendering.md#the-view-from-inside-and-the-split-shot).
  The critical angle, the exactness of total internal reflection outside it, the `d/n` apparent
  depth and the flat-port field narrowing (46° → ≈34° at `n = 1.333`) are textbook geometrical
  optics, recomputed here. The **0.39° dispersive rim** is arithmetic on the reference
  implementation's own IOR triple (`D`); the 5 m transmission `(0.27, 0.75, 0.96)` is Beer-Lambert
  on the corrected pure-water triple. **No underwater or over-under photograph of the reference pool
  exists**, so the port comparison rests on two supplied photographs of other water plus the optics
  (`D/?`), and the behaviour of a dome port *in air* was not worked through (`?`). The mirrored-twin
  cue and the "one straight edge settles which port" check are this chapter's composition, and both
  are cheap to falsify.
- **P** — Linear (Airy) wave theory — dispersion `ω² = gk·tanh(kh)`, shallow-water celerity
  `sqrt(g·h)`, Green's-law shoaling `a ∝ h^(-1/4)`, refraction: coastal-engineering canon;
  textbook treatment in Dean & Dalrymple, *Water Wave Mechanics for Engineers and Scientists*
  (1991). Constants quoted from model knowledge of the textbooks, not re-derived.
- **P** — Breaker criterion `H ≈ 0.78·h` (McCowan lineage) and surf-similarity/breaker
  classification via the Iribarren number: Battjes, "Surf Similarity", *Proceedings of the 14th
  International Conference on Coastal Engineering*, Copenhagen, ASCE, 1974, 466–480 (verified
  2026-08 — note several citation databases propagate a wrong "Honolulu, 446–480"; Honolulu was
  the 15th ICCE, 1976).
- **P** — Wave–current interaction (Doppler-shifted dispersion `ω = σ + k·U`, steepening
  against opposing flow, blocking near group speed): Peregrine, "Interaction of Water Waves
  and Currents", *Advances in Applied Mechanics* 16, 1976.
  [Semantic Scholar (verified 2026-08)](https://www.semanticscholar.org/paper/Interaction-of-Water-Waves-and-Currents-Peregrine/ead4947119505f48eaa8adaa4a3d78da7c722fad).
  The renderer-side opposition-scalar treatment is F-tier practice, not from the paper.
- **P** — Yuksel, House & Keyser, "Wave Particles" (SIGGRAPH 2007, ACM TOG 26(3)): Lagrangian
  wave carriers rasterized to a height field; object interaction.
  [Author page (verified 2026-08)](https://www.cemyuksel.com/research/waveparticles/).
- **T** — Gonzalez-Ochoa, "Water Technology of Uncharted" (GDC 2012, Naughty Dog): shipped
  ocean/beach water — mesh LOD, wave generation, flow shader.
  [GDC Vault (verified 2026-08)](https://gdcvault.com/play/1015309/Water-Technology-of).
  Whether the shipped waves were specifically *wave particles* is **`?`** — widely repeated,
  not verified against the talk.
- **P** — Jeschke & Wojtan, "Water Wave Packets" (SIGGRAPH 2017); Jeschke, Skřivan,
  Müller-Fischer, Chentanez, Macklin & Wojtan, "Water Surface Wavelets" (SIGGRAPH 2018):
  dispersive Lagrangian wave groups; emergent refraction/shoaling over bathymetry.
  [ACM DL (verified 2026-08)](https://dl.acm.org/doi/10.1145/3197517.3201336).
- **T** — Ang, Catling, Ciardi & Kozin, "The Technical Art of Sea of Thieves" (SIGGRAPH 2018
  Talks): stylized FFT water and its supplements in a shipped open-sea title.
  [ACM DL (verified 2026-08)](https://dl.acm.org/doi/10.1145/3214745.3214820).
- **F** — The travel-time (eikonal) shore phase field, breaker-profile authoring
  (spill/plunge/surge constructs), group-envelope "sets", foam lifecycle, and blend-band
  widths: production practice assembled from multiple talks and community writeups; no single
  canonical source. The `0.70–0.85` break-mask window and `hFade` style constants are tuning
  ranges, not measured standards.
- **D/N** — **Unreal Engine Water plugin** (the engine-native section): Epic documentation, fetched
  2026-08. Architecture and defaults —
  [Water System](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-system-in-unreal-engine);
  quadtree tiles, concentric-ring LOD, 4↔1 morphing, `Tile Size` 2400 uu, `Extent in Tiles` 64,
  `LODScale`, `Tessellation Factor`, far-distance mesh and the stated horizon-gap reason —
  [Water Meshing System and Surface Rendering](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-meshing-system-and-surface-rendering-in-unreal-engine);
  body types, spline metadata (river depth/width/velocity), the all-one-elevation lake rule, Island
  and Custom bodies, the Landmass brush with its depth curve / falloff modes / edge offset / blend
  modes, the edit-layers requirement, and exclusion volumes —
  [Water Body Actors](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-body-actors-in-unreal-engine);
  the pass position, scattering/absorption/`PhaseG`/colour-scale inputs, the single-depth-layer limit
  and the low-end fallback —
  [Single Layer Water Shading Model](https://dev.epicgames.com/documentation/en-us/unreal-engine/single-layer-water-shading-model-in-unreal-engine);
  Gerstner generator parameters (`Num Waves` 16, wavelength/amplitude ranges and falloffs, dominant
  wind angle and spread, steepness, seed) and the custom-generator base class —
  [Water Waves Asset](https://dev.epicgames.com/documentation/en-us/unreal-engine/simulating-waves-using-the-water-waves-asset-in-unreal-engine);
  zone properties — water-info texture **array** (single-target form deprecated), half-precision
  toggle, capture Z offset, velocity-blur radius in the finalize pass, `ZoneExtent`,
  `RenderTargetResolution`, local-only tessellation with its sliding-window extent, auto-include
  landscapes as ground actors, `GroundZMin`, `MarkForRebuild`/`Update` —
  [AWaterZone API](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/Water/AWaterZone).
  ⚠️ Engine docs drift by release and Water has changed shape repeatedly; re-verify constants.
- **F/?** — The buoyancy amortization controls (`N Points Per Frame`, `N Frames Pause`) and the note
  that buoyancy is CPU-evaluated come from Epic's water-waves/buoyancy documentation as surfaced in
  search, not from a page-by-page read — the *technique* (round-robin probe updates with declared
  latency) is the transferable part and is standard practice. Community reports of version-specific
  Water breakage under World Partition are forum-tier and deliberately not asserted as fact.
- **?** — Attribution of specific shallow-water shoaling approximations to particular shipped
  titles beyond the two talks above: multiple GDC/SIGGRAPH-Advances talks cover it; treat any
  further specific title claim as unverified.
- **P** — Caustic brightness as the inverse Jacobian of the ray map (`E ∝ 1/|det ∂q/∂p|`):
  conservation of flux in a ray tube, classical geometrical optics. No specific citation is owed
  and none should be invented.
- **P** — Fold/cusp classification of caustic structure — the claim that a caustic network has no
  triple junctions, which is the load-bearing argument against the Voronoi fake. Whitney, "On
  Singularities of Mappings of Euclidean Spaces I: Mappings of the Plane into the Plane", *Annals
  of Mathematics* 62 (1955): the only structurally stable singularities of a smooth map of the
  plane into the plane are folds and cusps. The optics reading is Berry & Upstill, "Catastrophe
  Optics: Morphologies of Caustics and Their Diffraction Patterns", in E. Wolf (ed.), *Progress in
  Optics* 18, North-Holland (1980), 257–346 — venue, volume and pages verified 2026-08; Whitney's
  attribution is from model knowledge and was not re-checked against the paper.
  [ADS](https://ui.adsabs.harvard.edu/abs/1980PrOpt..18..257B/abstract).
- **P/F** — The focal-set vs cut-locus framing: that a Worley `F2−F1` ridge set is the cut locus of
  circular fronts expanding from the seeds (equivalently the Voronoi edge set, where the two
  nearest seeds tie), that circular fronts have a degenerate focal set (the evolute of a circle is
  its centre), and that a planar cut locus generically has degree-3 vertices while a focal set
  generically has cusps. Each piece is standard — singularity theory and computational geometry —
  and the statements were checked for internal consistency here, but **no source was chased for
  the combination**. It is this skill's account of why the fake resembles a caustic and why
  refining it cannot converge; present it as an argument, not as a cited theorem.
- **P** — Image-space caustic maps (Tier 2): Shah, Konttinen & Pattanaik, "Caustics Mapping: An
  Image-Space Technique for Real-Time Caustics", *IEEE TVCG* 13(2), 2007, 272–280
  ([IEEE Xplore](https://ieeexplore.ieee.org/document/4069236/)); Wyman & Davis, "Interactive
  Image-Space Techniques for Approximating Caustics", I3D 2006, 153–160
  ([ACM DL](https://dl.acm.org/doi/10.1145/1111411.1111439)). Both verified 2026-08.
- **D/F** — The water-specific practical build: Guardado & Sánchez-Crespo, "Rendering Water
  Caustics", *GPU Gems* 1 ch. 2 (2004) — explicitly an aesthetics-driven approximation, not a
  physical solution, and it says so itself. Verified 2026-08.
  [NVIDIA](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics).
- **P** — Caustic sharpness floor from the solar disc: 0.53° subtense (the same figure used in
  [Sun glitter](12-water-rendering.md#sun-glitter-the-sparkle-path)), compressed on entry by `cos θ_i/(n cos θ_t)` —
  differentiated Snell, `≈ 1/n` near normal incidence. Arithmetic (0.53°/1.33 ≈ 0.40° ≈ 7.0 mrad,
  ≈ 0.7 cm blur per metre of depth) derived here and checked, not quoted from a source.
- **P/?** — Visible-band dispersion of water (`n ≈ 1.337 at 486 nm` to `≈ 1.331 at 656 nm`):
  standard optical data, quoted from model knowledge and **not** web-verified — treat the third
  decimal as indicative. The qualitative claim (fold sets separate per channel, so caustic edges
  fringe) is robust regardless.
- **P/D** — [A channel is a band](12-water-rendering.md#a-channel-is-a-band-not-a-wavelength). That a three-IOR render is
  a three-point spectral quadrature, and that a step edge at the dispersion scale therefore resolves
  as a comb, is an argument rather than a cited result — but it is falsifiable and was falsified the
  right way round: the silhouette speckle it predicts was present and the fold fringing it exempts
  was correct. The 9.8 mm red/blue bed separation, the 2.1 output pixels and the 0.33% ray
  disagreement are measured on the reference implementation (`D`). The Cauchy consistency (three
  IORs recovered from a two-parameter fit to 5×10⁻⁵) was recomputed here. The **3.5 mm / 9.4 mm**
  band smear on the red and blue folds is recomputed here from the Voronoi band edges of
  620/545/460 nm and the 21° sun's refracted path, and quoted across the beam so that it compares
  like-for-like with the 6.8 mm sun-disc penumbra; the implementation's own comment says 3.4/9.6 mm
  from a slightly different band statistic, which is the size of the disagreement. The Latin-square
  spectral stratification over the subsample grid is this chapter's composition — the idea is
  ordinary stratified spectral sampling, the point worth keeping is that the resolve filter is
  already an integral and can carry it for free.
- **P/D** — [Pick the kernel on purpose](12-water-rendering.md#pick-the-kernel-on-purpose-and-give-the-variance-a-receiver).
  `W(k)` for box/tent/Gaussian, the sinc's −0.217 first negative lobe, `σ_box = 1/(2√3) = 0.2887·fp`,
  the 0.663 amplitude (44% of variance) a box-matched Gaussian passes at Nyquist, and
  `σ = √(2 ln 2)/π = 0.3748·fp` with its "half gone at `fp = λ/2`, 94% gone at `fp = λ`" reading are
  all Fourier arithmetic, recomputed here. The reflection Jacobian `J = diag(−2, −2cos θ_v)` is
  derived here from `r = 2(n·v)n − v` and is exact to first order; the 1.8× stretch is
  `1/cos 57°`. Its Monte-Carlo validation (400k perturbed reflections, agreeing to 4% major / 8%
  minor axis) is the reference implementation's (`D`). Which kernel to prefer, and the
  attenuate-amplitude / per-component / output-footprint rules, are this chapter's composition from
  that arithmetic.
- **P/D** — [The sun must be a disc](12-water-rendering.md#sun-glitter-the-sparkle-path). `n = 2/θ_s² − 1` making a
  `cos^n` lobe's hemispherical flux `2π/(n+1)` equal `Ω_sun = πθ_s²` is exact for small `θ_s` and
  was recomputed here (`n = 93 493`, `Ω_sun = 6.72×10⁻⁵ sr` at `θ_s = 0.265°`). The audit figures —
  1563× under-peak, 7.8× over-width, three lobes carrying 0.695 against a direct beam of 24.1 — are
  measured on the reference implementation against its own constants (`D`), so they price *that*
  fitted lobe rather than fitted lobes in general; the failure mode they illustrate is the general
  claim. The atmosphere half of the argument lives in `10`.
- **D** — The wall as a light carrier, in
  [Caustics](12-water-rendering.md#caustics-the-other-half-of-the-light-path). The 35% mean / 77% worst-texel wall share
  of the bed's cosine-weighted hemisphere is an exact rectangle view factor computed per texel; the
  58% of the total-internal-reflection return meeting a wall follows from the 48.6° critical angle
  needing ≥1.59 m of horizontal run out of 1.40 m of depth in a 4 m basin; the 2.2× red gradient
  down the wall is measured. All three are properties of *that* basin — what transfers is the
  opposite-sign diagnostic, which is this chapter's composition.
  The **third symptom** — a submerged riser rendering flat and near-neutral — is the same entry's
  mechanism seen on a vertical receiver, and its two figures are measured on the same
  implementation (`D`): about **6%** of a riser's arc is both sunlit and camera-visible with
  `min(N·L, N·V)` nowhere above **0.10**, so the missing term is the bounce off the tread in front
  of it and not the direct sun. Both are properties of that step unit at that sun; the transferable
  claim is that a receiver with no direct sun and one flat ambient loses its *colour* as well as
  its level, and that the bounce is the term carrying the caustic net onto a vertical face.
- **P/D** — The bubble constant. `1 − 1/n²` is the cosine-weighted flux beyond the critical angle
  and equals **43.7%** at `n = 1.333` (44.3% at 1.34) — arithmetic here, and the same quantity as
  `cos²θ_c`. The 0.999 red transmission over 5 mm is Beer-Lambert on the corrected `a(610)`. The
  surf/plume split is this chapter's composition; the physics in each column is standard.
- **P/F** — Glitter as a level set of the slope field, and the four review tests that follow
  (trackable crests, dispersive multi-scale motion, phase-lock with the caustics, interference
  rather than cells). The geometry — a glint occurs where the normal is the sun/eye half-vector —
  is definitional; the dispersion arithmetic (≈0.25 m/s at 3 cm against ≈0.93 m/s at 55 cm, from
  `c = sqrt(g/k + σk/ρ)`) was derived and checked here. Framing these as *review tests*, and the
  claim that a still frame cannot separate real glitter from noise-perturbed specular, is this
  skill's composition — production observation, not a cited result.
- **P/F** — [The meniscus line](12-water-rendering.md#the-meniscus-line-where-reachability-cannot-fail). `a = √(σ/ρg)` and
  `h = a·√(2(1 − sin θ))` are textbook capillary rise on a vertical plate; `a = 2.727 mm`, `h = 3.856`
  / `2.727 mm` at `θ = 0°`/`30°`, recomputed here (`σ = 0.0728`, `ρ = 998`, `g = 9.81` SI). Contact
  angle **unmeasured** (`?`) so the rise is a range; the 5–10 mm fillet is order-of-magnitude; the σ
  counts use this chapter's convention (tilt ÷ per-axis `σ = s/√2`, in degrees) on an **ensemble**
  far field of `s ≈ 0.056` — the quadrature sum of the reference implementation's three chosen band
  constants, recomputed here — against which any 2 m patch of that field measures 0.053–0.058
  depending on where it is taken (`D`, both readings printed by `reference-impl/field.py`). The
  spread is finite-component sampling plus a varying shelter mask, not water, and the conclusion is
  quoted across the whole of it (7.6σ–8.3σ, 14.7σ–16.1σ). **Occlusion versus cast shadow was never
  separated** (`?`). AO/bevel framing is composition.
- **F** — The four-gate masking contract (depth fade, extinction along the light path, sun
  visibility at the surface entry point, irradiance-not-albedo) and the tier ladder as a whole:
  production practice assembled over the physics above. The shadow-at-entry-point rule is the one
  most often skipped and is stated here as doctrine, not as a cited result.
- **P** — Pool-water optics: pure-water absorption from the Pope & Fry table read above, sampled at
  this chapter's RGB points — `a = (0.2644, 0.0565, 0.00922) m⁻¹` at 610/550/450 nm; the 417.5 nm
  absolute minimum is deliberately *not* used as a blue channel. (`reference-impl` uses the same
  table averaged over its own channel bands instead — `(0.2617, 0.05299, 0.01022)` — for the reason
  given in the Pope & Fry entry above.) The round-trip transmittances and
  the resulting `(0.36, 0.68, 0.78)` white-liner and `(0.11, 0.46, 0.68)` blue-liner returns are
  arithmetic recomputed here on the corrected red, as are the liner albedos (`0.8` white,
  `(0.24, 0.54, 0.70)` mid-blue PVC), which are representative values, not measured product data.
- **P** — The chapter's vocabulary, in [Saying it in
  OpenPBR](12-water-rendering.md#saying-it-in-openpbr-and-where-the-mapping-stops) and [The
  vocabulary](12-water-rendering.md#the-vocabulary-and-which-half-of-it-you-can-look-up). Two
  standards, no house style.
  **OpenPBR Surface** supplies the interface names (`base_color`, `base_weight`, `specular_ior`,
  `specular_roughness`, `transmission_color`, `transmission_depth`, `transmission_scatter`,
  `transmission_scatter_anisotropy`) and the semantics this chapter relies on — in particular that
  `transmission_depth` is the distance at which white light becomes exactly `transmission_color`,
  which is what makes `a = −ln(T)/λ_T` an identity rather than a fit. The specification is the
  OpenPBR Surface specification (Adobe/Autodesk, under the Academy Software Foundation); the
  chapter's inversion of the pair and the RGB values quoted from it are arithmetic done here (`D`).
  **The IOP/AOP division** — inherent optical properties belonging to the medium alone (`a`, `b`,
  `b_b`, `c = a + b`, the phase function and `g`), apparent optical properties depending also on
  the light field (`K_d`, reflectances) — is Preisendorfer's, standard in ocean optics, and is
  visible in the title of a source already cited above: Solonenko & Mobley, "*Inherent* optical
  properties of Jerlov water types". Attribution of the division to Preisendorfer specifically is
  from model knowledge and was **not** chased to *Hydrologic Optics* (1976) (`?`); that the
  division itself is the field's standard vocabulary is not in doubt.
  **MaterialX** was checked (2026-08, specification sources on the AcademySoftwareFoundation
  repository) for whether it already names the medium-with-boundaries side, so that this chapter
  would not coin a third vocabulary. It names the medium's *optics* and nothing beyond them: a
  `volume` shader node built from VDF and EDF components, `absorption_vdf(absorption)` and
  `anisotropic_vdf(absorption, scattering, anisotropy)` in m⁻¹ — the same `a`, `b`, `g` — composed
  under a transmissive BSDF with a `<layer>` node, whose own documented example is "colored glass
  or turbid water", which is a direct corroboration of this chapter's boundary-plus-medium framing.
  It does **not** name a bounded body, a thickness or depth field, a per-body property set, or
  anything about render passes; geometry association runs through `MaterialAssign` inside a `Look`,
  which assigns a material rather than describing a body. Renderer-specific MaterialX extensions
  were not surveyed (`?`). Because MaterialX's medium inputs are the IOPs under other spellings,
  adopting IOP names costs nothing in recognisability and gains the measurement literature.
- **F/?** — The coinage audit in the same section. That **focusing number**, **driven basin** and
  **trapped series** are this chapter's own names is asserted from a failure to find them
  established, not from a systematic literature survey (`?` — a wrongly-claimed coinage is the
  cheap error here, and the labels are written so that it stays cheap). The terms listed as
  standard are standard: SI radiometry for radiance/irradiance/radiant intensity, Cox & Munk for
  mean square slope, Morel & Prieur for Case 1 / Case 2, and the rest as cited in their own entries
  above. That **`c` and `K_d` must be two coefficients and not one** is Preisendorfer's division
  applied, plus the 5–20× ratio already cited in the optics entries; the correction of the
  chapter's own shading pseudocode to use both was made 2026-08 and is `F` — the *ratio* is sourced,
  the two-term composite (`refracted·T_beam + L_scatter·(1 − T_diff)`) is a renderer construction
  and not a solution of the radiative transfer equation.
- **P/D** — Pool chemistry, in
  [Pool optics](12-water-rendering.md#pool-optics-the-colour-is-the-bottom-not-the-water). The hypochlorite absorption
  peak at **292 nm** and hypochlorous acid at 235 nm, with `ε ≈ 300–380 M⁻¹cm⁻¹`, are standard
  solution spectroscopy from model knowledge and were **not** chased to a primary source (`?` on the
  molar absorptivity in particular). The **0.5–1.5 m⁻¹ in the UV** at a 1–3 mg/L dose is arithmetic
  done here from that `ε` (dose as Cl₂, MW 70.9), and is reproducible from it. That precipitated
  CaCO₃ above ~pH 7.8 is the standard cloudy-pool mechanism is pool-operation practice (`D`). The
  absorption-subtracts / scattering-adds diagnostic and the "a sharp caustic net bounds `b_b`"
  argument are this chapter's composition; **no numeric bound on `b_b` was extracted** (`?`).
- **P/?** — The constituent model and the turbidity ladder. The four-component decomposition, the
  CDOM exponential with `S ≈ 0.014 nm⁻¹`, and the Case-1/Case-2 free-parameter count are standard
  ocean optics — Bricaud, Morel & Prieur (Limnology & Oceanography 26(1), 43–53, 1981) for the CDOM
  exponential and its slope, Morel & Prieur (1977) for the case split, and the Ocean Optics Web
  Book's Case-1 IOP model for the covariance structure; attributions are from model knowledge and
  were **not** re-verified against the papers. The CDOM table (`+0.0185 / +0.0429 / +0.1739` at
  610/550/450 for `a_g(440) = 0.20`) is arithmetic on that exponential, recomputed here. Pure
  water's molecular scattering is marked `?` — it is of order 10⁻³ m⁻¹ at 550 nm but was not
  verified. In the turbidity ladder, `ω₀` and the `exp(−b·1.96 m)` caustic contrast are exact given
  the stated `a` and slant; the **Secchi column is `?`** — `Z ≈ 1.44/(c + K_d)` is the classical
  Preisendorfer form and `K_d ≈ a + 0.02·b` is a placeholder backscatter ratio, so the depths are
  indicative and the *ordering* of the five symptoms is the durable claim.
- **P/F** — The driven-basin model for pool waves. Viscous decay `α = 2νk²` for deep-water gravity
  waves is Lamb's classical result (*Hydrodynamics*; attribution from model knowledge, not
  re-checked); `c_g = (g + 3(σ/ρ)k²)/(2ω)` follows from differentiating the capillary–gravity
  dispersion relation. The e-folding distances (~90 m at 16.5 cm, ~2.1 m at 3 cm, with
  ν = 1.004×10⁻⁶ m²/s) were computed here and are reproducible from those two formulas. That the
  filtration return is the dominant source, that tiled walls are near-total reflectors at these
  wavelengths, and the edge-contract inversion are this skill's framing from the physics plus
  direct observation — **no measurement of a wall reflection coefficient was chased**, so treat
  "near-total" as an argued approximation rather than a figure. The method-of-images construction
  and the early-reflections-plus-diffuse-tail split are standard room-acoustics practice carried
  over.
- **P/?** — The submerged-jet footprint. Linear spreading `r½ ≈ 0.094·s` and `1/s` centreline decay
  are textbook free-shear-flow results (Pope, *Turbulent Flows*, ch. 5; Rajaratnam, *Turbulent
  Jets*) and the structure was web-confirmed 2026-08; the numerical constants are from model
  knowledge and were **not** confirmed against a primary source — they vary by a few percent across
  experiments, which does not move the footprint qualitatively. The surface-deformation link
  `η ~ C·u'²/g` is a scaling argument (stagnation pressure of an eddy) whose **O(1) constant `C` is
  genuinely unknown**; `C = 1` was used, so the durable claim is the near/far **ratio** (`0.122`
  against a far patch reading `0.053–0.058`, i.e. 2.1–2.3, measured on `reference-impl/field.py` as
  total `√⟨|∇h|²⟩`; the spread is the far patch's position, not the jet), not either level: the
  far field is set by that file's `WIND_RMS` and `REVERB_RMS`, which are **chosen, not measured**
  (`?`), so citing them back as measurement would be circular. This link is the weakest in the chain.
- **P** — The wake geometry. `c_min = (4gσ/ρ)^(1/4) = 0.231 m/s` at 17.1 mm is the standard
  capillary–gravity minimum already cited in [Calm water](12-water-rendering.md#calm-water-the-low-energy-regime);
  `U0 = C_d√(2ΔP/ρ)` is Bernoulli with an orifice discharge coefficient (`C_d ≈ 0.92` assumed, a
  typical eyeball value from model knowledge); the stationary condition `c(k) = U·cos ψ` is textbook
  wave–current interaction, the same Doppler machinery this chapter cites for
  [rivers](12-water-rendering.md#rivers-flow-driven-surfaces). That a running return's pattern is a narrow downstream
  band and cannot be a ring system follows from those with no free parameter, and is the durable
  part. The **±19° energy fan** is narrower than the ±78° range of stationary *wavevectors* because
  energy travels at `c_g·k̂ + U`; the figure is the output of integrating the ray equations
  (`H = σ(k) + k·U`, Hamilton's equations, wave-action conservation — standard geometrical wave
  optics in a moving medium, Whitham; attribution from model knowledge, not re-verified) through the
  jet's decaying drift field — reproducible from those equations plus a drift field, not a measured
  angle.
  The **aim rule** attached to that bullet — a train whose plan axis sits within a few degrees of
  the camera azimuth projects as a near-vertical stripe and reads as a seam — is a projection fact
  with no physics in it; what is `D` is the pair of angles it is quoted with, 3.4° against 11.9° off
  `CAM_AZ`, which are that camera, that basin and that fitting position on the reference scene and
  were arrived at by moving the fitting rather than by sweeping the angle. No threshold was measured
  between them, so read "a few degrees" as the bracket those two numbers put on it and not as a
  constant.
- **P/?** — Inextensible-film damping `α ≈ 0.35·k·√(νω)`. The *structure* follows from the Stokes
  layer an unstretchable surface forces beneath it and is not in doubt; the numerical prefactor is
  the classical Lamb/Levich result from model knowledge and **could not be confirmed against a
  primary source** in a 2026-08 search — the literature found (Jenkins & Jacobs 1997; the
  Alpers–Hühnerfuss slick line) confirms the clean-surface `2νk²` and the existence of strong
  film enhancement, not the prefactor. Treat the factor 3–9 as indicative. The restriction to short
  waves is physics, not caution: the inextensible limit needs film elasticity large against the
  wave, which fails for swell.
- **F** — That treated pool water sits outside every Jerlov class (`b_b ≈ 0`, `c ≈ a`, Secchi
  exceeding body depth), that pool colour is therefore a bottom-albedo property rather than a
  scattering one, and the man-made gating table: this skill's composition from the optics above
  plus standard pool-operation practice.
