#!/usr/bin/env python3
"""gauntlet.py — deterministic state for a Gauntlet Loop run.

Stdlib only. The model decides; this script counts. Streaks, stop conditions,
revert rates and budget consumption are computed here so they cannot drift in a
long context.

Commands:
  init        Create the gauntlet/ state directory and config
  log-round   Append one validated comparison record to rounds.jsonl
  status      Per-lane/per-dimension streaks, revert rate, fired stop conditions
  report      Draft the end-of-run gauntlet report from the log
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

MODES = ("blind", "rubric", "champion")
WINNERS = ("ours", "other")
MARGINS = ("decisive", "clear", "thin")
SEVERITIES = ("major", "minor", "none")
ACTIONS = ("promoted", "reverted")

DEFAULT_CONFIG = {
    "stops": {"bar_met_n": 2, "clean_streak_n": 2, "budget_waves": 12},
    "dimensions": ["overall"],
    "lanes": [],
    "bar_kind": "reference",
}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_config(root):
    p = root / "config.json"
    if not p.exists():
        die(f"{p} not found — run init first")
    return json.loads(p.read_text())


def load_rounds(root):
    p = root / "rounds.jsonl"
    if not p.exists():
        return []
    out = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            die(f"rounds.jsonl line {i} is corrupt: {e}")
    return out


def cmd_init(args):
    root = Path(args.root)
    if (root / "config.json").exists() and not args.force:
        die(f"{root}/config.json already exists (use --force to overwrite config only)")
    for d in ("bar",):
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    if args.lanes:
        cfg["lanes"] = [s.strip() for s in args.lanes.split(",") if s.strip()]
    if args.dimensions:
        cfg["dimensions"] = [s.strip() for s in args.dimensions.split(",") if s.strip()]
    if args.bar_met_n is not None:
        cfg["stops"]["bar_met_n"] = args.bar_met_n
    if args.clean_streak_n is not None:
        cfg["stops"]["clean_streak_n"] = args.clean_streak_n
    if args.budget_waves is not None:
        cfg["stops"]["budget_waves"] = args.budget_waves
    if args.bar_kind:
        if args.bar_kind not in ("reference", "acceptance criteria", "hybrid"):
            die("bar-kind must be one of: reference, acceptance criteria, hybrid")
        cfg["bar_kind"] = args.bar_kind
    (root / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    for name, header in (
        ("contract.md", "# Gauntlet contract\n\n(goal / bar / inspection / stops / budget / autonomy / workbench)\n"),
        ("ownership.md", "# File ownership — refreshed every wave\n\n| lane | owned paths |\n|---|---|\n"),
    ):
        p = root / name
        if not p.exists():
            p.write_text(header)
    (root / "rounds.jsonl").touch()
    print(f"initialised {root}/ — freeze bar artifacts into {root}/bar/ before wave 1")


def cmd_log_round(args):
    root = Path(args.root)
    cfg = load_config(root)
    dims = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    if args.dimension not in dims:
        die(
            f"dimension {args.dimension!r} is not declared in config.json ({', '.join(dims)}) — "
            "judge each declared dimension in its own comparison"
        )
    lanes = cfg.get("lanes") or []
    if lanes and args.lane not in lanes:
        print(
            f"warning: lane {args.lane!r} is not in config.json ({', '.join(lanes)}) — "
            "re-run init --force after a re-cut, or fix the typo",
            file=sys.stderr,
        )
    if args.mode not in MODES:
        die(f"mode must be one of {MODES}")
    if args.winner not in WINNERS:
        die(f"winner must be one of {WINNERS} (in champion mode: ours=challenger, other=champion)")
    if args.margin not in MARGINS:
        die(f"margin must be one of {MARGINS}")
    if args.score is None or not (0 <= args.score <= 10):
        die("score must be an integer between 0 and 10")
    if not args.evidence:
        die("evidence is required — a verdict with nothing inspected is not a round")

    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "wave": args.wave,
        "lane": args.lane,
        "dimension": args.dimension,
        "round": args.round,
        "mode": args.mode,
        "winner": args.winner,
        "margin": args.margin,
        "score": args.score,
        "evidence": args.evidence,
        "critic_framing": args.critic_framing,
    }

    if args.mode == "champion":
        # Promotion decision: challenger vs previous champion.
        if args.action not in ACTIONS:
            die("champion-mode records require --action promoted|reverted")
        if args.winner == "ours" and args.action != "promoted":
            die("challenger won but action is not 'promoted' — that is a logging mistake")
        if args.winner == "other" and args.action != "reverted":
            die("champion won but action is not 'reverted' — losers get reverted")
        rec["action"] = args.action
        rec["champion_ref"] = args.champion_ref or ""
    else:
        # Bar comparison: gap severity drives clean-streak; winner drives bar-met.
        if args.severity not in SEVERITIES:
            die("bar-mode records require --severity major|minor|none")
        if args.severity != "none" and not args.gap:
            die("severity is major/minor but no gap named — name the gap or the round didn't happen")
        rec["severity"] = args.severity
        rec["gap"] = args.gap or "none"

    with (root / "rounds.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"logged: wave {rec['wave']} lane {rec['lane']} [{rec['dimension']}] {rec['mode']} → {rec['winner']} ({rec['margin']})")


def _streaks(records):
    """Compute trailing streaks over bar-mode records, ordered as logged."""
    bar_met = clean = 0
    for r in reversed(records):
        if r["winner"] == "ours":
            bar_met += 1
        else:
            break
    for r in reversed(records):
        if r.get("severity") == "none":
            clean += 1
        else:
            break
    return bar_met, clean


def _lane_dim_status(rounds, cfg):
    """Returns {(lane, dim): stats} and set of retired lanes."""
    stops = cfg["stops"]
    keys = {}
    for r in rounds:
        keys.setdefault((r["lane"], r["dimension"]), []).append(r)
    out = {}
    for key, recs in keys.items():
        bar_recs = [r for r in recs if r["mode"] in ("blind", "rubric")]
        champ_recs = [r for r in recs if r["mode"] == "champion"]
        bar_met, clean = _streaks(bar_recs)
        reverts = sum(1 for r in champ_recs if r.get("action") == "reverted")
        margins = [r["margin"] for r in bar_recs][-5:]
        rubric_share = (
            sum(1 for r in bar_recs if r["mode"] == "rubric") / len(bar_recs)
            if bar_recs else 0.0
        )
        # Open only if the *latest* verdict still names a gap — an older gap
        # followed by a clean round has been closed, and reporting it as open
        # would put stale work in the hand-off.
        last_gap = (
            bar_recs[-1].get("gap")
            if bar_recs and bar_recs[-1].get("severity") not in (None, "none")
            else None
        )
        out[key] = {
            "bar_rounds": len(bar_recs),
            "promotions": sum(1 for r in champ_recs if r.get("action") == "promoted"),
            "reverts": reverts,
            "bar_met_streak": bar_met,
            "clean_streak": clean,
            "recent_margins": margins,
            "rubric_share": round(rubric_share, 2),
            "open_gap": last_gap,
            "retired": bar_met >= stops["bar_met_n"] or clean >= stops["clean_streak_n"],
        }
    # A lane retires only when every *declared* dimension has retired — a
    # dimension nobody ever judged must not let the lane out early.
    declared = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    lanes = {lane for lane, _ in out}
    retired_lanes = {
        lane for lane in lanes
        if all(out.get((lane, d), {}).get("retired") for d in declared)
    }
    return out, retired_lanes


def cmd_status(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    if not rounds:
        print("no rounds logged yet")
        return
    per, retired = _lane_dim_status(rounds, cfg)
    max_wave = max(r["wave"] for r in rounds)
    budget = cfg["stops"]["budget_waves"]

    print(f"wave {max_wave} of {budget} budgeted\n")
    for (lane, dim), s in sorted(per.items()):
        flag = " RETIRED" if s["retired"] else ""
        print(f"[{lane} / {dim}]{flag}")
        print(f"  bar rounds {s['bar_rounds']}  promoted {s['promotions']}  reverted {s['reverts']}")
        print(f"  bar-met streak {s['bar_met_streak']}  clean streak {s['clean_streak']}  rubric share {s['rubric_share']}")
        print(f"  recent margins: {' → '.join(s['recent_margins']) or '—'}")
        if s["open_gap"]:
            print(f"  open gap: {s['open_gap']}")
        print()

    fired = []
    if max_wave >= budget:
        fired.append(f"budget (wave {max_wave} >= {budget})")
    all_lanes = {lane for lane, _ in per}
    if all_lanes and all_lanes == retired:
        fired.append("all lanes retired (bar-met / clean-streak)")
    total_champ = [r for r in rounds if r["mode"] == "champion"]
    recent = total_champ[-6:]
    if len(recent) >= 4 and sum(1 for r in recent if r.get("action") == "reverted") > len(recent) / 2:
        fired.append("judgment signal: revert rate over 50% in recent rounds — likely at the ceiling")
    if fired:
        print("STOP CONDITIONS FIRED / SIGNALLED:")
        for f in fired:
            print(f"  - {f}")
    else:
        print("no stop condition fired")


def cmd_report(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    if not rounds:
        die("no rounds to report on")
    per, retired = _lane_dim_status(rounds, cfg)
    lines = ["# Gauntlet report (draft — lead agent completes the judgement fields)", ""]
    lines += [f"Waves run: {max(r['wave'] for r in rounds)} of {cfg['stops']['budget_waves']} budgeted", ""]
    blind = sum(1 for r in rounds if r["mode"] == "blind")
    rubric = sum(1 for r in rounds if r["mode"] == "rubric")
    lines += [f"Verdict evidence: {blind} blind rounds, {rubric} rubric rounds (not equivalent evidence)", ""]
    lines += ["## Lanes", ""]
    for (lane, dim), s in sorted(per.items()):
        state = "retired" if s["retired"] else "open"
        lines.append(f"- **{lane} / {dim}** — {state}; {s['bar_rounds']} bar rounds, {s['reverts']} reverts")
    lines += ["", "## Open gaps (do not soften this section)", ""]
    any_gap = False
    for (lane, dim), s in sorted(per.items()):
        if s["open_gap"]:
            any_gap = True
            lines.append(f"- [{lane} / {dim}] {s['open_gap']}")
    if not any_gap:
        lines.append("- none recorded — verify this against the last wave's verdicts before believing it")
    lines += ["", "## Was the loop still improving at the stop?", "", "(lead agent: answer from margin trends and revert rate — do not fudge this)", ""]
    out = root / "report.md"
    out.write_text("\n".join(lines))
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser(prog="gauntlet.py", description=__doc__)
    ap.add_argument("--root", default="gauntlet", help="state directory (default: gauntlet/)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--lanes", help="comma-separated initial lane names")
    p.add_argument("--dimensions", help="comma-separated bar dimensions (default: overall)")
    p.add_argument("--bar-kind", help="reference|acceptance criteria|hybrid")
    p.add_argument("--bar-met-n", type=int)
    p.add_argument("--clean-streak-n", type=int)
    p.add_argument("--budget-waves", type=int)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("log-round")
    p.add_argument("--wave", type=int, required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--dimension", default="overall")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--mode", required=True, help="blind|rubric (vs bar) or champion (promotion)")
    p.add_argument("--winner", required=True, help="ours|other")
    p.add_argument("--margin", required=True, help="decisive|clear|thin")
    p.add_argument("--score", type=int, required=True, help="0-10 integer score")
    p.add_argument("--severity", help="major|minor|none — bar modes only")
    p.add_argument("--gap", help="the named gap — required unless severity none")
    p.add_argument("--evidence", required=True, help="path/measurement actually inspected")
    p.add_argument("--action", help="promoted|reverted — champion mode only")
    p.add_argument("--champion-ref", help="git ref or snapshot path of the pre-round champion")
    p.add_argument("--critic-framing", default="default")
    p.set_defaults(fn=cmd_log_round)

    p = sub.add_parser("status")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("report")
    p.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
