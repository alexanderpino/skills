#!/usr/bin/env python3
"""shallow-water.md's `## Use this` fences, RUN and checked against their own page.

The first gate in this corpus that runs a recommendation rather than evaluating a closed form,
which is what criterion 2's phrase "the block was run" was always about. The pipe-flux fence at
:61-74 is transcribed literally -- two passes, `K*Sigma f`, the guarded `K` -- and the page's
own unconditional-stability claim is reproduced from it.

Four fences, but their claims OVERLAP and each is gated once. A completeness critic caught the
triage fleet double-booking two of them across three blocks -- `0.099 m/s` claimed by both the
:40-42 and :133-134 verdicts, and the `5x` margin by both :133-134 and :209-210 -- which would
have inflated any denominator built by counting per fence. Claims are the unit here.

⚠️ NOT GATED, deliberately: the :40-42 fence prints the shallow-water SYSTEM, not a scheme, and
:45 says this document's own scheme does not discretise the second equation. Any solver a rig
supplied would be the rig's invention and its failures would indict the rig, not the page. Only
the characteristic speed that fence states is checked.

Halting: fixed step counts over fixed grids; every loop bound is a literal or parsed integer.
"""
import math
import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "shallow-water.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")
G = 9.81
ok = True


def page(pattern, what, group=1):
    m = re.search(pattern, BODY)
    if not m:
        sys.exit(f"the page no longer states {what} (pattern {pattern!r})")
    return float(m.group(group))


def check(label, got, want, tol):
    global ok
    good = abs(got - want) <= tol
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got:.6g}, page says {want:.6g}")


# ── 1. the celerity, against BOTH places the page prints it ──────────────────────────────
DEPTH_MM = page(r"At (\d+) mm depth `sqrt\(g\*h\)` is", "the depth it instantiates")
CEL_BODY = page(r"At \d+ mm depth `sqrt\(g\*h\)` is\s*\n?\*\*([\d.]+) m/s\*\*", "the celerity")
CEL_TABLE = page(r"at \d+ mm depth[^|]*?is ([\d.]+) m/s", "the celerity in the failure table")
derived = math.sqrt(G * DEPTH_MM / 1000.0)
check(f"sqrt(g*h) at {DEPTH_MM:g} mm, body end", round(derived, 3), CEL_BODY, 0.0)
check(f"sqrt(g*h) at {DEPTH_MM:g} mm, failure-table end", round(derived, 3), CEL_TABLE, 0.0)
if CEL_BODY != CEL_TABLE:
    ok = False
    print(f"FAIL  the two ends disagree with EACH OTHER: {CEL_BODY} against {CEL_TABLE}")

# ── 2. the coefficient identity the page calls the only form worth remembering ───────────
COEFF = page(r"dt_crit = \(1/sqrt2\) \* dx / sqrt\((\d+)\*g\*A/l\)\s*=\s*([\d.]+) \* dx",
             "the dt_crit identity", 2)
INNER = page(r"dt_crit = \(1/sqrt2\) \* dx / sqrt\((\d+)\*g\*A/l\)", "the inner factor")
identity = (1.0 / math.sqrt(2)) / math.sqrt(INNER)
check(f"(1/sqrt2)/sqrt({INNER:g}) against the printed coefficient",
      round(identity, 2), COEFF, 0.0)
MEASURED = page(r"held at ([\d.]+) across `A", "the measured dt_crit ratio")
check("the identity against the measured ratio", identity, MEASURED, 0.01 * MEASURED)
LINEAR = page(r"the linear scheme returns \*\*([\d.]+)\*\*", "the linear-scheme bisection")
check("the identity against the linear-scheme bisection", identity, LINEAR, 5e-4)
ONE_D = page(r"the same\s*\n?chain returns \*\*([\d.]+)\*\*", "the 1-D bound")
check("1-D: von Neumann c*dt/dx <= 1", round(1.0 / math.sqrt(2), 4), ONE_D, 0.0)

# ── 3. the shipped Courant number and both margins ───────────────────────────────────────
C_SHIP = page(r"a shipped `C = ([\d.]+)`", "the shipped Courant number")
MARGIN = page(r"is a \*\*([\d.]+)× margin\*\*", "the margin on this scheme's limit")
NAIVE = page(r"\*not\* the ([\d.]+)× that reading", "the margin a C <= 1 reading suggests")
check(f"{COEFF:g}/C at C = {C_SHIP:g}", COEFF / C_SHIP, MARGIN, 1e-9)
check(f"1.0/C at C = {C_SHIP:g}", 1.0 / C_SHIP, NAIVE, 1e-9)

# ── 4. the block, transcribed literally, and RUN ─────────────────────────────────────────
RUN = re.search(r"a (\d+)² grid over a rough bed runs (\d+) steps at every `dt` from\s*\n?"
                r"`C = ([\d.]+)` to `C = ([\d.]+)` with no NaN, `min depth = (-?[\d.]+)`, and\s*\n?"
                r"mass drift ≤ (\d+(?:\.\d+)?e-\d+)", BODY)
if not RUN:
    sys.exit("the page no longer states the unconditional-stability run")
NGRID, NSTEPS = int(RUN.group(1)), int(RUN.group(2))
C_LO, C_HI = float(RUN.group(3)), float(RUN.group(4))
MIN_DEPTH, DRIFT = float(RUN.group(5)), float(RUN.group(6))


def run_block(n, steps, C, guarded=True, seed=20260915, dry_but_one=False):
    """The fence at :61-74, transcribed literally. Two passes; K*Sigma f, not Sigma f.

    ⚠️ The opposite pipe is `d ^ 1`, not `3 - d`. With `off` ordered -x, +x, -y, +y, `3 - d`
    pairs -x with +y and +x with -y: every cell's inflow reads a pipe aimed somewhere else,
    and mass drifts by 17% while the stability claims still pass. That was this rig's bug and
    it would have indicted the page -- exactly what the :40-42 triage warned a supplied solver
    would do. Caught because the drift assertion is separate from the NaN assertion.
    """
    s = seed
    rnd = []
    for _ in range(n * n):
        s = (1103515245 * s + 12345) % (1 << 31)
        rnd.append(s / (1 << 31))
    b = [r * 2.0 for r in rnd]
    if dry_but_one:                       # the page's own configuration for the guard test
        # FLAT bed. With the rough bed used elsewhere, dry cells still have head differences,
        # so their pipes carry flux, `Sigma f > 0`, and the 0/0 never arises -- 51 of 64 rather
        # than the page's 63. The page's sentence is "an 8x8 grid dry but for one wet cell",
        # and a dry cell only reaches 0/0 when nothing drives it.
        b = [0.0] * (n * n)
        h = [0.0] * (n * n)
        h[n * n // 2] = 0.5
    else:
        h = [0.1 + 0.05 * r for r in rnd]
    dx = l = A = 1.0
    cell_area = dx * dx
    dt = C * dx / math.sqrt(G * max(max(h), 1e-3) / l)
    f = [[0.0] * 4 for _ in range(n * n)]
    off = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    mass0 = sum(h)
    worst = 0.0
    k_nan_step0 = None
    for _ in range(steps):
        H = [b[i] + h[i] for i in range(n * n)]
        for y in range(n):
            for x in range(n):
                i = y * n + x
                tot = 0.0
                for d, (ox, oy) in enumerate(off):
                    nx, ny = x + ox, y + oy
                    hn = H[ny * n + nx] if 0 <= nx < n and 0 <= ny < n else H[i]
                    f[i][d] = max(0.0, f[i][d] + dt * (A * G / l) * (H[i] - hn))
                    tot += f[i][d]
                if guarded:
                    K = min(1.0, h[i] * cell_area / (dt * tot)) if tot > 0 else 1.0
                else:                    # [mei2007] eq. (4) as printed: 0/0 on a dry cell
                    K = min(1.0, h[i] * cell_area / (dt * tot)) if dt * tot != 0 else float("nan")
                if k_nan_step0 is None or isinstance(k_nan_step0, list):
                    if not isinstance(k_nan_step0, list):
                        k_nan_step0 = []
                    k_nan_step0.append(K != K)
                for d in range(4):
                    f[i][d] *= K
        for y in range(n):
            for x in range(n):
                i = y * n + x
                inflow = 0.0
                for d, (ox, oy) in enumerate(off):
                    nx, ny = x + ox, y + oy
                    if 0 <= nx < n and 0 <= ny < n:
                        inflow += f[ny * n + nx][d ^ 1]
                h[i] += dt * (inflow - sum(f[i])) / cell_area
                if h[i] == h[i]:
                    worst = min(worst, h[i])
    nan = sum(1 for v in h if v != v)
    k0 = sum(1 for v in (k_nan_step0 or []) if v)
    return worst, nan, abs(sum(h) - mass0) / mass0, k0


print()
for C in (C_LO, 1.0, 5.0, C_HI):
    steps = NSTEPS if C == C_LO else 60
    worst, nan, drift, _ = run_block(NGRID, steps, C)
    # ⚠️ Drift is asserted at MACHINE-EPSILON SCALE, not at the page's exact 1.1e-16. This rig
    # reproduces ~7e-16 over the same grid and step count; the difference is summation order,
    # which the page does not state and this rig cannot recover. Asserting the page's figure
    # exactly would be asserting their loop order. Both numbers are printed so the gap is
    # visible rather than absorbed into a tolerance nobody reads.
    # Assert the page's min-depth MEASUREMENT, not a one-sided bound. The first version used
    # `worst < MIN_DEPTH - 1e-9`, which passes a page claiming a WORSE bound than reality --
    # walking the page to `-0.004000` left this rig green. A measurement claim is reproduced or
    # it is not; "no worse than" is a different claim and the page does not make it.
    bad = nan or round(worst, 6) != MIN_DEPTH or drift > 1e-14
    ok = ok and not bad
    print(f"{'FAIL' if bad else 'PASS'}  fence RUN at C = {C:<5g} ({steps} steps): {nan} NaN, "
          f"min depth {worst:+.6f}, mass drift {drift:.3e}")
print(f"      (page: no NaN, min depth {MIN_DEPTH:.6f}, drift <= {DRIFT:g}, "
      f"{NGRID}² over {NSTEPS} steps, C from {C_LO:g} to {C_HI:g})")

# ── 5. the guard the page says is load-bearing, removed ──────────────────────────────────
NANC = re.search(r"`K` NaN in (\d+) of (\d+) cells at step 0", BODY)
GRID = re.search(r"Measured on an (\d+)\u00d7(\d+)\s*\n?grid dry but for one wet cell", BODY)
if not NANC or not GRID:
    sys.exit("the page no longer states the unguarded NaN count on a named grid")
want_k0, want_tot = int(NANC.group(1)), int(NANC.group(2))
side, side2 = int(GRID.group(1)), int(GRID.group(2))
# ⚠️ The grid comes from the PROSE, never from the denominator under test. The first
# version took `side = sqrt(want_tot)`, so walking the page to "63 of 100" silently resized this
# rig's grid to 10x10 and it passed -- the assertion followed the number it was meant to check.
if side * side2 != want_tot:
    ok = False
    print(f"FAIL  the page says an {side}\u00d7{side2} grid but counts out of {want_tot} cells")
_, nan_after, _, k0 = run_block(side, 1, 0.2, guarded=False, dry_but_one=True)
if k0 != want_k0:
    ok = False
    print(f"FAIL  guard removed: K is NaN in {k0} of {side * side} cells at step 0; "
          f"the page says {want_k0}")
else:
    print(f"PASS  guard removed: K is NaN in {k0} of {side * side} cells at step 0")
if nan_after == side * side:
    print(f"PASS  ... and the whole {side}\u00d7{side} depth field is NaN after one step")
else:
    ok = False
    print(f"FAIL  guard removed: {nan_after} of {side * side} NaN after one step; the page "
          f"says the whole field")


# ── 5b. what the transcription DEPENDS ON, pinned ────────────────────────────────────────
# ⚠️ THE DEEPEST LIMIT OF THIS RIG, named rather than hidden. `run_block` transcribes the
# fence's ALGORITHM by hand; only its NUMBERS are parsed. So an edit to the fence's code does
# not reach the transcription -- deleting the `(Sigma f > 0) ?` guard from the page left this
# rig green, because the rig's own copy still had it. That is the limit
# `registers/pseudocode-execution.tsv` has carried since it was created ("the pseudocode,
# transcribed literally"), and no rig in this corpus escapes it.
#
# What CAN be pinned is the text the transcription claims to be a transcription OF. Each line
# below is a load-bearing feature of the fence: if one disappears, the rig is now measuring
# something the page no longer recommends, and that is a failure even though the numbers still
# reproduce.
FENCE_FEATURES = [
    (r"K\s*=\s*\(\u03a3f > 0\) \?", "the guarded K -- the whole 0/0 warning turns on it"),
    (r"f_i \*= K", "the clamp applied to the fluxes"),
    (r"h\s*\+= dt \* \(inflow - K\*\u03a3f\) / cellArea", "K*Sigma f, the POST-clamp outflow"),
    (r"TWO passes over the grid \u2014 never one", "the two-pass structure"),
]
for pat, what in FENCE_FEATURES:
    if re.search(pat, BODY):
        print(f"PASS  the fence still carries {what}")
    else:
        ok = False
        print(f"FAIL  the fence no longer carries {what} -- this rig's transcription is now of "
              f"something the page does not recommend")

# ── 6. the min() asymmetry the whole warning turns on ────────────────────────────────────
nan = float("nan")
if min(1, nan) == 1 and min(nan, 1) != min(nan, 1):
    print("PASS  min(1, NaN) == 1 and min(NaN, 1) is NaN -- the prototype is clean and the "
          "shader is not")
else:
    ok = False
    print("FAIL  min()'s NaN asymmetry does not hold on this interpreter")

print()
sys.exit(0 if ok else 1)
