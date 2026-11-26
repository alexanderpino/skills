# Proposal — HR Payroll Studio

> Rendered from `proposal.json` by `proposal.py render`. Edit the JSON, never this file.

**Domain:** HR & payroll back-office software  
**Goal:** internal tool  
**Generate:** mvp · **Default rigor:** minimal

## 1. Domain overview

A studio for building and maintaining HR and payroll back-office software: specs and versioned payroll rules first, test-first implementation, compliance review and user acceptance before release. (Test fixture — its sources are placeholders.)

## 2. Concept mapping (studio building block → this domain)

| Building block | Here | Claims |
|---|---|---|
| Design document per module | Functional specification per module | C002 |
| Configurable parameters and calculations | Payroll rule catalog with effective dates / configurable parameters | C003 |
| Product authority (director) | product-director | C001 |
| Delivery authority (director) | delivery-director | C001 |
| User acceptance evidence | UAT report | C005 |
| Stack table | stacks.tsv | USER: fixture |

## 3. Roster

```
product-director (director)
  business-analysis-lead (lead)
    business-analyst (specialist)
    payroll-rules-specialist (specialist)
  compliance-lead (lead)
technical-director (director)
  lead-engineer (lead)
    backend-engineer (specialist)
    integration-engineer (specialist)
    data-migration-specialist (specialist)  [later]
delivery-director (director)
  qa-lead (lead)
    qa-tester (specialist)
```

### `product-director` — Product Director (director)

Owns the product vision, scope and the final word on business rules and priorities.

- **Reports to:** the user
- **Delegates to:** `business-analysis-lead`, `compliance-lead`
- **Implements specs from:** none
- **Escalation targets:** the user when a business rule conflicts with a legal obligation, the budget or the agreed scope
- **Sibling coordination:** none
- **Coordinates with:** `technical-director` for trade-offs between scope and technical risk; `delivery-director` for release scope and dates
- **Gates owned:** `PD-SPEC-REVIEW`
- **Owns:** `docs/product-vision.md`
- **Skills preloaded:** none · **Model:** opus/high · **Workflow:** question-first
- **Responsibilities:** Set and guard the product vision and non-goals; Arbitrate conflicts between business rules; Approve functional specs through PD-SPEC-REVIEW
- **Must not:** Write code or tests; Approve a rule change that compliance has rejected
- **Claims:** C001

### `technical-director` — Technical Director (director)

Owns architecture, technology choices and technical risk across the product.

- **Reports to:** the user
- **Delegates to:** `lead-engineer`
- **Implements specs from:** none
- **Escalation targets:** the user when an architecture decision changes cost, risk or a commitment made to the business
- **Sibling coordination:** none
- **Coordinates with:** `product-director` for scope versus technical risk; `delivery-director` for technical blockers to a release
- **Gates owned:** `TD-ADR-REVIEW`
- **Owns:** `docs/architecture/`
- **Skills preloaded:** none · **Model:** opus/high · **Workflow:** question-first
- **Responsibilities:** Decide the architecture and record it as ADRs; Review ADRs through TD-ADR-REVIEW; Own technical risk and the stack choice
- **Must not:** Change business rules; Merge code without the lead engineer's review
- **Claims:** C001

### `delivery-director` — Delivery Director (director)

Owns planning, release readiness and the propagation of changes across roles.

- **Reports to:** the user
- **Delegates to:** `qa-lead`
- **Implements specs from:** none
- **Escalation targets:** the user when a release date, budget or quality bar cannot be met
- **Sibling coordination:** none
- **Coordinates with:** `product-director` for release scope; `technical-director` for technical readiness
- **Gates owned:** `DD-RELEASE-READINESS`
- **Owns:** `production/`
- **Skills preloaded:** none · **Model:** opus/medium · **Workflow:** question-first
- **Responsibilities:** Plan increments and track risks; Coordinate cross-role change propagation; Decide release readiness through DD-RELEASE-READINESS
- **Must not:** Decide business rules or architecture; Mark a release ready with open blocking defects
- **Claims:** C001

### `business-analysis-lead` — Business Analysis Lead (lead)

Leads requirements work: functional specs, rule catalogs and stories.

- **Reports to:** `product-director`
- **Delegates to:** `business-analyst`, `payroll-rules-specialist`
- **Implements specs from:** none
- **Escalation targets:** `product-director` when two specs conflict or scope is unclear
- **Sibling coordination:** `compliance-lead` for regulatory constraints on requirements; `lead-engineer` for feasibility of a requirement
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `docs/specs/`
- **Skills preloaded:** functional-spec · **Model:** opus/high · **Workflow:** question-first
- **Responsibilities:** Assign spec and rule work to analysts; Keep requirements traceable to stories and tests; Break approved specs into stories
- **Must not:** Write production code; Approve its own specs — that is PD-SPEC-REVIEW's job
- **Claims:** C002

### `lead-engineer` — Lead Engineer (lead)

Leads implementation: code architecture, standards, review and assignment to engineers.

- **Reports to:** `technical-director`
- **Delegates to:** `backend-engineer`, `integration-engineer`, `data-migration-specialist`
- **Implements specs from:** `business-analysis-lead`
- **Escalation targets:** `technical-director` when an ADR is needed or two ADRs conflict
- **Sibling coordination:** `business-analysis-lead` for spec ambiguities; `qa-lead` for testability
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `src/`, `docs/architecture/`
- **Skills preloaded:** architecture-decision · **Model:** opus/high · **Workflow:** implementation
- **Responsibilities:** Define module boundaries and coding standards; Review all code; Assign stories to engineers
- **Must not:** Change a business rule without the analysts; Skip tests for rule code
- **Claims:** C001

### `qa-lead` — QA Lead (lead)

Owns test strategy, UAT and the quality gates.

- **Reports to:** `delivery-director`
- **Delegates to:** `qa-tester`
- **Implements specs from:** none
- **Escalation targets:** `delivery-director` when quality blocks a release
- **Sibling coordination:** `lead-engineer` for testability and defects; `business-analysis-lead` for acceptance criteria
- **Coordinates with:** none
- **Gates owned:** `QL-UAT-SIGNOFF`
- **Owns:** `tests/`, `production/qa/`
- **Skills preloaded:** uat-report · **Model:** sonnet/high · **Workflow:** question-first
- **Responsibilities:** Write the test strategy; Run UAT with business users; Sign off through QL-UAT-SIGNOFF
- **Must not:** Fix product code; Sign off with failing acceptance tests
- **Claims:** C005

### `compliance-lead` — Compliance Lead (lead)

Owns regulatory and privacy requirements and reviews rule changes for compliance.

- **Reports to:** `product-director`
- **Delegates to:** none
- **Implements specs from:** none
- **Escalation targets:** `product-director` when a business demand conflicts with a legal requirement
- **Sibling coordination:** `business-analysis-lead` for regulatory input to specs
- **Coordinates with:** none
- **Gates owned:** `CL-RULE-COMPLIANCE`
- **Owns:** `docs/compliance/`
- **Skills preloaded:** business-rules · **Model:** opus/high · **Workflow:** question-first
- **Responsibilities:** Maintain the regulatory obligations register; Review rule catalogs through CL-RULE-COMPLIANCE; Define personal-data handling rules
- **Must not:** Give legal advice beyond the sourced obligations; Approve a rule without its effective date
- **Personal Data:** Minimise personal data in every spec; Every access to salary data is audit-logged
- **Claims:** C004

### `business-analyst` — Business Analyst (specialist)

Writes functional specifications and acceptance criteria with the business.

- **Reports to:** `business-analysis-lead`
- **Delegates to:** none
- **Implements specs from:** none
- **Escalation targets:** `business-analysis-lead` when a requirement is contested
- **Sibling coordination:** `payroll-rules-specialist` for calculations inside a spec
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `docs/specs/`
- **Skills preloaded:** functional-spec · **Model:** sonnet/medium · **Workflow:** question-first
- **Responsibilities:** Interview stakeholders and draft functional specs; Write testable acceptance criteria
- **Must not:** Decide scope; Write code
- **Claims:** C002

### `payroll-rules-specialist` — Payroll Rules Specialist (specialist)

Models payroll calculations as a versioned rule catalog with effective dates.

- **Reports to:** `business-analysis-lead`
- **Delegates to:** none
- **Implements specs from:** none
- **Escalation targets:** `business-analysis-lead` when a rule's source is unclear; `compliance-lead` when a rule may conflict with legislation
- **Sibling coordination:** `business-analyst` for rules referenced by specs
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `docs/specs/rules/`
- **Skills preloaded:** business-rules · **Model:** sonnet/medium · **Workflow:** question-first
- **Responsibilities:** Write every rule with formula, inputs, effective date and source; Provide worked examples for tests
- **Must not:** Invent a statutory rate — write NOT SOURCEABLE instead
- **Rule Versioning:** Every rule has an effective-from date; Rules are never edited in place; a change is a new version
- **Claims:** C003

### `backend-engineer` — Backend Engineer (specialist)

Implements stories: domain logic, persistence and APIs, test-first for rules.

- **Reports to:** `lead-engineer`
- **Delegates to:** none
- **Implements specs from:** `business-analyst`, `payroll-rules-specialist`
- **Escalation targets:** `lead-engineer` when an interface or architecture question; `payroll-rules-specialist` when a rule is ambiguous
- **Sibling coordination:** `integration-engineer` for contracts with external systems
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `src/`
- **Skills preloaded:** dev-story · **Model:** sonnet/medium · **Workflow:** implementation
- **Responsibilities:** Implement stories against their acceptance criteria; Write unit tests first for every rule
- **Must not:** Hardcode a rate or threshold; Log personal data
- **Claims:** C001

### `integration-engineer` — Integration Engineer (specialist)

Builds interfaces to banks, tax authorities and time-tracking systems.

- **Reports to:** `lead-engineer`
- **Delegates to:** none
- **Implements specs from:** `business-analyst`
- **Escalation targets:** `lead-engineer` when an external contract changes
- **Sibling coordination:** `backend-engineer` for internal interfaces
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `src/integrations/`
- **Skills preloaded:** dev-story · **Model:** sonnet/medium · **Workflow:** implementation
- **Responsibilities:** Implement and version external interfaces; Write contract tests
- **Must not:** Store credentials in the repository
- **Claims:** C001

### `qa-tester` — QA Tester (specialist)

Writes test cases and executes them, including UAT scripts.

- **Reports to:** `qa-lead`
- **Delegates to:** none
- **Implements specs from:** none
- **Escalation targets:** `qa-lead` when a defect's severity is disputed
- **Sibling coordination:** `backend-engineer` for defect reproduction
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `tests/`
- **Skills preloaded:** uat-report · **Model:** sonnet/medium · **Workflow:** question-first
- **Responsibilities:** Write test cases from acceptance criteria; Record UAT results as evidence
- **Must not:** Change acceptance criteria
- **Claims:** C005

### `data-migration-specialist` — Data Migration Specialist (specialist)

Plans and verifies migration of employee and payroll history from legacy systems.

- **Reports to:** `lead-engineer`
- **Delegates to:** none
- **Implements specs from:** none
- **Escalation targets:** `lead-engineer` when migration needs a schema change
- **Sibling coordination:** none
- **Coordinates with:** none
- **Gates owned:** none
- **Owns:** `docs/migration/`
- **Skills preloaded:** migration-plan · **Model:** sonnet/medium · **Workflow:** question-first
- **Responsibilities:** Write the migration plan; Reconcile migrated balances
- **Must not:** Migrate production data without a rehearsal
- **Claims:** C006

## 4. Workflow phases

### discovery — Discovery (next: requirements)

| Step | Command | Owner | Required | From workflow | Artifact | Claims |
|---|---|---|---|---|---|---|
| vision Product vision | — | `product-director` | yes | minimal | docs/product-vision.md | C001 |

### requirements — Requirements (next: architecture)

| Step | Command | Owner | Required | From workflow | Artifact | Claims |
|---|---|---|---|---|---|---|
| specs Functional specs | /functional-spec | `business-analyst` | yes | minimal | docs/specs/*.md | C002 |
| rules Rule catalogs | /business-rules | `payroll-rules-specialist` | yes | minimal | docs/specs/rules/*.md | C003 |

### architecture — Architecture (next: build)

| Step | Command | Owner | Required | From workflow | Artifact | Claims |
|---|---|---|---|---|---|---|
| adrs Architecture decisions | /architecture-decision | `lead-engineer` | yes | standard | docs/architecture/adr-*.md | USER: ADRs from standard rigor |

### build — Build (next: acceptance)

| Step | Command | Owner | Required | From workflow | Artifact | Claims |
|---|---|---|---|---|---|---|
| stories Stories | /create-stories | `business-analysis-lead` | yes | minimal | production/stories/*.md | C002 |
| implement Implement stories | /dev-story | `backend-engineer` | no | minimal | — | C001 |

### acceptance — Acceptance (next: end)

| Step | Command | Owner | Required | From workflow | Artifact | Claims |
|---|---|---|---|---|---|---|
| uat User acceptance testing | /uat-report | `qa-lead` | yes | minimal | production/qa/uat-*.md | C005 |

## 5. Artifacts and templates

| Id | Name | Path | Owner | Sections | Claims |
|---|---|---|---|---|---|
| product-vision | Product Vision | `docs/product-vision.md` | `product-director` | Problem; Users; Goals; Non-goals; Success measures | C001 |
| functional-spec | Functional Specification | `docs/specs/<module>.md` | `business-analyst` | Overview; Users and Roles; Detailed Rules; Data; Edge Cases; Dependencies; Configurable Parameters; Acceptance Criteria | C002 |
| rule-catalog | Payroll Rule Catalog | `docs/specs/rules/<area>.md` | `payroll-rules-specialist` | Rules; Formulas; Effective Dates; Sources; Worked Examples | C003 |
| adr | Architecture Decision Record | `docs/architecture/adr-NNNN-<slug>.md` | `lead-engineer` | Status; Context; Options; Decision; Consequences | USER: record architecture decisions as ADRs |
| story | Story | `production/stories/<id>.md` | `business-analysis-lead` | Story; Acceptance Criteria; Spec References; Test Evidence | C002 |
| uat-report | UAT Report | `production/qa/uat-<date>.md` | `qa-lead` | Scope; Participants; Results; Defects; Sign-off | C005 |
| migration-plan | Data Migration Plan | `docs/migration/plan.md` | `data-migration-specialist` | Sources; Mapping; Rehearsals; Reconciliation | C006 |

## 6. Skills

| Skill | Owner | Produces | Gates | Verdicts | Claims |
|---|---|---|---|---|---|
| /functional-spec | `business-analyst` | functional-spec | PD-SPEC-REVIEW | COMPLETE / PARTIAL | C002 |
| /business-rules | `payroll-rules-specialist` | rule-catalog | CL-RULE-COMPLIANCE | COMPLETE / PARTIAL | C003 |
| /architecture-decision | `lead-engineer` | adr | TD-ADR-REVIEW | ACCEPTED / PROPOSED | USER: keep ADRs |
| /create-stories | `business-analysis-lead` | story | — | COMPLETE / PARTIAL | C002 |
| /dev-story | `backend-engineer` | — | — | DONE / BLOCKED | C001 |
| /uat-report | `qa-lead` | uat-report | QL-UAT-SIGNOFF | ACCEPTED / CONCERNS / REJECTED | C005 |
| /migration-plan | `data-migration-specialist` | migration-plan | — | COMPLETE / PARTIAL | C006 |

Baseline skills generated from the skeleton: /start, /next-step, /gate-check, /project-settings.

## 7. Path-scoped rules

- **payroll-rules-code** (`src/**/payroll/**`, `src/main/java/**/payroll/**`; owner `lead-engineer`): Every rate, threshold and bracket comes from versioned configuration with an effective date; Every rule has unit tests built from the catalog's worked examples; Money uses a decimal type, never floating point — C003
- **personal-data** (`src/**`; owner `compliance-lead`): Never log personal data or salary values; Every read of salary data goes through the audited access layer — C004
- **tests** (`tests/**`, `src/test/**`; owner `qa-lead`): Tests are deterministic: no wall-clock time, no random seeds without a fixed value; Test data is synthetic — never production personal data — C004

## 8. Stack table

| Stack | Code root | Test root | Build | Test | Run | Claims |
|---|---|---|---|---|---|---|
| Java-Spring | `src/main/java` | `src/test/java` | ./mvnw -q package | ./mvnw -q test | ./mvnw spring-boot:run | USER: fixture stack |
| DotNet | `src` | `tests` | dotnet build | dotnet test | dotnet run --project src | USER: fixture stack |
| TypeScript-Node | `src` | `tests` | npm run build | npm test | npm start | USER: fixture stack |

## 9. Review gates

| Gate | Owner | Phase | Lean | Verdicts | Trigger | Claims |
|---|---|---|---|---|---|---|
| PD-SPEC-REVIEW | `product-director` | requirements | yes | APPROVE / CONCERNS / REJECT | A functional spec is drafted or revised | C002 |
| CL-RULE-COMPLIANCE | `compliance-lead` | requirements | no | COMPLIANT / CONCERNS / NON-COMPLIANT | A rule catalog is written or changed | C003, C004 |
| TD-ADR-REVIEW | `technical-director` | architecture | yes | APPROVE / CONCERNS / REJECT | An ADR is proposed | USER: keep ADR review |
| DD-RELEASE-READINESS | `delivery-director` | build | no | READY / CONCERNS / NOT READY | Leaving the build phase | C005 |
| QL-UAT-SIGNOFF | `qa-lead` | acceptance | yes | ACCEPT / CONCERNS / REJECT | UAT is complete | C005 |

## 10. Hooks

session-start, validate-commit, validate-write, validate-read, log-agent

## 11. Rigor modes

Default `minimal`. `minimal` → workflow minimal, docs terse, QA minimal, review solo; `standard` → standard, balanced, standard, lean; `full` → full, thorough, full, full.

## 12. Scope

Generate: **mvp**. Deferred (not generated): artifact:migration-plan, role:data-migration-specialist, role:lead-engineer, skill:migration-plan

## 13. Open questions

- Which country's payroll legislation is in scope first?
