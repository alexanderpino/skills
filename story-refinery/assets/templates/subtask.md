<!-- FALLBACK RENDERING. bundle.json is the source of truth; emit.py produces this
     view automatically. Use this template only when you cannot run the scripts. -->

# {S-id} — [{repo}] {Verb} {object}

Parent: {KEY} · Covers: {AC ids} · Depends on: {S-ids or —} · Est: {days}d
Kind: feature | test | docs | migration | spike | enabling | rollout

## For the developer
<!-- ≤ 80 words. What changes, the one thing that is easy to get wrong, and the
     boundary with neighbouring subtasks. Assume shared context. -->

## Done when
- [ ] `{command}` → exit 0
- [ ] {behavioural assertion, specific enough to write the test from}

---

<!-- AGENT-BRIEF v1 BEGIN -->
```json
{
  "objective": "",
  "repo": "",
  "branch_hint": "",
  "read_first": [{"path": "", "why": ""}],
  "entry_points": [{"path": "", "line": 0, "symbol": "", "why": ""}],
  "change_surface": [{"path": "", "role": "modify"}],
  "contracts_must_not_break": [{"path": "", "note": ""}],
  "conventions": [{"rule": "", "evidence": "path:line"}],
  "done_when": [
    {"type": "command", "cmd": "", "expect": "exit 0"},
    {"type": "assertion", "text": ""}
  ],
  "forbidden": [],
  "out_of_scope": [],
  "rollback": {"flag": "", "note": ""},
  "context_budget_hint": "read_first only; do not index the repo",
  "provenance": []
}
```
<!-- AGENT-BRIEF v1 END -->
