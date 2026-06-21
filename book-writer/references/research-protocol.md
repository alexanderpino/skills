# Research protocol

Research is the phase where the book gets its credibility. A beautifully written chapter built on unverified claims is worse than no chapter — it launders error into something that *looks* authoritative. This file describes how to do research that earns the reader's trust.

## The guiding principle

**Write nothing you cannot trace.** Every factual claim in the finished book must trace back to an entry in `sources.json`. If at the end of research a claim has no source, it either needs one or it doesn't belong in the book.

---

## Step 1 — Decompose the topic into research questions

Before searching, sit down (figuratively) and list the questions the book needs to answer. These become the structure of the research.

Examples:

**Biography of Ada Lovelace:**
- What was her childhood and education? (Byron's daughter, mother's role, tutors)
- How did she meet Babbage and what was their working relationship?
- What exactly did the Notes on the Analytical Engine contain that was original?
- What was her health history and cause of death?
- How did her reputation evolve posthumously?
- What is currently contested in her scholarship?

**Textbook on reinforcement learning:**
- What problem does RL solve that supervised learning doesn't?
- Historical development: Bellman, Sutton & Barto, DQN, AlphaGo
- MDP formalism — the canonical statement
- Value-based methods — Q-learning, SARSA, DQN
- Policy-gradient methods — REINFORCE, actor-critic, PPO
- Model-based RL
- Exploration vs exploitation — the bandit theory that grounds it
- Current open problems and frontier research

Aim for 8–20 questions for a standard book. Save them as the top of `notes/_research-plan.md` so progress can be tracked.

---

## Step 2 — Search each question

For each research question, use `web_search` with focused queries, then `web_fetch` on the most promising results to get full content. Respect the search guidelines already in your system prompt — short queries, multiple angles.

### Source reliability tiers

Not all sources are equal. Tag each source in `sources.json` with one of these:

| Tier | What it means | Examples |
|---|---|---|
| `primary` | The original record | Letters, diaries, archival documents, original papers, legislation, interviews you conduct |
| `peer-reviewed` | Scholarly literature vetted by the field | Journal articles, academic monographs, conference proceedings |
| `reference` | Curated scholarly reference works | Stanford Encyclopedia of Philosophy, Oxford Dictionary of National Biography, established field handbooks |
| `journalistic` | Reputable journalism | NYT, The Guardian, The Economist, FT, BBC, NRC, major trade publications |
| `popular` | Popular nonfiction, established blogs, expert commentary | Trade books, well-regarded technical blogs, podcasts with named experts |
| `unverified` | Anything else — Wikipedia, forums, anonymous posts | Use as pointers to better sources, not as sources themselves |

**Wikipedia rule:** Wikipedia is excellent for orientation and for finding primary and secondary sources via its footnotes. It is not itself a citation. When a claim comes from Wikipedia, follow its footnote to the real source and cite *that*.

### Search strategy per profile

- **Academic / textbook:** start with review articles and survey papers, then drill into primary research. Google Scholar-style queries. Look at textbooks in the field to see how they structure the same material.
- **Biography:** look for established biographies first (they're gold mines of primary-source citations), then seek the primary sources directly — letters, diaries, archives. Check whether papers have been digitised.
- **Narrative history:** primary sources for texture (weather, newspapers of the day, letters), secondary sources for analysis and interpretation.
- **Popular-technical:** official documentation, specifications (RFCs, language standards), source code when relevant, expert blog posts by named practitioners.
- **School textbook:** published curriculum standards, established textbooks in the same subject for comparison, primary sources to verify any historical or factual claims made in those textbooks.

---

## Step 3 — Double-check every claim

This is the step most easily skipped and most dangerous to skip.

**Rule:** a factual claim worth putting in the book is worth verifying with a second, independent source.

"Independent" means: not the same article rehosted, not the same author, not citing only the first source. Two newspapers reporting from the same wire story count as one source, not two.

**Procedure:**

1. When you find a claim worth using, do a second search specifically to verify it — often with different keywords.
2. Record both sources in `sources.json` and link them via `verified_by`.
3. If the second source contradicts the first, go to Step 4 (conflicts).
4. If you cannot find a second independent source, mark the claim `single-source: true` in the relevant note and flag it at the end of the research phase for the user's attention.

**When a single source is acceptable:**
- Original research papers for their own results (the paper itself *is* the primary source)
- Archival primary sources for what they literally contain
- Direct interviews
- Official records (government statistics, court rulings) from the issuing authority

In these cases, the source is the evidence; no corroboration is needed to establish that the source *says* what it says. But claims *beyond* what the source directly supports still need corroboration.

---

## Step 4 — Handle conflicts honestly

When sources disagree, the book does not pick a side in silence.

**Procedure:**

1. Record both (or all) positions in the relevant note, with `CONFLICT:` marker.
2. In the note, record:
   - What each source claims
   - The reliability tier of each
   - Whether one is primary and others secondary
   - Whether there's a consensus in the field (check a scholarly reference source)
3. In the chapter, handle the conflict according to the genre:
   - **Academic:** discuss the disagreement, cite both, state your interpretation (if any) as interpretation
   - **Narrative history / biography:** present the best-supported version, but footnote or endnote the alternative
   - **Popular-technical / textbook:** usually go with consensus; if the field itself is unsettled, say so briefly
   - **School textbook:** go with curriculum / consensus; note unsettled status only if age-appropriate

**Never** silently average conflicting numbers, pick the more dramatic version, or ignore the one you don't like.

---

## Step 5 — Synthesise into notes

Raw search results are not research. Notes in your own words, with source references, are research.

For each research question, produce `notes/<question-slug>.md`:

```markdown
# Question: How did Lovelace and Babbage meet?

## Summary
Ada met Babbage at a party hosted by Mary Somerville in June 1833,
when Ada was 17. [src:3][src:7] Babbage showed her a working portion
of the Difference Engine, and her mathematical interest was immediate.
[src:3]

## Key facts
- Date: 5 June 1833 [src:3] — some secondary sources say early 1833
  without specifying [src:12]. **Primary source (Somerville's diary)
  gives 5 June.** [src:3]
- Lovelace was 17, Babbage was 41. [src:3][src:7]
- They began corresponding within weeks. [src:7]

## CONFLICT: nature of early relationship
Doron Swade [src:4] characterises their early relationship as primarily
intellectual mentorship. Betty Alexandra Toole [src:9] reads it as more
emotionally intimate based on letter tone. Swade is more rigorous with
sources; Toole reads more between the lines. → Go with Swade's
framing, footnote Toole's alternative reading.

## Open questions
- Exact content of their first conversation — not recorded directly.
  Biographers reconstruct from later letters.

## Sources drawn on
[src:3] Somerville, Personal Recollections, 1873 (primary)
[src:4] Swade, The Difference Engine, 2001 (peer-reviewed)
[src:7] Toole, Ada, The Enchantress of Numbers, 1992 (popular)
[src:9] ...
```

These notes are what the writing phase draws from. Good notes make the writing phase fast; bad notes make it painful.

---

## Progress reporting

Research takes a long time. The user should not be left in silence.

After each research question is complete (or every 15–30 minutes on long questions), give a short update:

> "Done with question 3 of 8 (childhood and education). Found 12 sources, 2 single-source claims flagged, 1 conflict (disputed date of first tutor). Moving to question 4."

At the end of the research phase, produce a summary for the user:

- Total sources, broken down by reliability tier
- Research questions covered vs. any gaps
- List of single-source claims
- List of conflicts and how you propose to handle each
- Anything you could not find (so the user knows the limits)

Then explicitly ask: "Do you want me to dig deeper anywhere before we move to the outline?"

---

## What not to do

- **Don't fabricate sources.** Under no circumstances invent a citation that doesn't exist. If you recall a source but can't find it, search until you find it — and if you can't find it, don't cite it.
- **Don't use "general knowledge" as a source.** Either it's in `sources.json` or it's not in the book.
- **Don't trust your training data for specific dates, numbers, or quotes.** Verify with a current search.
- **Don't skip the verification step to save time.** The verification step is where the book stops being AI slop and starts being trustworthy.
- **Don't silently drop claims that turn out to be wrong.** Update your notes to reflect what the sources actually say.
