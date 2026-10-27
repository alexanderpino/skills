# Round 5 adjudication

Ground truth: current `data/*.json`, `docs/`, `scripts/check.py` (0 errors, 0 warnings before this review). 42 dispositions reviewed (partial/reject; no merges are recorded in dispositions.md): 33 upheld, 9 overturned (K-ARCH-14, K-FUTURE-1, K-PLATFORM-3, K-PLATFORM-5, K-PROD-5, K-TEST-2, K-TEST-9, K-TEST-10, K-TOOLS-11). Overturns are small mechanical remainders; K-TOOLS-11 is a weak overturn.

| Finding | Disposition | Verdict | Reason |
|---|---|---|---|
| K-ARCH-9 | reject | UPHELD | C-EDCMD and C-EDIT already require C-CMD; the owner/implementer split is deliberate. GAM.FW.turns is a game-level turn log, not the edit-command core, so the residue is summary prose. |
| K-ARCH-14 | partial | OVERTURNED | An xl tier is rightly refused (workstreams are the co-hosting unit, independence is proven per tier). But ARCH.ORG.independence still promises "co-hosting capped by capability count", which check.py does not enforce and the small tier (12 workstreams, one agent) contradicts. Reword the claim. |
| K-ARCH-16 | reject | UPHELD | Contract listings are generated into SKILL.md and check.py requires leads to own a contract; purpose omissions are polish. |
| K-ARCH-17 | partial | UPHELD | Understated edges are mostly to universal or M0 contracts (C-FLOW, C-RES, C-INSTANCES) that are always present, so closure loses nothing. The change log's claim that all named cases were reconciled is overstated, but a general "informs" lint is not warranted. |
| K-COMPLETE-1 | reject | UPHELD | XC.SEC.data-rights owns inventory, retention and the data-subject request flow, is gated M2 (validator QA.CERT.privacy), and the personal-data cross-cutting rule requires every skill to declare a deletion path. (The verifier's "C-PRIVACY" does not exist, but the coverage conclusion holds.) |
| K-COMPLETE-2 | reject | UPHELD | Physical media is a niche SKU variant; RES.IO.media-policy and the PLAT.CON packaging stubs cover the engine-visible seek and patch behavior. Minor. |
| K-FUTURE-1 | partial | OVERTURNED | The radar `_doc` sets the rule "M requires two shipped titles with postmortems; one title or research evidence is X". Six M entries still contradict their own evidence or revisit text (see Required fixes). Only the numeric check can stay out. |
| K-FUTURE-4 | reject | UPHELD | The WebGPU-only stance and its measurable reversal trigger are recorded (docs/00, docs/09); reserving a slot for a hypothetical reversal is speculative. |
| K-LEGACY-10 | reject | UPHELD | C-ANIM already says animation events are delivered as batched outputs via C-FLOW; nothing states an immediate callback. |
| K-NET-2 | reject | UPHELD | Consistent with round 4 K-NET-6 and docs/00 line 125: input-only netcode families are separate add-ons and relay or referee servers are external. No new evidence. |
| K-NET-3 | reject | UPHELD | Relay and directory operation is backend service scope (docs/06 C.3, network-transport non-responsibility). No new evidence. |
| K-NET-5 | reject | UPHELD | C-PHYS carries collider history and is needs_implementer; C-REWIND assembles providers. Consistent with round 4 K-ARCH-8: extra optional edges from physics-2d and others add nothing. |
| K-NET-9 | reject | UPHELD | NET.TRANS.web already lists WebRTC unreliable channels and WebSocket fallback beside WebTransport. |
| K-NET-14 | reject | UPHELD | Membership means "may be built" (docs/06 C.4); a mandatory pairs_with rule is process preference with no failure mode. |
| K-PERF-2 | partial | UPHELD | M2 gates PRF.GPU.power (sustained state) and C-BENCH specifies thermal-soak. A thermal-signal governor gate cannot exist before M3, where CORE.SCALE.governor is gated. |
| K-PERF-4 | partial | UPHELD | PRF.BENCH.proxy-metrics is gated at M0 and PRF.BENCH.lab at M1 (validator BLD.CI.device-lanes). Per-platform lab gates at M2/M3 are extension, not a defect. |
| K-PERF-7 | reject | UPHELD | C-BUDGET already has one input-to-photon latency line per refresh class and netcode family; PRF.NET.latency lists frame-orchestration. Cosmetic. |
| K-PERF-8 | reject | UPHELD | Maturity classes describe technique maturity, not host availability. Relabeling would misapply the scheme. |
| K-PLATFORM-1 | partial | UPHELD | DESK/MOB/WEB.backend-slots now exist with domain skills as contributors. needs_implementer is per contract, not per capability, so marking slot contracts adds nothing (cf. round 3 K-PLATFORM-1). |
| K-PLATFORM-3 | partial | OVERTURNED | Data-class rules cover tiers, DDC, symbols and captures but omit the first-named classes: console SDK version pins, cert minimums and compiler matrix, still held by non-NDA BLD.SYS.platform-sdks and QA.CERT.prechecks. No split is needed; wording closes it. |
| K-PLATFORM-5 | partial | OVERTURNED | No new variant or configuration is fine (cloud-render-host is X). But platform-server-host's purpose still says "no display or GPU" while it now owns PLAT.SRV.gpu-host. Reword the purpose. |
| K-PLATFORM-8 | partial | UPHELD | Mobile-AR contributor added. Tagging xr-runtime platforms would need pc, mobile, xr-standalone and console and risks dropping it from configurations; consistent with round 4 K-PLATFORM-8 (domain owns, platform contributes). |
| K-PROD-4 | partial | UPHELD | A rule that a validator's gate is no later than the gated milestone would force gating of 21 validators; gate-canaries (M0) already keeps every gate and oracle exercised and all process skills are staffed from M0 (round 4 K-TEST-1). Round 4 itself chose prechecks for incident. Real mismatches are handled under K-PROD-5 and K-TEST-2. |
| K-PROD-5 | partial | OVERTURNED | Independence blocks security-owned validators for security gates, but not the proposed release-rehearsal capability owned by functional-automation-soak. M4 exit says patch, DLC, staged rollout and rollback are "executed", yet BLD.REL.rollback is validated by release-criteria (a definition, gated M7), staged-rollout by compat-corpus, PLAT.LIVE.operations by soak. Nothing runs them. |
| K-PROD-7 | reject | UPHELD | ARCH.ORG.scope-control owns the descope order and human-capacity owns capacity and SLA. Deferring M0 skills contradicts the checked walking-skeleton closure. |
| K-PROD-8 | reject | UPHELD | C-BUDGET is a process contract; M0 exit says "v0" and later tier lines are additive data. |
| K-PROD-9 | reject | UPHELD | Not every capability is gated (roughly 100 are). The sample ladder rides the reference games and creator-panel sampling is in human-capacity (round 4 K-PROD-7). A C-DOCS contract is speculative. |
| K-PROD-10 | reject | UPHELD | Marketplace and partner or support tiers are commercial/backend scope (docs/06 C.3, round 4 K-PROD-1). |
| K-RENDER-5 | partial | UPHELD | path-tracing leaves lite3d closures; software RT stays. Reference tracer in std3d clients is removed by dev-surface exclusion and shipping-delta gates; a dev-only closure check is not required. |
| K-SEC-8 | reject | UPHELD | Server backup, KMS and retention is backend operation (docs/06 C.3); XC.SEC.data-rights carries retention and request flow. |
| K-SEC-9 | reject | UPHELD | Ingestion workers are backend; crash-diagnostics and telemetry already validate crash-uploads and telemetry-batches, so naming them parser_owners is redundant. |
| K-SIM-6 | reject | UPHELD | NET.PRED.physics-lockstep is limited to backends declaring the deterministic level; CORE.MATH.deterministic is now X with an A4 radar entry and fixed-point fallback. Row split is redundant. |
| K-SYSTEMS-6 | partial | UPHELD | C-LIFETIME and C-RES edges added. C-CFG to C-MEM/C-TYPES is a deliberate bootstrap decision (allocator budgets read config; C-BASE has the raw allocator). The remainder is an understated edge with no failure mode. |
| K-TEST-2 | partial | OVERTURNED | Golden and stability were re-pointed, but unaddressed mismatches have exact fixes: RES.MGMT.validation is validated by load-time analysis although QA.SIM.streaming exists for that oracle; transactions and cross-server are validated by load tests although QA.ROBUST.distributed-faults (added this round) checks idempotency and hand-off; M7 release-criteria stays circular-ish. New evidence over round 4 (which chose QA.FUNC.load before distributed-faults existed). exercised_by/known_red fields stay out. |
| K-TEST-7 | partial | UPHELD | test_double.real_backend_lane is required on boundary contracts by check.py (line 390) and QA.STRAT.contract-fakes states a periodic differential. The remainder is only cadence text. |
| K-TEST-9 | reject | OVERTURNED | Contract-level oracle authors are independent, but NET.ARCH.validation (network-architect defines thresholds, co-sign only), UI.A11Y.validation and CNT.COOK.determinism-check are still worded as implementer-owned validation, exactly what round 4 K-ARCH-4 and K-TEST-4 fixed with hooks-only wording. Reword only; ownership unchanged. RND.PT.reference, RND.SHADER.precision and RND.RHI.* stay (independently validated or run-only). |
| K-TEST-10 | partial | OVERTURNED | freeze_requires is rightly not added (per-contract oracle-author independence is machine-checked). But the independence pair `test-architect / owning-skill / oracle author vs implementer` is stale: test-architect is oracle author of no contract (27 contracts sit with simulation-validation, 24 render-validation, and so on). Fix the reason text. |
| K-TEST-12 | reject | UPHELD | ML.RT.validation names conformance tolerance tables and model-version regression; the remaining eval-set idea is speculative on M/X features with fallbacks. |
| K-TOOLS-1 | reject | UPHELD | C-CMD is drafted at M0 and frozen at M2; editor contracts freezing at M2 to M3 with headless commandlets is the reasoned ladder (round 4 K-TOOLS-3). |
| K-TOOLS-7 | reject | UPHELD | The shared schema is C-CMD, which C-EDCMD requires; freezing it after C-EDCMD would violate freeze order. |
| K-TOOLS-9 | reject | UPHELD | Live-ops data goes through C-GAMEDATA tooling and CNT.VAL.submit-gate; remote-config changes are on the human-gates register; backend services are out of scope. |
| K-TOOLS-11 | reject | OVERTURNED | Weak, minor. Gizmos, splines and the outliner must stay untagged (2D and ortho use), as the verifier says. But ED.WORLD.blockout (primitives, booleans, UVs), ED.WORLD.mesh-paint and ED.WORLD.color-management (HDR preview) are 3D-only, and untagged peers such as ED.WORLD.partitioned already carry lite3d/std3d tags. Tag those three. |

## Required fixes

Run `python3 scripts/check.py` after the edits and regenerate the docs (`scripts/render.py`). Ids below all exist unless marked new.

### 1. K-ARCH-14 (wording)
`data/capabilities.json`, ARCH.ORG.independence: delete the trailing clause `; co-hosting capped by capability count` and append `; the co-hosting unit is the workstream (data/organizations.json tiers), and per-agent load is bounded by tier choice and ARCH.ORG.human-capacity, not by a capability-count cap`. No tier or check.py change.

### 2. K-FUTURE-1 (six radar rows to X)
For each of ANM.SYN.learned, ANM.DEF.ml, GAM.AI.learned, ML.RT.os-models, XC.EXT.generated-assets, ED.COLLAB.concurrent-world in `data/capabilities.json` set maturity `M` to `X` and profiles to exactly `["experimental"]` (ED.COLLAB.concurrent-world currently has `["team-large"]`; replace it). In `data/radar.json`:
- Entries "ML deformers", "Learned motion & neural controllers", "Learned & LLM-driven agents", "Conflict-free concurrent world editing", "Player-prompted runtime asset generation": change `class` from `M` to `X`; keep fallbacks; keep `reviewed` current.
- Entry "OS model APIs, weight residency & local/remote routing": split it. Remove ML.RT.os-models from it (keep ML.RT.residency and ML.RT.local-remote as class M). Add a new entry: tech "OS-provided foundation-model APIs as a backend", class `X`, owner `ml-inference-runtime`, capabilities `["ML.RT.os-models"]`, evidence "Windows ML GA, Apple Foundation Models, Android AICore announced (2025); no shipped title with a postmortem", revisit "Two shipped titles using an OS model API, with postmortems", fallback "Engine-packaged models", reviewed "2026-09-30".
- Optional: add to the radar `_doc` "Program-level entries (ARCH.ORG.*) are judged by their human fallback." Do not add a shipped_titles field or numeric check.

### 3. K-PLATFORM-3 (wording; avoid the words "confidential" and "console SDK" in capability names, they trigger check.py's CONFIDENTIAL rule)
- BLD.SYS.platform-sdks name: `Platform SDK version management & store/cert-mandated minimums (public SDKs only; holder-platform SDK pins, cert minimums and compiler matrices are per-holder data under PLAT.PAL.confidential-extensions)`.
- PLAT.PAL.confidential-extensions name: append `; SDK version pins, cert-mandated minimums and compiler matrices of holder platforms join the per-holder partitions, with only a public envelope in BLD.SYS.platform-sdks and BLD.SYS.toolchains`.
- QA.CERT.prechecks name: `Automated certification pre-checks (public and non-holder checks; holder pre-submission checkers belong to PLAT.CON.submission)`.

### 4. K-PLATFORM-5 (wording)
`data/skills.json`, skill platform-server-host, purpose: replace `no display or GPU,` with `no display (headless GPU only through PLAT.SRV.gpu-host: offscreen surfaces, container GPU passthrough, hardware encode),`.

### 5. K-PROD-5 (release rehearsal drill)
- Add capability `QA.FUNC.release-rehearsal`: "Release rehearsal drills on the online reference game: patch, DLC, staged rollout with halt, rollback and roll-forward, live-ops runbook and incident drills, key-rotation and revocation drill, vulnerability-disclosure SLA drill; records executed evidence per gate", owner `functional-automation-soak`, maturity `E`, contributors `["packaging-release-patching", "online-services-liveops", "security-engineering", "reference-games"]`, in area QA.FUNC.
- `data/milestones.json` M4 gates: change validator of `BLD.REL.rollback` from `QA.STRAT.release-criteria` to `QA.FUNC.release-rehearsal`; of `BLD.REL.staged-rollout` from `QA.FUNC.compat-corpus` to `QA.FUNC.release-rehearsal`; of `PLAT.LIVE.operations` from `QA.FUNC.soak` to `QA.FUNC.release-rehearsal`. Leave BLD.REL.patching and BLD.REL.dlc on compat-corpus and XC.SEC.incident on QA.CERT.prechecks (round 4 K-SEC-4). Independence holds (gated owners packaging-release-patching and online-services-liveops differ from functional-automation-soak; workstream quality is not governance). No cycle: the new capability is not itself gated.
- M4 exit: after "patch + DLC + staged rollout + rollback executed on the online reference game" add "(QA.FUNC.release-rehearsal validates rollout, rollback and live-ops)". Mirror in the docs/09 M4 gate list and exit.

### 6. K-TEST-2 (three re-points)
`data/milestones.json`:
- M5 gate `RES.MGMT.validation`: validator `PRF.LOAD.load-time` to `QA.SIM.streaming` (owner simulation-validation differs from resource-streaming-architect).
- M4 gate `NET.SRV.transactions`: validator `QA.FUNC.load` to `QA.ROBUST.distributed-faults`. M6 gate `NET.SRV.cross-server`: validator `QA.FUNC.load` to `QA.ROBUST.distributed-faults`. (QA.ROBUST.distributed-faults is itself gated at M6 by QA.FUNC.load; no cycle; owner robustness-fuzzing differs from server-scaleout-persistence.)
- M7 gate `QA.STRAT.release-criteria`: validator `QA.FUNC.compat-corpus` to `QA.FUNC.release-rehearsal` (new capability from fix 5; owner functional-automation-soak differs from test-architect).
Update the docs/09 gate lists (M4, M5, M6, M7). Do not add exercised_by/known_red fields.

### 7. K-TEST-9 (hooks-only wording; owners and contributors unchanged)
- NET.ARCH.validation name: `Netcode validation hooks: reference scenes incl. host-drop and threshold proposals only; scenario suites and acceptance thresholds belong to the contracts' oracle_author (simulation-validation)`.
- UI.A11Y.validation name: `Accessibility validation hooks (reference scenes and threshold proposals only; suite authorship belongs to the contract's oracle_author, ui-text-conformance)`.
- CNT.COOK.determinism-check name: `Cook determinism hooks (reference inputs and threshold proposals only; suite authorship belongs to the contract's oracle_author, tools-pipeline-conformance)`.

### 8. K-TEST-10 (stale pair text)
`data/crosscutting.json` independence entry `["test-architect", "owning-skill", "oracle author vs implementer"]`: change the reason to `test policy, definition-of-done and canary owner vs implementer (per-contract oracle_author independence is checked per contract and per tier by check.py)`. Mirror the row in docs/04 line 51. Keep the pair itself.

### 9. K-TOOLS-11 (weak; profile tags only)
`data/capabilities.json`: add profiles `["lite3d", "std3d"]` to ED.WORLD.blockout and ED.WORLD.mesh-paint, and `["std3d"]` to ED.WORLD.color-management (same tuple position as ED.WORLD.partitioned). Leave ED.WORLD.gizmos, ED.WORLD.splines and ED.UI.outliner untagged.
