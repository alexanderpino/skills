---
type: Bibliography
title: Papers — stratigraphy and grain classes
description: "Sources behind Gaia's layered-erodibility document and the multi-grain sediment section, each graded by provenance tier."
tags: [bibliography, provenance, stratigraphy, lithology, sediment]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — stratigraphy and grain classes

The bibliography family for two subjects Gaia had opinions about before it had operators: rock
that varies with **depth** rather than only with position, and sediment that comes in more than
one **size**. **The tier table and the two non-negotiable rules live in `papers-flow.md`** and
are not repeated here; read them before citing anything below.

One tier decision recurs in this family and is stated once. **Reading an abstract is reading a
locator, and it is the only locator that entry may then carry.** Two entries here were reached
only through their abstracts because the full text is paywalled. They keep `P` — the venue is
peer-reviewed and the attributed claim is verifiably in the abstract — and their locator says
`Abstract` and nothing else. Inventing a section number for the part not read is the exact
failure `papers-flow.md` records against `bornwolf_optics`, and the abstract-only marker is
what stops this family from repeating it.

## Layered rock in landscape evolution

- **benes2001** `P` — Beneš, B. & Forsbach, R. (2001). *Layered Data Representation for Visual Simulation of Terrain Erosion.* Proceedings of the 17th Spring Conference on Computer Graphics (SCCG 2001), 80–86. doi:10.1109/SCCG.2001.945341. — The graphics origin of the per-column layer stack: the landscape as a 2D array of 1D arrays, each entry a layer of one material with its own properties, and thermal erosion run over it. Read in full. Its own demonstration is the differential-erosion one — a hard letter buried under weak mud, which survives being exhumed — and its cost argument (`k·n²`, not `n³`) is why the structure is affordable at all. It is a *representation* paper: the erosion law it carries is thermal, not fluvial, so it grounds the data structure and not the incision.
- **mitchell2021** `P` — Mitchell, N.A. & Yanites, B.J. (2021). *Bedrock river erosion through dipping layered rocks: quantifying erodibility through kinematic wave speed.* Earth Surface Dynamics 9, 723–753. doi:10.5194/esurf-9-723-2021. Open access, CC-BY; read in full. — 1-D stream-power models of rivers cutting layered stratigraphy, with contact dip as the control variable. Carries the two equations this skill needs: kinematic wave speed for horizontal contacts, and the dip-corrected form. ⚠️ It deliberately does **not** run `n = 1` (see its §2.4), so its own numbers are for `n = 0.67` and `n = 1.5`; the `n = 1` reduction quoted in `stratigraphy-and-lithology.md` is arithmetic on its eq. (6), not a result it reports.
- **forte2016** `P` — Forte, A.M., Yanites, B.J. & Whipple, K.X. (2016). *Complexities of landscape evolution during incision through layered stratigraphy with contrasts in rock strength.* Earth Surface Processes and Landforms 41(12), 1736–1757. doi:10.1002/esp.3947. — The landscape-evolution study that established which properties of a two-unit stratigraphy matter: the erodibility contrast, the **order** of the units, and the contact orientation and dip. ⚠️ **Abstract only.** The full text is behind Wiley; the LSU repository record carries metadata and no file. The locator says `Abstract` because that is what was read.
- **barnhart2018** `P` — Barnhart, K.R., Hutton, E., Gasparini, N.M. & Tucker, G.E. (2018). *Lithology: A Landlab submodule for spatially variable rock properties.* Journal of Open Source Software 3(30), 979. doi:10.21105/joss.00979. CC-BY; both pages read. — The shipped implementation of a depth-varying rock column under a landscape-evolution solver: a generic `Lithology` and a parallel-layer `LithoLayers`, each rock type carrying arbitrary attributes, layers removed by erosion and added by deposition. Its load-bearing contribution here is the **choice of two storage schemes** and what each costs. A two-page software paper, peer-reviewed by JOSS's open review as software — named as that, not dressed as a results paper; the claim taken from it is a description of its own data structures, which is the thing a software paper is authoritative about.
- **strat_authoring** `F` — No canonical source. The authoring recipe for a stratigraphic column in a terrain tool — an ordered thickness list, resistant and weak alternating, per-bed erodibility, jittered thicknesses from a seed, and the whole thing sampled as `K(x, y, z)` through a dip plane — is standard practice in landscape-evolution modelling and in every terrain tool that ships a stratification node, and no paper claims it. The published pieces are separable: `benes2001` grounds the layer stack, `mitchell2021` the dip term, `barnhart2018` the attribute lookup. The *recipe that composes them* is folklore. [no-artefact]

## Grain classes in sediment transport

- **parker1982** `P` — Parker, G. & Klingeman, P.C. (1982). *On why gravel bed streams are paved.* Water Resources Research 18(5), 1409–1423. doi:10.1029/WR018i005p01409. — Why a coarse surface layer forms over a finer subsurface, and the equal-mobility argument behind it: coarse grains are intrinsically less mobile, so the pavement must be what equalises mobility, by exposing proportionally more coarse grains to the flow. The prediction that pavement is absent in most sand-bed streams is the falsifiable half. ⚠️ **Abstract only** — AGU paywall; the locator says `Abstract`.
- **gaea_erosion2** `F` — Gaea 2.x documentation, the Erosion2 node. — The shipped multi-class formulation this skill describes: three sediment classes, **Suspended Load**, **Bed Load** and **Coarse Sediments**, ordered by increasing mass and decreasing mobility, each with its own *Discharge Amount* and its own *Discharge Angle*, the angle being the slope at or above which that class comes to rest. Tool documentation, cited as tool documentation: it evidences that the practice exists and what its controls are called, and it is not a derivation. No paper covers the heightfield form.
