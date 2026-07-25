"""Placement & masking: the art-direction layer.

The contract these pin: a placement is authored in METRES and must land in the same world position
at any resolution (08), masks are smooth-edged coverage in [0,1], and masking an effect is an exact
interpolation between "not applied" and "applied everywhere".
"""
import numpy as np
import pytest

import ops_filters
import placement


def _centroid(mask, cellsize):
    """Coverage-weighted centre in metres."""
    n, m = mask.shape
    y, x = np.mgrid[0:n, 0:m].astype(np.float64)
    w = mask.sum()
    return (float((x * mask).sum() / w * cellsize), float((y * mask).sum() / w * cellsize))


# --------------------------------------------------------------------------- #
# masks are coverage
# --------------------------------------------------------------------------- #
def test_disc_is_bounded_and_centred_where_asked():
    mask = placement.disc((128, 128), cellsize=10.0, center=(400.0, 700.0), radius=150.0, falloff=40.0)
    assert mask.min() >= 0.0 and mask.max() <= 1.0
    cx, cy = _centroid(mask, 10.0)
    assert abs(cx - 400.0) < 10.0 and abs(cy - 700.0) < 10.0


def test_disc_area_matches_the_requested_radius():
    cellsize, r = 5.0, 120.0
    mask = placement.disc((160, 160), cellsize=cellsize, center=(400.0, 400.0), radius=r)
    area = mask.sum() * cellsize * cellsize
    assert area == pytest.approx(np.pi * r * r, rel=0.05)


def test_placement_is_resolution_independent():
    """SCALE (08): the same metres-authored disc must occupy the same world position and area
    whether the grid is coarse or fine."""
    extent, center, r = 1000.0, (300.0, 620.0), 180.0
    areas, centres = [], []
    for n in (64, 128, 256):
        cellsize = extent / n
        mask = placement.disc((n, n), cellsize=cellsize, center=center, radius=r, falloff=30.0)
        areas.append(mask.sum() * cellsize * cellsize)
        centres.append(_centroid(mask, cellsize))
    assert max(areas) / min(areas) < 1.05, f"area drifted with resolution: {areas}"
    for cx, cy in centres:
        assert abs(cx - center[0]) < extent / 64 and abs(cy - center[1]) < extent / 64


def test_hard_edge_is_still_antialiased_to_one_cell():
    """falloff=0 must not produce a binary staircase — it is clamped to one cell of softness."""
    mask = placement.disc((96, 96), cellsize=10.0, center=(480.0, 480.0), radius=200.0, falloff=0.0)
    partial = np.count_nonzero((mask > 0.01) & (mask < 0.99))
    assert partial > 0, "hard edge left no antialiased boundary cells"


def test_falloff_widens_the_soft_edge():
    kw = dict(cellsize=10.0, center=(480.0, 480.0), radius=200.0)
    narrow = placement.disc((96, 96), falloff=20.0, **kw)
    wide = placement.disc((96, 96), falloff=120.0, **kw)
    count = lambda m: np.count_nonzero((m > 0.01) & (m < 0.99))
    assert count(wide) > count(narrow)


def test_rect_rotation_moves_coverage_but_conserves_area():
    kw = dict(cellsize=8.0, center=(400.0, 400.0), half_extent=(220.0, 60.0), falloff=10.0)
    flat = placement.rect((100, 100), rotation=0.0, **kw)
    turned = placement.rect((100, 100), rotation=np.pi / 2, **kw)
    assert flat.sum() == pytest.approx(turned.sum(), rel=0.05)   # same shape, turned
    assert not np.allclose(flat, turned)


def test_capsule_and_path_follow_their_spine():
    shape, cellsize = (128, 128), 8.0
    seg = placement.capsule(shape, cellsize, a=(200.0, 500.0), b=(800.0, 500.0), radius=40.0)
    assert seg[int(500 / cellsize), int(500 / cellsize)] > 0.9      # on the spine
    assert seg[int(200 / cellsize), int(500 / cellsize)] < 0.1      # well off it
    path = placement.path_mask(shape, cellsize,
                               points=[(150.0, 200.0), (500.0, 500.0), (850.0, 300.0)], radius=40.0)
    assert path[int(500 / cellsize), int(500 / cellsize)] > 0.9     # the elbow is covered
    assert path.sum() > seg.sum() * 0.5


def test_path_mask_rejects_a_degenerate_spine():
    with pytest.raises(ValueError):
        placement.path_mask((32, 32), 1.0, points=[(0.0, 0.0)], radius=2.0)


# --------------------------------------------------------------------------- #
# masking an effect
# --------------------------------------------------------------------------- #
def test_apply_masked_is_exactly_the_two_endpoints():
    rng = np.random.default_rng(0)
    base = rng.random((32, 32))
    modified = base + 5.0
    assert np.allclose(placement.apply_masked(base, modified, np.zeros((32, 32))), base)
    assert np.allclose(placement.apply_masked(base, modified, np.ones((32, 32))), modified)
    half = placement.apply_masked(base, modified, np.full((32, 32), 0.5))
    assert np.allclose(half, base + 2.5)


def test_apply_masked_confines_an_effect_to_the_mask():
    """The point of the whole layer: erode here, leave the rest untouched."""
    import erosion_thermal as T

    rng = np.random.default_rng(0)
    h = rng.random((64, 64)) * 30.0
    eroded = T.thermal_erosion(h, 0.4, iters=30)
    mask = placement.disc((64, 64), cellsize=1.0, center=(16.0, 16.0), radius=12.0, falloff=3.0)
    out = placement.apply_masked(h, eroded, mask)
    assert not np.allclose(out[mask > 0.9], h[mask > 0.9])          # changed inside
    assert np.allclose(out[mask < 1e-6], h[mask < 1e-6])            # untouched outside


def test_stamp_modes():
    base = np.full((16, 16), 5.0)
    patch = np.full((16, 16), 3.0)
    assert np.allclose(placement.stamp(base, patch, mode="max"), 5.0)
    assert np.allclose(placement.stamp(base, patch, mode="add"), 8.0)
    assert np.allclose(placement.stamp(base, patch, mode="replace"), 3.0)
    with pytest.raises(ValueError):
        placement.stamp(base, patch, mode="nope")


def test_stamp_respects_its_mask():
    base = np.zeros((32, 32))
    patch = np.full((32, 32), 10.0)
    mask = placement.disc((32, 32), cellsize=1.0, center=(8.0, 8.0), radius=5.0)
    out = placement.stamp(base, patch, mask=mask, mode="max")
    assert out[8, 8] == pytest.approx(10.0, rel=1e-6)
    assert out[28, 28] == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# placing a GENERATOR: transform the coordinates, not the raster
# --------------------------------------------------------------------------- #
def test_place_coords_is_an_exact_coordinate_shift():
    """ORACLE: a pure translation must offset the sample coordinates exactly — no interpolation."""
    n, cellsize = 128, 10.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    ox, oy = placement.place_coords(xx, yy, (n, n), cellsize, center=(320.0, 520.0))
    assert np.allclose(ox, xx - (320.0 / cellsize - n / 2))
    assert np.allclose(oy, yy - (520.0 / cellsize - n / 2))


def test_placing_at_the_native_centre_is_the_identity():
    import landforms

    n, cellsize = 96, 10.0
    plain = landforms.ridge((n, n), cellsize, seed=2)
    placed = landforms.ridge((n, n), cellsize, seed=2,
                             place=dict(center=(n / 2 * cellsize, n / 2 * cellsize)))
    assert np.allclose(plain, placed)


def test_placing_translates_the_feature_by_exactly_what_was_asked():
    """The crest must land where the layout says, and the interior must be the SAME terrain —
    up to the generator's own self-normalisation, which depends on what is in frame (measured
    global scale factor 1.0006, mean difference 0.013% of relief)."""
    import landforms

    n, cellsize, shift = 128, 10.0, 20
    plain = landforms.ridge((n, n), cellsize, seed=2)
    placed = landforms.ridge((n, n), cellsize, seed=2,
                             place=dict(center=((n / 2 + shift) * cellsize, n / 2 * cellsize)))
    assert int(np.argmax(placed.max(axis=0))) - int(np.argmax(plain.max(axis=0))) == shift
    overlap = np.abs(placed[:, shift:] - plain[:, :n - shift]).mean()
    assert overlap < 0.01 * np.ptp(plain), "placed terrain is not the same terrain, moved"


def test_coordinate_transform_keeps_detail_a_raster_transform_loses():
    """WHY placement belongs before sampling: resampling a raster is a low-pass filter. Generating
    at shifted coordinates is exact; translating the output blurs it."""
    import noise
    import ops_filters

    n, off = 192, 37.4                                    # non-integer: the realistic case
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    detail = lambda h: float(np.abs(h - ops_filters.gaussian(h, sigma=1.5)).mean())

    at_coords = noise.fbm((xx + off) / 40.0, (yy + off) / 40.0, seed=3, octaves=6)
    plain = noise.fbm(xx / 40.0, yy / 40.0, seed=3, octaves=6)
    as_raster = ops_filters.resample(plain, (n, n))        # a resample at the same size still filters
    x0 = np.clip(xx + off, 0, n - 1); y0 = np.clip(yy + off, 0, n - 1)
    i0 = np.floor(x0).astype(int); j0 = np.floor(y0).astype(int)
    i1 = np.minimum(i0 + 1, n - 1); j1 = np.minimum(j0 + 1, n - 1)
    fx, fy = x0 - i0, y0 - j0
    as_raster = (plain[j0, i0] * (1 - fx) * (1 - fy) + plain[j0, i1] * fx * (1 - fy)
                 + plain[j1, i0] * (1 - fx) * fy + plain[j1, i1] * fx * fy)

    core = (slice(0, n - 60), slice(0, n - 60))            # exclude the raster path's edge clamp
    assert detail(as_raster[core]) < 0.9 * detail(at_coords[core]), (
        "expected the raster transform to lose detail the coordinate transform keeps")


# --------------------------------------------------------------------------- #
# the placement IS an affine matrix — and sampling uses its inverse
# --------------------------------------------------------------------------- #
def test_place_coords_is_exactly_the_inverse_affine():
    """`place_coords` is the hand-decomposed inverse of `affine`. Proving they agree pins the whole
    convention — including that sampling uses M^-1, the classic sign error in texture transforms."""
    n, cellsize = 128, 10.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    for kw in ({"center": (320.0, 520.0)},
               {"center": (300.0, 300.0), "rotation": 0.7},
               {"center": (400.0, 200.0), "rotation": -0.3, "scale": 1.8}):
        hand = placement.place_coords(xx, yy, (n, n), cellsize, **kw)
        M = placement.affine(center=(kw["center"][0] / cellsize, kw["center"][1] / cellsize),
                             rotation=kw.get("rotation", 0.0), scale=kw.get("scale", 1.0),
                             pivot=(n / 2, n / 2))
        mat = placement.sample_coords(xx, yy, M)
        assert np.allclose(hand[0], mat[0]) and np.allclose(hand[1], mat[1]), kw


def test_affine_round_trip_is_the_identity():
    n = 64
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    M = placement.affine(center=(12.0, -7.0), rotation=0.4, scale=(1.7, 0.6), shear=0.25)
    fx, fy = placement.transform_coords(xx, yy, M)
    bx, by = placement.sample_coords(fx, fy, M)
    assert np.allclose(bx, xx) and np.allclose(by, yy)


def test_compose_equals_applying_in_sequence():
    """Composing to ONE matrix must equal applying each in turn — the property that lets a chain of
    placements collapse into a single evaluation."""
    n = 48
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    A = placement.affine(center=(10.0, 0.0))
    B = placement.affine(rotation=np.pi / 2)
    C = placement.affine(scale=(2.0, 0.5))
    x1, y1 = placement.transform_coords(xx, yy, A)
    x2, y2 = placement.transform_coords(x1, y1, B)
    x3, y3 = placement.transform_coords(x2, y2, C)
    xc, yc = placement.transform_coords(xx, yy, placement.compose(A, B, C))
    assert np.allclose(x3, xc) and np.allclose(y3, yc)


def test_affine_supports_non_uniform_scale_and_shear():
    """What the hand-decomposed form cannot express: per-axis scale and shear."""
    M = placement.affine(scale=(2.0, 0.5), shear=0.3)
    assert M[0, 0] == pytest.approx(2.0) and M[1, 1] == pytest.approx(0.5)
    assert M[0, 1] == pytest.approx(0.3 * 0.5)          # shear composed with the y scale
    n = 32
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    fx, fy = placement.transform_coords(xx, yy, M)
    assert np.ptp(fx) > np.ptp(xx) and np.ptp(fy) < np.ptp(yy)
