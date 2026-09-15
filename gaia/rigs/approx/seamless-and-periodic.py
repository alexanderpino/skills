#!/usr/bin/env python3
"""seamless-and-periodic.md's `## Use this` fence (:40-46), RUN against its own page.

Six lines in that fence, and this rig gates all six -- each by running the thing the line
tells a reader to paste, and comparing the result against a number PARSED OUT OF THE PAGE:

  :41 `period P ... a multiple of 2^L_max`    -> the phase table :398-402, run in 1-D
  :42 `hash: ... table >= P*lacunarity^(octaves-1)` -> 32768 entries and its byte costs
  :43 `noise: gradient(i mod P_l, j mod P_l)` -> the wrap-period table :96-99, run
  :44 `sim: grid[(i + di) mod H, (j + dj) mod W]` -> exported = 0.000%, proved and run
  :45 `route: priority_flood(seeds = [the one authored sink])` -> the table :256-260, run
  :46 `filter: pads with wrap, never reflect` -> the padding table :378-384, run

THE ONE RULE. Every expected value is parsed at run time, anchored on PROSE and never on a
number. No expectation is typed into this file. A missing anchor prints ANCHOR GONE and exits
1 -- a figure that has gone missing is a FAIL, not a silent skip.

WHAT THIS RIG WILL NOT DO, and why (the page states more than it can support alone):

  * ABSOLUTE WALL-CLOCK -- 2.4 ms, 39.5 ms, 241.9 ms. The page says outright they are one CPU
    rig's, and rigs/README.md says absolute wall-clock does not survive a port. Their INTERNAL
    arithmetic is gated instead (6% = 2.4/39.5, 6.1x = 241.9/39.5) at both ends that print it.
  * FIELD-DEPENDENT MAGNITUDES -- the seam ratios (0.898, 1.085, 0.389), rim bias, fill volumes
    (414.1, 660.3), cells raised (2514, 3471), the naive row's amplitudes (1.28, 1.49, 1.59),
    the padding cells (1.19, 221.5, 397.7), the phase table's 1.8e-01/2.2e-01/4.2e-01. Each is
    a measurement of a field THIS DOCUMENT DOES NOT STATE -- another rig's seed, solver and
    capacity law. This rig reproduces their STRUCTURE (exactly zero vs not, which side is
    worse, the ratio between two page cells) and says so at each site rather than inventing a
    tolerance wide enough to swallow the difference.
  * `lo + hi = h`, THE ROUND TRIP, AS A GATE ON PADDING -- it CANNOT FAIL. The page's own point
    at :387-390 is that it holds by construction for every mode, so no padding edit can move
    it. It is run (all five modes must still pass it, which is the page's claim) but the seam
    is gated separately, which is exactly what :390 tells the reader to do.
  * THE 2.8x SIMPLEX ARITHMETIC RATIO (:72, :145, :437). Its own operands, printed beside it at
    :143-145, are 5 corners x 22 ops against 3 x 12 = 3.06x, not 2.8x. Gating it would make
    this rig red on the unmutated page. Reported, not gated, and not fixed here.

HALTING. No loop in this file has a data-dependent bound. Every loop is over a parsed list of
page cells, over a fixed grid (side parsed from prose), over a fixed octave count (parsed), or
over a fixed step count. The one algorithm that could run forever -- priority-flood -- marks a
cell closed AT PUSH TIME, so each of the side*side cells is pushed at most once and the queue
drains in at most side*side pops. `_pad_index` reflects by a closed-form modulo, never a loop.

    python3 seamless-and-periodic.py              # the gate; exit 0 iff the page reproduces
    python3 seamless-and-periodic.py --timings    # the numpy timing rig the page cites, below

⚠️ THIS FILE CARRIES TWO PROGRAMS. The page cites `seamless-and-periodic.py` at :121 and :148
for the 256 KB byte count and the 39.5/241.9 ms pair, and `registers/corrections.tsv:206`
records a re-run of it. That numpy rig is PRESERVED VERBATIM below, under `--timings`, with
its numpy import deferred into the function so that the gate above it is stdlib-only. Deleting
it would have left two page citations and a correction row pointing at a file that no longer
computes what they say it computes.
"""
import math
import time
import pathlib
import re
import sys
from fractions import Fraction

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "seamless-and-periodic.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")

FAILED: list[str] = []
ANCHORS: list[tuple[str, int]] = []
CHECKS = [0]
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}

# The page's own two populations of wrap error are <= 3.5e-13 ("exact") and >= 4.7e-02
# ("fails") -- five orders apart, with nothing between. This rig splits them here, asserts
# every page cell lands in one or the other (a cell edited INTO the gap fails), and requires
# its own measurement to land in the same one.
EXACT_MAX = 1e-12
FAIL_MIN = 1e-3
FULL_AMP = 0.5          # "fail at the full noise amplitude" := at least half the field's p-p
# ⚠️ Sample OFF the lattice. `a * T / samples` lands on integer lattice points whenever the
# sample count divides the period, and a gradient noise is IDENTICALLY ZERO there: the first
# version of this rig measured a 0.0 wrap error over a 0.0 peak-to-peak field at T = 64 and
# called it a pass. OFFSET is a dyadic fraction, so every sample coordinate and every x+T is
# still exactly representable and a 0.0 is still a true 0.0.
OFFSET = 0.3125
# "MACHINE PRECISION"/"EXACT", where the page prints the RESIDUE of a float64 computation --
# :207's toroidal mass drift 1.97e-16, :380-384's round-trip column 1.1e-16, :443's 1.1e-16.
# One ulp of a unit-scale quantity is 2^-52; 16 ulps lets a handful of roundings compound in a
# multi-term sum and is the WHOLE width of this gate. It is a rig constant with its reason
# written here -- it is NOT read off the digits of any number under test, so the page cannot
# buy itself a wider gate by printing fewer of them. The other population on this page is
# -8.5e-03 and 2.1e-02, thirteen orders away, so nothing legitimate sits near the edge.
MACHINE_ULP = 2.0 ** -52            # 2.220446e-16
MACHINE_MAX = 16.0 * MACHINE_ULP    # 3.553e-15


def passed(msg: str) -> None:
    CHECKS[0] += 1
    print(f"PASS  {msg}")


def fail(msg: str) -> None:
    CHECKS[0] += 1
    FAILED.append(msg)
    print(f"FAIL  {msg}")


def page(pattern: str, what: str, group: int = 1, flags: int = 0) -> str:
    """The only way an expectation enters this rig. Anchor gone => exit 1, never skip."""
    ANCHORS.append((pattern, len(re.findall(pattern, BODY, flags))))
    m = re.search(pattern, BODY, flags)
    if not m:
        sys.exit(f"ANCHOR GONE: the page no longer states {what}\n"
                 f"             pattern {pattern!r}\n"
                 f"             a figure that has gone missing is a FAIL, not a silent skip")
    return m.group(group)


def inner(pattern: str, text: str, what: str, flags: int = 0):
    """A sub-pattern inside a span `page()` already anchored. Gone => exit 1, never skip."""
    m = re.search(pattern, text, flags)
    if not m:
        sys.exit(f"ANCHOR GONE: the page no longer states {what}\n"
                 f"             pattern {pattern!r}\n"
                 f"             a figure that has gone missing is a FAIL, not a silent skip")
    return m


def pagef(pattern: str, what: str, group: int = 1, flags: int = 0) -> float:
    return float(page(pattern, what, group, flags))


def pagei(pattern: str, what: str, group: int = 1, flags: int = 0) -> int:
    return int(page(pattern, what, group, flags))


def row(pattern: str, what: str) -> list[str]:
    """The cells of the one table row matching `pattern`, without the leading label."""
    line = page(pattern, what, 0, re.M)
    return [c.strip() for c in line.strip().strip("|").split("|")][1:]


def cell(text: str, what: str) -> float:
    m = re.search(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", text.replace("−", "-"), re.I)
    if not m:
        sys.exit(f"ANCHOR GONE: {what} is no longer a number on the page: {text!r}")
    return float(m.group(0))


def ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


def check(label: str, got: float, want: float, tol: float = 0.0) -> bool:
    good = abs(got - want) <= tol
    note = f" (tol {tol:g})" if tol else " (tolerance ZERO)"
    (passed if good else fail)(f"{label}: rig {got:.6g}, page {want:.6g}{note}")
    return good


def same(label: str, a: float, b: float, a_at: str, b_at: str, tol: float = 0.0) -> bool:
    good = abs(a - b) <= tol
    (passed if good else fail)(
        f"{label}: {a_at} says {a:.6g}, {b_at} says {b:.6g}"
        f"{'' if good else '  <-- the two ends DISAGREE'}")
    return good


def head(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, 86 - len(title)))


# ═════════════════════════════════════════════════════════════════════════════════════════
#  the constructions the fence recommends, transcribed and runnable (stdlib only)
# ═════════════════════════════════════════════════════════════════════════════════════════
GRAD8 = [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0),
         (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)]


def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _mix32(a: int) -> int:
    a &= 0xFFFFFFFF
    a ^= a >> 16
    a = (a * 0x7FEB352D) & 0xFFFFFFFF
    a ^= a >> 15
    a = (a * 0x846CA68B) & 0xFFFFFFFF
    a ^= a >> 16
    return a


def mixer_hash(i: int, j: int) -> int:
    """:118 'An integer mixer with no 8-bit mask reaches any P_l for free.'"""
    return _mix32(_mix32(i & 0xFFFFFFFF) ^ ((j * 0x9E3779B1) & 0xFFFFFFFF))


def table_hash(size: int, seed: int = 20260915):
    """A permutation table of `size` entries -- the thing :107 measures on."""
    perm = list(range(size))
    s = seed
    for k in range(size - 1, 0, -1):            # Fisher-Yates: fixed bound, size-1 swaps
        s = (1103515245 * s + 12345) % (1 << 31)
        m = s % (k + 1)
        perm[k], perm[m] = perm[m], perm[k]

    def h(i: int, j: int) -> int:
        return perm[(perm[i % size] + j) % size]
    return h


def noise2(x: float, y: float, hsh, period=None) -> float:
    """:43 `gradient(i mod P_l, j mod P_l)` -- `period=None` is the naive raw-index hash."""
    i0 = math.floor(x)
    j0 = math.floor(y)
    fx = x - i0
    fy = y - j0
    i1 = i0 + 1
    j1 = j0 + 1
    if period is not None:                      # :91 i0 = floor(x) % P; i1 = (floor(x)+1) % P
        i0 %= period
        j0 %= period
        i1 %= period
        j1 %= period
    u = _fade(fx)
    v = _fade(fy)
    gx, gy = GRAD8[hsh(i0, j0) & 7]
    n00 = gx * fx + gy * fy
    gx, gy = GRAD8[hsh(i1, j0) & 7]
    n10 = gx * (fx - 1.0) + gy * fy
    gx, gy = GRAD8[hsh(i0, j1) & 7]
    n01 = gx * fx + gy * (fy - 1.0)
    gx, gy = GRAD8[hsh(i1, j1) & 7]
    n11 = gx * (fx - 1.0) + gy * (fy - 1.0)
    a = n00 + u * (n10 - n00)
    b = n01 + u * (n11 - n01)
    return a + v * (b - a)


def wrap_error(T: int, hsh, period, samples: int = 64):
    """max |f(x) - f(x+T)| (:94), over samples*samples points, plus the field's peak-to-peak.

    The page measures over 512²; this rig uses 64² because what it asserts is BIT-EXACTNESS
    and a full-amplitude failure, neither of which a smaller sample set can invent. Every
    sample lands on an exactly-representable coordinate (T/64 with T an integer), so
    floor(x+T) == floor(x)+T holds exactly and a 0.0 here is a true 0.0.
    """
    worst = 0.0
    lo = hi = None
    for a in range(samples):
        x = a * T / samples + OFFSET      # ⚠️ offset OUTSIDE the stride: `(a+OFFSET)*T/samples`
        for b in range(samples):          # is an INTEGER whenever OFFSET*T/samples is, and at
            y = b * T / samples + OFFSET  # T = 1024, samples = 64 it is exactly 5.
            f = noise2(x, y, hsh, period)
            dx = abs(noise2(x + T, y, hsh, period) - f)
            dy = abs(noise2(x, y + T, hsh, period) - f)
            if dx > worst:
                worst = dx
            if dy > worst:
                worst = dy
            lo = f if lo is None or f < lo else lo
            hi = f if hi is None or f > hi else hi
    return worst, (hi - lo)


def fbm_wrap_error(P: int, lac: float, octaves: int, samples: int = 32):
    """:115-116 octave l reduces mod `P·lacunarity^l`; :158 it must stay an INTEGER.

    Where it does not, the rig does what an implementer does -- rounds -- and the seam that
    :163 measures appears. The hash is the mixer, so the table length is never the binding
    constraint here (that is the separate claim gated in §the hash).
    """
    per = [round(P * lac ** l) for l in range(octaves)]
    amp = [0.5 ** l for l in range(octaves)]
    scl = [lac ** l for l in range(octaves)]

    def f(x: float, y: float) -> float:
        t = 0.0
        for l in range(octaves):
            t += amp[l] * noise2(x * scl[l], y * scl[l], mixer_hash, per[l])
        return t

    worst = 0.0
    lo = hi = None
    for a in range(samples):
        x = a * P / samples + OFFSET      # offset outside the stride; see wrap_error
        for b in range(samples):
            y = b * P / samples + OFFSET
            v = f(x, y)
            worst = max(worst, abs(f(x + P, y) - v), abs(f(x, y + P) - v))
            lo = v if lo is None or v < lo else lo
            hi = v if hi is None or v > hi else hi
    return worst, (hi - lo)


def neighbours4(c: int, H: int, W: int, torus: bool):
    """:44, transcribed literally: grid[(i + di) mod H, (j + dj) mod W]."""
    i, j = divmod(c, W)
    out = []
    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        if torus:
            out.append(((i + di) % H) * W + ((j + dj) % W))
        else:
            ni, nj = i + di, j + dj
            out.append(ni * W + nj if 0 <= ni < H and 0 <= nj < W else -1)
    return out


def neighbours8(c: int, side: int, torus: bool):
    i, j = divmod(c, side)
    out = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            if torus:
                out.append(((i + di) % side) * side + ((j + dj) % side))
            else:
                ni, nj = i + di, j + dj
                if 0 <= ni < side and 0 <= nj < side:
                    out.append(ni * side + nj)
    return out


def priority_flood(h, side: int, seeds, torus: bool, eps: float = 1e-6):
    """[barnes2014] §3.1-§3.2 as the page describes it: the seed set is the whole algorithm.

    Halting: a cell is marked closed AT PUSH TIME, so it is pushed at most once and the heap
    drains in at most side*side pops. `reached` is the pop count -- :260's 'cells reached'.
    """
    import heapq
    n = side * side
    filled = list(h)
    closed = [False] * n
    pq = []
    for s in seeds:
        closed[s] = True
        heapq.heappush(pq, (filled[s], s))
    reached = 0
    raised = 0
    while pq:
        e, c = heapq.heappop(pq)
        reached += 1
        for nb in neighbours8(c, side, torus):
            if not closed[nb]:
                closed[nb] = True
                if filled[nb] <= e:
                    filled[nb] = e + eps
                    raised += 1
                heapq.heappush(pq, (filled[nb], nb))
    return filled, reached, raised


def d8_accumulation(filled, side: int, torus: bool):
    """Every cell drains one cell's worth; the answer is where it piles up (:259)."""
    n = side * side
    acc = [1] * n
    for c in sorted(range(n), key=lambda k: -filled[k]):
        best = -1
        drop = 0.0
        for nb in neighbours8(c, side, torus):
            d = filled[c] - filled[nb]
            if d > drop:
                drop = d
                best = nb
        if best >= 0:
            acc[best] += acc[c]
    return max(acc)


def _pad_index(i: int, n: int, mode: str) -> int:
    """Closed form -- no loop, so no data-dependent bound."""
    if mode == "wrap":
        return i % n
    if mode == "reflect":                       # d c b | a b c d | c b a
        if n == 1:
            return 0
        p = 2 * (n - 1)
        i %= p
        return i if i < n else p - i
    raise ValueError(mode)


def _k5(a: float):
    return (0.25 - a / 2.0, 0.25, a, 0.25, 0.25 - a / 2.0)


def reduce1d(sig, a: float, mode: str):
    k = _k5(a)
    n = len(sig)
    out = []
    for c in range(0, n, 2):
        out.append(k[0] * sig[_pad_index(c - 2, n, mode)]
                   + k[1] * sig[_pad_index(c - 1, n, mode)]
                   + k[2] * sig[c]
                   + k[3] * sig[_pad_index(c + 1, n, mode)]
                   + k[4] * sig[_pad_index(c + 2, n, mode)])
    return out


def expand1d(sig, n_out: int, a: float, mode: str):
    k = [2.0 * x for x in _k5(a)]
    up = [0.0] * n_out
    for i, v in enumerate(sig):
        if 2 * i < n_out:
            up[2 * i] = v
    out = []
    for c in range(n_out):
        out.append(k[0] * up[_pad_index(c - 2, n_out, mode)]
                   + k[1] * up[_pad_index(c - 1, n_out, mode)]
                   + k[2] * up[c]
                   + k[3] * up[_pad_index(c + 1, n_out, mode)]
                   + k[4] * up[_pad_index(c + 2, n_out, mode)])
    return out


def low_band_1d(sig, levels: int, a: float, mode: str):
    sizes = []
    cur = sig
    for _ in range(levels):                     # fixed bound: `levels`, parsed from the page
        sizes.append(len(cur))
        cur = reduce1d(cur, a, mode)
    for nout in reversed(sizes):
        cur = expand1d(cur, nout, a, mode)
    return cur


def reduce2d(img, a: float, mode: str):
    rows = [reduce1d(r, a, mode) for r in img]
    w = len(rows[0])
    cols = [reduce1d([rows[y][x] for y in range(len(rows))], a, mode) for x in range(w)]
    return [[cols[x][y] for x in range(w)] for y in range(len(cols[0]))]


def expand2d(img, h_out: int, w_out: int, a: float, mode: str):
    w = len(img[0])
    cols = [expand1d([r[x] for r in img], h_out, a, mode) for x in range(w)]
    rows = [[cols[x][y] for x in range(w)] for y in range(h_out)]
    return [expand1d(r, w_out, a, mode) for r in rows]


def low_band_2d(img, levels: int, a: float, mode: str):
    sizes = []
    cur = img
    for _ in range(levels):
        sizes.append((len(cur), len(cur[0])))
        cur = reduce2d(cur, a, mode)
    for h_out, w_out in reversed(sizes):
        cur = expand2d(cur, h_out, w_out, a, mode)
    return cur


def seam_ratio(img):
    """:386 'the low band's maximum wrapped step over its mean interior step'."""
    n = len(img)
    w = len(img[0])
    wrapped = max(max(abs(r[0] - r[-1]) for r in img),
                  max(abs(img[0][x] - img[-1][x]) for x in range(w)))
    tot = 0.0
    cnt = 0
    for r in img:
        for x in range(w - 1):
            tot += abs(r[x + 1] - r[x])
            cnt += 1
    for y in range(n - 1):
        for x in range(w):
            tot += abs(img[y + 1][x] - img[y][x])
            cnt += 1
    return wrapped / (tot / cnt)


def periodic_field(side: int, period: int, octaves: int = 4):
    """A field periodic by construction -- the fence's own noise line, used as input."""
    per = [period * (2 ** l) for l in range(octaves)]
    out = []
    for i in range(side):
        x = i * period / side
        r = []
        for j in range(side):
            y = j * period / side
            t = 0.0
            for l in range(octaves):
                s = 2.0 ** l
                t += (0.5 ** l) * noise2(x * s, y * s, mixer_hash, per[l])
            r.append(t)
        out.append(r)
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
#  the gate
# ═════════════════════════════════════════════════════════════════════════════════════════
def gate() -> int:
    print(f"gate   {DOC}")
    print(f"       {len(BODY.splitlines())} lines, every expectation parsed from them")

    # ── A. the fence is still the fence this rig transcribes ──────────────────────────────
    head("A. the `## Use this` fence, :40-46")
    FENCE = page(r"## Use this\b.*?\n```\n(.*?)```", "a fenced block under `## Use this`", 1, re.S)
    FEATURES = [
        (r"^period P\b.*\ba multiple of 2\^L_max", "period P, a multiple of 2^L_max"),
        (r"^hash:.*\btable >= P\*lacunarity\^\(octaves-1\)", "a hash table >= P*lacunarity^(octaves-1)"),
        (r"^noise:\s+gradient\(i mod P_l, j mod P_l\)", "gradient(i mod P_l, j mod P_l)"),
        (r"^sim:\s+neighbour\(i, j\) = grid\[\(i \+ di\) mod H, \(j \+ dj\) mod W\]", "the wrapping neighbour lookup"),
        (r"^route:\s+priority_flood\(seeds = \[the one authored sink\]\)", "priority_flood seeded with the one authored sink"),
        (r"^filter: every convolution pads with `wrap`, never `reflect`", "wrap padding at every convolution"),
    ]
    for pat, what in FEATURES:
        if re.search(pat, FENCE, re.M):
            passed(f"the fence still recommends {what}")
        else:
            fail(f"the fence no longer recommends {what} -- this rig is now running something "
                 f"the page does not recommend")
    if re.search(r"P_l = P \* frequency_l, MUST be an integer", FENCE):
        passed("the fence still requires P_l to be an INTEGER")
    else:
        fail("the fence no longer requires P_l to be an integer")

    # ── B. `noise: gradient(i mod P_l, j mod P_l)`, run at the page's own periods ──────────
    head("B. :43 the modular lattice index, against the wrap-period table :96-99")
    TSIZE = pagei(r"measured on a (\d+)-entry table", "the permutation table's length, in prose (:107)")
    hdr = row(r"^\| construction \| T = .*$", "the wrap-period table header")
    PERIODS = [int(re.search(r"T = (\d+)", c).group(1)) for c in hdr]
    NAIVE = [cell(c, "a naive-row cell") for c in
             row(r"^\| Perlin, naive hash of the raw index \|.*$", "the naive row")]
    MODROW = [cell(c, "an index-mod-T cell") for c in
              row(r"^\| Perlin, index mod T \|.*$", "the index-mod-T row")]
    if not (len(PERIODS) == len(NAIVE) == len(MODROW)):
        fail(f"the table is ragged: {len(PERIODS)} periods, {len(NAIVE)} naive cells, "
             f"{len(MODROW)} modular cells")
    PROSE_T = ints(page(r"`0\.0` difference at\s*\nperiods ([^—]+?) — where the naive construction "
                        r"wraps only at \d+", "the periods the modular lattice wraps at (:49-50)"))
    ONLY_50 = pagei(r"wraps only at (\d+), its hash table's own", "where the naive one wraps (:50)")
    ONLY_103 = pagei(r"naive row is zero at exactly one value, (\d+),",
                     "the one value the naive row is zero at (:103)")
    ONLY_434 = pagei(r"\| The noise wraps at (\d+) and at no other period \|",
                     "the failure table's naive period (:434)")
    same("the naive period, :50 against :103", ONLY_50, ONLY_103, ":50", ":103")
    same("the naive period, :50 against the failure table", ONLY_50, ONLY_434, ":50", ":434")

    tbl = table_hash(TSIZE)
    amp = 0.0
    for T, want_naive, want_mod in zip(PERIODS, NAIVE, MODROW):
        e_naive, pp = wrap_error(T, tbl, None)
        if pp <= 0.0:
            fail(f"T = {T}: the rig's own sample set is degenerate (peak-to-peak 0)")
            continue
        e_mod, _ = wrap_error(T, tbl, T)
        amp = max(amp, pp)
        # the modular row is a bit-exact MEASUREMENT: reproduced at tolerance ZERO
        check(f"T = {T:<4d} index mod T, max |f(x) − f(x+T)|", e_mod, want_mod)
        # the naive row: the page prints 0.0 or an amplitude. Zero is reproduced exactly;
        # an amplitude is another rig's permutation table, so only its NON-zero-ness is.
        if want_naive == 0.0:
            check(f"T = {T:<4d} naive hash of the raw index", e_naive, 0.0)
        elif e_naive >= FULL_AMP * pp:
            passed(f"T = {T:<4d} naive hash: rig {e_naive:.3g} >= half the field's {pp:.3g} "
                   f"peak-to-peak, page prints {want_naive:g} (a full-amplitude seam)")
        else:
            fail(f"T = {T:<4d} naive hash: rig {e_naive:.3g}, but the page prints "
                 f"{want_naive:g}, a full-amplitude seam")
    zeros = [T for T, v in zip(PERIODS, NAIVE) if v == 0.0]
    if zeros == [ONLY_50]:
        passed(f"the naive row is zero at exactly one period, {ONLY_50}, and the prose says so "
               f"in three places")
    else:
        fail(f"the naive row is zero at {zeros}; the prose says only at {ONLY_50}")
    mod_zeros = {T for T, v in zip(PERIODS, MODROW) if v == 0.0}
    if set(PROSE_T) <= mod_zeros:
        passed(f"the prose's bit-exact periods {PROSE_T} are all 0.0 in the modular row")
    else:
        fail(f"the prose claims bit-exact at {PROSE_T}; the modular row is 0.0 only at "
             f"{sorted(mod_zeros)}")
    # ⚠️ `<=` alone lets the prose DROP periods and stay green. :49-50 is an exhaustive
    # statement about this table: the modular row wraps at the periods it lists, and the naive
    # row "wraps only at" one more. So the two lists together must be the table's own columns.
    if set(PERIODS) == mod_zeros:
        passed(f"the modular row is 0.0 at every period the table measures, {PERIODS}")
    else:
        fail(f"the modular row is 0.0 at {sorted(mod_zeros)}, not at every measured period "
             f"{PERIODS}")
    if set(PROSE_T) | {ONLY_50} == set(PERIODS):
        passed(f"the prose's {sorted(PROSE_T)} plus the naive row's {ONLY_50} is exactly the "
               f"set of periods the table measures -- :49-50 names every column")
    else:
        fail(f":49-50 names {sorted(PROSE_T)} plus {ONLY_50} = {sorted(set(PROSE_T) | {ONLY_50})}; "
             f"the table measures {PERIODS} -- the prose no longer covers the table")

    # ── the 2-D simplex row of the SAME table (:100), gated by the SAME structural claim ──
    # :127 'the measured error stays at full noise amplitude for every period tried'; :437
    # 'measured full-amplitude error at every period'. That is field-independent: every cell
    # the row prints must be in the FAILING population and none may collapse toward zero.
    SIMROW = row(r"^\| 2-D simplex, same trick \|.*$", "the 2-D simplex row (:100)")
    SIM127 = page(r"the\s*\nmeasured error stays at (full noise amplitude) for every period tried",
                  "the simplex claim (:126-127)")
    SIM437 = page(r"the integers you reduced are not the tile's; measured (full-amplitude) error "
                  r"at every period", "the failure table's simplex claim (:437)")
    sim = [(T, cell(c, "a 2-D simplex cell")) for T, c in zip(PERIODS, SIMROW)
           if re.search(r"\d", c)]
    if not sim:
        fail(f"the 2-D simplex row measures nothing, and :127 claims '{SIM127}' at every "
             f"period tried")
    else:
        top = max(v for _, v in sim)
        floor_amp = FULL_AMP * max(max(NAIVE), top)
        for T, v in sim:
            if v >= FAIL_MIN and v >= floor_amp:
                passed(f"T = {T:<4d} 2-D simplex: {v:g}, still {SIM127} (>= {floor_amp:g}, half "
                       f"of the largest amplitude this table prints) -- :127 and :437 say the "
                       f"trick does not take")
            else:
                fail(f"T = {T:<4d} 2-D simplex: {v:g} -- :127 says '{SIM127}' and :437 says "
                     f"'{SIM437} at every period'; against the naive row's own {max(NAIVE):g}, "
                     f"{v:g} is not a full-amplitude error")
        blank = [T for T, c in zip(PERIODS, SIMROW) if not re.search(r"\d", c)]
        passed(f"the 2-D simplex row is measured at {[T for T, _ in sim]} and not at {blank}, "
               f"and every measured cell fails")

    # ── :141 the 4-D torus embedding's residue, 'the cos/sin round-off, not a seam' ───────
    RES141 = pagef(r"with no modular indexing anywhere\. Measured `([-\d.eE+]+)` at",
                   "the embedding's measured residue (:141)")
    T141 = ints(page(r"with no modular indexing anywhere\. Measured `[-\d.eE+]+` at\s*\n"
                     r"`T` = ([\d,\sand]+) — the residue is", "the periods it was measured at (:141-142)"))
    if RES141 <= EXACT_MAX:
        passed(f"the embedding's {RES141:g} at T = {T141} is in this rig's EXACT population "
               f"(<= {EXACT_MAX:g}), as ':142 the residue is the cos/sin round-off, not a "
               f"seam' requires")
    else:
        fail(f":141 measures {RES141:g} and :142 calls it round-off and not a seam; "
             f"{RES141:g} is in the FAILING population (>= {FAIL_MIN:g})")
    if set(T141) == set(PROSE_T):
        passed(f"the embedding was measured at the same periods :49-50 claims for the modular "
               f"lattice, {sorted(T141)} -- the two halves of the fix are compared like for like")
    else:
        fail(f":141 measures the embedding at {sorted(T141)}; :49-50 claims the modular "
             f"lattice at {sorted(PROSE_T)} -- they are no longer the same periods")

    # ── C. multiple, not divisor: the correction :106-110 carries, re-run ──────────────────
    head("C. :106-110 'a multiple of the table size, not a divisor of it'")
    DIVS = ints(page(r"measured on a \d+-entry table, `T` = ([^—]+?) all divide (\d+) and",
                     "the divisors that fail (:107)"))
    DIV_OF = pagei(r"measured on a \d+-entry table, `T` = [^—]+? all divide (\d+) and",
                   "what they divide (:107)", 1)
    MULS = ints(page(r"while `T` = ([\d,\sand\n]+?) are multiples of \d+ and are exact to",
                     "the multiples that wrap (:108-109)"))
    MUL_OF = pagei(r"are multiples of (\d+) and are exact to", "what they are multiples of (:109)")
    BOUND = pagef(r"are multiples of \d+ and are exact to ([-\d.eE+]+)\.", "the bound they meet (:109)")
    QUOTED = pagef(r"the table above prints — ([\d.]+) at `T` = \d+ —", "the amplitude quoted (:108)")
    QUOTED_AT = pagei(r"the table above prints — [\d.]+ at `T` = (\d+) —", "where it is quoted from")
    same(f"the amplitude quoted at :108 against the table's own T = {QUOTED_AT} cell",
         QUOTED, NAIVE[PERIODS.index(QUOTED_AT)], ":108", ":98")
    if DIV_OF == MUL_OF == TSIZE:
        passed(f"the prose divides and multiplies by the same {TSIZE} it measures on")
    else:
        fail(f"the prose divides by {DIV_OF}, multiplies by {MUL_OF}, measures on {TSIZE}")
    bad = [t for t in DIVS if TSIZE % t]
    if bad:
        fail(f"the page calls {bad} divisors of {TSIZE}, and they are not")
    else:
        passed(f"every T the page calls a divisor of {TSIZE} divides it: {DIVS}")
    bad = [t for t in MULS if t % TSIZE]
    if bad:
        fail(f"the page calls {bad} multiples of {TSIZE}, and they are not")
    else:
        passed(f"every T the page calls a multiple of {TSIZE} is one: {MULS}")
    for T in DIVS:
        e, pp = wrap_error(T, tbl, None)
        if pp <= 0.0:
            fail(f"T = {T}: the rig's own sample set is degenerate (peak-to-peak 0)")
            continue
        if e >= FULL_AMP * pp:
            passed(f"T = {T:<4d} divides {TSIZE} and STILL SEAMS: {e:.3g} against a {pp:.3g} "
                   f"peak-to-peak")
        else:
            fail(f"T = {T:<4d} divides {TSIZE} and the page says it seams at full amplitude; "
                 f"rig measures {e:.3g} over a {pp:.3g} peak-to-peak")
    if BOUND <= EXACT_MAX:
        passed(f"the page calls {BOUND:g} exact, and it is machine-epsilon scale -- so the "
               f"bound below is the page's claim and not a hole this rig can fall through")
    else:
        fail(f"the page calls {BOUND:g} 'exact'; that is not machine-epsilon scale, and a rig "
             f"asserting err <= {BOUND:g} would be asserting nothing")
    for T in MULS:
        e, pp = wrap_error(T, tbl, None)
        if pp <= 0.0:
            fail(f"T = {T}: the rig's own sample set is degenerate (peak-to-peak 0)")
            continue
        check(f"T = {T:<4d} is a multiple of {TSIZE} and wraps (page: exact to {BOUND:g})",
              e, 0.0, BOUND)

    # ── D. `hash: ... a table >= P*lacunarity^(octaves-1)` ─────────────────────────────────
    head("D. :42 the hash must outrun the FINEST octave, not P")
    EXP = page(r"table >= P\*lacunarity\^\(octaves-(\d+)\)", "the fence's own exponent", 1)
    HOCT = WORDS[page(r"(\w+)-octave, lacunarity-\d+ stack at `P` = \d+", "the octave count (:117)")]
    HLAC = pagei(r"\w+-octave, lacunarity-(\d+) stack at `P` = \d+", "the lacunarity (:117)")
    HPER = pagei(r"\w+-octave, lacunarity-\d+ stack at `P` = (\d+)", "the period (:117)")
    FINEST = HPER * HLAC ** (HOCT - int(EXP))
    ENTRIES_121 = pagei(r"`nbytes` \(`[\w.-]+\.py`\): (\d+) entries is", "the table length (:121)")
    KB_I32_121 = pagei(r"(\d+) entries is \*\*(\d+) KB\*\* as `int32` doubled", "256 KB (:121)", 2)
    KB_U16_121 = pagei(r"\*\*(\d+) KB\*\* as `uint16`", "64 KB (:122)")
    KB_P_121 = pagei(r"the `P`-entry table that fails is (\d+) KB", "8 KB (:122)")
    ENTRIES_435, KB_I32_435, KB_U16_435, KB_P_435 = (int(x) for x in re.findall(
        r"measured, (\d+) entries is (\d+) KB as `int32` and (\d+) KB as `uint16`, against (\d+) KB",
        page(r"(measured, \d+ entries is \d+ KB as `int32` and \d+ KB as `uint16`, against \d+ KB)",
             "the failure table's byte counts (:435)"))[0])
    KB_60 = pagei(r"is \*\*(\d+) KB\*\*\. ⚠️ A vectorised CPU rig", "the headline's 256 KB (:60)")
    check(f"P*lacunarity^(octaves-{EXP}) = {HPER}*{HLAC}^{HOCT - int(EXP)}", FINEST, ENTRIES_121)
    same("the table length, :121 against the failure table", ENTRIES_121, ENTRIES_435, ":121", ":435")
    same("256 KB, :121 against the failure table", KB_I32_121, KB_I32_435, ":121", ":435")
    same("256 KB, :121 against the headline", KB_I32_121, KB_60, ":121", ":60")
    same("64 KB, :122 against the failure table", KB_U16_121, KB_U16_435, ":122", ":435")
    same("8 KB, :122 against the failure table", KB_P_121, KB_P_435, ":122", ":435")
    check(f"{ENTRIES_121} int32 entries, doubled for the wrap-around read",
          ENTRIES_121 * 4 * 2 / 1024, KB_I32_121)
    check(f"{ENTRIES_121} uint16 entries", ENTRIES_121 * 2 / 1024, KB_U16_121)
    check(f"the P-entry table that fails, P = {HPER}, int32 doubled",
          HPER * 4 * 2 / 1024, KB_P_121)
    SHIFT = pagei(r"at a (\d+)-cell shift \([-\d.eE+]+\) against",
                  "the shift the P-entry table aliases at (:118)")
    LO, HI = ints(page(r"leaves octaves (\d+–\d+) bit-identical", "the octaves that alias (:117)"))
    if (LO, HI) == (1, HOCT - 1):
        passed(f"the aliasing octaves {LO}–{HI} are exactly 1..n−1 of a {HOCT}-octave stack")
    else:
        fail(f"the page says octaves {LO}–{HI} alias; a {HOCT}-octave stack's are 1..{HOCT - 1}")
    bad = [l for l in range(LO, HI + 1) if SHIFT % (HPER // HLAC ** l)]
    if bad:
        fail(f"octaves {bad} do not repeat at a {SHIFT}-cell shift; the page says {LO}–{HI} do")
    elif SHIFT % HPER == 0:
        fail(f"octave 0 repeats at {SHIFT} cells too, so the page's '{LO}–{HI}' understates")
    else:
        passed(f"a P-long table repeats every P/lacunarity^l cells, so octaves {LO}–{HI} are "
               f"bit-identical at exactly {SHIFT} cells and octave 0 is not")
    # ⚠️ "divides every octave's repeat and does not divide P" is satisfied by 1536, 2560, ...
    # :116 states the repeat exactly -- P/lacunarity^l cells -- so the SMALLEST shift at which
    # octaves LO..HI are all bit-identical is P/lacunarity^LO. That is the one the page prints.
    check(f"the shift octaves {LO}–{HI} FIRST repeat at, P/lacunarity^{LO} = {HPER}/{HLAC}^{LO} "
          f"(:116's own rule)", float(SHIFT), float(HPER // HLAC ** LO))

    # ── :118's aliasing pair, classified and RUN octave by octave ─────────────────────────
    ALIAS_ERR = pagef(r"at a \d+-cell shift \(([-\d.eE+]+)\) against [-\d.eE+]+ at \d+ entries",
                      "the P-entry table's shift error (:118)")
    LONG_ERR = pagef(r"at a \d+-cell shift \([-\d.eE+]+\) against ([-\d.eE+]+) at \d+ entries",
                     "the long table's shift error (:118)")
    LONG_TS = pagei(r"at a \d+-cell shift \([-\d.eE+]+\) against [-\d.eE+]+ at (\d+) entries",
                    "the long table's length (:118)")
    same("the long table's length, :118 against :121", LONG_TS, ENTRIES_121, ":118", ":121")
    if ALIAS_ERR <= EXACT_MAX:
        passed(f"the P-entry table's {ALIAS_ERR:g} at a {SHIFT}-cell shift is in the EXACT "
               f"population (<= {EXACT_MAX:g}), as ':117 bit-identical' requires")
    else:
        fail(f":117 calls octaves {LO}–{HI} bit-identical at {SHIFT} cells and :118 measures "
             f"{ALIAS_ERR:g} -- that is in the FAILING population (>= {FAIL_MIN:g})")
    if LONG_ERR >= FAIL_MIN:
        passed(f"and a {LONG_TS}-entry table breaks the aliasing: {LONG_ERR:g}, the FAILING "
               f"population -- the two cells are not interchangeable")
    else:
        fail(f":118 measures {LONG_ERR:g} at {LONG_TS} entries; that is in the EXACT population, "
             f"so the long table would alias too and :114-118's whole point is gone")

    tbl_P = table_hash(HPER)                    # the `P`-entry table that fails
    tbl_long = table_hash(ENTRIES_121)          # the finest octave's P*lacunarity^(n-1)

    def octave_shift(tb, l, shift, samples=32):
        """max |g_l(x+shift) − g_l(x)| for octave l alone, and that octave's peak-to-peak.

        ⚠️ Measured in the OCTAVE's OWN lattice coordinates (u = x·lacunarity^l), at u = a +
        OFFSET for a = 0..samples-1, and the domain shift carried across as shift·lacunarity^l.
        Walking the DOMAIN at a fixed stride instead re-aliases: a stride of P/samples cells is
        P·lacunarity^l/samples lattice units, which at octave 5 of this stack is exactly the
        table length, so every sample lands in the same table slot with the same fractional
        part and the field is CONSTANT -- a 0.0 measured over a 0.0 peak-to-peak. Every
        coordinate here is a dyadic rational, so a 0.0 is a true 0.0.
        Fixed bound: samples*samples.
        """
        per = HPER * HLAC ** l
        lshift = shift * HLAC ** l              # the shift, in this octave's lattice units
        worst = 0.0
        lo_v = hi_v = None
        for a in range(samples):
            u = a + OFFSET
            for b in range(samples):
                v = b + OFFSET
                f = noise2(u, v, tb, per)
                d = max(abs(noise2(u + lshift, v, tb, per) - f),
                        abs(noise2(u, v + lshift, tb, per) - f))
                if d > worst:
                    worst = d
                lo_v = f if lo_v is None or f < lo_v else lo_v
                hi_v = f if hi_v is None or f > hi_v else hi_v
        return worst, hi_v - lo_v

    for l in range(0, HI + 1):
        e, pp = octave_shift(tbl_P, l, SHIFT)
        if pp <= 0.0:
            fail(f"octave {l}: the rig's own sample set is degenerate (peak-to-peak 0)")
        elif LO <= l <= HI:
            check(f"octave {l} of the {HOCT}-octave stack, shifted {SHIFT} cells over a "
                  f"{HPER}-entry table (:117 'bit-identical')", e, 0.0)
        elif e >= FULL_AMP * pp:
            passed(f"octave {l} is NOT bit-identical at {SHIFT} cells ({e:.3g} over a {pp:.3g} "
                   f"peak-to-peak), which is why :117 says {LO}–{HI} and not 0–{HI}")
        else:
            fail(f"octave {l} repeats at {SHIFT} cells too ({e:.3g}); :117 says only {LO}–{HI} do")
    for l in range(LO, HI + 1):
        e, pp = octave_shift(tbl_long, l, SHIFT)
        if e >= FULL_AMP * pp:
            passed(f"octave {l} over a {ENTRIES_121}-entry table is NOT bit-identical at "
                   f"{SHIFT} cells: {e:.3g} over a {pp:.3g} peak-to-peak, page {LONG_ERR:g}")
        else:
            fail(f"octave {l} over a {ENTRIES_121}-entry table still repeats at {SHIFT} cells "
                 f"({e:.3g}); :118 says the long table cures it ({LONG_ERR:g})")

    # ── :112-113 and :435 are the SAME measurement printed twice. Cross-read every figure. ─
    A112 = page(r"(With a \d+-entry table a `P` = \d+ tile is a \d+ tile laid \d+×\d+ — "
                r"[-\d.eE+]+\s*\ninside it against [-\d.eE+]+ with a \d+-entry table — while the "
                r"`T = P` wrap test reads [-\d.eE+]+ either\s*\nway, blind to it)",
                "the 4×4 self-repeat measurement (:112-113)", 1, re.S)
    a112 = inner(r"With a (\d+)-entry table a `P` = (\d+) tile is a (\d+) tile laid (\d+)×(\d+) — "
                 r"([-\d.eE+]+)\s+inside it against ([-\d.eE+]+) with a (\d+)-entry table — while "
                 r"the `T = P` wrap test reads ([-\d.eE+]+) either", A112,
                 "the figures of the 4×4 self-repeat measurement (:112-113)", re.S)
    F435 = page(r"(`P` was set to \d+ over a \d+-entry permutation table.*?come out bit-identical "
                r"at a \d+-cell shift)", "the failure table's aliasing mechanism cell (:435)", 1, re.S)
    f435a = inner(r"`P` was set to (\d+) over a (\d+)-entry permutation table", F435,
                  "the failure table's P and table length (:435)")
    f435b = inner(r"the tile is a (\d+) tile laid (\d+)×(\d+); measured "
                  r"`max\\\|f\(x\) − f\(x\+(\d+)\)\\\|` = ([-\d.eE+]+) inside the tile, against "
                  r"([-\d.eE+]+) with a (\d+)-entry table, while the wrap test at `T = P` reads "
                  r"([-\d.eE+]+) either way", F435,
                  "the failure table's restatement of the 4×4 measurement (:435)")
    f435c = inner(r"octaves (\d+)–(\d+) of the (\w+)-octave, lacunarity-(\d+) stack come out "
                  r"bit-identical at a (\d+)-cell shift", F435,
                  "the failure table's restatement of the octave aliasing (:435)")
    same("the tile period P, :117 against :112", HPER, int(a112.group(2)), ":117", ":112")
    same("the tile period P, :117 against the failure table", HPER, int(f435a.group(1)),
         ":117", ":435")
    same("the permutation table's length, :107 against :112", TSIZE, int(a112.group(1)),
         ":107", ":112")
    same("the permutation table's length, :107 against the failure table", TSIZE,
         int(f435a.group(2)), ":107", ":435")
    same("the aliased inner tile, :112 against the failure table", int(a112.group(3)),
         int(f435b.group(1)), ":112", ":435")
    check(f"the inner tile is the permutation table's own length", float(int(a112.group(3))),
          float(TSIZE))
    check(f"the tile is laid P/table = {HPER}/{TSIZE} across", float(HPER // TSIZE),
          float(int(a112.group(4))))
    check(f"and P/table = {HPER}/{TSIZE} down", float(HPER // TSIZE), float(int(a112.group(5))))
    same("the repeat count across, :112 against the failure table", int(a112.group(4)),
         int(f435b.group(2)), ":112", ":435")
    same("the repeat count down, :112 against the failure table", int(a112.group(5)),
         int(f435b.group(3)), ":112", ":435")
    same("the shift the inner repeat is measured at, :435 against the table length :107",
         int(f435b.group(4)), TSIZE, ":435", ":107")
    same("the inner-repeat error, :112 against the failure table", float(a112.group(6)),
         float(f435b.group(5)), ":112", ":435")
    same("the long-table control, :112 against the failure table", float(a112.group(7)),
         float(f435b.group(6)), ":112", ":435")
    same("the control table's length, :112 against the failure table", int(a112.group(8)),
         int(f435b.group(7)), ":112", ":435")
    same("the T = P wrap test, :113 against the failure table", float(a112.group(9)),
         float(f435b.group(8)), ":113", ":435")
    same("the aliasing octaves (lower), :117 against the failure table", LO,
         int(f435c.group(1)), ":117", ":435")
    same("the aliasing octaves (upper), :117 against the failure table", HI,
         int(f435c.group(2)), ":117", ":435")
    same("the stack's octave count, :117 against the failure table", HOCT,
         WORDS[f435c.group(3)], ":117", ":435")
    same("the stack's lacunarity, :117 against the failure table", HLAC, int(f435c.group(4)),
         ":117", ":435")
    same("the aliasing shift, :118 against the failure table", SHIFT, int(f435c.group(5)),
         ":118", ":435")
    check(f"the control table is as long as the tile is wide, P = {HPER}",
          float(int(a112.group(8))), float(HPER))

    INNER_E, CTRL_E, TP_E = (float(a112.group(g)) for g in (6, 7, 9))
    if INNER_E <= EXACT_MAX:
        passed(f"the {TSIZE}-cell self-repeat inside the tile measures {INNER_E:g} -- the EXACT "
               f"population, i.e. the tile really is {a112.group(4)}×{a112.group(5)} copies")
    else:
        fail(f":112 says a P tile over a {TSIZE}-entry table IS a {TSIZE} tile laid "
             f"{a112.group(4)}×{a112.group(5)}, and measures {INNER_E:g} -- not a repeat at all")
    if CTRL_E >= FAIL_MIN:
        passed(f"and with a {HPER}-entry table that same shift measures {CTRL_E:g} -- the "
               f"FAILING population, so the defect is the table's length and nothing else")
    else:
        fail(f":112's {HPER}-entry control measures {CTRL_E:g}, in the EXACT population -- then "
             f"the long table aliases too and the sentence has no control")
    if TP_E <= EXACT_MAX:
        passed(f"the `T = P` wrap test reads {TP_E:g} either way -- EXACT, which is exactly why "
               f":113 calls it blind to the defect")
    else:
        fail(f":113 says the `T = P` wrap test passes either way; {TP_E:g} is a failing wrap")

    e, _ = wrap_error(TSIZE, tbl, HPER)
    check(f"a P = {HPER} tile hashed through a {TSIZE}-entry table repeats every {TSIZE} cells "
          f"INSIDE itself (:112)", e, 0.0)
    e, pp = wrap_error(TSIZE, tbl_P, HPER)
    if pp > 0.0 and e >= FULL_AMP * pp:
        passed(f"and with a {HPER}-entry table it does not: {e:.3g} over a {pp:.3g} peak-to-peak, "
               f"page {CTRL_E:g}")
    else:
        fail(f"a {HPER}-entry table still repeats every {TSIZE} cells here ({e:.3g}); :112 says "
             f"{CTRL_E:g}")
    e_s, _ = wrap_error(HPER, tbl, HPER)
    e_l, _ = wrap_error(HPER, tbl_P, HPER)
    check(f"the `T = P` wrap test over the {TSIZE}-entry table (:113 'either way')", e_s, 0.0)
    check(f"the `T = P` wrap test over the {HPER}-entry table (:113 'either way')", e_l, 0.0)

    # ── E. `P_l = P * frequency_l, MUST be an integer` ─────────────────────────────────────
    head("E. :43 P_l MUST be an integer, against the lacunarity table :161-163")
    NOCT = pagei(r"Measured on a (\d+)-octave fBm with", "the octave count (:158)")
    PBASE = pagei(r"Measured on a \d+-octave fBm with\s*\n`P = (\d+)`", "the period (:159)")
    LACS = [cell(c, "a lacunarity") for c in row(r"^\| lacunarity \|.*$", "the lacunarity row")]
    ERRS = [cell(c, "a wrap error") for c in row(r"^\| max wrap error \|.*$", "the wrap-error row")]
    E = NOCT - pagei(r"the period must be divisible by\s*\n`q\^\(n-(\d+)\)`",
                     "the rule's exponent (:168-169)")
    P1, N1, D1, K1 = (pagei(r"is exact because `(\d+) · \((\d+)/(\d+)\)\^(\d+) = ([\d.]+)`",
                            "the 3/2 identity (:165)", g) for g in (1, 2, 3, 4))
    R1 = pagef(r"is exact because `\d+ · \(\d+/\d+\)\^\d+ = ([\d.]+)`", "its value (:165)")
    p2, q2, k2 = (page(r"because\s*\n`(\d+) · \((\d+)/(\d+)\)\^\d+ = [\d.]+`\. ⚠️",
                       "the 5/4 identity (:166)", g) for g in (1, 2, 3))
    k2b = pagei(r"because\s*\n`\d+ · \(\d+/\d+\)\^(\d+) = [\d.]+`\. ⚠️", "its exponent (:166)")
    R2 = page(r"because\s*\n`\d+ · \(\d+/\d+\)\^\d+ = ([\d.]+)`\. ⚠️", "its value (:166)")
    check(f"{P1} · ({N1}/{D1})^{K1} = {R1:g}",
          float(Fraction(P1) * Fraction(N1, D1) ** K1), R1)
    check(f"{p2} · ({q2}/{k2})^{k2b} = {R2}",
          float(Fraction(int(p2)) * Fraction(int(q2), int(k2)) ** k2b), float(Fraction(R2)))
    if K1 == E and k2b == E:
        passed(f"both worked identities compound to octave {E} = n−1 of {NOCT}")
    else:
        fail(f"the identities use exponents {K1} and {k2b}; the rule's binding octave is {E}")
    ESC_Q, ESC_K, ESC_N = (pagei(r"predicts the escape — `\d+/\d+` needs `(\d+)\^(\d+) = (\d+)`",
                                 "the 5/4 escape (:172)", g) for g in (1, 2, 3))
    ESC_LAC = page(r"predicts the escape — `(\d+/\d+)` needs `\d+\^\d+ = \d+`", "which lacunarity (:172)")
    NEED_LAC = page(r"`(\d+/\d+)` needs (\d+) at (\w+)\s*\noctaves", "the 3/2 escape (:173)")
    NEED_P = pagei(r"`\d+/\d+` needs (\d+) at \w+\s*\noctaves", "what it needs (:173)")
    NEED_OCT = WORDS[page(r"`\d+/\d+` needs \d+ at (\w+)\s*\noctaves", "at how many octaves (:173)")]
    F436 = page(r"(`\d+/\d+` at \w+ octaves needs \d+, so it wraps on any power-of-two period "
                r"\*\*of \d+ or more\*\* and not at \d+, where `\d+·\(\d+/\d+\)\^\d+ = [\d.]+`; "
                r"`\d+/\d+` needs \d+)", "the failure table's escape row (:436)")
    f436 = re.search(r"`(\d+)/(\d+)` at (\w+) octaves needs (\d+), so it wraps on any power-of-two "
                     r"period \*\*of (\d+) or more\*\* and not at (\d+), where "
                     r"`(\d+)·\((\d+)/(\d+)\)\^(\d+) = ([\d.]+)`; `(\d+)/(\d+)` needs (\d+)", F436)
    check(f"{ESC_Q}^{ESC_K} (the escape {ESC_LAC} needs)", float(ESC_Q ** ESC_K), float(ESC_N))
    check(f"q^(n−1) for lacunarity {ESC_LAC} over {NOCT} octaves",
          float(int(ESC_LAC.split('/')[1]) ** E), float(ESC_N))
    check(f"q^(n−1) for lacunarity {NEED_LAC} over {NEED_OCT} octaves",
          float(int(NEED_LAC.split('/')[1]) ** (NEED_OCT - (NOCT - E))), float(NEED_P))
    same("the 3/2 escape, :173 against the failure table", NEED_P, int(f436.group(4)), ":173", ":436")
    same("the 5/4 escape, :172 against the failure table", ESC_N, int(f436.group(14)), ":172", ":436")
    same("the octave count, :173 against the failure table",
         NEED_OCT, WORDS[f436.group(3)], ":173", ":436")
    check(f"{f436.group(7)}·({f436.group(8)}/{f436.group(9)})^{f436.group(10)} "
          f"= {f436.group(11)} (:436, why 16 is too short)",
          float(Fraction(int(f436.group(7))) * Fraction(int(f436.group(8)), int(f436.group(9)))
                ** int(f436.group(10))), float(Fraction(f436.group(11))))

    M436 = page(r"(`period × lacunarity\^k` stopped being an integer at some octave; measured "
                r"[-\d.eE+]+ at lacunarity [\d.]+ with period \d+)",
                "the failure table's lacunarity mechanism cell (:436)")
    m436 = inner(r"measured ([-\d.eE+]+) at lacunarity ([\d.]+) with period (\d+)", M436,
                 "the figures of the failure table's lacunarity mechanism (:436)")
    same("the fBm's period, :159 against the failure table", PBASE, int(m436.group(3)),
         ":159", ":436")
    if float(m436.group(2)) in LACS:
        passed(f"the failure table's lacunarity {m436.group(2)} is a column of the table "
               f":161 measures ({[f'{x:g}' for x in LACS]})")
        same(f"the wrap error at lacunarity {m436.group(2)}, :163 against the failure table",
             ERRS[LACS.index(float(m436.group(2)))], float(m436.group(1)), ":163", ":436")
    else:
        fail(f"the failure table measures lacunarity {m436.group(2)}; :161's columns are "
             f"{[f'{x:g}' for x in LACS]} -- the two ends no longer measure the same thing")

    for lac, want in zip(LACS, ERRS):
        if not (want <= EXACT_MAX or want >= FAIL_MIN):
            fail(f"lacunarity {lac:g}: the page's {want:g} falls between this rig's two "
                 f"populations ({EXACT_MAX:g} .. {FAIL_MIN:g}) and states neither")
            continue
        got, pp = fbm_wrap_error(PBASE, lac, NOCT)
        if pp <= 0.0:
            fail(f"lacunarity {lac:g}: the rig's own sample set is degenerate (peak-to-peak 0)")
            continue
        page_exact = want <= EXACT_MAX
        rig_exact = got <= EXACT_MAX
        if page_exact == rig_exact and (rig_exact or got >= FAIL_MIN):
            passed(f"lacunarity {lac:<5g} {'wraps' if rig_exact else 'SEAMS'}: rig {got:.3g}, "
                   f"page {want:.3g}")
        else:
            fail(f"lacunarity {lac:<5g}: rig {got:.3g}, page {want:.3g} -- the page says it "
                 f"{'wraps' if page_exact else 'seams'} and it does not")
    PRED = page(r"integrality of every octave for lacunarity ([^:]+?) at `T = (\d+)`",
                "the seven lacunarities the rule was checked against (:170-171)")
    PRED_T = pagei(r"integrality of every octave for lacunarity [^:]+? at `T = (\d+)`",
                   "the period they were checked at (:171)", 1)
    fr = [(int(a), int(b or 1)) for a, b in re.findall(r"(\d+)(?:/(\d+))?", PRED)]
    # ⚠️ `PRED_T % den**E` and `fbm_wrap_error(PRED_T, ...)` are the same arithmetic on the
    # same two parsed numbers, so "the condition predicts the outcome" is green at ANY T the
    # page cares to print -- 63, 97, 2048. T is therefore pinned to the period the fBm this
    # rule was checked against actually ran at (:159, restated at :436), and the rule is then
    # re-derived a second way, from the integrality of each octave's P·lacunarity^k over exact
    # rationals, which is the check :170 says was performed.
    same("the period the rule was checked at, :171 against the fBm's own period :159",
         PRED_T, PBASE, ":171", ":159")
    for num, den in fr:
        rule = PRED_T % (den ** E) == 0
        octs = [Fraction(PRED_T) * Fraction(num, den) ** k for k in range(NOCT)]
        integral = all(o.denominator == 1 for o in octs)
        if rule != integral:
            fail(f"lacunarity {num}/{den}: q^(n−1) = {den}^{E} "
                 f"{'divides' if rule else 'does not divide'} {PRED_T}, but the octave periods "
                 f"{[str(o) for o in octs]} are {'all' if integral else 'not all'} integers -- "
                 f":170's 'checked against the integrality of every octave' does not hold")
            continue
        got, pp = fbm_wrap_error(PRED_T, num / den, NOCT)
        if pp <= 0.0:
            fail(f"lacunarity {num}/{den}: the rig's own sample set is degenerate")
            continue
        seen = got <= EXACT_MAX
        if rule == seen:
            passed(f"lacunarity {num}/{den}: q^(n−1) = {den}^{E} "
                   f"{'divides' if rule else 'does not divide'} {PRED_T}, and the rig "
                   f"{'wraps' if seen else 'seams'} ({got:.3g}) -- the condition predicts it")
        else:
            fail(f"lacunarity {num}/{den}: the rule predicts {'exact' if rule else 'a seam'}, "
                 f"the rig measures {got:.3g} -- 'the condition predicts the outcome in every "
                 f"case' does not hold")

    # :172-173 name three MORE periods, independently of :171's T: 5/4 escapes at q^(n−1) =
    # 1024, 3/2 escapes at 32 over six octaves, and :436 says 3/2 does NOT escape at 16. Run
    # all three. A T walked at :171 now contradicts a T fixed here.
    for lacstr, per, oct_n, want_exact, at in (
            (ESC_LAC, ESC_N, NOCT, True, ":172"),
            (NEED_LAC, NEED_P, NEED_OCT, True, ":173"),
            (NEED_LAC, int(f436.group(6)), NEED_OCT, False, ":436")):
        n_, d_ = (int(x) for x in lacstr.split("/"))
        got, pp = fbm_wrap_error(per, n_ / d_, oct_n)
        if pp <= 0.0:
            fail(f"lacunarity {lacstr} at P = {per}: degenerate sample set (peak-to-peak 0)")
            continue
        seen = got <= EXACT_MAX
        if seen == want_exact:
            passed(f"{at}: a {oct_n}-octave fBm at lacunarity {lacstr} and period {per} "
                   f"{'WRAPS' if seen else 'SEAMS'} ({got:.3g}), as the page says -- and "
                   f"{d_}^{oct_n - 1} = {d_ ** (oct_n - 1)} "
                   f"{'divides' if per % d_ ** (oct_n - 1) == 0 else 'does not divide'} {per}")
        else:
            fail(f"{at}: a {oct_n}-octave fBm at lacunarity {lacstr} and period {per} measures "
                 f"{got:.3g}; the page says it "
                 f"{'wraps exactly' if want_exact else 'does not wrap'}")

    # ── F. `sim: neighbour(i, j) = grid[(i + di) mod H, (j + dj) mod W]` ───────────────────
    head("F. :44 the wrapping neighbour lookup, and what it exports")
    SIDE_E = pagei(r"A (\d+)² field is built by the modular construction", "the erosion grid (:198)")
    DHDR = ints(" ".join(row(r"^\| boundary \| \d+ steps \|.*$", "the depth table's header (:228)")))
    DEPTHS = [int(cell(c, "a depth")) for c in
              row(r"^\| closed \*\*and\*\* open, depth where error > 0\.1% \(both measured the "
                  r"same\) \|.*$", "the 0.1%-error depth row (:231)")]
    D440 = ints(page(r"not of a kernel radius: ([\d ,→]+?) cells at [\d ,→]+ steps",
                     "the failure table's crop depths (:440)"))
    S440 = ints(page(r"not of a kernel radius: [\d ,→]+ cells at ([\d ,→]+?) steps",
                     "the failure table's crop step counts (:440)"))
    _C66 = r"the crop grows with simulated time: (\d+) cells at (\d+)\s*\nsteps, (\d+) at (\d+),"
    D66 = [pagei(_C66, "the shallowest crop in the headline (:66)", 1),
           pagei(_C66, "the deepest crop in the headline (:67)", 3)]
    S66 = [pagei(_C66, "its first step count (:66)", 2),
           pagei(_C66, "its last step count (:67)", 4)]
    STEPS = ints(page(r"^\| torus \| ([\d /]+) \|", "the torus row's step counts (:207)", 1, re.M))
    T_EXPORT = cell(row(r"^\| torus \|.*$", "the torus row")[4], "the torus export")
    C_EXPORT = cell(row(r"^\| closed \|.*$", "the closed row")[4], "the closed export")
    O_EXPORT = cell(row(r"^\| open \|.*$", "the open row")[4], "the open export")
    T_DRIFT = cell(row(r"^\| torus \|.*$", "the torus row")[3], "the torus mass drift")
    E51 = pagef(r"Toroidal erosion conserves mass to `([-\d.eE+]+)` and exports \*\*([\d.]+)%\*\*",
                "the headline's toroidal drift (:51)")
    E51X = pagef(r"conserves mass to `[-\d.eE+]+` and exports \*\*([\d.]+)%\*\*",
                 "the headline's toroidal export (:51)")
    E52 = pagef(r"export ([\d.]+)% of the terrain and flatten the seam", "the headline's open export (:52)")
    E439 = pagef(r"and ([\d.]+)% of terrain mass exported", "the failure table's open export (:439)")
    same("toroidal export, :51 against the table", E51X, T_EXPORT, ":51", ":207")
    same("toroidal mass drift, :51 against the table", E51, T_DRIFT, ":51", ":207")
    _R241 = (r"Measured: `exported =\s*\n([\d.]+)%` and mass drift `([-\d.eE+]+)` over (\d+) steps")
    same("toroidal export, :207 against §A torus has no outlet", T_EXPORT,
         pagef(_R241, "the toroidal export restated (:240)", 1), ":207", ":240")
    same("toroidal mass drift, :207 against §A torus has no outlet", T_DRIFT,
         pagef(_R241, "the toroidal drift restated (:241)", 2), ":207", ":241")
    same("the step count that drift is measured over, :207 against :241", STEPS[-1],
         pagei(_R241, "the step count it is measured over (:241)", 3), ":207", ":241")
    same("open export, :52 against the failure table", E52, E439, ":52", ":439")
    check("open export, the headline's 2 dp against the table's 3", round(O_EXPORT, 2), E52)
    if T_DRIFT <= MACHINE_MAX:
        passed(f"the page's toroidal drift {T_DRIFT:g} is {T_DRIFT / MACHINE_ULP:.2f} ulp of a "
               f"unit-scale sum -- machine precision, as :212 claims (this rig cannot reproduce "
               f"another solver's summation order, only the scale of its residue)")
    else:
        fail(f":212 calls the toroidal drift 'machine precision' and :207 prints {T_DRIFT:g} -- "
             f"{T_DRIFT / MACHINE_ULP:.0f} ulp, past this rig's {MACHINE_MAX:g} ceiling; a "
             f"drift that large is a solver residue, not a rounding")
    if len(D440) == len(DEPTHS) and all(a == b for a, b in zip(D440, DEPTHS)):
        passed(f"the crop depths, :231 against the failure table: both say {DEPTHS} cells")
    else:
        fail(f"the crop depths disagree: :231 says {DEPTHS}, :440 says {D440}")
    if len(S440) == len(DHDR) == len(STEPS) and all(a == b == c for a, b, c
                                                    in zip(S440, DHDR, STEPS)):
        passed(f"the step counts, :207 against :228 against the failure table: all {STEPS}")
    else:
        fail(f"the step counts disagree: :207 {STEPS}, :228 {DHDR}, :440 {S440}")
    if [D66[0], D66[-1]] == [DEPTHS[0], DEPTHS[-1]] and [S66[0], S66[-1]] == [STEPS[0], STEPS[-1]]:
        passed(f"the headline's '{D66[0]} cells at {S66[0]} steps, {D66[-1]} at {S66[-1]}' is "
               f"the depth table's own first and last columns")
    else:
        fail(f":66-67 says {D66} cells at {S66} steps; the table says {DEPTHS} at {STEPS}")
    # ⚠️ :198's grid is BOTH the size under test and this rig's own grid, so shrinking it on
    # the page silently re-points the rig. It is pinned here to the page's OTHER measurement of
    # the same run: at the deepest step count the wrong boundary reaches DEEPEST cells in from
    # every edge (:231), so only (side − 2·DEEPEST)² cells are undamaged interior. :201 divides
    # every ratio in :204-209 by a mean over "interior neighbours"; require that undamaged
    # interior to be at least half the domain, or the denominator is itself boundary-damaged
    # and the table does not measure what :201 says it measures.
    DEEPEST = max(DEPTHS)
    core = (SIDE_E - 2 * DEEPEST) ** 2
    if core * 2 >= SIDE_E * SIDE_E:
        passed(f"{SIDE_E}² leaves {core} of {SIDE_E * SIDE_E} cells more than {DEEPEST} cells "
               f"(:231, at {STEPS[-1]} steps) from an edge -- the interior :201 divides by is "
               f"{100.0 * core / (SIDE_E * SIDE_E):.0f}% of the domain")
    else:
        fail(f":198 measures on {SIDE_E}², and :231 says the wrong boundary reaches "
             f"{DEEPEST} cells in from every edge at {STEPS[-1]} steps -- that leaves only "
             f"{core} of {SIDE_E * SIDE_E} cells undamaged, under half, so :201's 'mean "
             f"absolute step between interior neighbours' has no interior to average over")

    tiles = {}
    for name in ("closed", "open", "looped / toroidal"):
        r = row(rf"^\| \*\*{re.escape(name)}\*\*.*$", f"the {name} row of the boundary table (:186-190)")
        tiles[name] = (r[0], r[1], r[2])
    # :219-220 states the rule the mass column has to obey: "`closed`'s 'conserved' claim rests
    # on `exported = 0.000%`, not that column". So the mass column is the export column, in
    # words -- and a row that exports is a row that does not conserve.
    for name, exp, at in (("closed", C_EXPORT, ":208"), ("open", O_EXPORT, ":209"),
                          ("looped / toroidal", T_EXPORT, ":207")):
        want = "exported" if exp > 0.0 else "conserved"
        got_mass = tiles[name][1]
        if got_mass == want:
            passed(f"the boundary table calls {name!r} mass {got_mass!r}, and {at} measures "
                   f"{exp:g}% exported -- :219-220's rule")
        else:
            fail(f"the boundary table calls {name!r} mass {got_mass!r} while {at} measures "
                 f"{exp:g}% of the terrain exported")
    if re.search(r"grid\[\(i\+di\) % H, \(j\+dj\) % W\]", tiles["looped / toroidal"][0]):
        passed("the boundary table's looped row carries the fence's own neighbour expression")
    else:
        fail(f"the looped row's line is {tiles['looped / toroidal'][0]!r}, not the fence's "
             f"`grid[(i+di) % H, (j+dj) % W]`")
    yes = [k for k, v in tiles.items() if v[2] == "yes"]
    if yes == ["looped / toroidal"]:
        passed("exactly one of the three boundaries tiles, and it is the looped one")
    else:
        fail(f"the boundary table says these tile: {yes}")

    # the structural proof, at tolerance ZERO
    H = W = SIDE_E
    offsets = 4
    bad = 0
    for c in range(H * W):
        nbs = neighbours4(c, H, W, True)
        bad += sum(1 for n in nbs if not 0 <= n < H * W)
        for d, n in enumerate(nbs):
            if neighbours4(n, H, W, True)[d ^ 1] != c:
                bad += 1
    if bad == 0:
        passed(f"on {H}×{W}, every one of {H * W * offsets} toroidal lookups is in-grid and "
               f"pairs with its opposite -- no edge case exists for a solver to treat specially")
    else:
        fail(f"{bad} of {H * W * offsets} toroidal lookups are off-grid or unpaired")
    indeg = [0] * (H * W)
    for c in range(H * W):
        for n in neighbours4(c, H, W, True):
            indeg[n] += 1
    if set(indeg) == {offsets}:
        passed(f"every cell has exactly {offsets} in-neighbours, so any antisymmetric flux sums "
               f"to zero over the domain -- nothing can leave")
    else:
        fail(f"in-degrees on the torus are {sorted(set(indeg))}, not {{{offsets}}}")

    for torus, want in ((True, T_EXPORT), (False, O_EXPORT)):
        h = [0.5 + 0.5 * ((_mix32(c * 2654435761) & 0xFFFF) / 65535.0) for c in range(H * W)]
        mass0 = sum(h)
        exported = 0.0
        worst_step = 0.0
        for _ in range(12):                    # fixed bound; export is a PER-STEP invariant
            nh = list(h)
            out = 0.0
            for c in range(H * W):
                share = 0.05 * h[c]
                for n in neighbours4(c, H, W, torus):
                    nh[c] -= share
                    if n >= 0:
                        nh[n] += share
                    else:
                        out += share            # the open rule: it leaves at base level
            h = nh
            exported += out
            worst_step = max(worst_step, out)
        pct = 100.0 * exported / mass0
        drift = abs(sum(h) + exported - mass0) / mass0
        if torus:
            check(f"toroidal export over 12 steps of the fence's own lookup, % of mass",
                  pct, want)
            # the rig's OWN residue is a naive sum of H*W terms, so its closed-form worst
            # case is H*W ulp -- not MACHINE_MAX, which bounds the page's single printed
            # figure. Using the page's ceiling here would gate this rig's summation order.
            own_max = H * W * MACHINE_ULP
            if drift <= own_max:
                passed(f"and the rig's own mass drift is {drift:.3g} = {drift / MACHINE_ULP:.1f} "
                       f"ulp, inside the {H * W} ulp a naive sum of {H * W} terms can reach; "
                       f"the page's column is {T_DRIFT:g}")
            else:
                fail(f"the rig's toroidal mass drift is {drift:.3g}, past the {own_max:.3g} a "
                     f"sum of {H * W} float64 terms can accumulate -- mass is leaving a torus")
        elif pct > 0 and want > 0:
            passed(f"open edges export {pct:.3f}% here against the page's {want:g}% -- the "
                   f"magnitude is that solver's, the sign is the claim")
        else:
            fail(f"open edges exported {pct:.3f}% here and the page says {want:g}%")
    check("the closed boundary exports nothing either (its 'conserved' rests on this column)",
          0.0, C_EXPORT)

    # ── the seam-ratio column, cross-read at every end that restates it ───────────────────
    SEED_SEAM = cell(row(r"^\| \*seed\* \|.*$", "the seed row (:206)")[1], "the seed seam ratio")
    C_SEAM = cell(row(r"^\| closed \|.*$", "the closed row")[1].split("/")[-1],
                  "the closed seam ratio at the deepest step count")
    O_SEAM = cell(row(r"^\| open \|.*$", "the open row")[1].split("/")[-1],
                  "the open seam ratio at the deepest step count")
    SEAM199 = pagef(r"so it wraps bit-exactly before erosion starts \(seam ratio ([\d.]+) —",
                    "the seed seam ratio in prose (:199)")
    NEUTRAL = pagef(r"absolute step between interior neighbours; ([\d.]+) means the seam is",
                    "the seam ratio that means 'indistinguishable' (:202)")
    _R215 = (r"The wrapped step goes from ([\d.]+) of an interior step to\s*\n\s*([\d.]+) — a "
             r"(\d+)% relative rise — and the outer four cells drift ([\d.]+)% of relief")
    FROM215 = pagef(_R215, "the seam ratio it rises from (:215)", 1)
    TO215 = pagef(_R215, "the seam ratio it rises to (:216)", 2)
    RISE215 = pagei(_R215, "the relative rise (:216)", 3)
    RIM216 = pagef(_R215, "the rim drift (:216)", 4)
    f438 = inner(r"measured seam ratio ([\d.]+) and rim drift ([\d.]+)% of relief",
                 page(r"(measured seam ratio [\d.]+ and rim drift [\d.]+% of relief)",
                      "the failure table's closed-boundary row (:438)"),
                 "the figures of the failure table's closed-boundary row (:438)")
    S221 = pagef(r"\*\*Open planes the seam flat\.\*\* ([\d.]+) means the seam is",
                 "the open seam ratio in prose (:221)")
    f439 = inner(r"measured seam ratio ([\d.]+) against an interior of ([\d.]+)",
                 page(r"(measured seam ratio [\d.]+ against an interior of [\d.]+)",
                      "the failure table's open-boundary row (:439)"),
                 "the figures of the failure table's open-boundary row (:439)")
    S52 = pagef(r"flatten the seam to ([\d.]+)× the interior roughness",
                "the headline's open seam ratio (:52)")
    same("the seed seam ratio, :199 against the table", SEAM199, SEED_SEAM, ":199", ":206")
    same("the seam ratio it rises from, :215 against the table", FROM215, SEED_SEAM, ":215", ":206")
    same("the closed seam ratio, :216 against the table", TO215, C_SEAM, ":216", ":208")
    same("the closed seam ratio, :208 against the failure table", C_SEAM, float(f438.group(1)),
         ":208", ":438")
    same("the closed rim drift, :216 against the failure table", RIM216, float(f438.group(2)),
         ":216", ":438")
    check(f"the {RISE215}% relative rise, from the table's own two seam ratios "
          f"({C_SEAM:g} over {SEED_SEAM:g})",
          round(100.0 * (C_SEAM / SEED_SEAM - 1.0)), float(RISE215))
    same("the open seam ratio, :221 against the table", S221, O_SEAM, ":221", ":209")
    same("the open seam ratio, :209 against the failure table", O_SEAM, float(f439.group(1)),
         ":209", ":439")
    same("'an interior of 1.0', :439 against the seam ratio's own definition",
         float(f439.group(2)), NEUTRAL, ":439", ":202")
    # :54's 221× for a 221.5 cell is the recorded truncate-or-round defect; :52's 0.39× for
    # 0.389 is the identical relation, gated the identical way. The band is ONE HUNDREDTH,
    # fixed here in the rig with its reason -- a quote of a ratio may truncate or round at the
    # hundredth and this corpus has a recorded defect for exactly that -- and NOT read off how
    # many digits :52 chooses to print, so the page cannot widen it by printing fewer.
    if math.floor(O_SEAM * 100.0) / 100.0 <= S52 <= math.ceil(O_SEAM * 100.0) / 100.0:
        passed(f"the headline's {S52:g}× is the table's {O_SEAM:g} "
               f"{'truncated' if S52 == math.floor(O_SEAM * 100.0) / 100.0 else 'rounded'} "
               f"to 2 dp (:52 against :209)")
    else:
        fail(f":52 says the open boundary flattens the seam to {S52:g}× and :209 measures "
             f"{O_SEAM:g}")
    if O_SEAM < NEUTRAL < C_SEAM:
        passed(f"open planes the seam below {NEUTRAL:g} ({O_SEAM:g}) and closed opens it above "
               f"({C_SEAM:g}) -- :215 and :221's two directions, from the table's own cells")
    else:
        fail(f":215 says closed opens the seam upward and :221 says open planes it flat; the "
             f"table reads closed {C_SEAM:g}, open {O_SEAM:g}, neutral {NEUTRAL:g}")

    # ── how much mass an OPEN edge can take, bounded by the page's own depth table ────────
    # :231: at the deepest step count the open boundary's field differs from the torus's by
    # more than 0.1% of relief only within DEEPEST cells of an edge, and the torus exports
    # nothing (:207). So the mass that left came out of that rim, and the rim is
    # 1 − ((side − 2·DEEPEST)/side)² of a side² domain by area. This is an upper bound with a
    # factor of sixteen of headroom on the page's own 2.184%, not a band around it.
    rim_pct = 100.0 * (1.0 - ((SIDE_E - 2 * DEEPEST) / SIDE_E) ** 2)
    if 0.0 < O_EXPORT <= rim_pct:
        passed(f"the open boundary exports {O_EXPORT:g}% of the terrain, inside the "
               f"{rim_pct:.1f}% that lies within {DEEPEST} cells of an edge on {SIDE_E}² "
               f"(:231) -- mass from deeper in would have moved the interior by more than the "
               f"0.1% of relief :231 measures")
    else:
        fail(f":209 exports {O_EXPORT:g}% of the terrain, but :231 says the open boundary only "
             f"reaches {DEEPEST} cells in, which is {rim_pct:.1f}% of a {SIDE_E}² domain -- the "
             f"two measurements of the same run contradict each other")

    # ── G. `route: priority_flood(seeds = [the one authored sink])` ────────────────────────
    head("G. :45 priority-flood on a torus, against the table :256-260")
    SIDE = pagei(r"(\d+)² = \d+ cells:", "the flow grid's side (:254)")
    CELLS = pagei(r"\d+² = (\d+) cells:", "the flow grid's cell count (:254)")
    PLANE = row(r"^\| plane, open edges \|.*$", "the open-plane row (:258)")
    SINK = row(r"^\| torus, one authored sink \|.*$", "the one-sink row (:259)")
    NOSINK = row(r"^\| torus, no sink \|.*$", "the no-sink row (:260)")
    OUTLETS = pagei(r"plane's (\d+) edge outlets", "the plane's outlet count (:54)")
    ACC53 = pagef(r"drains \*\*([\d.]+)%\*\* of the domain through it, against ([\d.]+)%",
                  "the headline's toroidal catchment (:53)")
    ACC53B = pagef(r"drains \*\*[\d.]+%\*\* of the domain through it, against ([\d.]+)%",
                   "the headline's plane catchment (:53)")
    ACC442 = pagef(r"max accumulation is ([\d.]+)% of the domain by construction",
                   "the failure table's catchment (:442)")
    REACH441 = pagei(r"a torus has none; measured (\d+) cells reached",
                     "the failure table's no-sink reach (:441)")
    FILL280, RAISE280 = (pagei(r"Fill volume rises (\d+)% and (\d+)% more cells are raised",
                               "the one-sink cost (:280)", g) for g in (1, 2))
    FILL442, RAISE442 = (pagei(r"measured fill volume \+(\d+)% and cells raised \+(\d+)%",
                               "the failure table's one-sink cost (:442)", g) for g in (1, 2))
    check(f"{SIDE}² = {CELLS} (the page's own product)", float(SIDE * SIDE), float(CELLS))
    same("the plane's outlet count, :54 against the table", OUTLETS, cell(PLANE[0], "seeds"),
         ":54", ":258")
    same("toroidal catchment, :53 against the table", ACC53,
         cell(SINK[4].split("=")[1], "the % cell"), ":53", ":259")
    same("toroidal catchment, :53 against the failure table", ACC53, ACC442, ":53", ":442")
    same("plane catchment, :53 against the table", ACC53B,
         cell(PLANE[4].split("=")[1], "the % cell"), ":53", ":258")
    _R278 = (r"With (\d+) outlets sharing the load the largest catchment is (\d+)%\s*\nof the "
             r"domain; with one, it is (\d+)% by definition")
    OUT278 = pagei(_R278, "the plane's outlet count (:278)", 1)
    ACC278 = pagei(_R278, "the plane's largest catchment, to the whole percent (:278)", 2)
    ONE278 = pagei(_R278, "the torus's catchment, to the whole percent (:279)", 3)
    same("the plane's outlet count, :54 against :278", OUTLETS, OUT278, ":54", ":278")
    # ⚠️ count-against-percent alone is one division: move the count and the percent together
    # and it stays green. :278 prints the same catchment a second time, to the whole percent.
    check(f"the plane's largest catchment at :258 ({ACC53B:g}%), to the whole percent as :278 "
          f"prints it", round(ACC53B), float(ACC278))
    check(f"the torus's catchment at :259 ({ACC53:g}%), to the whole percent as :279 prints it",
          round(ACC53), float(ONE278))
    PLANE_CNT = cell(PLANE[4].split("=")[0], "the plane's accumulation count")
    SINK_CNT = cell(SINK[4].split("=")[0], "the torus's accumulation count")
    check("the plane's largest catchment, count against percent (:258)",
          round(100.0 * PLANE_CNT / CELLS, 2), ACC53B)
    if 0 < PLANE_CNT < CELLS:
        passed(f"the plane's largest catchment is {PLANE_CNT:g} of {CELLS} cells -- a strict "
               f"fraction, because {OUT278} outlets share the load (:278)")
    else:
        fail(f":258 gives the plane's largest catchment as {PLANE_CNT:g} of {CELLS} cells, and "
             f":278 says {OUT278} outlets SHARE the load")
    check("the torus's catchment, count against percent (:259)",
          round(100.0 * cell(SINK[4].split("=")[0], "the count") / CELLS, 2), ACC53)
    same("fill volume rise, :280 against the failure table", FILL280, FILL442, ":280", ":442")
    same("cells raised rise, :280 against the failure table", RAISE280, RAISE442, ":280", ":442")
    check("fill volume rise, from the table's own two volumes (:258-259)",
          round(100.0 * (cell(SINK[3], "fill") / cell(PLANE[3], "fill") - 1.0)), float(FILL280))
    check("cells raised rise, from the table's own two counts (:258-259)",
          round(100.0 * (cell(SINK[2], "raised") / cell(PLANE[2], "raised") - 1.0)), float(RAISE280))

    fld = [((_mix32(c * 40503) & 0xFFFF) / 65535.0) for c in range(SIDE * SIDE)]
    edge = [c for c in range(SIDE * SIDE)
            if c // SIDE in (0, SIDE - 1) or c % SIDE in (0, SIDE - 1)]
    check(f"a {SIDE}² plane's edge cells, counted", float(len(edge)), cell(PLANE[0], "seeds"))
    filled_p, reached, _ = priority_flood(fld, SIDE, edge, torus=False)
    check("plane, open edges: cells reached", float(reached), cell(PLANE[1], "cells reached"))
    acc_p = d8_accumulation(filled_p, SIDE, torus=False)
    one = [SIDE * SIDE // 2 + SIDE // 3]
    fld_s = list(fld)
    fld_s[one[0]] = -1.0                        # [barnes2014] §3.2: a pinned low cell is a seed
    check("torus, one authored sink: seeds", float(len(one)), cell(SINK[0], "seeds"))
    filled, reached, _ = priority_flood(fld_s, SIDE, one, torus=True)
    check("torus, one authored sink: cells reached", float(reached), cell(SINK[1], "cells reached"))
    acc = d8_accumulation(filled, SIDE, torus=True)
    check("torus, one authored sink: max accumulation, in cells", float(acc), SINK_CNT)
    check("torus, one authored sink: max accumulation, as % of domain",
          round(100.0 * acc / CELLS, 2), ACC53)
    # the same routing, run on the PLANE's filled field -- the arm :258's 2803 comes from and
    # the one the rig used to skip. The count is that field's, so what is gated is :278-279's
    # own contrast: many outlets share, one takes everything.
    if 0 < acc_p < acc == CELLS:
        passed(f"plane, {len(edge)} open edge outlets: largest catchment {acc_p} of {CELLS} "
               f"cells ({100.0 * acc_p / CELLS:.2f}%), strictly inside the torus's {acc} = "
               f"{ACC53:g}% -- :278's '{ACC278}% ... with one, it is {ONE278}% by definition' "
               f"(the page's {PLANE_CNT:g} is its own field's)")
    else:
        fail(f"plane: largest catchment {acc_p} of {CELLS}, torus: {acc} -- :278-279 says the "
             f"plane's {OUT278} outlets share the domain and the torus's one sink takes all "
             f"{ONE278}% of it")
    _, reached, _ = priority_flood(fld, SIDE, [], torus=True)
    check("torus, no sink: cells reached (the queue starts empty)",
          float(reached), cell(NOSINK[1], "cells reached"))
    same("the no-sink reach, the table against the failure table",
         cell(NOSINK[1], "cells reached"), REACH441, ":260", ":441")

    # ── H. `filter: every convolution pads with wrap, never reflect` ───────────────────────
    head("H. :46 wrap, never reflect, against the padding table :378-384")
    NPYR = pagei(r"`m6_pyramid_padding\.py`[^\n]*?, (\d+)², `a = [\d.]+`", "the pyramid grid (:375)")
    A = pagef(r", (?:\d+)², `a = ([\d.]+)`, input seam-to-interior", "the generating kernel's a (:375)")
    IN_RATIO = pagef(r"input seam-to-interior step\s*\nratio ([\d.]+):",
                     "the pyramid input's own seam ratio (:375-376)")
    LVLS = ints(" ".join(row(r"^\| padding \| L = .*$", "the padding table header")[:-1]))
    WRAPR = row(r"^\| `wrap` \|.*$", "the wrap row (:380)")
    REFR = row(r"^\| `reflect` \|.*$", "the reflect row (:381)")
    RT = [cell(row(rf"^\| {re.escape(m)} \|.*$", f"the {m} row")[-1], "a round-trip cell")
          for m in ("`wrap`", "`reflect`", "`symmetric`", "`edge`", "`constant` (zero)")]
    if len(set(RT)) == 1:
        passed(f"every padding mode's round trip is the same {RT[0]:g} -- the page's point: "
               f"`lo + hi = h` holds by construction and CANNOT see a padding defect")
    else:
        fail(f"the round-trip column is not uniform: {RT} -- the page says it holds for every mode")
    # ⚠️ uniform-and-equal-to-:443 is satisfied by a column of 1.1e+03. :387-388's claim is
    # `lo + hi = h` HOLDS TO MACHINE PRECISION for every mode, so each cell has to be one.
    for m, v in zip(("`wrap`", "`reflect`", "`symmetric`", "`edge`", "`constant` (zero)"), RT):
        if v <= MACHINE_MAX:
            passed(f"{m:<18s} round trip {v:g} = {v / MACHINE_ULP:.2f} ulp -- machine "
                   f"precision, as :387-388 claims for every mode")
        else:
            fail(f"{m} round trip {v:g} = {v / MACHINE_ULP:.0f} ulp; :387-388 says `lo + hi = h` "
                 f"holds to machine precision for every mode, and that is a residue, not one")
    ALLROWS = {m: [cell(c, f"a {m} cell") for c in
                   row(rf"^\| {re.escape(m)} \|.*$", f"the {m} row")[:-1]]
               for m in ("`wrap`", "`reflect`", "`symmetric`", "`edge`", "`constant` (zero)")}
    for i, L in enumerate(LVLS):
        col = {m: v[i] for m, v in ALLROWS.items()}
        best = min(col, key=lambda m: col[m])
        if best == "`wrap`":
            passed(f"L = {L}: `wrap` has the smallest seam of the {len(col)} modes "
                   f"({col['`wrap`']:g}), as ':386 only wrap keeps the seam in the same "
                   f"population' requires")
        else:
            fail(f"L = {L}: the smallest seam is {best}'s {col[best]:g}, not `wrap`'s "
                 f"{col['`wrap`']:g} -- the fence says wrap")
    for i, L in enumerate(LVLS):
        w = ALLROWS["`wrap`"][i]
        if w <= IN_RATIO:
            passed(f"L = {L}: `wrap` leaves the seam at {w:g}, no worse than the {IN_RATIO:g} "
                   f"the input already had (:375) -- ':386 only `wrap` keeps the seam in the "
                   f"same population as the terrain'")
        else:
            fail(f"L = {L}: `wrap` padding raises the seam from the input's {IN_RATIO:g} to "
                 f"{w:g} -- then :386's 'only `wrap` keeps the seam in the same population as "
                 f"the terrain' is false and the fence's filter line has no basis")
    DEEP = max(LVLS)
    for m, v in ALLROWS.items():
        if m == "`wrap`":
            continue
        if v[LVLS.index(DEEP)] > IN_RATIO:
            passed(f"L = {DEEP}: {m} raises the seam from the input's {IN_RATIO:g} to "
                   f"{v[LVLS.index(DEEP)]:g}, out of the terrain's population")
        else:
            fail(f"L = {DEEP}: {m} leaves the seam at {v[LVLS.index(DEEP)]:g}, no worse than "
                 f"the input's {IN_RATIO:g} -- :386 says only `wrap` does that")
    # ⚠️ :375's grid is BOTH the size under test and this rig's own grid. Pin it to the page's
    # own two statements about how deep a split this table runs: :393's halo for the deepest
    # level, and :394-395's N ≡ 0 (mod 2^L). A domain shorter than the halo a level-L split
    # reaches wraps its own padding round more than once, and the table's L column is then not
    # a band split of that field at all.
    HALO_A, HALO_B = (pagei(r"band split needs `halo ≥ (\d+)·2\^L − (\d+)`",
                            "the tiled split's halo rule (:393)", g) for g in (1, 2))
    need = HALO_A * 2 ** DEEP - HALO_B
    if NPYR > need:
        passed(f"{NPYR}² is wider than the halo a level-{DEEP} split reaches, "
               f"{HALO_A}·2^{DEEP} − {HALO_B} = {need} (:393)")
    else:
        fail(f":375 measures on {NPYR}² and tabulates L = {DEEP}, whose halo is "
             f"{HALO_A}·2^{DEEP} − {HALO_B} = {need} cells (:393) -- the padding wraps the "
             f"domain more than once and the L = {DEEP} column is not a band split of it")
    if NPYR % 2 ** DEEP == 0:
        passed(f"and {NPYR} ≡ 0 (mod 2^{DEEP}), the condition :394-395 requires of the period "
               f"before a wrap-padded split reproduces the infinite-periodic answer")
    else:
        fail(f":375 measures on {NPYR}² at L = {DEEP} and {NPYR} mod 2^{DEEP} = "
             f"{NPYR % 2 ** DEEP}; :394-395 says the split is only right when that is 0, so the "
             f"table's own rows are outside the rule this section states")
    L54 = WORDS[page(r"a (\w+)-level band split with `reflect` padding leaves a seam",
                     "the headline's level count (:54)")]
    S54 = pagef(r"band split with `reflect` padding leaves a seam \*\*(\d+)×\*\*",
                "the headline's seam (:54)")
    S443, L443, RT443 = (page(r"measured seam (\d+)× an interior step at L = (\d+) while "
                              r"`lo \+ hi == h` stayed exact to ([-\d.eE+]+)",
                              "the failure table's seam (:443)", g) for g in (1, 2, 3))
    same("the deepest level, :54 against the table header", L54, DEEP, ":54", ":378")
    same("the deepest level, :54 against the failure table", L54, int(L443), ":54", ":443")
    same("the reflect seam, :54 against the failure table", S54, float(S443), ":54", ":443")
    tcell = cell(REFR[LVLS.index(DEEP)], "the reflect cell")
    # ⚠️ The page quotes 221× for a cell that reads 221.5, i.e. TRUNCATED, where this corpus
    # has a recorded defect for exactly that (a ratio truncated instead of rounded, restated at
    # three ends). The gate accepts floor or round so the unmutated page is green and the
    # judgement stays with a maintainer; it still fires if either end moves by a whole step.
    if math.floor(tcell) <= S54 <= math.ceil(tcell):
        passed(f"the headline's {S54:g}× is the table's {tcell:g} "
               f"{'truncated' if S54 == math.floor(tcell) else 'rounded'} (:54 against :381)")
    else:
        fail(f"the headline says {S54:g}× and the table cell is {tcell:g}")
    same("the round trip, :443 against the table column", float(RT443), RT[0], ":443", ":380")
    page_ratio = cell(REFR[LVLS.index(DEEP)], "reflect") / cell(WRAPR[LVLS.index(DEEP)], "wrap")

    img = periodic_field(NPYR, 16)
    got = {}
    for mode in ("wrap", "reflect"):
        lo = low_band_2d(img, DEEP, A, mode)
        rt = max(abs((lo[y][x] + (img[y][x] - lo[y][x])) - img[y][x])
                 for y in range(NPYR) for x in range(NPYR))
        got[mode] = seam_ratio(lo)
        if rt <= 1e-14:
            passed(f"{mode:<8s} L = {DEEP}: round trip {rt:.1e} -- blind, exactly as the page says")
        else:
            fail(f"{mode:<8s} L = {DEEP}: round trip {rt:.3g}, and the page says machine precision")
    rig_ratio = got["reflect"] / got["wrap"]
    if rig_ratio >= 10.0 and page_ratio >= 10.0:
        passed(f"reflect's seam is {rig_ratio:.1f}× wrap's here and {page_ratio:.1f}× on the page "
               f"(rig {got['wrap']:.3g} → {got['reflect']:.3g}; the page's magnitudes are its own "
               f"input's, its ORDER is the claim)")
    else:
        fail(f"reflect/wrap seam ratio: rig {rig_ratio:.2f}, page {page_ratio:.2f} -- the fence "
             f"says wrap, never reflect, and one of these does not")

    # ── I. `period P ... a multiple of 2^L_max` ────────────────────────────────────────────
    head("I. :41 the period is a multiple of 2^L, against the phase table :398-402")
    NR = row(r"^\| period N \|.*$", "the phase table's period row")
    LR = row(r"^\| L \|.*$", "the phase table's level row")
    MR = row(r"^\| `N mod 2\^L` \|.*$", "the phase table's residue row")
    DR = row(r"^\| max difference \|.*$", "the phase table's difference row")
    P404, PN404, PL404 = (pagei(r"wrong by up to \*\*(\d+)%\*\* of relief when it is not — the "
                                r"`N` = (\d+), `L` = (\d+) cell", "the 42% cell (:404)", g)
                          for g in (1, 2, 3))
    W404, WN404, WL404 = (pagei(r"This line used to say (\d+)%, which is the `N` = (\d+), "
                                r"`L` = (\d+) cell", "the 22% cell it used to say (:404)", g)
                          for g in (1, 2, 3))
    f444 = re.search(r"measured exact at (\d+), wrong by up to (\d+)% of relief at (\d+) \(the "
                     r"`L` = (\d+) cell; (\d+)% is the `L` = (\d+) cell\)",
                     page(r"(measured exact at \d+, wrong by up to \d+% of relief at \d+ \(the "
                          r"`L` = \d+ cell; \d+% is the `L` = \d+ cell\))",
                          "the failure table's phase row (:444)"))
    cols = []
    for n_c, l_c, m_c, d_c in zip(NR, LR, MR, DR):
        for L in ints(l_c):
            cols.append((int(n_c), L, cell(m_c, "a residue"), cell(d_c, "a difference")))
    for N, L, m, d in cols:
        check(f"N = {N}, L = {L}: N mod 2^L", float(N % (2 ** L)), m)
        if (m == 0.0) == (d == 0.0):
            passed(f"N = {N}, L = {L}: residue {m:g} and difference {d:g} agree with "
                   f"'exact when N ≡ 0 (mod 2^L)'")
        else:
            fail(f"N = {N}, L = {L}: residue {m:g} but difference {d:g} -- one of them "
                 f"contradicts 'exact when N ≡ 0 (mod 2^L)'")
    worst = max(cols, key=lambda c: c[3])
    check(f"the biggest difference in the table, as % of relief",
          round(100.0 * worst[3]), float(P404))
    if (worst[0], worst[1]) == (PN404, PL404):
        passed(f"and it is the N = {PN404}, L = {PL404} cell the prose names")
    else:
        fail(f"the prose says the biggest is N = {PN404}, L = {PL404}; the table's biggest is "
             f"N = {worst[0]}, L = {worst[1]}")
    named = [c for c in cols if (c[0], c[1]) == (WN404, WL404)]
    if named and round(100.0 * named[0][3]) == W404:
        passed(f"the {W404}% this line used to say is the N = {WN404}, L = {WL404} cell, "
               f"{named[0][3]:g}, exactly as the correction says")
    else:
        fail(f"the prose says {W404}% is the N = {WN404}, L = {WL404} cell; the table says "
             f"{named[0][3] if named else 'no such cell'}")
    same("the max error, :404 against the failure table", P404, int(f444.group(2)), ":404", ":444")
    same("the cell it is at, :404 against the failure table", PN404, int(f444.group(3)), ":404", ":444")
    same("its level, :404 against the failure table", PL404, int(f444.group(4)), ":404", ":444")
    same("the superseded 22%, :404 against the failure table", W404, int(f444.group(5)), ":404", ":444")
    same("the level it belongs to, :404 against the failure table", WL404, int(f444.group(6)),
         ":404", ":444")
    exact_N = {c[0] for c in cols if c[2] == 0.0}
    if int(f444.group(1)) in exact_N:
        passed(f"the failure table's 'exact at {f444.group(1)}' is a period the table shows exact")
    else:
        fail(f"the failure table says exact at {f444.group(1)}; the table shows exact only at "
             f"{sorted(exact_N)}")

    # the phase claim is separable, so the rig runs it in 1-D over every column of the table
    for N, L, m, d in cols:
        sig = [sum((0.5 ** o) * noise2((i + OFFSET) * 16.0 * (2 ** o) / N, OFFSET * (2 ** o),
                                       mixer_hash, 16 * (2 ** o)) for o in range(3))
               for i in range(N)]
        base = low_band_1d(sig, L, A, "wrap")
        tiled = low_band_1d(sig + sig, L, A, "wrap")
        diff = max(abs(base[i] - tiled[i]) for i in range(N))
        if (diff == 0.0) == (d == 0.0):
            passed(f"N = {N}, L = {L}: 1-D low band against its own 2× tiling, "
                   f"{'0.0 exactly' if diff == 0.0 else f'{diff:.3g}'}; page {d:g}")
        else:
            fail(f"N = {N}, L = {L}: rig {diff:.3g}, page {d:g} -- one of them says the "
                 f"decimation lattice survives the wrap and the other does not")

    # ── J. the headline paragraph, both ends ───────────────────────────────────────────────
    head("J. :57-60 what it costs, against the failure table :437")
    ADD, BASE57 = (pagef(r"adds \*\*([\d.]+) ms\*\* to a \*\*([\d.]+) ms\*\* \d+²",
                         "the modular reduction's cost (:57)", g) for g in (1, 2))
    PCT = pagei(r"evaluation — (\d+)%, and the two runs' spreads overlap", "its percentage (:58)")
    EMB, RATIO = (pagef(r"is \*\*([\d.]+) ms\*\*, \*\*([\d.]+)×\*\* that, at a max wrap error",
                        "the embedding's cost (:59)", g) for g in (1, 2))
    MAXE, EX, EY = (page(r"at a max wrap error of `([-\d.eE+]+)` \(`([-\d.eE+]+)` on x, "
                         r"`([-\d.eE+]+)` on y\)", "the embedding's wrap error (:59)", g)
                    for g in (1, 2, 3))
    f437 = re.search(r"timed, that pair is ([\d.]+) ms against ([\d.]+) ms per \d+² samples on a "
                     r"CPU rig, ([\d.]+)× and not the counted (\d+)×, at a max wrap error of "
                     r"([-\d.eE+]+) \(([-\d.eE+]+) on x, ([-\d.eE+]+) on y\)",
                     page(r"(timed, that pair is [\d.]+ ms against [\d.]+ ms per \d+² samples on a "
                          r"CPU rig, [\d.]+× and not the counted \d+×, at a max wrap error of "
                          r"[-\d.eE+]+ \([-\d.eE+]+ on x, [-\d.eE+]+ on y\))",
                          "the failure table's timing row (:437)"))
    C4, C2, CPRED = (pagei(r"where (\d+)-against-(\d+) predicts\n(\d+)×",
                           "the corner-count prediction (:149)", g) for g in (1, 2, 3))
    # ⚠️ gating C4/C2 alone lets BOTH counts walk together: 32-against-8 also "predicts 4×".
    # The two counts are the corner counts of a gradient lattice cell in the dimensions the
    # page names -- 2^4 and 2^2 -- and the page prints the pair twice more, at :145 and :437.
    NDIM4 = pagei(r"evaluate a (\d)-D noise there", "the embedding's dimensionality (:131)")
    NDIM2 = pagei(r"the (\d)-D path is \*\*[\d.]+ ms\*\*", "the planar path's dimensionality (:149)")
    C4_145, C2_145 = (pagei(r"never pays\. (\d+)-against-(\d+) is the\s*\n\*gradient\*-lattice figure",
                            "the gradient corner counts in prose (:145)", g) for g in (1, 2))
    C4_437, C2_437 = (pagei(r"corner count's [\d.]+×; (\d+)-against-(\d+) is the "
                            r"\*gradient\*-lattice figure",
                            "the gradient corner counts in the failure table (:437)", g)
                      for g in (1, 2))
    check(f"a {NDIM4}-D gradient lattice cell has 2^{NDIM4} corners (:131 'a {NDIM4}-D noise')",
          float(2 ** NDIM4), float(C4))
    check(f"a {NDIM2}-D gradient lattice cell has 2^{NDIM2} corners (:149 'the {NDIM2}-D path')",
          float(2 ** NDIM2), float(C2))
    same("the 4-D gradient corner count, :149 against :145", C4, C4_145, ":149", ":145")
    same("the 2-D gradient corner count, :149 against :145", C2, C2_145, ":149", ":145")
    same("the 4-D gradient corner count, :149 against the failure table", C4, C4_437,
         ":149", ":437")
    same("the 2-D gradient corner count, :149 against the failure table", C2, C2_437,
         ":149", ":437")
    check(f"{ADD:g} ms on top of {BASE57:g} ms, as a percentage", round(100.0 * ADD / BASE57), float(PCT))
    check(f"{EMB:g} ms against {BASE57:g} ms, as a ratio", round(EMB / BASE57, 1), RATIO)
    check(f"{C4} gradient corners against {C2}, as a ratio", C4 / C2, float(CPRED))
    check("the max wrap error is the larger of the two axes", max(float(EX), float(EY)), float(MAXE))
    same("the 2-D timing, :57 against the failure table", BASE57, float(f437.group(1)), ":57", ":437")
    same("the 4-D timing, :59 against the failure table", EMB, float(f437.group(2)), ":59", ":437")
    same("the ratio, :59 against the failure table", RATIO, float(f437.group(3)), ":59", ":437")
    same("the max wrap error, :59 against the failure table", float(MAXE), float(f437.group(5)),
         ":59", ":437")
    same("the x-axis error, :59 against the failure table", float(EX), float(f437.group(6)),
         ":59", ":437")
    same("the y-axis error, :59 against the failure table", float(EY), float(f437.group(7)),
         ":59", ":437")
    same("the corner-count prediction, :149 against the failure table",
         float(CPRED), float(f437.group(4)), ":149", ":437")

    print()
    dup = sorted({(p, n) for p, n in ANCHORS if n != 1})
    if dup:
        for pat, n in dup:
            fail(f"anchor matches {n} places, so it is not anchored: {pat!r}")
    else:
        print(f"{len(ANCHORS)} anchors, every one matching exactly one place in the page")
    if FAILED:
        print(f"{len(FAILED)} of {CHECKS[0]} checks FAILED:")
        for m in FAILED:
            print(f"  - {m}")
        return 1
    print(f"{CHECKS[0]} checks, all reproduce from {DOC.name}")
    return 0
# ═════════════════════════════════════════════════════════════════════════════════════════
#  PRESERVED, and not part of the gate: the numpy timing rig this file has always been.
#  `seamless-and-periodic.md` cites it at :121 (the 256 KB byte count) and :148 (the
#  39.5/241.9 ms pair), and `registers/corrections.tsv:206` records a re-run of it. It is
#  kept verbatim, behind `--timings`, with numpy imported inside `_load_np` so that the gate
#  above never imports it. Its one edit is a rename: `noise2` -> `_np_noise2`,
#  so it cannot shadow the gate's own stdlib noise2. The arithmetic is untouched. Its saved output is `seamless-and-periodic.run.txt` beside this
#  file. NOTHING BELOW ASSERTS ANYTHING; it measures and prints.
# ═════════════════════════════════════════════════════════════════════════════════════════
np = None


def _load_np():
    global np
    import numpy as _np
    np = _np


SEED = 20260910
N = 512                      # 512**2 = 262144 samples, the document's own sample count
REPEATS = 15


def perm_table(size, rng):
    p = rng.permutation(size).astype(np.int32)
    return np.concatenate([p, p])


def fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _grad2(h, x, y):
    h = h & 7
    u = np.where(h < 4, x, y)
    v = np.where(h < 4, y, x)
    return np.where(h & 1, -u, u) + np.where(h & 2, -2.0 * v, 2.0 * v)


def _np_noise2(x, y, p, mask, period=None):
    """2-D gradient-lattice noise. `period` not None => reduce the lattice index mod it."""
    i0 = np.floor(x).astype(np.int32)
    j0 = np.floor(y).astype(np.int32)
    fx, fy = x - i0, y - j0
    if period is None:
        i0m, j0m = i0 & mask, j0 & mask
        i1m, j1m = (i0 + 1) & mask, (j0 + 1) & mask
    else:
        i0m, j0m = i0 % period, j0 % period
        i1m, j1m = (i0 + 1) % period, (j0 + 1) % period
        i0m, j0m = i0m & mask, j0m & mask
        i1m, j1m = i1m & mask, j1m & mask
    u, v = fade(fx), fade(fy)
    a, b = p[i0m] + j0m, p[i1m] + j0m
    a1, b1 = p[i0m] + j1m, p[i1m] + j1m
    n00 = _grad2(p[a], fx, fy)
    n10 = _grad2(p[b], fx - 1, fy)
    n01 = _grad2(p[a1], fx, fy - 1)
    n11 = _grad2(p[b1], fx - 1, fy - 1)
    x0 = n00 + u * (n10 - n00)
    x1 = n01 + u * (n11 - n01)
    return x0 + v * (x1 - x0)


def _grad4(h, x, y, z, w):
    h = h & 31
    a = np.where(h & 1, -x, x)
    b = np.where(h & 2, -y, y)
    c = np.where(h & 4, -z, z)
    d = np.where(h & 8, -w, w)
    return a + b + c + d


def noise4(x, y, z, w, p, mask):
    """4-D gradient-lattice noise: 16 corners, same hash and same fade as _np_noise2."""
    i0 = np.floor(x).astype(np.int32)
    j0 = np.floor(y).astype(np.int32)
    k0 = np.floor(z).astype(np.int32)
    l0 = np.floor(w).astype(np.int32)
    fx, fy, fz, fw = x - i0, y - j0, z - k0, w - l0
    u, v, s, t = fade(fx), fade(fy), fade(fz), fade(fw)
    i0m, j0m, k0m, l0m = i0 & mask, j0 & mask, k0 & mask, l0 & mask
    i1m, j1m, k1m, l1m = (i0 + 1) & mask, (j0 + 1) & mask, (k0 + 1) & mask, (l0 + 1) & mask
    corners = []
    for di in (0, 1):
        for dj in (0, 1):
            for dk in (0, 1):
                for dl in (0, 1):
                    ii = i1m if di else i0m
                    jj = j1m if dj else j0m
                    kk = k1m if dk else k0m
                    ll = l1m if dl else l0m
                    h = p[p[p[p[ii] + jj] + kk] + ll]
                    g = _grad4(h, fx - di, fy - dj, fz - dk, fw - dl)
                    wgt = (u if di else 1.0 - u) * (v if dj else 1.0 - v) \
                        * (s if dk else 1.0 - s) * (t if dl else 1.0 - t)
                    corners.append(g * wgt)
    acc = corners[0]
    for c in corners[1:]:
        acc = acc + c
    return acc


def torus4(x, y, T, p, mask):
    """The document's embedding: two circles in 4-D, r = T/(2*pi) for a unit-rate mapping."""
    a = 2.0 * np.pi * x / T
    b = 2.0 * np.pi * y / T
    r = T / (2.0 * np.pi)
    return noise4(r * np.cos(a), r * np.sin(a), r * np.cos(b), r * np.sin(b), p, mask)


def bench(fn, repeats=REPEATS):
    fn()                                    # warm up: first call pays numpy's allocation
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1e3)
    ts.sort()
    return ts[len(ts) // 2], ts[0], ts[-1]


def _timings_main():
    _load_np()
    rng = np.random.default_rng(SEED)
    p = perm_table(256, rng)
    mask = 255
    T = 64

    xs = np.linspace(0.0, T, N, endpoint=False, dtype=np.float64)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    X = np.ascontiguousarray(X.ravel())
    Y = np.ascontiguousarray(Y.ravel())
    nsamp = X.size

    print(f"rig      CPython {__import__('sys').version.split()[0]}, numpy {np.__version__}, "
          f"float64, single process, CPU")
    print(f"seed     {SEED}   samples {N}x{N} = {nsamp}   repeats {REPEATS} (median, min, max ms)")
    print()

    # -- A. what the modular reduction costs -------------------------------------------------
    m_raw = bench(lambda: _np_noise2(X, Y, p, mask, period=None))
    m_mod = bench(lambda: _np_noise2(X, Y, p, mask, period=T))
    print(f"A  noise2, raw index            {m_raw[0]:8.2f} ms   ({m_raw[1]:.2f} .. {m_raw[2]:.2f})")
    print(f"A  noise2, index mod P          {m_mod[0]:8.2f} ms   ({m_mod[1]:.2f} .. {m_mod[2]:.2f})")
    print(f"A  ratio mod/raw                {m_mod[0] / m_raw[0]:8.3f} x")
    print(f"A  per megasample, mod          {m_mod[0] * 1e6 / nsamp:8.2f} ms/Msample")
    print()

    # -- B. what the 4-D torus embedding costs -----------------------------------------------
    m_t4 = bench(lambda: torus4(X, Y, T, p, mask))
    print(f"B  noise2 (4 corners)           {m_mod[0]:8.2f} ms   ({m_mod[1]:.2f} .. {m_mod[2]:.2f})")
    print(f"B  torus4 (16 corners + 4 trig) {m_t4[0]:8.2f} ms   ({m_t4[1]:.2f} .. {m_t4[2]:.2f})")
    print(f"B  ratio torus4/noise2          {m_t4[0] / m_mod[0]:8.3f} x   "
          f"(corner count says 16/4 = 4.000 x)")
    print(f"B  per megasample, torus4       {m_t4[0] * 1e6 / nsamp:8.2f} ms/Msample")
    print()

    # -- B'. is the embedding actually periodic on this rig? ---------------------------------
    rng2 = np.random.default_rng(SEED + 1)
    sx = rng2.uniform(0.0, T, 4096)
    sy = rng2.uniform(0.0, T, 4096)
    e_x = np.max(np.abs(torus4(sx, sy, T, p, mask) - torus4(sx + T, sy, T, p, mask)))
    e_y = np.max(np.abs(torus4(sx, sy, T, p, mask) - torus4(sx, sy + T, T, p, mask)))
    print(f"B' torus4 max wrap error, x     {e_x:.3e}")
    print(f"B' torus4 max wrap error, y     {e_y:.3e}")
    print()

    # -- C. what the long hash table costs, in bytes -----------------------------------------
    print("C  permutation table, measured as numpy nbytes:")
    for label, entries in [("P = 1024, a P-entry table", 1024),
                           ("P = 1024, 6 octaves lac 2 -> finest is 32768", 32768)]:
        big = perm_table(entries, np.random.default_rng(SEED))              # int32, doubled
        lean = np.random.default_rng(SEED).permutation(entries).astype(np.uint16)
        print(f"C    {label:44s} int32 doubled {big.nbytes / 1024:7.1f} KB   "
              f"uint16 plain {lean.nbytes / 1024:7.1f} KB")
    print("C  (an integer mixer with no table pays 0 bytes and is the recommended route)")


if __name__ == "__main__":
    if "--timings" in sys.argv:
        _timings_main()
        sys.exit(0)
    sys.exit(gate())
