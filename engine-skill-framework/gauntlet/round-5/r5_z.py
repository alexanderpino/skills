"""Round-5 finalisation: freeze new contracts, keep the M0 process-skill list and radar dates current."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round-4"))
import r4_z  # noqa: E402


def apply(ed):
    r4_z.apply(ed, tagged=False)
    procs = [s["id"] for s in ed.doc["skill"]["skills"] if s.get("kind") == "process"]
    ed.doc["milestone"]["milestones"][0]["process_skills"] = sorted(procs)
    for tags, text in (
            ("K-LEGACY-6", "contradiction_terms added for L14, L35, L36, L38 and L16"),
            ("K-LEGACY-9", "legacy catalogue L89 (independent per-domain streaming pools)"),
            ("K-NET-4", "configuration community-server-pc (online+ugc, server, pc+server-host) claimed at M4"),
            ("K-NET-15", "untrusted input qos-probe-replies registered"),
            ("K-PERF-6", "gates: M3 PRF.CPU.parallel-scaling and PRF.MEM.bandwidth, M5 PRF.BENCH.sim-worst-case, M6 PRF.PIPE.cook "
                         "and PRF.METH.model"),
            ("K-PLATFORM-7", "M4 exit requires a holder pre-submission or partner review on a console configuration"),
            ("K-PROD-2", "engine_release per milestone (M2 preview, M4 beta, M6 release candidate); XC.EXT.upgrade gated at M2"),
            ("K-PROD-3", "ARCH.ORG gates: ownership-ledger and agent-continuity at M0; change-requests, critic-calibration and "
                         "human-capacity at M1; escalation at M4"),
            ("K-PROD-6", "release mechanics gated: packaging at M2; patching and DLC at M4"),
            ("K-SEC-4", "untrusted input remote-play-input registered"),
            ("K-SEC-7", "untrusted input player-profile-strings registered"),
            ("K-TEST-3", "gates added per exit clause: UI.A11Y.validation M1, RND.GEO.cpu-submission M3, "
                         "QA.ROBUST.distributed-faults M6"),
            ("K-TOOLS-3", "tools configurations sandbox-2d-tools (M2), rt-required-3d-tools and aaa-experimental-tools (M6)")):
        ed.note(tags, text)
