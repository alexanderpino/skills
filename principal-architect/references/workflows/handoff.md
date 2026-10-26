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
   story, the PRD) and re-export with `--force`; do not patch a derivation in the seed,
   or the two records drift. A re-export is safe for the implementer's work: files
   untouched since seeding are regenerated, files edited since are kept and listed in
   `kept` (carry the record's change into those by hand), and `tasks.md` keeps its
   ticked boxes.

5. **Hand over and stop**, in the format below. The target tool's own flow finishes
   the artifacts and is the gate: `openspec validate <id> --strict`, or
   `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze`.

## Two lifecycles, one visible link

The architecture change and the implementation change do not wait for each other.
A decision record is **accepted when the decision is made** (MADR; TOGAF separates
decision from implementation governance), so `arch.py archive` accepts the records
and archives the change whether or not the implementation is finished. Holding an
ADR in `proposed` until the code ships would make the next `consult` treat a decision
already taken as non-binding — worse than any drift. Delivery is the implementation
tool's job and is tracked there.

What the architecture side keeps is **sight of the implementation**, from the
`handoff:` entry the export writes (`<target>:<path>@<fingerprint>`):

- `arch.py status` reports each hand-over's `state` (`seeded`, `not_started`,
  `in_progress`, `done`, `archived` — an OpenSpec change is followed into
  `changes/archive/` — or `missing`) and its task progress.
- `arch.py verify` adds an **Implementation** dimension: WARNING when a hand-over
  target no longer exists, WARNING when the architecture record changed after the seed
  was written (the fingerprint no longer matches: an ADR, driver, story, scope or
  contract moved on), SUGGESTION when a seed predates fingerprints. Accepting an ADR or
  archiving the change is not drift; only the facts the seed derives from count.
- `arch.py archive` lists the implementation state in its plan so the user sees it
  before saying yes, and never refuses because of it.

On a drift warning: re-export with `--force` (step 4 says what that keeps), or, when
the implementer has already carried the change into the seed, re-export anyway so the
fingerprint is refreshed; a hand-edited file is kept either way.

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
