# Principles every generated piece obeys

These are built into the skeleton and the renderers. Each exists because its absence
produces a specific, recurring failure — noted where it is not obvious. Keep them when you
extend a studio by hand.

1. **User-driven collaboration.** Question → Options → Decision → Draft → Approval. Agents
   ask "May I write this to `<path>`?"; a multi-file change is approved as a listed
   changeset; a dismissed question is not an answer.
2. **A check that cannot report that it did not run is not a check.** Every verdict
   vocabulary has `NOT ASSESSED`, ranked above the pass value and below the failure values,
   with the reason named. A skipped step announces itself in the output.
3. **An absent value never defaults to the permissive one.** The resolver prints
   `NOT ASSESSED (stack.name is not set)` rather than guessing a code root.
4. **Never assert what you cannot source.** Write `NOT SOURCEABLE — <what>` and let the gap
   reach the verdict (a proposal item with no solid support is a CONCERN the user sees).
5. **Helpers observe; skills judge.** `artifact_check.py` prints rows; `/next-step` and
   `/gate-check` decide what they mean. A helper that judges will contradict a mode it
   cannot see.
6. **Derive covered sets; do not enumerate them.** The checker walks the files on disk.
7. **Derive relationships; do not store them twice.** Delegates-to and gates-owned are
   computed from reports-to and gate owners.
8. **Hooks warn, never rewrite;** the one that refuses (the long-document read guard) says
   why and how to retry.
9. **Read long documents by section.** Grep for `^#`, Read with offset and limit.
10. **The session checkpoint is a file** (`production/session-state/active.md`), not the
    conversation.
11. **Nothing goes upstream.** No issues or comments on vendor repositories; draft them for
    the user.
12. **No commits without the user's instruction.**
