# K-PROD · Production Critic · G1 round 2

### K-PROD-1 · blocker · dependency-error
- Target: data/milestones.json (M0–M4), scripts/check.py milestone gate, ARCH.ORG.milestones, ml-inference-runtime, platform-console, platform-mobile, platform-web, rhi-d3d12, rhi-metal, rhi-webgpu, collaboration-version-control, ai-assisted-authoring, online-services-liveops, anti-cheat-integrity, ik-procedural-animation, network-* skills
- Finding: The milestone check only proves *contract-dependency* closure of the skills named in each milestone. It does not check that the skills available by a milestone make up the configuration that the milestone names, or the configurations its exit text promises. I computed `members(config)` minus the skills available by each milestone, and every milestone before M5 fails its own exit:
  - **M1** (`indie-2d-client`, "shippable"). Missing: platform-console, platform-mobile, platform-web, rhi-d3d12, rhi-metal, rhi-webgpu, online-services-liveops, anti-cheat-integrity, ik-procedural-animation. The exit also promises "indie-2d-tools configuration builds", but that configuration also needs collaboration-version-control (joins M2) and ai-assisted-authoring (joins M5).
  - **M2** (`standard-3d-client`, and the lite-3d mobile configuration named in its exit). Missing: ml-inference-runtime (joins M5; its profiles are `lite3d`/`std3d`, so it is in every 3D build), motion-synthesis (joins M3), online-services-liveops, anti-cheat-integrity.
  - **M3** ("massim configuration closed and benchmarked"). `rts-3d-massim-client` includes `online`, but network-architect, network-transport, replication and prediction-rollback only join at M4.
  - **M4** (`online-3d-server`). Missing: ml-inference-runtime.
  
  The ladder is the program's schedule and the gate that agents are staffed against. As written, M1–M4 exit gates cannot pass: either agents stall, or gates get waived informally. Either way milestone gating stops meaning anything, and check.py reports this as proven.
- Evidence: I checked `Model.members()` against the cumulative milestone skill sets, using the same model the checker uses. check.py lines 233–252 never compare the milestone set with `m.members(ms["configuration"])`. PROTOCOL.md says the gate is trusted, so critics are told not to re-derive it. Production precedent: milestone exit criteria that are unreachable by construction are the classic cause of "milestone theatre" (see Keith, *Agile Game Development*, on vertical-slice definitions).
- Proposed change:
  - check.py: for every milestone, fail if `members(configuration)` (and every configuration listed in a new `exit_configurations` field) ⊄ skills available by that milestone. Restrict platforms with a new `platforms` field on the milestone, so M1 can honestly be `indie-2d-client@pc`. Add a selftest mutation for this.
  - milestones.json: set M1 platforms to [pc] and move indie-2d-tools to the milestone where collaboration-version-control joins. Either move ml-inference-runtime's profile to an add-on (`aaa`, or a new `ml` profile; it is an emerging, optional-contract capability per §7) or move it to M2. Move motion-synthesis to M2 or gate it by `aaa`. Split M3's massim claim into a single-player massim configuration, or move it after M4.

### K-PROD-2 · major · wrong-boundary
- Target: ARCH.ORG.staffing, ARCH.ORG.adjudication, ARCH.ORG.critic-calibration, ARCH.ORG.critic-gates, program-orchestration, reference-games (parent), QA.AGENT.oracle-independence
- Finding:
  - Staffing co-hosts skills "by workstream" but has no independence constraints. At small scale, one agent would host engine-architect, architecture-governance, program-orchestration and research-evidence, so the decider, the reviewer of decisions and the adjudicator are one agent. The rendering workstream, with 26 skills, becomes one monolithic agent.
  - program-orchestration owns 16 capabilities. Most are schedule and delivery (decomposition, milestones, triage, risk), yet it also owns critic calibration and independent adjudication, and its child reference-games owns the milestone release gate.
  - The party accountable for hitting milestones therefore also calibrates the critics, adjudicates rejected findings and owns the gate content. That is the builder-grades-itself problem that §6 and QA.AGENT.* reject for code, re-created at the organization level.
- Evidence: Separation of duties (release manager ≠ QA sign-off ≠ producer) is standard at AAA publishers, and certification exists because studios cannot self-certify. PROTOCOL.md itself requires "the builder never grades its own fixes". The data states that rule for G1 only, not for the engine program or for co-hosted staffing.
- Proposed change:
  - Add `ARCH.ORG.independence`: a never-co-host / never-same-agent matrix covering decider vs governance reviewer, implementer vs oracle author, builder vs adjudicator, security reviewer vs code under review, and milestone owner vs gate owner. Staffing must respect it at every organization tier. Also cap co-hosting by capability count, not only by workstream (e.g. rendering → at least 3 agents).
  - Move ARCH.ORG.adjudication and ARCH.ORG.critic-calibration to architecture-governance, or to a new `review-integrity` process skill that reports to engine-architect and not to program-orchestration.
  - Re-parent reference-games under test-architect.
  - Add a check.py rule for the matrix.

### K-PROD-3 · major · omission
- Target: reference-games, QA.REF.ladder, QA.REF.content, QA.REF.dogfood
- Finding: The reference-game ladder is one reference game per configuration (22 configurations), up to an AAA open-world online slice with production-scale content. It is both the milestone gate and the release gate. It is owned by one *process* expert with no build targets, no write set for game code and no content-acquisition capability.
  - Nobody owns building the reference games' game code: it is excluded as `external:*` game content everywhere else.
  - Nobody owns acquiring or generating production-scale content (licensed marketplace packs, scan libraries, procedural or synthetic content, with rights through CNT.ID.rights).
  - Nobody owns keeping those games alive across engine versions.
  
  This is the largest single production effort in the program, and it is modelled as a three-capability expert.
- Evidence: Every engine vendor staffs its dogfood content as full game teams: Epic's Fortnite and The Matrix Awakens/Valley of the Ancient, Unity's Demo Team (Enemies, The Heretic, Megacity), EA SEED's PICA PICA, Frostbite's first-party titles. Megacity-scale content alone took a dedicated team. Agents writing reference-game code are also the first real consumers of the public API (C-API). That is exactly the dogfooding the ladder is supposed to provide.
- Proposed change: Promote reference-games to a lead of a new `reference-production` workstream with runtime/tool kind and targets. Add experts, or at minimum capabilities:
  - `QA.REF.game-code`: reference-game gameplay code written only against public API. It is a build skill in each reference configuration.
  - `QA.REF.content-acquisition`: licensed, purchased, scanned, procedural and generated content sets with a rights manifest. Contributors: CNT.ID.rights, procedural-generation, ai-assisted-authoring.
  - `QA.REF.upkeep`: migrating reference games on every engine release, feeding ARCH.PROD.customer-corpus.
  
  Add reference-game content milestones to milestones.json.

### K-PROD-4 · major · omission
- Target: dedicated-server, online-services-liveops, packaging-release-patching, XC.SEC.incident, NET.ARCH.versioning, BLD.REL.staged-rollout
- Finding: Live operations is covered at the *feature* boundary (remote config, events, experiments, staged client rollout, kill switches). The *operational* side of running a live title has no owner:
  - Server-build release artifacts: container images, deploy manifests carrying compatibility keys, symbols.
  - Server process lifecycle for rolling deploys: health and readiness probes, graceful drain, session hand-off, old and new fleets running side by side.
  - Live-title SLOs and alerting built on engine telemetry.
  - Operational (non-security) incident response: crash-loop after a patch, login storms, a desync spike after a data hotfix, launch-day war-room triage.
  
  Only XC.SEC.incident exists, and it is owned by security-engineering with a security mandate. NET.ARCH.versioning mentions "rolling server deploys", but only as a compatibility policy. Nobody implements the drain and hand-off. BLD.REL.* is entirely store/client packaging.
- Evidence: Rolling deploys and fleet version skew are standard for session-based and persistent online games. Examples: Agones and GameLift server lifecycle hooks such as `Shutdown`/`ProcessEnding`, Riot's and Bungie's published live-ops postmortems, and GDC talks on launch-day readiness (e.g. the Destiny and Fortnite launch retrospectives). Backends are out of scope, but the engine-side server process behaviour and the artifacts are engine territory, just as `external:backend` leaves "the integration boundary" to the engine.
- Proposed change: Add:
  - `NET.SRV.lifecycle`: health/readiness, graceful drain, session migration on deploy, fleet-version coexistence. Owner dedicated-server; contributors network-architect, online-services-liveops.
  - `BLD.REL.server-artifacts`: server container images, deploy manifests with C-RELEASE compatibility keys. Owner packaging-release-patching.
  - `PLAT.LIVE.operations`: live-title SLO definitions over engine telemetry, alerting hooks, operational incident runbooks and launch readiness review. Owner online-services-liveops; contributors observability-telemetry, crash-diagnostics, dedicated-server.
  
  Narrow XC.SEC.incident to security incidents, with a hand-off to PLAT.LIVE.operations. Map a seed-map term "live-service operations" to the new capabilities.

### K-PROD-5 · major · omission
- Target: dedicated-server, online-services-liveops, visual-debugging-tools, security-engineering, XC.SEC.testing
- Finding: There is no owner for *production* admin, game-master and player-support tooling on live titles:
  - Authenticated admin commands on shipping servers: kick, ban, mute, grant or restore items, teleport, and inspecting a player's server-side state.
  - Role-based access control and an immutable audit log for those commands.
  - Customer-support views of player save and inventory history.
  
  The dev console and cheats in visual-debugging-tools are development-only and must be stripped from shipping builds (XC.SEC.testing audits that). So a live title has no sanctioned path at all, and teams bolt on unaudited back doors, which is a known exploit and insider-abuse vector.
- Evidence: Every live MMO or service game ships GM tooling as a separate, audited surface. Precedents are CCP's EVE GM tools, Blizzard's GM system, and Riot's player-support tooling talks. Platform policies and privacy law (GDPR access and rectification) also require support staff to be able to inspect and correct player data under audit.
- Proposed change: Add:
  - `NET.SRV.admin`: authenticated admin/GM command surface on shipping servers, RBAC, audit log, rate limits. Owner dedicated-server; contributors security-engineering, anti-cheat-integrity.
  - `PLAT.LIVE.support-tools`: player-support data inspection and restoration boundary over NET.SRV.persistence. Owner online-services-liveops; contributors persistence-save, XC.SEC.data-rights.
  
  Register the admin channel as an untrusted input with a fuzz target.

### K-PROD-6 · major · omission
- Target: ARCH.ORG.provenance, QA.CERT.licenses, CNT.ID.rights, research-evidence, media-playback, engine-product-management (ARCH.PROD.licensing-model)
- Finding: Legal/IP coverage stops at third-party dependency licences (SBOM) and asset rights. For an engine written by autonomous agents, the dominant IP risk is none of those. It is **code provenance**: agents are told to study UE5, Frostbite and others as references. UE5 source is available under an EULA that forbids its use in competing engines, and GPL/AGPL code is abundant online. Model output can reproduce licensed code verbatim.
  - No capability defines a clean-room policy: which sources agents may read versus only cite, and the separation of reading agents from implementing agents.
  - No capability defines similarity scanning of agent-produced code against known licensed corpora, or patent review of adopted techniques (research-evidence grades evidence but never checks encumbrance).
  - No capability covers codec royalty obligations (H.264/HEVC/AAC decode in media-playback, and audio codecs).
  
  ARCH.ORG.provenance records *which agent* wrote a change, not *whose IP* it contains.
- Evidence: Epic's UE EULA §"restrictions" bars using engine code in competing engine products. Clean-room practice is established precedent (Phoenix BIOS; the Wine/ReactOS contributor rules). Licence-similarity scanning (e.g. Black Duck/ScanCode snippet matching) is standard M&A due diligence for engines. MPEG-LA/Access Advance pool royalties apply to shipped decoders.
- Proposed change: Add:
  - `ARCH.EVID.source-policy`: allowed, cite-only and forbidden source classes for agents, plus clean-room separation. Owner research-evidence; contributors security-engineering, program-orchestration.
  - `QA.CERT.code-provenance`: snippet-similarity scanning of agent output as a merge gate, and licence contamination triage. Owner certification-compliance; contributor ci-cd-automation.
  - `QA.CERT.patents-codecs`: patent/encumbrance review as an ADR field, and a codec royalty register per shipped configuration. Owner certification-compliance; contributors media-playback, audio-dsp-mixing, architecture-governance.
  
  Add "legal sign-off on source policy" to ARCH.ORG.human-gates.

### K-PROD-7 · major · other
- Target: data/milestones.json, ARCH.ORG.milestones, QA.STRAT.release-criteria, certification-compliance, packaging-release-patching, api-lifecycle-migration
- Finding: The ladder stops at "AAA reference slice" (M5). It has no engine-as-product or ship-lifecycle milestones:
  - No first title passing *console certification* or store review. Console appears only at M2 as "runs on one console tier", and the only cert criterion is "pre-checks for online features" at M4, even though indie-2d-client targets console, mobile and web.
  - No milestone exercises patch, DLC, rollback or staged rollout on a shipped reference game.
  - No engine alpha, beta, 1.0 or LTS release with a tested upgrade path over the customer corpus.
  - No live-ops rehearsal and no end-of-service rehearsal.
  
  Separately, M1 adds 44 skills at once (76 build skills by M1): editor, graph editors, cinematics, media, AI, navigation, narrative and platform services. It is a big-bang integration labelled "vertical slice".
- Evidence: Late platform bring-up is the most common cause of AAA port crunch. Engines such as id Tech and Decima bring consoles up with the core. The cert/TRC failure loop typically takes 2–6 weeks per submission, and it must be rehearsed before any external team depends on it. Vertical slice practice (thin, full-depth path) comes from Keith, *Agile Game Development*, and Chandler, *The Game Production Handbook*.
- Proposed change:
  - Split M1 into M1a (playable 2D runtime on pc) and M1b (editor/tools, localization, accessibility, services).
  - Bring platform-console and platform-mobile bring-up into M1b, with a TRC/store-review dry run of the indie-2d reference game in its exit.
  - Add M4 exit items: patch plus DLC plus staged rollout plus rollback executed on the online reference game.
  - Add M6 "Engine 1.0 / first LTS": customer-corpus upgrade from the previous release, release notes, backport stream open, console cert pass of at least one reference game.
  - Add a live-ops/end-of-service rehearsal milestone.
  - Record milestone exit ownership as test-architect evidence plus a human gate.

### K-PROD-8 · major · missing-contract
- Target: ARCH.REQ.game-requirements, ARCH.PROD.roadmap, ARCH.PROD.intake, C-PROD, engine-architect, engine-product-management, performance-architect, build-release-architect, api-lifecycle-migration
- Finding: Game-team requirements have two owners with no contract edge between them:
  - engine-architect owns "capture target game requirements … as engine requirements" (ARCH.REQ.game-requirements) and consumes *nothing*.
  - engine-product-management owns roadmap and intake, and C-PROD is consumed only by program-orchestration.
  
  So profiles, hardware tiers and the platform matrix are set without a declared input from the roadmap. Release trains (C-RELEASE), LTS policy (XC.EXT.lts) and budgets (C-BUDGET) do not consume product priorities either. engine-product-management itself consumes no field signal: aggregated crash, perf and DX telemetry from shipped titles.
- Evidence: At engine vendors (Unity, Epic) product management owns "what and when" and architecture owns "how", joined by a requirements contract. Without that edge, agents cannot tell whose word wins when the roadmap and the profiles disagree.
- Proposed change:
  - Rename ARCH.REQ.game-requirements to "Translate prioritized requirements (C-PROD) into profiles, tiers and non-goals" and move raw capture into ARCH.PROD.intake.
  - Add C-PROD to consumes of engine-architect, build-release-architect, api-lifecycle-migration and performance-architect.
  - Add `ARCH.PROD.field-feedback`: cross-title crash, perf and DX metrics feeding the roadmap. Owner engine-product-management; contributors crash-diagnostics, performance-architect, developer-experience-docs.

### K-PROD-9 · major · scale-down
- Target: ED.COLLAB.locking, BLD.CI.farm
- Finding: `ED.COLLAB.locking` ("Locking & checkout workflows") is gated to `team-large`, so indie-2d-tools and standard-3d-tools have no exclusive checkout. Binary assets (textures, audio, world cells, one-file-per-object actors) cannot be merged, so even a 2–3 person team needs locks from day one. `BLD.CI.farm` also bundles "artifact storage" with the build farm under `team-large`, but small teams still need retained build artifacts for crash symbolication, bisection and store resubmission.
- Evidence: Git LFS added file locking precisely for small teams with binaries. Unity Version Control and Perforce Helix Core free tiers expose exclusive checkout for teams of 1–5. BLD.CI.local-first and OBS.CRASH.symbolication both presuppose retained artifacts.
- Proposed change: Remove the `team-large` tag from ED.COLLAB.locking; keep it on ED.COLLAB.multiuser. Split BLD.CI.farm into `BLD.CI.artifacts` (artifact retention, untagged) and `BLD.CI.farm` (team-large).

### K-PROD-10 · major · omission
- Target: api-lifecycle-migration, XC.EXT.upgrade, build-release-architect, ARCH.PROD.customer-corpus
- Finding: AAA licensees modify engine source. The upgrade story (codemods, data upgraders, deprecation) assumes projects consume the engine through its public API. Nothing owns:
  - supported customization seams versus source modification;
  - tracking of licensee engine modifications;
  - tooling and process for merging upstream engine releases into modified forks ("engine integrations");
  - policy for accepting licensee changes back upstream.
- Evidence: UE licensee "engine integration" is a known multi-engineer-month cost per release; The Coalition and Rare have given GDC/Unreal Fest talks on managing engine upgrades. Unity's source-licence customers face the same problem. Without a seam policy, every AAA customer drifts off the LTS path, and customer-corpus validation (ARCH.PROD.customer-corpus) no longer reflects real customers.
- Proposed change: Add:
  - `XC.EXT.fork-integration`: customization-seam catalogue, modification manifest, upstream-merge tooling and reports. Owner api-lifecycle-migration; contributors build-release-architect, collaboration-version-control.
  - `ARCH.PROD.upstreaming`: intake of licensee patches with IP terms. Owner engine-product-management; contributor certification-compliance (code provenance, see K-PROD-6).

### K-PROD-11 · major · omission
- Target: developer-experience-docs, XC.DX.*, ED.ARCH.discipline-workflows, ED.UI.ux
- Finding: The documentation and learning owner is programmer-centric: API reference, architecture docs, samples, doc-tests, error messages. No capability owns documentation and learning for *content creators*:
  - editor and tool user manuals per discipline (level design, lighting, animation, audio, VFX, UI, narrative);
  - in-editor contextual help;
  - tutorials and learning paths for non-programmers;
  - keeping creator docs in sync with tool changes.
  
  This leaves "content creators are first-class users" and "tooling as thorough as runtime" without a documentation owner, and domain TOOL owners have no obligation to document their editors.
- Evidence: Unreal's and Unity's creator documentation and learning portals (Unreal Online Learning, Unity Learn) are primary adoption drivers. Onboarding time for artists and designers is a standard studio cost metric. NN/g and GDC tools-UX talks (e.g. Insomniac's and Ubisoft's tools-UX teams) treat docs and in-tool help as part of tool quality.
- Proposed change:
  - Add `XC.DX.creator-docs`: per-discipline tool manuals, in-editor help surface and learning paths. Owner developer-experience-docs; contributors editor-ui-framework and each `<DOMAIN>.TOOL` owner.
  - Extend the crosscutting "authoring path" obligation to require creator-facing docs for each TOOL capability.
  - Add "content creator" to developer-experience-docs' purpose.

### K-PROD-12 · major · omission
- Target: data/crosscutting.json, localization-i18n, api-lifecycle-migration, online-services-liveops, packaging-release-patching
- Finding: The cross-cutting obligation list misses two production obligations that are classically bolted on late and then force rework across many skills:
  - **Localizability.** Every skill that emits player-visible text, audio or images (UI, narrative, cinematics, platform dialogs, error and system messages, achievements, store metadata) must use string IDs, allow text expansion and supply culturalizable variants. UI.LOC owns the mechanism but places no obligation on other skills.
  - **Post-launch changeability.** Every runtime skill should declare which behaviour can change without a client patch (remote config, data hotfix), which formats affect patch size or chunk stability, and how it behaves under client/server/content version skew.
- Evidence: Localization retrofits and patch-size blowups from unstable content layout are recurring postmortem items (Gamasutra/Game Developer postmortems; GDC Localization Summit talks). NET.ARCH.versioning and GAM.DATA.hotfix exist but only bind their owners.
- Proposed change: Add two concerns to crosscutting.json:
  - `localizability`, owner localization-i18n, obligation: "declare every player-visible text, audio and image output; use stable string IDs; support expansion, RTL and culturalized variants".
  - `live changeability`, owner online-services-liveops together with packaging-release-patching, obligation: "declare remote-tunable parameters, patch-stable data layout and behaviour under version skew".

### K-PROD-13 · major · omission
- Target: program-orchestration, architecture-governance, engine-architect (ARCH.STRUCT.arbitration), ARCH.ORG.*
- Finding: The framework defines how G1/G2 produce the skill library, but not how the library *evolves while the engine is being built*. Nobody owns:
  - re-bounding when a skill's territory outgrows one agent or an ADR changes the technique (split, merge, re-own);
  - regenerating the affected SKILL.md files and re-running check.py;
  - re-briefing the agents that host changed skills;
  - versioning the skill library against engine versions.
  
  ARCH.ORG.change-requests covers *contracts*, and territory loans cover temporary performance work. Permanent boundary changes during M0–M5 have no process, so SKILL.md files drift from the code and the ledger.
- Evidence: 08-phase-2-plan says graph changes found in G2 route back to G1, but says nothing after G2. Real organizations re-org teams at milestone boundaries; for agents, the SKILL.md *is* the team charter, so stale charters silently mis-route work.
- Proposed change: Add `ARCH.ORG.skill-lifecycle`: territory re-bounding via ADR, check.py re-gate, SKILL.md regeneration, agent re-brief, and library versioning tied to C-RELEASE. Owner program-orchestration; contributors architecture-governance and engine-architect. Require that a skill-lifecycle review runs at every milestone exit.

### K-PROD-14 · major · omission
- Target: collaboration-version-control, security-engineering, PLAT.PAL.confidential-extensions, BLD.CI.binary-distribution, ED.COLLAB.partial-sync
- Finding: AAA production relies on external co-development and outsourcing: art vendors, co-dev studios, porting houses and localization vendors. Access classes exist only for NDA platform code. Nothing owns:
  - project-scoped and asset-scoped access control for external partners;
  - editor and tool distributions for partners without full source;
  - delivery and acceptance workflows for vendor content (validation on ingest, rights capture);
  - revocation at contract end.
- Evidence: Outsourced content is a large share of AAA asset production (industry practice across Ubisoft, EA and Sony first-party; GDC outsourcing summit talks). Leaks through partner workspaces are a recurring source of pre-launch leaks.
- Proposed change: Add:
  - `ED.COLLAB.codev`: partner-scoped workspaces and permissions, vendor delivery/acceptance flow with CNT.VAL.submit-gate and CNT.ID.rights, access revocation. Owner collaboration-version-control; contributors security-engineering, ci-cd-automation. Tag it team-large.
  - Extend XC.SEC.dev-trust to cover partner access classes.

### K-PROD-15 · minor · wrong-boundary
- Target: build-release-architect, BLD.CI.orchestration, ci-cd-automation
- Finding: build-release-architect's purpose claims "orchestration of the code → content → package pipeline", but BLD.CI.orchestration is owned by ci-cd-automation. The purpose also omits territory the skill actually owns (BLD.CI.title-branching, BLD.CI.backports, BLD.REL.archival). An agent briefed from the purpose will contest ci-cd-automation's territory and neglect its own.
- Evidence: skills.json purpose text compared with the capabilities.json owners.
- Proposed change: Rewrite the purpose as "branching and merge model, engine release trains and versioning, title release-branch/content-lock/hotfix streams, LTS backports, shipped-build archival and rebuildability". Add a non-responsibility "pipeline orchestration → ci-cd-automation".

### K-PROD-16 · minor · omission
- Target: package-formats-vfs, packaging-release-patching, PLAT.LIVE.events
- Finding: Launch and live content confidentiality has no owner:
  - pre-load / pre-download of encrypted content with keys released at launch time;
  - datamining protection for unreleased live content shipped early in patches (encrypted chunks with server-delivered keys, per-event key rotation).
  
  PLAT.LIVE.events covers time-gated *activation*, not confidentiality or pre-load packaging.
- Evidence: Steam pre-load, console pre-download and Epic/Riot's encrypted-pak practice for live seasons exist because unreleased content leaks via datamining within hours of a patch.
- Proposed change: Add `BLD.REL.preload-embargo` (owner packaging-release-patching; contributors package-formats-vfs, online-services-liveops, security-engineering), and add the key-delivery path to C-LIVE.

### K-PROD-17 · minor · omission
- Target: program-orchestration, ARCH.ORG.human-gates, performance-architect
- Finding: "Spend" appears as a human gate, but nothing tracks or budgets program cost:
  - agent compute and tokens per skill and milestone;
  - CI, device-farm and cloud-cook cost;
  - load-test hosting;
  - server cost per CCU as a product constraint.
  
  Without a cost ledger, the risk register and staffing decisions have no economic input.
- Evidence: FinOps practice for CI/build farms and live server fleets; PRF.METH.model already computes capacity but not cost.
- Proposed change: Add `ARCH.ORG.cost-ledger` (owner program-orchestration; contributors ci-cd-automation, performance-architect, dedicated-server), and extend PRF.METH.model with cost per CCU and per build.
