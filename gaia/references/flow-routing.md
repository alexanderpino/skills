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
  - { id: barnes2014, tier: P, locator: "§3 Algorithm 1 the base Priority-Flood and Algorithm 2 the Improved form that adds a plain queue; Algorithm 3 Priority-Flood+epsilon, whose line 1 requires a priority queue WITH TOTAL ORDER; §4 Ordering for why; §5 Analysis for the O(m log2 m), m <= n float bound" }
  - { id: lindsay2016, tier: P, locator: "hybrid breach/fill with a depth limit; DEM-modification comparison" }
  - { id: planchon2002, tier: P, locator: "the fill algorithm" }
  - { id: montgomery1992, tier: P, locator: "the area-slope channel-initiation threshold, A*S^2 = const" }
  - { id: braun2013, tier: P, locator: "the O(N) stack ordering: base levels first, every cell after its receiver" }
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

- **Fill** [barnes2014] raises every basin to its rim. The base algorithm pushes every cell
  through the priority queue, so on floating-point elevations it is **O(n log n)**. The paper's
  *Improved* form (its Algorithm 2) adds a plain FIFO queue for the interior of a depression
  once its rim is known, so only **m ≤ n** cells ever reach the priority queue and the bound
  falls to **O(m log₂ m)** — same result, strictly less queue traffic. O(1)-per-operation
  queues need integer elevations and a hierarchical/bucket queue, and terrain heightfields are
  float, so assume a comparison queue unless you have quantised. The epsilon variant leaves a tiny gradient across the
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
trenches through real ones. That is an aggregate result over test DEMs, not a per-basin
guarantee: on the single deep basin measured below, breaching everything moves **11.9** units of
elevation against the hybrid's **680** — and drains the basin doing it. Less modification is the
argument for the policy, not a property of every depression it meets.

**What it beats.** *Fill alone* [barnes2014] — simpler, and correct if you have no lakes to
lose. *Breach alone* [lindsay2016] — correct only if every depression in your input is an
artefact. *Planchon–Darboux fill* [planchon2002] — a different fill with the same consequence as
priority-flood.

⚠️ A common trap: applying the filled surface as the terrain. **Fill the copy you route on,
not the heightmap you render.** The filled surface exists to give the router a downhill path;
if it reaches the renderer, every basin in the world has been quietly levelled.

### The fill, and the epsilon that makes it routable

`neighbours8(c)` below is the in-bounds subset of the eight `NB` offsets tabulated in the next
section.

```
priorityFlood(z, useEpsilon):                  # z is the ROUTING COPY, never the render heightfield
    closed[:] = false
    open = min-priority-queue keyed on elevation, TOTAL ORDER
                                               # ties MUST break by insertion order -- see below.
                                               # A bare binary heap does not do this; push a
                                               # monotonic counter alongside the elevation.
    for each boundary cell b:  closed[b] = true;  open.push(b, z[b])
    while open not empty:
        c = open.pop()                         # the lowest elevation still queued
        for j in neighbours8(c):
            if closed[j]: continue
            closed[j] = true
            lift = useEpsilon ? nextafter(z[c], +INF) : z[c]
            z[j] = max(z[j], lift)
            open.push(j, z[j])
```

That is [barnes2014]'s Algorithm 1 with the epsilon lift folded in. Every cell is pushed once
and popped once, which is the O(n log n) above — the caveat, not a different algorithm. The
paper's own epsilon variant (Algorithm 3) is built on the *Improved* Algorithm 2 instead, and
if you want the `m ≤ n` bound that is the one to transcribe; the fill it produces is the same.

⚠️ **The tie-breaking is part of the algorithm, and a bare heap gets it wrong.** Algorithm 3's
first line is "Let `Open` be a priority queue **with total order**", and §4 Ordering says why:
with `ε = 0` a total and a strict weak ordering "produce the same results", but once `ε ≠ 0` a
total order is what guarantees each cell a shortest path to its flooding source, and therefore
that a depression with several equally-low outlets drains through the nearest one. `heapq`,
`std::priority_queue` and every other plain binary heap have a **strict weak** ordering: equal
elevations come out in whatever order the heap's internal swaps produced. Push a monotonic
counter as a second key.

**Measured, because the failure is invisible where you would look for it.** A flat basin with
two outlets at exactly equal elevation, epsilon fill, tie order randomised over six seeds: the
**filled surface is bit-identical every time** — so nothing that checks elevations catches
this. What moves is the drainage. Up to **13 of 361** interior cells change which outlet they
flood from, and the basin's split wanders from 181/180 to 187/174 between seeds. The fill looks
perfect and the flow directions are non-deterministic, which is the worst possible arrangement
for a bug: it survives every test of the thing it damages least.

**Route on the epsilon variant, not on the plain fill.** Transcribed and run on a 60×60 bowl
carrying 380 pits: both fills leave zero pits, the plain fill agrees to **0.0** with an
independent Planchon–Darboux fill [planchon2002] and the epsilon fill to 7e-15, and outside the
filled basins both are bit-identical to the input. But the plain fill leaves **1353 interior cells with no strictly lower neighbour** — the
flat lake surfaces — and D8 makes every one of them a self-receiving sink. Accumulate on that and
**3224 of 3600** cell-areas strand on the flats; **376** reach the domain edge. With `nextafter`,
nothing strands and every interior cell's receiver chain reaches the edge.

⚠️ **The epsilon has to be big enough to change the number.** `z + eps == z` is a flat, not a
gradient. On R32F the ulp is 6.1e-5 at 1000 m and 4.9e-4 at 8000 m, so a literal `eps = 1e-5` is
silently swallowed above ~100 m of elevation and `1e-4` is swallowed on a Himalaya. `nextafter`
is the increment that cannot be swallowed, and it costs one ulp per cell of flat.

### The hybrid, and the depth limit it is named for

```
# One pit, lowest first. Returns true if this pit was carved.
breachPit(z, p, maxCut, eps):
    cost[:] = +INF;  cost[p] = 0;  prev[p] = p;  settled = {}
    open = min-priority-queue;  open.push(p, 0);  outlet = none
    while open not empty:
        c = open.pop()
        if c in settled: continue
        settled.add(c)
        if z[c] < z[p]:  outlet = c;  break                  # lower ground reached
        for j in neighbours8(c):
            d = cost[c] + max(0, z[j] - z[p])                # excess to remove at the pit's level
            if d < cost[j]:  cost[j] = d;  prev[j] = c;  open.push(j, d)
    if outlet == none: return false                          # nothing lower anywhere: fill it
    path = [outlet]
    while last(path) != p:  path.append(prev[last(path)])
    reverse(path)                                            # p first, outlet last
    target[k] = z[p] - k * eps                               # a channel descending eps per step
    requiredCut = max over k of (z[path[k]] - target[k])
    if requiredCut > maxCut: return false                    # too deep: leave it for the fill
    for k: z[path[k]] = min(z[path[k]], target[k])
    return true
```
```
for p in pits(z), z ascending:  breachPit(z, p, maxCut, eps)
priorityFlood(z, useEpsilon = true)            # everything that refused a breach
```

**`requiredCut` versus `maxCut` is the depth limit**, and it is the only place the recommendation
becomes an instruction. Transcribed and run on a 41×41 ramp carrying a one-cell artefact pit inside
a 0.6-high rim and a bowl ringed by a ridge 10 units above its floor, the search reports a
required cut of **0.999** for the artefact and **10.0** for the bowl (two incidental pits on the
ramp report ~0) — the two populations the policy separates, with the limit between them:

| `maxCut` | breached | outcome |
|---|---|---|
| 0 | 0 | identical to fill-only (both modify 680.26) |
| 1 | 3 | artefact carved, ridge **intact**, bowl filled to a lake at 13 |
| ∞ | 4 | ridge notched, bowl drained to 3.0 — the trenching the limit exists to prevent |

All three leave zero interior sinks after the closing epsilon fill.

⚠️ The path is least-**cost**, not least-**depth**. Dijkstra here minimises summed excess, so
`requiredCut` measures the path you were handed, not the shallowest one that exists; a pit can be
filled that a better search would have breached. Constrained breaching [lindsay2016] is this
shape — a limit on the cut, and a fall back to filling when the limit is exceeded.

⚠️ **`pits(z)` = "no strictly lower neighbour" does not see a flat-floored depression**, because
every cell of the floor has an equal neighbour. On a 69-cell flat basin that test found exactly one
cell, and it was a rim accident. Take the depression cells from the fill instead: `filled > z`
marked all 72 of them.

## Receivers, and the one crossover that matters

**D8** [ocallaghan1984] sends all of a cell's water to the single steepest of its eight
neighbours. **MFD** spreads it across all downslope neighbours weighted by slope to an exponent
— `p = 1.1` in [freeman1991], `p = 1` with contour-length weighting in [quinn1991]; these are
different methods and are constantly conflated. **D∞** [tarboton1997] splits between the two
neighbours bracketing the steepest downslope facet direction — a middle course that avoids D8's
grid-direction bias without MFD's full dispersion. It is the right answer when the artefact you
are fighting is specifically the eight-direction staircase; for the network/field split below,
D8 and MFD remain the two ends worth reaching for first.

```
NB   = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1,-1), (0,-1), (1,-1)]   # dx, dy
DIST = [     1, sqrt(2),      1, sqrt(2),       1, sqrt(2),      1, sqrt(2)] # × cellSize
index(x, y) = y * width + x                # N = width * height cells, row-major

# D8 [ocallaghan1984], run on the epsilon-filled routing copy.
for each cell i at (x, y):
    receivers[i] = i;  dist[i] = 0             # self-receiving = base level
    if i is on the domain edge, or is sea: continue      # a DECLARED base level; stays self-receiving
    best = 0
    for k in 0..7:                             # i is interior, so every offset is in bounds
        j = index(x + NB[k].dx, y + NB[k].dy)
        s = (z[i] - z[j]) / (DIST[k] * cellSize)         # drop per unit LENGTH
        if s > best:  best = s;  receivers[i] = j;  dist[i] = DIST[k] * cellSize
```

**The `sqrt(2)` is the convention the rest of this corpus is built on.** A diagonal neighbour is
1.414 cellSize away, so dividing the drop by a cell *count* instead of a *distance* overstates
every diagonal slope by 41% and bends D8 towards the diagonals — the staircase D∞ exists to
remove. `dist[]` is the array `stream-power.md` divides by; get it wrong and the incision
coefficient is wrong with it. Because `s > best` starts at zero and the comparison is strict,
`receivers[i]` is always *strictly* lower, so a receiver cycle cannot form.

```
# MFD [freeman1991]: p = 1.1, and the normalisation the exponent exists for.
mfdWeights(i at (x, y), p):                     # i interior, as above
    total = 0
    for k in 0..7:
        nbr[k] = index(x + NB[k].dx, y + NB[k].dy)
        s[k]   = max(0, (z[i] - z[nbr[k]]) / (DIST[k] * cellSize))
        total += pow(s[k], p)
    if total == 0: return {}                   # nothing downslope: a pit, or a flat
    return { (nbr[k], pow(s[k], p) / total)  for every k with s[k] > 0 }
                                               # Σ w = 1 BY CONSTRUCTION — the missing half
```

Dividing by `total` is what conserves water; the exponent only sets how sharply the split
concentrates on the steepest neighbour. `p = 1.1` is [freeman1991]'s calibrated value, `p → ∞`
degenerates to D8, and `p = 1` weighted by contour length rather than bare slope is
[quinn1991] — a different method, not a tuning of this one. Measured over 3600 cells, the
weights sum to 1 within 4e-16.

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

## Accumulation, and the three arrays every downstream document consumes

`receivers[]`, `dist[]` and `A[]` are this document's output contract. `stream-power.md`,
`terrain-analysis-masks.md` and `hydraulic-erosion.md` all read them, and all three assume the
conventions above: `receivers[i] == i` means base level, `dist[]` is in world units with the
diagonal at `sqrt(2)·cellSize`, and `A` was accumulated on the *same* receivers.

```
buildStack(receivers):                         # [braun2013] — O(N), no sort, no recursion
    donors[:] = empty lists
    for i: if receivers[i] != i: donors[receivers[i]].append(i)
    stack = [];  work = every i with receivers[i] == i        # the base levels
    while work not empty:
        c = work.pop();  stack.append(c);  work.extend(donors[c])
    assert length(stack) == N               # N = cell count; see the D8 block
    return stack                               # every cell appears AFTER its receiver
```
```
A[:] = cellArea                                # or any per-cell input: rainfall, mm/step
for i in REVERSE(stack):                       # donors before receivers
    if receivers[i] != i:  A[receivers[i]] += A[i]
```

The stack is [braun2013]'s: base levels first, every cell after its receiver. The reverse pass
over it is D8 accumulation; the **forward** pass over the same stack is the order
`stream-power.md`'s solver walks. Both rules need this traversal — it is what the budget
note above means by "topological".

MFD has no single-receiver stack to build, so it orders by elevation instead, which is why it
needs a depression-free surface and not merely a receiver array:

```
A[:] = cellArea
for i in cells sorted by z DESCENDING:
    for (j, w) in mfdWeights(i, 1.1):  A[j] += w * A[i]
```

Verified on the 60×60 field above: `buildStack` returns all 3600 cells with every receiver ahead
of its donors; D8 accumulation lands exactly 3600 of 3600 cell-areas on base levels, and
reproduces the sum of a random per-cell input field to nine decimals; MFD accumulation delivers
exactly 3600 to the domain edge.

⚠️ `assert length(stack) == N` costs nothing under the strict receiver rule above, which cannot
produce a cycle. Keep it anyway: the moment someone routes across ties to escape a flat, it can,
and the symptom of a cycle is silently missing area rather than a crash.

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
| Area vanishes on flat lake surfaces; only a fraction reaches the outlet | Plain fill, not the epsilon variant — D8 makes every flat cell self-receiving | Fill with `nextafter`, on the routing copy |
| The epsilon fill still leaves flats | `eps` smaller than the ulp at that elevation on R32F | `nextafter`, never a literal |
| Diagonal channels preferred; slopes read 41% high | Drop divided by a cell count instead of `sqrt(2)·cellSize` | The `DIST` table |
| A flat-floored basin is never breached or reported | `pits()` tested for a strictly lower neighbour | Take depression cells from `filled > z` |
| Area silently missing, no crash | A receiver cycle from routing across ties | `assert length(stack) == N` |
| Rivers one cell wide, parallel, with dry gaps between | D8 used where a field was wanted | Route MFD for the field |
| River mask smeared and braided | MFD thresholded to make a network | Route D8 for the network |
| Every lake basin has flattened | The filled surface was written back to the heightfield | Fill the routing copy only |
| Canyons cut through basins that should hold water | Breaching with no depth limit | Set the limit; use the hybrid |
| Channel heads march up over ridge lines | Area-only channel threshold | Threshold on `A·S²` [montgomery1992] |
