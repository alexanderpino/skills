# Intake: is there enough to refine?

Most refinement waste happens before refinement starts: a scan budget spent on
the wrong hypothesis, a decomposition of something nobody has agreed on, a
polished plan for a mechanism whose purpose was never stated. This gate exists
to stop that, mechanically, before Phase 2.

## Contents

1. What "enough" means
2. The three verdicts
3. How the detector works, and what it cannot do
4. Statuses and what each obliges you to record
5. Asking well
6. Signals the detector raises

---

## 1. What "enough" means

Enough is per kind of item, per dimension. Defaults `[L]`, configurable under
`intake:`.

**Feature** - required: `actor` (who), `outcome` (what is different afterwards),
`trigger` (what sets it off). Recommended: `success_signal` (how we would know),
`scope` (what it is not).

**Bug** - required: `repro` (steps from a clean state), `expected`, `actual`,
`environment` (where and which version). Recommended: `impact` (how many, how
often, since when).

These map to the two classic intake shapes - the user-story template
`[F: Connextra, 2001]` and the bug report template `[F]` - stripped down to the
parts that change what you would build. "Priority" and "story points" are not
here because they change when, not what.

Why `trigger` is required and `success_signal` only recommended: without a
trigger you cannot find the entry point in the code, so Phase 2 has nowhere to
start. Without a success signal you can still build the right thing; you just
cannot yet prove it, and Phase 3's examples usually surface one.

---

## 2. The three verdicts

| Verdict | Condition | What you do |
|---|---|---|
| **sufficient** | every required dimension present, assumed, or answered | continue to Phase 2 |
| **scoutable** | a required dimension is missing, but there is ≥ 1 code anchor and a reachable repo | run Phase 2 **only**, to turn the missing dimension into a sharper question, then stop and ask. Do not decompose. |
| **insufficient** | required dimensions missing and nothing to scan for | stop and ask before spending anything |

`scoutable` exists because sometimes the code answers the question better than
the stakeholder can: "what triggers the export?" is often one `grep` away. But
it is a licence to look, not to build. `validate.py` fails a bundle that has
subtasks under any verdict other than `sufficient` (`INT003`).

Exit codes from `intake.py assess`: 0 sufficient, 3 scoutable, 4 insufficient,
so a script can branch on it.

---

## 3. How the detector works, and what it cannot do

`intake.py` matches **lexical signals** in English and Dutch: "as a", "so that",
"zodat", numbered steps, "expected"/"verwacht", version strings, browser names,
units like "5 seconds" or "binnen 1 minuut". For each dimension it reports the
snippet it matched.

What it cannot do is read. It will mark `outcome` present on "I want the button
blue" and `repro` present on "1. it breaks". Every `present` it emits carries
`heuristic: true` until a reader flips it, and `validate.py` warns on any that
were never confirmed (`INT009`).

What it *can* guarantee: a dimension recorded as `present` quotes text that is
actually in `story.source_text` (`INT007`). You cannot satisfy the gate by
paraphrasing the ticket into something better than it was.

Anchors are the second thing it looks for: CamelCase symbols, `snake_case`,
endpoints, paths, HTTP statuses, ticket keys, code spans, quoted strings, and
title-case domain nouns mid-sentence ("Invoices", "OrderDetail"). Anchors are
what a Phase 2 hypothesis is made of; a ticket with none is a ticket you cannot
scan for.

---

## 4. Statuses and what each obliges you to record

| Status | Means | Must carry | Gate |
|---|---|---|---|
| `present` | the source text says it | `evidence` - a verbatim quote | `INT007` quote must occur in source_text |
| `missing` | it is not there and you do not know | `question_id` → a **blocking** open question (required dims) | `INT004` |
| `assumed` | it is not there and you are proceeding on a stated guess | `assumption` text + `question_id` → a **non-blocking** question | `INT005`, `INT006` |
| `answered` | it was not there, you asked, someone answered | `answer` + `answered_by` (who, when) | `INT010` |

The distinction between `assumed` and `answered` matters later. An assumption is
yours and can be wrong silently; an answer has a name on it. Both are legitimate
ways to reach `sufficient`. Quietly promoting an assumption to `present` by
editing the source text is not, and `INT007` is there to make that awkward.

`intake.py assess --bundle bundle.json --write` fills `story.intake` and appends
one open question per missing dimension, blocking for required ones, with a
`(best guess: ?)` placeholder. Replace every `?` with your actual best guess
before showing the questions - see below.

---

## 5. Asking well

Attach a guess to every question. "What triggers it?" makes the stakeholder
write an essay; "What triggers it - I assume the Export button on the Invoices
screen, is that right?" makes them say "yes" or "no, the nightly job". The
second is faster for them and gives you a correctable hypothesis either way.

Ask all of them at once. Three rounds of one question each is how a ticket
spends a week in refinement.

Put the owner's name on each one. An unowned question does not get answered.

If the verdict was `scoutable`, do the scan first and let it sharpen the
questions - "I found `InvoiceExportJob` running nightly and an Export button in
`InvoicesPage.tsx`; which one is this story about?" is a better question than
either half alone.

---

## 6. Signals the detector raises

- **mechanism-only** - a solution is named (cache, queue, index, migrate to,
  refactor) with no outcome. This is the most common way a bad story looks like
  a good one: it reads as specific because it names a technology. Ask what it
  is for. Refining "add a Redis cache" without knowing which latency it is meant
  to fix produces a cache in the wrong place.
- **very short** - under a dozen words. Not necessarily insufficient, but a
  prompt to look twice at what was marked present.
- **no repos reachable** - the config names repos that are not on disk. Phase 2
  cannot run; `scoutable` is impossible; say so rather than pretending to scan.
- **kind mismatch** - the text reads as a bug (`INT011`) but the profile is not
  `bugfix`. The bugfix profile puts the failing test first; using vertical-slice
  on a defect produces a plan with no reproduction.
