# Mission Control — Contracts

Artifacts and state have fixed shapes because commands parse them and audit
replays them. Content outside the contract is not a substitute for a required
field.

## Canonical state and concurrency

`.mission-control/state.db` is canonical. It uses SQLite WAL, foreign keys, a
busy timeout, and schema versioning. Core tables are:

- `documents`: mission, agenda, and investigations;
- `backlog_items` and `queue_items`: independently versioned item rows;
- `leases` and `contention`: atomic semantic ownership and collision events;
- `evidence_seals`: accepted artifact hashes;
- `sandboxes` and `merge_jobs`: versioned runtime records;
- `audit_log`: append-only command events.

Mutations use short `BEGIN IMMEDIATE` transactions. Item and runtime updates
compare the observed version/state before replacing a row. Filesystem, Git,
AST, container, and agent work occurs outside transactions, then commits with
CAS. A lost CAS reloads/retries; it never overwrites the winner.

Lease acquisition is all-or-nothing. One transaction checks all existing
targets, inserts all requested targets or none, and records one contention
event on failure.

The six JSON files are compatibility snapshots only. `export-json` writes
them; edits do not affect SQLite and are detected before the next export.
`--force` explicitly replaces edited snapshots.

Legacy JSON migration:

1. requires all six JSON files;
2. copies exact bytes to `migration-backup/legacy-json-v1/`;
3. refuses to overwrite a differing backup;
4. imports once and records hashes/metadata;
5. converts `ready-to-merge` to `merge-pending`;
6. is idempotent when `state.db` already exists.

## Queue states

```text
backlog → researching → plan-review → [orchestrator-approval] → approved
backlog → approved                                      (fast_track only)
approved → building → verifying → [code-review] → merge-pending
merge-pending → merging
merging → post-merge-verifying                          (clean)
merging → merge-conflict                                (conflict/invariant)
merge-conflict → merging | merge-pending
post-merge-verifying → done                             (verified CAS publish)
post-merge-verifying → merge-conflict | merge-pending  (failure/CAS loss)
```

Compatibility input `ready-to-merge` maps to `merge-pending`; it is not a
distinct modern state. Direct `transition ... done` is illegal.

Bounce transitions:

- `plan-review → researching`;
- `orchestrator-approval → researching`;
- `verifying → building`;
- `code-review → building`.

At `mission.bounce_limit`, a bounce becomes `blocked`. Blocking releases
leases. A plan-side block returns only to `researching`, a build-side block only
to `approved`, and a merge-side block only to `merge-pending`.

`building → verifying` requires a committed worktree diff, handoff evidence,
and a green computed semantic-scope artifact. Verification/code-review advance
to `merge-pending` only with sealed evidence.

Only merge finalization may reach `done`: it must validate merge evidence,
pass a post-merge sandbox, win ref CAS, remove the worktree/branch, release
leases, and update both queue and backlog in one SQLite transaction.

## Mission document

```json
{
  "goal": "one paragraph defining done",
  "created": "ISO-8601",
  "state": {
    "backend": "sqlite",
    "journal_mode": "WAL",
    "busy_timeout_ms": 10000
  },
  "terminal_conditions": {
    "backlog_drained": true,
    "max_items_completed": null,
    "token_budget": null,
    "deadline": null
  },
  "concurrency": {
    "implementers": 2,
    "scouts": 2,
    "investigators": 1
  },
  "throughput": {
    "maximize": false,
    "decided_by": "user",
    "reason": null
  },
  "lease_ttl_minutes": 90,
  "bounce_limit": 3,
  "semantic": {
    "python_adapter": "stdlib-ast",
    "fallback": "file"
  },
  "execution": {
    "backend": "auto",
    "image": null,
    "native_fallback": true,
    "network": "none",
    "read_only_root": true,
    "resources": {"cpus": 2, "memory": "2g", "pids": 256},
    "commands": ["build command", "test command"],
    "artifact_paths": []
  },
  "merge": {
    "target_ref": null,
    "max_cas_retries": 3,
    "require_resolution_review": true
  },
  "repo_oracle": {
    "build": "build command",
    "test": "test command",
    "lint": null
  },
  "gates": {
    "orchestrator_approval_min_blast": "high",
    "code_review_min_blast": "medium"
  }
}
```

At least one terminal condition is enabled. Build and test commands are
mandatory before `building`. `throughput.reason` is mandatory when the
Orchestrator decides autonomously.

`execution.backend` is `auto | docker | podman | native`. Container execution
requires an image. `auto` chooses an available container only when an image is
configured; otherwise `native_fallback` controls explicit degraded execution.

## Backlog item

```json
{
  "id": "MC-007",
  "title": "short imperative title",
  "priority": 3,
  "depends_on": ["MC-004"],
  "ui": false,
  "fast_track": false,
  "constraints": ["public query layout remains frozen"],
  "origin": "architect",
  "status": "open"
}
```

`origin` is `architect | user | escalation:<id> | split:<id> |
investigation:<id>`. Status is `open | claimed | done`. Queue and backlog
exports add their current optimistic `version`.

## Semantic lease target

```json
{
  "path": "src/query.py",
  "type": "symbol",
  "qualified_symbol": "Query.execute",
  "node_kind": "FunctionDef",
  "base_blob": "<git blob or content hash>",
  "base_commit": "<commit>",
  "structural_anchor_hash": "<sha256>",
  "adapter": "python-ast"
}
```

Target types:

- `file`: `qualified_symbol` and anchor are null. A directory-like path owns
  every descendant.
- `symbol`: a qualified Python class/function/async function. A parent symbol
  owns descendants.
- `synthetic`: `imports | globals | module-members | preprocessor`.
  The Python adapter currently emits imports, globals, and module-members.

Anchors identify path + adapter version + node kind + qualified name, so body
edits do not move the anchor. Base blob/commit bind discovery to a revision.

Conflict rules:

- any file target conflicts with equal/ancestor/descendant paths;
- equal symbol and parent/child symbols conflict;
- sibling symbols do not;
- equal synthetic areas conflict;
- `module-members` conflicts with top-level symbol structure;
- imports/globals are separate from ordinary sibling function bodies.

Unsupported languages, generated or invalid Python, non-UTF-8 source,
format/comment-only diffs, file add/delete/rename/copy, and any ambiguous AST
mapping collapse to a file target. This fallback is mandatory.

Committed semantic diff records modifications, deletions, safe unique renames,
new nested nodes against their parent, and new top-level nodes against
`module-members`. Every changed target must be covered by a held target.

Ledger export:

```json
{
  "leases": [{
    "item": "MC-007",
    "target": {"path": "src/query.py", "type": "symbol"},
    "path": "src/query.py",
    "acquired": "ISO-8601",
    "ttl_minutes": 90
  }],
  "contention": [{
    "item": "MC-009",
    "held_by": ["MC-007"],
    "targets": [{"path": "src/query.py", "type": "symbol"}],
    "at": "ISO-8601"
  }]
}
```

## Research document — `evidence/<id>/research.md`

```markdown
---
item: MC-007
complexity: medium
blast_radius: medium
touch_list:
  - src/query.py
lease_targets:
  - {"path":"src/query.py","type":"symbol","qualified_symbol":"Query.execute","node_kind":"FunctionDef","base_blob":"...","base_commit":"...","structural_anchor_hash":"...","adapter":"python-ast"}
ui: false
splittable: false
concurrency: false
---

# Problem
Grounded problem with file:line citations.

# Approach
Chosen path, rejected alternatives, and constraint compliance.

# Acceptance criteria
1. Mechanically checkable criterion — exact test/command.

# Risks & unknowns
Honest risks.
```

`touch_list` remains mandatory for human scope and compatibility. If
`lease_targets` is absent, every touch-list path becomes a conservative file
target. Discover targets with `semantic-index`; never invent anchors.

`complexity` is `low | medium | high`; `blast_radius` is
`low | medium | high | critical`. `concurrency` declares threaded/shared
mutable state and controls explicit review. `splittable` is meaningful only in
maximize mode and requires a `# Split proposal` whose sibling targets are
predicted disjoint.

## Gate artifacts

Every accepted gate artifact is hashed into queue history and the
`evidence_seals` table. JSON artifacts carry timezone-aware timestamps.
Markdown modification time and JSON timestamp must belong to the current gate
attempt. Reusing unchanged bounced evidence is rejected.

### Plan review — `plan-review.json`

```json
{
  "item": "MC-007",
  "reviewer": "plan-reviewer",
  "verdict": "sign-off",
  "checks": {
    "soundness": "pass",
    "testability": "pass",
    "routing_honesty": "pass",
    "scope": "pass"
  },
  "notes": "",
  "timestamp": "ISO-8601"
}
```

Bounce requires verdict `bounce`, at least one `fail: reason`, and actionable
notes. `approval.json` has the same schema with reviewer `orchestrator`;
high-blast sign-off requires non-empty reasoning.

### Implementer handoff — `handoff.md`

```markdown
---
item: MC-007
implementer: senior
---

# Changed
Per-target summary.

# Criteria status
1. pass — command and observed result.

# Judgment calls
Decisions bridged by a senior, or None.

# Backlog suggestions
Out-of-scope observations, or None.
```

### Semantic scope — `semantic-scope.json`

Generated by the CLI, not the Implementer:

```json
{
  "item": "MC-007",
  "base_commit": "...",
  "result_commit": "...",
  "changed_paths": [],
  "changed_targets": [],
  "leased_targets": [],
  "uncovered_targets": [],
  "diagnostics": [],
  "verdict": "green",
  "timestamp": "ISO-8601"
}
```

An uncovered or unmappable target makes verdict red and blocks verification.

### Sandbox — `sandbox.json`

```json
{
  "item": "MC-007",
  "backend": "docker",
  "degraded_isolation": false,
  "image": "repo/image:tag",
  "image_digest": "repo/image@sha256:...",
  "source_commit": "...",
  "source_tree_sha256": "...",
  "resource_policy": {
    "cpus": 2,
    "memory": "2g",
    "pids": 256,
    "network": "none",
    "no_new_privileges": true,
    "cap_drop": "ALL",
    "private_tmp": true
  },
  "commands": [{
    "command": "...",
    "exit_code": 0,
    "log": "sandbox-1.log",
    "log_sha256": "..."
  }],
  "artifact_hashes": {},
  "timestamp": "ISO-8601"
}
```

Each log path is evidence-directory confined and hash checked. Native evidence
must use `backend: native`, `degraded_isolation: true`.

### Verification — `verify.json`

```json
{
  "item": "MC-007",
  "verdict": "green",
  "build": {"command": "...", "pass": true},
  "tests": {"command": "...", "pass": true, "failures": []},
  "criteria": [{
    "n": 1,
    "pass": true,
    "command": "...",
    "output_excerpt": "..."
  }],
  "diff_in_scope": true,
  "out_of_scope_paths": [],
  "oracle_tampering": false,
  "sandbox_evidence_sha256": "...",
  "timestamp": "ISO-8601"
}
```

Green requires every mechanical check, semantic scope, and sandbox command to
pass. Red/oracle-broken evidence is valid only for a bounce.

### Code review — `code-review.json`

```json
{
  "item": "MC-007",
  "verdict": "approve",
  "concurrency_reviewed": false,
  "findings": [],
  "judgment_calls_audited": true,
  "timestamp": "ISO-8601"
}
```

Findings use severity `blocking | advisory` and require location, defect, and
standard violated. Approval cannot contain blocking findings.

## Merge evidence

### Clean merge — `merge.json`

```json
{
  "item": "MC-007",
  "kind": "clean",
  "base": "...",
  "ours": "...",
  "theirs": "...",
  "target_ref": "refs/heads/main",
  "result_commit": "...",
  "conflict_paths": [],
  "scope_validation": {"verdict": "green", "uncovered_targets": []},
  "timestamp": "ISO-8601"
}
```

`kind` is `clean | already-integrated`. Scope is recomputed from target head to
the result and must be green.

### Conflict/resolution — `merge-resolution.json`

```json
{
  "item": "MC-007",
  "base": "...",
  "ours": "...",
  "theirs": "...",
  "target_ref": "refs/heads/main",
  "conflict_paths": ["src/query.py"],
  "conflict_hunks": [],
  "ours_semantic_targets": [],
  "theirs_semantic_targets": [],
  "overlapping_semantic_targets": [],
  "semantic_invariant_violation": false,
  "resolution_allowed": true,
  "reasoning": "why resolution is safe or forbidden",
  "resolution_commit": "...",
  "scope_validation": {"verdict": "green", "uncovered_targets": []},
  "code_review": {
    "verdict": "approve",
    "reviewer": "code-reviewer",
    "findings": [],
    "timestamp": "ISO-8601"
  },
  "timestamp": "ISO-8601"
}
```

The coordinator stores a hash of the conflict-analysis fields. The Merge Agent
may complete only `resolution_commit`; the Code Reviewer completes
`code_review`. Changing base/heads, paths/hunks, semantic targets, invariant
flags, or reasoning is tampering.

When `semantic_invariant_violation` is true, `resolution_allowed` is false and
finalization always rejects. When resolution is allowed, integration HEAD must
equal `resolution_commit`, contain no unmerged entries, remain within item
leases, and receive Code Reviewer approval.

### Post-merge evidence

`post-merge-sandbox.json` has the sandbox schema.

```json
{
  "item": "MC-007",
  "verdict": "green",
  "result_commit": "...",
  "target_head": "...",
  "sandbox_evidence_sha256": "...",
  "timestamp": "ISO-8601"
}
```

A red result does not publish. A green result is sealed before compare-and-swap
publication. CAS failure records the observed head and returns to
`merge-pending`.

## Agenda and investigations

Agenda:

```json
{
  "next_id": 2,
  "notes": [{
    "n": 1,
    "text": "non-derivable directive",
    "when": "optional trigger",
    "added": "ISO-8601",
    "resolved": null
  }]
}
```

Queue positions, contention, investigations, and unblock/merge candidates are
never agenda notes because status derives them.

Investigation:

```json
{
  "id": "INV-001",
  "issue": "user symptom",
  "opened": "ISO-8601",
  "state": "open",
  "disposition": null
}
```

`diagnosis.md` requires frontmatter fields `investigation`, verdict
`root-cause-found | no-defect | cannot-reproduce`, `root_cause_items`, and
recommended disposition `fix | architect | no-action`, plus non-empty Symptom,
Reproduction, Root cause, and Recommended disposition sections.

Closing seals the diagnosis hash. `fix` names pre-created backlog items whose
origin is `investigation:<id>`; `architect` and `no-action` require written
reasoning.

## Audit

For every done item, audit requires:

1. done queue and backlog rows;
2. research/plan/approval gates as applicable;
3. handoff and committed implementation metadata;
4. green semantic scope matching the lease snapshot;
5. green verification with untampered sandbox logs/evidence;
6. code-review approval when required;
7. valid, untampered clean or reviewed resolution evidence;
8. green post-merge sandbox evidence;
9. published merge commit reachable from target ref;
10. removed worktree state and released leases.

Audit also validates closed diagnosis hashes/origins and reports every open
investigation as a hole.
