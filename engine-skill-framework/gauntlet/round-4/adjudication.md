# Round 4 adjudication

Ground truth: current data/*.json and docs/. 41 dispositions reviewed (partial/reject/merge); 33 upheld, 8 overturned.

| Finding | Disposition | Verdict | Reason |
|---|---|---|---|
| K-ARCH-2 | reject | UPHELD | docs/06 C.4 records membership as 'may be built'; reference game proves use. No new evidence. |
| K-ARCH-4 | partial | UPHELD | Hooks-only wording now on PHY/ANM/AUD/GAM.AI/RES.MGMT/UI.FW validation; QA.SIM.navigation and QA.SIM.streaming exist. A data check for owner==implementer markers is a process nicety, not a defect. |
| K-ARCH-5 | partial | UPHELD | foundation-conformance and ui-text-conformance exist and C-MATH/C-SYNC/C-TEXT are re-pointed; keeping robustness-fuzzing for parsers/faults is consistent with the proposal. |
| K-ARCH-6 | reject | UPHELD | C-ORCH is frozen at M0, BLD.CI.sealed-suites is owned by a tool skill, and coordination is an emerging radar row with a human-coordinator fallback (docs/09). Ledger/lease service ownership is a meta-program concern, not an engine defect. |
| K-ARCH-8 | partial | UPHELD | C-REWIND (L3, owner prediction-rollback, oracle simulation-validation) exists and is consumed by gameplay-systems-toolkit; needs_implementer for physics/animation adds nothing given existing optional edges. |
| K-ARCH-12 | partial | OVERTURNED | C-A11Y is still the only contract never frozen (checked in milestones.json), and it is a hard requirement of cinematics, gameplay and narrative skills at M1. Freezing it is a one-line data change. |
| K-COMPLETE-5 | reject | UPHELD | Time-gated activation is owned by PLAT.LIVE.events with trusted-time; tz/DST is implementation detail of that capability. |
| K-FUTURE-2 | partial | UPHELD | radar.json has as_of, max_age_days and reviewed dates with a check; typed evidence_refs is polish. |
| K-FUTURE-3 | partial | UPHELD | PLAT.PAL.cloud-render-host exists in capabilities and radar; a new target value would need configurations and closure machinery for a maturity-M future case. |
| K-FUTURE-7 | reject | UPHELD | WebGL non-goal with measured-share revisit trigger is a recorded decision; no new evidence. |
| K-GAMEPLAY-6 | reject | UPHELD | Narrative-centric minimal profile is not evidenced; portrait staging and text reveal are game-level content (docs/06 C.2). |
| K-LEGACY-2 | reject | UPHELD | Baked GI/PVS as low-tier fallbacks is recorded (docs/06 B5); using them as stance capabilities of an anti-baked pattern is incoherent. |
| K-LEGACY-3 | reject | UPHELD | Thread-per-subsystem is covered by L79, blocking IO by L16, budgeted allocation by L66. Wall-clock timers and sync save are catalogue wishes, not material. |
| K-LEGACY-7 | reject | UPHELD | Bare term 'level' in contradiction_terms would false-positive; L18/L39/WLD.MODEL.strategy already stance partitioned worlds. |
| K-LEGACY-8 | reject | UPHELD | CORE.OBJ.world-instances already states world-scoped state with no current-world global, stanced by L32. |
| K-NET-1 | reject | OVERTURNED | Verifier concedes C-REP has no M2 configuration. replication is built at M1, its only consumers are optional edges, and nothing claimed before M4 exercises it, yet C-REP is frozen at M2 (frozen list of M2 in milestones.json). Only C-REP needs to move; C-PREDICT/C-NETSESSION/C-HOSTAUTH are exercised by fighting-2d-rollback-client and stay. |
| K-NET-6 | reject | UPHELD | docs/00 records input-only netcode as separate add-ons and relay as external:backend; scope expansion without new evidence. |
| K-NET-7 | reject | UPHELD | Composite query now has C-REWIND and NET.PRED.lagcomp owner; the view-stamp field and C-BUDGET line are detail-level. |
| K-NET-11 | reject | UPHELD | PHY.ARCH.rewind and GAM.SYS.hit-detection cover 2D rewind; niche case. |
| K-PERF-3 | partial | UPHELD | M1 declaration gate and M5 circularity fix are in; a scale-probe freeze precondition would contradict 'frozen exactly once' ladder mechanics and is not required by the M1 gate. |
| K-PERF-7 | partial | OVERTURNED | M4 exit text still says 'server density within budget' while PRF.NET.server-density is gated only at M6 (milestones.json M4 exit vs M6 gate; docs/09 line 360). The inconsistency the finding named remains. Skipping the M5 XR energy gate is fine. |
| K-PLATFORM-6 | partial | OVERTURNED | ARCH.REQ.platform-matrix still promises an 'OS x ISA x API x store' matrix generated from platform_variants, which has no store field. The new store capabilities exist but the matrix capability contradicts the data source; needs a wording fix, not a new field. |
| K-PLATFORM-8 | reject | UPHELD | Domain-owns, platform-contributes is the standard pattern. |
| K-PLATFORM-9 | reject | UPHELD | Speculative; null/software GPU device covers headless CI; cloud-render-host now exists. |
| K-PLATFORM-10 | reject | UPHELD | ML.RT.npu X is a recorded radar decision tied by check.py to maturity. |
| K-PROD-1 | reject | UPHELD | XC.EXT.lts (LTS & support policy) and BLD.REL.end-of-service exist and are M7 gates. |
| K-PROD-3 | reject | UPHELD | External partners as exit gates make agent milestones depend on outside parties; ARCH.ORG.external-dependencies covers lead times. |
| K-PROD-7 | partial | UPHELD | Creator-panel sampling folded into ARCH.ORG.human-capacity; per-milestone gates would add human dependencies without an owner-capacity model. |
| K-RENDER-6 | reject | OVERTURNED | Weak overturn (minor). multiview names PiP/captures and GAM.CAM.photo/PLAT.SVC.capture exist, but no capability says runtime isolated preview scenes (3D UI, character creator) with own lighting/budget are possible, and C-RSCENE speaks of one persistent instance scene. A wording change closes it. |
| K-SEC-4 | reject | OVERTURNED | Verifier itself says dev-trust, incident, server-validation, info-hiding, admin, transactions and receipts claims hold; verified none is in any gate in milestones.json. M4 exit names server-authority review as prose only. agent-redteam (M0) and XC.SEC.testing (M4) are already gated and stay out. |
| K-SEC-5 | reject | UPHELD | Organizational preference; security-engineering has a critic and a runtime child. |
| K-SEC-6 | reject | UPHELD | cloud-saves is harness-mode with the same size/depth limits; label change is cosmetic. |
| K-SEC-8 | reject | UPHELD | XC.SEC.tamper is a boundary co-owned with anti-cheat-integrity; C-SIGN covers signature verification; self-integrity/DRM is middleware integration. |
| K-SIM-5 | reject | UPHELD | docs/06 C.4; profile matching is OR-only so proposed profile restriction is inexpressible. |
| K-SIM-6 | reject | UPHELD | 22 caps is under the cap limit and comparable to other leads; overlap claim thin. |
| K-TEST-1 | partial | UPHELD | All process skills staffed at M0 (milestones[0].process_skills) and checked, so oracle authors and gate validators trivially exist by every freeze; per-milestone staffing would add nothing. |
| K-TEST-2 | reject | OVERTURNED | Verifier disproved one pair but missed others visible in milestones.json: M2 PRF.MEM.footprint->QA.FUNC.soak and QA.FUNC.soak->PRF.MEM.footprint (2-cycle); prechecks->release-criteria->compat-corpus->prechecks (3-cycle across M2/M7); holdout validated by golden-traces, which cannot show implementers cannot read it. Workstream-move and criterion-schema parts are not needed. |
| K-TEST-4 | reject | OVERTURNED | Mostly upheld (contracts re-pointed under K-ARCH-5), but CORE.CONC.correctness (model checking) is still owned by implementer concurrency-primitives while C-SYNC's oracle is robustness-fuzzing, the exact independence problem accepted in K-ARCH-4. Reword to the hooks-only form; do not move ownership. |
| K-TOOLS-3 | partial | UPHELD | Tool freeze at M3 with headless commandlets over C-CMD (frozen M1) is a reasoned sequencing choice; a minimal editor at M1 is not needed. |
| K-TOOLS-5 | reject | UPHELD | minimal-cli-tools cannot close because minimal-profile skills consume C-EDCMD via tool_consumes. |
| K-TOOLS-7 | partial | UPHELD | RND.TOOL.direct-lights added; adding 'rendering' to AUTHORING_WORKSTREAMS needs notes on rhi-* skills for no added coverage. |

## Required fixes

1. **K-SEC-4 (gates).** In data/milestones.json add gates (validators pass check.py: different owner, non-governance workstream). M2: `{XC.SEC.dev-trust -> QA.FUNC.editor}`. M4: `{XC.SEC.server-validation -> QA.FUNC.network}`, `{XC.SEC.info-hiding -> XC.SEC.testing}`, `{XC.SEC.incident -> QA.CERT.prechecks}`, `{NET.SRV.admin -> XC.SEC.testing}`, `{NET.SRV.transactions -> QA.FUNC.load}`, `{PLAT.COMM.receipts -> XC.SEC.testing}`. Mirror in docs/09 gate lists (M2, M4). Reword M4 exit "server-authority review and external pen test (human gate)" to name these gates (XC.SEC.testing is the pen-test validator). All ids verified to exist.

2. **K-TEST-2 (gate independence).** (a) M2 gate `QA.FUNC.soak`: change validator from `PRF.MEM.footprint` to `PRF.BENCH.stats` (breaks the 2-cycle). (b) M7 gate `QA.FUNC.compat-corpus`: change validator from `QA.CERT.prechecks` to `QA.REF.upkeep` (breaks prechecks -> release-criteria -> compat-corpus -> prechecks; QA.REF.upkeep is not itself a gated capability, owner reference-games, workstream quality). (c) M0 gate `QA.AGENT.holdout`: change validator from `QA.SIM.golden-traces` to `XC.SEC.agent-redteam` (a read-attempt against sealed:oracle; owner security-engineering differs from test-architect). Update docs/09 gate lists. Add to check.py a fail on gate cycles of length 2 and 3 (capability->validator graph across milestones) plus a check.py self-test mutation. Leave mutation-gate as is.

3. **K-NET-1 (C-REP freeze).** Move `C-REP` from M2 `contracts_frozen` to M4 `contracts_frozen` (keep it in M1 `contracts_draft`). Nothing requires C-REP before C-SHARD (M6), so ordering checks stay green. Update the M2 and M4 "Contracts frozen" lines in docs/09 (line ~336) and any doc statement of M2 net freezes. Leave C-PREDICT, C-NETSESSION, C-HOSTAUTH at M2.

4. **K-PERF-7 (M4 exit).** In milestones.json M4 `exit` and docs/09 line ~360 change "Perf: bandwidth per player and server density within budget." to "Perf: bandwidth per player within budget and latency gated; server density is gated at M6 (PRF.NET.server-density)". Do not add a duplicate gate.

5. **K-PLATFORM-6.** Reword capability `ARCH.REQ.platform-matrix` to "Platform matrix (OS x ISA x API; store axis from PLAT.SVC.pc-storefronts, platform-console entries and BLD.REL.store-variants) generated from skills.json platform_variants and implementer variants". Owner and contributors unchanged. Regenerate docs/01.

6. **K-ARCH-12.** Add `C-A11Y` to M1 `contracts_frozen` (accessibility skill and its consumers are M1; layer-P contracts are skipped by the consumer check, as C-ORCH shows). Update docs/09 M1 frozen line.

7. **K-TEST-4.** Reword `CORE.CONC.correctness` name to "Thread-safety annotations and model-checking hooks (litmus/linearizability reference scenes and threshold proposals only; suite authorship belongs to the contract's oracle_author)". Owner concurrency-primitives, contributor robustness-fuzzing unchanged.

8. **K-RENDER-6 (minor).** Reword `RND.ARCH.multiview` to "Multi-view rendering: split-screen, PiP, captures, stereo/multiview; isolated preview scenes with their own lighting and budget for 3D UI and render-to-texture cameras; UI-less, HDR and tiled capture honoring platform capture restrictions (PLAT.SVC.capture)"; add `ui-architect`, `gameplay-camera` to contributors (owner render-architect). If C-RSCENE's "one persistent instance scene" wording conflicts, add "plus isolated auxiliary scenes for previews".
