"""Round-3 dispositions that are not plain 'accept' (filled after the critics report)."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
SEED_HITS = {}
if os.path.exists(os.path.join(_HERE, "seed_hits.json")):
    for sid, fids in json.load(open(os.path.join(_HERE, "seed_hits.json"))).items():
        for f in fids:
            SEED_HITS[f] = sid

OVERRIDES = {}
