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
- **kind mismatch** - the text reads as a bug and the profile is not `bugfix`, or
  as research and the profile is not `research` (`INT011`). Each profile exists
  because the others handle that shape badly: vertical-slice on a defect produces
  a plan with no reproduction, and a delivery profile on a research item plans
  the build the item exists to inform.
- **language** - detected from the source text and recorded in `story.language`
  (`scripts/lang.py`: distinct function words, seven languages, `unknown` below
  the floor or on a near tie). The refinement is written in that language and
  the ticket renders its headings in it. The lexical dimension patterns cover
  English and Dutch only; for any other language the assessment is yours by
  reading, and the flag says so. `unknown` is a prompt to name it, not a verdict.
- **unknown kind** - `INT012`. Only `feature`, `bug`, `spike` and `enabling`
  have a questionnaire. Anything else would silently fall back to the feature one, which
  is worse than failing: the item comes back assessed, with three dimensions
  answered that nobody asked about.

---

## 7. Is it knowable? (Cynefin)

The sufficiency gate measures whether the *information* is there. It cannot tell
you whether the *answer* is knowable in advance, and those are different
failures. A story can have an actor, an outcome and a trigger, pass every gate,
and still be unrefinable because nobody yet knows what will work.

Classify the problem and record it as `story.intake.domain` with a one-sentence
rationale `[P: Snowden & Boone, "A Leader's Framework for Decision Making",
HBR 2007]`:

| Domain | What it means here | Correct output |
|---|---|---|
| **clear** | known practice; the team has done this exact thing | refine, briefly - do not ceremony a two-line change |
| **complicated** | knowable, but needs expertise to work out | refine fully; this is the skill's home ground |
| **complex** | only knowable by trying; cause and effect are visible afterwards | a probe: a spike whose output is information, not a plan (`CYN001`) |
| **chaotic** | live incident, nothing stable to plan against | act to stabilise; refine what is left (`CYN002`) |

Most backlog items are complicated. The ones that are complex usually look
complicated - "improve the recommendation quality", "make onboarding feel
faster", "reduce churn on the trial plan" - because the *mechanism* is
unknowable even though the goal is clear. Decomposing one into seven confident
subtasks is the most expensive mistake this skill can make: everything downstream
runs correctly against an assumption nobody tested.

The tell is whether you can state the acceptance criteria without guessing at
what will work. If the honest AC is "we learn whether X moves Y", the output is a
probe with a hypothesis and a measure, not a decomposition.

### When the item *is* the research

The domain classification above tells a delivery story to grow a probe. A
research item is the other case: the probe is the whole ticket. It gets
`intake.kind: spike` - set by the discovery labels, or detected from the ticket
text - and with it a different questionnaire, because the feature one asks for an
actor and an outcome that do not exist yet. Answering those anyway is the
characteristic failure here: it produces a plausible feature story for work
nobody has established is worth doing.

| Dimension | The question | Why it blocks |
|---|---|---|
| **question** | What exactly do we not know, phrased so it can come back answered? | "Investigate caching" is a topic. A topic has no end, so the timebox has nothing to bound |
| **decision** | Which decision waits on the answer, and who makes it? | If none, this is reading. Reading is valuable and is not a ticket (`SPK003`) |
| **timebox** | How long before we decide with what we have? | The timebox is the price of the option; without it the spike becomes the project (`SPK002`) |
| *answer_shape* | What does the answer look like when it arrives - a number, a prototype, a recommendation? | Recommended. Without it two people expect different artefacts and both are disappointed |

The plan that follows is in `references/decomposition.md` §3 under `research`.
The one thing it must not contain is the build: a research item that already
plans `feature` work has assumed the answer, and `SPK004` says so.

### When the customer is the team

An enabler - an upgrade, a pipeline, tooling, infrastructure `[P: SAFe,
"enabler stories"]` - has no customer-facing outcome either, and the story form
hides that with "as a developer I want". It gets `intake.kind: enabling`, set by
the `enabler` labels or detected from the text, and two required dimensions
that the feature questionnaire would never ask:

| Dimension | The question | Why it blocks |
|---|---|---|
| **unlocks** | Which story, team or capability is waiting on this? Name it | Nothing waiting means gold-plating. A named ticket becomes a `blocks` link (`ENB001`), which is what keeps the enabler from being scheduled *after* the story it exists for, by someone who read neither |
| **cost_of_delay** | What breaks, slows down or stays risky for every sprint this is not done? `[P: Reinertsen, cost of delay]` | An enabler with no cost of delay loses every prioritisation it enters - and usually should |

`success_signal` and `scope` are recommended: "the build is green on 5.0" is a
better done-signal than "upgraded". No decomposition profile is forced - an
upgrade is usually `expand-contract`, a pipeline is usually `layered` - so choose
one on purpose. Detection is deliberately narrow: "platform" and "pipeline" are
domain nouns in half the businesses this will meet and are not enough alone;
"as a developer", "upgrade", "end-of-life", "set up" are.

## 8. Impact mapping the answer

The `mechanism-only` flag catches a ticket that names a solution with no outcome,
and stops to ask. When the answer comes back, record it as a chain rather than
prose `[P: Adzic, Impact Mapping, 2012]`:

**goal** → **actors** → **impacts** → **deliverables**

- **goal** - measurable, with a number and a date. "Manual reverse-charge refunds
  fall from around 40 a month to 0 within 30 days of the NL rollout." This is the
  field that tells you afterwards whether it worked (`IMP002`).
- **actors** - who has to behave differently. Include the ones who are not users:
  finance, support, the on-call engineer.
- **impacts** - the behaviour change in each actor that moves the goal. This is
  the column that gets skipped, and it is where alternatives live.
- **deliverables** - what we build to cause the impact. The least important
  column, and the one the ticket usually arrived as.

Read right to left to check the ticket: does this deliverable cause an impact
that moves the goal? A deliverable that does not is scope, however reasonable it
sounds. Read left to right to find cheaper options: another impact on the same
goal is often a tenth of the work, and proposing one is the highest-value thing
refinement can do.
