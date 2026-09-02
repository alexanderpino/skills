---
type: Technique
title: Flow routing — where the water goes
description: "Routing flow over a heightfield: which receiver rule to use, and how to handle depressions."
tags: [generation, hydrology, flow-routing, authoring-time, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: ocallaghan1984, tier: P, locator: "§3, the 8-neighbour steepest-descent rule" }
  - { id: freeman1991, tier: P, locator: "eq. 2, exponent p = 1.1" }
  - { id: quinn1991, tier: P, locator: "eq. 4, contour-length weighting" }
  - { id: tarboton1997, tier: P, locator: "§3, the 8-facet construction" }
  - { id: barnes2014, tier: P, locator: "priority-flood; the epsilon variant; complexity analysis" }
  - { id: lindsay2016, tier: P, locator: "hybrid breach/fill with a depth limit; DEM-modification comparison" }
  - { id: planchon2002, tier: P, locator: "the fill algorithm" }
  - { id: montgomery1992, tier: P, locator: "the area-slope channel-initiation threshold, A*S^2 = const" }
---
# Flow routing — where the water goes

Every drainage network, river mask, wetness map and hydraulic-erosion step starts by deciding,
for each cell, **where its water goes next**. Two decisions, in this order: what to do about
depressions, and which receiver rule to use.

## Use this

**Depressions: hybrid breach/fill with a depth limit** [lindsay2016]. Carve a channel out of
shallow pits, fill the deep ones.

**Receivers: D8 if the result is a network, MFD if the result is a field.** See the crossover
below — this is the one place the answer genuinely changes.

## Depressions first, and why the hybrid wins

A raw heightfield is full of pits. Noise makes them by construction, and an erosion loop leaves
more. Until they are dealt with, flow accumulation is meaningless: water reaches a pit and
stops, so downstream contributing area is wrong everywhere below it.

- **Fill** [barnes2014] raises every basin to its rim. With a priority queue on
  floating-point elevations it is **O(n log n)**; the O(n) result in that paper needs the
  integer variant with a bucket/radix queue, and terrain heightfields are float — so assume
  O(n log n) unless you have quantised. The epsilon variant leaves a tiny gradient across the
  filled surface so routing still has a direction. Its cost is that it *invents a spill
  point*: a noise pit becomes a lake with an outlet the terrain never had.
- **Breach** [lindsay2016] cuts a channel from the pit to lower ground instead. It removes the
  artefact rather than drowning it, but unrestricted breaching will happily trench through a
  real basin that should hold a lake.
- **Hybrid**, the recommendation: breach where the required cut is shallower than a limit, fill
  where it is deeper. [lindsay2016] argues this on the grounds of **minimising the modification
  made to the DEM**, which is the defensible form of the argument. The rule of thumb that
  shallow pits tend to be artefacts and deep ones landforms is practitioner folklore, not
  Lindsay's claim — treat the depth limit as a parameter you tune against your own noise, not
  as a physical boundary.

**Why it wins**: measured as total elevation change to the input, the hybrid modifies less than
either pure policy [lindsay2016] — fill-everything raises every basin, breach-everything
trenches through real ones.

**What it beats.** *Fill alone* [barnes2014] — simpler, and correct if you have no lakes to
lose. *Breach alone* [lindsay2016] — correct only if every depression in your input is an
artefact. *Planchon–Darboux fill* [planchon2002] — a different fill with the same consequence as
priority-flood.

⚠️ A common trap: applying the filled surface as the terrain. **Fill the copy you route on,
not the heightmap you render.** The filled surface exists to give the router a downhill path;
if it reaches the renderer, every basin in the world has been quietly levelled.

## Receivers, and the one crossover that matters

**D8** [ocallaghan1984] sends all of a cell's water to the single steepest of its eight
neighbours. **MFD** spreads it across all downslope neighbours weighted by slope to an exponent
— `p = 1.1` in [freeman1991], `p = 1` with contour-length weighting in [quinn1991]; these are
different methods and are constantly conflated. **D∞** [tarboton1997] splits between the two
neighbours bracketing the steepest downslope facet direction — a middle course that avoids D8's
grid-direction bias without MFD's full dispersion. It is the right answer when the artefact you
are fighting is specifically the eight-direction staircase; for the network/field split below,
D8 and MFD remain the two ends worth reaching for first.

The choice is decided by what consumes the result, and this is the crossover:

| You want | Use | Because |
|---|---|---|
| A **network** — river masks, channel carving, anything you will threshold | **D8** | Single-receiver routing concentrates flow into one-cell-wide lines. That is what a river mask needs, and it is why D8 survives despite being the crudest rule. |
| A **field** — wetness, moisture, vegetation density, erosion *mask* weighting | **MFD** | Multi-receiver routing spreads flow across hillslopes, which is what actually happens. D8 gives a field full of parallel one-cell stripes and dry cells between them. |

⚠️ "Erosion weighting" above means a **mask** — where to soften, where to let a pass bite. It is
not the routing an erosion *solver* runs on: stream power builds its stack from a single-receiver
array and keys incision on single-receiver accumulation, so it needs D8 (or D∞ collapsed to one
neighbour) and cannot consume an MFD field at all (`stream-power.md`).

Thresholding an MFD field to get a network produces a smeared, braided mask; smoothing a D8
field to get a wetness map produces stripes. Route twice if you need both — it is cheaper than
post-processing either into the other.

**Per-frame budget.** Both rules need a topological traversal to accumulate — that is not the
difference, and saying so would be wrong. The difference is per cell: D8 stores one receiver
and adds one contribution, MFD stores up to seven weights and accumulates a contribution from
each, so its inner loop and its memory traffic are several times D8's on the same grid.

⚠️ **No measured crossover is stated here, deliberately.** The honest answer is that it depends
on grid size, memory layout and hardware, and this skill has no benchmark to cite — writing a
millisecond figure would be a `?` wearing a P's confidence. What holds regardless: the terrain
is not changing per frame, so route once and cache. If it *is* changing per frame you have a
simulation problem, not a routing one, and `shallow-water.md` is the document you want.

## Where the network starts

Flow accumulation gives contributing area for every cell, including hilltops. A river does not
start at the drainage divide, so a threshold decides where the channel head is. The standard
criterion combines area and slope rather than using area alone: in [montgomery1992] the
critical source area falls as slope rises, in the form **A·S² ≈ constant** — *not* the product
A·S. Using area alone puts channel heads at a constant contributing area regardless of
steepness, which draws rivers straight over ridges in steep terrain.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Drainage stops mid-slope, area jumps to zero | An unhandled depression upstream | Handle depressions before accumulating |
| Rivers one cell wide, parallel, with dry gaps between | D8 used where a field was wanted | Route MFD for the field |
| River mask smeared and braided | MFD thresholded to make a network | Route D8 for the network |
| Every lake basin has flattened | The filled surface was written back to the heightfield | Fill the routing copy only |
| Canyons cut through basins that should hold water | Breaching with no depth limit | Set the limit; use the hybrid |
| Channel heads march up over ridge lines | Area-only channel threshold | Threshold on `A·S²` [montgomery1992] |
