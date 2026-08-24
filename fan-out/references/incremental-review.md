# Incremental review

Read this before running a verification round or changing the verdict schema.

## Contents
- [The problem](#the-problem)
- [Findings are the unit of state, not artifacts](#findings-are-the-unit-of-state-not-artifacts)
- [Scope: what a verification round is allowed to read](#scope-what-a-verification-round-is-allowed-to-read)
- [Re-opening approved scope](#re-opening-approved-scope)
- [Cross-slice cascades](#cross-slice-cascades)
- [The ratchet guard](#the-ratchet-guard)
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
open ──► verified     (the check now holds)
     ├─► unresolved   (the check still fails — carries to the next round)
     └─► waived       (orchestrator overrules; ships as a known issue)
```

Three states, plus two optional fields: `reason` (free text, mandatory on `waived`, useful
on `unresolved`) and `late` (a boolean, see the ratchet guard). Resist adding a fourth. An
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

The `severity` scale decides what blocks:

- `blocker` — correctness, data loss, security, or the acceptance criteria are unmet
- `major` — will cause a real problem, but the artifact is not wrong today
- `minor` — worth fixing, doesn't block
- `nit` — preference; logged, never actioned in this run

Only `blocker` and `major` hold the gate. Everything else lands in the fold report as a
follow-up, which is the honest place for it.

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

## Cheap oracles before expensive judgement

Run the mechanical checks before spawning anything. Compilation, tests, linters, a grep
for the condition a `check` describes — each of these resolves findings at near-zero cost
and with better reliability than an agent reading code.

Order the gates by cost, cheapest first, and stop at the first one that fails:

```
compile ──► tests ──► static checks ──► grep/AST for specific checks ──► agent judgement
```

A round where the build is broken should never reach an agent; the build failure is the
finding. In practice a large share of `check` fields on a code slice are mechanically
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
- Spawn verifiers for all slices in the same turn, immediately after the builders return,
  while the prefix is warm.
- Don't re-warm with a pathfinder for a verification wave. The prefix already exists and
  the wave is short.

If the run has been idle long enough for the 5-minute TTL to expire, the verification
prompts are small enough that a cold prefix costs little — the brief dominates, and you'd
be re-writing it either way.

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
suggestion. This is the most common quality leak in the whole loop.
