"""Gaia's one guard. Run it before believing anything this skill says.

    python gaia/scripts/check.py            # report and exit non-zero on any problem
    python gaia/scripts/check.py --list     # what is checked, and what is NOT

WHAT THIS CAN AND CANNOT ESTABLISH -- read this before quoting a green run.

It checks the FORM of attribution: every claim points at a bibliography entry, every entry is
used, every entry carries a provenance tier, nothing is orphaned, no document cites something
graded unverifiable. It CANNOT check that a cited paper says what the document claims. That
one step is human, and `verified:` in a document's front matter is where a human records
having done it.

In this repo's vocabulary a green run here is an `attestation` channel, not an `independent`
one: the same kind of author writes the claim, the citation and this guard. Saying "grounded"
because this passes would be the exact overstatement Gaia exists to avoid.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from okf import Unparseable, documents, parse_front_matter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "references" / "papers.md"
INDEX = ROOT / "references" / "index.md"

MAX_LINES = 450          # per the plan: a document at the cap is two topics wanting a split
TIERS = {"P", "F", "L", "N", "?"}
STATUS = {"draft", "stable", "deprecated"}

# `- **id** `T` — Reference text.`  with an optional trailing ` [background]`
_ENTRY = re.compile(r"^- \*\*(?P<id>[a-z][a-z0-9_]*)\*\*\s+`(?P<tier>[PFLN?])`\s+—\s+(?P<ref>.+?)"
                    r"(?P<background>\s+\[background\])?\s*$")
# an inline citation marker in a body: [ocallaghan1984]  (not a markdown link, so not `](`)
_ID_OPENER = re.compile(r"^- \*\*[a-z][a-z0-9_]*\*\*")
_MARKER = re.compile(r"(?<!\])\[(?P<id>[a-z][a-z0-9_]*)\](?!\()")


def bibliography() -> tuple[dict[str, dict], list[str]]:
    """id -> {tier, ref, background}. Problems are returned, never printed and swallowed."""
    problems: list[str] = []
    if not PAPERS.exists():
        return {}, [f"{PAPERS.relative_to(ROOT)} does not exist"]
    entries: dict[str, dict] = {}
    _, body = parse_front_matter(PAPERS)
    in_fence = False
    for n, line in enumerate(body.splitlines(), 1):
        # Skip fenced blocks. This file documents its OWN entry format inside a fence, and
        # without this the guard reads that example as a malformed entry -- a guard tripping
        # over its own documentation. Detection matches the fence wherever it is indented,
        # because a fence under a list item is still a fence.
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # An entry opens with an id-shaped bold token. Prose bullets in this file open with
        # bold ENGLISH ("- **Never upgrade a tier..."), so keying on `- **` alone reported
        # three of them as malformed entries on the first run. The id shape is the
        # discriminator; anything else on a `- **` line is prose and is left alone.
        if not _ID_OPENER.match(line):
            continue
        m = _ENTRY.match(line.rstrip())
        if not m:
            problems.append(f"papers.md:{n}: entry does not match "
                            f"`- **id** `T` -- Reference.`  ->  {line.strip()[:60]}")
            continue
        if m["id"] in entries:
            problems.append(f"papers.md:{n}: duplicate id `{m['id']}`")
        entries[m["id"]] = {"tier": m["tier"], "ref": m["ref"].strip(),
                            "background": bool(m["background"])}
    return entries, problems


def check_documents(bib: dict[str, dict]) -> tuple[list[str], set[str]]:
    problems: list[str] = []
    used: set[str] = set()

    for path in documents(ROOT):
        rel = path.relative_to(ROOT)
        try:
            fm, body = parse_front_matter(path)
        except Unparseable as e:
            problems.append(str(e))
            continue

        # --- OKF conformance -------------------------------------------------------------
        if "type" not in fm:
            problems.append(f"{rel}: no `type` -- the one always-required OKF key")
        if fm.get("status", "stable") not in STATUS:
            problems.append(f"{rel}: status `{fm.get('status')}` is not one of {sorted(STATUS)}")
        if "okf_version" in fm and path != INDEX:
            problems.append(f"{rel}: `okf_version` belongs in the bundle root only")
        # `generated` is not `verified`. A document may not claim a human checked it unless a
        # human is named -- this is the only line between attribution and verification.
        ver = fm.get("verified")
        for entry in (ver if isinstance(ver, list) else [ver] if ver else []):
            if not isinstance(entry, dict) or not str(entry.get("by", "")).startswith("human:"):
                problems.append(f"{rel}: `verified:` without a `human:<id>` actor. Only a "
                                "person can verify a citation; a process can only generate.")
        if fm.get("status") == "stable" and not ver:
            problems.append(f"{rel}: status `stable` with no `verified:` entry -- stable claims "
                            "a human checked the citations. Use `draft` until one has.")

        # --- size ------------------------------------------------------------------------
        n = len(path.read_text(encoding="utf-8").splitlines())
        if n > MAX_LINES and path not in (PAPERS, INDEX):
            problems.append(f"{rel}: {n} lines, over the {MAX_LINES} cap -- it is two topics")

        # --- citations, both directions --------------------------------------------------
        declared = {s["id"] for s in fm.get("sources", []) if isinstance(s, dict) and "id" in s}
        for s in fm.get("sources", []):
            if not isinstance(s, dict) or "id" not in s:
                problems.append(f"{rel}: a `sources:` entry has no `id`")
                continue
            if s["id"] not in bib:
                problems.append(f"{rel}: cites `{s['id']}`, absent from papers.md")
                continue
            if bib[s["id"]]["tier"] == "?" and path != INDEX:
                problems.append(f"{rel}: cites `{s['id']}`, graded `?` (claimed but "
                                "unverified). The tier rules forbid citing it -- say it needs "
                                "checking instead.")
            if "locator" not in s:
                problems.append(f"{rel}: `{s['id']}` has no `locator` (equation or page). "
                                "A citation without one cannot be checked by a reader.")
        used |= declared & set(bib)

        markers = {m["id"] for m in _MARKER.finditer(body)}
        for mid in sorted(markers - declared):
            if mid in bib:
                problems.append(f"{rel}: body cites [{mid}] but it is not in `sources:`")
        for did in sorted(declared - markers):
            problems.append(f"{rel}: `sources:` declares `{did}`, never cited in the body")

    return problems, used


def check_orphans(bib: dict[str, dict], used: set[str]) -> list[str]:
    """The other direction. 216 of terrain-architect's 326 entries were cited by nothing."""
    return [f"papers.md: `{i}` is cited by no document and is not marked [background]"
            for i in sorted(set(bib) - used) if not bib[i]["background"]]


def check_duplication(threshold: float = 0.7) -> list[str]:
    """Once the corpus is large, overlap is the failure mode, not size."""
    docs = []
    for path in documents(ROOT):
        if path in (PAPERS, INDEX):
            continue
        try:
            fm, _ = parse_front_matter(path)
        except Unparseable:
            continue
        ids = {s["id"] for s in fm.get("sources", []) if isinstance(s, dict) and "id" in s}
        docs.append((path.relative_to(ROOT), ids, set(fm.get("tags", []))))

    out = []
    for i, (a, sa, ta) in enumerate(docs):
        for b, sb, tb in docs[i + 1:]:
            if not sa or not sb:
                continue
            j = len(sa & sb) / len(sa | sb)
            if j >= threshold and (ta & tb):
                out.append(f"{a} and {b} share {j:.0%} of their sources and overlapping tags "
                           "-- merge candidates")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="what is checked, and what is not")
    args = ap.parse_args()
    if args.list:
        print(__doc__)
        return 0

    bib, problems = bibliography()
    doc_problems, used = check_documents(bib)
    problems += doc_problems + check_orphans(bib, used) + check_duplication()

    docs = [p for p in documents(ROOT) if p not in (PAPERS, INDEX)]
    print(f"documents {len(docs)}   bibliography {len(bib)}   cited {len(used)}   "
          f"background {sum(1 for e in bib.values() if e['background'])}")

    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\n{len(problems)} problem(s).")
        return 1
    print("\nAttribution is well-formed. That is NOT the same as verified -- see --list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
