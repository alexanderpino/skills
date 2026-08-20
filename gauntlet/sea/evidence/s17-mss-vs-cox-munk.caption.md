# s17-mss-vs-cox-munk — the fit, returned as a limit

Thirteen waves took the sea's mean square slope from one cited line,
`mss = 0.003 + 5.12e-3 U`. It is honest and it is **not derived**: a 1954
empirical summary of what wind does to open water with long fetch, obtained by
photographing sun glitter from an aircraft. Feeding it to a scene asserts a
measurement taken somewhere else, and the standing ruling is that the physics
comes from physical effects rather than from a constant chosen to make the
picture right.

This figure asks the only question that retires that objection: **compute the
slope statistics from the forcing instead, and see whether Cox & Munk comes
back out.**

## Left — the control whose answer was known in advance

`mss = INT k² S(k) dk` over an ECKV (1997) spectrum at large fetch, against the
1954 fit and its own published ±0.004 band. The wind is converted 10 m → 12.5 m
by a neutral log profile before the comparison, because ECKV is parameterised on
`U₁₀` and Cox & Munk's mast was at 12.5 m — 2.1%, and the answer key's G2 trap.

| U (12.5 m) | Cox & Munk | derived, full integration | gap |
|---|---|---|---|
| 3 m/s | 0.01836 | **0.02491** | **+0.00655** — outside the band |
| 6 m/s | 0.03372 | **0.03597** | +0.00225 — inside |
| 10 m/s | 0.05420 | 0.05914 | +0.00494 — outside |
| 14 m/s | 0.07468 | **0.07511** | +0.00043 — inside |

**At the scene's own wind the derivation returns the fit to 6.7%, inside the
1954 paper's own uncertainty.** So for this scene the fit is a *consequence* of
the wind and not an input, which is what the round was sent to establish.

**The disagreement has a shape and it is not noise.** The derived mss runs
*high*, and it runs highest at low wind. That is not this run's discovery:
Guérin et al. (Archimer/Ifremer 28378, read in this container) report the same
sign — *"the slick and clean mss predicted by Elfouhaily spectrum are larger
than those experimentally observed by Phillips and CM"* — and propose an
excavation of the decimetre range to remove it. **The term is named**: the
short-wave branch `B_h` carries `α_m = 0.01[1 + ln(u*/c_m)]`, which stays finite
as the wind drops instead of switching off. Logged `OPEN` in the suite, parked
with its mechanism, per ruling 11.

**The visible kink near 6.1 m/s is in the model, not in the sea.** `α_m` changes
branch at `u* = c_m`, i.e. `U₁₀ = 6.061 m/s`. This scene's 6 m/s sits 3% below
it. A wind sweep that steps across that value crosses a derivative
discontinuity in ECKV; a later wave reading the kink off this plot should not go
looking for it in the water.

## Right — why "the" mean square slope does not exist until a cut-off is named

`mss` is dominated by its high-wavenumber tail, so the integral has no value
until you say where it stops. **The stopping point is a property of the
instrument, not of the water** — and that is the scale-free statement the
owner's question was reaching for.

| upper cut-off | what sets it | mss at 6 m/s | share of total |
|---|---|---|---|
| 11 rad/m | L-band radar | 0.01876 | 52% |
| **20 rad/m** | **Cox & Munk's own artificial slick** | **0.02127** | **59%** |
| 95 rad/m | Ku band | 0.02615 | 73% |
| 250 rad/m | Ka band | 0.02985 | 83% |
| 370 rad/m | the capillary scale | 0.03170 | 88% |
| 3700 rad/m | everything | 0.03597 | 100% |

Cox & Munk's *slick* runs suppressed waves shorter than about 0.3 m — an upper
cut-off near 20 rad/m — so the paper's own two numbers are two different
integrals of one sea. Four instruments, four "the" mean square slopes, and none
of them wrong. **41% of the slope variance lives in waves shorter than 31 cm**,
which is the half a renderer is most likely to drop and least likely to notice
dropping.

*Provenance: **derived** (the spectrum) + **P** (the 1954 fit) + **P
(attribution)** (ECKV itself). Scene-linear SI throughout; nothing is read off a
PNG. Drawn by `terrain-renderer/reference-impl/wind_spectrum_figures.py:fig_mss_vs_cox_munk`
from `wind_spectrum.py`. ⚠️ **The ECKV 1997 paper is not held in this
container** — the equations are the intersection of four independent
restatements, listed in `wind_spectrum.py`'s header, and two transcription traps
found while cross-checking are fired as suite defects. The instrument cut-offs
are from Hwang & Fois, arXiv:2204.11591, read here. `?` carried by the input:
the frame's wind, 6 m/s, which is unobserved and marked `?` in the bar.*
