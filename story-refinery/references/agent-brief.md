# The agent brief

The human text and the agent brief describe the same work at different
compression ratios. The human shares your context, so you delete what they know.
The agent shares none of it, so you write it down.

## Contents

1. The compression asymmetry
2. Failure modes the brief exists to prevent
3. Field-by-field
4. Writing `done_when`
5. What not to put in it
6. Worked contrast
7. The dossier: what the ticket does not say
8. Preflight: briefs go stale
9. The shared context block
10. The loop back

---

## 1. The compression asymmetry

| | Human text | Agent brief |
|---|---|---|
| Audience assumption | knows the codebase, the team, last sprint | knows nothing outside this document |
| Budget | ≤ 80 words per subtask | none |
| Format | prose, decision-dense | structured JSON |
| Omits | anything obvious to a colleague | nothing |
| Includes uniquely | judgement, politics, "ask Marieke about X" | exact paths, commands, forbidden actions |
| Failure if wrong | developer asks a question | agent silently builds the wrong thing |

They must never contradict. If you find yourself writing something in the agent
brief that would surprise the human reader, it belongs in the human text too -
it is a decision, not a detail.

---

## 2. Failure modes the brief exists to prevent

Four ways an autonomous implementor fails on a well-written human ticket `[N]`:

**Wandering.** It reads 200 files looking for context, burns its budget, and
implements from a fuzzy average of the codebase.
→ `read_first`, `change_surface`, `context_budget_hint`, `entry_points`.

**Scope creep.** It notices adjacent problems and fixes them, producing a diff
nobody wants to review.
→ `forbidden`, `out_of_scope`.

**Convention drift.** It writes idiomatic-for-the-language code that is
unidiomatic for *this* codebase - different error handling, different test
layout, different DI wiring.
→ `conventions`, each with a `path:line` citation so the pattern can be read
rather than described.

**False completion.** It declares done because the code looks right, without
running anything that would have caught the failure.
→ `done_when` as runnable commands with expected results.

---

## 3. Field-by-field

```json
{
  "objective": "One sentence. What is true after this subtask that was not before.",
  "repo": "api",
  "branch_hint": "feat/ABC-123-tax-reverse-charge",
  "read_first": [
    {"path": "src/api/billing/tax.py", "why": "the calculator you are extending"},
    {"path": "tests/billing/test_tax.py", "why": "the test style to match"}
  ],
  "entry_points": [
    {"path": "src/api/billing/tax.py", "line": 88, "symbol": "TaxCalculator.rate_for",
     "why": "insert the reverse-charge branch here"}
  ],
  "change_surface": [
    {"path": "src/api/billing/tax.py", "role": "modify"},
    {"path": "tests/billing/test_reverse_charge.py", "role": "create"}
  ],
  "contracts_must_not_break": [
    {"path": "openapi.yaml", "note": "response shape is additive only; web@1.4 reads tax.total"}
  ],
  "conventions": [
    {"rule": "Money is Decimal, never float. Round with money.round_half_up.",
     "evidence": "src/api/billing/money.py:17"},
    {"rule": "Domain errors subclass BillingError and are returned, not raised.",
     "evidence": "src/api/billing/handlers.py:44"}
  ],
  "done_when": [
    {"type": "command", "cmd": "pytest tests/billing -q", "expect": "exit 0"},
    {"type": "command", "cmd": "ruff check src/api/billing", "expect": "exit 0"},
    {"type": "assertion", "text": "A B2B order with a valid EU VAT number outside NL returns tax.total == 0 and tax.reason == 'reverse-charge'"}
  ],
  "forbidden": [
    "Do not modify openapi.yaml in this subtask - S4 owns it.",
    "Do not reformat files you did not otherwise change.",
    "Do not add or upgrade dependencies."
  ],
  "out_of_scope": [
    "Non-EU B2B handling (follow-up ABC-131)",
    "Retroactive recalculation of existing orders"
  ],
  "rollback": {"flag": "billing.reverse_charge", "note": "default off; no data migration"},
  "context_budget_hint": "read_first only; do not index the repo",
  "provenance": ["api@9f2c1ab", "manifest 2026-09-02"]
}
```

**Path convention.** Story-level evidence (`evidence.change_surface`,
`evidence.conventions`) is repo-qualified: `api/src/billing/money.py:17`. Inside
an agent brief every path is relative to the brief's own `repo`:
`src/billing/money.py:17`. The brief carries `repo` once so the implementor never
has to strip a prefix, and `validate.py` matches the two forms up when it checks
briefs against evidence.

Guidance per field:

- **`objective`** - state the post-condition, not the activity. "Reverse-charge
  orders return zero tax with a reason code" beats "work on tax logic".
- **`read_first`** - three to six files, each with a *why*. This is the single
  highest-leverage field; it is what stops the wandering.
- **`entry_points`** - line + symbol. Line numbers drift, symbol names survive;
  give both.
- **`change_surface`** - roles: `create` | `modify` | `delete`. If you are not
  sure a file needs changing, leave it in `read_first` instead.
- **`contracts_must_not_break`** - name the consumer and the version if known.
  "Additive only" is a real instruction; "be careful" is not.
- **`conventions`** - 2-6 entries. Evidence is mandatory. Uncited conventions
  are your training priors leaking into someone's codebase.
- **`forbidden`** - phrase as prohibitions, not preferences. Include the
  cross-subtask boundaries; this is how you stop two parallel agents fighting
  over the same file.
- **`context_budget_hint`** - tells the implementor how much exploration is
  warranted. Cheap to write, saves a lot.

---

## 4. Writing `done_when`

This is the contract for completion. Two types:

**`command`** - anything runnable with a checkable result. Take the actual
commands from the repo manifest (`commands.test`, `commands.lint`), not from
what you assume the stack uses.

```json
{"type": "command", "cmd": "pytest tests/billing/test_reverse_charge.py -q", "expect": "exit 0"}
```

Scope the command to the subtask where possible. `pytest -q` on a large repo is
slow and noisy; a targeted path is a better gate and a faster loop.

**`assertion`** - a behavioural statement that cannot be a command yet, usually
because the test does not exist. It must be specific enough that the implementor
can write the test from it. If you cannot write it that specifically, it is an
open question, not a done-when.

Rules `[L]`:
- Every subtask has ≥ 1 `command` entry. A subtask verified only by assertions
  has no mechanical gate.
- Every AC the subtask covers appears in at least one `done_when`.
- Do not include "code reviewed" or "PR approved" - those are workflow states,
  not completion evidence, and the tracker already tracks them.

---

## 5. What not to put in it

- **The implementation.** No pseudocode, no diffs, no "then add a method that
  loops over...". You are specifying the seam, not filling it. If you catch
  yourself writing the solution, move the content into a design decision and
  record only the decision.
- **Speculative context.** Anything you did not verify. A wrong path is worse
  than a missing one, because the agent will trust it.
- **Duplicated story text.** The brief links to the parent; it does not restate
  the business case beyond `objective`.
- **Secrets, tokens, internal URLs** that the tracker exposes more widely than
  the repo does.

---

## 6. Worked contrast

Same subtask, both audiences.

**Human (58 words):**
> Extend `TaxCalculator` with the EU reverse-charge rule. Rate table already
> handles NL; this adds the B2B-with-valid-VAT-number branch returning zero with
> a reason code. Behind `billing.reverse_charge`, default off. VAT number
> validation is out of scope - S1 landed `VatNumber.is_valid`. Web renders the
> reason in S4; do not touch `openapi.yaml` here.

**Agent:** the JSON block in section 3 above.

The human version assumes you know what `TaxCalculator` is, that flags default
off here, and that S1 and S4 exist. The agent version assumes none of it, and
spends 40 lines saying so. Both were written from the same evidence, in the same
pass, and they agree.


---

## 7. The dossier: what the ticket does not say

A refinement learns far more than it writes down. The human text is compressed on
purpose, the brief carries what this subtask needs, and the rest - the files you
opened and closed, the thing you went looking for and could not find, the term
that means something specific here - evaporates. Then the implementor re-derives
it, badly, at full price. Where the implementor is an agent this is worse: it has
no colleague to ask, and its re-derivation is invisible until the diff arrives.

Two fields hold the residue that pays for itself.

### `evidence.ruled_out` - the negative results

The most valuable thing you know at the end of Phase 2 is often what is *absent*.
Absence is expensive to establish (you have to look everywhere it could be) and
free to lose (nothing in the ticket has a natural place for it).

```json
{"claim": "There is no existing VIES client, cache or VAT verification against an external service",
 "looked_in": ["api/src/billing/**", "api/src/integrations/**", "rg -i 'vies|vat.?check'", "api/pyproject.toml"],
 "conclusion": "vat.py:12 validates format only. The lookup is new work; do not hunt for a helper, and do not mistake VatNumber.is_valid for verification."}
```

Three rules `[L]`:

- **`looked_in` must be re-checkable.** Paths, globs, the actual queries. A
  negative result nobody can re-run is a rumour, and it ages worse than a
  positive one (`EVI009`).
- **`conclusion` says what to do, not just what is missing.** "There is no cache
  wrapper" is a fact; "so if you want one, that is a decision, not a detail -
  raise it" is usable.
- **The dangerous absence is the near-miss.** When something *similar* exists,
  say so explicitly. An agent that finds `VatNumber.is_valid` while looking for
  VIES verification will use it, and every test will pass.

`EVI008` fires when a story crossing more than one repo rules nothing out: you
cannot have read two codebases and learned nothing about what is not in them.

### `evidence.glossary` - the words

Domain nouns are where a context-free implementor confidently goes wrong.
"Reverse charge" is not a discount, "reason" is a customer-visible contract and
not an implementation detail. Four to eight terms, each with where you got it.
Cheap to write, and it is read by every subtask.

---

## 8. Preflight: briefs go stale

A brief is a snapshot of a repository at a sha. By the time an agent picks up
subtask four, the file may have moved, the symbol may have been renamed, and
`line 88` is now something else entirely. A human notices. An agent edits what is
at line 88.

```json
"preflight": [
  {"type": "command", "cmd": "grep -n \"def rate_for\" src/billing/tax.py",
   "expect": "a hit at or near line 88"}
]
```

One command per anchor the brief actually depends on - the entry point, the
convention's file, the flag. `BRF013` fires when entry points carry line numbers
and nothing verifies them.

The instruction that goes with it matters as much as the commands: **if preflight
fails, stop and report - do not implement against a stale anchor, and do not go
looking for where the code moved to.** That is the one case where the ticket is
wrong and the implementor is right, and it should come back to refinement rather
than being silently absorbed.

`stop_and_ask` is the same instinct for ambiguity rather than drift.
`forbidden` says what not to touch; `stop_and_ask` says what not to *decide*
(`BRF014`). Every open question that could surface mid-implementation belongs
here, phrased as the condition the implementor would actually notice:

```json
"stop_and_ask": [
  "S0 has not landed, so the cache TTL is still unknown - do not pick one",
  "vat.py does not distinguish an invalid number from an unreachable VIES - that distinction is AC2 and is not yours to invent"
]
```

---

## 9. The shared context block

`emit.py` writes `out/context/<KEY>-context.md`: one document, identical for
every subtask on the story, carrying the glossary, the cited conventions, the
contracts, the ruled-out list, what was decided and what is deliberately still
open, and the shas it was all true at.

It is a separate artefact rather than repeated per brief for three reasons `[N]`:

1. **It is the dossier.** Facts that belong to the story, not to one subtask.
2. **One copy cannot disagree with itself.** Repeat a convention in seven briefs
   and the seventh will drift on the next re-refinement.
3. **It is a stable prefix.** Byte-identical across subtasks, so a runner that
   puts it first in every agent's context pays for it once - the same ordering
   rule the `fan-out` skill documents for its shared brief. Order it: shared
   context, then the subtask brief, then the work. Never interleave.

The rendered ticket carries a one-line pointer to it and nothing more. Preflight
commands and `stop_and_ask` stay in the brief: a developer reading the ticket
already knows to check whether the file moved, and the ticket is theirs to read.

---

## 10. The loop back

An implementor - human or agent - is the last reader of the refinement and the
first to find out where it was wrong. That discovery is worth more than anything
else produced downstream, and it has exactly one route home: the next bundle.

Ask for it explicitly. What comes back should be:

- **a failed preflight** - the anchor moved; the citation needs re-establishing
- **a convention that was not true** - it was a training prior with a citation
  that did not say what it was claimed to say, or the house changed
- **a `stop_and_ask` that fired** - a question refinement should have asked
- **an absence that was wrong** - something in `ruled_out` that does exist

Fold it in with `emit.py --previous`, which separates what changed from what is
new. A `ruled_out` entry that turned out to be false is the highest-value
correction of the lot: it means a *search* was wrong, not a sentence, and the same
search will be run again on the next story in that area.
