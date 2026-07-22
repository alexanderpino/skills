# Validity evidence ledger

Evidence that the skill's **concepts, pseudocode and math are valid** — kept honest about what
each check does and does not prove. This is distinct from the oracle tests in `tests/`, which
mostly prove **internal consistency** (the code solves the stated equation correctly), not
validity (the equation is the right one).

## The distinction that matters

A closed-form oracle derived from the same equation the code implements proves the code
**solves it correctly** — not that the equation is **right**. A wrong coefficient mirrored into
both the code and its analytic check passes green. So "117 tests pass" is self-consistency.
Validity needs evidence from an **independent source**.

## The evidence ladder (weakest → strongest) and current status

| Rung | Evidence type | What it proves | Status |
|---|---|---|---|
| 1 | **Dimensional consistency** | Necessary condition; a unit-inconsistent equation is invalid | ✅ `tests/test_dimensional.py` (below) |
| 2 | **Independent-implementation agreement** | Our result matches a separately-developed library | ✅ 4 families (RichDEM/pysheds/Landlab) |
| 3 | **Published-benchmark agreement** | Matches a number in the primary source / a standard analytic solution | ✅ partial (catalogue below); gap: **Halfar/Bueler SIA** |
| 4 | **Primary-source audit** | Citations real, papers say what's claimed, constants correct | ✅ **sampled** (7/7 confirmed, below); not exhaustive |
| 5 | **Empirical vs real data** | Generated statistics live in the real-terrain distribution | ✅ published-statistics (below); full DEM comparison still open |

All five rungs now carry evidence. The remaining hardening is breadth: a full (not sampled)
rung-4 citation audit, and a real-DEM (not published-statistics) rung-5 comparison.

## Rung 5 — empirical agreement with real-terrain statistics

Our generated landscape is measured and compared to statistics published for **real**
landscapes. These targets are **emergent** — nothing in the code sets Hack's exponent or the
hypsometric integral; they arise from the erosion physics — so landing in the real range is
evidence of physical realism, not self-consistency. `tests/test_empirical.py`:

| Statistic | Real-terrain value (published) | Ours (emergent) | Verdict |
|---|---|---|---|
| Hypsometric integral | ~0.4–0.6, mature fluvial basins (Strahler 1952) | **0.48** | ✅ in range |
| Hack's law exponent `L ∝ A^h` | ~0.5–0.6 (Hack 1957; classic 0.57) | **0.50** | ✅ in range |

No DEM download — compared against literature values. A stronger version (real SRTM/3DEP tiles,
more statistics: drainage density, width function, slope PDF) is the remaining rung-5 work.

## Rung 2 — independent-implementation agreement

Our result compared **by test** against a mature library developed separately from the same
papers (agreement = two independent readings converge). `tests/test_crossvalidate*.py`:

| Family | Independent implementation | Check |
|---|---|---|
| Priority-flood fill | RichDEM (Barnes) | correlated raised-height, no interior pit |
| D8 accumulation | pysheds · Landlab `FlowAccumulator` | drainage-area correlation > 0.9 |
| Stream power | Landlab `FastscapeEroder` | slope-area exponent = −m/n, and agree |
| Hillslope diffusion | Landlab `LinearDiffuser` | single-mode decay factor matches |

## Rung 3 — published-benchmark agreement

**Emergent** output checked against a result derived *outside* our code (an analytic continuum
solution or an independent recomputation), not an oracle re-derived from the same equation:

| Model | External benchmark | Where |
|---|---|---|
| Hillslope diffusion | Gaussian Green's function — variance = s₀² + 2Dt/dim | `test_benchmarks.py` (new) |
| Hillslope diffusion | exact discrete single-Fourier-mode decay | `test_diffusion.py` |
| Worley F1 | independent brute-force nearest-feature-point | `test_benchmarks.py` (new) |
| Isostatic flexure | analytic single-mode & line-load kernel (Turcotte & Schubert) | `test_isostasy.py` |
| Stream power | Flint's law S ∝ A^(−m/n) at steady state (emergent) | `test_streampower.py` |
| Voellmy runout | analytic L = H/tan α on a ramp | `test_runout.py` |
| Tephra thinning | Pyle 1989: ln(thickness) linear in distance | `test_analytic.py` |
| Seafloor age–depth | Parsons & Sclater / GDH1: d ∝ √age | `test_analytic.py` |
| PDC energy cone | Malin & Sheridan: runout = H_c/μ | `test_analytic.py` |

**Known gap:** the SIA glacier (`sims_illustrative.py`) has only invariant checks — no published
benchmark. The right one is the **Halfar/Bueler exact isothermal-ice-sheet similarity solution**
(Bueler et al. 2005), which needs the exact formula from the primary source; deferred to the
rung-4 audit, and it will also quantify how far the *illustrative* (CFL-capped) SIA is from an
accurate solver.

## Rung 1 — dimensional audit (machine-checked with `pint`)

`tests/test_dimensional.py` builds each load-bearing equation from quantities carrying real
units and asserts the result's dimension. Two grades:

- **DECISIVE** — built from constants with *independently-known* units (g, ρ, Glen's `A`,
  viscosity `η`). A wrong exponent or factor gives the wrong dimension and the test fails. These
  test the physics.
- **CONFIRMATORY** — a phenomenological constant (stream-power `K`, hillslope `D`) whose units
  are *defined* by the equation. Confirms the stated unit is self-consistent; cannot fail on
  physics.

| Equation | Ref | Result dim | Grade | Verdict |
|---|---|---|---|---|
| `τ = ρ g L sinθ` (pipe / lava driving stress) | 04, 19 | Pa | **decisive** | ✅ balanced |
| `D = (2A/(n+2))(ρg)ⁿ H^(n+2) \|∇s\|^(n-1)` (SIA) | 12 | m²/s | **decisive** | ✅ balanced |
| `q = k(τ−τ_y)L²/η` (Bingham flux) | 19 | m²/s | **decisive** | ✅ balanced |
| `L = H/tanα` (Voellmy runout) | 05 | m | **decisive** | ✅ balanced |
| `r = h·ρ_c/(ρ_m−ρ_c)` (Airy root) | 02 | m | **decisive** | ✅ balanced |
| `T = T₀ exp(−k x)` (tephra thinning) | 11 | exponent dimensionless | **decisive** | ✅ balanced |
| `d = d₀ + C√age` (age–depth) | 12 | m | **decisive** | ✅ balanced |
| `dh/dt = U − K A^m S^n` (stream power) | 04 | m/s | confirmatory | ✅ consistent |
| `dh/dt = D ∇²h` (hillslope diffusion) | 04/05 | m/s | confirmatory | ✅ consistent |

**One honest finding.** `TWI = ln(a / tanS)` with `a = A/width` has an argument in **units of
length** — `ln` of a dimensioned quantity, which is strictly improper (it implies a hidden 1 m
reference length). This is a **real, long-standing convention** of the Beven–Kirkby index, not a
transcription error — recorded here rather than hidden. Any port should be aware the index is
scale-referenced.

All 10 checks pass. Dimensional validity is a *necessary* condition met across the load-bearing
physics — it does not by itself prove the equations are physically right (that is rungs 2–5).

Run: `pip install -r requirements-validate.txt && pytest -q tests/test_dimensional.py`

## Rung 4 — primary-source audit (sampled)

A **representative sample** of the most load-bearing constants and citations, re-verified against
primary or authoritative sources on the web (2026-07). This is *not* exhaustive — the skill's
claim of full author-by-author verification remains its own — but a 7-item sample across noise,
scatter, glaciology, cratering, geomorphology and the erosion backbone found **no fabricated
citation and no wrong constant**, which is consistent with that claim.

| Skill claim (ref) | Primary/authoritative source | Verdict |
|---|---|---|
| Improved-Perlin quintic fade `6t⁵−15t⁴+10t³` (`01`) | Perlin 2002, *Improving Noise* (ACM TOG) | ✅ CONFIRMED — exact, continuous 2nd derivative |
| Bridson Poisson-disk `k=30`, cell `r/√n` (`07`) | Bridson 2007 SIGGRAPH sketch (UBC PDF) | ✅ CONFIRMED — both stated verbatim |
| Simplex skew `F2=(√3−1)/2`, `G2=(3−√3)/6` (`01`) | Gustavson, *Simplex noise demystified* | ✅ CONFIRMED — exact |
| Glen's flow law `n=3`, `A≈2.4e-24 Pa⁻³s⁻¹` at 0 °C (`12`) | glaciology (Paterson/Cuffey lineage) | ✅ CONFIRMED — standard 0 °C value; **temperature-dependent, and the skill says so** |
| Impact-crater depth/diameter ≈ 0.2 (`11`) | Pike 1977 (d/D = 0.1866 ± 0.0004) | ✅ CONFIRMED — 0.19 ≈ 1/5 |
| Angle of repose, dry sand ≈ 34° (`05`) | USBR hydraulics lab / standard tests | ✅ CONFIRMED |
| Braun & Willett 2013 O(N) implicit stream power (`04`) | *Geomorphology* 180:170–179 | ✅ CONFIRMED — citation & method real |

**Two honest caveats surfaced (neither a defect):**

1. **Simplex `70` normalisation** is empirical and gradient-set-specific (Gustavson's `simplexnoise1234.c`), not a universal constant — which the skill's `01` already states, and it further warns that OpenSimplex2 is a *different* contract to be ported from the pinned source, not this one.
2. **Lunar simple→complex crater transition** — the skill says "~15 km", Pike's onset is ~10.6 km and the change spans ~10–30 km. "~15 km" is a reasonable central value within that range; tighten to "~10–20 km" for precision.

**Sources:** [Perlin *Improving Noise* (ACM)](https://dl.acm.org/doi/10.1145/566654.566636) · [Bridson 2007 (UBC PDF)](https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph07-poissondisk.pdf) · [Simplex noise demystified (Gustavson)](https://cgvr.cs.uni-bremen.de/teaching/cg_literatur/simplexnoise.pdf) · [Pike 1977 (ADS)](https://ui.adsabs.harvard.edu/abs/1977iecp.symp..489P/abstract) · [Braun & Willett 2013 (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0169555X12004618)

**Scope honesty:** a 7-item sample cannot certify the whole corpus; it raises confidence and found zero defects. A full audit of every `P`-tier citation and load-bearing constant is the remaining rung-4 work.
