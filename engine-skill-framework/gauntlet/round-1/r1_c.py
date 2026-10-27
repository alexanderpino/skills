"""G1 round-1 revision, part C: networking, gameplay, UI/a11y, editor & content, platform."""

ALL_T = ["client", "headless-client", "server", "tools"]
CLIENT_TOOLS = ["client", "tools"]


def networking(ed):
    na, nt, rp, pr, ds = "network-architect", "network-transport", "replication", "prediction-rollback", "dedicated-server"
    ed.contract_set("C-NET", requires=["C-FRAME", "C-ID"], tags="K-NET-2 K-ARCH-3",
                    name="Netcode model & authority policy",
                    summary="Netcode model per game type, authority model, net tick and time policy, compatibility "
                            "window and handshake policy.")
    ed.contract_add("C-NETLINK", 2, nt, "Network links & sessions",
                    "Sessions, channels, reliability/ordering classes, send budgets, link statistics, connection "
                    "events; used by replication, voice, rollback input exchange and telemetry streams.",
                    ["C-PAL", "C-TASK"], tags="K-NET-2")
    ed.contract_add("C-REP", 3, rp, "Replication",
                    "Replicated state declaration, relevancy hooks, RPCs, net IDs, batch registration, replay and "
                    "spectator streams.", ["C-NETLINK", "C-SER", "C-ID"], tags="K-NET-2")
    ed.contract_add("C-PREDICT", 3, pr, "Prediction & rollback",
                    "Predicted/rollback-able state registration, tick-stamped input history, resimulation hooks, "
                    "rewind queries, cosmetic-effect suppression during resim.",
                    ["C-REP", "C-DET", "C-SNAPSHOT", "C-INPUT"], tags="K-NET-2 K-NET-3 K-NET-5")
    ed.skill_set(na, consumes=["C-FRAME", "C-SER", "C-DET", "C-ID", "C-ECS?"], tags="K-ARCH-3")
    ed.skill_set(nt, consumes=["C-PAL", "C-TASK", "C-SVC?", "C-LIVE?"], tags="K-NET-2")
    ed.skill_set(rp, consumes=["C-NET", "C-NETLINK", "C-ECS?", "C-SER", "C-ID", "C-SPATIAL", "C-WORLD?", "C-SIGNIF?",
                               "C-REPLAY?"], tags="K-NET-13 K-ARCH-9")
    ed.skill_set(pr, consumes=["C-NET", "C-REP", "C-DET", "C-SNAPSHOT", "C-INPUT", "C-ECS?", "C-PHYS?", "C-ANIM?"],
                 tags="K-NET-3 K-NET-4 K-GAMEPLAY-3 K-GAMEPLAY-8")
    ed.skill_set(ds, targets=["server", "tools"], consumes=["C-NET", "C-NETLINK", "C-FRAME", "C-SVC?", "C-LIVE", "C-WORLD?"],
                 tags="K-NET-13 K-NET-7")
    for cid, name, owner, contrib, mat, t in [
            ("NET.TRANS.web", "Browser transports (WebSocket, WebRTC data channels; WebTransport where available)",
             nt, ["platform-web"], "E", "K-NET-15 K-COMPLETE-3"),
            ("NET.TRANS.voice", "Game-transport voice path (P2P/server-relayed)", nt, ["audio-dsp-mixing"], "E", "K-NET-10 K-COMPLETE-5"),
            ("NET.TRANS.dos", "Anti-amplification handshake, stateless challenges, rate limiting, relay-shielded addressing",
             nt, ["security-engineering", ds], "E", "K-NET-14 K-QUALITY-17"),
            ("NET.TRANS.platform-requirements", "Platform networking requirements (IPv6-only/NAT64, network change & "
             "migration, connectivity state)", nt, ["platform-console", "platform-mobile"], "E", "K-PLATFORM-18"),
            ("NET.REP.spectator", "Spectator/broadcast clients with delay & observer relevancy", rp, [], "E", "K-NET-16 K-COMPLETE-13"),
            ("NET.REP.killcam", "Short-horizon instant replay / kill-cam", rp, ["prediction-rollback"], "E", "K-COMPLETE-13"),
            ("NET.PRED.input-commands", "Tick-stamped networked input commands, redundancy, buffering, server-side "
             "validation hooks", pr, ["input-system", "anti-cheat-integrity"], "E", "K-NET-4"),
            ("NET.PRED.lockstep-replay", "Shipping input-stream replays for lockstep games", pr, ["determinism-replay"], "E", "K-NET-16"),
            ("NET.ARCH.async", "Asynchronous / turn-based backend-mediated play", na, ["online-services-liveops"], "E", "K-NET-11"),
            ("NET.ARCH.distributed-authority", "Per-object ownership transfer & shared authority", na, [rp], "E", "K-NET-11"),
            ("NET.ARCH.connectivity", "Connectivity loss, sign-out & suspend/resume session policy", na,
             ["platform-console", "platform-mobile", "gameplay-architect"], "E", "K-NET-9"),
            ("NET.ARCH.validation", "Netcode oracle suite: deterministic net simulation, prediction/replication "
             "correctness metrics", na, ["functional-automation-soak"], "E", "K-QUALITY-5"),
            ("NET.SRV.persistence", "Server-authoritative persistent player/world data boundary (write-behind, leases, "
             "crash consistency, live schema migration)", ds, ["persistence-save", "serialization-schema"], "E", "K-NET-7 K-COMPLETE-12"),
            ("NET.SRV.transactions", "Idempotent economy/inventory transaction boundary", ds, ["anti-cheat-integrity"], "E", "K-NET-7"),
            ("NET.SRV.auth", "Server-side auth-ticket & service-identity validation", ds, [nt], "E", "K-NET-7"),
            ("NET.SRV.zoning", "Zoned/instanced multi-server worlds & player handoff", ds, ["world-architect", rp], "E", "K-NET-8")]:
        ed.cap(cid, name, owner, mat=mat, contrib=contrib, tags=t)
    ed.cap_move("NET.ARCH.sharding", "NET.ARCH.meshing", tags="K-NET-8")
    ed.cap_set("NET.ARCH.meshing", name="Seamless dynamic server meshing / cross-server entity authority", mat="X",
               tags="K-NET-8")
    ed.cap_set("NET.ARCH.versioning", name="Compatibility-window policy & handshake (live-ops version skew, crossplay "
               "patch skew, rolling server deploys)", add_contrib=["packaging-release-patching"], tags="K-NET-12")
    ed.cap_set("BLD.REL.compat", name="Emit version/compatibility manifests per NET.ARCH.versioning", tags="K-NET-12")
    ed.cap_set("NET.REP.replays", name="Replays from the replication stream (C-REPLAY producer)", tags="K-NET-16 K-ARCH-9")
    ed.cap_set("NET.REP.interest", add_contrib=["world-architect"], tags="K-NET-13")
    ed.cap_move("PLAT.DESK.server-host", "NET.SRV.host-os", tags="K-PLATFORM-19")
    ed.cap_set("NET.SRV.host-os", name="Server host OS & container specifics (Linux, ARM64 hosts)", owner=ds,
               rm_contrib=[ds], add_contrib=["platform-desktop"], tags="K-PLATFORM-19")
    ed.area("NET.DBG", "Network debugging & profiling", tags="K-NET-6")
    ed.cap("NET.DBG.profiler", "Network profiler: bandwidth attribution per connection/entity/property", rp,
           tags="K-NET-6 K-TOOLS-10")
    ed.cap("NET.DBG.inspect", "Packet capture & protocol dissector", nt, tags="K-NET-6")
    ed.cap("NET.DBG.visualize", "Relevancy, priority & prediction-error visualization", rp,
           contrib=["visual-debugging-tools"], tags="K-NET-6")
    ed.cap("NET.DBG.session-replay", "Record/replay of full network sessions for debugging", rp,
           contrib=["determinism-replay"], tags="K-NET-6")
    # anti-cheat
    ac = "anti-cheat-integrity"
    ed.skill_set(ac, profiles=["all"], consumes=["C-NET?", "C-PREDICT?", "C-PHYS?", "C-GAME?", "C-SVC?", "C-LIVE?"],
                 tags="K-QUALITY-19 K-NET-17")
    for cid in ("XC.SEC.server-validation", "XC.SEC.anticheat", "XC.SEC.abuse"):
        ed.cap_set(cid, profiles=["online"], tags="K-QUALITY-19")
    ed.cap("XC.SEC.score-integrity", "Leaderboard & achievement submission validation", ac, tags="K-QUALITY-19")
    ed.cap_set("XC.SEC.tamper", add_contrib=[ac], tags="K-NET-17")


def gameplay(ed):
    ga = "gameplay-architect"
    ed.contract_set("C-GAME", requires=["C-ID", "C-FRAME"], tags="K-LEGACY-10 K-GAMEPLAY-14",
                    summary="Game module entry points, rules/session state, data-oriented control binding (input "
                            "source or AI → controlled entity), scheduled gameplay systems, extension hooks.")
    ed.skill_set(ga, profiles=["all"],
                 consumes=["C-ID", "C-FRAME", "C-TASK", "C-ECS?", "C-INPUT?", "C-PHYS?", "C-ANIM?", "C-AUDIO?", "C-NET?",
                           "C-REP?", "C-WORLD?", "C-SAVE?", "C-UI?", "C-VIEW?", "C-A11Y"],
                 non_responsibilities=[["Abilities/tags/volumes toolkit", "gameplay-systems-toolkit"],
                                       ["Scripting VM", "scripting-runtime"],
                                       ["Game-specific code", "external:game-team"]],
                 tags="K-LEGACY-3 K-GAMEPLAY-14 K-GAMEPLAY-5 K-ARCH-20 K-PROD-17")
    ed.cap_set("GAM.FW.rules", name="Game rules & session state", tags="K-LEGACY-10")
    for cid, name, contrib, t in [
            ("GAM.FW.control", "Player/agent ↔ controlled-entity association as data (control model per game by ADR)",
             ["input-system"], "K-LEGACY-10 K-GAMEPLAY-21"),
            ("GAM.FW.execution", "Gameplay execution model: scheduled systems/jobs with declared access; no per-object "
             "tick by default", ["frame-orchestration", "ecs-runtime"], "K-LEGACY-3"),
            ("GAM.FW.ui-binding", "Gameplay view-model exposure for HUD & menus", ["ui-architect"], "K-GAMEPLAY-5"),
            ("GAM.FW.engagement", "Engagement, sign-in change & controller-disconnect flows",
             ["certification-compliance", "input-system", "platform-services"], "K-GAMEPLAY-17"),
            ("GAM.FW.objectives", "Objective/quest state extension point with save & replication hooks",
             ["narrative-dialogue", "persistence-save"], "K-GAMEPLAY-1"),
            ("GAM.FW.streamer-mode", "Streamer-safe mode (licensed music, PII hiding)", ["audio-content-runtime"], "K-COMPLETE-13")]:
        ed.cap(cid, name, ga, contrib=contrib, tags=t)
    ed.cap_set("GAM.FW.flow", name="Game flow & state transitions (menus, transitions)", tags="K-GAMEPLAY-5")
    tk = "gameplay-systems-toolkit"
    ed.skill_set(tk, consumes=["C-GAME", "C-VIEW", "C-PHYS?", "C-ANIM?", "C-AUDIO?", "C-DEVICE?", "C-PREDICT?", "C-REP?",
                               "C-INPUT?", "C-GAMEDATA", "C-A11Y"],
                 tool_consumes=["C-EDCMD", "C-EDHOST"], tags="K-GAMEPLAY-4 K-SIM-12 K-NET-5")
    ed.cap_set("GAM.SYS.camera", name="Gameplay camera rigs, blending & collision (C-VIEW sources)", tags="K-ARCH-11")
    ed.cap_set("GAM.SYS.spawning", name="Spawning (batched, deferred structural changes); pooling only where measured",
               tags="K-LEGACY-14")
    ed.cap_set("GAM.SYS.messages", name="Gameplay-tag message channels built on C-ID events",
               add_contrib=["entity-object-model"], tags="K-ARCH-18")
    for cid, name, contrib, t in [
            ("GAM.SYS.predicted-abilities", "Predicted abilities & effects (prediction keys, rollback of effects)",
             ["prediction-rollback"], "K-NET-5"),
            ("GAM.SYS.impacts", "Surface-type impact effects routing (audio, VFX, decals, haptics)",
             ["audio-content-runtime", "vfx-particles"], "K-SIM-12"),
            ("GAM.SYS.volumes", "Trigger & gameplay volumes, gameplay markers, level-scoped logic wiring",
             ["collision-detection", "scripting-runtime"], "K-GAMEPLAY-11 K-COMPLETE-24"),
            ("GAM.SYS.building", "Player construction (snapping, sockets, structural integrity)", ["voxel-worlds"], "K-COMPLETE-16"),
            ("GAM.SYS.hit-detection", "Hit/hurtbox authoring, frame data & hit resolution",
             ["collision-detection", "animation-runtime", "prediction-rollback"], "K-COMPLETE-27")]:
        ed.cap(cid, name, tk, contrib=contrib, tags=t)
    # character movement
    ed.skill_add(id="character-movement", name="Character Movement", tier="expert", parent=ga,
                 profiles=["min2d", "lite3d", "std3d"], kind="runtime", targets=ALL_T, workstream="gameplay",
                 purpose="Character movement as one system at the junction of input, physics, animation and netcode: "
                         "movement modes, step/slope rules, root-motion consumption and authority, networked "
                         "predicted/reconciled movement with a resimulatable move API, mount/vehicle transitions, 2D "
                         "platformer movement.",
                 non_responsibilities=[["Collide-and-slide controller primitive", "character-physics"],
                                       ["Generic prediction machinery", "prediction-rollback"],
                                       ["Animation selection", "motion-synthesis"]],
                 consumes=["C-GAME", "C-PHYS", "C-INPUT", "C-ANIM?", "C-PREDICT?", "C-DET"],
                 expertise=["character movement", "movement netcode", "game feel"], tags="K-SIM-2 K-GAMEPLAY-7")
    ed.contract_add("C-MOVE", 4, "character-movement", "Character movement",
                    "Movement modes, move requests, resimulatable move API, root-motion hand-off.", ["C-PHYS", "C-GAME"],
                    tags="K-SIM-2")
    ed.area("GAM.MOVE", "Character movement", tags="K-SIM-2")
    for cid, name in [("GAM.MOVE.modes", "Movement modes (walk, sprint, crouch, swim, climb, mantle, fly, glide)"),
                      ("GAM.MOVE.networked", "Networked predicted/reconciled movement & resimulatable move API"),
                      ("GAM.MOVE.root-motion", "Root-motion vs capsule authority"),
                      ("GAM.MOVE.transitions", "Mount & vehicle transitions"),
                      ("GAM.MOVE.platformer", "2D platformer movement (coyote time, input buffering)")]:
        ed.cap(cid, name, "character-movement", tags="K-SIM-2 K-GAMEPLAY-7")
    for s_, what in (("motion-synthesis", "Locomotion gameplay"),):
        s = ed.skill(s_)
        s["non_responsibilities"] = [[w, "character-movement" if w == what else o] for w, o in s["non_responsibilities"]]
    ed.use("motion-synthesis", "C-MOVE?", "C-ML?", tags="K-SIM-2 K-FUTURE-1")
    # gameplay data
    ed.skill_add(id="gameplay-data", name="Gameplay Data & Tuning", tier="expert", parent=ga, profiles=["all"],
                 kind="runtime", targets=ALL_T, workstream="gameplay",
                 purpose="Designer-owned data: typed data tables and row references, curve assets, tuning assets with "
                         "inheritance and per-platform/difficulty variants, spreadsheet round-trip, balance "
                         "simulation, and live data hotfixes through remote overrides.",
                 non_responsibilities=[["Serialization mechanics", "serialization-schema"],
                                       ["Remote-config service", "online-services-liveops"],
                                       ["Tabular editing widgets", "editor-ui-framework"]],
                 consumes=["C-REFL", "C-ASSET", "C-SER", "C-LIVE?", "C-CFG"], tool_consumes=["C-EDCMD", "C-EDHOST"],
                 expertise=["data-driven design", "balancing", "spreadsheet pipelines"],
                 tags="K-GAMEPLAY-10 K-COMPLETE-9 K-PROD-5 K-TOOLS-5")
    ed.contract_add("C-GAMEDATA", 3, "gameplay-data", "Gameplay data",
                    "Data tables, curve assets, tuning assets with overrides, live override layer.", ["C-REFL", "C-ASSET"],
                    tags="K-GAMEPLAY-10")
    ed.area("GAM.DATA", "Gameplay data", tags="K-GAMEPLAY-10")
    for cid, name, mat in [("GAM.DATA.tables", "Typed data tables & row references", "E"),
                           ("GAM.DATA.curves", "Designer curve assets", "E"),
                           ("GAM.DATA.tuning", "Tuning assets with inheritance, platform & difficulty variants", "E"),
                           ("GAM.DATA.spreadsheets", "Spreadsheet round-trip (CSV/Sheets/Excel)", "E"),
                           ("GAM.DATA.balance-sim", "Balance simulation runs (combat/economy)", "E"),
                           ("GAM.DATA.hotfix", "Server-delivered data overrides for tunables", "E")]:
        ed.cap(cid, name, "gameplay-data", mat=mat, tags="K-GAMEPLAY-10 K-COMPLETE-9 K-PROD-6")
    # narrative & dialogue
    ed.skill_add(id="narrative-dialogue", name="Narrative & Dialogue", tier="expert", parent=ga, profiles=["all"],
                 kind="runtime", targets=ALL_T, workstream="gameplay",
                 purpose="The dialogue line model and narrative runtime shared by VO, subtitles, lip sync, localization, "
                         "cinematics and AI: line database with stable IDs, branching dialogue runtime and narrative-"
                         "middleware interchange, narrative fact store with save/replication participation, barks and "
                         "response rules, recording scripts and placeholder VO.",
                 non_responsibilities=[["Quest content", "external:game-team"], ["VO playback", "audio-content-runtime"],
                                       ["String formatting", "localization-i18n"]],
                 consumes=["C-LOC", "C-SER", "C-ID", "C-SAVE?", "C-REP?", "C-A11Y"],
                 tool_consumes=["C-EDCMD", "C-EDHOST", "C-GRAPH"],
                 expertise=["dialogue systems", "response rules", "Ink/Yarn/articy interchange", "VO pipelines"],
                 tags="K-GAMEPLAY-1 K-COMPLETE-10")
    ed.contract_add("C-DIALOGUE", 3, "narrative-dialogue", "Dialogue lines & narrative state",
                    "Line records (speaker, text per locale, VO per locale, timing, lip-sync data), conditions, "
                    "playback requests, narrative fact store.", ["C-LOC", "C-ID"], tags="K-GAMEPLAY-1")
    ed.area("GAM.NARR", "Narrative & dialogue", tags="K-GAMEPLAY-1")
    for cid, name, contrib in [("GAM.NARR.lines", "Dialogue & VO line database with stable IDs", ["localization-i18n", "audio-content-runtime"]),
                               ("GAM.NARR.branching", "Branching dialogue runtime", []),
                               ("GAM.NARR.middleware", "Narrative-tool interchange (Ink/Yarn/articy class)", []),
                               ("GAM.NARR.facts", "Narrative fact & flag store with save/replication participation", ["persistence-save"]),
                               ("GAM.NARR.barks", "Contextual barks & response rules", ["ai-behavior-perception"]),
                               ("GAM.NARR.vo-script", "Recording scripts & placeholder TTS VO", ["audio-content-runtime", "localization-i18n"])]:
        ed.cap(cid, name, "narrative-dialogue", contrib=contrib, tags="K-GAMEPLAY-1 K-COMPLETE-10")
    # scripting
    sc = "scripting-runtime"
    ed.contract_set("C-SCRIPT", requires=["C-REFL"], layer=3, tags="K-LEGACY-3")
    ed.skill_set(sc, consumes=["C-REFL", "C-RELOAD?", "C-GAME?", "C-TASK"], tool_consumes=["C-GRAPH"],
                 tags="K-LEGACY-3 K-TOOLS-5")
    ed.cap("GAM.SCR.concurrency", "Script VM concurrency: per-worker VMs/isolates, thread-safe binding rules, "
           "deferred world mutation", sc, tags="K-LEGACY-3")
    ed.cap("GAM.SCR.level-scripting", "Level-bound script/event wiring", sc, contrib=["world-data-model"], tags="K-GAMEPLAY-11")
    # AI & navigation
    nv = "navigation-pathfinding"
    ed.contract_set("C-NAV", requires=["C-SPATIAL"], tags="K-GAMEPLAY-14")
    ed.skill_set(nv, profiles=["min2d", "lite3d", "std3d"], consumes=["C-SPATIAL", "C-PHYS?", "C-WORLD?", "C-TASK", "C-ENV?"],
                 tool_consumes=["C-COOK", "C-EDCMD", "C-EDHOST"], tags="K-GAMEPLAY-14")
    ed.cap_move("GAM.AI.avoidance", "GAM.AI.local-avoidance", tags="K-GAMEPLAY-13")
    ed.cap_set("GAM.AI.local-avoidance", name="Local avoidance (ORCA/RVO)", owner=nv, tags="K-GAMEPLAY-13")
    ed.cap("GAM.AI.lanes", "Lane/road graphs & vehicle navigation", nv, contrib=["crowd-simulation"], tags="K-GAMEPLAY-22")
    cw = "crowd-simulation"
    ed.skill_set(cw, profiles=["openworld", "massim"], tags="K-SIM-5 K-PERF-13")
    ed.cap("GAM.AI.traffic", "Traffic simulation with LOD (physics vehicle → kinematic → abstract flow)", cw,
           contrib=["vehicle-physics"], tags="K-SIM-5")
    ed.cap_set("GAM.AI.flowfields", name="Flow fields (grid and navmesh variants, 2D-capable)", tags="K-PERF-13")
    ai = "ai-behavior-perception"
    ed.skill_set(ai, consumes=["C-GAME", "C-NAV?", "C-SPATIAL", "C-PHYS?", "C-ML?", "C-LIVE?", "C-DIALOGUE?", "C-SIGNIF?"],
                 tool_consumes=["C-GRAPH", "C-EDCMD", "C-EDHOST"], tags="K-GAMEPLAY-15 K-FUTURE-1 K-FUTURE-5 K-TOOLS-5")
    ed.contract_add("C-AIAGENT", 4, ai, "AI decision-provider extension point",
                    "Optional decision providers (learned policies, LLM agents) with budget, timeout, moderation and "
                    "authored fallback.", ["C-GAME"], tags="K-GAMEPLAY-15")
    ed.cap_set("GAM.AI.llm", mat="M", name="LLM-driven NPC dialogue & behavior (via C-AIAGENT; guardrails per XC.SEC.genai)",
               tags="K-FUTURE-5 K-FUTURE-15 K-GAMEPLAY-15")
    ed.cap_set("GAM.AI.learned", mat="M", name="Learned policies / ML agents (via C-AIAGENT)", tags="K-FUTURE-15")
    ed.cap("GAM.AI.tactical", "Cover/tactical point generation & squad coordination", ai, tags="K-GAMEPLAY-22")
    ed.area("GAM.TOOL", "Gameplay authoring tools", tags="K-TOOLS-5")
    for cid, name, owner, contrib in [
            ("GAM.TOOL.ai-editors", "Behavior-tree, state-tree & environment-query editors and testing", ai, ["graph-editor-framework"]),
            ("GAM.TOOL.ai-debug", "AI debugger", ai, ["visual-debugging-tools"]),
            ("GAM.TOOL.nav", "Nav modifiers, links & navigation debugging", nv, ["visual-debugging-tools"]),
            ("GAM.TOOL.tags-abilities", "Gameplay-tag dictionary, ability & effect authoring", tk, []),
            ("GAM.TOOL.data", "Data-table, curve & tuning editors", "gameplay-data", ["editor-ui-framework"]),
            ("GAM.TOOL.dialogue", "Dialogue editor & screenplay/narrative-tool import", "narrative-dialogue", ["graph-editor-framework"])]:
        ed.cap(cid, name, owner, contrib=contrib, tags="K-TOOLS-5 K-GAMEPLAY-9")
    # persistence
    ps = "persistence-save"
    ed.skill_set(ps, consumes=["C-SER", "C-ID", "C-SVC?", "C-WORLD?", "C-CFG"], tags="K-GAMEPLAY-14")
    ed.cap("GAM.SAVE.settings", "Player settings/options model, scopes (device/user/cloud) & first-boot availability", ps,
           contrib=["input-system", "accessibility", "runtime-scalability"], tags="K-GAMEPLAY-19 K-COMPLETE-26")
    ed.cap("GAM.SAVE.integrity", "Save signing & tamper policy", ps, contrib=["security-engineering"], tags="K-QUALITY-11")
    # reference games
    ed.skill_add(id="reference-games", name="Reference Games", tier="expert", parent="program-orchestration",
                 profiles=["all"], kind="process", targets=[], workstream="governance",
                 purpose="The reference-game ladder (one representative game per configuration) used as milestone and "
                         "release gate, representative production-scale content sets, and the internal playtest and "
                         "dogfood loop.",
                 non_responsibilities=[["Teaching samples", "developer-experience-docs"],
                                       ["Benchmark harness", "perf-benchmarking"]],
                 consumes=[], expertise=["game production", "content production", "playtesting"],
                 tags="K-PROD-4 K-GAMEPLAY-21")
    ed.area("QA.REF", "Reference games", tags="K-PROD-4")
    ed.cap("QA.REF.ladder", "Reference-game ladder per configuration as milestone & release gate", "reference-games",
           contrib=["test-architect"], tags="K-PROD-4")
    ed.cap("QA.REF.content", "Representative production-scale content sets", "reference-games",
           contrib=["perf-benchmarking"], tags="K-PROD-4")
    ed.cap("QA.REF.dogfood", "Internal playtest & dogfood loop", "reference-games", tags="K-PROD-4")


def ui(ed):
    ua, a11 = "ui-architect", "accessibility"
    ed.contract_add("C-A11YRT", 3, a11, "Accessibility runtime",
                    "Caption/subtitle submission, screen-reader announcements and accessibility-tree ingestion, TTS/STT, "
                    "accessibility settings and change events.", ["C-TEXT"], tags="K-ARCH-8 K-GAMEPLAY-6")
    ed.skill_set(a11, consumes=["C-TEXT", "C-PAL", "C-DIALOGUE?"], tags="K-ARCH-8")
    ed.cap_set("UI.A11Y.subtitles", name="Caption & subtitle service and policy (C-A11YRT)", tags="K-ARCH-8")
    ed.cap_move("UI.A11Y.text-scale", "UI.FW.text-scale", tags="K-ARCH-8")
    ed.cap_set("UI.FW.text-scale", owner=ua, rm_contrib=[ua], add_contrib=[a11], tags="K-ARCH-8")
    ed.cap("UI.A11Y.comms", "Accessible communications (chat TTS/STT transcription)", a11,
           contrib=["online-services-liveops"], tags="K-COMPLETE-5 K-GAMEPLAY-6")
    ed.nonresp(a11, [["Input remapping implementation", "input-system"], ["UI layout engine & subtitle presentation", ua],
                     ["Colorblind passes", "post-color-hdr"], ["Legal compliance sign-off", "certification-compliance"]],
               tags="K-ARCH-8")
    ed.cap_set("UI.FW.architecture", name="Game UI architecture (retained + data binding)", tags="K-ARCH-18 K-TOOLS-15 K-GAMEPLAY-20")
    ed.area("UI.TOOL", "UI authoring tools", tags="K-TOOLS-1")
    ed.cap_move("UI.FW.authoring", "UI.TOOL.designer", tags="K-TOOLS-1")
    for cid, name, contrib, t in [
            ("UI.FW.safe-area", "Safe areas, cutouts & aspect-ratio adaptation", ["platform-architect"], "K-GAMEPLAY-18 K-COMPLETE-25"),
            ("UI.FW.rtl-mirroring", "RTL layout mirroring", ["localization-i18n"], "K-GAMEPLAY-18"),
            ("UI.FW.xr-interaction", "XR UI interaction (pointer, poke, hand tracking)", ["xr-runtime"], "K-GAMEPLAY-18"),
            ("UI.FW.platform-dialogs", "Platform-mandated dialogs & system keyboard", ["certification-compliance"], "K-GAMEPLAY-18"),
            ("UI.FW.a11y-tree", "Semantic accessibility tree for game UI", ["accessibility"], "K-GAMEPLAY-6"),
            ("UI.FW.logic", "UI logic hosting via reflection-invoked handlers (script/visual script)", ["scripting-runtime"], "K-GAMEPLAY-5"),
            ("UI.FW.loading-screens", "Non-blocking loading/boot screens & movie playback", ["resource-streaming-architect", "media-playback"], "K-GAMEPLAY-5"),
            ("UI.FW.subtitles", "Subtitle & caption presentation", ["accessibility"], "K-ARCH-8")]:
        ed.cap(cid, name, ua, contrib=contrib, tags=t)
    ed.skill_set(ua, consumes=["C-REFL", "C-INPUT", "C-DRAW2D", "C-TEXT", "C-LOC", "C-A11YRT", "C-AUDIO?", "C-VIDEO?",
                               "C-PAL", "C-A11Y"], tool_consumes=["C-EDCMD", "C-EDHOST"], tags="K-GAMEPLAY-5 K-ARCH-8")
    ed.use("text-fonts", "C-A11Y", tags="K-GAMEPLAY-6")
    ed.cap("UI.TXT.font-subsetting", "Per-locale font subsetting & font-pack chunking", "text-fonts",
           contrib=["asset-cook-processors"], tags="K-GAMEPLAY-18")
    lo = "localization-i18n"
    ed.cap("UI.LOC.language-packs", "On-demand language & VO packs", lo, contrib=["packaging-release-patching"],
           tags="K-GAMEPLAY-18")
    ed.cap("UI.LOC.overflow-validation", "Text-expansion auto-fit & overflow validation", lo,
           contrib=["content-pipeline-architect"], tags="K-GAMEPLAY-18")
    ed.use(lo, "C-VFS?", tags="K-GAMEPLAY-18")
    # developer UI
    vd = "visual-debugging-tools"
    ed.cap_move("ED.UI.imgui", "ED.DEBUG.imgui", tags="K-TOOLS-15 K-GAMEPLAY-20")
    ed.cap_set("ED.DEBUG.imgui", name="Immediate-mode developer UI (in-game, with remote front end for servers)", owner=vd,
               add_contrib=["editor-ui-framework"], tags="K-TOOLS-15 K-GAMEPLAY-20")
    ed.contract_add("C-DEVUI", 3, vd, "Developer UI",
                    "Immediate-mode developer UI and debug menus available in development builds on every target.",
                    ["C-DRAW2D"], tags="K-TOOLS-15")
    ed.skill_set(vd, consumes=["C-INSTR", "C-ECS?", "C-DRAW2D?", "C-RSCENE?", "C-REPLAY?", "C-IPC"], tags="K-TOOLS-15")


def editor_content(ed):
    ea, eu, wv, cv = "editor-architect", "editor-ui-framework", "world-editor-viewport", "collaboration-version-control"
    ed.contract_add("C-EDHOST", 5, eu, "Editor host",
                    "Asset-editor host, preview-scene registration, thumbnail providers, inspector customization, "
                    "tool-mode registration, shared curve/timeline widgets.", ["C-EDCMD"], tags="K-TOOLS-1 K-TOOLS-3")
    ed.skill_set(eu, consumes=["C-EDCMD", "C-REFL", "C-DRAW2D", "C-TEXT", "C-DEVUI?"], tags="K-TOOLS-15")
    for cid, name, contrib, t in [
            ("ED.UI.asset-editor-host", "Generic asset-editor host (tabs, preview, viewers, inspection modes)", [], "K-TOOLS-3"),
            ("ED.UI.thumbnails", "Thumbnail generation & caching", ["content-pipeline-architect", "render-architect"], "K-TOOLS-3"),
            ("ED.UI.curves-timeline", "Shared curve, timeline & dope-sheet editors", ["cinematics-sequencer", "animation-runtime", "vfx-particles"], "K-TOOLS-3"),
            ("ED.UI.tabular", "Tabular/bulk editing & spreadsheet round-trip", ["gameplay-data"], "K-TOOLS-5"),
            ("ED.UI.toolkit-basis", "Editor toolkit basis: shared with or separate from game UI (ADR)", ["ui-architect"], "K-TOOLS-15")]:
        ed.cap(cid, name, eu, contrib=contrib, tags=t)
    for cid, name, contrib, t in [
            ("ED.WORLD.preview-scenes", "Isolated preview scenes & asset inspection viewports", [], "K-TOOLS-3"),
            ("ED.WORLD.blockout", "Blockout & in-editor modeling (primitives, booleans, UVs)", ["asset-cook-processors"],
             "K-TOOLS-12 K-COMPLETE-8 K-GAMEPLAY-11 K-PROD-5"),
            ("ED.WORLD.ld-utilities", "Level-design utilities: measure, filters, bulk replace, layer visibility", [], "K-TOOLS-12"),
            ("ED.WORLD.2d-mode", "2D/orthographic editing, pixel snapping, sorting-layer tools", ["render-2d-vector"], "K-TOOLS-11")]:
        ed.cap(cid, name, wv, contrib=contrib, tags=t)
    ed.skill_set(wv, consumes=["C-EDCMD", "C-EDHOST", "C-WORLD", "C-RSCENE", "C-SPATIAL", "C-VIEW"], tags="K-ARCH-11")
    for cid, name, contrib, mat, t in [
            ("ED.ARCH.recovery", "Autosave, transaction journal & crash recovery", ["crash-diagnostics"], "E", "K-TOOLS-7"),
            ("ED.ARCH.pie-net", "Multiplayer play-in-editor & network emulation", ["dedicated-server", "network-transport"], "E", "K-TOOLS-17 K-NET-6"),
            ("ED.ARCH.agent-api", "Agent/automation control & introspection protocol for editor and runtime",
             ["visual-debugging-tools", "observability-telemetry"], "M", "K-FUTURE-12"),
            ("ED.ARCH.discipline-workflows", "Per-discipline end-to-end workflow specs & iteration targets",
             ["hot-reload-iteration"], "E", "K-PROD-10")]:
        ed.cap(cid, name, ea, mat=mat, contrib=contrib, tags=t)
    ed.skill_set(ea, consumes=["C-REFL", "C-SER", "C-ASSET", "C-WORLD", "C-PLUGIN", "C-UI?", "C-IPC", "C-NET?", "C-REP?"],
                 tags="K-TOOLS-17 K-SYSTEMS-7")
    ed.cap("ED.COLLAB.partial-sync", "Sparse/virtualized workspaces & on-demand payloads", cv, tags="K-TOOLS-9")
    ed.cap_set("ED.COLLAB.multiuser", profiles=["team-large"], tags="K-PROD-9")
    ed.cap_set("ED.COLLAB.locking", profiles=["team-large"], tags="K-PROD-9")
    # graph editor non-responsibility: one entry per graph-owning domain
    ed.nonresp("graph-editor-framework", [["Each domain's graph semantics",
                                           ["material-system", "animation-graphs", "vfx-particles", "audio-content-runtime",
                                            "procedural-generation", "scripting-runtime", "ai-behavior-perception",
                                            "narrative-dialogue"]]], tags="K-TOOLS-20")
    # AI-assisted authoring
    ed.skill_set("ai-assisted-authoring", profiles=["all"], tags="K-FUTURE-18 K-TOOLS-16")
    ed.cap_del("ED.AI.processing", tags="K-TOOLS-16 (techniques move to format owners)")
    ed.cap("ED.AI.evaluation", "Evaluation harness for generative & ML-assisted tools", "ai-assisted-authoring", mat="M",
           tags="K-TOOLS-16")
    # content pipeline
    cp = "content-pipeline-architect"
    ed.contract_set("C-COOK", tags="K-FUTURE-4 K-LEGACY-6 K-TOOLS-6",
                    summary="Processor inputs, cache keys, determinism class (bit-exact / tolerance / pinned-artifact), "
                            "platform variants, world-scope steps, per-asset on-demand invocation, validation hooks.")
    for cid, name, contrib, mat, prof, t in [
            ("CNT.COOK.world-build", "World-scoped derived-data build graph: region invalidation, distributed bakes, "
             "staleness reporting", ["world-architect", "ci-cd-automation"], "E", None, "K-TOOLS-6"),
            ("CNT.COOK.on-demand", "On-demand cooking, cook-server streaming to running targets, play without full cook",
             ["hot-reload-iteration", "resource-streaming-architect", "editor-architect", "platform-console", "platform-mobile"],
             "E", None, "K-LEGACY-6 K-TOOLS-8"),
            ("CNT.COOK.shared-cache", "Team/cloud derived-data cache deployment & health", ["ci-cd-automation"], "E",
             ["team-large"], "K-TOOLS-9"),
            ("CNT.COOK.gpu-steps", "GPU & training cook steps with pinned-artifact determinism & dataset lineage",
             ["ml-inference-runtime", "ci-cd-automation"], "M", None, "K-FUTURE-4"),
            ("CNT.VAL.audit", "Asset reference, size & chunk auditing tools", ["package-formats-vfs", "packaging-release-patching"],
             "E", None, "K-TOOLS-13"),
            ("CNT.VAL.submit-gate", "Validate-on-save & pre-submit content checks (domain validators registered via hooks)",
             ["ci-cd-automation"], "E", None, "K-TOOLS-13"),
            ("CNT.ID.rights", "Asset rights/license/provenance metadata through cook to a shipping rights manifest",
             ["certification-compliance", "ai-assisted-authoring"], "E", None, "K-PROD-12")]:
        ed.cap(cid, name, cp, mat=mat, contrib=contrib, profiles=prof, tags=t)
    ed.cap_set("CNT.COOK.distributed", profiles=["team-large"], tags="K-PROD-9")
    ed.cap_set("ED.AI.provenance", add_contrib=["content-pipeline-architect"], name="Provenance of generated content "
               "(consumer of CNT.ID.rights)", tags="K-PROD-12")
    ai_ = "asset-import-interchange"
    for cid, name, mat, t in [("CNT.IMP.caches", "Geometry/point cache import", "E", "K-TOOLS-18"),
                              ("CNT.IMP.procedural", "Procedural-asset (HDA-class) evaluation", "E", "K-TOOLS-18"),
                              ("CNT.IMP.rules", "Import pipelines, presets & batch import", "E", "K-TOOLS-18"),
                              ("CNT.IMP.dcc-plugins", "DCC exporters & in-DCC validation", "E", "K-TOOLS-18"),
                              ("CNT.IMP.splats", "Splat/radiance-field import & compression", "X", "K-RENDER-15 K-FUTURE-9"),
                              ("CNT.IMP.geospatial", "Geospatial data ingestion (DEM, 3D Tiles, OSM)", "M", "K-COMPLETE-15")]:
        ed.cap(cid, name, ai_, mat=mat, tags=t)
    acp = "asset-cook-processors"
    ed.cap("CNT.COOK.images", "Image processing (mips, normal maps, channel packing)", acp, tags="K-GAMEPLAY-12")
    ed.cap("CNT.COOK.geometry-ops", "Mesh boolean, remesh & UV-unwrap operations for processors and blockout", acp,
           contrib=["world-editor-viewport"], tags="K-TOOLS-12")
    ed.cap("CNT.COOK.ml-assisted", "ML-assisted retopology/UV/LOD techniques as processor options", acp, mat="M",
           contrib=["ai-assisted-authoring", "virtualized-geometry-lod"], tags="K-TOOLS-16")
    ed.use(acp, "C-ML?", tags="K-FUTURE-1")
    # world data model tool logic
    ed.area("WLD.TOOL", "World & environment authoring tools", tags="K-TOOLS-1")
    for cid, name, owner in [("WLD.TOOL.prefabs", "Prefab & override editing", "world-data-model"),
                             ("WLD.TOOL.foliage", "Foliage painting & placement tools", "vegetation-foliage"),
                             ("WLD.TOOL.water", "Water body authoring tools", "water-ocean"),
                             ("WLD.TOOL.sky-weather", "Sky, time-of-day & weather authoring", "atmosphere-weather"),
                             ("WLD.TOOL.pcg", "PCG graph authoring & debugging", "procedural-generation")]:
        ed.cap(cid, name, owner, contrib=["world-editor-viewport"], tags="K-TOOLS-1")
        ed.use(owner, "C-EDCMD", "C-EDHOST", tool=True, tags="K-TOOLS-1")
    ed.cap_move("WLD.ENV.terrain-tools", "WLD.TOOL.terrain", tags="K-TOOLS-1")
    ed.use("terrain", "C-EDCMD", "C-EDHOST", tool=True, tags="K-TOOLS-1")
    ed.use("procedural-generation", "C-GRAPH", tool=True, tags="K-TOOLS-1")
    ed.use("world-data-model", "C-RELOAD?", tags="K-TOOLS-14")
    # CI/CD
    ci = "ci-cd-automation"
    for cid, name, contrib, prof, t in [
            ("BLD.CI.binary-distribution", "Prebuilt editor/tool binaries matched to content revisions",
             ["collaboration-version-control"], None, "K-TOOLS-9 K-PROD-10"),
            ("BLD.CI.build-distribution", "Build distribution to QA, playtesters, betas & devkits",
             ["platform-console", "packaging-release-patching"], None, "K-PROD-10 K-COMPLETE-11"),
            ("BLD.CI.local-first", "Zero-infrastructure local workflow (local caches, single-machine CI)",
             ["collaboration-version-control"], None, "K-PROD-9")]:
        ed.cap(cid, name, ci, contrib=contrib, profiles=prof, tags=t)
    for cid in ("BLD.CI.farm", "BLD.CI.devices"):
        ed.cap_set(cid, profiles=["team-large"], tags="K-PROD-9")
    ed.cap_set("BLD.CI.orchestration", owner=ci, tags="K-ARCH-13")


def platform(ed):
    pa, ps = "platform-architect", "platform-services"
    ed.cap_set("PLAT.PAL.os", name="OS services abstraction (VM, files, time, dynamic libraries)", tags="K-SYSTEMS-4")
    for cid, name, contrib, mat, t in [
            ("PLAT.PAL.base", "Bootstrap base (C-BASE): raw allocator, raw sinks, hook tables", ["core-runtime-architect"], "E", "K-SYSTEMS-1"),
            ("PLAT.PAL.threads", "Thread creation, affinity & QoS per OS", ["job-system-task-graph"], "E", "K-SYSTEMS-4"),
            ("PLAT.PAL.thread-affinity", "Thread-affinity registry & isolation of OS-thread-bound APIs behind queues; "
             "engine loop never assumes the OS main thread", ["job-system-task-graph", "platform-mobile", "platform-console"], "E", "K-LEGACY-5"),
            ("PLAT.PAL.process", "Processes, pipes, shared memory, local/dev sockets, HTTP(S)/TLS client (platform stacks)",
             ["security-engineering"], "E", "K-SYSTEMS-7 K-COMPLETE-3"),
            ("PLAT.PAL.clocks", "Clocks, timer precision & clock-domain correlation (CPU↔GPU↔audio↔display↔input)",
             ["rhi-core", "audio-architect", "frame-orchestration"], "E", "K-SYSTEMS-16"),
            ("PLAT.PAL.signals", "Signal/SEH handler registry & chaining order", ["crash-diagnostics"], "E", "K-SYSTEMS-17"),
            ("PLAT.PAL.fs-watch", "File-system change notification", ["hot-reload-iteration"], "E", "K-SYSTEMS-17"),
            ("PLAT.PAL.power", "Power, thermal & performance-hint APIs", ["runtime-scalability"], "E", "K-SYSTEMS-13"),
            ("PLAT.PAL.system-events", "System events & queries: memory pressure, reachability, audio endpoints, locale, "
             "OS accessibility settings, overlay/focus, storage, page size", ["memory-allocators", "accessibility"], "E", "K-PLATFORM-14"),
            ("PLAT.PAL.safe-area", "Title-safe area, cutouts & rounded corners", ["ui-architect"], "E", "K-PLATFORM-13"),
            ("PLAT.PAL.permissions", "Runtime permission requests & rationale hooks", [], "E", "K-PLATFORM-15"),
            ("PLAT.PAL.device-db", "Device capability database: hardware → tier mapping, deny-lists, remote updates",
             ["rhi-core", "performance-architect", "observability-telemetry", "online-services-liveops"], "E", "K-PLATFORM-7"),
            ("PLAT.PAL.performance-modes", "Performance-mode switching (docked/handheld, Pro/enhanced, TDP profiles)",
             ["platform-console", "platform-desktop", "runtime-scalability"], "E", "K-PLATFORM-12"),
            ("PLAT.PAL.os-support-policy", "Supported OS versions, deprecation & beta-OS validation", [], "E", "K-PLATFORM-8"),
            ("PLAT.PAL.devlink", "Development host↔target connection service", ["editor-architect", "observability-telemetry"], "E", "K-TOOLS-8"),
            ("PLAT.PAL.confidential-extensions", "NDA platform extensions: segregated modules/repos, public stubs, "
             "sanitized CI results, access classes", ["build-system-toolchains", "security-engineering", "program-orchestration", "platform-console"],
             "E", "K-PLATFORM-3 K-PROD-11"),
            ("PLAT.PAL.cloud-hybrid", "Split client/cloud compute boundary", [], "X", "K-FUTURE-11")]:
        ed.cap(cid, name, pa, mat=mat, contrib=contrib, tags=t)
    ed.cap_move("PLAT.DESK.display", "PLAT.PAL.display", tags="K-PLATFORM-13")
    ed.cap_set("PLAT.PAL.display", owner=pa, add_contrib=["platform-desktop", "platform-console", "platform-mobile"],
               tags="K-PLATFORM-13")
    ed.area("ARCH.STRUCT", "Structure & boundaries")
    ed.cap("ARCH.STRUCT.platform-backends", "Registered platform backend slots (RHI, IO, audio endpoint, input, sockets, "
           "crash, save storage, service SDK, IME/a11y bridge)", pa, contrib=["architecture-governance"], tags="K-PLATFORM-1")
    # platform experts
    ed.skill_set("platform-desktop", platforms=["pc"], tags="K-PLATFORM-2")
    ed.cap("PLAT.DESK.os-security", "OS security interplay (Defender scanning, controlled folders, notarization, TCC, "
           "sandboxes, anti-cheat on Proton)", "platform-desktop",
           contrib=["async-io-storage", "shader-system", "persistence-save", "anti-cheat-integrity"], tags="K-PLATFORM-15")
    ed.cap("PLAT.DESK.arm64", "Windows on ARM (ARM64EC, emulation interop, middleware availability)", "platform-desktop",
           tags="K-FUTURE-17")
    ed.skill_set("platform-console", profiles=["all"], platforms=["console"], implements=["C-RHI"],
                 consumes=["C-PAL", "C-SVC", "C-GPUTIER"], tags="K-PLATFORM-2 K-PLATFORM-4")
    ed.cap("PLAT.CON.portable", "Portable-console integration", "platform-console", tags="K-PLATFORM-12")
    ed.cap("PLAT.CON.cross-gen", "Cross-generation SKUs & backward-compatibility modes", "platform-console", tags="K-PLATFORM-8")
    ed.cap("PLAT.CON.rhi-backends", "Console graphics API backends (confidential extensions implementing C-RHI)",
           "platform-console", contrib=["rhi-core"], tags="K-PLATFORM-4 K-RENDER-16")
    ed.cap_set("PLAT.CON.devkit", name="Devkit deploy/run/debug workflows", tags="K-PLATFORM-8")
    pm = "platform-mobile"
    ed.skill_set(pm, name="Mobile Platforms", profiles=["all"], platforms=["mobile", "xr-standalone"],
                 purpose="iOS and Android (incl. Android-based standalone XR) integration: app lifecycle, thermal/power "
                         "adaptivity, tile-based GPU implications, frame pacing, storage, notifications, deep links.",
                 tags="K-PLATFORM-2 K-PLATFORM-12")
    ed.cap_set("PLAT.MOB.os", name="iOS / Android integration", tags="K-PLATFORM-12")
    ed.cap_set("PLAT.MOB.storage", name="Runtime storage constraints (free-space checks, OS cache purge)", tags="K-PLATFORM-20")
    for cid, name, t in [("PLAT.MOB.frame-pacing", "Mobile frame pacing & refresh-rate selection", "K-PLATFORM-13"),
                         ("PLAT.MOB.notifications", "Local & push notifications", "K-COMPLETE-23"),
                         ("PLAT.MOB.links", "Deep links & attribution boundary (ATT consent)", "K-COMPLETE-23")]:
        ed.cap(cid, name, pm, tags=t)
    # web
    ed.skill_add(id="platform-web", name="Web Platform", tier="expert", parent=pa, profiles=["min2d", "lite3d"],
                 kind="runtime", targets=["client", "tools"], platforms=["web"], workstream="platform",
                 purpose="Web target (WASM + WebGPU): threads and cross-origin isolation, memory limits, OPFS/IndexedDB "
                         "storage, HTTP streaming delivery, user-gesture rules for audio/pointer/fullscreen, browser "
                         "transport constraints.",
                 non_responsibilities=[["WebGPU backend", "rhi-webgpu"], ["Browser transports", "network-transport"]],
                 consumes=["C-PAL"], expertise=["WebAssembly", "browser platform APIs", "web delivery"],
                 tags="K-PLATFORM-6")
    ed.area("PLAT.WEB", "Web platform", tags="K-PLATFORM-6")
    for cid, name, contrib, mat in [("PLAT.WEB.runtime", "WASM threads, cross-origin isolation & memory limits", ["job-system-task-graph"], "E"),
                                    ("PLAT.WEB.storage", "OPFS/IndexedDB storage & quotas", ["persistence-save"], "E"),
                                    ("PLAT.WEB.delivery", "HTTP streaming delivery & caching", ["packaging-release-patching"], "E"),
                                    ("PLAT.WEB.gestures", "User-gesture rules (autoplay, pointer lock, fullscreen)", ["audio-architect"], "E"),
                                    ("PLAT.WEB.webgpu-target", "WebGPU-class 3D on the web", ["rhi-webgpu"], "M")]:
        ed.cap(cid, name, "platform-web", mat=mat, contrib=contrib, tags="K-PLATFORM-6")
    ed.cap_del("PLAT.PAL.web", tags="K-PLATFORM-6 (moved to platform-web)")
    # platform services split
    ed.skill_set(ps, name="Platform Services",
                 purpose="First-party platform and store services: identity and sign-in, achievements and presence, "
                         "entitlements and commerce through first-party stores, privileges and parental controls, social "
                         "graph and invites, block/mute and text filtering, crossplay policy, leaderboards, cloud-save "
                         "APIs, media capture, age and region policy enforcement.",
                 non_responsibilities=[["Third-party/own backend & live-ops boundaries", "online-services-liveops"],
                                       ["Game-server hosting", "dedicated-server"], ["Save-game content", "persistence-save"],
                                       ["Backend implementation", "external:backend"]],
                 consumes=["C-PAL", "C-TASK", "C-CFG"], tags="K-COMPLETE-1 K-PLATFORM-10 K-PROD-17")
    ed.skill_add(id="online-services-liveops", name="Online Services & Live Ops", tier="expert", parent=pa,
                 profiles=["all"], kind="runtime", targets=["client", "headless-client", "server", "tools"],
                 workstream="platform",
                 purpose="Integration boundary to third-party and own online backends and live operations: matchmaking/"
                         "lobby/session boundary, remote config and feature flags, live events and experiments, "
                         "service-hosted voice/text chat sessions, moderation (UGC, chat, generated content), wallet and "
                         "ads boundaries, trusted time, remote generative-AI/inference boundary, service emulators and "
                         "outage injection for tests.",
                 non_responsibilities=[["First-party platform services", ps], ["Backend implementation", "external:backend"],
                                       ["Game-server hosting", "dedicated-server"]],
                 consumes=["C-PAL", "C-TASK", "C-CFG", "C-SVC?"],
                 expertise=["online service APIs", "live operations", "experimentation"],
                 tags="K-COMPLETE-1 K-PROD-6 K-FUTURE-5")
    ed.contract_add("C-LIVE", 3, "online-services-liveops", "Online & live-ops services",
                    "Sessions/matchmaking tickets, remote config, events/experiments, chat sessions, moderation, "
                    "generative/inference service calls with quotas, trusted time, service emulation.",
                    ["C-PAL", "C-TASK"], tags="K-COMPLETE-1")
    ed.contract_set("C-SVC", name="Platform services", tags="K-COMPLETE-1",
                    summary="Identity tokens, entitlements & commerce, privileges, social graph, achievements, "
                            "leaderboards, cloud save, region/age policy.")
    ol = "online-services-liveops"
    for cid in ("PLAT.SVC.matchmaking", "PLAT.SVC.remote-config", "PLAT.SVC.moderation"):
        ed.cap_set(cid, owner=ol, tags="K-COMPLETE-1")
    ed.cap_set("PLAT.SVC.moderation", name="Moderation boundary (UGC, chat, generated content)", tags="K-FUTURE-5")
    ed.area("PLAT.LIVE", "Live operations", tags="K-PROD-6")
    for cid, name, owner, contrib, mat, t in [
            ("PLAT.SVC.social", "Friends, parties, invites & join-in-progress", ps, [], "E", "K-NET-9 K-COMPLETE-5"),
            ("PLAT.SVC.privileges", "Privileges & parental controls at feature boundaries", ps, ["certification-compliance"], "E",
             "K-NET-9 K-PLATFORM-10 K-COMPLETE-4"),
            ("PLAT.SVC.social-safety", "Block/mute/report sync & platform text filtering", ps, [], "E", "K-PLATFORM-10"),
            ("PLAT.SVC.crossplay-policy", "Crossplay opt-in/out & cross-network communication policy", ps, [], "E", "K-PLATFORM-10"),
            ("PLAT.SVC.leaderboards", "Leaderboards, stats & tournaments", ps, ["anti-cheat-integrity"], "E", "K-NET-9 K-COMPLETE-21"),
            ("PLAT.SVC.age-region", "Age verification, playtime/spending limits & regional policy enforcement", ps,
             ["certification-compliance", "gameplay-architect"], "E", "K-PLATFORM-11 K-COMPLETE-4"),
            ("PLAT.SVC.voice-text", "Voice & text chat sessions, channels, mute/block enforcement", ol,
             ["audio-dsp-mixing", "accessibility", "certification-compliance"], "E", "K-NET-10 K-COMPLETE-5"),
            ("PLAT.SVC.trusted-time", "Trusted server time", ol, [], "E", "K-COMPLETE-23"),
            ("PLAT.SVC.genai-boundary", "Remote generative-AI/inference boundary (auth, quotas, cost, latency, routing)", ol,
             ["ml-inference-runtime"], "M", "K-FUTURE-5 K-FUTURE-2"),
            ("PLAT.SVC.emulation", "Service test doubles & outage injection", ol, ["robustness-fuzzing"], "E", "K-QUALITY-10"),
            ("PLAT.LIVE.events", "Scheduled/time-gated content activation", ol, ["package-formats-vfs"], "E", "K-PROD-6"),
            ("PLAT.LIVE.experiments", "A/B assignment & exposure logging", ol, [], "E", "K-PROD-6 K-COMPLETE-22")]:
        ed.cap(cid, name, owner, mat=mat, contrib=contrib, tags=t)
    ed.area("PLAT.COMM", "Commerce & monetization boundary", tags="K-COMPLETE-1")
    for cid, name, owner, contrib in [
            ("PLAT.COMM.iap", "Consumable, non-consumable & subscription purchases via first-party stores", ps, []),
            ("PLAT.COMM.receipts", "Receipt/entitlement validation boundary", ps, ["anti-cheat-integrity", "security-engineering"]),
            ("PLAT.COMM.disclosure", "Randomized-item odds disclosure & regional spending rules", ps, ["certification-compliance"]),
            ("PLAT.COMM.currency", "Virtual-currency & wallet integration boundary", ol, []),
            ("PLAT.COMM.ads", "Ad-SDK integration boundary (consent, mediation, rewarded callbacks, isolation)", ol,
             ["observability-telemetry"])]:
        ed.cap(cid, name, owner, contrib=contrib, tags="K-COMPLETE-1")
    # XR
    xr = "xr-runtime"
    ed.contract_add("C-XRVIEW", 3, xr, "XR views",
                    "View poses, projections, foveation maps, compositor layers and spacewarp depth/motion submission.",
                    ["C-VIEW"], tags="K-RENDER-11")
    ed.skill_set(xr, consumes=["C-PAL", "C-INPUT", "C-FRAME", "C-PRESENT", "C-VIEW", "C-DEVICE", "C-TEMPORAL?", "C-A11Y"],
                 tags="K-RENDER-11 K-ARCH-10 K-RENDER-2")
    for cid, name, contrib, mat in [("PLAT.XR.fixed-foveation", "Fixed foveation parameters", [], "E"),
                                    ("PLAT.XR.passthrough", "Passthrough & MR compositing", [], "E"),
                                    ("PLAT.XR.scene", "Scene understanding (planes, meshes, semantic labels, environment depth)",
                                     ["collision-detection", "navigation-pathfinding"], "M"),
                                    ("PLAT.XR.anchors", "Spatial anchors (persistent, shared)", ["network-architect", "persistence-save"], "M"),
                                    ("PLAT.XR.depth-occlusion", "Real-world depth occlusion", ["render-architect"], "M"),
                                    ("PLAT.XR.layers", "Compositor layers (quad/cylinder)", [], "E"),
                                    ("PLAT.XR.gaze-input", "Gaze + pinch interaction", ["input-system"], "M"),
                                    ("PLAT.XR.light-estimation", "Real-world light estimation", ["global-illumination"], "M"),
                                    ("PLAT.XR.mobile-ar", "Phone/tablet AR sessions (ARKit/ARCore class)", [], "E")]:
        ed.cap(cid, name, xr, mat=mat, contrib=contrib, tags="K-FUTURE-10 K-COMPLETE-6")
    # ML runtime split
    ml = "ml-inference-runtime"
    ed.contract_set("C-ML", layer=2, requires=["C-TASK", "C-MEM"], tags="K-FUTURE-2 K-SYSTEMS-18",
                    summary="Model format and packaging, CPU and NPU backends, async invocation, precision classes, "
                            "budgets.")
    ed.contract_add("C-MLGPU", 3, ml, "GPU inference",
                    "Inference as a render-graph pass under async-compute and budget scheduling; weights for in-shader "
                    "networks.", ["C-RG", "C-ML"], tags="K-FUTURE-2 K-FUTURE-3")
    ed.skill_set(ml, profiles=["all"], targets=ALL_T, consumes=["C-TASK", "C-RHI?@C-MLGPU", "C-RG?@C-MLGPU", "C-PAL"],
                 non_responsibilities=[["Vendor upscalers", "reconstruction-upscaling"],
                                       ["In-shader (fused) networks", "shader-system"],
                                       ["Neural feature design", "owning-skill"],
                                       ["Model training", "external:ml-training"]],
                 tags="K-FUTURE-2 K-SYSTEMS-18 K-ARCH-17")
    ed.cap("ML.RT.npu", "NPU backends via platform ML APIs", ml, mat="M", contrib=["platform-architect"],
           tags="K-FUTURE-2 K-SYSTEMS-18")
    ed.cap_set("ML.RT.inference", name="Standalone network inference (GPU, CPU paths)", tags="K-FUTURE-3")
    ed.cap_set("ML.RT.scheduling", name="Inference scheduling within frame budgets incl. online in-frame training",
               tags="K-FUTURE-16")
    # certification
    cc = "certification-compliance"
    ed.contract_add("C-CERT", "P", cc, "External requirements register",
                    "Register of external requirements per program (console cert, Steam Deck Verified, store review, "
                    "law) each mapped to an owning capability; owners must satisfy their entries.", [],
                    universal="all", tags="K-PLATFORM-9")
    for cid, name, contrib, t in [
            ("QA.CERT.programs", "Non-console verification programs (Steam Deck Verified, store review)", ["platform-desktop", "platform-mobile"], "K-PLATFORM-9"),
            ("QA.CERT.store-policy", "Store-policy compliance (account deletion, tracking, IAP rules, alternative stores)", ["platform-services"], "K-PLATFORM-11"),
            ("QA.CERT.monetization-law", "Loot-box & odds-disclosure law", ["platform-services"], "K-PLATFORM-11"),
            ("QA.CERT.regional", "Regional regimes (licensing, real-name, minors' playtime, data localization)", ["platform-services"], "K-PLATFORM-11"),
            ("QA.CERT.export-crypto", "Encryption export compliance", ["security-engineering"], "K-PLATFORM-11"),
            ("QA.CERT.genai", "Rating & platform disclosure for runtime-generated content", ["ai-behavior-perception"], "K-FUTURE-5 K-QUALITY-16")]:
        ed.cap(cid, name, cc, contrib=contrib, tags=t)
    ed.cap("BLD.SYS.platform-sdks", "Platform SDK version management & store/cert-mandated minimums",
           "build-system-toolchains", contrib=["platform-console", "platform-mobile", "platform-desktop", "certification-compliance"],
           tags="K-PLATFORM-8")
    pk = "packaging-release-patching"
    for cid, name, contrib, t in [
            ("BLD.REL.api-redist", "API runtime redistribution (Agility SDK, DXC runtime)", ["rhi-d3d12"], "K-PLATFORM-4"),
            ("BLD.REL.engine-distribution", "Engine SDK/editor binary distribution & installers", [], "K-PROD-3"),
            ("BLD.REL.staged-rollout", "Canary/staged rollout & kill switches", ["online-services-liveops"], "K-PROD-6"),
            ("BLD.REL.end-of-service", "End-of-service: offline fallback, community server release, data export",
             ["online-services-liveops", "network-architect", "dedicated-server"], "K-PROD-7 K-COMPLETE-29")]:
        ed.cap(cid, name, pk, contrib=contrib, tags=t)
    ed.cap_set("BLD.REL.on-demand", name="Install-on-demand & streaming install (AAB/Play Asset Delivery, iOS background "
               "assets)", add_contrib=["platform-mobile"], tags="K-PLATFORM-20")
    ed.cap_set("BLD.REL.packaging", name="Platform packaging & signing (incl. notarization, hardened runtime)",
               tags="K-PLATFORM-15")
    ea = "engine-architect"
    ed.cap("ARCH.REQ.platform-matrix", "Supported-target matrix (OS × ISA × GPU API × store × support tier)", ea,
           contrib=["platform-architect", "build-system-toolchains", "ci-cd-automation", "certification-compliance"],
           tags="K-PLATFORM-16")
    ed.cap_set("ARCH.REQ.hardware-tiers", name="Hardware tier definitions incl. server instance classes and refresh-rate "
               "classes", add_contrib=["dedicated-server"], tags="K-PERF-15")


def apply(ed):
    networking(ed)
    gameplay(ed)
    ui(ed)
    editor_content(ed)
    platform(ed)
