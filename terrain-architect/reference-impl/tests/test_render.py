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


# --------------------------------------------------------------------------------------
# CRITERION G1 — NO DEAD PUBLIC PARAMETER, AS A CENSUS RATHER THAN AS A STORY ABOUT ONE
#
# The two defects above were found by reading `material_rgb`. That does not scale and it does not
# generalise: the question "is every declared parameter actually read?" is decidable by static
# analysis over the whole module set, so it is answered that way here, once, for all 44 modules.
#
# WHY THIS CLASS IS WORSE THAN IT LOOKS, measured twice on this tree:
#   * `material_rgb(..., shade=True)` was BIT-IDENTICAL to `shade=False` while the docstring
#     promised "With `shade`, modulate by hillshade for relief" — and had it ever been implemented
#     as documented, multiplying by a hillshade in [0,1] would have silenced the over-subscription
#     detector in `tests/test_mask_partition.py` with nothing failing.
#   * A dead `cellsize` is not merely inert, it is EVIDENCE-SHAPED. `tests/test_scale_contract.py`
#     asked `"cellsize" in signature(fn).parameters` and credited that as scale-explicitness, so
#     four atoms satisfied the scale contract with a parameter no line of their body reads. That
#     guard now asks this census instead — see `test_scale_contract.test_every_atom_is_scale_explicit`.
#
# WHAT "READ" MEANS HERE. A parameter is read if its name appears in a LOAD context anywhere in the
# function's AST subtree — which covers nested functions, comprehensions, f-strings, decorators and
# default expressions, and deliberately does NOT count the docstring, a comment, or an assignment
# to the name. That is the whole point: `shade` was named in the docstring and nowhere else.
#
#   DENOMINATOR (recomputed on every run; the file count is pinned, the rest are floors)
#     modules scanned (reference-impl/*.py) ......... 44
#     public functions and public methods ........... 317
#     parameters checked (self/cls excluded) ........ 1331
#     dead: declared, never read .................... 0
#     exemptions ....................................  0  -- the table below is EMPTY
#   IDENTITY: dead == exempted, and every exemption names a live dead parameter -> asserted below.
#
# ⚠️ THE EXEMPTION TABLE IS EMPTY, AND THAT IS THE FINDING, NOT AN OMISSION. It used to carry four
# entries, all of them the same parameter — a dead `cellsize` on `aeolian.yardang`,
# `tectonics.fault_weakness`, `analysis.deposit_fill` and `hydrology.water_surface` — each exempted
# on the ground that a call site in a test file the code wave did not own blocked the deletion.
# `registers/OPEN-ITEMS.md` item 20 carried the removal patches. All four are now DELETED, together
# with every call site, and the census reports zero dead parameters in the tree.
#
# ⚠️ AND THE OPEN-ITEMS PATCH WAS INCOMPLETE, WHICH IS WHY THE DELETION IS GUARDED BELOW RATHER
# THAN JUST DONE. Item 20 named five call sites for `water_surface` and four for `deposit_fill`;
# `hero.py:191` (`hydrology.water_surface(h, cell, Q)`) appeared in neither list and is not a test
# file. Both removals drop the ARITY of a positional slot, so every stale call raises TypeError
# rather than sliding the next argument into the empty slot — the `material_rgb(masks, cellsize,
# palette)` hazard. `test_the_four_removed_cellsize_parameters_stay_removed` pins both halves.
# --------------------------------------------------------------------------------------
import ast                                                    # noqa: E402
from pathlib import Path                                      # noqa: E402

REF = Path(__file__).resolve().parents[1]                     # reference-impl/

MODULE_COUNT = 44                # pinned: a new module must be scanned, not silently skipped
MIN_FUNCTIONS = 300              # floors, not equalities — a signature edit must not turn this red
MIN_PARAMETERS = 1250

# The dynamic escape hatches. A body that calls any of these can read a parameter without ever
# naming it, so every parameter of such a function is treated as read — and the function is
# counted, because an unexplained exemption bucket is how a census stops being one.
_DYNAMIC = ("locals", "vars", "eval", "exec", "globals")

# (module, qualified function name, parameter) -> why it is still declared.
# ⚠️ EVERY REASON MUST NAME THE CALL SITE THAT BLOCKS THE DELETION. "It is harmless" is not a
# reason; the whole finding above is that this class is not harmless. The table is EMPTY and the
# intended steady state is that it stays empty: an entry here is a dead parameter shipping, not a
# dead parameter excused. It is kept, rather than deleted with its last row, because
# `test_no_public_function_declares_a_parameter_it_never_reads` needs somewhere for a genuinely
# blocked deletion to be recorded, and because a table that has to be re-invented is a table the
# next wave will re-invent without the staleness half.
DEAD_PARAMETER_EXEMPTIONS: dict = {}


def _public_functions(tree):
    """(qualname, node) for every public top-level function and public method of a public class."""
    def walk(node, qual):
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith("_"):
                    continue
                yield qual + child.name, child
            elif isinstance(child, ast.ClassDef) and not child.name.startswith("_"):
                yield from walk(child, child.name + ".")
    yield from walk(tree, "")


def _declared_parameters(fn):
    a = fn.args
    out = [(p.arg, "posonly") for p in a.posonlyargs]
    out += [(p.arg, "positional") for p in a.args]
    if a.vararg:
        out.append((a.vararg.arg, "vararg"))
    out += [(p.arg, "kwonly") for p in a.kwonlyargs]
    if a.kwarg:
        out.append((a.kwarg.arg, "kwarg"))
    return [(name, kind) for name, kind in out if name not in ("self", "cls")]


def parameter_census(source, module):
    """(functions, parameters, dead, dynamic) for one module's source.

    `dead` is [(module, qualname, param, kind)] for parameters never read. A body that reaches for
    `locals()`/`vars()`/`eval`/`exec`/`globals` can read a name it never mentions, so its
    parameters are all counted as read and the function is listed in `dynamic` instead of being
    quietly dropped.
    """
    tree = ast.parse(source)
    functions = parameters = 0
    dead, dynamic = [], []
    for qual, fn in _public_functions(tree):
        functions += 1
        loaded, is_dynamic = set(), False
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                loaded.add(node.id)
                if node.id in _DYNAMIC:
                    is_dynamic = True
        declared = _declared_parameters(fn)
        parameters += len(declared)
        if is_dynamic:
            dynamic.append((module, qual))
            continue
        for name, kind in declared:
            if name not in loaded:
                dead.append((module, qual, name, kind))
    return functions, parameters, dead, dynamic


def _whole_tree_census():
    modules = sorted(REF.glob("*.py"))
    functions = parameters = 0
    dead, dynamic = [], []
    for path in modules:
        f, p, d, dy = parameter_census(path.read_text(encoding="utf-8"), path.stem)
        functions += f
        parameters += p
        dead += d
        dynamic += dy
    return modules, functions, parameters, dead, dynamic


def test_no_public_function_declares_a_parameter_it_never_reads():
    """⚠️ THE CENSUS. Every dead parameter in `reference-impl/*.py` is exempted, with a reason."""
    modules, functions, parameters, dead, dynamic = _whole_tree_census()

    assert len(modules) == MODULE_COUNT, (
        "reference-impl now has %d modules, not the %d this census is pinned to. A module that "
        "joins the tree unscanned is exactly the gap this guard exists to close: update "
        "MODULE_COUNT and the denominator in this file's header together."
        % (len(modules), MODULE_COUNT))
    assert functions >= MIN_FUNCTIONS and parameters >= MIN_PARAMETERS, (
        "the census went thin (%d functions, %d parameters); a scan that stops finding things "
        "passes for the wrong reason" % (functions, parameters))

    unexplained = [(m, q, p, k) for m, q, p, k in dead
                   if (m, q, p) not in DEAD_PARAMETER_EXEMPTIONS]
    assert not unexplained, (
        "public parameters that are declared and never read:\n  "
        + "\n  ".join("%s.%s(%s)  [%s]" % r for r in unexplained)
        + "\nDelete the parameter (and grep the WHOLE repo for call sites first — a positional "
          "slot that disappears does not raise, it takes the next argument), or implement it, or "
          "add it to DEAD_PARAMETER_EXEMPTIONS with the call site that blocks the deletion.")

    assert dynamic == [], (
        "a public function now reaches for locals()/eval()/exec(), so this census cannot see what "
        "it reads: %s. Either drop the dynamic access or record it in the header's denominator."
        % dynamic)


def test_every_dead_parameter_exemption_is_still_a_live_dead_parameter():
    """⚠️ THE HALF THAT KEEPS THE ALLOWLIST FROM BECOMING THE ANSWER.

    An exemption table only ever grows unless something prunes it. Fix a parameter — implement it
    or delete it — and its exemption becomes a lie that would then cover a NEW dead parameter of
    the same name reintroduced later. So each entry must still name a parameter this census
    actually reports as dead, and must still carry a reason that names a blocker.

    ⚠️ WITH THE TABLE EMPTY THIS ROW IS VACUOUS, AND SAYING SO IS THE POINT. Both loops run over
    `DEAD_PARAMETER_EXEMPTIONS`, so no mutation to any MODULE can turn it red today — it is a
    tripwire armed only by a future entry, not a live measurement, and it is recorded as
    DECORATIVE in `registers/mutation-proofs.wave6-graph.tsv` rather than given an invented proof.
    The live measurement is `test_no_public_function_declares_a_parameter_it_never_reads` above:
    with the table empty, its `unexplained` list IS the whole dead list, so it fails on the first
    dead parameter anywhere in the tree. This row is kept so that the first entry someone adds
    back cannot be a permanent one.
    """
    _, _, _, dead, _ = _whole_tree_census()
    live = {(m, q, p) for m, q, p, _ in dead}
    stale = sorted(set(DEAD_PARAMETER_EXEMPTIONS) - live)
    assert not stale, (
        "these exemptions no longer describe anything — the parameter was fixed or removed. "
        "Delete the entry: %s" % (stale,))
    for key, reason in DEAD_PARAMETER_EXEMPTIONS.items():
        assert len(reason) > 200 and ("tests/" in reason or "OPEN-ITEMS" in reason), (
            "exemption %s must say which call site blocks the deletion; got %r" % (key, reason))


# (module, function, the callable) for the four parameters criterion G1 removed. The tuple is the
# worklist `registers/OPEN-ITEMS.md` item 20 wrote out, executed.
_REMOVED_CELLSIZE = [
    ("aeolian", "yardang"),
    ("tectonics", "fault_weakness"),
    ("analysis", "deposit_fill"),
    ("hydrology", "water_surface"),
    ("hydrology", "water_depth"),          # forwarded water_surface's, so it carried one too
]


@pytest.mark.parametrize("module,fname", _REMOVED_CELLSIZE,
                         ids=["%s.%s" % r for r in _REMOVED_CELLSIZE])
def test_the_four_removed_cellsize_parameters_stay_removed(module, fname):
    """⚠️ THE FOUR DEAD `cellsize` PARAMETERS ARE GONE, AND THIS ROW IS WHAT KEEPS THEM GONE.

    The census above would catch a dead parameter coming back, but only while it stays dead. This
    row is the narrower claim the removal actually made: these five signatures do not take a cell
    size AT ALL, because none of them has a horizontal length in it — index-space abrasion lanes
    (`yardang`), index-space fault feathering returning a dimensionless K (`fault_weakness`), a
    morphological closing over a radius in cells (`deposit_fill`), and elevation comparisons plus a
    metres-valued depth law (`water_surface`/`water_depth`).

    ⚠️ AND IT PINS THE HAZARD HALF, WHICH IS THE REASON THE REMOVAL WAS DEFERRED FOR A WHOLE WAVE.
    `deposit_fill` took `cellsize` in the SECOND POSITIONAL slot and `water_surface` in a REQUIRED
    one, so a bare deletion would not have raised — it would have handed `radius` a cell size and
    `discharge` a scalar, the `render.material_rgb(masks, cellsize, palette)` defect exactly, and
    the same shape that nearly took `n=121` into `halfar_anatomy.sia_at_cfl`'s `cellsize=12000.0`.
    Every stale positional call must therefore be a TypeError, which is what the second half
    checks. If someone re-adds the parameter for symmetry, both halves go red here before the
    census gets a chance to call it merely dead.
    """
    import importlib
    fn = getattr(importlib.import_module(module), fname)
    params = inspect.signature(fn).parameters
    assert "cellsize" not in params, (
        "%s.%s grew back the dead `cellsize` this wave deleted (%s). It is not scale-awareness: no "
        "line of the body has a horizontal length in it. registers/OPEN-ITEMS.md item 20."
        % (module, fname, list(params)))


def test_a_stale_positional_call_into_a_removed_cellsize_slot_raises():
    """The other half of the removal: the two positional slots must be a TypeError, not a slide."""
    import analysis
    import hydrology

    h = np.zeros((5, 5))
    with pytest.raises(TypeError):
        analysis.deposit_fill(h, 30.0)                     # the old positional cellsize -> radius
    with pytest.raises(TypeError):
        hydrology.water_surface(h, 30.0, h)                # the old (bed, cellsize, discharge)
    with pytest.raises(TypeError):
        hydrology.water_depth(h, 30.0, h)                  # ... and the wrapper that forwarded it

    # the surviving keyword-only parameters must still be reachable BY KEYWORD, or the guard above
    # would pass on a function that had simply been broken
    assert analysis.deposit_fill(h, radius=2).shape == (5, 5)
    assert hydrology.water_surface(h, h, smooth=0.0).shape == (5, 5)


# --------------------------------------------------------------------------------------
# The analyser's own oracles. A census guard whose analyser is untested is the failure mode
# `registers/guard-domains.tsv` was built to expose: a scan that cannot see what it claims to
# read. Each pair below is a mutation the census MUST catch and a decoy it must NOT fire on.
# --------------------------------------------------------------------------------------
_MUST_FLAG = [
    ("plain dead argument", "def f(a, b):\n    return a\n", "b"),
    ("documented but never implemented — the `shade` case",
     'def f(a, shade=False):\n    """With `shade`, modulate by hillshade for relief."""\n'
     "    return a\n", "shade"),
    ("named in a comment only", "def f(a, b):\n    # b would go here\n    return a\n", "b"),
    ("assigned, never read", "def f(a, b):\n    b = 1\n    return a\n", "b"),
    ("dead keyword-only", "def f(a, *, cellsize=1.0):\n    return a\n", "cellsize"),
    ("dead **kwargs", "def f(a, **kw):\n    return a\n", "kw"),
]

_MUST_NOT_FLAG = [
    ("read in a nested closure", "def f(a, b):\n    def g():\n        return b\n    return g() + a\n"),
    ("read in a comprehension", "def f(a, b):\n    return [b for _ in range(a)]\n"),
    ("read in an f-string", 'def f(a, b):\n    return f"{a}{b}"\n'),
    ("read in a lambda default", "def f(a, b):\n    return (lambda x=b: x)() + a\n"),
    ("**kwargs forwarded", "def f(a, **kw):\n    return g(a, **kw)\n"),
    ("read only in an except branch",
     "def f(a, b):\n    try:\n        return a\n    except ValueError:\n        return b\n"),
    ("private function is out of scope", "def _f(a, b):\n    return a\n"),
    ("dunder method is out of scope", "class C:\n    def __init__(self, a, b):\n        self.a = a\n"),
    ("self and cls are never counted", "class C:\n    def m(self):\n        return 1\n"),
]


@pytest.mark.parametrize("why,src,param", _MUST_FLAG, ids=[m[0] for m in _MUST_FLAG])
def test_the_census_catches_a_dead_parameter(why, src, param):
    _, _, dead, _ = parameter_census(src, "fixture")
    assert [d[2] for d in dead] == [param], "%s: expected %r flagged, got %s" % (why, param, dead)


@pytest.mark.parametrize("why,src", _MUST_NOT_FLAG, ids=[m[0] for m in _MUST_NOT_FLAG])
def test_the_census_does_not_fire_on_a_live_parameter(why, src):
    _, _, dead, _ = parameter_census(src, "fixture")
    assert dead == [], "%s: false positive %s" % (why, dead)


def test_a_dynamic_body_is_reported_rather_than_silently_passed():
    """`locals()` can read a parameter that is never named, so the census must say so out loud
    instead of scoring the function clean — a scanner that cannot see must not report zero."""
    f, p, dead, dynamic = parameter_census("def f(a, b):\n    return locals()\n", "fixture")
    assert dead == [] and dynamic == [("fixture", "f")] and (f, p) == (1, 2)
