import re
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


def test_skill_frontmatter_contract():
    lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    assert lines[1] == "name: terrain-architect"
    assert lines[2] == "description: >-"
    description_lines = lines[3:end]
    assert description_lines
    assert all(line.startswith("  ") for line in description_lines)
    description = " ".join(line.strip() for line in description_lines)
    assert 1 <= len(description) <= 1024


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


def test_literal_skill_paths_resolve():
    pattern = re.compile(r"`((?:references|reference-impl|evals)/[^`\s]+)`")
    for markdown in SKILL_ROOT.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for raw_path in pattern.findall(text):
            path = raw_path.rstrip(".,;:)")
            assert (SKILL_ROOT / path).exists(), f"{markdown}: missing {path}"


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
