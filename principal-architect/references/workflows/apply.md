# Workflow: apply

Carry out a planned change, one task at a time: update the living documents, place
the `ARCH-REF:` breadcrumbs, keep the index and AD current. SKILL.md Steps 2–4,
driven by the task list the propose workflow wrote.

**Scope boundary.** Edit only what a task names. Work the tasks call for but do not
describe is surfaced and agreed before it is done, then added to `tasks.md` so the
record stays true. Records keep their `proposed`/`draft` status, and the decision log
is left alone; archive owns both.

`ARCH` below means `python3 <skill-dir>/scripts/arch.py`, where `<skill-dir>` is the
directory holding this skill's SKILL.md. Run it from the repository root and always
pass `--json`. The CLI is the source of truth for state; never infer what it reports.

**Input**: optionally a change id. If none is given, infer it from the conversation;
if that is ambiguous, list the changes and ask.

## Steps

1. **Select the change**

   With an id, use it. Otherwise run `ARCH list --json`: one active change → use it;
   several → ask which. Always announce: "Using change: <id>" and how to pick another
   (`/arch-apply <other-id>`).

2. **Check the state**

   ```bash
   ARCH status --change <id> --json
   ```

   Parse `state`, `missing`, `records`, `progress`, `tasks` (each with `text`,
   `done`, `source`, `line`, `paths`), `next`.
   - `blocked` → show `missing` and stop. Planning is incomplete; it is finished in
     the propose workflow, not patched here.
   - `not_needed` → the change is trivial; say so and stop.
   - `archived` → nothing to apply; stop.
   - `all_done` → every task is done; go to step 7.
   - `ready` or `in_progress` → continue.

3. **Load the context, from disk**

   Read `change.md`, every record in `records`, and every document a pending task
   names. Then re-check what binds the change:
   ```bash
   ARCH consult --affects <the change's affects> --json
   ```
   If `binding` now holds a decision that `change.md` "Decisions on record" does not
   mention (someone merged one since planning), pause: report it and ask whether the
   plan still holds.

4. **Show progress**

   ```
   ## Applying: <id> — <title>
   Progress: <done>/<total> tasks · next: <first pending task>
   ```

5. **Work the tasks, in order, until done or paused**

   For each task whose `done` is false:
   - Say which task you are on.
   - Make the edit, following the skill's rules for that artifact: templates and
     front-matter from `references/conventions.md` (stamp `updated:` on every living
     doc you change), C4 and diagrams from `references/mermaid-guide.md`, the threat
     model and FinOps sections for any HLD or SAD, and the house style when a
     `house-profile.yaml` exists. Place `ARCH-REF:` markers where a decision is
     enacted or could be violated, not on every line.
   - Before ticking, confirm the line at the task's `source`:`line` still reads as the
     task you did; if it moved, run status again and use the new line.
   - Change `- [ ]` to `- [x]` at that line, then run status again and confirm
     `progress.done` went up.

   **Pause when:**
   - a task is unclear → ask;
   - the edit shows the plan is wrong (a record's decision does not survive contact
     with the code, a conflict surfaces) → stop, describe it, and propose updating the
     change in the propose workflow;
   - the work needs edits no task describes, or you are tempted to narrow, defer, or
     drop part of a task to make it fit → surface it and ask; never absorb it silently;
   - a command fails or the docs are in a state the plan did not expect → report and
     wait.

6. **On a pause**, show the paused output below and wait.

7. **When every task is done**, run the verify workflow
   (`references/workflows/verify.md`) in full, including the judgement gate. Apply is
   not finished until verify has run and its result is reported.

## Output

During the work:
```
Working on task 2.1/3: <task text>
✓ done — <file> updated
```

On completion:
```
## Applied: <id> — <title>
**Progress:** <total>/<total> tasks ✓

### Done this session
- [x] <task>

### Verify
<the verify workflow's report>
```

On a pause:
```
## Paused: <id> — <title>
**Progress:** <done>/<total> tasks

### Issue
<what happened, with path:line>

**Options:**
1. <option>
2. <option>
3. Another approach

What would you like to do?
```

## Guardrails

- Keep going until every task is done or a pause condition holds.
- Tick a task only when everything it names is done, not when it is partly done.
- Use each task's `source` and `line` to tick exactly that checkbox.
- Never edit a record's `status:`, the decision log, or the change's front-matter to
  move the state forward.
- Honour the correspondence rules: when a view changes, every view, SD and diagram
  that corresponds to it changes in the same run, as its own task.
- Re-read a file from disk before editing it.
