"""Smoke/regression guard for the 3D hero renderer (hero.py). It is a *look*, not an oracle, so the
checks are structural: the camera maths is finite, and the render is a valid, non-blank RGB image that
contains both sky and terrain (the projection actually drew something). Runs tiny for speed."""
import numpy as np

import analysis
import archetypes as A
import hero


def test_camera_matrices_are_finite():
    v = hero._look_at((10, 8, 10), (0, 0, 0), (0, 1, 0))
    p = hero._perspective(35.0, 1.6, 1.0, 100.0)
    assert v.shape == (4, 4) and p.shape == (4, 4)
    assert np.all(np.isfinite(v)) and np.all(np.isfinite(p))


def test_hero_renders_valid_nonblank_image():
    n, cell = 40, 2000.0 / 40
    h = A.alpine(n=n, cell=cell)
    col, _, surf = A.substance_color(h, "temperate", cell)
    img = hero.hero(surf, cell, col, size=(220, 150), ss=1, fog=0.2)
    assert img.shape == (150, 220, 3) and img.dtype == np.uint8
    assert np.all(np.isfinite(img.astype(np.float64)))
    # both sky (top row, untouched by terrain) and terrain (drawn) are present
    assert int(img.reshape(-1, 3).std(axis=0).sum()) > 10
    top_is_sky = img[0].mean() > 120                        # sky gradient fills the top band
    assert top_is_sky


def test_supersample_downscales_to_requested_size():
    n, cell = 32, 2000.0 / 32
    h = A.alpine(n=n, cell=cell)
    col, _, surf = A.substance_color(h, "temperate", cell)
    img = hero.hero(surf, cell, col, size=(180, 120), ss=2)
    assert img.shape == (120, 180, 3)                        # ss folds back to the requested size
