---
type: Bibliography
title: Papers — river networks as authored objects
description: "Sources for the fourth wave: downstream hydraulic geometry, meander and braiding thresholds, Horton–Strahler ordering, and the graphics papers that build a river network before they build the terrain."
tags: [bibliography, provenance, generation, hydrology, rivers]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — river networks as authored objects

One family: the river network treated as a thing an author makes, rather than a thing erosion
leaves behind. Entry format, tier definitions and the two non-negotiable rules live in
`papers-flow.md`; they are not restated here.

Note for editors: entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

Every `P` below was opened and the cited pages read. The specific artefact each grade rests on:

**`leopold1953`** — the USGS scan at `pubs.usgs.gov/pp/0252/report.pdf`. The two exponent triples
were read off the page images of pp. 9 and 16, not off the OCR text layer, which mangles `b` to
`6` and drops the `m = 0.1` line entirely.
**`leopoldwolman1957`** — the USGS scan at `pubs.usgs.gov/pp/0282b/report.pdf`. Same treatment:
eq. (1) on p. 60 and the wavelength fit on p. 59 are absent from the OCR and were read from the
page images.
**`strahler1957`** — a scan of the Trans. AGU pages hosted at `pdodds.w3.uvm.edu`. Figures 3 and
4 on p. 915 and the order-designation text on p. 914 were read from the page images.
**`genevaux2013`** — the authors' PDF hosted at Purdue CGVLab; §4–§7 read there.
**`peytavie2019`** — the authors' PDF at `perso.liris.cnrs.fr/eric.galin`; §4–§5 read there.
**`paris2023`** — the accepted version deposited at HAL (hal-04227965); §4 and §6 read there.
**`candel2021`** — open access (SAGE, CC-BY) at `edepot.wur.nl/532990`; §2.2, §2.3, eqs. (4)–(11)
and Table 1 read there.

⚠️ **Three sources are deliberately absent.**

**Horton (1945)**, *Erosional development of streams and their drainage basins*, GSA Bulletin 56,
275–370, is where the law of stream numbers and the bifurcation ratio originate. It is paywalled
at GeoScienceWorld and **could not be obtained**. `river-networks.md` therefore cites
`strahler1957` for the bifurcation ratio, since Strahler restates Horton's law and gives the
numbers this document actually uses, and names Horton in prose as the origin.

**Van den Berg (1995)**, *Prediction of alluvial channel pattern of perennial rivers*,
Geomorphology 12, 259–279, is the origin of the potential-specific-stream-power discriminator.
It is paywalled at Elsevier and **was not reached**. The discriminator's equations are taken from
`candel2021`, which restates them as its eqs. (4)–(8) and, unlike the original, measures how well
they classify a modern dataset.

**Dunne & Leopold (1978)**, *Water in Environmental Planning*, is the source both graphics papers
cite for `φ = 0.42 A^0.69`. It is a textbook, it **was not opened**, and no entry is made for it.
The coefficient is attributed here to `genevaux2013` and `peytavie2019`, which both print it.

## River networks

- **leopold1953** `P` — Leopold, L.B. & Maddock, T., Jr. (1953). *The hydraulic geometry of stream channels and some physiographic implications.* U.S. Geological Survey Professional Paper 252. — The origin of hydraulic geometry: width, mean depth and mean velocity each a power function of discharge, `w = aQ^b`, `d = cQ^f`, `v = kQ^m`, with `b + f + m = 1` forced by `Q = wdv`. Two distinct exponent triples, and the distinction is the load-bearing part: *at a station*, watching one cross section through a flood, and *downstream*, comparing sections at constant discharge frequency. The paper is equally explicit that the **coefficients** `a`, `c`, `k` are not universal — "Width and depth for a given discharge vary widely from one cross section to another" (p. 9) — so it publishes an exponent, not a width.
- **leopoldwolman1957** `P` — Leopold, L.B. & Wolman, M.G. (1957). *River channel patterns: braided, meandering and straight.* U.S. Geological Survey Professional Paper 282-B (Physiographic and hydraulic studies of rivers), from p. 39; the contents run to appendix H at p. 81 and the end page is not asserted. — The planform paper. Defines a braid as a reach with "relatively stable alluvial islands, and hence two or more separate channels" and a meander as sinuosity ≥ 1.5, calls the latter arbitrary, and then draws the one line every later channel-pattern paper argues with: a slope–discharge threshold separating braided from meandering reaches. Also fits meander wavelength against bankfull width, and reports the observed wavelength-to-width ratio drifting from ~7 at small widths to ~15 at large ones. The Cottonwood Creek reach — the same discharge, meandering above the gage and braided below — is the paper's own demonstration that slope, not discharge alone, flips the pattern.
- **strahler1957** `P` — Strahler, A.N. (1957). *Quantitative analysis of watershed geomorphology.* Transactions, American Geophysical Union 38(6), 913–920. doi:10.1029/TR038i006p00913. — The ordering scheme in the form everyone uses, credited by Strahler as "only slightly modified from Horton [1945, p. 281–282]": finger-tip tributaries are order 1, two channels of order *k* join to make order *k*+1. Restates Horton's law of stream numbers, fits it, and — the part that matters most to anyone thinking of exposing the bifurcation ratio as a slider — reports that the ratio is "highly stable and shows a small range of variation from region to region or environment to environment, except where powerful geologic controls dominate."
- **candel2021** `P` — Candel, J., Kleinhans, M., Makaske, B. & Wallinga, J. *Predicting river channel pattern based on stream power, bed material and bank strength.* Progress in Physical Geography, doi:10.1177/0309133320948831. Open access (CC-BY); the online-first version read here is stamped © The Author(s) 2020 and paginated 1–26, so the volume, issue and final page range are not asserted, though the paper is generally cited as 2021. — Puts eight published channel-pattern discriminators on one dataset and scores them. Restates the Leopold–Wolman line, the Van den Berg (1995) and Makaske et al. (2009) potential-specific-stream-power discriminators, and the Crosato–Mosselman bar-mode equation, then reports the fraction each classifies correctly and a κ statistic. This is the source for the honest answer to "does the braiding threshold work?", and for the two facts an authoring tool most needs: that anastomosing/laterally stable reaches sit an order of magnitude *below* the braiding threshold in stream power, and that a thread count is predictable from bar mode.
- **genevaux2013** `P` — Génevaux, J.-D., Galin, E., Guérin, E., Peytavie, A. & Beneš, B. (2013). *Terrain generation using procedural models based on hydrology.* ACM Transactions on Graphics 32(4), art. 143. doi:10.1145/2461912.2461996. — The paper that inverts the pipeline: build the river network first as a geometric graph, then construct the terrain around it. A grammar grows the network under Horton–Strahler rules with user-controlled continuation, symmetric-branch and asymmetric-branch probabilities; Voronoi cells of the river nodes become watersheds and their shared edges become ridges; a construction tree of compactly supported primitives with a *replace* operator carves the river into the blended terrain. Its river primitive is the whole carve operator in one line.
- **peytavie2019** `P` — Peytavie, A., Dupont, T., Guérin, E., Cortial, Y., Benes, B., Gain, J. & Galin, E. (2019). *Procedural riverscapes.* Computer Graphics Forum 38(7) (Pacific Graphics 2019); the page range is not on the author version read here and is not asserted. — The complement to `genevaux2013`: it takes an existing bare-earth heightfield, extracts the network from it, and then amplifies. Contributes the two things that document does not — a cross-section template normalised to unit area and scaled by discharge over velocity, and an explicit downstream-monotonicity check on the carved bed with the propagate-downstream fix. Its Rosgen-D handling is the only published account here of building a multi-thread channel as an authoring primitive.
- **paris2023** `P` — Paris, A., Guérin, E., Collon, P. & Galin, E. (2023). *Authoring and simulating meandering rivers.* ACM Transactions on Graphics 42(6), art. 241. doi:10.1145/3618350. — Meander migration as an authoring loop: a network of channel curves migrated by a curvature-driven rate with user control terms, with cutoffs and avulsions handled as topological edits to the network graph. Cited here for three specific things rather than for the migration model: the width law it actually implements, the junction-angle rule keyed to the flow ratio, and the fact that a migrating network needs explicit collision cases — which is what it costs to leave the tree.
- **braid_flow_split** `F` — No canonical source. — How to divide a reach's discharge among the threads of a braid. `peytavie2019` §5.2 says the parameters are "determined by partitioning the aggregate flow between channels" and prints no rule; nothing else opened here prints one either. [no-artefact]
- **subcell_channel** `F` — No canonical source. — The rule that a channel narrower than about two cells cannot be carved into a heightfield at all, and that below that width a river has to become a texture or a spline rather than geometry. Universal in practice, unpublished as such. [no-artefact]
