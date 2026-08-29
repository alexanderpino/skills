#!/usr/bin/env python3
"""fanout.py — deterministic run state for the fan-out skill.

No model calls, no network. Its job is to make the silent failure modes loud (a mutated
shared brief; a verification round that re-reviews approved code) and to give every agent
a stable set of paths.

    fanout.py init "<task>" --mode compete --n 4
    fanout.py seal                            # hash brief.md + rubric.md
    fanout.py check                           # fail if either changed since seal

    fanout.py plan                            # coupling between proposed slices

    fanout.py snapshot <slice> <path>...      # record the bytes under review
    fanout.py scope <slice>                   # in-scope diff / re-opened / out of scope
    fanout.py gate <slice>                    # 0 done, 1 another round, 2 escalate

    fanout.py status                          # candidates, verdicts, open findings
"""

import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".fan-out")
SEALED = ("brief.md", "rubric.md")
BLOCKING = ("blocker", "major")
UNRESOLVED = ("open", "unresolved")   # waived and verified do not block
MAX_ROUNDS = 2

# Language keywords. These are never meaningful as names, not even in a definition
# position, where a loose regex can otherwise mistake `if (x)` for a function called `if`.
KEYWORDS = frozenset("""
    int uint float double bool char void const static inline return if else while for
    class struct enum union template typename namespace public private protected virtual
    override final auto using typedef sizeof nullptr true false new delete throw catch
    try def import from lambda self none pass raise yield async await elif print
    let var function export default require module interface extends implements
""".split())

# Generic vocabulary. Too common to signal coupling when it merely appears in a changed
# line — but NOT filtered from definition names: a method genuinely called `Get` or `Add`
# is a real dependency edge, and dropping it would make `scope` miss a re-open, which is
# the one error this design cannot afford.
COMMON = frozenset("""
    the and for not with this that from have has was were will you your are but its
    size data value index count name list dict set get add remove init main test result
    str len type
""".split())

STOPWORDS = KEYWORDS | COMMON

# Keywords that open a statement rather than a definition. A line starting with one of
# these never defines anything, whatever shape the rest of it has.
STATEMENT_KEYWORDS = frozenset("""
    return if elif else while for switch case do throw raise yield assert
    print del with break continue import from pass await goto
""".split())

BRIEF_TEMPLATE = """# Brief

<!-- SHARED CONTEXT. Byte-identical for every builder AND every critic.
     No agent names, no slice IDs, no timestamps, no run IDs. If it differs
     between agents it goes in the per-agent delta, not here. -->

## Goal

{task}

## Constraints

-

## Context

<!-- Paths, excerpts, specs, conventions. Everything the agents would otherwise
     each go rediscover on their own. -->

## Visual surface

<!-- Only if there is something to look at: a page, chart, UI state, frame, diagram,
     laid-out document. Give ONE render command and the exact state to render in —
     viewport, seed, theme, sample input, which page. Identical for every agent, or
     the candidates are not comparable. Builders write output to
     renders/<slice-id>/r1/; critics judge that, not the source behind it.
     Delete this section if the work has no visual surface — an invented one costs a
     round and proves nothing. -->

## Acceptance criteria

<!-- Concrete and checkable. "Works well" is not a criterion. -->

-

## Definition of done

-
"""

RUBRIC_TEMPLATE = """# Rubric

<!-- Written BEFORE any builder runs. A rubric written afterwards is a
     rationalisation of the candidate you already liked. -->

## Axes (score 1-5)

<!-- If the brief names a visual surface, at least one axis must be scoreable ONLY
     from the render. Otherwise critics score the source that produces the picture. -->

### <axis-name>
What 5 looks like:
What 1 looks like:
Concrete failure example:

## Blocking conditions

<!-- Any one of these forces verdict=reject regardless of scores. -->

-
"""


# ---------------------------------------------------------------- helpers

def run_dir() -> Path:
    if not ROOT.exists():
        sys.exit("no .fan-out/ directory — run `fanout.py init` first")
    runs = sorted(d for d in ROOT.iterdir() if d.is_dir())
    if not runs:
        sys.exit("no runs found — run `fanout.py init` first")
    return runs[-1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revisions(d: Path, slice_id: str) -> list:
    base = d / "revisions" / slice_id
    if not base.exists():
        return []
    return sorted(base.glob("v*"), key=lambda p: int(p.name[1:]))


def read_text(path: Path) -> list:
    try:
        return path.read_text(errors="replace").splitlines()
    except OSError:
        return []


def identifiers(lines) -> set:
    out = set()
    for line in lines:
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", line):
            if tok.lower() not in STOPWORDS:
                out.add(tok)
    return out


# A change inside a function body must re-open that function's *callers*, and the
# callee's name never appears in the changed lines themselves. So walk back to the
# enclosing definition and add its name to the touched set. Portable heuristics only.
DEF_PATTERNS = (
    re.compile(r"([A-Za-z_][A-Za-z0-9_]*)::([A-Za-z_~][A-Za-z0-9_]*)\s*\("),   # C++ qualified
    re.compile(r"^\s*(?:def|class|fn|func|impl|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    # C-family. The leading type/qualifier is required: without it a bare call statement
    # like `doThing(x)` reads as a definition, which would credit the caller as the definer
    # and cancel the very dependency edge `plan` exists to find.
    re.compile(r"^\s{0,4}[A-Za-z_][\w:<>,&*\s]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)"
               r"\s*(?:const\s*)?(?:noexcept\s*)?\{?\s*$"),
    re.compile(r"^#{1,6}\s+(.+?)\s*$"),                                        # markdown
)


def enclosing_symbols(lines, idx: int, lookback: int = 300) -> set:
    """Names of the definition containing line `idx`, searching upward."""
    for i in range(min(idx, len(lines) - 1), max(-1, idx - lookback), -1):
        line = lines[i]
        # `return Store().get(s)` otherwise matches the C-family shape and turns a call
        # site into a definition. A statement opening with a keyword never defines.
        head = line.strip().split("(")[0].split()
        if head and head[0].lower() in STATEMENT_KEYWORDS:
            continue
        for pat in DEF_PATTERNS:
            if m := pat.search(line):
                names = {g for g in m.groups() if g}
                out = set()
                for n in names:
                    out |= {t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", n)
                            if t.lower() not in KEYWORDS}
                if out:
                    return out
    return set()


def definitions(lines) -> set:
    """Symbols this file defines — the ones whose change re-opens every caller."""
    out = set()
    for i in range(len(lines)):
        out |= enclosing_symbols(lines, i, lookback=1)
    return out


def load_verdict(d: Path, slice_id: str) -> dict:
    p = d / "verdicts" / f"{slice_id}.json"
    if not p.exists():
        sys.exit(f"no verdict yet for '{slice_id}' — critics must run first")
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"verdict for '{slice_id}' is not valid JSON: {e}")


# ---------------------------------------------------------------- commands

def cmd_init(args) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", args.task.lower())[:40].strip("-") or "run"
    d = ROOT / f"{stamp}-{slug}"
    (d / "candidates").mkdir(parents=True)
    (d / "verdicts").mkdir()
    (d / "revisions").mkdir()
    (d / "renders").mkdir()

    (d / "brief.md").write_text(BRIEF_TEMPLATE.format(task=args.task))
    (d / "rubric.md").write_text(RUBRIC_TEMPLATE)
    (d / "run.json").write_text(
        json.dumps(
            {"task": args.task, "mode": args.mode, "n": args.n,
             "max_rounds": args.max_rounds, "created": stamp},
            indent=2,
        ) + "\n"
    )

    print(f"run:    {d}")
    print(f"mode:   {args.mode}   n: {args.n}   max verification rounds: {args.max_rounds}")
    print(f"brief:  {d / 'brief.md'}")
    print(f"rubric: {d / 'rubric.md'}")
    print("\nFill both, then: fanout.py seal")


def cmd_seal(args) -> None:
    d = run_dir()
    lock = {name: digest(d / name) for name in SEALED}
    (d / "seal.json").write_text(json.dumps(lock, indent=2) + "\n")
    for name, h in lock.items():
        print(f"sealed {name}  {h[:12]}")
    print("\nBrief is now immutable. Per-agent text goes below the '---' separator.")


def cmd_check(args) -> None:
    d = run_dir()
    lock_path = d / "seal.json"
    if not lock_path.exists():
        sys.exit("not sealed — run `fanout.py seal` before spawning agents")
    lock = json.loads(lock_path.read_text())
    drift = [n for n, h in lock.items() if digest(d / n) != h]
    if drift:
        print("DRIFT: " + ", ".join(drift), file=sys.stderr)
        print(
            "\nThe shared block changed mid-run. Agents spawned before and after this\n"
            "edit worked from different ground truths, so their outputs are not\n"
            "comparable and the cached prefix is dead. Finish this round, then start a\n"
            "new sealed run with the corrected brief.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("clean — brief and rubric unchanged since seal")


def cmd_snapshot(args) -> None:
    """Record the exact bytes under review. Must run BEFORE the builder edits."""
    d = run_dir()
    n = len(revisions(d, args.slice)) + 1
    dest = d / "revisions" / args.slice / f"v{n}"
    dest.mkdir(parents=True)

    manifest = {}
    for raw in args.paths:
        src = Path(raw)
        if not src.exists():
            shutil.rmtree(dest)
            sys.exit(f"missing: {src}")
        key = hashlib.sha256(str(src.resolve()).encode()).hexdigest()[:12]
        shutil.copy2(src, dest / key)
        manifest[key] = {"path": str(src), "sha": digest(src)}

    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"snapshot {args.slice} v{n}  ({len(manifest)} file(s))")
    for meta in manifest.values():
        print(f"  {meta['sha'][:12]}  {meta['path']}")
    if n == 1:
        print("\nThis is the baseline. Snapshot again after the builder's fix, then `scope`.")


def cmd_scope(args) -> None:
    """Partition the artifact into in-scope / re-opened / out-of-scope."""
    d = run_dir()
    revs = revisions(d, args.slice)
    if len(revs) < 2:
        sys.exit(
            f"need two snapshots of '{args.slice}' to compute a delta (have {len(revs)}).\n"
            "Snapshot before the builder's fix and again after."
        )
    old, new = revs[-2], revs[-1]
    old_m = json.loads((old / "manifest.json").read_text())
    new_m = json.loads((new / "manifest.json").read_text())

    changed, unchanged, touched = [], [], set()

    for key, meta in new_m.items():
        prev = old_m.get(key)
        if prev is None:
            changed.append((meta["path"], ["(new file)"]))
            touched |= identifiers(read_text(new / key))
            continue
        if prev["sha"] == meta["sha"]:
            unchanged.append((meta["path"], key))
            continue

        a, b = read_text(old / key), read_text(new / key)
        hunks, delta = [], []
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
            if op == "equal":
                continue
            enclosing = enclosing_symbols(b, j1) | enclosing_symbols(a, i1)
            label = f"lines {j1 + 1}-{max(j2, j1 + 1)} ({op})"
            if enclosing:
                label += f"  in {'/'.join(sorted(enclosing))}"
            hunks.append(label)
            delta += a[i1:i2] + b[j1:j2]
            touched |= enclosing
        changed.append((meta["path"], hunks))
        touched |= identifiers(delta)

    for key, meta in old_m.items():
        if key not in new_m:
            changed.append((meta["path"], ["(removed)"]))

    print(f"scope for {args.slice}   {old.name} -> {new.name}")
    print(f"\nIN SCOPE — changed, review fully ({len(changed)}):")
    for path, hunks in changed or [("(nothing changed)", [])]:
        print(f"  {path}")
        for h in hunks:
            print(f"      {h}")

    reopened, clear = [], []
    for path, key in unchanged:
        body = read_text(new / key)
        hits = sorted({s for s in touched
                       if any(re.search(rf"\b{re.escape(s)}\b", ln) for ln in body)})
        (reopened if hits else clear).append((path, hits))

    print(f"\nRE-OPENED — unchanged but reference a touched symbol ({len(reopened)}):")
    print("  Ask only: did this change break you? Not a fresh general review.")
    for path, hits in reopened or [("(none)", [])]:
        print(f"  {path}")
        if hits:
            print(f"      via: {', '.join(hits[:6])}{' ...' if len(hits) > 6 else ''}")

    print(f"\nOUT OF SCOPE — do not read ({len(clear)}):")
    for path, _ in clear or [("(none)", [])]:
        print(f"  {path}")

    approved = load_verdict(d, args.slice).get("approved", [])
    if approved:
        print(f"\nprior approvals on record: {len(approved)}")
    print(f"\ntouched symbols: {len(touched)}")
    print("Re-opening over-approximates on purpose; a false re-open costs tokens, a\n"
          "missed one ships a regression. Overrule sparingly and note it in the fold.")


def cmd_gate(args) -> None:
    """Stop condition. 0 = done, 1 = another round, 2 = escalate."""
    d = run_dir()
    meta = json.loads((d / "run.json").read_text())
    cap = meta.get("max_rounds", MAX_ROUNDS)
    verdict = load_verdict(d, args.slice)
    findings = verdict.get("findings", [])
    rnd = verdict.get("round", 1)

    def bucket(sev):
        return [f for f in findings
                if f.get("severity") == sev and f.get("status", "open") in UNRESOLVED]

    blocking = [f for sev in BLOCKING for f in bucket(sev)]
    deferred = [f for sev in ("minor", "nit") for f in bucket(sev)]
    late = [f for f in findings if f.get("late")]
    verified = [f for f in findings if f.get("status") == "verified"]
    waived = [f for f in findings if f.get("status") == "waived"]

    print(f"gate {args.slice}   round {rnd}/{cap + 1}")
    print(f"  verified:  {len(verified)}")
    print(f"  blocking:  {len(blocking)}   (blocker/major still open)")
    print(f"  deferred:  {len(deferred)}   (minor/nit — follow-ups, never block)")
    if waived:
        print(f"  waived:    {len(waived)}   (shipped as known issues)")
        for f in waived:
            reason = f.get("reason")
            print(f"      {f.get('id')}: {reason or 'NO REASON GIVEN — record one'}")
    if late:
        print(f"  late:      {len(late)}   (raised outside scope — round 1 under-reviewed)")

    for f in blocking:
        anchor = f.get("anchor", {})
        where = anchor.get("symbol") or anchor.get("file") or "?"
        print(f"\n  [{f.get('severity')}] {f.get('id')}  {where}")
        print(f"      claim: {f.get('claim', '')}")
        print(f"      check: {f.get('check', '')}")
        if reason := f.get("reason"):
            print(f"      reason: {reason}")

    if not blocking:
        print("\nPASS — no open blockers or majors.")
        if deferred:
            print("Carry the deferred findings into the fold report as follow-ups.")
        sys.exit(0)

    if rnd > cap:
        print(f"\nESCALATE — {rnd - 1} verification rounds spent, still blocking.")
        print("Three attempts failing points at the brief or the slice cut, not the\n"
              "builder. Take the disagreement to the user rather than spawning another.")
        sys.exit(2)

    print("\nANOTHER ROUND — snapshot, send only these findings, then `scope`.")
    sys.exit(1)


def cmd_plan(args) -> None:
    """Measure coupling between proposed slices. Cut where coupling is weakest.

    Three tiers, strongest first. The first two are categorical — they are not
    heuristics but restatements of rules the run already enforces elsewhere.
    """
    d = run_dir()
    spec = d / "slices.json"
    if not spec.exists():
        sys.exit(
            f"no {spec}. Create it as:\n"
            '  {"slices": [{"id": "ecs-query", "summary": "...",\n'
            '               "files": ["src/ecs/query.cpp", "src/ecs/store.h"]}]}\n'
            "List the files each slice would touch — that is what coupling is measured on."
        )
    slices = json.loads(spec.read_text()).get("slices", [])
    if len(slices) < 2:
        sys.exit("need at least two slices to measure coupling")

    defs, uses, files = {}, {}, {}
    for s in slices:
        paths = [Path(p) for p in s.get("files", [])]
        if missing := [str(p) for p in paths if not p.exists()]:
            print(f"  warn: {s['id']} lists missing path(s): {', '.join(missing)}",
                  file=sys.stderr)
        body, defined = [], set()
        for p in paths:
            lines = read_text(p)
            body += lines
            defined |= definitions(lines)
        defs[s["id"]] = defined
        uses[s["id"]] = identifiers(body)
        files[s["id"]] = {str(p) for p in paths}

    # Vocabulary shared by every slice discriminates nothing; keep the rare names.
    spread = {}
    for names in uses.values():
        for n in names:
            spread[n] = spread.get(n, 0) + 1
    cutoff = max(2, len(slices) // 2)
    rare = {sid: {n for n in names if spread[n] <= cutoff} for sid, names in uses.items()}

    rows, edges = [], []
    for a, b in ((slices[i], slices[j])
                 for i in range(len(slices)) for j in range(i + 1, len(slices))):
        ia, ib = a["id"], b["id"]
        shared_files = files[ia] & files[ib]

        # A defines it, B calls it: changing A re-opens B. This is not a guess — it is
        # exactly the rule `scope` applies, run before the fact instead of after.
        dep_ab = defs[ia] & uses[ib] - defs[ib]
        dep_ba = defs[ib] & uses[ia] - defs[ia]

        vocab = (rare[ia] & rare[ib]) - defs[ia] - defs[ib]
        floor = min(len(rare[ia]), len(rare[ib])) or 1
        ratio = len(vocab) / floor

        if shared_files:
            tier, detail = "WRITE", f"shared write targets: {', '.join(sorted(shared_files))}"
        elif dep_ab or dep_ba:
            arrows = []
            if dep_ab:
                arrows.append(f"{ia} -> {ib} via {', '.join(sorted(dep_ab)[:4])}")
            if dep_ba:
                arrows.append(f"{ib} -> {ia} via {', '.join(sorted(dep_ba)[:4])}")
            tier, detail = "DEP", "; ".join(arrows)
        elif ratio >= args.threshold:
            shown = sorted(vocab)[:6]
            tier = "VOCAB"
            detail = f"shared rare symbols: {', '.join(shown)}{' ...' if len(vocab) > 6 else ''}"
        else:
            tier, detail = "", f"vocabulary overlap {ratio:.2f}"

        rows.append((tier, ratio, ia, ib, detail))
        if tier in ("WRITE", "DEP", "VOCAB"):
            edges.append((ia, ib))

    order = {"WRITE": 0, "DEP": 1, "VOCAB": 2, "": 3}
    rows.sort(key=lambda r: (order[r[0]], -r[1]))

    print(f"coupling across {len(slices)} proposed slices "
          f"(vocabulary threshold {args.threshold:.2f})\n")
    print("  WRITE  same file — violates slice disjointness, merge")
    print("  DEP    one defines what the other calls — revising either re-opens the "
          "other, merge")
    print("  VOCAB  shared rare names only — advisory, judge it yourself\n")
    for tier, _, ia, ib, detail in rows:
        if not tier:
            continue
        print(f"  {tier:<6} {ia} <-> {ib}")
        print(f"         {detail}")
    if quiet := [r for r in rows if not r[0]]:
        top = max(quiet, key=lambda r: r[1])
        print(f"  --     {len(quiet)} pair(s) below threshold "
              f"(highest {top[1]:.2f}: {top[2]} <-> {top[3]})")

    # Coupling is transitive here: if A must merge with B and B with C, splitting A
    # from C still cascades re-opens through B.
    group = {s["id"]: s["id"] for s in slices}

    def root(x):
        while group[x] != x:
            group[x] = group[group[x]]
            x = group[x]
        return x

    for ia, ib in edges:
        ra, rb = root(ia), root(ib)
        if ra != rb:
            group[rb] = ra

    clusters = {}
    for s in slices:
        clusters.setdefault(root(s["id"]), []).append(s["id"])

    print(f"\nsuggested grouping — N = {len(clusters)} (proposed {len(slices)}):")
    for members in clusters.values():
        print(f"  {'MERGE  ' if len(members) > 1 else '       '}{' + '.join(members)}")

    if len(clusters) == 1 and len(slices) > 1:
        print("\nEverything collapsed into one group. Either the work is more coupled\n"
              "than the proposed cut admits, or this is not fan-out work at all.")
    elif len(clusters) < len(slices):
        print("\nSplitting a merged pair means two agents rebuilding the same model, and\n"
              "every later revision re-opening the other's approved regions. Merge unless\n"
              "the combined slice no longer fits one working set.")
    else:
        print("\nNo coupling above threshold — the cut is clean.")


def cmd_status(args) -> None:
    d = run_dir()
    meta = json.loads((d / "run.json").read_text())
    cands = sorted(p.stem for p in (d / "candidates").glob("*") if p.is_file())
    verds = sorted(p.stem for p in (d / "verdicts").glob("*.json"))

    print(f"run:    {d}")
    print(f"task:   {meta['task']}")
    print(f"mode:   {meta['mode']}   expected: {meta['n']}")
    print(f"sealed: {'yes' if (d / 'seal.json').exists() else 'NO'}")
    print(f"\ncandidates ({len(cands)}): {', '.join(cands) or '-'}")
    print(f"verdicts   ({len(verds)}): {', '.join(verds) or '-'}")

    if missing := [c for c in cands if c not in verds]:
        print(f"\nawaiting critique: {', '.join(missing)}")

    if verds:
        print("\nverdicts:")
        for name in verds:
            try:
                v = json.loads((d / "verdicts" / f"{name}.json").read_text())
            except (json.JSONDecodeError, OSError):
                print(f"  {name:<20} unreadable")
                continue
            findings = v.get("findings", [])
            blocking = sum(1 for f in findings
                           if f.get("severity") in BLOCKING
                           and f.get("status", "open") in UNRESOLVED)
            revs = len(revisions(d, name))
            print(f"  {name:<20} {v.get('verdict', '?'):<8} "
                  f"round {v.get('round', 1)}  "
                  f"blocking {blocking}/{len(findings)}  snapshots {revs}")


# ---------------------------------------------------------------- cli

def main() -> None:
    p = argparse.ArgumentParser(prog="fanout.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="create a run directory")
    i.add_argument("task")
    i.add_argument("--mode", choices=["partition", "compete"], default="compete")
    i.add_argument("--n", type=int, default=4,
                   help="expected slice count — a hint; `plan` determines the real one")
    i.add_argument("--max-rounds", type=int, default=MAX_ROUNDS,
                   help="verification rounds before escalating (default 2)")
    i.set_defaults(func=cmd_init)

    pl = sub.add_parser("plan", help="coupling between proposed slices")
    pl.add_argument("--threshold", type=float, default=0.35,
                    help="merge slices coupled at or above this (default 0.35)")
    pl.set_defaults(func=cmd_plan)

    s = sub.add_parser("snapshot", help="record the bytes under review")
    s.add_argument("slice")
    s.add_argument("paths", nargs="+")
    s.set_defaults(func=cmd_snapshot)

    for name, fn, helptext, needs_slice in (
        ("seal", cmd_seal, "hash brief + rubric", False),
        ("check", cmd_check, "fail if the shared block drifted", False),
        ("scope", cmd_scope, "in-scope / re-opened / out-of-scope", True),
        ("gate", cmd_gate, "stop condition for a slice", True),
        ("status", cmd_status, "candidates, verdicts, open findings", False),
    ):
        sp = sub.add_parser(name, help=helptext)
        if needs_slice:
            sp.add_argument("slice")
        sp.set_defaults(func=fn)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    # Agents pipe this output; a truncated pipe is not an error.
    try:
        main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
