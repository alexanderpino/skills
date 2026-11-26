#!/usr/bin/env python3
"""Generate a studio template from an APPROVED proposal. Never overwrites a file.

    generate.py TARGET --dry-run                 # list every file it would write, by layer
    generate.py TARGET --layer core              # write one layer (ask the user first)
    generate.py TARGET --layer all               # every layer, in order

Reads TARGET/.ssb/proposal.json and TARGET/.ssb/state.json. Refuses when:
  * the proposal is not approved, or changed since it was approved (state.py approved);
  * proposal.py check reports a structural FAIL;
  * the MVP cut would break the hierarchy (a generated role reporting to a deferred one,
    a generated item owned by a deferred role, a catalog step pointing at a deferred skill…).

Every file is reported on one line:
  WRITE <path>        written now
  WOULD-WRITE <path>  --dry-run
  SAME <path>         exists with identical content
  UPDATE <path>       exists, unchanged since this generator last wrote it, and the proposal now
                      renders it differently — replaced (e.g. the roster after adding a role)
  WOULD-UPDATE <path> the same, under --dry-run
  KEEP <path>         exists with DIFFERENT content that someone edited (or that predates the
                      manifest) — left alone; merge it by hand
"Never overwrite" means never overwrite a person's edit: the manifest records the sha256 of every
file the generator wrote, and only a file whose current hash still matches is updated.
.claude/docs/studio-manifest.json is merged and rewritten on every run.

Layers, in order: core, agents, skills, rules, templates, gates, catalog, hooks, tests.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
SKELETON = os.path.join(SKILL_ROOT, "assets", "skeleton")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKELETON, ".claude", "scripts"))
import proposal as proposalmod  # noqa: E402
import mini_yaml  # noqa: E402
import state as statemod  # noqa: E402

LAYERS = statemod.LAYERS
MAX_TURNS = {"director": 25, "lead": 20, "specialist": 15}


# ------------------------------------------------------------------ deferral

def deferred_set(bp: dict) -> set[str]:
    return set(proposalmod.deferred_items(bp))  # one rule, shared with what proposal.md shows the user


def cut_conflicts(bp: dict, d: set[str]) -> list[str]:
    out = []
    live = lambda k, i: f"{k}:{i}" not in d  # noqa: E731
    for r in bp["roles"]:
        if not live("role", r["id"]):
            continue
        if r["reports_to"] != "user" and not live("role", r["reports_to"]):
            out.append(f"role {r['id']} is generated but reports to deferred role {r['reports_to']}")
        for lab, key in (("escalation", "to"), ("siblings", "with"), ("coordinates_with", "with")):
            for e in r[lab]:
                if e[key] != "user" and not live("role", e[key]):
                    out.append(f"role {r['id']}: {lab} names deferred role {e[key]}")
        for t in r["implements_specs_from"]:
            if not live("role", t):
                out.append(f"role {r['id']}: implements specs from deferred role {t}")
        for s in r["skills"]:
            if s not in proposalmod.BASELINE_SKILLS and not live("skill", s):
                out.append(f"role {r['id']}: preloads deferred skill {s}")
    for kind, key, items in (("skill", "name", bp["skills"]), ("rule", "id", bp["rules"]),
                             ("gate", "id", bp["gates"]), ("artifact", "id", bp["artifacts"])):
        for it in items:
            if live(kind, it[key]) and not live("role", it["owner"]):
                out.append(f"{kind} {it[key]} is generated but its owner {it['owner']} is deferred")
    for s in bp["skills"]:
        if not live("skill", s["name"]):
            continue
        if s.get("produces") and not live("artifact", s["produces"]):
            out.append(f"skill {s['name']} produces deferred artifact {s['produces']}")
        for g in s.get("gates", []):
            if not live("gate", g):
                out.append(f"skill {s['name']} runs deferred gate {g}")
    for p in bp["phases"]:
        for st in p["steps"]:
            cmd = (st.get("command") or "").lstrip("/").split(" ")[0]
            if cmd and cmd not in proposalmod.BASELINE_SKILLS and not live("skill", cmd):
                out.append(f"catalog step {st['id']} runs deferred skill /{cmd}")
            if st.get("template") and not live("artifact", st["template"]):
                out.append(f"catalog step {st['id']} uses deferred template {st['template']}")
            if not live("role", st["owner"]):
                out.append(f"catalog step {st['id']} is owned by deferred role {st['owner']}")
    return out


# ------------------------------------------------------------------ renderers

def _read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _q(s: str) -> str:
    return '"' + str(s).replace('"', "'") + '"'


def _bt(xs) -> str:
    return ", ".join(f"`{x}`" for x in xs)


def authorities(bp: dict) -> dict:
    a = dict(bp["studio"].get("authorities") or {})
    dirs = [r["id"] for r in bp["roles"] if r["tier"] == "director"]
    for k in ("product", "technical", "delivery"):
        if a.get(k) not in dirs:
            a[k] = None
    return a


def render_agent(bp: dict, r: dict, d: set[str]) -> str:
    title, studio = r["title"], bp["studio"]["name"]
    tools = ", ".join(r["tools"])
    skills = [s for s in r["skills"] if s in proposalmod.BASELINE_SKILLS or f"skill:{s}" not in d]
    L = ["---", f"name: {r['id']}", f"description: {_q(title + ' — ' + r['description'])}",
         f"tools: {tools}", f"model: {r['model']}", f"effort: {r['effort']}",
         f"maxTurns: {MAX_TURNS[r['tier']]}", f"skills: [{', '.join(skills)}]", "memory: project", "---", "",
         f"You are the **{title}** in {studio}. {r['description']}", "",
         "### When You Are Spawned", "",
         "You start with no memory of the conversation that spawned you. Everything you need is in "
         "your brief and in the files it names.", "",
         "1. Read `production/session-state/active.md` if it exists — it is the current checkpoint.",
         "2. Read the documents your brief names, by section: Grep for `^#`, then Read with offset and limit.",
         "3. If the brief lacks an input you need, do not guess: say `NOT ASSESSED — <the missing input>` "
         "and stop, or ask in one round.",
         "4. Return, in this order: one line with the outcome (for a gate, the verdict token on line one); "
         "the files you wrote, as paths; decisions that need the user; anything NOT ASSESSED, with the reason.", "",
         "### Collaboration Protocol", "",
         ("**You are a collaborative consultant, not an autonomous decision-maker.** The user makes every "
          "decision; you bring structure, options and expertise.") if r["workflow"] == "question-first" else
         ("**You are a collaborative implementer, not an autonomous coder.** The user approves every "
          "architectural decision and every file change."), ""]
    if r["workflow"] == "question-first":
        L += ["#### Question-First Workflow", "",
              "1. **Understand the ask.** Read the relevant documents by section; ask every question you need "
              "in one round, each with a recommended answer.",
              "2. **Present options.** 2–4 options with trade-offs, sourced where the domain demands it, and "
              "your recommendation.",
              "3. **The user decides.** A skipped or dismissed question is not an answer — re-ask and wait.",
              "4. **Draft.** Show the draft (section by section for long documents).",
              "5. **Approval.** Ask \"May I write this to `<path>`?\" and write only on a yes.", ""]
    else:
        L += ["#### Implementation Workflow", "",
              "1. **Read the spec first.** Identify what is specified and what is ambiguous; flag deviations "
              "from the studio's standards before writing code.",
              "2. **Ask architecture questions** where the spec is silent, with a recommendation each.",
              "3. **Propose the approach** — files, responsibilities, interfaces, tests — before implementing.",
              "4. **Implement with transparency.** Stop and ask when the spec turns out to be ambiguous.",
              "5. **Approval.** Ask \"May I write this to `<paths>`?\"; a multi-file change is approved as one "
              "listed changeset.",
              "6. **Prove it works.** Tests first for business rules; run them and report the result, including "
              "anything NOT ASSESSED.", ""]
    L += ["#### Collaborative Mindset", "",
          "- Clarify before assuming — specs are never 100% complete.",
          "- Propose, don't impose — the user owns the decision.",
          "- Explain trade-offs openly, with sources for domain facts; write `NOT SOURCEABLE — <what>` "
          "instead of filling a gap from memory.",
          "- Flag deviations from specs, standards or regulation explicitly.",
          "- A check you could not run is reported as `NOT ASSESSED`, never as a pass.", "",
          "### Key Responsibilities", ""]
    L += [f"{i}. {x}" for i, x in enumerate(r["responsibilities"], 1)]
    L.append("")
    for sd in r["standards"]:
        L += [f"### {sd['heading']}", ""] + [f"- {x}" for x in sd["rules"]] + [""]
    gates = [g for g in proposalmod.gates_owned(bp, r["id"]) if f"gate:{g}" not in d]
    if gates:
        L += ["## Gate Verdict Format", "",
              f"Gates owned: {_bt(gates)}.", "",
              "When invoked through a gate, read the gate's file in `.claude/docs/gates/<ID>.md` first: its "
              "**Verdicts** line lists the only words you may return for that gate — or `NOT ASSESSED`, naming "
              "the input, when the gate names an input you were not given or could not read. A problem you did "
              "find still takes the gate's own word, and so does an artifact the calling skill reports as "
              "absent: a missing artifact is a finding, not a missing input.", "",
              "Begin your response with the verdict token on its own line:", "", "```",
              "[GATE-ID]: [a word from that gate's Verdicts line, or NOT ASSESSED]", "```", "",
              "Then give your full rationale below it. Never bury the verdict inside paragraphs — the calling "
              "skill reads the first line.", ""]
    L += ["### What This Agent Must NOT Do", ""] + [f"- {x}" for x in r["must_not"]]
    L += [f"- Write outside its own paths ({_bt(r['owns_paths'])}) without explicit delegation",
          "- Make a binding decision in another role's domain — consult, then escalate", "",
          "### Delegation Map", ""]
    L += [f"**Reports to**: {'the user' if r['reports_to'] == 'user' else '`' + r['reports_to'] + '`'}", ""]
    dl = [x for x in proposalmod.delegates_to(bp, r["id"]) if f"role:{x}" not in d]
    roles = proposalmod.role_by_id(bp)
    L += ["**Delegates to**:" + ("" if dl else " none"), ""]
    if dl:
        L += [f"- `{x}` for {roles[x]['title'].lower()} work" for x in dl] + [""]
    L += ["**Implements specs from**: " + (_bt(r["implements_specs_from"]) or "none"), ""]
    for label, key, why, items in (("Escalation targets", "to", "when", r["escalation"]),
                                   ("Sibling coordination", "with", "for", r["siblings"]),
                                   ("Coordinates with", "with", "for", r["coordinates_with"])):
        L += [f"**{label}**:" + ("" if items else " none"), ""]
        if items:
            L += [(f"- the user {why} {e[why]}" if e[key] == "user" else f"- `{e[key]}` {why} {e[why]}")
                  for e in items] + [""]
    return "\n".join(L).rstrip() + "\n"


def render_roster(bp: dict, d: set[str]) -> str:
    roles = [r for r in bp["roles"] if f"role:{r['id']}" not in d]
    L = [f"# Agent Roster — {bp['studio']['name']}", "",
         "Three tiers, as in a real delivery organisation: directors set direction, leads own a "
         "discipline, specialists do the work. The table is read by `check_template.py` (C05); every "
         "row must match the agent file's **Reports to**.", "", "```"]

    def tree(parent, depth):
        for r in roles:
            if r["reports_to"] == parent:
                L.append("  " * depth + f"{r['id']}  ({r['tier']})")
                tree(r["id"], depth + 1)
    tree("user", 0)
    L += ["```", "", "| Role | Tier | Reports to | Title |", "|---|---|---|---|"]
    for r in roles:
        rt = "user" if r["reports_to"] == "user" else f"`{r['reports_to']}`"
        L.append(f"| `{r['id']}` | {r['tier']} | {rt} | {r['title']} |")
    later = sorted(x.split(":", 1)[1] for x in d if x.startswith("role:"))
    if later:
        L += ["", f"Deferred (in the proposal, not generated yet): {_bt(later)}."]
    return "\n".join(L) + "\n"


def render_models(bp: dict, d: set[str]) -> str:
    data = {"agents": {r["id"]: {"model": r["model"], "effort": r["effort"]}
                       for r in bp["roles"] if f"role:{r['id']}" not in d}}
    return ("# Model and effort per agent. check_template.py (C06) checks every agent file agrees.\n"
            "# Change a row here AND in the agent's frontmatter.\n" + mini_yaml.dumps(data))


def render_coordination(bp: dict, d: set[str]) -> str:
    a = authorities(bp)
    dirs = [r["id"] for r in bp["roles"] if r["tier"] == "director" and f"role:{r['id']}" not in d]
    prod = f"`{a['product']}`" if a["product"] else "the director whose domain it is"
    tech = f"`{a['technical']}`" if a["technical"] else "the technical director"
    deliv = f"`{a['delivery']}`" if a["delivery"] else "the delivery director"
    return f"""# Agent Coordination Rules

Directors: {_bt(dirs)}. The full tree is `.claude/docs/agent-roster.md`.

1. **Vertical Delegation**: Directors delegate to leads, leads to specialists. Never skip a
   tier for a complex decision.
2. **Horizontal Consultation**: Agents at the same tier may consult each other but must not
   make binding decisions outside their domain.
3. **Conflict Resolution**: When two agents disagree, escalate to the shared parent. With no
   shared parent, escalate to {prod} for product and business-rule conflicts and to {tech}
   for technical conflicts. A conflict between directors goes to the user.
4. **Change Propagation**: When a change affects several domains, {deliv} coordinates the
   propagation and names every affected document.
5. **No Unilateral Cross-Domain Changes**: An agent never modifies files outside its own
   paths (its **What This Agent Must NOT Do** section) without explicit delegation.
6. **Read Documents by Section**: A brief names the sections an agent needs by heading.
   Grep for `^#`, then Read that range with offset and limit.
7. **Nothing Goes Upstream**: Never file or comment on an issue in a vendor or third-party
   repository. Draft it; the user submits it.

## Parallel Task Protocol

When a skill spawns several independent agents:

1. Issue every independent `Agent` call before waiting for any result.
2. Collect all results before a phase that depends on them.
3. A BLOCKED agent is surfaced at once — never silently skipped.
4. Always produce a partial report when some agents finish and others block.
"""


def render_dirs(bp: dict, d: set[str] | None = None) -> str:
    d = d or set()
    L = [f"# Directory Structure — {bp['studio']['name']}", "", "```text", "/",
         "├── CLAUDE.md                 # Master configuration",
         "├── project.yaml              # Project config — stack, modes, stage (source of truth)",
         "├── .claude/                  # Agents, skills, hooks, rules, docs, scripts",
         "├── <code root>/              # Source code — THE PATH IS STACK-SPECIFIC, see below",
         "├── docs/                     # Specs, architecture (ADRs), studio research record",
         "│   ├── specs/                # Functional specs and the documents the workflow names",
         "│   ├── architecture/         # ADRs",
         "│   └── studio-research/      # The ledger and proposal this studio was generated from",
         "├── tests/                    # Test suites",
         "├── production/               # Sprints, releases, QA evidence, session state",
         "│   ├── session-state/        # active.md — the session checkpoint (gitignored)",
         "│   └── session-logs/         # Agent audit trail (gitignored)",
         "└── studio-tests/             # Self-tests for the studio itself", "```", "",
         "## The code root is stack-specific", "",
         "| `stack.name` | Code root | Test root |", "|---|---|---|"]
    for s in bp["stacks"]:
        L.append(f"| {s['name']} | `{s['code_root']}` | `{s['test_root']}` |")
    L += ["", "Rows come from `.claude/docs/stacks.tsv`; `stack.code_root` and `stack.test_root` in "
          "`project.yaml` override them. Resolve before writing any source file:",
          "`python3 .claude/scripts/resolve_config.py --keys stack.code_root,stack.test_root`.", "",
          "## Where each artifact lives", "", "| Artifact | Path | Owner |", "|---|---|---|"]
    for a in bp["artifacts"]:
        if f"artifact:{a['id']}" in d:
            continue
        L.append(f"| {a['name']} | `{a['path']}` | `{a['owner']}` |")
    later = [a["name"] for a in bp["artifacts"] if f"artifact:{a['id']}" in d]
    if later:
        L += ["", "Deferred (in the proposal, not generated — no template and no owner agent exist yet): "
              + ", ".join(later) + "."]
    return "\n".join(L) + "\n"


def render_stacks(bp: dict) -> str:
    L = ["# Stack table: one row per supported stack. `-` means empty. Read by resolve_config.py.",
         "stack\tcode_root\ttest_root\tbuild\ttest\trun"]
    for s in bp["stacks"]:
        L.append("\t".join([s["name"], s["code_root"], s["test_root"], s.get("build") or "-",
                            s.get("test") or "-", s.get("run") or "-"]))
    return "\n".join(L) + "\n"


def render_project_yaml(bp: dict) -> str:
    first = bp["phases"][0]["id"] if bp["phases"] else None
    data = {"project": {"name": bp["studio"]["name"], "goal": bp["studio"].get("goal") or None, "stage": first},
            "modes": {"rigor": bp["rigor"]["default"]},
            "stack": {"name": None}}
    return ("# Team-wide studio config (mini-YAML subset: see .claude/scripts/mini_yaml.py).\n"
            "# Personal overrides (modes.review_mode, modes.automation) go in project.local.yaml.\n"
            "# Check after any edit: python3 .claude/scripts/resolve_config.py --validate\n"
            + mini_yaml.dumps(data))


def render_skill(bp: dict, s: dict) -> str:
    owner = s["owner"]
    art = next((a for a in bp["artifacts"] if a["id"] == s.get("produces")), None)
    verdicts = [v for v in s["verdicts"] if v != "NOT ASSESSED"]
    L = ["---", f"name: {s['name']}", f"description: {_q(s['description'])}",
         f"argument-hint: {_q(s.get('argument_hint') or '[no arguments]')}", "user-invocable: true",
         "allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Agent, "
         "Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)",
         "---", "", f"# /{s['name']}", "", s["description"], "",
         f"**Owner:** `{owner}` — for specialist depth, spawn it with the Agent tool "
         f"(subagent_type: `{owner}`) and pass the documents it needs by section.", "",
         "## Before you start", "",
         "Run `python3 .claude/scripts/resolve_config.py --keys modes.workflow,modes.docs_density,modes.review_mode,"
         "stack.name`. Read `production/session-state/active.md` if it exists. A `notes:` line is reported to "
         "the user, never ignored.", ""]
    for i, step in enumerate(s["steps"], 1):
        name = step["name"] if isinstance(step, dict) else step
        detail = step.get("detail") if isinstance(step, dict) else None
        # a heading with nothing under it gives an agent nothing to do: the step text is the instruction
        L += [f"## Phase {i} — {name}", "", (detail or f"{name.rstrip('.')}.") , ""]
    if art:
        L += ["## Output", "",
              f"`{art['path']}`, from the template `.claude/docs/templates/{art['id']}.md` "
              f"(sections: {'; '.join(x['heading'] if isinstance(x, dict) else x for x in art['sections'])}). "
              "Draft one section at a time; at `modes.docs_density: terse` keep each section to its essentials.", ""]
    gates = s.get("gates", [])
    if gates:
        L += ["## Review", "",
              f"Gates: {_bt(gates)}. With `modes.review_mode` `full` run every gate; `lean` only the gates "
              "marked `lean: yes` in `.claude/docs/gates.md`; `solo` none — and the report then says "
              "`Review: skipped — review_mode=solo`. Spawn each gate's owner (see `.claude/docs/gates.md`) with "
              "the gate file and the draft; read the verdict token on the first line of its answer.", ""]
    L += ["## Collaboration", "",
          "Ask every question in one round, each with a recommended answer. Show the draft before writing. "
          f"Ask \"May I write this to `{art['path'] if art else '<path>'}`?\" and write only on a yes. "
          "Then append one line to `production/session-state/active.md`.", "",
          "## Return", "",
          f"End with `{s['name'].upper()}: <verdict>` — one of {' / '.join(verdicts)} — or "
          "`NOT ASSESSED — <which input was missing or unreadable>`. A step that did not run is named in the "
          "report, never left out. Then name the one next step (`/next-step` decides when unsure).", ""]
    return "\n".join(L)


def render_rule(r: dict) -> str:
    L = ["---", "paths:"] + [f"  - {_q(p)}" for p in r["paths"]] + ["---", "",
         f"# {r.get('title') or r['id'].replace('-', ' ').title()}", "",
         f"Owner: `{r['owner']}`. Applies to every file matching the paths above.", ""]
    L += [f"- {x}" for x in r["rules"]]
    return "\n".join(L) + "\n"


def render_template(a: dict) -> str:
    L = [f"# {a['name']}: [Title]", "",
         f"> Template for `{a['path']}` · owner `{a['owner']}`. "
         + (a.get("purpose") or ""), "",
         "<!-- For the agent filling this in: keep every heading; replace each comment with the content it "
         "asks for; cite sources as ledger claim ids or write NOT SOURCEABLE — <what>. -->", "",
         "**Status**: Draft | In Review | Approved  ", "**Last updated**: [date]  ",
         "**Sources**: [ledger claim ids, documents, or `NOT SOURCEABLE — <what>`]", ""]
    for sec in a["sections"]:
        h = sec["heading"] if isinstance(sec, dict) else sec
        g = sec.get("guidance") if isinstance(sec, dict) else None
        L += [f"## {h}", "", f"<!-- {g or 'Write this section, or write N/A — <reason>.'} -->", ""]
    return "\n".join(L)


def render_gate(g: dict) -> str:
    return "\n".join([
        f"# {g['id']}", "",
        f"**Agent**: `{g['owner']}`  ",
        f"**Phase**: {g.get('phase') or '— (run by a skill, not a phase gate)'}  ",
        f"**Lean**: {'yes' if g.get('lean') else 'no'}  ",
        f"**Trigger**: {g['trigger']}  ",
        f"**Context to pass**: {g['context']}  ",
        f"**Verdicts**: {' / '.join(g['verdicts'])}", "",
        "Verdict words are ordered best first; the last is the failing word.", "",
        "## Prompt", "", g["prompt"], "",
        "## How to answer", "",
        f"Begin with `{g['id']}: <word>` on its own line, using only the words above — or "
        f"`{g['id']}: NOT ASSESSED` when an input this gate names was not given to you or could not be read; "
        "name that input. A problem you did find takes the gate's own word, and so does an artifact the "
        "calling skill reports as absent: a missing artifact is a finding, not a missing input.", ""])


def render_gates_index(bp: dict, d: set[str]) -> str:
    L = [f"# Review Gates — {bp['studio']['name']}", "",
         "Each gate is reviewed by one owning agent, which reads the gate file itself. `/gate-check` runs "
         "the gates of the phase being left; skills run the gates they name. Review mode decides which run: "
         "`full` all, `lean` only `lean: yes`, `solo` none (and the report says so).", "",
         "| Gate | Owner | Phase | Lean | Verdicts |", "|---|---|---|---|---|"]
    for g in bp["gates"]:
        if f"gate:{g['id']}" in d:
            continue
        L.append(f"| `{g['id']}` | `{g['owner']}` | {g.get('phase') or '—'} | {'yes' if g.get('lean') else 'no'} | "
                 f"{' / '.join(g['verdicts'])} |")
    return "\n".join(L) + "\n"


def render_catalog(bp: dict) -> str:
    phases = []
    for p in bp["phases"]:
        steps = []
        for s in p["steps"]:
            steps.append({"id": s["id"], "name": s["name"], "command": s.get("command"), "owner": s["owner"],
                          "required": bool(s.get("required")), "min_workflow": s.get("min_workflow", "minimal"),
                          "artifact": s.get("artifact"),
                          "template": f".claude/docs/templates/{s['template']}.md" if s.get("template") else None})
        phases.append({"id": p["id"], "name": p["name"], "next": p.get("next"), "steps": steps})
    return json.dumps({"schema": "studio-catalog/1", "phases": phases}, indent=2) + "\n"


def skeleton_files(bp: dict) -> list[tuple[str, str, str | bytes, bool]]:
    """(layer, relpath, content, executable) for every skeleton file."""
    d = deferred_set(bp)
    live_roles = [r for r in bp["roles"] if f"role:{r['id']}" not in d]
    dirs = [r for r in live_roles if r["tier"] == "director"]
    subs = {
        "{{STUDIO_NAME}}": bp["studio"]["name"], "{{SUMMARY}}": bp["studio"]["summary"],
        "{{DOMAIN}}": bp["studio"]["domain"], "{{ROLE_COUNT}}": str(len(live_roles)),
        "{{DIRECTORS}}": _bt(r["id"] for r in dirs),
        "{{STACK_NAMES}}": " / ".join(s["name"] for s in bp["stacks"]),
    }
    out = []
    for base, _, files in os.walk(SKELETON):
        for f in files:
            if f.endswith(".pyc") or "__pycache__" in base:
                continue
            src = os.path.join(base, f)
            rel = os.path.relpath(src, SKELETON)
            if rel == "gitignore.tmpl":
                rel_out = ".gitignore"
            else:
                rel_out = rel[:-5] if rel.endswith(".tmpl") else rel
            with open(src, encoding="utf-8") as fh:
                text = fh.read()
            if rel.endswith(".tmpl"):
                for k, v in subs.items():
                    text = text.replace(k, v)
            if rel.startswith(".claude/hooks/") or rel == ".claude/settings.json":
                layer = "hooks"
            elif rel.startswith(".claude/skills/"):
                layer = "skills"
            elif rel.startswith("studio-tests/"):
                layer = "tests"
            else:
                layer = "core"
            out.append((layer, rel_out, text, rel_out.endswith((".sh", ".py")) and "studio-tests" not in rel_out))
    return out


def plan(bp: dict, run_dir: str) -> list[tuple[str, str, str, bool]]:
    d = deferred_set(bp)
    files = skeleton_files(bp)
    add = lambda layer, rel, text, ex=False: files.append((layer, rel, text, ex))  # noqa: E731
    add("core", "project.yaml", render_project_yaml(bp))
    add("core", ".claude/docs/directory-structure.md", render_dirs(bp, d))
    add("core", ".claude/docs/stacks.tsv", render_stacks(bp))
    for f in ("proposal.json", "proposal.md"):
        p = os.path.join(run_dir, f)
        if os.path.exists(p):
            add("core", f"docs/studio-research/{f}", _read(p))
    rdir = os.path.join(run_dir, "research")
    if os.path.isdir(rdir):
        for f in sorted(os.listdir(rdir)):
            if f.startswith("."):
                continue
            p = os.path.join(rdir, f)
            if os.path.isfile(p):
                add("core", f"docs/studio-research/{f}", _read(p))
    for r in bp["roles"]:
        if f"role:{r['id']}" not in d:
            add("agents", f".claude/agents/{r['id']}.md", render_agent(bp, r, d))
    add("agents", ".claude/docs/agent-roster.md", render_roster(bp, d))
    add("agents", ".claude/agent-models.yaml", render_models(bp, d))
    add("agents", ".claude/docs/coordination-rules.md", render_coordination(bp, d))
    for s in bp["skills"]:
        if f"skill:{s['name']}" not in d:
            add("skills", f".claude/skills/{s['name']}/SKILL.md", render_skill(bp, s))
    for r in bp["rules"]:
        if f"rule:{r['id']}" not in d:
            add("rules", f".claude/rules/{r['id']}.md", render_rule(r))
    for a in bp["artifacts"]:
        if f"artifact:{a['id']}" not in d:
            add("templates", f".claude/docs/templates/{a['id']}.md", render_template(a))
    for g in bp["gates"]:
        if f"gate:{g['id']}" not in d:
            add("gates", f".claude/docs/gates/{g['id']}.md", render_gate(g))
    add("gates", ".claude/docs/gates.md", render_gates_index(bp, d))
    add("catalog", ".claude/docs/workflow-catalog.json", render_catalog(bp))
    return files


def write_manifest(target: str, bp: dict, run_dir: str, layers: list[str], dry: bool,
                   files: dict | None = None):
    p = os.path.join(target, ".claude/docs/studio-manifest.json")
    m = {}
    if os.path.exists(p):
        try:
            m = json.loads(_read(p))
        except ValueError:
            m = {}
    d = deferred_set(bp)
    gen = set(m.get("generated", []))
    for kind, key, items in (("role", "id", bp["roles"]), ("skill", "name", bp["skills"]),
                             ("rule", "id", bp["rules"]), ("gate", "id", bp["gates"]),
                             ("artifact", "id", bp["artifacts"])):
        layer = {"role": "agents", "skill": "skills", "rule": "rules", "gate": "gates", "artifact": "templates"}[kind]
        if layer in layers:
            for it in items:
                if f"{kind}:{it[key]}" not in d:
                    gen.add(f"{kind}:{it[key]}")
    m.update({"generated_by": "software-studio-builder", "proposal_sha256": statemod.proposal_hash(run_dir),
              "generated": sorted(gen), "deferred": sorted(d),
              "layers": sorted(set(m.get("layers", [])) | set(layers), key=LAYERS.index),
              "files": {**m.get("files", {}), **(files or {})}})
    if dry:
        print("WOULD-WRITE .claude/docs/studio-manifest.json (merged)")
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2)
        fh.write("\n")
    print("WRITE .claude/docs/studio-manifest.json (merged)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--layer", action="append", help="a layer, or `all`; repeatable")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    target = os.path.abspath(a.target)
    run_dir = os.path.join(target, ".ssb")
    ok, why = statemod.is_approved(run_dir)
    if not ok:
        print(f"REFUSED: {why}. Show the user proposal.md and record their approval with "
              f"`state.py approve {run_dir} --by user`.")
        return 2
    bp = proposalmod.load(run_dir)
    verdict, fail, _, _ = proposalmod.check(bp, os.path.join(run_dir, "research"))
    if fail:
        print("REFUSED: the proposal has structural failures:")
        for f in fail:
            print(f"  FAIL: {f}")
        return 2
    d = deferred_set(bp)
    conflicts = cut_conflicts(bp, d)
    if conflicts:
        print("REFUSED: the MVP cut breaks the proposal's links — defer these together or keep them:")
        for c in conflicts:
            print(f"  {c}")
        return 2
    layers = LAYERS if not a.layer or "all" in a.layer else [l for l in LAYERS if l in a.layer]
    unknown = [l for l in (a.layer or []) if l != "all" and l not in LAYERS]
    if unknown:
        print(f"unknown layer(s): {', '.join(unknown)}; layers are {', '.join(LAYERS)}")
        return 2
    counts = {"WRITE": 0, "WOULD-WRITE": 0, "UPDATE": 0, "WOULD-UPDATE": 0, "SAME": 0, "KEEP": 0}
    mp = os.path.join(target, ".claude/docs/studio-manifest.json")
    try:
        written = json.loads(_read(mp)).get("files", {}) if os.path.exists(mp) else {}
    except ValueError:
        written = {}
    new_hashes: dict[str, str] = {}
    for layer in layers:
        print(f"== layer {layer}")
        for (lay, rel, text, ex) in plan(bp, run_dir):
            if lay != layer:
                continue
            dest = os.path.join(target, rel)
            if os.path.exists(dest):
                cur = _read(dest)
                if cur == text:
                    tag = "SAME"
                    new_hashes[rel] = _sha(text)
                elif written.get(rel) == _sha(cur):
                    # untouched since we generated it: the proposal changed, not a person
                    tag = "WOULD-UPDATE" if a.dry_run else "UPDATE"
                    if not a.dry_run:
                        with open(dest, "w", encoding="utf-8") as fh:
                            fh.write(text)
                        new_hashes[rel] = _sha(text)
                else:
                    tag = "KEEP"
            elif a.dry_run:
                tag = "WOULD-WRITE"
            else:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(text)
                if ex:
                    os.chmod(dest, 0o755)
                tag = "WRITE"
                new_hashes[rel] = _sha(text)
            counts[tag] += 1
            print(f"{tag} {rel}" + ("  (exists with different content; left alone)" if tag == "KEEP" else ""))
        if not a.dry_run:
            statemod.main(["layer", run_dir, layer])
    write_manifest(target, bp, run_dir, layers, a.dry_run, new_hashes)
    print("SUMMARY: " + " ".join(f"{k}={v}" for k, v in counts.items()) + f" deferred={len(d)}")
    if counts["KEEP"]:
        print("NOTE: KEEP files were edited after generation (or predate the manifest) and were not updated — "
              "compare them with the proposal by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
