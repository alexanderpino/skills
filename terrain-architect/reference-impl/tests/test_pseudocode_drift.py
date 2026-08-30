"""Anti-drift harness between the chapters' PSEUDOCODE and the shipped modules.

THE GAP THIS CLOSES. `test_atom_coverage.py` guards which atoms exist. Nothing guarded the
NUMBERS inside the chapters' pseudocode blocks, and the chapters are what a reader implements
from. `01`'s four fBm blocks carried `lacunarity=2.0` while `noise.py` ships `2.03` — the exact
value the prose one paragraph below warns against, and one that puts a grid of identically-zero
pinch points into the output (`test_noise_pinch.py`). Prose and code had drifted apart at the one
place where the drift is executable.

HOW IT WORKS, AND WHY IT IS A REGISTER RATHER THAN A SCAN. An automatic scan over every numeric
default in every chapter is mostly noise: generic parameter names (`radius`, `depth`, `angle`,
`height`) collide with ordinary prose, and a harness that cries wolf is one people delete. So the
pairs below are declared. Each entry says: this chapter's pseudocode quotes this parameter, and
this module's function is what ships it. Adding a row is cheap; the register is the point, because
it makes the correspondence explicit instead of hoping a regex finds it.

⚠️ WHAT A FAILURE HERE MEANS. Not necessarily that the code is wrong. It means the two artifacts
disagree, and *someone must decide which one moves* — exactly the judgement `ATOM-COVERAGE.md`
already forces for the atom set. Silently widening a tolerance is not available: these are exact
values on both sides.
"""
import importlib
import inspect
import re
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]
CHAPTERS = REF.parent / "references"

# (chapter file, pseudocode signature name, module, function, parameter)
# The signature name is how the CHAPTER writes it; the function is how the MODULE does.
PAIRS = [
    ("01-noise.md", "fbm", "noise", "fbm", "lacunarity"),
    ("01-noise.md", "fbm", "noise", "fbm", "gain"),
    ("01-noise.md", "ridgedMF", "noise", "ridged_mf", "lacunarity"),
    ("01-noise.md", "ridgedMF", "noise", "ridged_mf", "gain"),
    ("01-noise.md", "ridgedMF", "noise", "ridged_mf", "offset"),
    ("01-noise.md", "hybridMF", "noise", "hybrid_mf", "lacunarity"),
    ("01-noise.md", "hybridMF", "noise", "hybrid_mf", "H"),
    ("01-noise.md", "hybridMF", "noise", "hybrid_mf", "offset"),
]


def _chapter_default(chapter, signature, param):
    """The value a chapter's pseudocode signature gives a parameter, or None."""
    text = (CHAPTERS / chapter).read_text(encoding="utf-8")
    # the signature line inside a fenced block: `name(... param=VALUE ...)`
    for m in re.finditer(r"^%s\(([^)]*)\)" % re.escape(signature), text, re.M):
        for part in m.group(1).split(","):
            k, _, v = part.partition("=")
            if k.strip() == param and v.strip():
                try:
                    return float(v.strip())
                except ValueError:
                    return None
    return None


def _module_default(module, function, param):
    fn = getattr(importlib.import_module(module), function)
    default = inspect.signature(fn).parameters[param].default
    return None if default is inspect.Parameter.empty else float(default)


@pytest.mark.parametrize("chapter,signature,module,function,param", PAIRS)
def test_pseudocode_default_matches_the_module(chapter, signature, module,
                                               function, param):
    doc = _chapter_default(chapter, signature, param)
    code = _module_default(module, function, param)
    assert doc is not None, (
        "%s's `%s(...)` pseudocode no longer gives `%s` a default — either the block changed or "
        "this row is stale" % (chapter, signature, param))
    assert code is not None, "%s.%s has no default for %s" % (module, function, param)
    assert doc == code, (
        "%s pseudocode says %s=%s; %s.%s ships %s. One of the two must move — a reader "
        "implements from the chapter." % (chapter, param, doc, module, function, code))


def test_the_register_still_points_at_things_that_exist():
    """A row naming a function that has been renamed would silently stop guarding anything."""
    missing = []
    for _chapter, _sig, module, function, param in PAIRS:
        try:
            fn = getattr(importlib.import_module(module), function)
        except (ImportError, AttributeError):
            missing.append("%s.%s" % (module, function))
            continue
        if param not in inspect.signature(fn).parameters:
            missing.append("%s.%s(%s)" % (module, function, param))
    assert not missing, "the drift register points at things that do not exist: %s" % missing


def test_no_pseudocode_block_still_ships_plain_lacunarity_two():
    """The specific regression this file was written for, stated as itself.

    Guarding the registered signatures is not quite enough: a NEW pseudocode block could
    reintroduce `lacunarity=2.0` without anyone adding a row for it. This scans every fenced block
    in `01` for that one value, because that one value has a measured artefact behind it.
    """
    text = (CHAPTERS / "01-noise.md").read_text(encoding="utf-8")
    offenders = re.findall(r"^\w+\([^)]*lacunarity\s*=\s*2\.0(?![0-9])[^)]*\)", text, re.M)
    assert not offenders, (
        "these pseudocode signatures ship lacunarity exactly 2.0, which puts a grid of "
        "identically-zero pinch points in the output (see test_noise_pinch.py): %s" % offenders)
