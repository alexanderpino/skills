---
type: Bibliography
title: Papers — sea ice
description: "Sources for the ninth wave: the sea-ice floe size distribution and the argument about whether it is a power law, floe shape statistics, the free-drift momentum balance, and pressure-ridge sail height."
tags: [bibliography, provenance, generation, water]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — sea ice

One family, one document. Entry format, tier definitions and the two non-negotiable rules live
in `papers-flow.md`; they are not restated here.

Note for editors: entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

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
  `papers-wave-3.md` uses for McGetchin.
- **Parmerter & Coon (1972)** on ridge formation and **Leppäranta (2011)**, *The Drift of Sea
  Ice* — named in prose as the standard references behind the ridging mechanism and the turning
  angle. Neither was opened, neither is cited, and no number is taken from either.

## Sea ice

- **rothrock1984** `P` — Rothrock, D.A. & Thorndike, A.S. (1984). *Measuring the sea ice floe size distribution.* Journal of Geophysical Research 89(C4), 6477–6486, doi:10.1029/JC089iC04p06477. — The founding paper of the subject, and much more sceptical than its reputation. Defines the two useful distributions (`F`, fractional area covered by floes no smaller than `p`; `N`, number per unit area no smaller than `p`), proves the finiteness constraints on the exponent, gives the measured shape ratios for 782 digitised summer floes, and reports slopes between −1.7 and −2.5 while explicitly declining to assert a power law. Also the source of the result that a **Poisson line field has an exponential piece-size distribution**, which is the negative control for every tessellation-based floe generator. See the caveat above: the artefact read is the submitted manuscript in NASA report NAG-5-160.
- **denton2022** `P` — Denton, A.A. & Timmermans, M.-L. (2022). *Characterizing the sea-ice floe size distribution in the Canada Basin from high-resolution optical satellite imagery.* The Cryosphere 16, 1563–1578, doi:10.5194/tc-16-1563-2022. — 78 high-resolution optical images, 1999–2014, floe areas from 5 m² to 100 km². Reports a single power law over 50 m² to 5 km², least-squares slopes from −2.03 to −1.65 with mean −1.79 ± 0.08, an MLE mean of −1.77 ± 0.11, and — the honest number — that only 76% of the fits pass the Clauset goodness-of-fit test. Sect. 1 is the cleanest published statement of the one-power-law-or-two disagreement; Sect. 3.4 gives the `2m+1` conversion between area-based and diameter-based noncumulative slopes that explains much of the apparent disagreement; Sect. 2.3 explains why a cumulative FSD is concave-down for a bounded population and therefore ambiguous to read. Open access.
- **brunette2022** `P` — Brunette, C., Tremblay, L.B. & Newton, R. (2022). *A new state-dependent parameterization for the free drift of sea ice.* The Cryosphere 16, 533–553, doi:10.5194/tc-16-533-2022. — Sect. 3.1 states the sea-ice momentum equation and reduces it, under steady state and no internal ice stress, to the free-drift balance `τ_a = τ_w` with the closed-form solution `U_i = α·e^(−iθ)·U_a + U_w` and `α = sqrt(ρ_a C_a / ρ_w C_w)`. Sect. 1 reviews the measured wind factors and turning angles from Nansen (1902) onward and records that this one-line relation explains roughly 70% of sea-ice velocity variance in the central Arctic. Cited here for the balance and the coefficient band, not for the paper's own thickness-dependent parameterisation. Open access.
- **duncan2018** `P` — Duncan, K., Farrell, S.L., Connor, L.N., Richter-Menge, J., Hutchings, J.K. & Dominguez, R. (2018). *High-resolution airborne observations of sea-ice pressure ridge sail height.* Annals of Glaciology 59(76pt2), 137–147, doi:10.1017/aog.2018.2. — Sail heights derived from shadow lengths in Operation IceBridge visible imagery along 12 mapped Arctic pressure ridges. Cited for the only vertical numbers in this document: mean sail height 0.99–2.16 m, maximum 2.1–4.8 m, and a 0.6 m lower cutoff below which a bump is sastrugi rather than a ridge. Open access.
