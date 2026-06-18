# Figures and media

A book earns the claim "a picture is worth a thousand words" only when the pictures are carefully chosen, properly captioned, consistently numbered, and correctly referenced in the text. Scattered unnumbered images are decoration; well-integrated figures are part of the argument.

This file governs all visual material: photos, diagrams, charts, tables, maps, illustrations, code listings. Read at intake (to establish approach), at the start of every chapter (to plan that chapter's visuals), and in assembly.

---

## The core rule — when to add a figure

There is one test that decides whether a figure belongs in your prose, and it works for every genre, every subject matter, every audience. The test is:

> **Does the reader need to visualise something here, and can prose alone reliably make them do it?**
> If yes, no figure. If no, add a figure.

That is the whole rule. Everything else in this file is in service of it.

The test has two parts. First, identify what the reader is being asked to picture. Some passages don't ask the reader to picture anything — they're carrying argument, emotion, or general framing, and they don't summon a mental image. Those passages need no figure. Second, when a passage *does* ask the reader to picture something, ask whether prose alone can carry that work. Sometimes it can. Sometimes it cannot.

When prose cannot carry the work, the figure is not optional. It is not "nice to have." It is what the chapter requires to do its job. A book about Roman conquest without a map of the empire's spread is *wrong*, not "less ideal." The reader is being asked to picture something prose cannot reliably reconstruct in their head. The map is required.

When prose can carry the work, a figure is decoration. Decoration costs the reader attention without paying it back. Worse, decorative figures make readers stop trusting figures generally — when a book has too many "look at this" pictures with no informational role, readers start skimming all the figures. The required figures lose their effect.

### Worked examples — the rule in different genres

The rule is genre-agnostic. The same test applied across different books gives different answers, all correct.

**A history book about Roman conquest.** Reader needs to picture the empire's territorial extent. Prose alone? "Spanned from the Atlantic to the Euphrates, with a northern boundary along the Rhine and Danube, southern boundary through the Sahara, and eastern reaches into Mesopotamia..." Three sentences in, the reader is lost. **Map required.** Reader needs to picture Caesar's face? Maybe — but prose has described faces for two thousand years, and a generic Caesar is in most readers' heads already. Unless the chapter is about how sculptors depicted him (the bust *is* the subject), no figure required.

**A biography of a composer.** Reader needs to picture the composer's score handwriting? If the chapter is about their composition process, yes — show a manuscript page. If the chapter is about their childhood, no — their handwriting isn't the subject. Reader needs to picture the cities they lived in? Maps if the chapter discusses geography substantively; not otherwise.

**A memoir.** Reader needs to picture a feeling of grief or longing? Prose. Always prose. No figure ever made grief more legible than well-written prose. Reader needs to picture the family farm where the memoir is set? If the farm's geography is part of the story (this is where the river was, that's where the sister was found) — a sketch or photo helps. If the farm is just where things happened — no figure.

**A self-improvement book.** Reader needs to picture a four-step framework? A diagram makes it stick. Reader needs to picture how habits form? Often a flow diagram clarifies what prose makes wordy. Reader needs to picture the author's general philosophy? Prose. Frameworks visualise; philosophies don't.

**A book on game engine architecture.** Reader needs to picture archetype-component memory layout? Diagram. The relationship between two-dimensional storage and one-dimensional iteration is exactly what prose describes badly. Reader needs to picture how a fiber yields control to a scheduler? Diagram or pseudo-code — concurrent state in two parties at once is what prose handles worst. Reader needs to picture *why* engines have job systems? Prose. The reasoning is verbal; no figure helps.

**A novel.** Reader needs to picture a character's internal struggle? Prose. Reader needs to picture the layout of a fictional city central to the plot? A map can work — Tolkien used them, many fantasy novels do. Reader needs to picture a complex family lineage where many characters share names across generations? A family tree front-of-book. Otherwise, no figures.

**A cookbook.** Reader needs to picture the finished dish? Photo. (This one is genre-mandatory — cookbook readers expect to see the dish before they commit to making it.) Reader needs to picture an unfamiliar technique like "the windowpane test for kneaded dough"? Process photo or illustration. Reader needs to picture an ingredient list? Just print the list — no figure.

**A scientific or technical textbook.** Reader needs to picture a molecular structure? Diagram. Reader needs to picture a force decomposition on an inclined plane? Diagram. Reader needs to picture how an algorithm walks through a data structure? Diagram or trace-table. The pattern is consistent: where the subject involves spatial relationships, structure, or simultaneous state, figures are required, not optional.

### What the rule excludes — and what it includes

The rule excludes two kinds of figures that creep in when nobody applies it.

**Decorative figures.** A bust of Caesar in a chapter about his military campaigns. A stock photo of "people working together" in a self-improvement chapter on collaboration. An aerial photo of a city in a chapter that doesn't discuss the city's geography. These are decoration — they don't help the reader picture anything they couldn't picture without them. They cost attention. Cut them.

**Pleonastic figures.** A diagram that depicts exactly what the prose just said, with no additional information. A flowchart showing "step 1, step 2, step 3" when the prose just enumerated three steps in a single sentence. A bar chart showing two numbers that the prose stated. These don't fail by being decorative — they fail by being redundant. The figure repeats the prose; the prose now has to compete for attention with its own echo. Cut them.

The rule includes things some authors don't think of as figures:

- **Code listings** — required when the reader needs to picture how a piece of behaviour is expressed in syntax
- **Pseudo-code** — required when the reader needs to picture an algorithm's flow but the language details don't matter
- **Equations** — required when the relationship between quantities is the thing being communicated
- **Tables** — required when the reader needs to picture a comparison across multiple dimensions
- **Timelines** — required when the reader needs to picture what happened when, and when the order or duration matters
- **Family trees and organisational charts** — required when the reader needs to picture relationships among many entities
- **Maps** — required when the reader needs to picture geographic or spatial relationships

If a chapter asks the reader to picture any of these things and prose alone struggles, the figure is required.

### The "would I be able to reconstruct this from prose?" self-test

The most useful question to ask while drafting:

*If I closed my eyes and listened to a friend read this section to me, would I be able to draw what they're describing?*

If yes, prose is doing its job — no figure needed. If no, ask whether figure is the right answer or whether prose itself needs to be clearer. Sometimes the answer is that the prose is genuinely struggling because the topic is one prose cannot reach. Sometimes the answer is that the prose is just badly written. Try improving the prose first; if after revision the topic still resists prose, the figure is needed.

This test works for every kind of visualisation — geographic, structural, temporal, emotional. The friend reading aloud is the human ear; what reaches it through speech alone is what prose can carry. What doesn't reach it needs a figure.

### A scaling note

The rule is the same for a 200-page memoir and an 800-page treatise. The *frequency* with which a chapter triggers the rule will differ enormously by genre and topic — a memoir chapter may have zero figures; an engine architecture chapter may have eight. That difference is not a separate rule for each genre; it's the same rule applied to different content. Memoirs ask the reader to picture different things than treatises do, and most of what a memoir asks for is exactly what prose handles best.

If you find yourself with no figures across a long technical chapter, suspect that you missed places where the reader needs to visualise. If you find yourself with many figures across a memoir chapter, suspect decoration.

---

## The chapter-level workflow — Plan visuals before drafting

Apply the rule before the chapter is drafted, not after. The workflow:

1. **Read the chapter's outline entry.** Note what the chapter is asking the reader to understand.
2. **List what the reader has to picture.** For this chapter specifically: what mental images does the reader need to form? Be concrete — "the layout of archetype storage", "the territory of Gallia in 58 BCE", "the relationship between five characters", "the four-step framework for habit change".
3. **For each item, apply the prose-alone test.** Can prose by itself put this image in the reader's head reliably? Be honest. The test fails more often than authors expect.
4. **For items where prose alone won't work, choose a visualisation form.** Map? Diagram? Table? Photo? Code listing? Family tree? Timeline?
5. **Write the visuals plan to disk** as `chapters/NN-visuals-plan.md` (or as a section in a shared plan file). Brief — usually a list of 3–8 items, each with a one-line description and an intended location in the chapter ("opening", "after the storage discussion", "near the end where examples come together").
6. **Then draft the chapter** with those visuals as known anchors. The prose can refer to them by their slug (`[fig:archetype-storage]`) and assume they'll be there. The chapter is being built around them, not the other way around.

This planning step takes five to fifteen minutes per chapter. It saves hours of "wait, this section doesn't have the diagram it needs" rework later. It also produces a consistent figure density that follows substance rather than habit.

### A worked example — visuals plan for a chapter

For an ECS implementation chapter in a game engine book, a plausible visuals plan:

```
Chapter 5 — Building the ECS — Visuals plan

Reader needs to picture:
1. How components are stored per archetype (memory layout, columnar)
   → fig:archetype-storage-layout — diagram, after introducing storage
2. How a query iterates across archetypes
   → fig:query-iteration — diagram, in queries section
3. The cost of add/remove component (entity moving between archetypes)
   → fig:archetype-graph — graph diagram, in modification section
4. The sparse-set alternative, side-by-side
   → tbl:archetype-vs-sparseset — comparison table, in alternatives section
5. The minimum working code (entity ID type, archetype struct, query fn, system fn)
   → 4 code listings: 10–25 lines each, distributed through the chapter

Items where prose alone is enough:
- Why ECS exists at all (verbal, conceptual)
- Why we chose archetype over sparse-set for Catalyst (argumentative, decision)
- The discipline of "components are data, systems are functions" (philosophical)

Total: 3 diagrams, 1 table, 4 code listings.
```

Compare to a Roman-history chapter on the conquest of Gaul:

```
Chapter 4 — The Conquest of Gaul — Visuals plan

Reader needs to picture:
1. The territorial extent of Gallia and the tribal regions before 58 BCE
   → fig:gaul-pre-conquest-map — political map of the tribes
2. Caesar's campaign route year by year
   → fig:caesar-campaign-route — map with date-stamped movement
3. The siege of Alesia — circumvallation and contravallation
   → fig:alesia-siege-map — tactical diagram
4. The chronology of the war 58–50 BCE
   → fig:gallic-wars-timeline — timeline
5. The legions deployed and where
   → tbl:legions-by-year — table

Items where prose alone is enough:
- Caesar's strategic mind and political motivations (character/argument)
- The cultural impact of the conquest on Gallic society (analysis)
- Why this campaign mattered for Roman politics (argument)

Total: 3 maps, 1 timeline, 1 table.
```

Same rule, different content, very different visuals. That is the rule working.

---

## Types of visual material

| Type | What it is | When to use |
|---|---|---|
| **Figure** | Any image — photo, diagram, illustration, chart | Default term for visual material |
| **Table** | Structured data in rows and columns | Comparison, specifications, structured data |
| **Map** | Geographic or conceptual spatial representation | History, travel, worldbuilding, architecture |
| **Equation** | Mathematical statement, often numbered | Academic, technical books |
| **Code listing** | Code block, usually numbered and titled | Programming books |
| **Inline image** | Small image without a number or caption | Decorative or closely-integrated visuals |

Most share the same machinery: they have a **number**, a **caption**, they're **referenced in the text**, and they appear in a **list** at the front or back. Equations and code listings follow the same pattern but with their own numbering sequence (Equation 3.2, Listing 5.1).

---

## During writing: placeholders versus inline rendering

There's an important distinction the skill must make: **some figures and tables can be rendered directly in markdown; others require external production.** The handling is different.

### Markdown-native artefacts — produce inline, do not defer

If the visual can be expressed in markdown-native syntax — meaning a markdown viewer or compiler will render it directly — produce it **directly in the chapter text**, not as a placeholder. The reader who opens the markdown sees the visual immediately. The reader doesn't see "[fig:something]" with the diagram waiting for assembly.

These are the markdown-native types:

**Mermaid diagrams** (rendered by GitHub, GitLab, most markdown viewers, and pandoc with the right plugins). Suitable for:
- Flowcharts and process diagrams
- State machines
- Sequence diagrams
- Simple class/relationship diagrams
- Graph diagrams (archetype-graph, dependency-graph)
- Gantt charts
- Pie charts (sparingly)
- Block diagrams of system components

```markdown
​```mermaid
graph LR
    A[Start] --> B{Decision}
    B -- Yes --> C[Action 1]
    B -- No --> D[Action 2]
​```
```

**Markdown tables** (rendered by every markdown viewer). Suitable for:
- Comparison tables (2-5 columns, up to ~20 rows)
- Parameter tables
- Reference tables
- Decision matrices

```markdown
| Aspect | Option A | Option B |
|---|---|---|
| Speed | Fast | Slow |
| Memory | Low | High |
```

**ASCII art diagrams** (rendered by every markdown viewer in code blocks). Suitable for:
- Memory layout diagrams (bytes, fields, alignment)
- Simple binary tree or list structures
- Simple timing diagrams
- Stack frames
- Data structure visualisations where precision matters more than aesthetics

```markdown
​```
┌─────────────┬─────────────┬─────────────┐
│  Position   │  Velocity   │   Mesh      │
├─────────────┼─────────────┼─────────────┤
│ x: 0.0      │ x: 1.0      │ id: 42      │
│ y: 0.0      │ y: 0.0      │ mat: 7      │
│ z: 0.0      │ z: 0.0      │             │
└─────────────┴─────────────┴─────────────┘
​```
```

**Code listings** (already always inline — these are obviously markdown-native).

For all four types, **produce the artefact directly in the chapter text during drafting**. Do not use placeholders. Do not defer to assembly. The chapter is more readable in its draft form, the user can see what the chapter delivers, and the assembly phase has nothing to generate.

### External-production artefacts — placeholders are correct

For visuals that can't be rendered in markdown-native form, placeholders remain the right approach:

- Photographs (a portrait of a historical figure, an archival photo)
- Complex technical illustrations (anatomical diagrams, architectural drawings, scientific figures with specialised notation)
- Custom artwork (commissioned illustrations, icons, branded diagrams)
- Screenshots from running software (will be added during writing or assembly when the software exists)
- Vector illustrations beyond what mermaid can do (multi-panel figures, annotated photographs, complex spatial diagrams)
- Equations rendered with LaTeX (some markdown viewers support this; if your target output requires it, treat as inline; otherwise placeholder)

For these, use the placeholder pattern below and resolve at assembly.

### How to choose

When you're about to add a visual, ask: **can a standard markdown viewer render this?**

- If yes → produce it inline in the chapter, no placeholder
- If no → use a placeholder, register in `figures.json`, generate during assembly

Common mistake: producing a placeholder for something that should have been a mermaid diagram or markdown table. The reader opens the chapter, sees a `[fig:slug]` orphan, and the chapter fails its job. If the visual is something a markdown viewer can render, do it in markdown.

Common mistake in the other direction: trying to render a complex technical illustration as ASCII art when it needs proper vector graphics. ASCII art has its place but doesn't substitute for a real diagram in genres where precision and detail matter (medical illustrations, complex circuit diagrams). For those, placeholder.

### Tables specifically — always inline

Markdown tables render everywhere. There is essentially no reason to use a placeholder for a comparison table. Even rough drafts of comparison tables should be in markdown form, with the rough content. They can be polished later, but they should never be empty placeholders.

If the table content isn't decided yet, write it as:

```markdown
| Aspect | Option A | Option B |
|---|---|---|
| Speed | TBD | TBD |
| Memory | TBD | TBD |
```

The structure is committed; the content is to be filled. This is much better than `[tbl:comparison-name]` with no rows. The next pass fills in the TBDs.

---

## During writing: placeholders for external-production artefacts

For figures that require external production (photos, complex illustrations, screenshots), use placeholders:

```markdown
[fig:gc-mark-sweep-diagram]

The basic mark-and-sweep algorithm works in two passes. See [fig:gc-mark-sweep-diagram]
for the flow. In the first pass...
```

The placeholder `[fig:slug]` is a unique identifier. The assembly phase resolves it to a real figure with number, caption, and (if available) the image itself. Numbers are assigned at assembly time so they stay correct when chapters are reordered.

Also record the figure in `<book>/figures.json`:

```json
{
  "figures": [
    {
      "id": "gc-mark-sweep-diagram",
      "type": "figure",
      "chapter": 4,
      "caption_short": "Mark-and-sweep garbage collection",
      "caption_full": "Mark-and-sweep garbage collection in two passes. Reachable objects are marked in the first pass; unmarked objects are freed in the second.",
      "source": "original|generated|uploaded|external",
      "source_details": "...",
      "alt_text": "Flowchart showing two passes over a memory heap...",
      "status": "placeholder|described|generated|uploaded|final",
      "file_path": "figures/gc-mark-sweep.svg",
      "attribution": "if not original, attribution line for captions and credits",
      "license": "if applicable"
    }
  ]
}
```

The `status` field tracks where each figure stands. During writing most will be `placeholder` or `described`; by end of assembly all should be `final`.

---

## Creating figures — five routes

### Route A: describe and defer

Write a clear description of what the figure should show. Useful when:
- The user will provide the image later
- You're in drafting mode and don't want to lose momentum
- The image requires specific data or real photography you can't produce

Save the description as `caption_full` in `figures.json` and leave `file_path` empty. The status is `described`. At assembly time the user is prompted to supply the actual image.

### Route B: generate with code (matplotlib, svg, mermaid)

For charts, diagrams, flowcharts, and simple schematic illustrations, Claude can generate the image directly.

**Tools available:**
- **matplotlib / plotly** — numerical charts (line, bar, scatter, histogram). Great for data visualisation.
- **SVG directly** — custom diagrams, schematics, technical illustrations. Precise control.
- **Mermaid** — flowcharts, sequence diagrams, state machines, entity-relationship diagrams. Easy syntax, limited to supported diagram types.
- **Graphviz** — graph diagrams where layout is mechanical.
- **TikZ** (if LaTeX output) — publication-quality technical figures.

Save generated images to `<book>/figures/<id>.svg` or `.png`. Update `figures.json` with the path and set status `generated`. Include the generating script/source alongside the output image (e.g. `figures/gc-mark-sweep.py` or `figures/gc-mark-sweep.mmd`) so it can be regenerated.

### Route C: generate via MCP (image generation, diagram services)

If the user has relevant MCP connectors enabled, they can produce higher-quality or specialised output. Common ones:

- **Mermaid Chart MCP** — validates and renders Mermaid to clean SVG
- **Excalidraw MCP** — hand-drawn-style diagrams
- **tldraw MCP** — sketch-style diagrams
- **Goodnotes MCP** — SVG drawings and Mermaid
- **Figma / Lucid / Miro MCP** — professional diagram tools

Before generating via code (Route B), check whether an MCP route would produce better results. If the user doesn't have a relevant MCP connected and the figure would benefit from one, **suggest it** via `suggest_connectors` rather than forcing a lower-quality code-generated version.

### Route D: user uploads

The user may provide their own images — photographs, scans, licensed stock, or art they've commissioned. These go in `<book>/figures/` with whatever filename. Update `figures.json` to point to them, status `uploaded`, and capture attribution and license in the JSON.

### Route E: existing / external with permission

Historic photos, public-domain images, Creative Commons material. Follow copyright carefully:

- **Public domain** — free to use, but credit where appropriate ("Photograph, c. 1890, public domain")
- **Creative Commons** — follow the specific licence terms (attribution is always required)
- **Fair use** — possible for limited critical purposes, but uncertain; when in doubt, don't
- **Anything else** — the user must confirm they have the rights

Never assume an image found on the web is free to reuse. Record license details in `figures.json.license`.

---

## Captions

A good caption has two jobs: identify the figure, and tell the reader something they couldn't extract just by looking.

**Format:**

> **Figure 4.3** — Mark-and-sweep garbage collection. Reachable objects are marked in the first pass; unmarked objects are collected in the second. Note that the time cost is proportional to the *total* number of objects, not only the live ones — a key limitation addressed by generational collectors in Section 4.6.

Components:
- **Label** (Figure 4.3) — generated at assembly
- **Short caption** (Mark-and-sweep garbage collection) — what the figure is
- **Full caption** — what the reader should understand from it; may point forward or back
- **Attribution** — where needed, below or inside the caption

A caption that just repeats the figure title is a missed opportunity. Use captions to teach.

---

## Alt text

For every figure, produce alt text — a description for readers using screen readers or for when the image fails to load. Store in `figures.json.alt_text`.

Alt text is not the caption. The caption is for sighted readers looking at the image; alt text substitutes *for* the image. Write it so someone who cannot see the figure gets the same information.

- For a chart: "Line chart showing GDP growth from 1950 to 2020; three recessions are visible as dips in 1974, 1991, and 2008. Overall trend is upward."
- For a photograph: "Ada Lovelace, seated, in a dark silk dress, looking past the camera. Oil portrait by Alfred Chalon, c. 1840."

---

## Numbering

Figures are numbered consecutively within their chapter: Figure 1.1, 1.2, 2.1, 2.2, 3.1... The format `Chapter.Sequence` is standard. Alternative schemes (book-wide continuous numbering 1, 2, 3...) work for short books but get awkward above ~20 figures.

Tables and equations have their own number series: Table 2.1, Table 2.2 runs parallel to Figure 2.1, 2.2.

**Rule:** numbers are assigned at assembly time, not during writing. Use placeholders with stable IDs (`[fig:slug]`) so references stay valid when chapters are reordered or figures added.

---

## Cross-references in the text

Placeholders in the writing phase look like `[fig:slug]`. At assembly, these resolve to "Figure N.N" in the running text, sometimes with a page number depending on format.

**Good references integrate with the prose:**

> As we saw in [fig:gc-mark-sweep-diagram], the second pass is where the actual freeing happens.

Becomes:

> As we saw in Figure 4.3, the second pass is where the actual freeing happens.

**Avoid:**

> The following figure shows the algorithm:
> [fig:gc-mark-sweep-diagram]

"The following figure" and "the figure above" are fragile — in digital formats figures may not be positioned where prose places them. Always reference by number/ID.

---

## Lists of figures / tables / etc.

For books with more than ~10 figures or tables, include a list at the front (after the table of contents). Generated at assembly from `figures.json`.

```
List of Figures

Figure 1.1 — A portrait of Ada Lovelace, 1840 ............. 12
Figure 1.2 — The family tree of the Byrons ................. 18
Figure 2.1 — Babbage's Difference Engine, partial ........... 31
```

Separate lists for tables, maps, and other specialised visual types where numerous.

---

## Tables

Tables share the figure machinery but have their own format. A table placeholder in the text:

```markdown
[tbl:compiler-comparison]
```

In `figures.json` (or a separate `tables.json` if preferred — doesn't matter much):

```json
{
  "id": "compiler-comparison",
  "type": "table",
  "chapter": 2,
  "caption_short": "Comparison of compiler architectures",
  "caption_full": "Comparison of compiler architectures across four dimensions.",
  "content": "markdown|html|csv reference",
  "file_path": "tables/compiler-comparison.md"
}
```

Tables can live inline in the chapter markdown (for simple tables) or as separate files (for complex tables, or when the final format needs special formatting).

**Design rules for tables:**
- Header row in bold; data rows plain
- Align numbers right, text left, headers to match their column
- Use units in the header, not the cells (km/h in header, "30" in cell)
- Keep cells short; if a cell needs explanation, footnote it
- Horizontal rules sparingly — only above and below the header and at the bottom
- Avoid vertical rules unless absolutely necessary

---

## Format-specific concerns

### Markdown

Figures are inserted as:
```markdown
![Figure 4.3: Mark-and-sweep garbage collection. Reachable objects are marked...](figures/gc-mark-sweep.svg "Mark-and-sweep")
```

Markdown has limited caption support natively — convert to HTML blocks for books that need real captions:
```html
<figure>
  <img src="figures/gc-mark-sweep.svg" alt="...">
  <figcaption><strong>Figure 4.3</strong> — Mark-and-sweep...</figcaption>
</figure>
```

### Website

Full HTML `<figure>`/`<figcaption>` semantics. Lazy-load for performance. Consider click-to-enlarge for complex figures.

### docx

Word has native figure support. Read `/mnt/skills/public/docx/SKILL.md` before generating — it explains how to insert images with captions that Word recognises (which is what makes auto-numbering and lists-of-figures work).

Key points:
- Insert figures as inline, not floating, for stable layout
- Use Word's caption feature (Insert → Caption) for auto-numbering
- Use the same caption label ("Figure" or "Tabel" in Dutch) consistently
- For the list of figures, use Insert → Table of Figures

### PDF

Same as docx if generating via docx → PDF. For LaTeX route, `\figure` and `\caption{}` with `\label{}` give proper cross-referencing and auto-numbered lists.

---

## Figures during fiction

Fiction books rarely have figures, but some do:

- **Historical fiction** — maps of the setting, family trees of characters
- **Epistolary novels** — images of documents (Dracula's newspaper clippings)
- **Children's fiction** — illustrations
- **Experimental fiction** — Jonathan Safran Foer, Mark Z. Danielewski: typography, photographs

The same machinery applies. Fiction doesn't need attribution for invented maps and trees, but any included photographs or documents follow normal copyright rules.

---

## Final checklist before assembly

- [ ] Every `[fig:slug]` in the text has a matching entry in `figures.json`
- [ ] Every figure in `figures.json` is referenced from at least one chapter, OR is marked "frontispiece" or similar decorative use
- [ ] Every figure has: caption, alt text, attribution (if not original), licence (if applicable)
- [ ] Every figure has `status: final` — nothing still `placeholder` or `described`
- [ ] Numbering is consecutive within each chapter
- [ ] List of figures generated if figure count warrants
