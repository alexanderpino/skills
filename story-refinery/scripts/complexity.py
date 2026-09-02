#!/usr/bin/env python3
"""How complex is this story, and what makes it so. Stdlib only, no network.

  python complexity.py assess --bundle bundle.json [--config refinery.yaml] [--write] [--json]

Every metric is derived from the bundle, never authored, so two people running
this on the same bundle get the same card. The band is explainable by
construction: it is the highest level any metric reaches, and the card names the
metrics at that level as the drivers. No weighted sum - a number nobody can take
apart is an opinion with decimals.

Metrics (each with where it comes from):
  repos           projects touched                    subtasks[].repo, blast_radius.repos
  code_paths      distinct entry points changed       agent_brief.entry_points (path, symbol)
  files_written   distinct files created/modified     agent_brief.change_surface
  read_set        distinct files an implementer must  read_first + entry_points + change_surface
                  hold in context
  contracts       contracts crossed / breaking        evidence.contracts, blast_radius.breaking_contracts
  owner_teams     teams that own touched code         blast_radius.owner_teams, evidence.owners
  rule_space      decision-table combinations         story.decision_table (product of values)
  decisions       forks, of which deferred            decisions[]
  unknowns        blocking questions + pending code   open_questions[], evidence.pending
                  + external blockers                 story.links[blocked_by]
  irreversible    migration subtasks / irreversible   subtasks[].kind, rollback.irreversible
                  rollbacks
  critical_path   longest dependency chain            subtasks[].depends_on
  domain          Cynefin classification              story.intake.domain
  greenfield      nothing exists yet                  evidence.greenfield

Levels: 0 none, 1 low, 2 medium, 3 high, from thresholds in refinery.yaml
(`complexity.thresholds`, defaults below). Bands: S when nothing reaches 2, M
when the highest level is 2, L when one or two metrics reach 3, XL when three
or more do - or when the domain is complex/chaotic and anything else reaches 3.

`--write` records the card in story.complexity; validate.py CPX002 reports a
recorded card that no longer matches the bundle, the same way COV002 treats a
stale coverage map.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yaml import get, load_config  # noqa: E402

# value >= threshold[i] -> level i+1. Three thresholds per metric: low, medium, high.
# Calibrated so that a thorough two-repo feature story with seven subtasks (the golden
# bundle) lands at M: bands only mean something if the typical story is not XL.
DEFAULT_THRESHOLDS = {
    "repos": [1, 2, 3],
    "code_paths": [1, 5, 12],
    "files_written": [1, 8, 20],
    "read_set": [1, 12, 30],
    "contracts": [1, 2, 3],
    "breaking_contracts": [1, 1, 2],
    "owner_teams": [1, 2, 3],
    "rule_space": [1, 8, 32],
    "forks": [1, 3, 6],
    "deferred": [1, 1, 3],
    "unknowns": [1, 2, 4],
    "irreversible": [1, 1, 2],
    "critical_path": [1, 4, 7],
}
DOMAIN_LEVEL = {"clear": 0, "complicated": 1, "complex": 3, "chaotic": 3}
BANDS = ("S", "M", "L", "XL")


def _level(value, thresholds):
    level = 0
    for i, t in enumerate(thresholds):
        if value >= t:
            level = i + 1
    return level


def _critical_path(subs):
    by_id = {s.get("id"): s for s in subs}
    memo = {}

    def depth(sid, seen=()):
        if sid in memo:
            return memo[sid]
        if sid in seen or sid not in by_id:
            return 0
        deps = [d for d in by_id[sid].get("depends_on") or [] if d in by_id]
        memo[sid] = 1 + max([depth(d, seen + (sid,)) for d in deps] or [0])
        return memo[sid]

    return max([depth(s.get("id")) for s in subs] or [0])


def metrics(bundle):
    story = bundle.get("story") or {}
    ev = bundle.get("evidence") or {}
    br = bundle.get("blast_radius") or {}
    subs = bundle.get("subtasks") or []
    briefs = [s.get("agent_brief") or {} for s in subs]

    repos = {s.get("repo") for s in subs if s.get("repo")}
    paths = {(e.get("path"), e.get("symbol") or e.get("line")) for b in briefs
             for e in b.get("entry_points") or [] if e.get("path")}
    written = {e.get("path") for b in briefs for e in b.get("change_surface") or []
               if e.get("role") in ("create", "modify", "delete") and e.get("path")}
    read_set = {e.get("path") for b in briefs
                for e in (b.get("read_first") or []) + (b.get("entry_points") or [])
                + (b.get("change_surface") or []) if e.get("path")}
    contracts = ev.get("contracts") or []
    teams = {o.get("team") for o in ev.get("owners") or [] if o.get("team")}
    table = story.get("decision_table") or {}
    rule_space = 1 if table.get("conditions") else 0
    for c in table.get("conditions") or []:
        rule_space *= max(1, len(c.get("values") or []))
    decisions = bundle.get("decisions") or []
    deferred = [d for d in decisions if d.get("status") == "deferred"]
    blocking_q = [q for q in bundle.get("open_questions") or [] if q.get("blocking")]
    pending = ev.get("pending") or []
    blocked_by = [l for l in story.get("links") or [] if l.get("type") == "blocked_by"]
    irreversible = [s for s in subs if s.get("kind") == "migration"
                    or ((s.get("agent_brief") or {}).get("rollback") or {}).get("irreversible")]
    domain = ((story.get("intake") or {}).get("domain")) or ""
    greenfield = bool(ev.get("greenfield"))

    m = {
        "repos": max(len(repos), int(br.get("repos") or 0)),
        "code_paths": len(paths),
        "files_written": len(written),
        "read_set": len(read_set),
        "contracts": max(len(contracts), int(br.get("contracts") or 0)),
        "breaking_contracts": int(br.get("breaking_contracts") or 0),
        "owner_teams": max(len(teams), int(br.get("owner_teams") or 0)),
        "rule_space": rule_space,
        "forks": len(decisions),
        "deferred": len(deferred),
        "unknowns": len(blocking_q) + len(pending) + len(blocked_by),
        "irreversible": len(irreversible),
        "critical_path": _critical_path(subs),
    }
    return m, {"domain": domain, "greenfield": greenfield, "subtasks": len(subs)}


def assess(bundle, cfg=None):
    cfg = cfg or {}
    thresholds = dict(DEFAULT_THRESHOLDS)
    for key, value in (get(cfg, "complexity.thresholds", {}) or {}).items():
        if isinstance(value, list) and len(value) == 3:
            thresholds[key] = [float(v) for v in value]
    m, extra = metrics(bundle)
    levels = {k: _level(v, thresholds[k]) for k, v in m.items()}
    levels["domain"] = DOMAIN_LEVEL.get(extra["domain"], 0)
    if extra["greenfield"]:
        # Nothing to cite and nothing to reuse: every convention is a decision. That
        # is at least a medium driver on its own, whatever the counts say.
        levels["greenfield"] = 2
    top = max(levels.values()) if levels else 0
    highs = sorted(k for k, l in levels.items() if l == 3)
    if top < 2:
        band = "S"
    elif top == 2:
        band = "M"
    elif len(highs) >= 3 or (levels["domain"] == 3 and len(highs) >= 2):
        band = "XL"
    else:
        band = "L"
    # Drivers are what makes it more than small. At S every metric is low or absent,
    # and listing eight of them as "drivers" is noise, not an explanation.
    drivers = sorted(k for k, l in levels.items() if l == top and top >= 2)
    return {
        "band": band,
        "drivers": drivers,
        "levels": levels,
        "metrics": m,
        "domain": extra["domain"],
        "greenfield": extra["greenfield"],
        "method": "highest-level-wins; XL when three metrics are high, or two under a complex domain",
    }


NAMES = {
    "repos": "projects touched", "code_paths": "code paths changed",
    "files_written": "files written", "read_set": "files to hold in context",
    "contracts": "contracts crossed", "breaking_contracts": "breaking contract changes",
    "owner_teams": "owning teams", "rule_space": "decision-table combinations",
    "forks": "design forks", "deferred": "deferred decisions",
    "unknowns": "blocking unknowns", "irreversible": "irreversible steps",
    "critical_path": "critical path (subtasks deep)", "domain": "Cynefin domain",
    "greenfield": "greenfield",
}
LEVEL_NAMES = ("none", "low", "medium", "high")


def card(a):
    out = ["Complexity: %s  - driven by %s" % (
        a["band"], ", ".join(NAMES.get(d, d) for d in a["drivers"]) or "nothing in particular")]
    out.append("  %-32s %7s  %s" % ("metric", "value", "level"))
    for key in DEFAULT_THRESHOLDS:
        out.append("  %-32s %7s  %s" % (NAMES[key], a["metrics"][key], LEVEL_NAMES[a["levels"][key]]))
    out.append("  %-32s %7s  %s" % (NAMES["domain"], a["domain"] or "-", LEVEL_NAMES[a["levels"]["domain"]]))
    if a["greenfield"]:
        out.append("  %-32s %7s  %s" % (NAMES["greenfield"], "yes", LEVEL_NAMES[2]))
    out.append("  method: %s" % a["method"])
    return "\n".join(out)


def one_line(a):
    """For summary.py and the ticket: the band and the drivers, nothing else."""
    parts = []
    for d in a["drivers"]:
        if d in a["metrics"]:
            parts.append("%s %s" % (a["metrics"][d], NAMES[d]))
        elif d == "domain":
            parts.append("%s domain" % a["domain"])
        else:
            parts.append(NAMES.get(d, d))
    return "%s - %s" % (a["band"], ", ".join(parts) if parts else "nothing reaches medium")


def record(a):
    return {"band": a["band"], "drivers": a["drivers"], "metrics": a["metrics"],
            "levels": a["levels"], "method": a["method"],
            "computed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}


def is_current(bundle, cfg=None):
    """True when story.complexity matches what the bundle computes now."""
    rec = (bundle.get("story") or {}).get("complexity")
    if not rec:
        return False
    a = assess(bundle, cfg)
    return rec.get("band") == a["band"] and rec.get("metrics") == a["metrics"] \
        and rec.get("drivers") == a["drivers"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("assess", help="compute the card; --write records it in story.complexity")
    p.add_argument("--bundle", default="bundle.json")
    p.add_argument("--config", default="refinery.yaml")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        with open(args.bundle, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
    except (OSError, ValueError) as exc:
        print("cannot read bundle: %s" % exc, file=sys.stderr)
        return 2
    cfg = load_config(args.config) if os.path.exists(args.config) else {}
    a = assess(bundle, cfg)
    print(json.dumps(record(a), indent=2) if args.json else card(a))
    if args.write:
        bundle.setdefault("story", {})["complexity"] = record(a)
        with open(args.bundle, "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("\nrecorded in story.complexity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
