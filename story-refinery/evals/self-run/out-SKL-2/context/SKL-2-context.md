# Shared context — SKL-2 manifest lifts a CI test command out of its working directory

Read this once before your subtask brief. It is identical for every subtask on this story: the facts refinement established, including the ones that are absences.

## The outcome this serves

The manifest scanner reads `run:` lines out of CI workflows but ignores `defaults.run.working-directory`, so a command that only runs inside terrain-architect/reference-impl is presented as the repo's test command and lands in briefs as a done_when that fails at the root. Fix: honour the workflow default and step-level working-directory by prefixing `cd <dir> &&`, and print the source file next to each command. Failing test first, then the fix.

## Glossary

Domain words in this story mean this here, whatever they mean elsewhere.

- **manifest** — The sha-keyed per-repo summary evidence.py builds: files, languages, commands, contracts. Rebuilt when HEAD moves or ttl_days passes. (`story-refinery/references/evidence.md`)
- **working directory (CI)** — GitHub Actions `defaults.run.working-directory` at workflow level, or `working-directory:` on a step; a `run:` command executes there, not at the repo root. (`.github/workflows/terrain-architect.yml:25`)

## House conventions, with the code that shows them

Each is cited. Read the citation rather than trusting the sentence, and match the code you find.

- Scripts are stdlib-only, no network; selftest prints ok/FAIL per named check and a failure total. — `skills/story-refinery/SKILL.md:821`
- selftest's check(name, ok, detail) prints `ok <name>` or `FAIL <name> <- detail`; a new check is one call. — `skills/story-refinery/scripts/selftest.py:50`
- detect_commands scans CI files line by line with a regex; extend the same loop, do not add a YAML parser. — `skills/story-refinery/scripts/evidence.py:104`

## Already ruled out

Refinement looked for these and did not find them. Do not spend budget re-checking, and do not substitute something that merely looks similar.

- **There is no linter configuration in this repository** — looked in `ls -a /home/user/skills (ruff, flake8, setup.cfg, pyproject, tox, eslint)`. dod-lint removed from the self-run config; do not put a lint command in done_when.
- **There is no tests/ directory; the manifest's guessed test command `python -m pytest tests/ -q -rs` is wrong for this repo** — looked in `ls /home/user/skills/tests`, `.refinery/manifests/skills@a837f43.json`. The test command is `python3 story-refinery/scripts/selftest.py`. Do not use the manifest's guess.
- **No consumer parses commands.test beyond printing it or copying it into a brief, so a `cd dir &&` prefix breaks nothing** — looked in `rg 'commands' story-refinery/scripts/emit.py story-refinery/scripts/validate.py story-refinery/scripts/summary.py`, `rg '\["test"\]' story-refinery/scripts/`. Carry the directory in the string (D2); no schema change.

## Decided already — do not re-open

- Root cause: why does a sub-project's command surface as the repo's? → **The regex only sees `run:` lines and has no notion of working directory**. evidence.py:104-108 reads lines in isolation; the workflow's default at terrain-architect.yml:25 is never read. Five whys stop here: this is the first cause we own and can fix.
- Carry the directory in the command string, or as a separate manifest field? → **`cd <dir> && <command>` in the string**. Briefs and done_when copy the string verbatim; a separate field would be dropped on the way.

## Freshness

This was true at: `skills@eeb5595`.

If your brief's preflight fails, the code has moved since. Stop and report it rather than implementing against the brief - a stale anchor is the one case where the ticket is wrong and you are right.
