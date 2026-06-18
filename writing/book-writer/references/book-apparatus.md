# Book apparatus

The apparatus of a book — table of contents, index, glossary, list of figures, notes on sources, appendices — is what separates a text from a book-as-object. A reader uses the apparatus without thinking about it; the writer has to build it deliberately.

This file covers the machinery. Load during writing (to mark candidates) and during assembly (to build the pieces).

---

## The semi-automatic principle

The skill works **semi-automatically**:

- **During writing**, it flags candidate terms and concepts as it encounters them, storing them in `index-candidates.md`, `glossary-candidates.md`, etc. This is cheap and reversible.
- **At assembly time**, the actual apparatus is built — but only for the pieces the user wants. The user's intake answer determines what gets built.

Nothing is auto-generated without being asked. But when asked, the building work is mostly already done.

---

## Candidate files during writing

As chapters are drafted, maintain these files in the book project root:

```
<book>/
├── index-candidates.md
├── glossary-candidates.md
└── figures.json (already covered elsewhere)
```

### index-candidates.md

For every chapter, after the draft is complete, scan for terms that might warrant an index entry:

- Proper nouns (people, places, organisations, named concepts)
- Technical terms that are defined or discussed substantively
- Concepts that recur across chapters

Record as:

```markdown
# Index candidates

## Chapter 1 — A Portrait in Shadow

- Lovelace, Ada — entire chapter (biographical overview)
- Byron, Lord — p. 3, 8–12
- Milbanke, Annabella — p. 4–7
- separation, the Byron — p. 5–9
- Lamb, Lady Caroline — p. 4

## Chapter 2 — The Machine

- Babbage, Charles — entire chapter
- Difference Engine — p. 16–22
- Analytical Engine — p. 23–35
- Turing, Alan — p. 31 (anticipated by Lovelace's Notes)
```

Use real page references only once final pagination is set (at assembly). During writing, just note the chapter and approximate section.

### glossary-candidates.md

For technical and specialist books, every time a term is introduced with a definition or substantial explanation, add it:

```markdown
# Glossary candidates

## Chapter 3
- **mark-and-sweep** — a two-pass garbage collection algorithm (ch. 3, §3.2)
- **root set** — the set of references known to be reachable (ch. 3, §3.1)
- **reachability** — (ch. 3, §3.3)

## Chapter 4
- **generational hypothesis** — (ch. 4, §4.1)
- **nursery** — (ch. 4, §4.2)
```

At assembly, the user decides which candidates become actual glossary entries. Not every introduced term belongs in the glossary — if the term is explained well in context and never used again, it doesn't.

---

## Frontmatter, in order

Standard order (omit what's not wanted):

1. **Half-title page** — just the title, minimal, on its own page. Common in print.
2. **Title page** — title, subtitle, author (persona name), publisher if any.
3. **Copyright page** — year, rights statement, ISBN if assigned, edition info, print/digital rights.
4. **Dedication** — one line, one page, optional.
5. **Epigraph** — a quotation setting the book's tone, optional.
6. **Table of contents** — see below.
7. **List of figures** — if >10 figures or book requires them.
8. **List of tables** — same rule.
9. **Foreword** — written by someone other than the author, optional.
10. **Preface** — written by the author, states scope and intent.
11. **Acknowledgements** — usually here, sometimes in backmatter.
12. **Introduction** — if substantial and setting up the book's thesis; otherwise chapter 1 serves.

### Table of contents

Generated from chapter titles. Format varies by genre:

**Academic/textbook**: show chapter numbers, chapter titles, and first-level sections; page numbers.
```
Chapter 3. Garbage Collection                           45
  3.1 The problem                                        45
  3.2 Mark-and-sweep                                     49
  3.3 Reference counting                                 57
  3.4 When simple algorithms fail                        64
```

**Narrative (biography, history, fiction)**: usually just chapter numbers and titles, page numbers.
```
1. A Portrait in Shadow                                   3
2. The Machine                                           16
3. The Correspondence                                    41
```

**Popular-technical**: often just titles, no chapter numbers; page numbers.
```
The Thing That Frees Memory                              1
Why Reference Counting Isn't Enough                     19
Generations of the Heap                                 39
```

Pick the style that matches the book. The skill should not impose a style the book isn't.

---

## Backmatter, in order

1. **Epilogue** — optional, narrative works.
2. **Appendices** — technical supplements, proofs, extended code, data tables. Label A, B, C.
3. **Endnotes** — if the chosen citation style uses them.
4. **Glossary** — see below.
5. **Bibliography / References / Works Cited** — per citation style.
6. **List of sources for illustrations** — if figures need separate crediting.
7. **Index** — see below.
8. **Acknowledgements** — if not in frontmatter.
9. **About the author** — short biographical note on the persona. A paragraph.
10. **Colophon** — technical note on typography, production. Rare in AI-generated books.

---

## Glossary (when requested)

Structure:
- Terms alphabetical, regardless of language
- Term in **bold**, then em-dash, then definition
- Cross-references to other glossary terms in italic
- Optional: reference to main discussion in the book

Example:
```
**mark-and-sweep** — a garbage collection algorithm in two passes.
The first pass marks all objects reachable from the *root set*; the
second pass frees unmarked objects. Discussed in detail in Chapter 3.
See also *generational garbage collection*.

**nursery** — in *generational garbage collection*, the region where
newly-allocated objects live before being promoted. Chapter 4.
```

Definitions should be self-contained where possible but may refer to other entries. Avoid definitions that require the reader to already understand the term.

**When to include a glossary:**
- The book introduces significant specialist vocabulary (>15–20 terms)
- Reader may dip in and out rather than read linearly
- The vocabulary is cumulative across chapters

**When to skip:**
- Narrative works (biographies, history, most fiction)
- Books where terms are defined well in context and not re-used
- Short books where a glossary would be padding

---

## Index (when requested)

An index is more work to build well than most writers realise. It's also one of the clearest marks of a "real" book versus a quick one.

### What goes in

- Every named person (with birth/death dates optional)
- Every named place, organisation, event
- Every substantial concept (not every mention — substantial discussion)
- Works cited as subjects (not just sources): "*Dracula* (Stoker)" if it's discussed
- Sub-entries for complex topics

### What stays out

- Passing mentions without substance
- Page-by-page minor references
- Author's own name (unless they appear as subject in the text)
- Figures and tables usually listed separately, not indexed

### Structure

```
Analytical Engine, 23–35, 42, 89
    description of, 25–28
    Notes on, 30–34
    as precursor to modern computer, 89
Babbage, Charles, 16–35, 41, 53, 127
    correspondence with Lovelace, 42–61
    Difference Engine and, 16–22
    financial difficulties, 53–55
    personality, 19–20, 53
    political frustrations, 53
```

Main entries alphabetical. Sub-entries indented, also alphabetical (not in order of first appearance — alphabetical). Page ranges with en-dash. "See" and "See also" cross-references:
```
algorithm. See also complexity; computation
artificial intelligence. See machine learning
```

### Building the index

For any book where the user requests an index:

1. During writing, maintain `index-candidates.md` (described above)
2. At assembly, after pagination is stable:
   - Walk `index-candidates.md` and identify the real entries (with sub-entries)
   - For each entry, locate every page where it actually appears
   - Generate the alphabetical index with page references
3. Review: is every major discussion indexed? Every person? Check the index against the TOC — do chapters that discuss X have X-entries at those pages?

The automatic part is the term collection. The judgement part (what's a main entry vs a sub-entry, what's significant enough to index) stays human (or at minimum, needs careful attention).

For long books (>200 pages) a proper index is essentially required for reference use. For short narrative books (<150 pages), often not needed.

---

## List of figures / tables / etc.

Generated from `figures.json`. For each chapter or for the whole book, show:

```
List of Figures

Figure 1.1 — Portrait of Ada Lovelace, Alfred Chalon, c. 1840 ....... 3
Figure 1.2 — Byron family tree .................................... 11
Figure 2.1 — Difference Engine, partial reconstruction ............. 17
```

Usually in frontmatter, after TOC. Same for tables, maps, etc. if the book has enough of them.

---

## A note on sources / author's note

For any book that touches real-world facts — non-fiction obviously, but also historical fiction, docu-fiction, speculative fiction drawing on real research — include an author's note or "On Sources" section.

Purpose: explain how the research was done, where the primary sources came from, what was invented vs recorded (for fiction), and how to pursue the topic further.

Placement: usually backmatter, before the bibliography. Can also go at the front in a preface.

Length: 2 pages to 20 pages depending on the book's claims. A trade biography might have a 5-page "Note on Sources"; a scholarly history might have a 20-page essay on archives used.

This is also where single-source claims and unresolved conflicts are acknowledged honestly. Not every fact needs a note; the ones where the honest author would want the reader to know "this is the best we have, and here's why" do.

---

## Building it all — assembly-time sequence

1. **Finalise chapters** (all content decisions locked)
2. **Generate TOC** from chapter titles and (optionally) first-level headings
3. **Resolve figure numbers** and generate list of figures (if applicable)
4. **Resolve citations** to chosen style, generate bibliography
5. **Build glossary** if requested — review glossary-candidates with the user, assemble
6. **Paginate** (convert to final format — docx/pdf — so page numbers are stable)
7. **Build index** if requested — candidates become real entries, look up page numbers in paginated output
8. **Assemble frontmatter and backmatter** in correct order
9. **Final scan** — confirm every reference (TOC → chapter, index → page, figure list → figure) resolves correctly

Pagination before index is critical. An index built before pagination would have wrong page numbers. For ebook/web formats without stable pagination, the index uses chapter/section anchors instead of page numbers.

---

## When the user asks

The workflow is:
1. During writing, maintain candidate files silently (no user interaction)
2. Near end of assembly (after chapters finalised), ask: "Should I build an index? A glossary? Any appendices?"
3. For each yes, walk the candidate file with the user (or do a first pass and show them) to refine
4. Build and include

For fiction books, often only TOC and author's note. For academic and reference-style books, often all of the apparatus. For popular-technical, usually TOC, glossary, and maybe a light index.
