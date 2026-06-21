# Outline template

The outline is the contract between the writer and the reader-proxy (the user). Once it's approved, the book's spine is locked — chapters may be polished and expanded, but the architecture shouldn't shift mid-book.

A weak outline produces a weak book. Don't settle for an inhoudsopgave with one-line descriptions. Fill in every field below for every chapter. If a field is genuinely not applicable for the genre, say so explicitly rather than skipping it silently.

---

## Book-level section

```markdown
# [Working title]: [subtitle]

**Genre profile:** [textbook | academic | popular-technical | biography | narrative-history | school-textbook | other: ...]
**Target reader:** [concrete description — not "anyone interested", but "third-year CS undergraduates", "curious adults with no technical background", etc.]
**Primary learning goal:** [what the reader will understand or be able to do after finishing]
**Length target:** [N pages / N,000 words]
**Language:** [nl / en / other]

## The throughline
[2–4 paragraphs. What is the single idea, story, or argument that holds this
book together? What does the reader carry with them when they close it?
For a biography: who is this person, really, and why does their life matter?
For a textbook: what is the field's core insight and what does competence in it look like?
For narrative history: what changed in this period and why does it echo?]

## Pacing curve
[How does the book breathe? Where does it slow down for depth? Where does it
accelerate? A typical curve: easier opening to invite the reader in → dense
middle chapters where the real work happens → a chapter or two that pull
back to synthesis or reflection → a closing that sends the reader off with
something to carry.]

## Opening strategy
[How does the book begin? Preface? In medias res prologue? A small, sharp
chapter that orients without boring?]

## Closing strategy
[How does it end? Synthesis chapter? A return to the opening image? An
epilogue that points outward? A final exercise or challenge?]

## Running example / cross-cutting throughline
[Optional but highly recommended for didactic non-fiction. A running example
is a single case, project, or scenario that threads through every chapter,
growing as the book progresses. For a textbook on compilers: a small
compiler that gets built up, chapter by chapter. For a biography: the
central relationship that the biography returns to. For a technical book
on PBR: a scene that starts unlit and ends physically-based.

Describe:
- What the throughline is (one paragraph)
- Where it starts (what the reader sees in chapter 1 or 2)
- Where it ends (what it's become by the final chapter)
- Which chapters add which pieces to it

If the book has no running example, state "none" explicitly rather than
leaving the section empty. That forces the decision to be deliberate.]

## Didactic architecture (only if didactic structure enabled at intake)
[If the book opted into didactic structure, this section anchors the
book-level learning architecture. Pull from project.json's didactic block.

- **Expected prior knowledge:** what the reader must already know, what's
  helpful, what's explicitly not assumed
- **Overall learning objective:** what the reader can do after finishing
- **Mid-book checkpoint:** what the reader can do at the halfway point
- **Minimum topics to cover:** the non-negotiable list
- **Learning curve:** gentle-throughout / gentle-to-steep / steep-start / uniform / peaked
- **Learning objectives visibility:** per-chapter / book-level / internal-only
- **Exercise scheme:** which exercise types this book uses, where solutions live
- **Required tools:** what the reader needs to follow along
- **Personal introduction:** biographical / thematic anecdote / none

Each of these should be concrete enough that a chapter can be checked against
it. See `references/didactic-structure.md` for details.]
```

---

## Per-chapter section

Repeat this block for every chapter, numbered in order.

```markdown
## Chapter [N] — [Title]

**Opening hook:**
[A specific, concrete thing the chapter opens with. Not "Introduction to X",
but a scene, a moment, a question, a case the reader can picture.
Examples:
- "It's 1843 in London. Ada, now Countess of Lovelace, is translating
  an Italian paper at her desk in Ockham Park..."
- "Your CSV file has 300,000 rows. Three of them are malformed. How
  would you find them?"
- "In 1957, a graduate student named Richard Bellman had a problem..."]

**Learning goal:**
[What will the reader understand or be able to do by the end of this chapter?
One or two sentences, concrete. "Understand X" is too vague — "Be able to
derive the Bellman equation and apply it to a small gridworld" is right.]

**Core arc — the 3 to 7 beats:**
1. [beat]
2. [beat]
3. [beat]
...

(These are not subsection headings — they're the movements of the chapter's
argument or story. A beat might become a subsection, or it might be a single
paragraph within one. The outline captures the *movement*, not the layout.)

**Running example contribution** (if the book has one):
- **State at chapter start:** [what the running example looks like coming in]
- **What this chapter adds:** [the specific thing this chapter builds on it]
- **State at chapter end:** [what it looks like going out]

If the book has no running example, omit this block.

**Learning objectives** (if didactic structure enabled):
By the end of this chapter the reader will be able to:
- [action verb + concrete outcome — see `didactic-structure.md` for verb choices]
- [...]
- [...]

Aim for 3–6 per chapter. Use measurable verbs (explain, implement, recognise,
compare, apply) rather than vague ones (know, understand, be familiar with).

**Assumed prerequisites:** [chapters or concepts the reader must have covered
to follow this chapter. Used in the prerequisite-order check at outline
approval. For chapter 1 this is just "the declared prior knowledge"; for
later chapters it should reference earlier chapters explicitly.]

**Key sources:**
[List of source IDs from sources.json this chapter leans on most heavily.
Not every source in the book — the load-bearing ones for this chapter.]

**Exercises / check-your-understanding** (if didactic structure enabled):
[Short list of what exercises this chapter will have. Exact wording is
drafted during writing; the outline captures count and difficulty.

Example:
- 3 end-of-chapter exercises (1 easy, 1 medium, 1 hard)
- 2 in-text check-your-understanding prompts (after §2.3 and §2.6)
- Solutions: appendix

If the book has no exercises, omit this block.]

**Handoff:**
[How does this chapter set up the next one? What question does it end on, or
what shift does it prepare?]

**Estimated length:** [N pages / N words]

**Visuals (rough):**
[List the things the reader will need to picture in this chapter, and what
form each takes — map, diagram, table, code listing, photo, timeline,
family tree, etc. Use the test from `figures-and-media.md` § "The core
rule": only items where prose alone can't carry the work belong here.

This is a rough early planning step. The detailed visuals plan is
produced just before drafting (see Phase 4 step 2). Outline-level just
needs the rough types and counts — for instance:

- Map of empire's spread by century
- Timeline of major emperors
- 1 family tree of the Julio-Claudian dynasty
- 2-3 diagrams showing administrative reorganisations

For chapters with no figures (philosophical, character-driven, argument-
focused), state "none" rather than leaving blank. That records the
deliberate decision.]

**Notes / risks:**
[Anything specific — a section that will be technically hard, a place where
sources conflict and we'll need to handle it carefully, a section that might
need expert review.]
```

---

## Front and back matter

```markdown
## Frontmatter planned
- [ ] Title page
- [ ] Copyright / credits
- [ ] Dedication — [if any]
- [ ] Table of contents
- [ ] Foreword / preface — [who, or skip]
- [ ] [other]

## Backmatter planned
- [ ] Bibliography — [style: APA / Chicago / MLA / plain]
- [ ] Glossary — [yes / no, and why]
- [ ] Index — [yes / no — usually yes for reference-style books, no for narrative]
- [ ] Endnotes — [if the citation style uses them]
- [ ] Acknowledgements
- [ ] About the author
- [ ] [other]
```

---

## Approval

End the outline document with a literal line for the user to check:

```markdown
---

## Approval

Reviewed by user: [ ] Date: ______
Changes requested: [yes / no — if yes, list them below]
```

Do not proceed to Phase 4 without an explicit "yes, write it" from the user in the chat. The checkbox in the file is a record, not the approval mechanism.

---

## How to use this template

1. Open `project.json` and draw the book-level fields from it.
2. For each research question in `notes/`, ask: does this become a chapter, part of a chapter, or cross-cutting material? Map answers to a chapter list.
3. Fill in the per-chapter blocks. The opening hook and the core arc are the two fields most worth sweating over — they determine whether the chapter will feel alive or dead.
4. Present the full outline in the chat (or as a file, for long books), and ask the user plainly: **"Ready to write, or should we revise?"**
5. Iterate on feedback. Don't be defensive — the outline is cheap to change; a half-written book isn't.

---

## Sanity checks before presenting

Before sending the outline to the user, check:

- [ ] Every chapter has a concrete opening hook (not "Introduction to X")
- [ ] Every chapter has a specific, testable learning goal
- [ ] The total estimated length is within 20% of the target
- [ ] Chapters handoff into each other — there's a reason for the order
- [ ] The throughline actually runs through the chapters, not just the preface
- [ ] Key sources exist in sources.json for every chapter
- [ ] If there's a running example, it grows continuously — no chapter leaves it untouched for long stretches without a reason
- [ ] For textbooks and academic books: exercises or reflection points are planned
- [ ] For biographies and narrative history: the scene-setting isn't all bunched at the start
- [ ] The book has a real ending, not just a last chapter
- [ ] **Visuals check**: every chapter has its **Visuals (rough)** field filled, even if the content is "none". Chapters where the reader is asked to picture geography, structure, relationships among many entities, or simultaneous state should not have an empty visuals field. Apply the test from `figures-and-media.md` to each chapter before approval.

**If didactic structure is enabled, additionally check:**

- [ ] Every chapter has 3–6 learning objectives using measurable verbs
- [ ] **Prerequisite-order check:** chapter N only assumes what chapters 1 to N-1 introduced, plus the declared prior knowledge. No chapter uses a concept before it's been introduced.
- [ ] The mid-book checkpoint promise is actually deliverable from the chapters leading up to it
- [ ] Every item in the "minimum topics" list is covered by at least one chapter
- [ ] The learning curve shape is reflected in the chapter lengths and densities
- [ ] If exercises are planned per chapter, every chapter has an exercise count in its outline block
- [ ] The personal introduction (if planned) is on the frontmatter list and its form (biographical / thematic) is set
