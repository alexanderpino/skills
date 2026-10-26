"""
arch_export.py — hand an architecture change over to an implementation workflow.

The skill's artifacts follow international standards (ISO/IEC/IEEE 42010 and 29148,
ISO/IEC 25010 quality scenarios, RFC 2119 drivers, Nygård/MADR decisions, TOGAF
principles). Implementation tools want the same facts in their own shape. This module
builds ONE source model from the standards-based documents and renders it for:

  openspec  → openspec/changes/<id>/  (proposal.md, design.md, specs/<cap>/spec.md, tasks.md)
  speckit   → specs/NNN-<id>/         (spec.md, plan.md, research.md, contracts/, checklists/, tasks.md)
  constitution → .specify/memory/constitution.md from the enterprise principles (PR.xx)

Everything written is a SEED derived from evidence already on record, never an
invention: where the record is silent the output says so, in the target's own marker
(`[NEEDS CLARIFICATION: …]` for spec-kit, a `<!-- principal-architect: … -->` note
for OpenSpec). The target tool's own validator remains the gate.

Mapping (source → target), kept here so it can be audited:

  change.md Intent + B.xx          → proposal Why · spec-kit Summary
  ADR Decision / alternatives      → proposal What Changes · design Decisions · research.md
  ADR Context / Consequences       → design Context / Risks · plan Complexity Tracking
  EP in/out scope                  → design Goals / Non-Goals
  F.xx (RFC 2119)                  → spec Requirement (SHALL/MUST) · FR-NNN
  US-NNN Gherkin acceptance        → #### Scenario: WHEN/THEN/AND · spec-kit Acceptance Scenarios (Given/When/Then kept)
  Q.xx 6-part scenario             → spec Requirement with its response measure · SC-NNN
  C.xx constraints                 → plan Technical Context
  realizes-capabilities / affects  → OpenSpec capability path
  SD api-spec:                     → contracts/
  PR.xx (TOGAF principles)         → Constitution Check · constitution.md
  ARCH-REF: ADR-NNNN               → a verification task in both task lists
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil

TODAY = datetime.date.today().isoformat()
PRIORITY_RANK = {"must": 1, "should": 2, "could": 3, "p1": 1, "p2": 2, "p3": 3,
                 "high": 1, "medium": 2, "low": 3, "critical": 1}
NEGATIVE = re.compile(r"\b(error|fail|invalid|reject|expired|impossible|never|denied|missing|"
                      r"unauthori[sz]ed|forbidden|not |cannot|without|exceed|limit)\b", re.I)


def _s(v):
    return "" if v is None else str(v).strip()


# ---------------------------------------------------------------- parsing helpers
def _lines_of_section(body, *keywords):
    """Text of the first level-2 section whose heading contains any keyword."""
    cur, buf, hit = None, [], False
    for line in body.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m and not line.startswith("###"):
            if hit:
                break
            cur = m.group(1).lower()
            hit = any(k in cur for k in keywords)
            continue
        if hit:
            buf.append(line)
    return "\n".join(buf)


def _sub_section(text, *keywords):
    """Text under a bold or level-3 sub-heading containing any keyword."""
    cur, buf, hit = None, [], False
    for line in text.splitlines():
        m = re.match(r"^(?:###\s+(.*?)|\*\*(.*?)\*\*)\s*$", line)
        if m:
            if hit:
                break
            cur = (m.group(1) or m.group(2) or "").lower()
            hit = any(k in cur for k in keywords)
            continue
        if hit:
            buf.append(line)
    return "\n".join(buf)


def _bullets(text):
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(.*\S)\s*$", line)
        if m and not m.group(1).startswith("<"):
            out.append(m.group(1))
    return out


def _paragraphs(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()
            and not p.strip().startswith(("|", "```", ">"))]


def _first_sentence(text):
    text = " ".join(text.split())
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return m.group(1) if m else text


def _clip(text, n):
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def _kebab(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _ids(text, prefix):
    return sorted(set(re.findall(r"\b" + prefix + r"\.\d{2}\b", text)))


def _outcome_sentence(text):
    """An epic Outcome is written '**So that** <benefit>'; turn it into a sentence."""
    text = re.sub(r"^\*\*so that\*\*\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"^so that\s+", "", text, flags=re.I)
    return text[:1].upper() + text[1:] if text else text


# ---------------------------------------------------------------- source model
class Source:
    """Reads the standards-based artifacts of one change into a plain dict."""

    def __init__(self, arch, ctx, state):
        self.arch, self.ctx, self.state = arch, ctx, state
        self.repo, self.root = ctx["repo"], ctx["root"]
        self.notes = []  # what could not be derived, for the report and the seeds

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    # -- documents --
    def _docs_of_kind(self, kinds):
        out = []
        for path in self.arch.walk_md(self.root):
            fm, body = self.arch.frontmatter(path)
            if self.arch.LINT.doc_kind(path, fm) in kinds:
                out.append((path, fm, body))
        return out

    def change(self):
        cpath = os.path.join(self.repo, self.state["path"], "change.md")
        fm, body = self.arch.frontmatter(cpath)
        secs = self.arch.sections(body)
        clean = lambda k: re.sub(r"<!--.*?-->", "", secs.get(k, ""), flags=re.S).strip()
        return {
            "id": self.state["change"], "title": _s(fm.get("title")), "path": self.state["path"],
            "level": _s(fm.get("level")), "archetype": _s(fm.get("archetype")),
            "affects": self.arch.as_list(fm.get("affects")), "base": _s(fm.get("base")) or None,
            "intent": clean("intent"), "evidence": clean("evidence"),
            "decisions": clean("decisions on record"), "triage": clean("triage"),
            "assumptions": [a for a in _bullets(clean("assumptions and gaps"))] or
                           ([] if clean("assumptions and gaps").lower().startswith("none") else
                            _paragraphs(clean("assumptions and gaps"))),
        }

    def records(self):
        adrs, rfcs = [], []
        for r in self.state["records"]:
            if not r.get("path"):
                continue
            path = os.path.join(self.repo, r["path"])
            fm, body = self.arch.frontmatter(path)
            secs = self.arch.sections(body)
            cons = secs.get("consequences", "")
            alts = []
            for b in _bullets(secs.get("decision", "")):
                m = re.match(r"(.+?)\s+[—-]+\s+(?:rejected|not chosen|declined)[,:]?\s*(?:because\s+)?(.*)", b, re.I)
                if m:
                    alts.append((m.group(1).strip(), m.group(2).strip()))
            rec = {
                "id": r["id"], "kind": r["kind"], "status": r.get("status"), "path": r["path"],
                "title": _s(fm.get("title")), "level": _s(fm.get("level")),
                "satisfies": self.arch.as_list(fm.get("satisfies")),
                "complies_with": self.arch.as_list(fm.get("complies-with")),
                "affects": self.arch.as_list(fm.get("affects")),
                "supersedes": _s(fm.get("supersedes")) or None,
                "context": _paragraphs(secs.get("context", "")),
                "decision": [p for p in _paragraphs(secs.get("decision", ""))
                             if not re.match(r"^- ", p)],
                "decision_bullets": _bullets(secs.get("decision", "")),
                "alternatives": alts,
                "positive": _bullets(_sub_section(cons, "positive")),
                "negative": _bullets(_sub_section(cons, "negative", "cost", "risk")),
                "tradeoffs": _bullets(_sub_section(cons, "trade-off", "tradeoff")),
                "consequences": _paragraphs(cons),
                "confirmation": _paragraphs(secs.get("confirmation", "")),
                "summary": _paragraphs(secs.get("summary", "")) + _paragraphs(secs.get("proposal", "")),
            }
            (adrs if rec["kind"] == "ADR" else rfcs).append(rec)
        return adrs, rfcs

    def prd(self, text=None):
        """Drivers from the PRD: F/B/C as id→text, Q as id→6-part scenario."""
        if text is None:
            found = self._docs_of_kind({"PRD"})
            if not found:
                self.note("no PRD found; functional and quality drivers could not be derived")
                return {"F": {}, "B": {}, "C": {}, "Q": {}, "path": None}
            path, _, body = found[0]
            text, prd_path = body, self.arch.rel(path, self.repo)
        else:
            prd_path = None
        out = {"F": {}, "B": {}, "C": {}, "Q": {}, "path": prd_path}
        for m in re.finditer(r"^\s*[-*]\s+\*\*([FBC])\.(\d{2}):?\*\*:?\s*(.+?)\s*$", text, re.M):
            out[m.group(1)][f"{m.group(1)}.{m.group(2)}"] = re.sub(r"\*\*", "", m.group(3))
        for m in re.finditer(r"^###\s+(Q\.\d{2})\s*[—–-]+\s*(.+?)\s*$", text, re.M):
            qid, name = m.group(1), m.group(2)
            block = text[m.end():]
            nxt = re.search(r"^##", block, re.M)
            block = block[:nxt.start()] if nxt else block
            parts = {}
            for row in re.finditer(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*$", block, re.M):
                key = row.group(1).lower()
                for k, label in (("characteristic", "characteristic"), ("source", "source"),
                                 ("stimulus", "stimulus"), ("environment", "environment"),
                                 ("artifact", "artifact"), ("response measure", "measure"),
                                 ("response", "response"), ("verification", "verification")):
                    if k in key and label not in parts:
                        parts[label] = row.group(2)
                        break
            out["Q"][qid] = dict(parts, name=name)
        return out

    def prd_delta(self, base):
        """F.xx ids added / changed / removed against the base branch's PRD."""
        found = self._docs_of_kind({"PRD"})
        if not found or not base:
            return {"added": [], "modified": [], "removed": [], "resolved": False}
        path = found[0][0]
        old = self.arch.git(self.repo, "show", f"{base}:{self.arch.rel(path, self.repo)}")
        if old is None:
            return {"added": [], "modified": [], "removed": [], "resolved": False}
        new_f = self.prd(found[0][2])["F"]
        old_f = self.prd(self.arch.split_frontmatter(old)[1])["F"]
        return {"added": sorted(set(new_f) - set(old_f)),
                "modified": sorted(k for k in new_f if k in old_f and new_f[k] != old_f[k]),
                "removed": sorted(set(old_f) - set(new_f)), "resolved": True}

    def stories(self):
        out = []
        for path, fm, body in self._docs_of_kind({"US"}):
            secs = self.arch.sections(body)
            story = secs.get("story", "")
            role = re.search(r"\*\*As an?\*\*\s*(.+)", story)
            want = re.search(r"\*\*I want\*\*\s*(.+)", story)
            so = re.search(r"\*\*so that\*\*\s*(.+?)\.?\s*$", story, re.I | re.M)
            ac = secs.get("acceptance criteria", "")
            scenarios, checklist = [], []
            fence = re.search(r"```(?:gherkin)?\s*\n(.*?)```", ac, re.S)
            if fence:
                cur = None
                for line in fence.group(1).splitlines():
                    m = re.match(r"^\s*(Scenario(?: Outline)?):\s*(.+?)\s*$", line)
                    if m:
                        cur = {"name": m.group(2), "given": [], "when": [], "then": [], "last": None}
                        scenarios.append(cur)
                        continue
                    m = re.match(r"^\s*(Given|When|Then|And|But)\s+(.+?)\s*$", line)
                    if m and cur:
                        kw, txt = m.group(1).lower(), m.group(2)
                        if kw in ("and", "but"):
                            kw = cur["last"] or "then"
                        cur[kw].append(txt)
                        cur["last"] = kw
                for s in scenarios:
                    s.pop("last", None)
            else:
                checklist = _bullets(ac)
            pri = _s(fm.get("priority")).lower()
            out.append({
                "id": _s(fm.get("id")), "title": _s(fm.get("title")), "path": self.arch.rel(path, self.repo),
                "role": role.group(1).strip() if role else "", "want": want.group(1).strip() if want else "",
                "so_that": so.group(1).strip() if so else "", "priority": pri,
                "rank": PRIORITY_RANK.get(pri, 2), "epic": _s(fm.get("epic")),
                "satisfies": self.arch.as_list(fm.get("satisfies")),
                "capabilities": self.arch.as_list(fm.get("realizes-capabilities")),
                "scenarios": scenarios, "checklist": checklist,
                "context": _paragraphs(secs.get("context / notes", "") or secs.get("context", "")),
            })
        return out

    def epics(self):
        out = {}
        for path, fm, body in self._docs_of_kind({"EP"}):
            secs = self.arch.sections(body)
            scope = secs.get("scope", "")
            inn = re.search(r"\*\*In scope:?\*\*:?\s*(.+)", scope)
            outs = re.search(r"\*\*Out of scope:?\*\*:?\s*(.+)", scope)
            out[_s(fm.get("id"))] = {
                "id": _s(fm.get("id")), "title": _s(fm.get("title")),
                "outcome": _outcome_sentence(" ".join(_paragraphs(secs.get("outcome", "")))),
                "in_scope": inn.group(1).strip() if inn else "", "out_scope": outs.group(1).strip() if outs else "",
                "acceptance": _bullets(next((v for k, v in secs.items() if "acceptance" in k), "")),
                "capabilities": self.arch.as_list(fm.get("realizes-capabilities")),
                "satisfies": self.arch.as_list(fm.get("satisfies")),
            }
        return out

    def contracts(self, affects):
        out = []
        for path, fm, _ in self._docs_of_kind({"SD"}):
            spec = _s(fm.get("api-spec"))
            if not spec:
                continue
            sd_affects = set(self.arch.as_list(fm.get("affects"))) | {_s(fm.get("id")).replace("SD-", "")}
            if not affects or sd_affects & set(affects):
                cand = os.path.normpath(os.path.join(os.path.dirname(path), spec))
                if not os.path.exists(cand):
                    cand = os.path.join(self.repo, spec)
                if os.path.exists(cand):
                    out.append(self.arch.rel(cand, self.repo))
        return out

    def principles(self):
        out = []
        for path, fm, body in self._docs_of_kind({"EA", "ENTERPRISE-ARCHITECTURE"}):
            for row in re.finditer(r"^\|\s*(PR\.\d{2})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", body, re.M):
                if row.group(2).startswith("<"):
                    continue
                out.append({"id": row.group(1), "name": row.group(2), "statement": row.group(3),
                            "rationale": row.group(4), "path": self.arch.rel(path, self.repo)})
        return out

    def hld_tech(self):
        """Best-effort technology facts from the HLD for spec-kit's Technical Context."""
        for path, fm, body in self._docs_of_kind({"HLD"}):
            tech = _lines_of_section(body, "technology", "constraints", "deployment")
            return [b for b in _bullets(tech)][:8]
        return []

    def _build(self):
        ch = self.change()
        adrs, rfcs = self.records()
        prd = self.prd()
        base = ch["base"] if ch["base"] and ch["base"] != "none" else self.arch.default_base(self.repo)
        delta = self.prd_delta(base)
        all_stories, epics = self.stories(), self.epics()
        # the drivers this change is about: named by its records or its intent/triage
        f_ids = set()
        for r in adrs + rfcs:
            f_ids |= {x for x in r["satisfies"] if x.startswith("F.")}
        for text in (ch["intent"], ch["triage"], ch["decisions"]):
            f_ids |= set(_ids(text, "F"))
        f_ids |= set(delta["added"]) | set(delta["modified"])
        q_ids = set()
        for r in adrs + rfcs:
            q_ids |= {x for x in r["satisfies"] if x.startswith("Q.")}
        for text in (ch["intent"], ch["triage"], ch["decisions"]):
            q_ids |= set(_ids(text, "Q"))
        stories = [s for s in all_stories if set(s["satisfies"]) & f_ids or s["id"] in ch["intent"]]
        for s in stories:
            f_ids |= set(x for x in s["satisfies"] if x.startswith("F."))
        f_ids = {f for f in sorted(f_ids) if f in prd["F"]} | {f for f in f_ids if f in delta["removed"]}
        missing_f = [f for f in sorted(f_ids) if f not in prd["F"] and f not in delta["removed"]]
        for f in missing_f:
            self.note(f"{f} is referenced but not defined in the PRD")
        if not f_ids and not q_ids:
            self.note("no F.xx or Q.xx driver is tied to this change (records' satisfies:, Intent, "
                      "or a story); the behaviour contract could not be derived")
        caps = []
        for s in stories:
            caps += s["capabilities"]
        for e in epics.values():
            if any(s["epic"] == e["id"] for s in stories):
                caps += e["capabilities"]
        caps = list(dict.fromkeys(_kebab(re.sub(r"^CAP-", "", c)) for c in caps if c))
        capability = caps[0] if caps else (_kebab(ch["affects"][0]) if ch["affects"] else _kebab(ch["id"]))
        if not caps:
            self.note(f"no realizes-capabilities on the stories or epic; capability path "
                      f"'{capability}' is taken from affects: and must be confirmed")
        story_epics = [epics[s["epic"]] for s in stories if s["epic"] in epics]
        epic = story_epics[0] if story_epics else None
        return {
            "change": ch, "adrs": adrs, "rfcs": rfcs, "base": base,
            "F": {f: prd["F"][f] for f in sorted(f_ids) if f in prd["F"]},
            "Q": {q: prd["Q"][q] for q in sorted(q_ids) if q in prd["Q"]},
            "B": prd["B"], "C": prd["C"], "prd_path": prd["path"], "delta": delta,
            "stories": sorted(stories, key=lambda s: (s["rank"], s["id"])),
            "epic": epic, "capability": capability, "capabilities": caps,
            "contracts": self.contracts(ch["affects"]), "principles": self.principles(),
            "hld_tech": self.hld_tech(), "notes": self.notes, "repo": self.repo,
        }

    def build(self):
        model = self._build()
        model["fingerprint"] = fingerprint(model)
        return model


# ---------------------------------------------------------------- fingerprint
RECORD_KEYS = ("id", "title", "satisfies", "complies_with", "affects", "supersedes", "context",
               "decision", "decision_bullets", "alternatives", "positive", "negative", "tradeoffs",
               "consequences", "confirmation", "summary")
CHANGE_KEYS = ("id", "title", "level", "archetype", "affects", "intent", "evidence", "decisions",
               "triage", "assumptions")
STORY_KEYS = ("id", "title", "role", "want", "so_that", "priority", "satisfies", "scenarios", "checklist")


def fingerprint(model):
    """A short hash of everything the seed is derived from — so a later `verify` can tell
    whether the architecture record moved on after the hand-over. Record *status* and
    file paths are left out on purpose: accepting an ADR or archiving the change is not
    drift, and neither is a link rewritten by the archive move."""
    facts = {
        "change": {k: model["change"][k] for k in CHANGE_KEYS},
        "records": [{k: r[k] for k in RECORD_KEYS} for r in model["adrs"] + model["rfcs"]],
        "F": model["F"], "Q": model["Q"], "C": model["C"],
        "stories": [{k: s[k] for k in STORY_KEYS} for s in model["stories"]],
        "epic": model["epic"], "capability": model["capability"],
        "principles": [(p["id"], p["statement"]) for p in model["principles"]],
        "contracts": [],
    }
    for c in model["contracts"]:
        try:
            with open(os.path.join(model["repo"], c), "rb") as fh:
                facts["contracts"].append((c, hashlib.sha256(fh.read()).hexdigest()[:12]))
        except OSError:
            facts["contracts"].append((c, None))
    dumped = json.dumps(facts, sort_keys=True, default=str)
    dumped = re.sub(r"\]\([^)]*\)", "]()", dumped)  # markdown link targets move with the folder
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- shared rendering
def _provenance(model, cmd):
    ids = ", ".join(r["id"] for r in model["adrs"] + model["rfcs"]) or "no decision records"
    return (f"<!-- Seeded by principal-architect from {model['change']['path']} ({ids}); "
            f"record fingerprint {model['fingerprint']}. Facts come from the architecture record; "
            f"markers show what it does not say. Regenerate with: {cmd} -->\n")


def _req_name(model, fid):
    for s in model["stories"]:
        if fid in s["satisfies"]:
            return s["title"]
    text = re.sub(r"^(The system|Users?|The \w+)\s+(MUST|SHALL|SHOULD|MAY)\s+(NOT\s+)?", "", model["F"][fid]).rstrip(".")
    words = text.split()
    return _clip(" ".join(words[:7]), 60).rstrip("…,")


def _normative(text):
    if re.search(r"\b(SHALL|MUST)\b", text):
        return text
    return re.sub(r"\b(should|may|will|can)\b", "SHALL", text, count=1, flags=re.I)


def _gherkin_to_openspec(sc):
    lines = []
    first_when = (sc["given"] + sc["when"])
    if first_when:
        lines.append(f"- **WHEN** {first_when[0]}")
        for extra in first_when[1:]:
            lines.append(f"- **AND** {extra}")
    then = sc["then"] or ["the expected outcome holds [NEEDS CLARIFICATION: no Then step in the source]"]
    lines.append(f"- **THEN** {then[0]}")
    for extra in then[1:]:
        lines.append(f"- **AND** {extra}")
    return "\n".join(lines)


def _q_scenario(q):
    who = q.get("source", "the environment")
    stim = q.get("stimulus", "the stimulus arrives")
    env = q.get("environment")
    resp = q.get("response", "the required response occurs")
    meas = q.get("measure", "")
    when = f"{who} {stim}" + (f" ({env})" if env else "")
    then = resp + (f"; measured as: {meas}" if meas else "")
    return when, then


def _trace(fid):
    return f" *(trace: {fid})*"


# ---------------------------------------------------------------- OpenSpec
def render_openspec(model, cmd, existing_specs):
    ch, adrs, rfcs = model["change"], model["adrs"], model["rfcs"]
    recs = adrs + rfcs
    files = {}
    prov = _provenance(model, cmd)

    # proposal.md
    why = [ch["intent"]] if ch["intent"] else []
    for bid, text in model["B"].items():
        if bid in ch["intent"] or any(bid in r["satisfies"] for r in recs):
            why.append(f"Business driver {bid}: {text}")
    what = []
    for r in recs:
        for p in r["decision"]:
            what.append(f"{p} ({r['id']})")
        if r["supersedes"]:
            what.append(f"**BREAKING**: supersedes {r['supersedes']}")
    if ch["archetype"] == "published-interface":
        what.append("**BREAKING**: this change alters a published interface (archetype published-interface)")
    for fid in model["delta"]["removed"]:
        what.append(f"**BREAKING**: removes {fid}")
    if not what:
        what.append(f"<!-- principal-architect: no decision text on record; state the change here -->")
    cap = model["capability"]
    cap_exists = cap in existing_specs
    new_caps = [] if cap_exists else [cap]
    mod_caps = [cap] if cap_exists else []
    impact = [f"Components: {', '.join(ch['affects'])}"] if ch["affects"] else []
    for c in model["contracts"]:
        impact.append(f"Contract: `{c}`")
    for r in recs:
        if r["negative"]:
            impact.append(f"{r['id']} consequences: " + "; ".join(r["negative"]))
    files["proposal.md"] = prov + "# Proposal\n\n## Why\n\n" + "\n\n".join(why or [
        "<!-- principal-architect: change.md has no Intent; state the problem and why now -->"]) + \
        "\n\n## What Changes\n\n" + "\n".join(f"- {w}" for w in what) + \
        "\n\n## Capabilities\n\n### New Capabilities\n" + \
        ("\n".join(f"- `{c}`: {_capability_blurb(model)}" for c in new_caps) or
         "<!-- none: the capability already exists -->") + \
        "\n\n### Modified Capabilities\n" + \
        ("\n".join(f"- `{c}`: requirements change for {', '.join(model['F']) or 'this change'}" for c in mod_caps) or
         "<!-- none: this change introduces the capability -->") + \
        (f"\n\n<!-- principal-architect: capability path '{cap}' was derived "
         f"({'from realizes-capabilities' if model['capabilities'] else 'from affects:, unconfirmed'}); "
         f"run `openspec list --specs` and reuse an existing path if one fits -->") + \
        "\n\n## Impact\n\n" + ("\n".join(f"- {i}" for i in impact) or
                                "<!-- principal-architect: nothing on record under affects:/api-spec -->") + "\n"

    # design.md
    ctx = []
    for r in recs:
        ctx += [f"{p} ({r['id']})" for p in r["context"]]
    if ch["evidence"]:
        ctx.append("Evidence: " + " ".join(ch["evidence"].split()))
    goals, nongoals = [], []
    if model["epic"]:
        if model["epic"]["in_scope"]:
            goals.append(model["epic"]["in_scope"] + f" ({model['epic']['id']})")
        if model["epic"]["out_scope"]:
            nongoals.append(model["epic"]["out_scope"] + f" ({model['epic']['id']})")
    decisions = []
    for r in recs:
        dec = " ".join(r["decision"]) or r["title"]
        block = f"### {r['id']}: {r['title']}\n\n{dec}"
        if r["alternatives"]:
            block += "\n\n**Alternatives considered:**\n" + "\n".join(
                f"- {a} — rejected because {b}" for a, b in r["alternatives"])
        if r["positive"]:
            block += "\n\n**Why:** " + "; ".join(r["positive"])
        decisions.append(block)
    risks = []
    for r in recs:
        for n in r["negative"]:
            risks.append(f"[{n}] → <!-- principal-architect: mitigation not on record in {r['id']} -->")
        for t in r["tradeoffs"]:
            risks.append(f"[trade-off: {t}] → accepted in {r['id']}")
        if not r["negative"] and not r["tradeoffs"]:
            # a Nygård ADR without MADR sub-headings: its Consequences prose is the record
            for p in r["consequences"]:
                risks.append(f"[{p}] → consequence accepted in {r['id']}")
    open_q = [f"{a}" for a in ch["assumptions"]]
    files["design.md"] = prov + "# Design\n\n## Context\n\n" + ("\n\n".join(ctx) or
        "See proposal.md — Why.") + "\n\n## Goals / Non-Goals\n\n**Goals:**\n" + \
        ("\n".join(f"- {g}" for g in goals) or f"- Deliver {', '.join(model['F']) or ch['title']}") + \
        "\n\n**Non-Goals:**\n" + ("\n".join(f"- {g}" for g in nongoals) or "- <!-- principal-architect: no out-of-scope on record -->") + \
        "\n\n## Decisions\n\n" + ("\n\n".join(decisions) or "<!-- principal-architect: no decision record in this change -->") + \
        "\n\n## Risks / Trade-offs\n\n" + ("\n".join(f"- {x}" for x in risks) or "- <!-- principal-architect: no consequences on record -->") + \
        ("\n\n## Open Questions\n\n" + "\n".join(f"- {q}" for q in open_q) if open_q else "") + "\n"

    # specs/<cap>/spec.md
    reqs = []
    story_by_f = {}
    for s in model["stories"]:
        for f in s["satisfies"]:
            story_by_f.setdefault(f, []).append(s)
    for fid, text in model["F"].items():
        name = _req_name(model, fid)
        desc = _clip(_normative(text), 480) + _trace(fid)
        scen = []
        for s in story_by_f.get(fid, []):
            for sc in s["scenarios"]:
                scen.append(f"#### Scenario: {sc['name']}\n{_gherkin_to_openspec(sc)}")
            for i, item in enumerate(s["checklist"], 1):
                scen.append(f"#### Scenario: {s['id']} criterion {i}\n- **WHEN** the condition in {s['id']} is exercised\n- **THEN** {item}")
        if not scen:
            scen.append(f"#### Scenario: {name}\n- **WHEN** <!-- principal-architect: no user story with acceptance criteria satisfies {fid}; write the scenario -->\n- **THEN** {_clip(text, 200)}")
        reqs.append((fid, f"### Requirement: {name}\n{desc}\n\n" + "\n\n".join(scen)))
    for qid, q in model["Q"].items():
        when, then = _q_scenario(q)
        char = q.get("characteristic", "")
        desc = f"The {q.get('artifact', 'system')} SHALL {q.get('response', 'meet ' + q['name'])}" + \
               (f" (ISO 25010: {char})" if char else "") + "."
        if q.get("measure"):
            desc += f" Response measure: {q['measure']}."
        scen = f"#### Scenario: {q['name']}\n- **WHEN** {when}\n- **THEN** {then}"
        if q.get("verification"):
            scen += f"\n- **AND** verified by: {q['verification']}"
        reqs.append((qid, f"### Requirement: {q['name']}\n{_clip(desc, 480)}{_trace(qid)}\n\n{scen}"))
    added = [b for fid, b in reqs if fid not in model["delta"]["modified"] or not cap_exists]
    modified = [b for fid, b in reqs if fid in model["delta"]["modified"] and cap_exists]
    spec = prov + "# Spec Delta\n\n"
    if not cap_exists:
        spec += f"## Purpose\n\n{_capability_blurb(model)}\n\n"
    if added:
        spec += "## ADDED Requirements\n\n" + "\n\n".join(added) + "\n\n"
    if modified:
        spec += "## MODIFIED Requirements\n\n<!-- principal-architect: MODIFIED must carry the full existing block; compare with openspec/specs/" + cap + "/spec.md before archiving -->\n\n" + "\n\n".join(modified) + "\n\n"
    if model["delta"]["removed"]:
        spec += "## REMOVED Requirements\n\n" + "\n\n".join(
            f"### Requirement: {fid}\n**Reason**: removed from the PRD in this change (see {', '.join(r['id'] for r in recs) or 'change.md'})\n**Migration**: <!-- principal-architect: not on record -->"
            for fid in model["delta"]["removed"]) + "\n\n"
    if not reqs and not model["delta"]["removed"]:
        spec += ("## ADDED Requirements\n\n<!-- principal-architect: no driver tied to this change. Either add "
                 "satisfies: [F.xx] to the record, or set skip_specs: true in .openspec.yaml if behaviour does not change -->\n\n")
    files[f"specs/{cap}/spec.md"] = spec.rstrip() + "\n"

    # tasks.md
    groups, n = [], 1
    if model["contracts"]:
        groups.append((f"{n}. Contracts", [f"Update `{c}` to the interface in design.md and verify the contract tests pass" for c in model["contracts"]])); n += 1
    for s in model["stories"] or [None]:
        if s is None:
            groups.append((f"{n}. {cap}", [f"Implement {fid}: {_clip(text, 90)} and verify its scenario in specs/{cap}/spec.md" for fid, text in model["F"].items()] or
                           ["<!-- principal-architect: no story or driver on record --> Implement the change and verify its scenario"]))
        else:
            items = [f"Implement {s['id']} {s['title']} and verify scenario \"{sc['name']}\" passes" for sc in s["scenarios"]] or \
                    [f"Implement {s['id']} {s['title']} and verify its acceptance criteria"]
            groups.append((f"{n}. {s['id']} — {s['title']}", items))
        n += 1
    q_items = [f"Verify {qid} by {q.get('verification') or 'its means of verification'} ({q.get('measure') or q['name']})" for qid, q in model["Q"].items()]
    ref_items = [f"Mark the site that enacts {r['id']} with `ARCH-REF: {r['id']}` in {', '.join(ch['affects']) or 'the code'} and verify `arch.py verify --change {ch['id']}` reports breadcrumbs passed" for r in adrs]
    if q_items or ref_items:
        groups.append((f"{n}. Verification and traceability", q_items + ref_items))
    tasks = prov + "# Tasks\n\n"
    t = 1
    for title, items in groups:
        tasks += f"## {title}\n\n"
        for i, item in enumerate(items, 1):
            tasks += f"- [ ] {title.split('.')[0]}.{i} {item}\n"
        tasks += "\n"
    tasks += ("## Workflow follow-up\n\n- Archive this change with `openspec archive` once reviewed; then "
              f"`arch.py archive --change {ch['id']}` accepts {', '.join(r['id'] for r in adrs) or 'the records'} on the architecture side.\n")
    files["tasks.md"] = tasks
    files[".openspec.yaml"] = f"schema: spec-driven\ncreated: {TODAY}\n# principal-architect: {ch['path']} — {', '.join(r['id'] for r in recs) or 'no records'}\n"
    return files


def _capability_blurb(model):
    if model["epic"] and model["epic"]["outcome"]:
        return _clip(_outcome_sentence(model["epic"]["outcome"]), 240)
    if model["change"]["intent"]:
        return _clip(_first_sentence(model["change"]["intent"]), 240)
    return "Covers " + (", ".join(model["F"]) or model["change"]["title"]) + "."


# ---------------------------------------------------------------- spec-kit
def render_speckit(model, cmd, feature_dir):
    ch, adrs, rfcs = model["change"], model["adrs"], model["rfcs"]
    recs = adrs + rfcs
    files = {}
    prov = _provenance(model, cmd)
    branch = os.path.basename(feature_dir)
    clar = []

    def need(text):
        if len(clar) < 3:
            clar.append(text)
            return f"[NEEDS CLARIFICATION: {text}]"
        return f"<!-- principal-architect: {text} -->"

    # spec.md
    stories = model["stories"]
    us = []
    for i, s in enumerate(stories, 1):
        p = min(s["rank"], 3)
        journey = f"As {('an ' if s['role'][:1].lower() in 'aeiou' else 'a ') if s['role'] else ''}{s['role'] or 'user'}, I want {s['want'] or s['title'].lower()}" + \
                  (f" so that {s['so_that']}." if s["so_that"] else ".")
        why = (f"Backlog priority '{s['priority']}' on {s['id']}" if s["priority"] else f"No priority recorded on {s['id']}") + \
              f"; delivers {', '.join(s['satisfies']) or 'no driver on record'}."
        first = s["scenarios"][0]["name"] if s["scenarios"] else None
        indep = (f"Can be fully tested by running scenario \"{first}\"" +
                 (f"; the value delivered: {s['so_that']}." if s["so_that"] else ".")) if first else need(f"independent test for {s['id']}")
        acc = []
        for sc in s["scenarios"]:
            g = " and ".join(sc["given"]) or "the system is in its normal state"
            w = " and ".join(sc["when"]) or "the action is taken"
            t = " and ".join(sc["then"]) or "the expected outcome holds"
            acc.append(f"**Given** {g}, **When** {w}, **Then** {t}")
        for item in s["checklist"]:
            acc.append(f"**Given** the context of {s['id']}, **When** the behaviour is exercised, **Then** {item}")
        if not acc:
            acc.append(need(f"acceptance scenarios for {s['id']}"))
        us.append(f"### User Story {i} - {s['title']} (Priority: P{p})\n\n{journey}\n\n**Why this priority**: {why}\n\n"
                  f"**Independent Test**: {indep}\n\n**Acceptance Scenarios**:\n\n" +
                  "\n".join(f"{k}. {a}" for k, a in enumerate(acc, 1)) + "\n\n---")
    if not us:
        us.append("### User Story 1 - " + ch["title"] + " (Priority: P1)\n\n" + (ch["intent"] or need("user journey")) +
                  "\n\n**Why this priority**: the only story in this change.\n\n**Independent Test**: " + need("independent test") +
                  "\n\n**Acceptance Scenarios**:\n\n1. " + need("acceptance scenarios: no US-NNN satisfies this change's drivers") + "\n\n---")
    edges = []
    for s in stories:
        for sc in s["scenarios"][1:]:
            if NEGATIVE.search(sc["name"]) or NEGATIVE.search(" ".join(sc["then"])):
                edges.append(f"{sc['name']}: " + " and ".join(sc["then"]))
    for r in recs:
        edges += [f"{n} ({r['id']})" for n in r["negative"]]
    frs = []
    for i, (fid, text) in enumerate(model["F"].items(), 1):
        frs.append(f"- **FR-{i:03d}**: {_normative(text)}{_trace(fid)}")
    if not frs:
        frs.append("- **FR-001**: " + need("functional requirements: no F.xx tied to this change"))
    scs = []
    i = 0
    for qid, q in model["Q"].items():
        i += 1
        scs.append(f"- **SC-{i:03d}**: {q.get('measure') or q.get('response') or q['name']}{_trace(qid)}")
    if model["epic"]:
        for a in model["epic"]["acceptance"]:
            i += 1
            scs.append(f"- **SC-{i:03d}**: {a} *(trace: {model['epic']['id']})*")
    if not scs:
        scs.append("- **SC-001**: " + need("measurable outcome: no Q.xx or epic acceptance on record"))
    assumptions = [f"- {a}" for a in ch["assumptions"]] or ["- None recorded in change.md."]
    files["spec.md"] = prov + f"# Feature Specification: {ch['title']}\n\n**Feature Branch**: `{branch}`\n\n**Created**: {TODAY}\n\n**Status**: Draft\n\n" \
        f"**Input**: Architecture change `{ch['id']}` ({ch['path']}); decisions {', '.join(r['id'] for r in recs) or 'none'}\n\n" \
        "## User Scenarios & Testing *(mandatory)*\n\n" + "\n\n".join(us) + "\n\n### Edge Cases\n\n" + \
        ("\n".join(f"- {e}" for e in edges) or "- " + need("edge cases: none derivable from the scenarios or consequences")) + \
        "\n\n## Requirements *(mandatory)*\n\n### Functional Requirements\n\n" + "\n".join(frs) + \
        "\n\n## Success Criteria *(mandatory)*\n\n### Measurable Outcomes\n\n" + "\n".join(scs) + \
        "\n\n## Assumptions\n\n" + "\n".join(assumptions) + "\n"

    # research.md (Phase 0): decisions with rationale and alternatives — the ADRs, verbatim in shape
    research = prov + f"# Research: {ch['title']}\n\n"
    for r in recs:
        research += f"## {r['id']}: {r['title']}\n\n- **Decision**: {' '.join(r['decision']) or r['title']}\n" \
                    f"- **Rationale**: {' '.join(r['context']) or need('rationale for ' + r['id'])}\n" \
                    f"- **Alternatives considered**: " + ("; ".join(f"{a} (rejected: {b})" for a, b in r["alternatives"]) or "none recorded in " + r["id"]) + "\n\n"
    if not recs:
        research += "No decision record in this change; see change.md Decisions on record.\n"
    files["research.md"] = research

    # plan.md
    tech = {"Language/Version": None, "Primary Dependencies": None, "Storage": None, "Testing": None,
            "Target Platform": None, "Project Type": None, "Performance Goals": None, "Constraints": None, "Scale/Scope": None}
    perf = [f"{q.get('measure')} ({qid})" for qid, q in model["Q"].items() if q.get("measure") and "performance" in q.get("characteristic", "").lower()]
    if perf:
        tech["Performance Goals"] = "; ".join(perf)
    cons = [f"{cid}: {t}" for cid, t in model["C"].items()]
    if cons:
        tech["Constraints"] = "; ".join(cons)
    if model["hld_tech"]:
        tech["Primary Dependencies"] = "; ".join(model["hld_tech"])
    const_rows = []
    for r in adrs:
        for pr in r["complies_with"]:
            name = next((p["name"] for p in model["principles"] if p["id"] == pr), pr)
            const_rows.append(f"- {pr} {name}: honoured by {r['id']}")
    const = "\n".join(const_rows) if const_rows else (
        "- No enterprise principles (PR.xx) are cited by this change's decisions" +
        (" — the architecture record has none." if not model["principles"] else "; check against the principles on record."))
    complexity = []
    for r in adrs:
        for t in r["tradeoffs"]:
            complexity.append(f"| {_clip(t, 60)} | see {r['id']} Consequences | {need('simpler alternative for ' + r['id']) if False else 'recorded in ' + r['id']} |")
    files["plan.md"] = prov + f"# Implementation Plan: {ch['title']}\n\n**Branch**: `{branch}` | **Date**: {TODAY} | **Spec**: [spec.md](./spec.md)\n\n" \
        f"**Input**: Feature specification from `{feature_dir}/spec.md`\n\n## Summary\n\n" + \
        (ch["intent"] + (" Approach: " + " ".join(adrs[0]["decision"]) if adrs and adrs[0]["decision"] else "") if ch["intent"] else need("summary")) + \
        "\n\n## Technical Context\n\n" + "\n\n".join(f"**{k}**: {v or 'NEEDS CLARIFICATION'}" for k, v in tech.items()) + \
        "\n\n## Constitution Check\n\n*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*\n\n" + const + \
        "\n\n## Project Structure\n\n### Documentation (this feature)\n\n```text\n" + feature_dir + "/\n├── plan.md\n├── research.md          # seeded from the decision records\n├── spec.md\n" + \
        ("├── contracts/           # seeded from the SD api-spec\n" if model["contracts"] else "") + "├── checklists/requirements.md\n└── tasks.md\n```\n\n### Source Code (repository root)\n\n```text\n" + \
        ("\n".join(f"{a}/" for a in ch["affects"]) or "NEEDS CLARIFICATION") + "\n```\n\n**Structure Decision**: components named in the architecture change's `affects:`" + \
        (f"; see {', '.join(r['id'] for r in adrs)}" if adrs else "") + ".\n\n## Complexity Tracking\n\n" + \
        ("| Violation | Why Needed | Simpler Alternative Rejected Because |\n|-----------|------------|-------------------------------------|\n" + "\n".join(complexity) if complexity else "No constitution violations to justify.") + "\n"

    # checklists/requirements.md — spec-kit's own quality gate, left unticked on purpose
    files["checklists/requirements.md"] = f"# Specification Quality Checklist: {ch['title']}\n\n**Purpose**: Validate specification completeness and quality before proceeding to planning\n**Created**: {TODAY}\n**Feature**: [spec.md](../spec.md)\n\n" \
        "## Content Quality\n\n- [ ] No implementation details (languages, frameworks, APIs)\n- [ ] Focused on user value and business needs\n- [ ] Written for non-technical stakeholders\n- [ ] All mandatory sections completed\n\n" \
        "## Requirement Completeness\n\n- [ ] No [NEEDS CLARIFICATION] markers remain\n- [ ] Requirements are testable and unambiguous\n- [ ] Success criteria are measurable\n- [ ] Success criteria are technology-agnostic (no implementation details)\n- [ ] All acceptance scenarios are defined\n- [ ] Edge cases are identified\n- [ ] Scope is clearly bounded\n- [ ] Dependencies and assumptions identified\n\n" \
        "## Feature Readiness\n\n- [ ] All functional requirements have clear acceptance criteria\n- [ ] User scenarios cover primary flows\n- [ ] Feature meets measurable outcomes defined in Success Criteria\n- [ ] No implementation details leak into specification\n\n" \
        f"## Notes\n\n- Seeded by principal-architect from {ch['path']}; {len(clar)} clarification marker(s) in spec.md.\n"

    # tasks.md
    t = 0
    def task(tag, text):
        nonlocal t
        t += 1
        return f"- [ ] T{t:03d} {tag}{text}"
    tasks = prov + f"# Tasks: {ch['title']}\n\n**Input**: Design documents from `{feature_dir}/`\n\n**Prerequisites**: plan.md, spec.md, research.md\n\n" \
        "**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.\n\n## Format: `[ID] [P?] [Story] Description`\n\n"
    tasks += "## Phase 1: Setup\n\n" + task("", f"Read {', '.join(r['id'] for r in recs) or 'change.md'} and confirm plan.md Technical Context has no NEEDS CLARIFICATION left") + "\n\n"
    if model["contracts"]:
        tasks += "## Phase 2: Foundational\n\n" + "\n".join(task("", f"Update `contracts/{os.path.basename(c)}` to the interface in research.md and verify contract tests pass") for c in model["contracts"]) + "\n\n"
    for i, s in enumerate(stories, 1):
        tasks += f"## Phase {i + 2}: User Story {i} - {s['title']} (Priority: P{min(s['rank'], 3)})\n\n**Goal**: {s['so_that'] or s['want'] or s['title']}\n\n"
        for sc in s["scenarios"] or [{"name": "acceptance criteria"}]:
            tasks += task(f"[US{i}] ", f"Implement {s['id']} so that scenario \"{sc['name']}\" passes in {', '.join(ch['affects']) or 'the code'}") + "\n"
        tasks += "\n"
    tasks += "## Final Phase: Verification and traceability\n\n"
    for qid, q in model["Q"].items():
        tasks += task("", f"Verify {qid} by {q.get('verification') or 'its means of verification'}: {q.get('measure') or q['name']}") + "\n"
    for r in adrs:
        tasks += task("", f"Mark the site that enacts {r['id']} with `ARCH-REF: {r['id']}` and verify `arch.py verify --change {ch['id']}` reports breadcrumbs passed") + "\n"
    files["tasks.md"] = tasks
    return files, clar


def render_constitution(principles, project, extra_sections):
    body = f"# {project} Constitution\n\n## Core Principles\n\n"
    for i, p in enumerate(principles, 1):
        roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][i - 1] if i <= 12 else str(i)
        body += f"### {roman}. {p['name']} ({p['id']})\n{p['statement']}\n\n*Rationale*: {p['rationale']}\n\n"
    for title, text in extra_sections:
        body += f"## {title}\n\n{text}\n\n"
    body += ("## Governance\n\nThis constitution restates the enterprise architecture principles (PR.xx) kept under the "
             "architecture docs root; those remain the source of truth, and an amendment here is an amendment there "
             "first, through the RFC → ADR lifecycle. Solution and software decisions cite the principles they honour "
             "in `complies-with:`; a deviation needs an ADR that says why.\n\n"
             f"**Version**: 1.0.0 | **Ratified**: {TODAY} | **Last Amended**: {TODAY}\n")
    return body


# ---------------------------------------------------------------- entry points
SIDECAR = ".principal-architect.json"
TASK_TEXT = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(?:T\d+\s+)?(?:\d+(?:\.\d+)*\s+)?(.*\S)\s*$")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _carry_ticks(old, new):
    """Re-seed a task list without losing the boxes the implementer already ticked."""
    done = set()
    for line in old.splitlines():
        m = TASK_TEXT.match(line)
        if m and re.match(r"^\s*[-*]\s+\[[xX]\]", line):
            done.add(" ".join(m.group(1).split()))
    out = []
    for line in new.splitlines():
        m = TASK_TEXT.match(line)
        if m and " ".join(m.group(1).split()) in done:
            line = re.sub(r"\[ \]", "[x]", line, count=1)
        out.append(line)
    return "\n".join(out) + ("\n" if new.endswith("\n") else "")


def export(arch, ctx, state, target, yes=False, force=False, out=None):
    """Build the model and write (or plan) the target. Returns the result dict."""
    if state["state"] in ("blocked", "not_needed"):
        raise arch.CliError("not_ready", f"change is {state['state']}; the design must be planned "
                            f"(status ready or later) before it can be handed over")
    model = Source(arch, ctx, state).build()
    repo = ctx["repo"]
    cid = state["change"]
    if target == "openspec":
        root = out or os.path.join(repo, "openspec")
        existing = set()
        specs_dir = os.path.join(root, "specs")
        if os.path.isdir(specs_dir):
            for d in os.listdir(specs_dir):
                if os.path.exists(os.path.join(specs_dir, d, "spec.md")):
                    existing.add(d)
        dest = os.path.join(root, "changes", cid)
        cmd = f"arch.py export openspec --change {cid}"
        files = render_openspec(model, cmd, existing)
        clar = []
        gate = f"openspec validate {cid} --strict"
        after = (f"Finish the seed with OpenSpec's own flow: `openspec status --change {cid}`, then "
                 f"`openspec instructions <artifact> --change {cid} --json` per artifact, and `{gate}`.")
    else:
        root = out or os.path.join(repo, "specs")
        n = 1
        if os.path.isdir(root):
            for d in os.listdir(root):
                m = re.match(r"^(\d{3})-", d)
                if m:
                    n = max(n, int(m.group(1)) + 1)
        dest = os.path.join(root, f"{n:03d}-{cid}")
        cmd = f"arch.py export speckit --change {cid}"
        files, clar = render_speckit(model, cmd, arch.rel(dest, repo))
        for c in model["contracts"]:
            files[f"contracts/{os.path.basename(c)}"] = ("copy", os.path.join(repo, c))
        gate = "/speckit.analyze (after /speckit.plan)"
        after = (f"Finish with spec-kit's own flow: `/speckit.clarify` for the {len(clar)} marker(s), "
                 f"`/speckit.plan` (research.md and plan.md are seeded; it adds data-model.md and quickstart.md), "
                 f"`/speckit.tasks`, `/speckit.analyze`.")
    exists = os.path.exists(dest)
    if exists and not force:
        raise arch.CliError("target_exists", f"{arch.rel(dest, repo)} already exists; pass --force to overwrite "
                            f"the seeded files (hand-written files there are kept)")
    plan = [{"path": arch.rel(os.path.join(dest, p), repo), "action": "copy" if isinstance(v, tuple) else "write",
             "overwrites": os.path.exists(os.path.join(dest, p))} for p, v in files.items()]
    result = {
        "change": cid, "target": target, "dest": arch.rel(dest, repo), "applied": False, "plan": plan,
        "derived": {"drivers": sorted(model["F"]), "quality": sorted(model["Q"]), "stories": [s["id"] for s in model["stories"]],
                    "records": [r["id"] for r in model["adrs"] + model["rfcs"]], "capability": model["capability"],
                    "contracts": model["contracts"], "principles_cited": sorted({pr for r in model["adrs"] for pr in r["complies_with"]}),
                    "prd_delta": model["delta"]},
        "gaps": model["notes"] + [f"[NEEDS CLARIFICATION: {c}]" for c in clar],
        "gate": gate, "next": after, "fingerprint": model["fingerprint"],
    }
    # A re-export must never destroy work done on the implementation side. The sidecar
    # remembers what each seeded file looked like; a file that still looks like that is
    # the seed's to rewrite, anything edited since is kept and reported.
    sidecar = os.path.join(dest, SIDECAR)
    seeded = {}
    if os.path.exists(sidecar):
        try:
            with open(sidecar, encoding="utf-8") as fh:
                seeded = json.load(fh).get("files", {})
        except (OSError, ValueError):
            seeded = {}
    kept = []
    for entry in plan:
        p = os.path.relpath(entry["path"], arch.rel(dest, repo)).replace(os.sep, "/")
        if not entry["overwrites"]:
            continue
        path = os.path.join(dest, p)
        v = files[p]
        if isinstance(v, tuple):
            with open(path, "rb") as fh:
                current = hashlib.sha256(fh.read()).hexdigest()
            edited = seeded.get(p) != current
        else:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            unticked = re.sub(r"\[[xX]\]", "[ ]", text)
            edited = seeded.get(p) not in (_sha(text), _sha(unticked))
            if not edited and p.endswith("tasks.md"):
                files[p] = _carry_ticks(text, v)
        if edited:
            kept.append(p)
            entry["action"] = "keep"
            entry["reason"] = "edited since it was seeded" if p in seeded else "no seed record for it"
    result["kept"] = kept
    if kept:
        result["gaps"].append("kept " + ", ".join(kept) + " as edited by hand; carry the record's change into them yourself")
    if yes:
        written = {}
        for p, v in files.items():
            if p in kept:
                written[p] = seeded.get(p)
                continue
            path = os.path.join(dest, p)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if isinstance(v, tuple):
                shutil.copyfile(v[1], path)
                with open(path, "rb") as fh:
                    written[p] = hashlib.sha256(fh.read()).hexdigest()
            else:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(v)
                written[p] = _sha(re.sub(r"\[[xX]\]", "[ ]", v)) if p.endswith("tasks.md") else _sha(v)
        with open(sidecar, "w", encoding="utf-8") as fh:
            json.dump({"change": cid, "target": target, "exported": TODAY, "fingerprint": model["fingerprint"],
                       "files": {k: v for k, v in written.items() if v}}, fh, indent=2)
            fh.write("\n")
        if target == "speckit":
            fj = os.path.join(repo, ".specify", "feature.json")
            if os.path.isdir(os.path.dirname(fj)):
                with open(fj, "w", encoding="utf-8") as fh:
                    json.dump({"feature_directory": arch.rel(dest, repo)}, fh, indent=2)
                result["feature_json"] = arch.rel(fj, repo)
        cpath = os.path.join(repo, state["path"], "change.md")
        fm, _ = arch.frontmatter(cpath)
        hand = [h for h in arch.as_list(fm.get("handoff")) if not h.startswith(target + ":")]
        arch.set_fm(cpath, "handoff", hand + [f"{target}:{arch.rel(dest, repo)}@{model['fingerprint']}"])
        result["applied"] = True
    return result


def export_constitution(arch, ctx, yes=False, force=False, out=None):
    src = Source(arch, ctx, {"change": None, "path": None, "records": []})
    principles = src.principles()
    if not principles:
        raise arch.CliError("no_principles", "no enterprise principles (PR.xx) on record; write them in "
                            "enterprise-architecture.md §2 first (TOGAF Preliminary), then export")
    dest = out or os.path.join(ctx["repo"], ".specify", "memory", "constitution.md")
    if os.path.exists(dest) and not force:
        raise arch.CliError("target_exists", f"{arch.rel(dest, ctx['repo'])} already exists; pass --force to replace it")
    project = os.path.basename(ctx["repo"].rstrip("/")).replace("-", " ").title()
    extra = []
    prd = src.prd()
    if prd["C"]:
        extra.append(("Additional Constraints", "\n".join(f"- {cid}: {t}" for cid, t in prd["C"].items())))
    if prd["Q"]:
        extra.append(("Quality Standards", "\n".join(
            f"- {qid} {q['name']}: {q.get('measure') or q.get('response') or ''}" for qid, q in prd["Q"].items())))
    text = render_constitution(principles, project, extra)
    result = {"dest": arch.rel(dest, ctx["repo"]), "principles": [p["id"] for p in principles],
              "source": principles[0]["path"], "applied": False}
    if yes:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        result["applied"] = True
    return result
