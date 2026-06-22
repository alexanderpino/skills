---
id: conformance-checklist
title: LinkShort — ISO conformance checklist
status: current
level: software
updated: 2026-06-20
---

# ISO conformance checklist — LinkShort

## ISO/IEC/IEEE 42010:2022 — Architecture Description
| # | Required content | Status | Location |
|---|------------------|--------|----------|
| 1 | AD identification & overview | ✅ | AD.md §1 |
| 2 | Stakeholders identified | ✅ | AD.md §2 |
| 3 | Concerns identified | ✅ | AD.md §3 |
| 4 | Each concern framed by ≥ 1 viewpoint | ✅ | AD.md §3 ↔ §5 |
| 5 | Each stakeholder has ≥ 1 concern | ✅ | AD.md §2 ↔ §3 |
| 6 | Viewpoints defined | ✅ | AD.md §5 |
| 7 | Views, each governed by exactly one viewpoint | ✅ | AD.md §6 |
| 8 | View components conform to model kinds | ✅ | HLD/SD diagrams |
| 9 | Correspondences & rules recorded | ✅ | AD.md §7 |
| 10 | Known inconsistencies recorded | ✅ | AD.md §7 (none) |
| 11 | Decisions captured with rationale | ✅ | decisions/ADR-0001 |

## ISO/IEC 25010:2023 — product quality
| # | Item | Status | Location |
|---|------|--------|----------|
| 1 | Quality driver references a 25010 characteristic | ✅ | PRD §5 (security→confidentiality) |
| 2 | Objective response measure | ✅ | PRD §5 Q.01 |
| 3 | Quality/utility tree | ✅ | PRD §5 |

## ISO/IEC/IEEE 29148:2018 — requirements
| # | Item | Status | Location |
|---|------|--------|----------|
| 1 | Stable IDs | ✅ | B/F/Q, EP-001, US-001 |
| 2 | RFC 2119 keywords | ✅ | PRD §4 |
| 3 | Verifiable (means of verification) | ✅ | PRD §5; US-001 acceptance criteria |
| 4 | Traceability EP→F→US→AC→test | ✅ | EP-001 / US-001 / PRD §7 |

## Sign-off
- Audited by: team-platform on 2026-06-20
- Result: conformant
- Open gaps: none
