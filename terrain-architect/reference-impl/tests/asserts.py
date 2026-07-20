"""The invariants from 09-verification.md, as reusable assertion helpers.

These are the machine-checkable properties every simulation must satisfy:
determinism, no NaN/Inf, no invalid negatives, mass conservation under pure
transport, and radial isotropy on a radially symmetric input.
"""
import numpy as np


def assert_finite(a, name="field"):
    assert np.all(np.isfinite(a)), f"{name} contains NaN or Inf"


def assert_deterministic(fn):
    """fn() must return a bit-identical array on repeat calls (fixed seed)."""
    a = fn()
    b = fn()
    assert np.array_equal(a, b), "result is not bit-identical across runs"


def assert_mass_conserved(before, after, tol=1e-6, msg=""):
    m0 = float(np.sum(before))
    m1 = float(np.sum(after))
    rel = abs(m1 - m0) / (abs(m0) + 1e-12)
    assert rel < tol, f"mass not conserved {msg}: {m0:.6g} -> {m1:.6g} (rel {rel:.2e})"


def assert_nonneg(a, name="field", tol=1e-9):
    assert np.all(a >= -tol), f"{name} has invalid negatives (min {float(a.min()):.3e})"


def radial_anisotropy(field, center=None):
    """Departure from perfect radial symmetry: the RMS residual of the field from its
    own radial-mean profile, normalised by the field's peak-to-peak amplitude. ~0 =>
    isotropic; a 4-pipe/4-neighbour plus artefact raises it. The quantitative form of
    09's cone / sun-sweep check. Normalising by global amplitude (not per-ring mean)
    keeps it robust where a ring mean passes through zero.
    """
    n, m = field.shape
    if center is None:
        center = ((n - 1) / 2.0, (m - 1) / 2.0)
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    rr = np.round(np.hypot(xx - center[1], yy - center[0])).astype(int).ravel()
    vals = field.ravel()
    counts = np.maximum(np.bincount(rr), 1)
    prof = np.bincount(rr, weights=vals) / counts     # radial mean at each ring
    resid = vals - prof[rr]
    amp = float(field.max() - field.min())
    if amp < 1e-12:
        return 0.0
    return float(np.sqrt(np.mean(resid ** 2)) / amp)


def no_interior_pit(h, eps=1e-9):
    """After a correct (epsilon) depression fill, every interior cell has at least one
    strictly-lower 8-neighbour -> a downhill path to the edge exists everywhere."""
    n, m = h.shape
    interior = h[1:-1, 1:-1]
    lower = np.zeros_like(interior, dtype=bool)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            nb = h[1 + di:n - 1 + di, 1 + dj:m - 1 + dj]
            lower |= nb < interior - eps
    return bool(np.all(lower))
