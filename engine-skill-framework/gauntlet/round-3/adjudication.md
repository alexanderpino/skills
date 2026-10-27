# G1 round 3 — adjudication of partial / reject / merge dispositions

Ground truth: current `data/*.json`, `docs/`, `scripts/check.py`. 24 findings adjudicated: 21 UPHELD, 3 OVERTURNED (K-ARCH-3, K-GAMEPLAY-7, K-TEST-6). All three overturns are small, mechanical remainders.

| Finding | Disposition | Verdict | Reason |
|---|---|---|---|
| K-ARCH-3 | partial | OVERTURNED | `ARCH.ORG.escalation` now routes same-workstream lead disputes to engine-architect, which is enough (no per-workstream arbiter or check.py rule needed). But `docs/00-design-principles.md` line 35 still says "Only cross-workstream disputes reach engine-architect", which contradicts the data. Fix the doc. |
| K-ARCH-4 | reject | UPHELD | The stated harm is a lead arbitrating a dispute it is a party to. The escalation capability now sends those to engine-architect. Splitting UI, cook-infrastructure and physics-runtime experts is a re-org, not a demonstrated defect. Lead capability counts are 21-26, under the check.py warning of 30. Judgement call, since both verifier lenses held the finding. |
| K-COMPLETE-6 | partial | UPHELD | `NET.SESS.content-set` and `NET.SESS.server-browser` already cover join-time negotiation and listing. `NET.SRV.community-hosting` covers redistribution and rulesets. The `server-pushed-content` input already registers hostile server-pushed content. A separate content-sync capability would duplicate content-set. |
| K-COMPLETE-12 | merge | UPHELD | `ED.UI.outliner` exists (editor-ui-framework, contributor world-data-model), which matches K-TOOLS-14. |
| K-FUTURE-1 | partial | UPHELD | The GPU tiers `rt` and `rt+tensor`, the `hwrt` add-on, `rt-required-3d-client`, `RND.GI.rt-required` and docs/00 §7 exist. Keeping C-RT, C-RTAS and C-MLGPU gated (optional) at the dependency level is a sound way to keep non-RT builds buildable. Required-RT is expressed by profile and tier. |
| K-FUTURE-15 | reject | UPHELD | Tool-side ML generation is already class M under `ED.AI.generative`, `ED.AI.provenance`, `ED.AI.evaluation` and `CNT.COOK.ml-assisted`. `WLD.PCG.ml` (X) is the runtime path. |
| K-GAMEPLAY-4 | partial | UPHELD | C-CAMERA (L4, gameplay-camera) exists, and the C-VIEW summary now says shake and accessibility scaling belong to C-CAMERA. It is consumed optionally by gameplay-systems-toolkit, character-movement and cinematics-sequencer. Layer-3 vehicle-physics and narrative-dialogue cannot consume an L4 contract, so leaving them out is correct. |
| K-GAMEPLAY-7 | partial | OVERTURNED | `UI.LOC.terms` exists, but the C-LOC summary is still "String IDs, formatting, locale switching." C-LOC is the only interface through which gameplay-data and narrative-dialogue could hand term attributes to localization. Without a term reference in the contract, `UI.LOC.terms` has no contract surface. |
| K-GAMEPLAY-14 | reject | UPHELD | M means "shipping in some titles, evaluate per ADR", which fits acoustic propagation. The radar records the fallback. |
| K-PLATFORM-1 | partial | UPHELD | `PLAT.CON.confidential-slots` now covers input, sockets, IME/TTS, XR and crash upload, with contributors. C-CERT is split into a public register and per-holder partitions. NDA work stays in per-holder console instances (`platform-console`, `rhi-console`), and the domain skills contribute to it. A capability-level access field would be a schema change with no data consumer. |
| K-PLATFORM-7 | reject | UPHELD | `platform-services` has no platform tag, provides C-SVC and owns entitlements, IAP and identity, so store SDK backends do have an owner. A storefront axis is a nice-to-have, not a defect. |
| K-PLATFORM-8 | partial | UPHELD | rhi-d3d12 contributes to `RND.RHI.console`, and a non-responsibility is recorded on rhi-console. No new NDA-module modelling is needed given the per-holder rhi-console design. |
| K-PLATFORM-12 | reject | UPHELD | Each Apple framework already has a single cross-platform owner (`PLAT.SVC.*`, `INP.DEV.gamepads`, `AUD.ARCH.devices`, `BLD.REL.packaging`). The only residual point is that tvOS is unmentioned, which is immaterial. |
| K-PROD-8 | reject | UPHELD | `QA.FUNC.bug-capture` (functional-automation-soak) and `OBS.CRASH.feedback` exist. The `player-feedback` input is already registered. |
| K-RENDER-5 | reject | UPHELD | The graph importing producer work items (`RND.GRAPH.external-work` lists AS builds, GPU decompression and uploads) is the framework's sanctioned inversion. Moving C-RTAS to L3 would break its non-render consumers. |
| K-RENDER-6 | partial | UPHELD | C-PTREF (L3, path-tracing, oracle_author render-validation) exists. It requires only C-RSCENE and C-MATIF, so the oracle contract has no contract-level dependency on C-LIGHT or C-TEMPORAL. The optional consumption at skill level is a residual weakness, but module attribution cannot express it (path-tracing has a single module). |
| K-SEC-6 | reject | UPHELD | `XC.SEC.agent-boundary` and `ARCH.ORG.human-gates` cover agent scoping and production data. A per-skill access object with a lint rule is a phase-2 SKILL.md design preference. |
| K-SEC-8 | reject | UPHELD | ED.ARCH.llm-agent-frontend is an M-class radar item with a CLI fallback. `ED.ARCH.automation-security` (editor-architect) already owns the permission model. The input's owner being the feature owner is defensible. |
| K-SEC-12 | reject | UPHELD | `XC.SEC.dev-trust`, `XC.EXT.mod-editor` and `ED.ARCH.process` cover signing, workspace trust and sandboxing. What remains is a wording nuance on a manifest field, which is not material. |
| K-SEC-15 | reject | UPHELD | `XC.SEC.tamper` is policy, like `XC.SEC.hardening`. Implementation sits under `BLD.REL.packaging`. |
| K-SIM-11 | reject | UPHELD | `PHY.COL.runtime-build` is budgeted. Hostile edits and meshes enter through registered inputs (`input-commands`, `mods`, `assets`) and are bounded by `NET.SRV.budgets`. Collision geometry is derived data, not a trust-boundary input. |
| K-TEST-4 | partial | UPHELD | The oracle authors are reassigned to quality validators. C-SIGN, C-SYNC, C-TASK, C-ML and C-PAL now have corpus-specific `oracle_reference` values. check.py requires it on L0-2, and no L0-2 contract lacks one. Consumer co-authoring by change request is sufficient. |
| K-TEST-6 | partial | OVERTURNED | `BLD.CI.sealed-suites` names an access class `sealed:oracle`, but C-ORCH, the contract that defines access classes and test write sets, lists only "public \| nda:<holder>" and says acceptance suites are "read-only (oracle-ro) for implementers", which still lets implementers read them. The class is undefined in the governing contract, so it is not a "phase-2" detail. |
| K-TOOLS-8 | partial | UPHELD | A `team-mid` add-on exists, and `standard-3d-team-tools` (std3d, online, team-mid) is in M4. `CNT.COOK.shared-cache` is tagged [lite3d, std3d], so every std3d tools configuration gets it. `ED.ARCH.telemetry`, `ED.COLLAB.multiuser` and `ED.COLLAB.session-server` are tagged team-mid and team-large. `cache-fleet` stays team-large. This meets the intent. |

## Required fixes

### K-ARCH-3 (docs only)
In `docs/00-design-principles.md` §2 (line 35), replace "A dispute inside one lead's subtree is settled by that lead. Only cross-workstream disputes reach `engine-architect` (`ARCH.ORG.escalation`)." with: "A dispute inside one lead's subtree is settled by that lead unless the arbitrating lead is a party to it. Disputes between leads of one workstream, disputes across workstreams, and disputes in which the arbitrating lead is a party reach `engine-architect` (`ARCH.ORG.escalation`)." No data or check.py change.

### K-GAMEPLAY-7
In `data/contracts.json`, change the C-LOC summary from "String IDs, formatting, locale switching." to "String IDs, formatting, locale switching; term references (per-locale grammatical attributes of substituted terms such as items, characters and places: gender, animacy, case forms, articles, particles) resolved for agreement in messages (UI.LOC.terms)." Regenerate the C-LOC row in `docs/02-skill-dependency-graph.md` and the contract listings in the docs, if the generator does not already do it. No radar entry is required.

### K-TEST-6
In `data/contracts.json`, edit the C-ORCH summary:
- Replace "access classes per skill (public | nda:<holder>)" with "access classes per skill and per path (public | nda:<holder> | sealed:oracle)".
- Replace "tests/acceptance/<contract-id>/ owned by the contract's oracle_author, read-only (oracle-ro) for implementers" with "tests/acceptance/<contract-id>/ owned by the contract's oracle_author, read-only (oracle-ro) for implementers; sealed holdouts, gate-time seeds and expected outputs live under access class sealed:oracle, readable only by oracle_author agents and CI runners and never by an implementer of that contract (BLD.CI.sealed-suites, QA.AGENT.holdout)".

Optionally add one check.py selftest, but not one on skills.json, since access classes are per skill there. Regenerate the C-ORCH text in docs if it is mirrored.
