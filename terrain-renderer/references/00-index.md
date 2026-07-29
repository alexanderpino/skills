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

Unlike terrain-architect's bibliography, this skill's attributions have **not** been through a
page-by-page primary-source verification pass. Tiers and author/year details were assigned from
model knowledge of well-known canon, and each chapter flags its least-confident claims (ledger
below). Practical rule: mechanisms and doctrine here are load-bearing and internally consistent;
**exact authors, years, venues, and numeric constants are "believed correct" and must be
re-checked against primary sources before publication-critical use.** When you verify a row,
upgrading this file is the right fix.

## Master technique index

| Technique / topic | Chapter | Canonical source | Tier |
|---|---|---|---|
| Screen-space geometric error (ρ = e·K/d) | `01` | Standard across LOD literature; formalized in Cozzi & Ring, *3D Engine Design for Virtual Globes* (2011) | P |
| ROAM (split/merge bintrees) | `01` | Duchaineau et al. 1997 | P |
| Geomipmapping | `01` | de Boer 2000 (web-published paper) | P/F |
| Chunked LOD | `01` | Ulrich, SIGGRAPH 2002 course | T |
| Geometry clipmaps | `01` | Losasso & Hoppe 2004; GPU version in GPU Gems 2 | P |
| CDLOD (quadtree + per-vertex morph) | `01` | Strugar whitepaper ~2009 | F/P |
| Hardware tessellation terrain | `01` | DX11-era vendor samples | D/T |
| CBT/LEB (GPU subdivision) | `01` | Dupuy, HPG 2020 | P |
| Skirts / stitching / morph / matched factors (crack taxonomy) | `01` | Folklore, consolidated | F |
| Cluster DAG build (group→simplify→split), monotonic error | `02` | Karis, "Nanite — A Deep Dive", SIGGRAPH 2021 Advances | T |
| Two-phase HiZ occlusion culling | `02` `08` | Nanite talk lineage + community practice | T/F |
| Software raster of micro-triangles, 64-bit visibility buffer | `02` | Karis 2021 | T |
| Visibility buffer (deferred material shading) | `08` | Burns & Hunt, JCGT 2013 | P |
| Meshlets / mesh shaders | `02` | Vendor docs; meshoptimizer | D/F |
| QEM simplification | `02` | Garland & Heckbert 1997 | P |
| UE Landscape (components/sections, LOD, weightmaps) | `03` | Epic docs | D/N |
| Nanite Landscape, Nanite displacement | `03` | Epic docs — version-sensitive, re-verify | D/N/? |
| Runtime Virtual Texture (RVT) | `03` `07` | Epic docs | D/N |
| World Partition / HLOD / LWC | `03` | Epic docs | D/N |
| Unity Terrain, Godot Terrain3D, O3DE Terrain | `03` | Engine docs / community | D/N |
| Palette-compressed chunk storage | `04` | Minecraft-lineage community documentation | F/N |
| Culled / greedy / binary-greedy meshing | `04` | Lysenko (0fps) for greedy; community for binary | F |
| Voxel vertex AO (side1+side2+corner, diagonal flip) | `04` | Lysenko (0fps) | F |
| Flood-fill sky/block lighting (0–15) | `04` | Minecraft-lineage community documentation | F/N |
| Cave culling via chunk-face connectivity | `04` | Checchi (Mojang) community writeup | F |
| Multi-draw indirect chunk submission, vertex pooling | `04` `08` | Community practice | F |
| Distant voxel LOD (downsampled far pipeline) | `04` | Distant Horizons et al. | N/F |
| Sparse voxel octrees | `04` | Laine & Karras 2010 | P |
| Weighted-blended OIT | `04` | McGuire & Bavoil, JCGT 2013 | P |
| Marching cubes (+ asymptotic decider) | `05` | Lorensen & Cline 1987; Nielson & Hamann ~1991 | P |
| Surface nets | `05` | Gibson 1998; naive form Lysenko (0fps) | P/F |
| Dual contouring (hermite + QEF) | `05` | Ju, Losasso, Schaefer, Warren 2002 | P |
| Transvoxel transition cells | `05` | Lengyel dissertation ~2010; transvoxel.org | P/D |
| GPU isosurface extraction (classify→scan→generate) | `05` | Community/vendor practice | F/D |
| Tile pyramid + SSE refinement, residency state machine | `06` | Cozzi & Ring 2011 + industry practice | P/F |
| DirectStorage-era streaming IO | `06` | Vendor docs | D |
| HLOD / far-world baking | `06` | Industry talks (various) | T/F |
| Splat blending: height-lerp, weight packing, mip halos | `07` | Folklore | F |
| Stochastic texturing (histogram-preserving blending) | `07` | Heitz & Neyret 2018 | P |
| Hex-tiling | `07` | Mikkelsen (JCGT-era publication) | P/? |
| Triplanar / biplanar projection | `07` | Folklore; Quilez writeups | F |
| Virtual texturing (page tables, feedback, transcode) | `07` | id Tech MegaTexture lineage; Mittring & van Waveren talks | T |
| Clipmap texturing | `07` | Tanner et al. 1998 | P |
| GPU-driven pipelines (persistent scene, indirect subm.) | `08` | Haar & Aaltonen, SIGGRAPH 2015 Advances | T |
| Terrain max-mip pyramid as long-range occluder | `08` | Industry practice | F/T |
| Work graphs / device-generated commands | `08` | D3D12/Vulkan docs — production maturity `?` | D/? |
| Camera-relative rendering / origin rebasing / RTE | `09` | Cozzi & Ring 2011 + folklore | P/F |
| Reversed-Z floating-point depth | `09` | Community canon (widely reproduced analyses) | F/D |
| Logarithmic depth | `09` | Outerra-lineage community practice | F |
| Cube-sphere quadtrees, per-patch local frames | `09` | Cozzi & Ring 2011 + industry practice | P/F |
| Horizon culling (ellipsoid occlusion) | `09` | Cozzi & Ring 2011 | P |
| Cascaded shadow maps (splits, snapping) | `10` | Engel/vendor lineage; split-scheme literature | P/F |
| Horizon mapping (baked terrain shadows) | `10` | Max 1988 | P |
| Heightfield ray-marched shadows | `10` | Engine features + community practice | N/F |
| Virtual shadow maps | `10` | Epic docs | D/N |
| Aerial perspective / sky LUTs | `10` | Hillaire 2020 | P |
| Failure catalogue, debug views, budget assertions | `11` | This skill's consolidation | F |

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

Public technical detail on shipped titles varies wildly; treat specific claims about any one
title as T/F tier unless a named talk is in hand.

## Least-confident-claims ledger

Each chapter ends with `## Sources & provenance`; the claims their authors flagged as least
certain are consolidated here so a reviewer knows where to spend verification effort first.

- `01`: GPU Zen 2 compute-tessellation attribution (Khoury/Dupuy/Riccio); CDLOD morph
  pseudocode variable conventions vs the whitepaper; "τ = 2–4 px shipping range" and morph-band
  fractions are folklore numbers; the ~20 km clipmap-vs-quadtree threshold is judgment.
- `02`: exact Nanite constants (group size, ~128 KB pages, METIS) — verify against the 2021
  talk; attribute-quadrics year (Garland & Heckbert 1998); hysteresis band k≈1.2 is folklore;
  visibility-buffer bit layout is illustrative; persistent-threads origin (Aila & Laine 2009).
- `03`: nearly everything version-sensitive is flagged `?` in-chapter — per-component batching
  in current UE, LOD cvar names, Nanite Landscape deformation/ray-tracing behavior per version,
  Nanite tessellation maturity, VHM status, mobile layer limits, O3DE internals.
- `04`: budget-table magnitudes are order-of-magnitude folklore (±2–3×); Minecraft water-surface
  offset fraction; Checchi writeup date; sky-light propagation specifics are F/N reverse-
  engineered behavior; "greedy win shrinks under smooth lighting" is observation, not
  measurement.
- `05`: asymptotic-decider venue-year (~1991); Gibson 1998 exact title/venue; Lengyel
  dissertation exact title; Transvoxel case counts stated more precisely than guaranteed;
  the heightfield→SDF conversion formula is the author's formulation; QEF clamp ~0.1 is soft.
- `06`, `09`: see those chapters' provenance sections (industry-example attributions are
  deliberately vague; worked memory-math is illustrative arithmetic, not a measured budget).
- `07`, `10`: hex-tiling venue; normal-blend variant naming (RNM/UDN/whiteout) is blog-lineage
  F-tier; heightfield-shadow engine-feature specifics are version-sensitive.
- `08`, `11`: work-graphs production readiness is `?` by construction; triangles-per-pixel
  target bands and budget numbers are practice bands, not standards.
