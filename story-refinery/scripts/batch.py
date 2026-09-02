#!/usr/bin/env python3
"""Refine several related stories in one run without paying for the area twice.

  python batch.py order  --bundles a.json b.json c.json
  python batch.py share  --bundles a.json b.json c.json [--write]
  python batch.py check  --bundles a.json b.json c.json

`inherit` (evidence.py) carries a dossier forward from an earlier session. This is
the other case: several stories on the desk at the same time, through the same
code. What is shared is *evidence* - the glossary, the house conventions, what is
absent. What is never shared is *judgement*: each story keeps its own intake
verdict, its own criteria, its own decomposition and its own critics, or the
second and third stories quietly become shallower copies of the first.

Bundles stay self-contained, because each one is pushed and read on its own. So
shared knowledge is copied into each, marked with where it came from - and `check`
is what stops the copies drifting apart afterwards.

Exit codes: check -> 0 clean, 1 findings that matter, 2 usage/parse error.
"""

import argparse
import json
import sys

SHARED_FIELDS = ("glossary", "conventions", "ruled_out")
# What makes two entries "the same thing said twice", per field.
IDENTITY = {"glossary": "term", "conventions": "rule", "ruled_out": "claim"}
BODY = {"glossary": "means", "conventions": "evidence", "ruled_out": "conclusion"}


# The codes only this module emits; see validate.CODES for the shape and the checks.
CODES = {
    # 9 other
    "BAT001": ("error", "two stories in the batch write the same file"),
    "BAT002": ("error", "shared knowledge says different things in different bundles"),
    "BAT003": ("warn", "one person is asked the same question from several stories"),
    "BAT004": ("error", "a story waits on another in the batch with no blocked_by link"),
    "BAT006": ("warn", "two stories in the batch touch mostly the same files"),
}

def load(paths):
    out = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as fh:
            out.append((path, json.load(fh)))
    return out


def key_of(bundle):
    return (bundle.get("story") or {}).get("key") or "?"


def writes_of(bundle):
    """(repo, path) -> [subtask ids], for files this story's subtasks will write."""
    owned = {}
    done = (((bundle.get("story") or {}).get("progress") or {}).get("subtasks") or {})
    for st in bundle.get("subtasks") or []:
        # A subtask that has landed no longer writes anything: two stories sharing a file
        # across a boundary that implementation already crossed is not a collision.
        if done.get(st.get("id")) == "done":
            continue
        for entry in (st.get("agent_brief") or {}).get("change_surface") or []:
            if entry.get("role") in ("create", "modify", "delete"):
                owned.setdefault((st.get("repo"), entry.get("path")), []).append(st.get("id"))
    return owned


def links_of(bundle):
    story = bundle.get("story") or {}
    out = {}
    for source in ((story.get("tracker_meta") or {}).get("links") or [],
                   story.get("links") or []):
        for link in source:
            if link.get("key"):
                kind = str(link.get("type", "")).lower().replace(" ", "_").replace("is_", "")
                out.setdefault(link["key"], set()).add(kind)
    return out


# ------------------------------------------------------------------------ order

def cmd_order(bundles):
    """Refine the story others depend on first: its decisions and its evidence are
    inputs to theirs, and re-deciding a fork per story is how a batch produces three
    incompatible answers."""
    keys = {key_of(b) for _, b in bundles}
    deps = {}
    for _, b in bundles:
        key = key_of(b)
        blockers = {t for t, kinds in links_of(b).items() if "blocked_by" in kinds}
        blockers |= {(p.get("provided_by") or {}).get("ticket")
                     for p in (b.get("evidence") or {}).get("pending") or []}
        deps[key] = {t for t in blockers if t in keys and t != key}

    ordered, seen = [], set()
    while len(ordered) < len(deps):
        ready = sorted(k for k, d in deps.items() if k not in seen and d <= seen)
        if not ready:
            rest = sorted(k for k in deps if k not in seen)
            print("cycle or missing predecessor among %s - refine them together and decide "
                  "the shared forks once" % ", ".join(rest))
            ordered += rest
            break
        ordered += ready
        seen |= set(ready)

    print("refinement order:")
    for i, key in enumerate(ordered, 1):
        blockers = sorted(deps.get(key, ()))
        print("  %d. %-10s%s" % (i, key,
                                 "  (needs %s first)" % ", ".join(blockers) if blockers else ""))
    shared_forks = {}
    for _, b in bundles:
        for d in b.get("decisions") or []:
            shared_forks.setdefault((d.get("question") or "").strip().lower(), []).append(key_of(b))
    repeated = sorted({(tuple(sorted(set(ks))), q) for q, ks in shared_forks.items()
                       if q and len(set(ks)) > 1})
    by_group = {}
    for ks, q in repeated:
        by_group.setdefault(ks, []).append(q)
    for ks, questions in sorted(by_group.items()):
        print("  ! %d fork(s) are open in all of %s: decide each once, in the first of them, "
              "and reference the decision from the others" % (len(questions), ", ".join(ks)))
    return 0


# ------------------------------------------------------------------------ share

def cmd_share(bundles, write):
    """Union the evidence half of the dossier, then push it back into every bundle."""
    union, conflicts = {f: {} for f in SHARED_FIELDS}, []
    for path, b in bundles:
        for field in SHARED_FIELDS:
            for entry in (b.get("evidence") or {}).get(field) or []:
                name = str(entry.get(IDENTITY[field], "")).strip()
                if not name:
                    continue
                prior = union[field].get(name.lower())
                if prior and str(prior[1].get(BODY[field], "")).strip() != \
                        str(entry.get(BODY[field], "")).strip():
                    conflicts.append((field, name, prior[0], key_of(b)))
                    continue
                union[field].setdefault(name.lower(), (key_of(b), entry))

    for field, name, first, second in conflicts:
        print("CONFLICT %s %r says different things in %s and %s - one of them is wrong, and "
              "sharing it would spread whichever" % (field, name, first, second))

    total = sum(len(v) for v in union.values())
    print("%d shared entr(ies): %s" % (total, ", ".join(
        "%d %s" % (len(v), f) for f, v in union.items() if v)))

    if not write:
        print("dry run - pass --write to copy them into every bundle")
        return 1 if conflicts else 0

    for path, b in bundles:
        ev = b.setdefault("evidence", {})
        for field in SHARED_FIELDS:
            existing = ev.setdefault(field, [])
            have = {str(e.get(IDENTITY[field], "")).strip().lower() for e in existing}
            for name, (origin, entry) in sorted(union[field].items()):
                if name in have or origin == key_of(b):
                    continue
                copied = dict(entry)
                copied["inherited_from"] = "%s (same refinement run)" % origin
                existing.append(copied)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(b, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    print("written into %d bundle(s). Each stays self-contained; `batch.py check` is what "
          "keeps the copies from drifting." % len(bundles))
    return 1 if conflicts else 0


# ------------------------------------------------------------------------ check

def cmd_check(bundles):
    findings = []

    def error(code, msg):
        findings.append(("ERROR", code, msg))

    def warn(code, msg):
        findings.append(("WARN", code, msg))

    keys = {key_of(b) for _, b in bundles}

    # One finding per pair of stories, not per file: twenty errors that all say the
    # same thing bury the one that does not.
    owners = {}
    for _, b in bundles:
        for (repo, path), ids in writes_of(b).items():
            owners.setdefault((repo, path), []).append(key_of(b))
    collisions = {}
    for (repo, path), holders in owners.items():
        for i, a in enumerate(sorted(set(holders))):
            for other in sorted(set(holders))[i + 1:]:
                collisions.setdefault((a, other), []).append("%s/%s" % (repo, path))
    for (a, other), paths in sorted(collisions.items()):
        shown = ", ".join(sorted(paths)[:3])
        error("BAT001", "%s and %s both write %d file(s) - %s%s. Inside one story the wave plan "
              "stops this; across stories nothing does, so order them with a blocked_by link or "
              "give each file to one of them"
              % (a, other, len(paths), shown,
                 " and %d more" % (len(paths) - 3) if len(paths) > 3 else ""))

    for field in SHARED_FIELDS:
        said = {}
        for _, b in bundles:
            for entry in (b.get("evidence") or {}).get(field) or []:
                name = str(entry.get(IDENTITY[field], "")).strip().lower()
                if name:
                    said.setdefault(name, {}).setdefault(
                        str(entry.get(BODY[field], "")).strip(), []).append(key_of(b))
        for name, versions in sorted(said.items()):
            if len(versions) > 1:
                error("BAT002", "%s %r says different things in %s - shared knowledge that "
                      "disagrees with itself is worse than none, because each story looks "
                      "internally consistent"
                      % (field, name, " vs ".join(", ".join(v) for v in versions.values())))

    asked = {}
    for _, b in bundles:
        for q in b.get("open_questions") or []:
            text = (q.get("text") or "").strip().lower()
            if text:
                asked.setdefault((q.get("owner") or "?", text), []).append(key_of(b))
    per_owner = {}
    for (owner, text), ks in asked.items():
        if len(set(ks)) > 1:
            per_owner.setdefault(owner, []).append(text)
    for owner, texts in sorted(per_owner.items()):
        warn("BAT003", "%s is being asked the same question in %s - put it once, naming the "
             "stories it affects, rather than once per ticket"
             % (owner, " and ".join(sorted({k for t in texts for k in asked[(owner, t)]}))))

    for _, b in bundles:
        key, links = key_of(b), links_of(b)
        for p in (b.get("evidence") or {}).get("pending") or []:
            provider = (p.get("provided_by") or {}).get("ticket")
            if provider in keys and provider != key and "blocked_by" not in links.get(provider, ()):
                error("BAT004", "%s waits on %s, which is in this very batch, and no blocked_by "
                      "link records it - within a batch the order is knowable, so there is no "
                      "excuse for it living only in your head" % (key, provider))

    surfaces = {}
    for _, b in bundles:
        surfaces[key_of(b)] = {(e.get("repo"), e.get("path"))
                               for e in (b.get("evidence") or {}).get("change_surface") or []}
    pairs = sorted(surfaces)
    for i, a in enumerate(pairs):
        for other in pairs[i + 1:]:
            shared = surfaces[a] & surfaces[other]
            smaller = min(len(surfaces[a]), len(surfaces[other])) or 1
            if shared and len(shared) / smaller > 0.6:
                warn("BAT006", "%s and %s touch mostly the same files (%d shared) - check they "
                     "are two stories and not one that was split by wording"
                     % (a, other, len(shared)))

    for severity, code, msg in findings:
        print("%-5s %-7s %s" % (severity, code, msg))
    errors = sum(1 for s, _, _ in findings if s == "ERROR")
    print("\n%s  %d error(s), %d warning(s) across %d bundle(s)"
          % ("CLEAN" if not errors else "NOT CLEAN", errors, len(findings) - errors, len(bundles)))
    if not findings:
        print("Shared knowledge agrees, no file is claimed twice, and every cross-story "
              "dependency is linked.")
    return 1 if errors else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, help_text in (("order", "which story to refine first, and which forks are shared"),
                            ("share", "union the evidence half of the dossier across the batch"),
                            ("check", "what only shows up when the bundles are read together")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--bundles", nargs="+", required=True)
        if name == "share":
            p.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    try:
        bundles = load(args.bundles)
    except (OSError, ValueError) as exc:
        print("cannot read bundles: %s" % exc, file=sys.stderr)
        return 2
    if args.cmd == "order":
        return cmd_order(bundles)
    if args.cmd == "share":
        return cmd_share(bundles, args.write)
    return cmd_check(bundles)


if __name__ == "__main__":
    sys.exit(main())
