# Acceptance criteria per stop

What "good" means at each stop, as numbered items. The **validator** (validation step 3)
writes one row per item for the stop it is validating, with evidence, in addition to the
rows for the user's request; `validate.py` (V90) reports **NOT ASSESSED** for any id it
does not find in `.ssb/validation.md`. The **refutation critic** may cite these ids in its
attacks. The Phase 2 design critic gets the proposal table.

Keep the ids stable — `validate.py` reads them from the tables below (`| P1 |`, `| G1 |`).
Add an item with the next free id; never renumber.

## Proposal stop

| Id | Criterion | How to check |
|---|---|---|
| P1 | `proposal.py check` has no FAIL; every CONCERN is fixed or listed in `open_questions` | run it; compare its CONCERN lines with `open_questions` |
| P2 | Every role traces to the domain's real work (claims), not to a generic role renamed | each role's claims resolve to ledger evidence about that role's work |
| P3 | The roster is a tree: one director per authority, every lead has reports, nobody reports sideways or down, directors escalate to the user, every escalation names a reason | `proposal.py derive` per role; the roster tree in `proposal.md` |
| P4 | Every phase transition that matters has a gate with a named owner; each gate's failing word means something in the domain (e.g. NON-COMPLIANT, REJECT) | the gates table against the phases |
| P5 | Every regulated obligation that binds code appears as a rule, a `must_not` or a standards section, and cites a primary source or says `NOT SOURCEABLE` | follow each regulation claim in `report.md` to where the proposal uses it |
| P6 | Every required catalog step produces an artifact that has a template | phases table against the artifacts table |
| P7 | Stacks have code and test roots; commands are present or deliberately empty | the stack table |
| P8 | The MVP cut is coherent: nothing generated depends on something deferred, and `proposal.md` shows the real cut | section 12 of `proposal.md`; `generate.py --dry-run` refuses an incoherent cut |
| P9 | Open questions are real decisions for the user, not research left undone | read each open question |
| P10 | Agent-facing text in the proposal is written for an agent reading it cold (`writing-for-agents.md`) | read three role descriptions and two skill step lists as that agent |

## Generated stop

| Id | Criterion | How to check |
|---|---|---|
| G1 | Every in-scope role has an agent file with `### When You Are Spawned` and a full Delegation Map | `check_template.py` C04/C13; open two agent files |
| G2 | The roster tree in `agent-roster.md` matches the proposal's roster | compare with `proposal.md` section 3 |
| G3 | Every required catalog step's skill and template exist, and the skill names the template it fills | C10; open the skills of two steps |
| G4 | Every gate is listed by its owner and in `gates.md` | C09 |
| G5 | `CLAUDE.md` counts and names match the files on disk | count `.claude/agents/*.md`; read the directors line |
| G6 | Hooks are wired in `settings.json` and the deny list is present | C02/C03 |
| G7 | At least three agent-facing files, read cold, can be acted on (`writing-for-agents.md`) | read one agent, one skill, one gate as the agent that receives it |
| G8 | Deferred items are absent from disk and listed as deferred where the studio mentions them | the manifest's `deferred`; grep their ids |
| G9 | The trial run passed: the picked agents and skill behave as their files promise | `.ssb/trial.md` (V26) |
| G10 | The research record (ledger, report, proposal) is copied to `docs/studio-research/` | list the folder |
