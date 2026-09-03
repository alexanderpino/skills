---
type: Technique
title: Stream power — the erosion backbone at map scale
description: "The one-line incision law, the O(N) implicit solver that makes it tractable, the companion diffusion term, and the slope-area check that proves it."
tags: [generation, erosion, stream-power, landscape-evolution, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: braun2013, tier: P, locator: "the O(N) stack ordering and the unconditionally stable implicit discretisation. NOT OPENED — Geomorphology is paywalled at Elsevier and no open copy was reachable from here, so nothing inside it is named. The scheme this document implements was read instead in cordonnier2016 section 5, eq. 2 — the same implicit update, solved with the receiver already known by parsing the stream trees root-to-leaves, and stated there as O(N) — and cordonnier2016 section 1 calls it 'the original method from Braun and Willett 2013'" }
  - { id: cordonnier2016, tier: P, locator: "READ IN FULL. Section 3.1 Geological Background, eq. 1 — dh(p)/dt = u(p) − k*A(p)^m*s(p)^n, the uplift coupling, with the paper's own sentence 'As in most geomorphological studies, we use n = 1 and m = 0.5'; section 5 Erosion, eq. 2, the implicit update h_i(t+dt) = (h_i(t) + dt*u_i + f*h_j(t+dt))/(1 + f) that this document's solver block transcribes, with the ordering requirement and the O(N) claim stated in the two sentences after it; section 4.3 Lake Overflow for the lake super-graph that handles local minima inside the loop, and its statement that Braun and Willett's own optional lake step costs O(N*sqrt(N)) against this paper's O(N + M log M). NOT the diffusion term: eq. 1 carries none, that is culling1960" }
  - { id: whipple1999, tier: P, locator: "the concavity ratio m/n ≈ 0.5, and the roles of m and n. NOT OPENED — JGR is paywalled at AGU and no open copy was reachable from here, so nothing inside it is named. The concavity claim alone was read second-hand in cordonnier2016 section 3.1, which states that 'the ratio m/n is constrained by the shape of the stream profiles and is thought of being m/n ≈ 0.5' and attributes it to Whipple and Tucker 1999. The kinematic-wave knickpoint celerity that this document's Knickpoints section also hangs on Whipple is NOT covered by that second-hand reading and is unverified" }
  - { id: crosby2006, tier: P, locator: "knickpoint distribution across a network. NOT OPENED — Geomorphology is paywalled at Elsevier and no open copy was reachable from here. The 236 waterfalls in the Waipaoa is the paper's own TITLE, not a place inside it, so it is a citation and not a locator; nothing in the body of this document has been checked against the paper's text" }
  - { id: culling1960, tier: P, locator: "hillslope transport as diffusion, the D*grad^2(h) term. NOT OPENED — Journal of Geology 1960 sits behind JSTOR and no open copy was reachable from here, so no section or equation inside it is named" }
  - { id: explicit_diffusion_limit, tier: F, locator: "no artefact: the explicit FTCS bound, dt <= dx^2 / (4D) in two dimensions. Von Neumann analysis, standard and unpublished as such" }
---
# Stream power — the erosion backbone at map scale

Past roughly 50 km of extent, this is the only erosion model that is stable over geological time
and the only one that produces correct large-scale drainage. Everything it needs comes from
elsewhere: `U` from `tectonic-uplift.md`, drainage area `A` and the receiver array from
`flow-routing.md`, and `K` from lithology.

⚠️ **It needs single-receiver routing.** The stack is built from a receiver *array* — one
receiver per cell — so [braun2013] requires **D8** (or D∞ collapsed to its steeper neighbour),
and `A` must be the accumulation computed on those same single receivers. An MFD field cannot
build the stack: there is no unique `receivers[i]` to order it by, and an MFD `A` disperses the
area the incision law is keyed on. MFD's place in this pipeline is masks and wetness fields
(`flow-routing.md`), not the erosion solve.

## Use this

**`∂h/∂t = U − K·A^m·S^n + D·∇²h`, solved with the O(N) implicit stack method** [braun2013],
with depressions handled **inside** the loop [cordonnier2016] and the diffusion term always on
[culling1960].

`m ≈ 0.5`, `n = 1`. The concavity ratio `m/n ≈ 0.5` is the well-constrained part [whipple1999]:
it is what makes river long profiles concave and it matches measured rivers. Whipple & Tucker
itself could not be opened here; the claim is taken from [cordonnier2016] §3.1, which states that
"the ratio `m/n` is constrained by the shape of the stream profiles and is thought of being
`m/n ≈ 0.5`" and cites Whipple & Tucker for it, then adopts `n = 1`, `m = 0.5` on that basis.
Use `n = 1` unless you have a reason; `n` in 1–2 is defensible and the visual difference is
subtle.

## Why the solver is the whole difficulty

The equation is one line. The explicit form is unstable under a CFL-like condition that scales
with `A^m`, and `A` spans six orders of magnitude across a map, so the timestep is dictated by the
largest river and you need millions of steps. This is why naive implementations either explode or
take hours.

[braun2013] discretises it implicitly. For `n = 1` the result is linear and closed-form, and the
receiver has already been updated when you reach a cell, because the stack is ordered base-levels
first. Braun & Willett could not be opened here, so the block below was checked against
[cordonnier2016] §5 eq. 2 instead, which is the same update written for a stream *tree*
(`h_i(t+δt) = (h_i(t) + δt·u_i + f·h_j(t+δt)) / (1 + f)`, with the receiver `j` solved first by
parsing root-to-leaves). The attribution to Braun & Willett is in that paper's **§1** — "The
original method from [BW13] is extended to efficiently model water flowing from lakes" — and §4,
where extending it to lakes is costed at O(N√N). ⚠️ This passage used to place the attribution in
§5; §5 states the scheme and the ordering requirement and cites nobody, so the section named as
the credit was the one section that does not give it.

```
stack = buildStack(receivers)               # flow-routing.md, "Accumulation, and the three arrays"
for i in stack:                             # FORWARD order
    if receivers[i] == i:                   # base level
        h[i] += U[i] * Δt;  continue
    r = receivers[i]
    f = K * Δt * pow(A[i], m) / dist[i]
    h[i] = (h[i] + U[i] * Δt + f * h[r]) / (1 + f)
    h[i] = max(h[i], h[r])                  # never fall below your receiver
```

Three lines, unconditionally stable, O(N), and it dissects a flat plate under constant uplift into
a proper dendritic network. `Δt` can be 1000 years or more; a 4k map reaches equilibrium in a few
hundred steps.

⚠️ **`receivers[i] == i` covers two different things, and the uplift line is not optional for one
of them.** The *domain edge* is a base level you declared: it is where water leaves, it must be
pinned, and `U` there must be zero. Every other self-receiving cell is an *interior local minimum*
the receiver rule produced this step — and for those, `h[i] += U[i]*Δt` is the only thing that
lifts a pit back out. It is not bookkeeping for cells that happen to have no receiver; it is the
mechanism, and skipping it is a plausible misreading of the word "base level". Measured on a
100×100 plate, 500 steps, `U = 5e-4 m/yr`, `Δt = 1000 yr`, `K = 3e-5`, `m = 0.5`, `n = 1`:

| base-level handling | after 500 steps |
|---|---|
| `continue` without the uplift | **1027** interior self-receiving pits, the largest draining 19 cells |
| the printed line applied to the edge as well | **632** pits; edge and interior both at 250 m, so no relief at all — the whole plate rose |
| uplift on interior minima, edge pinned at `h = 0` with `U = 0` | **0** pits; `log S` vs `log A` slope −0.498 |

So: pin the edge outside this loop (or keep it out of the stack), and let the printed line run on
everything else. A reader who treats the edge as an ordinary base level raises the plate uniformly
and erodes nothing.

For `n ≠ 1` the implicit equation is nonlinear — guarded Newton–Raphson or bracketed root finding,
converging in a handful of iterations, and restricted to single-flow routing in mature
implementations.

**The depression guard belongs inside the solver, not only before it.** Filling before routing is
not sufficient, because erosion recreates pits as it runs. Never update a cell below its
already-updated receiver or into a flooded node — the `max(h[i], h[r])` line above is that guard —
and expose the correction count as a diagnostic that must not grow without bound. Re-running a
full depression fill every step is O(n log n) per step and dominates the run; [cordonnier2016]
handles minima with a lake graph inside the loop instead, and that is the version to implement.

## The diffusion term is not optional

Stream power carves channels and leaves the interfluves as unweathered plateaux. `D·∇²h`
[culling1960] is what gives them hillslopes, and `D` competes with `K` to select **valley
spacing** — which is the one landscape property the pair exists to set, and the reason the term
belongs inside the same solver rather than bolted on as a separate pass. Raising `D` widens valley
spacing; raising `K` tightens it. Past some `D`, diffusion erases the network rather than
coarsening it.

⚠️ **Sub-cycle strictly, not exactly.** The explicit Laplacian is stable for `D·dt/Δx² ≤ 0.25`
[explicit_diffusion_limit] — no canonical paper; it is the von Neumann bound on the FTCS
discretisation, `Δt ≤ Δx²/(4D)` in two dimensions, standard in any numerical-methods text — so
`ceil(D·dt / (0.25·Δx²))` lands *exactly* on 0.25 whenever it divides evenly. At exactly 0.25 the
checkerboard mode's amplification factor is `1 − 8c = −1`: it flips sign every step and its
amplitude is **preserved, never amplified**. The field stays finite and mass stays conserved,
every other mode damps, and grid noise is the one thing left standing — so the pass reads as
though it roughened the terrain when what it did was smooth everything except the artefact. Keep
a 0.9 safety factor (`c = 0.225`) and assert the *direction* of the effect, not merely that the
output is finite.

⚠️ **A thermal pass is not a substitute for `D·∇²h`.** Slope-limited relaxation
(`thermal-and-aeolian-erosion.md`) is cheaper and gives repose-angle behaviour the Laplacian
cannot, and it will take the knife-edge off an interfluve — but that is the *visual symptom*,
not the mechanism. It does nothing at all below the talus angle, it drives faces to planar
repose where diffusion makes hilltops convex, and it carries no `D`, so it cannot participate in
the `D`-versus-`K` competition that selects valley spacing. Run both if you want repose faces;
if valley spacing is a parameter you are tuning, `D·∇²h` stays.

## Knickpoints are outputs, not stamps

A waterfall is a **knickpoint** — a step where the long profile departs from its concave
equilibrium. There is no waterfall algorithm. With `n = 1` the incision equation is a kinematic
wave, so a step migrates *upstream* at a celerity set by discharge, preserving its height rather
than diffusing away [whipple1999] — a claim this document has **not** been able to check against
Whipple & Tucker, which was not obtainable, and which the second-hand reading through
[cordonnier2016] does not cover:

```
C_kp(A) = K * pow(A, m)      # m/yr upstream — larger rivers consume knickpoints faster
```

Which is why trunk streams have rapids and small tributaries keep their falls — [crosby2006]
mapped 236 of them, though "236 waterfalls in the Waipaoa" is that paper's *title* and not
something read inside it; the paper was not obtainable here. The solver above already *produces* knickpoints wherever
`K` jumps, and the `max(h[i], h[r])` guard is what preserves the step. So: to get a durable
waterfall, put a **hard bed across the channel**; to get a migrating one, **drop the base level**
and let it run. Carving a vertical cliff into the heightfield with uniform `K` gives a step
nothing pins, and the next pass relaxes it into a rapid.

**What it beats.** *Droplet erosion at map scale* — a droplet's path is a fixed number of steps
(~30–60), each about one cell, so its reach is `lifetime × cellSize`: a few tens of cells,
whatever they measure. On a grid whose drainage network spans thousands of cells that is a
scratch, not a valley (`hydraulic-erosion.md`). *Pipe erosion at map scale* — bounded by CFL
on a timestep measured in seconds, when the process being modelled takes 10⁶ years. *The explicit
stream-power solver* — same equation, timestep set by the largest drainage area, so millions of
steps and it still explodes. *Stream power on a 500 m map* — produces nothing, because there is no
drainage area worth speaking of; use `hydraulic-erosion.md`. *A terrace node for strata steps* —
quantises absolute elevation, so the steps cut across valleys instead of following bed geometry.

**Time budget.** Strictly authoring-time, and it is the cheapest of the three erosion backbones per
unit of simulated time precisely because `Δt` is unbounded: push it to 100–5000 years and take
hundreds of steps rather than millions. What costs is the per-step routing — receivers, stack,
accumulation — which is why the in-loop depression handling matters more than the erosion
arithmetic. Nothing here runs per frame; a runtime consumes the baked result.

**Verify it, because eyeballing will not.** Plot the main channel's long profile: it must be
concave. Plot `log(S)` against `log(A)` for channel cells: it must be a straight line of slope
`−m/n ≈ −0.5`. That check is direct, cheap and quantitative, and it catches implementation errors
that look fine in a hillshade.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| The solve explodes, or needs millions of steps | Explicit discretisation; `Δt` bounded by the largest `A^m` | The implicit stack solve [braun2013] |
| Knife-edge interfluves between channels | The diffusion term omitted | Add `D·∇²h`; a thermal pass hides the symptom but does not restore the `D`/`K` valley-spacing control |
| Everything smooths except a persistent checkerboard | Sub-cycling landing exactly on `D·dt/Δx² = 0.25`; the checkerboard's factor is exactly −1, so it is preserved | `c = 0.225` |
| The network is erased rather than coarsened | `D` too high relative to `K` | Lower `D`; measure valley spacing, not channel count |
| Cells sinking below their receivers; pits reappearing | Erosion recreating depressions mid-run | The `max(h[i], h[r])` guard, and in-loop lake handling [cordonnier2016] |
| Each step costs O(n log n) and the run crawls | A full depression fill re-run every step | Lake graph inside the loop [cordonnier2016] |
| `log S` vs `log A` is not a straight line of slope −m/n | Wrong drainage area, wrong receiver distances, or an unhandled depression | Fix routing before touching the erosion |
| A convex long profile | `U` and `K` mis-scaled, or the run stopped far from equilibrium | Check `U × time` against the relief you want |
| A carved waterfall relaxes into a rapid | Uniform `K`, so nothing pins the step | A hard bed across the channel, then let the solver run |
| Waterfalls everywhere, including on trunk rivers | Knickpoints stamped rather than produced | Author the cause — a `K` jump or a base-level fall |
| A flat, featureless result on a small map | No drainage area at this extent | Wrong backbone; use droplet or pipe |
