"""Round-3 revision, part E: foundation, performance, production and future-proofing findings
(K-SYSTEMS-5,7,9,10,11; K-PERF-5..9,13; K-PROD-4,9,10,12,13; K-FUTURE-1,4,5,6,9,11..14,16,17)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r3_d import _add, _append, _config, _input, _radar, _unt  # noqa: E402


def _radar_set(ed, tech_prefix, **kw):
    hit = False
    for e in ed.doc["radar"]["entries"]:
        if e["tech"].startswith(tech_prefix):
            e.update(kw)
            hit = True
    assert hit, tech_prefix


def apply(ed):
    # ============================================================ SYSTEMS
    t = "K-SYSTEMS-5"
    ed.cap("CORE.FRAME.multi-world", "Concurrent per-world frame graphs on one worker pool: independent time domains and "
           "cadences, cross-world priority and fair share, per-world overload isolation, process-global vs world-scoped "
           "sync points", "frame-orchestration",
           contrib=["dedicated-server", "editor-architect", "job-system-task-graph"], tags=t)

    t = "K-SYSTEMS-7"
    _input(ed, "ipc-messages", "core-runtime-architect", ["crash-diagnostics", "editor-architect"], "hostile-local",
           "frame size/rate/schema version; TOCTOU-safe copy-out from shared memory")
    _append(ed, "C-IPC", "untrusted-frame validation (ipc-messages input) on every endpoint that survives into shipping.", t)

    t = "K-SYSTEMS-9"
    ed.use("memory-allocators", "C-SYNC", tags=t)
    ed.contract_set("C-MEM", requires=ed.contract("C-MEM")["requires"] + ["C-SYNC"], tags=t)
    _append(ed, "C-SYNC", "lock-free node storage uses the C-BASE raw allocator (not C-MEM).", t)

    t = "K-SYSTEMS-10"
    ed.note(t, "C-TYPES no longer carries crypto text (fixed with K-ARCH-16); crypto stays in CORE.TYPES.crypto owned by "
               "security-runtime behind C-SIGN")

    t = "K-SYSTEMS-11"
    ed.cap_set("CORE.MEM.virtual", name="Virtual memory reservation, mapping & page-size policy (4K/64K/2M, large/huge "
               "pages, commit/decommit granularity per platform, client and server)", tags=t)

    # ============================================================ PERF
    t = "K-PERF-5"
    _append(ed, "C-GOVERN", "CPU critical-path and per-phase tick-overrun signals from C-FRAME (shipping-grade); "
            "CPU-vs-GPU-bound classification selects actuators; server tick overrun is the primary input on server "
            "targets.", t)
    ed.cap_set("NET.SESS.overload", name="Server overload actuators (time dilation, adaptive tick, relevancy throttling) "
               "registered with CORE.SCALE.actuators", add_contrib=["runtime-scalability"], tags=t)

    t = "K-PERF-6"
    ed.cap("PRF.NET.resim-cost", "Worst-case resimulation cost vs frame budget per rollback/prediction configuration",
           "online-performance", contrib=["prediction-rollback", "determinism-replay"], tags=t)
    _append(ed, "C-BUDGET", "resimulation-window line per rollback/prediction configuration "
            "((window × tick cost) + snapshot save/restore per tick fits one frame).", t)

    t = "K-PERF-7"
    ed.cap("PRF.MEM.size", "Binary/WASM, install, download and on-disk cache size analysis and attribution per module, "
           "asset class and configuration", "memory-performance",
           contrib=["build-system-toolchains", "packaging-release-patching", "platform-web"], tags=t)
    _append(ed, "C-BUDGET", "size lines per configuration × platform (binary/WASM, install, download, shader/PSO cache).", t)

    t = "K-PERF-8"
    _append(ed, "C-BUDGET", "energy per frame / battery-hours and sustained-state frame-time budgets per battery-powered tier.", t)
    _append(ed, "C-BENCH", "thermal-soak preconditioning and sustained-window measurement.", t)
    ed.cap("PRF.METH.energy", "Whole-device energy & sustained-performance methodology", "performance-architect",
           contrib=["gpu-performance", "cpu-performance", "platform-mobile"], tags=t)

    t = "K-PERF-9"
    ed.skill_add(tags=t, id="pipeline-performance", name="Pipeline Performance", tier="expert",
                 parent="performance-architect", profiles=["all"], kind="process", targets=[], workstream="performance",
                 purpose="Independent analysis of production-pipeline performance: distributed-cook utilization and "
                         "critical path, DDC miss root causes, shader permutation compile cost, C++/native build critical "
                         "path and header cost, CI wall-clock; routes findings via C-PERF.",
                 non_responsibilities=[["Pipeline implementation", "build-release-architect"],
                                       ["Benchmark harness", "perf-benchmarking"],
                                       ["Editor implementation", "editor-architect"]],
                 expertise=["build and cook profiling", "critical-path analysis", "cache hit-rate analysis"],
                 consumes=["C-INSTR", "C-BUDGET", "C-BENCH"])
    for cid, name, contrib in (("PRF.PIPE.cook", "Distributed-cook utilization, critical path and DDC miss root causes",
                                ["content-pipeline-architect", "asset-cook-processors"]),
                               ("PRF.PIPE.shader-compile", "Shader permutation compile cost and cache analysis",
                                ["shader-system"]),
                               ("PRF.PIPE.build", "Native build critical path, header cost and cache effectiveness",
                                ["build-system-toolchains"]),
                               ("PRF.PIPE.ci", "CI wall-clock and queue analysis", ["ci-cd-automation"])):
        ed.area("PRF.PIPE", "Pipeline performance", tags=t)
        ed.cap(cid, name, "pipeline-performance", contrib=contrib, tags=t)
    ed.cap_move("PRF.LOAD.editor", "PRF.PIPE.editor", tags=t)
    ed.cap_set("PRF.PIPE.editor", owner="pipeline-performance", add_contrib=["loading-streaming-performance"], tags=t)

    t = "K-PERF-13"
    ed.cap("PRF.BENCH.lab", "Reference perf hardware per tier: inventory, clock/thermal control, exclusivity, noise "
           "qualification (tiers from ARCH.REQ.hardware-tiers)", "perf-benchmarking", contrib=["ci-cd-automation"], tags=t)

    # ============================================================ PROD
    t = "K-PROD-4"
    ed.cap_set("ARCH.ORG.human-gates", name="Register of decisions requiring human authorization (contracts, spend, NDA "
               "material, and irreversible live-production actions: player-data restore/edit, GM/admin commands on "
               "shipping servers, ban waves, rollout promotion past canary, global kill switch and remote-config changes, "
               "economy grants)", add_contrib=["online-services-liveops", "anti-cheat-integrity", "dedicated-server"],
               tags=t)
    _append(ed, "C-LIVE", "live-production actions carry a human-approval token.", t)

    t = "K-PROD-9"
    ed.cap("ARCH.PROD.vendor-telemetry", "Legal and privacy basis of vendor-bound telemetry: licensee-controlled opt-in, "
           "controller/processor roles, DPA template, allowed data classes, no silent billing telemetry",
           "privacy-data-protection", contrib=["engine-product-management", "observability-telemetry",
                                               "crash-diagnostics", "certification-compliance"], tags=t)

    t = "K-PROD-10"
    ed.cap("QA.CERT.ml-provenance", "Provenance of shipped ML models and training data: model/dataset licence register, "
           "performer-consent register for digital replicas (voice, face, motion) linked to CNT.ID.rights, AI-output "
           "transparency mapping (EU AI Act class)", "certification-compliance",
           contrib=["ml-inference-runtime", "content-pipeline-architect", "motion-synthesis", "facial-animation",
                    "narrative-dialogue"], tags=t)

    t = "K-PROD-12"
    import r3_z
    for row in r3_z.LADDER:
        if row[0] == "M7":
            row[4] = [g for g in row[4] if g != "PLAT.LIVE.operations"]
        if row[0] == "M4":
            row[4].append("PLAT.LIVE.operations")
    r3_z.GATE_VALIDATOR.setdefault("PLAT.LIVE.operations", "QA.FUNC.load")
    ed.note(t, "PLAT.LIVE.operations gate moves to M4 (operational readiness before the first online launch); "
               "end-of-service rehearsal stays at M7")

    t = "K-PROD-13"
    ed.cap_set("BLD.REL.rollback", name="Per-channel recovery: server/content rollback, client roll-forward hotfix path "
               "(store clients cannot be downgraded), rollout halt, compatibility-window constraints",
               add_contrib=["network-architect", "online-services-liveops"], tags=t)

    # ============================================================ FUTURE
    t = "K-FUTURE-1"
    ed.doc["skill"]["profiles"]["addons"]["hwrt"] = "Hardware ray tracing required (RT-only lighting paths, RT+tensor console " \
        "baseline); no raster fallback is validated in these configurations"
    _append(ed, "C-GPUTIER", "tiers 'rt' and 'rt+tensor' declare hardware ray tracing and tensor support as required "
            "baselines for configurations carrying the hwrt profile.", t)
    ed.cap("RND.GI.rt-required", "Hardware-RT-only lighting path (no raster fallback) for the hwrt profile",
           "global-illumination", contrib=["ray-tracing-infrastructure", "path-tracing"], profiles=["hwrt"], tags=t)
    _config(ed, "rt-required-3d-client", ["std3d", "aaa", "hwrt"], "client", ["pc", "console"], None, "M6")
    ed.note(t, "gated contracts (C-RT, C-RTAS, C-MLGPU) stay optional at the dependency level so non-RT builds stay "
               "buildable; RT-required products are expressed as the hwrt profile plus the 'rt' GPU tier (partial)")

    t = "K-FUTURE-4"
    _radar_set(ed, "Agent/automation control API (MCP class) (QA.FUNC", fallback="scripted bots and random-walk monkeys",
               evidence="EA SEED RL testing; academic game-testing agents", revisit="Agent-found defects exceed the "
               "scripted-bot rate over two milestones")
    _radar_set(ed, "Generative authoring tools (CNT.COOK", fallback="classical processors",
               revisit="Licensing/provenance clear for training data (QA.CERT.ml-provenance)")
    _radar_set(ed, "Strand hair simulation & rendering (PHY.SOFT", fallback="bone-chain dynamics")
    _radar_set(ed, "ReSTIR GI & path-traced GI (RND.PT", fallback="hybrid raster + RT effects")
    _radar_set(ed, "WebGPU backend & web 3D (PLAT.WEB", revisit="Shipped WebGPU with bindless/timestamp features in all "
               "engines' target browsers")
    _radar_set(ed, "Gaussian splatting & radiance fields (CNT.IMP", fallback="convert to meshes at import")
    _radar_set(ed, "Work graphs & mesh nodes (RND.RHI", fallback="ExecuteIndirect / device-generated commands")
    _radar_set(ed, "Generative-AI service boundary & guardrails (XC", fallback="no live-generated content; offline "
               "authored variants")

    t = "K-FUTURE-5"
    ed.cap("ARCH.GOV.radar-transitions", "Maturity-class transitions: radar review at every milestone exit, promotion "
           "checklist (evidence, profile retag, optional-to-required change, extension-tier freeze, conformance, budget) "
           "and demotion into legacy-patterns on vendor withdrawal", "architecture-governance",
           contrib=["research-evidence", "api-lifecycle-migration"], tags=t)

    t = "K-FUTURE-6"
    ed.cap_set("ML.RT.sequence-models", name="Constrained decoding and diffusion execution inside the frame budget",
               tags=t)
    ed.cap_move("ML.RT.sequence-models", "ML.RT.constrained-decoding", tags=t)
    ed.cap("ML.RT.sequence-exec", "Autoregressive execution: KV-cache budgets, token streaming, cancellation",
           "ml-inference-runtime", "M", contrib=["audio-content-runtime", "ai-behavior-perception"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "ML.RT.sequence-models" in e["capabilities"]:
            e["capabilities"] = ["ML.RT.constrained-decoding"]
    _radar(ed, "On-device autoregressive execution", "M", "ml-inference-runtime", ["ML.RT.sequence-exec"],
           "OS-provided and open on-device speech/language runtimes (2024–2026)",
           "Two shipping consumers stay within KV-cache and latency budgets on min-spec", "remote model via C-LIVE (ML.RT.local-remote)")
    for cid in ("AUD.CONTENT.speech", "GAM.AI.local-guardrails"):
        ed.cap_set(cid, add_contrib=["ml-inference-runtime"], tags=t)
    ed.note(t, "AUD.CONTENT.speech and GAM.AI.local-guardrails depend on ML.RT.sequence-exec (M), not on the X row")

    t = "K-FUTURE-9"
    ed.cap_set("CORE.LIFE.language", name="Implementation language(s) ADR (C++, Rust or mixed), standard baseline & "
               "compiler feature policy, coding standard", tags=t)
    ed.cap_set("BLD.SYS.compile-speed", name="Compile-time scalability (modules/unity/PCH or crate-graph partitioning)",
               tags=t)
    ed.cap_set("XC.ITER.live-coding", name="Native-code live coding", tags=t)
    ed.cap_set("RND.SHADER.interop", name="Shared host/shader interop headers", tags=t)
    ed.skill("core-runtime-architect")["expertise"] = ["C++/Rust systems programming", "module systems", "error models"]

    t = "K-FUTURE-11"
    ed.cap("PHY.ARCH.learned-surrogates", "Learned policies/surrogates inside the physics step (substep hook with recorded "
           "or deterministic outputs)", "physics-architect", "X", contrib=["ml-inference-runtime"],
           profiles=["experimental"], tags=t)
    ed.use("physics-architect", "C-ML?", tags=t)
    ed.use("rigid-body-dynamics", "C-ML?", tags=t)
    _append(ed, "C-PHYS", "substep policy hook whose outputs are recorded or deterministic.", t)
    _radar(ed, "Learned surrogates inside the physics step", "X", "physics-architect", ["PHY.ARCH.learned-surrogates"],
           "Research on learned destruction/fluid surrogates; no shipped engine feature",
           "A shipped title uses a learned surrogate with recorded outputs", "classical solvers")

    t = "K-FUTURE-12"
    _input(ed, "player-model-prompts", "ai-behavior-perception",
           ["audio-content-runtime", "online-services-liveops", "modding-ugc"], "hostile-remote",
           "length/rate/token budget/moderation pre-filter")
    ed.cap_set("XC.SEC.genai", add_contrib=["ai-behavior-perception"], tags=t)

    t = "K-FUTURE-13"
    ed.doc["skill"]["profiles"]["addons"]["ml"] = "Runtime ML features (on-device inference, OS models, ML upscaling)"
    ed.skill_set("ml-inference-runtime", profiles=["ml"], tags=t)
    for name, cfg in ed.doc["skill"]["configurations"].items():
        if any(p in cfg["profiles"] for p in ("aaa", "xr", "experimental")) and "ml" not in cfg["profiles"]:
            cfg["profiles"].append("ml")

    t = "K-FUTURE-14"
    ed.cap_set("RND.GPU.hetero-offload", name="Heterogeneous adapter offload (non-inference async work and encode on a "
               "secondary adapter)", tags=t)
    ed.cap_set("ML.RT.npu", add_contrib=["gpu-platform-architect"], tags=t)

    t = "K-FUTURE-16"
    ed.skill("ml-inference-runtime")["purpose"] = ed.skill("ml-inference-runtime")["purpose"].replace(
        "cooperative-vector / tensor", "matrix/tensor intrinsics tier")
    ed.skill("ml-inference-runtime")["expertise"] = [x.replace("cooperative vectors", "matrix/tensor intrinsics")
                                                     for x in ed.skill("ml-inference-runtime")["expertise"]]
    ed.cap_set("RES.IO.gpu-decompress", name="GPU decompression (GPU-decodable codecs, GDeflate/Zstd class)", tags=t)
    _radar_set(ed, "Neural materials", revisit="Cross-vendor matrix/tensor-intrinsic support + shipped evidence")
    _radar_set(ed, "Neural texture compression", revisit="Shipped titles + non-preview matrix/tensor-intrinsic support")

    t = "K-FUTURE-17"
    ed.cap_set("PLAT.PAL.cloud-hybrid", owner="network-architect",
               add_contrib=["platform-architect", "frame-orchestration", "online-services-liveops"], tags=t)
    _radar_set(ed, "Cloud-hybrid compute", owner="network-architect")
