"""`render.material_rgb`: the DEFAULT colorizer, and the two ways it used to lie about itself.

TWO DEFECTS, BOTH IN THE SAME FIFTEEN LINES, BOTH INVISIBLE FROM THE OUTSIDE.

  1. THE DOCUMENTED DEFAULT PAIRING DID NOT RUN. `GROUNDING.md` names
     `analysis.derive_substances` + `render.material_rgb` as the **default** colorizer, and
     `tests/test_mask_partition.py` cites that line as authority for what `material_rgb` is.
     `derive_substances` emits SEVEN channels (`analysis.SUBSTANCE_NAMES`); `render` shipped ONE
     built-in palette, `_MATERIAL_PALETTE`, with FIVE rows; and `material_rgb` sliced it `pal[:k]`,
     which for `k = 7` silently yields 5 rows and hands numpy a mismatched contraction. The
     documented default died with `ValueError: shape-mismatch for sum` — an error naming neither
     the stack nor the palette nor the word "palette". Nothing in the suite ran that pairing, so
     nothing caught it: `gallery.py` and `graph_demo.py` both feed the FIVE-channel
     `derive_materials` stack instead.

     Fixed by shipping `_SUBSTANCE_PALETTE` (7 colours, keyed to `SUBSTANCE_NAMES`) and selecting
     by `masks.shape[0]` — the capability the docs already claimed — rather than by demoting the
     documentation to match the narrower code.

  2. `shade` AND `cellsize` WERE DEAD PARAMETERS. Neither was read anywhere in the body, and
     `material_rgb(..., shade=True)` was bit-identical to `shade=False`, while the docstring
     promised "With `shade`, modulate by hillshade for relief". It never happened, and it never
     could: `material_rgb` takes no height field, so relief is not computable at this signature.
     `render.hillshade`, `sun_sky_shade` and `photoreal` are where relief lives.

     ⚠️ AND THE DEAD PARAMETER WAS NOT HARMLESS, IT WAS LOAD-BEARING IN THE WRONG DIRECTION.
     `material_rgb` is the tree's only downstream detector of a mask-partition bug: over-subscribed
     masks push channels past 255 and clip (`tests/test_mask_partition.py`). Multiplying by a
     hillshade in [0, 1], as the docstring promised, would pull those channels back UNDER 255 and
     silence the detector — and nothing would have failed, because the detector row pinned
     `shade=False`. A parameter that does nothing today would have quietly disabled the check the
     moment someone implemented it as written.

Both parameters are gone rather than implemented, so `material_rgb(masks, CELLSIZE)` is now a
TypeError rather than a silently-ignored argument — `palette` is keyword-only precisely so that a
stale positional `cellsize` cannot slide into it and repaint the terrain.
"""
import inspect

import numpy as np
import pytest

import analysis
import flow
import render


def _fixture(n=48, cellsize=25.0):
    """A small peak with real drainage — enough relief for a snowline and a channel network."""
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = (700.0 * np.exp(-(((xx - 24) ** 2 + (yy - 22) ** 2) / 420.0))
         + 24.0 * np.sin(xx / 4.0) * np.cos(yy / 5.0) + rng.normal(0.0, 6.0, (n, n)))
    area = flow.d8_accumulation(flow.priority_flood_fill(h), cellsize)
    return h, analysis.slope(h, cellsize), area, cellsize


def _stack(pairs):
    return np.stack([m for _, m in pairs])


def test_the_default_colorizer_pairing_runs():
    """⚠️ `GROUNDING.md`'s "(default)" — `derive_substances` + `material_rgb` — END TO END.

    This is the row whose absence let the default pairing ship broken. It calls the two functions
    the documentation pairs, with the argument the shipped call sites pass (none: no palette), and
    checks the result is a picture rather than an exception.

    It also checks the thing that makes the pairing meaningful: `derive_substances` returns a
    CLOSED stack (Σ = 1 exactly), so the weighted sum is a convex combination and the export lands
    inside the palette's hull with nothing clipped. A partition in, a well-formed image out.
    """
    h, slope_tan, area, cs = _fixture()
    stack = analysis.derive_substances(h, slope_tan, area, cs,
                                       climate={"has_water": True, "has_snow": True,
                                                "has_veg": True})
    assert [n for n, _ in stack] == list(analysis.SUBSTANCE_NAMES), (
        "derive_substances no longer emits SUBSTANCE_NAMES in order; material_rgb's built-in "
        "palette is keyed to that order and would now mis-colour every cell")
    masks = _stack(stack)
    assert masks.shape[0] == len(render._SUBSTANCE_PALETTE) == 7, (
        "the default pairing is %d masks into a %d-colour palette; those must match or the "
        "documented default raises" % (masks.shape[0], len(render._SUBSTANCE_PALETTE)))

    img = render.material_rgb(masks)                       # the shipped call: no palette
    assert img.shape == h.shape + (3,) and img.dtype == np.uint8

    pal = np.asarray(render._SUBSTANCE_PALETTE, dtype=float)
    total = masks.sum(axis=0)
    assert np.abs(total - 1.0).max() < 1e-9, (
        "derive_substances stopped closing to Σ = 1 (worst %.3e); the no-clipping claim below "
        "depends on the weighted sum being a convex combination"
        % float(np.abs(total - 1.0).max()))
    unclipped = np.tensordot(np.moveaxis(masks, 0, -1), pal, axes=([2], [0]))
    assert unclipped.max() <= pal.max() + 1e-9 and unclipped.min() >= pal.min() - 1e-9, (
        "a partitioned stack should land inside the palette's hull [%.1f, %.1f]; got [%.1f, %.1f]"
        % (pal.min(), pal.max(), unclipped.min(), unclipped.max()))
    assert (img < 255).any() and int((img == 255).all(axis=-1).sum()) == 0, (
        "the default pairing is clipping on a Σ = 1 stack, which means either the palette left "
        "8-bit range or material_rgb stopped being a weighted sum")

    # the substances are actually distinguishable: snow-heavy cells read pale, rock-heavy grey
    named = dict(stack)
    if named["snow"].max() > 0.5:
        snowy = named["snow"] > 0.5
        assert img[snowy].mean() > img[~snowy].mean(), (
            "snow cells are not brighter than the rest; the palette is no longer keyed to the "
            "substance names")


def test_material_rgb_picks_its_built_in_palette_by_channel_count():
    """FIVE channels -> `MATERIAL_NAMES` colours, SEVEN -> `SUBSTANCE_NAMES` colours.

    A bare `(K, H, W)` stack carries no names, so the channel count is the only thing there is to
    dispatch on — and the two shipped producers happen to differ in it. Checked with one-hot
    stacks, which must reproduce the palette rows exactly.
    """
    for palette, names in ((render._MATERIAL_PALETTE, analysis.MATERIAL_NAMES),
                           (render._SUBSTANCE_PALETTE, analysis.SUBSTANCE_NAMES)):
        k = len(palette)
        assert k == len(names), "%s has %d colours for %d names" % (names, k, len(names))
        for i, name in enumerate(names):
            masks = np.zeros((k, 2, 2))
            masks[i] = 1.0
            got = list(render.material_rgb(masks)[0, 0])
            assert got == list(palette[i]), (
                "a stack of %d channels that is all '%s' should ship %s; got %s"
                % (k, name, list(palette[i]), got))

        # ⚠️ AND THE COLOURS ARE KEYED TO THE NAMES, NOT MERELY TO THE SAME LIST. Comparing the
        # output against the palette by index passes even if the palette is permuted — snow
        # painted rock-grey and rock painted white would satisfy every assertion above it. These
        # are the semantic pins: snow is white because snow is white (`archetypes.py`).
        cols = {n: np.asarray(c, dtype=float) for n, c in zip(names, palette)}
        assert cols["snow"].min() > max(c.max() for n, c in cols.items() if n != "snow"), (
            "'snow' is no longer the brightest colour in %s; the palette looks permuted" % (names,))
        assert cols["water"][2] > cols["water"][:2].max() + 20, (
            "'water' is no longer blue-dominant in %s" % (names,))
        veg = "grass" if "grass" in cols else "vegetation"
        assert cols[veg][1] > cols[veg][0] and cols[veg][1] > cols[veg][2], (
            "'%s' is no longer green-dominant in %s" % (veg, names))
        assert abs(cols["rock"].max() - cols["rock"].min()) < 12, (
            "'rock' is no longer near-neutral grey in %s" % (names,))


def test_a_palette_length_mismatch_names_both_counts():
    """⚠️ THE ERROR MESSAGE IS THE FIX AS MUCH AS THE PALETTE IS.

    `pal[:k]` truncated silently, so a mismatch surfaced as numpy's `shape-mismatch for sum` —
    which names no array, no palette and no channel count, and sends the reader into `tensordot`'s
    documentation rather than to their own stack. Any mismatch now raises here, naming both
    numbers, whether the palette is passed or inferred.
    """
    six = np.zeros((6, 2, 2))
    with pytest.raises(ValueError) as e:
        render.material_rgb(six)                           # no built-in has 6 rows
    msg = str(e.value)
    assert "6" in msg and "5" in msg and "7" in msg, (
        "the no-built-in-palette error must name the stack's channel count and the counts that "
        "do exist; got %r" % msg)

    with pytest.raises(ValueError) as e:
        render.material_rgb(np.zeros((7, 2, 2)), palette=render._MATERIAL_PALETTE)
    msg = str(e.value)
    assert "7" in msg and "5" in msg and "palette" in msg, (
        "an explicit short palette must be reported as a length mismatch naming both counts; "
        "got %r" % msg)

    # the same discipline for a categorical index map, which used to CLIP the index and
    # mis-colour those cells with the last palette entry instead of failing
    idx = np.array([[0, 6], [2, 3]], dtype=float)
    with pytest.raises(ValueError) as e:
        render.material_rgb(idx, palette=render._MATERIAL_PALETTE)
    assert "6" in str(e.value) and "5" in str(e.value), str(e.value)
    # ...and with no palette named, the index map picks the built-in that spans it
    assert list(render.material_rgb(idx)[0, 1]) == list(render._SUBSTANCE_PALETTE[6])
    assert list(render.material_rgb(np.array([[0.0, 4.0]]))[0, 1]) == list(render._MATERIAL_PALETTE[4])


def test_dominant_material_round_trips_through_the_colorizer():
    """The categorical path on the DEFAULT stack: 7 substances -> index map -> substance colours."""
    h, slope_tan, area, cs = _fixture()
    stack = analysis.derive_substances(h, slope_tan, area, cs,
                                       climate={"has_water": True, "has_snow": True,
                                                "has_veg": True})
    idx = analysis.dominant_material(stack)
    img = render.material_rgb(idx)
    pal = np.asarray(render._SUBSTANCE_PALETTE, dtype=np.uint8)
    assert np.array_equal(img, pal[idx]), (
        "the index map no longer colours through the substance palette; a 7-substance index map "
        "used to be clipped to index 4 and mis-coloured silently")


def test_material_rgb_has_no_dead_parameters():
    """⚠️ `shade` AND `cellsize` ARE GONE, AND THIS ROW IS WHAT KEEPS THEM GONE.

    They were accepted, documented and never read: `shade=True` was bit-identical to
    `shade=False`, and `cellsize` was accepted by a function with no spatial term in it at all.
    A parameter that does nothing is worse than no parameter, because a caller reading the
    signature believes relief has been applied — and `photoreal`, the function that DOES apply
    relief, would then apply it twice.

    ⚠️ AND IF `shade` WERE EVER IMPLEMENTED AS DOCUMENTED IT WOULD BREAK THE PARTITION DETECTOR.
    Multiplying by a hillshade in [0, 1] pulls over-subscribed channels back under 255, and
    `tests/test_mask_partition.py`'s detector rows would go quiet with nothing to say so. If you
    want shaded materials, compose: `photoreal(material_rgb(masks), h, cellsize)`.
    """
    params = inspect.signature(render.material_rgb).parameters
    assert "shade" not in params and "cellsize" not in params, (
        "material_rgb grew back a dead parameter (%s). If it is implemented rather than dead, the "
        "clipping rows in tests/test_mask_partition.py need re-measuring FIRST — a hillshade "
        "multiply silences them." % list(params))
    assert params["palette"].kind is inspect.Parameter.KEYWORD_ONLY, (
        "palette must stay keyword-only: the call sites used to pass `cellsize` positionally in "
        "that slot, and a positional palette would let a stale call repaint the terrain with a "
        "float instead of raising")

    masks = np.zeros((5, 3, 3))
    masks[2] = 1.0
    with pytest.raises(TypeError):
        render.material_rgb(masks, 30.0)                   # the old positional cellsize
