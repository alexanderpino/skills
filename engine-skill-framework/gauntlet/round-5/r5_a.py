"""Round-5 revision, part A: rendering, systems, architecture and simulation findings
(K-RENDER-4..10; K-SYSTEMS-2,4..9; K-ARCH-10..15,17; K-SIM-2..5,7..9)."""
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "round-3"))
sys.path.insert(0, os.path.join(R, "round-4"))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap, _rename  # noqa: E402


def _radar_caps(ed, tech_prefix, add=None, **kw):
    for e in ed.doc["radar"]["entries"]:
        if e["tech"].startswith(tech_prefix):
            e["capabilities"] = sorted(set(e["capabilities"]) | set(add or []))
            e.update(kw)
            return
    raise KeyError(tech_prefix)


def apply(ed):
    # ================================================================ RENDER
    t = "K-RENDER-4"
    for cid in ("RND.LOD.instanced-clusters", "RND.LOD.foliage"):
        ed.cap_set(cid, mat="M", tags=t)
    _radar_caps(ed, "Cluster/virtualized geometry refinements", add=["RND.LOD.instanced-clusters", "RND.LOD.foliage"],
                fallback="Discrete LOD + HLOD/impostors + instanced draws")

    t = "K-RENDER-5"
    ed.skill_set("path-tracing", profiles=["std3d"], tags=t)
    ed.note(t, "path-tracing (reference tracer, real-time PT, offline render) leaves lite3d closures; RT infrastructure keeps "
               "lite3d for software RT; a check that dev-only capabilities never resolve into client targets is not added "
               "(partial)")

    t = "K-RENDER-6"
    _cap(ed, "RND.GI.baked-streaming", "Cell-streamed baked lighting: lightmaps, probe volumes, reflection captures and "
         "lighting-scenario/time-of-day blending, with a pool registered in RES.MGMT.arbitration and C-GI",
         "global-illumination", contrib=["world-architect", "resource-streaming-architect", "async-io-storage"], tags=t)

    t = "K-RENDER-7"
    ed.cap_set("RND.SHADER.autodiff", mat="X", profiles=["experimental"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "RND.SHADER.autodiff" in e["capabilities"]:
            e["class"] = "X"
            e["tech"] = "Differentiable shader compilation (autodiff)"

    t = "K-RENDER-8"
    ed.cap_set("RND.SHADER.toolchain", name="Compilation toolchain (DXC, SPIR-V, Metal shader converter; Slang via "
               "RND.SHADER.slang)", tags=t)
    for cid in ("RND.RHI.webgpu-validation", "RND.RHI.webgpu-quirks"):
        ed.cap_set(cid, mat="M", tags=t)
    ed.cap_set("RND.ARCH.multiview-nview", mat="X", profiles=["experimental"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "RND.ARCH.multiview-nview" in e["capabilities"]:
            e["class"] = "X"
        if "RND.RHI.webgpu" in e["capabilities"]:
            e["capabilities"] = sorted(set(e["capabilities"]) | {"RND.RHI.webgpu-validation", "RND.RHI.webgpu-quirks"})

    t = "K-RENDER-9"
    _radar_caps(ed, "Sampler-feedback streaming", fallback="Shader-written feedback buffer (VT feedback pass), then mip "
                "streaming")
    ed.cap_set("RND.TEX.feedback", name=ed._find_cap("RND.TEX.feedback")[1][1].rstrip(".") + "; backend abstraction: hardware "
               "sampler feedback where present, shader-written feedback elsewhere", tags=t)

    t = "K-RENDER-10"
    ed.cap_set("RND.LOD.hlod", name="HLOD proxy/impostor formats, builders and runtime selection", tags=t)
    ed.cap_set("WLD.PART.hlod", name="HLOD strategy, partitioning and invalidation (formats and builders belong to "
               "RND.LOD.hlod; orchestration to CNT.COOK.world-build)", tags=t)
    _rename(ed, "RND.GI.bake-pipeline", "; GI-owned bake processors hosted by CNT.COOK.world-build", tags=t)

    # ================================================================ SYSTEMS
    t = "K-SYSTEMS-2"
    _cap(ed, "PLAT.PAL.storage-class", "Storage class discovery (rotational/SATA-SSD/NVMe/removable/network) with a throughput "
         "and latency probe", "platform-architect", tags=t)
    _cap(ed, "RES.IO.media-policy", "Media-aware IO policy: seek-aware ordering, low queue depth, duplication or clustering "
         "per storage class; storage-class axis in tier records", "async-io-storage",
         contrib=["package-formats-vfs", "platform-architect"], tags=t)

    t = "K-SYSTEMS-4"
    c = ed.contract("C-LIFETIME")
    ed.contract_set("C-LIFETIME", summary=c["summary"] + " Mechanism only (retirement service, completion tokens, epochs); "
                    "ownership policy belongs to CORE.LIFE.ownership-model (core-runtime-architect).", tags=t)
    ed.cap_set("CORE.OBJ.references", name="Reference kinds & explicit lifetime in the object model (policy from "
               "CORE.LIFE.ownership-model; handles generational, script references weak)", tags=t)

    t = "K-SYSTEMS-5"
    _append(ed, "C-BASE", "signal-safe subset: pre-opened fd/pipe write, raw file write, alternate-stack reservation, "
            "exception/signal handler registration hook, monitor-process spawn.", t)
    ed.cap_set("PLAT.PAL.process", name=ed._find_cap("PLAT.PAL.process")[1][1].rstrip(".") + " (crash-time use goes through "
               "the C-BASE signal-safe subset)", tags=t)

    t = "K-SYSTEMS-6"
    ed.contract_set("C-LIFETIME", requires=sorted(set(ed.contract("C-LIFETIME")["requires"]) | {"C-MEM"}), tags=t)
    ed.contract_set("C-RES", requires=sorted(set(ed.contract("C-RES")["requires"]) | {"C-FRAME"}), tags=t)
    ed.note(t, "C-CFG→C-TYPES/C-MEM is not added (would close a cycle with pre-C-MEM config use) (partial)")

    t = "K-SYSTEMS-7"
    ed.cap_set("CORE.FRAME.pipelining", name="Frame pipelining & frames in flight (the ADR fixes pipeline depth and lane roles; "
               "CORE.JOBS.thread-model registers the resulting threads)", tags=t)
    _append(ed, "C-TASK", "threads and lanes are obtained only through the thread-model inventory (lint-enforced).", t)

    t = "K-SYSTEMS-8"
    _cap(ed, "PRF.METH.tier-emulation", "Lower-tier emulation on stronger machines: core-count and P/E affinity masks, hard "
         "memory ceiling at the tier budget, IO throttle, GPU clock caps; run per configuration in a CI lane",
         "performance-architect", contrib=["test-runtime-harness", "ci-cd-automation", "memory-allocators",
                                           "async-io-storage"], tags=t)

    t = "K-SYSTEMS-9"
    _cap(ed, "CORE.MEM.exec-pages", "Executable-memory policy: W^X, JIT entitlement, code-page allocation, icache flush, "
         "per-platform executable-mapping queries from PAL", "memory-allocators",
         contrib=["scripting-runtime", "hot-reload-iteration", "security-engineering"], tags=t)

    # ================================================================ ARCH
    t = "K-ARCH-10 K-ARCH-11"
    for sid, name, expertise in (("tools-pipeline-conformance", "Tools & Pipeline Conformance",
                                  ["import/cook/package round-trip corpora", "command apply/invert property tests"]),):
        ed.skill_add(tags=t, id=sid, name=name, tier="expert", parent="test-architect", profiles=["all"], kind="process",
                     targets=[], workstream="quality", purpose="Independent authoring of conformance suites for tool, "
                     "cook, build and editor-command contracts, distinct from their owners and implementers.",
                     non_responsibilities=[["Contract implementation", "owning-skill"]], expertise=expertise,
                     consumes=["C-TEST"])
    _cap(ed, "QA.CONF.tools-pipeline", "Tools and pipeline conformance suites (cook, build, package, editor commands, graphs)",
         "tools-pipeline-conformance", contrib=["test-architect"], tags=t)
    _cap(ed, "QA.CONF.import-roundtrip", "Import/cook round-trip corpora", "tools-pipeline-conformance",
         contrib=["test-architect"], tags=t)
    _cap(ed, "QA.CONF.command-properties", "Command apply/invert/merge property tests", "tools-pipeline-conformance",
         contrib=["test-architect"], tags=t)
    for cid in ("C-PAL", "C-MOD", "C-SYNC", "C-LIFETIME", "C-ID", "C-REFL", "C-SER", "C-FRAME", "C-FLOW", "C-PRESENT", "C-IPC"):
        ed.contract_set(cid, oracle_author="foundation-conformance", tags=t)
    for cid in ("C-COOK", "C-BUILD", "C-PKG", "C-EDCMD", "C-GRAPH", "C-CMD", "C-IMPORT", "C-VCS", "C-EDHOST", "C-EDVIEW"):
        ed.contract_set(cid, oracle_author="tools-pipeline-conformance", tags=t)
    ed.note(t, "QA.ROBUST.concurrency (stress/perturbation) stays with robustness-fuzzing; litmus and model checking with "
               "foundation-conformance")

    t = "K-ARCH-12"
    ed.contract_add("C-GRAPHRT", 2, "scripting-runtime", "Runtime graph schema",
                    "Node/pin schema, validation and the restricted node-set profile for graphs compiled at runtime "
                    "(UGC graphs, visual script); consumed tool-side by C-GRAPH.", requires=["C-SER"], conformance=True,
                    oracle_author="functional-automation-soak", oracle_reference=[
                        "malformed and adversarial graph corpora; restricted-profile conformance cases"], tags=t)
    ed.use("modding-ugc", "C-GRAPHRT", tags=t)
    ed.use("graph-editor-framework", "C-GRAPHRT", tool=True, tags=t)
    for cid in ("C-GRAPH", "C-EDIT"):
        ed.contract_set(cid, requires=sorted(set(ed.contract(cid)["requires"]) | {"C-GRAPHRT"}), tags=t)

    t = "K-ARCH-13"
    for sid in ("physics-architect", "terrain", "audio-content-runtime", "vfx-particles", "material-system"):
        ed.use(sid, "C-GAMEDATA?", tags=t)

    t = "K-ARCH-14"
    ed.note(t, "an 'xl' tier is not added: tiers partition workstreams (the co-hosting unit); per-skill hosting is covered by "
               "write-sets and the ledger (partial)")

    t = "K-ARCH-15"
    ed.skill_set("accessibility", purpose="Maps XAG/GAG and legal requirements to engine features; defines the requirement "
                 "mapping, services (C-A11YRT), settings and validation; presentation is owned by ui-architect (subtitles, text "
                 "scaling), post-color-hdr (colorblind and contrast passes) and input-system.", tags=t)

    t = "K-ARCH-17"
    ed.note(t, "contract-text/requires reconciliation is done for the named cases in K-SYSTEMS-6; a general 'informs' check is "
               "not added (partial)")

    # ================================================================ SIM
    t = "K-SIM-2"
    _cap(ed, "PHY.ARCH.migration", "Live body, joint-graph and controller hand-off across authority boundaries; ghost-body "
         "policy; declared unsupported cases", "physics-architect",
         contrib=["server-scaleout-persistence", "replication"], tags=t)
    for sid in ("physics-architect", "vehicle-physics", "character-physics"):
        ed.use(sid, "C-SHARD?", tags=t)

    t = "K-SIM-3"
    _cap(ed, "GAM.MOVE.ragdoll-transition", "Capsule to ragdoll to get-up transition: state machine, capsule/body-set handover, "
         "authority class (cosmetic by default), ragdoll body budget", "character-movement",
         contrib=["ik-procedural-animation", "character-physics"], tags=t)

    t = "K-SIM-4"
    _add(ed, "collision-detection", "implements", "C-PHYS")
    _append(ed, "C-PHYS", "implementers split: rigid-body-dynamics implements bodies, stepping and snapshot; "
            "collision-detection implements shapes, queries and collider history.", t)

    t = "K-SIM-5"
    ed.cap_set("NET.PRED.physics", name=ed._find_cap("NET.PRED.physics")[1][1].rstrip(".") + "; owns all client-side "
               "presentation of replicated bodies (extrapolation, smoothing, snap thresholds)", tags=t)
    ed.cap_set("NET.REP.physics-bodies", name="Physics-body replication: wire content, priority and ownership hand-off "
               "(client-side presentation belongs to NET.PRED.physics)", tags=t)

    t = "K-SIM-7"
    ed.use("cloth-deformables", "C-SNAPSHOT?", "C-STATECLASS", tags=t)
    _append(ed, "C-STATECLASS", "soft bodies: cloth and hair are derived/cosmetic and excluded from hashes; ropes and softbody "
            "are restorable when gameplay-visible.", t)

    t = "K-SIM-8"
    refs = {"C-VEHICLE": "reference manoeuvres (ISO 3888 double lane change, skidpad) and Pacejka tire-model reference curves",
            "C-CROWD": "ORCA/RVO reference scenarios and flow-rate benchmarks (fundamental diagram data)",
            "C-MOVE": "character-controller edge-case corpora (step, slope, ledge, moving platform) from published test scenes",
            "C-CHARCTRL": "collide-and-slide analytic cases and a second-backend differential run",
            "C-AI": "behavior-tree/utility reference traces and EQS analytic cases"}
    for cid, r in refs.items():
        ed.contract_set(cid, oracle_reference=[r], tags=t)
    ed.contract_set("C-PHYS", oracle_reference=["analytic physics scenes (pendulum, stacking, restitution) and a differential "
                                              "run against a backend other than the shipped one"], tags=t)

    t = "K-SIM-9"
    ed.cap_set("PHY.FLUID.grid", name=ed._find_cap("PHY.FLUID.grid")[1][1].rstrip(".") + "; decision table: gameplay-"
               "authoritative liquid or fire is cellular (GAM.SIM.cellular/GAM.SIM.fields); PHY.FLUID.* is presentation-grade "
               "with one-way coupling into C-PHYS bodies; the C-ENV water volume is authoritative for buoyancy", tags=t)
