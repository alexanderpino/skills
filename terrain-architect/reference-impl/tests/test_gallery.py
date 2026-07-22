"""Regression guard for the visual reference (gallery.py). Renders every algorithm on the
shared base and asserts the numeric sanity the normalised images cannot show: every field is
finite and none has blown up. This is the automated form of the check that caught a stream-
power-at-the-wrong-scale explosion — a panel that looked fine but held 70,000,000 m of relief.
"""
import numpy as np
import gallery


def test_gallery_panels_valid_and_numerically_sane():
    gallery._REPORT.clear()
    tiles = gallery.panels()
    assert len(tiles) > 20
    for name, tile in tiles:
        assert tile.dtype == np.uint8 and tile.ndim == 3 and tile.shape[2] == 3, name
        assert np.all(np.isfinite(tile))

    base_relief = next(hi - lo for n, lo, hi, _ in gallery._REPORT if n == "base")
    for name, lo, hi, finite in gallery._REPORT:
        assert finite, f"{name} is non-finite"
        assert (hi - lo) < 50 * base_relief, f"{name} relief {hi - lo:.3e} — blown up?"
