"""Invariants for the water-surface node (hydrology.py) — water is a substance at a level, so the
checks are physical: the surface never sits below the bed, lakes fill enclosed depressions, rivers
carry depth only in their channels, and the depth tint darkens with depth."""
import numpy as np

import hydrology


def test_surface_never_below_bed():
    rng = np.random.default_rng(0)
    bed = rng.normal(100.0, 20.0, (32, 32))
    Q = np.abs(rng.normal(0.0, 5.0, (32, 32)))                          # discharge, m³/s
    w = hydrology.water_surface(bed, 10.0, Q)
    assert np.all(w >= bed - 1e-6)


def test_discharge_from_area_scales_with_rain():
    area = np.array([[0.0, 100.0], [1e4, 1e6]])
    Q = hydrology.discharge_from_area(area, rain=2e-6)
    assert np.allclose(Q, area * 2e-6)                                  # Q = rain · upstream area


def test_lake_fills_a_depression():
    n = 41
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bed = ((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / 12.0                 # a bowl, lowest at the centre
    Q = np.zeros((n, n))
    w = hydrology.water_surface(bed, 10.0, Q, q_channel=1e18)            # lakes only, no rivers
    depth = w - bed
    assert depth[n // 2, n // 2] > 0.0                                   # the bowl holds water
    assert depth[0, 0] < 1e-6                                            # the high corner is dry


def test_river_depth_only_in_channels():
    n = 30
    bed = np.tile(np.linspace(100.0, 0.0, n), (n, 1))                    # a planar slope, no pits
    Q = np.zeros((n, n))
    Q[:, n // 2] = 50.0                                                  # one channel down the middle
    w = hydrology.water_surface(bed, 10.0, Q, lakes=False, q_channel=10.0, smooth=0.0)
    depth = w - bed
    assert depth[:, n // 2].max() > 0.0                                 # water flows in the channel
    assert depth[:, 0].max() < 1e-6                                     # dry off-channel


def test_depth_tint_darkens_with_depth():
    shallow = hydrology.water_colour(np.array([0.2]))
    deep = hydrology.water_colour(np.array([7.0]))
    assert deep.sum() < shallow.sum()                                   # deeper water is darker


def test_water_over_land_is_translucent_by_depth():
    """Water is a translucent stage: shallow water shows the bed through; deep water hides it under blue."""
    land = np.zeros((3, 3, 3)) + np.array([120.0, 100.0, 80.0])       # a soil-brown bed
    shallow = hydrology.water_over_land(land, np.full((3, 3), 0.1))
    deep = hydrology.water_over_land(land, np.full((3, 3), 25.0))
    assert np.linalg.norm(shallow[0, 0] - land[0, 0]) < np.linalg.norm(deep[0, 0] - land[0, 0])
    assert deep[0, 0, 2] > deep[0, 0, 0]                              # deep water reads blue, not brown
    assert np.allclose(hydrology.water_over_land(land, np.zeros((3, 3))), land)   # dry land unchanged
