# Workflow: archive

Close a change once its work is applied and verified: record the decisions as made,
bring the decision log in line, and move the change folder to
`changes/archive/<date>-<id>/`, where it stays as the history of why the docs read the
way they do.

**Confirmation boundary.** Accepting an ADR makes it immutable history. The CLI shows a
dry run first; the archive itself runs only after the user has said yes, in a message
of their own, to that plan.

`ARCH` below means `python3 <skill-dir>/scripts/arch.py`, where `<skill-dir>` is the
directory holding this skill's SKILL.md. Run it from the repository root and always
pass `--json`. The CLI is the source of truth for state; never infer what it reports.

**Input**: optionally a change id. If none is given, infer it from the conversation;
if that is ambiguous, list the changes and ask.

## Steps

1. **Select the change**

   With an id, use it. Otherwise run `ARCH list --json`: one active change → use it;
   several → ask which. Announce: "Archiving change: <id>".

2. **Check the state**

   ```bash
   ARCH status --change <id> --json
   ```
   - `blocked` → stop; planning is incomplete (propose workflow).
   - `ready` or `in_progress` → show the open tasks and ask whether to archive anyway.
     Continue only on an explicit yes, and pass `--allow-incomplete` in step 5.
   - `archived` → say where it is and stop.
   - `all_done` → continue.

3. **Verify**

   Run the verify workflow (`references/workflows/verify.md`) in full unless it ran
   in this conversation after the last edit to the change's files. Any CRITICAL issue
   → stop and report it. The CLI re-runs the mechanical gate in step 4 and refuses on
   CRITICAL issues anyway; the judgement gate is yours.

4. **Settle how each decision was made, then dry-run**

   For every record in `records` still `proposed` or `draft`, ask the user, or take it
   from the PR or board outcome if they already said:
   - **Accepted** (reviewed on the PR, or approved by the board) → the default.
   - **Still awaiting the board** → archive with `--leave-proposed`; the record stays
     `proposed` and the board's outcome is recorded later.
   - **Rejected** → do not archive. The living docs now describe a design that was
     turned down; revert the change or re-plan it in the propose workflow.

   Then:
   ```bash
   ARCH archive --change <id> [--leave-proposed] [--allow-incomplete] --json
   ```
   Parse `refused`, `refusals`, `plan`, `implementation`. Refused → report each refusal
   and stop. Otherwise show the `plan` lines to the user and ask: "Archive <id> with
   these changes?" The plan names the state of any hand-over (an OpenSpec or spec-kit
   change still open, a seed behind the record). That is information for the user, not
   a refusal: the decision is accepted when it is made, and delivery is tracked on the
   implementation side (handoff workflow, "Two lifecycles, one visible link").

5. **Archive, on the user's yes**

   ```bash
   ARCH archive --change <id> --yes [--leave-proposed] [--allow-incomplete] --json
   ```
   Parse `applied`, `archived_to`, `log_changes`, `lint_after`. If `lint_after.exit`
   is not 0, report the errors: the archive happened, and the tree needs a fix before
   CI will pass.

6. **Report**, in the format below.

## Output

```
## Archived: <id> — <title>

**Archived to:** <archived_to>
**Decisions:** ADR-NNNN accepted · ADR-MMMM superseded by ADR-NNNN · RFC-NNNN accepted
**Decision log:** <log_changes, or "already in sync">
**Validator after archive:** <clean | n error(s), listed below>
```

## Guardrails

- Never run `--yes` before the user has seen the plan and said yes.
- Never archive with CRITICAL issues, and never with a rejected decision.
- Never imitate the archive by hand: no editing `status:` fields, the decision log, or
  moving the folder yourself. The CLI keeps them consistent with each other.
- Never delete a change folder; the archive is the history.
- One change per run.
