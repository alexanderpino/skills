# Book formats

A page count means nothing without a page format. "400 pages" in a Pelican paperback is roughly 100,000 words; "400 pages" in a royal-format textbook is closer to 180,000 words. The skill must establish the format at intake before any page targets become meaningful.

This file defines the standard formats by genre, gives words-per-page conventions, and explains how non-prose elements (code listings, figures, tables) affect page counts.

Read at intake (after genre is decided), and again whenever a page-count discussion happens during the project.

---

## Why format matters at intake

Format affects:

- **What "400 pages" means.** The same word count fills different page counts depending on trim size, font, line spacing, and margins.
- **What the chapter density should be.** A small mass-market paperback page can hold 250–300 words; a textbook royal-format page holds 380–450. A chapter outlined as "20 pages" is a different writing target in each.
- **How code listings, diagrams, and tables are estimated.** A 20-line code listing is roughly half a page in a 7×9.25" technical book and nearly a full page in a 5.5×8.5" trade format.
- **What the printer expects.** Most print-on-demand platforms (KDP, IngramSpark) have specific format options. Choosing one early aligns the project with production realities.

The format choice is recorded in `project.json` under `format` with concrete fields: `trim_size`, `words_per_page_target`, `lines_per_page`.

---

## Formats by genre — recommended defaults

### Fiction (general)

**Mass-market paperback** — 4.25" × 7" (108 × 178 mm).
- ~250–300 words per page
- 32–36 lines per page
- Used for: airport thrillers, romance, SFF series, anything intended for impulse purchase
- Typical book length: 80,000–100,000 words → 280–400 pages

**Trade paperback** — 5.5" × 8.5" (140 × 216 mm).
- ~280–320 words per page
- 33–37 lines per page
- Used for: most contemporary fiction, literary fiction, debut novels
- Typical book length: 80,000–100,000 words → 250–350 pages

**Hardcover (fiction)** — 6" × 9" (152 × 229 mm).
- ~300–340 words per page
- 34–38 lines per page
- Used for: literary fiction in hardback, prestige fiction, lead titles
- Typical book length: 90,000–120,000 words → 280–400 pages

### Non-fiction (popular)

**Trade paperback** — 5.5" × 8.5".
- ~280–320 words per page
- Used for: trade non-fiction, popular history, biography, self-improvement, popular-technical, memoir, essay collections
- Typical book length: 60,000–100,000 words → 220–360 pages

**Hardcover (popular non-fiction)** — 6" × 9".
- ~300–340 words per page
- Used for: lead non-fiction titles, prestige biographies, popular-science hardbacks
- Typical book length: 80,000–110,000 words → 250–380 pages

### Technical and academic

**Royal** — 6.14" × 9.21" (156 × 234 mm).
- ~380–430 words per page
- 38–44 lines per page
- Used for: academic monographs, advanced textbooks, technical treatises
- Typical book length: 100,000–180,000 words → 260–470 pages

**Crown quarto / 7×10** — 7" × 10" (178 × 254 mm).
- ~400–470 words per page (more for code-heavy books)
- Used for: serious textbooks, reference works, books with substantial figures or code
- Typical book length: 120,000–250,000 words → 300–600 pages

**O'Reilly format** — 7" × 9.25" (178 × 235 mm).
- ~380–450 words per page in prose; less for code-heavy pages
- Industry standard for programming books
- Used for: O'Reilly, Manning, Pragmatic, Apress technical titles
- Typical book length: 100,000–200,000 words → 280–550 pages

### School textbooks

**Crown quarto or oversized** — 7" × 10" or 8.5" × 11".
- Variable words per page — these books are layout-heavy with photos, sidebars, callouts
- Word count alone is misleading; design fills the pages
- Estimate by spread (two-page layout) rather than per page

### Children's

**Picture book** — 8" × 8" or 9" × 9".
- Word counts are tiny (300–800 words for the whole book typically)
- The illustrations *are* the book; words are minimal
- Page counts are usually fixed by printer convention (32 pages standard)

**Middle grade / YA** — 5.5" × 8.5" trade paperback or 6" × 9" hardcover.
- ~250–300 words per page (larger font for younger readers)
- Typical length: 30,000–80,000 words for middle grade, 50,000–100,000 for YA

### Specialised

**Cookbook** — 7.5" × 9" or 8" × 10", often hardcover.
- Words per page wildly variable (recipe pages are mostly white space and photo)
- Estimate by recipe count, not word count: typical cookbook has 75–150 recipes

**Coffee table / art book** — 9" × 12" or larger.
- Photo and design driven
- Word count secondary to image count

**Reference / dictionary** — 6" × 9" or larger, often dense layouts.
- Two-column or denser layouts
- 600–800+ words per page possible

---

## How code listings, figures, and tables affect page counts

Non-prose elements take up page space. A book with heavy code or figures will have fewer prose words for the same page count.

### Code listings

A code listing of N lines (in monospace, usually 9–10 pt) takes roughly:

- **N lines of monospace code** in a typical technical book = **N+4 lines of equivalent prose space** (the +4 accounts for the title, the spacing above and below, and the syntax-highlighting line height being slightly larger than prose line height)
- A 20-line listing in a 7×9.25" technical book = roughly half a page
- A 40-line listing = roughly a full page
- A listing crossing a page boundary should be avoided; break listings to fit, or refactor the example

For estimating: assume code-heavy chapters average **60–70% of normal prose density**. A 20-page chapter with substantial code averages 13–14 pages of prose-equivalent.

### Figures and diagrams

A figure with caption typically takes:

- **Quarter page** for a small inline diagram or a small chart
- **Half page** for a standard diagram or photo with caption
- **Full page** for a large or complex figure
- **Two-page spread** for a large map or detailed reference figure

Figure-heavy chapters (history with maps, technical with diagrams) commonly run at **70–80% prose density**.

### Tables

Tables vary widely. A small comparison table is half a page; a large data table can cross multiple pages. Estimate based on row count: ~30 rows fits a typical page in technical formats.

### The combined effect

A book with substantial code, figures, and tables — say a technical treatise with one major code listing per ~5 prose pages, one figure per ~4 pages, and one table per ~10 pages — will run at roughly **65–75% prose density** overall. The skill should account for this when estimating page counts from word counts.

A useful rule: for a technical book, take your word count, divide by the format's words-per-page (say 400), then **multiply by 1.3–1.5** to account for code, figures, and tables. So 100,000 words at 400 wpp = 250 pages of pure prose, but probably 325–375 pages of finished technical book.

---

## Recording format in the project

After format is decided at intake, record in `project.json`:

```json
"format": {
  "trim_size": "7×9.25",
  "trim_size_inches": [7, 9.25],
  "binding": "trade-paperback",
  "words_per_page_target": 400,
  "lines_per_page_target": 40,
  "non_prose_density_factor": 1.4,
  "_note": "Standard O'Reilly-style technical format. The non-prose factor accounts for code, figures, and tables typical of this genre."
}
```

The `non_prose_density_factor` is what to multiply pure-prose page counts by to get the realistic finished page count.

---

## When to revisit format

The format chosen at intake is a working assumption. It should be revisited:

- **At the end of outline** — if the outlined chapter lengths don't match the target, adjust either format or scope
- **At first complete draft** — if the actual word count plus non-prose is producing more pages than budgeted, decide whether to cut, change format, or accept a longer book
- **Before assembly** — final format choice locks in for production

If the project is going to a specific publisher with specific format conventions, those conventions override these defaults. Ask the user.

---

## A concrete example of why this matters

For the AAA engine book, Volume A:

- Target: ~400 pages (decided at intake)
- Format: not initially decided; defaulted mentally to "textbook"
- Word count target: not computed

Once we decide format = O'Reilly 7×9.25" (industry standard for programming books), 400 wpp baseline:

- 400 pages × 400 wpp = 160,000 words pure prose target
- But code/figures/tables factor of 1.4 means realistic prose target is ~115,000 words
- A chapter outlined as "30 pages" is roughly 8,500 prose words

The HLSL book chapter 1 was 3,691 words. At this format, that's ~9 pages. The outline had estimated 10–14 pages. Slightly under, which is fine.

The AAA engine book chapter 16 was 5,287 words. At this format, that's ~13 pages. The outline had estimated 24–30 pages. Significantly under — about half. Either the chapter is missing substance, or the estimate was wrong.

This is the kind of thing format makes visible. Without it, "5,287 words" is just a number.
