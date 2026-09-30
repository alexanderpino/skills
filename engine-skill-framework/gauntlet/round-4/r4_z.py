"""Round-4 finalisation: freeze every new code contract at the earliest milestone that respects its owner, oracle
author, requirements and dependants (the ladder itself was built in round 3)."""


def apply(ed):
    ms = ed.doc["milestone"]["milestones"]
    idx = {m["id"]: i for i, m in enumerate(ms)}
    placed = {s: i for i, m in enumerate(ms) for s in m["skills"]}
    frozen = {c: i for i, m in enumerate(ms) for c in m["contracts_frozen"]}
    ctr = {c["id"]: c for c in ed.doc["contract"]["contracts"]}
    new = [c for c in ctr if ctr[c]["layer"] != "P" and c not in frozen]
    for _ in range(len(new) + 1):
        for cid in new:
            c = ctr[cid]
            f = max([placed.get(c["owner"], 0), placed.get(c.get("oracle_author"), 0)]
                    + [frozen.get(r, 0) for r in c["requires"]])
            # never after a dependant that is already frozen
            deps = [frozen[d] for d, x in ctr.items() if cid in x["requires"] and d in frozen]
            if deps and f > min(deps):
                f = min(deps)
            frozen[cid] = f
    for cid in new:
        for m in ms:
            if cid in m["contracts_draft"]:
                m["contracts_draft"].remove(cid)
        ms[frozen[cid]]["contracts_frozen"] = sorted(ms[frozen[cid]]["contracts_frozen"] + [cid])
        ed.note("", f"contract {cid} frozen at {ms[frozen[cid]]['id']}")
