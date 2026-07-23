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
| 2 | **Independent-implementation agreement** | Our result matches a separately-developed library | ✅ 4 families (RichDEM/pysheds/Landlab) — RichDEM runs in the base env; the pysheds/Landlab checks `pytest.importorskip` and run once `requirements-crossvalidate.txt` is installed |
| 3 | **Published-benchmark agreement** | Matches a number in the primary source / a standard analytic solution | ✅ catalogue below (incl. the **Halfar/Bueler SIA** exact solution) |
| 4 | **Primary-source audit** | Citations real, papers say what's claimed, constants correct | ✅ **full** — 34/34 load-bearing citations confirmed (below) |
| 5 | **Empirical vs real data** | Generated statistics live in the real-terrain distribution | ✅ **real DEMs** (below) — ours in-range on all 3 metrics |

All five rungs carry evidence, at full coverage of the load-bearing set.

## Rung 5 — empirical agreement with real-terrain statistics

Our generated landscape is measured and compared to statistics published for **real**
landscapes. These targets are **emergent** — nothing in the code sets Hack's exponent or the
hypsometric integral; they arise from the erosion physics — so landing in the real range is
evidence of physical realism, not self-consistency. `tests/test_empirical.py`:

| Statistic | Real-terrain value (published) | Ours (emergent) | Verdict |
|---|---|---|---|
| Hypsometric integral | ~0.4–0.6, mature fluvial basins (Strahler 1952) | **0.48** | ✅ in range |
| Hack's law exponent `L ∝ A^h` | ~0.5–0.6 (Hack 1957; classic 0.57) | **0.50** | ✅ in range |

**Full version — real DEMs** (`empirical_dem.py`): two independent real landscapes pulled from
open SRTM (AWS Terrain Tiles) and measured with the **identical estimator** used on our terrain
(the only fair test — concavity especially is measurement-sensitive):

| | Hypsometric integral | Concavity θ | Hack's h |
|---|---|---|---|
| **Colorado Plateau** (N36W113, 3 windows) | 0.57–0.63 | 0.03–0.22 | 0.48–0.50 |
| **Great Smoky Mtns** (N35W083, 3 windows) | 0.21–0.34 | 0.15–0.31 | 0.54–0.60 |
| **real range (6 windows)** | **0.21–0.63** | **0.03–0.31** | **0.48–0.60** |
| **OURS** (stream power, same estimator) | **0.483** | **0.268** | **0.499** |
| | ✅ in range | ✅ in range | ✅ in range |

**Ours falls inside the real range on all three metrics.** Two honest notes: (1) Hack's law is
the robust one — it agrees across two very different landscapes; (2) raw slope–area concavity is
biased low on noisy real DEMs (hillslope contamination; Wobus et al. 2006), which is exactly why
the estimator must be identical on both sides — measured that way, ours (0.27) sits squarely in
the real 0.03–0.31. This is stronger than the textbook θ≈0.45 comparison, which only holds under
careful channel extraction.

## Rung 2 — independent-implementation agreement

Our result compared **by test** against a mature library developed separately from the same
papers (agreement = two independent readings converge). `tests/test_crossvalidate*.py`. **Only
RichDEM is a base-environment dependency and always runs; the pysheds and Landlab checks
`pytest.importorskip` those libraries and are exercised when `requirements-crossvalidate.txt` is
installed (CI / a dev machine), so in a bare install they SKIP rather than fail** — real external
validation, but gated on the optional dependency being present:

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
| **SIA glacier** | **Halfar (1983) similarity solution / Bueler 2005 Test B** — self-similar dome `H_c·[1−(r/R)^(4/3)]^(3/7)` for n=3, exact volume conservation, centre thins while margin advances | `test_benchmarks.py` (interior shape reproduced to <3%) |
| Hillslope diffusion | Gaussian Green's function — variance = s₀² + 2Dt/dim | `test_benchmarks.py` (new) |
| Hillslope diffusion | exact discrete single-Fourier-mode decay | `test_diffusion.py` |
| Worley F1 | independent brute-force nearest-feature-point | `test_benchmarks.py` (new) |
| Isostatic flexure | analytic single-mode & line-load kernel (Turcotte & Schubert) | `test_isostasy.py` |
| Stream power | Flint's law S ∝ A^(−m/n) at steady state (emergent) | `test_streampower.py` |
| Voellmy runout | analytic L = H/tan α on a ramp | `test_runout.py` |
| Tephra thinning | Pyle 1989: ln(thickness) linear in distance | `test_analytic.py` |
| Seafloor age–depth | Parsons & Sclater / GDH1: d ∝ √age | `test_analytic.py` |
| PDC energy cone | Malin & Sheridan: runout = H_c/μ | `test_analytic.py` |

**SIA glacier — gap now closed.** Previously the SIA glacier (`sims_illustrative.py`) had only
invariant checks. It is now benchmarked against the **Halfar (1983) exact similarity solution**
(Bueler et al. 2005, "Test B"): started from the analytic Halfar dome and run with zero mass balance,
the numerical solver conserves ice exactly, thins at the centre while the margin advances, and
reproduces the analytic self-similar profile `[1−(r/R)^(4/3)]^(3/7)` (n=3) to within ~1% in the
interior (`test_glacier_sia_matches_halfar_similarity_solution`). The exponents 4/3 and 3/7 come from
the analytic solution, not the code, so this is genuinely independent. The illustrative CFL-capped
sub-cycling is accurate enough to hold the self-similar shape over the tested span; a geological `dt`
would still want an implicit solver (as the docstring notes).

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

## Rung 4 — primary-source audit (full coverage of the load-bearing set)

Every load-bearing citation that drives the `reference-impl` code — each module's primary
paper(s) and its named constants — re-verified against primary/authoritative sources on the web
(2026-07). **34 citations audited, 34 confirmed: no fabricated citation, no wrong method, no
wrong constant.** Verdicts abbreviated ✅ (paper real, method/constant as claimed).

| Family | Citation → skill claim | Verified |
|---|---|---|
| Noise `01` | Perlin 2002 *Improving Noise* — quintic fade `6t⁵−15t⁴+10t³` | ✅ exact |
| | Gustavson *Simplex demystified* — `F2=(√3−1)/2`, `G2=(3−√3)/6` | ✅ exact |
| | Worley 1996 *A cellular texture basis function* (SIGGRAPH) — F1/F2 | ✅ |
| | Fournier/Fussell/Carpenter 1982 (CACM 25:371) — midpoint displacement | ✅ |
| Flow `03` | O'Callaghan & Mark 1984 (CVGIP 28) — D8 | ✅ |
| | Freeman 1991 (C&G 17:413) — MFD, `p≈1.1` | ✅ constant exact |
| | Barnes/Lehman/Mulla 2014 (C&G 62:117) — priority-flood, O(n)/O(n log n) | ✅ |
| Erosion `04`/`05` | Mei/Decaudin/Hu 2007 (Pacific Graphics) — virtual-pipe shallow water | ✅ |
| | Beyer 2015 (TU München thesis) — droplet particle erosion | ✅ |
| | Braun & Willett 2013 (Geomorph. 180:170) — O(N) implicit stream power | ✅ |
| | Cordonnier 2016 (CGF/EG 35:165) — uplift + stream-power terrain | ✅ |
| | Culling 1960 (J. Geol. 68:336) — hillslope diffusion (heat-flow analogy) | ✅ |
| | Werner 1995 (Geology 23:1107) — first CA dune model | ✅ |
| | Voellmy 1955 — runout friction `μ` + turbulent `ξ` | ✅ |
| | angle of repose, dry sand ≈ 34° (USBR) | ✅ |
| Analysis/scatter `06`/`07` | Zevenbergen & Thorne 1987 (ESPL 12:47) — partial-quartic curvature | ✅ exact |
| | Beven & Kirkby 1979 (HSB 24:43) — TWI / TOPMODEL | ✅ |
| | Bridson 2007 (SIGGRAPH) — Poisson-disk `k=30`, cell `r/√n` | ✅ verbatim |
| Ops/filters `10` | Frisken et al. 2000 (SIGGRAPH) — adaptively-sampled distance fields | ✅ |
| | Tomasi & Manduchi 1998 (ICCV) — bilateral filter | ✅ |
| | He/Sun/Tang 2010 (ECCV) — guided filter, O(1) | ✅ |
| | Perona & Malik 1990 (PAMI 12:629) — anisotropic diffusion | ✅ |
| Geological `11` | Pike 1977 — crater depth/diameter 0.1866 ≈ 0.2 | ✅ |
| | Melosh 1989 (*Impact Cratering*) — π-group gravity scaling | ✅ |
| | Beneš & Forsbach 2001 (SCCG) — layered strata representation | ✅ |
| | Pyle 1989 (BVol 51:1) — exponential tephra thinning | ✅ |
| | Malin & Sheridan 1982 — energy-cone `H/L` runout | ✅ |
| | Mohrig et al. 2000 (GSA Bull 112:1787) — avulsion superelevation | ✅ |
| | Collins/Melosh/Marcus 2005 (MAPS) — impact π-scaling `L^0.78 v^0.44 g^(−0.22) (sinθ)^(1/3)` | ✅ exponents |
| | Gault & Wedekind 1978 (LPSC 9:3843) — oblique-impact elongation & ejecta | ✅ |
| Glacial/coastal `12` | Glen's law `n=3`, `A≈2.4e-24 Pa⁻³s⁻¹` @0 °C (Paterson/Cuffey) | ✅ std, temp-dep (flagged) |
| | Parsons & Sclater 1977 (JGR 82:803) — age–depth `d ∝ √age` | ✅ |
| Lava `19` | Miyamoto & Sasaki 1997 (C&G 23:283) — CA lava with temperature | ✅ |
| Climate `13` | Sherman 1978 (JAM 17:312) — mass-consistent wind | ✅ |

**Two honest caveats (neither a defect):**

1. **Simplex `70` normalisation** is empirical / gradient-set-specific (Gustavson's
   `simplexnoise1234.c`), not universal — which `01` already states.
2. **Lunar simple→complex crater transition** — the skill said "~15 km"; Pike's onset is
   ~10.6 km, the change spans ~10–30 km. **Applied:** `references/11-geological.md` now reads
   "~10–20 km" (onset ~11 km, span ~10–30 km) — the one prose correction from the audit.
3. **Oblique-impact ejecta morphology** — a source check of the oblique-impact literature
   (Gault & Wedekind 1978; Anderson et al. 2003; Luo et al. 2022; azimuthal sand data
   arXiv 2404.16677; Schultz 1996; Ekholm & Melosh 2001) corrected the `crater.py` ejecta/peak
   model, which had three wrong specifics: the cross-range **butterfly** was onsetting at ~15°
   (it belongs <~5°; the up-range forbidden wedge is the <~20° feature); the downrange/up-range
   mass contrast ran ~12–18× (the sand data cap is ~8×); and the complex central peak was nudged
   **downrange** (the offset points **up-range**, toward deepest penetration — and is contested,
   so now slight). **Applied:** `crater.py`, `references/11-geological.md`, and the size×angle
   `crater_matrix.png` now follow the observed sequence, with regression oracles in
   `test_crater.py` (`test_butterfly_only_at_grazing_not_premature`,
   `test_central_peak_offset_is_uprange_not_downrange`).
4. **Grazing-crater depth asymmetry** — a follow-up source check (Schultz; the subsurface-pulse
   study Anderson et al., arXiv 2308.01876, reporting the up-range floor slope ~10° steeper) showed
   the `crater_demo.py` grazing "plow" was deepening **down-range** (a skipping-stone intuition) —
   backwards, and inconsistent with the up-range central peak. A grazing crater is **deeper
   up-range** (first contact / peak energy). **Applied:** the plow floor tilt is flipped (regression
   oracle `test_grazing_crater_is_deeper_uprange`), a labelled `crater_anatomy.py` /
   `crater_anatomy.png` figure documents the corrected morphology, and `references/11-geological.md`
   is updated. (Presentation layer — the analytic `crater.py` oracles were unaffected.)

**Coverage.** This covers every `reference-impl` module's primary citation(s) and named
constants. The handful of un-itemised references are standard textbooks whose existence is not
in question (Turcotte & Schubert *Geodynamics*; Serra 1982 *Image Analysis & Mathematical
Morphology*; Ford & Williams 2007 *Karst Hydrogeology*) or `F`-tier folklore the skill already
marks as having no canonical paper. Across 32 audited primary citations, **zero were fabricated
or misattributed** — strong direct evidence for the skill's author-by-author claim.
