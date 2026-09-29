"""Loads the framework data files into one in-memory model. Stdlib only."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

MATURITY = {"E": "established", "M": "emerging", "X": "experimental", "S": "speculative"}
TIERS = ["orchestrator", "cross-cutting", "lead", "expert"]


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
                    self.caps.setdefault(cid, []).append(
                        {"id": cid, "name": name, "owner": owner, "maturity": mat,
                         "contributors": contrib, "domain": d["id"], "area": a["id"]})
                    self.cap_order.append(cid)

        self.skills = {}
        self.skill_order = []
        for s in self.skill_doc["skills"]:
            self.skills.setdefault(s["id"], []).append(s)
            self.skill_order.append(s["id"])

        self.contracts = {}
        for c in self.contract_doc["contracts"]:
            self.contracts.setdefault(c["id"], []).append(c)

        self.critics = {c["id"]: c for c in self.critic_doc["critics"]}
        self.profiles_base = self.skill_doc["profiles"]["base"]
        self.profiles_addon = self.skill_doc["profiles"]["addons"]
        self.configurations = self.skill_doc["configurations"]

    # ---- convenience accessors (first definition wins; duplicates are reported by check.py)
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
        return (dep[:-1], True) if dep.endswith("?") else (dep, False)

    def universals_for(self, sid):
        s = self.skill(sid)
        out = []
        for cid in self.contracts:
            u = self.contract(cid).get("universal")
            if u == "all" or (u == "runtime" and s.get("runtime")):
                if cid not in s["provides"]:
                    out.append(cid)
        return out

    def deps(self, sid, include_universal=False):
        """[(contract_id, optional)] explicitly consumed (+ universals if asked)."""
        s = self.skill(sid)
        out = [self.parse_dep(d) for d in s["consumes"]]
        if include_universal:
            have = {c for c, _ in out}
            out += [(u, False) for u in self.universals_for(sid) if u not in have]
        return out

    def skill_edges(self, include_universal=False, include_optional=True):
        """skill -> set(skill) via consumed contracts' owners."""
        edges = {s: set() for s in self.skill_order}
        for s in self.skill_order:
            for cid, opt in self.deps(s, include_universal):
                if opt and not include_optional:
                    continue
                if cid in self.contracts:
                    o = self.contract(cid)["owner"]
                    if o != s:
                        edges[s].add(o)
        return edges

    def in_configuration(self, sid, config_tokens):
        prof = self.skill(sid)["profiles"]
        if "all" in prof:
            return True
        if "client" in prof and "server" not in config_tokens:
            return True
        return any(p in config_tokens for p in prof)

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
            if sel.startswith("subtree:") and sid in self.subtree(sel[8:]):
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
    index = {}
    low = {}
    stack = []
    on = set()
    out = []
    counter = [0]

    import sys
    sys.setrecursionlimit(10000)

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
