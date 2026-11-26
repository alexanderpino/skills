#!/usr/bin/env python3
"""Resolve the studio's effective configuration and say where every value came from.

    python3 .claude/scripts/resolve_config.py                 # every key
    python3 .claude/scripts/resolve_config.py --keys modes.review_mode,stack.code_root
    python3 .claude/scripts/resolve_config.py --get modes.workflow   # the bare value only
    python3 .claude/scripts/resolve_config.py --validate      # notes on invalid values only

Lookup order, first hit wins:
  1. project.local.yaml  (personal, gitignored — only the keys in LOCAL_KEYS)
  2. project.yaml        (team-wide)
  3. modes.rigor fan-out (for the knobs rigor controls)
  4. stack row in .claude/docs/stacks.tsv (for stack.code_root / stack.test_root / commands)
  5. the default below

A value outside its allowed list is SKIPPED (never coerced) and named on a `notes:` line;
the lookup then continues with the next source. A key no source can give prints
`NOT ASSESSED (<reason>)`, never a guess.

This script reports; it never fails the caller: the exit code is always 0.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mini_yaml  # noqa: E402

ROOT = os.environ.get("STUDIO_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

ENUMS = {
    "modes.rigor": ["minimal", "standard", "full"],
    "modes.workflow": ["minimal", "standard", "full"],
    "modes.docs_density": ["terse", "balanced", "thorough"],
    "modes.qa_level": ["minimal", "standard", "full"],
    "modes.review_mode": ["solo", "lean", "full"],
    "modes.automation": ["ask", "guided", "autonomous"],
}
DEFAULTS = {
    "modes.rigor": "minimal",
    "modes.automation": "ask",
}
FANOUT = {
    "minimal": {"modes.workflow": "minimal", "modes.docs_density": "terse",
                "modes.qa_level": "minimal", "modes.review_mode": "solo"},
    "standard": {"modes.workflow": "standard", "modes.docs_density": "balanced",
                 "modes.qa_level": "standard", "modes.review_mode": "lean"},
    "full": {"modes.workflow": "full", "modes.docs_density": "thorough",
             "modes.qa_level": "full", "modes.review_mode": "full"},
}
LOCAL_KEYS = {"modes.review_mode", "modes.automation"}
FREE_KEYS = ["project.name", "project.goal", "project.stage", "stack.name",
             "stack.code_root", "stack.test_root", "commands.build", "commands.test", "commands.run"]
ALL_KEYS = list(ENUMS) + FREE_KEYS
STACK_COLUMNS = {"stack.code_root": "code_root", "stack.test_root": "test_root",
                 "commands.build": "build", "commands.test": "test", "commands.run": "run"}


def _load(name: str, notes: list[str]):
    path = os.path.join(ROOT, name)
    if not os.path.exists(path):
        return None
    try:
        return mini_yaml.load(path)
    except mini_yaml.MiniYamlError as e:
        notes.append(f"{name} could not be read ({e}); its values were not used")
        return None


def stack_rows(notes: list[str]) -> dict[str, dict]:
    path = os.path.join(ROOT, ".claude", "docs", "stacks.tsv")
    if not os.path.exists(path):
        notes.append(".claude/docs/stacks.tsv is missing; stack rows unavailable")
        return {}
    rows = {}
    with open(path, encoding="utf-8") as fh:
        lines = [l for l in fh if l.strip() and not l.startswith("#")]
    for r in csv.DictReader(lines, delimiter="\t"):
        rows[r["stack"]] = {k: (None if v in ("-", "", None) else v) for k, v in r.items()}
    return rows


def resolve() -> tuple[dict[str, tuple[object, str]], list[str]]:
    notes: list[str] = []
    local = _load("project.local.yaml", notes) or {}
    team = _load("project.yaml", notes)
    if team is None and not os.path.exists(os.path.join(ROOT, "project.yaml")):
        notes.append("project.yaml is missing; run /start")
    team = team or {}
    out: dict[str, tuple[object, str]] = {}

    def from_files(key: str):
        for src_name, data in (("project.local.yaml", local), ("project.yaml", team)):
            if src_name == "project.local.yaml" and key not in LOCAL_KEYS:
                if mini_yaml.get(data, key) is not None:
                    notes.append(f"project.local.yaml sets {key}, which is team-wide only; ignored")
                continue
            v = mini_yaml.get(data, key)
            if v is None:
                continue
            if key in ENUMS and v not in ENUMS[key]:
                notes.append(f"{src_name}: {key}={v!r} is not one of {'|'.join(ENUMS[key])}; skipped")
                continue
            return v, src_name
        return None

    rigor = from_files("modes.rigor") or (DEFAULTS["modes.rigor"], "default")
    out["modes.rigor"] = rigor
    for key in ENUMS:
        if key == "modes.rigor":
            continue
        hit = from_files(key)
        if hit:
            out[key] = hit
        elif key in FANOUT[rigor[0]]:
            out[key] = (FANOUT[rigor[0]][key], f"modes.rigor={rigor[0]}")
        elif key in DEFAULTS:
            out[key] = (DEFAULTS[key], "default")
    rows = stack_rows(notes)
    for key in FREE_KEYS:
        hit = from_files(key)
        if hit:
            out[key] = hit
            continue
        if key in STACK_COLUMNS:
            name = out.get("stack.name", (None,))[0]
            if not name:
                out[key] = (None, "NOT ASSESSED (stack.name is not set)")
            elif name not in rows:
                out[key] = (None, f"NOT ASSESSED (stack {name!r} has no row in stacks.tsv)")
            elif rows[name].get(STACK_COLUMNS[key]) is None:
                out[key] = (None, f"NOT ASSESSED (stacks.tsv row {name!r} leaves it empty)")
            else:
                out[key] = (rows[name][STACK_COLUMNS[key]], f"stacks.tsv row {name}")
        else:
            out[key] = (None, "unset")
    if out.get("stack.name", (None,))[0] and out["stack.name"][0] not in rows and rows:
        notes.append(f"stack.name={out['stack.name'][0]!r} is not a row of stacks.tsv")
    return out, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keys", help="comma-separated keys to print")
    ap.add_argument("--get", help="print only this key's bare value (empty when unset)")
    ap.add_argument("--validate", action="store_true", help="print only the notes")
    a = ap.parse_args(argv)
    values, notes = resolve()
    if a.get:
        v = values.get(a.get, (None, ""))[0]
        print("" if v is None else v)
        return 0
    if not a.validate:
        keys = [k.strip() for k in a.keys.split(",")] if a.keys else ALL_KEYS
        print("=== Resolved config ===")
        for k in keys:
            if k not in values:
                print(f"{k} = NOT ASSESSED (unknown key)")
                continue
            v, src = values[k]
            print(f"{k} = {'' if v is None else v}  ({src})")
    for n in notes:
        print(f"notes: {n}")
    if a.validate and not notes:
        print("notes: none")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # report, never fail the caller
        print(f"notes: resolve_config.py could not run ({e.__class__.__name__}: {e})")
        sys.exit(0)
