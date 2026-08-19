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
import hashlib
import os
import re
import subprocess
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
        # The budget the user agrees is in waves; the thing actually consumed is
        # tokens. Without this the two never meet and consent is uninformed.
        # null = not agreed, and status says so rather than pretending.
        "budget_tokens": None,
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
    # Per-dimension target overrides ({dim: 1-10}); stops.target_score is the
    # default for dimensions not named here. A blanket "10/10" request is
    # decomposed into these at intake — the same 10 that is merely expensive
    # on one dimension is unreachable by iteration on another.
    "dimension_targets": {},
    "lanes": [],
    "bar_kind": "reference",
    # Granted budget extensions, appended by `extend`. The run's history of
    # "the budget ran out and the user chose to keep going".
    "extensions": [],
    # Lane/dimension pairs deliberately stopped short of retirement, appended by
    # `park`. Their gaps stay open in the report; their budget goes back.
    "parked": [],
    # Mechanical checks a command can decide. Each names the paths it depends on;
    # a gate whose inputs are unchanged since it last passed is NOT re-run, and
    # its result is handed to the critic so no round pays to re-derive it.
    # [{"name": ..., "cmd": "<shell>", "paths": ["a", "b/"]}]
    "gates": [],
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


def target_for(cfg, dimension):
    """The target score this dimension retires against: its own entry in
    dimension_targets, or the run default in stops."""
    return (cfg.get("dimension_targets") or {}).get(dimension, cfg["stops"]["target_score"])


def usable_line(target):
    """The 'usable' rung for a dimension: 7 on the method's scale, or the
    dimension's own target when that is lower. The build order climbs every
    dimension here before any dimension buys a rung above it — Kniberg's
    skateboard at run level: whole and crude beats one part excellent."""
    return min(7, target)


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
    old = None
    if (root / "config.json").exists():
        # A re-cut re-inits with --force. A re-cut changes the lane set, not the
        # agreement: the budget, hard cap, target, stops, WIP limit and the run's
        # history (extensions, parks, gates) all carry across, and the flags
        # below override only what was explicitly re-stated. Resetting the
        # budget to the default here would be a silent budget grant — the
        # bug class `extend` exists to prevent.
        old = json.loads((root / "config.json").read_text())
        for k, v in old.items():
            if k == "stops":
                cfg["stops"].update(v or {})
            else:
                cfg[k] = json.loads(json.dumps(v))
    if args.lanes:
        cfg["lanes"] = [s.strip() for s in args.lanes.split(",") if s.strip()]
    if args.dimensions:
        cfg["dimensions"] = [s.strip() for s in args.dimensions.split(",") if s.strip()]
    for key, val in (
        ("bar_met_n", args.bar_met_n),
        ("clean_streak_n", args.clean_streak_n),
        ("no_progress_n", args.no_progress_n),
        ("budget_waves", args.budget_waves),
        ("budget_tokens", args.budget_tokens),
        ("target_score", args.target_score),
    ):
        if val is not None:
            cfg["stops"][key] = val
    if not (1 <= cfg["stops"]["target_score"] <= 10):
        die("target-score must be between 1 and 10")
    if cfg["stops"]["target_score"] == 10:
        print(
            "warning: target-score 10 means bar-met can never fire (a round advances the "
            "streak only at or above the target) — lanes could only retire on clean-streak "
            "evidence. Set the target where the bar actually is, and record any higher "
            "ambition as a stretch in contract.md",
            file=sys.stderr,
        )
    if args.dimension_targets:
        dt = {}
        for part in args.dimension_targets.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" not in part:
                die(f"--dimension-targets entries are dim=score, got {part!r}")
            d, _, v = part.partition("=")
            d = d.strip()
            try:
                v = int(v.strip())
            except ValueError:
                die(f"dimension target for {d!r} must be an integer 1-10, got {v.strip()!r}")
            if not (1 <= v <= 10):
                die(f"dimension target for {d!r} must be between 1 and 10")
            if d not in cfg["dimensions"]:
                die(f"dimension {d!r} in --dimension-targets is not declared "
                    f"({', '.join(cfg['dimensions'])})")
            if v == 10:
                print(
                    f"warning: target 10 on {d!r} means bar-met can never fire on that "
                    "dimension — it could only retire on clean-streak evidence. Put the 10 "
                    "in the stretch line and set the target where the bar actually is",
                    file=sys.stderr,
                )
            dt[d] = v
        cfg["dimension_targets"] = dt
    if old and args.budget_waves is not None and \
            args.budget_waves != (old.get("stops") or {}).get("budget_waves"):
        print(
            "warning: changing the wave budget through init --force bypasses every guard "
            "`extend` enforces (depleted-budget, park-first, at-ceiling, hard cap). Do this "
            "only on an explicit user grant, and record the grant in contract.md",
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
        # Noticed-but-not-funded work. One line each, never promoted into the
        # run without a re-cut — this is what stops a wave from growing.
        ("backlog.md", "# Backlog — noticed, deliberately not funded\n\n"
                       "One line per item. Nothing here is in scope for this run; the report\n"
                       "carries the list so the user can decide what a future run should cover.\n\n"),
    ):
        p = root / name
        if not p.exists():
            p.write_text(header)
    (root / "rounds.jsonl").touch()
    lanes = len(cfg["lanes"]) or 1
    per_wave = min(lanes, cfg["wip_limit"]) * CALLS_PER_LANE_ROUND + CALLS_PER_WAVE_OVERHEAD
    print(f"initialised {root}/ — freeze bar artifacts into {root}/bar/ before wave 1")
    if cfg.get("dimension_targets"):
        print("per-dimension targets: "
              + ", ".join(f"{d}={v}" for d, v in sorted(cfg["dimension_targets"].items()))
              + f" (default {cfg['stops']['target_score']} for the rest)")
    if old:
        print(
            "re-cut: budget, stops, WIP limit, gates, parks and extensions carried across. "
            "A lane that keeps its name keeps its streaks — rename any lane whose scope "
            "changed, so its counters start fresh."
        )
    total_calls = per_wave * cfg["stops"]["budget_waves"]
    print(
        f"projected cost: ~{per_wave} subagent calls per wave "
        f"(WIP limit {cfg['wip_limit']} lane(s)), ~{total_calls} "
        f"over the {cfg['stops']['budget_waves']}-wave budget"
    )
    tb = cfg["stops"].get("budget_tokens")
    if tb:
        print(f"token budget: {tb:,} — ~{tb // max(1, total_calls):,} per call at that projection")
    else:
        print(
            "no token budget agreed. A critic call that inspects a whole artifact runs tens of "
            "thousands of tokens, so this projection is in the wrong unit for what actually "
            "burns. Measure one round, then set --budget-tokens before agreeing to a long run."
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
    prior = load_rounds(root)
    if (args.lane, args.dimension) in parked_keys(cfg):
        print(
            f"warning: [{args.lane} / {args.dimension}] is parked — you are spending on a lane "
            "the run already decided to stop funding. Resume it explicitly "
            "(`park --resume`) or leave it parked.",
            file=sys.stderr,
        )
    elif prior:
        # Settled work is not re-judged. A retired dimension has already met its
        # bar; re-running it is the commonest way a long run spends money on
        # ground it already covered.
        per_prior, _r, _c = _lane_dim_status(prior, cfg)
        if per_prior.get((args.lane, args.dimension), {}).get("retired"):
            print(
                f"warning: [{args.lane} / {args.dimension}] has retired — settled work is not "
                "re-judged. Log this only as a regression check (say so in the gap text); "
                "otherwise you are paying to re-review a closed dimension.",
                file=sys.stderr,
            )
    # A retried command (timeout, double-pasted shell line) writes a second
    # record and advances a streak the artifact never earned. Warn, don't block:
    # a re-run with rotated framing legitimately shares these coordinates.
    if any(
        r["wave"] == args.wave and r["round"] == args.round and r["lane"] == args.lane
        and r["dimension"] == args.dimension and r["mode"] == args.mode
        for r in prior
    ):
        print(
            f"warning: a {args.mode} record for wave {args.wave} round {args.round} on "
            f"[{args.lane} / {args.dimension}] already exists — a retried command logs twice "
            "and advances streaks twice. Make sure this is a deliberate second comparison.",
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
    # A bar comparison needs something to compare against. Champion mode does
    # not (both sides are ours), so it stays available — but then nothing can
    # retire on bar-met, and the run should say so rather than drift into
    # grading its own taste.
    if args.mode in BAR_MODES:
        bar_dir = root / "bar"
        if not (bar_dir.exists() and any(f.is_file() for f in bar_dir.rglob("*"))):
            die(
                f"no comparison material in {bar_dir}/ — a bar verdict needs a bar that "
                "exists outside this run, or the round measures the builder's own taste.\n"
                "  python3 scripts/gauntlet.py bar-request   # writes what this run needs\n"
                "Freeze the comparator (or a research-backed answer key) into that directory "
                "first. Champion-mode rounds still work without it, but nothing retires on "
                "bar-met (bar-selection.md)."
            )
    # Evidence is free text (a measurement, a comparison note) — but when it
    # looks like a file path, it should open. A verdict citing a screenshot
    # nobody can open is progress theatre with a citation.
    ev = args.evidence.strip()
    if " " not in ev and ("/" in ev or Path(ev).suffix):
        bare = re.sub(r":[0-9][0-9,-]*$", "", ev)
        if not Path(bare).exists():
            print(
                f"warning: evidence {ev!r} looks like a path but does not exist from here — "
                "a verdict citing evidence nobody can open is progress theatre "
                "(failure-modes.md). Check the path, or make the evidence a measurement.",
                file=sys.stderr,
            )

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
    if args.critic_model:
        rec["critic_model"] = args.critic_model
    if args.tier == "screening":
        rec["tier"] = "screening"
        if args.severity == "none":
            print(
                "note: screening verdict with severity none — recorded, but it will not "
                "advance retirement streaks. A lane's lifecycle needs a deciding-tier verdict.",
                file=sys.stderr,
            )
    if args.blind:
        if args.mode != "champion":
            die("--blind marks a blinded promotion comparison; for bar comparisons use --mode blind")
        rec["blind"] = True
    if args.diff_lines is not None:
        if args.diff_lines < 0:
            die("--diff-lines cannot be negative")
        rec["diff_lines"] = args.diff_lines
    if args.tokens is not None:
        if args.tokens < 0:
            die("--tokens cannot be negative")
        rec["tokens"] = args.tokens
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
        if not args.champion_ref:
            print(
                "warning: no --champion-ref on a promotion record — without the pre-round "
                "champion (git ref or snapshot path) this promotion/revert cannot be verified "
                "or recovered later, and 'best champion' at stop time is guesswork.",
                file=sys.stderr,
            )
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
        target = target_for(cfg, args.dimension)
        if args.severity == "major" and args.score >= target:
            print(
                f"warning: score {args.score} is at or above the target of {target} but severity is "
                "'major' — the critic is scoring one bar and grading against another. Check which "
                "bar the verdict used.",
                file=sys.stderr,
            )
        if args.winner == "ours" and args.score < target:
            print(
                f"warning: winner is ours but score {args.score} is below the target of {target} — "
                "a win below the bar advances no bar-met streak. Check the calibration: the "
                "target score is where the bar sits, and beating the comparator should land "
                "at or above it.",
                file=sys.stderr,
            )
        if args.severity == "none" and args.score < target:
            print(
                f"warning: severity is 'none' but score {args.score} is below the target of "
                f"{target} — 'no meaningful gap left' below the bar is contradictory, and this "
                "verdict feeds a clean streak. Re-check it before trusting the round.",
                file=sys.stderr,
            )

    # Concurrent lanes mean concurrent log-round calls. Lock the append so two
    # verdicts landing at once cannot interleave into a corrupt line.
    with (root / "rounds.jsonl").open("a") as f:
        try:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass  # no flock (Windows, exotic filesystem) — appends stay best-effort
        f.write(json.dumps(rec) + "\n")
        f.flush()
    print(f"logged: wave {rec['wave']} lane {rec['lane']} [{rec['dimension']}] {rec['mode']} → {rec['winner']} ({rec['margin']})")


def _streaks(records, target):
    """Compute trailing streaks over bar-mode records, ordered as logged.

    Lifecycle streaks count deciding verdicts only. A screening-tier win can
    steer the next round but never advances a lane toward retirement — cheap
    verdicts buy iteration, not lifecycle. A screening loss still breaks the
    streak: bad news is bad news at any tier.

    A bar-met round must also sit at or above the target with no major gap.
    Winning the comparison while scoring below the bar, or while a major gap
    stays open, is not the bar being met — counting it was how a lane could
    retire at 3/10 with an open major gap and read as a success. The target
    is per dimension (target_for): a run can hold gameplay to 8 and graphics
    to 6 without one number lying about both.
    """
    bar_met = clean = 0
    for r in reversed(records):
        if r["winner"] == "ours" and r.get("severity") != "major" and r["score"] >= target:
            if r.get("tier") == "screening":
                continue
            bar_met += 1
        else:
            break
    for r in reversed(records):
        if r.get("severity") == "none":
            if r.get("tier") == "screening":
                continue
            clean += 1
        else:
            break
    return bar_met, clean


MARGIN_RANK = {"decisive": 3, "clear": 2, "thin": 1}
SEVERITY_RANK = {"major": 3, "minor": 2, "none": 1}


def _softening_read(bar_recs, window=3):
    """Severity easing while the artifact barely changed is the softening
    signature — a critic drifting agreeable, not an artifact improving. Only
    readable when rounds carry --diff-lines; silent otherwise."""
    recs = [r for r in bar_recs if "diff_lines" in r][-window:]
    if len(recs) < 2:
        return None
    sev = [SEVERITY_RANK.get(r.get("severity"), 3) for r in recs]
    if sev[-1] < sev[0] and max(r["diff_lines"] for r in recs) <= 10:
        return ("severity eased while diffs stayed under 10 lines — possible critic "
                "softening, not progress; re-run the verdict with rotated framing "
                "before trusting it")
    return None


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


def _stall_read(bar_recs, champ_recs, stops, target):
    """Has this dimension stopped paying for its rounds?

    Returns (stalled, note). Stalling is the prune signal: it is not a verdict
    on the artifact, only on whether more rounds of *this* lane are worth money.
    """
    n = stops["no_progress_n"]
    if len(bar_recs) < n:
        return False, f"{len(bar_recs)} bar round(s) — too early to call it"
    # Flat at or above the target with no gap named is done, not stuck. This is
    # the normal shape of a lane whose recent rounds ran at the screening tier
    # (a deciding streak would already have retired it): the next spend is one
    # deciding verdict, not a park. Without this read, the prune eats winning
    # lanes and `extend` then demands they be parked.
    window = bar_recs[-n:]
    if all(r.get("severity") == "none" for r in window) and \
            window[-1]["score"] >= target:
        return False, (
            f"flat at {window[-1]['score']} with no gap named — at the target, awaiting "
            "a deciding-tier verdict to retire, not stalled"
        )
    trend = _dimension_trend(bar_recs, window=n)
    if trend["improving"] is False:
        # A flat score with a *different* named gap every round is not a stall:
        # the lane is closing gaps and finding the next one, and the score simply
        # has not crossed a threshold yet. Only call it stalled when the flatness
        # outlives that excuse — otherwise the prune eats the lanes doing the
        # most honest work. Found by running this loop on itself.
        window = bar_recs[-n:]
        named = [r.get("gap") for r in window if r.get("severity") not in (None, "none")]
        if len(named) == len(window) and len(set(named)) == len(named):
            if len(bar_recs) < 2 * n:
                return False, (
                    f"score flat over {n} rounds, but each round named a different gap — "
                    "closing gaps and finding the next, not stalling"
                )
            return True, (
                f"score flat for {2 * n} rounds despite a new gap each round — the gaps are "
                "real but too small to move the score; the bar or the lane is wrong"
            )
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
    for r in rounds:
        keys.setdefault((r["lane"], r["dimension"]), []).append(r)
    # A declared lane/dimension pair with no rounds yet is OPEN work, not absent
    # work. Reading the key set out of the log alone made unjudged pairs
    # invisible: the next-wave plan could not fund a lane the WIP limit had
    # deferred, so the wave that owed it a round was skipped, and "all lanes
    # retired" fired over lanes nobody had ever judged. Seed every declared pair
    # and let the log fill it in. Lanes seen in the log but missing from
    # config.json still count — log-round only warns on those.
    declared_dims = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    for lane in cfg.get("lanes") or []:
        for dim in declared_dims:
            keys.setdefault((lane, dim), [])
    # Cost per lane, mixed honestly: measured rounds report what they logged,
    # unmeasured rounds fall back to the estimate. The old all-or-nothing read
    # (one --calls record silenced the estimator for the whole lane) made a
    # partially measured run look far cheaper than it was.
    lane_groups = {}  # lane -> {(wave, round): {"calls": int|None, "tokens": int|None}}
    for r in rounds:
        g = lane_groups.setdefault(r["lane"], {}).setdefault(
            (r["wave"], r["round"]), {"calls": None, "tokens": None}
        )
        if "calls" in r:
            g["calls"] = (g["calls"] or 0) + r["calls"]
        if "tokens" in r:
            g["tokens"] = (g["tokens"] or 0) + r["tokens"]
    lane_cost = {}
    for lane, groups in lane_groups.items():
        calls = sum(
            g["calls"] if g["calls"] is not None else CALLS_PER_LANE_ROUND
            for g in groups.values()
        )
        tokens = sum(g["tokens"] or 0 for g in groups.values())
        measured = sum(1 for g in groups.values() if g["tokens"] is not None)
        lane_cost[lane] = (calls, tokens, measured, len(groups))
    out = {}
    for key, recs in keys.items():
        lane, dim = key
        tgt = target_for(cfg, dim)
        bar_recs = [r for r in recs if r["mode"] in BAR_MODES]
        champ_recs = [r for r in recs if r["mode"] == "champion"]
        bar_met, clean = _streaks(bar_recs, tgt)
        margins = [r["margin"] for r in bar_recs][-5:]
        # Trends and stalls read one tier track at a time. Screening and
        # deciding verdicts come from different critics; pooling them makes a
        # tier switch read as the artifact moving (model-routing.md). Follow
        # the track the latest round ran on — that is the one being funded.
        screening_recs = [r for r in bar_recs if r.get("tier") == "screening"]
        deciding_recs = [r for r in bar_recs if r.get("tier") != "screening"]
        if screening_recs and deciding_recs:
            on_screening = bar_recs[-1].get("tier") == "screening"
            track_recs = screening_recs if on_screening else deciding_recs
            track_note = " [screening track]" if on_screening else " [deciding track]"
        else:
            track_recs, track_note = bar_recs, ""
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
        stalled, stall_note = _stall_read(track_recs, champ_recs, stops, tgt)
        is_parked = key in parked
        trend = _dimension_trend(track_recs, window=stops["no_progress_n"])
        if track_note:
            trend = {**trend, "note": trend["note"] + track_note}
            stall_note += track_note
        out[key] = {
            "bar_rounds": len(bar_recs),
            "screening_rounds": len(screening_recs),
            "blind_promos": sum(1 for r in champ_recs if r.get("blind")),
            "champ_rounds": len(champ_recs),
            "softening": _softening_read(track_recs),
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
            "target": tgt,
            "lane_calls": lane_cost.get(lane, (0, 0, 0, 0))[0],
            "lane_tokens": lane_cost.get(lane, (0, 0, 0, 0))[1],
            "token_coverage": lane_cost.get(lane, (0, 0, 0, 0))[2:4],
            "state": "RETIRED" if retired else "PARKED" if is_parked else "STALLED" if stalled else "OPEN",
        }
    # A lane retires only when every *declared* dimension has retired — a
    # dimension nobody ever judged must not let the lane out early. A lane
    # *closes* when each dimension is retired or parked: nothing left to fund.
    lanes = {lane for lane, _ in out}
    retired_lanes = {
        lane for lane in lanes
        if all(out.get((lane, d), {}).get("retired") for d in declared_dims)
    }
    closed_lanes = {
        lane for lane in lanes
        if all(
            out.get((lane, d), {}).get("retired") or out.get((lane, d), {}).get("parked")
            for d in declared_dims
        )
    }
    return out, retired_lanes, closed_lanes


def _active_keys(per):
    return [k for k, s in per.items() if not s["retired"] and not s["parked"]]


def _next_wave_plan(per, cfg):
    """Which lanes the next wave should fund, ranked by evidence.

    Moving dimensions first, then unread ones, then stalled — and inside each
    band, dimensions still below their usable line come before dimensions
    polishing above it (the build order: usable everywhere before lovable
    anywhere), then the Phase 3 ranking (the order of `lanes` in config.json)
    breaks the tie. Without that tiebreaker the plan funded whichever lane
    happened to be judged first, and the ranked list the contract agreed was
    never consulted. The WIP limit cuts the tail: funding every lane a little
    is how a budget dies without a result.
    """
    active = _active_keys(per)
    if not active:
        return [], []
    rank = {True: 0, None: 1, False: 2}
    lane_rank = {lane: i for i, lane in enumerate(cfg.get("lanes") or [])}

    def sort_key(k):
        s = per[k]
        sev_rank = 0 if s["open_gap"] and s["trend"]["improving"] is not False else 1
        below_usable = s["last_score"] is None or s["last_score"] < usable_line(s["target"])
        return (
            2 if s["stalled"] else rank[s["trend"]["improving"]],
            0 if below_usable else 1,
            sev_rank,
            lane_rank.get(k[0], len(lane_rank)),
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
        # The per-key trend already reads the right tier track — recomputing it
        # here from raw records would price the extension on a pooled reading.
        t = per[key]["trend"]
        trends[key] = t
        mark = {True: "still moving", False: "flat", None: "unknown"}[t["improving"]]
        gap = per[key]["open_gap"] or (
            "never judged — no verdict was logged against this dimension"
            if not per[key]["bar_rounds"] else "last verdict named no gap"
        )
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


def _paths_hash(paths):
    """Content hash of a gate's declared inputs. A gate is invalidated by a change
    to what it reads, never by the passage of a round.

    Returns (hash, files_seen). A gate whose paths resolve to no file at all —
    empty `paths`, a typo, a glob the shell would have expanded — hashes the same
    empty state forever, so it would pass once and then be skipped for the rest of
    the run without ever being checked again. The caller refuses to cache that.
    """
    h = hashlib.sha256()
    seen = 0
    for spec in sorted(paths):
        pp = Path(spec)
        files = sorted(pp.rglob("*")) if pp.is_dir() else [pp]
        for f in files:
            if f.is_file():
                seen += 1
                h.update(f.as_posix().encode())
                h.update(f.read_bytes())
    return h.hexdigest()[:16], seen


def _read_gate_cache(cache_p):
    """Tolerant cache read. The cache is disposable — a corrupt file (a run
    killed mid-write) costs one full re-run of the suite, never a traceback
    that blocks all gating."""
    if not cache_p.exists():
        return {}
    try:
        return json.loads(cache_p.read_text())
    except json.JSONDecodeError:
        print(
            "warning: gates.json is corrupt (interrupted write?) — cache rebuilt, "
            "every gate re-runs this pass",
            file=sys.stderr,
        )
        return {}


def cmd_gate(args):
    """Run the mechanical checks — and skip the ones whose inputs have not moved.

    This is the counterpart to "settled work is not re-judged": a check that
    passed against a state that has not changed does not need a second opinion,
    and certainly not a subagent's.
    """
    root = Path(args.root)
    cfg = load_config(root)
    gates = cfg.get("gates") or []
    if not gates:
        print("no gates declared. Anything a command can decide belongs here, not in a\n"
              "critic prompt — add them to config.json under \"gates\" as\n"
              '  {"name": ..., "cmd": "<shell>", "paths": ["<files the check reads>"]}')
        return
    # Concurrent lanes gate at once, and the checks are the slow part — so the
    # checks run without any lock (worst case two lanes run the same unchanged
    # gate once each), and only the cache merge at the end is serialised.
    # Holding the lock across the subprocesses turned "gates are not a wave
    # barrier" (SKILL.md) into a suite-wide mutex.
    cache_p = root / "gates.json"
    cache = _read_gate_cache(cache_p)
    rounds = load_rounds(root)
    wave = max((r["wave"] for r in rounds), default=0)
    ran = skipped = failed = 0
    results = []
    unreadable = []
    updates = {}
    dropped = []
    for g in gates:
        name, cmd, paths = g["name"], g["cmd"], g.get("paths") or []
        h, files_seen = _paths_hash(paths)
        prev = cache.get(name)
        if files_seen and prev and prev.get("hash") == h and prev.get("ok") and not args.force:
            skipped += 1
            results.append((name, "SKIP", f"unchanged since wave {prev.get('wave', '?')}"))
            continue
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ok = proc.returncode == 0 and not proc.stdout.strip()
        ran += 1
        if not ok:
            failed += 1
        detail = (proc.stdout + proc.stderr).strip().splitlines()
        first = detail[0] if detail else ""
        if not ok and proc.returncode == 0:
            # The contract is "fails on non-zero exit OR any stdout" — say which
            # one fired, or a passing test suite reads as a failure with its own
            # success line as the only explanation.
            first = f"exit 0 but wrote to stdout: {first}" if first else "exit 0 but wrote to stdout"
        results.append((name, "PASS" if ok else "FAIL", first))
        if files_seen:
            updates[name] = {"hash": h, "ok": ok, "wave": wave, "ts": now()}
        else:
            # Never cache a gate with nothing to hash: it would be skipped from
            # here on without being checked. Run it every wave and say why.
            dropped.append(name)
            unreadable.append(name)
    # Merge under the lock: another lane may have written results while ours ran.
    lock_f = (root / ".gates.lock").open("a+")
    try:
        import fcntl
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
    except (ImportError, OSError):
        fcntl = None  # no flock (Windows, exotic filesystem) — merge stays best-effort
    fresh = _read_gate_cache(cache_p)
    fresh.update(updates)
    for name in dropped:
        fresh.pop(name, None)
    tmp = cache_p.parent / (cache_p.name + ".tmp")
    tmp.write_text(json.dumps(fresh, indent=2) + "\n")
    os.replace(tmp, cache_p)  # atomic — a killed run never leaves a half-written cache
    if fcntl:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
    lock_f.close()
    for name, state, detail in results:
        print(f"  [{state}] {name}" + (f" — {detail}" if detail else ""))
    print(f"\n{ran} run, {skipped} skipped (inputs unchanged), {failed} failed")
    if unreadable:
        print(
            "warning: these gates declare no readable path, so the cache cannot tell when they\n"
            "go stale and they re-run every wave: " + ", ".join(unreadable) + "\n"
            "Declare every file each check reads under \"paths\" in config.json."
        )
    if skipped:
        print("Hand these results to the critic. A round that re-derives them pays twice.")
    if failed:
        sys.exit(1)


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

    per, _retired, _closed = _lane_dim_status(rounds, cfg)
    stats = per.get(key)
    unjudged = stats is not None and not stats["bar_rounds"] and not stats["champ_rounds"]
    if (stats is None or unjudged) and not args.force:
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
    per, _retired, _closed = _lane_dim_status(rounds, cfg)
    funded, deferred = _next_wave_plan(per, cfg)
    print(f"parked [{args.lane} / {args.dimension}] at wave {max_wave} — {reason}")
    print(
        "  A park defunds EVERY remaining gap in this dimension. If the blocker is one\n"
        "  structural gap while the rest still moves, the cheaper move is smaller: that\n"
        "  gap goes to backlog.md as deliberately-not-funded and the dimension keeps its\n"
        "  funding for the gaps that remain (stop-conditions.md)."
    )
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
    tok = sum(r.get("tokens", 0) for r in rounds)
    tbudget = stops.get("budget_tokens")
    token_depleted = bool(tbudget and tok >= tbudget)
    if max_wave < budget and not token_depleted and not args.force:
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

    per, retired, _closed = _lane_dim_status(rounds, cfg)
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

    ext_rec = {
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
    }
    if args.budget_tokens is not None:
        if tbudget and args.budget_tokens <= tbudget:
            die(f"--budget-tokens {args.budget_tokens:,} does not raise the current ceiling of {tbudget:,}")
        ext_rec["budget_tokens_from"] = tbudget
        ext_rec["budget_tokens_to"] = args.budget_tokens
        stops["budget_tokens"] = args.budget_tokens
    elif token_depleted:
        print(
            f"warning: the token budget is depleted ({tok:,} of {tbudget:,}) and this grant "
            "does not raise it — pass --budget-tokens <N> with the user's grant, or the token "
            "stop stays fired whatever the wave count says.",
            file=sys.stderr,
        )
    cfg["extensions"].append(ext_rec)
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


def _ceil(x):
    return int(x) + (x % 1 > 0)


def _climb_rounds(score, target, rpg):
    """Estimated rounds for one lane to climb from `score` to `target`.

    One gap is roughly one score point up to 7 (the usable rung); above 7 each
    point costs about double the one before — the tapering the method's own
    literature measures (Madaan et al., cost-discipline.md). 9→10 is priced
    nowhere: bar-met cannot fire at 10, so a 10 is a stretch, not a target.
    """
    total = 0.0
    for p in range(int(score), int(target)):
        total += rpg * (2 ** max(0, (p + 1) - 7))
    return total


def cmd_quote(args):
    """Print the quality-price menu: what each target rung costs from here.

    Pre-run it prices from first light's single score; at a wave boundary it
    prices each open lane from its last score, and swaps the rounds-per-gap
    guess for the measured cost per closed gap where the log has one. The
    menu exists so TARGET and BUDGET are chosen together, informed — a user
    who sees 9 cost three times 7 picks on purpose, in either direction.
    """
    root = Path(args.root)
    cfg = load_config(root)
    stops = cfg["stops"]
    rounds = load_rounds(root)
    wip = cfg.get("wip_limit") or DEFAULT_CONFIG["wip_limit"]

    rpg, rpg_src = args.rounds_per_gap, "assumed (minor gap ≈ 1 round, major ≈ 2-3; pass --rounds-per-gap)"
    tpr, tpr_src = args.tokens_per_round, "from --tokens-per-round"
    lane_scores = {}
    budget_left = stops["budget_waves"]

    if rounds:
        per, _r, _c = _lane_dim_status(rounds, cfg)
        open_keys = _active_keys(per)
        if args.dimension:
            open_keys = [k for k in open_keys if k[1] == args.dimension]
            if not open_keys:
                die(f"no open lane carries dimension {args.dimension!r}")
        unjudged = [k for k in open_keys if per[k]["last_score"] is None]
        if unjudged and args.current_score is None:
            die(
                "these open dimensions were never judged: "
                + ", ".join(f"{l}/{d}" for l, d in unjudged)
                + " — pass --current-score to price them, or judge them first"
            )
        for (lane, _dim), s in ((k, per[k]) for k in open_keys):
            sc = s["last_score"] if s["last_score"] is not None else args.current_score
            lane_scores[lane] = min(lane_scores.get(lane, 10), sc)
        closed = sum(s["gaps_closed"] for s in per.values())
        bar_rounds = sum(s["bar_rounds"] for (l, d), s in per.items())
        if args.rounds_per_gap is None and closed:
            rpg, rpg_src = bar_rounds / closed, f"measured: {bar_rounds} bar rounds / {closed} closed gap(s)"
        if tpr is None:
            tok = sum({l: s["lane_tokens"] for (l, _d), s in per.items()}.values())
            meas = sum({l: s["token_coverage"][0] for (l, _d), s in per.items()}.values())
            if meas:
                tpr, tpr_src = tok // meas, f"measured average over {meas} lane-round(s)"
        budget_left = stops["budget_waves"] - max(r["wave"] for r in rounds)
    else:
        if args.current_score is None:
            die("no rounds logged — pass --current-score with first light's verdict score")
        lanes = cfg.get("lanes") or ["artifact"]
        lane_scores = {lane: args.current_score for lane in lanes}
    if rpg is None:
        rpg = 2.0
    if not (0 <= min(lane_scores.values()) <= 10):
        die("scores must be between 0 and 10")

    dt = cfg.get("dimension_targets") or {}
    targets = sorted({int(t) for t in (args.targets or "").split(",") if t.strip()}
                     or ({7, 8, 9, 10} | {stops["target_score"]} | set(dt.values())))
    n_lanes = len(lane_scores)
    print(
        f"quality-price menu{' — dimension ' + args.dimension if args.dimension else ''}"
        f" — from {'scores ' + ', '.join(f'{l}:{s}' for l, s in sorted(lane_scores.items()))}"
        f" | {rpg:.1f} round(s) per gap ({rpg_src}) | {n_lanes} lane(s), WIP {wip}"
    )
    print(f"  {'target':<8}{'waves':<8}{'calls':<8}{'tokens(est)':<14}vs budget ({max(budget_left, 0)} wave(s) left)")
    for t in targets:
        if t >= 10:
            print(f"  {t:<8}{'—':<8}{'—':<8}{'—':<14}not priceable: bar-met cannot fire at 10 — "
                  "write a 10 as the stretch, not the target")
            continue
        per_lane = {l: _climb_rounds(s, t, rpg) for l, s in lane_scores.items()}
        if all(v <= 0 for v in per_lane.values()):
            print(f"  {t:<8}{'0':<8}{'0':<8}{'0':<14}already there — raise the bar or stop")
            continue
        total = sum(per_lane.values())
        waves = _ceil(max(max(per_lane.values()), total / wip))
        calls = _projected_calls(waves, list(lane_scores), wip)
        tok_s = f"~{int(total * tpr):,}" if tpr else "not measured"
        fit = ("fits" if waves <= budget_left
               else f"needs +{waves - max(budget_left, 0)} wave(s)" + (" (extension)" if rounds else ""))
        print(f"  {t:<8}{waves:<8}{'~' + str(calls):<7}{tok_s:<14}{fit}")
    print(
        "assumptions: one gap ≈ one score point up to 7; each point above 7 costs ~2× the "
        "one before (diminishing returns — cost-discipline.md). An estimate to choose a rung "
        "by, not a promise; re-quote at wave boundaries, where the measured cost replaces it."
    )
    if dt and not args.dimension:
        print(
            "note: dimensions carry their own targets ("
            + ", ".join(f"{d}={v}" for d, v in sorted(dt.items()))
            + f", default {stops['target_score']}) — price one dimension's ladder with --dimension <d>"
        )


def cmd_bar_request(args):
    """Write gauntlet/bar-request.md — what comparison material this run needs.

    The loop compares A against B. When B does not exist yet, the honest move
    is to name what would settle each dimension and stop, so a user or a scout
    agent can fetch it — never to invent a standard and grade against it.
    """
    root = Path(args.root)
    cfg = load_config(root)
    dims = cfg.get("dimensions") or DEFAULT_CONFIG["dimensions"]
    have = sorted(f.name for f in (root / "bar").rglob("*") if f.is_file()) if (root / "bar").exists() else []
    L = [
        "# Bar request — comparison material this run needs before wave 1",
        "",
        f"Bar kind agreed at intake: **{cfg.get('bar_kind', 'reference')}**",
        f"Already frozen in `{root}/bar/`: " + (", ".join(f"`{n}`" for n in have) if have else "_nothing yet_"),
        "",
        "A gauntlet's output is \"A or B is better\". Without a B that exists outside",
        "this run, every verdict measures the builder's own taste. So this run does not",
        "start until the material below is in place — or until the user decides the run",
        "is not worth it, which is also a valid answer.",
        "",
        "## What a usable bar must satisfy",
        "",
        "1. **External** — it exists independently of this run and of the agent's opinion.",
        "2. **Inspectable** — a critic can open, run or measure it, not just read about it.",
        "3. **Unarguable** — the artifact cannot talk its way past it.",
        "4. **Reachable** — the distance from today's artifact is closeable inside the budget.",
        "",
        "## Per dimension",
        "",
    ]
    for d in dims:
        L += [
            f"### {d}  (target {target_for(cfg, d)}/10)",
            "",
            "- **What would settle it** (lead agent: name the comparator concretely — the",
            "  product, document, implementation, measurement or corpus a critic would hold",
            f"  up next to ours to judge *{d}*):",
            "- **Acceptable forms**: reference artifact (files, screenshots at a stated",
            "  viewport, recordings), a measurement plus threshold, a competing",
            "  implementation, or — where nothing comparable exists — a research-backed",
            "  spec and answer key authored before wave 1 (`bar-selection.md`).",
            "- **Where it goes**: `" + f"{root}/bar/{d}/" + "` (frozen; read-only once wave 1 starts).",
            "- **Done when**: a critic given only that path can score our artifact against it",
            "  without asking anyone what \"good\" means.",
            "",
        ]
    L += [
        "## For whoever fetches this",
        "",
        "Bring the real thing, not a description of it: a paraphrased bar drifts every",
        "time it is restated, and drift always makes the bar easier. Capture references",
        "at comparable framing and resolution to our own output. If the best available",
        "comparator is weaker than the ambition, say so — a run against a soft bar that",
        "everyone believes is hard is worse than no run.",
        "",
        "Answer-key route only: state each item as something checkable, and mark which",
        "dimensions it cannot cover (taste, feel, visual craft) so those get a reference",
        "artifact of their own instead of passing by default.",
    ]
    out = root / "bar-request.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out}")
    print("Hand it to the user or to a scout agent. Do not start wave 1 until "
          f"{root}/bar/ holds something a critic can open.")


def cmd_plan(args):
    """Draft gauntlet/plan.md — the run's forward-looking scaffold.

    The workbench looks backward (what happened); the plan looks forward:
    the build stages in order, which dimensions each stage climbs, and what
    each stage costs at current prices. Stage order is Kniberg's ladder run
    at run level — bootstrap to testable, climb everything to usable, only
    then climb the ambitious dimensions to their higher targets, and stretch
    only on a user grant. Regenerate at wave boundaries: prices swap from
    the intake guess to measured actuals as the log fills.
    """
    root = Path(args.root)
    cfg = load_config(root)
    stops = cfg["stops"]
    rounds = load_rounds(root)
    wip = cfg.get("wip_limit") or DEFAULT_CONFIG["wip_limit"]
    per, _r, _c = _lane_dim_status(rounds, cfg)

    rpg, rpg_src = args.rounds_per_gap, "assumed — pass --rounds-per-gap or let the log measure it"
    tpr = args.tokens_per_round
    if rounds:
        closed = sum(s["gaps_closed"] for s in per.values())
        bar_rounds_n = sum(s["bar_rounds"] for s in per.values())
        if args.rounds_per_gap is None and closed:
            rpg, rpg_src = bar_rounds_n / closed, f"measured: {bar_rounds_n} bar rounds / {closed} closed gap(s)"
        if tpr is None:
            tok = sum({l: s["lane_tokens"] for (l, _d), s in per.items()}.values())
            meas = sum({l: s["token_coverage"][0] for (l, _d), s in per.items()}.values())
            if meas:
                tpr = tok // meas
    if rpg is None:
        rpg = 2.0

    done, bootstrap, to_usable, to_target = [], [], [], []
    for key in sorted(per):
        s = per[key]
        if s["retired"] or s["parked"]:
            done.append(key)
        elif s["last_score"] is None:
            score = args.current_score
            (bootstrap if score is None else
             to_usable if score < usable_line(s["target"]) else to_target).append(key)
        elif s["last_score"] < usable_line(s["target"]):
            to_usable.append(key)
        else:
            to_target.append(key)
    # Everything active at/above its usable line is stage-3 work by definition:
    # still open (no retirement streak yet), climbing toward its own target.

    def stage_price(keys, to_line):
        per_lane = {}
        for lane, dim in keys:
            score = per[(lane, dim)]["last_score"]
            score = args.current_score if score is None else score
            tgt = to_line(per[(lane, dim)]["target"])
            per_lane[lane] = per_lane.get(lane, 0.0) + _climb_rounds(score, tgt, rpg)
        tot = sum(per_lane.values())
        if tot <= 0:
            return 0, 0, 0
        # Makespan bound: no shorter than the longest lane, no shorter than the
        # total spread over the WIP slots.
        waves = _ceil(max(max(per_lane.values()), tot / wip))
        calls = _projected_calls(waves, sorted(per_lane), wip)
        return waves, calls, int(tot * tpr) if tpr else 0

    def fmt(keys, to_line=None):
        out = []
        for l, d in keys:
            s = per[(l, d)]["last_score"]
            s = args.current_score if s is None else s
            goal = per[(l, d)]["target"] if to_line is None else to_line(per[(l, d)]["target"])
            out.append(f"{l}/{d} ({'?' if s is None else s}→{goal})")
        return ", ".join(out) or "—"

    L = [
        "# Gauntlet plan (drafted by `gauntlet.py plan` — lead agent completes the anchor and order fields)",
        "",
        f"Contract: gauntlet/contract.md | bar: gauntlet/bar/ | WIP {wip} | "
        f"budget {stops['budget_waves']} wave(s)"
        + (f", {stops['budget_tokens']:,} tokens" if stops.get("budget_tokens") else ""),
        f"Prices: {rpg:.1f} round(s) per gap ({rpg_src})"
        + (f", ~{tpr:,} tokens per lane-round" if tpr else ", tokens unmeasured"),
        "",
        "Build order — a stage starts when the one before it has nothing left in it.",
        "Rungs above usable wait: whole-and-crude beats one-part-excellent (bar-selection.md).",
        "",
        "## Stage 0 — First light (testable)",
        "One thin end-to-end build, one verified inspection path, one verdict.",
        "Recorded in contract.md, not the log. Done before this plan means anything.",
        "",
        "## Stage 1 — Bootstrap: every dimension judged once",
        f"Dimensions never judged: {fmt(bootstrap)}",
        "(unpriced until judged — first light or the bootstrap wave sets the number)"
        if bootstrap else (
            "(empty — every declared dimension has a logged verdict)" if rounds else
            f"(priced from --current-score {args.current_score} — first light's verdict; "
            "each dimension still logs its own first verdict in wave 1)"
        ),
        "",
    ]
    w2, c2, t2 = stage_price(to_usable, lambda tgt: usable_line(tgt))
    L += [
        "## Stage 2 — Climb to usable (everything to its usable line)",
        f"Dimensions below usable: {fmt(to_usable, usable_line)}",
        (f"Price: ~{w2} wave(s), ~{c2} calls" + (f", ~{t2:,} tokens" if t2 else "")) if to_usable else "(empty)",
        "",
    ]
    w3, c3, t3 = stage_price(to_target, lambda tgt: tgt)
    L += [
        "## Stage 3 — Climb to target (the ambitious dimensions)",
        f"Dimensions above usable, below their target: {fmt(to_target)}",
        (f"Price: ~{w3} wave(s), ~{c3} calls" + (f", ~{t3:,} tokens" if t3 else "")) if to_target else "(empty)",
        "",
        "## Stage 4 — Stretch (user-bought only)",
        "The contract's stretch, re-armed as an announced target with the same guards.",
        "Never entered on the run's own authority; priced with `quote` when offered.",
        "",
        "## What each rung buys (lead agent: copy the anchors from contract.md)",
        "Per dimension, one line per rung on the menu: what n/10 concretely IS for",
        "this artifact — the anchor the user agreed to, not an adjective.",
        "",
        "## Order constraints (lead agent: record the serialised pairs)",
        "Lanes where one result changes what 'good' means for another",
        "(lighting before materials — decomposition.md), and why.",
        "",
        f"Retired/parked already: {fmt(done) if done else '—'}",
    ]
    out = root / "plan.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out}")
    stage = ("1 (bootstrap)" if bootstrap else "2 (climb to usable)" if to_usable
             else "3 (climb to target)" if to_target else "done — every dimension retired or parked")
    print(f"current stage: {stage}")


def cmd_status(args):
    root = Path(args.root)
    cfg = load_config(root)
    rounds = load_rounds(root)
    # The same rule as gates: a bar that resolves to no file cannot invalidate
    # anything, and it erodes silently — every verdict is then judged against a
    # paraphrase carried in context. bar_kind names what the bar is; this checks
    # that it exists at all.
    bar_dir = root / "bar"
    bar_frozen = bar_dir.exists() and any(f.is_file() for f in bar_dir.rglob("*"))
    if not bar_frozen:
        print(
            "WARNING: gauntlet/bar/ contains no files — bar verdicts are being judged "
            "against nothing frozen. Freeze the comparator files before the next round "
            "(bar-selection.md: bars described from memory drift; bars stored as files do not).\n"
        )
    if not rounds:
        # Wave 1 is exactly when the funded plan is needed — the declared lanes
        # are seeded even with an empty log, so print the plan instead of nothing.
        per, _retired, _closed = _lane_dim_status([], cfg)
        funded, deferred = _next_wave_plan(per, cfg)
        print("no rounds logged yet — plan from config:")
        if funded:
            cost = _projected_calls(1, funded, cfg.get("wip_limit"))
            print(f"NEXT WAVE (WIP {cfg.get('wip_limit')}): {', '.join(funded)}  → ~{cost} subagent calls")
            if deferred:
                print(f"  waiting: {', '.join(deferred)} — do not widen the wave to fit them in")
        else:
            print("no lanes declared — pass --lanes at init (or init --force after the cut)")
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
          f" | {closed_gaps} gap(s) closed{per_gap} | WIP limit {wip}")
    tok = sum({lane: s2["lane_tokens"] for (lane, _d), s2 in per.items()}.values())
    coverage = {lane: s2["token_coverage"] for (lane, _d), s2 in per.items()}
    tok_measured = sum(m for m, _t in coverage.values())
    tok_rounds = sum(t for _m, t in coverage.values())
    tbudget = cfg["stops"].get("budget_tokens")
    if tok:
        line = f"tokens: {tok:,} measured"
        if tok_measured < tok_rounds:
            # Partial measurement must read as a floor, not a total — one
            # measured round out of five used to silence the other four.
            line += (f" on {tok_measured} of {tok_rounds} lane-round(s) — "
                     "a floor, not the burn")
        if closed_gaps:
            line += f" ({tok // closed_gaps:,} per closed gap)"
        if tbudget:
            pct = 100 * tok // tbudget
            line += f" — {pct}% of the {tbudget:,} agreed"
            if tok >= tbudget:
                line += "  ** TOKEN BUDGET DEPLETED **"
        else:
            line += " — no token budget agreed; waves are the only ceiling"
        print(line)
    else:
        print("tokens: not measured. Waves are what the user agreed to; tokens are what "
              "burns. Pass --tokens on log-round or the budget is in the wrong unit.")
    print()

    for (lane, dim), s in sorted(per.items()):
        head = f"[{lane} / {dim}] {s['state']}"
        print(head)
        screen = f" ({s['screening_rounds']} screening)" if s["screening_rounds"] else ""
        blind_p = f" ({s['blind_promos']} blind)" if s["champ_rounds"] else ""
        print(f"  bar {s['bar_rounds']}{screen}  promoted {s['promotions']}{blind_p}"
              f"  reverted {s['reverts']}"
              f"  streaks bar-met {s['bar_met_streak']} clean {s['clean_streak']}"
              f"  rubric {s['rubric_share']}")
        score = (
            f"score {s['last_score']}/{s['target']} target"
            if s["last_score"] is not None
            else f"never judged (target {s['target']})"
        )
        print(f"  {score}"
              f"  margins {' → '.join(s['recent_margins']) or '—'}  trend: {s['trend']['note']}")
        if s["softening"]:
            print(f"  SOFTENING TRIPWIRE: {s['softening']}")
        if s["stalled"]:
            print(f"  PARK RECOMMENDED: {s['stall_note']}")
        if s["open_gap"]:
            print(f"  open gap: {s['open_gap']}")
        print()

    champ_all = [r for r in rounds if r["mode"] == "champion"]
    if champ_all and not any(r.get("blind") for r in champ_all):
        print("NOTE: every promotion so far ran unblinded. Champion vs challenger is the most\n"
              "blindable comparison in the method — both sides are ours (blind-protocol.md).\n"
              "Export both under randomised labels and log the round with --blind.\n")

    funded, deferred = _next_wave_plan(per, cfg)
    stalled = _park_candidates(per)
    if funded:
        below = [
            k for k in _active_keys(per)
            if per[k]["last_score"] is None or per[k]["last_score"] < usable_line(per[k]["target"])
        ]
        stage = ("climb-to-usable — below the line: "
                 + ", ".join(f"{l}/{d}" for l, d in sorted(below))
                 if below else
                 "climb-to-target — every open dimension is usable; what remains is the rungs above")
        print(f"BUILD STAGE: {stage}")
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
    token_depleted = bool(tbudget and tok >= tbudget)
    if token_depleted:
        fired.append(
            f"token budget ({tok:,} measured >= {tbudget:,} agreed"
            + (f", on {tok_measured} of {tok_rounds} lane-round(s) — the true burn is higher"
               if tok_measured < tok_rounds else "")
            + ") — the run stops like any budget stop; waves left do not override tokens spent"
        )
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

    if all_lanes and all_lanes == retired and max_wave < budget:
        surplus = budget - max_wave
        print(f"\nSURPLUS: every lane retired with {surplus} wave(s) of agreed budget unspent.")
        print("That surplus IS the deliverable — the same result, cheaper — and it returns")
        print("to the user by default. Stop, report, and state the savings. Mention that a")
        print("stretch block exists (contract's stretch as an announced target, same guards)")
        print("only as an option the user may buy; never spend the surplus unasked —")
        print("polishing past the bar converts the savings into gold plating. (bar-selection.md)")

    if max_wave >= budget or token_depleted:
        if token_depleted and max_wave < budget:
            print("\n(the token budget fired before the wave budget — an extension must "
                  "raise the token ceiling too: extend --budget-tokens <N>)")
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
        f"- Target score: {cfg['stops']['target_score']}/10"
        + (" (per-dimension: "
           + ", ".join(f"{d}={v}" for d, v in sorted(cfg["dimension_targets"].items())) + ")"
           if cfg.get("dimension_targets") else "")
        + f" | WIP limit: {cfg.get('wip_limit')} lane(s)",
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
            f"{per[k]['last_score']}/{per[k]['target']}"
            if per[k]["last_score"] is not None else "—",
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
            ("bar-met" if per[k]["bar_met_streak"] >= cfg["stops"]["bar_met_n"] else "clean-streak")
            + f" at {per[k]['target']}",
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
    max_wave = max(r["wave"] for r in rounds)
    budget = cfg["stops"]["budget_waves"]
    lines += [f"Waves run: {max_wave} of {budget} budgeted", ""]
    lines += [
        f"Cost: ~{spent} subagent calls for {closed_gaps} closed gap(s)"
        + (f" (~{spent / closed_gaps:.0f} calls per gap)" if closed_gaps else "")
        + f"; target score {cfg['stops']['target_score']}/10"
        + (" (per-dimension: "
           + ", ".join(f"{d}={v}" for d, v in sorted(cfg["dimension_targets"].items())) + ")"
           if cfg.get("dimension_targets") else ""),
        "",
    ]
    # The parity claim, made checkable: this run promises the same result at
    # lower cost, so the report states cost against the intake projection —
    # the budget the user first agreed to, not the extended one. Measuring
    # against the extended budget let a run that depleted its intake budget
    # and asked for more report the extension as a saving.
    lanes_n = len(cfg.get("lanes") or []) or 1
    per_wave = min(lanes_n, cfg.get("wip_limit") or 3) * CALLS_PER_LANE_ROUND + CALLS_PER_WAVE_OVERHEAD
    initial = initial_budget(cfg)
    projected = per_wave * initial
    verdict = "under" if spent < projected else "at or over"
    lines += [
        f"Against projection: ~{projected} calls projected at intake for {initial} wave(s); "
        f"~{spent} spent — {verdict} projection"
        + (f", {initial - max_wave} wave(s) of the intake budget returned unspent"
           if max_wave < initial else "")
        + ".",
        "",
    ]
    tok = sum(r.get("tokens", 0) for r in rounds)
    if tok:
        tb = cfg["stops"].get("budget_tokens")
        coverage = {lane: s["token_coverage"] for (lane, _d), s in per.items()}
        tok_m = sum(m for m, _t in coverage.values())
        tok_r = sum(t for _m, t in coverage.values())
        lines += [
            f"Tokens: {tok:,} measured"
            + (f" on {tok_m} of {tok_r} lane-round(s) — a floor, not the burn"
               if tok_m < tok_r else "")
            + (f"; {100 * tok // tb}% of the {tb:,} agreed" if tb else "")
            + ".",
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
    hist = cfg.get("park_history") or []
    if hist:
        # A park that was later resumed is exactly the sunk-cost history a
        # reader needs visible: what stopped the lane, and what evidence
        # justified funding it again.
        lines += ["## Parked and later resumed", ""]
        for p in hist:
            lines.append(
                f"- **{p['lane']} / {p['dimension']}** — parked at wave {p.get('at_wave', '?')}"
                f" ({p.get('reason', 'no reason recorded')}), resumed at wave"
                f" {p.get('resumed_at_wave', '?')}: {p.get('resume_reason', 'no reason recorded')}"
            )
        lines += [""]
    blind = sum(1 for r in rounds if r["mode"] == "blind")
    rubric = sum(1 for r in rounds if r["mode"] == "rubric")
    lines += [f"Verdict evidence: {blind} blind rounds, {rubric} rubric rounds (not equivalent evidence)", ""]
    tiers = {}
    for r in rounds:
        if r["mode"] in BAR_MODES and r.get("critic_model"):
            tiers[r["critic_model"]] = tiers.get(r["critic_model"], 0) + 1
    if tiers:
        lines += [
            "Critic tiers: " + ", ".join(f"{m} ({n})" for m, n in sorted(tiers.items()))
            + " — a streak from a cheaper critic is weaker evidence; say so where it matters.",
            "",
        ]
    lines += ["## Lanes", ""]
    for (lane, dim), s in sorted(per.items()):
        detail = (
            f"{s['bar_rounds']} bar rounds, {s['reverts']} reverts,"
            f" last score {s['last_score']}/{s['target']}"
            if s["bar_rounds"]
            else "never judged — no verdict was logged against this dimension"
        )
        lines.append(f"- **{lane} / {dim}** — {s['state'].lower()}; {detail}")
    lines += ["", "## Open gaps (do not soften this section)", ""]
    any_gap = False
    for (lane, dim), s in sorted(per.items()):
        state = " *(parked)*" if s["parked"] else ""
        if s["open_gap"]:
            any_gap = True
            lines.append(f"- [{lane} / {dim}]{state} {s['open_gap']}")
        elif not s["bar_rounds"]:
            # A dimension the run declared and never judged is a hole in the
            # evidence, not a closed gap. The report says so.
            any_gap = True
            lines.append(
                f"- [{lane} / {dim}]{state} never judged — the run declared this dimension"
                " and logged no verdict against it"
            )
    if not any_gap:
        lines.append("- none recorded — verify this against the last wave's verdicts before believing it")
    backlog = root / "backlog.md"
    if backlog.exists():
        items = [
            ln.strip() for ln in backlog.read_text().splitlines()
            if ln.strip().startswith(("-", "*"))
        ]
        if items:
            lines += [
                "",
                "## Noticed, deliberately not funded",
                "",
                "Seen during the run and kept out of it on purpose. This is scope the user"
                " can choose to buy in a future run — it was never silently added to this one.",
                "",
            ]
            lines += items
    lines += [
        "",
        "## Handoff smoke test",
        "",
        "(lead agent: after promoting the best champion and running the smoother, open,"
        " run or render the final artifact once, end to end. State what you opened and"
        " what you saw — the promoted-and-smoothed state is otherwise the one state of"
        " the artifact nobody ever inspected as a whole. 'Not run' is an answer the"
        " reader deserves to see written down.)",
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
    p.add_argument("--dimension-targets",
                   help='per-dimension target overrides, e.g. "gameplay=8,graphics=6" — a blanket '
                        "10/10 request is decomposed into these at intake; unnamed dimensions use "
                        "--target-score")
    p.add_argument("--wip-limit", type=int, help="max lanes funded per wave (default 3)")
    p.add_argument("--budget-waves", type=int)
    p.add_argument("--budget-tokens", type=int,
                   help="token ceiling for the run (optional). Waves are what the user agrees "
                        "to; tokens are what gets consumed — state both or consent is uninformed")
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
    p.add_argument("--tier", choices=("screening", "deciding"), default="deciding",
                   help="screening verdicts steer rounds but never advance retirement streaks")
    p.add_argument("--blind", action="store_true",
                   help="champion mode only: the promotion comparison ran under the blind protocol")
    p.add_argument("--diff-lines", type=int,
                   help="lines changed by this round's build — feeds the softening tripwire")
    p.add_argument("--critic-model",
                   help="model tier that produced this verdict (optional); the report shows the "
                        "distribution, because a streak from a cheap critic is weaker evidence")
    p.add_argument("--tokens", type=int,
                   help="tokens this round actually consumed (subagent + inspection). Optional, "
                        "but without it cost is an estimate in the wrong unit")
    p.add_argument("--calls", type=int,
                   help="subagent calls this round actually cost (optional; estimated when omitted)")
    p.set_defaults(fn=cmd_log_round)

    p = sub.add_parser("status")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("quote", help="price the target rungs: what 7, 8, 9 cost from here; 10 is not a price")
    p.add_argument("--current-score", type=int,
                   help="first light's verdict score (pre-run); mid-run the log's last scores are used")
    p.add_argument("--rounds-per-gap", type=float,
                   help="estimated rounds to close one gap (default 2.0 pre-run; measured cost per closed gap mid-run)")
    p.add_argument("--tokens-per-round", type=int,
                   help="tokens one lane-round costs (default: measured average from the log, when logged)")
    p.add_argument("--targets", help="comma-separated rungs to price (default: 7,8,9,10 plus the configured targets)")
    p.add_argument("--dimension", help="price one dimension's ladder from its own scores (mid-run)")
    p.set_defaults(fn=cmd_quote)

    p = sub.add_parser("bar-request",
                       help="write gauntlet/bar-request.md — the comparison material this run needs, for a user or scout agent")
    p.set_defaults(fn=cmd_bar_request)

    p = sub.add_parser("plan", help="draft gauntlet/plan.md — build stages in order, priced; the forward-looking scaffold")
    p.add_argument("--current-score", type=int,
                   help="score for dimensions not yet judged (first light's verdict), so their stages price")
    p.add_argument("--rounds-per-gap", type=float,
                   help="estimated rounds to close one gap (default 2.0; measured cost per closed gap mid-run)")
    p.add_argument("--tokens-per-round", type=int,
                   help="tokens one lane-round costs (default: measured average from the log, when logged)")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("park", help="stop funding a lane/dimension that stopped moving")
    p.add_argument("--lane", required=True)
    p.add_argument("--dimension", default="overall")
    p.add_argument("--reason", required=True, help="the log read that justifies stopping the spend")
    p.add_argument("--resume", action="store_true",
                   help="unpark: fund it again, on new evidence only")
    p.add_argument("--force", action="store_true",
                   help="park a dimension the log still reads as moving (scope or priority call)")
    p.set_defaults(fn=cmd_park)

    p = sub.add_parser("gate", help="run the mechanical checks; skip those whose inputs have not changed")
    p.add_argument("--force", action="store_true", help="re-run every gate, ignoring the cache")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("board", help="regenerate gauntlet/workbench.md from the log")
    p.set_defaults(fn=cmd_board)

    p = sub.add_parser("extend", help="raise the wave budget after the user grants an extension")
    p.add_argument("--waves", type=int, required=True, help="additional waves granted")
    p.add_argument("--reason", required=True, help="the user's grant, justified from the log")
    p.add_argument("--budget-tokens", type=int,
                   help="raise the token ceiling with the same grant (required when the "
                        "token budget is what fired)")
    p.add_argument("--force", action="store_true",
                   help="override the depleted-budget, unparked-stall and at-ceiling guards")
    p.set_defaults(fn=cmd_extend)

    p = sub.add_parser("report")
    p.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    # `status | head` is the normal way to read this output; without the guard
    # Python raises BrokenPipeError on the way out and the agent sees a crash
    # where it should see a clean exit.
    try:
        main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            os._exit(0)
