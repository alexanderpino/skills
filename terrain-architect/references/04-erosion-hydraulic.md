# Hydraulic Erosion

Contents: [Attribution correction](#attribution-correction-read-first) · [Choosing](#choosing-a-backbone) ·
[Pipe model](#pipe-model-mei-et-al-2007) · [Št'ava extensions](#štava-et-al-2008-extensions) ·
[Droplet](#droplet--particle-erosion) · [Stream power](#stream-power--the-important-one) ·
[Knickpoints & waterfalls](#knickpoints--waterfalls) ·
[Grain size & bedload](#grain-size-bedload--gravel-bars) · [Parameters](#parameter-reference)

## Attribution correction (read first)

The common taxonomy pairs "Hydraulic (Particle)" with Mei et al. 2007 and "Hydraulic
(Grid/Pipe)" with Št'ava et al. 2008. **This is wrong, and it matters because it sends
implementers to the wrong paper.**

- **Mei, Decaudin & Hu (2007), "Fast Hydraulic Erosion Simulation and Visualization on GPU"**
  is a **grid/pipe model**, not a particle model. It is the canonical virtual-pipe reference.
- **Št'ava, Beneš, Brisbin & Křivánek (2008), "Interactive Terrain Modeling Using Hydraulic
  Erosion"** is *also* a pipe model — it extends Mei with sediment slippage, multiple material
  layers, and boundary handling. It is a superset, not a different family.
- The **particle/droplet** method that everyone actually means has no single canonical paper.
  It descends from Musgrave, Kolb & Mace (1989) via **Hans Theobald Beyer's 2015 TU München
  thesis, "Implementation of a Method for Hydraulic Erosion"**, which borrowed Mei's transport
  capacity formulation and applied it per-droplet. It was popularised by Sebastian Lague's
  implementation.

So the honest mapping is:

| Family | Reference | Difficulty | GPU |
|---|---|---|---|
| Pipe / grid | Mei et al. 2007 | ★★★ | ✔✔ (it was designed for GPU) |
| Pipe + slippage + layers | Št'ava et al. 2008 | ★★★★ | ✔✔ |
| Droplet / particle | Beyer 2015 (after Musgrave 1989) | ★★★ | ✔ (with care — see races) |
| Stream power | Braun & Willett 2013; Cordonnier et al. 2016 | ★★★★★ | ✔ |

Also: the tectonic-plates row is usually cited as "Cordonnier 2015". The paper is
**Cordonnier et al. 2016**, *Large Scale Terrain Generation from Tectonic Uplift and Fluvial
Erosion* (Eurographics / CGF 35:2) — the same paper as the stream power row. There is one
paper doing both, not two.

## Choosing a backbone

Restating the rule from SKILL.md because this is where it gets decided:

- **< 2 km extent** → droplet. Cheap, art-directable, detail-scale, easy to tune by eye.
- **2–50 km** → pipe. Handles standing water, produces deltas and lakes, GPU-native.
- **> 50 km** → stream power. The only one that is stable over geological time and the only
  one that yields correct large-scale drainage.

The failure mode of using the wrong one: droplet erosion on a 100 km map produces scratches,
not valleys, because each droplet's lifetime covers a few hundred metres. Stream power on a
500 m map produces nothing, because there is no drainage area worth speaking of.

## Pipe model (Mei et al. 2007)

*Runnable reference: `reference-impl/erosion_pipe.py` (the water solver — where the NaN failure
lives), verified by `tests/test_pipe.py` — depth stays ≥ 0 via the step-3 scaling; 8-pipe is more
radial than 4-pipe (`09`).*

State per cell: terrain height `b`, water depth `d`, suspended sediment `s`, outflow flux
`f = (fL, fR, fT, fB)`, velocity `v`.

```
step(Δt):
  # 1. Water input
  d1 = d + Δt * rain                                     # or a source term

  # 2. Flux update — the "virtual pipes"
  for each direction D in {L, R, T, B}:
      Δh_D = (b + d1) - (b_D + d1_D)                     # hydraulic head difference
      f_D  = max(0, f_D + Δt * A * g * Δh_D / l)         # A = pipe cross-section, l = pipe length
                                                          # A/l is usually folded into one constant

  # 3. Scaling — CRITICAL, prevents negative water
      K = min(1, (d1 * lx * ly) / ((fL + fR + fT + fB) * Δt))
      f_D *= K                                            # can't drain more water than exists

  # 4. Water depth update
      ΔV = Δt * ( Σ inflow - Σ outflow )
      d2 = d1 + ΔV / (lx * ly)

  # 5. Velocity field
      Wx = (fR_left_neighbour - fL + fR - fL_right_neighbour) / 2
      Wy = (analogous in y)
      d_mean = (d1 + d2) / 2
      v = (Wx / (d_mean * ly), Wy / (d_mean * lx))        # guard d_mean → 0

  # 6. Erosion / deposition
      α = local tilt angle;  sinα = sin(max(α, α_min))    # α_min guards flat areas
      C = Kc * sinα * |v| * lmax(d1)                       # transport capacity
      if C > s:                                            # water is hungry → erode
          b  -= Ks * (C - s)
          s1  = s + Ks * (C - s)
      else:                                                # water is loaded → deposit
          b  += Kd * (s - C)
          s1  = s - Kd * (s - C)

  # 7. Sediment transport — semi-Lagrangian advection
      s(x, y) = s1(x - v.x * Δt, y - v.y * Δt)             # bilinear sample, backward trace

  # 8. Evaporation
      d = d2 * (1 - Ke * Δt)
```

**The details that decide whether it works:**

- **Step 3 is not optional.** Without the scaling factor `K`, a cell can output more water
  than it contains in one step, water depth goes negative, the velocity term divides by a
  negative, and the sim explodes within ~20 iterations. If someone reports "my pipe erosion
  produces NaN spikes", this is it, every time.
- **`lmax(d1)`** is Št'ava's addition, a soft ramp `min(d1, dmax)/dmax` that scales capacity
  down in shallow water. Without it, a 1 mm film of water on a steep slope has full transport
  capacity and carves as aggressively as a river. Mei's original omits this and it shows.
- **`α_min`** guards `sinα → 0` on flats: with capacity exactly zero, all sediment dumps
  instantly and you get a hard rim around every flat area. Clamp `sinα ≥ 0.05` or so.
- **Semi-Lagrangian advection is unconditionally stable but diffusive.** Sediment smears.
  That's usually acceptable; if not, MacCormack or BFECC costs one extra advection each.
- **CFL condition.** `Δt * |v| < cellSize`. Violate it and the advection samples past its
  neighbours and the sim goes unstable. If velocity spikes, clamp it rather than reducing `Δt`
  globally — the spike is almost always one bad cell.
- **Double-buffer everything.** In-place neighbour updates make the result depend on traversal
  order, which makes it non-deterministic under threading.
- **The 4-pipe stencil is anisotropic.** Water can only leave a cell along the cardinals —
  *stronger* axis-locking than D8's 45° bias (`03`), which at least has diagonals. Flow down a
  diagonally-oriented slope staircases, and carved channels drift toward axis alignment over
  long runs. The cone test (`09`) makes it loud: water spreading from a central source goes
  plus/diamond-shaped instead of radial, and the erosion pattern follows. The fix is the
  **8-pipe variant** with a per-pipe length — `l = cellSize` cardinal, `cellSize·√2` diagonal
  in the `Δh/l` flux term — the same distance correction D8 (`03`) and thermal erosion (`05`)
  require; the velocity field then sums all 8 fluxes componentwise (diagonal fluxes project
  onto x/y with a `1/√2` factor). If you stay with 4 pipes for cost, know the artefact and
  review under a sun sweep (`09`) — the grid-anisotropy family table there lists its siblings.

## Št'ava et al. (2008) extensions

What it adds over Mei, and why each matters:

1. **Sediment slippage.** After erosion, relax the *sediment layer* to its repose angle
   (a thermal-erosion pass restricted to the deposited material, `05`). Without this,
   deposition builds vertical sediment walls that no real material would support. This is
   the single biggest visual improvement over plain Mei.
2. **Multiple layers.** Separate bedrock and regolith with different erodibility `K`.
   Erosion consumes regolith first. This is what produces the rock-outcrop-above-scree look
   for free.
3. **Boundary conditions.** Explicit open/closed edges instead of Mei's implicit wall.
4. **Water sources and sinks** as authored inputs — springs, rivers entering the domain.

## Droplet / particle erosion

*Runnable reference: `reference-impl/erosion_droplet.py`, verified by `tests/test_droplet.py` —
deterministic; volume conserved (erode-brush + deposit-bilinear + drop-leftover); gullies are random,
not grid-aligned (`09`).*

Beyer (2015), after Musgrave et al. (1989). Simulate N independent droplets.

```
droplet(map, x, y):
    pos = (x, y);  dir = (0, 0)
    speed = 1;  water = 1;  sediment = 0

    for step in 0..maxLifetime:
        cell = floor(pos);  offset = pos - cell
        (height, grad) = bilinearHeightAndGradient(map, pos)

        # inertia blend: 0 = follow gradient exactly, 1 = go straight
        dir = dir * inertia - grad * (1 - inertia)
        if |dir| < eps: break                        # or re-randomise
        dir = normalize(dir)
        newPos = pos + dir                            # one cell per step

        if newPos out of bounds: break
        newHeight = bilinearHeight(map, newPos)
        Δh = newHeight - height                       # negative = downhill

        capacity = max(-Δh, minSlope) * speed * water * capacityFactor

        if sediment > capacity or Δh > 0:             # deposit
            amount = (Δh > 0) ? min(Δh, sediment)     # fill the pit we just hit, no more
                              : (sediment - capacity) * depositSpeed
            sediment -= amount
            depositBilinear(map, pos, offset, amount) # only the 4 cells under pos
        else:                                          # erode
            amount = min((capacity - sediment) * erodeSpeed, -Δh)
            erodeWithBrush(map, pos, radius, amount)  # spread over a disc, weighted
            sediment += amount

        speed = sqrt(max(0, speed*speed + (-Δh) * gravity))
        water *= (1 - evaporateSpeed)
        pos = newPos
```

**The details that decide whether it works:**

- **Deposition is point-wise (bilinear, 4 cells); erosion is brush-wise (a disc of radius
  2–4 cells).** This asymmetry is deliberate and essential. Erode with a single cell and you
  get 1-pixel scratches instead of valleys. Deposit with a brush and your rivers silt up into
  mush. Getting this backwards is the number one droplet-erosion bug.
- **`min(Δh, sediment)` when going uphill** — deposit only enough to fill the pit, not the
  whole load. Otherwise droplets bury the terrain in front of every rise.
- **`max(-Δh, minSlope)`** with `minSlope ≈ 0.01` prevents capacity collapsing to zero on
  flats, which would dump the entire load in one cell as a spike.
- **`speed = sqrt(speed² + Δh·gravity)`** — sign convention trips people. `Δh` is negative
  downhill; you want speed to *increase* downhill, so it's `+ (-Δh) * gravity`. Writing it
  the other way gives droplets that accelerate uphill and the terrain grows tumours.
- **Droplet count.** ~`0.5–2 × cellCount` for a visible effect; 4× for a mature look. This is
  the honest cost: a 4k map wants ~30–60M droplets.
- **Races on GPU.** Droplets write to overlapping brush footprints. Naive parallelisation is
  non-deterministic and loses deposits. Options: (a) accumulate `Δh` into a separate buffer
  with atomics and apply in a second pass; (b) partition droplets into spatial tiles with a
  gap ≥ brush radius and run tiles in a checkerboard. Option (a) is simpler and usually
  fast enough; the atomics are the bottleneck but the contention is low because droplets
  spread out quickly.
- **Droplet erosion has no standing water.** No lakes, no deltas, no ponding. If the brief
  mentions lakes, this is the wrong backbone.

## Stream power — the important one

*Runnable reference: `reference-impl/erosion_streampower.py` (Braun–Willett implicit), verified by
`tests/test_streampower.py` — the decisive check: the steady-state slope–area exponent comes out at
−m/n (`09`).*

This is the ★★★★★ row, and the reason is not the equation. The equation is one line:

```
∂h/∂t = U − K · A^m · S^n
```

- `U` = uplift rate (m/yr), from `02`
- `A` = drainage area (m²), from `03`
- `S` = slope toward the receiver = `(h_i − h_receiver) / d_i`
- `K` = erodibility (units depend on m, n — typically 1e-5 to 1e-6 for m=0.5, n=1)
- `m ≈ 0.5`, `n = 1` — the concavity ratio `m/n ≈ 0.5` is the well-constrained part;
  it's what makes river long-profiles concave, and it matches measured rivers.

The difficulty is that **the explicit solver is unstable**. `Δt` must satisfy a CFL-like
condition that scales with `A^m`, and `A` spans six orders of magnitude across a map, so the
timestep is dictated by the largest river and you need millions of steps. This is why naive
implementations either explode or take hours.

**Braun & Willett (2013) solve it implicitly in O(N), unconditionally stable.** For `n = 1`
the implicit discretisation is linear and has a closed form:

```
streamPowerStep(h, receivers, dist, A, U, K, Δt):
    stack = buildStack(receivers)          # see 03 — base levels first

    for i in stack:                        # FORWARD order: receiver already updated
        if receivers[i] == i:              # base level
            h[i] = h[i] + U[i] * Δt        # (or hold fixed, depending on BC)
            continue

        r = receivers[i]
        f = K * Δt * pow(A[i], m) / dist[i]

        h[i] = (h[i] + U[i] * Δt + f * h[r]) / (1 + f)
        h[i] = max(h[i], h[r])             # guard: never go below your receiver
```

That is the whole thing. Three lines, unconditionally stable, O(N), and it produces a proper
dendritic drainage network from a flat plate with constant uplift. `Δt` can be 1000 years or
more. A 4k map reaches equilibrium in a few hundred steps — seconds, not hours.

**For `n ≠ 1`** the implicit equation is nonlinear and needs Newton–Raphson per node:

```
        # solve  h - h_old - U*Δt + K*Δt*A^m*((h - h_r)/d)^n = 0  for h
        h_new = h[i]
        repeat until |δ| < tol:
            g  = h_new - h_old - U*Δt + K*Δt*pow(A[i], m) * pow((h_new - h[r])/d, n)
            dg = 1 + K*Δt*pow(A[i], m) * n * pow((h_new - h[r])/d, n-1) / d
            δ  = g / dg
            h_new -= δ
        h[i] = h_new
```

Converges in 2–5 iterations. Use `n = 1` unless you have a reason; `n` in [1, 2] is the
plausible range and the visual difference is subtle.

**What Cordonnier et al. (2016) add:**

1. **Coupling to tectonic uplift** — `U` from a plate simulation rather than a constant.
2. **Local minima handling inside the loop** via the lake graph + MST (see `03`). Erosion
   creates new pits as it runs; re-running priority-flood every step is O(n log n) per step
   and dominates. Their contraction approach is the fix.
3. **Hillslope diffusion** as a companion term, because stream power alone only carves
   channels and leaves the interfluves as unweathered plateaux:

```
∂h/∂t = U − K·A^m·S^n + D·∇²h
```

`D` is hillslope diffusivity, ~0.01–0.1 m²/yr. Solve the Laplacian term with a simple
explicit pass or ADI; it's stiff only if `D·Δt/cellSize²` exceeds ~0.25, so subcycle it.
**Do not skip the diffusion term.** Stream power without it produces knife-edge interfluves
and reads as obviously synthetic. In practice you can substitute a thermal erosion pass
(`05`) for the diffusion, which is cheaper and gives you the repose-angle behaviour too.

**Verification for stream power:** plot the long profile of the main channel (elevation vs
distance downstream). It must be concave. Plot `log(S)` vs `log(A)` for channel cells — it
must be a straight line of slope `−m/n ≈ −0.5`. This is a direct, cheap, quantitative check
that the implementation is correct, and it will catch an error that eyeballing never will.

## Knickpoints & waterfalls

A waterfall is a **knickpoint** — a step in the river's long profile where it departs from the
smooth concave equilibrium (the long-profile check in `09`). There is **no graphics "waterfall
algorithm"**; the mechanism is stream-power incision and the geomorphology is well constrained.
You author a waterfall by creating the *cause* of the step, not by stamping the step:

| Origin | Mechanism | Comes from |
|---|---|---|
| **Lithology contrast** | A hard bed resists while the soft rock below is stripped; the step pins on the caprock | Spatial `K` from layered lithology (`11`) |
| **Base-level fall** | The outlet drops (sea-level fall, uplift pulse, stream capture) and a step propagates upstream | Sea level (`03`), uplift (`02`) |
| **Hanging valley** | A tributary is left perched above a trunk that incised — or was glaciated — faster | Glacial trunk/tributary (`12`), or `K` contrast |

**How a knickpoint moves.** In the detachment-limited stream-power model with `n = 1` the
incision equation is a kinematic wave, so a step travels *upstream* at a celerity set by
discharge — it does not diffuse away, it migrates, preserving its height:

```
# Knickpoint celerity, n=1 stream power — the kinematic-wave speed of
#   ∂h/∂t = U − K·A^m·(∂h/∂x)   (Rosenbloom & Anderson 1994; Whipple & Tucker 1999)
C_kp(A) = K * pow(A, m)                  # metres/yr upstream — larger rivers retreat faster

retreatKnickpoints(channel, K, A, m, Δt):
    for kp in knickpoints(channel):      # cells where |dS/dx| spikes above the concave trend
        advance kp upstream by C_kp(A[kp]) * Δt along its channel
        # the face (the fall) is preserved; it only drops when two knickpoints merge
        # or it reaches a hard bed, where it stalls and the waterfall persists
```

**The consequence for a graph.** The Braun–Willett solve above already *produces* knickpoints
wherever `K` jumps — the `h[i] = max(h[i], h[r])` guard is exactly what preserves the step. So to
get a durable waterfall, give the erosion a **hard bed across the channel** (`11`); to get a
*migrating* one, drop the base level and let the solver run. What you must **not** do is carve a
vertical cliff into the height field and hope: with uniform `K` the next erosion pass relaxes it
into a rapid, because nothing pins it. Big rivers (high `A`) consume knickpoints fast — which is
why trunk streams have rapids and small tributaries keep their falls (Crosby & Whipple 2006
mapped 236 of them doing exactly this; Berlin & Anderson 2007 model the retreat).

Waterfalls also sit on the heightfield boundary (`11`): the undercut **plunge pool** and the
overhanging lip of a mature fall are voids a heightfield can't hold — you get the drop, not the
overhang.

## Grain size, bedload & gravel bars

Every model above tracks sediment as a single depth field in metres — a grey mud with no grain
size. That's fine until the brief is a river like the Ardèche: **boulders in the rapids, cobbles
in the bends, pebble beaches in the pools.** Those are not decoration — they are the visible record
of *which grains the flow could move where*, and they need one extra field, **caliber** (the
grain-size distribution), plus three pieces of well-established sediment physics.

**Grains have a size class (Wentworth 1922; Udden 1914).** The φ scale, coarse to fine:

```
boulder > cobble > pebble > granule > sand > silt > clay       # φ = -log2(D_mm)
#  >256mm   64–256   4–64     2–4      1/16–2
```

Track at least a representative **D50** (median grain diameter) field, not one undifferentiated
"sediment".

**Which grains move — critical shear stress (Shields 1936).** A grain sits still until the bed
shear stress exceeds a threshold that scales with its size:

```
τ      = ρ g d_water S                     # bed shear stress from flow depth and slope
τ_c(D) = θ_c (ρ_s − ρ) g D                 # Shields: critical shear ∝ grain diameter, θ_c ≈ 0.045
inMotion(D) = τ > τ_c(D)                   # a big clast needs a big flood
```

This is the *water* twin of Bagnold's threshold friction velocity for wind (`05`) — same idea,
same shape. Its consequence is **selective transport**: at flood peak everything moves; as the
flood wanes `τ` falls and the coarsest fraction drops first, then finer. Sorting is not authored —
it falls out of a threshold that depends on size.

**How much moves — bedload transport (Meyer-Peter & Müller 1948).** The canonical gravel formula:

```
q_b ∝ (τ* − τ*_c)^1.5                       # τ* = Shields stress; zero below threshold
```

Pebbles and cobbles travel as **bedload** — rolling and saltating along the bed — a different
transport mode from the suspended load the pipe/droplet capacity terms model. For a gravel-bed
river (Parker 1990 is the modern surface-based relation) bedload *is* the sediment budget.

**Where the coarse stuff ends up — downstream fining (Sternberg 1875).** Grain size decays
exponentially downstream, from abrasion (clasts rounding as they tumble — angular block → rounded
pebble) plus selective sorting:

```
D(x) = D0 * exp(-α x)                       # α ≈ 1e-3–1e-2 /km; boulders near source, sand far away
```

So the caliber field is high in the steep headwaters and at cliff bases (rockfall feed), low far
downstream — which is why the Ardèche has boulders in its upper rapids and rounded pebbles on its
lower beaches, not the reverse.

**The deposits — gravel bars and pebble beaches — are where competence drops.** Bedload settles
wherever `τ` falls below `τ_c` for its size: the **inner bank of a bend** (the point bar — tie to
meandering, `03`), **channel-margin slackwater**, **pool tails below a rapid**, and behind
constrictions. In a gorge that alternates pools and rapids, the pebble beaches are the pool
deposits on the inside of the entrenched bends. Two finishing details:

- **Imbrication.** Water-laid pebbles do not lie flat — they stack like tilted books, dipping
  *upstream*, the stable position against the current. Carry it into the clast scatter (`07`) as
  an orientation, or a gravel bar reads as a random rubble pile.
- **Armouring.** A gravel bed winnows its fines and leaves a coarse surface layer (the armour or
  pavement) one grain thick over finer material (Parker 1990). It's why a riverbed is cobbles on
  top and sand underneath — a `06` material distinction, not a height one.

**In the graph.** Derive a **D50 field** from local competence (`τ` from slope × discharge — `Q`
from *Water sources & discharge*, `03`), fine it downstream by Sternberg, and use it two ways: as a
**material/splat input** (`06`) for the bed texture, and as the **density-and-size driver for
discrete clast scatter** (`07`) — boulders where D50 is boulder-scale, pebble beaches where it's
pebble-scale. You never simulate a million pebbles; you simulate the *field* and scatter instances
that obey it.

**Tier.** The physics is P-tier, old and solid — Shields 1936, Meyer-Peter & Müller 1948, Sternberg
1875, Wentworth 1922 (overview: Leopold, Wolman & Miller 1964). There is **no graphics paper for
"pebble beaches"**; the terrain realisation — a caliber field feeding materials and scatter — is the
honest F-tier composition on top of P-tier sediment mechanics.

## Parameter reference

Order-of-magnitude starting points. Everything is world-unit dependent — re-derive if the
cell size changes.

| Model | Parameter | Start | Notes |
|---|---|---|---|
| Pipe | `A·g/l` (flux constant) | 1.0 | Fold `A`, `g`, `l` into one tunable |
| Pipe | `Kc` sediment capacity | 0.1–1.0 | Higher = more aggressive carving |
| Pipe | `Ks` dissolving | 0.1–0.5 | |
| Pipe | `Kd` deposition | 0.1–0.5 | `Kd > Ks` → sediment-dominated, fans; `Ks > Kd` → canyons |
| Pipe | `Ke` evaporation | 0.01–0.05 /step | Controls how far water travels |
| Pipe | `Δt` | 0.02–0.1 | Subject to CFL |
| Droplet | `inertia` | 0.05–0.3 | High = straighter, wider valleys; low = gradient-hugging scratches |
| Droplet | `capacityFactor` | 4–8 | |
| Droplet | `erodeSpeed` | 0.3 | |
| Droplet | `depositSpeed` | 0.3 | |
| Droplet | `evaporateSpeed` | 0.01–0.05 | With 0.01, lifetime ~30 steps is plenty |
| Droplet | `gravity` | 4–10 | Arbitrary units; tune with `speed` |
| Droplet | `brushRadius` | 2–4 cells | Below 2 → scratches |
| Droplet | `maxLifetime` | 30–64 | |
| Stream power | `K` | 1e-6 – 1e-5 | For m=0.5, n=1, A in m², t in yr |
| Stream power | `m` | 0.5 | 0.4–0.6 defensible |
| Stream power | `n` | 1.0 | Use 1 unless you need otherwise |
| Stream power | `D` diffusivity | 0.01–0.1 m²/yr | |
| Stream power | `Δt` | 100–5000 yr | Unconditionally stable — push it |
