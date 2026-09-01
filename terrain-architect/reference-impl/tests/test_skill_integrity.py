import re
import subprocess
import sys
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[2]


def test_skill_frontmatter_contract():
    """`name` first, `description` as a folded scalar, and both within bounds.

    ⚠️ THIS USED TO FORBID EVERY OTHER KEY, AND ONLY BY ACCIDENT. It read
    `lines[3:end]` — everything from the description's first continuation line
    to the closing delimiter — as description text, and then required each line
    to be indented. That is a fine way to read a two-key file and an accidental
    prohibition on a third key, which is what it became when OKF v0.2 headers
    were added. The contract's real content is the two assertions in the
    docstring above; the description block now ends where the indentation ends,
    and anything after it is somebody else's business.
    """
    lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    assert lines[1] == "name: terrain-architect"
    assert lines[2] == "description: >-"
    description_lines = []
    for line in lines[3:end]:
        if not line.startswith("  "):
            break                      # the folded scalar ended; a new key began
        description_lines.append(line)
    assert description_lines, "the description block is empty"
    description = " ".join(line.strip() for line in description_lines)
    assert 1 <= len(description) <= 1024


def test_skill_frontmatter_keys_are_wellformed():
    """Every top-level key after the description parses as `key: value`.

    Replaces the guarantee the old parser gave by accident — that nothing
    unexpected sits in the block — without forbidding additional keys.
    """
    import re as _re
    lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
    end = lines.index("---", 1)
    seen_description = False
    for line in lines[1:end]:
        if line.startswith("  ") or not line.strip() or line.lstrip().startswith("#"):
            continue
        assert _re.match(r"^[A-Za-z_][\w-]*:", line), (
            "frontmatter line is not a key: %r" % line)
        if line.startswith("description:"):
            seen_description = True
    assert seen_description


def test_eval_integrity():
    subprocess.run(
        [sys.executable, str(SKILL_ROOT / "evals" / "validate.py")],
        check=True,
        capture_output=True,
        text=True,
    )


# --------------------------------------------------------------------------------------
# Anchored recognition of a chapter reference.
#
# ⚠️ THE ROUTING CHECK USED TO BE A BARE SUBSTRING: `f"references/{chapter.name}" in skill_text`.
# That is satisfied by any sentence that happens to contain the filename — including a sentence
# that says the chapter is NOT routed ("we dropped references/03-flow-routing.md from the table"),
# a line inside a fenced example, or the OKF `resource:` header. So the assertion "every chapter
# is routed" was really the assertion "every chapter filename appears somewhere in the file",
# which is a strictly weaker claim and not the one the docstring makes.
#
# Routing in this skill is a TABLE: Part 4 of SKILL.md is a `| chapter | what is in it |` grid,
# and every one of the 30 chapters is written there as a backticked code span. So the check is now
# two-part and both parts are structural rather than lexical:
#
#   1. the filename must appear as a DELIMITED citation — a whole token inside a backtick span, or
#      a markdown link/image target — not as loose prose; and
#   2. it must appear that way inside a markdown TABLE ROW, which is what "routed" means here.
#
# Measured before tightening: all 30 chapters already satisfy both, so this narrows what can
# satisfy the guard without narrowing what the corpus is required to contain. `test_routing_
# recogniser_rejects_bare_prose` pins the distinction against fixtures, so a future widening of
# the recogniser fails there rather than silently readmitting the substring.
# --------------------------------------------------------------------------------------

_BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")
_MD_LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")
# Prose punctuation a writer wraps around a citation, stripped from BOTH ends. `/` is deliberately
# absent, so `/references/00-index.md` — the skill-root-absolute form the OKF `resource:` header
# uses — stays a different token from the relative one and does not satisfy the routing row.
#
# ⚠️ KNOWN LIMIT, stated rather than papered over: `.` is in this set, so a leading `..` is eaten
# too. That is harmless for the one job this helper has (chapter filenames, which never begin with
# a dot) and it is why this recogniser is NOT reused for relative figure embeds — `tests/
# test_cited_paths_exist.py` owns those and strips front and back separately for exactly this
# reason. If this helper ever grows a second caller, take that split with it.
_EDGE_PUNCT = "*.,;:!?()[]{}<>\"'"


def _anchored_tokens(line):
    """Path tokens this line writes as a DELIMITED citation, not as running prose.

    A backtick span is tokenised on whitespace INSIDE the span, so `see references/01-noise.md`
    written as one span still yields the path; a markdown link target is taken whole.
    """
    tokens = set()
    for span in _BACKTICK_SPAN.findall(line):
        for token in span.split():
            tokens.add(token.strip(_EDGE_PUNCT))
    for target in _MD_LINK_TARGET.findall(line):
        tokens.add(target.strip(_EDGE_PUNCT))
    tokens.discard("")
    return tokens


def _routing_rows(skill_text):
    """The markdown table rows of SKILL.md — the only place a chapter counts as ROUTED."""
    return [ln for ln in skill_text.splitlines() if ln.lstrip().startswith("|")]


def _routed_chapter_tokens(skill_text):
    routed = set()
    for row in _routing_rows(skill_text):
        routed |= _anchored_tokens(row)
    return routed


def test_all_reference_chapters_are_routed():
    """Every chapter must be named as a delimited citation inside SKILL.md's routing table.

    See the block comment above for why this is not `filename in skill_text`.
    """
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    chapters = sorted((SKILL_ROOT / "references").glob("*.md"))
    assert chapters
    routed = _routed_chapter_tokens(skill_text)
    unrouted = [
        chapter.name for chapter in chapters
        if f"references/{chapter.name}" not in routed
    ]
    assert not unrouted, (
        "these chapters are not routed from SKILL.md's table as a backticked code span or a "
        "markdown link target (a bare mention in prose is not routing): %s" % unrouted)


def test_the_routing_table_is_where_the_routing_lives():
    """Non-vacuity: the table must exist and carry the chapters, or the row above proves nothing.

    A recogniser that matched nothing would make `unrouted` empty only if the corpus were empty;
    this pins the other side — the table is real, and it is what the row above is reading.
    """
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    chapter_count = len(sorted((SKILL_ROOT / "references").glob("*.md")))
    assert chapter_count == 30, (
        "the chapter corpus is %d, not the 30 this file's routing claim was measured against; "
        "re-measure before changing this number" % chapter_count)
    routed = _routed_chapter_tokens(skill_text)
    named = {t for t in routed if t.startswith("references/") and t.endswith(".md")}
    assert len(named) >= chapter_count, (
        "SKILL.md's tables name only %d chapter paths as delimited citations; the routing "
        "recogniser has stopped seeing the table" % len(named))


@pytest.mark.parametrize("line,expected", [
    # the routing table's own form
    ("| `references/03-flow-routing.md` | Depression fill, D8, MFD |",
     {"references/03-flow-routing.md"}),
    # a markdown link target is equally delimited
    ("| [flow routing](references/03-flow-routing.md) | routing |",
     {"references/03-flow-routing.md"}),
    # trailing prose punctuation around a span is not part of the path
    ("see `references/03-flow-routing.md`.", {"references/03-flow-routing.md"}),
    # ⚠️ the defeat the old substring check could not see: the filename in running prose
    ("we dropped references/03-flow-routing.md from the routing table", set()),
    ("| references/03-flow-routing.md | routing |", set()),
    ("    resource: /references/03-flow-routing.md", set()),
])
def test_routing_recogniser_rejects_bare_prose(line, expected):
    """Fixtures, not the corpus: this pins the RECOGNISER, so widening it fails here first."""
    assert _anchored_tokens(line) == expected


# `test_literal_skill_paths_resolve` was RETIRED from this file; `tests/test_cited_paths_exist.py`
# is its successor. This is a deliberate deletion, and it was measured rather than assumed: every
# citation the old regex found — 119 of them, across 30 documents — is also found by the new
# recogniser, and none of them resolved only because the new guard added resolution roots, so no
# citation lost a check. The successor scanned 44 documents and 411 citations when it was
# written, and 47 / 447 once `registers/*.md` and `DEFINITION-OF-DONE.md` were added to it; and
# `test_cited_paths_exist.py::test_no_unscanned_markdown_carries_citations` stands in for the old
# `rglob("*.md")` sweep so that no future document escapes the enumerated set.
#
# The retirement is not tidying. The old check had two holes the successor closes:
#
#   * `f"def {node}(" in target.read_text()` is a SUBSTRING test. A comment, a docstring or a
#     string literal holding the name satisfied it, so a function could be renamed away with the
#     citation left false and this test still green. The successor resolves symbols by AST.
#   * that same form rejected every symbol that is not a function, so a truthful citation of a
#     module-level constant (`heightfield_io.py::_CACHE`) RED-tested. A guard that fails on true
#     statements teaches people to edit the guard.
#
# If you are tempted to restore a path check here, extend the successor instead: two recognisers
# for one job is how the sibling-skill citations stayed invisible to both.


def test_crossvalidation_claim_matches_dependencies():
    dependency_text = (
        SKILL_ROOT / "reference-impl" / "requirements-crossvalidate.txt"
    ).read_text(encoding="utf-8").lower()
    dep_tokens = set(dependency_text.split())
    # richdem + pysheds are the baseline wired flow cross-checks.
    assert {"richdem", "pysheds"} <= dep_tokens
    documents = (
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "references" / "00-index.md",
        SKILL_ROOT / "reference-impl" / "README.md",
    )
    combined = "\n".join(
        document.read_text(encoding="utf-8").lower() for document in documents
    )
    assert "richdem and pysheds" in combined or "richdem/pysheds" in combined
    # No unbacked claims: any library the docs describe as cross-validated must actually
    # be wired as a cross-validation dependency. (Landlab joined richdem/pysheds once its
    # cross-checks in tests/test_crossvalidate_landlab.py were wired.)
    for lib in ("landlab", "richdem", "pysheds"):
        if re.search(rf"cross-validat(?:e|es|ed|ing|ion)[^\n]{{0,100}}{lib}", combined):
            assert lib in dep_tokens, (
                f"docs describe {lib} cross-validation but it is not in "
                "requirements-crossvalidate.txt"
            )


def test_clean_room_chapter_is_first_class():
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
    chapter = SKILL_ROOT / "references" / "21-clean-room-implementation.md"
    assert chapter.exists()
    assert "implement engine-native" in skill_text
    # Anchored for the same reason as the routing row above: a bare substring is satisfied by a
    # sentence saying the chapter was REMOVED, and "first-class" is a claim about routing.
    assert "references/21-clean-room-implementation.md" in _routed_chapter_tokens(
        (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")), (
        "references/21-clean-room-implementation.md is mentioned in SKILL.md but is not routed "
        "from its table as a delimited citation")
    chapter_text = chapter.read_text(encoding="utf-8").lower()
    assert "reference-informed, engine-native" in chapter_text
    assert "source-independent" in chapter_text
