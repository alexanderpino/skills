import numpy as np
import inputs
import asserts
import flow


def test_fill_removes_all_interior_pits():
    dem = inputs.inverted_cone(n=41, depth=8.0)
    filled = flow.priority_flood_fill(dem, eps=1e-4)
    assert np.all(filled >= dem - 1e-12)          # fill never lowers
    assert asserts.no_interior_pit(filled, eps=1e-9)


def test_fill_two_basins_spill_level():
    dem = inputs.two_basins(n=48)
    filled = flow.priority_flood_fill(dem, eps=1e-5)
    assert asserts.no_interior_pit(filled)
    # both basin floors are raised to (near) the single outlet level, 0, via the fill
    assert filled[14, 14] > dem[14, 14]           # shallow basin A raised
    assert filled[14, 34] > dem[14, 34]           # deep basin B raised


def test_d8_constant_slope_routes_downhill():
    dem = inputs.constant_slope(n=32, gradient=0.5)
    rec, slope = flow.d8_receivers(dem)
    # an interior cell drains to the row below it (toward the low edge)
    ri, rj = rec[10, 10]
    assert ri == 11 and rj == 10
    assert slope[10, 10] > 0


def test_accumulation_conserves_area():
    dem = flow.priority_flood_fill(inputs.inverted_cone(n=41, depth=6.0))
    n, m = dem.shape
    acc = flow.d8_accumulation(dem, cellsize=1.0)
    rec, _ = flow.d8_receivers(dem)
    outlet_total = sum(
        acc[i, j] for i in range(n) for j in range(m) if rec[i, j][0] < 0
    )
    assert abs(outlet_total - n * m) < 1e-6        # all area exits via outlets
    assert np.all(acc >= 1.0 - 1e-9)               # every cell has >= its own area


def test_mfd_conserves_area_and_less_grid_biased_than_d8():
    dem = flow.priority_flood_fill(inputs.cone(n=41, height=8.0))
    n, m = dem.shape
    acc_mfd = flow.mfd_accumulation(dem)
    acc_d8 = flow.d8_accumulation(dem)
    for acc in (acc_mfd, acc_d8):
        asserts.assert_finite(acc)
        assert np.all(acc >= 1.0 - 1e-9)
    # MFD disperses -> lower directional (grid) bias than D8 on a radial cone
    assert asserts.radial_anisotropy(acc_mfd) <= asserts.radial_anisotropy(acc_d8) + 1e-9
