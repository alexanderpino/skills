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


def assert_layer_budget(before, after, tol=1e-6, msg=""):
    """27's co-evolution budget: under pure transport the layer STACK closes as ONE budget --
    height/bedrock plus every granular or transient layer (soil, sediment, sand, snow) summed
    together -- even while individual layers legitimately exchange mass (erosion turns soil into
    sediment, an avalanche moves snow between cells). Checking layers separately would flag those
    exchanges as leaks; checking only height would miss a layer silently minting mass.
    `before`/`after` are sequences of same-shape fields (the stack's thickness/height layers)."""
    m0 = sum(float(np.sum(a)) for a in before)
    m1 = sum(float(np.sum(a)) for a in after)
    rel = abs(m1 - m0) / (abs(m0) + 1e-12)
    assert rel < tol, f"layer-stack budget not closed {msg}: {m0:.6g} -> {m1:.6g} (rel {rel:.2e})"


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


def boundary_influence_profile(field):
    """`field` binned by INSET RING -- Chebyshev distance from the perimeter, so ring 0 is the
    outermost cells -- returned as the per-ring mean. The domain-edge check of 03 (*Domain
    boundaries*) and 09.

    A boundary policy whose influence never reached inward gives a FLAT profile. A uniform open
    perimeter gives a monotone ramp across an outer band: every edge cell is an outlet, so the
    band drains straight out and erodes into the fringe ("tablecloth"), with the interior beyond
    it untouched.
    """
    field = np.asarray(field, dtype=np.float64)
    n, m = field.shape
    ii, jj = np.mgrid[0:n, 0:m]
    ring = np.minimum(np.minimum(ii, n - 1 - ii), np.minimum(jj, m - 1 - jj)).ravel()
    counts = np.maximum(np.bincount(ring), 1)
    return np.bincount(ring, weights=field.ravel()) / counts


def boundary_influence_distance(field, tol=0.1):
    """The inset (in cells) beyond which `boundary_influence_profile` stays settled at its
    interior value -- the knee of the ramp, and therefore **the margin width to simulate and
    crop**, measured rather than guessed. 0 => the edge policy left no measurable signature.

    The interior value and the interior's own ring-to-ring spread are both taken from the inner
    half of the profile, so the threshold comes from a measured noise floor rather than a chosen
    constant (09: a metric with no control is not evidence). `tol` is the fraction of the total
    edge-to-interior swing still permitted at the knee.
    """
    prof = boundary_influence_profile(field)
    if prof.size < 4:
        return 0
    inner = prof[prof.size // 2:]
    interior = float(np.median(inner))
    noise = float(np.max(np.abs(inner - interior)))
    swing = float(prof[0]) - interior
    if abs(swing) <= max(noise, 1e-12):
        return 0                                          # flat: no boundary signature
    band = max(abs(tol * swing), noise)
    settled = np.abs(prof - interior) <= band
    stays = np.logical_and.accumulate(settled[::-1])[::-1]  # settled from here all the way in
    return int(np.argmax(stays)) if stays.any() else int(prof.size - 1)


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
