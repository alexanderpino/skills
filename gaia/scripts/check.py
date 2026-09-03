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

# `- **id** `T` — Reference text.`  with optional trailing ` [background]` and ` [no-artefact]`.
# [no-artefact] is a STRUCTURED declaration, not prose: it is what lets a locator opt out of the
# locator-quality denominator. It replaced a regex over the entry's prose, which was gameable by
# moving four words onto the first line -- see check_no_artefact.
_ENTRY = re.compile(r"^- \*\*(?P<id>[a-z][a-z0-9_]*)\*\*\s+`(?P<tier>[PFLN?])`\s+—\s+(?P<ref>.+?)"
                    r"(?P<background>\s+\[background\])?(?P<noartefact>\s+\[no-artefact\])?\s*$")
# an inline citation marker in a body: [ocallaghan1984]  (not a markdown link, so not `](`)
_ID_OPENER = re.compile(r"^- \*\*[a-z][a-z0-9_]*\*\*")
_TOPIC = re.compile(r"^- \*\*(?P<id>[a-z][a-z0-9-]*)\*\*\s+`(?P<state>covered|planned|out-of-scope)`"
                    r"\s+—\s+(?P<rest>.+?)\s*$")
_MARKER = re.compile(r"(?<!\])\[(?P<id>[a-z][a-z0-9_]{3,})\](?!\()")


def bibliography() -> tuple[dict[str, dict], list[str]]:
    """id -> {tier, ref, background, no_artefact}. Problems are returned, never raised."""
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
                            "background": bool(m["background"]),
                              "no_artefact": bool(m["noartefact"]), "file": stem}


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


LOCATOR_PRECISE = re.compile(r"""
          §\s*\S                                  # numbered or named section mark
        | \bsecs?\.\s*\d     | \bsections?\s+\d
        | \beqs?\.\s*\(?\d   | \bequations?\s+\(?\d
        | \bpp?\.\s*\d       | \bpages?\s+\d
        | \bfigs?\.\s*\d     | \bfigures?\s+\d
        | \bchs?\.\s*\d      | \bchapters?\s+\d
        | \btables?\s+\d     | \balgorithms?\s+\d
        | \blistings?\s+\d   | \bslides?\s+\d
        | \blines?\s+\d                          # source code: a file and a line range IS
                                                  # a locator, and a sharper one than a section
    """, re.I | re.X)

# A locator that opens with this marker declares there is NOTHING TO OPEN: the claim rests on
# classical results, standard analysis, or a convention this repository recommends, none of
# which has a citable artefact. Those cannot ever become precise, so counting them in the
# denominator makes the metric look permanently unfinished and quietly implies 100% is the
# target. They are reported as their own category, and the author has to declare it in the
# locator rather than a script inferring it from bibliography prose.
LOCATOR_NO_ARTEFACT = "no artefact:"

# The fixture set for LOCATOR_PRECISE, asserted by `--selftest` and run in CI.
# A REPORTED metric never fails, so nothing forces it to be right -- and this one was
# wrong for weeks, counting "the fill algorithm" as a precise locator because it matched
# the bare word "algorithm". Enforced assertions get mutation rows because failing is
# what they do; a reported number needs a fixture set instead, or it is decoration.
# A locator carrying this marker declares the OPPOSITE of `no artefact:`: the artefact exists,
# it is peer-reviewed, and NOBODY IN THIS PROJECT HAS READ IT. The claim rests on the paper's
# reputation and on whatever secondary source reported it.
#
# This exists because the tier vocabulary has no cell for it. `P` means peer-reviewed AND opened;
# demoting an unread paper to `F` would assert "no canonical source", which is a DIFFERENT
# falsehood; and `?` is forbidden from citation, which would make eight documents uncitable. A
# grounding pass hit that wall on 21 sources at once and resolved it in the only honest way
# available -- saying so in the locator. That made the gap visible to a reader and invisible to
# the guard, which is exactly the shape of a number that drifts. So it is counted here.
#
# It is NOT a failure and must never become one. A corpus that cannot cite a paywalled paper is
# not more honest, it is less useful. What matters is that the count is on screen every run.
LOCATOR_NOT_OPENED = ("NOT OPENED", "NO LOCATOR")

NOT_OPENED_FIXTURES = [
    ("\u00a73.1 eq. 1, the stream-power form", False),
    ("the topographic index ln(a / tan beta). NOT OPENED \u2014 the journal is paywalled", True),
    ("NO LOCATOR \u2014 not obtained, and deliberately not guessed", True),
    ("no artefact: a convention this repository recommends", False),
    ("Abstract only; the full text was not reached", False),  # weaker, but something WAS read
]


def not_opened_count() -> tuple[int, int]:
    """(citations declaring the source was never opened, total citations with a locator).

    Deliberately counts the DECLARATION, not the reading -- there is nothing else to count.
    Its only guarantee is that a writer who declines to declare is making a claim in prose that
    the guard will not repeat for them.
    """
    skip = set(paper_files()) | {INDEX, COVERAGE}
    seen = unread = 0
    for path in documents(ROOT):
        if path in skip:
            continue
        try:
            fm, _ = parse_front_matter(path)
        except Unparseable:
            continue
        for src in fm.get("sources", []):
            if not isinstance(src, dict):
                continue
            loc = src.get("locator", "")
            if not loc:
                continue
            seen += 1
            if any(mark in loc for mark in LOCATOR_NOT_OPENED):
                unread += 1
    return unread, seen


LOCATOR_FIXTURES = [
    ("the fill algorithm", False),
    ("the thin-elastic-plate equation", False),
    ("the area-slope channel-initiation threshold, A*S^2 = const", False),
    ("priority-flood; the epsilon variant; complexity analysis", False),
    ("the 8-facet construction", False),
    ("eq. 2, exponent p = 1.1", True),
    ("\u00a73, the 8-neighbour steepest-descent rule", True),
    ("\u00a7Computation of Fn(x)", True),
    ("p. 682", True),
    ("Figure 2, p. 30", True),
    ("\u00a72.3 eq. 6", True),
    ("ch. 2, the GPU-resident form", True),
    ("Table 1", True),
    # Plurals. These are perfectly followable and scored vague until a rendering agent hit
    # them: it had to write "slide 19" singular to get credit for "slides 75-77".
    ("slides 75-77", True),
    ("sections 3-4", True),
    ("Figures 2 and 3", True),
    ("chapters 5 and 6", True),
    # Paraphrases that merely CONTAIN a marker word. All three are real locators from
    # virtual-texturing.md that the original bare-word pattern scored as sharp.
    ("Runtime Virtual Texture -- page composition and invalidation", False),
    ("page tables, the feedback pass, page borders", False),
    ("the software page-table indirection and feedback loop", False),
    # Source code. A grounding agent's honest locator for `lague_erosion` named a file and four
    # line ranges -- more followable than most section numbers, since it survives no reformatting
    # but pins an exact revision -- and scored VAGUE, because the pattern knew every designator
    # a PAPER uses and none that code uses. The metric was penalising the sharpest locator in
    # the corpus.
    ("Erosion.cs lines 47-128, the droplet loop", True),
    ("line 124, the speed update", True),
    ("the droplet loop and brush weights in the published source", False),
]


NO_ARTEFACT_FIXTURES = [
    ("no artefact: the explicit FTCS bound, dt <= dx^2 / (4D) in two dimensions", True),
    ("no artefact: the beam-versus-diffuse attenuation split, c = a + b against K_d", True),
    ("No Artefact: a convention this repository recommends", True),   # case-insensitive
    ("  no artefact: leading whitespace is tolerated", True),
    # These must NOT be swallowed by the marker. The first two are real, followable locators
    # that merely mention absence; the third is the paraphrase form the marker replaces, and
    # letting it through would quietly delete a genuine gap from the denominator.
    ("§4 Ordering, which notes no artefact is required for the eps = 0 case", False),
    ("eq. 26 — the fit has no artefact-free derivation", False),
    ("the fill algorithm", False),
]


def selftest() -> int:
    """Assert the locator pattern classifies known-good and known-bad locators."""
    bad = [(t, want) for t, want in LOCATOR_FIXTURES
           if bool(LOCATOR_PRECISE.search(t)) != want]
    for t, want in bad:
        print(f"  FAIL  locator fixture: {t!r} should be "
              f"{'SHARP' if want else 'vague'}")
    nbad = [(t, want) for t, want in NO_ARTEFACT_FIXTURES
            if t.strip().lower().startswith(LOCATOR_NO_ARTEFACT) != want]
    for t, want in nbad:
        print(f"  FAIL  no-artefact fixture: {t!r} should be "
              f"{'EXCLUDED' if want else 'counted'}")
    ubad = [(t, want) for t, want in NOT_OPENED_FIXTURES
            if any(mark in t for mark in LOCATOR_NOT_OPENED) != want]
    for t, want in ubad:
        print(f"  FAIL  not-opened fixture: {t!r} should be "
              f"{'COUNTED as unread' if want else 'not counted'}")
    if bad or nbad or ubad:
        print(f"\n{len(bad)} of {len(LOCATOR_FIXTURES)} locator fixtures, "
              f"{len(nbad)} of {len(NO_ARTEFACT_FIXTURES)} no-artefact fixtures and "
              f"{len(ubad)} of {len(NOT_OPENED_FIXTURES)} not-opened fixtures misclassified.")
        return 1
    print(f"locator pattern: {len(LOCATOR_FIXTURES)}/{len(LOCATOR_FIXTURES)} fixtures correct; "
          f"no-artefact marker: {len(NO_ARTEFACT_FIXTURES)}/{len(NO_ARTEFACT_FIXTURES)} correct; "
          f"not-opened marker: {len(NOT_OPENED_FIXTURES)}/{len(NOT_OPENED_FIXTURES)} correct.")
    return 0


def locator_quality() -> tuple[int, int, int, list[str]]:
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
    # The first version of this pattern matched the BARE WORDS "equation", "section",
    # "algorithm", "table" and so on -- so "the fill algorithm" and "the thin-elastic-plate
    # equation", both pure topic paraphrases, scored as sharp. The metric was measuring
    # vocabulary, not followability, and it was inflated by exactly the locators it existed to
    # find. A designator is now required: a number after the word, or a section mark. `§` on
    # its own is allowed to introduce a NAME ("§Computation of Fn(x)") because a named section
    # is genuinely followable; the English words are not, because they occur in ordinary prose.
    precise = LOCATOR_PRECISE
    skip = set(paper_files()) | {INDEX, COVERAGE}
    total = sharp = noart = 0
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
            if loc.strip().lower().startswith(LOCATOR_NO_ARTEFACT):
                noart += 1
                continue
            total += 1
            if precise.search(loc):
                sharp += 1
            else:
                vague.append(f"{path.name}:{s.get('id')} -> {loc[:44]}")
    return sharp, total, noart, vague


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


def check_no_artefact(bib: dict[str, dict]) -> list[str]:
    """A `no artefact:` locator is excluded from the locator ratio, so it must be EARNED.

    Without this, the marker is a way to make a gap disappear: paste it onto a real paper's
    locator and the denominator shrinks and the percentage rises. That is precisely the move
    this skill exists to prevent, and it would be invisible -- the guard stays green and the
    number gets better.

    So the claim is checked against the bibliography, in BOTH directions: a locator may open with
    `no artefact:` only if its entry carries the explicit `[no-artefact]` tag, and an entry
    carrying that tag may not be cited anywhere with an ordinary locator.

    An earlier version regex-matched the entry's PROSE for "no canonical source" and read only
    the entry's first physical line. That was gameable and a reviewer demonstrated it: move four
    words onto line 1 of a source with a real, openable artefact and the exclusion passed green,
    moving the reported ratio 53% -> 54%. Prose written by the same author who wrote the locator
    is not a second opinion. An explicit tag is at least an explicit claim, in a different file,
    that a reader can check against the reference it sits beside.
    """
    problems: list[str] = []
    skip = set(paper_files()) | {INDEX, COVERAGE}
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
            if not str(s.get("locator", "")).strip().lower().startswith(LOCATOR_NO_ARTEFACT):
                continue
            sid = s.get("id")
            entry = bib.get(sid)
            if entry is None:
                continue                      # a dangling id is reported by check_documents
            if not entry["no_artefact"]:
                problems.append(
                    f"{path.relative_to(ROOT)}: `{sid}` is marked `no artefact:`, which excludes "
                    f"it from the locator ratio, but its bibliography entry in "
                    f"{entry['file']} is not tagged [no-artefact]. Either the marker is wrong, "
                    f"or the entry must declare it -- do not shrink the denominator by assertion")

    # And the other direction: an entry tagged [no-artefact] that some document cites with a
    # REAL locator is either mistagged or being cited beyond what it can support.
    for sid, entry in sorted(bib.items()):
        if not entry["no_artefact"]:
            continue
        for path in documents(ROOT):
            if path in skip:
                continue
            try:
                fm, _ = parse_front_matter(path)
            except Unparseable:
                continue
            for s2 in fm.get("sources", []):
                if not isinstance(s2, dict) or s2.get("id") != sid:
                    continue
                loc = str(s2.get("locator", "")).strip().lower()
                if not loc.startswith(LOCATOR_NO_ARTEFACT):
                    problems.append(
                        f"{path.relative_to(ROOT)}: `{sid}` is tagged [no-artefact] in "
                        f"{entry['file']}, but this document gives it a locator that does not "
                        f"open with `{LOCATOR_NO_ARTEFACT}`. A source cannot have no artefact "
                        f"here and an openable one there")
    return problems


def check_recommendation() -> tuple[list[str], int, int]:
    """Every content document must NAME AN APPROACH TO IMPLEMENT, in a `## Use this` section.

    This is the one item on the plan's verification list that was never implemented. The plan
    wanted it checked by shape -- "flag any document where a named alternative gets its own
    heading" -- and that version is unbuildable without false positives: a real time-budget
    crossover legitimately gives alternatives their own space, and a guard that cries wolf on
    the corpus's best documents gets ignored within a week.

    What IS checkable without ambiguity is the other half of the same doctrine: the
    recommendation has to exist, and it has to be findable. A document with no `## Use this`
    is a survey, and this skill's whole claim over a literature review is that it recommends.

    Whether that section comes FIRST is reported, not enforced. `caustics.md` legitimately
    defines the phenomenon before recommending a tier, and hard-failing it would be the guard
    dictating prose order. But a corpus quietly drifting toward explain-then-maybe-recommend
    is the slide into a survey, so the count is visible.
    """
    problems: list[str] = []
    skip = set(paper_files()) | {INDEX, COVERAGE}
    total = first = 0
    for path in documents(ROOT):
        if path in skip:
            continue
        body = path.read_text(encoding="utf-8")
        heads = [ln.strip() for ln in body.splitlines() if ln.startswith("## ")]
        if not any(h.lower().startswith("## use this") for h in heads):
            problems.append(f"{path.relative_to(ROOT)}: no `## Use this` section -- it "
                            "surveys rather than recommends, or the recommendation is buried")
            continue
        total += 1
        if heads and heads[0].lower().startswith("## use this"):
            first += 1
    return problems, first, total


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
    ap.add_argument("--selftest", action="store_true",
                    help="assert the reported metrics classify their fixture sets correctly")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.list:
        print(__doc__)
        return 0

    bib, problems = bibliography()
    doc_problems, used = check_documents(bib)
    rec_problems, rec_first, rec_total = check_recommendation()
    problems += (doc_problems + check_orphans(bib, used) + check_duplication()
                 + check_coverage() + check_index() + rec_problems
                 + check_no_artefact(bib))

    docs = [p for p in documents(ROOT)
            if p not in paper_files() and p not in (INDEX, COVERAGE)]
    print(f"documents {len(docs)}   bibliography {len(bib)}   cited {len(used)}   "
          f"background {sum(1 for e in bib.values() if e['background'])}")
    if (summary := coverage_summary()):
        print(summary)
    if rec_total:
        print(f"recommendation {rec_total}/{rec_total} documents name an approach to "
              f"implement; {rec_first} state it first, before any explanation.")

    sharp, tot, noart, _vague = locator_quality()
    if tot:
        print(f"locators {sharp}/{tot} ({100 * sharp / tot:.0f}%) of the FOLLOWABLE citations "
              f"name a section, equation or page; the rest are topic paraphrases a reader "
              f"cannot follow. A further {noart} cite doctrine or classical results with no "
              f"artefact to open — declared in the locator, and excluded from the ratio rather "
              f"than held against it. Reported, not enforced; see registers/guard-proofs.tsv.")

    unread, seen = not_opened_count()
    if seen:
        print(f"unread {unread}/{seen} ({100 * unread / seen:.0f}%) of citations DECLARE that "
              f"the source was never opened here — paywalled, or not obtainable — so the claim "
              f"rests on the paper's reputation and on whatever secondary source reported it. "
              f"Not a failure: a corpus that cannot cite a paywalled paper is less useful, not "
              f"more honest. The tier vocabulary has no cell for 'peer-reviewed, not read', so "
              f"this counts the declaration instead. A writer who declines to declare is making "
              f"a claim in prose the guard will not repeat for them.")

    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\n{len(problems)} problem(s).")
        return 1
    print("\nAttribution is well-formed. That is NOT the same as verified -- see --list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
