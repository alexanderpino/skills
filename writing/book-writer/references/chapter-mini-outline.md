# Chapter mini-outline — sectie-level decompositie voor het hoofdstuk

## Why this reference exists

The skill's Phase 3 produces a book-level outline in which each chapter gets a paragraph or two: title, opening hook, learning goal, three to seven beats, key sources, handoff. That outline is enough to plan the book. It is not enough to write a chapter from.

The gap between *outline entry* and *finished chapter* is large. A chapter outlined as "Three to seven beats" might in practice need fifteen paragraphs across five or six sections, with internal handoffs, with specific scenes anchoring specific beats, with sources distributed across sections. Without a mini-outline that closes this gap, the writer (human or agent) reaches for the chapter file and starts producing prose — discovering structure as they go, often producing a first section that turns out to be wrong once the rest of the chapter takes shape.

This is wasteful for any writer. It is **especially wasteful for agents with small context budgets.** An agent that has to regenerate or substantially revise five thousand words because the structure was wrong from paragraph one has burned tokens on work that gets thrown away. Agents with smaller budgets cannot afford this. They need to start each section with a clear local task and a clear local context.

The chapter mini-outline closes the gap. It is a separate deliverable produced at the start of writing each chapter, before any prose is generated. It is mandatory for every chapter, regardless of length, regardless of who is writing.

## What a chapter mini-outline contains

For each chapter, a file at `chapters/NN-slug.outline.md` (named to sit next to the chapter file it plans). The file contains:

### Header

```
# Chapter NN — Title — Mini-outline

**Throughline contribution**: [one sentence from throughline.md's
per-chapter section, repeated here for the writer's working context]

**Target**: [word count, page count]

**Status**: [planning / approved / writing / revising / complete]
```

### Section plan

For each section the chapter will contain, the following fields:

```
### Section N — Short title (target word count)

**Purpose**: What does this section do that no other section in the
chapter does? One sentence.

**Opening anchor**: The concrete scene, moment, fact, or claim that
opens the section. Specific enough that the writer can begin without
inventing — but not yet written out as prose.

**Beats**: Three to seven things that happen in this section, in
order. Each beat is a short phrase, not a sentence. Beats are
the section's structure; they will become paragraphs or paragraph-groups.

**Sources**: Specific source IDs from sources.json this section
uses. Mark single-source claims that may need verification.

**Throughline-touch**: How (if at all) this specific section advances
the chapter's throughline contribution. Sections that don't advance
the throughline aren't necessarily wrong — they may be foundational
or atmospheric — but the writer should know which sections carry
the spine and which do not.

**Handoff**: How this section ends and how the next section opens.
For the last section of the chapter, how this chapter's ending
hands off to the next chapter.

**Special techniques** (if any): Mark sections that will use specific
disciplines — productive puzzlement for a central insight, an extended
scene rather than analysis, a deliberate quotation, a foto-marker
placement, a flashforward.
```

### Section count

Most chapters will have **four to eight sections**. Fewer than four means the chapter is probably either short (and acceptable) or under-decomposed (and at risk of structureless drift). More than eight means the chapter is either long (and acceptable) or fragmented (and may be two chapters).

For a typical 5000-8000 word adult chapter, six to seven sections of 800-1300 words each is the sweet spot.

For shorter chapters (under 2000 words), three to four sections of 400-600 words.

For very short chapters (a Bruna-register picture book spread, an essay), the mini-outline may compress to just the beats with no formal sections — but a mini-outline still exists.

## When the mini-outline is produced

At the start of writing each chapter in Phase 4, before any prose. The mini-outline is the **first deliverable** of each chapter's writing loop. Specifically:

1. Load persona, throughline, chapter entry from book outline, relevant sources, prior chapter's handoff note
2. **Produce the mini-outline** as `chapters/NN-slug.outline.md`
3. **Show the mini-outline to the user.** This is not an approval gate (no waiting for explicit yes) but a *visibility moment*: the user sees the plan and can intervene if they spot a problem.
4. **Proceed to writing the first section** unless the user has intervened
5. Continue section by section, applying per-paragraph self-critique to each
6. After all sections are written, run the chapter-level self-critique pass (anti-AI-tells, language-naturalness, reading-level, throughline-check, productive-puzzlement-check if applicable)

The visibility-without-gate pattern lets the work proceed while keeping the user informed. For long working sessions the user may not want to be a gatekeeper at every chapter — but they always want the chance to see the plan and to say "actually, section 4 should come first" before the prose is generated.

## Why this matters specifically for agents with smaller budgets

The skill must be usable by agents whose per-call context budget is much smaller than a high-end Claude session. For such agents, the mini-outline is not a convenience but a structural requirement. Several reasons:

### Section-at-a-time writing

With a mini-outline, the agent can write **one section per call** rather than trying to fit the entire chapter into a single context window. Each section call loads only: the persona, the throughline contribution for this chapter, the mini-outline (which is compact), the source material for *this section*, and the immediately preceding section for tonal continuity. That fits comfortably in budgets that could not hold the entire chapter's working context.

For an 8000-word chapter, this means six to eight separate, well-scoped calls instead of one impossibly-large call.

### Resumable across sessions

If the agent (or the human) has to pause mid-chapter — whether from session limits, fatigue, or external interruption — resuming is trivial when a mini-outline exists. The handoff is: "*I was writing chapter 3, sections 1-3 are complete (in chapters/03-slug.md), section 4 was the next one. Here's the mini-outline; here's the persona; here's section 3 for tonal continuity; please write section 4.*" Without a mini-outline, the resuming agent has to either re-read everything to figure out where things stand or improvise structure that the original writer may have planned differently.

### Pre-flight detection of structural problems

The most expensive failure mode in chapter writing is producing a full chapter that has the wrong structure — the analysis is well-written but should have been a scene, the chapter weights wrongly toward background where it should weight toward the central question, the handoff to the next chapter is impossible because the chapter ends in the wrong place. A mini-outline surfaces these problems before any prose is generated. Five minutes of mini-outline revision saves hours of chapter rewriting.

For smaller-budget agents this is even more critical: they have fewer tokens to spend on rewriting. The mini-outline shifts that cost from generation to planning, which is the cheaper place to put it.

### Standardised section interface

When sections are explicitly bounded with handoffs, the agent has a well-defined interface between sections. Section N ends in a known state; section N+1 begins from that state. The agent does not have to keep all of chapter 3's prior content in working memory; it only needs the immediately-prior section's ending and the mini-outline plan for the current section.

This is the same engineering principle that makes well-designed software modular: clear interfaces between components let each component be reasoned about independently. For documents being written under context constraints, clear interfaces between sections do the same job.

## How the mini-outline is *not* the chapter

A common failure mode in AI-generated mini-outlines is that they become miniature versions of the chapter — full sentences, complete arguments, prose-style writing. That defeats the purpose. The mini-outline is **structural**, not draft prose. It says *what* will happen in each section, in compressed form, without saying *how* the prose will say it.

Compare:

**Bad mini-outline (prose-style, looks like a chapter):**

> Section 2: Wilhelm flees to the Netherlands. The Kaiser had been at the German headquarters in Spa, Belgium, since the war's end approached. By November 9th, however, his position had become untenable. The chancellor announced his abdication without authorization. Wilhelm, sensing the futility, ordered his special train to depart for the Dutch border...

**Good mini-outline (structural, says what happens):**

> ### Section 2 — Wilhelm flees (1200 wo)
>
> **Purpose**: shows the monarchy's symbolic collapse and introduces the
> resentment that fuels the Dolchstoßlegende — Wilhelm did not die fighting.
>
> **Opening anchor**: Wilhelm's train arriving at Eijsden station, 07:10 on
> 10 November 1918. Stationmaster Pinckers initially refuses passage.
>
> **Beats**:
> - Hohenzollern train route Spa → Dutch border (departure 14:30 on Nov 9)
> - The waiting at intermediate station, the unanswered telegrams
> - Eijsden arrival, Pinckers refusal, telegram to Den Haag, Wilhelmina's asylum
> - Amerongen 18 months, then Doorn until 1941 death
> - The "Wilhelm should have died fighting" reaction in nationalist circles
> - Ludendorff's 1919 memoirs version (planting the Dolchstoßlegende seed)
>
> **Sources**: [3, 8, 12]
>
> **Throughline-touch**: this section sets up the central early-Weimar grievance
> — that the Kaiser fled rather than fell. The "Novemberverbrecher" frame in
> §1 (Erzberger's murder) and the "shameful peace" frame from this section
> together form the emotional landscape into which the NSDAP grows.
>
> **Handoff to §3**: from "the keizer is gone, betrayed his army" to "but the
> army knew it was actually lost — Ludendorff's secret request" — pivots from
> myth to the contradicting fact.

Five hundred words of structural plan rather than five hundred words of draft prose. The agent writes the actual prose **after** this plan exists, and the plan is short enough that it lives easily in a section-writing call's context budget.

## Anti-AI-tells specific to mini-outlines

AI-generated mini-outlines fail in characteristic ways. Catch each during self-critique of the mini-outline (before any prose is written).

### Tell 1 — Sections that are actually paragraphs

The mini-outline divides 6000 words into twelve sections of 500 words each. This is over-decomposition: 500-word "sections" are paragraphs in a fluid chapter, not section-units. The chapter will read as choppy.

**Cure**: aim for 800-1500 word sections in adult-literary-general chapters. Fewer, larger sections create flow; many small sections create fragmentation.

### Tell 2 — Sections that have no purpose distinct from each other

Section 1: "Introduces the topic." Section 2: "Develops the topic further." Section 3: "Deepens the analysis." This is fake-decomposition — each section's "purpose" is a synonym for the others. The chapter has no internal structure; it just has paragraphs grouped under arbitrary headers.

**Cure**: every section's purpose must be specific enough that you could swap two sections and the result would be wrong. If swapping sections doesn't matter, they aren't distinct sections.

### Tell 3 — Beats that are themes, not events

"The horror of war." "The disillusionment." "The moral collapse." These are atmospheric descriptions, not beats. A beat is something that *happens* in the section — an event, a specific claim, a concrete moment.

**Cure**: every beat should be a verb-driven phrase. "Erzberger signs at 5:15." "Wilhelm's train crosses the Dutch border." "Pabst gives the kill order at the Eden Hotel." These are beats. "The collapse of monarchy" is a theme.

### Tell 4 — Missing handoffs

The mini-outline lists sections in order but does not specify how section N ends and section N+1 begins. The result is a chapter that feels like list-of-things-that-happened rather than narrative-with-momentum.

**Cure**: every section except the last needs an explicit handoff sentence. The handoff is what makes the chapter feel inevitable rather than enumerated.

### Tell 5 — Throughline-touch as decoration

Every section's throughline-touch field reads similarly — "advances the central argument" or "supports the book's thesis." This is the same fake-decomposition as Tell 2, just at the throughline layer.

**Cure**: be specific or write "this section is foundational/atmospheric and does not directly advance the throughline." Sections that do not advance the throughline are not necessarily bad, but acknowledging it honestly is better than pretending every section does throughline-work.

### Tell 6 — Word budgets that don't add up

Mini-outlines that claim 8000 total words but whose section budgets sum to 5200 or 11000. AI generates plausible numbers without summing them.

**Cure**: sum the section budgets. They should equal the chapter target within ±10%. If they don't, either the chapter is mis-budgeted or the sections are wrongly sized.

### Tell 7 — Sources spread evenly when they shouldn't be

Each section is annotated with one or two sources, distributed evenly. Real chapters often have sections that lean heavily on one source (a long primary-source passage, a single biographical study) while other sections weave many sources lightly. Even distribution is a sign the AI assigned sources to look thorough rather than because the section actually uses them.

**Cure**: be honest about which sections need which sources. Some sections may use zero sources (pure synthesis from the writer's understanding); others may use eight (a dense factual reconstruction). Distribution should reflect the work, not the appearance of work.

## Integration with the existing skill

### Phase 3 (Outline)

No change to Phase 3 itself. The book-level outline remains as it is. The mini-outlines are a Phase 4 artifact, not a Phase 3 one — they require enough context (persona, throughline, source state, prior-chapter handoff) that they belong inside the writing loop, not before it.

### Phase 4 (Writing) — per-chapter loop modification

The per-chapter loop becomes:

1. **Mini-outline production** (new step, mandatory). Produce `chapters/NN-slug.outline.md` per the format above. Show to user without gate; user may intervene but agent proceeds.
2. **Mini-outline self-critique** (new step, mandatory). Apply the seven anti-AI-tells above to the mini-outline. Revise if any fire.
3. **Section-by-section writing**. For each section, the agent loads: persona, throughline-contribution, mini-outline, source material for this section, immediately preceding section for tonal continuity. Writes the section. Applies per-paragraph self-critique (anti-AI-tells, language-naturalness, reading-level checks).
4. **Chapter-level self-critique** (existing step, runs after all sections complete). Applies chapter-level checks: throughline-check, productive-puzzlement check if applicable, voice consistency across sections, skim-test for sentences that would be skipped.
5. **Status update**: chapter moves from `planning` → `writing` → `draft`.

### Phase 5 (Manuscript Finishing)

No change to Phase 5. The mini-outlines remain as project artefacts. They are not part of the published book but are part of the project's working state, useful for later revisions or for resuming work after the project sits idle.

For revision-mode (`revision-mode.md`), the mini-outline is consulted: if a section needs revision, the agent reads the section's mini-outline entry to remember the section's purpose, then revises the prose accordingly. Without the mini-outline, the reviser may rewrite the section toward a different purpose than the original, breaking the chapter's plan.

## A note on writers who already plan this way

Many experienced human writers produce something equivalent to a mini-outline in their notebooks before writing each chapter. The discipline this reference describes is not a new invention; it is the formalisation of a long-standing practice. What it adds is that the formalisation lives as a file alongside the chapter, available to whoever (or whichever agent) picks up the work next.

For writers who already think this way, the mini-outline is just writing down what they were already going to think. For agents that do not naturally decompose, the mini-outline is the structural scaffolding that makes long-form work feasible under context constraints.

Either way, the result is the same: every chapter has a plan before it has prose, and the plan is good enough that the prose can be written one bounded chunk at a time.
