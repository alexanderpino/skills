"""Round-4 dispositions that are not plain 'accept'."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
SEED_HITS = {}
for sid, fids in json.load(open(os.path.join(_HERE, "seed_hits.json"))).items():
    for f in fids:
        SEED_HITS[f] = sid

OVERRIDES = {
    "K-ARCH-2": ("reject", "verifier: The counts (74 vs 98 members, cosmetic skills tagged 'all' or server) are accurate, but docs/06 section C item 4 records that membership means 'may be built, not must be built' and that the reference game proves use. The finding c"),
    "K-ARCH-6": ("reject", "verifier: Partly wrong: BLD.CI.sealed-suites is owned by the tool skill ci-cd-automation, and C-ORCH is already frozen in M0. Coordination is a recorded emerging radar entry with a human-coordinator fallback (docs/09), so 'include in M0' an"),
    "K-COMPLETE-5": ("reject", "verifier: Timezone/DST is absent, but PLAT.LIVE.events already owns time-gated activation with trusted-time as authority, so calendar/tzdata policy is an implementation detail of an existing capability rather than a framework-level ownershi"),
    "K-FUTURE-7": ("reject", "verifier: The WebGL non-goal and its measured-share revisit trigger (PLAT.WEB.audience-share) are a recorded, reasoned scope decision in docs/00 and radar, and the finding adds no new evidence beyond the general WebGPU rollout tail."),
    "K-GAMEPLAY-6": ("reject", "verifier: The premise that the minimal profile is narrative-centric and carries VN needs is not evidenced in the data or docs, and portrait staging and text reveal are game-level content (docs/06 C.2 scopes game-specific systems out), so ma"),
    "K-LEGACY-2": ("reject", "verifier: Baked GI/PVS exist as E capabilities, but docs/06 B5 already records 'baked stays for low tiers', dynamic GI and GPU HZB occlusion capabilities already exist, and using the baked capabilities as stance for an anti-baked pattern is"),
    "K-LEGACY-3": ("reject", "verifier: Four unrelated gaps are bundled and each is partly covered (L03/CORE.JOBS.thread-model for threads, L65/L16/L66 for sleeps, blocking IO and budgeted allocation), and they are catalogue-completeness wishes rather than a major defec"),
    "K-LEGACY-7": ("reject", "verifier: L39, L18, L07 and WLD.MODEL.strategy/file-per-object already stance partitioned worlds, the renames are cosmetic, and adding the bare term 'level' to contradiction_terms would false-positive on many unrelated capability and skill "),
    "K-LEGACY-8": ("reject", "verifier: CORE.OBJ.world-instances already states world-scoped state reachable only through a world handle with no current-world global and L32 stances it, so ECS singletons are already covered and the finding is a naming preference."),
    "K-NET-1": ("reject", "verifier: Only C-REP lacks an M2 configuration (replication is profile 'online' only); C-PREDICT, C-NETSESSION and C-HOSTAUTH are exercised at M2 by fighting-2d-rollback-client (online-rollback contains prediction-rollback, net-session and "),
    "K-NET-11": ("reject", "verifier: ANM.RT.pose-history is indeed restricted to lite3d/std3d, but PHY.ARCH.rewind already covers collider history, GAM.SYS.hit-detection owns frame-data hitboxes with a prediction-rollback contributor, and frame-data hitboxes are stat"),
    "K-NET-6": ("reject", "verifier: The configuration facts are true, but docs/00 records a reasoned decision that input-only netcode families are separate add-ons not linked to state replication/servers, relay operation is external:backend, and lockstep/rollback so"),
    "K-NET-7": ("reject", "verifier: Overstated: C-PREDICT already lists rewind queries and consumes C-PHYS?/C-ANIM?, NET.PRED.lagcomp is owned by prediction-rollback (so the composed query has an owner), and C-PREDICT no longer requires C-REP by a recorded decision;"),
    "K-PLATFORM-10": ("reject", "verifier: ML.RT.npu is X by a recorded, reasoned radar entry with a revisit trigger, and check.py ties radar class to capability maturity. Splitting it and adding a platform slot re-argues that decision without new evidence."),
    "K-PLATFORM-8": ("reject", "verifier: UI.A11Y.screen-reader and UI.TXT.ime are owned by the domain skills with platform-architect as contributor. That is the framework's standard domain-owns, platform-contributes pattern, so this is an ownership preference rather than"),
    "K-PLATFORM-9": ("reject", "verifier: platform-server-host is defined as having no GPU and rhi-vulkan omits server-host. The GPU-server cases are speculative: tools configurations run on pc and a null/software GPU device exists for headless CI, so no closure failure i"),
    "K-PROD-1": ("reject", "verifier: XC.EXT.lts ('LTS & support policy', owned by api-lifecycle-migration) and BLD.REL.end-of-service already exist and are M7 gates, so the support commitment is covered and the 'nothing found' claim is wrong."),
    "K-PROD-3": ("reject", "verifier: The absence of an external design-partner program is real, but making external titles milestone exit gates (M2/M4/M7) makes agent-executed milestones depend on outside parties and is a business-development request beyond the engin"),
    "K-RENDER-6": ("reject", "verifier: Partly covered already: RND.ARCH.multiview names PiP and captures, RND.ARCH.portals exists, GAM.CAM.photo is owned, and PLAT.SVC.capture ('Media capture & share integration') covers platform share-capture, so the claim that offscr"),
    "K-SEC-4": ("reject", "verifier: The numbers are wrong (12 of 32 XC.SEC capabilities are in gates, so 20 are not, not 22 of 30), and XC.SEC.agent-redteam is already a gate validator at M0 and XC.SEC.testing at M4 (NET.TRANS.dos); only the claims for dev-trust, in"),
    "K-SEC-5": ("reject", "verifier: security-engineering is a process skill with a security-runtime child and a domain critic, and splitting a policy owner for the agent program is an organizational preference with no evidenced defect."),
    "K-SEC-6": ("reject", "verifier: cloud-saves is labeled semi-trusted-signed but is registered in harness mode with the same size/depth limits as saves, so the label does not reduce fuzz or limit coverage and the relabel is cosmetic."),
    "K-SEC-8": ("reject", "verifier: XC.SEC.tamper is already co-owned with runtime skill anti-cheat-integrity, and security-runtime already provides C-SIGN signed-artifact verification, so the implementation slot is not unowned and the finding overstates the gap."),
    "K-SIM-5": ("reject", "verifier: The profile facts are right, but docs/06 C4 records that membership means 'may be built', not 'must be built'. 'sandbox-3d' is not a profile and profile matching is OR-only, so 'aaa and sandbox-3d' cannot be expressed. Dropping li"),
    "K-SIM-6": ("reject", "verifier: physics-architect does own 22 capabilities, but that is under the MAX_CAPS_SKILL limit of 30 and platform-architect (26) and ui-architect (22) are in the same range, so this is an organizational preference; the events overlap clai"),
    "K-TEST-2": ("reject", "verifier: Gate objects do carry only capability and validator, but the claimed circular pair is wrong (M0 gate-canaries is validated by agent-redteam, not agent-boundary), the 28-gate count is unverified, and moving security-engineering out"),
    "K-TEST-4": ("reject", "verifier: Author counts (35/26/26/24) are accurate, but expertise fit is a judgment about skill breadth that the framework can widen by description, and relocating CORE.CONC.correctness away from its implementer is a contestable design pref"),
    "K-TOOLS-5": ("reject", "verifier: minimal-tools does include the 'all'-profile editor skills, but the proposed minimal-cli-tools without editor-architect cannot close because minimal-profile skills such as material-system and animation-runtime require C-EDCMD via "),
    "K-ARCH-4": ("partial", "hooks-only wording applied; the owner-equals-implementer check is not added"),
    "K-ARCH-5": ("partial", "two conformance experts added and contracts re-pointed; robustness-fuzzing keeps parsers and fault campaigns"),
    "K-ARCH-12": ("partial", "first-instance arbiter wording added; a data check for named process contracts is not added"),
    "K-ARCH-8": ("partial", "C-REWIND added as optional consumer path; no needs_implementer"),
    "K-TOOLS-3": ("partial", "tool contracts still freeze at M3; earlier tool halves are headless (commandlet) over C-CMD"),
    "K-TOOLS-7": ("partial", "RND.TOOL.direct-lights added; 'rendering' is not added to AUTHORING_WORKSTREAMS"),
    "K-PLATFORM-6": ("partial", "store axis carried by capabilities, not a platform_variants field"),
    "K-PERF-3": ("partial", "gate moved to M1 and circularity broken; scale-probe precondition on freezes not added"),
    "K-PERF-7": ("partial", "four of five gates added"),
    "K-FUTURE-2": ("partial", "reviewed date, as_of and max_age checked; evidence_refs typing not added"),
    "K-FUTURE-3": ("partial", "capability and radar entry added; no new target/platform value"),
    "K-TEST-1": ("partial", "process skills declared staffed at M0 and checked; per-milestone process staffing not modelled"),
    "K-PROD-7": ("partial", "folded into ARCH.ORG.human-capacity; no milestone gates"),
}
