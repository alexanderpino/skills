# Characters

A novel lives or dies on its people. A plot can be inventive, the prose can be polished, the setting can be vivid — but if the characters don't feel like they have lives the reader didn't see, the book is flat.

This file governs characters: how they're defined, how depth is calibrated, how arcs are tracked, how relationships are recorded, how knowledge-state is maintained across a timeline, and how characters persist across a series.

Read this during Phase 2 (Preparation) in fiction mode, and consult it during writing whenever a character makes a significant decision or change.

---

## Table of contents

1. The four depth tiers
2. Protagonist template — the deep profile
3. Antagonist template — the adversary's internal logic
4. Support template — fleshed out but not central
5. Secondary template — the light touch
6. Arc tracking: where a character goes
7. Growth events: no unearned change
8. Relationships as first-class entities
9. Knowledge state: what does this character know when?
10. Series support: characters across multiple books
11. Library storage and reuse
12. Consistency checks

---

## 1. The four depth tiers

Not every character needs a complete interior life. A butler who appears twice doesn't need a childhood trauma. A protagonist does. Calibrate by role:

| Tier | Who | What they get |
|---|---|---|
| **Protagonist** | POV characters, central figures | Full profile + arc + relationships + knowledge log |
| **Antagonist** | Whoever opposes the protagonist | Full profile + internal logic + arc (theirs matters too) |
| **Support** | Major allies, love interests, key secondary | Mid-depth profile + arc notes + key relationships |
| **Secondary** | Named minor characters | Surface sheet only (name, role, 2-3 defining traits) |

A book may have 1–5 protagonists (single-POV to multi-POV), 1–3 antagonists, 5–15 support characters, and any number of secondary characters. In a very long novel these counts grow; in a novella they shrink.

**Rule:** every named character gets *some* file. Unnamed characters ("the barkeeper", "a sailor") don't — they're part of scenes, not of the book's roster. The moment a character gets a name, they get a file, even if it's 4 lines.

---

## 2. Protagonist template

Save to `<book>/notes/characters/protagonist-<slug>.md`. Multiple protagonists get multiple files.

```markdown
---
tier: protagonist
name: Mina Murray
aliases: [Mina Harker (after marriage)]
age_at_story_start: 22
first_appears: chapter 3
pov: true
---

# Mina Murray

## Surface
[Two or three paragraphs. The things another character would notice in the
first minute. Physical presence, age, occupation, manner, voice in
casual speech, distinguishing habits or tics. How they dress. How they
hold themselves. What they look like when caught off-guard.]

## Interior
[Three or four paragraphs. The things another character wouldn't see for
months or ever. Their actual way of perceiving the world. What they
value and what they're afraid of. The pattern of their attention — what
they notice that others miss, what they miss that others notice. The
shape of their thinking. What they'd never say aloud.]

## Backstory
[One or two paragraphs. The formative events before the book opens.
Childhood, family, major turning points. Enough that every choice they
make in the book makes sense in this light. Don't write a biography —
write the load-bearing parts.]

## Wants — stated
[What they would say they want, if asked. The surface goal that drives
their plot actions.]

## Wants — real
[What they actually want, often unknown to themselves. The deeper need.
The gap between stated and real wants is often the character's arc.]

## Fears
[The real ones, the ones that make them who they are. Not "afraid of
spiders" unless that fear carries symbolic weight. The existential
fears.]

## Contradictions
[Every protagonist needs at least one real contradiction. Someone who
wants intimacy and flinches from it. Someone who believes in rules and
breaks them. Someone who claims to be pragmatic but acts on faith.
The contradiction is the engine.]

## Voice
[How they talk. Sentence length. Vocabulary range. Topics they return
to. Things they never say. How they sound different in dialogue than in
their own POV passages. If they speak multiple languages or registers,
how they switch and when.]

## Skills and limitations
[What they're genuinely good at. What they're bad at. What they think
they're good at but aren't. What they're better at than they know.]

## Signature gestures / habits
[Small physical or verbal tells the reader will come to recognise.
Not quirks — calibrated specificity. A hand going to a locket. A pause
before answering. The way they say a name.]

## Arc summary
[One paragraph. Where they start, where they end, what transforms them.
The full arc lives in arc-<slug>.md, but the one-paragraph summary
sits here as the north star.]
```

**Anti-patterns to avoid:**
- Listing 15 personality traits that don't cohere into a person
- Backstory that exists only to justify a plot mechanism
- Protagonists with no contradictions ("she was smart and kind and brave")
- "Dark past" substituting for actual interiority
- Skills that match exactly what the plot needs and nothing else

---

## 3. Antagonist template

Save to `<book>/notes/characters/antagonist-<slug>.md`. Mostly same structure as protagonist, with these additions:

```markdown
## What they actually believe
[Not "they're evil". Every functional antagonist has an internal logic
that makes sense from the inside. What's their theory of the world? Why
do they think they're right — or if they know they're wrong, what's the
compensating logic? A villain without a coherent interior is a
cardboard one.]

## Why this conflict matters to them
[What does the protagonist (or the protagonist's goal) take from them,
threaten about them, expose in them? The stakes from their side.]

## Where they could have turned
[Every antagonist had a branching point. When? What would it have taken?
This is sometimes backstory, sometimes mid-book opportunity. The reader
should sense it exists even if it's never named.]

## Their view of the protagonist
[How do they see the person opposing them? What do they misunderstand?
What do they see clearly that the protagonist misses about themselves?]
```

**Rule:** a villain who is just evil is a failure. The reader should be able to argue their position — not agree with it, but understand it.

---

## 4. Support template

Save to `<book>/notes/characters/support-<slug>.md`. Mid-depth profile:

```markdown
---
tier: support
name: Jonathan Harker
age_at_story_start: 24
first_appears: chapter 1
relationship_to_protagonist: fiancé / husband
---

# Jonathan Harker

## Surface
[One paragraph. Who they appear to be.]

## Interior
[One or two paragraphs. The substance under the surface, enough that
their choices in the book make sense.]

## Backstory
[A paragraph or less. Only the parts that bear on the story.]

## Function in the story
[What do they do for the plot? What do they do for the protagonist's
arc? Most support characters serve both. If they only serve one,
question whether they're the right character.]

## Voice
[Distinguishable from the protagonist's and other support. Even a few
notes help consistency.]

## Arc
[Brief. Support characters often have mini-arcs — a change, a
reckoning, a choice.]

## Key relationships
[Who do they matter to, besides the protagonist? Any relationships that
affect the plot.]
```

---

## 5. Secondary template

Save to `<book>/notes/characters/secondary-<slug>.md` or, for efficiency, collect all secondaries in `<book>/notes/characters/secondary.md` as a list.

Format per character (compact):

```markdown
## Mr. Swales
**Role:** Whitby fisherman, elderly.
**Appears in:** chapters 6, 8.
**Function:** Foreshadowing — the local voice of "something is wrong here".
**Voice/traits:** Broad Yorkshire dialect. Sees what the visitors don't.
Dies mysteriously between appearances.
**Key facts:** Age ~75. Knows the coast. Lost his wife to "the sea" years
ago (metaphorical? literal? — leave ambiguous).
```

Four to eight lines. If a secondary character starts demanding more, promote them to support and write the full sheet.

---

## 6. Arc tracking: where a character goes

For protagonists and antagonists (and major support), maintain `<book>/notes/characters/arc-<slug>.md`:

```markdown
# Mina Murray — arc

## Starting state (chapter 1)
Engaged schoolteacher. Competent, quiet, dutiful. Believes her role is
to support Jonathan's career. Feels underestimated but doesn't challenge
it. Writes obsessively in her diary.

## Arc in one sentence
From competent supporter to the investigative intelligence at the
centre of the counter-attack.

## Key beats (mapped to chapters)

### Beat 1 — Chapter 3: Introduction
She is introduced in her element (teaching, correspondence), established
as sharp but deferential.

### Beat 2 — Chapter 8: First sign she sees what others don't
She notices something about Lucy's illness that Dr. Seward and Van
Helsing miss. She says it tentatively; they brush past it. Planted
seed.

### Beat 3 — Chapter 12: The group patronises her
When she offers to transcribe and collate the documents, the men
accept but frame it as clerical work. She accepts the framing because
she hasn't yet seen her own capacity.

### Beat 4 — Chapter 16: The transcription reveals the pattern
By collating the documents, she sees a pattern none of them saw. This
is the turning point — not external, internal. She realises what she's
capable of.

### Beat 5 — Chapter 21: She is used against them
The antagonist uses her capability against the group. She becomes the
conduit of the threat. Darkest point.

### Beat 6 — Chapter 25: She uses the conduit back
She realises the connection runs both ways and uses it for surveillance.
Agency reclaimed, now on her terms.

### Final state (epilogue)
Mother. Her role in the events is recorded in the document she herself
compiled. She knows what she did; she also knows how the world will
remember it. Both sit in her quietly.

## What changes
Not her nature — she's always been this. What changes is her
permission-to-herself. The arc is a revelation to her, not an
acquisition.

## What stays the same
Her dutifulness. Her formality. Her pattern of listening before
speaking. The change is underneath these constants.
```

**Key principle:** a character arc is about *change*, but not total change. Something stays constant — the thing that makes them *them*. The arc is usually a revelation, a shift in what they permit themselves, or a cost they decide to pay. Avoid "she became a different person" as a description of any arc.

---

## 7. Growth events: no unearned change

Rule: **a character does not change off-stage or without cause.** Every shift in a character's arc must tie to an event in the book.

Maintain a `growth-events` log inside each arc file:

```markdown
## Growth events

| Chapter | Event | What it changes | Why it lands |
|---------|-------|-----------------|--------------|
| 8 | She notices Lucy's pattern | Plants doubt that the experts know everything | Small, private noticing — doesn't challenge her self-concept yet |
| 16 | The transcription reveals the pattern | Realises her specific capability | It's earned by hours of patient work, consistent with her character |
| 21 | She is turned into a conduit | Forces her agency question into crisis | External event imposes the question she's been avoiding |
| 25 | She uses the conduit back | Agency fully claimed | Previous beats have built to this — no sudden transformation |
```

Before writing a chapter in which a character changes, check: is this change in the growth events log? If not, either (a) it shouldn't happen, or (b) the log is missing an event and needs updating — which may require revising earlier chapters to plant the cause.

**The cheat to avoid:** character X "realises" something between chapters because the plot needs it. If the reader didn't see the moment, the realisation isn't earned. Either show the moment or delay the realisation until something happens that justifies it.

---

## 8. Relationships as first-class entities

Relationships are not just properties of characters. They have their own states, histories, and changes. Maintain `<book>/notes/characters/relationships.md`:

```markdown
# Relationships

## Mina ↔ Jonathan
**Type:** engaged (ch. 1–10), married (ch. 11 onward)
**Met:** four years before story opens, at a cousin's wedding
**Knowledge state at story open:** Jonathan knows Mina well; Mina
knows Jonathan well but has never seen him under pressure
**Arc:** The events of the book reveal things about each to the other
that didn't surface in normal life. They're still the same people but
they now know things about each other they didn't.
**Key moments:**
- Ch. 4: Jonathan's letter from Transylvania — the last normal
  communication
- Ch. 11: Reunion in Budapest — changed, marked, recovering
- Ch. 25: Working side by side on the final plan — functional
  partnership emerges
**Notes:** The love doesn't change. The shape of the partnership does.

## Mina ↔ Lucy
**Type:** closest friendship
**Met:** schoolgirls together
**Arc:** Loss. The book is also about Mina losing Lucy — that grief is
fuel for everything after.
**Key moments:**
- Ch. 6–9: Whitby visit, Lucy's decline begins
- Ch. 11: Lucy's death
- Ch. 16+: Lucy's presence in the transcripts (her letters, diary)
**Notes:** Lucy appears in the second half only through what she wrote
earlier. That absence structures Mina's grief.

## Mina ↔ Van Helsing
**Type:** collaborator (after ch. 14), intellectual father-figure
**Met:** chapter 14
**Knowledge state at meeting:** He is wary of including her; she is
deferential to his authority
**Arc:** He comes to see her as a peer. She comes to see him as a
mentor rather than an authority.
**Key moments:**
- Ch. 14: First meeting, cautious mutual assessment
- Ch. 16: He sees what she's done with the transcripts — shift
- Ch. 22: He defers to her reasoning for the first time
**Notes:** The relationship's real arc is about who gets to be serious
in this kind of work.
```

**What relationships track:**
- Type (friend, enemy, lover, family, colleague, etc.) and whether it changes
- When they met — a timeline fact the prose must respect
- Key shared events — these are the moments the relationship pivots on
- Knowledge state — what each knows about the other
- Arc — what the relationship becomes, or how it ends

---

## 9. Knowledge state: what does this character know when?

Major characters accumulate knowledge through the book. Tracking this prevents one of fiction's most common errors: a character knows something in chapter 4 that they only learn in chapter 7.

For each major character, maintain `<book>/notes/characters/knowledge-<slug>.md`:

```markdown
# Mina — knowledge timeline

## Chapter 1
**Knows:** Everything about her life as of 1893. Jonathan is abroad on
business. The nature of her work, her school, her circle.
**Doesn't know:** That Jonathan's business is not normal. Anything
about vampires. That Lucy is in any danger.

## Chapter 4
**Newly knows:** Jonathan's letters have stopped. Something is wrong.
**Doesn't know:** What.

## Chapter 8
**Newly knows:** Lucy is sleepwalking. Small marks on her neck. A local
fisherman was found dead unnaturally.
**Doesn't know:** Cause. She is beginning to suspect pattern but has no
vocabulary for it.

## Chapter 12
**Newly knows:** Jonathan has resurfaced in Budapest. Lucy is dead.
The men are hunting something.
**Doesn't know:** That she should be part of it. That the thing they
hunt can reach her.

[continues chapter by chapter]
```

This file is maintained as chapters are drafted. Before writing a character's line of dialogue or internal thought in a new chapter, consult this file: does this character plausibly know what they seem to be saying they know?

**Shortcut for light cases:** for secondary and some support characters, a one-paragraph "knowledge at story end" note is often enough. Full tracking is for POV characters and anyone whose knowledge directly drives plot.

---

## 10. Series support: characters across multiple books

A character in a series has a life that spans books. Book 2 begins where book 1 ended — but the character's state (age, relationships, knowledge, scars, growth) has continued.

### Series-level character file

Save to `~/characters/<slug>/` (library structure below). The file `series-state.md` tracks cross-book state:

```markdown
# Mina Murray — series state

## Books in series
1. *Dracula* (1897-equivalent setting) — protagonist, co-POV
2. *The Amsterdam Letters* (1904-equivalent) — protagonist, sole POV
3. *Quincey's Inheritance* (1923-equivalent) — mentor role, not POV

## State at end of book 1
- Age: 22
- Marital status: Married (Jonathan)
- Children: Pregnant at epilogue
- Knowledge gained: Everything about the events of Dracula. Has read
  and transcribed all documents.
- Key scars/changes: Bears the mark of being used as a conduit. This
  doesn't fade. Her relationship with Jonathan has been tested and
  deepened. She knows what she is capable of.
- Relationships: Van Helsing (mentor), Seward (colleague), Arthur
  (friend, grieving). Quincey Morris (deceased — his memory carried)

## State at end of book 2
[filled when book 2 is written]

## State at end of book 3
[filled when book 3 is written]

## Arc across the series
Book 1: revelation (she discovers her capacity)
Book 2: consolidation (she acts from that capacity, faces new costs)
Book 3: transmission (she prepares the next generation)
```

### How series state is used in a new book

At the start of a new book in the series, during Phase 2 (Preparation):

1. Load `~/characters/<slug>/series-state.md` for every character continuing into this book
2. Copy the relevant characters' files (profile, arc, knowledge, relationships) from `~/characters/<slug>/` into `<book>/notes/characters/`
3. Use the "state at end of previous book" as the **starting state** for this book — the character begins this book knowing what they knew then, scarred as they were scarred, in the relationships they were in
4. As this book proceeds, its chapters update the character's state — at the end of this book, update `~/characters/<slug>/series-state.md` with the new end-state

**The rule that makes this work:** no character in book N starts in a state inconsistent with their end-state in book N-1. A character who lost a hand in book 1 still has one hand in book 2. A character who stopped drinking in book 1 either still isn't drinking in book 2 or has an explained relapse. Continuity is a promise to the reader.

---

## 11. Library storage and reuse

Characters, like personas, have two layers:

### Library layer — `~/characters/<slug>/`

Global. Characters saved here can be reused across books. Useful for:
- Series protagonists (a detective appearing in multiple novels)
- Recurring supporting characters across standalone books
- An author's "stock company" of characters in related works

Structure:

```
~/characters/mina-murray/
├── profile.md              # the deep profile
├── voice-samples/          # 2-4 short samples of this character's voice
│   ├── dialogue.md
│   ├── internal-monologue.md
│   └── letter.md
├── series-state.md         # cross-book state tracking
└── notes.md                # author's notes on this character, evolution log
```

### Book layer — `<book>/notes/characters/`

Per-book, working copy. When a character is loaded from the library at preparation time, their files are **copied** into the book:

```
<book>/notes/characters/
├── protagonist-mina-murray.md
├── arc-mina-murray.md
├── knowledge-mina-murray.md
├── antagonist-dracula.md
├── arc-dracula.md
├── support-jonathan-harker.md
├── support-van-helsing.md
├── secondary.md            # all the minor characters in one file
└── relationships.md
```

At the end of the book (assembly), changes to the character in the book can be folded back into the library version, kept book-only, or logged in notes. Same pattern as personas.

### Creating a character — routes

1. **From library** — load an existing character. Good for series, recurring figures.
2. **Structured intake** — fill in the template fields. Good when user knows exactly who they want.
3. **Free description, skill distills** — user writes a paragraph, skill produces a full profile. Good for fast prototyping.
4. **From archetype** — propose 2–3 starting archetypes based on genre and role (see below). User picks and customises.

### Character archetypes by role (for Route 4)

For **protagonists**, common seeds:
- *The reluctant investigator* — gets drawn into something they tried to avoid
- *The specialist out of context* — skilled in their world, lost in the book's world
- *The watcher who acts* — observes carefully until they can't not intervene
- *The inheritor* — comes into something they didn't choose and must reckon with
- *The outsider returning* — left, comes back to a place that has changed or hasn't

For **antagonists**:
- *The true believer* — actions driven by sincere (but wrong) conviction
- *The wounded* — harm comes from unhealed injury, not malice
- *The rationalist* — cold calculation; incapable of seeing what rationality misses
- *The charming predator* — superficial warmth masking emptiness
- *The system* — not a person but an institution or force personified

Archetypes are starting points, not endpoints. Every archetype becomes a real specific person through the profile work.

---

## 12. Consistency checks

During writing and at assembly, run these checks for every chapter:

### Per-chapter (after drafting)
- **Voice consistency:** Does each character sound like themselves? Re-read their lines against their voice notes.
- **Knowledge state:** Does every character in this chapter know only what they plausibly know at this point? Consult `knowledge-<slug>.md`.
- **Relationship state:** Do the interactions reflect where the relationship is at this point? Consult `relationships.md`.
- **Arc alignment:** If this chapter is supposed to land a growth event, does it actually land? If it's not a growth-event chapter, did the character accidentally change anyway?
- **Physical consistency:** Eye colour, age, height, scars, distinguishing features — same as established.

### At assembly
All of the per-chapter checks, but swept across the whole book. Look for:
- A character knowing something in chapter N that they only learn in chapter N+k
- A relationship being warm in chapter 6 and frosty in chapter 7 without cause
- A physical description drift (she was 5'4" in chapter 2, 5'7" in chapter 14)
- An arc beat that was written but doesn't actually land because the setup was cut
- Named characters introduced who then disappear without purpose (either reintroduce or remove the name)

Record issues in `consistency-report.md` along with the other consistency findings (see `assembly.md`).

---

## A note on scope

Characters are, after prose quality itself, the most valuable thing a novel has. Investing time in this layer of the skill is not overhead — it's the work. A shallow character who goes through a plot is a novel no one remembers. A deep character who goes through the same plot is a novel that sits with the reader for years.

But: proportion to project. A 40,000-word novella doesn't need every character treated like a Tolstoy protagonist. Use the depth tiers honestly. The secondaries can be four lines. The protagonist gets the full treatment. Don't bury a small book in a database of imaginary friends.
