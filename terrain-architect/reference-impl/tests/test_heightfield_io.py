"""Oracles for heightfield I/O — the load/save round-trips that make a real DEM a first-class base.

The guarantee is that what you save is what you load back (to the format's quantisation), for every
interchange format, and that an SRTM/USGS `.hgt` tile decodes to sane metres. Network fetch itself is
exercised opportunistically (skipped offline)."""
import os

import numpy as np
import pytest

import heightfield_io as hio


def _surface(n=48, m=60):
    y = np.sin(np.linspace(0, 6, n))[:, None]
    x = np.cos(np.linspace(0, 6, m))[None, :]
    return (y * x) * 300.0 + 500.0                         # ~200..800 m, non-square (catches shape bugs)


def test_npy_roundtrip_is_lossless(tmp_path):
    h = _surface()
    p = str(tmp_path / "h.npy")
    hio.save_heightfield(p, h)
    assert np.allclose(hio.load_heightfield(p), h)


@pytest.mark.parametrize("ext", [".png", ".r16", ".raw"])
def test_integer_formats_roundtrip_to_quantisation(tmp_path, ext):
    """16-bit integer formats preserve the surface to one quantum of the stored value range."""
    h = _surface()
    p = str(tmp_path / f"h{ext}")
    lo, hi = hio.save_heightfield(p, h)
    back = hio.load_heightfield(p, shape=h.shape, vmin=lo, vmax=hi)
    quantum = (hi - lo) / 65535.0
    assert np.max(np.abs(back - h)) <= quantum             # within one 16-bit step


def test_float_raw_roundtrip(tmp_path):
    h = _surface()
    p = str(tmp_path / "h.r32")
    hio.save_heightfield(p, h)
    back = hio.load_heightfield(p, shape=h.shape)
    assert np.max(np.abs(back - h)) < 1e-2                 # float32 precision on ~800 m values


def test_png_scales_into_metres(tmp_path):
    """Saving with an explicit range then loading with the same range reproduces the metres, i.e. the
    integer PNG is a faithful metre carrier, not just a 0..1 image."""
    h = _surface()
    p = str(tmp_path / "h.png")
    hio.save_heightfield(p, h, vmin=0.0, vmax=1000.0)
    back = hio.load_heightfield(p, vmin=0.0, vmax=1000.0)
    assert abs(back.max() - h.max()) < 0.05 and abs(back.min() - h.min()) < 0.05


def test_window_crops_and_decimates():
    dem = np.arange(400 * 400, dtype=float).reshape(400, 400)
    w = hio.window(dem, 100, 50, 200, stride=2)
    assert w.shape == (100, 100)
    assert w[0, 0] == dem[100, 50]


def test_srtm_fetch_decodes_sane_metres():
    """If the AWS tile is reachable/cached, it must decode to a big square array in a real elevation
    band; skip cleanly when offline so the suite stays green without network."""
    dem = hio.fetch_srtm("N36W113")
    if dem is None:
        pytest.skip("SRTM tile not reachable and not cached")
    assert dem.ndim == 2 and dem.shape[0] == dem.shape[1] >= 1201
    finite = dem[np.isfinite(dem)]
    assert -500 < np.nanmin(finite) and np.nanmax(finite) < 9000     # plausible Earth elevations (m)
