# Co-authorship

Most books have one author. This skill, by default, assumes one. But some projects are genuinely co-authored — two voices that produce the book together, with neither subordinate to the other. The relationship between those voices needs explicit decisions.

This file describes the patterns for co-authored projects: how voices coexist on the page, how chapters are assigned, how disagreements are handled, and how the per-chapter writing loop changes when more than one persona is in the room.

Read at intake when the user signals two (or more) authors. Read again at outline (chapter assignment), and at the start of every chapter (which voice is primary).

---

## When co-authorship is the right answer

Genuine co-authorship — as opposed to a single author with a contributing editor — makes sense when:

- **The subject matter spans two genuinely different domains of expertise.** A book on how engines and renderers compose, written by an engine architect and a graphics specialist together, captures things neither could capture alone.
- **The book benefits from productive tension.** Two authors with somewhat different views, who disagree visibly in places, give the reader a richer sense of the problem space than a single author could.
- **The audience expects it.** Some kinds of books, especially in specialised technical or academic fields, gain credibility from named expert co-authors.
- **The work is genuinely too big for one author.** Less common — most books are within one author's reach — but real for very large projects.

Co-authorship is *not* right when one party is contributing material that the other will mostly rewrite. That's a single-author book with sources or contributors. The skill's persona system handles single-author already.

---

## What the skill needs from co-authorship at intake

If the user wants co-authors, the intake collects:

- **How many authors?** Two is most common. Three or more is possible but exponentially harder; warn the user.
- **Are they real or fictional?** A single book can have two real authors (memoir co-written with someone), one real and one fictional (an author writing under their own name with a fictional collaborator), or two fictional. Each combination has different ethical and persona constraints.
- **What's each author's domain?** The split should be clear. "Engine architecture" + "graphics" is clear; "tech stuff" + "more tech stuff" isn't.
- **What's the voice relationship?** Distinct voices? Fused? Alternating? See the patterns below.
- **Who decides what?** Editorial authority — is it shared, or does one author have final say? This matters when disagreements are surfaced.

The intake produces:

- One `persona.md` file per author, in their own folder under `~/writers/<slug>/`
- A `co-authorship.md` file in the book project that records the working relationship, voice conventions, and chapter assignment
- A note in `project.json` with `co_authored: true` and `personas: [list]`

---

## Voice patterns — how authors coexist on the page

Three main patterns for how multiple authors share the prose. The choice affects every subsequent decision.

### Pattern 1 — Alternating "I"

Each chapter has one primary author. Within that chapter, "I" refers to the primary author throughout. The reader knows whose perspective they're inside.

This is the cleanest pattern. It avoids the dilution that comes when two voices try to share a paragraph. It lets each voice be itself — different rhythms, different hobbyhorses, different relationships with the reader.

Cross-references between authors use an explicit form when needed: **"Saskia would push back here:"** followed by the other author's view rendered in their voice. Or "Alexander would put it differently:" — same pattern, other direction.

The "would push back here" form has three properties that make it work:

1. The reader sees the disagreement clearly attributed
2. The other author's voice gets a moment, in their own register
3. The chapter's primary "I" reasserts after the cross-reference

This pattern works for technical books, treatises, and most non-fiction co-authorship. It is the pattern this skill recommends as default.

### Pattern 2 — Joint "we"

Both authors speak as "we" throughout. There is no per-chapter primary; the prose is fused into a single joint voice. The "I" disappears entirely.

This is harder to do well. The fused voice tends to lose the texture of either author and produce a generic-feeling joint persona. When it works, it works because the two authors have genuinely converged on a shared sensibility through long collaboration. When it doesn't work, the prose feels neither like author A nor like author B but like a third, hollower voice.

Use this pattern only when:
- The authors have genuinely worked together long enough to have a shared voice
- Chapter-by-chapter perspective changes would feel artificial
- The book's argument is unitary, not multi-perspective

Most co-authored books shouldn't use this pattern. It seems easier and is harder.

### Pattern 3 — Hybrid

Most chapters use alternating "I" (Pattern 1). Specific chapters use joint "we" (Pattern 2). The "we" chapters are typically:

- Preface (signed by both)
- Introduction
- Closing chapter where the authors synthesise
- Occasional chapters where both contributions are genuinely fused

This is the pattern recommended for most co-authored projects. It gets the legibility of Pattern 1 with the unity of Pattern 2 at the moments unity is wanted.

---

## Chapter assignment

In Patterns 1 and 3, every body chapter has a primary author. The assignment happens in the outline phase, recorded in each chapter's outline entry.

Three approaches to assignment:

**By expertise.** Each author writes the chapters within their domain. This is the cleanest split. The engine architect writes the architectural chapters; the graphics specialist writes the graphics chapters. Joint chapters are the few where the domain is genuinely shared.

**By preference.** The authors negotiate which chapters they want to write. Often produces a similar result to expertise-based assignment, but with personal preferences sometimes overriding the obvious match.

**By balance.** The authors aim for roughly equal page counts, even if some chapters could go either way. Used when both authors are equally credentialed and assignment by expertise would create a heavy-light imbalance.

Most co-authored projects use a combination: expertise where it's clear, preference for the rest, with awareness of overall balance.

The outline records primary author per chapter and optionally a secondary author who reviews and may have specific contributions or push-back insertions.

---

## The "would push back here" pattern in practice

When a primary author wants to bring in the other voice mid-chapter, the form is:

> Most of my approach is to instrument first — get data, then theorise. Saskia would push back here: she'd argue that if you're already at the instrument-first stage, you've usually skipped a structural question that would have made the bug not exist. She's not wrong. We just disagree about which step the typical reader is more likely to skip.

Notice the four moves:

1. **Primary author's own claim** — the chapter's perspective continues
2. **Explicit hand-off** — "Saskia would push back here:" — clear attribution
3. **Other author's view, in their voice** — what they would actually say, in their register
4. **Closing acknowledgement** — the primary author's stance toward the disagreement (acceptance, productive tension, or principled difference)

The closing should not always be "she's not wrong" — sometimes the primary author thinks the other author *is* wrong, and the chapter says so. The point is the disagreement is real, on the page, and the reader sees both views.

A common failure mode: manufactured disagreement. If the authors actually agree on something, the "would push back here" form should not appear. Disagreement is a tool for the moments it genuinely exists, not a stylistic mannerism.

A second failure mode: the other voice gets watered down to make the disagreement smaller. The other author's view should be expressed as forcefully as they would express it themselves. Anything less is patronising.

---

## Conflict resolution between authors

When the authors genuinely disagree on something the book has to take a position on (not just present both views):

1. **Surface it explicitly.** Note the disagreement in `co-authorship.md` under "open disagreements" so it doesn't get lost.
2. **Try to characterise both positions fairly.** Often the disagreement is smaller than it first looks once both positions are written down side by side.
3. **Decide the resolution type:**
   - **Present both** — for design questions where there isn't a single right answer. The book shows both positions and lets the reader decide.
   - **Take a position** — when one author is genuinely more authoritative on the specific question, or when the project needs to commit (a running example can't have two implementations).
   - **Punt** — leave the topic out of the book entirely. Sometimes the right answer when the disagreement is over something the book doesn't actually need.
4. **Record the resolution.** Future chapters need to know whether the book has taken a position on X, presented both, or skipped.

Disagreements that recur across chapters often indicate a deeper structural question. Flag those for the closing chapter to address head-on rather than letting them rumble through every chapter.

---

## How the per-chapter writing loop changes

For co-authored projects, the per-chapter loop in Phase 4 of the skill changes:

**Step 1 (Re-read).** Read both personas, plus the `co-authorship.md` agreement. The primary author's persona is the voice being inhabited; the other is reference.

**Step 2 (Plan visuals).** Same as single-author.

**Step 3 (Draft).** Write in the primary author's voice. If a "would push back here" insertion is planned, switch to the other author's voice for that passage, then back.

**Step 4 (Mark apparatus).** Same as single-author.

**Step 5 (Self-critique).** New checks:
- Voice purity: does the primary author's voice hold throughout, or does it drift toward the other author?
- Cross-references: every "would push back here" insertion uses the other author's voice authentically and is genuinely a disagreement, not a manufactured one
- Co-author alignment: if the other author would object to anything in this chapter on factual or position grounds, is that captured?

**Step 6 (Revise).** Same as single-author, with attention to voice purity issues.

**Step 7 (Save).** Add the primary author to chapter frontmatter:
```yaml
primary_author: saskia
secondary_author: alexander  # optional, for chapters with their input
```

**Step 8 (Optional second-author review).** For production-scope projects, the secondary author reads the draft and either approves, suggests revisions for the primary author to integrate, or proposes specific "would push back here" insertions. The primary author decides what to integrate.

---

## What `co-authorship.md` should contain

The book project's `co-authorship.md` (typically in `<book>/writer/`) records:

- **Why two authors** — the rationale for co-authorship on this project
- **Voice pattern** — alternating "I", joint "we", or hybrid (with which chapters use which)
- **Chapter assignment** — which author is primary on which chapters
- **Editorial authority** — who has final say on which decisions
- **Process rules** — how a chapter moves from primary draft through secondary review to saved
- **Open disagreements** — running list of disagreements that haven't been resolved yet, with current resolution status

This file is read at the start of every chapter and updated as the project progresses. It is the working agreement between the authors, made legible.

---

## A worked example — Alexander and Saskia

The AAA engine book in this skill's testing has co-authors Alexander Pino and Saskia Vermeer. The pattern they use:

- **Voice pattern:** Hybrid — alternating "I" by chapter, joint "we" in preface, introduction, and closing chapter
- **Chapter assignment:** By expertise — Saskia leads architectural and structural chapters (PAL, game loop, ECS, memory, jobs, the seams), Alexander leads rendering chapters (Vulkan, render graph, shaders, assets, frame timeline). Joint authorship on chapters 1, 15, 17.
- **Editorial authority:** Shared. Disagreements are surfaced; resolution is by the resolution-type rules above.
- **Process:** Primary author drafts; secondary author reviews; primary author integrates, decides on push-backs, saves.
- **Disagreement style:** Both authors agree they will let real disagreements show in the text using the "would push back here" form. Alexander leans toward "make it work first, then understand it"; Saskia leans toward "understand it, then make it work, because making-it-work-first traps you." Both views appear in the book.

This worked example is the pattern this skill recommends for most two-author technical projects. Adapt the specifics; the structure is general.

---

## Three or more authors — a warning

This skill's patterns scale to two authors well. Three or more is harder than three-times-as-hard:

- Voice differentiation gets thinner with each added author (readers can hold two distinct voices easily; three is harder)
- "Would push back here" gets messy with three potential push-back-ers
- Chapter assignment becomes a coordination problem
- Editorial authority becomes either a committee (slow) or a hierarchy (one author dominates)

For three+ author projects, consider:

- **Edited collection model** — single editor, multiple contributors, each contributing distinct chapters in their own voice. This is not co-authorship; it's editing. The skill could support this, but it's outside the patterns in this file.
- **Lead author + co-authors model** — one author has primary authority and voice; others contribute material that the lead integrates. This is closer to single-author with research support.

If three+ true co-authors is genuinely the structure, document the patterns explicitly in `co-authorship.md` and accept the complexity. The skill will not handle this automatically.
