"""Round-4 dispositions that are not plain 'accept'."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
SEED_HITS = {}
for sid, fids in json.load(open(os.path.join(_HERE, "seed_hits.json"))).items():
    for f in fids:
        SEED_HITS[f] = sid

OVERRIDES = {}
