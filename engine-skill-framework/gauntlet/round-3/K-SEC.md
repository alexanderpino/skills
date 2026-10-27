# K-SEC — Security Critic, round 3

### K-SEC-1 · major · obsolete-assumption
- **Target:** untrusted-inputs.json `saves`, `cloud-saves`, `config-layers`; GAM.SAVE.integrity; persistence-save
- **Finding:** Local saves are classed `trusted-local`. Cloud saves and local config layers are classed `semi-trusted-signed`, but the only signer is the client, which holds the key. A save is a file the attacker fully controls: it is shared online, edited in save editors and restored from USB or cloud by the attacker's own account. A signature made with a key embedded in the client is not a trust boundary. The same applies to user-writable ini/cvar layers on PC.
- **Evidence:** Save-game exploits are the classic console jailbreak entry point: Twilight Hack (Wii), Smash Stack, and the PSP/3DS save exploits. Platform holders test for save robustness in certification. The framework's own L48 says "long-lived secrets in clients" is legacy, so "semi-trusted-signed" for client-signed data contradicts it. XC.SEC.memory-safety makes the hardened parser depend on the trust class, so this label silently lets save parsing skip it.
- **Proposed change:** Set `saves` → `hostile-local` and `cloud-saves` → `hostile-remote`. Split `config-layers` into `config-layers-local` (hostile-local: user ini, command line, intents) and `config-layers-remote` (semi-trusted-signed, server-signed only). Reword GAM.SAVE.integrity to "Save tamper policy: client-side signatures are corruption/casual-edit detection only, never a trust boundary; authoritative progression lives in NET.SRV.persistence". Add a rule to untrusted-inputs.json `_doc`: `semi-trusted-signed` requires a signer key that is not present on the client.

### K-SEC-2 · major · wrong-boundary
- **Target:** BLD.REL.staged-rollout; milestone M4 gate; XC.SEC.incident
- **Finding:** "Staged rollout" is defined as a "simultaneous global rollout to all players with post-release kill switches". That is the opposite of a staged rollout. Every compromised, malicious or defective update, including a supply-chain-injected one, reaches the whole player base before any signal comes back. Incident response has nothing it can halt.
- **Evidence:** Standard practice is percentage and cohort rollouts with automated halt on crash/telemetry regressions: Google Play staged rollouts, App Store phased release, Steam beta branches, and canary rings in live services. The CrowdStrike Channel File 291 incident (July 2024) shows how an all-at-once push fails. SolarWinds shows the supply-chain case.
- **Proposed change:** Rename and reword it to "Staged/phased rollout: cohort and percentage rings (internal → canary → %), automatic halt on crash-rate/telemetry regressions from OBS.CRASH.pipeline, server-side kill switches, signed rollback". Add `observability-telemetry` and `crash-diagnostics` as contributors. Add a legacy pattern: "All-at-once global release" → stance BLD.REL.staged-rollout, owner packaging-release-patching.

### K-SEC-3 · major · wrong-boundary
- **Target:** CNT.COOK.ddc; CNT.COOK.shared-cache; BLD.SYS.caching; RND.SHADER.cache; untrusted-inputs.json `shared-ddc`
- **Finding:** CNT.COOK.ddc says the derived-data cache is "keyed by source path & file modification time". The registry entry for `shared-ddc` promises "content-addressed/verified". Nobody can verify an entry keyed by path and mtime: any writer can plant arbitrary derived data under a key that every consumer trusts, and the cooked result then gets signed and shipped. Distributed compile caches and remote compilation (BLD.SYS.caching, RND.SHADER.cache) are not registered at all, although they are the same class of poisoning surface.
- **Evidence:** Bazel remote-cache and remote-execution guidance says only trusted CI may write and developers may only read, because a cache entry is not checkable. The ccache/sccache shared-cache poisoning advisories make the same point. Path+mtime keys are also a correctness legacy (clock skew, VCS sync resets mtime). Current practice keys on a hash of input content plus processor version and parameters.
- **Proposed change:** Reword CNT.COOK.ddc as "Derived-data cache keyed by hash of input content, processor version and parameters (content-addressed)". Add a CNT.COOK.shared-cache obligation: "write access restricted to trusted builders; client reads verified against key; poisoning drill". Add registry inputs `compile-cache` (owner build-system-toolchains) and `remote-shader-compile` (owner shader-system), trust hostile-local, with the limit "trusted-writer/verified". Add a legacy pattern "path/mtime-keyed derived caches".

### K-SEC-4 · major · dependency-error
- **Target:** C-SIGN (oracle_author modding-ugc), milestones M0; also C-SER, C-SCRIPT, C-AIAGENT, C-LIVE
- **Finding:** C-SIGN (crypto primitives, CSPRNG, signature envelope, anti-rollback) is frozen at M0. Its oracle author, modding-ugc, is first staffed at M4 and has no cryptographic expertise. The crypto contract is frozen with no conformance suite, and the future author is the wrong discipline. The same freeze-before-oracle pattern hits other security-bearing contracts: C-SER "untrusted-input rules" is frozen at M1 with its oracle at M2, C-SCRIPT "sandbox limits" at M2 with its oracle at M4, and C-AIAGENT and C-LIVE at M2 with their oracles at M4. Overall, 29 contracts are frozen before their oracle author is staffed. check.py only checks the owner and a consumer.
- **Evidence:** Crypto conformance depends on negative vectors: Project Wycheproof, NIST CAVP/ACVP, signature malleability, invalid-curve points, and rollback/downgrade cases per TUF. A mod-distribution skill will write positive-path tests. Freezing a contract with no acceptance suite defeats the framework's own rule that "acceptance suites are read-only for implementers".
- **Proposed change:** Set C-SIGN `oracle_author` to `security-engineering`, which is always staffed as a process skill, with required Wycheproof/ACVP/TUF vectors. Add a check.py rule that the oracle author must be staffed by the freeze milestone. For the other contracts listed, move the oracle author to a skill present at freeze (C-SER → robustness-fuzzing, C-SCRIPT → security-engineering) or move the freeze.

### K-SEC-5 · major · other
- **Target:** security-runtime, security-engineering (workstream `quality`); crosscutting.json independence; ARCH.ORG.staffing
- **Finding:** security-runtime writes the most security-critical code in the engine: crypto, the signed-artifact envelope, trust roots. It shares workstream `quality` with security-engineering, its reviewer. The docs say a small effort co-hosts one workstream in one agent, so the security reviewer can end up reviewing its own crypto code. The independence pair (security-engineering, owning-skill) is not machine-checked, because check.py compares workstreams only for named skills.
- **Evidence:** The framework's own independence principle ("security reviewer vs reviewed code") and ARCH.ORG.sensitive-paths ("crypto… require a K-SEC gate plus a second agent's approval") are defeated when the work is co-hosted.
- **Proposed change:** Move security-runtime to workstream `core`/foundation. Add the explicit independence pair `["security-engineering","security-runtime","security reviewer vs crypto implementer"]` to crosscutting.json so check.py enforces it.

### K-SEC-6 · major · omission
- **Target:** skills.json access classes (only `nda:per-platform-holder` exists); XC.SEC.agent-boundary; ARCH.ORG.human-gates
- **Finding:** Least privilege for development agents is described in prose (XC.SEC.agent-boundary) but not recorded per skill. The only access class in the data is NDA. Nothing records which roles have network egress (research-evidence reads the web), which read production player data (crash-diagnostics triaging player dumps, online-services-liveops support tools, observability-telemetry), which may write to CI or sensitive paths, and which may request signing. Phase-2 SKILL.md files therefore cannot state an agent's privileges, and nothing prevents a role from combining untrusted input, private data and egress.
- **Evidence:** This is the "lethal trifecta" for prompt injection (Willison 2025): private data, untrusted content and an exfiltration channel in one agent. OWASP LLM Top 10 lists LLM06 Excessive Agency. The registry already lists agent inputs per role, so the combination can be computed.
- **Proposed change:** Add an `access` object per skill with fields `egress` (none/allow-list/research), `data` (none/pseudonymous/player-PII/production), `ci` (none/propose/write) and `secrets` (always none). Add a check.py rule: no skill with an agent-input (redteam) entry or web egress may also hold player-PII/production data or CI write. Add "agent access to production player data" to ARCH.ORG.human-gates.

### K-SEC-7 · major · omission
- **Target:** untrusted-inputs.json agent inputs (web-sources, external-reports, vuln-reports, third-party-source, project-content-to-llm); XC.SEC.agent-redteam
- **Finding:** Several attacker-reachable texts that agents read are missing from the agent-input registry:
  - Player bug reports and feedback (OBS.CRASH.feedback).
  - Crash annotations and log lines carrying player-controlled strings, read by triage agents (ARCH.ORG.triage, OBS.CRASH.pipeline). They are registered only as a Log4Shell-style harness input (`logged-untrusted-strings`), not as a red-team input.
  - CI and test output that includes content from third-party code.
  - Inter-agent artefacts: change requests, critic findings, commit messages and code-review comments produced by other, possibly injected, agents (ARCH.ORG.change-requests).
  - Mod/UGC text read by moderation or support agents.

  A single injected agent can move laterally through change requests.
- **Evidence:** Indirect prompt injection (Greshake et al. 2023) and published injections through GitHub issues and PR comments against coding agents (2025) show that any text an agent reads is an input.
- **Proposed change:** Add red-team inputs `player-feedback` (validator crash-diagnostics), `triage-artifacts` (crash/log/CI output; validator ci-cd-automation) and `inter-agent-messages` (validator program-orchestration, limit "provenance-tagged, quarantined as data, no instruction authority"). Extend XC.SEC.agent-redteam to cover agent-to-agent propagation.

### K-SEC-8 · major · wrong-owner
- **Target:** untrusted-inputs.json `project-content-to-llm` (validator ai-assisted-authoring, staffed at M6); ED.ARCH.llm-agent-frontend and ED.ARCH.automation-security (editor-architect, staffed at M2)
- **Finding:** The editor LLM/agent front end (MCP class) is built and staffed from M2. It ingests project content: asset names, scripts, mod files, imported DCC metadata. The validating owner for that input is ai-assisted-authoring, which does not arrive until M6. So for four milestones the injection surface of an agent that can execute editor commands has no validating owner. The owner that does hold the permission model (ED.ARCH.automation-security) is editor-architect.
- **Evidence:** The MCP tool-poisoning and injection advisories of 2025 show that project-content injection turns directly into tool actions.
- **Proposed change:** Set the `project-content-to-llm` validating owner to editor-architect and add ai-assisted-authoring as a parser owner. Add a check.py rule that the validating owner must be staffed no later than every skill that consumes the input.

### K-SEC-9 · major · dependency-error
- **Target:** milestones.json M0–M2 gates; build-system-toolchains and ci-cd-automation (first staffed at M2); `third-party-source`; XC.SEC.supply-chain, XC.SEC.agent-boundary, XC.SEC.secrets, XC.SEC.key-custody, XC.SEC.data-rights, XC.SEC.vuln-response
- **Finding:** Agents write code, pull third-party libraries (Vulkan loader, zstd) and run CI from M0. The M0 exit even signs assets. Yet the owners of the build graph, third-party dependency management, CI pipelines and the `third-party-source` validator are only staffed at M2. No milestone gates agent boundaries, supply chain, secrets or key custody. M2 ships to stores, including mobile with ATT and children's audiences, with no privacy/data-rights gate and no vulnerability-response readiness gate. Security gates appear only at M1 (threats, hardening), M4 (DoS) and M6 (sandbox).
- **Evidence:** SLSA and NIST SSDF (SP 800-218) put the PO/PS controls before development. App Store and Google Play require privacy labels and account deletion at first submission. CRA-class regulation requires vulnerability handling from first placement on the market.
- **Proposed change:** Staff build-system-toolchains and ci-cd-automation at M0. Add M0 gates XC.SEC.agent-boundary, XC.SEC.supply-chain, XC.SEC.secrets and XC.SEC.key-custody. Add M2 gates XC.SEC.data-rights, XC.SEC.childrens-data and XC.SEC.vuln-response.

### K-SEC-10 · major · omission
- **Target:** ci-cd-automation, build-system-toolchains, packaging-release-patching; XC.SEC.supply-chain; BLD.REL.server-artifacts; dedicated-server
- **Finding:** XC.SEC.supply-chain is policy owned by a process skill. No code-owning skill has a capability for:
  - build provenance attestation (SLSA/in-toto);
  - hermetic, isolated, ephemeral CI runners;
  - separation of untrusted, agent-authored pre-merge jobs from privileged release jobs;
  - short-lived workload identity (OIDC) instead of static CI and cloud credentials;
  - secret delivery to server fleets without baking secrets into container images.

  ci-cd-automation's purpose never mentions security, and it is not a contributor to XC.SEC.supply-chain.
- **Evidence:** SLSA Build L3 requires an isolated build platform and non-forgeable provenance. Precedents: GitHub "pwn request" attacks on privileged workflows, Codecov (2021), tj-actions/changed-files (2025) and the xz-utils backdoor (2024).
- **Proposed change:** Add BLD.CI.hardening (owner ci-cd-automation): "Ephemeral isolated runners, untrusted vs privileged job separation, OIDC workload identity, pinned actions/images, CI audit log". Add BLD.SYS.provenance (owner build-system-toolchains): "Hermetic builds, SLSA provenance and in-toto attestations verified at packaging". Add NET.SRV.secrets-delivery (owner dedicated-server, contributor security-engineering). Add a legacy pattern "Long-lived static CI/cloud credentials".

### K-SEC-11 · major · omission
- **Target:** crosscutting.json concerns; privacy-data-protection; XC.SEC.privacy-review
- **Finding:** The framework has a cross-cutting concern for security and one for untrusted input, but none for personal data. Privacy review is a capability, yet no skill has an obligation to declare the personal data it collects, stores, logs or transmits. Many skills handle personal data without being privacy-scoped: replays (names, voice), crash dumps, analytics, XR scene/gaze, voice chat, UGC, player feedback, cloud saves, leaderboards and anchors. Their SKILL.md files will have no privacy section, and XC.SEC.data-rights will have no input.
- **Evidence:** GDPR Art. 25 (data protection by design) and Art. 30 (records of processing), the UK AADC and COPPA all need a per-feature data inventory. Store privacy labels (App Store privacy nutrition labels, Google Play data safety) need it per SDK and feature.
- **Proposed change:** Add the concern `{"concern":"personal data","owner":"privacy-data-protection","obligation":"Declare personal/sensitive data classes collected, stored, logged or transmitted, purpose, retention, on-device default and deletion path; feed XC.SEC.data-rights"}`. Add a check.py rule that skills listed as contributors to privacy-classed capabilities declare it.

### K-SEC-12 · major · wrong-boundary
- **Target:** untrusted-inputs.json `editor-plugins` (limit "permissions"), `mods` (parser plugin-system); XC.EXT.plugin-trust; ED.ARCH.extension; ED.ARCH.process
- **Finding:** Native editor plugins and editor Python/tool scripts are registered as a fuzzable input whose limit is a "permissions" manifest. For in-process native code, and for unsandboxed Python, a permission manifest is advisory: the code has full process and user privileges. The real boundaries are the publisher's signature, a workspace-trust decision, and out-of-process or WASM hosting for anything that claims permissions. Marketplace and outsourced plugins are a known compromise vector.
- **Evidence:** Malicious Unity/Unreal marketplace packages, the VS Code extension malware campaigns of 2023–25, and the design of VS Code's own Workspace Trust. Browser extension models enforce permissions only because the extension runs out of process.
- **Proposed change:** Split the `editor-plugins` input into `editor-plugins-native` (trust = code; limit "signed publisher + workspace trust + human gate for unsigned") and `editor-plugins-sandboxed` (limit "out-of-process/WASM host, enforced capability permissions"). Add ED.ARCH.plugin-isolation (owner editor-architect, contributor plugin-system): "out-of-process/WASM plugin host enforcing permission manifests". Reword XC.EXT.plugin-trust to say manifests are enforceable only in isolated hosts.

### K-SEC-13 · major · omission
- **Target:** PLAT.COMM.*, PLAT.SVC.identity, NET.SRV.transactions, anti-cheat-integrity
- **Finding:** Commerce and account security have three gaps:
  - Refunds, voided purchases and chargebacks: there is no entitlement or virtual-currency revocation or clawback, so buy → consume → refund abuse goes unhandled.
  - No capability covers client-side storage of refresh and session tokens in the OS keychain, Keystore, DPAPI or platform secure storage.
  - No capability covers account-linking and login flows using the system browser with PKCE instead of embedded webviews.

  Account takeover and linking abuse (crossplay identity) have no threat owner.
- **Evidence:** Google Play Voided Purchases API, App Store Server Notifications (REFUND/REVOKE), Steam refund policy and its abuse cases. RFC 8252 (OAuth for native apps: no embedded user agents) and RFC 7636 (PKCE). OWASP MASVS-STORAGE.
- **Proposed change:** Add PLAT.COMM.revocation (owner platform-services, contributors server-scaleout-persistence and anti-cheat-integrity): "Refund/void/chargeback notifications → idempotent entitlement & currency clawback, abuse signals". Add PLAT.SVC.credential-storage (owner platform-services, contributor security-runtime): "Platform secure token storage, token lifetimes, system-browser+PKCE login and linking, account-takeover signals". Register `store-notifications` as an untrusted input (hostile-remote, signature-verified).

### K-SEC-14 · major · obsolete-assumption
- **Target:** PLAT.WEB.runtime
- **Finding:** "SharedArrayBuffer required; cross-origin isolation assumed on every host" is false. Web-game portals and embedding sites frequently serve games in cross-origin iframes without COOP/COEP. COEP `require-corp` also breaks the third-party ad and analytics SDKs that PLAT.COMM.ads integrates. Cross-origin isolation is a Spectre mitigation that the host controls, not the engine. The engine should detect it, not assume it.
- **Evidence:** The Chrome/Firefox SharedArrayBuffer gating since 2020–21 (the Spectre response). The `self.crossOriginIsolated` feature check. Poki/CrazyGames/itch-style iframe embedding. CORE.JOBS.degenerate already provides the 0-worker fallback.
- **Proposed change:** Reword to "WASM threads when `crossOriginIsolated` (COOP/COEP) is available; otherwise fall back to CORE.JOBS.degenerate inline mode; document the COEP/credentialless impact on ad/analytics SDKs". Add `security-engineering` as a contributor.

### K-SEC-15 · minor · wrong-owner
- **Target:** XC.SEC.tamper (owner security-engineering, a process skill)
- **Finding:** "Anti-tamper & DRM boundary" is an integration boundary made of code: packaging hooks, runtime checks and the perf-exempt code-region list. Yet its owner is a process skill, which the framework's own principle says cannot own code. By contrast, XC.SEC.anticheat, the analogous middleware boundary, sits in a runtime skill.
- **Evidence:** docs/00 §8: "a process skill cannot own code". Denuvo-class DRM integrates at link and package time and has a measured frame-time cost.
- **Proposed change:** Split the capability. Policy stays as XC.SEC.tamper-policy (owner security-engineering). Integration goes to XC.SEC.tamper-integration (owner packaging-release-patching, contributors anti-cheat-integrity and cpu-performance).

### K-SEC-16 · minor · overlap
- **Target:** security-engineering purpose, expertise and non_responsibilities
- **Finding:** security-engineering's purpose and expertise still claim "privacy engineering", but XC.SEC.privacy, XC.SEC.data-rights and XC.SEC.childrens-data belong to privacy-data-protection. Its non-responsibilities also do not route crypto and signed-artifact code to security-runtime. The generated SKILL.md will claim territory that belongs to two other skills.
- **Evidence:** skills.json security-engineering: purpose "...privacy engineering, mod/UGC sandbox policy"; the non_responsibilities list only anti-cheat, fuzzing and transport.
- **Proposed change:** Remove privacy from the purpose and expertise. Add the non-responsibilities `["Privacy engineering & data rights","privacy-data-protection"]` and `["Crypto & signed-artifact implementation","security-runtime"]`.

### K-SEC-17 · minor · omission
- **Target:** BLD.CI.build-distribution; BLD.SYS.dev-surface-exclusion
- **Finding:** Builds for external playtesters and betas leave the studio, but nothing requires them to be dev-surface-free. There is also no watermarking or traceability, and no revocation of pre-release builds. These builds are the main source of leaks and datamining, and they are how development endpoints (C-AUTOMATION, the console) get exposed.
- **Evidence:** Frequent leaks of pre-release builds from external playtests. BLD.REL.preload-embargo shows that datamining is already in the threat model.
- **Proposed change:** Extend BLD.CI.build-distribution: "external builds use test/shipping configurations passing dev-surface exclusion, per-recipient forensic watermarking, expiring entitlement/revocation". Add `security-engineering` as a contributor.
