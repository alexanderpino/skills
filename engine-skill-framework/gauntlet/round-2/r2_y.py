"""Round-2 revision, part Y: the anti-legacy catalogue (K-LEGACY-13, K-NET-10, K-SIM-15, K-TOOLS-12, K-SEC-10,
K-TEST-16, K-LEGACY-8/9/14). Every pattern gets stance_capabilities (the capabilities that carry its modern default),
which check.py verifies. Runs after the parts that create those capabilities."""

STANCE = {
    "L01": ["CORE.FRAME.access-model", "CORE.FRAME.phases"],
    "L02": ["GAM.FW.execution", "CORE.FRAME.amortized"],
    "L03": ["CORE.FRAME.pipelining", "RND.GPU.recording", "CORE.JOBS.thread-model"],
    "L04": ["PLAT.PAL.thread-affinity", "CORE.JOBS.pinned"],
    "L05": ["CORE.OBJ.hybrid"],
    "L06": ["GAM.FW.control"],
    "L07": ["WLD.MODEL.strategy", "WLD.SPACE.transforms"],
    "L08": ["CORE.LIFE.services", "CORE.LIFE.boot"],
    "L09": ["CORE.LIFE.config-snapshots"],
    "L10": ["ARCH.STRUCT.binding"],
    "L11": ["CORE.CONC.sync", "CORE.CONC.lockfree"],
    "L12": ["RND.ARCH.submission-strategy", "RND.GEO.cpu-submission"],
    "L13": ["RND.RHI.binding-tiers", "RND.GRAPH.barriers"],
    "L14": ["RND.ARCH.scene-sync", "RND.GEO.gpu-scene"],
    "L15": ["CORE.CONC.retirement", "RND.MEM.lifetime"],
    "L16": ["RES.MGMT.pipeline", "RES.IO.backends"],
    "L17": ["RES.IO.mmap"],
    "L18": ["WLD.PART.activation", "WLD.MODEL.unit-load"],
    "L19": ["CORE.OBJ.events"],
    "L20": ["CORE.REFL.static-default"],
    "L21": ["CORE.OBJ.references"],
    "L22": ["GAM.SCR.concurrency"],
    "L23": ["ED.ARCH.separation"],
    "L24": ["CNT.COOK.on-demand"],
    "L25": ["CORE.JOBS.scheduler", "CORE.JOBS.degenerate", "ARCH.GOV.fitness"],
    "L26": ["ARCH.STRUCT.contracts", "ARCH.STRUCT.replaceability"],
    "L27": ["ARCH.GOV.adr"],
}

NEW = [
    # id, pattern, detection, default stance, justification owner, stance caps, tags
    ("L28", "Global renderer sync & CPU/GPU flushes", "WaitForIdle / flush calls on frame paths",
     "Render-graph-derived barriers; external work imported with queue transfers", "render-graph-scheduling",
     ["RND.GRAPH.barriers", "RND.GRAPH.external-work"], "K-LEGACY-14"),
    ("L29", "Runtime shader/PSO compilation on first use", "PSO created on first draw; hitch on new material",
     "PSO coverage from play traces, precompiled/pipeline libraries, async creation with fallbacks",
     "shader-system", ["RND.SHADER.pso-lists", "RND.SHADER.cache"], "K-LEGACY-13"),
    ("L30", "Frame-coupled variable-timestep simulation", "simulation stepped by render delta",
     "Fixed/declared step with interpolation per C-FRAME", "frame-orchestration", ["CORE.FRAME.fixed-step"],
     "K-LEGACY-13 K-SIM-15"),
    ("L31", "Hard-reference transitive load graphs", "loading one asset pulls large dependency closures",
     "Soft references, dependency-aware loading with budgets", "resource-streaming-architect",
     ["RES.MGMT.dependencies"], "K-LEGACY-13"),
    ("L32", "Process-global current world", "static world accessor", "World handles; multiple isolated worlds",
     "entity-object-model", ["CORE.OBJ.world-instances"], "K-LEGACY-8 K-LEGACY-13"),
    ("L33", "Per-connection property polling replication", "shadow-state comparison per object per connection",
     "Push/dirty tracking, serialize once, O(changes)", "replication",
     ["NET.REP.change-tracking", "NET.REP.state"], "K-LEGACY-9 K-LEGACY-13 K-NET-10"),
    ("L34", "Global shared RNG used from parallel tasks", "one generator object shared by jobs",
     "Counter-based / per-stream RNG for parallel determinism", "math-simd-numerics", ["CORE.MATH.random"],
     "K-LEGACY-13"),
    ("L35", "Stringly-typed or polling UI binding", "property paths resolved and evaluated every frame",
     "Change-notified view models with resolved bindings", "ui-architect",
     ["UI.FW.architecture", "UI.FW.logic"], "K-LEGACY-13"),
    ("L36", "Per-body sync callbacks & mid-step world mutation", "O(bodies) transform write-back; queries mid-step",
     "Active-set/change-set output, batched queries, deferred commands", "physics-architect",
     ["PHY.ARCH.events", "PHY.ARCH.async"], "K-SIM-15"),
    ("L37", "Modal, blocking editor operations", "synchronous import/save/compile/bake on the editor UI thread",
     "Asynchronous, cancellable editor jobs with progress", "editor-architect", ["ED.ARCH.process"], "K-TOOLS-12"),
    ("L38", "Snapshot-based undo", "whole-object serialization per transaction",
     "Serializable, diff-based commands", "editor-architect", ["ED.ARCH.transactions"], "K-TOOLS-12"),
    ("L39", "Monolithic binary scene/asset files", "one binary level file edited by exclusive lock",
     "One-file-per-object layout with semantic merge", "world-data-model", ["WLD.MODEL.file-per-object"],
     "K-TOOLS-12"),
    ("L40", "Editor-only data fields in runtime types", "editor fields compiled into runtime structs",
     "Editor/runtime data separation", "editor-architect", ["ED.ARCH.separation"], "K-TOOLS-12"),
    ("L41", "Full re-cook or re-bake after local edits", "any edit triggers a full rebuild",
     "Incremental cooking with region invalidation, proven equal to clean cook", "content-pipeline-architect",
     ["CNT.COOK.incremental-equivalence"], "K-TOOLS-12"),
    ("L42", "TCP or all-reliable channels for real-time state", "state over reliable ordered stream",
     "UDP-class channels with per-message reliability classes", "network-transport", ["NET.TRANS.reliability"],
     "K-NET-10"),
    ("L43", "Client-authoritative gameplay, hits or economy", "server trusts client results",
     "Server authority with bounded-rewind validation", "network-architect",
     ["NET.ARCH.authority", "XC.SEC.server-validation"], "K-NET-10 K-SEC-10"),
    ("L44", "RPC-as-state-sync", "state changes sent as RPCs", "State replication plus events", "replication",
     ["NET.REP.state"], "K-NET-10"),
    ("L45", "Exact-build version lock", "clients rejected on any build difference", "Compatibility windows",
     "network-architect", ["NET.ARCH.versioning"], "K-NET-10"),
    ("L46", "Exposed peer IP addresses", "direct P2P addressing of players", "Relay-shielded addressing",
     "network-transport", ["NET.TRANS.nat"], "K-NET-10"),
    ("L47", "Lockstep without desync detection", "no state hashing in lockstep", "State-hash desync detection & tooling",
     "determinism-replay", ["XC.DET.desync"], "K-NET-10"),
    ("L48", "Content encryption as protection; long-lived secrets in clients", "pak keys or API secrets in binaries",
     "Server-held secrets, short-lived tokens, signing with custody", "security-engineering",
     ["XC.SEC.secrets", "XC.SEC.key-custody"], "K-SEC-10"),
    ("L49", "Client-side receipt validation", "client grants purchases", "Server-side verification & transactions",
     "platform-services", ["PLAT.COMM.receipts"], "K-SEC-10"),
    ("L50", "Unsandboxed native mods by default", "mods load native code without opt-in",
     "Sandboxed by default; native only by explicit opt-in; signed distribution", "modding-ugc",
     ["XC.EXT.ugc-integrity", "XC.SEC.sandbox"], "K-SEC-10"),
    ("L51", "Hand-written parsers of hostile input without hardening", "unfuzzed C/C++ parser of network/UGC data",
     "Registered untrusted input, fuzzed, hardened or memory-safe parser", "security-engineering",
     ["XC.SEC.memory-safety", "XC.SEC.trust"], "K-SEC-10"),
    ("L52", "Dev surfaces reachable in shipping", "console/ports/live coding present in shipping binaries",
     "Dev-surface manifest, exclusion fitness function & binary scan", "build-system-toolchains",
     ["BLD.SYS.dev-surface-exclusion"], "K-SEC-10"),
    ("L53", "Unkeyed hashing of attacker-controlled keys", "default hash on untrusted keys", "Keyed hashing",
     "containers-core-types", ["CORE.TYPES.hash-dos"], "K-SEC-10"),
    ("L54", "Collect-everything telemetry", "telemetry without data classes or minimization",
     "Data inventory, sensitivity classes, minimization & consent", "privacy-data-protection",
     ["XC.SEC.privacy", "XC.SEC.data-rights"], "K-SEC-10"),
    ("L55", "Kernel-mode anti-cheat as the default posture", "kernel driver required by default",
     "Server authority, attestation and user-mode anti-cheat first", "anti-cheat-integrity",
     ["XC.SEC.usermode-anticheat", "XC.SEC.attestation"], "K-SEC-10"),
    ("L56", "Late or implementer-owned validation", "tests written after features by their implementer",
     "Oracles by declared oracle authors, tests before features", "test-architect",
     ["QA.AGENT.oracle-independence", "QA.STRAT.dod"], "K-TEST-16"),
    ("L57", "Wall-clock time and exact-pixel goldens in tests", "sleeps, real clocks, bit-exact images across GPUs",
     "Injectable clocks, perceptual metrics with per-GPU tolerances", "test-architect",
     ["QA.STRAT.oracles", "CORE.FRAME.test-clock"], "K-TEST-16"),
]


def apply(ed):
    pats = ed.doc["legacy"]["patterns"]
    for p in pats:
        if p["id"] in STANCE:
            p["stance_capabilities"] = STANCE[p["id"]]
        if p["id"] == "L11":
            p["pattern"] = "Coarse locks"
            p["default_stance"] = "Declared access, channels, lock-free where justified (renderer sync: L28)"
        if p["id"] == "L18":
            p["pattern"] = "Blocking whole-level load before play"
            p["default_stance"] = "Async non-blocking loading; cell streaming with budgeted activation for 3D/openworld"
        if p["id"] == "L25":
            p["default_stance"] = "Parallel by construction, correct on one worker (inline mode)"
    ed.note("K-LEGACY-13", "stance_capabilities on every legacy pattern (checked); L11 split, L18/L25 restated")
    ed.note("K-LEGACY-11 K-LEGACY-12", "L18 and L25 stances restated for scale-down")
    for pid, pat, det, stance, owner, caps, tags in NEW:
        pats.append({"id": pid, "pattern": pat, "detection": det, "default_stance": stance,
                     "justification_owner": owner, "stance_capabilities": caps})
        ed.note(tags, f"legacy {pid}: {pat} → {owner}")
    ed.cap_set("CORE.MATH.random", name="Random numbers (counter-based / per-stream for parallel determinism) & noise",
               tags="K-LEGACY-13")
    ed.note("K-LEGACY-13", "check.py: every legacy pattern has existing stance capabilities owned, contributed or "
                           "led by its justification owner")
