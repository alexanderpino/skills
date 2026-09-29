#!/usr/bin/env python3
"""Validates the engine skill framework. Exit 1 on any error.

Machine-checks the structural parts of the definition of done:
  * every capability has exactly one existing owner; every skill owns territory;
  * contracts have one owner that provides them; build-level contract layering is
    acyclic and never points upward;
  * a skill never links upward: what a runtime module consumes sits at or below
    the lowest code layer it provides, and tool contracts (layer 5) are only
    consumed from the tool side;
  * the foundation tier (L0/L1 providers) is acyclic even counting the implicit
    universal contracts (the bootstrap proof);
  * every named configuration (scale profile x build target x platforms) is closed
    under its required dependencies, and contracts that need an implementer have one
    in the configuration: the scale-down proof;
  * every milestone is closed over its own and earlier milestones' skills: the
    walking-skeleton proof;
  * leads own a contract; non-responsibilities route to real owners;
  * every skill has a domain critic; tool-logic owners reach the editor via contracts;
    ML/neural capability owners reach the shared inference runtime via contracts;
  * every non-established capability is on the technology radar;
  * every brief term maps to real capabilities.

Usage: python3 scripts/check.py [--selftest] [--quiet]
"""
import re
import sys

from model import (KINDS, MATURITY, PLATFORMS, TARGETS, TIERS, TOOL_LAYER, Model, sccs)

MIN_CAPS_EXPERT = 3
MAX_CAPS_SKILL = 30
ML_NAME = re.compile(r"\bML\b|\bLLM\b|[Nn]eural|[Ll]earned")


def _owner_ok(m, owner):
    return owner in m.skills or owner.startswith("external:") or owner == "owning-skill"


def run(m):
    errors, warnings, info = [], [], []
    E, W, I = errors.append, warnings.append, info.append
    all_tokens = set(m.profiles_base) | set(m.profiles_addon)

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
        for p in c["profiles"] or []:
            if p not in all_tokens:
                E(f"capability {cid} profile token '{p}' unknown")

    # -- skills
    roots = [s for s in m.skill_order if m.skill(s)["parent"] is None]
    if len(roots) != 1:
        E(f"expected exactly one root skill, found {roots}")
    for sid in m.skill_order:
        s = m.skill(sid)
        if s["tier"] not in TIERS:
            E(f"skill {sid} tier '{s['tier']}' invalid")
        if s.get("kind") not in KINDS:
            E(f"skill {sid} kind '{s.get('kind')}' invalid (expected {KINDS})")
        for t in s["targets"]:
            if t not in TARGETS:
                E(f"skill {sid} target '{t}' invalid")
        if s.get("kind") == "process" and s["targets"]:
            E(f"process skill {sid} must not declare build targets")
        for p in s["platforms"] or []:
            if p not in PLATFORMS:
                E(f"skill {sid} platform '{p}' invalid")
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
        if not s["non_responsibilities"]:
            E(f"skill {sid} declares no non-responsibilities")
        for what, owner in s["non_responsibilities"]:
            owners = owner if isinstance(owner, list) else [owner]
            for o in owners:
                if not _owner_ok(m, o):
                    E(f"skill {sid} non-responsibility '{what}' points at unknown skill '{o}'")
                elif o == sid:
                    E(f"skill {sid} non-responsibility '{what}' points at itself")
        for tok in s["profiles"]:
            if tok != "all" and tok not in all_tokens:
                E(f"skill {sid} profile token '{tok}' unknown")
        if s["tier"] == "lead":
            if not s["provides"]:
                E(f"lead {sid} provides no contract (a lead that only coordinates)")
            kids = len(m.children(sid))
            if kids < 3 and not m.code_layers_provided(sid):
                W(f"lead {sid} has {kids} children and no code contract")
        for cid in s["implements"]:
            if cid not in m.contracts:
                E(f"skill {sid} implements unknown contract {cid}")

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
            lr, lc = m.layer(r), c["layer"]
            if lr == "P" or lc == "P":
                if lr == "P" and lc != "P":
                    E(f"code contract {cid} requires process contract {r}")
                continue
            if lr > lc:
                E(f"layering: {cid} (L{lc}) requires {r} (L{lr}) — upward dependency")
    for comp in sccs({cid: set(m.contract(cid)["requires"]) for cid in m.contracts}):
        E(f"contract build-dependency cycle: {' -> '.join(comp)}")

    # -- consumption: existence, own-contract, tool side, no upward links from a module
    for sid in m.skill_order:
        s = m.skill(sid)
        for cid in s["provides"]:
            if cid not in m.contracts:
                E(f"skill {sid} provides unknown contract {cid}")
            elif m.contract(cid)["owner"] != sid:
                E(f"skill {sid} provides {cid} but contract owner is {m.contract(cid)['owner']}")
        for side in ("consumes", "tool_consumes"):
            for dep in s[side]:
                cid, _ = m.parse_dep(dep)
                if cid not in m.contracts:
                    E(f"skill {sid} {side} unknown contract {cid}")
                elif cid in s["provides"]:
                    E(f"skill {sid} consumes its own contract {cid}")
        if s.get("kind") == "runtime":
            for dep in s["consumes"]:
                cid, _ = m.parse_dep(dep)
                if cid in m.contracts and m.layer(cid) != "P" and m.layer(cid) >= TOOL_LAYER:
                    E(f"runtime skill {sid} consumes tool contract {cid} from runtime code (move to tool_consumes)")
            provided = m.code_layers_provided(sid)
            for dep in s["consumes"]:
                cid, _ = m.parse_dep(dep)
                mod = m.parse_for(dep)
                if mod is not None and mod not in s["provides"]:
                    E(f"skill {sid} attributes {cid} to module {mod}, which it does not provide")
                    continue
                if cid not in m.contracts or m.layer(cid) == "P" or not provided:
                    continue
                floor = m.layer(mod) if mod else min(provided)
                if floor != "P" and m.layer(cid) > floor:
                    E(f"upward link: {sid} module L{floor} consumes {cid} (L{m.layer(cid)}); attribute it to a higher module with @")

    # -- foundation must be acyclic even counting universals (bootstrap proof)
    code_edges = m.skill_edges(include_universal=True, include_optional=True, code_only=True)
    foundation = {s for s in m.skill_order if m.code_layers_provided(s) and min(m.code_layers_provided(s)) < 2}
    for comp in sccs(code_edges):
        if foundation & set(comp):
            E(f"foundation cycle (bootstrap impossible): {', '.join(comp)}")
    for comp in sccs(m.skill_edges(include_universal=False, include_optional=False, code_only=True)):
        I(f"runtime coupling cycle (must be a declared channel, not a direct call): {', '.join(comp)}")

    consumers = {cid: [] for cid in m.contracts}
    for sid in m.skill_order:
        for cid, _ in m.deps(sid, include_universal=True, include_tool=True):
            if cid in consumers:
                consumers[cid].append(sid)
        for cid in m.skill(sid)["implements"]:
            if cid in consumers:
                consumers[cid].append(sid)
    for cid, users in consumers.items():
        if not users:
            W(f"contract {cid} has no consumers")

    # -- configuration closure (the scale-down proof)
    for name, cfg in m.configurations.items():
        profiles, target, platforms = cfg["profiles"], cfg["target"], cfg.get("platforms", [])
        if not any(p in m.profiles_base for p in profiles):
            E(f"configuration '{name}' has no base profile")
        for p in profiles:
            if p not in all_tokens:
                E(f"configuration '{name}' profile '{p}' unknown")
        if target not in TARGETS:
            E(f"configuration '{name}' target '{target}' invalid")
        for p in platforms:
            if p not in PLATFORMS:
                E(f"configuration '{name}' platform '{p}' invalid")
        members = m.members(name)
        mset = set(members)
        tool = target == "tools"
        for sid in members:
            for cid, opt in m.deps(sid, include_universal=True, include_tool=tool):
                if opt or cid not in m.contracts:
                    continue
                c = m.contract(cid)
                owner = c["owner"]
                if m.skill(owner).get("kind") == "process" or c["layer"] == "P":
                    continue
                if owner not in mset:
                    E(f"configuration '{name}': {sid} requires {cid} but its owner {owner} is not in the configuration")
                if c.get("needs_implementer") and not any(cid in m.skill(x)["implements"] for x in members):
                    E(f"configuration '{name}': {cid} is required but no implementer is in the configuration")
        ncap = sum(1 for cid in m.caps if m.cap_in_configuration(cid, name))
        I(f"configuration {name:34s} {len(members):3d} build skills, {ncap:3d} capabilities")

    # -- milestones (walking-skeleton proof)
    earlier = set()
    for ms in m.milestone_doc["milestones"]:
        sk = set(ms["skills"])
        for s in sk:
            if s not in m.skills:
                E(f"milestone {ms['id']} names unknown skill {s}")
        if ms.get("configuration") and ms["configuration"] not in m.configurations:
            E(f"milestone {ms['id']} names unknown configuration {ms['configuration']}")
        avail = sk | earlier
        for s in sk & set(m.skills):
            for cid, opt in m.deps(s, include_universal=True):
                if opt or cid not in m.contracts or m.layer(cid) == "P":
                    continue
                if m.contract(cid)["owner"] not in avail:
                    E(f"milestone {ms['id']}: {s} requires {cid} (owner {m.contract(cid)['owner']}) not built yet")
        for cid in ms.get("contracts_frozen", []) + ms.get("contracts_draft", []):
            if cid not in m.contracts:
                E(f"milestone {ms['id']} names unknown contract {cid}")
        earlier |= sk

    if m.milestone_doc["milestones"]:
        placed = {}
        for ms in m.milestone_doc["milestones"]:
            for s_ in ms["skills"]:
                placed.setdefault(s_, []).append(ms["id"])
        for sid in m.skill_order:
            if m.skill(sid).get("kind") in ("runtime", "tool"):
                n = len(placed.get(sid, []))
                if n != 1:
                    E(f"build skill {sid} appears in {n} milestones (expected exactly 1)")

    # -- critics
    for k, c in m.critics.items():
        for sel in c["scope"]:
            if sel == "all" or sel.startswith(("tier:", "kind:", "owns-area:")):
                continue
            target_ = sel[8:] if sel.startswith("subtree:") else sel
            if target_ not in m.skills:
                E(f"critic {k} scope selector '{sel}' names unknown skill")
        for st in c["stages"]:
            if st not in m.critic_doc["stages"]:
                E(f"critic {k} stage '{st}' unknown")
    for sid in m.skill_order:
        domain = [k for k in m.critics_for(sid, "G2")
                  if m.scope_matches([x for x in m.critics[k]["scope"] if x != "all"], sid)]
        if not domain:
            E(f"skill {sid} has no domain critic at stage G2")

    # -- authoring paths and ML paths go through contracts
    for sid in m.skill_order:
        s = m.skill(sid)
        reach = {m.parse_dep(d)[0] for d in s["consumes"] + s["tool_consumes"]} | set(s["provides"])
        tool_caps = [c["id"] for c in m.owned_caps(sid) if c["area"].endswith(".TOOL")]
        if tool_caps and not reach & {"C-EDCMD", "C-EDHOST"}:
            E(f"skill {sid} owns tool logic ({tool_caps[0]}…) but reaches the editor through no contract")
        if sid != "ml-inference-runtime" and s.get("kind") != "process":
            ml_caps = [c["id"] for c in m.owned_caps(sid)
                       if "ml-inference-runtime" in c["contributors"] or ML_NAME.search(c["name"])]
            if ml_caps and not reach & {"C-ML", "C-MLGPU"}:
                E(f"skill {sid} owns ML capability {ml_caps[0]} but consumes no inference contract")

    # -- technology radar: every non-established capability is tracked
    radar_caps = set()
    for e in m.radar_doc["entries"]:
        if e.get("class") not in MATURITY:
            E(f"radar entry '{e.get('tech')}' class invalid")
        if not e.get("capabilities") and not e.get("non_goal"):
            E(f"radar entry '{e.get('tech')}' neither maps to capabilities nor is a non-goal")
        for cid in e.get("capabilities", []):
            if cid not in m.caps:
                E(f"radar entry '{e.get('tech')}' names unknown capability {cid}")
            radar_caps.add(cid)
        if e.get("owner") and e["owner"] not in m.skills:
            E(f"radar entry '{e.get('tech')}' owner unknown")
        if e.get("class") in ("M", "X", "S") and not e.get("non_goal") and not e.get("revisit"):
            E(f"radar entry '{e.get('tech')}' has no revisit/promotion trigger")
    for cid in m.caps:
        if m.cap(cid)["maturity"] != "E" and cid not in radar_caps:
            E(f"non-established capability {cid} is not on the technology radar")

    # -- legacy pattern catalogue
    for p in m.legacy_doc["patterns"]:
        if p.get("justification_owner") not in m.skills:
            E(f"legacy pattern '{p.get('id')}' owner unknown")

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

    counts = {}
    for cid in m.caps:
        counts[m.cap(cid)["maturity"]] = counts.get(m.cap(cid)["maturity"], 0) + 1
    I(f"{len(m.caps)} capabilities ({', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}), "
      f"{len(m.skills)} skills, {len(m.contracts)} contracts, {len(m.critics)} critics")
    return errors, warnings, info


def selftest():
    """A guard never seen to fail is not known to be a guard: mutate and require red."""
    base = Model()
    e, _, _ = run(base)
    assert not e, f"selftest needs a green baseline, got: {e[:3]}"

    def first_cap(m):
        return m.cap_doc["domains"][0]["areas"][0]["caps"][0]

    mutations = [
        ("orphan capability owner", lambda m: first_cap(m).__setitem__(2, "nobody"), "is not a skill"),
        ("upward contract layering", lambda m: m.contract("C-PAL")["requires"].append("C-GAME"), "upward dependency"),
        ("configuration closure break", lambda m: m.skill("physics-2d")["consumes"].append("C-RT"), "is not in the configuration"),
        ("unknown brief capability", lambda m: m.seed_doc["brief_domains"].__setitem__("x", ["NOPE.x"]), "unknown capability"),
        ("self non-responsibility", lambda m: m.skill("terrain")["non_responsibilities"].append(["x", "terrain"]), "points at itself"),
        ("tool contract in runtime code", lambda m: m.skill("terrain")["consumes"].append("C-EDCMD"), "consumes tool contract"),
        ("upward module link", lambda m: m.skill("memory-allocators")["consumes"].append("C-GAME"), "upward link"),
        ("foundation cycle", lambda m: m.skill("platform-architect")["consumes"].append("C-MEM"), "foundation cycle"),
        ("capability off the radar", lambda m: first_cap(m).__setitem__(3, "X"), "not on the technology radar"),
        ("lead without contract", lambda m: m.skill("audio-architect").__setitem__("provides", []), "provides no contract"),
        ("ML owner without inference path", lambda m: m.skill("motion-synthesis").__setitem__("consumes", ["C-ANIM"]) or m.skill("motion-synthesis").__setitem__("tool_consumes", []), "consumes no inference contract"),
        ("milestone before its dependency", lambda m: m.milestone_doc["milestones"][0]["skills"].append("render-architect"), "not built yet"),
        ("missing implementer", lambda m: [m.skill(s)["implements"].remove("C-RHI") for s in m.skill_order if "C-RHI" in m.skill(s)["implements"]], "no implementer"),
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
    if "--quiet" not in sys.argv:
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
