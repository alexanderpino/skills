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

# Located from this file -- rigs/approx/ -> gaia/ -- not from a hardcoded absolute path. The
# old default was `/home/user/skills`, which made the rig unrunnable against any other checkout.
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
DOC = ROOT / "references" / "node-graph-runtime.md"
if not DOC.exists():                       # tolerate being handed a repo root instead
    DOC = ROOT / "gaia" / "references" / "node-graph-runtime.md"
if not DOC.exists():
    sys.exit(f"cannot find node-graph-runtime.md under {ROOT} -- run this rig from inside the repo")

# --- (1) re-derive, from the fence PARSED OUT OF the document ----------------
# ⚠️ Until 2026-09-15 these six numbers were LITERALS typed into this file, under a comment
# claiming they came "from the fence already in the document". They did not -- they were a
# transcript of it, made once, and this rig would have gone on passing through any edit to the
# page. That is the third time this corpus has been caught with a harness checking its own
# memory (`heightfield-lod.py`, `mu-d-overcast.py`, and now this), and it was caught here by
# check.py's own `rig_asserts()` counting this file as one that checks its page when it did not.
BODY = DOC.read_text(encoding="utf-8")
FENCE = {}
for _m in re.finditer(r"^(canyon relief|canyon pit-storage|badlands relief)\s+"
                      r"([\d.eE+-]+)\s+([\d.eE+-]+)", BODY, re.M):
    FENCE[_m.group(1)] = (float(_m.group(2)), float(_m.group(3)))
if len(FENCE) != 3:
    sys.exit(f"the SIMD-drift fence has moved: parsed {sorted(FENCE)} from {DOC.name}, want 3 rows")

# The percentage the PAGE prints for the pit-storage gap, and the one it says the other
# denominator would give. Parsed too, because the whole point of the paragraph is which
# denominator was used.
_pm = re.search(r"=\s*([\d.]+)%`;\s*against the other column the same gap reads\s*([\d.]+)%", BODY)
if not _pm:
    sys.exit("the page no longer states the pit-storage gap against both denominators")
PAGE_ON_PCT, PAGE_OFF_PCT = float(_pm.group(1)), float(_pm.group(2))

# The relief gap the page prints in prose and repeats in its failure table. Parsed, because a
# rig that gates one of three parsed rows is three-quarters decoration -- found when mutating
# `badlands relief` in a scratch copy left this rig GREEN, hours after it was repaired for
# exactly this class of defect. Assert on every row you bothered to parse.
_rm = re.search(r"\*\*([\d.]+)% off\*\* on canyon relief", BODY)
if not _rm:
    sys.exit("the page no longer states the canyon-relief gap")
PAGE_RELIEF_PCT = float(_rm.group(1))

ok = True
print("gap over the AVX512-ON value (the denominator the page names):")
for name, (on, off) in FENCE.items():
    pct = abs(on - off) / on * 100.0
    print(f"  {name:<20} on={on:<12g} off={off:<12g} |gap| = {pct:.3f}%  -> printed {round(pct,1)}%")
    if "relief" in name:
        # Both relief rows are the page's "0.6%" claim to one decimal; a row that moves off it
        # is the page and the fence disagreeing, whichever end moved.
        good = abs(round(pct, 1) - PAGE_RELIEF_PCT) <= 0.15
        ok = ok and good
        print(f"    {'PASS' if good else 'FAIL'}  {name} against the page's "
              f"{PAGE_RELIEF_PCT}% relief claim")
# the other column, for the sentence that says the same gap reads 25% there
on, off = FENCE["canyon pit-storage"]
derived_on = abs(on - off) / on * 100.0
derived_off = abs(on - off) / off * 100.0
for label, got, want in (("AVX512-ON denominator", derived_on, PAGE_ON_PCT),
                         ("AVX512-OFF denominator", derived_off, PAGE_OFF_PCT)):
    good = abs(got - want) <= 0.05 * want
    ok = ok and good
    print(f"  {'PASS' if good else 'FAIL'}  pit-storage gap over the {label}: "
          f"derived {got:.1f}%, page says {want:.1f}%")

# --- (2) the pair check.py actually looks for -------------------------------
sys.path.insert(0, str(DOC.resolve().parents[1] / "scripts"))
import check  # noqa: E402

_, body = check.parse_front_matter(DOC)
err = check.ERROR_STATED.search(body)
costs = [m.group(0) for m in check.COST_UNIT.finditer(body)]
line = body[:err.start()].count("\n") + 1 if err else None
print()
print(f"ERROR_STATED: {err.group(0)!r} at body line {line}" if err else "ERROR_STATED: NONE")
print(f"COST_UNIT   : {len(costs)} matches, first {costs[:4]}")
print(f"lines       : {len(DOC.read_text().splitlines())} / 450 cap")
sys.exit(0 if (ok and err and costs) else 1)
