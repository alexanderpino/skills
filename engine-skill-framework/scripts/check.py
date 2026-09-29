#!/usr/bin/env python3
"""Validates the engine skill framework. Exit 1 on any error.

Machine-checks the parts of the definition of done that are structural:
  every capability has exactly one existing owner; every skill owns territory;
  contracts have one owner that provides them; build-level contract layering is
  acyclic and never points upward; every consumed contract exists; every named
  non-responsibility points at a real, different skill; each configuration
  (indie 2D ... AAA online ... dedicated server) is closed under its required
  dependencies, which is what proves the architecture scales down; every skill
  has a domain critic; every brief term maps to real capabilities.

Usage: python3 scripts/check.py [--selftest]
"""
import sys

from model import MATURITY, TIERS, Model, sccs

MIN_CAPS_EXPERT = 3
MAX_CAPS_SKILL = 30


def run(m):
    errors, warnings, info = [], [], []
    E, W, I = errors.append, warnings.append, info.append

    # -- uniqueness
    for kind, table in (("capability", m.caps), ("skill", m.skills), ("contract", m.contracts)):
        for k, v in table.items():
            if len(v) > 1:
                E(f"duplicate {kind} id: {k}")

    # -- capabilities
    for cid in m.caps:
        c = m.cap(cid)
        if c["owner"] not in m.skills:
            E(f"capability {cid} owner '{c['owner']}' is not a skill")
        if c["maturity"] not in MATURITY:
            E(f"capability {cid} maturity '{c['maturity']}' not in {list(MATURITY)}")
        for co in c["contributors"]:
            if co not in m.skills:
                E(f"capability {cid} contributor '{co}' is not a skill")
            if co == c["owner"]:
                E(f"capability {cid} lists its owner as contributor")
        if not cid.startswith(c["area"] + "."):
            E(f"capability {cid} id does not start with its area id {c['area']}")

    # -- skills: tiers, parents, territory
    roots = [s for s in m.skill_order if m.skill(s)["parent"] is None]
    if len(roots) != 1:
        E(f"expected exactly one root skill, found {roots}")
    for sid in m.skill_order:
        s = m.skill(sid)
        if s["tier"] not in TIERS:
            E(f"skill {sid} tier '{s['tier']}' invalid")
        p = s["parent"]
        if p is not None and p not in m.skills:
            E(f"skill {sid} parent '{p}' is not a skill")
        seen, cur = set(), sid
        while cur is not None and cur in m.skills:
            if cur in seen:
                E(f"skill {sid}: parent chain has a cycle")
                break
            seen.add(cur)
            cur = m.skill(cur)["parent"]
        n = len(m.owned_caps(sid))
        if n == 0:
            E(f"skill {sid} owns no capability (a skill without territory)")
        elif s["tier"] == "expert" and n < MIN_CAPS_EXPERT:
            W(f"expert skill {sid} owns only {n} capabilities (microscopic?)")
        if n > MAX_CAPS_SKILL:
            W(f"skill {sid} owns {n} capabilities (monolithic?)")
        for what, owner in s["non_responsibilities"]:
            if owner not in m.skills:
                E(f"skill {sid} non-responsibility '{what}' points at unknown skill '{owner}'")
            elif owner == sid:
                E(f"skill {sid} non-responsibility '{what}' points at itself")
        if not s["non_responsibilities"]:
            E(f"skill {sid} declares no non-responsibilities")
        for tok in s["profiles"]:
            if tok not in ("all", "client") and tok not in m.profiles_base and tok not in m.profiles_addon:
                E(f"skill {sid} profile token '{tok}' unknown")

    # -- contracts
    for cid in m.contracts:
        c = m.contract(cid)
        o = c["owner"]
        if o not in m.skills:
            E(f"contract {cid} owner '{o}' is not a skill")
        elif cid not in m.skill(o)["provides"]:
            E(f"contract {cid} owner {o} does not list it in provides")
        for r in c["requires"]:
            if r not in m.contracts:
                E(f"contract {cid} requires unknown contract {r}")
                continue
            lr, lc = m.contract(r)["layer"], c["layer"]
            if lr == "P" or lc == "P":
                if lr == "P" and lc != "P":
                    E(f"code contract {cid} requires process contract {r}")
                continue
            if lr > lc:
                E(f"layering: {cid} (L{lc}) requires {r} (L{lr}) — upward dependency")
    req_edges = {cid: set(m.contract(cid)["requires"]) for cid in m.contracts}
    for comp in sccs(req_edges):
        E(f"contract build-dependency cycle: {' -> '.join(comp)}")
    for sid in m.skill_order:
        for cid in m.skill(sid)["provides"]:
            if cid not in m.contracts:
                E(f"skill {sid} provides unknown contract {cid}")
            elif m.contract(cid)["owner"] != sid:
                E(f"skill {sid} provides {cid} but contract owner is {m.contract(cid)['owner']}")
        for dep in m.skill(sid)["consumes"]:
            cid, _ = m.parse_dep(dep)
            if cid not in m.contracts:
                E(f"skill {sid} consumes unknown contract {cid}")
            elif cid in m.skill(sid)["provides"]:
                E(f"skill {sid} consumes its own contract {cid}")
    consumers = {cid: [] for cid in m.contracts}
    for sid in m.skill_order:
        for cid, _ in m.deps(sid, include_universal=True):
            if cid in consumers:
                consumers[cid].append(sid)
    for cid, users in consumers.items():
        if not users:
            W(f"contract {cid} has no consumers")

    # -- configuration closure (the scale-down proof)
    for name, tokens in m.configurations.items():
        members = [s for s in m.skill_order if m.in_configuration(s, tokens)]
        mset = set(members)
        for sid in members:
            for cid, opt in m.deps(sid, include_universal=True):
                if opt or cid not in m.contracts:
                    continue
                owner = m.contract(cid)["owner"]
                if owner not in mset:
                    E(f"configuration '{name}': {sid} requires {cid} but its owner {owner} is not in the configuration")
        I(f"configuration {name:28s} {len(members):3d} skills")

    # -- critics
    for k, c in m.critics.items():
        for sel in c["scope"]:
            if sel == "all" or sel.startswith("tier:"):
                continue
            target = sel[8:] if sel.startswith("subtree:") else sel
            if target not in m.skills:
                E(f"critic {k} scope selector '{sel}' names unknown skill")
        for st in c["stages"]:
            if st not in m.critic_doc["stages"]:
                E(f"critic {k} stage '{st}' unknown")
    for sid in m.skill_order:
        domain = [k for k in m.critics_for(sid, "G2")
                  if m.scope_matches([x for x in m.critics[k]["scope"] if x != "all"], sid)]
        if not domain:
            E(f"skill {sid} has no domain critic at stage G2")

    # -- cross-cutting & seed map
    for c in m.cross_doc["concerns"]:
        if c["owner"] not in m.skills:
            E(f"cross-cutting concern '{c['concern']}' owner '{c['owner']}' unknown")
    for section in ("brief_domains", "brief_hardware", "brief_targets"):
        for term, cids in m.seed_doc[section].items():
            if not cids:
                E(f"brief term '{term}' maps to no capability")
            for cid in cids:
                if cid not in m.caps:
                    E(f"brief term '{term}' maps to unknown capability {cid}")

    # -- informational: runtime coupling cycles (resolved by frame phases, must be declared)
    comps = sccs(m.skill_edges(include_universal=False, include_optional=False))
    for comp in comps:
        I(f"runtime coupling cycle (needs phase-mediated contract): {', '.join(comp)}")
    I(f"{len(m.caps)} capabilities, {len(m.skills)} skills, {len(m.contracts)} contracts, {len(m.critics)} critics")
    return errors, warnings, info


def selftest():
    """A guard never seen to fail is not known to be a guard: mutate and require red."""
    base = Model()
    e, _, _ = run(base)
    assert not e, f"selftest needs a green baseline, got: {e[:3]}"
    mutations = [
        ("orphan capability owner", lambda m: m.cap_doc["domains"][0]["areas"][0]["caps"][0].__setitem__(2, "nobody"), "is not a skill"),
        ("upward layering", lambda m: m.contract("C-PAL")["requires"].append("C-GAME"), "upward dependency"),
        ("closure break", lambda m: m.skill("physics-2d")["consumes"].append("C-RT"), "is not in the configuration"),
        ("unknown brief capability", lambda m: m.seed_doc["brief_domains"].__setitem__("x", ["NOPE.x"]), "unknown capability"),
        ("self non-responsibility", lambda m: m.skill("terrain")["non_responsibilities"].append(["x", "terrain"]), "points at itself"),
    ]
    ok = True
    for label, mutate, needle in mutations:
        m = Model()
        mutate(m)
        m.reindex()
        errs, _, _ = run(m)
        hit = any(needle in x for x in errs)
        print(f"  selftest {'RED ok ' if hit else 'MISSED'}: {label}")
        ok &= hit
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    errors, warnings, info = run(Model())
    for x in info:
        print("info:", x)
    for x in warnings:
        print("WARN:", x)
    for x in errors:
        print("ERROR:", x)
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
