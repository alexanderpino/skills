# Working agreement

## Keep going until the queue is empty

**Do not stop and wait for input at phase boundaries.** Finishing a phase is not a decision point —
it is the middle of the plan. Work items end to end: implement, gate, commit, next.

Stop only for one of these. Nothing else counts:

1. **A real decision only the user can make** — a product choice, a trade-off with no defensible
   default, a change of direction.
2. **An unsafe or irreversible action** — pushing to a remote (never authorised in this repo),
   deleting work, rewriting published history, anything reaching outside the machine.
3. **A finding that invalidates the plan** — not a defect found and fixed, but evidence the approach
   itself is wrong.
4. **The queue is genuinely empty.**

Explicitly NOT reasons to stop: a phase completing, a gate passing, a commit landing, a good place
to summarise, "shall I continue?", or the work having gone on a long time. If the todo list has a
pending item and none of 1–4 applies, start it.

## Report through the document, not the conversation

`apps/terrain-studio/PROGRESS.md` is the running record — position, gate readings, what is next,
what is blocked. Keep it current. Chat replies stay short: what landed, what is next, anything that
needs a decision. A per-commit narration in chat is noise; the same content written once in the
document is useful.

## Verification discipline

This project's standing failure mode is **the vacuous gate** — a check that passes on a broken
build. Seven instances found so far, each by a different route. Non-negotiables:

- **A gate that has never been seen to fail is not a gate.** Arm every bound between two *measured*
  endpoints — one on the broken path, one on the fixed — and demonstrate the failing one.
- **Assert on output, never on exit status alone.** A process can exit 0 having done nothing.
- **A quantity worth printing is worth asserting.** If it is diagnostic enough to report, it is
  diagnostic enough to fail on.
- **Absence of evidence is a failure, not a pass.** An empty result set, a scan that found no files,
  a probe that compared nothing — all are red.
- **Measure before concluding.** Guessing a cause and committing the guess has been wrong more often
  than right here. Read the code, run the probe, then say what it is.

## Standing permissions

- **Commits: authorised.** Commit freely as work lands.
- **Push: NOT authorised.** Has never been granted. Ask.
- **Sub-agents and workflows: authorised.** Fan out whenever it helps; no need to ask.

## Orientation

- `apps/terrain-studio/` — the app. `PROGRESS.md` for position, `BACKLOG.md` for findings and
  decisions, `~/.claude/plans/quiet-wishing-harbor.md` for the architecture plan.
- Run it: `.\run-studio.ps1` (dev) · `-Mode pwa` (build + preview).
- Gate of record: `npm run verify -- _verify_digest.js` — 60 node types, bit-identical.
  Note it runs with `USE_GPU = false`, so it does **not** cover the GPU kernels.
- `terrain-architect/` and the installed skill under `~/.claude/skills/` — the doctrine corpus. The
  **installed** copy is the source of truth; this repo's copy catches up on merge.
