"""Gaia's one guard. Run it before believing anything this skill says.

    python gaia/scripts/check.py            # report and exit non-zero on any problem
    python gaia/scripts/check.py --list     # what is checked, and what is NOT
    python gaia/scripts/check.py --digest references/caustics.md   # the two digests a stamp needs

WHAT THIS CAN AND CANNOT ESTABLISH -- read this before quoting a green run.

It checks the FORM of attribution: every claim points at a bibliography entry, every entry is
used, every entry carries a provenance tier, nothing is orphaned, no document cites something
graded unverifiable. It CANNOT check that a cited paper says what the document claims. That
one step is human, and `verified:` in a document's front matter is where a human records
having done it.

In this repo's vocabulary a green run here is an `attestation` channel, not an `independent`
one: the same kind of author writes the claim, the citation and this guard. Saying "grounded"
because this passes would be the exact overstatement Gaia exists to avoid.

Two structural facts about a document are checked against each other rather than reported. A
`**Tier:` line's budget regime must agree with the budget tag in `tags:`, in BOTH directions:
a regime named on the page must be a tag, and a tag must be named on the page. It CANNOT check
that the regime is true -- a real-time claim over a 400 ms recommendation is agreement, not
correctness -- and a document with no Tier line at all is an ALLOWED state, counted and named,
because the 450-line cap refuses the insertion in the documents nearest it, which the run
names. And every
`document.md` a body names in a code span must be a document that exists: that is a FAILURE,
not a metric, because the same dangling reference in coverage.md's `→ target` column has always
been one. Its reach is gaia's own naming shape; bare `.md` names belonging to other
repositories -- five of them, `19-fluid-simulation.md` among them -- are named in the output
and NOT checked, and `.py` and `.tsv` paths are not read at all.

It also checks the SHAPE of `registers/pseudocode-execution.tsv`: seven fields, the header that
names them, and a `termination` token from a closed vocabulary, so that no row can be silent
about whether its block halts. It cannot check that the token is TRUE -- `halts-proven` is worth
exactly the argument written beside it. The `unknown` count and the count of documents holding a
fenced block that no row names are REPORTED, never enforced.

One idiom in that register is enforced too: a cell may not name another row of the same file by
line number. Rows have no stable lines -- the edit that added the `termination` column inserted
55 lines of header and left seven cells pointing 55 lines short, into the comment block, every
one of them still well-formed and none of them caught. References INTO reference documents
(`flow-routing.md:239`) are the correct idiom and are deliberately not checked: those files are
edited daily by other hands, and a guard over them would be permanently red on other people's
work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from okf import Unparseable, documents, parse_front_matter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "references" / "index.md"
COVERAGE = ROOT / "references" / "coverage.md"
TRIGGERS = ROOT / "evals" / "trigger-evals.json"
PSEUDOCODE = ROOT / "registers" / "pseudocode-execution.tsv"


# One spelling of the bibliography glob, used by `paper_files()` and by the error text that
# names it. They disagreed for a whole rename: the files became `papers-*.md` and the guard went
# on telling readers a citation was "absent from papers.md", a file that no longer existed.
PAPERS_GLOB = "papers*.md"


def paper_files() -> list[Path]:
    """The bibliography, split by family across `papers*.md`.

    One file would serialise every author onto one merge point; families are how 99-papers.md
    already organises itself, and splitting lets documents and their sources land together.
    Globbed from disk, never listed by hand -- a hand-kept list is the thing that goes stale.
    """
    return sorted((ROOT / "references").glob(PAPERS_GLOB))

MAX_LINES = 450          # per the plan: a document at the cap is two topics wanting a split
# A bibliography is a LIST, not a topic, and it grows with the corpus by design -- so the
# "it is two topics" reading of the cap does not apply to it. It was exempt from the cap
# altogether, by two conditions that could never fire (the paths were already excluded from
# the loop), which is not a decision, it is a leftover: papers-rendering.md reached 411 lines
# with no ceiling at all. They get a looser cap of their own instead of none. Past it, a family
# file wants splitting the way `papers.md` itself already was.
BIB_MAX_LINES = 600
TIERS = {"P", "F", "L", "N", "?"}
STATUS = {"draft", "stable", "deprecated"}
# The only keys a `sources:` row may carry. `Tier:`, `teir:` and `locater:` all used to pass
# in silence, and a misspelled `tier:` is worse than an absent one: the tier-agreement check
# reads `if "tier" in s`, so the row loses its comparison while still LOOKING graded on the
# page. An unknown key here is either a typo or a field nothing reads.
SOURCE_KEYS = {"id", "tier", "locator"}

# `- **id** `T` — Reference text.`  with optional trailing ` [background]` and ` [no-artefact]`.
# [no-artefact] is a STRUCTURED declaration, not prose: it is what lets a locator opt out of the
# locator-quality denominator. It replaced a regex over the entry's prose, which was gameable by
# moving four words onto the first line -- see check_no_artefact.
# `[not-opened]` sits IMMEDIATELY AFTER THE TIER, unlike `[background]` and `[no-artefact]`,
# which trail the entry. That is deliberate and not an inconsistency: those two qualify the
# entry's ROLE, while this one qualifies the GRADE, and a reader scanning tiers has to see it
# in the same glance. Trailing it would bury it after a paragraph of commentary, which is
# exactly how eighteen unread `P` entries went unnoticed for as long as they did.
_ENTRY = re.compile(r"^- \*\*(?P<id>[a-z][a-z0-9_]*)\*\*\s+`(?P<tier>[PFLN?])`"
                    r"(?P<notopened>\s+\[not-opened\])?\s+—\s+(?P<ref>.+?)"
                    r"(?P<background>\s+\[background\])?(?P<noartefact>\s+\[no-artefact\])?"
                    r"(?P<notopened_trailing>\s+\[not-opened\])?\s*$")
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
                            "no_artefact": bool(m["noartefact"]),
                            "not_opened": bool(m["notopened"] or m["notopened_trailing"]),
                            "file": stem}


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


_EMPTY_BODY_DIGEST = hashlib.sha256(b"").hexdigest()[:12]


def body_digest(body: str) -> str:
    """A fingerprint of the two sections a reader actually lands on.

    `sources_digest` scopes a stamp to a CITATION SET, which is necessary and not sufficient.
    Reproduced end to end before this existed: stamp a document, then replace EVERY prose
    sentence in its body with an invention -- keeping headings, tables and citation markers --
    and the guard exits 0 while the index goes on printing **checked**. The stamp certified
    which papers were cited, and the claims are what a human actually read.

    Hashing the whole body would make a stamp brittle against a typo fix, which is how a
    digest gets routed around. `## Use this` and the failure table are the two places this
    corpus's readers land (`SKILL.md:42` tells them to take the failure table as one packet)
    and the two places its recorded corrections land. The text is whitespace-normalised, so a
    re-wrap or a reflow is not a change; a word is.

    ⚠️ WHAT THIS CANNOT SEE, stated so no one reads a valid stamp as a checked document. It is
    a digest, not a reader: it detects that the anchors MOVED, never that they are wrong, and
    the three defect shapes this audit records most often all sit outside its scope.
      * X7 (`gpu-driven-culling.md:108`, an inverted consequence one bullet below its own
        correct statement) lives in body prose. It is not hashed, and a stamp survives both the
        defect and its fix untouched.
      * X17 (`node-graph-runtime.md:232` vs `:386`, opposite prescriptions for one decision)
        and X52 (`mask-to-material.md:296,300`, a retracted claim re-asserted in two failure
        rows) sit INSIDE the anchors and are hashed -- but they shipped that way, so a human
        stamping the document would digest the defect along with everything else.
    A hash scopes a reading. It does not perform one.
    """
    parts = re.split(r"^## +(.+?)\s*$", body, flags=re.M)
    chunks = [" ".join((h + " " + b).split())
              for h, b in zip(parts[1::2], parts[2::2]) if _is_anchor(h.strip().lower())]
    return hashlib.sha256("\n".join(chunks).encode()).hexdigest()[:12]


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

    papers = set(paper_files())
    apparatus_paths = papers | {INDEX, COVERAGE}
    for path in documents(ROOT):
        rel = path.relative_to(ROOT)
        try:
            fm, body = parse_front_matter(path)
        except Unparseable as e:
            problems.append(str(e))
            continue

        # Bibliographies, the index and the coverage map make no claims of their own -- they
        # are apparatus. But `if path in skip: continue` at the top of this loop exempted them
        # from the OKF conformance block as well, and that block is the FORMAT contract for
        # every document in the bundle: a bibliography could lose its `type:`, take an illegal
        # `status:`, grow an `okf_version:` or carry a `verified:` naming nobody, and nothing
        # here looked. What apparatus is still exempt from is the whole CITATION block --
        # not, as this comment once claimed, exactly two things. `if apparatus: continue`
        # below skips the `sources:` requirement, the body-marker cross-check AND every
        # per-entry check with them, so a `sources:` row on a bibliography with a dangling
        # id and a misspelled key produces no failure at all. That is safe only while no
        # apparatus file carries `sources:`; the day one does, this exemption has to narrow.
        #
        # The second half of that exemption is not cosmetic. `papers-flow.md:146` ends a prose
        # sentence with the literal `[background]`, which `_MARKER` reads as a citation to an id
        # that exists in no bibliography -- so running the cross-check over apparatus reports a
        # fabricated citation in a clean corpus. Verified by running it; the marker is prose
        # about the tag, not a citation.
        apparatus = path in apparatus_paths

        # --- OKF conformance, on EVERY document ------------------------------------------
        if "type" not in fm:
            problems.append(f"{rel}: no `type` -- the one always-required OKF key")
        # ABSENT `status:` is a failure, not a default. Three sites used to disagree about a
        # missing key: this one validated it as `stable`, the "stable needs `verified:`" rule
        # below read None and never fired, and index.py PRINTED stable -- so DELETING one line
        # from a draft document advertised it as checked by a human, past both guards. The
        # obvious repair, defaulting to `draft` here and in index.py, fixes the display and
        # makes its own mutation a no-op: a draft with the line deleted is still a draft, so
        # nothing could ever be seen going red. The key is required instead.
        status = fm.get("status")
        if status is None:
            problems.append(f"{rel}: no `status:` -- required, not defaulted. An absent status "
                            "read as `stable` in the index and as neither value in this guard, "
                            "so deleting one line advertised a document as human-checked.")
        elif not isinstance(status, str):
            # `status:` with an empty value parses to a list, and `in STATUS` on an
            # unhashable raised TypeError -- CI went red with a traceback instead of a
            # FAIL line, breaking this module's promise that problems are returned,
            # never raised.
            problems.append(f"{rel}: status `{status!r}` is not a scalar. Write one of "
                            f"{sorted(STATUS)} on the line, unquoted.")
        elif status not in STATUS:
            problems.append(f"{rel}: status `{status}` is not one of {sorted(STATUS)}")
        if "okf_version" in fm and path != INDEX:
            problems.append(f"{rel}: `okf_version` belongs in the bundle root only")
        # `generated` is not `verified`. A document may not claim a human checked it unless a
        # human is named -- this is the only line between attribution and verification.
        ver = fm.get("verified")
        digest, bdigest = sources_digest(fm), body_digest(body)
        for entry in (ver if isinstance(ver, list) else [ver] if ver else []):
            who = str(entry.get("by", "")) if isinstance(entry, dict) else ""
            # `len(who) > len("human:")` passed `by: "human: "` -- seven characters, naming
            # nobody. What has to be non-empty is the ID, not the string.
            if not (who.startswith("human:") and who[len("human:"):].strip()):
                problems.append(f"{rel}: `verified:` needs a named `human:<id>` actor. "
                                f"`{who}` names nobody -- `human:` with nothing after it is not "
                                "an actor, and a process can only generate.")
                continue
            # A stamp over NO anchor section certifies nothing. Apparatus -- the
            # bibliographies, index.md, coverage.md -- has neither `## Use this` nor a failure
            # table, so `body_digest` hashes the empty string and every one of them digests to
            # the same value. Proved end to end: stamp a bibliography, replace all 19 of its
            # references with inventions attributed to nobody, and this guard stayed green while
            # the index printed **checked**. One such stamp is valid on all nine files. Phase 0
            # made these rules REACHABLE on apparatus; without this line it made them vacuous.
            if bdigest == _EMPTY_BODY_DIGEST:
                problems.append(
                    f"{rel}: `verified:` on a document with neither `## Use this` nor a failure "
                    f"table. `covers_body` is the digest of the empty string here, so the stamp "
                    f"is identical on every such file and scopes to nothing. Stamp a Technique, "
                    f"or give this document the two anchor sections first.")
                continue
            if not isinstance(entry, dict) or "covers" not in entry or "covers_body" not in entry:
                missing = [k for k in ("covers", "covers_body")
                           if not isinstance(entry, dict) or k not in entry]
                problems.append(
                    f"{rel}: `verified:` is missing {', '.join(f'`{k}`' for k in missing)}. A "
                    f"stamp scopes to BOTH halves of what was read: `covers` is the citation "
                    f"set (now `{digest}`), `covers_body` is `## Use this` and the failure "
                    f"table (now `{bdigest}`). Without the second, every claim in the document "
                    f"can be replaced and the stamp stays valid.")
                continue
            # Which half moved is the whole message. "The digest changed" sends a reader to
            # re-read a document when all that happened was a new citation, or the reverse.
            moved = []
            if entry["covers"] != digest:
                moved.append(f"the SOURCES changed -- `covers` says `{entry['covers']}`, they "
                             f"now digest to `{digest}`")
            if entry["covers_body"] != bdigest:
                moved.append(f"the CLAIMS changed -- `covers_body` says "
                             f"`{entry['covers_body']}`, `## Use this` and the failure table "
                             f"now digest to `{bdigest}`")
            if moved:
                problems.append(f"{rel}: `verified:` is stale: " + "; and ".join(moved) +
                                f". That happened after {who} read it, so the verification no "
                                "longer covers the document. Re-check and update the digest, "
                                "or drop to draft.")
        if status == "stable" and not ver:
            problems.append(f"{rel}: status `stable` with no `verified:` entry -- stable claims "
                            "a human checked the citations. Use `draft` until one has.")
        # And the other direction. index.py prints **checked** on the presence of `verified:`
        # alone, so a draft carrying a stamp read as verified in the index while its own status
        # line said otherwise. A stamp is what makes a document stable; the two must agree.
        if ver and status != "stable":
            problems.append(f"{rel}: `verified:` on a `{status}` document. The index prints "
                            "**checked** for any document carrying a stamp, so this advertises "
                            "a verification the status line denies. A stamp requires "
                            "`status: stable`.")

        # --- size ------------------------------------------------------------------------
        # index.md is generated: its length is a function of how many documents exist, so a cap
        # on it would report the corpus growing as a defect. Every other file has one.
        if path != INDEX:
            cap = BIB_MAX_LINES if path in papers else MAX_LINES
            n = len(path.read_text(encoding="utf-8").splitlines())
            if n > cap:
                problems.append(f"{rel}: {n} lines, over the {cap} cap -- {'split the family' if cap == BIB_MAX_LINES else 'it is two topics'}")

        if apparatus:
            continue

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
            # Checked before the id is resolved, so a row that is BOTH misspelled and dangling
            # still reports the misspelling.
            extra = sorted(set(s) - SOURCE_KEYS)
            if extra:
                problems.append(f"{rel}: `{s['id']}` carries unknown `sources:` key(s) "
                                f"{', '.join(f'`{k}`' for k in extra)}; only "
                                f"{', '.join(f'`{k}`' for k in sorted(SOURCE_KEYS))} are read. "
                                "A misspelled `tier:` is worse than an absent one -- the row "
                                "still looks graded on the page and nothing compares it.")
            # The bibliography was split into seven `papers-*.md` files and this message went on
            # naming `papers.md`, which has not existed since. `guard-proofs.tsv:17` already
            # records that rows naming it were a known post-rename problem -- the register was
            # corrected and the guard's own error text was not, inside the tool that polices
            # exactly that shape. Named from the glob so a future split cannot stale it again.
            if s["id"] not in bib:
                problems.append(f"{rel}: cites `{s['id']}`, absent from every "
                                f"references/{PAPERS_GLOB} "
                                f"({', '.join(p.name for p in paper_files())})")
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

# The ENTRY side of the same claim. These assert the grammar accepts the tag where it belongs
# and nowhere else -- a tag the regex silently dropped would turn the bidirectional check into a
# one-directional one, and the corpus would drift back to a tier saying "read" beside a locator
# saying "not read".
ENTRY_TAG_FIXTURES = [
    ("- **beven1979** `P` [not-opened] — Beven, K. (1979). *A physically based model.*", True),
    ("- **beven1979** `P` — Beven, K. (1979). *A physically based model.*", False),
    ("- **strat_authoring** `F` [not-opened] — No canonical source. [no-artefact]", True),
    ("- **burt1983** `P` — Burt, P.J. (1983). *The Laplacian Pyramid.* [background]", False),
    # An author writes the tag where the two SIBLING tags go -- at the END. There it used to be
    # swallowed silently by the `ref` group, with no format error, because the line still
    # matched. most entries wrap onto a continuation line (the absolute count moves with the corpus; an earlier version of this comment froze it and went stale twice), so for those the visual end of
    # the entry is a line this regex never reads, which is exactly where a hand would put it.
    # (This comment said 69 of 196 while check_propagation's docstring said 88 of 214 -- one
    # count, two places in this file, neither re-run. Measured 2026-09-06: 88 of 214.)
    ("- **horn1981** `P` — Horn, B.K.P. (1981). *Hill shading.* [not-opened]", True),
    ("- **horn1981** `P` — Horn, B. (1981). *Hill shading.* [background] [not-opened]", True),
]

NOT_OPENED_FIXTURES = [
    ("\u00a73.1 eq. 1, the stream-power form", False),
    ("the topographic index ln(a / tan beta). NOT OPENED \u2014 the journal is paywalled", True),
    ("NO LOCATOR \u2014 not obtained, and deliberately not guessed", True),
    ("no artefact: a convention this repository recommends", False),
    ("Abstract only; the full text was not reached", False),  # weaker, but something WAS read
    ("\u00a73.1. not opened -- the journal is paywalled", True),  # lower case must count too
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
            if any(mark in loc.upper() for mark in LOCATOR_NOT_OPENED):
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
    ebad = []
    for t, want in ENTRY_TAG_FIXTURES:
        m = _ENTRY.match(t)
        if m is None or bool(m["notopened"] or m["notopened_trailing"]) != want:
            ebad.append((t, want))
    for t, want in ebad:
        print(f"  FAIL  entry-tag fixture: {t!r} should parse with not_opened="
              f"{want}")
    ubad = [(t, want) for t, want in NOT_OPENED_FIXTURES
            if any(mark in t.upper() for mark in LOCATOR_NOT_OPENED) != want]
    for t, want in ubad:
        print(f"  FAIL  not-opened fixture: {t!r} should be "
              f"{'COUNTED as unread' if want else 'not counted'}")
    cbad = [(t, want) for t, want in COST_FIXTURES
            if bool(COST_UNIT.search(t)) != want]
    for t, want in cbad:
        print(f"  FAIL  cost fixture: {t!r} should be "
              f"{'COUNTED as priced' if want else 'not counted'}")
    rbad = [(t, want) for t, want in ERROR_FIXTURES
            if bool(ERROR_STATED.search(t)) != want]
    for t, want in rbad:
        print(f"  FAIL  error fixture: {t!r} should be "
              f"{'COUNTED as an error' if want else 'not counted'}")
    pbad = [(t, want) for t, want in PROPAGATION_FIXTURES if section_tokens(t) != want]
    for t, want in pbad:
        print(f"  FAIL  propagation fixture: {t!r} should yield {sorted(want)}, "
              f"got {sorted(section_tokens(t))}")
    xbad = [(t, want) for t, want in CROSSREF_FIXTURES if _x_formula(t) != want]
    for t, want in xbad:
        print(f"  FAIL  crossref fixture: {t!r} should yield {want}, got {_x_formula(t)}")
    xpbad = [(t, want) for t, want in CROSSREF_PATH_FIXTURES if _x_is_path(t) != want]
    for t, want in xpbad:
        print(f"  FAIL  crossref path fixture: {t!r} should be "
              f"{'a PATH' if want else 'a formula'}")
    xrbad = [(t, want) for t, want in CROSSREF_RATIO_FIXTURES if _x_ratios(t) != want]
    for t, want in xrbad:
        print(f"  FAIL  crossref ratio fixture: {t!r} should yield {sorted(want)}, "
              f"got {sorted(_x_ratios(t))}")
    dbad = [(t, want) for t, want in DOC_NAME_FIXTURES
            if bool(_DOC_NAME.match(t)) != want]
    for t, want in dbad:
        print(f"  FAIL  cross-reference fixture: {t!r} should be "
              f"{'a document this corpus must have' if want else 'out of reach'}")
    bbad = [(t, wc, we) for t, wc, we in BUDGET_FIXTURES if _budget_tokens(t) != (wc, we)]
    for t, wc, we in bbad:
        print(f"  FAIL  budget fixture: {t!r} should claim {sorted(wc)} and evidence "
              f"{sorted(we)}, got {[sorted(s) for s in _budget_tokens(t)]}")
    xcbad = crossref_corpus_selftest()
    for msg in xcbad:
        print(f"  FAIL  crossref corpus: {msg}")
    gbad = register_selftest()
    for msg in gbad:
        print(f"  FAIL  execution register: {msg}")
    xbad += xpbad + xrbad
    if bad or nbad or ubad or ebad or cbad or rbad or pbad or xbad or xcbad or gbad \
            or dbad or bbad:
        # `ebad` used to gate the exit code and not appear in this sentence, so a run with
        # only entry-tag failures printed "0 ... 0 ... 0 misclassified" above a non-zero exit.
        print(f"\n{len(bad)} of {len(LOCATOR_FIXTURES)} locator fixtures, "
              f"{len(nbad)} of {len(NO_ARTEFACT_FIXTURES)} no-artefact fixtures, "
              f"{len(ubad)} of {len(NOT_OPENED_FIXTURES)} not-opened fixtures and "
              f"{len(ebad)} of {len(ENTRY_TAG_FIXTURES)} entry-tag fixtures and "
              f"{len(cbad)} of {len(COST_FIXTURES)} cost fixtures and "
              f"{len(rbad)} of {len(ERROR_FIXTURES)} error fixtures and "
              f"{len(pbad)} of {len(PROPAGATION_FIXTURES)} propagation fixtures and "
              f"{len(xbad)} of "
              f"{len(CROSSREF_FIXTURES) + len(CROSSREF_PATH_FIXTURES) + len(CROSSREF_RATIO_FIXTURES)}"
              f" crossref fixtures misclassified, "
              f"{len(dbad)} of {len(DOC_NAME_FIXTURES)} cross-reference fixtures and "
              f"{len(bbad)} of {len(BUDGET_FIXTURES)} budget fixtures misclassified, "
              f"and {len(xcbad)} crossref corpus "
              f"assertion(s) and {len(gbad)} execution-register assertion(s) failed.")
        return 1
    print(f"locator pattern: {len(LOCATOR_FIXTURES)}/{len(LOCATOR_FIXTURES)} fixtures correct; "
          f"no-artefact marker: {len(NO_ARTEFACT_FIXTURES)}/{len(NO_ARTEFACT_FIXTURES)} correct; "
          f"not-opened marker: {len(NOT_OPENED_FIXTURES)}/{len(NOT_OPENED_FIXTURES)} correct; "
          f"entry tag: {len(ENTRY_TAG_FIXTURES)}/{len(ENTRY_TAG_FIXTURES)} correct; "
          f"cost unit: {len(COST_FIXTURES)}/{len(COST_FIXTURES)} correct; "
          f"error: {len(ERROR_FIXTURES)}/{len(ERROR_FIXTURES)} correct; "
          f"propagation: {len(PROPAGATION_FIXTURES)}/{len(PROPAGATION_FIXTURES)} correct; "
          f"crossref: {len(CROSSREF_FIXTURES)}/{len(CROSSREF_FIXTURES)} formula, "
          f"{len(CROSSREF_PATH_FIXTURES)}/{len(CROSSREF_PATH_FIXTURES)} path, "
          f"{len(CROSSREF_RATIO_FIXTURES)}/{len(CROSSREF_RATIO_FIXTURES)} ratio correct; "
          f"cross-reference shape: {len(DOC_NAME_FIXTURES)}/{len(DOC_NAME_FIXTURES)} correct; "
          f"budget vocabulary: {len(BUDGET_FIXTURES)}/{len(BUDGET_FIXTURES)} correct, including "
          f"the four cases that decide the `runtime` asymmetry; and "
          f"check_crossrefs() itself reports {len(CROSSREF_CORPUS_EXPECTED)}/"
          f"{len(CROSSREF_CORPUS_EXPECTED)} reconstructed instances on the fixture corpus and "
          f"nothing once they are corrected; the execution-register check reports "
          f"{len(PSEUDOCODE_FIXTURE_EXPECTED)}/{len(PSEUDOCODE_FIXTURE_EXPECTED)} malformed rows "
          f"plus the dropped column name, and nothing once they are repaired.")
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


# A number bound to a unit that can only mean MACHINE COST. Wall-clock prose is deliberately
# absent: "about 2 minutes" and "1.3 hours" are indistinguishable by pattern from a physical
# timescale, and coastal-erosion.md's "1.3 hours" is a shoreline e-folding time, not a bake. So
# this UNDER-counts, which is the safe direction for a number that is supposed to go up, and a
# document that wants credit has to state the cost precisely enough to be actionable anyway.
COST_UNIT = re.compile(r"(?<![\w.])\d[\d.,]*\s*(?:ms|\u00b5s|us|MB|GB|KB|TB|MiB|GiB|KiB|fps|FPS)\b"
                       r"|bytes?\s*(?:per|/)\s*cell", re.I)

# The other half of the engineer's question. Deliberately NOT matching a bare "N% of": that
# catches "70% of the variance" and every other proportion in the corpus, and a metric that
# counts prose about percentages is not measuring error at all.
ERROR_STATED = re.compile(r"(?:\u00b1|\+/-)\s?\d[\d.]*"
                          r"|\bwithin\s+\d[\d.]*\s?%"
                          r"|\d[\d.]*\s?%\s+(?:error|too\s+\w+|low|high|off|out)"
                          r"|\berror\s+(?:of|is|was)\s+[-+]?\d[\d.]*"
                          r"|\b(?:max(?:imum)?|mean|rms|peak)\s+(?:relative\s+)?error\b"
                          r"|\b(?:RMSE|MAE|RMS error|L2 error)\b[^.\n]{0,60}?\d"
                          r"|\d[^.\n]{0,60}?\b(?:RMSE|MAE|RMS error|L2 error)\b", re.I)

ERROR_FIXTURES = [
    ("the max relative error is 14.32% at 78.89 deg", True),
    ("T = (0.14 \u00b1 0.062) R^0.77", True),
    ("within 30% where R < 5 km", True),
    ("runs 22% low at the Brewster angle", True),
    ("an RMSE of 11.3 against the measurements", True),        # an error in physical units, not a percentage
    ("we did not compute an RMSE for this", False),      # a negation, not a measurement
    ("MAE", False),                                      # a bare acronym with no number
    ("giving near-constant relative error across the range", False),  # qualitative, not a figure
    ("about 70% of the variance is explained", False),   # a proportion, not an error
    ("39.18% coverage, 25676 set cells", False),
    ("it is a good approximation", False),
]

COST_FIXTURES = [
    ("the bake is 104 ms at 4k", True),
    ("32 MB per resident tile", True),
    ("4 bytes per cell, so 1.3 GB", True),
    ("holds 20 fps on the preview", True),
    ("if the composite below is too expensive per frame", False),  # the false positive that made
    ("synthesise triangles per frame from a heightfield", False),  # this metric read 10/36 when
    ("choose a budget tier and stick to it", False),               # the honest answer was 4/36
    ("about 2 minutes at 16 azimuths", False),      # wall clock: not a machine unit
    ("an e-folding time of 1.3 hours", False),      # physical, and the reason minutes/hours are out
    ("a 512 preview against a 4k build", False),    # resolutions are not costs
    ("the timestep limit is 0.5", False),
    ("wind at 0.28 m s-1", False),
    ("it is fast in practice", False),
]


def approximation_coverage() -> tuple[int, int, int, int]:
    """Can a reader tell how good the recommendation is AND what it costs?

    This skill's audience builds a game engine or an authoring tool, and the question they
    actually bring is not "what is true" but **"how well can I approximate this inside a frame
    budget"**. That question has two halves and needs both in the same document: the error the
    approximation carries, and the cost it incurs. Either alone is unactionable -- an error
    bound with no cost cannot be budgeted, a cost with no error cannot be justified.

    Measured honestly: **4 of 36 documents state both**. 10 say how good and not what it costs;
    4 say what it costs and not how good; 18 say neither.

    It read 10/36 for half a day, and that was this metric committing the defect it exists to
    detect. `COST_UNIT` matched the bare phrases "per frame", "budget tier" and "offline bake", so
    six documents scored on sentences that are not costs at all -- one of them on "if the composite
    below is too expensive per frame", a sentence whose whole point is that the cost is UNKNOWN.
    The error side was equally loose: "we did not compute an RMSE" matched. Both patterns now
    require a NUMBER, and the fixtures pin exactly those cases.

    An earlier version counted cost alone, which measured the wrong unit: cost is half of a pair.

    REPORTED, not enforced, like `locators`. An OPEN row in registers/guard-proofs.tsv.

    What it cannot see: it counts UNITS, not claims. It cannot tell a measured error from a
    quoted one, cannot tell whether the cost and the error describe the same technique, and
    cannot see an error stated in cells or an asymptotic cost stated in O-notation. It is a
    floor on how many documents put both halves in front of the reader at all.
    """
    docs = content_documents()
    both = err = cost = neither = 0
    for d in docs:
        try:
            _, body = parse_front_matter(d)
        except (OSError, Unparseable):
            continue
        e, c = bool(ERROR_STATED.search(body)), bool(COST_UNIT.search(body))
        if e and c:
            both += 1
        elif e:
            err += 1
        elif c:
            cost += 1
        else:
            neither += 1
    return both, err, cost, neither


# Words that carry no subject matter, so a section whose heading is only these has nothing
# distinctive to look for downstream. Kept deliberately short: the check's job is to find
# sections with NO reachable subject, and a long stop list would manufacture that condition.
_REACH_STOP = {
    "the", "and", "for", "with", "what", "which", "that", "this", "from", "into", "your",
    "you", "are", "not", "but", "how", "why", "when", "where", "who", "does", "actually",
    "here", "there", "them", "they", "its", "it's", "one", "two", "three", "each", "every",
    "any", "all", "own", "why", "use", "using", "used", "make", "makes", "made", "gets",
    "get", "put", "puts", "than", "then", "also", "more", "most", "less", "least", "same",
    "different", "other", "another", "about", "over", "under", "after", "before", "way",
    "ways", "thing", "things", "part", "parts", "side", "sides", "enough", "still", "just",
}

# Hyphen is a SEPARATOR, not a word character. Keeping it inside the token made
# "The three-media rule" read as unreachable from a failure row that says "Three media
# attenuating the same path" -- the row covers the section exactly, in two words instead of
# one. That was a false positive in a check whose whole output is candidate false positives,
# and splitting on it removed two of twenty-one.
# A bare number is a content word here. "The 42 degree switch, where smoothing becomes
# roughening" read as unreachable while `## Use this` and three failure rows all named 42
# degrees -- the distinctive term in that heading is the NUMBER, and requiring a leading
# letter threw it away. Removed one more false positive, 19 -> 18.
_REACH_WORD = re.compile(r"[a-z][a-z0-9']{2,}|[0-9]{2,}")


def _reach_terms(heading: str) -> set[str]:
    """Content words of a section heading, singular and plural collapsed."""
    out = set()
    for w in _REACH_WORD.findall(heading.lower()):
        if w in _REACH_STOP:
            continue
        out.add(w)
        if w.endswith("s") and len(w) > 4:
            out.add(w[:-1])          # classes -> classe, angles -> angle
        else:
            out.add(w + "s")
    return out


def _is_anchor(heading_lower: str) -> bool:
    """The two headings a reader lands on first.

    The failure table is `## How this fails, and what it looks like` in 35 documents and
    `## When it fails` in two. Matching a bare "fails" anywhere would also swallow content
    sections -- "The priority function, and why FIFO fails" is a section ABOUT a failure, not
    the table -- so the two spellings are named rather than pattern-matched.
    """
    return (heading_lower.startswith("use this")
            or heading_lower.startswith("how this fails")
            or heading_lower.startswith("when it fails"))


def check_section_reach() -> tuple[list[str], int, int]:
    """Does every major section reach `## Use this` or the failure table?

    This corpus is read in two places first: the recommendation at the top and the failure
    table at the bottom. A section reachable from neither is invisible to the reader it was
    written for, however good it is.

    WHY THIS EXISTS. The shape was found BY HAND in five consecutive documents, and it is the
    corpus's most-recorded process defect: a correction lands in the prose and not at the two
    ends a reader actually uses. The largest instance was hydraulic-erosion.md, where the grain
    classes section -- about 31% of the body, carrying armouring, downstream fining, per-class
    capacity and per-class repose -- appeared in neither. Finding that by hand five times and
    not mechanising it is the definition of a discipline that does not hold.

    HOW IT DECIDES. For each `## ` section other than `## Use this` and the failure table, it
    takes the content words of the heading and asks whether ANY of them appears in the union of
    those two. One word is enough to pass.

    ⚠️ IT DOES NOT CATCH THE CASE IT WAS BUILT FOR, AND THAT IS MEASURED, NOT SUSPECTED.
    Run against hydraulic-erosion.md at 634ca6f -- the version whose grain-classes section
    reached neither end -- it reports NOTHING. The heading is "Grain classes: one capacity, one
    talus angle, and why that is not enough", and the words `capacity` and `angle` both appear in
    that document's failure table already, in rows belonging to the PIPE section. Weighting by
    corpus-wide rarity does not help: `capacity` is rare across the corpus and still present in
    this document's table. Lexical overlap cannot separate "the table covers this section" from
    "the table happens to use this word elsewhere", because the distinction is semantic. A
    stronger word rule would not fix it; a different instrument would be needed.

    SO WHAT IT IS FOR. It catches the strictly weaker condition it can actually see: a section
    with NO lexical contact with either end at all -- 18 of 193 sections.

    ⚠️ THE FIRST TWO EXAMPLES THIS DOCSTRING CITED AS REAL WERE BOTH FALSE POSITIVES, and
    fixing them is why the count fell from 21. "The three-media rule" is covered by a failure
    row reading "Three media attenuating the same path" -- the hyphen made one token where the
    row has two. "The 42 degree switch" is named in `## Use this` and three failure rows -- the
    distinctive term there is a NUMBER, and the pattern required a leading letter. Both are now
    tokenised correctly. The lesson is that this instrument's output is CANDIDATES, and the two
    the author reached for first as evidence it worked were both wrong.

    What remains is mostly generic navigational headings with no subject matter to match at all
    ("Submission", "The ladder", "Where this sits in the pipeline", "The handoff"), for which a
    failure row would be meaningless. A net with a known hole and a known false-positive rate,
    reported as such. It does not discharge the hand review.

    REPORTED, not enforced. An OPEN row in registers/guard-proofs.tsv records the negative
    result above so nobody rebuilds this and believes it works.
    """
    problems: list[str] = []
    docs = content_documents()
    unreachable = total = 0
    for d in docs:
        try:
            _, body = parse_front_matter(d)
        except (OSError, Unparseable):
            continue
        text = _unfenced(body)
        parts = re.split(r"^## +(.+?)\s*$", text, flags=re.M)
        if len(parts) < 3:
            continue
        heads = parts[1::2]
        bodies = parts[2::2]
        anchor = []
        for h, b in zip(heads, bodies):
            hl = h.lower()
            if _is_anchor(hl):
                anchor.append(h + " " + b)
        if not anchor:
            continue
        anchor_text = " ".join(anchor).lower()
        for h in heads:
            hl = h.lower()
            if _is_anchor(hl):
                continue
            total += 1
            terms = _reach_terms(h)
            if terms and not any(t in anchor_text for t in terms):
                unreachable += 1
                problems.append(
                    f"  ....  {d.relative_to(ROOT)}: section '{h}' reaches neither "
                    f"`## Use this` nor the failure table")
    return problems, unreachable, total


# ── check_crossrefs: does a value agree at both ends of a link? ───────────────────────────────
# Superscripts and `N × 10^M` are folded into ordinary floats BEFORE anything is compared. This
# is not cosmetic. `U = 5×10⁻⁴ m/yr` and `U = 0.0005 m/yr` are the same measurement written two
# ways, and without the fold the guard read them as {5, 10} against {0.0005} and reported three
# corpus-wide disagreements that were all the same number. Folding removed all three.
_SUPS = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻"
_SUP_MAP = str.maketrans(_SUPS, "0123456789+-")
_SUP_RUN = re.compile(f"[{_SUPS}]+")
_SCI = re.compile(r"(?<![A-Za-z0-9_.])(\d+(?:\.\d+)?)\s*\*\s*10\^(-?\d+)")
# A number, exponent included. `1.2e-7` must be ONE token: reading it as `1.2` + an identifier
# `e` + `7` invented a shared key `e|x` and reported planetary-precision.md against
# shader-craft.md for two unrelated ULP figures.
_XNUM = re.compile(r"(?<![A-Za-z0-9_.])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
_XIDENT = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*")
_XSPAN = re.compile(r"`([^`\n]+)`")
_XSYM = r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)?"
_XRATIO = re.compile(rf"^({_XSYM})\s*/\s*({_XSYM})$")
# The same ratio with the slash OUTSIDE the code spans -- water-optics.md writes `c`/`K_d`.
_XSPLIT_RATIO = re.compile(rf"`({_XSYM})`\s*/\s*`({_XSYM})`")
# `c` typically runs 5–20× `K_d`  -- a multiplier magnitude standing between two named symbols.
_XMULT = re.compile(rf"`(?P<s1>{_XSYM})`[^`]{{0,80}}?"
                    r"\d+(?:\.\d+)?(?:\s*[–—-]\s*\d+(?:\.\d+)?)?\s*[×x]"
                    rf"[^`]{{0,80}}?`(?P<s2>{_XSYM})`")
_XPATHY = re.compile(r"://|\.(?:md|py|tsv|cs|json|glsl|hlsl)\b")
_XSLUG = re.compile(r"[\w.-]+(?:/[\w.-]+)+")
_XFAILS = re.compile(r"^## +(?:How this fails|When it fails).*$", re.M)
_XOPS = "*/+^"


def _x_norm(s: str) -> str:
    """One spelling of arithmetic, so `·`, `×`, `⁻⁴` and `5×10⁻⁴` compare with `*`, `^-4`, `0.0005`."""
    for a, b in (("·", "*"), ("×", "*"), ("−", "-"),
                 ("≈", "="), ("≃", "=")):
        s = s.replace(a, b)
    s = _SUP_RUN.sub(lambda m: "^" + m.group(0).translate(_SUP_MAP), s)

    def fold(m: re.Match) -> str:
        try:
            return repr(float(m.group(1)) * 10 ** int(m.group(2)))
        except (OverflowError, ValueError):
            return m.group(0)      # `10^400` overflows a float; leave it as written
    return _SCI.sub(fold, s)


def _x_is_path(span: str) -> bool:
    """A file path or a branch name is not a formula, even though `/` is an operator.

    The first version of this test was `[a-z]/[a-z]` anywhere in the span, which also ate
    `dt <= 0.50·dx/sqrt(g·A/l)` -- a real formula -- and with it the 0.50 that the shallow-water
    failure row is checked against. A path is now required to be path-SHAPED: no spaces, no
    brackets, and either an extension, a scheme, two separators, or a hyphen or dot inside.
    """
    if _XPATHY.search(span):
        return True
    return ("/" in span and _XSLUG.fullmatch(span) is not None
            and ("-" in span or "." in span or span.count("/") > 1))


def _x_formula(span: str) -> tuple[str, tuple[float, ...]] | None:
    """A code span -> (identifier-set key, the numeric constants it prints), or None.

    The KEY is the set of identifiers, not the expression's shape, so `sqrt(2·g·A/l)` and
    `sqrt(g·A/l)` land on the same key and their constants can be compared. Two identifiers and
    one operator are required: a bare symbol names a quantity rather than asserting a value.
    """
    s = _x_norm(span)
    if not any(c in _XOPS for c in s):
        return None
    vals = tuple(sorted({float(n) for n in _XNUM.findall(s)}))
    ids = sorted(set(_XIDENT.findall(_XNUM.sub(" ", s))))
    if len(ids) < 2:
        return None
    return "|".join(ids), vals


def _x_ratios(block: str) -> set[str]:
    """Ratio keys a block claims a magnitude for: `c/K_d`, or "`c` runs 5–20× `K_d`"."""
    out: set[str] = set()
    for m in _XSPAN.finditer(block):
        r = _XRATIO.match(m.group(1).strip())
        if r:
            out.add(f"{r.group(1)}/{r.group(2)}")
    if block.startswith("```"):
        for m in re.finditer(rf"(?<![A-Za-z0-9_/])({_XSYM})\s*/\s*({_XSYM})(?![A-Za-z0-9_/])",
                             block):
            out.add(f"{m.group(1)}/{m.group(2)}")
    for m in _XSPLIT_RATIO.finditer(block):
        out.add(f"{m.group(1)}/{m.group(2)}")
    for m in _XMULT.finditer(block):
        out.add(f"{m['s1']}/{m['s2']}")
    return out


def _x_blocks(text: str, base: int = 1) -> list[tuple[int, str]]:
    """(first line, text) per paragraph, fenced block, table row, or `- **id**` entry.

    A table ROW and a bibliography ENTRY are their own blocks. Lumping the failure table into one
    paragraph, or a bibliography into one list, pools every number in it -- and pooling is what
    let the whole of papers-simulation.md's number set stand in for one entry's, which hid the
    `iop_split` disagreement this guard exists to find.
    """
    out: list[tuple[int, str]] = []
    buf: list[str] = []
    start, fence = base, False
    for i, line in enumerate(text.split("\n"), base):
        if line.startswith("```"):
            if not fence and buf:
                out.append((start, "\n".join(buf)))
                buf = []
            fence = not fence
            if fence:
                start = i
            buf.append(line)
            if not fence:
                out.append((start, "\n".join(buf)))
                buf = []
            continue
        if fence:
            buf.append(line)
            continue
        if line.startswith("|") or line.startswith("- **"):
            if buf:
                out.append((start, "\n".join(buf)))
                buf = []
            out.append((i, line))
            continue
        if not line.strip():
            if buf:
                out.append((start, "\n".join(buf)))
                buf = []
            continue
        if not buf:
            start = i
        buf.append(line)
    if buf:
        out.append((start, "\n".join(buf)))
    return out


def _x_side(text: str, base: int = 1) -> tuple[dict, dict]:
    """One end of a link, as two key -> (values, first line) tables: formulas and ratios.

    A formula's value is the tuple of constants IN ITS OWN SPAN, and a side holds the SET of
    those tuples -- not their union. The difference is load-bearing. shallow-water.md's body
    prints both `2A/l` and `A/l` in one sentence ("`2A/l`, not `A/l`, is the effective depth"),
    so under a union the body reads {2} against the table's {} and the guard cries wolf. As a set
    of tuples the body holds {(2,), ()}, the table holds {()}, they intersect, and it stays
    quiet. A ratio's value IS a flat set: the magnitude sits in the prose around the symbol, not
    inside it.
    """
    f: dict[str, list] = {}
    r: dict[str, list] = {}
    for ln, block in _x_blocks(text, base):
        clean = _XSPAN.sub(lambda m: " " if _x_is_path(m.group(1)) else m.group(0), block)
        for m in _XSPAN.finditer(clean):
            k = _x_formula(m.group(1).strip())
            if k is None:
                continue
            slot = f.setdefault(k[0], [set(), ln])
            slot[0].add(k[1])
        nums = {float(n) for n in _XNUM.findall(_x_norm(clean))}
        if not nums:
            continue
        for key in _x_ratios(clean):
            slot = r.setdefault(key, [set(), ln])
            slot[0] |= nums
    return f, r


# The two ends of each real instance this guard was built from, plus the normalisations that
# had to exist before they compared at all. `--selftest` asserts every row.
CROSSREF_FIXTURES = [
    ("sqrt(2·g·A/l)", ("A|g|l|sqrt", (2.0,))),      # shallow-water.md's body
    ("sqrt(g·A/l)", ("A|g|l|sqrt", ())),            # its failure table, before the fix
    ("A ≈ h·lx/2", ("A|h|lx", (2.0,))),
    ("A ≈ h·lx", ("A|h|lx", ())),
    ("U = 5×10⁻⁴ m/yr", ("U|m|yr", (0.0005,))),     # folded, so it equals `U = 0.0005 m/yr`
    ("Δt ≤ Δx²/(4D)", ("D|t|x", (2.0, 4.0))),       # a superscript is a constant, not decoration
    ("x · 1.2e-7", None),                           # `e` is an exponent, never an identifier
    ("K_d", None),                                  # a bare symbol names, it does not assert
    ("1/(b − b_b)", ("b|b_b", (1.0,))),             # the clean corpus's one false positive,
    ("b_b = b/2", ("b|b_b", (2.0,))),               # pinned: two formulas, one identifier pair
]
# A path is not a formula. The second row is the span the first version of `_x_is_path` ate.
CROSSREF_PATH_FIXTURES = [
    ("references/papers-flow.md", True),
    ("dt <= 0.50·dx/sqrt(g·A/l)", False),
    ("origin/claude/swimming-pool-voronoi-render-m22g6r", True),
    ("terrain-architect/references/28-liquids.md", True),
    ("c/K_d", False),
    ("b_b/b", False),
]
CROSSREF_RATIO_FIXTURES = [
    ("the observation that `c` typically runs 5–20× `K_d` because natural water "
     "scatters strongly forward", {"c/K_d"}),       # papers-simulation.md's `iop_split`, as it was
    ("A `c`/`K_d` ratio quoted without its `mu_d` is not a number", {"c/K_d"}),
    ("their backscatter ratio `b_b/b` is about 0.018", {"b_b/b"}),
    ("its signal speed is `sqrt(g·A/l)`, fixed by parameters", set()),
]

# A CORPUS, not a span. Four fixture documents and a fixture bibliography carrying two of the
# five real instances this guard was built from, reconstructed in the shape they had on disk:
#   * `fx-tide.md`  -- body `sqrt(2*g*A/l)` against its OWN failure table's `sqrt(g*A/l)`,
#                      which is shallow-water.md at 1816b23^
#   * `papers-fx.md` -- an entry keeping "5–20×" after the document derived 0.75–1.20, which is
#                      papers-simulation.md's `iop_split` at dcc2f65^ (49d1b94^ is the
#                      water-rendering end of the same correction, and had this one already)
# plus a cross-document positive (`A = h*lx/3` against `A = h*lx/2`) and FOUR negative controls
# that must stay quiet: a bare `sqrt(g*A/l)` mentioned in another document with no constant of
# its own; every value once corrected; `fx-basin.md`, which is quiet only because of the
# union-overlap escape (see CROSSREF_CORPUS_QUIET); and the FENCED entry in papers-fx.md, which
# is quiet only because the entry scan skips fences. The last two exist because each guards a
# decision in check_crossrefs that nothing else here can see: removing either leaves all three
# extractor suites and all three positive pins green.
# This exists because `--selftest` asserted only the three EXTRACTORS: gutting check_crossrefs()
# to `return [], 0, 0, 0, 0` left it green, and check.py still exited 0 -- an assertion defined
# and never invoked, which is the hole this register already records for check_not_opened and
# for requote's `check()`.
# The fixture entry is one over-long line ON PURPOSE: this guard reads only an entry's OPENER
# line, so a wrapped fixture would test nothing. 41% of the real bibliography wraps.
_FX_FM = "---\ntype: reference\ntitle: {t}\n---\n\n"
CROSSREF_CORPUS = {
    # The front-matter `description` carries a DECOY: `sqrt(7*g*A/l)` shares the body's key but
    # is not body, and `_offset` is the only thing that keeps it out. Hardwiring `_offset` to
    # `return 1` makes the first pin below read `fx-tide.md:1 ... constants [2.0, 7.0]` instead
    # of `fx-tide.md:11 ... constants [2.0]`, and it fails. A LINE pin alone could never catch
    # that -- see the note over CROSSREF_CORPUS_EXPECTED -- so the pinned CONSTANTS do it.
    # It is also the guard's stated limit made testable: front matter is not read, which is why
    # heightfield-raymarching.md's front-matter locator is one of the three instances it misses.
    "fx-tide.md": "---\ntype: reference\ntitle: Fixture -- the constant-A pipe form\n"
    "description: A fixture. Front matter is not body: `sqrt(7*g*A/l)` must never be read.\n"
    "---\n\n" + """\
# Fixture: the constant-`A` pipe form

## Use this

The pipe form's own signal speed is `sqrt(2*g*A/l)`, and with `A` and `l` held constant it does
not move with depth at all. The cross-section one cell offers a face is `A = h*lx/2`.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Reducing `dt` by the deepest cell changes nothing | its signal speed is `sqrt(g*A/l)` | Bound on `sqrt(g*A/l)` |
""",
    "fx-other.md": _FX_FM.format(t="Fixture -- the same section from another document") + """\
# Fixture: the same cross-section, quoted from another document

`fx-tide.md` derives the constant-`A` pipe form. The cross-section used here is `A = h*lx/3`,
and the signal speed it quotes, `sqrt(g*A/l)`, is repeated with no constant of its own.
""",
    "fx-basin.md": _FX_FM.format(t="Fixture -- a formula, then the same formula evaluated")
    + """\
# Fixture: a formula stated, then the same formula with its value

## Use this

Compactness of a cell footprint is the isoperimetric ratio `4*Aw/P^2`, which is 1 for a disc and
falls as the outline gets ragged. Its mean depth is `h = V/Aw`.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Footprints read as ragged | Boundary noise applied after the partition | `4*Aw/P^2 = 0.817`, so they are compact |
| Depth is read off the bounding box | The footprint is not its box | `h = V/Aw`, over the wetted area |
""",
    "fx-optics.md": _FX_FM.format(t="Fixture -- the two attenuation coefficients") + """\
# Fixture: beam and diffuse attenuation

Beam attenuation `c` and diffuse attenuation `K_d` are not interchangeable [fx_split]. In pure
water the ratio between them runs:

```
mu_d    c/K_d at 450 / 500 nm
1.00    1.20 / 1.07
0.75    0.90 / 0.80
```
""",
    "papers-fx.md": _FX_FM.format(t="Fixture bibliography") + """\
# Fixture bibliography

- **fx_split** `F` — No single canonical source. The split between beam attenuation `c` and diffuse attenuation `K_d`, and the observation that `c` typically runs 5–20× `K_d` because natural water scatters strongly forward. [no-artefact]

An entry looks like this:

```
- **fx_split** `F` — the ratio `c`/`K_d` here runs 900–999× for illustration only.
```
""",
}
# The same corpus with both corrections landed at BOTH ends. Overlaid on the dict above.
CROSSREF_CORPUS_FIXED = {
    "fx-tide.md": CROSSREF_CORPUS["fx-tide.md"].replace(
        "| its signal speed is `sqrt(g*A/l)` | Bound on `sqrt(g*A/l)` |",
        "| its signal speed is `sqrt(2*g*A/l)` | Bound on `sqrt(2*g*A/l)` |"),
    "fx-other.md": CROSSREF_CORPUS["fx-other.md"].replace("`A = h*lx/3`", "`A = h*lx/2`"),
    "papers-fx.md": CROSSREF_CORPUS["papers-fx.md"].replace(
        "the observation that `c` typically runs 5–20× `K_d` because natural water scatters "
        "strongly forward",
        "a `c`/`K_d` ratio of 0.75–1.20 in pure water, which crosses one"),
}
# The two `fx-basin.md` shared keys, which must appear in NO finding of EITHER corpus. Each is
# held quiet by ONE HALF of `if (va & vb) or (ua & ub)` in check_crossrefs and by nothing else,
# and that line is the tuning decision holding the corpus-wide count at 1. Both halves were
# unasserted until these controls existed: either could be deleted with the whole fixture green.
#   * `Aw|P` -- `4*Aw/P^2` in the body against `4*Aw/P^2 = 0.817` in the failure row, a formula
#     stated against the SAME formula with its evaluated value. That is sea-ice.md:206 against
#     sea-ice.md:356, and it is the commonest quiet shape in the corpus. The tuple sets are
#     DISJOINT ({(2.0, 4.0)} against {(0.817, 2.0, 4.0)}); only the flattened unions overlap, so
#     `or (ua & ub)` alone keeps it quiet. Dropping that half: real tree 1 finding -> 7.
#   * `Aw|V|h` -- `h = V/Aw` at both ends, neither printing a constant. Both tuple sets are
#     {()}, so they intersect while the unions are EMPTY and cannot: `va & vb` alone keeps it
#     quiet. Dropping that half: real tree 1 finding -> 34. Within one document a missing
#     constant is a finding by design, which is what makes this pair worth pinning.
CROSSREF_CORPUS_QUIET = ("`Aw`, `P`", "`Aw`, `V`, `h`")
# Each entry is the set of substrings ONE finding must contain, pinned to the LINE and to the
# CONSTANTS, and the two pins assert different things.
# The LINE asserts the BLOCK-START attribution: replacing `head = base + body[:cut].count("\n")`
# with `head = base` moves the second end of the first pin from `fx-tide.md:18` to `:9`.
# The LINE CANNOT assert `_offset`, and no line pin anywhere ever could: the body is sliced at
# `base` and then numbered from that same `base`, so the two cancel exactly, and hardwiring
# `_offset` to `return 1` (17 -> 1 on shallow-water.md) leaves every line number here and every
# number the real corpus reports unchanged. What `_offset` decides is which lines are SCANNED,
# not what they are called -- so it is the CONSTANTS that pin it, against the decoy planted in
# fx-tide.md's front matter above.
# The corrected corpus must produce none of them and no others: both counts are asserted.
CROSSREF_CORPUS_EXPECTED = [
    # the shallow-water shape: one document against its own failure table, factor dropped
    ("references/fx-tide.md:11 and references/fx-tide.md:18", "`A`, `g`, `l`, `sqrt`",
     "constants [2.0] at the first and none at the second"),
    # the cross-document shape: a document against one it names in prose
    ("references/fx-other.md:8 and references/fx-tide.md:11", "`A`, `h`, `lx`",
     "constants [3.0] at the first and [2.0] at the second"),
    # the iop_split shape: a document against the bibliography entry it cites
    ("references/fx-optics.md:11 and references/papers-fx.md:8", "ratio `c/K_d`",
     "against [5.0, 20.0]"),
]


def _crossref_corpus_run(files: dict[str, str]) -> list[str]:
    """Write a fixture corpus to a temporary tree and return what check_crossrefs() says of it.

    The tree is temporary on purpose: a fixture corpus living under `references/` would be read
    by every other check in this file and would have to be a real document to pass them.
    """
    with tempfile.TemporaryDirectory() as tmp:
        refs = Path(tmp) / "references"
        refs.mkdir()
        for name, text in files.items():
            (refs / name).write_text(text, encoding="utf-8")
        return check_crossrefs(Path(tmp))[0]


def crossref_corpus_selftest() -> list[str]:
    """Assert check_crossrefs() itself -- not only its extractors -- on the reconstructed corpus."""
    bad: list[str] = []
    broken = _crossref_corpus_run(CROSSREF_CORPUS)
    for want in CROSSREF_CORPUS_EXPECTED:
        if not any(all(s in p for s in want) for p in broken):
            bad.append("no finding matches the reconstructed instance "
                       + " + ".join(repr(s) for s in want))
    if len(broken) != len(CROSSREF_CORPUS_EXPECTED):
        bad.append(f"{len(broken)} findings on the broken fixture corpus, expected "
                   f"{len(CROSSREF_CORPUS_EXPECTED)}: {broken}")
    for p in broken:
        # Named, not left to the count above, so the failure says WHICH decision was removed.
        for k in CROSSREF_CORPUS_QUIET:
            if k in p:
                bad.append(f"the quiet control over {k} is REPORTED, so one half of "
                           f"`if (va & vb) or (ua & ub)` in check_crossrefs is gone: " + p.strip())
    quiet = _crossref_corpus_run({**CROSSREF_CORPUS, **CROSSREF_CORPUS_FIXED})
    if quiet:
        bad.append(f"the corrected fixture corpus is not quiet: {quiet}")
    return bad


def check_crossrefs(root: Path | None = None) -> tuple[list[str], int, int, int, int]:
    """Does a NUMBER agree at both ends of a link this corpus already draws?

    WHY THIS EXISTS. A correction landing at one end only is this corpus's most-recorded defect;
    it has been found BY HAND five times in two days. Every instance is the same shape -- one
    site is rewritten and a second site that prints the same quantity is not:
      * shallow-water.md's body said `sqrt(2·g·A/l)` while its own failure table said `sqrt(g·A/l)`
      * papers-simulation.md's `iop_split` entry kept the "5–20×" that water-optics.md replaced
      * water-rendering.md printed `exp(-K_d*z)` after water-optics.md derived `exp(-(K_d+c/mu_v)*z)`
      * mask-to-material.md retracted a claim at :217 and restated it at :169
      * heightfield-raymarching.md's front-matter locator still credited Dummer after the body moved
    `check_propagation` already ties the two ends of a citation on WHICH SECTION. This ties two
    ends on WHAT NUMBER.

    HOW IT DECIDES. Both ends must be linked already, by one of three relations the corpus
    writes for itself: a document's body against its own failure table; a document against
    another it NAMES in prose (`water-optics.md`); a document against the BIBLIOGRAPHY ENTRY it
    cites (`[iop_split]`). On each end it extracts *keyed magnitudes* -- a formula keyed by its
    identifier set and valued by the constants in the span, and a ratio (`c/K_d`, or "`c` runs
    5–20× `K_d`") valued by the numbers printed around it. A key present at both ends whose
    values neither match nor overlap is reported. Across two documents both ends must actually
    print a constant; within one document a MISSING constant counts, because a failure row
    restates the body's own quantity and dropping the factor there is the shallow-water defect
    exactly.

    ⚠️ IT DOES NOT CATCH THREE OF THE FIVE INSTANCES ABOVE, AND ONE MISS IS MEASURED, NOT
    SUSPECTED. Reconstruct water-rendering.md at 49d1b94^ -- `exp(-K_d * verticalDepth)` where
    water-optics.md derives `exp(-(K_d + c/mu_v) * verticalDepth)` -- and this check reports
    NOTHING. The correction added a TERM, so the identifier set changed from
    `{exp, K_d, verticalDepth}` to `{exp, K_d, c, mu_v, verticalDepth}`, the two ends no longer
    share a key, and nothing is ever compared. The instrument sees a constant that moved; a
    correction that renames, rewords, adds or drops a term is invisible to it. mask-to-material's
    retraction (prose, no number) and heightfield-raymarching's locator (an attribution, and in
    front matter, which this does not read) are outside its reach for the same reason.

    ⚠️ AND ITS REACH IS THE POINT. Measured 2026-09-06 on a 39-document tree: only 103 of 1101
    linked side-pairs share a single keyed magnitude at all. For the other 91% there is nothing
    to compare and a green line here says nothing whatever about them. The two numbers move with
    the corpus; the run prints the current pair, and the ratio is what to read.

    ⚠️ IT HAS FALSE POSITIVES, AND THE ONE ON THE CLEAN CORPUS IS NAMED SO NOBODY HUNTS IT
    TWICE. caustics.md's scattering length `1/(b − b_b)` and water-optics.md's Rayleigh
    backscatter `b_b = b/2` share the identifier pair `{b, b_b}` and print 1 against 2. They are
    two different formulas, not two versions of one, and no lexical rule separates them --
    the same number meaning different things is this instrument's characteristic error.

    ⚠️ AND IT READS ONLY THE OPENER LINE OF A BIBLIOGRAPHY ENTRY. 92 of the 225 entries (41%,
    measured 2026-09-06) wrap onto a continuation line, and for those the whole of the
    continuation -- which is where a long entry does most of its arguing -- is not compared at
    all. That is the same blind spot the `[not-opened]` tag was once lost in.

    REPORTED, not enforced, like approximation / reach / locators / unread. Its output is
    CANDIDATES for a human, it does not discharge the hand review, and an OPEN row in
    registers/guard-proofs.tsv records the measured miss above.

    `root` exists so `--selftest` can run this FUNCTION over the reconstructed fixture corpus
    rather than only its extractors; see CROSSREF_CORPUS.
    """
    root = ROOT if root is None else root
    refs = root / "references"
    docs = [p for p in documents(root) if p not in (refs / "index.md", refs / "coverage.md")]
    papers = {p for p in refs.glob(PAPERS_GLOB)}
    techs = [p for p in docs if p not in papers]
    names = {p.name for p in techs}

    sides: dict[str, tuple[dict, dict, str]] = {}
    for d in techs:
        try:
            text = d.read_text(encoding="utf-8")
        except OSError:
            continue
        base = _offset(d)
        body = "\n".join(text.split("\n")[base - 1:])
        m = _XFAILS.search(body)
        cut = m.start() if m else len(body)
        head = base + body[:cut].count("\n")
        sides[f"{d.name}#body"] = _x_side(body[:cut], base) + (d.name,)
        sides[f"{d.name}#fails"] = _x_side(body[cut:], head) + (d.name,)
    entry_side: dict[str, str] = {}
    for p in sorted(papers):
        try:
            lines = p.read_text(encoding="utf-8").split("\n")
        except OSError:
            continue
        off, fence = _offset(p), False
        for i, line in enumerate(lines[off - 1:], off):
            # Skip fenced blocks, as `_scan` already does: papers-flow.md and
            # papers-generation.md document the ENTRY FORMAT inside a fence, and one of those
            # illustrations is a copy of a real entry (`beven1979`). Without this the example is
            # registered as a side under the real id, and which of the two a citation is
            # compared against is decided by filename order -- papers-flow sorts before
            # papers-masks-and-filtering, so today the real entry happens to win. Luck is not a
            # rule. Three phantom sides on the current tree; no reported number moves.
            if line.lstrip().startswith("```"):
                fence = not fence
                continue
            if not fence and _ID_OPENER.match(line):
                cid = line.split("**")[1]
                sides[f"{p.name}#{cid}"] = _x_side(line, i) + (p.name,)
                entry_side[cid] = f"{p.name}#{cid}"

    pairs: set[tuple[str, str]] = set()
    for d in techs:
        try:
            text = d.read_text(encoding="utf-8")
        except OSError:
            continue
        pairs.add((f"{d.name}#body", f"{d.name}#fails"))
        for m in re.finditer(r"([a-z0-9][a-z0-9-]*\.md)", text):
            other = m.group(1)
            if other in names and other != d.name:
                for h in ("body", "fails"):
                    for g in ("body", "fails"):
                        pairs.add(tuple(sorted((f"{d.name}#{g}", f"{other}#{h}"))))
        for m in _MARKER.finditer(text):
            if m.group("id") in entry_side:
                for g in ("body", "fails"):
                    pairs.add(tuple(sorted((f"{d.name}#{g}", entry_side[m.group("id")]))))

    problems: list[str] = []
    seen: set[tuple] = set()
    compared = reach = 0
    for a, b in sorted(pairs):
        if a not in sides or b not in sides:
            continue
        fa, ra, na = sides[a]
        fb, rb, nb = sides[b]
        shared_f = sorted(set(fa) & set(fb))
        shared_r = sorted(set(ra) & set(rb))
        compared += len(shared_f) + len(shared_r)
        reach += 1 if (shared_f or shared_r) else 0
        for k in shared_f:
            va, vb = fa[k][0], fb[k][0]
            ua = {x for tup in va for x in tup}
            ub = {x for tup in vb for x in tup}
            if (va & vb) or (ua & ub):
                continue
            if na != nb and not (ua and ub):
                continue          # a bare mention in another document is normal usage
            if (na, nb, "f", k) in seen:
                continue
            seen.add((na, nb, "f", k))
            problems.append(
                f"  ....  references/{na}:{fa[k][1]} and references/{nb}:{fb[k][1]} both print "
                f"the expression over `{k.replace('|', '`, `')}`, with constants "
                f"{sorted(ua) or 'none'} at the first and {sorted(ub) or 'none'} at the second. "
                f"One end may have been corrected and the other not")
        for k in shared_r:
            va, vb = ra[k][0], rb[k][0]
            if va & vb or (na, nb, "r", k) in seen:
                continue
            seen.add((na, nb, "r", k))
            problems.append(
                f"  ....  references/{na}:{ra[k][1]} and references/{nb}:{rb[k][1]} give the "
                f"ratio `{k}` magnitudes that do not overlap: {sorted(va)[:6]} against "
                f"{sorted(vb)[:6]}. One end may have been corrected and the other not")
    return problems, len(problems), compared, reach, len(pairs)


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


def citations_by_id() -> dict[str, list[tuple[Path, str]]]:
    """id -> [(document, locator)], built by walking every document ONCE.

    check_no_artefact used to re-walk and re-parse the whole corpus once per tagged entry --
    7 entries x 34 documents was ~238 redundant parses of the same front matter, and adding a
    second bidirectional check would have doubled it. One pass, shared.
    """
    out: dict[str, list[tuple[Path, str]]] = {}
    skip = set(paper_files()) | {INDEX, COVERAGE}
    for path in documents(ROOT):
        if path in skip:
            continue
        try:
            fm, _ = parse_front_matter(path)
        except Unparseable:
            continue
        for s in fm.get("sources", []):
            if isinstance(s, dict) and s.get("id"):
                out.setdefault(s["id"], []).append((path, str(s.get("locator", ""))))
    return out


def check_not_opened(bib: dict[str, dict], cites: dict[str, list[tuple[Path, str]]]) -> list[str]:
    """The bibliography's grade and the document's locator must agree about whether it was READ.

    `papers-flow.md` defines `P` as "Peer-reviewed, AND verified to actually contain the algorithm
    attributed to it", and says again below the table that `P` asserts a human read the paper and
    found the algorithm in it. Eighteen `P` entries nevertheless declared, in their own prose,
    that the artefact was never obtained -- while the documents citing them had already started
    writing `NOT OPENED --` into their locators. The two halves of the same citation contradicted
    each other, and nothing could see it, because one half was prose and the other was prose.

    `[not-opened]` makes the bibliography's half structural, and this check ties the halves
    together in BOTH directions:

      - an entry tagged [not-opened] must not be cited with a locator that claims a reading;
      - a locator saying NOT OPENED must sit against an entry that admits it.

    It is deliberately NOT a failure to have unread sources. A corpus that cannot cite a paywalled
    paper is less useful, not more honest. What is a failure is claiming, on one side of a
    citation, something the other side denies.
    """
    problems: list[str] = []
    for sid, entry in sorted(bib.items()):
        tagged = entry["not_opened"]
        for path, loc in cites.get(sid, []):
            declares = any(mark in loc.upper() for mark in LOCATOR_NOT_OPENED)
            rel = path.relative_to(ROOT)
            if tagged and not declares:
                problems.append(
                    f"{rel}: cites `{sid}`, whose entry in {entry['file']} is tagged "
                    f"[not-opened], with a locator that does not say so. Either the source was "
                    f"opened after all and the tag is stale, or this locator is claiming a "
                    f"reading nobody did")
            elif declares and not tagged:
                problems.append(
                    f"{rel}: cites `{sid}` with a locator declaring NOT OPENED, but its entry in "
                    f"{entry['file']} is not tagged [not-opened]. A tier that says a human read "
                    f"the paper, beside a locator that says nobody did, is the contradiction this "
                    f"tag exists to close")
    return problems


AXIS_TAGS = ("generation", "simulation", "rendering", "architecture")

# The closed budget vocabulary a `tags:` line may use. It is a MEASUREMENT of the corpus, not a
# wish: over the 39 content documents the tag counts are authoring-time 26, real-time 19,
# near-real-time 3, and `runtime` -- the fourth word the migration started from -- appears in no
# `tags:` line at all. It was collapsed into `real-time` and the collapse is complete.
BUDGET_TAGS = ("authoring-time", "near-real-time", "real-time")
# `runtime` survives in ONE Tier line (simulation-time-budget.md: "the boundary between
# authoring-time and runtime") as the pre-migration spelling of the real-time budget. It is
# accepted as EVIDENCE that a page names the real-time budget, and never as a CLAIM that the
# page carries a regime its tags do not -- because "the runtime" is also this corpus's word for
# the host that consumes a baked field, and four authoring-time-only documents use it that way
# (driver-fields, flow-routing, node-graph-runtime, sea-ice). Reading it symmetrically would
# fail all four; refusing it entirely would fail simulation-time-budget. The asymmetry is the
# whole design and it is why this is a pair of one-directional rules and not a set equality.
BUDGET_ALIASES = {"runtime": "real-time"}
# Hyphen is a word character on both sides here, so `near-real-time` does NOT also register
# `real-time`, and `node-graph-runtime.md` -- a document NAME that appears in Tier prose -- does
# not register `runtime`. Both were live in the corpus when this was written.
_BUDGET_WORD = {w: re.compile(rf"(?<![a-z-]){re.escape(w)}(?![a-z-])")
                for w in (*BUDGET_TAGS, *BUDGET_ALIASES)}
TIER_PREFIX = "**Tier:"


def content_documents() -> list[Path]:
    """The documents a reader is routed to: everything but the bibliographies and apparatus.

    Three call sites computed this by hand with the same comprehension, one of them re-globbing
    `paper_files()` once per document. A denominator five call sites share is worth one spelling.
    """
    papers = set(paper_files())
    return [p for p in documents(ROOT) if p not in papers and p not in (INDEX, COVERAGE)]


def _budget_tokens(text: str) -> tuple[set[str], set[str]]:
    """`(claimed, evidenced)` budget regimes named in `text`.

    `claimed` is the canonical vocabulary only -- what the page asserts. `evidenced` adds the
    pre-migration aliases -- what the page can be read as naming. See BUDGET_ALIASES for why
    those are two sets and not one.
    """
    claimed = {w for w in BUDGET_TAGS if _BUDGET_WORD[w].search(text)}
    return claimed, claimed | {canon for alias, canon in BUDGET_ALIASES.items()
                               if _BUDGET_WORD[alias].search(text)}


def check_budget_agreement() -> tuple[list[str], int, int, list[str]]:
    """The `**Tier:` line on the page must agree with the budget tag in `tags:`.

    Criterion 6 of the plan reads "37/37 carry a `**Tier:` line that agrees with one canonical
    budget tag, CHECKED". The lines landed -- 38 of 39 documents carry one -- and for two days
    nothing compared them to anything. The fact was on the page 38 times and enforced zero
    times, which is the same shape as the `tier:` field before check_documents grew a comparison
    for it: a value that LOOKS graded, that a reader trusts, and that no run can contradict.

    Two one-directional rules, because the vocabulary is asymmetric (see BUDGET_ALIASES):

      * a regime NAMED on the page must be a tag -- otherwise the page advertises a budget the
        machine-readable half denies, and `index.py`'s routing disagrees with the prose;
      * a regime TAGGED in front matter must be named on the page -- otherwise the reader the
        criterion is about cannot tell the regime from the page, which is the whole criterion.

    NOT a failure, and deliberately: a document with NO `**Tier:` line at all. Ground rule 2
    (subtract before you add) blocks a four-line insertion into a document already inside the
    20-line no-add band, and river-networks.md at 430 lines is there on purpose -- the commit
    that migrated the other 38 says so in its subject line. A guard that goes red on a decision
    the corpus made deliberately is a guard that gets stubbed within a week, and this file has
    the decoys to prove it takes that seriously. But silence is not the alternative: the count
    is REPORTED with the missing documents NAMED, so the coverage can be seen to fall without
    anyone being punished for a cap they cannot violate. What IS enforced for every content
    document, Tier line or not, is that `tags:` carries at least one budget regime -- so the
    regime is always machine-readable even where the page does not print it.

    What it cannot see: whether the regime is TRUE. `**Tier: real-time rasteriser.**` on a
    document whose one recommendation takes 400 ms is agreement, not correctness. It compares
    two declarations to each other, exactly like check_axis_agreement, and the two are written
    by the same hand on the same day.
    """
    problems: list[str] = []
    stated = 0
    missing: list[str] = []
    for path in content_documents():
        rel = path.relative_to(ROOT)
        try:
            fm, body = parse_front_matter(path)
        except (OSError, Unparseable):
            continue                      # reported by check_documents
        tags = {str(t).strip().lower() for t in fm.get("tags", [])} & set(BUDGET_TAGS)
        if not tags:
            problems.append(f"{rel}: no budget tag in `tags:` -- one of "
                            f"{', '.join(sorted(BUDGET_TAGS))} is required, so a reader who "
                            f"never opens the page can still tell what budget it is written for")
            continue
        offset = _offset(path)
        lines = body.split("\n")
        start = next((i for i, ln in enumerate(lines) if ln.startswith(TIER_PREFIX)), None)
        if start is None:
            missing.append(rel.name)
            continue
        stated += 1
        # The whole PARAGRAPH, not the line. wave-models.md's Tier sentence wraps, and its
        # second regime -- "the shore band's travel-time solve is / authoring-time" -- is on the
        # continuation line. Reading one line called that document a disagreement.
        para: list[str] = []
        for ln in lines[start:]:
            if not ln.strip():
                break
            para.append(ln)
        n = start + offset
        claimed, evidenced = _budget_tokens("\n".join(para))
        if extra := claimed - tags:
            problems.append(
                f"{rel}:{n}: the `{TIER_PREFIX}` line claims "
                f"{', '.join(f'`{t}`' for t in sorted(extra))}, which `tags:` does not carry "
                f"({', '.join(f'`{t}`' for t in sorted(tags))}). The page and the routing table "
                f"name different budgets")
        if unnamed := tags - evidenced:
            problems.append(
                f"{rel}:{n}: `tags:` carries {', '.join(f'`{t}`' for t in sorted(unnamed))} and "
                f"the `{TIER_PREFIX}` line never names it, so a reader cannot tell that regime "
                f"from the page -- which is the whole reason the line exists")
    return problems, stated, stated + len(missing), sorted(missing)


# A cross-reference into this corpus, as the corpus actually writes one: a code span whose
# ENTIRE content is a document filename. That shape is what 560 of them look like today, across
# all 48 files, and it is deliberately narrower than "anything ending in .md":
#   - `→ file.md` and `→ document.md` in coverage.md's row-format legend are placeholders in a
#     schema, not references, and the arrow inside the span is what says so;
#   - `WorkGraphs.md`, `ResourceBinding.md`, `README.md` name files in other people's
#     repositories -- CamelCase is not this corpus's naming shape;
#   - `19-fluid-simulation.md`, `12-water-rendering.md` are files of the retired `terrain-*`
#     skills, which numbered their documents; gaia never has.
# The residue is REPORTED by name below rather than dropped in silence.
_DOC_SPAN = re.compile(r"`([^`\n]+)`")
_DOC_LINK = re.compile(r"\]\(([^)\s]+\.md)\)")
_DOC_NAME = re.compile(r"^[a-z][a-z0-9-]*\.md$")
_MD_BARE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.md$")

# (span content, is it a cross-reference this guard must resolve?). Every False here is a live
# span in the corpus today, not an invented one, and each is the reason the pattern is not
# simply `.*\.md`.
DOC_NAME_FIXTURES = [
    ("shallow-water.md", True),
    ("caustics.md", True),                 # no hyphen: the corpus has three such documents
    ("papers-flow.md", True),
    ("→ file.md", False),                  # coverage.md's row-format legend, not a reference
    ("WorkGraphs.md", False),              # a Microsoft spec file
    ("ResourceBinding.md", False),
    ("19-fluid-simulation.md", False),     # the retired terrain-renderer numbered its documents
    ("d3d/WorkLists.md", False),           # carries its directory: not a bare sibling name
    ("scripts/check.py", False),
    ("see `shallow-water.md`", False),     # a span is the whole reference or it is not one
]

# (text, claimed regimes, evidenced regimes). The first four are Tier paragraphs from the
# corpus, verbatim in substance; they are the cases that decide the asymmetry.
BUDGET_FIXTURES = [
    ("**Tier: real-time rasteriser.**", {"real-time"}, {"real-time"}),
    ("**Tier: real-time rasteriser and near-real-time ray-traced.**",
     {"real-time", "near-real-time"}, {"real-time", "near-real-time"}),
    # `near-real-time` must not also register `real-time`: the hyphen is a word character.
    ("**Tier: near-real-time and ray-traced.**", {"near-real-time"}, {"near-real-time"}),
    # The alias, evidencing a tag it may not claim on its own.
    ("**Tier: the crossover document; both budgets.** the boundary between authoring-time\n"
     "and runtime, so every section states the same step under each regime.",
     {"authoring-time"}, {"authoring-time", "real-time"}),
    # "the runtime" as a NOUN, on four authoring-time-only documents. Reading it as a claim
    # would fail all four; it is evidence and nothing more.
    ("**Tier: authoring-time; the runtime consumes the baked fields.**",
     {"authoring-time"}, {"authoring-time", "real-time"}),
    # A document NAME is not a budget word.
    ("see `node-graph-runtime.md` for the scheduler", set(), set()),
    ("nothing here states a budget at all", set(), set()),
]


def check_paths() -> tuple[list[str], int, int, list[str]]:
    """A document this corpus names must be a document this corpus has.

    Audit G#9. `check.py` was green on a dangling `.md` cross-reference: a reviewer renamed one
    in caustics.md to a file that does not exist and the run exited 0. Nothing read them --
    check_coverage validates coverage.md's `→ target` column and stops there, so the 560
    references the BODIES and SKILL.md carry, which is how a reader actually moves through this
    skill, were unwatched. A rename is the ordinary event that breaks them, and this corpus renames.

    This is a FAILURE, not a metric, and the distinction is the point: a dangling `→ file.md`
    in coverage.md has been a hard failure since the map existed, and the same sentence in a
    document's prose was worth nothing. Two spellings of one defect cannot have two verdicts.

    Read from the BODY only, outside fenced blocks. A `locator:` in front matter names a place
    INSIDE a cited artefact -- "the front-to-back bullet in README.md" is a location in someone
    else's repository, not a path in this one -- and a fenced block is code or a template.

    ⚠️ What it does NOT check, named rather than implied. Bare `.md` names outside gaia's own
    naming shape are out of reach, and the corpus has five, at six sites: `19-fluid-simulation.md`
    (shallow-water.md, papers-simulation.md), `12-water-rendering.md`,
    `12b-water-provenance.md`, `WorkGraphs.md`, `ResourceBinding.md`. The plan named the first
    of those -- shallow-water.md's reference to the retired terrain-renderer's fluid document --
    as G#9's live instance, and it is live still: as written it resolves to no path a reader can
    open, because the directory that would make it resolvable sits in a DIFFERENT code span.
    Enforcing those here would go red on five documents this guard's author does not own, so the
    residue is counted and named in the run's output instead, and a `corrections.tsv` row asks
    the owners for the one repair that fixes the class: put the directory inside the span.
    Paths to `.py` harnesses and `.tsv` registers are also unread -- the execution register names
    27 harness scripts that were never committed, so a check over them would be red on arrival.
    """
    problems: list[str] = []
    existing = {p.name for p in documents(ROOT)}
    refs = 0
    residue: dict[str, list[str]] = {}
    for path in [ROOT / "SKILL.md", *documents(ROOT)]:
        if not path.exists():
            continue
        rel = path.relative_to(ROOT)
        offset = _offset(path)
        fenced = False
        for n, line in enumerate(path.read_text(encoding="utf-8").split("\n")[offset - 1:],
                                 offset):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for span in _DOC_SPAN.findall(line) + _DOC_LINK.findall(line):
                name = span.strip()
                if not _DOC_NAME.match(name):
                    if _MD_BARE.match(name):
                        residue.setdefault(name, []).append(f"{rel}:{n}")
                    continue
                refs += 1
                if name not in existing:
                    problems.append(
                        f"{rel}:{n}: names `{name}`, and references/{name} does not exist. A "
                        f"cross-reference to a document nobody wrote sends the reader nowhere; "
                        f"either the target was renamed and this end was not, or the document "
                        f"was never written and belongs in coverage.md as `planned`")
    return problems, refs, len(existing), [f"{k} ({', '.join(v)})" for k, v in sorted(residue.items())]


def covered_documents() -> dict[str, str]:
    """`{document filename: topic id}` for every `covered` row in coverage.md.

    Shares `_TOPIC` with `check_coverage`, which reports the malformed rows; this one assumes
    the rows it can parse and stays silent about the rest so the same defect is not reported
    from two places with two different wordings.
    """
    out: dict[str, str] = {}
    try:
        _, body = parse_front_matter(COVERAGE)
    except (OSError, Unparseable):
        return out
    in_fence = False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not (m := _TOPIC.match(line.rstrip())):
            continue
        if m["state"] == "covered" and "\u2192" in m["rest"]:
            target = m["rest"].split("\u2192")[-1].strip()
            # A target that does not exist is check_coverage's finding and only its finding.
            # Passing it on gave ONE defect two messages from two functions, and that is why
            # the `bites` row for it was vacuous: it stayed red with check_coverage deleted,
            # because check_trigger_coverage was reporting the same broken row in its own
            # words. Same rule as this docstring already states for malformed rows.
            if (ROOT / "references" / target).exists():
                out[target] = m["id"]
    return out


def check_trigger_coverage() -> list[str]:
    """Does the trigger suite actually exercise the corpus, or only the parts someone remembered?

    A trigger suite is easy to grade by its size and impossible to grade by its reach: 25 queries
    look thorough right up until you ask which documents they touch. When this was first counted,
    **17 of 34 written documents had no positive query at all** -- half the corpus, including every
    one of the eleven gap documents written most recently. Nothing reported that, because nothing
    could: `should_trigger` says whether the SKILL should fire, never which document should answer.

    So each positive now names the document(s) it should reach, and this asserts the same two
    directions `check_coverage` asserts of the map itself: every `covered` document is reached by
    some query, and every query reaches a document that exists and is claimed. The first direction
    is the one that catches a new document arriving with no eval; the second catches a rename.
    """
    if not TRIGGERS.exists():
        return [f"evals/{TRIGGERS.name} is missing -- trigger coverage cannot be checked"]
    try:
        rows = json.loads(TRIGGERS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"evals/{TRIGGERS.name}: {e}"]

    problems: list[str] = []
    reached: set[str] = set()
    for i, row in enumerate(rows):
        if not row.get("should_trigger"):
            if "routes_to" in row:
                problems.append(f"evals/{TRIGGERS.name}[{i}]: a NEGATIVE query carries `routes_to`. "
                                "A query the skill must not fire on cannot route anywhere.")
            continue
        targets = row.get("routes_to")
        if not targets:
            problems.append(f"evals/{TRIGGERS.name}[{i}]: positive query names no `routes_to` -- "
                            f"{row.get('query', '')[:60]!r}. Without it the suite's reach across "
                            "the corpus is unmeasurable, which is how half of it went untested.")
            continue
        reached.update(targets)

    claimed = covered_documents()
    problems += [f"evals/{TRIGGERS.name}: `routes_to` names {t}, which no `covered` coverage.md "
                 "topic claims -- renamed, or never written" for t in sorted(reached - set(claimed))]
    problems += [f"references/{d} is `covered` (topic `{claimed[d]}`) but no positive trigger "
                 "query routes to it -- the skill is never tested on the subject it claims"
                 for d in sorted(set(claimed) - reached)]
    return problems


_SECTION = re.compile(r"(?:§|\bsections?\s+)\s*([0-9]+(?:\.[0-9]+)*|[IVX]+(?:-[A-Z])?)", re.I)

# A section belonging to a DIFFERENT paper named in the prose. The first version of this check
# had no such filter and its single corpus-wide hit was exactly that: `orzan2008`'s entry says
# "the paper `hnaidi2010` §4.2 borrows from", and §4.2 was read as orzan2008's own.
_FOREIGN_SECTION = re.compile(
    r"[`\[]?\b[a-z][a-z0-9_]{4,}\b[`\]]?\s+(?:§|sections?\s+)\s*[0-9IVX][0-9.\-A-Z]*", re.I)


def section_tokens(text: str) -> set[str]:
    """Section numbers a passage claims for its OWN source."""
    return {m.group(1).upper() for m in _SECTION.finditer(_FOREIGN_SECTION.sub(" ", text))}


PROPAGATION_FIXTURES = [
    ("§4.2 Theorem 3 and §3", {"4.2", "3"}),
    ("section 3.1 River network and channel models", {"3.1"}),
    ("§II-A Eq. (1) and Fig. 2", {"II-A"}),
    ("the paper `hnaidi2010` §4.2 borrows from", set()),      # a foreign section, not ours
    ("READ IN FULL, no section named", set()),
    ("p. 146 and Fig. 11", set()),                            # pages are not sections
    # The text of a WRAPPED entry's continuation line -- where a section number sits for 88 of
    # the 214 entries, and the half `check_propagation` deliberately does not read. It
    # tokenises perfectly; the reason it is unread is the measured false-positive rate in that
    # function's docstring, not an inability to parse it. Pinned here so the two claims stay
    # distinguishable.
    ("cross-section at `C = l²`, constant, and §4 writes the outflow", {"4"}),
]


def check_propagation(bib: dict[str, dict],
                      cites: dict[str, list[tuple[Path, str]]]) -> tuple[list[str], int, int]:
    """Do the two ends of a citation name the SAME section?

    The most common defect this corpus has ever recorded is a correction landing at one end of a
    citation and not the other -- a locator sharpened in a document while its bibliography entry
    keeps the old section, or the reverse. It has been found by hand at least eight times, and
    twice the *fix* for it landed at one end only. `check_not_opened` already ties the two ends
    on the question of whether a source was read; this ties them on WHERE.

    It reports only the unambiguous case: both ends name sections and the sets are **disjoint**.
    Overlap passes, because a bibliography entry legitimately describes more of a paper than any
    one document cites.

    ⚠️ **What it cannot see, and the number is the point.** Only about 6% of citation pairs name a
    section at both ends; the rest name one at one end or neither, and nothing can be
    cross-checked there. This is a narrow instrument over a corpus-wide problem, and the ratio is
    reported so nobody mistakes a green check for a checked corpus.

    ⚠️ **Why the bibliography side reads only the entry's first line.** This used to say
    `f"{entry['ref']} {entry.get('note', '')}"`, and `_scan` builds no `note` key, so half the
    text named in that expression was always `""`. The obvious repair -- populate `note` from the
    88 entries that wrap onto continuation lines -- was BUILT AND MEASURED before being rejected:
    it lifts the comparable pairs from 16/256 to 48/256 and reports **seven** corpus-wide hits,
    every one of them correct prose. `mei2007`'s entry names §3 while three documents cite §3.2,
    §3.2.1 and §3.2.2 (a parent section, read as disjoint by a token compare); `stava2008`'s
    entry names §4 for the pipe cross-section while two documents cite §5, §7 and §8 for other
    claims; `hillaire2020`'s entry names §7 and Table 2 for the cost figures while two documents
    cite §5.3. That is the identical false-positive shape already recorded in
    `guard-proofs.tsv` for the body-prose direction: a document legitimately cites different
    sections of one paper for different claims, and an entry need not enumerate them all. So the
    dead key is REMOVED rather than filled, and this paragraph is why -- the reach stays at
    16/256 by choice, not by oversight.
    """
    problems: list[str] = []
    both = total = 0
    for cid, uses in sorted(cites.items()):
        entry = bib.get(cid)
        if not entry:
            continue
        btoks = section_tokens(entry.get("ref", ""))
        for path, locator in uses:
            total += 1
            ltoks = section_tokens(locator)
            if not btoks or not ltoks:
                continue
            both += 1
            if not (btoks & ltoks):
                problems.append(
                    f"references/{path.name}: cites `{cid}` at section(s) "
                    f"{sorted(ltoks)}, but its bibliography entry names {sorted(btoks)} and the "
                    "two do not overlap. One end was corrected and the other was not")
    return problems, both, total


def check_axis_agreement() -> list[str]:
    """A document's axis tag must match the coverage.md section its topic row sits under.

    Three sources name a document's axis and nothing compared them: the document's own `tags:`
    (from which index.py builds the routing table), coverage.md's hand-written `## ` sections,
    and SKILL.md's routing bullets. Three documents had drifted -- seamless-and-periodic filed
    Generation by tag and Architecture by the router, sea-ice Generation by tag and Simulation
    by coverage, mask-to-material Rendering by tag and Generation by coverage.

    A reader following SKILL.md to the generated index landed under a different heading, and no
    check could see it: check_coverage() matches topics to files and never reads the headings
    those topics sit under. This compares the two machine-readable halves. SKILL.md's prose is
    still on the author.
    """
    problems: list[str] = []
    try:
        text = COVERAGE.read_text(encoding="utf-8")
    except OSError:
        return problems
    section = None
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        m = _TOPIC.match(line)
        if not m or section not in AXIS_TAGS:
            continue
        doc = re.search(r"→\s*([a-z0-9-]+\.md)", m["rest"])
        if not doc:
            continue
        path = ROOT / "references" / doc.group(1)
        if not path.exists():
            continue                      # reported by check_coverage
        try:
            fm, _ = parse_front_matter(path)
        except Unparseable:
            continue
        tags = [str(t).strip().lower() for t in fm.get("tags", [])]
        axis = next((t for t in tags if t in AXIS_TAGS), None)
        if axis is None:
            problems.append(f"references/{doc.group(1)}: no axis tag, so index.py cannot route "
                            f"it, while coverage.md files it under `{section}`")
        elif axis != section:
            problems.append(f"references/{doc.group(1)}:{n}: tagged `{axis}` -- so the generated "
                            f"index lists it under {axis.title()} -- but coverage.md files it "
                            f"under `{section}`. A reader routed by one lands under the other")
    return problems


def check_headings() -> list[str]:
    """Headings must be unique within a document and must not carry unbalanced backticks.

    This exists because of a real corruption that shipped. A section was inserted by replacing
    the first occurrence of a heading string -- but that string also appeared INSIDE a sentence
    (`see `## What these fields do to the runtime` below`), so the insertion split the sentence,
    swallowed the new section's own heading, and left a bogus `## What these fields do to the
    runtime` below. Worse than the horizon` heading mid-file. The document then had two headings
    with the same name, one of them a fragment, and a cross-reference pointing at a heading that
    no longer existed.

    Every other check passed. Citations resolved, the line cap held, the front matter parsed,
    `## Use this` was still first -- because none of them look at heading STRUCTURE. A document
    can be spliced in half and stay green.

    Both rules below are cheap and would have caught it: the duplicate name, and the unbalanced
    backtick in the fragment.
    """
    problems: list[str] = []
    skip = {INDEX, COVERAGE}
    for path in documents(ROOT):
        if path in skip:
            continue
        rel = path.relative_to(ROOT)
        seen: dict[tuple[int, str], int] = {}
        fenced = False
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            # A `#` comment inside a code block is not a heading. Without this, a duplicated
            # comment in two fences was reported as a duplicate heading, and an odd backtick in
            # a comment as an unbalanced one -- naming a line the reader does not see as a
            # heading at all. Every other walker in this file tracks fences; this one did not.
            if fenced or not line.startswith("#"):
                continue
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            if line.count("`") % 2:
                problems.append(f"{rel}:{n}: heading has an unbalanced backtick -- "
                                f"a heading is not a place for half a code span, and this is "
                                f"what a spliced insertion looks like: {text[:60]!r}")
            # Keyed on (level, text): a `### Cost` under two different `##` sections is
            # legitimate, and the bibliographies -- previously skipped, which was hiding this
            # rather than deciding it -- carry three real `##`/`###` same-name pairs.
            if (level, text) in seen:
                problems.append(f"{rel}:{n}: duplicate heading {text[:50]!r} at the same level, "
                                f"already at line {seen[(level, text)]}. Either one is a leftover "
                                f"from an edit, or a cross-reference to it is ambiguous")
            else:
                seen[(level, text)] = n
    return problems


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

    THE FAILURE TABLE IS STRUCTURE TOO, and for a second reason. It is the other place a reader
    lands (`SKILL.md:42` tells them to take it as one packet), and since `body_digest` it is
    half of what a `verified:` stamp certifies. A digest keyed on a heading spelling is a digest
    that can be emptied by renaming the heading -- so the two spellings the corpus uses are
    named here, exactly one per document, rather than left to `_is_anchor` to find or not find.
    Two spellings, not a pattern: matching a bare "fails" would swallow content sections like
    "The priority function, and why FIFO fails", which is a section ABOUT a failure.
    """
    problems: list[str] = []
    skip = set(paper_files()) | {INDEX, COVERAGE}
    total = first = 0
    for path in documents(ROOT):
        if path in skip:
            continue
        rel = path.relative_to(ROOT)
        body = path.read_text(encoding="utf-8")
        heads = [ln.strip() for ln in body.splitlines() if ln.startswith("## ")]
        fails = [h for h in heads if h.lower().startswith("## how this fails")
                 or h.lower().startswith("## when it fails")]
        if len(fails) != 1:
            problems.append(
                f"{rel}: {len(fails)} heading(s) start `## How this fails` or `## When it "
                f"fails`; exactly one is required. That heading is where a reader's second "
                f"landing is, and half of what `covers_body` digests -- renaming it would "
                f"empty that half of a stamp with nothing going red.")
        if not any(h.lower().startswith("## use this") for h in heads):
            problems.append(f"{rel}: no `## Use this` section -- it "
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


# The execution register's columns, in order. Named here rather than counted, so that dropping
# a column is a FAILURE with a name and not a silent re-interpretation of every row: the file is
# tab-separated with prose in five of the seven fields, and a lost tab shifts `provenance` into
# `termination` without changing a single character a reader would notice.
PSEUDOCODE_COLUMNS = ("document", "block", "what was asserted", "what the run measured",
                      "outcome", "provenance", "termination")
# The `termination` vocabulary, documented at the head of the register itself. It is a CLOSED
# set on purpose: the point of the column is that a row cannot be silent about halting, and a
# free-text cell is silence with extra steps. `n/a` and `no-block` are not the same value --
# the first says the code has no loop, the second says there is no code.
TERMINATION_VALUES = {"n/a", "halts-proven", "halts-measured", "cap-bounded", "unknown",
                      "no-block"}
# A cell that names another row of the same file BY LINE NUMBER. A row has no stable line: every
# row that lands above it moves it, and the header moves them all at once. The edit that added
# the `termination` column is the proof and the reason this exists -- it inserted 55 lines of
# header, and seven cells that had been written `row :52` went on saying :52, which by then was a
# line of the comment block. Every one of them still parsed, still had seven fields and still
# carried a legal token, so nothing in this file objected; a reviewer found them by hand. The
# repair is an idiom (name the row by its document and block, which do not move) and this is the
# gate that keeps it. Deliberately narrow: `\brows? :\d+` and nothing else, so it cannot fire on
# `flow-routing.md:239` or on a bare `:42`, both of which are lines in a REFERENCE document and
# are the normal, correct thing for a cell to carry.
REGISTER_ROW_REF = re.compile(r"\brows?\s+:\d+")


def check_pseudocode_register(path: Path | None = None) -> tuple[list[str], dict[str, int]]:
    """The execution register's shape, and how many blocks nobody has checked for halting.

    WHY THIS EXISTS. A row in that register says a block reproduces a NUMBER. It never said the
    block STOPS. `heightfield-raymarching.md`'s row is the proof that those are two claims: it
    measured missed hits, recorded SOUND, and the same block livelocked on 35.7% of 600 rays,
    found by hand a fortnight later. SKILL.md:103 carries the sentence; this carries the column.

    What it ENFORCES is shape -- seven fields, the header naming them, a termination token from
    the closed vocabulary -- and one idiom: a cell may NOT name another row of this file by line
    number (see REGISTER_ROW_REF). That is deliberately mechanical: nothing here can tell whether
    `halts-proven` is true, any more than the citation checks can tell whether a paper says what
    a document claims. What it REPORTS is the `unknown` count, in the style of the other reported
    metrics: a number that has to go down, not a gate that can be gamed by writing `n/a`
    everywhere. A reviewer still has to read the cell's argument.

    ⚠️ It does NOT resolve the `document.md:NN` references the cells DO carry. Those point into
    39 documents this repo edits daily, and an insertion anywhere above a fence moves it silently
    -- four such references were stale the day this guard was written, every one of them because
    another author had inserted a paragraph, none of them because the cell was wrong when
    written. A guard over them would be permanently red on other people's work, which is a guard
    nobody reads. Self-references are different in kind: this file moves them itself.
    """
    reg = path or PSEUDOCODE
    problems: list[str] = []
    counts: dict[str, int] = {v: 0 for v in TERMINATION_VALUES}
    if not reg.exists():
        return [f"{reg}: the pseudocode execution register is missing -- without it, no block "
                f"in this corpus is recorded as having been run"], counts
    text = reg.read_text(encoding="utf-8")
    # Every line, comments included: one of the seven references this catches lived in the
    # header comment block, and a comment that misdirects a reader is not a lesser defect.
    for n, ln in enumerate(text.split("\n"), 1):
        if m := REGISTER_ROW_REF.search(ln):
            problems.append(
                f"{reg.name}:{n}: {m.group(0)!r} names a row of THIS file by line number, and a "
                f"row has no stable line -- adding the `termination` header moved every row 55 "
                f"lines and seven such references followed it into the comment block. Name the "
                f"row by its document and block, which do not move")
    rows = [(n, ln) for n, ln in enumerate(text.split("\n"), 1)
            if ln.strip() and not ln.lstrip().startswith("#")]
    if not rows:
        return problems + [f"{reg.name}: no header row and no rows"], counts
    n, header = rows[0]
    got = tuple(header.split("\t"))
    if got != PSEUDOCODE_COLUMNS:
        # Returned early: with the header wrong, every per-row message below would be noise
        # about the same one defect. The line-reference findings are NOT noise about it -- they
        # are independent of the column shape -- so they are carried out rather than dropped.
        return (problems + [f"{reg.name}:{n}: columns are [{' | '.join(got)}]; expected "
                            f"[{' | '.join(PSEUDOCODE_COLUMNS)}]"], counts)
    for n, ln in rows[1:]:
        f = ln.split("\t")
        where = f"{reg.name}:{n}"
        named = f"{f[0][:36]} / {f[1][:44]}" if len(f) > 1 else f[0][:36]
        if len(f) != len(PSEUDOCODE_COLUMNS):
            problems.append(f"{where}: {len(f)} fields, expected {len(PSEUDOCODE_COLUMNS)} "
                            f"({', '.join(PSEUDOCODE_COLUMNS)})  ->  {named}")
            continue
        token = f[-1].split()[0] if f[-1].split() else ""
        if token not in TERMINATION_VALUES:
            problems.append(f"{where}: termination is {token or '(empty)'!r}, not one of "
                            f"{sorted(TERMINATION_VALUES)}  ->  {named}")
            continue
        counts[token] += 1
    return problems, counts


def fenced_block_coverage() -> tuple[int, int, list[str]]:
    """Fenced blocks in the corpus, and the documents holding one that NO register row names.

    Criterion 2 has two halves. The register's own half -- every row says whether its block
    halts -- is checked above. This is the other: a block with no row at all is untested by
    construction, and the register cannot see it because the register only knows what it lists.

    It counts DOCUMENTS, not blocks, and the difference matters. Rows are keyed by prose ("the
    droplet loop, after adding the sediment writes"), never by line, so no mechanical map exists
    from a row to the fence it ran; a row may cover several fences and several rows may cover
    one. So a document appearing here is a certainty (nothing in it is registered) while its
    absence proves nothing about its other fences. REPORTED, not enforced.
    """
    skip = {p.name for p in paper_files()} | {INDEX.name, COVERAGE.name}
    fences: dict[str, int] = {}
    for p in documents(ROOT):
        if p.name in skip:
            continue
        n = inside = 0
        for line in p.read_text(encoding="utf-8").split("\n"):
            if line.lstrip().startswith("```"):
                inside = not inside
                n += inside          # count openers only, so ```lang and ``` are one block
        fences[p.name] = n
    # Tokenised, not a substring test: one document's name being a substring of another's
    # would silently mark it registered. The document column holds `a.md, b.md` and `a.md:14`.
    listed: set[str] = set()
    if PSEUDOCODE.exists():
        for ln in PSEUDOCODE.read_text(encoding="utf-8").split("\n"):
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            for tok in re.split(r"[,\s]+", ln.split("\t")[0]):
                listed.add(tok.split(":")[0].strip())
    total = sum(fences.values())
    with_fences = sum(1 for v in fences.values() if v)
    gap = sorted(name for name, v in fences.items() if v and name not in listed)
    return total, with_fences, gap


# A register with one defect of each shape the check exists to catch. Every row below is a real
# failure mode, not a decoration: a dropped tab (the shape a hand edit produces), an extra tab
# (the shape a note containing a tab produces), a plausible-but-unlisted token, an empty cell,
# and -- in a data row AND in the header comment, because both happened -- a row named by line
# number. The FIXED copy differs from it ONLY in those six places and must go quiet: a check
# that cannot be made to fail is not a check, and two of this corpus's guards were exactly that.
_REG_HEAD = "\t".join(PSEUDOCODE_COLUMNS)
_REG_OK = ("a.md\tthe stack loop\tit halts\t3600 of 3600\tSOUND\tlead\t"
           "halts-proven -- one for-each over a finite set")
PSEUDOCODE_FIXTURE = "\n".join([
    # the header comment block is scanned too, and a blank line is skipped
    "# the driver every row here shares is row :4's",
    "",
    _REG_HEAD,
    _REG_OK,
    # a dropped tab: six fields, so `provenance` would be read as `termination`
    "b.md\tthe droplet step\tit erodes\trelief 1.0 to 0.91\tDEFECT CONFIRMED\tagent",
    # an extra tab inside the note
    "c.md\tthe march\tit stops\t0/600\tSOUND\tagent\thalts-measured -- 0/600\tstepCap 1e9",
    # a token that reads like a value and is not one
    "d.md\tthe relaxation\tit converges\t155 passes\tSOUND\tlead\tterminates -- it finished",
    # nothing at all in the cell
    "e.md\tthe sweep\tit is exact\tzero drift\tSOUND\tlead\t",
    # well-formed in every other way, and pointing at a line instead of at a row. Note the
    # `f.md:12` beside it: a reference into a DOCUMENT is correct and must NOT be flagged.
    "f.md\tthe second pass\tit repeats the first\t12 passes\tSOUND\tlead\t"
    "halts-proven -- the fence at f.md:12 repeats row :4's pass",
]) + "\n"
PSEUDOCODE_FIXTURE_FIXED = "\n".join([
    "# the driver every row here shares is the `a.md / the stack loop` row's",
    "",
    _REG_HEAD,
    _REG_OK,
    "b.md\tthe droplet step\tit erodes\trelief 1.0 to 0.91\tDEFECT CONFIRMED\tagent\t"
    "n/a -- the fence is one step, straight-line",
    "c.md\tthe march\tit stops\t0/600\tSOUND\tagent\thalts-measured -- 0/600, stepCap 1e9 unhit",
    "d.md\tthe relaxation\tit converges\t155 passes\tSOUND\tlead\thalts-measured -- to tolerance",
    "e.md\tthe sweep\tit is exact\tzero drift\tSOUND\tlead\tunknown",
    "f.md\tthe second pass\tit repeats the first\t12 passes\tSOUND\tlead\t"
    "halts-proven -- the fence at f.md:12 repeats the `a.md / the stack loop` row's pass",
]) + "\n"
# (line in the fixture, substring the message must carry)
PSEUDOCODE_FIXTURE_EXPECTED = [
    (":1", "'row :4' names a row of THIS file by line number"),
    (":5", "6 fields, expected 7"),
    (":6", "8 fields, expected 7"),
    (":7", "termination is 'terminates'"),
    (":8", "termination is '(empty)'"),
    (":9", "'row :4' names a row of THIS file by line number"),
]


def _register_fixture_run(text: str) -> list[str]:
    """What check_pseudocode_register() says of a fixture register written to a temp tree."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "pseudocode-execution.tsv"
        p.write_text(text, encoding="utf-8")
        return check_pseudocode_register(p)[0]


def register_selftest() -> list[str]:
    """Assert the register check goes RED on each defect and GREEN once they are repaired."""
    bad: list[str] = []
    broken = _register_fixture_run(PSEUDOCODE_FIXTURE)
    for line, want in PSEUDOCODE_FIXTURE_EXPECTED:
        if not any(line in p and want in p for p in broken):
            bad.append(f"no finding matches {line} + {want!r}: {broken}")
    if len(broken) != len(PSEUDOCODE_FIXTURE_EXPECTED):
        bad.append(f"{len(broken)} findings on the broken fixture register, expected "
                   f"{len(PSEUDOCODE_FIXTURE_EXPECTED)}: {broken}")
    with tempfile.TemporaryDirectory() as tmp:
        absent = check_pseudocode_register(Path(tmp) / "absent.tsv")[0]
    if not any("missing" in p for p in absent):
        bad.append(f"an absent register is not reported as missing: {absent}")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "fixed.tsv"
        p.write_text(PSEUDOCODE_FIXTURE_FIXED, encoding="utf-8")
        fixed, counts = check_pseudocode_register(p)
    if fixed:
        bad.append(f"the repaired fixture register is not quiet: {fixed}")
    if (counts["n/a"], counts["halts-measured"], counts["halts-proven"],
            counts["unknown"]) != (1, 2, 2, 1):
        bad.append(f"the repaired fixture register tallies {counts}, expected one each of "
                   f"n/a and unknown and two each of halts-proven and halts-measured")
    # The document reference in the repaired `f.md` row -- `f.md:12` -- must survive: a guard
    # that also flagged those would make the correct idiom unwritable, and that is the shape of
    # over-reach this repo's guard-proofs register exists to record.
    if any("f.md:12" in p for p in fixed):
        bad.append(f"a `document.md:NN` reference is being flagged as a row self-reference: "
                   f"{fixed}")
    # The header is the other half: drop the column name and every row below it is being read
    # against a shape the file no longer has.
    headless = _register_fixture_run(
        PSEUDOCODE_FIXTURE_FIXED.replace("\ttermination\n", "\n", 1))
    if not any("columns are" in p for p in headless):
        bad.append(f"dropping the `termination` column name is not reported: {headless}")
    # ...and the header check returns EARLY, which is a place findings can be silently dropped.
    # A row self-reference has nothing to do with the column shape, so it must survive that
    # return. Asserted because the first draft of this guard did not: with the header broken it
    # reported the header and swallowed the reference, and the selftest went green anyway.
    headless_ref = _register_fixture_run(
        PSEUDOCODE_FIXTURE.replace("\ttermination\n", "\n", 1))
    if not (any("columns are" in p for p in headless_ref)
            and any("names a row of THIS file by line number" in p for p in headless_ref)):
        bad.append(f"a broken header swallows the row self-reference findings: {headless_ref}")
    return bad


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
    ap.add_argument("--digest", metavar="DOC",
                    help="print the two digests a `verified:` stamp for DOC must carry")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.digest:
        # A stamp has to be computable by the human writing it. Before this the only way to
        # obtain `covers` was to read sources_digest and run it by hand, which is the kind of
        # friction that ends with a guessed value and a permanently stale stamp.
        p = Path(args.digest)
        if not p.exists():
            p = ROOT / args.digest
        fm, body = parse_front_matter(p)
        print(f"covers: {sources_digest(fm)}          # the citation set")
        print(f"covers_body: {body_digest(body)}     # `## Use this` + the failure table")
        return 0
    if args.list:
        print(__doc__)
        return 0

    bib, problems = bibliography()
    doc_problems, used = check_documents(bib)
    rec_problems, rec_first, rec_total = check_recommendation()
    reg_problems, term = check_pseudocode_register()
    bud_problems, bud_stated, bud_total, bud_missing = check_budget_agreement()
    path_problems, path_refs, path_targets, path_residue = check_paths()
    problems += (doc_problems + check_orphans(bib, used) + check_duplication()
                 + check_coverage() + check_index() + rec_problems
                 + check_no_artefact(bib) + check_not_opened(bib, citations_by_id())
                 + check_headings() + check_axis_agreement()
                 + check_trigger_coverage() + reg_problems
                 + bud_problems + path_problems)
    prop_problems, prop_both, prop_total = check_propagation(bib, citations_by_id())
    problems += prop_problems

    docs = content_documents()
    print(f"documents {len(docs)}   bibliography {len(bib)}   cited {len(used)}   "
          f"background {sum(1 for e in bib.values() if e['background'])}")
    if (summary := coverage_summary()):
        print(summary)
    if rec_total:
        print(f"recommendation {rec_total}/{rec_total} documents name an approach to "
              f"implement; {rec_first} state it first, before any explanation.")

    if bud_total:
        print(f"budget {bud_stated}/{bud_total} documents print their budget regime on the page "
              f"as a `{TIER_PREFIX}` line, and every one of those {bud_stated} is CHECKED against "
              f"the budget tag in `tags:` -- both directions, so neither end can move alone. "
              f"All {bud_total} carry a budget tag, which is ENFORCED. "
              + (f"⚠️ Printing no Tier line is an ALLOWED state, not a pass: "
                 f"{', '.join(bud_missing)} "
                 f"{'sits' if len(bud_missing) == 1 else 'sit'} inside the 20-line no-add band "
                 f"under the 450 cap, where ground rule 2 refuses the insertion. Named here so "
                 f"the count can be seen to fall. " if bud_missing else "")
              + f"⚠️ Agreement is not correctness: this compares two declarations written by the "
                f"same hand, never the regime against a measured cost.")

    if path_refs:
        print(f"paths {path_refs} `document.md` cross-references across the corpus and SKILL.md "
              f"all resolve to one of the {path_targets} documents on disk -- ENFORCED, because a "
              f"reference to a document nobody wrote is a broken link, not a metric. "
              + (f"⚠️ Its reach is gaia's own naming shape. {len(path_residue)} bare `.md` "
                 f"name(s) in another shape are NOT checked: {'; '.join(path_residue)}. "
                 f"The first of those is audit G#9's named live instance and it is still live. "
                 if path_residue else "")
              + f"⚠️ `.py` and `.tsv` paths are unread; the execution register names harness "
                f"scripts that were never committed, so a check over them would be red on "
                f"arrival. See registers/guard-proofs.tsv.")

    if prop_total:
        print(f"propagation {prop_both}/{prop_total} ({100 * prop_both / prop_total:.0f}%) of "
              f"citations name a section at BOTH ends, so the rest cannot be cross-checked at all. "
              f"Where both ends name one they must overlap -- a correction landing at one end only "
              f"is this corpus's most-recorded defect, found by hand at least eight times.")

    both, eonly, conly, none = approximation_coverage()
    ntot = both + eonly + conly + none
    if ntot:
        print(f"approximation {both}/{ntot} ({100 * both / ntot:.0f}%) of documents state BOTH how "
              f"good the recommendation is and what it costs -- the two halves of \"how well can I "
              f"approximate this inside a frame budget\", which is the question this audience "
              f"actually brings. {eonly} give an error and no cost, {conly} a cost and no error, "
              f"{none} neither. An error nobody can budget and a cost nobody can justify are each "
              f"half an answer. Reported, not enforced; see registers/guard-proofs.tsv.")

    _reach_problems, unreach, reach_tot = check_section_reach()
    if reach_tot:
        print(f"reach {unreach}/{reach_tot} ({100 * unreach / reach_tot:.0f}%) of body sections "
              f"share NO word with either `## Use this` or the failure table -- the two places a "
              f"reader lands first. Content reachable from neither is invisible to the reader it "
              f"was written for, a shape found by hand in five consecutive documents. ⚠️ This "
              f"check DOES NOT catch the case that motivated it: hydraulic-erosion.md's "
              f"grain-classes section, 31% of that body and absent from both ends, shares the "
              f"words `capacity` and `angle` with failure rows belonging to a different section, "
              f"so it passes. Lexical overlap cannot see a semantic gap. Its output is CANDIDATES: "
              f"most of what remains is generic navigational headings with nothing to match. "
              f"Reported, not enforced, and it does not discharge the hand review; see "
              f"registers/guard-proofs.tsv.")

    _x_problems, xdis, xcmp, xreach, xpairs = check_crossrefs()
    if xpairs:
        print(f"crossrefs {xdis}/{xcmp} shared keyed magnitudes DISAGREE across the "
              f"{xreach}/{xpairs} linked side-pairs that print one at both ends -- a document "
              f"against its own failure table, against a document it names, or against the "
              f"bibliography entry it cites. A correction landing at one end only is this "
              f"corpus's most-recorded defect, found by hand five times in two days. "
              f"⚠️ Its reach is {100 * xreach / xpairs:.0f}% of linked pairs: for the rest there "
              f"is nothing to compare and this line says nothing about them. ⚠️ It DOES NOT "
              f"catch three of the five instances that motivated it -- reconstructing "
              f"water-rendering.md's `exp(-K_d*z)` against water-optics.md's "
              f"`exp(-(K_d + c/mu_v)*z)` reports NOTHING, because the correction added a TERM "
              f"and the two ends stop sharing a key. It sees a constant that moved, never a "
              f"rewording. Output is CANDIDATES with a known false positive (caustics.md's "
              f"`1/(b − b_b)` against water-optics.md's `b_b = b/2`, two formulas over one "
              f"identifier pair). Reported, not enforced; see registers/guard-proofs.tsv.")
        for p in _x_problems:
            print(p)

    sharp, tot, noart, _vague = locator_quality()
    if tot:
        print(f"locators {sharp}/{tot} ({100 * sharp / tot:.0f}%) of the FOLLOWABLE citations "
              f"name a section, equation or page; the rest are topic paraphrases a reader "
              f"cannot follow. A further {noart} cite doctrine or classical results with no "
              f"artefact to open — declared in the locator, and excluded from the ratio rather "
              f"than held against it. Reported, not enforced; see registers/guard-proofs.tsv.")

    if (registered := sum(term.values())):
        blocks = registered - term["no-block"]
        fences, fdocs, fgap = fenced_block_coverage()
        print(f"termination {term['unknown']}/{registered} register rows say NOTHING about "
              f"whether their block halts (`unknown`); {term['n/a']} have no loop, "
              f"{term['halts-proven']} carry an argument, {term['halts-measured']} rest on a run "
              f"that finished with the cap unhit, {term['cap-bounded']} halt only because a cap "
              f"stops them, and {term['no-block']} register a prose claim rather than a block. A "
              f"row here proves a block reproduces a NUMBER, never that it STOPS: the "
              f"raymarching row measured missed hits, recorded SOUND, and that block livelocked "
              f"on 35.7% of 600 rays. ⚠️ The token is ENFORCED, its truth is not -- `halts-proven` "
              f"is worth only the argument written beside it, and `halts-measured` says nothing "
              f"about inputs outside the run. ⚠️ And the register cannot see criterion 2's other "
              f"half: {fences} fenced blocks across {fdocs} documents against {blocks} rows that "
              f"name a block, with {len(fgap)} document(s) holding a fence and no row at all"
              + (f" ({', '.join(fgap)})" if fgap else "")
              + ". Rows are keyed by prose, not by line, so that pair is two counts and NOT a "
                "matching: it is a floor on the gap, never the size of it. Reported, not "
                "enforced; see registers/guard-proofs.tsv.")

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
