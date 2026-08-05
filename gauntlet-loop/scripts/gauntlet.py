#!/usr/bin/env python3
"""gauntlet.py — deterministic state for a Gauntlet Loop run.

Stdlib only. The model decides; this script counts. Streaks, stop conditions,
revert rates and budget consumption are computed here so they cannot drift in a
long context.

Commands:
  init        Create the gauntlet/ state directory and config
  log-round   Append one validated comparison record to rounds.jsonl
  status      Per-lane/per-dimension streaks, revert rate, fired stop conditions
  extend      Raise the wave budget after the user grants an extension
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
    "stops": {
        "bar_met_n": 2,
        "clean_streak_n": 2,
        "budget_waves": 12,
        # Absolute ceiling no extension may cross. null = no ceiling agreed, in
        # which case every extension needs the user again.
        "hard_cap_waves": None,
    },
    "dimensions": ["overall"],
    "lanes": [],
    "bar_kind": "reference",
    # Granted budget extensions, appended by `extend`. The run's history of
    # "the budget ran out and the user chose to keep going".
    "extensions": [],
}

# One builder call plus up to two critic calls per lane per wave, plus one
# smoother call per wave. Used to price an extension before it is granted.
CALLS_PER_LANE_ROUND = 3


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_config(root):
    p = root / "config.json"
    if not p.exists():
        die(f"{p} not found — run init first")
    cfg = json.loads(p.read_text())
    # Backfill fields a config written by an older run will not have, so a
    # resumed run can still be extended.
    cfg.setdefault("extensions", [])
    cfg.setdefault("stops", {})
    for k, v in DEFAULT_CONFIG["stops"].items():
        cfg["stops"].setdefault(k, v)
    return cfg


def save_config(root, cfg):
    (root / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")


def initial_budget(cfg):
    """The budget agreed at intake, before any extension."""
    ext = cfg.get("extensions") or []
    return ext[0]["from_waves"] if ext else cfg["stops"]["budget_waves"]


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
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy — stops is nested
    if (root / "config.json").exists():
        # A re-cut re-inits with --force. Extensions the user already granted
        # are run history, not configuration — carry them across.
        cfg["extensions"] = json.loads((root / "config.json").read_text()).get("extensions", [])
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
    if args.hard_cap_waves is not None:
        if args.hard_cap_waves < cfg["stops"]["budget_waves"]:
            die("hard-cap-waves is below budget-waves — the cap is the ceiling extensions may not cross")
        cfg["stops"]["hard_cap_waves"] = args.hard_cap_waves
    if args.bar_kind:
        if args.bar_kind not in ("reference", "acceptance criteria", "hybrid"):
            die("bar-kind must be one of: reference, acceptance criteria, hybrid")
        cfg["bar_kind"] = args.bar_kind
    save_config(root, cfg)
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


MARGIN_RANK = {"decisive": 3, "clear": 2, "thin": 1}
SEVERITY_RANK = {"major": 3, "minor": 2, "none": 1}


def _recent_revert_rate(rounds, window=6):
    champ = [r for r in rounds if r["mode"] == "champion"][-window:]
    if len(champ) < 4:
        return None
    return sum(1 for r in champ if r.get("action") == "reverted") / len(champ)


def _dimension_trend(bar_recs, window=4):
    """Is this dimension still moving? Computed from the log, not from feeling."""
    recs = bar_recs[-window:]
    if len(recs) < 2:
        return {"improving": None, "note": "too few bar rounds to read a trend"}
    scores = [r["score"] for r in recs]
    score_delta = scores[-1] - scores[0]
    sev = [SEVERITY_RANK.get(r.get("severity"), 3) for r in recs]
    severity_easing = sev[-1] < sev[0]
    margins = [MARGIN_RANK[r["margin"]] for r in recs]
    # Narrowing = losing by less than we used to. Only meaningful while losing.
    losing = [r for r in recs if r["winner"] == "other"]
    margin_narrowing = len(losing) >= 2 and margins[-1] < margins[0]
    improving = score_delta > 0 or severity_easing or margin_narrowing
    bits = [f"score {scores[0]}→{scores[-1]}"]
    if severity_easing:
        bits.append("severity easing")
    if margin_narrowing:
        bits.append("margin narrowing")
    if not improving:
        bits.append("flat")
    return {"improving": improving, "note": ", ".join(bits)}


def _extension_evidence(rounds, cfg, per, retired):
    """Evidence and a verdict for the extend-or-stop decision.

    Verdict is one of: nothing-open, improving, mixed, at-ceiling. It is a
    reading of the log, not a decision — granting an extension is the user's.
    """
    open_dims = sorted(k for k, s in per.items() if not s["retired"])
    lines = []
    trends = {}
    for key in open_dims:
        lane, dim = key
        bar_recs = [
            r for r in rounds
            if r["lane"] == lane and r["dimension"] == dim and r["mode"] in ("blind", "rubric")
        ]
        t = _dimension_trend(bar_recs)
        trends[key] = t
        mark = {True: "still moving", False: "flat", None: "unknown"}[t["improving"]]
        gap = per[key]["open_gap"] or "no gap named in the last verdict"
        lines.append(f"  [{lane} / {dim}] {mark} ({t['note']}) — open gap: {gap}")

    revert_rate = _recent_revert_rate(rounds)
    if revert_rate is not None:
        lines.append(f"  recent revert rate: {int(revert_rate * 100)}%")

    moving = [k for k, t in trends.items() if t["improving"] is True]
    flat = [k for k, t in trends.items() if t["improving"] is False]
    if not open_dims:
        verdict = "nothing-open"
    elif not moving and not flat:
        # Every open dimension has too little history to read. Not a ceiling.
        verdict = "unclear"
    elif not moving:
        verdict = "at-ceiling"
    elif flat and revert_rate is not None and revert_rate > 0.5:
        verdict = "at-ceiling"
    elif len(moving) == len(open_dims):
        verdict = "improving"
    else:
        verdict = "mixed"
    return lines, verdict, sorted({lane for lane, _ in open_dims} - retired)


VERDICT_READS = {
    "nothing-open": "every judged dimension has retired — an extension buys polish, not gap closure",
    "improving": "every open dimension is still moving — an extension is likely to buy real gains",
    "mixed": "some dimensions are still moving and some are flat — extend on the moving ones, or re-cut",
    "unclear": "too few bar rounds on the open dimensions to read a trend — say so rather than selling the extension",
    "at-ceiling": "no open dimension is still moving — recommend stopping or re-cutting, not extending",
}


def _projected_calls(waves, open_lanes):
    lanes = max(1, len(open_lanes))
    return waves * (lanes * CALLS_PER_LANE_ROUND + 1)


def _print_extension_offer(rounds, cfg, per, retired, max_wave):
    """Printed when the budget stop fires. The run stops either way; this is the
    material the user needs to decide whether to fund more waves."""
    budget = cfg["stops"]["budget_waves"]
    cap = cfg["stops"].get("hard_cap_waves")
    lines, verdict, open_lanes = _extension_evidence(rounds, cfg, per, retired)
    print("\nBUDGET DEPLETED — stop cleanly, report, then OFFER AN EXTENSION.")
    print("Do not extend on your own. Do not keep running while you ask.\n")
    print("Evidence for the offer:")
    for line in lines or ["  (no open dimensions logged)"]:
        print(line)
    print(f"\n  read: {VERDICT_READS[verdict]}")
    if verdict == "nothing-open":
        print("\n  Nothing is open. Raise the bar (announced) or stop — do not fund waves"
              " against an artifact that has already retired every dimension.")
        return
    if cap is not None and budget >= cap:
        print(f"\n  Hard cap of {cap} waves reached — no extension may be granted. Stop and report.")
        return
    if verdict == "at-ceiling":
        print("\n  Offer the stop, not the waves: recommend re-cutting the lanes or ending the run."
              " `extend` refuses this read without --force.")
    else:
        suggested = min(4, cap - budget) if cap is not None else 4
        print(f"\nSuggested next wave block: {min(2, suggested)}–{suggested} waves"
              f" (~{_projected_calls(min(2, suggested), open_lanes)}–{_projected_calls(suggested, open_lanes)}"
              f" subagent calls over {len(open_lanes) or 1} open lane(s)).")
    if cap is not None:
        print(f"Hard cap: {cap} waves — {cap - budget} wave(s) of extension remain.")
    print("If the user grants it:")
    print("  python3 scripts/gauntlet.py extend --waves <N> --reason \"<evidence from the log>\"")
    print(f"(current: wave {max_wave} of {budget})")


def cmd_extend(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    stops = cfg["stops"]
    budget = stops["budget_waves"]
    cap = stops.get("hard_cap_waves")

    if args.waves <= 0:
        die("--waves must be a positive number of additional waves")
    reason = (args.reason or "").strip()
    if len(reason) < 12:
        die(
            "--reason is required and must cite the log — an extension without evidence is "
            "budget creep. Say what is still moving and what it will close."
        )

    max_wave = max((r["wave"] for r in rounds), default=0)
    if not rounds and not args.force:
        die("no rounds logged — raise --budget-waves at init instead of extending a run that has not started")
    if max_wave < budget and not args.force:
        die(
            f"budget is not depleted (wave {max_wave} of {budget}) — extend when it runs out, "
            "so the decision is made on evidence. Use --force to override."
        )

    new_budget = budget + args.waves
    if cap is not None and new_budget > cap:
        die(
            f"extension would take the budget to {new_budget} waves, past the agreed hard cap of {cap}. "
            f"Grant at most {max(0, cap - budget)} more wave(s), or ask the user to raise the cap."
        )

    first = initial_budget(cfg)
    if args.waves > first:
        print(
            f"warning: a {args.waves}-wave extension is larger than the whole original budget "
            f"({first}) — extend in small blocks so each one is decided on fresh evidence",
            file=sys.stderr,
        )

    per, retired = _lane_dim_status(rounds, cfg) if rounds else ({}, set())
    _, verdict, open_lanes = _extension_evidence(rounds, cfg, per, retired)
    if verdict == "at-ceiling" and not args.force:
        die(
            "the log shows no open dimension still moving — extending here spends the user's money on "
            "a ceiling. Re-cut the lanes or stop. Use --force if the user was shown this and chose to "
            "continue anyway."
        )

    cfg["extensions"].append({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "at_wave": max_wave,
        "from_waves": budget,
        "to_waves": new_budget,
        "waves": args.waves,
        "reason": reason,
        "log_read": verdict,
        "forced": bool(args.force),
        # The one worth flagging in the report: the log said "ceiling" and the
        # user funded more waves regardless.
        "against_log_read": bool(args.force and verdict == "at-ceiling"),
    })
    stops["budget_waves"] = new_budget
    save_config(root, cfg)

    n = len(cfg["extensions"])
    print(f"budget extended: {budget} → {new_budget} waves (+{args.waves}); extension {n} of this run")
    print(f"  projected: ~{_projected_calls(args.waves, open_lanes)} subagent calls over "
          f"{len(open_lanes) or 1} open lane(s)")
    print(f"  log read at grant time: {verdict}")
    if cap is not None:
        print(f"  hard cap {cap} waves — {cap - new_budget} wave(s) of extension remain")
    print("Record the extension in contract.md and on the workbench, then resume at the wave boundary.")


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

    ext = cfg.get("extensions") or []
    ext_note = (
        f" (initial {initial_budget(cfg)}, extended {len(ext)}×: "
        + ", ".join(f"+{e['waves']}" for e in ext) + ")"
        if ext else ""
    )
    print(f"wave {max_wave} of {budget} budgeted{ext_note}\n")
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

    if max_wave >= budget:
        _print_extension_offer(rounds, cfg, per, retired, max_wave)


def cmd_report(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    if not rounds:
        die("no rounds to report on")
    per, retired = _lane_dim_status(rounds, cfg)
    lines = ["# Gauntlet report (draft — lead agent completes the judgement fields)", ""]
    lines += [f"Waves run: {max(r['wave'] for r in rounds)} of {cfg['stops']['budget_waves']} budgeted", ""]
    ext = cfg.get("extensions") or []
    if ext:
        lines += [
            f"## Budget extensions ({len(ext)}; initial budget {initial_budget(cfg)} waves)",
            "",
        ]
        for e in ext:
            forced = " *(granted against the log read)*" if e.get("against_log_read") else ""
            lines.append(
                f"- at wave {e['at_wave']}: +{e['waves']} → {e['to_waves']} waves"
                f" — {e['reason']} [log read: {e.get('log_read', 'n/a')}]{forced}"
            )
        lines += [
            "",
            "(lead agent: say whether each extension paid for itself — it is the cheapest"
            " lesson in the report for the next run)",
            "",
        ]
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
    p.add_argument("--hard-cap-waves", type=int,
                   help="absolute ceiling extensions may not cross (optional; agreed at intake)")
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

    p = sub.add_parser("extend", help="raise the wave budget after the user grants an extension")
    p.add_argument("--waves", type=int, required=True, help="additional waves granted")
    p.add_argument("--reason", required=True, help="the user's grant, justified from the log")
    p.add_argument("--force", action="store_true",
                   help="override the depleted-budget and at-ceiling guards (user chose anyway)")
    p.set_defaults(fn=cmd_extend)

    p = sub.add_parser("report")
    p.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
