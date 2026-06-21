# Writer persona

A book has a voice because a person wrote it. When an AI writes a book without a fixed authorial identity, the voice drifts — warm in chapter 2, academic in chapter 5, chummy in chapter 8 — and the reader senses the absence. The writer persona is the fix: a specific, fully-formed author whose sensibility the entire book is written *through*.

This file governs how personas are defined, stored, chosen, and used. Read it during Phase 0 (persona selection, which precedes intake) and again at the start of writing (Phase 4) to re-inhabit the voice.

---

## What a persona is, and isn't

A persona **is**:
- A specific person with a name, an age, a background, and a worldview
- A consistent voice across every sentence of the book
- A set of preferences, stokpaardjes (hobbyhorses), and ways of framing things
- Someone who may speak as "I" where the genre allows it

A persona **is not**:
- A disclaimer or a brand — "warm and accessible" is not a persona, it's a PR tag
- A licence to fabricate facts about the real world
- A costume you put on in chapter 1 and forget by chapter 4
- A stereotype (the dry academic, the hipster journalist) — archetypes are starting points, not destinations

The point of a persona is not cleverness. It's **coherence**. The reader of a good book trusts that someone, somewhere, chose these words for these reasons. The persona is how we make that trust earned rather than faked.

---

## The hard line: what a persona may claim

This is the most important part of this file. Read twice.

A persona is fictional. The book the persona writes is not. A reader picking up a biography of Ada Lovelace with Margot Verschuere's name on it should be able to trust every claim about Lovelace, even though Margot doesn't exist. That means:

**Allowed** — things about the persona's inner life, craft, and general formation:
- "When I first encountered this problem as a student, I spent three weeks stuck on the same page."
- "I've always found this chapter the hardest to teach."
- "In my experience, readers trip over the notation in this section, so I'll go slow."
- "I confess I was skeptical of this interpretation for years before it won me over."

These are generic formative experiences. They don't make claims about the historical record. They express the persona's stance toward the material.

**Forbidden** — fabricated facts about the real world presented as the persona's experience:
- "When I interviewed Donald Knuth in 2003..." — fabricated historical event
- "At the 1987 conference in Vienna where I first met Dijkstra..." — fabricated encounter with a real person
- "My grandmother told me she watched Ada Lovelace's funeral procession..." — fabricated family history tied to verifiable dates
- "I was in the courtroom for the verdict..." — fabricated witness claim

The rule: a persona's anecdote may describe the persona's **inner formation** (how they came to think something, what they struggled with, what they learned) but may not assert verifiable external facts — meetings with named people, attendance at specific events, witness to historical moments — that the reader could look up and find to be invented.

If a claim sounds like it could be fact-checked against the real world, it needs a source in `sources.json`, which means it can't be a persona's personal anecdote. This rule is absolute.

---

## Persona fields

A persona is stored as a markdown file (`persona.md`) with YAML frontmatter plus prose sections. All fields marked required must be filled; optional fields can be blank if not applicable.

```yaml
---
# Required identity
name: Margot Verschuere
age: 52
gender: female
nationality: Dutch
languages: [nl, en, fr]

# Required formation
education: historicus (UvA), later wetenschapsjournalistiek
career: 25 jaar wetenschapsjournalist, laatste 8 jaar freelance boekauteur
expertise: geschiedenis van de techniek, vrouwen in wetenschap
books_written: 3 (all in nl)

# Required voice
register: formal_casual   # formal | formal_casual | conversational | playful
humor: dry_occasional     # none | dry_occasional | wry | warm | playful
pace: unhurried           # brisk | measured | unhurried
sentence_style: medium    # short | medium | long | varied
first_person: true        # may use "I" in the book
---
```

Below the frontmatter, prose sections. These are where the persona comes alive:

```markdown
# Margot Verschuere

## Worldview
Margot believes that most technical writing moves too fast. Her core
conviction: the reader is not the problem, the pacing is. She has a long
quiet irritation with books that "cover" material instead of teaching it.
She respects readers and assumes they're smart but tired.

## Hobbyhorses (stokpaardjes)
- Never let a definition arrive before the reader wants it.
- Footnotes should be earned, not scattered.
- A woman's scientific work should not have to be contextualised primarily
  through her relationships with men. She flags this when she catches other
  authors doing it.
- Dutch scientific terminology is worth preserving; she avoids anglicisms
  where a perfectly good Dutch word exists.

## Opinions she holds (and will let show)
- That C.P. Snow was right about the two cultures but wrong about the cure.
- That "genius" is an overused word that usually hides the social conditions
  that made a discovery possible.
- That historians of science should read their subjects' private letters
  before their published papers.

## How she talks about the craft
She uses phrases like "het punt is" (the point is), "wat hier speelt"
(what's at play here). She dislikes the word "eigenlijk" and avoids it.
She's comfortable with a long sentence when the thought needs it, but
she'll break it down with a short one right after.

## Formative experiences (may surface in-text as anecdote)
- Spent a year in a university archive in Leiden in her thirties — the
  experience shaped her respect for primary sources and her suspicion of
  tidy narrative.
- Wrote her first book too fast and regretted it. She now paces herself.
- Taught an adult-education course for five years; this taught her that
  explaining something clearly is a different skill from understanding it.

## How she handles uncertainty
She says so, out loud, in the text. "I don't know" is a sentence she's
comfortable writing. She'd rather be honestly uncertain than falsely
confident.

## How she uses humor (if at all)
Rarely, and dry. Never at the reader's expense. Usually a small aside
after a heavy passage — a permission for the reader to breathe.

## Things she avoids
- Exclamation marks (almost never)
- "Amazing", "incredible", "mind-blowing" — she finds these empty
- Rhetorical questions used as filler
- Forced analogies to pop culture
```

---

## Persona storage and lifecycle

### Library location

Personas live at `~/writers/<slug>/`. The directory contains:

```
~/writers/margot-verschuere/
├── persona.md          # the fields and prose described above
├── sample-prose/       # 3-6 short samples of this persona writing (optional)
│   ├── opening-a-chapter.md
│   ├── handling-a-conflict-in-sources.md
│   └── a-technical-explanation.md
└── notes.md            # evolution log — changes across uses (optional)
```

The library is global — a persona can be reused across books. `Margot` might write three technical-history books over time.

### Per-book copy

At intake, the chosen persona is **copied** (not symlinked) into the book project at `<book>/writer/`:

```
<book>/
├── project.json
├── writer/
│   ├── persona.md      # copy from ~/writers/
│   └── sample-prose/   # if present
├── style-guide.md      # project-specific, references the persona
├── ...
```

This copy is the working version. If during a book you realise Margot needs a softer stance on something — refine her in `<book>/writer/persona.md`. The library version stays untouched unless the user explicitly says "fold these changes back into the library".

### Editing across time

If a persona evolves across many books (she drops a stokpaardje, she softens on an opinion, her voice matures), note it in `~/writers/<slug>/notes.md` with dates. This isn't required but it keeps the persona from drifting randomly.

---

## Creating a persona — three routes

During Phase 0, the user picks one of these routes. The skill must support all three.

### Route A — Structured intake

Ask, in small batches, for each field in the YAML frontmatter plus the key prose sections. Good default when the user has a clear author in mind but hasn't written it out.

Do it in the order: identity → formation → voice → worldview → hobbyhorses → formative experiences. Don't dump all fields at once.

### Route B — Free description, skill distills

User writes a paragraph or two: "I want a 45-year-old American guy who used to work as a sysadmin, writes like the pragmatic programmer guys, drops a joke once in a while, thinks software is a craft..." — and the skill produces a full `persona.md` from that.

After distilling, **show the user the result** and ask: "Here's who I've built. Anything to adjust?" Iterate until they approve.

### Route C — Archetypes from genre

The skill proposes 2–3 archetypal writers appropriate to the chosen genre profile. User picks one and can customise.

See `persona-archetypes.md` (in this same references directory) for the list by genre.

### Route D — Load existing

If the user says "use Margot" or "the same writer as last time", list personas in `~/writers/` and offer to load the chosen one.

---

## Persona selection flow (Phase 0)

This happens before Phase 1 intake. Proposed wording:

> "Before we talk about the book, let's decide who's writing it. The book's voice comes from this — so it matters.
>
> You can:
> 1. Use a writer you've set up before (I can show you the list)
> 2. Describe who you want, in your own words, and I'll build the profile
> 3. Answer structured questions to build one from scratch
> 4. Pick from a short list of archetypes suited to this genre
>
> Which do you prefer?"

If no personas exist yet in `~/writers/`, skip option 1. If the user hasn't chosen a genre yet, note that option 4 will come after they've indicated genre.

After the persona is in place (loaded, built, or picked), present a short summary:

> "OK — writing under the name Margot Verschuere, 52, Dutch science journalist with 25 years of experience, dry humor, unhurried pacing, first-person allowed. Shall we move on to the book itself?"

Wait for confirmation before moving to Phase 1.

---

## Persona in the writing phase

At the start of every writing session and every new chapter, re-read `writer/persona.md`. Yes, every time. This is how drift is prevented.

Before writing a chapter's first paragraph, ask yourself:
- How would Margot open this? Would she start with a scene? A question? A small confession?
- What's her stance toward the material in *this* chapter? Is it a subject she's passionate about, mildly skeptical of, deeply respectful of?
- Is there a formative experience of hers that legitimately bears on this topic? If yes, it may belong in this chapter. If no, don't force one.

During the chapter's self-critique pass (already described in `writing-craft.md`), add these persona-specific checks:
- Is there a sentence here Margot wouldn't write? (Look for exclamation marks, forced enthusiasm, phrases she avoids.)
- Did I use her first-person where it earned its place, not just to prove she exists?
- If the chapter uses a personal anecdote, is it about her inner formation — or have I accidentally fabricated a historical event?

---

## Sample prose — why it matters

The optional `sample-prose/` directory in each persona's folder is worth building. Three or four 200–400-word samples of the persona writing in different modes (opening a chapter, explaining something technical, handling a hard emotional moment, closing a book) give future sessions something concrete to calibrate against.

When starting writing, if sample prose exists, read at least one sample that matches the current task. Pattern-match your prose to its rhythm.

You can build these samples organically: after the first one or two successful chapters, extract a strong passage and save it to the persona's library folder (with user permission). Over time the persona accumulates a corpus.

---

## Keeping the persona honest

A persona can fail in two directions, both bad.

**Failure 1: the persona disappears.** The prose is generic — could've been written by anyone. Solution: go back to `persona.md`, re-read the hobbyhorses and voice notes, and rewrite at least the opening and closing of each suspect chapter.

**Failure 2: the persona becomes a caricature.** The prose is too much — every paragraph reminds the reader that the author is quirky/warm/Dutch/opinionated. Solution: the persona should be present in sensibility, not in performance. If a reader notices the author in every sentence, back off.

A good persona is like a good accent in a film — you notice it for a minute, then you forget it's there, and it shapes everything without demanding attention.

---

## Persona modalities — when one persona writes in multiple registers

A single project sometimes requires the persona to write in more than one register. The same writer who composes the body of a book may also write a preface, a foreword, an author's note, an afterword, footnotes, an appendix, captions to illustrations, or a glossary. In technical documentation projects, the same engineer-documenter writes reference, how-to, explanation, and tutorial content — four genuinely different registers — under one consistent identity. In academic books, the same scholar writes the main argument, the historiographical footnote apparatus, and the bibliographic essay.

These are **modalities** — not different personas, but the same persona writing with different relationships to the reader. The discipline is to acknowledge them explicitly rather than letting them blur into one another.

### Pattern A — One persona, multiple modes

The default. A single persona document specifies the writer's identity, formation, opinions, and voice fundamentals. Within that document, distinct modes are described for the registers the project requires. For example:

- **Body / chapter mode** — the primary register the persona writes in, the one their voice was built for
- **Preface / introduction mode** — slightly more direct address to the reader, more meta-commentary about the project itself, often warmer
- **Footnote / apparatus mode** — terser, more declarative, less voice-driven, source-oriented
- **Caption mode** — short, factual, oriented to the image
- **Letter / dedication mode** — personal, brief, named address

Each mode has its own discipline notes within the persona document. When the writer enters a new mode, they read the relevant discipline notes before drafting. The transitions are deliberate: the writer is the same person, but they speak slightly differently in different relationships to the reader.

For technical documentation specifically, see `technical-documentation.md` for the four-quadrant modality system (reference, how-to, explanation, tutorial) and how a Pattern A persona handles the four registers.

### Pattern B — Multiple personas under one project

Less common, but appropriate when the registers are genuinely too different for one persona to inhabit. Examples:

- A book with a translator's introduction by a different person
- A documentation set where the tutorial is genuinely written by a teacher and the reference by an engineer, and pretending they are the same person would be dishonest
- A collaborative academic work with chapters by different specialists

In Pattern B, separate persona documents exist under one project. Each has its own voice, formation, and discipline. The cross-persona consistency is editorial rather than authorial — a copy-editor's pass at the project level keeps overall coherence, but each persona's voice remains its own.

### Choosing the pattern

Pattern A is sufficient for most projects. Pattern B is warranted when:

- The text genuinely originates from different writers in real life
- The registers are so different that a single persona inhabiting both would feel synthetic
- The project benefits from explicitly different voices as a structural choice

When in doubt, default to Pattern A and document the modalities. Only escalate to Pattern B when Pattern A produces forced or thin writing in one of the modes.

### Modes in the persona document

For Pattern A, add a `## Modes` section to the persona document. For each mode the project will use:

```
### Body mode (primary)
[normal voice description from the rest of the persona]

### Preface mode
- Slightly more direct address to the reader
- Acceptable to use "I" where the body might use "we" or third-person
- Length restraint: 800-1500 words typically
- Tone: warmer than body, but not casual

### Footnote mode
- Declarative and terse
- Source-citation pattern: [author, year, page]
- No conversational asides
- One paragraph per note unless the note demands more
```

The modes serve as an explicit reminder of register-shift when the writer moves between sections. Without them, AI tends to write everything in the persona's strongest register, which produces footnotes that read like body prose and prefaces that read like introductions to a different book.

---

## When to offer updating the library version

If during a book the working persona diverges meaningfully from the library version (new hobbyhorse surfaces, a core opinion shifts, voice matures), at the end of Phase 5 ask the user:

> "Margot evolved a bit on this project — she's softened on 'genius' as a concept and picked up a new stokpaardje about illustrations. Want to fold these changes back into her library profile for future books, keep them only in this book, or just note them in her evolution log?"

Three outcomes, all legitimate. Default to "note in evolution log" if the user doesn't care.
