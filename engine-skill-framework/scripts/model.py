"""Loads the framework data files into one in-memory model. Stdlib only.

Schema v1 (after G1 round 1): configurations are points in four independent axes:
  scale/feature profiles  (min2d | lite3d | std3d  + add-ons)
  build target            (client | headless-client | server | tools)
  platforms               (pc | console | mobile | web | xr-standalone | server-host)
Skills declare which of each axis they belong to; processes skills (governance,
testing, docs, ...) are organizational and outside build closure.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

MATURITY = {"E": "established", "M": "emerging", "X": "experimental", "S": "speculative"}
TIERS = ["orchestrator", "cross-cutting", "lead", "expert"]
KINDS = ["runtime", "tool", "process"]
TARGETS = ["client", "headless-client", "server", "tools"]
PLATFORMS = ["pc", "console", "mobile", "web", "xr-standalone", "server-host"]
# default build targets per kind
DEFAULT_TARGETS = {"runtime": ["client", "headless-client", "server", "tools"], "tool": ["tools"], "process": []}
TOOL_LAYER = 5


def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


class Model:
    def __init__(self):
        self.cap_doc = _load("capabilities.json")
        self.skill_doc = _load("skills.json")
        self.contract_doc = _load("contracts.json")
        self.critic_doc = _load("critics.json")
        self.cross_doc = _load("crosscutting.json")
        self.seed_doc = _load("seed-map.json")
        self.radar_doc = _load("radar.json") if os.path.exists(os.path.join(DATA, "radar.json")) else {"entries": []}
        self.legacy_doc = _load("legacy-patterns.json") if os.path.exists(os.path.join(DATA, "legacy-patterns.json")) else {"patterns": []}
        self.milestone_doc = _load("milestones.json") if os.path.exists(os.path.join(DATA, "milestones.json")) else {"milestones": []}
        self.untrusted_doc = _load("untrusted-inputs.json") if os.path.exists(os.path.join(DATA, "untrusted-inputs.json")) else {"inputs": []}
        self.reindex()

    def reindex(self):
        """Rebuild lookup tables from the loaded documents (call after mutating a doc)."""
        self.domains = self.cap_doc["domains"]
        self.caps = {}
        self.cap_order = []
        for d in self.domains:
            for a in d["areas"]:
                for c in a["caps"]:
                    cid, name, owner, mat = c[0], c[1], c[2], c[3]
                    contrib = c[4] if len(c) > 4 else []
                    prof = c[5] if len(c) > 5 else None
                    self.caps.setdefault(cid, []).append(
                        {"id": cid, "name": name, "owner": owner, "maturity": mat,
                         "contributors": contrib, "profiles": prof, "domain": d["id"], "area": a["id"]})
                    self.cap_order.append(cid)

        self.skills = {}
        self.skill_order = []
        for s in self.skill_doc["skills"]:
            s.setdefault("tool_consumes", [])
            s.setdefault("implements", [])
            s.setdefault("platforms", None)
            if "targets" not in s:
                s["targets"] = list(DEFAULT_TARGETS.get(s.get("kind", "process"), []))
            self.skills.setdefault(s["id"], []).append(s)
            self.skill_order.append(s["id"])

        self.contracts = {}
        for c in self.contract_doc["contracts"]:
            self.contracts.setdefault(c["id"], []).append(c)

        self.critics = {c["id"]: c for c in self.critic_doc["critics"]}
        self.profiles_base = self.skill_doc["profiles"]["base"]
        self.profiles_addon = self.skill_doc["profiles"]["addons"]
        self.configurations = self.skill_doc["configurations"]

    # ---- accessors (first definition wins; duplicates are reported by check.py)
    def skill(self, sid):
        return self.skills[sid][0]

    def contract(self, cid):
        return self.contracts[cid][0]

    def cap(self, cid):
        return self.caps[cid][0]

    def owned_caps(self, sid):
        return [self.cap(c) for c in self.cap_order if self.cap(c)["owner"] == sid]

    def contributed_caps(self, sid):
        return [self.cap(c) for c in self.cap_order if sid in self.cap(c)["contributors"]]

    def children(self, sid):
        return [s for s in self.skill_order if self.skill(s)["parent"] == sid]

    def subtree(self, sid):
        out = [sid]
        for ch in self.children(sid):
            out.extend(self.subtree(ch))
        return out

    @staticmethod
    def parse_dep(dep):
        """'C-X', 'C-X?' (optional), 'C-X@C-Y' (consumed by the module that provides C-Y)."""
        base = dep.split("@")[0]
        return (base[:-1], True) if base.endswith("?") else (base, False)

    @staticmethod
    def parse_for(dep):
        return dep.split("@")[1].rstrip("?") if "@" in dep else None

    def layer(self, cid):
        return self.contract(cid)["layer"]

    def code_layers_provided(self, sid):
        return [self.layer(c) for c in self.skill(sid)["provides"]
                if c in self.contracts and self.layer(c) != "P" and self.layer(c) < TOOL_LAYER]

    def code_layers_implemented(self, sid):
        return [self.layer(c) for c in self.skill(sid).get("implements", [])
                if c in self.contracts and self.layer(c) != "P" and self.layer(c) < TOOL_LAYER]

    def floor_layers(self, sid):
        """Module layers that unattributed dependencies are checked against: provided contracts, or for a pure
        implementer (a backend) the contracts it implements."""
        return self.code_layers_provided(sid) or self.code_layers_implemented(sid)

    def universals_for(self, sid):
        """Universal contracts apply to 'all' skills, and 'runtime' universals to runtime/tool code skills
        that sit at layer >= 2 (or provide no code contract). Foundation skills (L0/L1 providers) list their
        dependencies explicitly, which is what keeps the bootstrap tier acyclic."""
        s = self.skill(sid)
        provided = self.floor_layers(sid)
        foundation = bool(provided) and min(provided) < 2
        out = []
        for cid in self.contracts:
            u = self.contract(cid).get("universal")
            if cid in s["provides"]:
                continue
            if u == "all":
                out.append(cid)
            elif u == "runtime" and s.get("kind") in ("runtime", "tool") and not foundation:
                out.append(cid)
        return out

    def deps(self, sid, include_universal=False, include_tool=False):
        """[(contract_id, optional)] consumed (+ universals, + tool-side if asked)."""
        s = self.skill(sid)
        out = [self.parse_dep(d) for d in s["consumes"]]
        if include_tool:
            out += [self.parse_dep(d) for d in s["tool_consumes"]]
        if include_universal:
            have = {c for c, _ in out}
            out += [(u, False) for u in self.universals_for(sid) if u not in have]
        return out

    def skill_edges(self, include_universal=False, include_optional=True, include_tool=False, code_only=False):
        """skill -> set(skill) via consumed contracts' owners."""
        edges = {s: set() for s in self.skill_order}
        for s in self.skill_order:
            for cid, opt in self.deps(s, include_universal, include_tool):
                if opt and not include_optional:
                    continue
                if cid not in self.contracts:
                    continue
                if code_only and self.layer(cid) == "P":
                    continue
                o = self.contract(cid)["owner"]
                if o != s:
                    edges[s].add(o)
        return edges

    def base_module(self, sid):
        """The module that unattributed dependencies belong to: the lowest-layer code contract a skill provides."""
        s = self.skill(sid)
        pool = s["provides"] if self.code_layers_provided(sid) else s.get("implements", [])
        code = [c for c in pool if c in self.contracts and self.layer(c) != "P" and self.layer(c) < TOOL_LAYER]
        return min(code, key=self.layer) if code else "_"

    def module_edges(self, include_optional=True):
        """(skill, module) -> set((skill, module)) over code contracts, counting universals.
        Unattributed deps belong to the base module; 'C-X@C-Y' belongs to module C-Y, which also depends on its
        own skill's base module. This is the granularity at which bootstrap order is real."""
        edges = {}
        for s in self.skill_order:
            base = self.base_module(s)
            edges.setdefault((s, base), set())
            for c in self.skill(s)["provides"] + self.skill(s).get("implements", []):
                if c in self.contracts and self.layer(c) != "P" and self.layer(c) < TOOL_LAYER and c != base:
                    edges.setdefault((s, c), set()).add((s, base))
            raw = list(self.skill(s)["consumes"]) + [u for u in self.universals_for(s)
                                                      if u not in {self.parse_dep(d)[0] for d in self.skill(s)["consumes"]}]
            for dep in raw:
                cid, opt = self.parse_dep(dep)
                if (opt and not include_optional) or cid not in self.contracts or self.layer(cid) == "P":
                    continue
                if self.layer(cid) >= TOOL_LAYER:
                    continue
                mod = self.parse_for(dep) or base
                o = self.contract(cid)["owner"]
                if o == s:
                    continue
                target = (o, cid if cid != self.base_module(o) else self.base_module(o))
                edges.setdefault((s, mod), set()).add(target)
                edges.setdefault(target, set())
        return edges

    # ---- configurations
    def config(self, name):
        c = self.configurations[name]
        return c["profiles"], c["target"], c.get("platforms", [])

    def profile_match(self, sid, profiles):
        prof = self.skill(sid)["profiles"]
        return "all" in prof or any(p in profiles for p in prof)

    def in_configuration(self, sid, name):
        """Build membership. Process skills are organizational and never part of a build."""
        s = self.skill(sid)
        if s.get("kind") == "process":
            return False
        profiles, target, platforms = self.config(name)
        if not self.profile_match(sid, profiles):
            return False
        if target not in s["targets"]:
            return False
        if s["platforms"] is not None and not any(p in self.platform_set(name) for p in s["platforms"]):
            return False
        return True

    def platform_set(self, name):
        """Platforms a configuration builds for; a tools configuration also covers the platforms it targets
        (cook, package, deploy), which pulls in platform skills' tool-side modules."""
        c = self.configurations[name]
        return list(dict.fromkeys(c.get("platforms", []) + c.get("target_platforms", [])))

    def members(self, name):
        return [s for s in self.skill_order if self.in_configuration(s, name)]

    def cap_in_configuration(self, cid, name):
        cap = self.cap(cid)
        if cap["owner"] not in self.skills or not self.in_configuration(cap["owner"], name):
            return False
        if cap["profiles"]:
            profiles, _, _ = self.config(name)
            return any(p in profiles for p in cap["profiles"])
        return True

    # ---- critics
    def critics_for(self, sid, stage=None):
        out = []
        for k, c in self.critics.items():
            if stage and stage not in c["stages"]:
                continue
            if self.scope_matches(c["scope"], sid):
                out.append(k)
        return out

    def scope_matches(self, scope, sid):
        s = self.skill(sid)
        for sel in scope:
            if sel == "all":
                return True
            if sel.startswith("tier:") and s["tier"] == sel[5:]:
                return True
            if sel.startswith("kind:") and s.get("kind") == sel[5:]:
                return True
            if sel.startswith("subtree:") and sid in self.subtree(sel[8:]):
                return True
            if sel.startswith("owns-area:"):
                suffix = sel[len("owns-area:"):]
                if any(c["area"].endswith("." + suffix) for c in self.owned_caps(sid)):
                    return True
            if sel == sid:
                return True
        return False

    def domain_lead(self, sid):
        """Nearest ancestor (or self) whose parent is the root; the domain grouping for views."""
        cur = sid
        while True:
            p = self.skill(cur)["parent"]
            if p is None:
                return cur
            if self.skill(p)["parent"] is None:
                return cur
            cur = p


def sccs(edges):
    """Tarjan's strongly connected components; returns components with size > 1."""
    import sys
    sys.setrecursionlimit(10000)
    index, low, stack, on, out, counter = {}, {}, [], set(), [], [0]

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in sorted(edges.get(v, ())):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    for v in sorted(edges):
        if v not in index:
            strong(v)
    return out
