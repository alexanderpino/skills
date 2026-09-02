---
type: Technique
title: Hydraulic erosion — droplet and pipe
description: "The two detail-scale water models: which one to run, the four details that decide whether each works, and the standing-water crossover between them."
tags: [generation, erosion, hydraulic, droplet, pipe, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: mei2007, tier: P, locator: "the eight-step pipe formulation; the outflow scaling factor K in the flux step" }
  - { id: stava2008, tier: P, locator: "sediment slippage, the material-layer stack, and the lmax shallow-water capacity ramp" }
  - { id: obrien1995, tier: P, locator: "the height-column fluid surface coupled by pipes on the head difference" }
  - { id: beyer2015, tier: F, locator: "the per-droplet transport-capacity formulation, and the erosion-brush radius" }
  - { id: musgrave1989, tier: P, locator: "the original grid hydraulic and thermal erosion passes" }
  - { id: lague_erosion, tier: F, locator: "the droplet loop, brush weights and parameter defaults in the published source" }
---
# Hydraulic erosion — droplet and pipe

Two families, one lineage, and a taxonomy that is wrong in most reference tables. The virtual-pipe
abstraction — a fluid surface as height columns coupled by pipes driven by head difference —
is [obrien1995]; [mei2007] is where it becomes an *erosion* model, and [stava2008] extends the same
model. **Neither is a particle method.** The particle method everyone means has no canonical paper:
it descends from [musgrave1989] and reaches its modern form in [beyer2015], popularised through
[lague_erosion]. Citing Mei for "particle erosion" sends the implementer to the wrong algorithm.

For maps past roughly 50 km, neither belongs here at all — see `stream-power.md`.

## Use this

**Droplet erosion [beyer2015] for detail work**: cheap, art-directable, tunable by eye, and the
easiest to get looking good on a small map.

**The pipe model [mei2007] with Šťava's slippage and layers [stava2008] the moment water has to
persist** — lakes, ponding, deltas, standing water of any kind. Droplet erosion has no water; it
has droplets, and they leave.

## The crossover, which is extent and standing water

| Map extent | Backbone | Because |
|---|---|---|
| < ~2 km | **Droplet** | A droplet's lifetime covers a few hundred metres. That is a valley here and a scratch on a 100 km map. |
| ~2–50 km | **Pipe** | Standing water, deltas, lakes; GPU-native by design [mei2007]. |
| > ~50 km | Stream power | The only one stable over geological time; see `stream-power.md`. |

The failure mode of choosing wrong is diagnostic, not subtle: droplet erosion on a large map
produces **scratches instead of valleys**, and stream power on a 500 m map produces **nothing**,
because there is no drainage area worth speaking of.

## Droplet: the asymmetry that is the whole method

```
capacity = max(-Δh, minSlope) * speed * water * capacityFactor
if sediment > capacity or Δh > 0:
    amount = (Δh > 0) ? min(Δh, sediment) : (sediment - capacity) * depositSpeed
    depositBilinear(map, pos, amount)          # 4 cells under the droplet
else:
    amount = min((capacity - sediment) * erodeSpeed, -Δh)
    erodeWithBrush(map, pos, radius, amount)   # a disc of radius 2-4 cells
speed = sqrt(max(0, speed*speed + (-Δh) * gravity))
```

- **Erosion is brush-wise; deposition is point-wise.** This asymmetry is the method. Erode through
  a single cell and you get one-pixel scratches instead of valleys; deposit through a brush and
  your rivers silt into mush. Getting it backwards is the commonest droplet bug there is.
- **`min(Δh, sediment)` going uphill.** Deposit only enough to fill the pit just hit, never the
  whole load, or droplets bury the terrain in front of every rise.
- **`minSlope ≈ 0.01`** stops capacity collapsing to zero on flats, which would dump the entire
  load into one cell as a spike.
- **The sign in the speed update.** `Δh` is negative downhill, so speed rises with `+(-Δh)·gravity`.
  Written the other way, droplets accelerate uphill and the terrain grows tumours.
- **Inertia** blends gradient-following against going straight: high gives straighter, wider
  valleys; low gives gradient-hugging scratches.
- **Count** is the honest cost: roughly 0.5–2× the cell count for a visible effect, 4× for a mature
  look. A 4k map wants tens of millions of droplets.
- **On GPU, droplets race.** Overlapping brush footprints make naive parallelism
  non-deterministic and lose deposits. Accumulate `Δh` into a separate buffer with atomics and
  apply in a second pass; contention is low because droplets spread out fast.

## Pipe: the four details, one of which is the NaN

```
Δh_D = (b + d1) - (b_D + d1_D)                      # 2. head difference per pipe
f_D  = max(0, f_D + Δt * A * g * Δh_D / l)
K    = min(1, (d1 * lx * ly) / ((fL + fR + fT + fB) * Δt))   # 3. THE scaling step
f_D *= K
C    = Kc * sin(max(α, α_min)) * |v| * lmax(d1)     # 6. transport capacity
```

- **Step 3 is not optional.** Without the scaling factor `K` a cell can output more water than it
  contains in one step; depth goes negative, the velocity term divides by it, and the sim explodes
  within about twenty iterations [mei2007]. Every report of "my pipe erosion produces NaN spikes"
  is this.
- **`lmax(d1)`**, Šťava's soft ramp on shallow water, scales capacity down in a thin film
  [stava2008]. Without it a millimetre of water on a steep slope carves like a river. Mei's
  original omits it and it shows.
- **`α_min`** guards `sin α → 0` on flats. With capacity exactly zero all sediment dumps at once
  and you get a hard rim around every flat.
- **The 4-pipe stencil is anisotropic**, more so than D8, which at least has diagonals. Flow down a
  diagonal staircases and channels drift toward the axes over long runs. The fix is 8 pipes with a
  per-pipe length (`cellSize` cardinal, `cellSize·√2` diagonal) in the `Δh/l` term, and a velocity
  field summing all eight fluxes componentwise.
- **Sediment advection is semi-Lagrangian**: unconditionally stable, diffusive, so sediment smears.
  Usually acceptable; MacCormack or BFECC costs one extra advection if it is not.
- **Double-buffer everything**, or the result depends on traversal order and stops being
  deterministic under threading.

**Šťava's three additions over Mei, in value order** [stava2008]: sediment slippage — a thermal
pass restricted to the deposited layer (`thermal-and-aeolian-erosion.md`), which is the single
biggest visual improvement, because plain Mei builds vertical sediment walls no material would
support; **material layers**, bedrock under regolith with different `K`, which buys the
rock-outcrop-above-scree look for free; and **explicit per-cell boundary conditions** instead of
Mei's implicit wall.

**What it beats.** *Mei alone* [mei2007] — correct and GPU-native, but the sediment walls and the
full-capacity thin film are visible, and both fixes are one pass each. *Musgrave's original grid
model* [musgrave1989] — the ancestor of both families and the origin of the thermal pass; superseded
as an erosion model, still the correct citation for the lineage. *Lague's implementation*
[lague_erosion] — no canonical paper; it follows [beyer2015] and is the code most people have
actually read, which makes it the useful cross-check on brush weights and defaults, not a source
for the method. *Thermal erosion alone* — relaxes what is there; it cuts nothing and moves no water.

**Time budget.** Both are authoring-time. Droplet cost is droplet count × lifetime, decoupled from
resolution, so it is the one you can dial down to interact with; pipe cost is a fixed number of
full-grid passes per step with `Δt` bounded by `Δt·|v| < cellSize`, so it is the one that maps onto
a compute shader and the one to pick if the tool must show the erosion progressing. Neither is a
per-frame operation at authoring resolution. If velocity spikes, clamp it rather than reducing
`Δt` globally — the spike is almost always one bad cell.

**Order in the graph: hydraulic first, thermal after.** Hydraulic over-steepens and thermal
relaxes; reversed, the hydraulic pass re-steepens what thermal fixed and the thermal pass was
wasted work.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| NaN spikes within ~20 iterations | Pipe outflow exceeds the water in the cell; depth goes negative | The step-3 scaling factor `K` [mei2007] |
| One-pixel scratches instead of valleys | Droplet erosion applied per-cell instead of through a brush | Erode through a disc of 2–4 cells |
| Rivers silted into mush | Deposition spread through a brush | Deposit bilinearly, 4 cells |
| The terrain grows tumours on the uphill side | Sign error in the speed update; droplets accelerate uphill | `speed² += (-Δh)·gravity` |
| An isolated spike where a droplet stopped | Capacity collapsed to zero on a flat | `minSlope ≈ 0.01` |
| Vertical walls of deposited sediment | No sediment slippage | A repose-angle pass on the deposit layer [stava2008] |
| A thin film carving like a river | Capacity not ramped by depth | `lmax(d1)` [stava2008] |
| A hard rim around every flat area | `sin α → 0`, so capacity is exactly zero | Clamp `sin α ≥ ~0.05` |
| Channels drifting toward the grid axes | 4-pipe cardinal-only stencil | 8 pipes with per-pipe length |
| Different result with threading enabled | In-place neighbour updates | Double-buffer |
| Deposits missing on GPU, non-repeatably | Droplet brush footprints racing | Accumulate with atomics, apply in a second pass |
| Scratches instead of valleys on a large map | Droplet lifetime covers a fraction of the domain | Change backbone: pipe, or stream power |
| The brief mentions lakes and there are none | Droplet erosion has no standing water | Pipe model |
