# Terrain Studio continuation prompt

Resume Terrain Studio work as of **2026-08-03**, commit `36d37b2` on
`claude/terrain-architect-heightmap-sample-ls4sjv`.

## Governing directive — read this first

The user has explicitly and repeatedly overridden the earlier Mission-Control-heavy plan that used
to occupy this file:

> **Timebox reviews. 80% of the time should go to implementation of new functionality and fixing
> issues when found.**

In practice this means, for routine single-owner terrain-generation work:

- **Do not** open a Mission Control item, worktree, lease, or handoff for an ordinary bug fix or
  small feature. Just make the change, in the actual product source
  (`apps/terrain-studio/src/**`, `apps/terrain-studio/index.html`), and validate it directly.
- **Direct validation pattern that worked well this session** (fast, no ceremony):
  1. Start a throwaway dev server: `Start-Process -FilePath "cmd.exe" -ArgumentList "/c npx vite
     --port <free-port> --strictPort > vite.out.log 2>&1" -WindowStyle Hidden`, then poll
     `Invoke-WebRequest -Method Head` until it answers.
  2. Run the relevant oracle(s) directly with `node`, pointing `$env:STUDIO_URL` at that server.
     Legacy oracles under `tests/legacy/` mix ESM (top-level `await import`) and genuine CommonJS
     (`require`) despite sharing one directory `package.json`. If `node file.js` fails with
     `ReferenceError: require is not defined in ES module scope`, the file is really CommonJS —
     run it as-is. If it fails the other way, copy it to a `.temp.mjs` extension, run that, then
     delete the copy.
  3. For anything touching a generator's output field, write a short throwaway Playwright script
     (`playwright-core`, launch with `--use-gl=angle --use-angle=swiftshader
     --enable-unsafe-swiftshader --no-sandbox`, executablePath
     `C:\Program Files\Google\Chrome\Application\chrome.exe`) that calls `TYPES.<type>.eval(...)`
     in-page and asserts on real numbers (min/max/NaN count/diff fraction) — never trust exit code
     alone. Delete the script after.
  4. If the change alters a node's numeric output, run `node tests/legacy/_verify_digest.js` (no
     flags) first to see exactly which node types drifted. It should be **only** the type(s) you
     intentionally changed. Then re-baseline with `node tests/legacy/_verify_digest.js --write` and
     diff `_digest_baseline.json` to confirm the diff is scoped to those exact entries.
  5. `npm run build` once at the end as a cheap whole-bundle sanity check.
  6. Kill the throwaway server, delete `.log`/temp files, leave the tree clean before committing.
- **Commit as work lands** (authorised). **Do not push** (not authorised).
- Only reach for Mission Control (`C:\Users\AlexanderPino\.agents\skills\mission-control`,
  canonical root `C:\repos\GitHub\skills\.mission-control-plan`) for genuinely shared/high-risk
  work, real multi-agent lease contention, or the large runtime/migration items called out in
  `DELIVERY.md` — not for the kind of fix described above.
- Keep chat replies short. Record what landed in `PROGRESS.md`, not in a long conversational
  narration.

## What just landed (commit `36d37b2`)

- **Volcano centre spike**: fixed (Hermite-capped stratovolcano profile below `rn=0.12`).
- **Canyon edge/border weathering seam**: fixed (`canyonSurfaceExpression` now covers the full
  field instead of skipping the outermost 1px ring).
- **Volcano `age` param**: new, default `0` (bit-identical). Aging warps the footprint, degrades/
  breaches the rim, adds a hummocky crater floor.
- **Canyon `waypoints` param**: new, default empty (bit-identical). Text field (`x,y` per line) plus
  a graphical top-down click/drag plan-view editor ("Edit waypoints on terrain…" button on the
  Canyon node, mirroring the existing Draw Mask editor at `#drawEditor`/`openDrawEditor`). New
  editor lives at `#pathEditor`/`openPathEditor` in `src/legacy.js`.
- All four verified: relevant oracle suites green, digest 68/68 bit-identical (touching only the
  two intentionally-changed node types along the way), clean production build, and targeted
  Playwright smoke tests for the new numeric/UI behavior specifically (oracles don't exercise `age`
  or `waypoints` yet — that is deliberate, see below).
- Full detail: `PROGRESS.md` "DIRECT FIX PASS — 2026-08-03" entry.

### Deliberately not done as part of that pass

- The legacy oracles (`_verify_landforms.js`, `_verify_all_canyon.js`) do not yet exercise
  `age`/`waypoints` themselves (only smoke-tested ad hoc). If you touch volcano or canyon again,
  consider whether it's worth adding a permanent oracle case for these — optional, not required,
  weigh against the 80% directive.
- **Mountain ranges via waypoints**: no new code needed. The existing **Layout** node
  (`src/plugins/gen/layout.js`, `parseLayout`/`layoutField` in `legacy.js`) already supports
  drawing a `path` shape with per-vertex elevation, width, falloff, and profile — that is the
  waypoint-authored ridgeline tool. Point users at it rather than rebuilding it.

## Next candidates, roughly in order of value for the time spent

1. If the user reports more visual/behavioral bugs: fix them directly using the pattern above.
   This is almost always higher value than any of the below.
2. Consider whether the Layout node's path editor and the new Canyon waypoint editor should be
   unified (they are two separate, nearly-identical top-down click/drag canvases). Not urgent —
   only worth it if a third node needs the same kind of editor, or if maintaining both starts
   causing bugs.
3. The larger, already-designed-but-unstarted backlog (ADRs exist, zero code written):
   - **Boundary Landforms** node — hills/mountains/cliffs along selected world edges. Described in
     `docs/plan/sprint-07-geology-and-regimes.md` story S7.6.
   - **Arbitrary raster dimensions** (including exact `16384x16384`, `1573x13789`, no power-of-two
     rounding) — `docs/adr-009-arbitrary-raster-gpu-authoring.md`,
     `docs/plan/sprint-09-large-worlds.md` S9.9.
   - **GPU-only "gpu-required-paged" execution mode** (forbids CPU terrain-field computation at
     those sizes) — same ADR-009, `docs/plan/sprint-10-runtime-extreme-detail.md` S10.8.
   - **Walkaround / traversal / reachability** — doll placement, Rapier WASM capsule controller,
     walk/run/jump only (no flight), WebGPU reachability —
     `docs/adr-010-walkaround-traversal-inspection.md`, S10.9.
   These are genuinely large (each is many-day scope even solo); if picked up, still favor direct
   implementation over ceremony, but do check `DELIVERY.md`'s risk-based gate table since these are
   exactly the "runtime/migration" class of work it flags as warranting more evidence.

## Where things physically are

- Product source: `apps/terrain-studio/src/**`, `apps/terrain-studio/index.html`.
- Legacy oracles: `apps/terrain-studio/tests/legacy/_verify_*.js` (aggregate:
  `_verify_all_canyon.js` for canyon; there is no single aggregate for landforms — run
  `_verify_landforms.js` directly). Digest oracle + baseline:
  `tests/legacy/_verify_digest.js` / `tests/legacy/_digest_baseline.json`.
- Run locally: `.\run-studio.ps1` from repo root (dev mode, HMR, no PWA cache in the way).
- Position/history: `PROGRESS.md` (position), `BACKLOG.md` (findings/decisions),
  `docs/plan/DELIVERY.md` (execution policy, still valid for anything that actually needs it).

## Standing permissions (from `CLAUDE.md`, unchanged)

- Commits: authorised. Push: **not** authorised — ask first.
- Sub-agents/workflows: authorised, no need to ask.
- Stop only for a real user decision, an unsafe/irreversible action, a finding that invalidates the
  plan, or a genuinely empty queue. A completed fix, passing gate, or landed commit is not a stopping
  point — keep going to the next item.

## Superseded material (Mission Control delivery-recovery plan)

Everything below this line is the **prior** plan, from before the 80%-implementation directive. It
is kept only for archaeology on the still-open `MC-S33`/`MC-S04` infrastructure items in case someone
resumes that specific thread. Do not default to it — the governing directive above takes priority for
any ordinary product work.

Read [docs/plan/DELIVERY.md](docs/plan/DELIVERY.md) first if you do pick this thread back up. It is
the canonical execution policy: focused evidence per changed slice, exhaustive evidence once per
integrated wave, risk-based review, and Mission Control only where shared/high-risk work or real
contention justifies it.

### Visible checklist (stale — MC-S33/MC-S04 status unverified since 2026-08-02)

- [ ] Diagnose and green the MC-S33 runner contract
- [ ] Review, integrate, and publish MC-S33
- [ ] Replay S1.3–S1.5 once on the published runner and close Sprint 1
- [ ] Publish the S2 typed-port keystone
- [ ] Start cover/state, Gerstner, graph-machinery, and large-world lanes in parallel
- [ ] Integrate S3–S5, then S6/S8/S9
- [ ] Calibrate S10.R0 and deliver S10
- [ ] Deliver exact arbitrary dimensions, 16K GPU-only evaluation, Boundary Landforms, and Walkaround
- [ ] Pass the final integrated quality gate and audit

### Non-negotiable operating rules (for the MC-S33/MC-S04 thread specifically)

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
- Keep routing through phase and wave boundaries; stop only for a real user decision, unsafe action,
  invalidated plan, or drained queue.

### Start here (if resuming the MC-S33/MC-S04 thread)

From `C:\repos\GitHub\skills`:

```powershell
$pipeline = 'C:\Users\AlexanderPino\.agents\skills\mission-control\scripts\pipeline.py'
$root = 'C:\repos\GitHub\skills\.mission-control-plan'
python $pipeline --root $root status
python $pipeline --root $root metrics
git status --short
git log -8 --oneline
```

State as of 2026-08-02 (unverified since):

- Integration product baseline at `97d163f`, with delivery-document edits in progress.
- Canonical done: `MC-S30`, `MC-S31`, `MC-S32`.
- S1.0, S1.1, S1.2 marked `DONE`.
- `MC-S04` is `verifying`, commit `3ebcb8d`, 19 leases, verdict `oracle-broken` only because the
  inherited runner cannot grade exact commands under Node 25/fixed-port reuse.
- `MC-S33` is `building`, seven leases, no commit/handoff yet.
- Approved waiting items: `MC-S01`, `MC-S21`, `MC-S25`.

If state differs, trust canonical SQLite and current Git over this prompt; explain the delta in
`PROGRESS.md` before proceeding.

### Priority 1 — finish MC-S33 without weakening evidence

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

### Priority 2 — retry MC-S04 on the published runner base

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

### Priority 3 — publish the keystone and fan out

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

### Product roadmap snapshot

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

### Status discipline

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
