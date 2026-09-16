#!/usr/bin/env python3
"""The one arithmetic in shader-craft.md's `## Use this` rules, against its own page.

⚠️ SCOPE, AND IT IS NARROW ON PURPOSE. The `## Use this` fence at :49-62 is eight numbered
rules. Seven of them are prescriptions with no numeric consequence -- "SampleLevel, never
Sample" -- and rules 4 and 5 are formulae whose operands are ALL unbound (`virtualSize`,
`poolSize`, `pageMip`, `computeMip`, `feedbackScale`). A rig over those could only restate the
formula: edit the page and both sides of the comparison move together, so the gate could not
fail. That is not a gate, and this file does not pretend otherwise.

Rule 8 is different. It prints two fp16 thresholds AND a multiplier relating them, so the page
can be internally wrong -- and it was. Until 2026-09-15 it said the flushed regime is `45x`
worse in three places; `7.8e-3 / 1.7e-4 = 45.882`, which rounds to 46. Truncation, repeated at
all three ends, in a corpus that rounds everywhere else.

⚠️ A completeness critic called this block inconsistent with `shallow-water.md:133-135`, on the
principle that a formula with unbound operands states nothing a page value can contradict. The
principle is right and it does NOT apply there: shallow-water binds its input (1 mm) AND its
output (0.099 m/s), so a rig applies `sqrt(g*h)` BETWEEN them and an edit to either end goes
red. Here nothing is bound. The two verdicts are consistent; the critic's finding was not.

Halting: three regex searches and one division.
"""
import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "shader-craft.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")
ok = True

m = re.search(r"it vanishes at ([\d.e-]+) per component at BEST, and at ([\d.e-]+) where\s+"
              r"float16 denorms are flushed -- ([\d.]+)x worse", BODY)
if not m:
    sys.exit("rule 8 no longer states both fp16 thresholds and the multiplier between them")
best, flushed, printed = float(m.group(1)), float(m.group(2)), float(m.group(3))
ratio = flushed / best
if round(ratio) != printed:
    ok = False
    print(f"FAIL  rule 8: {flushed:g} / {best:g} = {ratio:.3f}, which rounds to {round(ratio)}; "
          f"the page prints {printed:g}x")
else:
    print(f"PASS  rule 8: {flushed:g} / {best:g} = {ratio:.3f} -> {round(ratio)}x, "
          f"and the page prints {printed:g}x")

# The same multiplier is restated twice in the body. A correction that lands at one end only is
# this corpus's most-recorded defect, so every end is checked against the computed value.
ends = re.findall(r"loses the dot `(\d+)×` earlier|flushed subnormal products by `(\d+)×`",
                  BODY)
found = [int(a or b) for a, b in ends]
if len(found) != 2:
    ok = False
    print(f"FAIL  expected the multiplier restated at 2 body ends, found {len(found)}")
elif any(v != round(ratio) for v in found):
    ok = False
    print(f"FAIL  body ends state {found}x against the computed {round(ratio)}x -- "
          f"a correction that landed at one end only")
else:
    print(f"PASS  both body ends restate {round(ratio)}x, agreeing with the fence")

print()
sys.exit(0 if ok else 1)
