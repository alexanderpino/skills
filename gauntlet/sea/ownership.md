# Ownership — one file, one owner, per wave

Rewritten at each wave start. Wave 12.

## The re-cut, and why

Wave 11 put three critics on the visual dimension, one per lane, in separate
contexts. All three scored 3/10 decisive/major, and **two of the three named the
LAND as the largest tell in frame — and both recorded it as out of their lane.**
The bar's own overriding rule had predicted exactly that: *the tell is usually
not the water; it is usually the sand, the rock, the foam edge or the horizon.*
The lane cut had put the biggest defect where nobody owned it.

Both "not closeable in this lane" verdicts pointed the same way:

> *rock, bench, cliff and headland cannot be rendered until the bed generator
> produces slopes that cross the rock threshold and relief above the waterline.
> That is a change below this lane.*

> *the surf-line count is not closeable here — three to four separated lines
> require a bar system in the depth field, which sits below this lane.*

A boundary that both critics had to reach through is in the wrong place. So the
lanes are **re-scoped, not renamed**: the names stay so that wave 1–11's round
records keep matching, and the scope moves under them. The lane set does not
grow — four lanes, as at intake.

## The lanes, as of wave 12

### `bathymetry` — everything solid, wet or dry

Now owns **the subaerial land as well as the bed**, and owns the bed *generator*
rather than consuming its output. This is the change that makes the two
not-closeable verdicts closeable.

- the coastal loop and the hardness field — and whether their output crosses the
  rock threshold at all
- relief above the waterline: cliff, headland, wave-cut bench, offshore outcrop
- the beach face, sand texture and the wet/dry boundary
- the depth field's bar system, including whether it can carry more than one
  breakpoint

Files: `beach.py` (bed and plan-form functions), `beach_render.py` (geometry and
material paths), `validate_beach.py::_sec_bathy` and `_sec_embay`.

### `wave-field` — the field, the breaking, and the foam as a field

Foam moves here in full. It is a breaking phenomenon with coverage, advection and
decay before it is an optical one, and wave 11 split it across two lanes, which is
how it ended up owned by neither in practice.

- the offshore spectrum, shoaling, refraction, diffraction
- breaking, and the surf zone's structure
- **foam: coverage, texture, advection, decay, stranded lace** — everything the
  wave-field critic called an airbrush gradient

Files: `beach.py` (wave-field functions), `beach_foam.py`,
`validate_beach.py::_sec_wave*` and the diffraction section.

### `optics` — the surface, the column, and the sky

- **the stochastic small-scale slope realisation** — the single highest-value
  item in the wave: the optics critic showed that glitter granularity and the
  flat water body are *one* defect, the render drawing the ensemble mean of the
  glint distribution and never its samples
- glitter, the surface BRDF, water colour and transparency
- entrained air's radiative effect, the submerged bed's appearance
- the sea–sky seam and the horizon

Files: `beach_optics.py`, `optics.py`, `validate_beach.py::_sec_bed` and the
optics sections.

### `chapter` — still behind the WIP limit

Unchanged, and still not funded. Do not widen a wave to fit it in.

## Boundaries that must not blur

- **The depth field's bar system is `bathymetry`'s**, and `wave-field` consumes
  it. A wave-field round must not add a breakpoint by hand to get a second surf
  line; that is the defect wave 11 named, moved rather than fixed.
- **Foam's geometry is `wave-field`'s; foam's radiance is `optics`'.** If a round
  cannot tell which side of that line it is on, it is on the wave-field side —
  texture before brightness.
- **`optics.py` is shared with the pool.** Standing ruling 6: the pool does not
  disappear, its frames stay bit-identical unless a physics correction is the
  cause, and its suite stays green.

## Not a lane, and now scheduled

**Captions move to sidecars.** Wave 11's three critics each reported, unprompted,
that the blind was defeated because every evidence frame carries the builder's
changelog burned into the pixels — and one had to crop before it could judge a
hero frame at all. Recorded in `gauntlet-loop/references/blind-protocol.md`.
From wave 12 every figure writes `<name>.caption.md` beside `<name>.png`, and
**hero frames carry no text at all**. This is owned by whichever lane writes the
figure, not by a lane of its own.
