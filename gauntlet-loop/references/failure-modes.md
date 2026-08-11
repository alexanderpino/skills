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

## Premature scale-up

**Signal.** Wave 1 opens every lane at full effort on the strongest models, before
a single verdict exists. The run looks impressively busy by lunchtime.

**Cause.** Treating the lane cut as a commitment rather than a hypothesis, and
effort as a setting rather than a purchase.

**Repair.** The effort ladder (`cost-model.md`). Start at tier 0: one lane, one
dimension, cheap models, one collapsed critic call. Escalate only through
`gauntlet.py escalate`, which checks four gates from the log and refuses when one
fails. The whole value of the shape is that a run which turns out to be
unpromising costs a fifth of the budget instead of all of it — and you only get
that if the first tier is genuinely small.

## Comfort-first probe

**Signal.** The probe passed easily, the pilot looked healthy — and the run's
real problem surfaced at tier 2 or 3: a foundational choice was wrong, an
unjudged dimension came back structurally broken, and lanes that built on top
of it are now rework. The ladder's receipts all say the escalations were
earned; the run still paid full price to learn what a probe could have said.

**Cause.** The POC proved the easy part. The probe lane was chosen for a quick
clean verdict (comfort), not for how much a verdict there would de-risk — and
nothing priced the never-judged dimensions before the campaign committed build
rounds across the full cut.

**Repair.** Two orderings, both already in the doctrine. The probe targets the
lane whose failure would invalidate the most — the tracer bullet through the
riskiest part, where a kill-verdict is cheapest (`decomposition.md`, "Order by
risk"). And before the campaign, a **survey** prices every never-judged
lane/dimension with one cheap bar verdict apiece — critics only, no builders —
so the first full `plan` ranks measured gaps. `plan` enforces the posture: a
never-judged pair outranks every known major until someone prices it, because
an unknown is a risk, not a zero.

## Unsatisfiable critic

**Signal.** No verdict ever reaches severity `none`. Streaks never build. Every
lane runs until the money is gone, and the report's stop reason is always
"budget". Score-wise, everything sits below whatever counts as a pass.

**Cause.** A critic calibrated so that only perfection passes — the mirror image
of sycophancy, and much easier to mistake for rigour. If the critic cannot ever
say "nothing meaningful remains", then `bar-met` and `clean-streak` cannot fire,
and budget depletion becomes the *only* way the run can end. The stop conditions
are still in the config; they have just been made unreachable.

**Repair.** A calibrated scale, not a pass mark (`critic.md`): 9 against a strong
bar is an excellent result, not a failure. `none` is a legitimate and expected
verdict, and its evidence requirement — not its rarity — is what keeps it honest.
Diagnostic: if a run ends on budget with every dimension still open and every
verdict still `minor`, read three verdicts in full before funding an extension.
The problem is probably the critic, and more waves will not fix it.

## Unmanaged fan-out

**Signal.** Every active lane gets a builder and its critics every wave,
regardless of what the log says. Parallel by default, including on lanes that
touch the same concern. The wave count is the only thing anyone decides.

**Cause.** Treating the loop as a schedule rather than as a thing to be managed.
The published method encourages exactly this — "tell it to keep looping" — and
supplies no scheduler, so the default is to run everything until something stops
it.

**Repair.** `gauntlet.py plan` before each wave: rank the open dimensions by gap
severity, hold what is flat or retired, cap with `--max-lanes`, and record what
you held. And prefer serial passes on coupled work — the canonical run's own
finding is that sequential single-owner passes beat parallel fan-out decisively
(`decomposition.md`), which makes the expensive default the worse one too.

## Convoy

**Signal.** Wave wall-clock is roughly the sum of every stage: builders idle
while critics judge, critics idle while builders build, everything idles while
the smoother runs. `status` shows elapsed time far above active time.

**Cause.** Reading "sequential single-owner passes" as "one thing happens at a
time". Ownership serialises writes; it says nothing about the clock.

**Repair.** Pipeline stages of independent work: dispatch the next lane's
builder while this lane's critics run; take oracle measurements and run `plan`
while the smoother works. And let the revert rate pick the judging strategy —
at a low rate, run the promotion and bar critics concurrently instead of paying
serial latency for a conditional that almost never fires. → `pace.md`

## Convergence tax

**Signal.** A dimension has been on `minor` for four rounds, each round closing
one cosmetic gap and surfacing the next. The verdicts are fine; the pace is not.

**Cause.** The one-gap-per-round discipline applied past the point where it pays.
Attribution matters while gaps are major; on a pile of cosmetics it costs a full
round of latency per item to protect information nobody needs.

**Repair.** A batch brief: fold the critic's second-order NOTES into one round
that closes the listed minors together. The champion guard is what makes this
safe — a batched round that regresses gets reverted like any other. `plan`
suggests it when a dimension sits on a minor. → `pace.md`

## Judging nothing

**Signal.** A verdict repeats the previous round almost verbatim. The gap text is
identical. Diffing the artifact across the round shows no change.

**Cause.** The builder produced nothing — it escalated, it failed silently, it
decided the gap was already closed — and the loop judged the unchanged artifact
anyway, because judging is what comes after building.

**Repair.** A free deterministic gate before any critic call: `git diff --quiet`
on the owned paths, a checksum, a pixel-diff of the render. No change means no
judgement — `skip --reason-code no-change`, then re-brief the builder with the
reason. The canonical run used the same shape at the other end, gating a final
pass on "zero visual change" with automated pixel-diffing.

## Build-and-hope

**Signal.** Rounds run, verdicts land, and nobody can say in advance what any of
them will show. Misses read as bad luck rather than as wrong ideas. The same
approach quietly gets tried twice. Asked "why did that round fail?", the honest
answer is "it just didn't work".

**Cause.** The loop measures everything *after* the fact and states nothing
*before* it. A round with no stated expectation cannot be wrong — and so cannot
teach. Verdicts say where the artifact is; only a prediction, scored, says
whether anyone understood why.

**Repair.** `gauntlet.py aim` before every builder from tier 1 up: hypothesis,
named approach, expected verdict — and the expectation must improve on the last
verdict, so nobody buys a hit rate by aiming at the floor (`aim.md`). Then read
the hit rate as what it is: the run's measure of whether it understands the
artifact. Under half, with three or more scored aims, more build rounds are more
guesses at the same wrong model — run one read-only **diagnosis round** whose
product is a cause, and never retry an approach from the failed ledger without a
new reason to believe it.

## Model reads a number

**Signal.** A critic call whose entire verdict restates a measurement the harness
already produced: "LCP is 2.1s against a 1.5s budget, so the bar wins."

**Cause.** Every dimension routed through the same model-critic pipeline,
including the ones with a numeric oracle.

**Repair.** `--mode oracle`. The measurement *is* the bar comparison: it costs no
critic tokens, feeds the streaks like any bar round, and is stronger evidence
than a model verdict because nothing was judged. Spend a model on that dimension
only to name the gap once the number stops moving.

## Top-tier default

**Signal.** Every role runs on the strongest available model. The spend-by-model
view is one bar. Nobody can say what the cheaper tiers would have cost, because
none of them ever ran.

**Cause.** Model choice treated as a quality setting with one correct value,
rather than as routing. It feels safe — nobody is ever blamed for using the best
model — and it is the single easiest way to multiply a run's bill by five while
changing almost nothing about the artifact.

**Repair.** Route by role (`cost-model.md`): generation quality is the artifact
and is worth paying for, classification usually is not. Then *check* the
assumption instead of asserting it — escalate specific `thin` verdicts with
`--escalated-from` and let `status` report how often the stronger critic actually
disagreed. Near-total agreement is the finding: the cheap critic was already
right, and the escalations bought confirmation. The inverse is a finding too, and
the same mechanism produces it.

**What this is not.** It is not licence to quietly move a running gauntlet onto a
cheaper model because it looks expensive. The roster is in the contract; if the
evidence says a tier is wrong, show the numbers and let the user decide.

## Cost blindness

**Signal.** The run is priced in waves and subagent calls. Nobody, including you,
can say what it has spent. The first accurate number anyone sees is the invoice.

**Cause.** Waves treated as a unit of money. A wave costs whatever its lanes,
dimensions and tier happen to cost — a 3-lane 2-dimension wave at full split is
five times a probe round, and that ratio is invisible in a wave count.

**Repair.** `--budget-tokens` at intake with `--cost-per-mtok`, `--tokens` on
every `log-round`, and `spend` for builders and the smoother. Then `status`
prints spend, burn rate, and the waves of budget remaining at that rate, and the
extension offer is priced in the user's currency from the run's own measured
calls. Also: quote the real call arithmetic — 1 builder + (critic calls ×
dimensions) — because dropping the dimension multiplier understates every
multi-dimension run at intake, which is where it does the most damage.

## Funding a stall

**Signal.** A lane stopped moving at wave 3 and was still being run at wave 12,
because nothing forced the question until the budget ran out.

**Cause.** The trend evidence existed in the log the whole time; it was only
*consulted* at depletion.

**Repair.** `status` reads the trend at every wave boundary and flags any
dimension flat for `flat_rounds_n` rounds, with the cost of running it again next
to it. Shelve it (`gauntlet.py shelve`) and reallocate to lanes with gaps left.
Shelved is parked, not retired: the report keeps the open gap, so this buys
honesty as well as money. And the shelf is a transfer, not a cut — when new
information arrives later (a diagnosis names the cause, a new asset lands),
`unshelve` brings the dimension back and the freed budget flows in again.

## Inspection rot

**Signal.** Critics stop citing specific evidence, or cite the same stale evidence
repeatedly.

**Cause.** The screenshot harness broke, the build stopped producing output, the
benchmark started failing silently — and nobody checked.

**Repair.** Verify the inspection path at every wave boundary, not just at intake.
A loop that cannot see the artifact is not measuring anything, and it will keep
producing confident verdicts anyway.

The board now catches the common half of this without anyone looking: `board`
checks every cited evidence path against the disk, draws a missing file as a
flagged tile in the lane's filmstrip, and raises a banner naming the paths. The
half it cannot catch is a harness that still writes files that no longer show
the artifact — which is what the filmstrip itself is for: five rounds of
identical thumbnails is the same signal as five rounds of identical verdicts,
visible at a glance rather than by reading the log.
