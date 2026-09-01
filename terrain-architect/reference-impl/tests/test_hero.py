"""Smoke/regression guard for the 3D hero renderer (hero.py). It is a *look*, not an oracle, so the
checks are structural: the camera maths is finite, and the render is a valid, non-blank RGB image that
contains both sky and terrain (the projection actually drew something). Runs tiny for speed.

The second half of the file guards something different: the COMPOSITION `hero.main()` actually
renders, which none of the structural checks touch. See the section comment there."""
import functools

import numpy as np

import archetypes as A
import asserts
import hero


def test_camera_matrices_are_finite():
    v = hero._look_at((10, 8, 10), (0, 0, 0), (0, 1, 0))
    p = hero._perspective(35.0, 1.6, 1.0, 100.0)
    assert v.shape == (4, 4) and p.shape == (4, 4)
    assert np.all(np.isfinite(v)) and np.all(np.isfinite(p))


def test_hero_renders_valid_nonblank_image():
    n, cell = 40, 2000.0 / 40
    h = A.alpine(n=n, cell=cell)
    col, _, surf = A.substance_color(h, "temperate", cell)
    img = hero.hero(surf, cell, col, size=(220, 150), ss=1, fog=0.2)
    assert img.shape == (150, 220, 3) and img.dtype == np.uint8
    assert np.all(np.isfinite(img.astype(np.float64)))
    # both sky (top row, untouched by terrain) and terrain (drawn) are present
    assert int(img.reshape(-1, 3).std(axis=0).sum()) > 10
    top_is_sky = img[0].mean() > 120                        # sky gradient fills the top band
    assert top_is_sky


def test_supersample_downscales_to_requested_size():
    n, cell = 32, 2000.0 / 32
    h = A.alpine(n=n, cell=cell)
    col, _, surf = A.substance_color(h, "temperate", cell)
    img = hero.hero(surf, cell, col, size=(180, 120), ss=2)
    assert img.shape == (120, 180, 3)                        # ss folds back to the requested size


# --------------------------------------------------------------------------------------------
# THE PATH THE FIGURE ACTUALLY RENDERS.
#
# The three checks above run `hero.hero()` on a hand-built `archetypes.alpine` tile. `hero.main()`
# runs something else entirely: `from_graph(seed=4)` -> stream-power erosion -> substances ->
# snowmelt -> `shallow_water.simulate(iters=1400)` -> `hydrology.water_surface` -> the render
# surface. Nothing asserted anything that path computed. `main()` even printed the shallow-water
# mass balance `rain_in == out + stored` and returned nothing, so the identity was stated on stdout
# and checked nowhere. `hero.scene()` now returns it (the `crater_anatomy.build()` /
# `flow_anatomy.measurements()` contract) and the guards below assert it.
#
# COST. The shipped figure is n=180 / iters=1400 (~14 s for the physics alone, plus a ~40 s
# rasterise). These guards build the SAME composition ONCE at n=72 / iters=400 (~2 s) and share it.
# The reduction is safe because every invariant asserted here is a conservation law, a sign or an
# ordering, none of which is a function of resolution:
#   * the budget closes to <= 2.9e-14 relative at every (n, iters, seed) measured below;
#   * `water_surface` returns `w >= bed` by construction at any n;
#   * meltwater is drawn from the snow mask at any n (measured: melt-weighted elevation is 0.943x
#     the snow-weighted one at BOTH n=72 and n=180 — the ratio does not move with resolution).
# What a smaller grid does change is relief and peak discharge, and no guard here pins either.
_SCENE_N, _SCENE_ITERS = 72, 400


@functools.lru_cache(maxsize=1)
def _scene():
    """The figure's composition, built once and shared by every guard in this section."""
    return hero.scene(n=_SCENE_N, iters=_SCENE_ITERS)


def test_the_figures_shallow_water_budget_closes():
    """THE CONSERVATION LAW THE FIGURE PRINTS AND NOBODY CHECKED: every drop of rain and snowmelt
    the figure delivers has either left the open boundary or is still standing on the terrain.

    This is the strongest invariant available on this path, and the right kind of one. Two CI runs
    with identical numpy/pillow/CPython produced different pixels because numpy 2.x dispatches SIMD
    kernels per-CPU and `iters=1400` of flux accumulation amplifies a last-bit difference (see
    `tools/regen_figures.py`). A conservation law is indifferent to that: reassociating the
    reductions moves the closure error, not the identity.

    WHAT THIS ADDS OVER `tests/test_shallow_water.py::test_open_domain_mass_balance`, which is the
    SOLVER's oracle. That one runs a 40x40 planar ramp with rain only. This runs the FIGURE's
    configuration: a stream-power-carved, priority-flood-filled bed, plus a per-cell `source_field`
    of snowmelt on top of the rain — the `sources`/`source_field` bookkeeping is a separate branch
    of `simulate`'s budget accounting, and a figure that fed melt in without crediting it to
    `rain_in` would balance nowhere yet still draw a plausible river.

    TOLERANCE, DERIVED. Measured relative closure |rain_in - (out + stored)| / rain_in over
    seeds 1-5 at (n=72, iters=400) and (n=72, iters=1400), plus the shipped (n=180, iters=1400):
    4.2e-15 .. 2.9e-14, worst 2.9e-14. That is float64 summation noise over `iters` steps of a
    four-term flux reduction and nothing else. 1e-9 sits ~4.5 decades above the worst measurement
    (headroom for a machine that associates the reductions differently) and ~5 decades below the
    smallest defect the identity can even express: the boundary term `out` is 12-29% of `rain_in`
    and the melt term is 10-13% of the input, so a dropped or mis-signed term moves this by O(0.1),
    not by O(1e-9). It is NOT the widest band that passes — it is two orders TIGHTER than the 1e-6
    `tests/test_shallow_water.py:34` already uses for the same budget.
    """
    _fields, facts = _scene()
    b = facts["budget"]
    asserts.assert_mass_conserved(b["rain_in"], b["out"] + b["stored"], tol=1e-9,
                                  msg="hero figure: rain+snowmelt delivered vs out+stored")
    # both sinks are live: a budget that closed with `out` at zero would mean the open boundary
    # stopped draining, and one with `stored` at zero would mean the terrain held no water at all.
    assert b["out"] > 0.0 and b["stored"] > 0.0


def test_the_figures_meltwater_comes_from_under_the_snow():
    """The figure's caption claims a percentage of its flow "from snowmelt", and `hero.py` says the
    water "runs from under the snow". Both are composition claims — `melt` is built from the `snow`
    layer of `analysis.derive_substances`, weighted so it is strongest at the snow's LOWER margin —
    and neither was asserted anywhere.

    All three checks are exact or ordinal, so none needs a tolerance:
      * the melt source is nonzero ONLY where the snow mask is (an equality on a mask);
      * both sources are live — 0 < melt fraction < 100 — so the caption is never quoting a figure
        that is really rain-only (or really melt-only);
      * meltwater is drawn from BELOW the snow's centre of mass: the melt-weighted mean elevation
        is lower than the snow-weighted one. Measured 0.943x at n=72 and 0.944x at n=180 — the
        ordering, and even its margin, is resolution-independent.
    If `melt` were ever re-wired to the wrong substance layer, or the elevation taper inverted so
    the melt came off the summits, the last two fire.
    """
    fields, facts = _scene()
    melt, snow, h = fields["melt"], fields["snow"], fields["height"]
    assert np.all(melt[snow <= 0.0] == 0.0), "meltwater is being sourced off the snow mask"
    assert melt.sum() > 0.0, "the snow layer produced no meltwater at all"
    assert 0.0 < facts["melt_fraction_pct"] < 100.0                   # rain AND melt both feed it
    melt_elev = float((melt * h).sum() / melt.sum())
    snow_elev = float((snow * h).sum() / snow.sum())
    assert melt_elev < snow_elev, (
        f"meltwater is not coming from under the snow: melt-weighted elevation {melt_elev:.0f} m "
        f"vs snow-weighted {snow_elev:.0f} m")


def test_the_figures_water_surface_never_sits_below_the_bed():
    """`depth = water_surface(h, Q) - h` is handed straight to the rasteriser as `water_depth`, and
    `hydrology.water_over_land` clips it (`np.clip(depth, 0, None)`) before compositing. So a
    water surface that sank below the bed would not raise, would not render oddly, and would not be
    visible in a pixel diff either — it would silently stop being water. Sign and ordering only:

      * depth >= 0 everywhere (the `w >= bed` contract `water_surface` states in its docstring);
      * the render surface is the UPPER ENVELOPE of the land surface and the water surface, which
        is what `np.maximum(surf, w)` means and what lets snow sit on peaks while water fills
        valleys;
      * the field is finite, so nothing NaN reaches the mesh.
    """
    fields, _facts = _scene()
    depth, surf, w = fields["water_depth"], fields["land_surface"], fields["water_surface"]
    asserts.assert_finite(depth, "hero water depth")
    asserts.assert_nonneg(depth, "hero water depth", tol=0.0)
    assert np.all(fields["render_surface"] >= surf)
    assert np.all(fields["render_surface"] >= w)
    assert np.all(fields["discharge"] >= 0.0) and fields["discharge"].max() > 0.0


def test_the_figure_composites_translucent_water_where_the_flow_put_it():
    """The figure's whole water claim is that the rivers are a SEPARATE TRANSLUCENT STAGE over the
    lit land, not a blue line painted on the bed — `hero(..., water_depth=...)` is the only thing
    that reaches `hydrology.water_over_land`, and no test ever passed it. Rendering the figure's
    own composition twice, with and without that argument, must differ, and `water_over_land`
    leaves dry cells byte-identical (`np.where(d > 1e-4, water, land)`), so the difference is
    evidence the flow actually wetted something.

    Tolerance-free: an inequality between two renders of the same mesh, plus a strictly-positive
    wet-cell count. Rendered small (240x160, ss=1, ~0.8 s each) because the claim is about which
    cells the water stage touched, not about how many pixels they cover.
    """
    fields, _facts = _scene()
    kw = dict(size=(240, 160), ss=1, ao=fields["ao"], z_exag=1.0)
    dry = hero.hero(fields["render_surface"], fields["cellsize"], fields["colour"], **kw)
    wet = hero.hero(fields["render_surface"], fields["cellsize"], fields["colour"],
                    water_depth=fields["water_depth"], **kw)
    assert dry.shape == wet.shape == (160, 240, 3)
    assert (fields["water_depth"] > 1e-4).any(), "the flow left no wet cell to composite"
    assert not np.array_equal(dry, wet), (
        "the translucent water stage changed no pixel — `water_depth` is not reaching "
        "`hydrology.water_over_land`")
