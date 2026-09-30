"""Round-4 finalisation: freeze every new code contract at the earliest milestone that respects its owner, oracle
author, requirements and dependants (the ladder itself was built in round 3)."""


def apply(ed, tagged=True):
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
            cons = [placed[x["id"]] for x in ed.doc["skill"]["skills"] if x["id"] in placed and x["id"] != c["owner"]
                    and cid in {d.rstrip("?").split("@")[0] for d in x.get("consumes", []) + x.get("tool_consumes", [])}]
            if cons:
                f = max(f, min(cons))
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
    freeze_before_claim(ed, tagged)
    if tagged:
        notes(ed)
    rd = ed.doc["radar"]
    for e in rd["entries"]:
        e.setdefault("reviewed", rd.get("as_of", "2026-09-30"))


def _model(ed):
    import json
    import os
    import sys
    import tempfile
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
    import model as model_mod
    tmp = tempfile.mkdtemp()
    for k, f in (("cap", "capabilities.json"), ("skill", "skills.json"), ("contract", "contracts.json"),
                 ("critic", "critics.json"), ("cross", "crosscutting.json"), ("seed", "seed-map.json"),
                 ("radar", "radar.json"), ("legacy", "legacy-patterns.json"), ("milestone", "milestones.json"),
                 ("untrusted", "untrusted-inputs.json"), ("org", "organizations.json")):
        with open(os.path.join(tmp, f), "w", encoding="utf-8") as fh:
            json.dump(ed.doc[k], fh)
    old = model_mod.DATA
    model_mod.DATA = tmp
    try:
        return model_mod.Model()
    finally:
        model_mod.DATA = old


def freeze_before_claim(ed, tagged=True):
    """K-ARCH-7: every non-optional contract in a claimed configuration's closure is frozen at or before the claim;
    contracts that must freeze earlier than the round-3 rule keep their later additions as an extension tier."""
    m = _model(ed)
    ms = ed.doc["milestone"]["milestones"]
    fr = {c: i for i, x in enumerate(ms) for c in x["contracts_frozen"]}
    placed = {s: i for i, x in enumerate(ms) for s in x["skills"]}
    need = {}
    for i, x in enumerate(ms):
        for c in x["configurations"]:
            for s in m.members(c.split("@")[0]):
                for cid, opt in m.deps(s, include_universal=True):
                    if not opt and cid in fr and m.layer(cid) != "P" and fr[cid] > i:
                        need[cid] = min(need.get(cid, 99), i)
    changed = True
    while changed:
        changed = False
        for cid in list(need):
            for r in m.contract(cid)["requires"]:
                if r in fr and fr[r] > need[cid] and need.get(r, 99) > need[cid]:
                    need[r] = need[cid]
                    changed = True
    new = dict(fr)
    for cid in need:
        new[cid] = need[cid]
    for _ in range(len(need) + 2):      # raise to lower bounds until stable (requirements before dependants)
        for cid in need:
            c = m.contract(cid)
            lb = max([placed.get(c["owner"], 0), placed.get(c.get("oracle_author"), 0)]
                     + [new.get(r, 0) for r in c["requires"] if r in new and m.layer(r) != "P"])
            new[cid] = min(fr[cid], max(lb, need[cid]))
    moved = []
    for cid, k in new.items():
        if k != fr[cid]:
            for x in ms:
                if cid in x["contracts_frozen"]:
                    x["contracts_frozen"].remove(cid)
            ms[k]["contracts_frozen"] = sorted(ms[k]["contracts_frozen"] + [cid])
            c = next(c for c in ed.doc["contract"]["contracts"] if c["id"] == cid)
            c.setdefault("extension_tiers", {})["late-consumers"] = ms[fr[cid]]["id"]
            moved.append(f"{cid} {ms[fr[cid]]['id']}->{ms[k]['id']}")
    ed.note("K-ARCH-7" if tagged else "", "contracts frozen at or before the first claim that needs them; the round-3 freeze milestone "
                        "becomes the extension tier 'late-consumers': " + ", ".join(moved))


def notes(ed):
    for tags, text in (
            ("K-GAMEPLAY-12", "legacy catalogue L85–L88 (text without shaping, sentence concatenation, synchronous pathfinding, "
                              "hard-coded tunables); L72 stance capabilities extended"),
            ("K-LEGACY-4", "L27 split into ECS, GPU-driven (L81), neural-by-default (L82) and async-physics-by-default (L83)"),
            ("K-NET-10", "untrusted input server-list-entries registered"),
            ("K-PERF-7", "gates: M2 PRF.NET.resim-cost and PRF.MEM.size, M3 PRF.METH.energy, M4 PRF.NET.latency (M5 XR energy "
                         "gate not added: one gate per capability) (partial)"),
            ("K-PERF-9", "legacy catalogue L79 (thread-per-subsystem) and L80 (unbounded stage queues)"),
            ("K-PLATFORM-5", "configurations lite-3d-mobile-openworld-online-client, lite-3d-portable-openworld-client, "
                             "lite-3d-web-client claimed at M5"),
            ("K-SIM-11", "untrusted input physics-assets registered"),
            ("K-SIM-13", "legacy catalogue L76–L78 (discrete-only collision, always-awake world, rollback over non-restorable "
                         "state)"),
            ("K-TOOLS-10", "untrusted inputs tabular-imports, localization-exchange, narrative-imports, vendor-deliveries, "
                           "tracker-webhooks registered")):
        ed.note(tags, text)
