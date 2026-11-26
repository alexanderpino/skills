# Agent Roster — HR Payroll Studio

Three tiers, as in a real delivery organisation: directors set direction, leads own a discipline, specialists do the work. The table is read by `check_template.py` (C05); every row must match the agent file's **Reports to**.

```
product-director  (director)
  business-analysis-lead  (lead)
    business-analyst  (specialist)
    payroll-rules-specialist  (specialist)
  compliance-lead  (lead)
technical-director  (director)
  lead-engineer  (lead)
    backend-engineer  (specialist)
    integration-engineer  (specialist)
delivery-director  (director)
  qa-lead  (lead)
    qa-tester  (specialist)
```

| Role | Tier | Reports to | Title |
|---|---|---|---|
| `product-director` | director | user | Product Director |
| `technical-director` | director | user | Technical Director |
| `delivery-director` | director | user | Delivery Director |
| `business-analysis-lead` | lead | `product-director` | Business Analysis Lead |
| `lead-engineer` | lead | `technical-director` | Lead Engineer |
| `qa-lead` | lead | `delivery-director` | QA Lead |
| `compliance-lead` | lead | `product-director` | Compliance Lead |
| `business-analyst` | specialist | `business-analysis-lead` | Business Analyst |
| `payroll-rules-specialist` | specialist | `business-analysis-lead` | Payroll Rules Specialist |
| `backend-engineer` | specialist | `lead-engineer` | Backend Engineer |
| `integration-engineer` | specialist | `lead-engineer` | Integration Engineer |
| `qa-tester` | specialist | `qa-lead` | QA Tester |

Deferred (in the proposal, not generated yet): `data-migration-specialist`.
