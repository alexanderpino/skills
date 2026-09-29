"""Round-2 dispositions that are not plain 'accept'. Seed hits come from seed_hits.json; a seed hit whose finding
also names a real defect is reported as seed+residual when a logged change cites it."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
SEED_HITS = {}
for sid, fids in json.load(open(os.path.join(_HERE, "seed_hits.json"))).items():
    for f in fids:
        SEED_HITS[f] = sid

OVERRIDES = {
    "K-SIM-1": ("seed/partial", "Seed S12. The proposed rule (capability names must not match legacy detection strings) "
                "is replaced by a stronger one: every legacy pattern names the capabilities that carry its modern "
                "stance, and check.py verifies them (r2_y)."),
    "K-FUTURE-1": ("seed/partial", "Seed S13; residual accepted (work-graph programs split out as X, radar class = "
                   "maturity rule). Device-generated commands stay inside the established RND.RHI.gpu-work: "
                   "ExecuteIndirect state changes and VK_EXT_device_generated_commands are shipped, cross-vendor APIs."),
    "K-SYSTEMS-3": ("partial", "Explicit C-FRAME/C-FLOW edges added to the eight multi-rate skills. The proposed "
                    "check.py rule is rejected: 'schedules per-frame work' is not decidable from the data without a "
                    "new per-capability field, and C-FRAME is consumed by every skill that registers phase work."),
    "K-SIM-3": ("partial", "Cellular/falling-sand fluids added and a min2d+sandbox configuration proves them. "
                "fluid-simulation is gated on the sandbox/massim/aaa add-ons rather than every base profile, because "
                "profile membership means 'available in every such build'."),
    "K-PLATFORM-3": ("partial", "C-PAL now needs a per-platform implementer and the platform experts implement it; the "
                     "per-platform closure check proves one backend per platform. A separate 'slots' data field is not "
                     "added: ARCH.STRUCT.platform-backends keeps the slot list."),
    "K-PLATFORM-6": ("partial", "NDA access class added and enforced; console skills are instantiated per platform "
                     "holder ('instances' field) instead of duplicated per holder in the data; confidential slot "
                     "implementations consolidated in PLAT.CON.confidential-slots instead of a per-capability field."),
    "K-PLATFORM-12": ("partial", "headless-client/server targets removed; the tools target is kept because the "
                      "platform skills now implement C-TARGETPLAT tool modules (K-PLATFORM-7)."),
    "K-NET-8": ("partial", "Boundaries of the four capabilities made explicit (scenarios, runner, bot harness, link "
                "conditioner); scenario definitions stay with network-architect but every change needs "
                "simulation-validation co-signature (QA.AGENT.oracle-change-control) instead of moving the oracle."),
    "K-NET-19": ("partial", "Radar entries added (L4S, MoQ, behavioral detection, user-mode anti-cheat). Server "
                 "meshing is aligned to M rather than X in data, radar and A5, because a live deployment exists."),
    "K-ARCH-14": ("partial", "All listed routes and purposes corrected. The proposed keyword lint on non-responsibility "
                  "text is rejected as unreliable; the authoring, legacy-stance and oracle rules cover the structural "
                  "part."),
    "K-ARCH-17": ("partial", "plugin-system and modding-ugc reparented. anti-cheat-integrity stays under "
                  "security-engineering: it also owns offline score integrity, attestation and privacy-sensitive "
                  "client code; networking reaches it through C-INTEGRITY."),
    "K-TOOLS-8": ("partial", "Runtime edit sessions (C-EDIT) owned by modding-ugc, which owns in-game creation; the "
                  "command schema is shared through ED.ARCH.transactions instead of C-EDCMD extending C-EDIT, so the "
                  "editor has no dependency on the UGC runtime. The 'mod-sdk' name rule is replaced by the general "
                  "tool-side rule."),
    "K-LEGACY-7": ("partial", "Tool contracts added and enforced for cook/bake/editor territory; the tool side is "
                   "derived from capability wording instead of a new per-capability 'side' field."),
    "K-LEGACY-12": ("partial", "Grid/sources/HLOD tagged lite3d+std3d (linear 3D games stream too), server streaming "
                    "openworld, simulation tiers openworld+massim; WLD.MODEL.unit-load added for minimal/2D."),
    "K-PROD-3": ("partial", "reference-games becomes a build skill with game-code, content-acquisition and upkeep "
                 "capabilities; it is not promoted to a lead with a new workstream (one agent per reference "
                 "configuration is a staffing decision under ARCH.ORG.staffing)."),
    "K-PROD-7": ("partial", "Ladder rebuilt M0–M7 (runtime-on-PC vs all platforms + tools, patch/DLC/rollback at M4, "
                 "engine 1.0/LTS at M7). M1 still adds 44 skills because its claimed configuration requires them "
                 "(check.py proves it); live-ops and end-of-service rehearsal folded into M7."),
    "K-TEST-2": ("partial", "QA.SIM capabilities renamed to the artifacts simulation-validation uniquely owns and its "
                 "contract access added; scenario definitions stay in the domain *.ARCH.validation capabilities with "
                 "co-signature."),
    "K-SEC-14": ("partial", "Dev surfaces declared on their owning skills and an exclusion capability with fitness "
                 "function and binary scan added; the scan is that capability's deliverable, not a check.py rule."),
    "K-FUTURE-7": ("partial", "ml-inference-runtime is now profile 'all' under core-runtime-architect; the extra "
                   "narrative-llm configuration is not added because minimal-client now contains the ML runtime and "
                   "proves the path."),
    "K-GAMEPLAY-2": ("partial", "C-ABILITY, C-CROWD and C-SEQ added; tags are exposed through C-GAMEDATA instead of a "
                     "new C-TAGS contract."),
    "K-GAMEPLAY-3": ("partial", "Established AI surface added as a new contract C-AI; C-AIAGENT stays the gated "
                     "optional extension point for learned/LLM providers instead of being renamed."),
    "K-GAMEPLAY-5": ("partial", "One settings mechanism: settings are declared as scoped C-CFG entries and persisted "
                     "by persistence-save into the C-CFG user layer. No new C-SETTINGS: runtime-scalability (L1) cannot "
                     "consume C-SAVE (L3)."),
    "K-GAMEPLAY-12": ("partial", "Team visibility owned by ai-behavior-perception (all profiles; roguelikes need it) "
                      "instead of the toolkit; markers in the toolkit and the map service in ui-architect."),
    "K-COMPLETE-4": ("partial", "Added as GAM.AI.team-visibility under ai-behavior-perception (merged with "
                     "K-GAMEPLAY-12) instead of crowd-simulation, which exists only in openworld/massim."),
}
