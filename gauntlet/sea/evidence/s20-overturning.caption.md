# s20-overturning — where the shipped surface wants to go multivalued

**Wave 20, scout round. Drawn by `gauntlet/sea/scout/figure-overturning.py`
from the arrays `scout/measure-overturning.py` and
`scout/measure-breaker-class.py` saved.** Nothing was built and
`terrain-renderer/reference-impl/` was not modified. All quantities are
scene-linear; no PNG was read for physics. Provenance marks are per panel.

**1 — the bar flank the wave breaks on.** `M`. The shipped bay's bed at the
middle alongshore row (y = 0), from `run_bay()`. The green dashes are the two
places where `H/d` crosses the breaker index `γ_b = 0.78` from below, in water
deeper than `D_MORPH_MIN`, computed exactly as `beach.breakpoints` computes them.
The seaward crossing lands at **x ≈ 496 m, on the steepest cell of the bar's
seaward flank** — |m| = 0.223, one in 4.5. The bar is the loop's own Exner
output; the breakpoint is the transform's own statement; nothing here is placed.

**2 — the local surf-similarity number across it.** `D` from `beach.iribarren`
on measured fields. `ξ = tanβ / √(H/L)` cell by cell, with `tanβ` the local bed
slope and `L = 2π/k` the transform's own local wavelength. It rises through the
**0.4 spilling/plunging boundary** (Battjes' local-quantity threshold set, the
one `beach.breaker_class(which='local')` carries) at x ≈ 482 m and reaches
**1.085 at x = 494 m**, where the wave breaks. Over all 89 rows the value at the
flank is **ξ = 1.110, range 0.967–1.203, plunging on 89 of 89 rows** under both
published threshold sets. The curve is clipped at 1.29 for the axis; the
shoreward spike past x = 600 m is the beach face, where the model hands over to
swash. ⚠️ The value depends strongly on the window the bed slope is differenced
over — 40 m gives 0.142 and reads *spilling*; the ladder is in
`scout/measure-breaker-class.log`.

**3 — face-angle exceedance.** `M`. `beach_render.surface_slope` at the shipped
`eps = 0.5 m`, over 90 000 world points, 8 instants across one period, plotted as
the per-point maximum. Two branches of the `SPECTRAL_ON` control panel, one flag
apart. The carrier alone (waves 5–18) stops at **16.02°**, against its own closed
form `max(a·k) × max(slope_gain) = 0.1481 × 2.000 = 0.2945 = 16.41°`. The shipped
surface (wave 19's transported bundle) reaches **43.53°** here and **46.89°** in
a 0.2 m fine zoom — past Stokes' 30° corner (`P`, and it caps waves of *permanent
form*, which a 256-component sum is not) and past the one-face 41.48° figure
(`D`, `90° − asin(1/n)` on `optics.IOR`'s green entry). Section A is nevertheless
still unreachable, because chapter 12's criterion is on the **sum** of two
crossings of the same ray, `α₁ + α₂ ≥ 82.96°`.

**4 — where the second-order validity clamp bites.** `M`. Orange is every wet
cell where the amplitude ratio `r` that second-order Stokes asks for exceeds
`beach.stokes2_crest_limit(ψ)`, the largest `r` for which the shape still has one
crest and one trough per cycle. **74.78 % of the wet bay**, spanning x = 214 m to
the shoreline and depths 0.10–7.14 m, with `r_raw/r_limit` median **50.5×** and
max **154×**. The green line is the seaward breakpoint per row. This is the
implementation's own statement that its shape has run out, and it is the
pre-image of the representation change priced in
`gauntlet/sea/overturning-price.md`.

**What else was running.** `nproc` = 4, two other builders' `python3` processes
at 100 % and 124 % CPU throughout. Wall-clock costs quoted in the price document
are upper bounds.

**The companion measurement, which has no panel because it is one number.**
`scout/measure-two-cone.py`, `M`, 45.9 s: over **10 889 060** admissible
ray-pairs on the drawn surface — pairs whose joining segment lies below the free
surface everywhere between, which is chapter 12's own condition — the best
`α₁ + α₂` anywhere in the scene is **68.48°** against the 82.96° two-cone floor,
**none** clears it, and the per-start-point p99.9 is 43.20°. The carrier alone
reaches 31.31°. 68.48° is already past the 60° a wave of permanent form can
reach, so the remaining 14.48° is not available to steepness.
