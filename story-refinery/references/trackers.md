# Tracker adapters

The bundle is tracker-agnostic. Adapters project it into whatever the house
uses. **Everything in this file about specific product APIs is `[?]` - probe
capabilities at runtime rather than trusting a hardcoded field id.**

## Contents

1. Adapter contract
2. Agent-brief sinks
3. Per-tracker notes
4. Push safety

---

## 1. Adapter contract

An adapter declares capabilities; `emit.py` picks a rendering strategy from them.

```yaml
capabilities:
  markup: adf | wiki | markdown | html | plaintext
  subtasks: native | task_list | linked_issues | none
  attachments: true | false
  comments: true | false
  custom_fields: true | false
  labels: true | false
  links: true | false
  max_description_chars: 32767
```

Degradation rules `[L]`:

- `subtasks: none` → render subtasks as a checklist in the parent description
  and emit each agent brief into a repo file, linked by path.
- `attachments: false` and `comments: false` → agent brief goes to
  `description_tail`; if that would exceed `max_description_chars`, it goes to
  `repo_file` and the description carries the link.
- `markup: plaintext` → strip fences, keep the markers, keep the JSON readable.

Markup conversion is implemented in `scripts/markup.py` and every payload carries
both `body` (markdown, the source) and `body_rendered` (the converted form) plus
a `markup` field, so a pusher never has to guess. `--adapter` on the command line
overrides the config's markup too - inheriting the markup of the adapter you just
replaced is how a Cloud description ends up in Server syntax.

Degradation is decided **per subtask**, not per story: one long brief moves to a
different sink while the rest stay where they are, and the push plan records
`agent_brief_sink_per_subtask` so the pusher knows where each one went. If a
subtask's description is over the limit even with the brief removed, that is
reported as a human-text problem, because it is one.

Probe order at runtime: read the config; if the session has a live connector or
CLI for the tracker, confirm issue types and field names from it; otherwise treat
config values as `[?]` and say so in the preview.

---

## 2. Agent-brief sinks

Where the machine-readable payload lands. Configure a primary and a fallback
chain, because the right answer is genuinely tracker-dependent.

| Sink | Mechanics | Good | Bad |
|---|---|---|---|
| `description_tail` | fenced by markers at the end of the subtask description | always visible; survives export; no extra fetch | clutters the human view; description size limits; humans edit it by accident |
| `comment` | first comment on the subtask, marker-fenced | keeps description clean; timestamped; easy to supersede | ordering not guaranteed; comment may be buried; some trackers throttle |
| `attachment` | `agent-brief.json` attached to the subtask | clean separation; real JSON, no markup escaping | needs an extra API call and download step; some trackers version attachments badly |
| `repo_file` | `.refinery/briefs/<KEY>.json` committed to the repo | versioned with the code; reviewable in the PR; diffable | drifts from the ticket if not regenerated; needs a commit |
| `custom_field` | dedicated text field | queryable, automatable | requires admin setup; field length limits; brittle across projects |

Recommended defaults `[L]`. Note the shipped `refinery.example.yaml` is tuned
for Jira (`attachment`, then `comment`); when you switch `tracker.adapter`,
reorder `agent_brief.fallback` to match the row below, or the fallback chain will
quietly pick the second-best sink for your tracker.

- **Jira**: `attachment`, fallback `[comment, description_tail]`. Attachments
  avoid the ADF escaping problem entirely.
- **GitHub / GitLab**: `description_tail`. Markdown fences render natively and
  the body is diffable in the UI.
- **Linear**: `description_tail`, fallback `comment`.
- **Azure DevOps**: `attachment`, fallback `description_tail`.
- **Markdown / no tracker**: `repo_file`.

Marker convention, used by every sink that embeds in text `[L]`:

```
<!-- AGENT-BRIEF v1 BEGIN {"ticket":"ABC-124","hash":"sha256:..."} -->
```json
{ ... }
```
<!-- AGENT-BRIEF v1 END -->
```

The hash lets a later run detect that a human edited the brief by hand. On
mismatch: warn, show the diff, never silently overwrite.

---

## 3. Per-tracker notes

All `[?]` - verify before relying on any of it.

### Jira

- Sub-tasks are a distinct issue type linked by the `parent` field. The type name
  varies per project ("Sub-task", "Subtaak", "Sub-Task") - read it from the
  project's issue type scheme, do not hardcode.
- Cloud REST v3 expects **ADF** (Atlassian Document Format) for rich text; Server
  and Data Center expect wiki markup. Getting this wrong produces a description
  full of literal asterisks. `emit.py` converts, but its ADF support is core
  nodes only and flattens tables to bullet lists on purpose: a malformed table
  node gets the whole document rejected. Verify against a live instance once,
  then trust it. When in doubt, use `--markup plaintext` with the brief as an
  attachment.
- Custom field ids (`customfield_1xxxx`) are per-instance. Always resolve by
  field *name* first, then cache the id.
- Bulk creation limits and screen configuration decide which fields you can
  actually set on create. Expect some fields to require a second update call.

### GitHub Issues

- No classic subtask type. Options: markdown task lists in the parent body, or
  the newer sub-issue relationship if the org has it enabled. Probe; fall back to
  task lists.
- Labels are the practical carrier for `kind` (`refinery:test`,
  `refinery:spike`).
- `gh issue create --body-file` avoids shell-escaping problems with long bodies.

### GitLab Issues

- Child relationships depend on tier and on whether the project uses epics or
  work items. Task lists are the universally available fallback.
- Quick actions (`/label`, `/assign`) in the body are a cheap way to set
  metadata without extra API calls.

### Linear

- Native sub-issues via a parent relationship. Markdown descriptions.
- Its API is GraphQL; field names differ from REST conventions - resolve from the
  schema.

### Azure DevOps

- `Task` work items under a `User Story` via the `System.LinkTypes.Hierarchy`
  relation. Descriptions are HTML for some work item types.

### Markdown / no tracker

- Write `out/<KEY>/story.md` and `out/<KEY>/S<n>.md`, briefs to
  `out/<KEY>/briefs/*.json`. This is also the right target for a dry run against
  any other tracker.

---

## 4. Push safety

`emit.py` never touches the network. Pushing is a separate, explicitly approved
step.

Before pushing, always:

1. Show `out/preview.md` and get approval on content.
2. Show the push plan: how many issues, of what type, into which project, with
   which parent. Counts matter - "creates 9 sub-tasks under ABC-123" is
   reviewable; "creates subtasks" is not.
3. Check idempotency. Search for existing subtasks whose title matches the
   pattern before creating. Duplicated subtask trees are painful to clean up.
4. Prefer create-then-verify over fire-and-forget: after creation, re-read one
   created issue and confirm the description and brief landed intact, especially
   the first time against a new project.

On partial failure, stop. Report what was created with keys, and what was not.
Do not retry blindly - half the tree existing is recoverable, a duplicated tree
is not.

### Updating an existing tree

Run `emit.py --previous <prior-bundle.json>`. The push plan becomes
`mode: update` with three lists:

- **creates** - new subtasks only
- **updates** - subtasks whose content changed; `brief_hash_changed` narrows this
  to the ones whose agent brief actually differs, so you can skip no-op writes
- **orphans** - subtasks that no longer exist in the refinement

Never auto-close or delete an orphan. Someone may already be working on it, or it
may have shipped. Report it and let a human decide. The same applies when a
brief's embedded hash does not match what is in the tracker: a human edited it,
so show the difference rather than overwriting.
