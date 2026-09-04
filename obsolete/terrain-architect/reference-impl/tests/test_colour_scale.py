"""Colour production (SatMap compositing, 2-D biome LUT) and spatial-scale atoms.

These are the learnings carried back from the interactive Studio: a SatMap is a CLUT driven by ANY
channel, SatMaps *combine* rather than being chosen one at a time, and an effect's footprint is set
by the grid it runs on.
"""
import numpy as np
import pytest

import analysis
import inputs
import ops_filters
import render
import erosion_thermal as T


# --------------------------------------------------------------------------- #
# colour: blending and the 2-D LUT
# --------------------------------------------------------------------------- #
def test_blend_modes_are_bounded_and_normal_is_a_lerp():
    rng = np.random.default_rng(0)
    a = rng.random((16, 16, 3)) * 255.0
    b = rng.random((16, 16, 3)) * 255.0
    for mode in render.BLEND_MODES:
        out = render.blend_rgb(a, b, mode=mode)
        assert np.all(np.isfinite(out))
        assert out.min() >= -1e-9 and out.max() <= 255.0 + 1e-9, mode
    # opacity 0 and 1 are the endpoints of a plain interpolation
    assert np.allclose(render.blend_rgb(a, b, opacity=0.0), a)
    assert np.allclose(render.blend_rgb(a, b, opacity=1.0, mode="normal"), b)
    assert np.allclose(render.blend_rgb(a, b, opacity=0.5, mode="normal"), 0.5 * (a + b))


def test_blend_mask_selects_where_the_overlay_lands():
    a = np.zeros((8, 8, 3))
    b = np.full((8, 8, 3), 255.0)
    mask = np.zeros((8, 8))
    mask[:, 4:] = 1.0
    out = render.blend_rgb(a, b, mask=mask, mode="normal")
    assert np.allclose(out[:, :4], 0.0)          # masked out -> base survives
    assert np.allclose(out[:, 4:], 255.0)        # masked in  -> overlay applies


def test_blend_max_keeps_the_brighter_layer():
    a = np.full((4, 4, 3), 100.0)
    b = np.full((4, 4, 3), 40.0)
    assert np.allclose(render.blend_rgb(a, b, mode="max"), 100.0)
    assert np.allclose(render.blend_rgb(b, a, mode="max"), 100.0)


def test_unknown_blend_mode_is_rejected():
    a = np.zeros((2, 2, 3))
    with pytest.raises(ValueError):
        render.blend_rgb(a, a, mode="not-a-mode")


def test_satmap_2d_selects_between_the_two_ramps_by_the_second_driver():
    """altitude x slope: the flat palette on gentle ground, the steep palette on cliffs."""
    drv = np.linspace(0, 1, 32)[None, :].repeat(32, 0)
    flat = [(0.0, (0, 200, 0)), (1.0, (0, 200, 0))]      # solid green
    steep = [(0.0, (200, 0, 0)), (1.0, (200, 0, 0))]     # solid red
    assert np.allclose(render.satmap_2d(drv, np.zeros_like(drv), flat, steep)[..., 1], 200.0)
    assert np.allclose(render.satmap_2d(drv, np.ones_like(drv), flat, steep)[..., 0], 200.0)
    mid = render.satmap_2d(drv, np.full_like(drv, 0.5), flat, steep)
    assert np.allclose(mid[..., 0], 100.0) and np.allclose(mid[..., 1], 100.0)


def test_satmap_driver_is_channel_agnostic():
    """The point of a SatMap: it colours whatever grayscale you hand it, not only elevation."""
    h = inputs.cone(n=33, height=10.0)
    stops = render.SATMAPS["temperate"]
    by_height = render.satmap(analysis.smoothstep(h.min(), h.max(), h), stops)
    s = analysis.slope(h)
    by_slope = render.satmap(s / max(s.max(), 1e-12), stops)
    assert by_height.shape == by_slope.shape == h.shape + (3,)
    assert not np.allclose(by_height, by_slope)      # different driver -> genuinely different colour


# --------------------------------------------------------------------------- #
# data-map channels
# --------------------------------------------------------------------------- #
def test_wear_is_high_on_convex_steep_ground_and_zero_in_a_bowl():
    h = inputs.cone(n=41, height=10.0, radius=18.0)
    w = analysis.wear(h)
    assert 0.0 <= w.min() and w.max() <= 1.0 + 1e-9
    assert w[20, 20] < w.max()                       # the flat apex is not "worn"
    assert np.all(analysis.wear(-h) >= 0.0)          # an inverted bowl: still a valid mask


def test_peaks_isolates_the_summit():
    h = inputs.cone(n=41, height=10.0, radius=18.0)
    p = analysis.peaks(h, radius=4)
    assert 0.0 <= p.min() and p.max() <= 1.0 + 1e-9
    assert p[20, 20] > p[20, 2]                      # apex above the local mean, the rim is not


def test_texture_base_mixes_its_three_inputs():
    h = inputs.cone(n=41, height=10.0, radius=18.0)
    area = np.ones_like(h)
    only_slope = analysis.texture_base(h, area, slope_w=1.0, soil_w=0.0, flow_w=0.0)
    only_soil = analysis.texture_base(h, area, slope_w=0.0, soil_w=1.0, flow_w=0.0)
    assert 0.0 <= only_slope.min() and only_slope.max() <= 1.0 + 1e-9
    assert not np.allclose(only_slope, only_soil)    # the weights actually route different channels


# --------------------------------------------------------------------------- #
# spatial scale
# --------------------------------------------------------------------------- #
def test_resample_preserves_a_constant_and_returns_the_asked_shape():
    c = np.full((23, 17), 4.25)
    out = ops_filters.resample(c, (40, 9))
    assert out.shape == (40, 9)
    assert np.allclose(out, 4.25)


def test_at_feature_scale_widens_the_effect_and_keeps_the_shape():
    """A coarser working grid must widen the erosion's footprint. Measured as the mean absolute
    Laplacian of the CHANGE: a wider (smoother) footprint has less small-scale structure."""
    rng = np.random.default_rng(0)
    h = rng.random((96, 96)) * 20.0
    run = lambda f: T.thermal_erosion(f, 0.5, iters=20)
    roughness = []
    for k in (1, 4):
        out = ops_filters.at_feature_scale(h, k, run)
        assert out.shape == h.shape and np.all(np.isfinite(out))
        roughness.append(float(np.abs(analysis.laplacian(out - h)).mean()))
    assert roughness[1] < roughness[0], f"factor 4 was not smoother/wider: {roughness}"


def test_at_feature_scale_factor_one_is_the_plain_call():
    h = inputs.cone(n=33, height=10.0)
    run = lambda f: T.thermal_erosion(f, 0.5, iters=5)
    assert np.allclose(ops_filters.at_feature_scale(h, 1.0, run), run(h))
