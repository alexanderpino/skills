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
import hashlib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from okf import Unparseable, documents, parse_front_matter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "references" / "index.md"
COVERAGE = ROOT / "references" / "coverage.md"


def paper_files() -> list[Path]:
    """The bibliography, split by family across `papers*.md`.

    One file would serialise every author onto one merge point; families are how 99-papers.md
    already organises itself, and splitting lets documents and their sources land together.
    Globbed from disk, never listed by hand -- a hand-kept list is the thing that goes stale.
    """
    return sorted((ROOT / "references").glob("papers*.md"))

MAX_LINES = 450          # per the plan: a document at the cap is two topics wanting a split
TIERS = {"P", "F", "L", "N", "?"}
STATUS = {"draft", "stable", "deprecated"}

# `- **id** `T` — Reference text.`  with an optional trailing ` [background]`
_ENTRY = re.compile(r"^- \*\*(?P<id>[a-z][a-z0-9_]*)\*\*\s+`(?P<tier>[PFLN?])`\s+—\s+(?P<ref>.+?)"
                    r"(?P<background>\s+\[background\])?\s*$")
# an inline citation marker in a body: [ocallaghan1984]  (not a markdown link, so not `](`)
_ID_OPENER = re.compile(r"^- \*\*[a-z][a-z0-9_]*\*\*")
_TOPIC = re.compile(r"^- \*\*(?P<id>[a-z][a-z0-9-]*)\*\*\s+`(?P<state>covered|planned|out-of-scope)`"
                    r"\s+—\s+(?P<rest>.+?)\s*$")
_MARKER = re.compile(r"(?<!\])\[(?P<id>[a-z][a-z0-9_]{3,})\](?!\()")


def bibliography() -> tuple[dict[str, dict], list[str]]:
    """id -> {tier, ref, background}. Problems are returned, never printed and swallowed."""
    problems: list[str] = []
    files = paper_files()
    if not files:
        return {}, ["references/papers*.md: no bibliography file exists"]
    entries: dict[str, dict] = {}
    for papers in files:
        try:
            fm, body = parse_front_matter(papers)
        except Unparseable as e:
            # Reported, not raised. Raising here aborted the run before a single document was
            # checked -- and this function's own docstring promised problems are returned.
            problems.append(str(e))
            continue
        _scan(papers, body, entries, problems, _offset(papers))
    return entries, problems


def _offset(path: Path) -> int:
    """Lines consumed by the front matter, so reported numbers point at the real file line.

    Without this the guard printed body-relative numbers as if they were file numbers, sending
    a reader to an unrelated line -- and the proof register enshrined the wrong number as
    expected output.
    """
    n = 0
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n")):
        if line.strip() == "---":
            n += 1
            if n == 2:
                return i + 2
    return 1


def _scan(papers: Path, body: str, entries: dict, problems: list, offset: int = 1) -> None:
    stem = papers.name
    in_fence = False
    for n, line in enumerate(body.split("\n"), offset):
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
            problems.append(f"{stem}:{n}: entry does not match "
                            f"`- **id** `T` -- Reference.`  ->  {line.strip()[:60]}")
            continue
        if m["id"] in entries:
            problems.append(f"{stem}:{n}: duplicate id `{m['id']}` "
                            f"(already defined in {entries[m['id']]['file']})")
        entries[m["id"]] = {"tier": m["tier"], "ref": m["ref"].strip(),
                            "background": bool(m["background"]), "file": stem}


def sources_digest(fm: dict) -> str:
    """A short fingerprint of exactly what a document cites, id and locator.

    Verification has to be SCOPED to something. Without this, `verified:` was a permanent
    label: a document could be stamped, then gain three new citations and a new claim, and
    still present itself as checked. The digest ties the stamp to the source set that existed
    when a human read it, so adding or re-pointing a citation invalidates it automatically.
    """
    rows = sorted((str(s.get("id", "")), str(s.get("locator", "")))
                  for s in fm.get("sources", []) if isinstance(s, dict))
    return hashlib.sha256("\n".join(f"{i}|{l}" for i, l in rows).encode()).hexdigest()[:12]


def _unfenced(body: str) -> str:
    """Body with code blanked, so indexing is never read as a citation.

    Markdown has TWO code-block forms and handling only fences was not enough: `receivers[i]`
    and `A[i]` in an INDENTED block were reported as fabricated citations to `i`. Both forms
    are blanked here.

    A citation id is also required to be at least four characters. Every real id in this
    corpus is six or more; `i`, `r`, `n`, `xy` are loop variables. The cost is that a
    fabricated three-letter citation would slip -- stated rather than hidden, and cheap
    against the alternative of a guard that cries wolf on every code sample until someone
    switches it off.
    """
    out, fence = [], False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append("")
            continue
        if fence or (line[:4] == "    " and line.strip()):
            out.append("")
            continue
        # Inline code spans too. `max(h[i], h[r])` in prose is indexing, and this is where the
        # last false positives came from after both block forms were handled -- three places
        # markdown can hold code, and a guard that knows about two of them cries wolf.
        out.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(out)


def check_documents(bib: dict[str, dict]) -> tuple[list[str], set[str]]:
    problems: list[str] = []
    used: set[str] = set()

    skip = set(paper_files()) | {INDEX, COVERAGE}
    for path in documents(ROOT):
        # Bibliographies, the index and the coverage map make no claims of their own -- they
        # are apparatus, and each has its own check. Demanding `sources:` from them would be
        # the guard misreading its own furniture as content.
        if path in skip:
            continue
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
        digest = sources_digest(fm)
        for entry in (ver if isinstance(ver, list) else [ver] if ver else []):
            who = str(entry.get("by", "")) if isinstance(entry, dict) else ""
            if not who.startswith("human:") or len(who) <= len("human:"):
                problems.append(f"{rel}: `verified:` needs a named `human:<id>` actor. "
                                "`human:` alone names nobody, and a process can only generate.")
            elif entry.get("covers") != digest:
                problems.append(
                    f"{rel}: `verified:` covers `{entry.get('covers')}` but the sources now "
                    f"digest to `{digest}`. The citations changed since {who} read them, so "
                    "the verification is stale. Re-check and update `covers`, or drop to draft.")
        if fm.get("status") == "stable" and not ver:
            problems.append(f"{rel}: status `stable` with no `verified:` entry -- stable claims "
                            "a human checked the citations. Use `draft` until one has.")

        # --- size ------------------------------------------------------------------------
        n = len(path.read_text(encoding="utf-8").splitlines())
        if n > MAX_LINES and path not in paper_files() and path != INDEX:
            problems.append(f"{rel}: {n} lines, over the {MAX_LINES} cap -- it is two topics")

        # --- citations, both directions --------------------------------------------------
        # A document with no `sources:` used to pass everything, because only DECLARED sources
        # were examined. That made the guard's headline claim false: nothing tied prose to a
        # citation, so a document of pure invention was "well-formed". A technique document
        # with no citations is not a well-formed document; it is an unsourced opinion.
        if not fm.get("sources"):
            problems.append(f"{rel}: no `sources:`. A document that cites nothing cannot be "
                            "checked at all -- if it genuinely needs none, it is not a "
                            "Technique; give it a type the guard exempts.")
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
            if "tier" in s and s["tier"] != bib[s["id"]]["tier"]:
                problems.append(f"{rel}: declares `{s['id']}` as tier `{s['tier']}`, but "
                                f"papers grades it `{bib[s['id']]['tier']}`. A tier written "
                                "here and never compared is decoration that reads as a check.")
            # `"locator" not in s` alone accepted "", " " and 0 -- the key present and saying
            # nothing. The register claimed this proved "a citation a reader cannot check";
            # it proved only that a key existed.
            if len(str(s.get("locator", "")).strip()) < 3:
                problems.append(f"{rel}: `{s['id']}` has no usable `locator` (equation, section "
                                "or page). A citation a reader cannot follow is not a citation.")
        used |= declared & set(bib)

        markers = {m["id"] for m in _MARKER.finditer(_unfenced(body))}
        for mid in sorted(markers - declared):
            # `if mid in bib` used to guard this, so a marker matching NOTHING ANYWHERE -- a
            # fabricated citation, the single worst thing this skill can ship -- was dropped
            # in silence. An unknown marker is now the loudest failure here.
            if mid in bib:
                problems.append(f"{rel}: body cites [{mid}] but it is not in `sources:`")
            else:
                problems.append(f"{rel}: body cites [{mid}], which exists in NO bibliography. "
                                "A citation to nothing is a fabrication, not a typo.")
        for did in sorted(declared - markers):
            problems.append(f"{rel}: `sources:` declares `{did}`, never cited in the body")

    return problems, used


def locator_quality() -> tuple[int, int, list[str]]:
    """How many citations can a reader actually follow?

    The guard requires a `locator` and rejects an empty one, which is a floor, not a
    standard: a topic paraphrase ("the fill algorithm" -- that is the entire paper) passes
    exactly like "eq. 7". An audit found only ~15 of ~120 locators carried a section or
    equation number, and no guard could see the difference.

    This is REPORTED, not enforced. Failing the ~105 topic-paraphrase locators today would
    make the guard red for a week and teach everyone to ignore it; a visible ratio that has
    to go up is the honest instrument. It is deliberately a metric, and it is recorded as an
    OPEN row in registers/guard-proofs.tsv rather than counted as a passing check.
    """
    precise = re.compile(r"(§|\bsec\.|\bsection\b|\beq\.|\bequation\b|\bp\.|\bpp\.|"
                         r"\bpage\b|\bfig\.|\bfigure\b|\bslide\b|\bch\.|\bchapter\b|"
                         r"\btable\b|\balgorithm\b|\blisting\b)", re.I)
    skip = set(paper_files()) | {INDEX, COVERAGE}
    total = sharp = 0
    vague: list[str] = []
    for path in documents(ROOT):
        if path in skip:
            continue
        try:
            fm, _ = parse_front_matter(path)
        except Unparseable:
            continue
        for s in fm.get("sources", []):
            if not isinstance(s, dict):
                continue
            loc = str(s.get("locator", ""))
            total += 1
            if precise.search(loc):
                sharp += 1
            else:
                vague.append(f"{path.name}:{s.get('id')} -> {loc[:44]}")
    return sharp, total, vague


def check_orphans(bib: dict[str, dict], used: set[str]) -> list[str]:
    """The other direction. 216 of terrain-architect's 326 entries were cited by nothing."""
    return [f"{bib[i]['file']}: `{i}` is cited by no document and is not marked [background]"
            for i in sorted(set(bib) - used) if not bib[i]["background"]]


def check_duplication(threshold: float = 0.7) -> list[str]:
    """Once the corpus is large, overlap is the failure mode, not size."""
    docs = []
    for path in documents(ROOT):
        if path in paper_files() or path == INDEX:
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


def check_coverage() -> list[str]:
    """Completeness, checked both ways.

    "The skill is complete" is unfalsifiable until the skill declares what it is trying to
    cover. coverage.md is that denominator, and this asserts the two directions that make it
    real: a `covered` topic must point at a document that exists, and every document must be
    claimed by exactly one topic. A document nobody planned means the map is stale; a plan
    nobody wrote means the corpus has a hole. Both are reported.
    """
    problems: list[str] = []
    if not COVERAGE.exists():
        return ["references/coverage.md is missing -- without it, completeness cannot be checked"]
    try:
        _, body = parse_front_matter(COVERAGE)
    except Unparseable as e:
        return [str(e)]

    claimed: dict[str, str] = {}
    in_fence = False
    for n, line in enumerate(body.split("\n"), _offset(COVERAGE)):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line.startswith("- **"):
            continue
        m = _TOPIC.match(line.rstrip())
        if not m:
            problems.append(f"coverage.md:{n}: row does not match "
                            f"`- **topic** `state` -- question. -> file.md`  ->  "
                            f"{line.strip()[:60]}")
            continue
        rest = m["rest"]
        if m["state"] == "covered":
            if "\u2192" not in rest:
                problems.append(f"coverage.md:{n}: `{m['id']}` is covered but names no document")
                continue
            target = rest.split("\u2192")[-1].strip()
            if not (ROOT / "references" / target).exists():
                problems.append(f"coverage.md:{n}: `{m['id']}` points at {target}, "
                                "which does not exist")
                continue
            if target in claimed:
                problems.append(f"coverage.md:{n}: {target} is claimed by both "
                                f"`{claimed[target]}` and `{m['id']}`")
            claimed[target] = m["id"]
        else:
            # The two states need different things, and one threshold for both was wrong.
            # `planned` must state THE QUESTION the topic answers, so the gap is legible to
            # whoever picks it up. `out-of-scope` must state WHY NOT -- without that it is a
            # shrug, and the same topic gets re-proposed next quarter.
            floor = 25 if m["state"] == "planned" else 60
            if len(rest.strip()) < floor:
                want = ("the question it answers" if m["state"] == "planned"
                        else "why it is excluded, at length enough to settle it")
                problems.append(f"coverage.md:{n}: `{m['id']}` is `{m['state']}` but does not "
                                f"state {want}")

    on_disk = ({p.name for p in documents(ROOT)} - {q.name for q in paper_files()}
               - {INDEX.name, COVERAGE.name})
    problems += [f"references/{o} exists but no coverage.md topic claims it -- the map is "
                 "stale, or the document was never planned" for o in sorted(on_disk - set(claimed))]
    return problems


def coverage_summary() -> str:
    try:
        _, body = parse_front_matter(COVERAGE)
    except (OSError, Unparseable):
        return ""
    rows = [m for m in (_TOPIC.match(l.rstrip()) for l in body.split("\n")) if m]
    c = sum(1 for m in rows if m["state"] == "covered")
    pl = sum(1 for m in rows if m["state"] == "planned")
    o = sum(1 for m in rows if m["state"] == "out-of-scope")
    return f"coverage {c} written / {c + pl} in scope, {pl} planned, {o} out of scope"


def check_index() -> list[str]:
    """One entry point. `check.py` used to be silent about a stale or unroutable index, so the
    documented command could go green on a corpus with a document nothing could route to."""
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("index.py")), "--check"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return []
    return [ln.strip().removeprefix("FAIL").strip() or ln.strip()
            for ln in (r.stdout + r.stderr).splitlines() if ln.strip()][:8]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="what is checked, and what is not")
    args = ap.parse_args()
    if args.list:
        print(__doc__)
        return 0

    bib, problems = bibliography()
    doc_problems, used = check_documents(bib)
    problems += (doc_problems + check_orphans(bib, used) + check_duplication()
                 + check_coverage() + check_index())

    docs = [p for p in documents(ROOT)
            if p not in paper_files() and p not in (INDEX, COVERAGE)]
    print(f"documents {len(docs)}   bibliography {len(bib)}   cited {len(used)}   "
          f"background {sum(1 for e in bib.values() if e['background'])}")
    if (summary := coverage_summary()):
        print(summary)
    sharp, tot, _vague = locator_quality()
    if tot:
        print(f"locators {sharp}/{tot} ({100 * sharp / tot:.0f}%) name a section, equation or "
              f"page — the rest are topic paraphrases a reader cannot follow. Reported, not "
              f"enforced; see registers/guard-proofs.tsv.")

    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\n{len(problems)} problem(s).")
        return 1
    print("\nAttribution is well-formed. That is NOT the same as verified -- see --list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
