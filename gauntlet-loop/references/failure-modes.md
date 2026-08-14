# Failure modes

Every one of these produces a loop that looks like it is working. That is what
makes them expensive — the run keeps logging rounds while the artifact stops
improving, and nobody notices until the budget is gone.

Read this before a long unattended run.

## Critic sycophancy

**Signal.** Everything passes. Gaps get vaguer round over round: "lighting could be
warmer", "prose flows well", "could be slightly more polished". Verdicts stop
citing specific evidence.

**Cause.** The critic is optimising for a pleasant exchange instead of judgement,
or the bar is too soft to discriminate.

**Repair.** Force a winner with no tie option. The severity field is the
counter-pressure: `none` is a strong, evidence-backed claim, not a shrug — and
`log-round` rejects a major/minor verdict with no named gap outright. If gaps
stay vague after that, the bar is the problem, not the critic.

## Rubric gaming

**Signal.** Rounds pass consistently while the artifact stops visibly improving.
Builder output starts matching the critic's phrasing suspiciously closely.

**Cause.** The builder has learned the critic rather than the bar. This is the most
insidious mode because every metric looks healthy.

**Repair.** Rotate critic framing between waves (specialist / first-time user /
hostile reviewer). Re-randomise A/B labels every comparison. Never pass the
critic's exact wording forward as a build target — pass the *gap*, then have the
builder look at the bar itself.

## Bar erosion

**Signal.** Comparisons quietly get easier. Late-run wins are decisive where
mid-run wins were thin, with no corresponding jump in quality.

**Cause.** The bar is being carried in paraphrase across rounds and has softened
each time it was restated.

**Repair.** Bar files frozen at `gauntlet/bar/` and re-read from disk each wave.
Never restate the bar from memory into a subagent prompt — point at the path.

## Unreachable bar

**Signal.** Every round loses. Scores sit at 4 and never move. Every dimension
looks stalled at the same time, and the loop reads as failing when it is actually
working.

**Cause.** The target was set at an ideal rather than at "done", or
`target_score` was set to 10 so nothing can ever pass. A bar nobody can reach
stops discriminating: a near miss and a disaster both log as a loss.

**Repair.** Put the ambition in the stretch line, and set the target where the
run can plausibly land inside the budget (`bar-selection.md`). Do it before wave
1 — the feasibility check after first light exists for exactly this. Mid-run, a
target that is provably out of reach is a rescope conversation with the user, not
something to grind against.

## Zombie lane

**Signal.** The same lane keeps getting funded, round after round, with the same
gap named each time. Its score has not moved in four rounds. Everyone can see it
is stuck; nobody stops it, because stopping feels like giving up.

**Cause.** No prune rule, or a lead agent treating parking as failure. Sunk cost
does the rest: the more rounds a lane has consumed, the more it seems to deserve
one more.

**Repair.** The `no-progress` condition is mechanical for this reason —
`status` flags it, `extend` refuses to price an extension until it is parked, and
`park` records the reason. Park it, name which of the three causes it was
(structural, not-a-code-problem, cut wrong — `decomposition.md`), and give the
slot to the next lane. The open gap goes to the user, who can act on it in ways
the loop cannot.

## Gold plating

**Signal.** Rounds still running on a dimension that already retired. Builders
polishing past the target because the artifact "could be better".

**Cause.** Retirement treated as a suggestion, or a target bar nobody believes in
so the run keeps going by feel.

**Repair.** Retirement is a stop. If the artifact genuinely passed the bar with
budget left, that is a bar problem: raise it, announced and recorded, and let the
run continue against something real. Do not fund unjudged polish — no gap, no
builder.

## Re-litigation

**Signal.** Rounds spent on ground the run already covered: a retired dimension
judged again, a closed gap re-argued by a new critic, a whole-artifact review
"just to check" every few waves. The log grows; the artifact does not.

**Cause.** No notion of settled work. Each critic starts cold by design, so
without an explicit rule nothing stops one from re-opening a question the log
answered three waves ago — and a lead agent nervous about quality will invite it.

**Repair.** Settled is settled: a closed gap and a retired dimension are not
re-judged (`critic.md`), and `log-round` warns when a record lands on a retired
dimension. Regressions are caught *mechanically* rather than by re-review — the
champion/challenger comparison catches them within a dimension, and machine gates
re-run every wave catch them across dimensions. A critic that believes something
previously closed has broken reports it as a regression in NOTES, with evidence.

## Scope snowball

**Signal.** More lanes at wave 6 than at wave 1. Builders fixing adjacent things
they noticed. A projected call count that has quietly doubled since intake, with
no extension granted.

**Cause.** Every agent in the loop can see improvements outside its lane, and
each individual addition looks small and obviously worthwhile. Nothing in the
method stops the sum.

**Repair.** The scope is frozen at the contract (`decomposition.md`): re-cuts
redistribute, they never expand, and a new lane needs a slot freed by a
retirement or a park. Noticed work goes to `gauntlet/backlog.md` and into the
report, where the user can buy it deliberately in a future run. Compare the
current projection against the intake projection at each wave boundary — a rise
with no granted extension is the snowball, measured.

## Token burn

**Signal.** Cost per closed gap climbing wave over wave in `status`. Waves that
cost as much as the first ones and close nothing.

**Cause.** Critic calls doing work a command could do, two critic calls where one
inspection would answer both questions, artifacts pasted into prompts, six lanes
funded for one round each.

**Repair.** `cost-discipline.md`, in full. The two that matter most: machine
gates for anything measurable, and the WIP limit for everything else. And when
cost per gap keeps climbing while the open gaps get cosmetic, the honest response
is a stop, not a cheaper loop.

## Progress theatre

**Signal.** Rounds logged, gaps named, verdicts recorded — and diffing the artifact
across ten rounds shows almost nothing changed.

**Cause.** Builders reporting intent rather than doing work, or critics grading
descriptions instead of artifacts.

**Repair.** Per-round artifact evidence is mandatory in the log — the script
refuses records without it. Periodically `git diff` the current champion against
its ref from five rounds ago and confirm the change is real.

## Lane collision

**Signal.** Reverts undo work that belonged to another lane. Builders report
confusing conflicts. The smoother finds contradictory changes in one file.

**Cause.** Two lanes wrote the same file in one wave.

**Repair.** One file, one owner, per wave, in `gauntlet/ownership.md`. Builders
escalate rather than reaching across. Shared files belong to the smoother.

## Downhill drift

**Signal.** The artifact at wave 10 is worse than at wave 6, though every
individual round was judged a win.

**Cause.** Local improvements that are global regressions, accumulating. Common
when a single dimension of a multi-dimensional bar is being optimised — visual
quality climbing while frame time quietly triples.

**Repair.** Champion commits every round; revert losers rather than merging
them. Declare dimensions in `config.json` and judge each separately — a lane
retires only when all its dimensions do. Every few waves, run one whole-artifact
comparison against the wave-1 champion ref.

## Context bleed

**Signal.** Critic verdicts echo the builder's justifications. Phrases like "the
approach here is reasonable given the constraints" — that is builder language.

**Cause.** Builder rationale reached the critic, through a shared context, a
handoff document, or a summary passed forward by the lead agent.

**Repair.** Critics receive artifact, bar and rules. Nothing else. If a builder's
handoff must exist for the lead agent's benefit, it does not travel to the critic.

## Ceiling denial

**Signal.** The same gap reappears round after round. Margins stop narrowing.
Revert rate climbs past wins.

**Cause.** The remaining distance is structural — a foundational choice made early
that lane-level work cannot reach.

**Repair.** Recognise it rather than grinding — `status` flags a revert rate
over 50% in the recent window as exactly this signal, and the same signal parks
the dimension. Either re-cut the lanes to include the structural element, or park
and report it as an open gap with a recommendation. Burning budget on a ceiling
is the most common way a long run wastes money while looking busy.

## Budget creep

**Signal.** Extension after extension, each one "nearly there". The run is at
wave 26 of an agreed 8, and no single grant looked unreasonable at the time.

**Cause.** Extensions offered on optimism instead of on the log, or granted in
blocks too large to be re-decided. Sunk cost does the rest — every extension makes
the next one feel cheaper, on both sides of the conversation.

**Repair.** Extend in blocks of 2–4 waves, never open-endedly, so each grant is
decided on fresh evidence. Every grant carries a reason drawn from the log and is
recorded in `config.json` and the report — `extend` enforces both, refuses a grant
before the budget is actually depleted, and refuses an `at-ceiling` log read
without `--force`. For long unattended runs, agree a `hard_cap_waves` at intake:
the budget becomes the checkpoint, the cap the ceiling. And when the honest read
is "flat", say so — recommending a stop is the whole point of being the one who
can read the log.

## Inspection rot

**Signal.** Critics stop citing specific evidence, or cite the same stale evidence
repeatedly.

**Cause.** The screenshot harness broke, the build stopped producing output, the
benchmark started failing silently — and nobody checked.

**Repair.** Verify the inspection path at every wave boundary, not just at intake.
A loop that cannot see the artifact is not measuring anything, and it will keep
producing confident verdicts anyway.
