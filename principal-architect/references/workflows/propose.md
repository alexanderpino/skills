# Workflow: propose

Plan one architecture change and write it down so it can be reviewed before anything
is applied: the change record, the decision records it needs, and the tasks that will
carry it out.

**Planning boundary.** This workflow writes planning artifacts only: the change folder
(`<root>/changes/<id>/`) and the decision records the CLI mints into `decisions/`
with status `proposed` (ADR) or `draft` (RFC). It does not edit living documents
(PRD, HLD, SD, SAD, AD, glossary, index), the decision log, or code — even when the
request asks to build or fix something. When the planning is complete, stop and wait
for a new request before starting the apply workflow.

`ARCH` below means `python3 <skill-dir>/scripts/arch.py`, where `<skill-dir>` is the
directory holding this skill's SKILL.md. Run it from the repository root and always
pass `--json`. The CLI is the source of truth for state; never infer what it reports.

**Input**: a change id in kebab-case, or a description of the change.

## Steps

1. **Understand the request**

   If no clear input is given, ask: "What change do you want to plan? Describe what
   you want to build or decide." Derive a kebab-case id from the answer
   ("rotate API keys" → `rotate-api-keys`).

   Ask before going further when an ambiguity would materially change scope, a
   published interface, a quality target, or which system owns the change. For
   smaller unknowns, decide later whether to derive, ask, or record an assumption
   (step 6).

2. **Resolve the docs root**

   ```bash
   ARCH context --json
   ```

   - `state: "no_docs_root"` → stop without creating anything; offer the bootstrap
     workflow.
   - The id is already in `changes` → ask whether to continue that change or pick a
     new id. Never overwrite one.

3. **Consult**

   Run steps 2–5 of the consult workflow (`references/workflows/consult.md`): what
   binds the change, read it from disk, conflicts, triage. Re-run `ARCH consult`
   rather than relying on an earlier result in the conversation; files may have
   changed.

4. **Apply the triage gate**

   - Archetype `trivial` → no change folder. Tell the user the change needs no
     documentation beyond fixing any line that is now wrong, and stop.
   - Any other archetype → continue. A `local` change may well end up with a single
     task; that is fine.

5. **Create the change**

   ```bash
   ARCH new <id> --title "<title>" --level <enterprise|solution|software> --archetype <archetype> --json
   ```

   Parse `path` and `created`. On `error: "change_exists"` go back to step 2.

6. **Fill `change.md`**

   Open `<path>/change.md` and fill every section; the template's guidance is in HTML
   comments and `<placeholders>`, which must all go.
   - **Front-matter.** `affects:` with the component names the records already use;
     `conflicts:` with every accepted ADR id step 3 found contradicted.
   - **Intent.** What and why, with driver IDs. No driver on record → say so and list
     it as a gap.
   - **Evidence.** What you read, as paths and `path:line`, split into observed and
     inferred. Derive from code, configs, tests and history before asking anyone.
   - **Decisions on record.** Each binding decision, honoured or contradicted.
   - **Triage.** Altitude, archetype, required artifacts, and the ones not needed.
   - **Assumptions and gaps.** Everything you could not derive and did not ask.
     Never fabricate a stakeholder, driver, or number to fill a section.

7. **Mint and write the decision records**

   For each decision the triage requires, choose the path from
   `references/governance.md`:
   - Significant but within one team → an ADR:
     ```bash
     ARCH record adr --change <id> --title "<decision as a noun phrase>" --json
     ```
   - Cross-team, enterprise, one-way door, or contested → an RFC now; the ADR is
     minted later from it (`ARCH record adr --from-rfc RFC-NNNN`) once it is approved:
     ```bash
     ARCH record rfc --change <id> --title "<proposal>" --json
     ```
   - The change contradicts an accepted ADR → supersede it:
     ```bash
     ARCH record adr --change <id> --title "<new decision>" --supersedes ADR-NNNN --json
     ```

   The CLI picks the number, writes the file from the template, sets the id, title,
   date, level and starting status, and adds the id to `records:`. Never number a
   record yourself or edit its `status:`. Fill `satisfies:` with the `F.xx` / `Q.xx`
   the decision serves: it is the join between the decision and the behaviour, and the
   handoff workflow derives the implementation's requirements from it — a record
   without it hands over a change with no behaviour contract. Then fill the record at the returned `path`:
   Nygård sections (`references/conventions.md` §3), MADR optional sections only when
   the decision needs them, the two §1 questions answered separately when it keeps,
   works around or replaces an existing design, and numbers with their model
   (`references/quantitative-methods.md`). For any HLD or SAD the change will alter,
   plan the threat model and FinOps updates; they are never optional.

8. **Write `tasks.md`**

   One checkbox per concrete edit, numbered `N.M`, each naming its target in
   backticks (a path relative to the docs root, or to the repository for code) and
   what changes there:
   ```
   - [ ] 2.1 Update `software/SD-api-keys.md` §3: add the rotation sequence
   - [ ] 3.1 Mark the rotation entry point in `src/keys.py` with `ARCH-REF: ADR-0002`
   ```
   Derive the tasks from SKILL.md Steps 2–4: the living documents the triage names,
   the `ARCH-REF:` markers where a decision is enacted, the index row for any new
   document, `AD.md` for any new stakeholder, concern or view, and every
   corresponding view the AD §7 rules tie to what changes. Keep the groups the triage
   calls for and delete the rest. Do not add tasks for the decision log or for
   accepting records; archive does both.

9. **Loop on status until ready**

   ```bash
   ARCH status --change <id> --json
   ```

   - `state: "blocked"` → fix every item in `missing` (an unfilled section, an empty
     `affects:`, a required record that does not exist, a record with placeholders,
     an unresolved conflict, no tasks), then run status again.
   - `state: "ready"` → planning is complete; go to step 10.
   Never edit a front-matter field just to make a check pass. If an item cannot be
   resolved without the user, ask.

10. **Present and stop**, in the format below.

## Output

```
## Proposed: <id> — <title>

**Location:** <path> · **Altitude:** <level> · **Archetype:** <archetype>

### Decisions
- ADR-NNNN (proposed): <the decision in one line>
- Supersedes ADR-NNNN: <why it no longer holds> (only if any)

### What will change
<the task groups in two or three lines; the full list is in tasks.md>

### Assumptions and gaps
<the visible list from change.md, or None>

The plan is ready for review. When it is approved, run `/arch-apply <id>`.
```

## Guardrails

- Planning only. An implementation instruction in the request does not carry over;
  do not edit living documents, the decision log, or code here.
- Every planning artifact is re-read from disk before the next one is written.
- Ask about anything that would change scope, a published interface, a quality
  target, or ownership; record smaller unknowns as assumptions.
- Records start `proposed`/`draft`. Only archive accepts them.
- One change per run. If the request is really two changes, say so and plan the
  first.
