# Didactic structure

Most books teach the reader something. Some books make that teaching explicit — learning objectives up front, exercises after chapters, progress checkpoints, stated prerequisites. Other books teach by example and story without ever calling it teaching. Both approaches work; they work for different books.

This file covers how the book-writer skill handles didactic structure: when to ask for it, what the components are, how they show up in the outline, and how they surface (or don't) in the finished book. Read during intake if the user opts into didactic structure, and again during outline to wire the learning objectives into chapters.

---

## When didactic structure applies

At intake, the user is asked one question: **does this book need didactic structure?** Not tied to genre — a biography can have reflection questions, a thriller probably can't but a craft book on writing thrillers can. The question is about this specific book's intent toward its reader.

A "yes" opens a subset-intake covering the fields below. A "no" skips the whole thing; the book gets written without explicit learning architecture, though the persona and outline will still teach in their own ways.

Default recommendations:
- **Textbook, academic, school textbook, popular-technical** — almost always yes
- **Biography, narrative history** — usually no, but sometimes "light" (a short reflection prompt per chapter)
- **Fiction** — typically no; if yes, usually for craft-of-writing books that are technically non-fiction about fiction

If the user is unsure, ask what they want the reader to do after finishing the book. If the answer involves "be able to", "know how to", or "understand how to" — didactic structure probably helps. If the answer is "feel", "see", or "understand who X was" — it probably doesn't.

---

## The fields, if didactic structure is chosen

### 1. Expected prior knowledge

What does the reader need to already know before opening this book?

Ask for this concretely. Not "some programming experience" — "the reader is comfortable writing C++ classes, has used at least one graphics API at some level (OpenGL tutorials count), and is not afraid of linear algebra." Specificity matters because it determines which concepts can be assumed and which need introduction.

Record in `project.json`:
```json
"expected_prior_knowledge": {
  "required": [
    "comfortable writing C++ classes",
    "familiar with 3D coordinate spaces",
    "basic linear algebra (dot products, matrix multiplication)"
  ],
  "helpful_but_not_required": [
    "prior exposure to any shading language",
    "experience with a graphics debugger"
  ],
  "explicitly_not_required": [
    "prior HLSL knowledge",
    "GPU architecture knowledge"
  ]
}
```

The third field — "explicitly not required" — is important. It tells future chapters what they must take care to explain. A chapter that assumes the reader already knows GPU architecture when the intake said that's explicitly-not-required is a drift that the consistency sweep should catch.

The expected prior knowledge shows up in the book's preface ("This book assumes you've worked with C++ and at least poked at a graphics API. It does not assume you've written shaders before."). Whether it appears per-chapter depends on the "learning-objectives-visibility" decision below.

### 2. Overall learning objective (book level)

What should the reader be able to do, know, or understand after finishing the whole book?

Write this concretely and actionably. Bad: "understand HLSL." Good: "read, write, and debug HLSL shaders for real-time rendering, with genuine intuition for what the GPU is doing when those shaders run."

This is a slightly expanded version of the `learning_goal` field from the basic intake. For didactic books it gets more weight because it anchors every chapter's contribution.

### 3. Mid-book checkpoint — where is the reader at halfway

This is the single field most frequently absent from ad-hoc outlines. After the reader reaches the structural midpoint of the book, what should they be able to do, even if they stopped reading then?

This matters because:
- It forces the author to design the book's halves as coherent units
- It gives the reader a natural pause-point with a sense of completion
- It prevents the "everything comes together in the last chapter" failure mode

Example: "After Part II, the reader can write a correctly-structured HLSL shader pair, read existing shader code without getting lost, and debug common failure modes with RenderDoc. The physically-based rendering in Part III builds on this foundation."

For books with Parts, this typically sits at the Part I → Part II boundary. For books without Parts, it sits between chapters N/2 and N/2+1.

### 4. Minimum topics to cover

What must this book absolutely include, regardless of structural choices?

This is a short list (5–15 items) of non-negotiable coverage. It's the backstop: if the outline grows in some direction, the minimum-topics list is checked to make sure nothing fundamental was displaced.

Example for an HLSL book:
```
- GPU execution model (waves, lanes, divergence)
- HLSL type system including vectors and swizzles
- Resource binding and the CBV/SRV/UAV model
- The graphics pipeline, all stages
- Compute shaders
- Shader debugging with RenderDoc or equivalent
- Basic lighting (Lambert, Blinn-Phong)
- Physically-based rendering basics
```

If the outline's chapters don't cover one of these, that's a gap to surface before approval.

### 5. Learning curve profile

Shape of the difficulty curve across the book:

- **Gentle-throughout** — easy start, easy middle, easy end. Suitable for introductions, "Dummies"-style popular books, school textbooks for younger audiences.
- **Gentle-to-steep** — eases reader in, ramps up. The most common textbook shape. Early chapters readable to near-novices; later chapters demand serious engagement.
- **Steep-start-then-gentle** — front-load the hard conceptual work, then spend most of the book applying it. Works for books where the payoff is in depth, not breadth.
- **Uniform** — consistent difficulty from start to end. Works for specialist books where reader is already committed.
- **Peaked** — dense middle with lighter bookending. Hard chapters in the middle are harder because they're surrounded by easier ones; this lets them go deep without exhausting the reader.

This is recorded in `project.json` and honoured by the outline. A chapter's estimated length and density should reflect the curve.

### 6. Per-chapter learning objectives

Each chapter gets explicit learning objectives in the outline. These already exist in the current outline template (see `outline-template.md`), but didactic mode elevates them — they're not just notes to the author, they may be shown to the reader.

Per chapter:
```markdown
**Learning objectives:**
By the end of this chapter you will be able to:
- Explain the SPMD execution model in your own words
- Predict where wave divergence will and won't happen in shader code
- Identify helper lanes in a pixel shader scenario
- Recognise which operations are cheap vs expensive on a GPU
```

Form: "you will be able to" + action verb. Use **Bloom's taxonomy** verbs where useful:
- *Remember*: list, recognise, recall
- *Understand*: explain, summarise, classify
- *Apply*: implement, use, execute
- *Analyse*: compare, differentiate, distinguish
- *Evaluate*: critique, judge, defend
- *Create*: design, construct, produce

Avoid vague verbs — "know about", "be familiar with", "have an understanding of". They're unmeasurable and generally mean the author isn't sure what they want.

### 7. Visibility of learning objectives

Should learning objectives appear in the reader-facing text, or only guide the author internally?

Three options:

- **Shown per chapter** — each chapter opens with a "By the end of this chapter you will be able to..." box. Standard in school textbooks, popular in academic texts. Makes expectations explicit; can feel school-like for adult readers.
- **Shown at the book level only** — the preface or introduction states what the whole book teaches; individual chapters don't call out their own objectives explicitly. The narrative carries the teaching without framing it as teaching. Works well for popular-technical, professional books, and adult learners.
- **Internal only** — learning objectives guide every outline decision and every chapter's self-critique, but never appear in reader-facing text. The teaching is felt in the structure, not declared.

Default recommendation: "shown at book level only" for most adult non-fiction; "shown per chapter" for school textbooks and entry-level materials.

### 8. Exercises and check-your-understanding

Exercises serve different purposes and come in different shapes. The intake should capture which of these this book uses:

**End-of-chapter exercises** (full exercises, often with worked solutions):
- Numbered, increasing difficulty
- Answers location: appendix at back of book / right after each chapter / separate solutions manual / no answers given
- Typical count: 3–10 per chapter in a textbook; 1–3 in a popular-technical book

**In-chapter check-your-understanding questions** (short prompts, woven into the text):
- Usually one sentence, testing recall or quick application
- Answer is often just "think about it" without formal solution
- Serves as self-pacing rather than assessment
- Placed at section breaks or after introducing a dense concept

**Chapter-end reflection prompts** (especially for narrative, humanities, craft books):
- Open-ended questions, no correct answers
- "How would you approach X in your own work?"
- Suitable for biography-reflection, writing craft, leadership books

**Worked examples within chapters** (always a good idea for technical books):
- Not exercises — fully-solved problems showing the thinking
- Typically embedded in prose, not segregated
- Go in the text, not the exercise section

For each type the book uses, the intake captures:
- Whether it's used at all
- Where solutions appear (if applicable)
- Approximate count per chapter (rough — final count emerges in writing)
- Whether solutions are the author's ("here's how I'd do it") or canonical ("the answer is X")

### 9. Required tools

What does the reader need to follow along?

For technical books this is specific: software, hardware, accounts, purchases, reference materials. Example for an HLSL book:

```
Required:
- A Windows PC with a recent GPU (DirectX 12 capable, any recent NVIDIA / AMD / Intel)
- Visual Studio 2022 or equivalent C++ toolchain
- The DirectX 12 Agility SDK
- RenderDoc (free)

Recommended:
- A second monitor for debugger + code
- PIX for Windows (free)
- A reference Real-Time Rendering textbook for deeper dives

Optional / advanced chapters:
- Vulkan SDK (for the SPIR-V chapter)
- Access to a GPU with ray tracing cores (for DXR chapter)
```

This list goes in the book's preface or a dedicated "Before you begin" section. For books whose setup is complex, it may deserve its own chapter.

For non-technical books the "tools" might be different: a journal, reference photos for a biography reader, access to archives, etc. Ask anyway — the framing applies.

### 10. Personal introduction

Does the book open with a personal introduction from the author (via the persona)?

Two shapes:

**Author-biographical intro** — something about the persona's own life, usually situated in childhood or early career, that establishes who they are and why they care about the subject. "I grew up in the generation that saw the first personal computers arrive. The day my uncle brought home a Commodore 64 was the day I became someone else." Not about the book's topic directly — about the person.

**Thematic anecdote** — a personal story that opens the book's subject rather than the author's life. The HLSL chapter 1's opening ("I want to start with a confession. Early in my career, I drowned in HLSL complexity for six weeks...") is this shape — it's personal, but it's specifically about the thing the book teaches.

Either works; each does different work. The biographical intro establishes the author's authority and affinity for the subject before the book even begins. The thematic anecdote earns the book's claim more quickly, but tells the reader less about the person carrying them through.

Not every book needs one. A formal academic monograph typically doesn't. A popular-technical book usually benefits from it. A textbook depends on the target audience — school textbooks often skip it, graduate textbooks sometimes include it.

### 11. Glossary commitment

Related to didactic structure: will this book include a glossary, and what's in it?

The base skill covers glossary generation as an apparatus piece (see `book-apparatus.md`). Didactic books should commit up front:
- Every term introduced as a bolded first-use goes in the glossary
- Terms from prior knowledge ("we assume you know X") do not
- Glossary entries are 1–3 sentences, self-contained, written so someone flipping to the glossary out of context understands the term

The intake's expected-prior-knowledge list determines what doesn't need glossary entries.

---

## How didactic structure surfaces in each phase

### Intake (Phase 1)

A single gate question: "Does this book need didactic structure (explicit learning objectives, exercises, stated prerequisites)?" If yes, ask the didactic subset in one or two batches. If no, skip.

For demo / first-pass scope, the intake can collect only fields 1, 2, and 9 (prior knowledge, overall objective, required tools) — the rest can be filled during outline. For production scope, collect everything at intake.

### Preparation (Phase 2)

The prior-knowledge field informs research depth. Topics the reader is assumed to know need no research for exposition (we'll reference, not teach). Topics the reader is explicitly-not-assumed-to-know need research for introduction.

### Outline (Phase 3)

Per-chapter learning objectives become a required field. The mid-book checkpoint is tested: does the book's structural half actually deliver what was promised? The minimum-topics list is walked: does every required topic have a chapter or section?

### Writing (Phase 4)

At the start of each chapter, re-read that chapter's learning objectives. At the end of the chapter, check: did this chapter deliver what it promised? The self-critique includes this check.

If learning-objectives-visibility is "shown per chapter," the chapter opens with a learning-objectives box. If it's "internal only," the box is still part of the draft file (as HTML comment or YAML metadata) for tracking, but not rendered in the output.

Exercises are drafted at the end of each chapter, following the scheme chosen at intake.

### Assembly (Phase 5)

Final checks specific to didactic structure:
- Every bolded first-use term has a glossary entry (if glossary is planned)
- Exercise solutions are in the right place (appendix vs per-chapter)
- The preface mentions required tools and prior knowledge
- Cross-references between chapters respect the learning order (chapter 6 doesn't assume knowledge from chapter 9)

---

## The "prerequisite order" check

One quiet but high-value consistency check for didactic books: **does chapter N assume only what chapters 1 through N-1 have taught?**

Build a simple dependency check: for each chapter, what concepts does it introduce, and what does it assume? The concepts-introduced of chapter N must be a subset of concepts-introduced of chapters 1 through N-1, plus the declared prior knowledge.

This catches drift like "chapter 7 explains ray tracing but chapter 5 already used BVHs without explanation." It's worth running once at outline approval and once at assembly.

Can be done manually for short books; for longer books, consider a small script that parses chapters for bolded first-use terms and builds the dependency graph.

---

## What this file doesn't cover

- **The persona's teaching voice.** How the persona teaches (patient, rigorous, with anecdotes, etc.) is in `writer-persona.md`. The didactic structure here is about *what* gets taught and in what order; the voice of teaching is persona territory.
- **Genre-specific conventions.** School textbooks have structural conventions (chapter-opening learning goals, end-of-chapter summaries, sidebar definitions) that are partly didactic, partly genre. Those live in `genre-profiles.md` under the school-textbook profile.
- **Exercise writing as craft.** Good exercises are hard to write; this file says *whether* to include them, not how to craft each one. Craft guidance for exercises would belong in `writing-craft.md` as an addition.

---

## Quick reference: didactic fields in project.json

When didactic structure is chosen, `project.json` gains this block:

```json
"didactic": {
  "enabled": true,
  "expected_prior_knowledge": {
    "required": [...],
    "helpful_but_not_required": [...],
    "explicitly_not_required": [...]
  },
  "overall_learning_objective": "...",
  "mid_book_checkpoint": "...",
  "minimum_topics": [...],
  "learning_curve": "gentle-to-steep | steep-start-then-gentle | uniform | peaked | gentle-throughout",
  "learning_objectives_visibility": "per-chapter | book-level | internal-only",
  "exercises": {
    "end_of_chapter": {
      "used": true,
      "solutions_location": "appendix | per-chapter | separate | none",
      "typical_count_per_chapter": "3-7"
    },
    "check_your_understanding": {
      "used": true,
      "per_section": true
    },
    "reflection_prompts": {
      "used": false
    }
  },
  "required_tools": {
    "required": [...],
    "recommended": [...],
    "optional": [...]
  },
  "personal_introduction": "biographical | thematic-anecdote | none",
  "glossary_commitment": "every-bolded-first-use"
}
```

When didactic structure is not chosen, this block is absent — and the rest of the skill works exactly as before.
