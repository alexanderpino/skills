---
name: reasoning-matrix
description: >-
  Generate genuinely non-obvious insights about a hard, open-ended question by
  building a reasoning matrix — systematically crossing the building blocks of a
  problem against a curated set of reasoning lenses, then filtering the results
  for novelty AND validity so what survives is both new and true. Use this
  whenever the user wants to think outside the box, find a fresh angle, break out
  of conventional framing, generate hypotheses, surface hidden structure, chain
  or compose one analysis into the next, attack a problem that "feels stuck," or
  asks for deep brainstorming, lateral thinking,
  or "new insights" — even if they don't say "matrix." Especially valuable when
  the obvious answer is already known and the user wants to get past it. Do NOT
  use for simple lookups, well-specified tasks with one right answer, or requests
  that just need a direct factual reply.
---

# Reasoning Matrix

A method for manufacturing insight on purpose instead of waiting for it.

Most "thinking harder" produces more of the obvious answer at higher volume. A
reasoning matrix avoids that by forcing combinations a linear train of thought
would never reach: it decomposes the subject into anchors, runs each anchor
through a set of distinct reasoning lenses, and treats every cell as a small
forced move. Each cell works the way explaining a bug to a rubber duck works:
re-encoding a problem in a register it wasn't stuck in fires reasoning paths the
original framing never activates. The matrix schedules those re-encodings
deliberately and in bulk instead of waiting for one to strike. The point of the
grid is structured surprise — and then a ruthless filter so only the cells that
are *both new and defensible* survive.

Nearly every invention is an **existing idea relocated into a new context** — a
mechanism lifted out of the domain that birthed it and dropped onto a new object
(natural selection was Malthus's economics applied to biology; the GUI desktop
was the office metaphor applied to a file system). The matrix manufactures those
relocations deliberately instead of waiting for one to occur to you. So it is
goal-agnostic by design: it carries no answers of its own, only the moves that
collide ideas you already have into ones you don't.

The output is **2–4 crystallized insights**, not a wall of cells. The matrix is
scaffolding; the user sees the building.

## When the matrix earns its cost

Use it for questions where the conventional answer exists and is unsatisfying —
"why does X keep happening," "what are we missing about Y," "what's a better way
to think about Z," strategy under uncertainty, design problems with no clean
spec, conceptual or causal puzzles. Skip it for anything with a single correct
answer or where the user just wants a fact. If you're unsure what kind of insight
is wanted, ask one question, then proceed.

## Right-size the matrix

The six phases are the *full* form; match the grid to the weight of the question
so the method never costs more than the answer is worth. The phases (frame the
default, decompose, populate, filter, synthesize, stress-test) are always run —
what scales is their visible footprint:

- **Light run** (a focused question, one clear insight type): a **3×4** grid,
  scoring done in your head, and only the kept cells shown. Skip the full scoring
  table; still name the default and still deliver the crystallized insights. This
  is the common case.
- **Full run** (a genuinely thorny, multi-stakeholder question): the complete
  4–7 × 5–8 grid with the explicit scored table and, if warranted, composition
  across matrices (`references/composition.md`).

Whatever the size, the output the user reads is the 2–4 insights — the grid is
shown below for inspectability, never as the answer itself. When in doubt, run
light; escalate only if the light grid keeps landing on the default.

## The method: six phases

Run these in order. Phases 1, 4, and 5 are where quality is won or lost — do not
rush them to get to a full grid.

> **Gate before you build (the default-first check).** The very first move is
> Phase 1's step 3: write the conventional, linear answer in one or two lines.
> Then judge it. If that answer already satisfies the question, *stop and return
> it* — the matrix is wasted ceremony on a question that didn't need it. Build the
> grid only once the linear answer is on the page and visibly *unsatisfying*. This
> is not a brake on out-of-the-box thinking; it's its precondition. You cannot
> reliably get past the obvious answer until you've named it — everything looks
> non-linear until you write down the line you're trying to leave.

### Phase 1 — Frame and name the default

Three moves, briefly:

1. **State the inquiry** in one sharp sentence. Vague input yields vague cells.
2. **Name the insight type** sought: causal (why), design (how to build),
   strategic (what to do), conceptual (how to understand), or predictive (what
   happens next). This drives lens selection in Phase 2.
3. **Write the default answer** — the conventional, competent take any informed
   person would give. This is the baseline. *Novelty is measured against it.*
   Without a named default, everything looks fresh and nothing actually is. This
   step is non-negotiable; it's what keeps the matrix honest.

### Phase 2 — Build the two axes

- **Rows = anchors.** Decompose the subject into **4–7 anchors**: its core
  components, load-bearing assumptions, key variables, stakeholders, or
  sub-questions. Anchors must be specific to *this* problem and roughly
  non-overlapping. Generic anchors ("people," "technology") produce generic
  cells. Aim for the things that, if they changed, would change everything.
  To find them, list the question's moving parts, then keep only rows that pass
  two tests: **load-bearing** ("if this changed, would the answer change?") and
  **problem-specific** ("could this exact row appear in an unrelated problem's
  matrix? If yes, sharpen it until it couldn't"). The strongest anchors are
  usually hidden assumptions, mechanisms, and points of tension — note that the
  worked examples' anchors ("the moment of writing," "shared context," "what
  'good' means") are all mechanisms or assumptions, never categories.
- **Columns = lenses.** Choose **5–8 reasoning lenses** from the catalog below.
  Don't use all of them; pick the ones suited to the insight type. See
  `references/operators.md` for the full catalog, a guiding question per lens,
  worked mini-examples, and which lenses fit which insight type.

Compact lens catalog (full versions in the reference file):

| Lens | Forcing question |
|---|---|
| **Essence** | Strip the label — what is this thing *actually*, underneath the word for it? Run early; it primes the rest. |
| **Inversion** | What would guarantee the opposite outcome? Flip the goal. |
| **First principles** | Strip to fundamentals — rebuild ignoring how it's "done." |
| **Cross-domain transfer** | Import a mechanism from another field — *near* (adjacent subfield) or *far* — onto this object. The skill's primary engine. |
| **Enabling shift (why now)** | Which idea, once dismissed as impractical, does a recent change in cost/capability now make viable? |
| **Scale shift** | What changes at 100× bigger, 1/100th, or a different time horizon? |
| **Constraint play** | The pure *"what if?"* — remove a limit, treat the wall *as* the problem to solve, or *add* a brutal one. |
| **Second-order** | Consequences of the consequences. Who adapts, and how? |
| **Adversarial** | How would a hostile party exploit or break this? |
| **Reframe the unit** | Change the basic object: individual→system, event→process, noun→verb. |
| **Temporal shift** | View from the deep past or far future. What's transient vs. permanent? |
| **Stakeholder inversion** | See it through the eyes of the party usually ignored. |
| **Edge case** | Push to the extreme where the normal logic breaks. |
| **Substrate** | What must be true *underneath* for the surface phenomenon to hold? |
| **Naive narration** | Explain it step by step, jargon-free, to someone with zero context — the step you rush or hand-wave is the cell. The one lens that shifts the *register*, not the subject. |

### Phase 3 — Populate the matrix

For each (anchor × lens) cell, write **one terse candidate move** — an
observation, a question, a reframing. One line each. Speed over polish here; the
filter comes next.

Be honest about empty cells. Not every intersection yields something — mark dead
or trivial cells with `—` and move on. A grid that's 40% empty but has six live
cells is a success. Forcing every cell to say something is how you manufacture
noise.

Render the populated grid as a markdown table (anchors as rows, lenses as
columns) so the user can see the raw move-space before the filter.

### Phase 4 — Score and filter

Rate each non-empty cell on two independent axes, Low / Med / High:

- **Novelty** — how far does it depart from the Phase 1 default?
- **Validity** — does it survive a first round of scrutiny? Is it plausibly true?

The two axes are independent on purpose, and the filter's job is **not** to tame
the wild cells — it's to keep the cells that are *both* wild and true and route
the rest honestly. A bold, non-linear move with real validity is the whole point;
a bold move with no validity isn't trash, it's a Provocation (kept, labeled). The
probes below exist to stop *vacuous* novelty from masquerading as insight, never
to push you back toward the safe linear answer.

**Probe Validity — don't just rate it.** Self-scored validity is the softest
joint in the method: the same judgment that generated a clever-sounding cell will
happily rate it High. Run these three cheap checks first; they're mechanical
enough to catch yourself:

- **Reversal test** (the vacuous-profundity killer): state the cell's opposite. If
  the opposite sounds *equally* profound, the cell asserts nothing testable — cap
  Validity at Low. ("Complexity is the default physics of writing code" passes:
  its opposite is plainly false. "Great teams are built on trust" fails: the
  mirror sounds just as wise.)
- **Mechanism in one sentence:** can you say *why* it's true without hand-waving?
  No nameable mechanism → Med at best.
- **Named falsifier:** can you state a concrete observation that would prove it
  false? If nothing could, it isn't valid-but-unproven, it's *unfalsifiable* —
  that's a Provocation, not an Insight.

Then sharpen Validity with the test that fits the insight type (the mirror of the
per-lens failure modes in `references/operators.md`):

| Insight type | Validity test — the cell must survive it |
|---|---|
| **Causal** | Name a confound that would produce the same effect *without* your mechanism. If one fits, validity drops. |
| **Design** | Name how the built thing fails in practice. Can't find a failure mode because it's vague? That's a vagueness tell, not a strength. |
| **Strategic** | Run Adversarial on your *own* move: name who adapts and defeats it. |
| **Conceptual** | Does it *pay rent* — change what you'd expect or do? A reframing that changes no prediction is a relabel. |
| **Predictive** | What's the base rate, and what does the null/default predict instead? A claim that doesn't beat the null isn't predictive. |

**Ground the recall-dependent cells before you score them.** Some cells rest on a
*factual* claim about the world, not just a reasoning move — and the model's
parametric memory of that fact may be lossy, stale, or confidently wrong. Scoring
such a cell High on Validity from memory is the method's blind spot: it launders
a half-remembered fact into a "validated insight." Flag any cell whose validity
turns on an empirical claim and **verify it with research/web search before
rating** — or, if you can't, cap its Validity and label it *ungrounded*. Treat
this as a hard gate: **a recall-dependent cell may not hold a High on memory
alone.** Either an external check confirms it or it's capped — because
introspection is precisely the instrument this blind spot blinds, and a signal
from outside the model is the only thing that reliably clears it. The
high-risk lenses:

- **Enabling shift (why now)** — inherently about a *recent* change in
  cost/capability. This is the most recency-sensitive cell in the whole grid;
  recall is least trustworthy here. Confirm the enabler actually arrived.
- **Cross-domain transfer** — the claim "field X solves this with mechanism M"
  must be *true of field X*, not a plausible-sounding guess about it.
- **Predictive** — base rates are facts, not vibes. Look them up.
- **Adversarial** — "an attacker would do Z" rests on whether Z is a real,
  current technique.

This is what keeps a less knowledge-saturated model honest: it can't *recall* as
much, so it must *ground* what it reasons over — and a grounded, cited claim beats
a confidently-remembered one. When grounding isn't available (no tools, offline),
say so and treat these cells as Provocations, not Insights. See the deep-research
skill for the fan-out-and-verify pattern when a cell needs real sourcing.

**Scrub self-preference before you commit a High (the demotion pass).**
Self-scored Validity is the softest joint in the method, and it fails in one
predictable direction: the same judgment that generated a clever cell rates its
*own* cleverness generously — the more fluent the cell, the stronger the pull.
You cannot fix this by re-rating. A second look from the same seat inherits the
same fondness, and an *unconstrained* "reconsider" pass is actively dangerous —
it can talk itself into promoting noise it now finds appealing, which is how
naive self-critique makes an answer worse than the first guess. So make the
second pass **adversarial and one-directional**:

- Take every cell you're about to mark High validity — the INSIGHTs, plus any
  High CONFIRMATION feeding a synthesis — and switch seats. Stop defending it;
  try to *break* it. Argue it's wrong, trivial, or a relabel, as a skeptic who
  didn't write it would.
- The pass may only **lower** a score, never raise one. A cell that survives a
  real attempt to break it keeps its High; one that wobbles drops to Med or
  becomes a Provocation. Nothing is promoted on reconsideration. This asymmetry
  *is* the safeguard: the pass's only possible error is being too strict, which
  costs you a candidate, not your credibility — so unlike an open self-critique
  loop, it can never introduce a false positive.
- If the strongest attack you'd mount is one you already ran (reversal /
  mechanism / falsifier), you're done — those *are* the break attempts. The
  demotion pass is for the cells that passed those and *still* feel too good:
  the ones your own fluency is most likely shielding.

This runs even on a light grid — it's just switching stance on the two-to-six
cells you kept, not new machinery. And it can't be waived on the strength of "I
scored honestly the first time": honesty was never the failure mode here —
fluency is. A well-made cell reads as valid because it reads well.

Then place each cell in the quadrant:

- **High novelty × High validity → INSIGHT.** Keep. These feed Phase 5.
- **High novelty × Low validity → PROVOCATION.** Flag separately. Do not present
  as truth; present as "worth probing." Honest about its status.
- **Low novelty × High validity → CONFIRMATION.** Discard for insight purposes
  (it's just the default restated), but note if it anchors a synthesis.
- **Low × Low → NOISE.** Discard silently.

Most cells are noise or confirmation. That's expected and fine. The grid's job is
to make the few real cells findable.

And sometimes *everything* is. If no cell clears the bar, the deliverable is the
validated default, stated plainly, plus any Provocations — a null result is the
method working, not failing (a matrix that always pays out is a bullshit
generator; see the second, null run in `references/worked-example.md`). Never
lower the bar to save the grid.

### Phase 5 — Synthesize (where the real insight lives)

The biggest insights are usually **not** single cells — they're convergences.
When two or three high-value cells, reached by *different lenses*, point at the
same underlying structure, that convergence is the insight, and it's stronger
than any cell alone because it's triangulated.

So actively look for resonance across the kept cells. Then crystallize **2–4
insights**, each stated as:

- **The insight** — one or two sentences, in plain language.
- **Why it's non-obvious** — what default it overturns or sidesteps.
- **What it rests on** — the cells/reasoning supporting it.
- **How it could be wrong** — the condition that would break it, or a test.

**Then distill — but only when the insights genuinely converge.** A convergence
*is* a core variable: when two or three insights triangulate on the same
underlying structure, name that structure as the single lever — the one thing
that, if it moved, would move everything else — and state one **reusable rule of
thumb**: a portable, context-free heuristic the user can carry to the *next*
problem, not just this one. (In the team-scaling example, the core variable is
"synchronized context as a perishable resource"; the rule of thumb is "when a
group slows down, suspect a decaying shared stock before you blame the links
between people.") This is the skill's own relocation move applied to its own
output — it lifts the finding out of this question so it travels.

Two guards, or distillation becomes an anti-pattern:

- **The rule of thumb obeys the Validity axis.** It must be falsifiable and carry
  its own *"...unless"* — a heuristic that asserts nothing testable is
  fortune-cookie noise, exactly what Phase 4 exists to kill.
- **Don't force a single lever onto genuinely plural insights.** If the surviving
  insights point at two or three *distinct* levers rather than one, say so and
  give a rule of thumb per lever. A false "core variable" that collapses real
  multiplicity is worse than none. Distillation is optional; skip it when the
  insights don't converge.

### Phase 6 — Stress test, then deliver

For each candidate insight, steelman the opposite and ask what would falsify it.
This is not the demotion pass repeated: that pass attacked individual *cells*;
this one attacks the *synthesis*. In particular, check each convergence's
provenance — did the converging cells really come from different reasoning
moves? Two lenses that are secretly the same move landing on the same cell isn't
triangulation, it's one path counted twice, and the "insight" is unsupported.
Drop any that collapse. Surviving insights are the deliverable. Lead with them.
The matrix itself goes *below* the insights (or in a collapsed/secondary section)
— the user wants the building, not the scaffold, but the scaffold should remain
inspectable.

## Output structure

ALWAYS deliver in this order:

```
## Insights
[2–4 crystallized insights, each with the four-part structure. This is the answer.]

## Distilled   (only when the insights converge on one lever)
[the core variable — the single dominant lever — and one reusable, falsifiable
rule of thumb the user can carry to the next problem. Omit entirely if the
insights are genuinely plural.]

## Provocations worth probing   (only if any survived Phase 4)
[high-novelty / unproven cells, clearly marked as unproven]

## The matrix
[the inquiry, the named default, and the populated + scored grid, so the
reasoning is fully inspectable]
```

On a null run (nothing survived Phase 4), the structure inverts honestly: lead
with the validated default as the answer — that *is* the finding — then any
Provocations, then the matrix.

## Anti-patterns (the ways this method fails)

- **Vacuous profundity.** Cells that sound deep but assert nothing testable.
  The Validity axis exists to kill these — apply it honestly.
- **Committing a High you never tried to break.** Self-scored Validity inherits
  the writer's fondness for their own cleverness, and that pull grows with how
  fluent the cell reads. Every High must survive the demotion pass — an
  adversarial, one-directional second look that can only lower a score — before
  it counts as an Insight.
- **Skipping the default.** Without Phase 1's baseline, every cell scores High
  novelty and the filter becomes meaningless. This is the most common failure.
- **Filling every cell.** Manufactured noise. Empty cells are honest.
- **Presenting the grid as the answer.** The grid is process; insights are
  product. Don't make the user mine the matrix themselves.
- **Lens monoculture.** Using five lenses that are secretly the same move
  (all variants of "what if it were bigger"). Diversity of lens is what makes
  cross-cell convergence meaningful.
- **Generic anchors.** "People / process / technology" produces a matrix of
  platitudes. Anchors must be load-bearing and specific.
- **False distillation.** Collapsing genuinely plural insights into one "core
  variable" that isn't really there, or offering a rule of thumb that asserts
  nothing testable. Distill only on real convergence; the rule of thumb must be
  falsifiable.

## Compact worked example

**Inquiry:** Why do experienced engineers keep writing over-engineered code even
when they know simplicity is better? (insight type: causal)

**Default:** "They gold-plate out of perfectionism / résumé-driven design / not
enough time pressure." Competent, and the thing we want to get past.

**A few live cells:**

- *Anchor "the moment of writing" × Inversion:* What would guarantee simple code?
  → Being forced to delete, not add. Insight seed: complexity is the **default
  physics** of writing — addition is frictionless, removal requires a separate
  deliberate act that nothing in the workflow prompts.
- *Anchor "the engineer's incentives" × Temporal shift:* From the far future,
  which code looks smart? → The code that was easy to change. Seed: engineers
  optimize for *looking* competent now (handling cases), which is the opposite of
  *being* competent later (changeability).
- *Anchor "what 'good' means" × Substrate:* What must be true underneath for
  over-engineering to feel correct in the moment? → That imagined future
  requirements are as real as present ones. They aren't — but the brain prices
  them identically.

**Convergence → Insight:** Over-engineering isn't a character flaw or a time
problem; it's a **pricing error**. The engineer's mind charges the same price to
imagined future requirements as to present real ones, while the cost of
complexity is paid immediately and the payoff is hypothetical. *Why non-obvious:*
the default blames the person (perfectionism); this blames a systematic
mispricing anyone rational would make. *Rests on:* the inversion, temporal, and
substrate cells converging. *Could be wrong if:* engineers who explicitly forecast
requirement-change rates over-engineer just as much — that would point back to
disposition over pricing.

This is the shape every run should produce: a small number of insights that
genuinely move past the default, each traceable to the cells that generated it
and each honest about how it might fail.

## Chaining matrices (advanced)

Feeding the kept insights of one matrix in as the anchors of the next (escalating
causal → strategic → design) turns the method from one-shot analysis into
recursion: you interrogate your own conclusions instead of stopping at them.
Reach for it when one matrix's output is itself a question worth attacking. Two
disciplines keep a chain honest and are worth stating plainly:

- **Order matters.** Diagnose-then-decide lands somewhere different from
  decide-then-diagnose. Pick the order deliberately and say why.
- **Contract, don't stack.** Only the *kept insights* of matrix A become anchors
  of B; everything else is dropped. Crossing every A-cell with every B-cell isn't
  chaining, it's a combinatorial noise factory. This is the one trap that sinks it.

The full treatment — including lens-fusion and cross-matrix convergence — is in
`references/composition.md`.

## Reference files

- `references/operators.md` — full lens catalog: a forcing question and mini-example
  for each lens, plus which lenses to favor per insight type. Read it when
  selecting lenses in Phase 2 or when a lens isn't producing live cells.
- `references/worked-example.md` — one complete end-to-end run (full grid, scoring,
  synthesis) on a non-trivial question. Read it for a model of the full workflow.
- `references/composition.md` — chaining matrices (A→B), fusing lenses, and
  cross-matrix convergence. Read it when one matrix's output is a question worth
  attacking, or when escalating causal → strategic → design across stages.
