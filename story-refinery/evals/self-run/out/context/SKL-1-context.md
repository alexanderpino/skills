# Shared context — SKL-1 Every validator code can be looked up

Read this once before your subtask brief. It is identical for every subtask on this story: the facts refinement established, including the ones that are absences.

## The outcome this serves

A finding like BRF009 is currently a dead end unless you open validate.py: 56 of 160 codes are documented nowhere. This adds an explicit registry of every code with a one-line meaning, a `--codes` flag (plain, JSON, markdown), a generated `references/codes.md`, a row for it in SKILL.md, and four selftest checks: emitted equals registered both ways, severity matches the call sites, the file is current, and each meaning is a meaning. Two subtasks, one repo, one day and a half.

## Glossary

Domain words in this story mean this here, whatever they mean elsewhere.

- **code** — The stable identifier of a finding, e.g. BRF009: a 3-6 letter prefix naming the family plus three digits. Cited in docs, comments and PRs, so it never changes meaning. (`story-refinery/references/acceptance-criteria.md; validate.py PHASE_OF`)
- **registry** — The explicit dict of every code a module can emit, with a one-line meaning (D1). New in this story. (`decisions.D1`)
- **docs suite** — selftest suite 16, 'docs consistency': paths, flags and codes cited in SKILL.md and references must exist. (`skills/story-refinery/scripts/selftest.py:600`)

## House conventions, with the code that shows them

Each is cited. Read the citation rather than trusting the sentence, and match the code you find.

- A code is a string literal as the first argument of rep.error(...)/rep.warn(...), or of a local alias of them (report(...) at l.1129). — `skills/story-refinery/scripts/validate.py:164`
- batch.py reports through local error()/warn() closures, same literal-first shape. — `skills/story-refinery/scripts/batch.py:188`
- criteria.py reports through a findings list of ("ERROR"|"WARN", "CODE", message) tuples. — `skills/story-refinery/scripts/criteria.py:106`
- Phase grouping is the PHASE_OF prefix map; phase_of() picks the longest matching prefix; main() prints groups in sorted(phase) order. — `skills/story-refinery/scripts/validate.py:74`
- Scripts are stdlib-only, no network (SKILL.md:821); selftest prints ok/FAIL per named check and a failure total, never an assertion count (selftest.py:51, :1516). — `skills/story-refinery/SKILL.md:821`
- The docs suite verifies docs -> code with a regex over references, config and SKILL.md; extend it, do not add a second suite. — `skills/story-refinery/scripts/selftest.py:640`

## Already ruled out

Refinement looked for these and did not find them. Do not spend budget re-checking, and do not substitute something that merely looks similar.

- **No code is built dynamically (format, concatenation, %-substitution into the code itself)** — looked in `rg '"[A-Z]{2,6}%' story-refinery/scripts/`, `rg '\.format\(' story-refinery/scripts/validate.py story-refinery/scripts/batch.py story-refinery/scripts/criteria.py`, `every first argument of error/warn/report/add in the three files (archaeologist re-ran it: 191 + 5 literals)`. A registry keyed by the literal is complete; do not add runtime discovery of codes.
- **summary.py and selftest.py contain code literals but emit nothing - they are consumers** — looked in `rg '"[A-Z]{2,6}[0-9]{3}"' story-refinery/scripts/summary.py story-refinery/scripts/selftest.py`, `the call-site regex in D4 against both files: 0 emitting calls`. Not emitters. Do not register their literals and do not stop on them.
- **There is no linter configuration in this repository** — looked in `ls -a /home/user/skills (ruff, flake8, setup.cfg, pyproject, tox, eslint)`. dod-lint removed from the self-run config; do not put a lint command in done_when.
- **There is no tests/ directory; the manifest's guessed test command `python -m pytest tests/ -q -rs` is wrong for this repo** — looked in `ls /home/user/skills/tests`, `.refinery/manifests/skills@a837f43.json`. The test command is `python3 story-refinery/scripts/selftest.py`. Do not use the manifest's guess.

## Decided already — do not re-open

- Where does the meaning of a code come from? → **An explicit CODES dict per module with a one-line meaning**. A reader wants the condition, not the message; and the both-ways check in AC3 needs a set whose literals are syntactically distinct from call sites - dict keys are.
- Is codes.md committed, or generated at test time? → **Committed, with selftest asserting it equals the generator's output**. The skill is installed as plain files and read by agents that may not run scripts; a committed file is the only one they see.
- Where do batch.py's BAT codes sit in the phase grouping, and with which label? → **Add BAT to PHASE_OF as its own group**. 'other' is where meaning goes to die. Label '9 batch': the batch check runs before the push, alongside emit. A validation run never emits BAT, so main()'s grouped output is unchanged.
- Which scripts count as emitters, and how does --codes reach their registries? → **validate.py, batch.py, criteria.py; --codes imports the other two lazily**. criteria.py:106 emits through a findings list; the archaeologist re-opened it. Consumers (summary.py, selftest.py) are excluded by the mechanical definition of 'emitted'.
- What does --codes print, and in which order? → **One TSV line per code, sorted by (phase label, code); --markdown groups under headings in the same order; --json a list**. PHASE_OF insertion order is not phase order (ENB, BAS sit after IRR); sorting by label is the ordering main() already uses, and it is the only one two implementers would reproduce identically.
- Where is the severity column from, given ten codes emitted at both severities and DOD001 whose severity a config rule decides? → **Authored in the registry, and selftest compares it to the call sites: error | warn | 'error | warn' | 'config' for an aliased emitter**. The tester found the column would be wrong for ten codes with nothing able to fail. Codes are never split - REV009 and PND001 are cited in existing findings.

## Freshness

This was true at: `skills@a837f43`.

If your brief's preflight fails, the code has moved since. Stop and report it rather than implementing against the brief - a stale anchor is the one case where the ticket is wrong and you are right.
