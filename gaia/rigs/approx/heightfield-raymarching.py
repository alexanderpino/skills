#!/usr/bin/env python3
"""heightfield-raymarching.md: the `## Use this` recommendation, GATED against its own page.

WHAT THIS IS.  The fence at :61-82 is what a reader pastes, and until now nothing checked it.
This file runs it and asserts what the page says about it.  Every expected value below is
PARSED OUT OF THE DOCUMENT at run time, anchored on PROSE and never on a number, and a figure
or a sentence that has gone missing is a FAIL -- `_page`/`_require` exit non-zero rather than
skip.  Where the page states one figure at two ends, BOTH are parsed and they are asserted to
agree with each other: 4/3 at :41 and again at :225-226, 2⁻²² at :112 and again at :285 and
:131-132, 2048 m at :110-111 and again at :285, the refinement range at :70 and again at
:49-50.  A correction landing at one end only is this corpus's most-recorded defect.

⚠️ TWO RIGS, ONE FILE, AND WHY.  `registers/corrections.tsv:227` names THIS PATH as the
harness behind the page's memory and error figures ("summed over the arrays actually built by
the harness at gaia/rigs/approx/heightfield-raymarching.py, seed 20260910").  `rigs/README.md`
says in as many words that a register row citing a path that no longer exists is a claim
nobody can check.  So the measurement harness is preserved here verbatim, under `--measure`,
and the gate is what runs by default:

    python3 heightfield-raymarching.py              the gate   (stdlib only; exit 0 or 1)
    python3 heightfield-raymarching.py --measure    the harness corrections.tsv:227 cites
                                                    (CPython + NumPy; measures, asserts
                                                    nothing, always exits 0)

The two share nothing: every gate name is `_`-prefixed and the gate never imports NumPy.  The
sibling gates in this corpus live beside their measurement rigs in a separate directory
(`rigs/materials/mask-to-material.py` next to `rigs/approx/mask-to-material.py`); this one was
assigned this path, so it is merged instead of overwriting.  Splitting it out later is a
one-line move.

WHAT THE GATE ASSERTS, AND WHAT IT REFUSES TO.  The page's own measurements at :47-53 -- 515
rays, 398 hits, ±21/±11/±2.6 mm, 57 m median, ±0.64 m -- are NOT gated AS ABSOLUTE VALUES
and cannot be: :54 gives the field's FORM, `h = a·sin(kx) + b·sin(k′z)`, and never a, b, k
or k′, so no rig can rebuild that ray set, and the register records the printed
millimetres as rounded UP from the run, i.e. as bounds.  Asserting a bound one-sidedly is precisely the shape this corpus keeps
catching: walk ±11 mm to ±110 mm and `worst < claimed` stays green.  What that same sentence
states EXACTLY -- zero missed, zero spurious, written as words -- is reproduced on this rig's
own field and gated at tolerance zero.  Everything else the gate declines to check is printed
at the end, with its reason, including one claim whose two sides move together under any edit
and therefore cannot be gated at all.

NO PARAMETER IS TAKEN FROM THE NUMBER UNDER TEST.  The grid this rig marches over is 2^_N_EXP
with _N_EXP a literal; its a, b, k, k′ are literals; its ray count, seed, scan width and caps
are literals.  The only page-derived inputs are the ones that are not themselves the quantity
being checked: the 512² at :54 (input to the memory formula, whose RATIO is what is checked),
the refinement counts at :49-50 and :70, the 1e-4 and 2048 m at :110-111, and the exponent 22.

HALTING.  No loop anywhere has a data-dependent bound.  Every `for` is over a literal range or
over an integer parsed from the page (the mip-chain depth, the refinement count); the march's
`while` is bounded by the literal _STATE_CAP and reports a livelock as a PROVEN CYCLE -- a
repeated (t, level) state -- never as a timeout; the closed-form reference's cell walk is
bounded by the literal _CELL_CAP and overrunning it is a FAIL.

Exit 0 when everything reproduces, non-zero otherwise.
"""
import math
import pathlib
import random
import re
import struct
import sys
from fractions import Fraction

try:                       # the preserved measurement harness only; the gate never uses it
    import numpy as np
except ImportError:        # pragma: no cover
    np = None

_DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "heightfield-raymarching.md"
_ok = True
_SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
        "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
          "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "third": 3}


def _load():
    if not _DOC.exists():
        sys.exit(f"cannot find {_DOC} -- run this rig from inside the repo")
    return _DOC.read_text(encoding="utf-8")


_BODY = _load()


def _page(pattern, what, group=1):
    """Parse one group out of the page. A missing anchor is a FAIL, never a skip."""
    m = re.search(pattern, _BODY)
    if not m:
        sys.exit(f"ANCHOR GONE -- the page no longer states {what} (pattern {pattern!r})")
    return m.group(group)


def _require(pattern, what):
    """Assert the page still SAYS something. A vanished sentence is a FAIL, not a skip."""
    if not re.search(pattern, _BODY):
        sys.exit(f"ANCHOR GONE -- the page no longer states {what} (pattern {pattern!r})")
    return True


def _num(pattern, what, group=1):
    return float(_page(pattern, what, group))


def _int(pattern, what, group=1):
    return int(_page(pattern, what, group))


def _sup(pattern, what, group=1):
    return int("".join(_SUP.get(c, c) for c in _page(pattern, what, group)))


def _word(pattern, what, group=1):
    w = _page(pattern, what, group).lower()
    if w not in _WORDS:
        sys.exit(f"the page writes {what} as {w!r}, which is not a number this rig knows")
    return _WORDS[w]


def _fail(msg):
    global _ok
    _ok = False
    print(f"FAIL  {msg}")


def _check(label, got, want, tol=0.0):
    global _ok
    if isinstance(got, (int, float, Fraction)) and isinstance(want, (int, float, Fraction)):
        good = abs(got - want) <= tol
    else:
        good = got == want
    _ok = _ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got!r}, page says {want!r}")
    return good


def _agree(label, a, b):
    global _ok
    good = a == b
    _ok = _ok and good
    print(f"{'PASS' if good else 'FAIL'}  BOTH ENDS {label}: {a!r} and {b!r}")
    return good


# ── fp32, by bit pattern ─────────────────────────────────────────────────────────────────
def _f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def _i32(x):
    return struct.unpack("<I", struct.pack("<f", _f32(x)))[0]


def _from_i32(b):
    return struct.unpack("<f", struct.pack("<I", b & 0xFFFFFFFF))[0]


def _ulp32(x):
    x = _f32(x)
    return _from_i32(_i32(x) + 1) - x


def _ulps32(a, b):
    return _i32(b) - _i32(a)


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 1 -- what the pyramid costs.  Exact rational arithmetic, tolerance ZERO.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_cost():
    print("\n── 1. the pyramid's memory, at :41-46 / :225-226 / :262-263 ─────────────────")
    n_rig = _int(r"(\d+)² samples of `h = ", "the resolution its own rig ran at (:54)")
    if n_rig <= 0 or (n_rig & (n_rig - 1)):
        _fail(f"the page's rig resolution {n_rig} is not a power of two; the "
              f"`2ⁿ×2ⁿ` formula at :45-46 does not apply to it")
        return
    n = n_rig.bit_length() - 1

    # the closed form the page prints, with ITS OWN integers parsed out of it
    fa, fb, fc = (int(x) for x in re.search(
        r"`\(4\^\(n\+(\d+)\) − (\d+)\)/\((\d+)·4\^n\)` of the base for a 2ⁿ×2ⁿ field",
        _BODY).groups()) if re.search(
        r"`\(4\^\(n\+(\d+)\) − (\d+)\)/\((\d+)·4\^n\)` of the base for a 2ⁿ×2ⁿ field",
        _BODY) else sys.exit("ANCHOR GONE -- the closed form at :45-46")

    # The structure the page prescribes, BUILT: level 0 is the 3x3-dilated max -- a SECOND
    # full-resolution array -- and the levels above it halve.  Loop bound: n, parsed.
    size, cells = n_rig, [n_rig * n_rig]
    for _ in range(n):
        size //= 2
        cells.append(size * size)
    if size != 1:
        _fail(f"the mip chain over {n_rig}² did not reach 1×1 in {n} reductions")
    base = Fraction(n_rig * n_rig)
    ratio = Fraction(sum(cells), 1) / base
    upper = Fraction(sum(cells[1:]), 1) / base

    closed = Fraction(4 ** (n + fa) - fb, fc * 4 ** n)
    _check(f"pyramid/field over the {n_rig}² field it built, against the page's own "
           f"(4^(n+{fa}) − {fb})/({fc}·4^n) at n={n}", ratio, closed)

    p, q = (int(x) for x in re.search(r"\*\*(\d+)/(\d+) of the field it is built over\*\*",
                                      _BODY).groups())
    p2, q2 = (int(x) for x in re.search(r"plus the pyramid's (\d+)/(\d+)\s*\n?of it",
                                        _BODY).groups())
    _agree("state the pyramid's size (:41 and :225-226)", (p, q), (p2, q2))
    _check(f"({p}/{q} − built ratio) against the page's own remainder 1/({fc}·4^n)",
           Fraction(p, q) - ratio, Fraction(fb, fc * 4 ** n))

    third = _word(r"only the levels above it sum to the (\w+)\.", "what the upper levels sum to")
    _check(f"(1/{third} − the levels above level 0) against 1/({fc}·4^n) -- "
           f"'only the levels above it sum to the {'third' if third == 3 else third}'",
           Fraction(1, third) - upper, Fraction(fb, fc * 4 ** n))
    _check("level 0 is a SECOND full-resolution array (cells at level 0 / base cells)",
           Fraction(cells[0]) / base, Fraction(1))

    b16 = _num(r"Over an R16 field at \*\*(\d+) bytes per cell\*\*", "the R16 cell size (:44)")
    bpyr = _num(r"\*\*([\d.]+) bytes per cell\*\* of pyramid", "the pyramid's bytes/cell")
    bres = _num(r"\*\*([\d.]+) bytes per cell\*\* resident", "the resident bytes/cell")
    mult = _num(r"— ([\d.]+)× the field, not the field itself\*\*", "the RT-section multiple")
    _check(f"{b16:g} bytes/cell × the built ratio", round(b16 * float(ratio), 2), bpyr)
    _check(f"{b16:g} bytes/cell × (1 + the built ratio)",
           round(b16 * (1 + float(ratio)), 2), bres)
    _check("1 + the built ratio, against the procedural-AABB end at :262-263",
           round(1 + float(ratio), 2), mult)


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 2 -- the fp32 constants the termination argument rests on.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_fp32():
    print("\n── 2. the relative advance in fp32, at :77 / :110-113 / :285 ────────────────")
    lit = _page(r"t\s+= max\(t, tExitNode\) \* \(1\.0f \+ ([\d.e+-]+)f\)",
                "the relative-advance literal in the fence (:77)")
    e_prose = _sup(r"`max\(t, tExitNode\)·\(1 \+ 2⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+)\)` moves",
                   "the relative advance as a power of two (:112)")
    e_table = _sup(r"\| `t = max\(t, tExitNode\)·\(1 \+ 2⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+)\)`",
                   "the same advance in the failure table (:285)")
    e_zero = _sup(r"the relative advance is\s*\n?`0·\(1\+2⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+)\) = 0`",
                  "the advance in the t = 0 argument (:131-132)")
    _agree("write the same exponent (:112 and :285)", e_prose, e_table)
    _agree("write the same exponent (:112 and :131-132)", e_prose, e_zero)
    _check(f"the fence's literal {lit!r} against 2^-{e_prose} in fp32",
           _f32(float(lit)), _f32(2.0 ** -e_prose))
    norm = lambda v: re.sub(r"e([+-])0*(\d)", r"e\1\2", v)
    _check(f"2^-{e_prose} printed to as many significant digits as the fence's literal",
           norm("%.9g" % (2.0 ** -e_prose)), norm(lit))

    lo = _int(r"moves (\d+)–\d+ ULP \*at every positive normal", "the low ULP count (:112)")
    hi = _int(r"moves \d+–(\d+) ULP \*at every positive normal", "the high ULP count (:112)")
    k = 1.0 + 2.0 ** -e_prose
    seen_lo, seen_hi, bad = 99, -1, 0
    for e in range(-126, 128):                      # every fp32 normal binade: 254, a literal
        for j in range(32):                         # a fixed mantissa sample, not exhaustive
            t = _f32(math.ldexp(1.0 + j / 32.0, e))
            d = _f32(t * k)
            if not d > t:
                bad += 1
                continue
            u = _ulps32(t, d)
            seen_lo, seen_hi = min(seen_lo, u), max(seen_hi, u)
    if bad:
        _fail(f"the advance failed to increase t on {bad} of the sampled magnitudes")
    _check(f"smallest ULP step over 254 binades × 32 mantissas", seen_lo, lo)
    _check(f"largest ULP step over 254 binades × 32 mantissas", seen_hi, hi)

    nudge = _num(r"`t \+ ([\d.e+-]+)` is a \*no-op in fp32 for\s*\n?every `t ≥ \d+ m`\*",
                 "the absolute nudge (:110-111)")
    thr = _num(r"`t \+ [\d.e+-]+` is a \*no-op in fp32 for\s*\n?every `t ≥ (\d+) m`\*",
               "the distance past which it is a no-op (:110-111)")
    thr_tbl = _num(r"absorbed by fp32 ULP past (\d+) m", "the same distance in the failure "
                                                         "table (:285)")
    _agree("state the same no-op distance (:110-111 and :285)", thr, thr_tbl)
    first = None
    for e in range(-20, 61):                        # a literal sweep of binades
        t = _f32(math.ldexp(1.0, e))
        if _f32(t + nudge) == t:
            first = t
            break
    _check(f"smallest fp32 magnitude where `t + {nudge:g}` is a no-op", first, thr)
    just_below = _from_i32(_i32(thr) - 1)
    if _f32(just_below + nudge) == just_below:
        _fail(f"`t + {nudge:g}` is ALREADY a no-op one ULP below {thr:g} m, so the page's "
              f"threshold is not the threshold")
    else:
        print(f"PASS  and NOT a no-op one ULP below it ({just_below!r}), so {thr:g} m is the "
              f"exact threshold, not a round number near it")
    _check(f"ULP at {thr:g} m in fp32", float("%.2g" % _ulp32(thr)),
           _num(r"\(ULP ([\d.e+-]+)\)", "the ULP it prints there (:111)"))

    pairs = re.search(r"\((\d+) mm at (\d+) km, (\d+) mm at (\d+) km", _BODY)
    if not pairs:
        sys.exit("ANCHOR GONE -- the two `N mm at N km` instantiations at :113")
    for mm, km in ((int(pairs.group(1)), int(pairs.group(2))),
                   (int(pairs.group(3)), int(pairs.group(4)))):
        t = _f32(km * 1000.0)
        _check(f"the step `max(t,·)·(1 + 2^-{e_prose})` takes at {km} km, in mm",
               round((_f32(t * k) - t) * 1000.0), mm)


# ═════════════════════════════════════════════════════════════════════════════════════════
# the field, the pyramid and the block itself.
#
# a, b, k and k' are NOT on the page -- :54 gives the FORM `h = a·sin(kx) + b·sin(k′z)` and
# nothing else -- so these four are this rig's own, stated here and never presented as a
# reproduction of the page's 515-ray run.  The grid is 2^_N_EXP, a literal: nothing checked
# below is derived from it.
# ═════════════════════════════════════════════════════════════════════════════════════════
_N_EXP = 6
_NG = 1 << _N_EXP
_S0 = 1.0
_AMP_X, _KX = 40.0, 2.0 * math.pi / 16.0
_AMP_Z, _KZ = 15.0, 2.0 * math.pi / 8.0
_MAPMAX = _AMP_X + _AMP_Z
_MAXDIST = 120.0
_EPS_T = 1.0 / 1024.0
_SEED = 424242
_CELL_CAP = 20000
_STATE_CAP = 20000


def _analytic(x, z):
    return _AMP_X * math.sin(_KX * x) + _AMP_Z * math.sin(_KZ * z)


def _samples():
    """Heights at texel CENTRES, per :146-147.  Periodic, so `floor` wraps exactly."""
    return [[_analytic((i + 0.5) * _S0, (j + 0.5) * _S0) for i in range(_NG)]
            for j in range(_NG)]


def _dilate3(a):
    n = len(a)
    return [[max(a[(j + dj) % n][(i + di) % n] for dj in (-1, 0, 1) for di in (-1, 0, 1))
             for i in range(n)] for j in range(n)]


def _reduce2(a, op=max):
    n = len(a) // 2
    return [[op(a[2 * j][2 * i], a[2 * j][2 * i + 1],
                a[2 * j + 1][2 * i], a[2 * j + 1][2 * i + 1]) for i in range(n)]
            for j in range(n)]


def _pyramid(h, apron="level0", op=max):
    """`dilate the base samples 3×3 and max-reduce *that*` (:148-150)."""
    lvl0 = _dilate3(h) if apron in ("level0", "perlevel") else [r[:] for r in h]
    out = [lvl0]
    for _ in range(_N_EXP):                         # literal bound
        nxt = _reduce2(out[-1], op)
        if apron == "perlevel":
            nxt = _dilate3(nxt)
        out.append(nxt)
    if apron == "toponly":
        out[-1] = _dilate3(out[-1])
    return out


def _surface(h, x, z):
    """Bilinear reconstruction from samples at texel centres (:147, :151-153)."""
    u, v = x / _S0 - 0.5, z / _S0 - 0.5
    i, j = math.floor(u), math.floor(v)
    p, q = u - i, v - j
    i0, j0, i1, j1 = i % _NG, j % _NG, (i + 1) % _NG, (j + 1) % _NG
    a = h[j0][i0] + (h[j0][i1] - h[j0][i0]) * p
    b = h[j1][i0] + (h[j1][i1] - h[j1][i0]) * p
    return a + (b - a) * q


def _corners(x, z):
    u, v = x / _S0 - 0.5, z / _S0 - 0.5
    i, j = math.floor(u), math.floor(v)
    return [(j % _NG, i % _NG), (j % _NG, (i + 1) % _NG),
            ((j + 1) % _NG, i % _NG), ((j + 1) % _NG, (i + 1) % _NG)]


def _node_max(pyr, level, x, z):
    s = _S0 * (1 << level)
    n = len(pyr[level])
    return pyr[level][math.floor(z / s) % n][math.floor(x / s) % n]


def _exit_distance(o, d, t, level):
    """DDA to the node boundary.  +inf for an axis the ray does not move along -- which is
    the column-locked picking ray of :120-122, and why the clamp exists."""
    s = _S0 * (1 << level)
    out = math.inf
    for ax in (0, 2):
        if d[ax] == 0.0:
            continue
        c = math.floor((o[ax] + d[ax] * t) / s)
        bound = (c + (1 if d[ax] > 0 else 0)) * s
        out = min(out, (bound - o[ax]) / d[ax])
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
# THE FENCE ITSELF, PINNED AS TEXT -- what the transcription below is a transcription OF.
#
# ⚠️ THE DEEPEST HOLE THIS RIG HAD, found by an independent attack and named rather than
# hidden.  `_march` below transcribes the fence's ALGORITHM by hand, so an edit to the
# fence's CODE never reached it.  Gutting five of the page's own lines -- dropping the
# `min(…, tExit)` clamp at :66, flipping the descending-ray guard at :71, deleting the
# `min(level+1, coarsestMip)` cap at :78, deleting the step-cap belt at :80 and turning
# `level--` at :75 into `level++` -- left this rig at 64 PASS, exit 0.  It was measuring its
# own remembered copy of the block, never the block on the page.
#
# The remedy is the one `rigs/approx/surface-and-scale-space.py` §0b uses: pin every
# load-bearing line of the fence as TEXT and assert it, then DERIVE the knobs `_march`
# actually turns from the parsed block, so the rig executes the page's form and not a
# remembered one.  A line edited away then fails twice over -- its own text assertion, which
# names the line, and the gate that line exists to hold up.
#
# Numbers inside the fence are deliberately NOT part of these text patterns: the relative
# step's `2.38418579e-7f` and the refine range's `5-8` are parsed and checked as VALUES by
# gates 2 and 6.  A text assertion that swallowed them would turn a legitimate correction
# into a spurious failure, and would be the typed-in expectation wearing a new hat.
# ═════════════════════════════════════════════════════════════════════════════════════════
_FENCE_BLOCK = _page(r"(?s)```\n(level = coarsestMip; t = tEnter; steps = 0.*?)\n```",
                     "the `## Use this` fence at :61-82")


def _fence(pattern, what, group=1):
    """Parse one group out of the FENCE. A line that has gone is a FAIL, never a skip."""
    m = re.search(pattern, _FENCE_BLOCK, re.M)
    if not m:
        sys.exit(f"ANCHOR GONE -- the fence at :61-82 no longer carries {what} "
                 f"(pattern {pattern!r})")
    return m.group(group)


# Every line the transcription below depends on, with what it is load-bearing FOR.
_FENCE_LINES = (
    (r"^level = coarsestMip; t = tEnter; steps = 0\b",
     "the entry state `level = coarsestMip; t = tEnter` (:62)"),
    (r"// tEnter = max\(EPS, ·\) — NOT max\(0, ·\)",
     "the STRICT `max(EPS, ·)` clamp on tEnter (:62) -- gate 4c's whole precondition"),
    (r"tExit: ray ∩ \[mapMin, mapMax\]",
     "what tExit is (:62) -- the slab entry gate 4c calls negative"),
    (r"^ +// both FINITE and NON-NEGATIVE",
     "that tEnter and tExit are BOTH FINITE AND NON-NEGATIVE (:63) -- an infinite tExit "
     "puts the level-0 refine back on the unbounded interval :286 exists to remove"),
    (r"^while \(t < tExit\) \{",
     "the loop condition `while (t < tExit)` (:64)"),
    (r"^  node      = texelAt\(rayPos\(t\), level\)",
     "the explicit-LOD node fetch (:65)"),
    (r"// explicit-LOD fetch: SampleLevel or Load, never Sample",
     "`never Sample` on the texelAt line (:65) -- the language rule :84-92 spends a "
     "paragraph on, and the reason a filtered tap breaks the skip test's bound"),
    (r"^  tExitNode = min\(exitDistance\(node, ray\), tExit\)",
     "the node exit CLAMPED to tExit (:66) -- without it a column-locked ray bisects an "
     "unbounded interval (:118-123, :286)"),
    (r"^  if \(min\(rayHeight\(t\), rayHeight\(tExitNode\)\) < node\.maxH\) \{",
     "the INTERVAL predicate (:69) -- the asymmetry :94-105 is about"),
    (r"^    if \(level == 0\) return refine\(t, tExitNode\)",
     "the level-0 refine (:70)"),
    (r"^    if \(rayDir\.y < 0\) \{",
     "the DESCENDING-ray guard on the tCross advance (:71) -- 'Ascending and horizontal "
     "rays simply enter the candidate span at `t`' (:105)"),
    (r"^      tCross = tWhereRayHeightEquals\(node\.maxH, ray\)",
     "the crossing solve (:72)"),
    (r"^      t = max\(t, tCross\)",
     "the `max` that keeps the tCross advance monotone (:73) -- the termination invariant "
     "at :129-130 is 'each iteration strictly increases `t` or decreases `level`'"),
    (r"^    level--",
     "the DESCEND (:75) -- `level` must fall here or the invariant at :129-130 is false"),
    (r"^    t     = max\(t, tExitNode\) \* \(1\.0f \+ ",
     "the RELATIVE skip advance `max(t, tExitNode)·(1 + ε)` (:77) -- :107-117 and :285"),
    (r"// RELATIVE step — never `\+ eps`",
     "that the skip advance is RELATIVE and never `+ eps` (:77)"),
    (r"^    level = min\(level\+1, coarsestMip\)",
     "the pop-up CLAMPED to coarsestMip (:78) -- an unclamped `level+1` walks off the "
     "pyramid the page just priced in gate 1"),
    (r"^  if \(\+\+steps > stepCap\) return miss",
     "the step-cap BELT (:80) -- ':285 a step cap only converts the hang into a slow "
     "frame', so it is a belt and not the termination argument"),
    (r"// a belt, NOT the termination argument",
     "that the step cap is a belt and NOT the termination argument (:80)"),
    (r"^return miss",
     "the fall-through miss (:82)"),
)

# ── the knobs `_march` turns, DERIVED from the block above rather than remembered ────────
# `_RHS` takes the right-hand side of a fence assignment, stopping at the line's `//`
# comment, so what is compared below is the CODE the page publishes and nothing else.
_RHS = r"\s*([^/\n]+?)\s*(?://|$)"
_F_EXITNODE = _fence(r"^  tExitNode =" + _RHS, "the node-exit assignment (:66)")
_F_GUARD_OP = _fence(r"^    if \(rayDir\.y (\S+) 0\) \{", "the tCross guard's comparison (:71)")
_F_TCROSS = _fence(r"^      t =" + _RHS, "the tCross assignment (:73)")
_F_DESCEND = _fence(r"^    level(--|\+\+)", "the descend step (:75)")
_F_POPUP = _fence(r"^    level =" + _RHS, "the pop-up assignment (:78)")
_F_CLAMP = _F_EXITNODE == "min(exitDistance(node, ray), tExit)"
_F_BELT = re.search(r"^  if \(\+\+steps > stepCap\) return miss", _FENCE_BLOCK, re.M) is not None

_GUARD_OPS = {"<": lambda v: v < 0.0, ">": lambda v: v > 0.0,
              "<=": lambda v: v <= 0.0, ">=": lambda v: v >= 0.0}
if _F_GUARD_OP not in _GUARD_OPS:
    sys.exit(f"the fence guards the tCross advance with `rayDir.y {_F_GUARD_OP} 0`, which is "
             f"not a comparison this rig can execute")
_F_GUARD = _GUARD_OPS[_F_GUARD_OP]
_F_DESCEND_DELTA = -1 if _F_DESCEND == "--" else +1
_F_MIP_CLAMP = _F_POPUP.startswith("min(")
_F_TCROSS_MAX = _F_TCROSS.startswith("max(")


def gate_fence():
    print("\n── 0. the fence at :61-82, pinned as TEXT ───────────────────────────────────")
    for pat, what in _FENCE_LINES:
        if re.search(pat, _FENCE_BLOCK, re.M):
            print(f"PASS  the fence still carries {what}")
        else:
            _fail(f"the fence no longer carries {what} -- everything `_march` runs below is "
                  f"a transcription of a block the page NO LONGER RECOMMENDS, so every "
                  f"green line under it is measuring the wrong algorithm")
    print(f"      knobs taken from the block, not remembered: clamp to tExit={_F_CLAMP}, "
          f"tCross guard `rayDir.y {_F_GUARD_OP} 0`, tCross assign `{_F_TCROSS}`, "
          f"descend `level{_F_DESCEND}`, pop-up `{_F_POPUP}`, belt={_F_BELT}")


# ── the block at :61-82, transcribed ─────────────────────────────────────────────────────
_SCAN = 8            # a literal


def _refine(h, o, d, t0, t1, iters):
    """`refine(t, tExitNode)` -- `binary or secant refine, 5-8 iterations` (:70).

    ⚠️ TWO DEVIATIONS from the block, both forced and both reported rather than hidden:

      * the block writes `return refine(t, tExitNode)`, which returns UNCONDITIONALLY.  A
        refine that finds no crossing must fall through and keep marching, or the traversal
        reports a hit on a level-0 node the interval test only said a hit was POSSIBLE in.
      * `binary refine` presupposes a BRACKET, and the endpoints of a level-0 span need not
        bracket: inside one texel a bilinear surface can dip below the ray and come back, so
        f(t) > 0 and f(tExitNode) > 0 with a real crossing between.  A short fixed scan finds
        the bracket first.  Without it this rig read a genuine first hit as a later one.
    """
    f = lambda t: (o[1] + d[1] * t) - _surface(h, o[0] + d[0] * t, o[2] + d[2] * t)
    flo, fhi = f(t0), f(t1)
    if flo <= 0.0:
        return t0
    lo, hi = t0, t1
    if not (fhi <= 0.0):
        prev_t, prev_f, found = t0, flo, False
        for si in range(1, _SCAN + 1):              # literal bound
            tt = t0 + (t1 - t0) * si / _SCAN
            ft = f(tt)
            if prev_f > 0.0 >= ft:
                lo, hi, found = prev_t, tt, True
                break
            prev_t, prev_f = tt, ft
        if not found:
            return None
    for _ in range(iters):     # bound: `iters`, parsed from the page
        mid = 0.5 * (lo + hi)
        if f(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _march(h, pyr, o, d, t_enter, t_exit, iters=6, *, advance="relative", nudge=1e-4,
           descend="interval", fp32=False, literal_return=False):
    """The fence at :61-82.  `advance` and `descend` select the page's own counterfactuals.

    The clamp, the tCross guard, the tCross assignment, the descend step and the pop-up cap
    are NOT transcribed here: they are `_F_CLAMP`, `_F_GUARD`, `_F_TCROSS_MAX`,
    `_F_DESCEND_DELTA` and `_F_MIP_CLAMP`, parsed out of the fence above.  Edit those lines
    on the page and this function changes what it runs.

    Halting: the while loop is bounded by _STATE_CAP, a literal; a livelock is reported as a
    PROVEN CYCLE (a repeated (t, level) state), never as a timeout.
    """
    coarsest = len(pyr) - 1
    level, t, steps = coarsest, t_enter, 0
    seen, spans = set(), []
    prev = None
    invariant_broken = None
    while t < t_exit:
        if fp32:
            t = _f32(t)
        key = (struct.pack("<d", t), level)
        if key in seen:
            return ("CYCLE", steps, spans, invariant_broken)
        seen.add(key)
        node_max = _node_max(pyr, level, o[0] + d[0] * t, o[2] + d[2] * t)
        t_exit_node = _exit_distance(o, d, t, level)
        if _F_CLAMP:                    # `min(exitDistance(node, ray), tExit)` (:66), PARSED
            t_exit_node = min(t_exit_node, t_exit)
        if not math.isfinite(t_exit_node):
            # :118-123 and :286: unclamped, a column-locked ray hands `refine` an UNBOUNDED
            # interval.  Reported as such, never bisected -- the page's own defect, surfaced.
            return ("UNBOUNDED", steps, spans, invariant_broken)
        h_t, h_e = o[1] + d[1] * t, o[1] + d[1] * t_exit_node
        if descend == "interval":
            candidate = min(h_t, h_e) < node_max
        else:                                        # the widely-circulated crossing form
            if d[1] < 0.0:
                candidate = ((node_max - o[1]) / d[1]) < t_exit_node
            else:
                candidate = h_t < node_max and False  # no crossing => it skips
        t_before, level_before = t, level
        if candidate:
            if level == 0:
                spans.append((t, t_exit_node))
                hit = _refine(h, o, d, t, t_exit_node, iters)
                if hit is not None:
                    return ("HIT", hit, spans, invariant_broken)
                if literal_return:
                    # `if (level == 0) return refine(t, tExitNode)` returns UNCONDITIONALLY.
                    return ("HIT-NO-BRACKET", t, spans, invariant_broken)
            else:
                if d[1] != 0.0 and _F_GUARD(d[1]):     # `if (rayDir.y < 0)` (:71), PARSED
                    t_cross = (node_max - o[1]) / d[1]
                    # `t = max(t, tCross)` (:73), PARSED -- or a bare `t = tCross`
                    t = max(t, t_cross) if _F_TCROSS_MAX else t_cross
                level += _F_DESCEND_DELTA             # `level--` (:75), PARSED
                if not 0 <= level <= coarsest:
                    return ("OFF-PYRAMID", steps, spans, invariant_broken)
        if (not candidate) or level == level_before:
            if advance == "relative":
                t = max(t, t_exit_node) * (1.0 + 2.0 ** -22)
            elif advance == "absolute":
                t = max(t, t_exit_node) + nudge
            else:                                    # the page's `t = tExitNode` (:108)
                t = t_exit_node
            if fp32:
                t = _f32(t)
            # `level = min(level+1, coarsestMip)` (:78), PARSED
            level = min(level + 1, coarsest) if _F_MIP_CLAMP else level + 1
            if level > coarsest:
                return ("OFF-PYRAMID", steps, spans, invariant_broken)
        if not (t > t_before or level < level_before):
            invariant_broken = (t_before, level_before, t, level)
        if level > level_before and not t > t_before:
            invariant_broken = (t_before, level_before, t, level)
        steps += 1
        if steps > _STATE_CAP:
            return ("CAP", steps, spans, invariant_broken)
    return ("MISS", steps, spans, invariant_broken)


def _reference(h, o, d, t0, t1):
    """First crossing of the SAME bilinear surface, in closed form per cell.  Halting: the
    cell walk is bounded by _CELL_CAP, a literal, and overrunning it is a FAIL."""
    t = t0
    for _ in range(_CELL_CAP):
        if not t < t1:
            return None
        x, z = o[0] + d[0] * t, o[2] + d[2] * t
        i, j = math.floor(x / _S0 - 0.5), math.floor(z / _S0 - 0.5)
        tx = math.inf if d[0] == 0 else (((i + 1.5) * _S0) - o[0]) / d[0] if d[0] > 0 else \
            (((i + 0.5) * _S0) - o[0]) / d[0]
        tz = math.inf if d[2] == 0 else (((j + 1.5) * _S0) - o[2]) / d[2] if d[2] > 0 else \
            (((j + 0.5) * _S0) - o[2]) / d[2]
        t_cell = min(tx, tz, t1)
        h00 = h[j % _NG][i % _NG]
        h10 = h[j % _NG][(i + 1) % _NG]
        h01 = h[(j + 1) % _NG][i % _NG]
        h11 = h[(j + 1) % _NG][(i + 1) % _NG]
        c1, c2 = h10 - h00, h01 - h00
        c3 = h00 - h10 - h01 + h11
        p0 = (o[0] - (i + 0.5) * _S0) / _S0
        q0 = (o[2] - (j + 0.5) * _S0) / _S0
        pd, qd = d[0] / _S0, d[2] / _S0
        a2 = -(c3 * pd * qd)
        a1 = d[1] - (c1 * pd + c2 * qd + c3 * (p0 * qd + q0 * pd))
        a0 = o[1] - (h00 + c1 * p0 + c2 * q0 + c3 * p0 * q0)
        # ⚠️ the NUMERICALLY STABLE form.  `(-a1 ± sqrt(disc))/(2·a2)` is catastrophic here:
        # a2 = -(c3·pd·qd) goes to ~1e-16 on an axis-aligned ray while a1 is O(1), and the
        # subtraction of two nearly equal quantities then returns a root off by 0.1 m.  That
        # was this rig's own bug, and it showed up as the march DISAGREEING with the page.
        roots = []
        if a2 == 0.0:
            if a1 != 0.0:
                roots.append(-a0 / a1)
        else:
            disc = a1 * a1 - 4 * a2 * a0
            if disc >= 0.0:
                qq = -0.5 * (a1 + math.copysign(math.sqrt(disc), a1 if a1 != 0.0 else 1.0))
                roots.append(qq / a2)
                if qq != 0.0:
                    roots.append(a0 / qq)
        got = sorted(r for r in roots if t - 1e-12 <= r <= t_cell + 1e-12)
        if got:
            return max(got[0], t0)
        t = t_cell * (1.0 + 2.0 ** -22) if t_cell > 0 else t_cell + 1e-9
    _fail("the closed-form reference overran its literal cell cap")
    return None


def _reference_selfcheck(h, rs, ref):
    """The closed-form reference, checked against a dense scan of the SAME surface.

    Without this the gate cannot tell a wrong reference from a wrong page, and a wrong
    reference is what it had: see the note in _reference.  Halting: the scan step and the
    ray length are literals, so the loop count is fixed.
    """
    step, bad_late, bad_root, bad_ghost = 0.02, 0, 0, 0
    for (o, d, t0, t1, _k), rt in zip(rs, ref):
        f = lambda t: (o[1] + d[1] * t) - _surface(h, o[0] + d[0] * t, o[2] + d[2] * t)
        hi = t1 if rt is None else rt
        n = int((hi - t0) / step)
        prev, crossed = f(t0), False
        for s_i in range(1, n + 1):
            cur = f(t0 + s_i * step)
            if prev > 0.0 >= cur:
                crossed = True
                break
            prev = cur
        if rt is None:
            bad_ghost += crossed
        else:
            bad_late += crossed
            bad_root += abs(f(rt)) > 1e-6
    _check("reference roots that are not crossings of the same surface", bad_root, 0)
    _check("references that skipped an EARLIER crossing (dense 20 mm scan)", bad_late, 0)
    _check("rays the reference called a miss that the dense scan crosses", bad_ghost, 0)


def _rays(h):
    rng = random.Random(_SEED)
    out = []

    def push(o, dv, kind):
        L = math.sqrt(sum(c * c for c in dv))
        dv = [c / L for c in dv]
        if dv[1] == 0.0:
            return
        # tExit: the ray ∩ [mapMin, mapMax], capped finite per the fence comment at :62-63
        t_slab = ((_MAPMAX if dv[1] > 0 else -_MAPMAX) - o[1]) / dv[1]
        t_exit = min(t_slab, _MAXDIST)
        if t_exit <= _EPS_T:
            return
        if (o[1] + dv[1] * _EPS_T) - _surface(h, o[0] + dv[0] * _EPS_T,
                                              o[2] + dv[2] * _EPS_T) <= 0.0:
            return          # an origin inside the terrain is outside this kernel's contract
        out.append((o, dv, _EPS_T, t_exit, kind))

    for _ in range(40):
        o = [rng.uniform(0, _NG), rng.uniform(_MAPMAX * 0.6, _MAPMAX), rng.uniform(0, _NG)]
        yaw, pitch = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(-40, -3))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "primary")
    for _ in range(40):
        x, z = rng.uniform(0, _NG), rng.uniform(0, _NG)
        o = [x, _surface(h, x, z) + 0.05, z]
        yaw, pitch = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(4, 30))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "ascending")
    for _ in range(20):
        x, z = rng.uniform(0, _NG), rng.uniform(0, _NG)
        o = [x, _surface(h, x, z) + 0.5, z]
        yaw, pitch = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(-0.8, 0.8))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "grazing")
    for _ in range(10):
        push([rng.uniform(0, _NG), _MAPMAX, rng.uniform(0, _NG)], [0.0, -1.0, 0.0], "picking")
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 3 -- registration: the apron, and what it is conservative against.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_registration(h):
    print("\n── 3. the apron and the reduce, at :145-153 / :290 ──────────────────────────")
    _require(r"dilate the base\s*\n?samples 3×3 and max-reduce \*that\*, which stays "
          r"conservative at every level", "that the 3×3 dilate stays conservative (:148-150)")
    _require(r"an un-aproned reduce is not conservative there",
          "that an un-aproned reduce is NOT conservative (:153-155)")
    _require(r"Max-\*\*height\*\* reduce for the ray pyramid, min-\*\*height\*\* reduce for the\s*\n?"
          r"occluder proxy", "the two opposite reduces (:290)")

    good = _pyramid(h, "level0")
    bare = _pyramid(h, "none")
    mini = _pyramid(h, "level0", op=min)
    if len(good) != _N_EXP + 1 or len(good[0]) != _NG:
        _fail(f"the prescribed pyramid is {len(good)} levels with a {len(good[0])}² level 0")
    else:
        print(f"PASS  the prescribed build gives {len(good)} levels, level 0 {len(good[0])}² "
              f"-- a second full-resolution array, which is GATE 1's 4/3")

    SUB = 4                                          # a literal
    pts = [(i + 0.5) / SUB for i in range(_NG * SUB)]
    bad_good = bad_bare = bad_min = 0
    worst_bare = 0.0
    for z in pts:
        for x in pts:
            cs = _corners(x, z)
            for level in range(len(good)):
                s = _S0 * (1 << level)
                jj, ii = math.floor(z / s) % len(good[level]), math.floor(x / s) % len(good[level])
                gm, bm, mm = good[level][jj][ii], bare[level][jj][ii], mini[level][jj][ii]
                for (cj, ci) in cs:                  # EXACT: stored float against stored float
                    if not gm >= h[cj][ci]:
                        bad_good += 1
                    if not bm >= h[cj][ci]:
                        bad_bare += 1
                        worst_bare = max(worst_bare, h[cj][ci] - bm)
                    if not mm >= h[cj][ci]:
                        bad_min += 1
    _check("bracketing samples the 3×3-dilated max-reduce fails to bound, over "
           f"{len(pts)}² positions × {len(good)} levels", bad_good, 0)
    if bad_bare > 0:
        print(f"PASS  the UN-aproned reduce fails to bound {bad_bare} of them, by up to "
              f"{worst_bare:.2f} m -- the page's 'not conservative there'")
    else:
        _fail("the un-aproned reduce bounded every bracketing sample, so this field cannot "
              "demonstrate the page's claim at :153-155 -- the gate is inert, not green")
    if bad_min > 0:
        print(f"PASS  a MIN-height reduce fails to bound {bad_min} of them -- :290's "
              f"'two pyramids', not one shared")
    else:
        _fail("a min-height reduce bounded every sample, contradicting :290")


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 4 -- the block, RUN: termination, and the page's own counterfactuals.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_termination(h, pyr, rs):
    print("\n── 4. termination, at :107-134 / :285 ───────────────────────────────────────")
    _require(r"each iteration strictly increases `t` or\s*\n?decreases `level`, and `level` "
          r"only rises on the branch that increases `t`",
          "the structural termination invariant (:129-130)")
    cyc = broke = unbounded = off_pyr = 0
    for (o, d, t0, t1, _k) in rs:
        r = _march(h, pyr, o, d, t0, t1, fp32=True)
        if r[0] in ("CYCLE", "CAP"):
            cyc += 1
        if r[0] == "UNBOUNDED":
            unbounded += 1
        if r[0] == "OFF-PYRAMID":
            off_pyr += 1
        if r[3] is not None:
            broke += 1
    _check(f"rays of {len(rs)} that livelock under the fence as written, in fp32", cyc, 0)
    _check("iterations that violated the page's own invariant", broke, 0)
    # the two outcomes the fence's OWN lines exist to prevent, run from the PARSED block
    # (see gate 0): drop `min(…, tExit)` at :66 and a column-locked ray bisects an unbounded
    # interval; drop `min(level+1, coarsestMip)` at :78, or write `level++` at :75, and the
    # march walks off the top of the pyramid gate 1 just priced.
    _check("rays handed an UNBOUNDED refine interval -- the fence's `min(exitDistance(node, "
           "ray), tExit)` at :66", unbounded, 0)
    _check("rays that marched off the pyramid -- the fence's `level--` at :75 and "
           "`level = min(level+1, coarsestMip)` at :78", off_pyr, 0)

    # (a) `t = tExitNode`, the page's :108-110 and failure-table :285
    _require(r"`t = tExitNode` lands the ray exactly on a node boundary", "the bare-assign hang")
    # the same fix cell, at its OTHER end: :285 says the belt CONVERTS the hang, never
    # removes it, which is why :80's `stepCap` is a belt and not the termination argument.
    _require(r"a step cap only converts the hang into a slow frame",
             "that a step cap only CONVERTS the hang into a slow frame (:285)")
    bare = sum(1 for (o, d, t0, t1, _k) in rs
               if _march(h, pyr, o, d, t0, t1, advance="bare", fp32=True)[0] == "CYCLE")
    if bare > 0:
        print(f"PASS  `t = tExitNode` is a PROVEN CYCLE on {bare} of {len(rs)} rays "
              f"(repeated (t, level) state, not a timeout)")
    else:
        _fail("`t = tExitNode` livelocked on no ray, so this rig cannot see the hang the "
              "page's whole termination paragraph is about")

    # (b) the absolute nudge, above and below the distance the page names.  The geometry is
    #     held FIXED and only the ray PARAMETER is moved: shifting the origin back by T along
    #     d leaves o + d*t identical, so the only thing that changes is the magnitude of t.
    nudge = _num(r"`t \+ ([\d.e+-]+)` is a \*no-op in fp32 for", "the absolute nudge")
    thr = _num(r"is a \*no-op in fp32 for\s*\n?every `t ≥ (\d+) m`\*", "the no-op distance")
    cyclers = [(o, d, t0, t1) for (o, d, t0, t1, _k) in rs
               if _march(h, pyr, o, d, t0, t1, advance="bare", fp32=True)[0] == "CYCLE"]
    counts = {}
    for tag, shift in (("far", 4.0 * thr), ("near", thr / 8.0)):
        n_cyc = 0
        for (o, d, t0, t1) in cyclers:
            os_ = [o[a] - d[a] * shift for a in (0, 1, 2)]
            r = _march(h, pyr, os_, d, t0 + shift, t1 + shift,
                       advance="absolute", nudge=nudge, fp32=True)
            n_cyc += (r[0] == "CYCLE")
        counts[tag] = n_cyc
    if counts["far"] > 0 and counts["near"] == 0:
        print(f"PASS  `t + {nudge:g}` is a PROVEN CYCLE on {counts['far']} of {len(cyclers)} "
              f"rays at t ≈ {4 * thr:g} m and on {counts['near']} of them at t ≈ {thr / 8:g} m "
              f"-- ':285 hides it near the camera and is absorbed past {thr:g} m'")
    else:
        _fail(f"`t + {nudge:g}` cycled on {counts['far']} rays far and {counts['near']} near; "
              f"the page says absorbed past {thr:g} m and hidden below it")

    # (c) tEnter = 0 and tEnter < 0 -- the precondition at :129-134
    _require(r"So clamp `tEnter` with `max\(EPS, ·\)` for a small positive\s*\n?`EPS`, "
          r"\*\*never `max\(0, ·\)`\*\*", "the strict clamp (:133-134)")
    _require(r"tEnter = max\(EPS, ·\) — NOT max\(0, ·\)",
          "the same clamp in the fence's own comment (:62)")
    _require(r"\*\*Termination is then structural, given `tEnter > 0`\*\*",
          "the STRICT precondition (:129)")
    e = _sup(r"the relative advance is\s*\n?`0·\(1\+2⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+)\) = 0`",
             "the t = 0 advance")
    _check(f"0·(1+2^-{e}) in fp32", _f32(0.0 * (1.0 + 2.0 ** -e)), 0.0)
    # the origin sits on x = z = 0, a node boundary at EVERY level, and travels back into
    # negative x and z, so `exitDistance` is 0 at every level: `tExitNode == t == 0`.
    o, d = [0.0, _MAPMAX, 0.0], [-0.6, -0.5, -0.62]
    L = math.sqrt(sum(c * c for c in d))
    d = [c / L for c in d]
    at_zero = _march(h, pyr, o, d, 0.0, 60.0, fp32=True)
    at_eps = _march(h, pyr, o, d, _EPS_T, 60.0, fp32=True)
    if at_zero[0] == "CYCLE" and at_eps[0] in ("HIT", "MISS"):
        print(f"PASS  a ray entered at t = 0 on a node boundary is a PROVEN CYCLE, and the "
              f"same ray entered at max(EPS, ·) terminates ({at_eps[0]}) -- :131-134, "
              f"both halves")
    else:
        _fail(f"the t = 0 precondition did not bite: at 0 -> {at_zero[0]}, "
              f"at EPS -> {at_eps[0]}; the page says cycles, then terminates")

    _require(r"at negative `t` the multiply moves \*away\* from zero,\s*\n?i\.e\. backward, "
          r"to an exact fixed point", "the negative-t fixed point (:132-133)")
    back = all(_f32(tn * (1.0 + 2.0 ** -e)) < tn
               for tn in (-1.0, -3584.0, -2.5e-3, -1e5))
    tn = _f32(-3584.0)
    fixed = _f32(tn * (1.0 + 2.0 ** -e))
    if back and _f32(fixed) == _f32(_f32(fixed)) and _f32(max(fixed, tn) * (1.0 + 2.0 ** -e)) == fixed:
        print(f"PASS  negative t moves BACKWARD and `max(t, tExitNode)·(1+2^-{e})` sits on an "
              f"exact fixed point ({fixed!r} from tExitNode {tn!r})")
    else:
        _fail("negative t did not move backward to an exact fixed point")

    # the textbook slab entry the page says the caller hands in
    _require(r"the textbook slab entry for an origin inside the map is negative",
          "the reason the clamp exists (:134)")
    o = [_NG * 0.5, 0.0, _NG * 0.5]
    d = [0.0, -1.0, 0.0]
    t_near = ((_MAPMAX if d[1] < 0 else -_MAPMAX) - o[1]) / d[1]
    if t_near < 0.0:
        print(f"PASS  the slab entry for an origin inside the map is {t_near:.3f} < 0")
    else:
        _fail(f"the slab entry for an interior origin came out {t_near:.3f}, not negative")


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 5 -- the clamp: the column-locked ray, and the NaN the clamp does NOT remove.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_clamp(h, pyr, rs):
    print("\n── 5. the clamp, at :120-128 / :286 ─────────────────────────────────────────")
    _require(r"never\s*\n?leaves its column, so `exitDistance` is `\+inf`",
          "the column-locked ray's infinite exitDistance (:120-122)")
    _require(r"a \*\*column-locked picking\s*\n?ray never leaves its column\*\*, so its level-0 "
          r"span is the rest of the ray", "the level-0 span of a picking ray (:51-53)")
    # The SAME claim at its other end, the failure table at :286.  Both halves of that cell
    # are load-bearing and neither was anchored: an attack walked `+inf` to `-inf` and
    # "unbounded" to "bounded" and this rig stayed green.
    _require(r"`exitDistance` is `\+inf` for a column-locked ray, so `refine\(t, ∞\)` bisects "
             r"an unbounded interval",
             "the failure table's own `+inf` and its UNBOUNDED refine interval (:286)")
    _require(r"`tExitNode = min\(exitDistance\(\.\.\.\), tExit\)` before the predicate — "
             r"which makes the refine interval finite, not short",
             "the failure table's own clamp prescription, and that it buys FINITE not SHORT "
             "(:286)")
    _require(r"a reciprocal-form DDA can make `exitDistance` NaN, which the clamp does not "
             r"remove", "that the clamp does NOT remove the NaN (:286)")
    bad = checked = no_span = off = 0
    for (o, d, t0, t1, kind) in rs:
        if kind != "picking":
            continue
        checked += 1
        for level in range(len(pyr)):
            if _exit_distance(o, d, t0, level) != math.inf:
                bad += 1
        r = _march(h, pyr, o, d, t0, t1)
        if not r[2]:
            no_span += 1
            continue
        # every level-0 span this ray handed to refine IS the rest of the ray, exactly
        for (t_at, t_end) in r[2]:
            if t_end != t1:
                off += 1
    _check(f"levels where a column-locked ray's exitDistance was finite ({checked} rays × "
           f"{len(pyr)} levels)", bad, 0)
    _check("column-locked rays that reached level 0 with no span recorded", no_span, 0)
    _check("level-0 spans of a column-locked ray that were NOT the rest of the ray "
           "(tExitNode != tExit) -- ':51-53, its level-0 span is the rest of the ray'", off, 0)

    _require(r"`\(bound − o\.x\)·invD = 0·∞ = NaN`, and `min\(NaN, tExit\)` is still NaN",
          "the reciprocal-form NaN (:125-126)")
    inv_d = 1.0 / 0.0 if False else math.inf      # invD = 1/0, as the page writes it
    prod = 0.0 * inv_d                            # (bound − o.x)·invD with bound == o.x
    if prod == prod:
        _fail("0·∞ did not produce NaN here, so :125-126 cannot be reproduced")
    else:
        print("PASS  `(bound − o.x)·invD` = 0·∞ is NaN")

    def min_nan_prop(a, b):
        return float("nan") if (a != a or b != b) else min(a, b)

    def min_num(a, b):
        return b if a != a else (a if b != b else min(a, b))

    t_exit = 100.0
    prop, num = min_nan_prop(prod, t_exit), min_num(prod, t_exit)
    # the predicate at :69 with tExitNode = NaN.  `min(rayHeight(t), NaN) < node.maxH`
    h_t, node_max = 5.0, 10.0
    pred_prop = min_nan_prop(h_t, h_t + prop) < node_max     # NaN < x is False -> SKIP
    pred_num = min(h_t, h_t + (0.0 if num != num else 0.0)) < node_max  # finite -> DESCEND
    if prop == prop or num != t_exit:
        _fail(f"the two min semantics did not split as :126-128 says: propagating gave "
              f"{prop!r}, minNum gave {num!r}")
    elif pred_prop or not pred_num:
        _fail(f"the NaN branch did not land where :126-128 says: propagating predicate "
              f"{pred_prop}, minNum predicate {pred_num}")
    else:
        print("PASS  `min(NaN, tExit)` is still NaN under a NaN-propagating min, the "
              "predicate is FALSE and the branch SKIPS ('reports clear sight'); an IEEE "
              "minNum returns tExit and the branch DESCENDS -- :126-128, both halves")


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 6 -- the predicate.  Interval test against the crossing test.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_predicate(h, pyr, rs):
    print("\n── 6. the predicate, at :67-69 / :95-105 / :291 ─────────────────────────────")
    _require(r"That is correct\s*\n?\*only for a descending ray\*", "the asymmetry (:96-97)")
    _require(r"the traversal \*\*skips a node that can contain a hit\*\*",
          "what the crossing form does (:100-101)")
    _require(r"Ascending and horizontal rays simply enter the candidate span at `t`",
             "what the interval form does instead (:105)")
    # the predicate itself, at BOTH ends: the fence line at :69 and the fix column at :291
    p_fence = _page(r"if \((min\(rayHeight\(t\), rayHeight\(tExitNode\)\) < node\.maxH)\) \{",
                    "the interval predicate in the fence (:69)")
    p_table = _page(r"\| Descend on the interval test `([^`]+)`",
                    "the interval predicate in the failure table (:291)")
    _agree("write the same predicate (:69 and :291)", p_fence, p_table)

    # (a) exhaustive over a fixed grid of node geometries -- no page number involved, the
    #     page's SENTENCE is the expectation.
    dis_desc = dis_asc = wrong_way = 0
    for hy in range(-20, 21):                       # literal bounds
        for dy_i in (-8, -4, -1, 0, 1, 4, 8):
            for nm in range(-20, 21):
                h_t, dy, node_max = hy * 1.0, dy_i * 1.0, nm * 1.0
                span = 3.0
                h_e = h_t + dy * span
                interval = min(h_t, h_e) < node_max
                if dy < 0:
                    crossing = ((node_max - h_t) / dy) < span
                else:
                    crossing = False
                if interval != crossing:
                    if dy < 0:
                        dis_desc += 1
                    else:
                        dis_asc += 1
                    if crossing and not interval:
                        wrong_way += 1
    _check("disagreements on DESCENDING rays ('correct only for a descending ray')",
           dis_desc, 0)
    if dis_asc > 0:
        print(f"PASS  {dis_asc} disagreements on ascending/horizontal rays, and in every one "
              f"the interval form descends where the crossing form skips")
    else:
        _fail("the two predicates never disagreed on an ascending ray, so :95-105 has no "
              "instance here -- the gate is inert, not green")
    _check("disagreements where the CROSSING form descends and the interval form skips "
           "(the page says the error is one-directional)", wrong_way, 0)

    # (b) the whole march: the page's ZERO missed and ZERO spurious, written as words
    z1 = _word(r"the traversal returns\s*\n?\*\*(\w+) missed and \w+ spurious hits\*\*",
               "the missed-hit count (:48-49)")
    z2 = _word(r"the traversal returns\s*\n?\*\*\w+ missed and (\w+) spurious hits\*\*",
               "the spurious-hit count (:48-49)")
    fence_lo = _int(r"refine\((?:[^)]*)\)\s*// binary or secant refine, (\d+)-\d+ iterations",
                    "the low refinement count in the fence (:70)")
    fence_hi = _int(r"// binary or secant refine, \d+-(\d+) iterations",
                    "the high refinement count in the fence (:70)")
    mid = _int(r"\*\*±[\d.]+ mm\s*\n?at (\d+) bisections\*\*",
               "the bisection count the prose bolds (:49-50)")
    lo_hi = re.search(r"\(±[\d.]+ mm at (\d+), ±[\d.]+ mm at (\d+)\)", _BODY)
    if not lo_hi:
        sys.exit("ANCHOR GONE -- the two other refinement counts at :50")
    prose = sorted({mid, int(lo_hi.group(1)), int(lo_hi.group(2))})
    if not prose:
        sys.exit("ANCHOR GONE -- the refinement counts the prose instantiates (:49-50)")
    _agree("the fence's refinement range and the prose's own counts (low)",
           fence_lo, min(prose))
    _agree("the fence's refinement range and the prose's own counts (high)",
           fence_hi, max(prose))
    # …and its THIRD end, the failure table at :286, which was unanchored: an attack moved
    # `5–8` there to `40–90` and every gate stayed green.  A correction landing at one end
    # only is this corpus's most-recorded defect.
    fix_lo = _int(r"refine to a tolerance rather than to a fixed (\d+)–\d+ bisections",
                  "the low refinement count in the failure table (:286)")
    fix_hi = _int(r"refine to a tolerance rather than to a fixed \d+–(\d+) bisections",
                  "the high refinement count in the failure table (:286)")
    _agree("the refinement range in the fence (:70) and in the failure table (:286), low",
           fence_lo, fix_lo)
    _agree("the refinement range in the fence (:70) and in the failure table (:286), high",
           fence_hi, fix_hi)

    ref = [_reference(h, o, d, t0, t1) for (o, d, t0, t1, _k) in rs]
    _reference_selfcheck(h, rs, ref)
    print(f"      ray set: {len(rs)} rays, {sum(1 for r in ref if r is not None)} of them "
          f"hits under the closed-form reference (this rig's field, NOT the page's)")
    for iters in prose:
        missed = spurious = late = 0
        for (o, d, t0, t1, _k), rt in zip(rs, ref):
            r = _march(h, pyr, o, d, t0, t1, iters=iters)
            got = r[1] if r[0] == "HIT" else None
            if rt is not None and got is None:
                missed += 1
            elif rt is None and got is not None:
                spurious += 1
            elif rt is not None and got is not None:
                # a hit at the WRONG crossing is a missed first hit wearing a hit's clothes.
                # The only residual the block allows is the refinement's own: span/2^k.
                span = r[2][-1][1] - r[2][-1][0]
                if abs(got - rt) > span / 2.0 ** iters + 1e-9:
                    late += 1
        _check(f"missed hits at {iters} bisections", missed, z1)
        _check(f"spurious hits at {iters} bisections", spurious, z2)
        _check(f"hits at {iters} bisections that are NOT the first crossing "
               f"(beyond the refinement's own span/2^{iters})", late, z1)

    # the crossing form, on the same rays: the page says it MISSES
    missed_x = 0
    for (o, d, t0, t1, kind), rt in zip(rs, ref):
        if kind != "ascending" or rt is None:
            continue
        r = _march(h, pyr, o, d, t0, t1, descend="crossing")
        if r[0] != "HIT":
            missed_x += 1
    if missed_x > 0:
        print(f"PASS  the crossing form misses {missed_x} ascending-ray hits the interval "
              f"form finds -- ':291 the ascending shadow ray skips nodes that hold the "
              f"occluder'")
    else:
        _fail("the crossing form missed nothing on this ray set, so :291 has no instance "
              "here -- the gate is inert, not green")


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 7 -- the depth token, derived from the two depth conventions.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_depth():
    print("\n── 7. the conservative-depth token, at :232-240 ─────────────────────────────")
    rev = _page(r"which is `(SV_Depth\w+)` under \*\*reversed-Z", "the reversed-Z token")
    std = _page(r"and `(SV_Depth\w+)` under standard depth\*\*", "the standard-depth token")
    _require(r"the promise is \*never nearer than\s*\n?the rasterized proxy\*", "the promise")
    _require(r"It holds only if the proxy is a \*\*max-height\*\* surface", "the proxy condition")
    # the proxy is a max-height hull, so it is at or NEARER than the hit: proxy_dist <= hit
    near_plane, far_plane = 1.0, 1000.0
    proxy_dist, hit_dist = 40.0, 55.0                # literals: the hull is nearer
    z_std = lambda t: (t - near_plane) / (far_plane - near_plane)
    z_rev = lambda t: 1.0 - z_std(t)
    want_rev = "SV_DepthLessEqual" if z_rev(hit_dist) <= z_rev(proxy_dist) else \
               "SV_DepthGreaterEqual"
    want_std = "SV_DepthLessEqual" if z_std(hit_dist) <= z_std(proxy_dist) else \
               "SV_DepthGreaterEqual"
    _check("the token 'never nearer than the proxy' needs under reversed-Z", want_rev, rev)
    _check("the token it needs under standard depth", want_std, std)
    if rev == std:
        _fail("the page gives the same token for both depth conventions; :237 calls them "
              "'opposite tokens for one promise'")


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 8 -- the rig the page describes at :54 IS the harness at the bottom of this file.
# `registers/corrections.tsv:227` names this path as the source of the figures at :41-53, so
# the page's description of it and the harness's own constants are two ends of one claim.
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate_rig_description():
    print("\n── 8. the rig the page describes, at :54, against the harness below ─────────")
    _require(r"reference roots solved in closed form per bilinear cell",
             "how the reference is computed (:54-55)")
    bits = _int(r"\*\*The rig\*\*: CPython/fp(\d+), \d+² samples of", "the rig's precision (:54)")
    res = _int(r"\*\*The rig\*\*: CPython/fp\d+, (\d+)² samples of", "the rig's resolution (:54)")
    tex = _num(r"b·sin\(k′z\)` at ([\d.]+) m texels", "the rig's texel size (:54)")
    seed = _int(r"seed (\d+), reference roots", "the rig's seed (:54)")
    _agree("the resolution the page states and the harness's own N", res, N)
    _agree("the texel size the page states and the harness's own S0", tex, S0)
    _agree("the seed the page states and the harness's own SEED", seed, SEED)
    mant = {24: 32, 53: 64}.get(sys.float_info.mant_dig)
    _agree("the ray-parameter precision the page states and this interpreter's float",
           bits, mant)


# ═════════════════════════════════════════════════════════════════════════════════════════
# GATE 9 -- the CONCLUSIONS the page draws from its residuals, at :49-53.
#
# The absolute millimetres are not gated and cannot be (see the diagnostics below: the page
# gives the FORM of its field and never a, b, k or k′, so no rig can rebuild that ray set).
# But the page does not only print them -- it draws a claim from them: "That residual is
# `span/2ᵏ` and nothing else, so it follows the *span*, not the terrain", and then applies
# it to get ±0.64 m at a 57 m span.  That inference is checkable WITHOUT the field, because
# it is a statement about the page's own numbers: the three residuals it prints at three
# refinement counts of ONE span must sit at one r·2ᵏ, and the per-texel and column-locked
# residuals must sit at the SAME fraction of their own span/2ᵏ.  They are printed to
# different precisions, so the test is whether the ROUNDING BANDS overlap -- a tolerance
# read off the page's own digits, not chosen here to make the check pass.
#
# The general-ray span is one texel: :52 says the column-locked span is "not one texel", and
# :54 states the texel size.  That size is a rig constant, not a measurement -- gate 8 above
# `_agree`s it exactly against this file's own S0 -- so it enters with no rounding band.
# ═════════════════════════════════════════════════════════════════════════════════════════
# The rounding band below is read off the digits the page prints, which is honest ONLY if the
# page cannot buy itself a wider gate by printing fewer of them.  It could: an independent
# attack on this file walked `±0.64 m` to `±0.7 m` -- the SAME claim, one digit coarser, 12%
# away from what the law gives -- and gate 9 went green, because the band widened with the
# string it was testing.  That is failure shape 3, a tolerance taken from the number under
# test, in the gate written to close a different one.
#
# The repair is not a wider band or a narrower one.  It is that a figure too coarse to check
# is a defect ON THE PAGE, not a free pass: this gate states the precision it needs, and a
# page that prints less than that FAILS naming the coarsening.  MIN_SIGFIGS is this rig's
# constant with its reason attached, not a value parsed from the document, so it is not the
# typed-in expectation wearing a new hat.
MIN_SIGFIGS = 2


def _sigfigs(printed):
    """Significant figures the page PRINTED: leading zeros are placeholders, the rest are not.

    Trailing zeros are NOT stripped. `0.70` is two figures, not one -- a first version of this
    stripped them and would have failed a page that printed `±0.70 m`, which is a perfectly
    good two-figure measurement. An over-strict precision rule is still a wrong rule.
    """
    return len(printed.replace("-", "").replace(".", "").lstrip("0")) or 1


def _half(printed):
    """The rounding half-width implied by how many digits the page printed."""
    dp = len(printed.split(".")[1]) if "." in printed else 0
    return 0.5 * 10.0 ** -dp


def gate_residual_follows_span():
    print("\n── 9. 'the residual follows the span': the page's own four numbers, at :49-53 ─")
    _require(r"That residual\s*\nis `span/2ᵏ` and nothing else, so it follows the \*span\*, "
             r"not the terrain", "that the residual follows the span and nothing else (:50-51)")
    _require(r"so its level-0 span is the rest of the ray", "why a picking ray's span is long (:52)")
    _require(r"median here, not\s*\none texel", "that the general span IS one texel (:52-53)")

    r_gen_s = _page(r"the hit lands within \*\*±([\d.]+) mm\s*\nat \d+ bisections\*\*",
                    "the per-texel residual (:49-50)")
    k_gen = _int(r"the hit lands within \*\*±[\d.]+ mm\s*\nat (\d+) bisections\*\*",
                 "its bisection count (:50)")
    span_s = _page(r"the rest of the ray — ([\d.]+) m median here", "the column-locked span (:52)")
    r_col_s = _page(r"and the same \d+ bisections land \*\*±([\d.]+) m\*\*",
                    "the column-locked residual (:53)")
    k_col = _int(r"and the same (\d+) bisections land \*\*±[\d.]+ m\*\*",
                 "its bisection count (:53)")
    texel = _num(r"b·sin\(k′z\)` at ([\d.]+) m texels", "the texel size (:54)")

    _agree("the bisection count both residuals are quoted at", k_gen, k_col)
    if k_gen != k_col:
        return

    # The SAME sentence prints the same residual at two more refinement counts -- "(±21 mm
    # at 5, ±2.6 mm at 8)" -- for the SAME ray set at the SAME span: "for primary, ascending
    # and grazing rays" is one clause covering all three.  So the page's own `span/2ᵏ` law
    # says r(k)·2ᵏ is ONE constant across the three, and that is an arithmetic claim about
    # the page's own numbers, needing no field.  It was not checked: an independent attack
    # moved ±2.6 mm at 8 to ±9.9 mm and ±21 mm at 5 to ±40 mm and every gate stayed green.
    other = re.search(r"\(±([\d.]+) mm at (\d+), ±([\d.]+) mm at (\d+)\)", _BODY)
    if not other:
        sys.exit("ANCHOR GONE -- the page no longer states its two other residuals at :50 "
                 "(pattern '(±N mm at k, ±N mm at k)')")
    trio = [(r_gen_s, k_gen), (other.group(1), int(other.group(2))),
            (other.group(3), int(other.group(4)))]

    coarse = [(w, t) for w, t in ([("the per-texel residual", r_gen_s),
                                   ("the column-locked residual", r_col_s),
                                   ("the column-locked span", span_s)]
                                 + [(f"the residual at {k} bisections", v) for v, k in trio])
              if _sigfigs(t) < MIN_SIGFIGS]
    for what, txt in coarse:
        _fail(f"{what} is printed as {txt!r} -- {_sigfigs(txt)} significant figure(s), and this "
              f"check needs {MIN_SIGFIGS}. At that precision the rounding band is wider than the "
              f"error it is meant to catch, so the page would be buying itself a looser gate by "
              f"printing fewer digits. Print {MIN_SIGFIGS} s.f. or drop the claim")
    if coarse:
        return

    # r(k)·2ᵏ, one constant across the three counts, each widened by its own printed
    # precision.  The bands must have a COMMON point -- pairwise overlap is not enough.
    lo_c = max((float(v) - _half(v)) * 2.0 ** k for v, k in trio)
    hi_c = min((float(v) + _half(v)) * 2.0 ** k for v, k in trio)
    for v, k in trio:
        print(f"      ±{v} mm at {k} bisections -> r·2^{k} = {float(v) * 2.0 ** k:7.1f} mm, "
              f"band [{(float(v) - _half(v)) * 2.0 ** k:.1f}, "
              f"{(float(v) + _half(v)) * 2.0 ** k:.1f}]")
    if lo_c <= hi_c:
        print(f"PASS  the page's three residuals sit at ONE r·2^k within their own printed "
              f"precision ([{lo_c:.1f}, {hi_c:.1f}] mm) -- ':51 that residual is span/2\u1d4f "
              f"and nothing else', across the counts the page itself instantiates")
    else:
        bands = [(v, k, round((float(v) - _half(v)) * 2.0 ** k, 1),
                  round((float(v) + _half(v)) * 2.0 ** k, 1)) for v, k in trio]
        _fail(f"the page's three residuals at :49-50 do not follow ONE `span/2\u1d4f` law: "
              f"r·2^k bands {bands} "
              f"have no common point ({lo_c:.1f} > {hi_c:.1f} mm), so at least one of "
              f"±{trio[0][0]} mm at {trio[0][1]}, ±{trio[1][0]} mm at {trio[1][1]} and "
              f"±{trio[2][0]} mm at {trio[2][1]} contradicts the other two")

    r_gen, r_col, span = float(r_gen_s) / 1000.0, float(r_col_s), float(span_s)
    h_gen, h_col, h_span = _half(r_gen_s) / 1000.0, _half(r_col_s), _half(span_s)
    two_k = 2.0 ** k_gen

    # fraction of the span/2^k bound each residual sits at, widened by the printed precision
    lo_gen = (r_gen - h_gen) / (texel / two_k)
    hi_gen = (r_gen + h_gen) / (texel / two_k)
    lo_col = (r_col - h_col) / ((span + h_span) / two_k)
    hi_col = (r_col + h_col) / ((span - h_span) / two_k)

    print(f"      per-texel : ±{r_gen_s} mm of a {texel:g} m span/2^{k_gen} = "
          f"{texel / two_k * 1000:.3f} mm  ->  {lo_gen:.4f}..{hi_gen:.4f} of the bound")
    print(f"      column-locked: ±{r_col_s} m of a {span_s} m span/2^{k_col} = "
          f"{span / two_k:.4f} m  ->  {lo_col:.4f}..{hi_col:.4f} of the bound")

    # State the discriminating power rather than assume it: how far off could the page's
    # column-locked residual be and still overlap?  Printed, so a reader sees the gate's reach.
    derived = r_gen * span / texel
    widest = max(abs(hi_col / lo_gen), abs(hi_gen / lo_col)) - 1.0
    print(f"      reach: the law gives ±{derived:.3f} m; the page's ±{r_col_s} m is "
          f"{abs(r_col - derived) / derived * 100:.1f}% off, and the bands admit at most "
          f"{widest * 100:.1f}%")

    global _ok
    good = lo_gen <= hi_col and lo_col <= hi_gen
    _ok = _ok and good
    print(f"{'PASS' if good else 'FAIL'}  the two fractions of span/2^{k_gen} overlap within "
          f"the page's own printed precision")
    if not good:
        _fail(f"the page's ±{r_col_s} m does not follow from its ±{r_gen_s} mm at a {span_s} m "
              f"span: the same law gives ±{r_gen * span / texel:.3f} m, and the printed digits "
              f"are too tight to reconcile the two")


# ═════════════════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS -- measured, printed, and DELIBERATELY NOT GATED.  Each says why.
# ═════════════════════════════════════════════════════════════════════════════════════════
def diagnostics(h, pyr, rs):
    print("\n── not gated, and why ───────────────────────────────────────────────────────")
    print("      :47-53  515 rays / 398 hits / ±21, ±11, ±2.6 mm / 57 m median / ±0.64 m:")
    print("              UNREPRODUCIBLE FROM THE PAGE.  :54 gives the FORM of the field,")
    print("              `h = a·sin(kx) + b·sin(k′z)`, and never a, b, k or k′, so no rig")
    print("              can rebuild that ray set.  The register says the printed mm are")
    print("              each ROUNDED UP from the run, so they are bounds, and asserting a")
    print("              bound one-sidedly is the defect this corpus keeps catching: walk")
    print("              ±11 mm to ±110 mm and `worst < claimed` stays green.  The counts")
    print("              the same sentence states as WORDS -- zero missed, zero spurious --")
    print("              are exact and ARE gated above, on this rig's own field.")
    print("              So is every RATIO among them: gate 9 above checks that ±21 mm at 5,\n"
          "              ±11 mm at 6 and ±2.6 mm at 8 sit at ONE r·2\u1d4f, and that ±0.64 m at\n"
          "              57 m and ±11 mm at one texel sit at the same fraction of their own\n"
          "              span/2\u1d4f.  That is the page's own inference and needs no field.\n"
          "              Only the ABSOLUTE millimetres stay ungated.")
    ref = [_reference(h, o, d, t0, t1) for (o, d, t0, t1, _k) in rs]
    worst = 0.0
    for (o, d, t0, t1, _k), rt in zip(rs, ref):
        r = _march(h, pyr, o, d, t0, t1, iters=6)
        if r[0] != "HIT" or rt is None or not r[2]:
            continue
        span = r[2][-1][1] - r[2][-1][0]
        if span > 0:
            worst = max(worst, abs(r[1] - rt) / (span / 2.0 ** 6))
    print(f"      :51    residual = span/2ᵏ: worst |hit − reference| on this field is "
          f"{worst:.3f}× span/2⁶.")
    print("              NOT GATED: `err <= span/2^k` is a property of bisection, true for")
    print("              any k and any span, so both sides move together when the page is")
    print("              edited.  A gate that cannot fail is not a gate.")
    print("              What IS gated, at 9 above, is the page's own use of that law across\n"
          "              its two spans -- an arithmetic claim, not a property of bisection.")

    # the block's own `return refine(...)`, run literally
    bad = 0
    for (o, d, t0, t1, _k) in rs:
        if _march(h, pyr, o, d, t0, t1, iters=6, literal_return=True)[0] == "HIT-NO-BRACKET":
            bad += 1
    print(f"      :70    `if (level == 0) return refine(t, tExitNode)` returns UNCONDITIONALLY.")
    print(f"              Run literally, {bad} of {len(rs)} rays reach a level-0 node whose")
    print(f"              interval brackets no crossing, and the block returns a hit there.")
    print(f"              Every gate above marches on instead, which is the only way the")
    print(f"              page's own `zero spurious` can hold.  A PAGE DEFECT, not gated,")
    print(f"              and not fixed here: this rig may not edit the document.")

    # the per-level apron's reach, measured
    per = _pyramid(h, "perlevel")
    reaches = []
    for L in range(1, _N_EXP - 2):      # above this the window wraps the periodic field
        s_n = len(per[L])
        need = 0
        for j in range(s_n):
            for i in range(s_n):
                for r in range(0, (1 << (L + 1)) + 1):
                    lo_i, hi_i = i * (1 << L) - r, (i + 1) * (1 << L) - 1 + r
                    lo_j, hi_j = j * (1 << L) - r, (j + 1) * (1 << L) - 1 + r
                    m = max(h[jj % _NG][ii % _NG]
                            for jj in range(lo_j, hi_j + 1) for ii in range(lo_i, hi_i + 1))
                    if m == per[L][j][i]:
                        need = max(need, r)
                        break
        reaches.append((L, need))
    print(f"      :149-150 'aproning per level over-bounds by 2^L': measured reach of a")
    print(f"              per-level apron, in BASE texels, is {reaches} (levels above")
    print(f"              these wrap this {_NG}² field) -- i.e. 2^(L+1) − 1 base texels,")
    print(f"              against the level-0 apron's 1 at every level.  NOT GATED: the page")
    print(f"              does not say whether 2^L is a factor or an offset, and it is")
    print(f"              neither on this measurement.  Reported, not asserted.")


def run_gate():
    print(f"heightfield-raymarching.md gate -- every expectation below is parsed out of\n"
          f"{_DOC}\n"
          f"at run time.  Field: {_NG}² at {_S0:g} m texels, h = a·sin(kx) + b·sin(k′z) with "
          f"a={_AMP_X:g}, k=2π/{2 * math.pi / _KX:g}, b={_AMP_Z:g}, k′=2π/{2 * math.pi / _KZ:g} "
          f"-- this rig's own constants, which the page does not state.")
    gate_fence()
    gate_cost()
    gate_fp32()
    h = _samples()
    pyr = _pyramid(h, "level0")
    rs = _rays(h)
    gate_registration(h)
    gate_termination(h, pyr, rs)
    gate_clamp(h, pyr, rs)
    gate_predicate(h, pyr, rs)
    gate_depth()
    gate_rig_description()
    gate_residual_follows_span()
    diagnostics(h, pyr, rs)
    print()
    return 0 if _ok else 1


# ═════════════════════════════════════════════════════════════════════════════════════════
# THE PRESERVED MEASUREMENT HARNESS -- `--measure`.
#
# This is the code `registers/corrections.tsv:227` cites, kept so that row stays checkable.
# It measures; it asserts nothing against the page and always exits 0.  Its own description,
# as it was written in the sitting that produced the page's figures, follows verbatim.
#
# Measure the max-mip traversal in gaia/references/heightfield-raymarching.md.
#
# Two questions, one rig:
#
#   ERROR  How far is the hit this kernel returns from the true first crossing of the
#          SAME reconstructed surface, as a function of the refinement iteration count
#          the block prescribes ("binary or secant refine, 5-8 iterations")?  And does
#          the pyramid ever hide a hit (a miss the reference finds) or invent one?
#
#   COST   What does the max-reduce pyramid add to the field it is built over?  This is
#          exact arithmetic over the arrays actually built here, not a timing.
#
# WHAT THIS RIG IS
#   CPython + numpy, fp64 ray parameter, fp32 height storage, 512x512 base field at
#   s0 = 1 m, surface reconstructed BILINEARLY from samples at texel centres, pyramid
#   built exactly as the document prescribes (dilate the base samples 3x3, then
#   max-reduce that).  Reference intersection is analytic: inside one bilinear cell the
#   ray-surface difference is a QUADRATIC in t, solved in closed form, so the reference
#   carries no step size and no tolerance of its own.
#
# WHAT THIS RIG IS NOT
#   Not a GPU measurement of any kind.  It prices no frame, no wave, no divergence, no
#   bandwidth.  It is fp64 in t, so it does NOT reproduce the fp32 ULP behaviour the
#   document argues about at :88-:96 -- the relative advance is exercised, its fp32
#   failure mode is not.  The field is smooth and synthetic; a real terrain with cliffs
#   has longer level-0 spans and therefore a larger refinement residual at the same
#   iteration count.
#
# Run:  python3 heightfield-raymarching.py
# Seed: 20260910 (fixed below)
# ═════════════════════════════════════════════════════════════════════════════════════════
SEED = 20260910
S0 = 1.0          # metres per level-0 texel
N = 512           # base grid is N x N
A, KX = 40.0, 2.0 * math.pi / 128.0
B, KZ = 15.0, 2.0 * math.pi / 91.0
BISECTIONS = (5, 6, 8)   # the range the document's block prescribes
SCAN = 8                 # linear-search samples used only when the endpoints do not bracket
STEP_CAP = 10 ** 9
RELATIVE_ADVANCE = 1.0 + 2.0 ** -22   # the constant printed in the document


def analytic(x, z):
    return A * math.sin(KX * x) + B * math.sin(KZ * z)


# ---------------------------------------------------------------- field + pyramid
def build():
    i = (np.arange(N) + 0.5) * S0
    hx = A * np.sin(KX * i)
    hz = B * np.sin(KZ * i)
    H = (hx[None, :] + hz[:, None]).astype(np.float32)   # H[j, i], i -> x, j -> z

    # level 0 of the pyramid: the base samples DILATED 3x3, per the document.  A texel's
    # half-open square is reconstructed from samples i-1..i+1, so the 3x3 max bounds it.
    d = H.copy()
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            d = np.maximum(d, np.roll(np.roll(H, dj, axis=0), di, axis=1))
    pyr = [d]
    while pyr[-1].shape[0] > 1:
        p = pyr[-1]
        pyr.append(np.maximum.reduce([p[0::2, 0::2], p[0::2, 1::2],
                                      p[1::2, 0::2], p[1::2, 1::2]]))
    return H, pyr


def surface(H, x, z):
    """Bilinear reconstruction from samples at texel centres."""
    u, v = x / S0 - 0.5, z / S0 - 0.5
    i, j = int(math.floor(u)), int(math.floor(v))
    p, q = u - i, v - j
    i = min(max(i, 0), N - 2)
    j = min(max(j, 0), N - 2)
    h00, h10 = float(H[j, i]), float(H[j, i + 1])
    h01, h11 = float(H[j + 1, i]), float(H[j + 1, i + 1])
    return (h00 * (1 - p) * (1 - q) + h10 * p * (1 - q)
            + h01 * (1 - p) * q + h11 * p * q)


# ---------------------------------------------------------------- exact reference
def cell_quadratic(H, o, d, i, j):
    """f(t) = rayHeight(t) - surface(t) inside bilinear cell (i, j): a quadratic."""
    h00, h10 = float(H[j, i]), float(H[j, i + 1])
    h01, h11 = float(H[j + 1, i]), float(H[j + 1, i + 1])
    c0 = h00
    c1 = h10 - h00
    c2 = h01 - h00
    c3 = h00 - h10 - h01 + h11
    x0 = (i + 0.5) * S0
    z0 = (j + 0.5) * S0
    p0, pd = (o[0] - x0) / S0, d[0] / S0
    q0, qd = (o[2] - z0) / S0, d[2] / S0
    a2 = -(c3 * pd * qd)
    a1 = d[1] - (c1 * pd + c2 * qd + c3 * (p0 * qd + q0 * pd))
    a0 = o[1] - (c0 + c1 * p0 + c2 * q0 + c3 * p0 * q0)
    return a2, a1, a0


def roots_in(a2, a1, a0, lo, hi):
    out = []
    if abs(a2) < 1e-18:
        if abs(a1) > 1e-18:
            out.append(-a0 / a1)
    else:
        disc = a1 * a1 - 4 * a2 * a0
        if disc >= 0.0:
            s = math.sqrt(disc)
            out += [(-a1 + s) / (2 * a2), (-a1 - s) / (2 * a2)]
    return sorted(t for t in out if lo - 1e-12 <= t <= hi + 1e-12)


def reference_hit(H, o, d, t_enter, t_exit):
    """First crossing of the bilinear surface, found cell by cell in closed form."""
    t = t_enter
    guard = 0
    while t < t_exit and guard < 4 * N:
        guard += 1
        x, z = o[0] + d[0] * t, o[2] + d[2] * t
        i = int(math.floor(x / S0 - 0.5))
        j = int(math.floor(z / S0 - 0.5))
        if not (0 <= i < N - 1 and 0 <= j < N - 1):
            return None
        tx = math.inf if d[0] == 0 else (((i + (1.5 if d[0] > 0 else 0.5)) * S0) - o[0]) / d[0]
        tz = math.inf if d[2] == 0 else (((j + (1.5 if d[2] > 0 else 0.5)) * S0) - o[2]) / d[2]
        t_cell = min(tx, tz, t_exit)
        a2, a1, a0 = cell_quadratic(H, o, d, i, j)
        r = roots_in(a2, a1, a0, t, t_cell)
        if r:
            return r[0]
        t = t_cell * RELATIVE_ADVANCE if t_cell > 0 else t_cell + 1e-9
    return None


# ---------------------------------------------------------------- the kernel
def refine(H, o, d, t0, t1, iters):
    """Bisection on [t0, t1], with a short linear scan when the ends do not bracket."""
    f = lambda t: (o[1] + d[1] * t) - surface(H, o[0] + d[0] * t, o[2] + d[2] * t)
    lo, hi = t0, t1
    flo, fhi = f(lo), f(hi)
    if flo <= 0.0:
        return lo
    if not (flo > 0.0 > fhi):
        found = False
        prev_t, prev_f = lo, flo
        for s in range(1, SCAN + 1):
            tt = lo + (hi - lo) * s / SCAN
            ft = f(tt)
            if prev_f > 0.0 > ft:
                lo, hi, flo, fhi = prev_t, tt, prev_f, ft
                found = True
                break
            prev_t, prev_f = tt, ft
        if not found:
            return None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if fm > 0.0:
            lo, flo = mid, fm
        else:
            hi, fhi = mid, fm
    return 0.5 * (lo + hi)


def march(H, pyr, o, d, t_enter, t_exit, iters):
    coarsest = len(pyr) - 1
    level = coarsest
    t = max(0.0, t_enter)
    steps = 0
    while t < t_exit:
        s = S0 * (1 << level)
        x, z = o[0] + d[0] * t, o[2] + d[2] * t
        i, j = int(math.floor(x / s)), int(math.floor(z / s))
        n = pyr[level].shape[0]
        if not (0 <= i < n and 0 <= j < n):
            return None, steps, 0.0
        node_max = float(pyr[level][j, i])
        tx = math.inf if d[0] == 0 else (((i + (1 if d[0] > 0 else 0)) * s) - o[0]) / d[0]
        tz = math.inf if d[2] == 0 else (((j + (1 if d[2] > 0 else 0)) * s) - o[2]) / d[2]
        t_exit_node = min(tx, tz, t_exit)
        if min(o[1] + d[1] * t, o[1] + d[1] * t_exit_node) < node_max:
            if level == 0:
                hit = refine(H, o, d, t, t_exit_node, iters)
                if hit is not None:
                    return hit, steps, t_exit_node - t
                t = max(t, t_exit_node) * RELATIVE_ADVANCE
                level = min(level + 1, coarsest)
                steps += 1
                continue
            if d[1] < 0.0:
                t_cross = (node_max - o[1]) / d[1]
                t = max(t, t_cross)
            level -= 1
        else:
            t = max(t, t_exit_node) * RELATIVE_ADVANCE
            level = min(level + 1, coarsest)
        steps += 1
        if steps > STEP_CAP:
            return None, steps, 0.0
    return None, steps, 0.0


# ---------------------------------------------------------------- ray set
def rays(H):
    rng = random.Random(SEED)
    lo, hi = 2.0 * S0, (N - 2) * S0
    out = []

    def clip(o, d):
        """t range over the interior box, and the [mapMin, mapMax] height slab."""
        t0, t1 = 0.0, 1e9
        for ax, a, b in ((0, lo, hi), (2, lo, hi), (1, -(A + B) - 1.0, (A + B) + 1.0)):
            if abs(d[ax]) < 1e-15:
                if not (a <= o[ax] <= b):
                    return None
                continue
            ta, tb = (a - o[ax]) / d[ax], (b - o[ax]) / d[ax]
            if ta > tb:
                ta, tb = tb, ta
            t0, t1 = max(t0, ta), min(t1, tb)
        return (max(0.0, t0), t1) if t1 > max(0.0, t0) else None

    def push(o, d, kind):
        L = math.sqrt(sum(c * c for c in d))
        d = [c / L for c in d]
        c = clip(o, d)
        if c:
            out.append((o, d, c[0], c[1], kind))

    # primary rays: camera above the field, looking forward and down
    for _ in range(250):
        o = [rng.uniform(20, N - 20), rng.uniform(70, 140), rng.uniform(20, N - 20)]
        yaw = rng.uniform(0, 2 * math.pi)
        pitch = math.radians(rng.uniform(-40, -3))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "primary")
    # ascending shadow / line-of-sight rays: start on the surface, climb toward the sun
    for _ in range(200):
        x, z = rng.uniform(20, N - 20), rng.uniform(20, N - 20)
        o = [x, surface(H, x, z) + 0.05, z]
        yaw = rng.uniform(0, 2 * math.pi)
        pitch = math.radians(rng.uniform(4, 30))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "ascending")
    # grazing rays: the worst case the document names.  Started just ABOVE the
    # reconstructed surface: an origin inside the terrain is outside this kernel's contract.
    for _ in range(100):
        x, z = rng.uniform(20, N - 20), rng.uniform(20, N - 20)
        o = [x, surface(H, x, z) + 0.5, z]
        yaw = rng.uniform(0, 2 * math.pi)
        pitch = math.radians(rng.uniform(-0.8, 0.8))
        push(o, [math.cos(pitch) * math.cos(yaw), math.sin(pitch),
                 math.cos(pitch) * math.sin(yaw)], "grazing")
    # straight-down picking rays
    for _ in range(50):
        o = [rng.uniform(20, N - 20), 120.0, rng.uniform(20, N - 20)]
        push(o, [0.0, -1.0, 0.0], "picking")
    return out


def measure():
    H, pyr = build()

    # ---- COST: exact arithmetic over the arrays actually built.  Level 0 of the max
    # pyramid is the 3x3-DILATED base, a second full-resolution array; the heights
    # themselves are not conservative and cannot serve as it.
    base_cells = H.size
    pyr_cells = sum(int(p.size) for p in pyr)
    upper = pyr_cells - int(pyr[0].size)
    for name, bpt in (("R16", 2), ("R32F", 4)):
        print(f"COST {name}: field {bpt:.2f} bytes/cell | pyramid {pyr_cells * bpt / base_cells:.4f} "
              f"bytes/cell (level 0 {int(pyr[0].size) * bpt / base_cells:.2f} + levels 1.. "
              f"{upper * bpt / base_cells:.4f}) | field+pyramid "
              f"{(base_cells + pyr_cells) * bpt / base_cells:.4f} bytes/cell")
    print(f"COST ratios: pyramid/field={pyr_cells / base_cells:.6f}  "
          f"(field+pyramid)/field={(base_cells + pyr_cells) / base_cells:.6f}  "
          f"levels={len(pyr)} base_cells={base_cells} pyramid_cells={pyr_cells}")

    rs = rays(H)
    # An origin inside the terrain is outside this kernel's contract: refine() reports the
    # origin itself and the reference reports the surface EXIT.  Drop them, and say how many.
    def above(o, d, t0):
        return (o[1] + d[1] * t0) - surface(H, o[0] + d[0] * t0, o[2] + d[2] * t0) > 0.0
    kept = [r for r in rs if above(r[0], r[1], r[2])]
    print(f"rays: {len(rs)} generated, {len(rs) - len(kept)} dropped (origin below the "
          f"reconstructed surface), {len(kept)} used; " + ", ".join(
              f"{k}={sum(1 for r in kept if r[4] == k)}" for k in
              ("primary", "ascending", "grazing", "picking")))
    rs = kept

    ref = [reference_hit(H, o, d, t0, t1) for (o, d, t0, t1, _) in rs]
    print(f"reference: {sum(1 for r in ref if r is not None)} hits, "
          f"{sum(1 for r in ref if r is None)} misses")

    # The reference is analytic; cross-check a sample of it against a dense brute march.
    def brute(o, d, t0, t1, step=5e-4):
        f = lambda t: (o[1] + d[1] * t) - surface(H, o[0] + d[0] * t, o[2] + d[2] * t)
        t, prev = t0, f(t0)
        while t < t1:
            t2 = min(t + step, t1)
            cur = f(t2)
            if prev > 0.0 >= cur:
                lo, hi = t, t2
                for _ in range(60):
                    m = 0.5 * (lo + hi)
                    if f(m) > 0.0:
                        lo = m
                    else:
                        hi = m
                return 0.5 * (lo + hi)
            t, prev = t2, cur
        return None
    worst_ref = 0.0
    checked = 0
    for (o, d, t0, t1, _), rt in list(zip(rs, ref))[::17]:
        if rt is None:
            continue
        b = brute(o, d, t0, min(t1, rt + 2.0))
        if b is not None:
            worst_ref = max(worst_ref, abs(b - rt))
            checked += 1
    print(f"reference cross-check: {checked} rays against a 0.5 mm brute march + 60 bisections, "
          f"max disagreement {worst_ref * 1e6:.3f} um")

    for iters in BISECTIONS:
        by = {}
        missed = spurious = 0
        for (o, d, t0, t1, kind), rt in zip(rs, ref):
            ht, steps, span = march(H, pyr, o, d, t0, t1, iters)
            if rt is None and ht is None:
                continue
            if rt is not None and ht is None:
                missed += 1
            elif rt is None and ht is not None:
                spurious += 1
            else:
                cls = "column-locked" if kind == "picking" else "general"
                by.setdefault(cls, []).append((abs(ht - rt), span, steps))
        for cls in ("general", "column-locked"):
            v = by.get(cls, [])
            if not v:
                continue
            errs = sorted(e for e, _, _ in v)
            n = len(errs)
            spans = [sp for _, sp, _ in v]
            bound = max(sp / 2 ** iters for sp in spans)
            print(f"ERROR k={iters} {cls:13s}: n={n} missed={missed} spurious={spurious} "
                  f"max={errs[-1] * 1000:8.2f} mm  p99={errs[int(0.99 * (n - 1))] * 1000:8.2f} mm  "
                  f"mean={sum(errs) / n * 1000:7.2f} mm | level-0 span max={max(spans):8.2f} m "
                  f"median={sorted(spans)[n // 2]:.3f} m | span/2^k bound={bound * 1000:.2f} mm "
                  f"| max_steps={max(st for _, _, st in v)}")


def main():
    if "--measure" in sys.argv[1:]:
        if np is None:
            sys.exit("--measure needs NumPy; the gate (no arguments) does not")
        measure()
        return 0
    if [a for a in sys.argv[1:] if a != "--gate"]:
        sys.exit(f"usage: {pathlib.Path(__file__).name} [--gate | --measure]")
    return run_gate()


if __name__ == "__main__":
    sys.exit(main())
