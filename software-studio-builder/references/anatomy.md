# Anatomy of a studio

What a studio is made of, which parts are reusable machinery, and which parts are the
domain content the research must supply. The skeleton in `assets/skeleton/` is the
machinery; the proposal is the content. Everything a studio needs is described here — no
other template is required.

## Layers

| Layer | What it is | In a generated studio | Machinery or content? |
|---|---|---|---|
| Master instructions | The file Claude Code loads first; imports the docs every session needs | `CLAUDE.md` (from `CLAUDE.md.tmpl`) importing directory structure and coordination rules | Machinery with domain text filled in |
| Config | One team-wide file, one personal override, a resolver that says where each value came from | `project.yaml` in a mini-YAML subset + `resolve_config.py` (stdlib): local → team → rigor fan-out → stack row → default | Machinery |
| Rigor | One dial that sets how much process every skill enforces | `modes.rigor` fans out to workflow, docs density, QA level, review mode (+ `modes.automation`, personal) | Machinery |
| Settings | Permissions and hook wiring | `.claude/settings.json`: deny `rm -rf`, force push, `reset --hard`, `git clean -f`, `sudo`, `.env` reads | Machinery |
| Hooks | Scripts Claude Code runs on events | `session-start`, `validate-commit`, `validate-write`, `validate-read`, `log-agent` — warn, never rewrite; only the read guard refuses, and says why | Machinery |
| Agents | Subagents in three tiers with explicit reporting lines | one file per proposal role; `agent-roster.md`; `agent-models.yaml` | **Content** (format is machinery) |
| Coordination | How agents delegate, consult and escalate | `coordination-rules.md`, rendered with the studio's directors as conflict authorities | Machinery with names |
| Collaboration protocol | Question → Options → Decision → Draft → Approval | `collaboration-protocol.md` (static) | Machinery |
| Skills | Slash commands, one per workflow step or review | 4 baseline (`/start`, `/next-step`, `/gate-check`, `/project-settings`) + the proposal's | Baseline machinery; the rest **content** |
| Rules | Coding standards that load by file path | one per proposal rule (`paths:` frontmatter + bullets) | **Content** |
| Templates | The skeleton of every document the workflow produces | one per proposal artifact | **Content** |
| Review gates | A named review, owned by one role, with fixed verdict words | one file per proposal gate + `gates.md` index | **Content** (format is machinery) |
| Workflow catalog | Phases, their steps, and the artifact each step leaves on disk | `workflow-catalog.json` + `artifact_check.py` | **Content** (format is machinery) |
| Stack table | Code root, test root and commands per supported stack | `stacks.tsv` | **Content** |
| Self-tests | Checks that the studio is internally consistent | `check_template.py` (13 checks) + `studio-tests/test_template.py` | Machinery |
| Session state | The checkpoint a session resumes from | `production/session-state/active.md`, read by `session-start.sh` | Machinery |

## The agent file, section by section

```
---
name, description, tools, model, effort, maxTurns, skills, memory
---
### When You Are Spawned                  what to read first, what to do without an input, what to return
### Collaboration Protocol
#### Question-First Workflow | Implementation Workflow
#### Collaborative Mindset
### Key Responsibilities
### <domain standards section(s)>          e.g. Rule Versioning, Personal Data
## Gate Verdict Format                     only for roles that own a gate
### What This Agent Must NOT Do
### Delegation Map
**Reports to**: `<role>` | the user
**Delegates to**: (bullets)                derived: who reports here
**Implements specs from**: `<role>`, …
**Escalation targets**: (bullets: `<role>` when <reason>)
**Sibling coordination**: (bullets: `<role>` for <topic>)
**Coordinates with**: (bullets: `<role>` for <topic>)
```

Why each part is there: the spawn section exists because a subagent starts cold — no
conversation, only its brief — so it must be told what to read and what shape to return; the protocol keeps the user in charge of every decision; the
standards sections carry the domain's hard rules into the agent that writes the code; the
**Must NOT** list is what stops a specialist from making a director's call; and the
Delegation Map makes the org chart executable — a skill spawns the owner, an agent knows
whom to ask and whom to escalate to, and the checker can prove the chart is a tree.

## Studio building blocks → what to research

Every studio needs a filler for each building block. Use the right-hand columns as prompts
for the research lanes, not as answers: each must be confirmed for the domain.

| Building block | Research question | Business / administrative example |
|---|---|---|
| Product vision | What does the product exist to do, for whom, and what is out of scope? | Product vision with goals and non-goals |
| Design document per module | What document defines a module's behaviour before it is built? | Functional spec per module (GL, AP, payroll run…) |
| Module map | How does the domain divide into modules or bounded contexts? | Module map |
| Configurable parameters and calculations | Which values and formulas change over time or by customer, and who owns them? | Rule catalog with effective dates; configuration tables |
| Data dictionary | What are the canonical entities and their owners? | Master data, canonical entities |
| Product authority (director) | Who has the final word on scope and business rules? | Product director / product owner |
| Technical authority (director) | Who decides architecture and technical risk? | Technical director / architect |
| Delivery authority (director) | Who plans, tracks and calls release readiness? | Delivery director / programme manager |
| Requirements roles | Who writes specs and rules with the business? | Business analyst, rules specialist, process designer |
| Experience roles | Who owns the UI, accessibility and the design system? | UX lead, UX designer |
| Content roles | Who writes help, documentation and in-product text? | Technical writer |
| Stack specialists | Which platforms need a specialist of their own? | Framework or packaged-platform specialist |
| User acceptance evidence | How do real users accept a release? | UAT report |
| Calculation verification | How are calculations and totals proven right? | Reconciliation, rule verification |
| Compliance and certification | Which external obligations must the software and process meet? | Regulatory compliance, audit readiness |
| Operations and change communication | What happens after release? | Release notes, change management, runbooks |
| Early prototype | What is the cheapest thing that shows the main workflow works? | Clickable prototype or walking skeleton |
| Stack table | Which stacks are used, with which code and test layout? | `stacks.tsv` |

## MVP subset vs. full

| Layer | MVP | Full |
|---|---|---|
| Agents | 10–12 (3 directors, 3–5 leads, rest specialists) | everything the research supports |
| Skills | 4 baseline + ~8–12 | one per workflow step and review |
| Rules | 3–6 | one per code area with distinct obligations |
| Templates | 6–10 | one per artifact |
| Gates | 4–8, one per phase transition that matters | one per decision a director signs |
| Phases | 4–6 | as researched |

Defer with `mvp: false` or `scope.later`; the generator refuses a cut that orphans
something, so deferred items travel together.
