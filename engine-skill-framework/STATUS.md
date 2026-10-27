# Engine skill framework — phase 1 status

> New session? Read `CLAUDE.md` in this directory first (saved workflow state, restore command, rules).

Branch: `claude/engine-skill-framework-phase1` (no PR). Phase 1 (G1) answers "do we have everything, with the right boundaries?". **No SKILL.md is written until G1 converges** (then G2, see `docs/08-phase-2-plan.md`).

## Where G1 stands

| Round | Result | Committed |
|---|---|---|
| 0 | capability map, skill graph, contracts, critics, validator | 72ac034 |
| 1 | 276 findings, schema v1 revision | 4a9a529 |
| 2 | calibrated (12/15 seeds), 265 findings, v2 revision (153 skills, 124 contracts, 1360 capabilities); adjudication 20 upheld / 4 overturned | fd20381, 7385ce7 |
| 3 | Calibrated (15/15 seeds, independent seed author). 224 findings, 53 seed hits, 171 real. **Revision applied** (r3_a–g, r3_z): 154 skills, 129 contracts, 39 configurations, 74 legacy patterns; check.py green, 37 selftest mutations red. Awaiting adjudication of the partial/reject dispositions. | f542e8c … (this commit) |
| 4 | 144 findings, seed recall 7/15 (**not calibrated**: K-ARCH, K-SYSTEMS, K-PLATFORM, K-PERF, K-PROD, K-FUTURE, K-TEST, K-SEC, K-COMPLETE missed their own seed; especially gate-validator and one-word-deletion seeds). 135 real findings: 107 confirmed by the verifier, 28 rejected. **Revision applied** (`gauntlet/round-4/r4_a–d`, `r4_z`): 156 skills, 134 contracts, 43 configurations, 88 legacy patterns; new rules (freeze-before-claim with extension tiers, radar staleness, process skills at M0, oracle_reference on all conformance contracts). Awaiting adjudication. | (this commit) |
| 5 | Calibrated: seed recall 14/15 (S11, an omitted validation capability, missed by all). 154 findings, 31 seed hits, 123 real (98 confirmed: 1 blocker, 60 major, 37 minor). **Revision applied** (`gauntlet/round-5/r5_a–c`, `r5_z`): 158 skills, 135 contracts, 47 configurations, 89 legacy patterns; new rules: placeholder oracle_reference banned, real_backend_lane on boundary contracts, gate cycles, freeze after first consumer. Awaiting adjudication. | (this commit) |

Not converged: round 3 still has real major/blocker findings to fix, and the Completeness critic must be clean in two consecutive rounds.

## Next steps (in order)

1. Round-5 adjudication done (`gauntlet/round-5/adjudication.md`: 33 upheld, 9 overturned and fixed in `r5_h.py`).
2. **Round 6**: fresh seed author (medium-visibility seeds, include an omission seed), same mechanical-sweep briefs (`gauntlet/round-5/workflow/g1-round-5-gauntlet.js` is the template). Convergence needs a calibrated round with zero accepted blocker/major findings and the Completeness critic clean in two consecutive rounds; rounds 4 and 5 still produced 50–60 confirmed major findings each, mostly new capability/contract gaps per domain rather than errors in earlier fixes.
3. Only then G2 (SKILL.md generation, `docs/08-phase-2-plan.md`).

## Rules of engagement

- Keep workflows small (about 30 agents per round: 15 critics plus one batch verifier each, not two per finding).
- Blind critics review a seeded copy in the scratchpad, never the repository; seeds are planted by an independent agent and sealed until all critics report.
- Checkpoint (commit + push, saving any workflow result/journal into `gauntlet/round-N/workflow/`) after every step **and after roughly every 15–20 agents finish** inside a workflow.
- `scripts/checkpoint.py` runs in the background (every 10 min) and force-pushes workflow journal/results to branch `claude/engine-skill-framework-checkpoints` (one replaced commit; recover files from there if a session dies). Start it with `python3 engine-skill-framework/scripts/checkpoint.py &`. It pushes only when files changed. When a workflow has finished and its result is committed to the working branch, stop it and run `python3 engine-skill-framework/scripts/checkpoint.py --clear` to delete the checkpoint branch.
- Commit and push after every step. Scripts reproduce every data change (`apply.py` resets `data/` to the previous commit and replays the parts).
- The framework is self-contained; do not link it to any other skill or repository.

## Verify the checkout

```bash
cd engine-skill-framework
python3 scripts/check.py --quiet          # 0 errors, 0 warnings
python3 scripts/check.py --selftest       # every mutation must go red
python3 scripts/render.py --check         # generated docs current
```
