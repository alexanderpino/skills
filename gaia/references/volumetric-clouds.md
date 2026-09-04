---
type: Technique
title: Volumetric clouds
description: "The cloud deck a mountain can pierce: an analytic Perlin-Worley density model marched with a cheap/expensive two-level sampler, the three couplings that make this terrain's problem rather than general sky rendering -- depth compositing against the terrain buffer, a projected shadow the ground receives, and the above-the-deck regime -- and the honest asymmetry that every cost figure here comes from an unrefereed source and every error figure from a refereed one."
tags: [rendering, clouds, volumetrics, sky, weather]
status: draft
generated: { by: process:claude-code, at: 2026-09-04T00:00:00Z }
sources:
  - { id: schneidervos2015, tier: F, locator: "READ IN FULL, all 99 PDF slide-pages of the released deck. pp.31-35 for Perlin-Worley and the exact texture budget (128^3 RGBA, 32^3 RGB, 128^2 RGB curl, '20 mb of ram'); pp.36-39 for the coverage/type/erosion pipeline; p.42 for the 2015 weather-texture channel assignment 'Red is coverage, Green is precipitation and blue is cloud type'; pp.79-80 for the cheap/expensive two-level march verbatim, 'we only need to do the high detail noise and all of its associated instructions where the low detail sample returns a non zero result'; p.83 for 64 samples rising to a potential 128 at the horizon; p.85 for the 6-sample sun cone; pp.93-95 for the performance rescue, 'around 20 milliseconds ... not fast enough to be included in our game' against '10x faster or more'. A SIGGRAPH COURSE talk -- invited instructors, no referee report -- exported from PowerPoint with speaker notes. The most influential real-time cloud document in existence and still F: being standard-setting is not review. NOTE the deck contradicts itself on the upsample factor, quarter-res 1-in-16 of a 4x4 block (p.94) against 'render this at half res' (p.95); both are quoted here rather than reconciled. Page numbers are PDF slide-pages and run one to two ahead of the deck's own printed numbers" }
  - { id: schneidervos2017, tier: F, locator: "READ IN FULL, 108 pages. pp.34-41 for the restated density model with the three remap formulae; p.98 for the depth-culling datum, 1.81 ms to 1.2 ms on PS4, using a conservative max() over a low-LOD depth mip because reprojection needs NEXT-frame visibility; pp.97-98 for the full 22 ms to 1.2 ms optimisation ladder; p.96 verbatim for reprojection as a precondition rather than an optimisation, 'The reason we are able to render our cloudscapes in 2ms is re-projection'; p.101 for cloud depth defined as the depth at which alpha reaches 0.5. A SIGGRAPH course talk, not peer review. NOTE its 22 ms baseline is POST-reprojection and schneidervos2015's 20 ms is PRE-reprojection: the two must not be stacked or read as a regression" }
  - { id: schneider2023, tier: F, locator: "READ IN FULL, 220 pages. p.3 for the 2011 offline baseline, '10 minutes to 4 hours on one core for a single 1920x1080 frame'; p.8 for the 2014 failure to fit voxels on a PS4; p.9 for the term '2.5D clouds' and its definition, 'not stored as 3D voxel data but rather as 2D texture data'; p.51 for temporal upscaling amortising over 16 frames and for its RETIREMENT near camera; p.81 for the 2048x2048x256 voxel grid at 2.146 GB uncompressed; p.170 for 0.541 Mb per cloudscape under the Vertical Profile Method; pp.176-185 for the voxel costs, 2.2-4 ms at 960x540 on PS5, and the 200 m depth split at 480x270 near and 960x540 far, 'Saves around 50%'; pp.177-179 for the geometry-against-cloud budget handoff; p.198 for the seven-axis capability table in which Vertical Profile -- the 2015/2017 method -- scores No on Terrain-Cast Shadows, Flight-Capable and Freeform Modeling, and for the verdict 'Voxel clouds check almost all of the boxes'. A SIGGRAPH course talk, not peer review. WARNING its own reference list at p.219 labels course talks as 'ACM SIGGRAPH' and a 2018 talk as 'Eurographics'; a citation copied from that slide will read as refereed and is not" }
  - { id: schneider2022, tier: F, locator: "READ IN FULL, 207 pages, in the videos-stripped PDF, which carries NO speaker notes -- so only on-slide text is quotable from it. p.91 for the early-out in HLSL, three texture reads, one multiply, return 0.0; p.112 for SampleLongDistanceShadowMap() multiplied into direct scattering; pp.183-184 for the console-generation scaling, PS4 960x540 with 6 light samples at 4 ms or under against PS5 1920x1080 with 10 light samples at 2-3 ms or under. A SIGGRAPH course talk, not peer review" }
  - { id: hillaire2016, tier: F, locator: "READ IN FULL, 62 pages of WRITTEN course notes rather than a slide deck, which is why it is quotable at a finer grain than the Guerrilla artefacts. pp.33-34 for an independent second lineage reaching the same density model, and for its one reported deviation -- single-channel noise, which 'made cloud a lot faster to render ... still giving the same final visual result'; p.36 for 4 sun samples against Guerrilla's 5 to 6; Eq. 21 p.43 for cloud depth as a TRANSMITTANCE-WEIGHTED MEAN FRONT DEPTH skipping samples where transmittance is 1; p.42 for the ground-receiving cloud shadow, 'baked into a 2D texture storing transmittance and projected onto the world ... applied on all opaque, transparent surfaces', with the flat-planet assumption declared and the term also feeding GI; p.45 for 0.91 ms at 720p on Xbox One. SIGGRAPH course NOTES, not peer review" }
  - { id: bouthors2008, tier: P, locator: "READ IN FULL in the authors' submitted version deposited at HAL, which is paginated 1-10 rather than 173-182 -- so sections are cited here and journal pages are not. The Monte-Carlo reference tabulated to 5% accuracy at the 95% confidence level, which is the error anchor for a multiple-scattering claim; 2-10 fps at 800x600 on an 8800 GTS; its verdict on the phase function every real-time implementation still ships -- Henyey-Greenstein phase functions 'give far from accurate visual effects'; and p.7 for the transport function allowing 'us to easily account for points of view inside the clouds'. I3D 2008, refereed" }
  - { id: yusov2014, tier: P, locator: "READ IN FULL. THE REFEREED SOURCE FOR BOTH TERRAIN COUPLINGS, which matters because the famous Guerrilla artefacts contain neither. Sections 5.4 and 5.6, pp.132-133, for a screen-space 'closest distance to cloud' buffer compared against the marched distance -- depth-aware compositing with a referee behind it; p.133 for a light-space cloud transparency buffer that SHARES THE CASCADED-SHADOW-MAP MATRICES, which is the ground-receiving cloud shadow; 5.6-15.4 ms at 1080p on a GTX 680. HPG 2014, refereed" }
  - { id: kallweit2017, tier: P, locator: "READ IN FULL. THE ERROR ANCHOR: RMSE against a path-traced reference, tabulated per method, with the reference itself stated as 34 hours to converge -- the only artefact in this document's source set that measures cloud shading against ground truth rather than against taste. Also the equal-time variance comparison per phase function, Henyey-Greenstein 698 against Lorenz-Mie 23136, which is what makes bouthors2008's verdict on HG quantitative. ACM TOG 36 (SIGGRAPH Asia 2017), Art. 231, refereed. NOTE the volume number differs between the paper's own front matter (36,4) and the ACM DL record (36,6); the article number is the stable handle" }
  - { id: hillaire2020, tier: P, locator: "Cited here ONLY for the ground-to-space transition and for being the single artefact in this set that states an error and a cost for the SAME configuration -- RMSE (0.94-6.07)e-3 at 0.31 ms, 1280x720, GTX 1080 -- which is the standard the cloud literature does not meet. Section 5.3 for the sky-view LUT losing accuracy once the camera leaves the ground and the switch to on-screen ray marching, which is the atmosphere half of the above-the-deck problem. The atmosphere itself is atmosphere-and-aerial-perspective.md's subject, not this document's. EGSR 2020 / CGF 39(4), refereed" }
  - { id: yang2020, tier: P, locator: "p.10 for the named failure modes of temporal reprojection, verbatim that 'transparency, particles and reflection ... are known challenging cases for TAA to handle' -- which is the refereed reason behind schneider2023's retirement of temporal upscaling for near-camera clouds, a decision that artefact states without explaining. CGF 39(2), Eurographics STAR, refereed" }
  - { id: olajos2026, tier: P, locator: "NOT OPENED -- ACM DL returned 403 on three attempts, the DiVA deposit reset the connection and the LUP mirror returned 500, and Unpaywall and Semantic Scholar both resolve back to the blocked DOI. Named here for DIRECTION ONLY, that the refereed frontier is proposing to drop ray marching entirely in favour of rasterised neural cloud assets. No parameter, cost or error from it is used anywhere in this document, because none was read. PACMCGIT 9(4) 2026, refereed and CC-BY per the record" }
---
# Volumetric clouds

## Use this

**Model density analytically and spend the saved memory on instructions; then buy the frame back
temporally, not by simplifying the model** [schneidervos2015] [hillaire2016]. A Perlin–Worley base
eroded by higher-frequency Worley, driven by a coverage/type/precipitation weather texture, marched
with a cheap sampler that only escalates to the expensive one where the cheap sample is non-zero.

⚠️ **The density model is the durable part; the 2015 rendering envelope around it is not.** Its own
originator's 2023 capability table scores that method **No** on terrain-cast shadows, **No** on
flight-capability and **No** on freeform modelling, and their verdict on the voxel successor is
"**Voxel clouds check almost all of the boxes**" [schneider2023]. Two of those three failures are
exactly terrain's problems. Take the density model from the 2015 lineage; do **not** take the
couplings from it, because they are not in it.

**What it costs.** Every figure below is from an unrefereed source, because that is where cost
figures exist — see *What error you are accepting*.

| Configuration | Cost | Hardware, as stated |
|---|---|---|
| Full-res march, no reprojection | ~20 ms | PS4, 2015 [schneidervos2015] |
| After temporal amortisation over 16 frames | ~2 ms | PS4, 2015 [schneidervos2015] |
| Optimisation ladder, post-reprojection baseline → final | 22 ms → 1.2 ms | PS4, 2017 [schneidervos2017] |
| — of which depth culling against scene geometry alone | 1.81 ms → 1.2 ms | PS4, 2017 [schneidervos2017] |
| Second lineage, independent implementation | 0.91 ms @ 720p | Xbox One, 2016 [hillaire2016] |
| Console generation shift | 960×540, 6 light samples, ≤4 ms → 1920×1080, 10, ≤2–3 ms | PS4 → PS5 [schneider2022] |
| Voxel successor | 2.2–4 ms @ 960×540 | PS5, 2023 [schneider2023] |
| Refereed implementation | 5.6–15.4 ms @ 1080p | GTX 680, 2014 [yusov2014] |

⚠️ **Do not stack these numbers or read them as a series.** The 20 ms is *pre*-reprojection and the
22 ms is *post*-reprojection — same studio, same console, one year apart, measuring different
things. A reader who lines them up sees a regression that did not happen.

## The crossover has a date and a direction, and the direction reverses

Clouds crossed from offline to real-time **between 2012 and 2015**, and what moved them was not the
density model. It was **evaluating noise instead of storing it**, and **amortising the march over
frames**. The second is load-bearing on its own: [schneidervos2017] p.96 states it as a
precondition, "*the reason we are able to render our cloudscapes in 2ms is re-projection*".

| Date | What changed | Source |
|---|---|---|
| 2011 | Offline voxel clouds in feature animation: "10 minutes to 4 hours on one core for a single 1920×1080 frame" | [schneider2023] p.3 |
| 2014 | Guerrilla try the offline method directly; it does not fit on a PS4 and is shelved | [schneider2023] p.8 |
| 2015 | The crossing. Analytic Perlin–Worley replaces stored volumes; reprojection turns 20 ms into 2 ms | [schneidervos2015] pp.31–39, 93–95 |
| 2016 | An independent second lineage reaches the same model and adds the terrain couplings | [hillaire2016] pp.33–45 |
| 2017 | The optimisation ladder is published: 22 ms → 1.2 ms | [schneidervos2017] pp.97–98 |
| 2017 | Offline sets the yardstick the other way: a converged path-traced cloud is 34 hours | [kallweit2017] |
| 2020 | Ground-to-space becomes tractable, with an error and a cost stated together | [hillaire2020] |
| 2023 | **The direction reverses.** Voxels return — the 2011 representation, now affordable | [schneider2023] pp.51, 176–185 |

**The reversal is the part a terrain engine must not miss.** The field went offline voxels (2011) →
procedural 2.5D *because voxels did not fit on a PS4* (2015–2022) → **back to voxels on a PS5**
(2023). [schneider2023] p.9 names the middle era itself: "2.5D clouds … **not stored as 3D voxel
data but rather as 2D texture data**". The memory arithmetic is the whole story — 2015's entire sky
system was "20 mb of ram" [schneidervos2015], against a 2048×2048×256 voxel grid at **2.146 GB
uncompressed** [schneider2023] p.81. **The famous Perlin–Worley model is an artefact of a memory
constraint that has since relaxed**, not the natural endpoint of the lineage. Presenting it as the
endpoint would be misreading the sources it comes from.

## The density model

Three textures and a weather field, all 2015 figures [schneidervos2015] pp.33–35, 42:

- **128³ RGBA** — channel 0 Perlin–Worley, channels 1–3 Worley at rising frequencies. The base shape.
- **32³ RGB** — Worley at rising frequencies. The erosion applied at cloud edges.
- **128² RGB** — curl noise, non-divergent, to fake fluid motion.
- **A 2D weather texture** — in 2015, "*Red is coverage, Green is precipitation and blue is cloud
  type*". **Cite the year**: by 2017 R and G are both coverage (Perlin and Perlin–Worley), and the
  sample counts and noise layout moved again in 2022 [schneidervos2017] [schneider2022].

Perlin–Worley itself is inverted Worley layered fBm-style and used *as an offset to dilate Perlin*,
which keeps Perlin's connectedness while adding billow. [hillaire2016] p.34 reaches the same model
independently and reports one deviation worth having: **single-channel noise**, which "*made cloud a
lot faster to render … still giving the same final visual result*". That is a second implementation
agreeing with the first, which is the strongest evidence available here — none of it refereed.

## The march

Two-level sampling is the optimisation that makes the rest affordable [schneidervos2015] pp.79–80:
cheap samples at a large step until the low-detail sample returns non-zero, then step **backward**
one and switch to full samples with the high-detail noise. The backward step is not decoration; it
is what stops the escalation missing the iso-surface it just crossed.

- **View ray:** 64 samples rising to a potential 128 at the horizon (2015) → 54–96 (2017) →
  60–90 on PS4 and 96–180 on PS5 (2022). "Potential", because early-out dominates.
- **Sun cone:** 6 samples (2015), 5 (2017), 6 on PS4 and 10 on PS5 (2022), **4** in Frostbite
  [hillaire2016] p.36. The last sample is placed far from the rest to catch distant-cloud shadowing.
- **The early-out** is three texture reads, one multiply, `return 0.0` [schneider2022] p.91.

## The three couplings terrain owns

This is where a terrain engine's needs diverge from general sky rendering, and where the most-cited
artefacts are silent. ⚠️ **[schneidervos2015] and [schneidervos2017] contain no depth compositing
against terrain and no ground-receiving cloud shadow.** The word "shadow" does not appear in the
2017 text layer at all, and appears twice in 2015, both times about *intra*-cloud shadowing. This is
confirmed by the originator's own scorecard: Terrain-Cast Shadows, **No** [schneider2023] p.198.
**Take these three from [yusov2014] and [hillaire2016], not from the famous decks.**

**1 — Depth compositing, or summits get cloud drawn over them.** The march must terminate at the
nearer of cloud exit and terrain hit. Three formulations of "what depth does a cloud have", in
descending order of provenance:

| Definition | Source | Tier |
|---|---|---|
| Screen-space "closest distance to cloud" buffer, compared against the marched distance | [yusov2014] §5.4, §5.6 | `P` |
| Transmittance-weighted mean front depth, skipping samples where transmittance is 1 | [hillaire2016] Eq. 21, p.43 | `F`, but a written equation |
| The depth at which alpha reaches 0.5 | [schneidervos2017] p.101 | `F` |

It is also the single largest optimisation in the ladder: depth culling against scene geometry is
**1.81 ms → 1.2 ms** on PS4 — a third of the remaining cost — by reducing a low-LOD depth mip
**conservatively toward the FARTHEST depth in the footprint**, because reprojection needs
*next*-frame visibility, not this frame's [schneidervos2017] p.98.

⚠️ **Write the quantity, not the operator, because the operator flips with the depth convention —
and an earlier version of this line got it backwards for this corpus.** Farthest-in-footprint is
`max()` under standard depth (near = 0), which is the convention [schneidervos2017] was written in,
and **`min()` under reversed-Z**, which is what `planetary-precision.md` mandates and what you are
almost certainly running. Transcribing the source's `max()` unchanged selects the *nearest* depth,
terminates the march early, and produces exactly the popping this optimisation exists to avoid —
`gpu-driven-culling.md` states the same rule for its HiZ reduce and names the same symptom,
"geometry near silhouettes disappears for a frame under motion".

**2 — The shadow the ground receives.** The cheapest large-scale life a vista buys, and absent from
the 2015/2017 lineage entirely.

- **[yusov2014] p.133** — a light-space cloud transparency buffer **sharing the cascaded-shadow-map
  matrices**. Refereed, and it costs almost nothing extra because the matrices already exist.
- **[hillaire2016] p.42** — "*baked into a 2D texture storing transmittance and projected onto the
  world … applied on all opaque, transparent surfaces*", and feeding GI. ⚠️ It declares a
  **flat-planet assumption**, which is exactly the assumption a large terrain breaks.
- **[schneider2022] p.112** — `SampleLongDistanceShadowMap()` multiplied into direct scattering.

**3 — Above the deck, which terrain uniquely forces.** A summit view puts the camera *in* or *over*
the cloud layer, and the 2015 model assumes it is under one: "*we will be drawing clouds per the
standard approach **in a zone above the camera***" [schneidervos2015] p.37. Its scorecard says
Flight-Capable **No** [schneider2023] p.198. What exists: [hillaire2020] §5.3 covers ground → space
for the **atmosphere**, switching away from the sky-view LUT once the camera leaves the ground;
[schneider2023] covers flying *through* clouds at 4 ms, 960×540, PS5; [bouthors2008] p.7 notes its
transport function "*allows us to easily account for points of view inside the clouds*".

⚠️ **The gap is real and is not closed here: no artefact in this set gives a cloud-top or orbital
view of a cloud *deck* with a stated error and a stated cost.** If you need that regime, you are
past the published envelope and should measure your own.

## What error you are accepting

**The three Guerrilla artefacts and the Frostbite notes contain, between them, roughly thirty
performance numbers and zero error figures against any reference solution.** The only comparative
language in the entire production corpus is perceptual: "*a pretty good approximation of our
reference*" [schneidervos2015] p.66; "*there's no apparent difference in the clouds with each
optimization*" [schneidervos2017] p.97; "*a bit more pixelation on sharp and dense features*"
[schneider2023] p.184.

⚠️ **So the cost comes from an `F` source and the error must come from a `P` one, and the two are
almost never measuring the same system.** State this when you quote a number; do not pair an RMSE
from one paper with a frame time from another and call it a measurement. What the refereed sources
give:

- **[kallweit2017]** — RMSE against a path-traced reference that took **34 hours** to converge. It
  also prices the phase function everyone ships: equal-time variance **698** for Henyey–Greenstein
  against **23136** for Lorenz–Mie.
- **[bouthors2008]** — a Monte-Carlo reference tabulated to **5% at the 95% confidence level**, and
  the verdict that Henyey–Greenstein phase functions "*give far from accurate visual effects*". Note that
  [schneidervos2015] p.64 concedes its own "powder" term is not in the refereed literature at all —
  the author says he looked for it in the ACM Digital Library and did not find it.
- **[hillaire2020]** — the only artefact here stating both halves for one configuration: RMSE
  (0.94–6.07)·10⁻³ **at 0.31 ms, 1280×720, GTX 1080**. It is about the atmosphere, not the cloud
  deck. That is the standard; the cloud literature does not meet it.

## Reprojection, and why it was retired near the camera

Temporal amortisation is what made this shippable, and it is also the part that aged worst.
[schneidervos2015] updates **1 pixel of each 4×4 block** from a quarter-res buffer, reprojecting the
previous frame. ⚠️ **The deck contradicts itself on the factor** — p.94 says quarter-res 1-in-16,
p.95 says "*render this at half res*". Both are quoted here because reconciling them silently would
invent a number neither slide states.

By 2023 it was **retired for near clouds**: temporal upscaling "*worked for distant clouds but not
for nearby clouds because the image would not be able to resolve in time when the camera moves
quickly*", and the Envelope method "*did away with temporal upscaling*" in favour of a **200 m depth
split — 480×270 near, 960×540 far — which "saves around 50%"** [schneider2023] pp.51, 182, 185. The
refereed reason sits in [yang2020] p.10: "*transparency, particles and reflection … are known
challenging cases for TAA to handle*". A camera that turns fast — which is every terrain flythrough
— is the case the scheme was weakest at from the start.

**Budget against geometry, not in isolation.** [schneider2023] pp.177–179 gives 7/5/4 ms of geometry
against 2.2/4.0/4.0 ms of cloud at 960×540 on PS5: **anti-correlated, competing for the same
pixels**. A cloud budget quoted without the geometry it displaces is half a number.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Cloud drawn over a mountain the first time a peak enters the deck | The march does not terminate at the terrain depth hit | Depth-aware compositing; pick one of the three depth definitions and use it everywhere [yusov2014] |
| Clouds pop at silhouettes as the camera turns | The depth-mip reduce picks the NEAREST depth in the footprint, so the march terminates early — the operator that does this flips with the depth convention | Reduce toward the FARTHEST depth: `min()` under reversed-Z, `max()` under standard depth. Write the quantity, not the operator [schneidervos2017] p.98 |
| Landscape looks dead and evenly lit under a dramatic sky | No ground-receiving cloud shadow — it is absent from the 2015/2017 lineage, so an implementation faithful to those decks has none | Light-space transparency buffer on the CSM matrices [yusov2014] p.133 |
| Cloud shadows drift wrong across a large map | The projected-shadow formulation assumes a flat planet | Declare the assumption and bound the map size, or project on the sphere [hillaire2016] p.42 |
| Ghosting and smearing on fast camera turns, worst near camera | Temporal amortisation over 16 frames cannot resolve in time | Depth-split the render instead of upscaling near clouds [schneider2023] p.185 |
| Sky is fine at ground level, wrong from a summit | The 2015 model draws clouds "in a zone above the camera" | Past the published envelope above the deck; measure it yourself |
| A cost budget that holds in isolation and blows up in play | Cloud and geometry compete for the same pixels | Budget the pair together [schneider2023] pp.177–179 |
| A "SIGGRAPH" citation that turns out not to be refereed | [schneider2023] p.219's own reference list labels course talks "ACM SIGGRAPH" | Check the venue, not the label |

## What is not established here

Stated plainly rather than inferred, because the temptation to fill this in is strong:

- **What a typical 2026 team ships is not established by these sources.** Claims of the form "most
  studios still use Nubis" circulate; no primary artefact in this set supports them.
- **Unreal Engine's Volumetric Cloud component could not be obtained** — JS-only documentation, and
  HTTP 403 on the mirror. Nothing here describes what it ships.
- **Unity, Godot and Frostbite-since-2016 were not investigated.** The only non-Guerrilla production
  source here is [hillaire2016], and it is ten years old.
- **Absence of a 2024–2026 successor is not evidence that 2023 is superseded.** SIGGRAPH 2026's
  *Advances in Real-Time Rendering* has no cloud talk; that makes [schneider2023] the last published
  word from the originator, nothing more.
- **[olajos2026] was not opened**, and is named for direction only: the refereed frontier is
  proposing to drop ray marching for rasterised neural cloud assets. That is a research direction,
  not a shipping practice.
