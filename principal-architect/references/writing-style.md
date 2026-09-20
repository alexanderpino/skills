# Writing style — prose that reads like an architect, not a generator

The structure rules (`conventions.md`) make docs greppable; this file makes them
worth reading. A document is read many more times than it is written, by people
with less context than the author had — every sentence is either doing work for
that reader or wasting their time. And a doc that *sounds* generated gets treated
as generated: skimmed, distrusted, abandoned. The tone target is a senior
colleague writing carefully for the next engineer — plain, specific, committed.

## The seven rules (SEI)

*Documenting Software Architectures* (Clements, Bachmann, Bass et al., 2nd ed.)
opens with seven rules for sound documentation. Condensed:

1. **Write from the reader's point of view** — their questions, their vocabulary,
   not the author's stream of discovery.
2. **Avoid unnecessary repetition** — one home per fact; link by ID elsewhere.
3. **Avoid ambiguity** — explain your notation (a C4 key, a defined term); an
   unlabeled arrow means five different things to five readers.
4. **Use a standard organization** — the templates; readers navigate by habit.
5. **Record rationale** — the *why* is the part the code can't recover (ADRs).
6. **Keep it current but not too current** — don't document what's still churning;
   do update what settled (`last-reviewed:`, the correspondence rules).
7. **Review for fitness of purpose** — could the intended reader actually use it
   to do their job? That's the only test that matters.

## Voice — where to be neutral and where to commit

- **Context is value-neutral; decisions are committed.** Nygård's original ADR
  prescription: the Context section "is value-neutral. It is simply describing
  facts." Then the Decision commits, in full active sentences: *"We will use a
  file-based event bus."* Never "it was decided that", never "the team may want
  to consider". The same split applies beyond ADRs: describe forces without spin,
  then take a position.
- **A verdict, not a survey.** An options table that ends "each option has
  trade-offs" is analysis theatre. The architect's job is the choice: name the
  loser, say what it would have bought, say why it lost. If you genuinely can't
  decide, say precisely what fact would decide it — that's still a position.
- **Own the uncertainty explicitly.** "We assume ≤ 200 rps until the Q3 launch
  (owner: platform team, revisit ADR-0012)" is honest; "should generally scale
  well" is noise. Hedge with facts and named assumptions, not with adverbs.

## Altitude of language (Hohpe)

*The Software Architect Elevator*: the architect rides between the penthouse
(board) and the engine room (developers) — and the writing must ride with them.
One document, one audience, one altitude of vocabulary. An `enterprise-architecture.md`
that drops into connection-pool sizing has crashed the elevator; an SD that says
"synergies across the digital estate" has too. The altitude you picked for the
artifact (`methods.md` §2) fixes the vocabulary too. When one decision must be
told at two altitudes, write it twice — a two-sentence penthouse summary on top,
the engine-room detail below — rather than averaging them into mush.

## Precision habits (Brown, Fowler, Hohpe)

- **Name responsibilities, not categories.** Brown's C4 discipline: every box
  states what it *does*, every arrow is labeled with what flows. The same applies
  to prose — "the runner executes analysis blocks and writes one result file per
  block" beats "the processing layer handles business logic". If a name ends in
  *Manager*, *Handler*, or *Layer* and you can't say its single responsibility,
  the vagueness is in the design, not just the writing.
- **Numbers over adjectives.** "p99 < 200 ms at 500 rps" is a claim; "highly
  performant and scalable" is decoration. If there is no number, give the bound
  you'd accept ("must survive the nightly 4× batch spike").
- **Guard the vocabulary.** Fowler calls the decay of a term's meaning *semantic
  diffusion*. Define a term once (GLOSSARY.md), then reuse it *exactly* — no
  elegant variation. If "job", "task", and "run" mean the same thing in your doc,
  two of them are bugs. Hohpe's EIP showed what a disciplined vocabulary buys:
  say *Content-Based Router* and stop re-explaining.
- **Example before generality** — Fowler's bliki habit. One concrete walk-through
  ("a 3-block chain on a 40 MB binary…") earns the abstraction that follows it.

## Tells of generated text — and the tests that kill them

The failure mode isn't grammar; it's prose that is true of every system and
therefore says nothing about this one.

- **The any-system test.** If a sentence would survive being pasted into a
  different project's doc unchanged, delete it. "Security is an important
  consideration for this service" fails; "the API accepts unauthenticated
  requests from the office VPN range only (ADR-0009)" passes.
- **No throat-clearing.** Cut "It is important to note that", "In order to",
  "plays a crucial role", "In today's landscape". Start with the fact.
- **No marketing adjectives.** *Robust, seamless, cutting-edge, comprehensive,
  powerful* — if the property matters, it has a `Q.xx` and a number; cite that.
- **Bullets must earn their symmetry.** Three same-shaped bullets that each say
  one vague thing are filler. Merge them into one sentence or make each carry a
  distinct fact. Prefer prose for reasoning; lists for enumerable items.
- **Don't restate the heading** as the section's first sentence, and don't close
  sections with a summary of the section. The reader just read it.
- **Empty sections stay empty.** "N/A — no personal data processed" is complete.
  Padding a section to look finished is worse than a visible gap (`methods.md`:
  record gaps, never fabricate).
- **Committed beats balanced.** Generated text reflexively gives both sides equal
  weight and ends nowhere. See "a verdict, not a survey" above — imbalance is
  information.

## House tone wins

Like every other convention, tone is detected, not imposed: if the org's existing
docs are first-person and informal, or third-person and contractual, match them
(`house-style.md` — terminology and voice are part of the profile). This file is
the default voice for greenfield, and the floor for precision everywhere: house
style may change the register, but it never licenses vagueness.

## The two-minute style pass

Before committing a doc, read only what you changed and ask: does every sentence
state a fact about *this* system, a decision, or a consequence? Would the named
reader know what to do next? Is every claim either numbered, ID-linked, or
flagged as an assumption? Three yeses or keep editing.
