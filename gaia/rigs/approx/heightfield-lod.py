#!/usr/bin/env python3
"""Re-derivation of every figure heightfield-lod.md states next to its cost.

NOT a benchmark and NOT a measurement: no new number is produced here. This is closed-form
arithmetic checked against the figures the DOCUMENT prints, so the orchestrator can re-run the
check that the pair (cost, error) is internally consistent. No seed, no timing.

⚠️ Rewritten 2026-09-15. Until then every `want` was a LITERAL typed into the source
(`check("R16 ...", cells*2/1e6, 134)`) and printed as "document says 134" -- so the rig compared
arithmetic against a transcript of the page made when the rig was written, and would have gone on
passing after any edit to the page. An independent rating panel found it, and it was the most
embarrassing kind of finding this corpus can take: a verification harness that verifies its own
memory. The figures are now PARSED out of the document, and a figure that goes missing is a FAIL,
not a silent skip -- a rig that quietly checks nothing is the defect it was just repaired for.

Halting: no loop with a data-dependent bound. Two fixed tuples, one regex pass over the file.
"""
import math
import pathlib
import re
import sys

# The document, located from this file, not from an absolute path: rigs/approx/ -> gaia/ -> .
DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "heightfield-lod.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
TEXT = DOC.read_text(encoding="utf-8")
LINES = TEXT.split("\n")

ok = True


def fail(msg: str) -> None:
    global ok
    ok = False
    print(f"FAIL  {msg}")


def check(label: str, got: float, want: float | None, tol: float = 0.05) -> None:
    """want=None means the figure was not found in the document -- that is a failure, not a skip."""
    global ok
    if want is None:
        fail(f"{label}: derived {got:.4g}, but the document no longer prints this figure")
        return
    good = abs(got - want) <= tol * abs(want)
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  {label}: derived {got:.4g}, document says {want:.4g}")


def mb_after(anchor: str, nth: int = 1) -> float | None:
    """The `nth` bolded MB figure the document prints after `anchor`.

    `nth` exists because one sentence carries two of them ("**268 MB** and **358 MB**").
    Anchoring on the prose rather than on either number is the point: anchor on a figure and
    the rig is back to checking its own memory.
    """
    i = TEXT.find(anchor)
    if i < 0:
        return None
    found = re.findall(r"\*\*([\d.]+)\s*MB\*\*", TEXT[i + len(anchor):i + len(anchor) + 400])
    return float(found[nth - 1]) if len(found) >= nth else None


def corner_multipliers() -> dict[int, float]:
    """The `N.N x at fovY D deg` pairs the document prints beside the corner formula."""
    out: dict[int, float] = {}
    for mult, fov in re.findall(r"([\d.]+)×\s*at\s*(?:fovY\s*)?(\d+)\s*°", TEXT):
        out.setdefault(int(fov), float(mult))
    return out


# ---- cost half: resident bytes for the 8k x 8k field in the tier line ----
cells = 8192 * 8192
check("R16 heightfield, 2 bytes/cell (MB)",
      cells * 2 / 1e6, mb_after("**2 bytes per cell**"))
check("R16 + full mip pyramid, x4/3 (MB)",
      cells * 2 * 4 / 3 / 1e6, mb_after("its full mip pyramid adds a third"))
check("R16 + mipped RG8 normals, 4 bytes/cell (MB)",
      cells * 4 / 1e6, mb_after("doubles both to 4 bytes per cell", nth=1))
check("that pair + full mip pyramid, x4/3 (MB)",
      cells * 4 * 4 / 3 / 1e6, mb_after("doubles both to 4 bytes per cell", nth=2))

# ---- error half: corner-vs-centre worst case, 1 + tan^2(fovY/2)*(1 + aspect^2), at 16:9 ----
ASPECT = 16 / 9
printed = corner_multipliers()
if not printed:
    fail("no `N.N× at D°` corner multipliers found in the document at all")
for fov in (60, 90, 110):
    m = 1 + math.tan(math.radians(fov) / 2) ** 2 * (1 + ASPECT ** 2)
    check(f"corner multiplier on rho at fovY {fov} deg", m, printed.get(fov))

# ---- the pair is actually adjacent in the file, and the file is under the cap ----
cost = [i for i, l in enumerate(LINES, 1) if re.search(r"\b134 MB\b", l)]
err = [i for i, l in enumerate(LINES, 1) if re.search(r"maximum\*\* error|\*\*maximum error\*\*", l)]
if cost and err and min(abs(c - e) for c in cost for e in err) < 20:
    print(f"PASS  cost line(s) {cost}, error line(s) {err} within 20 lines of each other")
else:
    fail(f"cost line(s) {cost}, error line(s) {err} -- not within 20 lines, or one is missing")

if len(LINES) <= 451:
    print(f"PASS  line count {len(LINES) - 1} vs 450 cap")
else:
    fail(f"line count {len(LINES) - 1} vs 450 cap")

sys.exit(0 if ok else 1)
