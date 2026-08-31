import re
import subprocess
import sys
from pathlib import Path


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


def test_all_reference_chapters_are_routed():
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    chapters = sorted((SKILL_ROOT / "references").glob("*.md"))
    assert chapters
    for chapter in chapters:
        assert f"references/{chapter.name}" in skill_text


# `test_literal_skill_paths_resolve` was RETIRED from this file; `tests/test_cited_paths_exist.py`
# is its successor. This is a deliberate deletion, and it was measured rather than assumed: every
# citation the old regex found — 119 of them, across 30 documents — is also found by the new
# recogniser, and none of them resolved only because the new guard added resolution roots, so no
# citation lost a check. The successor scans 44 documents and 411 citations, and
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
    assert "references/21-clean-room-implementation.md" in skill_text
    chapter_text = chapter.read_text(encoding="utf-8").lower()
    assert "reference-informed, engine-native" in chapter_text
    assert "source-independent" in chapter_text
