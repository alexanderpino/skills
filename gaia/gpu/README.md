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

The finding, corrected once already in this same file (see below) and now stated for
what it actually is: **this is a property of the algorithm under fp32, triggered by
trajectory, not a property of any one ray class.** An earlier pass here reported
ascending/grazing rays as a clean PASS and confined the fp32 finding to `primary`. That was
wrong, caught the same way everything else in this corpus is caught: by tracing a specific
failure. 7 of 105 rays miss entirely — some `ascending`, some `grazing`, not only `primary`.

1. **Most rays (91 of 105) reproduce the Python fp64 rig's closed-form reference to
   millimetre precision** — the actual validation this file exists to produce: the fence, as
   real GLSL, matches. `ascending`/`grazing` rays that DO hit land within the page's own
   `span/2^6` bound, `+5%` fp32 slack.
2. **The mechanism, traced on one ascending ray by hand**: a ray whose trajectory crosses a
   mip-level cell boundary within about 1e-6 of exactly on it is sensitive to which side of
   that knife-edge fp32 rounding lands it on. Traced case: `z` evaluates to `-7.15e-7` in real
   GLSL — a tiny NEGATIVE number where a coarser estimate would round to a tiny positive one —
   and `floor`/`mod` correctly wrap that to the LAST row of the level's texture rather than
   the first. That wrap is the periodic-domain logic working exactly as designed; the
   trajectory that follows from it simply differs from the one the other side of the knife-edge
   would take. `primary`/`picking` rays hit this constantly because they march far and cross
   many boundaries; `ascending`/`grazing` hit it rarely (7 of 105 here) because they converge
   in a few dozen steps. Rarely is not never, and reporting a class as immune from a sample
   that missed the exception is exactly the overclaim this corpus's registers exist to catch.
3. **The page (`:154-155`) already documents fp32 sensitivity — but only for the *unfixed*
   registration** ("ranged over 36-63% with nothing changed but the registration convention").
   This shader implements the *correct*, fixed registration (the 3x3-dilated apron, matching
   `_pyramid(h, "level0")`) and still shows this sensitivity: genuinely new. **Not gated on an
   absolute figure** (the page states no `a, b, k, k'` for its field, so no rig anywhere can
   assert a number a real GPU would reproduce) but the MISS RATE per ray class is gated, and
   a page-mutation cannot make that gate pass by accident — it fails loudly, honestly, on the
   current, unmutated field, which is the correct state to ship this file in.

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

## The lighter pass — four more real-time documents, 2026-09-15

`heightfield-raymarching/` above cost most of a session, most of it in forensic tracing of one
branchy, stateful algorithm. Not every fenced formula needs that. Most of what a technique
document states as GPU-relevant is pure, branch-free per-fragment math with no loop and no
state — evaluating it at N test points needs no mip pyramid and no step tracing, only a
correct read-back. `lib/pointwise.mjs` is that: launch Chromium once, compile one fragment
shader, feed it up to two vec4 inputs per point (plus, for `gpu-driven-culling/`, a texture
array for a real mip pyramid), and read back one vec4 per point.

**`caustics/`** — the exact unpolarised Fresnel formula and the Henyey-Greenstein backscatter
fraction, both already exhaustively checked in fp64 Python, now confirmed to reproduce the
page's own stated values in real fp32 GLSL. Clean pass, no surprises — which is itself the
finding: these two formulas survive the language change.

**`water-rendering/`** — the roughness-aware Fresnel fit `[bruneton2010]` (`:112-118`), never
tested by any existing rig. Reproduces the page's own two worked degenerate points (`m = 6.3`
and `2.50` at `sigma_v = 0.12` and `0.2`) to the digit. **A genuine new finding**: the page
warns that an unrenormalised blended normal drives `pow(negative, exponent)` to NaN "in
practice." Tested against real fp32 `pow()` for the first time — on SwiftShader/ANGLE it does
**not** go NaN. It silently computes `exp(y·ln(|x|))`, verified consistent across six
negative-base/exponent pairs. The page's engineering conclusion (both clamps are load-bearing)
still holds — a silently wrong small value is not a safer fallback than a NaN, arguably worse
for debugging — but the specific "NaN in practice" wording does not hold on this
implementation. Filed as `WR-POW-NONAN`, explicitly scoped to SwiftShader and untested on real
hardware.

**`gpu-driven-culling/`** — the four-corner-tap HiZ occlusion test (Part 1 of the existing rig),
run against the rig's own depth buffer and mip pyramid (`export_scene.py` imports the rig and
calls `build_scene`/`build_pyramid` directly) over 300 fresh trials. The rule's central safety
property — never wrongly cull visible geometry — holds at all three tested mip offsets on real
GLSL texture fetches: 0 false culls out of 224 drawable trials at every offset. The fence
itself (`:102-108`) is a two-pass render pipeline, not a single shader, and running that for
real was out of scope for this pass — declared, not attempted.

**`virtual-texturing/`** — declared out of scope entirely; see its own `README.md`. Its
central claims are exact arithmetic over fixed constants with nothing GPU-specific to test; its
one genuinely GPU-relevant claim (`SampleGrad` gradient scaling) would need a real mip-tagged
texture and a driver's own LOD-selection heuristic to test honestly, which is a deeper pass
than this round's scope.
