"""Oracles for the analysis & masks layer (06-analysis-masks.md). Each function is checked
against a terrain whose analytic answer is known: a constant-slope plane, a paraboloid
(exact discrete Laplacian), a pit (occlusion), and the partition property of a material stack.
"""
import numpy as np
import inputs
import analysis as A


def _paraboloid(n=41, R=500.0, cellsize=10.0):
    """h = -(X^2 + Y^2) / (2R) in world metres. grad^2 h = -2/R exactly, so the discrete
    5-point Laplacian of it is -2/R on every interior cell (a quadratic is reproduced exactly)."""
    c = (n - 1) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    X = (xx - c) * cellsize
    Y = (yy - c) * cellsize
    return -(X * X + Y * Y) / (2.0 * R)


def test_slope_of_constant_slope_plane():
    """A plane of gradient g has slope tan = g everywhere (central and Horn agree)."""
    g = 0.1
    h = inputs.constant_slope(n=48, gradient=g)
    for method in ("central", "horn"):
        s = A.slope(h, cellsize=1.0, method=method)
        assert np.allclose(s[2:-2, 2:-2], g, atol=1e-9), method


def test_aspect_is_constant_on_a_plane():
    """A uniform plane faces one direction everywhere — aspect has ~zero spread interior."""
    h = inputs.constant_slope(n=48, gradient=0.2)
    a = A.aspect(h, cellsize=1.0)[2:-2, 2:-2]
    assert np.std(a) < 1e-6


def test_northness_sign_matches_facing():
    """+1 on a NORTH-facing slope (surface dips toward row 0), -1 facing south. Row index increases
    southward, so this pins the -sin(aspect) orientation — a wrong sign puts snow on the sunny face."""
    yy = np.mgrid[0:21, 0:21][0].astype(float)
    north_facing = 2.0 * yy                                # h rises with row -> downhill toward row 0 (north)
    south_facing = -2.0 * yy
    assert A.northness(A.aspect(north_facing))[5:-5, 5:-5].mean() > 0.9
    assert A.northness(A.aspect(south_facing))[5:-5, 5:-5].mean() < -0.9


def test_horn_and_central_gradient_agree_in_sign():
    """The two gradient estimators must agree on the SIGN of both components (Horn smooths, so
    magnitudes differ slightly, but a flipped dz/dy is a bug — it y-flips analysis.normals)."""
    yy, xx = np.mgrid[0:24, 0:24].astype(float)
    h = 5.0 * yy + 3.0 * xx
    cx, cy = A.gradient(h, 1.0, "central")
    hx, hy = A.gradient(h, 1.0, "horn")
    assert np.sign(cy[2:-2, 2:-2]).mean() == np.sign(hy[2:-2, 2:-2]).mean() == 1.0
    assert np.sign(cx[2:-2, 2:-2]).mean() == np.sign(hx[2:-2, 2:-2]).mean() == 1.0


def test_profile_curvature_is_positive_in_concave_hollows():
    """Profile curvature must be >0 in a concave valley/hollow and <0 on a convex ridge — the
    convention the docstring states AND derive_substances relies on to deposit sediment in hollows
    (plan/mean are already concave-positive; profile was the sign outlier)."""
    bowl = _paraboloid(n=41, R=500.0, cellsize=10.0) * -1.0   # concave-up bowl
    dome = _paraboloid(n=41, R=500.0, cellsize=10.0)          # convex dome
    assert A.curvature(bowl, 10.0, "profile")[20, 6] > 0.0    # flank of a concave hollow
    assert A.curvature(dome, 10.0, "profile")[20, 6] < 0.0    # flank of a convex ridge


def test_laplacian_of_paraboloid_is_exact():
    """The decisive curvature oracle: discrete Laplacian of -(X^2+Y^2)/2R equals -2/R."""
    R, cs = 500.0, 10.0
    h = _paraboloid(n=41, R=R, cellsize=cs)
    lap = A.laplacian(h, cellsize=cs)
    assert np.allclose(lap[2:-2, 2:-2], -2.0 / R, atol=1e-9)


def test_curvature_flat_guard_and_finite():
    """Curvature is guarded to 0 where the surface is flat (p<eps at the dome apex) and is
    finite everywhere; a convex dome reads convex (Laplacian < 0)."""
    h = _paraboloid(n=41, R=500.0, cellsize=10.0)
    for kind in ("profile", "plan", "mean"):
        c = A.curvature(h, cellsize=10.0, kind=kind)
        assert np.all(np.isfinite(c))
    assert A.laplacian(h, cellsize=10.0)[10:-10, 10:-10].mean() < 0.0   # convex


def test_ao_zero_on_flat_and_positive_in_a_pit():
    """AO is 0 on an open plane (nothing occludes) and larger inside a pit (walls occlude)."""
    flat = inputs.flat(n=48)
    ao_flat = A.horizon_ao(flat, cellsize=1.0)
    assert np.allclose(ao_flat, 0.0, atol=1e-9)

    pit = inputs.inverted_cone(n=49, depth=12.0)
    ao_pit = A.horizon_ao(pit, cellsize=1.0)
    assert ao_pit.min() >= -1e-9 and ao_pit.max() <= 1.0 + 1e-9
    c = 49 // 2
    assert ao_pit[c, c] > ao_pit[2, 2] + 1e-3          # centre more occluded than the rim


def test_twi_is_finite_on_flats_and_monotone_in_area():
    """Both guards (06): TWI stays finite where slope -> 0, and rises with drainage area."""
    slope0 = np.zeros((8, 8))                            # flat -> tan 0
    area = np.full((8, 8), 100.0)
    assert np.all(np.isfinite(A.twi(area, slope0, cellsize=1.0)))

    s = np.full((8, 8), 0.1)
    low = A.twi(np.full((8, 8), 10.0), s, cellsize=1.0)
    high = A.twi(np.full((8, 8), 1000.0), s, cellsize=1.0)
    assert np.all(high > low)


def test_selectors_are_masks_in_unit_range():
    """smoothstep and band_select stay in [0,1]; band_select is ~1 inside the band, ~0 out."""
    x = np.linspace(0.0, 100.0, 200)
    s = A.smoothstep(20.0, 40.0, x)
    assert s.min() >= 0.0 and s.max() <= 1.0
    assert s[x < 15].max() < 1e-6 and s[x > 45].min() > 1.0 - 1e-6

    b = A.band_select(x, lo=30.0, hi=60.0, w=3.0)
    assert b.min() >= 0.0 and b.max() <= 1.0
    assert b[(x > 40) & (x < 50)].min() > 0.9          # inside the band
    assert b[x < 20].max() < 0.1 and b[x > 70].max() < 0.1


def test_material_masks_partition():
    """A priority material stack partitions: every mask in [0,1] and they sum to ~1 (else a
    splatmap silently rescales them)."""
    n, cs = 40, 20.0
    rng = np.random.default_rng(3)
    h = _paraboloid(n=n, R=300.0, cellsize=cs) + rng.uniform(0, 30, (n, n))
    s = A.slope(h, cellsize=cs)
    area = np.abs(rng.normal(0, 1, (n, n))).cumsum().reshape(n, n) * cs * cs
    stack = A.derive_materials(h, s, area, cs)

    total = np.zeros((n, n))
    for name, m in stack:
        assert m.min() >= -1e-9 and m.max() <= 1.0 + 1e-9, name
        total = total + m
    assert np.allclose(total, 1.0, atol=1e-6)          # partition
    idx = A.dominant_material(stack)
    assert idx.min() >= 0 and idx.max() < len(stack)
