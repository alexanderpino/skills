---
name: fan-out
description: >-
  User-invoked only — reachable exclusively through the /fan-out slash command. Do NOT load
  or act on this skill because a task looks parallelisable, because the user mentions
  sub-agents, critics, parallel work, multiple approaches, or reviewing agent output, or
  because it would be faster. Those are not invocations. If the user has not typed
  /fan-out or named the fan-out method by name, this skill does not apply — answer the
  request directly instead. When it IS invoked: fans one task out to parallel sub-agents
  against a single sealed brief, has independent critics judge each candidate against a
  rubric written before the work started, verifies fixes against the delta only so approved
  work is never re-reviewed, and folds one result with an evidence trail.
metadata:
  invocation: user
---

# Fan-Out

One brief. N builders. Independent critics. One fold.

## Invocation

This is a **user-invoked** skill. It runs when the user types:

```
/fan-out <task>
```

and at no other time. Never start this loop on your own initiative — spawning N sub-agents
and a critic wave is an expensive, high-latency commitment that belongs to the user, not to
your judgement about what would be thorough. A task that merely *looks* like fan-out work
is a task you should do directly.

Two consequences that follow from being user-invoked:

- **Never nest.** A builder or critic spawned by this skill must not invoke `/fan-out`, or
  any other user-invoked skill. Model-invoked skills are fine and often useful — pass the
  relevant ones through in the shared block so every agent gets the same discipline.
- **The slash command is required.** `commands/fan-out.md` must be copied to
  `.claude/commands/`. Claude Code only reads commands from there, so while it sits in the
  skill folder there is no way to invoke this at all.

## Orientation

**Governing principle:** the shared context is written once and never mutated. Everything
that differs between agents lives at the *end* of the prompt, never the beginning. That one
rule is what makes prompt caching work and what makes the critics' comparisons valid — if
agents disagree about the ground truth, their outputs are not comparable and the critique
is noise.

**You (the model reading this) are the Orchestrator.** You slice, spawn, gate, and fold.
You do not build the candidates yourself. The moment you write one, you can no longer judge
the set impartially.

## Conventions

Everything lives under `.fan-out/<run-id>/`. Each slice gets one **slice id** — lowercase,
hyphenated, fixed for the whole run — and it must be identical in all three places, or the
tooling silently fails to correlate them:

```
candidates/<slice-id>.md     verdicts/<slice-id>.json     revisions/<slice-id>/v<N>/
renders/<slice-id>/r<N>/
```

`renders/` holds whatever a critic has to *look at* rather than read — screenshots,
plots, frames, exported pages. One directory per round, so a verification round can put
the new render beside the old one instead of taking the builder's word that the visual
finding is fixed.

## The loop

```
TASK
   │
   ├─► SLICE ──────► partition (different parts) or compete (same part, N approaches)
   │
   ├─► BRIEF ──────► one immutable file: shared context, identical for everyone
   ├─► RUBRIC ─────► written BEFORE any builder runs, sealed with the brief
   │
   ├─► PATHFINDER ─► builder #1 alone; its run writes the shared cache prefix
   │
   ├─► FAN-OUT ────► builders #2..N in parallel; they read the prefix from cache
   │
   ├─► CRITICS ────► one per candidate, blind to each other, same brief prefix
   │
   ├─► VERIFY ─────► delta and open findings only; never re-review approved scope
   │
   └─► FOLD ───────► one result + a short evidence trail
```

## Step 1 — Slice

Pick the mode first, because it changes everything downstream:

| Mode | When | Fold means |
|---|---|---|
| `partition` | The job splits into independent parts (per-module refactor, per-chapter draft, per-file audit) | Merge the parts |
| `compete` | One job, genuinely uncertain approach (algorithm choice, API design, prose voice) | Pick the winner, or synthesize |

If the request is ambiguous, ask once. Guessing wrong is expensive: `partition` work judged
as `compete` produces critics arguing that incomparable things are unequal.

### Cohesion first: N is an output, not an input

Work that sits close together — same files, same symbols, same mental model — belongs in
**one** slice, and the cut goes where the coupling is weakest. Splitting coupled work makes
two agents rebuild the same model, fight over the same files, each drag a critic behind
them, and — worst — makes every verification round cascade, because revising one re-opens
the other's approved regions. `references/incremental-review.md` has that mechanism.

Don't guess at the coupling, measure it:

```bash
python scripts/fanout.py plan
```

Fill `slices.json` with the proposed slices and the files each would touch. `plan` reports
three tiers: shared write targets and cross-slice dependencies are merges, shared
vocabulary is advisory.

- **Floor** — don't spawn an agent for work smaller than the brief it must read. Three
  one-line fixes in one file are one slice. This holds inside the loop too: give a builder
  all of a slice's open findings in one pass, not one pass per finding.
- **Ceiling** — stop merging when a slice no longer fits one coherent working set, or stops
  being verifiable in one pass. Between floor and ceiling, N is determined by the work.
- **`compete` is exempt** — there the redundancy is the point, and merging destroys the
  diversity that made the mode worth choosing. It's bounded instead by how many genuinely
  different constraints you can state, which is rarely more than four.

**`partition` rules.** No two slices write the same file — if `plan` shows an overlap,
merge rather than coordinate. Each slice must be verifiable on its own: if B can only be
judged once A lands, it isn't a slice, it's a phase, and phases are sequential.

**`compete` rules.** Each builder gets a genuinely different constraint, not different
wording. "Optimise for allocation count" vs "optimise for readability" is a real choice;
"do it well" vs "do it nicely" is N copies of one answer and N critics with nothing to say.
State it in one line — that line is the only per-agent text.

## Step 2 — Brief and rubric

```bash
python scripts/fanout.py init "<task>" --mode compete --n 4
```

Creates `.fan-out/<run-id>/` with `brief.md` and `rubric.md` skeletons.

**Fill `brief.md` with everything every agent needs and nothing else:** goal, constraints,
relevant paths, acceptance criteria, definition of done, and any excerpt the agents would
otherwise go discover for themselves. Pre-loading this isn't only a caching trick — it
stops N agents from each exploring separately and arriving at N different models of the
problem.

**`brief.md` must not contain** timestamps, run IDs, agent numbers, per-slice file lists,
"you are agent 3 of 7", or anything else that differs between agents.
`references/prompt-caching.md` explains why each of those is fatal.

**If the work has a visual surface, the brief carries the recipe for reaching it.** One
command that renders the candidate, plus the exact state to render it in — viewport, seed,
theme, sample input, which page or frame. This belongs in the shared block precisely
because it must not vary: two candidates screenshotted at different widths are two facts
about different things, and the critics' scores stop being comparable. The recipe is
identical for everyone; only the slice id in the output path comes from the delta.

**Fill `rubric.md` before any builder runs.** A rubric written after seeing the candidates
is a rationalisation of the one you already liked. Three to six axes, each with a concrete
failure example, plus the blocking conditions that force `reject` regardless of score. If
there is something to look at, at least one axis must be scoreable **only** from the
render — otherwise the critics quietly score the source that produces the picture, which
is the failure Step 4 exists to prevent.

```bash
python scripts/fanout.py seal
```

From here on, an edit to the brief is a detected error rather than a silent one —
`fanout.py check` will fail.

## Step 3 — Pathfinder, then fan out

Spawn builder #1 **alone** and wait for it to return, then spawn #2..N **in the same turn**.
The pathfinder does real work on a real slice; it goes first only so its request writes the
shared prefix that the other N-1 read from cache.

Skip it and fire everything at once when the brief is under roughly 1,000 tokens or N is 2.
Read `references/prompt-caching.md` before deviating further.

**Builder prompt — this exact shape, shared block first:**

```
Read <run-dir>/brief.md in full before doing anything else. It is the complete and
authoritative context for this task. Do not go looking for additional context; if the
brief is insufficient, say so in your notes rather than improvising.

Write your candidate to <run-dir>/candidates/<slice-id>.md (plus any code files it
describes). End it with a "Notes" section: what you assumed, what you were unsure
about, and what you would check next.

If the brief names a visual surface, produce it before you finish: run the render
recipe exactly as written, write the output to <run-dir>/renders/<slice-id>/r1/, and
link it from your candidate. Your critic will judge the render rather than your
description of it, so an unrendered candidate is judged on a missing artifact. If the
recipe fails, say so in your notes with the error — do not substitute a description.

---
YOUR SLICE: <the one line that differs>
```

Everything above the `---` is byte-identical across every builder. Everything below is the
delta. Keep it that way even when it feels redundant.

## Step 4 — Critics

One critic per candidate, all spawned in the same turn, each seeing **exactly one**
candidate. They do not see each other's verdicts and they do not see the other candidates —
a critic that has already read three candidates is anchored, and anchored critics converge
on the first thing they read.

Critics read the same `brief.md` first, so they hit the prefix the builders just paid for.
A long pause between build and critique costs you the cache (5-minute default TTL).

**Critic prompt:**

```
Read <run-dir>/brief.md in full. It is the authoritative context.
Then read <run-dir>/rubric.md.

---
Judge exactly one artifact: <run-dir>/candidates/<slice-id>.md
If the brief names a visual surface, open <run-dir>/renders/<slice-id>/r1/ and judge
what you see there. Do not read any other candidate.
Write your verdict to <run-dir>/verdicts/<slice-id>.json in this schema:

{
  "candidate": "<slice-id>",
  "round": 1,
  "scores": {"<axis>": 1-5, ...},
  "findings": [
    {
      "id": "F-<slice-id>-01",
      "severity": "blocker" | "major" | "minor" | "nit",
      "anchor": {"file": "<path>", "symbol": "<function or heading>",
                 "quote": "<short verbatim excerpt>", "line_hint": 42},
      "claim": "what is wrong",
      "check": "the concrete observation that would prove this fixed",
      "status": "open"
    }
  ],
  "approved": ["<path or symbol you examined and found sound>", ...],
  "evidence": ["what you actually ran or read", ...],
  "verdict": "accept" | "revise" | "reject"
}

Score against the rubric, not against your taste. Every finding needs an anchor into the
candidate — an unfalsifiable objection is not a finding.

Where the brief names a visual surface, your evidence must say what you saw in the
render. If it is missing, stale, or the recipe errored, do not grade the source in its
place: return "revise" with one finding whose check is the render you need, stated
precisely enough for someone to produce it — what to render, at which state, viewport
and seed. Where the brief names none, do not ask for one.

Calibrate severity to consequence, not to how strongly you feel about it. Be blunt about
anything provably wrong — correctness, data loss, security, an unmet acceptance
criterion, a failing check: state it flatly with its anchor, no hedging and no softening.
Be gentle about preference — a defensible call the brief left open, a structure you would
have built differently: one line, "nit" or "minor", and say plainly what you found sound.
Never raise a severity to make a preference get attention.
```

Three fields carry the whole re-review design:

- **`check` is an observation, not an instruction.** "Add a null guard" is a demand;
  "`Frame()` returns early when `entity` is invalid" is a check, and a later round can
  confirm it mechanically. What can't be phrased as an observation is taste, and taste is a
  `nit` at most.
- **`anchor` must survive an edit** — symbol name plus a short verbatim quote, line as a
  hint only. Line numbers shift the moment the builder touches the file.
- **`approved` is a claim you'll be held to** — whatever is listed there is out of scope for
  every later round unless the code underneath it changes.

Critics that can run something (compile it, execute the tests, diff it) should. A critic
whose `evidence` contains only opinions is a weak gate; treat its `accept` as unproven.

### Demand the visual when there is a visual to demand

The rule is conditional, and both halves of the condition do work:

- **Something visual exists — or the candidate already ships what produces it — so the
  critic demands it and judges that.** A rendered page, a chart, a UI state, a game frame,
  a diagram, a laid-out document. Never grade the markup, the shader, or the plotting call
  in place of the thing they produce: source that *should* centre the legend and a render
  showing the legend clipped are two different facts, and only one of them is the artifact.
  A verdict on a visual axis whose `evidence` names no render is unproven in exactly the
  way an untested `accept` is unproven.
- **Nothing visual exists** — a pure refactor, an API design, a parser, a prose slice with
  no layout — **so the critic does not ask for one.** A screenshot manufactured to satisfy
  a checklist costs a round and proves nothing, and a critic that pushes a builder to
  invent a visual surface has widened the brief on its own authority.

**Producing it is the builder's job and yours, never the critic's.** The brief carries the
recipe (Step 2) and the builder runs it (Step 3), so in the normal case the render is
already sitting in `renders/<slice-id>/r1/` and the demand never has to be made.

**When the critic demands and finds nothing to look at** — missing, stale, empty, or a
recipe that errored — that is a broken inspection path, not a low score. The critic states
the demand precisely (what to render, at which state, viewport, seed) and returns `revise`
with a finding whose `check` is the render's own existence: `renders/<slice-id>/r1/empty-state.png
exists and shows the placeholder copy at 1280px`. It does not fall back to grading the
source — a guess dressed as a verdict is worse than a stalled round, because the fold
cannot tell the two apart.

Then **satisfy the demand rather than waving it away.** Re-run the recipe yourself if it is
mechanical, hand the demand back to the builder if it is not, and re-spawn the critic on
the render. That round is cheap: the demand is delta text and the prefix is still warm.
Only when the render genuinely cannot be produced here — no headless renderer, no harness,
an asset nobody has — do you record the visual axis as **unscored** in the fold report and
say why. Never let a source-only verdict stand in for it silently.

### Soft where it can be, harsh where it must be

Severity is a claim about consequence, not a measure of how strongly the critic felt.
Calibrate both the severity and the tone that carries it to what being wrong would cost:

- **Harsh** where the artifact is wrong and provably so — correctness, data loss, security,
  an unmet acceptance criterion, a failing oracle, a claim the candidate makes that its own
  render or test output contradicts. State it flatly, once, with the anchor: no hedging, no
  praise sandwich, no "you might consider". Softening a real failure is the expensive
  direction; the gate opens and the fold reports as shipped something nobody approved.
- **Soft** where the disagreement is preference — a defensible call the brief left open, a
  structure the critic would have built differently, a style choice with no consequence
  downstream. Say it once as a `nit` or `minor`, phrase it in the builder's own terms, and
  approve the surrounding work explicitly. Do not inflate severity to make a preference get
  attention; that is precisely how `major` stops meaning anything.
- **Soft on the builder, never soft on the check.** Harshness is refusal to grade on a
  curve, not insult, and it is never a licence for contempt. Where the candidate is sound,
  say so plainly — a critic that finds nothing has produced a result, not failed at its
  job, as long as its `evidence` shows it looked.
- **A defect in the brief is not a defect in the candidate.** When a builder was misled by
  an ambiguous brief, say that in the finding's `claim` and keep the severity honest. The
  brief is the orchestrator's error to fix between runs, not the builder's to absorb.

The tie-breaker when a finding sits between `major` and `nit`: ask what it costs to be
wrong in each direction. Wrong-harsh on a nit costs one builder round. Wrong-soft on a
blocker ships the blocker. Where the two are symmetric, go soft; where they are not, go
harsh.

The loop punishes each failure direction differently, and both are visible in the run. A
uniformly harsh critic inflates severities until the gate can no longer discriminate and
the builder spends its two rounds on taste. A uniformly soft critic returns `accept` with a
thin `evidence` array and the gate becomes theatre. If a critic's verdict shows either
pattern, re-read it yourself before folding on it.

## Step 5 — Verification rounds (never re-review what was approved)

A round that re-reads everything is expensive, and worse, it moves the target so the
builder can never converge and the earlier `accept` turns out to have meant nothing. So a
verification round reviews **the delta and the open findings only**. Mechanism and rationale
in `references/incremental-review.md`.

**1. Snapshot before the builder touches anything.**

```bash
python scripts/fanout.py snapshot <slice-id> <path>...
```

Without this there is no delta and the round degenerates into a full re-review.

**2. Send the builder only the open findings**, below the `---` as always, each with its
`check`, plus:

> Fix only these findings. If a fix requires changing something outside them, say so in
> your notes instead of doing it silently — an unexplained out-of-scope edit re-opens
> everything it touches.

**3. Compute the scope mechanically before spawning any critic.**

```bash
python scripts/fanout.py snapshot <slice-id> <path>...   # the new revision
python scripts/fanout.py scope <slice-id>
```

Prints three sets: changed hunks (in scope), previously-approved files referencing a symbol
touched by the diff (**re-opened** — this is what keeps delta-review honest), and everything
else (out of scope, do not read).

**4. Run the cheap oracles first, and re-render.** Build, tests, lint, a grep for what the
`check` describes. Every finding a mechanical check resolves is one the critic never sees.
If the slice has a visual surface, re-run the render recipe — same command, same state —
into `renders/<slice-id>/r<N>/`. A finding on a visual axis is verified by looking at the
new render beside the old one; "fixed the clipping" is a claim, and a claim is not a check.

**5. Spawn the verifier** — same shared prefix, tiny delta:

```
Read <run-dir>/brief.md in full. It is the authoritative context.
Then read <run-dir>/rubric.md.

---
VERIFICATION ROUND <N> for <slice-id>.

Open findings to verify: <run-dir>/verdicts/<slice-id>.json (status == "open")
In-scope diff and re-opened files: <paste the `scope` output>
Renders: <run-dir>/renders/<slice-id>/r<N>/ against r<N-1> — for any finding on a
visual axis, decide it by comparing the two renders, not by reading the change that
was supposed to produce them.

For each open finding, decide `verified` or `unresolved` against its own `check` — not
against a better fix you would have preferred. Record the observation that decided it in
a "reason" field. A fix that satisfies the check is verified even where you would have
written it differently; a check that still fails is unresolved even where the builder
clearly tried. Do not promote a nit to keep the round busy.

You may raise a new finding ONLY if it sits inside the in-scope diff or a re-opened file.
Anything outside that is out of bounds — except a genuine blocker (correctness, data
loss, security), which you may raise with "late": true and an explanation of why it was
not visible in round 1. Late minors and nits are logged as follow-ups.

Do not read files listed as out of scope. Do not re-score axes with no in-scope change;
carry the previous score forward.
```

**6. Gate.**

```bash
python scripts/fanout.py gate <slice-id>
```

Exit 0 = done, 1 = another round, 2 = escalate. Default cap is two verification rounds. If
a slice can't converge in three attempts, the brief was wrong or the slice was badly cut —
both your errors, not the builder's. Escalate with what the rounds disagreed about.

To ship a known issue past the gate, set that finding's status to `waived` with a `reason`.
That is an orchestrator decision, it is recorded, and it appears in the fold report.

For `partition` runs, the integration critic on the merged result reviews **the seams
only** — the interfaces between slices. Slice internals were already approved by their own
critic and are not its business.

## Step 6 — Adjudicate and fold

Read the **verdicts**, not the candidates. That keeps your context small enough to hold the
whole picture, which is the only place cross-cutting judgement can happen. Pull up a full
candidate only when a verdict is contested or unclear.

- `partition` → merge slices that passed the gate. Never edit the brief to fix a slice.
- `compete` → rank by rubric score, break ties on unresolved findings weighted by severity,
  then read the top two candidates yourself before committing. Synthesis is allowed and
  often correct: take the winner's structure and the runner-up's specific better idea, and
  say which is which.

For a `compete` run with a visual surface, look at the renders side by side yourself before
you rank — the verdicts tell you what each critic saw one at a time, and a comparison
across candidates is the one judgement no critic was allowed to make.

Finish with a short fold report: what shipped, what was rejected and why, every `waived`
finding with its reason, any visual axis left unscored because the render could not be
produced, the late and nit findings deferred to follow-ups, and any assumption a builder
recorded that nobody verified. Those last two are where fan-out runs actually go wrong — not in what the critics caught, but in what everyone agreed to stop
looking at.

## When an agent fails

A missing, empty, or truncated candidate is a **failed** slice, not a rejected one. There
is nothing to judge, so don't spawn a critic for it and don't let it enter the fold as a
low score. Re-spawn once with the identical prompt; a second failure points at the slice or
the brief, so escalate rather than trying a third time.

The same goes for a verdict that won't parse or arrives with an empty `evidence` array —
that is not a verdict. Re-spawn once, then judge that slice yourself and say so in the fold
report.

A partial fan-out is still useful. If three of five slices land, fold those three and
report the other two as unattempted rather than discarding a good round for being
incomplete.

## Resuming

```bash
python scripts/fanout.py status
```

Reports the newest run: which candidates exist, which have verdicts, how many snapshots
each slice has. Pick up from there rather than restarting — the brief is sealed, so the
ground truth is intact, and `check` will say so if it isn't.

## Cost discipline

Fan-out multiplies token spend by roughly N. It pays for itself when the slices are truly
independent or the approach is genuinely uncertain, and not on a task one agent could do in
one pass — parallelism buys wall-clock time and diversity, never correctness by itself.
Three agents confidently wrong in the same direction is the normal failure mode, and it is
why the critics are separate agents with a pre-written rubric rather than a self-review
step.

## Reference

- `commands/fan-out.md` — the `/fan-out` slash command; the only entry point. Copy it to
  `.claude/commands/` (see Invocation above).
- `references/prompt-caching.md` — what actually caches, what silently doesn't, the
  ordering rules, and why the pathfinder goes first. Read before changing prompt shapes or
  the spawn sequence.
- `references/incremental-review.md` — the finding lifecycle, why re-opening approved scope
  is necessary, cross-slice cascades, the ratchet guard, anchor drift. Read before running a
  verification round or changing the verdict schema.
- `scripts/fanout.py` — run dir, seal/check, plan, snapshot/scope/gate, status.
  Deterministic; no model calls. `plan` and `scope` apply the same coupling rule, before and
  after the fact respectively.
