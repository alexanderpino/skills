#!/usr/bin/env python3
"""List, per workflow step, whether the artifact it produces exists. Observations, never verdicts.

    python3 .claude/scripts/artifact_check.py                 # every phase
    python3 .claude/scripts/artifact_check.py --phase build   # one phase

Reads .claude/docs/workflow-catalog.json and the effective modes.workflow. Prints one row
per step:

    step=<id> phase=<id> expected=yes|no|later status=PRESENT|MISSING|NOT_ASSESSED files=<n> glob=<glob>

`expected=later` means the step's min_workflow is above the project's modes.workflow, so its
artifact is not asked for at this rigor. `status=NOT_ASSESSED` means the step names no
artifact glob, so nothing could be counted. Deciding what a row means is the calling skill's
job (/next-step, /gate-check): a helper that judged would contradict a mode it cannot see.
Exit code is 0 unless the catalog itself cannot be read (2).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("STUDIO_ROOT") or os.path.abspath(os.path.join(HERE, "..", ".."))
ORDER = ["minimal", "standard", "full"]


def workflow_level() -> str:
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "resolve_config.py"), "--get", "modes.workflow"],
                           capture_output=True, text=True, timeout=30, env={**os.environ, "STUDIO_ROOT": ROOT})
        v = r.stdout.strip()
        return v if v in ORDER else "minimal"
    except Exception:
        return "minimal"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase")
    a = ap.parse_args(argv)
    path = os.path.join(ROOT, ".claude", "docs", "workflow-catalog.json")
    try:
        with open(path, encoding="utf-8") as fh:
            cat = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"CATALOG: NOT_ASSESSED ({path}: {e})")
        return 2
    level = workflow_level()
    print(f"WORKFLOW: {level}")
    phases = cat.get("phases", [])
    if a.phase and a.phase not in {p["id"] for p in phases}:
        print(f"PHASE: NOT_ASSESSED (no phase {a.phase!r}; phases: {', '.join(p['id'] for p in phases)})")
        return 0
    counts = {"PRESENT": 0, "MISSING": 0, "NOT_ASSESSED": 0}
    for p in phases:
        if a.phase and p["id"] != a.phase:
            continue
        for s in p.get("steps", []):
            need = s.get("min_workflow", "minimal")
            if not s.get("required", False):
                expected = "no"
            elif ORDER.index(need if need in ORDER else "minimal") > ORDER.index(level):
                expected = "later"
            else:
                expected = "yes"
            art = s.get("artifact") or {}
            g = art.get("glob")
            if not g:
                status, n = "NOT_ASSESSED", 0
            else:
                n = len(glob.glob(os.path.join(ROOT, g), recursive=True))
                status = "PRESENT" if n >= int(art.get("min_count", 1)) else "MISSING"
            counts[status] += 1
            print(f"step={s['id']} phase={p['id']} expected={expected} status={status} files={n} glob={g or '-'}")
    print("STEPS: " + " ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
