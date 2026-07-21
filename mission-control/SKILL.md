---
name: mission-control
description: >-
  Durable command-and-control orchestration for middle-large and large
  repository changes executed by several agents. Uses canonical SQLite/WAL
  state, semantic leases, private build sandboxes, evidence-gated transitions,
  automated merge coordination, and crash recovery. Use when the user asks for
  a sustained multi-agent implementation mission, maximum-throughput
  decomposition, or resumption/audit of an existing .mission-control state.
  Do not use for small fixes, ordinary one-agent coding, or lightweight
  delegation where this lifecycle would add more ceremony than safety.
---

# Mission Control

Mission Control turns one large goal into a continuously routed
plan → build → merge pipeline. Valuable work should not starve, but filling
slots with make-work is never a goal. The backlog defines work; queue states are
derived execution state; no change publishes without a sealed evidence chain.

**You are the Orchestrator.** Route agents and enforce gates. Do not implement
production code or resolve merge conflicts yourself: impartial routing is your
job.

## Suitable missions

Use this skill when all or most are true:

- the change is middle-large or large and has several independently leasable
  slices;
- agents need durable handoffs, budgets, crash recovery, and isolated builds;
- parallel throughput matters enough to justify architecture, plan, code, and
  merge gates;
- `.mission-control/` already exists and must be resumed or audited.

Do not use it for a routine fix, short investigation, non-code coordination, or
work one capable agent can safely complete.

## Lifecycle

```text
GOAL
  └─ ARCHITECT ─ backlog
       └─ SCOUT ─ research.md + semantic touch targets
            └─ PLAN REVIEWER ─ plan-review.json
                 └─ ORCHESTRATOR APPROVAL (high/critical only)
                      └─ APPROVED
                           └─ IMPLEMENTER ─ committed branch + handoff.md
                                └─ VERIFIER ─ sandbox.json + verify.json
                                     └─ CODE REVIEWER (medium+ only)
                                          └─ MERGE PENDING
                                               ├─ clean mechanical merge
                                               └─ MERGE AGENT (conflicts only)
                                                    └─ post-merge sandbox
                                                         └─ CAS publish ─ DONE
```

Plan gates bless intent. Build gates bless the implementation. Merge gates
bless the integrated result. Never substitute evidence from one chain for
another.

## Durable state

Initialize in the target repository:

```bash
python scripts/pipeline.py --root .mission-control init --goal "..."
python scripts/pipeline.py --root .mission-control configure --json '{...}'
```

The state directory contains:

```text
.mission-control/
├── state.db                 # canonical SQLite state, WAL journal
├── mission.json             # read-only compatibility export
├── backlog.json             # read-only compatibility export
├── queue.json               # read-only compatibility export
├── ledger.json              # read-only compatibility export
├── agenda.json              # read-only compatibility export
├── investigations.json      # read-only compatibility export
├── evidence/<id>/           # gate, semantic, sandbox, and merge evidence
├── worktrees/<id>/          # implementer worktrees
├── sandboxes/<id>/          # private source/build/cache/package storage
└── integration/<id>/        # private merge clones
```

`state.db` is the only state source after initialization or migration. Never
edit JSON snapshots to drive the pipeline. Export explicitly:

```bash
python scripts/pipeline.py --root .mission-control export-json
```

The exporter detects edits to prior snapshots; `--force` is an explicit
discard of those edits. Legacy JSON-only state migrates automatically, or with
`migrate-state`. Migration first copies all six files to
`migration-backup/legacy-json-v1/`; it is idempotent.

All item rows carry optimistic versions. Commands use short transactions and
compare-and-swap, so unrelated item commands can proceed concurrently without
lost updates. Lease sets are acquired atomically.

If state already exists, resume instead of initializing:

```bash
python scripts/pipeline.py --root .mission-control status
```

## Phase 0: define the mission

Record:

1. **Goal** — one paragraph defining done.
2. **Terminal condition** — drained backlog, completed-item cap, token budget,
   deadline, or a combination.
3. **Throughput posture** — ask whether to maximize throughput. In autonomous
   mode, maximize only when the work has real parallel slices and the repo
   oracle is reliable. Record decision maker and reasoning.
4. **Concurrency limits** — implementers 2, scouts 2, investigators 1 by
   default. Raise implementer width only when semantic targets can remain
   disjoint.
5. **Repo oracle** — build and test commands are mandatory before building;
   lint is optional.
6. **Execution policy** — prefer Docker or Podman with a pinned image. Native
   execution is an explicit degraded fallback and is always labeled as such.
7. **Merge target** — default is the symbolic current branch; configure
   `merge.target_ref` when detached or when another integration ref is desired.

## Phase 1: architecture gate

Spawn the Architect using `references/roles.md`. It produces prioritized,
constraint-carrying backlog items. If throughput is maximized, front-load
interfaces/scaffolding that unlock siblings and keep sibling predicted semantic
targets disjoint. Never manufacture filler.

Gate the initial backlog with the user, or with a Plan Reviewer in fully
autonomous mode. An ungated self-decomposing pipeline can invent work.

## Phase 2: continuous routing loop

At the start of every cycle run `status`. Act first on:

- `UNBLOCK CANDIDATE`;
- `MERGE CANDIDATE` or `MERGE RESOLUTION`;
- repeated semantic contention;
- `DIAGNOSIS READY`;
- unresolved agenda notes.

### Feed the plan side

When approved depth is below roughly twice implementer capacity, claim the
highest-value unclaimed items and spawn Scouts up to the configured limit.
One Scout owns one research document.

Before plan review, handle a Scout's `splittable: true` proposal. Only an
accepted proposal or another documented reshape signal returns work to the
Architect. Then run Plan Review. Signed low/medium plans become approved;
high/critical plans require written Orchestrator approval.

### Acquire semantic leases

Leases are hierarchical targets:

- `file`: a file or directory subtree;
- `symbol`: a Python class/function/async function, including parent/child
  hierarchy;
- `synthetic`: imports, globals, or module-member structure.

Examples:

```bash
python scripts/pipeline.py --root .mission-control lease MC-7 \
  --symbol src/query.py::Query.execute
python scripts/pipeline.py --root .mission-control lease MC-8 \
  --synthetic src/query.py::imports
python scripts/pipeline.py --root .mission-control lease MC-9 \
  --path generated/schema.json
```

The Python adapter uses `ast` and stable structural anchors. Unsupported,
generated, unparsable, renamed-file, comment-only, and otherwise unmappable
changes require a file lease. Sibling symbols can run concurrently; the same
symbol and parent/child symbols cannot. A file lease conflicts with every
semantic target beneath it. Never weaken a fallback to gain throughput.

Create a worktree only after acquiring every research target:

```bash
python scripts/pipeline.py --root .mission-control worktree-add MC-7
python scripts/pipeline.py --root .mission-control transition MC-7 building
```

### Build and verify privately

Implementers edit and commit only in their worktree. Build/test commands run
through the sandbox lifecycle:

```bash
python scripts/pipeline.py --root .mission-control sandbox prepare MC-7
python scripts/pipeline.py --root .mission-control sandbox run MC-7
```

The sandbox exports the commit into private source storage; it never mounts the
shared `.git` directory. Source, build, cache, and package directories are
separate. Container defaults disable networking, drop capabilities, prevent
privilege gain, limit resources, use private temporary storage, and make the
container root read-only.

Native mode retains private storage but cannot isolate the kernel, process,
credentials, or network. Its warning and `degraded_isolation: true` evidence
must never be suppressed. `wait-in-line.py` is deprecated; it exists only for
legacy host-side commands and warns on every invocation.

Before verification the CLI computes a semantic diff between the worktree base
and implementation commit. Every changed target must be covered by the lease
snapshot. Verifier evidence must seal passing sandbox evidence. Medium+ changes
then receive Code Review.

### Merge; never complete manually

Compatibility `ready-to-merge` maps to `merge-pending`. It does not bypass the
new lifecycle:

```bash
python scripts/pipeline.py --root .mission-control merge prepare MC-7
python scripts/pipeline.py --root .mission-control merge status MC-7
python scripts/pipeline.py --root .mission-control merge finalize MC-7
```

`merge prepare` clones privately, integrates the implementation, validates the
result against semantic leases, and writes merge evidence.

- Clean mechanical merges advance to post-merge verification.
- Text conflicts between disjoint Python sibling symbols may be combined
  mechanically, but still require Merge Agent output and Code Reviewer
  approval.
- Same-symbol, parent/child, file-fallback, or other overlapping semantic
  histories are invariants: the Merge Agent must not guess. Serialize, retry
  from a new base, or reshape the remaining backlog.
- Other resolvable conflicts go to the Merge Agent. Only
  `resolution_commit` and the embedded code-review record may complete the
  sealed conflict analysis.

`merge finalize` recomputes scope, runs the full sandbox against the integrated
commit, and publishes with `git update-ref <ref> <new> <expected-old>`. A CAS
loss returns the item to `merge-pending`; retry integration against the new
head. A failed post-merge sandbox does not publish and creates a reviewed
resolution task.

`complete` is deprecated. It can finalize only an already prepared
`post-merge-verifying` item; it never performs or bypasses merge preparation.
Only successful CAS publication marks queue and backlog done, removes the
worktree/branch, and releases leases.

### Escalations, budgets, and terminal conditions

Block an item when research is genuinely missing:

```bash
python scripts/pipeline.py --root .mission-control transition MC-7 blocked \
  --blocked-on MC-22 --note "..."
```

Blocking releases leases. Plan-side blocks return to research; build-side
blocks may return to approved; merge-side blocks return to merge-pending.
Bounce caps force chronic failures upstream rather than burning budget.

Pass known token spend with `transition --tokens N`; inspect `metrics`.
Count/token/deadline stops reject new claims, leases, worktrees, and build
starts while allowing in-flight gates and merges to finish safely.

## Reshaping

Only these signals license re-invoking the Architect over open backlog:

1. repeated semantic lease contention;
2. an accepted Scout split proposal;
3. bounce evidence pointing at decomposition;
4. a closed investigation dispositioned `architect`.

In-flight and done history is immutable. Reorganize only where it buys genuine
parallelism.

## Mid-mission user issues

Answer questions derivable from state directly. Anything requiring source
reading or reproduction becomes an investigation:

```bash
python scripts/pipeline.py --root .mission-control investigate open INV-1 "..."
```

The read-only Investigator writes `diagnosis.md`. The Orchestrator closes it as
`fix`, `architect`, or `no-action`. Fix items still pass ordinary gates.
Investigations are derived state; do not duplicate them in the agenda.

## Agenda discipline

Agenda notes hold only non-derivable intent: user directives, deferred
decisions, and scheduled follow-ups. Never record queue positions, free slots,
merge candidates, or unblock conditions; `status` computes those.

## Spawning discipline

Every brief must include:

- the exact role section from `references/roles.md`;
- the relevant contract from `references/contracts.md`;
- the evidence directory and item ID;
- worktree/sandbox paths and repo oracle where applicable;
- explicit prohibitions (for example Scout: no code; Reviewer: verdict, do not
  fix; Merge Agent: no invariant override).

Each role owns one artifact. Gates matter even when roles must run
sequentially.

## Audit and recovery

Run before declaring the mission complete:

```bash
python scripts/pipeline.py --root .mission-control audit
```

Audit verifies backlog/queue completion, artifact schemas and sealed hashes,
research and review gates, committed semantic scope, sandbox logs and hashes,
merge analysis/resolution, post-merge verification, ref ancestry, and cleanup.
It also audits closed investigations and reports open ones as holes.

After a crash, run `status`; SQLite/WAL and queue history recover the world.
`reclaim` returns stale build-side items to approved while preserving
worktrees. Merge-side leases remain held: finish, explicitly block, or inspect
and retry. Never delete unmerged work implicitly.

## References

- `references/contracts.md` — state, target, artifact, and transition schemas.
- `references/roles.md` — Architect, Scout, Plan Reviewer, Implementer,
  Verifier, Code Reviewer, Merge Agent, Investigator, and Designer briefs.
- `scripts/pipeline.py` — composition entrypoint; `--help` lists commands.
- `scripts/wait-in-line.py` — deprecated legacy mutex wrapper.
