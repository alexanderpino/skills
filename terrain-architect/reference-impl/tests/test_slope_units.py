"""Guard: `slope` is a TANGENT, so no chapter may apply a trig function to it.

THE DEFECT THIS CLOSES. `06` defines `slope = sqrt(dzdx² + dzdy²)` — the dimensionless gradient
magnitude, already equal to `tan θ` — and the shipped code agrees: `analysis.slope()` returns
`np.hypot(dzdx, dzdy)`, and `erosion_thermal.thermal_erosion` documents `repose_slope = tan(repose
angle)`. But three chapters then fed that ratio straight into a trig function:

    05  wet = min(1, K_w * A_specific / sin(slope))      # sin of a tangent
    05  FS  = (1 - wet * ρw/ρs) * tan(φ) / tan(slope)    # tan of a tangent
    06  TWI = ln( A_specific / tan(slope) )              # tan of a tangent
    17  flux = K_soli * frostCycles * soilMoisture * sin(slope)

`tan(slope)` is `tan(tan θ)`, which is not any physical quantity. The cost was measured before the
fix: the infinite-slope factor of safety came out 7.4% / 16.9% / 35.8% LOW at 25° / 35° / 45°, and
the dry critical angle landed at 31.4° instead of the friction angle 35°. `06`'s TWI formula
disagreed with its own pseudocode two lines below it (which correctly divides by `slope`) and with
`analysis.twi`, which ships `log(a / s)`.

WHY A SCAN AND NOT A REGISTER. `test_pseudocode_drift.py` argues for declared pairs over scanning,
because generic parameter names collide with prose. That argument does not apply here: the pattern
`sin(slope)` is unambiguous, has zero legitimate uses, and the failure mode is a NEW chapter
reintroducing it — precisely what a register cannot see. So this one scans.

WHAT IS LEGITIMATE, AND MUST NOT TRIP THE SCAN:
  * `atan(slope)`      — recovering the angle FROM the tangent. Correct; `09` uses it twice.
  * `tan(35°)`, `tan(φ)` — trig of an angle LITERAL or an angle-valued symbol. Correct: a threshold
                         is built by taking the tangent of the angle, then compared to `slope`.
  * `sin(θ)`           — `05`'s Voellmy block and `runout.py` genuinely carry an angle (the module
                         computes `theta = np.arctan2(dh, horiz)` first). Correct.
  * `tan(maxSlope)` (`07`), `tan(shoreSlope)` (`12`) — DIFFERENT symbols that are angle-valued;
                         `07` even writes `s > tan(maxSlope)` with `s = slope(p)`, the endorsed
                         threshold form. The scan matches the identifier `slope` only where it
                         STARTS the token, so camelCase names ending in `Slope` are not caught.
The scan therefore keys on the literal identifier `slope`, not on trig calls in general.

TWO TIERS, AND WHY. Tier 1 scans FENCED CODE BLOCKS with zero tolerance: that is the surface a
reader implements from, and there is no legitimate reason for the pattern to appear there. Tier 2
scans PROSE, where the pattern legitimately appears in warnings that name the bad form in order to
forbid it (this fix added several). Prose is therefore allowed the pattern only on a line that also
carries a negation cue; a bare prose assertion like `09`'s failure-mode table row still trips it.
"""
import re
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]
CHAPTERS = REF.parent / "references"

# `sin(slope)` / `tan(slope)` / `cos(slope)`, including `sin(slope_tan)` and `np.sin(slope)`.
#   * the lookbehind for a letter is what lets `atan(`/`arctan(`/`asin(` through;
#   * requiring the argument to START with lowercase `slope` is what lets `tan(maxSlope)` and
#     `tan(shoreSlope)` through — those are separate, angle-valued symbols;
#   * case-sensitive on purpose, so camelCase `...Slope` cannot match.
FORBIDDEN = re.compile(r"(?<![A-Za-z_])(?:sin|cos|tan)\s*\(\s*(?:np\.)?slope(?![A-Za-z0-9])")

# Words that mark a prose line as *discussing* the bad form rather than asserting it. Kept small
# and explicit; a warning that trips this scan just needs to say what it is warning about.
NEGATION_CUES = ("never", "not ", "wrong", "✗", "would", "computes", "biases", "error",
                 "version", "instead", "rather than", "defect", "bug", "mistake")

# Chapters known to still carry the defect in PROSE but outside this change's file ownership. Each
# row must name a real, currently-present offender; `test_the_known_unfixed_list_is_not_stale`
# fails as soon as one is fixed, so the list liquidates itself instead of becoming an excuse.
KNOWN_UNFIXED = {
    # 09-verification.md:319, "| Wetness index → Inf | `tan(slope) → 0` on flats | Clamp slope ≥
    # 0.001 (`06`) |" in the failure-mode table. Same units error; the adjacent remedy is already
    # phrased correctly ("clamp slope"), so it is a stale formula in a table rather than something
    # a reader executes. Outside the file ownership of the change that added this test — 09 needs
    # an owner. Drop this row when it is fixed.
    "09-verification.md": 1,
}


def _chapters():
    return sorted(CHAPTERS.glob("*.md"))


def _split_fences(path):
    """(fenced_code_lines, prose_lines), each a list of (line number, text)."""
    code, prose, in_fence = [], [], False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        (code if in_fence else prose).append((n, line))
    return code, prose


def _code_offenders(path):
    """Tier 1: the pattern inside a fenced block. Zero legitimate uses."""
    code, _ = _split_fences(path)
    return [(n, t.strip()) for n, t in code if FORBIDDEN.search(t)]


def _prose_offenders(path):
    """Tier 2: the pattern in prose on a line with no negation cue — i.e. asserted, not warned."""
    _, prose = _split_fences(path)
    return [(n, t.strip()) for n, t in prose
            if FORBIDDEN.search(t) and not any(c in t.lower() for c in NEGATION_CUES)]


def _offenders(path):
    return sorted(_code_offenders(path) + _prose_offenders(path))


@pytest.mark.parametrize("chapter", _chapters(), ids=lambda p: p.name)
def test_no_pseudocode_block_applies_trig_to_the_slope_tangent(chapter):
    """Tier 1, the guard proper: `slope` is `tan θ`, so `sin(slope)` in a block a reader
    implements from is a units error. No tolerated offenders — this tier is clean everywhere."""
    found = _code_offenders(chapter)
    assert not found, (
        "%s has a PSEUDOCODE BLOCK applying a trig function to `slope`, which is the "
        "dimensionless gradient |grad h| = tan(theta), not an angle (06). `tan(slope)` means "
        "`tan(tan theta)`. This cost the infinite-slope factor of safety 7.4%%/16.9%%/35.8%% at "
        "25/35/45 deg before it was fixed.\n"
        "  Use `slope` directly where the textbook form wants `tan theta`;\n"
        "  use `slope / sqrt(1 + slope**2)` where it wants `sin theta`;\n"
        "  use `atan(slope)` to recover the angle itself.\n"
        "Offending lines:\n%s"
        % (chapter.name, "\n".join("  %s:%d: %s" % (chapter.name, n, t) for n, t in found)))


@pytest.mark.parametrize("chapter", _chapters(), ids=lambda p: p.name)
def test_no_prose_asserts_trig_on_the_slope_tangent(chapter):
    """Tier 2: prose may NAME the bad form to forbid it, but may not assert it as a formula."""
    found = _prose_offenders(chapter)
    allowed = KNOWN_UNFIXED.get(chapter.name, 0)
    assert len(found) <= allowed, (
        "%s applies a trig function to `slope`, which is the DIMENSIONLESS gradient |grad h| "
        "= tan(theta), not an angle (06). `tan(slope)` means `tan(tan theta)`. This cost the "
        "infinite-slope factor of safety 7.4%%/16.9%%/35.8%% at 25/35/45 deg before it was fixed.\n"
        "  Use `slope` directly where the textbook form wants `tan theta`;\n"
        "  use `slope / sqrt(1 + slope**2)` where it wants `sin theta`;\n"
        "  use `atan(slope)` to recover the angle itself.\n"
        "Offending lines (%d found, %d tolerated):\n%s"
        % (chapter.name, len(found), allowed,
           "\n".join("  %s:%d: %s" % (chapter.name, n, t) for n, t in found)))


def test_the_known_unfixed_list_is_not_stale():
    """A tolerated offender that has since been fixed must be removed, or it silently re-opens
    the hole it was documenting."""
    stale = []
    for name, count in KNOWN_UNFIXED.items():
        path = CHAPTERS / name
        if not path.exists():
            stale.append("%s no longer exists" % name)
            continue
        actual = len(_offenders(path))
        if actual < count:
            stale.append("%s now has %d offender(s), not %d — lower the count or drop the row"
                         % (name, actual, count))
    assert not stale, "the tolerated-offender list is stale: %s" % stale


def test_the_scan_pattern_actually_catches_the_original_defect():
    """A guard nobody has seen fail is a guard nobody should trust. These are the four lines as
    they were literally written before the fix; the pattern must catch every one."""
    original = [
        "    wet = min(1, K_w * A_specific / sin(slope))      # relative saturation",
        "    FS  = (1 - wet * rw/rs) * tan(phi) / tan(slope)  # factor of safety",
        "TWI = ln( A_specific / tan(slope) )",
        "    flux = K_soli * frostCycles * soilMoisture * sin(slope)     # cm/yr",
        "        s = cos(slope) * something",           # the third variant, for completeness
        "    w = sin( slope )",                          # whitespace inside the call
        "    x = np.sin(slope_tan)",                     # a prefixed identifier
    ]
    missed = [line for line in original if not FORBIDDEN.search(line)]
    assert not missed, "the guard pattern fails to catch its own motivating defect: %s" % missed


def test_the_two_tiers_discriminate_code_from_warning_prose(tmp_path):
    """The tier split is the load-bearing trick here, so exercise it on a synthetic chapter:
    a fenced offender must be caught, a warning that names the form must not be, and a bare
    prose assertion (the shape `09` still has) must be."""
    doc = tmp_path / "99-synthetic.md"
    doc.write_text(
        "Intro paragraph.\n"
        "```\n"
        "FS = tan(phi) / tan(slope)\n"                       # 3: fenced offender
        "```\n"
        "Never write `sin(slope)`; it applies a sine to a ratio.\n"   # 5: warning, cued
        "| Wetness index | `tan(slope)` on flats | clamp |\n"         # 6: bare assertion
        "Use `atan(slope)` to recover the angle.\n",                  # 7: legitimate
        encoding="utf-8")

    assert [n for n, _ in _code_offenders(doc)] == [3], (
        "the fenced-block tier must catch the pseudocode offender and nothing else, got %s"
        % _code_offenders(doc))
    assert [n for n, _ in _prose_offenders(doc)] == [6], (
        "the prose tier must catch the bare table assertion (line 6) while letting the cued "
        "warning (line 5) and `atan(slope)` (line 7) through, got %s" % _prose_offenders(doc))


def test_the_scan_pattern_does_not_flag_the_legitimate_forms():
    """The other half: a guard that cries wolf gets deleted. These must all pass clean."""
    legitimate = [
        "Plot the distribution of `atan(slope)` in degrees.",
        "| **Slope shade** | `atan(slope)` on a ramp | Steepness directly",
        "rockMask   = smoothstep(tan(35deg), tan(45deg), slope)              # steep = exposed rock",
        "slopeSel(s, lo, hi, w)   = smoothstep(lo-w, lo+w, s)   # s = tan, not degrees",
        "    FS  = (1 - wet * rw/rs) * tan(phi) / slope         # factor of safety",
        "    a      = g*sin(theta) - mu*g*cos(theta) - g*v*v/xi  # Voellmy: theta IS an angle",
        "    sin_theta = slope / sqrt(1 + slope**2)             # exact, stays in the tangent",
        "  at `slope = tan(phi)` -- the critical angle is `phi` on the nose.",
        "        return np.arctan(slope)",
        "screeSource = cliffMask * weatheringRate      # cliffMask = slope > ~55deg",
    ]
    flagged = [line for line in legitimate if FORBIDDEN.search(line)]
    assert not flagged, (
        "the guard flags a CORRECT form; `atan(slope)` and `tan(<angle literal>)` are both "
        "legitimate and must stay legal: %s" % flagged)


def test_the_three_fixed_chapters_are_clean():
    """State the fix as itself, so a partial revert of any one chapter is named directly."""
    dirty = {}
    for name in ("05-erosion-thermal-aeolian.md", "06-analysis-masks.md", "17-periglacial.md"):
        found = _offenders(CHAPTERS / name)
        if found:
            dirty[name] = found
    assert not dirty, (
        "these chapters were fixed for the slope-units defect and have regressed: %s" % dirty)


def test_06_defines_slope_as_a_tangent_and_says_so():
    """The fix is only durable if the DEFINITION site warns the next reader. If this note is
    deleted, the three call sites will drift back."""
    text = (CHAPTERS / "06-analysis-masks.md").read_text(encoding="utf-8")
    assert "Never write `sin(slope)`" in text, (
        "06 has lost the explicit note saying what `slope` is and is not. That note is what stops "
        "the units error being reintroduced at a new call site.")
    assert "sqrt(1 + slope²)" in text, (
        "06 has lost the exact tangent->sine identity, which is the escape hatch a reader needs "
        "when a textbook formula genuinely wants sin(theta).")


def test_the_chapter_twi_formula_matches_the_shipped_twi():
    """`06`'s TWI formula disagreed with `analysis.twi` (and with its own pseudocode). Pin them."""
    import numpy as np

    import analysis

    text = (CHAPTERS / "06-analysis-masks.md").read_text(encoding="utf-8")
    assert re.search(r"TWI = ln\(\s*A_specific\s*/\s*slope\s*\)", text), (
        "06's TWI formula is no longer `ln(A_specific / slope)`. `analysis.twi` divides by the "
        "slope tangent directly; dividing by `tan(slope)` biases TWI low by 0.08/0.19/0.44 nats "
        "at 25/35/45 deg.")

    # and the shipped function really does divide by the tangent, not by tan(tangent)
    for deg in (25.0, 35.0, 45.0):
        s = np.tan(np.radians(deg))
        got = analysis.twi(np.array([100.0]), np.array([s]), cellsize=1.0)[0]
        assert got == pytest.approx(np.log(100.0 / s)), (
            "analysis.twi no longer computes ln(A_specific / slope) at %g deg" % deg)


def test_the_dry_infinite_slope_criterion_recovers_the_friction_angle():
    """The identity that makes the units error self-evident, executed.

    Cohesionless and dry, FS = tan(phi)/slope crosses 1 at slope = tan(phi) — the critical angle
    IS the friction angle. The `tan(slope)` form crosses at 31.4 deg for phi=35 deg, missing by
    3.6 deg. This test is the chapter's claim, checked."""
    import numpy as np

    def critical_angle(denominator):
        lo, hi = 0.5, 60.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            s = np.tan(np.radians(mid))
            if np.tan(np.radians(35.0)) / denominator(s) > 1.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    correct = critical_angle(lambda s: s)
    assert correct == pytest.approx(35.0, abs=1e-6), (
        "the corrected form must put the dry critical angle exactly at the friction angle; "
        "got %.4f deg" % correct)

    wrong = critical_angle(lambda s: np.tan(s))
    assert wrong == pytest.approx(31.42, abs=0.01), (
        "the defective form's critical angle should be 31.42 deg, the number quoted in 05; "
        "got %.4f deg" % wrong)
    assert correct - wrong == pytest.approx(3.58, abs=0.01), (
        "05 quotes a 3.6 deg miss on the dry critical angle; got %.4f" % (correct - wrong))


@pytest.mark.parametrize("deg,expected_pct", [(25.0, -7.36), (35.0, -16.90), (45.0, -35.79)])
def test_the_factor_of_safety_error_quoted_in_05_is_real(deg, expected_pct):
    """The percentages written into `05`'s table, recomputed. FS is proportional to 1/denominator,
    so the error is (slope/tan(slope) - 1)."""
    import numpy as np

    s = np.tan(np.radians(deg))
    pct = (s / np.tan(s) - 1.0) * 100.0
    assert pct == pytest.approx(expected_pct, abs=0.01), (
        "05's table says the factor of safety comes out %.2f%% off at %g deg; recomputing gives "
        "%.2f%%. The prose and the arithmetic must agree." % (expected_pct, deg, pct))
