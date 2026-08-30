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

import flow
import flow_anatomy as FA
import noise


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


def test_the_hybrid_degenerates_to_each_parent_at_the_limits(dem):
    """The hybrid's two limit cases, which are the property it actually has.

    ⚠️ THIS ROW USED TO SAY SOMETHING FALSE: "the hybrid is a composition, so it cannot be
    outside the pair it composes". That is the SPLICE's property — a per-cell pick between two
    finished fields is trivially bracketed by them — and it is not the router's. The router
    builds a THIRD field, and on this figure's own ramp family it lands outside its parents:
    at 8 m of relief (panel d's reversal point) `half_drainage_cells` gives D8 3192, MFD 3439,
    hybrid 878; at 4 m, 4021 / 3845 / 852. The row survived only by being pinned to one
    fixture, where the ordering happens to hold.

    What is true, exactly and on every DEM, is the pair of limits: drive the channelisation
    threshold below one cell and every cell is channelised from the start, so the hybrid IS
    D8; drive it past the cell count of the domain and nothing ever channelises, so it IS MFD.
    Verified to 0.000e+00 on six random DEMs and the fixture.
    """
    d8, mfd, _hybrid = FA.routings(dem)
    all_d8 = flow.hybrid_accumulation(dem, FA.CELLSIZE, channel_cells=1.0)
    all_mfd = flow.hybrid_accumulation(dem, FA.CELLSIZE, channel_cells=float(dem.size) + 1)
    assert np.allclose(all_d8, d8, rtol=0, atol=0), (
        "at channel_cells <= 1 every cell is channelised, so the hybrid must reproduce D8 "
        "exactly; worst difference %.3e" % np.abs(all_d8 - d8).max())
    assert np.allclose(all_mfd, mfd, rtol=0, atol=0), (
        "above the domain's cell count nothing channelises, so the hybrid must reproduce MFD "
        "exactly; worst difference %.3e" % np.abs(all_mfd - mfd).max())


# The three DEMs the conservation invariant is checked on. The shipped fixture is not enough:
# the bound it replaced was fitted to it and false-failed on the second of these.
def _corner_plane(n=40):
    """A plane tilted to one corner. No pits, one outlet, and every path is a straight run."""
    i, j = np.mgrid[0:n, 0:n].astype(float)
    return -(i + j)


def _ramp(amp, n=120):
    """`relief_sweep`'s DEM at one relief — the family panel d sweeps."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    f = noise.fbm(xx / n * 4.0, yy / n * 4.0, FA.SEED, octaves=6, base=noise.perlin)
    return flow.priority_flood_fill(200.0 * (n - yy) / n + amp * f)


@pytest.mark.parametrize("name", ["fixture", "corner-plane", "ramp-amp-4"])
def test_the_hybrid_conserves_drainage_which_a_splice_does_not(dem, name):
    """The row that separates a routing from a compositing operation.

    ⚠️ THE BOUND HERE WAS FITTED, AND IT FALSE-FAILED A CORRECT ROUTER. It read
    `assert ratio < 1.15` on `hybrid.sum()/d8.sum()`, with the message that a one-pass routing
    "cannot manufacture that much water". On a 40x40 plane tilted to a corner — no pits, no
    flats, nothing pathological — the genuine hybrid scores 1.1958 and the row FIRES, while
    manufacturing no water at all. `acc.sum()` was never a water budget: it counts each cell
    once per downstream cell it reaches, so it grows with PATH LENGTH, and on a smooth plane
    MFD's paths are long.

    The invariant that was meant is exact and needs no constant. Outlets are the cells with no
    strictly-lower 8-neighbour; the routers only look at in-bounds neighbours, so nothing
    leaves the domain and every cell's area must arrive at one of them. `outlet_conservation`
    returns 1.000000000000 for D8, MFD and the hybrid on all three DEMs here — and 1.039 for
    the splice, nine orders of magnitude away.

    The `<= mfd + 0.01` half is kept: it survived every DEM tried, and it is the cheap second
    lock that says the hybrid never disperses harder than the parent it disperses like.
    """
    dem = {"fixture": dem, "corner-plane": _corner_plane(),
           "ramp-amp-4": _ramp(4.0)}[name]
    d8, mfd, hybrid = FA.routings(dem)
    for label, acc in (("D8", d8), ("MFD", mfd), ("hybrid", hybrid)):
        share = FA.outlet_conservation(dem, acc)
        assert abs(share - 1.0) < 1e-9, (
            "%s on %s delivers %.12f of the domain area to its outlets; a one-pass routing "
            "must deliver exactly 1 — water is being created or destroyed"
            % (label, name, share))
    ratio, mfd_ratio = hybrid.sum() / d8.sum(), mfd.sum() / d8.sum()
    assert ratio <= mfd_ratio + 0.01, (
        "the hybrid threads water through more cells than pure MFD (%.3f vs %.3f relative to "
        "D8) on %s — it is compositing finished fields, not routing"
        % (ratio, mfd_ratio, name))


def test_the_splice_the_figure_used_to_draw_is_caught(dem):
    """Prove the conservation row can fail. A guard never seen to fail is not known to be a guard.

    This reconstructs the exact expression panel c shipped with and asserts the row above
    rejects it. If someone "simplifies" `hybrid_accumulation` back into a `np.where`, this is
    what says no.

    ⚠️ PINNED TO THE SHIPPED FIXTURE ON PURPOSE, unlike the invariant it controls. A splice only
    splices where the two fields actually differ across the threshold. On the corner plane D8
    never reaches 60 cells anywhere, so `np.where` picks MFD everywhere and the "splice" IS MFD
    — outlet-conserving, 1.000, and this control would go quiet without anything being wrong.
    The invariant is parametrised over three DEMs; its control has to stay where the defect
    exists.
    """
    d8, mfd, _hybrid = FA.routings(dem)
    cellarea = FA.CELLSIZE * FA.CELLSIZE
    splice = np.where(d8 >= FA.CHANNEL_CELLS * cellarea, d8, mfd)
    share = FA.outlet_conservation(dem, splice)
    assert abs(share - 1.0) > 1e-3, (
        "the splice now delivers %.12f of the domain area to its outlets — it has stopped "
        "manufacturing water, this control has gone quiet, and the conservation row above is "
        "no longer known to be able to fail" % share)
    assert splice.sum() / d8.sum() > 1.15, (
        "the splice no longer inflates the accumulation total (%.3f x D8) — the figure's "
        "quoted 1.58x has moved and the caption is stale" % (splice.sum() / d8.sum()))


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

    (The conservation law that DOES exist is the outlet sum, asserted above. Note it is not the
    one the second sentence of `test_dispersion_shows_up_in_the_total_as_well` used to give: MFD's
    excess is not "dispersion off the domain edge". Nothing leaves the edge — the routers only
    consider in-bounds neighbours — and if water did leave early, MFD's total would be LOWER, not
    higher.)
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


def test_the_hillslope_statistic_is_a_claim_about_THIS_relief_only():
    """⚠️ PINS THE QUALIFICATION THE CHAPTER AND THE CAPTION NOW CARRY.

    `03` and the figure both report "a quarter of the domain is bone dry under D8" and "the
    hybrid is indistinguishable from D8 on concentration". Both are measured on the 28 m ramp
    and both INVERT below about 8 m — the same relief as panel d's order reversal, which is
    exactly the failure panel d exists to prevent anyone repeating.

    So the qualification is asserted rather than trusted to prose: at 8 m, D8 wets nearly
    everything (so there is no dry quarter to find), and the hybrid concentrates several times
    harder than EITHER parent (so "scores as D8" is false there). If either stops being true,
    the qualifying sentences are the stale ones and this row says so.
    """
    dem = _ramp(8.0)
    d8, mfd, hybrid = FA.routings(dem)
    wet = FA.hillslope_wetted(d8)
    assert wet > 0.85, (
        "D8 wets only %.1f%% of cells at 8 m relief; the chapter's qualification says the "
        "'quarter of the domain is dry' claim does NOT hold here, and it now does" % (100 * wet))
    n_d8, n_mfd, n_hy = (FA.half_drainage_cells(a) for a in (d8, mfd, hybrid))
    assert n_hy < 0.5 * min(n_d8, n_mfd), (
        "at 8 m relief the hybrid concentrates into %d cells against D8's %d and MFD's %d; the "
        "qualification claims it is several times harder than either parent here, and it is "
        "no longer" % (n_hy, n_d8, n_mfd))


def test_diagonal_share_is_a_fraction(dem):
    """Guards the `(rec, slope)` unpacking that raised the first time it was written."""
    share = FA.diagonal_share(dem)
    assert 0.0 < share < 1.0, "diagonal share %r is not a fraction" % share


def test_figure_builds_at_the_declared_size():
    pytest.importorskip("PIL", reason="the anatomy figures need Pillow")
    img = FA.build()
    assert img.size[0] == FA.PAD * 2 + FA.COLS * FA.PANEL_W
    assert img.size[1] > FA.TOP + FA.PANEL_H
