"""Numerical-contract oracles (14 *Numerical contracts*, 09).

Individually-correct nodes still produce garbage when they are combined, and the reported
symptom is nearly always isolated spikes or a field that has quietly gone NaN. These tests pin
the composition traps the chapter claims, so the claims stay honest:

  * a stability limit met EXACTLY is not met -- and the wrong result passes every
    finite/conserved assertion, which is the whole reason those assertions are not enough;
  * NaN spreads SPATIALLY through any stencil, so the poisoned region grows per pass and a NaN
    found at export has lost its origin;
  * an out-of-range value is what turns into NaN downstream, one operation later;
  * a clamp count that rises is a guard masking a divergence.
"""
import numpy as np
import pytest
import asserts
import diffusion


def _checkerboard(n=32, amp=1.0):
    """The grid-scale mode: +-alternating cells. Invisible in a histogram, unmistakable under a
    sun sweep (09), and the thing "weird spikes" usually turn out to be."""
    ii, jj = np.mgrid[0:n, 0:n]
    return amp * (-1.0) ** (ii + jj)


# --------------------------------------------------------------------------- #
# "A stability limit met exactly is not met" (09) -- made executable.

def test_diffusion_at_exactly_the_limit_never_damps():
    """At c = D*dt/dx^2 = 0.25 the checkerboard's amplification factor is 1 - 8c = -1: it flips
    sign forever and never decays. The field stays finite and mass stays conserved, so every
    blow-up assertion passes while the pass does not actually diffuse."""
    h0 = _checkerboard(n=32, amp=1.0)
    h = diffusion.hillslope_diffuse(h0, D=1.0, dt=0.25, iters=50)   # c = 0.25 exactly

    asserts.assert_finite(h)                                        # passes...
    asserts.assert_mass_conserved(h0 + 10.0, h + 10.0)              # ...and so does this...
    assert np.allclose(np.abs(h), np.abs(h0)), (                    # ...while nothing damped
        "amplitude changed; expected |amplification| == 1 at the exact limit")


def test_safety_factor_below_the_limit_does_damp():
    """The control that gives the test above its meaning: the same mode under the 0.9 safety
    factor (`diffusion.stable_dt`) decays as it should. If this failed, the test above would be
    measuring something other than the exact-limit trap."""
    h0 = _checkerboard(n=32, amp=1.0)
    dt = diffusion.stable_dt(D=1.0, cellsize=1.0)                   # 0.9 * 0.25
    h = diffusion.hillslope_diffuse(h0, D=1.0, dt=dt, iters=50)

    assert np.max(np.abs(h)) < 1e-3 * np.max(np.abs(h0)), "the checkerboard mode did not decay"


def test_finiteness_and_conservation_do_not_imply_correctness():
    """The general shape of the trap: assert on the DIRECTION of the effect, not merely that the
    output is finite. Measured the way 09 measures it -- mean |laplacian h|, which a diffusion
    pass is supposed to lower. At the exact limit it does not."""
    def roughness(h):
        lap = (-4.0 * h + np.roll(h, 1, 0) + np.roll(h, -1, 0)
               + np.roll(h, 1, 1) + np.roll(h, -1, 1))
        return float(np.mean(np.abs(lap)))

    rng = np.random.default_rng(0)
    h0 = _checkerboard(n=32, amp=1.0) + rng.normal(0.0, 0.01, (32, 32))

    at_limit = diffusion.hillslope_diffuse(h0, D=1.0, dt=0.25, iters=50)
    safe = diffusion.hillslope_diffuse(h0, D=1.0, dt=diffusion.stable_dt(1.0), iters=50)

    assert roughness(at_limit) > 0.9 * roughness(h0), (
        "at the exact limit the pass is supposed to leave the grid-scale mode untouched")
    assert roughness(safe) < 0.01 * roughness(h0), (
        "below the limit the same pass must actually smooth -- otherwise the safety factor is "
        "not doing the work 14 says it does")


# --------------------------------------------------------------------------- #
# NaN spreads spatially, not merely downstream.

def test_one_nan_grows_through_a_stencil():
    """A single NaN mixed into its neighbours by a 5-point stencil poisons a region that grows
    every pass. This is why 09 says assert after EVERY step: by export, one bad cell has become
    a blob and the origin is unrecoverable (14)."""
    h = np.zeros((64, 64))
    h[32, 32] = np.nan

    counts = []
    for _ in range(4):
        h = diffusion.hillslope_diffuse(h, D=1.0, dt=0.2, iters=1)
        counts.append(asserts.nonfinite_count(h))

    assert counts == sorted(counts) and counts[-1] > counts[0], (
        f"NaN region did not grow through the stencil: {counts}")
    assert counts[0] > 1, "a 5-point stencil should poison the 4 neighbours on the first pass"


# --------------------------------------------------------------------------- #
# An out-of-range value is what becomes NaN one operation later.

def test_negative_slope_becomes_nan_in_stream_power():
    """Mechanism 1 of 14: `S^n` with S < 0 -- an unfilled pit, or a sign slip -- is NaN on the
    spot for non-integer n. The value that crossed the edge was merely out of range; the NaN
    appears in the next node, which is why the port check has to happen at the producer."""
    S = np.array([0.5, 0.1, -1e-6])                     # last cell fractionally out of range
    with np.errstate(invalid="ignore"):
        incision = np.power(S, 0.7)                     # non-integer n
    assert asserts.nonfinite_count(incision) == 1, "expected the negative slope to produce NaN"

    with pytest.raises(AssertionError):                 # the port check catches it FIRST
        asserts.assert_in_range(S, lo=0.0, name="slope")


def test_port_range_check_accepts_a_legal_field_and_rejects_a_leaked_one():
    """The port contract of 14: depth is `>= 0`, a mask is closed [0,1], height is finite but
    unbounded -- a range check on height would itself be the bug (real terrain spans -11 km to
    +9 km)."""
    asserts.assert_in_range(np.array([0.0, 1.5, 3.0]), lo=0.0, name="waterDepth")
    asserts.assert_in_range(np.array([0.0, 0.5, 1.0]), lo=0.0, hi=1.0, name="mask")
    asserts.assert_in_range(np.array([-11000.0, 8848.0]), name="height")   # finite, unbounded

    with pytest.raises(AssertionError):
        asserts.assert_in_range(np.array([0.0, -1e-9]), lo=0.0, name="waterDepth")
    with pytest.raises(AssertionError):
        asserts.assert_in_range(np.array([0.0, 1.0 + 1e-9]), lo=0.0, hi=1.0, name="mask")
    with pytest.raises(AssertionError):
        asserts.assert_in_range(np.array([0.0, np.inf]), name="height")


# --------------------------------------------------------------------------- #
# A rising clamp count is a guard masking a divergence.

def test_settling_clamp_counts_pass_and_rising_ones_fail():
    """14's rule, and the generalisation of 09's erosion-created-pit check: a guard fires while
    the sim settles and then subsides. The same guard firing more often every iteration is the
    only thing hiding a divergence, so the trend is the assertion, not the presence."""
    asserts.assert_clamps_not_growing([40, 12, 5, 3, 1, 0, 0, 0])       # settling: fine
    asserts.assert_clamps_not_growing([3, 7, 2, 6, 3, 5, 2, 4])         # noisy, no trend: fine

    with pytest.raises(AssertionError):
        asserts.assert_clamps_not_growing([1, 2, 4, 8, 16, 32, 64, 128])
