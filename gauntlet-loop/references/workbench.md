# The workbench

A long unattended run needs a surface the user can glance at without interrupting
it. Interrupting to ask for status costs a context switch on both sides and is the
main reason people stop letting loops run long enough to work.

## The Live Kanban Workbench

The workbench is an HTML file (`gauntlet/workbench.html`) that serves as a live Progress Board (Kanban).
During Phase 0, the lead agent copies a provided HTML template to this location and opens it in the user's browser.

**CRITICAL RULE:** You and all sub-agents MUST ONLY edit the `#gauntlet-state` JSON block inside this HTML file. You must NEVER generate, modify, or rewrite the HTML structure itself.

## Language Rules (ASD-STE100)

All visible text on the Kanban board (goals, gaps, next fixes) must be written in Simplified Technical English:
1. Maximum sentence length: 20-25 words.
2. Use active voice always.
3. One instruction or statement per sentence.
4. ZERO AI marketing language (no "amazing", "leverage", "streamline", "delve").
5. Be direct and objective.

## What it needs

- Current wave, active lanes, elapsed time and budget consumed
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
  "critic_framing": "domain-specialist"
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

## Reporting at the end

`gauntlet.py report` drafts the report from the log; you complete the judgement
fields. It must cover:

- Bar used, and whether it was raised mid-run
- Lanes, rounds each, and how each retired
- The gaps that closed
- **The gaps still open** — the section the user actually needs
- Blind versus rubric round counts
- Whether the loop was still improving at the stop

Keep the open-gaps section unsoftened. A report that reads as a victory lap is
worth less than one that tells the user exactly where the artifact is still weak.
