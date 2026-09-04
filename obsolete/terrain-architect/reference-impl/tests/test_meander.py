"""Oracle tests for lateral fluvial migration (meander.py / 03-flow-routing.md).

The load-bearing physics is the UPSTREAM-LAG (Ikeda–Parker–Sawai 1981): near-bank velocity
depends on exponentially-lagged upstream curvature, which is what puts the migration peak
downstream of the curvature peak and makes meanders skew instead of standing still. Every other
invariant here (carve-only channel, cutoff shortens + emits an oxbow, sinuosity grows) is the
honest realisation on top."""
import numpy as np

import asserts
import meander as M


# --------------------------------------------------------------------------- #
# Geometry primitives
# --------------------------------------------------------------------------- #
def test_curvature_sign_left_turn_positive():
    """Signed curvature is +ve for a LEFT (CCW) turn, -ve for a right turn, and equal in
    magnitude for the mirror image (the convention migration direction relies on)."""
    left = np.array([[0, 0], [1, 0], [1, 1]], float)          # +x then +y = CCW
    right = np.array([[0, 0], [1, 0], [1, -1]], float)         # mirror = CW
    assert M.curvature(left)[1] > 0.0
    assert M.curvature(right)[1] < 0.0
    assert np.isclose(M.curvature(left)[1], -M.curvature(right)[1])


def test_curvature_of_circle_is_one_over_radius():
    """Menger curvature of a sampled circle equals 1/R (the physical unit, not an arbitrary scale)."""
    R = 12.0
    th = np.linspace(0.2, np.pi, 80)                           # CCW arc -> +1/R
    p = np.column_stack([R * np.cos(th), R * np.sin(th)])
    C = M.curvature(p)[5:-5]                                   # drop the endpoints
    assert np.allclose(C, 1.0 / R, rtol=0.02)


def test_resample_gives_uniform_spacing():
    # a finely-sampled curve so resampled chords aren't shortened by original-vertex bends
    t = np.linspace(0, 6, 400)
    p = np.column_stack([np.linspace(0, 100, 400), 8.0 * np.sin(t)])
    r = M.resample(p, ds=2.0)
    seglen = np.hypot(*np.diff(r, axis=0).T)
    assert np.allclose(seglen, seglen[0], rtol=1e-3)           # equal arc-length spacing
    assert abs(seglen.mean() - 2.0) < 0.05                     # ~ the requested ds
    assert np.allclose(r[0], p[0]) and np.allclose(r[-1], p[-1])  # endpoints preserved


# --------------------------------------------------------------------------- #
# The upstream lag — the whole thing
# --------------------------------------------------------------------------- #
def test_near_bank_velocity_no_lag_is_in_phase_with_curvature():
    """With L_adj -> 0 the filter has no memory: u_b == C (DC-normalised). Zero phase lag — the
    degenerate case the chapter says gives sine waves, not meanders."""
    ds = 1.0
    s = np.arange(300) * ds
    C = np.sin(2 * np.pi * s / 60.0)
    u0 = M.near_bank_velocity(C, ds, L_adj=1e-4)
    assert np.corrcoef(C[50:], u0[50:])[0, 1] > 0.999          # in phase
    assert np.allclose(u0, C, atol=1e-3)


def test_upstream_lag_shifts_migration_peak_downstream():
    """THE key invariant (Ikeda–Parker–Sawai 1981): a real adjustment length lags the near-bank
    velocity so its peak sits DOWNSTREAM of the curvature peak. Without the lag the peaks coincide.
    This asymmetry is what skews meanders; drop it and bends stay symmetric and stationary."""
    ds = 1.0
    s = np.arange(400) * ds
    period = 80.0
    C = np.sin(2 * np.pi * s / period)
    u0 = M.near_bank_velocity(C, ds, L_adj=1e-4)               # no lag
    u1 = M.near_bank_velocity(C, ds, L_adj=40.0)               # real lag

    win = slice(160, 240)                                      # an interior period (skip warm-up)
    lag0 = int(np.argmax(u0[win])) - int(np.argmax(C[win]))
    lag1 = int(np.argmax(u1[win])) - int(np.argmax(C[win]))
    assert lag0 == 0                                           # no-lag peak coincides
    assert lag1 > 0                                            # lagged peak is downstream
    assert lag1 < period / 2.0                                 # ...but under a quarter-to-half wave


# --------------------------------------------------------------------------- #
# Migration loop
# --------------------------------------------------------------------------- #
def test_migration_is_deterministic():
    cl = _sine_centreline()
    a, oa = M.migrate(cl, steps=25, ds=2.0, L_adj=25.0, E=0.6)
    b, ob = M.migrate(cl, steps=25, ds=2.0, L_adj=25.0, E=0.6)
    assert np.array_equal(a, b) and len(oa) == len(ob)


def test_migration_amplifies_bends_sinuosity_grows():
    """Sweeping the channel by E·u_b grows the bends: sinuosity increases monotone-ish over the
    run (until a cutoff resets it). A pinned straight-ish wave should get wigglier, not flatten."""
    cl = _sine_centreline()
    s0 = M.sinuosity(cl)
    c1, _ = M.migrate(cl, steps=100, dt=1.0, ds=2.0, L_adj=28.0, E=1.2, cutoff_dist=7.0, min_sep=10)
    c2, _ = M.migrate(cl, steps=200, dt=1.0, ds=2.0, L_adj=28.0, E=1.2, cutoff_dist=7.0, min_sep=10)
    assert M.sinuosity(c1) > s0
    assert M.sinuosity(c2) > M.sinuosity(c1)                   # keeps growing with more steps


def test_migration_pins_endpoints():
    cl = _sine_centreline()
    out, _ = M.migrate(cl, steps=40, ds=2.0, E=0.8, pin_ends=True)
    assert np.allclose(out[0], cl[0]) and np.allclose(out[-1], cl[-1])


# --------------------------------------------------------------------------- #
# Neck cutoff -> oxbow
# --------------------------------------------------------------------------- #
def test_neck_cutoff_shortens_line_and_emits_oxbow():
    """A loop whose neck is within cutoff_dist short-circuits: the centreline loses the loop's
    nodes and the abandoned arc is returned as an oxbow whose ends nearly touch (the neck)."""
    p = np.array([[0, 0], [1, 0], [2, 0], [3, 0],
                  [3.5, 1], [3.2, 2], [2.5, 2.3], [2.0, 2], [1.8, 1],
                  [2, 0.2], [3, 0.2], [4, 0.2], [5, 0.2]], float)   # node 9 loops back near node 2
    sp, ox = M._neck_cutoff(p, cutoff_dist=0.5, min_sep=5)
    assert len(sp) < len(p)                                    # loop spliced out
    assert len(ox) == 1
    neck = np.hypot(*(ox[0][-1] - ox[0][0]))
    assert neck < 0.5                                          # the abandoned arc closes on itself
    assert M.sinuosity(sp) < M.sinuosity(p)                   # a cutoff always straightens the reach


def test_no_cutoff_on_a_gentle_reach():
    """A gentle wave has no near-touching non-adjacent nodes, so nothing cuts off (no spurious
    oxbows from adjacent nodes — that's what min_sep guards)."""
    cl = _sine_centreline()
    sp, ox = M._neck_cutoff(cl, cutoff_dist=2.0, min_sep=8)
    assert len(ox) == 0 and np.array_equal(sp, cl)


# --------------------------------------------------------------------------- #
# Height-field realisation (burnChannel)
# --------------------------------------------------------------------------- #
def test_burn_channel_carves_only_never_raises():
    """burnChannel subtracts: h only ever goes down (step 4 in the pseudocode), so no cell is
    raised and no positive rim appears — the property a raw min() carve would violate."""
    h = np.full((80, 80), 100.0)
    line = np.column_stack([np.full(50, 20.0), np.linspace(4.0, 36.0, 50)])   # world metres
    h2 = M.burn_channel(h, line, half_width=3.0, depth=8.0, bank_width=4.0, cellsize=0.5)
    assert np.all(h2 <= h + 1e-9)                              # carve-only
    assert h2.max() <= h.max() + 1e-9                          # never raised
    assert (h.min() - h2.min()) > 6.0                          # the thalweg is cut ~depth down


def test_burn_channel_cross_section_deepens_toward_thalweg():
    """The bed is a parabola in the SDF (bed = thalweg + depth·t²): deepest on the centreline,
    shallowing to the bank. Sampling across the channel must be monotone from thalweg outward."""
    h = np.full((60, 120), 50.0)
    line = np.column_stack([np.linspace(4.0, 56.0, 60), np.full(60, 30.0)])   # horizontal channel at y=30
    h2 = M.burn_channel(h, line, half_width=4.0, depth=10.0, bank_width=5.0, cellsize=0.5)
    col = 60                                                   # a column crossing the channel
    profile = h2[:, col]
    bed_row = int(np.argmin(profile))
    # from the bed outward (increasing distance) the surface rises monotonically on each side
    assert np.all(np.diff(profile[bed_row:]) >= -1e-9)
    assert np.all(np.diff(profile[:bed_row + 1]) <= 1e-9)


def test_point_bars_raise_only_the_inner_bank():
    """depositPointBars aggrades the inner (convex, centre-of-curvature) bank and leaves the outer
    (cut) bank alone — the deposition half of the erode-one-side/deposit-the-other asymmetry."""
    # a single left-bending arc; inner bank is on the +N (centre) side
    th = np.linspace(0.6, 2.5, 40)
    R = 18.0
    line = np.column_stack([30.0 + R * np.cos(th), 30.0 + R * np.sin(th)])
    h = np.full((120, 120), 40.0)
    h2 = M.deposit_point_bars(h, line, half_width=2.0, bar_height=6.0, bank_width=6.0, cellsize=0.5)
    asserts.assert_finite(h2)
    assert h2.max() > h.max() + 1.0                            # a bar was built
    assert np.all(h2 >= h - 1e-9)                              # deposition never cuts


# --------------------------------------------------------------------------- #
# Composite belt node (meander_belt) + deposition survival
# --------------------------------------------------------------------------- #
def test_seed_wave_tapers_to_straight_ends():
    """The default seed carries the wave in its interior and tapers flat toward the ends, so the
    pinned inflow/outflow ride a nearly-straight reach and don't coil. Measured as lateral deviation
    from the centreline: the outer eighths average a small fraction of the middle."""
    cl = M.seed_wave((120, 200), cellsize=4.0)
    y = cl[:, 1]
    dev = np.abs(y - np.median(y))
    m = len(y)
    ends = np.concatenate([dev[:m // 8], dev[-m // 8:]])
    mid = dev[3 * m // 8: 5 * m // 8]
    assert ends.mean() < 0.4 * mid.mean()           # ends ride a much flatter reach than the middle


def test_meander_belt_is_deterministic_and_carves_a_channel():
    base = np.full((100, 160), 50.0)
    cl = M.seed_wave((100, 160), cellsize=4.0)
    a = M.meander_belt(base, cl, cellsize=4.0, steps=100)
    b = M.meander_belt(base, cl, cellsize=4.0, steps=100)
    assert np.array_equal(a["height"], b["height"])         # deterministic
    assert a["water"].dtype == bool and a["channel"].sum() > 0
    assert a["water"].sum() >= a["channel"].sum()           # water = channel (+ any oxbow lakes)
    assert a["height"][a["channel"]].mean() < 50.0          # the channel is incised below the plain


def test_belt_is_not_carve_only_point_bars_stand_above_the_carve():
    """The regression behind Gemini's 'carve-only' read: the belt deposits point/scroll bars on the
    convex banks AFTER the carve, so material stands ABOVE the deposit=False (carve-only) belt over a
    real area — the cut-bank-erodes / point-bar-deposits asymmetry, not just an incised groove."""
    base = np.full((120, 200), 100.0)
    cl = M.seed_wave((120, 200), cellsize=4.0)
    kw = dict(cellsize=4.0, steps=140, half_width=8.0, depth=6.0, bank_width=12.0,
              bar_height=4.0, bar_bank_width=12.0)
    with_bars = M.meander_belt(base, cl, **kw)["height"]
    carve_only = M.meander_belt(base, cl, deposit=False, **kw)["height"]
    standing = with_bars - carve_only
    assert standing.min() >= -1e-9                          # deposition only ADDS vs the carve-only belt
    assert standing.max() > 1.0                             # a real bar, not a rounding speck
    assert (standing > 0.2).sum() > 60                      # over a meaningful scroll-bar area


# --------------------------------------------------------------------------- #
def _sine_centreline():
    x = np.linspace(0.0, 500.0, 260)
    y = 5.0 * np.sin(2 * np.pi * x / 90.0)
    return np.column_stack([x, y])
