# The physics answer key — sea and surf. Frozen at authoring, read-only once the wave starts.

This is the **bar** for the `physics` dimension of `gauntlet/sea`. It is one file, and a critic
handed only this path must be able to score the artifact without asking anyone what "good" means.

Thirteen waves have scored physics on the builder's own assertion. The closed forms those waves
were measured against are real, external and unarguable — they were simply scattered across four
chapters and thirteen round records, so nothing could be opened and checked. This file collects,
checks and freezes them. **It invents no physics.** Every row is either cited to the literature or
marked `DERIVED` with the wave and the file that derived it, so a critic can tell "the literature
says" from "we showed".

## How to use it

Each row carries five things: **the claim, its source, the expected value, the tolerance, and how
to check it.** Score a row `PASS` / `FAIL` / `ERROR` / `N/A`:

- **PASS** — the check was run, the quantity was inside the tolerance, and the check was not
  structurally exempt from the defect it is aimed at (see [the tolerance rules](#the-tolerance-rules)).
- **FAIL** — the quantity is outside the tolerance. Report the value, not "fails".
- **ERROR** — the check could not be evaluated (the code path does not exist, the row threw, the
  quantity is unreachable in every frame). **ERROR is not PASS**, and a run containing one is
  INCOMPLETE rather than merely failing. Half the rows below have no implementation to check yet;
  those score ERROR, and that is the honest result.
- **N/A** — the row's precondition is not met by this artifact at all (e.g. no vessel, so no wake).
  N/A must name the precondition.

**Do not score the artifact's current values as the bar.** The key states what the physics
requires. If the implementation disagrees, that is a finding for a wave, not a reason to edit this
file. This file is frozen: corrections to it belong in a *new* dated block at the bottom, visible,
never by silent overwrite.

## The tolerance rules

Read `terrain-renderer/references/11-verification-failures.md` before disputing any tolerance
below. It runs to fourteen ways a verification lies, and eight of them decide tolerances:

1. **A tolerance is a claim about the instrument, so state the instrument's error.** Every
   tolerance below names where it comes from — a quadrature's own residual, a grid cell subtended
   at a range, a published uncertainty band, a Monte-Carlo standard error.
2. ⚠️ **Never size a tolerance from the disagreement it accommodates.** The thirteenth way: this
   project shipped a row whose justification string read *"the two disagree by 3e-5 and the
   tolerance is three of it"* at `1e-4`. It passes at 3e-5 and it passes at 9e-5, in the same tone.
   The tell is grep-able: any justification that mentions the *current* disagreement instead of an
   estimator or a standard.
3. **Count resolution, not rows.** For every quantity, the reviewable number is *the smallest error
   any row on it could detect* — the **minimum** over rows, not the count of them. Two guards both
   coarser than the effect are zero guards.
4. **At least one absolute row per quantity.** A suite made of ratios is blind to exactly the
   errors that are common factors (the tenth way: a ×50 defect passed a 53-row suite with the
   ratio row bit-identical to twelve figures). An order-of-magnitude bracket is the cheapest
   absolute row there is and it caught that fifty.
5. **No row at a degenerate argument or a fixed point.** Zero load, zero absorption, unit albedo,
   normal incidence, isotropic covariance: these are where a formula proves itself and therefore
   where a second copy of it is invisible. For every map the code can apply twice, put a guard
   strictly between its fixed points.
6. **The error must rise as the condition hardens.** A row that gets easier the harder the case is
   reporting its own window. Print the sample count beside every number.
7. **Two instruments agreeing establishes nothing until their sensitivities are compared** — print
   each path's smallest detectable difference in the underlying quantity before calling an
   agreement corroboration. See [§X](#x--cross-instrument-what-two-readings-of-one-wind-do-not-establish).
8. **Measure in the render target, before the tone map.** A ratio read off a PNG is a measurement
   of the grade. Any row on a radiometric quantity states which space it is in.

## Provenance tiers

Following `terrain-renderer/references/12b-water-provenance.md`:

| Tier | Meaning here |
|---|---|
| **P** | Published, and the *content* was checked. The row says where. |
| **P (attribution)** | Published and correctly attributed, but the paper was **not read in this container**. Cite the structure; do not claim the numbers were re-verified. |
| **D** | Measured or recomputed on `terrain-renderer/reference-impl/`, or standard docs. A measured `D` is a property of *that* scene — what transfers is the mechanism. |
| **DERIVED** | This run derived it rather than citing it. The row names the wave and the file. |
| **?** | Open. Not usable as a bar. Listed in [§OPEN](#open--what-this-key-could-not-source). |

---

## K · The wake of a moving hull

The one falsifiable geometric prediction with no free parameter that this run's wave-field lane has
been offered. Bar `bar.md` §M is the photographic side; this is the closed form.

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **K1** | Deep-water Kelvin wake envelope half-angle | `θ_K = asin(1/3) = 19.4712°` (19.47122063°) | **±0.3°** — one grid cell subtended at the measurement radius: `atan(dx/r)` = 0.29° at `dx = 1 m`, `r = 200 m`. Tighten with the grid; never widen to accommodate a reading. | Detect crest maxima in the wake field, fit the outer envelope over `r ∈ [100, 400] m`, take the half-angle from the fit. Print the number of crest points in the fit. | **P** — William Thomson (Kelvin), *On Ship Waves*, Proc. IMechE **38**, 409–434 (1887). Web-verified 2026-08 (`terrain-renderer/references/00-index.md`, index row and the verification note). Restated in `19-fluid-simulation.md`. |
| **K2** | That angle is **independent of speed**, because deep-water group velocity is half the phase velocity | half-angle constant across a `U` sweep | spread across the sweep **≤ K1's tolerance (0.3°)**, *and* not monotone in `U` | Sweep `U` over ≥ ×3 at fixed depth. Plot half-angle against `U`. A trend is a finding whatever the mean. | **P** — same. The `c_g = c/2` reason is in `19-fluid-simulation.md`. |
| **K3** | The angle must be an **output of the dispersion relation**, not a construction | — | structural, no numeric tolerance | Grep the wake path for a literal `19.47`, `1/3`, or a hard-coded envelope mask. A wedge stamped at the right angle scores **FAIL**, not PASS. Then run the *same* code at `Fr_h ≈ 0.9` (K5) and require it to widen. | Bar `bar.md` §M2, stated as a scoring rule at intake. |
| **K4** | Transverse-wave wavelength inside the wedge | `λ_t = 2πU²/g`; **64.05 m** at `U = 10 m/s`, `g = 9.81` | **±1 grid cell over N crests**, i.e. `dx/(N·λ_t)` relative. At `dx = 1 m` over 5 crests that is **0.3%**. | Sample the surface along the track centre-line behind the hull; FFT or peak-to-peak over ≥5 crests. Report N. | **P** — stationary phase on the deep-water dispersion relation `σ² = gk`; the transverse system is the `k = g/U²` stationary point. Standard; consistent with `19-fluid-simulation.md`. |
| **K5** | **Finite depth**: the pattern is governed by the depth Froude number `Fr_h = U/√(gh)`. As `Fr_h → 1⁻` the wedge **widens toward 90°**; the transverse system **vanishes at `Fr_h = 1`**; above 1 it narrows again | monotone widening on `Fr_h ∈ [0.7, 1)`; no transverse crests at `Fr_h = 1` | **sign and monotonicity only** at this tier. The half-angle at a given `Fr_h < 1` is a solve, not a constant, and no closed-form target is asserted here. | Fix `U`, sweep `h` so `Fr_h` runs 0.3 → 0.95. The half-angle must be flat at 19.47° over `Fr_h ≲ 0.7` and rise thereafter. **This is the severity-knob row of §K** — a half-angle that *falls* as `Fr_h` rises is the eleventh way, not a result. | **P (attribution)** — classical finite-depth ship-wave theory (Havelock 1908; Lighthill, *Waves in Fluids* §3.10). ⚠️ **Not re-verified in this container.** The run's own record carries only the qualitative form: `19-fluid-simulation.md` — "In shallow water, or above roughly Froude number 1, the pattern changes and narrows." |
| **K6** | Above `Fr_h = 1` the pattern is a single Mach-type wedge of half-angle `arcsin(1/Fr_h)`, with no transverse system | `arcsin(1/Fr_h)` | **not a bar row** — see [§OPEN](#open--what-this-key-could-not-source). Recorded so a critic knows the shape, not so a wave is scored on it. | — | **P (attribution)**, unverified here. |
| **K7** | ⚠️ **Deep-water validity condition.** 19.47° applies only where the wake's own waves are deep-water waves. Conventionally `Fr_h ≲ 0.7`. | — | — | Before scoring K1 at all, compute `Fr_h` for the scene and print it. **K1 scored at `Fr_h > 0.7` is not a physics finding, it is a category error.** | Bar `bar.md` §M2, which prices this for the reference photograph: a RIB at 10–15 m/s over 10–30 m of Algarve inshore water has `√(gh)` = 10–17 m/s, so `Fr_h` is plausibly near 1 and *that frame may not show a deep-water wake at all*. |

**What §K cannot cover.** Whether the wake *looks* like a wake — the feathering of the divergent
arms, the whiteness of the disturbed water, the way the two systems interleave. That is craft and
goes to `gauntlet/sea/bar/visual/` (blocked; see `bar-request.md`). The wake's **white** is not the
Kelvin wave field at all — it is entrained air, and its clock is §F, not §K.

---

## G · Sea-surface slope statistics and the glitter path

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **G1** | Cox & Munk total mean-square slope, clean sea | `mss = 0.003 + 5.12×10⁻³ U` (`U` in m/s) | the paper's own quoted uncertainties, **±0.004 on the intercept and ±0.002 on the slope coefficient** | Evaluate at 3 / 6 / 10 / 16 m/s and compare with the shipped slope variance. Absolute row, not a ratio. | **P** — Cox & Munk, *Measurement of the Roughness of the Sea Surface from Photographs of the Sun's Glitter*, JOSA **44**(11), 838–850 (1954). Verified 2026-08 against the paper (`12b-water-provenance.md`). |
| **G2** | ⚠️ **The wind is referenced at 12.5 m and the fit is calibrated only over 1–14 m/s.** | — | — | A row evaluating G1 at `U₁₀` without conversion, or at storm winds, is out of the fit's domain. State which reference height the artifact uses. | **P** — same paper; the domain limits are stated in `12b-water-provenance.md`. |
| **G3** | The **components** are per-axis variances: `σ_c² = 0.003 + 1.92×10⁻³ U` (crosswind), `σ_u² = 3.16×10⁻³ U` (up/downwind) | at `U = 6`: `σ_c² = 0.01452`, `σ_u² = 0.01896`, sum `mss = 0.03348` | exact arithmetic on the published coefficients; **1e-12** | Evaluate both and their sum. | **P** — same paper, restated in `12-water-rendering.md`. |
| **G4** | ⚠️ **Cox & Munk's own two fits do not agree, and neither implies the other.** The components sum to `0.003 + 5.08×10⁻³ U`; the separately fitted combined slope is `0.003 + 5.12×10⁻³ U` | **0.8% apart at any wind** | inside the paper's own quoted uncertainties (G1) | Carry the components against **their own sum**, and the total against **the published fit**, as two rows. A file that checks one against the other has misread the source. | **P** + **DERIVED** (wave 4, `reference-impl/README-beach.md` §F4). |
| **G5** | The slope distribution is **anisotropic** | `σ_u²/σ_c²` averages ≈ **1.34**, range 1.0–1.8 | the published range is the tolerance: **1.0–1.8** | Compare the shipped ratio at the scene's wind. An isotropic slope pdf scores FAIL. | **P** — same paper, restated `12-water-rendering.md`. |
| **G6** | ⚠️ **Name the variance convention once, upstream.** Per-axis variance and total `mss` differ by a factor that both expressions divide by | — | — | One named function returning one convention, called by every consumer. A comment at each call site is not the fix. In one slope budget in this project two of five bands normalised per-axis and three in the total, and it shipped for months. | `11-verification-failures.md`, third of the seven. |
| **G7** | **The glitter path's width is a readout of the wind**: `width ∝ √mss` | log-log regression of width on `mss` across ≥4 winds spanning ×5 gives an exponent of **0.500** | **±0.02** on the exponent — ≈2× the estimator floor, which is `2×0.01/ln(5.3) = 0.009` for a 1% width repeatability over that lever arm. **Not** sized from any observed residual. | Measure the width at `U` = 3 / 6 / 10 / 16 m/s at fixed sun and view, regress, report the exponent and the four widths. | **P** for the `√mss` law (G1). **DERIVED** for the measurement, wave 4: `reference-impl/beach_optics.py:glitter_width_deg`, reported in `README-beach.md` §F2. |
| **G8** | The run's own measured invariance: `width/√mss` = **53.53 / 53.52 / 53.75 / 54.43** deg per unit rms slope at `U` = 3 / 6 / 10 / 16 — **constant to 1.7% over ×5 in wind** | those four numbers, at that sun (21.02°) and that view | reproduce to **±0.5%** if re-measured at the same geometry; otherwise the row is the *mechanism*, not the numbers | Re-run `glitter_width_deg` at the four winds. ⚠️ **The 1.7% is the result, never the tolerance for G7.** A Gaussian slope pdf *without* Cox & Munk's skewness and peakedness corrections returns an exponent of **0.511** on these four points; that 0.011 excess is the pdf, and it must be attributed rather than absorbed. | **DERIVED** (wave 4), priced in `12b-water-provenance.md` as a property of *that* sun and *that* wind (6 m/s, itself `?`). |
| **G9** | The path **narrows and brightens toward the horizon** | from a 25° view elevation down to the horizon: width narrows **2.26×** (14.96° → 6.63° in azimuth) and peak radiance rises **14×** (13.6 → 193.4, green, scene-linear) | **sign and monotonicity are the bar**; the two factors reproduce to ±2% only at that sun and wind | Sweep view elevation 25° → 0.2°. Width must be monotone decreasing, peak radiance monotone increasing, with no non-monotone step. A path of uniform width is the default and is wrong. | **DERIVED** (wave 4, `README-beach.md` §F2). Bar `bar.md` §K predicted the *sign* from geometry alone before the measurement. |
| **G10** | A single-bounce glitter model **loses the light that reflects below the horizon** | **10.3%** of intercepted flux at that sun and wind | the two integrals (radiance over the upward hemisphere; `ρ_F(ω)cos ω·p/cos β` over slope space) agree to **7×10⁻⁵ relative** — that agreement is the instrument's resolution and hence the tolerance floor | Integrate both ways; the second restricted to facets whose mirror direction points **up**. The difference is the loss. | **P** for the Cox–Munk construction; **D** for the figures, `12b-water-provenance.md`. |
| **G11** | Whitecap coverage law | Monahan & O'Muircheartaigh (1980) `W = 3.84×10⁻⁶ U^3.41` | ⚠️ **a factor of 3** — the literature's own spread, not sloppiness. The same paper's optimal fit is `2.95×10⁻⁶ U^3.52`; Callaghan et al. (2008, GRL 35, L23609) is not a power law at all but piecewise with an onset at `U₁₀ = 3.70 m/s`. From the exponent spread alone one coverage maps to **5.67–7.66 m/s**. | Never use coverage as a wind instrument to better than that band. See §X. | **P** for the laws; **D** for the band, recomputed in `11-verification-failures.md` (fourteenth way) on `reference-impl/beach_foam.py`. |
| **G12** | **The level is checkable even though the law is not.** At `U₁₀ = 6 m/s` the coverage is **0.173%** of the sea surface | 0.173% | order-of-magnitude: coverage must be **< 1%** at any wind the glitter path reports below ~9 m/s | Count foam fraction in the open-water region of the scene-linear buffer, excluding the surf zone. **A render with conspicuous open-water foam has a different wind from the one its glitter path reports** — and unlike an agreement, that check can fail. | **D**, `11-verification-failures.md` fourteenth way; `README-beach.md` §W6. |
| **G13** | Capillary–gravity minimum phase speed | `c_min = (4gσ/ρ)^(1/4)` = **0.2312 m/s** at `σ = 0.0728 N/m`, at `λ_min = 2π√(σ/ρg)` = **1.712 cm** | closed form; **1e-6** relative on the arithmetic once `σ` is declared | Evaluate both from the *same* declared `σ`. `reference-impl/wake.py` uses `SIG = 0.0728` and `C_MIN = 0.231`. | **P** (classical); verified against standard references per `00-index.md`. ⚠️ **See [ERRATA](#errata--found-while-mining-reported-not-fixed) — the chapter's quoted pair is not consistent at one `σ`.** |

**What §G cannot cover.** Whether the glitter reads as *separated glints with dark water between
them* rather than as the ensemble mean of the distribution. That is a sampling-and-craft judgement
— the wave-11 optics verdict measured it as an interior sd of 1.0–2.6 grey levels across a path
clipping at 255, which is a *symptom* a critic can measure, but "does it look like sun on water"
is not scorable here. Goes to the visual bar.

---

## B · Wave transformation on a beach

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **B1** | **Green's law**: shoaling amplitude goes as `H ∝ h^(−1/4)` — the `kd → 0` asymptote of energy-flux conservation | exponent **−0.2500** in the shallow limit | **±0.003**, which is the model's own `O((kd)²)` truncation at the measurement point: at `kd = 0.05`, `(kd)² = 2.5×10⁻³`. Sized from the physics' neglected term, never from a residual. | Push a long wave onto a gentle ramp until `kd < 0.05`; regress `log H` on `log h`. Print `kd` with the exponent. | **P** — classical (Green 1838), stated in `12-glacial-coastal.md` and measured in `README-beach.md`. |
| **B2** | ⚠️ **B1 is conditional on `kd`, and the condition is the whole row.** | at `kd ≈ 0.3` the correct exponent is ≈ **−0.207**, not −0.25 | — | Any row asserting −0.25 at `kd = 0.3` is testing the wrong thing. The run measured −0.2497 (with `H·d^(1/4)` constant to 0.1%) at `kd < 0.05` and −0.207 at `kd ≈ 0.3`; **the second is the `O((kd)²)` term, not an error.** | **DERIVED** (wave 1, `README-beach.md`, `s1-shoaling-green.png`). |
| **B3** | **Snell for water waves**: `sin θ / c` is invariant along a ray as `c` varies with depth; crests turn onto the depth contours | invariant | on a **grid-aligned** bed a column march returns it to float64 noise (`5.5×10⁻¹⁸` spread) — that row is an **identity and no test at all** | Score B4 instead. Keep B3 only as a smoke row and label it as such. | **P** — classical. Measured `sin θ/c = 2.4348×10⁻²`, `θ` 20° offshore → 6.5° at the break (`README-beach.md`). |
| **B4** | The **real** refraction row: a plane beach whose depth contours run at **10° / 20° / 30°** to the grid, with the marching integrator never told the rotation | angular error against rotated-normal Snell | **0.5°**, justified as the march's own first-order truncation on that grid — *and the row must print its sample count* | The measurement window must be centred on the alongshore row that samples the ramp **most fully**, not on the grid centre. ⚠️ **The eleventh way, committed here:** a centre-pinned window reads 0.186 / 0.059 / **0.030°** and *passes the same 0.5° tolerance* while the truth is 0.186 / 0.310 / 0.277° — because at 30° the centre row contains **zero** ramp cells. **A row that gets easier as the rotation grows is reporting its window.** | **DERIVED** (`reference-impl/validate_beach.py`; both columns recomputed in `11-verification-failures.md`, eleventh way). |
| **B5** | An independent refraction check that shares no Snell with the march: a 2-D ray tracer | reproduces Snell's angle to **1.3×10⁻³ rad** over 400 m; rays **converge on a bar and spread over a rip channel** | that 1.3e-3 rad is the tracer's own integration error and is the resolution floor for this pair | Two methods that read the same premise are one method. The tracer has no Snell in it, which is what makes the agreement evidence. | **DERIVED** (wave 1, `s1-refraction-rays.png`). |
| **B6** | **The breaker index**: waves break near `H/h = γ ≈ 0.78` | 0.78 | ⚠️ **the tolerance is not "±0.1 because the literature spans that".** The checkable assertion is the artifact's **internal consistency**: one constant, defined once, doing both jobs (breaking the wave in the transform *and* predicting the crest depth), reproducing itself at the interpolated crossing to the **crossing's own interpolation error**, ≈0.3% on a 1 m grid. | Measure `H/d` at the interpolated crossing and compare with the declared constant. Measured here: **0.7796** against a declared `GAMMA_B`. Corroborated by a third document that knew neither chapter — REF/DIF 1 v3.0 §2.3.5, "a breaking index relation (H > 0.78 h)". | **P** — McCowan lineage; Battjes, *Surf Similarity*, Proc. 14th Coastal Engineering Conference, Copenhagen, 466–480 (1974). Index row in `00-index.md`. |
| **B7** | ⚠️ **`γ` is where breaking STARTS, not what a surf zone SITS at.** The saturated ratio is slope-dependent | `Γ_eq = γ_s/√(1 + (5/2)(dd/dx)/K)` — **0.477** on that beach's inner slope | against a **field range of 0.2–1.0** correlated with local slope (Raubenheimer, Guza & Elgar 1996, JGR 101, 25589) | Do not let a reader infer a second constant a surf zone relaxes to. `γ_s = 0.40` is the **flat-bed limit of a family**, not the `H/d` of any real surf zone. Companion: `tan β_crit = 2K/5`, the slope above which no saturated state exists. | **DERIVED** (wave 2, `reference-impl/beach.py:saturated_ratio`, three lines of algebra printed above the function). Model cited to Dally, Dean & Dalrymple (1985), JGR **90**(C6), 11917. |
| **B8** | **Battjes & Janssen (1978) `Q_b`** — the clipped-Rayleigh fraction of breaking crests | `Q_b` on the scene's own `H_rms` and depth-limited `H_max` | — | Compute on the scene's own field, not on a nominal one. `reference-impl/beach.py:breaking_fraction_bj` has done so since wave 2. | **P** — Battjes & Janssen (1978), cited in `README-beach.md` as read this run. |
| **B9** | The foam mass driven by `Q_b` has a **closed-form phase mean** | `m(a) = Q_b·exp(−a/τ)/(1 − exp(−T/τ))`, phase-mean **exactly `Q_b·τ/T`** — the steady state of `dW/dt = S − W/τ` with `S = Q_b/T` | **1e-8**, the closed form's own float agreement. Not an accommodation of anything. | Integrate the shipped foam accumulator over one phase and compare with `Q_b τ/T`. | **DERIVED** (`README-beach.md` §W-block; `k` **is** `τ/T`). |
| **B10** | **Dean's equilibrium profile** | `h = A·x^(2/3)` | exponent **2/3 ± 0.005**, from the log-log fit's own residual over the ramp span | Fit `log h` on `log x` over the far-field ramp only. | **P** — Dean, R.G. (1991), *Equilibrium beach profiles: characteristics and applications*, J. Coastal Research **7**(1), 53–84. Index row in `terrain-architect/references/00-index.md`; chapter statement in `12-glacial-coastal.md`. |
| **B11** | ⚠️ **The "cross-shore distance" in Dean's profile is a distance to the shoreline CURVE, not an offset along a grid axis.** `d = A(x_s(y) − x)^(2/3)` generates the *translates* of the shoreline; `d = A·dist(P, shore)^(2/3)` generates its *normal offsets*. They coincide **iff** the shore is parallel to the grid axis (`φ_s ≡ 0`) | first-order mismatch `Δθ = −(dφ_s/dy)·s·sin φ_s` | on the reference embayment: **0.397°** axis-keyed against **0.0008°** normal-keyed at the 2 m contour, and **5.4%** of spurious contour crowding. Those are that scene's; the **mechanism** is the bar. | Rotate the grid under a fixed shoreline. An axis-keyed bathymetry changes; a normal-keyed one does not. | **DERIVED** (wave 10, `12a-water-derivations.md` §11, `12b-water-provenance.md`, `s10-bathy-contours.png`). Eight waves of surf work could not see it because every earlier scene had `φ_s ≡ 0`. |
| **B12** | ⚠️ **The Dean profile has no shoreline slope.** `dh/dx = (2/3)A x^(−1/3) → ∞` as `x → 0`, so the beach *face* angle is not set by Dean and must come from somewhere else | — | — | An implementation that reads a face slope off the equilibrium profile has read a singularity. What fixes the angle is where the equilibrium profile stops answering. | **DERIVED** (`README-beach.md`). |
| **B13** | **Longshore thrust**, radiation-stress form | `(E₀/4)·sin 2θ₀` in **deep-water** quantities; `(E_b/2)·sin 2θ_b` in **breaking-zone** quantities | the two forms measured on one field must agree to **`1/n_b − 1`**, where `n_b = c_g/c` at breaking — **3.7% at `n_b = 0.964`**. The residual is *predicted*, not tolerated: it is the shallow-water limit not quite being reached. | Compute both on the same field and compare against `1/n_b − 1`, printing `n_b`. ⚠️ **Pairing the quarter with breaking-zone values is wrong by exactly two.** | **P** — Longuet-Higgins, M.S. (1970), *Longshore currents generated by obliquely incident sea waves*, parts 1 & 2, JGR **75**(33), 6778–6789 & 6790–6801. The factor-of-two warning is in `terrain-architect/references/99-papers.md` and `12-glacial-coastal.md`; the measurement is `README-beach.md`. |
| **B14** | The longshore-current coefficient | **`5π/16 = 0.9817`** | closed form; the numerical solve must land on it, and `π/4 = 0.7854` is **incomplete by 25%** — 1.25 is not a tolerance anyone may widen to | Deriving from the depth gradient of `S_yx` alone gives `π/4`. The missing term is `d(sinθ cosθ)/dx`: in shallow water Snell makes `sin θ ∝ √d`, so alongshore refraction contributes exactly a quarter of the depth term with the same sign, and `(π/4)(5/4) = 5π/16`. | **DERIVED** (wave 1, `README-beach.md`) — *and it is the Longuet-Higgins (1970) coefficient, reached by a test that failed at it rather than by citation.* ⚠️ Chapter 12 carries **no** coefficient (it writes `V_long ∝ …` and stops), so this is an **addition**, not a correction — a `rounds.jsonl` line that filed it under `overturned` was itself corrected in `README-beach.md`. |
| **B15** | ⚠️ **The Iribarren thresholds come in two conventions.** `ξ < 0.5 / 0.5–3.3 / > 3.3` and `ξ < 0.4 / 0.4–2 / > 2` are both attributed to Battjes (1974) and are **not** in conflict — the first is in deep-water quantities, the second in local ones | — | — | A breaker-class function must take an argument naming which convention it answered in. `reference-impl/beach.py:breaker_class` does. | **P** + **DERIVED** (`README-beach.md`). |
| **B16** | **Hunt (1959) run-up** | `R ∼ H·ξ`, `ξ = tanβ/√(H/L₀)`, valid `0.1 < ξ < 2.3` | the validity range is checkable; **the constant of proportionality is `?`** — see [§OPEN](#open--what-this-key-could-not-source) | Check `ξ₀` and `ξ_b` fall inside Hunt's stated range (measured 0.332 and 0.300). Do **not** score a run-up magnitude against this row. | **P** for the scaling and range (Coastal Wiki, *Surf similarity parameter*, read this run). Coefficient open. |
| **B17** | The undertow, dimensionally | `u_u = E_w/(ρ c d)`, from the wave's own mass flux `M = E/c` returned below trough level over depth `d` | dimensions pushed through the **shipped** function must give m/s — and **m/s² when `D_w` is substituted for `E_w`**, which is the standing trap | An algebraic unit check through the shipped path, not by inspection. | **DERIVED** (wave 1, `README-beach.md`); the `E_w` vs `D_w` trap is named in `12-glacial-coastal.md`. |

**What §B cannot cover.** Whether the surf *reads* as surf: the shape of a plunging lip, the
texture of a bore front, whether the foam looks like foam. `bar.md` §§B, E, H5, I hold the
photographic criteria for those and they are not numeric. Also uncovered: whether the breaking is a
**prediction** rather than a mask — B6 checks that one constant does both jobs, which is necessary
and not sufficient; a visual critic still has to confirm the foam line sits where the depth field
puts it.

---

## D · Diffraction — Sommerfeld's half-plane

The half-plane solution is the only closed form in this bar with an **exact** value at a named
point, which makes it the strongest row here and the one a critic should run first.

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **D1** | On the geometric shadow boundary the diffraction coefficient is **exactly one half** | `K_d(0) = 0.500000` | **1e-9** — the cross-route agreement of the Fresnel-integral evaluators (power series / Gauss–Legendre / asymptotic agree to 1e-12 and 1e-9 in their overlaps). ⚠️ **This is not an asymptotic result and the tolerance must not be loosened as if it were:** `X = 0` on the boundary and `F(0) = 0`, so the half is exact **at every `kr`**. | Evaluate the shipped diffraction field on the shadow boundary at ≥3 values of `kr` spanning a decade and require 0.5 at each. A row at one `kr` cannot distinguish an exact half from an asymptotic one. | **P (attribution)** — Sommerfeld (1896); Penney & Price (1952) for the water-wave rigid-screen (`s = +1`, Neumann) application. ⚠️ **Neither paper is held in this container and neither was re-verified.** The numbers are **D**, `reference-impl/beach_diffract.py`. |
| **D2** | The half is a half because of the **Cornu spiral's limits** | `C(±∞) = S(±∞) = ±½`; the bracket `(1+i)/2 + C(X) + iS(X)` becomes `(1+i)/2` at `X = 0` and `(1+i)` as `X → +∞` | analytic; the evaluator's 1e-12 | Check all three limits of `U`, not just the middle one: plane wave as `cos(ψ/2) → +∞`, exactly one half at 0, switched off as `→ −∞`. | **P** (classical Fresnel integrals) + **DERIVED** (`12a-water-derivations.md` §12, built here from three routes because there is no scipy in this container). |
| **D3** | The incident term contributes **exactly 0.5** on the boundary — no asymptotics enter | 0.5 | 1e-12 | Same as D2's middle line. | **DERIVED**, `12a` §12. |
| **D4** | `K_d` off the boundary | **0.30783 / 0.20267 / 0.11103** at `v` = 0.5 / 1 / 2 | reproduce to **1e-4** (the chapter's own tabulation is 0.31 / 0.20 / 0.11, i.e. two digits — the four-digit values are the bar) | Evaluate the field at the three offsets. Absolute row, not a ratio. | **D** — `beach_diffract.py`, `12b-water-provenance.md`. |
| **D5** | The coastal-engineering chart parameter is the same variable: `v = b√(2/(λr)) = −X` | identity | analytic | Expand `X` about the boundary with `ψ = π + ε`, `b = rε`. An implementation carrying both variables without the identity will disagree by a sign somewhere. | **DERIVED**, `12a` §12. |
| **D6** | ⚠️ **The reflected term's argument must be `2π − φ − φ₀`, not `φ + φ₀`.** Both give the same reflected plane wave (`cos` is even) but they **switch it on in different regions** | with the wrong argument the field reads `K_d = 1.106` on the shadow boundary | **D1 is the guard** — this is what D1 is *for* | This is the cheapest deliberate defect in the whole key: swap the argument, and D1 must fail. `reference-impl` shipped `φ + φ₀` first, and **it drew a convincing lee**. A picture cannot catch this; D1 can. | **DERIVED**, `12a` §12 (fixed by requiring the physical switch-on regions, then verified — not transcribed). |
| **D7** | Structural guards on the diffracted field | `(K_d − ½)·√(kr)` constant to **0.005** near the boundary; Helmholtz residual **1.4×10⁻⁶** falling as `h⁴`; energy gain in the shadow **0.98** of the lit side's deficit; deep-shadow wavenumber direction radial to **0.10°** with `\|k\|/k = 1.0007` | as listed | the `h⁴` falloff is the tolerance's justification: refine the grid and the residual must fall as the fourth power, which no accommodation can fake | Grid-refine and check the **rate**, not the value. | **D** — `beach_diffract.py`, `12b-water-provenance.md`. |
| **D8** | ⚠️ **Two conventions hide under "the lee table".** A coherent sum of two half-plane edge fields, `2·K_d((W/2)√(2/(λr)))`, gives **0.51** where a Fresnel–Kirchhoff aperture integral on the same geometry gives **0.431** | — | — | Name which one the artifact computes before comparing it with any published lee chart. | **D**, newly stated in `12b-water-provenance.md` (it was not in the chapter's words). |
| **D9** | ⚠️ **Diffraction is not refraction, and nothing in a ray description contains any of it.** | — | — | Blurring the depth field, widening a filter, or adding directional spread does **not** produce diffraction. A lee that appears only when the bathymetry is smoothed is not a diffraction result. | **P/D** — `12-water-rendering.md`, "Diffraction is not refraction"; bar `bar.md` restates it. |
| **D10** | The **direction** of the diffracted field is a theorem, not an ansatz | `k_vec = grad(arg u) = Im(grad u / u)`; radial from the tip to **0.10°** deep in the shadow, incident direction to **0.02°** far in the lit region, and **neither near the boundary, where it rings** | as listed | Compute on the complex field, never on `arg u` (which wraps by 2π). A *stated* radial fan has no shadow boundary, applies the fan in the lit region too, and is radial at the shoreline station rather than at the point — worth **11.4° rms** across the offshore boundary. | **DERIVED**, `12a` §12. |

**What §D cannot cover.** Whether a lee *looks* sheltered. Also uncovered by construction:
combined refraction–diffraction (the run applies the edge at the offshore boundary and refracts it
in, which is defensible for a tip 773 m seaward and is **not** a mild-slope solve — a scene with an
obstacle *inside* the domain needs one and this run does not have it).

---

## S · Directional spreading

⚠️ **This section is the weakest in the key, and it is weak in a stated way.** The wave-field lane
has reached wave 13 without ever implementing a directional spectrum — `workbench.md` rows 12.2 and
13.3 both record it as unreached — and the primary sources are not held in this container. The
rows below are therefore **P (attribution)** and the parameterisation is **open**. Nothing here may
be scored as though it were verified physics.

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **S1** | The standard directional spreading function is `D(θ) ∝ cos^(2s)((θ − θ̄)/2)` | that functional form | **structural, not numeric** | Check the artifact's angular energy distribution has this shape, not a top-hat and not a delta. | **P (attribution)** — Longuet-Higgins, Cartwright & Smith (1963), in *Ocean Wave Spectra* (Prentice-Hall), 111–136. ⚠️ **Not read here.** |
| **S2** | It normalises to unity over the circle | `D(θ) = [2^(2s−1)/π]·[Γ(s+1)²/Γ(2s+1)]·cos^(2s)((θ−θ̄)/2)`, `∫D dθ = 1` | **1e-6** by quadrature — this is a mathematical identity in `s` and needs no citation | Integrate the shipped `D` over 2π at ≥3 values of `s`. A normalisation checked at one `s` is a degenerate row. | **P (attribution)** for the form; the normalisation is arithmetic. |
| **S3** | `s` is frequency-dependent, peaking at the spectral peak | Mitsuyasu et al. (1975): `s_p ≈ 11.5 (U/c_p)^(−2.5)`; Hasselmann et al. (1980): `s_p ≈ 9.77` with a JONSWAP-based frequency dependence | **NOT A BAR ROW** — see [§OPEN](#open--what-this-key-could-not-source) | — | **?** — attribution only, neither paper read, no figure in this run's record. |
| **S4** | **The consequence that IS checkable today**, and it is what thirteen waves have been failing | a unidirectional field has **zero** alongshore variance; a spread field has finite alongshore correlation length | the wave-11/12 critics' own measurement is the instrument: alongshore residual **5.2 DN** against **31.7 DN** across the crests, a **ratio of 0.16** — "corrugated roofing". The bar is that the ratio must be **an output of `s`**, not near zero. | Measure the alongshore and cross-shore residual of the surface in the scene-linear buffer, in the same region, and report the ratio with the sample count. A 1-D profile extruded alongshore returns ≈0 by construction and scores FAIL. ⚠️ **No threshold on the ratio is asserted here** — the closed-form map from `s` to that ratio is open, so this row establishes *presence*, not *magnitude*. | **DERIVED** (the measurement, wave 12 critic, `workbench.md` row 12.2). |

**What §S cannot cover.** Almost everything quantitative. It cannot say what `s` should be for a
given sea state, so it cannot fail a field that is short-crested by the *wrong amount*. That is the
largest single hole in this key and it is named rather than papered over.

---

## I · The air/water interface

The most thoroughly derived block in the run, and the one carrying the most traps.

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **I1** | **Walsh's relation** ties the two diffuse Fresnel constants across the boundary | `n²(1 − R_int) = 1 − R_ext` | **1e-9**. It holds to **6×10⁻¹¹** on independent quadratures — float64 noise, not agreement to a tolerance. | Compute `R_ext` and `R_int` from **different index pairs** and close the identity. ⚠️ **It pins the exponent, not merely the presence of a factor**: at `n¹` the two sides part by 25%, at `n³` by 33%. This is the guard that catches a missing `1/n²`, because it is the one row that **crosses** the boundary rather than taking a ratio on one side of it. | **P** for the identity (standard optics: `L/n²` invariance plus Fresnel reciprocity), **D** for the closure. ⚠️ **The name is `?`** — widely attached to J.W.T. Walsh, *The reflection factor of a polished glass surface for diffused light* (1926), a paper **not read in this container**. `12b-water-provenance.md` marks it. |
| **I2** | External diffuse reflectance — the **loss** on light arriving from the air | `R_ext = 6.669%` at `n = 1.3348`; across the IOR triple 1.3320 / 1.3348 / 1.3400 it is **6.6248 / 6.6690 / 6.7511 %** | quadrature residual **1.8×10⁻⁷** (a 512-point midpoint rule over the air-side cosine, against 4 000 000 nodes) | `R_ext = ∫₀¹ 2μ R(μ; air→water) dμ`. Absolute row. | **D** — 2000-node Gauss–Legendre, `12a-water-derivations.md` §7 and `12b`. |
| **I3** | Internal diffuse reflectance — the **trap** on light arriving from the water | `R_int = 47.617%` at `n = 1.3348` (**47.3712 / 47.6166 / 48.0681 %** across the triple); ratio `R_int/R_ext` = **7.140** (7.151 / 7.140 / 7.120) | see I5 for the quadrature's own tolerance | Same integral, indices swapped. ⚠️ **One interface carries two diffuse constants and nothing in a shader's spelling tells them apart.** A reader who takes the wrong one is out by **7.14×** in the direction that darkens a water interior. | **D** — same. `12-water-rendering.md` disambiguates the two senses in place after using one word for both for its whole run. |
| **I4** | `R_int` **decomposes exactly**, and the larger piece is not Fresnel | `R_int = (1 − 1/n²) + ∫_{μ_c}^1 2μ R(μ) dμ` = **43.8735% + 3.7431% = 47.6166%** at `n = 1.3348`. **92.1%** of the internal return is the mirror outside Snell's window; 7.9% is partial Fresnel inside the cone | **1e-6** on the sum; the geometric term `1 − 1/n²` is closed-form and exact | Compute the two pieces separately and require them to sum to the quadrature. | **D** — `12a` §7. |
| **I5** | ⚠️ **The internal integrand has a KINK at `μ_c` and the quadrature must be split there.** `R_int(μ)` is identically 1 below `μ_c` | split at `cos θ_c`, **400 nodes a side** → **8 digits** (2.3–3.9e-9) | ⚠️ **A single un-split 2000-node Gauss–Legendre rule is off by 3e-5** and a `1e-4` tolerance on it is the thirteenth way. The air-side rule's own error is 1.8e-7 — *that* is the resolution the row should be set at. | Substituting a smooth reflectance for `R_int` and changing nothing else returns the un-split 125-node rule to **6.7×10⁻¹⁵**, which is the control that attributes the error to the kink and not to the `exp(−τ/μ)` endpoint. ⚠️ **A convergence study does not catch this** — the single rule's error shrinks *and changes sign* almost every refinement (+6.4e-4 → −3.0e-4 → +1.0e-4 → −6.2e-5 → +1.5e-5 → +5.2e-6 over N = 250…8000). **Compare against a rule with a different structure, not a finer version of the same rule.** | **DERIVED**, `11-verification-failures.md` thirteenth way, recomputed on `reference-impl/optics.py`. |
| **I6** | **Critical angle / Snell's window** | `θ_c = asin(1/n)`: **48.519°** at `n = 1.3348`, **48.607°** at `n = 1.333` | closed form, 1e-6 | ⚠️ **The chapters quote both 48.5° and 48.6°, and both are right for their own `n`.** A critic who reads them as a discrepancy has found a rounding convention, not a defect. Any row must state which `n`. | **P** (Snell) + **D** for the values, `12a` §7 table. |
| **I7** | ⚠️ **`1 − 1/n²` is a REFLECTANCE, not a backscatter fraction.** | a traced bubble returns `b_b/b` = **0.0230** (0.0228 / 0.0230 / 0.0235 across the IOR triple) and `g` = **0.688** (0.691 / 0.688 / 0.684) — **twenty times smaller** than the 43.874% reflectance | the ray trace closes to `1 ± 8×10⁻⁷` by construction *and checked*; a second, independent quadrature returns `R_int` to six digits from code it shares nothing with | Reading 43.874% as `b_b/b` in a volumetric foam model is the `foam-backscatter-is-tir` defect; it fires **4 rows** in the beach suite. A bubble is a **side** scatterer. | **P/D** — `12b-water-provenance.md`, `reference-impl/beach_foam.py:bubble_scatter`; `12-water-rendering.md`. |
| **I8** | **Radiance is not conserved across the interface — `L/n²` is the invariant, `L` is not** | dropping the divisor on light *leaving* the water is **1.78×** | the lossless-white-pool audit reads **1.73** instead of 1 without it | ⚠️ **Every ratio row is blind to this**, because `n²` cancels in a ratio: reflectance is a ratio, transmittance is a ratio, the s/p ordering is a ratio. This project's water suite covered exact Fresnel about as thoroughly as a suite can — normal incidence, grazing, Brewster's zero, the critical angle from two directions — and **not one row could see it**, for the project's whole run. The guards that see it are I1 (an identity written *across* the interface) and a closed end-to-end energy audit whose right-hand side is the number 1. | **P** — Preisendorfer / standard radiometry; the `L/n²` invariance verified 2026-08 against the 1963 source cited in `12b`. **D** for the 1.78 and 1.73. |
| **I9** | ⚠️ **Put the interface side in the parameter's name.** `a_wet(a)` maps a **water-side** substrate reflectance to the air-side apparent albedo; `rho_water(rho_bed, …)` crosses the interface twice inside itself, so *its* `rho_bed` is water-side too | composing `a_wet` inside `rho_water` applies the interface twice — worth up to **35%** | ⚠️ **No tolerance reaches it at the arguments every guard was written at.** `a_wet(1) = 1` and `a_wet(0) − R_ext = 0` **exactly** — 0 and 1 are the map's **fixed points**, and 0 and 1 are where every energy guard in the project was written. At `rho_bed = 1` the two chains agree to **twelve significant figures**; at 0.45 they differ by **1.350×**. | Put **one** guard at an interior albedo — 0.15, 0.45, 0.9 — and it catches this in any of nine waves. None was written. The row that finally settled it is the **identity between the two forms** on the interior: `a_wet(a) − R_ext == (1−R_ext)·a·T_esc(0)/(1 − a·G_rt(0))`, which states in code which side of the interface each argument lives on. | **DERIVED**, `11-verification-failures.md` tenth way, fourth shape; recomputed on `reference-impl/optics.py`. |
| **I10** | The Snell-window escape geometry | a submerged source can leave only through a disc of half-angle `θ_c` about the vertical; outside it, reflectance is **exactly 1** | exact | A renderer treating the surface as a *partial* reflector from below spills light onto the deck that physics forbids. | **P** (Snell/Fresnel) + **D**, `gauntlet/bar/photo-spec.md` §L, which is the frame that inverts the illuminant and puts this asymmetry on the outside of the picture. |
| **I11** | ⚠️ **Reachability of a tilt is not reachability of a position.** A meniscus sweeps every surface tilt 0→90°, so any condition stated on the *normal* is met somewhere in it by construction — but a term can be reached in angle and identically zero in transport | writing the refracted direction as `t = ηi + fn`, `f = η cos_i − cos_t` is **negative for every incidence** whenever `η < 1`, so a camera above the water sends `t_z < 0` identically: the ray descends and can never arrive at a surface above it | — | Separate the two questions **before** building: *does the geometry admit the configuration* is about normals; *does a path from source to sensor pass through it* is about positions and is answered by tracing, not by sweeping. | **DERIVED**, `11-verification-failures.md` fifth of the seven. |

**What §I cannot cover.** Whether the water *colour* is right. `bar.md` §A holds that criterion and
it is photographic; and `11-verification-failures.md`'s seventh way establishes that a phone frame
is a reference and not a colorimeter, so even the photographic side yields ratios and a sign, not a
number. Absolute exposure is uncheckable here in both directions.

---

## F · Foam, bubbles and their clocks

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **F1** | Surface foam-raft decay time, **salt water** | **τ = 3.85 s** | published constant; check the artifact's decay e-folding against it to the fit's own precision. ⚠️ **Fresh water decays faster** — a row that does not say which is checking neither. | Fit an exponential to whitecap area after a break; report the e-folding and the fit's `R²`. | **P** — Monahan & Zietlow (1969). Recorded as PUBLISHED in `README-beach.md` §W7. |
| **F2** | **There are three clocks and no two share a source** | surface raft **3.85 s** (P), the plume's entrained **air 0.81 s** (DERIVED — `⟨τ⟩_vol` with Schiller & Naumann drag, size-resolved), the **suspension 143 s** (DERIVED — `d/w_s` with Soulsby, at that bay's 6.07 m median) | each against its own source; the **separation** is the claim | That no two share a source is what makes the separation an argument rather than an assertion. ⚠️ **A single rise speed at the Sauter radius gives `τ_air = 15.7 s` and inverts the ordering** — the size-resolved steady state gives 0.81 s and the bar's ordering survives. Recorded because the claim survived a serious attempt to break it. | **P** + **DERIVED** (wave 6, `reference-impl/beach_foam.py`, `README-beach.md` §W7). |
| **F3** | A conservative slab's whiteness | `τ' = (1 − g)τ`, `R = τ'/(1 + τ')`, `T = 1 − R` | closed form | This is the **liftable** half of I7: a foam volume that spends its reflectance as `b_b/b` whitens without hiding, which is the symptom rather than the mechanism. | **DERIVED**, `12b-water-provenance.md`. |
| **F4** | ⚠️ **The white behind a hull is not the Kelvin wave field.** It is entrained air and turbulence from propeller and hull, on its own clock | — | — | Length of trail ÷ boat speed is a residence time. If §F's surf-zone constants predict a wake trail's persistence, they have survived a transfer no surf frame could offer — **which is the strongest available test of F1/F2 and it uses a completely different generator.** | Bar `bar.md` §M3, which supplies two wakes at two ages *in one frame, one lighting, one sea state* — the confounds removed. |

**What §F cannot cover.** Foam's *appearance* — the lace of a dissipating raft, the difference
between a spilling and a plunging cloud. `bar.md` §§C and E hold those and they are photographic.
§C's "three whites, one constant, and they are not one mechanism" is a taste-and-mechanism claim
this key can only half-reach: F2 checks the clocks are three, not that the three read as three.

---

## O · The water column

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **O1** | **The Babin bridge**: concentration → optics for mineral-dominated suspended matter | `b_p(555)/SPM ≈ 0.5 m²/g`; since 1 mg/L = 1 g/m³, **each mg/L adds ≈0.5 m⁻¹ to `b` at 555 nm** | the published value is a central estimate, not a precision constant; **organic-dominated matter is roughly double per unit mass**, so a row must say which regime | Absolute row at a declared SPM. | **P** — Babin, Morel, Fournier-Sicre, Fell & Stramski, Limnology & Oceanography **48**(2), 843–859 (2003). Chapter statement: `terrain-architect/references/28-liquids.md`. |
| **O2** | **The order-of-magnitude bracket, and it is the cheapest absolute row in this key** | coastal few-mg/L water → `b` of order **1 m⁻¹**; a 1000 mg/L silt river → `b ≈ 500 m⁻¹`, i.e. a millimetre-scale photon path | **two decades wide, and it still catches a factor of fifty** | ⚠️ It needs no calibration and it is not a tuning target — it is a statement that the quantity is the *kind* of thing it is named after. Turbid seawater is not silt slurry. Writable before the code is. | **P** (dimension check in `28-liquids.md`) + **DERIVED** (`11-verification-failures.md` tenth way). |
| **O3** | ⚠️ **The suspension balance is driven by the BED's stream power, not the WAVE's dissipation** | bed stream power `ρ·c_f·⟨\|u\|³⟩` = **2.6101 W/m²** at `u = 1 m/s`; depth-averaged breaking-zone load **373 mg/L** | the second is checked against a **published bracket** whose far end is the 1000 mg/L "opaque silt river" | ⚠️ **This defect is ×50 and a 53-row suite passed it.** Both ratio rows were blind: `M(2)/M(1)` vs 8 reads **8.000000000000 with and without the defect** — twelve significant figures, unchanged, *because the defect is absent from the quantity the row computes, not small in it.* The two absolute rows fire on the first digit (2.61 → 130.51 W/m²; 373 → 18 671 mg/L). **A suite made only of ratios is blind to precisely the errors that are constant factors.** | **DERIVED**, `11-verification-failures.md` tenth way, re-fired on `reference-impl/beach_optics.py` + `validate_beach.py`. |
| **O4** | ⚠️ **`c` and `K_d` are two coefficients and not one.** Beam attenuation `c` governs the sightline through the water to the bed; diffuse attenuation `K_d` governs the depth-tinted column | they differ by **5–20×** | — | A single constant driving both has one of the two wrong by that factor, and **no value of it is right**. Symptom: the bed reads far murkier than the column above it, or the column far clearer than the bed. | **P** — Preisendorfer's division, `12-water-rendering.md`, `12b`. |
| **O5** | ⚠️ **One turbidity slider is the canonical wrong architecture.** Tying the water mass's absorption and CDOM to the mineral load is a defect that is **bit-identical to clean at `spm = 0`** | absorption at `spm = 0`: (0.2824, 0.0835, 0.1577) clean **and** bugged; at `spm = 50`: (0.2824, 0.0835, 0.1577) clean against (1.3177, 1.6106, 7.5292) bugged | — | **Every row that touched the function called it at `spm = 0`.** A guard called at the parameter value where the defect is inert is not a weak guard; it is not a guard. Sweep the argument, or state in the row's own reason why the chosen value is where the defect is **largest** rather than where it is convenient. | **DERIVED**, `11-verification-failures.md` tenth way. |
| **O6** | ⚠️ **A transmission window is a property of the total, not of a constituent.** The 550–570 nm window is a statement about **`a_ph` plus pure water**, not about `a_ph` | the minimum of a sum of two absorption lines sits **between** them, nearer the broader tail; for peaks at 440 and 675 that is **590–600 nm** (this run's declared shape lands at **592**) | — | Carry it as a **pair**: a row on the total absorption minimising in the band containing 550–570 (it does), and an INFO row on where `a_ph` alone minimises. Fitting a pigment spectrum to put *its* minimum at 560 needs widths no pigment has. | **DERIVED** (wave 4, `README-beach.md` §F5), correcting a reading of `28-liquids.md`. |

**What §O cannot cover.** Whether the surf zone reads as *turbid* — `bar.md` §D makes turbidity a
state variable and §H2 measures a laden swash, and both are photographic criteria. This key can
check the load is the right *number*; it cannot check the water looks like that number.

---

## A · The illuminant

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **A1** | **Kasten–Young relative optical air mass** | `m = 1/(sin h_app + 0.50572·(h_app + 6.07995)^(−1.6364))`, equivalently `1/(cos ζ + 0.50572·(96.07995 − ζ)^(−1.6364))` | closed form; 1e-6 | It must be fed the **refracted** elevation. Feeding true elevation is 0.2% at 21°; the naive `1/sin h` is **0.6% off at 21° and diverges from there**. | **P** — Kasten & Young (1989). Row in `10-lighting-shadows.md`. |
| **A2** | ⚠️ **Kasten–Young is undefined below the horizon and fails SILENTLY.** A negative base raised to a fractional power returns `nan` with a `RuntimeWarning`, and **a `nan` multiplied into a radiance field propagates without raising** | `nan` | — | **A guard belongs on that boundary.** Any code path that can feed a below-horizon illuminant into an air-mass extinction must be shown to reject it, not to survive it by luck. Test it: put the sun 12° below the horizon and check the frame, not the exception log. | **DERIVED** — `gauntlet/bar/photo-spec.md` §L, the night frame that exposes it. |
| **A3** | Atmospheric refraction | Bennett: `R = (1/60)·cot(h + 7.31/(h + 4.4))` degrees, written for **apparent** altitude | Sæmundsson's true-altitude twin `1.02·cot(h + 10.3/(h + 5.11))` differs by **< 0.001° above 20°** — below anything that matters, so either is fine **as long as one is used** | Check which one, and check the elevation it is fed. | **P** + **D** (recomputed, `10-lighting-shadows.md`). |
| **A4** | The worked suns this project is calibrated against (Aljezur, 37.3167° N, 8.8000° W, WEST = UTC+1) | 2026-08-10 18:41 → elevation **21.02°**, azimuth **273.75°**, `m` = **2.771**; 2026-08-12 15:28 → **57.22°**, **233.96°**, `m` = **1.189** | reproduce to **0.01°** in elevation/azimuth from the low-order NOAA/Meeus algorithm | ⚠️ **`4·lon_east_deg` means east-positive longitude.** A western site takes a negative number; the wrong sign shifts true solar time by twice the longitude correction while leaving everything downstream self-consistent. | **D** — recomputed in full, `10-lighting-shadows.md`. |
| **A5** | The illuminant's **colour** is not free | `exp(−m·τ_Rayleigh)` at its own air mass, to one part in 10⁴ | that 1e-4 is the agreement achieved, and the row's resolution | This fixes three things at once: the air mass is not free, the reddening is not a grade, and a sun colour that inverts to the wrong air mass is a finding. `SUN_COL = (1.000, 0.892, 0.674)` inverts to air mass **2.77**. | **D**, `12a-water-derivations.md`; the form and its Hansen & Travis corrections are `P`, cited in `10`. |

**What §A cannot cover.** Absolute exposure. `11-verification-failures.md`'s seventh way is
explicit: without a RAW capture, a known neutral in frame, or usable EXIF, **a comparison against a
photograph is only ever relative** — a renderer can have every proportion in the frame right and
its absolute exposure wrong, and no amount of ratio discipline will discover it.

---

## X · Cross-instrument: what two readings of one wind do not establish

One row, and it is the row that stops a false corroboration.

| # | Statement | Expected | Tolerance, and where it comes from | How to check | Source |
|---|---|---|---|---|---|
| **X1** | **Two instruments agreeing establishes nothing until their sensitivities are compared.** The glitter-path width and the whitecap coverage both read the wind | `d(ln width)/dU` = **0.0759** per m/s at 6 m/s → `dU` = **0.13 m/s** at 1% width error; `d(ln W)/dU = n/U` = **0.5683** per m/s → `dU` = **1.93 m/s** at the law's factor-of-3 spread. **The width is a 14.7× sharper wind instrument.** | print each path's `dU` **before** the agreement is allowed to count | The two readouts agreed to **2.7%** (5.84 vs 6.00 m/s) and that agreement is **inside the coverage's own noise by a factor of ~50**. They could not have disagreed informatively. ⚠️ **The raw sensitivities rank them the other way** — coverage is 7.5× steeper in `U` and is the *worse* instrument. `dU = σ_lnX/\|d(ln X)/dU\|` is the only figure that ranks instruments, and neither factor ranks them alone. | **DERIVED**, `11-verification-failures.md` fourteenth way, recomputed on `reference-impl/beach_optics.py` and `beach_foam.py`. Arithmetic re-verified while authoring this key. |

---

## TRAPS · Constants that are wrong outside their domain

Every one of these has already cost this project, or this project's sources, a round. They are
collected here because a critic scoring row-by-row will not see them.

| Trap | The wrong use | The cost | Where |
|---|---|---|---|
| **Kelvin's 19.4712° is deep-water only** | applied at `Fr_h` near 1 | the wedge widens toward 90° there; "the render is 30° wide, so it is wrong" is a **category error** if `Fr_h > 0.7` | K5, K7 |
| **`1 − 1/n²` is a reflectance, not a backscatter fraction** | used as `b_b/b` in a foam volume | 43.874% against a traced **0.0230** — twenty times | I7 |
| **The longshore quarter and half are two conventions** | `E₀/4` paired with breaking-zone quantities | wrong by **exactly two** | B13 |
| **Kasten–Young is undefined below the horizon** | a below-horizon illuminant fed to an air-mass extinction | silent `nan` propagating through a radiance field | A2 |
| **`γ ≈ 0.78` is where breaking starts** | read as what a surf zone sits at | the saturated ratio is slope-dependent, 0.477 here against a field range 0.2–1.0 | B7 |
| **`γ_s = 0.40` is a flat-bed limit** | read as a second universal constant | it is the limit of a *family*, not a value | B7 |
| **The Iribarren thresholds have two conventions** | one table carried without an argument | 0.5/3.3 (deep-water) vs 0.4/2 (local) | B15 |
| **Cox & Munk's components and total are separate fits** | one quoted as implying the other | 0.8% at any wind, and a file that checks one against the other has misread the source | G4 |
| **Cox & Munk's wind is at 12.5 m over 1–14 m/s** | used as `U₁₀`, or extrapolated to storms | outside the fit's own domain | G2 |
| **Per-axis variance vs total `mss`** | consumers disagreeing on the convention | each stays individually defensible while the budget summing them is wrong by that factor | G6 |
| **Whitecap coverage's own law spans a factor of 3** | used as a precision wind instrument | `dU` = ±1.93 m/s at 6 m/s | G11, X1 |
| **`c` and `K_d`** | one constant driving both | 5–20× on one of the two paths | O4 |
| **The Dean profile's `x` is a distance to a curve** | an axis offset on a curved coast | 0.397° against 0.0008°, plus 5.4% spurious contour crowding; the bathymetry changes when the grid rotates | B11 |
| **`a_wet` and `rho_water` both take water-side arguments** | composed | up to 35%, invisible at both of the map's fixed points | I9 |
| **`R_int`'s integrand kinks at `μ_c`** | one Gauss–Legendre rule across it | 3e-5, with a sign-alternating convergence table that reports success at every refinement | I5 |
| **Numeral collision, and it is a real grep hazard** | `19.47` appears in `README-beach.md` as a **beach-face run length in metres** (`0 → 1.029 m over 19.47 m`), nothing to do with Kelvin's angle | a critic grepping `19.47` to find the wake constant will land on a beach profile | K1 |

---

## OPEN · What this key could not source

Listed as open rather than defaulted, per the intake rule. **None of these may be scored.**

| Open item | Why it is open | What is survivable about it |
|---|---|---|
| **`s` in `cos^(2s)(θ/2)`** — the Mitsuyasu (1975) `11.5(U/c_p)^(−2.5)` and Hasselmann (1980) `9.77` parameterisations | attribution only; neither paper is held in this container and this run has never implemented a directional spectrum (`workbench.md` 12.2, 13.3) | S4 still catches a *unidirectional* field, which is the defect thirteen waves actually have. It cannot catch a field short-crested by the wrong amount. |
| **Longuet-Higgins, Cartwright & Smith (1963) itself** | cited for the functional form, not read | the `cos^(2s)` form is standard enough to state; the normalisation (S2) is arithmetic and needs no paper |
| **The supercritical wake half-angle `arcsin(1/Fr_h)`** | classical, attributed to Havelock/Lighthill, not verified here | K5's sign-and-monotonicity row does not depend on it |
| **Hunt's run-up constant of proportionality** | the published relation is a scaling; the coefficient depends on which run-up level and which `H` is meant | the *validity range* `0.1 < ξ < 2.3` is checkable and `ξ₀ = 0.332`, `ξ_b = 0.300` sit inside it |
| **Dally's decay coefficient `K`** | quoted as 0.15 in the energy-flux form and 0.017 in REF/DIF's amplitude form; the 1985 paper could not be obtained to settle the conversion | **bounded rather than cited**: the break onset, and with it the crest depth, is independent of `K` to machine precision — proved, not asserted |
| **The name "Walsh"** on the reciprocity relation | widely attached to J.W.T. Walsh (1926); the paper was not read here | the *identity* is standard optics and closes to 6e-11; only the attribution is soft |
| **Sommerfeld (1896) and Penney & Price (1952) as read documents** | cited for the **structure**; neither held in this container | every number in §D is `D`, evaluated here from Fresnel integrals rather than read off a table, and D1 is exact rather than tabulated |
| **The Secchi column** `Z ≈ 1.44/(c + K_d)` with `K_d ≈ a + 0.02b` | the classical Preisendorfer form with a **placeholder** backscatter ratio | the depths it produces are as good as the placeholder and are marked `?` in `12b` |
| **The reference frame's wind (6 m/s)** and the RIB's speed, size and water depth in `bar.md` §M | unobserved | which is exactly why K5/K7 exist: the finding from a wide wedge is the *depth*, not an error |

---

## WHAT THIS KEY CANNOT COVER — stated globally

Per `bar-selection.md`: what an answer key cannot check must be **sent somewhere**, not allowed to
pass by default.

1. **Taste, feel and visual craft.** Everything in the "What §… cannot cover" notes above. These
   route to `gauntlet/sea/bar/visual/` — **which is empty and blocked.** `gauntlet/sea/bar/bar.md`
   is a *written description* of the owner's photographs, and a description is the one thing a bar
   may not be. All three wave-11 critics reached the same conclusion independently: the visual
   dimension is judgeable from 0 to about **6** and un-judgeable above it until the image files are
   on disk. **A physics PASS on this key is not a visual score and must never be reported as one.**
2. **Absolute radiometry.** See §A's note. Ratios internal to one frame, pairs close in level; a
   photograph gives a sign and an ordering, not a number.
3. **Prose and provenance discipline.** Routes to `gauntlet/sea/bar/prose/README.md`, which points
   at `terrain-architect/references/` as the comparator.
4. **Whether the code is reached at all.** This key checks quantities; it cannot check coverage. A
   branch with **zero subsamples** across every frame in the suite is a finding, and this project
   has one on record: a shade sail 3.4× wrong survived three rounds, a 268-row suite and a
   per-channel colour regression on **0 of 8 640 000 subsamples** of the hero frame. Ask of every
   §-row: *did any pixel reach this?* — and answer with an integer.
5. **Performance.** Nothing here is a budget. `11-verification-failures.md`'s metrics section owns
   that.

---

## ERRATA · Found while mining, reported not fixed

Per the scout's brief: errors found in a chapter are reported here and in the round record, **not
edited in place**.

- ⚠️ **The capillary-minimum pair `(23.1 cm/s, 1.73 cm)` is not self-consistent at one surface
  tension.** `12-water-rendering.md` lines 452 and 3727, and the verification note in
  `00-index.md` line 291, quote both halves as verified against standard references. Recomputed
  while authoring this key: `c_min = 23.1 cm/s` implies `σ = 0.07256 N/m`, while
  `λ_min = 1.73 cm` implies `σ = 0.07437 N/m` — **2.5% apart in `σ`, 1.1% in `λ`**. At the value
  the run's own code uses (`reference-impl/wake.py`, `SIG = 0.0728`, matching pure water at 20 °C)
  the consistent pair is **`c_min = 23.12 cm/s` at `λ_min = 1.712 cm`**. The 1.73 cm figure is a
  common textbook rounding taken at a warmer/cleaner `σ` and does not come from the same `σ` as the
  23.1. **Nothing downstream moves at the precision either is quoted to** — this is a provenance
  defect, not a render defect, and the fix is to declare one `σ` and derive both halves from it.
  Filed here rather than corrected, because this file is not the chapter.
- **Not an error, recorded so it is not reported as one:** `12a-water-derivations.md` uses
  **48.5°** for the critical angle and `12b`/`photo-spec.md` use **48.6°**. Both are correct —
  48.519° at `n = 1.3348` and 48.607° at `n = 1.333`. See I6.
- **Not an error, recorded so it is not reported as one:** `11-verification-failures.md` says the
  glitter width is a "**15×** sharper wind instrument" in prose and **14.7×** in its provenance
  row. Recomputed here: `1.933/0.1318 = 14.67`. The prose figure is a stated rounding.

---

## Row census

Each row is assigned **one** primary tier, by what its *expected value* rests on. Rows whose
structure is cited but whose number was recomputed here (much of §D and §I) count as DERIVED,
because the number is what a critic checks.

| Section | Rows | CITED (`P` / `P (attribution)`) | DERIVED / `D` | scoring rule | not scorable (see §OPEN) |
|---|---|---|---|---|---|
| K — wake | 7 | 5 | 0 | 2 (K3, K7) | K6 |
| G — slope & glitter | 13 | 9 | 4 | — | — |
| B — beach transform | 17 | 8 | 9 | — | B16's coefficient only |
| D — diffraction | 10 | 3 | 7 | — | — |
| S — spreading | 4 | 2 | 1 | — | S3 |
| I — interface | 11 | 4 | 7 | — | I1's *name* only |
| F — foam | 4 | 1 | 3 | — | — |
| O — column | 6 | 3 | 3 | — | — |
| A — illuminant | 5 | 2 | 3 | — | — |
| X — cross-instrument | 1 | 0 | 1 | — | — |
| **Total** | **78** | **37** | **38** | **2** | **1 row + 9 items in §OPEN** |

K3 and K7 are scoring rules rather than physics statements (K3 forbids a constructed wedge; K7
forbids scoring K1 outside its domain) and are counted in K's total. S3 is a row that exists so a
critic knows the shape of the missing parameterisation and is explicitly **not scorable**; K6 is
cited for shape only and carries no tolerance. §OPEN lists nine items, some of which qualify a row
rather than being a row.

---

*Frozen 2026-08-20, before the wave it judges. Corrections append below with a date; nothing above
this line is edited in place.*
