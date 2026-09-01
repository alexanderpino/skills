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


def test_area_node_reaches_all_three_shipped_routers():
    """`03`'s recommended hybrid must be selectable from the shipped graph, not just from
    `flow.py`. All three routers are reachable through the `area` node's `method` param, all
    three are valid drainage fields, and the hybrid is genuinely the third one — a field of its
    own, not an alias that quietly re-ran D8 or MFD."""
    g, (_, a_out), ctx = _small(size=32)
    acc = {}
    for method in ("d8", "mfd", "hybrid"):
        g.nodes["area"].params["method"] = method
        acc[method] = g.evaluate(a_out)
        asserts.assert_finite(acc[method], f"area/{method}")
        assert acc[method].min() >= ctx.cellsize ** 2 - 1e-9   # every cell drains at least itself
    assert not np.allclose(acc["hybrid"], acc["d8"])
    assert not np.allclose(acc["hybrid"], acc["mfd"])


def test_hybrid_node_forwards_its_channelisation_threshold():
    """`channel_cells` is a real port on the node, not a swallowed param. It is checked by the
    two limits `test_flow_anatomy` proves exactly: at <= 1 cell every cell is channelised from
    the start, so the hybrid IS D8; above the domain's cell count nothing channelises, so it IS
    MFD. A node that dropped the param (always using flow.py's 60.0) fails both."""
    g, (_, a_out), ctx = _small(size=32)
    n_cells = float(ctx.resolution ** 2)
    g.nodes["area"].params["method"] = "d8"
    d8 = g.evaluate(a_out)
    g.nodes["area"].params["method"] = "mfd"
    mfd = g.evaluate(a_out)
    g.nodes["area"].params.update(method="hybrid", channel_cells=1.0)
    assert np.allclose(g.evaluate(a_out), d8, rtol=0, atol=0)
    g.nodes["area"].params["channel_cells"] = n_cells + 1.0
    assert np.allclose(g.evaluate(a_out), mfd, rtol=0, atol=0)


def test_unknown_accumulation_method_is_rejected():
    """A method the node does not understand must fail loudly. It used to fall through to D8,
    so `"mdf"` or `"MFD"` silently routed the whole graph with the wrong router and returned a
    plausible-looking drainage field — a quiet wrong answer, which is worse than a crash."""
    g, (_, a_out), _ = _small(size=32)
    for bad in ("mdf", "MFD", "d-8", ""):
        g.nodes["area"].params["method"] = bad
        try:
            g.evaluate(a_out)
        except ValueError as e:
            assert repr(bad) in str(e) and "hybrid" in str(e)   # the offender and the legal set
        else:
            raise AssertionError(f"unknown method {bad!r} was silently accepted")


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


# --------------------------------------------------------------------------------------
# CRITERION G2 — NOTHING THE CHAPTERS RECOMMEND IS UNREACHABLE FROM THE SHIPPED GRAPH
#
# The defect class, measured twice on this tree. `03` calls the MFD/D8 hybrid accumulation "what
# most good terrain tools do"; `flow.hybrid_accumulation` implemented it; and `graph_demo._area_fn`
# could not select it, so the recommendation was true of the library and false of the thing the
# demo actually runs. A capability that ships but cannot be chosen is documentation, not a
# capability — and the failure is silent in both directions, because the graph keeps returning a
# plausible field computed by the router the reader did not ask for.
#
# THE POPULATION, AND WHY IT IS THIS ONE. `references/*.md` was swept for recommendation language
# (`recommend*`, `prefer*`, `the right default`, `default choice`, `is the default`,
# `use ... by default`), which returns 38 lines. Twenty-nine are excluded in eleven counted
# buckets (below); nine are in scope. Those nine lines name EIGHT capabilities — `07:149` and
# `07:175` recommend the same one twice.
#
# ⚠️ AND THE SWEEP DOES NOT CONTAIN THE KNOWN INSTANCE. `03:247` recommends the hybrid router in
# the words "this costs almost nothing and is what most good terrain tools do" — no recommendation
# word anywhere in the sentence. So a purely mechanical census of this class UNDERCOUNTS, and the
# row is added by hand and labelled as such rather than left out to keep the denominator tidy.
# That is the one honest thing to do with a population whose extraction rule provably misses a
# member: report the rule, report the miss, and carry the member.
#
#   DENOMINATOR
#     recommendation-language lines in references/*.md ......... 38
#     excluded, in eleven counted buckets ...................... 29
#       physical_preferred_direction (7) — "preferred direction"/"prefers" as anisotropy physics,
#           not advice: 00:425, 03:1074, 09:397, 09:430, 12:1826, 26:72, 99:641
#       descriptive_not_advice (4) — "is the default" reporting what other implementations or the
#           chapter's own exposition do: 00:429, 03:1004, 14:340, 26:676
#       engineering_practice (4) — how to work, not which capability to run: 08:238, 09:541,
#           21:132, 24:309
#       gpu_or_device_scope (4) — GPU/device dispatch, outside a CPU reference graph: 12:94,
#           14:409, 15:81, 15:93
#       mesh_or_lattice_scope (3) — hex/mesh/raster topology, no stage in this graph: 00:428,
#           26:44, 26:623
#       constant_not_capability (2) — recommends a VALUE: 12:171, 99:573
#       units_convention (1) — 17:73
#       cross_skill_comparison (1) — what an upstream project recommends: 22:144
#       bibliography_restatement (1) — 99:251 restates 03:101
#       no_shipped_alternative (1) — 08:309 (flat rectangular heightfield; 24/25 ship no node)
#       crossref_to_another_section (1) — 05:363 points at the dune section's recommendation
#     in scope .................................................  9 lines
#     hand-added (recommendation with no recommendation word) ...  1 line   (03:247)
#     IDENTITY: 29 + 9 = 38 -> HOLDS.  10 lines -> 9 capabilities (07:149/07:175 are one).
#
# Eight of the nine are reachable and are proved so BEHAVIOURALLY below — by selecting them
# through the shipped graph and checking the field that comes back is the one the recommended
# callable produces, never by asserting a name appears in a source file. The ninth (Ulichney
# tiles) is not implemented at all and is pinned as a known gap under the staleness rule this
# repo already uses for divergences: implement it and the row FAILS, which is what forces it to
# be promoted rather than forgotten.
# --------------------------------------------------------------------------------------
import inspect                                           # noqa: E402
import re                                                # noqa: E402
from pathlib import Path                                 # noqa: E402

import pytest                                            # noqa: E402

import flow                                              # noqa: E402
import ops_filters                                       # noqa: E402
import scatter as scatter_mod                            # noqa: E402

_CHAPTERS = Path(__file__).resolve().parents[2] / "references"


def _chapter_line(chapter, lineno):
    return (_CHAPTERS / chapter).read_text(encoding="utf-8").split("\n")[lineno - 1]


# (id, chapter, line, the exact phrase that makes it a recommendation, what is recommended)
RECOMMENDED_CAPABILITIES = [
    ("epsilon-fill", "03-flow-routing.md", 81, "Use the epsilon variant by default",
     "flow.priority_flood_fill's epsilon gradient across filled flats"),
    ("hybrid-breach-fill", "03-flow-routing.md", 101, "Hybrid is the right default",
     "breach shallow pits, fill deep ones (flow.breach_fill)"),
    ("hybrid-accumulation", "03-flow-routing.md", 247, "what most good terrain tools do",
     "MFD on the hillslope, D8 once channelised (flow.hybrid_accumulation)"),
    ("area-as-discharge-proxy", "03-flow-routing.md", 744, "That's the right default",
     "route bare drainage area; discharge Q is the upgrade, not the default"),
    ("thermal-for-diffusion", "05-erosion-thermal-aeolian.md", 81, "Recommend this substitution",
     "thermal erosion stands in for stream power's D grad^2 h term — one node instead of two"),
    ("density-rejection-scatter", "07-scatter.md", 103, "Rejection against a density map (recommended)",
     "scatter.scatter_by_density: generate at minimum spacing, reject against the density map"),
    ("ulichney-ground-cover", "07-scatter.md", 149, "Recommendation for terrain:",
     "Ulichney void-and-cluster tiles for dense tileable ground cover"),
    ("bilateral-over-gaussian", "00-index.md", 710, "prefer bilateral / guided over Gaussian",
     "ops_filters.bilateral / guided_filter as the denoise family"),
    ("emergent-over-primitive", "11-geological.md", 240, "prefer the",
     "the emergent (erosion) recipe when the material field is what you care about, "
     "with the feature-primitive construction tree as the art-directable alternative"),
]

# The one in-scope recommendation with NOTHING behind it. Same staleness rule as
# `test_pseudocode_drift.KNOWN_DIVERGENCES`: both sides pinned, so implementing it fails this row.
KNOWN_UNREACHABLE = {
    "ulichney-ground-cover": (
        "Ulichney's void-and-cluster tiles are recommended TWICE in 07 (line 149 for ground cover, "
        "line 175 as the tiling answer, 'Preferred') and are implemented nowhere: `scatter.py` "
        "ships poisson_disk (Bridson), scatter_by_density, jittered_grid and rule_based, and 07's "
        "own text calls jittered_grid the fallback that is 'not true blue noise'. So the graph's "
        "ground-cover story is the option the chapter ranks SECOND. Recorded rather than "
        "implemented because a void-and-cluster tile generator is a new atom with its own oracle, "
        "not a wiring fix; logged in registers/OPEN-ITEMS.md."),
}


@pytest.mark.parametrize("rid,chapter,lineno,phrase,what", RECOMMENDED_CAPABILITIES,
                         ids=[r[0] for r in RECOMMENDED_CAPABILITIES])
def test_the_recommendation_is_still_in_the_chapter(rid, chapter, lineno, phrase, what):
    """Every row is anchored to the sentence that makes it a recommendation.

    Without this the table becomes a list of things someone once believed the chapters said, and a
    chapter edit that withdraws a recommendation leaves a guard enforcing it forever.
    """
    line = _chapter_line(chapter, lineno)
    assert phrase in line, (
        "%s: %s:%d no longer reads %r (it reads %r). If the chapter withdrew or moved the "
        "recommendation, this row must be re-adjudicated, not silently re-anchored."
        % (rid, chapter, lineno, phrase, line.strip()))


def test_every_recommended_capability_is_reachable_or_pinned_as_a_known_gap():
    """The census itself: nine capabilities, eight reachable, one pinned. No third state."""
    ids = [r[0] for r in RECOMMENDED_CAPABILITIES]
    assert len(ids) == len(set(ids)) == 9, ids
    assert set(KNOWN_UNREACHABLE) <= set(ids), (
        "a known-gap row names a capability that is not in the enumeration: %s"
        % (set(KNOWN_UNREACHABLE) - set(ids)))
    for _, reason in KNOWN_UNREACHABLE.items():
        assert len(reason) > 120, "a known gap needs a reason a human can act on, got %r" % reason


def test_epsilon_fill_and_the_hybrid_breach_fill_policy_are_both_selectable():
    """`03` recommends two different things about depressions and the graph must offer both.

    The epsilon gradient (03:81) is what makes flow directions defined across a filled flat; the
    breach/fill hybrid (03:101) is what stops "fill everything" from raising every basin to its rim
    and taking the lakes with it. Both are proved by SELECTING them on the shipped node and
    comparing against the library call, and the two exact limits are what make `max_depth` a real
    port rather than a swallowed parameter:  0 -> bitwise the pure fill;  inf -> the fill's raised
    cells are strictly fewer, which is the lakes-vs-canyons trade the chapter describes.
    """
    g, _, ctx = _small(size=32)
    relaxed = g.evaluate("relaxed")

    assert flow.priority_flood_fill.__defaults__[0] > 0.0, (
        "priority_flood_fill's eps default is no longer positive; 03:81's epsilon variant is the "
        "recommended one and a zero eps leaves flow directions undefined on filled flats")

    g.nodes["filled"].params["method"] = "fill"
    plain = g.evaluate("filled")
    assert np.array_equal(plain, flow.priority_flood_fill(relaxed)), (
        "the 'fill' method is no longer plain priority-flood")

    g.nodes["filled"].params.update(method="breach_fill", max_depth=0.0)
    assert np.array_equal(g.evaluate("filled"), plain), (
        "breach_fill at max_depth=0 must be BITWISE the pure fill — nothing is shallow enough to "
        "breach — or the threshold is not the thing deciding")

    g.nodes["filled"].params["max_depth"] = float("inf")
    breached = g.evaluate("filled")
    assert (breached <= plain + 1e-12).all(), "breaching raised ground somewhere; it only carves"
    raised_fill = int((plain > relaxed + 1e-9).sum())
    raised_breach = int((breached > relaxed + 1e-9).sum())
    assert raised_breach < raised_fill, (
        "breaching everything did not reduce the cells raised above the input (%d vs %d); 03's "
        "whole argument is that filling everything is what loses the lakes"
        % (raised_breach, raised_fill))
    assert asserts.no_interior_pit(breached), (
        "breach_fill must still leave a DEM every cell drains on — it replaces the fill, it does "
        "not run before one")


def test_an_unknown_depression_method_is_rejected():
    """Same law as the accumulation router: an unrecognised policy is a failure, not a default."""
    g, _, _ = _small(size=24)
    for bad in ("breach", "FILL", "hybrid", ""):
        g.nodes["filled"].params["method"] = bad
        try:
            g.evaluate("filled")
        except ValueError as e:
            assert repr(bad) in str(e) and "breach_fill" in str(e)
        else:
            raise AssertionError(f"unknown depression method {bad!r} was silently accepted")


def test_the_area_node_routes_area_and_the_scatter_node_rejects_against_density():
    """03:744 and 07:103 — the two rows whose recommendation IS the shipped default.

    Both are checked behaviourally: the area node reproduces `flow.d8_accumulation` on the filled
    DEM (bare area, not a discharge), and the scatter node reproduces `scatter.scatter_by_density`
    for the same seed — so neither can drift into some other routine while the row still passes.
    """
    g, (_, a_out), ctx = _small(size=32)
    assert g.nodes["area"].params["method"] == "d8"
    filled = g.evaluate("filled")
    assert np.array_equal(g.evaluate(a_out), flow.d8_accumulation(filled, cellsize=ctx.cellsize))

    pts = g.evaluate("scatter")
    slope_tan = g.evaluate("slope")
    dens = analysis_smoothstep_density(slope_tan)
    direct = scatter_mod.scatter_by_density(
        ctx.resolution * ctx.cellsize, ctx.resolution * ctx.cellsize,
        lambda pt: float(scatter_mod.sample_field(dens, [pt], ctx.cellsize)[0]),
        r_min=g.nodes["scatter"].params["r_min"], seed=ctx.root_seed)
    assert np.array_equal(pts, direct), (
        "the scatter node no longer routes through scatter.scatter_by_density — 07:103's "
        "recommended rejection-against-a-density-map")


def analysis_smoothstep_density(slope_tan):
    import analysis
    return analysis.smoothstep(np.tan(np.radians(18.0)), np.tan(np.radians(35.0)), slope_tan)


def test_thermal_stands_in_for_the_stream_power_diffusion_term():
    """05:81 — "one node instead of two". The graph must actually take the substitution.

    Two halves, and the second is the one that can rot silently: there is a thermal node after the
    fluvial one, AND the stream-power node's companion `D` term is off by default. Turn `D` on and
    the recommendation has quietly become "both nodes", which is what it advises against.
    """
    g, _, _ = _small(backbone="streampower", size=32)
    assert g.nodes["relaxed"].type_id.startswith("erosion.thermal")
    assert g.nodes["relaxed"].inputs == ("fluvial",)
    assert g.nodes["fluvial"].params.get("D", 0.0) == 0.0, (
        "the stream-power node now ships a nonzero hillslope diffusion D as well as the thermal "
        "node; 05 recommends thermal INSTEAD of that term, not alongside it")


def test_the_recommended_filters_are_shipped_and_node_wrappable():
    """00:710 — bilateral / guided over Gaussian. Shipped, and usable as graph nodes.

    Reachability here means the runtime can actually run them, so it is proved by building a node
    around each and evaluating it, not by checking the names exist in `ops_filters`.
    """
    for name in ("bilateral", "guided_filter", "gaussian"):
        assert callable(getattr(ops_filters, name, None)), f"ops_filters.{name} is gone"
    ctx = G.Ctx(cellsize=10.0, resolution=24, root_seed=1)
    g = G.Graph(ctx)
    g.add("base", "noise.perlin/1", G._noise_fn,
          params={"noise": "perlin", "wavelength": 120.0, "octaves": 4, "relief": 100.0})
    g.add("bilateral", "ops.bilateral/1",
          lambda p, ins, c: ops_filters.bilateral(ins[0], p["sigma_s"], p["sigma_r"]),
          inputs=("base",), params={"sigma_s": 1.5, "sigma_r": 8.0}, locality="NEIGHBOURHOOD")
    g.add("guided", "ops.guided/1",
          lambda p, ins, c: ops_filters.guided_filter(ins[0], r=2, eps=1e-2),
          inputs=("base",), params={}, locality="NEIGHBOURHOOD")
    base = g.evaluate("base")
    for name in ("bilateral", "guided"):
        out = g.evaluate(name)
        assert out.shape == base.shape and np.all(np.isfinite(out))
        assert not np.array_equal(out, base), f"the {name} node returned its input unchanged"


def test_both_generator_recipes_are_reachable_and_are_different_graphs():
    """11:240 — the emergent recipe and the feature-primitive construction tree, both shipped.

    The chapter recommends the emergent one *when the material field is what you care about* and
    keeps the primitive one for art direction, so the guard is that BOTH are buildable and that
    they are genuinely different pipelines rather than two names for one.
    """
    ctx = G.Ctx(cellsize=1000.0 / 32, resolution=32, root_seed=2)
    emergent, _ = G.build_graph(ctx)
    primitive, _ = G.build_scene_graph(ctx)
    assert "fluvial" in emergent.nodes and "fluvial" not in primitive.nodes
    assert "blocks" in primitive.nodes and "blocks" not in emergent.nodes
    assert primitive.nodes["blocks"].type_id.startswith("landform."), (
        "the mesa graph's primitive node is no longer a landform primitive")
    assert "materials" in emergent.nodes and "materials" in primitive.nodes


def test_ulichney_tiles_are_still_recommended_and_still_absent():
    """⚠️ THE ONE IN-SCOPE RECOMMENDATION WITH NOTHING BEHIND IT, PINNED ON BOTH SIDES.

    `07` recommends Ulichney void-and-cluster tiles twice — for ground cover (149) and as the
    tiling answer (175, "Preferred") — and nothing implements them. This row asserts BOTH halves,
    so it fails the moment either changes: implement the tiles and the row goes red, which is what
    makes the gap get promoted into a real reachability row instead of quietly closing.
    """
    text = (_CHAPTERS / "07-scatter.md").read_text(encoding="utf-8")
    assert "Ulichney tiles for ground cover" in text and "Ulichney tiles**" in text, (
        "07 no longer recommends Ulichney tiles; delete this row and re-adjudicate the census")
    surface = {n for n in vars(scatter_mod) if not n.startswith("_")}
    assert not [n for n in surface if re.search(r"ulichney|void.?and.?cluster", n, re.I)], (
        "Ulichney tiles now exist in scatter.py — delete this row and add a real reachability row "
        "to RECOMMENDED_CAPABILITIES: %s" % KNOWN_UNREACHABLE["ulichney-ground-cover"])


def test_an_unknown_noise_kind_is_rejected_before_it_can_mint_a_type_id():
    """⚠️ THE FALLTHROUGH CORRUPTED THE CACHE IDENTITY, NOT JUST THE FIELD.

    `_noise_fn` used to end in a bare `else: perlin`, and `build_graph` builds the base node's
    `type_id` as `f"noise.{kind}/1"` from the same unvalidated string. The CLI is fenced by
    `argparse choices`; `build_graph(noise_kind=...)` was not. So `noise_kind="simplex"` — a real
    function in `noise.py`, which is what makes it the argument someone would actually pass — wrote
    a content-addressed cache entry IDENTIFIED as `noise.simplex/1` holding Perlin. Under `14`'s
    Merkle keying that identity is hashed into every downstream node's key, so the graph does not
    merely return the wrong field: it certifies the wrong field as the right one, and every cone
    below inherits the certificate. `_area_fn` had the identical defect and now raises; so does this.

    Both gates are checked, because they fail at different moments: `build_graph` must refuse
    before the node exists, and `_noise_fn` must refuse even if a node is assembled by hand.
    """
    ctx = G.Ctx(cellsize=25.0, resolution=24, root_seed=1)
    for bad in ("simplex", "worley", "gabor", "Perlin", "perlin ", ""):
        with pytest.raises(ValueError) as e:
            G.build_graph(ctx, noise_kind=bad)
        assert repr(bad) in str(e.value) and "perlin" in str(e.value), str(e.value)

        g = G.Graph(ctx)
        g.add("base", "noise.perlin/1", G._noise_fn,
              params={"noise": bad, "wavelength": 200.0, "octaves": 3, "relief": 100.0})
        with pytest.raises(ValueError) as e:
            g.evaluate("base")
        assert repr(bad) in str(e.value)

    # ...and every legal kind really is dispatched to a DIFFERENT generator, so the legal set is
    # not five names for one field (which is what a fallthrough looks like from the outside).
    fields = {}
    for kind in G._NOISE_KINDS:
        g, (h_out, _) = G.build_graph(ctx, noise_kind=kind)
        fields[kind] = g.evaluate("base")
        assert g.nodes["base"].type_id == f"noise.{kind}/1"
    for a in G._NOISE_KINDS:
        for b in G._NOISE_KINDS:
            if a < b:
                assert not np.allclose(fields[a], fields[b]), (
                    f"noise kinds {a!r} and {b!r} return the same field; one of them is falling "
                    f"through to the other and the type_id is recording a lie")


def test_the_cli_noise_choices_come_from_the_dispatcher():
    """The argparse fence and the dispatcher must be one list, not two that agree today.

    They disagreeing is how `--noise simplex` would become reachable again: argparse is the only
    thing that stopped it before, and it was written out by hand beside the dispatcher.
    """
    src = inspect.getsource(G.main)
    assert "choices=_NOISE_KINDS" in src, (
        "the --noise choices are spelled out beside the dispatcher again instead of taken from "
        "it; that duplication is exactly what let the two lists differ")
