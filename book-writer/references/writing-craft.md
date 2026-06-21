# Writing craft

This is the phase where a book becomes a book or becomes a dense Wikipedia article. The difference is craft. This file is about craft — specifically about the moves that make non-fiction feel alive, precise, and honest.

Read this at the start of Phase 4, and keep `style-guide.md` and the current chapter's outline entry open alongside it.

---

## The core rule

**Do not write a sentence that only states a fact.**

This sounds extreme. It isn't. Here's what it means:

Bad: "Ada Lovelace was born on 10 December 1815 in London."

Better: "On the night Ada Lovelace was born — 10 December 1815, in a house on Piccadilly Terrace — her father, Byron, was already planning the separation that would send him out of England forever."

The first sentence is true. The second is also true, and it does three things the first doesn't: it places the reader in a specific time and space, it introduces a tension (the marriage about to shatter), and it plants a thread that matters (her father's absence will shape everything).

Not every sentence can do this much work. But every sentence should *try* to do something beyond recitation. Ask of each paragraph: if I cut this, would the reader miss anything besides the information? If not, rewrite it so they would.

---

## Opening a chapter

The opening hook from the outline isn't decoration — it's the chapter's first job. Three patterns that work:

**1. Drop into a scene.**
A specific moment — day, place, weather, person doing something concrete. Pull back from the scene into the chapter's argument.

> "At 8:42 on the morning of 10 July 1962, a technician at the Andover Earth Station in Maine watched a screen fill with snow and resolve into the face of a French announcer. The first live transatlantic television image had just crossed the ocean via a satellite the size of a beach ball. Telstar was in orbit. And a new kind of infrastructure — the one you're using to read this — had its first breath."

**2. Pose a question the reader didn't know they wanted answered.**

> "Why do neural networks, which have been around since the 1950s, suddenly work now? The honest answer isn't 'we got smarter'. It's that we got patient, we got GPUs, and we accidentally discovered that scale matters more than cleverness. This chapter is about how we found that out."

**3. State a puzzle or tension.**

> "Reinforcement learning has a strange feature: the agent doesn't know what it's supposed to do. It receives rewards, but no one tells it which actions produced them or what the goal actually is. Somehow, that's enough. This chapter is about why."

**Avoid:**
- "In this chapter, we will cover…"
- "First, let's define…"
- Dictionary-opening definitions
- Anything that could be the first line of a Wikipedia article on the topic

---

## Weaving exposition into narrative

Exposition is necessary. The question is where it sits.

**Bad pattern (exposition dump then example):**
> "A Markov Decision Process consists of a set of states S, a set of actions A, a transition function T, and a reward function R. Let's consider an example: a robot in a gridworld..."

**Better pattern (example first, then extract the formalism from it):**
> "Imagine a robot in a 4×4 grid. It can move up, down, left, or right. Some squares give it a reward; one, in the corner, is a trap. At every step, it has to decide where to move next. This is, as written, a Markov Decision Process. The ingredients are all there: the states (which square you're on), the actions (four directions), the rewards (what you get for stepping on each square), and the transitions (what happens when you try to move). Writing it out formally gives us: ..."

The second version does the same teaching work, but it gives the reader something to think *with* before giving them something to memorise.

---

## Handling technical depth without losing the reader

**The ladder principle.** Introduce ideas at one level of abstraction, then climb. Don't drop the reader at the top and hope.

Example, introducing backpropagation:
1. *Intuition*: "Imagine you made a prediction and got it wrong. Which of the network's weights should you blame?"
2. *Concrete example*: "A 2-layer network on a single data point. We'll compute the error and then trace it backward to see which weights contributed how much."
3. *General formula*: [the chain-rule derivation]
4. *Why it matters*: "This is the reason deep networks are trainable at all. Without it, we'd be stuck."

Each rung supports the next. If you skip a rung, readers fall off.

**Hedge honestly.** If the field is unsettled, say so. Readers trust an author who admits uncertainty more than one who fakes confidence.

**Use notation consistently.** When you introduce a symbol, commit to it. If sources in the field disagree (ml notation is famously inconsistent), pick one, state the choice, and stick with it.

**Keep equations embedded in prose.** An equation on its own line is fine; a wall of equations with no connecting prose is a textbook's death.

---

## Code listings — the comment balance

For technical books, code listings carry a portion of the chapter's teaching. Comments inside listings can support that or undermine it. Both happen often.

**Decide at intake what the book teaches and what it assumes.** A book on building an OS for embedded systems engineers assumes C and ARM assembly; a book on machine learning for working data scientists assumes Python; an introductory programming book assumes nothing. The book's audience-knowledge contract determines what comments need to say.

**The principle.** Code comments should explain *what the algorithm does* and *what design choices were made*. They should not explain *how a language feature works* if the audience is presumed to know the language. Two comments that look similar are very different in role:

- `// Bump the generation so old EntityIds become safely dead.` — algorithm intent. Worth keeping; the reader needs to understand the use-after-free defence.
- `// std::atomic so that concurrent first-calls from different threads see a consistent counter.` — language-feature explanation. If the audience knows C++, this is noise; the word `atomic` already says it.

The second kind of comment is where AI-assisted writing accumulates noise. It feels generous to explain things, and the result is code that's harder to read because every line has a paragraph next to it.

**Cardinal sins of code comments.**
- *Repeating in a comment what the prose just said.* The reader has already read the prose. A comment restating it is redundant.
- *Repeating in prose what the comment said.* Same problem in the other direction. Pick one location for each idea.
- *Explaining the language to readers who know it.* If the book's intake says "audience knows C++23", don't explain `std::atomic`, `if constexpr`, parameter packs, or placement-new in code comments. If a feature genuinely warrants explanation, it goes in the prose around the listing, where it can do its job once.
- *Pseudo-prose comments.* "Result: fn(positions[i], velocities[i], ...) for this row." That's not a comment; it's a paraphrase of the line above it. Cut.

**What to keep.**
- Field comments that name a non-obvious role. `std::vector<EntityId> entity_ids;  // parallel-indexed with the columns` — useful, the role isn't obvious from the type.
- Algorithm intent comments. `// Capture the entity about to be swap-moved into our row.` — explains the *why*, which the code alone can't.
- Sentinel and constant comments. `// Sentinel for "no entity"` — the value `0xFFFFFFFF` doesn't speak for itself.
- Section markers in long listings. `// ─── World ──────────` — orientation in a 200-line file.

**What to cut.**
- Comments that explain syntax. `// 'new (dst) C(...)' is placement-new.`
- Comments that summarise the next line. `// Push to the column.` followed by `col->push_back(...)`.
- Boilerplate framework explanation. `// Google Test calls SetUp before each TEST_F.`
- Comments that hedge or apologise. `// This works but a real engine would do X.` Put hedges in prose, not in code.

**A test you can run during self-critique.** Read the listing without its comments. Is the *what* still clear? If yes, keep all the comments — they're additive, not load-bearing. Read the listing without its surrounding prose, with only the comments. Is the *why* still clear? If not, the comments are missing the load they should carry, or the prose is doing it (in which case some can move into the comments). The two together — listing and surrounding prose — should leave no critical question unanswered, with each idea explained once, in the place where it naturally lives.

**A note on density.** A rough heuristic for technical books: somewhere between one comment per five to ten lines of code is normal. Less than one per fifteen lines and the listing is probably under-explained for its audience; more than one per three lines and the listing is probably over-commented. These are guides, not rules; some listings legitimately need more, some less. The ratio is downstream of the principle, not the principle itself.

---

## Using examples and cases

A non-fiction book lives or dies by its examples. The outline committed you to an opening hook per chapter — don't stop there. Within each chapter, every major idea wants an example.

**Criteria for a good example:**
- **Specific.** "A social network" is not an example. "Twitter in 2010, when the follow graph was still public" is an example.
- **Concrete enough to picture.** The reader should be able to imagine it without effort.
- **Does the work of the concept.** If you can swap the example for another and the point still lands, the example isn't teaching — it's decoration.
- **Honest.** Don't invent tidy examples. Real cases have mess; acknowledge it.

**Running examples** — in textbooks and technical books, a recurring example (the same system built up across chapters) is extraordinarily effective. The reader builds intuition cumulatively. Plan it in the outline phase.

---

## Pacing within a chapter

A chapter is not a uniform slab. It has rhythm.

- **Open with pace** — get the reader in. First page matters more than the rest.
- **Slow down for the hard part** — when you reach the chapter's real intellectual work, give it room. Worked examples. Small examples before big ones. Multiple angles on the same idea.
- **Breathe after effort** — after a dense stretch, a lighter passage. A historical anecdote, a reflection, a story.
- **End on something that lands** — not a summary, ideally. A question, an implication, a thread into the next chapter.

If a chapter is all one texture — all dense, all breezy, all abstract — it's tiring in the same way a meal with no contrast is tiring.

---

## Handling quotations

Quotes from primary sources are gold. Overquoting is lead.

**Rules:**
- Short quotes (under a sentence) can sit inline, in quotation marks, with a source reference.
- Block quotes (indented) are for passages of two or more sentences where the voice matters.
- Never quote to fill space. Every quote earns its presence.
- In biographies and narrative history, quotes from letters and diaries give the subject their own voice — use them where vivid, paraphrase where merely informative.
- Always cite. `[src:N]` inline; the assembly phase converts to the final style.

**Copyright:** keep quotes short. For any source that is still in copyright, the rule "fewer than 15 words" is a safe upper bound for a single quote, and use only one quote from any given source unless it's clearly in the public domain. Paraphrase the rest.

---

## Citations inline

During writing, use the placeholder form `[src:N]` where N is the source ID in `sources.json`. Examples:

> The Notes were published in *Taylor's Scientific Memoirs* in August 1843 [src:3], and Ada's additions ran to roughly three times the length of the original paper [src:3][src:7].

> "I am more than ever now the bride of science" [src:3] — she wrote to her mother the same month.

The assembly phase walks through every `[src:N]` and converts it to the user's chosen citation style (footnote, endnote, parenthetical). Don't try to format final citations in the draft — it's wasted work.

---

## Self-critique before saving a chapter

After you finish drafting, before you save, read the chapter with these questions:

1. **Opening.** Does the first paragraph give the reader something concrete? If it opens with "This chapter will…" — rewrite.
2. **Facts without narrative.** Any paragraph that's just a list of facts? Find a case, a moment, or an example to carry them.
3. **Uncited claims.** Any factual claim without a `[src:N]`? Add the source or cut the claim. No exceptions.
4. **The skim test.** Read fast, like a tired reader. Which paragraphs did you skim? Those are either cut-candidates or rewrite-candidates.
5. **Learning goal.** Does this chapter deliver on the learning goal from the outline? Could a reader, after this chapter, do what the outline promised?
6. **Voice.** Is the voice consistent with `style-guide.md`? Any slippage into the other genre profile?
7. **Handoff.** Does the chapter end in a way that pulls the reader to the next one?
8. **Length.** Within 20% of the outlined estimate? If way over, something's diffuse. If way under, something's missing.

Do a revision pass addressing what the critique surfaces. Then save.

---

## Chapter file format

Each chapter is a markdown file at `chapters/NN-slug.md`:

```markdown
---
chapter: 3
title: The Year in Which the Machine Learned
status: draft
word_count: 4213
sources_used: [3, 7, 12, 14, 18, 23]
outline_ref: ch3
---

# Chapter 3 — The Year in Which the Machine Learned

[chapter body in markdown, with [src:N] citations]
```

The frontmatter is read by the assembly phase. `status` moves from `draft` → `reviewed` (if user reviewed) → `final` (after assembly's consistency pass).

---

## Pitfalls to avoid

- **The encyclopedia voice.** "X is a Y that does Z. It was developed by P in 19NN." If you catch yourself writing this way, stop. Find the story, the tension, or the example.
- **Over-hedging.** "It could be argued that some have suggested…" — either say it or don't. Hedging is for genuine uncertainty, not for cowardice.
- **Dry lists where prose would do.** A bulleted list has its place; a chapter full of them is a PowerPoint, not a book.
- **"Interesting" as a claim.** Never call something interesting. Show it, and let the reader feel it.
- **Forcing "relatable" examples that aren't.** A forced analogy to pizza or dating is worse than no analogy.
- **Summary sections that restate what you just said.** A recap after a hard section is fine. A recap after every section is tedious.
- **Losing the narrator's honesty.** If you're not sure, say so. If the field is contested, say so. The reader's trust is the book's real currency.
