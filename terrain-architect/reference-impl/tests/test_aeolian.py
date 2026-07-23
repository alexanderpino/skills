"""Invariant tests for aeolian abrasion / yardangs (aeolian.py / 16, Ward & Greeley 1984).

F-tier "look" held to invariants: the abraded ridges elongate PARALLEL to the wind (streamlined,
the yardang/drumlin signature), abrasion only removes material and only within the soft mask, and —
the Ward & Greeley detail — the low ground is cut fastest (bottom-weighted saltation → undercut,
streamlined ridges), not the crests. Not a certified erosion-rate oracle."""
import numpy as np

import aeolian
import noise


def _playa(n=120, relief=12.0, wind=(1.0, 0.25), seed=3):
    """A soft substrate with a faint wind-aligned grain, ready to be abraded into yardangs."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    u, v = wind; mag = np.hypot(u, v); u, v = u / mag, v / mag
    along, cross = xx * u + yy * v, -xx * v + yy * u
    h = relief * noise.fbm(along * 0.018, cross * 0.11, seed, octaves=4)
    return h - h.min()


def _acf(z, di, dj):
    a = z - z.mean()
    return float((a * np.roll(np.roll(a, di, 0), dj, 1)).mean() / (a * a).mean())


def test_ridges_elongate_parallel_to_the_wind():
    """Streamlined yardang ridges: the surface stays correlated far ALONG the wind but decorrelates
    quickly ACROSS it (the drumlin-like signature). Isotropic erosion would give equal correlation."""
    h = aeolian.yardang(_playa(), wind=(1.0, 0.25), soft_mask=1.0, iters=10, seed=3)
    assert _acf(h, 1, 5) > 3.0 * _acf(h, 5, -1)       # along-wind autocorr >> cross-wind


def test_abrasion_is_carve_only():
    playa = _playa()
    h = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=10, seed=3)
    assert np.all(h <= playa + 1e-9)                  # wind removes, never builds


def test_only_soft_ground_is_abraded():
    """A hard mask (soft=0) leaves the rock untouched — wind abrasion needs a cohesive-but-soft
    substrate (playa clay, loess, tuff)."""
    playa = _playa()
    soft = np.ones_like(playa); soft[:, playa.shape[1] // 2:] = 0.0
    h = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=soft, iters=10, seed=3)
    assert np.allclose(h[:, playa.shape[1] // 2 + 3:], playa[:, playa.shape[1] // 2 + 3:])


def test_low_ground_is_cut_fastest():
    """Bottom-weighted saltation (Ward & Greeley: sand only saltates ~1 m up): the troughs / low
    ground are abraded far more than the ridge crests — which is what undercuts and streamlines the
    ridges rather than lowering everything uniformly."""
    playa = _playa()
    h = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=10, saltation_h=3.0, seed=3)
    ero = playa - h
    med = np.median(playa)
    assert ero[playa < med].mean() > 2.0 * ero[playa > med].mean()


def test_yardang_is_deterministic():
    playa = _playa()
    a = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=6, seed=1)
    b = aeolian.yardang(playa, wind=(1.0, 0.25), soft_mask=1.0, iters=6, seed=1)
    assert np.array_equal(a, b)
