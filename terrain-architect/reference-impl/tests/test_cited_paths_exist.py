"""Every path-shaped citation in `references/` must resolve to a real file.

WHY THIS EXISTS, AND THE DEFECT THAT CAUSED IT. Fifteen citations across `12`, `27` and `28`
named `terrain-renderer/reference-impl/beach.py`, `…/beach_optics.py` and
`terrain-renderer/references/12a-water-derivations.md`. **None of those paths existed.** The
files are real and every measurement quoted off them reproduces — they live in the
**water-physics** skill, which is where the beach implementations went when water was split out.
The prose around them said things like "reproducible by running the file named above" and
"recomputed here rather than relayed", so the chapters were making their strongest evidentiary
claim while pointing at a directory a reader cannot open. That is this skill's own founding
defect — a citation that cannot be followed — committed against its own reference implementation.

WHY NOTHING CAUGHT IT. `test_skill_integrity.py::test_literal_skill_paths_resolve` already checks
literal paths, and checks them well, including the `::node` suffix. But its pattern is
`(?:references|reference-impl|evals)/…` **anchored at the opening backtick**, so it only ever sees
paths that begin inside this skill. Every one of the fifteen began with a *sibling skill's* name
and was therefore invisible to it — and so were the ~35 bare `tests/test_*.py` citations, which
are written relative to `reference-impl/` rather than to the skill root.

THE DIFFERENCE IN APPROACH, WHICH IS THE POINT. That guard recognises a path by its **prefix**;
this one recognises it by its **shape** (a slashed token whose last segment carries a file
extension, or that ends in `/`), and then decides which root it hangs off. A prefix whitelist can
only ever guard the roots someone remembered to list, and the roots nobody remembered are exactly
where the rot was. The two overlap on this skill's own paths, deliberately: a citation being
checked twice costs nothing, and the overlap is what lets either guard be rewritten without
opening a hole.

WHAT THIS DOES NOT CHECK. That the cited file still *says* what the sentence claims. A path can
resolve and the surrounding prose still be stale — `test_chapter_numbers.py` is the harness for
that, and it can only cover numbers a module in *this* repo re-derives. Where the citation names a
symbol (`file.py::name`) the symbol is checked too, which closes the narrower version of the same
lie: a path fixed to the right directory while the function it names has moved or gone.
"""
import re
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]          # …/terrain-architect/reference-impl
SKILL = REF.parent                                 # …/terrain-architect
SKILLS = SKILL.parent                              # …/skills  (the sibling-skill root)

# Sibling skills these chapters are allowed to cite into. A path starting with one of these
# resolves against SKILLS, not against this skill — and is SKIPPED, loudly, if that skill is not
# checked out beside us, because absence of a sibling is an environment fact and not chapter rot.
SIBLING_SKILLS = {
    "terrain-architect",              # this skill, cited absolutely
    "terrain-renderer",
    "water-physics",
    "physically-based-rendering",
}

# The extensions that make a slashed token a FILE citation rather than a fraction, a unit, an
# upstream `owner/repo@sha`, or a cross-skill chapter reference like `terrain-renderer/11`.
FILE_SUFFIXES = (".py", ".md", ".json", ".png", ".txt", ".csv")

CITATION = re.compile(r"`([^`\s]*/[^`\s]*)`")
TRAILING_PUNCT = ".,;:)"


def _looks_like_a_path(body):
    """Shape test. Deliberately conservative: a false negative silently drops coverage, a false
    positive turns maths into a red test and teaches people to edit the guard."""
    segments = [s for s in body.split("/") if s]
    if not segments:
        return False                                  # a bare `/` used as prose separator
    if body.endswith("/"):
        return "." not in segments[-1]                # a directory citation, e.g. `reference-impl/`
    return body.endswith(FILE_SUFFIXES)


def _root_for(body):
    """Which tree the citation hangs off, or None if it is not ours to resolve."""
    first = body.split("/")[0]
    if first in SIBLING_SKILLS:
        return SKILLS
    if first in ("references", "reference-impl", "evals"):
        return SKILL
    if first == "tests":
        return REF                                    # written relative to reference-impl/
    return None


def _citations():
    """(chapter, token, body, symbol) for every path-shaped citation in references/."""
    found = []
    for chapter in sorted((SKILL / "references").glob("*.md")):
        for token in CITATION.findall(chapter.read_text(encoding="utf-8")):
            body, _, symbol = token.partition("::")
            body = body.rstrip(TRAILING_PUNCT)
            symbol = symbol.rstrip(TRAILING_PUNCT)
            if _looks_like_a_path(body):
                found.append((chapter, token, body, symbol))
    return found


def test_the_scan_still_finds_the_citations():
    """A guard that matches nothing passes forever.

    The floor is deliberately well below the real count (125 at the time of writing) so ordinary
    editing does not trip it, but a regex change that quietly stops matching does.
    """
    found = _citations()
    assert len(found) >= 100, (
        "only %d path-shaped citations matched in references/; the recogniser has probably "
        "stopped matching a whole family. Do not lower this floor to make it pass."
        % len(found))
    roots = {_root_for(body) for _, _, body, _ in found}
    assert SKILLS in roots, (
        "no cross-skill citation matched. Those are the family this guard exists for — if they "
        "have genuinely all gone, delete this assertion deliberately rather than by accident.")


def test_every_cited_path_resolves():
    """The row that would have caught all fifteen on the day they broke."""
    unresolved, skipped = [], []
    for chapter, token, body, _ in _citations():
        root = _root_for(body)
        if root is None:
            unresolved.append("%s: `%s` starts at a root this guard cannot resolve — add it to "
                              "SIBLING_SKILLS or fix the citation" % (chapter.name, token))
            continue
        if root is SKILLS and not (SKILLS / body.split("/")[0]).is_dir():
            skipped.append("%s: `%s` (sibling skill %r is not checked out here)"
                           % (chapter.name, token, body.split("/")[0]))
            continue
        if "*" in body:                               # a glob citation, e.g. `tests/test_x*.py`
            if not list(root.glob(body)):
                unresolved.append("%s: `%s` matches no file under %s"
                                  % (chapter.name, token, root))
            continue
        if not (root / body).exists():
            unresolved.append("%s: `%s` does not exist (looked at %s)"
                              % (chapter.name, token, root / body))
    if skipped and not unresolved:
        pytest.skip("some citations were unverifiable:\n  " + "\n  ".join(skipped))
    assert not unresolved, (
        "these citations name a path that is not there:\n  " + "\n  ".join(unresolved))


def test_every_cited_symbol_is_defined_in_the_file_that_is_cited():
    """`file.py::name` is the most precise citation form available; it has to stay true.

    Fixing a moved file's DIRECTORY while the function it names has been renamed or merged away
    leaves a subtler version of the same defect — the path opens, the sentence is still false.
    """
    wrong, skipped = [], []
    for chapter, token, body, symbol in _citations():
        if not symbol or not body.endswith(".py"):
            continue
        root = _root_for(body)
        if root is None:
            continue                                  # the row above already reports it
        if root is SKILLS and not (SKILLS / body.split("/")[0]).is_dir():
            skipped.append("%s: `%s`" % (chapter.name, token))
            continue
        target = root / body
        if not target.exists():
            continue                                  # the row above already reports it
        if ("def %s(" % symbol) not in target.read_text(encoding="utf-8"):
            wrong.append("%s: `%s` — %s defines no %s()"
                         % (chapter.name, token, body, symbol))
    if skipped and not wrong:
        pytest.skip("some symbol citations were unverifiable:\n  " + "\n  ".join(skipped))
    assert not wrong, (
        "these citations name a symbol the file does not define:\n  " + "\n  ".join(wrong))
