# Directory Structure — HR Payroll Studio

```text
/
├── CLAUDE.md                 # Master configuration
├── project.yaml              # Project config — stack, modes, stage (source of truth)
├── .claude/                  # Agents, skills, hooks, rules, docs, scripts
├── <code root>/              # Source code — THE PATH IS STACK-SPECIFIC, see below
├── docs/                     # Specs, architecture (ADRs), studio research record
│   ├── specs/                # Functional specs and the documents the workflow names
│   ├── architecture/         # ADRs
│   └── studio-research/      # The ledger and proposal this studio was generated from
├── tests/                    # Test suites
├── production/               # Sprints, releases, QA evidence, session state
│   ├── session-state/        # active.md — the session checkpoint (gitignored)
│   └── session-logs/         # Agent audit trail (gitignored)
└── studio-tests/             # Self-tests for the studio itself
```

## The code root is stack-specific

| `stack.name` | Code root | Test root |
|---|---|---|
| Java-Spring | `src/main/java` | `src/test/java` |
| DotNet | `src` | `tests` |
| TypeScript-Node | `src` | `tests` |

Rows come from `.claude/docs/stacks.tsv`; `stack.code_root` and `stack.test_root` in `project.yaml` override them. Resolve before writing any source file:
`python3 .claude/scripts/resolve_config.py --keys stack.code_root,stack.test_root`.

## Where each artifact lives

| Artifact | Path | Owner |
|---|---|---|
| Product Vision | `docs/product-vision.md` | `product-director` |
| Functional Specification | `docs/specs/<module>.md` | `business-analyst` |
| Payroll Rule Catalog | `docs/specs/rules/<area>.md` | `payroll-rules-specialist` |
| Architecture Decision Record | `docs/architecture/adr-NNNN-<slug>.md` | `lead-engineer` |
| Story | `production/stories/<id>.md` | `business-analysis-lead` |
| UAT Report | `production/qa/uat-<date>.md` | `qa-lead` |

Deferred (in the proposal, not generated — no template and no owner agent exist yet): Data Migration Plan.
