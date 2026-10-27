# Gauntlet G1 — Framework Gauntlet Protocol

G1 answers one question: **do we have everything, with the right boundaries?** It does not judge whether any skill is *described* well; that is G2 (see `docs/08-phase-2-plan.md`).

## The loop

```
data/*.json ──render──▶ docs/01-05 (+ 00 rationale)
      ▲                         │
      │                  15 blind critics (fresh context each round)
   revise                       │
      │                  findings (schema below)
      └──── dispositions ◀──────┘
```

1. **Gate.** `python3 scripts/check.py` must be green and `check.py --selftest` must go red on every mutation before a round starts. Critics never re-derive what the gate proves: unique owners, closure, layering, reference integrity.
2. **Critique.** Every critic in `data/critics.json` (stage G1) reviews the whole framework in a fresh context. Critics receive the artifact only: `data/`, `docs/00-09` and `gauntlet/PROTOCOL.md`, in a seeded copy (see calibration). They never receive this log, prior findings, or the builder's dispositions. That is the blind rule.
3. **Findings.** Each finding has:
   `id · critic · severity (blocker | major | minor) · type (omission | overlap | wrong-boundary | wrong-owner | obsolete-assumption | missing-contract | dependency-error | maturity-error | scale-down | other) · target (capability / skill / contract ids) · evidence · proposed change`.
   - **blocker**: the framework cannot coordinate agents correctly (e.g. two owners, a missing domain that many skills need).
   - **major**: a material omission or wrong boundary that would cause rework or silent legacy architecture.
   - **minor**: a wording, naming or small-placement issue.
   Stylistic preferences are not findings.
4. **Disposition.** The builder assigns each finding one disposition: **accept** (change applied, commit referenced), **partial** (part applied, rest reasoned), **reject** (with a technical reason recorded), **merge** (a duplicate of another finding), or **seed** (it hit a planted seed; any real residual defect it also names is fixed and marked `seed+residual`). Severity is fixed by the critic: the builder may not downgrade it (added in round 2, K-TEST-9). Dispositions are recorded in `gauntlet/round-N/dispositions.md`.
5. **Revise, re-gate, re-render.** Every accepted change that is structural is also expressed in data, so the next gate checks it. A missing brief term becomes a `seed-map.json` entry.

## Adjudication (added in round 1, K-QUALITY-4)

The builder does not get the last word on its own rejections. Every finding dispositioned **reject** or **partial** goes to a fresh-context **adjudicator**. The adjudicator receives the finding, the disposition text and the current data, but not the builder's other reasoning. It rules **uphold** (the disposition resolves the material problem) or **overturn** (the problem is still materially open). An overturned finding counts as an open accepted finding of its original severity and must be fixed in the next revision. Rulings are recorded in `gauntlet/round-N/adjudication.md`.

## Critic calibration (added in round 1, K-QUALITY-4)

From round 2 on, critics review a **seeded copy** of the framework in the scratchpad, not the repository. Before the round, the orchestrator plants 10–15 defects that `check.py` cannot see: omissions, overlaps, wrong owners, dishonest maturity labels, legacy stances and wrong platform tags. Each seed sits inside a specific critic's mandate. The seed list is sealed in `gauntlet/round-N/seeds.md` and is written only after the round.

- A round **counts toward convergence only if the union of critics finds at least 80% of the seeds**, and each scoped critic finds the seeds in its own mandate at least once over two consecutive rounds.
- Findings that hit a seed are removed before dispositions. The real framework never contained the seed.
- A critic that misses its own seed twice in a row is re-briefed or replaced.

### Round-2 amendments (K-TEST-9)

- **Adjudicated paths.** Besides `partial` and `reject`, the adjudicator also rules on every claim that a finding is a non-material re-raise, and on every `seed+residual` whose residual the builder declined.
- **Precision as well as recall.** Calibration reports each critic's precision: the share of its findings that survive disposition and adjudication. A critic below the precision floor (50%) is re-briefed like one that misses its seed.
- **Seed author independence.** From round 3, seeds are planted by a separate agent in a fresh context, not by the builder, and sealed before the critics start.
- **Diversity.** Critics, adjudicators and seed authors use at least two model families or prompt lineages where available; when only one is available, that limitation is recorded in the round's `seeds.md`.
- **Human audit.** A human samples adjudications at a fixed rate (`ARCH.ORG.human-audit`); the sample and its outcome are recorded per round.

## Convergence (stop rule)

The loop stops only when both hold:

- **A.** In one full, *calibrated* round, all critics produce **zero accepted or adjudicator-overturned blocker or major findings**.
- **B.** The **Completeness Critic** produces zero accepted material omissions in **two consecutive rounds**. Each round uses a fresh instance with no memory of the previous one.

A re-raised finding that was rejected earlier counts as non-material unless it brings new evidence. A fixed round count is never a stop reason. If a round still has accepted blocker or major findings, another round runs.

## Independence measures

- Fresh context per critic per round; no shared scratchpad.
- Critics do not see each other's output within a round.
- The builder (lead agent) never grades its own fixes. The next round's critics do.
- Critics are told the brief's standard: "best practice" means the strongest demonstrated approach today, not the most common historical one.
