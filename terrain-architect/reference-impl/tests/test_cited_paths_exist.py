"""Every path-shaped citation in this skill's prose must resolve to a real file.

WHY THIS EXISTS, AND THE DEFECT THAT CAUSED IT. Fifteen citations across `12`, `27` and `28` named
`terrain-renderer/reference-impl/beach.py`, `…/beach_optics.py` and
`terrain-renderer/references/12a-water-derivations.md`. **None of those paths existed.** The files
are real and every measurement quoted off them reproduces — they live in the **water-physics**
skill, which is where the beach implementations went when water was split out. The prose around
them said things like "reproducible by running the file named above", so the chapters were making
their strongest evidentiary claim while pointing at a directory a reader cannot open.

WHY NOTHING CAUGHT IT. `test_skill_integrity.py`'s literal-path check recognises a path by its
**prefix** (`references|reference-impl|evals`, anchored at the opening backtick), so a citation
beginning with a *sibling skill's* name was invisible to it. This guard recognises a path by its
**shape** and then decides which root it hangs off, because the roots nobody remembered to list are
exactly where the rot was.

WHAT A LATER AUDIT FOUND IN *THIS* GUARD, and what each rule below is answering.

* **Symbols were checked by substring.** `("def %s(" % symbol) in target.read_text()` is satisfied
  by a comment. Renaming `dry_snow_attribution` to `_gone_dry_snow_attribution` and leaving the old
  name in a `#` comment kept this file green while `27`'s citation was already false. The same
  substring form also *red*-tested truthful citations of anything that is not a function — a
  module-level constant like `heightfield_io.py::_CACHE` has no `def`. A guard that rejects true
  statements teaches people to edit the guard. Both are fixed by asking the AST what a module
  actually defines (`_module_level_names`).

* **The recogniser required backticks AND no whitespace**, so it could not see 43 occurrences of
  `tools/okf_apply.py` (in the OKF frontmatter header of every generated document — not backticked
  at all), the `../reference-impl/*.png` figure embeds (markdown image syntax), `python
  evals/validate.py` (whitespace inside the span), or the whole `file.py:NN` family. It now reads
  three shapes: backtick spans tokenised on whitespace *inside* the span, markdown link/image
  targets, and bare tokens in running prose.

* **The cross-skill canary was satisfied by a self-reference.** `99-papers.md` contains
  `terrain-architect/reference-impl/`, so "some citation resolved against the skills directory" was
  true with zero real cross-skill citations. It now counts sibling roots with this skill's own name
  excluded.

* **Only `references/*.md` was scanned**, leaving `reference-impl/*.md`, `SKILL.md` and
  `evals/*.md` — and the ~46 bare `tests/…` citations they carry — covered by nothing.

WHAT THIS DOES NOT CHECK: that the cited file still *says* what the sentence claims. A path can
resolve and the prose around it still be stale; `test_chapter_numbers.py` is the harness for that.
The `::symbol` and `:NN` checks close the two narrower versions of the same lie.
"""
import ast
import re
from pathlib import Path

import pytest


REF = Path(__file__).resolve().parents[1]          # …/terrain-architect/reference-impl
SKILL = REF.parent                                 # …/terrain-architect
SKILLS = SKILL.parent                              # …/skills  (the sibling-skill root)

# The documents that carry citations. Enumerated rather than rglob'd, so a build cache
# (`reference-impl/.pytest_cache/README.md`) can never quietly join the corpus.
# `test_no_unscanned_markdown_carries_citations` proves nothing falls outside this set.
CITING_GLOBS = ("references/*.md", "reference-impl/*.md", "evals/*.md")
CITING_FILES = ("SKILL.md", "index.md")

# The extensions that make a slashed token a FILE citation rather than a fraction, a unit, an
# upstream `owner/repo@sha`, or a cross-skill chapter reference like `terrain-renderer/11`.
FILE_SUFFIXES = (".py", ".md", ".json", ".png", ".txt", ".csv", ".jpg", ".svg",
                 ".yaml", ".yml", ".r16", ".r32", ".raw")

# First path segments this guard knows how to resolve. Used only to admit DIRECTORY citations,
# where there is no extension to key on and prose is full of `and/or`, `w/` and `fBm/ridged/`.
KNOWN_ROOTS = {"references", "reference-impl", "evals", "tests", "agents", "eval-viewer",
               "results"}

# Real things outside this skill's tree, cited honestly by documents describing the wider
# harness. This repo cannot vouch for them, so it does not pretend to.
#
# `results/` is deliberately NOT here: `evals/README.md` cites `results/iteration-1.json`, which
# is a real file resolved against the citing document's own directory. Listing it would have
# excused a citation that is perfectly checkable.
EXTERNAL_ROOTS = ("agents/", "eval-viewer/")

# Sibling SKILLS this corpus cites into — named statically, because a skill that is not checked
# out has to be distinguishable from a typo, and a directory listing cannot tell you which of the
# two you are looking at. `tools/` is deliberately absent: it is shared tooling beside the skills,
# not a skill (it has no SKILL.md), and letting it count as a cross-skill citation would give the
# canary below 43 easy tokens to pass on while every real cross-skill citation rotted away.
SIBLING_SKILLS = ("water-physics", "terrain-renderer", "physically-based-rendering")

_BACKTICK = re.compile(r"`([^`\n]+)`")
_MD_TARGET = re.compile(r"\]\(([^)\s]+)\)")
_SCHEME = re.compile(r"^\w+://")
# `file.py:70`, `file.py:52-53`, `file.py:52–53` (en dash), `file.py:61,109–121`. The corpus
# uses all four, and an en dash is what a prose editor produces from a typed hyphen.
_LINE_PIN = re.compile(r":((?:\d+)(?:[,–—-]\d+)*)$")
_TRAILING_PUNCT = ".,;:)]}*\"'>"
# Stripped from the FRONT. Deliberately excludes `.` — a leading `..` is part of the path, and
# removing it rewrites `../reference-impl/x.png` into something that resolves somewhere else.
_LEADING_PUNCT = "([{<\"'"

# How a token was written. Only whole backtick spans and markdown targets may be directory
# citations; only slashed tokens may be bare prose; a symbol or line pin licenses a bare filename.
WHOLE_SPAN, IN_SPAN, LINK, BARE = "whole", "in-span", "link", "bare"


class Citation:
    """One path-shaped citation: where it was written, and what it claims."""

    __slots__ = ("source", "lineno", "raw", "path", "symbol", "pins", "is_dir")

    def __init__(self, source, lineno, raw, path, symbol, pins, is_dir):
        self.source = source        # the markdown file that wrote it
        self.lineno = lineno        # 1-based line within that file
        self.raw = raw              # the token exactly as written
        self.path = path            # the path part: punctuation, `::name` and `:NN` removed
        self.symbol = symbol        # the part after `::`, or None
        self.pins = pins            # every line number in a `:NN` / `:N,M–K` suffix, or None
        self.is_dir = is_dir        # the citation named a directory, not a file

    def __repr__(self):
        return "%s:%d: `%s`" % (self.source.name, self.lineno, self.raw)


# --------------------------------------------------------------------------------------
# Recogniser
# --------------------------------------------------------------------------------------

def _tokens(text):
    """Yield (lineno, token, kind) for every candidate citation token in a document.

    Three shapes, because the corpus writes citations in three shapes:
      1. backtick spans, tokenised on whitespace INSIDE the span -> `python evals/validate.py`
      2. markdown link and image targets                         -> ![fig](../reference-impl/x.png)
      3. bare tokens in running text                             -> the OKF header's
         `# --- okf v0.2, written by tools/okf_apply.py ---`, which has no backticks at all
    """
    for lineno, line in enumerate(text.splitlines(), start=1):
        for span in _BACKTICK.findall(line):
            parts = span.split()
            kind = WHOLE_SPAN if len(parts) == 1 else IN_SPAN
            for token in parts:
                yield lineno, token, kind
        for target in _MD_TARGET.findall(line):
            yield lineno, target, LINK
        # what is left once spans and link targets are removed, so nothing is counted twice
        for token in _MD_TARGET.sub(" ", _BACKTICK.sub(" ", line)).split():
            yield lineno, token, BARE


def _parse(token, kind):
    """Reduce a raw token to (path, symbol, pins, is_dir), or None if it is not a citation."""
    token = token.lstrip(_LEADING_PUNCT)
    if _SCHEME.match(token):
        return None                     # http://, https://, file:// — not ours to resolve

    token = token.rstrip(_TRAILING_PUNCT)
    if not token:
        return None

    path, separator, symbol = token.partition("::")
    symbol = symbol.rstrip(_TRAILING_PUNCT) if separator else None

    pins = None
    pin = _LINE_PIN.search(path)
    if pin:
        pins = [int(n) for n in re.findall(r"\d+", pin.group(1))]
        path = path[: pin.start()]
    if not path:
        return None

    if path.endswith("/"):
        # Directory citations have no extension to key on, and prose is full of slashed
        # non-paths (`w/`, `fBm/ridged/`, `and/or`). Admit them only where the author clearly
        # delimited one — a whole backtick span or a link target — and only under a known root.
        if kind not in (WHOLE_SPAN, LINK):
            return None
        segments = [s for s in path.strip("/").split("/") if s]
        if not segments or segments[0].lstrip(".") not in KNOWN_ROOTS:
            return None
        return path, symbol, pins, True

    if not path.endswith(FILE_SUFFIXES):
        return None
    if "/" not in path:
        # A bare filename is prose ("see flow.py") unless it carries a precise locator. `:NN`
        # and `::name` are exactly the forms that promise something checkable, and they are the
        # forms an audit found unchecked.
        if kind == BARE or (pins is None and symbol is None):
            return None
    return path, symbol, pins, False


def _citations(markdown):
    """Every citation one document makes, de-duplicated per (line, path, symbol, pins)."""
    found, seen = [], set()
    for lineno, token, kind in _tokens(markdown.read_text(encoding="utf-8")):
        parsed = _parse(token, kind)
        if parsed is None:
            continue
        path, symbol, pins, is_dir = parsed
        key = (lineno, path, symbol, tuple(pins or ()))
        if key in seen:
            continue
        seen.add(key)
        found.append(Citation(markdown, lineno, token, path, symbol, pins, is_dir))
    return found


def _citing_documents():
    documents = [SKILL / name for name in CITING_FILES]
    for pattern in CITING_GLOBS:
        documents.extend(sorted(SKILL.glob(pattern)))
    return [d for d in documents if d.is_file()]


def _all_citations():
    return [c for document in _citing_documents() for c in _citations(document)]


# --------------------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------------------

def _roots(citation):
    """The trees a citation may hang off, in the order a reader would try them.

    * the citing document's own directory — markdown's own rule, and what `..` means when the
      reader's viewer renders `![hex anatomy](../reference-impl/hex_anatomy.png)`
    * the skill root — the plain reading of `reference-impl/flow.py`
    * `reference-impl/` — bare `tests/test_flow.py` is written from inside that package
    * `reference-impl/tests/` — only for bare filenames carrying a `:NN` or `::name` locator,
      which is how the audit tables cite `test_crossvalidate.py:26`. Kept off the general path
      so a slashed citation cannot resolve by accident.
    * the skills directory — sibling skills and shared tooling (`water-physics/…`, `tools/…`)
    """
    if citation.path.startswith("/"):
        return (SKILL,)                 # OKF `resource:` paths are skill-root-absolute
    roots = [citation.source.parent, SKILL, REF]
    if "/" not in citation.path:
        roots.append(REF / "tests")
    roots.append(SKILLS)
    return tuple(dict.fromkeys(roots))          # de-duplicated, order preserved


def _is_checked_out(skill_name):
    """A sibling skill is usable only if it is actually here, with its own SKILL.md."""
    return (SKILLS / skill_name / "SKILL.md").is_file()


def _skip_reason(citation):
    """Why a recognised citation is not resolved. Each entry is a decision, not an oversight."""
    head = citation.path.lstrip("/").split("/")[0]
    if any(citation.path.startswith(root) for root in EXTERNAL_ROOTS):
        return "outside this skill's tree"
    if head in SIBLING_SKILLS and not _is_checked_out(head):
        # An absent sibling is an environment fact, not chapter rot.
        return "sibling skill %r is not checked out here" % head
    return None


def _resolve(citation):
    """The file or directory a citation names, or None."""
    relative = citation.path.lstrip("/")
    for root in _roots(citation):
        candidate = root / relative
        if candidate.is_dir() if citation.is_dir else candidate.is_file():
            return candidate
    return None


def _module_level_names(source, filename="<citation target>"):
    """Every name a module defines at module level, by AST.

    Functions, async functions, classes, and module-level bindings — including annotated and
    tuple-unpacked ones. A comment mentioning a name is not a definition, a docstring is not a
    definition, and a string literal containing "def foo(" is not a definition. That distinction
    is the entire reason this is an AST walk and not an `in` test.
    """
    names = set()
    for node in ast.parse(source, filename=filename).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names |= _bound_names(target)
        elif isinstance(node, ast.AnnAssign):
            names |= _bound_names(node.target)
    return names


def _bound_names(target):
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return set().union(*(_bound_names(e) for e in target.elts)) if target.elts else set()
    return set()


# --------------------------------------------------------------------------------------
# The guards
# --------------------------------------------------------------------------------------

def test_the_scan_still_finds_the_citations():
    """A guard that matches nothing passes forever.

    Floors are set well below the real counts (411 citations over 44 documents at the time of
    writing) so ordinary editing does not trip them, but a recogniser change that quietly stops
    matching a whole family does. Do not lower these to make the file pass.
    """
    documents = _citing_documents()
    assert len(documents) >= 40, "only %d citing documents found" % len(documents)
    found = _all_citations()
    assert len(found) >= 300, (
        "only %d path-shaped citations matched; the recogniser has probably stopped matching a "
        "whole family" % len(found))

    # Each family below was invisible to an earlier version of this recogniser.
    assert any(c.symbol for c in found), "no `file.py::symbol` citations matched"
    assert any(c.pins for c in found), "no `file.py:NN` citations matched"
    assert any(c.path.startswith("../") for c in found), "no relative citations matched"
    assert any(c.is_dir for c in found), "no directory citations matched"
    assert any(c.source.parent.name != "references" for c in found), (
        "only references/ matched; reference-impl/, SKILL.md and evals/ are unscanned again")


def test_cross_skill_citations_are_present_and_resolve():
    """Citations into a SIBLING skill are the family this guard was built for.

    The canary this replaces asked whether any citation resolved against the skills directory.
    `99-papers.md` writes `terrain-architect/reference-impl/` — this skill's own name — so that
    was true with zero real cross-skill citations, and deleting all sixteen `water-physics/…`
    citations left the guard green. Two things are excluded from the count for that reason: this
    skill's own name, and `tools/`, which is shared tooling rather than a skill and appears 43
    times in generated OKF headers. Either would let this row pass on tokens that prove nothing
    about the citations it exists to protect.
    """
    cross = [c for c in _all_citations()
             if c.path.lstrip("/").split("/")[0] in SIBLING_SKILLS]
    assert cross, (
        "no cross-skill citation matched. Those are the family this guard exists for — if they "
        "have genuinely all gone, delete this assertion deliberately rather than by accident.")

    unresolved, unverifiable = [], []
    for citation in cross:
        reason = _skip_reason(citation)
        if reason:
            unverifiable.append("%r — %s" % (citation, reason))
        elif _resolve(citation) is None:
            unresolved.append("%r — no such file under %s" % (citation, SKILLS))
    assert not unresolved, (
        "cross-skill citations that do not resolve:\n  " + "\n  ".join(unresolved))
    # Only a wholly absent set of siblings is an environment fact worth skipping for; a partial
    # one must still report on the siblings that ARE here.
    if len(unverifiable) == len(cross):
        pytest.skip("no cited sibling skill is checked out here:\n  " + "\n  ".join(unverifiable))


def test_every_cited_path_resolves():
    """The row that would have caught all fifteen on the day they broke.

    ⚠️ THIS MUST NOT SKIP ON PARTIAL UNVERIFIABILITY, and it used to. The previous version ended
    `if skipped and not unresolved: pytest.skip(...)`, so the two honest external citations in
    `reference-impl/README.md` turned the whole row — every one of the ~360 paths it had just
    verified — into a SKIPPED line. A reader scanning CI sees no failure; a citation deleted
    anywhere in the corpus is reported by a test that is not running. Out-of-scope citations are
    now simply not counted, and an unavailable sibling skill is reported without discarding the
    result for everything else.
    """
    unresolved, unverifiable, checked = [], [], 0
    for citation in _all_citations():
        reason = _skip_reason(citation)
        if reason == "outside this skill's tree":
            continue                    # deliberately out of scope; see EXTERNAL_ROOTS
        if reason:
            unverifiable.append("%r — %s" % (citation, reason))
            continue
        checked += 1
        if "*" in citation.path or "?" in citation.path:
            relative = citation.path.lstrip("/")
            if not any(list(root.glob(relative)) for root in _roots(citation)):
                unresolved.append("%r — matches no file" % citation)
            continue
        if _resolve(citation) is None:
            unresolved.append(
                "%r — not found under any of: %s"
                % (citation, ", ".join(str(r) for r in _roots(citation))))
    assert not unresolved, (
        "these citations name a path that is not there:\n  " + "\n  ".join(unresolved))
    assert checked >= 300, (
        "only %d citations were actually verified (%d unverifiable) — the guard has stopped "
        "checking rather than started passing:\n  %s"
        % (checked, len(unverifiable), "\n  ".join(unverifiable)))


def test_every_cited_symbol_is_defined_in_the_file_that_is_cited():
    """`file.py::name` is the most precise citation form available; it has to stay true.

    Checked against the module's AST. The substring form this replaces passed on a name that
    survived only in a comment, and failed on every truthful citation of a constant or a class.
    """
    wrong = []
    for citation in _all_citations():
        if not citation.symbol or not citation.path.endswith(".py"):
            continue
        if _skip_reason(citation):
            continue
        target = _resolve(citation)
        if target is None:
            continue                    # the path row above already reports it
        names = _module_level_names(target.read_text(encoding="utf-8"), str(target))
        if citation.symbol not in names:
            wrong.append("%r — %s defines no module-level `%s`"
                         % (citation, target.name, citation.symbol))
    assert not wrong, (
        "these citations name a symbol the file does not define:\n  " + "\n  ".join(wrong))


def test_every_cited_line_number_is_inside_the_file():
    """`file.py:70` must be a line the file has, and a range must run forwards.

    This cannot tell you a pin still points at the *right* line — `GALLERY.md` records one that
    drifted from 205 to 296 while staying in range. It does catch the pin left behind when the
    file it names is gutted, which is the version that turns a citation into a lie.
    """
    wrong = []
    for citation in _all_citations():
        if not citation.pins or _skip_reason(citation):
            continue
        target = _resolve(citation)
        if target is None or target.is_dir():
            continue
        total = len(target.read_text(encoding="utf-8").splitlines())
        if min(citation.pins) < 1 or max(citation.pins) > total:
            wrong.append("%r — %s has %d lines" % (citation, target.name, total))
        elif citation.pins != sorted(citation.pins):
            wrong.append("%r — line range runs backwards" % citation)
    assert not wrong, "line pins outside the file they cite:\n  " + "\n  ".join(wrong)


def test_pinned_snippets_appear_near_the_line_they_pin():
    """Where prose pins a line AND quotes the code there, the quote must be within ±3 lines.

    Narrow on purpose. It fires only when a backticked span sits on the same markdown line as a
    `file.py:NN` citation, holds no path separator, and is not itself a citation. Pins drift by a
    line or two under ordinary editing; ±3 forgives that and still catches a quote whose code has
    moved somewhere else entirely.
    """
    wrong = []
    for document in _citing_documents():
        lines = document.read_text(encoding="utf-8").splitlines()
        for citation in _citations(document):
            if not citation.pins or _skip_reason(citation):
                continue
            target = _resolve(citation)
            if target is None or target.is_dir() or target.suffix != ".py":
                continue
            snippets = _quoted_snippets(lines[citation.lineno - 1])
            if not snippets:
                continue
            body = target.read_text(encoding="utf-8").splitlines()
            low = max(0, min(citation.pins) - 4)
            high = min(len(body), max(citation.pins) + 3)
            window = "\n".join(body[low:high])
            for snippet in snippets:
                if snippet not in window:
                    wrong.append("%r — `%s` is not within ±3 lines of %s:%d"
                                 % (citation, snippet, target.name, min(citation.pins)))
    assert not wrong, "pinned snippets that have moved:\n  " + "\n  ".join(wrong)


def _quoted_snippets(markdown_line):
    """Backticked spans on a line that are a quotation of Python, not another citation.

    The bar is deliberately high, because the first draft of this check was WRONG and the corpus
    proved it: line pins sit in tables beside type signatures (`(bed, H, abrasion)`) and in prose
    beside typeset maths (`τ_y = max(τ_y0 + gain·(T_solidus − T), 1)`). Both look like code to a
    "has an `=` or a `(`" heuristic, neither is a quotation of a source line, and failing on them
    would be exactly the false positive that teaches people to edit the guard rather than the
    prose. So a span must additionally PARSE as Python before its absence means anything.
    """
    snippets = []
    for span in _BACKTICK.findall(markdown_line):
        body = span.rstrip(_TRAILING_PUNCT)
        if _LINE_PIN.search(body):
            continue                    # the pin itself
        if "/" in body or "::" in body:
            continue                    # another citation
        if body.endswith(FILE_SUFFIXES):
            continue                    # a bare filename
        if len(body) < 8 or ("=" not in body and "(" not in body):
            continue                    # prose in code voice, not a line of code
        try:
            ast.parse(body.strip())
        except (SyntaxError, ValueError):
            continue                    # a fragment or typeset maths, not quotable Python
        snippets.append(body)
    return snippets


def test_no_unscanned_markdown_carries_citations():
    """The scanned set is enumerated, so prove nothing carrying citations falls outside it.

    Without this, adding `reference-impl/tests/NOTES.md` would create a document whose citations
    no guard reads. Build caches are excluded by name, not by luck.
    """
    scanned = {d.resolve() for d in _citing_documents()}
    unscanned = []
    for markdown in SKILL.rglob("*.md"):
        if markdown.resolve() in scanned:
            continue
        if {".pytest_cache", "__pycache__", ".git", "out"} & set(markdown.parts):
            continue
        if _citations(markdown):
            unscanned.append(str(markdown.relative_to(SKILL)))
    assert not unscanned, (
        "markdown carrying citations that no guard scans; add its directory to CITING_GLOBS:\n  "
        + "\n  ".join(unscanned))


# --------------------------------------------------------------------------------------
# Unit tests for the recogniser, against fixture strings rather than the corpus.
#
# The corpus is the thing being measured; measuring the ruler against it proves nothing. Each
# case below is a hole a previous version of this file actually had.
# --------------------------------------------------------------------------------------

def _recognise(text):
    """Run the recogniser over a fixture string, returning the paths it admitted."""
    out, seen = [], set()
    for _lineno, token, kind in _tokens(text):
        parsed = _parse(token, kind)
        if parsed is None:
            continue
        path, symbol, pins, is_dir = parsed
        key = (path, symbol, tuple(pins or ()), is_dir)
        if key in seen:
            continue
        seen.add(key)
        out.append(parsed)
    return out


@pytest.mark.parametrize("text,expected", [
    # the form the old recogniser handled
    ("see `reference-impl/flow.py` for it", ["reference-impl/flow.py"]),
    # whitespace INSIDE the span used to hide the path
    ("Run `python evals/validate.py` and the suite.", ["evals/validate.py"]),
    ("`cd reference-impl && pytest tests/test_flow.py -q`", ["tests/test_flow.py"]),
    # markdown image and link targets were invisible
    ("![hex anatomy](../reference-impl/hex_anatomy.png)", ["../reference-impl/hex_anatomy.png"]),
    ("[the ladder](../reference-impl/VALIDATION.md)'s rung", ["../reference-impl/VALIDATION.md"]),
    # bare prose: the OKF header of every generated document
    ("# --- okf v0.2, written by tools/okf_apply.py ------", ["tools/okf_apply.py"]),
    ("    resource: /references/00-index.md", ["/references/00-index.md"]),
    # schemes belong to somebody else's namespace
    ("`https://github.com/r-barnes/richdem/blob/master/a.py`", []),
    ("see <https://docs.pytest.org/en/stable/x.py> for it", []),
    # trailing punctuation is prose; a leading `..` is part of the path
    ("`reference-impl/flow.py`.", ["reference-impl/flow.py"]),
    ("see `../reference-impl/gallery.png`,", ["../reference-impl/gallery.png"]),
    # a bare filename in prose is not a citation...
    ("`flow.py` does the routing", []),
    ("the dunes at 5,5 are `dunes.py` (Werner slab CA)", []),
    # ...but one carrying a precise locator is
    ("`capability_grid.py:445` draws it", ["capability_grid.py"]),
    ("`test_crossvalidate.py::test_priority_flood_matches_richdem`", ["test_crossvalidate.py"]),
    # directory citations: delimited and under a known root only
    ("`reference-impl/` is numpy-only", ["reference-impl/"]),
    ("a `w/` shorthand, `fBm/ridged/` blends, and `steepest-descent/` routing", []),
    ("the `(fBm/ridged/` fragment", []),
])
def test_recogniser_fixtures(text, expected):
    assert [path for path, _sym, _pins, _d in _recognise(text)] == expected


def test_recogniser_extracts_symbol_and_pins():
    (path, symbol, pins, is_dir), = _recognise("`reference-impl/snow.py::dry_snow_attribution`")
    assert (path, symbol, pins, is_dir) == ("reference-impl/snow.py", "dry_snow_attribution",
                                            None, False)

    # a pytest node ID is a path plus a symbol, not a path with a strange name
    (path, symbol, _p, _d), = _recognise("`tests/test_flow.py::test_d8_is_deterministic`")
    assert (path, symbol) == ("tests/test_flow.py", "test_d8_is_deterministic")

    # every line-pin dialect the corpus uses, en dash included
    assert _recognise("`sims_illustrative.py:70`")[0][2] == [70]
    assert _recognise("`sims_illustrative.py:52-53`")[0][2] == [52, 53]
    assert _recognise("`sims_illustrative.py:28–78`")[0][2] == [28, 78]
    assert _recognise("`crater.py:61,109–121`")[0][2] == [61, 109, 121]


def test_symbol_check_is_ast_not_substring():
    """The exact defeat: the old name survives in a comment, a docstring and a string literal."""
    source = (
        "# dry_snow_attribution moved; see the changelog\n"
        '"""Docstring mentioning def dry_snow_attribution( for good measure."""\n'
        'TEMPLATE = "def dry_snow_attribution("\n'
        "def _gone_dry_snow_attribution(h):\n"
        "    return h\n"
    )
    assert "def dry_snow_attribution(" in source      # the old substring check passed on this
    names = _module_level_names(source)
    assert "dry_snow_attribution" not in names        # the hole, closed
    assert "_gone_dry_snow_attribution" in names


def test_symbol_check_accepts_what_modules_really_define():
    """The old form's false positive: a module-level constant has no `def`, and is still real."""
    source = (
        "import os\n"
        "_CACHE = os.path.join('.', '.dem_cache')\n"
        "TILE: str = 'N36W113'\n"
        "A, B = 1, 2\n"
        "class Grid:\n"
        "    def method(self):\n"
        "        pass\n"
        "async def fetch():\n"
        "    pass\n"
        "def outer():\n"
        "    def nested():\n"
        "        pass\n"
    )
    names = _module_level_names(source)
    assert {"_CACHE", "TILE", "A", "B", "Grid", "fetch", "outer"} <= names
    assert "method" not in names                      # a method is not a module-level name
    assert "nested" not in names                      # nor is a closure


def test_quoted_snippet_detection_is_narrow():
    line = "uniform by construction (`sims_illustrative.py:70`), which reads `T -= cool * dt`"
    assert _quoted_snippets(line) == ["T -= cool * dt"]
    # other citations on the same line are not quoted code
    assert _quoted_snippets("`a/b.py:12` and `c/d.py`") == []
    assert _quoted_snippets("`a/b.py:12` and `flow.py`") == []
    # prose in code voice is not a quotable snippet
    assert _quoted_snippets("`a/b.py:12` is `illustrative-tier`") == []
