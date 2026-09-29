# 08 · Phase 2 Plan — the SKILL.md Gauntlet (G2)

**Status: not started.** G2 starts only after G1 has converged (see `gauntlet/PROTOCOL.md`). G1 asks *do we have everything, with the right boundaries?* G2 asks *is each node described correctly?* The two are kept separate so that description effort is never spent on a node that the graph later deletes, merges or re-bounds.

## Inputs frozen by G1

- `data/*.json` at the converged commit: capabilities, owners, contracts, profiles, critics.
- Any G2 finding that implies a *graph* change (a new owner, a moved boundary, a new contract) is **not** fixed inside G2. It is routed back as a G1 change request, re-gated by `check.py`, and re-reviewed by the G1 critics that own that area. This stops description work from silently re-drawing boundaries.

## What each node becomes

Each skill node becomes a directory that follows this repository's skill conventions:

```
skills/<skill-id>/
  SKILL.md          router: frontmatter (name, trigger description), purpose, when to use / not use,
                    responsibilities, non-responsibilities, contracts, the decision checklist
  references/       load-on-demand depth: techniques by maturity class, validation, sources
  evals/            trigger and behaviour evals
```

`SKILL.md` must contain every section the brief requires. The generator pre-fills the sections marked ⚙ from `data/`. The ⚙ sections are regenerated rather than edited, so graph and description cannot drift.

| Section | Source |
|---|---|
| Purpose | ⚙ skill.purpose, then expanded |
| Responsibilities | ⚙ owned capabilities, with scope detail added |
| Non-responsibilities | ⚙ skill.non_responsibilities with owners |
| Required knowledge | languages, algorithms, APIs, hardware, mathematics, standards, research areas |
| Inputs | what an agent must receive before using the skill (requirements, profile, budgets, contracts) |
| Outputs | ADRs, APIs, specs, implementation, tests, benchmarks, docs, telemetry, validation reports |
| Dependencies | ⚙ consumed contracts (required / optional) |
| Interfaces | ⚙ provided contracts plus the domains they touch |
| Constraints | performance, latency, determinism, memory, threading, platform, security, compatibility, scalability |
| Technique ladder | **traditional → current mainstream → current high-end → emerging → research-stage**, each with a maturity class and graded sources, plus a recommendation justified against requirements (never "engines normally do it") |
| Failure modes | how implementations of this subsystem typically fail |
| Validation | how an independent critic objectively decides correctness (oracles, reference data, contract tests) |
| Performance validation | what is benchmarked, on which representative workloads, against which budget |
| Scalability validation | behavior per configuration (`indie-2d` … `aaa-open-world-online`, `dedicated-server`) |
| Cross-cutting obligations | ⚙ one answer per concern in `04-cross-cutting.md` |
| Research sources | from `07-research-plan.md`, graded T1–T6 |
| ADR seeds | decisions this skill must record (from `06-gap-analysis.md` §B), with revisit conditions |

## Order of generation

1. **Contracts first.** Each contract owner drafts its contract specification before its SKILL.md: responsibilities, invariants, threading rules and versioning. The highest fan-in contracts come first (see `02-skill-dependency-graph.md`). Consumers review the contracts they consume.
2. **Orchestrators and cross-cutting skills.** Their obligations must exist before domain skills can answer them.
3. **Domain leads.**
4. **Experts,** in parallel waves grouped by lead. The G2 critics for a wave are the ones `05-critic-framework.md` assigns (◆ domain critics plus the universal critics).

## Machine gates (run before any critic reads a SKILL.md)

- Every required section is present and non-empty.
- Every ⚙ section matches `data/` exactly (regenerate; never hand-edit).
- Every technique named in the ladder carries a maturity class that matches the capability map. An `experimental` technique is never the recommendation without an ADR reference.
- Every non-responsibility names an owner, and that owner's SKILL.md lists the item as a responsibility, so both sides agree.
- Every cited source has a provenance tier; none are forum or tutorial sources.
- Trigger descriptions pass the repository's trigger-eval conventions (`evals/`).
- Size budget: SKILL.md stays a router; depth moves to `references/`.

## G2 convergence

G2 uses the same loop and stop rule as G1, applied per wave. A node converges when its assigned critics produce no accepted blocker or major findings in one round. It also needs its consumers to confirm that the contracts it provides match what they need. A wave converges when all its nodes have converged. G2 ends when every node has converged and a final **cross-node consistency round** finds no contradictions between skills: two skills claiming the same technique, obligations answered inconsistently, or conflicting defaults.
