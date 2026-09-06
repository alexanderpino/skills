---
type: Technique
title: Tectonic uplift — the field erosion runs against
description: "Uplift is an input to erosion, not terrain: how to author U, when a plate simulation earns its cost, and the isostatic response that makes peaks rise as valleys cut."
tags: [generation, tectonics, uplift, isostasy, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: cordonnier2016, tier: P, locator: "§3.1 eq. 1 — dh(p)/dt = u(p) - k*A(p)^m*s(p)^n, with m/n ≈ 0.5 and the paper taking m = 0.5, n = 1; §4.3 Lake Overflow — the lake super-graph that routes local minima" }
  - { id: cortial2019, tier: P, locator: "§3 Overview — plates are spherical Voronoi cells of a noise-warped geodetic distance, moving by rigid rotation s(p) = ω w × p; §4.1 subduction, §4.2 collision, §4.4 rifting" }
  - { id: turcotte2014, tier: F, locator: "the Airy root r = pc*h/(pm-pc), and the thin-elastic-plate equation D grad^4 w + delta-rho*g*w = q with D = E*Te^3/12(1-v^2)" }
  - { id: molnar1990, tier: P, locator: "§Definitions of uplift and Fig. 2, p. 30 — eroding ΔT lowers the surface by ΔT*(pm-pc)/pm and raises rock by (pc/pm)*ΔT, their 5ΔT/6; Fig. 2b incises a highland of mean elevation h, dropping the mean to about 5h/6 while peaks rise to about 1.8h" }
---
# Tectonic uplift — the field erosion runs against

Tectonics does not produce terrain. It produces an **uplift field `U(x,y)`** in metres per year,
whose only consumer is the uplift term of a long-running erosion solve (`stream-power.md`). The
realism does not come from the plate model, which is crude. It comes from running fluvial erosion
against a spatially varying `U` until the landscape reaches dynamic equilibrium, where
`U = K·A^m·S^n` and slope self-organises to `S = (U / (K·A^m))^(1/n)` — steep where uplift is high,
gentle where drainage area is large [cordonnier2016]. That relationship is what makes a range read
as a range, and no amount of noise reproduces it.

## Use this

**Author `U` directly and hand it to stream power.** A distance field from a spline, a blurred
painted mask, a low-frequency field remapped so most of the domain is ~0 — or a constant.

Reach for a **plate simulation only when plate boundaries and crustal history are wanted as
outputs**, not as a route to a mountain range. A tectonics node whose output goes anywhere except
the uplift term of a long-running erosion sim is decoration, and should be replaced by a cheaper
large-scale mask.

## Authoring U

| Source | Produces |
|---|---|
| Distance field from a spline, `U = A·exp(-d²/2σ²)` | One linear range with a natural cross-section |
| Painted or spline mask, blurred | Directed ranges, art-directable |
| Low-frequency fBm remapped so most of the domain is ~0 | Scattered massifs |
| **Constant `U`** | A uniform plateau dissected into a dendritic network — the cheapest genuinely realistic landscape there is |

Constant uplift plus stream power is worth proposing every single time someone reaches for a
twelve-node stack to get valleys.

**A spline feeding `U` is a cause seed, and it is the only legitimate way to draw a range.** The
crest, the spurs, the valley network and the flank gradients are all *produced* by the erosion that
follows. The same curve extruded straight into height is a smooth wall with none of them, and no
amount of noise on top repairs it. Give the curve uplift amplitude rather than crest elevation:
the height is an outcome, and authoring it directly is what makes the range look moulded.

**Parameter sanity.** Uplift in active orogens is of order 0.1–10 mm/yr; over 10⁶ years that is
100–10 000 m, the right order for a range. If `U × time` misses that window, erosion never reaches
equilibrium and you get a flat plain (too little) or an unerodible plateau (too much). These are
order-of-magnitude figures for calibration, not constants read out of a paper.

## When you do want plates

No canonical source for the *planar* recipe; standard practice is a domain-warped Voronoi
partition with per-boundary classification. It is not folklore, though: every step below has a
published spherical counterpart in [cortial2019] — §3 for plates as spherical Voronoi cells of a
noise-warped geodetic distance, §4.1–4.4 for the per-boundary branches, and §4.2 for spreading
boundary uplift inland over a radius of influence. The planar version is a restatement:

1. Seed 8–20 plate centres with Poisson-disk or relaxed random placement — pure random gives
   implausibly uneven plates.
2. Assign cells to the nearest centre, with the distance metric perturbed by low-frequency noise:
   `d = |cell - centre| + warpAmp·fbm(cell·warpFreq)`.
3. Give each plate a velocity, a type (oceanic/continental) and a base elevation.
4. At each boundary cell take `conv = dot(v_a - v_b, n)` and branch: continental–continental
   collision and oceanic subduction give uplift proportional to convergence (plus a trench on the
   oceanic side); two oceanic plates give a narrow arc; divergence gives a rift; shear dominance
   gives lateral offset with little uplift.
5. **Diffuse the boundary uplift inland** over the orogen width — real orogens are 100–300 km
   wide, not one cell. That range is an order-of-magnitude calibration figure of the same kind as
   the uplift rates above, not a constant read out of a cited source.
6. Optionally iterate: move the centres, re-partition, accumulate. Three to eight iterations give
   old inactive ranges beside young active ones, which reads far better than one snapshot.

Two tells identify a bad plate node at a glance: **straight Voronoi edges** (step 2 skipped) and a
**razor ridge sitting exactly on the boundary** (step 5 skipped).

On a sphere the kinematics are different in kind, not degree: a plate moves as a rigid rotation
about an Euler pole rather than translating, so transform faults trace small circles and spreading
rate scales with angular distance from the pole. [cortial2019] is the graphics realisation — take
it whole rather than bending a planar model onto a globe.

## Faults belong in K, not in h

A fault is a line of **weakened rock**. Implement it as a local reduction in erodibility `K(x,y)`
and let erosion exploit it; you get valleys that follow structure, which is what faulted terrain
actually looks like. Displacing height directly gives a step that erosion has no reason to
respect, and the next pass relaxes it. The same argument governs strata: layered `K` produces
caprock, cuestas and mesas as *outputs*, where a terrace node quantises height and produces
contour lines on a model.

**What it beats.** *A full plate-tectonic simulation* — geodynamics at game scale costs orders of
magnitude more and changes `U` by less than the erosion run does. *Fault-formation fractals*
(random line + offset, iterated) — no canonical source; a fractal with no drainage, useful only as
structural anisotropy fed into `K`. *Extruding a ridgeline curve into height* — the fastest route
to a range that has no valleys. *Thresholded noise for coastlines* — a coastline is an erosion
output; set sea level after the erosion run and the estuaries land where the drainage says.

## Isostasy: the range rises as it wears down

Uplift adds load; erosion strips it; the crust floats. Leave isostasy out and a range only ever
erodes downward. Put it in and **summits rise while mean elevation falls** — the real long-term
behaviour, and it reshapes the whole profile [molnar1990].

**Fix the two densities once and derive everything from them.** Take `ρc = 2800`, `ρm = 3300`
kg/m³ — the usual pair, chosen here as calibration rather than quoted from a table. Then:

- erosion removes mean load, so the range rebounds by `ρc/ρm ≈ 0.85` of the mean thickness
  stripped, and measured peak uplift is not by itself evidence of tectonic uplift;
- **Airy** is one multiply per cell — a *surface* standing at elevation `h` presses a root
  `r = ρc·h/(ρm − ρc) = 2800/500 = 5.6·h` into the mantle, so the rock column that carries it is
  `t_load = h + r = 6.6·h`, of which `h` shows above the datum.

Both numbers move together with the pair: at `ρc/ρm = 0.8` the rebound is 0.8 and the root is
`4.0·h`, not 5–6. Quoting a rebound from one pair and a root from another, as this document once
did, is exactly the inconsistency the rest of it insists on catching.

**Two symbols, kept apart.** In the Airy line `h` is the *surface elevation after compensation*,
and the surface stays at `h`. The flexure block below takes the *load column* `t_load` — the
un-deflected rock thickness, root included — and returns the surface that column produces. They
are not the same quantity, and the block is written so that the two never share a name.

Airy is wrong at short wavelengths, because the plate has strength — the standard geodynamics
text [turcotte2014] carries both it and the thin-plate equation below (a textbook, not a paper;
there is no canonical paper for either, and standard practice is to take the textbook derivation
whole).

**Flexural** is the one to implement, and over a heightfield the practical solve is spectral,
because `∇⁴` is a multiply in Fourier space. **The deflection is a state variable.** Carry
`w_prev`, the deflection already applied to `h` — zeros on the first call when `h` starts as
un-deflected rock (a flat plain that `U` will build up); an authored surface that is meant to
already stand at `h` starts with `w_prev = IFFT2(T/(1 − T) · FFT2(h))`, its own flexural root, so
the first call changes nothing — and on every call rebuild the load from the *un-deflected* rock
column, then apply only the change in deflection:

```
t_load = h + w_prev                          # the UN-deflected rock column, not the surface
q = ρc · g · t_load ;  Q = FFT2(q)
k = sqrt(kx² + ky²)                          # RADIAL wavenumber, in rad/m — see the ⚠️ below
W = Q / (D · k⁴ + (ρm − ρinfill) · g)        # the plate transfer function T(k), applied to Q
w_new = IFFT2(W)                             # subside under loads, rebound at deficits
h = h − (w_new − w_prev) ;  w_prev = w_new   # apply the INCREMENT; the state carries the rest
```

Written with `T(k) = ρc·g / (D·k⁴ + Δρ·g)`, `Δρ = ρm − ρinfill`, the first call gives `w = T·h₀` and `h = (1 − T)·h₀`;
the second rebuilds `t_load = h + w = h₀`, gets the same `w`, and changes nothing — the block is
idempotent, which is what a periodic update inside a long loop has to be. The naive form —
`q = ρc·g·h` from the current, already-deflected surface, written back over `h` — is not, because
each call multiplies the long-wavelength surface by another `1 − ρc/Δρ = 0.15`, so it converges to
zero: on a 3000 m Gaussian bump (`σ = 60 km`, `Te = 20 km`) one call leaves a 1163 m peak, ten
leave 76 m, and the domain-mean component is down to `0.15¹⁰ ≈ 6×10⁻⁹` after those ten — a long
run leaves nothing. Nor is the half-fix of
computing `w_new` from the deflected `h` and subtracting only the increment: that converges to
`h₀/(1 + T)`, `0.54·h₀` at long wavelength against the correct `0.15·h₀`, and a gate of *"the
ridge survives"* passes it. The gate that catches both is numeric: ten calls must agree with one
to `< 1e-9 m`. The block above does, to fp64 roundoff (`~10⁻¹³ m` on a 512² grid; `~10⁻⁴ m` in
fp32, still idempotent to the metre).

`Te`, the effective elastic thickness inside `D`, is the one knob that matters: a few km for weak
hot lithosphere, tens of km for old cold lithosphere. The response width is
`α = [4D / ((ρm − ρinfill)·g)]^¼`, and since `D ∝ Te³` it grows as **`Te^(3/4)`** — thickening
the plate *widens* the response (`E = 70 GPa`, `ν = 0.25`, chosen as calibration like the
densities above, `ρm − ρinfill = 3300 kg/m³`):

| `Te` (km) | 5 | 10 | 20 | 40 | 80 |
|---|---|---|---|---|---|
| `α` (km) | 17.6 | 29.6 | 49.8 | 83.8 | 140.9 |

⚠️ **Build `k` with `fftfreq`, not a `linspace` ramp, and make it radial.** This is where the
solve is most often quietly wrong. `fftfreq` returns the signed, Nyquist-wrapped frequencies in
the FFT's own mode order; the angular wavenumber is `2π` times that, in rad/m, so `Δx` must be in
metres. `k` is the **radial magnitude** `sqrt(kx² + ky²)`, so `k⁴ = (kx² + ky²)²`; the plausible
slip `kx⁴ + ky⁴` is a different, anisotropic operator and gives a four-lobed flexural moat where
the correct response is circular — on the `σ = 60 km` bump above nearly twice as deep on the
diagonals as on the axes, subtler for narrower loads (1.1× at `σ = 20 km`) but never round. No `k = 0`
guard is needed — the denominator there is finite, `(ρm − ρinfill)·g`, and the domain-mean load
subsides uniformly by `T(0) = ρc/(ρm − ρinfill) = 0.85` of its column, leaving the surface at
`0.15·t_load`. **That reproduces Airy only when `t_load` is the whole column:** with `ρinfill = 0`,
`0.1515 × 6.6·h = 1.0000·h`, the surface the Airy line says stands at `h`. Feed the block a
surface elevation `h` in place of the column and its `k = 0` limit puts the surface at `0.15·h` —
the same mistake that made the old form of the block eat the range. The domain must exceed a few
`α`, often hundreds of km, or the flexural response wraps around it.

**Time budget.** All of this is authoring-time. `U` is built once; the flexure solve is two FFTs,
which is nothing next to the erosion run it feeds, and it belongs *inside* the erosion loop as a
periodic update, not as a post-process — which is exactly why the block has to be idempotent, and
why `w_prev` is state the loop owns rather than a temporary. Nothing in this document runs per
frame — a runtime that needs tectonics needs a baked `U` and a baked heightfield.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Mountains with no valley network | `U` fed to a short droplet run, or to nothing at all | `U` only means anything as the uplift term of a long erosion solve |
| A razor ridge exactly along a plate boundary | Boundary uplift never diffused inland | Blur over the orogen width, 100–300 km |
| Straight-edged, obviously Voronoi plates | Unperturbed distance metric | Warp the metric with low-frequency noise |
| A flat plain after a long erosion run | `U × time` far below the 100–10 000 m window | Re-derive the uplift rate against the run length |
| An unerodible plateau | `U × time` far above it, or `K` too low | Same calculation, other direction |
| A smooth wall where a range was drawn | The curve was extruded into height instead of into `U` | Feed the curve to uplift and let erosion cut it |
| A fault step that vanishes after the next erosion pass | The fault was written into height | Write it into `K` instead |
| Peaks sink as valleys incise, through a long run | No isostatic rebound | Couple erosional unloading, `ρc/ρm ≈ 0.85` of mean stripped thickness [molnar1990] |
| Flexural deflection wraps or ripples across the domain | `k` built from a `linspace` ramp, or a domain smaller than a few `α` | `fftfreq` in rad/m; enlarge the domain or **lower** `Te` — `α ∝ Te^(3/4)`, so raising it widens the response and shrinks `domain/α` (512 km is 10.3 `α` at `Te = 20 km`, 3.6 at 80) |
| The range loses most of its height over a run with no erosion | Flexure re-loaded from the already-deflected surface each periodic call, `0.15` per call at long wavelength | Carry `w_prev`; load from `h + w_prev`; apply only `w_new − w_prev` — ten calls must equal one to `< 1e-9 m` |
| A four-lobed star in the flexural moat around an isolated load | `k⁴` built as `kx⁴ + ky⁴` | `k = sqrt(kx² + ky²)`, then `k⁴` |
| Rivers meet the sea at arbitrary points, with no estuaries | Coastline authored by thresholding noise before erosion | Set sea level after erosion |
