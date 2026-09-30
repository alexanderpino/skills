# Round 4 — state and how to resume

Copy for critics: scratchpad `r4/engine-skill-framework` (built from commit f7e2bff+ with gauntlet/round-* removed, seeds planted by an independent agent). Sealed seeds: `seeded/seeds.sealed.json` — do NOT open until all critics report. Seeded data: `seeded/data/`.
Workflow script: `workflow/g1-round-4-gauntlet.js` (15 critics + 1 batch verifier each). Its `COPY` constant must point at the rebuilt copy:
```bash
COPY=<scratchpad>/r4/engine-skill-framework; mkdir -p $COPY
git archive f7e2bff engine-skill-framework | tar -x -C <scratchpad>/r4   # then rm -rf gauntlet/round-* STATUS.md CLAUDE.md, cp -r gauntlet/round-4/seeded/data over data/, render.py, check.py
```
While running: `python3 scripts/checkpoint.py --interval 600 &`; new session: `scripts/checkpoint.py --restore`, read finished critic outputs from the journal, re-run only the missing ones. After the workflow: save `workflow/round4-result.json` + journal, `checkpoint.py --clear`.
