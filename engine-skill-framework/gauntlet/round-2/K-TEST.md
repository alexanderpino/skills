# K-TEST · Testing & Validation Critic · Round 2 findings

### K-TEST-1 · blocker · missing-contract
- Target: C-ORCH, C-TEST, QA.AGENT.oracle-independence, QA.STRAT.contracts, all 86 `conformance: true` contracts
- Finding: The framework never says who writes which tests, and in practice the implementer ends up owning its own oracle. C-ORCH assigns write sets as `src/<skill-id>/`, `tools/<skill-id>/`, with "tests owned by the test-owning skill", but no data field or rule names that skill. C-TEST then says "conformance suites owned by contract owners with consumer-driven additions". Of the 86 conformance contracts, 84 have no implementer other than the owner; only C-RHI and C-ENV have separate implementers. For almost every contract, the agent that implements it also writes the suite that judges it. QA.AGENT.oracle-independence accepts tests "authored **or approved** by an agent other than the implementer", but no approving role is named, so any agent's approval satisfies it. This contradicts the stated default in 00 §6 ("implementers grading their own tests" is the legacy pattern) and §8 ("Implementers must not control the oracles that judge them"). The failure is a coordination one: two agents (implementer and test owner) have no defined write boundary over test files, and check.py cannot detect this.
- Evidence: Consumer-driven contract testing (Pact; Fowler's "ConsumerDrivenContracts") works because consumers write the expectations and the provider only runs them. Sea of Thieves (GDC 2019, already cited in 07) separates feature tests from the feature owner's merge authority. With LLM agents, a model that can edit the tests judging it will make them pass by weakening them. This is documented in agentic coding benchmarks: SWE-bench keeps its FAIL_TO_PASS tests hidden, and reward-hacking reports show models editing tests.
- Proposed change: (1) contracts.json: add `oracle_author` to each conformance contract. It is a consumer skill or a quality-workstream skill, and never the owner when the owner is the only implementer. (2) C-ORCH: replace "tests owned by the test-owning skill" with two write sets. `tests/unit/<skill-id>/` is implementer-owned. `tests/acceptance/<contract-id>/` is oracle-author-owned, and the implementer gets read-only access class `oracle-ro` in the ownership ledger. (3) Change QA.AGENT.oracle-independence to "authored by the declared oracle author; implementer may propose additions via change request only". (4) check.py: fail when `oracle_author == owner` for a single-implementer contract, and fail when a skill's acceptance write set is writable by its implementer.

### K-TEST-2 · major · overlap
- Target: QA.SIM.stability-suite / PHY.ARCH.validation; QA.SIM.animation / ANM.ARCH.validation; QA.SIM.audio / AUD.ARCH.validation; QA.SIM.netsim / NET.ARCH.validation / QA.FUNC.network / NET.TRANS.simulation; simulation-validation
- Finding: The same suites have two owners under nearly identical names. For example, "Audio oracle suite: bit-exact offline render, loudness, glitch & latency" is owned by audio-architect, while "Audio offline-render, loudness & glitch suites" is owned by simulation-validation. Animation, physics stability and net simulation follow the same pattern. The "define vs run" split exists only in simulation-validation's prose. "Running" a suite is CI (ci-cd-automation), so simulation-validation owns no distinct artifact, and both agents will write the same test sources. Network testing is split four ways with no stated boundary: NET.ARCH.validation, QA.SIM.netsim, QA.FUNC.network ("Network test harnesses") and NET.TRANS.simulation (link simulation). simulation-validation also consumes no contracts (C-PHYS, C-ANIM, C-AUDIO, C-NET, C-REPLAY), although it runs suites against all of them. Its non-responsibility points to `owning-skill`, which is not a real owner.
- Evidence: Compare render-validation. It owns distinct artifacts (image metrics, per-GPU tolerance tables, the comparison harness), and material-system's furnace tests are named as the input it runs. The QA.SIM caps have no equivalent distinct artifact.
- Proposed change: Rename the QA.SIM caps to the artifacts simulation-validation actually uniquely owns: the metric library (pose error, loudness per ITU-R BS.1770, penetration/energy drift), the tolerance/baseline store, the cross-platform comparison harness and the result dashboards. Keep scene and scenario definitions in the *.ARCH.validation caps. Make the boundaries explicit: QA.FUNC.network = multi-process bot harness; QA.SIM.netsim = deterministic single-process net simulation; NET.TRANS.simulation = the link-conditioner seam. Add consumes `C-PHYS, C-ANIM, C-AUDIO, C-NET?, C-REPLAY`. Replace `owning-skill` with explicit owners.

### K-TEST-3 · major · wrong-owner
- Target: PHY.ARCH.validation, ANM.ARCH.validation, AUD.ARCH.validation, NET.ARCH.validation, RND.MAT.validation, RND.PT.reference, QA.AGENT.baseline-governance
- Finding: Each domain oracle is defined by the lead or skill whose own subtree it judges, and that lead also owns the milestone exit. material-system defines the furnace tests for its own code. The ground-truth renderer (RND.PT.reference) is a sibling feature in render-architect's subtree, joins at the same milestone (M2) as the features it validates, and nothing validates the oracle itself. Baseline governance covers goldens and tolerances, but not the oracle *definitions*, meaning scene sets, metrics and pass criteria. A lead under schedule pressure can therefore narrow a suite without tripping any gate.
- Evidence: Oracle validity is a known failure point. Path-tracer references are themselves validated against independent renderers and analytic cases: white-furnace tests, PBRT-v4/Mitsuba 3 cross-checks, and Heitz's multiple-scattering microfacet furnace tests. Physics oracles are cross-checked against analytic solutions and a second engine (differential testing). Metamorphic testing literature (Chen et al., ACM CSUR 2018) is the standard answer when no ground truth exists.
- Proposed change: (1) Add QA.AGENT.oracle-change-control, owned by test-architect: any change to a *.ARCH.validation scene set, metric or threshold needs co-signature from the matching quality skill (simulation-validation or render-validation) and is diffed by QA.AGENT.test-integrity. (2) Add QA.RENDER.reference-validation, owned by render-validation with contributor path-tracing: the reference tracer is validated against analytic furnace scenes and an external renderer on a fixed scene set before it may serve as a baseline. (3) Move the furnace pass/fail thresholds (not the scenes) from material-system to render-validation.

### K-TEST-4 · major · omission
- Target: ML.RT.*, GAM.AI.*, WLD.*/RES.MGMT (streaming), UI.FW.*, CNT.COOK.*, ED.ARCH (transactions), ml-inference-runtime, navigation-pathfinding, resource-streaming-architect, ui-architect, content-pipeline-architect, editor-architect
- Finding: Domain oracle capabilities exist only for physics, animation, audio, netcode and rendering. The following domains have no objective oracle:
  - **ML inference:** CPU/GPU/NPU numerical equivalence, quantization accuracy regression and model-version regression. The domain is maturity M with vendor-variable numerics, and ML.RT.determinism is only a "characteristics" description.
  - **Navigation/AI:** navmesh connectivity and coverage, path optimality versus exact A* on reference maps, avoidance with no interpenetration.
  - **World streaming correctness:** no required cell missing at a given traversal speed, no hole or pop beyond budget, the residency invariant under arbitration. PRF.LOAD covers speed, not correctness.
  - **UI:** layout and screenshot regression, focus-navigation graph completeness for controllers, safe-area compliance.
  - **Content pipeline:** incremental cook equals clean cook. CNT.COOK.determinism-check covers only cook-twice equality.
  - **Editor:** the transaction invariant that do→undo→redo is equivalent to do, including for multi-user merges.
  Under the §1 rule, "a critic can decide whether it is correct" is unmet for these skills.
- Evidence: UE's editor transaction tests and Unity's incremental-import consistency checks show that incremental-vs-clean divergence and undo corruption are the dominant tool bugs. Recast/Detour ship navmesh test suites. ONNX Runtime and TFLite use per-op backend conformance with tolerance tables as their standard practice.
- Proposed change: Add six capabilities, each owned by the domain skill and run by the matching quality skill: ML.RT.validation (backend and quantization conformance with tolerance tables), GAM.AI.validation (owner navigation-pathfinding), RES.MGMT.validation (streaming correctness oracle, contributor loading-streaming-performance), UI.FW.validation (layout and focus-graph oracles), CNT.COOK.incremental-equivalence (owner content-pipeline-architect), ED.ARCH.transaction-invariants (property-based undo/redo, owner editor-architect).

### K-TEST-5 · major · wrong-boundary
- Target: test-architect, functional-automation-soak, robustness-fuzzing, perf-benchmarking, render-validation, simulation-validation (all `kind: process`, `targets: []`); QA.STRAT.frameworks, QA.STRAT.contract-fakes, QA.ROBUST.faults, QA.FUNC.automation, QA.STRAT.integration
- Finding: Test infrastructure is shipped code, but every skill that owns it is a process skill with no targets. That code includes the unit/integration framework, the on-device test runner, bots, fuzz harnesses, fault-injection hooks, contract fakes and benchmark harnesses. All of it must compile for console, mobile, web and server and link into the `test` build configuration (BLD.SYS.configs). As a result:
  - The configuration-closure proof never shows that a configuration can actually be tested. Nothing proves that a test runner exists for `indie-2d-client` on web or console, or for `online-3d-server`, so QA.STRAT.integration ("per-configuration build/boot/test matrix") is asserted, not proven.
  - Fault-injection hooks for IO errors, OOM and device-lost must live inside the code of async-io-storage, memory-allocators and rhi-core. robustness-fuzzing is a process skill, and the stated rule is that process experts never own subsystem code (the §8 perf rule). So those hooks have no owner.
- Evidence: Production precedent treats test infrastructure as a runtime module with platform backends. UE has the Automation framework, Gauntlet and the Low-Level Tests module; Unity has the Test Framework player runner. Console on-device test runners go through the PAL and devkit deployment.
- Proposed change: Add a runtime-kind expert `test-runtime-harness` (parent test-architect; targets client, headless-client, server, tools; profiles all). It owns QA.STRAT.frameworks, the on-device runner, result reporting and the seam registry, and it provides C-TESTHOST (L1: test registration, runner, fixtures, fault-point registry). Owners implement fault points against C-TESTHOST, and robustness-fuzzing owns only the policies and campaigns. check.py: every configuration closes over test-runtime-harness for each of its platforms.

### K-TEST-6 · major · missing-contract
- Target: ED.ARCH.agent-api, editor-architect, crosscutting "agent operability", QA.FUNC.automation, QA.FUNC.agent-exploration, radar entry "Agent/automation control API"
- Finding: Remote automation of *runtime* builds (clients on devkits, dedicated servers, soak rigs) has no reachable owner. The only automation/introspection protocol, ED.ARCH.agent-api, is owned by editor-architect, which is `kind: tool` and targets only `tools`, so tool-side rules prevent its runtime half from shipping in client or server builds. No contract carries the protocol: the crosscutting obligation "expose debug state and controls through the agent/automation API" names no contract that runtime skills could consume. The whole capability is also labelled emerging (M) because of the MCP-class LLM front end. Remote automation of player and server builds is itself established practice (UE Gauntlet, Unity remote player tests, Sea of Thieves), and the framework's autonomous-agent validation depends on it.
- Evidence: Without a runtime automation channel, bots, soak runs, cert pre-checks and agent-driven repro cannot drive shipping-config binaries. This is the exact "cannot be debugged or tested" condition the brief rejects.
- Proposed change: Add contract C-AUTOMATION (L3, runtime; owner visual-debugging-tools or the new test-runtime-harness from K-TEST-5). It covers a structured command/query/observe protocol, discovery of exposed debug state and controls, authentication, and compilation out of shipping builds. Split ED.ARCH.agent-api into ED.ARCH.automation-protocol (E, runtime owner) and ED.ARCH.llm-agent-frontend (M, editor-architect, radar). Point the crosscutting obligation at C-AUTOMATION. Register the protocol as an untrusted input (see K-TEST-10).

### K-TEST-7 · major · missing-contract
- Target: crosscutting "testability seams", QA.STRAT.contract-fakes, PLAT.SVC.emulation, C-PAL, C-SVC, C-IO, C-RHI, C-MEM
- Finding: The seam obligation is prose and does not appear in data. No contract records whether it has a null device, fake, emulator or recording double, who owns that double, or whether the double is itself verified. QA.STRAT.contract-fakes gives one process agent (test-architect) the job of writing fakes for about 100 contracts, which is the wrong expertise and a bottleneck. Specific seams are also missing:
  - **PAL lifecycle and event injection** (suspend/resume, constrained mode, user sign-out, controller disconnect, memory pressure, thermal). Console cert pre-checks are built from exactly these.
  - **First-party service emulation for C-SVC** (identity, entitlements, privileges, achievements). PLAT.SVC.emulation belongs to online-services-liveops, a third-party/NDA-less skill, and only C-LIVE mentions emulation.
  - **Hook ownership for GPU device-lost/TDR, IO errors and allocation failure.**
- Evidence: Fakes that are not run against the real contract's test suite drift; "verified fakes" is the standard remedy (Google testing practice; Fowler, "ContractTest"). Console TRC/XR checklists are dominated by lifecycle and account-state cases that need injection, because they cannot be reproduced by hand in CI.
- Proposed change:
  - contracts.json: add `test_double: {kind, owner}`, defaulting to the contract owner, and require the double to pass the contract's conformance suite.
  - check.py: every L0–L4 contract that crosses a platform, device, service or IO boundary declares a test double.
  - Add PLAT.PAL.event-injection (platform-architect).
  - Move first-party service emulation into platform-services as PLAT.SVC.first-party-emulation, and add emulation to the C-SVC summary. Keep PLAT.SVC.emulation for C-LIVE only.
  - Reword QA.STRAT.contract-fakes to "policy and verification of contract doubles".

### K-TEST-8 · major · other
- Target: ARCH.ORG.critic-calibration, ARCH.ORG.critic-gates, critics.json stages S1–S4, gauntlet/PROTOCOL.md
- Finding: Calibration applies only to gauntlet rounds, which review the framework. The critics that judge agent-written code (S3), and releases and benchmarks (S4), have no measure of how often they miss defects. Their pass verdicts are therefore unfalsifiable, which violates the framework's own principle that "a guard never seen to fail is not a guard" (06 A13). The same principle is applied to check.py (`--selftest`) and to tests (mutation gate), but not to critics, CI gates or oracles.
- Evidence: This is mutation analysis applied to reviewers. Plant known bugs in a sample of changes, the same idea as the seeded-defect code-review studies in the Fagan-inspection literature, and treat any gate that has never gone red as untrusted.
- Proposed change: Extend ARCH.ORG.critic-calibration to S1–S4. The orchestrator plants canary defects in a sample of changes under review (for example about 5%): mutated code, a silently loosened tolerance, a missing fuzz registration. Recall is tracked per critic per stage. A critic below threshold stops counting as a gate. Add QA.AGENT.gate-canaries (test-architect): every CI gate and oracle keeps a known-red case that is exercised periodically.

### K-TEST-9 · major · other
- Target: gauntlet/PROTOCOL.md (calibration, disposition, convergence), ARCH.ORG.adjudication
- Finding: Several routes let the builder game the critic loop.
  - (a) Calibration measures recall only, so a critic that floods findings reaches 100% seed recall. Precision is never measured, and noise then drives the builder to reject in bulk.
  - (b) The builder can re-grade severity. Dispositions are accept/reject/merge/partial, and "accept as minor" is not adjudicated. Convergence rule A counts only accepted blocker/major findings.
  - (c) "A re-raised finding that was rejected earlier counts as non-material unless it brings new evidence." Blind critics cannot know a finding was raised before. The builder alone decides that it is a re-raise without new evidence, so this path skips the adjudicator.
  - (d) Seeds are planted by the orchestrator in the builder's organization, and all critics, adjudicators and seeders can be the same model family. Calibration then measures only the defects that model can imagine, and misses are correlated.
  - (e) No human samples critic or adjudicator verdicts. ARCH.ORG.human-gates covers spend, NDA and legal matters, but not validation quality.
- Evidence: LLM-as-judge studies report self-preference and correlated errors (Zheng et al., "Judging LLM-as-a-Judge", NeurIPS 2023; Panickssery et al., 2024 on self-recognition bias). Independent verification needs diversity, not just fresh context.
- Proposed change:
  - PROTOCOL: severity is fixed by the critic, and any downgrade goes to the adjudicator.
  - Any "non-material re-raise" ruling goes to the adjudicator.
  - Calibration reports precision as well as recall: the share of a critic's findings that survive disposition and adjudication must stay at or above a floor.
  - The seed author must be a context and model different from the builder.
  - Critics, adjudicators and seeders must use at least two model families or prompt lineages.
  - Add ARCH.ORG.human-audit (program-orchestration): a human samples adjudications and S3/S4 pass verdicts on a fixed rate. List it in ARCH.ORG.human-gates.

### K-TEST-10 · major · omission
- Target: robustness-fuzzing.fuzz_targets, `untrusted_inputs` on skills, check.py, packaging-release-patching, crash-diagnostics, observability-telemetry, shader-system, rhi-core, core-runtime-architect, visual-debugging-tools, editor-architect, collaboration-version-control, async-io-storage, hot-reload-iteration, platform-web
- Finding: check.py never cross-checks `untrusted_inputs` against `fuzz_targets` (grep finds no fuzz or untrusted logic in the scripts). The crosscutting claim "every untrusted input has a validating owner and a fuzz target" is therefore unproven. The following attacker-reachable parsers are also not registered at all:
  - patch/delta manifests and delta payloads (packaging-release-patching);
  - uploaded crash dumps and telemetry batches parsed by the crash and telemetry processors (crash-diagnostics, observability-telemetry);
  - on-disk shader and PSO caches (shader-system, rhi-core);
  - config files, command line and cvars, including remote/live layers (core-runtime-architect, C-CFG);
  - remote debug, dev-UI, live-link, hot-reload and automation endpoints on development servers (visual-debugging-tools, hot-reload-iteration, editor-architect);
  - the multi-user collaboration protocol (collaboration-version-control);
  - HTTP/CDN responses (async-io-storage RES.IO.remote);
  - the browser JS bridge (platform-web);
  - runtime image decoders for UGC and avatars.
- Evidence: Minidump processors, patchers and shader caches have a history of memory-safety CVEs (e.g. Breakpad/Crashpad processor fixes, Source-engine and Steam patch-path advisories). OSS-Fuzz practice is one harness per parser, owned next to the parser.
- Proposed change: check.py: every `untrusted_inputs` entry must be a key of `fuzz_targets`, and every fuzz target must have an owning skill that registers it. Give `fuzz_targets` owners (`{target: owner}`), with the harness in the owner's write set and campaign policy in robustness-fuzzing. Add the missing inputs above to the skills named.

### K-TEST-11 · major · omission
- Target: CORE.SER.evolution, GAM.SAVE.migration, XC.DET.compat, NET.ARCH.versioning, XC.EXT.mod-compat, XC.EXT.upgrade, RES.PKG, functional-automation-soak
- Finding: Each persisted or wire format has an owner for migration, but no one owns the *cross-version test oracle*. Nothing is assigned to keep the following:
  - a corpus of historical artifacts (saves from every shipped version, patch chains base→N, replays, cooked packages, projects, mods);
  - an N−1/N+1 client–server skew matrix inside the compatibility window, including rolling server deploys and crossplay patch skew;
  - the requirement that each release load that corpus.
  Migration code without a historical corpus is tested only against what the implementer thinks old data looked like.
- Evidence: Live games routinely break on save and patch-chain compatibility. Patch-chain testing (base plus every delta) is a standard release step on console and PC stores. Protocol skew testing is standard in live-service deploys.
- Proposed change: Add QA.FUNC.compat-corpus, owned by functional-automation-soak with contributors serialization-schema, persistence-save, determinism-replay, packaging-release-patching and modding-ugc. It covers the governed historical-artifact corpus, with additions required on every release, and the load/upgrade matrix. Add QA.FUNC.version-skew (contributor network-architect) for the skew matrix across the compatibility window. Make both inputs to QA.STRAT.release-criteria.

### K-TEST-12 · major · other
- Target: QA.AGENT.*, ARCH.ORG.ownership-ledger, C-TEST
- Finding: Acceptance suites are visible to the implementer, and nothing gates for overfitting. QA.AGENT.test-integrity catches "input special-casing" only after the fact. The framework has no sealed holdout cases, and no property-based or metamorphic cases generated with fresh seeds at gate time. An implementer that can read every acceptance case can pass them without being correct in general.
- Evidence: Agent benchmarks keep evaluation tests hidden from the agent (SWE-bench FAIL_TO_PASS). Property-based testing with gate-time seeds (QuickCheck/Hypothesis) and metamorphic relations resist overfitting to fixed inputs.
- Proposed change: Add QA.AGENT.holdout, owned by test-architect. Each conformance and oracle suite keeps a sealed holdout partition under a ledger access class the implementer cannot read, plus gate-time seeded property and metamorphic cases. A pass on the visible cases alongside a fail on the holdout is triaged as overfitting, not as a flaky test.

### K-TEST-13 · major · dependency-error
- Target: milestones.json (M0–M5 exits), QA.STRAT.release-criteria, C-TEST evidence bundle, determinism-replay
- Finding: Milestone exits are prose with no objective gates. M2 says "runs on PC and one console tier" but states no crash-free session rate, soak hours, perf-budget pass per tier, determinism lanes or fuzz hours. The S3/S4 evidence bundle is named in C-TEST and in K-TEST's checks but defined nowhere in data. M0's exit requires "determinism … smoke lanes", yet determinism-replay (the C-DET owner and XC.DET.conformance) only joins at M1. C-DET, C-SNAPSHOT and C-REPLAY are never frozen, even though replay-driven benchmarks (PRF.BENCH.replay), bug capture and golden traces depend on a stable replay format.
- Evidence: A walking skeleton only enforces discipline if its exit gates are mechanical. Otherwise the "tests before features" default in 00 §6 cannot be checked.
- Proposed change: milestones.json: add `gates` per milestone, as references to QA.STRAT.release-criteria entries (such as reference-game pass, soak ≥ N h, determinism-matrix lanes, fuzz campaign hours, cert pre-check pass, perf budgets per tier). Add an `evidence_bundle` schema to contracts.json under C-TEST, and check.py verifies that each gate names an existing capability. Either move determinism-replay (the C-DET rules module) into M0 or reword the M0 exit to "job-system serial/perturbation lane". Freeze C-DET at M1 and C-REPLAY at M2.

### K-TEST-14 · minor · overlap
- Target: QA.STRAT.content, QA.REF.content, PRF.BENCH.workloads, PRF.BENCH.scale-content; ARCH.ORG.triage vs PRF.BENCH.regression
- Finding: Test content has three owners with overlapping names: "Test content & test maps", "Representative production-scale content sets" and "Representative workload scenes". Bisection is claimed by both ARCH.ORG.triage and PRF.BENCH.regression.
- Evidence: With overlapping names, duplicate content sets diverge and perf and functional results are measured on different scenes.
- Proposed change: Make QA.REF.content the single source of representative content, consumed by test-architect and perf-benchmarking. Limit QA.STRAT.content to minimal unit/integration fixtures, and PRF.BENCH.workloads to "benchmark scenarios over QA.REF.content". Make ARCH.ORG.triage the routing policy, and a single bisection engine owned by ci-cd-automation that serves both.

### K-TEST-15 · minor · other
- Target: QA.STRAT.flaky, QA.AGENT.test-integrity
- Finding: Quarantining a flaky test is a silent weakening path, because a quarantined test stops gating. Flaky management names ci-cd-automation as a contributor, but quarantine is not routed through the test-integrity gate or given an expiry.
- Evidence: Google's flaky-test reports show quarantine backlogs growing without bound unless expiry and ownership are enforced.
- Proposed change: Reword QA.STRAT.flaky so that quarantine counts as a skip under QA.AGENT.test-integrity, with governed approval, a mandatory expiry and an owner, and the determinism seam used for reproduction.

### K-TEST-16 · minor · omission
- Target: legacy-patterns.json, 00 §6 last row
- Finding: 00 §6 lists "profiling and testing added late; implementers grading their own tests" as a replaced legacy pattern, but legacy-patterns.json has no such entry. K-LEGACY, which checks only that catalogue, therefore cannot flag these patterns. Other validation anti-patterns are also absent: wall-clock sleeps and real-time dependencies in tests, exact-pixel goldens across GPUs, and manual QA as the primary gate.
- Evidence: The catalogue is the mechanical input for K-LEGACY and ARCH.GOV.anti-legacy.
- Proposed change: Add L28 "Late or implementer-owned validation" (justification owner test-architect) and L29 "Nondeterministic test time/pixels" (owners frame-orchestration and render-validation), with detection hints.

### K-TEST-17 · minor · other
- Target: critics.json stage S3 coverage: api-lifecycle-migration, program-orchestration, research-evidence
- Finding: At S3, seven skills have no domain critic (computed from critics.json scopes). Most are pure process skills. api-lifecycle-migration, however, writes codemods and data upgraders (XC.EXT.upgrade) that rewrite customer code and data, and at S3 it gets only universal critics. check.py enforces domain-critic coverage only at G2.
- Evidence: Automated codemods are high-blast-radius code and need a domain reviewer at implementation time.
- Proposed change: Add api-lifecycle-migration to the K-TOOLS or K-ARCH scope at S3/S4. Extend check.py so that every skill that writes code (runtime/tool kinds, plus process skills that own code-producing capabilities) has a domain critic at S3.
