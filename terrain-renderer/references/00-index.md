# Technique Index

The skill's map of its own knowledge. Every row carries a **provenance tier**, because the
failure mode this file exists to prevent is *confident fabrication of a citation* — and this
domain is unusually exposed to it: terrain rendering's canon lives disproportionately in GDC
and SIGGRAPH-Advances talks, vendor docs, and community blog posts, not peer-reviewed papers.
Present it that way.

## Provenance tiers

| Tier | Meaning | How to talk about it |
|---|---|---|
| **P** | **Paper/book.** Peer-reviewed or formally published, widely known to contain the technique. | Cite it directly — but see the verification status below. |
| **T** | **Talk.** GDC / SIGGRAPH Advances / vendor conference presentation. | "Presented in <talk>"; never dress as peer review. Slides may be offline; ideas are the citation. |
| **D** | **Docs.** Official vendor or engine documentation. | Cite the docs; flag that engine docs drift by version. |
| **F** | **Folklore.** Universal practice with no canonical source; a blog post, a repo, or nothing. | "No canonical paper; standard practice is…". Naming a blog (e.g. 0fps) is fine — as a blog. |
| **N** | **Named feature.** An engine's or game's branding over one or more techniques. | Name the underlying technique family. |
| **?** | **Claimed but unverified.** Plausible, commonly repeated, not confirmed. | **Do not cite.** Say it needs checking, and search if you can. |

**Never upgrade a tier to satisfy a question.** If someone asks for "the Nanite paper", the
correct answer is that there isn't one — it is a SIGGRAPH Advances talk (T) plus shipped code —
not a plausible-looking citation. If a question lands on `?`, say so and offer to search.

## Verification status — read before citing anything

The master index below went through a web-verification pass in **2026-07**: for every row that
carries a URL in the `Link` column, the author/year/venue attribution was checked against a
search-engine result or a fetch of a prominent source (publisher page, JCGT, ACM DL,
advances.realtimerendering.com, author sites, engine docs), and corrections found during that
pass were applied in place (see the ledger for which flagged doubts were resolved). Rows whose
`Link` cell is an em-dash were **not** web-checked and remain model-knowledge-only — treat their
author/year details as "believed correct". Two further caveats: (1) the pass verified
*attributions*, not content — **numeric constants and mechanism details inside the chapters have
not been checked against the primary sources**; (2) engine-doc links (Epic, Unity, Microsoft)
are version-sensitive and drift. When you verify a further row, upgrading this file is the
right fix.

## Where a chapter is more than one file

Most chapters are one file, and the `Chapter` column below names it directly. **`12` is three**,
and a route to "chapter 12" means whichever of them holds the answer:

| File | Holds | Go there for |
|---|---|---|
| `12-water-rendering.md` | The chapter itself: doctrine, mechanisms, the **diagnostic index** near its front (symptom on screen → mechanism → section), and the pitfall catalogue | Everything by default |
| `12a-water-derivations.md` | The **mathematics and pseudocode** behind results the chapter quotes in a line | Re-deriving a number, or carrying one to different constants |
| `12b-water-provenance.md` | **Sources & provenance for all of `12`**: every tier, every citation, every `?`, and the `P/T/D/F/N/?` convention restated so it reads alone | Before citing anything out of `12` — including the rows tagged `12` in the table below |

`12`'s executable half is `terrain-renderer/reference-impl/`, and its `validate.py` is the arbiter
for the chapter's numeric claims: it checks the implementation against closed forms, published
measurements and independent methods. It **exited non-zero on eight rows** for several rounds — each
a recorded finding with its tolerance justified from the estimator's own error, not a broken build —
and all eight are now closed, with no tolerance widened and four of them tightened.

## Figures, and the chapters that deliberately have none

Every image in `references/` is drawn by the single script
[`figures/make_figures.py`](figures/make_figures.py), which imports the implementation **read-only**
and writes no physics of its own, so a figure cannot drift from the code that ships. Captions live
in the markdown beside the image, never in the pixels, where they can be read, diffed and corrected.

```
python3 terrain-renderer/references/figures/make_figures.py             # redraw all thirteen
python3 terrain-renderer/references/figures/make_figures.py --selftest  # prove the guard can fail
```

| Chapter | Figures | The shape each one carries |
|---|---|---|
| `09` | 3 | The float32 spacing **staircase** against the smooth law that bounds it; reversed-Z **flat over seven decades** while three other curves climb as one; the cube-sphere's two mappings, and the direction each is worst in |
| `10` | 3 | The Rayleigh aureole's **ceiling of ½** with the shipped constant above it; the two receiver weights, **equal in area and nothing else**; an `acos` **folding** about solar noon |
| `12`, `12a` | 6 | Two Fresnel constants from one surface; a product that is not a mean; a series and its bound; a distribution painted where its realisation belongs; Sommerfeld's exact half; a width that is a function |
| `19` | 1 | The Kelvin wedge as a **ratio**, self-similar in `V·t`, and the capillary band where the ratio leaves ½ |

**The twenty-chapter gap is deliberate elsewhere, and the reasons are the useful part.** A figure
earns its place when a claim has a **shape** — a curve that crosses, two factors that diverge, a
distribution against a realisation, a bound something clears. It does not earn its place when the
claim is a number, a table or an identity. Recorded so a later round does not re-litigate them:

| Chapter | Considered | Rejected because |
|---|---|---|
| `01` | The T-junction sparkle — a vertex exactly on a coarse edge that still leaks | Real, and drawable, but only by putting a **rasterizer inside the generator**. The generator's charter is that it contains no implementation; a figure is not worth breaking it for |
| `01` | Distance-to-centre vs distance-to-closest-point; the CDLOD morph shortfall | `d_centre/d_nearest` is a ratio of two lengths and the crack from `morphK = 0.98` is `(1 − morphK)·Δh` — both are **identities**, and their pictures are a hyperbola and a straight line |
| `06` | Ring cut vs whole pyramid resident | A geometric series against a constant one — an identity. Every number in the worked example is a **chosen parameter with no implementation behind it**, so the figure would re-typeset a table. Checking the table instead of drawing it found an arithmetic error the picture would have inherited (the ring column sums to ~205 tiles, not 255) |
| `07` | The mip halo from independently filtered weights and content | The defect is real and is the same class as `12`'s slope filtering, but showing it needs an **invented weight ramp and two invented layer colours**. "Same mathematics as non-premultiplied alpha halos" already names a known class, which is sharper than a picture of this file's own test case |
| `08` | The HiZ footprint's mip selection | Suspected the stated rule under-samples straddling rects. **Checked it: the rule is sound** — `ceil(log2 w)` puts the rect at ≤1 texel, so a 2×2 fetch always spans it. No figure, and no correction needed |
| `08` | LOD/occlusion hysteresis as a loop | "Split at `tau`, merge at `tau·h`" is already the clearest statement; the loop adds a rectangle |
| `10` | CSM split schemes: uniform vs log vs the `lambda` blend | The **strongest rejection in the set**, and the closest call. It has a genuine shape — texels-per-screen-pixel diverging by orders of magnitude near the camera — but near, far, cascade count and shadow resolution would all be **numbers this file chose**, with nothing shipping behind them. The round's rule is that a figure's numbers come from something that ships |
| `11` | Anything | Unchanged from the previous round: "a ratio cannot see a common factor" is an algebraic identity, and a picture would illustrate the scene rather than the mechanism |
| `19` | Particle count scaling with volume | `8×` for a doubled linear size is a cube law stated in four words |

The remaining chapters — `02`–`05`, `13`–`18` — have no implementation behind their quantitative
claims anywhere in this skill, which is the same reason and the one the project's contract already
names as its largest unproven region. **An invented number in a figure is worse than no figure.**

## Master technique index

| Technique / topic | Chapter | Canonical source | Tier | Link |
|---|---|---|---|---|
| Screen-space geometric error (ρ = e·K/d) | `01` | Standard across LOD literature; formalized in Cozzi & Ring, *3D Engine Design for Virtual Globes* (2011) | P | [virtualglobebook.com](https://virtualglobebook.com/) |
| ROAM (split/merge bintrees) | `01` | Duchaineau, Wolinsky, Sigeti, Miller, Aldrich & Mineev-Weinstein, IEEE Visualization '97 | P | [IEEE Xplore](https://ieeexplore.ieee.org/document/663860/) |
| Geomipmapping | `01` | de Boer 2000 (web-published paper, flipcode) | P/F | [flipcode PDF](https://www.flipcode.com/archives/article_geomipmaps.pdf) |
| Chunked LOD | `01` | Ulrich, SIGGRAPH 2002 course ("Super-size it! Scaling up to Massive Virtual Worlds") | T | [tulrich.com](https://tulrich.com/geekstuff/chunklod.html) |
| Geometry clipmaps | `01` | Losasso & Hoppe, SIGGRAPH 2004 (ACM TOG 23(3)); GPU version in GPU Gems 2 | P | [hhoppe.com](https://hhoppe.com/proj/geomclipmap/) |
| CDLOD (quadtree + per-vertex morph) | `01` | Strugar 2009, *Journal of Graphics, GPU, and Game Tools* 14(4); whitepaper + code self-published | P | [github.com/fstrugar/CDLOD](https://github.com/fstrugar/CDLOD) |
| Hardware tessellation terrain | `01` | DX11-era vendor samples | D/T | — |
| CBT/LEB (GPU subdivision) | `01` | Dupuy, HPG 2020 (PACM CGIT) | P | [onrendering.com PDF](https://onrendering.com/data/papers/cbt/ConcurrentBinaryTrees.pdf) |
| Skirts / stitching / morph / matched factors (crack taxonomy) | `01` | Folklore, consolidated | F | — |
| Hex-lattice triangulation (corner-only 2N / center-fan 3N / flat prism) | `01` | terrain-architect `26` catalog, restated render-side | D | — |
| Cluster DAG build (group→simplify→split), monotonic error | `02` | Karis, Stubbe & Wihlidal, "Nanite: A Deep Dive", SIGGRAPH 2021 Advances | T | [advances.realtimerendering.com](https://advances.realtimerendering.com/s2021/Karis_Nanite_SIGGRAPH_Advances_2021_final.pdf) |
| Two-phase HiZ occlusion culling | `02` `08` | Nanite talk lineage + community practice | T/F | [advances.realtimerendering.com](https://advances.realtimerendering.com/s2021/Karis_Nanite_SIGGRAPH_Advances_2021_final.pdf) |
| Software raster of micro-triangles, 64-bit visibility buffer | `02` | Karis, Stubbe & Wihlidal 2021 | T | [advances.realtimerendering.com](https://advances.realtimerendering.com/s2021/Karis_Nanite_SIGGRAPH_Advances_2021_final.pdf) |
| Visibility buffer (deferred material shading) | `02` `07` `08` | Burns & Hunt, JCGT 2(2), 2013 | P | [jcgt.org](https://jcgt.org/published/0002/02/04/) |
| Meshlets / mesh shaders | `02` | Vendor docs; meshoptimizer | D/F | [github.com/zeux/meshoptimizer](https://github.com/zeux/meshoptimizer) |
| QEM simplification | `02` | Garland & Heckbert, SIGGRAPH 1997 | P | [ACM DL](https://dl.acm.org/doi/10.1145/258734.258849) |
| Progressive meshes / view-dependent refinement (runtime edge collapse — historical; lineage of the DAG cut) | `02` | Hoppe, SIGGRAPH 1996 & 1997 | P | [hhoppe.com](https://hhoppe.com/proj/vdrpm/) |
| UE Landscape (components/sections, LOD, weightmaps) | `03` | Epic docs | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-technical-guide-in-unreal-engine) |
| Nanite Landscape, Nanite displacement | `03` | Epic docs — version-sensitive, re-verify | D/N/? | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-nanite-with-landscapes-in-unreal-engine) |
| Runtime Virtual Texture (RVT) | `03` `07` | Epic docs | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/runtime-virtual-texturing-in-unreal-engine) |
| World Partition / HLOD / LWC | `03` | Epic docs | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition-in-unreal-engine) |
| Unity Terrain, Godot Terrain3D, O3DE Terrain | `03` | Engine docs / community | D/N | [docs.unity3d.com](https://docs.unity3d.com/Manual/script-Terrain.html) |
| Palette-compressed chunk storage | `04` | Minecraft-lineage community documentation | F/N | — |
| Culled / greedy / binary-greedy meshing | `04` | Lysenko (0fps, 2012) for greedy; community for binary | F | [0fps.net](https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/) |
| Voxel vertex AO (side1+side2+corner, diagonal flip) | `04` | Lysenko (0fps, 2013) | F | [0fps.net](https://0fps.net/2013/07/03/ambient-occlusion-for-minecraft-like-worlds/) |
| Flood-fill sky/block lighting (0–15) | `04` | Minecraft-lineage community documentation; Lysenko (0fps) consolidation | F/N | [0fps.net](https://0fps.net/2018/02/21/voxel-lighting/) |
| Cave culling via chunk-face connectivity | `04` | Checchi (Mojang), "The Advanced Cave Culling Algorithm", blog 2014 | F | [tomcc.github.io](https://tomcc.github.io/2014/08/31/visibility-1.html) |
| Multi-draw indirect chunk submission, vertex pooling | `04` `08` | Community practice | F | — |
| Distant voxel LOD (downsampled far pipeline) | `04` | Distant Horizons et al. | N/F | [gitlab.com](https://gitlab.com/distant-horizons-team/distant-horizons) |
| Sparse voxel octrees | `04` | Laine & Karras, I3D 2010 | P | [ACM DL](https://dl.acm.org/doi/10.1145/1730804.1730814) |
| Weighted-blended OIT | `04` | McGuire & Bavoil, JCGT 2(2), 2013 | P | [jcgt.org](https://jcgt.org/published/0002/02/09/) |
| Marching cubes (+ asymptotic decider) | `05` | Lorensen & Cline, SIGGRAPH 1987; Nielson & Hamann, IEEE Visualization '91 (1991) | P | [ACM DL](https://dl.acm.org/doi/10.1145/37402.37422) |
| MC lookup tables (canonical public source) | `05` | Bourke, "Polygonising a Scalar Field" (1994; tables by Bloyd) | F/D | [paulbourke.net](https://paulbourke.net/geometry/polygonise/) |
| Surface nets | `05` | Gibson 1998, "Constrained Elastic Surface Nets", MICCAI '98; naive form Lysenko (0fps) | P/F | [Springer](https://link.springer.com/chapter/10.1007/BFb0056277) |
| Dual contouring (hermite + QEF) | `05` | Ju, Losasso, Schaefer & Warren, SIGGRAPH 2002 | P | [ACM DL](https://dl.acm.org/doi/10.1145/566570.566586) |
| Transvoxel transition cells | `05` | Lengyel 2010, UC Davis dissertation ("Voxel-Based Terrain for Real-Time Virtual Simulations"); transvoxel.org | P/D | [transvoxel.org](https://transvoxel.org/) |
| GPU isosurface extraction (classify→scan→generate) | `05` | Community/vendor practice | F/D | — |
| Tile pyramid + SSE refinement, residency state machine | `06` | Cozzi & Ring 2011 + industry practice | P/F | [virtualglobebook.com](https://virtualglobebook.com/) |
| DirectStorage-era streaming IO | `06` | Vendor docs | D | [github.com/microsoft/DirectStorage](https://github.com/microsoft/DirectStorage) |
| HLOD / far-world baking | `06` | Industry talks (various) | T/F | — |
| Detail texturing (high-frequency tiled modulation over macro color) | `07` | Fixed-function multitexture lineage; no single terrain-specific canonical source | F/D | — |
| Alpha/weight splatting | `07` | Crawfis & Max, "Texture Splats for 3D Scalar and Vector Field Visualization", IEEE Visualization 1993; terrain adaptation is industry practice | P/F | [IEEE Xplore](https://ieeexplore.ieee.org/document/398679/) |
| Splat blending: height-lerp, weight packing, mip halos | `07` | Folklore | F | — |
| Stochastic texturing (histogram-preserving blending) | `07` | Heitz & Neyret, HPG 2018 (PACM CGIT) | P | [eheitzresearch.wordpress.com](https://eheitzresearch.wordpress.com/722-2/) |
| Hex-tiling | `07` | Mikkelsen, "Practical Real-Time Hex-Tiling", JCGT 11(3), 2022 | P | [jcgt.org](https://jcgt.org/published/0011/03/05/) |
| Triplanar / biplanar projection | `07` | Folklore; Quilez writeups | F | — |
| Reoriented Normal Mapping & normal-blend family (formulas inlined in `07`) | `07` | Barré-Brisebois & Hill, "Blending in Detail", 2012 | D/F | [selfshadow.com](https://blog.selfshadow.com/publications/blending-in-detail/) |
| Virtual texturing (page tables, feedback, transcode) | `07` | id Tech MegaTexture lineage; Mittring "Advanced Virtual Texture Topics" (SIGGRAPH 2008) & van Waveren talks | T | [advances.realtimerendering.com](https://advances.realtimerendering.com/s2008/SIGGRAPH%202008%20-%20Advanced%20virtual%20texture%20topics.pdf) |
| id Tech MegaTexture (unique authored surface streamed as pages) | `07` | id Software / van Waveren and Mittring talk lineage | T/N | [advances.realtimerendering.com](https://advances.realtimerendering.com/s2008/SIGGRAPH%202008%20-%20Advanced%20virtual%20texture%20topics.pdf) |
| Runtime virtual texturing as cached material composition | `03` `07` `13` `17` | Epic docs; dynamic-state exclusion is this skill's cache doctrine | D/N/F | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/runtime-virtual-texturing-in-unreal-engine) |
| Clipmap texturing | `07` | Tanner, Migdal & Jones, SIGGRAPH 1998 | P | [ACM DL](https://dl.acm.org/doi/10.1145/280814.280855) |
| GPU-driven pipelines (persistent scene, indirect subm.) | `08` | Haar & Aaltonen, SIGGRAPH 2015 Advances | T | [advances.realtimerendering.com](https://advances.realtimerendering.com/s2015/aaltonenhaar_siggraph2015_combined_final_footer_220dpi.pdf) |
| Terrain max-mip pyramid as long-range occluder | `08` | Industry practice | F/T | — |
| Work graphs / device-generated commands | `08` | D3D12/Vulkan docs — production maturity `?` | D/? | [DirectX-Specs](https://microsoft.github.io/DirectX-Specs/d3d/WorkGraphs.html) |
| Camera-relative rendering / origin rebasing / RTE | `09` | Cozzi & Ring 2011 + folklore | P/F | [virtualglobebook.com](https://virtualglobebook.com/) |
| Reversed-Z floating-point depth | `09` | Community canon; Reed, "Depth Precision Visualized" (NVIDIA dev blog) is the widely cited analysis | F/D | [developer.nvidia.com](https://developer.nvidia.com/blog/visualizing-depth-precision/) |
| Logarithmic depth | `09` | Outerra-lineage community practice | F | — |
| Cube-sphere quadtrees, per-patch local frames | `09` | Cozzi & Ring 2011 + industry practice | P/F | [virtualglobebook.com](https://virtualglobebook.com/) |
| Horizon culling (ellipsoid occlusion) | `09` | Cozzi & Ring 2011 | P | [virtualglobebook.com](https://virtualglobebook.com/) |
| Cascaded shadow maps (splits, snapping) | `10` | Engel/vendor lineage; split-scheme literature; Microsoft CSM technical article | P/F | [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/cascaded-shadow-maps) |
| Horizon mapping (baked terrain shadows) | `10` | Max 1988, *The Visual Computer* 4 | P | [Springer](https://link.springer.com/article/10.1007/BF01905562) |
| Heightfield ray-marched shadows | `10` | Engine features + community practice | N/F | — |
| Virtual shadow maps | `10` | Epic docs | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine) |
| Aerial perspective / sky LUTs | `10` | Hillaire, EGSR 2020 (CGF 39(4)) | P | [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.14050) |
| Rayleigh/Mie atmosphere scattering for realtime skies | `10` | Bruneton & Neyret 2008 lineage; Hillaire 2020 production model | P | [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.14050) |
| Failure catalogue, debug views, budget assertions | `11` | This skill's consolidation | F | — |
| FFT/spectral ocean synthesis | `12` | Tessendorf, "Simulating Ocean Water", SIGGRAPH course notes | T/P | [clemson.edu PDF](https://people.computing.clemson.edu/~jtessen/reports/papers_files/coursenotes2004.pdf) |
| Gerstner/trochoidal wave sums | `12` | Classical; GPU form in GPU Gems ch. 1 (Finch) | F/D | [developer.nvidia.com](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models) |
| UE Water plugin: bounded water zone, sparse quadtree water mesh, fused top-down water-info capture | `12` `03` | Epic docs (fetched 2026-08) — version-sensitive | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-meshing-system-and-surface-rendering-in-unreal-engine) |
| Single Layer Water (opaque surface + participating-medium pass after deferred lighting) | `12` | Epic docs | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/single-layer-water-shading-model-in-unreal-engine) |
| Spline water bodies carving terrain via Landscape edit layers (Landmass brushes) | `03` `12` | Epic docs | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-body-actors-in-unreal-engine) |
| Landscape Blueprint Brush family: Landscape Splines (per-point width/falloff, cosine edge, layer painting) and Landmass custom brushes (falloff angle, blend mode, capped/uncapped) — curve brushes are general, water is one instance | `03` | Epic docs via search summaries — property names `?` per version | D/N/? | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-splines-in-unreal-engine) |
| Gerstner wave *data asset* with a shared CPU/GPU evaluator | `12` `19` | Epic docs | D/N | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/simulating-waves-using-the-water-waves-asset-in-unreal-engine) |
| Amortized CPU buoyancy queries (points-per-frame, frames-pause) | `19` | Epic Water docs via search; technique is standard practice | D/F/? | — |
| Flow mapping (rivers) | `12` | Vlachos, "Water Flow in Portal 2", SIGGRAPH 2010 | T | [steamstatic PDF](https://cdn.akamai.steamstatic.com/apps/valve/2010/siggraph2010_vlachos_waterflow.pdf) |
| Projected-grid water surface | `12` | Johanson, Lund University master's thesis, 2004 | P | [lth.se PDF](https://fileadmin.cs.lth.se/graphics/theses/projects/projgrid/projgrid-lq.pdf) |
| Linear (Airy) wave theory: dispersion, shoaling (Green's law), refraction | `12` | Coastal-engineering canon; textbook treatment in Dean & Dalrymple, *Water Wave Mechanics for Engineers and Scientists* (1991) | P | — |
| Breaker criterion (H ≈ 0.78·h) & surf-similarity breaker classification (Iribarren ξ) | `12` | McCowan lineage; Battjes, "Surf Similarity", Coastal Engineering Conference 1974 | P | — |
| Wave–current interaction (Doppler-shifted dispersion, blocking at group speed) | `12` | Peregrine, "Interaction of Water Waves and Currents", *Advances in Applied Mechanics* 16, 1976 | P | [Semantic Scholar](https://www.semanticscholar.org/paper/Interaction-of-Water-Waves-and-Currents-Peregrine/ead4947119505f48eaa8adaa4a3d78da7c722fad) |
| Wave particles (Lagrangian wave carriers → height field) | `12` | Yuksel, House & Keyser, SIGGRAPH 2007 (ACM TOG 26(3)) | P | [cemyuksel.com](https://www.cemyuksel.com/research/waveparticles/) |
| Wave packets / water surface wavelets (dispersive Lagrangian wave groups) | `12` | Jeschke & Wojtan, SIGGRAPH 2017; Jeschke, Skřivan, Müller-Fischer, Chentanez, Macklin & Wojtan, SIGGRAPH 2018 | P | [ACM DL](https://dl.acm.org/doi/10.1145/3197517.3201336) |
| Shipped shore/ocean water systems (ocean mesh LOD + flow shader; stylized FFT + shore treatment) | `12` | Gonzalez-Ochoa, "Water Technology of Uncharted", GDC 2012; Ang, Catling, Ciardi & Kozin, "The Technical Art of Sea of Thieves", SIGGRAPH 2018 Talks | T | [gdcvault.com](https://gdcvault.com/play/1015309/Water-Technology-of) |
| Travel-time (eikonal) shore phase fields, breaker-profile authoring, group-envelope sets | `12` | Production practice, no canonical source | F | — |
| Fullscreen-triangle pass (screen-space water, skybox, aux composites) | `12` `16` `10` | Community canon (Bilodeau GDC 2014 vertex-shader-tricks lineage; multiple writeups) | F/T | [slideshare Bilodeau](https://www.slideshare.net/DevCentralAMD/vertex-shader-tricks-bill-bilodeau) |
| Cloud shadows (projected scrolling coverage) | `10` | Standard practice, no canonical source | F | — |
| Volumetric cloudscapes (terrain seams: depth, one sky state) | `10` | Schneider, "The Real-Time Volumetric Cloudscapes of Horizon Zero Dawn", SIGGRAPH 2015 Advances | T | [advances.realtimerendering.com](https://advances.realtimerendering.com/s2015/The%20Real-time%20Volumetric%20Cloudscapes%20of%20Horizon%20-%20Zero%20Dawn%20-%20ARTR.pdf) |
| God rays: screen-space post-process form | `10` | Mitchell, "Volumetric Light Scattering as a Post-Process", GPU Gems 3 ch. 13 | P/D | [developer.nvidia.com](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process) |
| Ocean/water shading (Bruneton model family) | `12` | Bruneton, Neyret & Holzschuch, CGF 29(2), 2010 | P | [inria.hal.science](https://inria.hal.science/inria-00443630) |
| Image-space caustic maps (refract from the light's view, splat receiver positions) | `12` | Shah, Konttinen & Pattanaik, *IEEE TVCG* 13(2), 2007, 272–280; Wyman & Davis, I3D 2006, 153–160 | P | [IEEE Xplore](https://ieeexplore.ieee.org/document/4069236/) |
| Water caustics, practical/aesthetic build | `12` | Guardado & Sánchez-Crespo, "Rendering Water Caustics", GPU Gems 1 ch. 2 — self-described as aesthetics-driven, not physical | D/F | [developer.nvidia.com](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics) |
| Caustic structure: brightness as inverse ray-map Jacobian; folds and cusps only (the argument against Voronoi caustics) | `12` | Whitney, *Annals of Mathematics* 62 (1955) for the fold/cusp classification; Berry & Upstill, "Catastrophe Optics", *Progress in Optics* 18 (1980), 257–346 for the optics reading | P | [ADS](https://ui.adsabs.harvard.edu/abs/1980PrOpt..18..257B/abstract) |
| Offline-correct caustics (photon mapping, manifold methods, the `SDS` limit) | `12` → PBR | Routed out: `physically-based-rendering/references/caustics.md` | P | — |
| Water vocabulary: OpenPBR Surface names the boundary (`transmission_color`/`transmission_depth` as Beer–Lambert, `specular_ior`, `base_color`), ocean optics' inherent/apparent optical properties name the medium (`a`, `b`, `b_b`, `c`, `g`) and what a renderer computes from it (`K_d`, reflectance) | `12` | OpenPBR Surface specification; Preisendorfer's IOP/AOP division as standard ocean-optics usage (attribution to *Hydrologic Optics* not chased, `?`). MaterialX checked and found to name the medium's optics only (`anisotropic_vdf`: `absorption`/`scattering`/`anisotropy`) and no bounded body, depth field or pass vocabulary | P/? | [materialx.org PBR spec](https://materialx.org/assets/MaterialX.v1.38.PBRSpec.pdf) |
| Man-made water bodies (pools, tanks, canals): which bands gate off; colour as bottom albedo, not scattering | `12` | This skill's composition over the Pope & Fry pure-water absorption already cited in `12`; the body-type extension is authored-side, never classified by terrain-architect `03` | F | — |
| Driven-basin pool wave field: two-band split (jet-driven long band + wind short band), shelter on the short band only, reverberant wall reflections, submerged-jet footprint and its ±19° downstream wake baked per fitting | `12` | This skill's composition over classical results (Lamb viscous decay, free-shear-jet scaling, capillary–gravity minimum phase speed, wave–current ray theory); no canonical source for the pool application — see the ledger | P/F/? | — |
| Deferred snow/mud deformation | `13` | Michels & Sikachev, GPU Pro 7 (talk form SIGGRAPH 2015); Barré-Brisebois, GDC 2014 (Batman); Surricchio, GDC 2023 (God of War Ragnarök) | P/T | [gdcvault Batman](https://gdcvault.com/play/1020177/Deformable-Snow-Rendering-in-Batman) |
| Wet-surface shading (porosity darkening, roughness drop) | `13` | Lagarde, "Water drop" blog series, 2012–2013 | F/D | [seblagarde.wordpress.com](https://seblagarde.wordpress.com/2013/03/19/water-drop-3a-physically-based-wet-surfaces/) |
| Transient season/weather overlays after RVT | `07` `13` | Cache-coherency doctrine; bounded local invalidation in engine docs, global-state exclusion is practice | D/F | [dev.epicgames.com](https://dev.epicgames.com/documentation/en-us/unreal-engine/runtime-virtual-texturing-in-unreal-engine) |
| Aux-map registry & consumption contract | `14` | terrain-architect `27` (generation-side contract), consumed render-side | D | — |
| GPU-driven procedural placement | `15` | van Muijden, "GPU-Based Run-Time Procedural Placement in Horizon Zero Dawn", GDC 2017 (speaker web-verified 2026-07) | T | [gdcvault.com](https://gdcvault.com/play/1024120/GPU-Based-Run-Time-Procedural) |
| Procedural GPU grass (Bezier blades) | `15` | Wohllaib, "Procedural Grass in Ghost of Tsushima", GDC 2021 Advanced Graphics Summit (speaker web-verified 2026-07); a companion wind talk exists (speaker unverified) | T | [gdcvault.com](https://gdcvault.com/play/1027033/Advanced-Graphics-Summit-Procedural-Grass) |
| Octahedral impostors | `15` | Community canon (shaderbits writeup; engine implementations) | F/N | [shaderbits.com](https://shaderbits.com/blog/octahedral-impostors) |
| Alpha-test mip shrinkage fix (coverage-preserving mips) | `15` | Castaño, The Witness blog, 2010 | F | [the-witness.net](https://the-witness.net/news/2010/09/computing-alpha-mipmaps/) |
| Depth-bias semantics (coplanar geometry) | `17` | Microsoft D3D output-merger docs (formula verified) | D | [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/win32/direct3d11/d3d10-graphics-programming-guide-output-merger-stage-depth-bias) |
| Physics heightfield colliders | `17` | Jolt HeightFieldShape / PhysX PxHeightField docs | D | [jrouwe.github.io](https://jrouwe.github.io/JoltPhysics/class_height_field_shape_settings.html) |
| Async GPU readback for surface queries | `17` | Engine docs (Unity AsyncGPUReadback as the D-tier example) | D/F | [docs.unity3d.com](https://docs.unity3d.com/ScriptReference/Rendering.AsyncGPUReadback.html) |
| Hillshade / derived-field viewport passes | `16` | ESRI hillshade reference; GPU Gems 3 ch. 1 for GPU heightfield derivation | D | [esri.com](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/3d-analyst/how-hillshade-works.html) |
| Heightmap import/export parity (R16 scaling, Y-flip) | `16` | Epic heightmap import docs + tool docs (Gaea) | D | [dev.epicgames.com](https://dev.epicgames.com/documentation/unreal-engine/importing-and-exporting-landscape-heightmaps-in-unreal-engine) |
| UE Mesh Terrain (5.8+, experimental 3D modifier-stack terrain) | `03` | Epic docs (fetched 2026-07) | D/N/? | [dev.epicgames.com](https://dev.epicgames.com/documentation/unreal-engine/mesh-terrain-in-unreal-engine) |
| Voxel Space column raycasting (Comanche family; 2.5D, no true voxels) | `18` | NovaLogic / Freeman, US patent 6,020,893 (fetched); canonical modern writeup s-macke | P/F | [patents.google.com](https://patents.google.com/patent/US6020893A/en) |
| Maximum mipmaps heightfield ray traversal | `18` | Tevs, Ihrke & Seidel, I3D 2008 | P | [ACM DL](https://dl.acm.org/doi/10.1145/1342250.1342279) |
| Relief / parallax occlusion mapping family | `18` | Policarpo et al. I3D 2005 lineage; Tatarchuk POM (I3D 2006) | P | [ACM DL](https://dl.acm.org/doi/10.1145/1053427.1053453) |
| Cone step mapping | `18` | Dummer, via GPU Gems 3 ch. 18's citation (original whitepaper not located) | F/? | [oreilly.com](https://www.oreilly.com/library/view/gpu-gems-3/9780321545428/ch18.html) |
| Quadtree displacement mapping | `18` | Drobot, GDC 2010 / gamedevs.org PDF | T | [gamedevs.org](https://www.gamedevs.org/uploads/quadtree-displacement-mapping-with-height-blending.pdf) |
| Static triangulated RT terrain proxy | `18` | DXR/Vulkan acceleration-structure update constraints + industry practice | D/F | [DirectX-Specs](https://microsoft.github.io/DirectX-Specs/d3d/Raytracing.html) |
| Procedural AABB + intersection shader for RT heightfields | `18` | DXR procedural-geometry sample; Vulkan RT procedural primitive model | D/F | [Microsoft sample](https://github.com/microsoft/DirectX-Graphics-Samples/tree/master/Samples/Desktop/D3D12Raytracing/src/D3D12RaytracingProceduralGeometry) |
| Opacity micromaps (alpha-tested RT geometry; not displacement) | `15` `18` | DXR opacity-micromap support and `VK_EXT_opacity_micromap` | D | [DirectX-Specs](https://microsoft.github.io/DirectX-Specs/d3d/Raytracing.html) |
| Displacement micromaps (terrain trajectory; capability-sensitive) | `18` | `VK_NV_displacement_micromap`; platform support remains non-universal | D/? | [Khronos registry](https://registry.khronos.org/vulkan/specs/1.3-extensions/html/chapters/VK_NV_displacement_micromap.html) |
| Stable semi-Lagrangian grid fluid | `19` | Stam, "Stable Fluids", SIGGRAPH 99, 121–128 | P | [author page](https://www.dgp.toronto.edu/public_user/stam/reality/Research/pub.html) |
| SPH for interactive fluids | `19` | Müller, Charypar & Gross, SCA 2003, 154–159 | P | [EG digital library](https://diglib.eg.org/handle/10.2312/SCA.SCA03.154-159) |
| Position Based Fluids (the games default) | `19` | Macklin & Müller-Fischer, ACM TOG 32(4), SIGGRAPH 2013 | P | [author page](http://blog.mmacklin.com/position-based-fluids/) |
| FLIP in graphics (and sand-as-fluid) | `19` | Zhu & Bridson, ACM TOG 24(3), 965–972, SIGGRAPH 2005 | P | [ACM DL](https://dl.acm.org/citation.cfm?id=1073298) |
| APIC (affine particle-in-cell) | `19` | Jiang, Schroeder, Selle, Teran & Stomakhin, ACM TOG 34(4), Art. 51, 2015 | P | [ACM DL](https://dl.acm.org/doi/10.1145/2766996) |
| MPM for yield-stress / multi-phase materials | `19` | Stomakhin, Schroeder, Chai, Teran & Selle, SIGGRAPH 2013 | P | [Disney Animation](https://disneyanimation.com/publications/a-material-point-method-for-snow-simulation/) |
| Screen-space fluid rendering (curvature flow) | `19` | van der Laan, Green & Sainz, I3D 2009, 91–98 | P | [ACM DL](https://dl.acm.org/doi/10.1145/1507149.1507164) |
| Kelvin wake half-angle `arcsin(1/3) ≈ 19.47°`, speed-independent in deep water | `19` | William Thomson (Kelvin), "On Ship Waves", Proc. IMechE 38, 409–434 (1887) | P | — |
| SPH incompressibility variants (PCISPH / IISPH / DFSPH) | `19` | Solenthaler & Pajarola, ACM TOG 28(3), 2009; Ihmsen et al., IEEE TVCG 20(3), 426–435, 2014; Bender & Koschier, SCA 2015 | P | [DFSPH](https://animation.rwth-aachen.de/publication/054/) |
| Stylized water (authored patterns over unchanged contracts) | `12` | Community canon; Gordon's Wind Waker ocean analysis is the canonical breakdown | F | [medium.com](https://medium.com/@gordonnl/the-ocean-170fdfd659f1) |
| TotK water-resistance physics (projected-area drag) | `19` | Dohta, Takayama & Osada, "Tunes of the Kingdom", GDC 2024 | T | [gdcvault.com](https://gdcvault.com/play/1034667/Tunes-of-the-Kingdom-Evolving) |
| Water as drivable gameplay surface (deterministic waves as collision) | `19` `12` | Wave Race 64 → Mario Kart World lineage; press/footage reconstruction, no first-party talk | F | — |

## Engine & shipped-system crosswalk

Branded system → what it actually is → where in this skill.

| Shipped system | Technique family | Route |
|---|---|---|
| UE Landscape (traditional) | Quadtree-ish per-component grid LOD + geomorph | `03`, theory `01` |
| UE Nanite Landscape | Heightfield converted to cluster DAG per component | `03`, mechanism `02` |
| Unity Terrain | Patch-based grid LOD, instanced draws | `03` appendix |
| Godot Terrain3D (community) | Clipmap-style | `03` appendix, theory `01` |
| Minecraft (Java/Bedrock) | Chunked culled/greedy meshing + flood-fill light + palettes | `04` |
| Distant Horizons (mod) | Separate downsampled far-LOD voxel pipeline | `04` |
| Teardown | Small-voxel ray-marched/hybrid | `04` frontier section |
| Space/planet engines (Outerra, flight sims, space games) | Cube-sphere quadtrees + camera-relative precision | `09`, streaming `06` |
| Cesium / virtual globes | Tile pyramid + SSE + horizon culling | `06`, `09` |
| id Tech MegaTexture | Virtual texturing (streaming VT) | `07` |
| No Man's Sky-class procedural planets | Procedural-on-demand patches + isosurface regions | `09`, `05` |
| Dual Universe / Astroneer-class editable planets | Voxel isosurface (DC/MC family) | `05` |
| Deep Rock Galactic-class fully-diggable worlds | Voxel isosurface everywhere (destruction tier 3) | `05`, ladder `17` |
| Battlefield-class battlefield cratering | Heightfield delta overlays (destruction tier 2) | `17` |
| Comanche / Outcast / Delta Force "voxel" terrain | 2.5D heightmap column raycasting (Voxel Space) — no true voxels | `18` |
| UE 5.8 Mesh Terrain | Experimental 3D modifier-stack terrain rendered through Nanite | `03`, family `02` |
| UE Water plugin (ocean / lake / river / island bodies) | Bounded zone + sparse morphing quadtree surface + fused water-info capture + Gerstner wave asset + single-depth-layer volume pass; bodies carve Landscape through edit layers | `12`, carve side `03` |
| Portal 2 water | Flow mapping over a static surface | `12` |
| Uncharted (3) water | Ocean mesh LOD + wave generation + flow shader; wave-particle lineage claimed but not confirmed against the talk (`?`) | `12` |
| Sea of Thieves water | Stylized FFT cascades + shore/foam treatments | `12` |
| The Wind Waker sea | Authored-pattern stylized water: flat colour + scrolling foam rings consuming the shore-distance field | `12` |
| Zelda: Tears of the Kingdom water | Cel look (community-observed) + projected-area water-resistance physics (GDC 2024) | `12`, `19` |
| Mario Kart World / Wave Race lineage | Water as drivable gameplay surface: deterministic waves as collision + trick ramps; interactive waves as gameplay state | `19`, `12` |
| Rise of the Tomb Raider / Batman: Arkham Origins / GoW Ragnarök snow | Deferred deformation (top-down capture → displacement) | `13` |
| Horizon Zero Dawn / Ghost of Tsushima vegetation | GPU-driven procedural placement + procedural grass | `15` |
| Gaea / World Machine-class tool viewports | Preview pyramid + derived-field passes + shading modes | `16` |

Public technical detail on shipped titles varies wildly; treat specific claims about any one
title as T/F tier unless a named talk is in hand.

## Least-confident-claims ledger

Each chapter ends with `## Sources & provenance` — except `12`, whose appendix outgrew the chapter
and now lives in `12b-water-provenance.md`, with a pointer left at both ends of `12`. The claims
their authors flagged as least certain are consolidated here so a reviewer knows where to spend
verification effort first.

- `01`: GPU Zen 2 compute-tessellation attribution — **resolved 2026-07**: confirmed as
  Khoury, Dupuy & Riccio, "Adaptive GPU Tessellation with Compute Shaders", *GPU Zen 2* (2019);
  author-hosted PDF at [onrendering.com](https://onrendering.com/data/papers/isubd/isubd.pdf).
  Also resolved: CDLOD is not just a whitepaper — Strugar 2009 appeared in *Journal of
  Graphics, GPU, and Game Tools* 14(4) (tier upgraded F/P → P). Still open: CDLOD morph
  pseudocode variable conventions vs the whitepaper; "τ = 2–4 px shipping range" and morph-band
  fractions are folklore numbers; the ~20 km clipmap-vs-quadtree threshold is judgment.
- `02`: attribute-quadrics attribution — **resolved 2026-07**: Garland & Heckbert,
  "Simplifying Surfaces with Color and Texture using Quadric Error Metrics", IEEE
  Visualization '98 (1998). Persistent-threads origin — **resolved 2026-07**: Aila & Laine,
  "Understanding the Efficiency of Ray Traversal on GPUs", HPG 2009. Still open: exact Nanite
  constants (group size, ~128 KB pages, METIS) — verify against the 2021 talk slides (linked
  in the table); hysteresis band k≈1.2 is folklore; visibility-buffer bit layout is
  illustrative.
- `03`: nearly everything version-sensitive is flagged `?` in-chapter — per-component batching
  in current UE, LOD cvar names, Nanite Landscape deformation/ray-tracing behavior per version,
  Nanite tessellation maturity, VHM status, mobile layer limits, O3DE internals.
- `04`: Checchi writeup date — **resolved 2026-07**: "The Advanced Cave Culling Algorithm"
  parts 1–2, tomcc.github.io, 2014-08-31 (developed during Minecraft Pocket Edition 0.9).
  Still open: budget-table magnitudes are order-of-magnitude folklore (±2–3×); Minecraft
  water-surface offset fraction; sky-light propagation specifics are F/N reverse-engineered
  behavior; "greedy win shrinks under smooth lighting" is observation, not measurement.
- `05`: asymptotic-decider venue-year — **resolved 2026-07**: Nielson & Hamann, "The
  Asymptotic Decider: Resolving the Ambiguity in Marching Cubes", IEEE Visualization '91
  (1991). Gibson — **resolved 2026-07**: "Constrained Elastic Surface Nets: Generating Smooth
  Surfaces from Binary Segmented Data", MICCAI '98, Springer LNCS 1496. Lengyel dissertation —
  **resolved 2026-07**: "Voxel-Based Terrain for Real-Time Virtual Simulations", UC Davis,
  2010. Still open: Transvoxel case counts stated more precisely than guaranteed; the
  heightfield→SDF conversion formula is the author's formulation; QEF clamp ~0.1 is soft.
- `06`, `09`: see those chapters' provenance sections (industry-example attributions are
  deliberately vague; worked memory-math is illustrative arithmetic, not a measured budget).
- `07`, `10`: hex-tiling venue — **resolved 2026-07**: Mikkelsen, "Practical Real-Time
  Hex-Tiling", JCGT 11(3), 2022 (tier upgraded P/? → P). Normal-blend family — **resolved
  2026-07**: Barré-Brisebois & Hill, "Blending in Detail", 2012, URL verified; RNM and the
  cheaper variants' formulas now inlined in `07`. Still open: heightfield-shadow
  engine-feature specifics are version-sensitive.
- `08`, `11`: work-graphs production readiness is `?` by construction; triangles-per-pixel
  target bands and budget numbers are practice bands, not standards.
- `12`: fullscreen-triangle rationale is community canon (F), not a paper; attribution
  corrections applied 2026-07 (Johanson 2004 Lund; Kass & Miller SIGGRAPH 1990; Bruneton,
  Neyret & Holzschuch CGF 2010). Shoal/shore-wave rows added 2026-08: Yuksel 2007,
  Jeschke & Wojtan 2017/2018, Gonzalez-Ochoa GDC 2012, and the Sea of Thieves SIGGRAPH 2018
  talk were web-verified (attribution only, not content). **Audit pass 2026-08** re-checked
  every row added in this batch and corrected: Battjes 1974 completed to Copenhagen, 466–480
  (databases propagate a wrong "Honolulu, 446–480"); Dean & Dalrymple 1991 now web-verified
  (World Scientific, *Advanced Series on Ocean Engineering* vol. 2), so it is no longer
  model-knowledge-only; and the claim that *Uncharted* shipped wave particles was demoted to
  **`?`** — the GDC 2012 talk documents mesh LOD, wave generation and a flow shader, and the
  wave-particle attribution is unconfirmed. Remaining model-knowledge-only: the Airy/McCowan
  physics rows (constants H ≈ 0.78·h and h^(-1/4) shoaling are standard textbook values, not
  re-derived). The eikonal travel-time phase field, breaker-profile constructs, and break-mask
  tuning windows are F-tier practice with no canonical source. Wave–current row added 2026-08:
  Peregrine 1976 attribution web-verified; the opposition-scalar modulation and blocking-range
  constants in the chapter are F-tier renderer practice, not from the paper. The shallow-water
  group speed in that chapter's snippet was corrected 2026-08 (`c_g = √(g·d)`; the earlier
  `½√(g·d)` was the deep-water relation). Energy-spectrum sections (sea states / calm / aerated,
  2026-08): Beaufort descriptors are verbatim from NOAA SPC (D-tier, fetched); Douglas/WMO
  adoption dates conflict across secondary sources and are deliberately not asserted; the Kelvin
  angle was verified against standard references. **The capillary minimum was recorded here as
  "verified as a pair" and the pair was not consistent** (corrected 2026-08): 23.1 cm/s implies
  `σ = 0.07256 N/m` and 1.73 cm implies `σ = 0.07437 N/m`, 2.5% apart. Each half is inside the
  published spread for clean water, so each survived being checked alone — which is what a
  pair-check is *for*, and this entry claimed one that had not been made. `12` now **declares one
  `σ` (0.0728 N/m, `reference-impl/wake.py::SIG`) and derives both halves from it** — 23.12 cm/s at
  1.712 cm — so the two cannot drift apart again; the constant is `P/?` and the two closed forms
  are `D`. Nothing downstream moved at the quoted precision: this was a provenance defect, not a
  numerical one. Foam
  optics are from Dierssen 2019 (fetched; sole author verified); the waterfall
  sheet→ligament→droplet cascade is classical instability theory with no waterfall-specific
  canonical citation; the pure-water RGB absorption triple was corrected 2026-08 to match its
  stated 610/550/450 nm sample points. Glacial-flour turquoise upgraded from synthesis-only to
  P/synthesis — corroborated by glacial-lake reflectance studies (MRD 37(1) 2017; ERL 17 2022),
  the Rayleigh explanation stays refuted.
- `12` (man-made water — the chapter's most speculative block, and the one to verify first):
  the **driven-basin** account of a pool's wave field is this skill's composition, not a cited
  model. Its ingredients are classical (Lamb's `α = 2νk²`, the capillary–gravity minimum phase
  speed, free-shear-jet spreading and `1/s` decay, wave–current ray theory) but the assembly is
  not, and three pieces are weaker than the prose density suggests. (1) The **submerged-jet
  footprint**: the jet scaling is textbook, its numerical constants are model-knowledge, and the
  surface-deformation link `η ~ C·u'²/g` carries an **O(1) constant that is genuinely unknown**
  (`C = 1` was used) — which is why the chapter states near-field roughness as a *ratio* to the far
  field, and why an absolute rms slope must not be quoted from it. (2) The **±19° energy fan** and
  the crest curvature are outputs of integrating the ray equations through a modelled drift field,
  reproducible but not measured; the supercritical conclusion (no ring system, no Kelvin wedge)
  is the durable part and follows with no free parameter. (3) **Inextensible-film damping**
  `α ≈ 0.35·k·√(νω)`: the Stokes-layer structure is solid, the prefactor could not be confirmed
  against a primary source, so the 3–9× factor is indicative. Also unmeasured: "tiled walls are
  near-total reflectors" is an argued approximation, not a figure. The pool-optics worked example
  is arithmetic done in-chapter over Pope & Fry absorption sampled at the chapter's own RGB points
  (610/550/450 nm — **not** the 418 nm absolute minimum, which is below a typical blue channel);
  the liner albedos are representative values, not product data. Two items added 2026-08 and both
  **open** rather than uncertain: the submerged vertical face's sky share is *located* — the window
  is 0.199 of a horizontal face at the same depth against the 0.390 the reference implementation
  hands it — but **not fixed**, because closing it needs the mirror's missing bounces at the same
  time and moving the sky constant alone runs the wrong way; and the caustic read on a vertical face
  is corrected to the refracted beam's continuation yet is still a **proxy**, since the bed's map is
  focused at each texel's own depth and the honest fix is to rasterise those faces into their own
  caustic map. The artefact figures attached to the second (41% arc rms, stripe rms 1.372 → 0.816,
  z/arc 0 → 0.941) are the implementation's own printed diagnostics on one frame and were not
  independently re-derived.
- `12`, `03` (engine-native water, added 2026-08): every claim in the UE Water sections is D/N-tier
  engine documentation fetched 2026-08 — architecture, quadtree/tile defaults, body types and spline
  metadata, Landmass brush modes and the edit-layers requirement, Single Layer Water's inputs and its
  single-depth-layer limit, Gerstner wave-asset parameters, and the `AWaterZone` properties (info
  texture **array**, half-precision toggle, capture Z offset, velocity-blur radius, local-only
  tessellation, ground actors). **Not** verified: the water-info texture's channel packing (the
  chapters deliberately describe *what it fuses*, not which channel holds what) and the buoyancy
  amortization property names, which came from search snippets rather than a fetched page (`?`).
  Community reports of version-specific Water breakage under World Partition are forum-tier and are
  flagged, not asserted. Everything here drifts by engine release; re-verify constants at time of use.
- `10`, `12`, `12b` (illuminants and the submerged hemisphere, added 2026-08): the **general
  results are derived and closed** — that an illuminant is a cosine integral of the scene's own sky
  and is therefore a property of the *receiver's orientation* (weights `cos θ sin θ` and `sin² θ`,
  equal at exactly ½ only under a uniform sky); that a disc lobe carrying the beam must be excluded
  from that integral while the aureole must be included; and that the Rayleigh aureole's share of
  any receiver is `⟨cos²Θ⟩_w/(1 + ⟨cos²Θ⟩_w)`, hence **≤ ½ pointwise and exactly ¼ over the
  sphere**, for any optical depth and any solar elevation. Those need no verification effort: they
  are moments of a phase function and an integral of the cosine law. What is **open**: the sky
  *gradient* the two lobes sit on is not derived from anything — single-scattered Rayleigh gives
  only a lower bound of 0.55 / 0.58 / 0.49 on it, missing orders ≥ 2 and the ground return (`?`);
  the reference run's band-irradiance **total** does not equal the sum of its own components
  (6.7 / 12.0 / 11.5 % apart, not a constant), so one of the two is wrong and this skill does not
  know which (`?`); and the observation this whole line of work chases — a submerged wall reading
  *lighter* than the dry band above it, on every side — **still does not emerge** now that both
  halves of the wall's upper hemisphere have been derived and its source illuminant with them. The
  render sits at 0.513 where the observation requires > 1. That supersedes the "located but not
  fixed" note in the block above: the sky share **is** fixed (0.199 in place of 0.390) and the
  mirror's bounces **are** carried to a fixed point with a measured residual bound, and the
  remaining factor of ~1.95 belongs to neither. Either something is still missing from both sides,
  or the observation and this physics disagree — and that is the state to leave it in.
- `12` (fouling, added 2026-08): **the whole section is a specification and nothing in it has been
  rendered.** The mechanism (three driver fields; stagnation from one Laplace solve; two unaligned
  drivers, so an AO-driven grime mask is backwards for one of them; patchiness as a linear
  instability of the roughness–deposit feedback) is argued and two pieces of it are derived here —
  the corner exponent `|u| ~ r^(π/α − 1)` and the instability threshold. **Everything chemical and
  biological is `?`**: which organism dominates where, every rate, and the per-material
  susceptibility orderings. A weathering *rate* is not renderable input at all, which is the
  section's own argument for stating susceptibility instead — verify the orderings against a
  materials source before quoting them, and do not quote numbers, because none are given.
- `12`, `12b` (the sea reference set, added 2026-08): the transfer table is bookkeeping over results
  already provenanced, and **`b_b ≈ 0` is the single entry that does not carry from a pool to the
  sea**. The observational rulings (a backlit wave reading green while the same water reads
  grey-blue two metres away; reveals-and-stays-put against hides-and-pulses; two clouds separated by
  lifetime) are readings of owner photographs, reproducible by anyone with a camera and a coast, and
  none is a calibration. **`?`**: no spectrum was extracted from any frame, so the coastal IOPs
  remain unmeasured and the CDOM/chlorophyll attribution is an identification; the sediment
  entrainment law and fall velocity are named for shape only; the multivalued free surface under a
  plunging lip is stated as a representation change with no route proposed. The reference set has a
  **named gap** — no frame catches the backwash lifting sand — and filling it by inference from the
  other eight is exactly the move the gap exists to prevent.
- `11` (verifying an approximation, added 2026-08): the claim that a photographic bar cannot verify
  an approximation rests on one episode (four transport faults of 5–25%, every one invisible in
  frame) plus arithmetic through the sRGB transfer function that is exact but is a property of *that*
  view transform — recompute it for a filmic curve or for PQ before quoting the levels. The three
  preconditions are house doctrine (**F**), not a cited methodology.
- `19`: PCISPH (Solenthaler & Pajarola 2009), IISPH (Ihmsen et al. 2014), DFSPH (Bender & Koschier
  2015) and the Kelvin-wake citation (Thomson 1887) were all **web-verified 2026-08** — the `?`
  flags are cleared. Probe-point buoyancy, the spray/foam/bubble split, domain-fade fractions and
  budget guidance remain F-tier production practice with no canonical source. Nintendo water
  (2026-08): the TotK projected-area drag has a first-party GDC 2024 talk (T, verified); everything
  else — Wind Waker mechanism, TotK's cel look, Mario Kart World's drivable waves — is community
  reconstruction or launch-window press (F), and Mario Kart World's especially so; the *doctrine*
  those examples illustrate (same contracts, authored bands; deterministic waves as gameplay state)
  is this skill's own, not a citation.
- `13`: RotTR snow-deformation attribution corrected 2026-07 to the GPU Pro 7 chapter
  (Michels & Sikachev; SIGGRAPH 2015 talk form); God of War row pinned to Surricchio GDC 2023.
  Still open: Horizon Frozen Wilds snow attribution (T/?, no primary talk found); wrapped-
  diffuse snow approximation and band/budget numbers are F-tier practice.
- `14`: per-map shipping formats and channel-pack groupings are standard-practice judgment;
  Ghost Recon Wildlands / Far Cry 5 talk attributions came from search snippets, not the talks;
  RVT aux-sampling behavior inferred from doc summaries.
- `15`: HZD and Tsushima talk speakers — **resolved 2026-07**: van Muijden (GDC 2017) and
  Wohllaib (GDC 2021) web-verified; the Tsushima wind companion talk's speaker remains
  unverified. Still open: Tsushima "~2.5 ms / ~10⁵ blades" figures are from a secondary
  summary; Décoret billboard-clouds attribution unverified (no URL); packing/distance/budget
  numbers are F-tier order-of-magnitude practice.
- `16`: viewport budget numbers (≤8 ms iGPU frame, ≤16 ms brush echo) are representative
  practice; UE Z-scale formula cited from Epic's doc without the underlying range being stated
  there; "sun sweep as highest-value check" inherits terrain-architect `09` without external
  citation.
- `17`: Far Cry 5 road-through-terrain-stack attribution not verified page-by-page; "2–3
  frame" async-readback latency grounded only on Unity's "a few frames" wording; Jolt
  height-update API name from release-note summaries; promotion-pipeline and stamp-replay
  patterns are F-tier with no canonical citation.
- `18`: "raster-primary + RT-secondary with a triangulated terrain proxy is the 2026 default"
  and the displacement-micromap trajectory are directional industry reads; cone-map bake cost
  and POM sample counts are practice numbers; cone-step-mapping attribution to Dummer is via
  GPU Gems 3's citation only; pitch/roll handling details in the Voxel Space section are part
  folklore (consistent with the s-macke construction).
- `03` (Mesh Terrain addendum): everything beyond Epic's fetched doc pages is flagged `?` —
  collision, runtime deformation, cook flattening, cost model, HLOD, roadmap; the June 2026
  release positioning is corroborated by third-party coverage because Epic's news page
  resisted fetching.
