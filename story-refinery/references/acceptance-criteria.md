# Acceptance criteria and example mapping

## Contents

1. Example Mapping
2. Choosing an AC form
3. Testability test
4. Non-functional criteria
5. Non-goals
6. Definition of Ready - and its critics

---

## 1. Example Mapping

`[P: Matt Wynne, Cucumber, 2015]`. A 25-minute conversation format with four
card colours:

| Colour | Content | Goes to |
|---|---|---|
| Yellow | The story | `story.title` / `story.summary_human` |
| Blue | A rule | one acceptance criterion |
| Green | A concrete example of a rule | `examples[]` under that criterion |
| Red | A question nobody can answer now | `open_questions[]` |

Signals from the card layout `[P: Wynne]`:
- **Many blue cards (>6)** - the story is too big; split it.
- **Many red cards** - the story is not ready; the finding is "not ready", and
  that is a successful refinement.
- **A blue card with no green cards** - nobody actually understands that rule.
- **Green cards that contradict** - a hidden rule is missing.

Run this even when refining solo. Writing the questions down is most of the
value; you are simulating the Three Amigos `[P: George Dinwiddie]` (business,
development, testing) perspectives.

---

## 1a. Codes

A criterion arrives from a ticket as a sentence and leaves this skill as `AC3`.
From that moment the code is a public reference: subtasks `cover` it, the decision
table cites it, critics locate findings by it, and people type it into comment
threads and pull request titles.

**Assign one where the source has none.** Most tickets arrive with prose or
bullets. Numbering them is free and makes every later conversation shorter -
"AC3 is not testable" instead of quoting a sentence back.

**Keep the source's scheme where it has one.** If the ticket already says `AC-1`
or `C1` or "Criterion 3", use that. Renaming someone's existing references to
match this skill's preference is a cost with no benefit, and `AC010` reports a
story that ends up carrying both schemes.

**Never renumber** `[L]`. This is the rule that matters, and the one that feels
harmless to break. Insert a criterion in the middle and the obvious move is to
shift the rest down - after which `AC4` in a three-week-old comment, in a merged
PR title, and in a subtask's `covers` list all point at a different rule, and
nothing anywhere reports an error. A new criterion takes the next free code.

**A deleted criterion leaves a gap.** Its code is retired, recorded in
`story.retired_criterion_ids`, and never reused (`AC011`). Gaps are cheap;
a code that changes meaning is not, because every reference to it still resolves.

```bash
python scripts/criteria.py assign --bundle bundle.json --previous prior.json --write
python scripts/criteria.py check  --bundle bundle.json --previous prior.json
```

`assign` fills in what is missing and, on a re-refinement, recovers the code a
criterion had last time even when the wording changed - text matching, so a
reworded rule keeps its identity. `check` is the one to run before pushing an
update: it detects the shift signature, where a code now carries what a different
code used to say.

One more, for anywhere a code leaves its own story - a batch finding, a `pending`
entry, a cross-story link: **qualify it**, `ABC-123/AC2`. Inside the story's own
ticket `AC2` is unambiguous and stays short.

---

## 2. Choosing an AC form

Two forms. Pick per criterion, not per story.

### Rule + examples (default `[L]`)

```
AC2: Refunds above the daily limit require supervisor approval.
  - 40 EUR refund, limit 100 EUR  -> processed immediately
  - 140 EUR refund, limit 100 EUR -> queued as PENDING_APPROVAL
  - 100 EUR refund, limit 100 EUR -> processed immediately (boundary: inclusive)
```

Compact, and forces the boundary case into the open. Best for business rules.

### Given / When / Then

`[P: Dan North, BDD, 2006]`. Use when the scenario has meaningful setup or
sequencing that the rule form hides.

```
Given a cart with a 100 EUR item and a 10% coupon
When the customer applies a second 10% coupon
Then the second coupon is rejected with COUPON_ALREADY_APPLIED
And the cart total remains 90 EUR
```

Rules for Gherkin that keep it useful `[F]`:
- One `When` per scenario. Two `When`s means two scenarios.
- No UI mechanics in `Given`/`When` ("clicks the blue button") unless the UI
  interaction *is* the behaviour under test.
- `Then` asserts observable outcome, not implementation state.
- Avoid `And` chains longer than two - they hide a missing abstraction.

Do not write Gherkin for everything. Ceremony without conversation is the most
common way BDD fails `[F]`.

---

## 3. Testability test

Every criterion must pass all four `[L]`:

1. **Observable** - can be checked from outside the unit that implements it.
2. **Binary** - it either holds or it does not; no "reasonably fast", no
   "user-friendly".
3. **Bounded** - it names its own limits; a criterion that implies "and all
   similar cases" is not one criterion.
4. **Falsifiable now** - you can describe the test that would fail today.

If a criterion fails the test, either add the missing number, split it, or move
it to `non_goals`.

**Vagueness lexicon** - `validate.py` flags these in AC (error) and human text
(warning). The list is **language specific and inflection specific**: a Dutch
ticket sails past every English term, and "netjes afhandelen" does not match
"netjes afgehandeld". Extend `validation.vagueness_lexicon` with the forms your
team actually writes, or the check is decorative. The shipped config carries a
Dutch block as a worked example.

Current English defaults:
`etc.`, `and so on`, `as needed`, `appropriately`, `properly`, `handle
gracefully`, `should probably`, `if necessary`, `where applicable`, `robust`,
`user-friendly`, `optimize`, `improve performance` (without a number),
`various`, `some`, `several`.

Each of these is a question in disguise. Convert it: "handle errors
appropriately" becomes "what should happen when the payment provider times out
after 30s?" - a red card.

---

## 4. Non-functional criteria

Refinements routinely omit these and the implementation routinely gets them
wrong. Check each category and either give a number or explicitly write
"unchanged from current behaviour" `[L]`:

| Category | Ask |
|---|---|
| Performance | p95 latency budget, payload size, N+1 risk on the touched path |
| Concurrency | what happens on simultaneous requests for the same entity |
| Failure | timeout, retry policy, idempotency, partial failure across repos |
| Data | migration required? backfill? reversible? volume? |
| Security | authz check location, PII in logs, new external input to validate |
| Observability | what metric/log/trace proves this works in production |
| Accessibility | for UI work, the specific WCAG criteria in play |
| i18n | new user-facing strings, currency/date/number formatting |
| Compatibility | old clients, in-flight records, feature flag and its removal |

ISO/IEC 25010 `[P]` is the fuller quality model if the house needs a formal
mapping; the table above is its practical subset.

Which categories are mandatory is configurable: `validation.non_functional_keys`
drives the `NFR001` check. The default is the seven that most often go wrong;
add accessibility and i18n if your product needs them checked every time.

---

## 5. Non-goals

An explicit `non_goals` list is the cheapest scope control available and the
single most useful field for an agent implementor `[N]`. Populate it from:
- things people mentioned in the conversation that are not in this story
- adjacent code the change surface touches but should not modify
- the "while we're in there" refactors somebody will suggest
- follow-up work you deliberately deferred (link the follow-up ticket)

---

## 6. Definition of Ready - and its critics

DoR is not in the Scrum Guide. The 2020 guide defines a Definition of Done but
no Definition of Ready `[P: Scrum Guide 2020]`. DoR is a widely-used community
practice `[F]`, and it has a real critique: used as a hard stage gate it
recreates a mini-waterfall, encourages big up-front specification, and blocks
flow while a ticket waits to be "ready enough" `[F]`.

How this skill handles that tension `[L]`:

- The DoR check is **mechanical and fast** (`validate.py`, seconds), not a
  recurring meeting.
- Failing it produces a **list of specific questions with owners**, not a
  rejection.
- A story with open questions can still be pulled as a **spike**. The gate
  blocks "build this now", not "work on this".

Default ready criteria, all machine-checkable:

- [ ] Every AC passes the testability test
- [ ] Every AC has ≥ 1 concrete example
- [ ] `open_questions` contains no `blocking: true` entries
- [ ] Every design decision is `locked` or `deferred` with a spike subtask
- [ ] Change surface is non-empty and every entry cites a real path
- [ ] Every subtask has ≥ 1 runnable `done_when`
- [ ] Coverage matrix: every AC → ≥ 1 subtask, every subtask → ≥ 1 AC or tagged
      `enabling`/`spike`
- [ ] Dependency graph is acyclic and contract producers precede consumers
- [ ] Non-functional table addressed or explicitly marked unchanged
