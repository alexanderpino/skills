# Mission Control — Artifact Contracts

Every artifact in the pipeline has a fixed shape. The shapes are contracts because
downstream agents parse them, gates require them, and the audit walks them. An artifact
that deviates from its contract is a bounce at the next gate, whatever its content.

All per-item artifacts live in `evidence/<item-id>/`. Filenames are fixed so the audit
can find them without guessing.

## Queue states and legal transitions

```
backlog ─► researching ─► plan-review ─► [orchestrator-approval] ─► approved
backlog ─► approved (if fast_track)
approved ─► building ─► verifying ─► [code-review] ─► done
```

Bracketed states apply only at the blast-radius tiers that require them
(orchestrator-approval: high/critical; code-review: medium and above).

Bounce transitions: `plan-review → researching`, `orchestrator-approval → researching`,
`verifying → building`, `code-review → building`. Bounces are capped: at
`mission.json:bounce_limit` (default 3) the transition is redirected to `blocked` with
the reason recorded — chronic bouncing means the research doc is wrong, and the cap
forces the upstream diagnosis.

Escalation/blocking: `blocked` is reachable from any gated state (leases released).
When blocking on new research, record the dependency —
`transition <id> blocked --blocked-on <item>` — so `status` can flag the unblock when
the dependency completes. Exit: `blocked → approved` (build-side blocks) or
`blocked → researching` (plan-side blocks or bounce-cap items needing a rewritten doc).

Worktree lifecycle: `worktree-add` on entering `building` (creates branch `mc/<id>`,
recorded as `worktree` on the queue item); all implementer/verifier work happens
there; merge + `worktree-remove` on `done`. A done item whose branch was never merged
is an audit hole.

`pipeline.py` enforces all of these; a transition without its required evidence file
fails.

## mission.json

```json
{
  "goal": "one-paragraph statement of done",
  "created": "ISO-8601",
  "terminal_conditions": {
    "backlog_drained": true,
    "max_items_completed": null,
    "token_budget": null,
    "deadline": null
  },
  "concurrency": { "implementers": 2, "scouts": 2 },
  "throughput": { "maximize": false, "decided_by": "user", "reason": null },
  "lease_ttl_minutes": 90,
  "bounce_limit": 3,
  "repo_oracle": {
    "build": "cmake --build build",
    "test": "ctest --test-dir build",
    "lint": null
  },
  "gates": {
    "orchestrator_approval_min_blast": "high",
    "code_review_min_blast": "medium"
  }
}
```

At least one terminal condition must be non-null/true. `repo_oracle.build` and
`repo_oracle.test` are mandatory before any item may enter `building`.

`throughput.decided_by` is `"user"` when the Orchestrator asked and the user
answered, `"orchestrator"` when running autonomously — in which case `reason` is
mandatory (one line: why maximize was or wasn't chosen). The flag licenses the
Architect's throughput-shaping only; it never changes gate tiers, bounce limits, or
evidence requirements.

## Backlog item (entries in backlog.json)

```json
{
  "id": "MC-007",
  "title": "short imperative title",
  "priority": 3,
  "depends_on": ["MC-004"],
  "ui": false,
  "fast_track": false,
  "constraints": [
    "structural constraints from the Architect, one per line",
    "e.g. no new subsystems; TransformComponent layout is frozen"
  ],
  "origin": "architect | escalation:<item-id> | user",
  "status": "open | claimed | done"
}
```

## Research doc — `evidence/<id>/research.md`

Markdown with a YAML header. The header is the machine-read part; the body is the
implementer's brief.

```markdown
---
item: MC-007
complexity: low | medium | high
blast_radius: low | medium | high | critical
touch_list:
  - src/ecs/query.cpp
  - src/ecs/query.h
ui: false
---

# Problem
What the backlog item needs and why, grounded in cited code
(file:line references, verified against the repo).

# Approach
The chosen implementation path, alternatives considered and rejected,
and how it respects the Architect's constraints.

# Acceptance criteria
Each criterion mechanically checkable, numbered, with its check:
1. Empty-archetype query returns empty span — test `test_query_empty_archetype`
2. No allocation in the hot path — check: existing bench `bench_query_iter`
   shows zero allocs
3. Public header unchanged — check: diff excludes src/ecs/query.h... (etc.)

# Risks & unknowns
Honest list. An empty section on a medium+ item is itself a review flag.
```

`touch_list` becomes the implementer's lease verbatim. Criteria the Verifier cannot
execute or diff are a Plan Reviewer bounce.

## Plan sign-off — `evidence/<id>/plan-review.json`

```json
{
  "item": "MC-007",
  "reviewer": "plan-reviewer",
  "verdict": "sign-off | bounce",
  "checks": {
    "soundness": "pass | fail: reason",
    "testability": "pass | fail: criterion #N not checkable because ...",
    "routing_honesty": "pass | fail: reason",
    "scope": "pass | fail: reason"
  },
  "notes": "actionable bounce reasons or empty",
  "timestamp": "ISO-8601"
}
```

Orchestrator approval (high/critical blast only) — `evidence/<id>/approval.json`, same
shape with `"reviewer": "orchestrator"` and written reasons in `notes` (an approval
with empty notes fails audit at this tier: the expensive gate must show its reasoning).

## Implementer handoff — `evidence/<id>/handoff.md`

```markdown
---
item: MC-007
implementer: senior | junior
---

# Changed
Per-file summary of the diff.

# Criteria status
1. pass — ran `ctest -R test_query_empty_archetype`, green
2. pass — bench output attached below
3. pass — header untouched

# Judgment calls
(senior only; empty for junior) Gaps in the doc I bridged, and why.

# Backlog suggestions
Out-of-scope improvements noticed but not made.
```

## Verifier record — `evidence/<id>/verify.json`

```json
{
  "item": "MC-007",
  "verdict": "green | red | oracle-broken",
  "build": { "command": "...", "pass": true },
  "tests": { "command": "...", "pass": true, "failures": [] },
  "criteria": [
    { "n": 1, "pass": true, "command": "...", "output_excerpt": "..." }
  ],
  "diff_in_scope": true,
  "out_of_scope_paths": [],
  "oracle_tampering": false,
  "timestamp": "ISO-8601"
}
```

## Review verdict — `evidence/<id>/code-review.json`

```json
{
  "item": "MC-007",
  "verdict": "approve | bounce",
  "concurrency_reviewed": true,
  "findings": [
    { "severity": "blocking | advisory",
      "location": "src/ecs/query.cpp:214",
      "defect": "…", "standard_violated": "…" }
  ],
  "judgment_calls_audited": true,
  "timestamp": "ISO-8601"
}
```

`concurrency_reviewed` must be `true` (with actual reasoning in findings or an explicit
all-clear) whenever the touch-list includes shared state or threaded code — audit
checks this field against the research doc.

## Agenda notes (agenda.json)

```json
{
  "next_id": 3,
  "notes": [
    { "n": 1,
      "text": "user directive: pause renderer-touching items until Thursday",
      "when": "before leasing anything under src/render/",
      "added": "ISO-8601",
      "resolved": null },
    { "n": 2,
      "text": "MC-014 bounce reasons suggest Architect constraint too vague",
      "added": "ISO-8601",
      "resolved": { "at": "ISO-8601", "note": "re-spawned Architect, MC-021" } }
  ]
}
```

The agenda is the Orchestrator's intent journal — the only Orchestrator-owned state
besides the queues, and deliberately tiny. Hard rule: nothing derivable from queue
state may appear here (no item positions, no idle-slot lists, no unblock conditions —
`status` computes those). Only non-reconstructible intent: deferred decisions,
mid-mission user directives, scheduled follow-ups. `when` is a free-text trigger hint,
not machine-evaluated — the Orchestrator reads and judges. Resolved notes keep their
resolution note so the trail shows what was decided; audit does not walk the agenda.

## Ledger entries (ledger.json)

```json
{
  "leases": [
    { "path": "src/ecs/query.cpp", "item": "MC-007",
      "acquired": "ISO-8601", "ttl_minutes": 90 }
  ]
}
```

One writer per path, no exceptions. Directory leases are allowed (`src/ecs/`) and
conflict with any path beneath them. Expired leases are reclaimable by the
Orchestrator only, after bouncing the holding item to `approved`.

## Audit chain

For every `done` item the audit requires, in order: backlog entry → `research.md` →
`plan-review.json` (sign-off) → `approval.json` iff blast ≥ high → `handoff.md` →
`verify.json` (green) → `code-review.json` (approve) iff blast ≥ medium. Missing or
failing links are reported by item id. The chain is cheap precisely because every gate
already wrote its evidence when it ran — audit reads, it never re-investigates.
