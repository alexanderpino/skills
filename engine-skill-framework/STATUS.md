# Engine skill framework — phase 1 status

Branch: `claude/engine-skill-framework-phase1` (no PR). Phase 1 (G1) answers "do we have everything, with the right boundaries?". **No SKILL.md is written until G1 converges** (then G2, see `docs/08-phase-2-plan.md`).

## Where G1 stands

| Round | Result | Committed |
|---|---|---|
| 0 | capability map, skill graph, contracts, critics, validator | 72ac034 |
| 1 | 276 findings, schema v1 revision | 4a9a529 |
| 2 | calibrated (12/15 seeds), 265 findings, v2 revision (153 skills, 124 contracts, 1360 capabilities); adjudication 20 upheld / 4 overturned | fd20381, 7385ce7 |
| 3 | **in progress.** Calibrated (15/15 seeds, independent seed author). 224 findings, 53 hit seeds, 171 real. Round-2 overturns already fixed in `gauntlet/round-3/r3_a.py`. K-NET missed its own seed twice, so it is re-briefed for round 4. | f542e8c |

Not converged: round 3 still has real major/blocker findings to fix, and the Completeness critic must be clean in two consecutive rounds.

## Next steps (in order)

1. **Verifier results for round 3.** 51 verifier calls (K-TEST-9..17, all K-SEC) failed at a usage limit. Either resume the workflow (`gauntlet/round-3/RESUME.md`, run `wf_f2b5b705-724`), or skip it: verifiers are a first screen only, not required by the protocol. Save the result to `gauntlet/round-3/workflow/`.
2. **Disposition** the 171 real findings (`gauntlet/round-3/K-*.md`, structured data in `workflow/round3-result.json`; seed hits in `seed_hits.json`). Findings that only mention a seeded item while raising a different defect are dispositioned on their merits.
3. **Revise**: add `gauntlet/round-3/r3_b.py …` parts (editor API: `scripts/edit.py`; examples: `gauntlet/round-2/r2_*.py`), fill `disp.py` overrides, run `python3 gauntlet/round-3/apply.py` (base `fd20381`), then `check.py`, `check.py --selftest`, `render.py`, commit.
4. **Adjudicate** partial/reject dispositions with one independent agent, fix overturns.
5. **Round 4**, with the K-NET brief strengthened.

Recurring themes worth fixing first in round 3: check.py should detect legacy wording in capability names (K-LEGACY-12); oracle authors are same-workstream for 40 contracts and chosen for passing the check rather than competence (K-ARCH-1/2); milestone gates name capabilities owned by the gated feature's own implementer (K-PROD-3).

## Rules of engagement

- Keep workflows small (about 30 agents per round: 15 critics plus one batch verifier each, not two per finding).
- Blind critics review a seeded copy in the scratchpad, never the repository; seeds are planted by an independent agent and sealed until all critics report.
- Checkpoint (commit + push, saving any workflow result/journal into `gauntlet/round-N/workflow/`) after every step **and after roughly every 15–20 agents finish** inside a workflow.
- Commit and push after every step. Scripts reproduce every data change (`apply.py` resets `data/` to the previous commit and replays the parts).
- The framework is self-contained; do not link it to any other skill or repository.

## Verify the checkout

```bash
cd engine-skill-framework
python3 scripts/check.py --quiet          # 0 errors, 0 warnings
python3 scripts/check.py --selftest       # every mutation must go red
python3 scripts/render.py --check         # generated docs current
```
