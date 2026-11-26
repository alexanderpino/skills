---
name: kickoff
description: Before building a feature, scout its scope and the repo's existing specs and decisions, and write a short contract to build against.
disable-model-invocation: true
---

# Kickoff

Turn a feature request into a **contract** before any code: where the work may go, what the repo has already decided, what the docs answer, and which few questions only the owner can answer. Read-only until the contract is written: the only file this skill writes is the contract itself.

## Steps

1. **Scope.** Name the allowed root: the directory the request names, otherwise the repository of the working directory. List every path the request could plausibly reach that lies outside it, as out of scope (a parent repo, a sibling repo, a shared `AGENTS.md` above the root). Done when the root and the out-of-scope list are written down.

2. **Inventory.** Inside the root, and the instruction files above it that load into this session, find:
   - every instruction file (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/`), each with one line on what it governs;
   - every spec and design source that bears on the feature: `openspec/specs/` and open `openspec/changes/`, ADRs, `docs/`, `design/`, code indexes, READMEs of the modules the feature touches.

   Search the docs and code for the feature's key terms and their synonyms, and record each search with its hit count. Done when every search is recorded and each hit is either listed as a source or set aside with a reason.

3. **Decisions and conventions.** From the sources, extract each rule that binds this feature, with `file:line`: earlier decisions and rejected alternatives, naming, how paths and environment variables are derived (relative to a root variable, never a machine's absolute path), testing and coverage rules, UI and platform conventions, safety rules. Done when every source from step 2 has been read for this, and each extracted rule carries its citation.

4. **Questions.** Write every design question the feature raises. Answer each from a cited source or a preference the owner has stated (memory, instruction files, this conversation), and record the answer. What remains open is a real question only when the docs cannot settle it and its answer changes scope, behaviour or cost. Keep at most 3; give each your recommended default and why. Done when every question is answered with a citation or is one of those ≤3.

5. **Acceptance tests.** Write the feature's acceptance criteria as Given/When/Then, each one a test that can go red before the work and green after it. Done when every behaviour in scope has at least one.

6. **Contract.** Write it to the session scratchpad as `contract-<feature>.md`, under these headings: Scope (root, in, out), Sources, Binding rules, Answered questions, Open questions (≤3, with defaults), Acceptance tests. Show it in the reply, with its full path.

## Hand-over

- **Open questions:** ask them once, batched, and wait for the answers before building; fold the answers into the contract.
- **A repo that plans through OpenSpec:** the contract is the input to `openspec-propose`; the change carries its rules and tests.
- **Otherwise:** implement test-first from the acceptance tests, staying inside the root, and cite the contract's rules where a choice rests on one.

At the end of the work, report each acceptance test as passed, failed or not run, and each out-of-scope path as untouched.
