# Fiction craft

This file governs fiction-mode. Non-fiction has research at its spine; fiction has world and character. Different load-bearing elements, same workflow shape (persona → intake → preparation → outline → writing → assembly), just substituted contents.

Read this file when the user's intake indicates fiction. The research-protocol.md and parts of writing-craft.md still apply — they're just weighted differently.

---

## Table of contents

1. Fiction genre profiles
2. What replaces Research: preparation (world, characters, structure)
3. Outline for fiction — what changes from the non-fiction template
4. Writing fiction — scene-craft, dialogue, POV, show-don't-tell
5. The truth rule: what fiction still owes the real world
6. Per-chapter self-critique for fiction

---

## 1. Fiction genre profiles

These replace (or sit alongside) the non-fiction profiles in `genre-profiles.md` when the mode is fiction. Pick one during intake; hybrids are fine.

### Literary fiction
Character-driven. Language-conscious. Interior life is the field of play. Plot serves character rather than the reverse. Recent reference points: Marilynne Robinson, Kazuo Ishiguro, Rachel Cusk.

**Reader contract:** "Show me a consciousness I haven't been inside before. Make the sentences themselves worth reading."

**Characteristic moves:** free indirect style, long meditative passages, deliberate ambiguity, endings that open rather than close, a narrator whose reliability is part of the texture.

### Thriller / suspense
Plot-driven. Pace matters more than prose. Chapters end on hooks. The reader should feel the click of pieces locking into place. Dan Brown, Lee Child, Gillian Flynn, John le Carré (literary end).

**Reader contract:** "Don't let me stop turning pages. Earn each twist. Don't cheat."

**Characteristic moves:** short chapters, POV jumps that build parallel tension, revelations paced carefully (never two in a row, never none for too long), a McGuffin that the plot spins around, a protagonist under escalating pressure.

### Horror / gothic
Atmosphere first. Dread is built slowly. The threat is often left partly unseen — the reader's imagination is the weapon. Bram Stoker, Shirley Jackson, Stephen King at his best.

**Reader contract:** "Make me afraid of something specific. Don't resolve it too neatly. Honour the dread."

**Characteristic moves:** epistolary devices (letters, diaries, transcripts) that create intimate dread; landscape as co-character; the protagonist's sanity/reliability as stakes; physical body as site of horror; endings that refuse full resolution.

### Mystery / detective
Puzzle-driven with character overlay. The contract with the reader is strict — clues must be fair, the solution must be deducible in retrospect. Agatha Christie, Tana French, Arthur Conan Doyle.

**Reader contract:** "Play fair. Let me solve it if I'm clever enough. Make the detective interesting."

**Characteristic moves:** clue-placement in plain sight, red herrings that are not cheats (they have other legitimate reasons to be there), a cast of suspects each with motive and opportunity, a detective with a specific method and blind spots.

### Historical fiction
Fiction set in a real past, with real historical events as context. Requires the same research rigour as narrative history. Hilary Mantel, Bernard Cornwell, Colson Whitehead.

**Reader contract:** "Take me to this place and time. Don't fake it. When you invent, invent within what was possible."

**Characteristic moves:** period-specific language without becoming parody, sensory detail drawn from primary sources, real historical figures treated with care, invented characters moving through real events, explicit author's note at the end explaining what was invented vs what happened.

### Science fiction / speculative
Fiction built on an imagined change — technological, social, biological — rigorously followed through. Ursula K. Le Guin, Ted Chiang, Kim Stanley Robinson.

**Reader contract:** "Change one thing about the world, then be honest about the consequences. Make the strangeness say something."

**Characteristic moves:** world-building revealed through character (not info-dump), scientific or social extrapolation treated consistently, the strangeness used as a mirror for the present, a protagonist who finds the world as strange as the reader does (sometimes).

### Fantasy
Imagined worlds with their own rules — magic, creatures, alternate histories. Tolkien, Ursula K. Le Guin, N.K. Jemisin, Terry Pratchett.

**Reader contract:** "Build a world I can believe in. Make the magic have costs. Don't solve problems by surprise."

**Characteristic moves:** magic with rules (and prices), maps and languages and histories that have depth even when not all shown, cultures that feel lived-in, protagonists whose ordinariness grounds the extraordinary.

### Romance
Relationship-centred. The emotional arc is the spine. There are structural conventions readers expect (HEA or HFN — "happily ever after" or "happy for now"). Jane Austen to contemporary.

**Reader contract:** "Make me feel the relationship. Earn the connection. Honour the promised ending."

**Characteristic moves:** alternating POV between the two principals (common in contemporary), emotional beats at specific structural points, physical and emotional tension built in parallel, the "dark night" moment before resolution.

---

## 2. What replaces Research: preparation

For non-fiction, Phase 2 is research. For fiction, Phase 2 is **preparation** — world-building, character work, and structural planning. The deliverables live in the same `notes/` directory but are organised differently.

### Deliverables (in `<book>/notes/`)

```
notes/
├── world.md              # setting, rules, cultures, tech-or-magic systems
├── timeline.md           # the world's history and the book's timeline
├── characters/
│   ├── protagonist.md
│   ├── antagonist.md
│   └── supporting/
│       ├── mentor.md
│       └── ...
├── plot-skeleton.md      # structure, major turns, ending
├── locations.md          # places that matter, with sensory detail
└── research-real/        # if historical/sci-fi: research on real things
    └── ...
```

### World-building — what to actually do

Don't build the world as a Tolkien-scale worldbook unless the book is big enough to need it. Build exactly what the plot touches, and stop.

For realistic settings: a few blocks of detail — where the protagonist lives, where they work, how they get from one to the other, what the weather is like, what the rhythm of ordinary life feels like. Concrete enough that scenes have texture.

For constructed worlds (fantasy, SF): the rules that matter to the plot. If magic exists, who has it, what it costs, what it can't do. If the technology is different, how it changes daily life. Write these in `world.md` as prose, not bullet points — you'll re-read it many times.

### Character work

Character work is the single most important part of fiction preparation. It has its own reference file: **`references/characters.md`**.

That file covers:
- The four depth tiers (protagonist, antagonist, support, secondary) and templates for each
- Arc tracking across chapters
- Growth events — no unearned change
- Relationships as first-class entities with their own state and timeline
- Knowledge-state tracking — what each character knows when
- Series support — characters persisting across multiple books
- Library storage at `~/characters/<slug>/` for reuse
- Consistency checks

Read `characters.md` before doing any character work — it defines the templates and the workflow. The key principles that belong in *every* fiction project:

- Every named character gets a file, even if short
- Protagonists and antagonists get full profiles plus arcs plus knowledge logs
- Characters without contradictions are cardboard — give every principal character at least one
- Arc changes must tie to in-book growth events, not happen off-stage

### The plot skeleton

Fiction outlines are less about "chapter by chapter" (that's Phase 3) and more about the structural bones: what's the central conflict, what's the inciting incident, where's the midpoint reversal, what's the climax, how does it end.

Write `plot-skeleton.md` as prose that tells the story in three or four pages. If you can't summarise it, you don't know what it is yet.

Useful structural templates (pick one or combine):

- **Three-act** — setup / confrontation / resolution. Classical.
- **Hero's journey** — call to adventure / crossing threshold / tests / ordeal / return. Good for fantasy and adventure.
- **Save the cat beats** — 15 beats at specific page-percentages. Commercial fiction.
- **Freytag's pyramid** — rising action, climax, falling action. Classical drama.
- **Seven-point** — hook, plot turn 1, pinch 1, midpoint, pinch 2, plot turn 2, resolution.

These are scaffolding, not prescription. A literary novel may legitimately refuse them.

---

## 3. Outline for fiction

The non-fiction outline template in `outline-template.md` mostly applies, with these substitutions:

- **Opening hook** → "scene or situation this chapter opens on" (same idea)
- **Learning goal** → "what this chapter *does* to the story" — reveals something, raises stakes, changes a relationship, introduces a character, plants a seed
- **Key sources** → not needed for pure fiction (used only in historical fiction and similar)
- **Core arc (beats)** → actual scene beats: what happens, in what order
- **Handoff** → "what this chapter ends on — cliffhanger, revelation, quiet beat, shift of perspective"

Add one new field specific to fiction:

- **POV / narrator** — whose head are we in for this chapter? (In single-POV books this is constant; in multi-POV thrillers and fantasies it changes chapter to chapter.)

---

## 4. Writing fiction — the moves

### Scene construction

A scene is not a summary. A scene is a specific place, a specific time, specific characters doing specific things.

**Anatomy of a scene:**
- **Entry** — drop into concrete sensory detail. Not "It was a cold night." but "The wind off the Thames was cold enough that Jonathan pulled his coat tighter and kept his head down as he crossed the bridge."
- **Interaction or action** — something happens. Character does something. Conflict, conversation, discovery, decision.
- **Shift** — by the end of the scene, *something* has changed. A relationship, an understanding, a situation. If nothing changed, the scene doesn't belong.
- **Exit** — line or beat that carries the reader forward.

### Dialogue

Dialogue is not conversation transcribed. Real conversation is full of filler; fictional dialogue is distilled.

**Rules:**
- Each character's voice should be distinguishable. Vocabulary, rhythm, what they refuse to say, what they return to.
- Dialogue should do at least two things at once: advance the plot *and* reveal character, or reveal character *and* establish relationship, or raise tension *and* convey information.
- Tag sparingly. "said" is invisible and that's a virtue. "Ejaculated", "opined", "exclaimed" — avoid. Action beats ("Mina set down the cup") are often better than tags.
- Read dialogue aloud in your head. If it sounds like writing, it isn't dialogue.

### Point of view

Choose deliberately per book (or per chapter, in multi-POV work).

- **First person** — intimate, limited to narrator's knowledge, unreliable possible
- **Close third** — one character's head at a time, the narrator's camera over their shoulder
- **Omniscient** — access to all characters' heads, authorial voice present. Out of fashion but powerful.
- **Epistolary** — letters, diaries, documents (Dracula's form). Creates unique intimacy and unreliability.

POV rules, once set, shouldn't be broken without purpose. A mid-scene jump into another character's head in a close-third book is a classic failure.

### Show don't tell — the real version

"Show don't tell" is advice so common it's become meaningless. The real version:

- **Tell what the reader doesn't need to experience.** ("Two months passed.")
- **Show what the reader needs to feel.** (The moment a character realises something. The specific argument that breaks a friendship. The death that breaks the protagonist.)

Both moves are legitimate. The mistake is showing trivial things at length and telling crucial things in summary.

### Description

Describe selectively. Not everything the character sees — only what matters to the character or the story. A description of a room should tell us something about the character in it or about what's going to happen there.

Sensory range: don't default to sight. Smell, sound, texture, temperature, taste — at least one non-visual sense per major scene.

### Exposition

How do you tell the reader what they need to know without stopping the story?

- Through character concern — someone in the scene *wants* to know, and we learn alongside them
- Through conflict — the information emerges because characters disagree about it
- Through action — show, don't explain, the mechanism
- Through strategic placement — small amounts of backstory, just-in-time, right before it becomes relevant

Avoid the infodump. A chapter that pauses the story to explain the world is a chapter that has failed.

---

## 5. The truth rule for fiction

Fiction doesn't need citations for invented characters or events. But when fiction touches real things — real people, real places, real historical events, real technical or scientific content — the truth rule applies.

**In historical fiction:**
- Real people should not do things they didn't do, or hold views they didn't hold, or say things they didn't say — unless it's explicitly speculative, and ideally with an author's note
- Events should happen on the dates they happened, in the places they happened
- Invented characters can move through real events; real characters should act in character

**In contemporary fiction:**
- Real places should be recognisable (the restaurant exists at that address, the street runs that direction)
- Real technical content (how a surgery works, how a rifle operates, how code compiles) should be right
- Real cultural content (languages, religions, customs) should be handled with care — research as if non-fiction

**In speculative fiction:**
- If you invent a physics or biology, it should be internally consistent. The rules can be impossible; they can't be incoherent.
- If you extrapolate from real science, the extrapolation should be defensible — not necessarily correct, but not handwaved.

**Author's note at the end:** for any book that touches real history, a short note ("On Sources" or "A Note on What Is and Isn't True") explaining what was invented vs what happened. This is the genre's honesty clause.

When doing this kind of research during fiction-mode preparation, follow `research-protocol.md` as if writing non-fiction for the facts in question. Store them in `sources.json` and cite in the author's note.

---

## 6. Per-chapter self-critique for fiction

After drafting a chapter, read it with these questions. These replace (or augment) the non-fiction critique in `writing-craft.md`.

**Scene-craft:**
- Does every scene end with something changed? If a scene could be cut without losing anything, it probably should be.
- Is the POV consistent per the chapter's decision?
- Does dialogue sound like these specific characters, or like writing?
- Are descriptions pulling their weight, or are they decoration?

**Plot:**
- Does this chapter move the plot forward *and* deepen character? If only one, why?
- Is the chapter-end hook earned, or manipulative?
- Did I accidentally reveal something too early? Or withhold something long enough that the reader feels cheated?

**Character:**
- Did the protagonist do anything in this chapter? (Characters who only react grow boring fast.)
- Did any secondary character feel like a plot device this chapter? Give them one line or gesture that's about them, not about the plot.
- Are characters acting consistently with their character sheet — or if they're breaking pattern, is the break earned?

**Voice and register:**
- Is the prose in the persona's voice, or did I drift?
- Did I lean on any crutch phrase this chapter? (Every writer has them; spot yours.)
- Is there purple prose? Cut it.
- Did I over-use dialogue tags other than "said"? Replace.

**Truth rule:**
- Did I make a claim about the real world (historical, scientific, geographical) that I haven't checked? Check it now.
- If there's real-world content, is there a source for it in `sources.json`?

**The test of the ordinary reader:**
- If I were reading this in bed at 11pm, tired, would I keep going to the next chapter? If no — why not? Fix it.
