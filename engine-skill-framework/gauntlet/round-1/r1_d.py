"""G1 round-1 revision, part D: performance, quality & security, orchestration & governance,
critics, cross-cutting obligations, seed map, radar, legacy patterns, milestones."""


def performance(ed):
    pa = "performance-architect"
    ed.contract_add("C-PERF", "P", pa, "Performance findings protocol",
                    "Finding format (hypothesis, capture, attribution, expected gain), routing as a change request to the "
                    "owning skill, time-boxed territory loans recorded in the ledger.", [], universal="all",
                    tags="K-PERF-1")
    ed.nonresp(pa, [["Optimizing subsystem code (via C-PERF findings)", "owning-skill"],
                    ["Instrumentation API", "observability-telemetry"], ["Benchmark harness", "perf-benchmarking"],
                    ["Runtime scalability machinery", "runtime-scalability"]], tags="K-PERF-1")
    for sid in ("cpu-performance", "gpu-performance", "loading-streaming-performance"):
        s = ed.skill(sid)
        s["non_responsibilities"] = [[w, "owning-skill" if o in ("engine-architect",) else o]
                                     for w, o in s["non_responsibilities"]]
    ed.nonresp_add("cpu-performance", "Changing subsystem code (findings route via C-PERF)", "owning-skill", tags="K-PERF-1")
    for cid, name, contrib, t in [
            ("PRF.METH.model", "Analytical performance & capacity model (unit costs × counts per tier/configuration, "
             "predicted scale limits, reconciliation)", ["perf-benchmarking", "network-architect", "world-architect"], "K-PERF-7"),
            ("PRF.METH.asymptotics", "Declared asymptotic cost per world-scale dimension for every runtime skill", [], "K-PERF-7 K-PERF-4"),
            ("PRF.METH.pipeline-budgets", "Production-pipeline budgets: editor startup, PIE start, registry queries, cook "
             "throughput, DDC hit rate, shader compile, build times",
             ["editor-architect", "content-pipeline-architect", "build-system-toolchains", "shader-system"], "K-PERF-9"),
            ("PRF.METH.field", "Field performance telemetry analysis & device-profile retuning",
             ["observability-telemetry", "perf-benchmarking", "runtime-scalability"], "K-PERF-17")]:
        ed.cap(cid, name, pa, contrib=contrib, tags=t)
    ed.cap_set("PRF.METH.scalability", name="Scalability policy: tier definitions & knob budgets (mechanism in "
               "runtime-scalability)", tags="K-SYSTEMS-14")
    ed.cap_set("PRF.METH.budgets", name="Budgets per hardware tier × configuration × refresh class", tags="K-PERF-15")
    pb = "perf-benchmarking"
    ed.contract_add("C-BENCH", "P", pb, "Benchmark registration",
                    "Benchmark registration, metric schema, C-BUDGET line reference, warm-up and variance rules, "
                    "required hardware tier, replay-driven runs.", [], universal="all", tags="K-PERF-10")
    for cid, name, contrib, t in [
            ("PRF.BENCH.scale-content", "Procedural synthetic stress worlds per configuration & scale dimension",
             ["procedural-generation", "functional-automation-soak", "reference-games"], "K-PERF-10"),
            ("PRF.BENCH.replay", "Replay- and flythrough-driven deterministic benchmark runs", ["determinism-replay"], "K-PERF-10"),
            ("PRF.BENCH.tools", "Tools & pipeline benchmark workloads", ["editor-architect", "content-pipeline-architect"], "K-PERF-9")]:
        ed.cap(cid, name, pb, contrib=contrib, tags=t)
    for cid, name in [("PRF.CPU.cache", "Cache & memory-access analysis and root-cause attribution"),
                      ("PRF.CPU.simd", "Vectorization audits"),
                      ("PRF.CPU.contention", "Contention & false-sharing analysis"),
                      ("PRF.CPU.hybrid", "Hybrid-core & power-aware placement analysis"),
                      ("PRF.LOAD.load-time", "Load-time analysis & root-cause attribution"),
                      ("PRF.LOAD.hitches", "Hitch & stutter analysis (PSO, streaming, GC, activation)"),
                      ("PRF.GPU.overlap", "Barrier & async-overlap analysis")]:
        ed.cap_set(cid, name=name, tags="K-PERF-1")
    ed.cap_set("PRF.CPU.compiler", name="PGO/LTO build profiles & optimization flag policy (sole owner)",
               rm_contrib=["build-system-toolchains"], tags="K-PERF-1")
    ed.cap("PRF.GPU.baselines", "Automated GPU capture & per-pass cost baselines", "gpu-performance",
           contrib=["render-graph-scheduling"], tags="K-PERF-1")
    ed.cap("PRF.LOAD.hitch-gate", "Load & hitch trace analyzers and the hitch gate", "loading-streaming-performance",
           contrib=["ci-cd-automation"], tags="K-PERF-1")
    ed.cap("PRF.LOAD.editor", "Editor startup, asset-open, PIE-start & large-world viewport budgets & analysis",
           "loading-streaming-performance", contrib=["editor-architect"], tags="K-TOOLS-7")
    ed.cap_set("PRF.LOAD.hitches", add_contrib=["physics-architect", "world-architect"], tags="K-SIM-8 K-PERF-5")
    ed.skill_add(id="memory-performance", name="Memory Performance", tier="expert", parent=pa, profiles=["all"],
                 kind="process", targets=[], workstream="performance",
                 purpose="Memory as its own performance discipline: whole-process CPU+GPU+UMA footprint analysis per "
                         "tier, snapshot capture and diffing, content-level attribution per asset/cell/feature, "
                         "transition peak analysis, fragmentation over time; reviewer for the memory-usage obligation.",
                 non_responsibilities=[["Allocator mechanisms", "memory-allocators"], ["Budget numbers", pa]],
                 expertise=["memory profiling (PIX, Razor-class, Memory Insights)", "fragmentation analysis", "console memory"],
                 tags="K-PERF-11")
    ed.area("PRF.MEM", "Memory performance", tags="K-PERF-11")
    for cid, name, contrib in [("PRF.MEM.footprint", "Whole-process CPU+GPU+UMA footprint analysis per tier", ["memory-allocators"]),
                               ("PRF.MEM.snapshots", "Memory snapshot capture & diff tooling", ["observability-telemetry"]),
                               ("PRF.MEM.attribution", "Content-level memory attribution per asset, cell & feature", ["content-pipeline-architect"]),
                               ("PRF.MEM.peaks", "Transition peak analysis (travel, cutscene preload, cell churn)", ["resource-streaming-architect"])]:
        ed.cap(cid, name, "memory-performance", contrib=contrib, tags="K-PERF-11")
    ob = "observability-telemetry"
    ed.cap("OBS.LOG.hw-counters", "Programmatic CPU PMU & GPU hardware-counter capture attributed to zones and passes", ob,
           contrib=["rhi-core", "gpu-performance", "cpu-performance"], tags="K-PERF-18")
    ed.cap("OBS.LOG.trace-analysis", "Engine-aware trace analysis & profiler UI (task graph, phases, loading, memory, "
           "render-graph passes)", ob,
           contrib=["job-system-task-graph", "resource-streaming-architect", "memory-allocators", "render-graph-scheduling"],
           tags="K-TOOLS-10")
    ed.cap("OBS.LOG.analytics", "Gameplay analytics event schema, taxonomy & privacy classes; analytics-SDK boundary", ob,
           contrib=["security-engineering", "online-services-liveops"], tags="K-PROD-6 K-COMPLETE-22")
    ed.cap_set("OBS.LOG.telemetry", name="Development & engineering telemetry pipeline", tags="K-PROD-6")


def quality_security(ed):
    ta = "test-architect"
    ed.contract_set("C-TEST", tags="K-QUALITY-1 K-QUALITY-6",
                    summary="Required test kinds per skill, test determinism, coverage & mutation thresholds, the "
                            "evidence bundle an implementer hands to S3/S4 critics, oracle independence, conformance "
                            "suites owned by contract owners with consumer-driven additions.")
    ed.area("QA.AGENT", "Validation of agent-produced work", tags="K-QUALITY-1")
    for cid, name, contrib in [
            ("QA.AGENT.oracle-independence", "Acceptance tests & oracles authored or approved by an agent other than the "
             "implementer", ["program-orchestration"]),
            ("QA.AGENT.baseline-governance", "Governed changes to goldens, tolerances, perf thresholds, hashes & corpora",
             ["render-validation", "perf-benchmarking"]),
            ("QA.AGENT.test-integrity", "Detection of weakened tests (deleted/skipped cases, loosened tolerances, "
             "assert-free tests, input special-casing) as a merge gate", ["ci-cd-automation"]),
            ("QA.AGENT.mutation-gate", "Mutation-score thresholds per skill tier as part of the definition of done", [])]:
        ed.cap(cid, name, ta, contrib=contrib, tags="K-QUALITY-1")
    for cid, name, contrib, t in [
            ("QA.STRAT.oracles", "Oracle taxonomy & policy (analytic, reference, metamorphic, differential, golden)", [], "K-QUALITY-5"),
            ("QA.STRAT.integration", "Cross-skill integration suites & per-configuration build/boot/test matrix",
             ["ci-cd-automation", "developer-experience-docs"], "K-QUALITY-7"),
            ("QA.STRAT.release-criteria", "Ship/launch gate (crash-free rate, perf gates, cert pre-checks, known issues)",
             ["reference-games"], "K-PROD-7"),
            ("QA.STRAT.contract-fakes", "Contract-first fakes/mocks so consumers start before providers finish",
             ["program-orchestration"], "K-PROD-1")]:
        ed.cap(cid, name, ta, contrib=contrib, tags=t)
    ed.cap_set("QA.STRAT.contracts", name="Contract-test framework & consumer-driven test policy", tags="K-QUALITY-6")
    ed.cap_set("XC.DX.samples", name="Teaching sample projects (contributes to integration suites)", tags="K-QUALITY-7 K-PROD-4")
    fa = "functional-automation-soak"
    for cid, name, contrib, mat, t in [
            ("QA.FUNC.editor", "Editor & tool automation, regression & soak testing", ["editor-ui-framework"], "E", "K-TOOLS-7"),
            ("QA.FUNC.agent-exploration", "RL/LLM exploratory test agents", [], "M", "K-FUTURE-12"),
            ("QA.FUNC.bug-capture", "In-game bug reporting with repro capture & tracker integration",
             ["crash-diagnostics", "observability-telemetry", "determinism-replay"], "E", "K-COMPLETE-11 K-PROD-6"),
            ("QA.FUNC.playtest", "Playtest capture, heatmaps & UX-research instrumentation", ["observability-telemetry"], "E", "K-COMPLETE-11")]:
        ed.cap(cid, name, fa, mat=mat, contrib=contrib, tags=t)
    ed.skill_add(id="simulation-validation", name="Simulation & Systems Validation", tier="expert", parent=ta,
                 profiles=["all"], kind="process", targets=[], workstream="quality",
                 purpose="Runs the objective validation that domain owners define for simulation-class systems: physics "
                         "stability and reference suites, simulation golden traces, animation error suites, audio "
                         "offline-render suites, and deterministic network simulation for prediction/replication "
                         "correctness, mirroring what render-validation does for rendering.",
                 non_responsibilities=[["Defining each domain's oracles", "owning-skill"],
                                       ["Determinism matrix definition", "determinism-replay"]],
                 expertise=["simulation testing", "deterministic simulation testing", "numerical error metrics"],
                 tags="K-SIM-14 K-QUALITY-5")
    ed.area("QA.SIM", "Simulation & systems validation", tags="K-SIM-14")
    for cid, name, contrib in [("QA.SIM.stability-suite", "Physics stability regression suite (stacking, joints, mass ratios, CCD)", ["rigid-body-dynamics", "physics-2d"]),
                               ("QA.SIM.golden-traces", "Simulation golden-trace comparison", ["determinism-replay"]),
                               ("QA.SIM.netsim", "Deterministic network simulation under link conditions", ["prediction-rollback", "replication"]),
                               ("QA.SIM.animation", "Animation error suites (compression, retarget, IK)", ["animation-architect"]),
                               ("QA.SIM.audio", "Audio offline-render, loudness & glitch suites", ["audio-architect"])]:
        ed.cap(cid, name, "simulation-validation", contrib=contrib, tags="K-SIM-14 K-QUALITY-5")
    rf = "robustness-fuzzing"
    ed.skill(rf)["fuzz_targets"] = ["assets", "packets", "saves", "scripts", "mods", "replays", "remote-config", "chat-text",
                                    "fonts", "media-decoders", "decompressors", "cloud-saves", "invites-deep-links",
                                    "ugc-graphs", "generated-content", "editor-plugins", "imported-dcc-files"]
    ed.cap_set("QA.ROBUST.fuzzing", name="Fuzzing of every registered untrusted input (see fuzz_targets)", tags="K-QUALITY-11")
    untrusted = {"replication": ["packets"], "network-transport": ["packets"], "persistence-save": ["saves", "cloud-saves"],
                 "scripting-runtime": ["scripts"], "modding-ugc": ["mods", "ugc-graphs"], "determinism-replay": ["replays"],
                 "online-services-liveops": ["remote-config", "chat-text", "generated-content"],
                 "text-fonts": ["fonts", "chat-text"], "media-playback": ["media-decoders"],
                 "package-formats-vfs": ["decompressors", "assets"], "platform-services": ["invites-deep-links"],
                 "shader-system": ["ugc-graphs"], "plugin-system": ["editor-plugins"],
                 "asset-import-interchange": ["imported-dcc-files"], "ai-behavior-perception": ["generated-content"],
                 "serialization-schema": ["assets", "saves", "packets"]}
    for sid, inputs in untrusted.items():
        ed.skill(sid)["untrusted_inputs"] = inputs
    ed.note("K-QUALITY-11", "untrusted_inputs registered per skill; fuzz_targets on robustness-fuzzing")
    se = "security-engineering"
    for cid, name, contrib, mat, t in [
            ("XC.SEC.memory-safety", "Memory-safety posture: hardened library modes, shipping bounds checks, memory-safe "
             "language for untrusted-input parsers, MTE/PAC", ["core-runtime-architect"], "M", "K-SYSTEMS-11 K-FUTURE-14"),
            ("XC.SEC.hardening", "Exploit-mitigation & hardened-build matrix per platform (CFI, shadow stacks, allocator hardening)",
             ["build-system-toolchains", "memory-allocators"], "E", "K-QUALITY-13"),
            ("XC.SEC.crypto-policy", "Cryptography & TLS/certificate policy", ["containers-core-types"], "E", "K-COMPLETE-3"),
            ("XC.SEC.vuln-response", "Vulnerability intake, disclosure, severity SLAs & patch path to shipped titles",
             ["packaging-release-patching", "api-lifecycle-migration", "build-release-architect"], "E", "K-QUALITY-12"),
            ("XC.SEC.incident", "Live incident-response runbooks for online titles",
             ["online-services-liveops", "anti-cheat-integrity"], "E", "K-QUALITY-12"),
            ("XC.SEC.dev-trust", "Project/workspace trust, plugin signing & permissions, sandboxed import of untrusted "
             "source assets", ["plugin-system", "editor-architect", "asset-import-interchange"], "E", "K-QUALITY-14"),
            ("XC.SEC.agent-boundary", "Development-agent capability scoping, sandboxing, egress & prompt-injection threat model",
             ["program-orchestration", "ci-cd-automation"], "E", "K-QUALITY-15"),
            ("XC.SEC.key-custody", "Platform signing keys, devkit credentials, release-signing ceremony; no agent-held keys",
             ["packaging-release-patching", "platform-console"], "E", "K-QUALITY-15"),
            ("XC.SEC.genai", "Generative-feature threat model: prompt injection, output handling, PII, cost DoS",
             ["ai-behavior-perception", "ai-assisted-authoring", "online-services-liveops"], "M", "K-FUTURE-5 K-QUALITY-16"),
            ("XC.SEC.data-rights", "Data inventory, retention & data-subject request flow",
             ["certification-compliance", "observability-telemetry", "crash-diagnostics"], "E", "K-QUALITY-18"),
            ("XC.SEC.testing", "Pen testing, red-teaming, secret scanning & shipping-build hardening audit",
             ["robustness-fuzzing", "ci-cd-automation", "visual-debugging-tools"], "E", "K-QUALITY-20")]:
        ed.cap(cid, name, se, mat=mat, contrib=contrib, tags=t)
    ed.cap("XC.EXT.plugin-trust", "Plugin signature & permission manifest fields", "plugin-system", tags="K-QUALITY-14")
    ed.cap("OBS.CRASH.privacy", "Client-side redaction of secrets/PII in dumps & logs, annotation allow-lists, retention",
           "crash-diagnostics", contrib=["security-engineering", "observability-telemetry"], tags="K-QUALITY-18")
    ed.cap_set("OBS.CRASH.gpu", name="GPU crash dump ingestion & triage", tags="K-RENDER-20")
    ed.cap("LIVE.feedback" if False else "OBS.CRASH.feedback", "In-game bug/feedback capture boundary for players",
           "crash-diagnostics", contrib=["functional-automation-soak"], tags="K-PROD-6")


def orchestration(ed):
    po = "program-orchestration"
    ed.contract_set("C-ORCH", tags="K-PROD-1 K-PROD-2 K-PROD-14 K-QUALITY-1 K-QUALITY-7 K-QUALITY-15 K-PLATFORM-3",
                    summary="Ownership ledger with access classes; write sets by module convention (src/<skill-id>/, "
                            "tools/<skill-id>/; tests owned by the test-owning skill); shared-file protocol; contributor "
                            "semantics (review + change request, never direct writes); change requests; integration "
                            "order and milestones; human-gate tasks; failure triage; per-change provenance; critic gates "
                            "with calibration and independent adjudication.")
    for cid, name, contrib, t in [
            ("ARCH.ORG.bootstrap", "Walking-skeleton definition & bring-up order", ["engine-architect", "platform-architect", "ci-cd-automation"], "K-PROD-1"),
            ("ARCH.ORG.milestones", "Milestone ladder with per-milestone skill set, contract maturity & exit criteria (data/milestones.json)", ["reference-games"], "K-PROD-1"),
            ("ARCH.ORG.write-sets", "Module/file write-set convention & shared-file protocol", ["build-system-toolchains"], "K-PROD-2"),
            ("ARCH.ORG.staffing", "Agent staffing tiers: co-hosting of skills per organization scale (by workstream)", [], "K-PROD-8"),
            ("ARCH.ORG.escalation", "Escalation tiers & decision SLAs; delegated arbitration inside a lead's subtree", ["engine-architect"], "K-ARCH-7 K-PROD-13"),
            ("ARCH.ORG.human-gates", "Register of decisions requiring human authorization (contracts, spend, NDA access, submissions, legal sign-off)",
             ["engine-architect", "certification-compliance"], "K-PROD-14"),
            ("ARCH.ORG.risk", "Program risk register & risk-driven milestone ordering", ["research-evidence"], "K-PROD-15"),
            ("ARCH.ORG.triage", "Failure attribution, bisection, routing to owners, revert-first policy", ["ci-cd-automation", "perf-benchmarking"], "K-QUALITY-7"),
            ("ARCH.ORG.critic-calibration", "Critic calibration via seeded defects; rounds count only above recall threshold", ["test-architect"], "K-QUALITY-4"),
            ("ARCH.ORG.adjudication", "Independent adjudication of rejected and partially accepted findings", [], "K-QUALITY-4"),
            ("ARCH.ORG.provenance", "Per-change agent/model/task attestation in the ledger", ["security-engineering"], "K-QUALITY-15")]:
        ed.cap(cid, name, po, contrib=contrib, tags=t)
    ag = "architecture-governance"
    ed.cap("ARCH.GOV.process-tiers", "Governance weight per organization tier (which ADR/CR/critic stages are mandatory)", ag,
           tags="K-PROD-8")
    ed.cap_set("ARCH.GOV.anti-legacy", name="Anti-legacy review against the flagged-pattern catalogue (data/legacy-patterns.json)",
               tags="K-LEGACY-16")
    ed.cap_set("ARCH.GOV.radar", name="Technology radar (data/radar.json): maturity, owners, revisit triggers, non-goals",
               tags="K-FUTURE-13")
    ea = "engine-architect"
    ed.cap("ARCH.STRUCT.registration", "Declarative self-registration for phases, render features, services, cvars, codegen "
           "inputs (no central tables)", ea, contrib=["frame-orchestration", "render-architect"], tags="K-ARCH-16")
    ed.cap("ARCH.STRUCT.binding", "Contract binding policy: implementation chosen at compile/link/load time; batch-granular "
           "interfaces; no per-item virtual dispatch across contracts on hot paths", ea,
           contrib=["cpu-performance", "architecture-governance"], tags="K-LEGACY-9")
    ed.cap_set("ARCH.REQ.non-goals", name="Capability & non-goal register (radar non-goals)", tags="K-FUTURE-13")
    ed.skill_add(id="engine-product-management", name="Engine Product Management", tier="orchestrator", parent=ea,
                 profiles=["all"], kind="process", targets=[], workstream="governance",
                 purpose="The engine as a product for game teams: roadmap and prioritization across game-team "
                         "requirements, bug and feature intake with triage SLAs, release notes and upgrade guides, the "
                         "customer-project corpus that validates each engine release, and the engine licensing model.",
                 non_responsibilities=[["Architecture decisions", ea], ["Work scheduling", po],
                                       ["Engine release mechanics", "build-release-architect"]],
                 expertise=["product management", "developer relations", "release management"], tags="K-PROD-3")
    ed.contract_add("C-PROD", "P", "engine-product-management", "Engine roadmap & intake",
                    "Roadmap priorities consumed by work decomposition, intake/triage SLAs, release-note obligations.", [],
                    tags="K-PROD-3")
    ed.area("ARCH.PROD", "Engine product management", tags="K-PROD-3")
    for cid, name, contrib in [("ARCH.PROD.roadmap", "Roadmap & prioritization across game-team requirements", []),
                               ("ARCH.PROD.intake", "Game-team bug & feature intake and triage SLAs", []),
                               ("ARCH.PROD.release-notes", "Release notes, changelogs & upgrade guides", ["developer-experience-docs"]),
                               ("ARCH.PROD.customer-corpus", "Customer/reference project corpus validating each release",
                                ["api-lifecycle-migration", "functional-automation-soak"]),
                               ("ARCH.PROD.licensing-model", "Engine licensing & terms model for game teams", [])]:
        ed.cap(cid, name, "engine-product-management", contrib=contrib, tags="K-PROD-3")
    br = "build-release-architect"
    ed.contract_add("C-RELEASE", "P", br, "Release model",
                    "Branch model, release trains, version identifiers, client/server/content compatibility keys, LTS "
                    "and hotfix streams.", [], tags="K-ARCH-13")
    for cid, name, contrib, t in [
            ("BLD.REL.archival", "Shipped-build archival & long-term rebuildability", ["build-system-toolchains", "platform-console", "crash-diagnostics"], "K-PROD-7"),
            ("BLD.CI.title-branching", "Title release-branch stabilization, content lock & hotfix streams", [], "K-PROD-7"),
            ("BLD.CI.backports", "LTS backport/hotfix streams incl. security backports", ["api-lifecycle-migration", "security-engineering"], "K-PROD-3 K-QUALITY-12")]:
        ed.cap(cid, name, br, contrib=contrib, tags=t)
    ed.nonresp("gameplay-architect", ed.skill("gameplay-architect")["non_responsibilities"], tags="")
    ed.nonresp("cpu-performance", [[w, "owning-skill" if w.startswith("Owning subsystem") else o]
                                   for w, o in ed.skill("cpu-performance")["non_responsibilities"]], tags="K-ARCH-20")
    ed.nonresp("render-architect", ed.skill("render-architect")["non_responsibilities"], tags="")
    ed.nonresp("ml-inference-runtime", ed.skill("ml-inference-runtime")["non_responsibilities"], tags="K-ARCH-20")
    # conformance flag on every code contract
    for c in ed.doc["contract"]["contracts"]:
        if c["layer"] != "P":
            c["conformance"] = True
    ed.note("K-QUALITY-6", "every code contract carries conformance=true: owner ships a conformance suite; consumers add "
                           "consumer-driven tests")


def critics(ed):
    cr = ed.doc["critic"]["critics"]
    by = {c["id"]: c for c in cr}
    q = by.pop("K-QUALITY")
    cr.remove(q)
    cr.append({"id": "K-TEST", "name": "Testing & Validation Critic",
               "mandate": "Validation, oracles, determinism and concurrency testing, agent-output integrity: can an "
                          "independent critic objectively decide correctness?",
               "checks": ["each skill has objective validation with an independent oracle",
                          "tests cannot be weakened silently", "determinism & concurrency testable via seams",
                          "evidence bundle defined for S3/S4"],
               "scope": ["all", "subtree:test-architect", "subtree:performance-architect"],
               "stages": ["G1", "G2", "S1", "S2", "S3", "S4"]})
    cr.append({"id": "K-SEC", "name": "Security Critic",
               "mandate": "Threat model, trust boundaries, memory safety, supply chain, privacy, incident response — "
                          "reviewed at design time as well as in code.",
               "checks": ["every untrusted input has a validating owner and a fuzz target", "trust boundaries explicit",
                          "hardening & key custody", "privacy of telemetry, crash and player data"],
               "scope": ["all", "subtree:security-engineering", "network-transport", "scripting-runtime", "modding-ugc",
                         "plugin-system", "serialization-schema", "package-formats-vfs", "persistence-save",
                         "platform-services", "online-services-liveops", "packaging-release-patching", "ci-cd-automation",
                         "build-system-toolchains", "observability-telemetry", "crash-diagnostics", "editor-architect",
                         "ai-assisted-authoring", "ai-behavior-perception", "dedicated-server", "asset-import-interchange"],
               "stages": ["G1", "G2", "S1", "S2", "S3", "S4"]})
    by = {c["id"]: c for c in cr}
    add_scope = {
        "K-RENDER": ["subtree:gpu-platform-architect", "media-playback", "voxel-worlds", "platform-console"],
        "K-SYSTEMS": ["subtree:gpu-platform-architect", "runtime-scalability", "media-playback"],
        "K-SIM": ["character-movement", "subtree:physics-architect", "simulation-validation", "voxel-worlds"],
        "K-NET": ["character-movement", "online-services-liveops", "narrative-dialogue"],
        "K-TOOLS": ["owns-area:TOOL", "kind:tool", "subtree:editor-architect"],
        "K-PLATFORM": ["subtree:platform-architect", "rhi-d3d12", "rhi-vulkan", "rhi-metal", "rhi-webgpu"],
        "K-PERF": ["runtime-scalability"],
        "K-PROD": ["engine-product-management", "reference-games"],
        "K-GAMEPLAY": ["subtree:gameplay-architect", "cinematics-sequencer"],
    }
    for k, sel in add_scope.items():
        for x in sel:
            if x not in by[k]["scope"]:
                by[k]["scope"].append(x)
    for k, st in {"K-GAMEPLAY": ["S3"], "K-PLATFORM": ["S3"], "K-SYSTEMS": ["S4"], "K-LEGACY": ["S4"]}.items():
        for s in st:
            if s not in by[k]["stages"]:
                by[k]["stages"].append(s)
    by["K-LEGACY"]["checks"] = ["each pattern in data/legacy-patterns.json absent or justified by an ADR"]
    ed.note("K-QUALITY-2 K-QUALITY-3 K-TOOLS-20 K-LEGACY-16", "critics: K-QUALITY split into K-TEST and K-SEC; S3/S4 "
            "coverage added; K-TOOLS scope covers every owner of a TOOL area; scopes extended to new skills")


def crosscutting(ed):
    cc = ed.doc["cross"]["concerns"]
    for c in cc:
        if c["concern"] == "memory usage":
            c["owner"] = "memory-performance"
            c["obligation"] = "Declare allocation strategy, memory tags, peak/steady budgets and OOM behavior (mechanisms by memory-allocators)."
        if c["concern"] == "concurrency":
            c["obligation"] = "Declare shared state and synchronization; follow thread-safety annotation conventions."
        if c["concern"] == "scalability":
            c["obligation"] = ("Declare behavior from the smallest to the largest configuration, scaling knobs, unit costs "
                               "and asymptotic class per world-scale dimension; spatial replicas update in O(changes).")
    cc += [
        {"concern": "thread placement", "owner": "job-system-task-graph",
         "obligation": "Declare frame-phase placement, dedicated threads (via the thread inventory) and OS-thread affinity needs."},
        {"concern": "network authority & replication", "owner": "network-architect",
         "obligation": "Declare replicated state, authority, prediction/rollback participation, cosmetic-vs-simulated split and server-target behavior."},
        {"concern": "testability seams", "owner": "test-architect",
         "obligation": "Declare the test seam each external dependency uses (null device, fake backend, injectable clock, service emulator)."},
        {"concern": "untrusted input", "owner": "security-engineering",
         "obligation": "Register every untrusted input (untrusted_inputs) with a validating owner and a fuzz target."},
        {"concern": "agent operability", "owner": "editor-architect",
         "obligation": "Expose debug state and controls through the agent/automation API with structured results."},
        {"concern": "external requirements", "owner": "certification-compliance",
         "obligation": "Satisfy the entries of the C-CERT register mapped to your capabilities."},
        {"concern": "authoring path", "owner": "editor-architect",
         "obligation": "Every user-facing runtime feature has tool logic in a <DOMAIN>.TOOL capability owned by the domain skill, hosted via C-EDCMD/C-EDHOST."}]
    for c in cc:
        if c["concern"] == "tooling":
            c["obligation"] = "Declare authoring path, inspectors and editor integration; tool logic is domain-owned, the editor provides the host."
    ed.note("K-PERF-4 K-PERF-7 K-PERF-11 K-SYSTEMS-4 K-NET-5 K-QUALITY-10 K-QUALITY-11 K-FUTURE-12 K-PLATFORM-9 K-TOOLS-1",
            "cross-cutting obligations extended and re-owned")


def seed(ed):
    ed.doc["seed"]["discovered_domains"] = {
        "_doc": "Domains found by critics beyond the brief's list; kept here so their coverage is machine-checked.",
        "video playback": ["RND.MEDIA.decode"],
        "monetization boundaries": ["PLAT.COMM.iap", "PLAT.COMM.ads"],
        "parental controls & privileges": ["PLAT.SVC.privileges"],
        "social graph & invites": ["PLAT.SVC.social"],
        "voice & text chat": ["PLAT.SVC.voice-text", "NET.TRANS.voice", "UI.A11Y.comms"],
        "spectating & kill-cams": ["NET.REP.spectator", "NET.REP.killcam"],
        "server persistence": ["NET.SRV.persistence"],
        "character movement": ["GAM.MOVE.modes", "GAM.MOVE.networked"],
        "dialogue & narrative": ["GAM.NARR.lines", "GAM.NARR.branching"],
        "designer data & balancing": ["GAM.DATA.tables", "GAM.DATA.hotfix"],
        "voxel & buildable worlds": ["WLD.VOX.storage", "GAM.SYS.building"],
        "planetary & geospatial worlds": ["WLD.MODEL.planetary", "CNT.IMP.geospatial"],
        "flight & orbital vehicles": ["PHY.CTRL.aero", "PHY.CTRL.orbital"],
        "force feedback & specialty controllers": ["INP.DEV.force-feedback", "INP.DEV.specialty"],
        "stylized rendering": ["RND.MAT.custom-lighting", "RND.POST.stylized"],
        "gaussian splatting": ["RND.GEO.splats", "CNT.IMP.splats"],
        "mixed reality": ["PLAT.XR.passthrough", "PLAT.XR.anchors"],
        "live operations": ["PLAT.LIVE.events", "PLAT.LIVE.experiments", "BLD.REL.staged-rollout"],
        "end of service": ["BLD.REL.end-of-service"],
        "engine as a product": ["ARCH.PROD.roadmap", "ARCH.PROD.intake"],
        "agent operability": ["ED.ARCH.agent-api"],
        "validation of agent output": ["QA.AGENT.oracle-independence", "QA.AGENT.test-integrity"],
        "vulnerability response": ["XC.SEC.vuln-response"],
        "web target": ["PLAT.WEB.runtime"],
        "NDA platform segregation": ["PLAT.PAL.confidential-extensions"],
        "memory performance": ["PRF.MEM.footprint"],
        "physics tooling": ["PHY.TOOL.physics-asset", "PHY.TOOL.visual-debugger"],
        "network debugging": ["NET.DBG.profiler", "NET.DBG.inspect"],
        "player settings": ["GAM.SAVE.settings"],
        "rhythm/latency calibration": ["AUD.ARCH.clock", "INP.ACT.calibration"]}
    ed.note("K-COMPLETE-*", "seed-map: discovered_domains section makes critic-found domains machine-checked")


def radar(ed):
    E = []

    def r(tech, cls, caps, owner, evidence, revisit, fallback=None, non_goal=False):
        e = {"tech": tech, "class": cls, "capabilities": caps, "owner": owner, "evidence": evidence, "revisit": revisit}
        if fallback:
            e["fallback"] = fallback
        if non_goal:
            e["non_goal"] = True
        E.append(e)
    r("Cloud game streaming targets", "M", ["PLAT.PAL.cloud-streaming"], "platform-architect", "Shipping services (GeForce NOW, xCloud) — platform docs", "Second streaming platform requiring engine-side encode/latency hooks", "Treat as a PC target")
    r("Cloud-hybrid compute (split client/cloud simulation)", "X", ["PLAT.PAL.cloud-hybrid"], "platform-architect", "Crackdown 3 cloud destruction (2019) — limited", "Two shipped titles publish latency/cost postmortems", "Local simulation only")
    r("ECS relationships", "M", ["CORE.ECS.relationships"], "ecs-runtime", "Flecs relationships; Bevy relations work", "Benchmarks on engine entity mixes show query cost acceptable", "Component references + explicit indices")
    r("C++26 static reflection", "M", ["CORE.REFL.generation"], "reflection-metadata", "P2996 adopted for C++26", "C++26 reflection available on every platform compiler", "Code generation")
    r("Memory-safe language components", "M", ["CORE.LIFE.interop", "XC.SEC.memory-safety"], "core-runtime-architect", "Android Rust adoption data; CISA/NSA roadmap guidance", "Console toolchain support for chosen language", "Hardened C++ subset + fuzzing")
    r("OpenUSD as interchange backbone", "M", ["CNT.IMP.usd"], "asset-import-interchange", "AOUSD Core Spec; DCC adoption", "Core spec 1.0 stable & DCC coverage of needed schemas", "glTF/FBX import")
    r("MaterialX / OpenPBR interchange & model", "M", ["CNT.IMP.materialx", "RND.MAT.openpbr"], "material-system", "OpenPBR 1.0 (ASWF 2024); UE Substrate production in 5.7", "Real-time OpenPBR evaluation cost within tier budgets", "Layered PBR model")
    r("Remote/CDN content streaming at runtime", "M", ["RES.IO.remote"], "async-io-storage", "Microsoft Flight Simulator, Roblox", "Offline & cache policy validated on target platforms", "Install-time content only")
    r("Planetary & geospatial worlds", "M", ["WLD.MODEL.planetary", "WLD.ENV.terrain-planetary", "CNT.IMP.geospatial"], "world-architect", "MSFS; Cesium/3D Tiles integrations", "A reference game requires planet scale", "Planar partitioned worlds")
    r("ML-generated content in PCG", "X", ["WLD.PCG.ml"], "procedural-generation", "Research & tool demos", "Deterministic, licensable models with provenance", "Rule-based PCG")
    r("Work graphs & mesh nodes", "X", ["RND.GRAPH.work-graphs", "RND.GEO.mesh-nodes"], "render-graph-scheduling", "D3D12 Work Graphs 1.0 (2024); vendor samples; no shipped titles", "Support on ≥2 console/desktop APIs and one shipped-title postmortem", "Indirect / device-generated commands")
    r("Neural materials", "X", ["RND.MAT.neural"], "material-system", "Zeltner et al., SIGGRAPH 2024", "Cross-vendor cooperative-vector support + shipped evidence", "Layered analytic BRDF")
    r("Cluster/virtualized geometry refinements (deforming LOD, displacement)", "M", ["RND.LOD.deforming", "RND.LOD.displacement"], "virtualized-geometry-lod", "UE 5.4+ Nanite skinning/tessellation", "Production use at target budgets", "Discrete LOD for deforming meshes")
    r("Sampler-feedback streaming", "M", ["RND.TEX.feedback"], "texture-streaming-vt", "D3D12 sampler feedback; SFS samples", "Hardware coverage across target tiers", "Mip streaming")
    r("Neural texture compression", "X", ["RND.TEX.ntc"], "texture-streaming-vt", "Vaidyanathan et al. 2023; RTX NTC SDK beta", "Shipped titles + non-preview cooperative-vector support", "BCn/ASTC; transcode-on-load variant")
    r("Stochastic many-light sampling", "M", ["RND.LIGHT.stochastic"], "direct-lighting-shadows", "ReSTIR DI (2020); MegaLights (SIGGRAPH 2025)", "Denoiser quality within tier budgets", "Clustered lighting + shadow maps")
    r("ReSTIR GI & path-traced GI", "M", ["RND.GI.restir", "RND.PT.realtime"], "global-illumination", "Ouyang et al. HPG 2021; shipped PT modes", "RT tier performance on console-class hardware", "Probe/radiance-cache GI")
    r("Neural radiance caching", "M", ["RND.GI.neural-cache"], "global-illumination", "Müller et al. 2021; RTX Remix titles", "Cross-vendor tensor support & budget fit", "Radiance cache")
    r("Advanced RT hardware features (OMM, SER, cluster BLAS)", "M", ["RND.RT.omm", "RND.RT.ser", "RND.RT.cluster-blas"], "ray-tracing-infrastructure", "DXR 1.2 / Vulkan extensions; vendor SDKs", "Availability on ≥2 vendors", "Standard BLAS/TLAS")
    r("ML denoising & ray reconstruction", "M", ["RND.RECON.denoise"], "reconstruction-upscaling", "DLSS RR; NRD", "Vendor-neutral path or per-vendor integration cost acceptable", "Spatiotemporal denoisers")
    r("Strand hair simulation & rendering", "M", ["RND.CHAR.hair", "PHY.SOFT.hair-sim"], "character-rendering", "UE Groom; Frostbite strands", "Budget fit at target character counts", "Hair cards")
    r("Foveated rendering implementation", "M", ["RND.RECON.foveation"], "reconstruction-upscaling", "Quest ETFR; VRS/FDM", "Eye-tracking availability on target headsets", "Fixed foveation")
    r("ACES 2.0 output transforms", "M", ["RND.POST.aces2"], "post-color-hdr", "AMPAS ACES 2.0 release", "Game-industry adoption & performance", "Current display transforms")
    r("Heterogeneous sparse volumes", "M", ["RND.VFX.volumes"], "vfx-particles", "UE Heterogeneous Volumes; NanoVDB", "Budget fit on std3d tier", "Particle/sprite volumetrics")
    r("Slang shading language", "M", ["RND.SHADER.slang"], "shader-system", "Khronos-hosted since 2024; production users", "Toolchain maturity on all backends incl. consoles", "HLSL via DXC")
    r("In-shader neural evaluation & differentiable shaders", "M", ["RND.SHADER.neural", "RND.SHADER.autodiff"], "shader-system", "SM 6.9 cooperative vectors (preview); Slang autodiff", "Non-preview cross-vendor support", "Standalone inference dispatch")
    r("WebGPU backend & web 3D", "M", ["RND.RHI.webgpu", "PLAT.WEB.webgpu-target"], "rhi-webgpu", "WebGPU in Chrome/Edge/Safari/Firefox (2023–2025)", "Bindless/timestamp features in WebGPU", "WebGL-class 2D only")
    r("Gaussian splatting & radiance fields", "X", ["RND.GEO.splats", "RND.GEO.splat-relight", "CNT.IMP.splats"], "geometry-pipeline", "Kerbl et al. 2023; 3DGRT 2024; glTF splat extension work", "Standard format + relighting + shipped game use", "Photogrammetry meshes")
    r("ML runtime (inference, packaging, scheduling, NPU)", "M", ["ML.RT.inference", "ML.RT.packaging", "ML.RT.scheduling", "ML.RT.training-boundary", "ML.RT.determinism", "ML.RT.npu"], "ml-inference-runtime", "UE NNE; Windows ML; Core ML", "Two engine features depend on it in shipped builds", "No ML features")
    r("GPU physics offload", "M", ["PHY.ARCH.gpu"], "physics-architect", "PhysX GPU rigid bodies", "Async-compute headroom on target tiers", "CPU solver")
    r("SDF collision", "M", ["PHY.COL.sdf"], "collision-detection", "PhysX 5 SDF collision", "Shipped-title use", "Convex decomposition")
    r("Particle & GPU fluids", "M", ["PHY.FLUID.particles", "PHY.FLUID.gpu"], "fluid-simulation", "Niagara Fluids (beta); Flex titles", "Gameplay-interactive shipped use", "Grid smoke / VFX-grade fluids")
    r("ML cloth & learned deformables", "X", ["PHY.SOFT.ml"], "cloth-deformables", "Research; UE ML cloth experiments", "Production quality & budget", "XPBD cloth")
    r("ML deformers", "M", ["ANM.DEF.ml"], "deformation-skinning", "UE ML Deformer", "Training pipeline & runtime cost fit", "Linear/DQ skinning + correctives")
    r("Learned motion & neural controllers", "M", ["ANM.SYN.learned"], "motion-synthesis", "Holden et al. 2020", "Memory/runtime vs quality evidence on engine data", "Motion matching")
    r("Audio-driven & ML lip sync", "M", ["ANM.FACE.lipsync"], "facial-animation", "Production phoneme lip sync; ML variants", "Localization coverage & quality", "Phoneme/viseme lip sync")
    r("Wave-based acoustic propagation", "M", ["AUD.SPAT.propagation"], "spatial-audio-acoustics", "Project Acoustics; Steam Audio", "Bake/runtime cost fit", "Reverb zones + occlusion")
    r("Runtime neural speech (TTS/ASR)", "M", ["AUD.CONTENT.speech"], "audio-content-runtime", "Shipped AI-NPC titles 2025", "Latency, cost & localization quality", "Recorded VO")
    r("Seamless server meshing", "X", ["NET.ARCH.meshing"], "network-architect", "Star Citizen (2024–25); SpatialOS withdrawn", "Two shipped-title technical postmortems", "Zoning/instancing")
    r("QUIC/WebTransport game transport", "M", ["NET.TRANS.quic"], "network-transport", "RFC 9000; WebTransport", "Latency parity with custom UDP on target platforms", "Custom UDP protocol")
    r("Learned & LLM-driven agents", "M", ["GAM.AI.learned", "GAM.AI.llm"], "ai-behavior-perception", "GT Sophy; inZOI/PUBG Ally/Where Winds Meet (2025)", "Moderation, cost & rating requirements met per title", "Authored behavior via C-AIAGENT fallback")
    r("Generative authoring tools", "M", ["ED.AI.generative", "ED.AI.provenance", "ED.AI.evaluation", "CNT.COOK.ml-assisted"], "ai-assisted-authoring", "Unity AI; Roblox Assistant", "Licensing/provenance clear for training data", "Manual authoring")
    r("Agent/automation control API (MCP class)", "M", ["ED.ARCH.agent-api", "QA.FUNC.agent-exploration"], "editor-architect", "MCP integrations for major engines (2025); EA SEED RL testing", "Stable protocol adoption", "CLI/commandlets")
    r("GPU & training cook steps", "M", ["CNT.COOK.gpu-steps"], "content-pipeline-architect", "NTC encoding; ML deformer training", "Pinned-artifact determinism validated", "CPU cook steps only")
    r("Generative-AI service boundary & guardrails", "M", ["PLAT.SVC.genai-boundary", "XC.SEC.genai"], "online-services-liveops", "OWASP LLM Top 10; Steam AI disclosure", "Per-title policy approval", "No live-generated content")
    r("Mixed reality & spatial computing", "M", ["PLAT.XR.scene", "PLAT.XR.anchors", "PLAT.XR.depth-occlusion", "PLAT.XR.gaze-input", "PLAT.XR.light-estimation"], "xr-runtime", "OpenXR 1.1 scene/anchor extensions; Quest 3 Depth API; visionOS", "Cross-vendor OpenXR standardization", "VR-only")
    r("Eye tracking as desktop input", "E", ["INP.DEV.eye-tracking"], "input-devices-haptics", "Tobii Game Integration SDK", "n/a (established)")
    r("Autostereo / light-field displays", "M", ["RND.ARCH.multiview"], "render-architect", "Samsung Odyssey 3D, SpatialLabs SDKs", "Market share justifies N-view tier", "Stereo/mono")
    r("RISC-V targets", "S", [], "platform-architect", "RVV 1.0 spec; no game hardware", "A target console/PC ships on RISC-V", non_goal=True)
    r("Brain-computer input", "S", [], "input-devices-haptics", "Research only (OpenBCI/Galea)", "Consumer device with SDK", non_goal=True)
    r("CXL memory tiers", "S", [], "memory-allocators", "Server-only hardware", "Client/console hardware exposes tiered memory", non_goal=True)
    r("Explicit multi-GPU", "S", [], "gpu-platform-architect", "Vendor support withdrawn", "Vendor re-investment", non_goal=True)
    r("Backend service implementation", "E", [], "engine-architect", "Scope decision", "Engine becomes a service platform", non_goal=True)
    ed.doc["radar"] = {"_doc": "Technology radar. Every non-established capability must appear here with owner, evidence, "
                               "revisit trigger and fallback; non-goals are recorded explicitly. Owned by "
                               "architecture-governance (ARCH.GOV.radar).", "entries": E}
    ed.note("K-FUTURE-13", f"radar.json created with {len(E)} entries")


def legacy(ed):
    P = []

    def p(pid, pattern, hint, stance, owner):
        P.append({"id": pid, "pattern": pattern, "detection": hint, "default_stance": stance, "justification_owner": owner})
    p("L01", "Central sequential update loop", "one function calls subsystems in order each frame", "Task graph of phases with derived ordering (C-FRAME)", "frame-orchestration")
    p("L02", "Per-object virtual Tick()", "tick functions on objects/components", "Scheduled systems with declared access; opt-in budgeted ticks", "gameplay-architect")
    p("L03", "Game-thread / render-thread dichotomy", "named long-lived render thread", "Render work as tasks; dedicated threads only by ADR", "gpu-platform-architect")
    p("L04", "Main-thread-only engine APIs", "UI, scripting or platform callbacks require the OS main thread", "PAL isolates OS-thread-bound APIs behind queues", "platform-architect")
    p("L05", "Pervasive inheritance object hierarchies", "Actor→Pawn→Character chains", "Composition of components/systems + services", "entity-object-model")
    p("L06", "Possession / controller-pawn model by habit", "universal possession concept", "Control binding as data, chosen per game by ADR", "gameplay-architect")
    p("L07", "Universal scene graph", "one tree holds the world", "Partitioned data-oriented world; hierarchy only for attachment", "world-architect")
    p("L08", "Hidden globals & singletons", "static instances initialized implicitly", "Service registry + init graph", "core-runtime-architect")
    p("L09", "Process-global mutable cvars read anywhere", "cvar reads inside parallel tasks", "Immutable config snapshots latched at sync points", "core-runtime-architect")
    p("L10", "Hot-path virtual dispatch across contracts", "virtual call per draw/body/query", "Batch-granular interfaces; binding at build/load time", "engine-architect")
    p("L11", "Coarse locks & global renderer sync", "mutex around a subsystem; renderer-wide flush", "Declared access, channels, lock-free where justified", "concurrency-primitives")
    p("L12", "Draw-call-centric CPU submission on capable tiers", "one CPU draw per object on desktop/console", "GPU-driven on capable tiers; CPU-batched on TBDR/lite3d by ADR", "render-architect")
    p("L13", "DX11/OpenGL binding & sync assumptions", "slot binding, immediate context, driver-managed hazards", "Binding tiers + render-graph-derived barriers", "rhi-core")
    p("L14", "Per-object render proxy mirror", "proxy objects created/synced per object per frame", "Change-tracked delta extraction, O(changes)", "render-architect")
    p("L15", "Frame-tied resource lifetimes", "resources freed at end of frame/level", "Explicit lifetimes + retirement keyed to completion tokens", "resource-streaming-architect")
    p("L16", "Synchronous IO / blocking loads", "file read on a frame-critical thread", "Async staged pipeline with deadlines", "async-io-storage")
    p("L17", "Page-fault-driven streaming", "mmap reads on latency-critical workers", "Explicit IO requests; mmap only prefetched/tool-side", "async-io-storage")
    p("L18", "Level-as-a-file loading", "whole level loaded before play", "Cell streaming with budgeted activation", "world-architect")
    p("L19", "Immediate synchronous observer callbacks across subsystems", "callbacks invoked on the producer's thread mid-update", "Deferred batched events at declared consumption points", "entity-object-model")
    p("L20", "Stringly-typed reflection on runtime paths", "name lookups per frame", "Static reflection & resolved IDs; strings at tool/script boundaries", "reflection-metadata")
    p("L21", "Tracing-GC-managed engine objects", "engine objects reachable via GC", "Explicit ownership + generational handles; weak script refs", "entity-object-model")
    p("L22", "Global script VM on one thread", "single interpreter mutating the world", "Per-worker VMs/isolates, deferred mutation", "scripting-runtime")
    p("L23", "Editor-in-runtime monolith", "editor code linked into shipping builds", "Tool-side modules; tools target only", "editor-architect")
    p("L24", "Blocking cook-before-play", "full cook required before running", "On-demand cooking & cook-server streaming", "content-pipeline-architect")
    p("L25", "Single-thread-first design", "systems that must run serially by construction", "Parallel by default; serial exceptions enumerated", "architecture-governance")
    p("L26", "Monolithic subsystems", "one module owning a whole domain", "Contracts + focused experts", "engine-architect")
    p("L27", "ECS for everything / GPU-driven everywhere (new dogma)", "technique applied where access patterns do not fit", "Per-domain ADR with workload evidence", "architecture-governance")
    ed.doc["legacy"] = {"_doc": "Anti-legacy pattern catalogue. A pattern is not forbidden; if present it needs an ADR by the "
                                "justification owner. Checked by K-LEGACY at G2 and S1–S4.", "patterns": P}
    ed.note("K-LEGACY-16", f"legacy-patterns.json created with {len(P)} patterns")


def milestones(ed):
    M0 = ["platform-architect", "platform-desktop", "core-runtime-architect", "math-simd-numerics", "memory-allocators",
          "containers-core-types", "concurrency-primitives", "job-system-task-graph", "observability-telemetry",
          "crash-diagnostics", "runtime-scalability", "frame-orchestration", "entity-object-model", "reflection-metadata",
          "serialization-schema", "async-io-storage", "package-formats-vfs", "content-pipeline-architect",
          "resource-streaming-architect", "gpu-platform-architect", "rhi-core", "rhi-vulkan", "gpu-memory-resources",
          "render-graph-scheduling", "shader-system", "text-fonts", "render-2d-vector", "input-devices-haptics",
          "input-system", "asset-cook-processors", "build-system-toolchains", "ci-cd-automation"]
    M1 = ["ecs-runtime", "spatial-transforms", "world-architect", "world-data-model", "determinism-replay",
          "physics-architect", "physics-2d", "animation-architect", "animation-runtime", "animation-graphs",
          "audio-architect", "audio-dsp-mixing", "audio-content-runtime", "localization-i18n", "accessibility",
          "ui-architect", "gameplay-architect", "gameplay-systems-toolkit", "gameplay-data", "scripting-runtime",
          "persistence-save", "character-movement", "render-architect", "material-system", "post-color-hdr",
          "texture-streaming-vt", "reconstruction-upscaling", "vfx-particles", "visual-debugging-tools", "plugin-system",
          "hot-reload-iteration", "editor-architect", "editor-ui-framework", "world-editor-viewport", "graph-editor-framework",
          "asset-import-interchange", "platform-services", "media-playback", "narrative-dialogue", "navigation-pathfinding",
          "ai-behavior-perception", "cinematics-sequencer", "packaging-release-patching", "physics-tools"]
    M2 = ["geometry-pipeline", "virtualized-geometry-lod", "direct-lighting-shadows", "global-illumination",
          "ray-tracing-infrastructure", "translucency-decals", "atmosphere-weather", "terrain", "water-ocean",
          "vegetation-foliage", "collision-detection", "rigid-body-dynamics", "character-physics", "cloth-deformables",
          "ik-procedural-animation", "deformation-skinning", "facial-animation", "spatial-audio-acoustics",
          "character-rendering", "path-tracing", "rhi-d3d12", "rhi-metal", "platform-console", "platform-mobile",
          "collaboration-version-control", "destruction-fracture"]
    M3 = ["procedural-generation", "crowd-simulation", "motion-synthesis", "vehicle-physics"]
    M4 = ["network-architect", "network-transport", "replication", "prediction-rollback", "dedicated-server",
          "anti-cheat-integrity", "online-services-liveops"]
    M5 = ["ml-inference-runtime", "fluid-simulation", "modding-ugc", "xr-runtime", "platform-web", "rhi-webgpu",
          "ai-assisted-authoring", "voxel-worlds"]
    ed.doc["milestone"] = {
        "_doc": "Milestone ladder (walking skeleton first, then widening). Each milestone lists the build skills that "
                "join it; check.py proves each milestone closed over its own and earlier milestones' skills. Process "
                "skills are active from M0. Contracts reach 'draft' when first consumed and 'frozen' at the listed "
                "milestone.",
        "milestones": [
            {"id": "M0", "name": "Walking skeleton", "configuration": "indie-2d-client", "skills": M0,
             "exit": "Boots on one PC platform, runs the task graph, opens a window, presents through the RHI, reads "
                     "input, draws a sprite and text, loads one cooked asset from a package, passes CI and the "
                     "determinism/sanitizer smoke lanes.",
             "contracts_frozen": ["C-BASE", "C-MEM", "C-SYNC", "C-TASK", "C-ERR", "C-INSTR"],
             "contracts_draft": ["C-PAL", "C-RHI", "C-RG", "C-SHADER", "C-RES", "C-ASSET", "C-FRAME"]},
            {"id": "M1", "name": "Indie 2D vertical slice", "configuration": "indie-2d-client", "skills": M1,
             "exit": "The indie-2d reference game is shippable on PC with editor, save, localization, accessibility "
                     "baseline and hot reload; indie-2d-tools configuration builds.",
             "contracts_frozen": ["C-PAL", "C-FRAME", "C-ID", "C-ECS", "C-SER", "C-ASSET", "C-RES", "C-DRAW2D", "C-UI"],
             "contracts_draft": ["C-RSCENE", "C-PHYS", "C-ANIM", "C-AUDIO", "C-GAME"]},
            {"id": "M2", "name": "Standard 3D", "configuration": "standard-3d-client", "skills": M2,
             "exit": "The standard-3d reference game runs on PC and one console tier with GPU-driven and CPU-submission "
                     "paths, reference path tracer validation, and the lite-3d mobile configuration.",
             "contracts_frozen": ["C-RSCENE", "C-INSTANCES", "C-PHYS", "C-ANIM", "C-AUDIO", "C-RHI"],
             "contracts_draft": ["C-RT", "C-LIGHT", "C-GI", "C-ENV"]},
            {"id": "M3", "name": "Open world & large simulation", "configuration": "open-world-client", "skills": M3,
             "exit": "Open-world reference slice streams at target speed within the arbitration budget; massim "
                     "configuration closed and benchmarked.", "contracts_frozen": ["C-WORLD", "C-SIGNIF", "C-ENV"],
             "contracts_draft": []},
            {"id": "M4", "name": "Online", "configuration": "online-3d-server", "skills": M4,
             "exit": "Online reference game with dedicated server, prediction/rollback, bot load test and cert "
                     "pre-checks for online features.", "contracts_frozen": ["C-NET", "C-NETLINK", "C-REP", "C-PREDICT"],
             "contracts_draft": []},
            {"id": "M5", "name": "AAA & ecosystem", "configuration": "aaa-open-world-online-client", "skills": M5,
             "exit": "AAA reference slice; mods; XR; web; ML features behind optional contracts.",
             "contracts_frozen": [], "contracts_draft": ["C-ML", "C-MLGPU"]}]}
    ed.note("K-PROD-1", "milestones.json: M0 walking skeleton → M5 AAA & ecosystem")


def apply(ed):
    performance(ed)
    quality_security(ed)
    orchestration(ed)
    critics(ed)
    crosscutting(ed)
    seed(ed)
    radar(ed)
    legacy(ed)
    milestones(ed)
    fixups(ed)


def fixups(ed):
    """Corrections found by check.py on the first application of this revision."""
    T = "check.py"
    ed.unuse("scripting-runtime", "C-GAME", tags=T + " K-LEGACY-3 (gameplay registers types via C-REFL; no upward edge)")
    ed.unuse("network-transport", "C-SVC", "C-LIVE", tags=T + " (relay/NAT credentials arrive via configuration; no upward edge)")
    ed.contract_set("C-SAVE", layer=3, tags=T + " (save participation is a subsystem-level interface)")
    ed.skill_set("localization-i18n", targets=["client", "headless-client", "server", "tools"],
                 tags=T + " (string IDs & formatting needed by server-side dialogue and messages)")
    ed.use("cinematics-sequencer", "C-ANIM?", tags=T + " (timelines without skeletal animation in minimal games)")
    ed.cap_set("RES.MGMT.arbitration", name="Cross-pool memory & IO-bandwidth arbitration (textures, geometry pages, shadow "
               "pages, audio, animation, world cells, BVH, model weights); single physical budget on UMA; OS pressure signals",
               tags=T)
    ed.cap_set("PLAT.SVC.genai-boundary", rm_contrib=["ml-inference-runtime"], tags=T)
    ed.use("content-pipeline-architect", "C-ML?", tool=True, tags=T + " K-FUTURE-4")
    sm = ed.doc["seed"]
    for sec in ("brief_domains", "brief_hardware", "brief_targets"):
        for term, caps in sm[sec].items():
            new = []
            for c in caps:
                if c == "RND.RHI.backends":
                    new += ["RND.RHI.d3d12", "RND.RHI.vulkan", "RND.RHI.metal", "RND.RHI.webgpu"]
                elif c == "RND.RHI.bindless":
                    new.append("RND.RHI.binding-tiers")
                elif c == "GAM.AI.avoidance":
                    new.append("GAM.AI.local-avoidance")
                else:
                    new.append(c)
            sm[sec][term] = new
    ed.note(T, "seed-map references updated for renamed/split capabilities")
    cp = "character-physics"
    ed.cap("PHY.CTRL.sensing", "Controller ground, step, slope & ledge sensing queries", cp, contrib=["collision-detection"],
           tags=T + " K-SIM-10")
    ed.cap_set("PHY.CTRL.platforms", name="Controller interaction with dynamic bodies (push, carry, ride, moving platforms)",
               tags=T)
    for sid in ("packaging-release-patching", "api-lifecycle-migration", "collaboration-version-control", "network-architect"):
        ed.use(sid, "C-RELEASE", tags=T + " K-ARCH-13")
    ed.use("program-orchestration", "C-PROD", tags=T + " K-PROD-3")
    for sid in ("entity-object-model", "resource-streaming-architect", "gpu-memory-resources", "scripting-runtime"):
        ed.use(sid, "C-LIFETIME", tags=T + " K-SYSTEMS-9")
    ed.use("gameplay-architect", "C-AIAGENT?", tags=T + " K-GAMEPLAY-15")

    ed.skill_set("ml-inference-runtime", profiles=["lite3d", "std3d"], tags=T + " (scale-down: not in minimal/2D unless a consumer opts in)")
    ed.skill_set("ecs-runtime", profiles=["min2d", "lite3d", "std3d"], tags=T + " K-GAMEPLAY-14 (hybrid model: minimal games need no ECS)")
    ed.skill_set("platform-web", profiles=["minimal", "min2d", "lite3d"], tags=T + " K-PLATFORM-6")
