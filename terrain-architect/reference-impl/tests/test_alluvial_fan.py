"""Invariant tests for the alluvial-fan generator (landforms.alluvial_fan / 16, Blair & McPherson 1994).

A fan is a DEPOSITIONAL landform stamped where a channel debouches onto a basin floor: it only adds
material, spreads over a downfan angular sector (nothing behind the apex, nothing off to the side),
and thins with distance (concave profile). F-tier look, invariant-checked."""
import numpy as np

import landforms as L


def _apex(n=120):
    return np.zeros((n, n)), (30, 60)


def test_fan_is_deposition_only():
    base, apex = _apex()
    h = L.alluvial_fan(base, apex, downfan=(1.0, 0.0), flux=9.0, length=80.0, seed=2)
    assert np.all(h - base >= -1e-9)                     # a fan builds, never cuts
    assert (h - base).max() > 1.0                        # something was actually deposited


def test_fan_deposits_only_downfan():
    base, apex = _apex()
    dep = L.alluvial_fan(base, apex, downfan=(1.0, 0.0), flux=9.0, length=80.0, seed=2) - base
    assert dep[:apex[0] - 1].max() < 1e-6                # nothing up-fan (behind the apex)


def test_fan_thins_downfan():
    base, apex = _apex()
    dep = L.alluvial_fan(base, apex, downfan=(1.0, 0.0), flux=9.0, length=80.0, seed=2) - base
    yy, xx = np.mgrid[0:base.shape[0], 0:base.shape[1]].astype(float)
    r = np.hypot(yy - apex[0], xx - apex[1])
    near = (r > 3) & (r < 8) & (dep > 0.3)
    far = (r > 25) & (r < 32) & (dep > 0.01)
    assert dep[near].mean() > dep[far].mean()            # concave thinning profile


def test_fan_is_confined_to_its_sector():
    """Sideways of the apex (perpendicular to the downfan axis, well beyond the spread) gets nothing
    — the fan is a sector, not a full disc."""
    base, apex = _apex()
    dep = L.alluvial_fan(base, apex, downfan=(1.0, 0.0), spread_deg=60.0, flux=9.0, length=80.0, seed=2) - base
    yy, xx = np.mgrid[0:base.shape[0], 0:base.shape[1]].astype(float)
    sideways = (np.abs(yy - apex[0]) < 5) & (np.abs(xx - apex[1]) > 25)   # level with apex, far to the side
    assert dep[sideways].max() < 1e-6


def test_fan_is_deterministic():
    base, apex = _apex()
    a = L.alluvial_fan(base, apex, seed=5)
    b = L.alluvial_fan(base, apex, seed=5)
    assert np.array_equal(a, b)
