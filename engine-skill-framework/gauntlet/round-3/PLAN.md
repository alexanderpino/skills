# Round 3 revision plan (decisions so far; implemented in r3_*.py)

Base: fd20381 (+ r3_a). Scripts run in name order; `r3_z.py` rebuilds milestones last. Findings not listed here are still to be read.

## Group 1 — governance, independence, oracle authors, milestones (r3_b, r3_z)
- **Oracle authors** (K-ARCH-1/2, K-PROD-1, K-SYSTEMS-6, K-TOOLS-5, K-PLATFORM-9, K-PERF-12): reassign every code contract's oracle_author to a quality/assurance/performance-workstream validator by domain; new check: author's workstream differs from owner's and all implementers' workstreams. Fix docs/00 §2 wording.
- **Escalation** (K-ARCH-3 partial, K-ARCH-4 reject-with-reason): same-workstream cross-lead disputes and disputes where a lead is a party go to engine-architect (ARCH.ORG.escalation wording + docs); no new per-workstream arbiter field, no new experts.
- **Organizations** (K-PROD-11): `data/organizations.json` with tiers (small/mid/large) mapping agents→skills; check: every skill hosted once per tier; independence pairs and oracle author vs owner/implementers on different agents.
- **Agent continuity** (K-PROD-5), **delegated planning** (K-PROD-6), **model requalification + lineage** (K-FUTURE-7): new capabilities in program-orchestration/architecture-governance; agent-coordination capabilities relabelled M with radar entries (K-FUTURE-8).
- **Milestones** (K-TOOLS-1/4, K-PLATFORM-3, K-SIM-2, K-FUTURE-2, K-PROD-3, K-PERF-10): build/CI/import skills into M0; freeze rules: needs_implementer contracts freeze after their last implementer, L≥2 contracts at the median consumer milestone, gated contracts at M6 with `extension_tiers`; gates become {capability, validator} with a validator owned outside the gated feature; add memory/pacing/baseline gates. C-PHYS becomes needs_implementer (K-SIM-4).
- **Tools/platform** (K-TOOLS-3,6-14; K-PLATFORM-1,2,6-8,10,12-14): see r3_c (editor/tools) and r3_d (platform).

## Still to read and dispose
NET, SIM (rest), RENDER, SYSTEMS, PERF, PROD (rest), FUTURE (rest), COMPLETE, LEGACY, GAMEPLAY, TEST, SEC (verifier outputs: verify_out_K-TEST.json, K-SEC pending).
