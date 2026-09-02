# Push preview — SKL-2 manifest lifts a CI test command out of its working directory


Adapter: **markdown** · markup: markdown · subtasks: none · agent brief sink: **description_tail**

_Untailored: no team house rules were applied to this refinement._

## Execution waves

Everything inside a wave can run in parallel. No two subtasks in the same wave write the same file.

- **Wave 1**: S1
- **Wave 2**: S2

## Triage

Labels: none · components: story-refinery · type: Bug · priority: Medium

No label on this item changes the refinement.

## Review

Method: **rubber-duck** · critics: rubber-duck (author, executor voice) · findings: 3

> Rubber-ducked, not reviewed by a blind panel: one voice with full context. Lower assurance, stated here rather than left to be assumed.

These findings were not fixed. They are what you are approving:

- **accepted F1** (major, `subtasks[1].agent_brief.stop_and_ask[0]`): A workflow-level default is under `defaults:` → `run:` → `working-directory:`, three lines deep; the loop's `run:` regex will match the `run:` line under `defaults:` as a command with empty text.
  - Harmless today by the `and value` guard at evidence.py:99; noted in S2's read_first so it is not 'fixed'.

Fixed before handover: F2, F3.


_Field names and issue types below are unverified `[?]` until probed against the live tracker._

---

## SKL-2 — manifest lifts a CI test command out of its working directory (Bug)

## Why / What

The manifest scanner reads `run:` lines out of CI workflows but ignores `defaults.run.working-directory`, so a command that only runs inside terrain-architect/reference-impl is presented as the repo's test command and lands in briefs as a done_when that fails at the root. Fix: honour the workflow default and step-level working-directory by prefixing `cd <dir> &&`, and print the source file next to each command. Failing test first, then the fix.

## Acceptance criteria

**AC1 — A `run:` command taken from a workflow whose `defaults.run.working-directory` is set is recorded as `cd <dir> && <command>`.**
- terrain-architect.yml, defaults working-directory terrain-architect/reference-impl → commands.test = 'cd terrain-architect/reference-impl && python -m pytest tests/ -q -rs'
- a workflow with no working-directory anywhere (boundary) → the command is recorded unchanged, as today

**AC2 — A step-level `working-directory:` overrides the workflow default for that step's command.**
- defaults say pkg-a, the step says pkg-b → cd pkg-b && ...
- step working-directory set, no defaults block (boundary) → cd <step dir> && ...

**AC3 — The manifest summary line names the file each command came from.**
- the repro → the line reads `test=cd terrain-architect/reference-impl && python -m pytest tests/ -q -rs  (.github/workflows/terrain-architect.yml)`
- a command inferred from a manifest file rather than CI (boundary) → the source reads `(python project)` - the string detect_commands already records

## Non-goals

- Verifying that a command's paths exist at its working directory - a second behaviour with its own failure modes; a follow-up if the cd prefix proves insufficient.
- GitLab CI and Azure Pipelines working-directory equivalents (`before_script: cd`, `workingDirectory:`) - same bug class, out of this fix; recorded in follow_ups.

## Technical notes

Root cause (D1): `detect_commands` (`story-refinery/scripts/evidence.py:94`) matches `run:`/`script:` lines (l.108) and records the first test-looking one via `put` (l.98), never reading `defaults.run.working-directory` or a step's `working-directory:`. The workflow sets the default at `.github/workflows/terrain-architect.yml:25` and the command at l.59. `command_sources` already records the file; the summary print at l.399 just does not show it. The manifest is sha-keyed, so a fixed scanner only takes effect on a rebuild - compatibility note in the handover. No YAML parser is available (stdlib only, `_yaml.py` is a subset reader) - the fix tracks the two keys with the same line-regex style as the existing loop.

**Decisions**
- D1 Root cause: why does a sub-project's command surface as the repo's? → **The regex only sees `run:` lines and has no notion of working directory**. evidence.py:104-108 reads lines in isolation; the workflow's default at terrain-architect.yml:25 is never read. Five whys stop here: this is the first cause we own and can fix.
- D2 Carry the directory in the command string, or as a separate manifest field? → **`cd <dir> && <command>` in the string**. Briefs and done_when copy the string verbatim; a separate field would be dropped on the way.


**Risks**
- R1 A workflow with several jobs and different working directories records the first test command's cd, which may be the wrong job → first-hit behaviour is unchanged; the source file is now printed so a reader can see which _(detected by: the summary line names the file)_
- R2 Existing manifests keep the wrong command until rebuilt → handover says to rebuild; ttl_days bounds it _(detected by: the summary line shows a command without a cd prefix on a repo whose CI has one)_

## Subtasks

| # | Title | Repo | Covers | Depends on | Est |
|---|-------|------|--------|------------|-----|
| S1 | [skills] Reproduce the lifted test command in selftest | skills | AC1, AC2, AC3 | — | 0.25d |
| S2 | [skills] Honour working-directory when lifting CI commands | skills | AC1, AC2, AC3 | S1 | 0.5d |

## Non-functional

- **performance**: unchanged - one extra regex per workflow line
- **concurrency**: unchanged
- **failure**: unchanged - a workflow that fails to parse is skipped as today
- **data**: manifest schema unchanged: commands stay strings; the cd prefix is part of the string
- **security**: none - no new input source
- **observability**: the summary line now shows the source file per command
- **compatibility**: manifests built before the fix keep validating; a re-run at the same sha rebuilds only when ttl_days has passed, so say in the handover that a rebuild is needed

_Blast radius: 1 repo(s), 2 primary + 0 secondary file(s), 0 contract(s)._


## Subtask checklist

- [ ] [skills] Reproduce the lifted test command in selftest
- [ ] [skills] Honour working-directory when lifting CI commands


---

## S1 — [skills] Reproduce the lifted test command in selftest (Sub-task)

Parent: SKL-2 · Covers: AC1, AC2, AC3 · Depends on: — · Est: 0.25d · Kind: test

## For the developer

Three selftest checks that reproduce the bug on HEAD and pass after S2: a fixture repo whose workflow sets a default working directory; one whose step overrides it; and the manifest summary line naming the source file. A check that passes on HEAD has not reproduced anything.

## Done when

- [ ] `python3 story-refinery/scripts/selftest.py | grep -cE '^FAIL +manifest: (workflow default cwd|step cwd overrides|summary names the source)'` → 3 on HEAD - the bug reproduced
- [ ] `python3 story-refinery/scripts/selftest.py | grep -cE '^(ok|FAIL) +manifest: '` → at least 3

_Shared context for every subtask on this story: `context/SKL-2-context.md`._

---

<!-- AGENT-BRIEF v1 BEGIN {"ticket": "SKL-2/S1", "hash": "sha256:0d500bbc3e21d22f"} -->
```json
{
  "objective": "Three named selftest checks - `manifest: workflow default cwd`, `manifest: step cwd overrides`, `manifest: summary names the source` - built on a fixture repo, failing on HEAD and passing once S2 lands.",
  "repo": "skills",
  "branch_hint": "skl-2-repro",
  "read_first": [
    {
      "path": "story-refinery/scripts/selftest.py",
      "why": "check() at l.50; where the evidence/pipeline checks live (l.360)"
    },
    {
      "path": "story-refinery/scripts/evidence.py",
      "why": "detect_commands(root, files) signature at l.94 - call it directly on a temp dir"
    }
  ],
  "entry_points": [
    {
      "path": "story-refinery/scripts/selftest.py",
      "line": 360,
      "symbol": "pipeline suite",
      "why": "add the checks beside the existing manifest assertions"
    }
  ],
  "change_surface": [
    {
      "path": "story-refinery/scripts/selftest.py",
      "role": "modify"
    }
  ],
  "contracts_must_not_break": [],
  "conventions": [
    {
      "rule": "selftest's check(name, ok, detail) prints `ok <name>` or `FAIL <name> <- detail`; a new check is one call.",
      "evidence": "skills/story-refinery/scripts/selftest.py:50"
    },
    {
      "rule": "detect_commands scans CI files line by line with a regex; extend the same loop, do not add a YAML parser.",
      "evidence": "skills/story-refinery/scripts/evidence.py:104"
    }
  ],
  "done_when": [
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py | grep -cE '^FAIL +manifest: (workflow default cwd|step cwd overrides|summary names the source)'",
      "expect": "3 on HEAD - the bug reproduced"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py | grep -cE '^(ok|FAIL) +manifest: '",
      "expect": "at least 3"
    }
  ],
  "forbidden": [
    "Do not touch evidence.py - S2 fixes it; a test that passes on HEAD has not reproduced the bug.",
    "Do not weaken any existing check."
  ],
  "out_of_scope": [
    "The fix (S2)"
  ],
  "rollback": {
    "flag": "",
    "note": "revert the commit; manifests rebuild on next run"
  },
  "preflight": [
    {
      "type": "command",
      "cmd": "grep -n '^def detect_commands' story-refinery/scripts/evidence.py",
      "expect": "line 94"
    },
    {
      "type": "command",
      "cmd": "grep -n '^def check(' story-refinery/scripts/selftest.py",
      "expect": "line 50"
    }
  ],
  "stop_and_ask": [
    "detect_commands cannot be called on a temp dir without a git repo - stop and report which call needs one, do not mock it."
  ],
  "context_budget_hint": "read_first only",
  "provenance": [
    "skills@eeb5595"
  ]
}
```
<!-- AGENT-BRIEF v1 END -->


---

## S2 — [skills] Honour working-directory when lifting CI commands (Sub-task)

Parent: SKL-2 · Covers: AC1, AC2, AC3 · Depends on: S1 · Est: 0.5d · Kind: feature

## For the developer

In detect_commands, track `defaults.run.working-directory` (workflow level) and `working-directory:` (step level, resets per step) with the same line-regex style, and record `cd <dir> && <command>` (D2). Print the source file after each command in the manifest summary. S1's three checks go green; nothing else changes.

## Done when

- [ ] `python3 story-refinery/scripts/selftest.py | grep -cE '^ok +manifest: (workflow default cwd|step cwd overrides|summary names the source)'` → 3
- [ ] `python3 story-refinery/scripts/selftest.py` → PASS  0 failure(s)
- [ ] `rm -f .refinery/manifests/skills@*.json; python3 story-refinery/scripts/evidence.py manifest --config story-refinery/evals/self-run/refinery.yaml | grep -F 'test=cd terrain-architect/reference-impl && python -m pytest tests/ -q -rs'` → one line, ending with (.github/workflows/terrain-architect.yml)

_Shared context for every subtask on this story: `context/SKL-2-context.md`._

---

<!-- AGENT-BRIEF v1 BEGIN {"ticket": "SKL-2/S2", "hash": "sha256:3edba041655c2aa8"} -->
```json
{
  "objective": "detect_commands records CI commands with their working directory as a cd prefix, and the manifest summary line shows each command's source file; S1's checks pass, all others unchanged.",
  "repo": "skills",
  "branch_hint": "skl-2-fix",
  "read_first": [
    {
      "path": "story-refinery/scripts/evidence.py",
      "why": "detect_commands l.94-150; the summary print at l.399"
    },
    {
      "path": ".github/workflows/terrain-architect.yml",
      "why": "the real-world shape: defaults at l.25, the command at l.59"
    }
  ],
  "entry_points": [
    {
      "path": "story-refinery/scripts/evidence.py",
      "line": 104,
      "symbol": "detect_commands workflow loop",
      "why": "where the two keys are tracked"
    },
    {
      "path": "story-refinery/scripts/evidence.py",
      "line": 399,
      "symbol": "manifest summary print",
      "why": "append the source"
    }
  ],
  "change_surface": [
    {
      "path": "story-refinery/scripts/evidence.py",
      "role": "modify"
    }
  ],
  "contracts_must_not_break": [],
  "conventions": [
    {
      "rule": "Scripts are stdlib-only, no network; selftest prints ok/FAIL per named check and a failure total.",
      "evidence": "skills/story-refinery/SKILL.md:821"
    },
    {
      "rule": "selftest's check(name, ok, detail) prints `ok <name>` or `FAIL <name> <- detail`; a new check is one call.",
      "evidence": "skills/story-refinery/scripts/selftest.py:50"
    },
    {
      "rule": "detect_commands scans CI files line by line with a regex; extend the same loop, do not add a YAML parser.",
      "evidence": "skills/story-refinery/scripts/evidence.py:104"
    }
  ],
  "done_when": [
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py | grep -cE '^ok +manifest: (workflow default cwd|step cwd overrides|summary names the source)'",
      "expect": "3"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py",
      "expect": "PASS  0 failure(s)"
    },
    {
      "type": "command",
      "cmd": "rm -f .refinery/manifests/skills@*.json; python3 story-refinery/scripts/evidence.py manifest --config story-refinery/evals/self-run/refinery.yaml | grep -F 'test=cd terrain-architect/reference-impl && python -m pytest tests/ -q -rs'",
      "expect": "one line, ending with (.github/workflows/terrain-architect.yml)"
    }
  ],
  "forbidden": [
    "Do not add a YAML parser or a dependency; the loop is line-regex by convention.",
    "Do not change the manifest schema - commands stay strings (D2).",
    "Do not touch selftest.py beyond nothing - S1 owns it."
  ],
  "out_of_scope": [
    "Path-existence checks for commands (non-goal)",
    "GitLab/Azure equivalents (follow-up)"
  ],
  "rollback": {
    "flag": "",
    "note": "revert the commit; manifests rebuild on next run"
  },
  "preflight": [
    {
      "type": "command",
      "cmd": "grep -n 'working-directory' .github/workflows/terrain-architect.yml",
      "expect": "line 25"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py | grep -cE '^FAIL +manifest: '",
      "expect": "3 - S1 has landed and still fails"
    }
  ],
  "stop_and_ask": [
    "A step's `working-directory:` appears before its `run:` in some workflows and after it in others - if the second shape occurs in a real workflow, stop; the line-by-line scan cannot see ahead."
  ],
  "context_budget_hint": "read_first only",
  "provenance": [
    "skills@eeb5595"
  ]
}
```
<!-- AGENT-BRIEF v1 END -->


---
