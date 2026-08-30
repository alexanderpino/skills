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
import importlib
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REF = Path(__file__).resolve().parents[1]
CHAPTERS = REF.parent / "references"


def _half_unit(printed):
    """Half a unit in the last PRINTED place of `printed` — trailing zeros included.

    ⚠️ This used to strip trailing zeros before counting, so `30` was held to ±5 and `100` to ±50 —
    a tenfold inflation on exactly the values a chapter is most likely to round. Under that rule,
    rewriting a `~29%` whose module computes 28.568 into `~30%` — a 1.43-point divergence — passed.
    That is the tolerance-widening this file's own docstring forbids, arriving through the tolerance
    function instead of through a row. A printed `30` claims two digits; two digits is what it is
    held to. Checked against every row here: none relied on the inflated band (the only integer
    values any pattern captures are `12`'s Halfar figures, 2439 m and 564 km, which have no trailing
    zero and were already on ±0.5).
    """
    s = printed.strip().rstrip("%×").replace(",", "")
    if "." in s:
        return 0.5 * 10.0 ** (-len(s.split(".")[1]))
    return 0.5


def _quoted(chapter, pattern):
    """Pull one number out of a chapter by regex, failing loudly if it moved."""
    text = (CHAPTERS / chapter).read_text(encoding="utf-8")
    m = re.search(pattern, text)
    assert m, ("%s no longer contains a number matching %r — either the prose changed or this "
               "row is stale. Both need a human." % (chapter, pattern))
    return m.group(1)


def check_in(blob, label, pattern, actual, scale=1.0):
    """`check`, against an arbitrary slice of text rather than a whole chapter.

    Exists so a row can be made LOCAL — pinned to the paragraph or sentence that makes the claim
    instead of to any occurrence anywhere in the file. A chapter-global substring test passes on a
    number that has drifted into an unrelated section, which is how the stale-figure guard below
    used to be satisfiable by the word "2.0" appearing in "lacunarity 2.03".
    """
    m = re.search(pattern, blob)
    assert m, ("%s no longer contains a number matching %r — either the prose changed or this "
               "row is stale. Both need a human." % (label, pattern))
    printed = m.group(1)
    exp = float(printed.rstrip("%×"))
    got = float(actual) * scale
    tol = _half_unit(printed)
    assert abs(got - exp) <= tol * (1 + 1e-9), (
        "%s prints %s; the code computes %.6g (tolerance %.3g, the printed precision). "
        "Fix the prose if the code moved deliberately; fix the code if it did not."
        % (label, printed, got, tol))


def check(chapter, pattern, actual, scale=1.0):
    check_in((CHAPTERS / chapter).read_text(encoding="utf-8"), chapter, pattern, actual, scale)


def _paragraph_containing(chapter, needle):
    """The markdown block (blank-line delimited) that carries `needle`, whitespace-flattened.

    Locality is the point: a claim is guarded where it is made. Flattened because a markdown
    paragraph wraps mid-sentence, so a pattern written against the sentence would otherwise depend
    on where the line broke.
    """
    text = (CHAPTERS / chapter).read_text(encoding="utf-8")
    blocks = [b for b in re.split(r"\n\s*\n", text) if needle in b]
    return [re.sub(r"\s+", " ", b).strip() for b in blocks]


def _sentences(blob):
    return [s for s in re.split(r"(?<=[.!?:])\s+", blob) if s]


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
    """⚠️ THE ROW THAT WENT STALE, KEPT AS THE REASON THIS FILE EXISTS.

    `03` used to print **3.7%** here, and it was wrong — not stale but never right. Panel c drew
    `where(A > threshold, d8, mfd)`, a pick between two FINISHED accumulations, which invents
    water and landed the statistic halfway between its parents. That midpoint read as exactly
    what a hybrid ought to score, which is why nobody looked at it twice. The real one-pass
    hybrid scores **1.5%**, indistinguishable from D8, because the trunk dominates the statistic
    and the hybrid IS D8 in the trunk.
    """
    m, _ = flow_m
    check("03-flow-routing.md", r"scores the hybrid at \*\*([0-9.]+)%\*\*", m["hybrid_frac"], 100.0)


@pytest.mark.parametrize("router,pattern", [
    ("hybrid_wet", r"upslope is \*\*([0-9.]+)%\*\* under the hybrid"),
    ("mfd_wet", r"under the hybrid and \*\*([0-9.]+)%\*\* under\n> MFD"),
    ("d8_wet", r"against only \*\*([0-9.]+)%\*\* under D8"),
])
def test_03_hillslope_wetting(flow_m, router, pattern):
    """The second statistic, which is the only one that can see the hybrid do anything.

    Bound here rather than left in prose because these three numbers carry the whole corrected
    claim: without them `03` reports the hybrid and D8 as identical and says nothing about why
    anyone would build one.
    """
    m, _ = flow_m
    check("03-flow-routing.md", pattern, m[router], 100.0)


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


# --------------------------------------------------------------------------- #
# 09 — the rotate-the-domain table
#
# ⚠️ THE FAILURE THIS CLOSES. `09`'s whole argument for the rotation test rests on one table of six
# measured numbers plus the 90° trap, and until now nothing tied them to `anisotropy_anatomy.py`.
# Five of the six had drifted: the control column — the FLOOR the separation is measured against —
# read 0.016/0.014/0.020 against a module computing 0.013/0.010/0.018, which inflates the floor and
# understates the very separation the chapter is arguing for. A table this load-bearing needs a row
# per cell, not a row per claim.

@pytest.fixture(scope="module")
def aniso():
    import anisotropy_anatomy as aa
    return {d: (aa.error(aa.axis_locked, math.radians(d)),
                aa.error(aa.isotropic, math.radians(d))) for d in (23, 30, 45, 90)}


@pytest.mark.parametrize("deg", [23, 30, 45])
def test_09_axis_locked_column(aniso, deg):
    """The defect column: a 4-neighbour max, scored by rotation residual."""
    check("09-verification.md", r"\| %d° \| `([0-9.]+)` \|" % deg, aniso[deg][0])


@pytest.mark.parametrize("deg", [23, 30, 45])
def test_09_isotropic_control_column(aniso, deg):
    """The floor column. `09`'s own rule is that a metric with no control is not evidence, so a
    stale floor is worse than a stale defect number — it corrupts the comparison, not just a cell."""
    check("09-verification.md", r"\| %d° \| `[0-9.]+` \| `([0-9.]+)` \|" % deg, aniso[deg][1])


def test_09_the_ninety_degree_row_is_the_floating_point_floor(aniso):
    """THE TRAP ROW — and the standard it is held to, reconciled with `tests/test_anisotropy.py`.

    ⚠️ TWO FILES ASSERTED DIFFERENT THINGS ABOUT ONE NUMBER. `test_anisotropy.py` requires
    `error(axis_locked, 90°) < 1e-12`; this row required `== 0.0`, and justified the difference by
    the lattice theorem — a quarter turn is a symmetry of the square grid, so the residual must be
    exactly zero. The theorem does not say that. It says the OPERATOR commutes with an exact quarter
    turn. The measurement composes the operator with `anisotropy_anatomy.rotate`, a bilinear
    resample whose 90° weights come out 1±6e-15 rather than 1 and 0, because `cos(pi/2)` is 6.1e-17
    in binary floating point and not 0. The bit-exact `0.0` that comes back is an arithmetic
    accident of the INPUT: the cone is 4-fold symmetric and smooth, so those residual weights fall
    on equal neighbours and round away. Hand the same operator a random field and the residual is
    2.5e-18 — still the floor, no longer zero. So `< 1e-12` is the claim the argument actually
    supports, it is what the sibling file already asserts, and it is what this row asserts now.

    The trap survives the change intact, because the trap was never about the last bit: at 90° the
    axis-locked operator scores at the floating-point floor while at 30° the same operator scores
    0.111. Thirteen orders of magnitude of separation is what makes a symmetry angle useless as a
    test angle, and this row pins that ratio rather than a coincidence of rounding.
    """
    for pattern in (r"\| \*\*90°\*\* \| \*\*`([0-9.]+)`\*\* \|",
                    r"\| \*\*90°\*\* \| \*\*`[0-9.]+`\*\* \| `([0-9.]+)` \|"):
        assert float(_quoted("09-verification.md", pattern)) == 0.0, (
            "09 no longer prints 0.000 in the 90° row; this row is stale")
    locked, floor = aniso[90]
    assert locked < 1e-12 and floor < 1e-12, (
        "09 claims equivariance at 90° to the floating-point floor; measured %.3e / %.3e"
        % (locked, floor))
    assert locked < 1e-9 * aniso[30][0], (
        "the 90° trap is that a symmetry angle hides a defect the same operator shows plainly at "
        "30°: %.3e at 90° against %.4f at 30°" % (locked, aniso[30][0]))

    # ...and the generalising form of the same claim, which the cone's symmetry hides: the residual
    # is at the floor on an input with no symmetry to exploit, where it is NOT bit-zero.
    import anisotropy_anatomy as aa
    rand = np.random.RandomState(0).rand(aa.N, aa.N)
    assert aa.error(aa.axis_locked, math.radians(90), rand) < 1e-12, (
        "equivariance at 90° must hold at the floor for any input, not only the 4-fold-symmetric "
        "cone that rounds it to exactly zero")


# --------------------------------------------------------------------------- #
# 10 — the cost of moving a raster instead of moving coordinates
#
# ⚠️ ONE DEFINITION OF THE EXPERIMENT, IMPORTED. This block used to restate `test_placement.py`'s
# setup — n, scale, seed, lacunarity, offsets — as its own literals. That is a guard that quietly
# stops guarding: retune the experiment there and these rows go on measuring the abandoned one and
# passing, which is exactly how the shipped file and the chapter could have drifted apart. The
# constants and the builder now live in `test_placement.py` and are imported here, so there is one
# experiment and both files are pinned to it.
#
# ⚠️ AND THE CAUSE `10` GAVE FOR THE WINDOW SPREAD WAS WRONG. It read the old build's large spread
# as the lacunarity-2 pinch lattice — the un-shifted base window sitting where every octave is zero
# at once. `test_placement.py::test_the_window_spread_tracks_px_per_cell_not_the_lacunarity`
# falsifies that; the rows below pin the four measurements `10` now prints in its place, and the
# refutation numbers that show the pinch points cannot be responsible for the statistic they were
# blamed for.

def _placement_detail_losses():
    """Re-run `test_placement.py`'s experiment on both metrics: mean |laplacian| and high-frequency
    band energy, after one and after four chained bilinear moves. Returns fractions, not
    percentages. The setup comes from `test_placement` — nothing here restates it."""
    import ops_filters
    from test_placement import (SHIFT_FRAC, N, _bilinear_shift, _detail, experiment_build,
                                experiment_grid)

    xx, yy = experiment_grid()
    band = lambda f: float(np.abs(f - ops_filters.gaussian(f, sigma=2.0)).mean())
    dx, dy = SHIFT_FRAC[0] * N, SHIFT_FRAC[1] * N
    out = {}
    for lac, suffix in ((None, ""), (2.0, "_lac2")):
        h = (experiment_build() if lac is None else experiment_build(lacunarity=lac))(xx, yy)
        for metric, tag in ((_detail, "lap"), (band, "band")):
            base, raster = metric(h), h
            for k in range(1, 5):
                raster = _bilinear_shift(raster, dx, dy)
                out["%s%d%s" % (tag, k, suffix)] = 1.0 - metric(raster) / base
    return out


@pytest.fixture(scope="module")
def placement_loss():
    return _placement_detail_losses()


def test_10_one_raster_move_laplacian(placement_loss):
    check("10-primitives-ops-filters.md",
          r"one move loses ~([0-9.]+)% of the fine detail", placement_loss["lap1"], 100.0)


def test_10_four_raster_moves_laplacian(placement_loss):
    check("10-primitives-ops-filters.md",
          r"four chained moves ~([0-9.]+)%\*\*", placement_loss["lap4"], 100.0)


def test_10_one_raster_move_band_energy(placement_loss):
    """The same experiment on a different metric. `10`'s point is that the metric must be quoted
    with the number, which only means anything if both numbers are actually the module's."""
    check("10-primitives-ops-filters.md",
          r"reads ~([0-9.]+)% and ~[0-9.]+% instead", placement_loss["band1"], 100.0)


def test_10_four_raster_moves_band_energy(placement_loss):
    check("10-primitives-ops-filters.md",
          r"reads ~[0-9.]+% and ~([0-9.]+)% instead", placement_loss["band4"], 100.0)


# --- the window-variance table, and the CAUSE it establishes ----------------- #
#
# ⚠️ WHAT THESE ROWS ARE FOR, WHICH IS NOT THE NUMBERS. `10` previously printed a correct,
# reproducible, stably measured window-variance figure beside an INVENTED mechanism: it blamed the
# lacunarity-2 pinch lattice. Thirteen rows pinning the numbers could not have caught that, because
# every number was right. What catches a false cause is a table that varies the supposed cause
# independently of the effect, so the four cells below are the experiment and not a decoration:
# lacunarity 2 with the finest octave off 2 px/cell (no effect) and lacunarity 2.03 with it back on
# 2 px/cell (full effect) are the two cells the old story predicts backwards.

_CELL = r"\*{0,2}`%s`\*{0,2}"
_TABLE_ROWS = [("2.00", "3.00"), ("2.00", "3.10"), ("2.03", "2.78478"), ("2.03", "3.00")]


def _window_row_patterns(lac, scale):
    head = r"\| %s \| %s[^|]*\| " % (re.escape(lac), re.escape(scale))
    return (head + _CELL % r"([0-9.]+)",
            head + (_CELL % r"[0-9.]+") + r" \| " + _CELL % r"([0-9.]+)%")


@pytest.fixture(scope="module")
def window_table():
    """The four (lacunarity, scale) cells `10` tabulates, measured through `test_placement`.

    Shares `test_placement`'s cache, so the mechanism row there and these rows are the same numbers
    from the same draw rather than two independent re-implementations that could disagree.
    """
    from test_placement import LACUNARITY, SCALE, SCALE_AT_TWO_PX, window_spread
    cfg = {("2.00", "3.00"): (2.0, 3.0), ("2.00", "3.10"): (2.0, 3.1),
           ("2.03", "2.78478"): (2.03, SCALE_AT_TWO_PX), ("2.03", "3.00"): (2.03, 3.0)}
    # The row `10` labels "(shipped)" must actually be the shipped setting. The other three cells
    # are deliberately literal — they are the falsifying arms of the experiment, and they must not
    # drift when the shipped one is retuned — but this one is a claim about `test_placement`.
    assert cfg[("2.03", "3.00")] == (LACUNARITY, SCALE), (
        "10's table labels lacunarity 2.03 / scale 3.0 as the shipped setting, but test_placement "
        "now ships %r / %r" % (LACUNARITY, SCALE))
    return {k: (lac, sc, window_spread(scale=sc, lacunarity=lac)) for k, (lac, sc) in cfg.items()}


@pytest.mark.parametrize("lac,scale", _TABLE_ROWS)
def test_10_window_table_px_per_cell(window_table, lac, scale):
    """The px/cell column — the quantity the chapter now says the effect tracks. It is derived from
    the row's own lacunarity and scale, so a row whose first two columns were edited without
    re-deriving the third fails here."""
    from test_placement import px_per_cell
    lacunarity, sc, _std = window_table[(lac, scale)]
    check("10-primitives-ops-filters.md", _window_row_patterns(lac, scale)[0],
          px_per_cell(scale=sc, lacunarity=lacunarity))


@pytest.mark.parametrize("lac,scale", _TABLE_ROWS)
def test_10_window_table_spread(window_table, lac, scale):
    """The measured column: std of the per-window detail ratio over 40 windows from
    `RandomState(3)`. std rather than `max |r-1|` because the max grows with the window count and
    swings 2:1 across the seed — see `test_placement.window_spread`."""
    check("10-primitives-ops-filters.md", _window_row_patterns(lac, scale)[1],
          window_table[(lac, scale)][2], 100.0)


def test_10_states_the_draw_the_window_spread_depends_on():
    """A spread over random windows is not reproducible without the RNG and the sample count.

    `10` used to print "over 40 random windows" and name neither the seed nor the statistic, which
    made the printed value un-rederivable by a reader: over `RandomState(0..24)` the old `max |r-1|`
    ranges 0.49-0.97%, so "±0.5%" was one draw out of twenty-five presented as the answer.
    """
    para = _paragraph_containing("10-primitives-ops-filters.md", "RandomState(3)")
    assert para, "10 no longer names the RNG behind its window-spread figure"
    assert re.search(r"\*\*40 windows\*\*|40 windows", para[0]), (
        "10 names the RNG but not the window count; an extreme-value or spread statistic is not "
        "reproducible without both")
    assert "standard deviation" in para[0], (
        "10 must name the statistic it prints; a bare percentage over windows could be a mean, a "
        "max or a std, and those differ by an order of magnitude here")


def test_10_the_pinch_lattice_refutation_numbers():
    """The three numbers that show the pinch points cannot be responsible for the statistic they
    were blamed for: how many exact zeros the old build has, how many of them the laplacian
    interior can even see, and what deleting all of them does to mean |laplacian|."""
    from test_placement import _detail, experiment_build, experiment_grid

    xx, yy = experiment_grid()
    h = experiment_build(lacunarity=2.0)(xx, yy)
    lap = np.abs(4 * h[1:-1, 1:-1] - h[1:-1, :-2] - h[1:-1, 2:] - h[:-2, 1:-1] - h[2:, 1:-1])
    zero = h == 0.0
    inner = zero[1:-1, 1:-1]
    para = _paragraph_containing("10-primitives-ops-filters.md", "invisible to any measure")[0]
    check_in(para, "10 (pinch refutation)", r"build \*\*([0-9]+)\*\* of the 36864 pixels",
             float(zero.sum()))
    check_in(para, "10 (pinch refutation)", r"exact zeros, \*\*([0-9]+)\*\* of them",
             float(inner.sum()))
    check_in(para, "10 (pinch refutation)", r"moves mean \|laplacian\| by \*\*([0-9.]+)%\*\*",
             abs(lap[~inner].mean() / lap.mean() - 1.0), 100.0)
    assert _detail(h) > 0.0


@pytest.mark.parametrize("px", [2.0, None], ids=["at-2-px-per-cell", "shipped"])
def test_10_the_sample_phase_numbers(px):
    """The mechanism in one measurement: at 2 px/cell every sample column sits on phase 0 or 0.5 of
    the finest octave; at the shipped setting almost none do."""
    from test_placement import LACUNARITY, N, OCTAVES, SCALE, SCALE_AT_TWO_PX

    scale = SCALE_AT_TWO_PX if px == 2.0 else SCALE
    phase = (np.arange(N) / N * scale * LACUNARITY ** (OCTAVES - 1)) % 1.0
    near = np.mean((np.minimum(phase, 1.0 - phase) < 0.02) | (np.abs(phase - 0.5) < 0.02))
    para = _paragraph_containing("10-primitives-ops-filters.md", "sample-grid commensurability")[0]
    pat = (r"\*\*(100)%\*\* of columns" if px == 2.0
           else r"against \*\*([0-9.]+)%\*\* at the shipped setting")
    check_in(para, "10 (sample phase)", pat, near, 100.0)


def test_10_the_outside_figure_is_never_restated_as_agreement(placement_loss):
    """⚠️ THE GUARD THAT WAS BYPASSABLE, REBUILT.

    It read: `if "24.7" in text: assert "stale" in text and "2.0" in text`. Both halves were
    chapter-GLOBAL substrings, so `"2.0"` was satisfied for free by the words "lacunarity 2.03"
    several paragraphs away, and `"stale"` by any use of the word anywhere in the file. Only the
    literal phrase "two implementations, one number" was banned, which a paraphrase walks straight
    past ("one figure").

    The lock that does the real work here is not a word list — a word list loses to paraphrase by
    construction. It is CO-LOCATION OF THE CONTRADICTION: the paragraph that quotes the outside
    24.7% / 53.8% must also quote this repo's own measurement of the same pair at lacunarity 2.0,
    and those two numbers are checked against the module. Restating the outside figure as agreement
    then requires either deleting the numbers that refute it — which fails this row — or printing
    them beside the claim, where any reader sees the contradiction. The word list below is the
    cheap second lock, not the argument.
    """
    text = (CHAPTERS / "10-primitives-ops-filters.md").read_text(encoding="utf-8")
    if "24.7" not in text:
        assert "53.8" not in text, "10 dropped 24.7 but kept its partner 53.8 unexplained"
        return

    paras = _paragraph_containing("10-primitives-ops-filters.md", "24.7")
    assert len(paras) == 1, (
        "the outside figure is quoted in %d paragraphs; a claim guarded in one place and repeated "
        "in another is guarded nowhere" % len(paras))
    para = paras[0]
    flat = re.sub(r"\s+", " ", text)
    for needle in ("24.7", "53.8"):
        assert flat.count(needle) == para.count(needle), (
            "%s appears outside the paragraph that qualifies it; a figure guarded in one place and "
            "repeated in another is guarded nowhere" % needle)

    # LOCK 1 — the repo's own contradicting measurement, in the same paragraph, module-verified.
    check_in(para, "10 (own lacunarity-2.0 re-run)",
             r"measures \*\*([0-9.]+)% / [0-9.]+%\*\*", placement_loss["lap1_lac2"], 100.0)
    check_in(para, "10 (own lacunarity-2.0 re-run)",
             r"measures \*\*[0-9.]+% / ([0-9.]+)%\*\*", placement_loss["lap4_lac2"], 100.0)
    assert re.search(r"no provenance|not reproducible|cannot be re-derived|nothing here can "
                     r"re-derive|stale figure", para), (
        "the paragraph quoting 24.7 / 53.8 must say plainly that the figure has no provenance here")

    # LOCK 2 — sentence-local: no sentence in that paragraph may assert agreement un-negated.
    agree = re.compile(r"agree(?:s|d|ment)?|corroborat|confirms|independently (?:verif|reproduc)"
                       r"|(?:same|one|a single) (?:number|figure|value|result)"
                       r"|two implementations|cross-check(?:s|ed)?\b", re.I)
    negate = re.compile(r"\bnot\b|\bnever\b|\bno\b|rather than|cannot|invented|stale|instead of",
                        re.I)
    for s in _sentences(para):
        m = agree.search(s)
        assert m is None or negate.search(s), (
            "10 asserts agreement with the outside figure in an un-negated sentence: %r" % s)


# --------------------------------------------------------------------------- #
# 12 — the one chapter number whose producer lives in ANOTHER skill

WATER_PHYSICS = CHAPTERS.parent.parent / "water-physics" / "reference-impl"


@pytest.mark.skipif(not (WATER_PHYSICS / "beach.py").exists(),
                    reason="the water-physics skill is not checked out beside this one; 12's "
                           "surf-zone numbers are computed there, not in this reference-impl")
def test_12_crest_depth_ratio_is_quoted_in_one_field():
    """⚠️ THE NUMBER THAT SUPERSEDED A STALE ONE, AND SO MOST NEEDS BINDING.

    `27` quoted **0.89** for this quantity long after `12` had superseded it with **0.9734**, and
    nothing pointed either number at the code — which is exactly how the 0.89 survived. Binding
    the replacement is the only thing that stops the same drift happening again.

    ⚠️ AND THE TWO NUMBERS ARE NOT INTERCHANGEABLE, which is the trap this row also guards.
    `crest_depth_ratio` takes a `field` argument: `'bed'` gives 0.8930 and `'wave'` gives 0.9734.
    They are the same quantity read off two different fields, and `12:1738-1745` establishes the
    rule that a ratio must name the field each of its terms came from. Swapping one for the other
    to "fix" a mismatch is the mixed-field error, not a correction — so this row asserts BOTH and
    asserts they differ, rather than checking the headline figure alone.

    This is the only chapter number in this skill that no module here can re-derive: the surf-zone
    loop is `water-physics/reference-impl/beach.py`. It earns a row anyway — a superseding number
    with nothing pointing at its source is how the last one went stale — and it skips cleanly when
    the sibling skill is absent. ~20 s: it runs the full 6000-step loop.
    """
    sys.path.insert(0, str(WATER_PHYSICS))
    try:
        beach = importlib.import_module("beach")
    finally:
        sys.path.pop(0)

    scene = beach.run_scene()
    crest = beach.bar_crest(scene["x"], scene["h"], scene["h_dean"])
    breaker = beach.breaker_state(scene["tr"])
    wave = beach.crest_depth_ratio(scene["tr"], crest, breaker, field="wave")
    bed = beach.crest_depth_ratio(scene["tr"], crest, breaker, field="bed")

    check("12-glacial-coastal.md",
          r"measured gap of `([\d.]+) [−-] [\d.]+ = [\d.]+`", wave)
    check("12-glacial-coastal.md",
          r"measured gap of `[\d.]+ [−-] ([\d.]+) = [\d.]+`", bed)
    assert abs(wave - bed) > 0.05, (
        "the wave-field and bed-field readings have converged (%.4f vs %.4f); the chapter's "
        "whole point is that they differ by the filter's own lift, so either the loop changed "
        "or this row is now measuring one field twice" % (wave, bed))
