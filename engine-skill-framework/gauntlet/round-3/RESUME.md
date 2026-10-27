# Round 3 — paused state and how to resume

Round 3 was paused mid-critique (usage limit). Everything needed to continue is in this directory, so nothing depends on the session scratchpad.

## What is here

| Path | What it is |
|---|---|
| `seeded/data/` | The seeded review copy's `data/` (framework at commit `9c6aa4e` plus the planted seeds). |
| `seeded/seeds.sealed.json` | **Sealed** seed list written by the independent seed author. The builder must not open it until all critics have reported (PROTOCOL.md, calibration). |
| `partial-critics/` | Critic outputs finished before the pause (K-ARCH, K-RENDER, K-SYSTEMS). |
| `workflow/g1-round-3-gauntlet-*.js` | The round-3 workflow: 15 blind critics, each finding verified by a fact lens and a materiality lens. |
| `workflow/journal.jsonl` | The workflow journal at the pause (cached agent results). |
| `r3_a.py`, `apply.py`, `disp.py` | Round-3 revision so far: fixes for the four round-2 overturns (applied and committed). |

## Resume

1. **Same session, scratchpad intact:** re-invoke the workflow with `resumeFromRunId: "wf_f2b5b705-724"` and the script path printed at launch; finished agents return cached results.
2. **New session:** rebuild the seeded copy, then run the workflow script again (its `COPY` constant must point at the rebuilt copy):
   ```bash
   COPY=<scratchpad>/r3/engine-skill-framework
   mkdir -p "$(dirname "$COPY")"
   git -C /home/user/skills archive 9c6aa4e engine-skill-framework | tar -x -C "$(dirname "$(dirname "$COPY")")/r3" --strip-components=0
   rm -rf "$COPY/gauntlet/round-1" "$COPY/gauntlet/round-2" "$COPY/gauntlet/round-3"
   rm -rf "$COPY/data" && cp -r gauntlet/round-3/seeded/data "$COPY/data"
   mkdir -p "$COPY/gauntlet/round-3"
   (cd "$COPY" && python3 scripts/render.py && python3 scripts/check.py --quiet)   # must be green
   ```
   Keep the critics blind: the copy must not contain `gauntlet/round-*`, and critics must not be pointed at this repository.
3. After all critics report: copy their `K-*.md` into this directory, open `seeded/seeds.sealed.json`, score recall into `seeds.md` / `seed_hits.json`, then disposition and revise with `r3_*.py` parts and `apply.py` (base `fd20381`).


## Saved state and new sessions

While the round-3 workflow is unfinished, its journal is also on branch `claude/engine-skill-framework-checkpoints`. In a **new** session run `python3 scripts/checkpoint.py --restore` (files land in `workflow/restored/`); `resumeFromRunId` only works in the session that started the workflow, so instead read the finished results from the journal and re-run only the missing verifiers (K-TEST-9..17 and all K-SEC findings) in a small workflow. Delete the branch with `--clear` once the results are committed here.
