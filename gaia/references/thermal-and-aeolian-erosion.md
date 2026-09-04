---
type: Technique
title: Thermal and aeolian erosion — repose, failure and wind
description: "Slope-limited relaxation to the angle of repose, the episodic failures it cannot make, and the two aeolian models: pick the CA or the flux field."
tags: [generation, erosion, thermal, aeolian, dunes, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: musgrave1989, tier: P, locator: "the thermal-erosion pass, material above the talus angle moving to lower neighbours. NOT OPENED — SIGGRAPH 1989 sits behind the ACM paywall, which refused the download, and no open copy was reachable from here, so nothing inside it is named. The pass was read instead in olsen2004 p. 6, section Thermal erosion (NOT p. 5 sub-head Overview: the formula is on p. 6, and the Musgrave credit is on p. 5 in the preceding Erosion algorithms introduction, not under a sub-head Overview at all), which states it as h_i += c*(d_max − T)*d_i/d_total and credits Musgrave et al. 1989 as its origin" }
  - { id: olsen2004, tier: F, locator: "p. 6, section Thermal erosion (NOT p. 5, which carries the DIFFERENT single-neighbour rule h_i + c*(d_i − T) and will read as a plausible match) — the reference implementation h_i += c*(d_max − T)*d_i/d_total, the paper's own 'A reasonable value for c is 0.5', and its oscillation warning for higher c; pp. 6–7, sub-head Optimizations — the four changes that make the fast variant: Von Neumann instead of Moore, material to the LOWEST neighbour only, delta_h = d_max/2, and immediate in-place writes to the height map instead of a difference map; Figure 12 the one-pair example, Figure 13 the rotated Von Neumann stencil; sub-head Analysis, p. 7, for 60 s against 10 s over 500 iterations. The paper contains no sweep" }
  - { id: werner1995, tier: P, locator: "the slab automaton — no erosion from a shadowed cell and deposition there with probability 1, differential deposition probability on sand against bare ground, and avalanche to repose after every move. NOT OPENED — Geology is paywalled at GeoScienceWorld and no open copy was reachable from here, so no section, figure or page inside it is named" }
  - { id: momiji2000, tier: P, locator: "the height-dependent saltation length, wind speed-up over the windward profile lengthening a slab's hop. NOT OPENED — Earth Surface Processes and Landforms is paywalled at Wiley and no open copy was reachable from here, so no section, figure or page inside it is named" }
  - { id: bagnold1941, tier: F, locator: "the threshold friction velocity, and the cube-of-shear-velocity saltation flux law. NOT OPENED — the 1941 monograph was not reachable from here, so no chapter inside it is named. A monograph and not peer review, which is why it is F and not P" }
  - { id: sauermann2001, tier: P, locator: "section VI, A Minimal Model for Geomorphological Applications (NOT 'for the Sand Flux' — that title was invented), eq. 46 — the relaxation toward saturation written as dq/dx = (q/l_s)*(1 − q/q_s), a LOGISTIC form and not the linear dq/ds = (q_sat − q)/L_sat this document integrates, which is its linearisation about saturation and carries the same l_s; eq. 47 is l_s itself and Figure 5 plots it against u*/u*_t, order 0.4–0.8 m and diverging near the threshold; the paper's parameters are alpha = 0.35, z1 = 0.005 m, gamma = 0.2. Section VIII explicitly defers the minimum-dune-size and slip-face results to Kroy, Sauermann and Herrmann, so this paper is NOT the source for them" }
  - { id: montgomery1994, tier: P, locator: "the wetness-coupled infinite-slope factor of safety with wetness from drainage area, and the finding that failures concentrate in steep, convergent, wet hollows. NOT OPENED — Water Resources Research is paywalled at AGU and no open copy was reachable from here, so no section or equation inside it is named" }
  - { id: corominas1996, tier: P, locator: "the angle of reach L = H/tan(alpha) and its decrease with failure volume. NOT OPENED — Canadian Geotechnical Journal is paywalled and no open copy was reachable from here, so no section or table inside it is named; the 204-landslide sample size and the reach-angle bands quoted in the body are repeated from the bibliography entry and are unverified here" }
---
# Thermal and aeolian erosion — repose, failure and wind

Three processes that share one idea: material moves when a *threshold* is crossed — a slope angle,
a friction angle, a shear velocity. Each is cheap, and each is the thing that makes a hydraulic
result stop looking like a hydraulic result.

## Use this

**Thermal: slope-limited relaxation to the angle of repose, run after hydraulic erosion**
[musgrave1989], with a per-neighbour distance-correct limit and double buffering. Its fixed point is
exactly *no pair over its limit*, and there the pass is the identity — but nothing here proves that
point is reached, so stop on a measured over-steep count and not on a pass count.

**Aeolian: Werner's slab automaton** [werner1995] when you want dune *forms* — barchan, transverse,
linear, star — to emerge from a wind regime. Switch to the **continuum flux/Exner chain**
[bagnold1941] [sauermann2001] when you have a spatially varying wind field and want the bed to
respond to it. (Bagnold is a 1941 monograph, not a peer-reviewed paper — canonical physics,
`F` provenance.)

**Failure: an infinite-slope mask** [montgomery1994] plus a reach-angle runout [corominas1996] when
the brief has landslide scars. Thermal alone is the slow process and can never make an episodic one.

## Thermal, and the distance bug hiding in the volume term

```
Δ = 0                                                    # second buffer, zeroed once per pass
for each cell i:
    steep     = []                                       # all three reset for every i; let them
    dTotal    = 0                                        #   carry across cells and they accumulate
    maxExcess = 0                                        #   over the whole grid — pass means nothing
    for n in the 8 neighbours of i:
        d[n]      = h[i] - h[n]                          # arrays over n, not scalars: the
        dist[n]   = (n is diagonal) ? cellSize*SQRT2 : cellSize   #   transfer loop reads them
        dLimit[n] = tan(talusAngle) * dist[n]            #   again, PER NEIGHBOUR
        if d[n] > dLimit[n]:
            steep.append(n)
            dTotal    += d[n]
            maxExcess  = max(maxExcess, d[n] - dLimit[n])
    if steep is empty: continue                          # nothing over the limit here
    moved = c * maxExcess / 2                            # c in 0.3..0.7 (tuning, see below)
    for n in steep:
        give = min(moved * d[n] / dTotal, (d[n] - dLimit[n]) / 2)
        Δ[i] -= give;  Δ[n] += give                      # both writes land in Δ; h is read-only
h += Δ                                                   # one apply, after the whole grid
```

`h` is never written during the sweep and `Δ` is never read during it. That *is* the double buffer,
and it is the only reason the result does not depend on visit order.

- **Compute `dLimit` per neighbour.** The shared form is `dLimit = tan(talus)·cellSize` for all
  eight, and it is applied across a diagonal whose real run is `cellSize·√2`, so it holds diagonals
  to `tan(talus)/√2` — √2 too **shallow**, not too steep. Diagonal pairs therefore stay over that
  wrong limit longest and material collapses preferentially along the **diagonals**: the cone
  spreads toward the corners into a **diamond**. Measured, 3:1 cone relaxed at 35° to a fixed point
  (81² grid, c = 0.5): shared limit → diagonals settle at slope `0.4951 = tan(35°)/√2` against
  cardinals at `0.6992`, footprint reaching 11.31 cells along the diagonal against 9.00 along the
  cardinal, apex 5.92; per-neighbour limit → both classes settle at `0.7002 = tan 35°`, footprint
  9.90 / 9.00, apex 6.86. The same bug hides a second time in the volume term if the excess is
  measured as `d − talus` against a cardinal limit.
- **`c·maxExcess/2`.** The `/2` traces to [olsen2004] p. 7, where `Δh = d_max/2` is introduced
  for a geometric reason — it is the transfer that levels a cell with its lowest neighbour — and
  not for stability. Used here it is a **stability margin, not an oscillation cure**, and the
  difference is measurable. Unclamped, varying the effective coefficient in
  `moved = c_eff·maxExcess/2`: `c_eff` = 0.5, 1.0, 1.4 and **2.0** — that last is the `/2`
  dropped entirely at `c = 1.0` — all converge to the same fixed point at max slope 0.70021,
  with zero sign-flips over the last 300 passes. The failure past the margin is **divergence,
  not bounded oscillation**, and it begins at `c_eff ≥ 3`, so `c` in 0.3..0.7 with the `/2`
  kept leaves a 4–10× margin. `c` itself is a **tuning range from practice**: the only
  stated value anywhere in this bibliography is [olsen2004]'s "A reasonable value for c is 0.5"
  (p. 6), and Olsen is a technical report, so no *peer-reviewed* source fixes it. Lower simply
  converges more slowly. Olsen's own reason for keeping it down — that "higher values may cause
  oscillation when the changes to the height map are applied only after completion of an entire
  iteration" (p. 6) — is precisely the claim the measurements above fail to reproduce: past the
  margin the failure is divergence, not oscillation.
- **The per-pair clamp** `min(share, (d − dLimit)/2)` bounds one transfer *in isolation*: that
  transfer alone leaves the pair at `dLimit`, so it cannot invert it. It is **not** a convergence
  guarantee. A cell issues up to eight outgoing transfers and accumulates its neighbours' incoming
  ones into the same `Δ` before anything is applied, so the net pass inverts pairs freely — counting
  pairs with `h[i] > h[n]` before a pass and `h[i] < h[n]` after, 25² noisy cone, c = 0.7, 60
  passes: **2192 with the clamp, 1861 without**. The clamp slightly *increases* them. Nothing is
  monotone per pass either: on a tilted noisy plane (25², c = 0.5, 1500 passes) the total over-steep
  excess *rose* on 17 passes, by up to 0.60, and the max slope rose on 153. What is true is weaker
  and sufficient: each transfer debits `i` and credits `n` by the same amount, so **volume is
  conserved exactly** (measured drift 0 over 60 passes), and the fixed point is exactly *no pair
  over its limit*, where the pass is the identity (measured `|h_next − h|_∞ = 0`). Every
  configuration tried reached it; that is evidence, not a proof, which is why the stopping rule
  below is a measurement. Sizing the move from the single steepest neighbour and splitting it by
  `d/dTotal` is an abstraction, not physics: it is the *reference* implementation of
  [olsen2004] p. 6, `h_i += c·(d_max − T)·d_i/d_total`, which Olsen in turn credits to Musgrave
  et al. — not his fast variant, which does something else entirely (see the time budget below).
- **The clamp earns very little, and the claim it prevents micro-oscillation did not reproduce.** It
  binds on 10.7% of transfers; clamped and unclamped runs from the same 25² noisy cone end within
  0.027 of each other on 39.6 of relief, both at max slope `0.70021 ≈ tan 35°`, and the unclamped
  one gets there marginally *sooner* (1605 passes against 1612). Neither jitters: after the last
  over-steep pair clears, both are at a fixed point and the pass is the identity. Keep the clamp for
  what it does do — it caps any single transfer at half the pair's excess, which is cheap insurance
  on a rough surface — and not for a convergence argument it cannot support.
- **Double-buffer.** In-place updates are order-dependent; this is the source of "my thermal
  erosion changes when I enable multithreading".
- **The pass count goes as the square of the feature, and "20–100 passes" is off by one to two
  orders of magnitude.** This is a diffusion-like relaxation: material moves one cell per pass, so
  the cost is set by how far it has to travel. Measured, c = 0.5, 3:1 cone relaxed to 35°, stopping
  when the max slope is within 1% of `tan 35°`: **155 passes at 17², 338 at 25², 590 at 33², 1306 at
  49², 2304 at 65²** — that is `0.54·n²`. And it is the *feature* that costs, not the grid: a
  radius-8 cone takes 283 passes whether the grid is 41², 65² or 97², while radius 16 / 24 / 32 in
  the same grid take 1155 / 2611 / 4346. So halving the cell size quadruples the passes for the same
  landform. ⚠️ **A map-scale over-steepening on a 4k grid is NOT "thousands", as an earlier version
  of this line said — it is millions.** The law measured here is `passes ≈ 4.5·r²` in the feature
  radius `r`, flat to well under 1% out to `r = 64`. A feature spanning a 4096² map is `r ≈ 2048`,
  which is **~1.9·10⁷ passes**; even a quarter-map feature is ~10⁶. At 30 s per 4096² pass on one
  CPU core that is **years**, and at ~1 ms per pass on a GPU it is **hours**. Quote the radius with
  the figure — this is the one number in the section that moves by four orders with it. Raising `c` buys a constant
  factor only (c = 0.7: 110 / 239 / 419 / 929 for the same four sizes), not a better exponent.
  Running longer than the fixed point changes nothing — the pass is then the identity — but the
  fixed point is much further away than the folklore range says. The defensible stopping rule is a
  measurement: iterate until the count of over-steep pairs (or the total excess) stops falling, and
  report the count you used.

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

Every symbol, because five of them used to be undefined here:

| Symbol | What it is |
|---|---|
| `slope` | `‖∇h‖`, already a tangent (see the warning below) |
| `A_specific` | contributing area **per unit contour width**, m²/m — the `a` of TWI, computed with multi-receiver routing (`terrain-analysis-masks.md`, `flow-routing.md`) |
| `K_w` | the wetness scale: steady recharge over soil transmissivity, `R/T`, in 1/m. One knob for how wet the whole map is; raising it floods more hollows into failure |
| `wet` | the saturated fraction of the soil column, 0..1, hence the `min(1, …)` |
| `φ` | the soil's angle of internal friction — an **angle**, so `tan(φ)` is correct here; 30–40° for most soils, and `FS = 1` lands on it exactly when `wet = 0` |
| `ρw/ρs` | water density over **saturated bulk** density of the soil, ≈ 1000/1800 ≈ 0.55; it is the buoyancy term, and it is why full saturation removes about half the friction |
| `α`, `H`, `L` | the reach angle of the runout — the line from the scar crown to the toe of the deposit — with `H` the drop along that line and `L` the horizontal distance it reaches |

The numbers in that table are conventional working values, not read out of [montgomery1994] or
[corominas1996]; the two papers are cited for the *form* of the wetness-coupled factor of safety and
of the reach-angle stop rule.

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

**The continuum chain** is five expressions and consumes a wind field directly. It is five and not
four because the flux does not reach saturation instantly, and everything the prose below asks of
this model lives in that one extra line:

```
u*    = speed · κ / ln(z/z₀)                                # law of the wall
q_sat = (u* > u*_t) ? C·√(grain/grainRef)·(ρ_a/g)·u*³ : 0   # threshold-gated, CUBIC
q     = q_sat + (q_up − q_sat) · exp(−ds/L_sat)             # dq/ds = (q_sat − q)/L_sat, integrated
                                                            #   along the streamline: q_up is q
                                                            #   one step ds upwind; exact step
                                                            #   for q_sat constant over ds
                                                            #   LINEARISED Sauermann eq. 46,
                                                            #   which is logistic — see below
q⃗     = q · normalize(wind)
bed  −= dt · ∇·q⃗ / ρ_bed                                    # Exner
```

`q_up` is what makes this a **sweep, not a per-cell kernel**: cells have to be visited in upwind
order (sort by `wind·position`, or march streamlines), with `q = 0` where sand enters the domain.
That ordering is the whole cost of the saturation length, and skipping it — setting `q = q_sat`
everywhere — is the same as `L_sat = 0`.

The symbols, all of them, with the values that make the expressions run:

| Symbol | What it is |
|---|---|
| `speed`, `wind` | per-cell wind at reference height `z`: magnitude in m/s and direction |
| `z`, `z₀` | the height the wind field is quoted at, and the surface's aerodynamic roughness length, both in m. Only the ratio matters; `z₀ ≈ grain/30` for loose sand, ~1e-5 m at 250 µm, so a 10 m/s wind at `z = 10` m gives `u* ≈ 0.29` m/s |
| `κ` | von Kármán constant, 0.41 |
| `u*`, `u*_t` | friction velocity and its threshold, m/s. `u*_t ≈ 0.23` for 250 µm quartz sand in air, from [bagnold1941]'s `u*_t = A·√((ρ_s−ρ_a)/ρ_a · g · grain)` with `A ≈ 0.1` |
| `grain`, `grainRef` | grain diameter and Bagnold's 0.25 mm reference grain, both in m; the ratio is there only to keep `C` dimensionless. **Renamed from `d` and `D`** — `D` is the hillslope diffusivity of `D·∇²h` two sections up and `d` is the height drop in the thermal block |
| `C` | dimensionless sorting coefficient: ≈1.5 well-sorted dune sand, ≈2.8 poorly sorted |
| `g` | gravitational acceleration, 9.81 m/s²; `ρ_a/g` is what turns a cubed velocity into a mass flux |
| `ρ_a`, `ρ_s`, `ρ_bed` | air density 1.2 kg/m³, quartz grain density 2650 kg/m³, and the **bulk** density of the deposited bed ≈1600 kg/m³ (2650 at ~40% porosity) |
| `q` | mass flux per unit width, kg/(m·s) — at `C = 1.8`, `u* = 0.4` that is 0.014, about 1.2 t per metre of width per day. `∇·q⃗ / ρ_bed` is then m/s, which is what `bed` wants |
| `L_sat`, `ds` | saturation length and the march step, m. `L_sat` is order `(ρ_s/ρ_a)·grain ≈ 0.5` m for 250 µm sand; on the grid it must span **several cells** or the relaxation is invisible and you are back to `q = q_sat` |

Those values are conventional working numbers, not read out of the cited locators: [bagnold1941] is
`F` here and is cited for the *form* of the threshold and the cubic law, [sauermann2001] for the
form of the relaxation. `L_sat ≈ (ρ_s/ρ_a)·grain` is the drag-length scaling that circulates in the
dune literature and is **not** Sauermann's expression; his `l_s` is eq. 47, a different functional
form that diverges as `u*` approaches the threshold. The two do agree in magnitude over the wind
speeds you will actually simulate, but ⚠️ **not for the reason an earlier version of this line
gave.** It called 0.4–0.8 m "Sauermann's Figure 5 asymptote". That is the **divergent
near-threshold branch**, and the caption says the opposite — `l_s` "*is asymptotically constant for
high shear velocities, but diverges for shear velocities near the threshold*". Recomputed from
eq. 47 with the paper's own constants, the true asymptote is **0.087 m**, five to nine times
smaller, and 0.4–0.8 m occurs only around `u*/u*t ≈ 1.7–2.3`.

**What rescues the shorthand is the operating range, not the asymptote.** Sauermann names his own
regime on p. 2 — "*typical sand storms, when shear velocities are in the range of 0.18 to
0.6 m s⁻¹*" — and across the transporting part of that band `l_s` runs from about 0.46 m upward,
crossing the 0.55 m drag length at `u* ≈ 0.55 m/s`. So the two agree **where sand actually moves**,
and diverge in both directions outside it. ⚠️ **Do not size grid cells against the 0.087 m
asymptote either**: it is reached only at shear velocities far above any sand storm. A `L_sat` held
constant as the wind drops toward threshold is the shorthand's approximation and not the paper's.

⚠️ **The linear relaxation above is a linearisation of [sauermann2001], not its equation.** Sauermann's
eq. 46 is `∂q/∂x = (q/l_s)·(1 − q/q_s)` — **logistic**, so a flux far below saturation grows slowly
because it is proportional to `q` itself. Substituting `q = q_s(1 + ε)` gives `dε/dx = −ε/l_s`, which
is the linear relaxation this chain integrates, so the two share `l_s` and agree wherever the bed is
near saturation. They do not agree at a phase boundary — bedrock meeting sand with `q = 0` — where the
logistic form starts from a *stalled* flux and the linear one ramps immediately.

⚠️ **"Stalled" is exact, and it makes the obvious fix useless.** `q = 0` is not slow under eq. 46;
it is an exact fixed point, because the whole right-hand side is proportional to `q`. So
integrating eq. 46 from `q = 0` at the inflow — which an earlier version of this line told you to
do — returns `q ≡ 0` at every cell downwind, forever. Seed it instead: [sauermann2001] does exactly
this and says so, "*we used a constant influx `q_in`, much smaller than the saturated one, which
represents the inter–dune sand flux*". Give the inflow a small non-zero `q_in` and integrate eq. 46
from there; with `q_in = 0` the equation has nothing to grow.

**`∇·q⃗` changes the bed, not `q`.** Divergence deflates, convergence deposits. Feed it a
**constant** wind vector and `∇·q⃗ ≡ 0` — nothing happens, ever, at any wind speed. That is both the
sharpest argument for a wind field and the first thing to check when an aeolian pass does nothing.
[bagnold1941] gives the threshold and the cubic law: transport scales with the *cube* of shear
velocity, so doubling the wind moves eight times the sand, and the threshold is a hard gate —
averaging or smoothing a wind field destroys the effect, and a wind *rose* of a few strong events
moves far more than its mean suggests. [sauermann2001] adds the **saturation length**, and it is a
first-order low-pass along the streamline: integrating `dq/ds = (q_sat − q)/L_sat` past a bed
perturbation of wavelength `λ` passes it through with amplitude `1/√(1 + (2πL_sat/λ)²)` and lags it
by `atan(2πL_sat/λ)`. Measured on that integration: `λ = L_sat` → amplitude 0.157, lag 81°;
`λ = 10·L_sat` → 0.847, lag 32°; `λ = L_sat/4` → 0.040, lag 87°. The lag is why the deposition
maximum sits downwind of the crest. The attenuation is why short bumps do not run away: with
`q = q_sat` there is no filter and `‖∇·q⃗‖` grows as `1/λ` without bound, so the *shortest*
wavelength on the grid drives the strongest bed change (1.26 at `λ = L_sat/4` against 0.006 at
`λ = 50·L_sat`, for a 0.1-amplitude perturbation), which is exactly the roughening the failure
table blames on a missing `L_sat`; with the relaxation it saturates at `amplitude/L_sat ≈ 0.05` for
every `λ` at or below `L_sat`. Short bumps are damped rather than amplified — the full
minimum-dune-size result also needs the upwind shift of the shear stress over the bump, which these
five lines do not carry, so read this as the *mechanism* for a minimum size and not as a prediction
of what it is. That is [sauermann2001]'s own division of labour, not a hedge added here: its section
VIII says the implications of saturation transients for dune formation, "in particular, the question
of shape differences between small and large dunes or the minimum size for slip-face formation", are
deferred to a companion paper — Kroy, Sauermann and Herrmann's minimal model, which adds the wind
field. **Do not cite the saturation-length paper for the minimum dune size.** Clamp deflation to the sand that is there; wind does not excavate bedrock.

**What it beats.** *Gaussian blur as a talus pass* — smooths ridges and cliffs, the features you
wanted, and leaves the noise. *Perona–Malik anisotropic diffusion* — the same object as thermal
with a different conductivity function; if you already run thermal you are already running it.
*A constant wind vector* — mathematically incapable of moving a grain through the Exner step.
*Authoring dune types directly* — the CA gives all four from the wind regime, and an authored
barchan field will not migrate or interact.

**Time budget.** Thermal is cheap **per pass** — eight neighbour reads, one add — and expensive to
**converge**: pass count goes as the square of the over-steep feature's width in cells (155 → 1306
passes for a 3:1 cone from 17² to 49², measured above). Inside an erosion loop that is fine, and it
is the argument for putting it there rather than at the end: hydraulic re-steepens a little each
step, a handful of passes take that back, and nothing ever relaxes a whole map from scratch. As a
one-off post-process on a map that is over-steep everywhere it is **millions** of full-grid passes
— see the `4.5·r²` law above, which puts a map-spanning feature on a 4k grid near 10⁷ — and
that is where [olsen2004]'s fast variant is worth *reading* — but read it before reaching for it.
⚠️ **It is not a sweep, and this document called it one.** Olsen's four changes (pp. 6–7,
*Optimizations*) are: the Von Neumann neighbourhood instead of Moore, material distributed to the
**lowest neighbour only**, `Δh = d_max/2` instead of a fraction of the excess, and — the one that
matters here — **writing the height map immediately instead of into a difference map**. That last
change deletes, deliberately and for speed, the double buffering this document tells you to keep, so
the variant is order-dependent by construction. Olsen measures 500 iterations in 10 s against the
reference implementation's 60 s, and reports the optimised version stabilising sooner while scoring
5% worse at 500 iterations (p. 7, *Analysis*). `F`-tier, and not re-measured here. Werner is the expensive one — one slab per iteration
means of order 10⁷ iterations for a 1k map before every cell has been touched a handful of times —
arithmetic on the cell count, not a measurement — so it is authoring-time only; batch source cells
with non-overlapping paths, or accumulate with atomics as with droplets. The continuum chain is five
expressions per step — four full-grid, plus one upwind sweep for the `L_sat` relaxation — and is the
one that fits a budget, but it needs a wind field computed first.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Cones spreading into a diamond, too flat toward the corners | One talus limit shared by cardinals and diagonals caps diagonals at `tan(talus)/√2` | `dLimit = tan(talus)·dist` per neighbour |
| Thermal stopped after its pass budget with the ridges still knife-edged | A fixed pass count: the real one grows as the square of the feature's width in cells, so folklore ranges undershoot badly | Iterate until the over-steep pair count stops falling, and report the count |
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
