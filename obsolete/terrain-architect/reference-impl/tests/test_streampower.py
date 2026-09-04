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


# --------------------------------------------------------------------------- #
# hillslope diffusion coupled into the solver (04): dh/dt = U - K A^m S^n + D lap(h)
# --------------------------------------------------------------------------- #
def _valley_spacing(h, thr=40.0):
    """Mean distance from an interior cell to the nearest channel cell. This is the metric
    Perron et al. predict on, and — unlike a channel-cell COUNT, which is resolution-saturated
    at these grid sizes and reads flat — it actually carries signal. nan if nothing channelised."""
    n = h.shape[0]
    interior = np.zeros((n, n), dtype=bool)
    interior[3:-3, 3:-3] = True
    ii, jj = np.mgrid[0:n, 0:n]
    hf = flow_fill(h)
    ri, rj, _, _ = SP.receivers(hf)
    A = SP.drainage_area(hf, ri, rj)
    ci, cj = np.nonzero(interior & (A > thr))
    if len(ci) == 0:
        return float("nan")
    d = np.full((n, n), np.inf)
    for a in range(len(ci)):
        d = np.minimum(d, np.hypot(ii - ci[a], jj - cj[a]))
    return float(d[interior].mean())


def _divide_roughness(h):
    """Mean |laplacian| over the interior — how knife-edged the interfluves are."""
    n = h.shape[0]
    interior = np.zeros((n, n), dtype=bool)
    interior[3:-3, 3:-3] = True
    lap = np.abs(-4.0 * h + np.roll(h, 1, 0) + np.roll(h, -1, 0)
                 + np.roll(h, 1, 1) + np.roll(h, -1, 1))
    return float(lap[interior].mean())


def test_diffusion_default_is_bit_for_bit_the_pure_fluvial_solver():
    """D is opt-in. The scalar-K, no-diffusion path must be untouched — otherwise every
    existing result (and the Landlab cross-validation) silently moves."""
    n = 30
    rng = np.random.default_rng(0)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    a = SP.stream_power_evolve(h0, 1.0, 1.0, 0.5, 1.0, 60)
    b = SP.stream_power_evolve(h0, 1.0, 1.0, 0.5, 1.0, 60, D=0.0)
    assert np.array_equal(a, b)


def test_diffusion_sets_valley_spacing_and_smooths_divides():
    """The Cordonnier companion term (04). Stream power alone leaves knife-edge interfluves;
    raising D rounds them and pushes the valleys further apart (Perron, Kirchner & Dietrich
    2008). Both trends must be monotone — a single pair could be noise.

    Reference numbers at n=80, iters=200 (see the `stream_power_evolve` docstring):
        D     0.0    0.1    0.5    1.5    4.0   10.0
        space 3.32   3.38   3.81   6.33   9.76  (erased)
        rough 1.4135 0.6797 0.2588 0.1078 0.0512 0.0204
    Run smaller here for suite time; the ordering is what is asserted, not the values."""
    n, iters = 48, 150
    rng = np.random.default_rng(0)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    space, rough = [], []
    for D in (0.0, 0.5, 2.0):
        h = SP.stream_power_evolve(h0, 1.0, 1.0, 0.5, 1.0, iters, D=D)
        asserts.assert_finite(h)
        space.append(_valley_spacing(h))
        rough.append(_divide_roughness(h))

    # divides get smoother, monotonically, and by a lot (measured 1.359 -> 0.265 -> 0.088)
    assert rough[0] > rough[1] > rough[2], f"divide roughness not monotone in D: {rough}"
    assert rough[0] / rough[2] > 5.0, f"diffusion barely smoothed anything: {rough}"
    # valleys get further apart, monotonically (measured 3.69 -> 4.19 -> 7.40)
    assert space[0] < space[1] < space[2], f"valley spacing not monotone in D: {space}"
    assert space[2] / space[0] > 1.5, f"spacing barely moved: {space}"


def test_diffusion_stability_the_safety_factor_is_load_bearing():
    """The sub-cycling must keep D*dt/cellsize^2 strictly BELOW 0.25. At exactly 0.25 the
    checkerboard mode's amplification is 1-8c = -1: it flips sign forever and never damps, so
    the pass roughens the terrain while passing every blow-up test. Sizing the sub-step with a
    bare ceil() lands exactly on 0.25 for every D that divides evenly (0.5, 1.5, 4, 10 at dt=1),
    which is why this is asserted rather than assumed."""
    n, iters = 40, 80
    rng = np.random.default_rng(0)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    prev = None
    for D in (0.5, 1.5, 4.0, 10.0):          # the exact values a bare ceil() would trip on
        h = SP.stream_power_evolve(h0, 1.0, 1.0, 0.5, 1.0, iters, D=D)
        asserts.assert_finite(h)
        r = _divide_roughness(h)
        assert prev is None or r < prev, (
            f"D={D} roughened the surface (|lap| {r:.4f} vs {prev:.4f}) — "
            "the diffusion sub-step is sitting on the stability limit")
        prev = r


def test_diffusion_accepts_a_field_so_soil_creeps_and_bare_rock_does_not():
    """D may vary in space, like K. Half the tile soil-mantled, half bare rock."""
    n, iters = 48, 120
    rng = np.random.default_rng(0)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    Dfield = np.where(np.mgrid[0:n, 0:n][1] < n // 2, 1.0, 0.0)     # left half creeps
    h = SP.stream_power_evolve(h0, 1.0, 1.0, 0.5, 1.0, iters, D=Dfield)
    asserts.assert_finite(h)
    lap = np.abs(-4.0 * h + np.roll(h, 1, 0) + np.roll(h, -1, 0)
                 + np.roll(h, 1, 1) + np.roll(h, -1, 1))
    soil, rock = lap[4:-4, 4:n // 2 - 2].mean(), lap[4:-4, n // 2 + 2:-4].mean()
    assert rock > 3.0 * soil, f"field D had little effect: soil {soil:.4f} vs rock {rock:.4f}"
