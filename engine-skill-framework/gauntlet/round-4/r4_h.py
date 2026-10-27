"""Round-4 revision, part H: adjudication overturns (K-SEC-4, K-TEST-2, K-NET-1, K-PERF-7, K-PLATFORM-6, K-ARCH-12,
K-TEST-4, K-RENDER-6)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round-3"))
from r4_c import _gate, _ms  # noqa: E402
from r3_f import _rename  # noqa: E402


def apply(ed):
    t = "K-SEC-4"
    _gate(ed, "M2", "XC.SEC.dev-trust", "QA.FUNC.editor")
    for cap, val in (("XC.SEC.server-validation", "QA.FUNC.network"), ("XC.SEC.info-hiding", "XC.SEC.testing"),
                     ("XC.SEC.incident", "QA.CERT.prechecks"), ("NET.SRV.admin", "XC.SEC.testing"),
                     ("NET.SRV.transactions", "QA.FUNC.load"), ("PLAT.COMM.receipts", "XC.SEC.testing")):
        _gate(ed, "M4", cap, val)
    m4 = _ms(ed, "M4")
    m4["exit"] = m4["exit"].replace("server-authority review and external pen test (human gate)",
                                    "server-authority review and external pen test (human gate; gates XC.SEC.server-validation, "
                                    "XC.SEC.info-hiding, XC.SEC.incident, NET.SRV.admin, NET.SRV.transactions, PLAT.COMM.receipts; "
                                    "XC.SEC.testing validates)")
    ed.note(t, "security gates added at M2 (dev-trust) and M4 (server-validation, info-hiding, incident, admin, transactions, "
               "receipts)")

    t = "K-TEST-2"
    for mid, cap, val in (("M2", "QA.FUNC.soak", "PRF.BENCH.stats"), ("M7", "QA.FUNC.compat-corpus", "QA.REF.upkeep"),
                          ("M0", "QA.AGENT.holdout", "XC.SEC.agent-redteam")):
        for g in _ms(ed, mid)["gates"]:
            if g["capability"] == cap:
                g["validator"] = val
    ed.note(t, "gate cycles broken (soak, compat-corpus) and holdout re-paired to a red-team read attempt; check.py now fails "
               "gate cycles of length 2 and 3")

    t = "K-NET-1"
    for m in ed.doc["milestone"]["milestones"]:
        if "C-REP" in m["contracts_frozen"]:
            m["contracts_frozen"].remove("C-REP")
    _ms(ed, "M4")["contracts_frozen"] = sorted(_ms(ed, "M4")["contracts_frozen"] + ["C-REP"])
    for m in ed.doc["milestone"]["milestones"]:
        if m["id"] != "M4" and "C-REP" in m["contracts_draft"] and m["id"] != "M1":
            m["contracts_draft"].remove("C-REP")
    ed.note(t, "C-REP frozen at M4 (first configuration with replication); C-PREDICT, C-NETSESSION, C-HOSTAUTH stay at M2")

    t = "K-PERF-7"
    m4["exit"] = m4["exit"].replace("bandwidth per player and server density within budget",
                                    "bandwidth per player within budget and latency gated; server density is gated at M6 "
                                    "(PRF.NET.server-density)")
    ed.note(t, "M4 exit reworded; no duplicate gate")

    t = "K-PLATFORM-6"
    ed.cap_set("ARCH.REQ.platform-matrix", name="Platform matrix (OS × ISA × API; store axis from PLAT.SVC.pc-storefronts, "
               "platform-console entries and BLD.REL.store-variants) generated from skills.json platform_variants and "
               "implementer variants", tags=t)

    t = "K-ARCH-12"
    _ms(ed, "M1")["contracts_frozen"] = sorted(set(_ms(ed, "M1")["contracts_frozen"]) | {"C-A11Y"})
    for m in ed.doc["milestone"]["milestones"]:
        if m["id"] != "M1" and "C-A11Y" in m["contracts_frozen"]:
            m["contracts_frozen"].remove("C-A11Y")
    ed.note(t, "C-A11Y frozen at M1")

    t = "K-TEST-4"
    ed.cap_set("CORE.CONC.correctness", name="Thread-safety annotations and model-checking hooks (litmus/linearizability "
               "reference scenes and threshold proposals only; suite authorship belongs to the contract's oracle_author)",
               tags=t)

    t = "K-RENDER-6"
    ed.cap_set("RND.ARCH.multiview", name="Multi-view rendering: split-screen, PiP, captures, stereo/multiview; isolated "
               "preview scenes with their own lighting and budget for 3D UI and render-to-texture cameras; UI-less, HDR and "
               "tiled capture honoring platform capture restrictions (PLAT.SVC.capture)",
               add_contrib=["ui-architect", "gameplay-camera"], tags=t)
    _ms(ed, "M7")  # (no-op: ensures ladder present)
