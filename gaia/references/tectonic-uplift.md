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
- **Airy** is one multiply per cell — a load of height `h` presses a root
  `r = ρc·h/(ρm − ρc) = 2800/500 = 5.6·h`.

Both numbers move together with the pair: at `ρc/ρm = 0.8` the rebound is 0.8 and the root is
`4.0·h`, not 5–6. Quoting a rebound from one pair and a root from another, as this document once
did, is exactly the inconsistency the rest of it insists on catching.

Airy is wrong at short wavelengths, because the plate has strength — the standard geodynamics
text [turcotte2014] carries both it and the thin-plate equation below (a textbook, not a paper;
there is no canonical paper for either, and standard practice is to take the textbook derivation
whole).

**Flexural** is the one to implement, and over a heightfield the practical solve is spectral,
because `∇⁴` is a multiply in Fourier space:

```
q = ρc · g · h ;  Q = FFT2(q)
W = Q / (D · k⁴ + (ρm − ρinfill) · g)        # the plate transfer function
w = IFFT2(W) ;  h_isostatic = h − w          # subside under loads, rebound at deficits
```

`Te`, the effective elastic thickness inside `D`, is the one knob that matters: a few km for weak
hot lithosphere, tens of km for old cold lithosphere. The response width is
`α = [4D / ((ρm − ρinfill)·g)]^¼`.

⚠️ **Build `k` with `fftfreq`, not a `linspace` ramp.** This is where the solve is most often
quietly wrong. `fftfreq` returns the signed, Nyquist-wrapped frequencies in the FFT's own mode
order; the angular wavenumber is `2π` times that, in rad/m, so `Δx` must be in metres. No `k = 0`
guard is needed — the denominator there is finite and the domain-mean load subsides uniformly,
which is the Airy limit falling out for free. The domain must exceed a few `α`, often hundreds of
km, or the flexural response wraps around it.

**Time budget.** All of this is authoring-time. `U` is built once; the flexure solve is two FFTs,
which is nothing next to the erosion run it feeds, and it belongs *inside* the erosion loop as a
periodic update, not as a post-process. Nothing in this document runs per frame — a runtime that
needs tectonics needs a baked `U` and a baked heightfield.

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
| Flexural deflection wraps or ripples across the domain | `k` built from a `linspace` ramp, or a domain smaller than a few `α` | `fftfreq` in rad/m; enlarge the domain or raise `Te` |
| Rivers meet the sea at arbitrary points, with no estuaries | Coastline authored by thresholding noise before erosion | Set sea level after erosion |
