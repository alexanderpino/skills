#!/usr/bin/env python3
"""The wishes a calling skill hands to story-refinery, pinned to the bundle. Stdlib only.

  python wishes.py stamp --file refinement.md --bundle bundle.json --source dev-skill [--write]
  python wishes.py check --bundle bundle.json

A developer skill calls story-refinery and passes its wishes - typically a
`refinement.md` reference file: owners, budgets, the DoD, labels, language, what
to skip and why. Those wishes steer the run, so the bundle records *which*
wishes: the path, a content hash, and the headings, so that a later reader can
tell whether the file that steered this refinement is the one on disk today.

`stamp` records it in bundle.tailoring.wishes. `check` re-hashes the file and
reports drift; validate.py TLR008 does the same at every validation, and TLR007
asks for a stamp whenever a tailoring source is recorded at all.

What the wishes *say* is not parsed here - they are instructions for the model,
and TLR006 is the gate that keeps the mechanical ones from staying prose.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone


def digest_file(path):
    with open(path, "rb") as fh:
        return "sha256:" + hashlib.sha256(fh.read()).hexdigest()


def headings(path):
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            m = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
            if m:
                out.append(m.group(2))
    return out


def stamp(path, source):
    return {"path": path, "digest": digest_file(path), "headings": headings(path),
            "source": source, "stamped_at":
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()}


def drift(record, root="."):
    """None when the file on disk matches the stamp; a reason otherwise."""
    path = record.get("path") or ""
    # Relative paths resolve against the working directory first, then the skill
    # root, so the shipped example stamps hold wherever validate.py is run from.
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [path] if os.path.isabs(path) else [os.path.join(root, path),
                                                     os.path.join(skill_root, path)]
    full = next((c for c in candidates if os.path.exists(c)), candidates[0])
    if not os.path.exists(full):
        return "the wishes file %r is not on disk - the instructions that steered this " \
               "refinement cannot be re-read" % path
    if digest_file(full) != record.get("digest"):
        now = headings(full)
        added = [h for h in now if h not in (record.get("headings") or [])]
        gone = [h for h in (record.get("headings") or []) if h not in now]
        detail = []
        if added:
            detail.append("new: %s" % ", ".join(added[:4]))
        if gone:
            detail.append("gone: %s" % ", ".join(gone[:4]))
        return "the wishes file changed since this refinement was made%s" % (
            " (%s)" % "; ".join(detail) if detail else "")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("stamp", help="record the wishes file in bundle.tailoring.wishes")
    p.add_argument("--file", required=True, help="the caller's refinement.md (or equivalent)")
    p.add_argument("--bundle", default="bundle.json")
    p.add_argument("--source", help="the calling skill's name; sets tailoring.source too")
    p.add_argument("--write", action="store_true")
    c = sub.add_parser("check", help="report drift between the stamp and the file on disk")
    c.add_argument("--bundle", default="bundle.json")
    args = ap.parse_args(argv)
    try:
        with open(args.bundle, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
    except (OSError, ValueError) as exc:
        print("cannot read bundle: %s" % exc, file=sys.stderr)
        return 2
    tailoring = bundle.setdefault("tailoring", {})
    if args.cmd == "stamp":
        try:
            rec = stamp(args.file, args.source or tailoring.get("source") or "")
        except OSError as exc:
            print("cannot read wishes: %s" % exc, file=sys.stderr)
            return 2
        print("wishes  %s  %s\n  headings: %s" % (rec["path"], rec["digest"][:18],
                                                  ", ".join(rec["headings"]) or "-"))
        if args.write:
            tailoring["wishes"] = rec
            if args.source:
                tailoring["source"] = args.source
            with open(args.bundle, "w", encoding="utf-8") as fh:
                json.dump(bundle, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            print("recorded in tailoring.wishes")
        return 0
    rec = tailoring.get("wishes")
    if not rec:
        print("no wishes stamped - run `wishes.py stamp` if a calling skill steered this run")
        return 1
    why = drift(rec)
    print(why or "wishes unchanged since the stamp (%s)" % rec.get("digest", "")[:18])
    return 1 if why else 0


if __name__ == "__main__":
    sys.exit(main())
