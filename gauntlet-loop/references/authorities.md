# Where this skill's rules come from

## What separates a gauntlet from a review

Four properties. A method missing any one of them is a review with extra steps,
and each is enforced somewhere concrete in the skill rather than merely believed:

1. **The bar is external and inspectable** — not "make it production-ready".
   Enforced by freezing bar files at intake and by critics that must cite what
   they inspected (`bar-selection.md`, the script's `--evidence` requirement).
2. **The bar is reachable.** The target is where done actually is; ambition above
   it is a *stretch* that never defines done. Enforced by `--target-score` and
   the warning at 10 (`bar-selection.md`).
3. **The builder never grades itself.** Justification is the enemy: a builder has
   seen every decision it made and is excellent at defending them. Enforced by
   separate critic agents in fresh context (`critic.md`, `blind-protocol.md`).
4. **Rounds are earned, not scheduled** — and withdrawn when a lane stops paying.
   Enforced by the `no-progress` stop and the park rule (`stop-conditions.md`).

The Gauntlet Loop is Matt Shumer's. Nearly everything wrapped around it —
budgets, kill criteria, the WIP limit, parking, the honest report — is
project-management practice with a literature behind it. This file names that
literature, so the rules can be argued with rather than merely obeyed.

Each entry is: who, what they established, and what it forces in this skill.

## Iteration and delivery

**W. Edwards Deming** — PDCA, and the warning to *cease dependence on inspection
to achieve quality* (`Out of the Crisis`, 1982). Inspection at the end is the
expensive way to get quality; you want the defect's cause fed back.
→ A gauntlet is a loop, not a final review: every critic verdict names a gap that
goes straight back to a builder. A run that inspects a lot and changes little is
in the "progress theatre" failure mode, not doing Deming's job.

**Barry Boehm** — the spiral model (1986): each cycle attacks the *highest risk*
first, and the cost of changing a decision rises the later you change it.
→ Lanes are ranked and the riskiest, highest-value one is funded first
(`decomposition.md`), and the feasibility check happens before wave 1 rather than
at wave 8, when rescoping is cheapest.

**Eric Ries** — `The Lean Startup` (2011): build-measure-learn, validated
learning, and *pivot or persevere* as an explicit scheduled decision.
→ The wave-boundary review is the persevere-or-pivot moment, and the extension
offer is that decision priced. The point is that it is a *decision made on
evidence at a boundary*, not a drift.

**Frank Robinson** coined *minimum viable product*; **Eric Ries** popularised it;
**Marty Cagan** (SVPG) spent a decade arguing the industry got it wrong — an MVP
is a prototype for learning, not a small shippable product, and real work has to
answer four risks: value, usability, feasibility, business viability.
→ Two consequences. A gauntlet answers the *quality* question only; it does not
tell you whether anyone wants the thing. And the target bar is a definition of
done, not a shrunken product.

**Alistair Cockburn** — the **walking skeleton**: a tiny end-to-end
implementation that exercises the real path, built first, then thickened.
**Andy Hunt and Dave Thomas** — **tracer bullets** (`The Pragmatic Programmer`,
1999): fire something that goes all the way to the target and shows you where it
lands, in the dark, before committing to the full build.
→ Phase 0, first light. The first thing the loop produces is thin, whole and
*visible*, and it doubles as the inspection-path test. It is also why the
bootstrap wave builds a slice rather than one polished part, and why the contract
is negotiated against a real artifact instead of an adjective.

**Henrik Kniberg** — "Making sense of MVP" (2016): the skateboard→bike→car
drawing, and the earliest **testable → usable → lovable** ladder. (The term
*Minimum Lovable Product* is usually credited to Brian de Haaff.)
→ This is the answer to "should the loop generate a POC, then an MVP, then an
MLP?" — see `bar-selection.md`. The ladder sets *where the target bar sits*; it
is not extra machinery. And the bootstrap wave builds the thin end-to-end slice
(skateboard), because lanes cannot be judged independently until the whole thing
exists to judge.

## Flow, queues and limits

**Donald Reinertsen** — `The Principles of Product Development Flow` (2009): an
economic framework for every decision, queueing theory applied to development,
small batches, and WIP constraints. His central move is insisting that decisions
be made in one currency rather than in proxy metrics.
→ The budget in waves, the projected call count, and cost-per-closed-gap exist so
that every decision in this skill is priced. The WIP limit is his constraint,
applied to lanes.

**David J. Anderson** — `Kanban` (2010): explicit WIP limits, explicit policies,
visualised flow. The practitioner slogan is *stop starting, start finishing*.
→ `wip_limit`, the ranked queue behind it, and the generated board. Depth over
breadth is the WIP limit doing its job.

**Eliyahu Goldratt** — Theory of Constraints (`The Goal`, 1984): improvement
anywhere but the bottleneck is an illusion.
→ Rank lanes by what actually carries the goal's quality, and re-rank when a lane
retires. Polishing a retired dimension is improving a non-constraint.

## Stopping, killing, and not fooling yourself

**Barry Staw** — escalation of commitment, "Knee-Deep in the Big Muddy" (1976):
people fund failing courses of action *more* the more they have already sunk.
→ The park rule is mechanical for exactly this reason. `status` flags the stall,
`extend` refuses to price around it, and resuming a parked lane demands new
evidence rather than optimism.

**Robert G. Cooper** — Stage-Gate: gates that carry a real *kill* option, with
success criteria agreed before the gate rather than at it.
→ Kill criteria in the intake contract (`stop-conditions.md`), checked at each
wave boundary. Agreeing them costs a line at intake and settles the argument that
would otherwise happen at wave 9 with everyone invested.

**Gary Klein** — the premortem (HBR, 2007): imagine the failure, then work
backwards to its causes.
→ `failure-modes.md` is a premortem written down once so every run inherits it.

**Annie Duke** — `Quit` (2022): kill criteria work when they are *states and
dates* set in advance; quitting on time feels like quitting early. She also
popularises **Astro Teller's** "monkeys and pedestals" from X — build the monkey
first, because the pedestal is the part you know you can do.
→ Kill criteria are written as observable states with a wave number. And round
zero attacks the lane most likely to be impossible, not the one most likely to
produce a quick win.

**Daniel Kahneman and Dan Lovallo** on the planning fallacy and the inside view;
**Bent Flyvbjerg** on reference-class forecasting — estimate from what comparable
past efforts actually cost, not from this plan's internals.
→ The feasibility check after first light is a reference-class estimate: rounds it
took to close the *first real gap*, times lanes, over WIP. A bar set from
ambition rather than from a measured first round is the inside view with better
adjectives.

## Allocating a fixed budget over uncertain options

**Successive halving and Hyperband** (Karnin et al. 2013; Jamieson & Talwalkar
2016; Li et al. 2017): with a fixed budget and several options of unknown value,
give every option a small amount, cut the worst, and reallocate to the survivors.
Repeat. This beats splitting the budget evenly, and it beats committing early.
→ This is the exact shape of a gauntlet's wave loop: first light is the small
initial allocation, the wave-boundary review is the cut, and parking plus
reallocation is the halving. The formal result is why the prune is not
pessimism — it is how a fixed budget finds the good option at all.

**Cost of delay / WSJF** (Reinertsen; adopted by SAFe): rank by value over
duration rather than by value alone.
→ The lane ranking formula in `decomposition.md`.

## Agents, prompting, and LLM judges

This section carries more weight than the rest, because a gauntlet's critic *is*
an LLM judge and the known failure modes of LLM judges are the method's `lasten`.
Every guardrail below buys off a measured effect, not a worry.

**Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet"
(2023)** — models asked to revise their own output *without external feedback*
frequently make it worse, not better; the apparent gains in earlier self-critique
results came from oracle labels leaking in.
→ This is the empirical backing for the skill's first non-negotiable. "No builder
grades its own homework" is not decorum about objectivity; self-grading is a
measured *regression* risk. It is also why the bar must be external and
inspectable rather than a rubric the builder can reason about, and why the
critic gets the artifact and the bar and nothing else.

**Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
(2023)** — LLM judges carry three measured biases: **position bias** (the same
pair scores differently when swapped), **verbosity bias** (longer answers score
higher at equal quality), and **self-enhancement bias** (a judge prefers text
from its own family). Their mitigation for position bias is to swap and re-judge.
→ Three rules come straight out of this. Randomised A/B labels every comparison
answer position bias. Capping the builder's handoff to five lines and forbidding
self-assessment answers verbosity bias — an uncapped handoff is a lever the
builder can pull on the judge without improving the artifact. Blinding, and
routing the deciding critic to a tier that can actually judge rather than the
cheapest one, answer self-enhancement.

**Madaan et al., "Self-Refine" (2023)** — iterative refinement pays when the
feedback is *specific and actionable*, and the gains taper across iterations.
→ Both halves are enforced. "Name the gap or the round didn't happen" is a hard
rejection in `log-round`, because vague feedback is a round that buys nothing.
The tapering is why `no-progress` parks a lane rather than funding one more push:
the method's own literature says the curve flattens, so flattening is a signal to
reallocate, not to try harder.

**Anthropic, "Effective context engineering for AI agents"** — treat the context
window as a finite, degrading resource; give an agent the smallest set of
high-signal tokens that lets it act, not everything that might be relevant.
→ "Paths, not payloads" is this rule. So is reading each reference at its phase
instead of at intake, and capping every handoff. It is also the honest limit on
this method: each subagent's cold re-read is simultaneously the source of its
independence and the largest single cost in the run.

**Anthropic, "Building effective agents"** — the *evaluator-optimizer* pattern: a
generator and a separate evaluator in a loop, used when there are clear
evaluation criteria and iteration measurably helps. Plus the standing advice to
start with the simplest thing that works and add structure only when it earns
its place.
→ This method *is* an evaluator-optimizer with two additions: the evaluator is
blind, and the evaluation is against an external artifact rather than a rubric
the generator can read. The "simplest thing" advice is why "When not to use this"
sends correctness work to a debug loop and small edits to a plain edit.

**Matt Shumer** — the Gauntlet Loop itself (27 July 2026), the technique behind
the "Claude of Duty" run: decompose, build, judge blind against a real bar,
repeat on the named gap.
→ Everything above is scaffolding around that core. Credit it accordingly.

## How to argue with this file

Two tests before adopting a rule from any of these sources:

1. **Does it survive the agent setting?** Human-team practices often assume
   coordination costs and morale effects that do not apply to subagents — and
   ignore token costs that dominate here. Reinertsen's queueing carries over
   cleanly; a stand-up does not.
2. **Does it change a decision?** A principle that never changes what the run
   funds, parks, or reports is decoration. Every entry above maps to a rule that
   fires.
