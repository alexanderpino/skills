# Genre profiles

Each profile captures what makes that kind of book *that* kind of book. Read the relevant profile during intake (to help the user choose and to calibrate the style guide) and again at the start of writing (to keep the voice honest).

A book rarely fits one profile cleanly. A biography of a scientist is part biography, part history of ideas. A "For Dummies"-style book on compilers is part popular-technical, part textbook. Use profiles as starting points, then mix.

---

## Table of contents

1. Textbook (general-purpose, undergraduate-ish)
2. Academic (research monograph, AIMA-level)
3. Popular-technical ("For Dummies", O'Reilly trade, Manning)
4. Biography
5. Narrative history
6. School textbook (primary/secondary education)
7. Memoir / autobiography
8. Self-improvement / popular psychology
9. Essay collection

---

## 1. Textbook

**Examples on the shelf:** *Structure and Interpretation of Computer Programs*, *Linear Algebra Done Right*, *Campbell Biology*.

**Reader contract:** "Teach me this field so I can use it. I'll do exercises. I accept rigour, but don't waste my time."

**Voice:** Second person ("you") is common. The author is a guide walking alongside. Warm but not chummy. Precise but not pedantic.

**Structure per chapter:**
- Concrete motivating problem or example up front — not definitions first
- Intuition before formalism. Formalism before generalisation.
- Worked examples (not just worked *problems* — examples that show the thinking)
- Exercises at the end, graded by difficulty if possible

**Characteristic moves:**
- "Before we define X formally, let's see why we'd want it." → a scenario → then the definition
- Running examples that recur across chapters (e.g. a compiler that gets built up over the book)
- "Here's a trap people fall into" sidebars

**Avoid:** dumping all definitions first; chapters that are just theorem-proof-theorem-proof without motivation; exercises that test recall instead of understanding.

**Citation style:** usually light in the main text, with a "Further reading" section per chapter.

---

## 2. Academic (research-level)

**Examples:** *Artificial Intelligence: A Modern Approach* (Russell & Norvig), *Pattern Recognition and Machine Learning* (Bishop), *The Elements of Statistical Learning*.

**Reader contract:** "I'm a researcher or advanced student. Give me the field's structure, the formalisms, the open questions, and point me to the primary literature."

**Voice:** Third person or authorial "we". Measured. Claims are hedged when the literature is unsettled. Opinions are flagged as opinions.

**Structure per chapter:**
- Motivation and historical context
- Formal framework (definitions, notation, assumptions — stated explicitly)
- Core results, with derivations or proof sketches (full proofs in appendices)
- Algorithms in pseudocode when relevant
- Discussion of variants, extensions, limitations
- Bibliographic notes — who did what, when, and where to read more
- Exercises, often research-flavoured

**Characteristic moves:**
- Notation boxes that stay consistent across the book
- "Historical notes" that trace the idea's development
- Explicit discussion of open problems
- Comparison tables between methods

**Avoid:** pretending the field is more settled than it is; omitting the history (it matters for understanding why things are shaped the way they are); handwaving through derivations that matter.

**Citation style:** author-year in text (Russell & Norvig, 2020), full bibliography at the end. Every non-obvious claim cited.

---

## 3. Popular-technical

**Examples:** *Python Crash Course*, the better "For Dummies" books, O'Reilly animal books aimed at practitioners, *The Pragmatic Programmer*.

**Reader contract:** "I want to *do* this thing. Get me productive quickly. Be funny if you can. Don't patronise me."

**Voice:** Conversational, often warm and a bit irreverent. First person and second person freely mixed. Jokes allowed. Self-deprecating author works well.

**Structure per chapter:**
- Short, punchy sections — a reader should be able to stop and start
- Lots of code/examples, immediately runnable
- "Try it yourself" moments
- Sidebars for "gotchas", "pro tips", historical trivia
- Recap at the end

**Characteristic moves:**
- Opening each chapter with a relatable problem ("You've got a CSV file. It's a mess. Here's how to fix it.")
- Progressive disclosure — show the simplest version that works, then layer in sophistication
- Permission to skip — "If you already know X, jump to section 3"
- Acknowledgement that the reader has a life and limited time

**Avoid:** being condescending (the "Dummies" brand is misleading — readers aren't dummies, they're busy); burying the useful bits under too much folksiness; theory without immediate payoff.

**Citation style:** usually minimal in text. A "Resources" or "Further reading" section suffices. Official docs and canonical blog posts get URLs.

---

## 4. Biography

**Examples:** Walter Isaacson's *Einstein*, Ron Chernow's *Hamilton*, Robert Caro's LBJ series.

**Reader contract:** "Show me this person as a human being. Tell me what shaped them, what they did, what it cost them. Don't hagiographise, don't tear down — understand."

**Voice:** Third person, narrative. The author recedes. The subject's own words (letters, diaries, interviews) are quoted liberally. The author's interpretive voice appears in shaping and selection more than in commentary.

**Structure:**
- Usually chronological, but not rigidly — a prologue often drops the reader into a defining moment, then jumps back to origins
- Chapters organised around phases of life, relationships, or projects
- Setting and context matter enormously — the reader needs to feel the world the subject lived in

**Characteristic moves:**
- Scene-setting openings: a specific day, a room, a weather, a gesture
- Long quotations from primary sources (letters, diaries) when the voice is vivid
- Supporting characters treated as full humans, not props
- Interweaving the personal with the work — the biography of an artist is also a biography of the art

**Avoid:** psychoanalysing the subject without evidence; making everything retrospectively meaningful (teleological fallacy); the great-man-of-history frame without acknowledging context and contingency.

**Citation style:** footnotes or endnotes, often detailed. Archive references (box/folder numbers) where relevant. Full bibliography.

**Sensitive points for AI writing:** Living or recently deceased subjects deserve extra care. Claims about private life, motivation, or controversy must be rigorously sourced. When sources disagree about a person's motives or actions, present the disagreement rather than inventing a resolution.

---

## 5. Narrative history

**Examples:** Barbara Tuchman's *The Guns of August*, Erik Larson's *The Devil in the White City*, David McCullough's *1776*.

**Reader contract:** "Take me there. Make me feel the weather, hear the voices, understand why people made the choices they made with what they knew at the time."

**Voice:** Third person narrative, usually past tense. The author is a storyteller first, historian second — but the history has to be right. Scenes are constructed only from what sources actually establish.

**Structure:**
- Usually chronological, with excursions
- Chapters often organised around scenes, days, or turning points rather than thematic categories
- Multiple viewpoint characters followed in parallel

**Characteristic moves:**
- Opening with a specific scene, then pulling back to context
- Dramatic irony — the reader knows what's coming, the characters don't
- Sensory detail drawn from primary sources (what the weather was, what people ate, what they wore)
- Footnotes or endnotes that justify the specificity ("The weather on that morning is from the diary of X")

**Avoid:** inventing scenes, dialogue, or interior thoughts that aren't in the sources. If a detail is speculation, say so ("she must have felt…" is a confession that you don't know). This genre's power depends entirely on the reader's trust that the specificity is earned.

**Citation style:** detailed endnotes, often by page reference. A "Note on sources" essay at the front or back explaining method and archive access.

---

## 6. School textbook (primary / secondary education)

**Examples:** Dutch "Getal & Ruimte", American high-school textbooks, Kindle reading-level primers.

**Reader contract:** "I am a student. I didn't choose to read this. Make it clear, make it reasonable, don't waste my attention."

**Voice:** Clear, direct, age-appropriate. Avoids jargon where possible; defines it clearly where unavoidable. Warm but not forced-fun. The author is a teacher who respects the student.

**Structure per chapter:**
- Learning goals stated up front ("By the end of this chapter you will be able to…")
- Short sections with frequent examples
- Worked examples showing the reasoning, not just the answer
- Exercises graded from easy to hard
- Summary / recap at the end
- Key terms highlighted and defined

**Characteristic moves:**
- Visual aids assumed (diagrams, photos, tables) — describe where they go
- Connections to the student's life where genuine
- Short biographical or historical asides to humanise the material
- Review questions after each section, not just the chapter

**Avoid:** forced "relevance" that feels like a teacher pretending to be cool; dumbing down to the point of imprecision (imprecise teaching causes confusion later); assuming background the student may not have.

**Citation style:** typically minimal in the student text. A teacher's edition or appendix may include sources. Primary sources should still be tracked internally so the book can be defended if questioned.

**Regulatory note:** school textbooks in many countries must align with a curriculum (e.g. Dutch SLO kerndoelen, Common Core in the US). Ask the user up front whether a specific curriculum framework applies and, if yes, map the outline against it.

---

## 7. Memoir / autobiography

**Examples on the shelf:** *The Liars' Club* (Mary Karr), *When Breath Becomes Air* (Paul Kalanithi), *Wild* (Cheryl Strayed), *Angela's Ashes* (Frank McCourt), *H is for Hawk* (Helen Macdonald).

**Reader contract:** "Tell me something true about what it was like to be you. Not flattering you, not flattering me — true. Make me feel the specific weight of your experience."

**Voice:** First person, always. Present or past tense, often shifting between them deliberately. The voice is close to the author's — closer than in any other genre, because the author *is* the subject. A memoir persona is a persona of the author, not a character the author writes.

**Structure:**
- Often structured around a single period or arc rather than a whole life (the "slice of life" memoir). Full-life autobiographies are rarer and usually by figures with public careers.
- Can be chronological, can be thematic, can be non-linear. The structure is a craft choice, not a default.
- Usually chapters are episodes, moments, or themed essays. They don't need to line up perfectly with biographical time.

**Characteristic moves:**
- Opening with a specific scene that carries the whole book's charge
- Freely moving between scene (moment rendered) and reflection (author looking back)
- Acknowledging memory's unreliability — "this is how I remember it" is honest; pretending to perfect recall isn't
- Naming what the author didn't understand at the time but understands now
- Admitting the author's own failures, blindness, cruelty where relevant

**Avoid:** self-glorification (the reader smells it immediately); therapy-in-prose that doesn't reach the reader; the revenge memoir that serves only to settle scores; pretending to perfect memory of dialogue from decades ago.

### Ethical grounds for memoir — unique to this genre

Memoir crosses lines no other genre does: **the author writes about real people who did not choose to be written about.** Spouses, parents, siblings, friends, ex-partners, children. This has both craft and ethical dimensions, and the skill must handle both.

**Before writing any memoir, ask the user these questions explicitly:**

1. **Who appears in this book?** Not "some characters" — real named or recognisable people.
2. **What's the relationship to each?** Family, friends, ex-partners, employers, children.
3. **Are they alive?** Living people have reputation interests and sometimes legal recourse.
4. **What are the stakes for them?** Being in this book could cost them jobs, relationships, peace, safety.
5. **What consent has been sought?** Showing a chapter in advance? A general "I'm writing about this"? None?
6. **Where are the limits the user has chosen?** What will *not* be in this book no matter how relevant?

Record the answers in `project.json` under a `memoir_ethics` block. The skill will not write content that crosses the user's stated limits, and will flag when a scene touches someone the user has indicated is sensitive.

**Absolute constraints:**

- **Minors** — children, including the author's own, should generally be protected. If a minor appears, the default is: compositing / age-shifting / pseudonymisation unless the user has strong reasons otherwise.
- **Abuse victims and other vulnerable people** — never identifiable without explicit consent recorded in project.json.
- **Fabricated scenes presented as memory** — do not. If the user can't remember something specifically, the memoir acknowledges that: "I don't remember what we said that night. I remember the kitchen smelled of coal and the dog barked when the door opened." Specific sensory details the author couldn't possibly remember are invention, not memory.
- **Compound characters** — acceptable if disclosed. The author's note should say "some characters are composites" if that's how the memoir handles multiple real people.

**Recommended practices:**

- Name-change option — the user decides per-person whether they're identified or pseudonymised
- Pre-publication showing — if the user wants to show relevant chapters to people before publication, the skill can track who has seen what
- Author's note — every memoir should have one, covering how memory was used, whether composites or changes were made, and the author's ethical stance

**Citation style:** usually none; memoir doesn't cite sources for personal memory. But if the memoir draws on factual research (dates, historical context, other people's writing), those get Chicago notes like any other non-fiction.

**Research:** memoir still research. Dates, places, public events the author's life touched — these should be verified. The author's own memory can be wrong about public facts.

---

## 8. Self-improvement / popular psychology

**Examples on the shelf:** *Atomic Habits* (James Clear), *The 7 Habits of Highly Effective People* (Stephen Covey), *Thinking, Fast and Slow* (Daniel Kahneman — closer to popular science but reads as self-improvement for many), *Deep Work* (Cal Newport), *Mindset* (Carol Dweck).

**Reader contract:** "I bought this book because I want to change something about my life. Give me something I can actually use, grounded enough that I trust you, practical enough that I can start today."

**Voice:** Conversational and warm, with authority earned through specifics. First person is standard — the author shares their own path, their own struggles, their own experiments. Strong opinions are not only allowed but expected.

**Structure:**
- Short chapters, often 5–10 pages each. A reader should be able to read one chapter per sitting and feel they got something.
- Each chapter usually delivers one idea, one framework, or one technique.
- Heavy use of frameworks, acronyms, and named concepts (the "4 Disciplines of Execution", "Atomic Habits", "Flow"). These give the reader handles.
- Case studies and anecdotes — often from the author's consulting practice or personal life — anchor each concept.
- End-of-chapter summaries or action items are expected, not optional.

**Characteristic moves:**
- Opening each chapter with a story, then extracting the principle
- The "and here's why this matters" bridge between anecdote and idea
- Named frameworks that become memorable: "The Two-Minute Rule", "The 4 Quadrants of Time Management"
- Call-backs across chapters — principle introduced in ch. 2 gets applied in ch. 7
- Permission-giving — "it's OK to be bad at this at first"
- Explicit action items: "try this for seven days and see what happens"

**Avoid:**
- Pop-science citations that crumble under scrutiny (the classic failure mode). If you cite a study, it should replicate. If it's a classic study with replication issues, acknowledge that.
- "Guru voice" — the infallible all-seeing author who never struggled. Readers smell it.
- Over-reliance on anecdotes without evidence
- Generic advice dressed up as insight ("be yourself", "work hard", "dream big")
- The 300-page book that should have been a 20-page article (a genre-endemic problem)

### The replication crisis problem — unique to this genre

Self-improvement leans heavily on psychology research, and much of the famous research from the 2000s-2010s has failed to replicate or been weakened substantially. The skill must handle this explicitly.

**When self-improvement books cite research, check:**
- Is the study recent enough that its replication status is known?
- If it's pre-2015 social psychology, has it been challenged or failed to replicate?
- Are there systematic reviews or meta-analyses that support or weaken the cited finding?
- Is the popular interpretation of the study what the study actually found?

Classics now in trouble include ego depletion, power posing, marshmallow test (replicated but weakened), priming effects, the Stanford prison experiment. If the user wants to cite these, the skill should flag that the research is contested and either (a) cite the current state honestly, or (b) pick a more robust finding.

**Citation style:** usually plain numeric or endnotes — not in-line academic citations that would slow the reader. But citations do exist; the book is not citation-free just because it's popular.

### Structure conventions specific to self-improvement

Self-improvement books have near-standardised structure expectations:

- **Introduction / opening chapter:** the promise. What will change if the reader finishes this book?
- **Framework chapter:** the core framework in one clear chapter, early.
- **Application chapters:** each chapter applies the framework to a life area, a scenario, or a common problem.
- **Integration chapter:** how the pieces fit together, often near the end.
- **"What now" chapter:** concrete action plan for the reader after closing the book.
- **Appendices:** action templates, checklists, further reading.

Not every self-improvement book follows this rigidly, but readers expect something close. Deviate deliberately, not accidentally.

### The didactic structure fit

Self-improvement books almost always benefit from didactic structure (see `didactic-structure.md`). Specifically:

- **Learning objectives** per chapter — always valuable ("by the end of this chapter you will have a framework for X")
- **Exercises** — this genre practically demands them. Reflection prompts, action items, self-assessments.
- **Action visibility** — the reader should know what to *do* after each chapter, not just what to think about.
- **Minimum topics** list matters — self-improvement books often try to cover too much. Setting minimums keeps the book from diffusing.

---

## 9. Essay collection

**Examples on the shelf:** *Slouching Towards Bethlehem* (Joan Didion), *Feel Free* (Zadie Smith), *Consider the Lobster* (David Foster Wallace), *Trick Mirror* (Jia Tolentino), *The White Album* (Joan Didion).

**Reader contract:** "I'm not reading cover to cover. Each essay should reward the fifteen minutes I give it, and together they should amount to something bigger than themselves — a sensibility, a way of seeing."

**Voice:** First person, literary. The author is present in every essay, not just as narrator but as mind. The reader is reading *for* the voice as much as for the subjects. A strong essay collection is as much a portrait of the essayist as the subjects treated.

**Structure:**
- Each essay is self-contained — standalone in topic, resolution, and completeness
- No sequential throughline — the collection is a constellation, not a line
- Essays may be grouped thematically (Part I: on reading; Part II: on cities; Part III: on people) but within a group, order doesn't imply dependency
- Length varies substantially: some essays 2 pages, some 40
- Often previously published individually — the book is the aggregation plus new material

**Characteristic moves:**
- Each essay has its own opening hook; there's no book-wide opening the reader is expected to follow from
- Recurring preoccupations across essays — a writer who keeps returning to loss, or California, or consciousness — that give the collection its shape
- Essays that directly respond to or build on each other can be clustered, but not required
- An introductory essay that does the work of a preface — not "welcome to the book" but an essay that happens to be first

**Avoid:**
- Forcing a throughline that isn't there (the reader knows when you're retrofitting)
- Essays that only make sense if you've read the previous one
- Weak filler essays that drag down the strong ones — better to have 10 strong essays than 18 with 8 weak ones
- Pretending standalone pieces are chapters of a coherent argument

### Structure-level decisions unique to essay collections

The outline for an essay collection looks different from a linear book's outline:

- **Per-essay** (not per-chapter): opening, stance, form (is this a personal essay, a review, a reported piece, a meditation?), length range
- **Thematic clusters**: which essays belong together, and why the groups sit in the order they sit
- **Opening essay choice**: essays are not chapters 1-15; one essay is chosen to open because it signals the collection's character
- **Closing essay choice**: an essay that lands the overall collection, often quieter or more reflective

The skill should handle this by treating each essay as a mini-book (with its own hook, goal, structure) while coordinating them at the collection level (theme, voice consistency, order).

**Citation style:** varies. Literary essays often use no citations, quoting informally in prose. Reviews and reported essays may use light citation. The collection should commit to one style and stick with it.

**Length target:** essay collections typically run 200–400 pages. Collections shorter than 150 pages can feel like a chapbook; longer than 400 tests the reader's patience for a form that asks the reader to re-enter a new mind with each essay.

---

## Choosing a profile — rules of thumb

| If the reader is... | Profile |
|---|---|
| A student working through exercises | textbook or school textbook |
| A researcher / grad student | academic |
| A working professional who wants to ship | popular-technical |
| A curious adult who wants to know a person | biography |
| A curious adult who wants to know an era | narrative history |
| A reader wanting to know what it was like to be the author | memoir |
| A reader wanting to change something about their life | self-improvement |
| A reader who wants to spend time inside a sensibility | essay collection |

If the user's answer straddles two profiles, say so and propose a hybrid (e.g. "textbook with biographical sections on key figures").
