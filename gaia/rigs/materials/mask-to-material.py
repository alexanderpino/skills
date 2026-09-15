#!/usr/bin/env python3
"""The `## Use this` composite of mask-to-material.md, run against its own page.

⚠️ WHY THIS FILE EXISTS. `registers/pseudocode-execution.tsv:226` recorded this block as RUN,
and named its harness `scratchpad/m2m_gate.py`. That file is in neither the tree nor the
history -- `git log --all -- '*m2m_gate*'` is empty -- and the row's own note said "Commit
pending" from the day it was written. It is the last survivor of the class `876e21f` fixed when
59 register rows pointed at a scratch directory a container reclaim would destroy: that pass
moved the rigs it could find and never noticed one it could not.

WHAT IS GATED, AND WHAT DELIBERATELY IS NOT. Three claims, all parsed from the page:

  1. STRUCTURAL -- the exact one. For `depth < 1/n`, every material below `(1/n - depth)/2` of
     the normalised weight is PROVABLY absent, not statistically absent. The page states 0.000%
     leak; this asserts exactly zero, with no tolerance, because the page's own word is "proof".
  2. CONTINUITY -- walking w_A down to 0, the largest step in its share is the page's figure,
     against 0.50 for a `w_i > 0` gate.
  3. DEGENERACY -- below `eps` every `b_i` is 0, `m = -depth`, and all n survive at 1/n each.

The COST figures at :264-267 are NOT gated, and that is a finding rather than an omission: the
page contradicts itself on them. See `report_cost_contradiction()` at the bottom.

Halting: fixed trial counts and one fixed-length walk. No loop with a data-dependent bound.
"""
import pathlib
import random
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "mask-to-material.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")

SEED = 20260915
EPS = 1e-6
ok = True


def page(pattern: str, what: str, group: int = 1) -> float:
    m = re.search(pattern, BODY)
    if not m:
        sys.exit(f"the page no longer states {what} (pattern {pattern!r})")
    return float(m.group(group))


def check(label: str, got: float, want: float, tol: float) -> None:
    global ok
    good = abs(got - want) <= tol
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got:.6g}, page says {want:.6g}")


def composite(weights, heights, depth, form="scaled"):
    """The block, transcribed literally from references/mask-to-material.md:38-42."""
    s = max(sum(weights), EPS)
    w = [x / s for x in weights]
    b = ([wi * (1 + hi) for wi, hi in zip(w, heights)] if form == "scaled"
         else [wi + hi for wi, hi in zip(w, heights)])
    m = max(b) - depth
    wp = [max(bi - m, 0.0) for bi in b]
    t = sum(wp)
    return [x / t for x in wp] if t > 0 else [0.0] * len(wp)


# ── 1. structural: a material below the threshold is PROVABLY absent ─────────────────────
# The page's own precondition, parsed rather than assumed.
LEAK = page(r"Measured:\s*\n?([\d.]+)% leak at", "the measured leak")
# The threshold the page proves, parsed rather than transcribed. It was `(1.0/3 - depth) / 2`
# typed into this file until a tamper test walked `/2` to `/9` on the page and this rig stayed
# GREEN -- a memory-check inside the rig written to end memory-checks, caught only because the
# mutation was run rather than reasoned about.
THRESH_DIV = page(r"every material below `\(1/n \u2212 depth\)/(\d+)`", "the absence threshold")
N_MATERIALS = 3
# ⚠️ Weights are sampled FREELY and EVERY material is tested against the threshold. The first
# version drew `[tiny] + two randoms` with `tiny` in {0, 1e-3, 1e-2}, so the only material it
# ever compared was one already far below any plausible threshold -- and widening the page's
# divisor from /2 to /1 left the rig GREEN, because no new material entered the test. The
# threshold was decoration. It is load-bearing now: at /1 the claim is violated with a share of
# 0.55, and this goes red.
rng = random.Random(SEED)
worst = 0.0
trials = below = 0
for depth in (0.1, 0.2):
    for _ in range(60000):
        trials += 1
        # a spread of regimes: free weights, and the near-zero cases the page argues about
        weights = [rng.choice([0.0, 1e-3, 1e-2, rng.random()]) for _ in range(N_MATERIALS)]
        if sum(weights) < EPS:
            continue
        heights = [rng.random() for _ in range(N_MATERIALS)]
        shares = composite(weights, heights, depth)
        s = sum(weights)
        for i in range(N_MATERIALS):
            if weights[i] / s < (1.0 / N_MATERIALS - depth) / THRESH_DIV:
                below += 1
                worst = max(worst, shares[i])
check(f"leak below the page's threshold ({below} materials under it, {trials} texels)",
      100.0 * worst, LEAK, 0.0)
print(f"      (asserted at tolerance 0 -- the page's word is 'provably absent', not 'small')")

# ── 2. continuity: the largest step as w_A walks to zero ─────────────────────────────────
STEP = page(r"largest step \*\*([\d.]+)\*\*", "the largest continuity step")
GATE = page(r"largest step \*\*[\d.]+\*\*, and ([\d.]+) for the gate", "the gated form's step")
rng = random.Random(SEED + 1)
heights = [rng.random() for _ in range(3)]
rest = [0.4, 0.5]
walk = [1e-1 * (1 - i / 2000.0) for i in range(2001)]
shares = [composite([wa] + rest, heights, 0.1)[0] for wa in walk]
biggest = max(abs(a - b) for a, b in zip(shares, shares[1:]))
check("largest step, weight-scaled", round(biggest, 3), STEP, 0.0)

# The form the page compares against: the ADDITIVE bias with a hard `w_i > 0` mask applied
# INSIDE the composite, so a material at exactly zero is excluded while one at 1e-9 is not.
# That is where the discontinuity lives -- not in the final share, which was this rig's own
# first mistake: masking the output instead of the input produced no jump at all and the
# check failed against the page for a reason that was mine.
def gated_composite(weights, heights, depth):
    keep = [i for i, w in enumerate(weights) if w > 0.0]
    if not keep:
        return [0.0] * len(weights)
    s = max(sum(weights), EPS)
    b = {i: weights[i] / s + heights[i] for i in keep}
    m = max(b.values()) - depth
    wp = {i: max(b[i] - m, 0.0) for i in keep}
    tot = sum(wp.values())
    return [wp.get(i, 0.0) / tot if tot > 0 else 0.0 for i in range(len(weights))]

# REPORTED, not gated. Over 20000 random height/weight draws the largest jump for the gated
# form is 1.0000 -- a zero-weight material that held the WHOLE pixel and then vanished -- not
# the page's 0.50. The page understates the case for its own recommendation, which is the
# harmless direction, but a gate asserting 0.50 would be asserting a number this rig cannot
# reach and the page cannot source. The claim that matters is the weight-scaled 0.000 above,
# and that reproduces exactly.
rngj = random.Random(SEED + 3)
worst_jump = 0.0
for _ in range(20000):
    hj = [rngj.random() for _ in range(3)]
    other = [rngj.random(), rngj.random()]
    worst_jump = max(worst_jump,
                     abs(gated_composite([1e-9] + other, hj, 0.1)[0]
                         - gated_composite([0.0] + other, hj, 0.1)[0]))
print(f"      (`w_i > 0` gate: page says {GATE:.2f}, this rig measures {worst_jump:.4f} over "
      f"20000 draws -- reported, not gated; the page understates its own case)")

# ── 3. degeneracy below eps: all n survive at 1/n ────────────────────────────────────────
n = 3
shares = composite([0.0] * n, [rng.random() for _ in range(n)], 0.1)
check(f"share of each of {n} materials below eps", shares[0], 1.0 / n, 1e-9)
if len(set(round(s, 12) for s in shares)) != 1:
    ok = False
    print(f"FAIL  below eps the {n} shares are not equal: {shares}")
else:
    print(f"PASS  below eps all {n} shares are equal -- the page's 'equal blend of all n'")


# ── the cost figures: NOT a gate, a drift report ─────────────────────────────────────────
def report_cost_contradiction() -> None:
    """The page states one quantity twice, with two values, and cites a harness that never was.

    `texels that are a mix at t = 0.5`, additive bias, depth 0.02:
      :200  the comparison table  -> 4.9%
      :216  the prose under it    -> 4.9%
      :267  the weight-scaled paragraph, naming the additive figure it beats -> 4.2%

    The page's own claim at :265 is "twice as many". 8.1/4.2 = 1.93 and 8.1/4.9 = 1.65, so the
    page's prose supports 4.2 and refutes 4.9 -- but an independent measurement here, over the
    ensemble as the page describes it, gives neither. Printed rather than gated, because a gate
    that picks a winner would be inventing provenance: `colour_blend.py`, named at :194 as the
    source of the 4.9, is absent from the tree AND from history, exactly like `m2m_gate.py`.
    """
    rng = random.Random(SEED + 2)
    out = {}
    for form in ("additive", "scaled"):
        mixed = 0
        for _ in range(200000):
            h = [rng.random() for _ in range(3)]
            surv = composite([0.5, 0.5, 0.0], h, 0.02, form)
            mixed += sum(1 for s in surv if s > 0) > 1
        out[form] = 100.0 * mixed / 200000
    print()
    print("  COST FIGURES -- reported, NOT gated. The page contradicts itself:")
    print(f"    page :200 and :216 say 4.9% mixed at t=0.5, additive, depth 0.02")
    print(f"    page :267 says 4.2% for the same quantity at the same depth")
    print(f"    measured here: additive {out['additive']:.2f}%, "
          f"weight-scaled {out['scaled']:.2f}%, ratio {out['scaled']/out['additive']:.2f}")
    print(f"    the page claims 'twice as many': 8.1/4.2 = 1.93, 8.1/4.9 = 1.65")
    print("    -> 4.9 is refuted by the page's own prose; 4.2 is not confirmed by this rig.")
    print("       Neither is traceable: colour_blend.py has never existed. Re-measure.")


report_cost_contradiction()
print()
sys.exit(0 if ok else 1)
