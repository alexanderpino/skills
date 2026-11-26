#!/usr/bin/env python3
"""Trial-run a generated studio: pick what to try, and print a ready brief for each.

    trial.py pick TARGET     # the files to trial, one per line (validate.py V26 uses the same pick)
    trial.py brief TARGET    # a brief per pick: the file's text, a sample task, the expected shape

Every check before this one reads files; this one uses them. The pick is deterministic, so a
re-run trials the same files and validate.py can tell whether all of them were covered:

  gate   the owner of the first gate (by id) that was generated — does it answer a gate run
         with the verdict token on line one, using only that gate's words?
  agent  the first generated specialist whose workflow is `implementation` — does it follow
         its `### When You Are Spawned` section and return in the order it promises?
  skill  the first catalog step whose command is a generated skill — does it resolve the
         config first and ask "May I write" before writing anything?

The target's agents are not loaded in this session, so each brief carries the file's full
text. Spawn the briefs as general-purpose subagents, all in one message, working in a
SCRATCH COPY of the studio (`cp -r <target> <scratch>`), never in the target itself. Record the
results in <target>/.ssb/trial.md (format in references/validation.md).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proposal as proposalmod  # noqa: E402


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def pick(target: str) -> list[dict]:
    """[{kind, path, ...}] — empty kinds are simply absent (a studio with no gates has no gate trial)."""
    rd = os.path.join(target, ".ssb")
    bp = proposalmod.load(rd)
    out = []
    exists = lambda rel: os.path.exists(os.path.join(target, rel))  # noqa: E731
    for g in sorted(bp.get("gates", []), key=lambda g: g["id"]):
        rel = f".claude/agents/{g['owner']}.md"
        if exists(f".claude/docs/gates/{g['id']}.md") and exists(rel):
            out.append({"kind": "gate", "path": rel, "gate": g["id"], "verdicts": g["verdicts"],
                        "gate_file": f".claude/docs/gates/{g['id']}.md"})
            break
    for r in bp.get("roles", []):
        rel = f".claude/agents/{r['id']}.md"
        if r.get("tier") == "specialist" and r.get("workflow") == "implementation" and exists(rel):
            out.append({"kind": "agent", "path": rel, "role": r["id"]})
            break
    cat = os.path.join(target, ".claude/docs/workflow-catalog.json")
    if os.path.exists(cat):
        for ph in json.loads(_read(cat)).get("phases", []):
            hit = None
            for s in ph.get("steps", []):
                cmd = (s.get("command") or "").lstrip("/").split(" ")[0]
                rel = f".claude/skills/{cmd}/SKILL.md"
                if cmd and exists(rel):
                    hit = {"kind": "skill", "path": rel, "skill": cmd, "step": s["id"]}
                    break
            if hit:
                out.append(hit)
                break
    return out


def brief(target: str, p: dict) -> str:
    text = _read(os.path.join(target, p["path"]))
    head = (f"You are running a TRIAL of one file from a generated Claude Code studio, to see whether an "
            f"agent given only this file can act on it. Work in a scratch copy of the studio: "
            f"`cp -r {target} <scratch>` and use <scratch> as the working directory. Write nothing in {target}.\n\n"
            f"--- the file ({p['path']}) ---\n{text}\n--- end of file ---\n\n")
    if p["kind"] == "gate":
        g = _read(os.path.join(target, p["gate_file"]))
        task = (f"Act as the agent above. You are invoked through gate {p['gate']}. The gate file:\n{g}\n"
                f"The artifact under review is a two-line stub you write yourself in the scratch copy, deliberately "
                f"missing one thing the gate's prompt asks about. Review it.")
        expect = (f"Line one is exactly `{p['gate']}: <word>` with <word> one of {' / '.join(p['verdicts'])} or "
                  f"NOT ASSESSED; the rationale follows; the deliberate gap is found.")
    elif p["kind"] == "agent":
        task = ("Act as the agent above. Your brief: 'Implement a one-function change from a two-sentence story "
                "you invent for this studio's domain; no spec section is given.' Follow the file exactly.")
        expect = ("It follows `### When You Are Spawned`: notices the missing spec input and says "
                  "`NOT ASSESSED — <input>` or asks in one round instead of guessing; its return is in the promised "
                  "order (outcome line, files written, decisions for the user, anything NOT ASSESSED).")
    else:
        task = (f"Act as the session that loaded the skill above (/{p['skill']}). The user typed "
                f"`/{p['skill']}` with a plausible argument. Run its phases in the scratch copy up to the first point "
                f"where it would write a file, and stop there.")
        expect = ("It runs `python3 .claude/scripts/resolve_config.py` first, reads "
                  "`production/session-state/active.md` if present, and asks \"May I write this to <path>?\" before "
                  "any write; it does not write unasked.")
    return (head + "Task: " + task + "\n\nReturn, max 150 words: what you did, the exact first line of your answer "
            "(for a gate), and anything in the file you could not act on.\n\n"
            f"[for the validator — expected shape] {expect}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pick", "brief"])
    ap.add_argument("target")
    a = ap.parse_args(argv)
    target = os.path.abspath(a.target)
    try:
        picks = pick(target)
    except (OSError, ValueError, KeyError) as e:
        print(f"TRIAL: NOT ASSESSED — could not read the studio or its proposal ({e})")
        return 3
    if not picks:
        print("TRIAL: NOT ASSESSED — nothing to trial (no generated gate owner, implementation specialist or "
              "catalog skill)")
        return 3
    for i, p in enumerate(picks, 1):
        if a.cmd == "pick":
            print(f"T{i} {p['kind']:5} {p['path']}")
        else:
            print(f"=== T{i} — {p['kind']} — {p['path']} ===")
            print(brief(target, p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
