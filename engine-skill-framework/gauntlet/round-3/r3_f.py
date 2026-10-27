"""Round-3 revision, part F: completeness sweeps, anti-legacy catalogue, gameplay/content findings
(K-COMPLETE-2..17; K-LEGACY-12..16; K-GAMEPLAY-2,4,6..13)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r3_d import _add, _append, _input, _radar  # noqa: E402


def _cap(ed, cid, name, owner, mat="E", contrib=None, profiles=None, tags=""):
    aid = cid.rsplit(".", 1)[0]
    try:
        ed._area(aid)
    except KeyError:
        ed.area(aid, aid.split(".")[1].title(), tags=tags)
    ed.cap(cid, name, owner, mat, contrib=contrib, profiles=profiles, tags=tags)


def _rename(ed, cid, suffix=None, name=None, tags=""):
    _, c = ed._find_cap(cid)
    ed.cap_set(cid, name=name or (c[1].rstrip(".") + suffix), tags=tags)


PATTERNS = [
    # id, pattern, detection, stance, owner, stance caps, contradiction terms
    ("L60", "float32 world positions & whole-world origin rebasing", "single-precision absolute positions; teleporting "
     "the world to hide jitter", "Large-world coordinates: double/tiled positions and local-frame rendering",
     "world-architect", ["WLD.SPACE.lwc", "WLD.PART.lwc-policy"], r"float32 world position|whole-world origin rebas"),
    ("L61", "Locks, allocation or IO in the real-time audio callback", "mutex, malloc or file read reachable from the "
     "audio render thread", "Lock-free, allocation-free audio render thread; control via lock-free queues",
     "audio-architect", ["AUD.ARCH.engine", "CORE.JOBS.thread-model"], r"locks? in the (?:audio )?callback"),
    ("L62", "#ifdef über-shader permutation explosion", "unbounded static permutations per material",
     "Permutation budgets with specialization constants and pipeline libraries", "shader-system",
     ["RND.SHADER.permutation-budget", "RND.SHADER.permutations"], r"über-?shader|permutation explosion"),
    ("L63", "Gameplay reading raw device state or key codes", "key/button codes or polling in gameplay code",
     "Actions and contexts through C-INPUT mapping", "input-system", ["INP.ACT.mapping"],
     r"raw (?:key|device) (?:codes|state)"),
    ("L64", "Raw struct-dump saves without a schema", "memcpy'd structs as save files",
     "Schema-versioned saves with migration", "persistence-save", ["GAM.SAVE.model", "GAM.SAVE.migration"],
     r"struct[- ]dump"),
    ("L65", "Fixed 30/60 Hz assumptions, sleep limiters and blocking vsync present", "sleep-based frame limiting; "
     "constants of 1/60", "Present timeline with pacing feedback and latency-aware limiters", "frame-orchestration",
     ["CORE.FRAME.present-timeline", "CORE.FRAME.latency"], r"sleep[- ]based (?:frame )?limit|fixed 60 ?hz"),
    ("L66", "Per-item general heap allocation on hot paths", "malloc/new per entity, event or command",
     "Pools, arenas and budget-enforced allocators", "memory-allocators",
     ["CORE.MEM.allocators", "CORE.MEM.budget-enforcement"], r"per-item (?:heap )?allocation"),
    ("L67", "#ifdef platform sprawl", "platform conditionals in shared code", "Platform backends behind contracts",
     "platform-architect", ["ARCH.STRUCT.platform-backends"], r"platform #ifdef|ifdef sprawl"),
    ("L68", "Timestamp-based derived data", "cook/build outputs keyed by file times", "Content-addressed derived data "
     "cache", "content-pipeline-architect", ["CNT.COOK.ddc"], r"timestamp[- ]based (?:cook|derived)"),
    ("L69", "Flaky-test tolerance (retry until green)", "retries or quarantines that hide nondeterminism",
     "Flake classification and root-cause policy", "test-architect", ["QA.STRAT.flaky"], r"retry until green"),
    ("L70", "Average-fps performance targets", "budgets stated as mean fps", "Per-tier frame-time budgets with "
     "percentiles", "performance-architect", ["PRF.METH.budgets"], r"average[- ]fps|mean fps"),
    ("L71", "Big-bang releases without staged rollout", "all-at-once patch to every client",
     "Canary/staged rollout with kill switches", "packaging-release-patching", ["BLD.REL.staged-rollout"],
     r"big-bang release"),
    ("L72", "Baked-string localization", "translated text embedded in code or textures",
     "Keyed string tables with plural/gender rules", "localization-i18n", ["UI.LOC.strings"], r"hard-?coded (?:ui )?strings"),
    ("L73", "Reconstruction/frame generation as budget substitute", "budgets or latency judged on generated frames",
     "Upscaling/frame generation is an optional presentation layer; budgets and latency judged on rendered frames with a "
     "minimum base rate per tier", "performance-architect", ["RND.RECON.framegen", "PRF.LOAD.pacing-latency"],
     r"counted toward (?:the )?(?:simulation|latency) budget"),
]
TERMS = {
    "L19": r"immediate synchronous|global event bus",
    "L30": r"variable[- ]timestep|render frame delta",
    "L38": r"snapshot-based undo",
    "L39": r"monolithic binary",
    "L42": r"\bTCP\b|all-reliable",
    "L45": r"exact-build",
    "L58": r"after tonemapping",
}


def apply(ed):
    # ============================================================ LEGACY
    t = "K-LEGACY-12 K-LEGACY-13 K-LEGACY-15"
    pats = ed.doc["legacy"]["patterns"]
    for pid, pat, det, stance, owner, caps, term in PATTERNS:
        pats.append({"id": pid, "pattern": pat, "detection": det, "default_stance": stance, "justification_owner": owner,
                     "stance_capabilities": caps, "contradiction_terms": [term]})
    for p in pats:
        if p["id"] in TERMS:
            p["contradiction_terms"] = [TERMS[p["id"]]]
    ed.doc["legacy"]["adr_exceptions"] = []
    ed.doc["legacy"]["_doc"] += " contradiction_terms are regexes: check.py fails when a capability name, contract " \
        "name/summary or skill purpose matches one, unless adr_exceptions names the pattern and the item with its ADR."
    ed.note(t, "legacy catalogue: patterns L60–L73; contradiction_terms scanned by check.py over capability names, "
               "contract text and skill purposes; adr_exceptions carry ADRs")
    ed.cap_set("AUD.ARCH.engine", name="Audio engine architecture & threading: lock-free, allocation-free real-time render "
               "thread; control via lock-free queues", tags=t)
    ed.cap_set("RND.RECON.framegen", name="Frame generation / interpolation as an optional presentation layer; never counted "
               "toward simulation or latency budgets; minimum base rate per tier", tags=t)

    t = "K-LEGACY-14"
    _rename(ed, "CORE.CONC.sync", "; no subsystem-wide locks on frame paths", tags=t)
    _rename(ed, "ED.ARCH.process", name="Editor process model: asynchronous cancellable editor jobs with progress; the UI "
            "thread never blocks (in-process vs out-of-process by ADR)", tags=t)
    _rename(ed, "ED.ARCH.transactions", "; serializable diff-based commands", tags=t)
    _rename(ed, "WLD.MODEL.file-per-object", "; with semantic merge", tags=t)
    _rename(ed, "RES.MGMT.dependencies", "; soft references, budgeted dependency-aware loading", tags=t)
    _rename(ed, "PHY.ARCH.events", "; batched change sets, queries batched, mutations deferred", tags=t)
    _rename(ed, "NET.TRANS.reliability", "; unreliable-first channels with per-message reliability/ordering classes", tags=t)
    for p in pats:
        if p["id"] == "L23":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"BLD.SYS.dev-surface-exclusion",
                                                                              "ARCH.STRUCT.layering"})
    ed.note("K-LEGACY-16", "docs/00 §6 wording and rows follow the contradiction-term scan (docs step)")

    # ============================================================ COMPLETE / GAMEPLAY content
    t = "K-COMPLETE-2 K-GAMEPLAY-2"
    _cap(ed, "AUD.TOOL.cook", "Audio cook processors: per-platform codec encoding, SRC, loudness normalization, bank/pack "
         "and stream-chunk/seek-table layout, per-locale VO packs", "audio-content-runtime",
         contrib=["audio-dsp-mixing", "asset-cook-processors"], tags=t)
    ed.use("audio-content-runtime", "C-COOK", tool=True, tags=t)
    _cap(ed, "CNT.COOK.video", "Video transcode cook (codec/bitrate ladder, muxed tracks, HDR metadata)",
         "media-playback", contrib=["asset-cook-processors"], tags=t)
    _cap(ed, "RND.MEDIA.encode", "Runtime/offline video encode (clip export, movie-render output)", "media-playback",
         contrib=["cinematics-sequencer"], tags=t)
    ed.use("media-playback", "C-COOK", tool=True, tags=t)

    t = "K-COMPLETE-3"
    _cap(ed, "QA.CERT.legal-surfaces", "Player-facing legal surfaces: ToS/EULA/privacy-policy presentation, versioned "
         "acceptance and re-acceptance gating, SBOM-generated OSS notices, middleware logo/splash obligations",
         "certification-compliance", contrib=["ui-architect", "platform-services", "privacy-data-protection"], tags=t)

    t = "K-COMPLETE-4"
    _cap(ed, "PLAT.MOB.location", "Device geolocation: fused location, geofences, background/approximate permissions, "
         "battery policy, location privacy class", "platform-mobile", contrib=["privacy-data-protection"], tags=t)
    _cap(ed, "PLAT.XR.geospatial", "Geospatial/VPS localization & Earth-anchored content", "xr-runtime", "M",
         contrib=["asset-import-interchange"], tags=t)
    _radar(ed, "Geospatial localization (VPS) & Earth-anchored content", "M", "xr-runtime", ["PLAT.XR.geospatial"],
           "Platform VPS/geospatial APIs (2022–2025)", "Two platforms expose stable geospatial anchors",
           "PLAT.XR.anchors (local/shared anchors) with PLAT.MOB.location")

    t = "K-COMPLETE-5"
    _cap(ed, "INP.ACT.stick-processing", "Analog stick processing: radial/axial deadzones, anti-deadzone, response "
         "curves, calibration, drift compensation", "input-system", tags=t)
    _cap(ed, "GAM.SYS.aim-assist", "Aim assist: magnetism/friction/slowdown, prediction-consistent and server-validated, "
         "per-device tuning and crossplay fairness", "gameplay-systems-toolkit",
         contrib=["input-system", "prediction-rollback", "anti-cheat-integrity"], tags=t)

    t = "K-COMPLETE-6"
    _cap(ed, "NET.SRV.community-hosting", "Player-hosted dedicated servers: redistributable server build, config/ruleset "
         "files, listing via NET.SESS.server-browser, join-time content negotiation via NET.SESS.content-set",
         "dedicated-server", contrib=["net-session", "modding-ugc", "packaging-release-patching"], tags=t)

    t = "K-COMPLETE-7"
    _cap(ed, "UI.FW.web-view", "Embedded web view & external-browser/device-code auth flows (navigation allow-lists, "
         "isolation)", "ui-architect", contrib=["platform-services", "security-engineering"], tags=t)
    _input(ed, "web-content", "ui-architect", ["platform-services"], "hostile-remote",
           "navigation allow-list; process isolation; no engine bridge by default")

    t = "K-COMPLETE-8"
    _cap(ed, "RND.VFX.cpu-sim", "CPU (SIMD) particle simulation path: low-count, deterministic and gameplay-readable "
         "emitters with the same graph semantics", "vfx-particles", tags=t)

    t = "K-COMPLETE-9"
    _cap(ed, "ANM.DEF.damage", "Skinned-mesh dismemberment/slicing & layered damage masks", "deformation-skinning",
         contrib=["character-rendering", "destruction-fracture"], tags=t)
    _cap(ed, "PHY.CTRL.vehicle-damage", "Vehicle body deformation & part detachment with replication", "vehicle-physics",
         contrib=["destruction-fracture", "replication"], tags=t)

    t = "K-COMPLETE-10"
    _cap(ed, "AUD.CONTENT.emitters", "World emitter management: area/spline/volume emitters, ambience beds, cell-streamed "
         "partitions and pre-voice culling", "audio-content-runtime",
         contrib=["spatial-audio-acoustics", "world-architect"], tags=t)

    t = "K-COMPLETE-11"
    _cap(ed, "BLD.CI.leak-protection", "Per-recipient forensic and visible watermarking of distributed pre-release "
         "builds, leak attribution", "ci-cd-automation", contrib=["security-engineering"], tags=t)

    t = "K-COMPLETE-12"
    ed.note(t, "ED.UI.outliner added under K-TOOLS-14")

    t = "K-COMPLETE-13"
    _cap(ed, "ED.UI.accessibility", "Editor & tool accessibility: screen-reader tree, keyboard-only operation, "
         "scalable/colour-safe themes", "editor-ui-framework", contrib=["accessibility"], tags=t)

    t = "K-COMPLETE-14"
    _cap(ed, "CNT.IMP.vector", "SVG & Lottie/Rive-class vector/motion-graphics import", "asset-import-interchange",
         contrib=["render-2d-vector"], tags=t)

    t = "K-COMPLETE-15"
    _cap(ed, "RND.GEO.spline-mesh", "Spline-deformed meshes (roads, rails, pipes, cables)", "geometry-pipeline", tags=t)
    _cap(ed, "WLD.PCG.roads", "Road/rail network generation: terrain conforming, intersections, lane-graph export",
         "procedural-generation", contrib=["terrain", "navigation-pathfinding"], tags=t)

    t = "K-COMPLETE-16"
    _cap(ed, "RND.ARCH.multi-display", "Spanned multi-display output with per-display off-axis projection and bezel "
         "correction", "render-architect", tags=t)
    _cap(ed, "INP.DEV.head-tracking", "Head-tracking devices (IR/webcam) as C-VIEW input", "input-devices-haptics", tags=t)

    t = "K-COMPLETE-17"
    _cap(ed, "ED.COLLAB.backup", "Depot, ledger, cache and signing-infrastructure backup and disaster recovery with "
         "restore drills (RPO/RTO)", "collaboration-version-control", contrib=["program-orchestration"], tags=t)

    t = "K-GAMEPLAY-4"
    ed.contract_add("C-CAMERA", 4, "gameplay-camera", "Gameplay camera requests",
                    "Camera mode/hint requests with priority and blend, per-local-player rig binding, shake/impulse assets "
                    "scaled by accessibility settings, framing targets; output is a view source for C-VIEW.",
                    requires=["C-VIEW"], conformance=True, oracle_author="functional-automation-soak", tags=t)
    for sid, dep in (("gameplay-systems-toolkit", "C-CAMERA?"), ("character-movement", "C-CAMERA?"),
                     ("cinematics-sequencer", "C-CAMERA?")):
        ed.use(sid, dep, tags=t)
    ed.note(t, "vehicle-physics and narrative-dialogue (layer-3 modules) publish camera hints as data on C-VEHICLE and "
               "C-DIALOGUE that gameplay-camera consumes; they do not consume C-CAMERA (no upward link) (partial)")
    _append(ed, "C-VIEW", "shake and FOV channels are final composition of view sources; shake content and its "
            "accessibility scaling belong to C-CAMERA.", t)

    t = "K-GAMEPLAY-6"
    ed.cap_set("NET.SESS.local-players", name="Several local players per connection: sub-player IDs, per-player "
               "auth/guest privileges, per-player ownership & prediction, drop-in/drop-out",
               add_contrib=["replication", "prediction-rollback"], tags=t)

    t = "K-GAMEPLAY-7"
    _cap(ed, "UI.LOC.terms", "Localizable terms with per-locale grammatical attributes (gender, animacy, case forms, "
         "articles, particles) and agreement in substituted messages", "localization-i18n",
         contrib=["gameplay-data", "narrative-dialogue"], tags=t)

    t = "K-GAMEPLAY-8"
    ed.use("character-movement", "C-GAMEDATA", tags=t)
    ed.use("character-movement", "C-EDCMD", "C-EDHOST", "C-EDVIEW", tool=True, tags=t)
    _cap(ed, "GAM.TOOL.movement", "Movement tuning assets & live tuning, trajectory/mode-history and network-correction "
         "visualization", "character-movement", contrib=["visual-debugging-tools", "gameplay-data"], tags=t)

    t = "K-GAMEPLAY-9"
    ed.cap_move("INP.DEV.haptic-assets", "AUD.CONTENT.haptic-assets", tags=t)
    ed.cap_set("AUD.CONTENT.haptic-assets", owner="audio-content-runtime", add_contrib=["input-devices-haptics"], tags=t)
    ed.cap_move("INP.TOOL.haptics", "AUD.TOOL.haptics", tags=t)
    ed.cap_set("AUD.TOOL.haptics", name="Haptic effect authoring & device preview", owner="audio-content-runtime",
               add_contrib=["input-devices-haptics"], tags=t)
    ed.use("audio-content-runtime", "C-EDCMD", "C-EDHOST", tool=True, tags=t)

    t = "K-GAMEPLAY-10"
    _cap(ed, "GAM.NARR.scenes", "Systemic dialogue scene generation: shot/camera/gesture/look-at selection from line data, "
         "per-locale retiming, manual override baked into C-SEQ", "narrative-dialogue",
         contrib=["cinematics-sequencer", "gameplay-camera", "motion-synthesis", "facial-animation"], tags=t)

    t = "K-GAMEPLAY-11"
    ed.cap_set("ANM.FACE.lipsync", name="Phoneme/viseme & procedural audio-driven lip sync, per-locale", mat="E", tags=t)
    _cap(ed, "ANM.FACE.lipsync-ml", "ML lip sync (audio-driven neural facial animation)", "facial-animation", "M",
         contrib=["ml-inference-runtime"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "ANM.FACE.lipsync" in e["capabilities"]:
            e["capabilities"] = ["ANM.FACE.lipsync-ml"]
            e["fallback"] = "ANM.FACE.lipsync (phoneme/viseme lip sync)"

    t = "K-GAMEPLAY-12"
    _cap(ed, "UI.TXT.cjk-layout", "Ruby annotations (furigana/zhuyin) & vertical text layout (UAX #50)", "text-fonts",
         contrib=["ui-architect"], tags=t)

    t = "K-GAMEPLAY-13"
    ed.cap_set("CORE.SCALE.profiles", name="Device-profile application & per-context knob sets (active view count/"
               "split-screen, XR) & scalability knob registry", add_contrib=["gameplay-architect", "render-architect"],
               tags=t)
