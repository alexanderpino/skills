---
name: software-studio-builder
description: >-
  Research a software domain and build a Claude Code "studio" for it: a ready-to-clone
  repository template with subagents in three tiers and full reporting lines, skills for
  every workflow phase, path-scoped coding rules, hooks with a deny list, review gates
  owned by named roles, a workflow catalog, rigor modes and self-tests — for
  administrative and business software (ERP, CRM, HR and payroll, finance, case
  management, public-sector admin) or any other kind of software. Two stages with a hard
  stop between them: parallel research into a sourced ledger feeds a proposal the user
  approves; only then is the template generated, layer by layer, and verified by a checker
  whose every check has been watched fail. Use when the user wants a studio, an agent team
  or org chart of Claude Code agents, or a .claude/ setup of agents, skills, rules and hooks
  for a kind of software or team — even if they only say "set up Claude Code for our
  <domain> team". Not for building the business application itself, and not for writing
  one agent or one skill.
argument-hint: <domain> [target-dir]
metadata:
  invocation: auto
---

# Software Studio Builder

Build a **studio**: a ready-to-clone repository that turns Claude Code into a coordinated
delivery organisation for one kind of software. A studio has a `CLAUDE.md`, a
`project.yaml` with a rigor dial, 10–80 subagents in three tiers with explicit reporting
lines, skills for each workflow phase, path-scoped coding rules, hooks, review gates owned
by named roles, document templates, a workflow catalog that `/next-step` and `/gate-check`
read, and self-tests.

A studio's **machinery** is the same for every domain, and this skill ships it as a
skeleton (`assets/skeleton/`). Its **content** is not: the roles, artifacts, phases, rules,
gates and stacks have to be researched for each domain, and that research is what this
skill does. Read `references/anatomy.md` for the layer-by-layer split and the building
blocks every domain must fill.

```
intake ─► research (parallel lanes → ledger) ─► proposal ─► check + blind critic ─► ■ USER APPROVES ■
                                                                                          │
                     handover card ◄─ verify (checker + self-tests) ◄─ generate layer by layer (ask each)
```

Before **each** of the two stops, and before you report any smaller job as finished, the
**validation stage** runs: it is triggered by your belief that you are done, and it tests
that belief (see "Validation" below).

## Non-negotiables

1. **Hard stop between the two stages.** `generate.py` refuses to run until
   `state.py approve RUN --by user` has recorded the user's approval. The approval pins the
   proposal's sha256, so any edit after approval needs a fresh approval. Never run
   `approve` on your own initiative. Run it only after the user has read `proposal.md`
   and said yes in their own words.
2. **Every proposal item is sourced or labelled.** Each role, step, artifact, skill, rule,
   gate and stack cites one of three things: a ledger claim (`C014`), `USER: <their
   decision>`, or `NOT SOURCEABLE: <what was searched>`. Never fill a gap from memory and
   present it as fact. `proposal.py check` fails on an empty `claims` list and raises a
   concern for anything resting only on weak support.
3. **A check that could not run says `NOT ASSESSED`, and says why.** This applies to every
   script here and to every skill and gate this skill generates. NOT ASSESSED ranks above
   PASS and below FAIL.
4. **Ask before every write outside `<target>/.ssb/`.** Show a `--dry-run` for each layer,
   ask "May I write layer `<layer>` (N files) to `<target>`?", and write on a yes.
5. **Never overwrite a person's edit.** The generator records the sha256 of every file it
   writes. On a later run, a file still matching that hash is updated (`UPDATE` — the
   proposal changed, not a person); a file someone edited is reported as `KEEP` and left
   alone for the user to merge.
6. **No commits and no pushes** unless the user asks.
7. **"Done" is validated before it is said.** The moment you believe the work is finished —
   at the proposal stop, at the handover, or at the end of a small edit — run the
   validation stage (`references/validation.md`), including a critic whose only job is to
   refute the changes. Tell the user it is done only in a
   message that quotes the `VALIDATE <stop>: <verdict>` line and names every FAIL,
   NOT ASSESSED and CONCERNS item.
8. **A refused tool is an answer, not an obstacle.** If a tool, hook or permission refuses
   a write, report it; do not route the same write through another tool.
9. **Agent-facing files are written for agents.** Nearly every `.md` a studio contains —
   agents, skills, rules, gates, templates, `CLAUDE.md` — is read by an agent at a specific
   moment, with no memory of this run, and acted on literally. Write them, and the proposal
   text that fills them, by `references/writing-for-agents.md`: lead with the action,
   self-contained, exact paths and output formats, a word for the unknown, a length budget
   per reading moment. Only `proposal.md`, `research/report.md` and the handover card are
   written for the user.

## The run at a glance

| Phase | What happens | Commands (all stdlib Python, in `scripts/`) |
|---|---|---|
| 0. Intake | One round of questions → `state.json` | `state.py init RUN --domain … --target T` · `state.py intake RUN --json …` |
| 1. Research | Explore what exists; 3–5 parallel research lanes write the ledger | `ledger.py init / add-source / add-evidence / add-claim / not-sourceable / check / show` |
| 2. Proposal | Write `proposal.json`, check it, render it, run a blind critic, then **hard stop** | `proposal.py init / check / render / derive` · `state.py approve` |
| 3. Generate | Dry-run each layer, ask, write | `generate.py T --dry-run` · `generate.py T --layer <layer>` |
| 4. Validate | **Whenever you think you are done** (before the hard stop, before the handover, after a small edit): mechanical checks incl. the checker and the studio's tests; a trial run of the studio; the final message drafted; a critic that tries to refute every change; a validator that checks the request, the stop's acceptance criteria and the message; re-check — then report and mark | `validate.py T` · `trial.py brief T` → `.ssb/trial.md` · `.ssb/final-message.md` · `validate.py T --changes` → critic → `.ssb/refutation.md` · validator → `.ssb/validation.md` · `validate.py T` · `validate.py T --mark-reported` |

`RUN` is always `<target>/.ssb/`. It holds `state.json`, `research/` (the ledger),
`proposal.json`, `proposal.md`, `critic.md`, and the validation record
(`refutation.md`, `validation.md`, `validation.json`, `baseline.json`). Paths below are relative to this skill's folder;
call the scripts as `python3 <skill>/scripts/<name>.py`.

## Phase 0 — Intake

Read `references/intake.md`. Ask **one round** of questions, each with a recommended answer
the user can accept with "you pick":

- the domain and its users
- regulation that applies
- known or preferred stacks
- team shape
- the default rigor
- generate MVP or full
- the target directory (default `./<slug>-studio`)

Also ask whether an existing codebase, docs or agent setup of theirs can be read first.
Record the answers with `state.py intake`.

If a domain pack exists, read it, for example `references/domain-packs/business-software.md`.
A pack holds **hypotheses to verify**, not facts to copy.

## Phase 1 — Explore and research

Read `references/research-protocol.md`. In short:

1. **Explore what exists first.** Read the user's codebase, docs and any agent setup they
   already have (`.claude/`, `CLAUDE.md`, CODEOWNERS, team handbooks). What already works
   for them is evidence; the studio should fit it, not replace it.
2. **Fan out** 3–5 research lanes as parallel subagents, all `Agent` calls in one message.
   The default lanes are:
   - `roles`: job titles, reporting lines, who decides what
   - `process`: lifecycle, phases, standards bodies, gates
   - `artifacts`: the documents the domain produces and their sections
   - `regulation`: obligations, audit, privacy, retention
   - `stack`: platforms, toolchains, code and test layout, the domain's known failure modes

   Each lane gets the brief in `research-protocol.md`, writes **only** through `ledger.py`,
   and returns at most 300 words that list its claim ids.

   **No Agent tool in this session?** Run the lanes yourself, one after another, with the
   same brief and budget, and say so in `report.md`'s Limitations. A wrong ledger entry is
   corrected with `--supersedes` — `ledger.py add-evidence … --supersedes E010` for a quote,
   `ledger.py add-claim … --supersedes C004` for a claim — never by editing the file.
3. **Integrate.** Run `ledger.py check RUN/research`. FAIL means fix the ledger.
   CONCERNS means read every unverified claim and decide whether to re-research it or carry
   it as weak. Write `RUN/research/report.md` with these sections: summary, roles,
   process, artifacts, regulation, stacks, open questions, limitations.

Stop researching when every proposal section you will need has claims behind it, or when a
gap is recorded with `ledger.py not-sourceable`. Do not stop when it merely feels thorough.

## Phase 2 — Proposal (stage 1 output)

Read `references/proposal-spec.md`. It gives the JSON schema, the role anatomy and the
acceptance checklist.

1. `proposal.py init RUN --name … --slug … --domain …`, then fill `proposal.json` from
   the report.
2. **Roles follow the agent anatomy** (`references/anatomy.md`). Each role gets:
   - tier (director, lead or specialist)
   - `reports_to` (directors report to `user`)
   - `implements_specs_from`
   - `escalation` (`to` + `when`)
   - `siblings` and `coordinates_with` (`with` + `for`)
   - `owns_paths`, `skills`, `tools`, `model`/`effort`, `workflow` (question-first or implementation)
   - `responsibilities`, domain `standards` sections, `must_not`
   - `claims`

   Every text field here — descriptions, responsibilities, standards, `must_not`, skill
   steps, rule bullets, gate prompts, section guidance — is rendered verbatim into files an
   agent reads cold. Write it for that agent (`references/writing-for-agents.md`);
   `proposal.py check` fails on conversation-dependent phrases and leftover placeholders.

   **Delegates to** and **Gates owned** are *derived*: from who reports to the role, and
   from each gate's `owner`. They are never stored, so they cannot disagree with their
   source. Use `proposal.py derive RUN <role>` to see a role's full reporting line.
3. `proposal.py check RUN` loops until there is no FAIL. Then `proposal.py render RUN`.
4. **Blind critic.** Spawn one subagent with only `proposal.md`, `research/report.md` and
   the proposal criteria P1–P10 from `references/acceptance.md`, not your reasoning. Ask it for the
   five most serious defects and have it write them to `RUN/critic.md` (first line
   `independent: yes`). Fix them, or list each in `open_questions` with why it stands.
   Without an Agent tool, do the critique as a separate pass yourself and write
   `independent: no` as the first line — validation then reports it as a concern.
5. **Validate** (Phase 4 below) — at the `proposal` stop. Fix every FAIL first.
6. **Hard stop.** Show the user a summary of `proposal.md`:
   - the roster tree
   - the phases
   - the concerns from `check`
   - the critic's findings
   - the open questions
   - the MVP cut (`scope`)
   - the `VALIDATE proposal: <verdict>` line and its non-PASS items

   Ask them to approve, edit or reject it. On "approve", run
   `state.py approve RUN --by user --note "<their words>"`. On edits, change the JSON,
   re-check, re-render and ask again.

## Phase 3 — Generate (stage 2)

Read `references/generation.md`. The layers run in this order:

`core → agents → skills → rules → templates → gates → catalog → hooks → tests`

For each layer: run `generate.py T --dry-run --layer <layer>`, show the file list, ask, then
run `generate.py T --layer <layer>`. The generator refuses in these cases:

- the proposal is unapproved, or was edited after approval
- the proposal has a structural failure
- the MVP cut would orphan something, for example a generated role reporting to a deferred
  one or a catalog step pointing at a deferred skill

When it refuses, report its exact lines. Do not work around them.

What each layer contains:

- **core**: `CLAUDE.md`, `project.yaml`, `.gitignore`, docs, `resolve_config.py`,
  `artifact_check.py`, `check_template.py`, the stack table, and the research record copied
  into `docs/studio-research/`
- **agents**: one file per role with every section and a Delegation Map, plus
  `agent-roster.md`, `agent-models.yaml` and `coordination-rules.md`
- **skills**: four baseline skills (`/start`, `/next-step`, `/gate-check`,
  `/project-settings`) plus the proposal's skills
- **hooks**: the hook scripts and `settings.json`, which has a deny list

## Phase 4 — Validate: whenever you think you are done

Read `references/validation.md`. This stage is triggered by the belief that the work is
finished — at the proposal stop, after generating (the handover), and after any smaller job
such as "add this rule". That belief is the hypothesis; this stage tests it — against
explicit criteria, against what you are about to tell the user, and, for a studio, against
actual use.

1. **Mechanical:** `validate.py T`. It detects the stop from `state.json` and runs that
   stop's checks. At the proposal stop: ledger chains, report citations, proposal check,
   `proposal.md` identical to a fresh render, nothing generated early, critic on record. At
   the generated stop: approval valid for the current proposal, files generated from it, all
   layers present, `check_template.py` (13 checks, `references/verification.md`), the
   studio's own tests, no drift. A FAIL goes back to the phase that owns it — fix the
   proposal or the skeleton, never the generated files.
2. **Trial and draft.**
   - *Generated stop:* trial-run the studio. `trial.py brief T` picks a gate owner, an
     implementing specialist and a catalog skill, and prints a brief for each with the
     expected behaviour. Spawn the briefs (in one message; each works in a scratch copy of
     the studio) and record what happened in `RUN/trial.md` — one row per pick: *Pass*,
     *Fail* or *Could not test*.
   - *Every stop:* write the message you intend to send the user — the summary, or the
     handover card — to `RUN/final-message.md`, with the verdict line still
     `VALIDATE <stop>: <pending>`. Its numbers and claims are checked against the files.
3. **Refutation critic + validator, in parallel** (two `Agent` calls in one message, neither
   given your reasoning):
   - The **critic** gets the change set from `validate.py T --changes` and the stop's
     criteria (`references/acceptance.md`), and one job: **prove each change wrong**. It
     writes `RUN/refutation.md` — one row per attempt, *Refuted*, *Not refuted* or
     *Could not test* — and a `REFUTATION:` verdict. A Refuted row fails the stage; a
     changed path it never attacked is NOT ASSESSED.
   - The **validator** gets the user's request **quoted verbatim**, the stop's criteria
     (`references/acceptance.md`: P1–P10 or G1–G10), `final-message.md`, the deliverable's
     paths and the `validate.py` output. It writes `RUN/validation.md`: one row per request
     item, one per criterion id, one per factual claim in the message (`M1…`), and a
     `VALIDATION:` verdict.

   No Agent tool: do the trials and both reviews yourself as separate passes from disk,
   marked `independent: no`; each is then capped at CONCERNS.
4. **Re-run** `validate.py T`. A refuted change, a failed trial, a wrong message claim or any
   FAIL goes back to the phase that owns it, and the fix is itself a change the next critic
   attacks. At most three rounds; after that, report what still fails as it is.
5. **Report, then mark.** Send `final-message.md` with only its verdict line filled in from
   `validate.py`, naming every FAIL, NOT ASSESSED and CONCERNS item. Then run
   `validate.py T --mark-reported`, so the next critic attacks only what changes after this
   point.

A change after validation makes the trial, the message and both reviews stale; `validate.py`
notices by file times and reports them NOT ASSESSED until they run again.

The blind critic in Phase 2 and the refutation critic here are different jobs: the first
looks for the proposal's biggest design defects; the second tries to break the specific
changes made since the last time you reported.

At the generated stop, end with the handover card:

```
STUDIO: <name> at <target>
Built:          <n> agents (<d> directors / <l> leads / <s> specialists), <k> skills, <r> rules, <g> gates, <p> phases
Validation:     VALIDATE generated: <verdict> · check_template <…> · studio-tests <ok|failed> · trial <Pass|…> · refutation <SURVIVED|…> · review <independent|self>
Not assessed:   <each NOT ASSESSED check or claim, by name — or "none">
Weakly sourced: <items resting on unverified / NOT SOURCEABLE support — or "none">
Deferred:       <scope.later and mvp:false items>
Kept (not overwritten): <KEEP files — or "none">
Next: open Claude Code in <target> and run /start. Not yet run by a person.
```

## Resuming

`state.py show RUN` prints the phase, intake, approval validity and the layers still to
generate. A `.ssb/` folder in the target means a run exists: resume it, never start over.
After a compaction, re-read `state.json`, `research/report.md` and `proposal.md` before
doing anything.

## Files

| Path | Read when |
|---|---|
| `references/intake.md` | Phase 0 — the questions and their defaults |
| `references/research-protocol.md` | Phase 1 — lanes, the subagent brief, tiers, stop rules |
| `references/anatomy.md` | Any time — what a studio is made of, what is machinery vs. content, the building blocks to research |
| `references/proposal-spec.md` | Phase 2 — schema, role anatomy, acceptance checklist |
| `references/generation.md` | Phase 3 — layers, file formats, refusals, KEEP handling |
| `references/validation.md` | Phase 4 — every time you think you are done: the checks, the trial, the message, the critic and validator briefs, rounds |
| `references/acceptance.md` | Phase 2 critic and Phase 4 — what good means at each stop (P1–P10, G1–G10) |
| `references/verification.md` | Phase 4 — the checker reference: what each of C01–C13 proves and what it cannot |
| `references/writing-for-agents.md` | Phase 2 and 3 — who reads each generated file, when, and how to write it for that agent |
| `references/principles.md` | When designing anything new for a studio — the rules every generated piece obeys |
| `references/domain-packs/business-software.md` | Business and administrative domains — starting hypotheses |
| `scripts/` | `ledger.py`, `proposal.py`, `state.py`, `generate.py`, `check_template.py`, `trial.py`, `validate.py` (each has `--help`) |
| `assets/skeleton/` | The domain-agnostic machinery copied into every studio |
| `tests/fixtures/hr-payroll/` | A complete worked proposal (placeholder sources) — the shape to copy |

## Anti-patterns

- **Generic roles with domain names.** "Backend engineer, frontend engineer, QA" with
  the domain's name in front is not research. Derive roles from the domain's real job
  titles and decisions — who owns the payroll rules, who signs off a period close.
- **One agent per job title.** A role exists if it owns decisions or paths no other role
  owns. Merge the rest. 10–15 roles for an MVP is plenty.
- **A flat roster.** Every non-director reports to someone exactly one tier up or more.
  Every lead has reports. Every escalation names a reason.
- **Unsourced regulation.** Never state an obligation, a rate or a deadline from memory.
  Write `NOT SOURCEABLE` and let the gap show.
- **Approving on the user's behalf.** Silence, "looks fine so far" or a dismissed question
  is not an approval.
- **Declaring done from memory.** "I generated it and the checker passed earlier" is not
  validation. Run Phase 4 on the files as they are now, and quote its verdict.
- **A friendly critic.** Briefing the critic with why each change is right turns it into a
  second author. Give it the change list and the files, and let it try to break them.
- **Editing generated files to make the checker pass.** Fix the proposal and regenerate,
  or fix the skeleton. The checker guards the template and is not an obstacle to it.
