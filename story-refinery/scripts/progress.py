#!/usr/bin/env python3
"""What has actually landed. Stdlib only, no network.

  python progress.py set  --bundle bundle.json --done S1 S2 --started S3 [--write]
  python progress.py from --bundle bundle.json --statuses statuses.json [--write]
  python progress.py show --bundle bundle.json

A refinement is a plan, and a plan that never learns what shipped keeps making
the same three mistakes: it re-refines work that is done, it reports an orphaned
subtask as safe to drop when someone already merged it, and it waits on a
`pending` item that arrived last week.

This skill never calls a tracker, so the state has to be handed to it - typed in
after standup, or dropped in as a file the session fetched. Either way it is
recorded with a date and a source, because a status nobody can date is a status
nobody should act on.

Exit codes: 0, or 2 on a bad file.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

STATES = ("todo", "started", "done")


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def apply_states(bundle, states, source):
    known = {s.get("id") for s in bundle.get("subtasks") or []}
    unknown = sorted(set(states) - known)
    progress = (bundle.setdefault("story", {})).setdefault("progress", {})
    progress.setdefault("subtasks", {}).update({k: v for k, v in states.items() if k in known})
    progress["updated_at"] = now()
    progress["source"] = source
    return unknown


def summarise(bundle):
    subs = bundle.get("subtasks") or []
    progress = ((bundle.get("story") or {}).get("progress") or {})
    states = progress.get("subtasks") or {}
    counted = {state: [s.get("id") for s in subs
                       if states.get(s.get("id"), "todo") == state] for state in STATES}
    done_days = sum(s.get("estimate_days") or 0.0 for s in subs
                    if states.get(s.get("id")) == "done")
    total_days = sum(s.get("estimate_days") or 0.0 for s in subs)
    return progress, counted, done_days, total_days


def resolvable_pending(bundle, shipped_tickets):
    """A pending claim whose provider has shipped is no longer pending - it is
    evidence, and it needs a citation to a line rather than to a plan."""
    out = []
    for entry in (bundle.get("evidence") or {}).get("pending") or []:
        ticket = (entry.get("provided_by") or {}).get("ticket")
        if ticket and ticket in shipped_tickets:
            out.append((ticket, entry.get("claim")))
    return out


def cmd_set(args):
    with open(args.bundle, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)
    states = {}
    for sid in args.done or []:
        states[sid] = "done"
    for sid in args.started or []:
        states.setdefault(sid, "started")
    unknown = apply_states(bundle, states, args.source or "reported by hand")
    for sid in unknown:
        print("! %s is not a subtask of this story - ignored" % sid)
    report(bundle)
    if args.write:
        with open(args.bundle, "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("written to %s" % args.bundle)
    else:
        print("dry run - pass --write to record it")
    return 0


def cmd_from(args):
    """Take a file the session fetched: {"S1": "Done", "ABC-123": "Released", ...}.

    Tracker status names are a house matter, so anything that is not obviously
    finished or obviously untouched is 'started' - the honest reading, and the one
    that does not silently promote work to done."""
    with open(args.bundle, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)
    with open(args.statuses, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    done_words = {w.strip().lower() for w in (args.done_when or
                                              "done,closed,released,merged,resolved").split(",")}
    todo_words = {w.strip().lower() for w in (args.todo_when or
                                              "to do,todo,open,backlog,new,refinement").split(",")}
    states = {}
    for key, value in (raw or {}).items():
        text = str(value).strip().lower()
        states[key] = "done" if text in done_words else \
            ("todo" if text in todo_words else "started")
    unknown = apply_states(bundle, states, "%s (%s)" % (args.statuses, args.source or "tracker"))
    for sid in unknown:
        print("! %s is not a subtask of this story - ignored" % sid)
    report(bundle)
    if args.write:
        with open(args.bundle, "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("written to %s" % args.bundle)
    return 0


def report(bundle):
    progress, counted, done_days, total_days = summarise(bundle)
    if not progress:
        print("no progress recorded - nothing knows what has shipped")
        return
    print("done %d, started %d, todo %d  ·  %.2g of %.2g day(s)  ·  as of %s (%s)"
          % (len(counted["done"]), len(counted["started"]), len(counted["todo"]),
             done_days, total_days, progress.get("updated_at", "?"),
             progress.get("source", "?")))
    for state in STATES:
        if counted[state]:
            print("  %-8s %s" % (state, ", ".join(counted[state])))
    shipped = {s for s in (progress.get("shipped_tickets") or [])}
    for ticket, claim in resolvable_pending(bundle, shipped):
        print("  ! %s has shipped, so %r is no longer pending - re-cite it against the code "
              "and drop the pending entry" % (ticket, claim))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("set", help="record what has landed, by subtask id")
    p.add_argument("--bundle", default="bundle.json")
    p.add_argument("--done", nargs="*")
    p.add_argument("--started", nargs="*")
    p.add_argument("--source", help="who said so, e.g. 'standup 2026-09-09'")
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("from", help="take a status map the session fetched from the tracker")
    p.add_argument("--bundle", default="bundle.json")
    p.add_argument("--statuses", required=True)
    p.add_argument("--done-when", help="comma-separated status names that mean finished")
    p.add_argument("--todo-when", help="comma-separated status names that mean untouched")
    p.add_argument("--source")
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("show", help="what is recorded")
    p.add_argument("--bundle", default="bundle.json")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "show":
            with open(args.bundle, "r", encoding="utf-8") as fh:
                report(json.load(fh))
            return 0
        return cmd_set(args) if args.cmd == "set" else cmd_from(args)
    except (OSError, ValueError) as exc:
        print("cannot read: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
