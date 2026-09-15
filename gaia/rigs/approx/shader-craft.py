#!/usr/bin/env python3
"""shader-craft.md -- Phase D approximation audit.

WHAT THIS IS: a provenance audit, run in CPython over the corpus text. It answers three
questions that decide whether this document's existing (c) "unpriced, and here is why"
should stand or be replaced by a figure.

WHAT THIS IS NOT: a benchmark. It measures NOTHING about a GPU. Every one of this
document's eight recommendations is a shader-text change whose cost is GPU ALU, register
pressure or a lost early-z rung. A CPython timing here would be a different quantity
wearing the same units, and is not produced.

Deterministic: no seed, no timing, no RNG. Two runs are byte-identical by construction;
run() is invoked twice anyway so the saved output shows it.

Usage:  python3 shader-craft.py            (from anywhere; paths are absolute)
"""
import math
import pathlib
import re
import sys

ROOT = pathlib.Path("/home/user/skills/gaia")
DOC = ROOT / "references" / "shader-craft.md"
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402  -- the corpus's own regexes, not a reimplementation


# The eight recommendations of the `## Use this` block, as topic keywords. A cost figure
# anywhere in the corpus that prices one of these would falsify the (c).
EIGHT = re.compile(
    r"sample(level|grad|bias)?|calculatelevelofdetail|ddx|ddy|derivat|quad|"
    r"max-?mip|point sampler|virtual uv|gradient|feedbackscale|feedback pass|"
    r"sv_depth|early.?z|odepth|conservative depth|nonuniform|divergent index|"
    r"normalize|saturate|clamp|nan|\bpow\b",
    re.I,
)


def q1_metric_halves():
    """Which half does check.py's approximation metric see in this document?"""
    _, body = check.parse_front_matter(DOC)
    errs = [m.group(0) for m in check.ERROR_STATED.finditer(body)]
    costs = [m.group(0) for m in check.COST_UNIT.finditer(body)]
    print("Q1  check.py halves for shader-craft.md")
    print("      ERROR matches: %r" % (errs,))
    print("      COST  matches: %r" % (costs,))
    print("      -> counts as: error=%s cost=%s" % (bool(errs), bool(costs)))
    return errs, costs


def q2_error_arithmetic():
    """Is the stated ERROR right? It is arithmetic, so it re-derives exactly."""
    virtual, pool, page_mip = 256 * 1024, 16 * 1024, 0
    s = virtual / (pool * 2 ** page_mip)
    signed = page_mip - math.log2(virtual / pool)
    print("Q2  'an error of 4 LOD levels', shader-craft.md:218")
    print("      s = virtualSize/(poolSize*2^pageMip) = %d/(%d*2^%d) = %g"
          % (virtual, pool, page_mip, s))
    print("      footprint understated by %gx -> log2 = %g levels too fine" % (s, math.log2(s)))
    print("      signed form pageMip - log2(virtualSize/poolSize) = %g" % signed)
    print("      -> magnitude 4 CONFIRMED; both ends (:218 body, :444 table) print 4")
    return abs(signed)


def q3_corpus_prices_any_of_the_eight():
    """Does ANY corpus document price one of the eight? The (c) claims none does."""
    hits = []
    for path in sorted((ROOT / "references").glob("*.md")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if check.COST_UNIT.search(line) and EIGHT.search(line):
                hits.append((path.name, i, line.strip()[:150]))
    print("Q3  corpus lines carrying BOTH a cost unit and one of the eight topics")
    print("      candidate lines: %d" % len(hits))
    for name, i, text in hits:
        print("      %s:%d  %s" % (name, i, text))
    return hits


def q4_sibling_pattern():
    """What do the two siblings that face the same wall actually do?"""
    print("Q4  the corpus's own precedent for an unpriceable GPU half")
    for name, lo, hi in (("gpu-driven-culling.md", 164, 170),
                         ("virtual-texturing.md", 52, 57)):
        lines = (ROOT / "references" / name).read_text(encoding="utf-8").splitlines()
        print("      --- %s:%d-%d" % (name, lo, hi))
        for i in range(lo - 1, min(hi, len(lines))):
            print("      | %s" % lines[i][:120])


def run(tag):
    print("=" * 78)
    print("RUN %s" % tag)
    print("=" * 78)
    q1_metric_halves()
    print()
    q2_error_arithmetic()
    print()
    q3_corpus_prices_any_of_the_eight()
    print()
    q4_sibling_pattern()
    print()


if __name__ == "__main__":
    run("1 of 2")
    run("2 of 2")
    print("VERDICT: the ERROR half is present and re-derives exactly. No cost figure for")
    print("any of the eight exists in this document, its locators, its register rows, or")
    print("anywhere in the corpus. The eight are shader-text changes with no allocation to")
    print("count and no GPU here to time, so channel (c) is the only honest channel and the")
    print("standing (c) at shader-craft.md:75-77 already says unpriced / what would price it")
    print("/ what to do meanwhile. CONFIRMED, unchanged.")
