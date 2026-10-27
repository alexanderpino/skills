# K-TEST · Testing & Validation Critic · Round 3

### K-TEST-1 · blocker · dependency-error
- **Target:** milestones.json contracts_frozen; contracts.json oracle_author; QA.AGENT.oracle-independence. Examples: C-SIGN, C-TASK, C-MATH, C-PAL, C-MOD, C-CFG, C-ASSET, C-SER, C-RG, C-SHADER, C-SPATIAL, C-AI, C-AIAGENT, C-LIVE, C-WORLD, C-SCRIPT
- **Finding:** About 30 code contracts are frozen before the skill named as their oracle author is staffed. C-SIGN freezes at M0, but its oracle author (modding-ugc) arrives at M4. C-TASK and C-MATH freeze at M0, but animation-architect and animation-runtime arrive at M1. C-ASSET freezes at M1, but ai-assisted-authoring arrives at M6. C-SPATIAL freezes at M1, but crowd-simulation arrives at M4. C-AI, C-AIAGENT and C-WORLD freeze at M2, but their oracle authors arrive at M4. check.py only proves that a freeze comes after the owner and one consumer. It never checks the oracle author. The result is that each of these frozen contracts has either an acceptance suite written by the implementer (which breaks QA.AGENT.oracle-independence) or no independent suite at all when it freezes.
- **Evidence:** A freeze with no independent acceptance suite breaks the definition of done that C-TEST states for provider changes. With consumer-driven contracts (the Pact model), the consumer tests must exist before the provider is locked. Otherwise the freeze locks in behaviour that no independent party has checked.
- **Proposed change:** In milestones.json, a contract may freeze only after its oracle_author arrives. Add this to check.py. Then reassign oracle_author to a consumer that is present by the freeze, or to a quality skill (see K-TEST-4). Candidates: C-SIGN → security-engineering, C-TASK → frame-orchestration, C-MATH → spatial-transforms, C-ASSET → asset-cook-processors, C-SPATIAL → world-data-model. The other option is to move each freeze later.

### K-TEST-2 · blocker · wrong-boundary
- **Target:** crosscutting.json independence ["test-architect","owning-skill","oracle author vs implementer"]; ARCH.ORG.independence; ARCH.ORG.staffing; docs/00 §Workstreams
- **Finding:** docs/00 says that implementer vs oracle author is enforced by keeping each pair in different workstreams, because a workstream is the co-hosting unit. The matrix does not encode the real pairs. It names test-architect, which authors only 4 oracles, against a generic owning-skill. In 46 (contract, implementer) pairs, the oracle author and the implementer share a workstream. Examples: C-RHI with all six backends vs gpu-memory-resources (rendering), C-SYNC concurrency-primitives vs entity-object-model (foundation), C-MEM, C-ID, C-REP vs prediction-rollback (online), C-SAVE, C-NAV, C-BUILD. In five pairs the oracle author is the implementer's own lead: C-TYPES, C-PKG, C-AUTOMATION, C-TESTHOST, C-CROWD. When a small organization co-hosts one workstream in one agent, the same agent writes both the code and its oracle. The lead also arbitrates oracle-vs-implementer disputes inside its own subtree (ARCH.ORG.escalation).
- **Evidence:** This output is computed from contracts.json oracle_author, skills.json implements, and workstream/parent. check.py's rule that independence pairs never share a workstream passes only because the per-contract pairs are never listed.
- **Proposed change:** Generate one independence pair per code contract from (oracle_author, owner ∪ implementers). Require a different workstream and no ancestor relation, and have check.py enforce it. Reassign the violating oracle authors to skills in other workstreams. Disputes between an oracle author and an implementer escalate outside the shared lead.

### K-TEST-3 · major · overlap
- **Target:** C-TEST summary; QA.AGENT.oracle-independence; RND.RHI.conformance (rhi-core); ML.RT.validation (ml-inference-runtime); RND.MAT.validation (material-system); XC.DET.conformance (determinism-replay); simulation-validation non_responsibilities
- **Finding:** C-TEST says conformance suites are "owned by contract owners with consumer-driven additions". QA.AGENT.oracle-independence says acceptance suites are authored by the declared oracle_author and that implementers only propose changes. In practice the capability map follows C-TEST. The contract owner and implementer owns the conformance suite for C-RHI (rhi-core also implements the software device), ML inference, material furnace scenes and the determinism matrix. The simulation "domain scenario definitions" go to the domain architects whose subtrees they validate. So two contradictory rules exist, and agents will follow whichever one favours them.
- **Evidence:** The Khronos Vulkan CTS and the ONNX backend test suite are written independently of any one driver or backend. That independence is what makes them oracles.
- **Proposed change:** Rewrite C-TEST so that the oracle_author owns the conformance suite, the contract owner owns the normative spec text, and consumers add cases by change request. Rename RND.RHI.conformance, ML.RT.validation and RND.MAT.validation to "run/maintain implementation hooks for", and move suite authorship to the oracle author, or to render-validation or simulation-validation. For scene sets defined by domain skills, require authorship or co-authorship by the matching quality skill, not just its co-signature.

### K-TEST-4 · major · wrong-owner
- **Target:** oracle_author of C-PAL (accessibility), C-SIGN (modding-ugc), C-ML (anti-cheat-integrity), C-MLGPU (texture-streaming-vt), C-EDHOST (fluid-simulation), C-VT (render-2d-vector), C-SYNC (entity-object-model), C-RTAS (spatial-audio-acoustics)
- **Finding:** Oracle authors look like a rotation over consumers, not a choice based on who can build the oracle. A crypto and signed-artifact contract needs known-answer and edge-case vectors that a mod-system agent cannot produce. Lock-free and memory-model contracts need linearizability and model checking, which example tests from one consumer cannot cover. ML inference needs parity against a reference framework across precision classes. No contract names the external reference corpus its oracle must include.
- **Evidence:** NIST CAVP and Project Wycheproof (crypto), Relacy/CDSChecker/Lincheck/Porcupine (linearizability), the Khronos CTS and WebGPU CTS, the ONNX backend tests, and the Unicode/HarfBuzz test suites. Production conformance for these domains comes from specialist or standards corpora, not from a single consumer.
- **Proposed change:** Add `oracle_reference` (the list of external corpora) to every code contract, and have check.py require it for layers 0–2. Allow a quality skill to be oracle_author, co-authoring with a consumer. Suggested: C-SIGN → security-engineering; C-SYNC and C-TASK → robustness-fuzzing with a consumer; C-ML and C-MLGPU → render-validation or simulation-validation with a consumer; C-PAL → platform-desktop consumer plus test-runtime-harness.

### K-TEST-5 · major · other
- **Target:** QA.STRAT.flaky
- **Finding:** "Automatic retry until green; the owning skill quarantines persistent offenders". Retry-until-green turns intermittent failures (races, uninitialized memory, order dependence) into passes. These are the exact bug class that concurrency, determinism and schedule-perturbation lanes exist to catch. Letting the owning skill quarantine its own tests hands the implementer a way to switch off the oracle that judges it, which QA.AGENT.test-integrity is supposed to stop.
- **Evidence:** Google's flaky-test studies (Micco 2016; Luo et al., FSE 2014) put a large share of flakes down to async waits and concurrency, meaning real product bugs. Chromium and Google TAP record flake rate and deflake by bisection; they do not retry until green.
- **Proposed change:** Allow retries only to classify a failure. Every retry-pass is recorded as a flake event against the test and the code under test. Only test-architect or the contract's oracle_author can quarantine. Each quarantine has an expiry and a mandatory ticket, and it counts in the QA.AGENT.test-integrity diff. Tests from determinism, sanitizer and concurrency lanes can never be quarantined; their flakes are treated as product failures.

### K-TEST-6 · major · omission
- **Target:** QA.AGENT.holdout; skills.json access classes; ARCH.ORG.write-sets
- **Finding:** The framework says acceptance suites are "read-only for implementers" with "sealed holdouts", but nothing enforces it. The only access class is nda:per-platform-holder, and write-sets control writes, not reads. Any implementer agent can read the holdout partitions and oracle expectations and fit its code to them. At that point the holdout no longer works.
- **Evidence:** ML evaluation practice treats test-set contamination as fatal, and the risk is the same for coding agents. The SWE-bench contamination and "reward hacking" results show agents special-casing visible tests.
- **Proposed change:** Add an access class `sealed:oracle` (holdout partitions, gate-time seeds, oracle expected outputs), readable only by oracle authors and CI runners. Add capability BLD.CI.sealed-suites, owned by ci-cd-automation with contributor test-architect, covering sealed storage, execution only inside CI, and results as pass/fail plus a failure category with no expected values. In check.py, no implementer of a contract holds its sealed:oracle access.

### K-TEST-7 · major · omission
- **Target:** milestones.json gates (M0–M7); QA.AGENT.*; QA.STRAT.release-criteria; QA.FUNC.soak; QA.FUNC.compat-corpus; QA.ROBUST.sanitizers/concurrency; QA.RENDER.golden
- **Finding:** No milestone ever gates on the agent-output integrity machinery: test-integrity, holdout, mutation-gate, oracle-independence, baseline-governance and gate-canaries. Yet M0 and M1 freeze all the foundation contracts, and that is where vacuous tests would do the most damage. M7 (Engine 1.0) does not gate on QA.STRAT.release-criteria, QA.FUNC.soak or QA.FUNC.compat-corpus. Golden-image rendering is never a gate, not even when the 2D slice ships in M1–M2.
- **Evidence:** docs/06 A13 says "a guard never seen to fail is not a guard". Machinery that is not required at M0 will be retrofitted onto code that was already accepted.
- **Proposed change:** Add QA.AGENT.test-integrity, QA.AGENT.holdout, QA.AGENT.mutation-gate and QA.AGENT.gate-canaries to the M0 gates. Add QA.RENDER.golden and QA.SIM.stability-suite to M1. Add QA.FUNC.soak to M2. Add QA.STRAT.release-criteria and QA.FUNC.compat-corpus to M7.

### K-TEST-8 · major · omission
- **Target:** BLD.CI.gating, BLD.CI.pipelines, QA.STRAT.integration
- **Finding:** There is no test impact analysis or test selection, and no merge queue. Consider 34 configurations × platforms × GPU/driver matrix × holdout, sanitizer, determinism and fuzz lanes, with many agents merging at once. Pre-submit cannot run everything, and without a serializing merge queue that batches and bisects, two individually green changes break main together. That makes failure attribution (ARCH.ORG.triage) unreliable.
- **Evidence:** Google TAP (Memon et al., ICSE-SEIP 2017), Meta Predictive Test Selection (Machalica et al., 2019), Uber SubmitQueue (EuroSys 2019), GitHub merge queue.
- **Proposed change:** Add BLD.CI.merge-queue (serialized, batched merges with auto-bisect) and BLD.CI.test-selection (dependency-graph and history-based selection, with a periodic full run whose misses are measured), both owned by ci-cd-automation with contributor test-architect. Add QA.STRAT.selection-policy, owned by test-architect, defining which lanes can never be skipped (holdouts, conformance of touched contracts).

### K-TEST-9 · major · omission
- **Target:** QA.ROBUST.faults; C-SHARD; C-SRVDATA; C-LIVE; server-scaleout-persistence; online-services-liveops
- **Finding:** Fault injection covers only in-process faults (IO error, OOM, device lost). Nothing owns distributed-systems validation: process kill, network partition, clock skew, dependency outage and message reordering across shards, persistence and live services, or linearizability and idempotency checking of NET.SRV.transactions and entity migration. M6 requires "persistence crash-consistency", but no capability produces that evidence, and C-SHARD and C-SRVDATA have no test double or simulator.
- **Evidence:** FoundationDB deterministic simulation (Wilson, Strange Loop 2014), Jepsen/Knossos, Netflix Chaos Monkey/ChAP, Antithesis. Duplicate or lost items in MMO economies usually trace back to exactly these failure modes.
- **Proposed change:** Add QA.ROBUST.distributed-faults (partition, kill and clock-skew campaigns plus history-based consistency checking), owned by robustness-fuzzing with contributors server-scaleout-persistence, online-services-liveops and dedicated-server. Add QA.SIM.server-dst (deterministic multi-process server simulation), owned by simulation-validation. Declare test doubles for C-SHARD and C-SRVDATA (an in-process multi-node simulator with fault points).

### K-TEST-10 · major · other
- **Target:** C-TEST evidence_bundle "fuzz hours on registered inputs"; untrusted-inputs.json "harness inputs are fuzz targets owned next to the parser"; QA.ROBUST.fuzzing
- **Finding:** The parser owner writes the fuzz harness, and the evidence is measured in hours. An agent can satisfy that with a shallow harness: one that rejects early, never reaches the decoder, or leaves out a structure-aware grammar. Nothing measures what the harness actually reaches or sets a target for it.
- **Evidence:** OSS-Fuzz's Fuzz Introspector and coverage reports show that CPU-hours say nothing about harness quality. Many OSS-Fuzz projects ran for years on harnesses that never reached the vulnerable code.
- **Proposed change:** Replace "fuzz hours" with "per-target coverage and reachability of the registered parser functions, plateau evidence, and corpus size". robustness-fuzzing reviews and co-signs each harness (it becomes an oracle-change-controlled artifact). Add reachability thresholds to QA.ROBUST.fuzzing.

### K-TEST-11 · major · other
- **Target:** untrusted-inputs.json id "saves" (trust: trusted-local)
- **Finding:** Local save files are classed as trusted-local, while mods and assets are hostile-local. Players share, download and edit saves, and save files are a classic code-execution vector. Getting the trust class wrong lowers fuzzing priority and resource limits on one of the most-attacked parsers.
- **Evidence:** The Wii "Twilight Hack" (Zelda save), many 3DS and PS-era save-game exploits, and PC save-editor ecosystems. On consoles, save exploits are a standard jailbreak entry point, and certification treats them as hostile.
- **Proposed change:** Set saves' trust to hostile-local, with limits of size/depth/count plus version-floor checks. Add persistence-save as a contributor to QA.ROBUST.fuzzing campaigns.

### K-TEST-12 · major · obsolete-assumption
- **Target:** BLD.REL.staged-rollout ("Simultaneous global rollout to all players with post-release kill switches"); M4 gate
- **Finding:** The capability is called staged rollout, but its text describes the opposite: a simultaneous global release. That removes the canary cohort, which is the release validation step where crash-free rate, performance and desync telemetry gate the next stage before everyone is exposed. QA.STRAT.release-criteria loses its production-validation stage.
- **Evidence:** App-store phased releases (Apple 7-day, Google Play %-rollout), Google SRE canarying (SRE Workbook ch. 16), and live-game practice of regional or percentage waves with automated halt on crash-rate regression.
- **Proposed change:** Reword to "Staged percentage/cohort rollout with automated halt on release-criteria regression (crash-free rate, perf, desync), plus kill switches". Add test-architect as contributor, and reference QA.STRAT.release-criteria as the halt oracle.

### K-TEST-13 · major · scale-down
- **Target:** render-validation consumes; QA.RENDER.golden; C-SCENETEX
- **Finding:** Rendering validation consumes C-RG, C-RHI, C-RSCENE and C-SCENETEX. Those are per-view 3D scene textures, captured before UI, text, 2D composition, the post-display transform, HDR encoding and XR/present. The golden-image oracle therefore misses the whole visible output of the 2D, minimal and UI-centric configurations (C-DRAW2D, C-TEXT, C-UI), as well as display encoding (RND.POST.hdr-output, PQ/scRGB).
- **Evidence:** Text-rendering regressions (HarfBuzz/FreeType updates) and UI layout regressions are caught by final-frame and UI snapshot tests, not scene-texture comparison. HDR output errors such as PQ/metadata mistakes only show up at the swapchain.
- **Proposed change:** Add QA.RENDER.final-frame: final swapchain or offscreen present capture, including UI, text and HDR-encoded output, with pixel-exact mode for pixel-art/2D and a perceptual mode otherwise. It is owned by render-validation with contributors render-2d-vector, text-fonts and post-color-hdr. render-validation consumes C-DRAW2D?, C-TEXT?, C-PRESENT and C-COLOR.

### K-TEST-14 · major · omission
- **Target:** untrusted-inputs.json (agent-input/redteam entries); ARCH.ORG.triage; QA.FUNC.bug-capture; OBS.CRASH.pipeline
- **Finding:** Triage and fixing agents read CI logs, fuzz crash reproducers, player crash annotations, bug-capture text and telemetry strings. That content comes from hostile sources. crash-uploads and telemetry-batches are registered only as parser harness inputs, not as agent inputs. Nothing red-teams prompt injection that goes from player or fuzz content through triage into code changes or baseline changes.
- **Evidence:** Indirect prompt injection (Greshake et al., 2023) through issue trackers and CI logs has been shown against coding agents (for example, GitHub-issue injection against agentic PR bots in 2025).
- **Proposed change:** Add an agent-input "triage-artifacts" (CI logs, crash annotations, fuzz reproducers, bug reports, telemetry strings reaching agents), with validating_owner program-orchestration, mode redteam and limits "quarantined as data". Triage agents may not change baselines or quarantine tests (see K-TEST-5).

### K-TEST-15 · minor · omission
- **Target:** C-TEST evidence_bundle
- **Finding:** The S3/S4 evidence bundle leaves out the agent-integrity artifacts that critics need in order to decide: holdout results, the QA.AGENT.test-integrity diff, the baseline/golden/tolerance change log, test-double conformance results, flake events and quarantines, the ARCH.ORG.provenance attestation, and compat-corpus results.
- **Evidence:** K-TEST checks require "evidence bundle defined for S3/S4" and "tests cannot be weakened silently". Neither can be judged without these items.
- **Proposed change:** Append these items to C-TEST evidence_bundle.

### K-TEST-16 · minor · other
- **Target:** ARCH.ORG.critic-calibration ("below-threshold critics stop counting as gates")
- **Finding:** When a critic falls below threshold it stops counting as a gate, but nothing replaces it. The stage then passes with fewer reviewers. A critic that misses canaries in its own domain ends up removing the review from that domain.
- **Evidence:** Fail-open vs fail-closed gate design. The rule also conflicts with QA.AGENT.gate-canaries, which treats a gate that does not trip as broken.
- **Proposed change:** A below-threshold critic blocks the stages in its scope, failing closed, until a recalibrated or replacement critic passes its canaries. The interim sign-off is recorded under ARCH.ORG.human-gates.

### K-TEST-17 · minor · maturity-error
- **Target:** QA.AGENT.holdout (E), QA.AGENT.gate-canaries (E), QA.AGENT.oracle-change-control (E), ARCH.ORG.independence (E) vs QA.AGENT.oracle-independence/test-integrity (M)
- **Finding:** Sealed holdouts and oracle change control as merge gates for autonomous coding agents are no more established than oracle independence, which is labelled M. The radar entry "Validation of autonomous-agent development" lists only four of the seven QA.AGENT capabilities, so the three labelled E escape radar revisit.
- **Evidence:** docs/06 A13 says there is "little evidence on failure modes of agent-written systems code at this scale".
- **Proposed change:** Mark QA.AGENT.holdout and QA.AGENT.oracle-change-control as M and add them to the radar entry. gate-canaries (mutation-style red cases) can stay E.
