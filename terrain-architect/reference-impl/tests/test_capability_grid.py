"""Build guard for `capability_grid.py` — the one-image claim that all 56 capabilities work.

WHY THIS FILE EXISTS. Until now `capability_grid.py` had no test of any kind: nothing in the tree
imported it, and its only check was `tools/regen_figures.py`'s PIXEL-EXACT diff of the committed
PNG. That gate has been shown unsound across machines — two CI runs with identical numpy 2.4.6 /
Pillow 12.3.0 / CPython 3.11.16 on ubuntu-latest produced different numbers (`canyon+strata`
pit-storage 5.22e+06 vs 4.16e+06 m3, Monument Valley relief 259 vs 268 m) and five figures drifted,
`capability_grid` among them. Whatever the pixel diff was implicitly covering has to be covered
explicitly now, and for this figure that is: **every tile is a live render of a working
capability**, which is the sentence the figure prints across its own header.

WHAT IT COSTS. The 56 thunks are 56 live simulations (~75 s). They are run ONCE at module scope and
shared by every test below; `build()` is then handed the finished tiles so the montage is not a
second pass. The cheap structural tests (`CELLS()` geometry, the loud-failure seams, the hero
substitution guard) do not touch that pass at all. A failure in the shared pass is captured, not
raised at import, so it surfaces as a named failing test with the real message rather than as a
collection error.
"""
import inspect
import os
import tempfile

import numpy as np
import pytest

pytest.importorskip("PIL", reason="the capability grid is laid out with Pillow")

import capability_grid as CG                                                # noqa: E402

# The published shape of this figure. These are the numbers GALLERY.md / README carry for it, and
# they are asserted against `CG.layout()` — the module's own arithmetic — not hard-coded twice.
N_CAPABILITIES = 56
GRID_COLS, GRID_ROWS = 7, 8
CANVAS_PX = (1448, 2082)

_OUT = os.path.join(tempfile.mkdtemp(prefix="capgrid-guard-"), "capability_grid.png")

# ---- the ONE expensive pass, shared by every test that needs real tiles --------------------
_FAILURE = None
_TILES: list = []
_IMG = None
_FACTS: dict = {}
try:
    _TILES = CG.render_tiles()                       # 56 live simulations, ~75 s, once
    _IMG, _FACTS = CG.build(path=_OUT, tiles=_TILES)  # montage only — no second simulation pass
except Exception as exc:                             # captured so it reports as a test, not a
    _FAILURE = exc                                   # collection error with no test name


def _require_grid():
    if _FAILURE is not None:
        raise AssertionError(
            "the capability grid did not build, so it can no longer claim that its 56 "
            "capabilities work and were generated live: %s: %s" % (type(_FAILURE).__name__, _FAILURE)
        ) from _FAILURE


def test_every_capability_tile_builds_live_with_no_err_swatch():
    """The figure's header says "every tile generated live in pure numpy". That is a claim about
    all 56, so all 56 must actually run — no exception swallowed, no ERR square standing in.

    `build` used to wrap each thunk in a bare `except Exception` and paste a dark-red "ERR" swatch
    where the render belonged, so a capability that had stopped working still produced a figure
    that looked rendered and still got committed. The swatch path now exists only behind the
    explicit `on_error="swatch"` opt-in, and this asserts the default path took none of it.
    """
    _require_grid()
    broken = [(t["title"], t["status"]) for t in _TILES if t["status"] != "ok"]
    assert broken == [], (
        "capability tile(s) did not build: %s. In the default path this cannot happen — "
        "render_tiles(on_error='raise') re-raises — so seeing it here means the ERR-swatch "
        "fallback came back and a broken capability is being shipped as a rendered figure."
        % broken)
    assert _FACTS["failed"] == [], "build()'s own facts report failed tiles: %s" % _FACTS["failed"]
    assert len(_TILES) == N_CAPABILITIES, (
        "the grid rendered %d tiles, not the %d capabilities it advertises" % (len(_TILES), N_CAPABILITIES))


def test_a_tile_that_cannot_build_is_a_failure_not_a_swatch():
    """The seam itself, driven with an injected failing capability — cheap, no simulations.

    Three separate things are pinned, because the defect can come back in three ways: the default
    must RAISE; the diagnostic grid must stay OPT-IN and must still REPORT the failure it drew;
    and an unrecognised mode must be rejected rather than silently treated as the lenient one
    (the `_noise_fn` `else: perlin` shape).
    """
    def boom():
        raise ZeroDivisionError("this capability is broken")

    cells = [("99 Injected", "a capability that stopped working", boom)]

    with pytest.raises(RuntimeError) as ei:
        CG.render_tiles(cells)
    msg = str(ei.value)
    assert "99 Injected" in msg and "ZeroDivisionError" in msg, (
        "the failure must name the tile and the underlying error, not just fail: %r" % msg)

    assert inspect.signature(CG.render_tiles).parameters["on_error"].default == "raise"
    assert inspect.signature(CG.build).parameters["on_error"].default == "raise", (
        "the ERR-swatch grid must be opt-in; a lenient default is the defect, not the guard")

    diag = CG.render_tiles(cells, on_error="swatch")
    assert diag[0]["rgb"] is None and diag[0]["status"].startswith("ZeroDivisionError"), (
        "the deliberate diagnostic grid must still record what failed: %r" % diag[0]["status"])
    _, facts = CG.build(path=None, on_error="swatch", tiles=diag)
    assert facts["failed"] == ["99 Injected"], (
        "a grid built with ERR swatches must say so in its facts, so no caller can mistake it "
        "for a clean build: %r" % facts["failed"])

    with pytest.raises(ValueError):
        CG.render_tiles(cells, on_error="ignore")


def test_a_tile_must_return_a_real_rgb_image():
    """The montage's contract. A thunk returning a float field or a 2-D array used to surface as
    an ERR swatch from `Image.fromarray` deep inside the paste loop; it is now a named refusal."""
    with pytest.raises(RuntimeError) as ei:
        CG.render_tiles([("99 Float", "returns a float field", lambda: np.zeros((8, 8, 3)))])
    assert "float" in str(ei.value).lower() and "99 Float" in str(ei.value)
    with pytest.raises(RuntimeError):
        CG.render_tiles([("99 Flat2D", "returns 2-D", lambda: np.zeros((8, 8), np.uint8))])


def test_grid_geometry_matches_the_modules_own_constants():
    """56 capabilities in a 7x8 grid on a 1448x2082 canvas — asserted through `CG.layout()` so the
    published numbers and the numbers `build` lays out with are the same arithmetic, and then
    against the canvas that was actually produced."""
    cells = CG.CELLS()
    assert len(cells) == N_CAPABILITIES
    for k, cell in enumerate(cells):
        assert len(cell) == 3, "cell %d is not a (title, test, thunk) triple: %r" % (k, cell)
        title, test, thunk = cell
        assert isinstance(title, str) and title.strip(), "cell %d has no title" % k
        assert isinstance(test, str) and test.strip(), (
            "cell %d (%s) has no oracle caption; the caption IS the figure's claim about what "
            "verifies that capability" % (k, title))
        assert callable(thunk), "cell %d (%s) is not generated live" % (k, title)
    titles = [c[0] for c in cells]
    assert len(set(titles)) == len(titles), (
        "duplicate tile title(s) %s — a copy-pasted cell renders one capability twice and drops "
        "another from the montage without changing the tile count"
        % sorted({t for t in titles if titles.count(t) > 1}))

    geom = CG.layout(N_CAPABILITIES)
    assert (geom["cols"], geom["rows"]) == (GRID_COLS, GRID_ROWS)
    assert geom["size"] == CANVAS_PX, (
        "the canvas geometry moved to %s; the committed figure and every document citing it are "
        "%dx%d" % (geom["size"], CANVAS_PX[0], CANVAS_PX[1]))
    assert geom["size"] == (GRID_COLS * (CG.TILE + CG.PAD) + CG.PAD,
                            CG.HEADER + GRID_ROWS * (CG.TILE + CG.CAP_H + CG.PAD) + CG.PAD)

    _require_grid()
    assert _IMG.size == CANVAS_PX, "the canvas built is %s, not %s" % (_IMG.size, CANVAS_PX)
    assert (_FACTS["cols"], _FACTS["rows"], _FACTS["n_cells"]) == (GRID_COLS, GRID_ROWS, N_CAPABILITIES)
    assert _FACTS["tile_px"] == CG.TILE


def test_every_tile_is_a_real_render_not_a_flat_square():
    """A tile that renders FLAT is a broken capability that still looks like a picture — and it is
    the shape a non-finite field takes, because `(nan * 255).astype(np.uint8)` is 0, so a NaN
    producer leaves as a uniformly black 200x200 square that reads as a legitimately dark render.

    Finiteness at this boundary is structural: `_check_tile` refuses anything but uint8, in which
    non-finite values are not representable — so what is asserted here is the observable
    consequence the guard can actually see, namely that the tile still VARIES. The floors are far
    below every shipped tile (worst observed: ptp 146, 2 distinct colours on the bilateral step
    edge, std 18.5) and far above a flat square (ptp 0, 1 colour, std 0).
    """
    _require_grid()
    for t in _TILES:
        rgb = t["rgb"]
        assert isinstance(rgb, np.ndarray) and rgb.dtype == np.uint8, (
            "%s: tile is %r, not a uint8 RGB image" % (t["title"], getattr(rgb, "dtype", type(rgb))))
        assert rgb.ndim == 3 and rgb.shape[2] == 3 and min(rgb.shape[:2]) >= 32, (
            "%s: tile shape %s is not a usable RGB render" % (t["title"], rgb.shape))
        assert t["ptp"] >= 24, (
            "%s renders essentially flat (ptp %d over the whole tile). A flat tile is a broken "
            "capability that still looks like a picture — this is what a NaN field, a zeroed "
            "colour ramp or a collapsed simulation all look like in the montage."
            % (t["title"], t["ptp"]))
        assert t["ncolours"] >= 2, "%s renders as a single colour" % t["title"]
        assert float(rgb.astype(np.float64).std()) >= 4.0, (
            "%s has almost no spatial variation (std %.2f); it is a wash, not a render"
            % (t["title"], float(rgb.astype(np.float64).std())))


def test_a_non_finite_field_is_a_failure_not_a_black_tile():
    """`_norm` is the colour-mapping funnel for `gray`/`ramp`. It used to pass NaN straight
    through to a uniformly black tile; it now refuses, so the montage names the broken capability
    instead of shipping a black square under its caption."""
    a = np.arange(16.0).reshape(4, 4)
    a[2, 2] = np.nan
    for fn in (CG._norm, CG.gray, CG.ramp):
        with pytest.raises(FloatingPointError):
            fn(a)
    ok = CG.gray(np.arange(16.0).reshape(4, 4))                # the finite case still works
    assert int(ok.max()) - int(ok.min()) > 200


def test_the_hero_tile_refuses_to_substitute_a_different_image(monkeypatch):
    """The 09 tile IMPORTS `hero.png` instead of generating a field, so it is the one tile whose
    input can go missing. It used to answer that with `except Exception: return gray(_terr)` — a
    grey hillshade of a mountain pasted under the caption "z-buffer, back-face cull, translucent
    water". That is a DIFFERENT picture presented as the capability, and it is how this figure
    drifted invisibly: `tools/regen_figures.py:88-97` records the tile "quietly drawing SOMETHING
    ELSE" in a bare scratch directory, visible only as an unfixable 200x200 pixel drift.
    """
    hero = [c for c in CG.CELLS() if c[0].startswith("09 Hero")]
    assert len(hero) == 1, "the hero tile is no longer in the grid"
    thunk = hero[0][2]

    monkeypatch.setattr(CG, "HERO_PNG", os.path.join(tempfile.mkdtemp(), "absent-hero.png"))
    with pytest.raises(RuntimeError) as ei:
        thunk()
    assert "hero" in str(ei.value).lower(), (
        "the missing input must be named: %r" % str(ei.value))

    _require_grid()
    tile = [t for t in _TILES if t["title"].startswith("09 Hero")][0]
    assert tile["shape"][:2] != (160, 160), (
        "the hero tile is 160x160 — the shape of the retired `gray(_terr)` stand-in, not of the "
        "imported hero render")


def test_tiles_are_deterministic_within_one_process():
    """Same process, same seeds, same tile — re-run against the module-scope pass, which came from
    a SEPARATE `CELLS()` call, so this also pins that a tile's result does not depend on which
    invocation of `CELLS()` built its closures.

    Only these seven are re-run (~2 s of the suite's ~8 min); each is stochastic-but-seeded and
    cheap. Re-running all 56 would double this file's cost for no extra defect class.
    """
    _require_grid()
    names = ["01 Curl noise", "13 Mass-consistent wind", "11 Karst sinkholes",
             "11 Fault-block butte", "04 Pipe erosion", "11 Mountain (basic)", "19 Lava CA"]
    by_title = {t: (ts, fn) for t, ts, fn in CG.CELLS()}
    first = {t["title"]: t["rgb"] for t in _TILES}
    for n in names:
        assert n in by_title and n in first, "%s is no longer a tile in the grid" % n
        again = np.ascontiguousarray(by_title[n][1]())
        assert again.shape == first[n].shape and np.array_equal(again, first[n]), (
            "%s is not reproducible within one process: a seeded capability that differs run to "
            "run cannot be checked by anything, and is how the committed figure drifted" % n)


def test_build_returns_the_canvas_and_its_per_tile_facts():
    """`build` returned None, so nothing downstream could assert anything at all — the pixel diff
    was the only check, and it is unsound across machines. It now returns `(canvas, facts)` the
    way `crater_anatomy.build` does, and the facts must actually describe the tiles that were
    drawn rather than being an independently-computed decoration."""
    _require_grid()
    assert _IMG is not None and os.path.getsize(_OUT) > 0, "the figure did not reach disk"
    for key in ("cols", "rows", "cell_w", "cell_h", "size", "n_cells", "tile_px",
                "path", "on_error", "failed", "tiles"):
        assert key in _FACTS, "build()'s facts lost the %r key" % key
    assert _FACTS["on_error"] == "raise" and _FACTS["path"] == _OUT
    assert len(_FACTS["tiles"]) == len(_TILES)
    for tf, t in zip(_FACTS["tiles"], _TILES):
        assert "rgb" not in tf, "facts must be scalars a guard can assert on, not the arrays"
        assert tf["title"] == t["title"] and tf["status"] == "ok"
        assert tuple(tf["shape"]) == tuple(t["rgb"].shape), (
            "%s: facts report shape %s but the tile is %s" % (tf["title"], tf["shape"], t["rgb"].shape))
        assert tf["ptp"] == int(t["rgb"].max()) - int(t["rgb"].min()), (
            "%s: facts report ptp %s, the drawn tile has %s"
            % (tf["title"], tf["ptp"], int(t["rgb"].max()) - int(t["rgb"].min())))
