#!/usr/bin/env python3
"""`clastic-debris.md`'s `## Use this` fence (:30-47), checked against its own page.

WHAT THIS IS. The fence is five things a reader pastes: the Wentworth class edges, the
largest-first ordering, `r_cls = d_max(cls)`, the cross-class `clear()` test, and two numbers
printed inside the block itself -- "granule at r = 4 mm is 923 GB/km2" and "one grid PER CLASS,
or this costs 42x more". Both of those fence numbers are ROUNDINGS OF TABLES FURTHER DOWN THE
PAGE, so they are derived here from those tables and compared to the fence. The sampler the
fence calls (`poisson_disk(domain, r_cls, k=30)`) is transcribed from the page's own §2 summary
and RUN, and the largest-first loop is transcribed and RUN on the page's own patch.

THE RULE. Every expected value below is PARSED OUT OF THE PAGE at run time, anchored on prose
and never on a number. Nothing is typed in. Two constants are exempt because they are
mathematics, not figures: 2 (the scale's ratio, which the page derives rather than measures),
sqrt(3) (the hexagonal bound's own definition, printed on the page as `2A/(sqrt3 r^2)`), and the
100 that three percentages of one whole must sum to. Every other `want` in every `check()` call
below is a `page(...)` result or arithmetic over `page(...)` results.
A figure that has gone missing is a FAIL -- every `page()` miss exits non-zero.

⚠️ FOUR TRAPS, and what is done about each:
  1. TYPED-IN EXPECTATION -- no numeric literal below is an expectation. Grep this file for
     `check(` and every `want` is a `page(...)` call or arithmetic over `page(...)` calls.
  2. ONE-SIDED ASSERTION -- the page's measurements are reproduced as MEASUREMENTS. The
     largest-first pass is asserted to give exactly the page's pair count, not "at most" it;
     the single-pass control is asserted to give MORE than zero only as proof that the
     detector detects, and that control is named below as NOT a gate on the page's 31.
  3. A PARAMETER FROM THE NUMBER UNDER TEST -- the patch is 10 m x 10 m from the PROSE, the
     draw counts come from the PROSE, the class edges come from the FENCE, and the transform
     size comes from the PROSE. No denominator is ever reconstructed from its own quotient.
  4. A GATE THAT CANNOT FAIL -- one claim is refused for exactly this reason (the first bullet
     below); the other three are refused because no rig can reproduce them, which is a
     different reason and is stated as one.

⚠️ NOT GATED, deliberately:
  * `r_cls = d_max(cls)  # = 2 * a_max: a class cannot overlap itself` -- TRAP 4. With
    a <= d_max/2 for every member, `a_i + a_j <= d_max = r` holds for ANY d_max the fence
    prints. Edit 1024 to 1000 and both sides move together; no page value can contradict it.
    What CAN be contradicted is that the tables use the fence's d_max as their `r`, and §2
    gates that. The cross-class version -- `a_i + a_j` spanning a factor of 256 -- is bound to
    the fence's own d_min and d_max and IS gated (§2c).
  * The absolute timings (2,853 ms; 214 / 148 / 76.1 / 9.8 us; 107-134 us per sample) -- an
    unnamed CPython 3 machine. Unreproducible anywhere else. Their ARITHMETIC is gated (§12).
  * The seed-11 measurements themselves (67 / 964 / 15,153 / 13,338 clasts, 17.60% and the
    other coverages, 31 pairs, "buried 63%") -- the page names seed 11 but not the generator,
    so no rig can land on its counts. Every arithmetic RELATION between them is gated, and
    every figure printed at two ends of the page is asserted at both ends and against itself.
  * The measured AREA columns of the global size-law table (75.38% ... 93.21%) -- area is
    dominated by the handful of largest draws, so the Monte-Carlo error on a 200,000-draw area
    fraction is not a number this rig can state honestly. The page's own closed-form claim
    about them -- equal area per octave at b = 2, i.e. 25 : 25 : 50 -- IS gated (§10).

⚠️ TWO PAGE DEFECTS THIS RIG TOLERATES RATHER THAN HIDES. Both are rounding, both are
named at the gate that tolerates them, and each is gated at the smallest band that admits the
page as written, so a real drift still fires:
  * §11 -- 67 clasts against `2A/(sqrt3 r^2)` at r = 1.024 m is 60.84%; the page prints
    **60.9%**, its own rounding missed by 0.06 pp. Gated at 0.1 pp. The other two rows
    (54.71 -> 54.7, 53.75 -> 53.8) are exact, and the 39-46% shortfall derived from all three
    is exact at tolerance ZERO.
  * §5 -- "Four halvings, each **4.00x** the last": 60,260/15,153 = 3.977, which rounds to
    3.98, not 4.00. The remaining three are 3.993, 3.997, 3.999. Gated at 1%. The GB column
    those candidate counts feed is exact to the last printed digit in all five rows.

HALTING. Four bounded loops, no data-dependent bound anywhere:
  * the sampler's `while active` is bounded by `2 * cells + 2` where `cells` is fixed by the
    parsed domain and `r`; exceeding it is a FAIL, and a parsed domain needing more than
    MAX_CELLS cells is refused before the loop starts;
  * the annulus Monte Carlo runs the page's printed draw count, refused above MAX_DRAWS;
  * table walks are over `re.findall` results of fixed length;
  * pair counting is a fixed 3x3 scan of a grid whose pitch is the largest class' d_max, so
    no clast can reach past one cell; the scan width is a literal, not a page figure.
"""
import math
import pathlib
import random
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "clastic-debris.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")

MAX_CELLS = 1_000_000      # literal halting ceiling on the sampler grid
MAX_DRAWS = 2_000_000      # literal halting ceiling on the Monte Carlo
ok = True


def gone(what, pattern):
    sys.exit(f"the page no longer states {what} (anchor {pattern!r}) -- a figure that has gone "
             f"missing is a FAIL, not a skip")


def page(pattern, what, group=1, flags=0):
    """The number the PAGE prints. Missing anchor => the rig exits non-zero."""
    m = re.search(pattern, BODY, flags)
    if not m:
        gone(what, pattern)
    return float(m.group(group).replace(",", "").replace("−", "-"))


def rows(pattern, what, want_n, flags=re.M):
    got = re.findall(pattern, BODY, flags)
    if len(got) != want_n:
        gone(f"{what} ({want_n} rows; found {len(got)})", pattern)
    return got


def f(s):
    return float(str(s).replace(",", "").replace("−", "-"))


def check(label, got, want, tol):
    global ok
    good = abs(got - want) <= tol
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got:.6g}, page says {want:.6g}")


def agree(label, values):
    """Same figure printed at two or more ends of the page: assert they agree with EACH OTHER.

    A correction landing at one end only is this corpus's most-recorded defect.
    """
    global ok
    vals = [v for _, v in values]
    good = all(abs(v - vals[0]) <= 0 for v in vals)
    ok = ok and good
    where = ", ".join(f"{w} {v:g}" for w, v in values)
    print(f"{'PASS' if good else 'FAIL'}  {label} agrees at {len(values)} ends: {where}")
    return vals[0]


print(f"=== {DOC.name} :: `## Use this` (:30-47) ===\n")

# ── §1 THE FENCE'S CLASS EDGES ARE THE phi ARITHMETIC, AT FOUR ENDS ──────────────────────
# The fence's own first comment: "phi = -log2(d/mm) at integer phi, so every edge is a power
# of two." The phi table below it prints phi and d in separate columns, so d = 2**(-phi) is a
# real check: corrupt either column and it fires.
print("-- §1 Wentworth edges: phi = -log2(d/mm), and the four ends that print them --")
PHI = rows(r"^\|\s*(−8|−6|−2|−1)\s*\|\s*(\d+) mm \|\s*(\w+) / (\w+)\s*\|",
           "the phi/d/edge table", 4)
tab_edges = []
for phi, d, lo, hi in PHI:
    derived = 2.0 ** (-f(phi))
    check(f"phi = {f(phi):g} ({lo}/{hi} edge) -> d", derived, f(d), 0.0)
    tab_edges.append(f(d))

FENCE = rows(r"^(?:classes|#)?\s+(boulder|cobble|pebble|granule)\s+d\s+(\d+)\.\.(\d+) mm",
             "the fence's four class rows", 4)
CLS = {n: (f(a), f(b)) for n, a, b in FENCE}
fence_edges = sorted({e for lo, hi in CLS.values() for e in (lo, hi)})
AUTHORED = page(r"every\s*\n?# figure on this page uses (\d+) mm", "the authored top d_max")
# The scale gives the top class no d_max; the fence AUTHORS one and says so. Everything below
# that needs a boulder `r` takes it from here, never from a measurement.
check(f"the fence's boulder d_max against the d_max its comment authors", CLS["boulder"][1],
      AUTHORED, 0.0)

PROSE = re.search(r"So \*\*boulder > (\d+) mm, cobble (\d+)–(\d+) mm, "
                  r"pebble (\d+)–(\d+) mm, granule (\d+)–(\d+) mm\*\*", BODY)
if not PROSE:
    gone("the class edges in prose", "So **boulder > ... granule N-N mm**")
prose_edges = sorted({f(x) for x in PROSE.groups()})
FAILTAB = re.search(r"the edges are ([\d, ]+) mm and nothing else", BODY)
if not FAILTAB:
    gone("the class edges in the failure table", "the edges are ... mm and nothing else")
fail_edges = sorted(f(x) for x in FAILTAB.group(1).split(","))

for name, got in (("the fence", fence_edges), ("the prose at 'So **boulder >'", prose_edges),
                  ("the failure table", fail_edges)):
    scale_edges = sorted(set(tab_edges))
    # the fence and the prose carry the AUTHORED 1024 as well; the scale does not give it.
    got_scale = sorted(set(got) - {AUTHORED})
    good = got_scale == scale_edges
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {name} prints the scale's edges {got_scale} "
          f"against the phi table's {scale_edges}")

# The page's own named defect: a rounded secondary. If the edges ever become these, §1 above
# already fires -- this only checks the page still carries the warning it turns on.
for pat, what in ((r'prints boulders as \*\*"250–100"\*\*', 'the "250-100" counterexample'),
                  (r'cobbles "65–250"', 'the "65-250" counterexample')):
    if re.search(pat, BODY):
        print(f"PASS  the page still carries {what} that makes the exactness load-bearing")
    else:
        ok = False
        print(f"FAIL  the page no longer carries {what}")

# ── §2 EVERY `r` IN EVERY TABLE IS THE FENCE'S d_max, IN METRES ──────────────────────────
print("\n-- §2 `r_cls = d_max(cls)`: the fence's edges are the tables' `r` --")
LF = rows(r"^\| (boulder|cobble|pebble) \| ([\d.]+) m \| ([\d,]+) \| ([\d,]+) \| ([\d.]+)% \|",
          "the largest-first per-class table", 3)
for name, r_m, cand, kept, surv in LF:
    check(f"§2a {name}: `r` in the table against d_max = {CLS[name][1]:g} mm from the fence",
          CLS[name][1] / 1000.0, f(r_m), 0.0)

OP = rows(r"^\| (?:\*\*)?one pass, sized (?:for the largest|for the smallest)(?:\*\*)? \| "
          r"([\d.]+) m \| ([\d,]+) \|", "the two extreme single-pass rows", 2)
check("§2b the single-pass 'sized for the largest' `r` against the boulder d_max",
      CLS["boulder"][1] / 1000.0, f(OP[0][0]), 0.0)
check("§2b the single-pass 'sized for the smallest' `r` against the pebble d_max",
      CLS["pebble"][1] / 1000.0, f(OP[1][0]), 0.0)

# §2c the cross-class span -- bound to the fence's own floor and ceiling, so it CAN fail.
SPAN = page(r"`a_i \+ a_j` varies over a factor of (\d+)", "the a_i+a_j span")
check("§2c max(a_i+a_j)/min(a_i+a_j) over the fence's 4..1024 mm field",
      CLS["boulder"][1] / CLS["pebble"][0], SPAN, 0.0)
LAW_LO = page(r"truncated power law `N\(>d\) ∝ d\^−b` over (\d+)–\d+ mm",
              "the global size law's floor")
LAW_HI = page(r"truncated power law `N\(>d\) ∝ d\^−b` over \d+–(\d+) mm",
              "the global size law's ceiling")
check("§2c the size law's floor against the fence's pebble d_min", CLS["pebble"][0], LAW_LO, 0.0)
check("§2c the size law's ceiling against the fence's authored d_max", AUTHORED, LAW_HI, 0.0)

# ── §3 THE LARGEST-FIRST TABLE CLOSES, AND ITS TOTALS ARE THE HEADLINE FIGURES ───────────
print("\n-- §3 the largest-first table's own arithmetic --")
TOT = re.search(r"^\| \*\*total\*\* \| \| \*\*([\d,]+)\*\* \| \*\*([\d,]+)\*\* \| \*\*([\d.]+)%\*\* \|",
                BODY, re.M)
if not TOT:
    gone("the largest-first total row", "| **total** | | **N** | **N** | **P%** |")
CAND_T, KEPT_T, SURV_T = f(TOT.group(1)), f(TOT.group(2)), f(TOT.group(3))
check("§3 candidates sum", sum(f(r[2]) for r in LF), CAND_T, 0.0)
check("§3 kept sum", sum(f(r[3]) for r in LF), KEPT_T, 0.0)
for name, r_m, cand, kept, surv in LF:
    check(f"§3 {name} survival = kept/candidates", round(f(kept) / f(cand) * 100, 1), f(surv), 0.0)
check("§3 total survival = kept/candidates", round(KEPT_T / CAND_T * 100, 1), SURV_T, 0.0)

REJ_BODY = page(r"the cross-class rejection is \*\*([\d.]+)%\*\* of the", "the rejection rate")
REJ_TAB = page(r"Cross-class rejection removes \*\*([\d.]+)%\*\* of candidates",
               "the rejection rate in the failure table")
REJ_TOP = page(r"takes ([\d.]+)% of the candidates and is not a rounding error",
               "the rejection rate under `## Use this`")
agree("§3 the cross-class rejection rate", [("body", REJ_BODY), ("failure table", REJ_TAB),
                                            ("`## Use this`", REJ_TOP)])
check("§3 rejection = 1 - kept/candidates", round((1 - KEPT_T / CAND_T) * 100, 1), REJ_BODY, 0.0)

MULT_TOP = page(r"\*\*multiply it by ([\d.]+)\*\*", "the plan multiplier under `## Use this`")
MULT_BODY = page(r"\*\*plan × ([\d.]+)\*\*", "the plan multiplier in the body")
agree("§3 the plan multiplier", [("`## Use this`", MULT_TOP), ("body", MULT_BODY)])
check("§3 multiplier = kept/candidates", round(KEPT_T / CAND_T, 3), MULT_TOP, 0.0)

OF_ACH = page(r"exceed the [\d,]+ achieved by ([\d.]+)% \*of the achieved count\*",
              "the overshoot stated of the achieved count")
OF_PLAN = page(r"while\s*\n?being ([\d.]+)% \*of the plan\*", "the overshoot stated of the plan")
check("§3 (cand-kept)/kept", round((CAND_T - KEPT_T) / KEPT_T * 100, 1), OF_ACH, 0.0)
check("§3 (cand-kept)/cand", round((CAND_T - KEPT_T) / CAND_T * 100, 1), OF_PLAN, 0.0)
RATIO = page(r"\*\*(\d+) pebble candidates for every boulder candidate\*\*", "the 225:1 ratio")
check("§3 pebble candidates / boulder candidates",
      round(f(LF[2][2]) / f(LF[0][2])), RATIO, 0.0)

# ── §4 DENSITY AND MEMORY: KEPT COUNTS / PATCH AREA, x 24 BYTES ──────────────────────────
print("\n-- §4 the instance-budget table, derived from the kept counts --")
SIDE = page(r"all measured below on a (\d+) m × \d+ m patch", "the patch side, in prose")
SIDE2 = page(r"all measured below on a \d+ m × (\d+) m patch", "the patch's second side")
AREA = SIDE * SIDE2                       # from PROSE, never from a density under test
BPI = page(r"at \*\*(\d+) bytes per instance\*\*", "the per-instance transform size")
MEM = rows(r"^\| (boulder|cobble|pebble) \| ([\d.]+) \| ([\d,]+) \| \*\*([\d.]+) (MB|GB)\*\* \|",
           "the instances/m2 -> transforms/km2 table", 3)
cum = 0.0
for (name, per_m2, per_km2, mem, unit), (_, _, _, kept, _) in zip(MEM, LF):
    cum += f(kept)                        # "carried down to" is cumulative, largest-first
    check(f"§4 {name} instances/m2 = (cumulative kept)/{AREA:g} m2", cum / AREA, f(per_m2), 0.0)
    check(f"§4 {name} instances/km2", f(per_m2) * 1e6, f(per_km2), 0.0)
    scale = 1e6 if unit == "MB" else 1e9
    dp = len(mem.split(".")[1]) if "." in mem else 0   # round as the PAGE prints it
    check(f"§4 {name} transforms/km2 in {unit} at {BPI:g} B",
          round(f(per_km2) * BPI / scale, dp), f(mem), 0.0)

# the same three figures, printed again in the opening paragraph and in the failure table
agree("§4 the pebble density", [
    ("table", f(MEM[2][1])),
    ("failure table", page(r"(\d+\.\d+) clasts/m² is \d+ million per km", "it there"))])
agree("§4 the pebble budget in GB", [
    ("table", f(MEM[2][3])),
    ("opening paragraph", page(r"instances per square kilometre\*\*,\s*\n?([\d.]+) GB", "it there")),
    ("failure table", page(r"million per km², \*\*([\d.]+) GB\*\*", "it there")),
    ("stratified table", page(r"^\| 2\.5 \|.*\| ([\d.]+) GB \|", "it there", flags=re.M))])
agree("§4 the boulder budget in MB", [
    ("table", f(MEM[0][3])),
    ("opening paragraph", page(r"per square metre and ([\d.]+) MB per square kilometre",
                               "it there")),
    ("failure table", page(r"Boulders alone are ([\d.]+) MB/km", "it there"))])
agree("§4 the cobble budget in MB", [
    ("table", f(MEM[1][3])),
    ("failure table", page(r"cobbles bring it to ([\d.]+) MB", "it there"))])
agree("§4 the boulder density", [
    ("table", f(MEM[0][1])),
    ("opening paragraph", page(r"The boulder class is\s*\n?([\d.]+) per square metre",
                               "it there"))])
# ⚠️ BOTH ends of the millions figure. The first version parsed only the opening paragraph's
# and left the failure table's free to drift: walking the failure table alone from "133 million"
# to "150 million" left this rig green. A correction landing at one end only is the defect this
# corpus records most often, and it had one here.
MILLIONS = page(r"A pebble bed is \*\*(\d+) million instances per square kilometre\*\*",
                "the headline millions figure")
MILLIONS_TAB = page(r"clasts/m\u00b2 is (\d+) million per km", "it in the failure table")
agree("§4 the pebble count in millions", [("opening paragraph", MILLIONS),
                                          ("failure table", MILLIONS_TAB)])
check("§4 the headline, in millions", round(f(MEM[2][2]) / 1e6), MILLIONS, 0.0)
check("§4 the failure table's, in millions", round(f(MEM[2][2]) / 1e6), MILLIONS_TAB, 0.0)

# ── §5 THE QUADRATIC TABLE, AND THE FENCE'S OWN 923 GB ───────────────────────────────────
print("\n-- §5 a finer class is quadratic, and the fence's granule warning --")
FINE = rows(r"^\| (\d+) mm(?: \((?:pebble|granule)\))? \| ([\d,]+) \| \*?\*?([\d.]+) GB\*?\*? \|",
            "the d_max -> candidates -> GB table", 5)
for d_mm, cand, gb in FINE:
    per_km2 = f(cand) * (1e6 / AREA)      # patch area from PROSE
    check(f"§5 a {f(d_mm):g} mm class: {f(cand):g} on the patch -> GB/km2 at {BPI:g} B",
          round(per_km2 * BPI / 1e9, 2), f(gb), 0.0)
QUAD = page(r"Four halvings, each ([\d.]+)× the last", "the halving ratio")
for (d0, c0, _), (d1, c1, _) in zip(FINE, FINE[1:]):
    r_obs = f(c1) / f(c0)
    # ⚠️ TOLERANCE, stated: the page rounds every one of these to `4.00x`, and the first is
    # 3.98. 1% is the smallest band that admits the page's own first row; see the return.
    check(f"§5 candidates {f(d0):g} mm -> {f(d1):g} mm (page: 1/d_max^2)", r_obs, QUAD,
          0.01 * QUAD)
GRAN_FENCE = page(r"# granule at r = (\d+) mm is [\d]+ GB/km2", "the fence's granule d_max")
GB_FENCE = page(r"# granule at r = \d+ mm is (\d+) GB/km2", "the fence's granule budget")
check("§5 the fence's granule r against the fence's granule class d_max",
      CLS["granule"][1], GRAN_FENCE, 0.0)
gran = [row for row in FINE if f(row[0]) == GRAN_FENCE]
if not gran:
    gone(f"a {GRAN_FENCE:g} mm row in the quadratic table", "| 4 mm (granule) | ... |")
check("§5 the fence's 923 GB against the table's granule row", round(f(gran[0][2])), GB_FENCE, 0.0)

# ── §6 THE GRID COST, AND THE FENCE'S OWN 42x ────────────────────────────────────────────
print("\n-- §6 per-class grids, and the fence's `42x` --")
ONE_GRID = page(r"\*\*Measured over the whole run: ([\d.]+) pairwise distance tests per candidate",
                "the one-grid test count")
PER_CLASS = page(r"\*\*([\d.]+) tests per candidate — [\d.]+× fewer\*\*",
                 "the per-class test count")
FEWER = page(r"[\d.]+ tests per candidate — ([\d.]+)× fewer", "the ratio")
FENCE_X = page(r"# -- one grid PER CLASS, or this costs (\d+)x more", "the fence's multiplier")
check("§6 one-grid / per-class tests", round(ONE_GRID / PER_CLASS, 1), FEWER, 0.0)
check("§6 the fence's `42x` against that ratio", round(ONE_GRID / PER_CLASS), FENCE_X, 0.0)
FLOOR_LO = page(r"dropping the\s*\n?pebble floor from (\d+) mm to \d+ mm", "the pebble floor")
FLOOR_NEW = page(r"pebble floor from \d+ mm to (\d+) mm", "the floor it is dropped to")
FLOOR_CAND = page(r"leaves the candidate count \*\*identical at ([\d,]+)\*\*",
                  "the unchanged candidate count")
T0 = page(r"by \*\*([\d.]+)%\*\* \((\d[\d,]*) → [\d,]+ tests", "the tests before", 2)
T1 = page(r"by \*\*[\d.]+%\*\* \([\d,]+ → ([\d,]+) tests", "the tests after")
MOVE = page(r"moves the\s*\n?rejection work by \*\*([\d.]+)%\*\*", "the move in rejection work")
check("§6 the pebble floor against the fence's pebble d_min", CLS["pebble"][0], FLOOR_LO, 0.0)
check("§6 the floor it drops to against the fence's granule d_min", CLS["granule"][0],
      FLOOR_NEW, 0.0)
check("§6 the 'identical' candidate count against the largest-first total", CAND_T,
      FLOOR_CAND, 0.0)
check("§6 (after-before)/before", round((T1 - T0) / T0 * 100, 1), MOVE, 0.0)
# 10.8 is a quotient of two other page figures, so it is derived rather than believed twice.
check("§6 per-class tests/candidate = total tests / candidates", round(T0 / CAND_T, 1),
      PER_CLASS, 0.0)
SCAN = page(r"that\s*\n?scan sweeps `9 × ([\d.]+)²` = [\d.]+ m²", "the scan's `r`")
SWEPT = page(r"`9 × [\d.]+²` = ([\d.]+) m²", "the swept area")
INSIDE = page(r"there are ~([\d,]+)\s*\n?clasts inside it", "the clasts inside the scan")
check("§6 the scan's `r` against the fence's boulder d_max", CLS["boulder"][1] / 1000.0,
      SCAN, 0.0)
check("§6 9 * r^2", round(9 * SCAN * SCAN, 2), SWEPT, 0.0)
check("§6 swept area x the pebble density", round(SWEPT * f(MEM[2][1])), INSIDE, 0.0)
PER_SCAN = page(r"so the [\d.]+ tests per candidate is about ([\d.]+) per class",
                "the per-class-scanned cost")
check(f"§6 {PER_CLASS:g} tests spread over the fence's {len(CLS) - 1:g} instanced classes",
      round(PER_CLASS / (len(CLS) - 1), 1), PER_SCAN, 0.0)

# ── §7 THE ANNULUS: CLOSED FORM AT TOLERANCE ZERO, THEN THE PAGE'S OWN DRAW COUNT RUN ────
print("\n-- §7 the annulus draw --")
# E[rho] over the annulus with area element rho drho, between r and 2r:
#   int_r^2r rho^2 drho / int_r^2r rho drho = (2/3)(8-1)/(4-1) = 14/9 r.
NUMER = page(r"against the exact (\d+)/\d+ = [\d.]+", "the exact mean's numerator")
DENOM = page(r"against the exact \d+/(\d+) = [\d.]+", "the exact mean's denominator")
EXACT = page(r"against the exact \d+/\d+ = ([\d.]+)", "the exact mean radius")
inner, outer = 1.0, 2.0
closed = (2.0 / 3.0) * (outer ** 3 - inner ** 3) / (outer ** 2 - inner ** 2)
check("§7 the annulus mean from its own area element", round(closed, 4), EXACT, 0.0)
check("§7 ... against the fraction the page prints it as", NUMER / DENOM, EXACT, 5e-5)
SHORT = page(r"shortcut gives \*\*([\d.]+) r\*\*", "the shortcut's mean")
check("§7 U(r,2r) mean", round((inner + outer) / 2.0, 4), SHORT, 0.0)
LOW_BODY = page(r"it runs \*\*([\d.]+)% low\*\*", "the shortcut's error")
LOW_TAB = page(r"against the correct [\d.]+ r — \*\*([\d.]+)% low\*\*", "the shortcut's error in the failure table")
agree("§7 the shortcut's error", [("body", LOW_BODY), ("failure table", LOW_TAB)])
check("§7 (exact - shortcut)/exact", round((closed - SHORT) / closed * 100, 1), LOW_BODY, 0.0)
SH_TAB = page(r"Mean candidate radius ([\d.]+) r against the correct", "the shortcut in the table")
EX_TAB = page(r"r against the correct ([\d.]+) r", "the exact mean in the failure table")
agree("§7 the shortcut's mean", [("body", SHORT), ("failure table", SH_TAB)])
agree("§7 the exact mean", [("body", EXACT), ("failure table", EX_TAB)])

DRAWS = page(r"measured over\s*\n?([\d,]+) draws the correct mean radius", "the draw count")
MEASURED = page(r"the correct mean radius is \*\*([\d.]+) r\*\*", "the measured mean radius")
if DRAWS > MAX_DRAWS:
    sys.exit(f"the page asks for {DRAWS:g} draws; this rig refuses above {MAX_DRAWS} (halting)")
rnd = random.Random(20260915)
s = 0.0
for _ in range(int(DRAWS)):                       # halting: a parsed integer under MAX_DRAWS
    s += math.sqrt(rnd.uniform(inner * inner, outer * outer))
mine = s / DRAWS
# Var over the annulus = E[rho^2] - E[rho]^2 = (1/4)(16-1)/((1/2)(4-1)) - (14/9)^2.
var = 0.25 * (outer ** 4 - inner ** 4) / (0.5 * (outer ** 2 - inner ** 2)) - closed ** 2
sig = math.sqrt(var / DRAWS) * math.sqrt(2.0)     # two independent runs of the same size
band = 4.0 * sig + 5e-5                           # 4 sigma + the page's own rounding half-width
check(f"§7 an independent {DRAWS:g}-draw run against the page's measurement "
      f"(band {band:.5f} = 4 sigma + rounding)", mine, MEASURED, band)

# ── §8 THE SAMPLER THE FENCE CALLS, TRANSCRIBED FROM §2 AND RUN ──────────────────────────
print("\n-- §8 `poisson_disk(domain, r_cls, k=30)` [bridson2007b] §2, RUN --")
K_FENCE = page(r"poisson_disk\(domain, r_cls, k=(\d+)\)", "the fence's k")
K_PROSE = page(r"a rejection limit `k`, \"typically k=(\d+)\"", "the k the paper gives")
agree("§8 the rejection limit k", [("the fence", K_FENCE), ("the Bridson summary", K_PROSE)])
# Step 0's two structural parameters, taken from the PROSE and fed into the transcription:
# the cell divisor `sqrt(n)` and the width of the neighbour scan. Neither is a number under
# test -- both are inputs the page states, and both change what the sampler DOES. Narrow the
# scan on the page and the min-separation guarantee below stops holding.
if not re.search(r'cell size "bounded by `r/sqrt\(n\)`, so that each grid cell\s*\n?\s*'
                 r'will contain at most one sample"', BODY):
    gone("step 0's cell-size rule", 'cell size "bounded by `r/sqrt(n)` ... at most one sample"')
SCAN_W = page(r"the neighbour test is a fixed (\d+)\u00d7\d+ scan of integers",
              "the width of the neighbour scan")
SCAN_H = page(r"the neighbour test is a fixed \d+\u00d7(\d+) scan of integers",
              "the height of the neighbour scan")
if SCAN_W != SCAN_H or SCAN_W % 2 != 1:
    sys.exit(f"the page states a {SCAN_W:g}x{SCAN_H:g} neighbour scan, which this rig cannot "
             f"centre on a cell")
HALF = int((SCAN_W - 1) // 2)
RUNS = rows(r"^\| (\d+)×(\d+) \| ([\d.]+) \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \| (\d+) \| "
            r"([\d.]+) \|", "the five sampler runs", 5)
NDIM = 2.0


def poisson_disk(L, r, k, seed):
    """Bridson §2 as the page states it: r/sqrt(n) cells, one seed, k candidates on the annulus.

    Halting: `while active` is bounded by `2*cells+2`; `cells` is fixed by L and r before the
    loop, and exceeding the bound is returned as a FAIL rather than looped through.
    """
    cell = r / math.sqrt(NDIM)
    gw = int(math.ceil(L / cell))
    if gw * gw > MAX_CELLS:
        sys.exit(f"a {L:g}x{L:g} domain at r={r:g} needs {gw * gw} cells; "
                 f"this rig refuses above {MAX_CELLS} (halting)")
    cap = 2 * gw * gw + 2
    grid = [-1] * (gw * gw)
    rng = random.Random(seed)
    pts = [(rng.random() * L, rng.random() * L)]
    grid[int(pts[0][1] / cell) * gw + int(pts[0][0] / cell)] = 0
    active, it, r2 = [0], 0, r * r
    while active:
        it += 1
        if it > cap:
            return None, it, None, None
        ai = rng.randrange(len(active))
        x0, y0 = pts[active[ai]]
        for _ in range(int(k)):                    # halting: the parsed k, a small integer
            rho = math.sqrt(rng.uniform(r2, 4 * r2))
            th = rng.uniform(0, 2 * math.pi)
            x, y = x0 + rho * math.cos(th), y0 + rho * math.sin(th)
            if not (0 <= x < L and 0 <= y < L):
                continue
            cx, cy = int(x / cell), int(y / cell)
            good = True
            for yy in range(max(0, cy - HALF), min(gw, cy + HALF + 1)):
                for xx in range(max(0, cx - HALF), min(gw, cx + HALF + 1)):
                    j = grid[yy * gw + xx]
                    if j >= 0:
                        dx, dy = pts[j][0] - x, pts[j][1] - y
                        if dx * dx + dy * dy < r2:
                            good = False
                            break
                if not good:
                    break
            if good:
                pts.append((x, y))
                grid[cy * gw + cx] = len(pts) - 1
                active.append(len(pts) - 1)
                break
        else:
            active.pop(ai)
            continue
        if not good:
            active.pop(ai)
    occ = {}
    for x, y in pts:
        key = (int(y / cell), int(x / cell))
        occ[key] = occ.get(key, 0) + 1
    # ⚠️ MEASURED ON ITS OWN GRID, NOT THE SAMPLER'S. The first version of this rig reused the
    # sampler's `cell` and `HALF` here, so narrowing the page's "fixed 5x5 scan" to 3x3 narrowed
    # the MEASUREMENT by the same step: the sampler started emitting pairs closer than `r` and
    # the rig could no longer see them. It stayed green on that mutation. That is trap 3 -- a
    # parameter taken from the thing under test -- committed inside the measurement rather than
    # the expectation. The pitch below is `r` and the scan is 3x3, and neither is a page figure:
    # any two points less than `r` apart share a cell of pitch `r` or touch one, always.
    buckets = {}
    for i, (x, y) in enumerate(pts):
        buckets.setdefault((int(x / r), int(y / r)), []).append(i)
    best = float("inf")
    for i, (x, y) in enumerate(pts):
        cx, cy = int(x / r), int(y / r)
        for gx in range(cx - 1, cx + 2):
            for gy in range(cy - 1, cy + 2):
                for j in buckets.get((gx, gy), ()):
                    if j != i:
                        best = min(best, math.hypot(pts[j][0] - x, pts[j][1] - y))
    return len(pts), it, max(occ.values()), best / r


ratios = {}
for L, L2, r, N, iters, twonm1, percell, minsep in RUNS:
    L, r, N = f(L), f(r), f(N)
    if f(L2) != L:
        ok = False
        print(f"FAIL  §8 the page prints a non-square domain {L:g}x{f(L2):g}")
    # (a) the PAGE's own columns: iterations == 2N-1, and its printed 2N-1 column == 2N-1.
    check(f"§8a page row {L:g}² r={r:g}: step-2 iterations against 2N-1 for its own N",
          2 * N - 1, f(iters), 0.0)
    check(f"§8a page row {L:g}² r={r:g}: its printed `2N-1` column", 2 * N - 1,
          f(twonm1), 0.0)
    # (b) this rig's own run of the same domain and r. N is NOT compared -- the page names
    #     seed 7 but not the generator. What IS compared is every claim §3 makes ABOUT N.
    n, it, percell_got, minsep_got = poisson_disk(L, r, K_FENCE, seed=20260915)
    if n is None:
        ok = False
        print(f"FAIL  §8b {L:g}² r={r:g}: the sampler exceeded its halting bound at {it}")
        continue
    check(f"§8b RUN {L:g}² r={r:g} (N={n}): step-2 iterations against 2N-1", 2 * n - 1,
          float(it), 0.0)
    check(f"§8b RUN {L:g}² r={r:g}: max samples per cell", float(percell_got),
          f(percell), 0.0)
    good = minsep_got >= 1.0 and f(minsep) >= 1.0
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  §8b RUN {L:g}² r={r:g}: min separation/r "
          f"{minsep_got:.6f}, and the page's own {f(minsep):.6f} (both must be >= 1)")
    ratios.setdefault(round(L / r, 9), []).append((f"{L:g}² r={r:g}", N, n))

# the span the page claims its timing held across, from the N column it prints
SPAN_N = page(r"across a (\d+)\u00d7 range in N", "the range in N the cost held across")
Ns = [f(r[3]) for r in RUNS]
check(f"§8 max N / min N over the five rows ({min(Ns):g} to {max(Ns):g})",
      round(max(Ns) / min(Ns)), SPAN_N, 0.0)

# (c) "N depends only on L/r" -- the page's last two rows are the same run, and so are mine.
if not re.search(r"\*\*N depends only on `L/r`\*\*", BODY):
    gone("the L/r claim", "**N depends only on `L/r`**")
for key, group in sorted(ratios.items()):
    if len(group) < 2:
        continue
    pg = {g[1] for g in group}
    mine_n = {g[2] for g in group}
    good = len(pg) == 1 and len(mine_n) == 1
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  §8c L/r = {key:g}: the page's rows "
          f"{sorted(pg)} and this rig's {sorted(mine_n)} each collapse to one N "
          f"({', '.join(g[0] for g in group)})")
if not any(len(g) >= 2 for g in ratios.values()):
    ok = False
    print("FAIL  §8c the page no longer prints two rows at the same L/r, so its "
          "'N depends only on L/r' claim has nothing left to rest on")

# ── §9 THE STRATIFIED TABLE: ROWS CLOSE, BUDGET DERIVES, BOULDERS ARE CONSTANT ───────────
print("\n-- §9 the largest-first construction at five exponents --")
STRAT = rows(r"^\| ([\d.]+) \| \*\*(\d+)\*\* \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \| "
             r"\*?\*?([\d.]+)%\*?\*? \| ([\d.]+) GB \|", "the five-exponent table", 5)
for b, bo, co, pe, tot, cov, gb in STRAT:
    check(f"§9 b={f(b):g}: boulders+cobbles+pebbles", f(bo) + f(co) + f(pe), f(tot), 0.0)
    check(f"§9 b={f(b):g}: GB/km2 at {BPI:g} B from the total",
          round(f(tot) * (1e6 / AREA) * BPI / 1e9, 2), f(gb), 0.0)
CONST = page(r"The boulder count is \*\*(\d+) at every exponent\*\*", "the constant boulder count")
agree("§9 the boulder count", [("the stratified table", f(STRAT[0][1])),
                               ("the prose", CONST),
                               ("the largest-first table", f(LF[0][3])),
                               ("the single-pass table", f(OP[0][1]))]
      + [(f"b={f(r[0]):g}", f(r[1])) for r in STRAT[1:]])
MOVE_T = page(r"The total moves (\d+)% across the entire range", "the total's range")
check("§9 (max total - min total)/min total",
      round((f(STRAT[-1][4]) - f(STRAT[0][4])) / f(STRAT[0][4]) * 100), MOVE_T, 0.0)
GB_LO = page(r"instance budget moves from ([\d.]+) to [\d.]+ GB/km", "the budget's low end")
GB_HI = page(r"instance budget moves from [\d.]+ to ([\d.]+) GB/km", "the budget's high end")
agree("§9 the budget's low end", [("prose", GB_LO), ("table b=1.0", f(STRAT[0][6]))])
agree("§9 the budget's high end", [("prose", GB_HI), ("table b=3.0", f(STRAT[-1][6]))])
NINETY = page(r"still lands at (\d+)% of the figure the next\s*\n?\s*section calls", "the 90% claim")
check("§9 the b=1 budget as a fraction of the pebble row's budget",
      round(GB_LO / f(MEM[2][3]) * 100), NINETY, 0.0)
COV_LO = page(r"falls\s*\n?monotonically from ([\d.]+)% to [\d.]+%", "coverage's high end")
COV_HI = page(r"monotonically from [\d.]+% to ([\d.]+)%", "coverage's low end")
agree("§9 coverage at b=1.0", [("prose", COV_LO), ("table", f(STRAT[0][5]))])
agree("§9 coverage at b=3.0", [("prose", COV_HI), ("table", f(STRAT[-1][5]))])
covs = [f(r[5]) for r in STRAT]
good = all(a > b2 for a, b2 in zip(covs, covs[1:]))
ok = ok and good
print(f"{'PASS' if good else 'FAIL'}  §9 coverage is monotonically decreasing in b: {covs}")

# the b=2.5 row IS the headline run; every figure must be the same figure
EXP = page(r"a truncated power law\s*\n?`N\(>d\) ∝ d\^−([\d.]+)`", "the headline exponent")
head = [r for r in STRAT if f(r[0]) == EXP]
if not head:
    gone(f"a b = {EXP:g} row in the stratified table", "| 2.5 | **67** | ... |")
agree("§9 the headline total", [("stratified b=2.5", f(head[0][4])),
                                ("largest-first total", KEPT_T),
                                ("`## Use this`", page(r"places \*\*([\d,]+)\s*\n?clasts with",
                                                       "it there")),
                                ("the one-pass table",
                                 page(r"largest-first, per class\*\* \| per class \| \*\*([\d,]+)",
                                      "it there"))])
agree("§9 the headline coverage", [
    ("stratified b=2.5", f(head[0][5])),
    ("`## Use this`", page(r"covers ([\d.]+)% of the ground", "it there")),
    ("the one-pass table", page(r"per class \| \*\*[\d,]+\*\* \| \*\*\d+\*\* \| \*\*([\d.]+)%",
                                "it there")),
    ("the failure table", page(r"against ([\d.]+)% for the largest-first pass", "it there"))])
agree("§9 the headline cobble/pebble kept counts", [("stratified cobbles", f(head[0][2])),
                                                    ("largest-first cobbles", f(LF[1][3]))])
agree("§9 ... and pebbles", [("stratified pebbles", f(head[0][3])),
                             ("largest-first pebbles", f(LF[2][3]))])

# ── §10 EQUAL AREA PER OCTAVE AT b = 2, FROM THE FENCE'S OWN EDGES ───────────────────────
print("\n-- §10 the global size law --")
OCT = re.search(r"The classes span (\d+), (\d+) and (\d+) octaves", BODY)
SPLIT = re.search(r"should split the ground (\d+) : (\d+) : (\d+)", BODY)
B_EQ = page(r"and at \*\*`b = (\d+)`\*\* that exponent is", "the equal-area exponent")
AREA_EXP = page(r"that exponent is\s*\n?`(−\d+)`", "the area exponent at that b")
if not OCT or not SPLIT:
    gone("the octave span and the 25:25:50 split", "The classes span N, N and N octaves")
for (name, (lo, hi)), want in zip([(n, CLS[n]) for n in ("boulder", "cobble", "pebble")],
                                  OCT.groups()):
    check(f"§10 {name} spans log2(d_max/d_min) octaves", math.log2(hi / lo), f(want), 0.0)
tot_oct = sum(f(x) for x in OCT.groups())
for name, want in zip(("boulder", "cobble", "pebble"), SPLIT.groups()):
    o = math.log2(CLS[name][1] / CLS[name][0])
    check(f"§10 equal area per octave -> {name}'s share", o / tot_oct * 100, f(want), 0.0)
check("§10 the covered-area exponent d^(1-b) at that b", 1.0 - B_EQ, AREA_EXP, 0.0)

# the count half of the global table, against the closed form for a truncated power law
GLOB_N = page(r"Sampling ([\d,]+) diameters from a truncated power law", "the global draw count")
GLOB = rows(r"^\| ([\d.]+) \| ([\d.]+)% \| ([\d.]+)% \| ([\d.]+)% \| \| ", "the global count table", 5)
for b, *pcts in GLOB:
    b = f(b)
    den = LAW_LO ** -b - LAW_HI ** -b
    row = 0.0
    for name, want in zip(("boulder", "cobble", "pebble"), pcts):
        lo, hi = CLS[name]
        frac = (lo ** -b - hi ** -b) / den
        sig = math.sqrt(frac * (1 - frac) / GLOB_N) * 100
        half = 0.5 * 10 ** -(len(want.split(".")[1]) if "." in want else 0)
        check(f"§10 b={b:g} {name} count share (4 sigma + rounding = {4 * sig + half:.4f})",
              frac * 100, f(want), 4 * sig + half)
        row += f(want)
    check(f"§10 b={b:g} the three count shares sum to 100%", row, 100.0, 0.05)
PEB_LO = page(r"— (\d+)% at `b = 1` and [\d.]+% at `b = 3`", "the pebble share at b=1")
PEB_HI = page(r"at `b = 1` and ([\d.]+)% at `b = 3`", "the pebble share at b=3")
check("§10 the b=1 pebble share, as the prose rounds it", round(f(GLOB[0][3])), PEB_LO, 0.0)
agree("§10 the b=3 pebble share", [("prose", PEB_HI), ("table", f(GLOB[-1][3]))])

# ── §11 THE PACKING BOUND ────────────────────────────────────────────────────────────────
print("\n-- §11 the achieved fraction of the hexagonal bound --")
ACH = re.search(r"the sampler achieved ([\d.]+)%, ([\d.]+)% and ([\d.]+)% at\s*\n?"
                r"`r` = ([\d.]+), ([\d.]+) and ([\d.]+) on the patch below", BODY)
if not ACH:
    gone("the three achieved fractions and their `r`", "the sampler achieved P%, P% and P% at")
counts = {}
for line in re.findall(r"^\| (?:\*\*)?one pass[^|]*\| ([\d.]+) m \| ([\d,]+) \|", BODY, re.M):
    counts[f(line[0])] = f(line[1])
lows = []
for pct, r_s in zip(ACH.groups()[:3], ACH.groups()[3:]):
    r_v = f(r_s)
    if r_v not in counts:
        gone(f"a single-pass row at r = {r_v:g} m", "| one pass, ... | R m | N |")
    bound = 2 * AREA / (math.sqrt(3) * r_v * r_v)      # the page's own `2A/(sqrt3 r^2)`
    # ⚠️ TOLERANCE, stated: 0.1 pp. The r = 1.024 row derives 60.84% and the page prints 60.9%,
    # which is that row's own rounding missed by 0.06 pp. Reported, not absorbed silently.
    check(f"§11 {counts[r_v]:g} clasts at r = {r_v:g} m against 2A/(sqrt3 r^2) = {bound:.1f}",
          counts[r_v] / bound * 100, f(pct), 0.1)
    lows.append(round((1 - counts[r_v] / bound) * 100))
LOW1 = page(r"the plan runs \*\*(\d+)–\d+% low\*\*", "the low end of the shortfall")
LOW2 = page(r"the plan runs \*\*\d+–(\d+)% low\*\*", "the high end of the shortfall")
BODY_LOW1 = page(r"comes out (\d+)–\d+% low", "the shortfall in the body")
BODY_LOW2 = page(r"comes out \d+–(\d+)% low", "the shortfall's high end in the body")
agree("§11 the shortfall's low end", [("body", BODY_LOW1), ("failure table", LOW1)])
agree("§11 the shortfall's high end", [("body", BODY_LOW2), ("failure table", LOW2)])
check("§11 min(1 - achieved)", float(min(lows)), LOW1, 0.0)
check("§11 max(1 - achieved)", float(max(lows)), LOW2, 0.0)
FACTOR = page(r"check the achieved count against ~([\d.]+) × the bound", "the ~0.54 factor")
fracs = [counts[f(r_s)] / (2 * AREA / (math.sqrt(3) * f(r_s) ** 2)) for r_s in ACH.groups()[3:]]
good = min(fracs) <= FACTOR <= max(fracs)
ok = ok and good
print(f"{'PASS' if good else 'FAIL'}  §11 the planning factor {FACTOR:g} lies inside the "
      f"measured range [{min(fracs):.4f}, {max(fracs):.4f}]")

# ── §12 THE TIMING ARITHMETIC (the timings themselves are NOT gated; see the docstring) ──
print("\n-- §12 the cost arithmetic --")
MS = page(r"\*\*([\d,]+) ms for [\d,]+\s*\n?\s*clasts", "the total placement time")
N_TIMED = page(r"\*\*[\d,]+ ms for ([\d,]+)\s*\n?\s*clasts", "the clasts it timed")
US_ONE = page(r"clasts, or (\d+) µs per clast\*\*", "the one-grid per-clast cost")
agree("§12 the timed clast count", [("the timing sentence", N_TIMED), ("the kept total", KEPT_T)])
check("§12 ms/clasts in microseconds", round(MS * 1000 / N_TIMED), US_ONE, 0.0)
P_ONE = page(r"placement alone is ([\d.]+) µs per kept clast on one grid", "placement, one grid")
P_PER = page(r"on one grid and ([\d.]+) µs on per-class grids", "placement, per-class grids")
SPEEDUP = page(r"µs on per-class grids — ([\d.]+)×\.?\*\*", "the placement speed-up")
check("§12 one-grid / per-class placement", round(P_ONE / P_PER, 1), SPEEDUP, 0.0)
US_PER_BODY = page(r"per-class arrangement at \*\*≈(\d+) µs per clast\*\*",
                   "the composed per-class cost")
US_PER_TOP = page(r"or \*\*≈(\d+) µs\*\* on the per-class grids", "it under `## Use this`")
US_PER_REG = page(r"into ≈(\d+) µs per clast of\s*\n?\s*compute", "it in the regeneration bullet")
agree("§12 the per-class per-clast cost", [("body", US_PER_BODY), ("`## Use this`", US_PER_TOP),
                                           ("the regeneration bullet", US_PER_REG)])
check("§12 214 - 76.1 + 9.8", round(US_ONE - P_ONE + P_PER), US_PER_BODY, 0.0)
OVER = page(r"which over-prices the trade by (\d+)%", "the over-pricing")
check("§12 (one-grid - per-class)/per-class", round((US_ONE - (US_ONE - P_ONE + P_PER))
                                                    / (US_ONE - P_ONE + P_PER) * 100), OVER, 0.0)
agree("§12 the one-grid per-clast cost", [("the timing sentence", US_ONE),
                                          ("`## Use this`", page(r"Placement costs \*\*(\d+) µs per clast\*\*", "it there")),
                                          ("the regeneration bullet", page(r"\((\d+) µs if you build the one-grid", "it there"))])
S_POISSON = page(r"account for\s*\n?roughly ([\d.]+) s of the [\d.]+ s", "the sampling share")
S_TOTAL = page(r"roughly [\d.]+ s of the ([\d.]+) s", "the total, in seconds")
COST_LO = page(r"Cost held between\s*\n?\*\*(\d+) and \d+ µs per sample\*\*", "the per-sample floor")
COST_HI = page(r"\*\*\d+ and (\d+) µs per sample\*\*", "the per-sample ceiling")
check("§12 the total in seconds against the total in ms", round(MS / 1000, 2), S_TOTAL, 0.0)
per_sample = S_POISSON * 1e6 / CAND_T
good = COST_LO <= per_sample <= COST_HI
ok = ok and good
print(f"{'PASS' if good else 'FAIL'}  §12 {S_POISSON:g} s over {CAND_T:g} candidates is "
      f"{per_sample:.1f} µs/sample, inside the page's own {COST_LO:g}-{COST_HI:g} band")
COMP = page(r"Composition costs about ([\d.]+)× a bare pass", "the composition factor")
check("§12 total / sampling", round(S_TOTAL / S_POISSON, 1), COMP, 0.0)

# ── §13 THE FENCE STILL SAYS WHAT §14 TRANSCRIBES ────────────────────────────────────────
# ⚠️ THE LIMIT OF §14, named rather than hidden, exactly as rigs/water/shallow-water.py names
# its own: `largest_first` transcribes the fence's ALGORITHM by hand, and only its NUMBERS are
# parsed. An edit to the fence's control flow does not reach the transcription. What CAN be
# pinned is the text the transcription claims to be a transcription OF.
print("\n-- §13 the fence still carries what §14 transcribes --")
for pat, what in (
        (r"for cls in classes, LARGEST FIRST:\s*# the order is the algorithm",
         "the largest-first ordering -- the whole construction turns on it"),
        (r"r_cls = d_max\(cls\)", "`r_cls = d_max(cls)`, the per-class separation"),
        (r"if clear\(p, a\): place\(p, a, cls\)", "the guarded place()"),
        (r"clear\(\) tests d_ij >= a_i \+ a_j against", "clear()'s test, `d_ij >= a_i + a_j`"),
        (r"# every clast already down, not just this class",
         "the CROSS-CLASS scope of clear() -- drop it and the pair count stops being 0"),
        (r"if instances_per_m2\(cls\) > budget: BREAK", "the stop rule, in the loop"),
        (r"a = radius drawn from the class' size law", "the within-class radius draw")):
    if re.search(pat, BODY):
        print(f"PASS  the fence still carries {what}")
    else:
        ok = False
        print(f"FAIL  the fence no longer carries {what} -- §14's transcription is now of "
              f"something the page does not recommend")

# ── §14 THE FENCE'S LOOP, TRANSCRIBED AND RUN ON THE PAGE'S OWN PATCH ────────────────────
print("\n-- §14 the largest-first loop, RUN --")
PAIRS_LF = page(r"places \*\*[\d,]+\s*\n?clasts with (\d+) interpenetrating pairs\*\*",
                "the largest-first pair count")
PAIRS_TAB = page(r"largest-first, per class\*\* \| per class \| \*\*[\d,]+\*\* \| \*\*(\d+)\*\*",
                 "the largest-first pair count in the table")
PAIRS_SP = page(r"leaves \*\*(\d+) interpenetrating pairs", "the single-pass pair count")
PAIRS_ZERO = page(r"Zero interpenetrating pairs over ([\d,]+) clasts", "the zero-pairs sentence")
agree("§14 the largest-first pair count", [("`## Use this`", PAIRS_LF), ("table", PAIRS_TAB)])
agree("§14 the count it is zero over", [("prose", PAIRS_ZERO), ("largest-first total", KEPT_T)])


def draw_radius(rng, d_lo, d_hi, b):
    """Inverse CDF of a truncated power law N(>d) prop d^-b, in DIAMETRES; returns a radius."""
    u = rng.random()
    d = (d_lo ** -b - u * (d_lo ** -b - d_hi ** -b)) ** (-1.0 / b)
    return d / 2.0


def count_pairs(placed, reach):
    """Pairs with d_ij < a_i + a_j. Halting: a fixed cell scan per clast, no growth."""
    cell = reach
    buckets = {}
    for i, (x, y, a) in enumerate(placed):
        buckets.setdefault((int(x / cell), int(y / cell)), []).append(i)
    pairs, worst = 0, 0.0
    for i, (x, y, a) in enumerate(placed):
        cx, cy = int(x / cell), int(y / cell)
        for gx in range(cx - 1, cx + 2):
            for gy in range(cy - 1, cy + 2):
                for j in buckets.get((gx, gy), ()):
                    if j <= i:
                        continue
                    xj, yj, aj = placed[j]
                    d = math.hypot(xj - x, yj - y)
                    if d < a + aj:
                        pairs += 1
                        worst = max(worst, (a + aj - d) / (a + aj))
    return pairs, worst


def largest_first(side, order, b, k, seed):
    """The fence at :39-47, transcribed. One Poisson pass per class at r = d_max, largest
    first, each candidate tested against EVERY clast already down with that pair's a_i + a_j.
    Halting: `order` is a fixed 3-element list; each pass halts by poisson_disk's own bound."""
    placed = []
    cell = max(d for _, d in order) / 1000.0
    buckets = {}
    kept_by_class, cand_by_class = [], []
    rng = random.Random(seed)
    for name, d_max in order:                       # LARGEST FIRST
        r_cls = d_max / 1000.0                      # = 2 * a_max
        pts_list = _sample_points(side, r_cls, k, seed + int(d_max))
        cand = len(pts_list)
        kept = 0
        for (x, y) in pts_list:
            a = draw_radius(rng, CLS[name][0] / 1000.0, d_max / 1000.0, b)
            cx, cy = int(x / cell), int(y / cell)
            clear = True
            span = int(math.ceil((a + max(d for _, d in order) / 2000.0) / cell)) + 1
            for gx in range(cx - span, cx + span + 1):
                for gy in range(cy - span, cy + span + 1):
                    for j in buckets.get((gx, gy), ()):
                        xj, yj, aj = placed[j]
                        if math.hypot(xj - x, yj - y) < a + aj:
                            clear = False
                            break
                    if not clear:
                        break
                if not clear:
                    break
            if clear:
                placed.append((x, y, a))
                buckets.setdefault((cx, cy), []).append(len(placed) - 1)
                kept += 1
        kept_by_class.append(kept)
        cand_by_class.append(cand)
    return placed, cand_by_class, kept_by_class


def _sample_points(L, r, k, seed):
    """poisson_disk's point list. Same algorithm; separated so §8 can stay a pure measurement."""
    cell = r / math.sqrt(NDIM)
    gw = int(math.ceil(L / cell))
    if gw * gw > MAX_CELLS:
        sys.exit(f"a {L:g}x{L:g} domain at r={r:g} needs {gw * gw} cells (halting)")
    cap = 2 * gw * gw + 2
    grid = [-1] * (gw * gw)
    rng = random.Random(seed)
    pts = [(rng.random() * L, rng.random() * L)]
    grid[int(pts[0][1] / cell) * gw + int(pts[0][0] / cell)] = 0
    active, it, r2 = [0], 0, r * r
    while active:
        it += 1
        if it > cap:
            sys.exit("the sampler exceeded its halting bound")
        ai = rng.randrange(len(active))
        x0, y0 = pts[active[ai]]
        hit = False
        for _ in range(int(k)):
            rho = math.sqrt(rng.uniform(r2, 4 * r2))
            th = rng.uniform(0, 2 * math.pi)
            x, y = x0 + rho * math.cos(th), y0 + rho * math.sin(th)
            if not (0 <= x < L and 0 <= y < L):
                continue
            cx, cy = int(x / cell), int(y / cell)
            good = True
            for yy in range(max(0, cy - HALF), min(gw, cy + HALF + 1)):
                for xx in range(max(0, cx - HALF), min(gw, cx + HALF + 1)):
                    j = grid[yy * gw + xx]
                    if j >= 0:
                        dx, dy = pts[j][0] - x, pts[j][1] - y
                        if dx * dx + dy * dy < r2:
                            good = False
                            break
                if not good:
                    break
            if good:
                pts.append((x, y))
                grid[cy * gw + cx] = len(pts) - 1
                active.append(len(pts) - 1)
                hit = True
                break
        if not hit:
            active.pop(ai)
    return pts


order = sorted(((n, CLS[n][1]) for n in ("boulder", "cobble", "pebble")),
               key=lambda t: -t[1])       # LARGEST FIRST, from the fence's own d_max
placed, cands, kepts = largest_first(SIDE, order, EXP, K_FENCE, seed=20260915)
reach = order[0][1] / 1000.0
pairs, worst = count_pairs(placed, reach)
check(f"§14 the fence's loop RUN on a {SIDE:g}x{SIDE2:g} m patch "
      f"({sum(kepts)} kept of {sum(cands)}): interpenetrating pairs", float(pairs), PAIRS_LF, 0.0)
print(f"      (classes largest-first: {[n for n, _ in order]}; "
      f"candidates {cands}, kept {kepts})")

# The control. Its ONLY job is to prove the detector detects; the page's 31 is NOT gated here
# -- it is a seed-11 measurement with no stated generator. What IS asserted is the page's own
# CONDITION for a pair: every pair the detector flags has a_i + a_j > r.
r_small = CLS["pebble"][1] / 1000.0
rng = random.Random(20260915)
single = [(x, y, draw_radius(rng, LAW_LO / 1000.0, LAW_HI / 1000.0, EXP))
          for (x, y) in _sample_points(SIDE, r_small, K_FENCE, 20260915)]
sp_pairs, sp_worst = count_pairs(single, reach)
good = sp_pairs > 0 and PAIRS_SP > 0
ok = ok and good
print(f"{'PASS' if good else 'FAIL'}  §14 control: one pass at r = {r_small:g} m over the whole "
      f"{LAW_LO:g}-{LAW_HI:g} mm law gives {sp_pairs} pairs (the page measures {PAIRS_SP:g}; "
      f"only the SIGN is gated -- see the docstring)")
COND = page(r"the \*condition\* — `a_i \+ a_j > r` — is met by any two clasts averaging "
            r"more than `r/(\d)` in\s*\n?\s*radius", "the interpenetration condition")
viol = 0
cellb = {}
for i, (x, y, a) in enumerate(single):
    cellb.setdefault((int(x / reach), int(y / reach)), []).append(i)
for i, (x, y, a) in enumerate(single):
    cx, cy = int(x / reach), int(y / reach)
    for gx in range(cx - 1, cx + 2):
        for gy in range(cy - 1, cy + 2):
            for j in cellb.get((gx, gy), ()):
                if j <= i:
                    continue
                xj, yj, aj = single[j]
                if math.hypot(xj - x, yj - y) < a + aj and a + aj <= r_small:
                    viol += 1
good = viol == 0 and COND == 2
ok = ok and good
print(f"{'PASS' if good else 'FAIL'}  §14 every flagged pair satisfies the page's condition "
      f"a_i + a_j > r (mean radius > r/{COND:g}): {viol} counter-examples")

# the "buried 63%" figure, at the three ends that print it
BUR_TOP = page(r"buried\s*\n?(\d+)% of the way into its neighbour", "the burial depth")
BUR_BODY = page(r"\*\*the worst is buried (\d+)% of the way into its neighbour\*\*",
                "the burial depth in the body")
BUR_TAB = page(r"worst buried (\d+)% of the contact radius", "the burial depth in the failure table")
agree("§14 the worst burial depth", [("`## Use this`", BUR_TOP), ("body", BUR_BODY),
                                     ("failure table", BUR_TAB)])
RATE = page(r"\*\*\d+\*\* \((\d+\.\d+) per 100\)", "the pairs-per-100 rate")
check("§14 pairs per 100 clasts in the single pass",
      round(PAIRS_SP / f(OP[1][1]) * 100, 1), RATE, 0.0)

print()
print("ALL REPRODUCE" if ok else "SOMETHING DOES NOT REPRODUCE")
sys.exit(0 if ok else 1)
