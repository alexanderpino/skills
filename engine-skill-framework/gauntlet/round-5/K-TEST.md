# K-TEST findings (Testing and Validation Critic, round 5)

### K-TEST-1 · major · wrong-owner
- Target: XC.DET.conformance, C-DET, determinism-replay, simulation-validation, milestones M0 gate
- Finding: The determinism conformance matrix (toolchain x ISA x platform x cores x schedule, incl. PGO/LTO) is owned by determinism-replay, the owner and implementer of C-DET. simulation-validation lists "Determinism matrix definition" as a non-responsibility, so the oracle for the most safety-critical property (rollback, lockstep, replay) is defined by the implementer. This contradicts L56 and QA.AGENT.oracle-independence. The M0 gate is validated by QA.ROBUST.concurrency, which is schedule stress and does not exercise cross-ISA or cross-compiler equality.
- Evidence: Bit-exact cross-platform lockstep (Factorio, GGPO/rollback fighters, Age of Empires deterministic sim) relies on desync detection by an independent state-hash oracle run on every toolchain and ISA. The framework's own rule says implementers must not control the suites that judge them.
- Proposed change: Move the matrix definition and the golden state-hash corpus to simulation-validation (add a QA.SIM.determinism-matrix capability). determinism-replay keeps policy (XC.DET.levels) and hooks, and becomes a contributor. Re-point the M0 XC.DET.conformance gate validator to QA.SIM.golden-traces plus a cross-ISA differential lane, with a known-red canary (a deliberate FMA or reduction-order change).

### K-TEST-2 · major · other
- Target: milestones.json gates (M0 QA.AGENT.mutation-gate, XC.DET.conformance, XC.SEC.key-custody; M1 QA.RENDER.golden, QA.SIM.stability-suite, QA.SIM.netsim, XC.SEC.threats, XC.SEC.hardening; M2 QA.FUNC.soak, PRF.LOAD.pacing-latency, XC.SEC.vuln-response; M3 QA.RENDER.reference-validation; M4 NET.SRV.transactions, XC.SEC.incident, PLAT.LIVE.operations; M5 RES.MGMT.validation; M6 NET.SRV.cross-server, XC.SEC.sandbox; M7 QA.FUNC.compat-corpus, QA.STRAT.release-criteria)
- Finding: Many gate validators do not exercise the property they gate. check.py only proves that the validator exists. Examples:
  - The mutation gate is validated by fuzzing.
  - Golden-image tests are validated by the HW/OS compat matrix. That matrix does not show that goldens detect a seeded regression, and a canary such as a known-bad shader is missing.
  - The physics stability suite is validated by soak.
  - QA.SIM.netsim and QA.RENDER.reference-validation are validated by oracle-change-control, a paperwork process. The reference path tracer needs an external-renderer comparison.
  - Idempotent transactions (NET.SRV.transactions) and cross-server hand-off are validated by load tests. They need QA.ROBUST.distributed-faults or QA.SIM.server-dst.
  - The streaming oracle RES.MGMT.validation is validated by load-time analysis instead of QA.SIM.streaming.
  - Key custody, incident response and hardening are validated by cert pre-checks, which are not drills or exercises.
  - Sandbox and vuln-response are validated by fuzzing.
  - PRF.LOAD.pacing-latency (hardware/marker measurement) is validated by statistics code.
  - The M7 chain is circular: QA.FUNC.compat-corpus is validated by QA.REF.upkeep (a migration process, not a validator). release-criteria is validated only at M7 but is used as a validator from M1.
- Evidence: A validator must be able to fail when the property is broken (mutation and canary principle; QA.AGENT.gate-canaries states this for gates, but the milestone data does not bind it).
- Proposed change: Add a required per-gate field `exercised_by` (a concrete lane, or canary id) and `known_red` (the seeded defect the validator must catch). Extend check.py so the validator capability appears in the gated capability's area, contract or family, or is explicitly on an allow-list. Re-point the listed gates: golden and stability go to QA.AGENT.gate-canaries, mutation-gate to a seeded-defect run, transactions and cross-server to QA.ROBUST.distributed-faults / QA.SIM.server-dst, streaming to QA.SIM.streaming, and so on. Give M7 release-criteria an independent validator (a rehearsal run on a reference game) and make compat-corpus validated by the corpus's replay lanes, not by its migration owner.

### K-TEST-3 · major · omission
- Target: milestones M1, M3, M5, M6, M7 exits vs gates
- Finding: Exit criteria promise things that no gate checks.
  - M1: save, localization, accessibility baseline and hot reload. Gates cover none of them, for example UI.A11Y.validation, QA.FUNC.compat-corpus (save migration) and XC.ITER.metrics.
  - M3: both GPU-driven and CPU-submission paths (RND.GEO.cpu-submission), and the lite-3d configurations.
  - M5: XR on PC, standalone and console (no XR gate: reprojection or motion-to-photon, OpenXR CTS), massim lockstep desync, "benchmarked" sandbox.
  - M6: persistence crash-consistency with 1k bots, distributed cook, the AAA reference slice.
  - M7: console certification pass (no QA.CERT.platform gate) and end-of-service rehearsal.
- Evidence: A milestone whose exit is not backed by gates is decided by the orchestrator's own judgment, which is what independent validation is meant to prevent. M5 has three gates and M6 four for the biggest scope.
- Proposed change: Add gate rows for each exit clause (for example UI.A11Y.validation validated by a screen-reader/caption golden run; RND.GEO.cpu-submission by QA.RENDER.matrix on the lite tier; XR gate on PLAT.XR.reprojection validated by a hardware motion-to-photon capture; M6 persistence consistency validated by QA.ROBUST.distributed-faults; M7 QA.CERT.platform validated by a console dry-run submission). Add a check that every named capability or QA lane in an exit sentence is gated.

### K-TEST-4 · major · missing-contract
- Target: contracts.json oracle_reference for 55 contracts (C-WORLD, C-MATIF, C-RSCENE, C-TEMPORAL, C-DRAW2D, C-SVC, C-UI, C-GAME, C-SCRIPT, C-COOK, C-EDCMD, C-GRAPH, C-BUILD, C-PKG, C-REPLAY, C-ENV, C-INSTANCES, C-GEOLOD, C-VT, C-LIGHT, C-GI, C-ATMOS, C-MOVE, C-GAMEDATA, C-AIAGENT, C-A11YRT, C-DEVUI, C-EDHOST, C-LIVE, C-XRVIEW, C-MLGPU, C-SCENETEX, C-LIGHTENV, C-TRANSLUCENT, C-PCG, C-VEHICLE, C-TARGETPLAT, C-NETSESSION, C-SERVER, C-SHARD, C-SRVDATA, C-EDVIEW, C-VCS, C-EDIT, C-AUTOMATION, C-INTEGRITY, C-CROWD, C-SEQ, C-AI, C-VFX, C-PTREF, C-HOSTAUTH, C-CAMERA, C-REWIND, C-CHARCTRL)
- Finding: 55 of about 125 code contracts carry the identical placeholder "reference scenes or analytic cases declared in the conformance suite; derived goldens are regression-only". That names no oracle. It is circular (the oracle author declares its own references) and gives an autonomous oracle author nothing to anchor to. Named external references exist for many of these.
- Evidence: Available references include:
  - the OpenXR CTS (C-XRVIEW);
  - furnace tests and analytic radiance, plus an external renderer such as Mitsuba or pbrt (C-GI, C-LIGHT, C-PTREF);
  - Jepsen or TLA+ models and idempotency-key oracles (C-SHARD, C-SRVDATA, C-SVC);
  - recorded provider traces or platform sandbox environments (C-SVC, C-LIVE, C-VCS: Perforce/Git behaviour);
  - reproducible-build comparison (C-BUILD, C-COOK);
  - the Khronos glTF sample models (C-IMPORT is already done, C-COOK is not);
  - supersampled ground-truth sequences (C-TEMPORAL);
  - test262-class script conformance or a reference VM (C-SCRIPT);
  - NavMesh/Recast (C-NAV is done, C-AI is not);
  - a published vehicle test set such as ISO 3888 double lane change (C-VEHICLE).
- Proposed change: Ban the placeholder string in check.py. Require each code contract's oracle_reference to name at least one non-derived source class (analytic, external implementation, standard suite or simplified model). Fill the 55 entries as above, with a `reference_status` (available, to-build) so the "to-build" ones get a capability owner.

### K-TEST-5 · major · wrong-owner
- Target: functional-automation-soak, robustness-fuzzing (oracle_author assignments), simulation-validation, render-validation consumes
- Finding: functional-automation-soak (expertise: bots, soak, game automation) is oracle author for 34 contracts spanning IO, VFS, cook, build, packaging, editor host, VCS, script VM, save, server persistence, service emulators, abilities and VFX. Its consumes list holds only C-GAME?, C-INPUT?, C-NET?, C-AUTOMATION, so it never consumes 31 of the 34. About 100 of about 130 contracts have oracle authors that neither consume nor implement them (check.py does not test it). robustness-fuzzing authors 19 contracts including semantic ones (C-ML, C-MLGPU, C-PRESENT, C-FLOW, C-FRAME, C-RELOAD, C-REFL, C-INSTR, C-CRASH): a fuzz corpus finds crashes, not semantic violations, and ML numeric parity or pacing metrics are not fuzzing expertise.
- Evidence: An SKILL.md agent for this role cannot hold 34 unrelated suites in context, and a bot/soak specialist has no build-system, distributed-persistence or editor-command literature. The framework's own rule is to split units that need different literatures.
- Proposed change: Split the role. Add a tool/pipeline conformance skill (C-ASSET, C-COOK, C-BUILD, C-PKG, C-VFS, C-EDCMD, C-EDHOST, C-GRAPH, C-EDVIEW, C-EDPREVIEW, C-VCS, C-CMD, C-IMPORT, C-EDIT) and a server/persistence/service conformance skill (C-SERVER, C-SRVDATA, C-SVC, C-LIVE, C-SAVE). Move C-ML, C-MLGPU to foundation-conformance or render-validation, and C-PRESENT/C-FLOW/C-FRAME to perf-benchmarking or simulation-validation. Add a `validates` (consume) edge, and a check.py rule that every oracle author consumes or lists the contract.

### K-TEST-6 · major · obsolete-assumption
- Target: QA.STRAT.flaky, L69, QA.AGENT.test-integrity, QA.STRAT.selection-policy
- Finding: Legacy pattern L69 ("retry until green", "retries or quarantines that hide nondeterminism") names QA.STRAT.flaky as its stance. But QA.STRAT.flaky itself defines automatic quarantine after repeated failures and "rerun-based clearing", with quarantined tests excluded from gate results, which is the legacy stance. selection-policy says determinism, conformance and holdout lanes are never skipped, but not that they are never quarantined. test-integrity lists deleted or skipped cases but not quarantine. For an autonomous agent, quarantining is the cheapest way to turn a gate green. For race and desync bugs an intermittent failure is the signal.
- Evidence: Google's flaky-test studies and Microsoft's test-flakiness work show flakes are often real races; rerun-until-pass masks them. L69's own default_stance says "classification and root-cause policy".
- Proposed change: Reword QA.STRAT.flaky to root-cause policy: reruns never clear a failure in determinism, concurrency, conformance, holdout, fuzz-regression or netsim lanes. Quarantine needs an owner, an expiry, a global budget counted by QA.AGENT.test-integrity, a recorded seed, and appears in the C-TEST evidence bundle (already listed) as a blocking item at release-criteria.

### K-TEST-7 · major · omission
- Target: QA.STRAT.contract-fakes, contracts with test_double (C-SVC, C-LIVE, C-VCS, C-INTEGRITY, C-SIGN, C-XRVIEW, C-VIDEO, C-DEVICE, C-NETLINK, C-SHARD, C-SRVDATA, C-RHI, C-PAL)
- Finding: A double is verified only by passing "the contract's conformance suite". That suite has no real-provider reference (for C-SVC, C-LIVE, C-VCS, C-INTEGRITY, C-XRVIEW the oracle_reference is the placeholder), so the double is checked against the same contract text it was built from. There is no drift lane running the same suite against the real provider (platform sandbox, Perforce server, OpenXR runtimes, real KMS).
- Evidence: Consumer-driven contract testing (Pact provider verification) and Google's "fakes must be verified against the real service" practice exist because fakes drift. Steam, PSN, EOS, OpenXR runtimes and Perforce all change behavior independently of the engine.
- Proposed change: Add to boundary contracts a `real_backend_lane` (sandbox or scheduled run and drift ticket) and to QA.STRAT.contract-fakes a periodic real-vs-double differential. Extend check.py: every test_double contract names its real backend and cadence.

### K-TEST-8 · major · omission
- Target: QA.RENDER.golden, QA.RENDER.final-frame, C-TEMPORAL, RND.RECON.upscalers, RND.RECON.denoise, RND.RECON.framegen
- Finding: Image validation is single-frame (FLIP-class golden, present capture). There is no sequence-based validation of temporal reconstruction: TAA, upscalers, denoisers, frame generation, motion vectors and disocclusion (ghosting, flicker, shimmer, motion-vector error). A frame-1 golden passes while ghosting persists, and C-TEMPORAL has the placeholder oracle reference.
- Evidence: Temporal artifacts are the main failure mode of DLSS/FSR/XeSS and ray-tracing denoisers, and are assessed with video metrics (FovVideoVDP, temporal FLIP/tLPIPS) against supersampled ground-truth sequences and reprojection-error tests.
- Proposed change: Add QA.RENDER.temporal (render-validation): scripted camera paths, supersampled ground-truth sequences, temporal metrics and motion-vector reprojection error. Make it the oracle_reference of C-TEMPORAL and gate it at M3.

### K-TEST-9 · major · overlap
- Target: NET.ARCH.validation, UI.A11Y.validation, RND.PT.reference, CNT.COOK.determinism-check, RND.SHADER.precision, RND.RHI.*-validation
- Finding: Other validation capabilities are marked "hooks only, suite authorship belongs to the oracle author", but these are owned by the implementing skill and define both scenarios and thresholds: NET.ARCH.validation (network-architect: "acceptance thresholds", only co-signed), UI.A11Y.validation (accessibility owns both features and their validation), RND.PT.reference ("ground-truth oracle" owned by path-tracing), cook determinism verification, FP32-reference validation of shader precision, and per-backend "validation layers and conformance runs" by each RHI backend skill. This is L56 (implementer-owned validation).
- Evidence: The framework's own pattern: "implementers must not control the oracles that judge them". Thresholds set by the party being judged is the loosest-tolerance failure mode.
- Proposed change: Apply the hooks-only wording. Move thresholds to the matching validator (simulation-validation, ui-text-conformance, render-validation, tool conformance skill). Backend skills run the suite and own the hooks only.

### K-TEST-10 · minor · missing-contract
- Target: contracts_frozen in milestones.json, C-TEST, QA.AGENT.oracle-independence, crosscutting.json independence
- Finding: check.py proves freeze order but nothing requires that the conformance suite, its sealed holdout and a known-red canary exist before a contract freezes. The independence matrix names (test-architect, owning-skill) for "oracle author vs implementer", but test-architect is the oracle author of no contract; the real pairs (render-validation, simulation-validation, functional-automation-soak, robustness-fuzzing, foundation-conformance, ui-text-conformance vs each owner and implementer) are not listed, and the pair gate validator vs gated capability owner is missing.
- Evidence: L56 requires tests before features. The check that implementers and oracle authors sit in different workstreams currently passes only by accident of how workstreams were assigned.
- Proposed change: Add `freeze_requires` (suite v1, holdout sealed, canary red, reference implementation passes) to milestone contract freezes and to check.py. Replace the matrix row with the real oracle author pairs, generated from contracts.json, and add the gate validator pair.

### K-TEST-11 · minor · maturity-error
- Target: QA.AGENT.holdout-hygiene, QA.AGENT.* (M), QA.STRAT.flaky
- Finding: QA.AGENT.holdout-hygiene is labelled E while its parents QA.AGENT.holdout, oracle-independence and mutation-gate are M. An anti-probing protocol with query budgets and retirement for LLM implementers has no established production practice.
- Evidence: Holdout hygiene against agent overfitting is new (benchmark contamination literature); no shipped engine has it.
- Proposed change: Relabel M and add a radar entry with a fallback (human-audited holdouts).

### K-TEST-12 · minor · omission
- Target: ML.RT.validation, C-ML, GAM.AI.llm-dialogue, ANM.SYN (motion-synthesis), RND.RECON.ml-denoise
- Finding: Validation of learned components covers runtime conformance (parity vs a reference framework, tolerance tables) but not model quality or behavior regression. There is no evaluation-suite owner for neural animation, learned denoisers, LLM barks or learned physics surrogates: statistical acceptance, held-out evaluation sets, drift and safety evals.
- Evidence: Model behavior can regress with identical numerics (quantization, retraining), and these features are M/X on the radar.
- Proposed change: Add QA.SIM.learned-eval (simulation-validation, M) with per-feature eval sets and statistical thresholds, gated on any M/X ML feature entering a shipping profile.

### K-TEST-13 · minor · overlap
- Target: QA.FUNC.compat, QA.RENDER.matrix, BLD.CI.device-lanes, PLAT.PAL.device-db
- Finding: Three owners run hardware matrices (QA.FUNC.compat, QA.RENDER.matrix, BLD.CI.device-lanes for infrastructure) with no rule for which device set a matrix covers. Nothing derives the matrix from PLAT.PAL.device-db tiers and PRF.METH.field telemetry (device share and driver deny-list changes).
- Evidence: Real-world GPU/driver matrices are chosen by share and defect history, else they grow without bound or miss the devices that fail.
- Proposed change: One matrix definition (owner test-architect or functional-automation-soak) generated from the device DB by tier and share; render, functional and perf lanes consume it.
