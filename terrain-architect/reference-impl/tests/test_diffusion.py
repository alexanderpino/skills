import numpy as np
import inputs
import asserts
import diffusion


def test_single_mode_exact_decay():
    """A single Fourier mode decays by the exact discrete factor per step."""
    n, cs, D, dt, iters = 64, 1.0, 0.1, 0.1, 25
    h0 = inputs.sinusoid(n, amp=1.0, k=1)          # mode along axis 1, kx = 2*pi/n
    kx = 2.0 * np.pi * 1.0 / (n * cs)
    h = diffusion.hillslope_diffuse(h0, D, dt, iters, cs)
    c = D * dt / cs ** 2
    factor = (1.0 - 2.0 * c * (1.0 - np.cos(kx * cs))) ** iters
    assert np.allclose(h, h0 * factor, atol=1e-9)


def test_conserves_mass():
    h0 = inputs.cone(n=64, height=5.0)
    h = diffusion.hillslope_diffuse(h0, D=0.1, dt=0.2, iters=50)
    asserts.assert_mass_conserved(h0, h, tol=1e-9, msg="diffusion")


def test_smooths_a_spike_without_blowing_up():
    h0 = inputs.spike(n=64, value=50.0)
    dt = diffusion.stable_dt(D=0.1)
    h = diffusion.hillslope_diffuse(h0, D=0.1, dt=dt, iters=100)
    asserts.assert_finite(h)
    assert h[32, 32] < h0[32, 32]                  # peak relaxes
    assert h.max() <= h0.max() + 1e-9              # no overshoot / instability
