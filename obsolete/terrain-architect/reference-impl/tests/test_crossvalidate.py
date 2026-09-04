"""Optional cross-validation against mature, independently-tested libraries.

These raise the verification bar from "self-consistent with 09's oracles" to "agrees with
an independent implementation". They are guarded by pytest.importorskip, so they SKIP
cleanly when the library isn't installed (the numpy-only core suite still runs green).
Install with:  pip install -r requirements-crossvalidate.txt
"""
import numpy as np
import pytest

import inputs
import asserts
import flow


def _pitted_dem(n=41):
    dem = inputs.inverted_cone(n, depth=8.0)
    rng = np.random.default_rng(0)
    return dem + rng.normal(0, 0.05, size=dem.shape)


def test_priority_flood_matches_richdem():
    """Our epsilon priority-flood fill vs RichDEM's (Barnes) epsilon FillDepressions.
    Both are valid epsilon fills, so the raised-height fields correlate strongly and
    both leave no interior pit."""
    rd = pytest.importorskip("richdem")
    dem = _pitted_dem()
    mine = flow.priority_flood_fill(dem, eps=1e-5)
    try:
        arr = rd.rdarray(dem.astype(np.float64), no_data=-9999)
        theirs = np.array(rd.FillDepressions(arr, epsilon=True, in_place=False))
    except Exception as e:                                    # noqa: BLE001
        pytest.skip(f"richdem API mismatch: {e}")
    assert asserts.no_interior_pit(mine)
    a = (mine - dem).ravel()
    b = (theirs - dem).ravel()
    if a.std() > 0 and b.std() > 0:
        assert np.corrcoef(a, b)[0, 1] > 0.9


def test_d8_accumulation_matches_pysheds():
    """Our D8 drainage area vs pysheds' D8 accumulation on the same DEM (strong
    correlation; conventions and edge handling differ, so we don't demand equality)."""
    pytest.importorskip("pysheds")
    dem = flow.priority_flood_fill(_pitted_dem())
    try:
        from pysheds.grid import Grid
        from pysheds.view import Raster, ViewFinder
        vf = ViewFinder(shape=dem.shape)
        ras = Raster(dem.astype(np.float64), viewfinder=vf)
        grid = Grid(viewfinder=vf)
        fdir = grid.flowdir(ras)
        theirs = np.array(grid.accumulation(fdir), dtype=np.float64)
    except Exception as e:                                    # noqa: BLE001
        pytest.skip(f"pysheds API mismatch: {e}")
    mine = flow.d8_accumulation(dem)
    interior = np.zeros(dem.shape, dtype=bool)
    interior[1:-1, 1:-1] = True
    r = np.corrcoef(mine[interior].ravel(), theirs[interior].ravel())[0, 1]
    assert r > 0.7
