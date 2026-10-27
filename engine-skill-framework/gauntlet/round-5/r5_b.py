"""Round-5 revision, part B: networking, tools, platform and performance findings
(K-NET-1,4,6..8,10..13,15,16; K-TOOLS-3..6,8,10; K-PERF-2..6,9; K-PLATFORM-1..3,5..8)."""
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "round-3"))
sys.path.insert(0, os.path.join(R, "round-4"))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap, _rename  # noqa: E402
from r4_c import _claim, _gate, _ms  # noqa: E402


def apply(ed):
    # ================================================================ NET
    t = "K-NET-1"
    _append(ed, "C-SHARD", "participant interface (on_migrate_out, on_migrate_in, ghost_border) implemented by replication, "
            "physics, movement, abilities, AI and script state.", t)
    for sid in ("character-movement", "gameplay-systems-toolkit", "ai-behavior-perception"):
        ed.use(sid, "C-SHARD?", tags=t)
    _append(ed, "C-STATECLASS", "migration state class: state handed off across authority boundaries.", t)

    t = "K-NET-4"
    _claim(ed, "community-server-pc", ["min2d", "online", "ugc"], "server", ["pc", "server-host"], None, "M4")

    t = "K-NET-6"
    ed.cap_set("NET.ARCH.distributed-authority", mat="M", add_contrib=["anti-cheat-integrity"],
               name="Per-object ownership transfer & shared authority (eligibility rule: ADR with declared trust tier and "
               "C-INTEGRITY validators on deltas)", tags=t)
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] == "L43":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"NET.ARCH.distributed-authority"})
    _radar(ed, "Distributed and client-owned authority", "M", "network-architect", ["NET.ARCH.distributed-authority"],
           "Shared-authority modes in Unity NGO and Fusion; few competitive titles", "Two shipped competitive titles with "
           "validated client-owned objects", "server-authoritative ownership (NET.ARCH.authority)")

    t = "K-NET-7"
    c = ed.contract("C-NETSESSION")
    ed.contract_set("C-NETSESSION", summary=c["summary"].replace("implemented by replication, prediction-rollback and "
                    "determinism-replay", "implemented by replication and prediction-rollback (determinism-replay supplies "
                    "the snapshot and command catch-up data through prediction-rollback)"), tags=t)

    t = "K-NET-8"
    ed.cap_set("NET.TRANS.web", name="Browser transports: WebTransport datagrams and WebRTC unreliable channels preferred; "
               "WebSocket fallback by ADR", tags=t)
    ed.cap_set("NET.ARCH.async", name="Asynchronous / turn-based backend-mediated play (channel is HTTPS via C-PAL, or "
               "WebSocket in browsers)", tags=t)

    t = "K-NET-10"
    ed.note(t, "docs/06 A5 corrected to X (data and radar)")

    t = "K-NET-11"
    ed.cap_set("NET.SESS.handshake", name="Connect state machine: pre-auth sequence (stateless challenge, crypto, auth ticket, "
               "version window, layout negotiation) owned here, the other rows are its steps; no per-connection state before "
               "the challenge passes (C-NETSESSION conformance case)", tags=t)

    t = "K-NET-12"
    ed.cap_set("NET.SESS.host-mode", name="Hosting modes (dedicated, listen, P2P host, relay-hosted, self-hosted/community "
               "servers); migration in NET.SESS.host-migration", tags=t)

    t = "K-NET-13"
    ed.cap_set("NET.ARCH.budgets", name="Network budgets & scale targets (players, entities, bandwidth) per configuration and "
               "link class (down, up, host uplink share, radio wake cost) keyed to NET.TRANS.simulation trace classes; maximum "
               "rewind window", tags=t)

    t = "K-NET-15"
    _input(ed, "qos-probe-replies", "network-transport", ["online-services-liveops"], "hostile-remote",
           "size/rate/signature limits; spoofable UDP")

    t = "K-NET-16"
    ed.cap_set("NET.PRED.lagcomp", add_contrib=["anti-cheat-integrity", "gameplay-systems-toolkit", "physics-architect"], tags=t)

    # ================================================================ TOOLS
    t = "K-TOOLS-3"
    _claim(ed, "sandbox-2d-tools", ["min2d", "sandbox"], "tools", ["pc"], ["pc"], "M2")
    _claim(ed, "rt-required-3d-tools", ["std3d", "hwrt"], "tools", ["pc"], ["pc", "console"], "M6")
    _claim(ed, "aaa-experimental-tools", ["std3d", "openworld", "online", "aaa", "experimental"], "tools", ["pc"], ["pc"], "M6")

    t = "K-TOOLS-4"
    _cap(ed, "CNT.IMP.sprites-2d", "Layered sprite/animation sources (Aseprite, layered PSD to atlas plus animation tags) and "
         "sprite sheets", "asset-import-interchange", contrib=["render-2d-vector"], tags=t)
    _cap(ed, "CNT.IMP.tilemaps", "Tile editors (Tiled TMX, LDtk, Ogmo) to tilemaps and collision", "asset-import-interchange",
         contrib=["render-2d-vector", "physics-2d"], tags=t)
    _cap(ed, "CNT.COOK.fonts", "Font and MSDF import-cook", "asset-cook-processors", contrib=["text-fonts"], tags=t)
    ed.cap_set("ANM.RT.2d-import", add_contrib=["asset-import-interchange"], tags=t)

    t = "K-TOOLS-5"
    _cap(ed, "NET.TOOL.replication-authoring", "Replication authoring: per-class conditions, priority, relevancy, RPC and "
         "authority annotations, ownership, rollback window and input-delay tuning", "replication",
         contrib=["editor-ui-framework", "network-transport"], tags=t)
    _cap(ed, "NET.TOOL.net-debug", "Network debugging tools (bandwidth attribution, prediction error, session replay views)",
         "replication", contrib=["editor-ui-framework", "network-transport"], tags=t)
    for sid in ("replication", "net-session"):
        ed.use(sid, "C-EDCMD", "C-EDHOST", tool=True, tags=t)

    t = "K-TOOLS-6"
    ed.cap_set("ED.ARCH.pie", add_contrib=["input-system", "audio-architect", "persistence-save", "online-services-liveops",
                                           "ecs-runtime", "hot-reload-iteration"],
               name="Play-in-editor & simulation isolation (no process-global state, sandboxed save profile, emulated services, "
               "input focus/capture and audio isolation)", tags=t)

    t = "K-TOOLS-8"
    _cap(ed, "ML.TOOL.model-assets", "Model asset tools: import (ONNX-class), inspect, quantize, per-backend preview, tolerance "
         "reports", "ml-inference-runtime", contrib=["editor-ui-framework", "asset-import-interchange"], tags=t)
    ed.use("ml-inference-runtime", "C-EDCMD", "C-EDHOST", tool=True, tags=t)

    t = "K-TOOLS-10"
    ed.cap_set("ED.ARCH.process", name="Editor process model: in-process vs out-of-process runtime by ADR, crash isolation "
               "(job semantics belong to ED.ARCH.async-jobs)", tags=t)

    # ================================================================ PERF
    t = "K-PERF-2"
    _gate(ed, "M2", "PRF.GPU.power", "PRF.BENCH.stats")
    ed.note(t, "M2 sustained-state (thermal-soak) mobile gate via PRF.GPU.power; the thermal-signal backend gate is left to "
               "M3 governor (partial)")

    t = "K-PERF-3"
    _cap(ed, "PRF.BENCH.shipping-delta", "Shipping-build smoke benchmark per tier with an overhead line for C-INSTR, hardening "
         "and DRM in C-BUDGET", "perf-benchmarking", contrib=["build-system-toolchains", "security-engineering"], tags=t)
    _gate(ed, "M1", "PRF.BENCH.shipping-delta", "BLD.SYS.dev-surface-exclusion")

    t = "K-PERF-4"
    _gate(ed, "M0", "PRF.BENCH.proxy-metrics", "BLD.CI.bisection")
    _gate(ed, "M1", "PRF.BENCH.lab", "BLD.CI.device-lanes")
    ed.note(t, "per-platform lab gates at M2/M3 are not added (partial)")

    t = "K-PERF-5"
    _append(ed, "C-BUDGET", "XR lines (missed-frame rate, reprojection headroom, compositor deadline margin, motion-to-photon "
            "per device).", t)
    _gate(ed, "M5", "PLAT.XR.reprojection", "PRF.LOAD.pacing-latency")
    ed.cap_set("PRF.LOAD.pacing-latency", add_contrib=["xr-runtime"], tags=t)

    t = "K-PERF-6"
    _gate(ed, "M3", "PRF.CPU.parallel-scaling", "PRF.BENCH.stats")
    _gate(ed, "M3", "PRF.MEM.bandwidth", "PRF.GPU.analysis")
    _gate(ed, "M5", "PRF.BENCH.sim-worst-case", "QA.SIM.mass-agents")
    _gate(ed, "M6", "PRF.PIPE.cook", "PRF.BENCH.stats")
    _gate(ed, "M6", "PRF.METH.model", "PRF.NET.load-analysis")

    t = "K-PERF-9"
    _append(ed, "C-PERF", "budget-waiver record (line, tier, owner, expiry, recovery plan) read by the perf gate; waivers that "
            "cross a milestone need an architect or human signature.", t)

    # ================================================================ PLATFORM
    t = "K-PLATFORM-1"
    for cid, owner in (("PLAT.DESK.backend-slots", "platform-desktop"), ("PLAT.MOB.backend-slots", "platform-mobile"),
                       ("PLAT.WEB.backend-slots", "platform-web")):
        _cap(ed, cid, "OS-specific implementations of registered backend slots (audio endpoint, input, sockets, save storage, "
             "IME/accessibility bridge); the domain skill owns the slot interface", owner,
             contrib=["input-devices-haptics", "audio-architect", "text-fonts", "accessibility", "persistence-save"], tags=t)
    ed.note(t, "slot contracts stay without needs_implementer; the slot rows are the per-platform owners (partial)")

    t = "K-PLATFORM-2"
    _cap(ed, "PLAT.MOB.svc-stores", "Mobile store/service adapters (StoreKit, Play Billing, Game Center, Play Games, Sign in "
         "with Apple)", "platform-mobile", contrib=["platform-services"], tags=t)
    _cap(ed, "PLAT.WEB.svc-portals", "Web-portal SDK adapters", "platform-web", contrib=["platform-services"], tags=t)
    ed.contract_set("C-SVC", needs_implementer=True, tags=t)
    _add(ed, "platform-services", "implements", "C-SVC")
    ed.note(t, "platform-services supplies the null/emulator implementer for every platform; per-store adapters sit in the "
               "platform skills' rows")

    t = "K-PLATFORM-3"
    ed.cap_set("PLAT.PAL.confidential-extensions", name=ed._find_cap("PLAT.PAL.confidential-extensions")[1][1].rstrip(".") +
               "; data-class rules: per-holder sealed partitions for tier/budget numbers, DDC, symbols and captures with a "
               "public envelope and sanitized summaries", tags=t)
    ed.note(t, "BLD.SYS.platform-sdks is not split (partial)")

    t = "K-PLATFORM-5"
    _cap(ed, "PLAT.SRV.gpu-host", "Headless GPU host: offscreen surfaces, container GPU passthrough, driver pinning, hardware "
         "encode", "platform-server-host", contrib=["gpu-platform-architect", "platform-architect"], tags=t)
    ed.cap_set("PLAT.PAL.cloud-render-host", name="Cloud render host policy (implementation in PLAT.SRV.gpu-host)", tags=t)
    ed.note(t, "no new variant or configuration: the capability stays policy-only until a claimed configuration exists (partial)")

    t = "K-PLATFORM-6"
    _cap(ed, "PLAT.DESK.compat-layers", "Proton/Wine ADR (native Linux vs Windows build under a compatibility layer) and a CI "
         "lane", "platform-desktop", contrib=["ci-cd-automation"], tags=t)
    _radar(ed, "Windows server hosts", "S", "platform-server-host", [], "Community servers on Windows PCs use the pc target",
           "A shipped title needs Windows as a fleet host", "pc target for community-hosted servers (community-server-pc)")
    ed.doc["radar"]["entries"][-1]["non_goal"] = True

    t = "K-PLATFORM-7"
    m4 = _ms(ed, "M4")
    m4["exit"] += " A console configuration passes a holder pre-submission or partner review (scheduled from " \
                  "ARCH.ORG.external-dependencies start-by dates); M7 stays the final pass."

    t = "K-PLATFORM-8"
    ed.cap_set("PLAT.XR.mobile-ar", add_contrib=["platform-mobile"], tags=t)
    ed.note(t, "xr-runtime platform tags and the PLAT.XR platform-area check are not added (partial)")
