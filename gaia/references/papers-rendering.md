---
type: Bibliography
title: Papers — rendering
description: "Sources for the rendering axis: heightfield LOD, streaming, virtual texturing, GPU-driven submission, planetary precision, water surfaces, caustics, ray marching, the clear-sky and atmosphere models behind the sky documents, and — arriving with a bibliography merge — offline mesh extraction and the colour sources behind mask-to-material."
tags: [bibliography, provenance, rendering]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Papers — rendering

The rendering family of Gaia's bibliography. Entry format, tier definitions, and the two
non-negotiable rules live in `papers-flow.md`; they are not restated here.

Note for editors: entry ids are written **without** square brackets in this file. A bracketed
id anywhere in a bibliography's body reads as an uncited inline citation and the guard rejects
it — bibliographies are checked as documents like everything else.

## What was read, and what was not — offline meshing and colour

This section covers the two sections a bibliography merge added to this file from separately
written documents. The rest of this
bibliography predates the practice.

**`garland1997`** — the authors' own PDF of the SIGGRAPH '97 paper; §3–§5 read there.

**sharma2005** — the author's PDF at hajim.rochester.edu, plus the 34-pair supplementary test
file `ciede2000testdata.txt` from the same site, which was used to validate the implementation
in `colour_blend.py`, recorded in `registers/pseudocode-execution.tsv`.
**moreland2009** — **the author's "Expanded" version was read, not the ISVC proceedings paper.**
Section and equation numbers in the locator refer to that expanded PDF, and the proceedings
pagination is not asserted.

⚠️ **The sRGB standard itself, IEC 61966-2-1, is deliberately absent**: it is paywalled and was
not opened. `icc_srgb` — a standards-body technical note restating it, graded `F` accordingly —
carries the constants instead. ⚠️ This note used to add "and `mask-to-material.md` names the
standard in prose", offered as the compensating control that made declining an entry acceptable.
It does not: `IEC` and `61966` occur in that document only inside the `srgb1996` YAML locator,
nowhere in its body. The absence is still the right call — the standard is paywalled and unopened,
and a `?` may not be cited — but it rests on `icc_srgb` restating the constants, not on a naming
that never happened. And the "full list of absences from this family" in
`papers-masks-and-filtering.md` does not include this one.

## What `F` means on this axis, and why there is so much of it

Real-time rendering's load-bearing literature is largely **not peer-reviewed**, and pretending
otherwise is the failure this file exists to prevent. Geomipmapping is a self-published
whitepaper. Chunked LOD is a SIGGRAPH *course note*. GPU-driven pipelines, Nanite, virtual
texturing and every shipped water system are conference **talks**. Clipmap texturing and the
visibility buffer are real papers; the chapter that made clipmaps practical on a GPU is a
GPU Gems book chapter.

So the tier distribution here is roughly half `F`, and that is the correct answer, not a gap.
A course note is `F`. A GDC deck is `F`. An engine's documentation is `F`. A book — even the
canonical one — is `F`, because "peer-reviewed paper" is what `P` asserts and a textbook is not
one. Say "no canonical paper; standard practice is…" and name the talk. Do not launder a slide
deck into a citation.

⚠️ **The tier is not the whole obligation — the prose has to say it too.** Four of this axis's
documents open on a headline recommendation that rests on an `F`, and a bare trailing marker reads
exactly like a peer-reviewed citation to anyone skimming: heightfield-lod.md on strugar2009 (a
whitepaper), gpu-driven-culling.md on haar2015 (a course talk), tiled-streaming.md on cozzi2011 (a
textbook), virtual-texturing.md on epicrvt (engine documentation this file itself flags as needing
re-verification per release). Each of those four now names the artefact in the sentence that makes
the recommendation. If you add a fifth, do the same: the reader must learn what kind of thing is
holding the claim up before they learn to trust the claim.

## Attribution corrections specific to this axis

Each of these sends an implementer to the wrong place.

The clipmap row below previously reassigned the toroidal update and the degenerate-triangle
stitching to the 2005 chapter and asserted "different authors". Both halves were wrong, and it was
wrong in the table whose job is being right about attribution: Hugues Hoppe is an author of both
publications, and the 2004 paper contains both mechanisms. The row now quotes the 2004 paper. A
corrections table that is not itself corrected is just a second source of errors with more
authority.

| Common claim | Reality |
|---|---|
| "Geometry clipmaps — Losasso & Hoppe 2004", cited for the *GPU-resident* form | The 2004 paper carries more than the split usually given it. §3: each level's vertex array "is accessed toroidally, i.e. with 2D wraparound addressing using mod operations", and textures likewise. §5: with toroidal access "we do not need to copy the old data when shifting a level — instead, we simply fill the newly exposed L-shaped region". §6.2: T-junctions are removed by "rendering zero-area triangles along the render region boundaries" — degenerate-triangle stitching, in 2004. (That sentence closes §6.2; §6.3 is "Texture mapping". This correction row itself said §6.3 until someone opened the PDF to check it — a wrong section number is worse than a paraphrase, because it reads as more verified than either. See papers-flow.md.) What asirvatham2005 adds is the **GPU-resident** form: heights in a *vertex texture* read by the vertex shader (§2.3.5) and the clipmap updated on the GPU (§2.4), which the 2004 paper names as future work. Same senior author, one year later, not different authors. Cite 2004 for toroidal addressing and zero-area stitching; cite 2005 for the vertex-texture implementation. |
| "Chunked LOD — Ulrich, SIGGRAPH 2002" | It is a SIGGRAPH **course note**, not a SIGGRAPH paper. Tier `F`. The technique is real and universal; the venue is not peer review. Same for Tessendorf's ocean notes, which the wave-model documents own. |
| "Real-time engines compute caustics" | Almost none do. The shipped default is an authored looping texture projected down the light direction — an *animation*, with no dependence on the water surface that supposedly focused it. The image-space caustic-map lineage (wyman2006, shah2007) is the cheapest thing that is actually a caustic. |
| "Bruneton's roughness-aware Fresnel is Schlick multiplied by `exp(-2.69σ)`" | The published form puts that factor **inside the exponent**: `pow(1 - cosθ, 5*exp(-2.69σ)) / (1 + 22.7σ^1.5)`, applied as `F = R + (1-R)·that`. Multiplied on the outside instead it can only *lower* reflectance, while the real fit raises it above Schlick through the middle of the angular range. Both forms agree exactly at σ = 0, so a calm-water test passes and only rough water at grazing angles is wrong. |
| "Opacity micromaps let ray tracing follow a deforming heightfield" | Category error. Opacity micromaps classify **alpha coverage** for traversal; they encode no displacement and track no height edits. See dxrspec, and keep the ray-tracing proxy contract. |

### Sky and atmosphere

**Six** refereed sources plus two `F` entries, all obtained and read. ⚠️ This paragraph said "five"
and was written before `hillaire2020` was added a commit later and never folded in — the count is
part of what a read log is for, so it is corrected rather than quietly widened. **Four of the six
`P` artefacts diverge from the published record**, so locators are indexed by section, equation,
figure or table rather than by page; the exception is `preethamshirleysmits1999`, the one copy
carrying real proceedings folios.

**`brunetonneyret2008`** — the publisher-typeset EGSR/CGF version via the Inria HAL deposit
(`inria-00288758`), carrying the Eurographics masthead and the Blackwell footer. **Its eight
article pages carry no folio numbers at all**, so cite sections and equations, never pages. ⚠️ An
earlier version of this log said "paginated 1–8, not 1079–1086" — both halves were wrong: there is
no 1–8 numbering to read, and the HAL cover sheet *does* print "27 (4), pp.1079-1086".
**`bruneton2017`** — arXiv:1612.04336v1, which states on its own first page that it is "the
author's version of an article that has been published in this journal". Paginated 1–15, not
2641–2655, and dated 2016 against a 2017 issue. Section, figure and table numbers match.
**`hosekwilkie2012`** — the authors' *lowres* preprint on the Charles University CGG page. Every
one of its nine pages is stamped "To appear in ACM TOG 31(4)." — checked, nine of nine — so it
carries no article pagination against the record's 95:1–95:9, and figure detail is degraded. Its
**supplemental material**, which holds the fitted matrices and the per-band SNR charts, is not in
this PDF and was **not opened**.
**`preethamshirleysmits1999`** — the ACM proceedings version, mirrored on a Duke course page, with
folios **91–100** present across its ten pages, so page citations into it are valid. ⚠️ This log
said 91–99 while the entry beside it cited 91–100; the entry was right. ⚠️ Its embedded fonts use a non-standard
encoding: extracted mathematics comes out as escape sequences (`/#0B /=/1 /: /3`), so every formula
quoted from it was reconstructed from context rather than copied.
**`nishita1993`** — the author's own **raster scan** at nishitalab.org, with no text layer and
pages stored vertically flipped; it was read as page images. Unpaywall reports the DOI closed with
no OA location, so this is the only route found. Quotations from it are transcriptions from a
bilevel scan, punctuation approximate, and **no proceedings folios were visible**, so pp. 175–182
comes from the record and not from the artefact.

## Heightfield LOD

- **duchaineau1997** `P` — Duchaineau, M., Wolinsky, M., Sigeti, D.E., Miller, M.C., Aldrich, C. & Mineev-Weinstein, M.B. (1997). *ROAMing terrain: real-time optimally adapting meshes.* IEEE Visualization '97, 81–88. — Longest-edge-bisection binary triangle tree with frame-coherent split/merge priority queues.
- **deboer2000** `F` — de Boer, W.H. (2000). *Fast terrain rendering using geometrical mipmapping.* Self-published whitepaper (flipcode). — Geomipmapping: fixed chunks, per-chunk mip chain, index-buffer edge stitching. No venue and no review; universally cited anyway.
- **ulrich2002** `F` — Ulrich, T. (2002). *Rendering massive terrains using chunked level of detail control.* SIGGRAPH 2002 course notes. — Chunked LOD: quadtree of pre-simplified static chunks, per-chunk maximum geometric error, skirts, per-chunk geomorph. Course notes, not peer review.
- **losasso2004** `P` — Losasso, F. & Hoppe, H. (2004). *Geometry clipmaps: terrain rendering using nested regular grids.* ACM TOG 23(3), SIGGRAPH '04, 769–776. — Nested viewer-centred rings, each 2× coarser, with a transition region on each ring's fringe. Also, and contrary to how it is usually split against the 2005 chapter: toroidal (2D wraparound, mod-addressed) access to each level's vertex array and to the textures, §3; the L-shaped incremental update that toroidal access makes possible, §5; and zero-area-triangle stitching for T-junction removal, at the close of §6.2 (§6.3 is Texture mapping).
- **asirvatham2005** `F` — Asirvatham, A. & Hoppe, H. (2005). *Terrain rendering using GPU-based geometry clipmaps.* GPU Gems 2, ch. 2, NVIDIA/Addison-Wesley. — The GPU-resident form: elevations live in a single-channel *vertex texture* the vertex shader reads (§2.3.5), and the clipmap is updated GPU-side by rendering quads into that texture (§2.4). Toroidal addressing and the zero-area stitching triangles ORIGINATE in losasso2004, which flagged the vertex-texture path as future work — cite 2004 for those mechanisms. ⚠️ But this entry used to say the GPU-resident form "is the whole of what is new here", and that overstates it: §2.4 Update restates the L-shaped region and toroidal wraparound in its own words and adds an observation the 2004 paper does not make. Inherited is not the same as absent. Book chapter, not peer review.
- **strugar2009** `F` — Strugar, F. (2009). *Continuous distance-dependent level of detail for rendering heightmaps (CDLOD).* Self-published whitepaper with a reference implementation; a peer-reviewed journal version exists as Journal of Graphics, GPU, and Game Tools 14(4), 57–74, doi:10.1080/2151237X.2009.10129287. — Quadtree selection over one shared grid mesh, with a per-vertex distance morph that makes a node vertex-identical to its parent at the range boundary. **Why this stays `F` while upchurch2012 — same journal, later run under its earlier name — is `P`: the difference is verification state, not venue.** ⚠️ The promotion path this entry used to give was itself wrong: it said to obtain JGGGT 14(4) and confirm "the morph derivation and the per-level morph constants" are there. The reachable whitepaper contains **neither** — it gives `morphK` as an input to `morphVertex()` and a 15–30% band, not a derivation or a constant table — so a reader could not have completed that path from the artefact this skill actually cites. Note too that the whitepaper is dated 11 July 2010 and closes "Paper revision 1 — Originally published in the journal of graphics, gpu and game tools", so it POST-dates the journal article. The venue argument for `F` is therefore stronger, not weaker. The journal article is peer-reviewed and on venue alone would qualify; the artefact read here is the whitepaper, every citing document's locator points into the whitepaper's derivation, and `P` asserts that a human read *the cited work* and found the algorithm in it. This is the most load-bearing `F` on the axis, since CDLOD is the primary recommendation of heightfield-lod.md, so the promotion path is written down rather than left implicit: obtain JGGGT 14(4), 57–74, confirm the morph-factor derivation and the per-level morph constants are there, re-point the locators at its sections, promote to `P`, and record the reader under `verified:`.
- **dupuy2020** `P` — Dupuy, J. (2020). *Concurrent binary trees (with application to longest edge bisection).* Proceedings of the ACM on Computer Graphics and Interactive Techniques 3(2) (HPG 2020), art. 21, doi:10.1145/3406186. — A GPU-resident bitfield binary tree: lock-free split/merge from thousands of threads, O(1) leaf enumeration for indirect draw.

## Streaming and residency

- **cozzi2011** `F` — Cozzi, P. & Ring, K. (2011). *3D Engine Design for Virtual Globes.* CRC Press. — Tile pyramids, screen-space-error refinement, replacement vs additive refinement, out-of-core residency, the horizon-culling test, camera-relative rendering and its GPU double-single form, ellipsoid geodesy. The canonical treatment of two of this axis's documents — and a textbook, not a peer-reviewed paper.
- **andersson2007** `F` — Andersson, J. (2007). *Terrain rendering in Frostbite using procedural shader splatting.* SIGGRAPH 2007 course (Advanced Real-Time Rendering). — Tile payloads split between the geometry and the material pipelines. Course talk.
- **directstorage** `F` — Microsoft. *DirectStorage* documentation. — Disk→GPU decompression, request batching, NVMe queue-depth guidance. Vendor documentation; drifts by release.

## Materials and virtual texturing

- **tanner1998** `P` — Tanner, C.C., Migdal, C.J. & Jones, M.T. (1998). *The clipmap: a virtual mipmap.* SIGGRAPH '98, 151–158. — A nested-resolution, toroidally updated texture stack centred on the viewer; residency as a pure function of view distance. The ancestor of virtual texturing.
- **mittring2008** `F` — Mittring, M. (2008). *Advanced virtual texture topics.* SIGGRAPH 2008 Advances in Real-Time Rendering course. — Page tables, feedback passes, page borders, transcode budgets. Course talk.
- **barrett2008** `F` — Barrett, S. (2008). *Sparse virtual textures.* GDC 2008. — The other standard exposition of the same plumbing, from the software-VT side. Conference talk.
- **mishkinis2013** `F` — Mishkinis, A. (2013). *Advanced terrain texture splatting.* GameDev.net article. — Height-based splat blending: per-layer height maps let the more prominent material win the boundary instead of a linear cross-fade. Article, not peer-reviewed.
- **epicrvt** `F` — Epic Games. *Runtime Virtual Texturing* and *Virtual Texturing* documentation, Unreal Engine. — The branded instance of the runtime-VT architecture: landscape materials composited into pages, meshes sampling them back. Engine documentation; re-verify per release.

## GPU-driven submission

- **haar2015** `F` — Haar, U. & Aaltonen, S. (2015). *GPU-driven rendering pipelines.* SIGGRAPH 2015 Advances in Real-Time Rendering course (Assassin's Creed Unity). — The persistent GPU scene, the CPU-policy/GPU-visibility split, and two-phase occlusion culling. The single most-cited source on this axis, and not a paper.
- **karis2021** `F` — Karis, B., Stubbe, R. & Wihlidal, G. (2021). *Nanite — a deep dive.* SIGGRAPH 2021 Advances in Real-Time Rendering course. — Cluster DAG LOD, two-pass occlusion culling, software rasterization coupled to a visibility buffer. Course talk.
- **burns2013** `P` — Burns, C.A. & Hunt, W.A. (2013). *The visibility buffer: a cache-friendly approach to deferred shading.* Journal of Computer Graphics Techniques 2(2), 55–69. — Rasterize (instance ID, triangle ID) plus depth; reconstruct attributes and shade in a later pass.
- **wihlidal2016** `F` — Wihlidal, G. (2016). *Optimizing the graphics pipeline with compute.* GDC 2016 (Frostbite). — Compute cluster and triangle culling: backface cones, zero-area and small-primitive rejection ahead of the rasterizer. Conference talk.
- **d3d12indirect** `F` — Microsoft. *Indirect drawing* / `ExecuteIndirect` documentation (D3D12), and the Vulkan `vkCmdDrawIndexedIndirectCount` specification. — Count-buffer semantics for GPU-written draw arguments, and descriptor-indexing divergence rules. API documentation.

## Planetary scale and numerical precision

- **upchurch2012** `P` — Upchurch, P. & Desbrun, M. (2012). *Tightening the precision of perspective rendering.* Journal of Graphics Tools 16(1), 40–56. — Error analysis of the depth transform, and the two mappings the paper actually recommends: the infinite projection (§3.2) and the two-step transform (§4.1). ⚠️ **It is not the source for reversed-Z.** This entry used to sell it as "why a reversed-Z mapping into a floating-point depth buffer keeps relative error near-constant" — the paper's §6 says complementary reversed Z suffers the **same 2ε arithmetic loss** as 1/Z. `planetary-precision.md` read §6 and says so at both ends; the bibliography kept advertising the conclusion that section denies.
- **reed2015** `F` — Reed, N. (2015). *Depth precision visualized.* Public write-up. — The standard practical explanation of the float-depth / reversed-Z interaction. Blog post.
- **epiclwc** `F` — Epic Games. *Large World Coordinates* documentation, Unreal Engine 5. — Engine-native double-precision world transforms, and the shader-side paths that still break. Engine documentation.

## Water surfaces

The wave field itself, the dispersion relation, and the absorption law belong to the water
documents on the simulation axis. What is listed here is what a *renderer* consumes.

- **bruneton2010** `P` — Bruneton, E., Neyret, F. & Holzschuch, N. (2010). *Real-time realistic ocean lighting using seamless transitions from geometry to BRDF.* Computer Graphics Forum 29(2) (Eurographics), 487–496. — The slope-variance tensor that carries unresolved wave detail out of geometry and into the BRDF, the roughness-aware Fresnel fit — whose `exp(-2.69σ)` term scales the *exponent* of the Schlick power, not the result — and the solar-disc clamp on variance.
- **coxmunk1954** `P` — Cox, C. & Munk, W. (1954). *Measurement of the roughness of the sea surface from photographs of the sun's glitter.* Journal of the Optical Society of America 44(11), 838–850. — Mean-square sea-surface slope regressed on wind speed, anisotropic along and across wind, plus the slicked-water measurements. Wind is referenced at 12.5 m, and the fit covers 1–14 m/s only.
- **ross2005** `P` — Ross, V., Dion, D. & Potvin, G. (2005). *Detailed analytical approach to the Gaussian surface bidirectional reflectance distribution function specular component applied to the sea surface.* JOSA A 22(11), 2442–2453. — The Gaussian-slope microfacet BRDF with Smith masking that a statistical glitter model evaluates.
- **dupuy2012** `P` — Dupuy, J. & Bruneton, E. (2012). *Real-time animation and rendering of ocean whitecaps.* SIGGRAPH Asia 2012 Technical Briefs, art. 15. — Prefilterable whitecap coverage as an error function over the footprint mean and variance of the displacement Jacobian.
- **monahan1980** `P` — Monahan, E.C. & O'Muircheartaigh, I. (1980). *Optimal power-law description of oceanic whitecap coverage dependence on wind speed.* Journal of Physical Oceanography 10(12), 2094–2099. — `W = 3.84e-6 · U^3.41`, U at 10 m: how much foam a given wind owes you.
- **deliot2023** `P` — Deliot, T. & Belcour, L. (2023). *Real-time rendering of glinty appearances using distributed binomial laws on anisotropic grids.* Computer Graphics Forum 42(8) (HPG 2023), doi:10.1111/cgf.14866. — Counting the facets inside a pixel footprint that reflect toward the eye; the discrete-glint tier above a statistical BRDF. The venue looks inconsistent with dupuy2020 above and is not: HPG's journal track has used two different journals across editions — PACMCGIT for HPG 2020, a Computer Graphics Forum special issue for HPG 2023 — so both entries are right as written. Checked against the publisher record rather than assumed, because "HPG publishes in PACMCGIT" is exactly the kind of half-true rule that produces a confident wrong correction.
- **johanson2004** `F` — Johanson, C. (2004). *Real-time water rendering — introducing the projected grid concept.* MSc thesis, Lund University. — A screen-space grid projected onto the water plane, and its horizon-edge instability. A thesis.
- **vlachos2010** `F` — Vlachos, A. (2010). *Water flow in Portal 2.* SIGGRAPH 2010 Advances in Real-Time Rendering course. — Flow mapping: two phase-offset samples of the same texture cross-faded on a triangle wave, so advection never accumulates unbounded distortion. Course talk.
- **unrealwater** `F` — Epic Games. *Water system*, *Water meshing and surface rendering*, and *Single Layer Water shading model* documentation, Unreal Engine 5. — The engine-native water architecture: a quadtree water mesh, a fused water-info texture, and a single-depth-layer transparent shading model. Engine documentation, and it has changed shape repeatedly across releases.

## Caustics

- **jensen1996** `P` — Jensen, H.W. (1996). *Global illumination using photon maps.* Rendering Techniques '96 (7th Eurographics Workshop on Rendering), 21–30. — The photon map, and the separate high-density **caustic map** built by shooting photons only along specular paths from the light. The ground truth every real-time approximation is approximating.
- **wyman2006** `P` — Wyman, C. & Davis, S. (2006). *Interactive image-space techniques for approximating caustics.* I3D 2006, 153–160. — Photons emitted per texel of a light-space image of the refractive surface, refracted twice, then gathered in image space. The first practical interactive caustic map.
- **shah2007** `P` — Shah, M.A., Konttinen, J. & Pattanaik, S. (2007). *Caustics mapping: an image-space technique for real-time caustics.* IEEE TVCG 13(2), 272–280. — The same family, with the receiver position found by iterating against a light-space depth map rather than assuming a plane — which is what makes it work over real bathymetry.
- **guardado2004** `F` — Guardado, J. & Sánchez-Crespo, D. (2004). *Rendering water caustics.* GPU Gems, ch. 2, NVIDIA/Addison-Wesley. — The projected-texture and per-vertex intensity forms of the effect as shipped in the early 2000s. Book chapter.
- **zeltner2020** `P` — Zeltner, T., Georgiev, I. & Jakob, W. (2020). *Specular manifold sampling for rendering high-frequency caustics and glints.* ACM TOG 39(4) (SIGGRAPH 2020). — Solving for specular chains by manifold walks instead of hoping to hit them by chance; the studio-quality answer for caustics through water.

## Ray marching and ray tracing against heightfields

- **tevs2008** `P` — Tevs, A., Ihrke, I. & Seidel, H.-P. (2008). *Maximum mipmaps for fast, accurate, and scalable dynamic height field rendering.* I3D 2008, 183–190. — The max-reduce pyramid and the hierarchical safe-skip traversal over it, with a precompute cheap enough for a heightfield that changes every frame.
- **policarpo2005** `P` — Policarpo, F., Oliveira, M.M. & Comba, J.L.D. (2005). *Real-time relief mapping on arbitrary polygonal surfaces.* I3D 2005, 155–162. — Linear search plus binary refinement against a tangent-space height field.
- **tatarchuk2006** `P` — Tatarchuk, N. (2006). *Dynamic parallax occlusion mapping with approximate soft shadows.* I3D 2006, 63–69. — POM: view-angle-adaptive step counts, refinement at the crossing, and self-shadowing inside the shell.
- **dummer2006** `F` — Dummer, J. (2006). *Cone step mapping: an iterative ray-heightfield intersection algorithm.* Self-published whitepaper. — A per-texel empty-cone opening as a provably safe step bound. Not republished in GPU Gems 3: that book's ch. 18, *Relaxed cone stepping for relief mapping*, is by Policarpo & Oliveira, who introduce the relaxed variant — one permitted overshoot, then a binary search back — and cite Dummer for the cone bound it relaxes. That chapter is how most readers meet the technique, which is why the two get conflated.
- **drobot2010** `F` — Drobot, M. (2010). *Quadtree displacement mapping with height blending.* GPU Pro 1 / GDC 2010. — The max-mip pyramid applied to material displacement, and the height-blend compositor beside it. Book chapter and conference talk.
- **smacke** `F` — s-macke. *VoxelSpace* — algorithm reconstruction and reference implementation, github.com/s-macke/VoxelSpace. — Column raycasting with the ascending y-buffer, as shipped in Comanche (1992). A repository, and the canonical modern reconstruction of a technique whose original has no publication.
- **dxrspec** `F` — Microsoft *DirectX Raytracing (DXR)* specification and the Khronos `VK_EXT_opacity_micromap` / `VK_NV_displacement_micromap` registry entries. — Intersection shaders for procedural AABB geometry, BLAS build-versus-refit semantics, and what opacity micromaps do and do not classify. API specifications.

## Clouds

⚠️ **Read the tier column before the content here.** This is the one subject in the corpus where the
standard-setting artefacts are all unrefereed: the founding cloud documents are SIGGRAPH *course*
talks — invited instructors, no referee report — and every wall-clock figure in the subject comes
from one. Every error figure comes from a refereed paper measuring a different system. That
asymmetry is stated in `volumetric-clouds.md` and is the honest state of the evidence, not a
shortcoming of this list.

- **schneidervos2015** `F` — Schneider, A. & Vos, N. (2015). *The Real-time Volumetric Cloudscapes
  of Horizon: Zero Dawn.* In SIGGRAPH 2015 Course: Advances in Real-Time Rendering in Games. 99
  slide-pages; **no DOI on the released artefact** (the parent course record is doi:10.1145/2776880,
  which is course-level and not a paper DOI). — The founding artefact: Perlin–Worley base at 128³
  eroded by 32³ Worley, a coverage/precipitation/type weather texture, a 64→128 sample march with a
  cheap/expensive two-level sampler, and the 20 ms → 2 ms PS4 datum showing that **reprojection, not
  the density model, is what made real-time cloudscapes shippable**. ⚠️ `F` despite being the most
  influential real-time cloud document in existence — **being standard-setting is not review.** The
  artefact is PowerPoint exported to PDF with speaker notes; its own p.1 says so. ⚠️ Authorship
  differs across surfaces: the PDF metadata and the course index name **Schneider alone**, while the
  deck's own p.1 names both authors — "Schneider & Vos" is supported by p.1, not by the index.
  ⚠️ It **contradicts itself on the upsample factor** (quarter-res 1-in-16 of a 4×4 block, p.94, vs
  "render this at half res", p.95); quote both. ⚠️ Page numbers are PDF slide-pages and run one to
  two ahead of the deck's printed numbers, so ranges quoted elsewhere for this talk are suspect.
  ⚠️ It contains **no depth compositing against terrain and no ground-receiving cloud shadow**, and
  p.64 concedes its own "powder" term is **not in the refereed literature** — the author says he
  searched the ACM Digital Library for it and found nothing.
- **schneidervos2017** `F` — Schneider, A. & Vos, N. (2017). *Nubis: Authoring Real-Time Volumetric
  Cloudscapes with the Decima Engine.* SIGGRAPH 2017 Course: Advances in Real-Time Rendering. 108
  pages. — The optimisation ladder, **22 ms → 1.2 ms on PS4**, of which **depth culling against
  scene geometry alone is 1.81 → 1.2 ms**, taken with a conservative `max()` over a low-LOD depth
  mip because reprojection needs *next*-frame visibility. Also cloud depth as the depth at which
  alpha reaches 0.5 (p.101). ⚠️ **Its 22 ms baseline is POST-reprojection while schneidervos2015's
  20 ms is PRE-reprojection.** The two must not be stacked or read as a regression — same studio,
  same console, one year apart, measuring different things. A course talk, not peer review.
- **schneider2022** `F` — Schneider, A. (2022). *Nubis, Evolved.* SIGGRAPH 2022 Course: Advances in
  Real-Time Rendering. 207 pages. — The console-generation scaling table: PS4 at 960×540 with 6
  light samples in ≤4 ms against PS5 at 1920×1080 with 10 in ≤2–3 ms; the HLSL early-out at p.91
  (three texture reads, one multiply, `return 0.0`); `SampleLongDistanceShadowMap()` at p.112.
  ⚠️ The circulating PDF is **videos-stripped and carries no speaker notes**, so only on-slide text
  is quotable from it. A course talk, not peer review.
- **schneider2023** `F` — Schneider, A. (2023). *Nubis Cubed: Methods (and madness) to model and
  render immersive real-time voxel clouds.* SIGGRAPH 2023 Course: Advances in Real-Time Rendering.
  220 pages. — **The published successor, and the artefact that dates the lineage in both
  directions.** p.3 for the 2011 offline baseline (10 minutes to 4 hours per 1920×1080 frame); p.9
  for the term "2.5D clouds"; p.81 for a 2048×2048×256 voxel grid at **2.146 GB uncompressed**
  against 2015's whole-system "20 mb of ram", which is the memory arithmetic the whole lineage turns
  on; pp.176–185 for voxel costs (2.2–4 ms at 960×540, PS5) and the 200 m depth split replacing
  temporal upscaling; pp.177–179 for the geometry-against-cloud budget handoff. **p.198 carries the
  seven-axis capability table in which the 2015/2017 method scores `No` on Terrain-Cast Shadows,
  Flight-Capable and Freeform Modeling** — direct evidence from the originator against its own
  earlier method. ⚠️ **Its own reference list at p.219 labels course talks "ACM SIGGRAPH" and a 2018
  talk "Eurographics"**; a citation copied from that slide will read as refereed and is not.
- **hillaire2016** `F` — Hillaire, S. (2016). *Physically Based Sky, Atmosphere and Cloud Rendering
  in Frostbite.* SIGGRAPH 2016 Course: Physically Based Shading in Theory and Practice. 62 pages. —
  **The independent second lineage, and the source for the terrain couplings the Guerrilla decks
  lack.** Reaches the same density model separately (pp.33–34) and reports one deviation worth
  having: single-channel noise, "made cloud a lot faster to render … still giving the same final
  visual result". **Eq. 21, p.43** for cloud depth as a transmittance-weighted mean front depth;
  **p.42** for the ground-receiving cloud shadow baked to a 2D transmittance texture and projected
  onto the world, also feeding GI — ⚠️ with a **flat-planet assumption** that a large terrain breaks.
  0.91 ms at 720p on Xbox One. These are **written course notes**, not a slide deck, which is why
  they are quotable at a finer grain than the Guerrilla artefacts — but course notes are not peer
  review, hence `F`.
- **bouthors2008** `P` — Bouthors, A., Neyret, F., Max, N., Bruneton, E. & Crassin, C. (2008).
  *Interactive Multiple Anisotropic Scattering in Clouds.* I3D 2008, 173–182,
  doi:10.1145/1342250.1342277. — A Monte-Carlo reference **tabulated to 5% accuracy at the 95%
  confidence level**, which is what a multiple-scattering claim can be measured against; 2–10 fps at
  800×600 on an 8800 GTS; and the verdict on the phase function every real-time implementation still
  ships, that Henyey–Greenstein phase functions "give far from accurate visual effects". Also notes
  its transport function "allows us to easily account for points of view inside the clouds" (p.7),
  which is one of the few refereed remarks on the inside-the-deck regime. ⚠️ Read here in the
  authors' **submitted version** deposited at HAL, paginated 1–10 rather than 173–182, so sections
  are citable and journal pages are not.
- **yusov2014** `P` — Yusov, E. (2014). *High-Performance Rendering of Realistic Cumulus Clouds
  Using Pre-computed Lighting.* High Performance Graphics 2014, 127–136, doi:10.2312/hpg.20141101. —
  **The refereed source for both terrain couplings, which is why it matters out of proportion to its
  fame.** §5.4 and §5.6 (pp.132–133) give a screen-space "closest distance to cloud" buffer compared
  against the marched distance — depth-aware compositing with a referee behind it; p.133 gives a
  light-space cloud transparency buffer that **shares the cascaded-shadow-map matrices**, which is
  the ground-receiving cloud shadow. 5.6–15.4 ms at 1080p on a GTX 680.
- **kallweit2017** `P` — Kallweit, S., Müller, T., McWilliams, B., Gross, M. & Novák, J. (2017).
  *Deep Scattering: Rendering Atmospheric Clouds with Radiance-Predicting Neural Networks.* ACM TOG
  36(6) [SIGGRAPH Asia 2017], Art. 231, doi:10.1145/3130800.3130880. — **The error anchor for this
  subject.** RMSE against a path-traced reference stated at **34 hours to converge**, and an
  equal-time variance comparison per phase function — Henyey–Greenstein **698** against Lorenz–Mie
  **23136** — which makes bouthors2008's verdict on HG quantitative rather than editorial. ⚠️ The
  volume number differs between the paper's own front matter (36,4) and the ACM DL record (36,6);
  **the article number is the stable handle**.
- **yang2020** `P` — Yang, L., Liu, S. & Salvi, M. (2020). *A Survey of Temporal Antialiasing
  Techniques.* Computer Graphics Forum 39(2), EG STAR, doi:10.1111/cgf.14018. — p.10 names the
  failure modes of temporal reprojection: "transparency, particles and reflection … are known
  challenging cases for TAA to handle". This is the **refereed reason behind schneider2023's
  retirement of temporal upscaling for near-camera clouds**, a decision that artefact states without
  explaining.
- **olajos2026** `P` [not-opened] — Olajos, R., Doggett, M. & Goswami, P. (2026). *Neural cloud
  shading.* Proc. ACM Comput. Graph. Interact. Tech. 9(4). — ⚠️ **Not opened**: ACM DL returned 403
  on three attempts, the DiVA deposit reset the connection, the LUP mirror returned 500, and
  Unpaywall and Semantic Scholar both resolve back to the blocked DOI. Named for **direction only** —
  that the refereed frontier is proposing to drop ray marching entirely in favour of rasterised
  neural cloud assets. No parameter, cost or error from it is used anywhere in this corpus. `P` from
  the publication record, not from a reading; the CC-BY licence in that record is why the failure to
  obtain it is a fetch problem rather than a paywall.

## Sky and atmosphere

The clear-sky literature is unusually easy to grade because one of its own papers measures the
others. Read `bruneton2017` before choosing anything here.

- **bruneton2017** `P` — Bruneton, E. (2017). *A Qualitative and Quantitative Evaluation of 8 Clear
  Sky Models.* IEEE Transactions on Visualization and Computer Graphics 23(12), 2641–2655,
  doi:10.1109/TVCG.2016.2622272. — **The error half of this axis, and there is no substitute for
  it.** §14.1 and **Table 2** rank eight models by RMSE in mW/(m²·sr·nm) against the **sky measurements**
  themselves — `libRadtran` is a physically-based comparison point in the paper, not the error
  reference, and an earlier version of this entry said otherwise: Preetham **88.1**, O'Neal
  49.5, Hosek **41.5**, Nishita93 26.6, Nishita96 18.3, Haber 14.7, Bruneton **11.3**, Elek 11.3.
  Table 2 is also a **cost** table in the same rows — precompute time, precompute memory and render
  time as complexities — which makes it the one artefact in this corpus that states both halves of
  a recommendation in a single table. ⚠️ **Its caption footnote is load-bearing and easy to drop:**
  the precompute columns for **Haber and Nishita96 are per single sun zenith angle**, Bruneton's and
  Elek's are for `n` angles, and Nishita93's are independent of sun angle. The columns are not
  comparable as printed. ⚠️ And the measurement window is **09h30–13h30 only** (§3.1, 17 daytimes,
  81 directions); the 06h00 cell is `n/a`, so no RMSE here evidences a sunset claim — Table 2's
  separate `sunset sunrise` column does. ⚠️ The paper spells the third author's model **O'Neal**, not
  O'Neil. It gives complexities, not wall-clock, so an RMSE from here must not be paired with a
  frame time from another paper and called a measurement.
- **brunetonneyret2008** `P` — Bruneton, E. & Neyret, F. (2008). *Precomputed Atmospheric
  Scattering.* Computer Graphics Forum 27(4), 1079–1086 (EGSR 2008),
  doi:10.1111/j.1467-8659.2008.01245.x. — The precomputation that the modern LUT pipeline descends
  from. §4 Algorithm 4.1 `PRECOMPUTE(norders)`; §2.1 for the medium — ground radius `Rg` = 6360 km,
  top of atmosphere `Rt` = 6420 km, Rayleigh scale height `HR` = 8 km, Mie `HM` ≈ 1.2 km, and
  `βs_R` = (5.8, 13.5, 33.1)·10⁻⁶ m⁻¹ at λ = (680, 550, 440) nm; eq. 2 for the Rayleigh phase
  function and eq. 4 for Cornette–Shanks. §6 for the tables: transmittance 64×256, ground
  irradiance 16×64, and inscattering as a 32×128×32×8 four-dimensional table packed into one
  32×128×256 RGBA texture, **8 MB at half precision**. §6 also states the cost: 125 fps at
  1024×768 on an NVidia 8800 GTS, of which 0.4 ms is the first three terms and 2.6 ms the rest,
  and 25 fps with light shafts.
  ⚠️ **It does not iterate to convergence, and a document must not say it does.** Algorithm 4.1 is
  `for i ← 1 to i < norders` — a fixed count with no stopping criterion, tolerance or residual
  anywhere in the paper. The implementation uses **five** orders. Checked: the string "ozone" does
  not appear in the paper at all; the medium is air molecules and aerosols only.
  ⚠️ Its two validation figures against the CIE clear sky model use **different** aerosol fits —
  Fig. 6 gives `g` = 0.76 with `βs_M` = 2·10⁻⁵ m⁻¹, Fig. 7 gives `g` = 0.73 with 2.2·10⁻⁵ m⁻¹. Cite
  one or the other with its figure; there is no single "the" value.
- **hosekwilkie2012** `P` — Hosek, L. & Wilkie, A. (2012). *An Analytic Model for Full Spectral
  Sky-Dome Radiance.* ACM Transactions on Graphics 31(4), art. 95 (SIGGRAPH 2012),
  doi:10.1145/2185520.2185591. — The analytic successor to Preetham, fitted to a brute-force
  reference rather than to a simpler model. Cited for the analytic tier: zero precompute, O(1)
  render, and per `bruneton2017` Table 2 an RMSE of 41.5 — better than Preetham's 88.1 and far
  worse than a precomputed model. ⚠️ The fitted matrices live in **supplemental material that was
  not opened here**, so nothing in this corpus may quote a coefficient from it.
- **preethamshirleysmits1999** `P` — Preetham, A.J., Shirley, P. & Smits, B. (1999). *A Practical
  Analytic Model for Daylight.* SIGGRAPH '99, 91–100, doi:10.1145/311535.311545. — The analytic
  daylight model that everything after it is measured against, and the worst performer in
  `bruneton2017`'s table at RMSE 88.1, overestimating by roughly a factor of two. Cited for what it
  is: the baseline that made analytic skies routine, not a model to ship in 2026. Among the five
  *clear-sky model* sources it is the only one treating **ozone**, and then only as a 0.0035 m NTP
  column absorber on the direct solar beam — but ⚠️ `hillaire2020` **does** model it, with a
  dedicated Table 1 row (σ_oa = 0.650, 1.881, 0.085 ·10⁻⁶ m⁻¹ and a tent profile), and calls it
  "key to achieving sky-blue colors when the sun is at the horizon". Do not read the five as the
  whole field — read on the page, in a sentence whose surrounding mathematics
  the artefact's font encoding renders unquotable.
- **nishita1993** `P` — Nishita, T., Sirai, T., Tadamura, K. & Nakamae, E. (1993). *Display of the
  Earth Taking into Account Atmospheric Scattering.* SIGGRAPH '93, 175–182,
  doi:10.1145/166117.166140. — The origin of the scale-height atmosphere in graphics, and the
  source of the constants everything since has inherited. `bruneton2017` scores it 26.6 — better
  than two models published a decade later. ⚠️ Read as a **raster scan with no text layer**; see
  the read log. Quotations are transcriptions, and its page numbers come from the record.

- **hillaire2020** `P` — Hillaire, S. (2020). *A Scalable and Production Ready Sky and Atmosphere
  Rendering Technique.* Computer Graphics Forum 39(4), 13–22 (EGSR 2020), doi:10.1111/cgf.14050. —
  **The cost half of this axis.** The LUT set that makes a physical sky fit in a frame *including*
  its own updates. §7 and **Table 2** give resolutions, step counts and per-LUT times on an NVIDIA
  1080 and an iPhone 6s: transmittance 256×64 / 40 steps / 0.01 ms, sky-view 200×100 / 30 / 0.05 ms,
  aerial perspective 32³ / 30 / 0.04 ms, multi-scattering 32² / 20 / 0.07 ms, **0.31 ms total at
  1280×720**; mobile 0.53 / 0.27 / 0.11 / 0.12 ms with sky-view dropped to 96×50. Volumetric
  atmospheric shadows at 32 samples take it to 1.0 ms.
  ⚠️ **It is not simply faster than its predecessor, and the entry must not say so.** §7 verbatim:
  "the total render time is 0.31 ms … For the same view, the Bruneton model [BN08] renders in
  0.22ms, **but this is without all the LUTs being updated**. Updating all the LUTs using the code
  provided costs **250ms**, where 99% of this cost comes from the many iterations required to
  estimate multiple scattering." Bruneton renders *faster*; what it cannot do is rebuild its state
  in a frame. That is the whole contribution, and it is a different claim from speed.
  ⚠️ Three Hillaire sky artefacts circulate and are routinely conflated: this refereed EGSR/CGF
  paper; a 2016 Frostbite SIGGRAPH **course talk** (`F`, and there is no written notes PDF at all —
  the substance is in a PowerPoint's speaker-notes pane); and a **2020 SIGGRAPH course** on the same
  technique in the same year (`F`). Only this one is peer-reviewed. Read at the author's copy
  `sebh.github.io/publications/egsr2020.pdf`, whose page 1 carries "Eurographics Symposium on
  Rendering 2020 / Volume 39 (2020), Number 4" and whose acknowledgments thank "the **anonymous
  reviewers**" — both checked. The publisher copy was not reached, so byte-identity with the record
  is unverified.
- **bilodeau2014** `F` — Bilodeau, B. (2014). *Vertex Shader Tricks*, AMD, GDC 2014. — A conference
  talk, not peer review. Cited for exactly one sentence, on slide 12: **"Triangle has better
  performance than quad."**
  ⚠️ **The reasoning everybody repeats is not in this artefact.** All 33 slides and their speaker
  notes were read; the quad-utilisation and diagonal-seam explanation appears nowhere in it, and
  slide 12 has no notes at all. That argument lives only in personal blogs, and the measurements
  there are small — about 0.1 ms on an artificial 512² shader, and **0.2% at 1080p**. Cite this for
  the claim; do not attribute the explanation to it, and do not present the effect as large.

- **tr_lighting_shadows** `F` — `terrain-renderer/references/10-lighting-shadows.md`, this
  repository. — Not peer review: a practitioner chapter in a sibling skill, cited for what a
  shipping renderer chose and never as evidence that a mechanism is correct. §"Atmospheric
  integration" for the fullscreen-triangle sky idiom, the three-media composition hazard and the
  height-fog boundary; the volumetric-cloud bullets for the **one sky state** rule — "the coverage
  field that shapes the clouds is the *same* map that drives the cloud-shadow term below and, where
  a weather system exists, `13`'s weather intensity" — and for the cloud scroll vector being the
  wind vector. Checked present on this branch and on `main`.

## Offline mesh extraction and simplification


- **garland1997** `P` — Garland, M. & Heckbert, P.S. (1997). *Surface simplification using quadric error metrics.* SIGGRAPH '97, 209–216, doi:10.1145/258734.258849. — The canonical error-driven simplifier. Iterative contraction of vertex *pairs* (not only edges, so disconnected regions can be joined), with the error at a vertex defined as the sum of squared distances to the planes of its incident triangles and stored as a single symmetric 4×4 quadric; the additive rule for merging two vertices' plane sets, the 4×4 linear solve for the optimal contraction target, and the cost heap that orders the whole run. §6 adds the boundary and discontinuity constraint planes, naming terrain height fields as the case that needs them. Note that the paper is careful about what its metric *is*: a sum of squared distances to a plane set, deliberately double-counting shared planes up to three times, whose absolute value has no intrinsic meaning outside the ranking it produces.
- **garland1995** `F` — Garland, M. & Heckbert, P.S. (1995). *Fast polygonal approximation of terrains and height fields.* Technical report CMU-CS-95-181, School of Computer Science, Carnegie Mellon University; C++ implementation released as `scape`. — The refinement family: greedy insertion of the highest-error grid point into a Delaunay TIN, four progressively optimised variants, the empirical comparison of importance measures that settles on plain vertical error against the current approximation, and the error-versus-vertex-count behaviour. `F` because it is a technical report and never went through peer review; the report itself records that greedy insertion "has been reinvented many times", so there is no canonical paper to promote to, and the honest form is to say so. Still the most useful single treatment of simplification aimed specifically at a heightfield.
- **hoppe1996** `P` — Hoppe, H. (1996). *Progressive meshes.* SIGGRAPH '96, 99–108, doi:10.1145/237170.237216. — The nested multiresolution representation: a base mesh plus a stream of vertex-split records, built by edge collapses alone, from which every intermediate mesh in the chain is recoverable. Cited here for the structural consequence rather than the construction — because consecutive levels share vertices by construction, a geomorph between them is definable at all, which is the property an exported LOD chain either has or does not.

## Mask to material


- **sharma2005** `P` — Sharma, G., Wu, W. & Dalal, E.N. (2005). *The CIEDE2000 color-difference formula: Implementation notes, supplementary test data, and mathematical observations.* Color Research & Application 30(1), 21–30, doi:10.1002/col.20070. — The colour-difference metric, plus the thing that makes it usable: 34 supplementary CIELAB pairs with published ΔE00 values, designed to catch the implementation errors — signed chroma and hue differences, the arctangent quadrant, the mean-hue boundary cases — that the CIE's own worked examples do not. The paper's own account is that several widely distributed implementations, including the authors' early ones, passed the CIE examples and were still wrong.
- **moreland2009** `P` — Moreland, K. (2009). *Diverging color maps for scientific visualization.* Proc. 5th International Symposium on Visual Computing (ISVC 2009), LNCS 5876, 92–103. Read as the author's expanded version, `ColorMapsExpanded.pdf`. — Mapping a scalar to a colour, done deliberately. ⚠️ The colour-space chain and eqs. (1)–(3) are **§2.2 Color Spaces**, not §3: §3 is "Color Map Requirements", a six-bullet list with no equations in it. This entry and `mask-to-material.md` both carried §2.2's title against §3's number. §2.1 is the case against the rainbow map: no perceptual ordering, non-uniform perceptual rate, and sensitivity to colour-vision deficiency. §3 gives the sRGB → linear → XYZ → CIELAB chain, eqs. (1)–(3), and states the operative distinction for a terrain palette — physical light effects belong in a linear space, perception of a colour belongs in CIELAB.
- **icc_srgb** `F` — International Color Consortium. *How to interpret the sRGB color space (specified in IEC 61966-2-1) for ICC profiles*, color.org. — The sRGB transfer function and primaries, restated from the standard by the body that maintains ICC profiles. §A.7 gives the XYZ(D65) → linear sRGB matrix; **§A.8 "Color component transfer function" gives the ENCODING equations and Part B "Hints for profile makers" gives only the DECODING inverse** — this entry and `mask-to-material.md` both credited §B with both halves. ⚠️ Do not "correct" the corpus's constants against this artefact: the ICC note itself misprints the blue inverse as `BL = B/12.02`, where 12.92 is right. §B gives the encoding and decoding equations with the 0.0031308 / 0.04045 thresholds, the 12.92 slope, the 0.055 offset and the 2.4 exponent. `F` because it is a standards-body technical note, not peer review, and because the normative document it restates — IEC 61966-2-1 — is paywalled and was not opened.
- **srgb1996** `F` — Stokes, M., Anderson, M., Chandrasekar, S. & Motta, R. (1996). *A Standard Default Color Space for the Internet — sRGB*, version 1.10, W3C Note. — The original proposal. Cited here only for the warning W3C now prints at the top of it: the document is obsolete, sRGB was standardised as IEC 61966-2-1, and "during standardization, a small numerical error caused by rounding error was corrected". That is the provenance of every slightly-different set of sRGB constants in circulation. The equations themselves are images in the HTML and were not read as text, which is why icc_srgb is cited for the numbers instead.
