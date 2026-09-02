---
type: Bibliography
title: Papers — architecture
description: "Sources for the architecture axis: graph evaluation, caching and invalidation, layering, and the driver fields a terrain graph carries."
tags: [bibliography, provenance, architecture]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Papers — architecture

The bibliography family for the architecture axis: how a node graph is executed, cached,
invalidated and kept resolution-independent. **The tier table and the two non-negotiable rules
live in `papers-flow.md`** and are not repeated here; read them before citing anything below.

⚠️ **This axis was grounded from scratch, and that is worth stating.** Its in-repo source,
`terrain-architect/references/14-graph-runtime.md`, is 425 lines of architecture prose carrying
**zero citations** — checked, no inline markers anywhere in the file. Distilling it would have
produced confident unsourced assertion, which is the failure mode this skill exists to prevent.
So the mechanisms below are grounded in the **incremental-computation and build-systems**
literature, which has studied exactly this problem for twenty years and which the terrain
literature does not cite. The mapping is not a metaphor: a node graph *is* a build system whose
keys are node outputs, and the design space is already mapped.

One tier decision recurs and is stated once: **a specification, a vendor documentation page or a
conference talk is graded `F`**, however authoritative. Microsoft's DirectX specifications are the
recurring case on this axis. Naming them is right; dressing them as peer review is not.

## Incremental evaluation and caching

- **alacarte** `P` — Mokhov, A., Mitchell, N. & Peyton Jones, S. (2018). *Build Systems à la
  Carte.* Proc. ACM Program. Lang. 2(ICFP), Article 79. — The decomposition this axis is built
  on: a build system is a **scheduler** (§4.1: topological, restarting, suspending) crossed with a
  **rebuilder** (§4.2: dirty bit, verifying traces, constructive traces, deep constructive
  traces). §2.3 defines **early cutoff**; §2.5 Table 1 classifies Make, Excel, Shake and Bazel by
  scheduler, minimality, cutoff and cloud support; §5.4 models Bazel, CloudBuild, Buck and Nix and
  closes by naming a suspending scheduler with constructive traces as the most desirable
  combination then unavailable.
- **adapton** `P` — Hammer, M.A. et al. (2014). *Adapton: Composable, Demand-Driven Incremental
  Computation.* PLDI 2014, Edinburgh. — Demand-driven incremental computation: results are
  recomputed lazily when *observed*, not eagerly when an input changes. §2 is the overview, §4.1
  the trace structure and propagation semantics.
- **acar2002** `P` — Acar, U.A., Blelloch, G.E. & Harper, R. (2002). *Adaptive Functional Programming.*
  POPL '02, Portland OR. — Change propagation as a language feature rather than an application
  concern; §6 proves the propagation sound. The ancestor of the whole self-adjusting-computation
  line that `adapton` continues.

## In-repo sources

These are artefacts in this repository rather than published work. They are `F` — a register or a
chapter is not peer review — but they are checkable, which a recollection is not.

- **ta_graph_runtime** `F` — `terrain-architect/references/14-graph-runtime.md`. — The node and
  parameter model, demand-driven evaluation, the content-addressed cache key, dirty propagation,
  and the accumulator pattern. **Carries no citations of its own**, so it is cited here for what a
  practitioner built and for the two defects Gaia found in it, never as evidence that a mechanism
  is correct.
- **simd_dispatch_drift** `F` — `terrain-architect/registers/figure-regen.tsv`, on the branch
  `origin/claude/terrain-architect-definition-of-done`. — A measured, reproducible case of the
  same code on the same CPU producing materially different terrain under two SIMD dispatch
  regimes. Records the reproduction recipe, the per-ufunc 1-ULP measurement over 10007 doubles,
  and the amplification mechanism. **Not present on `main` or on this branch** — cite it to that
  branch or not at all.
