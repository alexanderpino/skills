# Intake

The contract exists because an unattended loop cannot ask permission later. Every
field here is something that becomes expensive or impossible to change once the
loop is running.

## How to run intake without interrogating anyone

Most of the contract you can propose. Only two things genuinely require the user:
**the stop conditions** and **the budget** — they encode how much of the user's
time and money this run may spend, and you cannot infer that.

So: infer or propose the rest, present the whole contract as a block, ask them to
confirm or correct it. One exchange, not seven questions.

If the user has given a bar already, say so and move on. If they have not, propose
one with a one-line justification and let them override it.

## The contract block

```
GOAL     <destination, one sentence — not an implementation plan>
BAR      <the concrete comparator, and where its files live>
INSPECT  <how a critic reaches the real output each round>
LANES    <your proposed initial split, or "to be cut after first look">
STOP     <which conditions are armed, with thresholds>
BUDGET   <waves / wall clock / tokens — always set>
AUTONOMY <unattended until stop | check in between waves>
BENCH    <where progress is visible>
```

## Field notes

**Goal.** Watch for users handing you an implementation plan and calling it a goal.
"Build the renderer with a deferred path and clustered lights" is a route. "Make
the lighting hold up against these three reference frames" is a destination. If
they insist on the route, take it — but note that you are giving up the model's
judgement about approach, which is where a lot of the method's value sits.

**Bar.** See `bar-selection.md`. Freeze the artifacts under `gauntlet/bar/` now,
before any lane runs.

**Inspection.** This is the field that silently kills runs. Before wave one,
verify a critic can actually reach the output: the screenshot harness works, the
build runs, the benchmark produces numbers, the document renders. A loop where
critics grade descriptions is not a gauntlet, it is a conversation.

**Stop.** Ask explicitly. See `stop-conditions.md`. Users routinely want several
armed at once and that is correct — first to fire wins.

**Budget.** Always armed even when other conditions are. It is the backstop that
makes unattended running safe to agree to. Give the user a scale to react to:
each round is one builder call plus up to two critic calls; multiply by lanes per
wave, add one smoother call per wave. State the projected total in the contract
block ("8 waves ≈ 40–60 subagent invocations") so "budget: 8 waves" is a number
they can actually evaluate. Parallel lanes raise the burn rate, not the total.

**Autonomy.** If the user wants check-ins, the natural boundary is the end of a
wave, after smoothing — the artifact is coherent there and a decision is cheap.
Mid-lane check-ins fragment the loop for no benefit.

## Cold start

When the artifact does not exist yet — the canonical from-scratch gauntlet —
"current artifact" in the contract is simply *empty*, and wave 1 is a bootstrap
wave: builders produce first versions, there is no champion to compare against,
and the first bar comparison runs as soon as there is output to inspect. Do not
manufacture a fake baseline to compare the first round against; the bar itself is
the comparison from round 1.

## Before wave one

Run a **round zero** on a single lane: one build, one critic, one verdict. It costs
almost nothing and it surfaces the two failures that would otherwise waste hours —
a broken inspection path, and a bar the critic cannot actually compare against.

If round zero produces a vague verdict, the bar is too soft. Fix it before scaling
up to a full wave.

## Recording it

Initialise the state directory as part of confirming the contract:

```bash
python3 scripts/gauntlet.py init --lanes <a,b,c> --dimensions <d1,d2> \
    --bar-met-n 2 --clean-streak-n 2 --budget-waves <N>
```


Write the confirmed contract to `gauntlet/contract.md`. Every subagent that needs
the goal, bar or rules reads it from there rather than from a paraphrase in a
prompt — paraphrase drift across a long run is real and compounds.
