"""Round-3 revision, part D: rendering, simulation and networking findings
(K-RENDER-3..6,8..12; K-SIM-5..7,9..14; K-NET-1..15). Seed hits (RENDER-1/2/7, SIM-1/3) are not revisited."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def _add(ed, sid, key, *items):
    s = ed.skill(sid)
    s[key] = sorted(set(s.get(key) or []) | set(items))


def _unt(ed, sid, *ids):
    _add(ed, sid, "untrusted_inputs", *ids)


def _input(ed, iid, owner, parsers, trust, limits, extra_fuzz=True):
    ed.doc["untrusted"]["inputs"].append({"id": iid, "validating_owner": owner, "parser_owners": list(parsers),
                                          "trust": trust, "mode": "harness", "limits": limits})
    for sid in [owner] + list(parsers):
        _unt(ed, sid, iid)
    if extra_fuzz:
        _add(ed, "robustness-fuzzing", "fuzz_targets", iid)


def _radar(ed, tech, cls, owner, caps, evidence, revisit, fallback):
    ed.doc["radar"]["entries"].append({"tech": tech, "class": cls, "owner": owner, "capabilities": caps,
                                       "evidence": evidence, "revisit": revisit, "fallback": fallback})


def _config(ed, name, profiles, target, platforms, target_platforms=None, milestone=None):
    cfg = {"profiles": profiles, "target": target, "platforms": platforms}
    if target_platforms:
        cfg["target_platforms"] = target_platforms
    ed.doc["skill"]["configurations"][name] = cfg
    if milestone:
        import r3_z
        for row in r3_z.LADDER:
            if row[0] == milestone:
                row[2].append(name)


def apply(ed):
    # ============================================================ RENDER
    t = "K-RENDER-3"
    ed.contract_add("C-VFX", 3, "vfx-particles", "Effect instances & data-source bindings",
                    "Batched effect-instance requests with pooled handles (spawn, attach, parameterize, stop), user "
                    "parameters, event payloads, data-source bindings (deformation streams, C-PHYS contacts, C-ENV "
                    "fields), significance/budget class and determinism class.", requires=["C-RSCENE"],
                    conformance=True, oracle_author="functional-automation-soak", tags=t)
    for sid in ("gameplay-systems-toolkit", "cinematics-sequencer", "destruction-fracture", "animation-runtime",
                "atmosphere-weather", "ui-architect"):
        ed.use(sid, "C-VFX?", tags=t)
    ed.use("vfx-particles", "C-ANIM?", tags=t)

    t = "K-RENDER-4"
    ed.use("material-system", "C-VT", tags=t)
    for sid in ("geometry-pipeline", "translucency-decals", "vfx-particles"):
        ed.use(sid, "C-VT?", tags=t)
    ed.use("texture-streaming-vt", "C-RSCENE", "C-INSTANCES?", "C-VIEW?", tags=t)
    _append(ed, "C-VT", "shader-side VT sampling and feedback interface for material-generated code.", t)

    t = "K-RENDER-5"
    ed.contract_set("C-RTAS", layer=3, requires=["C-RG", "C-GPUMEM"], tags=t)
    ed.use("ray-tracing-infrastructure", "C-RG", tags=t)
    ed.note(t, "C-RTAS moves to layer 3: acceleration-structure builds are graph-scheduled producers "
               "(RND.GRAPH.external-work), so the contract requires C-RG")

    t = "K-RENDER-6"
    ed.contract_add("C-PTREF", 3, "path-tracing", "Reference render service",
                    "Reference render request (scene snapshot, view, convergence criterion, seed, AOVs) and converged, "
                    "undenoised output with a per-pixel variance estimate; shares no sampling code with the real-time "
                    "lighting modules.", requires=["C-RSCENE", "C-MATIF"], conformance=True,
                    oracle_author="render-validation", tags=t)
    ed.use("render-validation", "C-PTREF?", tags=t)
    ed.use("cinematics-sequencer", "C-PTREF?", tags=t)
    for cid in ("C-LIGHT", "C-TEMPORAL"):
        ed.unuse("path-tracing", cid, tags=t)
        ed.use("path-tracing", cid + "?@C-PTREF" if False else cid + "?", tags=t)
    ed.note(t, "independence: path-tracing vs direct-lighting-shadows/global-illumination share no sampling code "
               "(recorded in crosscutting independence pairs by ARCH.ORG.independence)")

    t = "K-RENDER-8"
    ed.cap_set("RND.RECON.denoise", name="Spatiotemporal denoising (established)", mat="E", tags=t)
    ed.cap("RND.RECON.ml-denoise", "ML / joint ray-reconstruction denoising", "reconstruction-upscaling", "M",
           contrib=["global-illumination", "ml-inference-runtime"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if e["tech"] == "ML denoising & ray reconstruction":
            e["capabilities"] = ["RND.RECON.ml-denoise"]
            e["fallback"] = "RND.RECON.denoise (spatiotemporal denoisers)"

    t = "K-RENDER-9"
    for e in ed.doc["radar"]["entries"]:
        if "RND.SHADER.autodiff" in e["capabilities"] and e["tech"] != "In-shader neural evaluation & differentiable shaders":
            e["fallback"] = "hand-derived gradients or finite differences in tool code"
        if e["tech"] == "In-shader neural evaluation & differentiable shaders":
            e["evidence"] = "API-neutral matrix/tensor intrinsics: DXIL linear algebra, Vulkan cooperative " \
                            "matrix/vector, Metal tensor operations (2025–2026 previews)"
            e["revisit"] = "Two shipping backends expose the same matrix intrinsic set in retail drivers"
            if "RND.SHADER.autodiff" in e["capabilities"]:
                e["capabilities"] = [c for c in e["capabilities"] if c != "RND.SHADER.autodiff"]

    t = "K-RENDER-10"
    ed.doc["legacy"]["patterns"] += [
        {"id": "L58", "pattern": "Display-referred / LDR effect pipeline", "detection": "bloom, DOF or motion blur after "
         "tonemapping; 8-bit intermediate targets on HDR-capable tiers",
         "default_stance": "Scene-referred linear HDR chain with a single output transform; only grain, dithering and "
                           "UI-safe sharpening after it", "justification_owner": "post-color-hdr",
         "stance_capabilities": ["RND.POST.color", "RND.POST.effects"]},
        {"id": "L59", "pattern": "Geometry shaders, HW tessellation and stream-out pipelines on capable tiers",
         "detection": "GS/HS/DS stages or stream-out in material or LOD paths",
         "default_stance": "Mesh shaders or compute expansion; cluster/displacement paths on GPU-driven tiers",
         "justification_owner": "geometry-pipeline", "stance_capabilities": ["RND.GEO.mesh-shaders", "RND.LOD.displacement"]}]
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] == "L29":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"RND.SHADER.precache", "RND.RHI.pso"})

    t = "K-RENDER-11"
    ed.cap("RND.TEX.transcode", "Load-time transcoding from supercompressed universal formats (KTX2/UASTC/ETC1S) to "
           "device formats", "texture-streaming-vt", contrib=["platform-web", "asset-cook-processors"], tags=t)
    ed.note(t, "transcoder input is covered by the existing assets/user-images entries (RND.TEX.runtime-decode)")

    t = "K-RENDER-12"
    for c in ed.doc["critic"]["critics"]:
        if c["id"] == "K-RENDER":
            c["scope"] = sorted(set(c["scope"]) | {"world-editor-viewport", "visual-debugging-tools", "text-fonts"})
    ed.note(t, "K-RENDER scope += world-editor-viewport, visual-debugging-tools, text-fonts")

    # ============================================================ SIM
    t = "K-SIM-5"
    ed.cap("PHY.ARCH.debug-capture", "Physics frame capture (bodies, contacts, queries, islands) on client, headless "
           "and server builds; compiled out of shipping", "physics-architect",
           contrib=["determinism-replay", "visual-debugging-tools"], tags=t)
    _append(ed, "C-REPLAY", "physics-debug stream (bodies, contacts, queries).", t)
    ed.cap_set("PHY.TOOL.visual-debugger", name="Physics visual debugger (viewer for PHY.ARCH.debug-capture)", tags=t)
    ed.use("physics-tools", "C-REPLAY", tags=t)

    t = "K-SIM-6"
    ed.cap("PHY.ARCH.persistence", "Physics state dehydrate/rehydrate on cell deactivation and save (moved props, sleep, "
           "broken joints, fracture state)", "physics-architect",
           contrib=["persistence-save", "world-architect", "destruction-fracture"], tags=t)
    ed.use("physics-architect", "C-SAVE?", "C-WORLD?", tags=t)
    ed.use("destruction-fracture", "C-WORLD?", "C-SAVE?", "C-SNAPSHOT?", "C-SIGNIF?", tags=t)

    t = "K-SIM-7"
    ed.cap("CORE.MATH.fixed-point", "Fixed-point numerics for cross-platform lockstep and rollback", "math-simd-numerics",
           contrib=["determinism-replay"], tags=t)
    ed.cap("PHY.ARCH.fixed-point-backend", "Fixed-point physics backend option", "physics-architect",
           contrib=["physics-2d", "rigid-body-dynamics"], tags=t)
    ed.cap_set("CORE.MATH.deterministic", mat="M", tags=t)
    _radar(ed, "Cross-platform bit-reproducible float math", "M", "math-simd-numerics", ["CORE.MATH.deterministic"],
           "Same-binary determinism is established; cross-ISA/compiler reproducibility of floats is not (A4)",
           "Two shipped titles run mixed-platform lockstep on float math without desync",
           "CORE.MATH.fixed-point (fixed-point numerics) or same-binary determinism")

    t = "K-SIM-9"
    ed.nonresp("voxel-worlds", [x for x in ed.skill("voxel-worlds")["non_responsibilities"]
                                if "tructural" not in x[0]] +
               [["Structural integrity & collapse", "destruction-fracture"]], tags=t)

    t = "K-SIM-10"
    for cid, name, owner, contrib in (
            ("QA.SIM.collision", "Collision robustness runs (CCD tunnelling, degenerate GJK/EPA inputs, query "
             "correctness vs brute force)", "simulation-validation", ["collision-detection"]),
            ("QA.SIM.destruction", "Destruction validation runs (determinism, debris budgets, replicated consistency)",
             "simulation-validation", ["destruction-fracture"]),
            ("QA.SIM.fluids-fields", "Fluid and field simulation runs (conservation, stability, desync lanes)",
             "simulation-validation", ["fluid-simulation", "systems-simulation"])):
        ed.cap(cid, name, owner, contrib=contrib, tags=t)

    t = "K-SIM-11"
    _input(ed, "runtime-collision-geometry", "collision-detection", ["voxel-worlds", "modding-ugc"], "hostile-remote",
           "triangle count/extents/degeneracy/rebuild time per tick", )

    t = "K-SIM-12"
    ed.cap_set("PHY.DEST.runtime", name="Pre-fractured destruction & debris management", tags=t)
    ed.cap("PHY.DEST.procedural", "Runtime procedural fracture at impact time at scale", "destruction-fracture", "M", tags=t)
    _radar(ed, "Runtime procedural fracture at scale", "M", "destruction-fracture", ["PHY.DEST.procedural"],
           "Pre-fractured destruction is established; impact-time fracture at scale is research-grade",
           "A shipped title fractures at impact within the debris budget on consoles",
           "PHY.DEST.runtime (pre-fractured assets)")

    t = "K-SIM-13"
    ed.cap("ANM.IK.learned-physics", "Physically simulated characters driven by learned (RL) policies",
           "ik-procedural-animation", "X", contrib=["rigid-body-dynamics", "ml-inference-runtime"],
           profiles=["experimental"], tags=t)
    ed.use("ik-procedural-animation", "C-ML?", tags=t)
    _radar(ed, "Learned physics-based character control", "X", "ik-procedural-animation", ["ANM.IK.learned-physics"],
           "Research and early middleware; no shipped engine feature", "A shipped title uses a learned physics policy",
           "ANM.IK.physical (active ragdoll with PD motors)")

    t = "K-SIM-14"
    for c in ed.doc["critic"]["critics"]:
        if c["id"] == "K-SIM":
            c["scope"] = sorted(set(c["scope"]) | {"gameplay-systems-toolkit", "navigation-pathfinding"})
            c["checks"] = c["checks"] + ["fixed-step only; sub-rates declared",
                                         "snapshot/resim participation and cost declared",
                                         "C-SIGNIF tier-transition handlers declared"]
    ed.note(t, "K-SIM scope and checks extended")

    # ============================================================ NET
    t = "K-NET-1"
    ed.contract_add("C-HOSTAUTH", 3, "net-session", "Host authority services",
                    "Per-connection quotas and budgets, overload state and degradation signals, kick/ban and the "
                    "host-local admin surface; available in every host mode (dedicated, listen, P2P host, rollback and "
                    "lockstep hosts).", requires=["C-NETLINK", "C-NET"], conformance=True,
                    oracle_author="simulation-validation", tags=t)
    ed.cap_move("NET.SRV.budgets", "NET.SESS.budgets", tags=t)
    ed.cap_set("NET.SESS.budgets", owner="net-session", add_contrib=["dedicated-server", "replication"], tags=t)
    ed.cap_move("NET.SRV.overload", "NET.SESS.overload", tags=t)
    ed.cap_set("NET.SESS.overload", owner="net-session", add_contrib=["dedicated-server"], tags=t)
    c = ed.contract("C-SERVER")
    ed.contract_set("C-SERVER", summary="Host process and fleet lifecycle (allocate, ready, health, drain, shutdown), "
                    "instance metadata, authenticated admin command surface; per-connection budgets and overload live in "
                    "C-HOSTAUTH.", requires=c["requires"] + ["C-HOSTAUTH"], tags=t)
    ed.use("dedicated-server", "C-HOSTAUTH", tags=t)
    for sid in ("replication", "prediction-rollback", "gameplay-architect"):
        ed.use(sid, "C-HOSTAUTH?", tags=t)

    t = "K-NET-2"
    ed.cap("NET.PRED.presentation", "Rollback/prediction-aware presentation: predicted cosmetic event keys, dedup on "
           "resim, cancel/fade of mispredicted cosmetics, late-confirm offset playback", "prediction-rollback",
           contrib=["vfx-particles", "audio-content-runtime", "animation-runtime", "input-devices-haptics"], tags=t)
    for sid in ("vfx-particles", "audio-content-runtime", "animation-runtime"):
        ed.use(sid, "C-PREDICT?", tags=t)

    t = "K-NET-3"
    ed.doc["skill"]["profiles"]["addons"]["persistent-world"] = "Persistent multi-server worlds (zoning, meshing, " \
        "hand-off, leases, transactions)"
    ed.skill_set("server-scaleout-persistence", profiles=["persistent-world"], tags=t)
    for name in ("aaa-open-world-online-client", "aaa-open-world-online-server", "aaa-open-world-online-tools",
                 "sandbox-online-server"):
        ed.doc["skill"]["configurations"][name]["profiles"].append("persistent-world")

    t = "K-NET-4"
    ed.cap_move("NET.DBG.profiler", "NET.DBG.profiler", tags=t)
    ed.cap_set("NET.DBG.profiler", name="Network profiler: channel attribution with registered categories, bandwidth "
               "per connection/entity/property", owner="network-transport",
               add_contrib=["replication", "prediction-rollback"], tags=t)
    ed.cap("NET.DBG.prediction-viz", "Prediction-error and rollback visualization", "prediction-rollback",
           contrib=["visual-debugging-tools"], tags=t)
    ed.cap("NET.PRED.spectator", "Input-stream spectators for lockstep and rollback games", "prediction-rollback",
           contrib=["determinism-replay"], tags=t)
    ed.skill_set("online-performance", profiles=["online", "online-lockstep", "online-rollback"], tags=t)
    ed.use("online-performance", "C-REP?", "C-PREDICT?", tags=t)

    t = "K-NET-5"
    _config(ed, "fighting-2d-rollback-tools", ["min2d", "online-rollback"], "tools", ["pc"], ["pc", "console"], "M2")
    _config(ed, "rts-massim-lockstep-tools", ["min2d", "massim", "online-lockstep"], "tools", ["pc"], ["pc"], "M4")
    ed.cap_set("ED.ARCH.pie-net", name="Multiplayer play-in-editor & network emulation",
               add_contrib=["net-session", "prediction-rollback", "network-transport", "dedicated-server"], tags=t)
    ed.cap("NET.PRED.sync-test", "Sync-test sessions: forced rollback and state-hash comparison in CI and dev builds",
           "prediction-rollback", contrib=["determinism-replay"], tags=t)

    t = "K-NET-6"
    ed.cap("NET.SESS.content-set", "Session content-set agreement: mods, DLC and content versions checked at join; "
           "match, download, subset play or refuse", "net-session",
           contrib=["modding-ugc", "packaging-release-patching", "platform-services"], tags=t)
    _append(ed, "C-NETSESSION", "content-set agreement results.", t)
    ed.use("modding-ugc", "C-NETSESSION?", tags=t)
    _input(ed, "server-pushed-content", "modding-ugc", ["net-session"], "hostile-remote",
           "size/type allow-list; signature required; sandboxed load")

    t = "K-NET-7"
    ed.cap("NET.REP.compat", "Wire-level replicated-schema compatibility: layout hashes, per-connection layout "
           "negotiation, tolerant decode", "replication", contrib=["serialization-schema", "network-architect"], tags=t)
    _append(ed, "C-REP", "layout negotiation within the compatibility window.", t)
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] == "L45":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"NET.REP.compat"})

    t = "K-NET-8"
    ed.cap("NET.ARCH.async-validation", "Deterministic re-simulation of submitted async results (PvP, leaderboards) in a "
           "headless backend worker", "determinism-replay", contrib=["online-services-liveops", "anti-cheat-integrity"],
           tags=t)
    _config(ed, "mobile-async-validator", ["minimal", "online-async"], "headless-client", ["server-host"], None, "M2")
    ed.note(t, "XC.SEC.score-integrity is fulfilled by NET.ARCH.async-validation for async games")
    ed.cap_set("XC.SEC.score-integrity", add_contrib=["determinism-replay"], tags=t)

    t = "K-NET-9"
    ed.use("dedicated-server", "C-LIVE?", tags=t)
    ed.cap_set("NET.SESS.host-mode", name="Hosting modes (dedicated, listen, P2P host, relay-hosted, self-hosted/"
               "community servers) & host migration", tags=t)
    ed.cap("NET.SESS.server-browser", "Server registration, listing and query via backend, master server or LAN; auth "
           "without a first-party backend", "net-session", contrib=["online-services-liveops", "network-transport"], tags=t)

    t = "K-NET-10"
    _input(ed, "client-rpcs", "replication", [], "hostile-remote", "per-RPC rate, argument bounds, authority check")
    ed.use("replication", "C-INTEGRITY?", tags=t)
    _append(ed, "C-REP", "per-RPC validator and authority declaration.", t)

    t = "K-NET-11"
    ed.cap_set("NET.TRANS.web", name="Browser transports: WebTransport datagrams and WebRTC unreliable channels "
               "preferred; WebSocket fallback for async/turn-based play or by ADR", tags=t)
    ed.cap_set("NET.TRANS.quic", name="QUIC/WebTransport as native transport", tags=t)
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] == "L42":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"NET.TRANS.web"})

    t = "K-NET-12"
    ed.cap("NET.TRANS.qos-probe", "Client latency and loss probing to regions, data centres and relays (matchmaking "
           "input)", "network-transport", contrib=["online-services-liveops"], tags=t)

    t = "K-NET-13"
    ed.use("prediction-rollback", "C-NETSESSION", tags=t)
    ed.cap_set("NET.SESS.baseline", name="Join-in-progress baseline: replicated snapshot or C-SNAPSHOT + command "
               "catch-up", add_contrib=["prediction-rollback", "determinism-replay"], tags=t)
    ed.cap_set("NET.SESS.reconnect", add_contrib=["prediction-rollback", "determinism-replay"], tags=t)

    t = "K-NET-14"
    ed.cap("NET.SESS.local-players", "Several local players per connection: per-player identity/auth, sub-connections "
           "and per-player command streams", "net-session",
           contrib=["gameplay-architect", "platform-services", "input-system"], tags=t)

    t = "K-NET-15"
    for c in ed.doc["critic"]["critics"]:
        if c["id"] == "K-NET":
            c["scope"] = sorted(set(c["scope"]) | {"physics-architect", "rigid-body-dynamics", "physics-2d",
                                                   "frame-orchestration", "crowd-simulation", "modding-ugc",
                                                   "platform-web", "audio-dsp-mixing", "platform-server-host",
                                                   "online-performance"})
    ed.note(t, "K-NET scope extended by ten netcode-critical skills")
