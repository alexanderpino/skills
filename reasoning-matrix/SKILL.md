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
forced move. The point of the grid is structured surprise — and then a ruthless
filter so only the cells that are *both new and defensible* survive.

The output is **2–4 crystallized insights**, not a wall of cells. The matrix is
scaffolding; the user sees the building.

## When the matrix earns its cost

Use it for questions where the conventional answer exists and is unsatisfying —
"why does X keep happening," "what are we missing about Y," "what's a better way
to think about Z," strategy under uncertainty, design problems with no clean
spec, conceptual or causal puzzles. Skip it for anything with a single correct
answer or where the user just wants a fact. If you're unsure what kind of insight
is wanted, ask one question, then proceed.

## The method: six phases

Run these in order. Phases 1, 4, and 5 are where quality is won or lost — do not
rush them to get to a full grid.

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
- **Columns = lenses.** Choose **5–8 reasoning lenses** from the catalog below.
  Don't use all of them; pick the ones suited to the insight type. See
  `references/operators.md` for the full catalog, a guiding question per lens,
  worked mini-examples, and which lenses fit which insight type.

Compact lens catalog (full versions in the reference file):

| Lens | Forcing question |
|---|---|
| **Inversion** | What would guarantee the opposite outcome? Flip the goal. |
| **First principles** | Strip to fundamentals — rebuild ignoring how it's "done." |
| **Cross-domain transfer** | Import a mechanism from a distant field (biology, markets, physics, music). |
| **Scale shift** | What changes at 100× bigger, 1/100th, or a different time horizon? |
| **Constraint play** | Remove a fixed limit — or *add* a brutal one. What becomes possible? |
| **Second-order** | Consequences of the consequences. Who adapts, and how? |
| **Adversarial** | How would a hostile party exploit or break this? |
| **Reframe the unit** | Change the basic object: individual→system, event→process, noun→verb. |
| **Temporal shift** | View from the deep past or far future. What's transient vs. permanent? |
| **Stakeholder inversion** | See it through the eyes of the party usually ignored. |
| **Edge case** | Push to the extreme where the normal logic breaks. |
| **Substrate** | What must be true *underneath* for the surface phenomenon to hold? |

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

Then place each cell in the quadrant:

- **High novelty × High validity → INSIGHT.** Keep. These feed Phase 5.
- **High novelty × Low validity → PROVOCATION.** Flag separately. Do not present
  as truth; present as "worth probing." Honest about its status.
- **Low novelty × High validity → CONFIRMATION.** Discard for insight purposes
  (it's just the default restated), but note if it anchors a synthesis.
- **Low × Low → NOISE.** Discard silently.

Most cells are noise or confirmation. That's expected and fine. The grid's job is
to make the few real cells findable.

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

### Phase 6 — Stress test, then deliver

For each candidate insight, steelman the opposite and ask what would falsify it.
Drop any that collapse. Surviving insights are the deliverable. Lead with them.
The matrix itself goes *below* the insights (or in a collapsed/secondary section)
— the user wants the building, not the scaffold, but the scaffold should remain
inspectable.

## Output structure

ALWAYS deliver in this order:

```
## Insights
[2–4 crystallized insights, each with the four-part structure. This is the answer.]

## Provocations worth probing   (only if any survived Phase 4)
[high-novelty / unproven cells, clearly marked as unproven]

## The matrix
[the inquiry, the named default, and the populated + scored grid, so the
reasoning is fully inspectable]
```

## Anti-patterns (the ways this method fails)

- **Vacuous profundity.** Cells that sound deep but assert nothing testable.
  The Validity axis exists to kill these — apply it honestly.
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

## Composing matrices (advanced)

A reasoning matrix is a *transformation*: it maps a question to a set of insights.
Transformations compose — and the faithful analog of matrix multiplication is
exactly that composition, not anything numeric. This is what turns the method
from one-shot analysis into recursion: you interrogate your own conclusions
instead of stopping at them. Reach for it when one matrix's output is itself a
question worth attacking.

### Main form: composition by contraction (A then B)

Feed the **kept insights of matrix A in as the anchors of matrix B**. The
intermediate insights are the shared axis — and, crucially, they're *contracted
away*: B doesn't re-report them, it transforms them. The chain reads
"question → insights → implications" as a single operation.

The natural use is **escalating the insight type** at each link, each link with
its own lenses:

- Matrix 1 (causal): "what's actually true here?"
- Matrix 2 (strategic): takes M1's insights as anchors → "so what should we do?"
- Matrix 3 (design): takes M2's insights as anchors → "so how do we build it?"

**Worked link.** The compact example above produced M1's insight: *over-engineering
is a pricing error — imagined future requirements are priced like present real
ones.* Make that an anchor of a **strategic** matrix:

- Anchor: "the mispricing of future requirements"
  - × *Constraint play (add a brutal limit):* require every speculative feature to
    name the present customer paying for it now → speculative complexity has no
    sponsor and dies on its own.
  - × *Adversarial:* a rival ships the dumb version first and learns the real
    requirements from the market you were imagining → speed beats foresight.

The strategic insights that fall out are ones M1 could not produce, because M1's
job was diagnosis, not action. That's composition doing real work.

**Two rules that keep composition honest:**

- **It's non-commutative.** A-then-B ≠ B-then-A, exactly as with real matrices.
  Diagnose-then-decide and decide-then-diagnose land in different places. Order is
  a deliberate modeling choice, not a detail — pick it on purpose and say why.
- **Contract, don't stack.** The intermediate axis must *disappear*. If you keep
  every M1 cell and cross it with every M2 cell, you haven't composed — you've
  built a tensor that explodes combinatorially (every decomposition × every other
  decomposition) into a noise factory. Only the *kept insights* of A survive as
  anchors of B; everything else is summed away. This is the single trap to avoid.
- **Beyond two stages, depth must earn itself.** Cascading (A→B→C…) is just
  repeated contraction and works, but each stage is lossy — you keep ~3 of N
  cells — so it's a telephone game: anchor the final judgment to the *root*
  question, not the last stage. Two asymmetries bite past stage two. Raise the
  validity bar on *early* stages (a stage-1 Provocation slipping through as an
  Insight poisons everything downstream). And add a relevance tether: each stage
  checks against the root, not only local novelty, or you spiral into
  locally-novel but globally-useless abstraction. Stop the moment a stage no
  longer beats its own default, or you've drifted from the root.

### Light form: composing lenses (the inner move)

You can also multiply *within* one matrix by fusing two lenses into a single move:

- Temporal × Adversarial → "how would a *future* adversary exploit this?"
- Scale shift × Stakeholder inversion → "at 100×, what does the ignored party live?"
- Inversion × Substrate → "what hidden precondition would *guarantee* the opposite?"

Fused lenses generate genuinely new columns for free and reach cells neither lens
finds alone. Use sparingly — two well-chosen fusions beat a grid of forced ones.

### Convergence is already a product

When two independently-run matrices score the *same* cells high, that's an
elementwise (Hadamard) agreement — and it's strong evidence, much harder to fake
than agreement inside a single grid. You need no new machinery: it's the
cross-cell triangulation of Phase 5, applied across matrices instead of within
one. Treat cross-matrix convergence as the most trustworthy signal the method
produces.

### What not to build

Do not literally multiply prose cells — score×score, or splicing two cells' text
together as if that were a product. There's no clean semantics under it; it's the
decorative analogy this method explicitly warns against. If a "multiplication"
doesn't correspond to either composition-by-contraction or lens-fusion, it's
sugar, not structure — drop it.

## Reference files

- `references/operators.md` — full lens catalog: a forcing question and mini-example
  for each lens, plus which lenses to favor per insight type. Read it when
  selecting lenses in Phase 2 or when a lens isn't producing live cells.
- `references/worked-example.md` — one complete end-to-end run (full grid, scoring,
  synthesis) on a non-trivial question. Read it for a model of the full workflow.
