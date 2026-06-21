# Citation styles

The writing phase records citations as `[src:N]` placeholders. The assembly phase converts these into the user's chosen style. This file describes the five supported styles, their formatting rules, and how to convert.

The user chooses a style during intake (`project.json.citation_style`). Load this file in assembly (Phase 5) and use the appropriate section.

**General principle:** once a style is chosen, be relentlessly consistent. Mixed styles in a bibliography are a red flag that says "AI slop" faster than almost anything else.

---

## Overview of the five styles

| Style | In-text | At end | Common in |
|---|---|---|---|
| **APA 7** | (Author, Year) | References, author-year order | Social sciences, psychology, education |
| **Chicago notes-bibliography** | Superscript footnotes/endnotes | Bibliography, alphabetical | History, biography, literary studies |
| **Chicago author-date** | (Author Year) | References, author-year order | Physical and natural sciences, some social sciences |
| **MLA 9** | (Author Page) | Works Cited, alphabetical | Humanities, literature, language studies |
| **IEEE** | [1], [2] | References, numeric order of first citation | Engineering, computer science |
| **Plain numeric** | [1], [2] | References, numeric order | Popular-technical, when formal rigour not needed |

Notes:
- "Chicago notes-bibliography" is the classic humanities style with footnotes/endnotes.
- "Chicago author-date" mirrors APA's look but has its own formatting quirks.
- "Plain numeric" isn't a formally defined style but works well for trade publishing where the reader just needs "where did this come from."

---

## The sources.json source of truth

Every conversion pulls from `sources.json`. The schema (recap from `research-protocol.md`):

```json
{
  "id": 1,
  "type": "book|article|website|archive|interview|paper|...",
  "author": "Last, First",                    // or array for multiple authors
  "title": "...",
  "publisher_or_venue": "...",
  "year": 2019,
  "url": "https://...",
  "accessed": "2026-04-24",
  ...
}
```

For multi-author works, `author` should be an array: `["Last1, First1", "Last2, First2"]`. For works with many authors, store all — the formatter decides when to elide (et al. / and others).

For non-book types, add fields as needed:
- Articles: `journal`, `volume`, `issue`, `pages`
- Book chapters: `book_title`, `editor`, `pages`
- Archival: `collection`, `box`, `folder`, `institution`
- Legal: `court`, `case_number`
- Web: always `url` and `accessed`

---

## APA 7

**In-text:**
- Single author: `(Smith, 2019)` or `Smith (2019) argued that...`
- Two authors: `(Smith & Jones, 2019)` or in text `Smith and Jones (2019)`
- Three or more: `(Smith et al., 2019)` always
- No author: use title, abbreviated: `("Short Title," 2019)`
- Quoting: add page: `(Smith, 2019, p. 42)`

**Reference list — common types:**

Book:
```
Smith, J. A. (2019). The title of the book: Subtitle goes here (2nd ed.).
Publisher Name.
```

Article in journal:
```
Smith, J. A., & Jones, K. L. (2019). Title of the article. Journal Name,
15(3), 234-251. https://doi.org/10.xxxx/yyyyy
```

Book chapter:
```
Smith, J. A. (2019). Chapter title. In K. L. Jones (Ed.), Book title
(pp. 45-67). Publisher.
```

Website:
```
Smith, J. A. (2019, March 15). Title of the page. Site Name.
https://example.com/page
```

Reference list is in alphabetical order by first author's last name. Hanging indent. Year in parentheses. Title in sentence case except for proper nouns and first word. Journal titles in italic and title case.

---

## Chicago notes-bibliography

**In-text:** superscript number, placed after punctuation.

> Ada was born on 10 December 1815.¹

The number refers to a footnote (bottom of page) or endnote (end of chapter/book). First full citation, later citations shortened.

**First full note (book):**
```
1. John A. Smith, The Title of the Book: Subtitle Goes Here, 2nd ed.
(New York: Publisher Name, 2019), 42.
```

**Subsequent note (same source):**
```
2. Smith, Book Title, 45.
```

**Bibliography entry** (alphabetical, at end):
```
Smith, John A. The Title of the Book: Subtitle Goes Here. 2nd ed.
New York: Publisher Name, 2019.
```

Note the differences between notes and bibliography entries:
- Notes: author first name first, commas, parentheses around publisher info
- Bibliography: author last name first, periods, no parentheses

**Article in journal — first full note:**
```
1. John A. Smith and Katherine L. Jones, "Title of the Article,"
Journal Name 15, no. 3 (2019): 234-51.
```

**Bibliography:**
```
Smith, John A., and Katherine L. Jones. "Title of the Article."
Journal Name 15, no. 3 (2019): 234-51.
```

Bibliography is alphabetical by author's last name. For multiple works by same author, use em-dashes for subsequent entries.

---

## Chicago author-date

**In-text:** `(Smith 2019, 42)` — comma before page, no "p." prefix.

**Reference list** (alphabetical, at end):

Book:
```
Smith, John A. 2019. The Title of the Book: Subtitle Goes Here. 2nd ed.
New York: Publisher Name.
```

Article:
```
Smith, John A., and Katherine L. Jones. 2019. "Title of the Article."
Journal Name 15 (3): 234-51.
```

Close to APA but differs in punctuation, capitalisation (title case for article titles, unlike APA's sentence case), and small details.

---

## MLA 9

**In-text:** `(Smith 42)` — no comma, no year, page only. If multiple works by same author are cited, include short title: `(Smith, Book Title 42)`.

**Works Cited** (alphabetical):

Book:
```
Smith, John A. The Title of the Book: Subtitle Goes Here. 2nd ed.,
Publisher Name, 2019.
```

Article:
```
Smith, John A., and Katherine L. Jones. "Title of the Article."
Journal Name, vol. 15, no. 3, 2019, pp. 234-51.
```

MLA uses commas rather than periods to separate core elements. Titles of standalone works in italic, titles of parts (articles, chapters) in quotation marks.

---

## IEEE

**In-text:** `[1]`, `[2]`, etc. Numbered in order of first appearance. Subsequent references use the same number.

> Ada was born in 1815 [3] and educated privately [3], [7].

**References** (numeric order, not alphabetical):

Book:
```
[3] J. A. Smith, The Title of the Book: Subtitle Goes Here, 2nd ed.
New York: Publisher Name, 2019.
```

Article:
```
[7] J. A. Smith and K. L. Jones, "Title of the article," Journal Name,
vol. 15, no. 3, pp. 234-251, 2019.
```

First initials abbreviated. Title of articles in quotes, titles of standalone works in italic. References appear in order cited.

---

## Plain numeric

Simplest style. Good for popular-technical and trade nonfiction where the reader just needs to know the source exists.

**In-text:** `[1]`, `[2]`, numbered in order of first appearance.

**References** (numeric, at end):

```
1. John A. Smith, The Title of the Book (New York: Publisher, 2019),
Chapter 4.

2. John A. Smith and Katherine L. Jones, "Title of the article,"
Journal Name, 2019, https://doi.org/xxx.
```

The style isn't formally defined, which means: be consistent with whatever you pick within the book. Include enough information that the reader can find the source.

---

## Conversion procedure

At assembly time, walk through every chapter's markdown:

1. Find every `[src:N]` token.
2. Look up source N in `sources.json`.
3. Render the in-text citation in the chosen style.
4. For footnote/endnote styles, generate the note entry (and track whether it's first occurrence or subsequent).
5. Build the reference list / bibliography / works cited, in the order required by the style.

Prefer writing this as a small Python script rather than doing it by hand — it's mechanical work. A rough skeleton:

```python
import json
from pathlib import Path

sources = json.load(open("sources.json"))["sources"]
sources_by_id = {s["id"]: s for s in sources}
style = "chicago-notes"  # from project.json

def render_inline(source, style, page=None):
    if style == "apa":
        # (Smith, 2019) or (Smith, 2019, p. 42)
        ...
    elif style == "chicago-notes":
        # return superscript number, accumulate note
        ...
    # etc.

# Walk chapters, substitute inline citations,
# emit bibliography in order required by style
```

For books with many citations, writing the script is faster and more reliable than manual conversion, and the script can be reused across projects. Save it to `<book>/scripts/build_citations.py`.

---

## Footnotes vs endnotes

Chicago notes-bibliography can use either:

- **Footnotes** — at the bottom of the same page. Best for readers who genuinely want to glance at the source. Common in print academic books.
- **Endnotes** — at the end of the chapter or book. Cleaner text pages. Common in trade nonfiction where most readers won't look.

The user chooses (`project.json.note_location`). Neither is wrong; it's about the reader's likely behaviour.

**Output format notes:**

- **Markdown** — has limited footnote support; use `[^1]` inline and `[^1]: Note text` definitions. Convert to proper footnotes in docx/pdf at output.
- **docx** — use Word's native footnote feature (Insert → Footnote). The docx skill handles this.
- **pdf via LaTeX** — `\footnote{}` or endnote packages.
- **Website** — footnotes as linked references at the bottom of each article, or as popover tooltips.

---

## Mixed citations (common real case)

Many books use footnotes for discursive notes ("the reader may also wish to consult...") and a bibliography for sources. That's fine. Two distinct machineries:

1. Footnotes/endnotes for commentary and for the full source citations on first mention
2. Bibliography at the end for the full list in alphabetical order

In Chicago notes-bibliography, this is the standard practice — not a mix.

Where confusion creeps in: if the user asks for "APA with footnotes", what they usually mean is APA author-date citations in-text, but also occasional footnotes for side remarks (a.k.a. "explanatory footnotes"). That's fine — just don't use footnotes for the source citations themselves, use them only for the discursive commentary.

---

## Inline citation practice during writing

When writing a chapter, the placeholder form is:

```markdown
The Notes were published in August 1843 [src:3], running to roughly
three times the length of Menabrea's original paper [src:3][src:7].
```

For direct quotes, also record the page number:

```markdown
"I am more than ever now the bride of science," she wrote to her mother
[src:3, p. 234].
```

The assembly script handles both — for styles that use page numbers (APA, MLA, Chicago), the page extracts from the placeholder; for styles that don't, it's dropped.

For Chicago notes-bibliography with page numbers:
```markdown
[src:3, p. 234]  →  footnote: "3. Somerville, Personal Recollections, 234."
```
