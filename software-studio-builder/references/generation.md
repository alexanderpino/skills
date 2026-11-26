# Generation — Phase 3

`generate.py <target>` renders the approved proposal plus the skeleton into the target.
It is deterministic: the same approved proposal gives byte-identical files, which is why a
second run reports `SAME` and why `KEEP` reliably means "someone edited this".

## Order and approval

```bash
python3 scripts/state.py approved <run>                    # must print "approved by user …"
python3 scripts/generate.py <target> --dry-run             # the whole plan, by layer
python3 scripts/generate.py <target> --dry-run --layer core
#   show the list → "May I write layer core (N files) to <target>?" → on yes:
python3 scripts/generate.py <target> --layer core
```

Repeat per layer: **core → agents → skills → rules → templates → gates → catalog → hooks →
tests**. The user may approve several layers at once ("all of them") — then
`--layer all`. Hooks come late on purpose: `settings.json` wires them, and a hook that runs
in the user's next session should be the last thing they approve.

## What each layer writes

| Layer | Files |
|---|---|
| core | `CLAUDE.md`, `project.yaml`, `.gitignore`, `.claude/docs/{collaboration-protocol,directory-structure}.md`, `.claude/docs/stacks.tsv`, `.claude/scripts/{mini_yaml,resolve_config,artifact_check,check_template}.py`, `docs/studio-research/*` (ledger, report, proposal) |
| agents | `.claude/agents/<role>.md` ×N, `.claude/docs/agent-roster.md`, `.claude/agent-models.yaml`, `.claude/docs/coordination-rules.md` |
| skills | `.claude/skills/{start,next-step,gate-check,project-settings}/SKILL.md`, `.claude/skills/<name>/SKILL.md` ×N |
| rules | `.claude/rules/<id>.md` ×N |
| templates | `.claude/docs/templates/<artifact>.md` ×N |
| gates | `.claude/docs/gates/<ID>.md` ×N, `.claude/docs/gates.md` |
| catalog | `.claude/docs/workflow-catalog.json` |
| hooks | `.claude/hooks/*.sh`, `.claude/settings.json` |
| tests | `studio-tests/test_template.py` |

Every run also merges `.claude/docs/studio-manifest.json` (generated and deferred items),
which the checker's C12 reads.

## Output lines

| Tag | Meaning | What to do |
|---|---|---|
| `WRITE` | written now | — |
| `WOULD-WRITE` | `--dry-run` | show the user |
| `SAME` | exists, identical | — |
| `UPDATE` / `WOULD-UPDATE` | exists, untouched since the generator wrote it (hash in the manifest), and the proposal now renders it differently — replaced | — this is how a studio follows a proposal change, e.g. the roster and the manager's Delegation Map after a role is added |
| `KEEP` | exists, **edited by someone** after generation (or predates the manifest) — left alone | tell the user; diff it against a dry-run render if they want to merge |

## Refusals (exit 2) — report them verbatim, never work around them

- `REFUSED: the proposal has not been approved` / `changed after approval` → show
  `proposal.md` again and get the user's approval.
- `REFUSED: the proposal has structural failures` → fix `proposal.json`, re-check,
  re-render, re-approve.
- `REFUSED: the MVP cut breaks the proposal's links` → each line names a generated item
  that depends on a deferred one; defer them together or keep both. Ask the user which.

## Formats the renderer produces

Every format below is agent-facing: it is read by a subagent or a session that has no memory
of this run. Write the proposal text that fills them by `references/writing-for-agents.md`.

- **Agent:** see `anatomy.md` — frontmatter (`name, description, tools, model, effort,
  maxTurns, skills, memory`), When You Are Spawned (read the checkpoint and the brief's
  documents by section, say NOT ASSESSED for a missing input, the return order), Collaboration Protocol with its workflow subsection and
  Collaborative Mindset, Key Responsibilities, standards sections, Gate Verdict Format
  (gate owners only), What This Agent Must NOT Do (adds the owned-paths limit), Delegation
  Map with **Reports to**, **Delegates to**, **Implements specs from**, **Escalation
  targets**, **Sibling coordination**, **Coordinates with**. `maxTurns`: director 25,
  lead 20, specialist 15.
- **Skill:** frontmatter (`name, description, argument-hint, user-invocable,
  allowed-tools`), Before you start (resolve config, read the checkpoint), one Phase per
  step, Output (template + path), Review (gates by review mode, and a stated skip at
  `solo`), Collaboration ("May I write…"), Return (its verdict words + `NOT ASSESSED — <why>`).
- **Rule:** `paths:` block list frontmatter, title, owner line, bullets.
- **Gate:** `**Agent**`, `**Phase**`, `**Lean**`, `**Trigger**`, `**Context to pass**`,
  `**Verdicts**`, Prompt, How to answer (verdict token first; NOT ASSESSED only for a
  missing *input*, never for a missing artifact — that is a finding).
- **Template:** title, purpose line, Status / Last updated / Sources header, one `##` per
  section with an HTML-comment guidance line.

## Changing the generated studio later

Change the proposal, re-check, re-render, re-approve, re-generate: new items are
`WRITE`, files the change affects `UPDATE`, unaffected ones `SAME`, and hand-edited ones
`KEEP`. Never hand-patch generated files to follow a proposal change — regenerate. For a change the proposal
cannot express, edit the studio directly and run its own `check_template.py`.
