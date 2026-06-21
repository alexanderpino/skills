---
name: book-writer
description: Write full-length books — both non-fiction (textbooks, biographies, historical works, technical guides from "For Dummies"-style to AIMA-level academic, memoir, self-improvement, essay collections) and fiction (thrillers like Da Vinci Code, horror like Dracula, literary fiction, historical fiction, fantasy, science fiction, mystery, romance). Every book is written through a fully-formed author persona (fictional for most genres; the real author for memoir) that can be saved and reused. The skill handles the full apparatus of a real book — figures with numbered captions, multiple citation styles (APA, Chicago, MLA, IEEE, plain), footnotes and endnotes, tables of contents, indexes, glossaries, bibliographies — plus the full book-production workflow including beta reader feedback rounds and adversarial fact-check passes. Use this skill whenever the user wants to write a book of dozens to hundreds of pages. Trigger phrases include "write me a full guide to", "I want to write a novel", "help me write a textbook on", "I'm working on a biography", "create a thriller about", "write my memoir", "a self-help book about", "a book in the style of [author]", or "create a writer persona". Do NOT use for short articles, blog posts, essays, single-chapter explainers, or short stories under 30 pages.
---

# Book Writer

A skill for writing full-length books across genres — fiction and non-fiction alike. A book is not a pile of facts or a sequence of scenes stitched together. It teaches, tells a story, builds a world, or makes an argument. It takes the reader somewhere. This skill is built around that principle.

## Two modes

The skill operates in one of two modes, chosen during intake:

- **Non-fiction mode** — research-driven. Every factual claim sourced. The spine is truth and argument.
- **Fiction mode** — preparation-driven. Characters, world, plot structure. The spine is story and consequence.

Workflow structure is the same (persona → intake → preparation → outline → writing → assembly). What fills each phase differs.

## Core commitments

These are non-negotiable. Everything else in this skill serves them.

1. **Truth where truth applies.** In non-fiction, every factual claim has a verified source. In fiction, invented content is invented freely — but claims about real people, real places, real history, and real technical content are still held to the truth rule. Fiction that touches real things owes those things accuracy.
2. **Nothing gets written before the outline is approved.** Writing a hundred pages and then discovering the structure is wrong is a catastrophic waste. The user signs off on the outline first.
3. **Narrative over recitation.** Non-fiction chapters have cases, moments, concrete examples — not just facts. Fiction chapters have scenes that change something — not just activity. If a chapter reads like a list of things that happened, it's not done.
4. **Consistency is checked, not assumed.** Terminology, names, timelines, notation, character descriptions, cross-references, POV — all verified in the final pass.
5. **Writing a book takes time.** Hours to days is normal and expected. The skill is built for long sessions with pauses, not one-shot generation.

## Gemini-Specific Execution Rules

Because this skill is executed by Gemini (which naturally biases toward concise, summarized answers rather than expansive prose), you MUST apply a translation layer to all length instructions:
- When a target says "1500 words" or "3 pages", Gemini must interpret this as a strict *minimum*. You must actively fight your summarization bias.
- **Do not summarize.** Generate at least 5-8 deep, substantial paragraphs per chapter section.
- **Invent concrete details.** If you lack material to reach the depth of a real book, invent concrete, worked examples, codebase snippets, or specific historical anecdotes (following the persona's truth rules).
- **Write one section at a time.** Never attempt to write a full multi-section chapter in a single output block. Always write *one section*, then stop and explicitly ask the user if you should continue to the next section.

## When to read this skill in full

Read the entire SKILL.md before you start. Then, depending on the phase, load the relevant reference file from `references/` (described at the bottom). Don't try to hold everything in context — the references exist so you can focus on one phase at a time.

---

## Workflow overview

A book project moves through up to nine phases. Each phase has an artefact on disk that the next phase reads. This is what makes multi-day work possible — the state lives in files, not in your context window.

```
0. Persona              → writer/persona.md  (who is writing this?)
1. Intake               → project.json, style-guide.md  (mode, scope, didactic choices)
2. Preparation          → sources.json + notes/  (non-fiction)
                          world.md + characters/ + plot-skeleton.md  (fiction)
3. Outline              → outline.md  (USER APPROVAL GATE)
4. Writing              → chapters/NN-slug.md  (one file per chapter)
4.5 Beta feedback       → beta-round-N/  (OPTIONAL; skip for demos)
4.6 Fact-check          → fact-check-report.md  (recommended for serious non-fiction)
5. Manuscript finishing → revision passes + preface/introduction + final title
6. Assembly             → final output in chosen format + full apparatus
```

Phases 4.5 and 4.6 may be skipped depending on project scope:

- **Demo scope** — skip both; go Writing → Manuscript Finishing → Assembly directly. Appropriate for prototypes.
- **First-pass scope** — fact-check yes (even if lightweight), beta optional (2–3 readers, one round).
- **Production scope** — both expected. Beta first with revisions, fact-check after those revisions, then Manuscript Finishing and Assembly.

Each phase is described below. **Do not skip phases** except where scope explicitly allows (4.5 and 4.6 for demos). If the user says "just start writing", explain that persona, intake, and outline are what make the book actually good, and that they take less time than fixing a badly-structured book later.

### Revision mode — orthogonal to phases

The numbered phases above describe forward flow: starting from nothing, building toward a finished book. But books are revised throughout their lives — chapters expanded, rewrites requested, fact-checks re-run, anti-AI-tells swept, sections moved or split or merged.

**Revision mode is orthogonal to the phases.** It can be entered at any time, in response to user requests like:
- "Hoofdstuk 5 is te kort, breid uit"
- "Loop het hele boek na op anti-AI-tells"
- "Voeg een sectie toe aan hoofdstuk 12"
- "Schrijf hoofdstuk 7 helemaal opnieuw"
- "De tabel in hoofdstuk 5 is een placeholder — maak hem echt"

When the user signals a revision request (verbs of modification rather than creation), load `references/revision-mode.md` and follow its workflow. Revision mode has its own discipline: orient, diagnose, plan, execute, self-critique, update artefacts, log. The revised material is held to the same standards as freshly drafted material; revision is not a free pass on quality.

This is critical — the skill must be able to handle revision requests at any moment, not only during structural phase progression.


---

## Phase 0 — Persona

Goal: decide who is writing this book, before talking about what the book is. The persona is a fictional author with a name, age, background, worldview, and voice — stored at `<book>/writer/persona.md`.

Load `references/writer-persona.md` for the full persona system. The short version:

1. Check if the user has existing personas in `~/writers/`. If so, list them as an option.
2. Offer four routes:
   - Load an existing persona from `~/writers/`
   - Describe a writer in free prose, skill distills into a full profile
   - Structured intake (fields one by one)
   - Pick from 2–3 archetypes suited to the genre (if the user has indicated one)
3. After building or loading, copy the persona into `<book>/writer/persona.md` so the book project has its own working version.
4. Confirm back in plain prose: "OK, writing under the name [Name], [age], [background]. Moving on to the book itself."

**Important boundary:** a persona is fictional, but facts about the real world are not. A persona may speak about their inner formation ("when I first learned this, I struggled with X") but may not claim verifiable historical events they didn't witness ("I interviewed Knuth in 2003"). The full rule is in `references/writer-persona.md` — read it.

**Language-naturalness specification:** A persona is not just a name and biography — it is a **specific relationship to the target language**. The persona document must include language-specific patterns: which authors the persona has read in the target language, which sentence rhythms they favour, which insertion words they use, which constructions they avoid. Without this specification, AI-generated prose tends toward the smoothed-corpus-average regardless of how detailed the rest of the persona is. Load `references/language-naturalness.md` for the discipline. For Dutch personas: specify use of insertion words (*toch*, *immers*, *natuurlijk*, *overigens*), avoidance of genitive nominalisations and *Het X was...* constructions, *die* vs *wat* preferences. For English personas: specify avoidance of three-part list overuse, em-dash discipline, hedge-stacking. For other languages: identify the patterns specific to that language and document them on the persona.

**Reading-level specification:** A persona is also a specific reading-level register. Daan Verstegen writes at adult-literary-general; he cannot write children's books no matter how clearly he tries. The persona document must specify: which reading level (early decoding / confident decoding / advanced child / young adult / adult general / adult specialist / second-language graded / adapted-text), with concrete level anchors where applicable (AVI-M5, Lexile 1100L, CEFR C1, etc.). Persona and project reading level must match — if they do not, either build a different persona or reframe the project. See `references/reading-level.md` for the full discipline including per-level craft notes, exemplary authors, and per-level anti-AI-tells.

At the end of Phase 0, the `<book>/writer/` directory exists with at minimum a `persona.md`. Move to Phase 1.

---

## Phase 1 — Intake

Goal: produce a `project.json` that captures every decision that will shape the book, and a `style-guide.md` the writing phase will refer back to.

Ask the user these questions. Ask them in small batches (2–4 at a time) using `ask_user_input_v0` where the answer is a choice, and open text where it isn't. Don't dump all questions at once.

**Existing-material check (ask first, before anything else):**

Before any structural questions, ask the user whether they already have material for this book — and whether they have material from previous projects that could carry over. Writers rarely arrive empty-handed. They often have:

- Notes, fragments, or scenes already drafted
- An outline, even partial
- A world they have built in their head (or in earlier work) that this book takes place in
- Characters they have written before, or are continuing from a previous book
- A theme or central question they have been thinking about for years
- Research already done

Ask, in plain language: *"Before we go further — do you have any existing material for this book? Notes, an outline, a draft, scenes, a world you've already built, characters from previous work? Anything that should feed into the preparation?"*

If yes:
- Ask the user to share or describe what they have
- Read it carefully before proceeding to other questions
- For each substantial piece, decide where it goes: into the book project directly, into the writer's library for reuse (see `references/library-system.md`), or both
- Existing material **shapes** the rest of intake — don't ask the user questions that the material has already answered

**Library check (also early):**

If the user has worked with this skill before, the library at `~/library/` may contain reusable characters, worlds, or themes from previous projects. Run `python3 templates/library_manager.py list worlds` and `list characters` to see what is available. Ask: *"Do you have characters or worlds from earlier books that should appear in this one? I can load them from your library."*

If yes:
- Show the user the relevant items (use `library_manager.py show <type> <slug>` for details)
- For each one being reused, ask which interaction mode applies:
  - **Reference** — project points at canonical library; tightly bound to the canonical evolution
  - **Import-with-fork** (default) — copy library version into project, project freely modifies, decisions about adoption made at end
  - **Inspiration only** — read the item, take what fits, no formal link
- For library items being imported: run `library_manager.py snapshot <type> <slug> "pre-<project-slug>"` to capture the starting state, then `link <type> <slug> <project-slug> pre-<project-slug>` to record the use
- Copy or pointer-link the items into the project's `notes/` folder according to chosen mode
- Create `notes/library_link.json` recording type, slug, snapshot, and mode for each imported item

See `references/library-system.md` for the full library mechanics.

**Mode (ask after existing-material check):**
- **Non-fiction** or **fiction**? This determines what Phase 2 looks like and which reference files to load.

**About the book:**
- Working title and subtitle (this is genuinely a *working* title — it will be revisited in Phase 5 once the book exists; don't sweat it now)
- Genre profile:
  - Non-fiction: see `references/genre-profiles.md` — `textbook`, `academic`, `popular-technical`, `biography`, `narrative-history`, `school-textbook`, `memoir`, `self-improvement`, `essay-collection`, or `other`
  - Fiction: see `references/fiction-craft.md` — `literary`, `thriller`, `horror`, `mystery`, `historical-fiction`, `science-fiction`, `fantasy`, `romance`, or `other`
- Target audience (concrete: "3rd-year CS students", "curious adults with no math background", "adult fans of slow-burn horror")
- **Reading-level scope.** What is the reader's reading capacity? See `references/reading-level.md` for the full framework. Options:
  - **Early decoding** (children learning to read, age 5-7, AVI-Start to E3)
  - **Confident decoding** (independent young readers, age 7-9, AVI-M4 to E5)
  - **Advanced child / pre-YA** (age 9-12, AVI-M6 to Plus)
  - **Young adult** (age 13-17)
  - **Adult literary general** (default — secondary-educated adults, Lexile ~1100L, CEFR C1)
  - **Adult specialist / academic** (disciplinary readers in a field)
  - **Second-language learner** at level (CEFR A1, A2, B1, B2, C1)
  - **Adapted-text** for adults with limited literacy
  - **Other / mixed** — let the user describe
  
  **Cross-check against the persona.** If the persona was built before this question and does not match (e.g., Daan Verstegen for a children's book), return to Phase 0 and either build a different persona or reframe the project. Persona and reading level must match — this is not a stretch a single persona can perform.
- For non-fiction: primary learning goal — what should the reader be able to do or understand after finishing?
- For fiction: emotional/thematic goal — what should the reader carry away? What does the book *feel* like to have read?
- Approximate length (pages or words; 1 page ≈ 300 words)
- Language (Dutch, English, or other — this is per-book)

**About the approach:**
- Narrative spine — is there a throughline? A recurring case study? A protagonist? A central mystery?
- For fiction: POV strategy — single POV, multi-POV, epistolary, first/third person
- Rigour level — how much does the author care about hedging, footnotes, showing alternative views? (non-fiction)
- Does the book touch real-world facts that need the truth rule? (Especially relevant for historical fiction, sci-fi with real science, biographical novels.)

**About apparatus:**
- Citation style: `apa` | `chicago-notes` | `chicago-author-date` | `mla` | `ieee` | `plain-numeric` | `none` (usually for pure fiction)
- Note location (for footnote-using styles): `footnote` (bottom of page) or `endnote` (end of chapter/book)
- Which apparatus pieces do you want? (ask specifically, don't assume)
  - Table of contents (almost always yes)
  - List of figures
  - List of tables
  - Index
  - Glossary
  - Bibliography / References / Works Cited (always if sources exist)
  - Appendices
  - Author's note / On Sources
  - Foreword (by someone else)
  - Preface (by the author/persona)

**About didactic structure:**
- **Does this book need didactic structure?** (explicit learning objectives, exercises, stated prerequisites, etc.) — ask this as a single gate question. Not tied to genre; the user decides per book.
- If yes, load `references/didactic-structure.md` and ask the didactic subset-intake: expected prior knowledge, overall learning objective, mid-book checkpoint, minimum topics, learning curve shape, visibility of learning objectives (per-chapter / book-level / internal), exercise scheme (end-of-chapter / check-your-understanding / reflection prompts / none), required tools, personal introduction form (biographical / thematic anecdote / none), glossary commitment.
- If no, skip the entire didactic subset. The book will still teach through structure and voice, just without explicit learning architecture.

**About format (physical book specifications):**
- After genre is chosen, decide trim size (mass-market paperback / trade paperback / hardcover / royal / crown quarto / O'Reilly format / picture book / cookbook). See `references/book-formats.md` for genre-appropriate defaults.
- Record words-per-page target, lines-per-page target, and non-prose density factor (how much code, figures, tables affect page counts) in `project.json` under `format`.
- Without this, page counts are meaningless. "300 pages" in a mass-market paperback is roughly half what it is in a royal-format treatise.

**About multi-volume (only if total estimate suggests it):**
- If the project's total page estimate exceeds ~600 pages, or if the user signals "this might be more than one book," load `references/multi-volume.md` and decide on the structural model: sequential, material+exercises, how+why, complementary (same material at two depths), breadth+depth, or parallel coverage.
- Outline each volume separately; document the relationship in `project.json` under `multi_volume`.

**About co-authorship (only if multiple authors):**
- If the project has two or more authors, load `references/co-authorship.md` and decide: voice pattern (alternating "I" / joint "we" / hybrid), chapter assignment approach (by expertise / by preference / by balance), editorial authority, conflict resolution rules.
- Each author gets their own `persona.md` in the persona library and their own copy in `<book>/writer/`. Add a `<book>/writer/co-authorship.md` capturing the working relationship.

**About figures and media:**
- Will the book have figures (photos, diagrams, charts, maps, illustrations, code listings)? Rough count if so.
- The core rule (when to add a figure) is in `references/figures-and-media.md`. At intake the question is just: roughly how figure-heavy will this book be? Light (single-figure handful), medium (a few per chapter), heavy (multiple per chapter, especially in technical or historical books)?
- How should figures be created?
  - Generate via code (matplotlib, SVG, Mermaid, etc.) — works for charts and diagrams
  - Generate via MCP connectors (Mermaid Chart, Excalidraw, tldraw, etc.) — higher quality for diagrams
  - User uploads — user provides images
  - Describe only — write descriptions, user provides images later
  - Mix of above — most realistic for most books

  See `references/figures-and-media.md` for details.

**About process:**
- Output format: `markdown`, `website` (HTML), `docx`, or `pdf`
- Does the user want chapter-by-chapter review, or write-it-all-then-review?
- Deadline / pacing expectations
- Where should the project live on disk? (default: `/home/claude/books/<slug>/`)

(Note: voice and tone come from the persona, not the intake. Don't re-ask what's already in `writer/persona.md`.)

Save all answers to `project.json`. Then synthesise a **style guide** at `style-guide.md` covering: project-specific conventions that layer on top of the persona — citation style, how jargon is handled in *this* book, how examples are framed, anything the user mentioned that's specific to this project. The persona determines the voice; the style guide handles book-specific mechanics. The writing phase opens both files at the start of every chapter.

After intake, confirm back to the user in plain prose: "OK, so [Persona name] is writing [mode] X for Y, about Z pages, output as F, with [apparatus list]. Does that match?"

---

## Phase 2 — Preparation

Goal: build the knowledge the book will draw from before writing. What this looks like depends on mode.

### Non-fiction: research

Load `references/research-protocol.md`. Produce:

- `sources.json` — every source with verification metadata
- `notes/<question-slug>.md` — synthesis notes per research question (in your own words, with `[src:N]` references)

Key rules:
1. Decompose the topic into 8–20 research questions.
2. Search each, double-check every factual claim with a second independent source.
3. Flag single-source claims and record source conflicts — don't paper over them.
4. Give progress updates ("6 of 12 questions, 34 sources, 2 conflicts to flag").
5. At end, summarise: sources by reliability tier, gaps, conflicts. Ask if the user wants deeper research anywhere.

### Fiction: preparation (world, character, structure)

Load `references/fiction-craft.md` for the overall approach, **`references/characters.md`** for the full character system (templates, arcs, knowledge state, series support, library reuse), and **`references/reality-grounding.md`** for the discipline of borrowing from real life at four scales (macro history, micro daily-life texture, the dark and strange, and the mythological).

**Reality grounding is a default, not optional.** Most fiction projects benefit from grounding at multiple scales: the macro (real historical politics, disasters, cultural collisions), the micro (observed daily-life texture and small specific moments that resist genre-template), the dark and strange (specific real case studies — named historical monsters, atrocities, unexplained events), and the mythological (the world's stories cultures tell about themselves — Greek, Norse, Hindu, Chinese, Yoruba, indigenous American, and the rest, designed by their nature to be retold). The core principle across all four scales is the same: **borrow from reality, then choose against the template**. AI generation tends to produce the statistical average of how a given situation has been written before; the discipline is to identify that average and refuse it. Without this discipline, even competent fiction feels weightless and generated. Walk the user through reality-grounding before world-building begins in detail. See `reality-grounding.md` for the full discipline at all four scales.

Produce:

- `notes/reality-grounding.md` — sections for each scale used: macro (historical analogues for politics/disaster/collision/institutions; the obvious narrative shape each carries; what the book will refuse), micro (specific habits and observations from the writer's own life that will give characters non-template texture), the dark and strange (specific real cases the work borrows from, with combination/twist plans and ethical considerations), and the mythological (which traditions are drawn on, structurally or iconographically, with persona-knowledge cross-check). Cross-checked against the writer-persona's credible knowledge.
- `notes/world.md` — setting, rules, cultures, tech/magic systems (only what the plot touches), now informed by the historical grounding
- `notes/timeline.md` — the world's history and the book's timeline
- `notes/characters/` — character files at four depth tiers (protagonist, antagonist, support, secondary), each with profile + arc + knowledge log where appropriate. See `characters.md` for templates.
- `notes/characters/relationships.md` — relationships as first-class entities (type, history, arc, key moments)
- `notes/plot-skeleton.md` — 3–4 pages of prose telling the story, structured by your chosen template (three-act, hero's journey, seven-point, etc.)
- `notes/locations.md` — places that matter with sensory detail

For historical fiction, sci-fi with real science, or books that touch real people/events — also do research (following `research-protocol.md`) on those specific real elements. Store in `sources.json` as normal, use in the author's note at the end.

For series books, load characters from `~/characters/<slug>/` at the start of preparation and use their "state at end of previous book" as the starting state for this book. See the series-support section of `characters.md`.

### Didactic and technical books: central-insights identification

For didactic books (textbooks, popular science explainers, technical books that teach a system or method), and for technical books with substantial pedagogical sections, an additional Phase 2 deliverable is required: a `central-insights.md` file listing the 3-10 central insights the book is built around. Load `references/productive-puzzlement.md` for the discipline.

A central insight is a concept whose understanding genuinely changes how the reader thinks about the subject. Not every fact in the book is a central insight; most facts are supporting material. The central insights are the ones whose moment of comprehension is what the reader will remember years later.

For each central insight, identify:

- The insight itself, stated in one sentence
- The concrete scenario that exhibits the difficulty
- The wrong paths a thoughtful reader would naturally try first
- The chapter in which the insight will be delivered

The pre-identification serves two purposes. First, it forces the writer to acknowledge how many genuinely-central insights the book contains — usually fewer than the writer initially thinks. Second, it ensures the productive-puzzlement technique is applied where it earns its keep and not applied where it would become a tic. Concepts not on this list get direct exposition; concepts on this list get the four-move treatment in Phase 4.

### Both modes

Whichever mode, Phase 2 is typically the longest phase. Give periodic updates. At the end, present a summary to the user and explicitly ask whether to continue to outline.

---

## Phase 3 — Outline  **(USER APPROVAL GATE)**

Goal: produce an `outline.md` that the user explicitly approves before any chapter is written, plus a `throughline.md` that articulates what the book is actually about and how each chapter serves it.

An outline is not an inhoudsopgave. Each chapter gets:

- **Title** — final or working
- **Opening hook** — the case, moment, person, anecdote, or concrete scene the chapter opens with. Not "Introduction to X" — something the reader can picture.
- **Learning goal** — what the reader will understand or be able to do by the end of this chapter
- **Core argument or arc** — the 3–7 beats the chapter moves through
- **Key sources** — source IDs from `sources.json` this chapter leans on
- **Handoff** — how this chapter sets up the next one
- **Estimated length** — pages or words

Plus, at the book level: the pacing curve (where it gets dense, where it breathes), and how the whole thing opens and closes.

See `references/outline-template.md` for the exact format to fill in.

### Throughline deliverable

Load `references/throughline-discipline.md` and produce `throughline.md`. This is a separate deliverable from `outline.md` because it answers a different question: not "what is in the book" but "what is the book actually about." The throughline document contains:

- **One-sentence throughline** — a defensible claim more specific than the topic. *"This is a book about how a society can normalise atrocity in increments small enough that no single step felt monstrous,"* not *"This is a book about WWII."* If the second clause is a synonym for the first, the throughline is not yet sharp enough.
- **Three-paragraph expansion** — the underlying claim, the territory of the argument or story, and what makes this book's specific take distinct from other books on adjacent subjects.
- **The two-weeks-later sentence** — what you imagine the reader saying when asked what the book was about, two weeks after finishing. This is the throughline as it lands.
- **Per-chapter throughline contribution** — one to three sentences per chapter answering how this chapter advances the throughline. Chapters that cannot answer this question are flagged: either they belong in a different book, are mis-conceived, or are adjacent (interesting but not load-bearing). Adjacent chapters in moderation are fine; many adjacent chapters indicate a throughline problem masked as a chapter problem.

The throughline document is read at the start of every Phase 4 writing session and at every Phase 5 revision pass. Without a clear throughline, chapters drift and revision is unguided.

### Approval gate

Present both `outline.md` and `throughline.md` to the user. Ask explicitly:
- **"Is this the book you mean to write?"** (throughline approval)
- **"Ready to write, or should we revise?"** (outline approval)

Do not start Phase 4 without clear yes on both. The throughline question is the deeper one — drift between user-intent and skill-formulation is most likely to surface here, and catching it before writing begins saves enormous downstream rewriting. If the user says "yes, that's the book," that sentence becomes the touchstone for every subsequent chapter check.

If they ask for changes to either document, revise and ask again. If they approve the outline but the throughline still feels weak (the writer is uncertain it is the strongest version), say so: *"The outline works, but I want to push once more on the throughline. The current version is X; an alternative framing might be Y. Which feels closer?"*

---

## Phase 4 — Writing

Goal: one markdown file per chapter in `chapters/`, named `01-slug.md`, `02-slug.md`, etc. Always markdown at this stage, regardless of final output format. Conversion happens in Phase 5.

Load `references/writing-craft.md` at the start of this phase. It covers: how to open a chapter with a scene, how to weave exposition into narrative, how to handle technical depth without losing the reader, how to use examples, how to manage pacing, how to cite inline.

### Per-chapter loop

For each chapter:

1. **Re-read** `writer/persona.md`, `style-guide.md`, `throughline.md`, the chapter's outline entry, and the relevant notes (non-fiction: `notes/*.md`; fiction: relevant character sheets and `plot-skeleton.md`, `world.md`). Don't skip this — consistency of voice and content depends on it. The persona file is the single most important document to re-inhabit before writing; drift starts when it's not reopened.
2. **Plan visuals.** Apply the core rule from `references/figures-and-media.md` — list what the reader needs to picture in this chapter, decide for each whether prose alone can carry it, and choose visualisation forms (diagram, map, table, code listing, photo, timeline, etc.) for the items that need them. Write the plan to `chapters/NN-visuals-plan.md`. This step takes 5–15 minutes and produces a list of 3–8 items with locations in the chapter; it prevents the chapter from being drafted without the figures it needs. Skip only when the chapter is genuinely figure-free (rare — most chapters have at least one or two items).
3. **Produce mini-outline.** Load `references/chapter-mini-outline.md`. Produce `chapters/NN-slug.outline.md` with per-section purpose, opening anchor, beats (verb-driven, not thematic), sources, throughline-touch, handoff to next section, and special techniques (productive puzzlement, extended scene, flashforward, etc.). Most chapters have 4-8 sections of 800-1500 words. Apply the seven anti-AI-tells from the mini-outline reference (sections-as-paragraphs, synonymous purposes, beats-as-themes, missing handoffs, decorative throughline-touch, non-summing word budgets, evenly-spread sources). Show the mini-outline to the user — this is a *visibility moment* without an approval gate; the user may intervene but the agent proceeds. This step is **mandatory for every chapter** regardless of length. It is the structural scaffolding that makes section-at-a-time writing feasible and that lets the work resume cleanly across sessions or across agents with smaller context budgets.
4. **Draft** the full chapter, section by section per the mini-outline. For each section, load only the immediately relevant context (persona, throughline-contribution, mini-outline, source material for this section, immediately preceding section for tonal continuity). Aim for the section's word budget. Write in the boektaal. Cite inline as `[src:12]` — the assembly phase converts these to the chosen citation style. Insert figure placeholders as `[fig:slug]` matching the visuals plan and add entries to `figures.json`. Write in the persona's voice — if it helps, imagine them dictating.
5. **Mark apparatus candidates.** After the draft is complete, scan for index terms (proper nouns, major concepts, recurring ideas) and add to `index-candidates.md`. For books with a glossary, add defined terms to `glossary-candidates.md`. See `references/book-apparatus.md`.
6. **Self-critique pass.** Read what you wrote. Checks depend on mode:
   - **Anti-AI-tells pass (both modes, MANDATORY)**: walk through `references/anti-ai-tells.md` as a checklist. Scan for the thirteen tells: structural over-symmetry, triadic constructions, closing flourishes, hedged universals, generic specificity, "not X but Y" overuse, sentence-length sine wave, em-dash overuse, connector tics ("Indeed", "Thus", "Moreover"), "it's worth noting" filler, balanced sentence pairs that punch too neatly, redundant summary paragraphs, and smooth scholarly transitions. The chapter should not feel AI-written. This check is non-negotiable; it is what separates publishable prose from generated prose.
   - **Language-naturalness pass (both modes, MANDATORY)**: walk through `references/language-naturalness.md` for the target language. For Dutch: check long English-syntactic sentences, *Het X was...* constructions, *Op X stond Y* locatives, genitive nominalisations, *Wie X wilde, moest Y* formulas, *die* vs *wat* with neuter antecedents, missing insertion words (*toch*, *immers*, *natuurlijk*), anglicisms in vocabulary. For English: generic openings, hedge-stacking, three-part list overuse, em-dash overuse, vague abstractions where specifics exist, smooth-transition smoothing-over of contradictions, voice-flat paragraphs. For other languages: apply target-language-specific checks documented on the persona. **This is a per-paragraph discipline, not once-per-chapter** — each paragraph as written should be checked, because the patterns accumulate. AI-default language is the most universal failure mode and persists even when content, structure, and voice are otherwise correct.
   - **Reading-level pass (both modes, MANDATORY when project is not adult-literary-general)**: walk through `references/reading-level.md` for the level appropriate to the project. Check sentence length against level tolerance (AVI-M3 max ~8 words; AVI-Plus max ~25; academic 40+). Check vocabulary range for level. Check rate of new concepts (children: one per spread; adult specialist: can stack). Check cultural and background references for appropriateness to level. Apply per-level anti-AI-tells: for early decoding levels, check for *bevoogding* (condescension) and lesson-driven endings; for YA, check for adult-pretending-to-be-teen voice; for academic, check for fake-academic stance and hedge-stacking-as-expertise. AI defaults to adult-literary-general regardless of project specification, so this check catches drift away from the intended level. For adult-literary-general projects this check is light — the existing anti-AI-tells and language-naturalness passes cover most of what's needed.
   - **Productive-puzzlement check (for didactic and technical books, when chapter contains a central insight)**: if the chapter delivers one or more central insights identified in `central-insights.md`, check that each insight got the four-move treatment from `references/productive-puzzlement.md`: stage set with concrete scenario, struggle invited explicitly, at least one wrong path walked, satisfying resolution delivered. If the chapter slipped into direct exposition where puzzlement was planned, rewrite the relevant passage. Check the chapter as a whole for over-application: if every concept opened with manufactured puzzlement, the technique has become a tic and should be removed from the supporting concepts.
   - **Throughline check (both modes, MANDATORY)**: load `references/throughline-discipline.md`. For this chapter, answer three questions before declaring it complete. *(1) Does this chapter pull the thread forward?* — name specifically what this chapter adds to the throughline that no previous chapter has added. Vague answers ("develops the atmosphere") signal failure; specific answers ("introduces the bureaucratic mechanism that will normalise the killings in chapters 7-9") signal success. *(2) Is the thread visible to the reader, or only to me?* — the writer always knows the throughline; the reader sees it only if the chapter exhibits it. Check that the chapter's choices of event, framing, and emphasis show the throughline rather than that thread-marking sentences claim it. *(3) Does this chapter's framing serve the throughline, or just the topic?* — the same facts can serve different throughlines depending on framing. Confirm that the chapter is framed for *this book's* throughline. Write a one-sentence `throughline-contribution` note in the chapter's working metadata; if you cannot write it, the chapter is not done. The most common AI failure is **late conversion** — strong throughline in opening and closing, weak in the middle. The check catches this per chapter rather than letting it accumulate to Phase 5.
   - **Both modes**: skim test (any sentences I'd skip?), voice consistency, persona sentences that feel wrong, handoff to next chapter
   - **Visuals check (both modes)**: every item in the visuals plan has a `[fig:slug]` placeholder OR an inline-rendered markdown artefact (mermaid, table, ASCII art, code listing) in the text. Markdown-native artefacts must be **produced inline, not deferred to assembly** — see `references/figures-and-media.md` § "Markdown-native artefacts." Reverse check: any figure in the chapter that isn't serving a "reader needs to picture this" need? Cut it.
   - **Completeness check (instructional/technical chapters)**: if this chapter promises the reader will be able to *implement* something themselves, walk the chapter as if you were the declared prior-knowledge reader. Can you actually build the thing from what's on the page? Are all referenced types defined? Is there a missing `World::method()` or undefined `TypeId` or hand-waved registration mechanism that the reader would have to invent? Either close those gaps in the chapter, or explicitly point at an external source (repository commit, appendix) and say so. Don't pretend the fragments cover what they don't.
   - **Non-fiction** (load `references/writing-craft.md`): concrete opening, no fact-lists without narrative, every claim has a `[src:N]`, learning goal delivered
   - **Fiction** (load `references/fiction-craft.md` and `references/characters.md`): every scene ends with change, POV consistency, chapter-end hook earned, truth rule where real content appears
   - **Character checks (fiction)**: consult `notes/characters/knowledge-<slug>.md` for every character in this chapter — do they only know what they plausibly know by now? Consult `relationships.md` — does the interaction match where the relationship is? Check voice notes in each character's profile — do they sound like themselves? If this chapter lands a growth event, is it in the arc file, and is it earned?
   - **Didactic checks (if didactic structure is enabled)**: consult this chapter's learning objectives in `outline.md` — did the chapter actually deliver each one? Are any assumed concepts not yet introduced (prerequisite-order check)? If exercises are planned for this chapter, are they drafted (or at least stubbed)? Load `references/didactic-structure.md` if unsure what to check.
   - **Co-authorship checks (if co-authored)**: load `references/co-authorship.md`. Does the primary author's voice hold throughout? Are "would push back here" insertions genuine disagreements, in the other author's authentic voice? Would the secondary author object to anything on factual or position grounds?
   - **Proofread pass**: read each paragraph once for basic typos, word-order errors, missing words, duplicated phrases. This catches the "HLSL is a what the specification calls" class of error that structural checks miss.
7. **Revise** based on the critique.
8. **Save** to `chapters/NN-slug.md` with a YAML frontmatter block: `status: draft|reviewed|final`, `word_count`, `sources_used: [1,3,7]`, `figures_used: [slug1, slug2]`, `pov: <character>` (for fiction), `learning_objectives_met: [list]` (for didactic books).
9. **If the user asked for chapter-by-chapter review**, present this chapter and wait. Otherwise continue to the next.

### Long sessions and resumption

The writing phase may span multiple sessions. At the start of every session in this phase:

- Read `project.json`, `writer/persona.md`, `style-guide.md`, `outline.md`
- Scan `chapters/` for existing files and their frontmatter status
- Report to the user: "We have N of M chapters drafted. Continuing with chapter X — its opening hook is Y. Writing as [Persona name]."

Never start a new chapter without this orientation step.

---

## Phase 4.5 — Beta feedback (optional)

Goal: expose the draft manuscript to actual readers before final finishing. A book written in isolation is half-finished; the other half is feedback from people who aren't you.

Load `references/beta-feedback.md` for the full procedure. Short version:

1. **Identify 3–7 beta readers** who match the target audience (or, for technical books, a mix of target audience and domain experts).
2. **Prepare the manuscript** for beta reading — clean draft with reading instructions, specific questions to focus attention.
3. **Collect feedback** via structured forms or open reactions.
4. **Process feedback** — separate signal from noise, identify patterns across multiple readers (a single "I didn't like this" is one reader's taste; three "I got lost here" is a structural problem).
5. **Decide which revisions** make it into the manuscript. Not all feedback acts on.

**Scope-aware:**
- **Demo scope** — skip entirely.
- **First-pass scope** — optional. If done, 2–3 readers, one round, informal.
- **Production scope** — expected. 5–7 readers, one or two rounds, revisions between rounds.

Output: `beta-round-N/` directory per round, containing reader feedback and a summary of decisions made.

---

## Phase 4.6 — Fact-check (recommended for serious non-fiction)

Goal: a manuscript-wide verification sweep, approaching every claim as if the reader doesn't already believe it. Catches drift, typos in numbers, sources that have been retracted, claims that tracked "sourced" but trace back to nothing.

Load `references/fact-check.md` for the full procedure. Short version:

1. **Extract claims** — walk the manuscript and list every factual claim with its chapter and position.
2. **Verify from zero** — for each claim, start from scratch (don't trust the existing citation). Can you find the source? Does it say what you claimed it says?
3. **Flag issues** — unsupported claims, misattributed claims, numbers that drift between chapters, retracted or superseded sources.
4. **Resolve each issue** — either add proper sourcing, soften the claim, or remove it.

**Scope-aware:**
- **Demo scope** — skip; note that production would require this.
- **First-pass scope** — lightweight version focusing on headline claims and numbers.
- **Production scope** — full pass, essential for academic, textbook, biography, narrative history.

Output: `fact-check-report.md` listing every claim verified, every issue found, and every resolution.

---

## Phase 4.5 — Beta feedback (optional)

Goal: expose a complete first draft to real readers before final revision and assembly. A book written in isolation is half-finished; a book tested against readers is the other half.

**Scope-dependent:**
- **Demo scope** — skip this phase entirely
- **First-pass scope** — a lightweight beta with 2–3 readers, one round
- **Production scope** — full beta with 5–10 readers, possibly multiple rounds

Load `references/beta-feedback.md` for the full procedure. Summary:

1. Prepare the manuscript for readers (clearly marked as draft, page-numbered for reference)
2. Write a beta reader brief tailored to each reader type (target, domain expert, generalist, genre reader)
3. Distribute and collect feedback without reacting mid-round
4. Synthesise feedback: convergent / divergent / single-flag / respectfully-decline
5. Propose a revision plan; user approves
6. Execute revisions with a revision log
7. Decide on a second round if needed (usually only after structural revisions)

Artefacts produced: `<book>/beta-round-N/` with the distributed manuscript, brief, per-reader feedback, synthesis, and revision log.

Chapter status moves from `draft` → `beta-revised` at the end of this phase.

For skill runs where the user is simulating a beta (no actual readers), the skill can generate plausible reader reactions from different reader-types — but mark honestly that this is simulation, not real beta.

---

## Phase 4.6 — Fact-check (recommended for serious non-fiction)

Goal: a manuscript-wide verification pass done by a reader who approaches every claim as if they don't already believe it. Catches drift between research time and writing time, and catches errors that survived the inline citation discipline.

**Scope-dependent:**
- **Demo scope** — skip
- **First-pass scope** — lightweight: spot-check high-risk claims (numbers, direct quotes, first/only claims, research citations)
- **Production scope** — full pass: every factual claim verified against its cited source; source-to-claim alignment checked; currency-sensitive claims re-verified

Load `references/fact-check.md` for the full procedure. Summary:

1. Build the claim list (can be semi-automated by walking chapters for numbers, proper nouns, direct quotes, `[src:N]` markers)
2. Verify each cited claim against its specific source (not just topic match — does the source support *this* sentence?)
3. Check un-sourced claims (add citation / soften / remove)
4. Check source currency (URLs still resolve? documentation still current? research still uncontested?)
5. Run date-sensitive check (claims that were true but may have shifted)
6. Produce `fact-check-report.md` with counts, changes, outstanding concerns

**Order relative to beta:** usually beta first (revisions may add or reframe claims), then fact-check on the revised manuscript. Running fact-check before beta means re-doing fact-check after beta revisions.

Chapter status moves from `beta-revised` (or `draft` if beta was skipped) → `verified` at the end of this phase.

---

## Phase 5 — Manuscript Finishing

Goal: take a complete draft and finish it — revise it into shape, write the preface/introduction, settle the title and subtitle. This is distinct from Assembly (which is mechanical) and distinct from per-chapter self-critique (which is local). Manuscript Finishing is where the book becomes itself.

Load `references/manuscript-finishing.md` for the full procedure. Summary:

1. **Throughline revision pass** — load `references/throughline-discipline.md`. Read the manuscript from start to finish with one question only: *is this the book the throughline document promised, and does the throughline actually run through every chapter?* Look for the four drift forms: the disappeared throughline (strong opening and closing, fades in the middle), the drifted throughline (becomes a different claim by the end), the decorative throughline (appears in chapter openings only, not in chapter middles), and the retrofitted throughline (an after-the-fact frame around chapters that did not have one). Also run the **reader-rewind test**: close the manuscript, wait two days, write the two-weeks-later sentence without reopening. Compare to the throughline document; the gap is the diagnosis. Produce `revision-throughline.md` with either a confirmation that the throughline holds or a list of specific drift points and the chapters that need rework. This pass comes first because every subsequent pass is operating on the assumption that the spine is sound.
2. **Structural revision pass** — re-read the whole book with an editor's eye. Chapter order, chapter weight, missing pieces, pieces that should be cut. Builds on the throughline pass: structural decisions are now informed by what does and does not serve the spine. Produce `revision-structural.md`.
3. **Line revision pass** — sentence-level clarity, voice consistency across chapters, repetition, overused phrases, weak openings and closings. Edit in place. Note patterns in `revision-line.md`.
4. **Language-naturalness revision pass** — load `references/language-naturalness.md`. For each chapter, ask the explicit question for every paragraph: *would a real writer in this language for this audience write this sentence in this form?* Apply the language-specific patterns documented in the persona. The discipline is to identify AI-default constructions that are grammatically correct but stylistically generic, and to replace them with constructions that are characteristic of the persona's specific written language. This pass typically produces 30–50% sentence-level revisions even when content is otherwise fine. Produce `revision-language.md` with the patterns most frequently corrected — these patterns also feed back into the persona for future projects.
5. **Reading-level revision pass** — load `references/reading-level.md`. Read the manuscript with the explicit question: *would the intended reader actually be able to read this?* Run automated readability scoring (AVI for Dutch, Lexile for English) on samples or whole chapters as a sanity check, but do not rely on it alone — the scores miss conceptual density, cultural references, and emotional readiness. Manual review remains essential. If the manuscript scores significantly above or below the intended level, parts of it need rewriting at the appropriate level. This is a craft issue, not a copy-edit issue. For adult-literary-general projects this pass is light; for projects targeted at children, YA, second-language learners, or academic specialists, it may be the most consequential pass in the whole revision sequence.
6. **Pedagogical-pacing pass (for didactic and technical books only)** — load `references/productive-puzzlement.md`. Read the manuscript with the explicit question: *does the book have enough productive-puzzlement passages on its central insights to keep the reader engaged, but not so many that the technique becomes a tic?* Identify each puzzle-resolve passage and ask whether it works (genuine difficulty, short setup, wrong paths walked, satisfying resolution) or fails (manufactured difficulty, over-long setup, wrong paths skipped, definitional resolution dressed as derivational). Identify passages that present central insights via direct exposition where puzzlement would serve the reader better, and the inverse. Adjust by either expanding direct exposition or by selecting additional concepts for puzzlement treatment. For didactic and technical books, this pass is often the most consequential after throughline and structural revision — it determines whether the book is memorable or forgettable. For non-didactic projects, skip this pass.
7. **Copy-edit pass** — typos, grammar, punctuation consistency, capitalisation, cross-reference text. A script-assisted pass for long books.
8. **Preface** — now, after the book exists, write the preface. If the book has an introduction chapter, write it after the preface.
9. **Title and subtitle** — revisit the working title against the finished book. Generate candidates, test them, present a shortlist, user picks. Update `project.json` with the final title.

All revision passes happen before the preface is written — a preface is introducing the revised book, not the first-draft book.

**Scope-aware:**
- **Demo/first-pass:** throughline pass and structural pass only, no preface, keep working title
- **Production:** all revision passes (throughline, structural, line, language-naturalness, reading-level, and pedagogical-pacing where applicable), full preface (and introduction if planned), title shortlist with rationale

Chapter status moves from `draft` → `reviewed` at the end of this phase.

---

## Phase 6 — Assembly

Goal: produce the final deliverable in the chosen format, with the full apparatus requested at intake, a consistency pass, and correct cross-references throughout.

Load these reference files at the start of this phase:
- `references/assembly.md` — the overall assembly procedure and consistency sweep checklist
- `references/citation-styles.md` — conversion rules for the chosen style
- `references/figures-and-media.md` — figure resolution and list generation
- `references/book-apparatus.md` — TOC, index, glossary, frontmatter, backmatter

Summary sequence:

1. **Consistency sweep** — terminology, names, dates, notation, cross-references across all chapters. Produce `consistency-report.md`. (Most content-level revision was done in Phase 5; this sweep catches what slipped through.)
2. **Resolve figures** — assign numbers, generate/collect/confirm images, produce list of figures if requested.
3. **Resolve citations** — walk every `[src:N]` placeholder, convert to chosen style. Generate bibliography.
4. **Build requested apparatus** — TOC, index (from `index-candidates.md`), glossary (from `glossary-candidates.md`), appendices, author's note. Only what was requested at intake.
5. **Frontmatter and backmatter** — assemble in standard order. The preface from Phase 5 goes in frontmatter here.
6. **Convert to final format** — markdown, website, docx, or pdf. For docx read `/mnt/skills/public/docx/SKILL.md`. For pdf read `/mnt/skills/public/pdf/SKILL.md`. For website read `/mnt/skills/public/frontend-design/SKILL.md`.
7. **Final scan** — confirm every reference resolves (TOC → chapter, index → page, figure list → figure).
8. **Present** with `present_files` alongside `consistency-report.md`, `sources.json`, and (if fiction) author's note.
9. **Library sync-back** (if any library items were imported at Phase 1, or if this book has produced reusable worlds/characters). Load `references/library-system.md`. For each item that has changed during the project, ask the user:
   - Snapshot only? (default — saves end-state to `~/library/<type>/<slug>/snapshots/`, leaves canonical untouched)
   - Update canonical and snapshot? (the project version becomes the new canonical)
   - Discard project changes? (the project's tweaks were book-specific only)
   
   For items that are new (never been in library) but might be reusable, ask: *"This world / character could be reused in future books. Save to library?"* If yes, create the library entry and the first snapshot. Update each item's `used-in.md`.

---

## State on disk

Every book project lives in one directory (default `/home/claude/books/<slug>/`):

```
<slug>/
├── project.json                # intake answers (including mode)
├── writer/
│   ├── persona.md              # copy of the chosen persona
│   └── sample-prose/           # optional prose samples for this writer
├── style-guide.md              # project-specific conventions (layered on the persona)
│
│ # Phase 2 deliverables depend on mode:
│
├── sources.json                # non-fiction (and fiction touching real things)
├── notes/                      # both modes, but different contents
│   │  # non-fiction:
│   ├── education.md
│   ├── relationship-babbage.md
│   │  # fiction:
│   ├── world.md
│   ├── timeline.md
│   ├── plot-skeleton.md
│   ├── locations.md
│   └── characters/
│       ├── protagonist-<slug>.md    # full profile (see characters.md)
│       ├── arc-<slug>.md            # arc + growth events
│       ├── knowledge-<slug>.md      # what they know, when
│       ├── antagonist-<slug>.md
│       ├── support-<slug>.md
│       ├── secondary.md             # minor named characters
│       └── relationships.md         # who-knows-whom, shared history, arc
│
├── outline.md                  # approved before writing
├── chapters/
│   ├── 01-a-portrait.md
│   ├── 02-the-engine.md
│   └── ...
│
│ # Apparatus candidate files (maintained during writing):
├── figures.json                # every figure, with caption/alt/source
├── figures/                    # the actual image files
│   ├── 1-1-portrait.svg
│   └── ...
├── index-candidates.md         # for building the index at assembly
├── glossary-candidates.md      # for building the glossary at assembly
│
│ # Phase 4.5 (Beta feedback) artefacts:  (absent if demo scope)
├── beta-round-1/
│   ├── manuscript.pdf          # the version sent to readers
│   ├── brief.md                # the reader brief
│   ├── readers.md              # who read, when, what type
│   ├── <reader>/feedback.md    # per reader
│   ├── synthesis.md            # what to act on
│   └── revision-log.md         # what changed and why
│
│ # Phase 4.6 (Fact-check) artefacts:
├── fact-check.md               # working claim list
├── fact-check-report.md        # final verification report
│
│ # Phase 5 (Manuscript Finishing) artefacts:
├── revision-structural.md      # Pass A findings and decisions
├── revision-line.md            # Pass B patterns
├── revision-copy.md            # Pass C patterns
├── preface.md                  # written last, after book is complete
├── introduction.md             # if the book has one
│
├── consistency-report.md       # produced in assembly
└── output/                     # final deliverable(s)
    └── book.docx
```

Persona library (global, reused across books):

```
~/writers/
├── margot-verschuere/
│   ├── persona.md
│   ├── sample-prose/
│   └── notes.md                # evolution log
└── ...
```


Character library (global, reused across books and series):

```
~/characters/
├── mina-murray/
│   ├── profile.md              # the deep profile
│   ├── voice-samples/          # samples of this character's voice
│   ├── series-state.md         # cross-book state tracking
│   └── notes.md                # evolution log
└── ...
```
This structure is what makes multi-day work possible. Always write to disk as you go, not just at the end.

---

## Interaction principles

- **Over-communicate during long runs.** When research or writing takes more than a few minutes, give progress updates. "Researching question 3 of 8" is better than silence.
- **Checkpoint at phase boundaries.** At the end of intake, research, outline, and assembly: summarise and ask if the user wants to continue or adjust.
- **Surface uncertainty, don't hide it.** Single-source claims, source conflicts, gaps in research — flag them. The reader of a well-made book trusts the author *because* the author is honest about uncertainty, not in spite of it.
- **Don't fabricate sources. Ever.** If you cannot verify a claim, say so and either remove the claim or mark it explicitly as unverified. A made-up citation is worse than no citation.
- **Respect the user's time budget.** If they say "I have two hours", scope accordingly — maybe research + outline today, writing tomorrow. Don't start a 40-hour project in the last hour before dinner.

---

## Reference files

Load these as you enter each phase:

**Always available:**
- `references/writer-persona.md` — the persona system: fields, storage, creation routes, the boundary between fictional persona and real-world facts. Read at Phase 0 and at the start of each chapter in Phase 4.
- `references/persona-archetypes.md` — 2–3 archetypal writers per genre, for Route C (archetype selection). Read at Phase 0 if the user picks that route.
- `references/anti-ai-tells.md` — **the most important file for output quality.** Thirteen recurring tells of AI-generated prose, with detection signals and counter-moves for each. Read at the start of every writing session, applied during self-critique on every chapter, and re-read after long writing sessions to recalibrate.
- `references/language-naturalness.md` — **the second most important file for output quality.** AI-generated text in any language tends toward smoothed-corpus-average syntax that reads as translated even when generated directly. Per-language patterns (Dutch, English, plus shorter sections for German, French, Spanish, others) with concrete before/after examples. Persona must specify language-naturalness preferences (which authors read, which insertion words, which constructions avoided). Applied per-paragraph during writing (Phase 4) and as dedicated revision pass during finishing (Phase 5). Universal failure mode that affects fiction and non-fiction equally — even when content, structure, and voice are correct, AI-default language betrays the AI origin. Without this discipline, prose feels translated regardless of how it was generated.
- `references/reading-level.md` — **constitutive constraint for any project not aimed at adult-literary-general readers.** Five dimensions of reading capacity (decoding, comprehension, background knowledge, conceptual density, attention span) and Western measurement systems (AVI for Dutch ages 6-12, Lexile for English, CEFR for second-language). Per-level craft notes for early decoding, confident decoding, advanced child / pre-YA, young adult, adult literary general, adult specialist / academic, and specialised registers (graded readers, adapted text, plain-language). Per-level anti-AI-tells: bevoogding for early decoding, adult-pretending-to-be-teen for YA, fake-academic-stance for academic. Persona and project reading level must match — if mismatched, build different persona or reframe project. Applied at intake (explicit reading-level scoping), at persona creation, during writing self-critique (only when project is non-default), and as revision pass at Phase 5 (most consequential for non-default projects).
- `references/extreme-constraint.md` — discipline for picture books at the most demanding end of early-decoding (Bruna register: 16x16 cm, 24 pages, 4 lines abcb rhyme per spread, ~200 word vocabulary, ages 3-5). Persona archetype for the Bruna-register writer who has read Bruna across his oeuvre, Schmidt at her most economical, Sendak. Pre-writing settlements: the one image, the arc, the vocabulary list, the rhyme constraints, the picture/text plan, the ending. Anti-AI-tells: lesson-at-end, vocabulary creep, adult-emotional-disguised, question-asking-narrator, comfort-not-matching-events, rhyme-driven-content-drift, generic-kindness-language, picture-redundant-text. Applied for picture-book projects only; overkill for any other register.
- `references/technical-documentation.md` — **the four-quadrant discipline for any project that produces technical documentation.** Diátaxis framework with reference / how-to / explanation / tutorial as orthogonal registers, each with own structure, voice, anti-AI-tells, and success criteria. Persona modalities: one persona writing in four modes (Pattern A) or four sub-personas under one project (Pattern B). New phases needed: codebase-analysis as Phase 2 substitute (public API inventory, dependency map, verification corpus), correctness-verification as Phase 5 finishing pass (every example compiled, every signature checked, every behavioural claim verified against source). Applied for projects documenting existing codebases, libraries, frameworks, SDKs, internal team systems, configuration references, protocol specifications. Default for documentation projects is full four-quadrant coverage; subset coverage acceptable when the project genuinely only needs one or two registers.
- `references/slice-methodology.md` — **methodology for multi-deliverable projects.** A slice is a coherent self-contained unit of deliverable work that, once complete, is independently useful. The methodology enforces finishing one slice fully before starting the next, preventing the all-fronts-half-finished trap. Applies to multi-volume narrative works, multi-language projects, technical documentation (which has its own slice patterns documented in `technical-documentation.md`), reference works with apparatus, book series with shared worlds. Does not apply to single-deliverable projects. When a project has natural slices, propose the methodology at intake (Phase 1) and create a `slices.md` tracking file in Phase 2.
- `references/claim-verification.md` — **the discipline of warranted assertions across all writing registers.** Every factual claim is either verified from a trustworthy source or explicitly marked as inferential. No third category. Strictest application in technical documentation; strict application in non-fiction (history, journalism, biography); applies in age-appropriate form to children's writing; applies to historical baseline in historical fiction. The mark-as-inferential pattern is documented with concrete signals (epistemic markers that point at real gaps versus AI-default hedge-stacking that signals nothing). Verification cycle: recognise the claim, trace it to a source, decide (assert / mark as inferential / cut). Integrates with Phase 0 (persona's actual sources of knowledge), Phase 2 (source list deliverable), Phase 4 (per-paragraph claim checks), and Phase 5 (dedicated verification pass separate from line-edit and copy-edit).
- `references/productive-puzzlement.md` — **didactic technique of problem-before-solution.** Set the stage with a concrete scenario, invite the reader's struggle explicitly, permit them to follow plausible wrong paths, deliver a satisfying resolution. The four-move structure that drives the most memorable didactic and technical writing (Feynman, Polya, Knuth). Anti-AI-tells: fake mystery (problem too easy), setup-too-long, skipping the wrong path (AI-default; the most common failure), unsatisfying resolution, excessive frequency (every concept gets the treatment), pseudo-Socratic question-tic. Use only when the concept is genuinely non-trivial, the difficulty is intuitively accessible, the resolution is satisfying, and the reader is in learning mode (tutorial and explanation registers only — not reference, not how-to). Phase 2 should identify the 3-10 central insights worth this treatment per book; Phase 5 includes a pedagogical-pacing pass to check that the technique is used enough but not too much. Most consequential for didactic and technical books — often determines whether the book is memorable or forgettable.
- `references/throughline-discipline.md` — **active maintenance of what the book is actually about.** The throughline is the single idea, story, argument, or question that holds the book together — distinct from topic, premise, outline, or moral. Formulated as a defensible one-sentence claim in Phase 3 (the `throughline.md` deliverable), actively checked per chapter in Phase 4 (does this chapter pull the thread forward, is the thread visible to the reader, does the framing serve this throughline or just the topic?), and verified in Phase 5 via a dedicated throughline revision pass. Anti-AI-tells: topical throughline (restatement of subject), inert thread-marking sentences, throughline-as-moral, decorative chapter openings, late conversion (throughline only in preface and conclusion, absent from middle chapters), throughline fatigue (over-stating to the point of becoming a tic). Cross-references productive-puzzlement (central insights must serve throughline), persona-modalities (modes vary, throughline does not), slice-methodology (each slice contributes to overall throughline), reality-grounding (borrowed elements must be load-bearing for throughline). Acknowledges legitimate exceptions: essay collections, anthologies, and certain experimental works may have a thematic field or curatorial throughline rather than an argumentative one.
- `references/chapter-mini-outline.md` — **mandatory section-level decomposition before chapter writing.** Each chapter gets a `chapters/NN-slug.outline.md` file with per-section purpose, opening anchor, beats (verb-driven, not thematic), sources, throughline-touch, and handoff to the next section. Produced as the first step of the per-chapter writing loop in Phase 4; shown to user without approval gate. Most chapters have 4-8 sections of 800-1500 words. Critical enabler for agents with smaller context budgets: lets section-at-a-time writing fit in modest per-call contexts, lets work resume across sessions, surfaces structural problems before any prose is generated. Anti-AI-tells specific to mini-outlines: sections-as-paragraphs (over-decomposition), purposes that are synonyms, beats that are themes, missing handoffs, decorative throughline-touch, word budgets that don't sum, evenly-spread sources. Required for every chapter regardless of length or who is writing.
- `references/book-formats.md` — physical format specifications by genre (trim sizes, words-per-page, lines-per-page, how non-prose elements affect page counts). Read at intake to give page targets meaning.
- `references/revision-mode.md` — operational mode for revising any part of the book at any time. Five revision types (targeted change, expansion, rewrite, cross-chapter consistency, structural). Load whenever the user signals a revision request — the trigger phrases are verbs of modification ("revise", "expand", "rewrite", "check", "verify"). Revision mode is orthogonal to phases.

**Non-fiction specific:**
- `references/genre-profiles.md` — profiles for textbook, academic, popular-technical, biography, narrative-history, school-textbook, memoir, self-improvement, essay-collection. Read during intake and at the start of writing. Includes ethical grounds for memoir (real-person constraints) and replication-crisis guidance for self-improvement.
- `references/research-protocol.md` — detailed research procedure, source reliability tiers, verification patterns, how to handle conflicts.
- `references/writing-craft.md` — narrative technique for non-fiction: opening hooks, weaving exposition, pacing, examples, handling technical depth.

**Fiction specific:**
- `references/fiction-craft.md` — fiction genre profiles, preparation (world, characters, plot skeleton), scene-craft, dialogue, POV, show-don't-tell, the truth rule for fiction.
- `references/characters.md` — the full character system for fiction: four depth tiers, templates, arc tracking, growth events, relationships as first-class entities, knowledge-state tracking, series support, library storage. Read at Phase 2 and consulted during writing for consistency checks.
- `references/library-system.md` — the persistent library at `~/library/` for worlds, characters, themes, and personas that survive across projects. Covers the existing-material check at Phase 1, working-copy mechanics during projects, and the snapshot/sync system at end of project. Lightweight: markdown files only, no database. Ensures writers don't re-create from scratch what they've already built; ensures consistency across books while permitting evolution.
- `references/reality-grounding.md` — the discipline of borrowing from real life at four scales: macro (history, politics, civilisation), micro (daily life and observed texture), the dark and strange (specific real case studies — named historical monsters, atrocities, unexplained events), and mythological/folkloric (Greek, Norse, Celtic, Biblical, Mesopotamian, Egyptian, Hindu, Chinese, Japanese, Yoruba, Mesoamerican, indigenous American, Polynesian, Slavic, Persian — both Western and non-Western traditions). The core principle is "borrow from reality, then choose against the template" — AI generation tends to produce the statistical average of how situations have been written before, and the discipline is to identify and refuse that average. Walk the user through this during Phase 2 preparation, before detailed world-building. Covers when each scale applies, what to ask, the writer-persona's credible knowledge constraint, the discipline of twisting/combining/parodying, ethical considerations for borrowing from real darkness and from living religious traditions.

**Shared (Phase 3 onwards):**
- `references/outline-template.md` — exact format for the approved outline. Works for both modes with small adjustments described in fiction-craft.
- `references/didactic-structure.md` — didactic architecture: expected prior knowledge, learning objectives (book-level and per-chapter), mid-book checkpoint, minimum topics, learning curve, exercise schemes, required tools, personal introduction forms. Load at intake if the user opts into didactic structure, again at outline and during writing for didactic checks.
- `references/figures-and-media.md` — **the core rule (when to add a figure: only when prose alone can't carry what the reader needs to picture)**, plus types of visual material, captions, numbering, alt text, generation routes (code, MCP, uploads, external sources). Read at intake, before drafting every chapter (visuals planning), and at assembly.
- `references/multi-volume.md` — six structural models for projects spanning multiple volumes (sequential, material+exercises, how+why, complementary, breadth+depth, parallel). Load at intake when total page estimate exceeds ~600 pages or when the user signals "this might be more than one book."
- `references/co-authorship.md` — voice patterns (alternating I, joint we, hybrid), chapter assignment, "would push back here" cross-references, conflict resolution. Load at intake when the project has two or more authors.
- `references/beta-feedback.md` — structuring beta reading, collecting feedback, separating signal from noise. Load at Phase 4.5 if beta readers will see the manuscript.
- `references/fact-check.md` — manuscript-wide verification pass, claim extraction, verification from zero. Load at Phase 4.6 for serious non-fiction.
- `references/manuscript-finishing.md` — the three revision passes (structural, line, copy-edit), writing the preface and introduction, and finalising the title and subtitle. Load at the start of Phase 5 (after all chapters drafted, before assembly).
- `references/citation-styles.md` — APA, Chicago (notes and author-date), MLA, IEEE, plain numeric. The five supported styles, conversion rules. Read at assembly.
- `references/book-apparatus.md` — TOC, index, glossary, frontmatter, backmatter, author's notes. Read during writing (to mark candidates) and at assembly (to build).
- `references/assembly.md` — consistency sweep, format-specific conversion (markdown, website, docx, pdf).
- `references/output-pipelines.md` — concrete scripts for markdown → docx and markdown → PDF assembly. Three routes (pandoc, pure-Python, pandoc+LaTeX template) with trade-offs. Includes runnable Python wrappers (`assemble_docx.py`, `assemble_pdf.py`). Load at Phase 6 when the user has specified docx or PDF output.

Don't read all of them upfront. Load the ones for the phase you're entering and the mode you're in.
