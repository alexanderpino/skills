"""Round-2 revision, part G: K-COMPLETE and K-GAMEPLAY findings (missing capabilities, gameplay-facing contracts,
accessibility runtime path, localization end to end, camera skill)."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def apply(ed):
    # ================================================================ COMPLETE
    t = "K-COMPLETE-1"   # seed S15 (runtime retargeting); residual: character customization
    ed.cap("ANM.DEF.modular-assembly", "Modular character assembly, mesh merging & runtime material/texture baking",
           "deformation-skinning", contrib=["character-rendering", "material-system"], tags=t)
    ed.cap("GAM.FW.customization-descriptor", "Character customization descriptor with save/replication/streaming "
           "participation", "gameplay-architect", contrib=["persistence-save", "replication", "deformation-skinning"],
           tags=t)

    t = "K-COMPLETE-2"
    ed.cap("ANM.SYN.motion-warping", "Motion warping of root motion to gameplay targets (vault, mantle, attack "
           "alignment)", "motion-synthesis", contrib=["character-movement"], tags=t)
    ed.cap("ANM.SYN.multi-actor", "Synchronized multi-actor animation scenes (paired/contextual; alignment, roles, "
           "predicted & replicated as one unit)", "motion-synthesis",
           contrib=["ik-procedural-animation", "prediction-rollback", "character-movement"], tags=t)
    ed.skill_set("motion-synthesis", profiles=["lite3d", "std3d"], tags=t)

    t = "K-COMPLETE-4 K-GAMEPLAY-12"
    ed.cap("GAM.AI.team-visibility", "Per-faction visibility fields & line-of-sight/FOV (grid/hex/navmesh, GPU "
           "variant), explored state, deterministic, feeding fog rendering, AI knowledge and replication relevancy",
           "ai-behavior-perception", contrib=["replication", "anti-cheat-integrity", "render-2d-vector",
                                              "crowd-simulation"], tags=t)
    ed.cap("GAM.SYS.markers", "POI/marker registry shared by gameplay, UI and map rendering", "gameplay-systems-toolkit",
           contrib=["ui-architect", "render-architect"], tags=t)

    t = "K-COMPLETE-5"
    ed.cap("NET.TRANS.local-network", "LAN/local-wireless session discovery & hosting without online services "
           "(broadcast/mDNS, console ad-hoc)", "network-transport", contrib=["platform-console", "net-session"],
           tags=t)

    t = "K-COMPLETE-7"
    ed.cap("PLAT.XR.body-face", "Body, face & eye-expression tracking inputs (OpenXR extensions) with biometric "
           "privacy class", "xr-runtime", "M", contrib=["privacy-data-protection"], tags=t)
    ed.cap("ANM.IK.avatar-embodiment", "Full-body avatar IK from sparse tracking & tracked-expression retargeting",
           "ik-procedural-animation", contrib=["facial-animation", "replication", "xr-runtime"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if e["tech"].startswith("Mixed reality"):
            e["capabilities"].append("PLAT.XR.body-face")

    t = "K-COMPLETE-9"   # seed S14; residual: patch-size budgets & layout stability were implicit
    ed.cap_set("BLD.REL.patching", name="Delta/chunk patching with patch-size budgets & layout stability across "
               "builds", tags=t)

    t = "K-COMPLETE-11"
    ed.cap("RND.GI.planar", "Planar reflections (clip-plane re-render, tier-scaled)", "global-illumination", tags=t)
    ed.cap("RND.ARCH.portals", "Portal views with recursive rendering and spatial-query transform through portals",
           "render-architect", contrib=["collision-detection", "spatial-audio-acoustics"], tags=t)

    t = "K-COMPLETE-12"
    ed.cap("AUD.CONTENT.music-clock", "Sample-accurate musical clock, quantized scheduling & beat events to gameplay",
           "audio-content-runtime", contrib=["frame-orchestration"], tags=t)
    for sec in ("brief_domains", "brief_targets", "discovered_domains"):
        for k in list(ed.doc["seed"].get(sec, {})):
            if "rhythm" in k.lower():
                ed.doc["seed"][sec][k] = sorted(set(ed.doc["seed"][sec][k] + ["AUD.CONTENT.music-clock"]))

    t = "K-COMPLETE-13"
    ed.cap("INP.ACT.sequences", "Deterministic input-sequence & gesture recognition (motion/charge commands, leniency "
           "windows, negative edge)", "input-system", tags=t)

    t = "K-COMPLETE-14"
    ed.cap("GAM.AI.search", "Game-tree search AI (minimax, MCTS, information-set search) over clonable rule state",
           "ai-behavior-perception", tags=t)

    t = "K-COMPLETE-15"
    ed.cap("PLAT.SVC.trials", "Demo & time-limited trial SKUs with entitlement gating & save carry-over",
           "platform-services", contrib=["packaging-release-patching"], tags=t)

    t = "K-COMPLETE-16 K-GAMEPLAY-20"
    ed.cap("PLAT.PAL.pointer-shell", "Cursor management (hardware/software cursors, confinement, relative mode), "
           "clipboard, file dialogs, drag-and-drop", "platform-architect",
           contrib=["input-devices-haptics", "platform-desktop"], tags=t)
    ed.cap("INP.ACT.touch-controls", "On-screen touch controls (virtual sticks/buttons) feeding actions",
           "input-system", contrib=["ui-architect"], tags=t)
    ed.cap_move("INP.DEV.injection", "INP.ACT.injection", tags=t)
    ed.cap_set("INP.ACT.injection", name="Action-level input injection for bots & tests (headless-capable)",
               owner="input-system", add_contrib=["input-devices-haptics"], tags=t)

    t = "K-COMPLETE-17"
    ed.cap("INP.DEV.companion", "Companion/second-screen devices as networked input devices", "input-devices-haptics",
           contrib=["network-transport", "platform-web"], tags=t)

    t = "K-COMPLETE-21"
    ed.cap("GAM.SCR.hotfix", "Script/logic hotfix delivery within store policy (signed, versioned, rollback)",
           "scripting-runtime", contrib=["packaging-release-patching", "certification-compliance"], tags=t)

    t = "K-COMPLETE-22"
    ed.cap("UI.FW.maps", "World map/minimap service (cooked map tiles, streamed markers, discovery overlay)",
           "ui-architect", contrib=["world-architect", "gameplay-systems-toolkit"], tags=t)

    t = "K-COMPLETE-23"
    ed.cap("CORE.MATH.bignum", "Large-magnitude/arbitrary-precision numeric types with canonical serialization",
           "math-simd-numerics", tags=t)

    t = "K-COMPLETE-24"
    ed.cap("ED.UI.localization", "Editor & tool UI localization", "editor-ui-framework",
           contrib=["localization-i18n"], tags=t)

    # ================================================================ GAMEPLAY
    t = "K-GAMEPLAY-1"
    ed.use("audio-content-runtime", "C-A11YRT", tags=t)
    for sid in ("cinematics-sequencer", "gameplay-architect", "gameplay-systems-toolkit", "input-system",
                "narrative-dialogue", "post-color-hdr"):
        ed.use(sid, "C-A11YRT?", tags=t)
    _append(ed, "C-A11YRT", "caption sources: dialogue, audio-event captions, sequencer; settings read through a "
            "snapshot like C-CFG.", t)
    ed.note(t, "check.py: contributors to UI.A11Y capabilities consume C-A11YRT")

    t = "K-GAMEPLAY-2"
    ed.contract_add("C-ABILITY", 4, "gameplay-systems-toolkit", "Abilities, effects & attributes",
                    "Ability activation, effects, attributes, tag queries, gameplay messages, hit results.",
                    requires=["C-GAME", "C-GAMEDATA"], conformance=True, tags=t)
    ed.contract_add("C-CROWD", 4, "crowd-simulation", "Crowds & mass agents",
                    "Agent spawn/despawn, batched queries, LOD and tier hooks, traffic promotion requests.",
                    requires=["C-NAV", "C-SIGNIF"], conformance=True, tags=t)
    ed.contract_add("C-SEQ", 4, "cinematics-sequencer", "Sequences",
                    "Sequence playback, actor binding, event/track callbacks, skip and blend policy.",
                    requires=["C-ANIM", "C-VIEW"], conformance=True, tags=t)
    ed.use("ai-behavior-perception", "C-ABILITY?", tags=t)
    ed.use("gameplay-architect", "C-SEQ?", "C-CROWD?", tags=t)
    _append(ed, "C-GAMEDATA", "gameplay tag registry and tag queries.", t)
    ed.use("narrative-dialogue", "C-GAMEDATA?", tags=t)

    t = "K-GAMEPLAY-3"
    ed.contract_add("C-AI", 4, "ai-behavior-perception", "AI agents",
                    "Brain assignment (behavior/state trees, utility, HTN), perception stimulus sources, smart-object "
                    "claim/release, environment query service; learned/LLM providers plug in through C-AIAGENT.",
                    requires=["C-GAME", "C-NAV"], conformance=True, tags=t)
    for sid in ("gameplay-architect", "gameplay-systems-toolkit", "crowd-simulation"):
        ed.use(sid, "C-AI?", tags=t)
    ed.use("ai-behavior-perception", "C-MOVE?", tags=t)

    t = "K-GAMEPLAY-4"
    for sid in ("gameplay-architect", "ui-architect", "ai-behavior-perception", "narrative-dialogue",
                "cinematics-sequencer", "gameplay-systems-toolkit"):
        ed.use(sid, "C-SCRIPT?", tags=t)
    _append(ed, "C-SCRIPT", "script-authored systems declare access sets and are scheduled through C-FRAME.", t)
    ed.use("scripting-runtime", "C-ID", "C-ECS?", tags=t)

    t = "K-GAMEPLAY-5"
    _append(ed, "C-CFG", "settings are declared as scoped C-CFG entries (device/user/cloud); the user layer is a "
            "read-only projection populated by the persisted settings store (GAM.SAVE.settings).", t)
    _append(ed, "C-SAVE", "persisted player-settings store per scope, populating the C-CFG user layer.", t)
    _append(ed, "C-A11YRT", "accessibility settings are C-CFG settings entries.", t)
    ed.cap_set("GAM.SAVE.settings", name="Persisted player-settings store per scope (device/user/cloud), first-boot "
               "availability; settings declared through C-CFG", tags=t)

    t = "K-GAMEPLAY-6"   # seed S08 (message formatting); residual: gather + locale-aware shaping
    ed.cap("UI.LOC.gather", "Localizable-text value type in reflection & gather from reflected and cooked data",
           "localization-i18n", contrib=["reflection-metadata", "gameplay-data"], tags=t)
    ed.use("localization-i18n", "C-REFL", tags=t)
    for sid in ("gameplay-data", "gameplay-systems-toolkit", "input-system", "persistence-save"):
        ed.use(sid, "C-LOC?", tags=t)
    _append(ed, "C-TEXT", "runs carry BCP-47 language/script; locale-aware line breaking.", t)
    ed.cap("UI.TXT.locale-shaping", "Locale-aware shaping & breaking (Han variant selection, dictionary breaking for "
           "Thai/Lao/Khmer, kinsoku)", "text-fonts", tags=t)
    ed.use("text-fonts", "C-PAL", tags=t)

    t = "K-GAMEPLAY-7"
    for sid in ("navigation-pathfinding", "ai-behavior-perception", "scripting-runtime", "gameplay-systems-toolkit",
                "gameplay-architect", "gameplay-data"):
        ed.use(sid, "C-DET?", tags=t)
    ed.cap_set("QA.SIM.mass-agents", name="Mass-agent throughput & determinism validation runs incl. desync-hash lanes "
               "on lockstep configurations", tags=t)

    t = "K-GAMEPLAY-9"
    ed.cap_set("ANM.ARCH.sync", name="Animation-side obligations within the canonical simulation schedule (root-motion "
               "deltas and trajectory via C-ANIM; authority in GAM.MOVE.root-motion)", tags=t)
    ed.cap_set("GAM.MOVE.root-motion", add_contrib=["animation-architect"], tags=t)
    s = ed.skill("character-movement")
    ed.nonresp("character-movement", [x if x[0] != "Animation selection" else
                                      ["Animation selection", ["animation-graphs", "motion-synthesis"]]
                                      for x in s["non_responsibilities"]], tags=t)

    t = "K-GAMEPLAY-10"
    ed.unuse("motion-synthesis", "C-MOVE", tags=t)
    _append(ed, "C-ANIM", "trajectory/desired-motion input and root-motion delta output.", t)
    ed.note(t, "check.py: a skill without provided or implemented contracts takes its nearest ancestor's code layer "
               "as its floor")

    t = "K-GAMEPLAY-13"
    for sid in ("animation-architect", "animation-runtime", "animation-graphs"):
        s = ed.skill(sid)
        ed.skill_set(sid, profiles=["minimal"] + s["profiles"], tags=t)
    for cid in ("ANM.RT.compression", "ANM.RT.pose-history"):
        ed.cap_set(cid, profiles=["lite3d", "std3d"], tags=t)

    t = "K-GAMEPLAY-14"
    ed.use("ui-architect", "C-VIEW", tags=t)
    _append(ed, "C-UI", "per-local-player UI roots and focus owners; world-to-view projection for in-world UI.", t)

    t = "K-GAMEPLAY-16"
    for cid, name, con in [
            ("UI.A11Y.sound-visualization", "Non-speech captions & directional sound visualization (caption/direction "
             "metadata on audio events)", ["audio-content-runtime"]),
            ("UI.A11Y.audio-description", "Audio description for cinematics & gameplay narration mode",
             ["cinematics-sequencer", "narrative-dialogue"]),
            ("UI.A11Y.palettes", "Semantic color tokens & redundant shape/icon palettes for UI and gameplay highlights",
             ["ui-architect", "post-color-hdr"])]:
        ed.cap(cid, name, "accessibility", contrib=con, tags=t)
    ed.use("accessibility", "C-AUDIO?", tags=t)

    t = "K-GAMEPLAY-17"
    ed.area("GAM.CAM", "Gameplay camera", tags=t)
    ed.skill_add(tags=t, id="gameplay-camera", name="Gameplay Camera", tier="expert", parent="gameplay-architect",
                 profiles=["all"], kind="runtime", targets=["client", "headless-client", "tools"],
                 workstream="gameplay",
                 purpose="Gameplay camera as its own discipline: camera rigs and modes as C-VIEW sources, blending, "
                         "collision and occlusion handling, framing, 2D cameras (dead zones, parallax, pixel snapping), "
                         "comfort and accessibility motion options, photo mode.",
                 non_responsibilities=[["View arbitration", "spatial-transforms"],
                                       ["Cinematic cameras", "cinematics-sequencer"],
                                       ["XR head pose", "xr-runtime"]],
                 expertise=["real-time cameras (Haigh-Hutchinson)", "camera feel & comfort", "2D camera design"],
                 consumes=["C-VIEW", "C-GAME", "C-PHYS?", "C-INPUT?", "C-A11YRT?"])
    ed.cap_move("GAM.SYS.camera", "GAM.CAM.rigs", tags=t)
    ed.cap_set("GAM.CAM.rigs", owner="gameplay-camera", tags=t)
    ed.cap_move("GAM.SYS.photo", "GAM.CAM.photo", tags=t)
    ed.cap_set("GAM.CAM.photo", owner="gameplay-camera", tags=t)
    ed.cap("GAM.CAM.2d", "2D cameras: dead zones, parallax, pixel snapping", "gameplay-camera", tags=t)
    ed.cap("GAM.CAM.comfort", "Camera comfort & accessibility motion options (shake, FOV, head-bob)", "gameplay-camera",
           contrib=["accessibility", "xr-runtime"], tags=t)
    ed.cap("GAM.TOOL.camera", "Camera rig authoring & preview", "gameplay-camera", tags=t)
    ed.use("gameplay-camera", "C-EDCMD", "C-EDHOST", "C-EDVIEW", tool=True, tags=t)
    s = ed.skill("cinematics-sequencer")
    ed.nonresp("cinematics-sequencer", [x if x[0] != "Gameplay camera" else ["Gameplay camera", "gameplay-camera"]
                                        for x in s["non_responsibilities"]], tags=t)
    for k in ed.doc["critic"]["critics"]:
        if k["id"] == "K-GAMEPLAY" and "gameplay-camera" not in k["scope"]:
            k["scope"].append("gameplay-camera")
    ed.cap_set("WLD.SPACE.views", rm_contrib=["gameplay-systems-toolkit"], add_contrib=["gameplay-camera"], tags=t)

    t = "K-GAMEPLAY-18"
    _append(ed, "C-GAMEDATA", "the live override layer is a sink of the single C-LIVE remote-config payload "
            "(precedence in CORE.LIFE.config).", t)
    _append(ed, "C-CFG", "the remote/live layer is a sink of the single C-LIVE remote-config payload.", t)
    ed.cap_set("CORE.LIFE.config", rm_contrib=["platform-services"], add_contrib=["online-services-liveops"], tags=t)
