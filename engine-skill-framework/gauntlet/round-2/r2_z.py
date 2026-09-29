"""Round-2 revision, part Z: the milestone ladder, rebuilt so that check.py can prove it
(K-PROD-1, K-PROD-7, K-NET-1, K-NET-15, K-RENDER-13, K-SYSTEMS-8, K-TOOLS-4, K-TEST-13, K-SEC-6, K-FUTURE-10,
K-GAMEPLAY-14/15, K-PERF-10).

Each milestone claims configurations (optionally restricted to platforms: 'name@pc'); every build skill is placed at
the first milestone whose claimed configurations contain it (or earlier, when pulled in by closure). Every code
contract is drafted when its owner arrives and frozen once the owner and at least one consumer exist, never before the
contracts it requires. Every configuration is claimed in full by exactly one milestone."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                "scripts"))

LADDER = [
    ("M0", "Walking skeleton", [],
     "Boots on one PC platform, runs the task graph, opens a window, presents through the RHI, reads input, draws a "
     "sprite and text, loads one cooked and signed asset from a package, passes CI with sanitizer, fuzz (package/"
     "serialization parsers) and determinism smoke lanes. Perf: trace capture and the C-BENCH runner on the skeleton; "
     "C-BUDGET v0 for indie-2d tiers; CI perf lane (frame time, startup, memory).",
     ["QA.HOST.runner", "XC.DET.conformance", "QA.ROBUST.fuzzing", "OBS.LOG.bench-runtime"]),
    ("M1", "Indie 2D slice on PC", ["indie-2d-client@pc", "minimal-client@pc"],
     "The indie-2d and minimal reference games are playable on PC with save, localization, accessibility baseline "
     "and hot reload. Network design authorities (network-architect, transport, replication, prediction, sessions) "
     "draft C-NET/C-REP/C-PREDICT/C-NETSESSION and review every freeze; a two-instance loopback session (lockstep or "
     "rollback) runs under QA.SIM.netsim. Security: threat model for the configuration, fuzz harnesses for every "
     "registered input reaching it, hardened shipping build, dev-surface audit. Perf: within budget on min-spec PC; "
     "hitch gate active.",
     ["QA.REF.ladder", "QA.SIM.netsim", "XC.SEC.threats", "XC.SEC.hardening", "BLD.SYS.dev-surface-exclusion",
      "PRF.LOAD.hitch-gate"]),
    ("M2", "Indie 2D ships everywhere, with tools", ["indie-2d-client", "minimal-client", "indie-2d-tools",
                                                     "minimal-tools", "mobile-async-client",
                                                     "fighting-2d-rollback-client", "sandbox-2d-client"],
     "indie-2d ships on PC, console, mobile and web with a TRC/store-review dry run; the editor and tools configuration "
     "closes with source control; rollback (8 frames under 150 ms / 5% loss) and async play proven. Local "
     "multiplayer: 2-player split-screen with independent UI focus, listeners and input. Perf: mobile tier within "
     "budget.",
     ["QA.CERT.prechecks", "ED.COLLAB.vcs", "NET.PRED.rollback", "GAM.FW.local-players"]),
    ("M3", "Standard 3D", ["standard-3d-client", "standard-3d-tools", "lite-3d-mobile-client", "lite-3d-mobile-tools",
                           "lite-3d-portable-console-client", "racing-3d-client"],
     "The standard-3d reference game runs on PC and console with GPU-driven and CPU-submission paths, reference "
     "path-tracer validation (itself validated), the lite-3d mobile and portable-console configurations; C-RHI "
     "reviewed against the tensor tier by ml-inference-runtime before freeze. Tools: iteration-latency targets met on "
     "standard-3d-tools and on-device iteration to console and mobile. Perf: std3d and lite3d budgets per tier; PSO "
     "first-encounter hitch gate; governor closed-loop test.",
     ["QA.RENDER.reference-validation", "RND.SHADER.pso-lists", "CORE.SCALE.governor", "XC.ITER.metrics"]),
    ("M4", "Online", ["online-3d-server", "online-3d-client", "online-3d-bot-client", "online-3d-tools",
                      "online-3d-console-client", "coop-3d-listen-client", "lite-3d-mobile-online-client",
                      "indie-2d-online-web-client", "indie-2d-online-moddable-client",
                      "indie-2d-online-moddable-server", "rts-2d-massim-client"],
     "Online reference games per netcode family: dedicated-server shooter with prediction and lag compensation, "
     "listen-server co-op, desync-free 2 h lockstep soak, web transports; bot load test; packet/handshake fuzzing, "
     "DoS test, server-authority review and external pen test (human gate); patch + DLC + staged rollout + rollback "
     "executed on the online reference game. Perf: bandwidth per player and server density within budget.",
     ["QA.FUNC.load", "NET.TRANS.dos", "BLD.REL.staged-rollout", "BLD.REL.rollback", "PRF.NET.bandwidth"]),
    ("M5", "Open world, simulation & XR", ["open-world-client", "rts-3d-massim-client", "sandbox-online-server",
                                          "xr-pc-client", "xr-standalone-client", "xr-console-client"],
     "Open-world reference slice streams at target speed within the arbitration budget (arbiter without oscillation "
     "or starvation, A14); massim and sandbox configurations closed and benchmarked; XR on PC, standalone and "
     "console. Perf: scale-content stress worlds within declared asymptotics.",
     ["RES.MGMT.arbitration", "RES.MGMT.validation", "PRF.BENCH.scale-content"]),
    ("M6", "AAA & ecosystem", ["aaa-open-world-online-client", "aaa-open-world-online-server",
                               "aaa-open-world-online-tools", "aaa-experimental-client"],
     "AAA reference slice; zoned hand-off and persistence crash-consistency with ≥1k bot clients; mods with sandbox-"
     "escape and GPU-DoS tests; experimental features only behind the experimental profile. Tools: team-large "
     "pipeline (multi-user sessions, distributed cook, world builds) on aaa-open-world-online-tools.",
     ["NET.SRV.cross-server", "XC.SEC.sandbox", "ED.COLLAB.multiuser"]),
    ("M7", "Engine 1.0 / first LTS", [],
     "Customer-corpus upgrade from the previous release, release notes, backport stream open, console certification "
     "pass of at least one reference game, live-ops and end-of-service rehearsal. Every milestone exit also runs the "
     "skill-library review (ARCH.ORG.skill-lifecycle).",
     ["ARCH.PROD.customer-corpus", "XC.EXT.lts", "BLD.REL.end-of-service", "PLAT.LIVE.operations"]),
]

SKELETON = ["platform-architect", "platform-desktop", "core-runtime-architect", "math-simd-numerics",
            "memory-allocators", "containers-core-types", "concurrency-primitives", "job-system-task-graph",
            "observability-telemetry", "crash-diagnostics", "runtime-scalability", "frame-orchestration",
            "entity-object-model", "reflection-metadata", "serialization-schema", "async-io-storage",
            "package-formats-vfs", "content-pipeline-architect", "resource-streaming-architect",
            "gpu-platform-architect", "rhi-core", "rhi-vulkan", "gpu-memory-resources", "render-graph-scheduling",
            "shader-system", "text-fonts", "render-2d-vector", "input-devices-haptics", "input-system",
            "asset-cook-processors", "test-runtime-harness", "determinism-replay", "security-runtime"]
M1_EXTRA = ["network-architect", "network-transport", "replication", "prediction-rollback", "net-session"]
P_FROZEN = {"M0": ["C-BUDGET", "C-TEST", "C-ORCH", "C-ARCH", "C-ADR"], "M1": ["C-TRUST", "C-API", "C-EVID", "C-PERF"],
            "M2": ["C-BENCH", "C-CERT", "C-RELEASE", "C-PROD"]}
P_DRAFT = {"M0": ["C-TRUST"]}


def apply(ed):
    from model import Model
    import json
    import tempfile
    # evaluate membership on the edited data through a throw-away model
    tmp = tempfile.mkdtemp()
    for k, f in (("cap", "capabilities.json"), ("skill", "skills.json"), ("contract", "contracts.json"),
                 ("critic", "critics.json"), ("cross", "crosscutting.json"), ("seed", "seed-map.json"),
                 ("radar", "radar.json"), ("legacy", "legacy-patterns.json"), ("milestone", "milestones.json"),
                 ("untrusted", "untrusted-inputs.json")):
        with open(os.path.join(tmp, f), "w", encoding="utf-8") as fh:
            json.dump(ed.doc[k], fh)
    import model as model_mod
    old = model_mod.DATA
    model_mod.DATA = tmp
    try:
        m = Model()
    finally:
        model_mod.DATA = old

    def members(claim):
        name, _, plats = claim.partition("@")
        cfg = m.configurations[name]
        saved = cfg.get("platforms", [])
        if plats:
            cfg["platforms"] = plats.split("+")
        try:
            return set(m.members(name))
        finally:
            cfg["platforms"] = saved

    def closure(start):
        out, todo = set(), list(start)
        while todo:
            s = todo.pop()
            if s in out:
                continue
            out.add(s)
            for cid, opt in m.deps(s, include_universal=True):
                if opt or cid not in m.contracts or m.layer(cid) == "P":
                    continue
                o = m.contract(cid)["owner"]
                if m.skill(o).get("kind") != "process":
                    todo.append(o)
        return out

    build = [s for s in m.skill_order if m.skill(s).get("kind") in ("runtime", "tool")]
    placed = {}
    for idx, (mid, _n, claims, _e, _g) in enumerate(LADDER):
        want = set()
        if mid == "M0":
            want = closure(SKELETON)
        else:
            for c in claims:
                want |= members(c)
            if mid == "M1":
                want |= closure(M1_EXTRA)
            want = closure(want)
        for s in sorted(want):
            if s in build and s not in placed:
                placed[s] = idx
    leftovers = [s for s in build if s not in placed]
    for s in leftovers:          # build skills in no claimed configuration (tools-only helpers etc.)
        placed[s] = len(LADDER) - 2

    # contract drafting / freezing
    ms_of = {s: i for s, i in placed.items()}
    consumers = {}
    for s in build:
        for cid, _opt in m.deps(s, include_universal=True, include_tool=True):
            consumers.setdefault(cid, []).append(s)
    freeze, draft = {}, {}
    code = [c for c in m.contracts if m.layer(c) != "P"]
    for c in code:
        o = m.contract(c)["owner"]
        om = ms_of.get(o, len(LADDER) - 2)
        cons = [ms_of[x] for x in consumers.get(c, []) if x in ms_of and x != o]
        first_cons = min(cons) if cons else om
        base = om if (m.layer(c) <= 1 and om == 0) else om + 1
        freeze[c] = min(max(base, first_cons), len(LADDER) - 1)
        draft[c] = om
    changed = True
    while changed:
        changed = False
        for c in code:
            for r in m.contract(c)["requires"]:
                if r in freeze and freeze[r] > freeze[c]:
                    freeze[c] = freeze[r]
                    changed = True

    out = []
    for idx, (mid, name, claims, exitt, gates) in enumerate(LADDER):
        entry = {"id": mid, "name": name, "configurations": claims,
                 "skills": sorted(s for s, i in placed.items() if i == idx),
                 "exit": exitt, "gates": gates,
                 "contracts_draft": sorted([c for c in code if draft[c] == idx and freeze[c] != idx]
                                           + P_DRAFT.get(mid, [])),
                 "contracts_frozen": sorted([c for c in code if freeze[c] == idx] + P_FROZEN.get(mid, []))}
        out.append(entry)
    ed.doc["milestone"]["milestones"] = out
    ed.doc["milestone"]["_doc"] = ("Milestone ladder (checked): each milestone claims configurations "
                                   "('name' or 'name@platform+platform'); every claimed configuration is closed over "
                                   "skills available by then; every configuration is claimed in full exactly once; "
                                   "every code contract is frozen exactly once, after its owner and a consumer "
                                   "arrive and never before what it requires; gates name capabilities.")
    tags = ("K-PROD-1 K-PROD-7 K-NET-1 K-NET-15 K-RENDER-13 K-SYSTEMS-8 K-TOOLS-4 K-TEST-13 K-SEC-6 K-FUTURE-10 "
            "K-GAMEPLAY-14 K-GAMEPLAY-15 K-PERF-10")
    ed.note(tags, "milestone ladder rebuilt: M0–M7, configurations claimed per milestone, skills placed by closure, "
                  f"contract freezes derived ({len(code)} code contracts); leftovers placed late: {leftovers}")
    ed.note(tags, "check.py: milestone configuration closure, full-claim coverage, contract freeze order, gates exist")
