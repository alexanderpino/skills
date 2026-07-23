"""The graph demo is a harness, not a new algorithm — but it still has to obey the same
invariants the algorithms do. These tests pin the two things that make it a *usable* dev
tool: the pipeline is wired in Legal Order and passes the `09` checks it advertises, and
the content-addressed cache (14) recomputes only what actually changed.
"""
import numpy as np
import asserts
import render
import graph_demo as G


def _small(backbone="droplet", size=40, seed=1):
    """A cheap graph for tests: same topology as the demo, tiny parameters."""
    ctx = G.Ctx(cellsize=1000.0 / size if backbone == "droplet" else 120000.0 / size,
                resolution=size, root_seed=seed)
    g, outs = G.build_graph(ctx, backbone)
    if backbone == "droplet":
        g.nodes["fluvial"].params["n_droplets"] = 1200
    else:
        g.nodes["fluvial"].params["iters"] = 25
    g.nodes["relaxed"].params["iters"] = 5
    return g, outs, ctx


# --------------------------------------------------------------------------- #
# the graph as a graph
# --------------------------------------------------------------------------- #
def test_runs_finite_and_right_shape():
    g, (h_out, a_out), ctx = _small()
    height = g.evaluate(h_out)
    area = g.evaluate(a_out)
    asserts.assert_finite(height, "height")
    asserts.assert_finite(area, "area")
    assert height.shape == area.shape == (ctx.resolution, ctx.resolution)


def test_deterministic():
    """Same file + same rootSeed = bit-identical output (14 determinism contract)."""
    def run():
        g, (h_out, _), _ = _small()
        return g.evaluate(h_out)
    asserts.assert_deterministic(run)


def test_legal_order_is_wired():
    """The two ordering laws 09 catches most: depression fill precedes flow routing, and
    analysis reads the FINAL height, never a pre-erosion one."""
    g, (h_out, a_out), _ = _small()
    assert g.nodes["area"].inputs == ("filled",)      # routing consumes the filled DEM
    assert g.nodes["filled"].inputs == ("relaxed",)   # ...which is the last height write
    assert g.nodes["relaxed"].inputs == ("fluvial",)  # thermal AFTER hydraulic
    # and the GLOBAL nodes are declared GLOBAL (they cannot be tiled — 08/14)
    assert g.nodes["filled"].locality == "GLOBAL"
    assert g.nodes["area"].locality == "GLOBAL"


def test_analysis_and_materials_downstream_of_final_height():
    """06 ordering rule: analysis (slope) and materials read the FINAL height, and the
    material stack partitions (sum ~ 1)."""
    g, _, ctx = _small()
    assert g.nodes["slope"].inputs == ("relaxed",)
    assert g.nodes["materials"].inputs == ("relaxed", "slope", "area")
    materials = g.evaluate("materials")
    n = ctx.resolution
    assert materials.shape == (5, n, n)                # water/snow/rock/sand/grass
    assert materials.min() >= -1e-9 and materials.max() <= 1.0 + 1e-9
    assert np.allclose(materials.sum(axis=0), 1.0, atol=1e-6)


def test_scene_graph_builds_an_archetype_as_a_dag():
    """The mesa scene is an archetype expressed as a DAG of grounded nodes (Create -> Modify ->
    Erode -> Texture) — the wiring is Legal Order and it evaluates finite, non-flat, with a real
    fault-block cliff (99th-pct slope well above repose: a mesa, not a relaxed hill)."""
    ctx = G.Ctx(cellsize=1000.0 / 48, resolution=48, root_seed=3)
    g, (h_out, a_out) = G.build_scene_graph(ctx)
    # Legal Order: primitive -> strata -> thermal -> fill -> area; analysis on final height
    assert g.nodes["blocks"].inputs == ("plain",)
    assert g.nodes["strata"].inputs == ("blocks",)
    assert g.nodes["relaxed"].inputs == ("strata",)
    assert g.nodes["filled"].inputs == ("relaxed",)
    assert g.nodes["materials"].inputs == ("relaxed", "slope", "area")
    height = g.evaluate(h_out)
    g.evaluate(a_out)
    assert np.all(np.isfinite(height))
    assert (height.max() - height.min()) > 150.0                     # a real butte stands above the plain
    p99_slope_deg = np.percentile(G.slope_degrees(height, ctx.cellsize), 99)
    assert p99_slope_deg > 45.0                                      # near-vertical caprock cliff, not a hill


def test_scatter_node_places_spaced_boulders():
    """07 step 12: the scatter node returns a PointSet; blue-noise spacing holds (>= r_min)."""
    g, _, ctx = _small(size=40)
    pts = g.evaluate("scatter")
    assert pts.ndim == 2 and pts.shape[1] == 2
    if len(pts) > 1:
        d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
        d[np.diag_indices(len(pts))] = np.inf
        assert d.min() >= g.nodes["scatter"].params["r_min"] - 1e-9


def test_cache_recomputes_only_downstream_cone():
    """Editing the thermal node re-runs it and its cone; the upstream base/fluvial are
    served from cache (14, content-addressed caching)."""
    g, (_, a_out), _ = _small()
    g.evaluate(a_out)
    g.evaluated.clear()
    g.cache_hits.clear()
    g.nodes["relaxed"].params["iters"] += 3           # a downstream edit
    g.evaluate(a_out)
    assert set(g.evaluated) == {"relaxed", "filled", "area"}
    assert "fluvial" in g.cache_hits                  # upstream cone reused
    assert "base" not in g.evaluated


def test_bad_node_is_caught_at_its_edge():
    """The runtime's validate() sweep raises where the NaN is produced, before it spreads
    (14: validation suite as a runtime option)."""
    g, (h_out, _), _ = _small()
    g.nodes["base"].fn = lambda p, ins, ctx: np.full((ctx.resolution, ctx.resolution), np.nan)
    try:
        g.evaluate(h_out)
    except ValueError as e:
        assert "base" in str(e)
    else:
        raise AssertionError("non-finite output was not caught")


# --------------------------------------------------------------------------- #
# the 09 checks the demo prints
# --------------------------------------------------------------------------- #
def test_flow_reaches_the_edge():
    """09 check 1: on a stream-power landscape (edges = base level) the trunk drainage
    exits at the domain boundary — rivers reach the edge, they don't stop mid-map."""
    g, (_, a_out), _ = _small(backbone="streampower", size=40)
    area = g.evaluate(a_out)
    fi, fj = np.unravel_index(int(np.argmax(area)), area.shape)
    n = area.shape[0]
    assert fi in (0, n - 1) or fj in (0, n - 1), (fi, fj)


def test_thermal_caps_slope_at_repose():
    """09 check 2: after thermal relaxation almost no slope exceeds the repose angle."""
    g, (h_out, _), ctx = _small(size=40)
    height = g.evaluate(h_out)
    slope = G.slope_degrees(height, ctx.cellsize)
    repose_deg = np.degrees(np.arctan(g.nodes["relaxed"].params["repose"]))
    assert np.percentile(slope, 99) <= repose_deg + 6.0


def test_fill_leaves_no_interior_pit():
    """The filled field routes everywhere (03) — the precondition flow accumulation needs."""
    g, _, _ = _small(size=40)
    filled = g.evaluate("filled")
    assert asserts.no_interior_pit(filled)


# --------------------------------------------------------------------------- #
# the render modes (09 visual review palette)
# --------------------------------------------------------------------------- #
import inputs                                            # noqa: E402


def test_render_modes_return_valid_rgb():
    h = inputs.cone(48, height=10.0)
    area = np.ones_like(h)
    for img in (render.greyscale(h),
                render.hillshade(h, 5.0),
                render.slope_shade(h, 5.0),
                render.flow_overlay(h, area, 5.0),
                render.hypsometric(h, 5.0),
                render.false_colour_clip(h)):
        assert img.shape == (48, 48, 3)
        assert img.dtype == np.uint8


def test_false_colour_flags_nonfinite():
    h = inputs.cone(48, height=10.0)
    h[0, 0] = np.nan
    h[1, 1] = np.inf
    img = render.false_colour_clip(h)
    assert tuple(img[0, 0]) == (255, 0, 255)             # NaN -> magenta
    assert tuple(img[1, 1]) == (255, 0, 255)             # Inf -> magenta


def test_png_writer_roundtrip(tmp_path):
    import struct
    img = render.hillshade(inputs.cone(48, height=10.0), 5.0)
    path = render.write_png(str(tmp_path / "h.png"), img)
    raw = open(path, "rb").read()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"               # PNG signature
    w, h = struct.unpack(">II", raw[16:24])              # IHDR width/height
    assert (w, h) == (48, 48)
