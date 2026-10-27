"""Round-4 revision, part C: platform, performance, production and future-proofing findings
(K-PLATFORM-1..7; K-PERF-1..9; K-PROD-2,4..7; K-FUTURE-1..6,8,9)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round-3"))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap, _rename  # noqa: E402


def _ms(ed, mid):
    return next(m for m in ed.doc["milestone"]["milestones"] if m["id"] == mid)


def _claim(ed, name, profiles, target, platforms, target_platforms, mid):
    cfg = {"profiles": profiles, "target": target, "platforms": platforms}
    if target_platforms:
        cfg["target_platforms"] = target_platforms
    ed.doc["skill"]["configurations"][name] = cfg
    _ms(ed, mid)["configurations"].append(name)


def _gate(ed, mid, cap, validator, move_from=None):
    if move_from:
        g = _ms(ed, move_from)["gates"]
        _ms(ed, move_from)["gates"] = [x for x in g if x["capability"] != cap]
    _ms(ed, mid)["gates"].append({"capability": cap, "validator": validator})


def apply(ed):
    # ================================================================ PLATFORM
    t = "K-PLATFORM-1"
    _cap(ed, "PLAT.PAL.target-tools", "Target-platform tooling contract content: cook format variants, shader-target hook, "
         "packager hook, deploy/run/debug", "platform-architect", tags=t)
    for cid, owner in (("PLAT.DESK.target-tools", "platform-desktop"), ("PLAT.MOB.target-tools", "platform-mobile"),
                       ("PLAT.WEB.target-tools", "platform-web"), ("PLAT.SRV.target-tools", "platform-server-host"),
                       ("PLAT.CON.target-tools", "platform-console")):
        _cap(ed, cid, "Target-platform cook variants, shader-target and packager hooks, deploy/run/debug", owner,
             contrib=["rhi-console"] if owner == "platform-console" else [], tags=t)

    for sid in ("platform-architect", "platform-desktop", "platform-mobile", "platform-web", "platform-server-host",
                "platform-console"):
        ed.use(sid, "C-COOK", tool=True, tags=t)

    t = "K-PLATFORM-2"
    _cap(ed, "PLAT.CON.svc-trophies-privileges", "Console first-party trophies/achievements, privileges and parental "
         "controls behind the public C-SVC interface", "platform-console", contrib=["platform-services"], tags=t)
    _cap(ed, "PLAT.CON.svc-entitlements-presence", "Console first-party entitlements, presence and activities behind the "
         "public C-SVC interface", "platform-console", contrib=["platform-services"], tags=t)
    ed.note(t, "platform-services keeps the C-SVC interface, PC/mobile stores and the emulator; console SDK "
               "implementations sit in per-holder confidential rows")

    t = "K-PLATFORM-3"
    for cid, nm in (("PLAT.CON.packaging", "Console packaging and signing tools"),
                    ("PLAT.CON.submission", "Console submission validators and pre-submission checkers"),
                    ("PLAT.CON.patch-format", "Console mandated patch/DLC formats and size rules"),
                    ("PLAT.CON.ci-lane", "Console devkit CI lanes")):
        _cap(ed, cid, nm + " (confidential, per platform holder; public stubs on BLD.REL.packaging/submission)",
             "platform-console", contrib=["packaging-release-patching", "ci-cd-automation"], tags=t)

    t = "K-PLATFORM-4 K-PLATFORM-7"
    pv = ed.doc["skill"]["platform_variants"]
    pv["xr-standalone"] = pv["xr-standalone"] + ["horizon-os", "pico-os"]
    pv["console"] = ["fixed-class-a", "portable-class-a", "fixed-class-b", "portable-class-b"]
    pv["web"] = ["chromium", "webkit", "gecko"]
    ed.skill("rhi-vulkan")["variants"] = ed.skill("rhi-vulkan")["variants"] + ["xr-standalone:horizon-os",
                                                                              "xr-standalone:pico-os"]
    _claim(ed, "xr-standalone-tools", ["lite3d", "xr"], "tools", ["pc"], ["xr-standalone"], "M5")
    ed.cap_set("QA.CERT.programs", add_contrib=["xr-runtime"], tags=t)

    t = "K-PLATFORM-5"
    _claim(ed, "lite-3d-mobile-openworld-online-client", ["lite3d", "openworld", "online"], "client", ["mobile"], None, "M5")
    _claim(ed, "lite-3d-portable-openworld-client", ["lite3d", "openworld"], "client", ["console"], None, "M5")
    _claim(ed, "lite-3d-web-client", ["lite3d"], "client", ["web"], None, "M5")

    t = "K-PLATFORM-6"
    _cap(ed, "PLAT.SVC.pc-storefronts", "PC storefront SDK adapters (Steamworks, Epic Online Services, GOG Galaxy, Microsoft "
         "Store/GDK-PC), Steam Input and overlay rules", "platform-services",
         contrib=["platform-desktop", "packaging-release-patching"], tags=t)
    _cap(ed, "BLD.REL.store-variants", "Per-store build variants and depots", "packaging-release-patching",
         contrib=["platform-services"], tags=t)
    ed.note(t, "a store axis is carried by these capabilities, not by a platform_variants field (partial)")

    # ================================================================ PERF
    t = "K-PERF-1"
    ed.cap_set("PRF.CPU.compiler", name="PGO profile data and optimization recommendations (flag mechanism belongs to "
               "BLD.SYS.configs)", tags=t)
    _rename(ed, "BLD.SYS.configs", "; sole owner of the compiler-flag mechanism with per-module flag classes ('det-strict' "
            "owned by determinism-replay, 'perf')", tags=t)
    _rename(ed, "XC.DET.conformance", "; optimization level, PGO and LTO are part of the conformance matrix", tags=t)

    t = "K-PERF-2"
    _append(ed, "C-SCALE", "each actuator carries a class ('presentation' | 'sim-local-nonobservable' | 'sim-authoritative'); "
            "under lockstep, rollback and replay recording only presentation actuators are client-driven, "
            "sim-authoritative ones go through tick-stamped recorded events.", t)

    t = "K-PERF-3"
    _gate(ed, "M1", "PRF.METH.asymptotics", "PRF.BENCH.scale-content", move_from="M6")
    for g in _ms(ed, "M5")["gates"]:
        if g["capability"] == "PRF.BENCH.scale-content":
            g["validator"] = "QA.SIM.mass-agents"
    ed.note(t, "asymptotic declaration gate moves to M1; M5 scale-content is validated by QA.SIM.mass-agents, breaking the "
               "circularity; the M1 scale-probe precondition on freezes is not added (partial)")

    t = "K-PERF-4"
    _cap(ed, "PRF.CPU.parallel-scaling", "Parallel scalability: work/span extraction, scaling curves (2 to 64 workers, SMT, "
         "P/E) with core masks, per-task overhead limits, parallel-efficiency-at-N line in C-BUDGET", "cpu-performance",
         contrib=["job-system-task-graph", "frame-orchestration", "observability-telemetry"], tags=t)

    t = "K-PERF-5"
    _cap(ed, "PRF.MEM.bandwidth", "DRAM/fabric bandwidth per frame by consumer class on UMA and mobile tiers "
         "(OBS.LOG.hw-counters), memory-bound classification and bandwidth actuators", "memory-performance",
         contrib=["gpu-performance", "loading-streaming-performance"], tags=t)
    _append(ed, "C-BUDGET", "DRAM/fabric bandwidth-per-frame line by consumer class for UMA and mobile tiers.", t)

    t = "K-PERF-6"
    _cap(ed, "PRF.BENCH.proxy-metrics", "Deterministic pre-merge proxy metrics (instruction and cache-miss counts, "
         "allocations per frame, draw/dispatch/barrier counts, bytes per entity, replay memory traffic) calibrated "
         "against lab wall-clock", "perf-benchmarking", contrib=["ci-cd-automation"], tags=t)
    _cap(ed, "PRF.BENCH.lab-scheduling", "Perf-lab scheduling, queueing and overload policy", "perf-benchmarking",
         contrib=["ci-cd-automation"], tags=t)

    t = "K-PERF-7"
    _gate(ed, "M2", "PRF.NET.resim-cost", "QA.SIM.netsim")
    _gate(ed, "M2", "PRF.MEM.size", "PRF.BENCH.stats")
    _gate(ed, "M3", "PRF.METH.energy", "PRF.GPU.power")
    _gate(ed, "M4", "PRF.NET.latency", "QA.FUNC.load")

    t = "K-PERF-8"
    _append(ed, "C-BUDGET", "p50/p99/p99.9 frame time, max hitch length and hitches per hour per tier, startup and "
            "level-transition time, stream-in quality at traversal speed, input-to-photon latency per refresh class and "
            "netcode family.", t)
    _rename(ed, "PRF.METH.budgets", "; percentile frame-time, hitch, startup/transition, traversal and latency lines", tags=t)

    t = "K-PERF-9"
    ed.doc["legacy"]["patterns"] += [
        {"id": "L79", "pattern": "Thread-per-subsystem and fixed worker counts", "detection": "per-subsystem loops for "
         "physics, audio, streaming or network; constant-size worker pools", "default_stance": "One scheduler, worker "
         "count from topology and actuators", "justification_owner": "job-system-task-graph",
         "stance_capabilities": ["CORE.JOBS.thread-model", "CORE.JOBS.scheduler", "CORE.SCALE.actuators", "PRF.CPU.hybrid"],
         "contradiction_terms": [r"thread-per-subsystem"]},
        {"id": "L80", "pattern": "Unbounded stage queues and benchmarks on non-profile builds", "detection": "queues "
         "without back-pressure; timings from debug builds", "default_stance": "Bounded queues with back-pressure; "
         "benchmarks on the profile build configuration", "justification_owner": "performance-architect",
         "stance_capabilities": ["PRF.METH.gates", "BLD.SYS.configs"], "contradiction_terms": [r"unbounded stage queues"]}]

    # ================================================================ PROD
    t = "K-PROD-2"
    _cap(ed, "ARCH.ORG.scope-control", "Scope control: budget envelope per milestone, burn/slip trigger, ordered descope list "
         "(configurations and non-goals), stop/cancel criterion, human gate for envelope raise", "program-orchestration",
         contrib=["engine-architect", "engine-product-management"], tags=t)

    t = "K-PROD-4 K-PROD-7"
    _cap(ed, "ARCH.ORG.human-capacity", "Human capacity model: role roster, SLA per gate class, non-blocking continuation "
         "(gated task parks, agents proceed on independent work packages), batching cadence per milestone, delegate/expiry "
         "rule, gate-wait-time metric; creator-panel sampling per discipline (task completion, time-to-first-asset)",
         "program-orchestration", contrib=["ed-ux-owner-placeholder"] if False else ["developer-experience-docs"], tags=t)

    t = "K-PROD-5"
    _cap(ed, "ARCH.ORG.external-dependencies", "External lead-time register (platform-holder admission and NDAs, devkit "
         "procurement, certification queue slots, pen-test booking, middleware negotiation) with start-by dates derived "
         "from milestone exits, feeding ARCH.ORG.risk", "program-orchestration",
         contrib=["platform-console", "certification-compliance", "ci-cd-automation"], tags=t)

    t = "K-PROD-6"
    _cap(ed, "QA.CERT.authorship-ip", "Outbound authorship and IP: authorship records, model-vendor terms register, licensor "
         "of record, trademark clearance", "certification-compliance", contrib=["program-orchestration"], tags=t)
    ed.cap_set("ARCH.PROD.licensing-model", add_contrib=["certification-compliance"], tags=t)

    # ================================================================ FUTURE
    t = "K-FUTURE-1"
    _append(ed, "C-GPUTIER", "features declare a required capability set (API-neutral feature bits with versioned limits); "
            "tiers are named bundles for configurations and QA matrices.", t)
    ed.doc["skill"]["profiles"]["addons"]["hwrt"] = "Hardware ray tracing required (RT-only lighting paths); tensor support " \
        "only where a feature declares it; no raster fallback is validated in these configurations"

    t = "K-FUTURE-2"
    rd = ed.doc["radar"]
    rd["as_of"] = "2026-09-30"
    rd["max_age_days"] = {"X": 180, "S": 180, "M": 365}
    for e in rd["entries"]:
        e["reviewed"] = "2026-09-30"
    rd["_doc"] += " Each entry carries 'reviewed' (ISO date); check.py fails entries older than max_age_days for their class " \
        "relative to as_of. Promotion triggers should be testable predicates (shipped-title count, API status)."
    ed.note(t, "radar: as_of, max_age_days per class and reviewed dates (evidence_refs typing is not added) (partial)")

    t = "K-FUTURE-3"
    _cap(ed, "PLAT.PAL.cloud-render-host", "Engine as cloud render host: headless GPU rendering, frame capture, low-latency "
         "hardware encode, video/input back-channel, multi-tenant GPU packing", "platform-architect", "M",
         contrib=["frame-orchestration", "gpu-platform-architect", "network-transport", "input-system"], tags=t)
    _radar(ed, "Engine as cloud render host", "M", "platform-architect", ["PLAT.PAL.cloud-render-host"],
           "Cloud gaming services host titles on datacentre GPUs (2020–2026)",
           "Two shipped titles run a first-party render host with published latency budgets",
           "client build streamed by a third-party host (PLAT.PAL.cloud-streaming)")

    t = "K-FUTURE-4"
    ed.cap_set("RND.GEO.splats", mat="X", profiles=["experimental"], tags=t)
    for e in rd["entries"]:
        if "RND.GEO.splats" in e["capabilities"]:
            e["class"] = "X"

    t = "K-FUTURE-5"
    ed.cap_set("NET.ARCH.meshing", mat="X", profiles=["experimental"], tags=t)
    for e in rd["entries"]:
        if "NET.ARCH.meshing" in e["capabilities"]:
            e["class"] = "X"
            e["fallback"] = "NET.SRV.zoning (zoned/instanced multi-server worlds)"
    rd["_doc"] += " Evidence-to-class rule: M requires at least two shipped titles with published postmortems; one " \
        "shipped title or research evidence is X."

    t = "K-FUTURE-6"
    ed.doc["legacy"]["patterns"] = [p if p["id"] != "L73" else {**p, "default_stance":
        "Frame generation is an optional presentation layer, never counted toward latency or simulation budgets; upscaling "
        "is a declared budget input per tier (internal-resolution budget at base rate with the reconstruction mode)"}
        for p in ed.doc["legacy"]["patterns"]]
    _append(ed, "C-BUDGET", "tier records declare the internal-resolution budget and reconstruction mode where the tier "
            "mandates upscaling.", t)

    t = "K-FUTURE-8"
    _cap(ed, "ML.RT.web-backends", "Browser ML backends (WebNN, WebGPU-compute inference)", "ml-inference-runtime", "M",
         contrib=["platform-web"], tags=t)
    _radar(ed, "Browser ML backends", "M", "ml-inference-runtime", ["ML.RT.web-backends"], "WebNN and WebGPU inference (2024–2026)",
           "Two browser engines ship WebNN by default", "remote inference via C-LIVE (ML.RT.local-remote)")
    for tech in ("Volumetric and spatial video", "Light-field and holographic displays"):
        _radar(ed, tech, "S", "render-architect" if "Light" in tech else "media-playback", [],
               "Research and early products", "A shipping title targets it", "flat video / stereoscopic rendering")
        rd["entries"][-1]["non_goal"] = True

    t = "K-FUTURE-9"
    _rename(ed, "CORE.LIFE.language", "; ADR criteria include agent-verifiability and undefined-behaviour class exposure",
            tags=t)
    for e in rd["entries"]:
        if e["tech"].startswith("Memory-safe language components"):
            e["revisit"] += "; agent-authored memory-safety escapes above threshold in C++ modules"
