# Refinement wishes

<!--
  What a calling skill hands to story-refinery, next to the item to refine. Keep it
  in your own skill as `refinement.md` (or any name) and pass its path:

      /story-refinery ABC-123 --wishes path/to/refinement.md

  story-refinery reads every wish, applies it under its precedence (invariants >
  the user in the session > these wishes > its own defaults), writes the mechanical
  ones into refinery.yaml so its gates see them (TLR006), stamps this file into the
  bundle so a later reader can tell what steered the run (TLR007/TLR008), and hands
  back out/handback.json with what was applied, what was refused, and whether the
  item is ready. Everything below is optional; delete what you do not need.
-->

## Who we are

- Calling skill: `<name>` - story-refinery records it as `tailoring.source`.
- Language: tickets are written in <Dutch / English>.

## Owners

Who answers what. A question without an owner is answered by "the team", which
is nobody.

| Question about | Ask | Fallback |
|---|---|---|
| <scope, priority, what was promised> | <name, role> | <name> |
| <domain rules, edge cases> | <name, role> | <name> |
| <data, migrations, retention> | <name, role> | <name> |
| <on-call, rollout, alerting> | <name, role> | <name> |

## Mechanical rules

Each of these becomes a `refinery.yaml` key before anything else runs; state
them as rules and story-refinery sets the key.

- Subtasks are at most <0.5> days and at least <0.25>.
- Done means `<make test>` passes for feature and migration subtasks; lint is
  `<make lint>`.
- Tracker: <Jira Cloud, project ABC>, subtasks are `<Sub-task>`, the brief goes in
  <an attachment>.
- Repos: <api at ../api, web at ../web>.
- Labels: `<prod-issue>` means an escaped defect - bugfix profile, reproducing
  test mandatory; `<team-...>` labels carry no refinement meaning.
- Quality attributes that must be answered with a number here: <performance,
  failure>.

## What to skip, and why

Any gate may be switched off; saying so is not optional (TLR005).

- <Skip the adversarial panel on items under 2 subtasks - rubber-duck instead.>
- <Do not run evidence.py scan on the `legacy/` tree; cite from the manifest.>

## Always ask

Questions story-refinery must put to the owners on every item here, in addition
to what the intake finds missing:

- <Which customer commitment does this touch, and by when?>
- <Is there a feature flag, and who removes it?>

## House conventions not in the code

Only the ones that cannot be cited from a file; anything in code is cited from
`path:line` by Phase 2 instead.

- <Money is minor units in transport, Decimal in domain code.>
- <A feature flag gets a removal ticket in the sprint it is created.>

## Escalate rather than assume when

- <The answer changes money, a customer commitment, or anything with a legal deadline.>

## What to hand back

story-refinery always writes `out/handback.json`. Say here if the calling skill
needs anything else on top - <a Dutch summary block; the subtask list as a
checklist; nothing else>.
