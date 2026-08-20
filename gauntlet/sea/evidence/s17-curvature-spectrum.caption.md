# s17-curvature-spectrum — the constant that was standing in for a shape

`B(k) = k³S(k)` is the **slope variance per unit ln k**: `mss = INT B(k) d ln k`,
so the area under each curve here *is* a mean square slope. That makes this the
one plot where the whole slope budget is visible at once.

## Left — what the project had been assuming

The dashed purple line is this project's shipped model. `beach_optics.py` builds
its slope realisation from Phillips' `k⁻⁴` saturation range, which is exactly
`B = constant` — **equal slope variance per octave** — with the amplitude
back-solved so that the whole range returns Cox & Munk:

```
2πB = mss / ln(k_cap/k_p) = 0.004508
```

The coloured curves are `B(k)` derived from the wind instead. Two results, and
they point in opposite directions:

- **The constant was right on average.** ECKV's mean `B` over the *same* band
  range is **0.004188**, against the back-solved **0.004508** — **7.1% apart**.
  The number the code had to assume is very close to the number the spectrum
  derives. That is the fit becoming a consequence a second time, independently
  of the total.
- **The shape was never right, and nothing had tested it.** `B` is not flat. It
  ranges **0.001568 … 0.005395** across the shipped band range — a factor of
  **3.44** — dipping near `k ≈ 30–100 rad/m` and rising again toward the
  capillary peak. Phillips asserts that factor is 1.000.

**This is why the suite carries a shape row beside every total row.** A flat
spectrum scaled to the right total passes every check about a mean; the project
has already shipped one guard that was green on a broken thing *because the mean
was always right*. The defect `spec-flat-b` reintroduces exactly that — flat `B`,
correct total — and **the shape row is the only row in the section that catches
it**.

At 10 and 14 m/s the capillary peak overtakes the gravity range entirely, which
is `α_m`'s second branch (`u* > c_m`) opening up above 6.06 m/s.

## Right — fetch moves the peak and nothing else

One wind, five fetches. The curves separate at the **left** end and lie on top of
one another at the **right** end, and that is the figure's real content.

**Fetch enters this derivation in exactly one place** — the peak wavenumber
`k_p = g Ω_c²/U₁₀²`. The short-wave branch is

```
B_h = ½ α_m (c_m/c) F_m ,    α_m = 0.01[1 + ln(u*/c_m)]
```

and `α_m` contains the friction velocity **and no length scale of any kind** — no
fetch, no basin, no shoreline. So the capillary half of the slope budget is
**scale-free by construction**. Measured at `k = k_m`, a 10 m basin and an open
ocean under the same wind differ by **1.7%**, and that residue is only `L_PM·J_p`,
which tend to 1 far above the peak.

**That is the owner's *"water is water"*, derived rather than asserted.** Shrink
the basin and the gravity waves have nowhere to grow; the centimetre waves that
carry most of `k²S(k)` never notice.

## The grey dashed curve is a refusal, not a prediction

The 10 m basin is drawn dashed and grey because **ECKV has nothing to say
there**. Its peak-enhancement branch is defined for `0.84 < Ω_c < 5`; a 10 m
fetch under this wind gives `Ω_c = 12.33`. The orange curve at **204 m** is where
the fitted domain actually stops for a 6 m/s wind — so a domestic pool is **20×
below it**, and a 25 m competition pool is still **8×** below it. The tall narrow
spike on both is `J_p` with `γ = 1.7 + 6log₁₀Ω_c` running away at young wave age,
which is the model leaving its range in a visible way.

The suite **asserts** the refusal (`a 10 m basin is OUTSIDE ECKV's fitted
domain`) rather than quoting the extrapolated figure, so that no later wave can
pick the number up as a result.

*Provenance: **derived**, scene-linear SI. Drawn by
`terrain-renderer/reference-impl/wind_spectrum_figures.py:fig_curvature_spectrum`
from `wind_spectrum.py`; the flat comparison line uses `beach_optics.K_CAP` and
`beach_optics.pm_peak_wavenumber`, i.e. the shipped model's own two limits.
⚠️ **P (attribution)** for ECKV, whose paper is not held here. Nothing is read
off a PNG.*
