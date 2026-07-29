"""Oracles for the primitives/ops/filters toolbox (10-primitives-ops-filters.md). These nodes
have no papers, so each is pinned to the property that makes it correct: SDF exactness, smin
below the hard min, edge-preserving filters that keep a step where Gaussian smears it, and the
morphology identities (dilate >= h >= erode, opening idempotent, closing fills a pit).
"""
import numpy as np
import inputs
import ops_filters as F


def test_sdf_circle_is_exact_and_signed():
    yy, xx = np.mgrid[-5:6, -5:6].astype(float)
    d = F.sd_circle(xx, yy, r=3.0)
    assert np.allclose(d, np.hypot(xx, yy) - 3.0)
    assert d[5, 5] < 0 and d[0, 0] > 0                 # centre inside, corner outside


def test_sd_box_sign():
    yy, xx = np.mgrid[-5:6, -5:6].astype(float)
    d = F.sd_box(xx, yy, 2.0, 2.0)
    assert d[5, 5] < 0                                  # centre inside
    assert d[0, 0] > 0                                  # corner outside
    assert abs(F.sd_box(np.array(2.0), np.array(0.0), 2.0, 2.0)) < 1e-9   # on the face


def test_sd_convex_polygon_matches_box_and_signs():
    yy, xx = np.mgrid[-5:6, -5:6].astype(float)
    # a 2x2 axis-aligned square as four half-planes == sd_box on its faces/interior
    normals = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    offsets = [2.0, 2.0, 2.0, 2.0]
    d = F.sd_convex_polygon(xx, yy, normals, offsets)
    box = F.sd_box(xx, yy, 2.0, 2.0)
    inside = box <= 0                                    # half-plane form is exact where sd_box is (interior/faces)
    assert np.allclose(d[inside], box[inside])
    assert d[5, 5] < 0 and d[0, 0] > 0                   # centre inside, corner outside
    assert abs(F.sd_convex_polygon(np.array(2.0), np.array(0.0), normals, offsets)) < 1e-9   # on a face
    # a rotated (non-axis-aligned) triangle is still sign-correct
    tri_n = [(np.cos(a), np.sin(a)) for a in (0.3, 0.3 + 2.094, 0.3 + 4.188)]
    dt = F.sd_convex_polygon(xx, yy, tri_n, [1.5, 1.5, 1.5])
    assert dt[5, 5] < 0                                  # origin is inside the centred triangle


def test_smin_below_hard_min_and_converges():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 5, 500)
    b = rng.normal(0, 5, 500)
    assert np.all(F.smin(a, b, 2.0) <= np.minimum(a, b) + 1e-9)
    assert np.all(F.smax(a, b, 2.0) >= np.maximum(a, b) - 1e-9)
    assert np.allclose(F.smin(a, b, 1e-6), np.minimum(a, b), atol=1e-4)   # k->0 recovers min


def test_gaussian_constant_and_variance():
    assert np.allclose(F.gaussian(np.full((32, 32), 3.7), sigma=2.0), 3.7)
    noisy = np.random.default_rng(1).normal(0, 1, (64, 64))
    assert F.gaussian(noisy, sigma=2.0).std() < noisy.std()


def _edge_jump(h):
    """Mean height jump across the step edge (inputs.step has it at the mid column)."""
    mid = h.shape[1] // 2
    return float((h[:, mid] - h[:, mid - 1]).mean())


def test_median_removes_spike_and_keeps_step():
    sp = inputs.spike(n=32, base=0.0, value=100.0)
    assert F.median(sp, r=1)[16, 16] == 0.0            # spike gone
    step = inputs.step(n=32, lo=0.0, hi=5.0)
    assert np.allclose(F.median(step, r=1)[:, 2:-2], step[:, 2:-2])   # step preserved


def test_bilateral_preserves_the_edge_gaussian_smears():
    step = inputs.step(n=48, lo=0.0, hi=5.0)
    orig = _edge_jump(step)
    bilat = _edge_jump(F.bilateral(step, sigma_s=2.0, sigma_r=1.0))
    gauss = _edge_jump(F.gaussian(step, sigma=2.0))
    assert bilat > 0.9 * orig                          # cliff stays sharp
    assert gauss < bilat                               # Gaussian rounded it off


def test_guided_filter_constant_and_edge():
    assert np.allclose(F.guided_filter(np.full((32, 32), 2.0), r=2, eps=1e-3), 2.0)
    step = inputs.step(n=48, lo=0.0, hi=5.0)
    assert _edge_jump(F.guided_filter(step, r=3, eps=0.04)) > _edge_jump(F.gaussian(step, 2.0))


def test_perona_malik_preserves_edge_and_denoises():
    step = inputs.step(n=48, lo=0.0, hi=5.0)
    assert _edge_jump(F.perona_malik(step, K=1.0, iters=20)) > 0.9 * _edge_jump(step)
    noisy = inputs.flat(48) + np.random.default_rng(2).normal(0, 0.3, (48, 48))
    assert F.perona_malik(noisy, K=1.0, iters=20).std() < noisy.std()


def test_morphology_identities():
    h = np.random.default_rng(3).normal(0, 1, (32, 32))
    assert np.all(F.dilate(h, 1) >= h - 1e-9) and np.all(F.erode(h, 1) <= h + 1e-9)
    assert np.all(F.closing(h, 1) >= h - 1e-9) and np.all(F.opening(h, 1) <= h + 1e-9)
    assert np.all(F.tophat(h, 1) >= -1e-9)
    assert np.allclose(F.opening(F.opening(h, 1), 1), F.opening(h, 1))   # idempotent


def test_closing_fills_a_one_cell_pit():
    h = np.full((16, 16), 5.0)
    h[8, 8] = 0.0
    assert F.closing(h, r=1)[8, 8] == 5.0              # pit filled by the SE


def test_warps_are_identity_at_zero():
    yy, xx = np.mgrid[0:8, 0:8].astype(float)
    tx, ty = F.twist(xx, yy, 3.5, 3.5, k=0.0)
    assert np.allclose(tx, xx) and np.allclose(ty, yy)
    bx, by = F.bend(xx, yy, k=0.0)
    assert np.allclose(bx, xx) and np.allclose(by, yy)


def test_remap_uses_written_constants():
    a = np.array([0.0, 5.0, 10.0])
    assert np.allclose(F.remap(a, 0.0, 10.0), [0.0, 0.5, 1.0])


def test_linear_gradient_is_a_directional_ramp():
    """0->1 along the angle, clamped, coordinate-based (no data dependence)."""
    yy, xx = np.mgrid[0:10, 0:10].astype(float)
    g = F.linear_gradient(xx, yy, angle=0.0, length=9.0)                # +x ramp over 9 cells
    assert np.allclose(g[:, 0], 0.0) and np.allclose(g[:, 9], 1.0)      # ends hit 0 and 1
    assert np.all(np.diff(g, axis=1) >= -1e-12)                         # monotone along +x
    gy = F.linear_gradient(xx, yy, angle=np.pi / 2, length=9.0)         # +y ramp
    assert np.allclose(gy[0, :], 0.0) and np.allclose(gy[9, :], 1.0)


def test_curve_generalises_remap_and_is_monotone():
    """curve through 2 points == remap; a monotone curve is order-preserving (never inverts)."""
    a = np.linspace(0.0, 10.0, 11)
    assert np.allclose(F.curve(a, [0.0, 10.0], [0.0, 1.0]), F.remap(a, 0.0, 10.0))
    c = F.curve(a, [0.0, 5.0, 10.0], [0.0, 0.9, 1.0])                   # steep low, flat high (an S-ish curve)
    assert np.all(np.diff(c) >= -1e-12)                                # monotone -> no terrain inversion
    assert c[5] == 0.9


def test_levels_clips_gammas_and_maps():
    a = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    lv = F.levels(a, 0.25, 0.75)                                        # clip to [.25,.75] -> [0,1]
    assert lv[0] == 0.0 and lv[-1] == 1.0 and abs(lv[2] - 0.5) < 1e-9
    bright = F.levels(a, 0.0, 1.0, gamma=2.0)                           # gamma>1 lifts midtones
    assert bright[2] > 0.5


def test_histogram_equalize_flattens_and_preserves_order():
    """Equalized output is monotone in the input (no inversion) and its histogram is far flatter
    than the (skewed) input's — every band gets ~equal area."""
    rng = np.random.default_rng(0)
    h = rng.random((64, 64)) ** 3                                       # strongly skewed toward 0
    e = F.histogram_equalize(h, bins=64)
    order = np.argsort(h, axis=None)
    assert np.all(np.diff(e.flatten()[order]) >= -1e-9)                # monotone in h -> order-preserving
    flat = np.histogram(e, bins=16)[0]
    skew = np.histogram(h, bins=16)[0]
    assert flat.std() < skew.std()                                     # flatter histogram than the input


def test_unsharp_zero_amount_is_identity_and_boosts_edges():
    h = inputs.step(16, lo=0.0, hi=1.0).astype(float)
    assert np.allclose(F.unsharp(h, 1.0, amount=0.0), h)               # amount 0 == identity
    s = F.unsharp(h, 1.0, amount=1.0)
    assert s.max() > h.max() and s.min() < h.min()                     # overshoot/undershoot at the edge
