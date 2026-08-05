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
over 50% in the recent window as exactly this signal. Either re-cut the lanes to
include the structural element, or stop and report it as an open gap with a
recommendation. Burning budget on a ceiling is the most common way a long run
wastes money while looking busy.

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
