"""Build guard for `flow_anatomy.py` — the figure for `03`'s D8-versus-MFD choice.

Same contract as `test_anatomy_figures.py`: the figure must build, and — the part that matters —
the CLAIMS it prints must still hold against the routers it draws from. A diagram that illustrates
something the chapter does not say is worse than no diagram, and this one has already been wrong
once in exactly that way.

⚠️ THE FIRST MEASUREMENT SAID THE OPPOSITE OF THE CHAPTER. `flow_anatomy` originally reported a
channel width as the count of cells above half the peak on one row. On a distribution this skewed
almost nothing clears that bar, so it returned 2 cells for D8 against 1 for MFD — the chapter's
claim inverted, printed in bold, in the figure whose entire purpose is that claim. The direction
rows below exist because of it: they assert the SIGN of the difference, which is the thing a
plausible-looking wrong statistic gets backwards.
"""
import numpy as np
import pytest

import flow_anatomy as FA


@pytest.fixture(scope="module")
def dem():
    return FA.terrain()


def test_mfd_needs_more_cells_than_d8_for_half_the_drainage(dem):
    """`03`: D8 converges hard, MFD 'never lets flow fully converge'.

    The sign is the claim. A statistic that gets it backwards is not a tighter measurement of the
    same thing — it is a different thing.
    """
    d8, mfd, _hybrid = FA.routings(dem)
    n_d8 = FA.half_drainage_cells(d8)
    n_mfd = FA.half_drainage_cells(mfd)
    assert n_mfd > n_d8, (
        "MFD (%d cells) should be less concentrated than D8 (%d) at this relief"
        % (n_mfd, n_d8))
    assert n_mfd / n_d8 > 2.0, (
        "the chapter's contrast should be a factor, not a rounding: got %.2fx"
        % (n_mfd / n_d8))


def test_hybrid_sits_between_its_two_parents(dem):
    """The hybrid is a composition, so it cannot be outside the pair it composes."""
    d8, mfd, hybrid = FA.routings(dem)
    n_d8, n_mfd = FA.half_drainage_cells(d8), FA.half_drainage_cells(mfd)
    n_hy = FA.half_drainage_cells(hybrid)
    assert n_d8 <= n_hy <= n_mfd, (
        "hybrid %d is outside [D8 %d, MFD %d]" % (n_hy, n_d8, n_mfd))


def test_the_low_relief_reversal_the_figure_claims():
    """Panel d's whole point: below a few metres of texture the order flips.

    This is the row that would catch the sweep silently losing its crossover — which would leave
    the figure drawing a monotone story while its caption promised a reversal.
    """
    sweep = FA.relief_sweep()
    assert sweep, "the sweep returned nothing"
    flips = [a for (a, d8, mfd) in sweep if d8 >= mfd]
    holds = [a for (a, d8, mfd) in sweep if d8 < mfd]
    assert flips, "no low-relief point where D8 is no better than MFD"
    assert holds, "no high-relief point where D8 concentrates harder"
    assert max(flips) < min(holds), (
        "the reversal is not monotone in relief: D8-worse at %s, D8-better at %s"
        % (sorted(flips), sorted(holds)))


def test_concentration_falls_as_relief_rises():
    """More relief means more convergence, for both routers. A sweep that did not would mean the
    terrain generator, not the routing, was driving the figure."""
    sweep = FA.relief_sweep()
    for idx, name in ((1, "D8"), (2, "MFD")):
        series = [row[idx] for row in sweep]
        assert series[0] > series[-1], (
            "%s should concentrate more at high relief: %s" % (name, series))


def test_the_real_invariants_of_an_accumulation(dem):
    """Every cell carries at least its own area, and no cell carries more than the domain.

    ⚠️ THIS ROW FIRST ASSERTED A CONSERVATION LAW THAT DOES NOT EXIST. It claimed the two
    accumulations must SUM to the same total, on the reasoning that both route one quantity. They
    do not, and cannot: accumulation is cumulative, so each unit of area is counted once in every
    cell downstream of it. A dispersive router threads each unit through more cells, so its sum is
    necessarily larger — MFD's exceeds D8's by 10.9% here, and that excess is not an error but the
    dispersion itself, measured a second way. The invariants that DO hold are these two.
    """
    d8, mfd, _hybrid = FA.routings(dem)
    cellarea = FA.CELLSIZE ** 2
    domain = dem.size * cellarea
    for name, acc in (("D8", d8), ("MFD", mfd)):
        assert acc.min() >= cellarea * (1 - 1e-9), (
            "%s gives a cell less than its own area" % name)
        assert acc.max() <= domain * (1 + 1e-9), (
            "%s gives a cell more than the whole domain" % name)


def test_dispersion_shows_up_in_the_total_as_well(dem):
    """The same claim, from an angle the figure does not draw.

    A second statistic pointing the same way is worth a row: if only the concentration measure
    separated them, the separation could be an artefact of that measure's threshold. This one has
    no threshold at all.
    """
    d8, mfd, _hybrid = FA.routings(dem)
    assert mfd.sum() > d8.sum(), (
        "MFD threads area through more cells, so its accumulation sum must exceed D8's: "
        "%.6g vs %.6g" % (mfd.sum(), d8.sum()))


def test_diagonal_share_is_a_fraction(dem):
    """Guards the `(rec, slope)` unpacking that raised the first time it was written."""
    share = FA.diagonal_share(dem)
    assert 0.0 < share < 1.0, "diagonal share %r is not a fraction" % share


def test_figure_builds_at_the_declared_size():
    pytest.importorskip("PIL", reason="the anatomy figures need Pillow")
    img = FA.build()
    assert img.size[0] == FA.PAD * 2 + FA.COLS * FA.PANEL_W
    assert img.size[1] > FA.TOP + FA.PANEL_H
