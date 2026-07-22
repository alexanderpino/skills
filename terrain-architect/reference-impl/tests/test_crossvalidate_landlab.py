"""Optional cross-validation against Landlab — a mature, independently-tested landscape
evolution library (MIT).

These extend the RichDEM/pysheds flow checks in `test_crossvalidate.py` to three more
node families the graph demo wires — **stream power, flow accumulation, and hillslope
diffusion** — so the reference-impl modules are checked against an independent
implementation, not only their own `09` oracles. Each raises the bar from "self-consistent
with 09" to "agrees with Landlab".

Guarded by `pytest.importorskip`, so they SKIP cleanly when Landlab isn't installed (the
numpy-only core suite still runs green). Install with:
    pip install -r requirements-crossvalidate.txt

Provenance: Landlab @ `landlab/landlab` (MIT); see `reference-impl/GROUNDING.md` and
`references/22-open-source-grounding.md`. Comparisons are on physical signatures
(slope-area exponent, drainage-area correlation, single-mode decay), not raw fields —
grid conventions and boundary handling differ, exactly as the pysheds check notes.
"""
import numpy as np
import pytest

import flow
import erosion_streampower as SP
import diffusion


def _my_slope_area_exponent(h, cellsize):
    """log(S)-vs-log(A) slope on our channel network — the 09 stream-power oracle."""
    hf = flow.priority_flood_fill(h)
    ri, rj, slope, _ = SP.receivers(hf, cellsize)
    A = SP.drainage_area(hf, ri, rj, cellsize * cellsize)
    n = h.shape[0]
    interior = np.zeros((n, n), dtype=bool)
    interior[2:-2, 2:-2] = True
    chan = interior & (A > 30.0 * cellsize * cellsize) & (slope > 1e-6)
    return float(np.polyfit(np.log(A[chan]), np.log(slope[chan]), 1)[0])


def test_streampower_slope_area_exponent_matches_landlab():
    """The decisive stream-power signature (09): at steady state S ∝ A^(-m/n). Our
    Braun-Willett solver and Landlab's FastscapeEroder must both recover -m/n, and agree."""
    pytest.importorskip("landlab")
    try:
        from landlab import RasterModelGrid
        from landlab.components import FastscapeEroder, FlowAccumulator
    except Exception as e:                                    # noqa: BLE001
        pytest.skip(f"landlab API mismatch: {e}")

    n, cs = 40, 100.0
    m, K, U, dt, iters = 0.5, 3e-5, 0.001, 1000.0, 300
    h0 = np.random.default_rng(0).uniform(0.0, 1.0, (n, n)) * 5.0

    mine = SP.stream_power_evolve(h0, U, K, m, dt, iters, cellsize=cs)
    b_mine = _my_slope_area_exponent(mine, cs)

    g = RasterModelGrid((n, n), xy_spacing=cs)
    z = g.add_zeros("topographic__elevation", at="node")
    z[:] = h0.ravel()
    fa = FlowAccumulator(g, flow_director="FlowDirectorD8",
                         depression_finder="DepressionFinderAndRouter")
    sp = FastscapeEroder(g, K_sp=K, m_sp=m, n_sp=1.0)
    for _ in range(iters):
        z[g.core_nodes] += U * dt
        fa.run_one_step()
        sp.run_one_step(dt=dt)
    A = g.at_node["drainage_area"]
    S = g.at_node["topographic__steepest_slope"]
    chan = (A > 30.0 * cs * cs) & (S > 1e-6) & (g.status_at_node == 0)
    b_landlab = float(np.polyfit(np.log(A[chan]), np.log(S[chan]), 1)[0])

    assert abs(b_mine - (-m)) < 0.1, f"ours {b_mine:.3f} not ~ -m/n"
    assert abs(b_landlab - (-m)) < 0.1, f"landlab {b_landlab:.3f} not ~ -m/n"
    assert abs(b_mine - b_landlab) < 0.1, f"ours {b_mine:.3f} vs landlab {b_landlab:.3f}"


def test_d8_accumulation_matches_landlab():
    """Our D8 drainage area vs Landlab's FlowAccumulator (FlowDirectorD8) on one DEM.
    Conventions differ at the edges, so we demand strong correlation, not equality."""
    pytest.importorskip("landlab")
    try:
        from landlab import RasterModelGrid
        from landlab.components import FlowAccumulator
    except Exception as e:                                    # noqa: BLE001
        pytest.skip(f"landlab API mismatch: {e}")

    cs = 100.0
    rng = np.random.default_rng(0)
    raw = rng.uniform(0.0, 1.0, (30, 30)) + np.linspace(0.0, 3.0, 30)[:, None]
    dem = flow.priority_flood_fill(raw)
    mine = flow.d8_accumulation(dem, cellsize=cs)

    g = RasterModelGrid(dem.shape, xy_spacing=cs)
    z = g.add_zeros("topographic__elevation", at="node")
    z[:] = dem.ravel()
    FlowAccumulator(g, flow_director="FlowDirectorD8").run_one_step()
    theirs = g.at_node["drainage_area"].reshape(dem.shape)

    interior = np.zeros(dem.shape, dtype=bool)
    interior[1:-1, 1:-1] = True
    r = np.corrcoef(mine[interior].ravel(), theirs[interior].ravel())[0, 1]
    assert r > 0.9, f"correlation {r:.3f}"


def test_hillslope_diffusion_matches_landlab():
    """Our explicit Culling diffusion vs Landlab's LinearDiffuser: a single Fourier mode
    must decay by the same factor over the same time (both match the analytic decay)."""
    pytest.importorskip("landlab")
    try:
        from landlab import RasterModelGrid
        from landlab.components import LinearDiffuser
    except Exception as e:                                    # noqa: BLE001
        pytest.skip(f"landlab API mismatch: {e}")

    n, cs, D, dt, iters = 48, 1.0, 0.1, 0.1, 40
    x = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    h0 = np.sin(x)[None, :] * np.ones((n, 1))

    mine = diffusion.hillslope_diffuse(h0, D, dt, iters, cs)

    g = RasterModelGrid((n, n), xy_spacing=cs)
    z = g.add_zeros("topographic__elevation", at="node")
    z[:] = h0.ravel()
    ld = LinearDiffuser(g, linear_diffusivity=D)
    for _ in range(iters):
        ld.run_one_step(dt)
    theirs = g.at_node["topographic__elevation"].reshape(n, n)

    amp_mine = float(np.ptp(mine[n // 2, 2:-2]))             # amplitude on an interior row
    amp_theirs = float(np.ptp(theirs[n // 2, 2:-2]))
    assert abs(amp_mine / amp_theirs - 1.0) < 0.03, f"{amp_mine:.4f} vs {amp_theirs:.4f}"
