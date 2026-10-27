#!/usr/bin/env python3
"""Reproducible G1 round-1 revision: restores data/ to the round-0 commit, applies r1_a..r1_d,
writes gauntlet/round-1/changes.md and dispositions.md. Run from anywhere."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(FW, "scripts"))
sys.path.insert(0, HERE)

BASE_COMMIT = "72ac034"   # round-0 framework
subprocess.run(["git", "checkout", BASE_COMMIT, "--", "data/"], cwd=FW, check=True)
for extra in ("radar.json", "legacy-patterns.json", "milestones.json"):
    p = os.path.join(FW, "data", extra)
    if os.path.exists(p):
        os.remove(p)

from edit import Editor  # noqa: E402
import r1_a, r1_b, r1_c, r1_d  # noqa: E402

ed = Editor()
for part in (r1_a, r1_b, r1_c, r1_d):
    part.apply(ed)

# ---- dispositions: explicit overrides; everything else accepted if a change cites it
OVERRIDES = {
    "K-GAMEPLAY-4": ("partial", "View/camera arbitration placed in C-VIEW (L2, spatial-transforms) rather than a gameplay-owned "
                     "C-CAMERA, so the editor, XR and cinematics can drive views without the gameplay layer; gameplay "
                     "camera rigs are C-VIEW sources; shake/FOV channels and per-local-player views are in C-VIEW; "
                     "AUD.ARCH.listeners added."),
    "K-PERF-8": ("partial", "Governor added, but owned by the new runtime skill runtime-scalability: performance-architect "
                 "became a process skill (K-SYSTEMS-14), so it cannot own runtime code."),
    "K-SYSTEMS-13": ("partial", "Governor added under runtime-scalability instead of frame-orchestration, to keep one owner "
                     "for the actuator registry and the control loop (merged with K-PERF-8)."),
    "K-SYSTEMS-14": ("partial", "C-BUDGET split as proposed; the runtime C-SCALE is owned by the new expert "
                     "runtime-scalability under core-runtime-architect rather than by the lead itself."),
    "K-RENDER-7": ("partial", "texture-streaming-vt retagged 'all' with VT/feedback/NTC gated by capability-level profiles "
                   "instead of splitting the skill; 2.5D handled by the lite3d base profile with first-class CPU "
                   "submission (RND.GEO.cpu-submission) and planar physics (PHY.DYN.dof-lock)."),
    "K-LEGACY-7": ("partial", "Stance rewritten and CPU submission made first-class, but kept in the same skill (renamed "
                   "geometry-pipeline) because both paths serve one contract (C-INSTANCES); the per-tier choice is an "
                   "ADR owned by render-architect (RND.ARCH.submission-strategy)."),
    "K-PROD-2": ("partial", "Write sets defined by module convention (src/<skill-id>/, tools/<skill-id>/, tests by the "
                 "test-owning skill) and a shared-file protocol in C-ORCH + ARCH.ORG.write-sets; per-skill path globs are "
                 "deferred until code exists (revisit at M0)."),
    "K-PROD-8": ("partial", "workstream field on every skill, ARCH.ORG.staffing and ARCH.GOV.process-tiers added; a "
                 "per-skill host_group field is deferred to the staffing capability (revisit at M0 planning)."),
    "K-QUALITY-6": ("partial", "Conformance ownership stated in C-TEST/C-ORCH and a conformance flag on every code contract "
                    "(checked); a separate conformance-owner field is redundant because the owner is always the "
                    "contract owner."),
    "K-FUTURE-10": ("partial", "All proposed MR capabilities added to xr-runtime; splitting a mixed-reality skill rejected "
                    "for now (xr-runtime owns 14 capabilities, below the size warning). Revisit if G2 shows distinct "
                    "literature load."),
    "K-TOOLS-12": ("partial", "Blockout and level-design utilities added to world-editor-viewport and geometry operations "
                   "to asset-cook-processors; a separate mesh-modeling-tools skill is deferred (revisit in G2)."),
    "K-COMPLETE-3": ("partial", "HTTP(S)/TLS client placed in the PAL (platform stacks are mandatory on consoles) and "
                     "crypto primitives in containers-core-types with a security-owned policy capability "
                     "(XC.SEC.crypto-policy), instead of security owning the primitives."),
    "K-GAMEPLAY-15": ("partial", "C-AIAGENT extension point, maturity changes and guardrail capabilities added; the proposed "
                      "generic check.py rule for X/S capabilities is replaced by the radar rule (every non-E capability "
                      "needs owner, revisit trigger and fallback)."),
    "K-GAMEPLAY-3": ("accept", "C-INPUT is now the device-free action schema and command-frame contract for all targets; "
                     "input-system ships in every target; device binding is client-side via C-DEVICE."),
    "K-PROD-18": ("accept", "06-gap-analysis.md was written during the round (after the critic's read); it now exists and "
                  "is updated for round-1 changes."),
    "K-ARCH-13": ("accept", "build-release-architect provides C-RELEASE; orchestration moved to ci-cd-automation; the lead "
                  "rule is enforced by check.py (a lead must provide a contract; <3 children without a code contract "
                  "warns)."),
    "K-QUALITY-4": ("accept", "ARCH.ORG.critic-calibration and ARCH.ORG.adjudication added, and applied to this gauntlet "
                    "from round 1: partial dispositions go to an independent adjudicator; round 2 onward uses seeded "
                    "defects to measure critic recall (see PROTOCOL.md)."),
    "K-SYSTEMS-2": ("accept", "Module attribution ('C-X@C-Y') added to the schema; check.py verifies each consumed contract "
                    "is at or below the layer of the consuming module; C-DET split into C-DET/C-SNAPSHOT/C-REPLAY; "
                    "C-ML split into C-ML (L2, CPU/NPU) and C-MLGPU (L3)."),
}
tag_index = {}
for tags, text in ed.log:
    for t in re.findall(r"K-[A-Z]+-\d+", tags or ""):
        tag_index.setdefault(t, []).append(text)

findings = []
for fn in sorted(os.listdir(HERE)):
    if fn.startswith("K-") and fn.endswith(".md"):
        for line in open(os.path.join(HERE, fn), encoding="utf-8"):
            mm = re.match(r"### (K-[A-Z]+-\d+) · (\w+) · ([\w-]+)", line)
            if mm:
                findings.append(mm.groups())

unaddressed = []
rows = []
for fid, sev, typ in findings:
    if fid in OVERRIDES:
        verdict, note = OVERRIDES[fid]
    elif fid in tag_index:
        verdict, note = "accept", "; ".join(tag_index[fid][:4]) + (" …" if len(tag_index[fid]) > 4 else "")
    else:
        verdict, note = "UNADDRESSED", ""
        unaddressed.append(fid)
    rows.append((fid, sev, typ, verdict, note))

ed.save()

with open(os.path.join(HERE, "changes.md"), "w", encoding="utf-8") as f:
    f.write("# G1 round 1 — change log\n\nGenerated by `apply.py`. Every change cites the findings that motivated it.\n\n")
    for tags, text in ed.log:
        f.write(f"- {text}" + (f"  _[{tags}]_" if tags else "") + "\n")
with open(os.path.join(HERE, "dispositions.md"), "w", encoding="utf-8") as f:
    from collections import Counter
    cnt = Counter((sev, v) for _, sev, _, v, _ in rows)
    f.write("# G1 round 1 — dispositions\n\nGenerated by `apply.py`. `partial` dispositions were sent to an independent "
            "adjudicator (see adjudication.md).\n\n")
    f.write("| severity | accept | partial | reject | unaddressed |\n|---|---|---|---|---|\n")
    for sev in ("blocker", "major", "minor"):
        f.write(f"| {sev} | {cnt[(sev,'accept')]} | {cnt[(sev,'partial')]} | {cnt[(sev,'reject')]} | {cnt[(sev,'UNADDRESSED')]} |\n")
    f.write("\n| Finding | Sev | Type | Disposition | Change / reason |\n|---|---|---|---|---|\n")
    for fid, sev, typ, v, note in rows:
        f.write(f"| {fid} | {sev} | {typ} | {v} | {note.replace('|', '/')} |\n")

print(f"{len(findings)} findings; {len(ed.log)} logged changes; unaddressed: {unaddressed}")
