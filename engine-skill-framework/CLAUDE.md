# engine-skill-framework — read this first

This is a self-contained framework (no relation to other skills in the repository). **Start with `STATUS.md`**: it says which gauntlet round is in progress, what is done, and the ordered next steps. Do not write any SKILL.md until phase 1 (G1) has converged.

## Saved workflow state (do not lose it)

Long gauntlet workflows write their state outside the repository, so it is copied to a git branch:

- Branch `claude/engine-skill-framework-checkpoints` holds the latest workflow journal and result files (`engine-skill-framework/gauntlet/round-N/workflow/checkpoint/`). It exists only while a workflow is unfinished; once the results are committed to the working branch it is deleted (`scripts/checkpoint.py --clear`).
- **New session?** Run `python3 engine-skill-framework/scripts/checkpoint.py --restore` (fetches that branch into `gauntlet/round-N/workflow/restored/`, no-op if the branch is gone). A workflow can only be resumed (`resumeFromRunId`) inside the session that started it, so a new session reuses the restored *results*: read the finished critic/verifier outputs from the journal (`{"type":"result",...}` lines) and re-run only what is missing, with a small workflow.
- **Same session?** Resume with the run id and script path recorded in `gauntlet/round-N/RESUME.md`.
- While a workflow runs, start the background saver: `python3 engine-skill-framework/scripts/checkpoint.py --interval 600 &` (pushes only when files changed).

## Rules

- Keep workflows small (about 30 agents per round). Checkpoint (commit + push) after every step and roughly every 15–20 finished agents.
- Blind critics review a seeded copy in the scratchpad, never the repository; seeds are planted by an independent agent and sealed until all critics report.
- `python3 scripts/check.py`, `--selftest` and `python3 scripts/render.py --check` must be green before committing.
