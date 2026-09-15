# gpu — the fenced algorithms, run as real shaders

`rigs/` proves a technique document is self-consistent, in CPython. This directory proves the
same document's fence runs correctly **in the language it is actually written for** — and,
where this container allows, measures what it costs.

## The one environment fact everything here defers to

**This container has no hardware GPU.** Headless Chromium's WebGL2 here runs on SwiftShader, a
software rasterizer (`ANGLE ... SwiftShader Device`, confirmed at the top of every script
before it runs anything else), and `navigator.gpu` (WebGPU) is unavailable entirely. So:

- **Wall-clock timings printed here are NOT a frame cost on any GPU a player owns.** They are
  printed anyway, loudly labelled, because omitting them silently would look like nothing was
  measured. What is safe to trust from them is a comparison *within one run* (gate-on vs
  gate-off); the absolute number is SwiftShader's, not a real device's — the same caveat
  `rigs/README.md` states for the Python rigs' CPython wall-clock, one level further down.
- **Step counts, texture-fetch counts and hit/miss/error results are hardware-independent** and
  reproduce on any conformant GL ES 3.00 implementation. These are the numbers worth trusting.

## Why this exists at all

Every rig in `rigs/` is a Python transcription of a fence. None had ever been run as a shader
before 2026-09-15. A shader-language defect — a sampler-array indexing restriction, an ANGLE/
SwiftShader rounding quirk, a texture-unit bookkeeping mistake in the harness itself — is a
failure mode nothing in `rigs/` can find, by construction.

## What one document turned up: `heightfield-raymarching/`

The fence was transcribed line-for-line into GLSL ES 3.00 (`shaders.mjs`), checked against the
**exact scene** `rigs/approx/heightfield-raymarching.py` runs (`export_scene.py` imports the
rig as a module and dumps its own field, its own 105 rays and its own closed-form reference —
so nothing here re-derives the field formula or the ray generator independently; a divergence
is attributable to the execution engine, not to two different inputs).

Three outcomes, not one:

1. **`ascending`/`grazing` rays (52 of 105): PASS, to millimetre precision** against the page's
   own `span/2^6` bound. This is the actual validation — the fence, run as real GLSL on a real
   (if software) rasteriser, reproduces the Python fp64 rig's closed-form reference.
2. **`picking` rays: NOT gated, matching the Python rig's own documented reason** — a
   column-locked ray's level-0 span is the rest of the ray, and the refine's fixed 8-step scan
   is not fine enough to bracket reliably over tens of metres. Known, not new.
3. **`primary` rays: a NEW finding.** The page (`:154-155`) already documents fp32 sensitivity
   — but only for the *unfixed* registration ("a third, in fp32, ranged over 36-63% with
   nothing changed but the registration convention"). This shader implements the *correct*,
   fixed registration and still shows severe errors (up to 97.6 m) on a subset of primary rays.
   The mechanism: a ray that crosses a mip-level cell boundary within about 1e-6 of exactly on
   the boundary can enter a many-step near-livelock, because the relative-step epsilon
   (`2.38e-7`) sits at the edge of what fp32 can resolve there. A bit-for-bit fp32 emulation of
   the same algorithm in Python (`numpy.float32` on every operation, see the session's
   `fp32_trace.py`) reproduces the same livelock pattern and *does* eventually escape to the
   correct answer. SwiftShader's actual execution escaped sooner, to a wrong answer — meaning
   the escape point is sensitive to the exact rounding behaviour of `floor()`/`mod()` on the
   executing driver, not just to "fp32 vs fp64" in the abstract. **Not gated** (a page that
   states no `a, b, k, k'` for its field cannot be gated on an absolute error a real GPU may or
   may not reproduce) but reported loudly, because a silent pass/fail here would hide the one
   result this exercise was built to find.

## Two bugs found and fixed in THIS harness, not in the algorithm

Recorded because a harness that hides its own mistakes is worse than one with none to hide:

1. **`_node_max` and `_surface` wrap periodically** (`% n`), matching the field's own
   periodicity; the first version of `texelAt`/`surface()` here clamped to the edge instead,
   producing errors of tens of metres on any ray whose projected position drifted outside
   `[0, NG·S0)` — which oblique rays do routinely.
2. **A texture-unit collision.** The output render target was bound to `TEXTURE0` after
   `uPyramid[0]` had already claimed that unit, silently zeroing every level-0 read. Found by a
   step-by-step trace comparing the shader's per-iteration state against an instrumented Python
   port of the identical control flow (`trace.py`, `debug_one.mjs`). Fixed by moving the output
   texture to an unused unit.

Neither is a shader-language or SwiftShader finding — both are this driver's own mistakes,
caught the same way this corpus catches everything else: by running a mutation (here, a
step-by-step trace) and reading what actually came back, not what was expected to.

## Running it

    python3 gaia/gpu/heightfield-raymarching/export_scene.py > scene.json
    node gaia/gpu/heightfield-raymarching/measure.mjs scene.json

Requires Node with `playwright` resolvable (`npm link playwright` against a global install) and
the Playwright Chromium at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
