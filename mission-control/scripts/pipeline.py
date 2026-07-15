#!/usr/bin/env python3
"""Mission Control pipeline state machine.

Stdlib-only CLI that owns all pipeline state transitions. It enforces legal
transitions, requires the evidence file each gate must have produced, stamps
timestamps, manages the file-ownership ledger, isolates parallel implementers
in git worktrees, and caps per-item bounce cycles. The Orchestrator calls this
instead of editing JSON by hand so the audit trail is structurally guaranteed.

Commands:
  init             create the state directory
  status           queue/ledger/backlog summary + unblock/merge flags
  add-item         append a backlog item
  claim            backlog item -> researching
  transition       move an item between states (evidence-checked, bounce-capped)
  lease            acquire file leases for an item (collision-checked)
  release          release an item's leases
  reclaim          release expired leases and bounce their items to 'approved'
  worktree-add     create an isolated git worktree + branch mc/<id> for an item
  worktree-remove  remove an item's worktree after its branch is merged
  metrics          per-item cost data: state durations, bounces, tokens
  agenda           orchestrator intent journal: add / resolve / list notes
  audit            verify the evidence chain for every done item
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# state -> allowed next states
TRANSITIONS = {
    "backlog": ["researching", "approved"],
    "researching": ["plan-review"],
    "plan-review": ["orchestrator-approval", "approved", "researching", "blocked"],
    "orchestrator-approval": ["approved", "researching", "blocked"],
    "approved": ["building"],
    "building": ["verifying", "blocked"],
    "verifying": ["code-review", "done", "building", "blocked"],
    "code-review": ["done", "building", "blocked"],
    "blocked": ["approved", "researching"],
    "done": [],
}

# evidence file that must exist (relative to evidence/<id>/) before an item
# may LEAVE the keyed state via a forward transition
FORWARD_EVIDENCE = {
    "researching": "research.md",
    "plan-review": "plan-review.json",
    "orchestrator-approval": "approval.json",
    "building": "handoff.md",
    "verifying": "verify.json",
    "code-review": "code-review.json",
}

BOUNCES = {
    ("plan-review", "researching"),
    ("orchestrator-approval", "researching"),
    ("verifying", "building"),
    ("code-review", "building"),
}

BLAST_ORDER = ["low", "medium", "high", "critical"]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_llm_json(path):
    """Robustly parse JSON written by LLMs, stripping markdown blocks."""
    text = path.read_text(encoding="utf-8").strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        raise


class State:
    def __init__(self, root):
        self.root = Path(root)
        self.paths = {
            "mission": self.root / "mission.json",
            "backlog": self.root / "backlog.json",
            "queue": self.root / "queue.json",
            "ledger": self.root / "ledger.json",
            "agenda": self.root / "agenda.json",
            "evidence": self.root / "evidence",
            "worktrees": self.root / "worktrees",
        }

    def load(self, name):
        return json.loads(self.paths[name].read_text())

    def save(self, name, data):
        tmp = self.paths[name].with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        tmp.replace(self.paths[name])

    def evidence_dir(self, item_id):
        return self.paths["evidence"] / item_id

    def item(self, queue, item_id):
        for it in queue["items"]:
            if it["id"] == item_id:
                return it
        die(f"unknown item: {item_id}")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def git(argv, check=True):
    r = subprocess.run(["git"] + argv, capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(argv)} failed: {r.stderr.strip()}")
    return r


def research_header(state, item_id):
    """Parse the YAML-ish header of research.md without a YAML dependency."""
    path = state.evidence_dir(item_id) / "research.md"
    if not path.exists():
        return {}
    header, inside = {}, False
    key = None
    for line in path.read_text().splitlines():
        s = line.strip()
        if s == "---":
            if inside:
                break
            inside = True
            continue
        if not inside:
            continue
        if s.startswith("- ") and key:
            header.setdefault(key, []).append(s[2:].strip())
        elif ":" in s:
            key, _, val = s.partition(":")
            key, val = key.strip(), val.strip()
            header[key] = val if val else []
    return header


def cmd_init(args):
    root = Path(args.root)
    if (root / "mission.json").exists():
        die(f"{root} already initialized — use 'status' to resume")
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    
    # Auto-detect repo oracle
    b_cmd, t_cmd = None, None
    if Path("package.json").exists():
        b_cmd, t_cmd = "npm run build --if-present", "npm test"
    elif Path("Cargo.toml").exists():
        b_cmd, t_cmd = "cargo build", "cargo test"
    elif Path("CMakeLists.txt").exists():
        b_cmd, t_cmd = "cmake -B build && cmake --build build", "ctest --test-dir build"
    elif Path("pytest.ini").exists() or Path("requirements.txt").exists():
        t_cmd = "pytest"

    st = State(root)
    st.save("mission", {
        "goal": args.goal or "TODO: set the mission goal",
        "created": now(),
        "terminal_conditions": {"backlog_drained": True,
                                "max_items_completed": None,
                                "token_budget": None, "deadline": None},
        "concurrency": {"implementers": 2, "scouts": 2},
        "lease_ttl_minutes": 90,
        "bounce_limit": 3,
        "repo_oracle": {"build": b_cmd, "test": t_cmd, "lint": None},
        "gates": {"orchestrator_approval_min_blast": "high",
                  "code_review_min_blast": "medium"},
    })
    st.save("backlog", {"items": []})
    st.save("queue", {"items": []})
    st.save("ledger", {"leases": []})
    st.save("agenda", {"next_id": 1, "notes": []})
    print(f"initialized {root} — edit mission.json (goal, repo_oracle, "
          f"terminal_conditions) before starting the loop")


def cmd_add_item(args):
    st = State(args.root)
    backlog = st.load("backlog")
    if any(i["id"] == args.id for i in backlog["items"]):
        die(f"backlog id exists: {args.id}")
    backlog["items"].append({
        "id": args.id, "title": args.title,
        "priority": args.priority,
        "depends_on": args.depends_on or [],
        "ui": args.ui, "fast_track": args.fast_track,
        "constraints": args.constraint or [],
        "origin": args.origin, "status": "open",
    })
    st.save("backlog", backlog)
    print(f"added {args.id} (priority {args.priority})")


def cmd_claim(args):
    st = State(args.root)
    backlog, queue = st.load("backlog"), st.load("queue")
    entry = next((i for i in backlog["items"] if i["id"] == args.id), None)
    if entry is None:
        die(f"not in backlog: {args.id}")
    if entry["status"] != "open":
        die(f"{args.id} is {entry['status']}, not open")
    unmet = [d for d in entry.get("depends_on", [])
             if not any(q["id"] == d and q["state"] == "done"
                        for q in queue["items"])]
    if unmet:
        die(f"{args.id} has unmet dependencies: {', '.join(unmet)}")
    entry["status"] = "claimed"
    
    nxt = "approved" if entry.get("fast_track") else "researching"
    queue["items"].append({"id": args.id, "state": nxt,
                           "ui": entry.get("ui", False),
                           "history": [{"state": nxt, "at": now()}]})
    st.evidence_dir(args.id).mkdir(parents=True, exist_ok=True)
    st.save("backlog", backlog)
    st.save("queue", queue)
    print(f"{args.id}: backlog -> {nxt} "
          f"(evidence dir: {st.evidence_dir(args.id)})")


def cmd_transition(args):
    st = State(args.root)
    queue, mission = st.load("queue"), st.load("mission")
    item = st.item(queue, args.id)
    cur, nxt = item["state"], args.to
    if nxt not in TRANSITIONS.get(cur, []):
        die(f"illegal transition {cur} -> {nxt} "
            f"(legal: {', '.join(TRANSITIONS.get(cur, [])) or 'none'})")
    is_bounce = (cur, nxt) in BOUNCES
    # Evidence is required leaving any gated state, whether the outcome is a
    # forward transition or a bounce — a bounce is exactly the gate's verdict
    # file recording why it failed. Only a pure escalation straight to
    # 'blocked' (nothing decided yet) is exempt.
    if nxt != "blocked" and cur in FORWARD_EVIDENCE:
        ev = st.evidence_dir(args.id) / FORWARD_EVIDENCE[cur]
        if not ev.exists():
            die(f"transition {cur} -> {nxt} requires evidence file "
                f"{ev} — the gate must write its artifact first")
    forced_block = None
    if is_bounce:
        # A chronically bouncing item almost always means the research doc is
        # wrong; force the upstream diagnosis instead of letting agents grind.
        limit = mission.get("bounce_limit", 3)
        prior = sum(1 for h in item["history"] if h.get("bounce"))
        if prior + 1 >= limit:
            forced_block = (f"bounce limit ({limit}) reached — "
                            f"orchestrator diagnosis required")
            nxt = "blocked"
    if nxt != "blocked":
        hdr = research_header(st, args.id)
        backlog = st.load("backlog")
        entry = next((b for b in backlog["items"] if b["id"] == args.id), None)
        fast_track = bool(entry and entry.get("fast_track"))
        # fast_track items have no research.md (Scout/Plan-Review skipped by
        # design), so default them to low blast instead of the conservative
        # 'high' used for genuinely unknown items.
        blast = hdr.get("blast_radius", "low" if fast_track else "high")
        gates = mission["gates"]
        if cur == "plan-review" and nxt == "approved":
            if BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
                    gates["orchestrator_approval_min_blast"]):
                die(f"{args.id} has blast_radius={blast}: must pass through "
                    f"orchestrator-approval, not straight to approved")
        if cur == "verifying" and nxt == "done":
            if BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
                    gates["code_review_min_blast"]):
                die(f"{args.id} has blast_radius={blast}: must pass through "
                    f"code-review, not straight to done")
        if nxt == "building":
            if not (mission["repo_oracle"].get("build")
                    and mission["repo_oracle"].get("test")):
                die("mission.json repo_oracle.build/test unset — no oracle, "
                    "no building")
    entry = {"state": nxt, "at": now()}
    if is_bounce:
        entry["bounce"] = True
    if forced_block:
        entry["reason"] = forced_block
    if args.blocked_on:
        entry["blocked_on"] = args.blocked_on
        item["blocked_on"] = args.blocked_on
    if args.tokens:
        entry["tokens"] = args.tokens
    if args.note:
        entry["note"] = args.note
    if cur == "blocked":
        item.pop("blocked_on", None)
    item["state"] = nxt
    item["history"].append(entry)
    st.save("queue", queue)
    if nxt in ("done", "blocked"):
        _release(st, args.id, quiet=True)
    msg = f"{args.id}: {cur} -> {nxt}"
    if forced_block:
        msg += f" ({forced_block})"
    if nxt == "done" and item.get("worktree"):
        msg += (f"\n{args.id}: worktree still present — merge branch "
                f"mc/{args.id} then run worktree-remove")
    print(msg)


def _conflicts(lease_path, existing_path):
    a, b = Path(lease_path).as_posix(), Path(existing_path).as_posix()
    return a == b or a.startswith(b.rstrip("/") + "/") \
        or b.startswith(a.rstrip("/") + "/")


def cmd_lease(args):
    st = State(args.root)
    ledger = st.load("ledger")
    paths = args.path or research_header(st, args.id).get("touch_list", [])
    if not paths:
        die("no paths given and no touch_list in research.md")
    clashes = [(p, l) for p in paths for l in ledger["leases"]
               if l["item"] != args.id and _conflicts(p, l["path"])]
    if clashes:
        for p, l in clashes:
            print(f"conflict: {p} vs {l['path']} (held by {l['item']})",
                  file=sys.stderr)
        sys.exit(2)  # distinct code: skip item this cycle, don't fail loop
    ttl = st.load("mission")["lease_ttl_minutes"]
    for p in paths:
        if not any(l["item"] == args.id and l["path"] == p
                   for l in ledger["leases"]):
            ledger["leases"].append({"path": p, "item": args.id,
                                     "acquired": now(), "ttl_minutes": ttl})
    st.save("ledger", ledger)
    print(f"{args.id}: leased {len(paths)} path(s)")


def _release(st, item_id, quiet=False):
    ledger = st.load("ledger")
    before = len(ledger["leases"])
    ledger["leases"] = [l for l in ledger["leases"] if l["item"] != item_id]
    st.save("ledger", ledger)
    if not quiet:
        print(f"{item_id}: released {before - len(ledger['leases'])} lease(s)")


def cmd_release(args):
    _release(State(args.root), args.id)


def cmd_reclaim(args):
    st = State(args.root)
    ledger, queue = st.load("ledger"), st.load("queue")
    expired_items = set()
    for l in ledger["leases"]:
        acquired = datetime.fromisoformat(l["acquired"])
        if datetime.now(timezone.utc) - acquired > timedelta(
                minutes=l["ttl_minutes"]):
            expired_items.add(l["item"])
    for item_id in sorted(expired_items):
        item = next((i for i in queue["items"] if i["id"] == item_id), None)
        if item and item["state"] == "building":
            item["state"] = "approved"
            item["history"].append({"state": "approved", "at": now(),
                                    "bounce": True, "reason": "lease-expired"})
            print(f"{item_id}: stale building -> approved")
        _release(st, item_id, quiet=True)
    st.save("queue", queue)
    if not expired_items:
        print("no expired leases")


def cmd_worktree_add(args):
    st = State(args.root)
    queue = st.load("queue")
    item = st.item(queue, args.id)
    if item.get("worktree"):
        die(f"{args.id} already has a worktree: {item['worktree']}")
    st.paths["worktrees"].mkdir(parents=True, exist_ok=True)
    path = st.paths["worktrees"] / args.id
    branch = f"mc/{args.id}"
    # reuse the branch if a previous attempt left it behind (bounce cycles)
    exists = git(["rev-parse", "--verify", "--quiet", branch],
                 check=False).returncode == 0
    if exists:
        git(["worktree", "add", str(path), branch])
    else:
        git(["worktree", "add", "-b", branch, str(path)])
    item["worktree"] = str(path)
    st.save("queue", queue)
    print(f"{args.id}: worktree at {path} on branch {branch} — implementer "
          f"and verifier operate in here, never in the main tree")


def cmd_worktree_remove(args):
    st = State(args.root)
    queue = st.load("queue")
    item = st.item(queue, args.id)
    path = item.get("worktree")
    if not path:
        die(f"{args.id} has no worktree")
    branch = f"mc/{args.id}"
    merged = git(["branch", "--merged", "HEAD"], check=False).stdout
    if branch not in [b.strip("*+ ") for b in merged.splitlines()] \
            and not args.force:
        die(f"branch {branch} is not merged into HEAD — merge it first, "
            f"or pass --force to discard the work")
    git(["worktree", "remove", "--force", path])
    git(["branch", "-D" if args.force else "-d", branch], check=False)
    item.pop("worktree", None)
    st.save("queue", queue)
    print(f"{args.id}: worktree removed")


def cmd_status(args):
    st = State(args.root)
    mission, backlog = st.load("mission"), st.load("backlog")
    queue, ledger = st.load("queue"), st.load("ledger")
    by_state = {}
    for it in queue["items"]:
        by_state.setdefault(it["state"], []).append(it["id"])
    open_items = [i for i in backlog["items"] if i["status"] == "open"]
    print(f"goal: {mission['goal']}")
    print(f"backlog open: {len(open_items)} "
          f"({', '.join(i['id'] for i in sorted(open_items, key=lambda x: x['priority'])[:5])}"
          f"{'…' if len(open_items) > 5 else ''})")
    for state in TRANSITIONS:
        if by_state.get(state):
            print(f"  {state:>22}: {', '.join(by_state[state])}")
    print(f"leases held: {len(ledger['leases'])} across "
          f"{len({l['item'] for l in ledger['leases']})} item(s)")
    done_ids = set(by_state.get("done", []))
    for it in queue["items"]:
        if it["state"] == "blocked" and it.get("blocked_on") in done_ids:
            print(f"UNBLOCK CANDIDATE: {it['id']} was blocked on "
                  f"{it['blocked_on']}, which is done — transition it back")
        if it["state"] == "done" and it.get("worktree"):
            print(f"MERGE PENDING: {it['id']} is done but branch "
                  f"mc/{it['id']} is unmerged — merge, then worktree-remove")
    open_notes = [x for x in _load_agenda(st)["notes"] if not x["resolved"]]
    for x in open_notes:
        when = f" [when: {x['when']}]" if x.get("when") else ""
        print(f"AGENDA #{x['n']}: {x['text']}{when}")
    tc = mission["terminal_conditions"]
    if tc.get("max_items_completed") and \
            len(done_ids) >= tc["max_items_completed"]:
        print("TERMINAL: max_items_completed reached")
    elif tc.get("backlog_drained") and not open_items and queue["items"] and \
            all(i["state"] == "done" for i in queue["items"]):
        print("TERMINAL: backlog drained and queues empty")


def cmd_metrics(args):
    st = State(args.root)
    queue = st.load("queue")
    out = []
    for it in queue["items"]:
        hist = it["history"]
        durations = {}
        for a, b in zip(hist, hist[1:]):
            secs = (datetime.fromisoformat(b["at"])
                    - datetime.fromisoformat(a["at"])).total_seconds()
            durations[a["state"]] = durations.get(a["state"], 0) + secs
        out.append({
            "id": it["id"], "state": it["state"],
            "bounces": sum(1 for h in hist if h.get("bounce")),
            "tokens": sum(h.get("tokens", 0) for h in hist),
            "seconds_per_state": {k: round(v) for k, v in durations.items()},
        })
    print(json.dumps({"items": out, "generated": now()}, indent=2))


def _load_agenda(st):
    # missions initialized before the agenda existed lack the file
    if not st.paths["agenda"].exists():
        return {"next_id": 1, "notes": []}
    return st.load("agenda")


def cmd_agenda(args):
    st = State(args.root)
    agenda = _load_agenda(st)
    if args.action == "add":
        if not args.text:
            die("agenda add requires text")
        note = {"n": agenda["next_id"], "text": args.text,
                "added": now(), "resolved": None}
        if args.when:
            note["when"] = args.when
        agenda["notes"].append(note)
        agenda["next_id"] += 1
        st.save("agenda", agenda)
        print(f"agenda #{note['n']}: {args.text}")
    elif args.action == "resolve":
        if args.n is None:
            die("agenda resolve requires --n")
        note = next((x for x in agenda["notes"] if x["n"] == args.n), None)
        if note is None:
            die(f"no agenda note #{args.n}")
        if note["resolved"]:
            die(f"agenda note #{args.n} already resolved")
        note["resolved"] = {"at": now(), "note": args.note or args.text or ""}
        st.save("agenda", agenda)
        print(f"agenda #{args.n} resolved")
    else:  # list
        notes = agenda["notes"] if args.all else \
            [x for x in agenda["notes"] if not x["resolved"]]
        if not notes:
            print("agenda: empty")
        for x in notes:
            mark = "x" if x["resolved"] else " "
            when = f" [when: {x['when']}]" if x.get("when") else ""
            print(f"[{mark}] #{x['n']} {x['text']}{when}")


def cmd_audit(args):
    st = State(args.root)
    queue, mission = st.load("queue"), st.load("mission")
    backlog = st.load("backlog")
    gates = mission["gates"]
    holes = 0
    for it in queue["items"]:
        if it["state"] != "done":
            continue
        ev = st.evidence_dir(it["id"])
        entry = next((b for b in backlog["items"] if b["id"] == it["id"]), None)
        fast_track = bool(entry and entry.get("fast_track"))
        hdr = research_header(st, it["id"])
        # fast_track items never go through Scout/Plan-Review, so there is no
        # research.md to read blast_radius from; treat them as low blast —
        # that's the whole premise of fast-tracking — unless a doc happens to
        # exist anyway (e.g. it was later un-fast-tracked).
        blast = hdr.get("blast_radius", "low" if fast_track else "high")
        chain = [] if fast_track else ["research.md", "plan-review.json"]
        if not fast_track and BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
                gates["orchestrator_approval_min_blast"]):
            chain.append("approval.json")
        chain += ["handoff.md", "verify.json"]
        if BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
                gates["code_review_min_blast"]):
            chain.append("code-review.json")
        for f in chain:
            p = ev / f
            if not p.exists():
                print(f"HOLE {it['id']}: missing {f}")
                holes += 1
                continue
            if f == "verify.json":
                try:
                    v = load_llm_json(p)
                except Exception as e:
                    print(f"HOLE {it['id']}: verify.json invalid JSON - {e}")
                    holes += 1
                    continue
                if v.get("verdict") != "green":
                    print(f"HOLE {it['id']}: verify verdict is "
                          f"{v.get('verdict')}, item marked done anyway")
                    holes += 1
            if f == "code-review.json":
                try:
                    v = load_llm_json(p)
                except Exception as e:
                    print(f"HOLE {it['id']}: code-review.json invalid JSON - {e}")
                    holes += 1
                    continue
                if v.get("verdict") != "approve":
                    print(f"HOLE {it['id']}: review verdict is "
                          f"{v.get('verdict')}, item marked done anyway")
                    holes += 1
                if not v.get("concurrency_reviewed"):
                    print(f"HOLE {it['id']}: concurrency_reviewed is false")
                    holes += 1
        if it.get("worktree"):
            print(f"HOLE {it['id']}: done but worktree/branch never merged "
                  f"and removed")
            holes += 1
    total = sum(1 for i in queue["items"] if i["state"] == "done")
    print(f"audit: {total} done item(s), {holes} hole(s)")
    sys.exit(1 if holes else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".mission-control")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("--goal")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("add-item")
    s.add_argument("id"); s.add_argument("title")
    s.add_argument("--priority", type=int, default=5)
    s.add_argument("--depends-on", nargs="*")
    s.add_argument("--constraint", action="append")
    s.add_argument("--ui", action="store_true")
    s.add_argument("--fast-track", action="store_true")
    s.add_argument("--origin", default="architect")
    s.set_defaults(fn=cmd_add_item)

    s = sub.add_parser("claim"); s.add_argument("id")
    s.set_defaults(fn=cmd_claim)

    s = sub.add_parser("transition")
    s.add_argument("id"); s.add_argument("to")
    s.add_argument("--blocked-on")
    s.add_argument("--tokens", type=int)
    s.add_argument("--note")
    s.set_defaults(fn=cmd_transition)

    s = sub.add_parser("lease")
    s.add_argument("id"); s.add_argument("--path", action="append")
    s.set_defaults(fn=cmd_lease)

    s = sub.add_parser("release"); s.add_argument("id")
    s.set_defaults(fn=cmd_release)

    s = sub.add_parser("worktree-add"); s.add_argument("id")
    s.set_defaults(fn=cmd_worktree_add)

    s = sub.add_parser("worktree-remove")
    s.add_argument("id"); s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_worktree_remove)

    s = sub.add_parser("agenda")
    s.add_argument("action", choices=["add", "resolve", "list"])
    s.add_argument("text", nargs="?", help="note text (add)")
    s.add_argument("--n", type=int, help="note number (resolve)")
    s.add_argument("--note", help="resolution note (resolve)")
    s.add_argument("--when", help="free-text trigger hint (add)")
    s.add_argument("--all", action="store_true", help="include resolved (list)")
    s.set_defaults(fn=cmd_agenda)

    s = sub.add_parser("reclaim"); s.set_defaults(fn=cmd_reclaim)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("metrics"); s.set_defaults(fn=cmd_metrics)
    s = sub.add_parser("audit"); s.set_defaults(fn=cmd_audit)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
