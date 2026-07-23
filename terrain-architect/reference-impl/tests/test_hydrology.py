"""Invariants for the water-surface node (hydrology.py) — water is a substance at a level, so the
checks are physical: the surface never sits below the bed, lakes fill enclosed depressions, rivers
carry depth only in their channels, and the depth tint darkens with depth."""
import numpy as np

import hydrology


def test_surface_never_below_bed():
    rng = np.random.default_rng(0)
    bed = rng.normal(100.0, 20.0, (32, 32))
    area = np.abs(rng.normal(0.0, 1e4, (32, 32)))
    w = hydrology.water_surface(bed, area, 10.0)
    assert np.all(w >= bed - 1e-6)


def test_lake_fills_a_depression():
    n = 41
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bed = ((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / 12.0                 # a bowl, lowest at the centre
    area = np.ones((n, n))
    w = hydrology.water_surface(bed, area, 10.0, channel_area=1e18)      # lakes only, no rivers
    depth = w - bed
    assert depth[n // 2, n // 2] > 0.0                                   # the bowl holds water
    assert depth[0, 0] < 1e-6                                            # the high corner is dry


def test_river_depth_only_in_channels():
    n = 30
    bed = np.tile(np.linspace(100.0, 0.0, n), (n, 1))                    # a planar slope, no pits
    area = np.zeros((n, n))
    area[:, n // 2] = 1e6                                                # one channel down the middle
    w = hydrology.water_surface(bed, area, 10.0, lakes=False, channel_area=1e5, smooth=0.0)
    depth = w - bed
    assert depth[:, n // 2].max() > 0.0                                 # water flows in the channel
    assert depth[:, 0].max() < 1e-6                                     # dry off-channel


def test_depth_tint_darkens_with_depth():
    shallow = hydrology.water_colour(np.array([0.2]))
    deep = hydrology.water_colour(np.array([7.0]))
    assert deep.sum() < shallow.sum()                                   # deeper water is darker
