# Backlog — noticed, deliberately not funded

One line per item. Nothing here is in scope for this run; the report
carries the list so the user can decide what a future run should cover.

- `--root` must precede the subcommand; no example in the skill shows this
- critic.md does not bound a critic's inspection scope — the largest single burner
- subagent cold re-reads are both the source of independence and the main cost;
  no guidance on giving a critic a scoped slice instead of a whole artifact
- report/board do not yet surface the token unit that status now reports
- ASD-STE100 20-25 word ceiling now names its scope; no gate checks the run's
  output against it, so the rule is unenforced
- gate cache is per-repo, not per-lane: concurrent lanes each run the full suite
  and invalidate each other's entries — correct but wasteful at high WIP
