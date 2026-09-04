# Refinement wishes - team billing

The wishes the billing team's developer skill passes when it calls
story-refinery. This is the file `assets/examples/example-bundle.json` is
stamped with; its rules are the ones that bundle records under `tailoring`.

## Who we are

- Calling skill: `team-billing-refinement`, version 3.2.
- Language: tickets are written in English; Dutch is fine in questions.

## Owners

| Question about | Ask | Fallback |
|---|---|---|
| money, VAT, reconciliation | Marieke (Finance) | Sanne |
| scope, what the customer was promised | Sanne (Product) | Marieke |
| on-call, rollout, alerting | Joris (Platform) | the api channel |

## Mechanical rules

- Every feature and migration subtask runs the contract suite before it counts
  as done: `pytest tests/contract -q`.
- Subtasks are at most 1 day and at least a quarter.
- Tracker is Jira Cloud, project ABC; subtasks are `Sub-task`; the agent brief
  goes in an attachment.
- Repos: api at `../api`, web at `../web`.
- `production-issue` means an escaped defect: bugfix profile, reproducing test
  mandatory, the operator joins the panel.
- Performance, concurrency and failure are answered with a number or
  "unchanged", never prose.

## What to skip, and why

- Nothing. The full panel runs on every billing item; money is the reason.

## Always ask

- Who signs this off, and do they need evidence retained beyond the code change?

## House conventions not in the code

- Money is Decimal; round with `money.round_half_up`, never float arithmetic.
- A feature flag gets a removal ticket in the sprint it is created.

## Escalate rather than assume when

- The answer changes what a customer is charged, or touches a VAT filing.
