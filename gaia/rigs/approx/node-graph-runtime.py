#!/usr/bin/env python3
"""node-graph-runtime.md -- re-derivation + guard probe. No new measurement.

Every figure this document gained is channel (a): already on the page. This script
(1) re-derives the two percentages from the four numbers already printed in the
document's own AVX512 fence, using the denominator the page names (the AVX512-ON
value, per registers/corrections.tsv X48), and (2) re-runs check.py's own COST_UNIT
and ERROR_STATED patterns over the document so the pair can be seen, not assumed.

NOT a benchmark. Nothing here is timed. The ms/MB figures on the page are another
run's recorded outputs (registers/pseudocode-execution.tsv:234 records the fence as
NOT RUN, recorded outputs), and this script does not reproduce or replace them.

Usage: python3 node-graph-runtime.py [path-to-repo-root]
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/skills")
DOC = ROOT / "gaia" / "references" / "node-graph-runtime.md"

# --- (1) re-derive, from the fence already in the document -------------------
# canyon relief, canyon pit-storage, badlands relief; AVX512 on vs off.
FENCE = {
    "canyon relief":      (268.99, 270.71),
    "canyon pit-storage": (5.2169e6, 4.1597e6),
    "badlands relief":    (260.52, 258.63),
}
print("gap over the AVX512-ON value (the denominator the page names):")
for name, (on, off) in FENCE.items():
    pct = abs(on - off) / on * 100.0
    print(f"  {name:<20} on={on:<12g} off={off:<12g} |gap| = {pct:.3f}%  -> printed {round(pct,1)}%")
# the other column, for the sentence that says the same gap reads 25% there
on, off = FENCE["canyon pit-storage"]
print(f"  canyon pit-storage over the AVX512-OFF value: {abs(on-off)/off*100:.1f}%  (page says 25%)")

# --- (2) the pair check.py actually looks for -------------------------------
sys.path.insert(0, str(ROOT / "gaia" / "scripts"))
import check  # noqa: E402

_, body = check.parse_front_matter(DOC)
err = check.ERROR_STATED.search(body)
costs = [m.group(0) for m in check.COST_UNIT.finditer(body)]
line = body[:err.start()].count("\n") + 1 if err else None
print()
print(f"ERROR_STATED: {err.group(0)!r} at body line {line}" if err else "ERROR_STATED: NONE")
print(f"COST_UNIT   : {len(costs)} matches, first {costs[:4]}")
print(f"lines       : {len(DOC.read_text().splitlines())} / 450 cap")
sys.exit(0 if (err and costs) else 1)
