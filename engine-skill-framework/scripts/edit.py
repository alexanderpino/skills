"""Tiny editing API over data/*.json used by gauntlet revision scripts.

Every mutation is tagged with the finding IDs that motivated it, so each round's
revision script doubles as the change log (gauntlet/round-N/changes.md).
"""
import json
import os

from model import DATA

FILES = {"cap": "capabilities.json", "skill": "skills.json", "contract": "contracts.json",
         "critic": "critics.json", "cross": "crosscutting.json", "seed": "seed-map.json",
         "radar": "radar.json", "legacy": "legacy-patterns.json", "milestone": "milestones.json",
         "untrusted": "untrusted-inputs.json"}


class Editor:
    def __init__(self):
        self.doc = {}
        for k, f in FILES.items():
            p = os.path.join(DATA, f)
            self.doc[k] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
        self.log = []
        self.dispositions = {}

    # ---------------------------------------------------------------- bookkeeping
    def note(self, tags, text):
        self.log.append((tags, text))

    def dispose(self, fid, verdict, text):
        assert verdict in ("accept", "partial", "reject", "merge"), verdict
        self.dispositions[fid] = (verdict, text)

    def save(self):
        for k, f in FILES.items():
            if self.doc[k] is not None:
                with open(os.path.join(DATA, f), "w", encoding="utf-8") as fh:
                    json.dump(self.doc[k], fh, indent=1, ensure_ascii=False)
                    fh.write("\n")

    # ---------------------------------------------------------------- capabilities
    def _domain(self, did):
        for d in self.doc["cap"]["domains"]:
            if d["id"] == did:
                return d
        raise KeyError(did)

    def _area(self, aid):
        for d in self.doc["cap"]["domains"]:
            for a in d["areas"]:
                if a["id"] == aid:
                    return a
        raise KeyError(aid)

    def _find_cap(self, cid):
        for d in self.doc["cap"]["domains"]:
            for a in d["areas"]:
                for c in a["caps"]:
                    if c[0] == cid:
                        return a, c
        raise KeyError(cid)

    def domain(self, did, name, tags=""):
        try:
            self._domain(did)
        except KeyError:
            self.doc["cap"]["domains"].append({"id": did, "name": name, "areas": []})
            self.note(tags, f"new domain {did} {name}")

    def area(self, aid, name, tags=""):
        try:
            self._area(aid)
            return
        except KeyError:
            pass
        did = aid.split(".")[0]
        self._domain(did)["areas"].append({"id": aid, "name": name, "caps": []})
        self.note(tags, f"new area {aid} {name}")

    def cap(self, cid, name, owner, mat="E", contrib=None, profiles=None, tags=""):
        aid = cid.rsplit(".", 1)[0]
        a = self._area(aid)
        for c in a["caps"]:
            assert c[0] != cid, f"duplicate {cid}"
        row = [cid, name, owner, mat]
        if contrib or profiles:
            row.append(list(contrib or []))
        if profiles:
            row.append(list(profiles))
        a["caps"].append(row)
        self.note(tags, f"+cap {cid} '{name}' → {owner} [{mat}]")

    def cap_set(self, cid, name=None, owner=None, mat=None, add_contrib=None, rm_contrib=None,
                profiles=None, tags=""):
        _, c = self._find_cap(cid)
        while len(c) < 5:
            c.append([])
        changes = []
        if name is not None:
            c[1] = name
            changes.append(f"name='{name}'")
        if owner is not None:
            if owner in c[4]:
                c[4].remove(owner)
            if c[2] != owner and c[2] not in c[4]:
                pass
            changes.append(f"owner {c[2]}→{owner}")
            c[2] = owner
        if mat is not None:
            changes.append(f"maturity {c[3]}→{mat}")
            c[3] = mat
        for x in add_contrib or []:
            if x not in c[4] and x != c[2]:
                c[4].append(x)
                changes.append(f"+contrib {x}")
        for x in rm_contrib or []:
            if x in c[4]:
                c[4].remove(x)
                changes.append(f"-contrib {x}")
        if profiles is not None:
            while len(c) < 6:
                c.append([])
            c[5] = list(profiles)
            changes.append(f"profiles={profiles}")
        # normalise trailing empties
        if len(c) == 6 and not c[5]:
            c.pop()
        if len(c) == 5 and not c[4]:
            c.pop()
        self.note(tags, f"~cap {cid}: " + ", ".join(changes))

    def cap_move(self, cid, new_id, tags=""):
        a, c = self._find_cap(cid)
        a["caps"].remove(c)
        c[0] = new_id
        self._area(new_id.rsplit(".", 1)[0])["caps"].append(c)
        self.note(tags, f"moved cap {cid} → {new_id}")

    def cap_del(self, cid, tags=""):
        a, c = self._find_cap(cid)
        a["caps"].remove(c)
        self.note(tags, f"-cap {cid}")

    def caps_owned(self, owner):
        out = []
        for d in self.doc["cap"]["domains"]:
            for a in d["areas"]:
                for c in a["caps"]:
                    if c[2] == owner:
                        out.append(c[0])
        return out

    # ---------------------------------------------------------------- skills
    def skill(self, sid):
        for s in self.doc["skill"]["skills"]:
            if s["id"] == sid:
                return s
        raise KeyError(sid)

    def skill_add(self, tags="", **s):
        s.setdefault("consumes", [])
        s.setdefault("tool_consumes", [])
        s.setdefault("provides", [])
        s.setdefault("implements", [])
        s.setdefault("expertise", [])
        self.doc["skill"]["skills"].append(s)
        self.note(tags, f"+skill {s['id']} ({s['tier']}, parent {s['parent']})")

    def skill_set(self, sid, tags="", **kw):
        s = self.skill(sid)
        for k, v in kw.items():
            s[k] = v
        self.note(tags, f"~skill {sid}: " + ", ".join(kw))

    def rename_skill(self, old, new, tags=""):
        """Rename a skill id everywhere it is referenced."""
        raw = {k: json.dumps(v) for k, v in self.doc.items() if v is not None}
        for k, text in raw.items():
            text = text.replace(f'"{old}"', f'"{new}"').replace(f'subtree:{old}"', f'subtree:{new}"')
            self.doc[k] = json.loads(text)
        self.note(tags, f"renamed skill {old} → {new}")

    def use(self, sid, *deps, tool=False, tags=""):
        key = "tool_consumes" if tool else "consumes"
        s = self.skill(sid)
        s.setdefault(key, [])
        for d in deps:
            base = d.rstrip("?").split("@")[0]
            s[key] = [x for x in s[key] if x.rstrip("?").split("@")[0] != base]
            s[key].append(d)
        self.note(tags, f"{sid} {key} += {', '.join(deps)}")

    def unuse(self, sid, *cids, tags=""):
        s = self.skill(sid)
        for key in ("consumes", "tool_consumes"):
            s[key] = [x for x in s.get(key, []) if x.rstrip("?").split("@")[0] not in cids]
        self.note(tags, f"{sid} no longer consumes {', '.join(cids)}")

    def nonresp(self, sid, entries, tags=""):
        self.skill(sid)["non_responsibilities"] = entries
        self.note(tags, f"{sid} non-responsibilities rewritten")

    def nonresp_add(self, sid, what, owner, tags=""):
        self.skill(sid)["non_responsibilities"].append([what, owner])
        self.note(tags, f"{sid} non-responsibility += {what} → {owner}")

    # ---------------------------------------------------------------- contracts
    def contract(self, cid):
        for c in self.doc["contract"]["contracts"]:
            if c["id"] == cid:
                return c
        raise KeyError(cid)

    def contract_add(self, cid, layer, owner, name, summary, requires=(), tags="", **extra):
        c = {"id": cid, "layer": layer, "owner": owner, "name": name, "summary": summary,
             "requires": list(requires)}
        c.update(extra)
        self.doc["contract"]["contracts"].append(c)
        prov = self.skill(owner)["provides"]
        if cid not in prov:
            prov.append(cid)
        self.note(tags, f"+contract {cid} L{layer} ({owner}): {name}")

    def contract_set(self, cid, tags="", **kw):
        c = self.contract(cid)
        if "owner" in kw and kw["owner"] != c["owner"]:
            old = self.skill(c["owner"])
            old["provides"] = [x for x in old["provides"] if x != cid]
            self.skill(kw["owner"])["provides"].append(cid)
        c.update(kw)
        self.note(tags, f"~contract {cid}: " + ", ".join(kw))

    def contract_rename(self, old, new, tags=""):
        raw = {k: json.dumps(v) for k, v in self.doc.items() if v is not None}
        for k, text in raw.items():
            for q in ('"', '?"', '@'):
                pass
            text = text.replace(f'"{old}"', f'"{new}"').replace(f'"{old}?"', f'"{new}?"')
            text = text.replace(f'"{old}@', f'"{new}@').replace(f'@{old}"', f'@{new}"')
            self.doc[k] = json.loads(text)
        self.note(tags, f"renamed contract {old} → {new}")

    def contract_del(self, cid, tags=""):
        self.doc["contract"]["contracts"] = [c for c in self.doc["contract"]["contracts"] if c["id"] != cid]
        for s in self.doc["skill"]["skills"]:
            s["provides"] = [x for x in s["provides"] if x != cid]
            for key in ("consumes", "tool_consumes"):
                s[key] = [x for x in s.get(key, []) if x.rstrip("?").split("@")[0] != cid]
            s["implements"] = [x for x in s.get("implements", []) if x != cid]
        self.note(tags, f"-contract {cid}")
