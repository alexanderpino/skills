#!/usr/bin/env python3
"""Read what the tracker already says about an item, before refining it. Stdlib only.

  python triage.py apply --bundle bundle.json --config refinery.yaml [--write]

A ticket arrives carrying labels, components, a priority, an issue type and links.
That metadata is a decision somebody already made - "production-issue" says this
escaped to customers, "security" says someone is waiting on it, "sev1" says
refinement is the wrong instrument right now - and refining the description while
ignoring it produces a plan that is correct and inapplicable.

This maps `story.tracker_meta` through the policy in `triage.labels` and writes
`story.triage`: the route, the profile and kind the labels imply, the extra intake
dimensions they demand, the subtask kinds and critics they require, and the
questions they raise. `validate.py` TRI gates hold the bundle to it.

Exit codes: 0 refine, 4 the labels say do not refine yet, 2 usage/parse error.
Capture the metadata verbatim from the tracker. Never invent a label.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yaml import get, load_config  # noqa: E402

TAG_FIELDS = ("labels", "components")
ALL_FIELDS = ("labels", "components", "issue_type", "priority", "status")
# Consequences a rule may carry. Lists merge, scalars take the first rule that sets
# them - so order in the config is precedence, and the file says so.
LIST_KEYS = ("require_dimensions", "mandatory_subtask_kinds", "add_critics",
             "must_answer_nfr", "ask")
SCALAR_KEYS = ("kind", "profile", "route")


def meta_values(meta, field):
    value = (meta or {}).get(field)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def rule_matches(rule, meta):
    """A rule matches when its regex hits any value of the field(s) it looks at."""
    pattern = rule.get("match")
    if not pattern:
        return []
    try:
        rx = re.compile(str(pattern), re.I)
    except re.error:
        return []
    field = str(rule.get("field") or "any").lower()
    fields = ALL_FIELDS if field == "all" else (TAG_FIELDS if field == "any" else (field,))
    hits = []
    for name in fields:
        for value in meta_values(meta, name):
            if rx.search(value):
                hits.append("%s=%s" % (name, value))
    return hits


def policy_for(meta, cfg):
    """Returns (matched rules with their hits, merged consequences, unmatched labels)."""
    matched, merged = [], {k: [] for k in LIST_KEYS}
    for i, rule in enumerate(get(cfg, "triage.labels", []) or []):
        hits = rule_matches(rule, meta)
        if not hits:
            continue
        rid = rule.get("id") or rule.get("match") or "rule%d" % i
        matched.append({"id": rid, "matched_on": hits})
        for key in LIST_KEYS:
            for item in rule.get(key) or []:
                if item not in merged[key]:
                    merged[key].append(item)
        for key in SCALAR_KEYS:
            if rule.get(key) and key not in merged:
                merged[key] = rule[key]
    merged.setdefault("route", "refine")

    ignored = [str(x).lower() for x in get(cfg, "triage.ignore", []) or []]
    claimed = set()
    for rule in get(cfg, "triage.labels", []) or []:
        for hit in rule_matches(rule, meta):
            claimed.add(hit.split("=", 1)[1].lower())
    # Only labels are reported as unclassified. Components are a taxonomy that
    # exists for routing and is always populated; labels are the ad-hoc signal
    # somebody added on purpose, which is exactly why an unrecognised one matters.
    unknown = [v for v in meta_values(meta, "labels")
               if v.lower() not in claimed
               and not any(re.search(pat, v, re.I) for pat in ignored)]
    return matched, merged, sorted(set(unknown))


def assess(bundle, cfg):
    meta = (bundle.get("story") or {}).get("tracker_meta") or {}
    matched, merged, unknown = policy_for(meta, cfg)
    triage = {"matched": matched, "unknown_labels": unknown}
    triage.update({k: v for k, v in merged.items() if v})
    return triage


def questions_from(triage):
    return [q for q in triage.get("ask") or []]


def write_into_bundle(path, triage):
    with open(path, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)
    story = bundle.setdefault("story", {})
    existing = bundle.setdefault("open_questions", [])
    used = {q.get("id") for q in existing}
    texts = {(q.get("text") or "").strip() for q in existing}
    added, n = 0, 1
    for text in questions_from(triage):
        if text.strip() in texts:
            continue
        while "Q%d" % n in used:
            n += 1
        qid = "Q%d" % n
        used.add(qid)
        existing.append({"id": qid, "text": text, "owner": "",
                         "blocking": False, "source": "triage"})
        added += 1
    story["triage"] = triage
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return added


def report(bundle, triage):
    meta = (bundle.get("story") or {}).get("tracker_meta") or {}
    if not meta:
        print("no story.tracker_meta - the ticket's own labels, components, priority and "
              "links were never read. Capture them verbatim before refining.")
        return
    print("labels: %s   components: %s   type: %s   priority: %s"
          % (", ".join(meta_values(meta, "labels")) or "none",
             ", ".join(meta_values(meta, "components")) or "none",
             meta.get("issue_type") or "?", meta.get("priority") or "?"))
    if not triage["matched"]:
        print("no policy matched - nothing on this ticket changes the refinement")
    for m in triage["matched"]:
        print("  rule %-22s <- %s" % (m["id"], ", ".join(m["matched_on"])))
    for key in ("kind", "profile", "route"):
        if triage.get(key):
            print("  %-10s %s" % (key + ":", triage[key]))
    for key in LIST_KEYS:
        if triage.get(key) and key != "ask":
            print("  %-24s %s" % (key + ":", ", ".join(map(str, triage[key]))))
    for text in questions_from(triage):
        print("  ask: %s" % text)
    if triage["unknown_labels"]:
        print("  ! no policy and no ignore rule covers: %s - decide whether they matter, "
              "then say so in triage.labels or triage.ignore"
              % ", ".join(triage["unknown_labels"]))
    if triage.get("route") == "incident":
        print("\nDo not refine yet: the labels say this is being handled as an incident. "
              "Stabilise first, then refine what is left.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("apply", help="map tracker metadata through the label policy")
    p.add_argument("--bundle", default="bundle.json")
    p.add_argument("--config", default="refinery.yaml")
    p.add_argument("--write", action="store_true",
                   help="write story.triage and add the questions it raises")
    args = ap.parse_args(argv)

    try:
        with open(args.bundle, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
    except (OSError, ValueError) as exc:
        print("cannot read bundle: %s" % exc, file=sys.stderr)
        return 2
    cfg = load_config(args.config) if os.path.exists(args.config) else {}

    triage = assess(bundle, cfg)
    report(bundle, triage)
    if args.write:
        added = write_into_bundle(args.bundle, triage)
        print("\nwrote story.triage; %d question(s) added" % added)
    return 4 if triage.get("route") == "incident" else 0


if __name__ == "__main__":
    sys.exit(main())
