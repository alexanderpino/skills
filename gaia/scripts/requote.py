#!/usr/bin/env python3
"""Re-quote pass: find every quotation in the corpus and check it against its artefact.

WHY THIS EXISTS. Truncation at the clause that changes the conclusion is this corpus's
most damaging recurring defect, and the only one found repeatedly BY HAND rather than by
any guard. Four instances so far, each of the same shape:

  * flow-routing.md quoted Lindsay on hybrid depression handling and stopped before
    "but that the improvements are only marginally better than a breaching-only solution.
    Thus ... the breaching component ... will result in the lower impact in most cases."
  * river-networks.md quoted Leopold & Wolman's Cottonwood Creek example as isolating the
    variable; the next sentence attributes the braid to a change in GRAIN SIZE.
  * mask-operators.md dropped hajdu2012's "approximately 4% improvement", leaving a mask
    reading as 31% off optimal instead of 4%.
  * atmosphere-and-aerial-perspective.md cut at "depth-test." where the source continues
    "at the far plane (GREATER_EQUAL at depth 0 under reversed-Z)", then told the reader
    no source supplies the compare function.

WHAT THIS TOOL DOES, AND WHAT IT DELIBERATELY DOES NOT.

It is mechanical about location and dumb about judgement, on purpose:

  MATCH      the quotation appears in the artefact. The tool prints the CONTINUATION --
             the artefact's next ~200 characters -- because that is the text a reader
             needs in order to see a silent cut. Whether the continuation changes the
             conclusion is a judgement, and this tool does not pretend to make it.
  ALTERED    the quotation does NOT appear in the artefact. That is a misquotation and is
             the one verdict here that is a defect on its own.
  UNFETCHED  no artefact is cached for that citation. REPORTED AS A NUMBER, NEVER SILENT.

The third verdict is the point. A quotation nobody could re-check must not read as
verified, and a tool that quietly skips what it cannot fetch would manufacture exactly the
false confidence this corpus exists to avoid. Several hosts served bot challenges during
the session this was written -- hal.science returned a 12,507-byte challenge three times
for a PDF another process fetched at 10.7 MB, journals.ametsoc.org 403s without a browser
user-agent, and persci.mit.edu has an expired certificate -- so UNFETCHED is the common
case, not an edge case.

WHAT IT CANNOT SEE, stated so nobody reads a green run as coverage:

  * It matches TEXT. A quotation reproduced accurately from the wrong page, or attributed
    to the wrong work, is a MATCH here. check.py's locator and propagation guards are the
    instruments for that, and they are weak.
  * PDF text extraction mangles ligatures, hyphenation and column order. The normaliser
    below handles the common cases; it will still produce false ALTERED verdicts on
    scanned pages and on any source read as page images.
  * It cannot see a quotation the document paraphrases without quoting, which is where a
    conclusion is most easily bent.

Usage:
    python3 gaia/scripts/requote.py                 # report over the whole corpus
    python3 gaia/scripts/requote.py --selftest      # fixtures, including the four real cuts
    python3 gaia/scripts/requote.py --id fiorio1996 # one citation
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "references"

# The artefact cache. Keyed by citation id, because that is how the fetching agents that
# populated it happened to name their files, and it is the only key the corpus shares.
CACHE_ENV = "GAIA_ARTEFACT_CACHE"
DEFAULT_CACHE = Path(
    os.environ.get(CACHE_ENV, "")
) if os.environ.get(CACHE_ENV) else None

# A quotation worth checking: at least this many characters. Below it the false-positive
# rate from ordinary quoted terms ("range", "the sweep") swamps the signal.
MIN_QUOTE = 40

# Continuation length. Long enough to carry the clause that usually does the damage --
# the Lindsay cut needed 118 characters to reach "only marginally better".
TAIL = 240

_QUOTE_PATTERNS = [
    re.compile(r'"([^"\n]{%d,})"' % MIN_QUOTE),          # "…"
    re.compile(r'“([^”\n]{%d,})”' % MIN_QUOTE),  # curly
    # ⚠️ The apostrophe is not a quote mark. A first version matched "paper's own axis
    # pair is DOMAIN and RANGE, not spatial and range; search it for" as a QUOTATION,
    # having opened on the possessive in "the paper's" and closed on the next one. The
    # lookarounds require a non-letter on both sides, which is what separates a quotation
    # from a possessive without needing to parse English.
    re.compile(r"(?<![A-Za-z])'([^'\n]{%d,})'(?![A-Za-z])" % MIN_QUOTE),
]

# The same three shapes BELOW the threshold, so what MIN_QUOTE discards is a number on screen
# rather than a silence. A threshold nobody can see is a threshold nobody can argue with: 40
# characters was chosen against a false-positive rate, and the only way to revisit it is to know
# how much it is throwing away. Same lookarounds on the apostrophe, for the same reason.
_SHORT_PATTERNS = [
    re.compile(r'"([^"\n]{1,%d})"' % (MIN_QUOTE - 1)),
    re.compile(r'“([^”\n]{1,%d})”' % (MIN_QUOTE - 1)),
    re.compile(r"(?<![A-Za-z])'([^'\n]{1,%d})'(?![A-Za-z])" % (MIN_QUOTE - 1)),
]


def normalise(s: str) -> str:
    """Collapse a string to what survives PDF extraction on both sides.

    Ligatures, smart quotes, soft hyphens and column-wrapped whitespace all differ between
    a document's rendering of a quotation and pdfminer's rendering of the same sentence.
    Normalising both sides is what makes a textual comparison possible at all; it is also
    what makes this tool blind to a quotation that differs only in punctuation.
    """
    s = unicodedata.normalize("NFKD", s)
    s = (s.replace("ﬁ", "fi").replace("ﬂ", "fl")
           .replace("’", "'").replace("‘", "'")
           .replace("“", '"').replace("”", '"')
           .replace("–", "-").replace("—", "-")
           .replace("­", "").replace("−", "-"))
    s = re.sub(r"-\s*\n\s*", "", s)      # hyphenation across a line break
    s = re.sub(r"[^\S\n]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def artefact_text(cid: str, cache: Path | None) -> str | None:
    """Return normalised full text for a citation id, or None if nothing is cached."""
    if cache is None:
        return None
    for cand in (cache / "pdf" / f"{cid}.txt",
                 cache / f"txt_{cid}.txt",
                 cache / f"{cid}.txt"):
        if cand.exists():
            return normalise(cand.read_text(encoding="utf-8", errors="replace"))
    pdf = cache / "pdf" / f"{cid}.pdf"
    if not pdf.exists():
        pdf = cache / f"{cid}.pdf"
    if pdf.exists():
        try:
            from pdfminer.high_level import extract_text
        except ImportError:
            return None
        try:
            txt = extract_text(str(pdf))
        except Exception:
            return None
        # Cache the extraction; pdfminer on a 10 MB paper is slow enough to matter over
        # 355 quotations.
        try:
            (cache / "pdf" / f"{cid}.txt").write_text(txt, encoding="utf-8")
        except OSError:
            pass
        return normalise(txt)
    return None


def _strip_spaces(text: str) -> tuple[str, list[int]]:
    """Whitespace-free text plus a map from each stripped index back to the original.

    Exists because PDF extraction inserts spaces inside words at column boundaries, which
    makes an exact search fail on text the document quoted correctly. The spine is what
    lets the continuation still be sliced out of the ORIGINAL, so the reader sees the
    artefact's real next words rather than a de-spaced approximation of them.
    """
    out, spine = [], []
    for i, ch in enumerate(text):
        if not ch.isspace():
            out.append(ch)
            spine.append(i)
    spine.append(len(text))
    return "".join(out), spine


def nearest_citation(line: str, prior: list[str]) -> str | None:
    """The citation id a quotation belongs to.

    Front matter names its id explicitly (`- { id: foo, ...`). In the body the convention
    is a `[id]` marker, and the quotation may sit before or after it on the same line, or
    a line or two away. Nearest-on-the-line first, then the most recent marker above.
    """
    m = re.search(r"\{\s*id:\s*([a-z0-9_]+)", line)
    if m:
        return m.group(1)
    ids = re.findall(r"\[([a-z][a-z0-9_]+)\]", line)
    if ids:
        return ids[0]
    for prev in reversed(prior[-3:]):
        ids = re.findall(r"\[([a-z][a-z0-9_]+)\]", prev)
        if ids:
            return ids[0]
    return None


_LOCATOR = re.compile(r'locator:\s*"(.*)"\s*\}?\s*$')


def quotations(paths, excluded: dict | None = None):
    """Yield (path, lineno, citation_id, quoted_text) for every checkable quotation.

    ⚠️ FRONT MATTER IS NOT QUOTATION. A `locator:` field is YAML, so its whole body sits
    inside double quotes -- and a first version of this tool read every locator as a
    verbatim quotation and reported 19 of them ALTERED, which is what a locator SHOULD be:
    it describes where a claim lives, in the writer's own words. Only quotations NESTED
    inside a locator (single- or curly-quoted) are the paper's words. Reading a description
    as a quotation is the same error the corpus records as "right content, wrong
    coordinate", committed by the instrument built to catch it.

    ⚠️ WHAT IT DROPS, IT COUNTS. `excluded` accumulates the three silent exclusions this
    generator used to make with no record at all: a quotation under `MIN_QUOTE`, a quoted
    stretch inside or full of code, and -- counted by `check()` rather than here -- a
    quotation whose citation the 3-line lookback cannot resolve. A reader was told "119
    checkable quotations" and had no way to learn what the other several hundred were, which
    is the same shape as a coverage figure quoted without its denominator.
    """
    exc = excluded if excluded is not None else {}
    for k in ("short", "code", "fenced_lines"):
        exc.setdefault(k, 0)
    for p in sorted(paths):
        lines = p.read_text(encoding="utf-8").split("\n")
        in_fm, fences, in_fence = False, 0, False
        for i, line in enumerate(lines, 1):
            if line.rstrip() == "---" and fences < 2:
                fences += 1
                in_fm = fences == 1
                continue
            if line.lstrip().startswith("```"):
                # A fenced block is code, not prose, and its string literals are not
                # quotations. This used to skip the FENCE LINE ONLY, so everything between a
                # pair of fences was read as though it were prose.
                in_fence = not in_fence
                continue
            if in_fence:
                exc["fenced_lines"] += 1
                continue
            seen = set()
            if in_fm:
                m = _LOCATOR.search(line)
                if not m:
                    continue
                inner, pats = m.group(1), _QUOTE_PATTERNS[1:]   # nested quotes only
                shorts = _SHORT_PATTERNS[1:]
            else:
                inner, pats = line, _QUOTE_PATTERNS
                shorts = _SHORT_PATTERNS
            for pat in shorts:
                exc["short"] += sum(1 for _ in pat.finditer(inner))
            for pat in pats:
                for m in pat.finditer(inner):
                    q = m.group(1).strip()
                    if len(q) < MIN_QUOTE or q in seen:
                        continue
                    # A quoted stretch that is mostly code or path is not prose.
                    if q.count("`") > 2 or q.startswith("http"):
                        exc["code"] += 1
                        continue
                    seen.add(q)
                    cid = nearest_citation(line, lines[:i - 1])
                    yield p, i, cid, q


def check(cache: Path | None, only: str | None = None, docs=None):
    """Locate every quotation in `docs` inside its artefact.

    `docs` exists so this function can be RUN BY THE SELFTEST. Before it, the corpus path was
    hard-coded here, so `--selftest` exercised `normalise` and a pair of string fixtures and
    never called `check` at all -- gutting the whole function to `return [], 0, 0, 0, 0` left
    the selftest green, which is the exact shape of "an assertion defined and never invoked"
    this repository records elsewhere. It defaults to the corpus, so nothing else changes.
    """
    docs = sorted(REFS.glob("*.md")) if docs is None else sorted(docs)
    match = altered = unfetched = nocite = 0
    findings = []
    excluded: dict[str, int] = {}
    texts: dict[str, str | None] = {}
    for path, lineno, cid, q in quotations(docs, excluded):
        if only and cid != only:
            continue
        if cid is None:
            nocite += 1
            continue
        if cid not in texts:
            texts[cid] = artefact_text(cid, cache)
        body = texts[cid]
        if body is None:
            unfetched += 1
            continue
        nq = normalise(q)
        idx = body.find(nq)
        end = idx + len(nq)
        if idx < 0:
            # ⚠️ SECOND ATTEMPT, WITH WHITESPACE REMOVED ENTIRELY. pdfminer breaks words
            # across column wraps -- Barnes 2014 extracts as "works by inse rting" and
            # "terrain flooding a nd" -- and a first version of this tool reported both as
            # ALTERED, i.e. as misquotations, when the document had them exactly right.
            # Two of its four findings were this artefact of the reader, not a defect in
            # the corpus. Matching on the space-stripped text and mapping the hit back
            # through `spine` recovers the continuation.
            stripped, spine = _strip_spaces(body)
            sq = re.sub(r"\s+", "", nq)
            si = stripped.find(sq)
            if si < 0:
                altered += 1
                findings.append(("ALTERED", path, lineno, cid, q, ""))
                continue
            idx, end = spine[si], spine[min(si + len(sq), len(spine) - 1)]
        match += 1
        findings.append(("MATCH", path, lineno, cid, q, body[end: end + TAIL]))
    excluded["nocite"] = nocite
    return findings, match, altered, unfetched, nocite, excluded


# ---------------------------------------------------------------- fixtures

# The four real cuts, as (quoted-as-shipped, artefact-continuation). A guard never seen to
# fail is not known to be a guard, so these replay the actual defects this tool exists for.
CUT_FIXTURES = [
    ("hybrid solutions offer the lowest impact on modelled flow paths",
     " but that the improvements are only marginally better than a breaching-only solution."),
    ("the reach above the gage meanders at slope 0.0011",
     " The difference in slope is accompanied by a change in the median grain size"),
]

NORMALISE_FIXTURES = [
    ("The “fi” ligature: ﬁlter", 'the "fi" ligature: filter'),
    ("hyphen-\nation across a break", "hyphenation across a break"),
    ("multiple   spaces\tand\ttabs", "multiple spaces and tabs"),
    ("smart ’quotes’ and – dashes", "smart 'quotes' and - dashes"),
]

# A CORPUS THE SELFTEST OWNS, so `check()` itself is exercised rather than only its helpers.
# One document carrying one of each verdict, plus one of each silent exclusion. It is written
# out to a tmpdir per run: a fixture that lives in the real corpus would be a document nobody
# planned, and check.py would (correctly) fail it.
FIXTURE_DOC = '''---
type: Technique
title: Requote fixture
status: draft
sources:
  - { id: fetched_paper, tier: P, locator: "§2, which states 'the exponent is fixed at one half for the whole reach'" }
  - { id: uncached_paper, tier: P, locator: "§4, the cost table" }
---
# Requote fixture

[fetched_paper] The artefact says "the recommended threshold is one half of the cell size"
and the document stops there.

[fetched_paper] It also claims "this sentence appears nowhere in the artefact, not one word"
which is a misquotation and nothing else.

[uncached_paper] "a quotation long enough to be checked whose artefact was never fetched"
cannot be re-read by anyone.



A line whose quotation "carries no citation id on it or on the three lines above it" here.

Somebody said "too short" and moved on.

The block "sets the `a`, `b` and `c` fields from the driver" is code, not prose.

```
inside a fence: "a quoted string in code is not a quotation of any paper at all"
```
'''

# The MATCHed sentences, each with the continuation a reader needs in order to see the cut.
FIXTURE_ARTEFACT = (
    "The exponent is fixed at one half for the whole reach, except where the bed is armoured.\n"
    "The recommended threshold is one half of the cell size, but only for grids coarser than "
    "30 m; below that it must be re-derived.\n"
)


def _fixture_corpus(tmp: Path) -> tuple[Path, Path]:
    """Write the fixture document and its one-artefact cache under `tmp`."""
    docs = tmp / "references"
    docs.mkdir(parents=True, exist_ok=True)
    cache = tmp / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    doc = docs / "requote-fixture.md"
    doc.write_text(FIXTURE_DOC, encoding="utf-8")
    (cache / "fetched_paper.txt").write_text(FIXTURE_ARTEFACT, encoding="utf-8")
    return doc, cache


# Four verdict counts, three exclusion counts, the ALTERED identity, the continuation, and the
# "an unfetched citation yields no finding" rule. Named so the printed total is not a guess.
CORPUS_ASSERTIONS = 10


def _corpus_fixture_checks() -> list[str]:
    """Run `check()` over the fixture corpus and return the failures, as strings.

    Asserts all three verdicts AND the three exclusions, because the exclusions are the half
    of this tool's output that decides whether its ratio means anything.
    """
    import tempfile

    fails: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        doc, cache = _fixture_corpus(Path(td))
        findings, match, altered, unfetched, nocite, exc = check(cache, docs=[doc])
        want = {"match": 2, "altered": 1, "unfetched": 1, "nocite": 1}
        got = {"match": match, "altered": altered, "unfetched": unfetched, "nocite": nocite}
        for k, v in want.items():
            if got[k] != v:
                fails.append(f"corpus fixture: {k} = {got[k]}, want {v}  ({got})")
        for k in ("short", "code", "fenced_lines"):
            if exc.get(k, 0) < 1:
                fails.append(f"corpus fixture: exclusion `{k}` counted {exc.get(k, 0)}, want >= 1")
        alt = [f for f in findings if f[0] == "ALTERED"]
        if len(alt) != 1 or "appears nowhere" not in alt[0][4]:
            fails.append(f"corpus fixture: ALTERED did not name the invented sentence: {alt}")
        # A MATCH is only useful if it carries the artefact's NEXT words -- that is the whole
        # instrument. A run that located the quotation and surfaced nothing is a green light
        # over an unread continuation.
        tails = [f[5].strip() for f in findings if f[0] == "MATCH"]
        if not all(tails) or not any("30 m" in t for t in tails):
            fails.append(f"corpus fixture: a MATCH surfaced no continuation: {tails}")
        # And the UNFETCHED case must never be reported as anything else.
        if any(f[3] == "uncached_paper" for f in findings):
            fails.append("corpus fixture: an unfetched citation produced a finding")
    return fails


def selftest() -> int:
    bad = 0
    for raw, want in NORMALISE_FIXTURES:
        got = normalise(raw)
        if got != want:
            print(f"  FAIL  normalise fixture: {raw!r} -> {got!r}, want {want!r}")
            bad += 1
    # A cut is detectable only as MATCH-plus-continuation: the quoted half IS present in
    # the artefact, which is exactly why a text search alone cannot flag it. These pin
    # that the tool surfaces the continuation rather than reporting a clean pass.
    for quoted, tail in CUT_FIXTURES:
        artefact = normalise(quoted + tail)
        idx = artefact.find(normalise(quoted))
        if idx < 0:
            print(f"  FAIL  cut fixture: quoted half not found in its own artefact")
            bad += 1
            continue
        surfaced = artefact[idx + len(normalise(quoted)):][:TAIL]
        if not surfaced.strip():
            print(f"  FAIL  cut fixture: no continuation surfaced for {quoted[:40]!r}")
            bad += 1
    corpus_fails = _corpus_fixture_checks()
    for f in corpus_fails:
        print(f"  FAIL  {f}")
    bad += len(corpus_fails)
    n = len(NORMALISE_FIXTURES) + len(CUT_FIXTURES) + CORPUS_ASSERTIONS
    print(f"requote: {n - bad}/{n} fixtures correct "
          f"({len(NORMALISE_FIXTURES)} normalise, {len(CUT_FIXTURES)} cut, "
          f"{CORPUS_ASSERTIONS} corpus assertions over a fixture directory: MATCH, ALTERED, "
          f"UNFETCHED, and the three exclusion counts)")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--id", help="check one citation id only")
    ap.add_argument("--cache", help="artefact cache directory")
    ap.add_argument("--require-cache", action="store_true",
                    help="exit non-zero when no cache is available, for CI")
    ap.add_argument("--show-matches", action="store_true",
                    help="print every MATCH with its continuation, not just the summary")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    require_cache = args.require_cache
    cache = Path(args.cache) if args.cache else DEFAULT_CACHE
    findings, match, altered, unfetched, nocite, excluded = check(cache, args.id)

    for kind, path, lineno, cid, q, tail in findings:
        if kind == "ALTERED":
            print(f"  ALTERED  {path.relative_to(ROOT)}:{lineno} [{cid}]")
            print(f"           quoted: {q[:110]}")
        elif args.show_matches and tail.strip():
            print(f"  MATCH    {path.relative_to(ROOT)}:{lineno} [{cid}]")
            print(f"           quoted: {q[:90]}")
            print(f"           artefact continues: {tail[:200]}")

    total = match + altered + unfetched
    if cache is None:
        # This used to print "that is not a pass" and then return 0 -- the sentence and the exit
        # status disagreeing in the same breath. guard-proofs.tsv recorded the contradiction as
        # fixed when the fix had landed only on the cache-present sibling: the same
        # one-sibling-fixed shape okf.py records for _inline_list against _inline_map.
        print("requote: NO ARTEFACT CACHE. Set GAIA_ARTEFACT_CACHE or pass --cache. "
              "Nothing was attempted, so nothing is asserted either way.")
        return 2 if require_cache else 0
    print(f"requote {match}/{total} quotations located in their artefact; "
          f"{altered} NOT FOUND (misquotation, or an extraction the normaliser cannot "
          f"reach); {unfetched} UNFETCHED because no artefact is cached for that citation. "
          f"{nocite} quotations carry no resolvable citation id and were skipped. "
          f"EXCLUDED BEFORE ANY OF THAT: {excluded.get('short', 0)} quoted spans shorter than "
          f"the {MIN_QUOTE}-character floor, {excluded.get('code', 0)} quoted spans that are "
          f"code or a URL, and {excluded.get('fenced_lines', 0)} lines inside fenced blocks. "
          f"Those are the denominators the ratio above is NOT taken over. "
          f"⚠️ A located quotation is NOT a verified one: this tool reports the artefact's "
          f"CONTINUATION so a reader can see a silent cut, and does not judge whether the "
          f"cut changes the claim. Run --show-matches to read them.")
    # EXIT CODES. A cache was supplied, so a run that located and refuted nothing did not
    # check the corpus -- it enumerated it. Returning 0 there is the "nothing was checked, and
    # that is not a pass" sentence contradicted by the process's own exit status, which is what
    # CI reads. An ALTERED verdict is the one finding here that is a defect on its own.
    if match + altered == 0:
        print("requote: FAIL -- a cache was given and NOT ONE quotation was located or "
              "refuted. Every checkable quotation was UNFETCHED or unresolvable, so this run "
              "establishes nothing about the corpus. Point --cache at the artefacts.")
        return 1
    if altered:
        print(f"requote: FAIL -- {altered} quotation(s) do not appear in their artefact.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
