# Flow Routing

Contents: [Order of operations](#order-of-operations) · [Depression handling](#depression-handling-mandatory) ·
[D8](#d8-ocallaghan--mark-1984) · [D∞](#d-tarboton-1997) · [MFD](#mfd-freeman-1991) ·
[Accumulation](#flow-accumulation) · [Stack ordering](#stack-ordering-braun--willett) ·
[Lakes](#lakes) · [Channel morphology](#channel-morphology-mountain-rivers) ·
[Meandering & bank erosion](#meandering--bank-erosion) ·
[River terraces](#river-terraces) · [Avulsion, crevasse splays & delta lobes](#avulsion-crevasse-splays--delta-lobes) ·
[Water sources & discharge](#water-sources--discharge) · [Sea level](#sea-level) · [Choosing](#choosing)

## Order of operations

```
height → depression handling → flow direction → flow accumulation → drainage area A
                     ↑                                                      ↓
              MANDATORY                                      stream power (04), wetness (06)
```

**Skipping depression handling is the most common defect in terrain graphs.** Symptoms:
drainage area map looks like scattered confetti instead of a branching network; rivers appear
then stop mid-slope; stream power erosion carves disconnected pits. Any DEM produced by noise
has thousands of pits — a pit is any cell with no lower neighbour, and noise generates them
everywhere.

## Depression handling (mandatory)

Two philosophies. Choose deliberately.

### Filling — Priority-Flood (Barnes, Lehman & Mulla 2014)

Raises pits to their spill elevation. Optimal, O(n) with the right queue, and trivially
correct.

```
priorityFlood(dem):
    open = priority_queue()                  // min-heap keyed by elevation
    closed = boolean grid, all false

    for each cell c on the domain edge:
        open.push(c, dem[c]); closed[c] = true

    while open not empty:
        c = open.pop()                       // lowest remaining
        for n in neighbours(c):
            if closed[n]: continue
            dem[n] = max(dem[n], dem[c])     // fill to spill level
            closed[n] = true
            open.push(n, dem[n])
```

**The epsilon variant.** Plain filling produces perfectly flat lakes, and a flat surface has no
flow direction — routing across it is undefined and D8 will make an arbitrary choice, giving
you a parallel-lines artefact across every filled basin. Fix:

```
dem[n] = max(dem[n], nextafter(dem[c], INFINITY))   // or dem[c] + eps
```

with `eps` around 1e-5 m. This creates an imperceptible gradient toward the spill point so
flow routes correctly across the filled area. **Use the epsilon variant by default.**

### Breaching (Lindsay 2016)

Carves a channel *out* of the pit to a lower cell rather than raising the pit. Geomorphically
far more plausible — real pits are usually artefacts of a missing channel, not real basins —
and it doesn't destroy the terrain inside the depression.

```
breach(dem, maxDepth, maxLength):
    for each pit p (ascending elevation):
        find least-cost path from p to a cell lower than p
            cost of a path = total material to remove
            bounded by maxLength
        if path found and depth needed <= maxDepth:
            carve dem along path, monotonically descending
        else:
            fill p with priority-flood                // fallback for genuine basins
```

**Hybrid is the right default for terrain generation:** breach shallow pits (they're noise
artefacts), fill deep ones (they're real basins that should become lakes). Threshold around
`maxDepth = 5–20 m` depending on your vertical scale.

If you fill everything, you lose all your lakes — the basins that *should* hold water get
raised to their rims. If you breach everything, you carve absurd canyons out of legitimate
craters and calderas.

### Cordonnier's approach

Cordonnier et al. (2016) handle local minima inside the erosion loop rather than as a
preprocess, by building a **lake graph**: each depression becomes a node, edges are the
spill-over passes between them, and a minimum spanning tree over that graph gives the
correct flow routing through the filled basins in O(n log n). This is more elegant and
handles the case where erosion *creates* new pits during the simulation — which it does. If
you're implementing stream power at scale, do this rather than re-running priority-flood
every timestep.

### The no-fill list: legitimate closed basins

"Depression handling is mandatory" has exceptions, and they have multiplied as the skill grew —
this is the canonical list. Each of these is a **real** closed basin: mask it so the fill/breach
node skips it (route flow *on the filled DEM*, render the original — the Lakes rule below), or the
fill erases the landform.

| Closed basin | Made by | See |
|---|---|---|
| Karst sinkholes / dolines | Dissolution; drainage goes underground | `11` |
| Glacial overdeepenings, cirque/tarn basins | Ice eroding below its outlet | `12` |
| Craters, calderas | Impact / volcanic collapse | `11` |
| Playas (endorheic basins) | No outlet at all — evaporation is the exit | `16` |
| Thermokarst pits, thaw lakes | Ground-ice melt collapse | `17` |
| Oxbow lakes | Meander neck cutoff | `03` meandering |
| Lagoons behind bay bars | Longshore deposition seals a bay | `12` |

Everything *not* on this list — the thousands of pits any noise or erosion output contains — is an
artefact and must be filled or breached. The review question (`09`) is therefore two-sided: *is
depression handling present*, **and** *are the legitimate basins masked out of it?*

## D8 (O'Callaghan & Mark 1984)

All flow from a cell goes to the single steepest downslope neighbour.

```
d8(dem, c):
    best = -INF; receiver = NONE
    for n in 8 neighbours:
        d = (n is diagonal) ? cellSize * SQRT2 : cellSize
        s = (dem[c] - dem[n]) / d                 // slope, note the distance weighting
        if s > best: best = s; receiver = n
    return receiver                                // NONE if best <= 0 → c is a pit
```

**The distance weighting is not optional.** Dividing by the diagonal distance is what makes
D8 pick correctly; using raw height differences biases every flow path toward the diagonals,
and you get a drainage network at 45°.

**Limitation.** D8 can only express 8 directions, so on a planar hillslope every cell picks
the same neighbour and flow collects into parallel lines. This is the classic D8 artefact and
it's why D8 is bad for *dispersive* flow (hillslopes, alluvial fans) and fine for *convergent*
flow (channels, once flow has already collected). It is still the right choice for extracting
a discrete channel network, because a channel network *should* be single-thread. The artefact
is one of a family — a discrete stencil printing through the physics — catalogued with its
siblings (thermal, 4-pipe, noise lattices) and the tests that catch each in `09`'s
grid-anisotropy table.

## D∞ (Tarboton 1997)

Flow direction is a continuous angle; flow is proportioned between the two neighbours that
bracket that angle. Eliminates D8's directional bias.

The domain around a cell is divided into 8 triangular facets. Each facet is defined by the
centre `e0`, a cardinal neighbour `e1` (at distance `d1 = cellSize`), and a diagonal neighbour
`e2` (at distance `d2 = cellSize` from `e1`).

```
facetSlope(e0, e1, e2, d1, d2):
    s1 = (e0 - e1) / d1                       // slope along the cardinal edge
    s2 = (e1 - e2) / d2                       // slope along the transverse edge
    r  = atan2(s2, s1)                        // direction within the facet
    s  = sqrt(s1*s1 + s2*s2)                  // magnitude

    if r < 0:                                 // direction falls outside facet, toward e1 side
        r = 0
        s = s1
    if r > atan2(d2, d1):                     // = π/4 for square cells; outside toward e2 side
        r = atan2(d2, d1)
        s = (e0 - e2) / sqrt(d1*d1 + d2*d2)
    return (r, s)

dinf(dem, c):
    best_s = 0; best_r = 0; best_facet = NONE
    for each of the 8 facets f:
        (r, s) = facetSlope(...)
        if s > best_s: best_s = s; best_r = r; best_facet = f
    if best_facet == NONE: return PIT

    // proportion flow between the facet's two neighbours
    alpha = PI / 4
    p_cardinal = (alpha - best_r) / alpha
    p_diagonal = best_r / alpha
    return (best_facet, p_cardinal, p_diagonal)
```

Note `s2` is measured from `e1` to `e2`, not from `e0` — this is the detail that gets
misimplemented most often, and it silently produces slightly wrong directions everywhere.

## MFD (Freeman 1991)

Flow is split among *all* downslope neighbours, weighted by slope to a power.

```
mfd(dem, c, p = 1.1):
    total = 0; w[8]
    for i, n in enumerate(8 neighbours):
        d = (n is diagonal) ? cellSize * SQRT2 : cellSize
        s = (dem[c] - dem[n]) / d
        w[i] = (s > 0) ? pow(s, p) : 0
        total += w[i]
    if total == 0: return PIT
    return w / total                          // fractions, sum to 1
```

**`p = 1.1` is Freeman's calibrated value** — not 1.0, not 2.0. The exponent controls
convergence: `p → 0` spreads flow evenly regardless of slope (pure dispersion), `p → ∞`
converges to D8. Freeman fitted 1.1 against measured hillslope hydrology.

Quinn et al. (1991) is the sibling variant with `p = 1` plus contour-length weighting —
slightly better on hillslopes, and worth knowing the two are usually cited interchangeably but
are not the same. To turn the code above into Quinn, *two* changes, not one:

```
w[i] = L * s                                  // p = 1  AND  the contour length multiplies in:
L    = (n is diagonal) ? 0.354 * cellSize : 0.5 * cellSize
```

Setting `p = 1` alone is neither Freeman nor Quinn: the contour length `L` is a *factor in the
weight*, not a substitute for the exponent, and without it diagonals are over-weighted by ~40%.

**MFD's weakness** is the mirror of D8's: it never lets flow fully converge, so channels stay
diffuse and rivers look like broad damp smears rather than lines. The standard fix is a
**hybrid**: MFD where `A` is small (hillslope), D8 or D∞ where `A` exceeds a channelisation
threshold. This costs almost nothing and is what most good terrain tools do.

## Flow accumulation

Drainage area `A` at a cell = its own area plus everything routed into it.

```
accumulate(dem, dirs):
    order = cells sorted by elevation, DESCENDING
    // or: topological order of the flow graph — cheaper and correct even on flats
    A = cellArea for every cell                 // ← in m², NOT a count of 1

    for c in order:
        for (receiver, fraction) in dirs[c]:
            A[receiver] += A[c] * fraction
    return A
```

**Report `A` in m², not cell counts.** A count is resolution-dependent, so every downstream
threshold ("channel starts at A > 1000") silently means something different at a different
resolution. `A_cell = cellSize²`.

Sorting by descending elevation is correct only if the DEM is depression-free and every cell's
receiver is strictly lower. After epsilon-filling this holds. Otherwise use a topological sort
of the flow DAG (Kahn's algorithm on in-degree), which is O(n) and robust.

## Stack ordering (Braun & Willett)

For stream power (`04`) you need cells in an order where every cell's receiver is processed
*before* it. Braun & Willett (2013) build this in O(n) without a sort:

```
buildStack(receivers):
    // 1. invert receivers → donors list
    donors = [[] for each cell]
    for c in all cells:
        if receivers[c] != c: donors[receivers[c]].append(c)

    // 2. depth-first from every base-level cell (receiver == self)
    stack = []
    for c where receivers[c] == c:
        dfs_push(c)                             // appends c, then recurses into donors[c]
    return stack                                // base levels first, headwaters last
```

Traverse `stack` forward and every node's receiver is already updated. Traverse it backward
and every node's donors are already updated (that's how you accumulate `A` in O(n) too).
This single data structure serves accumulation and the implicit erosion solve.

## Lakes

Once you have filled depressions with the epsilon variant, you know the lakes: they are the
cells whose filled elevation exceeds their original elevation.

```
lakeDepth = filledDem - originalDem              // > 0 inside lakes
lakeMask  = lakeDepth > 0
lakeSurface = filledDem                          // flat, by construction
```

Keep both DEMs. Route flow on the filled one; render and analyse on the original one with a
water surface at `filledDem`. Substituting the filled DEM for the terrain is the mistake that
makes every basin in the map a flat plate.

**Mountain lakes are a landform, not a new algorithm.** Every mountain lake is a filled (or
deliberately unfilled) depression whose surface is the flat spill plane above — the algorithm is
already here. What varies is *what dammed the basin*, all **L-tier** compositions (`00`):

| Lake | Basin cause | Where |
|---|---|---|
| **Tarn** | Glacial cirque overdeepening | `12` (Argudo 2020) |
| **Paternoster chain** | A staircase of glacial steps down a trough — a lake *cascade* | `12` + the lake graph below |
| **Ribbon lake** | A long overdeepened glacial trough | `12` |
| **Moraine-dammed** | A terminal/lateral moraine impounds the valley | `12` (track the moraine sediment field) |
| **Landslide / rockfall-dammed** | A slump blocks the valley, often short-lived | `05` mass wasting |
| **Crater / caldera lake** | A volcanic or impact basin | `02`/`11` primitive + a no-fill mask |

They share one computation: **the lake surface is a horizontal plane at the spill elevation**,
and a chain of connected basins spills one into the next — exactly the lake-graph / minimum-
spanning-tree cascade of Cordonnier et al. (2016) above. The overdeepened and crater cases are
genuine closed basins: **do not fill them** (`12`, `11`) — mask them so the fill node skips them,
or the lakes vanish.

## Channel morphology (mountain rivers)

Flow routing tells you *where* the rivers are; this is *what a river looks like* running down a
mountain. A steep mountain channel is not a shrunk lowland river — its reach type is set by slope
and drainage, and that governs width, roughness, and whether you draw whitewater at all.

**Reach classification by slope (Montgomery & Buffington 1997).** The canonical mountain-channel
taxonomy — cite it rather than inventing thresholds:

```
reachType(S, A):                         # S = channel slope, A = drainage area
    if S > 0.08:  return CASCADE         # continuous whitewater over boulders — steepest
    if S > 0.03:  return STEP_POOL       # rhythmic steps and plunge pools
    if S > 0.015: return PLANE_BED       # straight, featureless gravel
    if S > 0.001: return POOL_RIFFLE     # alternating bars — where meandering begins
    return DUNE_RIPPLE                   # lowland sand bed
```

The number that matters for *look*: cascade and step-pool reaches are where a mountain river
reads as whitewater, and they sit above the slope at which meandering (Howard & Knutson 1984,
`00`) can happen at all — a steep channel is straight because it *can't* meander.

**Whitewater is caused, not carved.** The foam in an Ardèche rapid is aerated turbulent flow — a
fluid-rendering job for the engine, not a heightfield feature. The terrain graph's job is the
*cause*: a steep bedrock gradient (cascade/step-pool), boulders and bedrock ledges that constrict
and step the channel (`04` clasts), and tributary debris fans pinching it. Build those and the
whitewater follows in the sim; try to put the foam in the height field and you have misplaced the
boundary between terrain and engine (`08`).

**Channel width from hydraulic geometry (Leopold & Maddock 1953).** Width scales with the square
root of discharge, and discharge scales with drainage area:

```
Q     = k_q * pow(A, 0.7)                # discharge from drainage area (basin exponent ~0.7–1)
width = k_w * sqrt(Q)                    # DOWNSTREAM hydraulic geometry: w ∝ Q^0.5
depth = k_d * pow(Q, 0.4)                #   depth ∝ Q^0.4, velocity ∝ Q^0.1 (exponents sum to 1)
```

These are Leopold & Maddock's **downstream** exponents (how a river grows heading downstream, the
terrain case) — *not* the at-a-station exponents (how one cross-section responds to a flood, where
width ∝ Q^~0.26). Use the downstream set for widening a river along its length.

Use `width` to burn the channel into the height field, or to stamp the river mask (`06`) at a
realistic, downstream-widening size — a constant-width river is an instant tell. And feed the
relations the **channel-forming discharge** — the *bankfull flood* (roughly the 1–2-year event) —
not the mean flow: channels are shaped by their floods, and a mean-flow `Q` under-sizes every
river.

**Braided vs meandering — the third planform.** The classic classification is **Leopold & Wolman
1957** (*River channel patterns: braided, meandering, and straight*, USGS Professional Paper 282-B):
a river **braids** — splits into multiple threads around mid-channel bars — where slope is high for
its discharge, bedload is heavy, and banks are erodible; it **meanders** (above) on gentler slopes
with cohesive banks. Braiding starts as a **central bar**: the coarsest bedload (`04`) stalls
mid-channel, flow splits around it, the split channels widen and deposit new bars, and the pattern
multiplies. For terrain, a braided reach is a *wide, flat, gravel-floored corridor* (a `06` material
band) stamped with a multi-thread channel pattern — anastomosing threads and lens-shaped bars —
rather than a single incised line; glacial outwash plains (`12`) and alluvial-fan surfaces (`16`)
are the type settings. Author the corridor from the routing (`03`) and the threads as a look; a
braid's individual channels shift every flood and carry no long-term memory worth simulating.

**Bedrock vs alluvial.** High in the range the river cuts *rock* (detachment-limited — stream
power, `04`); lower down it reworks its own *sediment* (transport-limited — deposition). The
incision physics for the bedrock reach is stream power; for the actual abrasion mechanism it's
**Sklar & Dietrich (2004)** (saltating bedload) and **Whipple (2004)** (bedrock rivers in active
orogens). To author a whole terrain *from* its river network instead of eroding into noise, the
graphics reference is **Génevaux et al. (2013)** — build the drainage tree first, then raise the
terrain around it.

## Meandering & bank erosion

First, the correction that the question usually needs: a river does **not** erode its banks with
waves. Coastal and marine erosion are *wave*-driven (`12`); a river migrates by **flow
curvature**. The outer, concave bank of a bend is the **cut bank** (erosion); the inner, convex
bank is the **point bar** (deposition). That erode-one-side / deposit-the-other asymmetry is the
same *shape* of process as headland-retreat-versus-bay-fill on a coast — but the driver is
curvature, not fetch, and conflating the two is a process error (`00`).

Meandering lives at the **low-slope end** of the channel-morphology spectrum above (pool-riffle
and gentler) — a steep channel is straight because it can't meander. So it runs on the floodplain,
after the valley exists, on a **centreline representation** (a polyline), not on the height field
directly — an agent model like scatter (`07`), not a per-cell sim.

```
meanderStep(centreline, Δt):
    resample(centreline, ds)                          # keep node spacing ~uniform
    for node i:  C[i] = curvature(centreline, i)      # signed, 1/radius

    # Near-bank excess velocity drives migration. The KEY detail (Ikeda, Parker & Sawai 1981;
    # Howard & Knutson 1984): it depends on UPSTREAM curvature, exponentially lagged — not on
    # local curvature alone.
    for node i:
        u_b[i] = Σ_{k≥0} C[i-k] * exp(-k * ds / L_adj)     # L_adj ≈ several channel widths
        move node i along its outward normal by E * u_b[i] * Δt    # E = bank erodibility

    # Neck cutoff → oxbow lake
    for non-adjacent pair (i, j) with |p_i − p_j| < cutoffDist:
        abandon the loop between i and j
        spawn oxbowLake(loop)                          # abandoned channel arc → a lake (Lakes above)

    burnChannel(h, centreline, width)                  # width from hydraulic geometry (above)
    depositPointBars(h, centreline, C)                 # inner banks aggrade; outer banks are cut
```

**What each detail buys:**
- **Upstream weighting is the whole thing.** Migration driven by *local* curvature alone grows
  symmetric, stationary bends. The exponential upstream lag (Ikeda–Parker–Sawai 1981) is what
  skews meanders downstream and lets them sharpen and overturn — the characteristic look. Drop it
  and you get sine waves, not meanders.
- **Neck cutoff makes oxbow lakes.** When a loop nearly closes on itself the river short-circuits
  across the neck, and the abandoned arc becomes an **oxbow lake** — a floodplain lake and a lake
  type for the Lakes table above (it silts up into a meander scar over time). Cutoff is not
  decoration: without it meanders grow forever and self-intersect.
- **The migrated swath is the floodplain.** Sweeping the channel back and forth plants **scroll
  bars** (the ridges of successive point bars) and builds a flat alluvial floodplain — which is
  where a meander belt reads as a meander belt from directly above (`09` plan view).

**Order.** This is a post-erosion, floodplain-scale process: it needs a low-gradient valley to run
in (from `04`) and it edits a centreline plus a shallow channel/floodplain in the height field.
Run it *after* the main erosion, and re-derive analysis (`06`) downstream of it like any other
height write.

**Tier.** The migration physics is P-tier (Ikeda–Parker–Sawai 1981; Howard & Knutson 1984); the
terrain realisation — burning the channel, scroll bars, oxbow fill — is the honest F-tier "look"
layered on top.

**Entrenched (incised) meanders.** When a meandering river is uplifted (`02`) it can keep its
sinuous pattern while cutting *down* into bedrock — a deep, winding **gorge** (the Ardèche, the
Goosenecks of the San Juan). Author it in that order: grow the meander belt on a low-gradient
surface *first*, then incise it with uplift + stream power (`04`). Meandering a river that is
already in a canyon is backwards — walls of rock cannot migrate. A neck that is cut off *as* it
incises leaves a **natural arch** across the abandoned neck (the Pont d'Arc), which is a void the
heightfield can't hold — see the representation warning in `11`.

## River terraces

A terrace is a **fossil valley floor stranded above the modern one** — the clearest single record
that a valley's history was not steady. You don't stamp it; it *falls out* of alternating **lateral
planation** and **vertical incision** (Bull 1990). Two kinds:

- **Strath (bedrock) terrace** — a rock bench under a thin alluvial veneer, bevelled while the river
  cut *sideways* and not *down*, then abandoned when incision resumed (Merritts, Vincent & Wohl 1994;
  Pazzaglia & Brandon 2001).
- **Fill (cut-and-fill) terrace** — the valley aggrades with sediment, then the river re-incises into
  its own fill, leaving the old fill surface as a bench (Bull 1991).

The switch between cutting sideways and cutting down is the **alluvial cover effect** (`04`, Sklar &
Dietrich 2004): bedrock incision is gated by how much sediment armours the bed. Write it as a cover
factor on the stream-power law:

```
∂h/∂t = U − K·A^m·S^n · f_c              # f_c = cover factor ∈ [0,1] (04)
f_c   = clamp(1 − alluvialDepth / H_ref, 0, 1)
```

- **Supply high** (a glacial or pluvial pulse fills the valley) → bed buried → `f_c → 0` → vertical
  incision stalls → the river planes laterally and cuts a **strath**.
- **Supply drops, or base level falls / uplift lifts the reach** (`02`) → bed re-exposed → `f_c → 1`
  → the river incises and **abandons the bevel as a terrace**.

A bench becomes a terrace once it stands more than ~one channel depth above the active bed. Run the
loop across an oscillating supply/discharge history and each cycle strands one tread — a **flight of
terraces** climbing the valley side, the fluvial twin of the marine and lacustrine terrace
staircases (`12`).

```
terraceStep(h, alluv, A, S, Δt):
    alluv += (supply(t) − transportCapacity(S)) / (W·(1−λ)) · Δt   # Exner; valley fill/scour
    f_c    = clamp(1 − alluv/H_ref, 0, 1)
    if f_c < ε:  widenValley(reach, E_lat·Δt)       # buried bed → bevel a strath at this level
    else:        h -= K·A^m·S^n·f_c·Δt               # exposed bed → incise
    h_reach += U·Δt                                  # uplift / base-level fall (02)
    tag as terrace where (strathLevel − channelBed) > channelDepth
```

**Provenance.** The strath/fill distinction and the climate-cycle framing are Bull 1990, 1991 (L —
concept, not code); strath genesis by lateral planation is Merritts, Vincent & Wohl 1994 and
Pazzaglia & Brandon 2001 (P, field studies). The **numerical model with an actual algorithm** is
**Hancock & Anderson 2002** (cover-limited bedrock incision + lateral valley-wall erosion under
oscillating climate) — the loop above is its shape.

**Watch for** reading every terrace as a climate or base-level signal. **Limaye & Lamb 2016** show
terraces form **autogenically** — a laterally migrating bedrock river cuts and abandons straths with
no external forcing at all. A terrace flight is *a* history, not necessarily *the* history; don't
over-interpret one.

## Avulsion, crevasse splays & delta lobes

Meandering (above) moves a channel *continuously*; **avulsion** moves it *discontinuously* — the
river abandons its course for a new one across the floodplain. It is what builds distributary
networks, switches delta lobes, and litters a floodplain with relict channel ridges. Canonical
review: **Slingerland & Smith 2004**.

Avulsion needs **setup and trigger** — both, not either:

- **Setup** is slow. The channel belt aggrades its own bed and levees until it sits *above* its
  floodplain — a **superelevation** of about one channel depth (Mohrig et al. 2000):
  ```
  SE = (channelBeltElev − floodplainElev) / channelDepth        # avulsion likely when SE ≳ 1
  ```
  A superelevated channel is a river perched on a ridge of its own sediment, with a steeper path to
  base level *off* the ridge than *along* it — primed to jump.
- **Trigger** is a discrete event once setup exists: a flood overtopping the levee, an ice or log
  jam, a crevasse breach. No trigger, no avulsion, however superelevated.

The **avulsion timescale** is the time to aggrade one channel depth (Jerolmack & Mohrig 2007):

```
T_A ≈ channelDepth / aggradationRate
```

and whether a river stays single-thread or **branches** into a distributary network is a competition
between lateral migration and aggradation — aggradation fast relative to bank erosion → frequent
avulsion → branching (Jerolmack & Mohrig 2007).

```
avulsionStep(h, path, Δt):
    aggrade(path, aggradationRate·Δt)                 # bed + levees rise → builds SE
    depositOverbank(near(path))                       # floodplain rises, but slower
    SE = (beltElev(path) − floodplainElev) / channelDepth
    if SE ≥ 1 and floodEvent(t) overtops levee:       # setup + trigger, both required
        breach  = steepestDescentOffTheRidge(h, path)
        newPath = routeSteepestDescent(h, breach → baseLevel)      # the 03 router, off the ridge
        if capturesMostFlow(newPath): path = newPath  # full avulsion; old belt → relict ridge
        else:                         stampCrevasseSplay(breach)   # partial: a splay lobe only
```

The cellular, heightfield-native realisation is **Jerolmack & Paola 2007**; the 3-D stochastic
stratigraphic model (slope-ratio + flood-stage avulsion rules) is **Mackey & Bridge 1995**.

**At the coast this is delta-lobe switching.** A delta builds a lobe until its channel is
superelevated and its path to the sea is longer than a fresh route across the delta plain; the river
then avulses near the apex and starts a new lobe, abandoning the old one to wave and subsidence
reworking. The Mississippi has done this through six Holocene lobes on a ~1000–1500 yr cadence
(Coleman 1988; Roberts 1997) — the **delta cycle**, and the reason a delta is a *fan of stacked
lobes*, not one static triangle. It is the coastal sibling of the alluvial-fan avulsion in `16`.

**Tier.** The superelevation criterion and avulsion timescale are P (Mohrig et al. 2000; Jerolmack &
Mohrig 2007); the cellular and stochastic realisations are P (Jerolmack & Paola 2007; Mackey &
Bridge 1995); the delta-lobe *sequence* is L — a composition (Coleman 1988; Roberts 1997).

## Water sources & discharge

Everything above routes *drainage area* `A` and treats rain as uniform — every cell contributes
its own area and nothing more. That's the right default, and it's a proxy that breaks the moment
you have a spring, a river entering from off-map, or non-uniform rainfall. The fix is to route
**discharge `Q`** (m³/s, or m³ per timestep) instead of bare area:

```
Q[c] = localRain[c] * cellArea            # distributed source — the precip field from 13
     + pointSource[c]                     # springs, authored inflows (m³/s injected at c)
# accumulate Q downstream with the SAME stack as A (above) — sources just seed the accumulation
```

Under uniform rain with no sources, `Q ∝ A` and nothing changes. With sources or an orographic
precip field (`13`), `Q` and `A` diverge — and **`Q` is the physically correct driver**: stream
power becomes `∂h/∂t = U − K·Q^m·S^n`, and wetness (`06`) and river width (above) scale with `Q`,
not `A`. This is the one change that lets a big river cross a dry region without pretending the
desert it flows through fed it — the Nile and the Colorado are exactly this.

**Kinds of source, and where each comes from:**

| Source | How to place it | Notes |
|---|---|---|
| **Distributed rain** | `localRain = precip` per cell (`13`) | The default; orographic (`13`) makes it spatial |
| **Boundary inflow** (river entering off-map) | Inject `Q_in` at an edge cell | Real water arriving — conserve it; label the edge a source, not base level |
| **Spring** | Point `Q` where the water table meets the surface | Emerges at permeable-over-impermeable **lithology contacts** (`11`), **fault** lines (`02`), or the base of a slope (high TWI, `06`) |
| **Karst resurgence** | Point `Q` where an underground stream returns | The exit of a sink (`11`) — the water that vanished into a doline reappears here |
| **Oasis / desert spring** | Point `Q` in a depression over an aquifer | A local water + vegetation source in an otherwise dry `Q` field; drives a green mask (`13`) |
| **Glacial / snowmelt** | Seasonal `Q` below the snow line | Couple to the snow field (`13`); it's why alpine rivers peak in summer |

**The authoring rule.** A spring is not a bump in the height field — it is a **source term in the
flow field**. Place it as discharge and let routing and erosion carve the valley below it, and the
stream is coherent with the rest of the drainage. Stamp a riverbed into the height instead and you
get a channel that ignores the hydrology and stops where you stopped drawing (the
spline-before-erosion caveat in `10`). Authored sources are the Št'ava (2008) extension (`04`):
springs and entering rivers as explicit inputs to the sim, not decoration.

**Sinks** are the mirror image — a cell that *removes* water: a doline swallowing a stream (`11`),
or an endorheic basin that only evaporates (the Dead Sea, the Aral). Mark them so depression
handling leaves them unfilled and accumulation terminates there instead of forcing an outlet.

## Sea level

Set it **after** erosion, not before. Sea level before erosion means erosion cuts to the wrong
base level and the drainage network is calibrated to a coastline you're about to move.

```
oceanMask = floodFillFromDomainEdge(dem <= seaLevel)
```

Use a flood fill from the edge, not a plain `dem <= seaLevel` threshold — otherwise every
inland depression below sea level becomes "ocean", including basins that are legitimately
below sea level and dry (Death Valley, the Dead Sea, the Qattara Depression).

## Choosing

| Need | Method |
|---|---|
| Channel network extraction, river polylines | D8 (after epsilon fill) |
| Drainage area for stream power | D∞ or MFD-hybrid — D8's parallel-lines artefact prints straight into the eroded terrain |
| Wetness index, moisture masks for vegetation | MFD — dispersion is the physically right behaviour on hillslopes |
| Cheapest thing that works | D8 + epsilon fill |
| Best quality per cost | D∞ + hybrid breach/fill |
