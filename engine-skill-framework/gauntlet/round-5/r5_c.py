"""Round-5 revision, part C: production, future-proofing, anti-legacy, gameplay, test and security findings
(K-PROD-1..6; K-FUTURE-1..3,6; K-LEGACY-6,9; K-GAMEPLAY-2..12; K-TEST-1..5,7,8,10,11,13; K-SEC-2..7)."""
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "round-3"))
sys.path.insert(0, os.path.join(R, "round-4"))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap, _rename  # noqa: E402
from r4_c import _claim, _gate, _ms  # noqa: E402

REFS = {
    "C-WORLD": "streaming-cell traversal scenarios from open-world benchmarks; analytic coverage tests",
    "C-MATIF": "MaterialX/OpenPBR reference renders and furnace tests",
    "C-RSCENE": "delta-extraction equivalence against a full-scene rebuild",
    "C-TEMPORAL": "supersampled reference sequences and motion-vector reprojection error",
    "C-DRAW2D": "pixel-exact sprite/tilemap reference frames from an independent rasterizer",
    "C-SVC": "platform SDK sample suites and store sandbox accounts",
    "C-UI": "W3C/Yoga flexbox layout test suites and focus-navigation reference graphs",
    "C-GAME": "reference games' scripted playthroughs with recorded state hashes",
    "C-SCRIPT": "language conformance suites (Lua test suite, ECMAScript test262 class) and sandbox-escape corpora",
    "C-COOK": "cook determinism corpora: identical inputs across machines produce identical outputs",
    "C-EDCMD": "undo/redo property tests against a model editor",
    "C-GRAPH": "graph compile round-trip corpora and adversarial graph cases",
    "C-BUILD": "reproducible-build comparison against a clean-room build",
    "C-PKG": "patch-chain corpora from historical builds and delta-size references",
    "C-REPLAY": "cross-build replay corpora with recorded hashes",
    "C-ENV": "analytic terrain/water/wind query cases",
    "C-INSTANCES": "instance-scene delta streams against a full rebuild",
    "C-GEOLOD": "cluster-LOD error-bound analytic cases and reference meshes",
    "C-VT": "page-table/feedback reference traces against a full-residency render",
    "C-LIGHT": "analytic light-transport scenes (Cornell box, furnace) via the reference path tracer",
    "C-GI": "reference path-traced GI captures",
    "C-ATMOS": "published atmospheric scattering reference tables",
    "C-GAMEDATA": "schema/referential-integrity corpora and spreadsheet round-trip cases",
    "C-AIAGENT": "deterministic decision-trace corpora for provider swap tests",
    "C-A11YRT": "WCAG/XAG test suites and screen-reader (NVDA/VoiceOver) walkthroughs",
    "C-DEVUI": "overlay golden cases and stripped-shipping binary scans",
    "C-EDHOST": "panel-embedding integration cases across editors",
    "C-LIVE": "service sandbox environments of the real backends",
    "C-XRVIEW": "OpenXR conformance test suite",
    "C-MLGPU": "GPU-vs-CPU inference parity with tolerance tables",
    "C-SCENETEX": "per-view texture layout cases against per-path reference frames",
    "C-LIGHTENV": "light-environment publication cases against an independent evaluator",
    "C-TRANSLUCENT": "OIT reference renders (depth-peeling ground truth)",
    "C-PCG": "seeded generation determinism corpora",
    "C-TARGETPLAT": "deploy/run/debug smoke suites on real devkits and emulators",
    "C-NETSESSION": "netem-class join/leave/reconnect scenarios",
    "C-SERVER": "orchestrator sandbox drain/readiness scenarios",
    "C-SHARD": "multi-node migration scenarios under partition and process-kill faults",
    "C-SRVDATA": "Jepsen-class consistency and idempotency checks",
    "C-EDVIEW": "picking/gizmo interaction property tests",
    "C-VCS": "real VCS server sandboxes (Perforce/Git) with merge conflict corpora",
    "C-EDIT": "permission and budget abuse corpora for edit sessions",
    "C-AUTOMATION": "automation-API protocol corpora",
    "C-INTEGRITY": "cheat-tool traces and validator false-positive corpora",
    "C-SEQ": "sequencer timing references against frame-accurate exports",
    "C-VFX": "particle-system determinism and budget scenarios",
    "C-PTREF": "analytic furnace scenes and an external renderer (PBRT/Mitsuba) differential",
    "C-HOSTAUTH": "quota/overload scenarios with load generators",
    "C-CAMERA": "blend/collision reference paths and comfort-limit cases",
    "C-REWIND": "lag-compensation reference traces with known hit outcomes",
}
PLACEHOLDER = "reference scenes or analytic cases declared in the conformance suite; derived goldens are regression-only"


def apply(ed):
    # ================================================================ PROD
    t = "K-PROD-1"
    ed.cap_set("ARCH.ORG.human-gates", name=ed._find_cap("ARCH.ORG.human-gates")[1][1].rstrip(")") + "; legal instrument and "
               "clearance class with named roles (counsel, data-protection officer, security lead, platform account holder))",
               tags=t)
    for mid, cap, val in (("M1", "QA.CERT.licenses", "XC.SEC.supply-chain"), ("M2", "CNT.ID.rights", "QA.CERT.licenses"),
                          ("M2", "QA.CERT.legal-surfaces", "UI.FW.validation"), ("M2", "QA.CERT.ratings", "QA.FUNC.compat"),
                          ("M2", "QA.CERT.export-crypto", "XC.SEC.testing"), ("M7", "ARCH.PROD.licensing-model", "QA.CERT.licenses"),
                          ("M7", "ARCH.PROD.upstreaming", "QA.CERT.code-provenance")):
        _gate(ed, mid, cap, val)

    t = "K-PROD-2"
    for mid, rel in (("M2", "preview"), ("M4", "beta"), ("M6", "release candidate")):
        _ms(ed, mid)["engine_release"] = rel
    _gate(ed, "M2", "XC.EXT.upgrade", "QA.FUNC.compat-corpus")
    m7 = _ms(ed, "M7")
    m7["exit"] = m7["exit"].replace("from the previous release", "from the M6 release candidate and earlier previews")

    t = "K-PROD-3"
    for mid, cap, val in (("M0", "ARCH.ORG.ownership-ledger", "QA.AGENT.gate-canaries"),
                          ("M0", "ARCH.ORG.agent-continuity", "QA.AGENT.test-integrity"),
                          ("M1", "ARCH.ORG.change-requests", "QA.AGENT.oracle-independence"),
                          ("M1", "ARCH.ORG.critic-calibration", "XC.SEC.agent-redteam"),
                          ("M1", "ARCH.ORG.human-capacity", "QA.AGENT.baseline-governance"),
                          ("M4", "ARCH.ORG.escalation", "QA.AGENT.oracle-change-control")):
        _gate(ed, mid, cap, val)

    t = "K-PROD-4 K-PROD-5"
    ed.note(t, "gates added for oracle-change-control-class validators via other gates; validators are constrained by the "
               "check.py independence rule (different owner, non-governance workstream), so key-custody/incident/sandbox/"
               "mutation-gate cannot move to same-owner security or test validators (partial)")

    t = "K-PROD-6"
    _gate(ed, "M2", "BLD.REL.packaging", "QA.CERT.prechecks")
    _gate(ed, "M4", "BLD.REL.patching", "QA.FUNC.compat-corpus")
    _gate(ed, "M4", "BLD.REL.dlc", "QA.FUNC.compat-corpus")

    # ================================================================ FUTURE
    t = "K-FUTURE-1"
    for cid in ("PHY.DEST.procedural", "NET.PRED.physics-rollback", "ML.RT.sequence-exec", "CORE.MATH.deterministic",
                "PLAT.PAL.cloud-render-host"):
        ed.cap_set(cid, mat="X", profiles=["experimental"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if any(c in e["capabilities"] for c in ("PHY.DEST.procedural", "NET.PRED.physics-rollback", "ML.RT.sequence-exec",
                                                "CORE.MATH.deterministic", "PLAT.PAL.cloud-render-host")):
            e["class"] = "X"
    ed.note(t, "five M rows contradicting their own evidence reclassified to X (opt-in, fallbacks kept); shipped_titles "
               "fields and a numeric check are not added (partial)")

    t = "K-FUTURE-2"
    ed.cap_set("RND.RT.cluster-blas", mat="X", profiles=["experimental"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "RND.RT.cluster-blas" in e["capabilities"]:
            e["capabilities"] = [c for c in e["capabilities"] if c != "RND.RT.cluster-blas"]
    _radar(ed, "Cluster acceleration structures", "X", "ray-tracing-infrastructure", ["RND.RT.cluster-blas"],
           "NVIDIA-only cluster BLAS API", "A vendor-neutral D3D12 or Vulkan KHR cluster-AS API ships",
           "proxy-mesh BLAS per cluster LOD level (RND.RT.lod)")

    t = "K-FUTURE-3"
    _cap(ed, "NET.TRANS.pq-kex", "Post-quantum hybrid key exchange (X25519MLKEM768 class) with algorithm ids in handshake "
         "formats and a handshake size that fits the MTU budget", "network-transport", "M", contrib=["security-engineering"],
         tags=t)
    _radar(ed, "Post-quantum hybrid key exchange", "M", "network-transport", ["NET.TRANS.pq-kex"],
           "Hybrid X25519MLKEM768 default in browsers and OpenSSL 3.5 (2025)", "Two game transports ship hybrid KEX",
           "classical key exchange with algorithm agility (NET.TRANS.crypto)")

    t = "K-FUTURE-6"
    ed.cap_set("RND.TEX.feedback", mat="X", profiles=["experimental"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "RND.TEX.feedback" in e["capabilities"]:
            e["class"] = "X"
    ed.cap_set("RND.RECON.upscalers", name="Engine temporal upscaler (TAAU class)", tags=t)
    _cap(ed, "RND.RECON.upscalers-ml", "Vendor ML upscaler integrations (DLSS, FSR, XeSS, PSSR class)",
         "reconstruction-upscaling", "M", tags=t)
    _radar(ed, "Vendor ML upscalers", "M", "reconstruction-upscaling", ["RND.RECON.upscalers-ml"],
           "DLSS 4, FSR 4 and PSSR ship in titles (2025)", "Two vendors expose a common integration API",
           "RND.RECON.upscalers (engine temporal upscaler)")

    # ================================================================ LEGACY
    t = "K-LEGACY-6"
    terms = {"L14": r"mirrored copy|O\(scene objects\)", "L35": r"(?<!no )per-frame (?:property )?polling|string-keyed bindings",
             "L38": r"full copy of the affected", "L36": r"step-time callbacks|modify bodies during the step",
             "L16": r"blocking waits on the host thread"}
    for p in ed.doc["legacy"]["patterns"]:
        if p["id"] in terms:
            p["contradiction_terms"] = sorted(set(p.get("contradiction_terms", [])) | {terms[p["id"]]})

    t = "K-LEGACY-9"
    ed.doc["legacy"]["patterns"].append(
        {"id": "L89", "pattern": "Independent per-domain streaming pools", "detection": "each domain sizes and evicts its "
         "own pool", "default_stance": "One arbitrated budget across pools", "justification_owner":
         "resource-streaming-architect", "stance_capabilities": ["RES.MGMT.arbitration", "CORE.MEM.uma"],
         "contradiction_terms": [r"independent (?:per-domain )?streaming pools"]})

    # ================================================================ GAMEPLAY
    t = "K-GAMEPLAY-2"
    _cap(ed, "GAM.MOVE.ai-drive", "Navigation-driven character movement: nav intents and off-mesh links driving C-MOVE modes",
         "character-movement", contrib=["navigation-pathfinding", "ai-behavior-perception"], tags=t)
    _cap(ed, "GAM.AI.agent-profiles", "Nav-agent profiles matching capsule and movement capabilities", "navigation-pathfinding",
         contrib=["character-movement", "character-physics"], tags=t)

    t = "K-GAMEPLAY-3"
    _cap(ed, "UI.FW.settings-model", "Settings screen model: schema-driven categories from C-CFG, apply/restart/dependency "
         "rules, timed display-mode revert, hardware-detected defaults", "ui-architect",
         contrib=["persistence-save", "runtime-scalability", "accessibility", "input-system", "audio-architect"], tags=t)

    t = "K-GAMEPLAY-4"
    _cap(ed, "UI.LOC.runtime-locale", "Runtime active-locale management: OS locale detection, separate text/VO/subtitle language, "
         "fallback chains, live switch re-resolving localized assets, fonts, VO packs and cached text", "localization-i18n",
         contrib=["persistence-save", "audio-content-runtime", "text-fonts", "resource-streaming-architect",
                  "platform-architect"], tags=t)
    _append(ed, "C-LOC", "locale-change event and reload obligations.", t)

    t = "K-GAMEPLAY-5"
    _cap(ed, "UI.FW.local-player-ui", "Local multiplayer UI: per-viewport HUD and safe area, per-player focus and menus, "
         "shared vs per-player screens", "ui-architect",
         contrib=["gameplay-architect", "gameplay-camera", "render-architect", "accessibility"], tags=t)
    ed.cap_set("GAM.FW.local-players", add_contrib=["ui-architect", "gameplay-camera", "persistence-save", "accessibility"],
               tags=t)

    t = "K-GAMEPLAY-6"
    for sid in ("text-fonts", "facial-animation", "cinematics-sequencer", "gameplay-data", "crowd-simulation"):
        ed.use(sid, "C-COOK", tool=True, tags=t)
    for sid in ("facial-animation", "cinematics-sequencer", "gameplay-data"):
        ed.use(sid, "C-IMPORT", tool=True, tags=t)
    for sid in ("ik-procedural-animation", "animation-runtime", "facial-animation"):
        ed.use(sid, "C-EDVIEW", tool=True, tags=t)

    t = "K-GAMEPLAY-7"
    _cap(ed, "ANM.CINE.localized-tracks", "Locale variant audio/subtitle/viseme tracks for authored cutscenes, duration "
         "reconciliation and per-locale validation", "cinematics-sequencer",
         contrib=["localization-i18n", "audio-content-runtime", "facial-animation", "narrative-dialogue"], tags=t)

    t = "K-GAMEPLAY-8"
    _cap(ed, "GAM.AI.nav-streaming", "Streamed, world-partitioned navigation data: per-cell navmesh cook and streaming, "
         "cross-cell stitching, server residency, regional generation, dynamic invalidation", "navigation-pathfinding",
         profiles=["openworld", "sandbox"], contrib=["world-architect", "world-data-model", "destruction-fracture",
                                                     "voxel-worlds", "resource-streaming-architect"], tags=t)

    t = "K-GAMEPLAY-9"
    ed.cap_set("INP.ACT.glyphs", add_contrib=["ui-architect", "text-fonts", "localization-i18n"],
               name=ed._find_cap("INP.ACT.glyphs")[1][1].rstrip(".") + "; typed input-action arguments in UI.LOC.messageformat "
               "and UI.TXT.rich re-resolve on device change", tags=t)

    t = "K-GAMEPLAY-10"
    _cap(ed, "AUD.DSP.user-mix", "Player-facing mix options: category volumes, mono downmix, dialogue boost, per-output dynamic-"
         "range profiles, speaker-layout selection, as C-CFG settings with an accessibility validation case",
         "audio-dsp-mixing", contrib=["accessibility", "persistence-save", "platform-architect"], tags=t)

    t = "K-GAMEPLAY-11"
    _cap(ed, "ANM.RT.2d-speech", "Dialogue-driven 2D portrait and sprite mouth animation per locale (C-DIALOGUE timing)",
         "animation-runtime", profiles=["minimal", "min2d"],
         contrib=["facial-animation", "narrative-dialogue", "audio-content-runtime"], tags=t)

    t = "K-GAMEPLAY-12"
    for sid in ("gameplay-camera", "ui-architect", "post-color-hdr", "vfx-particles", "gameplay-systems-toolkit"):
        ed.use(sid, "C-A11YRT?", tags=t)
    ed.cap_set("UI.A11Y.motion", add_contrib=["gameplay-camera", "ui-architect", "post-color-hdr", "vfx-particles",
                                              "gameplay-systems-toolkit"],
               name=ed._find_cap("UI.A11Y.motion")[1][1].rstrip(".") + "; sole setting owner, with a runtime flash-limiter hook",
               tags=t)
    _rename(ed, "GAM.CAM.comfort", " (consumes UI.A11Y.motion settings)", tags=t)

    # ================================================================ TEST
    t = "K-TEST-1"
    _cap(ed, "QA.SIM.determinism-matrix", "Determinism conformance matrix (toolchain × ISA × platform × cores × schedule) and "
         "golden hash corpus; determinism-replay keeps policy and hooks", "simulation-validation",
         contrib=["determinism-replay"], tags=t)
    for g in _ms(ed, "M0")["gates"]:
        if g["capability"] == "XC.DET.conformance":
            g["validator"] = "QA.SIM.golden-traces"

    t = "K-TEST-2"
    for mid, cap, val in (("M1", "QA.RENDER.golden", "QA.AGENT.gate-canaries"),
                          ("M1", "QA.SIM.stability-suite", "QA.AGENT.gate-canaries")):
        for g in _ms(ed, mid)["gates"]:
            if g["capability"] == cap:
                g["validator"] = val
    ed.note(t, "per-gate exercised_by/known_red fields are not added (partial)")

    t = "K-TEST-3"
    _gate(ed, "M1", "UI.A11Y.validation", "QA.FUNC.compat")
    _gate(ed, "M3", "RND.GEO.cpu-submission", "QA.RENDER.matrix")
    _gate(ed, "M6", "QA.ROBUST.distributed-faults", "QA.FUNC.load")

    t = "K-TEST-4"
    n = 0
    for c in ed.doc["contract"]["contracts"]:
        if c.get("oracle_reference") == [PLACEHOLDER] and c["id"] in REFS:
            c["oracle_reference"] = [REFS[c["id"]]]
            n += 1
    ed.note(t, f"{n} placeholder oracle_reference values replaced by named reference sources; check.py bans the placeholder")

    t = "K-TEST-5"
    ed.skill_add(tags=t, id="services-conformance", name="Services & Persistence Conformance", tier="expert",
                 parent="test-architect", profiles=["all"], kind="process", targets=[], workstream="quality",
                 purpose="Independent authoring of conformance suites for server, persistence, service-boundary and save "
                         "contracts, distinct from their owners and implementers.",
                 non_responsibilities=[["Contract implementation", "owning-skill"], ["Load tests", "functional-automation-soak"]],
                 expertise=["consistency and idempotency checking", "service sandboxes", "save migration corpora"],
                 consumes=["C-TEST"])
    _cap(ed, "QA.CONF.services", "Server, persistence and service-boundary conformance suites", "services-conformance",
         contrib=["test-architect"], tags=t)
    _cap(ed, "QA.CONF.saves", "Save migration and integrity conformance corpora", "services-conformance",
         contrib=["test-architect"], tags=t)
    _cap(ed, "QA.CONF.service-doubles", "Real-provider sandbox lanes for service and platform doubles", "services-conformance",
         contrib=["test-architect"], tags=t)
    for cid in ("C-SERVER", "C-SRVDATA", "C-SHARD", "C-SVC", "C-LIVE", "C-SAVE"):
        ed.contract_set(cid, oracle_author="services-conformance", tags=t)

    t = "K-TEST-7"
    for c in ed.doc["contract"]["contracts"]:
        if c.get("boundary") and isinstance(c.get("test_double"), dict):
            c["test_double"]["real_backend_lane"] = "sandbox or devkit lane on a fixed cadence; drift ticket on divergence"
    ed.cap_set("QA.STRAT.contract-fakes", name=ed._find_cap("QA.STRAT.contract-fakes")[1][1].rstrip(".") + "; periodic real-vs-"
               "double differential per boundary contract", tags=t)

    t = "K-TEST-8"
    _cap(ed, "QA.RENDER.temporal", "Temporal image validation: scripted camera paths, supersampled reference sequences, "
         "temporal metrics (ghosting, flicker, shimmer), motion-vector reprojection error", "render-validation",
         contrib=["reconstruction-upscaling"], tags=t)
    ed.contract_set("C-TEMPORAL", oracle_reference=[REFS["C-TEMPORAL"] + " (QA.RENDER.temporal)"], tags=t)
    _gate(ed, "M3", "QA.RENDER.temporal", "QA.AGENT.gate-canaries")

    t = "K-TEST-10"
    ed.note(t, "freeze_requires fields are not added; the oracle-author staffing rule and per-gate validators cover ordering "
               "(partial)")

    t = "K-TEST-11"
    ed.cap_set("QA.AGENT.holdout-hygiene", mat="M", tags=t)
    for e in ed.doc["radar"]["entries"]:
        if e["tech"].startswith("Validation of autonomous-agent development"):
            e["capabilities"] = sorted(set(e["capabilities"]) | {"QA.AGENT.holdout-hygiene"})

    t = "K-TEST-13"
    ed.cap_set("QA.FUNC.compat", name=ed._find_cap("QA.FUNC.compat")[1][1].rstrip(".") + " (single matrix definition generated "
               "from PLAT.PAL.device-db tiers, share and driver deny-list; render, functional and perf lanes consume it)",
               tags=t)

    # ================================================================ SEC
    t = "K-SEC-2"
    for i in ed.doc["untrusted"]["inputs"]:
        if i["id"] == "cloud-saves":
            i["trust"] = "hostile-local"
    ed.cap_set("GAM.SAVE.integrity", name=ed._find_cap("GAM.SAVE.integrity")[1][1].rstrip(".") + "; client-signed saves are "
               "tamper-evident only; online-relevant fields are server-authoritative (NET.SRV.persistence); server-held keys "
               "under XC.SEC.key-custody", tags=t)

    t = "K-SEC-3"
    _cap(ed, "RND.MEM.zero-init-robust-access", "Zero-initialization of fresh and aliased VRAM, robust bounds-checked buffer/"
         "image access for untrusted shaders, device-lost/TDR recovery", "gpu-memory-resources",
         contrib=["shader-system", "render-graph-scheduling", "security-engineering"], tags=t)

    t = "K-SEC-4"
    _input(ed, "remote-play-input", "platform-architect", ["input-system", "network-transport"], "hostile-remote",
           "rate/schema/session-token; per-session process/GPU-context isolation")

    t = "K-SEC-5"
    ed.cap_set("BLD.SYS.third-party", name="Third-party dependency management with an agent admission policy: mirror-only egress, "
               "hash-pinned lockfile, human gate for new dependencies and maintainer changes (ARCH.ORG.human-gates), "
               "vendored-diff review", add_contrib=["ci-cd-automation", "program-orchestration"], tags=t)

    t = "K-SEC-6"
    _cap(ed, "XC.SEC.gameplay-rng", "Security-relevant gameplay randomness: economy and ranking outcomes use a server CSPRNG with "
         "an audit record; deterministic RNG is forbidden for them", "anti-cheat-integrity",
         contrib=["security-runtime", "math-simd-numerics", "server-scaleout-persistence", "determinism-replay"], tags=t)

    t = "K-SEC-7"
    _input(ed, "player-profile-strings", "online-services-liveops", ["text-fonts", "ui-architect"], "hostile-remote",
           "length, NFC normalization, control/bidi-override allow-list, output-context escaping")
