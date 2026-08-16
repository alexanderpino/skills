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
  (JGR Oceans, 2004). **P/D — and stronger than "under-represents": 0.22 is not a foam albedo.**
  Koepke, *Applied Optics* 23, 1816, measures whitecap reflectance falling from **0.20–0.55 at first
  breaking to 0.03–0.10 after ten seconds** and reports 0.22 as a **life-and-area-averaged
  effective** value — the product of a coverage that decays and a reflectance that decays,
  integrated. So a renderer carrying an explicit coverage mask and an explicit `R(age)` and *also*
  multiplying by 0.22 has **counted the decay twice**; grey foam is the symptom. `D`, recomputed
  here: a fresh raft at this project's own derived thickness (0.1075 m, an inventory rather than a
  guess) is `N = 73.3` bubble walls, and Stokes' pile of plates `Nρ/(1 + (N−1)ρ)` with
  `ρ = 1 − 1/n²` gives **0.9828** against a two-stream `τ'/(1 + τ')` with `τ' = (1 − g)bh` that never
  sees that constant at **0.9849** — **0.21% apart**, two routes with no shared source. And
  `1 − 1/n² = 0.4387` sits inside Koepke's own fresh-whitecap 0.20–0.55: a published bracket on a
  derived constant, recorded as **survived**. Still `?`: the shape of `R(age)` between his endpoints,
  which needs his time-resolved bins.
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
- **P/D** — [Radiance is not conserved across the
  interface](12-water-rendering.md#radiance-is-not-conserved-across-the-interface). The invariance of
  `L/n²` across a refracting boundary is standard radiometry — the **n-squared law for radiance**,
  also called the *fundamental theorem of radiometry*, a consequence of the étendue `n² dA dΩ` being
  the conserved quantity. Cite **Nicodemus, "Radiance", *American Journal of Physics* 31(5) 368–377
  (1963)** (`P`, verified 2026-08: the paper states `L/n²` invariant along a ray *and across a
  smooth boundary between lossless media*). For the water-specific statement and the same
  arithmetic, the [Ocean Optics Web Book](https://www.oceanopticsbook.info/) carries it under that
  name with an in-water-to-air reduction of 1.76 at its own `n` (`D`, ocean-optics reference text);
  Preisendorfer's *Hydrologic Optics* is the usual deeper citation but **the specific volume and
  section were not confirmed here — do not cite it for this without checking** (`?`).
  `n² = 1.774/1.782/1.796` and the 0.827–0.844 stops are arithmetic on the reference
  implementation's IOR triple (`D`); the 1.78× is that, not a general constant — it moves with the
  body's IOR exactly as `F0` does. **Walsh's relation** `n²(1 − R_int) = 1 − R_ext`: the identity is
  `P` (a two-line consequence of the n² law plus Fresnel reciprocity, and quadratured both ways in
  `reference-impl/validate.py`), and it is cross-checked there against the independent Egan &
  Hilgeman (1979) empirical fit for internal diffuse reflectance to 0.09%. The **name** is the
  attribution that could not be closed: it is widely attached to J. W. T. Walsh, "The reflection
  factor of a polished glass surface for diffused light", *Illumination Research Technical Paper*
  No. 2 (1926), but the original was not read here (`?` on the name, not on the relation). The
  diffuse figures `1 − R_int = 0.526/0.524/0.519` and `R_int ≈ 0.476` are quadratures here (`D`).
  The energy audit — a lossless body with a white Lambertian bed returns **exactly 1**, against 1.73
  without the divisor and 1.31 with a `1/n` — is energy conservation and contains no constant of the
  renderer (`P`, arithmetic). The **verification** half of this entry, and why a Fresnel suite cannot
  see any of it, is `11`'s
  [sixth way a measurement lies](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one).
  ⚠️ **What that audit could not see, added in this pass:** it borrows exactly one name from the
  renderer, so it certifies the divisor and nothing else. The replacement pair and the
  reintroduced-bug table are `11`'s
  [eighth way](11-verification-failures.md#the-eighth-way-is-about-the-test-not-the-measurement).
- **P/D** — [Attenuation and escape do not
  factorise](12-water-rendering.md#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them),
  and the same derivation in
  [`12a` §10](12a-water-derivations.md#the-diffuse-exit-and-why-its-two-factors-may-not-be-separated).
  The identity `⟨fg⟩ = ⟨f⟩⟨g⟩ + Cov(f, g)`, and its relative form `r·CV_f·CV_g`, are elementary
  probability (`P`) and carry no water in them — the transferable claim is that a pre-computation
  may split a product only across variables the integral does not run over. Everything numeric is
  `D`, recomputed here by 2000-node Gauss–Legendre on the exact unpolarised internal Fresnel over
  the cosine-weighted measure `2μ dμ`: `T_esc = 0.3403 / 0.4795 / 0.5106` and
  `G_rt = 0.0965 / 0.3277 / 0.4445` at this pool's `τ = a·d = 0.3664 / 0.0742 / 0.0143`; the
  separated forms `2E₃(τ)·(1 − R_int) = 0.2850 / 0.4563 / 0.5050` and
  `(2E₃(τ))²·R_int = 0.1389 / 0.3614 / 0.4546`; hence **16.2 / 4.8 / 1.1 % low** on the escape leg
  and **43.9 / 10.3 / 2.3 % high** on the round trip. ⚠️ Those percentages are quoted in both
  directions on purpose, because the same two facts have circulated as "understates by 19.4%" and
  "overstates by 30%" — which are the *reciprocal* readings (joint over separated) of the same two
  numbers. Both readings are correct; mixing one of each in a chain is how a factor gets
  double-counted, so a percentage of this kind is quoted with its denominator or not at all.
  ⚠️ **That warning has since been earned twice over, and the second time cost a false alarm worth
  recording.** A later figure-drawing pass reported that the reference implementation's inline
  comment — *"the factorised form OVERstates it by 30% in red"* — **did not reproduce**, measuring
  55.6 / 11.4 / 2.4 % instead and concluding that *no* reading of the two integrals gives 30 at this
  depth. Re-derived here, **both halves of that report are wrong in different ways** and the truth
  is a third thing: 30.5% *is* a reading — it is the joint form sitting below `(2E₃(τ))²·R_int`, the
  reciprocal of the +43.9% already in the table — so the comment's number is right and only its
  *direction* is wrong; and 55.6% is a reading too, but of a **different separated form**,
  `2E₃(2τ)·R_int`, which the figure pass had not distinguished from the squared one. Two forms, two
  directions, four percentages, one comment. The corrective in the chapter is the
  **8.1% spread between the two separated forms** and the ordering result that goes with it (the
  direction-preserving form is the further off); the comment's 30% needs a denominator, not a
  recalculation. **Nothing in the chapter's figures moved** — the entry above already carried the
  correct pair in both directions, which is why the reconciliation was possible at all, and it is a
  small argument for quoting reciprocals explicitly. The
  correlation coefficients (**+0.76**, **−0.85** at the red `τ`, both tending toward ±0.90 as `τ`
  grows) and the error-versus-`τ` ladder are quadratures here (`D`). The **cancellation** — 19.4% in
  the term against 2.8% in the composed albedo — is a property of *this* chain's algebra (the round
  trip sits in a denominator) and is `D`; that term-level errors of this class hide behind
  chain-level agreement is the general claim. That the separated form is **exact at `τ = 0`**, and
  therefore invisible to every lossless or white-bed check, is algebra (`P`), and it is the reason
  the guard is a photon walk at nonzero absorption rather than a second quadrature.
- **P/D** — The near-Lambertian emergence in the same section: that a Lambertian bed under a flat
  surface emits nearly Lambertian into air, so a water-to-deck ratio needs no view axis. The
  mechanism is `P` — the only angular dependence on the way out is the Fresnel transmittance, the
  `1/n²` being angle-independent, and Fresnel is flat far from grazing. The **cone** is the part
  that must travel with the claim, and it is `D`, recomputed here on this chapter's IOR triple: the
  shape factor `S(θ) = (1 − R(θ))/(1 − R_ext)` spreads **0.11% inside 30°, 0.43% inside 40°, 0.78%
  inside 45°, 4.2% by 60° and 13.1% by 70°** in luminance. ⚠️ **A correction made in this pass:** a
  figure of "0.5% across a whole basin" was in circulation; 0.4–0.5% is the spread inside a **40°
  cone**, and across the reference implementation's own whole-basin frame — whose water spans
  44°–73° from vertical — the shape factor alone varies by **17.6%**, and the full emergent field,
  once the up leg's own `exp(−a·d/μ_w)` is included, by **21.2%** in luminance and **29.3%** in red.
  "Near-Lambertian" is a nadir statement — an aerial reference, or a closed form written for one;
  at a poolside eye it is worth a fifth of the answer. The medium also tilts it per channel
  (emergent red 0.855 of nadir at 60° against 0.955 in blue), which is a signed inference rule when
  two cameras at different heights disagree.
- **P/D** — [The illuminant is part of the
  comparison](12-water-rendering.md#the-illuminant-is-part-of-the-comparison-what-cancels-and-what-does-not).
  The **solar position** half lives in [`10`](10-lighting-shadows.md#computing-the-illuminant-from-a-place-and-a-time)
  and carries its own provenance rows there — the low-order NOAA/Meeus algorithm (`P`), Bennett
  refraction (`P`), Kasten–Young air mass (`P`), and the Aljezur table computed here (`D`). What is
  this file's to price is the **water** half, and all of it is arithmetic recomputed here on the
  reference implementation's own IOR triple (`D`): the incidence angles 68.98°/32.78°; the
  unpolarised transmitted shares **87.76% / 97.78%** (exact Fresnel, `n = 1.3348`, spread 0.1% across
  the three channels and 0.02% between `n = 1.333` and `n = 1.3348`); the refracted angles
  44.37°/23.93°; the slant paths **1.959 m / 1.532 m** to a 1.40 m bed and the 1.370 m / 0.621 m
  horizontal offsets; the **1.114×** Fresnel factor, the **1.118×** red one-way path factor at
  `a(610) = 0.2644 m⁻¹`, and their product **1.246×**. Those are properties of *that* depth and
  those two suns; what transfers is the **cancellation rule** — that `sin h` and air-mass
  attenuation are common to any two horizontal receivers and therefore cancel in their ratio, while
  the Fresnel entry share and the slant path do not — which is this chapter's composition from
  standard radiometry and has no free parameter in it. The `sin h` figure 2.34 and the per-channel
  2.58 / 2.75 / 3.23 irradiance ratio are arithmetic here on the same Rayleigh optical depths `10`
  uses. The **reddening inference rule** is `exp(−m·τ_R(λ))` (`P`, the form and its Hansen & Travis
  corrections are cited in `10`) evaluated at this chapter's band centres: `SUN_COL`'s red-to-blue
  **1.484** against **1.184** for a true air-mass-1.189 illuminant, hence **1.253× redder** (`D`,
  recomputed here). ⚠️ **A correction made in this pass:** the 1.484 figure had been quoted as the
  size of the confound, which compares the render's sun to a *flat white* illuminant rather than to
  the photograph's own; the confound is the 1.253, and the qualitative conclusion — that the
  illuminant difference runs the wrong way to explain a red *deficit* — is unchanged by the
  correction. The two limits stated at the end of the section (the ambient-to-direct mixture does
  not cancel, and none of it survives a nonlinear camera) are this chapter's composition, the second
  routing to [`11`](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one).
- **D/?** — The two claims in that section and in the
  [diagnostic index](12-water-rendering.md#diagnostic-index-symptom-to-mechanism) that are about
  *this* project's open finding rather than about physics: that the render's water reads less red
  than the reference photograph's, and that the measured water-to-sunlit-stone ratio gap is about
  twice the 1.246 the illuminant difference can account for. Both are measured on `reference-impl`
  against photographs of the reference pool (`D` for the render side) but the photographic side is
  **not** a colorimetric measurement (`?`) — it is a phone frame, and what it can and cannot support
  is [`11`](11-verification-failures.md#seven-ways-a-measurement-lies-while-looking-like-one), whose
  provenance table prices the Display-P3 and tone-curve figures the index row quotes. The finding is
  recorded here as open, which is the only status it can have until a RAW capture or an in-frame
  neutral exists. What is durable regardless is the **inference rule**: a confound whose direction
  is known either shrinks a discrepancy or strengthens it, and it must be signed before it is
  invoked.
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
- **P/D** — [What the window actually contains, and why the rim is where the world
  is](12-water-rendering.md#what-the-window-actually-contains-and-why-the-rim-is-where-the-world-is),
  derived in [`12a`
  §7](12a-water-derivations.md#the-window-from-below-snells-jacobian-and-where-the-horizon-goes).
  **Snell's Jacobian** `dΩ_w/dΩ_a = cos θ_a/(n² cos θ_w)` is differentiated Snell and carries no free
  parameter (`P`); its closure `∫dΩ_a = 2π(1 − cos θ_c)` is an identity and is the only guarded
  quantity in the whole audit — quadratured here to **2.1213850054 vs 2.1213850054 sr** and asserted
  in `reference-impl/validate.py` (`D`). The elevation → polar-angle table, the 3.75% / 0.95% / 0.04%
  annulus shares, the 7.6× over-service of the zenith and the 8.5× starvation of the outer degree,
  and the change of variable `v = cos θ_a = √(1 − n² sin²θ_w)` are closed-form arithmetic recomputed
  here at `n = 1.3348` (`D`). The **contents** table is a property of *that* pool, that sail and that
  camera and transfers as a mechanism only (`D`): route 1 weights a rendered frame's transmitting
  subsamples by `cos³`, route 2 samples the air hemisphere stratified in `cos θ_a` under the
  Jacobian. The **sail's 72–77° from the vertical** is that scene's geometry; the **1.44°** it
  compresses into is recomputed here and is the number the chapter's earlier "about 1.5°" rounds to.
  ⚠️ **Neither route guards the other** — they answer different questions and a binning error common
  to both would not show (`?`). The claim that a raised edge admits **no deck** into the window is
  geometry (`P`) and is additionally asserted against a 0.2 mm march of the edge profile in that
  implementation (`D`). ⚠️ **A correction carried by this entry:** an earlier round priced the
  missing world as "a thin rim" — the outermost 0.205° of window at low transmittance — and
  separately expected the sail to occupy a large solid angle. Both are refuted above: the rim
  measurement is the right measurement for the rim and the wrong one for the share, and the sail is
  **0.066%** of the window against the pool's own edge section at **0.989%**.
- **P** — Linear (Airy) wave theory — dispersion `ω² = gk·tanh(kh)`, shallow-water celerity
  `sqrt(g·h)`, Green's-law shoaling `a ∝ h^(-1/4)`, refraction: coastal-engineering canon;
  textbook treatment in Dean & Dalrymple, *Water Wave Mechanics for Engineers and Scientists*
  (1991). Constants quoted from model knowledge of the textbooks, not re-derived.
- **P/?/D** — The **static-equilibrium (headland-)bay** plan-form
  ([`12`](12-water-rendering.md#the-shoreline-is-part-of-the-wave-field-and-a-straight-one-is-a-test-that-cannot-fail),
  [`12a` §11](12a-water-derivations.md#11-the-static-equilibrium-bay)). Three separable claims and
  they do not share a tier.
  **`P`** — that a sandy shore between rock control points relaxes to zero longshore transport, and
  that the resulting plan-form has closed forms: the **logarithmic spiral** (Krumbein 1944; Yasso
  1965; Silvester 1970) and the **parabolic bay-shape equation** (Hsu & Evans 1989). Attributions
  quoted from model knowledge of the coastal-engineering literature and **not** verified against the
  papers in this container — treat the attributions as `?` and the *mechanism* as `P`.
  **`?` and NOT CARRIED** — Hsu & Evans' `C₀/C₁/C₂` quartic coefficients. Fifteen fitted numbers with
  no internal consistency check; nothing here holds the paper; **they are deliberately absent from
  all three files and must not be cited from them**.
  **`D`** — the derivation that the *circular* member (`α = 90°`) follows exactly from "shore normal
  to a radial orthogonal", and that the spiral is uniquely the constant-residual-obliquity
  generalisation; the impossibility result that a plane-crest field admits only a straight rotated
  equilibrium; and every number in the transport table, measured on `reference-impl/beach.py` over
  1408 m of coast at `H₀ = 1.5 m, T = 9 s, θ₀ = 20°`. Those numbers are properties of *that* scene;
  what transfers is the mechanism and the calibration discipline, never the figures.
  **`?`** — `δ`, the residual obliquity that fixes `α`. Bracketed by the circle (0.9 % in
  indentation on this scene), not closed.
- **D** — **The offshore Snell invariant is the wavenumber component along the CONTOUR, not along
  the grid.** Found by calibrating the transport meter: on the closed-form zero-transport coast,
  which must break at exactly `θ = 0`, a 2-D march that conserved `k_y` on the grid axis left 4.89°
  of residual obliquity and 76 % of the straight coast's transport; against the local contour it
  leaves 0.20°. Exact for a straight coast, silently wrong on any bay. Measured on
  `reference-impl/beach.py`, waves 1–8 shipped the grid-axis form.
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
- **P/D** — [The glitter path's width as a readout of the mean-square slope](12-water-rendering.md#sun-glitter-the-sparkle-path).
  The slope regressions are Cox & Munk's (`P`, entry above). Everything the chapter reports *around*
  them is measured on the reference implementation's second scene
  (`terrain-renderer/reference-impl/beach_optics.py`, `glitter_width_deg`; all figures recomputed
  here): FWHM/`√mss` = 53.53 / 53.52 / 53.75 / 54.43 at `U` = 3 / 6 / 10 / 16 m/s, the 2.26×
  narrowing and 14.2× brightening from a 25° view down to the horizon, and the five-term
  decomposition of that brightening. Those are properties of *that* sun (21.02°), *that* wind
  (6 m/s, itself `?` — the reference frame's wind is unobserved) and a Gaussian slope pdf without
  Cox & Munk's own skewness and peakedness corrections, which move the wings more than the
  half-maximum. What transfers is the **mechanism and the sign**: the width tracks `√mss`, and the
  path narrows and brightens toward the horizon. Re-measure the constants for another geometry.
  The closed forms beside them — `β₀ = |θ_sun − θ_view|/2`, and the azimuth-to-tilt steepening —
  are half-vector geometry derived here and checked against the model (`D`).
- **P/D** — [What a single-bounce glitter model loses below the horizon](12-water-rendering.md#sun-glitter-the-sparkle-path).
  The two integrals — the radiance over the upward hemisphere, and `ρ_F(ω) cos ω · p/cos β` over
  slope space — are the Cox–Munk construction (`P`); their agreement to 7×10⁻⁵ relative, and the
  share of intercepted flux whose mirror direction points *down*, are measured here on
  `reference-impl/beach_optics.py` and converged against grid extent and resolution (10.262 /
  10.261 / 10.271% at ±1.5/601, ±2.0/1201, ±3.0/2001 samples). The 10.3% is that sun (21.03°), that
  wind (6 m/s) and that wind azimuth; the elevation × wind table beside it is what carries, and the
  "negligible above 45°" reading is that table's, not a published result. **Not modelled anywhere in
  this chapter** — the multiple-surface-bounce term that would return the light is named and left
  open.
- **P/D** — [The forward glow is not Beer–Lambert](12-water-rendering.md#water-body-optical-identity-where-the-iops-come-from).
  The single-scattering integral collapsing to `b·p(Θ)·E·L·e^{−cL}` is textbook radiative transfer
  done in one line here — the two exponentials multiply to `e^{−cL}` independent of `s`, so the
  integral is the path length — and the cuvette relation `c = −ln(T₂/T₁)/(L₂−L₁)` is standard
  spectrophotometry (`P` both). The **bias** is `D`: measured on the reference implementation's
  backlit wedge (`beach_render.py`, off the scene-linear buffer, term by term), −5.4 / −24.3 /
  −15.8% at `L₁ = 1 m`, `L₂ = 3 m` with the glow at 5.07% of the pixel. The **shape** of the error
  — low, worst in the clearest band, growing with the glow's share — is general; the −24.3% is that
  water, that geometry and those two thicknesses. Two other thickness pairs were run and are worth
  recording because they *look* like a robustness result and are not one: `L₁/L₂ = 0.25/1.0` and
  `0.5/2.5` give −25.0% and −24.6% in green, against −24.3%. The bias **coefficient**
  `ln(L₂/L₁)/(L₂−L₁)` across those three pairs is 1.848, 0.805, 0.549 — a factor of 3.4 — so the
  near-constant answer is the coefficient and the glow's share moving in opposite directions
  (0.012, 0.026, 0.038 inferred), not the bias being insensitive to geometry. Quote the formula,
  not the percentage.
- **P/D** — [Diffraction is not refraction](12-water-rendering.md#diffraction-is-not-refraction-and-nothing-above-contains-any-of-it).
  The Sommerfeld half-plane solution and its coastal-engineering use for breakwaters
  (Penney & Price 1952) are `P` — cited for the *structure*, and **not** re-verified against those
  papers this run. The numbers beside them are `D`, evaluated here from Fresnel integrals rather
  than read off a table: `K_d = 0.5000` exactly on the shadow boundary, 0.31 / 0.20 / 0.11 at
  `v` = 0.5 / 1 / 2, and the lee centre-line amplitude behind a strip (0.20 → 0.80 over 0.1 → 10
  `W²/λ`) from the Fresnel–Kirchhoff integral. The `W²/λ` closing scale follows from that table and
  is stated as a scaling, not a formula to quote. The **2.5× lee focus** is measured here on
  `reference-impl/beach.py`'s `transform_2d` with a 40 m emergent rock on a flat 8 m shelf
  (`λ = 74.4 m`, `H = 3.66 m` on the lee centre line against a 1.478 m ambient) — a property of
  *that* march's `D_MIN` depth floor, quoted to show that the diffraction-free failure is not
  always a shadow, not to claim every implementation focuses. The refraction figures it is
  contrasted with (0.186 / 0.310 / 0.277° on a rotated bed) are recomputed here from
  `validate_beach.py`. The originating observation is a photograph of surf closing in the lee of an
  isolated rock; `?` for that scene's wavelength and obstacle width, which is why the chapter states
  the regime rather than a number for it.
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
  The **ceiling on that bounce**, added in the same section, is the half of this entry that is *not*
  a property of the basin. A Lambertian source is view-independent, so a neighbour cannot
  concentrate it; the form factor from a differential element on a plane to the adjoining infinite
  perpendicular plane is exactly **½** — standard radiative transfer, in any view-factor catalogue
  (Hottel & Sarofim, *Radiative Transfer*, 1967; Modest, *Radiative Heat Transfer*), and recomputed
  here two ways, in closed form (the neighbour fills half the cosine-weighted hemisphere, the sky the
  other half) and against a 4M-sample cosine-weighted Monte-Carlo, **0.49996** (`P` + arithmetic,
  2026-08). Hence `L_wall ≤ ρ_wall·L_floor/2` for *any* diffuse-lit neighbour — a cave wall, a
  canyon, a light well — with no water in the argument. What is measured on this basin (`D`) are the
  numbers that price it: `ρ_wall = 0.82·LINER_TINT = (0.246, 0.648, 0.754)`, so the ceiling is
  **12 / 32 / 38 %** of the floor's radiance; the shipped gather delivers **0.77 / 0.83 / 0.87** of
  that ceiling, which is the fact that turns "add more bounce" into a dead end; and the east/north
  split — **2.63 / 1.63 / 1.39×** the deep floor on the wall the refracted sun lands on against
  **0.34 / 0.57 / 0.72×** on the one it never reaches (direct caustic 0.000) — is that sun, that
  basin and that liner. The transferable claim is the inequality and the diagnostic that follows it:
  the *ordering* of two surfaces at one depth through one water is invariant to exposure, tone curve
  and white point, being a ratio of radiances within a single frame.
- **P/D** — [What a submerged vertical face sees of the
  sky](12-water-rendering.md#what-a-submerged-vertical-face-sees-of-the-sky), derived in
  [`12a` §7](12a-water-derivations.md#the-window-and-the-mirror-two-halves-of-one-hemisphere). The
  physics is standard optics with no free parameter: past `θ_c = asin(1/n)` the underside of a flat
  water surface is a **perfect mirror** and inside it the sky arrives compressed into that cone
  about the vertical, so a vertical receiver's upper half-hemisphere is a partition of those two and
  not "the sky". The three integrals — `tir_vert(0) = ½`, `TIR_VERT = 0.8853`,
  `TIR_FRAC = 1 − 1/n² = 0.4387` — are closed forms recomputed here at `n = 1.3348` and are each
  guarded in `reference-impl/validate.py`, `TIR_VERT` by a quadrature and a 4M-sample Monte-Carlo of
  the arriving *radiance* plus two premise-free rows. What is new here and is arithmetic on them
  (`D`): the split of that half-hemisphere into **77.7% mirror and 22.3% window**, and the window's
  share against a horizontal face at the same depth, `(0.5 − TIR_VERT·TIR_FRAC)·n² = **0.199**`
  (0.1995 / 0.1988 / 0.1976 per channel — a 1% spread, so one figure is honest). The renderer's
  `WALL_SKY × WAO = 0.50 × 0.78 = 0.390`, hence an over-give of **×1.96**, is a property of *that*
  implementation (`D`), and the submerged-wall readings it produces — **0.470** of the dry band over
  the first 100 mm and **0.581** over the next 150 mm, against an observation that puts it above 1 —
  are that frame, that liner and that sun. The **coupling** is the transferable half and it is
  structural, not measured: the window and the mirror partition one hemisphere, so over-giving one
  necessarily under-gives the other and any instrument that reads only their sum is blind by
  construction. The three separators offered (hue, moving caustic structure, and zeroing the sky to
  test for a fall to 0.777) follow from the same partition. This is **not** the floor-lit-wall
  ceiling `L_wall ≤ ρ·L_floor/2` in the entry above — that bounds the *lower* half of the same
  hemisphere against the floor — and the two are additive; conflating them has already cost this
  project a round, which is why both sections state the distinction rather than assume it.
  The fault itself is **open** (`?`): closing it needs the window's share *and* the mirror's missing
  bounces, and moving the sky constant alone runs the wrong way.
- **D** — [A caustic on a vertical
  face](12-water-rendering.md#a-caustic-on-a-vertical-face-is-not-the-beds-pattern-at-that-faces-own-position).
  The correction is conservation of flux along one refracted direction, which is `P` and has no free
  parameter: the point at height `z` on a vertical face is lit by the beam that would have landed at
  `face_xy + (z − z_foot)·tan θ_t·ŝ`, with `θ_t` the **refracted** sun angle. The geometry figures
  are recomputed here on the reference implementation's sun (incidence 68.97°, refracted 44.37°,
  `tan θ_t = 0.978`, hence **235 mm of run over the 240 mm riser, 249 mm over the 255 mm one and
  685 mm over the 700 mm drop at the outer nosing**) (`D`). ⚠️ **A correction made in this pass:**
  "249 mm on the tallest riser" pairs the run of the *middle* riser with a face that is not the
  tallest — the outer nosing's face, which is where the artefact was measured, drops the full 700 mm
  to the floor. The artefact figures — **41% rms along the arc against zero up the face**, a stripe
  rms of **1.372 → 0.816** encoded levels, and the term's height-to-arc ratio **0 → 0.941** — are
  the implementation's own printed diagnostics on one frame (`D`) and were **not** re-derivable here
  without a full render; they price that step unit at that sun. So is the negative result beside
  them, that quadrupling the caustic map's arc bins *and* the gather's directions moved the stripe
  rms only 1.372 → 1.363. What transfers is the **signature** — a term whose variation collapses to
  exactly zero along one axis is missing an argument, not noise — and the observation that a
  screen-space or world-axis projected caustic pass has the identical degeneracy on vertical faces.
  The fix shipped there is still a **proxy** (`?`): the bed map is focused at each texel's own
  depth, so reading it at the face's height ignores the focusing over that run; the honest answer is
  to rasterise the vertical faces into their own caustic map, which is not done.
- **P/D** — The bubble constant. `1 − 1/n²` is the cosine-weighted flux beyond the critical angle
  and equals **43.7%** at `n = 1.333` (44.3% at 1.34) — arithmetic here, and the same quantity as
  `cos²θ_c`. The 0.999 red transmission over 5 mm is Beer-Lambert on the corrected `a(610)`. The
  surf/plume split is this chapter's composition; the physics in each column is standard. **What is
  new in this pass** is the exact relation between that constant and the diffuse internal
  reflectance it is routinely confused with: `R_int = (1 − 1/n²) + partial Fresnel inside the cone =
  0.438735 + 0.037431 = 0.476166` at `n = 1.3348`, so `1 − 1/n²` is **92.1%** of `R_int` and not all
  of it (`D`, quadratured here). Use `1 − 1/n²` for a bubble wall — a per-direction mirror — and
  `R_int` for a hemispherical average; the two are 3.74 points apart, which is worth 1.9% of a red
  trap and 12.2% of a blue one.
- **D** — **The bubble constant is a reflectance and not a backscatter fraction**, and this is a
  correction to how `12` read its own number rather than to the number. A geometric-optics trace over
  a bubble's disc — area-uniform impact parameter (`p = √u`, so the measure is `2μ dμ` by
  construction rather than by weighting), water→air Fresnel by reciprocity, the sphere's textbook
  deviations `Θ₀ = π − 2θᵢ` and `Θ_p = 2(θᵢ − θ_t) + (p−1)(π − 2θ_t)`, forty orders, weights summing
  to `1 ± 8×10⁻⁷` *by construction and checked* — returns `b_b/b = 0.0228 / 0.0230 / 0.0235` and
  `g = 0.691 / 0.688 / 0.684` across the IOR triple. **Twenty times under the 43.874% reflectance**,
  because `θᵢ > θ_c` forces `Θ₀ < π − 2θ_c = 82.96°`: every totally reflected ray leaves forward of
  the perpendicular. The same trace recovers the totally-reflected share as
  `0.436378 / 0.438728 / 0.443078` **without evaluating `1 − 1/n²`** — it is measuring the area of the
  disc beyond `θ_c`, which is what the formula is — and, with the Fresnel evaluated per channel
  rather than at the red band's refracted cosine, recovers the full disc-average reflectance as
  `0.473713 / 0.476167 / 0.480681` against the independent quadrature's `R_int` of
  `0.473712 / 0.476166 / 0.480681`, agreeing to six digits from a ray trace that shares no code with
  it. Both figures recomputed here from `reference-impl/beach_foam.py:bubble_scatter`; the
  per-channel Fresnel variant is this pass's, and the difference it makes to `b_b/b` is 0.0230 →
  0.0233 in green, which moves nothing in the finding. The **liftable** half is that a conservative
  slab's white comes from `τ' = (1 − g)τ`, `R = τ'/(1 + τ')`, `T = 1 − R` — so a foam volume that
  spends the reflectance as `b_b/b` whitens without hiding, which is the symptom rather than the
  mechanism.
- **P/D** — [Surface reflection names two opposite things: a loss and a
  trap](12-water-rendering.md#surface-reflection-names-two-opposite-things-a-loss-and-a-trap),
  derived in [`12a` §7](12a-water-derivations.md#one-interface-two-diffuse-reflectances). That one
  interface carries two diffuse Fresnel constants, that they are the same integral over `2μ dμ` with
  the index pair swapped, and that they are tied by Walsh's relation, are standard optics (`P`; the
  **name** Walsh is still `?` — see the `1/n²` entry above, where the 1926 paper is cited but was not
  read here). Every figure is a quadrature recomputed here (`D`, 2000-node Gauss–Legendre, the
  internal integrand split at `μ_c` because it is discontinuous there): `R_ext = 6.6248 / 6.6690 /
  6.7511 %` and `R_int = 47.3712 / 47.6166 / 48.0681 %` across the IOR triple 1.3320/1.3348/1.3400,
  hence a ratio of **7.151 / 7.140 / 7.120** and Walsh closing to **6×10⁻¹¹**; the directional
  external values 2.056% at normal, **2.217%** at 32.78° and **12.241%** at 68.98°; the decomposition
  43.874% + 3.743%. The **cost of the confusion** — trap gain −9.2 / −24.9 / −29.2 % per channel if
  `R_ext` is used internally, ×0.561 if `R_int` is used externally, ×0.421 for both — is arithmetic
  on this chapter's liner `ρ = 0.222 / 0.585 / 0.681` (`D`) and is a property of that albedo, not a
  general constant; what transfers is that the two errors are of *different kinds*, one chromatic and
  one flat. ⚠️ **This entry exists because the chapter used both senses under one word** in several
  places for its whole run; those uses are now disambiguated in place, and a reader who took the
  wrong one was out by 7.14× in the direction that darkens a pool interior.
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
- **P/D** — [A floating body, and the split its own meniscus
  hides](12a-water-derivations.md#a-floating-body-and-the-split-its-own-meniscus-hides). The
  generalisation of the wall fillet to a hull is one substitution — with perfect wetting the surface
  leaves the solid tangentially, so `φ_w` is the solid's own tangent angle, which on a sphere is the
  contact polar angle `β` — and the rest of the fillet algebra is unchanged (`P`, with the perfect
  wetting itself a **choice**, `?`, as it is for the wall). The **flotation balance**
  `m = ρ[V_cap − z_w π r_w²] − (σ/g)2π r_w sin φ_w` is the divergence theorem plus the contact line's
  own pull (`P`); the two capillary terms carrying **13.0%** of the weight, and Archimedes alone
  floating the ball **2.50 mm** high, are that ball (`D`, re-solved here by bisection on `β` at the
  implementation's ρ = 1000, where every row of the balance reproduces its printed figures exactly;
  `12`'s ρ = 998 convention moves the draught by 0.04 mm). The **tangency condition** `β + θ_w > 90°` **and**
  `R(1 − sin(β + θ_w)) > z_w sin θ_w` is derived here from the perpendicular distance of the limiting
  ray to the body's centre (`P/synthesis`); its `z_w = 0` corollary — no above-water camera sees a
  floating sphere's wet half until the draught exceeds **12.55%** of the diameter — is general, and
  the frame-specific numbers (`β + θ_w = 92.01°`, 0.068 mm against 1.541 mm, short by **22.6×**) are
  that ball at that eye (`D`, recomputed here). The threshold `β > 51.78°`, i.e. `m > 0.480 kg` against FINA's 0.450 kg
  ceiling, is the flotation solve evaluated at `θ_w = θ_c` (`D`). The **guard** is the one thing here
  that shares nothing with the derivation: 396 `(β, θ_w)` pairs × 4800 rays through the shipped
  ray–sphere intersector, and it **failed** the first version of the derivation on 196 of 396 pairs.
  The **instrument** argument — a FINA size 5 ball because circumference (0.68–0.71 m) and mass
  (0.400–0.450 kg) are both published, so the draught is an output with a published tolerance —
  **38.40–40.79 mm** across the mass band and **40.15–39.10 mm** across the circumference band — is
  `P/D` and is stated as method in
  [`11`](11-verification-failures.md#pick-instruments-whose-parameters-someone-else-has-fixed).
  ⚠️ **A correction made in this pass:** an inflatable ring of tube radius 90 mm and skin 0.25 mm has
  `ρ_eff = ρ_PVC·2t/r + ρ_air = 8.42 kg/m³` and floats at 0.842% of its volume, which is
  **5.27 mm of a 180 mm tube** — not the 9 mm in circulation, which needs 18.7 kg/m³ and looks like a
  *sphere's* `3t/R` applied to a tube. The companion beach-ball figure (17 mm of a 360 mm sphere)
  reproduces at 17.2 mm, which is what identifies the slip (`D`, both recomputed here). Its meniscus
  climbs **0.93 mm**, 17.7% of that draught, which is the real reason an inflatable cannot read a
  waterline. The full derivation and the correction are
  [`12a`'s eighth non-reproducing item](12a-water-derivations.md#what-did-not-reproduce).
- **F** — The four-gate masking contract (depth fade, extinction along the light path, sun
  visibility at the surface entry point, irradiance-not-albedo) and the tier ladder as a whole:
  production practice assembled over the physics above. The shadow-at-entry-point rule is the one
  most often skipped and is stated here as doctrine, not as a cited result. ⚠️ **An attribution
  corrected in this pass:** the chapter attributed a shadow that reads as a *reduction* rather than a
  hole to the occluder being non-binary — fabric or foliage transmitting 15–30% diffusely. That
  mechanism is real and stays, and it is **not the dominant one**. A facet tilted by `ε` swings the
  transmitted ray by `|1 − cos θ_i/(n cos θ_t)|·ε`, which is differentiated Snell (`P`) and is the
  same derivative the [focusing
  number](12a-water-derivations.md#the-focusing-number-derived) is built from — **0.2508** at normal
  incidence, where it is exactly `1 − 1/n`, and **0.6241** at this chapter's 21° sun (`D`,
  recomputed here). So the shadow of an **opaque** body fills in too, and on the reference
  implementation's float it fills by **84%**: an 87 mm rms wander (slope rms 0.0712 over a 1.96 m
  slant) against a 221 mm shadow, geometric umbra 0.0800 m² against 0.0131 m² surviving in the
  caustic map, bed radiance **72.8%** inside and net contrast **61.5%** (`D`, that ball, that sun,
  that basin — the umbra's core is measured at exactly zero, so the occluder really is opaque). What
  transfers is the coefficient and its sun dependence, not the 84%.
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
- **`?`** — **Waterline weathering: the zones, the mechanisms and their signs**, in [A liner in
  service is an albedo field](12-water-rendering.md#a-liner-in-service-is-an-albedo-field-and-the-waterline-is-its-coordinate).
  The organising claim — that a liner in service is an albedo *field* keyed to `h = z − z_water`
  rather than one swatch — is this skill's framing over the project owner's ruling that not every
  pool is newly laid. The chemistry under it is **standard in kind and unsourced in quantity**, and
  the quantities are exactly where the section stops on purpose:
  - **Carbonate scale at the waterline** by evaporative concentration past the saturation index is
    standard pool-operation practice (`D` in kind, the same practice cited in the pool-chemistry
    entry above). The **deposition rate, the band width (quoted as "order 1–5 cm"), and the albedo
    and spectrum of pool scale were not measured and not chased to a source** (`?`). The organic
    half of the deposit — body oils, sunscreen, airborne dust — is observation, with no composition
    or reflectance behind it (`?`).
  - **UV photodegradation of PVC liner pigment and plasticiser** above the line, and **oxidative
    attack by free chlorine** below it, are standard polymer-degradation mechanisms from model
    knowledge; **neither was chased to a primary source, and there is no rate, no dose–response and
    no measured albedo of an aged liner against a new one** (`?`). That UV-B is stripped in the top
    decimetres of water faster than UV-A is standard water optics in kind; the depth grading of the
    submerged wall that this chapter infers from it is **argued, not computed here** (`?`).
  - **Biofilm and algae in dead-circulation corners**, darkening and green-shifted, is
    pool-operation practice plus direct observation (`F`); the establishment and kill times are
    stated as orders of magnitude and are `?`. That corners are the dead zones *because* the return
    jets sweep the open water is this chapter's own [driven-basin](12-water-rendering.md#the-wave-field-is-a-driven-basin-not-a-spectrum)
    reasoning, not a measured circulation map (`?`).
  - **Abrasion** on treads and the shallow end is `F`; the claim that its roughness change is a more
    reliable cue than its albedo change is this chapter's and is untested (`?`).
  - The **modification-versus-deposit composition split** (a multiply against a coverage lerp toward
    the deposit's own albedo) and the **six inference rules R1–R6** are this chapter's construction
    over those mechanisms (`F`). R4's content — orientation-independence rules a shading explanation
    out — is the reference observer's own reasoning as recorded in the project bar, not a citation.
  - **Nothing in this section carries a measured number**, which is the entry's most important line.
    A reader who wants a figure has to go and get one; the durable content is the zone set, the
    mechanism in each, and the **sign**, and the signs are checkable against any photograph of a pool
    that has been in service.
- **D/?** — **The weathering amplification**, in [Where a weathering profile is allowed to come
  from](12-water-rendering.md#where-a-weathering-profile-is-allowed-to-come-from-and-what-the-water-does-to-it).
  `A = ρ/(1 − ρ·R_int)`, `G = 1/(1 − ρ·R_int)` and the identity `dlnA/dlnρ = G` are algebra,
  recomputed here (`D`); the four-row table at `R_int = 0.47617` (the green diffuse internal
  reflectance already quadratured in the Fresnel entry above) reproduces to every digit printed, as
  does the paired **+27.5% albedo → +36.3% apparent** step from ρ = 0.40 to 0.51.
  **The depth-aware table is the load-bearing correction and it is per-channel.** For a bed at depth
  the denominator is `1 − ρ·G_rt(τ)`, not `1 − ρ·R_int` — `G_rt → R_int` only as `τ → 0`, exactly as
  [Attenuation and escape do not
  factorise](12-water-rendering.md#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them)
  establishes — so on this chapter's pool (`G_rt = 0.0965 / 0.3277 / 0.4445` at
  `τ = 0.3664 / 0.0742 / 0.0143`, both already `D` in the LUT entry above) the gain runs **1.04–1.07
  in red against 1.22–1.45 in blue** where the diffuse constant promises 1.24–1.50. The diffuse-
  constant table is therefore an **upper bound**, and quoting it for a body with depth overstates the
  amplification by up to 40% in red. Round-trip transmittances `exp(−a·2.80) = 0.4806 / 0.8621 /
  0.9718` at the 1.40 m floor are arithmetic on the reference implementation's band means (`D`).
  The three consequences — contrast amplified by exactly `G`, level attenuated by exactly the round
  trip, and hence a colour-neutral material change arriving cyan-shifted at a red:blue swing ratio of
  **0.494** — are this chapter's composition of those two results (`F`) and were **not** checked
  against `reference-impl/` (`?`).
  One bookkeeping note for anyone comparing the two tables in `12`: the `Apparent` column of the
  liner table in [The two materials a pool actually
  has](12-water-rendering.md#the-two-materials-a-pool-actually-has-and-neither-is-water) is **not**
  `ρ·G` — across all six of its rows it is consistent with `ρ·G` carrying a constant first-surface
  factor of ≈ 0.934 = `1 − R_ext`. The two tables agree exactly on gain and on every ratio; only the
  absolute column differs, and only by that constant.
- **F** — **The stated/derived doctrine and the runtime form of the profile**, in the same section.
  That light transport is derived and material parameters are stated is [OpenPBR's own
  division](12-water-rendering.md#saying-it-in-openpbr-and-where-the-mapping-stops) restated, and
  the freeze-then-render test (*would you have written the same profile if you had never seen the
  render?*) is this skill's doctrine, not a cited method. The runtime rules — two `z_water` (datum
  for the deposit, instantaneous surface for the wet film), `h` sourced from the same field every
  other consumer reads, exclusion from RVT/VT page generation carried over from `13`'s
  [state-layer doctrine](13-snow-weather-surface-state.md#static-says-possible-runtime-says-current),
  the 1-D-LUT-in-`h` form with a non-linear parameterisation, and the prohibition on touching
  `transmission_*` — are this chapter's composition over contracts it already owns. The texel
  arithmetic is exact (±2 m at 256 texels is 15.6 mm/texel) but the tide-line width it is compared
  against is `?`. **No implementation of this profile exists in `reference-impl/`** (`?`): the
  section is a specification, and nothing in it has been rendered or falsified.
- **F** — That treated pool water sits outside every Jerlov class (`b_b ≈ 0`, `c ≈ a`, Secchi
  exceeding body depth), that pool colour is therefore a bottom-albedo property rather than a
  scattering one, and the man-made gating table: this skill's composition from the optics above
  plus standard pool-operation practice.
- **P/synthesis, with three `D` measurements and one `?`** — **[An illuminant per receiver, and
  what that costs at a waterline](12-water-rendering.md#an-illuminant-per-receiver-and-what-that-costs-at-a-waterline).**
  The general result — that an illuminant is `(1/π)∫L(ω)(ω·N)⁺dω` and therefore a property of the
  *receiver's orientation*, with weights `cos θ sin θ` for a horizontal face and `sin² θ` for a
  vertical one, agreeing at exactly ½ under a uniform sky and nowhere else — is derived in
  [`10`](10-lighting-shadows.md#an-illuminant-is-a-property-of-the-receivers-orientation-not-of-the-scene)
  from the cosine law alone; the ½ was verified here by quadrature to 10⁻¹¹. **D** for the three
  measured triples, all recomputed here on the reference implementation's own sky and basin: the
  band's own hemisphere against half the derived deck illuminant (1.232 / 1.099 / 0.966), the
  sun-facing-to-averted band ratio (1.201 / 1.238 / 1.234 per channel, **1.231** in luminance), and
  the three-term irradiance table with the reflected sky at 19 / 12 / 11 % of the band's total and
  63 / 23 / 21 % of its lower half. **D** for the `sin²θ`-weighted mean external reflectance
  **0.2112** against 0.0667 cosine-weighted and 0.0206 at normal incidence, quadratured here from
  the exact Fresnel equations at `n = 1.3348`. ⚠️ **`?` on the run's printed "total"** for that
  table: it prints `(0.4761, 0.9220, 1.3568)` where its own three components sum to
  `(0.4461, 0.8233, 1.2164)` — a discrepancy of 6.7 / 12.0 / 11.5 %, not a constant, so a different
  normalisation rather than a rounding. This chapter quotes the components, marks the total open,
  and does not know which is right. ⚠️ The reference implementation's **0.243** for the reflected
  sky's mean `R_ext` is *not* the 0.2112 above: its weighting also carries the sky's own horizon
  brightening. Two different quantities, one name. **D, integrated here** for the ledge table
  (87.5 / 81.5 / 70.6 % of the full upper half, averaged over a 100 mm strip at 20 / 30 / 50 mm of
  overhang; 99.7 / 99.0 / 96.0 % at the strip's foot) from the closed form `(α + sin α cos α)/π`,
  `α = atan(D/w)`, which is exactly 0.50 at `w = 0`. ⚠️ A **94%** figure for a 30 mm overhang on this
  geometry does not reproduce: the mean is dominated by the strip's top edge, where the form goes to
  zero, so the answer is set by how far the strip's top sits below the ledge — a section question,
  not a lighting one. Quote the profile or the foot, never the mean.
- **D/P, with one derived bound** — **[The upgoing half, traced: the return leg, the mirror, and the
  fixed point](12-water-rendering.md#the-upgoing-half-traced-the-return-leg-the-mirror-and-the-fixed-point).**
  The gather's shape — trace the upgoing half, let the trace decide window from mirror, exact
  per-direction internal Fresnel by Stokes reversibility, walls as emitters — is `reference-impl/`'s
  `up_gather` read as doctrine (**D**), and the physics in it is standard (**P**). **D** for the
  bed-ambient table (window sky falling 17% in green while the mirror-and-wall term rises ~8×, the
  bed's ambient +39% in green, the occluder's shadow arriving at 92% of its own depth against 91%),
  the 35.3% wall share of a bed point's hemisphere, the 87%-of-the-floor window-occlusion figure at
  `1.40·tan 48.5° = 1.58 m` of run in an 8 × 4 m basin, the ×1.96 sky over-give, the +9.5 / +15.3 /
  −6.2 % wall response and the +39% riser response, and the 4.9% / 1.4% riser hole. **D, recomputed
  here** for the truncation table (`1/(1 − ρR_int)` against one and two bounces and against the
  wrong cone, at `R_int = 0.47617` and `1 − 1/n² = 0.43874`, ρ = 0.222 / 0.400 / 0.585 / 0.681) —
  the finding that the truncation error is **chromatic**, hence a desaturation rather than a
  darkening, is this chapter's reading of that table and is new here. **Derived here** for the
  geometric residual bound `tail ≤ dₖ·r/(1−r)`, and its evaluation at the run's measured gains
  (0.335 / 0.442 on the bed, 0.378 / 0.475 on the wall → 0.50 / 0.79 and 0.61 / 0.90 × the last
  increment, i.e. 0.012% and 0.033% of the converged level in green). `?` for the still-plane mirror
  (the wave field is not on the mirror leg) — stated as an approximation, with its argument, not as
  a result.
- **`?` throughout, and deliberately** — **[Fouling in the corners, from an
  algorithm](12-water-rendering.md#fouling-in-the-corners-from-an-algorithm-rather-than-from-a-texture).**
  Nothing in this section is rendered, measured or falsified; it is a specification written before
  implementation so the choices can be argued with rather than discovered in a diff. What is **P**
  in it: potential flow as the classical first approximation, and the corner solution
  `φ = A r^(π/α) cos(πθ/α)` with `|u| ~ r^(π/α − 1)` — **derived here**, giving exactly zero velocity
  at a square corner (`r¹`), `r^0.5` at a 120° chamfer and a `r^(−1/3)` **singularity** at a
  re-entrant one. That the model therefore *flatters the result precisely where the effect is
  wanted* is the section's loudest mark. **Derived here** for the patchiness argument: linearising
  `ḋ = S(1 + κd)(1 − d)` about a uniform state gives growth rate `S(κ(1 − 2d̄) − 1)`, positive above
  a threshold coupling, so blotchiness is a linear instability and not a texture. **`?`** for
  everything chemical and everything biological: which organism dominates in which conditions, every
  rate, and the two-number susceptibility table (PVC / glazed ceramic / concrete) — those are
  *orderings* a materials scientist would recognise, not measurements, and no numbers are stated
  because none were measured. **A rate is not renderable at all** — it needs water hardness,
  sanitiser regime, cumulative UV dose and polymer formulation, none of which is renderer input —
  which is why the section states susceptibility instead. **F** for the parameter placement rule
  (susceptibility on the material, the `neglect` path on the instance) and for the non-zero default,
  which rests on an observation about pools in service rather than on a measurement.
- **D/P, with the IOPs `?`** — **[The surf zone: what a pool reference lends the sea, and the one
  thing it cannot](12-water-rendering.md#the-surf-zone-what-a-pool-reference-lends-the-sea-and-the-one-thing-it-cannot)**,
  and the three-whites table in [Aerated
  water](12-water-rendering.md#aerated-water-foam-spray-and-whitewater). The transfer table is
  bookkeeping over results already provenanced in this file — Fresnel both sides, the critical
  angle, `L/n²`, Beer–Lambert, the trapped series and dispersion are properties of an interface and
  an IOR and carry unchanged; **`b_b ≈ 0` does not, and it is the only entry that does not.**
  **D, recomputed here**: `1 − 1/n²` = 43.72% at `n = 1.333` and **43.874%** at 1.3348, running
  43.64 / 43.87 / 44.31 % across the IOR triple; pure-water transmission over 2 m
  `(0.593, 0.899, 0.980)` at the band means. **Derived here**: the wedge inversion
  `c(λ) = −ln(T₂/T₁)/(L₂ − L₁)`, whose value is that the ratio cancels source spectrum, both surface
  transmissions and camera gain — a within-frame pair in the sense `11` requires. **`?`** for the
  coastal IOPs themselves: no spectrum was extracted from any of the nine frames, and the CDOM /
  chlorophyll attribution of a green wave face is an identification, not a measurement. **`?`** for
  the sediment transport in [Water-body optical
  identity](12-water-rendering.md#water-body-optical-identity-where-the-iops-come-from) — the
  entrainment law and the fall velocity in `db/dt + u·∇b = E − w_s b/d` are named to give the
  *shape* of the coupling, and neither term is quantified here. The load-bearing claim is
  categorial and needs no number: in the surf zone an IOP is a **state variable produced by the
  dynamics**, not a material input. **F/D** for the two observational rulings the section rests on —
  the two-colour backlit wave (a category refutation that needs no measurement, and the sharpest
  available falsification of a `waterColor` tint), the reveals/hides discriminator watched under
  motion, and the two-lifetime cloud. Each is a *reading* of an owner photograph, reproducible by
  anyone with a camera and a coast, and none is a calibration. **`?`** for the multivalued free
  surface: it is stated as a representation change with no route proposed, which is the honest state
  of it. **The reference set has a named gap** — no frame catches the backwash lifting sand, i.e.
  the erosive half of the swash cycle, and the inference that would fill it from the other eight is
  exactly the inference not to make.
- **T/D** — [The 30° ceiling](12-water-rendering.md#the-30-ceiling-a-single-valued-crest-cannot-be-read-lengthwise).
  Two independent results, and they are different tiers.
  **Stokes' corner is `T`**: the stagnation/wedge exponent match giving `2α = 120°` is Stokes (1880),
  standard in every water-wave text, and it is *reproduced here in full* rather than quoted — the
  four lines in the chapter are the whole of it, and they carry no depth, wavelength or wave height,
  which is the property the conclusion rests on. Longuet-Higgins & Fox (1977), max inclination of the
  almost-highest wave ≈ **30.37°**, is **`P`** — cited, not reproduced, and quoted only as the
  slightly-more-generous cap. Nothing below turns on 30 vs 30.4.
  **The two-cone condition is `D`, and it is this chapter's own**: `α₁ + α₂ ≥ 2(90° − θ_c)` =
  82.689 / 82.962 / 83.464° on the IOR triple. It follows from requiring one straight in-water
  direction to lie inside the entry cone *and* the exit cone, with the `180° − (α₁+α₂)` normal
  separation from the spherical triangle inequality — so it is a **necessary** condition for any
  single-valued surface in 3-D, independent of the shape between the two crossings, and it is not
  sufficient. ⚠️ **It supersedes the framing this project used for two rounds**, which was "the face
  must exceed `90° − θ_c` = 41.48°": that figure is the symmetric special case and the reasoning
  behind it (*"a ray entering water is confined to the Snell cone"*) named only the entry crossing.
  The number was right; half the mechanism was missing, and the missing half is what makes the
  result general and what makes it a statement about a **sum** rather than about one face.
  Checked here by shooting the full incidence hemisphere at a wedge and refracting: zero survivors
  at sums of 16.5 → 82.96°, first survivors at 83.10°, and 30+53.1 / 20+63.1 / 10+73.1 open at the
  same sum with the same ray count — i.e. the split is verified not to matter, which is the part an
  algebraic argument alone would leave open.
  **The Fresnel table** (best `T_in·T_out` and the flux share, 41.6° → 70°) is `D`, this chapter's
  own unpolarised Fresnel on both crossings over a cosine-weighted incidence hemisphere. Its role is
  to say the geometric floor is *not* the operative threshold; the ≈50° / ≈55° figures for a tenth
  and a fifth of the flux are read off that table and are not sharp constants.
  **The render measurement** — through-face fraction **0.0000** at 8.23° and at 15.78° steepest
  face, ~70 000 water pixels a side — is `D`, recomputed here from `reference-impl/beach_render.py`
  (`surface_report`, `chord_report`/`through_face`) at half the shipped frame resolution. It is
  consistent with the theorem and does **not** test it: 15.78 + 15.78 = 31.6° is nowhere near the
  floor, so the frame confirms the scene, not the bound. The bound is carried by the geometry.
- **P/D** — [A peaked crest is not a steep face](12-water-rendering.md#a-peaked-crest-is-not-a-steep-face-one-harmonic-two-moments).
  Second-order Stokes' bound harmonic `η = a[cos φ + r cos(2φ+ψ)]` and its depth function
  `C(kd) = cosh(kd)(2 + cosh 2kd)/sinh³(kd)` are **`P`** (Dean & Dalrymple, *Water Wave Mechanics for
  Engineers and Scientists*, the second-order surface profile) — structure cited, and this appendix
  did not open it; the shallow limit `r → 2·Ur` follows from substituting `C → 3/(kd)³` and is `D`.
  Everything else in the section is **`D`, this chapter's own**:
  the closed-form moments and the invariant `Sk² + As² = (9/16) r²/((1+r²)/2)³`, checked here against
  a direct 2²⁰-sample quadrature of `⟨η³⟩` and `⟨H(η)³⟩` at four `(r, ψ)` pairs and agreeing to all
  printed digits; the two secondary-crest limits `r = 1/4` and `r = 1/2`, each verified by counting
  sign changes of `dη/dφ` across the limit (2 → 3 → 4 roots at `r` = 0.24 / 0.25 / 0.26); the exact
  slope gains **3√3/4** and **1 + 2r**, against `beach.slope_gain`'s numerical maximum
  (1.2990380 vs 1.2990381); and the monotone sweep along the validity boundary establishing **2.000
  as the family ceiling**. The 97.7% figure is the reference bay's 15.78° against `×2` on its own
  8.23° linear face — one scene, quoted as a scene.
  ⚠️ **`?` on `ψ` itself.** Nothing above fixes what `ψ` *is* for a real shoaling wave; the section
  is deliberately written so that no claim depends on it — the two endpoints are derived (a bound
  harmonic is phase-locked at `ψ = 0`; a fully broken bore is a sawtooth at `ψ = −π/2`) and every
  number quoted sits at one endpoint or is a bound over the whole range. Ruessink et al. (2012)
  publish a `ψ(Ur)` that goes the same way; it could not be verified from a source here and is
  **not** claimed or used.
