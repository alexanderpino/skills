"""Round-3 revision, part B: governance, independence, oracle authors, organization tiers, agent-coordination
maturity (K-ARCH-1/2/3/4, K-PROD-1/5/6/11, K-SYSTEMS-6, K-TOOLS-5, K-PLATFORM-9, K-PERF-12, K-FUTURE-7/8, K-SIM-4)."""

ORACLES = {}
_R = "render-validation"
_S = "simulation-validation"
_F = "functional-automation-soak"
_Z = "robustness-fuzzing"
_P = "perf-benchmarking"
for c in ("C-RHI C-GPUMEM C-RG C-SHADER C-MATIF C-RSCENE C-TEMPORAL C-RT C-RTAS C-DRAW2D C-GPUTIER C-INSTANCES "
          "C-GEOLOD C-VT C-LIGHT C-GI C-VIDEO C-SCENETEX C-COLOR C-LIGHTENV C-TRANSLUCENT C-ATMOS C-XRVIEW").split():
    ORACLES[c] = _R
for c in ("C-PHYS C-ANIM C-AUDIO C-SPATIAL C-VIEW C-SIGNIF C-ENV C-NAV C-VEHICLE C-SEQ C-DET C-SNAPSHOT C-REPLAY "
          "C-CROWD C-WORLD C-PCG C-AI C-AIAGENT C-MOVE C-PREDICT C-REP C-NET C-NETLINK C-NETSESSION C-SHARD").split():
    ORACLES[c] = _S
for c in ("C-PAL C-BASE C-ERR C-MOD C-CFG C-MATH C-MEM C-TYPES C-SYNC C-TASK C-INSTR C-CRASH C-LIFETIME C-IPC "
          "C-FLOW C-PRESENT C-FRAME C-ID C-ECS C-REFL C-SER C-RELOAD C-ML C-MLGPU C-TESTHOST C-PLUGIN").split():
    ORACLES[c] = _Z
for c in ("C-IO C-VFS C-ASSET C-RES C-COOK C-BUILD C-PKG C-EDCMD C-GRAPH C-EDHOST C-EDVIEW C-VCS C-DEVUI "
          "C-AUTOMATION C-EDIT C-SERVER C-SRVDATA C-LIVE C-TARGETPLAT C-SVC C-INPUT C-DEVICE C-UI C-TEXT C-LOC "
          "C-A11YRT C-SCRIPT C-SAVE C-GAME C-GAMEDATA C-DIALOGUE C-ABILITY C-CMD").split():
    ORACLES[c] = _F
ORACLES.update({"C-SCALE": _P, "C-GOVERN": _P, "C-SIGN": "security-engineering", "C-INTEGRITY": "security-engineering"})

# name -> hosting agents per tier (workstreams partitioned; every workstream exactly once)
TIERS = {
    "small": {"build": ["foundation", "platform", "content", "world", "rendering", "simulation", "audio", "online",
                        "gameplay", "ui", "tools", "release"],
              "verify": ["quality", "performance", "assurance"], "govern": ["governance"]},
    "mid": {"core-platform": ["foundation", "platform"], "rendering": ["rendering"],
            "world-sim-audio": ["world", "simulation", "audio"], "game-content-tools": ["gameplay", "ui", "content", "tools"],
            "online-release": ["online", "release"], "quality": ["quality"], "perf-assurance": ["performance", "assurance"],
            "govern": ["governance"]},
    "large": {w: [w] for w in ("foundation", "platform", "content", "world", "rendering", "simulation", "audio",
                               "online", "gameplay", "ui", "tools", "release", "quality", "performance", "assurance",
                               "governance")},
}


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def apply(ed):
    t = "K-ARCH-1 K-ARCH-2 K-PROD-1 K-SYSTEMS-6 K-TOOLS-5 K-PLATFORM-9 K-PERF-12"
    ed.skill_set("security-runtime", workstream="foundation", tags=t)
    ed.skill_set("test-runtime-harness", workstream="foundation", tags=t)
    n = 0
    for c in ed.doc["contract"]["contracts"]:
        if c["layer"] == "P":
            continue
        c["oracle_author"] = ORACLES.get(c["id"], _F)
        n += 1
    ed.note(t, f"oracle_author reassigned for {n} code contracts to quality/performance validators by domain; "
               "security-runtime and test-runtime-harness moved to the foundation workstream (they own shipped code)")
    ed.note(t, "check.py: an oracle author is in a quality/performance/assurance workstream and shares none with the "
               "owner or any implementer; per-tier hosting (organizations.json) proves it per organization size")
    ed.cap_set("QA.AGENT.oracle-independence", name="Acceptance suites authored by each contract's declared "
               "oracle_author (a validator in another workstream than owner and implementers); implementers propose "
               "additions by change request only", tags=t)

    t = "K-ARCH-3 K-ARCH-4"
    ed.cap_set("ARCH.ORG.escalation", name="Escalation tiers & decision SLAs; delegated arbitration inside a lead's "
               "subtree; disputes between leads of one workstream, and disputes in which the arbitrating lead is a "
               "party, go to engine-architect", tags=t)

    t = "K-PROD-11 K-PROD-5 K-PROD-6 K-FUTURE-7 K-FUTURE-8"
    ed.doc["org"] = {"_doc": "Organization tiers (checked). Each tier partitions the workstreams into agents; every "
                             "workstream is hosted exactly once. check.py proves per tier that independence pairs and "
                             "oracle authors vs owners/implementers land on different agents. The minimum agent count "
                             "that keeps the independence pairs apart is 3 (build, verify, govern). Tier names are owned "
                             "by ARCH.ORG.staffing; ARCH.GOV.process-tiers consumes them.",
                     "tiers": {k: {"agents": v} for k, v in TIERS.items()}}
    ed.cap_set("ARCH.ORG.staffing", name="Agent staffing tiers (small 3 agents, mid 8, large 16; data/organizations.json) "
               "co-hosting skills by workstream; sole owner of tier names", tags=t)
    ed.cap_set("ARCH.GOV.process-tiers", name="Governance weight per organization tier (consumes tier names from "
               "ARCH.ORG.staffing)", tags=t)
    ed.cap("ARCH.ORG.agent-continuity", "Agent continuity: lock leases with heartbeats and fencing tokens, stale-lock "
           "reclamation, mandatory task hand-off record and re-brief when an agent crashes, runs out of context or is "
           "replaced", "program-orchestration", "M", profiles=["experimental"] if False else None, tags=t)
    ed.cap("ARCH.ORG.delegated-planning", "Delegated planning: program-orchestration issues per-lead work packages and "
           "cross-workstream integration tasks; leads decompose inside their subtree (work-package format in C-ORCH)",
           "program-orchestration", "M", contrib=[s["id"] for s in ed.doc["skill"]["skills"] if s["tier"] == "lead"],
           tags=t)
    ed.cap_set("ARCH.ORG.decomposition", name="Milestone → work-package decomposition by workstream (intra-subtree "
               "decomposition in ARCH.ORG.delegated-planning)", tags=t)
    ed.cap("ARCH.ORG.model-requalification", "Model/prompt lineage and requalification: implementer, oracle author and "
           "S3/S4 critics use different model families or versions (otherwise the human-audit rate rises); any change "
           "of agent model or prompt re-runs seeded-defect calibration and holdouts before the agent counts as a gate; "
           "the model is recorded in provenance", "architecture-governance", "M",
           contrib=["program-orchestration", "test-architect"], tags=t)
    _append(ed, "C-ORCH", "lock leases and hand-off records (ARCH.ORG.agent-continuity); work-package format for "
            "delegated planning; model lineage recorded per change.", t)
    for cid in ("ARCH.ORG.ownership-ledger", "ARCH.ORG.staffing", "ARCH.ORG.change-requests", "ARCH.ORG.write-sets",
                "ARCH.ORG.skill-lifecycle"):
        ed.cap_set(cid, mat="M", tags=t)
    for cid in ("ARCH.ORG.independence",):
        ed.cap_set(cid, mat="M", tags=t)
    fb = "Human coordinator role per workstream and mandatory human review sampling per tier (ARCH.ORG.human-gates)"
    ed.doc["radar"]["entries"] += [
        {"tech": "Coordination of ~150 autonomous agents (program)", "class": "M", "owner": "program-orchestration",
         "capabilities": ["ARCH.ORG.ownership-ledger", "ARCH.ORG.staffing", "ARCH.ORG.change-requests",
                          "ARCH.ORG.write-sets", "ARCH.ORG.skill-lifecycle", "ARCH.ORG.agent-continuity",
                          "ARCH.ORG.delegated-planning"],
         "evidence": "No published precedent at this agent count; multi-agent coding systems (2025)",
         "revisit": "Two milestones completed without lock deadlock or lost work", "fallback": fb},
        {"tech": "Independence & model lineage of agent verification", "class": "M", "owner": "architecture-governance",
         "capabilities": ["ARCH.ORG.independence", "ARCH.ORG.model-requalification"],
         "evidence": "LLM-as-judge self-preference and correlated errors (2023–2024)",
         "revisit": "Measured escape rate of seeded defects stable across model changes", "fallback": fb}]
    ed.note(t, "agent-coordination capabilities relabelled M with radar entries")

    t = "K-SIM-4"
    ed.contract_set("C-PHYS", needs_implementer=True, tags=t)
    for sid in ("physics-2d", "rigid-body-dynamics"):
        ed.skill(sid)["implements"].append("C-PHYS")
    _append(ed, "C-PHYS", "backends (in-house 2D, in-house 3D, or middleware behind the integration layer "
            "PHY.ARCH.middleware-layer) implement it; every configuration that requires it contains one.", t)
