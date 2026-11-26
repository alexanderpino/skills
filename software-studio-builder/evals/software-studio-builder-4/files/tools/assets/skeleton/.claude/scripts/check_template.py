#!/usr/bin/env python3
"""Check that a studio template is internally consistent. Stdlib only.

    python3 .claude/scripts/check_template.py [ROOT] [--proposal PATH] [--only C04,C05]

Every check prints one line, `CHECK <id> <PASS|FAIL|NOT ASSESSED> — <what>`, followed by the
files or findings behind it. The run ends with

    VERDICT: FAIL | NOT ASSESSED | PASS   (pass=<n> fail=<n> not_assessed=<n>)

ranked FAIL > NOT ASSESSED > PASS: a known problem outranks an unknown, and a check that could
not run outranks a pass, because a scope nobody could look at has not been shown to be good.
Exit codes: 0 PASS, 1 FAIL, 3 NOT ASSESSED.

The covered sets are DERIVED from the files on disk (every agent file, every skill folder,
every gate file), never from an allowlist, so a role added later cannot slip past the checks
by not being on a list.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mini_yaml  # noqa: E402

TIERS = ["director", "lead", "specialist"]
MODELS = {"opus", "sonnet", "haiku", "inherit"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
AGENT_FM = ["name", "description", "tools", "model", "effort", "maxTurns", "skills", "memory"]
AGENT_SECTIONS = [
    ("### When You Are Spawned", True),
    ("### Collaboration Protocol", True),
    ("#### Collaborative Mindset", True),
    ("### Key Responsibilities", True),
    ("### What This Agent Must NOT Do", True),
    ("### Delegation Map", True),
]
MAP_LABELS = ["Reports to", "Delegates to", "Implements specs from", "Escalation targets",
              "Sibling coordination", "Coordinates with"]
REQUIRED_FILES = [
    "CLAUDE.md", "project.yaml", ".claude/settings.json", ".claude/agent-models.yaml",
    ".claude/docs/coordination-rules.md", ".claude/docs/collaboration-protocol.md",
    ".claude/docs/directory-structure.md", ".claude/docs/agent-roster.md",
    ".claude/docs/workflow-catalog.json", ".claude/docs/stacks.tsv", ".claude/docs/gates.md",
    ".claude/scripts/resolve_config.py", ".claude/scripts/artifact_check.py",
    ".claude/scripts/mini_yaml.py",
]


class Report:
    def __init__(self):
        self.rows: list[tuple[str, str, str, list[str]]] = []

    def add(self, cid: str, status: str, what: str, details: list[str] | None = None):
        self.rows.append((cid, status, what, details or []))

    def verdict(self) -> str:
        st = {r[1] for r in self.rows}
        if "FAIL" in st:
            return "FAIL"
        if "NOT ASSESSED" in st or not self.rows:
            return "NOT ASSESSED"
        return "PASS"

    def print(self):
        for cid, status, what, det in self.rows:
            print(f"CHECK {cid} {status} — {what}")
            for d in det[:40]:
                print(f"  {d}")
            if len(det) > 40:
                print(f"  … {len(det) - 40} more")
        c = {s: sum(1 for r in self.rows if r[1] == s) for s in ("PASS", "FAIL", "NOT ASSESSED")}
        print(f"VERDICT: {self.verdict()}   (pass={c['PASS']} fail={c['FAIL']} not_assessed={c['NOT ASSESSED']})")


# ---------------------------------------------------------------- parsing helpers

def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if not mm:
            continue
        k, v = mm.group(1), mm.group(2).strip()
        if v.startswith("[") and v.endswith("]"):
            fm[k] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        else:
            fm[k] = v.strip("\"'") if v not in ("", ">-", "|") else v
    # a `paths:` block list
    pm = re.search(r"^paths:\s*\n((?:\s+-\s+.*\n?)+)", m.group(1) + "\n", re.M)
    if pm:
        fm["paths"] = [re.sub(r"^\s+-\s+", "", l).strip().strip("\"'") for l in pm.group(1).splitlines() if l.strip()]
    return fm, m.group(2)


def section(body: str, heading: str) -> str | None:
    level = len(heading) - len(heading.lstrip("#"))
    lines = body.splitlines()
    for i, l in enumerate(lines):
        if l.strip() == heading:
            out = []
            for l2 in lines[i + 1:]:
                m = re.match(r"^(#+)\s", l2)
                if m and len(m.group(1)) <= level:
                    break
                out.append(l2)
            return "\n".join(out)
    return None


def delegation_map(body: str) -> dict[str, list[str]]:
    """Parse **Label**: lines and the bullets under them into {label: [role names]}."""
    sec = section(body, "### Delegation Map")
    out: dict[str, list[str]] = {}
    if sec is None:
        return out
    cur = None
    for line in sec.splitlines():
        m = re.match(r"^\*\*([^*]+)\*\*:?\s*(.*)$", line.strip())
        if m:
            cur = m.group(1).strip().rstrip(":")
            out.setdefault(cur, [])
            rest = m.group(2)
            out[cur] += re.findall(r"`([a-z0-9][a-z0-9-]*)`", rest)
            continue
        if cur and re.match(r"^\s*-\s+", line):
            first = re.search(r"`([a-z0-9][a-z0-9-]*)`", line)
            if first:
                out[cur].append(first.group(1))
    return out


def roster_table(text: str) -> dict[str, dict]:
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) >= 3:
            role = re.fullmatch(r"`([a-z0-9-]+)`", cells[0])
            if role and cells[1].lower() in TIERS:
                rt = re.fullmatch(r"`([a-z0-9-]+)`", cells[2])
                rows[role.group(1)] = {"tier": cells[1].lower(), "reports_to": rt.group(1) if rt else cells[2]}
    return rows


# ---------------------------------------------------------------- checks

def c01_files(root, rep):
    missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(root, f))]
    rep.add("C01", "FAIL" if missing else "PASS", "required files exist",
            [f"missing: {m}" for m in missing] or [f"{len(REQUIRED_FILES)} files present"])


def c02_settings(root, rep):
    p = os.path.join(root, ".claude/settings.json")
    if not os.path.exists(p):
        rep.add("C02", "NOT ASSESSED", "settings.json hooks resolve", ["settings.json missing (see C01)"])
        return
    try:
        s = json.loads(read(p))
    except ValueError as e:
        rep.add("C02", "FAIL", "settings.json parses", [str(e)])
        return
    probs, seen = [], 0
    for event, groups in (s.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                for rel in re.findall(r"(\.claude/hooks/[A-Za-z0-9_.-]+)", cmd):
                    seen += 1
                    if not os.path.exists(os.path.join(root, rel)):
                        probs.append(f"{event}: {rel} does not exist")
    deny = (s.get("permissions") or {}).get("deny") or []
    for must in ("rm -rf", "push --force", "reset --hard", ".env"):
        if not any(must in d for d in deny):
            probs.append(f"permissions.deny has no rule for {must!r}")
    if seen == 0:
        rep.add("C02", "NOT ASSESSED", "settings.json hooks resolve", ["no hook commands found"] + probs)
    else:
        rep.add("C02", "FAIL" if probs else "PASS", "settings.json parses, hooks exist, deny list present",
                probs or [f"{seen} hook commands resolve"])


def c03_hooks(root, rep):
    hooks = sorted(glob.glob(os.path.join(root, ".claude/hooks/*.sh")))
    if not hooks:
        rep.add("C03", "NOT ASSESSED", "hook scripts parse", ["no .claude/hooks/*.sh"])
        return
    bash = shutil.which("bash")
    if not bash:
        rep.add("C03", "NOT ASSESSED", "hook scripts parse", ["bash not found; `bash -n` could not run"])
        return
    bad = []
    for h in hooks:
        r = subprocess.run([bash, "-n", h], capture_output=True, text=True)
        if r.returncode:
            bad.append(f"{os.path.relpath(h, root)}: {r.stderr.strip()}")
    rep.add("C03", "FAIL" if bad else "PASS", "hook scripts pass `bash -n`", bad or [f"{len(hooks)} hooks parse"])


def load_agents(root):
    agents = {}
    for p in sorted(glob.glob(os.path.join(root, ".claude/agents/*.md"))):
        fm, body = front_matter(read(p))
        agents[os.path.basename(p)[:-3]] = {"path": os.path.relpath(p, root), "fm": fm, "body": body,
                                            "map": delegation_map(body)}
    return agents


def c04_agents(root, rep, agents):
    if not agents:
        rep.add("C04", "NOT ASSESSED", "agent files well-formed", ["no .claude/agents/*.md"])
        return
    probs = []
    for name, a in agents.items():
        fm = a["fm"]
        for k in AGENT_FM:
            if k not in fm or fm[k] in ("", None):
                probs.append(f"{a['path']}: frontmatter lacks {k}")
        if fm.get("name") and fm["name"] != name:
            probs.append(f"{a['path']}: name {fm['name']!r} != file name")
        if fm.get("model") and fm["model"] not in MODELS:
            probs.append(f"{a['path']}: model {fm['model']!r} not in {sorted(MODELS)}")
        if fm.get("effort") and fm["effort"] not in EFFORTS:
            probs.append(f"{a['path']}: effort {fm['effort']!r} not in {sorted(EFFORTS)}")
        for h, _ in AGENT_SECTIONS:
            if section(a["body"], h) is None:
                probs.append(f"{a['path']}: missing section {h!r}")
        for lab in MAP_LABELS:
            if lab not in a["map"]:
                probs.append(f"{a['path']}: Delegation Map lacks **{lab}**")
        rt = a["map"].get("Reports to")
        if rt is not None and len(rt) > 1:
            probs.append(f"{a['path']}: **Reports to** names {len(rt)} roles; it must name one (or the user)")
        if rt == [] and not re.search(r"^\*\*Reports to\*\*:?\s*the user", a["body"], re.M):
            probs.append(f"{a['path']}: **Reports to** names no role and is not `the user`")
    rp = os.path.join(root, ".claude/docs/agent-roster.md")
    tiers = roster_table(read(rp)) if os.path.exists(rp) else {}
    for name, a in agents.items():
        if tiers.get(name, {}).get("tier") != "director":
            continue
        sec = section(a["body"], "### Delegation Map") or ""
        m = re.search(r"^\*\*Escalation targets\*\*:?(.*?)(?=^\*\*|\Z)", sec, re.M | re.S)
        if not m or not re.search(r"^\s*-\s+the user\b", m.group(1), re.M):
            probs.append(f"{a['path']}: a director must escalate to the user (`- the user when …` under "
                         "**Escalation targets**)")
    rep.add("C04", "FAIL" if probs else "PASS", "agent files have frontmatter, required sections, full Delegation Map",
            probs or [f"{len(agents)} agents checked"])


def c05_hierarchy(root, rep, agents):
    rp = os.path.join(root, ".claude/docs/agent-roster.md")
    if not agents or not os.path.exists(rp):
        rep.add("C05", "NOT ASSESSED", "reporting hierarchy", ["no agents or no agent-roster.md"])
        return
    roster = roster_table(read(rp))
    probs = []
    names = set(agents)
    if set(roster) != names:
        for m in sorted(names - set(roster)):
            probs.append(f"agent-roster.md has no row for `{m}`")
        for m in sorted(set(roster) - names):
            probs.append(f"agent-roster.md lists `{m}`, which has no agent file")
    for name, a in agents.items():
        r = roster.get(name)
        if not r:
            continue
        rt = a["map"].get("Reports to", [])
        target = rt[0] if rt else "user"
        if target != r["reports_to"]:
            probs.append(f"{a['path']}: Reports to `{target}` but roster says `{r['reports_to']}`")
        if r["tier"] == "director":
            if target != "user":
                probs.append(f"{a['path']}: a director reports to the user, not `{target}`")
        else:
            if target not in roster:
                probs.append(f"{a['path']}: reports to unknown role `{target}`")
            elif TIERS.index(roster[target]["tier"]) >= TIERS.index(r["tier"]):
                probs.append(f"{a['path']}: reports to `{target}` ({roster[target]['tier']}), "
                             f"which is not above its own tier ({r['tier']})")
        # both directions: delegates_to == roles reporting here
        reports_here = {n for n, rr in roster.items() if rr["reports_to"] == name}
        declared = set(a["map"].get("Delegates to", []))
        for m in sorted(reports_here - declared):
            probs.append(f"{a['path']}: `{m}` reports here but is not under **Delegates to**")
        for m in sorted(declared - reports_here):
            probs.append(f"{a['path']}: delegates to `{m}`, which does not report here")
        for lab in ("Escalation targets", "Sibling coordination", "Coordinates with", "Implements specs from"):
            for t in a["map"].get(lab, []):
                if t not in names:
                    probs.append(f"{a['path']}: **{lab}** names unknown role `{t}`")
                elif t == name:
                    probs.append(f"{a['path']}: **{lab}** names itself")
    # reachability and cycles
    for name in roster:
        seen, cur = [], name
        while cur in roster and roster[cur]["reports_to"] != "user":
            if cur in seen:
                probs.append(f"reporting cycle: {' -> '.join(seen + [cur])}")
                break
            seen.append(cur)
            cur = roster[cur]["reports_to"]
        else:
            if cur not in roster:
                probs.append(f"`{name}` does not reach a director (chain ends at `{cur}`)")
    if not any(r["tier"] == "director" for r in roster.values()):
        probs.append("no director in agent-roster.md")
    rep.add("C05", "FAIL" if probs else "PASS",
            "reporting lines: one tier up, reciprocal delegation, known targets, no orphans or cycles",
            probs or [f"{len(roster)} roles in one hierarchy"])


def c06_models(root, rep, agents):
    p = os.path.join(root, ".claude/agent-models.yaml")
    if not os.path.exists(p):
        rep.add("C06", "NOT ASSESSED", "agent-models.yaml matches agents", ["file missing"])
        return
    try:
        data = mini_yaml.load(p)
    except mini_yaml.MiniYamlError as e:
        rep.add("C06", "FAIL", "agent-models.yaml parses", [str(e)])
        return
    table = data.get("agents") or {}
    probs = []
    for m in sorted(set(agents) - set(table)):
        probs.append(f"`{m}` has no row in agent-models.yaml")
    for m in sorted(set(table) - set(agents)):
        probs.append(f"agent-models.yaml lists `{m}`, which has no agent file")
    for n, row in table.items():
        if not isinstance(row, dict):
            probs.append(f"`{n}`: row must have model and effort")
            continue
        if n in agents:
            fm = agents[n]["fm"]
            if fm.get("model") != row.get("model") or fm.get("effort") != row.get("effort"):
                probs.append(f"`{n}`: agent file says {fm.get('model')}/{fm.get('effort')}, "
                             f"table says {row.get('model')}/{row.get('effort')}")
    rep.add("C06", "FAIL" if probs else "PASS", "agent-models.yaml lists exactly the agents, same model/effort",
            probs or [f"{len(table)} rows agree"])


def c07_skills(root, rep, agents):
    dirs = sorted(d for d in glob.glob(os.path.join(root, ".claude/skills/*")) if os.path.isdir(d))
    if not dirs:
        rep.add("C07", "NOT ASSESSED", "skills well-formed", ["no .claude/skills/*/"])
        return
    probs = []
    for d in dirs:
        name = os.path.basename(d)
        p = os.path.join(d, "SKILL.md")
        if not os.path.exists(p):
            probs.append(f".claude/skills/{name}: no SKILL.md")
            continue
        fm, body = front_matter(read(p))
        rel = os.path.relpath(p, root)
        if fm.get("name") != name:
            probs.append(f"{rel}: name {fm.get('name')!r} != folder")
        if not fm.get("description"):
            probs.append(f"{rel}: no description")
        if "NOT ASSESSED" not in body:
            probs.append(f"{rel}: verdicts lack a NOT ASSESSED value")
        if "Write" in str(fm.get("allowed-tools", "")) and "May I write" not in body:
            probs.append(f"{rel}: may write files but never asks \"May I write\"")
        for role in re.findall(r"subagent_type[:=]\s*`?([a-z0-9-]+)`?", body):
            if role not in agents:
                probs.append(f"{rel}: spawns unknown agent `{role}`")
    for n, a in agents.items():
        for s in a["fm"].get("skills", []) if isinstance(a["fm"].get("skills"), list) else []:
            if not os.path.isdir(os.path.join(root, ".claude/skills", s)):
                probs.append(f"{a['path']}: preloads unknown skill `{s}`")
    rep.add("C07", "FAIL" if probs else "PASS", "skills: name, description, NOT ASSESSED verdict, ask-before-write",
            probs or [f"{len(dirs)} skills checked"])


def c08_rules(root, rep):
    rules = sorted(glob.glob(os.path.join(root, ".claude/rules/*.md")))
    if not rules:
        rep.add("C08", "NOT ASSESSED", "path-scoped rules", ["no .claude/rules/*.md"])
        return
    probs = []
    for p in rules:
        fm, body = front_matter(read(p))
        if not fm.get("paths"):
            probs.append(f"{os.path.relpath(p, root)}: no `paths:` globs")
        if not re.search(r"^\s*[-*]\s+\S", body, re.M):
            probs.append(f"{os.path.relpath(p, root)}: no rule bullets")
    rep.add("C08", "FAIL" if probs else "PASS", "rules have paths and bullets", probs or [f"{len(rules)} rules"])


def c09_gates(root, rep, agents):
    files = sorted(glob.glob(os.path.join(root, ".claude/docs/gates/*.md")))
    if not files:
        rep.add("C09", "NOT ASSESSED", "review gates", ["no .claude/docs/gates/*.md"])
        return
    probs, owners = [], {}
    for p in files:
        gid = os.path.basename(p)[:-3]
        t = read(p)
        rel = os.path.relpath(p, root)
        m = re.search(r"^\*\*Agent\*\*:\s*`([a-z0-9-]+)`", t, re.M)
        if not m:
            probs.append(f"{rel}: no **Agent**: line")
        elif m.group(1) not in agents:
            probs.append(f"{rel}: agent `{m.group(1)}` does not exist")
        else:
            owners[gid] = m.group(1)
        v = re.search(r"^\*\*Verdicts\*\*:\s*(.+)$", t, re.M)
        if not v or len([x for x in re.split(r"\s*/\s*", v.group(1)) if x.strip()]) < 2:
            probs.append(f"{rel}: **Verdicts** line missing or has fewer than two words")
        if "NOT ASSESSED" not in t:
            probs.append(f"{rel}: does not say when to answer NOT ASSESSED")
    for n, a in agents.items():
        sec = section(a["body"], "## Gate Verdict Format")
        listed = set(re.findall(r"`([A-Z][A-Z0-9-]+)`", sec or ""))
        for g in sorted(listed):
            if g not in owners:
                probs.append(f"{a['path']}: lists gate `{g}`, which has no file")
            elif owners[g] != n:
                probs.append(f"{a['path']}: lists gate `{g}`, owned by `{owners[g]}`")
        for g, o in owners.items():
            if o == n and g not in listed:
                probs.append(f"{a['path']}: owns gate `{g}` but its Gate Verdict Format does not list it")
    idx = os.path.join(root, ".claude/docs/gates.md")
    if os.path.exists(idx):
        it = read(idx)
        for g in owners:
            if f"`{g}`" not in it:
                probs.append(f".claude/docs/gates.md does not list `{g}`")
    rep.add("C09", "FAIL" if probs else "PASS", "gates: one existing owner each, verdict words, NOT ASSESSED, indexed",
            probs or [f"{len(files)} gates"])


def c10_catalog(root, rep):
    p = os.path.join(root, ".claude/docs/workflow-catalog.json")
    if not os.path.exists(p):
        rep.add("C10", "NOT ASSESSED", "workflow catalog", ["file missing"])
        return
    try:
        cat = json.loads(read(p))
    except ValueError as e:
        rep.add("C10", "FAIL", "workflow-catalog.json parses", [str(e)])
        return
    probs, ids, pids = [], set(), [ph.get("id") for ph in cat.get("phases", [])]
    if not pids:
        probs.append("no phases")
    for ph in cat.get("phases", []):
        nxt = ph.get("next")
        if nxt is not None and nxt not in pids:
            probs.append(f"phase {ph.get('id')}: next {nxt!r} is not a phase")
        for s in ph.get("steps", []):
            sid = s.get("id")
            if sid in ids:
                probs.append(f"duplicate step id {sid}")
            ids.add(sid)
            cmd = s.get("command")
            if cmd:
                sk = cmd.lstrip("/").split()[0]
                if not os.path.exists(os.path.join(root, ".claude/skills", sk, "SKILL.md")):
                    probs.append(f"step {sid}: command {cmd} has no skill")
            tpl = s.get("template")
            if tpl and not os.path.exists(os.path.join(root, tpl)):
                probs.append(f"step {sid}: template {tpl} does not exist")
            if s.get("required") and not (s.get("artifact") or {}).get("glob"):
                probs.append(f"step {sid}: required but names no artifact glob")
    rep.add("C10", "FAIL" if probs else "PASS", "catalog: phases link, commands and templates exist",
            probs or [f"{len(pids)} phases, {len(ids)} steps"])


def c11_config(root, rep):
    p = os.path.join(root, "project.yaml")
    if not os.path.exists(p):
        rep.add("C11", "NOT ASSESSED", "project.yaml", ["missing"])
        return
    try:
        mini_yaml.load(p)
    except mini_yaml.MiniYamlError as e:
        rep.add("C11", "FAIL", "project.yaml is in the mini-YAML subset", [str(e)])
        return
    r = subprocess.run([sys.executable, os.path.join(root, ".claude/scripts/resolve_config.py"), "--validate"],
                       capture_output=True, text=True, env={**os.environ, "STUDIO_ROOT": root})
    notes = [l for l in r.stdout.splitlines() if l.startswith("notes:") and l != "notes: none"]
    rep.add("C11", "FAIL" if notes or r.returncode else "PASS", "project.yaml parses and every value is valid",
            notes or ["resolve_config.py --validate: no notes"])


def c12_proposal(root, rep, proposal):
    if not proposal:
        rep.add("C12", "NOT ASSESSED", "proposal coverage", ["no --proposal given; coverage not checked"])
        return
    try:
        bp = json.loads(read(proposal))
    except (OSError, ValueError) as e:
        rep.add("C12", "NOT ASSESSED", "proposal coverage", [f"{proposal}: {e}"])
        return
    mp = os.path.join(root, ".claude/docs/studio-manifest.json")
    deferred = set()
    if os.path.exists(mp):
        deferred = set(json.loads(read(mp)).get("deferred", []))
    probs = []

    def want(kind, ident, path):
        if f"{kind}:{ident}" in deferred:
            return
        if not os.path.exists(os.path.join(root, path)):
            probs.append(f"{kind} {ident}: {path} neither generated nor listed as deferred")

    for r in bp.get("roles", []):
        want("role", r["id"], f".claude/agents/{r['id']}.md")
    for s in bp.get("skills", []):
        want("skill", s["name"], f".claude/skills/{s['name']}/SKILL.md")
    for r in bp.get("rules", []):
        want("rule", r["id"], f".claude/rules/{r['id']}.md")
    for g in bp.get("gates", []):
        want("gate", g["id"], f".claude/docs/gates/{g['id']}.md")
    for a in bp.get("artifacts", []):
        want("artifact", a["id"], f".claude/docs/templates/{a['id']}.md")
    rep.add("C12", "FAIL" if probs else "PASS", "every proposal item is generated or listed as deferred",
            probs or [f"deferred: {len(deferred)}"])


# --- C13: agent-facing Markdown is written for an agent arriving cold
# (see the skill's references/writing-for-agents.md). Budgets are per reading moment.
BUDGETS = {"CLAUDE.md": 150, "agent": 400, "skill": 500, "rule": 120}
DESC_WORDS = 80
COLD_PHRASES = re.compile(r"\b(as discussed|as mentioned (?:above|earlier|before)|see above|mentioned earlier|"
                          r"the above|previous conversation|earlier in (?:the|this) conversation|as we said)\b", re.I)
PLACEHOLDERS = re.compile(r"\{\{[^}]*\}\}|\[TBD\]|\[CHOOSE[^\]]*\]|\bTODO\b")


def agent_facing(root):
    """(kind, path) for every agent-facing Markdown file. Templates keep their [fields] on purpose."""
    out = []
    if os.path.exists(os.path.join(root, "CLAUDE.md")):
        out.append(("CLAUDE.md", os.path.join(root, "CLAUDE.md")))
    out += [("agent", p) for p in sorted(glob.glob(os.path.join(root, ".claude/agents/*.md")))]
    out += [("skill", p) for p in sorted(glob.glob(os.path.join(root, ".claude/skills/*/SKILL.md")))]
    out += [("rule", p) for p in sorted(glob.glob(os.path.join(root, ".claude/rules/*.md")))]
    out += [("doc", p) for p in sorted(glob.glob(os.path.join(root, ".claude/docs/**/*.md"), recursive=True))
            if "/templates/" not in p.replace(os.sep, "/")]
    out += [("template", p) for p in sorted(glob.glob(os.path.join(root, ".claude/docs/templates/*.md")))]
    return out


def c13_agent_readable(root, rep):
    files = agent_facing(root)
    if not files:
        rep.add("C13", "NOT ASSESSED", "agent-facing Markdown is written for agents", ["no agent-facing files found"])
        return
    probs = []
    for kind, p in files:
        rel = os.path.relpath(p, root)
        text = read(p)
        fm, body = front_matter(text)
        n = len(text.splitlines())
        if kind in BUDGETS and n > BUDGETS[kind]:
            probs.append(f"{rel}: {n} lines, over the {BUDGETS[kind]}-line budget for a {kind} — move detail to a "
                         "file it points to")
        if kind in ("agent", "skill"):
            d = fm.get("description", "")
            if len(d.split()) > DESC_WORDS:
                probs.append(f"{rel}: description is {len(d.split())} words (budget {DESC_WORDS}); it is always in "
                             "context")
        if kind == "skill" and "Use when" not in fm.get("description", ""):
            probs.append(f"{rel}: description does not say `Use when …` — the session cannot tell when to load it")
        if kind == "agent" and section(body, "### When You Are Spawned") is None:
            probs.append(f"{rel}: no `### When You Are Spawned` section — a cold agent is not told what to read "
                         "or return")
        if kind == "skill" and not re.search(r"^## Return\s*$", body, re.M):
            probs.append(f"{rel}: no `## Return` section — the caller cannot parse what it returns")
        lines = [l for l in body.splitlines() if l.strip()]
        for i, l in enumerate(lines[:-1]):
            h1 = re.match(r"^(#+)\s", l)
            h2 = re.match(r"^(#+)\s", lines[i + 1])
            if h1 and h2 and len(h2.group(1)) <= len(h1.group(1)):
                probs.append(f"{rel}: section {l.strip()!r} is empty — an agent reading it gets no instruction")
        for m in COLD_PHRASES.finditer(body):
            probs.append(f"{rel}: '{m.group(0)}' assumes context a spawned agent does not have")
        if kind != "template":
            for m in PLACEHOLDERS.finditer(body):
                probs.append(f"{rel}: placeholder {m.group(0)!r} left in agent-facing text")
    rep.add("C13", "FAIL" if probs else "PASS",
            "agent-facing Markdown: budgets, trigger descriptions, spawn/return sections, no cold-context phrases or "
            "placeholders", probs or [f"{len(files)} files checked"])


CHECKS = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13"]


def run(root: str, proposal: str | None = None, only: list[str] | None = None) -> Report:
    rep = Report()
    agents = load_agents(root)
    table = {
        "C01": lambda: c01_files(root, rep), "C02": lambda: c02_settings(root, rep),
        "C03": lambda: c03_hooks(root, rep), "C04": lambda: c04_agents(root, rep, agents),
        "C05": lambda: c05_hierarchy(root, rep, agents), "C06": lambda: c06_models(root, rep, agents),
        "C07": lambda: c07_skills(root, rep, agents), "C08": lambda: c08_rules(root, rep),
        "C09": lambda: c09_gates(root, rep, agents), "C10": lambda: c10_catalog(root, rep),
        "C11": lambda: c11_config(root, rep), "C12": lambda: c12_proposal(root, rep, proposal),
        "C13": lambda: c13_agent_readable(root, rep),
    }
    for cid in CHECKS:
        if only and cid not in only:
            rep.add(cid, "NOT ASSESSED", "skipped by --only", [])
            continue
        try:
            table[cid]()
        except Exception as e:  # a crashed check is not a pass
            rep.add(cid, "NOT ASSESSED", "check crashed", [f"{e.__class__.__name__}: {e}"])
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=os.environ.get("STUDIO_ROOT") or os.path.abspath(os.path.join(HERE, "..", "..")))
    ap.add_argument("--proposal")
    ap.add_argument("--only")
    a = ap.parse_args(argv)
    rep = run(os.path.abspath(a.root), a.proposal, a.only.split(",") if a.only else None)
    rep.print()
    return {"PASS": 0, "FAIL": 1, "NOT ASSESSED": 3}[rep.verdict()]


if __name__ == "__main__":
    sys.exit(main())
