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
    "K-FUTURE-15": ("reject", "verifier: tool-side ML generation is already M under ED.AI.generative/ED.AI.provenance and CNT.COOK.ml-assisted; the X row is the in-PCG runtime path"),
}
