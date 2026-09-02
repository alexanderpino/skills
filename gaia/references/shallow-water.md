---
type: Technique
title: Shallow water — the solver for bounded, interactive bodies
description: "The virtual-pipe discretisation of the shallow-water equations: why it is the default for a pool, a flood or a ripple patch, and the five places it stops being the right model."
tags: [simulation, water, shallow-water, solver, runtime, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: mei2007, tier: P, locator: "the eight-step formulation and the outflow scaling factor K" }
  - { id: obrien1995, tier: P, locator: "the height-column fluid coupled to its neighbours by virtual pipes on the head difference" }
  - { id: stava2008, tier: P, locator: "the sediment-slippage and material-layer extensions to the pipe model" }
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

The pipe form [obrien1995] discretises this as flux between neighbouring columns through virtual
pipes, driven by the **hydraulic head** difference `H = b + h`:

```
per step, per cell:
  h  += source * dt                                  # rain, springs, snowmelt, a hose
  H   = b + h
  f_i = max(0, f_i + dt * (A*g/l) * (H - H_neighbour_i))     # accelerate each of 4 fluxes by head
  K   = min(1, h * cellArea / (dt * sum(f_i)))               # <-- the clamp; see below
  f_i *= K
  h  += dt * (inflow - outflow) / cellArea
```

Four properties make this the recommendation, in order of how much they matter.

**1. The outflow scaling factor `K` makes positivity unconditional** [mei2007]. A cell may never
output more water than it holds, so depth cannot go negative regardless of `dt`. A pipe model
written without this clamp produces negative depths and then NaNs, and it is the single most common
port error. ⚠️ **Positivity is not stability.** Above the CFL limit you get checkerboard sloshing
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

**The stability limit** is the gravity-wave CFL condition [courant1928]:

```
dt <= C * dx / sqrt(g * h_max)          # C ~ 0.2 in shipped code, not 1.0
```

Celerity rises with depth, so **a filling pool gets progressively more expensive**. Recompute the
limit from the current state every step; do not compute it once at initialisation.

## Where it stops being the right model

Five limits. The first three are structural — no resolution, tuning or budget reaches them.

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

## Authority: which half of the water is real

A simulated body is exactly one of two things and there is no middle [fluid_authority]:

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

**What it beats.** *Full nonlinear shallow water with a Riemann solver* — correct shocks and
hydraulic jumps, and it needs a wetting/drying treatment and a per-cell wave-speed limit; reach for
it when a dam break is the shot. *An implicit heightfield solve* [kass1990] — unconditionally
stable, and each step is a global solve, so it buys a bigger `dt` you do not need in a frame.
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
| Checkerboard sloshing that never damps, no NaN | `dt` above the CFL limit while the clamp holds positivity | Positivity is not stability — lower `dt` [courant1928] |
| Stable until the pool fills, then explodes | `sqrt(g*h)` grew with depth; `dt` computed once | Recompute the limit each step from the current state |
| Water piles up along the domain border | Closed boundary where an open one was meant | Ghost cells at a very low elevation drain the edge |
| A basin never fills | Open boundary where a wall was meant | Reflect at real walls; fade only where a patch ends inside a larger body |
| Water flows uphill or sits on a slope | Flux driven by bed slope instead of hydraulic head | Drive it by `b + h`, not `b` |
| Explodes when the rain or inflow slider moves | Injection unclamped; `dt_stable` predates it | Clamp per-step injection to a fraction of the local depth |
| Rivers one cell wide and shimmering | Channel narrower than a cell | Carry *discharge* as the physical truth and derive a channel from it |
| The sea built on this has no swell or groups | Shallow-water has no dispersion, by construction | Use a spectral or trochoidal field for open water |
| Splashes never form no matter the resolution | A heightfield cannot represent an overturning surface | Layer particles for the splash; keep the heightfield for the bulk |
| Flood drowns the player but not the AI | Cosmetic water treated as gameplay state on one side | Declare authority; collision and navmesh follow the authoritative field [fluid_authority] |
| Different results on a different machine or frame rate | Step count tied to frames | Fixed step, accumulate the remainder |
