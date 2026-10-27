"""Round-2 revision, part F: K-PROD, K-TEST, K-SEC and K-FUTURE findings (production lifecycle, oracle independence,
untrusted-input registry, signing, maturity honesty, experimental opt-in)."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def _unt(ed, sid, *ids):
    s = ed.skill(sid)
    s["untrusted_inputs"] = sorted(set(s.get("untrusted_inputs") or []) | set(ids))


def apply(ed):
    cfgs = ed.doc["skill"]["configurations"]

    # ================================================================ PROD
    t = "K-PROD-3"
    ed.skill_set("reference-games", kind="runtime", targets=["client", "headless-client", "server", "tools"],
                 consumes=["C-GAME", "C-INPUT?", "C-UI?", "C-SCRIPT?", "C-GAMEDATA?", "C-API"],
                 purpose="The reference-game ladder (one representative game per configuration) used as milestone and "
                         "release gate: reference-game code written only against the public API, production-scale "
                         "content acquired or generated with a rights manifest, upkeep across engine releases, and the "
                         "internal playtest and dogfood loop.", tags=t)
    ed.cap("QA.REF.game-code", "Reference-game gameplay code written only against the public API (a build skill in "
           "each reference configuration)", "reference-games", contrib=["gameplay-architect"], tags=t)
    ed.cap("QA.REF.content-acquisition", "Licensed, purchased, scanned, procedural and generated reference content "
           "with a rights manifest", "reference-games", contrib=["content-pipeline-architect",
                                                              "procedural-generation"], tags=t)
    ed.cap("QA.REF.upkeep", "Reference-game migration on every engine release (feeds ARCH.PROD.customer-corpus)",
           "reference-games", contrib=["api-lifecycle-migration"], tags=t)

    t = "K-PROD-4"
    ed.cap("BLD.REL.server-artifacts", "Server container images & deploy manifests with C-RELEASE compatibility keys",
           "packaging-release-patching", contrib=["dedicated-server"], tags=t)
    ed.cap("PLAT.LIVE.operations", "Live-title SLOs over engine telemetry, alerting hooks, operational incident "
           "runbooks & launch-readiness review", "online-services-liveops",
           contrib=["observability-telemetry", "crash-diagnostics", "dedicated-server"], tags=t)
    ed.cap_set("XC.SEC.incident", name="Security incident response for engine infrastructure and shipped/online "
               "titles (hand-off to PLAT.LIVE.operations for operational incidents)",
               add_contrib=["ci-cd-automation", "build-release-architect"], tags=t + " K-SEC-5")
    sm = ed.doc["seed"]
    sm["discovered_domains"]["live-service operations"] = ["PLAT.LIVE.operations", "NET.SRV.lifecycle",
                                                           "BLD.REL.server-artifacts"]

    t = "K-PROD-5"
    ed.cap("PLAT.LIVE.support-tools", "Player-support data inspection & restoration boundary over NET.SRV.persistence "
           "(audited)", "online-services-liveops", contrib=["persistence-save", "security-engineering"], tags=t)

    t = "K-PROD-6"
    ed.cap("ARCH.EVID.source-policy", "Source policy for agents: allowed, cite-only and forbidden source classes, "
           "clean-room separation of reading and implementing agents", "research-evidence",
           contrib=["security-engineering", "program-orchestration"], tags=t)
    ed.cap("QA.CERT.code-provenance", "Snippet-similarity scanning of agent output as a merge gate; licence "
           "contamination triage", "certification-compliance", contrib=["ci-cd-automation"], tags=t)
    ed.cap("QA.CERT.patents-codecs", "Patent/encumbrance review as an ADR field; codec royalty register per shipped "
           "configuration", "certification-compliance",
           contrib=["media-playback", "audio-dsp-mixing", "architecture-governance"], tags=t)

    t = "K-PROD-6 K-SEC-5 K-TEST-9"
    ed.cap_set("ARCH.ORG.human-gates", name="Register of decisions requiring human authorization (contracts, spend, "
               "NDA access, submissions, legal/source-policy sign-off, production signing, security exceptions & risk "
               "acceptance, CI permission/secret-scope changes, new third-party dependencies, vulnerability "
               "disclosure, telemetry scope, sampled audit of adjudications and S3/S4 verdicts)",
               add_contrib=["security-engineering"], tags=t)
    ed.cap_set("XC.SEC.key-custody", name="Signing-key custody: key hierarchy, HSM/KMS, signing as a gated service "
               "with human approval for production keys, rotation, revocation, compromise drill; no agent-held keys",
               add_contrib=["ci-cd-automation", "package-formats-vfs", "persistence-save"], tags="K-SEC-5")

    t = "K-PROD-8"
    ed.cap_set("ARCH.REQ.game-requirements", name="Translate prioritized requirements (C-PROD) into profiles, tiers "
               "and non-goals", tags=t)
    ed.cap_set("ARCH.PROD.intake", add_contrib=["engine-architect"], tags=t)
    for sid in ("engine-architect", "build-release-architect", "api-lifecycle-migration", "performance-architect"):
        ed.use(sid, "C-PROD", tags=t)
    ed.cap("ARCH.PROD.field-feedback", "Cross-title crash, performance and developer-experience metrics feeding the "
           "roadmap", "engine-product-management", contrib=["crash-diagnostics", "performance-architect",
                                                            "developer-experience-docs"], tags=t)

    t = "K-PROD-10"
    ed.cap("XC.EXT.fork-integration", "Customization-seam catalogue, licensee modification manifest, upstream-merge "
           "tooling & reports", "api-lifecycle-migration", contrib=["build-release-architect",
                                                                  "collaboration-version-control"], tags=t)
    ed.cap("ARCH.PROD.upstreaming", "Intake of licensee patches with IP terms", "engine-product-management",
           contrib=["certification-compliance"], tags=t)

    t = "K-PROD-11"
    ed.cap("XC.DX.creator-docs", "Creator documentation: per-discipline tool manuals, in-editor contextual help, "
           "learning paths for non-programmers, kept in sync with tool changes", "developer-experience-docs",
           contrib=["editor-ui-framework"], tags=t)
    s = ed.skill("developer-experience-docs")
    ed.skill_set("developer-experience-docs", purpose=s["purpose"].rstrip(".") + "; documentation and learning for "
                 "content creators as well as programmers.", tags=t)
    for c in ed.doc["cross"]["concerns"]:
        if c["concern"] == "authoring path":
            c["obligation"] = c["obligation"].rstrip(".") + "; ship creator-facing docs for every TOOL capability."

    t = "K-PROD-12"
    ed.doc["cross"]["concerns"] += [
        {"concern": "localizability", "owner": "localization-i18n",
         "obligation": "Declare every player-visible text, audio and image output; use stable string IDs; support "
                       "expansion, RTL and culturalized variants."},
        {"concern": "live changeability", "owner": "online-services-liveops",
         "obligation": "Declare remote-tunable parameters, patch-stable data layout and behaviour under client/server/"
                       "content version skew (with packaging-release-patching)."}]
    ed.note(t, "crosscutting += localizability, live changeability")

    t = "K-PROD-13"
    ed.cap("ARCH.ORG.skill-lifecycle", "Skill-library lifecycle during the build: territory re-bounding by ADR, "
           "check.py re-gate, SKILL.md regeneration, agent re-brief, library versioning tied to C-RELEASE; review at "
           "every milestone exit", "program-orchestration", contrib=["architecture-governance", "engine-architect"],
           tags=t)

    t = "K-PROD-14 K-COMPLETE-20"
    ed.cap("ED.COLLAB.codev", "Co-development & outsourcing: partner-scoped workspaces and permissions, vendor "
           "delivery/acceptance via CNT.VAL.submit-gate and CNT.ID.rights, access revocation",
           "collaboration-version-control", contrib=["security-engineering", "ci-cd-automation"],
           profiles=["team-large"], tags=t)
    ed.cap("ED.COLLAB.production-tracking", "Production-tracking integration (asset/shot status, task-tracker links)",
           "collaboration-version-control", profiles=["team-large"], tags=t)
    ed.cap_set("XC.SEC.dev-trust", name="Project/workspace trust, partner access classes, plugin signing & "
               "permissions, sandboxed import of untrusted source assets", tags=t)

    t = "K-PROD-15"
    ed.skill_set("build-release-architect", purpose="Branching and merge model, engine release trains and versioning, "
                 "title release-branch/content-lock/hotfix streams, LTS backports, shipped-build archival and "
                 "rebuildability; pipeline architecture (execution by ci-cd-automation).", tags=t + " K-ARCH-14")
    ed.nonresp_add("build-release-architect", "Pipeline orchestration", "ci-cd-automation", tags=t)

    t = "K-PROD-16"
    ed.cap("BLD.REL.preload-embargo", "Pre-load of encrypted content with keys released at launch; per-event key "
           "delivery against datamining", "packaging-release-patching",
           contrib=["package-formats-vfs", "online-services-liveops", "security-engineering"], tags=t)
    _append(ed, "C-LIVE", "content-key delivery for pre-loaded and embargoed content.", t)

    t = "K-PROD-17"
    ed.cap("ARCH.ORG.cost-ledger", "Program cost ledger: agent compute per skill/milestone, CI/device-farm/cloud-cook "
           "cost, load-test hosting, server cost per CCU", "program-orchestration",
           contrib=["ci-cd-automation", "performance-architect", "dedicated-server"], tags=t)
    ed.cap_set("PRF.METH.model", name="Analytical performance, capacity & cost model (unit costs × counts per "
               "tier/configuration, cost per CCU and per build, predicted scale limits, reconciliation)", tags=t)

    # ================================================================ TEST
    t = "K-TEST-1"
    load = {}
    S = {s["id"]: s for s in ed.doc["skill"]["skills"]}
    consumers = {}
    for s in ed.doc["skill"]["skills"]:
        for d in s["consumes"] + s.get("tool_consumes", []):
            consumers.setdefault(d.split("@")[0].rstrip("?"), []).append(s["id"])
    for c in ed.doc["contract"]["contracts"]:
        if c["layer"] == "P":
            continue
        impls = [x for x in S if c["id"] in S[x].get("implements", [])]
        cands = [x for x in consumers.get(c["id"], []) if x != c["owner"] and S[x]["parent"] != c["owner"]]
        cands = cands or [x for x in consumers.get(c["id"], []) if x != c["owner"]]
        if impls and not cands:
            c["oracle_author"] = c["owner"]
        elif cands:
            best = min(sorted(set(cands)), key=lambda x: load.get(x, 0))
            load[best] = load.get(best, 0) + 1
            c["oracle_author"] = best
        else:
            c["oracle_author"] = "test-architect"
    ed.note(t, "oracle_author assigned to every code contract (a consumer, never the sole implementer)")
    _append(ed, "C-ORCH", "test write sets: tests/unit/<skill-id>/ implementer-owned; tests/acceptance/<contract-id>/ "
            "owned by the contract's oracle_author, read-only (oracle-ro) for implementers.", t)
    ed.cap_set("QA.AGENT.oracle-independence", name="Acceptance suites authored by each contract's declared "
               "oracle_author; implementers propose additions by change request only", tags=t)

    t = "K-TEST-2"
    for cid, name in (("QA.SIM.stability-suite", "Physics stability runner, metrics (penetration, energy drift) & "
                       "tolerance store"),
                      ("QA.SIM.golden-traces", "Simulation golden-trace comparison harness & baseline store"),
                      ("QA.SIM.animation", "Animation error metrics (pose error, compression, retarget, IK) & "
                       "tolerance store"),
                      ("QA.SIM.audio", "Audio metric library (BS.1770 loudness, glitch detection) & offline-render "
                       "comparison harness")):
        ed.cap_set(cid, name=name, tags=t)
    ed.use("simulation-validation", "C-PHYS", "C-ANIM", "C-AUDIO", "C-NET?", "C-REPLAY", tags=t)
    ed.nonresp("simulation-validation", [["Domain scenario definitions", ["physics-architect", "animation-architect",
                                          "audio-architect", "network-architect"]],
                                         ["Determinism matrix definition", "determinism-replay"]], tags=t)

    t = "K-TEST-3"
    ed.cap("QA.AGENT.oracle-change-control", "Changes to *.validation scene sets, metrics or thresholds need "
           "co-signature by the matching quality skill and are diffed by QA.AGENT.test-integrity", "test-architect",
           contrib=["simulation-validation", "render-validation"], tags=t)
    ed.cap("QA.RENDER.reference-validation", "Reference path tracer validated against analytic furnace scenes and an "
           "external renderer before serving as a baseline", "render-validation", contrib=["path-tracing"], tags=t)
    ed.cap_set("RND.MAT.validation", name="Material furnace & energy-conservation scenes (pass thresholds owned by "
               "render-validation)", add_contrib=["render-validation"], tags=t)

    t = "K-TEST-4"
    for cid, name, owner, con in [
            ("ML.RT.validation", "Backend & quantization conformance with tolerance tables; model-version regression",
             "ml-inference-runtime", []),
            ("GAM.AI.validation", "Navigation/AI oracles: navmesh connectivity & coverage, path optimality vs exact A*, "
             "avoidance without interpenetration", "navigation-pathfinding", ["simulation-validation"]),
            ("RES.MGMT.validation", "Streaming-correctness oracle: no required cell missing at traversal speed, "
             "residency invariants under arbitration", "resource-streaming-architect",
             ["loading-streaming-performance"]),
            ("UI.FW.validation", "UI layout/screenshot regression, focus-graph completeness, safe-area compliance",
             "ui-architect", ["functional-automation-soak"]),
            ("CNT.COOK.incremental-equivalence", "Incremental cook equals clean cook (bit/tolerance per determinism "
             "class)", "content-pipeline-architect", []),
            ("ED.ARCH.transaction-invariants", "Property-based do→undo→redo equivalence incl. multi-user merges",
             "editor-architect", ["functional-automation-soak"])]:
        ed.cap(cid, name, owner, "M" if cid.startswith("ML.") else "E", contrib=con, tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "ML.RT.inference" in e.get("capabilities", []):
            e["capabilities"].append("ML.RT.validation")

    t = "K-TEST-5"
    ed.skill_add(tags=t, id="test-runtime-harness", name="Test Runtime Harness", tier="expert", parent="test-architect",
                 profiles=["all"], kind="runtime", targets=["client", "headless-client", "server", "tools"],
                 workstream="quality",
                 purpose="Test infrastructure that ships as code on every target: unit/integration test framework, "
                         "on-device test runner and result reporting, fixtures, and the fault-point registry that "
                         "owners implement fault injection against.",
                 non_responsibilities=[["Test strategy & definition of done", "test-architect"],
                                       ["Fuzz/fault campaign policy", "robustness-fuzzing"],
                                       ["CI pipelines", "ci-cd-automation"]],
                 expertise=["test frameworks", "on-device test execution", "fault injection seams"],
                 consumes=["C-BASE", "C-PAL", "C-SYNC", "C-MEM"])
    ed.contract_add("C-TESTHOST", 1, "test-runtime-harness", "Test host",
                    "Test registration, runner, fixtures, fault-point registry, result reporting; present in "
                    "development and test builds of every configuration.", requires=["C-BASE"], universal="runtime",
                    conformance=True, tags=t)
    ed.cap_set("QA.STRAT.frameworks", name="Unit & integration test framework policy (implementation in "
               "QA.HOST.framework)", tags=t)
    ed.area("QA.HOST", "Test host runtime", tags=t)
    ed.cap("QA.HOST.framework", "Unit/integration test framework & fixtures (C-TESTHOST)", "test-runtime-harness",
           tags=t)
    ed.cap("QA.HOST.runner", "On-device test runner & result reporting for every platform", "test-runtime-harness",
           contrib=["platform-architect"], tags=t)
    ed.cap("QA.HOST.fault-points", "Fault-point registry (IO errors, OOM, device lost) implemented by owners",
           "test-runtime-harness", contrib=["async-io-storage", "memory-allocators", "rhi-core",
                                            "robustness-fuzzing"], tags=t)
    ed.cap_set("QA.ROBUST.faults", name="Fault-injection campaigns & policy (fault points in QA.HOST.fault-points)",
               tags=t)

    t = "K-TEST-7"
    boundary = {"C-PAL": ("null/fake platform + event injection", "platform-architect"),
                "C-RHI": ("null/software device", "rhi-core"),
                "C-IO": ("in-memory IO with fault points", "async-io-storage"),
                "C-SVC": ("first-party service emulator", "platform-services"),
                "C-LIVE": ("service emulator", "online-services-liveops"),
                "C-NETLINK": ("loopback + link conditioner", "network-transport"),
                "C-DEVICE": ("virtual devices / injection", "input-devices-haptics"),
                "C-MEM": ("tracking/failing allocator", "memory-allocators")}
    for cid, (kind, owner) in boundary.items():
        ed.contract_set(cid, boundary=True, test_double={"kind": kind, "owner": owner}, tags=t)
    ed.cap("PLAT.PAL.event-injection", "Lifecycle & system-event injection (suspend/resume, constrained mode, "
           "sign-out, controller disconnect, memory pressure, thermal)", "platform-architect",
           contrib=["test-runtime-harness", "certification-compliance"], tags=t)
    ed.cap("PLAT.SVC.first-party-emulation", "First-party service emulation for C-SVC (identity, entitlements, "
           "privileges, achievements)", "platform-services", tags=t)
    ed.cap_set("PLAT.SVC.emulation", name="Third-party/own-backend service emulation for C-LIVE", tags=t)
    ed.cap_set("QA.STRAT.contract-fakes", name="Policy & verification of contract test doubles (doubles pass the "
               "contract's conformance suite)", tags=t)
    ed.note(t, "check.py: boundary contracts declare a verified test double")

    t = "K-TEST-8"
    ed.cap_set("ARCH.ORG.critic-calibration", name="Critic calibration via seeded defects at every stage (G1, G2, "
               "S1–S4 canary defects in sampled changes); recall and precision tracked per critic; below-threshold "
               "critics stop counting as gates", tags=t)
    ed.cap("QA.AGENT.gate-canaries", "Every CI gate and oracle keeps a known-red case exercised periodically",
           "test-architect", contrib=["ci-cd-automation"], tags=t)

    t = "K-TEST-9"
    ed.cap("ARCH.ORG.human-audit", "Human sampling of adjudications and S3/S4 pass verdicts at a fixed rate",
           "architecture-governance", contrib=["program-orchestration"], tags=t)
    ed.note(t, "PROTOCOL.md: severity downgrades and re-raise rulings go to the adjudicator; calibration tracks "
               "precision; seeds planted by a separate agent; model/prompt-lineage diversity")

    t = "K-TEST-10 K-SEC-1 K-SEC-2 K-SEC-3 K-NET-13 K-SEC-7 K-SEC-8"
    reg = [
        # id, validating owner, parser owners, trust, mode, limits
        ("assets", "serialization-schema", ["package-formats-vfs"], "hostile-local", "harness", "size/depth/count"),
        ("packets", "network-transport", ["serialization-schema", "net-session"], "hostile-remote", "harness",
         "size/rate"),
        ("replicated-state", "replication", [], "hostile-remote", "harness", "count/depth/rate"),
        ("input-commands", "prediction-rollback", [], "hostile-remote", "harness", "rate/tick window"),
        ("peer-inputs", "prediction-rollback", [], "hostile-remote", "harness", "rate/tick window"),
        ("peer-state-hashes", "determinism-replay", [], "hostile-remote", "harness", "rate"),
        ("saves", "persistence-save", ["serialization-schema"], "hostile-local", "harness", "size/depth"),
        ("cloud-saves", "persistence-save", [], "semi-trusted-signed", "harness", "size/depth"),
        ("scripts", "scripting-runtime", [], "hostile-local", "harness", "time/memory/instructions"),
        ("mods", "modding-ugc", ["plugin-system"], "hostile-local", "harness", "size/permissions"),
        ("ugc-graphs", "modding-ugc", ["shader-system"], "hostile-remote", "harness", "node count/GPU time"),
        ("replays", "determinism-replay", [], "hostile-remote", "harness", "size/length"),
        ("remote-config", "online-services-liveops", [], "semi-trusted-signed", "harness", "size/keys"),
        ("chat-text", "online-services-liveops", ["text-fonts"], "hostile-remote", "harness", "length/rate"),
        ("fonts", "text-fonts", [], "hostile-local", "harness", "tables/glyphs"),
        ("media-decoders", "media-playback", [], "hostile-local", "harness", "resolution/duration"),
        ("decompressors", "containers-core-types", ["package-formats-vfs"], "hostile-local", "harness",
         "ratio/output size"),
        ("invites-deep-links", "platform-services", ["platform-mobile"], "hostile-remote", "harness", "length"),
        ("generated-content", "ai-behavior-perception", ["online-services-liveops"], "hostile-remote", "harness",
         "length/moderation"),
        ("editor-plugins", "plugin-system", [], "hostile-local", "harness", "permissions"),
        ("imported-dcc-files", "asset-import-interchange", [], "hostile-local", "harness", "size/depth"),
        ("voice-streams", "audio-dsp-mixing", [], "hostile-remote", "harness", "bitrate/frame size"),
        ("admin-commands", "dedicated-server", [], "semi-trusted-signed", "harness", "rate/RBAC"),
        ("automation-commands", "visual-debugging-tools", ["editor-architect"], "hostile-local", "harness",
         "dev-only/auth"),
        ("auth-tickets", "net-session", [], "hostile-remote", "harness", "size/expiry"),
        ("transaction-requests", "server-scaleout-persistence", [], "hostile-remote", "harness", "rate/idempotency"),
        ("client-integrity-reports", "anti-cheat-integrity", [], "hostile-remote", "harness", "size/rate"),
        ("user-images", "texture-streaming-vt", [], "hostile-remote", "harness", "dimensions/size"),
        ("ml-models", "ml-inference-runtime", [], "semi-trusted-signed", "harness", "size/op set"),
        ("service-responses", "online-services-liveops", ["platform-services", "async-io-storage"], "hostile-remote",
         "harness", "size/depth"),
        ("logged-untrusted-strings", "observability-telemetry", [], "hostile-remote", "harness",
         "no interpolation/lookups"),
        ("collab-session", "collaboration-version-control", [], "hostile-local", "harness", "size/rate"),
        ("shared-ddc", "content-pipeline-architect", [], "hostile-local", "harness", "content-addressed/verified"),
        ("dcc-live-link", "asset-import-interchange", [], "hostile-local", "harness", "rate/size"),
        ("procedural-asset-eval", "asset-import-interchange", [], "hostile-local", "harness",
         "sandboxed out-of-process"),
        ("launch-args", "core-runtime-architect", ["platform-mobile", "platform-desktop", "platform-console"],
         "hostile-local", "harness", "allow-listed settable-from layers"),
        ("config-layers", "core-runtime-architect", [], "semi-trusted-signed", "harness", "trust tier per layer"),
        ("patch-manifests", "packaging-release-patching", [], "semi-trusted-signed", "harness", "size/signature"),
        ("crash-uploads", "crash-diagnostics", [], "hostile-remote", "harness", "size"),
        ("telemetry-batches", "observability-telemetry", [], "hostile-remote", "harness", "size/rate"),
        ("shader-caches", "shader-system", ["rhi-core"], "hostile-local", "harness", "versioned/verified"),
        ("dev-endpoints", "hot-reload-iteration", [], "hostile-local", "harness", "dev-only/auth"),
        ("browser-bridge", "platform-web", [], "hostile-remote", "harness", "message schema"),
        ("web-sources", "research-evidence", [], "agent-input", "redteam", "provenance tiers"),
        ("external-reports", "engine-product-management", ["program-orchestration"], "agent-input", "redteam",
         "quarantined as data"),
        ("vuln-reports", "security-engineering", [], "agent-input", "redteam", "quarantined as data"),
        ("third-party-source", "build-system-toolchains", [], "agent-input", "redteam", "pinned/verified"),
        ("project-content-to-llm", "ai-assisted-authoring", [], "agent-input", "redteam", "workspace trust"),
    ]
    ed.doc["untrusted"] = {"_doc": "Untrusted-input registry (K-SEC-1). Each input class has exactly one validating "
                                   "owner; parser owners also register it; 'harness' inputs are fuzz targets owned "
                                   "next to the parser, 'redteam' inputs are agent inputs covered by the prompt-"
                                   "injection corpus (XC.SEC.agent-redteam).",
                           "inputs": [{"id": i, "validating_owner": v, "parser_owners": p, "trust": tr, "mode": mo,
                                       "limits": li} for i, v, p, tr, mo, li in reg]}
    for s in ed.doc["skill"]["skills"]:
        s.pop("untrusted_inputs", None) if not s.get("untrusted_inputs") else None
    for i, v, p, *_ in reg:
        for sid in [v] + p:
            _unt(ed, sid, i)
    ed.skill("robustness-fuzzing")["fuzz_targets"] = sorted(i for i, *_rest, mo, _l in
                                                            [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in reg]
                                                            if mo == "harness")
    ed.note(t, "data/untrusted-inputs.json registry (49 input classes); skills' untrusted_inputs and fuzz_targets "
               "derived from it; check.py validates registry ↔ skills ↔ fuzz targets")
    ed.cap("RND.TEX.runtime-decode", "Runtime image decode for player-supplied images (avatars, sprays, UGC "
           "thumbnails)", "texture-streaming-vt", contrib=["security-engineering"], tags=t)
    ed.cap("CORE.LIFE.config-trust", "Config trust tiers per layer & per-cvar settable-from allow-lists (no code "
           "loading or path cvars from command-line, intent or remote layers in shipping)", "core-runtime-architect",
           contrib=["security-engineering"], tags=t)
    _append(ed, "C-CFG", "per-layer trust tier and per-cvar settable-from allow-list.", t)
    ed.cap("XC.SEC.agent-redteam", "Prompt-injection corpus run against each agent role; agent-input registry "
           "entries", "security-engineering", "M", contrib=["program-orchestration"], tags=t)
    ed.cap("ARCH.ORG.sensitive-paths", "Sensitive write sets (registry parsers, crypto, auth, sandboxes, build & CI) "
           "require a K-SEC gate plus a second agent's approval", "program-orchestration",
           contrib=["security-engineering"], tags=t)
    ed.cap_set("XC.SEC.agent-boundary", mat="M", tags=t)
    ed.cap("ED.ARCH.automation-security", "Copilot/agent action security: capability-scoped tokens, per-command "
           "permission classes, confirmation for code-exec/destructive/network actions, workspace-trust gating",
           "editor-architect", contrib=["security-engineering"], tags=t)
    ed.cap_set("XC.SEC.genai", add_contrib=["editor-architect"], tags=t)

    t = "K-TEST-11"
    ed.cap("QA.FUNC.compat-corpus", "Governed historical-artifact corpus (saves, patch chains, replays, packages, "
           "projects, mods) loaded on every release", "functional-automation-soak",
           contrib=["serialization-schema", "persistence-save", "determinism-replay", "packaging-release-patching",
                    "modding-ugc"], tags=t)
    ed.cap("QA.FUNC.version-skew", "Client/server/content version-skew matrix across the compatibility window",
           "functional-automation-soak", contrib=["network-architect"], tags=t)

    t = "K-TEST-12"
    ed.cap("QA.AGENT.holdout", "Sealed holdout partitions of conformance/oracle suites plus gate-time seeded "
           "property & metamorphic cases", "test-architect", contrib=["program-orchestration"], tags=t)

    t = "K-TEST-13"
    c = ed.contract("C-TEST")
    ed.contract_set("C-TEST", evidence_bundle=["unit+acceptance results", "mutation score", "coverage",
                                               "fuzz hours on registered inputs", "determinism lanes",
                                               "perf gate results", "validation-layer/sanitizer runs"], tags=t)

    t = "K-TEST-14"
    ed.cap_set("QA.STRAT.content", name="Minimal unit/integration test fixtures (representative content comes from "
               "QA.REF.content)", tags=t)
    ed.cap_set("PRF.BENCH.workloads", name="Benchmark scenarios over QA.REF.content", tags=t)
    ed.cap_set("ARCH.ORG.triage", name="Failure attribution & routing policy, revert-first (bisection engine in "
               "BLD.CI.bisection)", tags=t)
    ed.cap("BLD.CI.bisection", "Single bisection engine serving functional and performance regressions",
           "ci-cd-automation", contrib=["perf-benchmarking"], tags=t)

    t = "K-TEST-15"
    ed.cap_set("QA.STRAT.flaky", name="Flaky-test management: quarantine counts as a skip under "
               "QA.AGENT.test-integrity (governed approval, owner, mandatory expiry)", tags=t)

    t = "K-TEST-17"
    for k in ed.doc["critic"]["critics"]:
        if k["id"] == "K-TOOLS":
            if "api-lifecycle-migration" not in k["scope"]:
                k["scope"].append("api-lifecycle-migration")
            for st in ("S3", "S4"):
                if st not in k["stages"]:
                    k["stages"].append(st)
    ed.skill_set("api-lifecycle-migration", writes_code=True, tags=t)
    ed.note(t, "check.py: every code-writing skill has a domain critic at S3")

    # ================================================================ SEC
    t = "K-SEC-4"
    ed.skill_add(tags=t, id="security-runtime", name="Security Runtime", tier="expert", parent="security-engineering",
                 profiles=["all"], kind="runtime", targets=["client", "headless-client", "server", "tools"],
                 workstream="quality",
                 purpose="Security-critical runtime code shared by every verifier: vetted crypto primitives and CSPRNG, "
                         "the signed-artifact envelope, trust-root store, key rotation/revocation, anti-rollback "
                         "version floors and algorithm agility.",
                 non_responsibilities=[["Security policy & threat model", "security-engineering"],
                                       ["Key custody", "security-engineering"]],
                 expertise=["applied cryptography", "code signing (TUF/Uptane class)", "constant-time code"],
                 consumes=["C-BASE", "C-TYPES", "C-PAL"])
    ed.contract_add("C-SIGN", 1, "security-runtime", "Crypto & signed artifacts",
                    "Crypto primitives and CSPRNG, signature envelope, trust roots, rotation/revocation, version floors "
                    "(anti-rollback), algorithm agility.", requires=["C-TYPES"], conformance=True, tags=t)
    ed.cap_set("CORE.TYPES.crypto", owner="security-runtime", add_contrib=["containers-core-types"], tags=t)
    ed.cap("XC.SEC.signed-artifacts", "Signed-artifact envelope, trust roots, rotation/revocation, version floors, "
           "algorithm agility", "security-runtime", contrib=["security-engineering"], tags=t)
    ed.cap("XC.SEC.pqc-signatures", "Post-quantum signature migration", "security-runtime", "M", tags=t)
    ed.doc["radar"]["entries"].append({"tech": "Post-quantum signatures", "class": "M",
                                       "capabilities": ["XC.SEC.pqc-signatures"], "owner": "security-runtime",
                                       "evidence": "NIST FIPS 204/205 (2024); deprecation track 2030–2035",
                                       "revisit": "Platform/store acceptance of PQC signatures",
                                       "fallback": "Classical signatures with algorithm agility"})
    for sid in ("package-formats-vfs", "persistence-save", "plugin-system", "modding-ugc", "online-services-liveops",
                "network-transport"):
        ed.use(sid, "C-SIGN", tags=t)
    c = ed.contract("C-TYPES")
    ed.contract_set("C-TYPES", summary=c["summary"].replace("crypto", "hashing"), tags=t)

    t = "K-SEC-9"
    ed.cap("XC.EXT.ugc-integrity", "Mod/UGC distribution integrity: package signing via C-SIGN, author identity & 2FA "
           "at the distribution boundary, update pinning/review, remote revocation/kill switch, native-code mod "
           "policy (sandboxed by default, native only by explicit player opt-in)", "modding-ugc",
           contrib=["security-engineering", "online-services-liveops", "platform-services"], tags=t)
    ed.cap_set("XC.SEC.sandbox", name="Mod / UGC sandbox policy (sandboxed by default; native mods only behind "
               "explicit opt-in, ADR)", tags=t)

    t = "K-SEC-11"
    ed.cap("XC.SEC.attestation", "Device/app attestation tokens (Play Integrity, App Attest, platform-signed tokens), "
           "server verification, graceful degradation", "anti-cheat-integrity",
           contrib=["platform-mobile", "platform-desktop", "platform-console", "platform-services"], tags=t)
    ed.cap("XC.SEC.usermode-anticheat", "User-mode & attestation-based anti-cheat posture (kernel-driver deprecation "
           "pressure, Proton/ARM)", "anti-cheat-integrity", "M", tags=t)
    ed.doc["radar"]["entries"].append({"tech": "User-mode & attestation-based anti-cheat", "class": "M",
                                       "capabilities": ["XC.SEC.usermode-anticheat"], "owner": "anti-cheat-integrity",
                                       "evidence": "Windows Resiliency Initiative (2024–2025); Proton compatibility",
                                       "revisit": "Windows kernel-access policy change",
                                       "fallback": "Middleware kernel anti-cheat where platform permits"})

    t = "K-SEC-12"
    ed.cap_set("NET.REP.interest", add_contrib=["anti-cheat-integrity"], tags=t)
    ed.cap("XC.SEC.info-hiding", "Information hiding: server-side visibility/fog culling, delayed reveal, per-netcode-"
           "model information-leak & host-trust assessment", "anti-cheat-integrity",
           contrib=["replication", "prediction-rollback"], tags=t)
    for c in ed.doc["cross"]["concerns"]:
        if c["concern"] == "network authority & replication":
            c["obligation"] = c["obligation"].rstrip(".") + "; declare what hidden state reaches clients."

    t = "K-SEC-13"
    ed.cap("CORE.TYPES.hash-dos", "Keyed hashing (SipHash class) mandated for containers keyed by untrusted data",
           "containers-core-types", contrib=["security-engineering"], tags=t)

    t = "K-SEC-14"
    ed.cap("BLD.SYS.dev-surface-exclusion", "Dev-surface manifest per skill, fitness function and binary scan proving "
           "shipping configurations contain none; allowed shipping surfaces authenticated via C-IPC",
           "build-system-toolchains", contrib=["security-engineering", "architecture-governance"], tags=t)
    for sid, surf in (("visual-debugging-tools", ["console & cheats", "automation endpoint"]),
                      ("hot-reload-iteration", ["live coding", "reload endpoint"]),
                      ("platform-architect", ["devlink"]), ("observability-telemetry", ["remote diagnostics"]),
                      ("scripting-runtime", ["script debugger (DAP)"])):
        ed.skill_set(sid, dev_surfaces=surf, tags=t)

    t = "K-SEC-15"
    for cid in ("PLAT.XR.gaze-input", "PLAT.XR.scene", "PLAT.XR.anchors", "PLAT.XR.passthrough",
                "INP.DEV.eye-tracking", "PLAT.SVC.voice-text", "XC.DET.replay-format"):
        ed.cap_set(cid, add_contrib=["privacy-data-protection"], tags=t)
    ed.cap_set("XC.SEC.data-rights", name="Data inventory with sensitivity classes (biometric, spatial, voice, "
               "minors), per-class retention, on-device-only defaults & data-subject request flow", tags=t)

    t = "K-SEC-16"
    ed.cap_set("PLAT.COMM.receipts", name="Server-side receipt/entitlement verification boundary (client only "
               "forwards receipts; grants via NET.SRV.transactions)", add_contrib=["dedicated-server",
                                                                                   "server-scaleout-persistence"],
               tags=t)

    t = "K-SEC-17"
    ed.skill_add(tags=t, id="privacy-data-protection", name="Privacy & Data Protection", tier="expert",
                 parent="security-engineering", profiles=["all"], kind="process", targets=[], workstream="quality",
                 purpose="Privacy as its own discipline: privacy engineering, data inventory and sensitivity classes, "
                         "retention, data-subject rights, consent policy for telemetry and analytics, privacy review "
                         "of every skill handling personal data.",
                 non_responsibilities=[["Consent mechanism implementation", "observability-telemetry"],
                                       ["Regulatory tracking", "certification-compliance"]],
                 expertise=["GDPR/CCPA/COPPA engineering", "data minimization", "privacy review"],
                 consumes=["C-TRUST"])
    for cid in ("XC.SEC.privacy", "XC.SEC.data-rights"):
        ed.cap_set(cid, owner="privacy-data-protection", add_contrib=["security-engineering"], tags=t)
    ed.cap("XC.SEC.privacy-review", "Privacy review of every skill handling personal data (data classes, "
           "minimization, on-device defaults)", "privacy-data-protection", tags=t)
    ed.cap("XC.SEC.childrens-data", "Children's data & age-appropriate design (COPPA, AADC, parental consent flows)",
           "privacy-data-protection", contrib=["platform-services", "certification-compliance"], tags=t)
    ed.cap_set("OBS.LOG.consent", name="Telemetry consent mechanism (policy in XC.SEC.privacy)",
               add_contrib=["privacy-data-protection"], tags=t)
    ed.cap_set("XC.SEC.vuln-response", add_contrib=["engine-product-management", "certification-compliance"],
               tags=t)
    for k in ed.doc["critic"]["critics"]:
        if k["id"] == "K-SEC" and "privacy-data-protection" not in k["scope"]:
            k["scope"].append("privacy-data-protection")

    # ================================================================ FUTURE
    t = "K-FUTURE-2"
    for cid in ("QA.AGENT.oracle-independence", "QA.AGENT.baseline-governance", "QA.AGENT.test-integrity",
                "QA.AGENT.mutation-gate", "ARCH.ORG.provenance", "ARCH.ORG.critic-calibration",
                "ARCH.ORG.adjudication"):
        ed.cap_set(cid, mat="M", tags=t)
    fb = "Mandatory human review sampling per tier (ARCH.ORG.human-gates) and frozen agent authority over oracles"
    ed.doc["radar"]["entries"] += [
        {"tech": "Validation of autonomous-agent development (test side)", "class": "M", "owner": "test-architect",
         "capabilities": ["QA.AGENT.oracle-independence", "QA.AGENT.baseline-governance", "QA.AGENT.test-integrity",
                          "QA.AGENT.mutation-gate"],
         "evidence": "docs/06 A13; reward-hacking reports in agentic coding (2025)",
         "revisit": "Measured seeded-defect escape rate below threshold across N milestones", "fallback": fb},
        {"tech": "Governance of autonomous-agent development (review side)", "class": "M",
         "owner": "architecture-governance", "capabilities": ["ARCH.ORG.critic-calibration", "ARCH.ORG.adjudication"],
         "evidence": "docs/06 A13; LLM-as-judge bias literature", "revisit": "Calibrated critic recall and precision "
         "stable across three milestones", "fallback": fb},
        {"tech": "Agent provenance & boundaries", "class": "M", "owner": "program-orchestration",
         "capabilities": ["ARCH.ORG.provenance"], "evidence": "SLSA provenance applied to agents (new)",
         "revisit": "Industry provenance standard for AI-authored code", "fallback": fb},
        {"tech": "Development-agent security boundary", "class": "M", "owner": "security-engineering",
         "capabilities": ["XC.SEC.agent-boundary", "XC.SEC.agent-redteam"],
         "evidence": "OWASP LLM01; CVE-2025-53773, CVE-2025-54135",
         "revisit": "Demonstrated robust prompt-injection defence", "fallback": fb}]
    ed.note(t, "agent-validation capabilities relabelled M with radar entries")

    t = "K-FUTURE-3 K-GAMEPLAY-19"
    ed.cap_move("GAM.AI.llm", "GAM.AI.llm-dialogue", tags=t)
    ed.cap_set("GAM.AI.llm-dialogue", name="LLM-generated barks & dialogue on non-authoritative state (via "
               "C-AIAGENT; guardrails per XC.SEC.genai; localized per UI.LOC.generated; conversational memory via "
               "C-SAVE with retention limits)", tags=t)
    ed.cap("GAM.AI.llm-decision", "Model output that changes authoritative simulation state (recorded as external "
           "input)", "ai-behavior-perception", "X", contrib=["determinism-replay"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "GAM.AI.learned" in e.get("capabilities", []):
            e["capabilities"] = ["GAM.AI.learned"]
            e["evidence"] = "GT Sophy shipped in Gran Turismo 7 (2023)"
    ed.doc["radar"]["entries"] += [
        {"tech": "LLM-generated dialogue", "class": "M", "owner": "ai-behavior-perception",
         "capabilities": ["GAM.AI.llm-dialogue"], "evidence": "Shipped 2025 titles with cloud/hybrid LLM companions",
         "revisit": "Published rating/moderation/cost postmortems", "fallback": "Authored dialogue"},
        {"tech": "LLM decisions on authoritative state", "class": "X", "owner": "ai-behavior-perception",
         "capabilities": ["GAM.AI.llm-decision"], "evidence": "Demos only",
         "revisit": "Shipped title with replay/rollback-safe model decisions", "fallback": "Authored AI"},
        {"tech": "Generated-text localization", "class": "M", "owner": "localization-i18n",
         "capabilities": ["UI.LOC.generated"], "evidence": "Follows LLM dialogue adoption",
         "revisit": "As LLM dialogue", "fallback": "Authored localized text"}]

    t = "K-FUTURE-4"
    ed.cap_set("RND.SHADER.neural", name="In-shader small-network evaluation (matrix-vector/tensor intrinsics tier; "
               "API-neutral; standalone-dispatch fallback via C-MLGPU)", mat="X", tags=t)
    ed.cap_set("RND.GI.neural-cache", mat="X", tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "RND.SHADER.neural" in e.get("capabilities", []) or "RND.GI.neural-cache" in e.get("capabilities", []):
            e["class"] = "X"
    _append(ed, "C-SHADER", "neural/tensor intrinsics are an optional tier with a mandatory standalone-dispatch "
            "fallback through C-MLGPU.", t)

    t = "K-FUTURE-5"
    ed.doc["skill"]["profiles"]["addons"]["experimental"] = "Opt-in experimental (X/S) capabilities"
    for d in ed.doc["cap"]["domains"]:
        for a in d["areas"]:
            for cap in a["caps"]:
                if cap[3] in ("X", "S"):
                    ed.cap_set(cap[0], profiles=["experimental"], tags=t)
    cfgs["aaa-experimental-client"] = {"profiles": ["std3d", "openworld", "online", "aaa", "experimental"],
                                       "target": "client", "platforms": ["pc"]}
    ed.note(t, "check.py: X/S capabilities carry exactly the 'experimental' profile; aaa-experimental-client added")

    t = "K-FUTURE-6"
    for cid, name, mat, con in [
            ("ML.RT.sequence-models", "Autoregressive/diffusion execution: KV-cache budgets, token streaming, "
             "cancellation, constrained decoding", "X", []),
            ("ML.RT.os-models", "OS-provided foundation-model APIs as a backend", "M", []),
            ("ML.RT.residency", "Model-weight residency registered as a pool in RES.MGMT.arbitration", "M",
             ["resource-streaming-architect"]),
            ("ML.RT.local-remote", "Same model interface served locally or through the C-LIVE generative boundary "
             "(routing policy, fallback)", "M", ["online-services-liveops"])]:
        ed.cap(cid, name, "ml-inference-runtime", mat, contrib=con,
               profiles=["experimental"] if mat == "X" else None, tags=t)
    _append(ed, "C-ML", "sequence sessions, streaming results, residency class, local/remote routing.", t)
    ed.doc["radar"]["entries"] += [
        {"tech": "On-device sequence/generative models", "class": "X", "owner": "ml-inference-runtime",
         "capabilities": ["ML.RT.sequence-models"], "evidence": "2025 on-device SLM demos in games",
         "revisit": "Shipped title with on-device generation within budget", "fallback": "Remote generation via C-LIVE"},
        {"tech": "OS model APIs, weight residency & local/remote routing", "class": "M", "owner": "ml-inference-runtime",
         "capabilities": ["ML.RT.os-models", "ML.RT.residency", "ML.RT.local-remote"],
         "evidence": "Windows ML GA, Apple Foundation Models, Android AICore (2025)",
         "revisit": "Shipped title using an OS model API", "fallback": "Engine-packaged models"}]
    ed.use("ml-inference-runtime", "C-RES", tags=t)

    t = "K-FUTURE-8"
    _append(ed, "C-DIALOGUE", "runtime line records (provenance = generated, transient ID, locale, moderation "
            "verdict, TTS/lip-sync-at-runtime flags, caption obligations).", t)
    _append(ed, "C-AIAGENT", "provider outputs enter simulation only as recorded external inputs (C-REPLAY external "
            "stream; replicated from authority); providers are never re-invoked on resimulate.", t)
    ed.cap("GAM.AI.local-guardrails", "On-device safety classification when no remote moderation is available",
           "ai-behavior-perception", "M", contrib=["security-engineering"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "GAM.AI.llm-dialogue" in e.get("capabilities", []):
            e["capabilities"].append("GAM.AI.local-guardrails")

    t = "K-FUTURE-10"
    _append(ed, "C-RHI", "optional tensor/matrix resource types and weight-layout conversion tier (reviewed by "
            "ml-inference-runtime before freeze).", t)

    t = "K-FUTURE-11 K-NET-19"
    ed.cap_set("NET.ARCH.meshing", mat="M", profiles=[], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "NET.ARCH.meshing" in e.get("capabilities", []):
            e["class"] = "M"
            e["owner"] = "server-scaleout-persistence"
            e["evidence"] = "Star Citizen server meshing live since late 2024; few technical postmortems"
            e["fallback"] = "Zoned/instanced servers (NET.SRV.zoning)"
    ed.note(t, "server meshing aligned to M across data, radar and docs/06 A5")

    t = "K-FUTURE-12"
    ed.cap_set("ML.RT.npu", mat="X", profiles=["experimental"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "ML.RT.npu" in e.get("capabilities", []):
            e["capabilities"].remove("ML.RT.npu")
            e["evidence"] = "ONNX Runtime/LiteRT/Core ML in shipped apps; engine NNE still beta"
    ed.doc["radar"]["entries"].append({"tech": "NPU inference backends in games", "class": "X",
                                       "owner": "ml-inference-runtime", "capabilities": ["ML.RT.npu"],
                                       "evidence": "NNAPI deprecated (Android 15); Windows ML GA 2025",
                                       "revisit": "Shipped title offloads a frame-relevant network to an NPU on two "
                                                  "platforms", "fallback": "GPU/CPU backend"})

    t = "K-FUTURE-13"
    for e in ed.doc["radar"]["entries"]:
        if e["tech"] == "Explicit multi-GPU":
            e["tech"] = "Linked/AFR multi-GPU rendering"
    ed.cap("RND.RHI.adapter-selection", "Adapter selection (high-performance vs low-power) & cross-adapter present on "
           "hybrid laptops", "rhi-core", tags=t)
    ed.cap("RND.GPU.hetero-offload", "Heterogeneous adapter offload (inference, encode, async work on the integrated GPU/NPU)",
           "gpu-platform-architect", "X", profiles=["experimental"], tags=t)
    ed.doc["radar"]["entries"].append({"tech": "Heterogeneous adapter offload", "class": "X",
                                       "owner": "gpu-platform-architect", "capabilities": ["RND.GPU.hetero-offload"],
                                       "evidence": "Vendor samples; no shipped titles",
                                       "revisit": "Two shipped titles", "fallback": "Single adapter"})

    t = "K-FUTURE-14"
    ed.cap("PLAT.XR.scene-export", "OS-composited shared-space scenes (engine exports a scene description via C-RSCENE "
           "change streams)", "xr-runtime", "M", contrib=["render-architect"], tags=t)
    ed.doc["radar"]["entries"].append({"tech": "OS-composited spatial scenes (shared space)", "class": "M",
                                       "owner": "xr-runtime", "capabilities": ["PLAT.XR.scene-export"],
                                       "evidence": "visionOS Shared Space/RealityKit; Unity PolySpatial",
                                       "revisit": "Second platform with OS-composited app scenes",
                                       "fallback": "Full/immersive space only"})

    t = "K-FUTURE-15"
    ed.skill_set("platform-web", profiles=["all"], tags=t)
    ed.cap("PLAT.WEB.std3d", "std3d-class web tier gated by C-GPUTIER (bindless, memory64)", "platform-web", "X",
           profiles=["experimental"], tags=t)
    ed.doc["radar"]["entries"].append({"tech": "std3d on the web", "class": "X", "owner": "platform-web",
                                       "capabilities": ["PLAT.WEB.std3d"], "evidence": "WebGPU subgroups (2025); "
                                       "bindless & memory64 in progress", "revisit": "WebGPU bindless + memory64 in "
                                       "two browsers", "fallback": "lite3d web tier"})

    t = "K-FUTURE-16"
    ed.cap("XC.EXT.generated-assets", "Runtime validation & cooking of player-prompted generated assets under "
           "XC.SEC.genai", "modding-ugc", "M", contrib=["asset-cook-processors", "security-engineering",
                                                        "online-services-liveops"], tags=t)
    ed.doc["radar"]["entries"] += [
        {"tech": "Player-prompted runtime asset generation", "class": "M", "owner": "modding-ugc",
         "capabilities": ["XC.EXT.generated-assets"], "evidence": "Roblox Cube 3D (2025)",
         "revisit": "Second platform shipping it", "fallback": "Offline UGC only"},
        {"tech": "Generative world models as renderer/simulator", "class": "S", "owner": "render-architect",
         "capabilities": [], "non_goal": True, "evidence": "Genie 3, Muse/WHAM (2025) research",
         "revisit": "Controllable, deterministic model at interactive rates on consumer hardware"}]
