# Geological Formation

Contents: [The central claim](#the-central-claim) · [Strata](#strata) · [Terracing](#terracing) ·
[Folding](#folding) · [Lithology & erodibility](#lithology--erodibility) ·
[Outcrops, mesas, badlands](#outcrops-mesas-badlands) · [When the heightfield fails](#when-the-heightfield-fails) ·
[Karst & caves](#karst--caves)

## The central claim

**Strata are a material field, not a height operator.**

This is the whole chapter. Real stratified landscapes — mesas, badlands, the Grand Canyon,
hoodoos — are not produced by carving steps into a height field. They are produced by
**erosion acting on rock of varying hardness**. Hard beds resist and form cliffs and caprock;
soft beds retreat and form slopes. The steps are an *output*.

Almost every terrain tool ships a "Terrace" node that quantises height directly. It is a fake,
it is often good enough, and you should know it's a fake, because the two approaches fail
differently:

| | Terrace node (height op) | Layered `K` (material field) |
|---|---|---|
| Cost | One node | Erosion must run |
| Steps follow | Absolute elevation | The bed geometry — so they *fold*, *tilt*, *pinch out* |
| At a valley | Steps cut across it, unrelated to the drainage | Caprock forms a rim, slopes below — correct |
| Overhangs | Impossible | Possible (with the right representation) |
| Reads as | Contour lines on a model | Geology |

Use the terrace node when it's a look. Use layered `K` when the brief says "badlands" or
"mesa" and means it.

## Strata

The material at a point depends on its **stratigraphic coordinate** — its depth within the
bed sequence — not on its current elevation.

```
stratCoord(p, h):
    s = h                                        # horizontal beds: strat coord = elevation
    s += tilt.x * p.x + tilt.y * p.y             # tilted beds (regional dip)
    s += foldAmp * sin(dot(p, foldDir) * foldFreq)   # folded beds — see below
    s += warpAmp * fbm(p * warpFreq)             # irregularity; beds are never planar
    return s

layerAt(s, bedTable):
    # bedTable = ordered list of (thickness, hardness, colour, ...)
    # Bed thickness must vary — uniform beds are the tell-tale of a fake.
    return bedTable[lookup(s mod totalThickness)]

K(p, h)     = layerAt(stratCoord(p, h), bedTable).erodibility
talus(p, h) = layerAt(stratCoord(p, h), bedTable).reposeAngle
```

Then feed `K` into stream power (`04`) or the pipe model's erodibility, and `talus` into
thermal (`05`). Erosion produces the landform.

**Bed thickness must be non-uniform.** A `sin` or a uniform modulo gives evenly-spaced steps,
which is exactly what a terrace node gives — you've done the expensive thing and got the cheap
result. Use an authored table, or a noise-driven thickness sequence with a plausible
distribution (log-normal is a reasonable stand-in for real bed thicknesses).

**Provenance:** the layered-representation idea is **Beneš & Forsbach 2001**, *Layered Data
Representation for Visual Simulation of Terrain Erosion* (SCCG). **Št'ava et al. 2008** (`04`)
carries it into the pipe model with bedrock/regolith separation. Musgrave's strata (in *Texturing
& Modeling*) is the height-op version. There is no canonical paper for the specific formulation
above — it's the obvious synthesis.

## Terracing

The height op. Fine when you want the look.

```
terrace(h, levels, sharpness):
    q = h * levels
    f = fract(q)
    f = smoothstep(0, 1, pow(f, sharpness))      # sharpness > 1 → flat treads, sharp risers
    return (floor(q) + f) / levels
```

Two fixes that cost nothing and remove most of the fakeness:

1. **Warp `h` before quantising**, not after: `terrace(h + amp*fbm(p), ...)`. The steps now
   wander rather than following perfect contours.
2. **Non-uniform levels.** Replace `floor(q)` with a lookup into an authored level table. Real
   beds are not equally thick.

**Do not run terrace after erosion.** It quantises the height field, which destroys the
drainage geometry — the rivers now run through steps rather than down. It's a `?`-shaped
question in the Legal Order: it belongs upstream, before flow routing, or it belongs only in
the material field where it doesn't touch height at all.

## Folding

Anticlines (up-folds) and synclines (down-folds). Purely a coordinate transform on the
stratigraphic coordinate — the beds fold, the topography follows only after erosion cuts into
them.

```
fold(p, h):
    # a simple sinusoidal fold train
    s = h + amp * sin(dot(p, dir) * freq + phase)
    # a single anticline
    s = h + amp * exp(-dot(p - axis, n)² / (2*sigma²))
    return s
```

The interesting result: fold the beds, then erode. Erosion cuts through the anticline crest
and exposes the *older* (deeper) beds in the middle, surrounded by concentric outcrops of
younger beds. That bullseye pattern is the classic breached-anticline map view, and you get it
for free — it is not something you could author. This is the strongest argument for the
material-field approach.

No canonical paper. It's structural geology applied as a warp.

## Lithology & erodibility

`K` is the single most useful material property, and it's a scalar.

| Rock | Relative `K` | Notes |
|---|---|---|
| Unconsolidated sediment / regolith | 5–20× | Erodes first, always |
| Shale, mudstone | 2–5× | Forms slopes |
| Sandstone | 1× | The reference; forms cliffs and caprock |
| Limestone | 0.5–2× | Depends on water chemistry — dissolves, doesn't abrade |
| Granite, basalt | 0.1–0.3× | Forms resistant highs |

These are ratios, not absolutes — the absolute `K` is calibrated once against the desired
relief in `04`. Spatially varying `K` costs one texture fetch in the erosion loop and buys:
differential erosion, caprock, outcrops, structural valleys, resistant ridges. **It is the
highest value-per-cost addition to any erosion node**, and most implementations omit it.

**Faults** (`02`) belong here, not in the height field: a fault is a line of *weakened rock*,
so implement it as a local reduction in `K`. Erosion then exploits it and cuts a valley along
the fault — which is what real faulted terrain looks like. Displacing height directly gives you
a step that erosion has no reason to respect.

## Outcrops, mesas, badlands

All **L-tier** — landforms, not algorithms (`00-index.md`). The recipes:

```
Mesa / butte      = hard caprock bed over soft beds + fluvial erosion + thermal
                    The caprock protects; the soft rock retreats; cliffs form at the caprock edge.
                    Butte = a mesa that has retreated until it's small. Same node graph.

Badlands          = high uplift + soft, uniform, poorly-consolidated rock + high drainage density
                    + minimal vegetation (so no soil cohesion)
                    The signature is drainage density: badlands are what you get when EVERY
                    hillslope is channelised. Push the channelisation threshold down (03).

Outcrop           = rockMask from (slope > tan 40°) ∪ (regolithDepth ≈ 0) ∪ (convex curvature)
                    Emerges automatically if you run layered K — you don't author it.

Cuesta / hogback  = tilted beds + differential erosion. Set `tilt` in stratCoord. Asymmetric
                    ridges: gentle dip slope, steep scarp. Free.
```

Nobody has published "the mesa algorithm" and nobody will. If asked for a paper, say so.

## When the heightfield fails

A heightfield is a function `h(x,y)` — one height per column. This makes **overhangs,
arches, hoodoo caps, sea caves, and karst impossible by construction.** No amount of
cleverness in the erosion loop changes that.

This is a principal-level call and it must be made early, because the representation decision
is not reversible cheaply:

| Need | Representation |
|---|---|
| Terrain with slopes, cliffs, valleys | Heightfield. Cheap, fast, tools exist. |
| Overhangs, arches, natural bridges | **Layered material stack** per column (Peytavie et al. 2009, *Arches*, CGF 28(2)) — a column stores an ordered list of (material, thickness) including air gaps |
| Caves, karst, full 3D | Volume / SDF. Marching cubes or dual contouring to mesh (`08`). |

**Peytavie's Arches** is the right middle ground and it's under-used: it keeps the
column-based structure (so erosion, flow routing, and analysis mostly still work) but permits
voids. If the brief is "cliffs with a few arches", this is the answer, not a full voxel
terrain.

If someone asks for arches in a heightfield pipeline, the honest answer is that the
representation forbids it — and then offer the two ways out. Agreeing to try is worse than
useless.

## Karst & caves

Dissolution, not abrasion. Limestone dissolves along fractures; the drainage goes underground;
the surface collapses into sinkholes (dolines) and the caves become a network.

**Provenance:** **Paris et al. 2021**, *Synthesizing Geologically Coherent Cave Networks* (CGF)
is the real reference for the cave network. The surface expression (sinkholes, poljes,
disappearing streams) has no canonical paper.

Surface-only approximation, if you don't need the caves:

```
karstSurface(h, solubleMask):
    sinkholes = poissonDisk(domain, r) filtered by solubleMask        # 07
    for each sinkhole:
        h -= depth * radialFalloff(d / radius)                        # inverted cone
    # Route flow (03) — the sinkholes are now pits.
    # Do NOT fill them. This is the one case where a pit is correct:
    # the water genuinely goes underground and leaves the surface network.
```

That last note is the interesting one: karst is the exception to the mandatory depression
handling in `03`. In karst, sinks are real. Fill them and you've destroyed the landform. Mark
them with a mask so the fill node skips them.

### Tower & cone karst

The dramatic karst *mountains* — the towers of Guilin and Halong Bay (**fenglin**), the cone
clusters of the wet tropics (**fengcong**) — are dissolution in thick, pure limestone under a
high water table. The mechanism is **differential vertical lowering to a base level**: corrosion
concentrates at the water table, so the soluble surface is planed down toward it while the most
massive, least-fractured rock survives as near-vertical towers standing out of a flat, alluviated
plain.

```
towerKarst(h, solubleMask, waterTable):
    # Towers survive where the rock is massive (low fracture density); everything
    # else dissolves down toward the water table (Ford & Williams 2007).
    fracture   = fbm(p * freq)                        # 01/07 — low fracture = massive = future tower
    resistance = smoothstep(hi, lo, fracture) * solubleMask
    lower      = (1 - resistance) * max(0, h - waterTable)
    h -= rate * lower                                  # massive columns barely lower → towers
    # The inter-tower plain alluviates to a flat base level, giving the steep tower/plain contact:
    h  = max(h, waterTable)  where not resistance
```

Two honesty notes, both straight from the central claim of this file:

- **Base level is the master parameter**, exactly as ELA is for glaciers (`12`). Lower the water
  table and the towers grow taller and steeper; raise it and they drown to a plain. You author
  tower karst by choosing the base level, not by sculpting towers.
- **A heightfield gets the towers but not the truth.** Mature tower karst is undercut, cave-
  riddled, and overhanging — the voids the heightfield forbids (see *When the heightfield fails*
  above). You get the steep-tower-and-flat-plain silhouette; for the notched bases and through-
  caves you need Peytavie's Arches or a volume. There is **no canonical graphics paper for tower-
  karst surface morphology** — the cave network is Paris et al. (2021), the surface is the
  composition above grounded in **Ford & Williams (2007)**.
