"""Round-3 dispositions that are not plain 'accept' (filled after the critics report)."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
SEED_HITS = {}
if os.path.exists(os.path.join(_HERE, "seed_hits.json")):
    for sid, fids in json.load(open(os.path.join(_HERE, "seed_hits.json"))).items():
        for f in fids:
            SEED_HITS[f] = sid

OVERRIDES = {
    "K-ARCH-3": ("partial", "adjudicator OVERTURNED the remainder, fixed in r3_h/docs; same-workstream lead disputes and disputes in which the arbitrating lead is a party go to engine-architect; delegated arbitration otherwise stays"),
    "K-ARCH-4": ("reject", "no new expert skills for the proposed roles; party leads recuse instead (ARCH.ORG.escalation)"),
    "K-TOOLS-8": ("partial", "shared DDC moves to a team-mid add-on and CNT.COOK.cache-fleet stays team-large; configuration standard-3d-team-tools added"),
    "K-PLATFORM-1": ("partial", "confidential slots extended and C-CERT split into public register and per-holder partitions; no module-level access field"),
    "K-PLATFORM-8": ("partial", "rhi-d3d12 contributes to RND.RHI.console and a non-responsibility is recorded; no new backend module"),
    "K-FUTURE-1": ("partial", "gated contracts stay optional so non-RT builds stay buildable; RT-required products are the hwrt profile plus rt/rt+tensor GPU tiers and configuration rt-required-3d-client"),
    "K-GAMEPLAY-4": ("partial", "C-CAMERA added at layer 4; layer-3 vehicle and dialogue modules publish camera hints as data instead of consuming it (no upward link)"),
    "K-RENDER-6": ("partial", "C-PTREF added; path-tracing consumes C-LIGHT/C-TEMPORAL optionally rather than per-module attribution"),
    "K-TEST-4": ("partial", "oracle_reference required on layer 0–2 contracts; oracle authors are quality/assurance validators (co-authoring by consumers is by change request)"),
    "K-TEST-6": ("partial", "adjudicator OVERTURNED the remainder, fixed in r3_h/docs; BLD.CI.sealed-suites added; the sealed:oracle access class is a phase-2 SKILL.md obligation, not a data field"),
    "K-COMPLETE-6": ("partial", "overlaps K-NET-6/9: content-set and server-browser cover join-time negotiation; NET.SRV.community-hosting added for redistribution and rulesets"),
    "K-COMPLETE-12": ("merge", "duplicate of K-TOOLS-14 (ED.UI.outliner)"),
    "K-GAMEPLAY-7": ("partial", "adjudicator OVERTURNED the remainder, fixed in r3_h/docs; UI.LOC.terms added; no radar entry (capability is established)"),
    "K-GAMEPLAY-3": ("accept", "GAM.DATA.tags in gameplay-data; tag queries removed from C-ABILITY"),
    "K-RENDER-5": ("reject", "verifier: layer-2 producers exposing work items that the graph imports (RND.GRAPH.external-work) is the sanctioned inversion, same as C-GPUMEM uploads and C-IO GPU decompression; the layer-3 C-RT module already wraps C-RTAS in graph passes"),
    "K-SIM-11": ("reject", "verifier: runtime collision geometry is derived from inputs already registered (mods, assets, input-commands); PHY.COL.runtime-build is budgeted and NET.SESS.budgets bounds client-triggered work; a derived-data entry would misuse parser_owners"),
    "K-PROD-8": ("reject", "verifier: QA.FUNC.bug-capture and OBS.CRASH.feedback already exist with the proposed owner and contributors"),
    "K-GAMEPLAY-14": ("reject", "verifier: acoustic propagation is a frontier at the runtime tier; M is honest for the real-time/dynamic-geometry path and the radar carries the fallback"),
    "K-SEC-6": ("reject", "verifier: agent capability scoping, egress and secret scope are owned by XC.SEC.agent-boundary and CI/secret capabilities; a per-skill access object duplicates them"),
    "K-SEC-8": ("reject", "verifier: the LLM front end is emerging (M6 owner is right); its permission model is already ED.ARCH.automation-security"),
    "K-SEC-12": ("reject", "verifier: plugin signing, workspace trust and sandboxed tool plugins are covered by XC.SEC.dev-trust and XC.EXT.mod-editor"),
    "K-SEC-15": ("reject", "verifier: XC.SEC.tamper is a policy/boundary capability like XC.SEC.hardening; packaging implementation sits under BLD.REL.packaging"),
    "K-PLATFORM-7": ("reject", "both verifier lenses: not supported by the data"),
    "K-PLATFORM-12": ("reject", "both verifier lenses: not supported by the data"),
    "K-FUTURE-15": ("reject", "verifier: tool-side ML generation is already M under ED.AI.generative/ED.AI.provenance and CNT.COOK.ml-assisted; the X row is the in-PCG runtime path"),
}
