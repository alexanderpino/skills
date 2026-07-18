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
  "concurrency": { "implementers": 2, "scouts": 2, "investigators": 1 },
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
  "origin": "architect | escalation:<item-id> | split:<item-id> | investigation:<inv-id> | user",
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
splittable: false
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

# Split proposal
(only when the header says splittable: true; omit the section otherwise)
The skeleton (interfaces/scaffolding to land first) and the parallel parts
behind it, each part with its predicted touch-list — the proposal is only
valid if those touch-lists are disjoint. Advisory: the Scout proposes, the
Orchestrator routes, the Architect decides.
```

`touch_list` becomes the implementer's lease verbatim. Criteria the Verifier cannot
execute or diff are a Plan Reviewer bounce.

`splittable` is optional (default false) and meaningful only on maximize-throughput
missions. The doc must still cover the *whole* item — a split proposal is a rider,
not a substitute, so declining it costs nothing. Timing matters: the flag is acted
on when the doc arrives, while the item is still `researching` and before a Plan
Reviewer is spawned. On acceptance no state surgery is needed — the item stays in
`researching`, its doc is narrowed to the skeleton scope, and the Architect adds
the part-items with `origin: "split:<item-id>"` and `depends_on` the skeleton.

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

## Investigations (investigations.json)

The triage side channel for mid-mission user issues. Investigations live outside the
item queue — they precede backlog creation (the root cause is unknown, and the issue
may not become work at all) — with a deliberately tiny lifecycle:

```
open ─► closed
```

`investigate open` creates the entry and its evidence directory; `investigate close`
is the Orchestrator's disposition gate and refuses to run until
`evidence/<inv-id>/diagnosis.md` exists. There is no intermediate state: "report on
disk while still open" *is* the awaiting-disposition condition, and `status` flags it
as `DIAGNOSIS READY`.

```json
{
  "items": [
    { "id": "INV-001",
      "issue": "user: query results duplicated after MC-012 merged",
      "opened": "ISO-8601",
      "state": "open | closed",
      "disposition": {
        "kind": "fix | architect | no-action",
        "items": ["MC-031"],
        "note": "reasoning, or null when kind is fix",
        "at": "ISO-8601"
      }
    }
  ]
}
```

Disposition rules, enforced by `pipeline.py`:

- `fix` requires `items`: the backlog entries created from the diagnosis (with
  `origin: "investigation:<inv-id>"`), which must already exist — `add-item` first,
  then close. The fix flows through the normal gates; a diagnosed bug earns no
  shortcut past them (though a trivial root cause may warrant `fast_track` on the
  item, same as any other trivial item).
- `architect` requires `note` naming the structural evidence — the closed diagnosis
  becomes a licensed re-shape signal and the note seeds the Architect's brief.
- `no-action` requires `note` with the reasoning (`no-defect`, `cannot-reproduce`,
  out of scope). The Orchestrator's gate must show its work either way.

Investigations are pipeline state, so the agenda's hard rule applies: never mirror
an open investigation into an agenda note — `status` computes it.

## Diagnosis report — `evidence/<inv-id>/diagnosis.md`

Markdown with a YAML header, written by the Investigator. The header carries the
verdict and routing hints; the body is both the Orchestrator's gate-read and the
answer relayed to the user.

```markdown
---
investigation: INV-001
verdict: root-cause-found | no-defect | cannot-reproduce
root_cause_items: []              # pipeline items implicated, e.g. [MC-012]
recommended_disposition: fix | architect | no-action
fix_hints:                        # only when recommending fix; omit otherwise
  complexity: low | medium | high
  blast_radius: low | medium | high | critical
  touch_list:
    - src/ecs/query.cpp
---

# Symptom
The issue as the user stated it, restated precisely.

# Reproduction
How the symptom was reproduced (commands, inputs, observed output), or why it
could not be.

# Root cause
The defect and its location (file:line), distinguished from the proximate
symptom site. If a pipeline item introduced it, name the item and the evidence.

# Recommended disposition
One of fix / architect / no-action, with the reasoning the Orchestrator will
audit before closing.
```

`verdict` is what the investigation found; `recommended_disposition` is what to do
about it — they are separate fields because they can diverge (`root-cause-found` in
a third-party dependency may still recommend `no-action`). `fix_hints` seed the
backlog item's routing fields but do not replace the Scout: unless the item is
fast-tracked, a research doc is still written and still gated.

## Ledger entries (ledger.json)

```json
{
  "leases": [
    { "path": "src/ecs/query.cpp", "item": "MC-007",
      "acquired": "ISO-8601", "ttl_minutes": 90 }
  ],
  "contention": [
    { "item": "MC-009", "at": "ISO-8601", "held_by": ["MC-007"] }
  ]
}
```

One writer per path, no exceptions. Directory leases are allowed (`src/ecs/`) and
conflict with any path beneath them. Expired leases are reclaimable by the
Orchestrator only, after bouncing the holding item to `approved`.

`contention` is maintained by `pipeline.py` alone: every collision-rejected `lease`
call appends an event; a successful acquire (or the item leaving the build side)
clears that item's events. Two or more events on one item make `status` print a
`RESHAPE CANDIDATE` flag — the mechanical signal that the backlog's shape, not bad
luck, is serializing the queue. The Orchestrator never edits this list by hand.

## Audit chain

For every `done` item the audit requires, in order: backlog entry → `research.md` →
`plan-review.json` (sign-off) → `approval.json` iff blast ≥ high → `handoff.md` →
`verify.json` (green) → `code-review.json` (approve) iff blast ≥ medium. Missing or
failing links are reported by item id. The chain is cheap precisely because every gate
already wrote its evidence when it ran — audit reads, it never re-investigates.

Closed investigations are audited too: `diagnosis.md` must exist, and a `fix`
disposition must name backlog items that exist. Open investigations are not holes —
they are live work — but a mission is not complete while one is open.
