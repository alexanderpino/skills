# State and resume

A gauntlet's value scales with how long it can run unattended — which means the
run must survive a crash, a context limit, or an interrupted session without
losing anything. Everything that matters lives on disk; nothing that matters
lives only in the model's memory.

## Layout

```
gauntlet/
├── config.json      # lanes, dimensions, armed stop thresholds, granted extensions
├── contract.md      # confirmed intake contract — subagents read goal/rules here
├── bar/             # frozen bar artifacts; read-only after intake
├── ownership.md     # file-ownership ledger, rewritten at each wave start
├── rounds.jsonl     # append-only, script-validated; the single source of truth
├── report.md        # drafted by `gauntlet.py report` at the end
└── workbench.html   # or .md — the live progress surface (references/workbench.md)
```

Add `gauntlet/` to the project's VCS. The state is small, and a resumed run
without its log is not a resumed run.

## Champion mechanics (git)

The champion/challenger guard is implemented with ordinary commits:

- **Snapshot before judging:** commit the pre-round state with the message
  convention `gauntlet(<lane>): wave <W> round <R> champion`. That commit hash is
  the round's `--champion-ref`.
- **Promote:** commit the challenger — `gauntlet(<lane>): wave <W> round <R>
  promoted — <gap closed>`.
- **Revert:** `git checkout <champion-ref> -- <owned paths>` then commit the
  revert. Never `git reset` across lanes: reverting one lane must not undo
  another's promoted work, which is exactly what one-file-one-owner guarantees.
  If a revert would touch a file the lane does not own, that is a lane-collision
  failure — stop and fix ownership before continuing.
- **Best champion:** at stop time, the artifact to hand over is the best
  champion in the log, findable by ref — not automatically the latest commit.

No git available and the user declines `git init`? Fall back to snapshot copies
under `gauntlet/champions/<lane>/w<W>r<R>/` for owned paths only, and say
plainly that this is weaker (no atomic revert, no history diffing).

## Resuming a run

On being asked to continue a gauntlet — or on discovering a `gauntlet/` directory
in a project — do this, in order, before touching any lane:

1. **Read `config.json` and `contract.md`.** The contract is the agreement; do
   not re-negotiate it unless the user asks.
2. **Run `gauntlet.py status`.** It reconstructs streaks, retirement, and fired
   stop conditions from the log — trust it over any summary in the conversation.
3. **Re-verify the inspection path.** Harnesses rot while runs are paused; a
   resumed loop grading stale screenshots is worse than no loop.
4. **Re-read the bar from `gauntlet/bar/`.** Never from memory — bar erosion
   loves a resume.
5. **Check for a half-finished wave.** Signs: a champion snapshot commit with no
   matching promotion/revert record, or a builder's uncommitted changes in the
   working tree. Resolution: judge the pending challenger now if its output is
   intact, otherwise discard uncommitted work and restart that round. Never
   promote unjudged work just because it exists.
6. **Rebuild `ownership.md` for the next wave** and continue at the wave
   boundary.

If a stop condition already fired while nobody was watching, do not run more
waves — go straight to Phase 5 and report. When the fired condition is the
budget, that report ends with an extension offer, not a new wave: a resumed run
that quietly keeps going past the budget has spent money nobody agreed to. A
granted extension is recorded in `config.json` (`extensions`), so `status` after
a resume shows the true agreed ceiling rather than the intake number.

## What never goes only in context

- Verdicts and their evidence → `rounds.jsonl`, via the script
- The bar → files in `gauntlet/bar/`
- Ownership → `ownership.md`
- The contract → `contract.md`

Paraphrase drift across a long run is real and compounds. Point subagents at
paths, not at restatements.
