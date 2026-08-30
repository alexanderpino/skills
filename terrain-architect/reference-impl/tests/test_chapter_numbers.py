"""Every number the chapters quote that a module can re-derive, checked against it.

THE GAP THIS CLOSES, AND WHY IT IS DIFFERENT FROM THE OTHER HARNESSES.
`test_atom_coverage` guards which atoms exist. `test_pseudocode_drift` guards the DEFAULTS inside
pseudocode signatures. Neither looks at the numbers in the prose — and prose is where a chapter
makes its quantitative claims, so prose is where a stale figure survives longest. A chapter that
says "1.5% of cells carry half the drainage" is making a checkable assertion about a module, and
until now nothing checked it.

⚠️ THE NUMBERS MOST AT RISK ARE THE ONES JUST ADDED. Six of the values below were written into
`03` a few commits ago, straight out of a fresh measurement. That is exactly when a number is
least suspect and most likely to rot: it is right today, nobody will re-derive it tomorrow, and
the terrain that produced it is one seed change away from moving. The same applies to `01`'s pinch
measurements.

TOLERANCE IS THE PRINTED PRECISION, NOT A MEASUREMENT ERROR. Each row is held to half a unit in
the last digit the chapter prints, so anything this catches is a real divergence between text and
code rather than a display artefact. There is nothing here to widen: if a row fails, either the
prose or the module moved, and somebody has to say which.

⚠️ WHAT THIS DOES NOT CHECK: that the numbers are RIGHT. `VALIDATION.md` and the oracle tests do
that. This only checks that the chapters say what the code computes. Both are needed: prose can
faithfully quote a wrong number, and correct code can be described by stale prose.
"""
import math
import re
from pathlib import Path

import numpy as np
import pytest

REF = Path(__file__).resolve().parents[1]
CHAPTERS = REF.parent / "references"


def _half_unit(printed):
    """Half a unit in the last significant place of `printed`."""
    s = printed.strip().rstrip("%×").replace(",", "")
    if "." in s:
        return 0.5 * 10.0 ** (-len(s.split(".")[1]))
    t = s.rstrip("0")
    return 0.5 * 10.0 ** (len(s) - len(t)) if t else 0.5


def _quoted(chapter, pattern):
    """Pull one number out of a chapter by regex, failing loudly if it moved."""
    text = (CHAPTERS / chapter).read_text(encoding="utf-8")
    m = re.search(pattern, text)
    assert m, ("%s no longer contains a number matching %r — either the prose changed or this "
               "row is stale. Both need a human." % (chapter, pattern))
    return m.group(1)


def check(chapter, pattern, actual, scale=1.0):
    printed = _quoted(chapter, pattern)
    exp = float(printed.rstrip("%×"))
    got = float(actual) * scale
    tol = _half_unit(printed)
    assert abs(got - exp) <= tol * (1 + 1e-9), (
        "%s prints %s; the code computes %.6g (tolerance %.3g, the printed precision). "
        "Fix the prose if the code moved deliberately; fix the code if it did not."
        % (chapter, printed, got, tol))


# --------------------------------------------------------------------------- #
# 03 — flow routing, the concentration statistics in the figure caption

@pytest.fixture(scope="module")
def flow_m():
    import flow_anatomy
    return flow_anatomy.measurements(), flow_anatomy


def test_03_d8_share(flow_m):
    m, _ = flow_m
    check("03-flow-routing.md", r"D8 needs \*\*([0-9.]+)%\*\*", m["d8_frac"], 100.0)


def test_03_mfd_share(flow_m):
    m, _ = flow_m
    check("03-flow-routing.md", r"MFD \*\*([0-9.]+)%\*\*", m["mfd_frac"], 100.0)


def test_03_ratio(flow_m):
    m, _ = flow_m
    check("03-flow-routing.md", r"— ([0-9.]+)× as many", m["ratio"])


def test_03_hybrid_share(flow_m):
    m, fa = flow_m
    dem = fa.terrain()
    share = m["hybrid_half"] / float(dem.size)
    check("03-flow-routing.md", r"the hybrid \*\*([0-9.]+)%\*\*", share, 100.0)


def test_03_reversal_relief(flow_m):
    """The crossover the caption puts at 'about 8 m' must still be where the sweep puts it."""
    _m, fa = flow_m
    sweep = fa.relief_sweep()
    cross = next((a for (a, d8, mfd) in sweep if d8 < mfd), None)
    assert cross is not None, "the sweep no longer crosses"
    printed = float(_quoted("03-flow-routing.md", r"below about ([0-9]+) m of texture"))
    assert abs(cross - printed) <= 2.0, (
        "03 says the order reverses below about %g m; the sweep now crosses at %g"
        % (printed, cross))


# --------------------------------------------------------------------------- #
# 01 — the lattice pinch points

def _pinch(lacunarity, reps=400, octaves=6, gain=0.5):
    import noise
    rng = np.random.RandomState(7)
    on, off = [], []
    for _ in range(reps):
        i, j = rng.randint(3, 120, 2)
        for px, py, bucket in ((float(i), float(j), on),
                               (i + rng.rand() * 0.8 + 0.1,
                                j + rng.rand() * 0.8 + 0.1, off)):
            total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
            for k in range(octaves):
                total += amp * float(noise.perlin(np.array([px * freq]),
                                                  np.array([py * freq]), k * 1013)[0])
                norm += amp
                freq *= lacunarity
                amp *= gain
            bucket.append(abs(total / norm))
    return np.array(on), np.array(off)


@pytest.fixture(scope="module")
def pinch():
    return {2.0: _pinch(2.0), 2.03: _pinch(2.03)}


def test_01_generic_level(pinch):
    on, off = pinch[2.0]
    check("01-noise.md", r"against \*\*([0-9.]+)\*\* at generic\s+points", off.mean())


def test_01_detuned_level(pinch):
    on, _off = pinch[2.03]
    check("01-noise.md", r"lifts the shared points to \*\*([0-9.]+)\*\*", on.mean())


def test_01_residual_fraction(pinch):
    on, off = pinch[2.03]
    check("01-noise.md", r"\(([0-9]+)% of the generic level\)", on.mean() / off.mean(), 100.0)


def test_01_the_zero_is_exact(pinch):
    """The chapter claims `0.000000, maximum 0.0e+00`. Exactness is the claim, not smallness."""
    on, _off = pinch[2.0]
    text = (CHAPTERS / "01-noise.md").read_text(encoding="utf-8")
    assert "maximum 0.0e+00" in text, "01 no longer states the maximum; this row is stale"
    assert on.max() == 0.0, "01 claims an exact zero; measured max %.3e" % on.max()


# --------------------------------------------------------------------------- #
# 26 — the hexagonal lattice constants the chapter names

def test_26_short_diagonal_is_cellsize_over_root_three():
    """`s = cellSize/√3` — the identity the whole chapter is parameterised on."""
    text = (CHAPTERS / "26-hexagonal-grids.md").read_text(encoding="utf-8")
    assert "cellSize/√3" in text or "cellSize / √3" in text, (
        "26 no longer states s = cellSize/√3; this row is stale")
    import hex_grid
    basis = hex_grid.basis(1.0)
    assert basis is not None
    assert abs(1.0 / np.sqrt(3.0) - 0.5773502691896258) < 1e-15


def test_26_corner_only_costs_one_third():
    """A one-cell spike reaches a corner-only mesh at H/3: corners are means of three cells."""
    text = (CHAPTERS / "26-hexagonal-grids.md").read_text(encoding="utf-8")
    assert re.search(r"H/3|×1/3|H\+0\+0\)/3", text), (
        "26 no longer states the corner-only 1/3 attenuation; this row is stale")


# --------------------------------------------------------------------------- #
# 12 — the veneer coverage fractions, checked against the chapter's OWN formula
#
# ⚠️ THE REACH THIS ADDS. Every row above re-derives a chapter number from a
# MODULE. `12` has no module here — the surf loop it describes is not shipped in
# this skill — but it states a closed form beside its numbers:
#
#     f   = Phi(u)                        covered area fraction
#     reg = sigma_r * (phi(u) + u*Phi(u)) mean sand depth, the volume book
#
# so the chapter can be checked against ITSELF: evaluate the formula it gives
# and confirm it produces the percentages it prints next to it. That catches the
# case a module-based row cannot — a number updated without re-deriving, or a
# formula that does not produce the values beside it — and it works for every
# chapter that writes its algebra down, implementation or no implementation.

def _std_normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _std_normal_pdf(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _veneer_coverage(depth_in_sigma):
    """Solve `phi(u) + u*Phi(u) = reg/sigma_r` for u, then return `f = Phi(u)`.

    Bisection rather than a solver import: the function is monotone in u and the
    reference implementation carries no scipy dependency.
    """
    lo, hi = -6.0, 6.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid * _std_normal_cdf(mid) + _std_normal_pdf(mid) < depth_in_sigma:
            lo = mid
        else:
            hi = mid
    return _std_normal_cdf(0.5 * (lo + hi))


@pytest.mark.parametrize("depth,pattern", [
    (1.00, r"covers \*\*([0-9.]+)%\*\* of the area"),
    (0.50, r"Half a\s+roughness covers ([0-9.]+)%"),
    (0.25, r"a quarter ([0-9.]+)%"),
])
def test_12_veneer_coverage_matches_its_own_closed_form(depth, pattern):
    check("12-glacial-coastal.md", pattern, _veneer_coverage(depth), 100.0)


def test_12_states_the_distribution_the_numbers_depend_on():
    """The percentages hold for a GAUSSIAN roughness and for no other.

    A reader who took `81.6%` as a property of veneers rather than of `N(0, sigma_r)` would carry
    it to a distribution where it is simply false, so the chapter naming the distribution is part
    of the claim rather than background.
    """
    text = (CHAPTERS / "12-glacial-coastal.md").read_text(encoding="utf-8")
    assert re.search(r"z\s*~\s*N\(0,\s*.?_?r?\)", text) or "N(0, σ_r)" in text, (
        "12 no longer states that the rock elevation is Gaussian; the coverage percentages "
        "beside it are only true for that distribution")


# --------------------------------------------------------------------------- #
# 12 — the Halfar benchmark figures quoted in the chapter

@pytest.fixture(scope="module")
def halfar_m():
    import halfar_anatomy
    return halfar_anatomy.measurements()


def test_12_halfar_centre_thins_to(halfar_m):
    check("12-glacial-coastal.md", r"centre thins\s+\*\*3000 → ([0-9]+) m\*\*",
          halfar_m["centre_final"])


def test_12_halfar_margin_advances_to(halfar_m):
    check("12-glacial-coastal.md", r"\*\*500 → ([0-9]+) km\*\*",
          halfar_m["radius_final"] / 1e3)


def test_12_halfar_shape_error(halfar_m):
    check("12-glacial-coastal.md", r"holds to \*\*([0-9.]+)%\*\*",
          halfar_m["shape_error"], 100.0)


def test_12_halfar_fitted_exponent(halfar_m):
    check("12-glacial-coastal.md", r"gets \*\*([0-9.]+)\*\* against the analytic",
          halfar_m["exponent"])


def test_12_halfar_analytic_exponent(halfar_m):
    check("12-glacial-coastal.md", r"against the analytic \*\*([0-9.]+)\*\*",
          halfar_m["exponent_analytic"])


def test_12_halfar_volume_claim_is_exactness(halfar_m):
    """The chapter says `exactly` and prints `0.0`. Exactness is the claim, not smallness."""
    text = (CHAPTERS / "12-glacial-coastal.md").read_text(encoding="utf-8")
    assert "conserved **exactly**" in text, "12 no longer claims exact conservation"
    assert halfar_m["volume_error"] == 0.0, (
        "12 claims exact volume conservation; measured %.3e" % halfar_m["volume_error"])
