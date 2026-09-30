# K-PROD · Production Critic · Round 5

### K-PROD-1 · blocker · omission
- Target: QA.CERT.licenses, QA.CERT.legal-surfaces, QA.CERT.ratings, QA.CERT.export-crypto, QA.CERT.patents-codecs, QA.CERT.authorship-ip, QA.CERT.ml-provenance, CNT.ID.rights, ARCH.PROD.licensing-model, ARCH.PROD.upstreaming, ARCH.ORG.human-gates, milestones.json
- Finding: none of the legal/IP capabilities is gated at any milestone including M7, and no human-gate names a legal role. ARCH.ORG.human-gates lists "contracts, spend, NDA material" (ambiguous with C-* contracts) and live-ops actions; nothing in data/ or docs/ mentions counsel or a data-protection officer. An agent organization cannot lawfully author or sign an EULA, a licensing model, a DPA (ARCH.PROD.vendor-telemetry), an age-rating submission, an export classification, or a patent/codec clearance.
- Evidence: a 1.0 with no gated SBOM/licence audit, rights manifest, ratings or export classification cannot pass store submission (Apple/Google/Steam/console TRC require rating, export-crypto and privacy declarations). Middleware licence audits are a standard AAA release-blocker.
- Proposed change: add a human-gate class "legal instrument and clearance" (named human roles: counsel, DPO) to ARCH.ORG.human-gates; gate QA.CERT.licenses and CNT.ID.rights at M1/M2 (first shipping build), QA.CERT.legal-surfaces, ratings, export-crypto at M2, ARCH.PROD.licensing-model and upstreaming at M7, each with a human sign-off validator recorded in the gate.

### K-PROD-2 · major · missing-contract
- Target: milestones M0–M6, M7 exit, XC.EXT.lts, XC.EXT.upgrade, XC.EXT.versioning, C-RELEASE
- Finding: M7 exit demands a "customer-corpus upgrade from the previous release", but the ladder defines no engine release before M7. M2 already "ships everywhere" and M4 patches a live game, yet no milestone cuts a numbered pre-1.0 engine release, API-stability tier (alpha/beta/stable), early-access licensee channel, or upgrade-tool gate. XC.EXT.upgrade (codemods, data upgraders) and API-break policy are never exercised between M2 and M7.
- Evidence: shipping engines (Unreal, Unity, Godot) cut preview/beta releases with migration guides for years before LTS; without them the first upgrade test is at 1.0 when breakage has accumulated over five milestones.
- Proposed change: give milestones an engine_release field (M2 = 0.x preview, M4 = 0.y beta, M6 = RC) and gate XC.EXT.upgrade with the corpus upgrade from M2 on; M7 exit then names a real prior release.

### K-PROD-3 · major · missing-contract
- Target: milestones M0 and M1 gate lists, ARCH.ORG.ownership-ledger, ARCH.ORG.agent-continuity, ARCH.ORG.change-requests, ARCH.ORG.critic-calibration, ARCH.ORG.adjudication, ARCH.ORG.human-audit, ARCH.ORG.model-requalification, ARCH.ORG.human-capacity, ARCH.ORG.escalation
- Finding: not one ARCH.ORG.* or ARCH.PROD.* capability except customer-corpus is gated or exercised at any milestone. Coordination is the mission's central risk, yet no exit proves that the ledger locks, lease/fencing recovery after a crashed agent, contract change-request routing, escalation SLA, critic recalibration or human-gate parking actually work under load. M0's gates are all test/security capabilities.
- Evidence: multi-agent programs fail at integration and stale-state points; a control plane never seen to fail is the same "guard never seen to fail" the framework rejects elsewhere (A13).
- Proposed change: add M0 gates for ARCH.ORG.ownership-ledger and ARCH.ORG.agent-continuity (forced agent kill, reclaim, hand-off), M1 gates for ARCH.ORG.change-requests (a real cross-workstream freeze change), ARCH.ORG.critic-calibration and ARCH.ORG.human-capacity (gate-wait metric), M4 for ARCH.ORG.escalation; validators owned by architecture-governance.

### K-PROD-4 · major · dependency-error
- Target: gates XC.SEC.key-custody, XC.SEC.hardening (M0/M1 validated by QA.CERT.prechecks, gated only at M2); XC.SEC.supply-chain (validated by BLD.SYS.dev-surface-exclusion, gated at M1); QA.STRAT.release-criteria (validator at M1, M2, M4; gated at M7); QA.FUNC.compat-corpus (validator at M4, gated M7); QA.FUNC.soak (validator M1, gated M2)
- Finding: validators are used before they are themselves proven. 21 validator capabilities (e.g. QA.AGENT.oracle-change-control, XC.SEC.testing, QA.REF.upkeep, PRF.BENCH.stats, QA.FUNC.compat) are never gated at all, so nothing shows they can fail. M7 release-criteria is validated by the compat-corpus, which is validated by QA.REF.upkeep, which is never gated.
- Evidence: a validator with no gate of its own is an unproven oracle; QA.AGENT.gate-canaries is gated only over M0 capabilities.
- Proposed change: order rule (checked in check.py): a validator's own gate milestone must be <= the gate it validates or the validator must be in M0 canary scope; add gates (validated by gate-canaries) for QA.AGENT.oracle-change-control, XC.SEC.testing, QA.REF.upkeep, PRF.BENCH.stats; move QA.STRAT.release-criteria and QA.CERT.prechecks gates to first use.

### K-PROD-5 · major · other
- Target: gates XC.SEC.key-custody, XC.SEC.incident, XC.SEC.hardening (validator QA.CERT.prechecks); XC.SEC.vuln-response, XC.SEC.sandbox, QA.AGENT.mutation-gate (validator QA.ROBUST.fuzzing/QA.ROBUST.fuzzing); PLAT.LIVE.operations (QA.FUNC.soak); BLD.REL.rollback (QA.STRAT.release-criteria); BLD.REL.staged-rollout (QA.FUNC.compat-corpus); QA.SIM.netsim (QA.AGENT.oracle-change-control)
- Finding: many validators do not exercise the gated capability. Store-cert prechecks do not test HSM key custody or incident response; fuzzing does not test vulnerability-disclosure SLAs, sandbox-escape/GPU-DoS (stated in M6 exit) or the mutation gate; a soak run does not exercise runbooks; a ship-criteria definition does not execute rollback; a compat corpus does not halt a rollout; oracle change control is not a network-simulation exercise. Exit text ("patch + DLC + staged rollout + rollback executed", "incident", "sandbox-escape and GPU-DoS tests") is therefore ungated by any validator that runs it.
- Evidence: game-day/chaos drills and red-team exercises are separate practices from soak and fuzz; certification prechecks are platform-holder rule scans.
- Proposed change: re-point validators: key-custody/incident to XC.SEC.agent-redteam or XC.SEC.testing; sandbox to XC.SEC.testing plus the mod-escape corpus; rollback/staged-rollout to a new drill capability (release-rehearsal, owner functional-automation-soak) run on the online reference game; mutation-gate to a canary-mutant validator.

### K-PROD-6 · major · omission
- Target: BLD.REL.patching, BLD.REL.dlc, BLD.REL.packaging, BLD.REL.submission, BLD.REL.store-variants, BLD.REL.cdn, BLD.REL.on-demand, BLD.REL.server-artifacts, BLD.REL.engine-distribution, BLD.REL.preload-embargo, PLAT.LIVE.support-tools, XC.EXT.upgrade, ARCH.PROD.release-notes
- Finding: release mechanics are gated only for rollout and rollback and end-of-service. M2 exit says indie-2d "ships on PC, console, mobile and web", and M4 exit says "patch + DLC ... executed", but patching, DLC, packaging, store variants and submission artifacts have no gate. M7 exit lists release notes and a backport stream with no capability gated (only XC.EXT.lts).
- Evidence: patch-size regressions and layout instability (BLD.REL.patching budgets) and store-package rejection are the commonest launch-week failures.
- Proposed change: gate BLD.REL.packaging/submission/store-variants at M2 and BLD.REL.patching, BLD.REL.dlc, BLD.REL.server-artifacts at M4 (validator QA.FUNC.compat-corpus with a patch-chain corpus); gate ARCH.PROD.release-notes and XC.EXT.upgrade at M7.

### K-PROD-7 · major · scale-down
- Target: ARCH.ORG.staffing, data/organizations.json, milestones.json (M0, M2, M4)
- Finding: staffing tiers are static and unrelated to the ladder. The "small" tier puts 12 build workstreams (about 1,300 of 1,537 capabilities) in one agent; nothing says which milestones or configurations a 3-agent organization can reach, how many skills an agent may load concurrently, or how M2 (nine configurations, four platforms, console with NDA/devkit lead time, tools, rollback) and M4 (13 configurations) are sequenced by a small team. M0 activates 43 build skills plus 26 process skills for a skeleton whose exit draws a sprite and text (reconstruction-upscaling, post-color-hdr and texture-streaming-vt are staffed at M0), so governance staffing exceeds delivery staffing.
- Evidence: real small teams ship one platform and one genre at a time; agent context and lock contention limit concurrent skills per agent.
- Proposed change: add per-tier fields (max concurrent skills, reachable configurations/milestones, descope order) to organizations.json; split M2 and M4 or make sub-milestones; defer M0 skills the exit does not need; check.py to prove each tier has a reachable ladder prefix.

### K-PROD-8 · major · maturity-error
- Target: milestones M0 contracts_frozen C-BUDGET, C-SCALE; M0 exit ("C-BUDGET v0 for indie-2d tiers")
- Finding: C-BUDGET is frozen at M0 while the exit text says only v0 indie-2d tier budgets exist. Std3d, lite3d, network, server-density and asymptotic budgets appear at M1 to M6, so every later tier forces a change request against a frozen contract.
- Evidence: freeze means compatible-only change; per-tier budgets are added over five milestones.
- Proposed change: freeze C-BUDGET at M0 as a schema only, with per-tier budget tables as versioned data outside the contract, or move the freeze to M3 after std3d/lite3d budgets; align exit text.

### K-PROD-9 · major · omission
- Target: developer-experience-docs, XC.DX.samples, XC.DX.templates, XC.DX.onboarding, XC.DX.creator-docs, XC.DX.doc-tests, ARCH.ORG.human-capacity, milestones gates
- Finding: content creators and first-time game teams are represented as capabilities but never gated. No milestone requires a working template, onboarding path, API reference, creator manual or creator-panel result (time-to-first-asset, task completion) before a config is claimed; XC.ITER.metrics at M3 measures latency, not creator success. developer-experience-docs provides no contract, so its outputs have no consumers or freeze.
- Evidence: engine adoption depends on samples and docs shipped with each release; Unity/Unreal/Godot ship templates and docs per release.
- Proposed change: gate XC.DX.templates/samples/doc-tests at M1 and XC.DX.creator-docs plus creator-panel sampling at M2 (tools) and M3; add a C-DOCS contract (sample and template versioning consumed by api-lifecycle-migration).

### K-PROD-10 · minor · omission
- Target: ARCH.PROD.*, XC.EXT.plugins, engine-product-management
- Finding: engine-as-product covers roadmap, intake, notes, corpus, licensing, feedback and upstreaming, but no ecosystem territory: plugin/asset marketplace or certified-listing policy, middleware-partner programme, licensee support tiers/escalation for production emergencies, source-escrow terms.
- Evidence: Unreal Marketplace/Fab, Unity Asset Store and certified middleware partners are core to adoption.
- Proposed change: add ARCH.PROD.ecosystem and ARCH.PROD.support-tiers owned by engine-product-management, contributors plugin-system, security-engineering (listing signing via XC.EXT.plugin-trust).
