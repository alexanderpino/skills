# Intake — Phase 0

Ask **one round**, all questions together, each with its recommended answer first. Take any
answer the user's own words already gave and say so in one line instead of asking it again.
A skipped question is not an answer: re-ask it in plain text.

| # | Question | Options (recommended first) | Why it matters |
|---|---|---|---|
| 1 | **Domain** — what kind of software, for whom? | free text; offer 2–3 sharper readings if vague ("business software" → ERP finance / CRM / HR & payroll / case management) | Sets every research lane's query |
| 2 | **Users and buyers** | internal staff / business customers (B2B) / public / mixed | Shapes UX, support and acceptance roles |
| 3 | **Regulation** | "research it" (recommended) / named regimes (GDPR, SOX, HIPAA, PCI DSS, local payroll or tax law…) / none | Opens the `regulation` lane; never assume none |
| 4 | **Stacks** | "research the common ones" (recommended) / named stacks / one fixed stack | Fills `stacks.tsv`; a fixed stack narrows the `stack` lane |
| 5 | **Team shape** | small team, AI-heavy (recommended) / established org with existing roles / solo developer | Sizes the roster: solo → 6–8 roles, small → 10–15, org → mirror their org chart |
| 6 | **Default rigor** | `minimal` (recommended) / `standard` / `full` | Written to `project.yaml`; regulated domains often pick `standard` |
| 7 | **Generate** | MVP (recommended: ~10–12 agents, ~15 skills) / full proposal | `scope.generate`; MVP marks the rest `mvp: false` |
| 8 | **Target directory** | `./<slug>-studio` (recommended) / a path | Where `.ssb/` and the studio live; must not be inside this skill |
| 9 | **Material to read** | none / an existing codebase, docs or agent setup of theirs | Phase 1 reads it before researching |

Then:

```bash
python3 scripts/state.py init <target>/.ssb --domain "<domain>" --target <target>
python3 scripts/state.py intake <target>/.ssb --json '{"domain": "...", "users": "...", "regulation": "...",
  "stacks": "...", "team": "...", "rigor": "minimal", "generate": "mvp", "material": ["..."]}'
python3 scripts/state.py phase <target>/.ssb research
```

If `<target>/.ssb/state.json` already exists, **resume** — `state.py show` — and confirm
with the user before changing any answer already recorded.

## Sizing guidance

- A role earns its place by owning **decisions or paths** no other role owns.
- Three directors is the usual shape (product/business authority, technical authority,
  delivery authority); a solo or small studio may merge delivery into product.
- Every lead has at least one specialist reporting to it, or it is a specialist.
- Regulated domains almost always need a compliance or risk role at lead level with a
  review gate — but only the research decides which obligations it reviews against.
