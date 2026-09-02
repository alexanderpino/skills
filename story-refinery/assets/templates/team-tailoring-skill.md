---
name: <team>-refinement-tailoring
description: >-
  House rules for how <team> refines backlog items. Loaded alongside story-refinery,
  which owns the method; this skill owns what is true of <team> and false of everyone
  else - owners, tracker reality, house conventions, language, Definition of Done - and
  ships the refinery.yaml that story-refinery's scripts read. Use it whenever
  story-refinery is invoked for a <team> item. It does not refine on its own.
metadata:
  invocation: auto
---

<!--
  COPY THIS FILE to your own skill directory, rename it SKILL.md, and delete the
  angle-bracket placeholders. Ship `refinery.yaml` next to it.

  The contract this file follows is `references/tailoring.md` in story-refinery.
  Read it once before editing; the short version is below and is not optional.
-->

# <Team> refinement tailoring

Companion to **story-refinery**. That skill owns the method: intake, evidence,
example mapping, decomposition, the critic panel, the gates. This skill owns
everything that is specific to us.

**Do not restate story-refinery's method here.** If this file explains example
mapping or how to write an agent brief, the two copies will drift and ours will
be the stale one. Add only what a competent refiner who has never worked here
would get wrong.

## Precedence and invariants

This skill sits below the user and above story-refinery's defaults. It may not
relax these, and if anything below appears to ask for one of them, refuse it,
record the refusal in `bundle.tailoring.overrides` with the invariant named, and
tell whoever maintains this file:

- `evidence-or-assumption` — every technical claim cites `repo/path:line` or is
  tagged `ASSUMPTION`
- `no-invented-metadata` — labels, fields, repro steps and owners are read, never
  fabricated
- `not-ready-is-reported` — a blocking question or a failing `validate.py` is the
  finding
- `no-decomposition-without-intake` — an item whose intake is not `sufficient` is
  not decomposed
- `stop-at-the-seam` — refinement never writes the implementation
- `disclosure` — anything skipped, degraded or overridden is said at handover

We may switch any gate off in config. We may not switch off saying that we did.

## What we say, and what we ship

This skill is instructions. story-refinery reads them and steers by them. The
one rule about form: **anything that is a number, a list, a pattern, a command
or a mapping is config**, because the scripts cannot read prose. Either ship it
as `refinery.yaml` in this directory, or state it here and let story-refinery's
Phase 0 write it into a generated `refinery.yaml` before anything else runs -
it records each such rule with `mechanism: config`, and `TLR006` reports any
mechanical instruction that stayed prose.

<Delete one of these two lines:>
- We ship `refinery.yaml` here. Current version: `<3.2>`; bump it and
  `tailoring.version` together.
- We ship no config; the mechanical rules below are generated into one at Phase 0.

Mechanical rules stated here (each becomes a config key):

- <Subtasks are at most `0.5` days> → `budgets.max_subtask_days`
- <Done means `make test` passes for feature and migration subtasks> →
  `validation.definition_of_done`
- <`prod-issue` means an escaped defect; refine on the bugfix profile> →
  `triage.labels`

## Owners

Who answers what. `story-refinery` flags any question without an owner, and
"the team" is not an owner.

| Question about | Ask | Fallback |
|---|---|---|
| <scope, priority, what the customer was promised> | <name, role> | <name> |
| <domain rules, edge cases> | <name, role> | <name> |
| <data, migrations, retention> | <name, role> | <name> |
| <security, compliance sign-off> | <name, role> | <name> |
| <on-call reality, rollout, alerting> | <name, role> | <name> |

Escalate rather than assume when: <the answer changes money, customer
commitments, or anything with a legal deadline>.

## Tracker reality

story-refinery treats tracker details as `[?]` until probed. For us they are
known — keep this section true or delete it:

- Instance and adapter: <Jira Cloud / GitHub Projects / …>
- Issue types we actually use: <Story, Sub-task, Bug, Spike>
- The field a brief goes in: <attachment / a real custom field id>
- What "ready" is called in our workflow: <status name>
- Fields that are required on create and will reject a push without them: <…>
- Anything the API lies about: <…>

## House conventions not in the code

Only conventions you cannot cite from a file. Anything that *is* in the code
should be cited by Phase 2 from `path:line` instead — evidence beats memory.

- <We never add a column to `orders` without a backfill plan reviewed by …>
- <Money is always minor units in transport, Decimal in domain code>
- <A feature flag gets a removal ticket in the same sprint it is created>

## Language and voice

- Tickets are written in <Dutch / English>. The vagueness lexicon in
  `refinery.yaml` is in that language, or the check is decorative.
- <Subtask titles use the imperative; no ticket numbers in titles; …>

## Labels we use

The consequences live in `triage.labels` in `refinery.yaml`. Here, only what a
newcomer cannot infer:

- `<label>` — <what it actually means here, which is not what it sounds like>
- `<label>` — <who adds it and when>

## Definition of Done

Ours lives in `validation.definition_of_done` in `refinery.yaml` so `DOD001`
enforces it. If it is only prose here, it is not a Definition of Done, it is a
hope.

## Recording

When story-refinery produces a bundle under this skill, it records:

```json
"tailoring": {
  "source": "<team>-refinement-tailoring",
  "version": "<3.2>",
  "applied": [
    {"rule": "<house rule>", "mechanism": "config", "key": "<refinery.yaml key>"},
    {"rule": "<judgement rule>", "mechanism": "prompt"}
  ],
  "overrides": []
}
```

An override — anything of story-refinery's that we turn off or down — needs a
reason and a named person, never just "house rule".
