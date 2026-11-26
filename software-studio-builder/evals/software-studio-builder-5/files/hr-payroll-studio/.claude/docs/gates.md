# Review Gates — HR Payroll Studio

Each gate is reviewed by one owning agent, which reads the gate file itself. `/gate-check` runs the gates of the phase being left; skills run the gates they name. Review mode decides which run: `full` all, `lean` only `lean: yes`, `solo` none (and the report says so).

| Gate | Owner | Phase | Lean | Verdicts |
|---|---|---|---|---|
| `PD-SPEC-REVIEW` | `product-director` | requirements | yes | APPROVE / CONCERNS / REJECT |
| `CL-RULE-COMPLIANCE` | `compliance-lead` | requirements | no | COMPLIANT / CONCERNS / NON-COMPLIANT |
| `TD-ADR-REVIEW` | `technical-director` | architecture | yes | APPROVE / CONCERNS / REJECT |
| `DD-RELEASE-READINESS` | `delivery-director` | build | no | READY / CONCERNS / NOT READY |
| `QL-UAT-SIGNOFF` | `qa-lead` | acceptance | yes | ACCEPT / CONCERNS / REJECT |
