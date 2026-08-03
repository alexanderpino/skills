#!/usr/bin/env python3
"""Gate runner — run a story's full evidence set in one command.

Every story in this project has to show the same thing: the oracle green, and EVERY declared
mutation red for a NAMED gate. Doing that by hand is a dozen commands per story and it is easy to
skim the output and see what you hoped for. This runs the set and reports it as a table.

It is deliberately strict about the two ways a mutation run can lie:

  NOT ARMED   the mutated run exited 0 — the mutation changed nothing the gate can see
  VACUOUS     the oracle printed its own "was not detected" line, meaning the mutation only
              tripped the safety net rather than a real gate

Both are failures. A mutation that cannot turn a named gate red is worse than no mutation, because
it reads as coverage. Eight of those have already been found in this codebase; this makes the check
cheap enough that there is no excuse for skipping it.

Usage
  python scripts/gate.py --oracle _verify_flow_control.js      green + every declared mutation
  python scripts/gate.py --oracle a.js --oracle b.js           several oracles
  python scripts/gate.py --core                                plugins/digest/bridge/build
  python scripts/gate.py --core --oracle _verify_doctrine.js   both
  python scripts/gate.py --sweep                               the full wave gate
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
NPM = "npm.cmd" if sys.platform == "win32" else "npm"

GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def run(cmd, timeout=1800):
    started = time.time()
    p = subprocess.run(cmd, cwd=APP, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, shell=False)
    return p.returncode, (p.stdout or "") + (p.stderr or ""), time.time() - started


def declared_mutations(oracle):
    """Read the MUTATIONS allowlist out of the oracle itself, so the runner cannot drift from it."""
    src = (APP / "tests" / "legacy" / oracle).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"const MUTATIONS\s*=\s*\[(.*?)\n\]", src, re.S)
    if not m:
        return []
    # Strip the trailing // comment on each entry BEFORE extracting the quoted name. Every mutation
    # in this suite is documented with a trailing comment, and those comments contain apostrophes
    # ("the story's named failure"), which a naive quote-scan happily reads as mutation names. The
    # first version of this parser did exactly that and tried to run three phantom mutations.
    names = []
    for line in m.group(1).splitlines():
        code = re.split(r"//", line, 1)[0].strip()
        found = re.findall(r"['\"]([^'\"]+)['\"]", code)
        names.extend(found)
    return names


def verdict_line(output):
    for line in output.splitlines():
        if line.startswith("PASS ") or line.startswith("FAIL "):
            return line.strip()
    return ""


def failed_gates(output):
    m = re.search(r"failed=\[([^\]]*)\]", output)
    return [g for g in (m.group(1).split(",") if m else []) if g]


def check_oracle(oracle):
    """Green run plus every declared mutation. Returns (ok, rows)."""
    rows = []
    code, out, secs = run([NPM, "run", "verify", "--", oracle])
    line = verdict_line(out)
    green_ok = code == 0
    rows.append(("green", green_ok, f"{secs:.0f}s", line[:120] if line else f"exit {code}"))
    if not green_ok and not line:
        # A parse/setup failure produces no verdict line at all; surface the tail so it is not silent.
        rows.append(("green:detail", False, "", " | ".join(out.strip().splitlines()[-3:])[:160]))

    muts = declared_mutations(oracle)
    if not muts:
        # Absence of evidence is failure: an oracle with no declared mutation has no armed control.
        rows.append(("mutations", False, "", "no MUTATIONS allowlist declared — this gate has no armed control"))
        return False, rows

    all_armed = True
    for name in muts:
        code, out, secs = run([NPM, "run", "verify", "--", oracle, f"--mutate={name}"])
        if "was not detected" in out:
            status, note = False, "VACUOUS — tripped the safety net, not a gate"
        elif code == 0:
            status, note = False, "NOT ARMED — mutated run exited 0"
        else:
            gates = failed_gates(out)
            status = bool(gates)
            note = ("red: " + ",".join(gates)) if gates else "red but named no gate"
        all_armed = all_armed and status
        rows.append((f"mutate:{name}", status, f"{secs:.0f}s", note[:120]))
    return green_ok and all_armed, rows


CORE = [
    ("plugins:check", [NPM, "run", "plugins:check"], None),
    ("digest", [NPM, "run", "verify", "--", "_verify_digest.js"], r"covered (\d+)/(\d+) registered node types, skipped (\d+)"),
    ("bridge:check", [NPM, "run", "bridge:check"], r"PASS: live surface matches .*\((\d+) symbols\)"),
    ("build", ["npx.cmd" if sys.platform == "win32" else "npx", "vite", "build"], r"built in ([\d.]+\w+)"),
]


def check_core():
    rows, ok = [], True
    for name, cmd, pattern in CORE:
        code, out, secs = run(cmd)
        detail = ""
        if pattern:
            m = re.search(pattern, out)
            detail = " ".join(m.groups()) if m else "(no reading found)"
            if not m:
                code = code or 1                       # a missing reading is not a pass
        rows.append((name, code == 0, f"{secs:.0f}s", detail))
        ok = ok and code == 0
    return ok, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle", action="append", default=[])
    ap.add_argument("--core", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()
    if not (args.oracle or args.core or args.sweep):
        ap.error("nothing to do: pass --oracle, --core or --sweep")

    overall, sections = True, []
    if args.core:
        ok, rows = check_core()
        sections.append(("core gates", rows)); overall = overall and ok
    for oracle in args.oracle:
        ok, rows = check_oracle(oracle)
        sections.append((oracle, rows)); overall = overall and ok
    if args.sweep:
        code, out, secs = run([NPM, "run", "verify:all"], timeout=5400)
        m = re.search(r"(\d+)/(\d+) green", out)
        inv = re.search(r"discovered=(\d+) declared=(\d+) started=(\d+) completed=(\d+) skipped=(\d+)", out)
        detail = (m.group(0) if m else "(no green count)") + (" | " + inv.group(0) if inv else "")
        # A sweep that reported no counts proves nothing, whatever it exited with.
        ok = code == 0 and bool(m) and bool(inv)
        sections.append(("wave sweep", [("sweep", ok, f"{secs:.0f}s", detail)]))
        overall = overall and ok

    print()
    for title, rows in sections:
        print(f"{BOLD}{title}{RESET}")
        for name, ok, secs, note in rows:
            mark = f"{GREEN}ok  {RESET}" if ok else f"{RED}FAIL{RESET}"
            print(f"  {mark} {name:<34} {DIM}{secs:>5}{RESET}  {note}")
        print()
    print(f"{(GREEN + 'ALL GATES GREEN') if overall else (RED + 'GATES FAILED')}{RESET}\n")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
