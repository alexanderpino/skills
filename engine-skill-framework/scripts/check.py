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
  * every non-established capability is on the technology radar, and M/X/S radar entries have a fallback;
  * every code contract has a conformance suite; gated extension points (C-ML, C-MLGPU, C-RT, C-AIAGENT)
    are only ever consumed optionally;
  * every brief term maps to real capabilities;
  (round 2)
  * needs_implementer contracts are closed per platform; platform capabilities sit in skills tagged with that
    platform; console-only skills carry an NDA access class;
  * the module-level bootstrap graph is acyclic; skills without a module inherit their lead's layer as floor;
  * radar classes equal capability maturity and radar owners own or lead the capabilities they list;
    X/S capabilities are opt-in through the 'experimental' profile only;
  * capability ids quoted in capability names exist; legacy patterns name existing stance capabilities
    that their justification owner owns, contributes to or leads;
  * tool-side capabilities and world tools reach tool contracts (C-COOK/C-EDCMD/C-EDHOST/C-EDVIEW);
    user-facing runtime domains have an authoring path; UI.A11Y contributors reach C-A11YRT;
  * every code contract has an oracle author other than its sole implementer; boundary contracts declare a
    verified test double;
  * the untrusted-input registry: one validating owner, registered parsers, a fuzz target (or red-team corpus
    for agent inputs) and resource limits per input;
  * milestones: claimed configurations closed by then, every configuration claimed once, every code contract
    frozen once after its owner and a consumer and never before its requirements, gates exist;
  * independence pairs never share a workstream; code-writing skills have an S3 domain critic.

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
            provided = m.floor_layers(sid)
            anc = s["parent"]
            while not provided and anc:            # no module of its own: inherit the lead's layer as floor
                provided = m.code_layers_provided(anc)
                provided = [max(provided)] if provided else provided
                anc = m.skill(anc)["parent"]
            for dep in s["consumes"]:
                cid, _ = m.parse_dep(dep)
                mod = m.parse_for(dep)
                if mod is not None and mod not in s["provides"] + s.get("implements", []):
                    E(f"skill {sid} attributes {cid} to module {mod}, which it does not provide")
                    continue
                if cid not in m.contracts or m.layer(cid) == "P" or not provided:
                    continue
                floor = m.layer(mod) if mod else min(provided)
                if floor != "P" and m.layer(cid) > floor:
                    E(f"upward link: {sid} module L{floor} consumes {cid} (L{m.layer(cid)}); attribute it to a higher module with @")

    # -- foundation must be acyclic even counting universals (bootstrap proof)
    # (module granularity: a skill's higher module may depend on skills that depend on its lower module)
    mod_edges = m.module_edges()
    for comp in sccs(mod_edges):
        if len(comp) < 2 and comp[0] not in mod_edges.get(comp[0], ()):
            continue
        if any(mod != "_" and m.layer(mod) < 2 for _, mod in comp):
            E(f"foundation cycle (bootstrap impossible): {', '.join(sorted({f'{s}[{mod}]' for s, mod in comp}))}")
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

    # -- platform code sits in skills tagged with that platform; console-only skills carry an NDA access class
    for sid in m.skill_order:
        s = m.skill(sid)
        for c in m.owned_caps(sid):
            area = ".".join(c["id"].split(".")[:2])
            need = PLATFORM_AREAS.get(area)
            if need and need not in (s["platforms"] or []):
                E(f"skill {sid} owns platform capability {c['id']} but is not tagged platform '{need}'")
        if s["platforms"] == ["console"] and not str(s.get("access", "")).startswith("nda"):
            E(f"console-only skill {sid} has no NDA access class")
        if str(s.get("access", "")).startswith("nda") and s["platforms"] != ["console"]:
            E(f"NDA skill {sid} is not confined to the console platform")

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
        for p in platforms + cfg.get("target_platforms", []):
            if p not in PLATFORMS:
                E(f"configuration '{name}' platform '{p}' invalid")
        if cfg.get("target_platforms") and target != "tools":
            E(f"configuration '{name}': target_platforms only apply to tools configurations")
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
                if c.get("needs_implementer"):
                    for p in m.platform_set(name):
                        if c.get("platforms") and p not in c["platforms"]:
                            continue
                        if not any(cid in m.skill(x)["implements"] and (m.skill(x)["platforms"] is None
                                   or p in m.skill(x)["platforms"]) for x in members):
                            E(f"configuration '{name}': {cid} is required but no implementer for platform '{p}' "
                              f"is in the configuration")
        ncap = sum(1 for cid in m.caps if m.cap_in_configuration(cid, name))
        I(f"configuration {name:34s} {len(members):3d} build skills, {ncap:3d} capabilities")

    # -- milestones (walking-skeleton proof, configuration claims, contract freeze order)
    earlier, placed, claims, frozen_at, idx_of = set(), {}, {}, {}, {}
    for idx, ms in enumerate(m.milestone_doc["milestones"]):
        idx_of[ms["id"]] = idx
        sk = set(ms["skills"])
        for s_ in sk:
            if s_ not in m.skills:
                E(f"milestone {ms['id']} names unknown skill {s_}")
            placed.setdefault(s_, []).append(ms["id"])
        avail = sk | earlier
        for s_ in sk & set(m.skills):
            for cid, opt in m.deps(s_, include_universal=True):
                if opt or cid not in m.contracts or m.layer(cid) == "P":
                    continue
                if m.contract(cid)["owner"] not in avail:
                    E(f"milestone {ms['id']}: {s_} requires {cid} (owner {m.contract(cid)['owner']}) not built yet")
        for claim in ms.get("configurations", []):
            name, _, plats = claim.partition("@")
            if name not in m.configurations:
                E(f"milestone {ms['id']} claims unknown configuration {name}")
                continue
            cfg = m.configurations[name]
            saved = cfg.get("platforms", [])
            if plats:
                cfg["platforms"] = plats.split("+")
            try:
                missing = sorted(set(m.members(name)) - avail)
            finally:
                cfg["platforms"] = saved
            if missing:
                E(f"milestone {ms['id']} claims {claim} but {len(missing)} member skills are not built by then "
                  f"(e.g. {missing[0]})")
            if not plats:
                claims.setdefault(name, []).append(ms["id"])
        for cid in ms.get("contracts_frozen", []) + ms.get("contracts_draft", []):
            if cid not in m.contracts:
                E(f"milestone {ms['id']} names unknown contract {cid}")
        for cid in ms.get("contracts_frozen", []):
            if cid in frozen_at:
                E(f"contract {cid} frozen twice ({frozen_at[cid]} and {ms['id']})")
            frozen_at[cid] = ms["id"]
        for g in ms.get("gates", []):
            cap_, val_ = (g.get("capability"), g.get("validator")) if isinstance(g, dict) else (g, None)
            if cap_ not in m.caps:
                E(f"milestone {ms['id']} gate names unknown capability {cap_}")
                continue
            if not val_ or val_ not in m.caps:
                E(f"milestone {ms['id']} gate {cap_} has no valid validator capability")
                continue
            vo, go = m.cap(val_)["owner"], m.cap(cap_)["owner"]
            if vo == go:
                E(f"milestone {ms['id']} gate {cap_}: validator {val_} is owned by the gated owner {go}")
            if m.skill(vo).get("workstream") == "governance":
                E(f"milestone {ms['id']} gate {cap_}: validator {val_} sits in the milestone owner's workstream")
        earlier |= sk
    if m.milestone_doc["milestones"]:
        for sid in m.skill_order:
            if m.skill(sid).get("kind") in ("runtime", "tool"):
                n = len(placed.get(sid, []))
                if n != 1:
                    E(f"build skill {sid} appears in {n} milestones (expected exactly 1)")
        for name in m.configurations:
            if len(claims.get(name, [])) != 1:
                E(f"configuration {name} is claimed in full by {len(claims.get(name, []))} milestones (expected 1)")
        ms_of = {s_: idx_of[v[0]] for s_, v in placed.items() if len(v) == 1}
        for cid in m.contracts:
            if m.layer(cid) == "P":
                continue
            if cid not in frozen_at:
                E(f"code contract {cid} is never frozen by a milestone")
                continue
            f = idx_of[frozen_at[cid]]
            owner = m.contract(cid)["owner"]
            if owner in ms_of and ms_of[owner] > f:
                E(f"contract {cid} frozen at {frozen_at[cid]} before its owner {owner} is built")
            cons = [ms_of[x] for x in m.skill_order if x in ms_of and x != owner
                    and cid in {d for d, _ in m.deps(x, include_universal=True, include_tool=True)}]
            if cons and min(cons) > f:
                E(f"contract {cid} frozen at {frozen_at[cid]} before any consumer is built")
            impl_ms = [ms_of[x] for x in m.skill_order if x in ms_of and cid in m.skill(x).get("implements", [])]
            if m.contract(cid).get("needs_implementer") and impl_ms and max(impl_ms) > f:
                E(f"contract {cid} frozen at {frozen_at[cid]} before its last implementer is built")
            for tier, tms in (m.contract(cid).get("extension_tiers") or {}).items():
                if tms not in idx_of or idx_of[tms] < f:
                    E(f"contract {cid} extension tier '{tier}' names milestone {tms} that does not follow the core freeze")
            for r in m.contract(cid)["requires"]:
                if r in frozen_at and idx_of[frozen_at[r]] > f:
                    E(f"contract {cid} frozen at {frozen_at[cid]} before its requirement {r} ({frozen_at[r]})")

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

    for sid in m.skill_order:
        sk_ = m.skill(sid)
        if sk_.get("kind") in ("runtime", "tool") or sk_.get("writes_code"):
            domain = [k for k in m.critics_for(sid, "S3")
                      if m.scope_matches([x for x in m.critics[k]["scope"] if x != "all"], sid)]
            if not domain:
                E(f"code-writing skill {sid} has no domain critic at stage S3")

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
        if e.get("class") in ("M", "X", "S") and not e.get("non_goal") and not e.get("fallback"):
            E(f"radar entry '{e.get('tech')}' has no fallback")
    for cid in m.caps:
        if m.cap(cid)["maturity"] != "E" and cid not in radar_caps:
            E(f"non-established capability {cid} is not on the technology radar")

    # -- code contracts carry a conformance suite; gated (non-established) extension points stay optional
    for cid in m.contracts:
        c = m.contract(cid)
        if c["layer"] != "P" and not c.get("conformance"):
            E(f"code contract {cid} has no conformance suite")
    for sid in m.skill_order:
        for dep in m.skill(sid).get("consumes", []):
            base, optional = m.parse_dep(dep)
            if base in m.contracts and m.contract(base).get("gated") and not optional \
                    and m.contract(base)["owner"] != sid:
                E(f"skill {sid} requires gated contract {base}; gated extension points must be optional (C-X?)")
    for cid in m.contracts:
        for r in m.contract(cid).get("requires", []):
            if r in m.contracts and m.contract(r).get("gated") and not m.contract(cid).get("gated"):
                E(f"contract {cid} requires gated contract {r}")

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

    # -- radar entries agree with the capability map (class and owner lineage)
    def lineage(sid):
        out = []
        while sid:
            out.append(sid)
            sid = m.skill(sid)["parent"] if sid in m.skills else None
        return out
    for e in m.radar_doc["entries"]:
        for cid in e.get("capabilities", []):
            if cid not in m.caps:
                continue
            if m.cap(cid)["maturity"] != e.get("class"):
                E(f"radar entry '{e.get('tech')}' class {e.get('class')} but {cid} is {m.cap(cid)['maturity']}")
            if e.get("owner") and e["owner"] not in lineage(m.cap(cid)["owner"]):
                E(f"radar entry '{e.get('tech')}' owner {e['owner']} neither owns nor leads {cid}")

    # -- capability ids quoted inside names exist
    for cid in m.caps:
        for ref in CAP_REF.findall(m.cap(cid)["name"]):
            if ref not in m.caps:
                E(f"capability {cid} refers to unknown capability {ref}")

    # -- experimental (X/S) capabilities are opt-in only
    for cid in m.caps:
        c = m.cap(cid)
        if c["maturity"] in ("X", "S") and (c["profiles"] or []) != ["experimental"]:
            E(f"{c['maturity']} capability {cid} must carry exactly the 'experimental' profile")

    # -- legacy patterns link to the capabilities that carry their stance
    for p in m.legacy_doc["patterns"]:
        caps_ = p.get("stance_capabilities") or []
        if not caps_:
            E(f"legacy pattern {p['id']} has no stance capabilities")
        ok_owner = False
        for cid in caps_:
            if cid not in m.caps:
                E(f"legacy pattern {p['id']} names unknown stance capability {cid}")
                continue
            c = m.cap(cid)
            if p.get("justification_owner") in [c["owner"]] + c["contributors"] or \
                    p.get("justification_owner") in lineage(c["owner"]):
                ok_owner = True
        if caps_ and not ok_owner:
            E(f"legacy pattern {p['id']}: justification owner owns, contributes to or leads none of its stance caps")

    # -- tool-side territory reaches the editor/cook through tool contracts
    for cid in m.caps:
        c = m.cap(cid)
        if CONFIDENTIAL.search(c["name"]) and cid not in CONFIDENTIAL_EXEMPT and \
                not str(m.skill(c["owner"]).get("access", "")).startswith("nda") and \
                "via PLAT.CON.confidential-slots" not in c["name"] and "slot in PLAT.CON" not in c["name"]:
            E(f"capability {cid} names confidential console territory but its owner {c['owner']} has no NDA access")
        if TOOL_SIDE.search(c["name"]) and c["area"] != "CNT.COOK" and cid not in TOOL_SIDE_EXEMPT \
                and not c["area"].endswith(".TOOL"):
            s_ = m.skill(c["owner"])
            if s_.get("kind") == "runtime" and not s_.get("tool_consumes"):
                E(f"runtime skill {c['owner']} owns tool-side capability {cid} but consumes no tool contract")
        if c["area"] == "WLD.TOOL" and "C-EDVIEW" not in {m.parse_dep(d)[0] for d in
                                                         m.skill(c["owner"]).get("tool_consumes", [])} \
                and c["owner"] != "world-editor-viewport":
            E(f"{c['owner']} owns world tool {cid} but does not reach C-EDVIEW")

    # -- accessibility runtime path
    for cid in m.caps:
        c = m.cap(cid)
        if c["area"] == "UI.A11Y":
            for co in c["contributors"]:
                if co in m.skills and m.skill(co).get("kind") == "runtime" and \
                        min(m.floor_layers(co) or [2]) >= 2 and \
                        "C-A11YRT" not in {m.parse_dep(d)[0] for d in m.skill(co)["consumes"]} and \
                        "C-A11YRT" not in m.skill(co)["provides"]:
                    E(f"{co} contributes to {cid} but does not consume C-A11YRT")

    # -- authoring path: user-facing runtime domains own or contribute tool logic, or say why not
    for sid in m.skill_order:
        s_ = m.skill(sid)
        if s_.get("kind") != "runtime" or s_.get("workstream") not in AUTHORING_WORKSTREAMS or s_.get("authoring"):
            continue
        tool = [c for x in m.subtree(sid) for c in m.owned_caps(x) + m.contributed_caps(x)
                if c["area"].endswith(".TOOL")]
        if not tool:
            E(f"runtime skill {sid} has no authoring path (owns/contributes no *.TOOL capability, no 'authoring' note)")

    # -- oracle independence and verified test doubles
    for cid in m.contracts:
        c = m.contract(cid)
        if c["layer"] == "P":
            continue
        oa = c.get("oracle_author")
        if not oa or oa not in m.skills:
            E(f"code contract {cid} has no valid oracle_author")
        elif oa == c["owner"] and not any(cid in m.skill(x).get("implements", []) for x in m.skill_order):
            E(f"code contract {cid}: its sole implementer {oa} is also its oracle author")
        if oa in m.skills:
            if m.skill(oa).get("workstream") not in ("quality", "performance", "assurance"):
                E(f"code contract {cid}: oracle author {oa} is not in a quality/performance/assurance workstream")
            ws_ = {m.skill(c["owner"]).get("workstream")} | {m.skill(x).get("workstream") for x in m.skill_order
                                                              if cid in m.skill(x).get("implements", [])}
            if m.skill(oa).get("workstream") in ws_:
                E(f"code contract {cid}: oracle author {oa} shares a workstream with its owner or an implementer")
        if c.get("boundary"):
            td = c.get("test_double") or {}
            if not td.get("kind") or td.get("owner") not in m.skills:
                E(f"boundary contract {cid} declares no verified test double")

    # -- untrusted-input registry: one validating owner, parsers registered, fuzz or red-team coverage
    reg = {i["id"]: i for i in m.untrusted_doc["inputs"]}
    fuzz = set()
    for sid in m.skill_order:
        fuzz |= set(m.skill(sid).get("fuzz_targets") or [])
    for sid in m.skill_order:
        for u in m.skill(sid).get("untrusted_inputs") or []:
            if u not in reg:
                E(f"skill {sid} declares untrusted input '{u}' missing from the registry")
            elif sid != reg[u]["validating_owner"] and sid not in reg[u].get("parser_owners", []):
                E(f"skill {sid} declares untrusted input '{u}' but is neither its validating nor a parser owner")
    for u, i in reg.items():
        for sid in [i["validating_owner"]] + i.get("parser_owners", []):
            if sid not in m.skills:
                E(f"untrusted input '{u}' names unknown skill {sid}")
            elif u not in (m.skill(sid).get("untrusted_inputs") or []):
                E(f"untrusted input '{u}': {sid} does not register it")
        if i.get("mode") == "harness":
            if u not in fuzz:
                E(f"untrusted input '{u}' has no fuzz target")
            if i["validating_owner"] in m.skills and m.skill(i["validating_owner"]).get("kind") == "process":
                E(f"untrusted input '{u}' is validated by process skill {i['validating_owner']}")
            if not i.get("limits"):
                E(f"untrusted input '{u}' declares no resource limits")
        elif i.get("mode") == "redteam":
            if "XC.SEC.agent-redteam" not in m.caps:
                E(f"agent input '{u}' has no red-team capability")
        else:
            E(f"untrusted input '{u}' mode must be harness or redteam")
    for f_ in fuzz:
        if f_ not in reg:
            E(f"fuzz target '{f_}' is not a registered untrusted input")

    # -- independence matrix
    for a, b, why in m.cross_doc.get("independence", []):
        for x in (a, b):
            if x not in m.skills and x != "owning-skill":
                E(f"independence pair ({a}, {b}) names unknown skill {x}")
        if a in m.skills and b in m.skills and m.skill(a).get("workstream") == m.skill(b).get("workstream"):
            E(f"independence pair ({a}, {b}) shares workstream '{m.skill(a).get('workstream')}': staffing must not "
              f"co-host them")

    # -- organization tiers: workstreams partitioned into agents; independence holds per tier
    all_ws = {m.skill(x).get("workstream") for x in m.skill_order}
    for tname, tier in m.org_doc["tiers"].items():
        host = {}
        for agent, wss in tier["agents"].items():
            for w in wss:
                if w in host:
                    E(f"organization tier {tname}: workstream {w} hosted by {host[w]} and {agent}")
                host[w] = agent
        for w in all_ws - set(host):
            E(f"organization tier {tname}: workstream {w} is hosted by no agent")
        hs = lambda sid: host.get(m.skill(sid).get("workstream"))
        for a, b, why in m.cross_doc.get("independence", []):
            if a in m.skills and b in m.skills and hs(a) == hs(b):
                E(f"organization tier {tname}: independence pair ({a}, {b}) is hosted by one agent {hs(a)}")
        for cid in m.contracts:
            c_ = m.contract(cid)
            oa = c_.get("oracle_author")
            if c_["layer"] == "P" or oa not in m.skills:
                continue
            for x in [c_["owner"]] + [y for y in m.skill_order if cid in m.skill(y).get("implements", [])]:
                if hs(x) == hs(oa):
                    E(f"organization tier {tname}: oracle author {oa} of {cid} is hosted with {x}")
                    break

    counts = {}
    for cid in m.caps:
        counts[m.cap(cid)["maturity"]] = counts.get(m.cap(cid)["maturity"], 0) + 1
    I(f"{len(m.caps)} capabilities ({', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}), "
      f"{len(m.skills)} skills, {len(m.contracts)} contracts, {len(m.critics)} critics")
    return errors, warnings, info


CAP_REF = re.compile(r"\b(?:ARCH|PLAT|CORE|RES|CNT|WLD|RND|ML|PHY|ANM|AUD|INP|NET|GAM|UI|ED|BLD|QA|PRF|OBS|XC)"
                     r"\.[A-Z0-9]+\.[a-z0-9-]+[a-z0-9]\b")
TOOL_SIDE = re.compile(r"\bcook(ed|ing| step)?\b|\bbak(e|ed|ing)\b|\beditor\b|\bSDK\b.*tool|modder editor|"
                       r"authoring tool|generation orchestration", re.I)
# runtime capabilities whose wording matches TOOL_SIDE but which are runtime by design (each justified)
TOOL_SIDE_EXEMPT = {
    "ED.DEBUG.automation-protocol",   # runtime automation protocol ships in development builds on every target
}
CONFIDENTIAL = re.compile(r"confidential|console (API|SDK)", re.I)
CONFIDENTIAL_EXEMPT = {"PLAT.PAL.confidential-extensions"}   # the mechanism, owned by the public platform lead
AUTHORING_WORKSTREAMS = {"world", "simulation", "audio", "ui", "gameplay"}

PLATFORM_AREAS = {"PLAT.CON": "console", "PLAT.MOB": "mobile", "PLAT.WEB": "web", "PLAT.DESK": "pc",
                  "PLAT.SRV": "server-host"}


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
        ("milestone before its dependency", lambda m: [ms["skills"].remove("server-scaleout-persistence") for ms in m.milestone_doc["milestones"] if "server-scaleout-persistence" in ms["skills"]] and m.milestone_doc["milestones"][0]["skills"].append("server-scaleout-persistence"), "not built yet"),
        ("code contract without conformance", lambda m: m.contract("C-PAL").pop("conformance"), "no conformance suite"),
        ("gated contract required", lambda m: m.skill("global-illumination")["consumes"].append("C-RT"), "requires gated contract"),
        ("radar entry without fallback", lambda m: [e.pop("fallback", None) for e in m.radar_doc["entries"] if e["class"] == "X"], "has no fallback"),
        ("console skill tagged pc", lambda m: m.skill("platform-console").__setitem__("platforms", ["pc"]), "is not tagged platform"),
        ("per-platform implementer", lambda m: m.skill("rhi-webgpu").__setitem__("platforms", ["pc"]), "no implementer for platform 'web'"),
        ("radar class mismatch", lambda m: [e.__setitem__("class", "E") for e in m.radar_doc["entries"] if "RND.GRAPH.work-graphs" in e.get("capabilities", [])], "but RND.GRAPH.work-graphs is X"),
        ("dangling capability reference", lambda m: first_cap(m).__setitem__(1, first_cap(m)[1] + " (see RES.MGMT.nothing)"), "refers to unknown capability"),
        ("experimental capability in a shipping profile", lambda m: [c.__setitem__(5, ["aaa"]) for d in m.cap_doc["domains"] for a in d["areas"] for c in a["caps"] if c[0] == "RND.GRAPH.work-graphs"], "must carry exactly the 'experimental' profile"),
        ("legacy pattern without stance", lambda m: m.legacy_doc["patterns"][0].__setitem__("stance_capabilities", []), "has no stance capabilities"),
        ("untrusted input not fuzzed", lambda m: [s["fuzz_targets"].remove("packets") for s in m.skill_doc["skills"] if s.get("fuzz_targets")], "has no fuzz target"),
        ("implementer grades itself", lambda m: m.contract("C-NAV").__setitem__("oracle_author", "navigation-pathfinding"), "is also its oracle author"),
        ("milestone claim not closed", lambda m: m.milestone_doc["milestones"][1]["configurations"].append("standard-3d-client@pc"), "member skills are not built by then"),
        ("contract frozen before owner", lambda m: [ms["contracts_frozen"].remove("C-RT") or m.milestone_doc["milestones"][0]["contracts_frozen"].append("C-RT") for ms in m.milestone_doc["milestones"] if "C-RT" in ms["contracts_frozen"]], "before its owner"),
        ("authoring path missing", lambda m: [c.__setitem__(2, "gameplay-camera") for d in m.cap_doc["domains"] for a in d["areas"] for c in a["caps"] if c[0] == "GAM.TOOL.camera"] and None or m.skill("gameplay-camera").__setitem__("workstream", "gameplay") or [c.__setitem__(2, "gameplay-architect") for d in m.cap_doc["domains"] for a in d["areas"] for c in a["caps"] if c[0] == "GAM.TOOL.camera"], "has no authoring path"),
        ("tool-side cap without tool contract", lambda m: m.skill("ecs-runtime").__setitem__("tool_consumes", []), "owns tool-side capability CORE.ECS.baking"),
        ("public owner of confidential territory", lambda m: [c.__setitem__(1, "Async IO backends (console APIs)") for d in m.cap_doc["domains"] for a in d["areas"] for c in a["caps"] if c[0] == "RES.IO.backends"], "names confidential console territory"),
        ("oracle author shares owner workstream", lambda m: m.contract("C-RG").__setitem__("oracle_author", "shader-system"), "not in a quality/performance/assurance"),
        ("oracle author in owner workstream", lambda m: m.contract("C-PAL").__setitem__("oracle_author", "perf-benchmarking") or m.skill("rhi-core").__setitem__("workstream", "performance") or m.contract("C-RHI").__setitem__("oracle_author", "perf-benchmarking"), "shares a workstream"),
        ("gate validator owned by gated owner", lambda m: m.milestone_doc["milestones"][0]["gates"][0].__setitem__("validator", m.milestone_doc["milestones"][0]["gates"][0]["capability"]), "owned by the gated owner"),
        ("organization hosts a pair together", lambda m: m.org_doc["tiers"]["small"]["agents"]["build"].extend(m.org_doc["tiers"]["small"]["agents"].pop("verify")), "hosted with"),
        ("needs_implementer frozen before implementer", lambda m: [ms["contracts_frozen"].remove("C-PHYS") for ms in m.milestone_doc["milestones"] if "C-PHYS" in ms["contracts_frozen"]] and m.milestone_doc["milestones"][0]["contracts_frozen"].append("C-PHYS"), "before"),
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
