# Domain pack — business and administrative software

**Status: hypotheses, not facts.** Everything below is a starting point for the research
lanes. Nothing here may enter a proposal without a ledger claim behind it (or a `USER:`
decision). Names of standards and regimes are given so lanes know where to look; what each
one *requires* must be read in the primary source and quoted.

Covers: ERP (finance, procurement, inventory), CRM, HR and payroll, case management,
public-sector administration, billing and invoicing, internal line-of-business tools.

## Candidate roles (verify against job postings and org charts)

| Tier | Candidates | Usually owns |
|---|---|---|
| Director | product director (or product owner at small scale), technical director / architect, delivery director (programme or release manager) | vision and business-rule arbitration · architecture · plans, release readiness, change propagation |
| Lead | business-analysis lead, lead engineer, UX lead, QA lead, compliance or risk lead, data lead, release manager | specs and rules · code standards and review · design system · test strategy and UAT · obligations register · data model and migration · release process |
| Specialist | business analyst, process designer, business-rules specialist (e.g. payroll, tax, pricing), data modeler, backend engineer, frontend engineer, integration engineer, reporting / BI engineer, security engineer, QA tester, technical writer, data-migration specialist, DevOps engineer, platform specialist (a framework or a packaged-ERP platform) | the matching artifact or code area |

Questions for the `roles` lane: Where does business-rule authority sit — product or a
dedicated domain expert? Is compliance a reviewer (gate) or a co-author? Is there a
separate "functional consultant" role (common around packaged ERP platforms)?

## Candidate artifacts

Product vision · functional specification per module · business-process model ·
business-rule catalog / decision tables with effective dates · data dictionary ·
integration specification (per external system) · role and permission matrix (with
segregation of duties) · report specification · ADR · story with acceptance criteria ·
test plan · UAT report · data-migration plan and reconciliation report · release notes ·
operational runbook · obligations register.

## Candidate standards and regimes to research (scope by domain and jurisdiction)

| Area | Where to look | Likely effect on the studio |
|---|---|---|
| Requirements and analysis | IIBA BABOK Guide; ISO/IEC/IEEE 29148 | spec sections, traceability, BA roles |
| Process and decisions | OMG BPMN; OMG DMN | process-model and decision-table artifacts |
| Product quality | ISO/IEC 25010 | non-functional sections, review criteria |
| Service management | ITIL (AXELOS/PeopleCert) | release, change and incident steps after go-live |
| Data management | DAMA-DMBOK | data dictionary, data-lead role |
| Application security | OWASP ASVS, OWASP Top 10 | security rules, a security review gate |
| Accessibility | W3C WCAG | UI rules, a UX review criterion |
| Privacy | GDPR (EU) and national equivalents | personal-data rules, records of processing, retention, a compliance gate |
| Financial controls | SOX (US) and IT general controls; SOC 2 (AICPA); ISO/IEC 27001 | audit trail, segregation of duties, change-approval evidence |
| Sector-specific | e.g. HIPAA (health, US), PCI DSS (card data), e-invoicing standards (e.g. EN 16931 in the EU), national payroll and tax law | rule catalogs with effective dates and sources; `must_not` lines |

The `regulation` lane decides which apply — from the intake's jurisdiction and data — and
records a `not-sourceable` gap for anything it cannot read in a primary source.

## Candidate phases and gates

Discovery (vision) → requirements (specs, rules, process models; spec review, compliance
review) → architecture (ADRs; ADR review) → build (stories, test-first rules; release
readiness) → acceptance (UAT; UAT sign-off) → release and operate (release notes,
runbooks, change approval).

## Candidate stacks to research

General-purpose web stacks (e.g. Java/Spring, .NET, Python/Django, TypeScript/Node, Ruby on
Rails) and packaged platforms (e.g. open-source ERP frameworks, large commercial ERP and
CRM platforms, low-code platforms). For packaged platforms the code root and test layout
are platform-defined — the `stack` lane must read the platform's own developer docs.

## Failure modes worth a rule or a `must_not` (verify and source each)

- Floating-point money; rounding rules not specified per currency or jurisdiction.
- Rules edited in place instead of versioned with effective dates.
- Customising a packaged platform where configuration would do.
- Missing audit trail on changes to financial or personal data.
- Segregation-of-duties conflicts in the permission model.
- Personal data in logs, test fixtures or analytics.
- Data migration without rehearsal and reconciliation.
- Period-close and multi-entity / multi-currency edge cases left out of specs.
- Time zones and effective dates conflated.
