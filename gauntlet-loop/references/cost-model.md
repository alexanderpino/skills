# The cost model

A gauntlet is the most expensive shape of agent work there is: it deliberately
spends compute to buy quality it cannot otherwise reach. That is fine, and it is
exactly why the spend has to be *steered*. This file is the steering.

Three ideas, in order of how much money they save:

1. **Buy effort in tiers.** Start at the cheapest tier that can produce a verdict.
   Escalate only when the log says the artifact is worth more.
2. **Price the run in the unit the user pays in.** Waves are not money.
3. **Stop paying for the parts that stopped moving**, at the wave they stop
   moving — not when the budget is gone.

## 1. The effort ladder

The real world does not fund a factory to find out whether an idea works; it
funds a prototype. A gauntlet works the same way. Effort per round rises in
steps, and each step is bought with evidence from the previous one.

| Tier | Name | Scope | Builder | Critic | Critic calls / lane / round | Share of budget |
|---|---|---|---|---|---|---|
| 0 | probe | 1 lane, 1 dimension, 1 round | mid | cheap | 1 (collapsed) | 5% |
| 1 | pilot | ≤2 lanes, 1 wave, all dimensions | mid | cheap | 1 (screening) | 15% |
| 2 | campaign | all lanes, full waves | high | mid | 2 (split, escalate on `thin`) | 40% |
| 3 | polish | only lanes still moving | high | high | 2 (full split) | 40% |

Shares are cumulative — an underspent probe hands its remainder up the ladder
rather than losing it. The arithmetic that matters: a run that turns out to be
unpromising dies at tier 0 or 1 having spent **a fifth** of the budget. Under a
flat model it spends all of it and reports the same conclusion.

`gauntlet.py tier` prints the current tier, its allowance, what it has spent, and
whether the next tier is earned. `gauntlet.py escalate --reason "..."` moves up.

### The four gates

`escalate` refuses unless all four hold, each computed from the log:

- **Rounds at this tier.** At least one bar round logged at the current tier.
  You cannot escalate out of a tier you never ran.
- **The bar discriminates.** At least one verdict named something specific, or an
  evidence-backed `none`. A vague tier means a soft bar, and a bigger budget
  makes a soft bar no sharper — it just buys more vague verdicts.
- **Inspection is live.** Evidence varies across rounds. Every round citing the
  same file is the signature of a harness that broke and nobody noticed.
- **The artifact is moving.** At tier 0 that means the probe produced an
  actionable verdict — the probe proves the loop can *see and judge*, not that
  the artifact climbed. From tier 1 it means the log read is not `at-ceiling`.

A failing gate is not an obstacle to route around. It is the mechanism telling
you that more money buys a bigger version of the problem you already have. Fix
it at the current tier's price, or stop. `--force` exists for the case where the
user was shown the failing gates and chose to fund it anyway; the report records
that they did.

### Descending the ladder

There is no `de-escalate` command, because the cheaper move already exists:
shelve the dimensions that stalled and let the tier apply to fewer lanes. Tier 3
on one surviving lane is cheaper than tier 2 on four.

## 2. Model tiering

Roles do not need the same model, and running them all at the top is the second
largest line in a gauntlet's bill.

| Role | Tier | Why |
|---|---|---|
| Builder | high from tier 2 | Generation quality is the artifact. This is where the money should go. |
| Bar critic | cheap → mid | Inspect, compare, classify: winner, margin, severity, one named gap. A structured judgement against a frozen reference, not open-ended reasoning. |
| Promotion critic | cheap → mid | Strictly easier — two versions of the same thing, one question. |
| Smoother | mid | Finds seams; it is explicitly forbidden from redesigning. |
| Escalated critic | high | Only when a cheaper critic returned `thin` and the round decides a retirement. |

The escalation rule for critics is worth stating on its own: **run the cheap
critic first, and buy the expensive one only for the verdicts that matter.** A
`decisive` verdict from a cheap critic is as good as a `decisive` verdict from an
expensive one. A `thin` verdict that will retire a lane is worth re-running at a
higher tier.

If verdicts from a cheap critic are systematically vaguer than the bar deserves,
that is a real finding — raise the critic tier for that dimension and note it in
the contract. Do not conclude it from one round.

## 3. Context discipline

Cost per call is set by what you put in the call. A builder that re-explores the
repository every round costs more than the rest of the wave.

**Pass paths, not contents.** The contract, the bar, the ownership ledger and the
current artifact are all files. A subagent reads what it needs. Pasting them into
the prompt pays for them again on every round, and paraphrase drift on top.

**Give every subagent a read budget.** State it: "read at most these paths; if
you need more, stop and say so." An escalation is cheap; a silent repo-wide
sweep is not.

**No repo-wide search in a lane.** The lane's files are in `ownership.md`. A
builder that greps the whole tree is a lane cut too vaguely — fix the cut.

**The critic gets the artifact, the bar, and nothing else.** This was already the
rule for independence (`critic.md`). It is also the cheapest possible critic
prompt, which is a pleasant coincidence and not the reason for it.

**Never hand a subagent the round log.** `status` exists so the lead agent reads
the history once, not so every subagent reads it every round.

## 4. Pricing the run honestly

Calls per lane per round = **1 builder + (critic calls × dimensions)**.

At tier 3 with 2 dimensions that is 5, not 3. The flat "3 calls per round" that
this skill used to quote undercounted every multi-dimension run — which is
exactly the kind of error that turns a budget the user agreed to into one they
did not. `gauntlet.py` now computes it from the tier and the declared dimensions.

A wave costs `lanes × calls-per-lane-round + 1` (the smoother).

### Measure, do not estimate

After round zero the run knows its own price. Use it:

```bash
python3 scripts/gauntlet.py log-round ... --tokens 120000   # what the critic call cost
python3 scripts/gauntlet.py spend --tokens 300000 --role builder --note "probe builder on typography"
python3 scripts/gauntlet.py status      # spend, burn rate, waves of budget left
```

`status` then prints the burn rate per wave and how many waves of budget remain
at that rate, and both the extension offer and `extend` price the next block from
this run's own measured calls rather than from a table. Set
`--cost-per-mtok` at init and every one of those numbers prints in euros.

Round zero is the calibration gate: **run it, price it, extrapolate, and put the
projected total in front of the user before wave 1.** One round of real data
beats any estimate, and it costs one round.

## 5. Stop paying for stalled work

A dimension that has not moved in `flat_rounds_n` bar rounds (default 3) is
flagged `FLAT` by `status`, at the wave boundary, with the cost of running it
again printed next to it. Shelve it:

```bash
python3 scripts/gauntlet.py shelve --lane imagery --dimension perf \
    --reason "flat 3 rounds, revert rate 60%; remaining distance is source-asset quality"
```

Shelved is **parked, not retired**: the dimension stops consuming calls from the
next wave, and the report still carries its open gap. `shelve` refuses a
dimension the log does not call flat, because shelving a moving dimension throws
away the gains it was about to make.

This is the single change that most directly addresses the classic failure: a
lane stalls at wave 3 and keeps costing a builder plus two critics every wave
until wave 12. The evidence was in the log from wave 3. Now it is on the screen
at wave 3.

## What this does not do

None of this makes a gauntlet cheap. It makes it *proportionate*: cheap while the
idea is unproven, expensive only where the log says expense is buying something,
and priced throughout in the unit the user is actually spending.
