# s17-fetch-and-footprint — where the model stops, and the measurement that split two defects

## Left — the only place basin size enters, and where it runs out

`Ω_c = U₁₀/c_p`, the inverse wave age, against fetch at 6 m/s. It is the single
channel through which the size of the water body reaches the slope statistics.

- Large fetch: `Ω_c → 0.84`, a fully developed sea. **The limit is a guard row**,
  and it did real work — one of the two transcription traps found while sourcing
  reads the fetch law as `0.84·tanh(...) − 0.75`, which at infinite fetch gives
  0.09 and contradicts every source. Read as an exponent it gives 0.84 exactly.
  The limit picked the reading; `spec-fetch-subtract` fires the other one and
  fails eleven rows.
- `Ω_c = 5` at a fetch of **204 m** — the edge of ECKV's fitted domain for this
  wind.
- A 10 m basin gives `Ω_c = 12.33`, **2.5× outside** the largest inverse wave age
  the model was ever fitted at.

**The honest answer for a swimming pool is that this derivation has nothing to
say**, and that is a real limit of the model rather than a failure of the round.
What survives the refusal is the structural result in
`s17-curvature-spectrum`: fetch moves the peak, and the capillary branch that
carries most of `k²S(k)` has no length scale in it at all.

## Right — the control that decided "one defect or two"

The round arrived with a hypothesis worth testing, because two measurements
overlapped and might have been one fault:

- the render's **resolved mss 0.0013** against Cox & Munk's 0.0335 — a factor of
  **26**;
- a real glitter path's **interior standard deviation of 41–60 grey levels**
  (36–70 in a second frame) against the render's **1.0–2.6** — a factor of
  **16–60**.

The hypothesis: the render draws a realisation of the **wrong spectrum**, losing
the capillary tail, so the path is smooth for the *same reason* the resolved mss
is low. One derivation would then close both.

**The control refutes it, and the refutation is this panel.** Both spectra —
ECKV derived, and the flat Phillips the project ships — are integrated to the
wavenumber a pixel of side `L` can resolve, `k = π/L`, which is the same box
filter `SlopeRealisation.slope` already applies:

| footprint | derived (ECKV) | flat Phillips | ratio |
|---|---|---|---|
| 0.05 m | 0.02491 | 0.02571 | 0.969 |
| 0.10 m | 0.02284 | 0.02258 | 1.011 |
| 0.20 m | 0.02032 | 0.01946 | **1.044** |
| 0.50 m | 0.01601 | 0.01533 | 1.044 |
| 1.00 m | 0.01230 | 0.01221 | 1.008 |
| 2.00 m | 0.00868 | 0.00908 | 0.956 |

**They agree to within 4.4% at every scale a pixel of this render subtends.** So
swapping the spectrum moves the resolvable slope variance by *almost nothing*.
The smooth glitter path cannot be blamed on the spectrum.

What the panel does show is the size of the actual gap. At a 0.2 m footprint the
spectrum offers **0.0203** of resolvable slope variance; the render's resolved
field carries **0.0013** (orange line, near the axis) — **15× less**. The render
draws one 90 m swell and its second harmonic, and under ECKV a resolved mss of
0.0013 corresponds to a cut-off of **0.31 rad/m**, i.e. resolving nothing shorter
than about **20 m**. Its own pixels could carry two decades more.

### The verdict, stated so it can be argued with

**The 26× and the 16–60× are one defect — but not the one proposed.** Both follow
from the resolved geometry stopping at the swell rather than being carried down
to the pixel footprint. Neither follows from the choice of spectrum. Wave 12's
*"draw the realisation, not the distribution"* was **necessary and it was not
drawing a realisation of the wrong spectrum** — the spectrum was right to within
4%; the realisation reaches the shading normals and never reaches the surface,
which is exactly what `README-beach` §7 says in words (*"complete for radiance
and absent for silhouette"*) and what this panel now says in numbers.

**That prunes a wave.** The next move on the glitter path is not a better
spectrum; it is putting the realisation into the geometry. `⚠️` The 1.0–2.6
interior sd is quoted from the wave-11 optics verdict and has **not** been
re-measured on a post-wave-12 render in this round, so the *size* of the glitter
gap is carried on attribution while the *cause* is measured here.

*Provenance: **derived**, scene-linear SI. Drawn by
`terrain-renderer/reference-impl/wind_spectrum_figures.py:fig_fetch_and_footprint`
from `wind_spectrum.py`, `beach_optics.K_CAP` and `beach_optics.pm_peak_wavenumber`.
The 0.0013 is read from `reference-impl/README-beach.md` and is **not**
recomputed here — it is drawn as a reference line and carried as `D`
(attribution to this project's own earlier measurement), which is why the suite
carries it as INFO and not as a check. The 41–60 / 1.0–2.6 grey-level figures are
from `gauntlet/sea/bar/generic/` and the wave-11 verdict respectively; that
directory's own README is the authority on what they may be held against.
⚠️ **P (attribution)** for ECKV. Nothing is read off a PNG.*
