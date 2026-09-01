"""Placement & masking: the art-direction layer.

The contract these pin: a placement is authored in METRES and must land in the same world position
at any resolution (08), masks are smooth-edged coverage in [0,1], and masking an effect is an exact
interpolation between "not applied" and "applied everywhere".

⚠️ AND ONE LESSON ABOUT MEASURING, WHICH COST THIS FILE A WRONG CAUSE IN `10`. The raster-vs-
coordinate experiment at the bottom is also a sampling experiment, and its window-to-window spread
turned out to depend on SAMPLE-GRID COMMENSURABILITY — whether `n / (scale * lacunarity**(octaves-1))`
lands on exactly 2 sample pixels per cell of the finest octave — and not, as `10` asserted for
several revisions, on the lacunarity-2 pinch lattice. Every number in the wrong version was correct;
only the mechanism was invented, and no row that checks a number can catch that. The rows that can
are `test_the_window_spread_tracks_px_per_cell_not_the_lacunarity` and
`test_the_spread_follows_px_per_cell_at_other_resolutions`, which vary the supposed cause
independently of the effect. When a measurement is explained here, that is the shape the guard has
to have.
"""
import numpy as np
import pytest

import noise
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


def _bilinear_shift(f, dx, dy):
    """The lossy operation under test: translate a RASTER by resampling it."""
    n, m = f.shape
    yy, xx = np.mgrid[0:n, 0:m].astype(float)
    sx, sy = xx + dx, yy + dy
    x0 = np.clip(np.floor(sx).astype(int), 0, m - 1); x1 = np.clip(x0 + 1, 0, m - 1)
    y0 = np.clip(np.floor(sy).astype(int), 0, n - 1); y1 = np.clip(y0 + 1, 0, n - 1)
    tx = np.clip(sx - x0, 0.0, 1.0); ty = np.clip(sy - y0, 0.0, 1.0)
    return ((f[y0, x0] * (1 - tx) + f[y0, x1] * tx) * (1 - ty)
            + (f[y1, x0] * (1 - tx) + f[y1, x1] * tx) * ty)


def _detail(f):
    """Fine-detail energy as mean |laplacian| — the band a low-pass filter removes."""
    return float(np.abs(4 * f[1:-1, 1:-1] - f[1:-1, :-2] - f[1:-1, 2:]
                        - f[:-2, 1:-1] - f[2:, 1:-1]).mean())


# --------------------------------------------------------------------------- #
# THE EXPERIMENT, DEFINED ONCE
#
# ⚠️ THIS BLOCK IS THE SINGLE SOURCE OF THE SETUP. `tests/test_chapter_numbers.py` re-runs the same
# experiment to check what `10` prints about it, and it IMPORTS these names rather than restating
# them. It used to carry its own copy of `n`, `scale`, `seed`, `lacunarity` and the offsets, which
# meant this file could be retuned while the chapter rows went on measuring the abandoned setup and
# passing — a duplicated constant is a guard that silently stops guarding.
# --------------------------------------------------------------------------- #
N = 192
SCALE = 3.0                     # base-noise cells across the grid
SEED = 7
OCTAVES = 6
LACUNARITY = 2.03               # the shipped detuned value (`01`, tests/test_noise_pinch.py)
GAIN = 0.5
SHIFT_FRAC = (0.037, 0.023)     # fractions of N — deliberately non-integer: the worst case
WINDOW_COUNT = 40
WINDOW_RNG_SEED = 3
WINDOW_SPAN = 400.0             # window offsets drawn uniformly from ±WINDOW_SPAN/2 cells

# `scale_for_px_per_cell(2.0)` to six significant figures — the retuned setting `10` tabulates as
# the falsifying cell: detuned lacunarity, finest octave back on exactly 2 sample px per cell.
SCALE_AT_TWO_PX = 2.78478


def px_per_cell(n=N, scale=SCALE, lacunarity=LACUNARITY, octaves=OCTAVES):
    """Sample pixels per lattice cell of the FINEST octave.

    The finest octave runs at `lacunarity**(octaves-1)` times the base frequency and the grid spans
    `scale` base cells in `n` pixels, so it is `n / (scale * lacunarity**(octaves-1))`. This, not
    the lacunarity, is what the window-to-window spread below tracks — see
    `test_the_window_spread_tracks_px_per_cell_not_the_lacunarity`.
    """
    return n / (scale * lacunarity ** (octaves - 1))


def scale_for_px_per_cell(target, n=N, lacunarity=LACUNARITY, octaves=OCTAVES):
    """Inverse of `px_per_cell`: the `scale` that puts the finest octave at `target` px/cell."""
    return n / (target * lacunarity ** (octaves - 1))


def experiment_grid(n=N):
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    return xx, yy


def experiment_build(n=N, scale=SCALE, lacunarity=LACUNARITY):
    """The field under test: `OCTAVES`-octave fBm on an n² grid spanning `scale` base cells."""
    return lambda gx, gy: noise.fbm(gx / n * scale, gy / n * scale, seed=SEED,
                                    octaves=OCTAVES, lacunarity=lacunarity, gain=GAIN)


_RATIO_CACHE = {}


def window_ratios(n=N, scale=SCALE, lacunarity=LACUNARITY,
                  nwin=WINDOW_COUNT, rng_seed=WINDOW_RNG_SEED):
    """Detail energy of `nwin` random windows of the same fBm, each as a ratio to the base window.

    Cached because the chapter-number harness asks for the same keys this file does, and each call
    is `nwin` six-octave evaluations.
    """
    key = (n, scale, lacunarity, nwin, rng_seed)
    if key not in _RATIO_CACHE:
        xx, yy = experiment_grid(n)
        build = experiment_build(n, scale, lacunarity)
        base = _detail(build(xx, yy))
        rng = np.random.RandomState(rng_seed)
        _RATIO_CACHE[key] = np.array(
            [_detail(build(xx + ox, yy + oy)) / base
             for ox, oy in rng.rand(nwin, 2) * WINDOW_SPAN - WINDOW_SPAN / 2.0])
    return _RATIO_CACHE[key]


def window_spread(**kw):
    """Window-to-window spread of detail energy, as the STANDARD DEVIATION of those ratios.

    ⚠️ std, and not `max |r-1|`, on purpose. The max is an extreme-value statistic: it grows with
    the sample count by construction (measured 0.40 / 0.54 / 0.79 % at 5 / 40 / 320 windows on the
    shipped setup) and it swings 2:1 across the RNG seed (0.49-0.97% over `RandomState(0..24)`,
    median 0.62%; the seed this file draws is the 3rd lowest of those 25, so quoting it prints an
    unrepresentatively small number). A figure that moves that much with how many samples you drew
    and which seed drew them is a property of the draw, not of the terrain. `std` converges instead
    — 0.17 / 0.22 / 0.25 % at the same three window counts — so it is what `10` prints.
    """
    return float(window_ratios(**kw).std())


def test_the_experiment_is_not_sample_grid_commensurate():
    """⚠️ THE GUARD ON THE HEADLINE FIX: reverting `LACUNARITY` to 2.0 must not pass silently.

    Every other row here happens to survive that revert — the raster losses barely move, and the
    coordinate-placement ratios stay positive. What does not survive is this: at `lacunarity=2.0`
    with `SCALE=3.0` and `OCTAVES=6`, `px_per_cell` is exactly 2.0000, the sample grid lands on the
    finest octave's lattice, and the whole measurement degenerates (2.31% window spread against
    0.22%). Guarding the constant rather than only its consequences is the point: a value this file
    was deliberately moved off must not be reachable by a one-character edit that nothing notices.
    """
    px = px_per_cell()
    assert abs(px - 2.0) > 0.1, (
        "the finest octave is at %.4f px/cell — on or beside the degenerate 2.0 commensurability "
        "this experiment exists to avoid" % px)
    assert abs(px - 1.0) > 0.1, (
        "the finest octave is at %.4f px/cell, on the 1.0 (fully aliased) point" % px)


def test_the_window_spread_tracks_px_per_cell_not_the_lacunarity():
    """⚠️ THE ROW THAT PINS THE CAUSE RATHER THAN THE NUMBER.

    `10` used to explain the old build's large window-to-window spread as the lacunarity-2 PINCH
    LATTICE — the un-shifted base window sitting where every octave is zero at once and so being
    systematically flatter. That was false, and no amount of pinning the numbers could have caught
    it: the numbers were right and the mechanism was wrong.

    The falsification is a 2x2. Lacunarity 2 is neither necessary (detune it and retune `scale` so
    the finest octave is back at 2 px/cell — the spread returns in full) nor sufficient (keep
    lacunarity at exactly 2 and move `scale` so it is not — the spread vanishes). What the spread
    follows, in all four cells, is `px_per_cell`. Restore the old story and this row fails, because
    the old story predicts the two lacunarity-2 cells to be the large ones.
    """
    assert abs(px_per_cell(scale=SCALE_AT_TWO_PX, lacunarity=2.03) - 2.0) < 1e-4, (
        "SCALE_AT_TWO_PX no longer puts the finest octave at 2 px/cell")
    commensurate = {
        "lacunarity 2.03, scale retuned to 2 px/cell":
            window_spread(scale=SCALE_AT_TWO_PX, lacunarity=2.03),
        "lacunarity 2.00, scale 3.0 (2 px/cell)":
            window_spread(scale=3.0, lacunarity=2.0),
    }
    incommensurate = {
        "lacunarity 2.03, scale 3.0 (shipped, 1.86 px/cell)":
            window_spread(),
        "lacunarity 2.00, scale 3.1 (1.94 px/cell)":
            window_spread(scale=3.1, lacunarity=2.0),
    }
    assert min(commensurate.values()) > 0.01, (
        "2 px/cell must produce the large spread at EITHER lacunarity: %s" % commensurate)
    assert max(incommensurate.values()) < 0.01, (
        "off 2 px/cell the spread must collapse at EITHER lacunarity: %s" % incommensurate)
    assert min(commensurate.values()) > 5.0 * max(incommensurate.values()), (
        "commensurability must separate these cleanly: %s vs %s" % (commensurate, incommensurate))


@pytest.mark.parametrize("n", [128, 256])
def test_the_spread_follows_px_per_cell_at_other_resolutions(n):
    """The control that rules out `n = 192` itself being the special thing.

    Hold lacunarity at 2.0 and vary only the window size: the spread appears wherever `scale` puts
    the finest octave at 2 px/cell and is absent wherever it does not, at 128 and at 256 exactly as
    at 192. It is a property of the sampling ratio, not of the resolution.
    """
    at_two = window_spread(n=n, scale=scale_for_px_per_cell(2.0, n=n, lacunarity=2.0),
                           lacunarity=2.0, nwin=12)
    off_two = window_spread(n=n, scale=3.0, lacunarity=2.0, nwin=12)
    assert at_two > 0.015, "no spread at 2 px/cell, n=%d: %.5f" % (n, at_two)
    assert off_two < 0.01, "spread survived off 2 px/cell, n=%d: %.5f" % (n, off_two)
    assert at_two > 3.0 * off_two, "n=%d: %.5f vs %.5f" % (n, at_two, off_two)


def test_raster_transform_loses_detail_that_placement_keeps():
    """WHY placement transforms coordinates instead of rasters, as a number rather than an assertion.

    Bilinear resampling is a low-pass filter, so every raster move costs fine detail and the losses
    compound. Evaluating the generator at moved coordinates is the same function sampled elsewhere,
    so it costs nothing however many times you move it. The percentages quoted in `placement.py` and
    references/10 are pinned here; they are metric-dependent (mean |laplacian|) and meaningless
    without that qualifier, which is the point of measuring rather than asserting.

    LACUNARITY. This measured at `lacunarity=2.0` until it was the last working use of that value
    left in the repo — the degenerate case `01` and `test_noise_pinch.py` exist to warn about, where
    every octave's zero set coincides and the base window sits on a grid of exact pinch points. It
    now uses `noise.fbm`'s shipped `2.03`, so the terrain under test is terrain the skill would
    actually recommend generating. The numbers moved when it changed; `10` was re-measured with it.

    ⚠️ The detuning also, incidentally, moved the finest octave off exactly 2 sample pixels per
    lattice cell — which is what actually fixed the window-ratio spread below, and is guarded
    separately by `test_the_experiment_is_not_sample_grid_commensurate` and
    `test_the_window_spread_tracks_px_per_cell_not_the_lacunarity`. The window tolerance here is set
    tight enough that reverting `LACUNARITY` to 2.0 fails this row too: the ratios go from a
    measured max |r-1| of 0.0030 to 0.0910.
    """
    xx, yy = experiment_grid()
    build = experiment_build()
    h = build(xx, yy)
    base = _detail(h)
    dx, dy = SHIFT_FRAC[0] * N, SHIFT_FRAC[1] * N

    raster, losses, placed_ratios = h, [], []
    for k in range(1, 5):
        raster = _bilinear_shift(raster, dx, dy)
        losses.append(1.0 - _detail(raster) / base)
        # coordinate-space placement of the SAME move, k times over — one evaluation, no filtering
        placed = build(xx + k * dx, yy + k * dy)
        placed_ratios.append(_detail(placed) / base)
        assert _detail(placed) > _detail(raster), (
            f"move {k}: coordinate placement ({_detail(placed):.5f}) must stay sharper than the "
            f"resampled raster ({_detail(raster):.5f})")

    # Placement lands on a DIFFERENT WINDOW of the same fBm, and detail energy genuinely varies
    # between windows — so the invariant is "no systematic decline", not "identical". Reading that
    # window variance as a loss would be the measurement failing, not the code. 0.02 is ~6x the
    # measured 0.0030 and ~4x below the 0.0910 the commensurate build produces; the old 0.15 was a
    # 50x margin that could not tell the two regimes apart.
    assert max(abs(r - 1.0) for r in placed_ratios) < 0.02, placed_ratios
    assert placed_ratios[-1] > placed_ratios[0] - 0.02, (
        f"coordinate placement must not degrade with depth, got {placed_ratios}")

    assert 0.15 < losses[0] < 0.35, f"one raster move lost {losses[0]:.1%}, expected ~29%"
    assert 0.45 < losses[3] < 0.65, f"four raster moves lost {losses[3]:.1%}, expected ~57%"
    assert losses == sorted(losses), f"raster loss must compound with each move, got {losses}"
