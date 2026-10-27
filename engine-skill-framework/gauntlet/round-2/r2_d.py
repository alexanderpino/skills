"""Round-2 revision, part D: K-PLATFORM and K-NET findings (PAL implementers, server host, console/NDA, tools target
platforms, netcode families, sessions, server scale-out)."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def _purpose(ed, sid, new, tags):
    ed.skill_set(sid, purpose=new, tags=tags)


def apply(ed):
    cfgs = ed.doc["skill"]["configurations"]

    # ================================================================ PLATFORM
    t = "K-PLATFORM-1"   # seed S06; residual: platform-area token rule (+ selftest) in check.py
    ed.note(t, "check.py: a skill owning PLAT.CON/MOB/WEB/DESK/SRV capabilities must carry that platform tag")

    t = "K-PLATFORM-2 K-ARCH-2"
    ed.note(t, "check.py: needs_implementer contracts are closed per platform of each configuration (+ selftest)")

    t = "K-PLATFORM-3"
    ed.contract_set("C-PAL", needs_implementer=True, tags=t)
    _append(ed, "C-PAL", "interfaces and policy owned by platform-architect; each platform's implementation is a "
            "registered backend implemented by that platform's skill.", t)
    for sid, area, os_name in (("platform-desktop", "PLAT.DESK", "Windows/Linux/SteamOS/macOS"),
                               ("platform-console", "PLAT.CON", "console OS"),
                               ("platform-mobile", "PLAT.MOB", "iOS/Android/visionOS"),
                               ("platform-web", "PLAT.WEB", "browser (WASM)")):
        s = ed.skill(sid)
        s["implements"] = [x for x in s["implements"] if x != "C-RHI"] + ["C-PAL"]
        s["consumes"] = [x for x in s["consumes"] if x.split("@")[0].rstrip("?") != "C-PAL"] + ["C-BASE"]
        ed.cap(f"{area}.pal", f"PAL implementation for {os_name} (C-PAL backend: OS services, windowing, threads, "
               f"clocks, IO, display, power, events)", sid, contrib=["platform-architect"], tags=t)
    s = ed.skill("platform-architect")
    _purpose(ed, "platform-architect", "Platform abstraction layer interfaces and policy (implemented per platform by "
             "the platform experts): OS services, CPU/GPU capability discovery, windowing, process lifecycle, device "
             "database, and evaluation of new targets (web, cloud streaming).", t)

    t = "K-PLATFORM-4 K-NET-2 K-ARCH-7"
    ed.area("PLAT.SRV", "Server host platform", tags=t)
    ed.skill_add(tags=t, id="platform-server-host", name="Server Host Platform", tier="expert",
                 parent="platform-architect", profiles=["all"], kind="runtime", targets=["server", "headless-client"],
                 platforms=["server-host"], workstream="platform", implements=["C-PAL"],
                 purpose="Server-host PAL implementation: containerized Linux and ARM64 hosts, cgroup-aware CPU and "
                         "memory discovery, NUMA on large instances, signal/termination handling, no display or GPU, "
                         "orchestrator health integration at the OS level.",
                 non_responsibilities=[["Server gameplay & lifecycle", "dedicated-server"],
                                       ["Fleet operation", "external:backend"]],
                 expertise=["Linux containers & cgroups", "server CPU topology", "ARM64 server ISAs"],
                 consumes=["C-BASE"])
    ed.cap("PLAT.SRV.pal", "PAL implementation for server hosts (C-PAL backend)", "platform-server-host",
           contrib=["platform-architect"], tags=t)
    ed.cap_move("NET.SRV.host-os", "PLAT.SRV.host-os", tags=t)
    ed.cap_set("PLAT.SRV.host-os", name="Server host OS & container specifics (Linux, ARM64 hosts, huge pages)",
               owner="platform-server-host", rm_contrib=["platform-desktop"], add_contrib=["dedicated-server"], tags=t)
    ed.cap("PLAT.SRV.container-topology", "cgroup-aware CPU/memory discovery feeding PLAT.PAL.cpu-topology",
           "platform-server-host", contrib=["job-system-task-graph"], tags=t)
    s = ed.skill("platform-desktop")
    _purpose(ed, "platform-desktop", s["purpose"].replace(", server host OS", ""), t)

    t = "K-PLATFORM-5"
    ed.skill_add(tags=t, id="rhi-console", name="Console RHI Backends", tier="expert", parent="gpu-platform-architect",
                 profiles=["all"], kind="runtime", targets=["client", "tools"], platforms=["console"],
                 workstream="rendering", implements=["C-RHI"], access="nda:per-platform-holder",
                 instances="one agent per platform-holder family",
                 purpose="Implements C-RHI on each console graphics API from licensed platform-holder documentation; "
                         "owns its validation runs, GPU-crash tooling integration and quirks. Instantiated per "
                         "platform holder so NDA access stays per holder.",
                 non_responsibilities=[["RHI abstraction & capability model", "rhi-core"],
                                       ["Console OS integration", "platform-console"]],
                 expertise=["console GPU APIs (licensed)", "UMA GPU memory", "console GPU debugging tools"],
                 consumes=["C-PAL", "C-SYNC", "C-GPUTIER"])
    ed.cap_move("PLAT.CON.rhi-backends", "RND.RHI.console", tags=t)
    ed.cap_set("RND.RHI.console", name="Console graphics API backends (confidential, per platform holder)",
               owner="rhi-console", tags=t)
    ed.cap("RND.RHI.console-validation", "Console backends: platform validation layers & conformance runs",
           "rhi-console", contrib=["render-validation"], tags=t)
    ed.cap("RND.RHI.console-quirks", "Console backends: GPU crash tooling integration & quirk handling",
           "rhi-console", contrib=["rhi-core", "crash-diagnostics"], tags=t)
    ed.nonresp("platform-console", [["Certification tracking", "certification-compliance"],
                                    ["Console graphics API backends", "rhi-console"]], tags=t)
    s = ed.skill("rhi-core")
    ed.nonresp("rhi-core", [x if x[0] != "Per-API backend code" else
                            ["Per-API backend code", ["rhi-d3d12", "rhi-vulkan", "rhi-metal", "rhi-webgpu", "rhi-console"]]
                            for x in s["non_responsibilities"]], tags=t)

    ed.contract_set("C-RHI", platforms=["pc", "console", "mobile", "web", "xr-standalone"], tags=t)
    s = ed.skill("platform-console")
    s["consumes"] = [x for x in s["consumes"] if x.split("@")[0].rstrip("?") not in ("C-SVC", "C-GPUTIER")]
    s["implements"].append("C-SVC")
    ed.note(t, "platform-console implements its C-SVC slot (console first-party backend) instead of consuming it; "
               "GPU tier mapping moves to rhi-console")

    t = "K-PLATFORM-6"
    ed.skill_set("platform-console", access="nda:per-platform-holder", instances="one agent per platform-holder family",
                 tags=t)
    ed.cap("PLAT.CON.confidential-slots", "Confidential implementations of registered slots (IO/decompression units, "
           "audio endpoints, save storage, crash upload, system keyboard, entitlement SDK) behind public interfaces "
           "owned by domain skills", "platform-console",
           contrib=["async-io-storage", "audio-architect", "persistence-save", "crash-diagnostics", "text-fonts"],
           tags=t)
    _append(ed, "C-ORCH", "access classes per skill (public | nda:<holder>); NDA work routed only to cleared agents.", t)
    ed.note(t, "check.py: console-only skills carry an NDA access class; NDA skills are console-only")

    t = "K-PLATFORM-7"
    for n in ("indie-2d-tools", "standard-3d-tools", "aaa-open-world-online-tools"):
        cfgs[n]["target_platforms"] = {"indie-2d-tools": ["pc", "console", "mobile", "web"],
                                       "standard-3d-tools": ["pc", "console", "mobile"],
                                       "aaa-open-world-online-tools": ["pc", "console", "server-host"]}[n]
        ed.note(t, f"configuration {n}: target_platforms {cfgs[n]['target_platforms']}")
    ed.contract_add("C-TARGETPLAT", 5, "platform-architect", "Target-platform tool modules",
                    "Per-target-platform tool modules loaded by editor, cooker and packager: cook format variants, "
                    "shader backend compiler hook, packager, deploy/launch/debug on device.",
                    requires=["C-COOK"], needs_implementer=True, conformance=True, tags=t)
    for sid in ("platform-desktop", "platform-console", "platform-mobile", "platform-web", "platform-server-host"):
        s = ed.skill(sid)
        s["implements"].append("C-TARGETPLAT")
        if "tools" not in s["targets"]:
            s["targets"].append("tools")
    for sid in ("content-pipeline-architect", "packaging-release-patching"):
        ed.use(sid, "C-TARGETPLAT", tool=True, tags=t)

    t = "K-PLATFORM-8"
    ed.cap_set("PLAT.CON.user-model", name="Console user-model implementation (C-SVC slot)", tags=t)
    ed.cap("PLAT.SVC.user-model", "Platform-user model: user handle, sign-in/out & user-change events, primary-user "
           "rules, guests (all platforms)", "platform-services",
           contrib=["platform-console", "platform-desktop", "platform-mobile", "input-devices-haptics",
                    "persistence-save"], tags=t)
    _append(ed, "C-SVC", "platform-user handle and sign-in/user-change events on every platform.", t)

    t = "K-PLATFORM-9"
    ed.cap("PLAT.XR.runtime-backends", "XR runtime backends: OpenXR, visionOS Compositor Services, console XR SDK "
           "(confidential slot)", "xr-runtime", contrib=["platform-mobile", "platform-console", "rhi-metal"], tags=t)
    s = ed.skill("rhi-metal")
    s["platforms"] = s["platforms"] + ["xr-standalone"]
    ed.note(t, "rhi-metal platforms += xr-standalone")
    _purpose(ed, "platform-mobile", ed.skill("platform-mobile")["purpose"].replace(
        "(incl. Android-based standalone XR)", "(incl. Android-based standalone XR and visionOS app lifecycle)"), t)
    cfgs["xr-console-client"] = {"profiles": ["std3d", "xr"], "target": "client", "platforms": ["console"]}
    ed.note(t, "configuration xr-console-client added")

    t = "K-PLATFORM-10"
    ed.cap_set("PLAT.PAL.device-db", name="Device capability database (single store): device records, driver "
               "deny-lists, hardware → tier keys, remote updates", tags=t)
    ed.cap_set("RND.RHI.driver-policy", name="Driver policy rules evaluated against C-PAL device records (no own "
               "deny-list)", tags=t)
    ed.cap_set("RND.RHI.caps", name="GPU capability detection feeding C-GPUTIER", tags=t)
    ed.cap_set("PLAT.PAL.capability-tiers", name="Platform capability feature query (tier names from "
               "ARCH.REQ.hardware-tiers)", tags=t)
    ed.cap_set("PRF.METH.scalability", name="Scalability policy: knob budgets per tier (tier names from "
               "ARCH.REQ.hardware-tiers; mechanism in runtime-scalability)", tags=t)
    ed.cap_set("ARCH.REQ.hardware-tiers", name="Hardware tier definitions (the only definition of tier names) incl. "
               "server instance classes and refresh-rate classes", tags=t)
    _append(ed, "C-PAL", "key chain: device record → GPU feature tier (C-GPUTIER) + platform capability tier → "
            "performance tier → knob set (C-SCALE).", t)

    t = "K-PLATFORM-11"
    cfgs["lite-3d-portable-console-client"] = {"profiles": ["lite3d"], "target": "client", "platforms": ["console"]}
    ed.note(t, "configuration lite-3d-portable-console-client added")

    t = "K-PLATFORM-12"
    for sid in ("platform-mobile", "platform-console", "platform-web"):
        ed.skill_set(sid, targets=["client", "tools"], tags=t)

    t = "K-PLATFORM-13"
    c = ed.contract("C-PRESENT")
    ed.contract_set("C-PRESENT", summary=c["summary"].replace("(frame generation, XR compositor, cloud encoder)",
                    "(frame generation, XR compositor)"), tags=t)

    t = "K-PLATFORM-14 K-PROD-9"
    ed.cap_set("BLD.CI.devices", name="Device-farm fleet scheduling & pooling", tags=t)
    ed.cap("BLD.CI.device-lanes", "On-device test lanes on attached devkits/phones or cloud device labs",
           "ci-cd-automation", contrib=["functional-automation-soak", "platform-console", "platform-mobile"], tags=t)
    ed.cap_set("BLD.CI.farm", name="Build farm (distributed builds & pooling)", tags=t)
    ed.cap("BLD.CI.artifacts", "Build artifact retention (symbols, bisection, resubmission)", "ci-cd-automation",
           contrib=["crash-diagnostics"], tags=t)

    t = "K-PLATFORM-15"
    ed.cap("INP.ACT.platform-remap", "Integration with OS/store input remapping layers (action-set APIs, system remap "
           "queries, origin → glyph resolution)", "input-system", contrib=["platform-desktop", "platform-console"],
           tags=t)

    t = "K-PLATFORM-16 K-LEGACY-18"
    for e in ed.doc["radar"]["entries"]:
        if e["tech"].startswith("WebGPU backend"):
            e["fallback"] = "Web target limited to WebGPU-capable browsers (no WebGL backend; see non-goal)"
    ed.doc["radar"]["entries"].append({
        "tech": "GLES / WebGL backends", "class": "S", "capabilities": [], "owner": "gpu-platform-architect",
        "non_goal": True, "evidence": "Vulkan/WebGPU coverage of the target device base (device DB share)",
        "revisit": "Device DB shows >10% of a shipping configuration's audience without Vulkan/WebGPU"})
    ed.note(t, "WebGPU fallback reworded; GLES/WebGL recorded as non-goal")

    # ================================================================ NET
    prof = ed.doc["skill"]["profiles"]["addons"]
    prof["online-lockstep"] = "Deterministic lockstep command networking (RTS, sims)"
    prof["online-rollback"] = "Input-exchange rollback networking (fighting, P2P action)"
    prof["online-async"] = "Asynchronous / turn-based backend-mediated play (no real-time transport)"
    prof["online"] = "Server-authoritative real-time multiplayer (replication + prediction)"
    t = "K-NET-4 K-ARCH-12"
    ed.note(t, "add-on profiles online-lockstep / online-rollback / online-async; online = server-authoritative")
    ed.skill_set("network-architect", profiles=["online", "online-lockstep", "online-rollback", "online-async"], tags=t)
    ed.skill_set("network-transport", profiles=["online", "online-lockstep", "online-rollback"], tags=t)
    ed.skill_set("prediction-rollback", profiles=["online", "online-lockstep", "online-rollback"], tags=t)
    ed.contract_set("C-PREDICT", requires=["C-NETLINK", "C-DET", "C-SNAPSHOT", "C-INPUT"], tags=t)
    ed.unuse("prediction-rollback", "C-REP", tags=t)
    ed.use("prediction-rollback", "C-NETLINK", "C-REP?", tags=t)
    ed.cap_set("NET.ARCH.async", owner="online-services-liveops", add_contrib=["network-architect"], tags=t)
    for n in ("rts-2d-massim-client", "rts-3d-massim-client"):
        cfgs[n]["profiles"] = [("online-lockstep" if p == "online" else p) for p in cfgs[n]["profiles"]]
    cfgs["fighting-2d-rollback-client"] = {"profiles": ["min2d", "online-rollback"], "target": "client",
                                           "platforms": ["pc", "console"]}
    cfgs["mobile-async-client"] = {"profiles": ["minimal", "online-async"], "target": "client", "platforms": ["mobile"]}
    ed.note(t, "RTS configurations use online-lockstep; configurations fighting-2d-rollback-client, mobile-async-client")

    t = "K-NET-3 K-NET-6"
    ed.area("NET.SESS", "Network sessions", tags=t)
    ed.skill_add(tags=t, id="net-session", name="Network Sessions", tier="expert", parent="network-architect",
                 profiles=["online", "online-lockstep", "online-rollback"], kind="runtime",
                 targets=["client", "headless-client", "server", "tools"], workstream="online",
                 purpose="The network session lifecycle in every hosting mode (dedicated, listen, P2P host, relay): "
                         "handshake with compatibility and auth, load-gated join, late-join baseline, reconnect within "
                         "a grace window, server-driven travel, host migration, disconnect reasons; turns matchmaking "
                         "results into connections.",
                 non_responsibilities=[["Transport links", "network-transport"], ["State replication", "replication"],
                                       ["Headless server builds & density", "dedicated-server"]],
                 expertise=["connection state machines", "session security", "host migration"],
                 consumes=["C-NETLINK", "C-NET", "C-FRAME", "C-SVC?", "C-LIVE?", "C-WORLD?", "C-REP?"],
                 untrusted_inputs=["auth-tickets", "packets"])
    ed.contract_add("C-NETSESSION", 3, "net-session", "Network session",
                    "Session lifecycle events (connect, join-ready, spawn, reconnect, travel, disconnect with reason), "
                    "host mode, baseline hand-off, auth results.", requires=["C-NETLINK", "C-NET"], conformance=True,
                    tags=t)
    for cid, name, con in [
            ("NET.SESS.handshake", "Connect handshake: compatibility/version check, auth token, capability negotiation",
             ["network-architect"]),
            ("NET.SESS.join", "Load-gated join readiness & spawn hand-off", ["gameplay-architect"]),
            ("NET.SESS.baseline", "Join-in-progress baseline snapshot", ["replication"]),
            ("NET.SESS.reconnect", "Reconnect/rejoin with ownership & state restore in a grace window", []),
            ("NET.SESS.travel", "Server-driven travel with connected clients", ["world-architect"]),
            ("NET.SESS.disconnect", "Disconnect/kick reasons & ban hook", ["anti-cheat-integrity"])]:
        ed.cap(cid, name, "net-session", contrib=con, tags=t)
    ed.cap_move("NET.SRV.listen", "NET.SESS.host-mode", tags=t)
    ed.cap_set("NET.SESS.host-mode", name="Hosting modes (dedicated, listen, P2P host, relay-hosted) & host migration",
               owner="net-session", add_contrib=["dedicated-server"], tags=t)
    ed.cap_move("NET.SRV.auth", "NET.SESS.auth", tags=t)
    ed.cap_set("NET.SESS.auth", name="Auth-ticket & service-identity validation in every host mode",
               owner="net-session", add_contrib=["dedicated-server"], tags=t)
    ed.cap_set("WLD.MODEL.travel", add_contrib=["net-session"], tags=t)
    ed.cap_set("PLAT.SVC.matchmaking", add_contrib=["network-transport", "net-session"], tags=t)
    for sid in ("gameplay-architect",):
        ed.use(sid, "C-NETSESSION?", tags=t)
    ed.use("dedicated-server", "C-NETSESSION", tags=t)
    cfgs["coop-3d-listen-client"] = {"profiles": ["std3d", "online"], "target": "client", "platforms": ["pc", "console"]}
    ed.note(t, "configuration coop-3d-listen-client added")

    t = "K-NET-5 K-ARCH-8 K-PROD-4 K-PROD-5 K-NET-17 K-SEC-13"
    ed.contract_add("C-SERVER", 3, "dedicated-server", "Server host lifecycle",
                    "Host lifecycle (allocate, ready, health, drain, shutdown), instance metadata, per-connection "
                    "budgets and overload state, authenticated admin command surface.",
                    requires=["C-NET", "C-FRAME"], conformance=True, tags=t)
    for cid, name, con in [
            ("NET.SRV.lifecycle", "Server lifecycle for rolling deploys: health/readiness, graceful drain, session "
             "hand-off, fleet-version coexistence", ["network-architect", "online-services-liveops"]),
            ("NET.SRV.admin", "Authenticated admin/GM command surface on shipping servers: RBAC, audit log, rate "
             "limits", ["security-engineering", "anti-cheat-integrity"]),
            ("NET.SRV.overload", "Overload degradation (time dilation, adaptive tick, relevancy throttling)",
             ["replication", "frame-orchestration"]),
            ("NET.SRV.budgets", "Per-connection memory/CPU/RPC quotas & limits on client-triggered work",
             ["replication", "anti-cheat-integrity"])]:
        ed.cap(cid, name, "dedicated-server", contrib=con, tags=t)
    ed.skill_add(tags=t, id="server-scaleout-persistence", name="Server Scale-out & Persistence", tier="expert",
                 parent="network-architect", profiles=["online"], kind="runtime", targets=["server", "tools"],
                 workstream="online",
                 purpose="Multi-server worlds and authoritative persistence: zoning and instancing with player "
                         "hand-off, cross-server messaging and entity migration, seamless meshing (experimental), "
                         "write-behind persistence with leases and live schema migration, idempotent economy "
                         "transactions.",
                 non_responsibilities=[["Headless builds, density & host lifecycle", "dedicated-server"],
                                       ["Backend database operation", "external:backend"],
                                       ["Local save format", "persistence-save"]],
                 expertise=["distributed consistency", "authority transfer", "idempotent transactions"],
                 consumes=["C-NET", "C-REP", "C-WORLD", "C-SER", "C-SERVER", "C-SAVE?"],
                 untrusted_inputs=["transaction-requests"])
    for cid in ("NET.SRV.zoning", "NET.SRV.persistence", "NET.SRV.transactions"):
        ed.cap_set(cid, owner="server-scaleout-persistence", add_contrib=["dedicated-server"], tags=t)
    ed.cap_set("NET.ARCH.meshing", owner="server-scaleout-persistence", add_contrib=["network-architect"], tags=t)
    ed.cap("NET.SRV.cross-server", "Cross-server messaging & entity/player hand-off", "server-scaleout-persistence",
           contrib=["replication", "world-architect"], tags=t)
    ed.cap_set("WLD.PART.sim-tiers", name="Off-bubble simulation tiers (abstract/statistical sim, promotion/demotion)",
               tags=t)
    ed.contract_add("C-SHARD", 3, "server-scaleout-persistence", "Multi-server authority",
                    "Region/cell → server ownership map, entity migration protocol, authority transfer, cross-boundary "
                    "relevancy, cross-server messages.", requires=["C-REP", "C-WORLD", "C-NET"], conformance=True,
                    tags=t)
    ed.contract_add("C-SRVDATA", 3, "server-scaleout-persistence", "Server persistence & transactions",
                    "Persistent records with leases and write-behind, idempotent transactions, schema migration hooks.",
                    requires=["C-SER", "C-NET"], conformance=True, tags=t)
    for sid in ("gameplay-architect", "persistence-save", "voxel-worlds", "anti-cheat-integrity"):
        ed.use(sid, "C-SRVDATA?", tags=t)
    ed.use("dedicated-server", "C-SHARD?", tags=t)
    ed.use("replication", "C-SHARD?", tags=t)
    s = ed.skill("dedicated-server")
    _purpose(ed, "dedicated-server", "Headless server builds and stripping, host lifecycle (C-SERVER) for rolling "
             "deploys, tick cost and multi-instance density, overload degradation, per-connection budgets, the "
             "authenticated admin surface, fleet orchestration boundary and server observability.", t)
    s["untrusted_inputs"] = sorted(set(s.get("untrusted_inputs") or []) | {"admin-commands"})
    ed.nonresp("dedicated-server", [["Fleet operation (outside engine scope)", "external:backend"],
                                    ["Server logging substrate", "observability-telemetry"],
                                    ["Sessions & hosting modes", "net-session"],
                                    ["Zoning, persistence & transactions", "server-scaleout-persistence"]], tags=t)
    ed.cap_set("NET.SRV.orchestration", rm_contrib=["platform-services"], add_contrib=["online-services-liveops"],
               tags=t)
    ed.cap("PLAT.SVC.admission", "Login queue & capacity admission boundary", "online-services-liveops",
           contrib=["net-session"], tags=t)

    t = "K-NET-7"
    for sid in ("platform-services", "online-services-liveops"):
        ed.skill(sid)["implements"].append("C-NETLINK")
    _append(ed, "C-NETLINK", "platform-SDK transports (Steam/EOS/console relays) register as backends implemented by "
            "platform-services and online-services-liveops.", t)
    ed.note(t, "platform-services, online-services-liveops implement C-NETLINK (SDK transports)")

    t = "K-NET-8 K-TEST-2"
    ed.cap_set("NET.ARCH.validation", name="Netcode oracle scenarios & acceptance thresholds (co-signed by "
               "simulation-validation per QA.AGENT.oracle-change-control)", add_contrib=["simulation-validation"],
               tags=t)
    ed.cap_set("QA.SIM.netsim", name="Deterministic single-process network-simulation runner, metrics & tolerance "
               "store", tags=t)
    ed.cap_set("QA.FUNC.network", name="Multi-client bot harness & scripted network sessions", tags=t)
    ed.cap_set("NET.TRANS.simulation", name="Network link conditioner seam (latency, loss, jitter)", tags=t)

    t = "K-NET-9"
    ed.cap("PLAT.SVC.xplat-social", "Cross-platform friends, parties, presence & invites via backend; reconciliation "
           "with first-party social, privileges and blocks", "online-services-liveops",
           contrib=["platform-services", "certification-compliance"], tags=t)
    _append(ed, "C-LIVE", "cross-platform parties and presence.", t)
    ed.nonresp("network-architect", [["Transport", "network-transport"], ["Replication mechanics", "replication"],
                                     ["Matchmaking services", "online-services-liveops"]], tags="K-ARCH-14")
    ed.nonresp("network-transport", [["What is replicated", "replication"],
                                     ["Relay service operation", "external:backend"]], tags="K-ARCH-14")

    t = "K-NET-11"
    ed.use("replication", "C-FRAME", "C-TASK", tags=t)
    ed.cap("NET.REP.parallel", "Parallel per-connection packet building with shared per-object serialization",
           "replication", tags=t)

    t = "K-NET-12"
    ed.cap("PRF.NET.latency", "End-to-end networked latency accounting (input → server tick → client display)",
           "online-performance", contrib=["network-architect", "frame-orchestration"], tags=t)
    for c in ed.doc["cross"]["concerns"]:
        if c["concern"].lower().startswith("latency"):
            c["obligation"] = c["obligation"].rstrip(".") + "; declare the network latency contribution (reviewed " \
                              "with network-architect)."
            ed.note(t, "crosscutting latency: network contribution")

    t = "K-NET-14"
    ed.cap_set("PLAT.SVC.voice-text", name="Voice & text chat end to end: path selection (service vs game transport), "
               "channels, privileges, mute/block", tags=t)
    ed.cap("PLAT.SVC.voice-moderation", "Voice reporting capture & retention for moderation",
           "online-services-liveops", contrib=["certification-compliance", "security-engineering"], tags=t)
    ed.cap("AUD.DSP.voice-jitter", "Voice jitter buffer, packet-loss concealment & codec", "audio-dsp-mixing",
           contrib=["network-transport"], tags=t)
    ed.cap("AUD.SPAT.proximity-voice", "Positional/proximity voice", "spatial-audio-acoustics",
           contrib=["replication", "online-services-liveops"], tags=t)
    s = ed.skill("audio-dsp-mixing")
    s["untrusted_inputs"] = sorted(set(s.get("untrusted_inputs") or []) | {"voice-streams"})

    t = "K-NET-16"
    ed.cap("NET.TRANS.web-server", "Server-side browser transport endpoints & certificate handling",
           "network-transport", contrib=["dedicated-server"], tags=t)
    cfgs["indie-2d-online-web-client"] = {"profiles": ["min2d", "online"], "target": "client", "platforms": ["web"]}
    ed.note(t, "configuration indie-2d-online-web-client added")

    t = "K-NET-18"
    for k in ed.doc["critic"]["critics"]:
        if k["id"] == "K-NET":
            for sid in ("vehicle-physics", "gameplay-systems-toolkit", "animation-architect", "animation-runtime",
                        "voxel-worlds", "cinematics-sequencer", "determinism-replay", "input-system",
                        "editor-architect", "functional-automation-soak", "simulation-validation", "net-session",
                        "server-scaleout-persistence"):
                if sid not in k["scope"]:
                    k["scope"].append(sid)
    ed.note(t, "K-NET scope extended")

    t = "K-NET-19"
    ed.cap("NET.TRANS.l4s", "L4S low-latency congestion signalling", "network-transport", "X", tags=t)
    ed.cap("NET.REP.moq-spectator", "Media-over-QUIC spectator/broadcast streams", "replication", "X", tags=t)
    ed.cap("XC.SEC.behavioral-detection", "Server-side behavioral / ML cheat detection from telemetry",
           "anti-cheat-integrity", "M", contrib=["observability-telemetry", "ml-inference-runtime"], tags=t)
    ed.doc["radar"]["entries"] += [
        {"tech": "L4S low-latency congestion signalling", "class": "X", "capabilities": ["NET.TRANS.l4s"],
         "owner": "network-transport", "evidence": "RFC 9330–9332", "revisit": "Deployed on two major access networks",
         "fallback": "Standard congestion control"},
        {"tech": "Media-over-QUIC spectator streams", "class": "X", "capabilities": ["NET.REP.moq-spectator"],
         "owner": "replication", "evidence": "IETF MoQ drafts", "revisit": "RFC + CDN support",
         "fallback": "Delayed spectator replication"},
        {"tech": "Behavioral / ML cheat detection", "class": "M", "capabilities": ["XC.SEC.behavioral-detection"],
         "owner": "anti-cheat-integrity", "evidence": "Shipped server-side detection in major shooters",
         "revisit": "Published false-positive rates", "fallback": "Rule-based server validation"}]
    ed.use("anti-cheat-integrity", "C-ML?", tags=t)
    ed.note(t, "radar += L4S, MoQ, behavioral detection")

    t = "K-NET-20"   # seed S06; residual: a console-only online configuration
    cfgs["online-3d-console-client"] = {"profiles": ["std3d", "online"], "target": "client", "platforms": ["console"]}
    ed.note(t, "configuration online-3d-console-client added")
