---
paths:
  - "src/**/payroll/**"
  - "src/main/java/**/payroll/**"
---

# Payroll Rule Code

Owner: `lead-engineer`. Applies to every file matching the paths above.

- Every rate, threshold and bracket comes from versioned configuration with an effective date
- Every rule has unit tests built from the catalog's worked examples
- Money uses a decimal type, never floating point
