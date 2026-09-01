---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Reference
title: "Blocky Voxel Rendering: The Minecraft Family"
description: "Blocky voxel rendering: meshing, face culling, greedy merging and the streaming shape the Minecraft family settled on."
tags: [terrain, voxel, blocky, greedy-meshing]
status: stable
generated: { by: process:claude-code, at: 2026-07-30T04:53:08Z }
# --- end okf v0.2 ----------------------------------------------------
---
# Blocky Voxel Rendering: The Minecraft Family

This chapter owns turning an already-generated blocky voxel world into frames: chunk render data,
meshing, vertex packing, baked voxel lighting, the remesh pipeline, submission, LOD, transparency,
and the ray-marched alternative. It does **not** own generating the voxels — chunk pipelines, seeds,
density functions, and biomes live in terrain-architect `24`; smooth isosurfaces live in `05`; the
streaming world frame in `06`. Most of this domain is folklore-tier: the canonical writeups are
community blog posts, not papers, and the provenance section says so honestly.

Contents: [Chunk render data & the apron](#chunk-render-data--the-apron) ·
[Meshing algorithms](#meshing-algorithms) · [Vertex format engineering](#vertex-format-engineering) ·
[Lighting: flood fill, smooth light, vertex AO](#lighting-flood-fill-smooth-light-vertex-ao) ·
[The remesh pipeline](#the-remesh-pipeline) · [Submission & culling](#submission--culling) ·
[Distant terrain LOD](#distant-terrain-lod) · [Transparency & fluids](#transparency--fluids) ·
[The ray-marched frontier](#the-ray-marched-frontier) · [Budgets & pitfalls](#budgets--pitfalls) ·
[Sources & provenance](#sources--provenance)

## Chunk render data & the apron

The render unit is the **chunk section**: 16³ (Minecraft lineage) or 32³ (most modern engines —
fewer draw records, better meshing amortization, and 32 fits bitwise meshing registers exactly).
Whatever generation hands you, re-slice to cubic sections for rendering: meshing, culling, and
allocation all want a uniform unit.

**Store voxels as palette + bit-packed indices, not raw IDs.** Each section keeps a small palette of
distinct block states and an index array at `ceil(log2(paletteSize))` bits per voxel. A plain-dirt
section with 5 states packs at 3 bits/voxel — 12 KB for 32³ instead of 64 KB of u16s. This is not
just a memory win; it is a **meshing-bandwidth** win: the mesher streams the entire section (plus
apron) per rebuild, and remesh throughput on worker threads is usually memory-bound, not ALU-bound.
Two structural bonuses: a **single-entry palette** (all air, all stone) is detected in O(1) — skip
meshing entirely, emit nothing or only boundary faces; and appearance-equivalence for meshing can be
computed **once per palette entry** (palette → face-texture/opacity table), not once per voxel.

**The apron.** A face is emitted iff the neighboring voxel doesn't occlude it, and vertex AO reads
the 3×3×3 neighborhood of each face — so meshing a section requires a **1-voxel halo** of neighbor
data, including edges and corners (AO needs the diagonals, not just the 6 face-neighbors). The mesh
of chunk A therefore **depends on the border layer of every neighbor of A**. Two consequences,
both classic bug sites:

1. **Re-mesh on neighbor change.** An edit at a section boundary dirties the edited section *and*
   every section whose apron contains that voxel — up to 8 sections for a corner voxel. Miss this
   and you get the canonical symptom: a block placed at a boundary leaves a phantom face or an AO
   seam on the neighbor until something else forces its rebuild.
2. **Snapshot the apron.** Worker-thread meshers must copy section + halo into a job-local snapshot
   at enqueue time. Meshing directly against live neighbor storage races with edits and produces
   meshes that are internally inconsistent (half old, half new world) — visible as one-frame cracks.

One 2D slice of a section plus its halo makes the ownership split concrete:

```
   b b b b b b b b b b      the job-local snapshot = section + 1-voxel halo
   b o o o o o o o o b
   b o o o o o o o o b      o  owned voxels — the mesher emits faces only for these
   b o o o o o o o o #      b  borrowed apron — the border layer of every neighbor,
   b o o o o o o o A #         edges and corners included (AO needs the diagonals)
   b b b b b b b b # #
                            A  owned voxel at the boundary: its face test and 3x3x3
                               AO neighborhood read the '#' borrowed cells — so an
                               edit to those voxels dirties THIS section's mesh
```

Pitfalls: apron copied from only the 6 face-neighbors (AO breaks at chunk edges/corners exactly);
dirtying only the edited chunk; palette remap during meshing (snapshot the palette too).

## Meshing algorithms

All raster paths reduce the volume to quads; they differ in how many quads and how fast.

| Algorithm | Mechanism | Quads emitted | Meshing speed | VS/raster cost | Per-vertex AO/light |
|---|---|---|---|---|---|
| Naive cubes | 6 faces per solid voxel | Catastrophic (~6n³) | Fast | Catastrophic overdraw | Fine |
| **Culled** | Emit face iff neighbor non-occluding | Baseline (surface only) | Fast, trivially simple | High vertex count | Perfect — every face is unit-size |
| **Greedy** | Merge coplanar same-appearance faces into maximal rectangles | 2–10× fewer than culled on natural terrain | Slower (per-slice mask + merge scan) | Low | **Only if light/AO join the merge key** |
| **Binary greedy** | Bitmask columns per axis; face masks and merges via bit ops | Same as greedy | Fastest known CPU path (tens of µs per 32³) | Low | Same constraint as greedy |

**Culled meshing** is the correctness reference: for each solid voxel, for each of 6 directions,
emit the face iff the neighbor (apron at boundaries) does not occlude it. Occlusion is per-pair —
glass does not occlude stone, water occludes water but not stone. Write this first; every fancier
mesher is verified against it (identical rasterized coverage, `11`).

**Greedy meshing** (Lysenko's 0fps formulation): sweep each of the 3 axes; for each slice build a
2D mask of visible faces with their appearance key; scan the mask merging runs into maximal
rectangles (extend along U, then grow along V while the whole row matches). The non-negotiable rule:
**the merge key is the full appearance tuple — texture, tint, per-vertex light, and all 4 AO
values — not just block type.** Merging across differing light/AO stretches vertex attributes across
the merged quad and produces smeared lighting and AO gradients that pop when a nearby edit re-splits
the quads. Under smooth lighting, natural terrain rarely merges far anyway — greedy's win shrinks
from ~10× to ~2-4×. Accept that; do not weaken the key. Two secondary artifacts: interpolation
**anisotropy** from the quad's split diagonal (fixed in the AO section below), and T-junctions
between differently-sized adjacent quads — harmless with integer-snapped vertices, a shimmer risk
once vertices pass through float transforms; keep chunk-local positions integral in the packed
vertex and let the VS do the single float transform.

**Binary greedy meshing** is the modern fast path: pack each axis column of solidity into a u32/u64
(why 32³ is the natural section size), compute face masks with shifts —
`faces = solid & ~(solid >> 1)` and the mirrored form per direction, apron bits fed into the shift
boundary — then greedy-merge the resulting 2D bit-planes with trailing-zero counts and run masks.
No per-voxel branching; the whole mesher is bit arithmetic over a few KB of masks. Community
implementations (F-tier) mesh a 32³ section in tens of microseconds, which changes the remesh-budget
math in `The remesh pipeline`. The appearance/light key still applies: binary merging handles the
solidity geometry; you must still split merges on appearance, typically by running the binary pass
per appearance class or validating merges against a per-face key plane.

**When NOT to greedy-mesh:** if block textures live in a **texture atlas**, a merged 3×2 quad needs
UVs that tile 3×2 across one atlas cell — impossible with hardware wrap, and `fract()` in the shader
breaks derivative-based mip selection at tile seams (visible as sparkling lines). The clean fix is
**texture arrays** (next section): one layer per block texture, UVs tile natively per layer. If you
are locked to an atlas, ship culled meshing; greedy + atlas + mipmaps is a known-bad triangle.

Pitfalls: merge key missing AO/light (smeared lighting); greedy across block-boundary tint variation
(biome color bands become stripes); comparing meshers by quad count alone (vertex cost is not the
bottleneck once submission is GPU-driven, `08`).

## Vertex format engineering

A cube-face vertex is tiny data; pack it. Chunk-local integer position needs 6 bits/axis for a 32³
section (0..32 inclusive — corners reach 32; 5 bits only covers 16³), the face normal is one of 6 →
3 bits, AO is 2 bits, sky+block light 4+4 bits, texture layer 8–16 bits. A workable 32-bit near
format: `pos 6+6+6 | normal 3 | AO 2 | light 8` with the texture layer per-quad; a 64-bit format
fits everything per-vertex with room for greedy quad extents. The chunk's world offset is a per-draw
constant (push constant / instance data / gl_DrawID-indexed SSBO) — never per-vertex floats, which
both bloats the vertex and reintroduces `09` precision drift far from origin.

**Vertex pulling beats classic vertex buffers here.** Store packed quads (not vertices) in an SSBO;
draw with a shared static index buffer (or 4-vertex instancing per face) and reconstruct the corner
in the VS from `gl_VertexID & 3` plus the quad record. Wins: 4 corners share one quad record
(~2-4× memory over expanded vertices), one giant buffer arena instead of per-chunk VBs (see
Submission), and the format is trivially consumable by compute for culling. Cost: a few ALU ops of
unpack in the VS — free on any 2020+ GPU. Classic VBs remain fine for a first implementation;
migrate when you adopt the pooled-arena submission model.

**Texture arrays vs atlases: arrays win.** Atlases bleed across cells in lower mips (a 16×16 tile
dies at mip 4 unless padded/duplicated), fight anisotropic filtering (samples cross cell borders),
and block greedy UV tiling. A `TEXTURE_2D_ARRAY` gives every block texture its own full mip chain,
correct wrap and aniso, and a flat integer layer index that packs into the vertex. The only atlas
survivors are engines targeting APIs without arrays; even then prefer padded atlases with per-mip
gutters and clamp the max sampled mip. Non-square/animated tiles: keep layers uniform size and
handle animation by layer-index swap per frame, not UV scrolling.

Pitfalls: 5-bit positions on a 32³ section (corner 32 wraps to 0 — one-in-33 vertex snaps across the
chunk); packing signed values without bias; forgetting that AO/light must interpolate — they belong
in vertex attributes, not per-quad flats, or smooth lighting dies.

## Lighting: flood fill, smooth light, vertex AO

The family's lighting is **baked per-voxel, consumed per-vertex**. Two independent 0–15 channels:
**block light** (torches: seed 15 at emitter, BFS flood fill decrementing 1 per step through
non-opaque voxels) and **sky light** (seed 15 in every column cell open to sky, propagate downward
without attenuation, sideways/up with −1 — this is what makes cave mouths glow inward). Removal is
the hard half: un-propagation BFS that clears cells lit *by* the removed source, then re-floods from
surviving border lights. Get removal wrong and stale light pools linger after a torch is broken —
the single most-reported lighting bug in the family. Lighting updates are world-data mutations that
**precede** meshing: edit → light BFS (may cross chunk borders; every touched section is dirtied) →
remesh. The mesher then just *reads* light; it never computes it.

**Flat lighting**: a face samples the one cell it faces into. **Smooth lighting**: each of the 4
face vertices averages the 4 cells (in the face's plane, one step outward) sharing that vertex —
same stencil as AO, so compute them together. Opaque cells are excluded from the average (or
contribute 0 — pick one convention and keep it, it changes the look at wall bases).

**Vertex AO — the canonical 3-neighbor rule** (Lysenko's formulation, F-tier canon). For a face
vertex, examine the two edge-adjacent cells (`side1`, `side2`) and the diagonal (`corner`) one step
out from the face:

```
ao(side1, side2, corner):
    if side1 and side2: return 0          # fully wedged — corner is irrelevant (occluded anyway)
    return 3 - (side1 + side2 + corner)   # 3 = open, 0 = darkest
```

2 bits per vertex, applied as a multiplier ramp (e.g. {1.0, 0.8, 0.6, 0.4} — tune, don't compute).
Then the **diagonal flip**: a quad rasterizes as two triangles, and interpolation of 4 unequal
corner values depends on which diagonal splits it — the same AO pattern shades differently under the
two splits (interpolation anisotropy; visible as inconsistent dark triangles on stair-step terrain).
Fix per quad: if `ao00 + ao11 > ao01 + ao10`, flip the split diagonal (emit indices for the other
triangulation). Apply the identical flip test to smooth-light values, and remember both AO and light
are part of the greedy merge key.

**Why this baked scheme survives into TAA-era pipelines:** it is free at shade time, edit-latency is
hidden inside the remesh you were doing anyway, and it is view-independent so TAA/upscalers treat it
as stable albedo-like signal. The modern alternative — upload the light field as a **3D texture**
(one R8/RG8 texel per voxel, or a downsampled clipmap) and sample it in the pixel shader — buys
per-pixel trilinear smooth light with no merge-key constraint on greedy meshing, plays cleanly with
deferred shading, and moves relight cost off the mesher (light edit = texture region upload, **no
remesh**). Costs: upload bandwidth, border-texel sharing between chunk-sized textures (or one big
clipmap volume, `10`), and AO still wants the vertex path or a screen-space term. Both schemes
coexist in shipping engines; choose per project, not per fashion. Full dynamic GI integration is
`10`'s problem.

Pitfalls: light BFS that stops at chunk borders (permanent dark seams at 16-block intervals); doing
light updates *after* queuing the remesh (mesh bakes stale light, corrects one rebuild later —
flickers); averaging AO across the flip test but not light (they disagree on split direction —
pick the dominant term, usually AO).

## The remesh pipeline

Remesh latency is a **player-visible metric**: the time from click to the block appearing is your
input latency plus this pipeline (`11` treats it as a first-class verification target — measure it,
budget single-digit ms for the edited chunk). Doctrine:

- **Dirty set, not dirty list.** Edits mark sections dirty in a dedup set; a section edited 10×
  in a frame meshes once.
- **Strict ordering per edit**: apply voxel write → run light propagation (collecting every section
  it touched) → enqueue all touched sections + apron-dependent neighbors. Any other order bakes
  stale data.
- **Priority**: player-edited sections first (they are the latency metric), then frustum-and-near
  by distance, then off-screen. A plain distance sort stalls the block the player is staring at
  behind 30 chunks loading in behind them.
- **Per-frame budget** on *uploads and swaps*, not just CPU meshing: N sections/frame (tune to
  frame budget; the constraint is usually upload + allocation, not mesh CPU once you have binary
  greedy). Exceeding budget rolls over to next frame — never spike.
- **Workers mesh snapshots** (apron section above); the render thread only receives finished
  vertex blobs.
- **Double-buffered swap**: build the new mesh into a fresh allocation, then atomically swap the
  section's draw record; free the old allocation after the frame fence. Never mutate a buffer the
  GPU may be reading — that is a stall (or corruption) generator. The one-frame window where old
  mesh renders against new world data is acceptable; a stall is not.

Pitfall — the **spiky remesh frame**: one block broken at a chunk corner triggers light BFS across 5
sections plus apron-dirtying of 7 more, and a naive pipeline meshes all 12 the same frame → visible
hitch on every edit. The budget + priority queue exists precisely to smear that spike; only the
section containing the edit needs same-frame service.

## Submission & culling

**One draw call per chunk section is dead.** A 32-chunk view distance is ~50k sections; even at 500
visible, per-draw CPU cost and state churn dominate. The shipping pattern is `08`'s: all section
meshes live in one **pooled vertex arena** (one big buffer + offset table), a GPU compute pass
frustum-culls section AABBs and compacts survivors into a **multi-draw indirect** argument buffer,
and the CPU issues one `MultiDrawIndirect` per pass per material domain (opaque / cutout /
translucent). Vertex pulling (above) makes the arena natural: a section's "mesh" is just
`{offset, quadCount}`.

**Arena allocation doctrine**: chunk meshes churn constantly (remesh = free + alloc), so a naive
first-fit heap fragments until allocation fails with plenty of free bytes. Use quantized size
buckets (power-of-two or 4 KB classes) with free lists, accept the ~20-30% internal waste, and run
lazy compaction (move a few blocks per frame during idle) rather than stop-the-world defrag. Track
high-water fragmentation as a live stat — it is a slow-leak class of bug (`11`).

**Cave/visibility culling** — the family's structural advantage: frustum culling alone still draws
every buried section between camera and skybox. The Minecraft-lineage answer (Checchi's "advanced
cave culling", F/T-tier) precomputes per section, at mesh time, a 6×6 **face-connectivity matrix**:
flood-fill the section's non-opaque voxels and record which pairs of its faces are connected
through it. At render time, BFS the section graph from the camera's section, entering a neighbor
only if the connectivity matrix permits the (entry face → exit face) path and the walk direction
never reverses against the view. Cheap (bitset per section, graph walk per frame or per camera-cell
change), and it eliminates essentially all underground overdraw when the camera is in a cave, and
all cave rendering when it is on the surface. **HiZ occlusion culling** (`08`) is the general
alternative — depth-pyramid test per section AABB in the same compute cull — and wins where the
connectivity model breaks down (huge carved-out arenas, non-voxel occluders); many engines run both.

Pitfalls: per-section descriptor sets/buffers (defeats the arena — bind once); forgetting the
connectivity matrix must be rebuilt on remesh (an edit can open a wall — stale matrix = rooms
popping in late); CPU frustum culling of 50k AABBs per frame on one thread (move it to compute or
at minimum coarse-grid it).

## Distant terrain LOD

Full-resolution voxels to the horizon do not fit — memory, meshing, and quad density all scale
against you. The standard ladder:

1. **Downsampled voxel LODs**: each level halves resolution (2×2×2 → 1). Selection is
   **majority-with-priority**, not average: pick the most frequent *opaque* voxel; prefer any
   opaque over air/transparent when the cell is mixed (a half-solid cell rendered as air punches
   holes; rendered solid it merely bulges — bulging is the correct bias). Keep water as a priority
   class or oceans thin out to nothing at distance. Mesh LOD sections with the same mesher at
   scaled quad size.
2. **Ring seams**: where LOD N meets N+1, faces don't line up — cracks. Blocky worlds get away
   with the blunt fixes: **skirts** (extrude ring-border sections downward/outward by one coarse
   voxel) or **overlap** (render the coarser ring one section deeper under the finer ring; depth
   test resolves it). Both are accepted practice; exact stitching (`05`'s Transvoxel-style) is
   overkill for cubes. Hide the transition with fog/dither at the ring boundary.
3. **Separate far pipeline** (the Distant Horizons pattern, N/F-tier): distant terrain gets its own
   data format (column-compressed color+height, not voxels), its own meshing, its own slower update
   cadence, and renders before the near world with a depth pre-pass boundary. Decoupling cadence is
   the point: far terrain updates seconds late and nobody notices.
4. **Planet scale**: past tens of kilometers, stop pretending it's voxels — collapse to a
   heightfield/clipmap far renderer (`01`, `06`) with `09`'s origin-relative precision regime, and
   blend at the paradigm boundary.

Pitfalls: averaging block *IDs* when downsampling (produces nonsense palette entries); LOD selection
flicker at ring boundaries (hysteresis on the distance thresholds); running far-LOD remeshes on the
same budget/queue as near edits (edits starve; split the queues).

## Transparency & fluids

Translucent geometry (water, stained glass, ice) goes in a **separate mesh per section**, drawn
after all opaque passes with depth-test-on/depth-write-off. Ordering discipline:

- **Between sections**: sort translucent sections back-to-front by view distance every frame —
  cheap (hundreds of items) and non-negotiable.
- **Within a section**: correct ordering needs quad-level sorting. The Minecraft-lineage approach
  re-sorts the section's translucent index buffer when the camera moves past a threshold (not per
  frame). Alternatives that trade correctness for stability: **dithered/hashed alpha** (order-free,
  TAA resolves the noise — good for foliage-like cutouts, marginal for water), or **weighted
  blended OIT** (order-independent, softens but never pops; acceptable for glass, wrong-looking for
  deep colored water). Pick per material class; most ship sorted-water + dithered-everything-else.
- **Water surfaces**: mesh only faces against air/non-water (water-water faces are culled like
  solid-solid), drop the top surface ~1/9 voxel below the cell top (the family-signature look, and
  it prevents z-fighting with shore blocks), and drive flow animation in the shader from a per-quad
  flow direction packed at mesh time — never by remeshing.

Pitfalls: translucent quads in the opaque mesh (random popping that "fixes itself" when the chunk
remeshes — the tell); sorting sections by AABB-center only (large sections misorder — sort by
nearest point when it matters); underwater camera needing reversed face winding (mesh both-sided
water faces or flip cull mode when submerged).

## The ray-marched frontier

Rasterized quads are not the only endgame. The alternative family renders voxels **directly** by ray
marching a sparse structure in compute/pixel shaders:

- **Sparse voxel octrees** (Laine & Karras 2010, the P-tier canon): pointer-compressed octree,
  rays descend with a stack; excellent for static, dense, small-voxel content; editing is the weak
  point (structural updates are expensive).
- **Brickmaps / two-level grids** (F-tier community lineage): coarse grid of pointers to dense
  8³/16³ "bricks"; DDA through the coarse grid, march inside bricks. Editing is O(brick) — this is
  why editable small-voxel games prefer it over SVOs.
- **The Teardown pattern** (T/F-tier, from Gustafsson's talks/writeups): world = many object-local
  dense voxel volumes; rasterize each object's bounding proxy, ray march its volume in the pixel
  shader; small voxels (~10 cm), fully destructible.

**When does ray marching beat raster meshing?** Rule of thumb by projected voxel size: when a voxel
covers **many pixels** (Minecraft-scale ~1 m blocks), raster quads win — few faces, perfect
hardware fill, trivial LOD by remeshing. When voxels approach **pixel scale** (≤10 cm at gameplay
distances), quad counts explode past what meshing/memory tolerate and marching wins — cost scales
with pixels, not voxel count. The blocky family therefore stays raster for primary visibility. The
**hybrid** is the practical frontier even for blocky worlds: keep raster primary, but march the
voxel grid for **secondary rays** — shadow rays toward the sun, coarse AO/GI cones against a
downsampled brick volume (`10`). The voxel world is a free ray-tracing acceleration structure;
using it only for primary rays wastes it.

Honesty note: outside Laine & Karras, this section is talk- and folklore-tier; production details
of shipped small-voxel engines are partially disclosed at best. Do not cite specifics beyond what
the named talks actually state.

## Budgets & pitfalls

Order-of-magnitude budgets (32³ section, natural terrain, 8-byte packed vertices, quad records):

| Quantity | Culled meshing | Greedy (light in key) | Notes |
|---|---|---|---|
| Quads / surface section | ~2–6k | ~0.5–2k | Terrain-dependent; flat land compresses best |
| Mesh memory / section | ~64–200 KB | ~16–64 KB | Quad-record SSBO halves this again |
| Mesh time / section | ~0.5–2 ms scalar | ~0.1–0.5 ms; **tens of µs binary** | Snapshot copy often rivals mesh time |
| Sections resident @ 32-chunk radius | ~50k allocated, ~500–2k drawn post-cull | — | Why per-section draws are dead |

The recurring failure catalogue for this chapter (verification harnesses in `11`):

- **Spiky remesh frame**: every edit hitches → no budget/priority queue; light+mesh of the whole
  neighborhood ran synchronously.
- **AO/light seams at chunk borders**: apron missing diagonals, or neighbor not re-meshed after a
  border edit. Test: place/break a block at a section corner and diff all 8 neighbors' meshes.
- **Smeared lighting on merged quads**: greedy merge key missing light/AO/tint.
- **Inconsistent dark triangles on stairs**: missing quad-diagonal flip (interpolation anisotropy).
- **Sparkles/lines at texture tile seams under mips**: atlas + tiled UVs; move to texture arrays.
- **Stale light pools after breaking a torch**: light removal BFS incomplete.
- **Allocation failure with free memory**: arena fragmentation; bucketize + lazy compaction.
- **Rooms appear late when digging through**: cave-culling connectivity matrix not rebuilt on
  remesh.
- **Holes or vanished oceans at distance**: LOD downsample used majority-of-all instead of
  opaque/water-priority selection.

## Sources & provenance

Tiers: **P** paper/book · **T** industry talk · **D** official docs · **F** folklore/community ·
**N** engine/game-branded · **?** unverified. Most of this chapter is F-tier by nature — the
canonical texts are blog posts. Never upgrade a tier to make a claim sound stronger.

- **F** — Mikola Lysenko, *Meshing in a Minecraft Game* (0fps.net, 2012): culled + greedy meshing,
  the merge-key discipline, T-junction discussion. The canonical meshing writeup.
- **F** — Mikola Lysenko, *Ambient Occlusion for Minecraft-like Worlds* (0fps.net, 2013): the
  side1/side2/corner vertex-AO rule and the quad-diagonal flip for interpolation anisotropy.
- **F/T** — Tommaso Checchi (Mojang), the MCPE "advanced cave culling algorithm" writeup
  (~2014): per-section face-connectivity flood fill + view-graph BFS. Community-preserved
  developer writeup, not a formal publication.
- **F** — Community binary greedy meshing implementations and writeups (e.g. open-source
  `binary-greedy-meshing` repos, associated explainer videos): the bitmask face-extraction and
  bit-plane merge formulation. No canonical paper; verify against your culled-mesh oracle.
- **F/N** — Minecraft chunk-section palette format: publicly documented via community wiki
  reverse-engineering of the save/network formats; the palette+bit-packing pattern itself is
  general practice.
- **P** — S. Laine, T. Karras, *Efficient Sparse Voxel Octrees* (I3D 2010): SVO representation and
  ray traversal. The P-tier canon for ray-marched voxels.
- **T/F** — Dennis Gustafsson (Tuxedo Labs), Teardown engine talks and blog posts: object-local
  dense volumes ray-marched from rasterized proxies. Cite only what the talks state.
- **N/F** — *Distant Horizons* (Minecraft mod): the separate far-LOD pipeline pattern
  (own data format, own cadence). Open source; the pattern generalizes, the internals are its own.
- **P** — M. McGuire, L. Bavoil, *Weighted Blended Order-Independent Transparency* (JCGT 2013):
  the WBOIT alternative to sorted translucency.
- **D** — Graphics API documentation (Vulkan/D3D12/GL): multi-draw indirect, texture arrays,
  vertex pulling via SSBO — mechanism claims only.
- **?** — Specific internal renderer details of closed commercial voxel games beyond the talks
  above: treat as unverified; describe at family level only.
