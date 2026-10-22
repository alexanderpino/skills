---
description: Consult, propose, apply, validate or bootstrap living architecture docs as a gate around a change
argument-hint: <consult|propose|apply|validate|bootstrap> <task> — or 'help'
---

This command is an explicit entry point to the `principal-architect` skill. The skill
also triggers on its own whenever a task touches structure, boundaries, interfaces, data,
or quality attributes; this command exists to pick the *mode* deliberately. Read its
SKILL.md now and follow it as written.

Arguments:

$ARGUMENTS

If the arguments above are exactly `?` or `help` (or nothing was provided), do NOT start
any of the modes. Instead, read `SKILL.md` and output a concise, user-facing guide on how
to use `/principal-architect`: what the skill does (living architecture docs as a gate
around engineering work, not an afterthought), the three altitudes, the triage rule that
most changes need little or no documentation, and the five modes below with one line
each. Then stop.

Otherwise, the first word of the arguments selects the mode and the rest is the task.
If the first word is not a mode, treat the whole argument as the task and run `consult`.

## Modes

**`consult <task>`** — Step 0 and Step 1 only. Locate the docs root, read the index and
`AD.md`, read what the task touches (drivers, HLD section, SDs, ADRs whose `affects:`
overlaps), and report: which accepted decisions constrain this task, any conflict between
the intended approach and an accepted ADR, and the documentation delta from the Triage
table. Write nothing to the docs tree. This is the mode to run before planning.

**`propose <task>`** — `consult`, then draft. Pick the altitude, triage the change, and
write the artifacts it needs as drafts: a `proposed` ADR (or an `RFC.md` when the decision
is significant or cross-team per `references/governance.md`), and the HLD/SD/PRD sections
it would change. Derive content from evidence first; ask only for what cannot be derived;
mark the rest as assumptions. Stop before touching the index, `AD.md`, the decision log,
or any code, and present the drafts for review. Nothing becomes `accepted` here.

**`apply [task]`** — take the reviewed drafts from `propose` (or, with a task, run
`propose` first and apply directly when the change is Trivial or Local per the triage
table) and land them: Step 2 through Step 4. Fill the templates, update the affected
docs, place `ARCH-REF:` markers where a decision is enacted, update the index, `AD.md`,
and `decisions/README.md`, and honour the correspondence rules. Then run `validate`
automatically — `apply` is not done until Step 5 passes or its open items are reported.

**`validate`** — Step 5 on its own. Run `arch_lint.py all` against the resolved root and
source tree (copy the validator in from `assets/ci/` if the repo does not have it), fix
what it reports, then walk the six judgement questions over the docs that changed on this
branch (or, if nothing changed, over the whole tree as a health check). Report the
validator exit status, what the judgement gate found, and what remains open and why.

**`bootstrap [slice]`** — for a repo with no architecture docs, or a legacy codebase that
needs its as-is recovered. Resolve the root, lay down the default structure from
`references/repository-structure.md`, and reverse-engineer *the slice named* (not the
whole repo) with `references/methods.md` §3 — or the full pipeline in
`references/reverse-engineering.md` for a large or polyglot codebase. Produce the minimal
conformant set (AD root, PRD stub, the relevant HLD/SD, the first ADR, checklist), detect
the house style with `detect_doc_conventions.py` if the repo already has docs of any kind,
then `validate`.

## Rules that hold in every mode

- Pick the altitude before producing anything; most coding tasks are software level.
- Never silently violate an accepted ADR — surface the conflict or supersede it.
- Never fabricate a stakeholder, driver, or number; record a gap instead.
- The threat model and FinOps estimate are not optional in any HLD or SAD.
- Conform to the house style when one exists; the skill's templates are defaults.
