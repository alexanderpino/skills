---
type: Bibliography
title: Papers — rendering
description: "Sources for the rendering axis: heightfield LOD, streaming, virtual texturing, GPU-driven submission, planetary precision, water surfaces, caustics, and ray marching."
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

## Attribution corrections specific to this axis

Each of these sends an implementer to the wrong place.

| Common claim | Reality |
|---|---|
| "Geometry clipmaps — Losasso & Hoppe 2004", meaning the *toroidal* texture update | losasso2004 is the nested-ring geometry scheme. The toroidal texture update, the degenerate-triangle ring stitching, and the GPU-resident form are **asirvatham2005** — a different publication, a year later, by different authors. Cite only the 2004 paper and the implementer misses the mechanism that makes it run. |
| "Chunked LOD — Ulrich, SIGGRAPH 2002" | It is a SIGGRAPH **course note**, not a SIGGRAPH paper. Tier `F`. The technique is real and universal; the venue is not peer review. Same for Tessendorf's ocean notes, which the wave-model documents own. |
| "Real-time engines compute caustics" | Almost none do. The shipped default is an authored looping texture projected down the light direction — an *animation*, with no dependence on the water surface that supposedly focused it. The image-space caustic-map lineage (wyman2006, shah2007) is the cheapest thing that is actually a caustic. |
| "Opacity micromaps let ray tracing follow a deforming heightfield" | Category error. Opacity micromaps classify **alpha coverage** for traversal; they encode no displacement and track no height edits. See dxrspec, and keep the ray-tracing proxy contract. |

## Heightfield LOD

- **duchaineau1997** `P` — Duchaineau, M., Wolinsky, M., Sigeti, D.E., Miller, M.C., Aldrich, C. & Mineev-Weinstein, M.B. (1997). *ROAMing terrain: real-time optimally adapting meshes.* IEEE Visualization '97, 81–88. — Longest-edge-bisection binary triangle tree with frame-coherent split/merge priority queues.
- **deboer2000** `F` — de Boer, W.H. (2000). *Fast terrain rendering using geometrical mipmapping.* Self-published whitepaper (flipcode). — Geomipmapping: fixed chunks, per-chunk mip chain, index-buffer edge stitching. No venue and no review; universally cited anyway.
- **ulrich2002** `F` — Ulrich, T. (2002). *Rendering massive terrains using chunked level of detail control.* SIGGRAPH 2002 course notes. — Chunked LOD: quadtree of pre-simplified static chunks, per-chunk maximum geometric error, skirts, per-chunk geomorph. Course notes, not peer review.
- **losasso2004** `P` — Losasso, F. & Hoppe, H. (2004). *Geometry clipmaps: terrain rendering using nested regular grids.* ACM TOG 23(3), SIGGRAPH '04, 769–776. — Nested viewer-centred rings, each 2× coarser, with a transition region on each ring's fringe.
- **asirvatham2005** `F` — Asirvatham, A. & Hoppe, H. (2005). *Terrain rendering using GPU-based geometry clipmaps.* GPU Gems 2, ch. 2, NVIDIA/Addison-Wesley. — The GPU form: heights in a texture updated toroidally, degenerate-triangle ring stitching. Book chapter.
- **strugar2009** `F` — Strugar, F. (2009). *Continuous distance-dependent level of detail for rendering heightmaps (CDLOD).* Whitepaper. — Quadtree selection over one shared grid mesh, with a per-vertex distance morph that makes a node vertex-identical to its parent at the range boundary. A journal version is often cited; the whitepaper is the artefact.
- **dupuy2020** `P` — Dupuy, J. (2020). *Concurrent binary trees (with application to longest edge bisection).* Proceedings of the ACM on Computer Graphics and Interactive Techniques 3(2) (HPG 2020), art. 20. — A GPU-resident bitfield binary tree: lock-free split/merge from thousands of threads, O(1) leaf enumeration for indirect draw.

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

- **upchurch2012** `P` — Upchurch, P. & Desbrun, M. (2012). *Tightening the precision of perspective rendering.* Journal of Graphics Tools 16(1), 40–56. — Error analysis of the depth transform: why a reversed-Z mapping into a floating-point depth buffer keeps relative error near-constant across the whole range.
- **reed2015** `F` — Reed, N. (2015). *Depth precision visualized.* Public write-up. — The standard practical explanation of the float-depth / reversed-Z interaction. Blog post.
- **epiclwc** `F` — Epic Games. *Large World Coordinates* documentation, Unreal Engine 5. — Engine-native double-precision world transforms, and the shader-side paths that still break. Engine documentation.

## Water surfaces

The wave field itself, the dispersion relation, and the absorption law belong to the water-physics
documents on the simulation axis. What is listed here is what a *renderer* consumes.

- **bruneton2010** `P` — Bruneton, E., Neyret, F. & Holzschuch, N. (2010). *Real-time realistic ocean lighting using seamless transitions from geometry to BRDF.* Computer Graphics Forum 29(2) (Eurographics), 487–496. — The slope-variance tensor that carries unresolved wave detail out of geometry and into the BRDF, the roughness-aware Fresnel fit, and the solar-disc clamp on variance.
- **coxmunk1954** `P` — Cox, C. & Munk, W. (1954). *Measurement of the roughness of the sea surface from photographs of the sun's glitter.* Journal of the Optical Society of America 44(11), 838–850. — Mean-square sea-surface slope regressed on wind speed, anisotropic along and across wind, plus the slicked-water measurements. Wind is referenced at 12.5 m, and the fit covers 1–14 m/s only.
- **ross2005** `P` — Ross, V., Dion, D. & Potvin, G. (2005). *Detailed analytical approach to the Gaussian surface bidirectional reflectance distribution function specular component applied to the sea surface.* JOSA A 22(11), 2442–2453. — The Gaussian-slope microfacet BRDF with Smith masking that a statistical glitter model evaluates.
- **dupuy2012** `P` — Dupuy, J. & Bruneton, E. (2012). *Real-time animation and rendering of ocean whitecaps.* SIGGRAPH Asia 2012 Technical Briefs, art. 15. — Prefilterable whitecap coverage as an error function over the footprint mean and variance of the displacement Jacobian.
- **monahan1980** `P` — Monahan, E.C. & O'Muircheartaigh, I. (1980). *Optimal power-law description of oceanic whitecap coverage dependence on wind speed.* Journal of Physical Oceanography 10(12), 2094–2099. — `W = 3.84e-6 · U^3.41`, U at 10 m: how much foam a given wind owes you.
- **deliot2023** `P` — Deliot, T. & Belcour, L. (2023). *Real-time rendering of glinty appearances using distributed binomial laws on anisotropic grids.* Computer Graphics Forum 42(8) (HPG 2023). — Counting the facets inside a pixel footprint that reflect toward the eye; the discrete-glint tier above a statistical BRDF.
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
- **dummer2006** `F` — Dummer, J. (2006). *Cone step mapping: an iterative ray-heightfield intersection algorithm.* Self-published whitepaper. — A per-texel empty-cone opening as a provably safe step bound; the relaxed variant trades one overshoot for far fewer steps. Distributed largely via GPU Gems 3 ch. 18.
- **drobot2010** `F` — Drobot, M. (2010). *Quadtree displacement mapping with height blending.* GPU Pro 1 / GDC 2010. — The max-mip pyramid applied to material displacement, and the height-blend compositor beside it. Book chapter and conference talk.
- **smacke** `F` — s-macke. *VoxelSpace* — algorithm reconstruction and reference implementation, github.com/s-macke/VoxelSpace. — Column raycasting with the ascending y-buffer, as shipped in Comanche (1992). A repository, and the canonical modern reconstruction of a technique whose original has no publication.
- **dxrspec** `F` — Microsoft *DirectX Raytracing (DXR)* specification and the Khronos `VK_EXT_opacity_micromap` / `VK_NV_displacement_micromap` registry entries. — Intersection shaders for procedural AABB geometry, BLAS build-versus-refit semantics, and what opacity micromaps do and do not classify. API specifications.
