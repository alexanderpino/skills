import numpy as np
import inputs
import asserts
import erosion_droplet as D


def _noisy_slope(n=64, seed=1):
    base = inputs.constant_slope(n, gradient=0.3)
    rng = np.random.default_rng(seed)
    return base + rng.normal(0, 0.05, size=(n, n))


def test_deterministic():
    h0 = _noisy_slope()
    asserts.assert_deterministic(lambda: D.droplet_erode(h0, n_droplets=2000, seed=7))


def test_mass_conserved():
    """Erode-brush + deposit-bilinear + drop-leftover conserve total volume."""
    h0 = _noisy_slope()
    h = D.droplet_erode(h0, n_droplets=5000, seed=3)
    asserts.assert_mass_conserved(h0, h, tol=1e-6, msg="droplet")


def test_finite_and_changes_terrain():
    h0 = _noisy_slope()
    h = D.droplet_erode(h0, n_droplets=5000, seed=3)
    asserts.assert_finite(h)
    assert not np.allclose(h, h0)                 # it actually did something


def test_grid_bias_is_random_not_systematic():
    """Droplet is largely immune to GRID anisotropy (continuous positions, bilinear
    gradients). A single run carves random gullies (a real, desired departure from
    radial), but those are random, not grid-aligned — so averaging over seeds cancels
    them. A fixed 4-pipe/plus artefact would survive the average. Verify the ensemble
    mean is markedly more radial than a single run."""
    h0 = inputs.cone(n=48, height=12.0, radius=22.0)
    single = h0 - D.droplet_erode(h0, n_droplets=1500, seed=0)
    acc = np.zeros_like(h0)
    K = 5
    for s in range(K):
        acc += h0 - D.droplet_erode(h0, n_droplets=1500, seed=s)
    mean = acc / K
    assert asserts.radial_anisotropy(mean) < asserts.radial_anisotropy(single)
