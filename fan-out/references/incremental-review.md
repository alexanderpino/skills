# Incremental review

Read this before running a verification round or changing the verdict schema.

## Contents
- [The problem](#the-problem)
- [Findings are the unit of state, not artifacts](#findings-are-the-unit-of-state-not-artifacts)
- [The check names the target, not the deviation](#the-check-names-the-target-not-the-deviation)
- [A finding is a delta, not a complaint](#a-finding-is-a-delta-not-a-complaint)
- [When the critic does not know the target either](#when-the-critic-does-not-know-the-target-either)
- [Give the check a decider](#give-the-check-a-decider)
- [Scope: what a verification round is allowed to read](#scope-what-a-verification-round-is-allowed-to-read)
- [Re-opening approved scope](#re-opening-approved-scope)
- [Cross-slice cascades](#cross-slice-cascades)
- [The ratchet guard](#the-ratchet-guard)
- [When the check alone stops working](#when-the-check-alone-stops-working)
- [Anchor drift](#anchor-drift)
- [Cheap oracles before expensive judgement](#cheap-oracles-before-expensive-judgement)
- [Termination](#termination)
- [Interaction with prompt caching](#interaction-with-prompt-caching)
- [Failure modes](#failure-modes)

## The problem

A naive critic loop re-reads the entire candidate every round. Three things go wrong, in
increasing order of seriousness:

1. **Cost.** You pay full review tokens per round for an artifact that changed by twenty
   lines.
2. **Non-convergence.** Every fresh read surfaces fresh objections, so the builder chases
   a target that moves. Rounds 2, 3 and 4 each produce "just one more thing" and the slice
   never lands.
3. **Approval becomes meaningless.** If round 2 can reject what round 1 approved, then
   round 1's `accept` was never a commitment, and there is no point in it. A gate that
   doesn't hold is theatre.

The fix is the same one every mature code review tool converged on: review the delta, not
the artifact — but with an explicit rule for the case where the delta invalidates
something previously approved. That rule is what separates this from naive diff-review,
which is unsound.

## Findings are the unit of state, not artifacts

An artifact-level verdict (`accept` / `revise`) can't survive a round trip, because
"revise" carries no memory of *what* needed revising. Findings can. Each one is a small
state machine:

```
open ──► verified     (the check now holds — terminal)
     ├─► unresolved   (the check still fails) ──┐
     │        ▲                                 │
     │        └───── next round ────────────────┘
     └─► waived       (orchestrator overrules; ships as a known issue — terminal)
```

Only `verified` and `waived` are terminal. `unresolved` is a cycle: it is re-sent to the
builder and re-judged, and the gate treats it exactly as it treats `open` — which is why
`fanout.py` blocks on both and why an anchor that stops resolving becomes `unresolved`
rather than disappearing.

Three transitions out of `open`, plus two optional fields: `reason` (free text, **enforced**
on `waived` — the gate stops on an unreasoned waive, because that is the one path where a
blocker leaves the loop by decision rather than by fix) and `late` (a boolean, see the
ratchet guard). Resist adding a fourth. An
earlier draft separated "the critic was wrong" from "valid but we ship anyway"; both mean
"does not block", the distinction lives in `reason`, and the gate only ever needed to know
which findings hold it shut.

The `check` field is what makes the transition decidable. It must be an **observation**
that is true or false about the artifact, not an instruction:

| Bad (`check` as a demand) | Good (`check` as an observation) |
|---|---|
| "Add bounds checking" | "`QueryChunk()` returns nullopt when `index >= count`" |
| "Improve error handling" | "Every `vkCreate*` return code is inspected before use" |
| "Make this clearer" | (not a check — this is a `nit`, and nits never block) |

If a finding can't be phrased as an observation, it's taste. Taste is worth recording as a
`nit`, and nits are follow-ups, never gates.

### The check names the target, not the deviation

An observation can be true, anchored, non-imperative — and still useless, because it
describes what is wrong instead of what would be right:

| Bad (`check` as a deviation) | Good (`check` as a target) |
|---|---|
| "The body colour is off" | "The body is `#C8102E`, as in `reference.png`" |
| "Frame time is too high" | "The p99 frame time is under 16.6 ms at 1080p, seed 7" |
| "The tone is inconsistent" | "Every section uses second person, as `intro.md` does" |
| "Error handling is weak here" | "Every `vkCreate*` return code is inspected before use" |

The left column is the same sentence as the `claim`. That is the tell: `claim` says what is
wrong, `check` says what would be true once it is right, and if the two say the same thing
the finding is carrying no target at all.

What it costs is a whole run. Told the colour is off, a builder paints the car blue — a
sincere attempt, and wrong, because the finding admitted an infinite set of satisfying
states and the critic was holding exactly one. Round 2 rejects it again. Round 3 rejects it
again. Every round is spent transmitting, one bit at a time, a fact the critic could have
written in six words. The escalation then reads as a builder that could not converge, which
is the wrong lesson: it was never told where to converge to.

There is also a soundness argument, independent of cost. A finding whose check only the
critic can evaluate is unfalsifiable, and an unfalsifiable finding is not a gate — it is a
veto. The verifier in the next round is a *different agent instance*, and it cannot read
the target out of the first critic's head. It either invents its own (the target moves
between rounds, which is the non-convergence this whole document exists to prevent) or it
defers to the builder (the gate rubber-stamps). Neither is review.

So a check must be **satisfiable by aiming**: a value, a range, a threshold with its
measurement conditions, a named reference to compare against, or a quoted line of the brief
or rubric. Where the target lives in the bar rather than in the text — "matches
`reference.png`" — naming the referent is enough, because the builder can go and look.

### A finding is a delta, not a complaint

The target is one end of a line. `observed` is the other, in the same units:

```json
"claim":    "the hero body renders grey, not the brand red",
"observed": "#808080 at the body panel — r1/hero.png, centre, 1280px",
"check":    "the body is #C8102E, as in bar/reference.png",
"sites":    ["hero.svg:carBody", "thumb.svg:carBody"]
```

Every field there is something the critic read off the artifact while it had the artifact
open. That is what makes them cheap to write and expensive to omit: the critic pays one
line, the builder pays a round.

- **`observed` without `check`** is the guessing game above.
- **`check` without `observed`** makes the builder re-measure what the critic just
  measured — and re-measure it *differently*, which is how a round gets spent arguing about
  whether the colour was ever grey.
- **Both** give a delta, and a delta is the only form a builder can act on directly and a
  verifier can decide without re-deriving anything.

`sites` closes the other repeat-round trap. A defect that occurs in three places, anchored
at one, is fixed at one and rejected for the other two — and the critic knew all three when
it looked. Listing them is not widening the finding; it is describing the finding
accurately, which is why the sites are in-bounds for the builder (see Step 5.2 in
SKILL.md). `scope` still sees those edits and still reviews them — that part is mechanical
and should not change — but they arrive as work the finding asked for rather than as
unexplained drift, which is the difference between a re-open and a suspicion. An empty
`sites` is a positive claim that the defect is local, in the same way `approved` is a
claim.

The discipline that keeps this from becoming verbosity: **detail about the observation,
never about the opinion.** A measurement, a location, a list of sites, a command that was
run — all bounded, all verifiable, all reusable by the next round. Rationale for the
severity, an argument for why the finding matters, a survey of what the critic considered —
unbounded, unverifiable, and carried by every agent downstream. A finding that needs a
paragraph of justification is usually a preference filed at the wrong severity.

### When the critic does not know the target either

The rule above has a failure case that must not be papered over. Sometimes the critic
genuinely cannot name the target, because nothing ever fixed it — the brief never said what
colour the car should be. The critic then knows only that the current colour is *a* choice,
not that it is the *wrong* choice.

That is a defect in the brief, and it is already the orchestrator's error rather than the
builder's (see *soft where it can be, harsh where it must be* in SKILL.md). The critic says
so in the `claim`, at the honest severity, and does not file a check the builder cannot aim
at. Filing one anyway is the worst outcome available: the run burns its cap discovering
that the critic's private preference was never written down, and the fold reports a slice
that failed to converge when what actually happened is that nobody specified it.

A run that produces these repeatedly is telling you the brief was thin. Fix it between
runs — that is what a sealed brief is for, and what the ratchet guard cannot do for you.

### Give the check a decider

An observation stated precisely enough is often one a command can settle. `check_cmd` is
that command, written so **exit 0 means the check holds**:

```json
"check": "QueryChunk() returns nullopt when index >= count",
"check_cmd": "ctest -R chunk_bounds --output-on-failure"
```

A finding with a decider never reaches an agent: `fanout.py deciders <slice-id>` prints
them, you run them, and each exit-0 closes its finding with a `reason` naming the command.
That is the same saving as *cheap oracles before expensive judgement* below, moved to
where it can be automated — the critic knows what would settle its own finding, and
writing it down costs one line while re-deriving it costs a verifier wave.

Four constraints keep it from rotting:

- **The critic writes only commands it ran**, here, against this candidate. An invented
  command is worse than no field: it fails for the wrong reason and the finding looks
  unfixed.
- **It must fail when filed.** A `check_cmd` that exits 0 at the moment the finding is
  raised means the check is wrong or the finding isn't real. Either way, resolving that at
  filing time is free and resolving it in round 2 is not.
- **It decides, it does not instruct.** `grep -n 'nullopt' store.cpp` tells the builder
  nothing about how to satisfy it, which is exactly why it is safe. A command that
  hard-codes the shape of the fix is a prescription wearing a shell prompt.
- **Never on a visual axis.** A render is decided by looking at the new one beside the
  old; a command that proves a PNG exists has not looked. `fanout.py deciders` says so, but
  the rule lives here.

`fanout.py` prints these commands and does not run them. The strings come from an agent,
and a tool that shells out to agent-authored text on sight would be handing the critique
loop an execution channel it has no reason to have. The operator runs them, in view.

The `severity` scale decides what blocks:

- `blocker` — correctness, data loss, security, or the acceptance criteria are unmet
- `major` — will cause a real problem, but the artifact is not wrong today
- `minor` — worth fixing, doesn't block
- `nit` — preference; logged, never actioned in this run

Only `blocker` and `major` hold the gate. Everything else becomes a follow-up — and a
follow-up needs somewhere to go, or "logged" means "left in a JSON file nobody opens after
the fold":

```bash
python scripts/fanout.py followups
```

Writes `follow-ups.md` in the run dir: everything waived (with the reason that justified
it), everything raised late, and every unresolved `minor` and `nit`, across all slices. Run
it before the fold and hand the file forward. A finding that still holds the gate is
deliberately excluded — that is work, not a follow-up, and a late `blocker` reopens the
round rather than draining into a file.

## Scope: what a verification round is allowed to read

`fanout.py scope <slice-id>` partitions the artifact into three sets by comparing the last
two snapshots:

**In scope — changed hunks.** Full review here, same standard as round 1. New findings
allowed freely.

**Re-opened — unchanged files that reference a symbol touched by the diff.** Reviewed for
one question only: *did this change break you?* Not a fresh general review.

**Out of scope — everything else.** Not read. Previous scores carry forward unchanged.

The verifier is told explicitly not to read the out-of-scope set. This is the actual
saving, and it only works if you tell it — an agent handed a file path will read the file.

## Re-opening approved scope

This is the part naive delta-review gets wrong, and it's worth being precise about.

"Unchanged bytes mean unchanged correctness" is false. A builder fixing finding F-03 in
`ArchetypeStore::Insert()` can trivially break `ArchetypeStore::Remove()` fifty lines
below, which round 1 approved and never touched. Reviewing only the diff would miss it,
and you would have shipped a regression through a gate that reported clean.

So `scope` over-approximates deliberately: it extracts every identifier appearing in
changed lines, then re-opens any previously-approved file mentioning one of them. This
reopens more than strictly necessary — a file that merely calls a touched function gets
pulled in even when the signature didn't change — and that bias is correct for a
correctness gate. A false re-open costs tokens; a missed one ships a regression.

`scope` prints which symbol caused each re-open, so you can overrule an obviously spurious
one. Overrule sparingly and say so in the fold report.

Where a project has better tooling than identifier matching — a compiler, a call-graph
index, `git blame`, a test-impact map — prefer it. Identifier matching is the portable
floor, not the ceiling.

### Cross-slice cascades

Everything above is local to one slice. Coupling *between* slices defeats it: if slice B
references a symbol slice A defines, then every revision of A re-opens B's approved
regions, and B's critic pays for A's rounds. Two coupled slices don't cost 2x — they cost
2x plus a cascade per round.

This is why `fanout.py plan` exists and why it runs before any agent is spawned. Its `DEP`
tier is not a heuristic: it applies exactly the rule `scope` applies, just before the fact
instead of after. A `DEP` edge between two proposed slices is a guarantee that the
verification rounds will cascade. Merge them and the cascade becomes an ordinary
within-slice re-open, which is the cheap case this whole design is built around.

## The ratchet guard

Without an explicit rule, a verifier will raise new findings anywhere it looks, and the
loop ratchets forever. The rule:

> In a verification round, a new finding is admissible only if it sits inside the
> in-scope diff or a re-opened file. Anything else is out of bounds — **except** a genuine
> blocker, which may be raised with `"late": true` plus an explanation of why round 1
> missed it.

The escape hatch matters. Without it you'd be committing to ship a known security hole
because the gate's own rules forbade mentioning it. With it, the cost of going late is
visible: a `late` finding is an admission that round 1 under-reviewed, it shows up in the
fold report, and if a critic produces them habitually its round-1 `approved` lists are
worth trusting less.

Late `minor` and `nit` findings are logged as follow-ups and never block. Only a late
`blocker` reopens the round.

**There is deliberately no late `major`.** The escape hatch is for damage you cannot ship —
correctness, data loss, security — and `major` means "will cause a real problem, but the
artifact is not wrong today", which by definition can wait for the follow-up list. Note
that the gate does not know this rule: it blocks on any unresolved `major`, `late` or not.
So a critic that files one has quietly widened the round past the ratchet guard, and you
either re-file it at its honest severity or accept it as work. The rule holds because you
enforce it at the prompt, not because the tooling catches it.

## When the check alone stops working

The `check`-not-instruction rule is right as a default and wrong as an absolute. Its cost
is real: a builder who cannot see what the critic sees can satisfy nothing three times in
a row, and the loop spends its whole cap discovering that.

So there is one licensed escape, and it is unlocked by evidence rather than by preference:

> Every finding a verifier marks `unresolved` carries a `remedy` — a concrete route to the
> check, at the anchor — or, where there is no route from here, a statement in `remedy` of
> what the gap actually needs.

The trigger is the `unresolved` transition and nothing else. Not severity, not the critic's
confidence, not how strongly it was phrased: a finding is `unresolved` exactly when a
builder has spent a round on it against the check and not closed it, which is the loop
*measuring* that the check alone did not land. A round-1 finding never gets a remedy —
that would hand every finding a suggested fix and reintroduce compliance-grading wholesale,
before there is any evidence the builder needed it.

Waiting one transition longer is tempting and wrong at the default cap. Three attempts per
slice means: build, fix, fix. A finding that only earns its remedy after two `unresolved`
verdicts gets it at the escalation, where the builder is no longer running — so the field
would only ever inform the user, never speed a round. Attaching it at the first
`unresolved` puts it in the one attempt that can still use it.

Three properties keep `remedy` from becoming the target:

- **The check remains the contract.** Verification decides against `check`, never against
  `remedy` — a builder who satisfies the check by a different route is `verified`, and one
  who follows the remedy exactly while the check still fails is `unresolved`. The verifier
  prompt says this in as many words.
- **It is non-binding to the builder**, who is asked to say in its notes when it took
  another route. That sentence is what lets you tell a bad remedy from a bad builder.
- **It is not a new status.** The state machine stays at three transitions. `remedy` is a
  field on a finding that is still `unresolved` and still holds the gate.

The "not closeable here" branch is the more valuable half. A remedy that reads *this needs
a schema change in another slice* ends the loop a round and a half early, and it is
information no gate can compute — only something that has now looked at the same gap
three times.

`fanout.py gate` prints unresolved blocking findings that carry no remedy, and repeats
every remedy in the escalation block, so the user deciding at the cap sees the critic's own
account of what it would take rather than a summary of the disagreement.

## Anchor drift

Line numbers are invalid the moment the builder edits the file, so a finding anchored on
`renderer.cpp:412` points somewhere arbitrary by round 2. Anchor on the durable things:

```json
"anchor": {
  "file": "src/renderer/passes/shadow.cpp",
  "symbol": "ShadowPass::RecordCascade",
  "quote": "for (uint32_t i = 0; i < kCascadeCount; ++i)",
  "line_hint": 412
}
```

Resolution order when verifying: symbol first, then quote, then `line_hint` — and if none
resolve, the finding is marked `unresolved` with `reason: "anchor lost"`, never silently
dropped. An anchor that stops resolving usually means the builder rewrote the region
wholesale, which is exactly the case that deserves a look rather than a shrug.

Watch what that does to termination, though. An anchor-lost `blocker` holds the gate while
pointing at nothing, so the builder has no target and each round re-loses it until the cap
escalates. Don't spend the rounds: re-anchor it yourself against the current artifact and
re-file, or escalate immediately. It is the one `unresolved` that another round cannot
move.

It is also the one `unresolved` with no honest remedy to attach — there is no route to a
check that points nowhere. Re-anchoring *is* the remedy, and it is yours, not the
verifier's. Where the gate lists an anchor-lost finding as carrying none, that is the
nudge working.

## Cheap oracles before expensive judgement

Run the mechanical checks before spawning anything. Compilation, tests, linters, a grep
for the condition a `check` describes — each of these resolves findings at near-zero cost
and with better reliability than an agent reading code.

Order the gates by cost, cheapest first, and stop at the first one that fails:

```
compile ──► tests ──► static checks ──► grep/AST for specific checks ──► agent judgement
```

A round where the build is broken should never reach an agent; the build failure is the
finding. Two things follow that are easy to get wrong. Stopping at the first failing gate
is right for *not spawning the critic* and wrong for *what you send the builder* — you
still cannot see the test failures behind a compile error, so send what you have and expect
another mechanical pass rather than pretending the list is complete. And a round that never
reached an agent does not spend the round budget: the cap counts judgement rounds, tracked
by the verdict's `round` field, so a slice that fails to compile three times has used none
of them. Otherwise a slice can exhaust its budget on mechanical failures and escalate
having never once been reviewed. In practice a large share of `check` fields on a code slice are mechanically
decidable, and the verifier agent ends up looking at a handful of judgement calls rather
than the whole file. That's the real cost reduction — bigger than the scope narrowing.

## Termination

- Default cap: **two verification rounds** (three attempts total per slice).
- Gate passes when no `blocker` or `major` finding is `open` or `unresolved`.
- Hitting the cap escalates to the user with the specific disagreement, not a summary.

Three failed attempts is a signal about the *brief* or the *slice cut*, not the builder. A
fourth attempt with the same brief has no reason to succeed, and spawning one is how a
fan-out run quietly consumes a whole budget.

## Interaction with prompt caching

Verification rounds are the cheapest agents in the run if you keep the shape right:

- `brief.md` is sealed, so it is still byte-identical — verifiers hit the prefix the
  builders already paid for. Never put the findings ledger in the shared block.
- The delta below the `---` is small: open findings plus a scope listing, not an artifact.
- Spawn verifiers for all slices in the same turn, immediately after the builders return.
  Whether the prefix is still warm is not up to you: the TTL runs from when a request
  starts, so a builder that spent longer than the TTL fixing findings has already aged out
  the entry. Spawn together anyway — it costs nothing and it is the only part you control.
- Don't re-warm with a pathfinder for a verification wave. The prefix already exists and
  the wave is short.

If the TTL has expired, the verification prompts are small enough that a cold prefix costs
little — the brief dominates, and you'd be re-writing it either way. Note that expiry
doesn't require the run to have been idle: the clock runs from the start of each request,
so a builder that spent five minutes fixing findings has aged the entry out by itself.

## Failure modes

**Critic lists whole files under `approved` after skimming.** Then the re-open logic has
nothing real to protect and round 2 rubber-stamps a regression. Approval claims should be
proportional to the evidence array; a critic with three evidence entries and eleven
approved files is claiming more than it checked.

**Builder makes out-of-scope edits while fixing.** This re-opens everything it touches and
inflates the next round. The builder prompt asks it to report rather than silently expand;
`scope` catches it either way, which is why the snapshot must be taken *before* the fix.

**Findings get merged or renumbered between rounds.** IDs must be stable — a finding
that changes identity can't be tracked to a resolution, and it's how a blocker disappears
without anyone deciding it should.

**`check` written as an instruction.** The verifier then evaluates "did you do what I
said" instead of "is the problem gone", and accepts a fix that follows the letter of a bad
suggestion. This is the most common quality leak in the whole loop. A `remedy` does not
make this safe — it makes it avoidable, by giving the instruction somewhere to live that
nothing grades against.

**`check` names the deviation, not the target.** The builder aims at nothing and the same
finding comes back round after round. The tell is in the ledger rather than in any single
verdict: the same finding `unresolved` twice, with the `reason` field naming a *different*
wrong state each time (grey, then blue). That is a critic revealing it held a target it
never wrote down. `fanout.py calibration` flags the shape as `NO-TARGET`; the ledger tell
is yours to notice. Re-file the check with the target in it — and if you cannot name the
target either, that is a brief defect, not another round.

**A defect fixed at its anchor and rejected for its unnamed siblings.** The critic saw
three call sites and anchored one. Round 2 rejects the fix as incomplete, and from the
builder's side the target moved. `sites` exists for exactly this; a critic that leaves it
empty on a pattern defect is filing one third of a finding.

**`check_cmd` the critic never ran.** It fails for its own reasons — wrong path, missing
target, a test that does not exist — and the finding reads as unfixed however good the
fix was. Worse, it fails *silently* in the useful direction: nobody re-examines a finding
that looks still-open. A command in this field is a claim to have run it.

**`remedy` graded instead of `check`.** The verifier reads the remedy, sees the builder
did something else, and marks `unresolved` on a check that now holds. That is the original
leak coming back through the escape hatch, which is why the field is non-binding in the
verifier prompt, in the builder's round instructions, and in the gate's own output.
