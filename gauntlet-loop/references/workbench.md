# The workbench

A long unattended run needs a surface the user can glance at without interrupting
it. Interrupting to ask for status costs a context switch on both sides and is the
main reason people stop letting loops run long enough to work.

## The board is generated, not written

```bash
python3 scripts/gauntlet.py board     # writes gauntlet/workbench.md from the log
```

`board` renders `gauntlet/workbench.md` from `rounds.jsonl` and `config.json`:
wave and budget, cost so far, target score, the WIP limit, which lanes the next
wave funds, then three columns — **Active** (with a park flag where `status`
recommends one), **Parked** with each open gap and the reason it stopped, and
**Retired** — plus the last twelve rounds.

Regenerate it at every wave boundary and after every park or extension. It is
deterministic, so keeping the user's progress surface current costs zero model
tokens — which is the point. **Never hand-write or hand-edit the workbench**: a
board written from memory drifts from the log, and the log is what the report and
the stop conditions are computed from.

If the user wants it in a browser, `workbench.md` renders anywhere markdown does
and can be opened directly. Do not build a bespoke HTML surface for a run — that
is a whole artifact's worth of tokens spent on a status page.

## Language rules (ASD-STE100)

All visible text you add around the board — gap wording, park reasons, report
prose — is Simplified Technical English: active voice, one statement per
sentence, 20–25 words maximum, and no marketing language ("amazing", "leverage",
"streamline", "delve"). Short and literal also happens to be cheap.

## What the user reads it for

- What the run has cost against what they agreed to — including any granted
  extensions (`wave 9 of 11: initial 8, extended +3`)
- Which lanes are still being funded, and which stopped and why
- **Evidence over time** — the artifact evolving, in whatever form it takes:
  screenshots, rendered pages, drafts, benchmark numbers, test output. The board
  links the latest evidence path per lane; keep those paths stable so a user can
  flip through them.
- Reverts, visibly — a run that reverts often looks different from one that does not

## Round log schema

`gauntlet/rounds.jsonl` is append-only and written **only** through
`gauntlet.py log-round` — the validation (no gap without severity, no gap without
the target that closes it, losers get reverted, evidence always) is the point. The workbench renders from it and the
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
  "closed_when": "a contact shadow at the rock/ground seam, as in bar/ref-cliff.png",
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

Records may also carry these optional fields, each set by its `log-round` flag:
`"calls": N` and `"tokens": N` (real cost — unmeasured rounds fall back to the
estimate, and `status` reports partial measurement as a floor), `"tier":
"screening"` (steers rounds, never advances retirement), `"blind": true`
(champion mode: the promotion ran under the blind protocol), `"diff_lines": N`
(feeds the softening tripwire), and `"critic_model": "<id>"` (the report prints
the distribution).

## Reading the log

`gauntlet.py status` computes streaks, retirement, stalls, revert rates, cost per
closed gap, the next-wave plan and fired stop conditions from the log — run it at
every wave boundary instead of counting in your head. Beyond what it prints,
three patterns to watch:

**Margins narrowing** across rounds in a lane — approaching the ceiling. Expected
and healthy.

**Revert rate rising** — challengers losing more than winning. The lane has run
out of closeable gaps, or the lane is cut wrong.

**The same gap recurring** across rounds after being marked closed — either the
builder is not actually closing it, or it is structural and no amount of lane-level
work will fix it. Re-cut or park rather than running the same round again;
`status` parks it for you after three identical gaps.

## Reporting at the end

`gauntlet.py report` drafts the report from the log; you complete the judgement
fields. It must cover:

- Target bar used, whether it was raised mid-run, and the distance to any stretch
- Lanes, rounds each, and how each ended — retired, parked, or still open
- The gaps that closed, and what they cost (calls per closed gap)
- **The gaps still open** — the section the user actually needs
- For each parked lane, what would have to change for it to be worth restarting.
  "More waves" is not an answer.
- Blind versus rubric round counts
- Any budget extensions, with the reason each was granted and whether it paid off
- Whether the loop was still improving at the stop

Keep the open-gaps section unsoftened. A report that reads as a victory lap is
worth less than one that tells the user exactly where the artifact is still weak.
