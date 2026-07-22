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
| 2 | **Independent-implementation agreement** | Our result matches a separately-developed library | ✅ 4 families (RichDEM/pysheds/Landlab) · expanding |
| 3 | **Published-benchmark agreement** | Matches a number in the primary source / a standard analytic solution | ◻ planned (Bueler SIA, Pike crater, Hack's law) |
| 4 | **Primary-source audit** | Citations real, papers say what's claimed, constants correct | ◻ planned (web) — *the skill claims this; not yet re-verified here* |
| 5 | **Empirical vs real data** | Generated statistics live in the real-terrain distribution | ◻ planned (DEM comparison) |

Rungs 3–5 are the open work; this file grows as each lands.

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
