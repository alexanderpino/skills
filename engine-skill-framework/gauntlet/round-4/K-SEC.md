# K-SEC round 4

### K-SEC-1 · major · omission
- Target: data/untrusted-inputs.json; ARCH.ORG.sensitive-paths; ARCH.ORG.skill-lifecycle; QA.AGENT.oracle-change-control; ARCH.ORG.human-gates
- Finding: The agent control plane is not a protected write set. Sensitive paths list "registry parsers, crypto, auth, sandboxes, build and CI", but not the ownership ledger and access-class definitions, critics.json and calibration seeds, check.py and its selftest, the untrusted-input registry itself, the human-gates register or the sealed-suite store. skill-lifecycle lets agents re-bound territory and re-run check.py. One agent can weaken the gate that constrains it: drop a registry entry, remove a critic scope, loosen an access class.
- Evidence: tamper-evident governance of automation (SLSA and CODEOWNERS practice: protect the policy repo more than the code repo); confused-deputy pattern in autonomous-agent pipelines.
- Proposed change: extend ARCH.ORG.sensitive-paths with a "control-plane" set (ledger, access classes, critics.json, check.py, registry, human-gates, calibration seeds). Changes need human-gate approval, not just a second agent. Add a fitness function that diffs the control plane between the agent branch and the protected branch.

### K-SEC-2 · major · omission
- Target: data/untrusted-inputs.json; NET.TRANS.local-network; NET.SRV.community-hosting; NET.SESS.server-browser; INP.DEV.abstraction; BLD.SYS.caching; CNT.COOK.distributed; BLD.REL.packaging; UI.LOC.pipeline
- Finding: Parsers of hostile bytes exist in capabilities but have no registry entry, so check.py's fuzz and limits proof never sees them. Missing: LAN discovery broadcast/mDNS replies; server-browser listings and query responses (server names, rulesets, player-controlled strings); community-server config and ruleset files (hostile to the host); HID reports and descriptors from hostile USB or Bluetooth devices; compile-cache and remote-execution results from build workers (cache poisoning); distributed-cook worker outputs; patch payloads and delta chunks (registry has only patch-manifests, but the delta applier runs on downloaded bytes); localization files from external vendors (format-specifier and markup injection).
- Evidence: CVE classes (mDNS and server-list overflows in shipped engines, USB HID descriptor fuzzing, Bazel and sccache cache-poisoning writeups, bsdiff and courgette patch-parser bugs, printf-style locale-string exploits).
- Proposed change: add registry entries lan-discovery, server-listings, community-server-config, hid-reports, remote-build-results (validating owner build-system-toolchains, content-pipeline-architect for cook), patch-payloads (packaging-release-patching, parser package-formats-vfs), localization-imports (localization-i18n). Give each a fuzz target or red-team mode, and limits.

### K-SEC-3 · major · omission
- Target: data/untrusted-inputs.json; XC.SEC.agent-boundary; XC.SEC.agent-redteam; ARCH.PROD.upstreaming; ARCH.ORG.agent-continuity
- Finding: The agent-input class is incomplete for the development agents. Registered: web sources, reports, triage artifacts, inter-agent messages. Not registered: (a) tool and MCP server responses and tool descriptions consumed by development agents (tool poisoning); (b) persisted agent memory, notes and hand-off records reloaded after a restart (only inter-agent messages are covered, not the persistent store); (c) licensee or contributor patches and PR text arriving through ARCH.PROD.upstreaming, which are both code and instructions; (d) SKILL.md or library content regenerated from web research, a persistence path for injection. third-party-source covers dependencies only.
- Evidence: MCP tool-poisoning and rug-pull research (Invariant Labs 2025); indirect prompt injection (Greshake et al. 2023); memory-poisoning attacks on agents; xz-utils maintainer takeover as the code-intake analogue.
- Proposed change: add redteam-mode inputs tool-outputs, agent-memory, contributed-patches. Validating owners: security-engineering for tool-outputs (allow-listed tool set, pinned descriptions), program-orchestration for agent-memory, engine-product-management for contributed-patches. Extend XC.SEC.agent-redteam corpus to cover them.

### K-SEC-4 · major · omission
- Target: data/milestones.json (M0, M2, M4); XC.SEC.agent-redteam; XC.SEC.dev-trust; XC.SEC.server-validation; XC.SEC.info-hiding; XC.SEC.incident; XC.SEC.attestation; NET.SRV.admin; NET.SRV.transactions; PLAT.COMM.receipts
- Finding: Milestone gates skip security capabilities that the exit text or configurations rely on. Of 30 XC.SEC capabilities, 22 are never gated, including agent-redteam (agents write code from M0), dev-trust (editor plugins and workspace trust at M2 tools) and incident (the first live title at M4). M4's "server-authority review and external pen test" are prose, not gates. Server validation, info-hiding, admin, transactions and receipts are ungated, so a first online release can pass with no exercised incident path or server-authority evidence.
- Evidence: check.py validates only that gate capabilities exist; the ladder therefore proves nothing about ungated capabilities. Live-service practice (incident tabletop before launch, GDC security talks on server authority).
- Proposed change: add gates. M0: XC.SEC.agent-redteam. M2 (tools closing): XC.SEC.dev-trust. M4: XC.SEC.server-validation, XC.SEC.info-hiding, XC.SEC.incident (tabletop plus key-compromise drill), XC.SEC.testing (external pen test, human gate), NET.SRV.admin, NET.SRV.transactions, PLAT.COMM.receipts, XC.SEC.attestation when a mobile or PC online title ships.

### K-SEC-5 · minor · wrong-boundary
- Target: security-engineering (18 capabilities); XC.SEC.agent-boundary; XC.SEC.key-custody; XC.SEC.dev-trust; XC.SEC.supply-chain; XC.SEC.secrets
- Finding: One process skill owns both product security (threat model, sandbox policy, memory safety, crypto policy) and the security of the agent program itself (agent boundary, key custody, dev-trust, secrets, supply chain, incident). The second set is the highest-risk, lowest-maturity part (agent-boundary is M) and its owner reviews everything else. It is also the only independent gate on the agents that write security-critical code. The independence matrix separates "security reviewer vs reviewed code", but one skill still both defines and reviews program-level controls.
- Evidence: separation of product security from corporate and DevSecOps security in mature organizations; SLSA distinguishes producer, build and consumer trust.
- Proposed change: split "development-security" (agent-boundary, agent-redteam, key-custody, secrets, supply-chain, dev-trust) out of security-engineering as an expert under it, or make it a separate lead in the governance workstream with its own domain critic. Record the independence pair with security-engineering.

### K-SEC-6 · minor · maturity-error
- Target: untrusted-inputs.json cloud-saves (trust semi-trusted-signed); GAM.SAVE.integrity
- Finding: Cloud saves are labeled semi-trusted-signed. A client-held signature does not authenticate against the device owner or the user's other accounts: platform sync layers expose saves to editing, and shared or community saves cross accounts. Only a server-held signature over server-produced data is semi-trusted. The label may lower validation effort for exactly the input most often tampered with.
- Evidence: standard save-editor and save-swap exploit history (Souls-class, Zelda-class save-parser exploits leading to code execution).
- Proposed change: relabel cloud-saves hostile-local unless the save is server-authoritative. Split entries: server-signed-saves (semi-trusted) and synced-client-saves (hostile-local). Require the same parser limits as saves.

### K-SEC-7 · minor · omission
- Target: XC.SEC.hardening; PLAT.SRV.host-os; NET.SRV.community-hosting; PLAT.WEB.runtime
- Finding: No capability names microarchitectural side-channel and co-tenancy threats: Spectre-class mitigations policy for shipped servers on shared hosts, timing-safe comparison in auth and ticket validation, shared-hardware GPU and cache side channels for cloud-streamed or multi-tenant server hosting. Only web cross-origin isolation is mentioned, and C-SIGN lists constant-time code only as expertise, not as a conformance obligation.
- Evidence: Spectre/Meltdown mitigation matrices per platform; Wycheproof timing vectors; multi-tenant game hosting on shared cloud instances.
- Proposed change: extend XC.SEC.hardening's per-platform matrix with a side-channel row (retpoline/SSBD policy, tenant isolation for server hosts); add a constant-time test obligation to C-SIGN's conformance suite (oracle author security-engineering).

### K-SEC-8 · minor · wrong-owner
- Target: XC.SEC.tamper; anti-cheat-integrity; C-INTEGRITY
- Finding: Anti-tamper and DRM boundary is owned by a process skill (security-engineering) with no code territory. Executable self-integrity, launch-time signature verification and licence or entitlement-gated startup have no implementation owner. The consumed C-INTEGRITY only covers server-side and middleware integration.
- Evidence: anti-tamper and DRM middleware need code integration (startup, packaging, exclusion from crash and debug builds), which lands in packaging-release-patching or platform PALs.
- Proposed change: assign the implementation slot for launch-time verification to security-runtime (using C-SIGN) with platform contributions, and keep security-engineering as policy owner. Make it explicit in the boundary contract.
