# Composing Matrices (advanced)

A reasoning matrix is a *transformation*: it maps a question to a set of insights.
Transformations compose — and the faithful analog of matrix multiplication is
exactly that composition, not anything numeric. This is what turns the method
from one-shot analysis into recursion: you interrogate your own conclusions
instead of stopping at them. Reach for it when one matrix's output is itself a
question worth attacking.

## Main form: composition by contraction (A then B)

Feed the **kept insights of matrix A in as the anchors of matrix B**. The
intermediate insights are the shared axis — and, crucially, they're *contracted
away*: B doesn't re-report them, it transforms them. The chain reads
"question → insights → implications" as a single operation.

The natural use is **escalating the insight type** at each link, each link with
its own lenses:

- Matrix 1 (causal): "what's actually true here?"
- Matrix 2 (strategic): takes M1's insights as anchors → "so what should we do?"
- Matrix 3 (design): takes M2's insights as anchors → "so how do we build it?"

**Worked link.** The compact example in SKILL.md produced M1's insight:
*over-engineering is a pricing error — imagined future requirements are priced
like present real ones.* Make that an anchor of a **strategic** matrix:

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

## Light form: composing lenses (the inner move)

You can also multiply *within* one matrix by fusing two lenses into a single move:

- Temporal × Adversarial → "how would a *future* adversary exploit this?"
- Scale shift × Stakeholder inversion → "at 100×, what does the ignored party live?"
- Inversion × Substrate → "what hidden precondition would *guarantee* the opposite?"

Fused lenses generate genuinely new columns for free and reach cells neither lens
finds alone. Use sparingly — two well-chosen fusions beat a grid of forced ones.

## Convergence is already a product

When two independently-run matrices score the *same* cells high, that's an
elementwise (Hadamard) agreement — and it's strong evidence, much harder to fake
than agreement inside a single grid. You need no new machinery: it's the
cross-cell triangulation of Phase 5, applied across matrices instead of within
one. Treat cross-matrix convergence as the most trustworthy signal the method
produces.

## What not to build

Do not literally multiply prose cells — score×score, or splicing two cells' text
together as if that were a product. There's no clean semantics under it; it's the
decorative analogy this method explicitly warns against. If a "multiplication"
doesn't correspond to either composition-by-contraction or lens-fusion, it's
sugar, not structure — drop it.
