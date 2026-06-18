# Fact-check

Fact-checking a book is not the same work as sourcing it while writing it. During writing, the author (or the skill) verifies each claim as it's introduced — that's Phase 2 research plus Phase 4's inline citation discipline. But over the months (or hours) a book takes, errors drift in. A number gets mistyped in one chapter and correctly cited in another. A source the user trusted turns out to have been retracted. A paraphrase shades into inaccuracy. A claim that seemed sourced traces back to nothing solid when checked from zero.

This file covers the fact-check pass: a manuscript-wide verification sweep done by a reader who approaches every claim as if they don't already believe it.

Read this file when the draft manuscript is complete and Phase 5 (Assembly) is about to begin — or when the user asks for a fact-check pass after the book is essentially written.

---

## When to do a fact-check pass

Not every book needs a full fact-check. Roughly:

- **Academic, textbook, biography, narrative history** — always. These books' reputations rest on their accuracy.
- **Popular-technical** — yes, for technical claims; maybe not for every anecdote.
- **Self-improvement** — especially for research citations (replication-crisis territory).
- **Memoir** — the internal emotional truth isn't fact-checkable, but any factual claims (dates, places, public events, claims about others) should be verified.
- **Essay collection** — per essay, as rigorous as the essay's register requires.
- **Fiction** — only for the real-world elements (historical fiction, sci-fi with real science, anything touching real people or events).

For a book that definitely needs a fact-check: this is a real pass, not a checkbox. It takes hours for a modest book and days for a big one.

---

## The mindset for fact-checking

The fact-check pass is not a re-read. It's an **adversarial re-read**.

The author (or skill) assumes, for the duration of this pass, that every claim might be wrong. Every number, every date, every "X said Y", every "studies show", every "the first person to". Each gets treated as a claim that must be defensible right now, from the sources available, without leaning on "I remember reading this somewhere."

This is uncomfortable. That's why it's valuable — the discomfort catches errors.

The fact-checker's default question: **"What would I need to believe this?"**

---

## What gets checked

### Definitely check

- **Numbers**: dates, statistics, measurements, counts, ages, years, percentages, dollar amounts. These are the easiest to get wrong and the easiest to verify.
- **Proper nouns**: names of people, places, organisations, events, titles. Spelling, diacritics, accent marks, honorifics.
- **Direct quotes**: word-for-word against the source. Near-perfect memory is unreliable; quotes drift over time and paraphrases sneak into quotation marks.
- **Attributions**: "Einstein said X." Did he? Where? When? (Einstein in particular is a magnet for misattributions.)
- **Causal claims**: "X caused Y" — often weaker than the prose makes them sound.
- **First/only claims**: "the first person to", "the only country that", "never before". These are almost always wrong when strongly stated.
- **Research citations**: especially for self-improvement and popular science. Has the study replicated? Is the popular interpretation what the study actually found?
- **Historical specificity**: weather on a specific day, what someone wore, what was said in a room — for narrative non-fiction, every sensory detail needs a source.
- **Technical claims**: API behaviours, specification details, physical constants, procedures. Technical claims date quickly; verify against current sources.

### Also check

- **Source status**: a URL that worked during research may now 404. A paper may have been retracted. A website may have been replaced with different content.
- **Currency**: facts that were true at research time but may have changed. Living people's roles, current laws, current prices, "the most recent X". These claims decay over time.
- **Internal consistency**: a number in chapter 3 agreeing with the same number in chapter 8. Already covered by the consistency sweep, but fact-check finds the case where both instances are wrong because they were copied from the same flawed source.
- **Source-to-claim alignment**: the citation points to a source that actually supports the specific claim, not just the general topic. This is the most common subtle failure — the source exists and is reputable, but doesn't actually say what the sentence claims it says.

### Don't exhaust on

- **Opinions and arguments**: "I believe this is important" isn't fact-checkable, and shouldn't be.
- **Hedged statements**: if the text says "some researchers argue", the fact-check confirms that some researchers did argue that, not that they were right.
- **Interpretations**: the author's reading of a novel, a person, a period. These are defended by argument, not verified by fact-check.
- **Known-contested claims**: where the book already surfaces the conflict, the fact-check confirms both sides were stated accurately, not which side is "true."

---

## The procedure

### Step 1 — Build the claim list

Walk the entire manuscript. For each factual claim that meets the "definitely check" criteria above, record it in `fact-check.md`:

```markdown
# Fact-check worksheet

## Chapter 1

- [ ] Claim: "HLSL was first released with Direct3D 9 in 2002"
  - Source in sources.json: [src:1], [src:3]
  - Verified: ___
  - Notes: ___

- [ ] Claim: "HLSL and Cg were 'considered identical, only marketed differently' in early versions"
  - Source in sources.json: [src:3]
  - Verified: ___
  - Notes: Direct quote from Wikipedia — trace to the fusionindustries.com FAQ source it cites

- [ ] Claim: "DXC was open-sourced on GitHub in 2017"
  - Source in sources.json: [src:8]
  - Verified: ___
  - Notes: Check the GitHub repo's initial commit date for precision
```

For long manuscripts this list will have hundreds of claims. That's the point. Each one takes 1–5 minutes to check if the source exists; longer if the source needs re-finding.

For book-writer-skill runs, consider generating the claim list semi-automatically: walk each chapter for sentences containing numbers, proper nouns, direct quotes, or `[src:N]` citations, and draft a claim entry per hit. Human review catches what the parser misses.

### Step 2 — Verify each claim against its cited source

Open each cited source and confirm it actually says what the claim says. Not "this source is about this topic." Specifically: "this page, this paragraph, this sentence supports this claim."

Common failures to watch for:
- Source supports a weaker version of the claim than the text uses
- Source says the opposite and was misread during research
- Source is an aggregator (Wikipedia, news article) and the claim needs to trace to Wikipedia's source, not Wikipedia itself
- Citation was added during writing without the source being re-checked

Mark each claim `verified`, `needs-softening`, `needs-new-source`, or `remove`.

### Step 3 — Check un-sourced claims

Some claims in the manuscript may not have `[src:N]` citations because they were treated as common knowledge. The fact-check questions this.

"A CPU cycle is about a third of a nanosecond" — common knowledge, but still a specific number. A fact-checker either finds a source or softens the claim ("on the order of a nanosecond") or removes the specific number.

For every un-sourced factual claim, the fact-check result is one of:
- **Source found** → add citation, update sources.json
- **Claim is genuinely common knowledge** → leave as is, with a note in fact-check.md explaining why (e.g. "basic arithmetic, no citation needed")
- **Claim is defensible but not common knowledge** → find a source or soften the claim
- **Claim is indefensible** → remove or rewrite

### Step 4 — Check source currency

For every source in `sources.json`:
- Does the URL still resolve? If not, find an archived version or a replacement.
- Has the source been updated, retracted, or superseded since it was recorded?
- For documentation sources (likely to change): is the cited version or commit still current? Should we pin to a specific version?

Web archive (archive.org) is the fact-checker's friend for URLs that 404.

### Step 5 — Run the date-sensitive check

Any claim that was true at research time but may have shifted since. These need either:
- A "current as of date X" qualification in the prose
- Re-verification and an update
- Removal if the currency has changed the meaning

Common categories: role holders ("the current CEO of..."), recent statistics, software version-specific claims, "the most recent" anything.

### Step 6 — Write the fact-check report

At the end of the pass, produce `fact-check-report.md`:

```markdown
# Fact-check report

**Manuscript checked:** HLSL book, draft of [date]
**Total claims reviewed:** 247
**Results:**
- Verified as written: 231
- Softened or qualified: 9
- Re-sourced (original source inadequate): 4
- Removed or rewritten: 3

**Changes applied to manuscript:**
1. Chapter 1: "a CPU cycle is about a third of a nanosecond" → "on the order of a nanosecond" (was a specific claim without specific source)
2. Chapter 4: Quote attributed to "Tim Sweeney" had drifted; restored exact wording and added proper citation
3. ...

**Outstanding concerns:**
- Source [src:8] (DXC release notes) will continue to drift — recommend pinning URL to a specific commit/tag before publication
- Chapter 9 cites a pre-2015 psychology study; consider whether the replication concerns should be mentioned in the text

**Single-source claims reviewed:**
- List of claims that still rest on only one source, with reasoning for why that's acceptable (or a flag for the user to address)

**Manuscript status:** ready for Assembly / needs another revision pass before Assembly
```

The report is an artefact the user sees. It's also what makes the fact-check auditable later — if someone questions a claim post-publication, the report shows what was checked and how.

---

## Collaboration with the user

For a demo or small project, the skill runs the fact-check alone and presents the report.

For a production book, the fact-check is an appropriate place for the user (or a dedicated fact-checker) to be more involved. The skill can:

- Produce the claim list and do the easy verifications (source-says-what-claim-says checks)
- Flag the hard cases for the user — claims where the source is ambiguous, where sources conflict, where the claim may have shifted since research
- Ask the user for decisions on softening vs re-sourcing vs removal

The skill should not make editorial decisions alone on high-stakes claims (ones about living people, contested history, or anything the user has flagged as sensitive). Those go to the user.

---

## The one-claim-per-source caution

One pattern worth guarding against: a book builds on itself, and the same source ends up supporting many claims. That's fine — but only if the source actually supports each claim. It's easy to cite [src:12] for claim A (which [src:12] genuinely covers), then re-cite [src:12] for claim B (which it doesn't). The fact-check checks each citation against its specific claim, not the source's general reputation.

A good practice during writing is to note in `sources.json` what specifically each source is useful for:

```json
{
  "id": 12,
  "title": "...",
  "useful_for": [
    "SM 6.6 feature list",
    "IsHelperLane intrinsic specification",
    "wave size attribute semantics"
  ]
}
```

Claims not on the `useful_for` list need a different source or additional corroboration, even if `[src:12]` happens to be about the right general topic.

---

## After the fact-check

A manuscript that has passed fact-check is called **verified**. Update each chapter's frontmatter:

```yaml
status: verified
fact_checked_at: 2026-04-25
fact_check_report: fact-check-report.md
```

From this point, Assembly can proceed. Claims added after the fact-check (during revision, during copy-edit) need their own mini-check — don't let late additions bypass the discipline.
