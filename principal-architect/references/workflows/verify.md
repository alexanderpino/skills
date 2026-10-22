# Workflow: verify

Decide whether a change is fit to archive, or whether a docs tree is healthy, and say
exactly what is wrong when it is not. SKILL.md Step 5: a mechanical gate the CLI runs
and a judgement gate you walk, reported together.

**Read-only boundary.** Verify reports; it does not fix. Recommend each fix with its
location, and make one only when the user asks for it.

`ARCH` below means `python3 <skill-dir>/scripts/arch.py`, where `<skill-dir>` is the
directory holding this skill's SKILL.md. Run it from the repository root and always
pass `--json`. The CLI is the source of truth for state; never infer what it reports.

**Input**: optionally a change id. With no change and no active changes, or when the
user asks for a health check, verify the whole tree (`--tree`).

## Steps

1. **Select the target**

   With an id, use it. Otherwise run `ARCH list --json`: one active change → use it;
   several → ask which; none → whole-tree health check. Announce the target.

2. **Run the mechanical gate**

   ```bash
   ARCH verify --change <id> --json      # or: ARCH verify --tree --json
   ```
   Add `--strict` when the docs are meant to be complete (unfilled template
   placeholders then count as errors), or when the user or CI asks for it.

   Parse `verdict`, `summary`, `checks` (each with `name`, `dimension`, `status`,
   `reason`), `issues` (each with `severity`, `dimension`, `message`, `path`, `line`),
   `judgement_gate`.
   - Exit code 2 with `error` → the target could not be verified; report the message
     and stop.
   - A check with `status: "skipped"` is **Not verified (<reason>)**. Never report it
     as passing.
   - An issue prefixed "pre-existing" is a lint failure in a file this change did not
     touch. Report it, separately; it is not this change's to fix, but CI will still
     fail on it.

3. **Walk the judgement gate**

   The CLI cannot judge content. For each question in `judgement_gate`, read the
   artifacts the change produced or altered (`change.md`, every record, every
   document a task names; for `--tree`, the documents changed most recently) and
   answer it with evidence:

   1. **Evidence** — every fact traceable to code, config, tests, history, or a named
      person; every guess marked as an assumption or gap.
   2. **Numbers** — every capacity, latency, availability or cost figure carries its
      model and assumptions, and says whether it is measured or derived.
   3. **Simplicity** — the four anti-over-engineering checks (SKILL.md §2) pass; for a
      kept or replaced mechanism, both §1 questions are answered separately and the
      gap is recorded.
   4. **Triage** — only the artifacts the archetype calls for, and every one it does
      call for.
   5. **Consistency** — the AD.md §7 correspondence rules hold for every view, SD and
      diagram that corresponds to what changed.
   6. **Voice** — prose reads as an engineer explaining a decision to a peer, with the
      forces and trade-offs on the page and none of the banned phrases.

   Record each finding as an issue, dimension **Judgement**:
   - **CRITICAL** — a fabricated stakeholder, driver or number; a required artifact
     missing; a decision that contradicts an accepted ADR without superseding it; a
     missing threat model or FinOps section in an HLD/SAD.
   - **WARNING** — an unstated assumption; a number without its model; a broken
     correspondence; a speculative mechanism the drivers do not justify.
   - **SUGGESTION** — voice, clarity, a diagram that would carry the point better
     (or one that should go).
   When unsure, choose the lower severity. A question you could not answer (a file you
   could not read, context you do not have) is **Not verified (<reason>)**, never
   passed.

4. **Report**, in the format below, with the final assessment chosen by these rules:
   - any CRITICAL → "<n> critical issue(s). Fix before archiving."
   - no CRITICAL, any check or question not verified → "No critical issues in the
     checks that ran. Not verified: <checks and reasons>." Do not claim readiness.
   - no CRITICAL, nothing skipped, warnings → "No critical issues. <n> warning(s) to
     consider. Ready to archive (with noted improvements)."
   - nothing at all → "All checks passed. Ready to archive."

## Output

```
## Verify: <id or "docs tree">

| Dimension | Status |
|-----------|--------|
| Conformance | <arch_lint result, decision log> |
| Completeness | <n/m tasks, planning complete?> |
| Traceability | <breadcrumbs, index> |
| Coherence | <review flags, AD root> |
| Judgement | <questions passed / issues / not verified> |

### CRITICAL — fix before archiving
- <message> — `<path>:<line>` — <recommended fix>

### WARNING — should fix
- …

### SUGGESTION — nice to fix
- …

### Pre-existing (not this change)
- …

**Assessment:** <one of the four sentences above>
```

Leave out an empty severity group rather than writing "none" under it.

## Guardrails

- Never score a skipped check or an unanswered question as a pass.
- `verdict: "mechanically_clean"` is not "ready": the judgement gate decides that.
- Every issue carries a location and a concrete fix.
- Prefer the lower severity when uncertain; do not pad the report with style
  nitpicks.
- Do not fix anything unless the user asks; then make only the fixes they chose and
  verify again.
