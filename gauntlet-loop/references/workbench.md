# The workbench

A long unattended run needs a surface the user can glance at without interrupting
it. Interrupting to ask for status costs a context switch on both sides and is the
main reason people stop letting loops run long enough to work.

## The Live Kanban Workbench

The workbench is `gauntlet/workbench.html`, copied from this skill's
`assets/workbench.html` during Phase 0 and opened in the user's browser. It polls
`gauntlet/state.json` and re-renders itself.

**CRITICAL RULE: nobody edits the HTML, and nobody edits `state.json` by hand.**
Both are generated:

```bash
python3 scripts/gauntlet.py board     # rewrites gauntlet/state.json from the log
```

Run it at every wave boundary, and after `escalate`, `shelve` or `extend`. This
is a cost decision as much as a correctness one: a subagent that has to open an
HTML file to report its progress pays for the whole file, every round it does so,
and a progress surface should not be one of the more expensive things in the run.

The board shows four columns — **open**, **flat** (no movement in the last
`flat_rounds_n` bar rounds; shelve or re-cut), **shelved**, **retired** — plus the
current wave, effort tier, the models that tier runs, calls per lane per round,
and spend against budget in the user's currency.

## Language Rules (ASD-STE100)

All visible text on the Kanban board (goals, gaps, next fixes) must be written in Simplified Technical English:
1. Maximum sentence length: 20-25 words.
2. Use active voice always.
3. One instruction or statement per sentence.
4. ZERO AI marketing language (no "amazing", "leverage", "streamline", "delve").
5. Be direct and objective.

## What it needs

- Current wave, active lanes, elapsed time and budget consumed — including any
  granted extensions (`wave 9 of 11: initial 8, extended +3`), so the user can
  see at a glance what the run has cost against what they agreed to
- Per lane: rounds run, current verdict, current named gap, clean-streak counter
- **Evidence over time** — the artifact evolving, in whatever form it takes:
  screenshots, rendered pages, drafts, benchmark numbers, test output
- Champion history, so a user can see whether it is still climbing
- Reverts, visibly — a run that reverts often looks different from one that does not

## Round log schema

`gauntlet/rounds.jsonl` is append-only and written **only** through
`gauntlet.py log-round` — the validation (no gap without severity, losers get
reverted, evidence always) is the point. The workbench renders from it and the
end-of-run report is drafted from it.

Two record shapes share the file, distinguished by `mode`:

**Bar comparison** (`mode: blind | rubric`) — drives streaks and gaps:

```json
{
  "ts": "2026-08-05T14:31:02+00:00",
  "wave": 3, "lane": "terrain-lighting", "dimension": "visual", "round": 7,
  "mode": "blind", "winner": "other", "margin": "thin",
  "score": 7,
  "severity": "minor",
  "gap": "no contact shadow where rock meets ground plane",
  "evidence": "gauntlet/shots/w3-terrain-r7.png",
  "critic_framing": "domain-specialist",
  "tier": 2,
  "tokens": 130000
}
```

**Promotion comparison** (`mode: champion`) — drives promote/revert:

```json
{
  "ts": "2026-08-05T14:29:41+00:00",
  "wave": 3, "lane": "terrain-lighting", "dimension": "visual", "round": 7,
  "mode": "champion", "winner": "ours", "margin": "clear",
  "score": 8,
  "action": "promoted", "champion_ref": "4f2a91c",
  "evidence": "gauntlet/shots/w3-terrain-r7-champ.png",
  "critic_framing": "default"
}
```

`champion_ref` is the git ref of the pre-round champion — it is what makes any
past state recoverable and the "best champion" findable at stop time. Blind and
rubric records are not equivalent evidence; `status` reports the rubric share so
the report can say so.

`tier` and `tokens` are what let the run price itself. `tier` is stamped
automatically; `tokens` you pass, and a record without it is logged with a
warning — a run that cannot say what it spent cannot say when to stop spending.

**Spend that produced no round** — builders, the smoother, your own passes — goes
in `gauntlet/spend.jsonl` via a separate command, because it is the larger half of
the bill and the round log has nowhere to put it:

```bash
python3 scripts/gauntlet.py spend --tokens 300000 --role builder --wave 3 \
    --note "terrain-lighting builder, contact-shadow gap"
```

## Reading the log

`gauntlet.py status` computes streaks, retirement, revert rates and fired stop
conditions from the log — run it at every wave boundary instead of counting in
your head. Beyond what it prints, three patterns to watch:

**Margins narrowing** across rounds in a lane — approaching the ceiling. Expected
and healthy.

**Revert rate rising** — challengers losing more than winning. The lane has run
out of closeable gaps, or the lane is cut wrong.

**The same gap recurring** across rounds after being marked closed — either the
builder is not actually closing it, or it is structural and no amount of lane-level
work will fix it. Escalate to a re-cut rather than running the same round again.

**Burn rate against remaining budget.** `status` prints tokens per wave and how
many waves of budget remain at that rate. When that number drops below the waves
you still expect to need, the decision is now, not at depletion: shelve something,
re-cut, or go back to the user early.

## Reporting at the end

`gauntlet.py report` drafts the report from the log; you complete the judgement
fields. It must cover:

- Bar used, and whether it was raised mid-run
- Lanes, rounds each, and how each retired
- The gaps that closed
- **The gaps still open** — the section the user actually needs
- Blind versus rubric round counts
- Any budget extensions, with the reason each was granted and whether it paid off
- Whether the loop was still improving at the stop

Keep the open-gaps section unsoftened. A report that reads as a victory lap is
worth less than one that tells the user exactly where the artifact is still weak.
