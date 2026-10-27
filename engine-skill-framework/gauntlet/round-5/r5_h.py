"""Round-5 revision, part H: adjudication overturns (K-ARCH-14, K-FUTURE-1, K-PLATFORM-3, K-PLATFORM-5, K-PROD-5, K-TEST-2,
K-TEST-9, K-TEST-10, K-TOOLS-11)."""
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "round-3"))
sys.path.insert(0, os.path.join(R, "round-4"))
from r3_d import _radar  # noqa: E402
from r3_f import _cap  # noqa: E402
from r4_c import _ms  # noqa: E402


def _gname(ed, cid):
    return ed._find_cap(cid)[1][1]


def apply(ed):
    t = "K-ARCH-14"
    n = _gname(ed, "ARCH.ORG.independence").replace("; co-hosting capped by capability count", "")
    ed.cap_set("ARCH.ORG.independence", name=n.rstrip(".") + "; the co-hosting unit is the workstream (data/organizations.json "
               "tiers), and per-agent load is bounded by tier choice and ARCH.ORG.human-capacity, not by a capability-count "
               "cap", tags=t)

    t = "K-FUTURE-1"
    six = ("ANM.SYN.learned", "ANM.DEF.ml", "GAM.AI.learned", "ML.RT.os-models", "XC.EXT.generated-assets",
           "ED.COLLAB.concurrent-world")
    for cid in six:
        ed.cap_set(cid, mat="X", profiles=["experimental"], tags=t)
    rd = ed.doc["radar"]
    for e in rd["entries"]:
        if e["tech"] in ("ML deformers", "Learned motion & neural controllers", "Learned & LLM-driven agents",
                         "Conflict-free concurrent world editing", "Player-prompted runtime asset generation"):
            e["class"] = "X"
        if e["tech"].startswith("OS model APIs"):
            e["capabilities"] = [c for c in e["capabilities"] if c != "ML.RT.os-models"]
    _radar(ed, "OS-provided foundation-model APIs as a backend", "X", "ml-inference-runtime", ["ML.RT.os-models"],
           "Windows ML GA, Apple Foundation Models, Android AICore announced (2025); no shipped title with a postmortem",
           "Two shipped titles using an OS model API, with postmortems", "Engine-packaged models")
    rd["_doc"] += " Program-level entries (ARCH.ORG.*) are judged by their human fallback."

    t = "K-PLATFORM-3"
    ed.cap_set("BLD.SYS.platform-sdks", name="Platform SDK version management & store-mandated minimums for public platforms "
               "(non-public platform pins and matrices are per-holder data under the NDA-extension mechanism of platform-architect)", tags=t)
    ed.cap_set("PLAT.PAL.confidential-extensions", name=_gname(ed, "PLAT.PAL.confidential-extensions").rstrip(".") +
               "; SDK version pins, cert-mandated minimums and compiler matrices of holder platforms join the per-holder "
               "partitions, with only a public envelope in BLD.SYS.platform-sdks and BLD.SYS.toolchains", tags=t)
    ed.cap_set("QA.CERT.prechecks", name="Automated certification pre-checks (public and non-holder checks; holder "
               "pre-submission checkers belong to PLAT.CON.submission)", tags=t)

    t = "K-PLATFORM-5"
    s = ed.skill("platform-server-host")
    ed.skill_set("platform-server-host", purpose=s["purpose"].replace("no display or GPU,", "no display (headless GPU only "
                 "through PLAT.SRV.gpu-host: offscreen surfaces, container GPU passthrough, hardware encode),"), tags=t)

    t = "K-PROD-5"
    _cap(ed, "QA.FUNC.release-rehearsal", "Release rehearsal drills on the online reference game: patch, DLC, staged rollout "
         "with halt, rollback and roll-forward, live-ops runbook and incident drills, key-rotation and revocation drill, "
         "vulnerability-disclosure SLA drill; records executed evidence per gate", "functional-automation-soak",
         contrib=["packaging-release-patching", "online-services-liveops", "security-engineering", "reference-games"], tags=t)
    for g in _ms(ed, "M4")["gates"]:
        if g["capability"] in ("BLD.REL.rollback", "BLD.REL.staged-rollout", "PLAT.LIVE.operations"):
            g["validator"] = "QA.FUNC.release-rehearsal"
    m4 = _ms(ed, "M4")
    m4["exit"] = m4["exit"].replace("staged rollout + rollback executed on the online reference game",
                                    "staged rollout + rollback executed on the online reference game "
                                    "(QA.FUNC.release-rehearsal validates rollout, rollback and live-ops)")

    t = "K-TEST-2"
    for mid, cap, val in (("M5", "RES.MGMT.validation", "QA.SIM.streaming"), ("M4", "NET.SRV.transactions",
                                                                              "QA.ROBUST.distributed-faults"),
                          ("M6", "NET.SRV.cross-server", "QA.ROBUST.distributed-faults"),
                          ("M7", "QA.STRAT.release-criteria", "QA.FUNC.release-rehearsal")):
        for g in _ms(ed, mid)["gates"]:
            if g["capability"] == cap:
                g["validator"] = val

    t = "K-TEST-9"
    ed.cap_set("NET.ARCH.validation", name="Netcode validation hooks: reference scenes incl. host-drop and threshold proposals "
               "only; scenario suites and acceptance thresholds belong to the contracts' oracle_author "
               "(simulation-validation)", tags=t)
    ed.cap_set("UI.A11Y.validation", name="Accessibility validation hooks (reference scenes and threshold proposals only; suite "
               "authorship belongs to the contract's oracle_author, ui-text-conformance)", tags=t)
    ed.cap_set("CNT.COOK.determinism-check", name="Cook determinism hooks (reference inputs and threshold proposals only; suite "
               "authorship belongs to the contract's oracle_author, tools-pipeline-conformance)", tags=t)

    t = "K-TEST-10"
    for row in ed.doc["cross"]["independence"]:
        if row[0] == "test-architect" and row[1] == "owning-skill":
            row[2] = ("test policy, definition-of-done and canary owner vs implementer (per-contract oracle_author independence "
                      "is checked per contract and per tier by check.py)")

    t = "K-TOOLS-11"
    ed.cap_set("ED.WORLD.blockout", profiles=["lite3d", "std3d"], tags=t)
    ed.cap_set("ED.WORLD.mesh-paint", profiles=["lite3d", "std3d"], tags=t)
    ed.cap_set("ED.WORLD.color-management", profiles=["std3d"], tags=t)
