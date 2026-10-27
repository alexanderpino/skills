"""Round-3 revision, part C: tools/editor, platform and architecture-wording findings
(K-TOOLS-3,6-14; K-PLATFORM-1,2,6,8,10,13,14; K-ARCH-5,15,16,17,18,19; K-GAMEPLAY-3)."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def _unt(ed, sid, *ids):
    s = ed.skill(sid)
    s["untrusted_inputs"] = sorted(set(s.get("untrusted_inputs") or []) | set(ids))


def _has(ed, cid):
    try:
        ed._find_cap(cid)
        return True
    except KeyError:
        return False


def _contract(ed, cid, layer, owner, name, summary, requires, tags, **extra):
    ed.contract_add(cid, layer, owner, name, summary, requires=requires, conformance=True,
                    oracle_author="functional-automation-soak", tags=tags, **extra)


def apply(ed):
    cfgs = ed.doc["skill"]["configurations"]

    # ================================================================ TOOLS
    t = "K-TOOLS-3"
    _contract(ed, "C-CMD", 2, "serialization-schema", "Command & transaction core",
              "Serializable diff-based commands, apply/invert, transaction batching, journal and merge hooks; the schema "
              "shared by the editor (C-EDCMD) and runtime edit sessions (C-EDIT).", ["C-SER", "C-REFL", "C-ID"], t)
    ed.cap("CORE.SER.commands", "Serializable command/transaction core (schema, apply/invert, journal, merge hooks)",
           "serialization-schema", contrib=["editor-architect", "modding-ugc", "collaboration-version-control"], tags=t)
    for cid in ("C-EDCMD", "C-EDIT"):
        c = ed.contract(cid)
        ed.contract_set(cid, requires=c["requires"] + ["C-CMD"], tags=t)
    _append(ed, "C-EDIT", "command schema from C-CMD.", t)
    ed.use("editor-architect", "C-CMD", tags=t)
    ed.use("modding-ugc", "C-CMD", tags=t)

    t = "K-TOOLS-6"
    for sid in ("material-system", "gameplay-data", "ui-architect", "localization-i18n", "audio-content-runtime",
                "vfx-particles", "animation-runtime", "animation-graphs", "navigation-pathfinding", "text-fonts",
                "input-system", "gameplay-camera", "cinematics-sequencer"):
        ed.use(sid, "C-RELOAD?", tags=t)

    t = "K-TOOLS-7"
    ed.cap_set("ED.WORLD.partitioned", profiles=["lite3d", "std3d"], tags=t)

    t = "K-TOOLS-8"
    ed.doc["skill"]["profiles"]["addons"]["team-mid"] = "Studios of about 10–150 people (shared DDC, tool telemetry, small-session multi-user)"
    ed.cap_set("CNT.COOK.shared-cache", profiles=["lite3d", "std3d"], tags=t)
    ed.cap("CNT.COOK.cache-fleet", "Multi-site derived-data cache fleet (replication, eviction, cost)",
           "content-pipeline-architect", profiles=["team-large"], tags=t)
    ed.cap_set("ED.COLLAB.multiuser", profiles=["team-mid", "team-large"], tags=t)
    ed.cap_set("ED.ARCH.telemetry", profiles=["team-mid", "team-large"], tags=t)
    cfgs["standard-3d-team-tools"] = {"profiles": ["std3d", "online", "team-mid"], "target": "tools",
                                      "platforms": ["pc"], "target_platforms": ["pc", "console", "server-host"]}
    ed.note(t, "team-mid add-on and configuration standard-3d-team-tools (claimed at M4)")

    t = "K-TOOLS-9"
    ed.use("editor-architect", "C-NETSESSION?", "C-NETLINK?", "C-PREDICT?", "C-SERVER?", tags=t)
    ed.cap_set("ED.ARCH.pie-net", add_contrib=["net-session", "prediction-rollback"], tags=t)

    t = "K-TOOLS-10"
    ed.cap("ED.COLLAB.session-server", "Collaboration session server: transport, auth via XC.SEC.dev-trust access "
           "classes, journal persistence, late join, presence and lock broadcast", "collaboration-version-control",
           contrib=["network-transport", "security-engineering"], profiles=["team-mid", "team-large"], tags=t)
    ed.use("collaboration-version-control", "C-NETLINK?", "C-IPC", "C-CMD", tags=t)

    t = "K-TOOLS-11"
    ed.cap("PLAT.XR.editor-preview", "XR authoring: play-in-headset, device simulator, in-headset editing, "
           "passthrough/anchor/scene-mesh preview", "xr-runtime",
           contrib=["editor-architect", "world-editor-viewport"], tags=t)
    ed.use("xr-runtime", "C-EDCMD", "C-EDVIEW", tool=True, tags=t)
    ed.cap("INP.TOOL.haptics", "Haptic and trigger-effect authoring with on-controller preview",
           "input-devices-haptics", contrib=["audio-content-runtime"], tags=t)
    ed.use("input-devices-haptics", "C-EDCMD", "C-EDHOST", tool=True, tags=t)
    for sid, why in (("xr-runtime", "XR content is authored in domain editors; PLAT.XR.editor-preview covers headset preview."),
                     ("platform-desktop", "OS integration has no designer-authored content."),
                     ("platform-console", "Platform integration; content authored in domain editors."),
                     ("platform-mobile", "Platform integration; mobile preview via RND.TOOL.scalability-preview."),
                     ("platform-web", "Platform integration; web preview via the standard editor play mode."),
                     ("platform-server-host", "Server-host OS integration; no authored content."),
                     ("platform-services", "Service integration; content authored by the games' tooling."),
                     ("online-services-liveops", "Live-ops configuration is data through C-GAMEDATA tooling.")):
        ed.skill_set(sid, authoring=why, tags=t)
    ed.note(t, "check.py: 'platform' joins AUTHORING_WORKSTREAMS")

    t = "K-TOOLS-12"
    for sid in ("functional-automation-soak", "perf-benchmarking", "render-validation", "ci-cd-automation"):
        ed.use(sid, "C-AUTOMATION", tags=t)

    t = "K-TOOLS-13"
    ed.doc["untrusted"]["inputs"].append({"id": "project-tool-code", "validating_owner": "editor-architect",
                                          "parser_owners": ["plugin-system"], "trust": "hostile-local", "mode": "harness",
                                          "limits": "no execution before workspace-trust grant; per-command permission classes"})
    _unt(ed, "editor-architect", "project-tool-code")
    _unt(ed, "plugin-system", "project-tool-code")
    ed.skill("robustness-fuzzing")["fuzz_targets"] = sorted(set(ed.skill("robustness-fuzzing")["fuzz_targets"])
                                                            | {"project-tool-code"})
    ed.note(t, "untrusted input project-tool-code registered (workspace trust before execution)")

    t = "K-TOOLS-14"
    ed.cap("ED.ARCH.async-jobs", "Editor background-job model: progress, cancellation, interaction with open "
           "transactions", "editor-architect", tags=t)
    ed.cap("ED.UI.outliner", "Virtualized scene outliner for 10⁶-object worlds (folders, filtering by data layer/cell)",
           "editor-ui-framework", contrib=["world-data-model"], tags=t)
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] == "L37":
            p["stance_capabilities"] = ["ED.ARCH.async-jobs"]

    # ================================================================ PLATFORM
    t = "K-PLATFORM-1"
    ed.cap_set("PLAT.CON.confidential-slots", name="Confidential implementations of registered slots (IO/decompression "
               "units, audio endpoints, save storage, crash upload, system keyboard/IME/TTS bridge, entitlement SDK, "
               "console pad & adaptive-trigger libraries, sockets/relay, console XR SDK) behind public interfaces "
               "owned by domain skills", add_contrib=["input-devices-haptics", "network-transport",
                                                      "text-fonts", "accessibility"], tags=t)
    _append(ed, "C-CERT", "the shared register is public: id, owner capability and a sanitized paraphrase; "
            "holder-specific TRC text lives only in per-holder confidential partitions under "
            "PLAT.CON.confidential-slots and is never published through the shared register.", t)
    ed.note(t, "confidentiality stays per skill (console-only NDA skills, per holder); no module-level access field")

    t = "K-PLATFORM-2 K-PLATFORM-9"
    ed.doc["skill"]["platform_variants"] = {
        "pc": ["win-x64", "win-arm64", "linux-steamos", "macos"],
        "mobile": ["ios", "android"],
        "xr-standalone": ["android-xr", "visionos"],
        "server-host": ["linux-x64", "linux-arm64"]}
    for sid, v in (("rhi-d3d12", ["pc:win-x64", "pc:win-arm64"]),
                   ("rhi-vulkan", ["pc:win-x64", "pc:win-arm64", "pc:linux-steamos", "mobile:android",
                                   "xr-standalone:android-xr"]),
                   ("rhi-metal", ["pc:macos", "mobile:ios", "xr-standalone:visionos"])):
        ed.skill(sid)["variants"] = v
    ed.note(t, "skills.json platform_variants; RHI backends declare variants; check.py proves needs_implementer closure "
               "per platform variant (macOS needs Metal, iOS needs Metal, Android needs Vulkan)")
    ed.cap_set("ARCH.REQ.platform-matrix", name="Platform matrix (OS × ISA × API × store) generated from "
               "skills.json platform_variants and implementer variants", tags=t)

    t = "K-PLATFORM-6"
    ed.cap_set("PLAT.PAL.cloud-streaming", name="Cloud-streaming policy (session detection, latency budget, device-kind "
               "changes); platform work in PLAT.CON/DESK.cloud-streaming", mat="E",
               add_contrib=["input-system", "ui-architect", "runtime-scalability", "frame-orchestration"], tags=t)
    ed.cap("PLAT.CON.cloud-streaming", "Console-build cloud streaming (streamed console titles)", "platform-console", tags=t)
    ed.cap("PLAT.DESK.cloud-streaming", "PC-build cloud streaming (touch-overlay controls, UI-scale tier)",
           "platform-desktop", contrib=["input-system"], tags=t)
    ed.doc["radar"]["entries"] = [e for e in ed.doc["radar"]["entries"] if e["tech"] != "Cloud game streaming targets"]
    ed.note(t, "cloud streaming is established: radar entry removed")

    t = "K-PLATFORM-8"
    ed.cap_set("RND.RHI.console", add_contrib=["rhi-d3d12"], tags=t)
    ed.nonresp_add("rhi-console", "Shared D3D12 code base (Xbox-class backend reuses it)", "rhi-d3d12", tags=t)

    t = "K-PLATFORM-10"
    for e in ed.doc["radar"]["entries"]:
        if e["tech"].startswith("GLES / WebGL"):
            e["class"] = "E"
            e["revisit"] = "Browser-capability share from web analytics/portal SDKs (measured by platform-web) shows "\
                           ">10% of a shipping web audience without WebGPU"
    ed.cap("PLAT.WEB.audience-share", "Browser-capability share measurement (WebGPU, threads, memory) from web "
           "analytics and portal SDKs", "platform-web", contrib=["observability-telemetry"], tags=t)
    ed.note(t, "web targets require WebGPU; docs/00 states it; the trigger is now an external measure")

    t = "K-PLATFORM-13"
    ed.cap("PLAT.MOB.windowing", "Resizable/multi-window mobile apps (iPadOS windowing, foldable posture, ChromeOS/"
           "desktop modes)", "platform-mobile", tags=t)
    ed.cap_set("PLAT.PAL.display", name="Display enumeration, modes, DPI, HDR & VRR capability, dynamic HDR/EDR headroom "
               "events", add_contrib=["post-color-hdr"], tags=t)
    ed.cap_set("PLAT.PAL.lifecycle", add_contrib=["platform-web"], tags=t)

    t = "K-PLATFORM-14"
    ed.note(t, "untrusted inputs device-db-updates, push-payloads, clipboard-dragdrop registered with fuzz targets")
    for i, own, par, tr, lim in (("device-db-updates", "platform-architect", [], "semi-trusted-signed",
                                  "schema/rollback/staged rollout"),
                                 ("push-payloads", "platform-mobile", [], "hostile-remote", "length/schema"),
                                 ("clipboard-dragdrop", "platform-architect", ["editor-ui-framework"], "hostile-local",
                                  "size/type allow-list")):
        ed.doc["untrusted"]["inputs"].append({"id": i, "validating_owner": own, "parser_owners": par, "trust": tr,
                                              "mode": "harness", "limits": lim})
        for sid in [own] + par:
            _unt(ed, sid, i)
    ed.skill("robustness-fuzzing")["fuzz_targets"] = sorted(set(ed.skill("robustness-fuzzing")["fuzz_targets"])
                                                            | {"device-db-updates", "push-payloads",
                                                               "clipboard-dragdrop"})

    t = "K-PLATFORM-1"
    ed.note(t, "docs/00 §8: first-party service SDK material is NDA territory held by console skills; platform-services "
               "keeps the cross-store model")

    # ================================================================ ARCH minors
    t = "K-ARCH-5 K-GAMEPLAY-5"
    s = ed.skill("gameplay-systems-toolkit")
    ed.skill_set("gameplay-systems-toolkit", purpose=s["purpose"].replace(", camera system", "").replace(", photo mode", ""),
                 tags=t)
    ed.nonresp_add("gameplay-systems-toolkit", "Gameplay cameras & photo mode", "gameplay-camera", tags=t)
    ed.unuse("gameplay-systems-toolkit", "C-VIEW", tags=t)
    ed.use("gameplay-systems-toolkit", "C-VIEW?", tags=t)

    t = "K-ARCH-15 K-GAMEPLAY-3"
    if _has(ed, "GAM.SYS.tags"):
        ed.cap_move("GAM.SYS.tags", "GAM.DATA.tags", tags=t)
        ed.cap_set("GAM.DATA.tags", name="Gameplay tag dictionary, hierarchical tag queries, redirects/renames",
                   owner="gameplay-data", add_contrib=["gameplay-systems-toolkit"], tags=t)
    if _has(ed, "GAM.TOOL.tags-abilities"):
        ed.cap_set("GAM.TOOL.tags-abilities", name="Ability and effect authoring (tag dictionary editor in GAM.TOOL.data)",
                   tags=t)
    c = ed.contract("C-ABILITY")
    ed.contract_set("C-ABILITY", summary=c["summary"].replace("tag queries, ", "").replace("; tag queries", ""), tags=t)
    ed.contract("C-GAMEDATA")["oracle_author"] = "functional-automation-soak"

    t = "K-ARCH-16"
    g = ed.skill("global-illumination")
    ed.skill_set("global-illumination", purpose=g["purpose"].replace("SDF scene representations",
                 "SDF/software ray queries consumed via C-RTAS"), tags=t)
    f = ed.skill("fluid-simulation")
    ed.skill_set("fluid-simulation", purpose=f["purpose"].replace("shallow-water simulation, ", "")
                 .replace(", shallow-water simulation", "").replace("shallow-water simulation", "volumetric fluids"), tags=t)
    ed.cap_set("PRF.BENCH.regression", name="Regression detection (bisection via BLD.CI.bisection)", tags=t)
    ct = ed.contract("C-TYPES")
    ed.contract_set("C-TYPES", summary=ct["summary"].replace("vetted hashinggraphic primitives wrapper", "hashing")
                    .replace("hashinggraphic", "hashing"), tags=t)
    ed.contract_set("C-NETLINK", name="Network links & channels", tags=t)
    _append(ed, "C-AI", "tactical/environment queries (EQS class), not world queries (C-ENV).", t)

    t = "K-ARCH-17"
    ed.nonresp("robustness-fuzzing", [["Threat model", "security-engineering"], ["Fixing parsers", "owning-skill"]], tags=t)
    ed.nonresp("ml-inference-runtime", [x if "arbitration" not in x[0] else
                                        ["GPU queue/budget arbitration of C-MLGPU work", "render-graph-scheduling"]
                                        for x in ed.skill("ml-inference-runtime")["non_responsibilities"]], tags=t)

    t = "K-ARCH-18"
    ed.cap_set("PLAT.MOB.frame-pacing", name="Mobile present-rate/pacing backends implementing C-PRESENT/C-PAL "
               "(selection policy in CORE.SCALE.actuators)", tags=t)

    t = "K-ARCH-19 K-SIM-8"
    ed.cap_move("PHY.FLUID.cellular", "PHY.2D.cellular", tags=t)
    ed.cap_set("PHY.2D.cellular", name="Grid/cellular material & fluid simulation (falling sand, liquid/gas/heat grids), "
               "2D-capable, deterministic", owner="physics-2d", add_contrib=["fluid-simulation"], tags=t)
    ed.use("fluid-simulation", "C-DET", "C-TASK", "C-SNAPSHOT?", tags="K-SIM-8")
    ed.doc["skill"]["configurations"]["sandbox-2d-client"]["profiles"] = ["min2d", "sandbox"]
