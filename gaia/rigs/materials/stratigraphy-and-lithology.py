#!/usr/bin/env python3
"""stratigraphy-and-lithology.md's `## Use this` fence, TRANSCRIBED AND RUN against its own page.

EVERY expected value below is parsed out of the document at run time, anchored on PROSE. No
expectation is typed into this file. A figure that has gone missing exits non-zero rather than
being skipped: `grab()` calls `sys.exit`, it does not return a default.

WHAT IS GATED. The fence at :38-52 is a sampler, and its load-bearing claim is the ⚠️ under it:
`s = h` advects with the uplift and `s = h - U_cum` does not. That is a MEASUREMENT with four
numbers (50 000 yr, twenty columns, 40 contacts, 0%), so section 3 transcribes the fence and
RUNS it, twice, over the page's own column and the page's own 2 Myr and 4 Myr budgets. Around it
sit nine more groups of closed-form claims, each reproduced at the page's own printed precision.

TWO-ENDED CLAIMS. Where a figure is printed in more than one place, BOTH are parsed and the two
are asserted to agree with each other -- `same()` prints BOTH ENDS. Forty-seven such pairs and
triples are checked, because a correction landing at one end only is this corpus's most-recorded
defect: the outcrop width at 25 m / 10 deg is stated in THREE places (prose :152, results table
:264, failure table :438) and all three are pinned to each other and to `T/tan d`.

THE PAGE'S OWN CODE IS RUN, NOT RETYPED. Where a claim is carried by a line of the page's code,
that line is LIFTED as text and evaluated (`page_eval`): the `## Use this` fence's `psi, delta`,
`dx, dy` and `s = ...` lines (section 4), the dip-corrected celerity fence and the undipped
exponent (section 8), and the failure table's two width gates (section 7). Every load-bearing
fence line is ALSO pinned as text in section 1, because a self-consistent edit at both ends of a
derivation cannot be caught by comparing the two ends -- only by pinning what they say.

WHAT IS NOT GATED, and why, is printed by `report_not_gated()` at the bottom rather than left
silent. Two of those are the shape `rigs/materials/shader-craft.py` names: a formula whose
operands are all unbound states nothing a page value can contradict.

DEFECT SHAPES THIS FILE WAS BUILT AGAINST (all four were committed elsewhere in this corpus TODAY):
  * typed-in expectation -- nothing is compared against a literal; `check()` takes a STRING off
    the page and reproduces it to the page's own decimal count.
  * one-sided assertion -- the 50 000 yr claim is asserted as a SUP that is attained
    (`max(first crossing) == the page's figure`), never as `<=`. Same for every range claim:
    min and max are both pinned to the page's two endpoints.
  * a parameter taken from the number under test -- the sampler's column is built from
    `Horizontal beds 25 m thick` at :242 and its cadence from `Δt = 2000 yr, 1000 steps` at :242.
    The `50 m` at :58 is NOT used to size the column; it is cross-checked against 2x25 afterwards.
  * a gate that cannot fail -- see `report_not_gated()`. Two identities that USED to sit here
    (section 4's sweep, built from both sides retyped; the failure table's sigma = 0 form) now
    evaluate the page's own two strings against each other instead.
  * a tolerance read off the digits of the string under test -- there is none. The three bands
    that are not exact are `BARELY` (the drift the page itself calls "barely moves", from a
    different pair of runs), `PP_AGREE` (the page's own "agreeing to within 1%", read as
    percentage points, from a different pair of runs) and float-rounding epsilons in the two
    RUN sections. Each is written beside the check that uses it.

HALTING. Every loop iterates a fixed finite sequence: the document's lines, a parsed table's
rows, a literal-length list, or `range()` of a literal or a page-parsed integer. No loop has a
condition-driven bound and none is nested inside a search. The rig terminates unconditionally.
"""
import math
import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "stratigraphy-and-lithology.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")

ok = True
SUP = {"⁻": "-", "⁰": "0", "¹": "1", "²": "2", "³": "3",
       "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
WORDS = {"one": 1, "two": 2, "twice": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
         "fifteen": 15, "twenty": 20}
SUPD = r"[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+"


def grab(pattern, what, group=1, body=None, flags=0):
    m = re.search(pattern, BODY if body is None else body, flags)
    if not m:
        sys.exit(f"the page no longer states {what} (pattern {pattern!r})")
    return m.group(group)


def grabs(pattern, what, body=None):
    m = re.search(pattern, BODY if body is None else body)
    if not m:
        sys.exit(f"the page no longer states {what} (pattern {pattern!r})")
    return m.groups()


def sci(mant, sup):
    return float(mant) * 10.0 ** int("".join(SUP[c] for c in sup))


def word(w, what):
    if w.lower() not in WORDS:
        sys.exit(f"the page writes {what} as {w!r}, which is not a number this rig knows")
    return WORDS[w.lower()]


def dp(s):
    s = s.strip()
    return len(s.split(".")[1]) if "." in s else 0


def check(label, got, printed, tol=None):
    """Reproduce a page figure AT THE PAGE'S OWN PRINTED PRECISION. `printed` is page text."""
    global ok
    want = float(printed)
    good = (abs(got - want) <= tol) if tol is not None else (round(got, dp(printed)) == want)
    ok = ok and good
    how = f"|d| <= {tol:g}" if tol is not None else f"{dp(printed)} dp"
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got:.6g}, page says {printed} ({how})")


def same(label, a, b, *rest):
    global ok
    vals = [float(a), float(b)] + [float(r) for r in rest]
    good = len(set(vals)) == 1
    ok = ok and good
    tail = "" if good else "   <- THE ENDS OF THE PAGE DISAGREE"
    print(f"{'PASS' if good else 'FAIL'}  BOTH ENDS {label}: "
          f"{', '.join(str(v) for v in vals)}{tail}")


def require(label, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {label}{(': ' + detail) if detail else ''}")


def head(t):
    print(f"\n-- {t} " + "-" * max(0, 86 - len(t)))


def page_eval(expr, env, what):
    """Evaluate an expression LIFTED OFF THE PAGE, in a namespace with no builtins.

    This is how a fence line becomes a number without being retyped here: the text evaluated is
    the page's own, so an edit to the fence changes what runs. Anything the expression needs is
    handed in explicitly; a name the page uses and this rig did not supply is a hard exit.
    """
    try:
        return eval(expr, {"__builtins__": {}}, env)   # noqa: S307 -- page text, no builtins
    except Exception as exc:                           # noqa: BLE001 -- page text, not rig code
        sys.exit(f"the page's {what} is not evaluable as written ({expr!r}): {exc}")


# =========================================================================================
head("1. the fence is still the thing this rig transcribes")
# The numbers below are parsed, but the ALGORITHM in section 3 is transcribed by hand -- the
# limit every rig in this corpus carries. So the lines the transcription claims to be a
# transcription OF are pinned. If one vanishes, this rig is measuring something the page no
# longer recommends, and that is a failure even when the numbers still reproduce.
FENCE = grab(r"## Use this\n.*?\n```\n(.*?)\n```\n", "the `## Use this` fence", 1, flags=re.S)
FENCE_FEATURES = [
    (r"^beds = \[\(thickness_0, K_0\), \(thickness_1, K_1\), \.\.\.\]\s+"
     r"# resistant and weak alternating",
     "the ALTERNATING bed list section 3 instantiates as two beds"),
    (r"^period = sum\(t for t, _ in beds\)", "period = sum of the bed thicknesses"),
    (r"^psi, delta = radians\(strike \+ 90\), radians\(dip_degrees\)",
     "the degrees->radians conversion at the boundary"),
    (r"ANGLES ARE IN RADIANS FROM HERE DOWN", "the radians imperative"),
    (r"^dx, dy = cos\(psi\), sin\(psi\)\s+# dip direction",
     "the dip-direction components (cos on x, sin on y -- section 4 evaluates this line)"),
    (r"^U_cum = zeros_like\(h\)\s+# rock lifted since t = 0, per cell",
     "the uplift accumulator's initialisation (without it there is no rock frame to subtract)"),
    (r"THE COLUMN RIDES WITH THE ROCK", "the rock-frame imperative"),
    (r"^U_cum\[y\]\[x\] \+= U\[y\]\[x\] \* dt", "the uplift accumulator"),
    (r"^s   = h\[y\]\[x\] - U_cum\[y\]\[x\] \+ tan\(delta\)\*\(dx\*x\*cellSize \+ dy\*y\*cellSize\)",
     "s built in the ROCK frame, h - U_cum"),
    (r"^u   = fmod\(s - datum, period\)", "the fmod into the column"),
    (r"^if u < 0: u \+= period", "the negative-fmod correction"),
    (r"^K   = lookup\(beds, u\)\s+# walk or prefix-sum table",
     "the lookup keyed on the WRAPPED coordinate u, not on the unwrapped s"),
]
for pat, what in FENCE_FEATURES:
    require(f"the fence still carries {what}", re.search(pat, FENCE, re.M) is not None)

# The three executable lines section 3 and section 4 depend on are also LIFTED as text, so the
# numbers below come out of the page's own arithmetic rather than out of a retyping of it.
FENCE_PSI = grab(r"^psi, delta = (.+)$", "the fence's degrees->radians line", 1, FENCE, re.M)
FENCE_DXDY = grab(r"^dx, dy = ([^#]+?)\s+#", "the fence's dip-direction line", 1, FENCE, re.M)
FENCE_S = grab(r"^s   = ([^#]+?)\s+#", "the fence's stratigraphic-height line", 1, FENCE, re.M)
FMOD_VERB = grab(r"^u   = fmod\(s - datum, period\)\s+# fmod (\w+) the sign of s, so:",
                 "the fence's claim about what fmod does with the sign", 1, FENCE, re.M)


def fence_angles(strike_deg, dip_deg):
    """psi and delta, from the fence's own line. Halts: one eval."""
    return page_eval(f"({FENCE_PSI})",
                     {"radians": math.radians, "strike": strike_deg, "dip_degrees": dip_deg},
                     "psi, delta line")


def fence_dxdy(psi):
    """dx, dy, from the fence's own line. Halts: one eval."""
    return page_eval(f"({FENCE_DXDY})",
                     {"cos": math.cos, "sin": math.sin, "psi": psi}, "dx, dy line")

# =========================================================================================
head("2. the fence's own degrees/radians imperative, evaluated")
ANG, TAN_DEG = grabs(r"tan\((\d+)\) is (-?[\d.]+) and inverts the dip", "the degrees-as-radians tangent")
ANG2, TAN_RAD = grabs(r"tan\(radians\((\d+)\)\) is (\d+\.\d+)", "the radians tangent")
same("the angle the fence instantiates", ANG, ANG2)
check(f"tan({ANG}) read as radians", math.tan(float(ANG)), TAN_DEG)
check(f"tan(radians({ANG}))", math.tan(math.radians(float(ANG))), TAN_RAD)
require("... and the degrees form 'inverts the dip' -- opposite sign",
        math.tan(float(ANG)) * math.tan(math.radians(float(ANG))) < 0,
        f"{float(TAN_DEG):+g} against {float(TAN_RAD):+g}")

# =========================================================================================
head("3. the fence TRANSCRIBED AND RUN: does `s = h` advect with the uplift?")
# --- the run's configuration, all from PROSE at :241-244, none of it from the claims at :55-63
U_ENDS = re.findall(r"U = ([\d.]+)·10(" + SUPD + ")", BODY)
require("`U` is stated in more than one place", len(U_ENDS) >= 2, f"{len(U_ENDS)} places")
same("the uplift rate U (m/yr)", *[sci(m, s) for m, s in U_ENDS])
U = sci(*U_ENDS[0])
BED_T = float(grab(r"Horizontal beds (\d+) m thick alternate", "the measured bed thickness"))
KH_M, KH_E, KS_M, KS_E, CONTRAST = grabs(
    r"`K_hard = ([\d.]+)·10(" + SUPD + r")` and `K_soft = ([\d.]+)·10(" + SUPD +
    r")` — a (\d+)× contrast", "the measured column's two erodibilities")
K_HARD, K_SOFT = sci(KH_M, KH_E), sci(KS_M, KS_E)
check("K_soft/K_hard against the page's stated contrast", K_SOFT / K_HARD, CONTRAST)
GEOM = sci("1", grab(r"uniform at the geometric mean\*\* `10(" + SUPD + r")`", "the control's K"))
check("sqrt(K_hard*K_soft) against the control's 'geometric mean'",
      math.sqrt(K_HARD * K_SOFT), f"{GEOM:g}", tol=0.0)
DT, NSTEPS, MYR = grabs(r"`Δt = (\d+) yr`, (\d+) steps \((\d+) Myr\)", "the run's cadence")
DT, NSTEPS, MYR = float(DT), int(NSTEPS), float(MYR)
check("dt x steps against the page's own '(N Myr)'", DT * NSTEPS / 1e6, f"{MYR:g}", tol=0.0)

# --- the claims, from :57-61, parsed independently of everything above
FIRST_YR = float(grab(r"across a\s*\ncontact within ([\d ]+) yr", "the first-crossing time")
                 .replace(" ", "").replace(" ", ""))
NCOL_W, PERIOD_PAGE, NCONTACT = grabs(
    r"\*\*(\w+) complete (\d+) m\s*\ncolumns — (\d+) contacts per cell\*\*",
    "the columns and contacts the broken sampler walks")
NCOL = word(NCOL_W, "the column count")
PERIOD_MOD = float(grab(r"periodic in `U·T mod (\d+) m`", "the period the comparison is modulo"))
ZERO_PCT = float(grab(r"it reads the same \*\*([\d.]+)%\*\*", "the net end-state-bed figure"))
MYR4 = float(grab(r"at \d+ Myr and at (\d+) Myr it", "the second budget the comparison returns at"))

# --- the column the fence's own line builds, from the bed prose. NOT from the `50 m` at :58.
BEDS = [(BED_T, K_HARD), (BED_T, K_SOFT)]          # "alternate", so two beds
PERIOD = sum(t for t, _ in BEDS)                   # the fence: period = sum(t for t, _ in beds)
same("the column period (2 x bed thickness, vs the page's own figure)",
     PERIOD, PERIOD_PAGE, PERIOD_MOD)
# The fence's `if u < 0` line exists only because of what the comment beside `fmod` claims. The
# claim is a WORD on the page and it is checkable: run fmod on a negative operand and look.
_FMOD_KEEPS = math.fmod(-1.0, PERIOD) < 0
require(f"the fence says fmod {FMOD_VERB} the sign of s -- and it does: "
        f"fmod(-1, {PERIOD:g}) = {math.fmod(-1.0, PERIOD):g}",
        FMOD_VERB == ("keeps" if _FMOD_KEEPS else "drops"),
        f"the page writes {FMOD_VERB!r}")
require("... so the `if u < 0: u += period` correction the fence carries is the needed one",
        _FMOD_KEEPS and 0.0 <= math.fmod(-1.0, PERIOD) + PERIOD < PERIOD)
check("the resistant share of the column, vs the page's 'what the bed thicknesses alone predict'",
      sum(t for t, k in BEDS if k == K_HARD) / PERIOD,
      grab(r"^([\d.]+)` is\s*\nwhat the bed thicknesses alone predict", "the predicted area_hard",
           1) if re.search(r"^([\d.]+)` is\s*\nwhat the bed", BODY, re.M) else
      grab(r"`area_hard` is the fraction of the map whose surface sits in a resistant bed; "
           r"([\d.]+) is\s*\nwhat the bed thicknesses alone predict", "the predicted area_hard"))


def bed_of(s, datum, period, beds):
    """The fence at :50-52, transcribed literally. Halts: the loop is `len(beds)` long."""
    u = math.fmod(s - datum, period)
    if u < 0:
        u += period
    acc = 0.0
    for i, (t, _k) in enumerate(beds):
        acc += t
        if u < acc:
            return i
    return len(beds) - 1


SWEEP = 200          # this rig's sampling density over one period -- not a page figure
OFFSETS = [j * PERIOD / SWEEP for j in range(SWEEP)]


def advect(nsteps, corrected):
    """Erosion OFF, uplift only, exactly as the page's warning specifies.

    `h += U*dt` every step, `U_cum += U*dt` beside it. The corrected sampler is the fence's
    `s = h - U_cum`; the broken one is the `s = h` the warning is about. Horizontal beds, so
    the fence's `tan(delta)*(...)` term is zero and drops out.
    Halts: SWEEP is a literal, nsteps a page-parsed integer.
    """
    crossings, first, moved = [], [], 0
    for h0 in OFFSETS:
        start = prev = bed_of(h0, 0.0, PERIOD, BEDS)
        n, ft = 0, None
        for k in range(1, nsteps + 1):
            u_cum = U * DT * k
            h = h0 + u_cum
            s = h - u_cum if corrected else h
            b = bed_of(s, 0.0, PERIOD, BEDS)
            if b != prev:
                n += 1
                if ft is None:
                    ft = k * DT
            prev = b
        crossings.append(n)
        first.append(ft)
        moved += int(prev != start)
    return crossings, first, moved


xb, fb, mb = advect(NSTEPS, corrected=False)
xc, fc, mc = advect(NSTEPS, corrected=True)
require(f"broken `s = h`: every one of {SWEEP} cells crosses a contact at all",
        all(f is not None for f in fb))
# A SUP THAT IS ATTAINED, not a bound. `max(...) <= FIRST_YR` would stay green on a page walked
# to a worse figure; the page states a measurement, so the measurement is reproduced.
check("broken `s = h`: worst first crossing over the sweep",
      max(f for f in fb if f is not None), f"{FIRST_YR:g}", tol=0.0)
require("... and no cell takes longer than that",
        max(f for f in fb if f is not None) == FIRST_YR)
check(f"broken `s = h`: contacts crossed per cell over {MYR:g} Myr (identical for all cells)",
      float(xb[0]), NCONTACT, tol=0.0)
require("... and every cell in the sweep crosses the same number",
        len(set(xb)) == 1, f"{sorted(set(xb))}")
check(f"broken `s = h`: complete {PERIOD:g} m columns walked in {MYR:g} Myr",
      U * DT * NSTEPS / PERIOD, f"{NCOL:g}", tol=0.0)
require("corrected `s = h - U_cum`: 'crosses none'",
        set(xc) == {0}, f"crossings {sorted(set(xc))}")
xb4, _, mb4 = advect(2 * NSTEPS, corrected=False)
xc4, _, mc4 = advect(2 * NSTEPS, corrected=True)
check(f"net end-state bed at {MYR:g} Myr, broken sampler: cells in a different bed",
      100.0 * mb / SWEEP, f"{ZERO_PCT:g}", tol=0.0)
check(f"net end-state bed at {MYR4:g} Myr, broken sampler: cells in a different bed",
      100.0 * mb4 / SWEEP, f"{ZERO_PCT:g}", tol=0.0)
check(f"net end-state bed at {MYR:g} / {MYR4:g} Myr, corrected sampler",
      100.0 * (mc + mc4) / (2 * SWEEP), f"{ZERO_PCT:g}", tol=0.0)
require(f"... and the page's reason: U*T mod {PERIOD:g} m is zero at both budgets",
        math.fmod(U * DT * NSTEPS, PERIOD) == 0.0 and math.fmod(U * DT * 2 * NSTEPS, PERIOD) == 0.0)
print(f"      (so the 'count the crossings' imperative bites: {xb[0]} against {xc[0]} at "
      f"{MYR:g} Myr and {xb4[0]} against {xc4[0]} at {MYR4:g} Myr, on identical {ZERO_PCT:g}%)")

# =========================================================================================
head("4. the two places the page writes s(x, y, z) agree -- BOTH SIDES EVALUATED OFF THE PAGE")
# fence :49 (grid indices x cellSize) against the standalone block :123 (world coordinates).
# NEITHER side is retyped in this file: `FENCE_S`, `FENCE_DXDY`, `FENCE_PSI` and `SBLOCK` are the
# page's own strings and `page_eval` runs them. A rotation of the dip plane at one end and not the
# other shows up as a disagreement here; a rotation at BOTH ends is caught by the text pins in
# section 1, which is the only way this comparison can be made to bite on a self-consistent edit.
SBLOCK = grab(r"^s\(x, y, z\) = ([^#\n]+?)\s+# z is the ROCK-frame height, h - U_cum",
              "the standalone dip-plane block", 1, flags=re.M)
require("the :123 block still names the ROCK frame in its own comment -- h - U_cum, not h",
        re.search(r"# z is the ROCK-frame height, h - U_cum", BODY) is not None)
worst, ndipped = 0.0, 0
for delta_d in (0.0, 2.0, 10.0, 30.0):
    for strike_d in (0.0, 37.0, 180.0):
        psi, delta = fence_angles(strike_d, delta_d)
        ddx, ddy = fence_dxdy(psi)
        for gx, gy, cs, hh, ucum in ((3, 7, 100.0, 412.0, 25.0), (0, 0, 50.0, -3.0, 0.0),
                                     (5, 2, 25.0, 88.0, 7.5)):
            fence_v = page_eval(FENCE_S,
                                {"h": {gy: {gx: hh}}, "U_cum": {gy: {gx: ucum}},
                                 "tan": math.tan, "delta": delta, "dx": ddx, "dy": ddy,
                                 "x": gx, "y": gy, "cellSize": cs}, "fence `s` line")
            block_v = page_eval(SBLOCK,
                                {"z": hh - ucum, "tan": math.tan, "delta": delta,
                                 "cos": math.cos, "sin": math.sin, "psi": psi,
                                 "x": gx * cs, "y": gy * cs}, ":123 dip-plane block")
            worst = max(worst, abs(fence_v - block_v))
            ndipped += int(abs(fence_v - (hh - ucum)) > 0)
require("the two forms agree exactly over a sweep of dip, strike and position",
        worst == 0.0, f"worst |difference| = {worst:g} m")
require("... and the sweep is not vacuous: the dip term actually moved s away from h - U_cum",
        ndipped > 0, f"{ndipped} of the sampled points carry a nonzero dip term")

# =========================================================================================
head("5. outcrop width w = T / tan(delta), at all three places the page prints it")
CELL = float(grab(r"on a \d+² grid at (\d+) m/cell", "the cell size of the measured rig"))
T1, D1, W1, C1, T2, D2, W2, C2 = grabs(
    r"(\d+) m beds at\s*\n?(\d+)° give `w = ([\d.]+) m` = \*\*([\d.]+) cells\*\* on a \d+ m "
    r"grid and (\d+) m beds at the same (\d+)° give\s*\n`w = ([\d.]+) m` = \*\*([\d.]+) cells\*\*",
    "the two worked outcrop widths")
for T, D, W, C in ((T1, D1, W1, C1), (T2, D2, W2, C2)):
    w = float(T) / math.tan(math.radians(float(D)))
    check(f"prose: {T} m beds at {D} deg, w", w, W)
    check(f"prose: {T} m beds at {D} deg, cells on a {CELL:g} m grid", w / CELL, C)

WIDTH_RULE = re.findall(r"T ≥ (\d+)·cellSize", BODY)
require("the T >= N*cellSize rule is stated in more than one place", len(WIDTH_RULE) >= 2,
        f"{len(WIDTH_RULE)} places")
same("the rule's cell-count coefficient", *WIDTH_RULE)
NCELLS_RULE = float(WIDTH_RULE[0])

# =========================================================================================
head("6. vertical span vs perpendicular thickness: the 1/cos(delta) penalty")
P2, A2, P10, A10, P30, A30, F60, A60 = grabs(
    r"at 1 m cells: ([\d.]+)% at (\d+)°, ([\d.]+)% at (\d+)°, \*\*([\d.]+)%\*\* at "
    r"(\d+)°\s*\nand \*\*([\d.]+)×\*\* at (\d+)°", "the mixing penalties")
for pct, ang in ((P2, A2), (P10, A10), (P30, A30)):
    check(f"1/cos({ang} deg) - 1, as a percentage",
          100.0 * (1.0 / math.cos(math.radians(float(ang))) - 1.0), pct)
check(f"1/cos({A60} deg), as a factor", 1.0 / math.cos(math.radians(float(A60))), F60)
require("... and the page's 'same distance written two ways' holds: T/tan d == (T*cos d)/sin d",
        all(abs(150.0 / math.tan(math.radians(d))
                - (150.0 * math.cos(math.radians(d))) / math.sin(math.radians(d))) < 1e-9
            for d in (2, 10, 30, 60)))

# =========================================================================================
head("7. the surface-slope generalisation, and the between-planes form the page rejects")
HT, HCELL, HC1, HS1, HC2, HS2, HC3, HS3, HC4, HS4 = grabs(
    r"Measured for (\d+) m beds on a (\d+) m grid: \*\*([\d.]+) cells\*\* on a (\d+)° "
    r"hillside, ([\d.]+) on (\d+)°, ([\d.]+) on\s*\n(\d+)° and \*\*([\d.]+) on "
    r"(\d+)°\*\*", "the hillside outcrop widths")
for cells, slope in ((HC1, HS1), (HC2, HS2), (HC3, HS3), (HC4, HS4)):
    check(f"horizontal beds, {HT} m, on a {slope} deg hillside, cells",
          (float(HT) / math.tan(math.radians(float(slope)))) / float(HCELL), cells)

CD, CS, CT, CCELL, CGATE, COUT, CFOUR, OPPA, OGATE, OTRUE = grabs(
    r"`δ = (\d+)°`, `σ = (\d+)°`, `T = (\d+) m` on\s*\n(\d+) m cells clears "
    r"its gate at ([\d.]+) m while the true outcrop is \*\*([\d.]+) cells\*\*, under the (\w+) "
    r"this\s*\npage asks for; opposed at ±(\d+)° it demands ([\d.]+) m where "
    r"([\d.]+) m does", "the co-dipping and opposed worked examples")
same("the 'four this page asks for' against the T >= N*cellSize rule", word(CFOUR, "the cell count"),
     NCELLS_RULE)
td, ts = math.tan(math.radians(float(CD))), math.tan(math.radians(float(CS)))
true_w = float(CT) / abs(td - ts)
check(f"co-dipping d={CD} s={CS}: true outcrop of a {CT} m bed, in {CCELL} m cells",
      true_w / float(CCELL), COUT)
require(f"... and that is under the {CFOUR} the page asks for",
        true_w / float(CCELL) < NCELLS_RULE)
between = abs(td - ts) / (1.0 + td * ts)                      # the page's rejected tan-theta form
check("co-dipping: the between-planes form's gate",
      NCELLS_RULE * float(CCELL) * between, CGATE)
require(f"... which T = {CT} m clears while the true gate "
        f"({NCELLS_RULE * float(CCELL) * abs(td - ts):.1f} m) refuses it -- the page's whole point",
        float(CT) >= float(CGATE) and float(CT) < NCELLS_RULE * float(CCELL) * abs(td - ts))
td2, ts2 = math.tan(math.radians(float(OPPA))), math.tan(math.radians(-float(OPPA)))
check(f"opposed at +/-{OPPA}: the between-planes form demands",
      NCELLS_RULE * float(CCELL) * abs(td2 - ts2) / (1.0 + td2 * ts2), OGATE)
check(f"opposed at +/-{OPPA}: the true rule demands",
      NCELLS_RULE * float(CCELL) * abs(td2 - ts2), OTRUE)
require("the page's 'off by a factor 1 + tan d * tan s', both signs, from its own four figures",
        round(float(CGATE) * (1.0 + td * ts), 1) == round(NCELLS_RULE * float(CCELL) * abs(td - ts), 1)
        and round(float(OGATE) * (1.0 + td2 * ts2), 1) == round(float(OTRUE), 1))
# The failure table states the general gate and its sigma = 0 specialisation as two expressions.
# Both are LIFTED and evaluated, so the claim "which at sigma = 0 is 4*cellSize*tan d" is tested
# against what the page actually wrote, not against a retyping of it. (Only the spelling is
# normalised: the page writes `tan δ` where python needs `tan(d)`.)
GEN_TXT, SPEC_TXT = grabs(
    r"Thicken the beds with the dip: `T ≥ (\d+·cellSize·abs\(tan δ − tan σ\))` against the surface "
    r"slope `σ`, which at `σ = 0` is `(\d+·cellSize·tan δ)`",
    "the failure table's general width gate and its sigma = 0 form")


def to_py(t):
    t = t.replace("·", "*").replace("−", "-")
    t = re.sub(r"tan\s*δ", "tan(d)", t)
    return re.sub(r"tan\s*σ", "tan(s)", t)


same("the width gate's cell-count coefficient: the rule above and the FAILURE TABLE",
     NCELLS_RULE, re.match(r"(\d+)", GEN_TXT).group(1), re.match(r"(\d+)", SPEC_TXT).group(1))
for _d in (2.0, 10.0, 30.0):
    _env = {"tan": math.tan, "abs": abs, "cellSize": CELL, "d": math.radians(_d), "s": 0.0}
    _gen = page_eval(to_py(GEN_TXT), _env, "the failure table's general width gate")
    _spec = page_eval(to_py(SPEC_TXT), dict(_env), "the failure table's sigma = 0 width gate")
    require(f"the failure table's general gate at sigma = 0 IS its tan-delta gate, at delta = {_d:g} deg",
            _gen == _spec, f"{_gen:.4f} m against {_spec:.4f} m")
require("... and the specialisation is not vacuous: the two forms differ once sigma is nonzero",
        page_eval(to_py(GEN_TXT), {"tan": math.tan, "abs": abs, "cellSize": CELL,
                                   "d": math.radians(10.0), "s": math.radians(30.0)}, "general gate")
        != page_eval(to_py(SPEC_TXT), {"tan": math.tan, "cellSize": CELL,
                                       "d": math.radians(10.0)}, "sigma = 0 gate"))

# =========================================================================================
head("8. the pole in the dip-corrected celerity -- the page's own formula, EVALUATED")
# The celerity fence is the second block this rig would otherwise transcribe. It is pinned as
# TEXT and then RUN: `celerity()` evaluates the page's string, so an edit to the exponent or to
# the denominator changes the numbers below.
CEL_LINE = grab(r"^C_H = (K_W \* A\^m \* \|dz/dx\|\^n / \( \|dz/dx\| - tan\(phi\) \))",
                "the dip-corrected celerity fence", 1, flags=re.M)
require("the celerity fence still carries its validity condition",
        re.search(r"# VALID ONLY FOR \|dz/dx\| > tan\(phi\)", BODY) is not None)
require("... and still says the form is singular at the pole and NEGATIVE below it",
        re.search(r"# singular at S = tan\(phi\) and NEGATIVE below it", BODY) is not None)
EXP_TXT, N_ONE = grabs(
    r"`C_H = K·A\^m·\|dz/dx\|\^\(([^)]+)\)`, which at `n = (\d+)` is exactly `K·A\^m`",
    "the undipped celerity and the exponent's n = 1 specialisation")
EXP_FM = grab(r"kinematic wave speed C_H = K\*A\^m\*\|dz/dx\|\^\(([^)]+)\)",
              "the frontmatter locator's copy of the same exponent")
NV = float(N_ONE)
E_BODY = float(page_eval(EXP_TXT.replace("−", "-"), {"n": NV}, "the celerity exponent"))
E_FM = float(page_eval(EXP_FM.replace("−", "-"), {"n": NV}, "the frontmatter's celerity exponent"))
same(f"the celerity exponent evaluated at n = {NV:g}: body and frontmatter locator", E_BODY, E_FM)
require(f"... and it is exactly 0 at n = {NV:g}, which is the whole of the page's "
        f"'at n = {NV:g} is exactly K*A^m'", E_BODY == 0.0, f"{EXP_TXT!r} -> {E_BODY:g}")


def celerity(S, phi_deg, n):
    """The dip-corrected celerity, from the page's own fence text. K_W and A^m are set to 1, so
    the value returned is the ratio to the undipped `K*A^m`. Halts: one eval."""
    txt = CEL_LINE.replace("^", "**").replace("|dz/dx|", "abs(S)")
    return page_eval(txt, {"K_W": 1.0, "A": 1.0, "m": 1.0, "n": n, "S": S, "abs": abs,
                           "tan": math.tan, "phi": math.radians(phi_deg)}, "the celerity fence")


PHI, TANPHI = grabs(r"At `φ = \+(\d+)°`, `tan φ = ([\d.]+)`", "the pole's location")
check(f"tan({PHI} deg)", math.tan(math.radians(float(PHI))), TANPHI)
SLOPES = re.findall(r"at `S = ([\d.]+)`, `([\d.]+)` and `([\d.]+)`, and blows up", BODY)
require("the page still names the slopes at which the celerity goes negative", bool(SLOPES))
_ss = [float(s) for s in SLOPES[0]]
require("the slopes it names are printed as a ladder -- monotone in one direction",
        _ss == sorted(_ss) or _ss == sorted(_ss, reverse=True), f"{SLOPES[0]}")
for s in SLOPES[0]:
    c_h = celerity(float(s), float(PHI), NV)
    und = abs(float(s)) ** E_BODY          # the undipped C_H at K_W = A^m = 1, same exponent
    require(f"C_H < 0 at S = {s} for phi = +{PHI} deg", c_h < 0, f"C_H/K*A^m = {c_h:.4g}")
    # NOT one-sided: the same sentence names TWO behaviours -- "returns a negative celerity" at
    # these three slopes and "blows up near 0.268". A slope whose |C_H| exceeds the undipped
    # K*A^m is in the blow-up regime, so it is not one of the three the sentence is listing.
    require(f"... and at S = {s} it is the NEGATIVE branch, not the BLOW-UP the same sentence "
            f"puts at tan phi = {TANPHI}: |C_H| does not exceed the undipped K*A^m",
            abs(c_h) <= und, f"|C_H| = {abs(c_h):.4g} against undipped {und:g}")
_near = celerity(float(TANPHI) * (1.0 - 1e-4), float(PHI), NV)
require(f"... and just below S = {TANPHI} it really does blow up, which is what makes that a "
        f"different claim from the three above",
        abs(_near) > float(TANPHI) ** E_BODY, f"|C_H| = {abs(_near):.4g}")
require(f"... and C_H > 0 just above S = {TANPHI}",
        celerity(float(TANPHI) + 1e-6, float(PHI), NV) > 0)
T1_ENDS = re.findall(r"(?:Table 1 (?:tests|works dips from)|the dips tested,) "
                     r"[−-]?(\d+)°? to \*{0,2}\+(\d+)", BODY)
T1_FM = re.search(r"Table 1 for the dips tested, -(\d+) to \+(\d+) degrees", BODY)
require("[mitchell2021] Table 1's range is stated in more than one place",
        len(T1_ENDS) + (1 if T1_FM else 0) >= 2)
lows = [e[0] for e in T1_ENDS] + ([T1_FM.group(1)] if T1_FM else [])
highs = [e[1] for e in T1_ENDS] + ([T1_FM.group(2)] if T1_FM else [])
same("Table 1's lower dip", *lows)
same("Table 1's upper dip", *highs)
require(f"the pole at phi = +{PHI} sits at the top of Table 1's tested range, as the page claims",
        float(PHI) == float(highs[0]))

# =========================================================================================
head("9. the results table: internal arithmetic, orderings and prose/table agreement")


def table_rows(header_pat, what):
    """Halts: iterates the document's own lines and breaks at the first non-table line."""
    m = re.search(header_pat, BODY)
    if not m:
        sys.exit(f"the page no longer has {what} (pattern {header_pat!r})")
    rows = []
    for line in BODY[m.start():].split("\n"):
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows[1:]


def cell(c):
    return c.replace("*", "").replace("`", "").replace("×", "").strip()


RUNS = table_rows(r"\| Run \| Outcrop width on a \*flat\* surface", "the results table")
require("the results table parsed", len(RUNS) >= 9, f"{len(RUNS)} rows")
parsed = []
for r in RUNS:
    lab = r[0]
    tm = re.search(r"(\d+) m (?:beds|bands)", lab)
    cm = re.search(r"(\d+)×", lab)
    dm = re.search(r"Dip (\d+)°", lab)
    wm = re.search(r"([\d.]+) m — \*{0,2}([\d.]+) cells", r[1])
    parsed.append({"label": lab, "control": "control" in lab,
                   "T": float(tm.group(1)) if tm else None,
                   "contrast": float(cm.group(1)) if cm else None,
                   "dip": float(dm.group(1)) if dm else (None if "control" in lab else 0.0),
                   "w": (wm.group(1), wm.group(2)) if wm else None,
                   "S_area": cell(r[2]), "conc": cell(r[3]), "area_hard": cell(r[4])})
LAY = [p for p in parsed if not p["control"]]
CTL = [p for p in parsed if p["control"]]
require("the table has controls and layered runs", len(CTL) == 2 and len(LAY) == 7,
        f"{len(CTL)} controls, {len(LAY)} layered")

for p in parsed:
    if p["w"]:
        w = p["T"] / math.tan(math.radians(p["dip"]))
        check(f"table row {p['label'][:34]!r}: w", w, p["w"][0])
        check(f"table row {p['label'][:34]!r}: cells", w / CELL, p["w"][1])
# the SAME two widths the prose states -- asserted at both ends and against each other
same("25 m beds at 10 deg, cells: prose and table",
     C1, [p["w"][1] for p in parsed if p["w"] and p["T"] == float(T1) and p["dip"] == float(D1)][0])
same("100 m beds at 10 deg, cells: prose and table",
     C2, [p["w"][1] for p in parsed if p["w"] and p["T"] == float(T2) and p["dip"] == float(D2)][0])
FT_T, FT_DIP, FT_CELLS, FT_GRID = grabs(
    r"Outcrop width below the grid — (\d+) m beds at (\d+)° are ([\d.]+) cells on a "
    r"(\d+) m grid", "the failure table's restatement of the aliasing width")
same("25 m beds at 10 deg, cells: prose, results table and FAILURE TABLE", C1, FT_CELLS,
     [p["w"][1] for p in parsed if p["w"] and p["T"] == float(FT_T)
      and p["dip"] == float(FT_DIP)][0])

SMIN, SMAX = grabs(r"`S_area` ([\d.]+)–([\d.]+) and", "the controls' S_area range")
CMIN, CMAX = grabs(r"`conc` ([\d.]+)–([\d.]+)× — no signal", "the controls' conc range")
check("controls: min S_area", min(float(p["S_area"]) for p in CTL), SMIN)
check("controls: max S_area", max(float(p["S_area"]) for p in CTL), SMAX)
check("controls: min conc", min(float(p["conc"]) for p in CTL), CMIN)
check("controls: max conc", max(float(p["conc"]) for p in CTL), CMAX)
LMIN, LMAX = grabs(r"beats\s*\nboth controls on `S_area`\*\*, by ([\d.]+)× to ([\d.]+)×",
                   "the layered S_area span")
check("layered: min S_area", min(float(p["S_area"]) for p in LAY), LMIN)
check("layered: max S_area", max(float(p["S_area"]) for p in LAY), LMAX)
require("... and every layered run really does beat both controls on S_area",
        min(float(p["S_area"]) for p in LAY) > max(float(p["S_area"]) for p in CTL))
AMIN, AMAX = grabs(r"`area_hard` runs ([\d.]+) to ([\d.]+) across every run above",
                   "the area_hard span")
check("every run: min area_hard", min(float(p["area_hard"]) for p in parsed), AMIN, tol=0.0)
check("every run: max area_hard", max(float(p["area_hard"]) for p in parsed), AMAX, tol=0.0)
NEVER = float(grab(r"never meaningfully exceeds\s*\n([\d.]+)\*\*",
                   "the ceiling area_hard never meaningfully clears"))
PRED_AH = float(grab(r"([\d.]+) is\s*\nwhat the bed thicknesses alone predict", "the prediction"))
same("the ceiling area_hard 'never meaningfully exceeds' is the thickness prediction itself",
     NEVER, PRED_AH)
# "meaningfully" is the page's own word elsewhere on this same metric: four rebuilds spanning
# 0.008 are "agreeing to within 1%", read as percentage points (area_hard is a fraction).
PP_AGREE = float(grab(r"agreeing to within ([\d.]+)%", "the page's own agreement threshold")) / 100.0
require(f"... and no run meaningfully exceeds it: every area_hard is within {PP_AGREE:g} of "
        f"{NEVER:g}, or below it", max(float(p["area_hard"]) for p in parsed) <= NEVER + PP_AGREE,
        f"highest {max(float(p['area_hard']) for p in parsed)}")

HI4_T, HI4_D, HI4_X, DIP_CONC, HOR_CONC, PCT_UP, HOR_S, DIP_S, PCT_DN = grabs(
    r"(\d+) m beds at\s*\n(\d+)° take the highest `conc` of the (\d+)× runs — ([\d.]+)× against "
    r"([\d.]+)× for the same beds horizontal,\s*\n\+([\d.]+)% — but the same pair reverses on "
    r"`S_area`, ([\d.]+) → ([\d.]+), −([\d.]+)%", "the dip/horizontal 100 m comparison")
check("the +% the page computes from its own two conc figures",
      100.0 * (float(DIP_CONC) / float(HOR_CONC) - 1.0), PCT_UP)
check("the -% the page computes from its own two S_area figures",
      -100.0 * (float(DIP_S) / float(HOR_S) - 1.0), PCT_DN)
same("the dipped 100 m conc: prose and table",
     DIP_CONC, [p["conc"] for p in LAY if p["T"] == 100 and p["dip"] == 10][0])
same("the horizontal 100 m S_area: prose and table",
     HOR_S, [p["S_area"] for p in LAY if p["T"] == 100 and p["dip"] == 0][0])
# "the HIGHEST conc of the 4x runs" is an ARGMAX over a block of the table, so it bounds every
# interior conc cell in that block from above -- not just the two the sentence quotes.
X4 = [p for p in LAY if p["contrast"] == float(HI4_X)]
require(f"the table really has a {HI4_X}x block to take a highest conc of", len(X4) >= 3,
        f"{len(X4)} rows at {HI4_X}x")
top4 = max(X4, key=lambda p: float(p["conc"]))
require(f"the highest conc of the {HI4_X}x runs is the {HI4_T} m / {HI4_D} deg row at {DIP_CONC}x",
        top4["T"] == float(HI4_T) and top4["dip"] == float(HI4_D) and top4["conc"] == DIP_CONC,
        f"{top4['label']} at {top4['conc']}")
EXC_D = grab(r"every one but the (\d+)° run beats them decisively on\n`conc` too",
             "the one layered run the page exempts from beating the controls on conc")
_ctl_hi = max(float(p["conc"]) for p in CTL)
require(f"every layered run but the {EXC_D} deg one beats BOTH controls on conc (> {_ctl_hi:g}) -- "
        "which bounds every layered conc cell from below",
        all(float(p["conc"]) > _ctl_hi for p in LAY if p["dip"] != float(EXC_D)),
        f"{sorted(float(p['conc']) for p in LAY if p['dip'] != float(EXC_D))}")
require(f"... and the {EXC_D} deg run is the one that does not do it decisively: it holds the "
        "lowest conc of any layered run",
        min(LAY, key=lambda p: float(p["conc"]))["dip"] == float(EXC_D))

LED_C, LED_CX, LED_S, LED_SX = grabs(
    r"`conc` is led by the (\d+)× horizontal run at ([\d.]+)×, `S_area` by the\s*\n"
    r"horizontal (\d+) m run at (\d+\.\d+)", "the two leaders")
best_c = max(LAY, key=lambda p: float(p["conc"]))
best_s = max(LAY, key=lambda p: float(p["S_area"]))
require(f"conc is led by the {LED_C}x horizontal run at {LED_CX}",
        best_c["contrast"] == float(LED_C) and best_c["dip"] == 0
        and best_c["conc"] == LED_CX, best_c["label"])
require(f"S_area is led by the horizontal {LED_S} m run at {LED_SX}",
        best_s["T"] == float(LED_S) and best_s["dip"] == 0 and best_s["S_area"] == LED_SX,
        best_s["label"])
LOW_T, LOW_D, LOW_S = grabs(r"The (\d+) m beds at the same (\d+)° do take the lowest "
                            r"`S_area` of any\nlayered run \(([\d.]+)\)", "the lowest layered S_area")
worst_s = min(LAY, key=lambda p: float(p["S_area"]))
require(f"the {LOW_T} m beds at {LOW_D} deg take the lowest layered S_area ({LOW_S})",
        worst_s["T"] == float(LOW_T) and worst_s["dip"] == float(LOW_D)
        and worst_s["S_area"] == LOW_S, worst_s["label"])
WID_C, WID_D = grabs(r"the \*widest\* dipped outcrop \(([\d.]+) cells at (\d+)°\) scores the "
                     r"lowest `conc`", "the widest-dipped claim")
dipped = [p for p in LAY if p["w"]]
widest = max(dipped, key=lambda p: float(p["w"][1]))
require(f"the widest dipped outcrop is {WID_C} cells at {WID_D} deg and scores the lowest conc",
        widest["w"][1] == WID_C and widest["dip"] == float(WID_D)
        and float(widest["conc"]) == min(float(p["conc"]) for p in LAY), widest["label"])
TWICE = grab(r"the best packs \*\*more than (\w+)\*\* the share", "the best conc's multiple")
# "more than N" is only a claim at the LARGEST N the measurement supports; printing a smaller N
# states something weaker than the page measured, so the bound is asserted as attained, not as `>`.
require(f"... and the best conc is more than {TWICE}",
        float(best_c["conc"]) > word(TWICE, "the multiple"))
require(f"... and {TWICE} is the largest whole multiple it clears, so the page states the "
        "strongest form of its own claim",
        float(best_c["conc"]) <= word(TWICE, "the multiple") + 1,
        f"best conc {best_c['conc']}")

# the under-read, and the 4x/16x figures the prose quotes out of this same table
NEXP, PRED, GOT_CH, GOT_SA = grabs(
    r"so 4× in `K` at `n = (\d+)` ought to give (\d+)× in slope\. It gives \*\*([\d.]+)\*\*"
    r" on the\nchannel slope ratio", "the equilibrium prediction") + (None,)
NEXP, PRED, GOT_CH = NEXP, PRED, GOT_CH
check(f"S ~ (U/K)^(1/n) at n = {NEXP}: the slope ratio a {CONTRAST}x contrast predicts",
      float(CONTRAST) ** (1.0 / float(NEXP)), PRED, tol=0.0)
SA_PROSE = grab(r"and \*\*([\d.]+)\*\* on `S_area`, the map-wide version", "the prose S_area at 4x")
SA16_PROSE, SA4_PROSE = grabs(r"does\s*\nnot raise `S_area` at all: (\d+\.\d+), \*below\* the 4× "
                              r"run's (\d+\.\d+)", "the prose 16x/4x S_area comparison")
tab4 = [p for p in LAY if p["contrast"] == 4 and p["dip"] == 0 and p["T"] == float(BED_T)
        and "Myr" not in p["label"]][0]
tab16 = [p for p in LAY if p["contrast"] == 16][0]

# ---- the SECOND copy of that row: "the 4 Myr row says it is converged rather than transient".
# The 4 Myr run is the 2 Myr run with the budget doubled, so "converged" is a claim that its three
# numbers did not move. That is the only thing the row is on the page to say, and it is asserted
# here against the 2 Myr row -- otherwise the row is an unread duplicate that can hold anything.
CONV_MYR = grab(r"the (\d+) Myr row says it is converged rather than\ntransient",
                "the page's 'converged rather than transient' claim")
same("the row the converged claim rests on is the second budget section 3 walks", CONV_MYR, MYR4)
MYR_ROWS = [p for p in LAY if "Myr" in p["label"]]
require(f"the results table carries exactly one 'run to {MYR4:g} Myr' row", len(MYR_ROWS) == 1,
        f"{[p['label'] for p in MYR_ROWS]}")
tabl = MYR_ROWS[0]
require(f"... and it is the {BED_T:g} m / {CONTRAST}x horizontal run with the budget doubled",
        tabl["T"] == BED_T and tabl["contrast"] == float(CONTRAST) and tabl["dip"] == 0.0,
        tabl["label"])
same(f"converged: `S_area` at {MYR:g} Myr and at {MYR4:g} Myr", tab4["S_area"], tabl["S_area"])
# The two tolerances below are the page's OWN two statements of what an insignificant move in
# each metric is, taken from sentences about other runs; neither is read off the digits of the
# figure under test. `conc`: the control "barely moves (0.86x -> 0.87x)" over a fourfold change of
# timestep. `area_hard`: four rebuilds spanning 0.728-0.736 are "agreeing to within 1%", read as
# percentage points (area_hard is a fraction), the reading report_not_gated() already uses.
CTL_A, CTL_B = grabs(r"The control barely moves \(([\d.]+)× → ([\d.]+)×\)",
                     "the prose's control drift -- the page's own 'barely moves'")
BARELY = round(abs(float(CTL_B) - float(CTL_A)), 10)   # PP_AGREE: parsed above, same threshold
require(f"converged: `conc` moved no more than the drift the page itself calls 'barely moves' "
        f"({CTL_A}x -> {CTL_B}x, {BARELY:g})",
        abs(round(float(tabl["conc"]) - float(tab4["conc"]), 10)) <= BARELY,
        f"{tab4['conc']} at {MYR:g} Myr -> {tabl['conc']} at {MYR4:g} Myr")
require(f"converged: `area_hard` agrees to within the {PP_AGREE * 100:g} percentage point the page "
        f"calls agreement for this same metric",
        abs(float(tabl["area_hard"]) - float(tab4["area_hard"])) <= PP_AGREE,
        f"{tab4['area_hard']} at {MYR:g} Myr -> {tabl['area_hard']} at {MYR4:g} Myr")
check("the prose's 4x S_area against the table row it quotes", float(tab4["S_area"]), SA_PROSE)
same("the prose's two statements of the 4x S_area", SA_PROSE, SA4_PROSE)
check("the prose's 16x S_area against the table row it quotes", float(tab16["S_area"]), SA16_PROSE)
AH16 = grab(r"conspicuously \*less\* \(([\d.]+) at 16×\)", "the prose's 16x area_hard")
same("the 16x area_hard: prose and table", AH16, tab16["area_hard"])
SC4L, SC4H, SC16L, SC16H, IN4, IN16 = grabs(
    r"agree on nothing: ([\d.]+) to\s*\n?([\d.]+) at 4× and ([\d.]+) to ([\d.]+) at 16×, with "
    r"the table's own ([\d.]+) and ([\d.]+) sitting inside that\nscatter", "the old-frame scatter")
same("the table's own 4x area_hard, as the prose quotes it", IN4, tab4["area_hard"])
same("the table's own 16x area_hard, as the prose quotes it", IN16, tab16["area_hard"])
require("... and both really do sit inside the scatter the page reports",
        float(SC4L) <= float(IN4) <= float(SC4H) and float(SC16L) <= float(IN16) <= float(SC16H))
# A containment alone is one-sided: every endpoint can walk outward and stay green. Both bands
# carry two further claims of the page's own, and each one binds an endpoint from the other side.
require("every area_hard figure on the page is a FRACTION of the map, so in [0, 1]",
        all(0.0 <= float(v) <= 1.0 for v in (SC4L, SC4H, SC16L, SC16H, IN4, IN16)),
        f"4x {SC4L}-{SC4H}, 16x {SC16L}-{SC16H}")
require("the old frame's own scatter FALLS with contrast -- the ordering the table shows "
        "('conspicuously less at 16x') and the corrected frame reverses: the 4x band sits "
        "entirely above the 16x band",
        float(SC4L) > float(SC16H), f"4x {SC4L}-{SC4H} against 16x {SC16L}-{SC16H}")
require(f"... and the two bands 'agree on nothing': each is wider than the {PP_AGREE * 100:g} "
        "percentage point the page calls agreement for the corrected rebuilds",
        float(SC4H) - float(SC4L) > PP_AGREE and float(SC16H) - float(SC16L) > PP_AGREE,
        f"widths {float(SC4H) - float(SC4L):.3g} and {float(SC16H) - float(SC16L):.3g}")

# the knob table's own ranges, against the runs that were actually measured
TLO, THI = grabs(r"\| Bed thickness \|[^|]*\| (\d+)–(\d+) m measured below", "the thickness range")
CX1, CX2 = grabs(r"\| Erodibility contrast[^|]*\|[^|]*\| (\d+)× and (\d+)× both measured below",
                 "the contrasts measured")
DLO, DHI = grabs(r"\| Dip, strike \| See below \| (\d+)–(\d+)°", "the dip range")
Ts = sorted({p["T"] for p in parsed if p["T"]})
require(f"every measured bed thickness lies in the knob table's {TLO}-{THI} m range",
        all(float(TLO) <= t <= float(THI) for t in Ts), f"measured {Ts}")
require(f"... and the range's floor is the thinnest bed measured ({TLO} m)", min(Ts) == float(TLO))
require(f"the contrasts measured below are exactly {{{CX1}, {CX2}}}",
        {p["contrast"] for p in LAY} == {float(CX1), float(CX2)},
        f"measured {sorted({p['contrast'] for p in LAY})}")
Ds = sorted({p["dip"] for p in LAY})
require(f"every measured dip lies in the knob table's {DLO}-{DHI} deg range",
        all(float(DLO) <= d <= float(DHI) for d in Ds), f"measured {Ds}")
require(f"... and the range's floor is the shallowest dip measured ({DLO} deg)",
        min(Ds) == float(DLO))
# The ceiling is not attained by any run (the thickness ceiling is not either -- see the DRIFT
# REPORT). It is pinned instead at the other end of the page that refers to it: the 1/cos note
# calls its own bolded worst case "the top of its own stated range", and that case is at A30.
require("the 1/cos note still calls its bolded worst case 'the top of its own stated range'",
        re.search(r"wrong at the top of\s*\nits own stated range", BODY) is not None)
same("the top of the stated dip range: the knob table, and the dip the 1/cos note calls "
     "the top of that range", DHI, A30)

# =========================================================================================
head("10. the timestep table, and the coefficient the page refuses to print as a rule")
TS = table_rows(r"\| Same \d+ Myr, same column", "the timestep table")
DT_A, N_A, DT_B, N_B = grabs(r"\| `Δt = (\d+)`, (\d+) steps \| `Δt = (\d+)`, (\d+) steps \|",
                             "the two timestep columns")
require("both timestep columns really are the same total time the header claims",
        float(DT_A) * float(N_A) == float(DT_B) * float(N_B) == MYR * 1e6,
        f"{float(DT_A)*float(N_A):g} and {float(DT_B)*float(N_B):g} yr")
same("the coarse step: results-table cadence and timestep-table column", DT, DT_A)
tsmap = {r[0]: [cell(c) for c in r[1:]] for r in TS}
conc_l = [v for k, v in tsmap.items() if "conc" in k and "layered" in k][0]
conc_u = [v for k, v in tsmap.items() if "conc" in k and "control" in k][0]
slope_r = [v for k, v in tsmap.items() if "Channel slope ratio" in k][0]
same("the layered conc at the coarse step: timestep table and results table",
     conc_l[0], tab4["conc"])
same("the control conc at the coarse step: timestep table and results table",
     conc_u[0], [p["conc"] for p in CTL if p["T"] == float(BED_T)][0])
same("the channel slope ratio at the coarse step: timestep table and prose", slope_r[0], GOT_CH)
FINE_PROSE = grab(r"drops it to ([\d.]+) at `Δt = \d+`", "the prose's fine-step slope ratio")
same("the channel slope ratio at the fine step: timestep table and prose", slope_r[1], FINE_PROSE)
FT_LO, FT_HI = grabs(r"a 4× `K` contrast measured ([\d.]+)–([\d.]+)× in slope",
                     "the failure table's slope-ratio range")
same("the slope ratio's two ends: timestep table, prose and FAILURE TABLE",
     slope_r[1], FINE_PROSE, FT_LO)
same("the slope ratio's other end: timestep table, prose and FAILURE TABLE",
     slope_r[0], GOT_CH, FT_HI)
same("the control conc at both steps: table and prose", conc_u[0], CTL_A)   # CTL_A/B: section 9
same("the control conc at the fine step: table and prose", conc_u[1], CTL_B)
CLEARS = grab(r"— ([\d.]+)\u00d7 still\s*\nclears the control",
              "the layered conc that survives the finer step")
same("the layered conc at the fine step: table and prose", conc_l[1],
     CLEARS if CLEARS else conc_l[1])
require("... and it really does clear the control at the fine step",
        float(conc_l[1]) > float(conc_u[1]))
RMS, RELIEF, RMSPCT = grabs(r"\| ([\d.]+) m on (\d+) m of relief — \*\*([\d.]+)%\*\*",
                            "the RMS difference between the two heightfields")
check("RMS / relief, from the page's own two figures", 100.0 * float(RMS) / float(RELIEF), RMSPCT)

COEF, RLO_M, RLO_E, RHI_M, RHI_E = grabs(
    r"gave `Δt ≤ ([\d.]+)·min\(bed thickness\)/max\(K·A\^m·S\^n\)`",
    "the old timestep coefficient") + grabs(
    r"between `([\d.]+)·10(" + SUPD + r")` and `([\d.]+)·10(" + SUPD + r") m/yr`",
    "the measured incision-rate range")
R_LO, R_HI = sci(RLO_M, RLO_E), sci(RHI_M, RHI_E)
DT_NEED = float(grab(r"the measured need for `Δt ≤ (\d+)`", "the step the rebuilds needed"))
C_LO, C_HI = grabs(r"takes a coefficient of `([\d.]+)`–`([\d.]+)`", "the reproducing coefficients")
check(f"coefficient that puts dt_max at {DT_NEED:g} yr for the SLOWEST rate",
      DT_NEED * R_LO / BED_T, C_LO)
check(f"coefficient that puts dt_max at {DT_NEED:g} yr for the FASTEST rate",
      DT_NEED * R_HI / BED_T, C_HI)
B_LO, B_HI, B_COEF = grabs(r"\*\*([\d.]+)× to (\d+)×\*\* below `([\d.]+)`",
                           "how far below the old rule")
check(f"{COEF}/{C_HI}", float(COEF) / float(C_HI), B_LO)
check(f"{COEF}/{C_LO}", float(COEF) / float(C_LO), B_HI)
SPREAD = grab(r"that whole ([\d.]+)×\nrange", "the rate spread the page names")
# The failure table states the SAME four figures a third time -- the coefficient, both ends of
# how far below it sits, and the rate spread. All four are captured and cross-pinned; a
# correction landing in the prose and not in the table (or the other way) fails here.
FT_COEF, FT_BLO, FT_BHI, FT_SPREAD = grabs(
    r"The old `([\d.]+)` coefficient is ([\d.]+)–(\d+)× too permissive, and the rate it divides "
    r"by moves ([\d.]+)× between rebuilds of the same rig", "the failure table's restatement")
same("the old rule's coefficient: the rule, the prose and the FAILURE TABLE", COEF, B_COEF, FT_COEF)
same(f"how far below {COEF}: prose and FAILURE TABLE, low end", B_LO, FT_BLO)
same(f"how far below {COEF}: prose and FAILURE TABLE, high end", B_HI, FT_BHI)
same("the rate spread between rebuilds: prose and FAILURE TABLE", SPREAD, FT_SPREAD)

# =========================================================================================
head("11. the butte: talus angle against bed-selective weathering")
# ---- the butte's own configuration, which the rest of this section then has to be consistent with
ESC, BBED, ANG_HARD, ANG_WEAK, BCELL = grabs(
    r"On a synthetic butte — a (\d+) m escarpment, (\d+) m beds, resistant standing at (\d+)° and "
    r"weak\nat (\d+)°, (\d+) m cells", "the butte's geometry")
FACE_ANG = grab(r"once the face is at\n(\d+)° the pass converges and stops",
                "the angle the page says the face converges at")
same("the angle the face converges at IS the resistant bed's talus angle", FACE_ANG, ANG_HARD)
require(f"the resistant bed stands steeper than the weak one ({ANG_HARD} deg against {ANG_WEAK} "
        "deg) -- without that ordering the weak bed sets the face and there is no caprock",
        float(ANG_HARD) > float(ANG_WEAK))
require(f"the butte's {BBED} m beds lie in the knob table's {TLO}-{THI} m range",
        float(TLO) <= float(BBED) <= float(THI))
require(f"the {ESC} m escarpment is at least one full column period ({2 * float(BBED):g} m) tall, "
        "so the face carries a resistant cap AND the weak beds under it that the bed-selective "
        "pass removes",
        float(ESC) >= 2.0 * float(BBED), f"{ESC} m of face over {BBED} m beds")
BUT = table_rows(r"\| Pass \| Scarp radius \| Tread std \| Tread mean \| Verdict \|",
                 "the butte table")
bmap = {r[0]: [cell(c) for c in r[1:]] for r in BUT}
talus = [v for k, v in bmap.items() if "Talus limit alone" in k][0]
unif = [v for k, v in bmap.items() if "uniform" in k][0]
sel = [v for k, v in bmap.items() if "bed-selective" in k][0]
TB0, TB1 = re.search(r"([\d.]+) → ([\d.]+) km", talus[0]).groups()
PW, PB = grabs(r"moved the escarpment \*\*from ([\d.]+) km to ([\d.]+) km\*\*\.\s*\n(\w+) metres",
               "the prose's talus-limit retreat")[:2]
METRES = grab(r"km to [\d.]+ km\*\*\.\s*\n(\w+) metres, on a (\w+)-kilometre butte", "the retreat")
same("the butte's start radius: prose and table", PW, TB0)
same("the butte's talus-limit end radius: prose and table", PB, TB1)
check("the retreat the talus limit alone achieves, in metres",
      (float(TB0) - float(TB1)) * 1000.0, f"{word(METRES, 'the retreat'):g}")
SB0, SB1 = re.search(r"([\d.]+) → \*{0,2}([\d.]+)\*{0,2} km", sel[0]).groups()
same("the butte's start radius, talus row and bed-selective row", TB0, SB0)
CLIFF = float(grab(r"while the cliff comes in by (\d+) m", "the bed-selective retreat"))
FT_CLIFF = float(grab(r"bed-selective removal retreats it by (\d+) m", "the failure table's retreat"))
same("the bed-selective retreat: prose and FAILURE TABLE", CLIFF, FT_CLIFF)
check("the bed-selective retreat, from the table's own two radii (page rounds to 2 s.f.)",
      round((float(SB0) - float(SB1)) * 1000.0, -1), f"{CLIFF:g}", tol=0.0)
require("'bit-for-bit as flat as it started': the bed-selective tread equals the talus row exactly",
        sel[1] == talus[1] and sel[2] == talus[2], f"std {sel[1]} vs {talus[1]}, "
        f"mean {sel[2]} vs {talus[2]}")
US0, US1 = re.search(r"([\d.]+) \u2192 ([\d.]+)", unif[1]).groups()
UM0, UM1 = re.search(r"([\d.]+) \u2192 ([\d.]+)", unif[2]).groups()
same("uniform weathering starts from the talus row's tread std",
     US0, re.search(r"[\d.]+", talus[1]).group(0))
same("uniform weathering starts from the talus row's tread mean",
     UM0, re.search(r"[\d.]+", talus[2]).group(0))
FT_M0, FT_M1 = grabs(r"tread mean fell (\d+) → (\d+) m", "the failure table's tread means")
require("the failure table's tread means are the butte table's, to the page's own rounding",
        round(float(UM0)) == float(FT_M0) and round(float(UM1)) == float(FT_M1),
        f"{UM0}->{FT_M0}, {UM1}->{FT_M1}")
require(f"uniform weathering destroys the mesa but cannot cut below the ground it stands on: the "
        f"tread fell to {UM1} m, and the butte's base is {float(UM0):g} - {ESC} = "
        f"{float(UM0) - float(ESC):g} m",
        float(UM1) >= float(UM0) - float(ESC),
        f"tread {UM0} -> {UM1} m against a {ESC} m escarpment")
AH_A, AH_B = grabs(r"parallel retreat it \*fell\*, ([\d.]+)% → ([\d.]+)%", "the mesa-run area_hard")
FT_A, FT_B = grabs(r"it fell ([\d.]+)% → ([\d.]+)% in the run", "the failure table's area_hard")
same("area_hard before parallel retreat: prose and FAILURE TABLE", AH_A, FT_A)
same("area_hard after parallel retreat: prose and FAILURE TABLE", AH_B, FT_B)
AH_START, AH_TALUS, SA_C1, SA_C2, SA_C3 = grabs(
    r"`area_hard` went ([\d.]+)% → ([\d.]+)%, against single-angle\ncontrols at ([\d.]+)%, "
    r"([\d.]+)% and ([\d.]+)% — the per-bed angles are \*\*indistinguishable from one angle\*\*",
    "the per-bed talus run's area_hard and its three single-angle controls")
same("the butte's starting area_hard, both sections", AH_START, AH_A)
require("... and the page's point holds: it FELL while the landform appeared",
        float(AH_B) < float(AH_A))
# The talus-angle paragraph's four percentages carry the claim "indistinguishable from one angle",
# and it is arithmetic over page figures: the per-bed run and all three single-angle controls have
# to agree, to the same 1 percentage point the page calls agreement for area_hard elsewhere.
_four = [float(AH_TALUS), float(SA_C1), float(SA_C2), float(SA_C3)]
require(f"'indistinguishable from one angle': the per-bed run ({AH_TALUS}%) and its three "
        f"single-angle controls agree to within the {PP_AGREE * 100:g} percentage point the page "
        f"calls agreement for area_hard (spread {max(_four) - min(_four):.2f} pp)",
        max(_four) - min(_four) <= PP_AGREE * 100.0, f"{_four}")
require("... and 'Nothing happens': the talus pass moves area_hard far less than the "
        "bed-selective retreat that follows it does",
        abs(float(AH_START) - float(AH_TALUS)) < abs(float(AH_A) - float(AH_B)),
        f"{abs(float(AH_START) - float(AH_TALUS)):.2f} pp against "
        f"{abs(float(AH_A) - float(AH_B)):.2f} pp")

# =========================================================================================
head("12. the explicit stack's memory figure")
SIDE, LAYERS_W, ATTRS_W, BYTES, GB = grabs(
    r"At (\d+)²\nwith (\w+) layers of (\w+) (\d+)-byte attributes that is about ([\d.]+) GB",
    "the explicit stack's memory figure")
check(f"{SIDE}^2 x {LAYERS_W} x {ATTRS_W} x {BYTES} bytes, in GB",
      float(SIDE) ** 2 * word(LAYERS_W, "the layer cap") * word(ATTRS_W, "the attribute count")
      * float(BYTES) / 1e9, GB)
CAP_FM = grab(r"a per-column properties array capped at MAX_LEVEL = (\d+)", "the frontmatter's cap")
CAP_BODY = grab(r"implementation caps `MAX_LEVEL` at (\w+)", "the body's cap")
same("[benes2001]'s MAX_LEVEL: frontmatter, body and the memory figure",
     CAP_FM, word(CAP_BODY, "the cap"), word(LAYERS_W, "the layer cap"))

# =========================================================================================
head("13. the convex-combination bracket, RUN at the page's own 1000x contrast")
UPD = grab(r"^h\[i\] = \(h\[i\] \+ U\[i\]\*Δt \+ f \* h\[r\]\) / \(1 \+ f\)$",
           "the implicit update the stability argument is about", 0, flags=re.M)
W1, W2 = grabs(r"— weights\n`([^`]+)` and `([^`]+)`, summing to one", "the convex weights")
try:
    sums = [eval(W1, {"__builtins__": {}}, {"f": v}) + eval(W2, {"__builtins__": {}}, {"f": v})
            for v in (0.0, 0.5, 1.0, 7.0, 1e6)]
except Exception as exc:                       # noqa: BLE001 -- page text, not this rig's code
    sums, ok = [None], False
    print(f"FAIL  the page's weights `{W1}` and `{W2}` are not evaluable: {exc}")
require(f"the page's own weights `{W1}` and `{W2}` sum to one at every f >= 0",
        sums != [None] and all(s == 1.0 for s in sums), f"{sums}")
BIGC, BIGDT = grabs(r"with a \*\*(\d+)× contrast\*\* at `Δt = ([\d ]+) yr` and no "
                    r"diffusion stays finite and bounded", "the extreme-contrast run")
BIGC, BIGDT = float(BIGC), float(BIGDT.replace(" ", "").replace(" ", ""))
M_EXP = float(grab(r"looked right at `m = ([\d.]+)` is wrong", "the exponent m"))
N_CHAIN, N_STEP = 64, 200                       # this rig's grid and step count -- literals
h = [200.0 - 2.0 * i for i in range(N_CHAIN)]   # a monotone chain: cell i drains to cell i+1
worst_out, nonfinite = 0.0, 0
for step in range(N_STEP):
    nh = list(h)
    for i in range(N_CHAIN - 1):
        K = K_HARD * (BIGC if bed_of(h[i], 0.0, PERIOD, BEDS) else 1.0)
        f = K * BIGDT * (i + 1.0) ** M_EXP / CELL
        a = h[i] + U * BIGDT
        b = h[i + 1]
        nh[i] = (a + f * b) / (1.0 + f)         # the page's line, transcribed
        if not math.isfinite(nh[i]):
            nonfinite += 1
        else:
            worst_out = max(worst_out, min(a, b) - nh[i], nh[i] - max(a, b))
    h = nh
require(f"at a {BIGC:g}x contrast and dt = {BIGDT:g} yr the update stays finite", nonfinite == 0)
require("... and every cell stays inside the bracket [min(h+U*dt, h_r), max(...)] -- "
        "the page's 'no value of K can push a cell outside'",
        worst_out <= 4 * sys.float_info.epsilon * 1e3,
        f"worst excursion {worst_out:.3g} m over {N_CHAIN * N_STEP} updates (float rounding only)")


# =========================================================================================
head("14. the diffusion sub-cycle constant the measured runs were made at, RUN")
# `c = 0.225` is run configuration, and the page's own bracket argument (section 13) decides it:
# an update that is a CONVEX COMBINATION of the values it reads cannot leave their range. The
# explicit five-point diffusion sub-step `h += c*(sum of four neighbours - 4h)` has centre weight
# `1 - 4c`, so it is that same convex combination exactly while 4c <= 1, and is the unbounded
# explicit form the page contrasts with once it is not. So: run it at the page's own c.
CSUB = float(grab(r"sub-cycled at `c = ([\d.]+)`", "the diffusion sub-cycle constant"))
GRID, DSTEPS = 24, 120                          # this rig's grid and step count -- literals
F0 = [[100.0 * math.sin(i * 1.7) * math.cos(j * 2.3) for j in range(GRID)] for i in range(GRID)]


def diffuse(field, c):
    """Explicit 5-point diffusion, `DSTEPS` sub-steps. Halts: both loops are literals."""
    worst, bad = 0.0, 0
    for _ in range(DSTEPS):
        nf = [row[:] for row in field]
        for i in range(1, GRID - 1):
            for j in range(1, GRID - 1):
                sten = (field[i][j], field[i - 1][j], field[i + 1][j],
                        field[i][j - 1], field[i][j + 1])
                nf[i][j] = field[i][j] + c * (sum(sten[1:]) - 4.0 * field[i][j])
                if not math.isfinite(nf[i][j]):
                    bad += 1
                else:
                    worst = max(worst, min(sten) - nf[i][j], nf[i][j] - max(sten))
        field = nf
    return worst, bad, min(map(min, field)), max(map(max, field))


_w, _bad, _lo, _hi = diffuse(F0, CSUB)
_lo0, _hi0 = min(map(min, F0)), max(map(max, F0))
require(f"at the page's own c = {CSUB:g} every diffusion sub-step stays inside its five-point "
        "stencil -- the same bracket argument section 13 makes for the implicit update",
        _bad == 0 and _w <= 8 * sys.float_info.epsilon * 100.0,
        f"worst excursion {_w:.3g} m over {DSTEPS * (GRID - 2) ** 2} updates (float rounding only)")
require(f"... and the field's range never grows: {_lo:.4g}..{_hi:.4g} inside the initial "
        f"{_lo0:.4g}..{_hi0:.4g}", _lo >= _lo0 and _hi <= _hi0)
require(f"... and the gate bites rather than being decoration: 4c = {4 * CSUB:g} <= 1 is what "
        "makes that centre weight non-negative", 4.0 * CSUB <= 1.0)


# =========================================================================================
def report_not_gated():
    print()
    print("  NOT GATED, and why. Each is named rather than left silent:")
    print("   1. `w = T/tan d` == `(T*cos d)/sin d`  -- an ALGEBRAIC TAUTOLOGY. T and d are")
    print("      unbound, so no edit to the page can make the two sides differ. Section 6 gates")
    print("      the 1/cos penalties instead, whose operands ARE page figures.")
    print("   2. `C_H = K*A^m*|dz/dx|^(n-1)`: K and A^m are unbound, so the PRODUCT states")
    print("      nothing a page value can contradict. The EXPONENT is bound and IS gated -- the")
    print("      page's own string is evaluated at its own n = 1 and must come out 0 (section 8),")
    print("      and the dip-corrected fence is evaluated, not transcribed, for the pole.")
    print("   3. The corrected-frame rebuild figures (S_area 1.11-1.13 / 1.25-1.66, area_hard")
    print("      0.728-0.736 / 0.860-0.869) -- reproducing them needs a 128^2 stream-power +")
    print("      diffusion solver this rig would have to INVENT, and its failures would indict")
    print("      the rig rather than the page. What IS checked below is every consequence the")
    print("      page derives from them, which is pure comparison of page figures.")
    print("   4. 'Take material layers unless something downstream reads the history', 'author")
    print("      more contrast than you want to see' -- imperatives with no measurable and no")
    print("      binding table to mechanise.")
    print("   5. `D = 0.02 m²/yr` and the butte's `50 m cells`. Both are run configuration that")
    print("      the page derives NOTHING from: no printed figure changes if either moves, and")
    print("      the only quantities they could reach (relief, S_area, conc, the scarp radius)")
    print("      are the 128² measurements item 3 explains this rig will not invent. `c = 0.225`")
    print("      IS gated (section 14) because the page's own bracket argument decides it, and")
    print("      the butte's 400 m escarpment IS gated (section 11) against the tread it has to")
    print("      stand above and against the column period it has to contain.")
    print("   6. INTERIOR CELLS of the results table. Pinned: every min, max, argmax and argmin;")
    print("      every cell the prose or the failure table quotes; both widths; the whole 4 Myr")
    print("      row against the 2 Myr row; every 4x `conc` against that block's own argmax; and")
    print("      every layered `conc` BUT THE 2° ROW'S from below, against the controls. NOT")
    print("      pinned, because the page states nothing about them, and each is named here so")
    print("      the omission is visible rather than silent:")
    print("        `area_hard` 0.499 and 0.464 (the two controls), 0.308, 0.476 and 0.378")
    print("        `S_area` 1.408 (the 2° row), and `conc` 0.92 (the 2° row) from below")
    print("      All of them stay inside spans that ARE gated at both ends (area_hard")
    print("      0.287-0.502; layered S_area 1.3-2.1). Closing them would take a relation the")
    print("      page does not state -- the controls' own `area_hard` is 0.499 against 0.464 on")
    print("      the same domain, so not even 'a uniform-K control scores the thickness")
    print("      prediction' survives contact with the page's own two rows.")
    print("   7. The old-frame scatter's OUTER endpoints (0.55 at 4x, 0.16 at 16x). Gated: both")
    print("      containments, the falling-with-contrast ordering (which pins 0.32 from below),")
    print("      both band widths against the page's own 1-percentage-point 'agreement', and")
    print("      that every figure is a fraction in [0, 1]. A walk OUTWARD from 0.55 or 0.16")
    print("      survives all four, and the page prints nothing else about those two ends.")
    print("      (The 16x band's top, 0.30, is numerically the table's own 0.300. Read as a")
    print("      rounding coincidence and NOT asserted as an equality: the four rebuilds are")
    print("      different runs from the table's.)")
    # consequences of (3), which ARE checkable
    r4l, r4h, r16l, r16h = grabs(r"`S_area` runs\n\*\*([\d.]+)–([\d.]+)\*\* at 4× against "
                                 r"\*\*([\d.]+)–([\d.]+)\*\* at 16×", "the corrected S_area bands")
    a4, a16 = grabs(r"put `area_hard` at \*\*([\d.]+)\*\* at\n4× and \*\*([\d.]+)\*\* at 16",
                    "the corrected area_hard figures")
    b4l, b4h, b16l, b16h = grabs(r"([\d.]+)–([\d.]+) and ([\d.]+)–([\d.]+) across all four",
                                 "the corrected area_hard bands")
    global ok
    for lbl, cond in (
        ("corrected S_area 'rises with contrast' (4x band entirely below the 16x band)",
         float(r4h) < float(r16l)),
        ("corrected area_hard rises with contrast too (4x band entirely below the 16x band), "
         "the reversal of the old frame's own ordering that section 9 gates",
         float(b4h) < float(b16l)),
        ("... and the old frame really does order them the other way (table 4x > table 16x)",
         float(tab4["S_area"]) > float(tab16["S_area"])),
        ("'they deepen it': the corrected 4x band sits below the table's own 4x S_area",
         float(r4h) < float(tab4["S_area"])),
        ("the corrected area_hard figures are the midpoints of their own bands, to 2 dp",
         round((float(b4l) + float(b4h)) / 2, 2) == float(a4)
         and round((float(b16l) + float(b16h)) / 2, 2) == float(a16)),
        ("'agreeing to within 1%' holds read as PERCENTAGE POINTS",
         (float(b4h) - float(b4l)) * 100 <= 1.0 and (float(b16h) - float(b16l)) * 100 <= 1.0),
    ):
        ok = ok and cond
        print(f"   {'PASS' if cond else 'FAIL'}  {lbl}")
    rel = max(100 * (float(b4h) / float(b4l) - 1), 100 * (float(b16h) / float(b16l) - 1))
    print(f"      (note: read as a RELATIVE spread the same sentence gives {rel:.1f}%, above the")
    print("       1% it claims. Reported, not gated -- the percentage-point reading is available")
    print("       and area_hard is a fraction, so the sentence is true on the natural reading.)")
    # a drift report, in the shape mask-to-material.py uses for its cost figures
    print()
    print("  DRIFT REPORT -- the page's own dt_max band does not follow from its own rate band:")
    lo, hi = float(COEF) * BED_T / R_HI, float(COEF) * BED_T / R_LO
    pl, ph = grabs(r"`Δt_max` between \*\*(\d+) and (\d+) yr\*\*", "the old rule's dt_max band")
    print(f"    the page's rates {R_LO:g} and {R_HI:g} m/yr, through its own "
          f"`{COEF}*{BED_T:g}/rate`, give dt_max {lo:.0f} to {hi:.0f} yr")
    print(f"    the page prints {pl} to {ph} yr, and separately prints `{B_HI}x below {COEF}`, "
          f"which pins the upper end at {float(B_HI) * DT_NEED:.0f}")
    print(f"    the rate band's own ratio is {R_HI / R_LO:.2f}x; the page calls it {SPREAD}x")
    print("    -> the printed rate endpoints are 2-s.f. roundings of something near 1.02e-3 and")
    print("       2.76e-3. Reported rather than gated: gating the page's 4900 would fail a")
    print("       correct page, and gating 5000 would assert a number the page does not print.")
    print()
    print("  DRIFT REPORT -- a knob-table range labelled 'measured below' whose ceiling was not:")
    print(f"    the thickness knob reads `{TLO}–{THI} m measured below`, but the runs below measure")
    print(f"    {sorted(Ts)} m: the floor {TLO} m is attained and the ceiling {THI} m is not measured")
    print("    anywhere on this page. So the ceiling is gated ONLY as an upper bound on the runs")
    print("    (any value >= 100 passes) -- an attained-sup gate there would fail the page as it")
    print("    stands, and the defect is the word 'measured', not the number. The dip knob has the")
    print(f"    same shape ({DLO}–{DHI} deg, measured {sorted(Ds)}), but its ceiling IS pinned: the")
    print("    1/cos note calls its own bolded worst case 'the top of its own stated range'.")


report_not_gated()
print()
sys.exit(0 if ok else 1)
