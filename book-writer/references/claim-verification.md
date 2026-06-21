# Claim verification — the discipline of warranted assertions

## What it is

Claim verification is the discipline of ensuring that every factual claim in a piece of writing is either:

1. **Verified from a trustworthy source** the writer has consulted, or
2. **Explicitly marked as inferential, conjectural, or otherwise uncertain**

There is no third category. The book-writer skill must not produce text in which claims that look authoritative are in fact generated from unverified pattern-completion. Such text is the most dangerous output a writing AI can produce, because it carries the appearance of reliability without the substance.

## Why this matters

A reader cannot tell, from the prose alone, whether a claim is verified or generated. The prose looks the same either way. The reader trusts the writer; if the writer is the skill, the skill carries that trust. Producing unverified claims that look verified breaks that trust at scale.

For technical documentation, the cost of unverified claims is concrete: developers waste hours debugging behaviour that does not match the docs. For non-fiction, the cost is intellectual: readers carry away beliefs that are not supported by evidence. For historical fiction, the cost is ethical: real people and real events are misrepresented in ways the reader assumes are warranted.

The discipline is not about being timid or hedging everything. It is about knowing the difference between what one has actually verified and what one has merely produced.

## How the discipline applies in different registers

### Technical documentation

The strictest application. Every claim about behaviour, type signatures, parameter constraints, return values, threading guarantees, performance, or version availability must be verifiable from the source code or from authoritative documentation produced by the maintainers.

Where the source documents the claim, state it. Where the source is silent, either:
- Test it empirically and state the result with the testing context, or
- State explicitly "not specified by the source" rather than asserting a default behaviour

See `technical-documentation.md` for the technical-doc-specific discipline including correctness-verification as a Phase 5 pass.

### Non-fiction (history, journalism, biography, memoir)

Strict application. Every factual claim — dates, places, attributions, events, causal connections, statistics — must come from a documented source. The persona's claimed knowledge cannot exceed the persona's actual access to sources. Daan Verstegen does not know what Hitler thought on a particular morning unless a verifiable source records it.

When the source is silent on a question that the prose addresses, the prose must signal the silence: "we do not know," "it is unclear," "no record survives of his reaction," "later commentators have speculated that..." The discipline distinguishes the documented from the speculative.

### Memoir and personal essay

The persona's own experience is the source. The discipline applies to claims that exceed personal experience — claims about what others thought, claims about historical context, claims about consequences the writer did not witness. These require documented sources or explicit marking.

### Historical fiction

The discipline applies to **the historical baseline**: the actual events, places, dates, and people in the period must be accurately represented unless the work explicitly announces alternate-history. The fictional layer (invented characters, invented dialogue, invented scenes) is acceptable but must not contradict verified historical fact about real people. See `reality-grounding.md` for the broader treatment of factual constraint in fiction.

### Speculative fiction

The constraint is internal rather than external: claims about the world must be consistent with the world's own rules as established. The discipline is to track established rules and refuse to violate them silently. This is the world-bible discipline that already lives in the skill.

### Children's writing

The discipline applies in age-appropriate form. A children's book about animals must not assert that whales are fish or that bees see in colour they cannot see. Simplification for the reading level is allowed; misinformation is not.

## The mark-as-inferential pattern

When a claim is not verifiable but seems worth making, the discipline is to mark it explicitly. Several patterns work:

**For technical writing:**
> "This documentation is based on inference from public interfaces; please verify against the actual implementation before relying on specific claims."

**For history and journalism:**
> "Although no contemporary record confirms this, [scholar X] has argued that..."
> "It is reasonable to suppose, although not documented, that..."
> "We do not know what he said in reply; what is recorded is only that..."

**For all writing:**
> "Likely" / "probably" / "appears to" / "may have" — these signal genuine uncertainty when used precisely. They become problematic when used as filler ("it might perhaps be the case that..." — that is hedge-stacking, not warranted uncertainty).

The discipline distinguishes between these signals when they are warranted (a real epistemic state) and when they are AI-default hedging (cover for not knowing). Real epistemic markers point at specific gaps in the evidence; AI-default hedges sprinkle uncertainty everywhere.

## The verification cycle

For any claim the writer is about to assert, the cycle is:

1. **Recognise the claim.** What am I about to assert? Is it factual?
2. **Trace it to a source.** Where does this come from? Memory? A specific source I've consulted? Pattern completion?
3. **Decide.** If verified, assert. If unverifiable but worth making, mark as inferential. If unverifiable and not central, cut.

For long projects, this cycle becomes habit. For short pieces, it can be applied at the editing pass. For drafts, it is acceptable to write loosely and then verify on revision — but the verification pass must actually happen.

## What the cycle prevents

Three failure modes that AI-generated text exhibits:

- **The plausible fabrication.** A specific date, name, or quotation that sounds right and is invented. AI does this routinely when prompted to produce specific historical detail.
- **The smooth generalisation.** "Many experts believe..." "It is widely held that..." "Studies have shown..." These constructions hide the absence of an actual source behind the appearance of one.
- **The confident over-extension.** A real source supports claim X; the prose extends it to imply Y, which the source does not support. This is harder to catch because there is real grounding, just not where the prose suggests.

The verification cycle catches all three by asking, of each claim: where exactly does this come from?

## Where this discipline integrates

### Phase 0 (Persona)

The persona document specifies the persona's actual sources of knowledge — what they have read, what they have personally witnessed, what fields they have worked in. The persona cannot claim knowledge their formation does not warrant.

### Phase 2 (Preparation)

For non-fiction, the source list is a deliverable. Every projected chapter has source material identified. Without the source list, the chapter cannot be drafted at the correctness level the discipline requires.

### Phase 4 (Writing)

Per-paragraph or per-claim checks during self-critique. For technical documentation: every API claim verified against source. For history: every event-level claim attributed. For fiction with historical baseline: every real-world reference checked against the baseline.

### Phase 5 (Manuscript Finishing)

A dedicated verification pass for non-fiction and technical documentation. For fiction, a fact-check pass on real-world references. The pass is separate from the line-edit and copy-edit passes because its question is different: not "is this well-written" but "is this true."

## Limits of the discipline

The skill cannot independently verify every claim against the world. What it can do is:

- Insist on traceability ("where does this come from?")
- Insist on explicit marking when claims are inferential
- Refuse to generate specific factual detail (specific dates, named people, exact quotations) without a source the user can review
- Flag claims as "needs verification" when the source is the AI's own pattern-matching rather than a documented reference

For ultimate factual correctness, a human reviewer with domain knowledge is required. The skill's role is to produce text that is verifiable, not to be the final verifier.
