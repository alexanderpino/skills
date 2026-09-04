---
type: Technique
title: Simulation time budget — minutes offline, milliseconds in a frame
description: "One solver, two schedulers: how the time budget decides the timestep, the substep policy, and what happens when the budget runs out."
tags: [simulation, water, time-budget, stability, authoring-time, runtime]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: courant1928, tier: P, locator: "Kap. II 'Der hyperbolische Fall', §2 'Ueber den Einfluss der Wahl des Gitters. Die Abhaengigkeitsgebiete bei Differenzen- und Differentialgleichung', pp. 61-62 with Fig. 7 — with time mesh h and space mesh kappa*h, the difference scheme converges only for kappa greater than 1" }
  - { id: kass1990, tier: P, locator: "sections are unnamed by number: 'Integration', eq. 9-16, the first-order implicit step and its symmetric tridiagonal system; 'Three Dimensions', eq. 18-20, the alternating-direction split that keeps each sub-iteration tridiagonal" }
  - { id: stam1999, tier: P, locator: "§2.2 'Method of Solution' — the advection step by the method of characteristics and its unconditional-stability claim, with the derivation in Appendix A, and the diffusion and projection steps that follow it as sparse global solves; the numerical-dissipation admission is in §1" }
  - { id: mei2007, tier: P, locator: "§3.2.1 'Outflow Flux Computation', eq. 4 defines K = min of 1 and d1*lX*lY over the summed outflow times dt, and eq. 5 applies it to all four fluxes" }
  - { id: braun2013, tier: P, locator: "the implicit stream-power update over the receiver-tree stack ordering. NOT OPENED — Geomorphology is paywalled at Elsevier and no open copy was reachable from here, so nothing inside it is named; the scheme is read instead in cordonnier2016 §5 eq. 2, which restates it" }
  - { id: fiedler_timestep, tier: F, locator: "§'Free the physics' — the accumulator loop that consumes produced time in fixed dt steps; the leftover-remainder interpolation is the section after it, §'The final touch'. The post numbers no sections" }
  - { id: explicit_diffusion_limit, tier: F, locator: "no artefact: the explicit FTCS bound, dt <= dx^2 / (4D) in two dimensions. Von Neumann analysis, standard and unpublished as such" }
---
# Simulation time budget — minutes offline, milliseconds in a frame

This is the axis every other simulation document in Gaia hangs off, because it is the question the
source material does not ask. An authoring tool assumes it has minutes and an artist willing to
wait. An engine assumes it has a slice of 16 ms and a player who is not. **The physics is the same
and the right answer is not**, and a team building a Gaea-shaped tool with a real-time viewport is
standing exactly on that boundary.

The running example is water, because water is where the boundary is most visible: a wave field
evaluated every frame and a hydraulic-erosion pass baked once are the *same* fluid, and almost
nothing about how you run them is shared.

## Use this

**Before choosing a solver, ask whether you need a solver at all** — see
[the cheapest step](#the-cheapest-stable-step-is-the-one-you-do-not-take). An ambient ocean has no
timestep and no state; that is why it fits in a frame and a pipe model does not.

When you do need one: **write the explicit, CFL-limited step once, and change the scheduler around
it, not the solver.** The step is identical at both budgets — compute a stable `dt` from the
current state, advance, repeat. One policy differs: *how many substeps you are allowed, and what
you do when you run out.*

- **Authoring-time**: substeps are unbounded and adaptive. Cover the whole physical interval the
  artist asked for, however many steps that takes. The artist waits; that is the deal.
- **Runtime**: substeps are capped, and the cap binding is a **designed state**, not a bug. When it
  binds, simulated time falls behind wall-clock time — the sim runs in slow motion — and `dt` never
  moves.

Reach for an implicit or unconditionally-stable scheme only when the *physical time you must cover
per call* is enormous compared to the stable step. That is the authoring-time case and almost never
the runtime case. The reasoning is below, and it is not "implicit is slower".

## The two stability limits, and which one you are under

**Advective / hyperbolic** — water moving, a gravity wave propagating, anything with a signal speed
`c`. The step is bounded by the requirement that the numerical domain of dependence contain the
physical one [courant1928]:

```
dt <= C * dx / c            # C is the Courant number; C <= 1 for the plain explicit scheme
c   = sqrt(g * h)           # shallow water: the long-wave celerity, h the water depth
```

Read what that says about a water patch. Celerity rises with **depth**, so a deep pool costs a
smaller step than a puddle at the same resolution, and a flood that deepens as it fills gets
*progressively* more expensive. Shipped code does not run at `C = 1`:
`obsolete/terrain-architect/reference-impl/shallow_water.py` uses `C = 0.20`, a 5x margin, because `c` is
estimated from the state at the start of the step and the state moves during it.

**Diffusive / parabolic** — viscous damping, thermal relaxation, hillslope creep, anything of the
form `∂u/∂t = ∇·(D∇u)`. Explicit stepping is bounded far harder [explicit_diffusion_limit]:

```
dt <= dx^2 / (4 D)          # two dimensions, isotropic D. In one dimension it is dx^2 / (2 D)
```

Two things follow and both bite. The `dx^2` means **halving the cell size quarters the timestep**,
so resolution is four times as expensive as it looks. And `D` is usually state-dependent, so the
substep count is not a constant you can budget at load time — it is a reduction you run every step.

⚠️ **The one-dimensional bound is the one people quote, and in two dimensions it is unstable by a
factor of two.** If a reference gives you `dx^2/(2D)` for a 2-D grid, it has handed you the 1-D
result; the correct factor is 4, and shipped solvers usually sit at 0.2 for margin.

## The decision rule

Compute one number:

```
N = physical_time_you_must_cover_per_call / dt_stable
```

| `N` | Do this |
|---|---|
| `N <= 1` | Explicit, one step. You are not near a limit; stop reading. |
| `N` small (2–8) and bounded | Explicit with adaptive substepping. This is the answer for nearly all runtime water. |
| `N` large, and you are offline | Substep and wait, **or** buy `dt` with an implicit solve if waiting is the bottleneck. Measure before switching — an implicit step is not free. |
| `N` large, and you are in a frame | **You are asking the wrong question.** Reduce the physical time per call, reduce resolution or domain, or move the process to a bake. Do not raise `dt`. |

The last row is the point. At runtime `physical_time_per_call` is 1/60 s and it is *yours to
choose* — nothing physical demands that one rendered frame equal one simulated frame. That free
variable is what offline work does not have.

## Why "unconditionally stable" is not the runtime answer

Unconditional stability buys **a larger `dt`**. It does not buy a cheaper step. At runtime you do
not want a larger `dt` — you already only need 16 ms of physics — so you are paying for something
you cannot spend.

And the payment is usually a **global data dependency**, which is the harder cost:

- [kass1990] integrates heightfield water implicitly with alternating tridiagonal sweeps, and it
  was the right call for offline film water. ⚠️ It is routinely called **unconditionally** stable —
  this repository's own bibliography entry said so until it was corrected, and
  `shallow-water.md` said so for longer — and **the paper does not claim that.** It
  claims implicitness buys a frame-sized step, and it then freezes the wave speed inside a step by
  holding `d` constant, which it says "virtually ensures that the iteration will not diverge". A
  strong practical guarantee, not an unconditional one. What is unarguable is the *shape* of the
  step: a solve across the whole grid, which cannot be tiled, cannot be evaluated for one streamed
  region, and cannot be stopped halfway and shown.
- [stam1999] gets its unconditional stability in the *advection* term by tracing characteristics
  backwards. That is the half everyone quotes; the expensive half is in the same section — "both
  the projection and the viscosity steps involve the solution of a large sparse system of
  equations". **Two** global solves per step, not one. And the method pays in numerical dissipation
  — the reason PIC-family water reads as syrup.
- [braun2013] solves the fluvial-incision equation implicitly in O(n), which is as good as this
  gets, and it still needs a global topological ordering of the drainage tree before it can take a
  step. That ordering is serial, and it is why landscape evolution is a bake and not a frame.

**The test is not "is it stable", it is "does one step touch the whole domain".** A step with a
global dependency is an authoring-time step no matter how stable it is.

**What it beats.** *Implicit heightfield water* [kass1990] — a big `dt` at the price of a global
solve per step; correct offline, pointless in a frame that needs 16 ms of physics. *Semi-Lagrangian
advection* [stam1999] — unconditional in one term, dissipative, and still carrying two
global sparse solves per step. *Implicit
fluvial incision* [braun2013] — the right offline answer, and its stack ordering is the
baked-versus-amortised boundary made concrete. *Position-based / constraint-projected fluids* —
genuinely large steps with no CFL, but the state becomes particles and your height field is no
longer the simulation's representation. *Frame-derived `dt`* — not an alternative, a bug.

## When the user drags a slider

This is the failure the offline literature never has to survive, and it has two distinct shapes.

**1. The slider changes a term in `dt_stable`.** Cell size, gravity, a viscosity, a pool's depth.
If `dt` was computed once at initialisation it is now wrong and the sim detonates on the next step.
**Fix: recompute `dt_stable` from the current state every step.** It is one reduction (`max(c)` or
`max(D)`); on GPU it is the one readback you keep.

**2. The slider changes the state.** Raising an inflow rate, dropping a dam, teleporting a
deformer into the water. A source at rate `r` deposits `r*dt` in one step; if `r` jumps, the head
gradient that step is enormous *even though `dt` was legal*, because `dt_stable` was computed
before the injection existed. **Fix: clamp the injection, not the `dt`.** Cap what any one step may
add to a fraction of what the cell already holds, and recompute `dt_stable` after injection.

[mei2007] does exactly half of this for you and it is worth naming: the outflow scaling factor
clamps a cell's total outflow to the water it holds, so depth cannot go negative regardless of
`dt`. **Nothing in the model does the same for inflow.** Positivity on the outflow side is not
stability, and that asymmetry is where "it was fine until I moved the rain slider" comes from.

**Never derive `dt` from frame time.** Accumulate real time, step a fixed `dt`, keep the remainder
[fiedler_timestep]. A solver whose stability constant is a function of frame rate explodes on the
first hitch — and a hitch is guaranteed, because streaming a texture causes one.

## The crossover

| | Authoring-time / offline | Runtime / per frame |
|---|---|---|
| Water example | hydraulic erosion to steady state; a bathymetry bake; a drainage solve | a wave field; a ripple patch around the player; a filling pool |
| Physical time per call | all of it — hundreds of iterations to convergence | 1/60 s, and you chose that |
| `dt` | as large as the scheme allows | fixed, `<= dt_stable`, never frame-derived |
| Substeps | unbounded, adaptive, one reduction per step | capped at a small integer; the cap binding is a designed state |
| When the budget runs out | the artist waits | sim time falls behind wall clock — slow motion, never a bigger `dt` |
| Stability bought with | substeps, or an implicit solve | the CFL limit plus a per-step injection clamp |
| Must survive | nothing; it is your machine | a slider drag, a teleport, a hitch, a pause, a resize |
| Global solve per step | fine | forbidden — it is the boundary between amortised and baked |
| Determinism | reproducible run to run | reproducible *and* independent of frame rate |

**The middle tier is real and is where tools actually live.** Between "every frame" and "baked
once" is *amortised*: the sim exposes `(state, step(state, budget_ms), progress)` and the runtime
spends a millisecond budget per frame. Budget in milliseconds and adapt the step count — a fixed
iteration count per frame is a frame-time landmine that only fires at high resolution. A
partially-converged erosion is a real intermediate terrain, and showing it evolve is half of what
makes a tool feel interactive.

## The cheapest stable step is the one you do not take

Before choosing a scheme, ask whether you want the *transient* or the *answer*. If it is the
answer, there is usually a closed form with no stability condition at all. In water this is not a
micro-optimisation — it is why real-time water exists:

- **An ambient ocean is not a simulation.** A Gerstner sum or an inverse-FFT of a spectrum is
  evaluated at time `t` from parameters. There is no state, no timestep, no CFL, and no way for it
  to explode. Simulate the sea only where the sea must respond to something.
  ⚠️ **"The same field evaluated on the CPU for physics and the GPU for rendering" is true per
  model, not in general.** A **Gerstner** sum has a genuine per-point evaluator and can be queried
  on any thread. An **FFT cascade cannot be**: the inverse transform yields a whole tile or nothing,
  so a CPU query costs either the entire transform run again CPU-side or a texture **readback** — a
  stall, and physics reading last frame's sea. Budget a cheap CPU proxy fitted to the same spectrum
  instead. And with choppiness on the result is a *displacement* field, not a height field, so "the
  height above `(x, z)`" requires iteratively inverting the horizontal displacement before it means
  anything at all. See `wave-models.md`.
- **Steady-state discharge** under uniform rain is `rain * upstream contributing area` — what a
  mass-conserving water solver converges to, available directly from flow accumulation with no
  time-stepping.
- **A runout integrated in space** rather than time — `d(v^2/2)/ds = a` along the path — has no
  `dt`, no CFL, and no state that can explode. Its cost is the path length.

Ask "do I need to watch it happen?" A generator usually does not. A game usually does, but only for
the tens of metres the player is standing in.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Sim explodes after a frame hitch or a streaming spike | `dt` derived from frame time | Fixed-step accumulator [fiedler_timestep] |
| Fine at 512, explodes at 2048 | The `dx` (advective) or `dx^2` (diffusive) in the bound | Recompute `dt_stable` from the current `dx` |
| Water patch is stable until the pool fills | `c = sqrt(g*h)` grew with depth; `dt` was computed once | Recompute the limit every step from the current state |
| "It was fine until I moved that slider" | A source term changed; `dt_stable` predates the injection | Clamp per-step injection to a fraction of the local state |
| Depth goes negative, then NaN | Outflow exceeded what the cell held | The outflow scaling clamp [mei2007] |
| Checkerboard sloshing that never damps, but no NaN | `dt` above the limit while a positivity clamp holds | Positivity is not stability — lower `dt` |
| Frame time spikes whenever the water is deep | Adaptive substep count unbounded at runtime | Cap the substeps and let sim time lag |
| Slow motion nobody asked for | The substep cap is binding every frame | That is the cap working; shrink resolution or domain, not the cap |
| Result differs between a fast and a slow machine | Step count tied to frames, not accumulated time | Fixed `dt`, accumulate the remainder |
| An offline solver ported to the viewport tanks the frame | Global solve per step [kass1990] [braun2013] | Bake it, or amortise with checkpoints; do not shrink it |
| The ocean is simulated and costs a fortune | A wave field was treated as a sim when it is a closed form | Evaluate the spectrum; simulate only the interactive patch |
