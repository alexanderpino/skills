#!/usr/bin/env python3
"""Re-derivation of every figure heightfield-lod.md now states next to its cost.

NOT a benchmark and NOT a measurement: no new number is produced here. This is closed-form
arithmetic over figures already in the document, so the orchestrator can re-run the check that
the pair (cost, error) is internally consistent. No seed, no rig, no timing.
"""
import math, pathlib, re, sys

ok = True
def check(label, got, want, tol=0.05):
    global ok
    good = abs(got - want) <= tol * abs(want)
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got:.4g}, document says {want:.4g}")

# Cost half: resident bytes for the 8k x 8k field in the tier line.
cells = 8192 * 8192
check("R16 heightfield, 2 bytes/cell (MB)", cells * 2 / 1e6, 134)
check("+ full mip pyramid, x4/3 (MB)", cells * 2 * 4 / 3 / 1e6, 179)
check("R16 + mipped RG8 normals, 4 bytes/cell (MB)", cells * 4 / 1e6, 268)
check("+ full mip pyramid, x4/3 (MB)", cells * 4 * 4 / 3 / 1e6, 358)

# Error half: corner-vs-centre worst case over camera orientation,
# 1 + tan^2(fovY/2) * (1 + aspect^2), at 16:9.
aspect = 16 / 9
for fov, want in ((60, 2.4), (90, 5.2), (110, 9.5)):
    m = 1 + math.tan(math.radians(fov) / 2) ** 2 * (1 + aspect ** 2)
    check(f"corner multiplier on rho at fovY {fov} deg", m, want)

# The pair is actually adjacent in the file, and the file is under the cap.
doc = pathlib.Path(__file__).resolve().parents[4] / "home/user/skills/gaia/references/heightfield-lod.md"
if not doc.exists():
    doc = pathlib.Path("/home/user/skills/gaia/references/heightfield-lod.md")
lines = doc.read_text(encoding="utf-8").split("\n")
cost = [i for i, l in enumerate(lines, 1) if re.search(r"\b134 MB\b", l)]
err = [i for i, l in enumerate(lines, 1) if re.search(r"maximum\*\* error|\*\*maximum error\*\*", l)]
print(f"{'PASS' if cost and err and min(abs(c - e) for c in cost for e in err) < 20 else 'FAIL'}"
      f"  cost line(s) {cost}, error line(s) {err} within 20 lines of each other")
print(f"{'PASS' if len(lines) <= 451 else 'FAIL'}  line count {len(lines) - 1} vs 450 cap")
sys.exit(0 if ok else 1)
