"""INVARIANT checks for the illustrative sims (12, 19). These are NOT decisive oracles — the
processes have none, which is why they're segregated. We assert only what must hold for the
code not to be grossly broken: the field stays finite, the mass/energy budget closes, and
trends go the right way. Passing does not certify the numbers, only that nothing exploded.
"""
import numpy as np
import inputs
import sims_illustrative as S


# ---- lava: mass conservation is the sim's own 09 check (19) ----
def test_lava_conserves_mass_and_freezes():
    bed = inputs.constant_slope(41, gradient=0.2)          # a ramp so lava runs downhill
    bed_out, L, T, budget = S.lava_flow(bed, source=(20, 20), steps=60, cool=150.0)
    assert np.all(np.isfinite(bed_out)) and np.all(np.isfinite(L)) and np.all(np.isfinite(T))
    assert abs(budget["erupted"] - budget["molten"] - budget["frozen"]) < 1e-6 * budget["erupted"]
    assert budget["frozen"] > 0.0                          # some lava cooled below solidus & froze


def test_lava_flows_downhill():
    bed = inputs.constant_slope(41, gradient=0.2)          # row 0 highest -> downhill = +row
    bed_out, L, _, _ = S.lava_flow(bed, source=(20, 20), steps=60, cool=150.0)
    deposit = (bed_out - bed) + L
    rows = np.arange(41)[:, None] * np.ones((1, 41))
    com_row = (deposit * rows).sum() / deposit.sum()
    assert com_row >= 20.0                                 # centre of mass is at/below the vent


# ---- glacier: the SIA transport conserves ice (12) ----
def _ice_cap(n=41, peak=200.0):
    c = (n - 1) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    return peak * np.exp(-((xx - c) ** 2 + (yy - c) ** 2) / (2 * (n / 6.0) ** 2))


def test_glacier_transport_conserves_ice_and_spreads():
    bed = inputs.flat(41)
    H0 = _ice_cap(41, peak=200.0)
    H = S.glacier_sia(bed, H0, steps=1, beta=0.0, cellsize=100.0, dt=5.0e6)
    assert np.all(np.isfinite(H)) and H.min() >= -1e-9
    assert abs(H.sum() - H0.sum()) < 1e-6 * H0.sum()       # divergence form conserves ice
    assert H.max() < H0.max()                              # the cap spread (peak lowered)


def test_glacier_mass_balance_grows_ice_above_ela():
    bed = inputs.cone(41, height=1000.0)                   # a peak
    H = S.glacier_sia(bed, inputs.flat(41), steps=1, beta=0.3, ela=500.0, b_max=5.0,
                      cellsize=100.0, dt=50.0)
    assert H.max() > 0.0                                   # ice accumulated above the ELA


# ---- coastal: the cliff retreats landward (12) ----
def test_coastal_erosion_removes_mass_monotonically():
    """The guaranteed invariant: the wave notch removes mass each step and the thermal collapse
    only redistributes it, so total mass strictly falls (the coast erodes). Where that mass ends
    up is the un-oracled part — hence this checks the budget, not the morphology."""
    h = inputs.constant_slope(48, gradient=0.3) * 10.0     # a sloping coast, ~0..141 m
    sea = 20.0
    m0 = float(h.sum())
    m5 = float(S.coastal_retreat(h, sea, steps=5, k_coast=1.0, notch=1.5).sum())
    h15 = S.coastal_retreat(h, sea, steps=15, k_coast=1.0, notch=1.5)
    assert np.all(np.isfinite(h15))
    assert m5 < m0                                         # wave erosion removed mass
    assert float(h15.sum()) < m5                           # more steps -> more removed


# ---- tides: an authored oscillation; the solid is never touched (12) ----
def test_tide_level_is_bounded():
    t = np.linspace(0.0, 25.0, 200)
    lvl = S.tide_level(t, mean_sea_level=0.0, tidal_range=4.0)
    assert lvl.max() <= 2.0 + 1e-9 and lvl.min() >= -2.0 - 1e-9


def test_high_tide_covers_low_tide_and_intertidal_between():
    solid = inputs.constant_slope(32, gradient=0.5) * 4.0
    high = S.tide_level(12.42 / 4, 0.0, 4.0)               # +2
    low = S.tide_level(3 * 12.42 / 4, 0.0, 4.0)            # -2
    wet_high = S.wet_mask(solid, high)
    wet_low = S.wet_mask(solid, low)
    assert np.all(wet_low <= wet_high)                     # low-tide wet implies high-tide wet
    inter = S.intertidal_mask(solid, 0.0, 4.0)
    assert np.array_equal(inter, wet_high & ~wet_low)      # the strip swept by the tide
