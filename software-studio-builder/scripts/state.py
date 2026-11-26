#!/usr/bin/env python3
"""Run state for one studio build, in `<target>/.ssb/state.json`, so a run resumes across sessions.

    state.py init RUN_DIR --domain "..." --target DIR
    state.py show RUN_DIR
    state.py intake RUN_DIR --json '{"domain": "...", "rigor": "minimal", ...}'
    state.py phase RUN_DIR research|proposal|generate|verify|done
    state.py approve RUN_DIR --by user --note "approved after removing role X"
    state.py approved RUN_DIR          # exit 0 if the CURRENT proposal.json is the approved one
    state.py layer RUN_DIR core        # record a generated layer

Approval pins the sha256 of proposal.json. Any edit after approval un-approves it: the
generator refuses to run until the user approves the edited proposal again. That is the
hard stop between the two stages, enforced by a file, not by a promise.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

PHASES = ["intake", "research", "proposal", "generate", "verify", "done"]
LAYERS = ["core", "agents", "skills", "rules", "templates", "gates", "catalog", "hooks", "tests"]


def sp(run_dir):
    return os.path.join(run_dir, "state.json")


def load(run_dir) -> dict:
    with open(sp(run_dir), encoding="utf-8") as fh:
        return json.load(fh)


def save(run_dir, st):
    tmp = sp(run_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, sp(run_dir))


def proposal_hash(run_dir) -> str | None:
    p = os.path.join(run_dir, "proposal.json")
    if not os.path.exists(p):
        return None
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def is_approved(run_dir) -> tuple[bool, str]:
    try:
        st = load(run_dir)
    except (OSError, ValueError) as e:
        return False, f"no readable state.json ({e})"
    ap = st.get("approval")
    if not ap:
        return False, "the proposal has not been approved"
    h = proposal_hash(run_dir)
    if h != ap.get("sha256"):
        return False, "proposal.json changed after approval; the user must approve it again"
    return True, f"approved by {ap.get('by')} on {ap.get('at')}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("run_dir"); p.add_argument("--domain", required=True); p.add_argument("--target", required=True)
    p = sub.add_parser("show"); p.add_argument("run_dir")
    p = sub.add_parser("intake"); p.add_argument("run_dir"); p.add_argument("--json", required=True)
    p = sub.add_parser("phase"); p.add_argument("run_dir"); p.add_argument("phase", choices=PHASES)
    p = sub.add_parser("approve"); p.add_argument("run_dir"); p.add_argument("--by", required=True); p.add_argument("--note", default="")
    p = sub.add_parser("approved"); p.add_argument("run_dir")
    p = sub.add_parser("layer"); p.add_argument("run_dir"); p.add_argument("layer", choices=LAYERS)
    a = ap.parse_args(argv)
    if a.cmd == "init":
        os.makedirs(a.run_dir, exist_ok=True)
        if os.path.exists(sp(a.run_dir)):
            print(f"state exists: {sp(a.run_dir)} (resume it with `state.py show`)")
            return 0
        save(a.run_dir, {"schema": "ssb-state/1", "domain": a.domain, "target": os.path.abspath(a.target),
                         "phase": "intake", "intake": {}, "approval": None, "layers": [],
                         "started": _dt.date.today().isoformat(), "history": []})
        print(f"initialised {sp(a.run_dir)}")
        return 0
    try:
        st = load(a.run_dir)
    except (OSError, ValueError) as e:
        print(f"state NOT ASSESSED: {e}")
        return 3
    if a.cmd == "show":
        ok, why = is_approved(a.run_dir)
        print(json.dumps(st, indent=2))
        print(f"proposal approval: {'valid' if ok else 'NOT VALID'} — {why}")
        print(f"layers remaining: {', '.join(l for l in LAYERS if l not in st['layers']) or 'none'}")
        return 0
    if a.cmd == "intake":
        st["intake"].update(json.loads(a.json))
    elif a.cmd == "phase":
        st["phase"] = a.phase
    elif a.cmd == "approve":
        h = proposal_hash(a.run_dir)
        if not h:
            print("no proposal.json to approve")
            return 1
        if a.by != "user":
            print("only the user approves a proposal (--by user), after reading proposal.md")
            return 1
        st["approval"] = {"by": a.by, "at": _dt.datetime.now().isoformat(timespec="seconds"), "sha256": h, "note": a.note}
        st["phase"] = "generate"
    elif a.cmd == "approved":
        ok, why = is_approved(a.run_dir)
        print(why)
        return 0 if ok else 1
    elif a.cmd == "layer":
        if a.layer not in st["layers"]:
            st["layers"].append(a.layer)
    st["history"].append({"at": _dt.datetime.now().isoformat(timespec="seconds"), "cmd": a.cmd,
                          "arg": getattr(a, "phase", None) or getattr(a, "layer", None) or ""})
    save(a.run_dir, st)
    print(f"{a.cmd}: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
