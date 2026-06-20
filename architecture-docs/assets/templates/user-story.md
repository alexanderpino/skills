---
id: US-NNN              # house ID scheme if one exists (e.g. PROJ-123); else US-NNN
title: <short story title>
status: draft           # draft | ready | in-progress | done | rejected
level: software         # enterprise | solution | software (where the value lands)
updated: <YYYY-MM-DD>
owner: <product owner / BA>
format: default         # 'house' once conformed to the org's style; 'default' = this template
epic: <epic id/name>    # parent epic/feature
satisfies: [<F.xx>]     # PRD functional driver(s) this story delivers
realizes-capabilities: []   # EA capability id(s), if traced that far up
ac-style: gherkin       # gherkin | checklist — match the house style
estimate: <points / size>   # use the team's unit (story points, T-shirt, …)
priority: <must|should|could|won't>   # or the house scheme (MoSCoW/WSJF/…)
---

# US-NNN — <title>

> **Adapt to the house format first.** If the organisation already writes stories a certain
> way (Gherkin `.feature` files, a Jira/issue template, a specific role taxonomy or DoD),
> detect it and rewrite this story in *that* format (`references/business-analysis.md` §2).
> This default (Connextra + INVEST + Gherkin) is only for when no house style exists — and
> once chosen, save it as the reusable house template.

## Story
**As a** <specific role>
**I want** <goal / capability, free of solution detail>
**so that** <benefit / why it matters>.

## Context / notes
The conversation behind the card: assumptions, constraints, links to the PRD driver
(`F.xx`), designs, and any open questions. Keep solutioning out — that lives in the SD/ADR.

## Acceptance criteria
> Testable, true/false conditions — the minimum for this story to be accepted (BABOK 10.1).
> Cover the happy path **and** key edge/negative cases. Use the house `ac-style`.

### Gherkin (if `ac-style: gherkin`)
```gherkin
Scenario: <happy path>
  Given <context>
  When  <action>
  Then  <expected outcome>

Scenario: <edge / error case>
  Given <context>
  When  <action>
  Then  <expected handling>
```

### Checklist (if `ac-style: checklist`)
- [ ] <single testable condition>
- [ ] <error / edge condition>
- [ ] <non-functional expectation → reference Q.xx, don't re-specify>

## INVEST self-check
Independent · Negotiable · Valuable · Estimable · Small · Testable — reshape or split if any
fails (`business-analysis.md` §3).

## Definition of Done
Use the team's DoD. Default: AC met & demoed · tests automated & green · SD/ADR updated if
the design changed · reviewed · merged · deployed to <env>.
