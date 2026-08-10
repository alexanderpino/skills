#!/usr/bin/env python3
"""gauntlet.py — deterministic state for a Gauntlet Loop run.

Stdlib only. The model decides; this script counts. Streaks, stop conditions,
revert rates and budget consumption are computed here so they cannot drift in a
long context.

Commands:
  init        Create the gauntlet/ state directory and config
  log-round   Append one validated comparison record to rounds.jsonl
  spend       Record token spend that is not attached to a logged round
  status      Per-lane/per-dimension streaks, revert rate, fired stop conditions
  tier        Current effort tier, its allowance, and whether escalation is earned
  escalate    Move up the effort ladder once the evidence justifies the spend
  shelve      Park a flat dimension so it stops consuming calls
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

# The effort ladder. A gauntlet buys its way up, it does not start at the top:
# each tier may spend `share` of the total token budget, and moving to the next
# one costs a piece of evidence. An unpromising run therefore dies having spent
# a fifth of the budget rather than all of it.
#
# `lanes`/`dims` are ceilings for the tier (null = no ceiling). `critic_calls`
# is the number of critic calls per lane per round: 1 = one collapsed screening
# call answering promotion and bar together, 2 = the full split, per dimension.
DEFAULT_LADDER = [
    {"name": "probe", "share": 0.05, "lanes": 1, "dims": 1,
     "critic_calls": 1, "builder_model": "mid", "critic_model": "cheap"},
    {"name": "pilot", "share": 0.15, "lanes": 2, "dims": None,
     "critic_calls": 1, "builder_model": "mid", "critic_model": "cheap"},
    {"name": "campaign", "share": 0.40, "lanes": None, "dims": None,
     "critic_calls": 2, "builder_model": "high", "critic_model": "mid"},
    {"name": "polish", "share": 0.40, "lanes": None, "dims": None,
     "critic_calls": 2, "builder_model": "high", "critic_model": "high"},
]

DEFAULT_CONFIG = {
    "stops": {
        "bar_met_n": 2,
        "clean_streak_n": 2,
        "budget_waves": 12,
        # The budget the user actually pays. null = not set, which `status`
        # complains about: waves are not a unit of money.
        "budget_tokens": None,
        # Absolute ceilings no extension may cross. null = no ceiling agreed, in
        # which case every extension needs the user again.
        "hard_cap_waves": None,
        "hard_cap_tokens": None,
        # A dimension that has not moved in this many bar rounds is flagged for
        # shelving — it is buying reverts, not gap closure.
        "flat_rounds_n": 3,
    },
    "dimensions": ["overall"],
    "lanes": [],
    "bar_kind": "reference",
    # Blended price of a million tokens, for printing the budget in the unit the
    # user thinks in. null = print tokens only.
    "cost_eur_per_mtok": None,
    "effort": {
        "tier": 0,
        "ladder": DEFAULT_LADDER,
        # Appended by `escalate`: the run's history of "the evidence justified
        # spending more per round".
        "history": [],
    },
    # Appended by `shelve`: dimensions parked mid-run and why.
    "shelved": [],
    # Granted budget extensions, appended by `extend`. The run's history of
    # "the budget ran out and the user chose to keep going".
    "extensions": [],
}


def tier_spec(cfg, tier=None):
    ladder = cfg.get("effort", {}).get("ladder") or DEFAULT_LADDER
    t = cfg["effort"]["tier"] if tier is None else tier
    return ladder[min(max(t, 0), len(ladder) - 1)]


def calls_per_lane_round(cfg, tier=None):
    """One builder call plus the tier's critic calls, per declared dimension.

    The old flat 3 undercounted every multi-dimension run — a 2-dimension lane
    at full split is 5 calls, not 3, and quoting 3 at intake is how a budget the
    user agreed to turns into one they did not.
    """
    spec = tier_spec(cfg, tier)
    dims = len(cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"])
    if spec["dims"]:
        dims = min(dims, spec["dims"])
    return 1 + spec["critic_calls"] * dims


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
    cfg.setdefault("shelved", [])
    cfg.setdefault("cost_eur_per_mtok", None)
    cfg.setdefault("stops", {})
    for k, v in DEFAULT_CONFIG["stops"].items():
        cfg["stops"].setdefault(k, v)
    effort = cfg.setdefault("effort", {})
    effort.setdefault("tier", 0)
    effort.setdefault("ladder", json.loads(json.dumps(DEFAULT_LADDER)))
    effort.setdefault("history", [])
    # Where this config came from, so helpers can reach the ledgers without
    # every caller threading the path through. Stripped again on save.
    cfg["_root"] = str(root)
    return cfg


def save_config(root, cfg):
    out = {k: v for k, v in cfg.items() if k != "_root"}
    (root / "config.json").write_text(json.dumps(out, indent=2) + "\n")


def initial_budget(cfg):
    """The budget agreed at intake, before any extension."""
    ext = cfg.get("extensions") or []
    return ext[0]["from_waves"] if ext else cfg["stops"]["budget_waves"]


def _load_jsonl(p):
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
            die(f"{p.name} line {i} is corrupt: {e}")
    return out


def load_rounds(root):
    return _load_jsonl(root / "rounds.jsonl")


def load_spend(root):
    return _load_jsonl(root / "spend.jsonl")


def total_spend(root, rounds=None):
    """Every token the run has cost, from both ledgers.

    Rounds carry the spend of the calls that produced them; spend.jsonl carries
    everything else — builders, the smoother, the lead agent's own passes.
    """
    rounds = load_rounds(root) if rounds is None else rounds
    return (sum(r.get("tokens") or 0 for r in rounds)
            + sum(s.get("tokens") or 0 for s in load_spend(root)))


def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def fmt_cost(cfg, tokens):
    """Tokens, plus money whenever the run knows its own price."""
    rate = cfg.get("cost_eur_per_mtok")
    if not rate:
        return f"{fmt_tokens(tokens)} tok"
    return f"{fmt_tokens(tokens)} tok ≈ €{tokens / 1_000_000 * rate:,.2f}"


def tier_allowance(cfg, tier=None):
    """Cumulative token allowance up to and including a tier.

    Cumulative, not per-tier: a probe that came in under budget hands its
    unspent share up the ladder rather than losing it.
    """
    budget = cfg["stops"].get("budget_tokens")
    if not budget:
        return None
    ladder = cfg["effort"]["ladder"]
    t = cfg["effort"]["tier"] if tier is None else tier
    t = min(max(t, 0), len(ladder) - 1)
    return int(budget * sum(s["share"] for s in ladder[: t + 1]))


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
    if args.budget_tokens is not None:
        if args.budget_tokens <= 0:
            die("--budget-tokens must be positive")
        cfg["stops"]["budget_tokens"] = args.budget_tokens
    if args.flat_rounds_n is not None:
        cfg["stops"]["flat_rounds_n"] = args.flat_rounds_n
    if args.cost_per_mtok is not None:
        cfg["cost_eur_per_mtok"] = args.cost_per_mtok
    if args.hard_cap_waves is not None:
        if args.hard_cap_waves < cfg["stops"]["budget_waves"]:
            die("hard-cap-waves is below budget-waves — the cap is the ceiling extensions may not cross")
        cfg["stops"]["hard_cap_waves"] = args.hard_cap_waves
    if args.hard_cap_tokens is not None:
        bt = cfg["stops"].get("budget_tokens")
        if bt and args.hard_cap_tokens < bt:
            die("hard-cap-tokens is below budget-tokens — the cap is the ceiling extensions may not cross")
        cfg["stops"]["hard_cap_tokens"] = args.hard_cap_tokens
    if not cfg["stops"].get("budget_tokens"):
        print(
            "warning: no --budget-tokens set. Waves are not a unit of money — a wave costs "
            "whatever its lanes and dimensions happen to cost, and the run cannot tell you "
            "what it spent. Set a token budget at intake.",
            file=sys.stderr,
        )
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
    (root / "spend.jsonl").touch()
    spec = tier_spec(cfg)
    print(f"initialised {root}/ — freeze bar artifacts into {root}/bar/ before wave 1")
    print(f"effort tier 0 ({spec['name']}): {spec['lanes'] or 'all'} lane(s), "
          f"{spec['critic_calls']} critic call(s) per lane per round, "
          f"builder={spec['builder_model']} critic={spec['critic_model']}")
    allow = tier_allowance(cfg, 0)
    if allow:
        print(f"  tier allowance: {fmt_cost(cfg, allow)} of {fmt_cost(cfg, cfg['stops']['budget_tokens'])} total")
    print("  run the probe, then `gauntlet.py tier` — do not open more lanes before the evidence does")


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

    if args.tokens is not None and args.tokens < 0:
        die("--tokens must be non-negative")

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
        "tier": cfg["effort"]["tier"],
        "tokens": args.tokens,
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
    if args.tokens is None:
        print("  note: no --tokens on this record — the run cannot price itself without them",
              file=sys.stderr)


def cmd_spend(args):
    """Record spend that produced no round: builders, the smoother, lead passes."""
    root = Path(args.root)
    cfg = load_config(root)
    if args.tokens < 0:
        die("--tokens must be non-negative")
    note = (args.note or "").strip()
    if not note:
        die("--note is required — unattributed spend is how a budget disappears without a story")
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "wave": args.wave,
        "role": args.role,
        "tokens": args.tokens,
        "note": note,
        "tier": cfg["effort"]["tier"],
    }
    with (root / "spend.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")
    spent = total_spend(root)
    budget = cfg["stops"].get("budget_tokens")
    line = f"recorded {fmt_cost(cfg, args.tokens)} ({args.role}) — run total {fmt_cost(cfg, spent)}"
    if budget:
        line += f" of {fmt_cost(cfg, budget)} ({spent / budget * 100:.0f}%)"
    print(line)


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


def _shelved_keys(cfg):
    return {(s["lane"], s["dimension"]) for s in cfg.get("shelved") or []}


def _lane_dim_status(rounds, cfg):
    """Returns {(lane, dim): stats} and set of retired lanes."""
    stops = cfg["stops"]
    shelved = _shelved_keys(cfg)
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
        is_shelved = key in shelved
        out[key] = {
            "bar_rounds": len(bar_recs),
            "promotions": sum(1 for r in champ_recs if r.get("action") == "promoted"),
            "reverts": reverts,
            "bar_met_streak": bar_met,
            "clean_streak": clean,
            "recent_margins": margins,
            "rubric_share": round(rubric_share, 2),
            "open_gap": last_gap,
            "shelved": is_shelved,
            # Shelved dimensions stop consuming calls, so they are closed for
            # scheduling — but they are not retired, and the report says so.
            "retired": (bar_met >= stops["bar_met_n"]
                        or clean >= stops["clean_streak_n"]
                        or is_shelved),
            "flat": _is_flat(bar_recs, stops.get("flat_rounds_n", 3)),
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


def _is_flat(bar_recs, n):
    """No movement across the last n bar rounds — the shelving signal.

    Flat means: no score gain, no severity easing, no margin narrowing. It is
    computed over the whole window, not the last pair, so one lucky round does
    not un-flatten a dimension that has stalled.
    """
    if n < 2 or len(bar_recs) < n:
        return False
    recs = bar_recs[-n:]
    scores = [r["score"] for r in recs]
    sev = [SEVERITY_RANK.get(r.get("severity"), 3) for r in recs]
    margins = [MARGIN_RANK[r["margin"]] for r in recs]
    losing = [r for r in recs if r["winner"] == "other"]
    return not (max(scores) > scores[0]
                or min(sev) < sev[0]
                or (len(losing) >= 2 and min(margins) < margins[0]))


MARGIN_RANK = {"decisive": 3, "clear": 2, "thin": 1}
SEVERITY_RANK = {"major": 3, "minor": 2, "none": 1}


def _recent_revert_rate(rounds, window=6):
    champ = [r for r in rounds if r["mode"] == "champion"][-window:]
    if len(champ) < 4:
        return None
    return sum(1 for r in champ if r.get("action") == "reverted") / len(champ)


def _dimension_trend(bar_recs, window=4, flat_n=3):
    """Is this dimension still moving? Computed from the log, not from feeling.

    The recent window wins: a dimension that climbed early and has not moved in
    its last `flat_n` rounds is flat, whatever the wider window says. Reading it
    the other way round is how a stalled lane keeps getting funded on the
    strength of progress it made four rounds ago.
    """
    if _is_flat(bar_recs, flat_n):
        return {"improving": False, "note": f"flat for {flat_n} rounds"}
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
        t = _dimension_trend(bar_recs, flat_n=cfg["stops"].get("flat_rounds_n", 3))
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


def _projected_calls(cfg, waves, open_lanes):
    """Priced at the *current* tier — a polish-tier wave costs more than a probe."""
    lanes = max(1, len(open_lanes))
    return waves * (lanes * calls_per_lane_round(cfg) + 1)


def _projected_tokens(root, cfg, waves, open_lanes, rounds=None):
    """Project the cost of N more waves from this run's own measured cost per call.

    Estimating from a table is guessing; estimating from the log is arithmetic.
    Returns None until the run has priced at least a few of its own calls.
    """
    rounds = load_rounds(root) if rounds is None else rounds
    priced = [r for r in rounds if r.get("tokens")]
    if len(priced) < 3:
        return None
    per_critic_call = sum(r["tokens"] for r in priced) / len(priced)
    # Builders and the smoother are the expensive half and are recorded
    # separately; use their own measured average when the run has one.
    non_round = [s for s in load_spend(root) if s.get("tokens")]
    per_other = (sum(s["tokens"] for s in non_round) / len(non_round)
                 if non_round else per_critic_call * 2)
    lanes = max(1, len(open_lanes))
    spec = tier_spec(cfg)
    dims = len(cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"])
    if spec["dims"]:
        dims = min(dims, spec["dims"])
    critic_calls = waves * lanes * spec["critic_calls"] * dims
    other_calls = waves * (lanes + 1)  # one builder per lane, one smoother
    return int(critic_calls * per_critic_call + other_calls * per_other)


def _escalation_gates(root, cfg, rounds):
    """Has this tier earned the next one? Four gates, all computed from the log.

    The ladder exists so that an idea that will not work dies cheap. Escalating
    on optimism defeats the whole mechanism, so every gate is a fact in the log
    rather than a judgement in the conversation.
    """
    tier = cfg["effort"]["tier"]
    at_tier = [r for r in rounds if r.get("tier", 0) == tier]
    bar_at_tier = [r for r in at_tier if r["mode"] in ("blind", "rubric")]
    gates = []

    gates.append((
        "rounds at this tier",
        len(bar_at_tier) >= 1,
        f"{len(bar_at_tier)} bar round(s) logged at tier {tier}"
        if bar_at_tier else "no bar round logged at this tier — run it before buying a bigger one",
    ))

    # The bar discriminates: at least one verdict that named something specific,
    # or an evidence-backed clean verdict. A vague tier is a broken bar, and
    # more money makes a broken bar no sharper.
    actionable = [
        r for r in bar_at_tier
        if (r.get("severity") == "none" and r.get("evidence"))
        or (r.get("gap") and len(r["gap"]) >= 20)
    ]
    gates.append((
        "the bar discriminates",
        bool(actionable),
        f"{len(actionable)} verdict(s) named something specific"
        if actionable else "verdicts are vague — sharpen the bar, do not escalate",
    ))

    # Inspection reached the real artifact. log-round already requires evidence;
    # what this catches is the same stale evidence cited round after round.
    evid = [r.get("evidence") for r in bar_at_tier if r.get("evidence")]
    fresh = len(set(evid)) > 1 or len(evid) <= 1
    gates.append((
        "inspection is live",
        fresh,
        "evidence varies across rounds" if fresh
        else "every round cites the same evidence — the inspection path is probably stale",
    ))

    # Movement. At tier 0 a single actionable verdict is the whole signal:
    # a probe proves the loop can see and judge, not that the artifact climbed.
    per, retired = _lane_dim_status(rounds, cfg)
    _, verdict, _ = _extension_evidence(rounds, cfg, per, retired)
    if tier == 0:
        # A genuine probe is one or two rounds, and the only thing it has to
        # prove is that the loop can see and judge. But a tier 0 that has been
        # run long enough to stall has told you something else, and "it is only
        # a probe" is not a reason to fund the next tier past it.
        moving = bool(actionable) and verdict != "at-ceiling"
        note = ("probe produced an actionable verdict" if moving
                else "nothing to build on yet" if not actionable
                else "the probe ran long enough to stall — fix or stop, do not scale")
    else:
        moving = verdict in ("improving", "mixed", "unclear")
        note = f"log read: {verdict}"
    gates.append(("the artifact is moving", moving, note))

    return gates, verdict


def cmd_tier(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    ladder = cfg["effort"]["ladder"]
    tier = cfg["effort"]["tier"]
    spec = tier_spec(cfg)
    spent = total_spend(root, rounds)
    allow = tier_allowance(cfg)

    print(f"effort tier {tier} of {len(ladder) - 1} — {spec['name']}")
    print(f"  scope: {spec['lanes'] or 'all'} lane(s), {spec['dims'] or 'all'} dimension(s), "
          f"{spec['critic_calls']} critic call(s) per lane per round")
    print(f"  models: builder={spec['builder_model']}  critic={spec['critic_model']}")
    print(f"  ~{calls_per_lane_round(cfg)} subagent calls per lane per round at this tier")
    if allow:
        pct = spent / allow * 100 if allow else 0
        print(f"  spend: {fmt_cost(cfg, spent)} of {fmt_cost(cfg, allow)} allowed through this tier ({pct:.0f}%)")
        if spent >= allow:
            print("  TIER ALLOWANCE DEPLETED — escalate on evidence, or stop. Do not keep running here.")
    else:
        print(f"  spend: {fmt_cost(cfg, spent)} (no token budget set — set one at intake)")

    for e in cfg["effort"]["history"]:
        print(f"  escalated at wave {e['at_wave']}: tier {e['from_tier']} → {e['to_tier']} — {e['reason']}")

    if tier >= len(ladder) - 1:
        print("\nTop of the ladder. There is no more effort to buy — the remaining levers are "
              "budget extensions, a re-cut, or stopping.")
        return

    gates, _ = _escalation_gates(root, cfg, rounds)
    nxt = ladder[tier + 1]
    print(f"\nGates to tier {tier + 1} ({nxt['name']}):")
    for name, ok, note in gates:
        print(f"  [{'x' if ok else ' '}] {name} — {note}")
    if all(ok for _, ok, _ in gates):
        print(f"\nEarned. Escalating raises cost per round to ~{calls_per_lane_round(cfg, tier + 1)} "
              f"calls per lane, on {nxt['builder_model']}/{nxt['critic_model']} models.")
        print("  python3 scripts/gauntlet.py escalate --reason \"<evidence from the log>\"")
    else:
        print("\nNot earned. Fix the failing gate at this tier's price, or stop the run. "
              "Escalating past a failing gate buys a bigger version of the same problem.")


def cmd_escalate(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    ladder = cfg["effort"]["ladder"]
    tier = cfg["effort"]["tier"]

    if tier >= len(ladder) - 1:
        die("already at the top of the effort ladder — extend the budget or re-cut, do not escalate")
    reason = (args.reason or "").strip()
    if len(reason) < 12:
        die("--reason is required and must cite the log — escalating on optimism is what the ladder exists to prevent")

    gates, verdict = _escalation_gates(root, cfg, rounds)
    failing = [name for name, ok, _ in gates if not ok]
    if failing and not args.force:
        die(
            "escalation gates not met: " + ", ".join(failing) + ". "
            "Fix these at the current tier's price. Use --force only when the user was shown "
            "the failing gates and chose to fund the next tier anyway."
        )

    max_wave = max((r["wave"] for r in rounds), default=0)
    cfg["effort"]["history"].append({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "at_wave": max_wave,
        "from_tier": tier,
        "to_tier": tier + 1,
        "spend_at": total_spend(root, rounds),
        "reason": reason,
        "log_read": verdict,
        "forced": bool(args.force),
        "failing_gates": failing,
    })
    cfg["effort"]["tier"] = tier + 1
    save_config(root, cfg)
    spec = tier_spec(cfg)
    print(f"escalated: tier {tier} → {tier + 1} ({spec['name']})")
    print(f"  scope now: {spec['lanes'] or 'all'} lane(s), {spec['critic_calls']} critic call(s) per lane per round")
    print(f"  models now: builder={spec['builder_model']}  critic={spec['critic_model']}")
    print(f"  ~{calls_per_lane_round(cfg)} calls per lane per round (was {calls_per_lane_round(cfg, tier)})")
    allow = tier_allowance(cfg)
    if allow:
        print(f"  allowance through this tier: {fmt_cost(cfg, allow)}")
    print("Record the escalation in contract.md and on the workbench.")


def cmd_shelve(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    dims = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    if args.dimension not in dims:
        die(f"dimension {args.dimension!r} is not declared in config.json ({', '.join(dims)})")
    reason = (args.reason or "").strip()
    if len(reason) < 12:
        die("--reason is required — say what the log shows, so the report can say why this was parked")
    key = (args.lane, args.dimension)
    if key in _shelved_keys(cfg):
        die(f"{args.lane}/{args.dimension} is already shelved")

    per, _ = _lane_dim_status(rounds, cfg)
    s = per.get(key)
    if s and not s["flat"] and not args.force:
        die(
            f"{args.lane}/{args.dimension} is not flat by the log "
            f"(margins {' → '.join(s['recent_margins']) or '—'}) — shelving a moving dimension "
            "throws away the gains it was about to make. Use --force if the user chose to park it."
        )

    cfg["shelved"].append({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "lane": args.lane,
        "dimension": args.dimension,
        "at_wave": max((r["wave"] for r in rounds), default=0),
        "reason": reason,
        "open_gap": (s or {}).get("open_gap"),
        "forced": bool(args.force),
    })
    save_config(root, cfg)
    print(f"shelved {args.lane}/{args.dimension} — it stops consuming calls from the next wave")
    print("  it is parked, not retired: the report keeps its open gap")


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
        lo = min(2, suggested)
        print(f"\nSuggested next wave block: {lo}–{suggested} waves"
              f" (~{_projected_calls(cfg, lo, open_lanes)}–{_projected_calls(cfg, suggested, open_lanes)}"
              f" subagent calls over {len(open_lanes) or 1} open lane(s)).")
        root = Path(cfg.get("_root", "gauntlet"))
        t_lo = _projected_tokens(root, cfg, lo, open_lanes, rounds)
        t_hi = _projected_tokens(root, cfg, suggested, open_lanes, rounds)
        if t_lo and t_hi:
            print(f"  measured from this run: ~{fmt_cost(cfg, t_lo)} – {fmt_cost(cfg, t_hi)}")
        else:
            print("  (cannot price it — too few rounds carried --tokens; quote calls, not money)")
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
    # Either budget being depleted is grounds to extend: whichever ran out first
    # is the one that stopped the run.
    spent_now = total_spend(root, rounds)
    tokens_depleted = bool(stops.get("budget_tokens")) and spent_now >= stops["budget_tokens"]
    if max_wave < budget and not tokens_depleted and not args.force:
        die(
            f"neither budget is depleted (wave {max_wave} of {budget}; "
            f"{fmt_cost(cfg, spent_now)} spent) — extend when one runs out, "
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

    tok_budget = stops.get("budget_tokens")
    tok_cap = stops.get("hard_cap_tokens")
    new_tok = tok_budget
    if args.tokens is not None:
        if args.tokens <= 0:
            die("--tokens must be a positive number of additional tokens")
        if not tok_budget:
            die("no token budget to extend — this run was initialised without --budget-tokens")
        new_tok = tok_budget + args.tokens
        if tok_cap is not None and new_tok > tok_cap:
            die(
                f"extension would take the token budget to {fmt_tokens(new_tok)}, past the agreed "
                f"hard cap of {fmt_tokens(tok_cap)}. Grant at most "
                f"{fmt_tokens(max(0, tok_cap - tok_budget))} more, or ask the user to raise the cap."
            )
    elif tok_budget:
        proj = _projected_tokens(root, cfg, args.waves, [], rounds)
        print(
            f"warning: {args.waves} more waves were granted but the token budget is unchanged at "
            f"{fmt_cost(cfg, tok_budget)}" + (f" (projected need ~{fmt_cost(cfg, proj)})" if proj else "")
            + " — the run will stop on tokens before it runs the waves. Pass --tokens too.",
            file=sys.stderr,
        )

    cfg["extensions"].append({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "at_wave": max_wave,
        "from_waves": budget,
        "to_waves": new_budget,
        "waves": args.waves,
        "from_tokens": tok_budget,
        "to_tokens": new_tok,
        "reason": reason,
        "log_read": verdict,
        "forced": bool(args.force),
        # The one worth flagging in the report: the log said "ceiling" and the
        # user funded more waves regardless.
        "against_log_read": bool(args.force and verdict == "at-ceiling"),
    })
    stops["budget_waves"] = new_budget
    if new_tok is not None:
        stops["budget_tokens"] = new_tok
    save_config(root, cfg)

    n = len(cfg["extensions"])
    print(f"budget extended: {budget} → {new_budget} waves (+{args.waves}); extension {n} of this run")
    print(f"  projected: ~{_projected_calls(cfg, args.waves, open_lanes)} subagent calls over "
          f"{len(open_lanes) or 1} open lane(s)")
    proj = _projected_tokens(root, cfg, args.waves, open_lanes, rounds)
    if proj:
        print(f"  projected spend: ~{fmt_cost(cfg, proj)} (measured from this run's own rounds)")
    print(f"  log read at grant time: {verdict}")
    if cap is not None:
        print(f"  hard cap {cap} waves — {cap - new_budget} wave(s) of extension remain")
    print("Record the extension in contract.md and on the workbench, then resume at the wave boundary.")


def _fired_stops(cfg, rounds, per, retired, max_wave, spent):
    """Every stop condition currently firing or signalling.

    Shared by `status` and `board` so the terminal and the workbench cannot
    disagree about whether the run should still be running.
    """
    fired = []
    budget = cfg["stops"]["budget_waves"]
    tok_budget = cfg["stops"].get("budget_tokens")
    if max_wave >= budget:
        fired.append(f"budget (wave {max_wave} >= {budget})")
    if tok_budget and spent >= tok_budget:
        fired.append(f"token budget ({fmt_cost(cfg, spent)} >= {fmt_cost(cfg, tok_budget)})")
    allow = tier_allowance(cfg)
    if allow and spent >= allow and cfg["effort"]["tier"] < len(cfg["effort"]["ladder"]) - 1:
        fired.append(f"tier {cfg['effort']['tier']} allowance depleted — escalate on evidence (`tier`) or stop")
    all_lanes = {lane for lane, _ in per}
    if all_lanes and all_lanes == retired:
        if any(s["shelved"] for s in per.values()):
            fired.append("no lane is still running — some dimensions shelved rather than retired; "
                         "the report must say which")
        else:
            fired.append("all lanes retired (bar-met / clean-streak)")
    recent = [r for r in rounds if r["mode"] == "champion"][-6:]
    if len(recent) >= 4 and sum(1 for r in recent if r.get("action") == "reverted") > len(recent) / 2:
        fired.append("judgment signal: revert rate over 50% in recent rounds — likely at the ceiling")
    return fired


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
    tok_budget = cfg["stops"].get("budget_tokens")
    spent = total_spend(root, rounds)

    ext = cfg.get("extensions") or []
    ext_note = (
        f" (initial {initial_budget(cfg)}, extended {len(ext)}×: "
        + ", ".join(f"+{e['waves']}" for e in ext) + ")"
        if ext else ""
    )
    spec = tier_spec(cfg)
    print(f"wave {max_wave} of {budget} budgeted{ext_note}")
    print(f"tier {cfg['effort']['tier']} ({spec['name']}) — "
          f"~{calls_per_lane_round(cfg)} calls per lane per round, "
          f"builder={spec['builder_model']} critic={spec['critic_model']}")
    if tok_budget:
        allow = tier_allowance(cfg)
        print(f"spend {fmt_cost(cfg, spent)} of {fmt_cost(cfg, tok_budget)} "
              f"({spent / tok_budget * 100:.0f}%); tier allowance {fmt_cost(cfg, allow)}")
        per_wave = spent / max_wave if max_wave else 0
        if per_wave:
            left = max(0, tok_budget - spent)
            print(f"  burn rate {fmt_cost(cfg, int(per_wave))}/wave → "
                  f"~{left / per_wave:.1f} wave(s) of budget left at this rate")
    else:
        print(f"spend {fmt_cost(cfg, spent)} — no token budget set; this run cannot tell you when to stop paying")
    print()

    for (lane, dim), s in sorted(per.items()):
        if s["shelved"]:
            flag = " SHELVED"
        elif s["retired"]:
            flag = " RETIRED"
        else:
            flag = ""
        print(f"[{lane} / {dim}]{flag}")
        print(f"  bar rounds {s['bar_rounds']}  promoted {s['promotions']}  reverted {s['reverts']}")
        print(f"  bar-met streak {s['bar_met_streak']}  clean streak {s['clean_streak']}  rubric share {s['rubric_share']}")
        print(f"  recent margins: {' → '.join(s['recent_margins']) or '—'}")
        if s["open_gap"]:
            print(f"  open gap: {s['open_gap']}")
        if s["flat"] and not s["retired"]:
            print(f"  FLAT for {cfg['stops']['flat_rounds_n']} bar rounds — shelve it or re-cut it;"
                  f" running it again costs ~{calls_per_lane_round(cfg)} calls per round for no movement")
            print(f"    python3 scripts/gauntlet.py shelve --lane {lane} --dimension {dim} --reason \"...\"")
        print()

    # The trend read every wave, not only once the money is gone. A dimension
    # that stalls at wave 3 should cost three waves of calls, not twelve.
    lines, verdict, _ = _extension_evidence(rounds, cfg, per, retired)
    if lines:
        print("Mid-run read (act on this at the wave boundary):")
        for line in lines:
            print(line)
        print(f"  read: {VERDICT_READS[verdict]}\n")

    fired = _fired_stops(cfg, rounds, per, retired, max_wave, spent)
    if fired:
        print("STOP CONDITIONS FIRED / SIGNALLED:")
        for f in fired:
            print(f"  - {f}")
    else:
        print("no stop condition fired")

    if max_wave >= budget or (tok_budget and spent >= tok_budget):
        _print_extension_offer(rounds, cfg, per, retired, max_wave)


def cmd_report(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    if not rounds:
        die("no rounds to report on")
    per, retired = _lane_dim_status(rounds, cfg)
    spent = total_spend(root, rounds)
    tok_budget = cfg["stops"].get("budget_tokens")
    lines = ["# Gauntlet report (draft — lead agent completes the judgement fields)", ""]
    lines += [f"Waves run: {max(r['wave'] for r in rounds)} of {cfg['stops']['budget_waves']} budgeted"]
    if tok_budget:
        lines += [f"Spend: {fmt_cost(cfg, spent)} of {fmt_cost(cfg, tok_budget)} budgeted "
                  f"({spent / tok_budget * 100:.0f}%)"]
    else:
        lines += [f"Spend: {fmt_cost(cfg, spent)} recorded (no token budget was set — say so)"]
    lines += [""]

    hist = cfg["effort"].get("history") or []
    spec = tier_spec(cfg)
    lines += [f"## Effort ladder", "",
              f"Ended at tier {cfg['effort']['tier']} ({spec['name']}).", ""]
    if hist:
        for e in hist:
            forced = " *(forced past failing gates: " + ", ".join(e["failing_gates"]) + ")" if e.get("forced") else ""
            lines.append(
                f"- wave {e['at_wave']}: tier {e['from_tier']} → {e['to_tier']} at "
                f"{fmt_cost(cfg, e['spend_at'])} spent — {e['reason']} [log read: {e['log_read']}]{forced}"
            )
        lines += ["", "(lead agent: say whether each escalation paid for itself — the probe that "
                  "should not have been escalated is the cheapest lesson this report can carry)", ""]
    else:
        lines += ["The run never escalated. Say whether that was the ladder working "
                  "(a cheap honest no) or the run stopping too early.", ""]

    shelved = cfg.get("shelved") or []
    if shelved:
        lines += ["## Shelved dimensions (parked, not retired)", ""]
        for s in shelved:
            lines.append(f"- wave {s['at_wave']}: **{s['lane']} / {s['dimension']}** — {s['reason']}"
                         + (f"; open gap: {s['open_gap']}" if s.get("open_gap") else ""))
        lines += [""]
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
        state = "shelved" if s["shelved"] else ("retired" if s["retired"] else "open")
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


STATE_SCHEMA_VERSION = 1


def _contract_goal(root):
    """The GOAL line from contract.md, for the board's header.

    Best-effort: the contract is prose written by the lead agent, so a missing
    or reworded goal line degrades to no title rather than to an error.
    """
    p = root / "contract.md"
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        s = line.strip().lstrip("*_# ").strip()
        if s.upper().startswith("GOAL"):
            return s[4:].lstrip(":*_ ").strip() or None
    return None


def build_state(root, cfg, rounds):
    """The workbench spec: everything the board renders, in one document.

    This is the contract between the run and the UI, the way an OpenAPI
    document is the contract between a service and Swagger UI. The HTML is
    generic and never edited; only this changes. Schema: references/workbench.md.
    """
    per, retired = _lane_dim_status(rounds, cfg)
    max_wave = max((r["wave"] for r in rounds), default=0)
    spent = total_spend(root, rounds)
    spend_recs = load_spend(root)
    tok_budget = cfg["stops"].get("budget_tokens")
    rate = cfg.get("cost_eur_per_mtok")
    spec = tier_spec(cfg)
    ladder = cfg["effort"]["ladder"]
    lines, verdict, open_lanes = (_extension_evidence(rounds, cfg, per, retired)
                                  if rounds else ([], "unclear", []))
    eur = (lambda t: round(t / 1_000_000 * rate, 2) if rate else None)

    # Spend by role, so the board can say where the money went rather than only
    # how much of it is gone. Critic calls are the ones attached to rounds.
    by_role = {"critic": sum(r.get("tokens") or 0 for r in rounds)}
    for s in spend_recs:
        by_role[s.get("role", "other")] = by_role.get(s.get("role", "other"), 0) + (s.get("tokens") or 0)

    by_tier = {}
    for r in rounds:
        by_tier[str(r.get("tier", 0))] = by_tier.get(str(r.get("tier", 0)), 0) + (r.get("tokens") or 0)
    for s in spend_recs:
        by_tier[str(s.get("tier", 0))] = by_tier.get(str(s.get("tier", 0)), 0) + (s.get("tokens") or 0)

    bar_rounds = [r for r in rounds if r["mode"] in ("blind", "rubric")]
    state = {
        "schema": STATE_SCHEMA_VERSION,
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "goal": _contract_goal(root),
        "bar_kind": cfg.get("bar_kind"),
        "wave": max_wave,
        "budget_waves": cfg["stops"]["budget_waves"],
        "initial_budget_waves": initial_budget(cfg),
        "read": verdict,
        "read_note": VERDICT_READS.get(verdict),
        "evidence_lines": [ln.strip() for ln in lines],
        "fired": _fired_stops(cfg, rounds, per, retired, max_wave, spent),
        "stops": {
            "bar_met_n": cfg["stops"]["bar_met_n"],
            "clean_streak_n": cfg["stops"]["clean_streak_n"],
            "flat_rounds_n": cfg["stops"].get("flat_rounds_n", 3),
            "hard_cap_waves": cfg["stops"].get("hard_cap_waves"),
            "hard_cap_tokens": cfg["stops"].get("hard_cap_tokens"),
        },
        "tier": {
            "index": cfg["effort"]["tier"],
            "name": spec["name"],
            "builder_model": spec["builder_model"],
            "critic_model": spec["critic_model"],
            "calls_per_lane_round": calls_per_lane_round(cfg),
            "allowance_tokens": tier_allowance(cfg),
            "ladder": [
                {"index": i, "name": t["name"], "share": t["share"],
                 "lanes": t["lanes"], "dims": t["dims"],
                 "critic_calls": t["critic_calls"],
                 "builder_model": t["builder_model"], "critic_model": t["critic_model"],
                 "state": ("done" if i < cfg["effort"]["tier"]
                           else "current" if i == cfg["effort"]["tier"] else "locked")}
                for i, t in enumerate(ladder)
            ],
            "history": cfg["effort"].get("history") or [],
        },
        "spend": {
            "tokens": spent,
            "budget_tokens": tok_budget,
            "eur": eur(spent),
            "budget_eur": eur(tok_budget) if tok_budget else None,
            "pct": round(spent / tok_budget * 100) if tok_budget else None,
            "per_wave": int(spent / max_wave) if max_wave else None,
            "waves_left_at_rate": (round((tok_budget - spent) / (spent / max_wave), 1)
                                   if tok_budget and max_wave and spent else None),
            "by_role": by_role,
            "by_tier": by_tier,
            "priced_rounds": sum(1 for r in rounds if r.get("tokens")),
            "total_rounds": len(rounds),
        },
        "evidence_mix": {
            "blind": sum(1 for r in bar_rounds if r["mode"] == "blind"),
            "rubric": sum(1 for r in bar_rounds if r["mode"] == "rubric"),
        },
        "extensions": cfg.get("extensions") or [],
        "shelved": cfg.get("shelved") or [],
        "columns": {"open": [], "flat": [], "shelved": [], "retired": []},
        "rounds": [],
    }

    for (lane, dim), s in sorted(per.items()):
        recs = [r for r in rounds if r["lane"] == lane and r["dimension"] == dim]
        bar_recs = [r for r in recs if r["mode"] in ("blind", "rubric")]
        last = bar_recs[-1] if bar_recs else None
        card = {
            "lane": lane, "dimension": dim,
            "bar_rounds": s["bar_rounds"], "promotions": s["promotions"], "reverts": s["reverts"],
            "bar_met_streak": s["bar_met_streak"], "clean_streak": s["clean_streak"],
            "bar_met_n": cfg["stops"]["bar_met_n"], "clean_streak_n": cfg["stops"]["clean_streak_n"],
            "margins": s["recent_margins"],
            "scores": [r["score"] for r in bar_recs][-12:],
            "severity": last.get("severity") if last else None,
            "gap": s["open_gap"],
            "evidence": last.get("evidence") if last else None,
            "rubric_share": s["rubric_share"],
            "tokens": sum(r.get("tokens") or 0 for r in recs),
            "trend": _dimension_trend(bar_recs, flat_n=cfg["stops"].get("flat_rounds_n", 3))["note"]
            if bar_recs else None,
        }
        if s["shelved"]:
            shelf = next((x for x in cfg.get("shelved") or []
                          if x["lane"] == lane and x["dimension"] == dim), {})
            card["shelved_reason"] = shelf.get("reason")
            card["shelved_at_wave"] = shelf.get("at_wave")
            state["columns"]["shelved"].append(card)
        elif s["retired"]:
            card["retired_by"] = ("bar-met" if s["bar_met_streak"] >= cfg["stops"]["bar_met_n"]
                                  else "clean-streak")
            state["columns"]["retired"].append(card)
        elif s["flat"]:
            state["columns"]["flat"].append(card)
        else:
            state["columns"]["open"].append(card)

    # Newest first, bounded — the board is a glance surface, not an archive.
    # rounds.jsonl remains the full record.
    for r in rounds[-80:][::-1]:
        state["rounds"].append({
            "ts": r.get("ts"), "wave": r["wave"], "round": r["round"],
            "lane": r["lane"], "dimension": r["dimension"], "mode": r["mode"],
            "winner": r["winner"], "margin": r["margin"], "score": r.get("score"),
            "severity": r.get("severity"), "gap": r.get("gap"), "action": r.get("action"),
            "evidence": r.get("evidence"), "champion_ref": r.get("champion_ref"),
            "critic_framing": r.get("critic_framing"), "tier": r.get("tier", 0),
            "tokens": r.get("tokens"),
        })
    return state


def cmd_board(args):
    """Write the workbench spec — everything the board renders.

    The board is generated, never hand-written. A subagent that has to open an
    HTML file to report progress pays for the whole file every round; this makes
    the progress surface cost one deterministic command instead.

    Two files, same content: `state.json` for anything that reads JSON, and
    `state.js` (one assignment to `window.GAUNTLET_STATE`) so the board also
    works when it is opened straight off disk, where browsers refuse to `fetch`
    a local file.
    """
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    state = build_state(root, cfg, rounds)
    blob = json.dumps(state, indent=2)
    (root / "state.json").write_text(blob + "\n")
    (root / "state.js").write_text(
        "// Generated by gauntlet.py board. Do not edit; do not edit workbench.html either.\n"
        "window.GAUNTLET_STATE = " + blob + ";\n"
    )
    print(f"wrote {root}/state.json and {root}/state.js — the workbench renders them; do not edit the HTML")


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
    p.add_argument("--budget-tokens", type=int,
                   help="the budget the user actually pays; waves are not a unit of money")
    p.add_argument("--cost-per-mtok", type=float,
                   help="blended EUR per million tokens, so status can print money")
    p.add_argument("--flat-rounds-n", type=int,
                   help="bar rounds without movement before a dimension is flagged for shelving (default 3)")
    p.add_argument("--hard-cap-waves", type=int,
                   help="absolute ceiling extensions may not cross (optional; agreed at intake)")
    p.add_argument("--hard-cap-tokens", type=int,
                   help="absolute token ceiling extensions may not cross (optional; agreed at intake)")
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
    p.add_argument("--tokens", type=int,
                   help="tokens the calls behind this record cost — without it the run cannot price itself")
    p.set_defaults(fn=cmd_log_round)

    p = sub.add_parser("spend", help="record spend not attached to a round (builders, smoother, lead passes)")
    p.add_argument("--tokens", type=int, required=True)
    p.add_argument("--role", default="builder", help="builder|smoother|lead|other")
    p.add_argument("--wave", type=int)
    p.add_argument("--note", required=True, help="what this bought")
    p.set_defaults(fn=cmd_spend)

    p = sub.add_parser("status")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("tier", help="current effort tier and whether escalation is earned")
    p.set_defaults(fn=cmd_tier)

    p = sub.add_parser("escalate", help="move up the effort ladder once the evidence justifies it")
    p.add_argument("--reason", required=True, help="the evidence from the log that earned the next tier")
    p.add_argument("--force", action="store_true",
                   help="escalate past failing gates (user saw them and chose to fund it anyway)")
    p.set_defaults(fn=cmd_escalate)

    p = sub.add_parser("shelve", help="park a flat dimension so it stops consuming calls")
    p.add_argument("--lane", required=True)
    p.add_argument("--dimension", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--force", action="store_true", help="shelve a dimension the log does not call flat")
    p.set_defaults(fn=cmd_shelve)

    p = sub.add_parser("board", help="regenerate gauntlet/state.json for the workbench")
    p.set_defaults(fn=cmd_board)

    p = sub.add_parser("extend", help="raise the wave budget after the user grants an extension")
    p.add_argument("--waves", type=int, required=True, help="additional waves granted")
    p.add_argument("--tokens", type=int, help="additional tokens granted alongside the waves")
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
