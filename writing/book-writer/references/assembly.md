# Assembly

The assembly phase turns a folder full of chapter drafts into a finished book. It has three core responsibilities:

1. **Consistency sweep** across all chapters
2. **Format conversion** to the chosen output (markdown, website, docx, pdf)
3. **Orchestration** of the apparatus-building that other reference files handle

The other work — citations, figures, apparatus — lives in its own reference files. Read them as you need them:

- `references/citation-styles.md` — convert `[src:N]` placeholders to APA / Chicago / MLA / IEEE / plain
- `references/figures-and-media.md` — resolve `[fig:slug]` placeholders, assign numbers, produce list of figures
- `references/book-apparatus.md` — TOC, index, glossary, frontmatter, backmatter

This file covers the consistency sweep (unique to assembly) and the format-specific conversion at the end.

---

## Part 1 — Consistency sweep

Ten chapters written by the same author across multiple sessions will drift. Terminology, names, dates, notation, cross-references, character behaviour — all of it needs a sweep before the book is called done.

Work through the checklist below. For each issue found, record it in `consistency-report.md` with: what the issue was, where it occurred, and how it was resolved. This report is an artefact the user sees — it's evidence the sweep happened.

### Terminology (both modes)

Build a glossary-in-progress by extracting all technical or named-concept terms from the chapters. Check:

- Does the same concept always get called the same thing? (e.g. "neural network" vs "neural net" vs "NN" — pick one or justify why they vary)
- When a term is first used, is it defined or at least situated? If a chapter introduces a term that was already introduced earlier, adjust.
- Abbreviations — are they spelled out on first use in each major section?

A fast way to do this: scan each chapter's text, extract candidate terms (capitalised nouns, quoted terms, terms introduced with "called" or "known as"), deduplicate, and look for near-duplicates.

### Names and spellings (both modes, critical for biography/history/fiction)

- Every person's name (real or fictional) — same spelling everywhere, including diacritics (Gödel, not Godel)
- Consistent use of first name / last name / full name per person, per the book's voice convention
- Titles and honorifics — consistent (Prof., Sir, Lady, etc.)
- Place names — consistent, and where historical vs modern names differ (Istanbul / Constantinople), pick the era-appropriate one and stay consistent

### Timelines and numbers (both modes)

- Dates mentioned in multiple chapters agree with each other
- Ages derived from dates are correct
- Statistics and numbers — where repeated, consistent. Where rounded differently (12% vs 11.7%), check it's deliberate.
- Currency, units — consistent conventions (metric or imperial, currency symbols)

### Notation (non-fiction, technical/academic)

- Variables and symbols mean the same thing throughout
- Equation numbering is consecutive and referenced correctly
- Typographic conventions — bold for vectors, calligraphic for sets, etc. — consistent

### Character consistency (fiction)

For fiction books, consult the files in `notes/characters/` during this sweep. They are the source of truth.

- **Voice:** Each character's voice stays recognisable from first to last appearance. Spot-check dialogue for each named character against their profile's voice notes.
- **Physical descriptions:** Eye colour, height, age, distinguishing features — same as established in the profile. No drift.
- **Knowledge state:** Consult `knowledge-<slug>.md` for each POV character. No character knows something in chapter N that they only learn in chapter N+k. This is the single highest-value character check.
- **Relationships:** Consult `relationships.md`. The state of each relationship — warmth, trust, conflict — follows the established timeline. A relationship that's frosty in ch. 6 and warm in ch. 7 needs cause in between.
- **Relationship timeline:** When the book mentions characters having known each other "for years" or "since university", check the backstory on the profile agrees.
- **Arc alignment:** For each protagonist/antagonist, walk their `arc-<slug>.md`. Did every listed growth event actually land? Did any unlisted change slip in? If yes, either revise the arc file (and accept the change as canonical) or revise the chapter (to make the change earned or remove it).
- **POV (multi-POV):** Every POV character sounds distinct from the others. If two POVs are hard to tell apart by voice, fix one.
- **Named characters:** Every named character appears at least twice (once-mentioned names are usually better unnamed). If a named character appears only once, either give them a second appearance or remove the name.

### Plot consistency (fiction)

- Timeline — events happen in a consistent sequence; if the narrative is non-linear, the underlying chronology still has to work
- World rules — magic/tech/social rules established early aren't violated later without explanation
- Setup and payoff — Chekhov's gun applies; things prominently placed should matter, and revelations should have been set up
- Foreshadowing — check that hints planted earlier resolve (or are deliberately abandoned)

### Cross-references (both modes)

When chapter 5 says "as we saw in chapter 2" (non-fiction) or "remember what Mina said at the Whitby hotel" (fiction), open the referenced chapter and verify it actually covered that. Cross-references are one of the highest-value consistency checks because broken ones are embarrassing and common.

### Voice and register (both modes)

Spot-check the opening and closing paragraphs of each chapter for voice. Major drift (chapter 4 is conversational, chapter 5 has shifted into academic register) needs reconciliation back to the persona and style guide.

### Citations (non-fiction)

- Every `[src:N]` in the text corresponds to an actual entry in `sources.json`
- Every source in `sources.json` that's marked as cited actually appears somewhere
- No source is cited without its ID being in its chapter's frontmatter `sources_used`

### Figures

- Every `[fig:slug]` in the text corresponds to an entry in `figures.json`
- Every figure in `figures.json` is referenced from at least one chapter (or explicitly marked decorative)
- Every figure has `status: final` by this point — nothing still `placeholder` or `described`

### Didactic consistency (if didactic structure enabled)

For books that opted into didactic structure, run these additional checks. The source of truth is the outline's didactic architecture block and each chapter's learning objectives.

- **Prerequisite-order check** (the highest-value one): for each chapter, list the concepts it uses. For each concept, confirm it was introduced in an earlier chapter or in the declared prior knowledge. A concept used-before-introduced is a fatal flaw for a didactic book. For long books with many concepts, consider writing a small script that extracts bolded first-use terms per chapter and builds a dependency graph.
- **Learning-objectives-met check:** every chapter has `learning_objectives_met` in its frontmatter. Confirm the chapter text actually delivers each one (not just mentions it).
- **Mid-book checkpoint delivery:** the book's structural halfway point — after chapter N/2 or at the end of Part I — should leave the reader where the outline promised. Re-read the checkpoint statement and the chapters leading up to it.
- **Minimum topics coverage:** walk the `minimum_topics` list from the didactic block of project.json. Every item appears in at least one chapter with real coverage (not just a passing mention).
- **Exercise and solution alignment:** every planned exercise is present; solutions are where the chosen scheme says they are (appendix / per-chapter / separate); the difficulty grading matches the outline's plan.
- **Glossary coverage (if didactic commits to "every bolded first-use"):** every bolded first-use term has a glossary entry; no term is bolded twice as if being introduced twice.
- **Required tools listed in preface:** the `required_tools` block from project.json appears, formatted, in the preface or a "Before you begin" section.
- **Personal introduction present (if planned):** if `personal_introduction` is biographical or thematic-anecdote, the preface or first chapter delivers it.

---

## Part 2 — Assembly-time sequence

After the consistency sweep, work through these in order:

1. **Resolve figures** — see `figures-and-media.md`. Assign chapter-based numbers, generate or confirm all image files, update figures.json with final numbers, produce list of figures if requested.
2. **Resolve citations** — see `citation-styles.md`. Walk every `[src:N]`, convert to chosen style, generate bibliography in the order required by the style. For footnote/endnote styles, generate the note entries.
3. **Build apparatus** — see `book-apparatus.md`. Generate TOC from chapter titles. Build glossary (from `glossary-candidates.md`) and index (from `index-candidates.md`) if requested. Appendices if requested.
4. **Paginate** — convert to final format (next section). This sets page numbers stable.
5. **Index resolution** — for index entries that were candidates, now resolve them to real page numbers in the paginated output. For ebook/web formats, use chapter/section anchors instead.
6. **Build frontmatter and backmatter** — in the standard order described in `book-apparatus.md`.
7. **Final scan** — every reference resolves (TOC → chapter, index → page, figure list → figure, cross-references in text).

---

## Part 3 — Format-specific conversion

### Markdown

Simplest case. Concatenate chapters in order, with the generated TOC at the top, frontmatter above that, backmatter at the end. One file, or one file per chapter with an index — ask the user.

Markdown has limited support for footnotes (`[^1]` syntax), figures with captions (use HTML `<figure>` blocks), and tables. For sophisticated apparatus, one of the other formats is usually better.

### Website (static HTML)

A multi-page static site:
- One HTML page per chapter
- Index page with the table of contents
- Prev/next navigation at the bottom of each chapter
- Clean typography — serif body font, generous line-height (≈1.6), max content width around 70ch
- Figures with `<figure>`/`<figcaption>`, click-to-enlarge for complex figures
- Footnotes as links to bottom-of-page notes, or as popover tooltips
- Read `/mnt/skills/public/frontend-design/SKILL.md` before styling — it has current design conventions

Convert markdown to HTML with a library that supports footnotes, tables, and code highlighting (Python: `markdown` or `mistune`; Node: `markdown-it`).

### docx

Read `/mnt/skills/public/docx/SKILL.md` and `references/output-pipelines.md` before starting. The output-pipelines file has concrete, runnable scripts; the docx skill covers Word's native features. Word has native support for the full apparatus — heading styles, auto-numbered captions, TOC fields, list of figures, cross-references, footnotes. Use these native features, not manual formatting:

- Heading 1 for chapter titles, Heading 2/3 for sections
- Consistent paragraph style (body text)
- Page break before each chapter
- Auto-generated TOC (Insert → Table of Contents)
- Captions for figures via Word's caption feature (enables list of figures)
- Footnotes via Insert → Footnote (not manual superscripts)
- Cross-references via Insert → Cross-reference (not hardcoded "see page 12")

The default route for docx is **pandoc with a reference template** (Route A in `output-pipelines.md`). The Python script `assemble_docx.py` takes a book directory and produces a single docx. For projects where pandoc isn't available, Route B (pure python-docx) is the fallback — more code to write, less polished output.

### PDF

Read `references/output-pipelines.md` for concrete scripts. Three routes are documented there:

1. **Pandoc + xelatex** (Route A) — markdown → PDF in one command, requires a LaTeX installation. Default for most projects. The `assemble_pdf.py` script wraps this.
2. **docx → PDF via LibreOffice** (Route B) — pure-Python pipeline, no LaTeX required. Quality is lower (kerning, hyphenation) but acceptable for review copies and beta distribution.
3. **Pandoc + custom LaTeX template** (Route C) — publication-grade typography, requires a custom `book-template.tex`. The route used for academic monographs and serious technical books.

For books over ~100 pages where typography matters, Route C earns the effort. For draft and review distribution, Routes A and B are faster.

---

## Final checklist before presenting to the user

- [ ] All chapters present, numbered correctly
- [ ] Table of contents matches actual chapters
- [ ] All `[src:N]` resolved; no placeholders left in output
- [ ] All `[fig:slug]` resolved to numbered figures; list of figures generated if requested
- [ ] Bibliography present if sources exist, formatted in chosen style
- [ ] Glossary built if requested
- [ ] Index built if requested (with correct page numbers from the paginated output)
- [ ] Frontmatter and backmatter match what was requested at intake
- [ ] Author's note / "On Sources" present if book touches real-world content
- [ ] Consistency report saved
- [ ] Output file opens correctly in its intended application
- [ ] File is in `/mnt/user-data/outputs/` if presenting to user
- [ ] `present_files` call will include the main output, the consistency report, and `sources.json`

Present the book with a short summary: length, number of sources, any single-source claims still flagged, any conflicts noted, apparatus pieces included. The user deserves to know what they're getting.

---

## Persona evolution check

At the very end, compare `<book>/writer/persona.md` with the original in `~/writers/<slug>/persona.md`. If they've diverged, ask the user:

> "The persona evolved a little while writing this book — [summarise the changes]. Want to fold these back into the library version for future books, keep them only in this book, or just log them in the evolution notes?"

If the user chose route "fold back", overwrite `~/writers/<slug>/persona.md` with the book version. If "log", append a timestamped note to `~/writers/<slug>/notes.md` describing the divergence. If "keep only in this book", do nothing — the library is untouched. This is described more fully in `writer-persona.md`.
