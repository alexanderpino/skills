# Beta feedback

A book written in isolation is half-finished. A book tested against real readers before publication is the other half. The beta phase sits between a complete first draft and final assembly — it's where the manuscript meets the reader's experience for the first time.

This file covers how to structure beta reading, what feedback to collect, how to process it, and how to distinguish useful feedback from noise.

Read this file at the end of Phase 4 (Writing), when the first complete draft of the manuscript exists.

---

## When beta feedback makes sense

Almost always, for non-fiction. Always for fiction. Skip only when:

- The project is a **demo or prototype** — the purpose is not publication, so readers aren't needed yet
- The book is **internal documentation** with a fixed single audience who will see it in its final form anyway
- The user explicitly **declines** after being informed — some users are writing for themselves and know it

When in doubt, do it. Beta readers find things the author cannot find.

Demo scope: skip beta phase entirely unless the user asks for it.
First-pass scope: a lightweight beta — 2-3 readers, one round.
Production scope: full beta — 5-10 readers, possibly multiple rounds with revision between.

---

## Why authors miss things readers catch

The author has been inside the book's logic for weeks or months. They know what they meant. They fill in gaps subconsciously when re-reading. They remember which chapter introduced which concept, even when the prose assumes a reader who doesn't.

Beta readers don't have that background. They experience the book as a reader experiences it — with the gaps, jumps, and unstated assumptions visible.

Typical things betas catch that authors miss:

- **Clarity gaps** — a concept the author thought they'd explained but only gestured at
- **Prerequisite ordering** — assuming knowledge that comes later in the book
- **Pacing issues** — "I got bored in chapter 6" or "chapter 10 felt rushed"
- **Emotional resonance failures** — a scene the author thought would land that doesn't
- **Character/persona inconsistencies** (fiction) — "this character wouldn't say that"
- **Tonal drift** — chapters in voices that feel subtly different
- **The "I skimmed this" signal** — sections readers rush through, indicating they're not pulling weight

These are not things a self-critique pass catches reliably, because self-critique is still done from inside the author's head.

---

## Choosing beta readers

Two to ten readers is the useful range. Fewer than two and you're collecting one person's idiosyncrasies as if they're feedback. More than ten and you drown in contradictory input.

**Mix types deliberately:**

- **Target readers** — people who match the intended audience. Most of the feedback weight goes here.
- **Domain experts** — people who know the subject and can catch errors the author missed. Especially important for technical and academic books.
- **Unrelated readers** — people outside the target audience who can flag clarity issues a target reader would paper over. "This should be readable by a smart generalist" is tested here.
- **Craft-attentive readers** — people who read as writers do, noticing prose patterns, structure, voice.

For fiction, add:
- **Genre readers** — people who read a lot of the specific genre and can spot convention issues (a thriller reader notices when a thriller doesn't pace like one)
- **Sensitivity readers** (for certain content) — people with relevant lived experience for material involving their communities, identities, or histories

For memoir specifically, add:
- **People named in the book** (where consented) — they should see their appearances before the book is locked. This isn't approval; it's honesty.

**Don't pick readers who will only say "this is great."** Affirmation is not feedback. A useful beta reader is someone who wants the book to succeed and is willing to tell the author what's between the current draft and success.

---

## What to ask them

The worst beta-reader brief is "read it and let me know what you think." The reader doesn't know what you want, can't prioritise, and will default to line-editing when you wanted structural feedback.

A good brief:

```markdown
# Beta reader brief — [Book Title]

## What this book is
[One paragraph: what the book is, who it's for, what it's trying to do.]

## Where we are
[First complete draft. Fact-checking done / not yet. Consistency sweep done / not yet.]

## What I'd like from you

Please read as a reader — not as an editor. I'll handle line-level fixes separately. What I need from you is the reader's experience.

Specifically, as you read, please note:

1. **Where you got confused.** Not "this was hard" but "I stopped understanding here." Page reference or chapter is enough.
2. **Where you got bored.** Where did you skim? Where did you want to put the book down?
3. **Where you were surprised.** Positively or negatively — moments that landed, moments that jarred.
4. **What you expected that didn't happen.** Questions you had that the book didn't answer. Promises you felt were made early and weren't kept.
5. **What sections felt most useful/memorable.** So I know what to preserve under revision.

You don't need to fix anything. Don't worry about typos or phrasing. Tell me about your experience.

## Timeline
[When feedback is wanted. Realistic — beta readers need weeks, not days, for a full-length book.]

## Format
[Whatever works for them — marginalia, email, a call, a shared doc with comments.]
```

Customise per reader type. A domain expert gets a question list about specific technical claims. A target reader gets the above. A sensitivity reader gets a brief specific to the content in question.

---

## Running the beta phase

### Step 1 — Prepare the manuscript for readers

The manuscript sent to betas is not the final artefact. It should be:

- **Clearly marked as a draft** — every page, so readers don't share it as if it's published
- **Numbered for reference** — page numbers, line numbers, or chapter-and-section markers so feedback can be located later
- **Without the apparatus that hasn't been built yet** — no incomplete index, no placeholder bibliography. An "apparatus to come" note is enough.
- **Readable in whatever format the reader prefers** — PDF is standard; some readers want print; some want e-reader files

Save a copy of the beta version in `<book>/beta-round-<N>/manuscript.pdf` (or equivalent). Later feedback will reference this specific version.

### Step 2 — Send with context

When distributing to readers, include:

- The brief (above)
- A reply-by date
- A clear way to reach the author with questions
- An acknowledgement that the reader's time is a gift — whether money, gift cards, or a credit in the book is offered, make the thank-you concrete

### Step 3 — Collect feedback without reacting

As feedback comes in, **do not start revising yet**. Collect everything first. It's tempting to fix the first thing a reader mentions, but:

- Early feedback biases later decisions
- Contradictory feedback (reader A loved chapter 5, reader B found it slow) resolves more clearly when you have the whole set
- Reactive revision mid-beta wastes work if a later reader would have changed your mind anyway

Store each reader's feedback in `<book>/beta-round-<N>/<reader-id>/feedback.md` — text, images of marginalia, notes from calls, whatever form it came in.

### Step 4 — Synthesise the feedback

Once all feedback is in, process it. Produce `<book>/beta-round-<N>/synthesis.md`:

```markdown
# Beta feedback synthesis — round 1

**Readers:** [list]
**Feedback collected:** [dates]

## Convergent feedback (multiple readers agreed)

### Opening works
Four of five readers specifically praised the opening anecdote in chapter 1. Preserve.

### Chapter 6 pacing
Three readers noted chapter 6 felt slow. Two specifically stopped reading mid-chapter and came back. Structural issue.

### Normal mapping explanation
Two readers independently said they lost the thread in section 7.3. Rewrite.

## Divergent feedback (readers disagreed)

### Humour level
Two readers wanted more humour; one wanted less. Author's call — my instinct is current level is right, with minor tightening of two paragraphs that felt forced.

## Single-reader flags worth considering

### Reader 3 on chapter 11
Reader 3 has domain expertise in PBR. They flagged three technical claims as oversimplified. Worth revisiting even though only one reader raised it.

## Feedback to respectfully decline

### Reader 2 on framing
Reader 2 suggested reframing the whole book around a different audience. Appreciated, but it's a different book than the one planned. Not acting on this.

## Revision plan

Based on above:
1. Chapter 6: substantial restructure. See separate notes.
2. Section 7.3: rewrite with stronger analogy (specific plan in chapter revision doc).
3. Chapter 11: revisit technical claims flagged by Reader 3, verify against primary sources.
4. Minor cleanups across chapters 3, 8, 12.

Estimated revision time: [estimate]
```

The synthesis is where the author's judgement does real work. Not every piece of feedback is equal; not every piece acted on; not every piece ignored. Sorting happens here.

### Step 5 — Revise

Work through the revision plan. For each item:

- Note what the feedback was
- Note what was changed
- Note what was not changed and why (so later review has the reasoning)

Save a revision log at `<book>/beta-round-<N>/revision-log.md`.

### Step 6 — Decide on a second round

Some books need only one beta round. Others need more, especially when:

- The first round's feedback triggered structural changes (the revised manuscript is substantially different)
- First-round readers flagged the same area and the author wants to confirm the fix landed
- New sections were added that no one has read yet

A second round, if needed, should use at least some **new readers** — because first-round readers already know the book and can't give fresh-reader feedback anymore. They can give "did this issue get fixed?" feedback, which is also valuable but different.

Three rounds is usually the maximum before diminishing returns. If the third round still surfaces substantial issues, the book may not be ready; consider whether the premise itself needs reconsideration.

---

## Processing feedback: the craft of deciding what's signal

Beta feedback is noisy. Readers misread, disagree, project their own preferences. The art of beta is distinguishing signal from noise.

### Weight convergence

If three readers independently flag the same passage, it's a problem. You can argue about what kind of problem, but something is there. Trust convergence more than any single strong opinion.

### Weight reader type

Feedback from a target reader ("I'm who this book is for, and I was confused here") weighs more than feedback from an unrelated reader on the same point. The target reader's confusion is the bug; the unrelated reader's confusion may be outside the book's responsibility.

Domain experts weigh heavily on factual and technical claims and lightly on reader-experience claims. They know if the physics is right; they may not know if a general reader will follow.

### Distrust uniform praise

If every reader loved every chapter, one of two things is true: the book is a masterpiece (rare), or the readers are being polite. The second is much more common than the first. If you're not getting any critical feedback, you've picked the wrong readers.

### Distinguish "this didn't work for me" from "this doesn't work"

A reader's "I didn't like chapter 3" might mean:
- The chapter has craft problems
- The chapter isn't for readers like them (but is for others)
- The chapter triggered something personal unrelated to the chapter

The author's job is to tell which. Not every "I didn't like" is a problem to fix. Not every "I loved" is a section to preserve untouched.

### Notice what they didn't say

Sometimes the gap is the signal. A reader who reported on chapters 1–5 and 7–10 but never mentioned chapter 6 probably skimmed chapter 6. The absence of reaction is a reaction.

### Act on the fixable

Some feedback is about the book fundamentally. "The premise doesn't grab me" is useful information but often not actionable without restructuring the whole work. Other feedback is about specific paragraphs or sections — fixable with hours of work. When resources are limited, the fixable wins.

Record the non-acted-on feedback in the synthesis so it doesn't disappear, but don't let it paralyse.

---

## When feedback contradicts the author's intent

Sometimes a reader flags something that the author chose deliberately. A deliberately difficult passage. A deliberately slow chapter. A deliberately unresolved ending.

The question isn't "was my choice right?" but "was the choice legible?"

If readers experienced "this is slow" and the author intended "this needs to slow down for contemplation", the author might be right that slowness was needed — and wrong that it reads as contemplation rather than drag. The craft problem is signalling the deliberateness.

Options:
- Signal more clearly in the text what the deliberate choice is doing
- Trust that some readers will miss it; that's OK
- Reconsider whether the deliberate choice was actually worth the cost

All three are sometimes right. None is always right.

---

## The user-in-the-loop version

For book-writer-skill runs, the "author" is the user, and the skill supports the beta process rather than replacing it. The skill can:

- Help write the beta reader brief
- Track readers and feedback deadlines
- Collect feedback as the user forwards it (paste emails, upload docs)
- Produce the synthesis
- Propose a revision plan based on the synthesis
- Execute revisions the user approves
- Maintain the revision log

What the skill does not do alone:

- Choose beta readers
- Send the manuscript out
- Make final decisions on contradictory feedback (that's the author's call)
- Override the user's decision to decline specific feedback

The skill can do the full workflow alone if the user is simulating a beta phase (running their own thought experiment about what different readers would say), but this is weaker than real readers. Note honestly when this is simulation vs real beta.

---

## Beta artefacts on disk

```
<book>/
├── beta-round-1/
│   ├── manuscript.pdf          # the version sent to readers
│   ├── brief.md                # the reader brief
│   ├── readers.md              # who read, when, what type of reader
│   ├── reader-1/
│   │   ├── feedback.md
│   │   └── marginalia.pdf
│   ├── reader-2/
│   │   └── feedback.md
│   ├── ...
│   ├── synthesis.md            # convergent / divergent / ignored
│   └── revision-log.md         # what changed, what didn't, why
├── beta-round-2/
│   └── ...
```

If the book has no beta rounds (demo scope or user declined), this directory is absent.

---

## After the beta phase

A manuscript that has been through beta feedback and revision is called **beta-tested**. Each chapter's frontmatter updates:

```yaml
status: beta-revised
beta_rounds: 1
last_revised: 2026-04-25
```

From here, fact-check (Phase 4.6) can run on the revised manuscript, and then Assembly (Phase 5) can produce the final deliverable.

It's worth noting that fact-check sometimes needs to run after beta revision because beta sometimes introduces new content or reframed claims that need their own verification. Order of Phase 4.6 (fact-check) and Phase 4.5 (beta) should usually be: beta first, fact-check after. The fact-check is the last thing before assembly.
