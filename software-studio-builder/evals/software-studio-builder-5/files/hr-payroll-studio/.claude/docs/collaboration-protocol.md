# Collaboration Protocol

**User-driven collaboration, not autonomous execution.** Every agent and skill in this
studio follows the same five steps.

1. **Question** — ask what you need to know before proposing anything. Ask a whole round
   at once, each question with a recommended answer the user can accept with "you pick".
2. **Options** — present 2–4 options with their trade-offs and a recommendation.
3. **Decision** — the user decides. A skipped or dismissed question is not an answer:
   act on nothing, re-ask in plain text and wait.
4. **Draft** — show the draft (or a summary of it for long documents) before writing.
   Long documents are drafted and approved one section at a time.
5. **Approval** — ask "May I write this to `<path>`?" and write only on a yes. A
   multi-file change is approved as a whole changeset, listed file by file.

## What this protects

- **The user owns the decisions.** Agents bring structure and expertise, not autonomy.
- **Nothing lands unseen.** Every write was shown and approved.
- **Unknowns stay visible.** A step that could not run says `NOT ASSESSED` and why; a fact
  that cannot be sourced says `NOT SOURCEABLE`. Neither is ever reported as a pass.

## Exceptions

- Appending a progress line to `production/session-state/active.md`.
- A subagent writing the new file its orchestrating skill named in its brief.
- `modes.automation: guided` or `autonomous` (per developer, in `project.local.yaml`)
  trades some of these prompts for speed; commits and pushes still need the user.

## Asking well

- One round, not a drip: every question you need now, none that depends on an answer
  from the same round.
- Each question stands on its own: name the thing you are asking about.
- Recommend. "Which do you prefer?" with no recommendation hands your job back.
