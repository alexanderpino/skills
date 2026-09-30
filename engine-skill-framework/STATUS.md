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

Not converged: round 3 still has real major/blocker findings to fix, and the Completeness critic must be clean in two consecutive rounds.

## Next steps (in order)

1. **Adjudicate** the partial and reject dispositions of round 3 (`gauntlet/round-3/dispositions.md`) with one independent agent; fix overturns in `gauntlet/round-3/r3_h.py` (then `python3 gauntlet/round-3/apply.py`, `check.py`, `--selftest` once, `render.py`).
2. **Round 4** (about 30 agents: 15 blind critics on a seeded copy in the scratchpad, one batch verifier each). New independent seed author; strengthen the K-NET brief (it missed its own seed twice in round 3). Save the workflow result to `gauntlet/round-4/workflow/` and run `scripts/checkpoint.py` while it runs.
3. Repeat until a calibrated round has zero accepted blocker/major findings and the Completeness critic is clean in two consecutive rounds. Only then G2 (SKILL.md generation, `docs/08-phase-2-plan.md`).

Recurring themes for round 4: rewordings that state a legacy stance are now scanned (`contradiction_terms`); oracle authors must be independent, staffed by the freeze and carry an `oracle_reference`; check that the new contracts (C-CMD, C-VFX, C-PTREF, C-HOSTAUTH, C-CAMERA) and the platform-variant closure hold up.

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
