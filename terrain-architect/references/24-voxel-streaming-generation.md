# Voxel & Streaming Chunk Generation

A **family** of terrain generators, not one game: infinite-or-bounded, lazily-streamed, editable
**voxel** worlds where every chunk is generated on demand from `(seed, chunkX, chunkZ)` and nothing
more. Minecraft is the *documented exemplar* — its world-generation format is public and has been
reverse-engineered — but the paradigm is the family it heads: cubic-voxel siblings (Creativerse,
Luanti/Minetest, Terasology, Vintage Story) and smooth-voxel cousins (Astroneer, No Man's Sky-style
planet terrain). Treat Minecraft the way the rest of this skill treats Gaea's *Erosion* node — as a
branded instance of a family, never as the family itself (`SKILL.md`, "six things people call an
algorithm"; the tool-node crosswalk in `00`).

This is a *generation-paradigm blueprint*, not a new algorithm — every ingredient decomposes into
chapters you already have (`01`, `07`, `08`, `11`, `13`, `14`, `15`, `23`). What is new is the
**assembly and the doctrine it deliberately breaks**. Read it when the requested output is a runtime
voxel world, a "Minecraft-like", an infinite streamed block terrain, or a chunk-based biome system —
and read the doctrine ledger first, because this regime suspends the spine of `SKILL.md` on purpose.

Contents: [The paradigm frame](#the-paradigm-frame) · [The family and its variants](#the-family-and-its-variants) ·
[What this regime suspends (the doctrine ledger)](#what-this-regime-suspends-the-doctrine-ledger) ·
[Representation: voxels and the density function](#representation-voxels-and-the-density-function) ·
[Biome by multi-noise](#biome-by-multi-noise) ·
[Terrain shape: splines into density](#terrain-shape-splines-into-density) ·
[The chunk pipeline and determinism](#the-chunk-pipeline-and-determinism) ·
[Caves and aquifers](#caves-and-aquifers) · [The legacy 2D biome cascade](#the-legacy-2d-biome-cascade) ·
[Where the pieces already live](#where-the-pieces-already-live) ·
[What you give up, and how to check it](#what-you-give-up-and-how-to-check-it) ·
[Provenance](#provenance) · [Implementation contract](#implementation-contract)

## The paradigm frame

One constraint sets the entire design, and everything else follows from it:

> **Every chunk must be generatable knowing only the world seed and its own coordinates, plus a
> bounded halo of neighbours — never the global domain.** The world is generated as the player walks
> into it, and it is **editable**, so there is no "whole map" to run a pass over and no baked mesh to
> lean on.

That single rule is why every member of this family looks nothing like the heightfield-and-erosion
pipeline the rest of this skill teaches. You cannot run depression-fill, flow routing, or stream-power
erosion (`03`, `04`) — they are **GLOBAL** operations (`08`, `23`) and there is no global domain to run
them on. So the paradigm makes the opposite trade: it gives up physical process history and buys back
plausibility with **noise, splines, and per-block density**, all strictly local and deterministic. It
is not a worse terrain pipeline; it is a *different design point chosen for a different constraint*
(infinite/streamed/editable). Judge it by that constraint, not by the `09` drainage oracles it was
never trying to satisfy.

The **editable** part is easy to overlook and is half the reason for the voxel substrate: a game that
lets the player dig, place, and destroy blocks anywhere needs a uniform, mutable representation *even
in the 99% of the world that is a plain hillside a heightfield would have stored far more cheaply*.
You pay the voxel cost everywhere to buy edit-anywhere plus native caves and overhangs; if you need
neither, a heightfield chunk streamer (`08`, `23`) is lighter.

## The family and its variants

A generator is in this family if it is **chunked, seeded, per-chunk deterministic, streamed, and
voxel/editable**. Within that, members differ along a handful of axes — and the axes, not any one
game, are what you design against:

| Axis | Options (members that pick each) |
|---|---|
| **World extent** | Infinite/unbounded (Minecraft, Luanti, Vintage Story) · bounded/finite but still chunked (Creativerse, many survival sandboxes) · discrete procedural realms assembled from prefabs (Trove-style) |
| **Representation** | 2D heightfield + separately carved caves (pre-1.18 Minecraft, many clones) · **full 3D density function** (Minecraft 1.18+, Vintage Story) · smooth signed-distance field (Astroneer, No Man's Sky-style) |
| **Mesher** | **Greedy cubic** — merge coplanar same-material faces into quads (blocky sandboxes; folklore, Lysenko's "0fps" write-ups) · **marching cubes / dual contouring / Transvoxel** for smooth voxel with LOD seams (`08`) |
| **Biome model** | 2D biome map (most clones) · **multi-noise** parameter space (Minecraft 1.18+) · Whittaker temp/moisture lookup (common) |
| **Generation authorship** | Hardcoded in the engine (closed clones) · **pluggable/moddable mapgen** where the engine is the substrate and generation is user code (Luanti, Terasology — this is `14`'s node-runtime idea taken to the whole generator) |

Two honesty rules, both inherited from the skill's N-tier discipline:

- **Internals of closed clones are not public.** Creativerse and most commercial Minecraft-likes do not
  document their generator; you can describe them at the *family* level ("cubic-voxel, chunked, seeded")
  but must not claim a specific internal algorithm. Say "a voxel-sandbox generator in this family",
  not "it uses multi-noise".
- **Minecraft and the open engines are the citable references.** Minecraft because its datapack
  worldgen format is a documented schema and Cubiomes reverse-engineers its biome layer from seed;
  **Luanti (formerly Minetest) and Terasology** because they are open source and their mapgen is
  directly inspectable. When you need a concrete, verifiable design, reach for one of these — not a
  closed clone whose behaviour you'd be guessing at.

The rest of this chapter uses **Minecraft's instantiation** as the worked example because it is the
best-documented, then flags where the family diverges. Do not read "multi-noise + density function" as
*the* voxel-world design — it is *one* member's choices on the representation and biome axes above.

## What this regime suspends (the doctrine ledger)

The value of a dedicated chapter is honesty about which of the skill's load-bearing doctrines this
paradigm turns off, and what it substitutes. The **suspensions** are the family's (every member drops
them); the **replacements** shown are Minecraft's concrete instance — a clone may replace them
differently (a 2D biome map, a simpler cave noise) and still be in the family. Do not carry the skill
defaults in silently — they will fight the design at every step.

| `SKILL.md` doctrine | Status here | What replaces it (Minecraft's instance) |
|---|---|---|
| **The heightfield is the source of truth** | **Suspended.** The truth is a 3D density/SDF volume; height is an *emergent readout* (the topmost solid block). | Density `d(x,y,z)`: `d>0` solid, `d<0` air. Overhangs, floating islands, caves are native, not exceptions (`11`). |
| **Every landform is a claim about a process / noise alone never suffices** | **Suspended.** Terrain is unapologetically noise-first with no process history. | Splines map climate noise → a target height and a "squash factor"; 3D noise perturbs it. Rivers/valleys are *shaped by noise*, not carved by water. |
| **The Legal Order: depression handling → flow routing are MANDATORY** | **Removed.** Both are GLOBAL; the world has no global domain. | Nothing routes. "Water" is placed by **aquifers** — local noise water-tables (below) — decoupled from any sea-level drainage. |
| **Multi-biome = one substrate, masks vary parameters** | **Kept, and literalised.** | The masks *are* the biome: a point's climate values select the biome and (some of them) drive terrain shape directly (below). `13`'s doctrine taken to its end. |
| **Analysis after final geometry; export last and once** | **Kept, reframed per-chunk.** | Surface rules and decoration run *after* the density is resolved for the chunk, inside the staged pipeline (below). |
| **Seed in world coordinates; determinism under parallelism** | **Kept, and absolute.** It is the whole game. | Every stage reseeds from `(worldSeed, chunkX, chunkZ)`; visit order and thread count must not change a single block (`14`, Invariants in `SKILL.md`). |

The two suspensions are the ones that trip people. If a user wants *real* drainage networks, deltas,
or eroded valleys in their voxel world, no member of this family gives it at runtime — that is a
**hybrid** job (`23`): bake the global process history offline, stream it as coarse fields, and let the
chunk generator refine deterministic local detail on top. Say so plainly rather than promising erosion
the architecture forbids.

## Representation: voxels and the density function

The surface is defined implicitly by a **noise router** — a small graph of *density functions*
returning one scalar per block position. Positive is solid, negative is air; the isosurface `d=0` is
the ground. This is the same implicit-surface idea as an SDF/volume in `11`, with three differences
that matter (all as Minecraft 1.18+ realises them; a 2D-heightfield clone skips the first):

- **It is sampled, not solved.** Density is evaluated on a **coarse lattice** (historically every
  4 blocks horizontally, 8 vertically; configurable as the noise "cell size") and **trilinearly
  interpolated** to fill the block grid. This is the performance trick that makes per-block 3D noise
  affordable — the expensive noise runs at a fraction of the block count (`01`, `15`).
- **It is meshed by a family-dependent mesher.** Blocky sandboxes use **greedy meshing** (merge
  coplanar same-material faces into quads; folklore, Lysenko's "0fps" articles), *not* marching cubes.
  Smooth-voxel cousins (Astroneer, No Man's Sky-style) mesh the *same kind of density field* with
  **marching cubes / dual contouring / Transvoxel** for LOD-seam stitching (`08`) — same representation,
  different mesher. The mesher is an axis of the family, not a fixed property of the paradigm.
- **Materials are a second field, not the density.** Density says *where* solid is; a separate
  **surface-rules** pass (below) decides *what* the top blocks are (grass over dirt over stone, sand
  in deserts), and carvers/features overwrite blocks afterwards. Keep them separate — the
  material-vs-height separation of `08`/`11`, one field for the collision surface and one for
  appearance.

Because the representation is a full 3D field, the "when the heightfield fails" decision in `11` is
already made *for* you: you paid the voxel cost up front, so caves, overhangs, and floating terrain are
free — at the cost of paying it everywhere (the frame above).

## Biome by multi-noise

This is **Minecraft's** biome instance (1.18+), the best-documented one; a clone may instead use a 2D
biome map or a Whittaker temperature/moisture lookup and remain in the family. Minecraft's biome
placement is **not** painted regions and **not** a Voronoi of biome seeds. It is a nearest-match lookup
in a **6-dimensional climate space**, each axis an independent low-frequency noise evaluated in world
coordinates (`01`):

| Parameter | Drives | Notes |
|---|---|---|
| **Temperature** | biome only | Does *not* affect terrain shape. |
| **Humidity** (vegetation) | biome only | Does *not* affect terrain shape. |
| **Continentalness** | biome **and** shape | Ocean → coast → inland → far-inland; the primary "how high is the base land" axis. |
| **Erosion** | biome **and** shape | High erosion → flat/low; low erosion → mountainous. A *noise parameter named "erosion"* — it is **not** the erosion of `04`/`05`, it carries no sediment and conserves no mass. |
| **Weirdness** (→ ridges / "peaks & valleys") | biome **and** shape | Folded through `1 − |3|weirdness| − 2||` to make ridge lines. |
| **Depth** | shape | How far below the spline surface a block is; the vertical term that turns the 2D climate splines into a 3D density. |

Each biome declares an **interval box** in this space; a location gets the biome whose box is nearest.
The design consequence, and it is the important one: **biome and terrain are read from the same noise
parameters**, so a mountain biome and mountainous shape co-occur *by construction* rather than by
blending two authored terrains — exactly the "parameterise one substrate, never blend two finished
terrains" rule of `13`/`20`, made mechanical. Temperature and humidity are kept *off* the shape axes on
purpose, so a hot and a cold desert can share a landform while looking different.

## Terrain shape: splines into density

Again **Minecraft's** instance. The bridge from the climate parameters to the density field is a set of
**splines** (attributed to Henrik Kniberg's design; a developer source, not a paper — treat as F-tier).
Continentalness, erosion, and the ridge term are each run through a piecewise curve to produce, per
column:

- an **offset** — the target base height the density should cross zero at;
- a **factor / jaggedness** — how strongly 3D noise is allowed to perturb that base (a "squash" toward
  the target on smooth biomes, a wide band on jagged ones).

Then the per-block density is roughly:

```
density(x, y, z):
    base   = offset(cont(x,z), erosion(x,z), ridge(x,z))     # splines → target surface height
    squash = factor(cont, erosion, ridge)                    # how far noise may push the surface
    d = (base - y) * squash + noise3D(x, y, z) * amplitude    # >0 solid, <0 air
    # slope the field to a solid floor and an air ceiling near the world limits
    return d
```

The `(base − y)` term is what makes it a *terrain* and not a cloud of noise blobs: it biases the field
solid below the target height and air above it, so the isosurface hugs the spline surface, while the 3D
noise carves the overhangs, floating islands, and cliff undercuts a heightfield could never hold. Tune
`amplitude` and `squash` per biome — flat plains get a hard squash and almost no 3D wobble; mountains
get a loose squash and full 3D noise. This is the whole reason the paradigm reaches for 3D noise
instead of a 2D heightmap: the extra dimension *is* the feature set. (A 2D-heightfield family member
skips the 3D term and carves caves separately — cheaper, but no overhangs.)

## The chunk pipeline and determinism

A chunk is not generated in one shot; it advances through **proto-chunk stages**, freezing at each
until its neighbours are far enough along that the next stage's bounded halo is safe to read. Minecraft
names the stages explicitly; other family members have the same shape under different names:

```
empty → structure_starts → structure_references → biomes → noise → surface
      → carvers → features → light → spawn → full
```

- **biomes** — evaluate the climate noise(s), assign the biome field.
- **noise** — resolve the density function into solid/air; place the ground and primary liquid bodies.
  This is the terrain-shape stage above.
- **surface** — apply **surface rules**: replace the top blocks per biome (grass/dirt, sand, snow), the
  material pass of `08`/`11`/`18`.
- **carvers** — carve air through solid (the older cave/ravine carvers; noise caves live in the density
  stage, below).
- **features** — decoration: ores, trees, lakes, structure pieces — deterministic **scatter** (`07`)
  keyed off a per-chunk **decoration seed** derived from the world seed and chunk coordinate.

Two engineering facts define correctness here, and both are `14`/`23` doctrine sharpened to a point:

1. **Bounded neighbour halo, not global.** A stage may read a *fixed radius* of neighbouring chunks
   (features famously write up to a chunk-and-a-margin over the border, which is why a tree from the
   next chunk can appear at the edge). The staged freezing is exactly the **apron / seam-ownership**
   contract of `08`/`23`: a shared border sample has one deterministic owner and every generator that
   touches it computes the identical value.
2. **Determinism is the product.** Same seed and coordinate → identical chunk, regardless of approach
   direction, thread count, or whether the chunk was generated now or a year ago. Every stochastic step
   reseeds from `hash(worldSeed, chunkX, chunkZ, stageSalt)` (Invariants, `SKILL.md`; `14`). This is what
   lets **reverse-engineering** tools (Cubiomes) locate biomes and structures straight from a seed
   without running the game — a useful external oracle for validating your own generator.

## Caves and aquifers

Caves are **noise, not dissolution** — the karst machinery of `11` (Paris et al. 2021) does not apply,
because there is no soluble-lithology flow to route. Instead the density function subtracts cave space
directly:

- **Cheese caves** — large chambers where a low-frequency 3D noise band goes negative.
- **Spaghetti / noodle caves** — long thin tunnels from the intersection of two ridged 3D noises (an
  `|noise| < ε` tube, the 3D analogue of a ridge line).

**Aquifers** are the paradigm's answer to "where is the water" without any drainage (`03`). Each region
gets a **local water-table height and fluid** from noise; a cave below its local table fills with water
(or lava) *independently of the global sea level*. That is physically backwards — real water tables
follow drainage — but it is local, deterministic, and cheap, and it produces flooded caves and springs
at altitude that look right without a single flow-routing pass. It is the cleanest illustration of the
whole family: **replace a global physical process with a local noise field that mimics its
appearance.**

## The legacy 2D biome cascade

Worth a section because plenty of clones still use it and it is simpler to implement — and it is closer
to the rest of this skill. Before 1.18 (and in many Minecraft-likes today), biomes come from a
**layered cascade** (the `GenLayer` system): start from a coarse climate grid, then repeatedly **zoom**
(2× with a little jitter at each new cell) and apply per-layer rules (add oceans, add rivers as a
separate zoomed layer, place rare biomes, smooth edges), ending at 1:1 with the block grid. Terrain
height then comes from a **2D noise blended by the neighbourhood's biome height/variation parameters** —
closer to the heightfield-plus-material worlds of the rest of this skill, with biome-blended amplitude.
Multi-noise replaced it precisely to *unify* biome and shape into one parameter space and to make 3D
terrain (overhangs, tall mountains) possible. If your engine only needs 2D biomes and a mostly-
heightfield surface, the legacy cascade is a legitimate, lighter member of the family; if you want
caves, cliffs and biome-coherent 3D shape, use multi-noise + density.

## Where the pieces already live

The chapter is short because it mostly *routes*. Build each component from its home chapter; this file
only supplies the assembly and the constraint.

| Component of a voxel/streaming generator | Build it from |
|---|---|
| World-coordinate noise for climate + 3D density (lattice sample + interpolate) | `01`, `15` |
| Biome as parameter-space lookup / 2D map; one substrate, params vary by locale | `13`, `20` |
| Voxel / implicit representation; when height is the wrong model | `11` |
| Meshing (greedy cubic, or dual-contouring/Transvoxel/marching cubes for smooth), materials, LOD, seams, aprons | `08` |
| Deterministic decoration (ores, trees, structures) | `07` |
| Runtime substrate: typed pure nodes, cache keys, chunk requests, cancellation, publish barrier; pluggable/moddable mapgen | `14`, `15`, `23` |
| Streaming/runtime delivery mode; hybrid bake-then-refine when you want real drainage | `23` |
| Surface material palette (top blocks, per-biome cover) | `18` |

## What you give up, and how to check it

The `09` failure catalogue and its drainage oracles were written for the process-based pipeline and
**mostly do not apply** — no member of this family has a mass budget to conserve, a drainage area to
accumulate, or a repose-angle slope histogram to hit. Verifying it means checking the properties this
paradigm *does* promise:

- **Chunk-seam invisibility under independent generation.** Generate two adjacent chunks in isolation,
  in both orders, on different thread counts; the shared border blocks — density, biome, surface, water
  level — must be **bit-identical**. This is the one check that matters most; it is the seam-ownership
  contract of `08`/`23` turned into a test.
- **Determinism.** Same `(seed, x, z)` → identical chunk across runs, machines, and visit orders. Hash
  the chunk and diff.
- **Biome-parameter continuity.** The climate fields must be continuous across chunk borders (they are
  world-space noise, so they are — this catches the classic bug of evaluating noise in *tile-local*
  coordinates, the seed-contract defect in `SKILL.md` and `09`).
- **No floating/hovering artefacts at section boundaries**, and caves connect across chunks — i.e. the
  density function is genuinely global-as-a-function even though it is evaluated per chunk.
- **What you must NOT claim to verify:** that rivers reach the sea, that sediment balances, that valleys
  are fluvially carved. They are not, by construction. If the brief needs them, it is the wrong
  paradigm — go hybrid (`23`).

## Provenance

**This whole family is F/N-tier — there are no peer-reviewed papers for it, and you must not dress it as
if there were.** The authoritative sources, in order:

- **Documented and open generators.** Minecraft's datapack world-generation format — `noise_settings`,
  the density-function/noise-router graph, the `multi_noise` biome source, and surface rules — is a
  versioned JSON schema and the closest thing to a specification. **Luanti (formerly Minetest) and
  Terasology are open source**, so their mapgen is directly inspectable — a stronger primary source than
  any closed clone. Prefer these when you need a verifiable design.
- **Developer explanations** — Henrik Kniberg's talks/videos on Minecraft map generation are the source
  for the splines and the multi-noise design intent. A developer account, credible but informal; cite as
  F-tier ("Mojang's Kniberg describes…"), never as a paper.
- **Reverse-engineering & community docs** — the Minecraft Wiki's *World generation* / *Noise settings*
  pages, and the **Cubiomes** project (biome/structure reproduction from seed). Useful and largely
  correct, but community-maintained and version-drifting.
- **Closed clones are N-tier unknowns.** Creativerse and most commercial Minecraft-likes do not publish
  their generators. Describe them at the family level; never attribute a specific internal algorithm to
  a closed engine (`SKILL.md`, N-tier discipline; the tool-node crosswalk in `00`).

Three rules keep this honest: **it is version-specific** (Minecraft's 1.18 multi-noise + density system
replaced a very different pre-1.18 cascade and keeps changing — re-check against the target version);
**the parameter named "erosion" is a noise axis, not the erosion of `04`/`05`** — conflating them is the
exact category error (`SKILL.md`, "six things people call an algorithm") this skill exists to prevent;
and **name the family, not a closed clone's internals**.

## Implementation contract

Ship a voxel/streaming generator only when every row holds:

- [ ] **Locality proved.** Every stage reads only `(seed, coord)` plus a declared, bounded neighbour
      halo. No stage requires the global domain. If one does, it is baked or async-region (`23`), not
      per-chunk.
- [ ] **Determinism proved.** Same seed+coord → identical chunk across visit order, thread count, and
      machine; seams bit-identical from either neighbour. Hash-diff test in CI.
- [ ] **World-space noise.** All climate and density noise evaluated in world coordinates, never
      tile-local `(u,v)` (`SKILL.md` seed contract; the #1 seam bug).
- [ ] **Representation owned.** Density/SDF field is the source of truth; the heightmap, if any, is a
      derived readout, not an upstream input. Overhangs/caves work because the field is genuinely 3D.
- [ ] **Biome ≡ parameters.** Biome and terrain shape are read from one shared parameter space (or one
      shared biome map); you are not blending two authored terrains (`13`).
- [ ] **Materials separated.** Density (collision surface) and surface rules (appearance) are distinct
      passes (`08`, `18`).
- [ ] **Honest water.** Aquifer/noise water is labelled as such; no claim of drainage realism. Real
      hydrology, if required, is a hybrid bake (`23`).
- [ ] **Provenance recorded.** Version pinned; parameters traced to a *documented or open* generator, not
      a closed clone's guessed internals; no fabricated citations; "erosion parameter ≠ erosion process"
      stated where it could mislead.
