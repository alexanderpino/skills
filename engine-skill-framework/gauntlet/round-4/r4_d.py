"""Round-4 revision, part D: completeness, anti-legacy, gameplay/content, test and security findings
(K-COMPLETE-1..4; K-LEGACY-4..6; K-GAMEPLAY-3..5,7..14; K-TEST-1,3,5..10; K-SEC-1..3,7)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round-3"))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap, _rename  # noqa: E402

REF3 = {
    "C-PHYS": "analytic physics scenes (pendulum, stacking, restitution) and Bullet/Jolt differential runs",
    "C-ANIM": "reference pose-error corpora (mocap clips with known retarget results)",
    "C-AUDIO": "BS.1770 loudness references and bit-exact offline renders",
    "C-SPATIAL": "analytic transform and large-world precision reference cases",
    "C-NAV": "navmesh connectivity references (Recast test maps) and A* optimality cases",
    "C-REP": "netem-class link scenarios and wire-format golden captures",
    "C-PREDICT": "rollback conformance scenarios (GGPO/Netcode-for-GameObjects-class reference traces)",
    "C-NET": "packet-capture corpora and protocol dissector cases",
    "C-TEXT": "HarfBuzz/ICU shaping and bidi conformance corpora (UAX #9/#14/#29 test files)",
    "C-LOC": "CLDR plural/gender and MessageFormat 2 test suites",
    "C-VIDEO": "codec conformance streams (AV1/H.264 reference bitstreams)",
    "C-COLOR": "ACES/OCIO reference transforms and ICC test charts",
    "C-RT": "analytic ray-scene references (Cornell box, furnace tests)",
    "C-RG": "barrier/aliasing validation-layer scenarios",
    "C-SHADER": "differential execution of reference compute kernels across backends; compile-all-permutations gate",
    "C-INPUT": "recorded device-report corpora and mapping golden cases",
    "C-SAVE": "save round-trip and migration corpora from historical builds",
    "C-DIALOGUE": "graph soft-lock and define-use reference graphs",
    "C-ABILITY": "effect-stacking rule tables from published system specs",
}
FALLBACK3 = "reference scenes or analytic cases declared in the conformance suite; derived goldens are regression-only"


def apply(ed):
    # ================================================================ COMPLETE
    t = "K-COMPLETE-1"
    _cap(ed, "GAM.SYS.timers", "Game-time timers and latent actions (delays, cooldowns, wait-N-seconds): time-domain aware, "
         "pausable, saveable, replicated, deterministic", "gameplay-systems-toolkit",
         contrib=["persistence-save", "frame-orchestration", "prediction-rollback"], tags=t)
    ed.cap_set("GAM.SCR.level-scripting", add_contrib=["gameplay-systems-toolkit"], tags=t)

    t = "K-COMPLETE-2"
    _cap(ed, "CORE.SCALE.safe-boot", "Startup crash-loop detection and safe-mode boot: crash marker, N-strike rollback of "
         "settings to last-known-good, plugin/mod disable", "runtime-scalability",
         contrib=["persistence-save", "crash-diagnostics"], tags=t)

    t = "K-COMPLETE-3"
    _cap(ed, "RND.ARCH.cluster-sync", "Genlock/frame-lock cluster rendering for virtual production", "render-architect", "X",
         profiles=["experimental"], tags=t)
    _cap(ed, "ANM.CINE.timecode", "Timecode sync for virtual production and sequencer playback", "cinematics-sequencer", "X",
         profiles=["experimental"], tags=t)
    for tech, cap, owner in (("Virtual-production cluster sync", "RND.ARCH.cluster-sync", "render-architect"),
                             ("Virtual-production timecode", "ANM.CINE.timecode", "cinematics-sequencer")):
        _radar(ed, tech, "X", owner, [cap], "Broadcast and LED-volume pipelines use dedicated tooling",
               "A shipped title runs synchronised cluster output", "external virtual-production tooling")

    t = "K-COMPLETE-4"
    _cap(ed, "BLD.SYS.ide-integration", "IDE/debugger integration: compile_commands.json and project generation, debugger "
         "visualizers for handles, containers and entity ids (new handle/container types ship visualizers)",
         "build-system-toolchains", contrib=["containers-core-types", "scripting-runtime", "developer-experience-docs"], tags=t)

    # ================================================================ LEGACY
    t = "K-LEGACY-4"
    pats = ed.doc["legacy"]["patterns"]
    for p in pats:
        if p["id"] == "L27":
            p["pattern"] = "ECS for everything (new dogma)"
            p["stance_capabilities"] = ["CORE.OBJ.hybrid", "CORE.ECS.bridges", "ARCH.GOV.adr"]
    pats += [
        {"id": "L81", "pattern": "GPU-driven everywhere (new dogma)", "detection": "GPU-driven path forced on tiers where "
         "it loses", "default_stance": "Per-tier submission strategy by ADR", "justification_owner": "render-architect",
         "stance_capabilities": ["RND.ARCH.submission-strategy"], "contradiction_terms": [r"gpu-driven everywhere"]},
        {"id": "L82", "pattern": "Neural/ML by default (new dogma)", "detection": "ML features without measured "
         "advantage or fallback", "default_stance": "ML behind optional contracts with fallbacks and evidence ADRs",
         "justification_owner": "ml-inference-runtime", "stance_capabilities": ["ML.RT.scheduling", "ARCH.GOV.adr"],
         "contradiction_terms": [r"ml by default"]},
        {"id": "L83", "pattern": "Async physics by default (new dogma)", "detection": "decoupled physics stepping "
         "without rollback or determinism review", "default_stance": "Stepping mode chosen per netcode family by ADR",
         "justification_owner": "physics-architect", "stance_capabilities": ["PHY.ARCH.async", "PHY.ARCH.stepping"],
         "contradiction_terms": [r"async physics by default"]}]

    t = "K-LEGACY-5"
    for cid, old, new in (("C-SEQ", "event/track callbacks", "batched event/track outputs via C-FLOW"),
                          ("C-ID", "lifetime rules, events.", "lifetime rules.")):
        c = ed.contract(cid)
        ed.contract_set(cid, summary=c["summary"].replace(old, new), tags=t)
    _append(ed, "C-ANIM", "animation events are delivered as batched outputs via C-FLOW", t)
    _append(ed, "C-PHYS", "contact events are delivered as batched, filtered outputs (no per-body synchronous callbacks)", t)
    for p in pats:
        if p["id"] == "L19":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"PHY.ARCH.events"})

    t = "K-LEGACY-6"
    _rename(ed, "CNT.ID.registry", "; cooked, chunked, on-demand registry with streamed indexes and an incremental editor "
            "registry (never a full scan or residency at boot)", tags=t)
    _append(ed, "C-ASSET", "registry queries are served from chunked, on-demand indexes.", t)
    pats.append({"id": "L84", "pattern": "Full asset-registry scan or residency at boot", "detection": "registry loaded in "
                 "full at startup", "default_stance": "Cooked, chunked, on-demand registry with streamed indexes",
                 "justification_owner": "content-pipeline-architect", "stance_capabilities": ["CNT.ID.registry"],
                 "contradiction_terms": [r"full (?:asset-)?registry scan"]})

    t = "K-GAMEPLAY-12"
    for p in pats:
        if p["id"] == "L72":
            p["stance_capabilities"] = sorted(set(p["stance_capabilities"]) | {"UI.LOC.messageformat", "UI.LOC.terms"})
    pats += [
        {"id": "L85", "pattern": "Text without shaping or grapheme awareness", "detection": "ASCII, bitmap-font or "
         "code-unit text handling", "default_stance": "Shaping, bidi and grapheme segmentation",
         "justification_owner": "text-fonts", "stance_capabilities": ["UI.TXT.shaping", "UI.TXT.bidi"],
         "contradiction_terms": [r"code-unit text"]},
        {"id": "L86", "pattern": "Sentence assembly by string concatenation", "detection": "concatenated fragments for "
         "localized sentences", "default_stance": "MessageFormat-class messages with terms and agreement",
         "justification_owner": "localization-i18n", "stance_capabilities": ["UI.LOC.messageformat", "UI.LOC.terms"],
         "contradiction_terms": [r"string concatenation for (?:sentences|messages)"]},
        {"id": "L87", "pattern": "Synchronous per-request pathfinding and navmesh rebuild", "detection": "path or "
         "rebuild on the calling thread", "default_stance": "Batched async path queries and incremental rebuild",
         "justification_owner": "navigation-pathfinding", "stance_capabilities": ["GAM.AI.pathfinding", "GAM.AI.navmesh"],
         "contradiction_terms": [r"synchronous (?:per-request )?pathfinding"]},
        {"id": "L88", "pattern": "Hard-coded gameplay tunables", "detection": "constants in code",
         "default_stance": "Data-driven tuning assets", "justification_owner": "gameplay-data",
         "stance_capabilities": ["GAM.DATA.tuning"], "contradiction_terms": [r"hard-?coded tunables"]}]

    # ================================================================ GAMEPLAY
    t = "K-GAMEPLAY-3"
    for cid, nm, owner, contrib in (
            ("GAM.NARR.validation", "Narrative/dialogue graph validation: unreachable/dead-end nodes, soft-locks, fact/flag "
             "define-use, per-locale VO/caption/loc coverage", "narrative-dialogue",
             ["localization-i18n", "audio-content-runtime", "accessibility"]),
            ("GAM.DATA.validation", "Gameplay data referential and range integrity validation", "gameplay-data", []),
            ("ANM.CINE.validation", "Sequencer validation (missing bindings, timing conflicts)", "cinematics-sequencer", []),
            ("GAM.CAM.validation", "Camera rig validation (collision, blend and comfort limits)", "gameplay-camera", []),
            ("INP.ACT.validation", "Action-map validation (conflicts, unreachable actions, glyph coverage)", "input-system", [])):
        _cap(ed, cid, nm + " (registers with CNT.VAL.submit-gate; suite authorship by the contract's oracle_author)", owner,
             contrib=contrib, tags=t)
        ed.cap_set("CNT.VAL.submit-gate", add_contrib=[owner], tags=t)

    t = "K-GAMEPLAY-4"
    _cap(ed, "CORE.FRAME.local-time-scale", "Per-entity and per-team time scale (hit-stop, bullet-time on a subset) obeyed by "
         "animation, physics, VFX, audio, abilities and movement; deterministic and recorded", "frame-orchestration",
         contrib=["animation-architect", "physics-architect", "audio-content-runtime", "vfx-particles",
                  "gameplay-architect"], tags=t)
    _cap(ed, "GAM.SYS.cues", "Feedback cues (hit-stop, shake, flash, sound, haptics) as predicted, deduplicated events",
         "gameplay-systems-toolkit", contrib=["prediction-rollback", "replication", "gameplay-camera",
                                              "input-devices-haptics"], tags=t)

    t = "K-GAMEPLAY-5"
    _cap(ed, "ANM.GRAPH.actions", "Action/montage playback: slots layered into graphs, sections and jumps, blend in/out, "
         "root-motion policy, notify-window ownership and replication participation", "animation-graphs",
         contrib=["animation-runtime", "prediction-rollback", "character-movement", "gameplay-systems-toolkit"], tags=t)
    ed.cap_set("ANM.TOOL.asset-editor", add_contrib=["animation-graphs"], tags=t)

    t = "K-GAMEPLAY-7"
    _cap(ed, "GAM.FW.turns", "Turn/phase/command-log substrate: ordered commands, undo/history, deterministic replay, "
         "clonable-state API for search", "gameplay-architect",
         contrib=["determinism-replay", "ai-behavior-perception", "persistence-save", "online-services-liveops"], tags=t)
    _cap(ed, "GAM.MOVE.grid", "Grid movement", "character-movement", tags=t)

    t = "K-GAMEPLAY-8"
    _cap(ed, "GAM.SAVE.unknown-content", "Unknown-record preservation and quarantine; mod/DLC dependency manifest per save",
         "persistence-save", contrib=["modding-ugc", "serialization-schema"], tags=t)
    _cap(ed, "GAM.SAVE.slots", "Save-slot catalogue: locale-independent metadata (playtime, thumbnail, version), per-user "
         "ownership and cross-platform portability", "persistence-save", contrib=["platform-services", "ui-architect"], tags=t)

    t = "K-GAMEPLAY-9"
    _cap(ed, "GAM.SYS.interaction", "Interaction and target selection: interactable discovery and focus, hold-to-interact, "
         "device-glyph prompts, soft-target/lock-on selection, arbitration among candidates and local players; server-"
         "validated online", "gameplay-systems-toolkit",
         contrib=["input-system", "ui-architect", "animation-runtime", "gameplay-camera"], tags=t)

    t = "K-GAMEPLAY-10"
    _cap(ed, "AUD.ARCH.routing", "Audio routing: endpoint hot-swap with format renegotiation, multi-endpoint output "
         "(main mix plus per-local-player devices), OS interruption handling", "audio-architect",
         contrib=["platform-architect", "platform-console", "input-devices-haptics", "gameplay-architect"], tags=t)
    ed.cap_set("PLAT.PAL.system-events", add_contrib=["audio-architect"], tags=t)

    t = "K-GAMEPLAY-11"
    _cap(ed, "UI.TXT.editing", "Text editing model: caret, selection, grapheme-cluster movement, bidi caret, password and "
         "character-limit fields", "text-fonts", contrib=["ui-architect", "platform-architect", "accessibility"], tags=t)
    _cap(ed, "UI.TXT.segmentation", "Text segmentation (UAX #29 grapheme, word and sentence boundaries)", "text-fonts", tags=t)
    _cap(ed, "UI.LOC.collation", "Locale collation, case mapping and sorting", "localization-i18n", tags=t)

    t = "K-GAMEPLAY-13"
    ed.skill_set("gameplay-systems-toolkit", purpose="Reusable gameplay systems: abilities, effects and attributes, hit "
                 "detection and projectiles, building, aim assist, volumes, impacts, timers, cues and interaction, batched "
                 "deferred spawning (pooling only where measured), gameplay message routing.", tags=t)
    ed.skill_set("gameplay-data", purpose=ed.skill("gameplay-data")["purpose"].rstrip(".") + ", gameplay tag dictionary and "
                 "surface types.", tags=t)
    ed.cap_set("UI.FW.maps", add_contrib=["asset-cook-processors", "render-architect"], tags=t)

    t = "K-GAMEPLAY-14"
    ed.use("gameplay-data", "C-A11YRT?", tags=t)
    ed.cap_set("UI.A11Y.assists", add_contrib=["gameplay-data"],
               name=ed._find_cap("UI.A11Y.assists")[1][1].rstrip(".") + "; assist class (cosmetic, input-only, "
               "simulation-affecting): simulation-affecting assists are replicated and recorded", tags=t)
    ed.cap_set("GAM.DATA.tuning", add_contrib=["accessibility"], tags=t)
    ed.cap_set("XC.SEC.score-integrity", add_contrib=["accessibility"], tags=t)

    # ================================================================ TEST
    t = "K-TEST-1"
    procs = [s["id"] for s in ed.doc["skill"]["skills"] if s.get("kind") == "process"]
    ed.doc["milestone"]["milestones"][0]["process_skills"] = sorted(procs)
    ed.doc["milestone"]["_doc"] += " Process skills (oracle authors, validators, critics) are staffed from M0."
    ed.note(t, "process skills are listed as staffed at M0 (milestones[0].process_skills); check.py requires it")

    t = "K-TEST-3"
    n = 0
    for c in ed.doc["contract"]["contracts"]:
        if c.get("conformance") and c["layer"] != "P" and not c.get("oracle_reference"):
            c["oracle_reference"] = [REF3.get(c["id"], FALLBACK3)]
            n += 1
    ed.note(t, f"oracle_reference on {n} layer 3–5 conformance contracts; derived goldens are regression-only")

    t = "K-TEST-5"
    _cap(ed, "QA.AGENT.holdout-hygiene", "Holdout anti-probing protocol: per-package query budget, retirement of failed cases "
         "replaced from a seeded generator, fixed failure taxonomy without input detail, redacted-repro channel, "
         "overfitting canary, queries logged in provenance", "test-architect",
         contrib=["program-orchestration", "ci-cd-automation"], tags=t)

    t = "K-TEST-6"
    for cid, kind, owner in (("C-XRVIEW", "scripted OpenXR runtime", "xr-runtime"),
                             ("C-VIDEO", "reference media decoder with conformance streams", "media-playback"),
                             ("C-ML", "reference inference runtime with tolerance tables", "ml-inference-runtime"),
                             ("C-MLGPU", "reference GPU inference pass", "ml-inference-runtime"),
                             ("C-INTEGRITY", "third-party anti-cheat SDK stub", "anti-cheat-integrity"),
                             ("C-SIGN", "software HSM/KMS emulator", "security-runtime"),
                             ("C-VCS", "in-process VCS server emulator", "collaboration-version-control")):
        ed.contract_set(cid, boundary=True, test_double={"kind": kind, "owner": owner}, tags=t)
    _cap(ed, "PLAT.CON.public-slot-reference", "Public conformance-passing null implementation of every confidential slot so "
         "non-cleared agents run the same suites", "platform-console", contrib=["platform-architect"], tags=t)

    t = "K-TEST-7"
    _cap(ed, "QA.RENDER.shader-conformance", "Shader toolchain validation: differential execution of reference compute kernels "
         "across backends, all-permutation compile gate, compiler-fuzz lane, compiler/driver version qualification",
         "render-validation", contrib=["shader-system", "rhi-core"], tags=t)

    t = "K-TEST-8"
    c = ed.contract("C-TESTHOST")
    ed.contract_set("C-TESTHOST", oracle_reference=["out-of-tree reference verifier written by the oracle author, run over the "
                                                    "canary suite outside the runner"], tags=t)
    _append(ed, "C-DET", "recorded state-hash traces are regression-only; an analytic or fixed-point determinism reference "
            "scenario anchors cross-platform claims.", t)

    t = "K-TEST-9"
    _cap(ed, "QA.ROBUST.minimization", "Test-case reduction: fuzz-input, replay-trace and scene minimization, required for "
         "failures handed to implementers", "robustness-fuzzing",
         contrib=["determinism-replay", "render-validation"], tags=t)

    t = "K-TEST-10"
    ed.cap_set("NET.TRANS.simulation", name=ed._find_cap("NET.TRANS.simulation")[1][1].rstrip(".") + "; replays a governed "
               "corpus of captured WAN, Wi-Fi and cellular traces", tags=t)
    ed.cap_set("QA.SIM.netsim", add_contrib=["network-transport"], tags=t)

    # ================================================================ SEC
    t = "K-SEC-1"
    ed.cap_set("ARCH.ORG.sensitive-paths", name=ed._find_cap("ARCH.ORG.sensitive-paths")[1][1].rstrip(".") + "; the agent "
               "control plane (ledger, access classes, critics.json, check.py, registry, human-gates register, seeds) needs "
               "human-gate approval and a fitness function diffs it against the protected branch", tags=t)

    t = "K-SEC-2"
    for iid, owner, parsers, why in (
            ("lan-discovery", "net-session", ["network-transport"], "pre-auth broadcast/mDNS replies: length/rate limits"),
            ("community-server-config", "dedicated-server", ["modding-ugc"], "ruleset/config file size/depth limits"),
            ("hid-reports", "input-devices-haptics", [], "report/descriptor size and structure limits"),
            ("remote-build-results", "ci-cd-automation", ["build-system-toolchains"], "cache/result signature and size limits"),
            ("patch-payloads", "packaging-release-patching", ["package-formats-vfs"], "signature, size and chunk limits")):
        _input(ed, iid, owner, parsers, "hostile-remote" if iid != "hid-reports" else "hostile-local", why)
    ed.note(t, "server listings are covered by server-list-entries and localization imports by localization-exchange")

    t = "K-SEC-3"
    for iid, owner in (("tool-outputs", "security-engineering"), ("agent-memory", "program-orchestration"),
                       ("contributed-patches", "engine-product-management")):
        ed.doc["untrusted"]["inputs"].append({"id": iid, "validating_owner": owner, "parser_owners": [],
                                              "trust": "agent-input", "mode": "redteam",
                                              "limits": "quarantined as data; no instruction authority"})
        _unt(ed, owner, iid)
    ed.cap_set("XC.SEC.agent-redteam", add_contrib=["engine-product-management"], tags=t)

    t = "K-SEC-7"
    _rename(ed, "XC.SEC.hardening", "; side-channel row (retpoline/SSBD policy, tenant isolation on shared hosts)", tags=t)
    _append(ed, "C-SIGN", "constant-time test obligation in the conformance suite.", t)
