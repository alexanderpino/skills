# Stories in a stream

Backlog items do not arrive one at a time. They arrive as a queue in an area of
the code, as the pieces of a split epic, as the follow-ups an earlier refinement
created, and as the same story coming round again because something changed.
Refining each one as though it were the first is how a team pays for the same
investigation four times and gets four slightly different answers.

Three rules carry a refinement forward `[L]`.

## 1. Refine just in time, not just in case

Refine what the next sprint could plausibly pull, and stop. A refinement is a
snapshot of a repository at a sha, and it decays: citations move, conventions
change, the decision that was open gets made elsewhere. A story refined six weeks
early is re-refined before it is implemented, so the first pass bought nothing
and cost the freshest thing in the bundle - its evidence `[F]`.

Practically: enough refined items to keep the next sprint's capacity fed, plus
whatever a spike must answer before it. If a backlog needs more than that, the
problem is prioritisation, and refinement is the most expensive place to discover
it.

The exception is a story blocked on someone outside the team. Refine that early
enough for the question to reach them, because the wait is the long pole, not the
work. That is what `open_questions[].asked` is for: the date the question left
your hands is the date the clock started.

## 2. Inherit the dossier, then re-verify it

The second story through the same code does not need the glossary, the house
conventions or the negative results re-derived. It needs them **re-checked**,
which is a fraction of the cost.

```bash
python scripts/evidence.py inherit --from .refinery/bundles/ABC-123@2026-09-02.json \
  --bundle bundle.json --write
```

It carries `glossary`, `conventions` and `ruled_out` across, stamps each with
where it came from, and compares the sha it was verified at against the repo's
HEAD now. If the repo moved, every carried entry is marked `stale: true` and
`SER001` keeps saying so until you have re-read them.

What ages at different speeds `[N]`:

| Carried | Ages | Because |
|---|---|---|
| glossary | slowly | domain words outlive refactors |
| conventions | at the pace of the codebase | cited, so cheap to re-check - open the citation |
| contracts | on every release | re-derive rather than trust |
| `ruled_out` | **fastest, and silently** | the absence someone filled in last sprint is exactly what a new story is likely to have added |

That last row is why `inherit` marks everything stale rather than only what
obviously moved. A ruled-out entry that has quietly become false is worse than no
entry: the previous refinement's confidence is now actively misleading, and it
reads like evidence.

Re-verification is not a re-scan. Open the citation, run the query in `looked_in`
again, and either keep the entry with a new sha or delete it. Anything you delete
is worth a sentence in the handover - it is a fact about the codebase that
changed.

## 3. Record what this refinement creates

A refinement is a producer of future work as much as of present work. Three
kinds, and all three vanish unless written down `[N]`:

- **Non-goals with a ticket.** "Non-EU B2B — follow-up ABC-131" is a promise. If
  nothing tracks ABC-131 it is not a scope boundary, it is a thing the team
  agreed to forget. `SER002` links the two.
- **Deferred decisions.** The spike answers a question; the answer changes the
  *next* story, not this one. Say which one.
- **Flags, migrations and temporary states.** Every one needs the item that ends
  it, with a trigger. "Remove the flag" with no trigger sits in a backlog forever
  and eventually becomes load-bearing.

```json
"follow_ups": [
  {"ticket": "ABC-140", "trigger": "the flag has been on for every market for two weeks",
   "owner": "@team-billing", "note": "Remove the flag and its branch. Without it, permanent."}
]
```

A `trigger` is a condition someone can observe, not a date. Dates in a backlog
are wishes; "when the flag has been on everywhere for two weeks" is checkable by
whoever picks it up.

## Refining against work that does not exist yet

The second story in a sequence is refined while the first is still being built,
so some of what it cites has not been written. This is the single most common way
a follow-up refinement quietly becomes fiction: a path is cited, it looks like
evidence, and nobody notices it is a prediction until an implementor opens it.

Three rules `[N]`:

1. **It gets its own state.** Not a citation, not an `ASSUMPTION`, but
   `evidence.pending`: a claim, and the item that creates it - ticket, subtask,
   and the stored bundle where its shape is fixed. That is still checkable; it
   just points at a plan rather than at a line. `expected_path` is allowed and is
   explicitly a prediction (`PND001`).
2. **Do not re-specify it.** The shape of the thing belongs to the item that
   creates it. Restating it here produces two specifications that drift, and the
   one in the follow-up is the one nobody updates. Point at it.
3. **The ordering has to leave your head.** Inside a story the wave plan orders
   the work. Across stories, nothing does except a tracker link, so a pending
   entry requires a `blocked_by` link to its provider (`PND002`). A "relates to"
   is not a prerequisite: it does not stop anyone starting this first.

`emit.py` turns `story.links` into the tracker's own vocabulary and reports what
it cannot express - GitHub has no typed issue links, so the ordering it carries
lives in the description where nothing enforces it, and the push plan says so
rather than pretending.

The two-sided output matters here. The **ticket** gets a Prerequisites section
so a developer sees what has to land first; the **shared context** gets a "Not
there yet" block so an implementor does not go looking for a file, and - the
expensive case - does not substitute something that merely looks similar.

## Several at once

Sometimes the request is not one story but five: an epic's slice, a triage batch,
everything queued in one area. Batching is legitimate when the set is *related* -
and only then. Five unrelated items refined to have "enough refined" is the
anti-pattern at the bottom of this file wearing a schedule.

When it is legitimate, the rule is one line: **share the evidence, never the
judgement.**

| Shared across the batch | Never shared |
|---|---|
| glossary, house conventions, `ruled_out` | the intake verdict |
| contracts and the repo manifests | the acceptance criteria |
| a fork that genuinely affects several stories - decided once | the decomposition |
| the questions, asked once per owner | the critic panel: critics judge one artefact |

The second column is what makes a batch dangerous. Reuse is efficient for facts
and corrosive for judgement: the second and third stories drift into shallower
copies of the first, because the shape is already there and filling it in feels
like refining `[N]`.

```bash
python scripts/batch.py order --bundles a.json b.json c.json    # who first, which forks are shared
python scripts/batch.py share --bundles a.json b.json c.json --write
python scripts/batch.py check --bundles a.json b.json c.json    # what only shows up side by side
```

**Order matters.** Refine the story the others depend on first: its decisions and
its evidence are inputs to theirs, and re-deciding a fork per story is how one
batch produces three incompatible answers. `order` derives that from the
cross-story `blocked_by` links and `evidence.pending`, and names the forks that
are open in more than one bundle.

**Bundles stay self-contained.** Each is pushed and read alone, so shared
knowledge is *copied* into every bundle rather than referenced - marked with
which story it came from. `share` refuses to spread a definition that two bundles
already disagree about, because sharing it would spread whichever one is wrong.

**`check` is the part that only works side by side**, and it finds what no
single-bundle gate can:

| | |
|---|---|
| `BAT001` | two stories whose subtasks write the same file. Inside a story the wave plan stops this; across stories nothing does |
| `BAT002` | shared knowledge that disagrees with itself - worse than none, because each story still looks internally consistent |
| `BAT003` | the same question put to the same person from three tickets. Ask once, name the stories it affects |
| `BAT004` | one story waits on another *in the same batch* with no `blocked_by` link. Here the order is knowable, so there is no excuse for it living only in your head |
| `BAT006` | two stories touching mostly the same files - check they are two stories and not one split by wording |

Run `check` before pushing any of them. A batch pushed one ticket at a time is a
batch whose contradictions arrive in production one sprint at a time.

## Sequences

**A split epic.** Map it, draw the release line, then refine **one** story
properly (see `references/decomposition.md`). The others get titles and a
one-line scope, nothing more, and they inherit the dossier when their turn comes.
Refining all of them now guarantees that the ones implemented later are wrong,
because the first one will teach you something.

**A spike and the story behind it.** The spike is refined; the story it informs
is *sketched*. Its acceptance criteria depend on an answer that does not exist
yet, so writing them now means writing fiction and defending it later. Record
which decision the spike resolves (`decisions[].spike`) and refine the story when
it lands.

**The same story again.** That is re-refinement, not a new story: keep the key,
diff against the stored bundle with `emit.py --previous`, and update the tree
rather than building a parallel one. Orphaned subtasks are reported, never
auto-deleted - work may already have happened against them.

**A story that implementation contradicted.** The most valuable input a
refinement gets. Fold the report in as a re-refinement (see
`references/agent-brief.md` §10), and pay particular attention to a `ruled_out`
entry that turned out to be false: that means a *search* was wrong, and the same
search will run again on the next story in this area.

## Sprint-cadence habits that pay

- **Keep the bundle next to the ticket.** `.refinery/bundles/<KEY>@<date>.json`
  is what the next refinement diffs and inherits from. Without it every pass
  starts from the tracker text, which is the compressed version.
- **Re-run `validate.py` on a bundle before pulling the story into a sprint.**
  It is cheap, and a bundle that was ready three weeks ago may now have a stale
  review stamp (`REV007`), a moved citation, or an expired deferred decision
  (`DEC007`) - all of which are better found at planning than at 3pm on day two.
- **Take the unasked questions to the session that exists anyway.** Refinement,
  planning, standup: the ceremony is already on the calendar, and `READY003`
  tells you exactly which questions have not yet been put to anyone.
- **Do not batch-refine to fill a slot.** Refining five items shallowly to have
  "enough refined" produces five items that pass the gates and none that survive
  contact. One properly refined story plus four honest "not ready, here is what
  we need" is a better sprint input, and says something true about capacity.

## Smells

**The perpetual first pass.** Every story in an area re-derives the same
conventions. *Tell:* no `story.series.predecessors` anywhere, and identical
`conventions` entries in successive bundles. *Fix:* `evidence.py inherit`.

**Inherited confidence.** A bundle carrying entries marked `stale` straight to
handover. *Tell:* `SER001`. *Fix:* re-read or drop; an unchecked inheritance is
worse than a blank field because it reads as evidence.

**The forgotten promise.** Non-goals naming tickets nobody created. *Tell:*
`SER002`. *Fix:* create them, or say plainly in the handover that the scope was
cut and not deferred - those are different, and only one of them is a plan.

**Refined-and-parked.** A backlog of items refined months ago, all of them
subtly wrong now. *Tell:* bundles whose newest `provenance` sha is far behind
HEAD. *Fix:* refine less, closer to the sprint. Refinement does not keep.
