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
