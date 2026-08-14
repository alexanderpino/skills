#!/usr/bin/env python3
"""gauntlet.py — deterministic state for a Gauntlet Loop run.

Stdlib only. The model decides; this script counts. Streaks, stall reads, stop
conditions, revert rates, cost and budget consumption are computed here so they
cannot drift in a long context — and so the lead agent never spends tokens
recomputing them.

Commands:
  init        Create the gauntlet/ state directory and config
  log-round   Append one validated comparison record to rounds.jsonl
  status      State per lane/dimension, the next-wave plan, fired stop conditions
  park        Stop spending on a lane/dimension that stopped moving (or resume it)
  board       Regenerate gauntlet/workbench.md from the log (no model tokens)
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
BAR_MODES = ("blind", "rubric")

DEFAULT_CONFIG = {
    "stops": {
        "bar_met_n": 2,
        "clean_streak_n": 2,
        # Rounds of no movement on a dimension before parking is recommended.
        # This is the prune: a lane that stopped moving stops getting funded.
        "no_progress_n": 3,
        "budget_waves": 12,
        # Absolute ceiling no extension may cross. null = no ceiling agreed, in
        # which case every extension needs the user again.
        "hard_cap_waves": None,
        # The score the target bar is set at. Retirement is judged against this,
        # not against a perfect 10 — a bar nobody can reach is not a target.
        "target_score": 7,
    },
    # Maximum lanes funded in one wave. Fewer lanes moving fast beats every lane
    # crawling: it is both the Kanban WIP limit and the main token control.
    "wip_limit": 3,
    "dimensions": ["overall"],
    "lanes": [],
    "bar_kind": "reference",
    # Granted budget extensions, appended by `extend`. The run's history of
    # "the budget ran out and the user chose to keep going".
    "extensions": [],
    # Lane/dimension pairs deliberately stopped short of retirement, appended by
    # `park`. Their gaps stay open in the report; their budget goes back.
    "parked": [],
}

# One builder call plus one combined critic call per lane per round is the
# default shape; a split-critic round costs one more. Used to price a wave and
# an extension before either is funded.
CALLS_PER_LANE_ROUND = 2
CALLS_PER_WAVE_OVERHEAD = 1  # the smoother, when it runs


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def load_config(root):
    p = root / "config.json"
    if not p.exists():
        die(f"{p} not found — run init first")
    cfg = json.loads(p.read_text())
    # Backfill fields a config written by an older run will not have, so a
    # resumed run can still be parked, priced and extended.
    for k, v in DEFAULT_CONFIG.items():
        if k == "stops":
            continue
        cfg.setdefault(k, json.loads(json.dumps(v)))
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


def parked_keys(cfg):
    return {(p["lane"], p["dimension"]) for p in cfg.get("parked") or []}


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
        # A re-cut re-inits with --force. Extensions and parks the user already
        # decided are run history, not configuration — carry them across.
        old = json.loads((root / "config.json").read_text())
        cfg["extensions"] = old.get("extensions", [])
        cfg["parked"] = old.get("parked", [])
    if args.lanes:
        cfg["lanes"] = [s.strip() for s in args.lanes.split(",") if s.strip()]
    if args.dimensions:
        cfg["dimensions"] = [s.strip() for s in args.dimensions.split(",") if s.strip()]
    for key, val in (
        ("bar_met_n", args.bar_met_n),
        ("clean_streak_n", args.clean_streak_n),
        ("no_progress_n", args.no_progress_n),
        ("budget_waves", args.budget_waves),
        ("target_score", args.target_score),
    ):
        if val is not None:
            cfg["stops"][key] = val
    if not (1 <= cfg["stops"]["target_score"] <= 10):
        die("target-score must be between 1 and 10")
    if cfg["stops"]["target_score"] == 10:
        print(
            "warning: target-score 10 makes every round a failure and no lane can retire — "
            "set the target where the bar actually is, and record any higher ambition as a "
            "stretch in contract.md",
            file=sys.stderr,
        )
    if args.wip_limit is not None:
        if args.wip_limit < 1:
            die("wip-limit must be at least 1")
        cfg["wip_limit"] = args.wip_limit
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
        ("contract.md", "# Gauntlet contract\n\n(goal / target bar / stretch / inspection / "
                        "stops / kill criteria / budget / autonomy / workbench)\n"),
        ("ownership.md", "# File ownership — refreshed every wave\n\n| lane | owned paths |\n|---|---|\n"),
    ):
        p = root / name
        if not p.exists():
            p.write_text(header)
    (root / "rounds.jsonl").touch()
    lanes = len(cfg["lanes"]) or 1
    per_wave = min(lanes, cfg["wip_limit"]) * CALLS_PER_LANE_ROUND + CALLS_PER_WAVE_OVERHEAD
    print(f"initialised {root}/ — freeze bar artifacts into {root}/bar/ before wave 1")
    print(
        f"projected cost: ~{per_wave} subagent calls per wave "
        f"(WIP limit {cfg['wip_limit']} lane(s)), ~{per_wave * cfg['stops']['budget_waves']} "
        f"over the {cfg['stops']['budget_waves']}-wave budget"
    )


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
    if (args.lane, args.dimension) in parked_keys(cfg):
        print(
            f"warning: [{args.lane} / {args.dimension}] is parked — you are spending on a lane "
            "the run already decided to stop funding. Resume it explicitly "
            "(`park --resume`) or leave it parked.",
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
        "ts": now(),
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
    if args.calls is not None:
        if args.calls < 0:
            die("--calls cannot be negative")
        rec["calls"] = args.calls

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
        if args.gap and args.severity != "none" and len(args.gap.strip()) < 12:
            die("the named gap is too thin to build against — say what differs and where")
        rec["severity"] = args.severity
        rec["gap"] = args.gap or "none"
        target = cfg["stops"]["target_score"]
        if args.severity == "major" and args.score >= target:
            print(
                f"warning: score {args.score} is at or above the target of {target} but severity is "
                "'major' — the critic is scoring one bar and grading against another. Check which "
                "bar the verdict used.",
                file=sys.stderr,
            )

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


MARGIN_RANK = {"decisive": 3, "clear": 2, "thin": 1}
SEVERITY_RANK = {"major": 3, "minor": 2, "none": 1}


def _revert_rate(champ_recs, window=6):
    recs = champ_recs[-window:]
    if len(recs) < 4:
        return None
    return sum(1 for r in recs if r.get("action") == "reverted") / len(recs)


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


def _stall_read(bar_recs, champ_recs, n):
    """Has this dimension stopped paying for its rounds?

    Returns (stalled, note). Stalling is the prune signal: it is not a verdict
    on the artifact, only on whether more rounds of *this* lane are worth money.
    """
    if len(bar_recs) < n:
        return False, f"{len(bar_recs)} bar round(s) — too early to call it"
    trend = _dimension_trend(bar_recs, window=n)
    if trend["improving"] is False:
        return True, f"no movement in {n} rounds ({trend['note']})"
    rate = _revert_rate(champ_recs)
    if rate is not None and rate > 0.5:
        return True, f"revert rate {int(rate * 100)}% — challengers losing more than winning"
    # The same gap named three times running is a structural ceiling, not a lane
    # that needs one more push.
    gaps = [r.get("gap") for r in bar_recs[-n:] if r.get("severity") not in (None, "none")]
    if len(gaps) >= 3 and len(set(gaps)) == 1:
        return True, f"the same gap named {len(gaps)} rounds running — structural, not closeable here"
    return False, trend["note"]


def _lane_dim_status(rounds, cfg):
    """Returns {(lane, dim): stats}, retired lanes, closed lanes.

    'retired' = the target bar is met or no closeable gap is left.
    'parked'  = deliberately unfunded, gap still open.
    'closed'  = every dimension of the lane is one or the other; the lane costs
                nothing more either way.
    """
    stops = cfg["stops"]
    parked = parked_keys(cfg)
    keys = {}
    lane_rounds = {}
    for r in rounds:
        keys.setdefault((r["lane"], r["dimension"]), []).append(r)
        lane_rounds.setdefault(r["lane"], set()).add((r["wave"], r["round"]))
    logged_calls = {}
    for r in rounds:
        if "calls" in r:
            logged_calls[r["lane"]] = logged_calls.get(r["lane"], 0) + r["calls"]
    out = {}
    for key, recs in keys.items():
        lane, _dim = key
        bar_recs = [r for r in recs if r["mode"] in BAR_MODES]
        champ_recs = [r for r in recs if r["mode"] == "champion"]
        bar_met, clean = _streaks(bar_recs)
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
        gaps_closed = sum(
            1 for i, r in enumerate(bar_recs)
            if r.get("severity") == "none"
            and any(p.get("severity") in ("major", "minor") for p in bar_recs[:i])
        )
        retired = bar_met >= stops["bar_met_n"] or clean >= stops["clean_streak_n"]
        stalled, stall_note = _stall_read(bar_recs, champ_recs, stops["no_progress_n"])
        is_parked = key in parked
        trend = _dimension_trend(bar_recs, window=stops["no_progress_n"])
        out[key] = {
            "bar_rounds": len(bar_recs),
            "promotions": sum(1 for r in champ_recs if r.get("action") == "promoted"),
            "reverts": sum(1 for r in champ_recs if r.get("action") == "reverted"),
            "bar_met_streak": bar_met,
            "clean_streak": clean,
            "recent_margins": margins,
            "rubric_share": round(rubric_share, 2),
            "open_gap": last_gap,
            "last_score": bar_recs[-1]["score"] if bar_recs else None,
            "gaps_closed": gaps_closed,
            "retired": retired,
            "parked": is_parked,
            "stalled": stalled and not retired and not is_parked,
            "stall_note": stall_note,
            "trend": trend,
            "lane_calls": logged_calls.get(lane, len(lane_rounds[lane]) * CALLS_PER_LANE_ROUND),
            "state": "RETIRED" if retired else "PARKED" if is_parked else "STALLED" if stalled else "OPEN",
        }
    # A lane retires only when every *declared* dimension has retired — a
    # dimension nobody ever judged must not let the lane out early. A lane
    # *closes* when each dimension is retired or parked: nothing left to fund.
    declared = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    lanes = {lane for lane, _ in out}
    retired_lanes = {
        lane for lane in lanes
        if all(out.get((lane, d), {}).get("retired") for d in declared)
    }
    closed_lanes = {
        lane for lane in lanes
        if all(
            out.get((lane, d), {}).get("retired") or out.get((lane, d), {}).get("parked")
            for d in declared
        )
    }
    return out, retired_lanes, closed_lanes


def _active_keys(per):
    return [k for k, s in per.items() if not s["retired"] and not s["parked"]]


def _next_wave_plan(per, cfg):
    """Which lanes the next wave should fund, ranked by evidence.

    Moving dimensions first, then unread ones, then stalled. The WIP limit cuts
    the tail: funding every lane a little is how a budget dies without a result.
    """
    active = _active_keys(per)
    if not active:
        return [], []
    rank = {True: 0, None: 1, False: 2}

    def sort_key(k):
        s = per[k]
        sev_rank = 0 if s["open_gap"] and s["trend"]["improving"] is not False else 1
        return (
            2 if s["stalled"] else rank[s["trend"]["improving"]],
            sev_rank,
            s["bar_rounds"],
        )

    ordered = sorted(active, key=sort_key)
    lanes_in_order = []
    for lane, _dim in ordered:
        if lane not in lanes_in_order:
            lanes_in_order.append(lane)
    wip = cfg.get("wip_limit") or DEFAULT_CONFIG["wip_limit"]
    funded = lanes_in_order[:wip]
    deferred = lanes_in_order[wip:]
    return funded, deferred


def _park_candidates(per):
    return sorted(k for k, s in per.items() if s["stalled"])


def _extension_evidence(rounds, cfg, per, retired):
    """Evidence and a verdict for the extend-or-stop decision.

    Verdict is one of: nothing-open, improving, mixed, at-ceiling, unclear. It
    is a reading of the log, not a decision — granting an extension is the
    user's. Parked dimensions are not open: the run already chose to stop
    funding them, and pricing an extension over them is how parks get undone by
    accident.
    """
    open_dims = sorted(_active_keys(per))
    lines = []
    trends = {}
    for key in open_dims:
        lane, dim = key
        bar_recs = [
            r for r in rounds
            if r["lane"] == lane and r["dimension"] == dim and r["mode"] in BAR_MODES
        ]
        t = _dimension_trend(bar_recs, window=cfg["stops"]["no_progress_n"])
        trends[key] = t
        mark = {True: "still moving", False: "flat", None: "unknown"}[t["improving"]]
        gap = per[key]["open_gap"] or "last verdict named no gap"
        lines.append(f"  [{lane} / {dim}] {mark} ({t['note']}) — open gap: {gap}")

    parked = sorted(k for k, s in per.items() if s["parked"])
    for lane, dim in parked:
        lines.append(f"  [{lane} / {dim}] parked — not priced into an extension")

    revert_rate = _revert_rate([r for r in rounds if r["mode"] == "champion"])
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
    "nothing-open": "every judged dimension has retired or been parked — an extension buys polish, not gap closure",
    "improving": "every open dimension is still moving — an extension is likely to buy real gains",
    "mixed": "some dimensions are still moving and some are flat — extend on the moving ones only, park the rest",
    "unclear": "too few bar rounds on the open dimensions to read a trend — say so rather than selling the extension",
    "at-ceiling": "no open dimension is still moving — recommend stopping or re-cutting, not extending",
}


def _projected_calls(waves, open_lanes, wip=None):
    lanes = max(1, len(open_lanes))
    if wip:
        lanes = min(lanes, wip)
    return waves * (lanes * CALLS_PER_LANE_ROUND + CALLS_PER_WAVE_OVERHEAD)


def _print_extension_offer(rounds, cfg, per, retired, max_wave):
    """Printed when the budget stop fires. The run stops either way; this is the
    material the user needs to decide whether to fund more waves."""
    budget = cfg["stops"]["budget_waves"]
    cap = cfg["stops"].get("hard_cap_waves")
    wip = cfg.get("wip_limit")
    lines, verdict, open_lanes = _extension_evidence(rounds, cfg, per, retired)
    print("\nBUDGET DEPLETED — stop cleanly, report, then OFFER AN EXTENSION.")
    print("Do not extend on your own. Do not keep running while you ask.\n")
    print("Evidence for the offer:")
    for line in lines or ["  (no open dimensions logged)"]:
        print(line)
    print(f"\n  read: {VERDICT_READS[verdict]}")
    if verdict == "nothing-open":
        print("\n  Nothing is open. Raise the bar (announced) or stop — do not fund waves"
              " against an artifact that has already retired or parked every dimension.")
        return
    if cap is not None and budget >= cap:
        print(f"\n  Hard cap of {cap} waves reached — no extension may be granted. Stop and report.")
        return
    if verdict == "at-ceiling":
        print("\n  Offer the stop, not the waves: recommend parking the flat dimensions and"
              " re-cutting or ending the run. `extend` refuses this read without --force.")
    else:
        suggested = min(4, cap - budget) if cap is not None else 4
        low = min(2, suggested)
        print(f"\nSuggested next wave block: {low}–{suggested} waves"
              f" (~{_projected_calls(low, open_lanes, wip)}–{_projected_calls(suggested, open_lanes, wip)}"
              f" subagent calls over {len(open_lanes) or 1} open lane(s), WIP limit {wip}).")
    if cap is not None:
        print(f"Hard cap: {cap} waves — {cap - budget} wave(s) of extension remain.")
    print("If the user grants it:")
    print("  python3 scripts/gauntlet.py extend --waves <N> --reason \"<evidence from the log>\"")
    print(f"(current: wave {max_wave} of {budget})")


def cmd_park(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    reason = (args.reason or "").strip()
    if len(reason) < 12:
        die("--reason must cite the log — a park is a spending decision and the report carries it")
    key = (args.lane, args.dimension)
    parked = cfg.setdefault("parked", [])
    max_wave = max((r["wave"] for r in rounds), default=0)

    if args.resume:
        match = [p for p in parked if (p["lane"], p["dimension"]) == key]
        if not match:
            die(f"[{args.lane} / {args.dimension}] is not parked")
        cfg["parked"] = [p for p in parked if (p["lane"], p["dimension"]) != key]
        cfg.setdefault("park_history", []).extend(
            [{**m, "resumed_at_wave": max_wave, "resume_reason": reason, "resumed_ts": now()} for m in match]
        )
        save_config(root, cfg)
        print(f"resumed [{args.lane} / {args.dimension}] — it is funded again from the next wave")
        print("Resume only on new evidence (a re-cut, a fixed inspection path, a new bar). "
              "Restarting a lane on hope is sunk cost with extra steps.")
        return

    per, _retired, _closed = _lane_dim_status(rounds, cfg) if rounds else ({}, set(), set())
    stats = per.get(key)
    if stats is None and not args.force:
        die(f"no rounds logged for [{args.lane} / {args.dimension}] — nothing to park (use --force)")
    if stats and stats["retired"] and not args.force:
        die(f"[{args.lane} / {args.dimension}] has retired — it already costs nothing (use --force)")
    if stats and not stats["stalled"] and not args.force:
        die(
            f"[{args.lane} / {args.dimension}] is still moving ({stats['trend']['note']}) — "
            "parking a lane that is still paying for its rounds throws away the run's best work. "
            "Use --force if you are parking it for a reason outside the log (scope, priority)."
        )
    if key in parked_keys(cfg):
        die(f"[{args.lane} / {args.dimension}] is already parked")

    parked.append({
        "ts": now(),
        "lane": args.lane,
        "dimension": args.dimension,
        "at_wave": max_wave,
        "reason": reason,
        "open_gap": (stats or {}).get("open_gap") or "",
        "bar_rounds": (stats or {}).get("bar_rounds", 0),
        "forced": bool(args.force),
    })
    save_config(root, cfg)
    per, _retired, _closed = _lane_dim_status(rounds, cfg) if rounds else ({}, set(), set())
    funded, deferred = _next_wave_plan(per, cfg)
    print(f"parked [{args.lane} / {args.dimension}] at wave {max_wave} — {reason}")
    if (stats or {}).get("open_gap"):
        print(f"  open gap carried into the report: {stats['open_gap']}")
    print(f"  next wave now funds: {', '.join(funded) or 'nothing — every lane is retired or parked'}")
    if deferred:
        print(f"  waiting behind the WIP limit: {', '.join(deferred)}")


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

    per, retired, _closed = _lane_dim_status(rounds, cfg) if rounds else ({}, set(), set())
    _, verdict, open_lanes = _extension_evidence(rounds, cfg, per, retired)
    if verdict == "at-ceiling" and not args.force:
        die(
            "the log shows no open dimension still moving — extending here spends the user's money on "
            "a ceiling. Park the flat dimensions, re-cut the lanes, or stop. Use --force if the user "
            "was shown this and chose to continue anyway."
        )
    stalled = _park_candidates(per)
    if stalled and not args.force:
        die(
            "park before you extend — these dimensions stopped paying for their rounds and would "
            "eat the new waves:\n"
            + "\n".join(f"  [{lane} / {dim}] {per[(lane, dim)]['stall_note']}" for lane, dim in stalled)
            + "\n  python3 scripts/gauntlet.py park --lane <lane> --dimension <dim> --reason \"<log read>\""
        )

    cfg["extensions"].append({
        "ts": now(),
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
    print(f"  projected: ~{_projected_calls(args.waves, open_lanes, cfg.get('wip_limit'))} subagent calls over "
          f"{len(open_lanes) or 1} open lane(s)")
    print(f"  log read at grant time: {verdict}")
    if cap is not None:
        print(f"  hard cap {cap} waves — {cap - new_budget} wave(s) of extension remain")
    print("Record the extension in contract.md, run `board`, then resume at the wave boundary.")


def cmd_status(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    if not rounds:
        print("no rounds logged yet")
        return
    per, retired, closed = _lane_dim_status(rounds, cfg)
    max_wave = max(r["wave"] for r in rounds)
    budget = cfg["stops"]["budget_waves"]
    wip = cfg.get("wip_limit")

    ext = cfg.get("extensions") or []
    ext_note = (
        f", initial {initial_budget(cfg)}, extended {len(ext)}×: "
        + ", ".join(f"+{e['waves']}" for e in ext)
        if ext else ""
    )
    lane_calls = {}
    for (lane, _dim), s in per.items():
        lane_calls[lane] = s["lane_calls"]
    spent = sum(lane_calls.values())
    closed_gaps = sum(s["gaps_closed"] for s in per.values())
    per_gap = f" (~{spent / closed_gaps:.0f} calls each)" if closed_gaps else ""
    print(f"wave {max_wave} of {budget} budgeted{ext_note} | ~{spent} calls spent"
          f" | {closed_gaps} gap(s) closed{per_gap} | WIP limit {wip}\n")

    for (lane, dim), s in sorted(per.items()):
        head = f"[{lane} / {dim}] {s['state']}"
        print(head)
        print(f"  bar {s['bar_rounds']}  promoted {s['promotions']}  reverted {s['reverts']}"
              f"  streaks bar-met {s['bar_met_streak']} clean {s['clean_streak']}"
              f"  rubric {s['rubric_share']}")
        print(f"  score {s['last_score']}/{cfg['stops']['target_score']} target"
              f"  margins {' → '.join(s['recent_margins']) or '—'}  trend: {s['trend']['note']}")
        if s["stalled"]:
            print(f"  PARK RECOMMENDED: {s['stall_note']}")
        if s["open_gap"]:
            print(f"  open gap: {s['open_gap']}")
        print()

    funded, deferred = _next_wave_plan(per, cfg)
    stalled = _park_candidates(per)
    if funded:
        cost = _projected_calls(1, funded, wip)
        print(f"NEXT WAVE (WIP {wip}): {', '.join(funded)}  → ~{cost} subagent calls")
        if deferred:
            print(f"  waiting: {', '.join(deferred)} — do not widen the wave to fit them in")
    else:
        print("NEXT WAVE: nothing to fund — every dimension is retired or parked")
    if stalled:
        print("PARK FIRST:")
        for lane, dim in stalled:
            print(f"  [{lane} / {dim}] {per[(lane, dim)]['stall_note']}")
            print(f"    python3 scripts/gauntlet.py park --lane {lane} --dimension {dim} --reason \"<log read>\"")
    print()

    fired = []
    if max_wave >= budget:
        fired.append(f"budget (wave {max_wave} >= {budget})")
    all_lanes = {lane for lane, _ in per}
    if all_lanes and all_lanes == retired:
        fired.append("all lanes retired (bar-met / clean-streak)")
    elif all_lanes and all_lanes == closed:
        fired.append("all lanes retired or parked — nothing left to fund; stop and report the open gaps")
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


def cmd_board(args):
    """Regenerate the workbench from the log. Deterministic, so keeping the
    user's progress surface current costs zero model tokens."""
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    out = root / "workbench.md"
    if not rounds:
        out.write_text("# Gauntlet workbench\n\nNo rounds logged yet.\n")
        print(f"wrote {out}")
        return
    per, _retired, _closed = _lane_dim_status(rounds, cfg)
    max_wave = max(r["wave"] for r in rounds)
    budget = cfg["stops"]["budget_waves"]
    ext = cfg.get("extensions") or []
    spent = sum({lane: s["lane_calls"] for (lane, _d), s in per.items()}.values())
    funded, deferred = _next_wave_plan(per, cfg)

    L = [
        "# Gauntlet workbench",
        "",
        f"Updated {now()} — generated by `gauntlet.py board`. Do not edit by hand.",
        "",
        f"- Wave **{max_wave} of {budget}**"
        + (f" (initial {initial_budget(cfg)}, extended {len(ext)}×)" if ext else ""),
        f"- Cost so far: ~{spent} subagent calls",
        f"- Target score: {cfg['stops']['target_score']}/10 | WIP limit: {cfg.get('wip_limit')} lane(s)",
        f"- Next wave funds: {', '.join(funded) or 'nothing — all lanes retired or parked'}"
        + (f" (waiting: {', '.join(deferred)})" if deferred else ""),
        "",
    ]

    def table(keys, cols, row):
        if not keys:
            return ["_none_", ""]
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(row(k)) + " |" for k in keys]
        return lines + [""]

    active = sorted(k for k, s in per.items() if s["state"] in ("OPEN", "STALLED"))
    L += ["## Active", ""]
    L += table(
        active,
        ["lane / dimension", "rounds", "score", "trend", "open gap", "last evidence"],
        lambda k: [
            f"{k[0]} / {k[1]}" + (" ⚠ park?" if per[k]["stalled"] else ""),
            str(per[k]["bar_rounds"]),
            f"{per[k]['last_score']}/{cfg['stops']['target_score']}",
            per[k]["trend"]["note"],
            (per[k]["open_gap"] or "—").replace("|", "/"),
            next(
                (r["evidence"] for r in reversed(rounds)
                 if (r["lane"], r["dimension"]) == k),
                "—",
            ).replace("|", "/"),
        ],
    )

    L += ["## Parked (unfunded, gap still open)", ""]
    parked = cfg.get("parked") or []
    if parked:
        L += ["| lane / dimension | parked at | reason | open gap |", "|---|---|---|---|"]
        L += [
            f"| {p['lane']} / {p['dimension']} | wave {p['at_wave']} | {p['reason']} |"
            f" {(p.get('open_gap') or '—').replace('|', '/')} |"
            for p in parked
        ]
        L += [""]
    else:
        L += ["_none_", ""]

    L += ["## Retired", ""]
    retired_keys = sorted(k for k, s in per.items() if s["retired"])
    L += table(
        retired_keys,
        ["lane / dimension", "rounds", "how", "gaps closed"],
        lambda k: [
            f"{k[0]} / {k[1]}",
            str(per[k]["bar_rounds"]),
            "bar-met" if per[k]["bar_met_streak"] >= cfg["stops"]["bar_met_n"] else "clean-streak",
            str(per[k]["gaps_closed"]),
        ],
    )

    L += ["## Recent rounds", ""]
    L += ["| wave.round | lane / dim | mode | winner | margin | score | note |", "|---|---|---|---|---|---|---|"]
    for r in rounds[-12:]:
        note = r.get("gap") if r["mode"] in BAR_MODES else r.get("action", "")
        L.append(
            f"| {r['wave']}.{r['round']} | {r['lane']} / {r['dimension']} | {r['mode']} |"
            f" {r['winner']} | {r['margin']} | {r['score']} | {(note or '—').replace('|', '/')} |"
        )
    L.append("")
    out.write_text("\n".join(L))
    print(f"wrote {out}")


def cmd_report(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    if not rounds:
        die("no rounds to report on")
    per, _retired, _closed = _lane_dim_status(rounds, cfg)
    lane_calls = {lane: s["lane_calls"] for (lane, _d), s in per.items()}
    spent = sum(lane_calls.values())
    closed_gaps = sum(s["gaps_closed"] for s in per.values())
    lines = ["# Gauntlet report (draft — lead agent completes the judgement fields)", ""]
    lines += [f"Waves run: {max(r['wave'] for r in rounds)} of {cfg['stops']['budget_waves']} budgeted", ""]
    lines += [
        f"Cost: ~{spent} subagent calls for {closed_gaps} closed gap(s)"
        + (f" (~{spent / closed_gaps:.0f} calls per gap)" if closed_gaps else "")
        + f"; target score {cfg['stops']['target_score']}/10",
        "",
    ]
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
    parked = cfg.get("parked") or []
    if parked:
        lines += ["## Parked lanes (stopped on purpose, not finished)", ""]
        for p in parked:
            lines.append(
                f"- **{p['lane']} / {p['dimension']}** — parked at wave {p['at_wave']} after"
                f" {p.get('bar_rounds', 0)} bar rounds: {p['reason']}"
                + (f" | open gap: {p['open_gap']}" if p.get("open_gap") else "")
            )
        lines += [
            "",
            "(lead agent: for each park, say what would have to change for it to be worth"
            " restarting — a re-cut, a new asset, a different bar. 'More waves' is not an answer.)",
            "",
        ]
    blind = sum(1 for r in rounds if r["mode"] == "blind")
    rubric = sum(1 for r in rounds if r["mode"] == "rubric")
    lines += [f"Verdict evidence: {blind} blind rounds, {rubric} rubric rounds (not equivalent evidence)", ""]
    lines += ["## Lanes", ""]
    for (lane, dim), s in sorted(per.items()):
        lines.append(
            f"- **{lane} / {dim}** — {s['state'].lower()}; {s['bar_rounds']} bar rounds,"
            f" {s['reverts']} reverts, last score {s['last_score']}/{cfg['stops']['target_score']}"
        )
    lines += ["", "## Open gaps (do not soften this section)", ""]
    any_gap = False
    for (lane, dim), s in sorted(per.items()):
        if s["open_gap"]:
            any_gap = True
            state = " *(parked)*" if s["parked"] else ""
            lines.append(f"- [{lane} / {dim}]{state} {s['open_gap']}")
    if not any_gap:
        lines.append("- none recorded — verify this against the last wave's verdicts before believing it")
    lines += [
        "",
        "## Distance to the stretch bar, if one was set",
        "",
        "(lead agent: the target bar is what retirement was judged against. If contract.md"
        " also names a stretch, say plainly how far the artifact is from it and whether that"
        " distance is closeable by iteration at all.)",
        "",
        "## Was the loop still improving at the stop?",
        "",
        "(lead agent: answer from score trends, margins and revert rate — do not fudge this)",
        "",
    ]
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
    p.add_argument("--no-progress-n", type=int,
                   help="rounds of no movement before a dimension is flagged for parking (default 3)")
    p.add_argument("--target-score", type=int,
                   help="score the target bar sits at, 1-10 (default 7); record higher ambition as a stretch")
    p.add_argument("--wip-limit", type=int, help="max lanes funded per wave (default 3)")
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
    p.add_argument("--calls", type=int,
                   help="subagent calls this round actually cost (optional; estimated when omitted)")
    p.set_defaults(fn=cmd_log_round)

    p = sub.add_parser("status")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("park", help="stop funding a lane/dimension that stopped moving")
    p.add_argument("--lane", required=True)
    p.add_argument("--dimension", default="overall")
    p.add_argument("--reason", required=True, help="the log read that justifies stopping the spend")
    p.add_argument("--resume", action="store_true",
                   help="unpark: fund it again, on new evidence only")
    p.add_argument("--force", action="store_true",
                   help="park a dimension the log still reads as moving (scope or priority call)")
    p.set_defaults(fn=cmd_park)

    p = sub.add_parser("board", help="regenerate gauntlet/workbench.md from the log")
    p.set_defaults(fn=cmd_board)

    p = sub.add_parser("extend", help="raise the wave budget after the user grants an extension")
    p.add_argument("--waves", type=int, required=True, help="additional waves granted")
    p.add_argument("--reason", required=True, help="the user's grant, justified from the log")
    p.add_argument("--force", action="store_true",
                   help="override the depleted-budget, unparked-stall and at-ceiling guards")
    p.set_defaults(fn=cmd_extend)

    p = sub.add_parser("report")
    p.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
