# Checker reference (C01–C13)

Part of Phase 4 — Validate: `validate.py` runs this checker as V23. This file says what
each check proves and what it cannot; `references/validation.md` is the stage itself.

## The checker

```bash
python3 scripts/check_template.py <target>       # runs the target's own copy, with --proposal
```

Verdict: `FAIL > NOT ASSESSED > PASS` (exit 1 / 3 / 0). Each check prints its evidence.

| Check | Proves | Cannot prove |
|---|---|---|
| C01 | the required files exist | that their content is right |
| C02 | `settings.json` parses; every hook command points at an existing script; the deny list covers `rm -rf`, force push, `reset --hard`, `.env` | that Claude Code loads it (only a session started in the target does) |
| C03 | every hook passes `bash -n` (NOT ASSESSED without bash) | that the hook behaves correctly at runtime |
| C04 | every agent has the full frontmatter, every required section, all six Delegation Map labels, one **Reports to** | that its prose is good |
| C05 | **the hierarchy**: roster ↔ agent files agree; every **Reports to** exists and sits in a higher tier (directors → the user); **Delegates to** equals exactly the roles reporting there; escalation / sibling / coordination targets exist; no cycles; everyone reaches a director | that the org design is wise |
| C06 | `agent-models.yaml` lists exactly the agents with the same model and effort | — |
| C07 | each skill: name = folder, description, a `NOT ASSESSED` verdict, asks "May I write" if it can write; preloaded skills exist | that the skill's steps work |
| C08 | each rule has `paths:` and bullets | that the globs match real code |
| C09 | each gate has one existing owner, ≥2 verdict words, says when to answer NOT ASSESSED, is listed by its owner and in `gates.md` | the quality of the gate prompt |
| C10 | catalog phases link; commands map to skills; templates exist; required steps have globs | — |
| C11 | `project.yaml` is in the mini-YAML subset and every value is valid | — |
| C12 | every proposal item is generated or listed as deferred | — |
| C13 | agent-facing Markdown is written for agents: length budgets per reading moment (`CLAUDE.md` 150, agent 400, skill 500, rule 120 lines), descriptions ≤ 80 words and skills say `Use when`, every agent has `### When You Are Spawned` and every skill `## Return`, no cold-context phrases ("as discussed", "see above"), no leftover placeholders | that the prose is clear — the reviewers judge that against `writing-for-agents.md` |

The covered sets are **derived from disk** (every agent file, every skill folder, every
gate file) — an item cannot dodge a check by being missing from a list.

## The checker has been watched fail

`tests/test_scripts.py` generates the fixture studio and then breaks it one property at a
time — a wrong **Reports to**, a missing delegate, a missing section, an unknown escalation
target, an orphan agent, model drift, an unlisted gate, a skill without NOT ASSESSED, a
dangling catalog command, a missing or broken hook, a removed deny rule, an invalid config
value, a missing proposal item — and asserts each turns the verdict to FAIL. If you change
a check, add or update its mutation test and watch it fail before trusting it.

```bash
python3 -m unittest discover -s <skill>/tests
```

## The studio's own tests

```bash
cd <target> && python3 -m unittest discover -s studio-tests -p 'test_*.py'
```

They run the checker, the resolver and `artifact_check.py` inside the generated studio.

## What remains NOT ASSESSED until a person runs it

- That Claude Code, started in `<target>`, loads the hooks, the deny list and the agents
  (an optional smoke: `claude -p "/next-step"` in the target, when the CLI is available).
- Whether the roles, gates and rules are *right* for the domain — the proposal's claims and
  the user's approval carry that; the checker only proves consistency.
- Every claim still `unverified` or `NOT SOURCEABLE` — list them on the handover card.
