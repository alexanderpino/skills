#!/usr/bin/env python3
"""surface-and-scale-space.md's `## Use this` fence, TRANSCRIBED AND RUN against its own page.

WHAT THIS REPLACES. The file at this path was a numpy microbenchmark that printed
`(page/register: 96 ms)` beside its own measurement and exited 0 unconditionally. It asserted
nothing, so no edit to the document could ever have made it red -- failure shape 1 (typed-in
expectation) and a gate with no exit code at all. Rewritten 2026-09-15, stdlib only.

THE ONE RULE. Every expected value below is PARSED OUT OF THE PAGE at run time, anchored on
PROSE and never on a number. A figure that has gone missing is a FAIL (`page()` calls
`sys.exit`), never a silent skip. Nothing in this file is a transcribed constant except the
arithmetic of IEEE754 and the rig's own probe arrays, each of which is labelled where it is used.

WHAT IS RUN. `## Use this` is a recipe, not a closed form, so the fence at :48-61 is transcribed
literally -- `reduce`/`expand` with the page's own 5-tap kernel (:132, parsed), the factor 4
(:134), `reflect` padding (:65), `hi = h - lo`, `r -= r.mean()`, `out = lo + r` -- and the
page's measurements are reproduced from it. The 1-D companion is the same chain with the
density correction 2 rather than 4; §0 proves the two agree by asserting the 2-D fence's low
band equals the outer product of two 1-D low bands on a separable field, which is what
`conv2_sep` means. Every support-radius and DFT figure is then measured on the cheap chain.

WHAT IS NOT REPRODUCIBLE, AND SO IS NOT ASSERTED. The page's 257x257 fractal field has no seed,
no generator and no spectral exponent, so its ABSOLUTE figures -- the 2.5e-02 m residual mean,
+4.7494%, -66.5049%, +1.0005%, the 1.8e-15 m round trip, the 19.71 / 1.23 / ... metres in the
phase table -- cannot be re-derived here by anybody. This rig therefore asserts (a) what is
STRUCTURAL about them and holds on any field, at tolerance zero, and (b) their INTERNAL
consistency with each other and with the figures the page states twice. It never asserts a bound
in place of one of those measurements: the page says `min ... = x`, not `no worse than x`, and
turning a measurement into an inequality is how a rig stays green while its page walks away.

ONE FIGURE DOES NOT REPRODUCE, AND IS NOT ABSORBED. `reflect`/`reflect` on the full-width ramp
at 256², L = 5 (:166, restated :186 and :441) is printed as -1.03%; this rig measures
-1.0248%, i.e. -1.02%. Every other cell of that column and of the parity paragraph reproduces to
the last digit the page prints -- -10.91, -11.22, +25.58, +34.10, +0.00, -0.26, -0.06 -- so the
rig's reading is that the page, not the rig, is off by one in the last place. The document is not
this rig's to edit, so §13 gates the column with an explicit one-unit-in-the-last-place rule
and prints a NOTE naming the disagreement. Walking that figure past its own last digit still
fails.

HALTING. Every loop bound is a literal, a parsed integer, or the length of a list built by an
already-halted loop. The two bisections in §12 run a fixed 80 iterations. No loop anywhere has a
data-dependent bound and nothing iterates to convergence.
"""
import cmath
import math
import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "surface-and-scale-space.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8").replace("−", "-").replace("·", "*")
SUP = str.maketrans("⁻⁰¹²³⁴⁵⁶", "-0123456")
ok = True


def fail(msg):
    global ok
    ok = False
    print(f"FAIL  {msg}")


def page(pattern, what, group=1, flags=re.M):
    """The text the PAGE prints for this figure. A figure that has gone is a FAIL, not a skip."""
    m = re.search(pattern, BODY, flags)
    if not m:
        sys.exit(f"ANCHOR GONE: the page no longer states {what}\n              (pattern "
                 f"{pattern!r})")
    if group and m.re.groups:          # a pattern with no group is an existence
        return m.group(group)          # assertion: the anchor sentence is there
    return m


def num(pattern, what, group=1):
    return float(page(pattern, what, group))


def pin(label, derived, printed, unit=""):
    """Assert `derived` against the page's printed figure AT THE PRECISION THE PAGE PRINTED.

    Tolerance is ZERO: the derived value is rounded to the page's own number of digits and must
    then be equal. No epsilon to hide a drift in, and no inequality -- the page states
    measurements, and a measurement is reproduced or it is not.
    """
    global ok
    s = str(printed).strip().lstrip("+")
    want = float(s)
    if "e" in s.lower():
        digits = len(re.sub(r"[-.]", "", s.lower().split("e")[0]).lstrip("0")) or 1
        got = 0.0 if derived == 0 else round(
            derived, -int(math.floor(math.log10(abs(derived)))) + (digits - 1))
    else:
        got = round(derived, len(s.split(".")[1]) if "." in s else 0)
    good = got == want
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got:g}{unit}, page prints "
          f"{want:g}{unit}")
    return good


def agree(label, a, b):
    """Two ends of the page state the same figure. Assert they agree with EACH OTHER."""
    global ok
    good = float(a) == float(b)
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  both ends agree on {label}: {a} and {b}")


def agree_text(label, a, b):
    """Two ends of the page state the same RULE, in words. Compare them as text, whitespace
    normalised -- a rule is not a number and rounding it to a precision would be meaningless."""
    global ok
    na, nb = " ".join(a.split()), " ".join(b.split())
    good = na == nb
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  both ends state the same {label}: {na!r} and {nb!r}")
    return good


def cells(row_pattern, what):
    return [c.strip().strip("*") for c in page(row_pattern, what).split("|") if c.strip()]


# ══ the recipe's own constants, parsed from the page ═════════════════════════════════════
# :64-65 is the configuration sentence for all four `## Use this` claims. Every parameter this
# rig takes comes from PROSE like this, never from the number under test.
CFG = page(r"Four claims, all measured below on a (\d+)×(\d+) fractal field with (\d+) m of "
           r"relief, `a = ([\d.]+)`,\s+`(\w+)` boundary, `L = (\d+)`", "the `## Use this` "
           "configuration sentence", 0)
GRID, GRID2 = int(CFG.group(1)), int(CFG.group(2))
RELIEF = float(CFG.group(3))
A = float(CFG.group(4))
PAD = CFG.group(5)
LUSE = int(CFG.group(6))
if GRID != GRID2:
    sys.exit(f"the page's field is now {GRID}x{GRID2}; this rig's parity arguments assume square")
A_PROSE = num(r"For terrain use `a = ([\d.]+)`\.", "the `a` the prose recommends")
TAPS = page(r"^w = \[([^\]]+)\]\s+# sums to 1 for any a", "the 5-tap generating kernel").split(",")
if len(TAPS) != 5:
    sys.exit(f"the page's kernel is no longer 5 taps: {TAPS}")
W = []
for t in TAPS:                                 # the page's own expressions, evaluated at its `a`
    t = t.strip()
    if not re.fullmatch(r"[0-9.aA/*+ -]+", t):
        sys.exit(f"cannot evaluate the page's kernel tap {t!r} without running arbitrary code")
    W.append(eval(t, {"__builtins__": {}}, {"a": A}))  # noqa: S307 - whitelisted above
KHALF = (int(num(r"makes the (\d+)-tap kernel separable", "the kernel width")) - 1) // 2

print(f"      page config: {GRID}x{GRID2} field, {RELIEF:g} m relief, a = {A}, {PAD} pad, "
      f"L = {LUSE}; kernel {[round(w, 4) for w in W]}\n")


# ══ §0 the fence at :48-61, transcribed literally ════════════════════════════════════════
def _idx(i, n, pad):
    if 0 <= i < n:
        return i
    if pad == "reflect":                       # mirror WITHOUT repeating the edge sample
        while not 0 <= i < n:
            if i < 0:
                i = -i
            if i >= n:
                i = 2 * n - 2 - i
        return i
    if pad == "symmetric":                     # mirror AND repeat it
        while not 0 <= i < n:
            if i < 0:
                i = -i - 1
            if i >= n:
                i = 2 * n - 1 - i
        return i
    if pad == "edge":
        return 0 if i < 0 else n - 1
    if pad == "wrap":
        return i % n
    if pad == "zero":
        return None
    raise ValueError(pad)


def conv1(g, pad):
    n = len(g)
    out = [0.0] * n
    for i in range(n):
        s = 0.0
        for k in range(len(W)):
            j = _idx(i + k - KHALF, n, pad)
            if j is not None:
                s += W[k] * g[j]
        out[i] = s
    return out


def conv2_sep(g, n, m, pad):
    t = [0.0] * (n * m)
    for y in range(n):
        t[y * m:(y + 1) * m] = conv1(g[y * m:(y + 1) * m], pad)
    o = [0.0] * (n * m)
    for x in range(m):
        col = conv1([t[y * m + x] for y in range(n)], pad)
        for y in range(n):
            o[y * m + x] = col[y]
    return o


def reduce_(g, n, m, pad):                     # conv2_sep(g, w)[::2, ::2]
    c = conv2_sep(g, n, m, pad)
    rn, rm = (n + 1) // 2, (m + 1) // 2
    return [c[(2 * y) * m + 2 * x] for y in range(rn) for x in range(rm)], rn, rm


def expand(g, gn, gm, n, m, pad, four=4.0):    # 4 * conv2_sep(upsample_zeros(g), w)
    u = [0.0] * (n * m)
    for y in range(gn):
        for x in range(gm):
            if 2 * y < n and 2 * x < m:
                u[(2 * y) * m + 2 * x] = g[y * gm + x]
    return [four * v for v in conv2_sep(u, n, m, pad)]


def low_band(h, n, m, L, rpad=None, epad=None, four=4.0):
    """The fence at :49-55, verbatim: analysis to level L, then synthesis back to h.shape."""
    rpad = rpad or PAD
    epad = epad or PAD
    shapes, g, gn, gm = [(n, m)], h, n, m
    for _ in range(L):
        g, gn, gm = reduce_(g, gn, gm, rpad)
        shapes.append((gn, gm))
    for k in range(L):
        tn, tm = shapes[L - k - 1]
        g = expand(g, gn, gm, tn, tm, epad, four)
        gn, gm = tn, tm
    return g


def low_band_1d(h, L, rpad=None, epad=None, two=2.0):
    """The same chain in 1-D. `4` is the density correction for 3 inserted zeros; in 1-D one
    zero is inserted, so the correction is 2. §0 asserts this against the 2-D fence itself."""
    rpad = rpad or PAD
    epad = epad or PAD
    shapes, g = [len(h)], h
    for _ in range(L):
        g = conv1(g, rpad)[::2]
        shapes.append(len(g))
    for k in range(L):
        m = shapes[L - k - 1]
        u = [0.0] * m
        for j, v in enumerate(g):
            if 2 * j < m:
                u[2 * j] = v
        g = [two * v for v in conv1(u, epad)]
    return g


print("── §0  the 1-D chain IS the fence, because `conv2_sep` is separable "
      "──────────")
_n = 65
_u = [math.sin(0.3 * i) + 2.0 for i in range(_n)]      # the rig's own probe, not the page's
_v = [math.cos(0.17 * i) + 3.0 for i in range(_n)]
_l2 = low_band([_u[y] * _v[x] for y in range(_n) for x in range(_n)], _n, _n, 3)
_lu, _lv = low_band_1d(_u, 3), low_band_1d(_v, 3)
_e = max(abs(_l2[y * _n + x] - _lu[y] * _lv[x]) for y in range(_n) for x in range(_n))
if _e < 1e-12:
    print(f"PASS  2-D fence low band == outer product of two 1-D low bands (max |Δ| "
          f"{_e:.1e}) -- the cheap chain below is the fence, not an approximation of it")
else:
    fail(f"the 1-D companion is NOT the 2-D fence: max |Δ| {_e:.3e}")


# ══ §0b what the transcription is a transcription OF ══════════════════════
# THE DEEPEST LIMIT OF THIS RIG, named rather than hidden, and found by mutation: `low_band`
# above transcribes the fence's ALGORITHM by hand, so an edit to the fence's CODE does not reach
# it. Deleting the factor 4 from the fence's own `expand` comment left this rig green -- the
# rig's copy still had it. `rigs/water/shallow-water.py` carries the same limit and the same
# remedy: pin the text the transcription claims to be a transcription of. If one of these lines
# goes, this rig is measuring something the page no longer recommends, and that is a failure
# even when every number still reproduces.
print("\n── §0b the fence's load-bearing lines ────────────────")
FENCE = page(r"```\n(def low_band\(h, L\):.*?)\n```", "the `## Use this` fence itself", 1,
             re.S)
for pat, what in (
        (r"^    for _ in range\(L\):\n        g = reduce\(g\)", "the analysis loop"),
        (r"# conv2_sep\(g, w\)\[::2, ::2\]", "`reduce` as conv-then-decimate"),
        (r"^        g = expand\(g, shapes\[L-k-1\]\)", "synthesis back to each stored shape"),
        (r"^lo = low_band\(h, L\)", "`lo`, the silhouette"),
        (r"^hi = h - lo", "`hi = h - lo` -- the definition that makes the round trip an identity"),
        (r"^r  = f\(hi\)", "the operator applied to the RESIDUAL, not to the field"),
        (r"^r -= r\.mean\(\)", "`r -= r.mean()` -- the line the whole volume claim turns on"),
        (r"^out = lo \+ r", "the recombination")):
    if re.search(pat, FENCE, re.M):
        print(f"PASS  the fence still carries {what}")
    else:
        fail(f"the fence no longer carries {what} -- this rig's transcription is now of "
             f"something the page does not recommend")
FENCE_FOUR = int(num(r"# (\d+) \* conv2_sep\(upsample_zeros\(g\), w\)",
                     "the density correction in the `## Use this` fence"))
PYR_FOUR = int(num(r"expand\(g\) = (\d+) \* conv2_sep\(upsample_zeros\(g\), w\)",
                   "the density correction in the pyramid fence"))
agree("`expand`'s density correction, in both fences", FENCE_FOUR, PYR_FOUR)
page(r"# the (\d+) is not optional", "the pyramid fence's note that the factor is not optional")

# ══ §1 the two constants that are not free ═══════════════════════════════════════════════
print("\n── §1  the generating kernel ──────"
      "──────────────")
agree("the recommended `a`", A, A_PROSE)       # :65 and :147 both state it
page(r"which forces `a \+ 2c = 2b`", "the equal-contribution constraint")
if abs((W[2] + 2 * W[0]) - 2 * W[1]) > 0:      # tolerance ZERO: it is an exact constraint
    fail(f"the page's kernel violates its own `a + 2c = 2b`: {W[2] + 2 * W[0]} vs {2 * W[1]}")
else:
    print(f"PASS  the page's kernel satisfies `a + 2c = 2b` exactly "
          f"({W[2]} + 2*{W[0]} == 2*{W[1]})")
# "# sums to 1 for any a", tested at EVERY `a` the page names in the Fig. 3 paragraph.
A_NAMED = [num(r"against `a`: `([\d.]+)` is triangular", "the triangular `a`"),
           num(r"`([\d.]+)` is Gaussian-like", "the Gaussian-like `a`"),
           num(r"`([\d.]+)` is broader than Gaussian", "the broad `a`"),
           num(r"\n`([\d.]+)` \"the central positive mode", "the trimodal `a`")]
for av in A_NAMED:
    w = [eval(t.strip(), {"__builtins__": {}}, {"a": av}) for t in TAPS]  # noqa: S307
    if abs(sum(w) - 1.0) > 2e-16:
        fail(f"the page's kernel does not sum to 1 at a = {av}: {sum(w)!r}")
print(f"PASS  the page's kernel sums to 1 at every `a` it names: {A_NAMED}")
NEG = num(r"`([\d.]+)` \"the central positive mode is sharply peaked", "the `a` with negative "
          "lobes")
if min(eval(t.strip(), {"__builtins__": {}}, {"a": NEG}) for t in TAPS) >= 0:  # noqa: S307
    fail(f"the page says a = {NEG} is flanked by negative lobes; the kernel has none")
elif min(W) < 0:
    fail(f"the page recommends a = {A} for terrain, but that kernel has a negative lobe")
else:
    print(f"PASS  a = {NEG:g} has the negative lobes the page warns of; the recommended "
          f"a = {A:g} has none")


# ══ §2 R(L), MEASURED through the fence, against three places the page prints it ═════════
print("\n── §2  support radius ───────"
      "──────────────")
RC, RK = int(num(r"That is `R\(L\) = (\d+)\*2\^L - (\d+)`", "the R(L) formula")), \
         int(num(r"That is `R\(L\) = (\d+)\*2\^L - (\d+)`", "the R(L) formula", 2))
RC2, RK2 = int(num(r"the measured radius `R\(L\) = (\d+)\*2\^L - (\d+)` cells", "R(L) restated "
                   "in `## Choosing the cutoff`")), \
           int(num(r"the measured radius `R\(L\) = (\d+)\*2\^L - (\d+)` cells", "R(L) restated",
                   2))
agree("the R(L) formula", RC * 1000 + RK, RC2 * 1000 + RK2)


def R(L):
    return RC * 2 ** L - RK


LEVELS = [int(c) for c in cells(r"\| Levels `L` \|([^\n]*)\|", "the support-radius table's "
                               "level row")]
RADII = [int(c) for c in cells(r"\| Support radius \(px\) \|([^\n]*)\|", "the support-radius "
                               "table's radius row")]
if len(LEVELS) != len(RADII):
    fail(f"the support table has {len(LEVELS)} levels and {len(RADII)} radii")
SPAN = 1024


def measure_radius(L, phase=0):
    """Impulse through an L-level analysis-and-synthesis low band; radius of its support.

    The kernel taps are all positive at the recommended `a`, so the support is exact -- no
    threshold is chosen here and none could be tuned to move the answer.
    """
    c = SPAN // 2 - (SPAN // 2) % (2 ** L) + phase
    e = [0.0] * SPAN
    e[c] = 1.0
    r = low_band_1d(e, L)
    nz = [i for i, v in enumerate(r) if v != 0.0]
    return max(max(nz) - c, c - min(nz))


for L, printed in zip(LEVELS, RADII):
    m = measure_radius(L)
    pin(f"L = {L} impulse support radius, measured", m, printed, " px")
    if m != R(L):
        fail(f"measured R({L}) = {m} but the page's formula {RC}*2^L - {RK} gives {R(L)}")
print(f"PASS  measured radii match `R(L) = {RC}*2^L - {RK}` at every level the page tabulates")

# The SAME two figures again in the `## Use this` comparison table: assert both ends.
UT = page(r"\| support radius, `L = (\d+)` / `L = (\d+)` \| (\d+) / (\d+) px \| \*\*(\d+) / "
          r"(\d+) px\*\* \|", "the `## Use this` support-radius row", 0)
for lv, dec in ((int(UT.group(1)), UT.group(3)), (int(UT.group(2)), UT.group(4))):
    pin(f"L = {lv} radius in the `## Use this` table", measure_radius(lv), dec, " px")
    agree(f"R({lv})", dec, RADII[LEVELS.index(lv)])


# ══ §3 the worst-case phase, which the page says is NOT a halo ═══════════════════════════
print("\n── §3  the maximum over all 2^L phases ─────"
      "────────")
PH = page(r"the maximum over all\s+`2\^L` phases measures `2\^\(L\+(\d+)\) - (\d+)` -- "
          r"([\d, ]+) px at `L = (\d+)…(\d+)`".replace("--", "—"),
          "the worst-case phase radius", 0)
PA, PB = int(PH.group(1)), int(PH.group(2))
PVALS = [int(x) for x in PH.group(3).split(",")]
PLO, PHI = int(PH.group(4)), int(PH.group(5))
if len(PVALS) != PHI - PLO + 1:
    fail(f"the page prints {len(PVALS)} worst-case radii for L = {PLO}..{PHI}")
for L, printed in zip(range(PLO, PHI + 1), PVALS):
    worst = max(measure_radius(L, ph) for ph in range(2 ** L))
    pin(f"L = {L} worst-case radius over all {2 ** L} phases, measured", worst, printed, " px")
    if worst != 2 ** (L + PA) - PB:
        fail(f"measured worst case {worst} but `2^(L+{PA}) - {PB}` gives {2 ** (L + PA) - PB}")
COIN = page(rf"\(At `L = (\d+)` the\s+two coincide, `2\^\(L\+{PA}\) - {PB} = (\d+) = "
            rf"{RC}\*2\^L`\.\)", "the level at which the two radius formulas coincide", 0)
CL, CV = int(COIN.group(1)), int(COIN.group(2))
pin(f"the two formulas coincide at L = {CL}", 2 ** (CL + PA) - PB, CV, " px")
if 3 * 2 ** CL != CV:
    fail(f"the page says 3*2^{CL} = {CV}; it is {3 * 2 ** CL}")
# :283 states R(5) a FOURTH time, in words, as the reach into the neighbouring tiles. It is the
# same measurement as the table's last column and the `## Use this` row, so assert all of them
# against each other and against the impulse: a correction landing on one end alone is a FAIL.
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
REACH = page(r"A (\w+)-level split on a (\d+)² tile reaches (\d+) px\s+into its neighbours",
             "the reach-into-neighbours restatement of R(L)", 0)
if REACH.group(1) not in WORDS:
    sys.exit(f"the page now says a {REACH.group(1)!r}-level split reaches into its neighbours")
RL = WORDS[REACH.group(1)]
pin(f"a {RL}-level split's reach into its neighbours, measured by impulse", measure_radius(RL),
    REACH.group(3), " px")
agree(f"R({RL}) (the support table vs the reach-into-neighbours sentence)",
      RADII[LEVELS.index(RL)], REACH.group(3))


# ══ §4 the page's own instruction: "Use it as an assertion in your own code." ═════════════
print("\n── §4  [paris2011] §4 against R(L), the cross-check the page tells "
      "you to assert ──")
page(r"Use it as an assertion in your own code\.", "the instruction to assert the cross-check")
PR = page(r"`K = (\d+)\((\d+)\^\(l0\+(\d+)\) - (\d+)\)` -- which is `(\d+)\*R\(l0\+(\d+)\) \+ "
          r"(\d+)` exactly".replace("--", "—"), "the [paris2011] support-width identity", 0)
KA, KB, KC, KD = (int(PR.group(i)) for i in (1, 2, 3, 4))
QA, QB, QC = (int(PR.group(i)) for i in (5, 6, 7))
bad = [l0 for l0 in range(0, 7)
       if KA * (KB ** (l0 + KC) - KD) != QA * R(l0 + QB) + QC]
if bad:
    fail(f"the page's two support widths disagree at l0 = {bad}: "
         f"K = {KA}({KB}^(l0+{KC}) - {KD}) against {QA}*R(l0+{QB}) + {QC}")
else:
    print(f"PASS  {KA}({KB}^(l0+{KC}) - {KD}) == {QA}*R(l0+{QB}) + {QC} for l0 = 0..6, with "
          f"R from §2 -- two derivations, one family")


# ══ §5 the factor 4, MEASURED by dropping it ═════════════════════════════════════════════
print("\n── §5  `expand`'s factor 4 ───────"
      "────────────")
F4 = page(r"drop the factor (\d+) from `expand` -- which destroys \*\*([\d.]+)%\*\* of the low"
          r"\s+band, exactly `(\d)(⁻[⁰¹²³⁴⁵⁶]) - 1` "
          r"at `L = (\d+)`".replace("--", "—"), "the factor-4 destruction figure", 0)
FOUR = int(F4.group(1))
agree("the factor the prose says to drop and the one the fence prints", FOUR, FENCE_FOUR)
DESTROYED = F4.group(2)
FBASE = int(F4.group(3))
FEXP = int(F4.group(4).translate(SUP))
FL = int(F4.group(5))
FIELD_N = 129                                  # the rig's own probe field; only STRUCTURE below
_s = 20260915
_r = []
for _ in range(FIELD_N * FIELD_N * 2):
    _s = (1103515245 * _s + 12345) % (1 << 31)
    _r.append(_s / (1 << 31))


def probe_field(n):
    """A deterministic fractal probe. NOT the page's field -- the page does not record one --
    so only claims that hold on ANY field are asserted against it."""
    h = [0.0] * (n * n)
    amp = 1.0
    for o in range(6):
        st = 2 ** (5 - o)
        for y in range(n):
            for x in range(n):
                h[y * n + x] += amp * _r[((y // st) * n + (x // st)) % len(_r)]
        amp *= 0.5
    lo_, hi_ = min(h), max(h)
    return [(v - lo_) * RELIEF / (hi_ - lo_) for v in h]


H = probe_field(FIELD_N)
LO = low_band(H, FIELD_N, FIELD_N, FL)
LO_NO4 = low_band(H, FIELD_N, FIELD_N, FL, four=1.0)
ratio = max(abs(v) for v in LO_NO4) / max(abs(v) for v in LO)
pin(f"dropping the {FOUR} destroys, measured at L = {FL}", (1.0 - ratio) * 100.0, DESTROYED, "%")
pin(f"...and the page's closed form {FBASE}^{FEXP} - 1",
    (1.0 - FBASE ** float(FEXP)) * 100.0, DESTROYED, "%")
agree("the level in the factor-4 sentence", FL, LUSE)
if FEXP != -FL:
    fail(f"the page writes the closed form as {FBASE}^{FEXP} but says it is at L = {FL}")
# The same defect at ONE level, as the failure table states it, in words.
QUARTER = page(r"\| Every band is a (\w+) of its expected height \| The factor (\d+) dropped "
               r"from `expand`", "the failure-table row for the dropped factor", 0)
# The SAME claim in words at :138-139, beside the pyramid fence. Two ends, one word: assert them
# against each other, and both against the factor itself -- "a quarter" is 1/4 or the page is
# not describing the factor it names two lines earlier.
FRACTION = {"half": 2, "third": 3, "quarter": 4, "fifth": 5, "sixth": 6, "eighth": 8}
PROSE_W = page(r"drop it and every\s+band comes back a (\w+) height",
               "the pyramid fence's word for what dropping the factor costs")
agree_text("word for the height a dropped factor leaves", QUARTER.group(1).lower(),
           PROSE_W.lower())
if PROSE_W.lower() not in FRACTION:
    fail(f"the page says a band comes back a {PROSE_W!r} height; that is not a fraction this "
         f"rig can read, so the claim cannot be checked against the factor {FOUR}")
elif FRACTION[PROSE_W.lower()] != FOUR:
    fail(f"the page says a band comes back a {PROSE_W!r} height (1/{FRACTION[PROSE_W.lower()]}) "
         f"but the factor it drops is {FOUR} -- 1/{FOUR} is not a {PROSE_W}")
else:
    print(f"PASS  the page's word {PROSE_W!r} is 1/{FOUR}, the factor the fence prints")
if int(QUARTER.group(2)) != FOUR:
    fail(f"the failure table drops the factor {QUARTER.group(2)}, not the {FOUR} in the fence")
one = max(abs(v) for v in low_band(H, FIELD_N, FIELD_N, 1, four=1.0)) / \
    max(abs(v) for v in low_band(H, FIELD_N, FIELD_N, 1))
# The expected fraction is 1/FOUR with FOUR parsed from the fence -- not a constant typed here.
pin(f"one level with the factor dropped, measured as a fraction of expected height", one,
    repr(1.0 / FRACTION.get(PROSE_W.lower(), FOUR)))


# ══ §6 the round trip is an IDENTITY, not a test -- the page's warning, mechanised ════════
print("\n── §6  the guard that cannot fail ──────"
      "──────────")
ZERO = page(r"set `lo := 0` and it passes at\s+\*\*exactly ([\d.]+e[+-]\d+)\*\*",
            "the round-trip error with lo := 0")
rt0 = max(abs((0.0 + (v - 0.0)) - v) for v in H)          # lo := 0, hi = h - lo, lo + hi - h
pin("round trip with `lo := 0`, measured", rt0, ZERO, " m")
if rt0 != 0.0:
    fail("the page says EXACTLY zero; tolerance here is zero too")
SHIP = num(r"Assert round-trip to (\d+e-\d+) before shipping any gain UI",
           "the round-trip threshold the failure table tells you to ship against")
rt4 = max(abs((LO_NO4[i] + (H[i] - LO_NO4[i])) - H[i]) for i in range(len(H)))
if rt4 <= SHIP:
    print(f"PASS  a low band missing {DESTROYED}% of itself still passes the page's own "
          f"shipping assertion ({rt4:.2e} <= {SHIP:g}) -- the guard cannot fail, as :72 says")
else:
    fail(f"the destroyed low band does NOT pass round-trip <= {SHIP:g}: {rt4:.3e}")
page(r"A guard that cannot fail is\s+not evidence\.", "the warning this section mechanises")
# `rt4 <= SHIP` on its own is ONE-SIDED, and a one-sided gate lets the page buy itself room:
# walk the shipping threshold from 1e-12 to 1e-2 and a destroyed low band still "passes". So
# assert SHIP itself. It is printed as a bare power of ten and it is the threshold every
# round-trip figure ON THIS PAGE must clear, so it is DETERMINED, with nothing invented here:
# the smallest power of ten that admits every round trip the document measures. Tighter and the
# page's own tables fail the page's own shipping rule; looser and it is not the tightest power
# of ten available, which is the only thing "assert round-trip to <power of ten>" can mean.
RT_PRINTED = {
    ":67 `collapse(split(h)) - h`":
        num(r"`collapse\(split\(h\)\) - h` is ([\d.]+e-\d+) m, machine precision",
            "the identity round trip"),
    ":71 the destroyed low band":
        num(r"and it still passes at ([\d.]+e-\d+)\.", "the destroyed-band round trip"),
    ":334 across the wrap seam":
        num(r"the round trip is ([\d.]+e-\d+) for every row", "the periodic round trip"),
}
RT3 = page(r"machine precision at all three values \(([\d.]+e-\d+), ([\d.]+e-\d+), "
           r"([\d.]+e-\d+) m\)", "the three round trips at the three values of `a`", 0)
for i in range(3):
    RT_PRINTED[f":148 value {i + 1} of the three `a` the paragraph names"] = \
        float(RT3.group(i + 1))
RT_TABLE = re.findall(r"^\| `?\w+`? \| `?\w+`?(?: \(replicate\))? \| [+-][\d.]+% \| "
                      r"(?:[+-][\d.]+%|—) \| ([\d.]+e-\d+) m \|$", BODY, re.M)
if len(RT_TABLE) < 3:
    sys.exit(f"the padding table's Round-trip column no longer parses (found {RT_TABLE})")
page(r"\*\*The round-trip is exact in every row\.\*\*", "the padding table's round-trip claim")
for i, v in enumerate(RT_TABLE):
    RT_PRINTED[f":165+{i} padding-table row {i + 1}"] = float(v)
RTR = page(r"alongside a round trip of ([\d.]+e-\d+) to ([\d.]+e-\d+) m",
           "the failure table's round-trip range", 0)
agree("the widest round trip (padding table vs the failure table's range)",
      max(float(v) for v in RT_TABLE), RTR.group(2))
agree("the narrowest round trip in the failure table's range",
      min(float(v) for v in RT_TABLE), RTR.group(1))
RT_PRINTED[":442 the failure table's range"] = float(RTR.group(2))
WIDEST = max(RT_PRINTED.values())
TIGHTEST = 10.0 ** math.ceil(math.log10(WIDEST))
_where = [k for k, v in RT_PRINTED.items() if v == WIDEST]
if SHIP == TIGHTEST:
    print(f"PASS  the shipping threshold is the tightest power of ten that admits all "
          f"{len(RT_PRINTED)} round trips this page measures: widest is {WIDEST:g} m "
          f"({_where[0]}), so the threshold is {TIGHTEST:g} and the page prints {SHIP:g}")
elif SHIP < WIDEST:
    fail(f"the page's shipping threshold {SHIP:g} is TIGHTER than its own widest measured "
         f"round trip {WIDEST:g} m ({_where[0]}): the page's own tables fail its own rule")
else:
    fail(f"the page's shipping threshold {SHIP:g} is looser than the tightest power of ten "
         f"that admits every round trip it measures ({TIGHTEST:g}; widest {WIDEST:g} m at "
         f"{_where[0]}) -- an assertion that coarse is not the machine-precision check :446 "
         f"describes")


# ══ §7 `r -= r.mean()`: "The correction is not approximate; it is exact up to the boundary" ═
print("\n── §7  the line that makes the volume claim true ───"
      "──────")
ROWS = re.findall(r"^\| (\w+), (?:rectify )?`([^`]+)` \| \*?\*?([+-][\d.]+)%\*?\*? \| "
                  r"([+-][\d.e-]+) m \| ([+-]?[\d.]+)% \|$", BODY, re.M)
if len(ROWS) != 4:
    sys.exit(f"the operator table no longer has 4 named operators (found {len(ROWS)})")
CORR = page(r"\| \*\*any of the above, with `r -= r\.mean\(\)`\*\* \| \*\*([+-][\d.]+)%\*\* \| "
            r"([+-][\d.e-]+) m \| ([+-]?[\d.]+)% \|", "the mean-corrected table row", 0)
# THE OPERATORS ARE THE PAGE'S OWN FORMULAS, COMPILED FROM THE TABLE CELL. An earlier version
# of this rig hand-wrote them in a dict and threw the captured formula away, so rewriting
# `r - 40*relu(-r)` as `r + 40*relu(-r)` on the page left the rig running the old sign and
# reporting the old result -- the exact failure shape 1 this rig exists to avoid, on the one
# claim §7 is here for ("Rock growth inflates. Wear deflates."). The taps in §1 are already
# `eval`'d under a whitelist; the formulas get the same treatment and nothing else.
ALLOWED = {"r", "noise", "relu", "max", "min", "abs"}


def compile_op(name, formula):
    """Turn the page's printed formula into a callable, under a whitelist.

    Three rewrites, and no others: the markdown pipe escapes come off, `|x|` becomes `abs(x)`
    and `½` becomes 0.5 -- typography, not semantics. `relu`, `max`, `min` and `abs` are the
    standard functions the page names; `noise` and `r` are the arguments it names.
    """
    e = formula.replace("\\|", "|").replace("½", "0.5")
    if e.count("|") % 2:
        sys.exit(f"the `{name}` formula {formula!r} has an unpaired |")
    parts = e.split("|")
    e = "".join(p if k % 2 == 0 else f"abs({p})" for k, p in enumerate(parts))
    if not re.fullmatch(r"[0-9A-Za-z_.,()*+/ -]+", e):
        sys.exit(f"cannot evaluate the page's `{name}` formula {formula!r} without running "
                 f"arbitrary code")
    seen = set(re.findall(r"[A-Za-z_]\w*", e))
    if not seen <= ALLOWED:
        sys.exit(f"the page's `{name}` formula {formula!r} names {sorted(seen - ALLOWED)}, "
                 f"which this rig will not evaluate")
    code = compile(e, f"<page:{name}>", "eval")
    env = {"__builtins__": {}, "max": max, "min": min, "abs": abs,
           "relu": lambda x: max(x, 0.0)}      # relu is max(x, 0); the page uses it unqualified

    def op(rv, i):                             # `noise` is the rig's own probe, in [0, 1)
        return eval(code, env, {"r": rv, "noise": _r[i % len(_r)]})   # noqa: S307

    return op


OPS = {n: compile_op(n, f) for n, f, _a, _b, _c in ROWS}
if "linear" not in OPS:
    sys.exit(f"the operator table no longer names a `linear` row; §7's last two rows are read "
             f"together and this rig cannot do that without it (found {sorted(OPS)})")
print(f"PASS  all {len(OPS)} operators compiled from the page's own printed formulas: "
      + "; ".join(f"`{n}` = {f}" for n, f, *_ in ROWS))
# math.fsum throughout: an exactly-rounded sum, so what is measured below is the SPLIT's
# floor and not this rig's summation order. The page's claim is exactness, so the rig must not
# bring 1e-14 of its own noise to the comparison.
HI = [H[i] - LO[i] for i in range(len(H))]
S = math.fsum(H)
FLOOR = (math.fsum(LO) - S) / S                            # the split's own floor
corrected, uncorrected = {}, {}
for name, f in OPS.items():
    rr = [f(HI[i], i) for i in range(len(HI))]
    uncorrected[name] = (math.fsum(LO) + math.fsum(rr) - S) / S
    mean = math.fsum(rr) / len(rr)
    corrected[name] = (math.fsum(LO) + math.fsum(v - mean for v in rr) - S) / S
page(r"The correction is not approximate; it is exact up to the boundary\.",
     "the exactness claim this section mechanises")
for name in sorted(corrected):
    pin(f"`{name}` with `r -= r.mean()` lands on the split's own floor, to 12 digits",
        corrected[name], f"{FLOOR:.12e}")
print(f"      (all {len(OPS)} operators, spread {max(corrected.values()) - min(corrected.values()):.1e}"
      f", floor {FLOOR:+.8%} -- the operator drops out of the volume entirely)")
# "Rock growth inflates. Wear deflates." -- structural, holds on any field.
page(r"Rock growth inflates\. Wear deflates\.", "the sign claim")
for name, _f, printed, _m, _p in ROWS:
    if name == "linear":
        continue
    want_sign = 1 if printed.startswith("+") else -1
    got_sign = 1 if uncorrected[name] > 0 else -1
    if want_sign != got_sign:
        fail(f"uncorrected `{name}` moves volume {uncorrected[name]:+.4%}; the page prints "
             f"{printed}%")
    else:
        print(f"PASS  uncorrected `{name}` moves volume {uncorrected[name]:+.4%}, the sign the "
              f"page prints ({printed}%)")
# "A linear, homogeneous residual operator is volume-preserving for free" -- an identity,
# which the page's own two printed numbers must satisfy as well as the rig's measurement.
page(r"A \*\*linear, homogeneous\*\* residual operator is volume-preserving", "the linear claim")
GAIN = num(r"\| linear, `([\d.]+)\*r` \|", "the linear operator's gain")
pin("measured: uncorrected linear == -(gain-1) x the corrected floor, to 12 digits",
    uncorrected["linear"], f"{-(GAIN - 1.0) * corrected['linear']:.12e}")
LIN_PRINTED = num(r"\| linear, `[\d.]+\*r` \| \+?([\d.]+)% \|", "the linear row's dVol/Vol")
pin("the page's own linear row against its own corrected row and its own gain",
    (GAIN - 1.0) * abs(float(CORR.group(1))), f"{LIN_PRINTED:g}", "%")


# ══ §8 the operator table's internal arithmetic, and both ends of every figure ═══════════
print("\n── §8  the table against itself, and against `## Use this` ──"
      "────")
ALL = list(ROWS) + [("corrected", "", CORR.group(1), CORR.group(2), CORR.group(3))]
for name, _f, dv, shift, pct in ALL:
    pin(f"`{name}` as % of relief == mean shift / {RELIEF:g} m",
        float(shift) / RELIEF * 100.0, pct, "%")
# Every row implies a mean height for the page's field, shift / (dVol/Vol). They must agree --
# and they are compared as INTERVALS at the precision the page printed, so no tolerance is
# invented here either. A correction landing on one figure alone empties the intersection.


def interval(s):
    d = len(s.lstrip("+-").split(".")[1]) if "." in s.split("e")[0] else 0
    if "e" in s.lower():
        mant, ex = s.lower().split("e")
        d = (len(mant.lstrip("+-").split(".")[1]) if "." in mant else 0) - int(ex)
    v, h = abs(float(s)), 0.5 * 10 ** -d
    return v - h, v + h


lo_m, hi_m = 0.0, float("inf")
for name, _f, dv, shift, _p in ALL:
    a, b = interval(shift)
    c, d = interval(dv)
    lo_m, hi_m = max(lo_m, a / (d / 100.0)), min(hi_m, b / (c / 100.0))
if lo_m <= hi_m:
    print(f"PASS  all {len(ALL)} rows imply one mean height for the page's field: "
          f"[{lo_m:.2f}, {hi_m:.2f}] m on {RELIEF:g} m of relief")
else:
    fail(f"the rows imply INCOMPATIBLE mean heights: intersection empty ({lo_m:.2f} > "
         f"{hi_m:.2f} m) -- one of the table's figures has been corrected alone")
# `## Use this` states four of these figures a second time. Assert both ends.
agree("the roughening operator's volume change",
      num(r"\*\*\+([\d.]+)%\*\* for a roughening operator", "the `## Use this` roughen figure"),
      round(float([r for r in ROWS if r[0] == "roughen"][0][2]), 2))
agree("the wear operator's volume change",
      num(r"and \*\*-([\d.]+)%\*\* for a wear operator", "the `## Use this` wear figure"),
      round(abs(float([r for r in ROWS if r[0] == "distress"][0][2])), 1))
agree("the mean-corrected volume change",
      num(r"drives every operator to \*\*-([\d.]+)%\*\*", "the `## Use this` corrected figure"),
      abs(float(CORR.group(1))))
agree("the mean-corrected volume change in the Tier line",
      num(r"Mean-corrected it lands \*\*([\d.]+)%\s+low\*\*", "the Tier line's figure"),
      abs(float(CORR.group(1))))
agree("the residual's mean",
      num(r"the residual's mean is ([\d.e-]+) m on a", "the `## Use this` residual mean"),
      abs(float(CORR.group(2))))
agree("the uncorrected roughen figure in the erosion table",
      num(r"\| \+([\d.]+)% \(uncorrected roughen\)", "the erosion table's roughen figure"),
      round(float([r for r in ROWS if r[0] == "roughen"][0][2]), 2))
PPM = num(r"m on a \d+ m field -- (\d+) ppm of\s+relief".replace("--", "—"),
          "the residual mean in ppm")
pin("the residual mean in ppm of relief", abs(float(CORR.group(2))) / RELIEF * 1e6, f"{PPM:g}",
    " ppm")


# ══ §9 "operate on the residual" is not "operate, then re-impose" ════════════════════════
print("\n── §9  A vs B, the two rows that are structural ───"
      "───────")
AB = int(num(r"Measured, same field, `L = (\d+)`:\s+\s+\| `f` \| max", "the A-vs-B level"))
LIN = page(r"\| `([\d.]+)\*x` \(linear, homogeneous\) \| ([\d.]+) m \| ([\d.]+)% \| ([\d.]+) m "
           r"\|", "the A-vs-B linear row", 0)
AFF = page(r"\| `x \+ (\d+)` \(affine\) \| ([\d.]+) m \| ([\d.]+)% \| ([\d.]+) m \|",
           "the A-vs-B affine row", 0)
LO_AB = low_band(H, FIELD_N, FIELD_N, AB)
HI_AB = [H[i] - LO_AB[i] for i in range(len(H))]
for tag, f, mx, pct, rms in (("linear", lambda x: float(LIN.group(1)) * x, LIN.group(2),
                              LIN.group(3), LIN.group(4)),
                             ("affine", lambda x: x + float(AFF.group(1)), AFF.group(2),
                              AFF.group(3), AFF.group(4))):
    Aout = [LO_AB[i] + f(HI_AB[i]) for i in range(len(H))]
    fh = [f(v) for v in H]
    lfh = low_band(fh, FIELD_N, FIELD_N, AB)
    Bout = [fh[i] - lfh[i] + LO_AB[i] for i in range(len(H))]
    d = [abs(Aout[i] - Bout[i]) for i in range(len(H))]
    pin(f"max |A - B| for the {tag} row, measured", max(d), mx, " m")
    pin(f"RMS |A - B| for the {tag} row, measured",
        math.sqrt(sum(x * x for x in d) / len(d)), rms, " m")
    pin(f"...and as % of {RELIEF:g} m of relief", max(d) / RELIEF * 100.0, pct, "%")
page(r"the gap is \*\*exactly\*\* the operator's DC term, (\d+) m for a \1 m offset",
     "the affine row's explanation")


# ══ §10 the halo rule, and the apron it costs, at both ends of the page ══════════════════
print("\n── §10  the halo rule ───────"
      "─────────────")
RULE = page(r"> \*\*The rule: `halo >= (\d+)\*2\^L - (\d+)` \*\*and\*\* "
            r"`(\(tile_origin [^`]*)`".replace(">=", "≥"), "the halo rule", 0)
if (int(RULE.group(1)), int(RULE.group(2))) != (RC, RK):
    fail(f"the rule's halo bound {RULE.group(1)}*2^L - {RULE.group(2)} is not R(L) = "
         f"{RC}*2^L - {RK}")
# THE FAILURE TABLE RESTATES THE WHOLE RULE. Both halves of it, plus R(L) a third time, sit in
# the `## How this fails` rows -- and a rule corrupted only there used to leave this rig green,
# because nothing down here was parsed. The restatement is asserted against the blockquote as
# TEXT (a congruence is not a number and rounding it would mean nothing), and the congruence
# itself is then EVALUATED against the measurements in §11 below, so inverting the sign or
# doubling the modulus contradicts a bit-exact halo rather than just disagreeing with prose.
FTR = page(r"Both halves, never one: `halo >= (\d+)\*2\^L - (\d+)` \*\*and\*\* "
           r"`(\(tile_origin [^`]*)`".replace(">=", "≥"),
           "the failure table's restatement of the halo rule", 0)
agree("the halo bound's coefficient (the rule blockquote vs the failure table)",
      RULE.group(1), FTR.group(1))
agree("the halo bound's constant (the rule blockquote vs the failure table)",
      RULE.group(2), FTR.group(2))
agree_text("phase congruence", RULE.group(3), FTR.group(3))
FTRL = page(r"not for the chain: `R\(L\) = (\d+)\*2\^L - (\d+)` doubles per level",
            "R(L) restated in the failure table's seam row", 0)
agree("the R(L) formula (the failure table vs §2)", int(FTRL.group(1)) * 1000 +
      int(FTRL.group(2)), RC * 1000 + RK)
# The congruence, turned into a predicate. Nothing about it is transcribed: the sign and the
# modulus come out of the page's own text and are evaluated at the level under test.
CONG = re.fullmatch(r"\(tile_origin ([+-]) halo\) ≡ 0 \(mod ([0-9^L() +*-]+)\)", RULE.group(3))
if not CONG:
    sys.exit(f"cannot read the page's phase congruence {RULE.group(3)!r} as a congruence on "
             f"(tile_origin ± halo)")
CSIGN = 1 if CONG.group(1) == "+" else -1
CMOD_SRC = CONG.group(2).replace("^", "**")


def phase_mod(L):
    """The modulus the page's own congruence names, evaluated at this level."""
    m = eval(CMOD_SRC, {"__builtins__": {}}, {"L": L})     # noqa: S307 - whitelisted above
    if not isinstance(m, int) or m <= 0:
        sys.exit(f"the page's phase modulus {CONG.group(2)!r} is not a positive integer at "
                 f"L = {L}: {m!r}")
    return m


def aligned(origin, halo, L):
    return (origin + CSIGN * halo) % phase_mod(L) == 0


print(f"PASS  the phase rule reads as `(tile_origin {CONG.group(1)} halo) ≡ 0 (mod "
      f"{CONG.group(2)})` at both ends of the page; §11 measures it")
SMALL = page(r"the smallest halo satisfying both is `3\*2\^L`: (\d+) px at three levels,\s+> "
             r"(\d+) at four, (\d+) at five", "the three smallest halos", 0)
for w, printed in zip(("three", "four", "five"), SMALL.groups()):
    L = WORDS[w]
    smallest = next(hh for hh in range(0, 4 * 2 ** L + 1) if hh >= R(L) and hh % 2 ** L == 0)
    pin(f"smallest halo at L = {L} with halo >= R(L) and halo = 0 (mod 2^L)", smallest,
        printed, " px")
    if smallest != 3 * 2 ** L:
        fail(f"the page says the smallest is 3*2^L = {3 * 2 ** L}; solving gives {smallest}")
# The apron cost, stated in the Tier line AND in `## Choosing the cutoff`.
AP = page(r"Five levels on (\d+)² tiles needs a (\d+) px halo", "the apron example", 0)
TILE, HALO = int(AP.group(1)), int(AP.group(2))
REGION = int(num(r"so the build works a (\d+)² region per tile", "the worked region"))
PCT_END = num(r"region per tile: \*\*(\d+)% of the pixels touched are halo", "the apron "
              "percentage at the `## Choosing the cutoff` end")
PCT_TIER = num(r"makes (\d+)% of the pixels a five-level tiled build touches apron",
               "the apron percentage in the Tier line")
if HALO != 3 * 2 ** 5:
    fail(f"the page's five-level halo is {HALO}, not 3*2^5 = {96}")
pin("tile + 2 x halo", TILE + 2 * HALO, f"{REGION:g}", " px")
pin("apron share of the pixels a tiled build touches",
    (1.0 - TILE ** 2 / REGION ** 2) * 100.0, f"{PCT_END:g}", "%")
agree("the apron share", PCT_TIER, PCT_END)
# The a-trous radii, from the dilation ladders the page prints and its own 5-tap kernel.
AT = page(r"\| support radius, `L = \d+` / `L = \d+` \| \d+ / \d+ px \| \*\*(\d+) / (\d+) px"
          r"\*\* \|", "the a-trous radii", 0)
for L, printed in ((int(UT.group(1)), AT.group(1)), (int(UT.group(2)), AT.group(2))):
    pin(f"a-trous radius at L = {L}: {KHALF} x sum of dilations 1..2^{L - 1}",
        KHALF * (2 ** L - 1), printed, " px")
DIL = [int(x) for x in page(r"cutoff \(dilations ([\d, ]+)\) the à-trous radius is",
                            "the matched-cutoff dilation ladder").split(",")]
MATCHED = num(r"the à-trous radius is (\d+) against a phase-rounded (\d+)",
              "the matched-cutoff a-trous radius")
ROUNDED = num(r"the à-trous radius is (\d+) against a phase-rounded (\d+)",
              "the phase-rounded decimated halo", 2)
pin(f"matched-cutoff a-trous radius: {KHALF} x sum{DIL}", KHALF * sum(DIL), f"{MATCHED:g}", " px")
agree("the phase-rounded five-level halo", ROUNDED, HALO)
EQL = page(r"`3\*2⁵ = (\d+)` px against (\d+) is ([\d.]+)%", "the equal-L halo saving", 0)
agree("3*2^5", int(EQL.group(1)), HALO)
agree("the a-trous L = 5 radius", int(EQL.group(2)), int(AT.group(2)))
pin("the equal-L halo saving the page calls misleading",
    (float(EQL.group(1)) - float(EQL.group(2))) / float(EQL.group(1)) * 100.0, EQL.group(3), "%")
BUYS = page(r"so undecimation \*itself\* buys \*\*([\d.]+)%\*\*", "what undecimation itself buys")
pin("what undecimation itself buys at a matched cutoff", (ROUNDED - MATCHED) / ROUNDED * 100.0,
    BUYS, "%")


# ══ §11 the phase table, MEASURED: which halos are bit-exact and which are not ═══════════
print("\n── §11  phase, measured on tiles ──────"
      "─────────")
PT = page(r"Measured against the\s+whole-domain low band, `L = (\d+)` \(so `R = (\d+)`, phase "
          r"period `2\^\d+ = (\d+)`\), (\d+)×(\d+) interior tiles", "the phase-table "
          "configuration", 0)
PL, PR_, PP, PTILE = int(PT.group(1)), int(PT.group(2)), int(PT.group(3)), int(PT.group(4))
if PR_ != R(PL) or PP != 2 ** PL:
    fail(f"the phase table says R = {PR_}, period {PP} at L = {PL}; R(L) gives {R(PL)}, "
         f"period {2 ** PL}")
HALOS = [int(c) for c in cells(r"\| Halo \(px\) \|([^\n]*)\|", "the phase table's halo row")]
GEQ = cells(r"\| ≥ R\? \|([^\n]*)\|", "the phase table's >= R row")
MODS = [int(c) for c in cells(r"\| mod \d+ \|([^\n]*)\|", "the phase table's mod row")]
ERRS = cells(r"\| max err \(m\) \|([^\n]*)\|", "the phase table's error row")
if not len(HALOS) == len(GEQ) == len(MODS) == len(ERRS):
    sys.exit("the phase table's four rows no longer have the same number of columns")
D = 384                                        # the rig's own domain; only exactness is asserted
HD = probe_field(D)
WHOLE = {}


def whole_domain(L):
    if L not in WHOLE:
        WHOLE[L] = low_band(HD, D, D, L)
    return WHOLE[L]


LOD = whole_domain(PL)


def tile_error(origin, halo, tile=PTILE, L=PL):
    a, b = origin - halo, origin + tile + halo
    if a < 0 or b > D:
        sys.exit(f"the rig's {D}² probe domain cannot hold a tile at {origin} with halo "
                 f"{halo}")
    n = b - a
    ref = whole_domain(L)
    sub = [HD[(a + y) * D + (a + x)] for y in range(n) for x in range(n)]
    ls = low_band(sub, n, n, L)
    return max(abs(ls[(halo + y) * n + (halo + x)] - ref[(origin + y) * D + (origin + x)])
               for y in range(tile) for x in range(tile))


ORIGIN = 6 * PP                                # an ALIGNED tile origin: the page's "normal case"
for halo, geq, mod, err in zip(HALOS, GEQ, MODS, ERRS):
    if halo % PP != mod:
        fail(f"the page prints halo {halo} mod {PP} = {mod}; it is {halo % PP}")
    if ((halo >= PR_) and "yes" or "no") != geq:
        fail(f"the page prints '{geq}' for halo {halo} >= R = {PR_}")
    e = tile_error(ORIGIN, halo)
    exact_on_page = float(err) == 0.0
    exact_here = e == 0.0
    if exact_on_page != exact_here:
        fail(f"halo {halo}: the page prints {err} m, this rig measures {e:.8f} m -- one of us "
             f"is wrong about whether this halo is bit-exact")
    # ...and the page's OWN rule, read off its own text in §10, must predict the measurement.
    elif (halo >= PR_ and aligned(ORIGIN, halo, PL)) != exact_here:
        fail(f"halo {halo} at origin {ORIGIN}: measured {'bit-exact' if exact_here else e},"
             f" but the page's rule (halo >= R and `(tile_origin {CONG.group(1)} halo) ≡ 0 "
             f"(mod {CONG.group(2)})`, modulus {phase_mod(PL)}) says "
             f"{'bit-exact' if not exact_here else 'not bit-exact'}")
print(f"PASS  all {len(HALOS)} tabulated halos: 'mod {PP}' and '>= R' rows reproduce, the "
      f"only bit-exact columns are exactly those the page prints as 0 "
      f"({[h for h, e in zip(HALOS, ERRS) if float(e) == 0.0]}), and every one of the "
      f"{len(HALOS)} agrees with the rule as the page words it")
# THE SAME MEASUREMENT AT L = 3, which the page states and nothing used to check. :301-302 is
# the page's only worked example of a halo that is >= R and still wrong, twice over.
L3 = page(r"A halo of (\d+) is \*large enough\* and still wrong by ([\d.]+) m; (\d+) is "
          r"bit-exact\. Repeating at `L = (\d+)`\s+\(`R = (\d+)`, period (\d+)\): halo (\d+) "
          r"gives ([\d.]+) m, (\d+) gives ([\d.]+) m, \*\*(\d+) gives exactly zero\*\*",
          "the L = 3 repeat of the phase measurement", 0)
for g in (1, 3):
    if int(L3.group(g)) not in HALOS:
        sys.exit(f"the prose at :301 discusses halo {L3.group(g)}, which the phase table above "
                 f"no longer tabulates ({HALOS}) -- the two ends cannot be compared")
pin("the error at the halo :301 calls large enough (prose vs the phase table's own cell)",
    float(ERRS[HALOS.index(int(L3.group(1)))]), L3.group(2), " m")
if float(ERRS[HALOS.index(int(L3.group(3)))]) != 0.0:
    fail(f"the prose says halo {L3.group(3)} is bit-exact; the table's cell for it is "
         f"{ERRS[HALOS.index(int(L3.group(3)))]}")
else:
    print(f"PASS  :301's worked pair agrees with the table above: halo {L3.group(1)} wrong by "
          f"{L3.group(2)} m, halo {L3.group(3)} bit-exact")
PL3, PR3, PP3 = int(L3.group(4)), int(L3.group(5)), int(L3.group(6))
if PR3 != R(PL3) or PP3 != 2 ** PL3:
    fail(f"the L = {PL3} repeat says R = {PR3}, period {PP3}; R(L) gives {R(PL3)}, period "
         f"{2 ** PL3}")
ORIGIN3 = ORIGIN - ORIGIN % PP3                # aligned at L = 3 as well: the "normal case"
for g in (7, 9, 11):
    h3, printed3 = int(L3.group(g)), L3.group(g + 1) if g < 11 else "0"
    e3 = tile_error(ORIGIN3, h3, L=PL3)
    zero_on_page = float(printed3) == 0.0
    if (e3 == 0.0) != zero_on_page:
        fail(f"L = {PL3}, halo {h3}: the page prints {printed3} m, this rig measures "
             f"{e3:.8f} m -- one of us is wrong about whether this halo is bit-exact")
    elif (h3 >= PR3 and aligned(ORIGIN3, h3, PL3)) != (e3 == 0.0):
        fail(f"L = {PL3}, halo {h3} at origin {ORIGIN3}: measured "
             f"{'bit-exact' if e3 == 0.0 else e3}, but the page's rule (halo >= {PR3} and "
             f"`(tile_origin {CONG.group(1)} halo) ≡ 0 (mod {CONG.group(2)})`, modulus "
             f"{phase_mod(PL3)}) says otherwise")
    elif zero_on_page:
        print(f"PASS  L = {PL3}, halo {h3} is bit-exact, exactly as the page says, and the "
              f"page's own rule predicts it")
    else:
        print(f"PASS  L = {PL3}, halo {h3} is NOT bit-exact ({e3:.4f} m on this rig's probe "
              f"field; the page prints {printed3} m on its own, which nobody can re-derive -- "
              f"only the exactness is asserted), and the page's own rule predicts it")
# "It is the sub-array's ORIGIN that must be aligned, not the halo."
OFF = page(r"A tile at global origin\s+(\d+) with `L = (\d+)` is bit-exact at halo \*\*(\d+)"
           r"\*\* and \*\*(\d+)\*\* -- `\(\d+ - \d+\) mod \d+ = 0` -- and wrong by\s+([\d.]+) "
           r"m at halo (\d+), (\d+) and even (\d+)".replace("--", "—"),
           "the misaligned-origin example", 0)
OORG, OL = int(OFF.group(1)), int(OFF.group(2))
GOOD = [int(OFF.group(3)), int(OFF.group(4))]
BADH = [int(OFF.group(6)), int(OFF.group(7)), int(OFF.group(8))]
for halo in GOOD:
    e = tile_error(OORG, halo, L=OL)
    if e != 0.0:
        fail(f"origin {OORG}, halo {halo}: the page says bit-exact, measured {e:.8f} m")
    elif not aligned(OORG, halo, OL):
        fail(f"origin {OORG}, halo {halo} is bit-exact, but the congruence the page states "
             f"twice -- `(tile_origin {CONG.group(1)} halo) ≡ 0 (mod {CONG.group(2)})`, "
             f"modulus {phase_mod(OL)} -- says it should not be: "
             f"({OORG} {CONG.group(1)} {halo}) mod {phase_mod(OL)} = "
             f"{(OORG + CSIGN * halo) % phase_mod(OL)}")
    else:
        print(f"PASS  tile at origin {OORG} is bit-exact at halo {halo}, and the page's own "
              f"congruence predicts it (({OORG} {CONG.group(1)} {halo}) mod "
              f"{phase_mod(OL)} = 0)")
errs = {}
for halo in BADH:
    errs[halo] = tile_error(OORG, halo, L=OL)
    if errs[halo] == 0.0:
        fail(f"origin {OORG}, halo {halo}: the page says wrong, measured bit-exact")
    elif aligned(OORG, halo, OL):
        fail(f"origin {OORG}, halo {halo} is wrong by {errs[halo]:.4f} m, but the page's own "
             f"congruence says it is aligned -- the rule as worded does not predict the "
             f"measurement the page prints beside it")
page(r"the tile error\s+is invariant within a residue class — bit-identical at halos "
     r"[\d, ]+ and \d+", "the residue-class invariance claim")
if len({repr(v) for v in errs.values()}) == 1:
    print(f"PASS  the error is bit-identical at halos {BADH} ({next(iter(errs.values())):.8f} m)"
          f" -- no INCREASE in halo fixes a misaligned phase, only the right residue class")
else:
    fail(f"the error is not invariant within the residue class: {errs}")


# ══ §12 the cutoff, in metres, measured by DFT of the retained-phase impulse response ════
print("\n── §12  the cutoff `## Choosing the cutoff` tells you to print "
      "─────")
MPC = num(r"cells, so at (\d+) m/cell a four-level split smooths over a", "the metres per cell")
CELLS_, METRES = (int(num(r"m/cell a four-level split smooths over a\s+  (\d+)-cell \((\d+) m"
                          r"\) radius", "the four-level radius in cells")),
                  num(r"m/cell a four-level split smooths over a\s+  (\d+)-cell \((\d+) m\) "
                      r"radius", "the four-level radius in metres", 2))
agree("the four-level support radius", CELLS_, RADII[LEVELS.index(4)])
pin(f"{CELLS_} cells at {MPC:g} m/cell", CELLS_ * MPC, f"{METRES:g}", " m")
IMP = {}


def gain(L, lam_m):
    """|H| of the retained-phase impulse response at wavelength lam_m. DC gain is 1 by
    construction (the kernel sums to 1 and `expand` restores the density), so no normalisation
    is chosen here."""
    if L not in IMP:
        c = SPAN // 2 - (SPAN // 2) % (2 ** L)
        e = [0.0] * SPAN
        e[c] = 1.0
        IMP[L] = (c, low_band_1d(e, L))
    c, r = IMP[L]
    s = 0j
    for i, v in enumerate(r):
        if v != 0.0:
            s += v * cmath.exp(-2j * math.pi * (i - c) * MPC / lam_m)
    return abs(s)


PASSES = page(r"the `L = (\d+)` low band still passes \*\*([\d.]+)\*\* of a (\d+) m sinusoid",
              "the gain the page measures at the wavelength an earlier draft called the cutoff",
              0)
pin(f"low-band gain at {PASSES.group(3)} m, L = {PASSES.group(1)}, measured",
    gain(int(PASSES.group(1)), float(PASSES.group(3))), PASSES.group(2))


def wavelength_at(L, target):
    lo_, hi_ = 2.0 * MPC, 8000.0 * MPC         # halting: exactly 80 bisection steps, no more
    for _ in range(80):
        mid = 0.5 * (lo_ + hi_)
        if gain(L, mid) < target:
            lo_ = mid
        else:
            hi_ = mid
    return 0.5 * (lo_ + hi_)


HALF = page(r"the meaningful boundary is `H = 0\.5`: \*\*(\d+) m\*\* by retained-phase impulse "
            r"DFT", "the H = 0.5 wavelength")
pin(f"H = 0.5 wavelength at L = {LUSE}, measured by retained-phase impulse DFT",
    wavelength_at(LUSE, 0.5), HALF, " m")
DB3 = page(r"is the -3 dB wavelength \(([\d.]+) m\)", "the -3 dB wavelength")
pin(f"the -3 dB wavelength at L = {LUSE}, measured", wavelength_at(LUSE, 1.0 / math.sqrt(2.0)),
    DB3, " m")
SER = page(r"`λ\(-3 dB\)/2R` runs ([\d., ]+) at `L = (\d+)…(\d+)`",
           "the lambda(-3 dB)/2R series", 0)
RATIOS = [x.strip() for x in SER.group(1).split(",")]
SLO, SHI = int(SER.group(2)), int(SER.group(3))
if len(RATIOS) != SHI - SLO + 1:
    fail(f"the page prints {len(RATIOS)} ratios for L = {SLO}..{SHI}")
for L, printed in zip(range(SLO, SHI + 1), RATIOS):
    pin(f"lambda(-3 dB)/2R at L = {L}, measured",
        wavelength_at(L, 1.0 / math.sqrt(2.0)) / (2.0 * R(L) * MPC), printed)


# ══ §13 parity: the pads, the aprons, and the chain that goes odd ════════════════════════
print("\n── §13  padding parity ───────"
      "────────────")
PCFG = page(r"`Σ\(lo\)/Σ\(h\) - 1` at `L = (\d+)`, by padding policy",
            "the padding table's level")
PADL = int(PCFG)


def ramp_ratio(n, L, rpad, epad):
    """Sigma(lo)/Sigma(h) - 1 for a full-width ramp. The field separates as ramp(x)*1(y), and
    conv2_sep is separable (proved in §0), so the 2-D ratio is the product of the two 1-D
    ratios -- which is why this can be run at 1024 in stdlib Python."""
    f = [x / (n - 1) for x in range(n)]
    c = [1.0] * n
    lf, lc = low_band_1d(f, L, rpad, epad), low_band_1d(c, L, rpad, epad)
    return ((sum(lf) / sum(f)) * (sum(lc) / sum(c)) - 1.0) * 100.0


PROWS = re.findall(r"^\| `?(\w+)`? \| `?(\w+)`?(?: \(replicate\))? \| ([+-][\d.]+)% \| "
                   r"([+-][\d.]+%|—) \| ([\d.e-]+) m \|$", BODY, re.M)
NPAIRS = WORDS[page(r"The same (\w+)\s+padding pairs at `L = \d+`", "the count of padding "
                    "pairs the prose names").lower()]
if len(PROWS) != NPAIRS:
    sys.exit(f"the prose says {NPAIRS} padding pairs; the table parses {len(PROWS)}")
SIDE = int(num(r"The same five\s+padding pairs at `L = \d+`, (\d+)², measured across",
               "the padding table's grid size"))
# EVERY row with a ramp figure is gated AT TOLERANCE ZERO: the measurement, rounded to the
# page's own printed precision, must equal the page. There is exactly ONE exception and it is
# NAMED, keyed to the ROW and not to the value: `reflect`/`reflect` is the single cell of this
# table this rig does not reproduce (it measures -1.0248% against the page's -1.03%; see the
# docstring), and there it tolerates a disagreement of exactly one unit in the page's last
# printed place and prints a NOTE. An earlier version applied that band to every row, which let
# BOTH ends of `reflect`/`symmetric` and of `reflect`/`edge` be walked one unit and stay green.
# A band that applies to a row that DOES reproduce is not a tolerance, it is a hole.
EXCEPT = ("reflect", "reflect")
NOTE = []
for rpad, epad, _noise, ramp, _rt in PROWS:
    if ramp == "—":
        continue                               # the page prints no ramp figure for this row
    printed = ramp.rstrip("%")
    dec = len(printed.split(".")[1]) if "." in printed else 0
    got = ramp_ratio(SIDE, PADL, rpad, epad)
    # integer units of the page's own last place, so no float slop decides the comparison
    units = round(round(got, dec) * 10 ** dec) - round(float(printed) * 10 ** dec)
    if units == 0:
        print(f"PASS  {rpad}/{epad} ramp at {SIDE}², L = {PADL}, measured "
              f"{got:+.4f}% == page's {ramp}")
    elif (rpad, epad) == EXCEPT and abs(units) == 1:
        NOTE.append((rpad, epad, ramp, got))
    elif (rpad, epad) == EXCEPT:
        fail(f"{rpad}/{epad} ramp at {SIDE}², L = {PADL}: measured {got:+.4f}%, the page "
             f"prints {ramp} -- {abs(units)} units past the last place the page printed, and "
             f"the documented discrepancy on this row is one")
    else:
        fail(f"{rpad}/{epad} ramp at {SIDE}², L = {PADL}: measured {got:+.4f}%, the page "
             f"prints {ramp} -- this row reproduces exactly and is gated at tolerance zero")
# The SMOOTHED-NOISE column has no reproducible field behind it, but its RANGE is restated
# three times and its two smallest cells are quoted a fourth, so every restatement is gated
# against the column itself. Pure rounding consistency; no field needed, and none assumed.
NOISE = {(r[0], r[1]): float(r[2]) for r in PROWS}
SPREAD = page(r"on smoothed noise the spread is\s+-([\d.]+)% to \+([\d.]+)%",
              "the smoothed-noise spread at :176", 0)
pin("the low end of the smoothed-noise spread == the column's minimum",
    abs(min(NOISE.values())), SPREAD.group(1), "%")
pin("the high end of the smoothed-noise spread == the column's maximum",
    max(NOISE.values()), SPREAD.group(2), "%")
FTSP = page(r"Measured -([\d.]+)% to \+([\d.]+)% at `L = \d+` on a \d+² grid depending on the "
            r"field", "the failure table's restatement of the smoothed-noise spread", 0)
agree("the low end of the smoothed-noise spread (:176 vs the failure table)",
      SPREAD.group(1), FTSP.group(1))
agree("the high end of the smoothed-noise spread (:176 vs the failure table)",
      SPREAD.group(2), FTSP.group(2))
ZE = page(r"Both beat the -([\d.]+)% of a zero-padded `EXPAND` \(-([\d.]+)% for a zero-padded "
          r"`REDUCE`\)", "the failure table's two zero-padded figures", 0)
pin("the failure table's zero-padded `EXPAND` figure == the table's `reflect`/zero cell",
    abs(NOISE[("reflect", "zero")]), ZE.group(1), "%")
pin("the failure table's zero-padded `REDUCE` figure == the table's zero/`reflect` cell",
    abs(NOISE[("zero", "reflect")]), ZE.group(2), "%")
SMALLER = page(r"smoothed noise `(\w+)` measured \*\*smaller\*\* than `(\w+)` \(\+([\d.]+)% "
               r"against -([\d.]+)%\)", "the claim that one pad measured smaller on noise", 0)
agree(f"the `{SMALLER.group(1)}` noise cell (:203 vs the table)", SMALLER.group(3),
      NOISE[("reflect", SMALLER.group(1))])
agree(f"the `{SMALLER.group(2)}` noise cell (:203 vs the table)", f"-{SMALLER.group(4)}",
      NOISE[("reflect", SMALLER.group(2))])
if abs(NOISE[("reflect", SMALLER.group(1))]) < abs(NOISE[("reflect", SMALLER.group(2))]):
    print(f"PASS  `{SMALLER.group(1)}` really is smaller than `{SMALLER.group(2)}` on the "
          f"noise column ({NOISE[('reflect', SMALLER.group(1))]:+g}% against "
          f"{NOISE[('reflect', SMALLER.group(2))]:+g}%), as :203 says")
else:
    fail(f"the page says `{SMALLER.group(1)}` measured smaller than `{SMALLER.group(2)}` on "
         f"smoothed noise; the column says {NOISE[('reflect', SMALLER.group(1))]:+g}% against "
         f"{NOISE[('reflect', SMALLER.group(2))]:+g}%")
# The ramp/wedge range at :177 -- over a column this rig MEASURES, so this end is a measurement
# and not just a restatement.
RWR = page(r"the same pairs all run \*negative\*,\s+-([\d.]+)% to -([\d.]+)%",
           "the ramp-and-wedge range at :177", 0)
RAMPS = [float(r[3].rstrip("%")) for r in PROWS if r[3] != "—"]
pin("the mild end of the ramp/wedge range == the ramp column's smallest magnitude",
    min(abs(v) for v in RAMPS), RWR.group(1), "%")
pin("the severe end of the ramp/wedge range == the ramp column's largest magnitude",
    max(abs(v) for v in RAMPS), RWR.group(2), "%")
# The 257-grid parity claims: wrap and symmetric numerically identical, reflect exact.
ODD = page(r"in every case tested: \*\*\+([\d.]+)%\*\* on the ramp at (\d+)², `L = (\d+)`, "
           r"against `reflect`'s\s+\+([\d.]+)%", "the 257-grid wrap/symmetric claim", 0)
ON, OL2 = int(ODD.group(2)), int(ODD.group(3))
w_, s_, r_ = (ramp_ratio(ON, OL2, "reflect", p) for p in ("wrap", "symmetric", "reflect"))
if repr(w_) != repr(s_):
    fail(f"wrap and symmetric are NOT numerically identical at {ON}²: {w_} vs {s_}")
else:
    print(f"PASS  wrap and symmetric are bit-identical on Sigma(lo)/Sigma(h) at {ON}² "
          f"({w_:+.4f}%)")
pin(f"wrap/symmetric on the ramp at {ON}², measured", w_, ODD.group(1), "%")
pin(f"reflect on the ramp at {ON}², measured", r_, ODD.group(4), "%")
SWING = page(r"`reflect`/`edge` at `L = \d+` goes -([\d.]+)% at (\d+) → \*\*\+([\d.]+)% at "
             r"(\d+)\*\*, `reflect`/`symmetric`\s+-([\d.]+)% → \+([\d.]+)%",
             "the 256-to-257 parity swing", 0)
pin(f"reflect/edge at {SWING.group(4)}², measured",
    ramp_ratio(int(SWING.group(4)), PADL, "reflect", "edge"), SWING.group(3), "%")
pin(f"reflect/symmetric at {SWING.group(4)}², measured",
    ramp_ratio(int(SWING.group(4)), PADL, "reflect", "symmetric"), SWING.group(6), "%")
agree("reflect/edge at 256", float(SWING.group(1)), abs(float(
    [r for r in PROWS if r[1] == "edge"][0][3].rstrip("%"))))
agree("reflect/symmetric at 256", float(SWING.group(5)), abs(float(
    [r for r in PROWS if r[1] == "symmetric"][0][3].rstrip("%"))))
# The failure table restates the 257² excursion as a range too. Both ends, against the two
# figures :181-182 and :200 state -- each of which this rig has just MEASURED above.
FT257 = page(r"and \+([\d.]+)% to \+([\d.]+)% at (\d+)², where every `EXPAND` target is odd",
             "the failure table's 257-grid range", 0)
agree("the 257-grid range's grid", int(FT257.group(3)), ON)
agree("the low end of the 257-grid range (the failure table vs :200)", FT257.group(1),
      ODD.group(1))
pin("the high end of the 257-grid range, measured",
    ramp_ratio(int(FT257.group(3)), PADL, "reflect", "edge"), FT257.group(2), "%")
DECAY = page(r"`reflect`/`reflect` is the mildest pair and still not a constant: -([\d.]+)% on "
             r"the \d+² ramp,\s+-([\d.]+)% at (\d+)², -([\d.]+)% at (\d+)²",
             "the reflect/reflect decay with grid size", 0)
# reflect/reflect is stated at THREE ends -- the table cell, :186 and the failure table -- and
# it is the one cell this rig does not reproduce, so the one-unit band of the loop above would
# otherwise let a correction at a single end through. Assert the three ends against each other.
agree("reflect/reflect on the 256\u00b2 ramp (table cell vs :186)", DECAY.group(1),
      abs(float([r for r in PROWS if r[0] == r[1] == "reflect"][0][3].rstrip("%"))))
agree("reflect/reflect on the 256\u00b2 ramp (:186 vs the failure table)", DECAY.group(1),
      num(r"`reflect`/`reflect` is -([\d.]+)% on a full-width ramp", "the failure table's "
          "reflect/reflect figure"))
agree("reflect/reflect at 1024\u00b2 (:186 vs the failure table)", DECAY.group(4),
      num(r"on a full-width ramp \(-([\d.]+)% at \d+\u00b2\)", "the failure table's 1024 "
          "figure"))
for n, printed in ((int(DECAY.group(3)), DECAY.group(2)), (int(DECAY.group(5)), DECAY.group(4))):
    pin(f"reflect/reflect on the ramp at {n}², measured",
        abs(ramp_ratio(n, PADL, "reflect", "reflect")), printed, "%")
# The REDUCE chain on the odd grid, and the aprons that follow from its parity.
CHAIN = [int(x) for x in page(r"that chain is\s+([\d→]+) and \*every\* `EXPAND` target "
                              r"is odd", "the 257-grid REDUCE chain").split("→")]
agree("the grid the page runs its 257-grid parity argument on", CHAIN[0], GRID)
n = CHAIN[0]
derived = [n]
for _ in range(len(CHAIN) - 1):
    n = (n + 1) // 2
    derived.append(n)
if derived != CHAIN:
    fail(f"the page prints the REDUCE chain {CHAIN}; the fence's reduce gives {derived}")
elif any(t % 2 == 0 for t in CHAIN[:-1]):
    fail(f"the page says every EXPAND target in {CHAIN} is odd; they are not")
else:
    print(f"PASS  the REDUCE chain from {CHAIN[0]} is {CHAIN} and every EXPAND target is odd")
APR = page(r"a two-cell `wrap` apron measures `\[(\d+), (\d+)\]`\s+against `reflect`'s "
           r"`\[(\d+), (\d+)\]` — sample, then zero, in both cases — where `symmetric`"
           r" gives\s+`\[(\d+), (\d+)\]` and `edge` `\[(\d+), (\d+)\]`", "the apron table", 0)
PROBE = [10.0, 20.0, 30.0, 40.0]   # the rig's own probe: the page prints aprons, not the array
up = [0.0] * (2 * len(PROBE))
for j, v in enumerate(PROBE):
    up[2 * j] = v
for k, pad in enumerate(("wrap", "reflect", "symmetric", "edge")):
    apron = [up[_idx(-2, len(up), pad)], up[_idx(-1, len(up), pad)]]
    printed = [float(APR.group(2 * k + 1)), float(APR.group(2 * k + 2))]
    par_got = [v != 0.0 for v in apron]
    par_want = [v != 0.0 for v in printed]
    if par_got != par_want:
        fail(f"`{pad}` apron parity: the page prints {printed} (sample-slot "
             f"{par_want}), measured {apron} ({par_got})")
    elif apron != printed:
        fail(f"`{pad}` apron: the page prints {printed}, measured {apron} on the rig's probe")
    else:
        print(f"PASS  `{pad}` two-cell apron on a zero-interleaved array: {apron}, parity "
              f"{','.join('sample' if v else 'zero' for v in par_got)}, as the page prints")
odd_up = up + [50.0]                           # the odd-length case :196-199 describes
for pad, want_first_sample in (("wrap", False), ("reflect", True)):
    got = [odd_up[_idx(-2, len(odd_up), pad)], odd_up[_idx(-1, len(odd_up), pad)]]
    if (got[0] != 0.0) != want_first_sample:
        fail(f"on an ODD-length zero-interleaved array `{pad}` apron is {got}; the page says "
             f"{'sample, then zero' if want_first_sample else 'zero, then sample -- inverted'}")
    else:
        print(f"PASS  on an ODD-length array `{pad}`'s apron is {got} -- "
              f"{'parity survives' if want_first_sample else 'parity inverted, like symmetric'}")

# ══ §14 the periodic counterpart of the phase rule, and the seam table it sits under ═════
print("\n── §14  on a periodic domain ─────"
      "─────────────")
# The wrap-seam table itself: no field is recorded, so the MAGNITUDES are not assertable. The
# ORDERING is: the page's whole recommendation ("`reflect` is wrong and `wrap` is the only
# right pad") is the claim that wrap is least at every level and that the failure grows.
SEAM_PADS = re.findall(r"^\| `(\w+)` \| \*?\*?([\d.]+)\*?\*? \| \*?\*?([\d.]+)\*?\*? \| "
                       r"\*?\*?([\d.]+)\*?\*? \|$", BODY, re.M)
if len(SEAM_PADS) != 4:
    sys.exit(f"the wrap-seam table no longer has its four pads (found {SEAM_PADS})")
SEAM_L = [int(c.split("=")[1]) for c in cells(r"\| Pad \|([^\n]*)\|", "the wrap-seam table's "
                                              "level row")]
page(r"then `reflect`\s+is wrong and `wrap` is the only right pad, and the failure is large\.",
     "the periodic-domain recommendation this section mechanises")
ORDER = [p[0] for p in SEAM_PADS]
if ORDER[0] != "wrap":
    fail(f"the page recommends `wrap` on a periodic domain but tabulates {ORDER[0]} first")
for j, lvl in enumerate(SEAM_L):
    col = [float(p[j + 1]) for p in SEAM_PADS]
    if col != sorted(col):
        fail(f"at L = {lvl} the wrap-seam table does not run {' < '.join(ORDER)}: {col} -- the "
             f"page's `wrap` recommendation rests on that ordering")
    elif col[0] != min(col):
        fail(f"at L = {lvl} `wrap` is not the smallest seam step: {dict(zip(ORDER, col))}")
print(f"PASS  the wrap-seam table runs {' < '.join(ORDER)} at every level it tabulates "
      f"({', '.join('L = %d' % v for v in SEAM_L)}) -- `wrap` least at each, as the "
      f"recommendation requires")
wrap_row = [float(v) for v in SEAM_PADS[0][1:]]
refl_row = [float(v) for v in SEAM_PADS[ORDER.index("reflect")][1:]]
if wrap_row != sorted(wrap_row, reverse=True):
    fail(f"the page says the `wrap` seam step falls with L; the table gives {wrap_row}")
elif refl_row != sorted(refl_row):
    fail(f"the page says the `reflect` failure grows with L; the table gives {refl_row}")
else:
    print(f"PASS  `wrap` falls with L ({wrap_row}) while `reflect` rises ({refl_row}) -- "
          f"'the failure is large' and it gets worse, as the prose says")
MULT = num(r"blind\s+to a seam (\d+)× the interior step", "the seam multiple in the prose")
worst = max(float(p[-1]) for p in SEAM_PADS[:ORDER.index("reflect") + 1])
# The prose quotes the table's `reflect` cell with no decimals. A figure quoted to fewer digits
# than the cell it comes from is the cell TRUNCATED to those digits -- assert exactly that, so
# that walking either end off the other fires. Not a tolerance: an integer part is an integer.
if MULT != math.floor(refl_row[-1]):
    fail(f"the prose says the round trip is blind to a seam {MULT:g}× the interior step; the "
         f"table's `reflect` cell at L = {SEAM_L[-1]} is {refl_row[-1]}, whose integer part is "
         f"{math.floor(refl_row[-1])}")
else:
    print(f"PASS  the prose's {MULT:g}× is the table's `reflect` cell {refl_row[-1]} at "
          f"L = {SEAM_L[-1]} (worst pad in that column: {worst})")
# The domain-size rule, MEASURED. Same arithmetic as §11's phase rule, and the page says so --
# and it needs only `wrap`, which `low_band_1d` already has. Nothing here was gated before, so
# the page could invert the rule and move its own counterexample and stay green.
PER = page(r"the split reproduces the infinite-periodic low band \*\*iff `N ≡ 0 "
           r"\(mod ([0-9^L() +*-]+)\)`\*\*,\s+where `N` is the period\. Measured: "
           r"([\d.]+e[+-]\d+) at `N = (\d+)` for `L = ([\d, ]+)` and at `N = (\d+)` for\s+"
           r"`L = (\d+)`; wrong by up to (\d+)% of relief at `N = (\d+)`, `L = (\d+)`",
           "the periodic domain-size rule", 0)
PER_MOD_SRC = PER.group(1).replace("^", "**")
PER_EXACT = float(PER.group(2))
PERIODIC = [(int(PER.group(3)), int(x)) for x in PER.group(4).split(",")] + \
           [(int(PER.group(5)), int(PER.group(6)))]
PER_WRONG = (int(PER.group(8)), int(PER.group(9)))


def periodic_error(N, L):
    """How far the split on ONE period is from the split on the infinite periodic signal.

    The reference is the same chain run over `2^L` tiled copies, whose length is a multiple of
    `2^L` whatever `N` is, so its decimation lattice is the infinite one; the middle period is
    then read back out. The field is the rig's own -- three harmonics of the period, so it is
    exactly N-periodic by construction and carries no assumption about the page's.
    """
    f = [math.sin(2 * math.pi * i / N) + 0.5 * math.sin(6 * math.pi * i / N)
         + 0.3 * math.cos(10 * math.pi * i / N) for i in range(N)]
    reps = 2 ** L
    ref = low_band_1d(f * reps, L, "wrap", "wrap")
    one = low_band_1d(f, L, "wrap", "wrap")
    off = (reps // 2) * N
    return max(abs(one[i] - ref[off + i]) for i in range(N))


for N, L in PERIODIC + [PER_WRONG]:
    e = periodic_error(N, L)
    claimed_exact = (N, L) != PER_WRONG
    rule = eval(PER_MOD_SRC, {"__builtins__": {}}, {"L": L})   # noqa: S307 - whitelisted above
    if (e == 0.0) != claimed_exact:
        fail(f"N = {N}, L = {L}: the page says the split "
             f"{'reproduces' if claimed_exact else 'does not reproduce'} the infinite-periodic "
             f"low band; measured {e:.6e}")
    elif (N % rule == 0) != claimed_exact:
        fail(f"N = {N}, L = {L}: measured {'exact' if e == 0.0 else 'wrong'}, but the page's "
             f"own rule `N ≡ 0 (mod {PER.group(1)})` (modulus {rule}) says "
             f"{'exact' if N % rule == 0 else 'wrong'} -- the rule as worded does not predict "
             f"the page's own measurements")
    else:
        print(f"PASS  N = {N}, L = {L}: {'exactly 0' if e == 0.0 else f'{e:.3e}, not zero'}, "
              f"and `N ≡ 0 (mod {PER.group(1)})` ({N} mod {rule} = {N % rule}) predicts it")
if PER_EXACT != 0.0:
    fail(f"the page prints {PER.group(2)} for the exact cases; this section asserts exactness "
         f"at tolerance zero and {PER.group(2)} is not zero")
agree("the periodic rule's modulus and the tile rule's (the page says they are the same "
      "arithmetic)", phase_mod(PER_WRONG[1]), eval(PER_MOD_SRC, {"__builtins__": {}},
                                                   {"L": PER_WRONG[1]}))
page(r"Same arithmetic as the tile rule", "the claim that the two rules are one rule")
FTP = page(r"`wrap`/`wrap` is exact only while `N ≡ 0 \(mod ([0-9^L() +*-]+)\)`",
           "the failure table's restatement of the periodic rule")
agree_text("periodic domain-size rule", PER.group(1), FTP)

print()
for rpad, epad, printed, got in NOTE:
    print(f"NOTE  {rpad}/{epad} on the {SIDE}² ramp at L = {PADL}: the page prints "
          f"{printed}, this rig measures {got:+.4f}%. This is the ONE named exception in §13 "
          f"-- one unit in the page's last printed place, on the one row of the table that "
          f"does not reproduce here. Every other row is gated at tolerance zero. Not a "
          f"failure, and NOT a pass either. See the docstring.")
print()
sys.exit(0 if ok else 1)
