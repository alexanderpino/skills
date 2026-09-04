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


def quotations(paths):
    """Yield (path, lineno, citation_id, quoted_text) for every checkable quotation.

    ⚠️ FRONT MATTER IS NOT QUOTATION. A `locator:` field is YAML, so its whole body sits
    inside double quotes -- and a first version of this tool read every locator as a
    verbatim quotation and reported 19 of them ALTERED, which is what a locator SHOULD be:
    it describes where a claim lives, in the writer's own words. Only quotations NESTED
    inside a locator (single- or curly-quoted) are the paper's words. Reading a description
    as a quotation is the same error the corpus records as "right content, wrong
    coordinate", committed by the instrument built to catch it.
    """
    for p in sorted(paths):
        lines = p.read_text(encoding="utf-8").split("\n")
        in_fm, fences = False, 0
        for i, line in enumerate(lines, 1):
            if line.rstrip() == "---" and fences < 2:
                fences += 1
                in_fm = fences == 1
                continue
            if line.lstrip().startswith("```"):
                continue
            seen = set()
            if in_fm:
                m = _LOCATOR.search(line)
                if not m:
                    continue
                inner, pats = m.group(1), _QUOTE_PATTERNS[1:]   # nested quotes only
            else:
                inner, pats = line, _QUOTE_PATTERNS
            for pat in pats:
                for m in pat.finditer(inner):
                    q = m.group(1).strip()
                    if len(q) < MIN_QUOTE or q in seen:
                        continue
                    # A quoted stretch that is mostly code or path is not prose.
                    if q.count("`") > 2 or q.startswith("http"):
                        continue
                    seen.add(q)
                    cid = nearest_citation(line, lines[:i - 1])
                    yield p, i, cid, q


def check(cache: Path | None, only: str | None = None):
    docs = [p for p in REFS.glob("*.md")]
    match = altered = unfetched = nocite = 0
    findings = []
    texts: dict[str, str | None] = {}
    for path, lineno, cid, q in quotations(docs):
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
    return findings, match, altered, unfetched, nocite


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
    n = len(NORMALISE_FIXTURES) + len(CUT_FIXTURES)
    print(f"requote: {n - bad}/{n} fixtures correct "
          f"({len(NORMALISE_FIXTURES)} normalise, {len(CUT_FIXTURES)} cut)")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--id", help="check one citation id only")
    ap.add_argument("--cache", help="artefact cache directory")
    ap.add_argument("--show-matches", action="store_true",
                    help="print every MATCH with its continuation, not just the summary")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    cache = Path(args.cache) if args.cache else DEFAULT_CACHE
    findings, match, altered, unfetched, nocite = check(cache, args.id)

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
        print("requote: NO ARTEFACT CACHE. Set GAIA_ARTEFACT_CACHE or pass --cache. "
              "Nothing was checked, and that is not a pass.")
        return 0
    print(f"requote {match}/{total} quotations located in their artefact; "
          f"{altered} NOT FOUND (misquotation, or an extraction the normaliser cannot "
          f"reach); {unfetched} UNFETCHED because no artefact is cached for that citation. "
          f"{nocite} quotations carry no resolvable citation id and were skipped. "
          f"⚠️ A located quotation is NOT a verified one: this tool reports the artefact's "
          f"CONTINUATION so a reader can see a silent cut, and does not judge whether the "
          f"cut changes the claim. Run --show-matches to read them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
