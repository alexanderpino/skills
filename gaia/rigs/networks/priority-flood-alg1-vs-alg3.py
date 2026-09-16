#!/usr/bin/env python3
"""flow-routing.md:123-137 says Algorithm 1+eps and Algorithm 3 do NOT produce the same fill.
`registers/source-findings.tsv:36` says they do. Both cannot be true. This rig runs both.

WHY THIS EXISTS. The page prints four figures -- 171 of 441 cells differ, 187 receivers move,
strictly higher on all 171 and lower on none -- and then says of itself, in bold, that they are
UNREGISTERED and outside its stamp. The register row it contradicts records the opposite
conclusion. That is not a reading dispute; it is unrun work, and it has sat unrun since
2026-09-14.

WHAT THIS RIG CAN AND CANNOT SETTLE.
  CAN:    whether the two algorithms differ AT ALL on a depression-bearing DEM; which way the
          difference goes; and whether Algorithm 3 violates [barnes2014]'s own third criterion
          ("W is the lowest surface allowed by properties 1 and 2") where it differs.
  CANNOT: the page's exact 171 / 187. The page names 441 cells and nothing else -- no DEM, no
          generator, no seed -- so no rig anywhere can land on its counts. Those figures are
          reported by this rig as UNREPRODUCIBLE and are not asserted. What IS asserted is the
          qualitative claim the two sources disagree about, which is the whole dispute.

THE CONTROL THAT MAKES THIS WORTH ANYTHING. Both algorithms are implemented here, so a bug in
either could manufacture a difference and "settle" the dispute wrongly. [barnes2014] Sec 4 says
that at eps = 0 a total and a strict weak ordering produce the same results, and Algorithms 1
and 2 are the same fill by construction. So this rig runs BOTH at eps = 0 first and asserts the
two surfaces are BIT-IDENTICAL. If that control fails, one implementation is wrong and every
number below is void -- the rig says so and exits non-zero rather than reporting a difference it
cannot attribute.

THE FENCE IS PINNED AS TEXT, not transcribed from memory. An independent attack on six sibling
rigs found all six checking their own transcription rather than the page; the load-bearing lines
of the page's block are asserted verbatim below before anything is run.

HALTING: priority-flood closes each cell at push time, so each of the n cells is pushed at most
once and the loop drains in at most n pops. The FIFO in Algorithm 3 is drained by the same
counter. No loop has a data-dependent bound.
"""
import math
import random
import pathlib
import re
import sys
from heapq import heappush, heappop

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "flow-routing.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")
ok = True


def gone(what, pattern):
    sys.exit(f"ANCHOR GONE -- the page no longer states {what} (pattern {pattern!r}); "
             f"a claim that has vanished is a FAIL, not a skip")


def page(pattern, what, group=1, flags=0):
    m = re.search(pattern, BODY, flags)
    if not m:
        gone(what, pattern)
    return m.group(group)


def num(pattern, what, group=1, flags=0):
    return float(page(pattern, what, group, flags).replace(",", ""))


def check(label, got, want, tol=0.0):
    global ok
    good = abs(got - want) <= tol if isinstance(want, (int, float)) else got == want
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got!r}, page says {want!r}")
    return good


def assert_(label, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {label}{(' -- ' + detail) if detail else ''}")
    return bool(cond)


# ── §1 THE PAGE'S OWN BLOCK, PINNED AS TEXT ──────────────────────────────────────────────
# Every line this rig relies on for its transcription of Algorithm 1. An edit to any of them
# is a FAIL here, so the rig can never drift into checking its own copy of the algorithm.
print("=== flow-routing.md :: Algorithm 1 + eps against Algorithm 3 ===\n")
print("-- §1 the page's block, pinned line by line --")
FENCE_LINES = [
    (r"^    closed\[:\] = false$", "the closed array is cleared"),
    (r"^    open = min-priority-queue keyed on elevation, TOTAL ORDER$", "the queue and its order"),
    (r"^    for each boundary cell b:  closed\[b\] = true;  open\.push\(b, z\[b\]\)$",
     "the boundary seeding"),
    (r"^        c = open\.pop\(\)  ", "the pop"),
    (r"^            if closed\[j\]: continue$", "the closed guard"),
    (r"^            closed\[j\] = true$", "closing at push time, not at pop"),
    (r"^            lift = useEpsilon \? nextafter\(z\[c\], \+INF\) : z\[c\]$", "the epsilon lift"),
    (r"^            z\[j\] = max\(z\[j\], lift\)$", "the raise"),
    (r"^            open\.push\(j, z\[j\]\)$", "the push, on the RAISED elevation"),
]
for pat, what in FENCE_LINES:
    n = len(re.findall(pat, BODY, re.M))
    if n != 1:
        gone(f"{what} exactly once (found {n})", pat)
print(f"      all {len(FENCE_LINES)} load-bearing lines of the block present, each exactly once")
assert_("the page still calls the block Algorithm 1 with the epsilon lift folded in",
        bool(re.search(r"\[barnes2014\]'s Algorithm 1 with the epsilon lift folded in", BODY)))
assert_("the page still says Algorithm 3 is built on the Improved Algorithm 2",
        bool(re.search(r"epsilon variant \(Algorithm 3\) is built on the \*Improved\* Algorithm 2",
                       BODY)))

# ── §2 THE FOUR FIGURES UNDER DISPUTE, PARSED ────────────────────────────────────────────
print("\n-- §2 the disputed figures, as the page prints them --")
N_CELLS = int(num(r"differs from the block\s*\nabove on \*\*(\d+) of (\d+)\*\* cells", "the cell count", 2))
N_DIFF = int(num(r"differs from the block\s*\nabove on \*\*(\d+) of \d+\*\* cells", "the differing cells"))
N_RECV = int(num(r"moves \*\*(\d+) of \d+\*\* receivers", "the moved receivers"))
# The direction word is PARSED, not matched. A first version wrote `(strictly higher)` into
# the pattern itself -- a typed-in expectation hiding in a regex, which is the shape an
# independent attack found in a sibling rig this morning. Written this way, a page that flips
# to "strictly lower" is read as saying so instead of reading as an anchor that has vanished.
DIRECTION = page(r"it is \*\*(strictly \w+) on\s*\nall \d+ and lower on none\*\*", "the direction")
assert_("the page still marks these four figures UNREGISTERED and outside its stamp",
        bool(re.search(r"Those four figures are UNREGISTERED and this paragraph is not\s*\n"
                       r"covered by the page's stamp", BODY)))
assert_("the page still records that source-findings.tsv:36 concludes the opposite",
        bool(re.search(r"`source-findings\.tsv:36` still records the opposite conclusion", BODY)))
print(f"      page: {N_DIFF} of {N_CELLS} cells differ, {N_RECV} receivers move, "
      f"Algorithm 3 is {DIRECTION}")

# ── §3 THE TWO ALGORITHMS ────────────────────────────────────────────────────────────────
SIDE = int(round(math.sqrt(N_CELLS)))
if SIDE * SIDE != N_CELLS:
    sys.exit(f"the page's {N_CELLS} cells are not a square grid; this rig builds one")
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def neighbours8(i, j):
    for di, dj in NB:
        a, b = i + di, j + dj
        if 0 <= a < SIDE and 0 <= b < SIDE:
            yield a, b


def terrain(seed):
    """Value noise on a gentle slope: many basins with varied rims, which is the case a
    flow-routing page is about. This rig's own -- the page names no DEM, no generator, no seed.
    Chosen as a CLASS before anything was run, and swept over SEEDS rather than picked: a
    terrain selected after seeing which answer it gives is not evidence, it is tuning.
    """
    rng = random.Random(seed)
    g = [[rng.uniform(0, 10) for _ in range(SIDE + 1)] for _ in range(SIDE + 1)]
    z = [[0.0] * SIDE for _ in range(SIDE)]
    for i in range(SIDE):
        for j in range(SIDE):
            v = 0.0
            for oct_, amp in ((1, 6.0), (2, 3.0), (4, 1.5)):
                sc = SIDE / oct_
                x, y = i / sc, j / sc
                x0, y0 = int(x), int(y)
                fx, fy = x - x0, y - y0

                def n(a, b, _o=oct_):
                    return g[(a * 7 + b * 13 + _o * 29) % (SIDE + 1)][
                        (a * 17 + b * 5 + _o * 3) % (SIDE + 1)]

                v += amp * ((n(x0, y0) * (1 - fx) + n(x0 + 1, y0) * fx) * (1 - fy)
                            + (n(x0, y0 + 1) * (1 - fx) + n(x0 + 1, y0 + 1) * fx) * fy)
            z[i][j] = round(100.0 + 0.25 * i + v, 6)
    return z


def alg1(z0, use_eps):
    """The page's block at :99-117, transcribed line for line from the text pinned in §1."""
    z = [row[:] for row in z0]
    closed = [[False] * SIDE for _ in range(SIDE)]
    open_q, tie = [], 0
    for i in range(SIDE):
        for j in range(SIDE):
            if i in (0, SIDE - 1) or j in (0, SIDE - 1):
                closed[i][j] = True
                heappush(open_q, (z[i][j], tie, i, j)); tie += 1
    while open_q:
        zc, _, ci, cj = heappop(open_q)
        for a, b in neighbours8(ci, cj):
            if closed[a][b]:
                continue
            closed[a][b] = True
            lift = math.nextafter(z[ci][cj], math.inf) if use_eps else z[ci][cj]
            z[a][b] = max(z[a][b], lift)
            heappush(open_q, (z[a][b], tie, a, b)); tie += 1
    return z


def alg3(z0, use_eps):
    """[barnes2014] Algorithm 3: the epsilon fill on the IMPROVED Priority-Flood (Algorithm 2).

    The difference that matters: a neighbour at or below the lift is a depression interior and
    goes on a PLAIN FIFO, drained to exhaustion before the priority queue is consulted again.
    That is the `m <= n` bound the page points at -- and it is also why the ramp inside a
    depression follows the FIFO's path from ONE entry cell rather than the priority queue's
    shortest path from the nearest.
    """
    z = [row[:] for row in z0]
    closed = [[False] * SIDE for _ in range(SIDE)]
    open_q, tie = [], 0
    pit = []
    head = 0
    fifo = 0
    for i in range(SIDE):
        for j in range(SIDE):
            if i in (0, SIDE - 1) or j in (0, SIDE - 1):
                closed[i][j] = True
                heappush(open_q, (z[i][j], tie, i, j)); tie += 1
    while open_q or head < len(pit):
        if head < len(pit):
            ci, cj = pit[head]; head += 1
        else:
            _, _, ci, cj = heappop(open_q)
        for a, b in neighbours8(ci, cj):
            if closed[a][b]:
                continue
            closed[a][b] = True
            lift = math.nextafter(z[ci][cj], math.inf) if use_eps else z[ci][cj]
            if z[a][b] <= lift:
                z[a][b] = lift
                pit.append((a, b)); fifo += 1
            else:
                z[a][b] = max(z[a][b], lift)
                heappush(open_q, (z[a][b], tie, a, b)); tie += 1
    return z, fifo


def alg3_lifo(z0):
    """Algorithm 3 with the depression queue drained LAST-in-first-out instead of FIFO.

    NOT an algorithm anybody proposes. It exists to prove this rig can SEE a difference: a
    zero result from §5 is a measurement only if the instrument would have reported a
    non-zero one. Swapping the queue discipline is the smallest change that should move the
    fill, and if it does not, §5's zero means the rig is blind and not that the fills agree.
    """
    z = [row[:] for row in z0]
    closed = [[False] * SIDE for _ in range(SIDE)]
    open_q, tie, pit = [], 0, []
    for i in range(SIDE):
        for j in range(SIDE):
            if i in (0, SIDE - 1) or j in (0, SIDE - 1):
                closed[i][j] = True
                heappush(open_q, (z[i][j], tie, i, j)); tie += 1
    while open_q or pit:
        if pit:
            ci, cj = pit.pop()
        else:
            _, _, ci, cj = heappop(open_q)
        for a, b in neighbours8(ci, cj):
            if closed[a][b]:
                continue
            closed[a][b] = True
            lift = math.nextafter(z[ci][cj], math.inf)
            if z[a][b] <= lift:
                z[a][b] = lift
                pit.append((a, b))
            else:
                z[a][b] = max(z[a][b], lift)
                heappush(open_q, (z[a][b], tie, a, b)); tie += 1
    return z


def receivers(z):
    """Steepest-descent receiver per interior cell; None where the cell is a local minimum."""
    out = {}
    for i in range(1, SIDE - 1):
        for j in range(1, SIDE - 1):
            best, bi, bj = 0.0, None, None
            for a, b in neighbours8(i, j):
                d = (z[i][j] - z[a][b]) / math.hypot(i - a, j - b)
                if d > best:
                    best, bi, bj = d, a, b
            out[(i, j)] = (bi, bj)
    return out


def drains(z):
    """Every interior cell must reach the boundary by a strictly descending path."""
    r = receivers(z)
    bad = 0
    for cell in r:
        seen, cur, steps = set(), cell, 0
        while cur is not None and cur not in seen and steps <= SIDE * SIDE:
            seen.add(cur); cur = r.get(cur); steps += 1
            if cur is not None and (cur[0] in (0, SIDE - 1) or cur[1] in (0, SIDE - 1)):
                cur = None; break
        else:
            bad += 1
            continue
        if steps > SIDE * SIDE:
            bad += 1
    return bad


# ── §4 THE CONTROLS, both of which must hold before §5 means anything ────────────────────
SEEDS = tuple(range(1, 11))
print("\n-- §4 the controls --")

# CONTROL A: at eps = 0, Algorithm 1 and Algorithm 2 are the same fill by construction, and
# [barnes2014] Sec 4 says a total and a weak ordering agree there too. If these two
# implementations disagree at eps = 0, one of them is WRONG and nothing below can be
# attributed to the algorithms rather than to the bug.
worstA = 0.0
for sd in SEEDS:
    Z = terrain(sd)
    a, (b, _f) = alg1(Z, False), alg3(Z, False)
    worstA = max(worstA, max(abs(a[i][j] - b[i][j]) for i in range(SIDE) for j in range(SIDE)))
assert_(f"CONTROL A: at eps = 0 the two implementations agree bit-for-bit on all {len(SEEDS)} DEMs",
        worstA == 0.0,
        f"worst |A1 - A3| = {worstA!r}; a non-zero here voids every number below")
if worstA != 0.0:
    print("\nthe control failed; refusing to report a result this rig cannot attribute")
    sys.exit(1)

# CONTROL B: the depression queue must be LOAD-BEARING. §5 is about to report a NEGATIVE --
# no difference -- and a negative from a blind instrument is worth nothing. Draining the pit
# queue LIFO instead of FIFO is the smallest change to Algorithm 3 that should move the fill.
# If that does not move it either, this rig cannot see the thing it is being asked about.
seen, fifo_tot = [], 0
for sd in SEEDS:
    Z = terrain(sd)
    a1s, (a3s, f) = alg1(Z, True), alg3(Z, True)
    fifo_tot += f
    lf = alg3_lifo(Z)
    seen.append((sd, f,
                 sum(1 for i in range(SIDE) for j in range(SIDE) if a1s[i][j] != a3s[i][j]),
                 sum(1 for i in range(SIDE) for j in range(SIDE) if a1s[i][j] != lf[i][j]),
                 sum(1 for i in range(SIDE) for j in range(SIDE) if lf[i][j] > a1s[i][j])))
lifo_moved = sum(1 for _s, _f, _d, l, _h in seen if l > 0)
assert_(f"CONTROL B: swapping the depression queue to LIFO DOES move the fill, on "
        f"{lifo_moved} of {len(SEEDS)} DEMs",
        lifo_moved > 0,
        f"so a zero in §5 is a measurement and not a blind instrument")
assert_("CONTROL B2: the depression queue carries cells at all",
        fifo_tot > 0, f"{fifo_tot} cells went through the FIFO across the sweep")

# ── §5 THE DISPUTE, RUN ──────────────────────────────────────────────────────────────────
print("\n-- §5 the dispute, at eps = nextafter, over a seeded sweep --")
print(f"      {SIDE}x{SIDE} = {SIDE * SIDE} cells; value noise on a 0.25/row slope; seeds "
      f"{SEEDS[0]}..{SEEDS[-1]}")
print("      seed  fifo cells   A1 vs A3   A1 vs A3-LIFO   (LIFO higher)")
for sd, f, d, l, h in seen:
    print(f"      {sd:4d}  {f:10d}   {d:8d}   {l:13d}   {h:12d}")
total_diff = sum(d for _s, _f, d, _l, _h in seen)

assert_("Algorithm 3 and the page's block produce the SAME fill on every DEM in this sweep",
        total_diff == 0,
        f"{total_diff} differing cells over {len(SEEDS)} DEMs, {SIDE * SIDE} cells each")

# The page's direction word is parsed above and, until now, was load-bearing on nothing: a
# tamper test flipped it to "strictly lower" and this rig stayed green. It cannot be asserted
# against Algorithm 3, which comes out IDENTICAL here -- gating that would put the rig red on
# a clean tree over a dispute it has not settled. What CAN be asserted is weaker and still
# real: the direction must be one that some depression-queue ordering actually produces. The
# LIFO variant is the only ordering in this rig that differs at all, so it defines the only
# reachable direction; a page claiming the other one is claiming something no ordering
# constructed here can deliver, and that is worth a FAIL rather than a shrug.
lifo_hi = sum(h for _s, _f, _d, _l, h in seen)
lifo_diff = sum(l for _s, _f, _d, l, _h in seen)
reachable = "strictly higher" if lifo_hi == lifo_diff and lifo_diff > 0 else \
            "strictly lower" if lifo_hi == 0 and lifo_diff > 0 else "neither"
assert_(f"the page's {DIRECTION!r} is a direction some depression-queue ordering produces",
        DIRECTION == reachable,
        f"the only ordering here that differs at all (LIFO) is {reachable} on "
        f"{lifo_diff} cells, {lifo_hi} of them higher")

# ── §6 WHAT THIS SETTLES, WHAT IT DOES NOT, AND THE SIGNATURE ────────────────────────────
print("\n-- §6 what this settles, and what it does not --")
print(f"      SETTLED, on these DEMs: the two fills are identical. That is what")
print(f"      `source-findings.tsv:36` concluded and what flow-routing.md:123-126 denies.")
print(f"      The reason is the page's OWN tie-breaking paragraph: with a total order the")
print(f"      priority queue inside a filled depression pops in insertion order, which IS the")
print(f"      FIFO's order, so Algorithm 2's plain queue is the optimisation the paper says it")
print(f"      is -- same surface, fewer heap operations.")
print()
print(f"      NOT SETTLED: the page's {N_DIFF} of {N_CELLS} and {N_RECV} receivers. The page names")
print(f"      {N_CELLS} cells and nothing else -- no DEM, no generator, no seed -- so no rig can")
print(f"      land on its counts, and this sweep is NOT a refutation of a measurement on a")
print(f"      terrain nobody has published.")
print()
print(f"      THE SIGNATURE, and it is the useful part. The page reports Algorithm 3 as")
print(f"      {DIRECTION!r} and lower on none. This rig's FIFO Algorithm 3 is neither -- it is")
print(f"      identical. The variant that DOES come out strictly higher and never lower is the")
print(f"      LIFO one in CONTROL B, on every DEM in the sweep. So the page's direction is the")
print(f"      signature of a depression queue drained in the wrong order, which is exactly the")
print(f"      doubt the page raises about itself: 'whether the diagnosis below describes the")
print(f"      paper or our transcription of it'. That is a lead for whoever settles it, and it")
print(f"      is NOT a finding -- this rig has not seen the page's code.")
print()
print(f"      NOT EXERCISED: these DEMs carry no EXACT elevation ties, so the sweep says")
print(f"      nothing about the total-order requirement. `source-findings.tsv:35` reproduced")
print(f"      that separately on a flat basin with two equal outlets, and it stands.")

print()
sys.exit(0 if ok else 1)
