# Terrain Studio continuation prompt

Resume the Terrain Studio implementation mission from delivery recovery on 2026-08-02.

Read [docs/plan/DELIVERY.md](docs/plan/DELIVERY.md) first. It is the canonical execution policy:
focused evidence per changed slice, exhaustive evidence once per integrated wave, risk-based review,
and Mission Control only where shared/high-risk work or real contention justifies it.

## Visible checklist

- [ ] Diagnose and green the MC-S33 runner contract
- [ ] Review, integrate, and publish MC-S33
- [ ] Replay S1.3–S1.5 once on the published runner and close Sprint 1
- [ ] Publish the S2 typed-port keystone
- [ ] Start cover/state, Gerstner, graph-machinery, and large-world lanes in parallel
- [ ] Integrate S3–S5, then S6/S8/S9
- [ ] Calibrate S10.R0 and deliver S10
- [ ] Deliver exact arbitrary dimensions, 16K GPU-only evaluation, Boundary Landforms, and Walkaround
- [ ] Pass the final integrated quality gate and audit

## Non-negotiable operating rules

- When Mission Control is warranted by `DELIVERY.md`, use only the **installed** skill:
  `C:\Users\AlexanderPino\.agents\skills\mission-control`.
- Use the **installed** Terrain Architect skill for every terrain-generation design, implementation,
  review, debugging, grounding, and verification decision:
  `C:\Users\AlexanderPino\.agents\skills\terrain-architect`.
- Treat that installed Terrain Architect corpus as authoritative. Read its `SKILL.md` and route to
  the relevant installed `references/` or `reference-impl/` material rather than reconstructing
  algorithms, constants, units, provenance, or verification criteria from memory.
- Canonical runtime root:
  `C:\repos\GitHub\skills\.mission-control-plan`.
- Do not read, execute, or modify the repository's tracked `mission-control/` skill.
- `apps/terrain-studio/docs/plan/README.md` plus Sprint 1–10 documents are the canonical story queue.
- ADRs 001–008 and `docs/plan/GROUNDING.md` are normative.
- Do not skip, weaken, silently rebaseline, or grandfather an oracle. Empty evidence is red.
- Apply readiness per story. An unresolved claim blocks that story and its consumers, not unrelated
  grounded work.
- Do not mark a story `DONE` until its focused/change-class evidence, integrated-wave gate, and
  integration commit are recorded in `PROGRESS.md`.
- Do not repeat an unchanged artifact's build, visual matrix, negative-control arming, or review
  without a source/toolchain/input identity change.
- Commits are authorized. Push is not authorized.
- Keep routing through phase and wave boundaries; stop only for a real user decision, unsafe action,
  invalidated plan, or drained queue.

## Start here

From `C:\repos\GitHub\skills`:

```powershell
$pipeline = 'C:\Users\AlexanderPino\.agents\skills\mission-control\scripts\pipeline.py'
$root = 'C:\repos\GitHub\skills\.mission-control-plan'
python $pipeline --root $root status
python $pipeline --root $root metrics
git status --short
git log -8 --oneline
```

Expected recovery state:

- Integration product baseline at `97d163f`, with delivery-document edits in progress.
- Canonical done: `MC-S30`, `MC-S31`, `MC-S32`.
- S1.0, S1.1, S1.2 marked `DONE`.
- `MC-S04` is `verifying`, commit `3ebcb8d`, 19 leases, verdict `oracle-broken` only because the
  inherited runner cannot grade exact commands under Node 25/fixed-port reuse.
- `MC-S33` is `building`, seven leases, no commit/handoff yet.
- Approved waiting items: `MC-S01`, `MC-S21`, `MC-S25`.

If state differs, trust canonical SQLite and current Git over this prompt; explain the delta in
`PROGRESS.md` before proceeding.

## Priority 1 — finish MC-S33 without weakening evidence

Worktree:
`C:\repos\GitHub\skills\.mission-control-plan\worktrees\MC-S33`

Reviewed scope is exactly:

- `apps/terrain-studio/scripts/isolated-verify-runner.mjs`
- `apps/terrain-studio/scripts/build-cache.mjs`
- `apps/terrain-studio/scripts/legacy-oracle-bootstrap.cjs`
- `apps/terrain-studio/scripts/run-legacy-verify.mjs`
- `apps/terrain-studio/scripts/sweep-oracles.mjs`
- `apps/terrain-studio/package.json`
- `apps/terrain-studio/tests/runner/isolated-verify-runner.test.mjs`

Current uncommitted state includes those files plus untracked
`apps/terrain-studio/runner-focused.log`. That log is not leased product scope; move its evidence into
canonical MC-S33 evidence or delete it after preserving needed output. Do not commit it casually.

The latest `npm run verify:all` exited 1. Inspect the complete output and identify whether the failure
is:

1. a runner implementation defect;
2. a selected legacy oracle with missing positive evidence; or
3. an already known product failure.

Fix only (1) inside MC-S33. For (2), keep the strict suite red and name the evidence debt; do not add
filename exceptions or weaken parsing. For (3), create a separate ordinary fix item.

Required MC-S33 gates from its research/approval:

- runner `node:test` suite, non-zero test count;
- unknown/excluded/zero selected cases red;
- empty output red;
- status-zero output without admitted positive assertion evidence red;
- bridge `--check` and PWA `--preview-prod` flags preserved;
- byte-identical CommonJS/module oracle execution with source hash validation;
- unique OS-selected strict ports and private browser/TEMP roots;
- token/ownership proof and zero owned processes after success, failure, timeout, and cancellation;
- foreign control process survives cleanup;
- deterministic dist-only cache: hit, miss, source/env/mode/tool invalidation, tamper red;
- no oracle bytes, baselines, product source, Vite config, or lockfile changed.

When green for its actual contract: commit MC-S33, write schema-valid canonical `handoff.md`, transition
through verifying, independent code review, merge prepare/finalize, and CAS publish.

## Priority 2 — retry MC-S04 on the published runner base

After MC-S33 is canonical `done` and target HEAD equals its merge result:

- Create `MC-S45` with `origin: split:MC-S04`, dependency `MC-S33`, and canonical S1.3–S1.5 scope.
- Do not rewrite/rebase MC-S04 history or evidence.
- Replay `ee56b0b` and `3ebcb8d` onto the new published HEAD in a fresh approved worktree.
- Prove the replayed product bytes match the reviewed MC-S04 product commits, then run through MC-S33:
  - focused source and built filter/coordinate/aspect gates;
  - reviewed mutation gates green, referencing their already-recorded red endpoints;
  - `npm run plugins:check`;
  - `npm run bridge:check`;
  - `npm run verify -- _verify_blur_isotropy.js`;
  - direct/CommonJS/built digest repeat, 79/79, zero skips;
  - selected five-oracle sweep with source identity;
  - one production build and the integrated-wave gate.
- Do not recapture an unchanged visual matrix. Recapture only if product/source identity differs or
  an integration spot-check detects drift.
- Complete one integration review, merge, and publication. Do not repeat separate reviews of the
  byte-identical product at each transition.
- Only after publication mark S1.3, S1.4, and S1.5 `DONE` in the plan and `PROGRESS.md`.

## Priority 3 — publish the keystone and fan out

After Sprint 1 closes, make S2 the primary lane: `MC-S01` then `MC-S02`. In parallel, route the
already-independent S9 domain/dialog/import work (`MC-S21`) and S10 capability probe (`MC-S25`) when
their exact ownership is disjoint.

After typed ports publish, start the first four real parallel bundles:

1. cover/state foundation — `MC-S05`;
2. Gerstner renderer foundation — `MC-S09`;
3. graph machinery — `MC-S18`;
4. large-world evaluator/regions — `MC-S22`.

Do not create extraction scaffolds speculatively. Extract field/context, evaluator/document, or
renderer/water boundaries only when two ready bundles demonstrably contend on the same file. The
extraction owns parity only, lands before its dependants, and may not duplicate story behavior.

Use at most four implementation lanes. Prefer the item that unlocks the most ready dependants, and
continue unrelated lanes whenever one is blocked.

## Product roadmap snapshot

- Sprint 1: S1.0–S1.2 DONE; S1.3–S1.5 implemented in MC-S04 but not published.
- Sprint 2–8: queued per canonical dependency graph.
- Sprint 4 includes AAA hybrid Gerstner water stories S4.7–S4.10.
- Sprint 9: 61-point large-world plan, user-authored 0.5 m cells, budget-derived evaluation regions,
  New Terrain dialog, import dimensions/provenance, global substrate + bounded tiled detail. ADR 009
  extends it to 66 points with exact arbitrary sample dimensions, including `16384 x 16384` and
  `1573 x 13789`, partial terminal pages, and no power-of-two rounding.
- Sprint 10: 81-point **cook-free** Extreme Detail plan. No Nanite/cluster cooking. WebGPU runtime
  fixed-topology heightfield clipmaps, streamed field pages, GPU visibility/LOD/instanced indirect
  buckets, bounded residency, camera-relative precision, capability modal, complete GPU-only paged
  terrain evaluation, and ADR 010 Walkaround/reachability. Walkaround is doll-placed, fixed-step
  walk/run/jump with no flight; collision is bounded Rapier WASM and reachability is WebGPU. S10.R0
  calibration must close before Sprint 10 becomes technically refined/Ready.
- Sprint 7 now includes the independently routable GPU-native Boundary Landforms node for selected
  border hills, mountain chains, and heightfield cliffs.
- Current programme total: 417 points.

## Status discipline

Update `apps/terrain-studio/PROGRESS.md` and its visible checklist as work lands. Keep chat short.
Record:

- item and story IDs;
- integration commit;
- focused and built gates;
- mutation red endpoint count;
- digest type/skip count;
- residual blockers and next item.

Do not record repeated evidence for an unchanged artifact. Link its validated content identity and
record only the new focused or integrated-wave result.

Do not claim all-sprint completion until Mission Control backlog is drained and final audit passes.
