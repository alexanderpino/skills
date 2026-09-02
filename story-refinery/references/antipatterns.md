# Refinement smells

Read this when the output feels thin, or before handing over. Each smell has a
mechanical tell so you can catch it in your own work.

## Content smells

**House rules that only look enforced.** The team skill states a cap, a
convention or a DoD in prose and the config never got it. *Tell:* `TLR002`, or a
tailoring rule applied with `mechanism: prompt` that is plainly a number. *Fix:*
`references/tailoring.md` - anything mechanical lives in `refinery.yaml` or it
does not exist.

**The silent override.** A gate the team switched off, and a handover that reads
as though everything ran. *Tell:* `TLR005`. *Fix:* one sentence. Skipping a gate
deliberately is fine; a reader who cannot tell is being misled.

**Refining past the label.** The description was refined and the ticket's own
metadata ignored: a `production-issue` planned as a feature, a `sev1`
decomposed into a sprint. *Tell:* `TRI001`, `TRI002`, or a `tracker_meta` block
that nobody filled in. *Fix:* `references/triage.md` - the labels are newer
information than the description, and usually truer.

**Refining on fumes.** Evidence gathered and subtasks written for an item whose
intake verdict was never `sufficient`. *Tell:* `INT003`, or an intake block whose
`present` dimensions still say `heuristic: true`. *Fix:* go back to the
questions. A plan built on a missing trigger is a plan for the wrong entry point.

**Restating the ticket.** The refinement says what the ticket already said, in
more words. *Tell:* the technical notes contain no path, no decision, no number.
*Fix:* Phase 2 was skipped. Go read the code.

**Confident fiction.** Paths, class names or line numbers that sound right.
*Tell:* a citation you cannot re-open. *Fix:* delete every uncited claim, then
verify the rest by reading. This is the most damaging failure in the whole
skill, because downstream everyone trusts it.

**Zero questions.** Every gap was quietly resolved by assumption. *Tell:*
`open_questions` is empty on a non-trivial story. *Fix:* re-read the AC and ask
what a tester would ask about boundaries, failure, and concurrency.

**Prose combinatorics.** A rule with "and", "unless" and "except" in one
sentence, so nobody can say how many cases it has. *Tell:* `AC008`, or examples
that all pass through the same code path. *Fix:* it is a decision table - see
`references/example-design.md`, which also covers partitions and boundaries.

**Risks nobody would notice.** Mitigations recorded, detection blank. *Tell:*
`RSK002`, or `story.risks` empty on a multi-repo change (`RSK003`). *Fix:* run
the premortem in `references/risk-and-options.md`; a mitigation says you thought
about it, a detection says you would find out.

**The eternal option.** A decision parked as deferred with nothing that would
decide it and no point at which it stops being deferrable. *Tell:* `DEC007` /
`DEC008`. *Fix:* an option without an expiry is not held, it is unmade - and the
first implementer to touch that code makes it silently.

**Planning the unknowable.** Seven confident subtasks for a story whose mechanism
nobody has tested. *Tell:* `CYN001`, or acceptance criteria you cannot write
without guessing at what will work. *Fix:* the output is a probe with a
hypothesis and a measure, and a decomposition of whatever it returns.

**Decision laundering.** A hard choice appears as a statement of fact with no
rationale, so nobody can challenge it. *Tell:* technical notes contain "we will
use X" with no `decisions` entry. *Fix:* promote it to a decision with options
and a rationale, even if the answer is obvious to you.

**Solution smuggled into the story.** The AC specifies a mechanism instead of an
outcome ("add a Redis cache"). *Tell:* AC mentions a technology. *Fix:* restate
as observable behaviour; move the mechanism to a decision where it can be argued
with.

**The implementation in the brief.** The agent brief contains pseudocode.
*Tell:* code blocks in `objective` or `conventions`. *Fix:* the seam is the
deliverable. Convert the code into a convention with a citation, or a decision.

## Decomposition smells

**Horizontal split.** "Backend subtask" and "frontend subtask" with nothing
demonstrable until both land. *Tell:* subtask titles name layers, under a
`vertical-slice` profile. *Fix:* re-slice, or switch profile deliberately and
add an explicit integration point.

**Subtask soup.** Fourteen 2-hour subtasks. *Tell:* subtask count above the
config max. *Fix:* the tracker is not a task list; merge to reviewable units, or
split the story.

**The catch-all.** A subtask called "Testing" or "Integration" or "Misc".
*Tell:* a title with no object, or with "and". *Fix:* those are the real work
hiding; name them.

**Phantom dependencies.** Everything depends on subtask 1 because it was written
first. *Tell:* a dependency chain that is a straight line with no contract
edges. *Fix:* only record a dependency when B genuinely cannot start without A's
output. Over-serialised graphs block parallel work for no reason.

**Shared file, no owner.** Two subtasks both list the same path in their brief's
change surface. *Tell:* `PAR001`. With humans this is a merge conflict; with
parallel agent implementors it is two runs overwriting each other. *Fix:* give
the file to one subtask, or add a dependency so they are ordered, and put the
boundary in both `forbidden` lists.

**One subtask per wave.** The dependency graph is a straight chain, so nothing
parallelises. *Tell:* `emit.py` reports as many waves as subtasks. *Fix:* most of
those edges exist because you wrote the subtasks in that order, not because the
work is sequential.

**Missing contract edge.** Two repos change, no contract listed, no ordering.
*Tell:* `evidence.contracts` empty while `blast_radius.repos > 1`. *Fix:* find
the seam - there is always one - and order the subtasks across it.

## Audience smells

**Two documents that disagree.** The human text says one thing, the agent brief
another, usually because the brief was written first and the story text was
edited later. *Tell:* a decision present in one and absent from the other.
*Fix:* regenerate both from the bundle; never hand-edit one side.

**Agent brief as padding.** The brief is the human text reformatted as JSON.
*Tell:* no `done_when` commands, no cited conventions, no `forbidden`. *Fix:*
it is not a brief until it prevents wandering, creep, drift and false
completion.

**Human text as documentation.** 600 words explaining the domain to a colleague
who works in it daily. *Tell:* over budget. *Fix:* cut every sentence they could
have written themselves. Compression is respect.

**Unverifiable done-when.** "Works correctly", "no regressions", "code
reviewed". *Tell:* zero `command` entries. *Fix:* take the real command from the
repo manifest.

## Process smells

**Readiness theatre.** The DoR checklist is ticked to unblock the sprint, with
the questions still open. *Tell:* `validate.py` was not run, or was run and
overridden. *Fix:* report not-ready. A blocked story that is honestly blocked is
worth more than a ready-looking one that stalls in development.

**Refining the unrefinable.** The story depends on a decision nobody has
authority to make in this session. *Tell:* an open question whose owner is
outside the team. *Fix:* stop, escalate the question by name, and propose a
spike that is useful regardless of which way the decision goes.

**Silent scope inflation.** The refinement is better than the story asked for.
*Tell:* AC not traceable to `story.source_text`. *Fix:* move the improvements to
`non_goals` with a follow-up note, and say out loud that you did so.

**Unopposed handover.** The bundle is well-formed and nothing hostile ever read
it. *Tell:* `REV001`, or a `review` block whose critics all found nothing.
*Fix:* Phase 8. The smells of the critique itself - the agreeable panel, critique
theatre, invented severity, the author defending - are in
`references/critique.md`.
