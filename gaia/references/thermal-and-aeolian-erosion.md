---
type: Technique
title: Thermal and aeolian erosion — repose, failure and wind
description: "Slope-limited relaxation to the angle of repose, the episodic failures it cannot make, and the two aeolian models: pick the CA or the flux field."
tags: [generation, erosion, thermal, aeolian, dunes, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: musgrave1989, tier: P, locator: "the thermal-erosion pass: material above the talus angle moves to lower neighbours" }
  - { id: olsen2004, tier: F, locator: "the sweep-based fast approximation of the talus redistribution" }
  - { id: werner1995, tier: P, locator: "the slab automaton: shadow zone (no erosion there, deposition with probability 1), differential deposition probability, avalanche to repose" }
  - { id: momiji2000, tier: P, locator: "the height-dependent saltation length: wind speed-up over the windward profile lengthens a slab's hop" }
  - { id: bagnold1941, tier: F, locator: "the threshold friction velocity, and the u*^3 saltation flux law" }
  - { id: sauermann2001, tier: P, locator: "the saturation length: dq/ds = (q_sat - q)/L_sat" }
  - { id: montgomery1994, tier: P, locator: "the infinite-slope factor of safety with wetness from drainage area" }
  - { id: corominas1996, tier: P, locator: "the angle of reach L = H/tan(alpha), and its decrease with failure volume" }
---
# Thermal and aeolian erosion — repose, failure and wind

Three processes that share one idea: material moves when a *threshold* is crossed — a slope angle,
a friction angle, a shear velocity. Each is cheap, and each is the thing that makes a hydraulic
result stop looking like a hydraulic result.

## Use this

**Thermal: slope-limited relaxation to the angle of repose, run after hydraulic erosion**
[musgrave1989], with a per-neighbour distance-correct limit and double buffering. It converges,
so you can run it to a fixed point.

**Aeolian: Werner's slab automaton** [werner1995] when you want dune *forms* — barchan, transverse,
linear, star — to emerge from a wind regime. Switch to the **continuum flux/Exner chain**
[bagnold1941] [sauermann2001] when you have a spatially varying wind field and want the bed to
respond to it. (Bagnold is a 1941 monograph, not a peer-reviewed paper — canonical physics,
`F` provenance.)

**Failure: an infinite-slope mask** [montgomery1994] plus a reach-angle runout [corominas1996] when
the brief has landslide scars. Thermal alone is the slow process and can never make an episodic one.

## Thermal, and the distance bug hiding in the volume term

```
for each cell i:
    for n in 8 neighbours:
        d      = h[i] - h[n]
        dist   = (n is diagonal) ? cellSize * SQRT2 : cellSize
        dLimit = tan(talusAngle) * dist                  # PER NEIGHBOUR
        if d > dLimit: steep.append(n); dTotal += d; maxExcess = max(maxExcess, d - dLimit)
    moved = c * maxExcess / 2                            # c in 0.3..0.7 (tuning, see below)
    for n in steep:
        give = min(moved * d[n] / dTotal, (d[n] - dLimit[n]) / 2)
        Δ[i] -= give;  Δ[n] += give
h += Δ                                                   # double-buffered
```

- **Compute `dLimit` per neighbour.** A single talus value for all eight holds diagonals to a slope
  √2 times too steep, so material collapses preferentially along the cardinals and every cone grows
  a plus-shaped artefact. The same bug hides a second time in the volume term if the excess is
  measured as `d − talus` against a cardinal limit.
- **`c·maxExcess/2`.** The `/2` is what stops the surface oscillating; without it the step
  overshoots the excess. `c` in 0.3..0.7 is a **tuning range from practice, not a cited
  result** — no canonical source fixes it; lower converges more slowly, higher approaches the
  oscillation the `/2` exists to prevent.
- **The per-pair clamp** `min(share, (d − dLimit)/2)` makes each transfer individually
  non-inverting, so the step converges no matter how many neighbours are over-steep. Sizing the
  move from the single steepest neighbour and splitting it by `d/dTotal` is a fast abstraction
  [olsen2004], not physics, and on rough surfaces it micro-oscillates without the clamp.
- **Double-buffer.** In-place updates are order-dependent; this is the source of "my thermal
  erosion changes when I enable multithreading".
- 20–100 passes, and then it is done — running longer changes nothing once every slope is at or
  under repose. That range is **practitioner folklore, not a bound anyone derived**; the
  defensible stopping rule is the one the convergence gives you — iterate until the count of
  over-steep pairs stops falling, and report it.

**Use real repose angles, and vary them by material.** Dry sand 30–35°, gravel and scree 35–40°,
soil 30–45°, fractured bedrock 45–55°, competent rock up to vertical. **No source in this
bibliography is cited for that table**: they are the ranges that circulate in practice, quoted
as calibration figures rather than read out of a paper, and a soil-mechanics reference is the
place to go if a number has to be defended. A spatially varying talus angle driven by a
material mask is one extra input and it is what puts vertical rock faces above 37° scree cones.

⚠️ **It is *slope-limited* relaxation, which is not linear diffusion, and it does not replace
`D·∇²h`.** It is inert below the talus angle, so it leaves the sub-repose hillslopes stream
power needs shaping; it drives faces to planar repose where `D·∇²h` makes hilltops convex; and
it carries no `D`, so it cannot enter the `D`-versus-`K` competition that selects valley
spacing (`stream-power.md`). What it *does* replace is the visible symptom — it takes the
knife-edge off an interfluve cheaply. Run it for repose behaviour, and keep `D·∇²h` in the
solver whenever valley spacing is being tuned.

**Scree cones need a source.** Thermal only relaxes what is there. Add material at the base of
cliffs in proportion to exposed cliff area, then run thermal at 37°.

## Failure: what thermal cannot do

Thermal is grain-by-grain creep. A slope that fails all at once produces scars, fans and dammed
valleys, and it needs two expressions:

```
sinθ = slope / sqrt(1 + slope²)              # slope IS tan θ — never tan() it again
wet  = min(1, K_w * A_specific / sinθ)       # wetness from contributing area
FS   = (1 - wet * ρw/ρs) * tan(φ) / slope    # fails where FS < 1
L    = H / tan(α)                            # runout: reach angle, shrinking with volume
```

[montgomery1994] is the susceptibility model; failures concentrate in **steep, convergent, wet
hollows**, which is why the mask needs contributing area and not slope alone. [corominas1996] gives
the stop rule from 204 landslides: rockfalls reach ~30–45°, small slides 20–30°, large rock
avalanches well under 10° — so large failures run dramatically further, which is the visible
difference between a scree chute and a valley-crossing avalanche. Evacuate the scar, deposit along
the runout, then run thermal over both.

⚠️ **`slope` is a tangent, not an angle.** `tan(slope)` computes `tan(tan θ)`; it is quiet, it stays
plausible, and it understates the factor of safety by about 7% / 17% / 36% at 25° / 35° / 45°,
painting stable hillside as landslide scar. The check that catches it: with `wet = 0` the formula
collapses to `FS = tan(φ)/slope`, which must cross 1 exactly at the friction angle.

## Aeolian: two models of the same physics

Both take a **wind field** — a per-cell speed and direction — not a wind direction.

**Werner's slab automaton** [werner1995] is short, and produces barchans, transverse ridges, linear
and star dunes from the wind regime alone. Pick a random cell with sand, remove one slab, hop it
downwind by a fixed saltation length — implementations typically use ~5 cells, which is tuning
against your grid rather than a physical length — and deposit with probability `p_sand` on sand
or `p_bare` on bare ground, unless it lands in the lee shadow zone, which always captures. Then
avalanche both sites back to repose.

Three ideas carry it, and dropping any one removes the result:

1. **The shadow zone** — cells sheltered within ~15° downwind of a crest. Inside it, [werner1995]
   already specifies both halves of the rule: **no slab is eroded from a shadowed cell**, and a
   slab that lands there deposits with probability 1. That pair is what creates the slip face and
   makes dunes migrate instead of diffusing away, and it is Werner's, not a later refinement.
   [momiji2000] refines something else: a **height-dependent saltation length**, standing in for
   wind speed-up over the windward profile, so slabs launched from high on the dune are carried
   further. Without it the slab model has nothing to bound dune growth; with it, dune height
   saturates.
2. **`p_sand > p_bare`** (≈0.6 vs 0.4). Sand sticks to sand. This positive feedback is the entire
   instability; set them equal and you have a featureless sheet forever.
3. **Avalanching after every move**, or the crest grows into a spike.

Expose the **wind regime**, not the dune type: unidirectional with limited sand gives barchans;
unidirectional with abundant sand gives transverse ridges; bimodal at 90–120° gives linear dunes;
multidirectional gives star dunes. Gate everything on a sand-availability mask — Werner assumes an
infinite sheet — and keep dunes in a separate `sandDepth` field added to `h` at the end, so the
material mask is free and a later wet phase can strip them.

**The continuum chain** is four expressions and consumes a wind field directly:

```
u* = speed · κ / ln(z/z₀)                                  # law of the wall
q  = (u* > u*_t) ? C·√(d/D)·(ρ_a/g)·u*³ : 0                # threshold-gated, CUBIC
q⃗  = q · normalize(wind)
bed −= dt · ∇·q⃗ / ρ_bed                                    # Exner
```

**`∇·q⃗` changes the bed, not `q`.** Divergence deflates, convergence deposits. Feed it a
**constant** wind vector and `∇·q⃗ ≡ 0` — nothing happens, ever, at any wind speed. That is both the
sharpest argument for a wind field and the first thing to check when an aeolian pass does nothing.
[bagnold1941] gives the threshold and the cubic law: transport scales with the *cube* of shear
velocity, so doubling the wind moves eight times the sand, and the threshold is a hard gate —
averaging or smoothing a wind field destroys the effect, and a wind *rose* of a few strong events
moves far more than its mean suggests. [sauermann2001] adds the **saturation length**: flux relaxes
toward saturation over `L_sat`, which is why a bump shorter than `L_sat` cannot grow (dunes have a
minimum size instead of roughening into noise) and why the deposition maximum sits downwind of the
crest. Clamp deflation to the sand that is there; wind does not excavate bedrock.

**What it beats.** *Gaussian blur as a talus pass* — smooths ridges and cliffs, the features you
wanted, and leaves the noise. *Perona–Malik anisotropic diffusion* — the same object as thermal
with a different conductivity function; if you already run thermal you are already running it.
*A constant wind vector* — mathematically incapable of moving a grain through the Exner step.
*Authoring dune types directly* — the CA gives all four from the wind regime, and an authored
barchan field will not migrate or interact.

**Time budget.** Thermal is a handful of full-grid passes and is cheap enough to run inside an
erosion loop; the sweep form [olsen2004] converges in fewer iterations and is the one to use if it
sits in an inner loop, unnecessary as a one-off post-process. Werner is the expensive one — one
slab per iteration means of order 10⁷ iterations for a 1k map before every cell has been touched
a handful of times — arithmetic on the cell count, not a measurement — so it is authoring-time
only; batch source
cells with non-overlapping paths, or accumulate with atomics as with droplets. The continuum chain
is four full-grid expressions per step and is the one that fits a budget, but it needs a wind field
computed first.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| A plus-shaped collapse pattern on every cone | One talus limit shared by cardinals and diagonals | `dLimit = tan(talus)·dist` per neighbour |
| Thermal never quite settles, micro-oscillating | Move sized from the steepest neighbour and split without a clamp | `min(share, (d − dLimit)/2)` per pair |
| Result changes when threading is enabled | In-place neighbour updates | Double-buffer |
| Thermal ran and the terrain is still over-steepened | It ran *before* hydraulic, which re-steepened it | Hydraulic first, thermal after |
| Cliffs with no scree at their base | Thermal relaxes; it has no source | Add material at the cliff base, then relax |
| Landslide scars painted across stable hillside | `tan(slope)` on a value that is already a tangent | Use `slope` bare; verify `FS = tan(φ)/slope` at `wet = 0` |
| Every failure runs the same distance | A fixed reach angle | `α` shrinks with volume [corominas1996] |
| A featureless sand sheet, forever | `p_sand = p_bare`, so no instability | `p_sand > p_bare` [werner1995] |
| Dune crests growing into spikes | No avalanche after the slab move | Avalanche both sites to repose |
| Dunes that diffuse instead of migrating | No shadow zone, or erosion still active inside it | Shadow capture *and* no lee erosion — both are [werner1995] |
| Dunes growing without bound in the slab model | A saltation length that does not rise with height | Height-dependent hop length [momiji2000] |
| The aeolian pass changes nothing at any wind speed | Constant wind, so flux divergence is identically zero | A spatially varying wind field |
| Wind eating into bedrock | Deflation not clamped to the sand layer | Clamp to `sandDepth`; bedrock removal is abrasion, orders of magnitude slower |
| Sand roughens into noise instead of forming dunes | No saturation length | `L_sat` relaxation [sauermann2001] |
