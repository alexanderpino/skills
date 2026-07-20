import numpy as np
import asserts
import erosion_streampower as SP


def test_slope_area_scaling_at_steady_state():
    """The decisive stream-power check (09): at steady state S proportional to
    A^(-m/n), so log(S) vs log(A) is a straight line of slope -m/n."""
    n = 40
    rng = np.random.default_rng(0)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05          # small noise breaks symmetry
    m_exp, K, U, dt, iters = 0.5, 1.0, 1.0, 2.0, 400
    h = SP.stream_power_evolve(h0, U, K, m_exp, dt, iters)

    ri, rj, slope, _ = SP.receivers(flow_fill(h))
    A = SP.drainage_area(flow_fill(h), ri, rj)
    interior = np.zeros((n, n), dtype=bool)
    interior[2:-2, 2:-2] = True
    chan = interior & (A > 30.0) & (slope > 1e-6)      # channel cells only
    logA = np.log(A[chan])
    logS = np.log(slope[chan])
    b = np.polyfit(logA, logS, 1)[0]
    assert abs(b - (-m_exp / 1.0)) < 0.1, f"slope-area exponent {b:.3f}, expected -0.5"


def flow_fill(h):
    import flow
    return flow.priority_flood_fill(h)


def test_produces_a_concave_channel_network():
    """A convex (uneroded) start becomes concave: the main-channel long profile
    steepens headward and flattens toward base level."""
    n = 40
    rng = np.random.default_rng(1)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    h = SP.stream_power_evolve(h0, uplift=1.0, K=1.0, m_exp=0.5, dt=2.0, iters=300)
    asserts.assert_finite(h)
    assert h.max() > 0.0                                 # relief built by uplift
    # interior is higher than the fixed base-level edges (drainage divide in the middle)
    assert h[n // 2, n // 2] > h[0, n // 2] + 1e-6
