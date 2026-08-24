---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Skill
title: Water Physics
tags: [water, rendering, physics, optics]
status: stable
generated: { by: process:claude-code, at: 2026-08-24T09:31:02Z }
sources:
  - id: chapter
    resource: /references/12-water-physics.md
    title: The water chapter
  - id: provenance
    resource: /references/12b-water-provenance.md
    title: Sources and tiers
# --- end okf v0.2 ----------------------------------------------------
name: water-physics
description: >-
  The measured physics of water, for renderers: the air/water interface (exact Fresnel, the
  1 - 1/n^2 partition, L/n^2 radiance transport, the critical angle and the Snell window),
  inherent optical properties and where a water body's colour actually comes from, sun glitter
  and the slope distribution behind it, caustics and their Jacobian, aerated water (foam, spray,
  whitecaps, bubble optics), the wind-wave spectrum derived from its forcing with Cox & Munk
  recovered as a limit, shoaling and refraction and depth-limited breaking, Sommerfeld
  diffraction and the fan a bay requires, the wave-height population and why a surf line breaks
  up, run-up and swash. Backed by three running reference implementations and their suites -
  a pool, an open coast, and a screen-space pass - so every number is checked against a closed
  form, a published measurement or an independent method. Use when a water number has to be
  right, defended, or re-derived at different constants: "why is my sea green everywhere",
  "what reflectance is foam", "how much light comes back up", "is this glitter path the right
  width", "where does the wave break". For the render-side architecture - LOD, passes, engine
  water systems - route terrain-renderer 12. For generating the bed, route terrain-architect.
---

# Water Physics

You are the warrant behind water rendering. Your job is not to write the shader — it is to
make sure the number in it is the right number, that it is derived rather than remembered, and
that the picture it produces is one the physics actually predicts.

This skill exists because **a water renderer fails on quantities, not on code**. A sea that is
green everywhere has a tint where it should have a path; foam that never hides the bed has a
reflectance where it should have a transmittance; a glitter path of the wrong width has a
distribution where it should have a realisation. None of those is a bug in a loop.

**Division of labour with sibling skills.** The *render-side architecture* — surface LOD, the
fullscreen-triangle pass, pass ordering, what to pre-cook, engine-native water systems,
shoreline integration — is `terrain-renderer`'s chapter `12`, and it routes here for every
number it quotes. *Generating* the bed — the coastal loop, the equilibrium profile, the
morphodynamics that build a bar — is `terrain-architect`'s `12`. BRDF and material math is
`physically-based-rendering`. When a task spans the boundary, take the physics half here and
route the rest.

---

# Part 1 · Doctrine

## The colour is the path, so it must vanish when the path does

The single most common category error in water rendering is a `waterColor` parameter. One
exposure refutes it and needs no measurement: in a frame of a breaking wave shot into the
light, the wave **face** reads saturated translucent green while the same water two metres
away reads grey-blue. The same liquid shows two colours at once, so the green cannot be a tint
on the body — it is a path-length effect, present only where the column is thin *and* backlit.

Everything downstream follows from taking that seriously: absorption and scattering are
properties of the water, and what you see is an integral along a path through them.

## A distribution is not a realisation, and painting one where the other belongs is this
## domain's dominant defect

It has appeared in five separate places in this work, and it looks different every time:

| Where | The expectation that got painted | What it looks like on screen |
|---|---|---|
| glitter | the slope PDF as an ensemble mean | a smooth airbrushed sheen instead of separate sparkles |
| foam | `coverage(m) = 1 − exp(−m)`, the void probability of a Boolean model | one continuous soft grey band, both edges continuous curves |
| swash wetness | the time-average of the run-up | a static damp stripe that never advances or dries |
| sand cover | an area fraction used as a blend coefficient | uniform tint where there should be patches of bare rock |
| the wave field | one `H` field, so every wave is the same height | one unbroken surf line arriving on a metronome |

**An expectation that varies smoothly in `x` *is* an airbrush gradient.** That is what the
operation means, not a side effect of it. The fix is always the same shape: draw a realisation
of the distribution, at the correlation length the photographs show, and let the mean fall out.

## Compose the error; do not reason term by term

Attenuation and escape do not factorise: `⟨fg⟩ = ⟨f⟩⟨g⟩ + Cov(f,g)`, and a LUT is exactly where
you will separate them without noticing. Two errors on one page can run opposite ways — a
truncation that makes a trap too weak and a lossless constant that makes it too strong — and
each looks defensible alone.

## Derived, guarded, and never called

A quantity can be derived from first principles, guarded by a hundred passing rows, written up
in a chapter, and **executed by nothing**. Every coverage instrument reports it as covered,
because the suite is the caller. It has happened four times here.

The check that works is `grep` for the symbol, requiring a hit **outside its defining module
and outside the suite**. The reference implementations carry reach rows that count integers off
the rendered buffer rather than asserting coverage.

## A near-zero is worthless until the target has been shown reachable

A measurement that returns "no effect" proves nothing until the instrument has been shown able
to return a non-zero on a case where one is known to exist. Every control in this skill is
written that way, and `--selftest` / `--bugs` exist to prove the guards can fail.

---

# Part 2 · The executable half

Four implementations, four suites, and they are **not interchangeable** — each is blind to
what the others test.

| Directory | What it is | Its arbiter |
|---|---|---|
| `reference-impl/` (pool) | A 1.40 m domestic pool: the cleanest optics laboratory available — flat datum, known bed, known depth, `b_b ≈ 0`. Every doctrine statement carrying a number was derived or falsified here | `python3 validate.py` — **306 pass / 0 FAIL / 64 info**, ~2 min |
| `reference-impl/` (coast) | An open coast: bathymetry and the morphodynamic loop, wave transform and depth-limited breaking, Sommerfeld diffraction, the wave-height population, the foam realisation, the camera and the renderer | `python3 validate_beach.py` — **612 pass / 0 FAIL / 0 ERROR / 36 open / 107 info**, ~28 min |
| `reference-impl/` (axes) | The six axes: `ice.py` (phase), `jet.py` (Weber), `impact.py` (impulse), `openchannel.py` (travelling vs standing), `thinfilm.py` (interference) and `vortex.py` (frame). Closed forms and named scalings, with every fitted constant exposed as an argument rather than baked in — and where a source gives a form without its coefficients, **there are no defaults** | `python3 validate_phases.py` — **41 pass / 0 FAIL / 1 info**, seconds; `--bugs` catches **8 of 8**. Its prose is guarded separately by `validate_chapter.py` — **120 numbers / 0 drifted** |
| `raster-impl/` | The real-time screen-space pass, its LUT and its wave surface. It exists because the offline path **structurally cannot** test approximation error — a code path that does not approximate has none | `python3 validate_raster.py` — **200 rows / 0 FAIL**, three tiers, ~2 min |

**Every tolerance is justified from the estimator's own error, never from the disagreement it
reports**, and `-v` prints that justification per row. `validate_beach.py --bugs` re-runs the
whole suite once per deliberately reintroduced defect and prints which rows caught it — a suite
that catches nothing is the failure this guards against.

**And two invariants keep the *documentation* from drifting from the code**, because a chapter can
go stale in ways no physics suite notices. `make_figures.py` imports the implementation rather than
restating it, so **a figure cannot drift from the code that ships**; `validate_chapter.py` re-derives
**120 numbers quoted in the chapter's prose** and holds each to half a unit in its own last printed
digit — so a stale sentence fails a run instead of surviving one. Both carry a `--bugs` harness of
their own.

    python3 reference-impl/beach_render.py --scene         # the current scene, with reach integers
    python3 reference-impl/validate_chapter.py             # prose against code, 120 numbers
    python3 references/figures/make_figures.py --selftest  # prove the figure guard can fail

## What transfers from a pool to the sea, and the one thing that does not

| Transfers unchanged | Why |
|---|---|
| external and internal Fresnel, the critical angle | properties of one interface and one IOR; the ocean's `n` is 1.339 against fresh water's 1.333 |
| the `1 − 1/n²` partition, `L/n²` across the interface | geometry and IOR only |
| Beer–Lambert along every leg | the law, not the coefficient |
| the trapped series, wherever there is a bottom in reach | geometry |
| the meniscus, the glitter path, the caustic Jacobian | surface mathematics |
| **the IOPs** | **nothing transfers. `b_b ≈ 0` is the pool's degenerate case and it is false everywhere in the sea** |

---

# Part 3 · Routing table

| Reference | Covers |
|---|---|
| `references/12-water-physics.md` | The chapter: the interface and its two Fresnel constants, radiance transport across it, the trapped series as a **bound**, what a submerged face sees, IOPs and where a body's colour comes from, sun glitter, caustics and the masking contract, aerated water, sea states, calm water, shoaling and refraction and breaking, diffraction, the wave-height population, the surf zone and the representation limits on it — and the **six axes** the rest of it is a point on: phase (ice), Weber (every free jet from a trickle to a fire hose), impulse (water entry and the Worthington jet), travelling-vs-standing (the hydraulic jump), interference (thin films) and frame (a drain vortex that stands, a shed vortex that travels) |
| `references/12a-water-derivations.md` | The **mathematics and pseudocode** behind every result the chapter quotes in a line, with the suite row that guards each |
| `references/12b-water-provenance.md` | **Sources and provenance**: every tier, every citation, every `?`, and the `P/T/D/F/N/?` convention restated so it reads alone. Read before citing anything out of this skill |
| `references/12c-uncovered.md` | **The gap register, and how each entry closed.** All six are now closed with formulas, an implementation, a figure and suite rows. Five were found by searching along **axes** rather than listing subjects; the sixth, vortex structure, had its axis from the start and was missing a **source** — it sat marked *open and unsourced* for several rounds rather than being written from memory. The file keeps that distinction because the two failures have different remedies. Read it before concluding that something is absent by oversight |
| `references/figures/` | The figures, drawn by one script that imports the implementation read-only and writes no physics of its own — so a figure cannot drift from the code that ships |

## Cross-skill routing

| Need | Route |
|---|---|
| Render-side architecture: water LOD, the fullscreen-triangle pass, pass ordering, what to pre-cook, engine-native water, shoreline integration, stylized water | **terrain-renderer** `12` |
| Real-time fluid simulation: SPH/PBF, FLIP/APIC, MPM, coupling, buoyancy | **terrain-renderer** `19` |
| Generating the bed: the coastal loop, the equilibrium profile, the morphodynamics that build a bar | **terrain-architect** `12` |
| BRDF math, specular AA theory, general scattering | **physically-based-rendering** |

## Provenance

Tiers are `P` paper/book · `T` talk · `D` derived or measured here · `F` folklore · `?` claimed
but unverified. ⚠️ **`D` in this skill means derived or measured *here*, and it is the strongest
tier**, not the weakest — it means a closed form, a published comparison or an independent
method is in the repository and can be re-run. **Never upgrade a tier to satisfy a question,
and never fabricate a citation.**
