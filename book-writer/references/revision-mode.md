# Revision mode

Up to this point, the skill has assumed a forward flow: persona → intake → preparation → outline → writing → manuscript finishing → assembly. That flow is correct for greenfield projects. But real books are revised throughout their lives, often at moments that don't fit any single phase.

The user might say:

- "Hoofdstuk 5 is te kort, breid uit"
- "Loop het hele boek na op anti-AI-tells"
- "Voeg een sectie toe over X aan hoofdstuk 12"
- "Reviseer hoofdstuk 8 met de nieuwe stijlgids"
- "Het bewijs voor de claim in hoofdstuk 3 paragraaf 4 is zwak — versterk het"
- "Schrijf hoofdstuk 7 helemaal opnieuw vanuit een ander uitgangspunt"
- "Het hele boek moet door de fact-check pass, ook al is alles al gedraft"
- "Maak de tabel in hoofdstuk 5 echt"

These are revision requests that arrive without warning, often months after a chapter was first written, sometimes after the book has been assembled, sometimes during beta feedback. The skill must handle them as a first-class workflow, not as awkward re-entries into the structural flow.

This file describes revision mode: when to enter it, how it differs from forward writing, what discipline it brings, and how the artefacts of revision are recorded.

Read at any moment when the user signals a revision request — the trigger phrases above, or anything similar. Read in full if the request is unfamiliar; skim the relevant sections otherwise.

---

## When the skill enters revision mode

Revision mode is triggered by user request, not by phase. It can be entered:

- During Phase 4 writing (revising an earlier chapter while still drafting later ones)
- During Phase 4.5 beta feedback (incorporating reader feedback)
- During Phase 4.6 fact-check (correcting factual claims)
- During Phase 5 manuscript finishing (which is itself a kind of revision phase, with its own structure in `manuscript-finishing.md`)
- During Phase 6 assembly (caught issues at assembly need fixes)
- After assembly (post-publication corrections, second editions)
- At any point when the user asks for revision

The skill's job is to recognise the trigger, enter revision mode for that specific request, do the work, and return.

### Trigger phrases

Common triggers (not exhaustive):

- "Reviseer / revise..."
- "Breid uit / expand..."
- "Werk uit / flesh out..."
- "Maak ... compleet / make ... complete"
- "Voeg toe... / add..."
- "Verwijder... / remove..."
- "Verkort... / shorten..."
- "Loop ... na op... / check ... for..."
- "Controleer... / verify..."
- "Schrijf ... opnieuw / rewrite..."
- "Reviseer het hele boek op... / revise the whole book for..."
- "Hoofdstuk N moet ..."

The trigger is in the verb. Forward writing uses verbs of creation ("schrijf", "draft", "begin"). Revision uses verbs of modification ("reviseer", "breid uit", "controleer", "verbeter").

---

## Types of revision request

Different revision requests need different procedures. Revision has two independent dimensions: **what kind of change** (the verb of revision) and **what scope** (the noun of revision). The five "types" below describe the most common combinations, but the dimensions can mix freely.

### The two dimensions

**The verb dimension — what kind of change.** Revision is not only addition. It includes all of the following, and the skill must handle each:

- **Add** — new material where there wasn't any (a new section, a missing code listing, a new example, a new figure)
- **Remove** — material that doesn't earn its place (a paragraph that doesn't add, a tangent that distracts, a redundant example, a forced metaphor, a triad that became a tic)
- **Replace** — material swapped for different material (a weak example for a stronger one, an outdated reference for a current one, a clumsy phrasing for a cleaner one)
- **Reorganise** — same material in a different order (paragraphs reordered for better argument flow, sections moved to a more logical position, a code listing relocated to where it's first needed rather than where it was originally drafted)
- **Restructure** — the chapter's overall architecture changes (sections merged or split, the spine of the argument refactored, the chapter's role in the book reconsidered)
- **Expand** — existing material made fuller (a paragraph that was too compressed for its own good, a one-line transition that needs to actually transition, a section sketch that needs to become a section)
- **Compress** — existing material made tighter (a passage that wandered, a long sentence that says less than its length suggests, a paragraph that could be three sentences)
- **Polish** — sentence-level work without changing meaning (rhythm, word choice, removing AI tells, fixing voice drift, sharpening a paragraph's first or last sentence)
- **Strengthen** — a claim made more defensible (better evidence, a real example replacing a generic one, a citation added, a hedge removed where commitment is warranted)
- **Soften** — a claim that overreached pulled back (a hedge added where overconfidence was unjustified, a "wrong" replaced with "less suited to this case")

These verbs are not mutually exclusive. A single revision request often involves several — *expand* this section, *replace* the example in it, *polish* the joins where new prose meets old.

**The scope dimension — what gets touched.** Independent of what kind of change, the change can be at any of these scopes:

- **Sentence** — a single sentence rewritten, replaced, or removed
- **Paragraph** — a paragraph reworked: split, merged, reordered, expanded, compressed
- **Section** — a section restructured, expanded, or replaced
- **Chapter** — a chapter as a whole, including its overall flow and architecture
- **Cross-chapter** — multiple chapters touched together (consistency sweeps, terminology unification, style alignment)
- **Book** — the entire book treated as one unit (full anti-AI-tells sweep, full fact-check pass, full reorganisation)

The skill must handle any combination of verb and scope. "Polish the third paragraph of chapter 5" is polish + paragraph. "Restructure chapter 8" is restructure + chapter. "Compress every chapter by 15%" is compress + book.

### The five common types

Most revision requests cluster into one of these five patterns. The procedure for each is described below; the underlying verb-and-scope combination is what the skill should hold in mind.

### Type 1 — Targeted change to a specific passage

"In hoofdstuk 5 paragraaf 3, de claim over EnTT klopt niet — corrigeer."
"De code in listing 5.7 mist een edge case voor empty archetypes — voeg toe."

The change is local. The author knows what's wrong and roughly how to fix it. The skill makes the change, runs a localised self-critique on the changed passage, and reports.

### Type 2 — Section or chapter expansion

"Hoofdstuk 5 is te kort. Breid uit."
"De query-sectie in hoofdstuk 5 is te dun, maak hem dieper."

The chapter or section needs more material. The skill identifies what's thin (using the original outline plus chapter content), generates additional material, integrates it, and runs a full self-critique pass on the affected chapter.

### Type 3 — Section or chapter rewrite

"Schrijf hoofdstuk 7 helemaal opnieuw."
"De opening van hoofdstuk 12 werkt niet — herschrijf."

The existing material is being replaced. The skill keeps the original (in version-control style), drafts the replacement following Phase 4 discipline (re-read persona, plan visuals, draft, self-critique), and either presents both for the user to choose or replaces directly per user instruction.

### Type 4 — Cross-chapter consistency revision

"Loop het hele boek na op anti-AI-tells en revisie waar nodig."
"Controleer of elk hoofdstuk zijn learning objectives waarmaakt."
"De terminologie voor X is inconsistent door het boek heen — uniformeer."

The change affects multiple chapters. The skill walks the affected chapters in order, applies the check or change to each, and produces a revision report showing what was changed where.

### Type 5 — Structural revision

"Hoofdstuk 5 en 6 moeten omgewisseld worden."
"Splits hoofdstuk 8 in twee."
"Voeg een hoofdstuk toe tussen 4 en 5 over X."

The book's structure changes. This affects outline, chapter numbering, cross-references, and frontmatter (lists of figures, etc.). The skill updates the outline first, then makes the structural change, then walks affected chapters to update cross-references.

---

## The revision workflow

For any revision request, the skill follows a procedure shaped by the request type. The general shape:

### Step 1 — Orient

Re-read what's needed:

- **Always**: `project.json`, `writer/persona.md` (or both for co-authored), `style-guide.md`
- **For chapter-specific revisions**: the chapter's outline entry, the chapter's current content, the chapter's `visuals-plan.md` if present
- **For cross-chapter revisions**: the relevant section of `outline.md`, plus enough chapters to understand the request

This orientation step is what makes revision mode different from blind editing. The skill is operating on a coherent project; it must inhabit the project before changing it.

### Step 2 — Diagnose

Before making changes, articulate what's wrong (or what's missing). Sometimes the user's request is precise ("add a TypeId mechanism to chapter 5"). Sometimes it's directional ("hoofdstuk 5 is te kort"). For directional requests, the skill must identify *what specifically* is missing — often by walking the chapter against its own outline.

The diagnosis is brief but explicit. "Hoofdstuk 5 mist: (1) de TypeId-machinerie, (2) de ComponentTypeInfo-definitie, (3) de complete World-klasse, (4) de tabel-inhoud voor archetype-vs-sparseset. Plus de pacing van de querying-sectie kan iets meer ademen."

The diagnosis is what the user can react to. The user might say "ja, fix die vier dingen, laat de pacing voor wat het is" — refining the scope before any work happens.

### Step 3 — Plan the revision

For non-trivial revisions, write a brief revision plan to `chapters/NN-revision-plan-<date>.md` (or similar). The plan lists:

- What's being changed
- What's not being changed (explicit, so the user knows what's deliberately left)
- Which artefacts need to move (visuals plan? new code listings? new references in sources.json?)
- Estimated change size (paragraphs, pages, sections)

For Type 1 (targeted change), the plan can be one sentence. For Type 2 or 3, it's a short list. For Type 4 or 5, it's substantial — possibly a sub-outline of the revision itself.

### Step 4 — Execute

Make the changes. The discipline depends on the type:

- **Type 1** — change the specific passage; check it reads well in context
- **Type 2** — add new material at marked insertion points; ensure prose flow is preserved at the joins
- **Type 3** — draft from scratch following Phase 4 discipline; re-use what's reusable from the old version (anchors, key examples) but don't be constrained by the old version
- **Type 4** — apply the check per chapter; record findings; make changes per chapter as needed
- **Type 5** — outline change first; chapter changes second; cross-reference and frontmatter sweep third

For all types, the new material is held to the same standards as forward writing: anti-AI-tells pass, visuals plan check, completeness check, voice consistency, etc. Revision is not exempt from quality checks; revised material gets the same scrutiny as fresh material.

### Step 4.5 — Read-through pass (mandatory after any revision that adds, removes, or reorganises material)

**This step is the one most often skipped, and the one that most often distinguishes good revisions from bad ones.**

After making the planned changes, read the whole chapter through, start to end, in one pass. Not for typos or anti-AI-tells — those come later. For *flow*. The questions:

- **Do the joins between old and new prose work?** When new material is inserted, the sentence before it and the sentence after it were written for a different chapter. They may now feel abrupt, or repetitive, or contradictory. The fix is usually small — a transition sentence, a slight rewording — but it has to be made.
- **Does the chapter's pacing still work?** Adding material changes the rhythm. A section that was the right length before may now feel too short next to its neighbour, or vice versa. Reorganising changes which sections set up which other sections. Read for the experience of the reader, not for the correctness of the parts.
- **Are there now redundancies?** New material may say things the existing material already said. Old material may now be redundant given what was added. One of the two has to go.
- **Are there now contradictions?** A new section may make a claim that an old paragraph implicitly contradicted. Either the new claim was wrong, or the old paragraph needs revising.
- **Does the chapter still deliver on its outline promise as a whole?** The original chapter had a learning goal and a structure. The revised chapter must still deliver them, possibly in a different shape.
- **Are there paragraphs that are now too short or too long for their function?** A paragraph that worked at 60 words may need to be 120 in the new context. A 200-word paragraph next to a new 400-word section may feel skimpy. Rebalance.
- **Does the closing of the chapter still set up the next chapter correctly?** If the revision added or restructured material, the original handoff sentence may no longer be the right one.
- **Are numbered references — listings, figures, tables, equations — still in appearance order?** When a revision inserts new material between existing material, it is tempting to give new listings the next available number rather than renumber the chapter. The result is a chapter where, for instance, Listing 5.10 appears before Listing 5.3, and prose references like "see Listing 5.4" point at material the reader hasn't reached yet or has already passed. After any insertion, walk the listing/figure/table numbers in the order they appear and confirm they are in numerical order. If they are not, renumber, and update every prose reference to match.

This read-through is a creative pass, not a mechanical check. The skill must read like a reader and notice what feels off. Then revise the off parts.

It is normal for the read-through to produce a second small wave of revisions — paragraph-level and sentence-level adjustments that respond to the chapter's new shape. These are part of the revision, not a separate phase. Make them.

A specific failure mode to avoid: treating revision as "I made the changes in the plan; done." That mindset produces chapters that are technically corrected but read worse than before, because the seams show. The read-through is what closes the seams.

### Step 5 — Self-critique

Run the self-critique pass on the affected chapter(s) — the same pass as Phase 4 step 5. New material may have new anti-AI-tells. Boundaries between old and new prose may have voice drift. Visuals plan may be out of sync. Treat the revised chapter as if it were freshly drafted.

### Step 6 — Update artefacts

Revisions touch more than just the chapter file:

- `figures.json` — new figures added, old figures removed or modified
- `sources.json` — new sources added, old sources updated or marked for re-verification
- `index-candidates.md`, `glossary-candidates.md` — new terms added
- Chapter frontmatter — `last_revised: <date>` field updated, `word_count` updated, status maybe demoted (a chapter that was `verified` may need to drop to `draft` if substantial new material was added)
- `outline.md` — if the chapter's outline entry no longer matches the chapter, update the outline

Failing to update artefacts is the most common revision-mode mistake. The chapter changes; nothing else does; the project gets quietly inconsistent. The skill must update artefacts as part of every revision.

### Step 7 — Record the revision

Append to `<book>/revision-log.md` (creating it if needed):

```markdown
## 2026-04-25 — Revised chapter 5

**Type:** expansion (Type 2)
**Reason:** Original chapter omitted TypeId, ComponentTypeInfo, and World definitions; readers couldn't actually implement the ECS from chapter alone.

**Changes:**
- Added section "TypeId machinery" (~250 words, listing 5.10 added)
- Added section "ComponentTypeInfo and registration" (~200 words, listing 5.11 added)
- Added section "The World class" (~400 words, listing 5.12 added)
- Filled tbl:archetype-vs-sparseset with content
- Added two mermaid diagrams replacing earlier placeholders
- Minor prose polish in querying section

**Word count change:** 4186 → 5800 (~+1600)
**Status change:** draft → draft (still draft; still needs full review)
**Artefacts updated:** figures.json (3 entries modified), chapter frontmatter
**Next steps:** None; ready for review or further editing.
```

The revision log is the project's audit trail. It lets future sessions understand what was done and why. It also lets the user see the project's history at a glance.

---

## Revision in the context of project status

Revision mode interacts with chapter status:

- A chapter at `status: draft` can be freely revised
- A chapter at `status: reviewed` can be revised; status drops to `draft` for material changes, stays at `reviewed` for typo or polish
- A chapter at `status: beta-revised` can be revised; if the revision is substantial, status drops; trivial fixes don't drop status
- A chapter at `status: verified` (passed fact-check) can be revised, but any new factual claims need their own fact-check; status drops to `draft` for material changes
- A chapter at `status: final` can be revised, but the user should be told that the chapter was considered final and asked to confirm; status definitely drops

The discipline is: status reflects what passes the chapter has cleared. Adding material requires re-clearing the passes for the new material, at minimum.

---

## What revision mode does not change

Revision mode is operational, not structural. It does not:

- Change which references files apply
- Change the persona system
- Change the style guide
- Change the outline (unless the revision is a Type 5 structural revision)
- Change the citation style
- Change the format

If the user wants to change any of these — say, "switch this whole book from APA to Chicago" — that's a meta-revision. It uses revision mode for the per-chapter mechanical changes, but the higher-level decision (which citation style) is an intake-level change recorded in `project.json`.

---

## When revision mode is the wrong answer

Some user requests look like revision but are something else:

- **"Schrijf een nieuw hoofdstuk over X"** — this is forward writing if the chapter doesn't exist yet. It's revision-mode Type 5 only if the chapter is being inserted into an existing structure.
- **"Begin opnieuw"** — if the user wants to start the project over, the answer isn't revision mode; it's persona phase again, possibly with a new project directory.
- **"Maak een variant van dit boek voor een andere doelgroep"** — this is a new book that shares some structure. Revision mode doesn't fit; new project does.
- **"Verbeter de hele schrijfstijl"** — this is a meta-revision that may need the persona file updated, the style guide updated, and then revision-mode Type 4 (cross-chapter style sweep) applied.

When in doubt, ask the user what they want the result to be: a changed version of the existing book (revision), a new variant (new project), or a fundamentally different book (new project).

---

## A worked example — the user asks "expand chapter 5"

User: "Hoofdstuk 5 is te kort. Breid uit."

**Step 1 — Orient.** Read `project.json`, both persona files, style guide, chapter 5's outline entry, chapter 5's current content, chapter 5's visuals plan.

**Step 2 — Diagnose.** Walk chapter 5 against its outline. The outline expected 28-36 pages; the current chapter is 17-20. The completeness check (from the writing-craft additions) shows that the chapter can't actually be implemented from its current content — TypeId, ComponentTypeInfo, World are referenced but not defined. Also the comparison table is a placeholder, and there are no inline mermaid diagrams where they were planned.

**Step 3 — Plan the revision.** Brief plan:

- Add section "TypeId machinery" with listing 5.10
- Add section "ComponentTypeInfo and registration" with listing 5.11
- Add section "The World class" with listing 5.12
- Fill `tbl:archetype-vs-sparseset` with content
- Replace `[fig:archetype-graph]` placeholder with inline mermaid
- Replace `[fig:query-iteration]` with inline mermaid or ASCII diagram
- Replace `[fig:archetype-storage-layout]` with ASCII art (precision matters here)
- Estimated word count change: +1500-2000 words
- Estimated final word count: 5500-6200, target page count 28-32 (within outline range)

**Step 4 — Execute.** Add the missing material. Replace placeholders with inline-rendered mermaid and ASCII. Fill the table. Polish the prose at the joins.

**Step 5 — Self-critique.** Run the full Phase 4 step 5 critique pass on the revised chapter. Check anti-AI-tells. Check completeness (now passes — reader can implement). Check voice (Saskia consistent throughout). Check the new visuals are at the right level.

**Step 6 — Update artefacts.** Update `figures.json` for the figures that changed status from placeholder to inline. Update chapter frontmatter (`word_count`, `last_revised`).

**Step 7 — Log.** Append to revision-log.md.

This is the procedure. It works for any expansion request. The key discipline: the revised chapter is held to the same standards as a freshly drafted one. Revision is not a free pass on quality.
