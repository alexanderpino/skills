---
id: EP-NNN              # house ID scheme if one exists; else EP-NNN
title: <short epic title — the outcome, not the solution>
status: draft           # draft | ready | in-progress | done | rejected
level: software         # enterprise | solution | software (where the value lands)
updated: <YYYY-MM-DD>
owner: <product owner>
format: default         # 'house' once conformed to the org's style; 'default' = this template
realizes-capabilities: []   # EA capability id(s) this epic advances, if traced that far up
satisfies: []           # PRD functional driver(s) F.xx delivered under this epic
priority: <must|should|could|won't>   # or the house scheme (MoSCoW/WSJF/…)
---

# EP-NNN — <title>

> **Adapt to the house format first.** If the org already groups work into epics a certain
> way (a Jira epic, an Azure DevOps feature, a label), detect and conform to it
> (`references/business-analysis.md` §2). This default is only for when none exists.
> An epic is a **large outcome** delivered over weeks–months; it is the parent of several
> features (`F.xx`) and user stories (`US-NNN`).

## Outcome
**So that** <the business/user outcome this epic exists to achieve>.
One paragraph: the problem and the value. Keep it solution-free.

## Scope
- **In scope:** <what this epic covers>
- **Out of scope:** <what it explicitly does not>

## Traceability
| Up — capability | Functional drivers (features) | Down — stories |
|---|---|---|
| <capability id/name> | F.xx, F.yy (PRD §4) | US-001, US-002, … |

Quality expectations under this epic reference the PRD quality drivers (`Q.xx`) — do not
re-specify them here.

## Epic-level acceptance (definition of done for the epic)
The epic is done when its stories' acceptance criteria are met and:
- [ ] <measurable outcome / KPI that confirms the epic delivered its value>
- [ ] <e.g. the relevant Q.xx scenario passes its means of verification>

## Notes / open questions
Assumptions and anything the given inputs left unanswered (record as a visible gap, don't
invent an answer).
