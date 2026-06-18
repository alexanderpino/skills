# Multi-volume projects

Some books are bigger than one book. Either because the subject matter genuinely exceeds what a reader can absorb in a single volume, or because the work splits naturally along an axis that produces two complementary books better than one large one.

This file covers the structural choices for multi-volume projects: what the relationships between volumes can be, how to choose, and what each model implies for outlining and writing.

Read at intake when the user signals "this might be more than one book" or when the page-count estimate runs significantly over what a single volume can hold. Read again at outline if multi-volume was chosen, because the relationship type affects per-volume outlining.

---

## When to consider splitting

A project should be considered for multi-volume if:

- **Estimated total pages exceed ~600** in the chosen format. Few readers complete a 600+ page book; even fewer complete it without losing thread. There are exceptions (a deeply-anticipated history of a major subject, a beloved author's magnum opus), but for most projects, 600 pages is the ceiling.
- **The subject matter has a natural seam.** "How something works" + "the history of how it came to work that way" is a natural seam. "Theory" + "practice" is another. "Foundations" + "advanced" is a third. When the seam is genuine, splitting makes both volumes better; when forced, both feel incomplete.
- **The audience splits on a real axis.** Some readers will want the overview only; others will want the depth. Forcing both groups through one volume serves neither well.
- **Production realities require it.** Page-budget constraints from a publisher, print-cost considerations for self-publishing, marketing reasons.

A project should *not* split just because it's long. Length alone, without a natural seam, produces two unsatisfying half-books rather than one good big book. *Game Engine Architecture* is 1200 pages and successfully a single volume because there is no obvious seam to split it along; splitting would arbitrarily separate things that belong together.

---

## The six models

Most multi-volume projects follow one of six structural patterns. They differ in how readers are expected to engage and how the volumes relate.

### Model 1 — Sequential

**The relationship.** Volume B assumes Volume A. Reading order is fixed. Most readers read both, in order.

**Examples.** A trilogy in fiction. A two-volume textbook where the first covers undergraduate material and the second covers graduate material. *Real-Time Rendering* across editions where each builds on the last (within a single edition, it is a single volume).

**Implications.**
- Volume A introduces shared concepts, vocabulary, characters/notation
- Volume B references back; doesn't reintroduce
- Outlines must be planned together — Volume A's choices constrain Volume B
- A reader who reads only Volume A gets a partial experience by design

**Intake fields specific to this model.**
- What concepts does Volume A definitely introduce that Volume B will rely on?
- Where does Volume A end relative to where Volume B begins? (No gap, no overlap.)
- What's the recommended gap between reading them? (Same week, same year, doesn't matter?)

**Best fit for.** Long fiction series, multi-edition academic series, projects where the material has a single natural progression.

### Model 2 — Material plus exercises

**The relationship.** Volume A is the textbook. Volume B is the workbook with exercises and answers. Used together, often by students under instruction.

**Examples.** Many language learning textbooks. Math textbook + solutions manual. Some music theory works.

**Implications.**
- Volume A's structure is the spine; Volume B mirrors it
- Volume B's exercises map to Volume A's chapters
- A reader can use Volume A alone (no exercises); using Volume B alone is meaningless
- Volume B is often shorter

**Intake fields specific to this model.**
- Are the exercises included in Volume A as well, just without solutions, or only in Volume B?
- Is Volume B intended to be sold separately, bundled, or only available with Volume A?
- Are the answers fully worked, or just final answers?

**Best fit for.** School and instructional textbooks where exercises are a major part of the learning model.

### Model 3 — How plus why

**The relationship.** Volume A presents the material assuming the reader will accept the basics on faith ("the empire used a system called X"). Volume B explains why ("X arose from political needs of a particular era and resolved tensions between Y and Z"). Each can be read alone; together they reinforce.

**Examples.** A history book that names the monsoons in passing, paired with a meteorology book that explains how monsoons work. A computer science textbook that uses balanced trees, paired with a deep book on balanced tree theory. A historical atlas (the maps + brief context) paired with a narrative history of the same period.

**Implications.**
- Volume A is the broader, often shorter book
- Volume B fills in the why behind concepts Volume A names
- Either can be the entry point — different readers will choose differently
- Cross-references between volumes are explicit but not blocking

**Intake fields specific to this model.**
- Which concepts in Volume A get full why-explanation in Volume B?
- Which concepts in Volume A are deliberately left as just-named without Volume B treatment?
- How does Volume A signal to readers that "more on this is in Volume B"?

**Best fit for.** Projects where readers reasonably want either the survey or the depth, and where the depth is genuinely a separate book.

### Model 4 — How plus depth on the same choices (complementary volumes)

**The relationship.** Both volumes describe the same material. Volume A is "how, with a touch of why." Volume B is "why, with depth of how." Same choices, different angles. Reading either gives a complete picture; reading both gives reinforcement and depth.

**Examples.** The AAA engine book in this skill's test (Volume A: how to build the engine, Volume B: why each subsystem is built that way and what the alternatives are). A book on database design that has a hands-on volume and a theory volume covering the same systems.

**Implications.**
- Both volumes follow the same outline structurally
- Both must commit to the same architectural choices — Volume A can't pick archetype ECS while Volume B advocates sparse-set
- Volume A is shorter and faster; Volume B is denser and slower
- A reader can complete a project from Volume A alone; Volume B is for the deeper reader

**Intake fields specific to this model.**
- What concrete choices does the project commit to that both volumes reflect?
- How are the volumes paginated against each other? (Same chapter numbers? Different? Cross-referenced by topic?)
- What proportion of readers are expected to read only Volume A?

**Best fit for.** Technical and craft works where some readers want to do the thing and others want to understand it deeply, and the project commits to specific defendable choices.

### Model 5 — Breadth plus depth on one topic from that breadth

**The relationship.** Volume A surveys a wide field. Volume B goes deep on one specific area within that field. Volume B presupposes Volume A's overview but treats one part of it intensively.

**Examples.** An overview of data structures (Volume A) plus a deep book on balanced trees (Volume B). A survey of 20th-century philosophy plus a deep book on phenomenology. *Real-Time Rendering* plus *Physically Based Rendering* (these are by different authors but exemplify the relationship).

**Implications.**
- Volume A reads like a guide; Volume B like a specialist work
- Most readers of Volume A do not read Volume B
- Volume B's audience is narrower but more committed
- Volume B is often by a different author or includes co-authors

**Intake fields specific to this model.**
- What specific area within Volume A's breadth does Volume B cover?
- Does Volume B require Volume A's overview, or does Volume B re-establish its own context?
- Are the two volumes part of a series with more depth-volumes planned?

**Best fit for.** Subjects where there's a survey audience and a specialist audience, and the specialist material is genuinely a separate book.

### Model 6 — Parallel coverage of one large field

**The relationship.** Two (or more) volumes that together cover a field too big for one. Neither is sequential to the other; each is self-contained on its part of the field.

**Examples.** *The Cambridge History of [X]* in multiple volumes, where each volume covers a period or aspect. *Knuth's The Art of Computer Programming* across volumes (somewhat — there's also some sequencing). *The Oxford Handbook of [X]* with volume-per-area.

**Implications.**
- Volumes can be read in any order, or only one of them
- Each volume is structured as a complete book on its part of the field
- Cross-references exist but are not blocking
- Marketing emphasises "the complete set" but each volume sells alone

**Intake fields specific to this model.**
- How is the field divided across volumes? (By period, by sub-topic, by approach?)
- Do volumes share an editorial framework, or are they more independent?
- How many volumes total? Are more planned beyond the initial set?

**Best fit for.** Reference works, edited collections covering a large field, ambitious survey projects where one volume can't fit the territory.

---

## Choosing the model

The intake conversation for a multi-volume project should arrive at one of these six models. The decision flow:

1. **Is the project actually multi-volume, or is it one long book?**
   - Total pages under 500: probably one volume.
   - Total pages 500–700: maybe one volume, depends on whether there's a natural seam.
   - Total pages over 700: probably multi-volume.

2. **What's the reading relationship?**
   - Sequential (read in order) → Model 1
   - Used together for instruction (textbook + exercises) → Model 2
   - Independent but mutually reinforcing → Models 3, 4, or 6
   - Survey + specialty → Model 5

3. **For independent-but-mutually-reinforcing, which?**
   - Volume A is broader, Volume B fills in why behind named concepts → Model 3
   - Both volumes describe the same material at different depths → Model 4
   - Volume B picks one topic from Volume A's breadth and goes deep → Model 5
   - The volumes cover different aspects of one field, neither subordinate → Model 6

4. **Sanity check: can each volume stand alone?**
   - Model 1: Volume A yes, Volume B no
   - Model 2: Volume A yes, Volume B no
   - Models 3, 4, 5, 6: each volume should stand alone

If a chosen model has Volume B unable to stand alone but the project needs Volume B to sell separately, reconsider the model.

---

## What this means for outlining

After the model is chosen, the outline phase works differently:

- **Sequential** — outline both volumes together; concept introductions in Volume A constrain Volume B.
- **Material + exercises** — outline Volume A first; outline Volume B as a structural mirror with exercise sets per chapter.
- **How + why** — outline both volumes; flag concepts in Volume A as "fully named, deep treatment in Volume B" or "fully treated here, no Volume B equivalent."
- **Complementary** — outline Volume A first; Volume B's outline mirrors Volume A's chapters but addresses the why-with-depth for each.
- **Breadth + depth** — outline Volume A as a complete survey; Volume B's outline is independent but cross-references Volume A's relevant chapter.
- **Parallel** — each volume outlined independently, with shared editorial conventions documented separately.

In all cases, the multi-volume nature of the project should be explicit in `project.json`:

```json
"multi_volume": {
  "model": "complementary",
  "volumes": [
    {"id": "A", "title": "...", "outline_file": "outline-volume-a.md"},
    {"id": "B", "title": "...", "outline_file": "outline-volume-b.md"}
  ],
  "shared_running_example": "Catalyst engine — same engine across both volumes",
  "shared_personas": ["alexander-pino", "saskia-vermeer"]
}
```

---

## What this means for writing

When working on Volume B (or any later volume), the writer must read the corresponding chapters of Volume A first. Continuity matters:

- **Shared terminology** — terms introduced in Volume A keep their definitions
- **Shared notation** — code conventions, diagram conventions, citation style
- **Voice consistency** — same persona(s) writing across volumes
- **Cross-references** — explicit links between volumes ("see Volume A, chapter 5")

This is no different in principle from chapter-to-chapter consistency within one volume; it just spans further. The skill's existing per-chapter loop applies. Just longer.

---

## A note on series-vs-multi-volume

A *series* is a sequence of related books with their own internal structure (most fiction series, some non-fiction series like *For Dummies* or *Pelican History of Art*). Series usually follow Model 1 (sequential) or Model 6 (parallel coverage), but each book in the series is a complete book in its own right, not a half-book.

A *multi-volume work* is a single project that happens to be split across volumes. Each volume isn't an independent book; the project is the book.

The distinction matters at intake. "I want to write a series of books on X" means designing a series — different work from designing a multi-volume project. This file is about the latter. Series planning has its own concerns (recurring characters in fiction, consistent format and conventions in non-fiction series, branding) that aren't covered here.
