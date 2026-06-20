<!--
TEMPLATE — decision log. Copy to <root>/decisions/README.md.
One row per ADR, sorted by ID. Update on every ADR add or status change.
This table is read in full by agents to get the decision landscape in one pass,
so keep it accurate and terse.
-->
# Decision log

All architecture decisions, recorded as ADRs in [Nygård](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
format — one decision per file, `ADR-NNNN-slug.md`.

**Find decisions fast**
- By component: `grep -rl "affects:.*<component>" .`
- Accepted only: `grep -rl "^status: accepted" .`
- By driver: `grep -rl "satisfies:.*Q.01" .`

| ID | Title | Status | Date | Summary |
|----|-------|--------|------|---------|
| [ADR-0001](./ADR-0001-<slug>.md) | <title> | accepted | <YYYY-MM-DD> | <one line> |

<!-- Status values: proposed · accepted · rejected · deprecated · superseded.
     When an ADR is superseded, keep its row, set status, and link the successor
     in both files. Never delete a row. -->
