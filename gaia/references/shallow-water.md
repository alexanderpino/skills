---
type: Technique
title: Shallow water — the solver for bounded, interactive bodies
description: "The virtual-pipe discretisation of the shallow-water equations: why it is the default for a pool, a flood or a ripple patch, and the six places it stops being the right model."
tags: [simulation, water, shallow-water, solver, runtime, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: mei2007, tier: P, locator: "§3.2 eq. (2) the flux update with pipe cross-section A and pipe length l as constants, eq. (4) the outflow scaling factor K, and the §3.2.2 CFL statement Δt·u ≤ lX" }
  - { id: obrien1995, tier: P, locator: "the height-column fluid coupled to its neighbours by virtual pipes on the head difference" }
  - { id: stava2008, tier: P, locator: "§4 eq. (1), the pipe cross-section fixed at C = l² and the outflow scale-down written as a guarded branch rather than a min; §5 the sediment-slippage and material-layer extensions" }
  - { id: kass1990, tier: P, locator: "the linearised shallow-water heightfield and its implicit integration" }
  - { id: courant1928, tier: P, locator: "the hyperbolic case — the domain-of-dependence requirement on the difference scheme" }
  - { id: steadystate_discharge, tier: F, locator: "the steady-state identity Q = runoff times upstream contributing area" }
  - { id: fluid_authority, tier: F, locator: "the cosmetic-versus-gameplay liquid state contract" }
---
# Shallow water — the solver for bounded, interactive bodies

When water must *respond* — fill, drain, slosh, flood, ripple around the player, break against a
wall you moved — a wave field cannot do it, because a wave field has no state. This is the solver
for that case, and only for that case: **bounded, interactive water**. An open sea is a spectrum,
not a simulation.

## Use this

**The virtual-pipe discretisation of the shallow-water equations** [mei2007], explicit, with the
outflow clamp. It is the default at both time budgets — the same machinery drives a generator's
hydraulic erosion offline and an engine's interactive patch per frame — and that is unusual enough
to be worth stating.

The depth-averaged equations, valid when horizontal scale greatly exceeds depth (true of nearly all
terrain water):

```
d h / d t + div(h * u)                 = 0        # mass;     h = column height, u = mean velocity
d u / d t + (u . grad) u + g grad(h+b) = 0        # momentum; b = bed elevation
```

⚠️ **The pipe form does not discretise the second equation as written — it drops `(u.grad)u`.**
Each pipe is accelerated by the head difference alone, there is no momentum advection anywhere in
the loop, and velocity is not a state variable at all but a quantity *reconstructed* from the
fluxes afterwards. What the pipe model actually solves is the **linearised long-wave** system: mass
conservation exactly, momentum only in its gravity-driven part. Limit 6 below is that sentence's
consequence, and it is the one most often discovered late.

With that stated, the pipe form [obrien1995] is flux between neighbouring columns through virtual
pipes, driven by the **hydraulic head** difference `H = b + h`:

Symbols: `h` depth, `b` bed, `H = b + h` head, `f_i` the outflow flux through pipe `i` of the
four, `cellArea = lx·ly`. The two that are usually left undefined and are not free: **`A` is
the virtual pipe's cross-sectional area and `l` its length, both constant parameters**
[mei2007] — Šťava fixes `A = l²` with `l` the grid spacing [stava2008]. Together they set the
scheme's signal speed, which is why they reappear under **The stability limit**.

```
per step, per cell:
  h  += source * dt                                  # rain, springs, snowmelt, a hose
  H   = b + h
  f_i = max(0, f_i + dt * (A*g/l) * (H - H_neighbour_i))     # accelerate each of 4 fluxes by head
  Σf  = sum(f_i)
  K   = (Σf > 0) ? min(1, h * cellArea / (dt * Σf)) : 1      # <-- the clamp; see below
  f_i *= K
  h  += dt * (inflow - outflow) / cellArea
```

Four properties make this the recommendation, in order of how much they matter.

**1. The outflow scaling factor `K` makes positivity unconditional** [mei2007]. A cell may never
output more water than it holds, so depth cannot go negative regardless of `dt`. A pipe model
written without this clamp produces negative depths and then NaNs, and it is the single most common
port error. Verified rather than asserted: with the guard below, a 64² grid over a rough bed runs
400 steps at every `dt` from `C = 0.2` to `C = 20` with no NaN, `min depth = -0.000000`, and mass
drift ≤ 1.1e-16. Unconditional means unconditional.

⚠️ **But `min(1, h·cellArea/(dt·Σf))` as printed in [mei2007] eq. (4) is itself a `0/0`.** On a
dry cell — no water, no flux — the argument is `0.0/0.0`. It survives a scalar CPU prototype by
accident: Python's `min(1, NaN)` returns `1` because it keeps the first argument when `NaN < 1`
is false, while `min(NaN, 1)` returns `NaN`, `np.minimum` propagates either way, and GLSL and
HLSL leave `min` on NaN undefined — so the prototype is clean and the shader is not, which for a
"GPU-native by design" recommendation is the worst possible place to hide. Measured on an 8×8
grid dry but for one wet cell: `K` NaN in 63 of 64 cells at step 0, and the whole depth field NaN
after one step. Guard the denominator, as the branch in the block does; that is also Šťava's own
form, which scales down only *if* outflow volume exceeds the water in the column [stava2008].

⚠️ **Positivity is not stability.** Above the CFL limit you get checkerboard sloshing
that never damps, with no NaN to tell you — see below.

**2. It is heightfield-native.** State is one depth per cell over the bed the terrain already
exports. It collides trivially, GPUs trivially, tiles, and shares its representation with the
terrain — which is why the generator and the engine can hold the same mental model and the same
debug view.

**3. Discharge is a real quantity.** `Q = sum(outflow)` is volumetric flow in m³/s, and at steady
state under uniform rain it accumulates downstream as roughly `rain × upstream drainage area`
[steadystate_discharge]. That gives you a free correctness test and a free shortcut.

**4. It extends without changing shape.** Sediment transport, slippage and material layers are the
same loop with extra fields [stava2008] — Mei and Št'ava are one family, not two, and the frequent
claim that one is a particle method is wrong about both.

**The stability limit** is the CFL condition on the *fastest signal in the system* [courant1928] —
and the system is not the same for both formulations here, so read which of the two bounds below
is yours. The characteristic speeds of the shallow-water *equations* are `u ± sqrt(g*h)`, so for
any scheme that discretises them faithfully — the shock-capturing solver in the crossover section,
and the pipe form only under the pipe geometry named further down — **both terms are in the
bound**:

```
dt <= C * dx / (max|u| + sqrt(g * h_max))      # C ~ 0.2 in shipped code, not 1.0
```

⚠️ **In that bound, the gravity term alone is not the stability limit.** `dt <= C*dx/sqrt(g*h_max)`
is the form that circulates, and it is only adequate in the subcritical case `|u| << sqrt(g*h)` — a
settled pool. Every case this document is aimed at is the other one. At 1 mm depth `sqrt(g*h)` is
**0.099 m/s** while a flood front, a dam break or a sheet running over terrain moves at metres per
second, so the gravity-only bound is an order of magnitude too large — in the direction that
explodes. The Froude number `Fr = |u| / sqrt(g*h)` is the diagnostic: at `Fr ≳ 1` the advective
half *dominates* the limit and the gravity-only version is simply wrong.

⚠️ **The pipe form's own signal speed is `sqrt(g·A/l)`, and with `A` and `l` constant it does not
move with depth at all.** Linearise the block above — flux accelerated by `A·g/l` times the head
difference, depth updated by flux divergence over `lx·ly` — and the wave speed that falls out is
`dx·sqrt(A·g/(l·lx·ly))`, i.e. `sqrt(g·A/l)` on a square grid. That is `sqrt(g·h)` **only if the
pipe area is tied to depth**, `A ≈ h·lx`. `A/l` is the model's *effective depth*: with Šťava's
`A = l²` [stava2008] the grid sloshes at the speed of water one cell deep, whatever the water is.

Measured, clamp disabled so instability is visible, critical `dt` bisected on a 32² grid:

| Pipe area | depth 0.1 | depth 1.0 | depth 10 |
|---|---|---|---|
| `A = 1`, constant (as published) | 0.1604 | 0.1604 | 0.1604 |
| `A = h·lx`, tied to depth | 0.5056 | 0.1599 | 0.0506 |

The constant-`A` row is flat, and `dt_crit / (dx/sqrt(g·A/l))` held at 0.502 across `A ∈ {1,4}`,
`l ∈ {1,4}`, `dx ∈ {1,2}` and depths two decades apart. The tied-`A` row is the `1/sqrt(h)` of
`sqrt(g·h)`, to three digits. So:

- **Full nonlinear shallow water, and the pipe form with `A ≈ h·lx`**: the bound above, both
  terms, recomputed every step. Celerity rises with depth, so **a filling pool gets progressively
  more expensive**; velocity rises as a front steepens, so **a dam break gets more expensive as it
  runs**. Do not compute it once at initialisation.
- **The pipe form as published, `A` constant**: the gravity half is *fixed* at `sqrt(g·A/l)`.
  A per-step `max(sqrt(g·h))` reduction over that grid measures nothing; `A/l` is what you are
  choosing when you choose `dt`, and it is chosen once. What remains per-step is Mei's own stated
  condition, `Δt·|u| ≤ lX` and `Δt·|v| ≤ lY` [mei2007] — the domain-of-dependence requirement that
  a cell reads only its four neighbours, which `hydraulic-erosion.md` prints as
  `Δt·|v| < cellSize`. That is one bound stated in two documents; the depth-dependent celerity is
  not.

⚠️ **Under constant `A`, `|u|` is not in the linear stability bound either** — no term of the
update contains `u` at all; it is reconstructed after the fact. Measured, `dt_crit` moved 0.1604 →
0.1601 as background transport went from 0 to 50 m/s. `|u|` binds *transport* — mass and sediment
skipping cells per step — not the growth rate. It is the shock-capturing solver, which carries
`(u.grad)u` for real, whose *stability* the `max|u|` half governs.

## Where it stops being the right model

Six limits. The first three are structural — no resolution, tuning or budget reaches them.

**1. The surface cannot overturn.** One height per column means breaking waves, splashes, droplets,
pouring, and anything that separates from the bulk are *unrepresentable* — not expensive,
impossible. If that must happen where the camera lives, you need particles, and no heightfield
tuning substitutes.

**2. One surface per column.** No water under a bridge *and* in a cave below it. This is an
architectural constraint on the level, not a shader problem.

**3. No dispersion.** The shallow-water equations are the long-wave limit: every wavelength travels
at `sqrt(g*h)`. There are no groups, no swell, and no deep-water motion. **Do not build an ocean
with it.** Conversely this is exactly why it is cheap and stable — one speed, one limit.

**4. No yield stress.** Mud, wet snow, lava and sand hold a shape on a slope and stop at a finite
thickness; water does not, and the equations above have no term for it. That family needs a
different constitutive model.

**5. The domain does not stream.** Fluid has no LOD. The patch is an explicit budget decision:
follow the camera, nest resolutions rather than growing one grid, and sleep bodies nobody is
looking at. Note the boundary contract flips with the body type — an open-water patch fades its
contribution to zero over the outer ~15% so the edge is never visible; a pool's edge is a real wall
and must reflect.

**6. No momentum advection, so no shocks and no hydraulic jump.** The update drops `(u.grad)u`, so
the model cannot steepen a front into a discontinuity, cannot form a hydraulic jump where
supercritical flow meets subcritical, and **carries no momentum around a bend** — water rounding a
corner does not run up the outside wall, because there is no inertia in the loop to carry it there.
A dam break, named in this document's opening line as a target case, is exactly where this shows:
you get a spreading, diffuse fill, not a bore with a front. Unlike the first three this one is not
structural — it is a *different solver*, not a resolution problem, and the crossover is next.

## When a propagating front is the shot, change solver

If the front *itself* is what the camera is on — a dam break, a bore running down a channel, a
hydraulic jump at the foot of a spillway — the pipe model is the wrong family and no amount of
resolution reaches it, because the missing term is in the equations, not in the grid. Use **full
nonlinear shallow water with a shock-capturing (Riemann/Godunov-type) flux**: it keeps the
advective term, resolves discontinuities as discontinuities, and puts front speeds and jump
locations in the right place.

Budget its costs rather than discovering them: a per-cell wave-speed estimate feeding the flux, an
explicit **wetting/drying** treatment (a naive Riemann solver produces negative depths at a wet–dry
front — the same failure the pipe model's clamp `K` exists to prevent, now yours to solve), and a
smaller `dt` under the same `max|u| + sqrt(g*h)` bound, with a `max|u|` that is now genuinely
large.

**Everything else keeps the pipe model.** Where the front is scenery rather than the shot —
flooding a basement, filling a pool, rain finding a channel — the diffuse fill does not read as an
error, and unconditional positivity plus a fixed per-cell cost are worth more than shock fidelity.

## Authority: which half of the water is real

⚠️ **This section is doctrine, not physics.** `fluid_authority` has **no external source**: it is
a convention this repository recommends, carried from terrain-renderer's `19-fluid-simulation.md`.
It is an engineering preference about ownership, replication and persistence, not a fact about
water, and it is written as a rule only because a project that leaves it implicit discovers it at
the worst possible moment.

With that said: a simulated body should be **exactly one of two things, with no middle**
[fluid_authority]:

- **Cosmetic GPU state** — ripples, splash response, wakes, puddle response. GPU-only,
  camera-local, non-authoritative. Physics, navigation and the server ignore it; it may be dropped
  on a low tier or off-screen.
- **Gameplay liquid state** — a flood that rises and drowns, a dam the player breaks, a channel
  diverted, water that persists in a save. CPU- or server-owned, versioned, replicated, persisted;
  the GPU renders its authoritative result.

There is **no automatic promotion** from the first to the second, and no GPU readback that makes
cosmetic water authoritative. "Can the player flood the basement?" is an architecture question
asked at design time, with a budget and a replication story — not a shader question. Water that
changes the navigable world also invalidates collision and navmesh.

**What it beats.** (*Full nonlinear shallow water with a shock-capturing solver* is deliberately
**not** in this list — it is the crossover above, not a dismissal.) *An implicit heightfield solve*
[kass1990] — unconditionally stable, and each step is a global solve, so it buys a bigger `dt` you
do not need in a frame.
*A wave-equation or convolution ripple patch* — cheapest of all, and it carries no mass: it cannot
flood, drain, or make a river. *Particles (SPH, position-based)* — necessary exactly when the
surface must overturn, and they make the free surface your problem to reconstruct. *Hybrid
grid-particle (FLIP/APIC)* — the quality tier for a bounded sloshing volume; viable for a room, not
an open world. *The steady-state shortcut* [steadystate_discharge] — if you want the converged
discharge rather than the transient, take `rain × contributing area` from flow accumulation and run
no solver at all.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Depth goes negative, then NaN | The outflow scaling factor is missing | Clamp outflow to the water held [mei2007] |
| Every cell is NaN after one step, and the dry parts went first | The clamp itself: `min(1, h·cellArea/(dt·Σf))` is `0/0` where there is no water and no flux | Scale only when `Σf > 0`; the guarded branch form [stava2008] |
| Clean in the Python prototype, NaN in the shader | Scalar `min(1, NaN)` returns 1; `np.minimum` propagates, and GLSL/HLSL leave it undefined | Same guard — never let `min` be the NaN handler |
| Checkerboard sloshing that never damps, no NaN | `dt` above the CFL limit while the clamp holds positivity | Positivity is not stability — lower `dt` [courant1928] |
| Stable until the pool fills, then explodes | `sqrt(g*h)` grew with depth; `dt` computed once. Only in a scheme whose celerity tracks depth: full SWE, or a pipe model with `A ≈ h·lx` | Recompute the limit each step from the current state |
| Reducing `dt` by the deepest cell each step changes nothing, and it still explodes | Constant-`A` pipe model: its signal speed is `sqrt(g·A/l)`, fixed by parameters, not by depth | Bound on `sqrt(g·A/l)`; lower `A/l` or `dt`, and stop measuring depth |
| Stable while still, explodes as soon as anything moves fast | Advective speed left out of the CFL bound — in a solver that carries `(u.grad)u`; the constant-`A` pipe form has no `u` in its update to destabilise | Bound on `max\|u\| + sqrt(g*h)`, never on `sqrt(g*h)` alone [courant1928] |
| A thin supercritical sheet explodes at a "correct" gravity-wave `dt` | Advective solver again: at `Fr ≳ 1` the advective half dominates; at 1 mm depth `sqrt(g*h)` is 0.099 m/s and `\|u\|` is metres per second | Recompute both halves every step from the current state |
| Water piles up along the domain border | Closed boundary where an open one was meant | Ghost cells at a very low elevation drain the edge |
| A basin never fills | Open boundary where a wall was meant | Reflect at real walls; fade only where a patch ends inside a larger body |
| Water flows uphill or sits on a slope | Flux driven by bed slope instead of hydraulic head | Drive it by `b + h`, not `b` |
| Explodes when the rain or inflow slider moves | Injection unclamped; `dt_stable` predates it | Clamp per-step injection to a fraction of the local depth |
| Rivers one cell wide and shimmering | Channel narrower than a cell | Carry *discharge* as the physical truth and derive a channel from it |
| The sea built on this has no swell or groups | Shallow-water has no dispersion, by construction | Use a spectral or trochoidal field for open water |
| Splashes never form no matter the resolution | A heightfield cannot represent an overturning surface | Layer particles for the splash; keep the heightfield for the bulk |
| A dam break spreads as a diffuse fill with no front; no hydraulic jump ever forms | The pipe form drops `(u.grad)u`, so nothing steepens a front | Shock-capturing shallow water if the front is the shot; otherwise accept it and stop tuning |
| Water rounds a bend without running up the outside wall | Same cause — no momentum is carried through the turn | Same crossover; a heightfield with no inertia term cannot bank |
| Flood drowns the player but not the AI | Cosmetic water treated as gameplay state on one side | Declare authority; collision and navmesh follow the authoritative field [fluid_authority] |
| Different results on a different machine or frame rate | Step count tied to frames | Fixed step, accumulate the remainder |
