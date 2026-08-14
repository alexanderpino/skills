# Gauntlet contract — the gauntlet-loop skill, on itself

```
GOAL     The gauntlet-loop skill reaches 9/10 on cost, first-show and speed
BAR KIND acceptance criteria — measurable, one per dimension
TARGET   score 9 on each of three lanes, where 9 means:
         tokens      no 100 contiguous words in SKILL.md could move to a
                     reference without losing an actionable rule
         first-show  1 step, 0 blocking confirmations, zero ambiguity about
                     what gates what; two agents would produce the same shape
         speed       ≤2 barriers per wave, concurrency executable without
                     inventing anything, dependent lanes handled, no contradictions
STRETCH  none set — 9 is the target and the run stops there
INSPECT  a fresh critic subagent reads SKILL.md in full and any reference it
         needs to verify a claim; `wc -lw SKILL.md` is a machine gate run inline
LANES    1 tokens  2 first-show  3 speed        WIP 3 (all funded)
STOP     bar-met 2, clean-streak 2, no-progress 2, budget 3 waves
KILL     any dimension still ≤7 after wave 2 → stop and report the ceiling
BUDGET   3 waves ≈ 21 subagent calls projected; actual is lower, see deviation
AUTONOMY unattended to a stop
BENCH    gauntlet/workbench.md
```

## Declared deviations from the method

Both are recorded here rather than hidden, per the skill's own honesty rules.

1. **Lead-as-builder.** The lead agent builds; it does not spawn builder
   subagents. The artifact is prose the lead wrote, and a builder subagent would
   have to ingest ~3,700 words plus references to make edits the lead can make
   directly. The non-negotiable that matters — *the builder never grades its own
   homework* — is preserved in full: every verdict comes from a separate agent in
   fresh context that receives the artifact and the bar, never the lead's
   reasoning. Actual cost is ~1 critic call per wave, not the projected 7.

2. **Blinding is not possible.** There is one artifact and its git history is
   readable, so the critic knows which side is "ours". The run is therefore
   logged `--mode rubric`, not `--mode blind`: the critic scores against
   enumerated acceptance criteria rather than picking a winner between two
   unlabelled candidates. Rubric rounds are weaker evidence than blind rounds and
   the report says so.

## First light (Phase 0 — not logged, predates init)

The artifact already existed, so first light captured it rather than building it:
`wc -lw SKILL.md` → 424 lines / 3,679 words, and one critic verdict against the
candidate bar.

An earlier critic pass on the previous champion returned **7 / 7 / 6** with six
defects, two of them correctness bugs in the concurrency advice (concurrent lanes
racing the git index; unguarded concurrent appends to `rounds.jsonl`). All six
were closed before this run opened. This run's first light re-judges the result
of those fixes, which had never themselves been judged — the previous round ended
on an unjudged build, which is what made a real run necessary.

Feasibility, from the first-light verdict:

> the named gaps read `minor` with concrete fixes ≈ 1 round each × 3 lanes ÷ WIP 3
> ≈ 1–2 waves. Fits inside 3. No rescope.

## Amendment, wave 2 — raised by the user, recorded not absorbed

The user observed that all three lanes push toward *cheaper and faster*, so
nothing in the bar guards the method's power, and that parts of the real loop are
uncontrolled token burners. Both are correct, and the first is the failure mode
this skill names itself: a dimension nobody is watching gets traded away.

Handled without growing the lane set, per the frozen-scope rule:

- **Fidelity is a machine gate, not a fourth lane.** Every core mechanism is
  checked for reachability at the phase where it is needed, by grep, at no
  subagent cost. Wave-2 result: `randomis`, `external`, `one file one owner`,
  `revert`, `severity`, `evidence` all dropped from SKILL.md but every one is
  present in the reference cited at its phase. Compression was relocation, not
  erosion.
- **Token burn became a governor in the tooling**, which is where a control
  belongs rather than in prose: `--budget-tokens` at init, `--tokens` per round,
  and `status` now reporting the unit that actually burns plus tokens per closed
  gap. Measured this run: ~65k–83k tokens per critic call. `init` had projected
  "~21 subagent calls" for this 3-wave budget — roughly 1.4M tokens, a number the
  user was never shown and therefore could not consent to.

Uncontrolled burners found and not yet fixed, on the backlog: a critic's
inspection scope is unbounded by the method (my own prompts capped it ad hoc);
every subagent re-reads the artifact cold, which is the source of its
independence and also of its cost.

## Amendment, wave 3 — the mantra

The user set the skill's mantra: **work smarter, not harder.**

This is not decoration and it changes the acceptance criteria. It names the
method's own natural drift: a gauntlet loop's failure mode is to work *harder* —
more rounds, more thorough re-checking, more coverage — all of which feel like
rigour and are only cost. Read that way, nearly every guardrail in the skill is
a stop-working-harder rule:

| Rule | What it stops you doing harder |
|---|---|
| machine gates before critics | using judgement where a command decides |
| one critic call per round | paying for the same inspection twice |
| hash-cached `gate` | re-deriving a check whose inputs never moved |
| settled work is not re-judged | re-opening ground already covered |
| `no-progress` park | pushing a lane that stopped paying |
| WIP limit | spreading thin instead of finishing |
| target score 7, not 10 | chasing a perfection nobody asked for |
| first light before the contract | debating in the abstract before building |
| frozen scope + backlog | absorbing every good idea into this run |

Two consequences for the bar, effective from wave 3:

1. The guardrail test sharpens from "does it name a weakness" to **"does it make
   the loop smarter, or only busier?"** A guardrail that adds work without
   removing more work elsewhere fails, even if it names a real weakness.
2. The mantra goes at the top of SKILL.md as the organising principle, not as a
   slogan — it has to be the sentence an agent can decide with.

Applied to this very moment, as evidence it is operative: a critic is mid-read on
SKILL.md. Editing now would cost that verdict and force a re-run. The amendment
is recorded here instead, and the edit lands with the wave-3 fixes in one build —
one cycle instead of two.
