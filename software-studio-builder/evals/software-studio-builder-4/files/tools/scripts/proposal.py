#!/usr/bin/env python3
"""The studio proposal: one JSON source of truth, a Markdown rendering, and a check.

    proposal.py init RUN_DIR --name "HR Studio" --slug hr-studio --domain "HR & payroll back-office"
    proposal.py check RUN_DIR [--ledger RUN_DIR/research]
    proposal.py render RUN_DIR            # writes RUN_DIR/proposal.md from proposal.json
    proposal.py derive RUN_DIR ROLE       # print one role's full reporting line

RUN_DIR is `<target>/.ssb/`. `proposal.json` is edited (by Claude, with the user's
decisions); `proposal.md` is ONLY ever rendered from it, so the two cannot drift.

Derived, never stored (so they cannot disagree with their source):
  * a role's **Delegates to**  = every role whose reports_to is that role
  * a role's **Gates owned**   = every gate whose owner is that role

Every role, phase step, artifact, skill, rule, gate and stack carries `claims`: a list
whose entries are ledger claim ids (`C001`), `NOT SOURCEABLE: <what was searched>`, or
`USER: <the decision the user made>`. An empty list is a FAIL; an item resting only on
NOT SOURCEABLE entries or on unverified claims is a CONCERN the user sees before approving.

Verdict: FAIL > NOT ASSESSED > CONCERNS > PASS (exit 1 / 3 / 0 / 0).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ledger  # noqa: E402

TIERS = ["director", "lead", "specialist"]
MODELS = ["opus", "sonnet", "haiku"]
EFFORTS = ["low", "medium", "high"]
WORKFLOWS = ["question-first", "implementation"]
RIGORS = ["minimal", "standard", "full"]
BASELINE_SKILLS = ["start", "next-step", "gate-check", "project-settings"]
KNOWN_HOOKS = ["session-start", "validate-commit", "validate-write", "validate-read", "log-agent"]
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
# Proposal text is rendered verbatim into agent-facing files (references/writing-for-agents.md).
COLD_PHRASES = re.compile(r"\b(as discussed|as mentioned (?:above|earlier|before)|see above|mentioned earlier|"
                          r"the above|previous conversation|earlier in (?:the|this) conversation|as we said)\b", re.I)
PLACEHOLDERS = re.compile(r"\{\{[^}]*\}\}|\[TBD\]|\[CHOOSE[^\]]*\]|\bTODO\b")
DESC_WORDS = 40
GATE_ID = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")
SECTIONS = ["studio", "concept_map", "roles", "phases", "artifacts", "skills", "rules", "stacks",
            "gates", "hooks", "rigor", "scope", "open_questions"]
ROLE_FIELDS = ["id", "title", "tier", "description", "reports_to", "implements_specs_from", "escalation",
               "siblings", "coordinates_with", "owns_paths", "skills", "model", "effort", "tools", "workflow",
               "responsibilities", "standards", "must_not", "mvp", "claims"]


def path(run_dir: str) -> str:
    return os.path.join(run_dir, "proposal.json")


def load(run_dir: str) -> dict:
    with open(path(run_dir), encoding="utf-8") as fh:
        return json.load(fh)


def skeleton(name: str, slug: str, domain: str) -> dict:
    return {
        "schema": "ssb-proposal/1",
        "studio": {"name": name, "slug": slug, "domain": domain, "summary": "", "goal": ""},
        "concept_map": [],
        "roles": [], "phases": [], "artifacts": [], "skills": [], "rules": [],
        "stacks": [], "gates": [], "hooks": list(KNOWN_HOOKS),
        "rigor": {"default": "minimal"},
        "scope": {"generate": "mvp", "later": []},
        "open_questions": [],
    }


# ------------------------------------------------------------------ derivations

def delegates_to(bp: dict, role_id: str) -> list[str]:
    return [r["id"] for r in bp.get("roles", []) if r.get("reports_to") == role_id]


def gates_owned(bp: dict, role_id: str) -> list[str]:
    return [g["id"] for g in bp.get("gates", []) if g.get("owner") == role_id]


def deferred_items(bp: dict) -> list[str]:
    """Everything that will not be generated: scope.later, plus mvp:false items when generating the MVP.
    The same rule generate.py's deferred_set applies — the user must see the real cut before approving."""
    d = set(bp.get("scope", {}).get("later", []))
    if bp.get("scope", {}).get("generate", "mvp") == "mvp":
        for kind, key, items in (("role", "id", bp.get("roles", [])), ("skill", "name", bp.get("skills", [])),
                                 ("rule", "id", bp.get("rules", [])), ("gate", "id", bp.get("gates", [])),
                                 ("artifact", "id", bp.get("artifacts", []))):
            for it in items:
                if it.get("mvp", True) is False:
                    d.add(f"{kind}:{it.get(key)}")
    return sorted(d)


def role_by_id(bp: dict) -> dict:
    return {r.get("id"): r for r in bp.get("roles", [])}


# ------------------------------------------------------------------ check

def check(bp: dict, ledger_dir: str | None) -> tuple[str, list[str], list[str], list[str]]:
    fail: list[str] = []
    concern: list[str] = []
    na: list[str] = []
    if bp.get("schema") != "ssb-proposal/1":
        fail.append("schema must be 'ssb-proposal/1'")
    for s in SECTIONS:
        if s not in bp:
            fail.append(f"missing section `{s}`")
    st = bp.get("studio", {})
    for k in ("name", "slug", "domain", "summary"):
        if not st.get(k):
            fail.append(f"studio.{k} is empty")
    if st.get("slug") and not SLUG.match(st["slug"]):
        fail.append("studio.slug must be a lowercase slug")
    roles = role_by_id(bp)
    skills = {s.get("name") for s in bp.get("skills", [])} | set(BASELINE_SKILLS)
    arts = {a.get("id") for a in bp.get("artifacts", [])}
    phases = [p.get("id") for p in bp.get("phases", [])]

    # --- claims
    led_claims = None
    if ledger_dir and os.path.exists(os.path.join(ledger_dir, "run_manifest.json")):
        led_claims = {c["claim_id"]: c for c in ledger.rows(ledger_dir, "claims.jsonl")}
    else:
        na.append(f"claims: no ledger at {ledger_dir} — claim ids could not be resolved")

    def claims_ok(where: str, cl):
        if not isinstance(cl, list) or not cl:
            fail.append(f"{where}: `claims` is empty — cite a claim id, `NOT SOURCEABLE: …` or `USER: …`")
            return
        solid, weak = 0, []
        for c in cl:
            c = str(c)
            if c.startswith("NOT SOURCEABLE:"):
                continue
            if c.startswith("USER:"):
                solid += 1
                continue
            if not re.fullmatch(r"C\d{3,}", c):
                fail.append(f"{where}: claim entry {c!r} is not Cnnn, `NOT SOURCEABLE: …` or `USER: …`")
                continue
            if led_claims is None:
                continue
            if c not in led_claims:
                fail.append(f"{where}: claim {c} is not in the ledger")
            elif led_claims[c]["status"] in ("unverified", "not-sourceable"):
                weak.append(f"{c} {led_claims[c]['status']}")
            else:
                solid += 1
        ns = sum(1 for c in cl if str(c).startswith("NOT SOURCEABLE:"))
        if solid == 0 and led_claims is not None:
            concern.append(f"{where}: no sourced or user-decided support"
                           + (f" ({', '.join(weak)})" if weak else "") + (f" ({ns} NOT SOURCEABLE)" if ns else ""))
        elif weak:
            concern.append(f"{where}: partly rests on {', '.join(weak)}")

    for i, m in enumerate(bp.get("concept_map", [])):
        if not m.get("concept") or not m.get("here"):
            fail.append(f"concept_map[{i}]: needs `concept` and `here`")

    # --- roles and hierarchy
    if not roles:
        fail.append("roles: none")
    directors = [r for r in roles.values() if r.get("tier") == "director"]
    if roles and not directors:
        fail.append("roles: no director")
    for rid, r in roles.items():
        w = f"role {rid}"
        for f in ROLE_FIELDS:
            if f not in r:
                fail.append(f"{w}: missing field `{f}`")
        if not isinstance(rid, str) or not SLUG.match(rid):
            fail.append(f"{w}: id must be a lowercase slug")
        if r.get("tier") not in TIERS:
            fail.append(f"{w}: tier {r.get('tier')!r} not in {TIERS}")
            continue
        if r.get("model") not in MODELS:
            fail.append(f"{w}: model {r.get('model')!r} not in {MODELS}")
        if r.get("effort") not in EFFORTS:
            fail.append(f"{w}: effort {r.get('effort')!r} not in {EFFORTS}")
        if r.get("workflow") not in WORKFLOWS:
            fail.append(f"{w}: workflow {r.get('workflow')!r} not in {WORKFLOWS}")
        rt = r.get("reports_to")
        if r["tier"] == "director":
            if rt != "user":
                fail.append(f"{w}: a director reports to `user`, not {rt!r}")
        elif rt not in roles:
            fail.append(f"{w}: reports_to {rt!r} is not a role")
        elif roles[rt].get("tier") in TIERS and TIERS.index(roles[rt]["tier"]) >= TIERS.index(r["tier"]):
            fail.append(f"{w}: reports_to {rt} ({roles[rt]['tier']}) is not above {r['tier']}")
        esc = [e for e in r.get("escalation", []) or [] if isinstance(e, dict)]
        to_user = [e for e in esc if e.get("to") == "user"]
        if r["tier"] == "director" and not to_user:
            fail.append(f"{w}: directors escalate to the user — add an escalation {{\"to\": \"user\", \"when\": …}}")
        if r["tier"] != "director" and to_user:
            fail.append(f"{w}: only a director escalates to `user`; a {r['tier']} escalates through its reporting line")
        for lab, key in (("escalation", "to"), ("siblings", "with"), ("coordinates_with", "with")):
            for e in r.get(lab, []) or []:
                if lab == "escalation" and isinstance(e, dict) and e.get("to") == "user":
                    if not e.get("when"):
                        fail.append(f"{w}: escalation → user gives no reason (`when`)")
                    continue
                if not isinstance(e, dict) or e.get(key) not in roles:
                    fail.append(f"{w}: {lab} target {e!r} is not a role")
                elif e.get(key) == rid:
                    fail.append(f"{w}: {lab} names itself")
                elif not (e.get("when") or e.get("for")):
                    fail.append(f"{w}: {lab} → {e.get(key)} gives no reason (`when`/`for`)")
        for t in r.get("implements_specs_from", []) or []:
            if t not in roles:
                fail.append(f"{w}: implements_specs_from {t!r} is not a role")
        for s in r.get("skills", []) or []:
            if s not in skills:
                fail.append(f"{w}: preloads unknown skill {s!r}")
        for k in ("responsibilities", "must_not", "owns_paths", "tools"):
            if not r.get(k):
                fail.append(f"{w}: `{k}` is empty")
        for sd in r.get("standards", []) or []:
            if not sd.get("heading") or not sd.get("rules"):
                fail.append(f"{w}: a standards entry needs `heading` and `rules`")
        if "delegates_to" in r and sorted(r["delegates_to"]) != sorted(delegates_to(bp, rid)):
            fail.append(f"{w}: stored delegates_to {r['delegates_to']} disagrees with the derived "
                        f"{delegates_to(bp, rid)} — delete the field; it is derived")
        if r["tier"] != "specialist" and not delegates_to(bp, rid):
            concern.append(f"{w}: a {r['tier']} with nobody reporting to it")
        claims_ok(w, r.get("claims"))
    # cycles / reachability
    for rid in roles:
        seen, cur = [], rid
        while cur in roles and roles[cur].get("reports_to") != "user":
            if cur in seen:
                fail.append(f"reporting cycle: {' -> '.join(seen + [cur])}")
                break
            seen.append(cur)
            cur = roles[cur].get("reports_to")

    # --- gates
    gids = set()
    for g in bp.get("gates", []):
        w = f"gate {g.get('id')}"
        if not GATE_ID.match(str(g.get("id", ""))):
            fail.append(f"{w}: id must look like PD-SPEC-REVIEW")
        if g.get("id") in gids:
            fail.append(f"{w}: duplicate id")
        gids.add(g.get("id"))
        if g.get("owner") not in roles:
            fail.append(f"{w}: owner {g.get('owner')!r} is not a role")
        if g.get("phase") is not None and g.get("phase") not in phases:
            fail.append(f"{w}: phase {g.get('phase')!r} is not a phase")
        if len(g.get("verdicts", [])) < 2:
            fail.append(f"{w}: needs >=2 verdict words, best first, failing last")
        if "NOT ASSESSED" in g.get("verdicts", []):
            fail.append(f"{w}: NOT ASSESSED is implicit on every gate; do not list it")
        for k in ("trigger", "context", "prompt"):
            if not g.get(k):
                fail.append(f"{w}: `{k}` is empty")
        claims_ok(w, g.get("claims"))

    # --- phases
    seen_steps = set()
    if not phases:
        fail.append("phases: none")
    for p in bp.get("phases", []):
        w = f"phase {p.get('id')}"
        if p.get("next") is not None and p.get("next") not in phases:
            fail.append(f"{w}: next {p.get('next')!r} is not a phase")
        for s in p.get("steps", []):
            sw = f"step {s.get('id')}"
            if s.get("id") in seen_steps:
                fail.append(f"{sw}: duplicate id")
            seen_steps.add(s.get("id"))
            cmd = s.get("command")
            if cmd and cmd.lstrip("/").split()[0] not in skills:
                fail.append(f"{sw}: command {cmd} is not a skill in the proposal")
            if s.get("owner") not in roles:
                fail.append(f"{sw}: owner {s.get('owner')!r} is not a role")
            if s.get("required") and not (s.get("artifact") or {}).get("glob"):
                fail.append(f"{sw}: required but has no artifact.glob")
            if s.get("template") and s["template"] not in arts:
                fail.append(f"{sw}: template {s['template']!r} is not an artifact id")
            if s.get("min_workflow", "minimal") not in RIGORS:
                fail.append(f"{sw}: min_workflow must be one of {RIGORS}")
            claims_ok(sw, s.get("claims"))

    # --- artifacts, skills, rules, stacks
    for a in bp.get("artifacts", []):
        w = f"artifact {a.get('id')}"
        if not SLUG.match(str(a.get("id", ""))):
            fail.append(f"{w}: id must be a slug")
        if a.get("owner") not in roles:
            fail.append(f"{w}: owner {a.get('owner')!r} is not a role")
        if len(a.get("sections", [])) < 2:
            fail.append(f"{w}: needs >=2 sections")
        if not a.get("path"):
            fail.append(f"{w}: no path")
        claims_ok(w, a.get("claims"))
    for s in bp.get("skills", []):
        w = f"skill {s.get('name')}"
        if not SLUG.match(str(s.get("name", ""))):
            fail.append(f"{w}: name must be a slug")
        if s.get("name") in BASELINE_SKILLS:
            fail.append(f"{w}: {s['name']} is a baseline skill; it is generated from the skeleton")
        if s.get("owner") not in roles:
            fail.append(f"{w}: owner {s.get('owner')!r} is not a role")
        if not s.get("description") or "Use when" not in s.get("description", ""):
            fail.append(f"{w}: description must say what it does and `Use when …`")
        if not s.get("steps"):
            fail.append(f"{w}: no steps")
        if s.get("produces") and s["produces"] not in arts:
            fail.append(f"{w}: produces {s['produces']!r}, not an artifact id")
        if len(s.get("verdicts", [])) < 2:
            fail.append(f"{w}: needs >=2 verdict words")
        for g in s.get("gates", []) or []:
            if g not in gids:
                fail.append(f"{w}: runs unknown gate {g}")
        claims_ok(w, s.get("claims"))
    for r in bp.get("rules", []):
        w = f"rule {r.get('id')}"
        if not SLUG.match(str(r.get("id", ""))):
            fail.append(f"{w}: id must be a slug")
        if not r.get("paths") or not r.get("rules"):
            fail.append(f"{w}: needs paths and rules")
        if r.get("owner") not in roles:
            fail.append(f"{w}: owner {r.get('owner')!r} is not a role")
        claims_ok(w, r.get("claims"))
    if not bp.get("stacks"):
        fail.append("stacks: none")
    for s in bp.get("stacks", []):
        w = f"stack {s.get('name')}"
        for k in ("name", "code_root", "test_root"):
            if not s.get(k):
                fail.append(f"{w}: `{k}` is empty")
        claims_ok(w, s.get("claims"))
    for h in bp.get("hooks", []):
        if h not in KNOWN_HOOKS:
            fail.append(f"hooks: {h!r} is not a skeleton hook ({', '.join(KNOWN_HOOKS)})")
    if (bp.get("rigor") or {}).get("default") not in RIGORS:
        fail.append(f"rigor.default must be one of {RIGORS}")
    if (bp.get("scope") or {}).get("generate") not in ("mvp", "full"):
        fail.append("scope.generate must be 'mvp' or 'full'")
    later = (bp.get("scope") or {}).get("later", [])
    for item in later:
        if not re.fullmatch(r"(role|skill|rule|gate|artifact):[a-zA-Z0-9-]+", str(item)):
            fail.append(f"scope.later entry {item!r} must be kind:id")
    # --- agent-facing text (rendered verbatim into agents, skills, rules, gates, templates)
    def texts():
        for r in bp.get("roles", []):
            w = f"role {r.get('id')}"
            yield w, "description", r.get("description", "")
            for x in r.get("responsibilities", []) + r.get("must_not", []):
                yield w, "responsibilities/must_not", x
            for sd in r.get("standards", []) or []:
                for x in sd.get("rules", []):
                    yield w, f"standards '{sd.get('heading')}'", x
        for s in bp.get("skills", []):
            yield f"skill {s.get('name')}", "description", s.get("description", "")
            for st in s.get("steps", []):
                yield f"skill {s.get('name')}", "steps", st.get("detail", "") + " " + st.get("name", "") \
                    if isinstance(st, dict) else st
        for r in bp.get("rules", []):
            for x in r.get("rules", []):
                yield f"rule {r.get('id')}", "rules", x
        for g in bp.get("gates", []):
            for k in ("prompt", "context", "trigger"):
                yield f"gate {g.get('id')}", k, g.get(k, "")
        for a in bp.get("artifacts", []):
            for sec in a.get("sections", []):
                if isinstance(sec, dict):
                    yield f"artifact {a.get('id')}", "section guidance", sec.get("guidance", "")

    for where, field, text in texts():
        text = str(text or "")
        for m in COLD_PHRASES.finditer(text):
            fail.append(f"{where}: {field} says '{m.group(0)}' — agents read it cold; name the file or fact")
        for m in PLACEHOLDERS.finditer(text):
            fail.append(f"{where}: {field} contains placeholder {m.group(0)!r}")
    for r in bp.get("roles", []):
        n = len(str(r.get("description", "")).split())
        if n > DESC_WORDS:
            concern.append(f"role {r.get('id')}: description is {n} words — it becomes the agent's always-loaded "
                           f"trigger; keep it under {DESC_WORDS}")
    for s in bp.get("skills", []):
        n = len(str(s.get("description", "")).split())
        if n > 2 * DESC_WORDS:
            concern.append(f"skill {s.get('name')}: description is {n} words — keep the trigger under {2 * DESC_WORDS}")

    if fail:
        return "FAIL", fail, concern, na
    if na:
        return "NOT ASSESSED", fail, concern, na
    if concern:
        return "CONCERNS", fail, concern, na
    return "PASS", fail, concern, na


# ------------------------------------------------------------------ render

def _cl(cl) -> str:
    return ", ".join(str(c) for c in (cl or [])) or "—"


def render(bp: dict) -> str:
    st = bp["studio"]
    roles = role_by_id(bp)
    L = [f"# Proposal — {st['name']}", "",
         "> Rendered from `proposal.json` by `proposal.py render`. Edit the JSON, never this file.", "",
         f"**Domain:** {st['domain']}  ", f"**Goal:** {st.get('goal') or '—'}  ",
         f"**Generate:** {bp['scope']['generate']} · **Default rigor:** {bp['rigor']['default']}", "",
         "## 1. Domain overview", "", st["summary"], "",
         "## 2. Concept mapping (studio building block → this domain)", "",
         "| Building block | Here | Claims |", "|---|---|---|"]
    for m in bp["concept_map"]:
        L.append(f"| {m['concept']} | {m['here']} | {_cl(m.get('claims'))} |")
    L += ["", "## 3. Roster", "", "```"]

    def tree(parent, depth):
        for r in bp["roles"]:
            if r["reports_to"] == parent:
                L.append("  " * depth + f"{r['id']} ({r['tier']}){'' if r.get('mvp', True) else '  [later]'}")
                tree(r["id"], depth + 1)
    tree("user", 0)
    L += ["```", ""]
    for r in bp["roles"]:
        L += [f"### `{r['id']}` — {r['title']} ({r['tier']})", "", r["description"], "",
              f"- **Reports to:** {'the user' if r['reports_to'] == 'user' else '`' + r['reports_to'] + '`'}",
              f"- **Delegates to:** {', '.join('`' + d + '`' for d in delegates_to(bp, r['id'])) or 'none'}",
              f"- **Implements specs from:** {', '.join('`' + d + '`' for d in r['implements_specs_from']) or 'none'}",
              "- **Escalation targets:** " + ("; ".join(("the user" if e["to"] == "user" else f"`{e['to']}`")
                                                         + f" when {e['when']}" for e in r["escalation"]) or "none"),
              "- **Sibling coordination:** " + ("; ".join(f"`{e['with']}` for {e['for']}" for e in r["siblings"]) or "none"),
              "- **Coordinates with:** " + ("; ".join(f"`{e['with']}` for {e['for']}" for e in r["coordinates_with"]) or "none"),
              f"- **Gates owned:** {', '.join('`' + g + '`' for g in gates_owned(bp, r['id'])) or 'none'}",
              f"- **Owns:** {', '.join('`' + p + '`' for p in r['owns_paths'])}",
              f"- **Skills preloaded:** {', '.join(r['skills']) or 'none'} · **Model:** {r['model']}/{r['effort']} · **Workflow:** {r['workflow']}",
              "- **Responsibilities:** " + "; ".join(r["responsibilities"]),
              "- **Must not:** " + "; ".join(r["must_not"]),
              *[f"- **{s['heading']}:** " + "; ".join(s["rules"]) for s in r["standards"]],
              f"- **Claims:** {_cl(r['claims'])}", ""]
    L += ["## 4. Workflow phases", ""]
    for p in bp["phases"]:
        L += [f"### {p['id']} — {p['name']} (next: {p.get('next') or 'end'})", "",
              "| Step | Command | Owner | Required | From workflow | Artifact | Claims |", "|---|---|---|---|---|---|---|"]
        for s in p["steps"]:
            L.append(f"| {s['id']} {s['name']} | {s.get('command') or '—'} | `{s['owner']}` | "
                     f"{'yes' if s.get('required') else 'no'} | {s.get('min_workflow', 'minimal')} | "
                     f"{(s.get('artifact') or {}).get('glob', '—')} | {_cl(s.get('claims'))} |")
        L.append("")
    L += ["## 5. Artifacts and templates", "", "| Id | Name | Path | Owner | Sections | Claims |", "|---|---|---|---|---|---|"]
    for a in bp["artifacts"]:
        L.append(f"| {a['id']} | {a['name']} | `{a['path']}` | `{a['owner']}` | {'; '.join(x['heading'] if isinstance(x, dict) else x for x in a['sections'])} | {_cl(a.get('claims'))} |")
    L += ["", "## 6. Skills", "", "| Skill | Owner | Produces | Gates | Verdicts | Claims |", "|---|---|---|---|---|---|"]
    for s in bp["skills"]:
        L.append(f"| /{s['name']} | `{s['owner']}` | {s.get('produces') or '—'} | {', '.join(s.get('gates', [])) or '—'} | "
                 f"{' / '.join(s['verdicts'])} | {_cl(s.get('claims'))} |")
    L.append(f"\nBaseline skills generated from the skeleton: {', '.join('/' + b for b in BASELINE_SKILLS)}.")
    L += ["", "## 7. Path-scoped rules", ""]
    for r in bp["rules"]:
        L += [f"- **{r['id']}** (`{'`, `'.join(r['paths'])}`; owner `{r['owner']}`): " + "; ".join(r["rules"])
              + f" — {_cl(r.get('claims'))}"]
    L += ["", "## 8. Stack table", "", "| Stack | Code root | Test root | Build | Test | Run | Claims |", "|---|---|---|---|---|---|---|"]
    for s in bp["stacks"]:
        L.append(f"| {s['name']} | `{s['code_root']}` | `{s['test_root']}` | {s.get('build') or '—'} | "
                 f"{s.get('test') or '—'} | {s.get('run') or '—'} | {_cl(s.get('claims'))} |")
    L += ["", "## 9. Review gates", "", "| Gate | Owner | Phase | Lean | Verdicts | Trigger | Claims |", "|---|---|---|---|---|---|---|"]
    for g in bp["gates"]:
        L.append(f"| {g['id']} | `{g['owner']}` | {g.get('phase') or '—'} | {'yes' if g.get('lean') else 'no'} | "
                 f"{' / '.join(g['verdicts'])} | {g['trigger']} | {_cl(g.get('claims'))} |")
    L += ["", "## 10. Hooks", "", ", ".join(bp["hooks"]), "",
          "## 11. Rigor modes", "", f"Default `{bp['rigor']['default']}`. "
          "`minimal` → workflow minimal, docs terse, QA minimal, review solo; `standard` → standard, balanced, "
          "standard, lean; `full` → full, thorough, full, full.", "",
          "## 12. Scope", "", f"Generate: **{bp['scope']['generate']}**. Deferred (not generated): "
          + (", ".join(deferred_items(bp)) or "none"), "",
          "## 13. Open questions", ""]
    L += [f"- {q}" for q in bp["open_questions"]] or ["- none"]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("run_dir")
    p.add_argument("--name", required=True); p.add_argument("--slug", required=True); p.add_argument("--domain", required=True)
    p = sub.add_parser("check"); p.add_argument("run_dir"); p.add_argument("--ledger")
    p = sub.add_parser("render"); p.add_argument("run_dir")
    p = sub.add_parser("derive"); p.add_argument("run_dir"); p.add_argument("role")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        os.makedirs(a.run_dir, exist_ok=True)
        if os.path.exists(path(a.run_dir)):
            print(f"{path(a.run_dir)} exists; not overwritten")
            return 0
        with open(path(a.run_dir), "w", encoding="utf-8") as fh:
            json.dump(skeleton(a.name, a.slug, a.domain), fh, indent=2)
            fh.write("\n")
        print(f"wrote {path(a.run_dir)}")
        return 0
    try:
        bp = load(a.run_dir)
    except (OSError, ValueError) as e:
        print(f"proposal.json could not be read: {e}")
        print("VERDICT: NOT ASSESSED")
        return 3
    if a.cmd == "check":
        verdict, fail, concern, na = check(bp, a.ledger or os.path.join(a.run_dir, "research"))
        tiers = {t: sum(1 for r in bp.get("roles", []) if r.get("tier") == t) for t in TIERS}
        print(f"roles: {len(bp.get('roles', []))} ({', '.join(f'{k}={v}' for k, v in tiers.items())}) · "
              f"skills: {len(bp.get('skills', []))}+{len(BASELINE_SKILLS)} baseline · rules: {len(bp.get('rules', []))} · "
              f"gates: {len(bp.get('gates', []))} · artifacts: {len(bp.get('artifacts', []))} · phases: {len(bp.get('phases', []))}")
        for f in fail:
            print(f"FAIL: {f}")
        for n in na:
            print(f"NOT ASSESSED: {n}")
        for c in concern:
            print(f"CONCERN: {c}")
        print(f"VERDICT: {verdict}")
        return {"PASS": 0, "CONCERNS": 0, "FAIL": 1, "NOT ASSESSED": 3}[verdict]
    if a.cmd == "render":
        verdict, fail, _, _ = check(bp, None)
        if fail:
            print("proposal has structural failures; run `proposal.py check` first")
            for f in fail[:20]:
                print(f"FAIL: {f}")
            return 1
        out = os.path.join(a.run_dir, "proposal.md")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(render(bp))
        print(f"wrote {out}")
        return 0
    roles = role_by_id(bp)
    r = roles.get(a.role)
    if not r:
        print(f"no role {a.role}")
        return 1
    print(json.dumps({"id": r["id"], "reports_to": r["reports_to"], "delegates_to": delegates_to(bp, r["id"]),
                      "gates_owned": gates_owned(bp, r["id"]), "escalation": r["escalation"],
                      "siblings": r["siblings"], "coordinates_with": r["coordinates_with"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
