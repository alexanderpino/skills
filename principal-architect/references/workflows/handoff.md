# Workflow: handoff

Turn a decided architecture change into the starting point of an implementation
workflow — OpenSpec or spec-kit — without rewriting what the standards-based record
already says. The architecture record (ISO 42010 AD, 29148 drivers, 25010 quality
scenarios, Nygård/MADR decisions, TOGAF principles) stays the source of truth; the
implementation tool gets the same facts in its own shape and keeps its own gate.

**Seed boundary.** The export writes a seed that is derived, never invented: every
statement traces to a record (`*(trace: F.01)*`), and what the record does not say is
marked in the target's own convention (`[NEEDS CLARIFICATION: …]` for spec-kit, a
`<!-- principal-architect: … -->` note for OpenSpec). This workflow does not implement,
does not edit architecture docs, and does not run the target tool's own planning
commands for the user; it hands over and stops.

`ARCH` below means `python3 <skill-dir>/scripts/arch.py`, where `<skill-dir>` is the
directory holding this skill's SKILL.md. Run it from the repository root and always
pass `--json`. The CLI is the source of truth for state; never infer what it reports.

**Input**: a target (`openspec` or `speckit`) and optionally a change id. Without a
target, ask which — unless the repository already has `openspec/` or `.specify/`, which
decides it.

## Steps

1. **Select the change and check it is decided**

   With an id, use it; otherwise `ARCH list --json` (one active → use it; several → ask).
   Then:
   ```bash
   ARCH status --change <id> --json
   ```
   - `blocked` or `not_needed` → stop; a design that is not planned cannot be handed
     over (propose workflow).
   - `ready`, `in_progress`, `all_done`, `archived` → continue. `ready` is enough: the
     implementation needs the decisions, not the finished documentation.

2. **Dry-run the export and read what it derived**

   ```bash
   ARCH export <target> --change <id> --json
   ```
   Parse `dest`, `plan`, `derived` (`records`, `drivers`, `quality`, `stories`,
   `capability`, `contracts`, `principles_cited`, `prd_delta`), `gaps`, `gate`, `next`.
   - `error: "target_exists"` → the seed was written before. Ask whether to regenerate
     (`--force` rewrites only the seeded files) or leave it.
   - `derived.drivers` and `derived.stories` empty → the record is not tied to behaviour.
     Go back: add `satisfies: [F.xx]` to the decision record, or confirm with the user
     that behaviour does not change (OpenSpec then needs `skip_specs: true`).
   - `derived.capability` → for OpenSpec, compare with `openspec list --specs` when the
     project has specs; reuse an existing path over a near-duplicate. The seed says in
     `proposal.md` whether the path came from `realizes-capabilities` or was guessed
     from `affects:`.
   - `gaps` → each is a fact the record lacks. Ask now for any that would change scope,
     an interface or a quality target; the rest stay marked in the seed.

3. **Write the seed**

   ```bash
   ARCH export <target> --change <id> --yes --json
   ```
   The CLI records the hand-over on the change (`handoff:` in `change.md`), so verify
   and archive can see where the implementation lives. For spec-kit it also writes
   `.specify/feature.json` when `.specify/` exists, so `/speckit.plan` finds the feature.

4. **Read the seed as the implementer will**

   Open every file in `plan` and check the mapping held: a requirement per driver, a
   scenario per acceptance criterion, decisions with their alternatives, the
   `ARCH-REF` verification task. Fix a wrong derivation at its source (the ADR, the
   story, the PRD) and re-export with `--force`; do not patch the seed by hand, or the
   two records drift.

5. **Hand over and stop**, in the format below. The target tool's own flow finishes
   the artifacts and is the gate: `openspec validate <id> --strict`, or
   `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze`.

## Constitution (spec-kit only)

spec-kit reads `.specify/memory/constitution.md` before every plan. The enterprise
principles (`PR.xx`, TOGAF Preliminary) are that constitution:
```bash
ARCH export constitution --json          # dry run; --yes writes, --force replaces
```
Run it once per repository, when the principles exist and no constitution does. It
refuses when there are no principles on record: write them in
`enterprise-architecture.md` §2 first, through the normal change workflow, rather than
inventing a constitution the architecture does not hold.

## Output

```
## Handed over: <id> — <title> → <target>

**Seed:** <dest>/ (<n> files) · **Derived from:** <records>; <drivers>; <stories>; capability `<capability>`
**Gaps the record does not fill:** <list, or none>
**Gate:** <gate command>

Next: <the `next` text from the CLI>
```

## Guardrails

- Hand over only a decided change (`ready` or later).
- Never edit the seed by hand to fix a derivation; fix the record and re-export.
- Never invent a driver, a story or a capability to make the seed look complete.
- The target tool's validator is the gate; this workflow does not replace it.
- One target per run; a change may be handed to both, each recorded in `handoff:`.
