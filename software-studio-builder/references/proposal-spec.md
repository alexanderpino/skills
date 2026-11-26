# Proposal specification — Phase 2

`<run>/proposal.json` is the single source of truth; `proposal.md` is rendered from it by
`proposal.py render` and never edited. The worked example is
`tests/fixtures/hr-payroll/.ssb/proposal.json` — copy its shape.

## Top level

```json
{
  "schema": "ssb-proposal/1",
  "studio": {"name", "slug", "domain", "summary", "goal",
             "authorities": {"product": "<director id>", "technical": "<director id>", "delivery": "<director id>"}},
  "concept_map": [{"concept": "Design document per module", "here": "Functional spec", "claims": [...]}],
  "roles": [...], "phases": [...], "artifacts": [...], "skills": [...], "rules": [...],
  "stacks": [...], "gates": [...],
  "hooks": ["session-start", "validate-commit", "validate-write", "validate-read", "log-agent"],
  "rigor": {"default": "minimal|standard|full"},
  "scope": {"generate": "mvp|full", "later": ["role:<id>", "skill:<name>", "rule:<id>", "gate:<ID>", "artifact:<id>"]},
  "open_questions": ["..."]
}
```

`authorities` names the directors that `coordination-rules.md` escalates conflicts to.

**`claims`** on every item: a non-empty list of `C001` (ledger claim), `USER: <decision>`
or `NOT SOURCEABLE: <what was searched>`.

## Role

| Field | Type | Notes |
|---|---|---|
| `id` | slug | the agent file name |
| `title`, `description` | text | description is the agent's one-line purpose |
| `tier` | `director` \| `lead` \| `specialist` | |
| `reports_to` | role id \| `user` | directors → `user`; others → a role in a **higher** tier |
| `implements_specs_from` | [role id] | whose specs this role builds from |
| `escalation` | [{`to`, `when`}] | every entry has a reason; targets are roles — except directors, who must escalate to `user` (`{"to": "user", "when": …}`); only directors may |
| `siblings` | [{`with`, `for`}] | same-level coordination |
| `coordinates_with` | [{`with`, `for`}] | cross-branch coordination |
| `owns_paths` | [path] | its write domain; rendered into **Must NOT** |
| `skills` | [skill name] | preloaded skills (proposal or baseline) |
| `model` / `effort` | `opus\|sonnet\|haiku` / `low\|medium\|high` | judgement-heavy roles high |
| `tools` | [tool] | implementers add `Bash` |
| `workflow` | `question-first` \| `implementation` | picks the protocol subsection |
| `responsibilities` | [text] | numbered in the agent file |
| `standards` | [{`heading`, `rules`}] | domain sections, e.g. "Personal Data" |
| `must_not` | [text] | hard limits |
| `mvp` | bool | false → deferred when `scope.generate` is `mvp` |

**Derived, never stored:** *Delegates to* (roles whose `reports_to` is this role) and
*Gates owned* (gates whose `owner` is this role). A stored `delegates_to` that disagrees
with the derivation is a FAIL.

## Phase and step

```json
{"id": "requirements", "name": "Requirements", "next": "architecture", "steps": [
  {"id": "specs", "name": "Functional specs", "command": "/functional-spec", "owner": "business-analyst",
   "required": true, "artifact": {"glob": "docs/specs/*.md", "min_count": 1},
   "template": "functional-spec", "min_workflow": "minimal", "claims": ["C002"]}]}
```

`command` names a proposal or baseline skill (or `null`); `template` an artifact id;
`min_workflow` the lowest `modes.workflow` at which the step is required.

## Artifact, skill, rule, gate, stack

- **Artifact:** `id`, `name`, `path` (may contain `<placeholders>`), `owner`, `sections`
  (≥2; strings or `{heading, guidance}`), `purpose`?, `mvp`?, `claims`.
- **Skill:** `name` (not a baseline name), `owner`, `description` (what it does + `Use when …`),
  `argument_hint`, `steps` (strings or `{name, detail}`), `verdicts` (≥2; NOT ASSESSED is
  added automatically), `produces` (artifact id or null), `gates` ([gate id]), `mvp`?, `claims`.
- **Rule:** `id`, `title`?, `paths` ([glob]), `rules` ([text]), `owner`, `mvp`?, `claims`.
- **Gate:** `id` (`AB-NAME`, upper case), `owner`, `phase` (phase id or null), `lean` (runs at
  `review_mode: lean`), `verdicts` (best first, failing last; never list NOT ASSESSED),
  `trigger`, `context`, `prompt`, `claims`.
- **Stack:** `name`, `code_root`, `test_root`, `build`?, `test`?, `run`?, `claims`.

## Acceptance checklist

The checklist lives in `references/acceptance.md` (items **P1–P10** for the proposal stop).
The Phase 2 design critic and the validation stage both work from it.

## Commands

```bash
python3 scripts/proposal.py init <run> --name "…" --slug … --domain "…"
python3 scripts/proposal.py check <run>              # FAIL > NOT ASSESSED > CONCERNS > PASS
python3 scripts/proposal.py render <run>             # writes proposal.md
python3 scripts/proposal.py derive <run> <role-id>   # the full reporting line, derived
python3 scripts/state.py approve <run> --by user --note "<the user's words>"   # ONLY on the user's yes
```
