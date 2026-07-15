# Thermal & Aeolian Erosion

Contents: [Thermal](#thermal-erosion-musgrave-et-al-1989) · [Repose angles](#repose-angles) ·
[Talus](#talus--scree-olsen-2004) · [Aeolian overview](#aeolian-erosion) ·
[Bagnold physics](#bagnold-1941--the-physics) · [Werner dunes](#werner-1995--the-implementable-model)

## Thermal erosion (Musgrave et al. 1989)

Material on a slope steeper than the repose angle collapses. Cheap, robust, and the fastest
way to make hydraulic erosion output look right.

```
thermalStep(h, talusAngle, c):
    talus = tan(talusAngle) * cellSize          # ← max legal height difference between neighbours
    Δ = zeros_like(h)                            # double-buffer: accumulate, then apply

    for each cell i:
        dMax = 0;  dTotal = 0;  steep = []
        for n in 8 neighbours:
            d = h[i] - h[n]
            dist = (n is diagonal) ? cellSize * SQRT2 : cellSize
            dLimit = tan(talusAngle) * dist      # per-neighbour, distance-correct
            if d > dLimit:
                steep.append((n, d))
                dTotal += d
                dMax = max(dMax, d)

        if dTotal == 0: continue
        moved = c * (dMax - talus) / 2           # c ≈ 0.5; the /2 keeps it stable
        Δ[i] -= moved
        for (n, d) in steep:
            Δ[n] += moved * (d / dTotal)         # distribute proportionally to excess

    h += Δ
```

**Details that matter:**

- **The per-neighbour distance correction.** Using a single `talus` value for all 8 neighbours
  means diagonals are held to a slope √2 times too steep, so material preferentially collapses
  along the cardinals and you get a plus-shaped artefact on every cone. Compute `dLimit` per
  neighbour.
- **Double-buffer.** In-place updates make the result order-dependent. This is the classic
  source of "my thermal erosion looks different when I enable multithreading".
- **`moved = c·(dMax − talus)/2`.** The `/2` is a stability factor — without it, moving the
  full excess overshoots and the surface oscillates. `c ∈ [0.3, 0.7]`.
- **Iterations.** 20–100 passes, and it converges — running more does nothing once every
  slope is at or under repose. That convergence is a useful property: you can run it to a
  fixed point and the result is deterministic and resolution-independent.
- **It is diffusion in disguise.** Thermal erosion is a slope-limited diffusion, so it can
  stand in for the `D·∇²h` term in stream power (`04`) and give you the repose behaviour for
  free. Recommend this substitution — it's one node instead of two.

**In the graph: thermal goes *after* hydraulic.** Hydraulic over-steepens; thermal relaxes.
Reversed, hydraulic just re-steepens what thermal fixed and the thermal pass is wasted work.

**Št'ava's sediment slippage** (`04`) is thermal erosion restricted to the deposited sediment
layer, run inside the hydraulic loop. Same code, different input field, much lower talus angle
(loose sediment ~30° vs bedrock ~45°).

## Repose angles

Use real numbers. They are the difference between a landscape and a lumpy noise field.

| Material | Angle of repose | `tan` |
|---|---|---|
| Dry loose sand | 30–35° | 0.58–0.70 |
| Wet sand | 45° | 1.00 |
| Gravel | 35–40° | 0.70–0.84 |
| Scree / talus (angular rock) | 35–40° | 0.70–0.84 |
| Loose snow | 35–40° | 0.70–0.84 |
| Soil | 30–45° | 0.58–1.00 |
| Fractured bedrock | 45–55° | 1.00–1.43 |
| Competent rock face | up to vertical | — |

A **spatially varying talus angle** driven by a material mask is nearly free and buys a lot:
rock faces stay vertical, scree cones sit at 37°, sand at 33°. One extra input to the node.

## Talus / scree (Olsen 2004)

Olsen's contribution is a fast approximation for real-time use: rather than the full
8-neighbour redistribution, do a **two-pass sweep** (left-to-right then right-to-left, then
the same vertically), moving material down-gradient in a single pass per direction. It
converges to nearly the same result in a fraction of the iterations. Worth it if thermal is
in an inner loop; unnecessary as a one-off post-process.

The distinctive **scree cone** below a cliff needs one more thing than plain thermal: a
*source*. Thermal alone just relaxes what's there. To get real talus fans, add material at
the cliff base proportional to the cliff's exposed area, then run thermal:

```
screeSource = cliffMask * weatheringRate      # cliffMask = slope > ~55°
h += dilate(screeSource, radius)              # deposit at the base
run thermal with talusAngle = 37°
```

## Aeolian erosion

Two separable effects, and most graphs only need the second:

1. **Deflation** — wind stripping fines from exposed surfaces. Slow, subtle, mostly affects
   material masks rather than height.
2. **Dune formation** — sand transport and deposition. This is the one with visual payoff.

Wind erosion is ★★★★ mostly because the physics reference (Bagnold) is not implementable as
written and the implementable model (Werner) is rarely cited.

## Bagnold (1941) — the physics

The reference for *why*, not *how*. Two results worth knowing:

**Threshold friction velocity** — below this, no grains move at all:

```
u*_t = A * sqrt( ((ρ_s − ρ_a) / ρ_a) * g * d )
```

`A ≈ 0.1` for turbulent flow, `ρ_s` ≈ 2650 kg/m³ (quartz), `ρ_a` ≈ 1.22 kg/m³, `d` = grain
diameter. For 250 µm sand this gives `u*_t ≈ 0.2 m/s`, corresponding to roughly 5 m/s at 1 m
height. The practical consequence: **transport is threshold-driven and highly nonlinear**, so
a wind field that's uniformly just-below-threshold moves nothing, and one that's just-above
moves a lot. Averaging your wind field destroys the effect.

**Saltation flux** — the cubic law:

```
q = C * sqrt(d / D) * (ρ_a / g) * u*³
```

The `u*³` is the important part: transport scales with the *cube* of shear velocity. Doubling
the wind moves eight times the sand. This is why dunes form where they form.

You will not integrate this over a heightfield. Use it to justify parameter choices and to
tell the user why a linear wind-strength slider feels wrong.

## Werner (1995) — the implementable model

*Eolian dunes: computer simulations and attractor interpretation.* A cellular automaton with
sand "slabs". This is what to actually build. It is remarkably short and it produces barchans,
transverse dunes, linear dunes and star dunes purely from the wind regime — no authoring.

```
werner(h, windDir, iterations):
    L = saltationHop                             # ~5 cells, fixed
    for it in 0..iterations:
        # 1. Pick a random cell with sand
        c = randomCellWithSand()

        # 2. Remove one slab
        h[c] -= slabHeight

        # 3. Transport downwind and try to deposit
        p = c
        loop:
            p = p + windDir * L
            if p out of bounds: wrap or discard
            if inShadowZone(h, p, windDir):
                deposit = true                   # shadow zone always captures
            else:
                prob = (h[p] > 0) ? p_sand : p_bare      # p_sand ≈ 0.6, p_bare ≈ 0.4
                deposit = (random() < prob)
            if deposit:
                h[p] += slabHeight
                break

        # 4. Avalanche both sites back to repose angle
        avalanche(h, c);  avalanche(h, p)        # = local thermal erosion, 33°
```

**The three ideas that make it work:**

1. **Shadow zone.** Cells in the lee of a crest, within a 15° angle downwind, are sheltered
   and always capture sand. This is what creates the slip face and makes dunes *migrate* and
   maintain their asymmetric profile rather than diffusing away.

```
inShadowZone(h, p, windDir):
    for k in 1..shadowLength:
        q = p - windDir * k
        if h[q] > h[p] + tan(15°) * k * cellSize: return true
    return false
```

2. **`p_sand > p_bare`.** Sand is more likely to stick to sand than to bedrock. This positive
   feedback is what breaks a flat sand sheet into discrete dunes — remove it (set both equal)
   and you get a featureless sheet forever. It is the whole instability.

3. **Avalanching after every move.** Keeps slip faces at repose. Without it the dune crest
   grows into a spike.

**Wind regime determines dune type** — this is Werner's actual result and it's free:

| Wind regime | Dune type |
|---|---|
| Unidirectional, limited sand | Barchans (crescents, horns downwind) |
| Unidirectional, abundant sand | Transverse ridges ⊥ to wind |
| Bimodal (two directions ~90–120° apart) | Linear / seif dunes, parallel to the resultant |
| Multidirectional | Star dunes |

So a wind direction that varies over the iterations (cycling between two modes, say) gives you
linear dunes for free. Expose the wind regime, not the dune type.

**Sand availability mask.** Werner assumes an infinite sand sheet. For terrain, gate it: sand
only exists where a mask says so (low elevation, low slope, downwind of a source). Slabs that
land outside the mask are lost.

**Cost.** One slab move per iteration is slow; a 1k map wants ~10⁷ iterations. Parallelise by
batching: pick many source cells at once, but ensure their transport paths don't overlap
within a batch, or accumulate with atomics as with droplets (`04`).

**Coupling to the rest of the graph.** Dunes are a surface layer, not bedrock. Keep them in a
separate `sandDepth` field added to `h` at the end, so that (a) the dune material mask is free,
and (b) hydraulic erosion in a later wet-phase can strip them correctly.
