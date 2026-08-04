# Operability — SLOs, error budgets, and recovery targets

A quality scenario promises behaviour; **operations has to observe and enforce that
promise**. The bridge is the SLO: the *response measure* of an operational `Q.xx`
scenario, restated as a target over a measured indicator. Reliability targets are
architecture inputs, not ops afterthoughts — you don't build multi-region
active-active for a 99% target, and each extra nine multiplies cost. Grounded in the
Google SRE discipline (Beyer et al., *Site Reliability Engineering*, 2016, ch. 4;
*The Site Reliability Workbook*, 2018) for the SLI/SLO/error-budget mechanics, and in
the international standards for what they measure and promise: **ISO/IEC 25010:2023**
**reliability** (availability, faultlessness, fault tolerance, recoverability) and
**performance efficiency** name the qualities; **ISO/IEC 25023** (SQuaRE quality
measures) is the measurement model an SLI instantiates; **ISO/IEC 20000-1** (IT
service management — service level management) governs the SLA side; **ISO 22301**
and **ISO/IEC 27031** ground the recovery targets (below).

## The three terms (use them precisely)

- **SLI — service level indicator.** A measured ratio of good events to total events
  over a window: successful requests / all requests, requests under 200 ms / all
  requests. It is the *means of verification* of the quality scenario, running in
  production.
- **SLO — service level objective.** The target for an SLI over a period:
  "99.9% of requests succeed, rolling 30 days." This is the `Q.xx` **response
  measure**, operationalised. (An SLA is an SLO with contractual penalties — a
  business document under **ISO/IEC 20000-1** service level management;
  the architecture works to the SLO.)
- **Error budget.** `1 − SLO` — the failure the target *permits* (99.9% ⇒ 43.8
  min/month). It turns reliability into a spendable resource: budget left → ship;
  budget burned → freeze features, spend on reliability. This is the mechanism that
  stops "as reliable as possible", which is unpayable.

## Q.xx → SLO — the translation is mechanical

| Quality scenario part | Becomes |
|---|---|
| Artifact + stimulus | what the SLI counts (which endpoint/flow, which events) |
| Response measure | the SLO target + window |
| Means of verification | the SLI implementation (metrics query) + alerting on burn rate |
| Environment | which SLO applies (normal vs degraded operation may differ) |

Rules:
- **Derive the SLO from the driver, not from ambition.** The `Q.xx` says what the
  business needs; setting 99.99% when the driver justifies 99.9% buys nothing and
  costs a redundancy tier. The quality/utility tree (PRD §5) is where that gets argued.
- **A reliability target that dictates topology is an ADR.** "99.95% availability ⇒
  multi-AZ, not multi-region" is a decision with a cost side — record it
  (`satisfies: [Q.xx]`), and let the FinOps matrix (HLD §9) carry its price.
- **Guard SLOs with fitness functions** where CI can check them (load-test
  thresholds, synthetic probes) — `automation.md` §4; production burn-rate alerts
  cover the rest.

## Recovery — RTO/RPO are recoverability response measures

For any stateful system, state the disaster targets as part of the operability row:
**RTO** (recovery time objective — how long until restored) and **RPO** (recovery
point objective — how much data loss is tolerable). The terms come from business
continuity management — **ISO 22301** (BCMS requirements) and **ISO/IEC 27031**
(ICT readiness for business continuity), where they are derived from a business
impact analysis, not chosen by engineering taste. Architecturally they are ISO 25010
*recoverability* scenarios and they dictate the backup/replication design the same
way availability dictates topology: RPO ≈ 0 means synchronous replication, not
nightly backups. Verified by a restore drill, not by the existence of backups. If
the organisation runs a BCMS, the system's targets must trace to it — a `C.xx`
constraint, not a local decision.

## Observability — how the SLIs exist at all

The design must state how the system is observed: metrics, logs, traces, and where
they land. Prefer **OpenTelemetry** as the vendor-neutral instrumentation standard
so the choice of backend stays reversible. One sentence per pillar in HLD §7 is
enough — the *SLIs* are the part that must be concrete.

## Where each piece lands

| Artifact | Carries |
|---|---|
| **PRD §5** | the operational `Q.xx` scenarios (response measure = the target) |
| **HLD §7 (operability)** | the SLI/SLO table, error-budget policy, RTO/RPO, observability approach |
| **HLD §6 (deployment)** | the topology the SLOs dictate |
| **ADR** | any reliability-driven structural choice and its cost trade-off |
| **CI** | fitness functions / load thresholds guarding the measurable ones |

Out of scope for the architecture docs: runbooks, on-call rotas, incident process.
Those are operations documents — link to them from HLD §7 if they exist; don't
write them here.
