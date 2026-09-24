---
id: ADR-0012
title: Size the Timefold worker pool from measured load and a bounded solve time
status: proposed
level: software
date: 2026-09-11
derivation: forward
deciders: [team-scheduling]
tags: [capacity, queueing, timefold, slo]
affects: [scheduling-engine, worker-pool]
satisfies: [Q.03]
---

# ADR-0012: Size the Timefold worker pool from measured load and a bounded solve time

## Status
Proposed

## Context
We need to size the worker pool for the new shift scheduling engine against `Q.03`:
*p99 end-to-end processing time < 5 minutes at peak load.*

Two figures come from the pilot:

- Peak arrival rate $\lambda = 10$ schedules per minute ($0.167\ \text{s}^{-1}$).
- Mean solve time $S = 120$ s, measured over 340 pilot runs.

Offered load is therefore $E = \lambda S = 20$ Erlangs — twenty units of concurrent solving
capacity merely to keep up, before any queueing. Timefold solving is CPU-bound and
single-threaded per solver, so a unit here is a **core**, not a thread; 30 threads on a
16-core task would be $c \approx 16$, not $c = 30$.

The pilot data also settles the question that decides the entire calculation: **solve time is
not exponentially distributed**, because the solver terminates on a configured time budget
rather than on convergence. That distinction is not academic. Under a naive M/M/c reading with
a 120 s mean, service time *alone* would have a p99 of $-120\ln(0.01) \approx 553$ s ≈ 9.2
minutes — `Q.03` would be unreachable at any pool size, and adding workers could not fix it,
because queueing was never the binding constraint. The target is achievable only because the
service time is bounded by construction.

## Decision
We will provision **30 solver cores** and cap the solver's termination budget at **3.5 minutes**
(210 s).

Sizing: $\rho = E/c = 20/30 = 67\%$. Erlang C is used here as a deliberately *conservative*
estimate: queueing delay scales roughly with $(1 + C_s^2)/2$ relative to the exponential case,
so a service time whose coefficient of variation is below 1 — which a budget-capped solver
should have — queues less than the figures below. That $C_s$ must be computed from the
measured solve times rather than assumed. On the Erlang C figures, $P_{wait} = 2.5\%$, the mean
queueing delay is $0.3$ s and the p99 queueing delay is $11$ s, so the p99 budget reads 210 s of
bounded solve time plus ≤ 11 s of queueing ≈ 3.7 minutes — inside the 5-minute target.

We reject running the pool at 85–90% utilization to save cores: at $c = 30$ that costs 90 s
(85%) to 154 s (90%) of p99 queueing delay, against the 90 s of slack the 3.5-minute solve cap
leaves in a 5-minute budget. 85% exhausts that slack exactly; 90% overruns it by 64 s. The
utilization ceiling here follows from `Q.03`, not from a rule of thumb.

## Consequences

**Positive**
- The tail is controlled by the solve-time cap, which is the only lever that actually bounds
  it; the pool then only has to keep queueing small.
- A 25% arrival spike ($\rho \to 83\%$) raises p99 queueing to ~77 s, giving ~4.8 minutes
  total — still inside the target.

**Negative / costs / risks**
- Capping the solver at 3.5 minutes trades solution quality for predictability. The pilot
  showed score improvement flattening after ~3 minutes, but production instances are larger,
  so this must be re-measured before rollout.
- Spike headroom is thin and non-linear: a 50% arrival spike puts $\rho$ at 100% and queueing
  delay grows without bound. Autoscaling must therefore trigger on **queue depth**, not on
  average CPU, which lags the cliff.
- 30 dedicated cores is 50% above the 20 that offered load strictly requires — that margin is
  the FinOps price of the tail guarantee (HLD §9).

**Assumptions to verify (`methods.md` §10)**
- **Arrivals are assumed Poisson, and this is both unverified and doubtful.** Schedules are
  produced around planning deadlines, so arrivals are probably bursty, which would push
  queueing delay above every Erlang C figure quoted here. Verification: fit the inter-arrival
  distribution on one month of production timestamps before relying on the headroom above.
- Mean solve time comes from the pilot, not from production. Re-derive $E$ once production
  instance sizes are known.

**Confirmation**
- A load test at $\lambda = 10$/min holding p99 < 5 minutes, run as a fitness function in CI.
- A production SLI on end-to-end processing time, alerting on error-budget burn.