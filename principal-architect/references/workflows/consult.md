# Workflow: consult

Find out what already binds a piece of work before anyone plans it: the accepted
decisions it must honour, the documents it must keep consistent, and how much
documentation it actually needs. SKILL.md Steps 0–1, made repeatable.

**Read-only boundary.** This workflow reads and reports. It writes nothing: no change
folder, no records, no edits to docs or code — even when the request asks to build or
fix something. If the user asks to capture the outcome, that is the propose workflow;
say so and stop.

`ARCH` below means `python3 <skill-dir>/scripts/arch.py`, where `<skill-dir>` is the
directory holding this skill's SKILL.md. Run it from the repository root and always
pass `--json`. The CLI is the source of truth for state; never infer what it reports.

**Input**: a description of the intended work, optionally with the files or
components it touches.

## Steps

1. **Resolve the docs root**

   ```bash
   ARCH context --json
   ```

   Parse `state`, `root`, `root_resolved_by`, `records`, `documents`, `changes`,
   `has`.
   - `state: "no_docs_root"` → stop. Report where the docs would live
     (`root`, `root_resolved_by`) and that none exist yet. If the work is
     architecturally significant, offer the bootstrap workflow; do not create anything.
   - An entry in `changes` that matches this work → say so; the user may want to
     continue that change (apply) instead of starting fresh.

2. **Find what binds the work**

   When the work is already on disk (a branch with edits), run:
   ```bash
   ARCH consult --json
   ```
   When it is not yet written, name what it will touch:
   ```bash
   ARCH consult --paths <files it will change> --affects <components> --json
   ```
   Take component names from `records[].affects` in the `context` result (that is how the
   existing decisions name things) and from the HLD's building blocks, so the match is
   on the names the docs already use.

   Parse `decisions` (each with `status`, `binding`, `strength`, `match`),
   `documents`, `warnings`, `overlapping_changes`, `suggested_reads`.
   - `strength: "strong"` means the code itself says so (an `ARCH-REF:` marker).
   - `strength: "candidate"` is a token match on names or `affects:`. Read it and
     decide; a candidate is not a binding decision until you have.

3. **Read, in this order, from disk**

   Read every path in `suggested_reads`: the index, `AD.md`, the matched documents,
   then the binding decisions. Re-read from disk even if you saw a file earlier in the
   conversation. Then read the candidate decisions and drop the ones that do not bind.

4. **Check for conflicts**

   For each decision that binds, answer one question: does the intended approach
   honour it? A contradiction is never resolved by silence. Name the decision, the
   specific sentence the plan contradicts, and the two ways out: change the plan, or
   supersede the decision through the propose workflow.

5. **Triage**

   Pick the altitude (SKILL.md "Three altitudes"), then the archetype from the Triage
   tables, then list the artifacts that archetype requires and the ones it does not.
   Use the archetype names the CLI knows: `trivial`, `local`, `new-component`,
   `published-interface`, `significant`, `quality-target`, `stakeholder`, `feature`,
   `greenfield`, `capability`, `solution`, `process`, `migration`, `platform`,
   `evaluation`. When unsure whether the work is significant, read
   `references/significance.md`.

6. **Report and stop**, in the format below.

## Output

```
## Consult: <the work, in one line>

**Docs root:** <root> (<root_resolved_by>) · **Active changes:** <ids, or none>

### Decisions that bind this work
| ID | Status | Why it binds | Honoured? |
|----|--------|--------------|-----------|
| ADR-NNNN | accepted | marker src/x.py:12 | yes — <one line> |

### Documents to keep consistent
- `<path>` — <what in it this work touches>

### Conflicts
None. | ADR-NNNN: <the sentence the plan contradicts>. Ways out: change the plan,
or supersede ADR-NNNN (propose).

### Triage
**Altitude:** <level> · **Archetype:** <archetype>
**Needs:** <artifacts, one line of reason each> · **Does not need:** <artifacts, reason>

### Warnings
<consult warnings: markers to superseded or missing records, overlapping changes; or None>

**Next:** No documentation needed — make the change. | Run the propose workflow
(`/arch-propose <suggested-change-id>`).
```

## Guardrails

- Write nothing. Answering a design question is not consent to write.
- Read every suggested path before you report; a decision you did not read is not one
  you can call honoured.
- Distinguish what a marker proves from what a name match suggests.
- Report a contradiction with an accepted decision even when the user did not ask.
- Do not inflate the triage: most changes need little or no documentation, and
  "trivial" is a legitimate, common answer.
