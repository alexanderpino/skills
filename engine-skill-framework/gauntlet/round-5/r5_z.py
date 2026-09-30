"""Round-5 finalisation: freeze new contracts, keep the M0 process-skill list and radar dates current."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round-4"))
import r4_z  # noqa: E402


def apply(ed):
    r4_z.apply(ed, tagged=False)
    procs = [s["id"] for s in ed.doc["skill"]["skills"] if s.get("kind") == "process"]
    ed.doc["milestone"]["milestones"][0]["process_skills"] = sorted(procs)
