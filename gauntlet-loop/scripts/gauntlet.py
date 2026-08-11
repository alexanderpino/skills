#!/usr/bin/env python3
"""gauntlet.py — deterministic state for a Gauntlet Loop run.

Stdlib only. The model decides; this script counts. Streaks, stop conditions,
revert rates and budget consumption are computed here so they cannot drift in a
long context.

Commands:
  init        Create the gauntlet/ state directory and config
  plan        Propose the next wave from the log, priced against running everything
  aim         State a round's hypothesis and expected outcome before it runs
  log-round   Append one validated comparison record to rounds.jsonl
  skip        Record a round deliberately not run, and what it saved
  spend       Record token spend that is not attached to a logged round
  status      Per-lane/per-dimension streaks, revert rate, fired stop conditions
  tier        Current effort tier, its allowance, and whether escalation is earned
  escalate    Move up the effort ladder once the evidence justifies the spend
  shelve      Park a flat dimension so it stops consuming calls
  unshelve    Re-open a shelved dimension on new information — reinvest, not retry
  extend      Raise the wave budget after the user grants an extension
  report      Draft the end-of-run gauntlet report from the log
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path, PurePosixPath

# `oracle` is a bar comparison decided by measurement rather than by a model —
# a frame time, an LCP number, a passing test. It costs no critic tokens and is
# stronger evidence than either model mode, so it counts toward the streaks and
# is reported separately in the evidence mix.
MODES = ("blind", "rubric", "oracle", "champion")
BAR_MODES = ("blind", "rubric", "oracle")
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
# Which model each tier label resolves to. The ladder speaks in labels so a run
# can be re-pointed at different models without touching its logic; this is the
# only place the labels become real model ids.
#
# Prices are USD per million tokens as published on 2026-06-24 — they are here
# for the *ratios*, which is what a routing decision actually turns on. Check
# the current numbers before quoting them as money.
DEFAULT_MODELS = {
    "cheap": "claude-haiku-4-5",
    "mid": "claude-sonnet-5",
    "high": "claude-opus-5",
}

MODEL_PRICES = {
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0},
    "claude-sonnet-5": {"in": 3.0, "out": 15.0},
    "claude-opus-5": {"in": 5.0, "out": 25.0},
    "claude-fable-5": {"in": 10.0, "out": 50.0},
}
PRICES_AS_OF = "2026-06-24"

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
    # Tier label → model id. Override at init when a run should use different
    # models; the ladder and every reference file keep speaking in labels.
    "models": dict(DEFAULT_MODELS),
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


def resolve_model(cfg, label):
    """Turn a tier label ('cheap') into a model id, or pass an id straight through."""
    if not label:
        return None
    return (cfg.get("models") or DEFAULT_MODELS).get(label, label)


def model_cost_ratio(cfg, label):
    """How many times a model's output costs relative to the cheapest tier's.

    This is the number a routing decision turns on: not "Opus costs $25" but
    "this call costs 5× what the same call costs on the cheap tier". Returns
    None for a model with no published price on file.
    """
    mid = resolve_model(cfg, label)
    price = MODEL_PRICES.get(mid)
    base = MODEL_PRICES.get(resolve_model(cfg, "cheap"))
    if not price or not base or not base["out"]:
        return None
    ratio = price["out"] / base["out"]
    return int(ratio) if ratio == int(ratio) else round(ratio, 1)


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
    models = cfg.setdefault("models", {})
    for k, v in DEFAULT_MODELS.items():
        models.setdefault(k, v)
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


def _parse_ts(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        return None


def fmt_duration(s):
    if s is None:
        return "—"
    s = int(s)
    if s < 90:
        return f"{s}s"
    if s < 5400:
        return f"{s / 60:.0f} min"
    return f"{s / 3600:.1f} h"


def _pace(rounds, spend, waves_remaining):
    """Wall-clock read from the timestamps the ledgers already carry.

    A wave's span is first-record-to-last-record within that wave, so it counts
    real elapsed time including the lead agent's own orchestration between
    calls — which is honest, because that time is part of the run. What it
    cannot see is the duration of the first call in a wave, so treat the
    figures as steering, not billing.
    """
    recs = []
    for r in list(rounds) + list(spend):
        t = _parse_ts(r.get("ts"))
        if t is not None and r.get("wave") is not None:
            recs.append((r["wave"], t, r))
    if len(recs) < 2:
        return None
    by_wave = {}
    for w, t, _ in recs:
        by_wave.setdefault(w, []).append(t)
    spans = {w: (max(ts) - min(ts)).total_seconds() for w, ts in by_wave.items()}
    timed = {w: s for w, s in spans.items() if s > 0}
    all_ts = [t for _, t, _ in recs]
    elapsed = (max(all_ts) - min(all_ts)).total_seconds()
    active = sum(timed.values())
    avg = active / len(timed) if timed else None

    # Optional --seconds per record splits the wave into stages, which is what
    # tells you what to pipeline: a judge-dominated wave and a build-dominated
    # wave call for different fixes.
    stage = {"build": 0, "judge": 0, "smooth": 0, "other": 0}
    any_sec = False
    for r in rounds:
        if r.get("seconds"):
            any_sec = True
            stage["judge"] += r["seconds"]
    for s_ in spend:
        if s_.get("seconds"):
            any_sec = True
            role = s_.get("role") or "other"
            stage["build" if role == "builder" else "smooth" if role == "smoother" else "other"] \
                += s_["seconds"]

    return {
        "waves_timed": len(timed),
        "avg_wave_seconds": int(avg) if avg else None,
        "last_wave_seconds": int(spans.get(max(by_wave), 0)) or None,
        "active_seconds": int(active),
        "elapsed_seconds": int(elapsed),
        # Below five minutes of active time the rate is noise, not signal.
        "waves_per_hour": round(len(timed) / (active / 3600), 1) if active >= 300 else None,
        "projected_seconds_remaining": (
            int(waves_remaining * avg)
            if avg and waves_remaining and waves_remaining > 0 else None
        ),
        "stage_seconds": stage if any_sec else None,
    }


def _judging_advice(cfg, rounds):
    """Serial, speculative, or collapsed judging — decided by the log.

    From tier 2 a round runs two critic calls: promotion, then bar if promoted.
    Serializing them is only load-bearing when reverts actually happen; when
    promotions almost always succeed, the conditional buys nothing and costs
    every round a full critic latency. The revert rate is the arbiter.
    """
    if cfg["effort"]["tier"] < 2:
        return None  # tiers 0-1 already collapse into one screening call
    rate = _recent_revert_rate(rounds, window=12)
    if rate is None:
        return None
    pct = int(rate * 100)
    if rate <= 0.15:
        return (f"revert rate {pct}% — run the promotion and bar critics concurrently: "
                "the rare wasted bar verdict costs one call, serializing costs every "
                "round a critic's full latency")
    if rate >= 0.35:
        return (f"revert rate {pct}% — keep the two comparisons serial: speculative bar "
                "verdicts would be thrown away, and the rate itself is a ceiling signal")
    return None


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
    if args.models:
        for pair in args.models.split(","):
            if "=" not in pair:
                die(f"--models takes label=model pairs, got {pair!r} (e.g. cheap=claude-haiku-4-5)")
            label, mid = (s.strip() for s in pair.split("=", 1))
            if label not in DEFAULT_MODELS:
                die(f"unknown tier label {label!r} — expected one of {', '.join(DEFAULT_MODELS)}")
            cfg["models"][label] = mid
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
    # The bar's provenance is scaffolded, not left to memory: an empty SOURCES
    # file is a visible "nobody went looking", which is the difference between
    # a bar that was chosen and one that was settled for (`bar-selection.md`).
    dims_for_sources = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    bar_sources = (
        "# Bar sources — where the bar came from, and what was searched\n\n"
        "Fill this before wave 1. \"No reference exists\" is a claim; it needs a\n"
        "search behind it, and the search goes here so a reader can check it.\n\n"
        + "".join(
            f"## {d}\n\n"
            "- **Bar artifact(s):** `bar/…` — what a critic actually compares against\n"
            "- **Where it came from:** supplied by the user / found (name the source)\n"
            "- **Searched:** what you looked for and where, including searches that\n"
            "  came back empty\n"
            "- **Cases covered:** the situations this bar can judge\n"
            "- **Cases NOT covered:** situations the run may hit that this bar cannot\n"
            "  judge — fill these before they surface mid-run as \"no reference\"\n\n"
            for d in dims_for_sources)
    )
    for name, header in (
        ("contract.md", "# Gauntlet contract\n\n(goal / bar / inspection / stops / budget / autonomy / workbench)\n"),
        ("ownership.md", "# File ownership — refreshed every wave\n\n| lane | owned paths |\n|---|---|\n"),
        ("bar/SOURCES.md", bar_sources),
    ):
        p = root / name
        if not p.exists():
            p.write_text(header)
    (root / "rounds.jsonl").touch()
    (root / "spend.jsonl").touch()
    spec = tier_spec(cfg)
    print(f"initialised {root}/ — freeze bar artifacts into {root}/bar/ before wave 1")
    print(f"effort tier 0 ({spec['name']}): {spec['lanes'] or 'all'} lane(s), "
          f"{spec['critic_calls']} critic call(s) per lane per round")
    print("  models: " + ", ".join(
        f"{label}={resolve_model(cfg, label)}"
        + (f" ({r}×)" if (r := model_cost_ratio(cfg, label)) else "")
        for label in ("cheap", "mid", "high")))
    print(f"  builder={resolve_model(cfg, spec['builder_model'])} "
          f"critic={resolve_model(cfg, spec['critic_model'])}")
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
        # Which model produced this verdict, and — when this round re-judged an
        # earlier verdict on a stronger model — which model's verdict it replaced.
        # The pair is what makes "was the cheap critic good enough?" answerable
        # from the log instead of from opinion.
        "model": resolve_model(cfg, args.model) if args.model else None,
        "escalated_from": resolve_model(cfg, args.escalated_from) if args.escalated_from else None,
        "seconds": args.seconds,
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
    # An oracle round is a measurement; there is no model call to price.
    if args.tokens is None and args.mode != "oracle":
        print("  note: no --tokens on this record — the run cannot price itself without them",
              file=sys.stderr)
    # An unaimed round cannot miss, and a round that cannot miss cannot teach.
    if args.mode in BAR_MODES and cfg["effort"]["tier"] >= 1:
        aims = _load_jsonl(root / "aims.jsonl")
        if not any((a["lane"], a["dimension"], a["round"]) ==
                   (args.lane, args.dimension, args.round) for a in aims):
            print("  note: no aim on record for this round — state the hypothesis and expected "
                  "outcome before the build next time (`gauntlet.py aim`)", file=sys.stderr)


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
        "model": resolve_model(cfg, args.model) if args.model else None,
        "seconds": args.seconds,
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
        bar_recs = [r for r in recs if r["mode"] in BAR_MODES]
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
            if r["lane"] == lane and r["dimension"] == dim and r["mode"] in BAR_MODES
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
    bar_at_tier = [r for r in at_tier if r["mode"] in BAR_MODES]
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
    print("  the calls it frees belong to the dimensions still moving — reinvest them;"
          " and `unshelve` brings this one back the moment there is new information")


def cmd_unshelve(args):
    """Re-open a shelved dimension — reinvestment, not a retry.

    Shelving freed budget; this is where it can flow back. The gate is that the
    reason must be NEW information — a diagnosis round's cause, a new source
    asset, a re-cut — because re-running a parked dimension on nothing but
    leftover money is the failed-approaches ledger's purest violation: the same
    ideas, retried on hope.
    """
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    reason = (args.reason or "").strip()
    if len(reason) < 12:
        die("--reason is required — state the NEW information (a diagnosis finding, a new "
            "asset, a re-cut) that says this dimension can move now when it could not before. "
            "Budget left over is not new information.")
    entry = next((s for s in cfg.get("shelved", [])
                  if s["lane"] == args.lane and s["dimension"] == args.dimension), None)
    if entry is None:
        die(f"{args.lane}/{args.dimension} is not shelved")
    cfg["shelved"] = [s for s in cfg["shelved"] if s is not entry]
    entry["unshelved_ts"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds")
    entry["unshelved_reason"] = reason
    cfg.setdefault("shelf_history", []).append(entry)
    save_config(root, cfg)
    print(f"unshelved {args.lane}/{args.dimension} — schedulable again from the next wave")
    if entry.get("open_gap"):
        print(f"  the gap it parked with: {entry['open_gap']}")
    aim = _aim_status(rounds, _load_jsonl(root / "aims.jsonl"))
    failed = [f for f in (aim or {}).get("failed", [])
              if (f["lane"], f["dimension"]) == (args.lane, args.dimension)]
    for f_ in failed:
        print(f"  tried and missed before the shelf: \"{f_['approach']}\" ({f_['reason']})")
    print("  the first aim back must carry the new reason in its hypothesis"
          + (" — and must not be one of the approaches above" if failed else ""))
    print("Record the unshelve in contract.md; the next `plan` will schedule it.")


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
        shelved_open = [s for s in cfg.get("shelved", []) if s.get("open_gap")]
        if shelved_open:
            print(f"  {len(shelved_open)} shelved dimension(s) still hold open gaps — remaining"
                  " budget can be reinvested there: run a diagnosis round, and a new cause is"
                  " grounds to `unshelve`.")
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


def _escalation_evidence(rounds):
    """Did paying for a stronger critic actually change the verdict?

    Every round logged with --escalated-from re-judged an earlier verdict on a
    more expensive model. Comparing the two tells you whether the cheap tier was
    good enough — the one question about model choice that a run can answer from
    its own log rather than from belief. A high agreement rate is an argument for
    escalating less; a low one is an argument for escalating earlier.
    """
    esc = [r for r in rounds if r.get("escalated_from")]
    if not esc:
        return None
    agreed = 0
    for r in esc:
        prior = [
            p for p in rounds
            if p["lane"] == r["lane"] and p["dimension"] == r["dimension"]
            and p["round"] == r["round"] and p["mode"] == r["mode"]
            and p.get("model") == r["escalated_from"]
        ]
        if prior and prior[-1]["winner"] == r["winner"] \
                and prior[-1].get("severity") == r.get("severity"):
            agreed += 1
    return {
        "escalations": len(esc),
        "agreed": agreed,
        "overturned": len(esc) - agreed,
        "agreement_rate": round(agreed / len(esc), 2),
        "tokens": sum(r.get("tokens") or 0 for r in esc),
    }


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
          f"~{calls_per_lane_round(cfg)} calls per lane per round")
    print(f"  builder {resolve_model(cfg, spec['builder_model'])}"
          + (f" ({r}×)" if (r := model_cost_ratio(cfg, spec['builder_model'])) else "")
          + f" · critic {resolve_model(cfg, spec['critic_model'])}"
          + (f" ({r}×)" if (r := model_cost_ratio(cfg, spec['critic_model'])) else ""))
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

    waves_remaining = max(0, budget - max_wave)
    if tok_budget and spent and max_wave:
        per_wave_tok = spent / max_wave
        if per_wave_tok:
            waves_remaining = min(waves_remaining, max(0.0, (tok_budget - spent) / per_wave_tok))
    pace = _pace(rounds, load_spend(root), waves_remaining)
    if pace and pace["avg_wave_seconds"]:
        line = (f"pace: avg wave {fmt_duration(pace['avg_wave_seconds'])}"
                + (f", {pace['waves_per_hour']} waves/hour" if pace.get("waves_per_hour") else "")
                + f" · elapsed {fmt_duration(pace['elapsed_seconds'])}"
                  f" (active {fmt_duration(pace['active_seconds'])})")
        print(line)
        if pace.get("projected_seconds_remaining"):
            print(f"  ~{waves_remaining:.0f} more wave(s) ≈ "
                  f"{fmt_duration(pace['projected_seconds_remaining'])} at this pace")
        st = pace.get("stage_seconds")
        if st:
            print("  stages: " + " · ".join(
                f"{k} {fmt_duration(v)}" for k, v in st.items() if v))
    advice = _judging_advice(cfg, rounds)
    if advice:
        print(f"  judging: {advice}")
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

    skips = _load_jsonl(root / "skips.jsonl")
    if skips:
        saved = sum(s.get("tokens_saved_est") or 0 for s in skips)
        print(f"Rounds not run: {len(skips)} — ~{sum(s.get('calls_saved') or 0 for s in skips)} calls"
              + (f" ≈ {fmt_cost(cfg, saved)}" if saved else "") + " not spent.")
        for code in SKIP_REASONS:
            n = sum(1 for s in skips if s.get("reason_code") == code)
            if n:
                print(f"  {n}× {code}")
        print()

    oracle_n = sum(1 for r in rounds if r["mode"] == "oracle")
    if oracle_n:
        print(f"Oracle rounds: {oracle_n} of {sum(1 for r in rounds if r['mode'] in BAR_MODES)} "
              "bar rounds were measured, not judged — no critic tokens, and stronger evidence.\n")

    aim = _aim_status(rounds, _load_jsonl(root / "aims.jsonl"))
    if aim and aim["scored"]:
        print(f"Aim: {aim['hits']} of {aim['scored']} scored rounds hit their stated expectation "
              f"({int(aim['hit_rate'] * 100)}%)"
              + (f"; {aim['pending']} pending" if aim["pending"] else "") + ".")
        for (lane, dim), d in sorted(aim["per_dim"].items()):
            if d["scored"] >= 3 and d["hits"] / d["scored"] < 0.5:
                print(f"  [{lane} / {dim}] {d['hits']}/{d['scored']} hit — this dimension is not "
                      "understood: diagnose before building again")
                for f_ in [x for x in aim["failed"]
                           if (x["lane"], x["dimension"]) == (lane, dim)][:3]:
                    print(f"    tried and missed: \"{f_['approach']}\" ({f_['reason']})")
        if aim["unbriefed_bar_rounds"]:
            print(f"  {aim['unbriefed_bar_rounds']} bar round(s) ran without an aim — an unstated "
                  "expectation cannot miss, or teach.")
        print()

    esc = _escalation_evidence(rounds)
    if esc:
        print(f"Critic escalations: {esc['escalations']} — the stronger model agreed "
              f"{esc['agreed']}× and overturned {esc['overturned']}× "
              f"({int(esc['agreement_rate'] * 100)}% agreement, {fmt_cost(cfg, esc['tokens'])} spent).")
        if esc["escalations"] >= 4 and esc["agreement_rate"] >= 0.9:
            print("  The cheap critic is agreeing with the expensive one. Escalate less,"
                  " or raise the bar so the comparison is harder.")
        elif esc["escalations"] >= 4 and esc["agreement_rate"] <= 0.5:
            print("  The cheap critic is being overturned half the time. Its verdicts are"
                  " not load-bearing — raise the critic tier for this dimension.")
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
    pace = _pace(rounds, _load_jsonl(root / "spend.jsonl"), 0)
    if pace and pace.get("avg_wave_seconds"):
        line = (f"Pace: avg wave {fmt_duration(pace['avg_wave_seconds'])}, "
                f"elapsed {fmt_duration(pace['elapsed_seconds'])} "
                f"(active {fmt_duration(pace['active_seconds'])})")
        st = pace.get("stage_seconds")
        if st and (st.get("build") or st.get("judge")):
            line += f" — build {fmt_duration(st['build'])}, judge {fmt_duration(st['judge'])}"
        lines += [line]
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

    esc = _escalation_evidence(rounds)
    if esc:
        lines += [
            "## Was the expensive critic worth it?", "",
            f"{esc['escalations']} verdict(s) were escalated to a stronger critic. It agreed "
            f"{esc['agreed']}× and overturned {esc['overturned']}× "
            f"({int(esc['agreement_rate'] * 100)}% agreement), at {fmt_cost(cfg, esc['tokens'])}.", "",
            "(lead agent: say what this means for the next run's critic tier — a high agreement "
            "rate is evidence the cheap critic was sufficient, and the cheapest finding this "
            "report can carry.)", "",
        ]

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
    oracle = sum(1 for r in rounds if r["mode"] == "oracle")
    lines += [f"Verdict evidence: {blind} blind, {rubric} rubric, {oracle} oracle rounds "
              "(not equivalent evidence — an oracle round was measured, not judged)", ""]

    aim = _aim_status(rounds, _load_jsonl(root / "aims.jsonl"))
    if aim and aim["scored"]:
        lines += [
            "## Did the rounds know what they were aiming at?", "",
            f"{aim['scored']} round(s) ran with a stated aim; {aim['hits']} hit their "
            f"expectation ({int(aim['hit_rate'] * 100)}%).",
        ]
        for (lane, dim), d in sorted(aim["per_dim"].items()):
            lines.append(f"- **{lane} / {dim}** — {d['hits']}/{d['scored']} hit")
        if aim["failed"]:
            lines += ["", "Approaches that missed (do not retry these without a new reason):"]
            for f_ in aim["failed"][:8]:
                lines.append(f"- [{f_['lane']} / {f_['dimension']}] \"{f_['approach']}\" — {f_['reason']}")
        if aim["unbriefed_bar_rounds"]:
            lines += ["", f"{aim['unbriefed_bar_rounds']} bar round(s) ran without an aim."]
        lines += [
            "",
            "(lead agent: a dimension with a low hit rate was not understood — say whether "
            "a diagnosis or a re-cut fixed that, and carry the missed approaches into the "
            "next run's aims.)", "",
        ]

    skips = _load_jsonl(root / "skips.jsonl")
    if skips:
        saved = sum(s.get("tokens_saved_est") or 0 for s in skips)
        lines += [
            "## Rounds not run", "",
            f"{len(skips)} round(s) were deliberately skipped, saving roughly "
            f"{sum(s.get('calls_saved') or 0 for s in skips)} subagent calls"
            + (f" (~{fmt_cost(cfg, saved)})" if saved else "") + ":", "",
        ]
        for code in SKIP_REASONS:
            n = sum(1 for s in skips if s.get("reason_code") == code)
            if n:
                lines.append(f"- {n}× {code} — {SKIP_REASONS[code] or 'see the log'}")
        lines += ["", "(lead agent: this is the management the run did. Say whether any of these "
                  "skips turned out to be wrong.)", ""]
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


# What an evidence string can be. Anything with a known media suffix is
# something the board can *show*; everything else it can only print.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg")
FILE_SUFFIXES = IMAGE_SUFFIXES + (
    ".html", ".htm", ".json", ".txt", ".md", ".csv", ".pdf", ".log", ".mp4", ".webm")


def _evidence_ref(raw, root):
    """Classify one evidence string and make it reachable from the board.

    Evidence is either a path to something inspectable (a screenshot, a render,
    a benchmark dump) or an inline measurement (`lighthouse: LCP 1.42s`). The
    board can display the first and can only print the second, so the
    difference gets decided here — deterministically, once — rather than by a
    regex in the page.

    Paths are rewritten **relative to the board's own directory**, because
    evidence is logged relative to the project root (`gauntlet/shots/w3.png`)
    while `workbench.html` is served from `gauntlet/` itself. Skipping that
    rewrite puts a broken-image icon on every card, which reads exactly like a
    dead screenshot harness — the false alarm most likely to send someone
    debugging the wrong system.
    """
    text = str(raw or "").strip()
    if not text:
        return None
    ref = {"raw": text, "kind": "text", "src": None, "exists": None}
    # Measurements contain spaces; logged paths in this system do not. Treating
    # a spaced string as text is the safe direction to be wrong in.
    if any(ch.isspace() for ch in text):
        return ref
    suffix = PurePosixPath(text).suffix.lower()
    if suffix not in FILE_SUFFIXES and "/" not in text:
        return ref
    ref["kind"] = "image" if suffix in IMAGE_SUFFIXES else "file"

    root = Path(root)
    as_path = Path(text)
    # The two places a logged path can legitimately mean: relative to the state
    # directory, or relative to the project root above it.
    bases = [as_path] if as_path.is_absolute() else [root / text, root.parent / text]
    for cand in bases:
        try:
            if cand.exists():
                ref["src"] = os.path.relpath(cand.resolve(), root.resolve())
                ref["exists"] = True
                return ref
        except OSError:
            pass
    # Not on disk. Still carried, still flagged: a cited file that is not there
    # is a finding (`11` inspection rot), not something to drop silently.
    ref["exists"] = False
    prefix = root.name + "/"
    ref["src"] = text[len(prefix):] if text.startswith(prefix) else text
    return ref


def _evidence_trail(recs, root, limit=14):
    """One dimension's evidence, oldest → newest — the artifact over time.

    This is the thing the doctrine has always asked the workbench for and the
    board could not previously give: not the latest path as text, but the
    sequence, so a glance shows whether the artifact is actually moving.
    """
    trail = []
    for r in recs[-limit:]:
        ref = _evidence_ref(r.get("evidence"), root)
        if not ref:
            continue
        ref.update({"wave": r.get("wave"), "round": r.get("round"),
                    "score": r.get("score"), "severity": r.get("severity"),
                    "mode": r.get("mode")})
        trail.append(ref)
    return trail


def _evidence_files(rounds, root):
    """Run-wide evidence accounting, including what has gone missing."""
    refs = [x for x in (_evidence_ref(r.get("evidence"), root) for r in rounds) if x]
    files = [x for x in refs if x["kind"] != "text"]
    missing = sorted({x["raw"] for x in files if x["exists"] is False})
    return {
        "records": len(refs),
        "files": len(files),
        "images": sum(1 for x in files if x["kind"] == "image"),
        "measurements": sum(1 for x in refs if x["kind"] == "text"),
        "missing": len(missing),
        "missing_paths": missing[:6],
    }


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

    # Where the money went by model — the view that shows whether the expensive
    # tier is earning its multiplier or just absorbing the run.
    by_model, calls_by_model = {}, {}
    for rec in list(rounds) + list(spend_recs):
        mid = rec.get("model")
        if not mid:
            continue
        by_model[mid] = by_model.get(mid, 0) + (rec.get("tokens") or 0)
        calls_by_model[mid] = calls_by_model.get(mid, 0) + 1

    bar_rounds = [r for r in rounds if r["mode"] in BAR_MODES]
    skips = _load_jsonl(root / "skips.jsonl")

    waves_remaining = max(0, cfg["stops"]["budget_waves"] - max_wave)
    if tok_budget and spent and max_wave:
        per_wave_tok = spent / max_wave
        waves_remaining = min(waves_remaining, max(0.0, (tok_budget - spent) / per_wave_tok))
    pace = _pace(rounds, spend_recs, waves_remaining)
    if pace:
        pace["judging"] = _judging_advice(cfg, rounds)
    aim_full = _aim_status(rounds, _load_jsonl(root / "aims.jsonl"))
    aim_spec = None
    if aim_full:
        aim_spec = {k: aim_full[k] for k in
                    ("scored", "hits", "misses", "pending", "hit_rate", "unbriefed_bar_rounds")}
        aim_spec["failed"] = aim_full["failed"][:8]
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
        # Which model each tier label points at, what it costs relative to the
        # cheapest, and how much of the run it actually consumed.
        "models": {
            "as_of": PRICES_AS_OF,
            "roster": [
                {"label": label, "id": resolve_model(cfg, label),
                 "ratio": model_cost_ratio(cfg, label),
                 "price": MODEL_PRICES.get(resolve_model(cfg, label)),
                 "tokens": by_model.get(resolve_model(cfg, label), 0),
                 "calls": calls_by_model.get(resolve_model(cfg, label), 0)}
                for label in ("cheap", "mid", "high")
            ],
            "escalation": _escalation_evidence(rounds),
            "attributed_calls": sum(calls_by_model.values()),
        },
        "tier": {
            "index": cfg["effort"]["tier"],
            "name": spec["name"],
            "builder_model": spec["builder_model"],
            "critic_model": spec["critic_model"],
            "builder_model_id": resolve_model(cfg, spec["builder_model"]),
            "critic_model_id": resolve_model(cfg, spec["critic_model"]),
            "calls_per_lane_round": calls_per_lane_round(cfg),
            "allowance_tokens": tier_allowance(cfg),
            "ladder": [
                {"index": i, "name": t["name"], "share": t["share"],
                 "lanes": t["lanes"], "dims": t["dims"],
                 "critic_calls": t["critic_calls"],
                 "builder_model": resolve_model(cfg, t["builder_model"]),
                 "critic_model": resolve_model(cfg, t["critic_model"]),
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
            "by_model": by_model,
            # Oracle rounds cost nothing by construction, so they are not
            # "unpriced" — counting them as missing data would nag about a
            # number that correctly does not exist.
            "priced_rounds": sum(1 for r in rounds if r.get("tokens")),
            "total_rounds": sum(1 for r in rounds if r["mode"] != "oracle"),
        },
        "pace": pace,
        "aim": aim_spec,
        "evidence_mix": {
            "blind": sum(1 for r in bar_rounds if r["mode"] == "blind"),
            "rubric": sum(1 for r in bar_rounds if r["mode"] == "rubric"),
            "oracle": sum(1 for r in bar_rounds if r["mode"] == "oracle"),
        },
        # What was actually inspected, and whether it is still on disk.
        "evidence_files": _evidence_files(rounds, root),
        # Rounds deliberately not run. The cheapest round is the one you decide
        # to skip, and without this the saving is invisible.
        "skipped": {
            "rounds": len(skips),
            "calls_saved": sum(s.get("calls_saved") or 0 for s in skips),
            "tokens_saved_est": sum(s.get("tokens_saved_est") or 0 for s in skips),
            "by_reason": {
                code: sum(1 for s in skips if s.get("reason_code") == code)
                for code in SKIP_REASONS
                if any(s.get("reason_code") == code for s in skips)
            },
        },
        "extensions": cfg.get("extensions") or [],
        "shelved": cfg.get("shelved") or [],
        "columns": {"open": [], "flat": [], "shelved": [], "retired": []},
        "rounds": [],
    }

    for (lane, dim), s in sorted(per.items()):
        recs = [r for r in rounds if r["lane"] == lane and r["dimension"] == dim]
        bar_recs = [r for r in recs if r["mode"] in BAR_MODES]
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
            "evidence_trail": _evidence_trail(bar_recs, root),
            "rubric_share": s["rubric_share"],
            "tokens": sum(r.get("tokens") or 0 for r in recs),
            "trend": _dimension_trend(bar_recs, flat_n=cfg["stops"].get("flat_rounds_n", 3))["note"]
            if bar_recs else None,
            "aim": (aim_full or {}).get("per_dim", {}).get((lane, dim)),
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
            "model": r.get("model"), "escalated_from": r.get("escalated_from"),
        })
    return state


def cmd_aim(args):
    """State a round's hypothesis and expected outcome before it runs.

    An aim turns a round from an attempt into an experiment: why the gap
    exists, what intervention should close it, and what the verdict must show
    if the hypothesis is right. A round without an aim cannot miss — and a
    round that cannot miss cannot teach the run anything.

    The expectation must improve on the last verdict. An aim the artifact has
    already met is not a bet, and allowing it would let a run buy a flattering
    hit rate by aiming at the floor.
    """
    root = Path(args.root)
    cfg = load_config(root)
    dims = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    if args.dimension not in dims:
        die(f"dimension {args.dimension!r} is not declared in config.json ({', '.join(dims)})")
    hypothesis = (args.hypothesis or "").strip()
    if len(hypothesis) < 20:
        die("--hypothesis must say why the gap exists and why this change should close it — "
            "a hypothesis you cannot state is a guess you are about to pay for")
    approach = (args.approach or "").strip()
    if len(approach) < 5:
        die("--approach must name the intervention — it is the key that stops a failed "
            "approach from being retried in silence")
    if args.expect_severity is None and args.expect_score is None:
        die("state at least one expectation (--expect-severity minor|none and/or --expect-score N) — "
            "without one the verdict cannot confirm or refute anything")
    if args.expect_severity is not None and args.expect_severity not in ("minor", "none"):
        # The honest cold-start case lands here: a first build genuinely may be
        # expected to come back `major`. That is not an aim, it is a forecast —
        # and tier 0 does not take an artifact aim at all (`aim.md`), because
        # the probe's hypothesis is about the apparatus, not the artifact.
        die("--expect-severity must be minor or none — aiming at major is not an improvement.\n"
            "  If this is a cold-start or probe round and `major` is the honest expectation, it "
            "does not need an aim: tier 0 aims at the loop (does inspection work, does the bar "
            "discriminate), and aim accounting starts at tier 1.")
    if args.expect_score is not None and not (0 <= args.expect_score <= 10):
        die("--expect-score must be 0-10")

    rounds = load_rounds(root)
    prior = [r for r in rounds
             if r["lane"] == args.lane and r["dimension"] == args.dimension
             and r["mode"] in BAR_MODES]
    last = prior[-1] if prior else None
    if last:
        if args.expect_severity is not None:
            last_rank = SEVERITY_RANK.get(last.get("severity") or "major", 3)
            if SEVERITY_RANK[args.expect_severity] >= last_rank:
                die(f"the last verdict is already severity {last.get('severity')} — the "
                    "expectation must improve on it; an aim you have already met is not a bet")
        if args.expect_score is not None and args.expect_score <= (last.get("score") or 0):
            die(f"the last verdict already scored {last.get('score')} — expect a higher score, "
                "or state a severity expectation instead")

    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "wave": args.wave,
        "lane": args.lane,
        "dimension": args.dimension,
        "round": args.round,
        "hypothesis": hypothesis,
        "approach": approach,
        "expect_severity": args.expect_severity,
        "expect_score": args.expect_score,
        "tier": cfg["effort"]["tier"],
    }
    with (root / "aims.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")
    expects = []
    if args.expect_severity:
        expects.append(f"severity → {args.expect_severity}")
    if args.expect_score is not None:
        expects.append(f"score ≥ {args.expect_score}")
    print(f"aimed: {args.lane}/{args.dimension} round {args.round} — {', '.join(expects)}")
    print(f"  approach: {approach}")


def _aim_status(rounds, aims):
    """Score every aim against what actually happened.

    Outcomes: hit (the verdict met every stated expectation), miss (the round
    reverted, or the verdict fell short), pending (no verdict yet). The hit
    rate is the run's measure of whether it understands the artifact — a
    dimension where aims keep missing is not a dimension that needs more
    rounds, it is one that needs a diagnosis.
    """
    if not aims:
        return None
    results = []
    for a in aims:
        key = (a["lane"], a["dimension"], a["round"])
        champ = [r for r in rounds
                 if (r["lane"], r["dimension"], r["round"]) == key and r["mode"] == "champion"]
        bars = [r for r in rounds
                if (r["lane"], r["dimension"], r["round"]) == key and r["mode"] in BAR_MODES]
        if champ and champ[-1].get("action") == "reverted":
            outcome, reason = "miss", "reverted"
        elif not bars:
            outcome, reason = "pending", None
        else:
            b = bars[-1]
            ok = True
            if a.get("expect_severity"):
                ok = ok and (SEVERITY_RANK.get(b.get("severity") or "major", 3)
                             <= SEVERITY_RANK[a["expect_severity"]])
            if a.get("expect_score") is not None:
                ok = ok and (b.get("score") or 0) >= a["expect_score"]
            outcome, reason = ("hit", None) if ok else ("miss", "fell short")
        results.append({"lane": a["lane"], "dimension": a["dimension"], "round": a["round"],
                        "approach": a.get("approach"), "outcome": outcome, "reason": reason})

    scored = [r for r in results if r["outcome"] != "pending"]
    hits = sum(1 for r in scored if r["outcome"] == "hit")
    per_dim = {}
    for r in scored:
        d = per_dim.setdefault((r["lane"], r["dimension"]), {"scored": 0, "hits": 0})
        d["scored"] += 1
        d["hits"] += 1 if r["outcome"] == "hit" else 0
    failed = [{"lane": r["lane"], "dimension": r["dimension"],
               "approach": r["approach"], "reason": r["reason"]}
              for r in scored if r["outcome"] == "miss" and r.get("approach")]
    aimed_keys = {(a["lane"], a["dimension"], a["round"]) for a in aims}
    unbriefed = sum(
        1 for r in rounds
        if r["mode"] in BAR_MODES and (r.get("tier") or 0) >= 1
        and (r["lane"], r["dimension"], r["round"]) not in aimed_keys
    )
    return {
        "scored": len(scored),
        "hits": hits,
        "misses": len(scored) - hits,
        "pending": len(results) - len(scored),
        "hit_rate": round(hits / len(scored), 2) if scored else None,
        "per_dim": per_dim,
        "failed": failed,
        "unbriefed_bar_rounds": unbriefed,
    }


SKIP_REASONS = {
    "no-change": "the builder produced no change to its owned paths — nothing to judge",
    "gap-too-small": "the open gap is smaller than another lane's, and the wave went there instead",
    "oracle-unchanged": "the numeric measurement did not move, so no model was asked",
    "structural": "the remaining distance is structural; a round would buy a revert",
    "other": "",
}


def cmd_skip(args):
    """Record a round that was deliberately not run, and what that saved.

    The cheapest round in a gauntlet is the one you decide not to run. Recording
    the decision keeps that from being invisible: without it, good management
    looks identical to a quiet run and the report cannot show what restraint was
    worth.
    """
    root = Path(args.root)
    cfg = load_config(root)
    dims = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    if args.dimension not in dims:
        die(f"dimension {args.dimension!r} is not declared in config.json ({', '.join(dims)})")
    if args.reason_code not in SKIP_REASONS:
        die(f"--reason-code must be one of {', '.join(SKIP_REASONS)}")
    note = (args.note or "").strip()
    if args.reason_code == "other" and len(note) < 12:
        die("--reason-code other needs a --note saying what the actual reason was")

    # Price it conservatively: the critic calls this dimension would have cost.
    # The builder is only saved when every dimension of the lane is held, and
    # claiming it here would flatter the number.
    priced = [r for r in load_rounds(root) if r.get("tokens")]
    per_critic = sum(r["tokens"] for r in priced) / len(priced) if len(priced) >= 3 else 0
    calls_saved = tier_spec(cfg)["critic_calls"]
    saved = int(calls_saved * per_critic)
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "wave": args.wave,
        "lane": args.lane,
        "dimension": args.dimension,
        "reason_code": args.reason_code,
        "note": note,
        "tier": cfg["effort"]["tier"],
        "calls_saved": calls_saved,
        "tokens_saved_est": saved,
    }
    with (root / "skips.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"skipped {args.lane}/{args.dimension} at wave {args.wave} — {args.reason_code}")
    print(f"  saved ~{calls_saved} critic call(s)"
          + (f" ≈ {fmt_cost(cfg, saved)} at this run's measured rate" if saved else "")
          + "; the builder is only saved too if every dimension of this lane is held")


def cmd_plan(args):
    """Propose the next wave: which lanes earn a round, which do not, and the cost.

    The loop's default is to run every active lane every wave. That is the
    expensive default and it is rarely the right one — a lane sitting on a
    `minor` gap does not deserve the same compute as one sitting on a `major`.
    This ranks what is open and prices both the proposed wave and the naive one.
    """
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    if not rounds:
        print("no rounds logged yet — run the tier-0 probe first")
        return
    per, retired = _lane_dim_status(rounds, cfg)
    max_wave = max(r["wave"] for r in rounds)
    flat_n = cfg["stops"].get("flat_rounds_n", 3)

    # A dimension unshelved after its last bar round is schedulable even though
    # the log still calls it flat — the unshelve reason IS the new information
    # the flat detector cannot see yet. One round back in, the log takes over.
    unshelved = {}
    for h in cfg.get("shelf_history", []):
        ts = h.get("unshelved_ts")
        if not ts:
            continue
        key = (h["lane"], h["dimension"])
        last_bar = max((r["ts"] for r in rounds
                        if r["lane"] == key[0] and r["dimension"] == key[1]
                        and r["mode"] in BAR_MODES), default="")
        # >= not >: timestamps have second resolution, and a same-second tie
        # goes to the unshelve — it is by definition the later decision.
        if ts >= last_bar:
            unshelved[key] = h.get("unshelved_reason", "")

    run, hold = [], []
    for key, s in sorted(per.items()):
        lane, dim = key
        if s["shelved"]:
            hold.append((key, "shelved",
                         "parked; `unshelve` re-opens it — on new information only"))
        elif s["retired"]:
            hold.append((key, "retired", "met the bar"))
        elif s["flat"] and key not in unshelved:
            hold.append((key, "flat", f"no movement in {flat_n} rounds — shelve or re-cut, do not re-run"))
        else:
            bar_recs = [r for r in rounds
                        if r["lane"] == lane and r["dimension"] == dim and r["mode"] in BAR_MODES]
            last = bar_recs[-1] if bar_recs else None
            sev = (last or {}).get("severity") or "major"
            gap = (last or {}).get("gap")
            run.append((key, sev, SEVERITY_RANK.get(sev, 3),
                        gap if gap and gap != "none" else None))

    # Lane/dimension pairs declared at init that never produced a round are
    # invisible in the log; a plan that silently omits them is not a plan. They
    # rank ABOVE known majors: an unjudged dimension is a risk, not a zero — a
    # named major is bounded, an unknown can still invalidate work everywhere.
    declared = cfg.get("lanes") or []
    dims = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    for lane in declared:
        for dim in dims:
            if (lane, dim) not in per:
                run.append(((lane, dim), "unknown", 4,
                            "never judged — price it with a survey verdict (critic only, no builder)"))

    run.sort(key=lambda x: -x[2])
    print(f"Plan for wave {max_wave + 1} — tier {cfg['effort']['tier']}, "
          f"~{calls_per_lane_round(cfg)} calls per lane per round\n")

    if not run:
        print("Nothing is open. Raise the bar (announced), re-cut, or stop — do not run a wave.")
        shelved_open = [s for s in cfg.get("shelved", []) if s.get("open_gap")]
        for s in shelved_open:
            print(f"  shelved with an open gap: [{s['lane']} / {s['dimension']}] — {s['open_gap']}")
        if shelved_open:
            print("  remaining budget can be reinvested there: a diagnosis round that names a new"
                  " cause is grounds to `unshelve`. Money left over on its own is not.")
        return

    aim = _aim_status(rounds, _load_jsonl(root / "aims.jsonl"))
    print("RUN (largest gap first):")
    for (lane, dim), sev, _, gap in run:
        note = "  clean — one more clean round retires it" if sev == "none" else ""
        d = (aim or {}).get("per_dim", {}).get((lane, dim))
        if d and d["scored"] >= 3 and d["hits"] / d["scored"] < 0.5:
            note = (f"  DIAGNOSE FIRST — {d['hits']}/{d['scored']} aims hit; another build "
                    "round is another guess")
        if (lane, dim) in unshelved:
            note = "  unshelved on new information — the first aim back must carry it"
        print(f"  [{lane} / {dim}]  severity {sev}{note}")
        if gap:
            print(f"      {gap}")
        for f_ in [x for x in (aim or {}).get("failed", [])
                   if (x["lane"], x["dimension"]) == (lane, dim)][:3]:
            print(f"      tried and missed: \"{f_['approach']}\" ({f_['reason']})")
    if hold:
        print("\nHOLD:")
        for (lane, dim), why, detail in hold:
            print(f"  [{lane} / {dim}]  {why} — {detail}")

    naive_lanes = sorted({lane for lane, _ in per})
    proposed_lanes = sorted({lane for (lane, _), *_ in run})
    cap = args.max_lanes
    if cap and len(proposed_lanes) > cap:
        kept = sorted({lane for (lane, _), *_ in run[:cap]})
        print(f"\n--max-lanes {cap}: run {', '.join(kept)} this wave and hold the rest for the next.")
        proposed_lanes = kept

    print(f"\nProposed wave: {len(proposed_lanes)} lane(s), "
          f"~{_projected_calls(cfg, 1, proposed_lanes)} calls")
    t_prop = _projected_tokens(root, cfg, 1, proposed_lanes, rounds)
    t_naive = _projected_tokens(root, cfg, 1, naive_lanes, rounds)
    if t_prop and t_naive:
        print(f"  ~{fmt_cost(cfg, t_prop)} — against ~{fmt_cost(cfg, t_naive)} "
              f"to run all {len(naive_lanes)} lane(s) regardless of evidence "
              f"(~{fmt_cost(cfg, t_naive - t_prop)} saved)")
    else:
        print("  (cannot price it — too few rounds carried --tokens)")

    print("\nBefore spending a critic call on any of these:")
    print("  - confirm the builder actually changed its owned paths; if not, "
          "`skip --reason-code no-change` and re-brief instead of judging nothing")
    print("  - for a dimension with a numeric bar, take the measurement and log "
          "`--mode oracle`; a model does not need to read a number")
    print("  - state every round's aim before its builder runs (`gauntlet.py aim`): the "
          "hypothesis, the approach, and what the verdict must show — never re-use an "
          "approach listed above as missed without a new reason to believe it")
    if any(sev == "unknown" for _, sev, _, _ in run):
        print("  - an unknown outranks a known major: buy its first verdict as a survey — "
              "one cheap bar comparison of the artifact as it stands, no builder — before "
              "spending build rounds anywhere it could invalidate")
    if any(sev == "minor" for _, sev, _, _ in run):
        print("  - a dimension on a minor gap converges faster in one batch round: fold the "
              "critic's second-order NOTES into the brief instead of spending a round per "
              "cosmetic gap — the champion guard catches regressions")
    if len(proposed_lanes) >= 2:
        print("  - lanes with disjoint ownership can pipeline: dispatch the next lane's builder "
              "while this lane's critics run — ownership serialises writes, not the clock")
    advice = _judging_advice(cfg, rounds)
    if advice:
        print(f"  - {advice}")


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
    p.add_argument("--models",
                   help="tier label to model id, comma separated "
                        "(default: cheap=claude-haiku-4-5,mid=claude-sonnet-5,high=claude-opus-5)")
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
    p.add_argument("--model",
                   help="model that produced this verdict — a tier label (cheap|mid|high) or a model id")
    p.add_argument("--escalated-from",
                   help="the model whose verdict this round re-judged, when a thin verdict was "
                        "escalated to a stronger critic; makes 'was the cheap critic enough?' measurable")
    p.add_argument("--seconds", type=int,
                   help="wall-clock seconds the calls behind this record took — lets `status` "
                        "split a wave into build/judge/smooth and say what to pipeline")
    p.set_defaults(fn=cmd_log_round)

    p = sub.add_parser("spend", help="record spend not attached to a round (builders, smoother, lead passes)")
    p.add_argument("--tokens", type=int, required=True)
    p.add_argument("--role", default="builder", help="builder|smoother|lead|other")
    p.add_argument("--wave", type=int)
    p.add_argument("--model", help="model that did the work — a tier label (cheap|mid|high) or a model id")
    p.add_argument("--seconds", type=int, help="wall-clock seconds the work took")
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

    p = sub.add_parser("unshelve", help="re-open a shelved dimension on new information")
    p.add_argument("--lane", required=True)
    p.add_argument("--dimension", required=True)
    p.add_argument("--reason", required=True,
                   help="the new information: a diagnosis finding, a new asset, a re-cut")
    p.set_defaults(fn=cmd_unshelve)

    p = sub.add_parser("aim", help="state a round's hypothesis and expected outcome before it runs")
    p.add_argument("--wave", type=int, required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--dimension", required=True)
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--hypothesis", required=True,
                   help="why the gap exists and why this change should close it")
    p.add_argument("--approach", required=True,
                   help="the intervention, named — the key that stops failed approaches being retried")
    p.add_argument("--expect-severity", help="severity the verdict should reach: minor|none")
    p.add_argument("--expect-score", type=int, help="score the verdict should reach")
    p.set_defaults(fn=cmd_aim)

    p = sub.add_parser("plan", help="propose the next wave from the log, and price it against running everything")
    p.add_argument("--max-lanes", type=int, help="cap how many lanes this wave runs; the rest wait")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("skip", help="record a round deliberately not run, and what it saved")
    p.add_argument("--wave", type=int, required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--dimension", required=True)
    p.add_argument("--reason-code", required=True,
                   help="no-change|gap-too-small|oracle-unchanged|structural|other")
    p.add_argument("--note", help="required when --reason-code is other")
    p.set_defaults(fn=cmd_skip)

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
