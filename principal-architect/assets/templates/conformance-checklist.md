---
id: conformance-checklist
title: ISO conformance checklist
status: current
updated: <YYYY-MM-DD>
---

# ISO conformance checklist

Audit the architecture documentation against the required content of the standards
it claims to conform to. Mark each item ✅ (satisfied), ⚠️ (partial), or ❌ (missing),
and point to where it is satisfied. Re-run whenever a stakeholder, concern, view, or
significant decision is added. This is the gap-analysis step ISO conformance expects.

## ISO/IEC/IEEE 42010:2022 — required content of an Architecture Description

| # | Required content | Status | Location |
|---|------------------|--------|----------|
| 1 | AD identification & overview (EoI, scope, version, status) | | AD.md §1 |
| 2 | Stakeholders identified | | AD.md §2 |
| 3 | Concerns identified | | AD.md §3 |
| 4 | **Each concern is framed by ≥ 1 viewpoint** | | AD.md §3 ↔ §5 (CR.01) |
| 5 | **Each stakeholder has ≥ 1 concern** | | AD.md §2 ↔ §3 |
| 6 | Architecture viewpoints defined (concerns framed, model kinds) | | AD.md §5 |
| 7 | Architecture views present, **each governed by exactly one viewpoint** | | AD.md §6 (CR.02) |
| 8 | View components / models conform to their model kinds | | HLD / SD diagrams |
| 9 | Correspondences & correspondence rules recorded | | AD.md §7 |
| 10 | Known inconsistencies recorded (not hidden) | | AD.md §7 |
| 11 | Architecture decisions captured with rationale | | decisions/ (ADRs) |

A 42010-conformant AD must address **all** of the above. "Briefly" is acceptable;
"absent" is not.

## ISO/IEC 25010:2023 — product quality model

| # | Item | Status | Location |
|---|------|--------|----------|
| 1 | Quality requirements reference 25010:2023 characteristics/sub-characteristics | | PRD §5 |
| 2 | Each quality driver names the specific characteristic it targets | | PRD §5 |
| 3 | Each quality driver has an objective response measure | | PRD §5 |
| 4 | Quality/utility tree prioritises the scenarios | | PRD §5 |

The nine 25010:2023 characteristics: functional suitability · performance efficiency ·
compatibility · interaction capability · reliability · security · maintainability ·
flexibility · safety. (See `references/standards.md` for sub-characteristics.)

## ISO/IEC/IEEE 29148:2018 — requirements (PRD)

| # | Item | Status | Location |
|---|------|--------|----------|
| 1 | Each requirement has a unique stable ID | | PRD (B/F/Q.xx) |
| 2 | Requirements use RFC 2119 keywords (MUST/SHALL/SHOULD/MAY) | | PRD §4 |
| 3 | Each requirement is verifiable (has a means of verification) | | PRD §4–5 |
| 4 | Requirements are necessary, unambiguous, singular, feasible | | PRD review |
| 5 | Traceability requirement ↔ decision ↔ component | | satisfies:/affects: front-matter |

## Sign-off
- Audited by: <name> on <date>
- Result: <conformant / gaps listed below>
- Open gaps: <list or "none">
