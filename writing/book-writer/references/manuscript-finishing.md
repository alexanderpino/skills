# Manuscript finishing

The phase between "all chapters are drafted" and "assemble the deliverable." Three things happen here that don't belong in per-chapter writing and don't belong in mechanical assembly:

1. **Manuscript-level revision** — revision passes over the whole book, each with its own focus, distinct from per-chapter self-critique
2. **Introduction / preface / foreword** — written last, because only now is it clear what the book has become
3. **Title and subtitle** — finalised here, tested against the finished book, not against the intake fantasy of it

These three belong together because they all require the finished manuscript to be done well. You cannot write a truthful introduction to a book you haven't finished writing. You cannot pick a great title from a working title when you don't yet know what the book is actually about. You cannot do a manuscript-level revision until there's a manuscript.

Read this file at the start of Phase 5 (Manuscript finishing). Work through the three parts in order: revision first, then introduction, then title. Each has its own process and artefacts.

---

## Part 1 — Manuscript-level revision

Per-chapter self-critique (described in `writing-craft.md`) catches issues within a chapter. Manuscript-level revision catches issues across chapters — the things that only become visible when you look at the whole book.

Revision is not one pass. It's three, each with a different focus. Doing them as one pass is how you miss things: structural problems get lost in the search for typos, sentence-level clumsiness gets lost in the search for structural problems.

### Pass A — Structural revision

**Goal:** does the book's architecture actually work?

This pass is about chapter order, chapter weight, and whether the book delivers what it promised.

Check, for the whole book:

- **Does the opening earn the reader's commitment?** Re-read the preface and chapter 1 after the book is done. Do they actually prepare the reader for what follows? Do they over-promise? Under-promise? A great book's opening rereads well *after* the book.
- **Does the closing land?** Re-read the final chapter. Does it synthesise, extend, or undermine what came before? If it's a technical or didactic book, does the final chapter leave the reader where the book promised?
- **Is each chapter the right weight?** A 40-page chapter 3 followed by a 12-page chapter 4 often means chapter 3 is trying to do too much. Look at the page/word count distribution. Outliers in either direction usually indicate structural issues.
- **Is anything missing that the outline promised?** Walk the outline chapter by chapter. Did every promised chapter get written? Did each cover what its outline block said it would? Gaps that "we'll cover later" sometimes never get covered.
- **Is anything there that doesn't belong?** Sometimes chapters that made sense in the outline don't earn their place in the finished book. Better to cut 15 pages than to pad a weak chapter.
- **Does the throughline run?** If the outline promised a running example or a narrative throughline, does it actually run through the chapters — including the ones where it's less load-bearing? Or does it appear in chapter 2, disappear for chapters 3–6, and return in chapter 7?
- **Does the handoff-to-next-chapter pattern work at scale?** Chapter endings and openings are the joints of the book. Strong joints feel continuous; weak joints feel like the chapters were written in isolation (often because they were).

**Output:** a `revision-structural.md` document listing issues found and decisions made. For each issue: what's wrong, what the options are, what gets changed.

**What gets changed:** chapter order, chapter scope, cuts, additions. These are big changes. Don't shy away from them, but think before you move — a re-ordered book is harder to revise than a moved chapter.

### Pass B — Line revision

**Goal:** does every sentence earn its place?

This pass is about prose quality, sentence-level clarity, paragraph flow, and voice consistency across the whole book.

Work through the manuscript from start to finish, reading for:

- **Sentences that could be cut.** Most manuscripts have 10–20% fat. Not big chunks — individual sentences that restate what the previous sentence said, phrases that hedge unnecessarily, transition sentences that aren't needed.
- **Paragraphs that could be combined or split.** Dense paragraphs often want splitting. Short paragraphs in series often want combining.
- **Voice drift.** Is the persona's voice consistent across all chapters? Did chapter 8 (written in a different session) drift into a different register? Flag drift and realign.
- **Repetition across chapters.** Did you introduce a concept in chapter 4 and then re-introduce it in chapter 8 as if for the first time? Did the same anecdote appear twice?
- **Overused words and phrases.** Every writer has them. Find yours across the manuscript — often "just", "really", "actually", "essentially", "in some sense", or specific metaphors you liked. Cut most instances.
- **Weak openings and closings.** Chapter openings and closings are high-value real estate. Any opening that reads "In this chapter we will..." or closing that reads "In summary, we have seen..." is a missed opportunity.
- **Long sentences that unravel.** Sentences with three nested clauses often want breaking. Sometimes they work; sometimes they don't.

**Output:** revision happens in-place (edits to chapter files). A `revision-line.md` document records patterns (overused words that got cut, voice-drift chapters that needed realignment) for future reference.

**What gets changed:** words, sentences, paragraphs. No chapter-level moves here — those were Pass A.

### Pass C — Copy-edit pass

**Goal:** the book is clean.

This is the detail pass. Technical errors, not creative judgements.

- **Typos, word-order errors, missing words.** The "HLSL is a what the specification calls" class of error.
- **Grammar.** Subject-verb agreement, pronoun clarity, tense consistency (does the book accidentally slip between present and past tense?).
- **Punctuation consistency.** En-dashes vs em-dashes, Oxford comma yes/no, straight vs curly quotes.
- **Capitalisation.** Chapter titles — title case or sentence case? Terms — capitalised on first use only, or everywhere? Be consistent.
- **Number formatting.** Digits vs words ("12" vs "twelve"), unit spacing ("10 km" vs "10km"), thousands separators. Follow a style guide or be internally consistent.
- **Hyphenation.** Compound modifiers ("well-defined" vs "well defined"), book-specific compound terms (is it "real-time" or "real time"?). Pick one and apply throughout.
- **Cross-reference text.** "As we saw in chapter 3" — did chapter 3 actually cover that, and was it called that? Especially important if Pass A moved chapters.

This pass is ideal for a script rather than manual eyeballing. Spell-checkers catch some. Style-linters (e.g., Vale, proselint) catch more. For long books, writing a project-specific linter that knows your capitalisation conventions, your preferred terms, your forbidden phrases is worth the half-hour it takes.

**Output:** clean manuscript. `revision-copy.md` records patterns found if useful for future books.

### Running the three passes

Do them in order: A, then B, then C. Each pass takes the manuscript from the previous one.

Don't skip A to get to B. Structural issues found late are expensive — if you do a perfect line-revision of a chapter that turns out to need cutting, you wasted the revision.

Don't do all three in one pass. The mental modes are different. Structural revision requires stepping back; copy-edit requires stepping in. Switching constantly is worse than switching once.

**For demo/first-pass scope**, often only Pass A is done thoroughly, with B and C deferred until the book approaches production. That's acceptable as long as the user knows.

**For production**, all three are done, in order, with real rigour. Pass C especially benefits from a break between manuscript completion and the copy-edit — a week of distance, if the schedule allows, produces a far better copy-edit than doing it immediately.

---

## Part 2 — Introduction, preface, or foreword

The introduction is written last. Not because it's unimportant — because you can't write a good one until you know what you're introducing.

### Which one(s)?

Three related but distinct frontmatter pieces:

- **Preface** — written by the author. About the book itself: why it exists, what the reader should expect, what prior knowledge is assumed, how to use the book. Usually 2–6 pages. Most non-fiction books benefit from a preface.
- **Foreword** — written by *someone other than* the author. Usually a respected figure in the field who vouches for the book and contextualises it. Usually 1–3 pages. Optional. For AI-generated books, a foreword is unusual unless the user has a specific person in mind.
- **Introduction** — the author's first chapter, often labeled "Introduction" rather than "Chapter 1." More substantive than a preface — it starts the actual content. Academic and reference books often have introductions that run 20+ pages. Popular-technical books rarely have them (chapter 1 does that work).

Most books need a preface and nothing else. Textbooks and academic books often have a preface *and* an introduction. Popular-technical books usually have only a preface, or nothing explicit at all.

The choice is set at intake (in the apparatus section), but **revisited here**, because the book you have now may be different from the book you imagined.

### Writing the preface

The preface does, roughly, three things:

1. **Establishes why the book exists.** The personal or intellectual motivation. For the HLSL book, Alexander's "I drowned in complexity and wrote the book I needed." For a biography, why this life. For a technical book, why this topic now.
2. **Sets expectations for the reader.** Who is this for, what does it assume, what does it promise. The "expected prior knowledge" from the didactic block (if enabled) surfaces here.
3. **Explains how to use the book.** Are there exercises? Is there a running example that builds? Can chapters be read out of order? Are there parts the reader can skip?

A preface should be personal without being self-indulgent. The persona's voice is at its most direct here — more first-person than most chapters, more willing to speak from the author's position rather than from inside the material.

**Length:** 2–6 pages. Longer prefaces almost always want to be an introduction chapter instead.

**Style:** The persona's voice, turned slightly warmer and more direct. Paragraphs can be shorter than elsewhere. First-person is expected. One or two paragraphs of genuine personal reflection is fine — more gets self-indulgent.

**What it should not be:**

- A summary of every chapter. Readers can see the table of contents.
- An apology. "This book is far from complete..." undermines the whole thing.
- A defensive pre-emption of criticism. If there are legitimate caveats, state them once, calmly, and move on.
- A marketing pitch. Save that for the back cover.

### Writing structure for the preface

A pattern that works:

1. **Open with a concrete moment or observation.** Not "This book is about X." A moment, a question, a confession that earns the reader's interest.
2. **The personal or intellectual origin.** Why this book, by this author, now.
3. **Who this is for.** One paragraph on the intended reader. Specific. The didactic block's "expected prior knowledge" belongs here if the book has it.
4. **How to use the book.** Practical guidance. Exercises, running examples, chapter independence, required tools.
5. **A short acknowledgement or gesture outward.** Not a full acknowledgements section (that goes in backmatter), but a gesture toward the community or tradition the book sits in.
6. **A brief closing that opens the book.** The last paragraph of the preface should make the reader want to turn to chapter 1.

Write the preface when everything else is done. Then revise it once after a day's distance — prefaces benefit more than any other chapter from being written cold.

### Working with the persona

The preface is where the persona is most visible. Re-read `writer/persona.md` before writing. The persona's formative experience, worldview, hobbyhorses, and voice all inform the preface more than any individual chapter does.

For a persona that uses first person freely (per `first_person: true_prominent` in the persona file), the preface can be quite personal. For a persona that keeps first person minimal, the preface can still use it more than the rest of the book — the preface is the one place where the author's personhood is expected to show.

### Personal introduction forms (if didactic structure is enabled)

If the didactic intake chose a `personal_introduction` value other than `none`, the preface carries it:

- **Biographical** — a passage (one or two paragraphs) from the persona's life that establishes them as a person, not just a name on the cover. Usually early in the preface.
- **Thematic anecdote** — a story from the persona's experience that opens the book's subject. Can be the opening of the preface itself (it often works as the book's very first sentences).

These were recorded at intake but are written here, in the preface, once you know what the book is.

### The introduction (if the book has one)

An introduction is distinct from a preface. It's chapter-scale work. If the outline has an introduction, write it after the preface, not before. Same principle: you need the book finished to introduce its content honestly.

An introduction typically:

- States the book's central question or thesis
- Surveys the territory the book will cover
- Sets up the framework or vocabulary the later chapters assume
- Justifies the book's approach (why this way and not another)

Unlike a preface, an introduction is *intellectual* rather than *personal*. Prefaces are about the author; introductions are about the material.

### The foreword (rarely)

If a foreword is planned, the author does not write it — the foreword-writer does. The skill can draft a brief to send to the foreword-writer (the book's thesis, its intended audience, the author's background) but should not generate the foreword itself unless the user explicitly asks for a placeholder to be replaced later.

---

## Part 3 — Title and subtitle

The working title you started with may or may not be the right title now. This is where you decide.

### Why revisit the title?

A title chosen at intake is a placeholder. It was chosen before the book existed. It reflected your intent, not the finished thing. By the end of the manuscript, several things have probably changed:

- The scope narrowed or broadened during writing
- The book's real centre of gravity emerged — which may not be what the outline said it would be
- The running example or throughline took on a specific shape that suggests a title
- The book found a voice (via the persona) that has a natural title-tone

A good title reflects what the book *became*, not what it was going to be.

### What a title has to do

A non-fiction title needs to:

- **Tell the reader what the book is about.** Clarity beats cleverness.
- **Promise something specific.** Not "A book about shaders" but something that signals the angle.
- **Be memorable.** Readers recommend books by titles they can recall.
- **Match the persona's voice.** A warm-pedagogical persona produces different titles than a rigorous-academic one.

A fiction title needs to:

- **Suggest tone and genre.** A thriller title differs from a literary novel title differs from a romance.
- **Be evocative without being obscure.** Specific enough to mean something, open enough to let the reader project.
- **Be short.** Most great fiction titles are 1–4 words.

### The subtitle

Subtitles do work that titles can't. The title establishes the promise; the subtitle makes it explicit.

For non-fiction, a good subtitle typically:

- **Names the specific audience.** "for Working Programmers" / "for Adults Who Want to Know How Anything Works"
- **Names the specific angle.** "A Historical Introduction" / "A Practical Guide" / "An Honest Account"
- **Resolves ambiguity in the title.** If the title could mean several things, the subtitle picks one

Not every book needs a subtitle. Short evocative titles sometimes need them more than long explanatory titles. A title like "HLSL" benefits from a subtitle; a title like "How to Write a Shader That Actually Works" doesn't.

### Patterns worth knowing

Common title patterns, with examples:

- **[Field]: [angle]** — "HLSL: A Programmer's Guide"
- **[Thing You Already Know] and [Thing You Don't]** — "Code and the City"
- **[Imperative]** — "Think in Systems"
- **[Metaphor]** — "The Black Swan", "The Tipping Point"
- **[Question]** — "Why We Sleep"
- **[Number] [thing]s** — "7 Habits of Highly Effective People"
- **[Field] from [A] to [B]** — "Machine Learning from Scratch"

Patterns aren't prescriptions. A title that breaks every pattern can work if it fits the book.

### Process

1. **Collect the evidence.** Re-read your preface draft. Re-read the first and last chapters. Re-read the outline's "throughline" section. What is this book actually about? Write a one-sentence summary of the finished book, not the outlined book.

2. **Generate 8–15 candidate titles.** This is a brainstorm. Bad titles are fine — they clarify what works by contrast. Include variants on the original working title, variants on the persona's formative experience, variants on the running example, variants on the opening hook.

3. **Generate matching subtitles for the survivors.** Cut the candidate list to the three or four you actually like. For each, draft 2–3 subtitle variants.

4. **Test against the book.** For each candidate title/subtitle: does it match the preface? The first chapter's voice? The book's actual scope? If the title suggests a promise the book doesn't keep, cut it.

5. **Test the shelf-view.** Say the title out loud. Imagine someone hearing it in a conversation and deciding whether to look it up. Imagine it on a bookshelf spine alongside other books in the genre.

6. **Present the shortlist to the user** — two or three finalists, each with rationale. The user picks.

### Titles to avoid

- **Generic field-name titles.** "HLSL" alone is not a title. It's a reference shelf-marker.
- **Titles that assume the reader already knows the angle.** "The New Approach" — what new approach?
- **Titles that over-promise.** "Master X" / "The Ultimate Guide" / "Everything You Need to Know" — these are marketing claims, not titles.
- **Clever titles that don't tell you what the book is about.** Humanities books sometimes get away with this; commercial non-fiction doesn't.
- **Titles that repeat the subtitle.** If the subtitle is "A Programmer's Guide to HLSL", the title "HLSL for Programmers" is redundant.

### Recording the decision

Update `project.json` with the final `title` and `subtitle`. If the final differs significantly from the working title, note the change. Future sessions benefit from knowing the title is settled, not still-working.

---

## Artefacts produced in this phase

By the end of Phase 5, the following should exist:

```
<book>/
├── revision-structural.md        # Pass A findings and decisions
├── revision-line.md              # Pass B patterns (overused words, drift chapters)
├── revision-copy.md              # Pass C patterns (spelling, capitalisation conventions)
├── chapters/                     # edited in place — now at status: reviewed
├── preface.md                    # freshly written
├── introduction.md               # if applicable
└── project.json                  # updated with final title and subtitle
```

The chapters themselves should have their status updated from `draft` to `reviewed` after revision. Assembly (Phase 6) will take them from `reviewed` to `final` after its consistency sweep and citation resolution.

---

## Scope-aware application

- **Demo scope:** Part 1 Pass A only (structural revision), no preface, keep working title. Flag that the book would need full manuscript finishing before production.
- **First-pass scope:** Part 1 Passes A and B, draft a preface, generate 3–5 title candidates. Defer Pass C and foreword.
- **Production scope:** All three passes, full preface (and introduction if planned), title shortlist with rationale, user selects.

The session-scope concept (demo / first-pass / production) isn't formally in the skill yet — when it lands, this phase is one of the biggest beneficiaries, because manuscript finishing's effort scales strongly with intended finish quality.
