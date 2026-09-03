---
type: Bibliography
title: Papers — coasts and sea ice
description: "Sources for what water does at the margin of the land: the equilibrium beach profile and its scale parameter, the Bruun rule together with the published case for abandoning it, alongshore transport and the high-angle instability that makes a coast roughen, threshold-driven cliff retreat, and the sea-ice floe size distribution and free-drift balance."
tags: [bibliography, provenance, generation, simulation, coastal, water]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — coasts and sea ice

One family, two documents, and a shared boundary: this is what happens where water meets land
rather than where it flows over it. `flow-routing.md` and `hydraulic-erosion.md` own water on the
land; `wave-models.md` owns the wave field itself. These sources own the margin.

Coastal erosion and sea ice sit together because each alone would be a stub of four entries, and
because they share the same structure of argument — a published law, a published rebuttal of it,
and a distribution whose exponent is contested.

**The tier table, the `[not-opened]` rule and the two non-negotiable rules live in
`papers-flow.md`** and are not repeated here.

Entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

Two subjects, two read logs, kept separate because the sources have nothing in common
beyond the boundary they describe.

### Coasts

Every `P` below was opened as a PDF and the cited section, equation, figure or page was read in
it. Where a figure carries the claim, the page was rendered and read as an image rather than
trusted to text extraction, because the numbers in this family live in figure annotations.

**`dean1991`** — the Journal of Coastal Research open archive PDF. Equations (1)–(5) on pp. 54–55
and equations (12)–(15) on p. 59 were read from rendered page images; the `A = 0.067 w^0.44`
annotation is inside the Figure 1 plot on p. 55 and was read the same way. The paper's own
Figure 9 caption on p. 59 supplies the two `A`-versus-grain-size anchors used downstream.
**`cooper2004`** — the author-hosted PDF of the published Elsevier article. §3 (pp. 159–160),
§4.1 (p. 161) and the closure-depth passage on p. 159 were read there.
**`ashton2006b`** — the Woods Hole open-access PDF of **Part 2**. Table 1 (p. 2), §2.3
(p. 4, equations 1–4), and §3.2 (p. 5, equations 7–10) were read there.
**`shadrick2022`** — the Nature Communications open-access PDF; the Results (p. 3) and the
Modelling subsection of Methods (p. 9) were read there.

⚠️ **Four sources are named in `coastal-erosion.md`'s prose and are deliberately absent here,
because they were not opened.**

- **Bruun, P. (1962)**, *Sea level rise as a cause of shore erosion*, J. Waterways and Harbors
  Division, ASCE 88, is the origin of the Bruun Rule. It was not reached. `coastal-erosion.md`
  therefore cites dean1991 eq. (15) — which states the rule, names it, and attributes it to Bruun
  — and cooper2004, which reproduces and attacks it.
- **Bruun, P. (1954)**, *Coast erosion and the development of beach profiles*, Beach Erosion
  Board Technical Memorandum 44, is where `h = A y^(2/3)` first appears. Not reached; dean1991
  p. 54 states the relationship and attributes it to Bruun (1954), and that is the citation used.
- **Pelnard-Considère, R. (1956)** is the origin of the one-line model. Not reached;
  ashton2006b §2.3 p. 4 derives the one-line evolution equation and attributes it to him.
- **Ashton, A., Murray, A.B. & Arnoult, O. (2001)**, *Formation of coastline features by
  large-scale instabilities induced by high-angle waves*, Nature 414, 296–300, is the paper that
  first reported the ~42° instability threshold and grew capes from it. Only the abstract was
  reached; the full text was not. ashton2006b — by two of the same authors, and openable — states
  the 42° result, attributes it to the 2001 paper, and independently supplies the equations from
  which 42.392° is recoverable, so that is the citation used.

Naming a paper in prose with the openable paper that reports it as the citation is the honest
form. Adding a bibliography entry for a paper nobody here opened would not be.

### Sea ice

**`rothrock1984`** — read as **Appendix I of NASA final report NAG-5-160**, *Remote Sensing of
Floe Size Distribution and Surface Topography*, retrieved from NTRS as document 19840017073 and
converted to text. Appendix I is the **submitted manuscript** of the JGR paper, carrying the
footnote "Submitted to Journal of Geophysical Research". ⚠️ **That is one step weaker than the
accepted manuscripts this corpus grades `P` elsewhere**, and there is direct evidence review
touched the numbers: the manuscript's prose gives floe area as `0.56 p²` while its own Table 1
gives `0.66`, and `denton2022`, reading the published paper, quotes `0.66`. Two independent
arithmetic checks in `scratchpad/w9/floe_numbers.py` resolve it to `0.66` — the table's
`perimeter/p = 3.17` and `area/perimeter² = 0.065` imply `area/p² = 0.653`, and the table's own
sd/mean column of `0.08` against `sd = 0.05` implies `0.66`, not `0.56`. Section, table and
figure numbers cited from it are the **manuscript's**; JGR page numbers are *not* asserted, and
the `p. 6477–6486` range is reported only as the published paper's citation, not as a locator.

**`denton2022`** — the publisher's open-access PDF at Copernicus, converted to text and read
directly. Sects. 1, 2.3, 2.3.1, 3.1 and 3.4 quoted from it.

**`brunette2022`** — the publisher's open-access PDF at Copernicus, converted to text and read
directly. The abstract, Sect. 1 and Sect. 3.1 with eqs. (1)–(6) quoted from it.

**`duncan2018`** — the Cambridge open-access PDF, converted to text and read directly. Abstract,
Introduction and the sail-height definition around eq. (10) quoted from it.

⚠️ **Sources named in `sea-ice.md` that were NOT reached, and are therefore not entries here.**

- **Stern, H.L., Schweiger, A.J., Zhang, J. & Steele, M. (2018).** *On reconciling disparate
  studies of the sea-ice floe size distribution.* Elementa 6, art. 49, doi:10.1525/elementa.304.
  This is the paper written specifically about the disagreement this document is built around,
  and **the publisher returned HTTP 403 to every retrieval attempt.** It is named in prose, and
  every claim that would have rested on it rests on `denton2022` instead, which reviews it,
  quotes its slope range from its Table 4, and applies the conversion between its convention and
  its own. Adding an entry for a paper nobody here opened would be the fabrication the tier
  rules exist to prevent.
- **Toyota et al. (2006, 2011)**, **Steer et al. (2008)**, **Geise et al. (2017)**,
  **Gherardi & Lagomarsino (2015)**, **Hwang et al. (2017)**, **Herman (2010)** — the studies on
  both sides of the one-power-law-or-two argument. None was opened. `sea-ice.md` reports the
  *existence and shape* of the disagreement, citing `denton2022` Sect. 1, which is where that
  list comes from; it quotes **no exponent** from any of them.
- **Thorndike & Colony (1982)**, *Sea ice motion in response to geostrophic winds*, JGR 87(C8),
  5845–5852 — the origin of every wind-factor and turning-angle number in the drift section. Not
  opened. `brunette2022` Sect. 1 reports its values and is cited for them, the same construction
  `papers-generation.md` uses for McGetchin.
- **Parmerter & Coon (1972)** on ridge formation and **Leppäranta (2011)**, *The Drift of Sea
  Ice* — named in prose as the standard references behind the ridging mechanism and the turning
  angle. Neither was opened, neither is cited, and no number is taken from either.
## The shore profile and its retreat


- **dean1991** `P` — Dean, R.G. (1991). *Equilibrium beach profiles: characteristics and applications.* Journal of Coastal Research 7(1), 53–84, ISSN 0749-0208. — The reference treatment of `h = A y^(2/3)`. Eq. (1) p. 54 states the form and attributes it to Bruun (1954) on Danish North Sea and Mission Bay profiles; eq. (3) p. 54 records that Dean (1977) least-squares-fitted `h = A y^n` to the 504 US Atlantic and Gulf profiles of Hayden et al. (1975) and found a central `n = 2/3`; eq. (4) p. 54 gives the physical reading, uniform wave energy dissipation per unit volume `D* = (1/h) ∂(E C_G)/∂y`, and eq. (5) p. 54 relates `A` to it. Figure 1 p. 55 is the empirical `A` against both grain diameter (Moore, 1982) and settling velocity, carrying the fitted `A = 0.067 w^0.44`. Eq. (8) p. 58 is the modified profile that adds gravity and so has a finite, planar beach face near the waterline instead of eq. (1)'s infinite slope. Eqs. (12)–(15) p. 59 carry the shoreline-recession algebra, including the seaward limit `W* = (H_b/(κA))^(3/2)` and the Bruun Rule itself. Open archive.
- **cooper2004** `P` — Cooper, J.A.G. & Pilkey, O.H. (2004). *Sea-level rise and shoreline retreat: time to abandon the Bruun Rule.* Global and Planetary Change 43(3), 157–171, doi:10.1016/j.gloplacha.2004.07.001. — The published refutation, and the reason no document in this corpus may state the Bruun rule without it. §3 pp. 159–160 goes through the claimed field verifications one at a time and reports, via the SCOR Working Group (1991) review, predicted-versus-measured errors from +224% to −68% at Chesapeake Bay sites, and that there has not been "a single field verification that the Bruun Rule actually operates as Bruun (1962) envisioned it". §4.1 p. 161 lists the assumptions — no net longshore transport, no aeolian or overwash gain or loss, a closed two-dimensional material balance, retreat always and never accretion — and reports that Zhang et al. (2004), searching the eastern US coast, could identify no site conclusively meeting them. P. 159 records that Bruun put the closure depth off east Florida at 18 m while nourishment design has since used values as shallow as 4 m, and that the US east coast shoreface extends to 10–12 m.

## Plan view: transport, the one-line model, and instability


- **ashton2006b** `P` — Ashton, A.D. & Murray, A.B. (2006). *High-angle wave instability and emergent shoreline shapes: 2. Wave climate analysis and comparisons to nature.* Journal of Geophysical Research: Earth Surface 111, F04012, doi:10.1029/2005JF000423. — **Part 2 only**; Part 1 (F04011, doi:10.1029/2005JF000422) was not opened and is not cited. Table 1 p. 2 sets out five alongshore transport formulations side by side with their maximising angles, including the CERC form's dependence `H_b^(5/2) cos(φ_b−θ) sin(φ_b−θ)` and its 45° breaking / 42° deepwater maxima, and the constants it uses (`K` typically 0.7, `ρ_s` 2.65 g/cm³, porosity 0.4). §2.3 p. 4 derives the one-line model from mass conservation, attributes the single-contour idea to Pelnard-Considère (1956), and reaches eq. (3), a **diffusion equation** for shoreline position with diffusivity eq. (4) `μ = −(1/D) ∂Q_s/∂θ`, `D` the shoreface depth — positive `μ` smoothing, negative `μ` growing perturbations. §3.2 p. 5 recasts CERC into deepwater variables, eq. (7), with `K_2 = 0.34 m^(3/5) s^(−6/5)` for r.m.s. wave height and 0.15 for significant height, and splits the resulting diffusivity eq. (8) into a wave-height factor eq. (9) and an angle factor eq. (10). Figure 3 p. 3 shows breaking wave height, breaking angle and transport varying along an undulating shoreline under refraction. The abstract p. 1 names the landforms the instability produces — capes, flying spits and alongshore sand waves — and records that the deepwater transport maximum falls between 35° and 50° across several common formulae. Open access via the Woods Hole repository.

## Cliff and rock coasts


- **shadrick2022** `P` — Shadrick, J.R., Rood, D.H., Hurst, M.D., Piggott, M.D., Hebditch, B.G., Seal, A.J. & Wilcken, K.M. (2022). *Sea-level rise will likely accelerate rock coast cliff retreat rates.* Nature Communications 13, 7005, doi:10.1038/s41467-022-34386-3. — Cited here for the *form* of the cliff-retreat model rather than for its sea-level projections. The Modelling subsection of Methods, p. 9, describes the coupled rock-coast evolution model: wave hydraulic and mechanical properties are expressed as a wave assailing force built from wave height and an exponential decay function across the platform, the domain is a grid of cells, and **a cell erodes only once that force exceeds a material resistance value `F_R` assigned to its rock**, with intertidal weathering acting to lower `F_R` rather than to erode directly. It is explicit that cliff retreat there is driven exclusively by wave attack at the cliff foot, with subaerial weathering and groundwater unrepresented. P. 3 gives the measured historical context this document uses for the episodicity argument: ~130-year mean retreat of 5.8 ± 4.0 cm/yr at Bideford and 5.9 ± 4.3 cm/yr at Scalby, against a 2–25 cm/yr range along ~2 km of the same coasts, attributed to "the stochastic pattern of erosion in space and time". P. 2 states that cliff erosion is intrinsically episodic. Open access.

## Sea ice


- **rothrock1984** `P` — Rothrock, D.A. & Thorndike, A.S. (1984). *Measuring the sea ice floe size distribution.* Journal of Geophysical Research 89(C4), 6477–6486, doi:10.1029/JC089iC04p06477. — The founding paper of the subject, and much more sceptical than its reputation. Defines the two useful distributions (`F`, fractional area covered by floes no smaller than `p`; `N`, number per unit area no smaller than `p`), proves the finiteness constraints on the exponent, gives the measured shape ratios for 782 digitised summer floes, and reports slopes between −1.7 and −2.5 while explicitly declining to assert a power law. Also the source of the result that a **Poisson line field has an exponential piece-size distribution**, which is the negative control for every tessellation-based floe generator. See the caveat above: the artefact read is the submitted manuscript in NASA report NAG-5-160.
- **denton2022** `P` — Denton, A.A. & Timmermans, M.-L. (2022). *Characterizing the sea-ice floe size distribution in the Canada Basin from high-resolution optical satellite imagery.* The Cryosphere 16, 1563–1578, doi:10.5194/tc-16-1563-2022. — 78 high-resolution optical images, 1999–2014, floe areas from 5 m² to 100 km². Reports a single power law over 50 m² to 5 km², least-squares slopes from −2.03 to −1.65 with mean −1.79 ± 0.08, an MLE mean of −1.77 ± 0.11, and — the honest number — that only 76% of the fits pass the Clauset goodness-of-fit test. Sect. 1 is the cleanest published statement of the one-power-law-or-two disagreement; Sect. 3.4 gives the `2m+1` conversion between area-based and diameter-based noncumulative slopes that explains much of the apparent disagreement; Sect. 2.3 explains why a cumulative FSD is concave-down for a bounded population and therefore ambiguous to read. Open access.
- **brunette2022** `P` — Brunette, C., Tremblay, L.B. & Newton, R. (2022). *A new state-dependent parameterization for the free drift of sea ice.* The Cryosphere 16, 533–553, doi:10.5194/tc-16-533-2022. — Sect. 3.1 states the sea-ice momentum equation and reduces it, under steady state and no internal ice stress, to the free-drift balance `τ_a = τ_w` with the closed-form solution `U_i = α·e^(−iθ)·U_a + U_w` and `α = sqrt(ρ_a C_a / ρ_w C_w)`. Sect. 1 reviews the measured wind factors and turning angles from Nansen (1902) onward and records that this one-line relation explains roughly 70% of sea-ice velocity variance in the central Arctic. Cited here for the balance and the coefficient band, not for the paper's own thickness-dependent parameterisation. Open access.
- **duncan2018** `P` — Duncan, K., Farrell, S.L., Connor, L.N., Richter-Menge, J., Hutchings, J.K. & Dominguez, R. (2018). *High-resolution airborne observations of sea-ice pressure ridge sail height.* Annals of Glaciology 59(76pt2), 137–147, doi:10.1017/aog.2018.2. — Sail heights derived from shadow lengths in Operation IceBridge visible imagery along 12 mapped Arctic pressure ridges. Cited for the only vertical numbers in this document: mean sail height 0.99–2.16 m, maximum 2.1–4.8 m, and a 0.6 m lower cutoff below which a bump is sastrugi rather than a ridge. Open access.
