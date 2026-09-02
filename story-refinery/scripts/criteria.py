#!/usr/bin/env python3
"""Give acceptance criteria a code, and keep that code meaning the same thing.

  python criteria.py assign --bundle bundle.json [--previous prior.json] [--write]
  python criteria.py check  --bundle bundle.json [--previous prior.json]

A criterion arrives from a ticket as a sentence. It leaves this skill as `AC3`,
and from that moment the code is a public reference: subtasks cover it, the
decision table cites it, critics locate findings by it, and people type it into
comment threads and pull request titles.

So the codes are cheap to assign and expensive to change. Assign one where the
source has none; keep the source's own scheme where it has one; and never
renumber. A criterion inserted in the middle takes the next free number, not the
middle one - shifting the rest is how `AC4` in a three-week-old comment quietly
starts pointing at a different rule.

Exit codes: check -> 0 stable, 1 something moved, 2 usage/parse error.
"""

import argparse
import difflib
import json
import re
import sys

# Enough to survive rewording, not enough to conflate two different rules.
SAME_CRITERION = 0.82
SCHEME_RX = re.compile(r"^([A-Za-z][A-Za-z._-]*?)(\d+)$")


def normalise(text):
    return re.sub(r"[^\w\s]", "", re.sub(r"\s+", " ", (text or ""))).strip().lower()


def criteria_of(bundle):
    return ((bundle.get("story") or {}).get("acceptance_criteria") or [])


def scheme_of(ids):
    """The prefix and width a story's ids share, if they share one."""
    parts = [SCHEME_RX.match(i or "") for i in ids]
    prefixes = {m.group(1) for m in parts if m}
    return (prefixes.pop() if len(prefixes) == 1 else None), [m for m in parts if m]


def next_free(prefix, taken, retired):
    used = set()
    for value in list(taken) + list(retired):
        m = SCHEME_RX.match(value or "")
        if m and m.group(1) == prefix:
            used.add(int(m.group(2)))
    n = 1
    while n in used:
        n += 1
    return "%s%d" % (prefix, n)


def assign(bundle, prior, prefix):
    """Fill in what is missing, preserve what is not, and never reuse a code."""
    story = bundle.setdefault("story", {})
    current = criteria_of(bundle)
    prior_by_text = {normalise(c.get("rule")): c.get("id") for c in criteria_of(prior or {})
                     if c.get("id")}
    retired = set(story.get("retired_criterion_ids") or [])
    retired |= {c.get("id") for c in criteria_of(prior or {}) if c.get("id")}

    existing = [c.get("id") for c in current if c.get("id")]
    found_prefix, _ = scheme_of(existing)
    prefix = found_prefix or prefix

    actions = []
    taken = set(existing)
    for c in current:
        if c.get("id"):
            actions.append(("kept", c["id"], c.get("rule", "")))
            continue
        text = normalise(c.get("rule"))
        reused = prior_by_text.get(text)
        if not reused and prior_by_text:
            match = difflib.get_close_matches(text, list(prior_by_text), 1, SAME_CRITERION)
            reused = prior_by_text[match[0]] if match else None
        if reused and reused not in taken:
            c["id"] = reused
            actions.append(("recovered", reused, c.get("rule", "")))
        else:
            c["id"] = next_free(prefix, taken, retired)
            actions.append(("assigned", c["id"], c.get("rule", "")))
        taken.add(c["id"])

    # Codes that existed before and no longer name anything are retired, not free.
    still_here = {c.get("id") for c in current}
    gone = sorted(i for i in retired if i and i not in still_here)
    if gone:
        story["retired_criterion_ids"] = gone
    return actions, gone


def check(bundle, prior):
    findings = []
    current = criteria_of(bundle)
    ids = [c.get("id") for c in current]

    missing = [c.get("rule", "?")[:60] for c in current if not c.get("id")]
    for rule in missing:
        findings.append(("ERROR", "AC003", "criterion with no code: %r - assign one, it is how "
                         "everything downstream will refer to it" % rule))

    prefix, parsed = scheme_of([i for i in ids if i])
    if not prefix and len(parsed) < len([i for i in ids if i]):
        findings.append(("WARN", "AC010", "mixed code schemes in one story (%s) - pick the "
                         "source's scheme or this skill's, not both"
                         % ", ".join(i for i in ids if i)))
    elif not prefix:
        findings.append(("WARN", "AC010", "codes do not share one prefix (%s)"
                         % ", ".join(i for i in ids if i)))

    retired = set((bundle.get("story") or {}).get("retired_criterion_ids") or [])
    for i in ids:
        if i in retired:
            findings.append(("ERROR", "AC011", "%s was retired and is in use again - a code "
                             "that changes meaning is worse than a new one, because every "
                             "reference to it still resolves" % i))

    if prior:
        before = {c.get("id"): normalise(c.get("rule")) for c in criteria_of(prior)}
        after = {c.get("id"): normalise(c.get("rule")) for c in criteria_of(bundle)}
        for code, text in sorted(after.items()):
            was = before.get(code)
            if was and text and was != text:
                moved = [c for c, t in before.items() if t == text and c != code]
                if moved:
                    findings.append(("ERROR", "AC011", "%s now carries what %s used to say - "
                                     "the criteria were renumbered, so every reference to "
                                     "either is now wrong" % (code, ", ".join(sorted(moved)))))
        for code in sorted(set(before) - set(after)):
            findings.append(("WARN", "AC012", "%s is gone. Its code stays retired - leave the "
                             "gap rather than closing it up" % code))
    return findings


def load(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("assign", "check"):
        p = sub.add_parser(name)
        p.add_argument("--bundle", default="bundle.json")
        p.add_argument("--previous", help="the stored bundle from the last refinement")
        if name == "assign":
            p.add_argument("--prefix", default="AC",
                           help="used only when the story has no scheme of its own")
            p.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    try:
        bundle, prior = load(args.bundle), load(args.previous)
    except (OSError, ValueError) as exc:
        print("cannot read bundle: %s" % exc, file=sys.stderr)
        return 2

    if args.cmd == "assign":
        actions, retired = assign(bundle, prior, args.prefix)
        for what, code, rule in actions:
            print("%-10s %-6s %s" % (what, code, (rule or "")[:70]))
        if retired:
            print("retired, never to be reused: %s" % ", ".join(retired))
        if args.write:
            with open(args.bundle, "w", encoding="utf-8") as fh:
                json.dump(bundle, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            print("written to %s" % args.bundle)
        else:
            print("dry run - pass --write to keep the codes")
        return 0

    findings = check(bundle, prior)
    for severity, code, message in findings:
        print("%-5s %-7s %s" % (severity, code, message))
    errors = sum(1 for s, _, _ in findings if s == "ERROR")
    print("\n%s  %d error(s), %d warning(s)"
          % ("STABLE" if not errors else "MOVED", errors, len(findings) - errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
