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
