---
type: Bibliography
title: Papers — flow, rivers, and the rules every bibliography follows
description: "Two jobs in one file: the sources for flow routing, depression handling and river networks as authored objects; and the shared apparatus every other bibliography points at — the provenance tier table, the [not-opened] rule, and the two non-negotiable rules that bind every entry in the corpus."
tags: [bibliography, provenance, flow, hydrology, rivers]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Papers — flow, rivers, and the rules every bibliography follows

⚠️ **This file used to be called `Papers` and described itself as "every source Gaia cites".**
That was true when it was the only bibliography. It now holds 18 of the corpus's 196 entries —
flow routing, depression handling, and river networks as authored objects — and the description
stayed behind, which mattered because `index.md` republished it verbatim as this file's row.

It does still carry one thing for everybody: **the shared apparatus**. The entry format, the
provenance tier table, the `[not-opened]` rule and the two non-negotiable rules live here and are
not repeated in the other six bibliographies, which point at this file instead. That is why it
must not be renamed or split.

Across all seven bibliographies the invariant holds: every claim in Gaia points at an entry in one
of them, and every entry is pointed at by some claim or marked `[background]`. `scripts/check.py`
enforces both directions; that is the whole of Gaia's grounding machinery.

## Entry format

```
- **id** `T` — Author (Year). *Title.* Venue. — note
```

`id` is what documents cite in their `sources:` and in the body as `[id]`. `T` is the
provenance tier.

## Provenance tiers

Carried over from `obsolete/terrain-architect/references/00-index.md`, because the failure they
prevent — confident fabrication of a citation — is the one Gaia is most exposed to.

| Tier | Meaning | How to write about it |
|---|---|---|
| **P** | **Paper.** Peer-reviewed, and verified to actually contain the algorithm attributed to it. If the artefact was never obtained here, the entry must carry `[not-opened]` — see below. | Cite it directly. |
| **F** | **Not peer-reviewed.** That is the whole criterion, and it is not the same as "no canonical source". Folklore qualifies — a thesis, a blog post, a repo, or nothing — but so does an artefact that is perfectly canonical and simply was not refereed: a standard, a vendor documentation page, a conference talk, a book, a set of course notes, a lab technical report. | Say "no canonical source; standard practice is…" where that is true. Where the source *is* canonical, name it plainly and say what it is; do not dress it as peer review. |
| **L** | **Landform, not algorithm.** An outcome, produced by composing other operators. | "There is no X algorithm. X emerges from A + B + C", then give the recipe. |
| **N** | **Node, not algorithm.** A tool's UI branding over an operator. | Name the underlying algorithm. |
| **?** | **Claimed but unverified.** Plausible, repeated, unconfirmed. | **Do not cite.** `check.py` rejects any document that does. Say it needs checking. |

Two rules, inherited verbatim and non-negotiable:

- **Never upgrade a tier to satisfy a question.** If the honest answer is `F`, an `F` answer
  is the good answer.
- **A constant reconstructed from memory is a `?` wearing a P's confidence.** If you cannot
  point at the equation, you do not have the constant.

### `[not-opened]`, the tag that stops `P` lying

⚠️ **A tier is a claim about the venue *and* about the reading, and those two came apart.**
`P` above says "verified to actually contain the algorithm attributed to it". Eighteen `P` entries
across this corpus's seven bibliographies could not honestly say that — one of them here, and
three `F` entries carry the tag for the same reason, twenty-one in all: the paper is peer-reviewed and behind a paywall,
and nobody here ever opened it. Meanwhile the documents citing them had started writing
`NOT OPENED —` into their locators. **One side of the citation said a human read it and the other
side said nobody did, and nothing could see the contradiction, because both sides were prose.**

⚠️ **The third case: the work was read, but in a different artefact.** `reda2004` cites a Solar
Energy article and was read in NREL's companion technical report; `wu2009` cites a Pattern Analysis
and Applications article and was read in the LBNL technical report that preceded it, under another
title. These are **not** `[not-opened]` — a source was obtained and every locator is verified
against it, so the tag would be false in the other direction and would forbid locators that were
actually checked. They stay `P`, and the entry must name the artefact that was read and say the
cited one was not. Whether a peer-reviewed paper read only through its own preprint deserves a
weaker grade is a real question this vocabulary does not answer; it is recorded here rather than
settled by whichever entry was written last.

So an entry whose artefact was never obtained carries an explicit tag, immediately after the tier
where a reader scanning grades cannot miss it:

```
- **beven1979** `P` [not-opened] — Beven, K.J. & Kirkby, M.J. (1979). *A physically based…*
```

`check.py` then ties the two halves together **in both directions**: an entry tagged
`[not-opened]` may not be cited with a locator that claims a reading, and a locator saying
`NOT OPENED` — or `NO LOCATOR`, the second marker the guard accepts and this paragraph used to
omit, in live use in `water-optics.md` — may not sit against an untagged entry. Enabling that check found three documents
citing a source as read that two other documents already described as unread.

**This is not a demotion and `[not-opened]` is not a failing grade.** A corpus that cannot cite a
paywalled paper is less useful, not more honest — `braun2013` is still the right citation for the
O(N) stack ordering. What the tag refuses is the *silent* version: a `P` that looks like every
other `P`, on a paper nobody has seen.

⚠️ **What a tier is not.** `P` asserts that *a human read the paper and found the algorithm in
it* — or, with `[not-opened]`, says openly that they did not. `check.py` cannot establish the
reading itself; it checks that the citation is well-formed, that it is used, and that both sides
agree about whether anyone read it. The `verified:` key in a document's front matter is where a
human records having done the reading; until it is there, the document stays `draft`.

⚠️ **A wrong locator is worse than a vague one, and the metric rewards the wrong direction.**
`check.py` reports how many locators name a section, equation or page, and that number is
meant to go up. But it counts *shape*, not correctness — so `§3` scores as sharp whether or
not the thing is in §3. A topic paraphrase advertises its own weakness and a reader who
follows it just searches the paper. A **wrong section number reads as more verified than
either**, sends the reader to the wrong page, and when they find nothing there the natural
conclusion is that they misread the claim, not that the citation is wrong.

This is not hypothetical. `water-optics.md` cited Bruneton's roughness-aware mean-Fresnel fit
to **§3**, which is "Our ocean model"; the fit is **eq. 26 in §5.2**. It had been sharp, and
wrong, and it looked better than the paraphrase it replaced.

So: **sharpen a locator only from the source in front of you.** If the paper is unreachable,
leave the paraphrase and say so — that is a correct outcome, not a failure to hit a number.
The one thing never to do is transplant a section number from a different edition, a
reproduction, or another document's entry. ⚠️ This paragraph used to claim the corpus already
carries such a locator, "recorded as outstanding rather than trusted". It does not, and the row
it was pointing at says the opposite: `source-findings.tsv` row 17 records that Zevenbergen &
Thorne's equation numbering **could not be verified and the locator was deliberately left as a
paraphrase**, because "writing 'eq. 15' from memory would be a `?` wearing a P's confidence". That
is the rule working, and the register's one OPEN row is a success story, not the violation this
paragraph was using it as.

## Attribution corrections

These errors circulate widely in terrain-generation reference tables, including in tables
generated by language models. They are listed first because they are the ones that send an
implementer to the wrong paper.

| Common claim | Reality |
|---|---|
| "Hydraulic (particle) — Mei et al. 2007" | **Mei et al. 2007 is a grid/pipe model**, not particle. It is the canonical virtual-pipe paper. |
| "Hydraulic (grid/pipe) — Šťava et al. 2008" | **Šťava et al. 2008 is also a pipe model** — an extension of Mei adding sediment slippage and layers. Mei and Šťava are one family, not two. |
| "Droplet erosion has a canonical paper" | It does not. It descends from **Musgrave et al. 1989** and reaches modern form in **Beyer's 2015 TU München thesis**. Tier `F`, not `P`. |
| "Tectonic plates — Cordonnier 2015" | The paper is **Cordonnier et al. 2016**, and it is the *same paper* as the stream-power citation. There is no separate 2015 tectonics paper. |
| "Stream power — Cordonnier et al. 2016" | Correct but incomplete: the O(N) implicit solver that makes stream power tractable is **Braun & Willett 2013**. Cite only Cordonnier and the implementer misses the solver. |
| "MFD — Quinn or Freeman, interchangeably" | Two different methods. **Freeman 1991** calibrates the exponent `p = 1.1`; **Quinn et al. 1991** uses `p = 1` with contour-length weighting. Conflating them changes the drainage pattern. |

## Flow routing

- **ocallaghan1984** `P` — O'Callaghan, J.F. & Mark, D.M. (1984). *The extraction of drainage networks from digital elevation data.* Computer Vision, Graphics and Image Processing 28(3), 323–344. — D8.
- **freeman1991** `P` — Freeman, T.G. (1991). *Calculating catchment area with divergent flow based on a regular grid.* Computers & Geosciences 17(3), 413–422. — MFD with the calibrated exponent p = 1.1.
- **quinn1991** `P` — Quinn, P., Beven, K., Chevallier, P. & Planchon, O. (1991). *The prediction of hillslope flow paths for distributed hydrological modelling using digital terrain models.* Hydrological Processes 5(1), 59–79. — The sibling MFD variant, p = 1 with contour-length weighting. Not the same method as Freeman.
- **tarboton1997** `P` — Tarboton, D.G. (1997). *A new method for the determination of flow directions and upslope areas in grid digital elevation models.* Water Resources Research 33(2), 309–319. — D∞, the 8-facet construction.
- **barnes2014** `P` — Barnes, R., Lehman, C. & Mulla, D. (2014). *Priority-Flood: an optimal depression-filling and watershed-labeling algorithm for digital elevation models.* Computers & Geosciences 62, 117–127. — Depression filling, including the epsilon variant that preserves a gradient across filled basins.
- **lindsay2016** `P` — Lindsay, J.B. (2016). *Efficient hybrid breaching-filling sink removal methods for flow path enforcement in digital elevation models.* Hydrological Processes 30(6), 846–857. — Breaching, and the hybrid breach/fill policy.
- **planchon2002** `P` — Planchon, O. & Darboux, F. (2002). *A fast, simple and versatile algorithm to fill the depressions of digital elevation models.* Catena 46(2–3), 159–176. — The other standard fill.
- **montgomery1992** `P` — Montgomery, D.R. & Dietrich, W.E. (1992). *Channel initiation and the problem of landscape scale.* Science 255(5046), 826–830. — The channel-head threshold in **A·S²**, contributing area against the SQUARE of local slope: where hillslope becomes channel. Eqs. (3) and (4) print `AS² = 4000 m²` and `AS² = 500 m²` as the upper and lower bounds on channel-head location. ⚠️ This entry previously said "area × slope", the unsquared product that `flow-routing.md` explicitly warns against — the bibliography stated the form its own consumer tells you not to use.
- **braun2013** `P` [not-opened] — Braun, J. & Willett, S.D. (2013). *A very efficient O(n), implicit and parallel method to solve the stream power equation governing fluvial incision and landscape evolution.* Geomorphology 180–181, 170–179. — The O(N) implicit solver. ⚠️ **Not obtained** — paywalled at Elsevier, no open copy reachable, so no locator into it is verified anywhere here. The scheme itself was verified second-hand in `cordonnier2016` **§5 eq. 2**, which restates the implicit update and the root-to-leaves ordering. ⚠️ **This entry used to add that §5 attributes both to Braun & Willett. It does not — §5 credits nobody.** The attribution sits in §1, "The original method from [BW13] is extended to efficiently model water flowing from lakes", and in §4; `stream-power.md` carries the checked retraction. §5 remains the right locator for the scheme and eq. 2 themselves, and an intermediate revision here wrongly deleted it along with the false attribution clause. [background]

### River networks

Every `P` in that section was opened and the cited pages read.

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
**`paris2023`** — the accepted version deposited at HAL (hal-04227965); §3.1, §4 and §6 read
there. ⚠️ §3.1 was missing from this list while carrying all three things the paper is cited
for, and every locator into it said §4. §4 is the migration model, which is not what Gaia
cites this paper for.
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

## River networks as authored objects


- **leopold1953** `P` — Leopold, L.B. & Maddock, T., Jr. (1953). *The hydraulic geometry of stream channels and some physiographic implications.* U.S. Geological Survey Professional Paper 252. — The origin of hydraulic geometry: width, mean depth and mean velocity each a power function of discharge, `w = aQ^b`, `d = cQ^f`, `v = kQ^m`, with `b + f + m = 1` forced by `Q = wdv`. Two distinct exponent triples, and the distinction is the load-bearing part: *at a station*, watching one cross section through a flood, and *downstream*, comparing sections at constant discharge frequency. The paper is equally explicit that the **coefficients** `a`, `c`, `k` are not universal — "Width and depth for a given discharge vary widely from one cross section to another" (p. 9) — so it publishes an exponent, not a width.
- **leopoldwolman1957** `P` — Leopold, L.B. & Wolman, M.G. (1957). *River channel patterns: braided, meandering and straight.* U.S. Geological Survey Professional Paper 282-B (Physiographic and hydraulic studies of rivers), from p. 39; the contents run to appendix H at p. 81 and the end page is not asserted. — The planform paper. Defines a braid as a reach with "relatively stable alluvial islands, and hence two or more separate channels" and a meander as sinuosity ≥ 1.5, calls the latter arbitrary, and then draws the one line every later channel-pattern paper argues with: a slope–discharge threshold separating braided from meandering reaches. Also fits meander wavelength against bankfull width, and reports the observed wavelength-to-width ratio drifting from ~7 at small widths to ~15 at large ones. The Cottonwood Creek reach — the same discharge, meandering above the gage and braided below — is the paper's own demonstration that slope, not discharge alone, flips the pattern.
- **strahler1957** `P` — Strahler, A.N. (1957). *Quantitative analysis of watershed geomorphology.* Transactions, American Geophysical Union 38(6), 913–920. doi:10.1029/TR038i006p00913. — The ordering scheme in the form everyone uses, credited by Strahler as "only slightly modified from Horton [1945, p. 281–282]": finger-tip tributaries are order 1, two channels of order *k* join to make order *k*+1. Restates Horton's law of stream numbers, fits it, and — the part that matters most to anyone thinking of exposing the bifurcation ratio as a slider — reports that the ratio is "highly stable and shows a small range of variation from region to region or environment to environment, except where powerful geologic controls dominate."
- **candel2021** `P` — Candel, J., Kleinhans, M., Makaske, B. & Wallinga, J. *Predicting river channel pattern based on stream power, bed material and bank strength.* Progress in Physical Geography, doi:10.1177/0309133320948831. Open access (CC-BY); the online-first version read here is stamped © The Author(s) 2020 and paginated 1–26, so the volume, issue and final page range are not asserted, though the paper is generally cited as 2021. — Puts eight published channel-pattern discriminators on one dataset and scores them. Restates the Leopold–Wolman line, the Van den Berg (1995) and Makaske et al. (2009) potential-specific-stream-power discriminators, and the Crosato–Mosselman bar-mode equation, then reports the fraction each classifies correctly and a κ statistic. This is the source for the honest answer to "does the braiding threshold work?", and for the two facts an authoring tool most needs: that anastomosing/laterally stable reaches sit an order of magnitude *below* the braiding threshold in stream power, and that a thread count is predictable from bar mode.
- **genevaux2013** `P` — Génevaux, J.-D., Galin, E., Guérin, E., Peytavie, A. & Beneš, B. (2013). *Terrain generation using procedural models based on hydrology.* ACM Transactions on Graphics 32(4), art. 143. doi:10.1145/2461912.2461996. — The paper that inverts the pipeline: build the river network first as a geometric graph, then construct the terrain around it. A grammar grows the network under Horton–Strahler rules with user-controlled continuation, symmetric-branch and asymmetric-branch probabilities; Voronoi cells of the river nodes become watersheds and their shared edges become ridges; a construction tree of compactly supported primitives with a *replace* operator carves the river into the blended terrain. Its river primitive is the whole carve operator in one line.
- **peytavie2019** `P` — Peytavie, A., Dupont, T., Guérin, E., Cortial, Y., Benes, B., Gain, J. & Galin, E. (2019). *Procedural riverscapes.* Computer Graphics Forum 38(7) (Pacific Graphics 2019); the page range is not on the author version read here and is not asserted. — The complement to `genevaux2013`: it takes an existing bare-earth heightfield, extracts the network from it, and then amplifies. Contributes the two things that document does not — a cross-section template normalised to unit area and scaled by discharge over velocity, and an explicit downstream-monotonicity check on the carved bed with the propagate-downstream fix. Its Rosgen-D handling is the only published account here of building a multi-thread channel as an authoring primitive.
- **paris2023** `P` — Paris, A., Guérin, E., Collon, P. & Galin, E. (2023). *Authoring and simulating meandering rivers.* ACM Transactions on Graphics 42(6), art. 241. doi:10.1145/3618350. — Meander migration as an authoring loop: a network of channel curves migrated by a curvature-driven rate with user control terms, with cutoffs and avulsions handled as topological edits to the network graph. Cited here for three specific things rather than for the migration model — and all three are in **§3.1 River network and channel models**, not §4: the width law it actually implements, the junction-angle rule keyed to the flow ratio, and the fact that a migrating network needs explicit collision cases — which is what it costs to leave the tree.
- **braid_flow_split** `F` — No canonical source. — How to divide a reach's discharge among the threads of a braid. `peytavie2019` §5.2 says the parameters are "determined by partitioning the aggregate flow between channels" and prints no rule; nothing else opened here prints one either. [no-artefact]
- **subcell_channel** `F` — No canonical source. — The rule that a channel narrower than about two cells cannot be carved into a heightfield at all, and that below that width a river has to become a texture or a spline rather than geometry. Universal in practice, unpublished as such. [no-artefact]
