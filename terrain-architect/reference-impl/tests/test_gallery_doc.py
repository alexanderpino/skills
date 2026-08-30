"""GALLERY.md's undrawn-modules table, checked against the modules it names.

WHAT THE TABLE CLAIMS AND WHY IT NEEDS A GUARD. `GALLERY.md` lists the twelve algorithm modules
with no panel in the contact sheet, and heads its second column **"2-D field it returns (verified
`ndim=2`)"**, over prose reading *"Every one was called and returns a finite 2-D array, so 'no
natural heightfield image' is not the reason for any of them."* That is a strong claim — it is the
whole argument that the missing panels are an omission rather than an impossibility — and the word
"verified" in a column head is a promise that something did the verifying.

⚠️ NOTHING DID, AND TWO OF THE TWELVE CELLS WERE WRONG. `hydrology.water_over_land` returns float
**RGB**, `ndim=3` by construction — a compositing stage, not a field. `empirical_dem.metrics`
returns a **tuple of three scalars** `(hi, theta, hack)`, not an array at all. Both sat in the
"2-D field it returns" column under the word "verified". The module-level claim survives — every
one of the twelve does return a finite 2-D field through some entry point — but two cells named
the wrong entry point, which is exactly the kind of error a column head asserting `ndim=2` invites
a reader to stop checking.

The table is now parsed rather than trusted: every module it lists must be importable, every
function it names in that column must be callable here, and what comes back must contain a finite
2-D array. `test_the_column_rejects_the_two_entries_that_were_wrong` is the control — it runs the
two removed callables through the same checker and asserts they fail it.
"""
import re
from pathlib import Path

import numpy as np
import pytest

REF = Path(__file__).resolve().parents[1]
GALLERY = REF / "GALLERY.md"

_SHAPE = (48, 48)
_CELLSIZE = 30.0


def _base():
    """One small synthetic heightfield, shared by every call below."""
    import noise
    yy, xx = np.mgrid[0:_SHAPE[0], 0:_SHAPE[1]].astype(float)
    return 100.0 * noise.fbm(xx / 12.0, yy / 12.0, 0, octaves=5, base=noise.perlin)


def _raw_dem_file(tmp_path):
    """A tiny on-disk heightfield, so `load_heightfield` needs no network and no fixture."""
    path = tmp_path / "tile.raw"
    data = np.linspace(0, 65535, _SHAPE[0] * _SHAPE[1]).astype("<u2")
    path.write_bytes(data.tobytes())
    return path


# How each function the table names is called. The table says these RETURN a 2-D field; this is
# what "called" means, stated once so the claim is reproducible rather than asserted.
def _calls(tmp_path):
    import aeolian
    import braided
    import empirical_dem
    import flow
    import glacier
    import heightfield_io
    import hex_grid
    import hydrology
    import meander
    import placement
    import shallow_water
    import snow
    import tectonics

    h = _base()
    dem = flow.priority_flood_fill(h)
    acc = flow.d8_accumulation(dem, _CELLSIZE)
    wind = (np.full(_SHAPE, 8.0), np.zeros(_SHAPE))
    return {
        ("braided", "braided_river"): lambda: braided.braided_river(h, 4, cellsize=_CELLSIZE),
        ("meander", "meander_belt"): lambda: meander.meander_belt(h, cellsize=_CELLSIZE,
                                                                 steps=20),
        ("snow", "snow_step"): lambda: snow.snow_step(h, np.full(_SHAPE, 2.0),
                                                      np.full(_SHAPE, -3.0),
                                                      np.full(_SHAPE, 0.5),
                                                      cellsize=_CELLSIZE),
        ("aeolian", "exner_step"): lambda: aeolian.exner_step(h, wind, cellsize=_CELLSIZE),
        ("aeolian", "yardang"): lambda: aeolian.yardang(h, wind, np.ones(_SHAPE),
                                                        iters=2, cellsize=_CELLSIZE),
        ("shallow_water", "simulate"): lambda: shallow_water.simulate(dem, _CELLSIZE, iters=40),
        ("tectonics", "fault_scarp"): lambda: tectonics.fault_scarp(h, cellsize=_CELLSIZE),
        ("tectonics", "fault_weakness"): lambda: tectonics.fault_weakness(_SHAPE,
                                                                          cellsize=_CELLSIZE),
        ("tectonics", "plate_uplift"): lambda: tectonics.plate_uplift(_SHAPE, cellsize=_CELLSIZE),
        ("glacier", "glacier_carve"): lambda: glacier.glacier_carve(
            h, np.full(_SHAPE, 40.0), 2, cellsize=_CELLSIZE),
        ("hydrology", "water_surface"): lambda: hydrology.water_surface(dem, _CELLSIZE, acc),
        ("hydrology", "water_depth"): lambda: hydrology.water_depth(dem, _CELLSIZE, acc),
        ("heightfield_io", "load_heightfield"): lambda: heightfield_io.load_heightfield(
            str(_raw_dem_file(tmp_path)), shape=_SHAPE),
        ("heightfield_io", "window"): lambda: heightfield_io.window(h, 4, 4, 16),
        ("hex_grid", "laplacian6"): lambda: hex_grid.laplacian6(h, _CELLSIZE),
        ("hex_grid", "hessian6"): lambda: hex_grid.hessian6(h, _CELLSIZE),
        ("hex_grid", "gradient6"): lambda: hex_grid.gradient6(h, _CELLSIZE),
        ("placement", "disc"): lambda: placement.disc(_SHAPE, _CELLSIZE, (24.0, 24.0), 300.0),
        ("placement", "rect"): lambda: placement.rect(_SHAPE, _CELLSIZE, (24.0, 24.0),
                                                      (200.0, 300.0)),
        ("placement", "capsule"): lambda: placement.capsule(_SHAPE, _CELLSIZE, (200.0, 200.0),
                                                            (900.0, 900.0), 150.0),
        ("placement", "path_mask"): lambda: placement.path_mask(
            _SHAPE, _CELLSIZE, [(100.0, 100.0), (900.0, 500.0), (1200.0, 1200.0)], 150.0),
        ("empirical_dem", "our_terrain"): lambda: empirical_dem.our_terrain(
            n=_SHAPE[0], cellsize=60.0, seed=0),
    }


def _fields(obj, depth=0):
    """Every 2-D float array reachable in a returned value, tuples and dicts unwrapped once."""
    if depth > 2:
        return []
    if isinstance(obj, dict):
        return [f for v in obj.values() for f in _fields(v, depth + 1)]
    if isinstance(obj, (tuple, list)):
        return [f for v in obj for f in _fields(v, depth + 1)]
    a = np.asarray(obj)
    return [a] if a.ndim == 2 and a.dtype.kind in "fiub" else []


def _table_rows():
    """`module -> [names in the '2-D field it returns' column]`, parsed from GALLERY.md.

    Only the second column is read. The fourth carries prose that legitimately names other
    modules and the two entries this column had to drop, and reading it would re-introduce them.
    """
    text = GALLERY.read_text(encoding="utf-8")
    head = "| Module | 2-D field it returns"
    assert head in text, (
        "GALLERY.md no longer carries the undrawn-modules table this file guards; if the table "
        "went away so should this guard, and a human has to say which")
    body = text[text.index(head):]
    body = body[:body.index("\n\n")]
    rows = {}
    for line in body.splitlines()[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        module = re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", cells[0])
        assert module, "table row names no module: %r" % line
        # Only what is left of the `→`. To its right the cell names the RETURN FIELDS
        # (`depth` / `discharge` / `speed`), which are outputs, not callables.
        entry = cells[1].split("→")[0]
        rows[module[0]] = re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", entry)
    return rows


def test_the_table_names_exactly_the_modules_this_file_calls(tmp_path):
    """The registry above and the table must not drift apart in either direction.

    Both directions matter. A name added to the table with no call here would be claimed and
    unverified; a call left here for a name the table dropped would make this file's coverage
    look wider than the claim it guards.
    """
    rows = _table_rows()
    assert len(rows) == 12, "the table lists %d modules, not the twelve it claims" % len(rows)
    named = {(mod, fn) for mod, fns in rows.items() for fn in fns}
    covered = set(_calls(tmp_path))
    assert named == covered, (
        "GALLERY.md's table and this file's call registry disagree — table only: %s; "
        "registry only: %s" % (sorted(named - covered), sorted(covered - named)))


@pytest.mark.parametrize("module,fn", sorted(
    (m, f) for m, fs in _table_rows().items() for f in fs))
def test_every_function_the_table_names_returns_a_finite_2d_field(module, fn, tmp_path):
    """The column head says `verified ndim=2`. This is the verification."""
    calls = _calls(tmp_path)
    assert (module, fn) in calls, (
        "GALLERY.md's table names %s.%s as a 2-D field it returns, but nothing here calls it — "
        "either add the call or stop claiming the column is verified" % (module, fn))
    fields = _fields(calls[(module, fn)]())
    assert fields, (
        "%s.%s is listed in the '2-D field it returns' column and returns no 2-D array at all"
        % (module, fn))
    for a in fields:
        assert np.isfinite(np.asarray(a, float)).all(), (
            "%s.%s returns a 2-D field with non-finite values" % (module, fn))


def test_the_column_rejects_the_two_entries_that_were_wrong(tmp_path):
    """⚠️ CONTROL. The two cells that were false must still fail the check that found them.

    `hydrology.water_over_land` returns float RGB (`ndim=3`); `empirical_dem.metrics` returns
    `(hi, theta, hack)`, three scalars. Both were listed in the `ndim=2` column. If either
    starts passing `_fields`, the checker has gone slack and the table's column head is again
    a promise nothing keeps.
    """
    import empirical_dem
    import hydrology

    rgb = hydrology.water_over_land(np.zeros(_SHAPE + (3,)), np.ones(_SHAPE))
    assert np.asarray(rgb).ndim == 3 and not _fields(rgb), (
        "water_over_land now passes the 2-D field check; it returns RGB and the control that "
        "caught it in the table has gone quiet")

    stats = empirical_dem.metrics(_base(), _CELLSIZE)
    assert isinstance(stats, tuple) and not _fields(stats), (
        "empirical_dem.metrics now passes the 2-D field check; it returns three scalars and "
        "the control that caught it in the table has gone quiet")


def test_the_two_wrong_entries_are_not_back_in_the_column():
    """Belt and braces: the names themselves must stay out of that column."""
    rows = _table_rows()
    assert "water_over_land" not in rows.get("hydrology", []), (
        "water_over_land is back in GALLERY.md's 'ndim=2' column; it returns RGB")
    assert "metrics" not in rows.get("empirical_dem", []), (
        "metrics is back in GALLERY.md's 'ndim=2' column; it returns three scalars")
