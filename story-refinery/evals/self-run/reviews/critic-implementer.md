# Critic packet - The Implementer (`implementer`)

Story: **SKL-1 Every validator code can be looked up**
Bundle digest: `sha256:04bb171ad20e05880bb1980005206e03b4e345a2315d58915c7ed720924698b0`

You are a competent engineer, or an agent, with zero context beyond this packet, who will follow the brief literally.

## Your mandate

Take each subtask in turn and try to execute it from the brief alone. Every point where you would have to guess, ask, or open a file the brief never named is a finding.

## What to hunt for

- the first ambiguity that would make you stop and ask
- a `done_when` you cannot actually run, or whose result you cannot predict
- an objective that needs a file `read_first` never mentions
- an instruction wide enough to justify touching code outside change_surface
- two subtasks that would both plausibly claim the same edit

## Withheld deliberately

You are not being shown the conversation that produced this, the rationale behind any decision, or the author's own assessment. If a choice only makes sense with context you do not have, that is a finding, not a gap in this packet.

## What you must return

A list of findings. Each one:

    id        F1, F2, ...
    severity  blocking | major | minor
    locator   a path into the bundle - story.acceptance_criteria[1],
              subtasks[3].agent_brief.done_when[0]. It must resolve; an
              unresolvable locator is dropped by validate.py (REV005).
    claim     what is wrong, in one sentence
    failure   the concrete thing that goes wrong downstream if it ships as is:
              who does what, and what they get. Not "this is unclear" - name
              the wrong turn the reader takes.

Rules of this panel:

- Your prior is that this refinement is wrong somewhere. Find where.
- "Looks good" is not a verdict. If you genuinely cannot break it, say what you
  tried and why it held - that goes in `attempted`, and it is the only accepted
  form of a clean report (REV004).
- No locator, no finding. Harshness without a locator is vibes, and this skill
  holds you to the same evidence rule it holds the refinement to.
- Do not propose the implementation. You are judging whether the package can be
  implemented correctly by someone who was not in the room, not writing it.
- Judge only what is in this packet. If something you need is missing from it,
  that absence is itself a finding.

## The artefact

```json
{
  "subtasks": [
    {
      "id": "S1",
      "title": "[skills] Register every code behind validate.py --codes",
      "repo": "skills",
      "kind": "feature",
      "estimate_days": 0.5,
      "human": "Every code validate.py and batch.py can emit gets an entry in a CODES dict with a one-line meaning (D1). `validate.py --codes` prints them grouped by PHASE_OF, with severity, and needs no bundle - make the positional optional. BAT joins PHASE_OF (D3). Do not touch selftest or references; S2 owns those.",
      "depends_on": [],
      "agent_brief": {
        "objective": "A CODES registry in validate.py and batch.py covering every emitted code, and a --codes flag (plain and --markdown) that prints it grouped by phase with severity and meaning, runnable without a bundle.",
        "repo": "skills",
        "branch_hint": "skl-1-code-registry",
        "read_first": [
          {
            "path": "story-refinery/scripts/validate.py",
            "why": "Report (l.135), PHASE_OF/phase_of (l.74-93), main() argparse (l.1631)"
          },
          {
            "path": "story-refinery/scripts/batch.py",
            "why": "the five BAT emitters (l.188-243) and main() (l.258)"
          },
          {
            "path": "story-refinery/scripts/selftest.py",
            "why": "read only: the docs suite (l.640) that will consume the registry in S2"
          }
        ],
        "entry_points": [
          {
            "path": "story-refinery/scripts/validate.py",
            "line": 1631,
            "symbol": "main",
            "why": "where --codes is parsed and short-circuits before validate()"
          },
          {
            "path": "story-refinery/scripts/validate.py",
            "line": 88,
            "symbol": "phase_of",
            "why": "grouping for the listing"
          }
        ],
        "change_surface": [
          {
            "path": "story-refinery/scripts/validate.py",
            "role": "modify"
          },
          {
            "path": "story-refinery/scripts/batch.py",
            "role": "modify"
          }
        ],
        "contracts_must_not_break": [],
        "conventions": [
          {
            "rule": "Every code is a string literal as the first argument of rep.error(...) / rep.warn(...).",
            "evidence": "skills/story-refinery/scripts/validate.py:158"
          },
          {
            "rule": "batch.py reports through local error()/warn() closures, same literal-first shape.",
            "evidence": "skills/story-refinery/scripts/batch.py:188"
          },
          {
            "rule": "Phase grouping is the PHASE_OF prefix map; phase_of() picks the longest matching prefix.",
            "evidence": "skills/story-refinery/scripts/validate.py:74"
          },
          {
            "rule": "Scripts are stdlib-only, no network; selftest prints the assertion count rather than docs claiming one.",
            "evidence": "skills/story-refinery/SKILL.md:821"
          }
        ],
        "done_when": [
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/validate.py --codes | grep -E '^BRF009\\b'",
            "expect": "one line, containing '6 briefs'"
          },
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/validate.py --codes | grep -E '^BAT004\\b'",
            "expect": "one line"
          },
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/validate.py --codes | grep -cE '^DOD001\\b'",
            "expect": "1"
          },
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/validate.py --codes --markdown | head -3",
            "expect": "a markdown heading, exit 0"
          },
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/validate.py story-refinery/assets/examples/example-bundle.json --config story-refinery/assets/refinery.example.yaml",
            "expect": "READY  0 error(s), 0 warning(s) - the positional form still works"
          },
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/selftest.py",
            "expect": "PASS  0 failure(s)"
          },
          {
            "type": "assertion",
            "text": "len(CODES) in validate.py plus len(CODES) in batch.py equals the number of distinct code literals in rep.error/rep.warn/error/warn calls across both files"
          }
        ],
        "forbidden": [
          "Do not change any message text, code, severity or call site - the registry is beside the emitters, not in them.",
          "Do not edit selftest.py or anything under references/ - S2 owns them.",
          "Do not add a dependency; stdlib only."
        ],
        "out_of_scope": [
          "Generating references/codes.md (S2)",
          "The selftest gates (S2)",
          "Any SKILL.md edit (Q1 open)"
        ],
        "rollback": {
          "flag": "",
          "note": "additive; revert the commit"
        },
        "preflight": [
          {
            "type": "command",
            "cmd": "grep -n '^class Report' story-refinery/scripts/validate.py",
            "expect": "one hit at line 135"
          },
          {
            "type": "command",
            "cmd": "grep -n '^PHASE_OF = {' story-refinery/scripts/validate.py",
            "expect": "one hit"
          },
          {
            "type": "command",
            "cmd": "grep -c 'rep\\.\\(error\\|warn\\)(\"' story-refinery/scripts/validate.py",
            "expect": "191 - the emitter count the registry must cover"
          },
          {
            "type": "command",
            "cmd": "grep -c '^ *\\(error\\|warn\\)(\"BAT' story-refinery/scripts/batch.py",
            "expect": "5"
          }
        ],
        "stop_and_ask": [
          "A code is emitted at more than one severity (DOD001 by rule severity, BAS003) - register it once as 'error | warn'; do not split it into two codes.",
          "A code literal appears in a script other than validate.py or batch.py - stop; the story scoped the registry to those two."
        ],
        "context_budget_hint": "read_first only; the two scripts and the one suite are the whole surface",
        "provenance": [
          "skills@a837f43"
        ]
      }
    },
    {
      "id": "S2",
      "title": "[skills] Gate references/codes.md in selftest",
      "repo": "skills",
      "kind": "test",
      "estimate_days": 0.5,
      "human": "Commit `references/codes.md` as the output of `validate.py --codes --markdown` (D2). Extend the docs suite: emitted codes == registered codes both ways, and codes.md byte-equal to the generator, with a message that says how to regenerate. Depends on S1. Do not hand-edit codes.md.",
      "depends_on": [
        "S1"
      ],
      "agent_brief": {
        "objective": "references/codes.md committed and two selftest checks that fail on a registry gap in either direction or a stale file.",
        "repo": "skills",
        "branch_hint": "skl-1-codes-index",
        "read_first": [
          {
            "path": "story-refinery/scripts/selftest.py",
            "why": "the docs suite at l.640 - extend it, no new suite"
          },
          {
            "path": "story-refinery/scripts/validate.py",
            "why": "read only: CODES and --codes --markdown as landed by S1"
          },
          {
            "path": "story-refinery/scripts/batch.py",
            "why": "read only: its CODES"
          }
        ],
        "entry_points": [
          {
            "path": "story-refinery/scripts/selftest.py",
            "line": 640,
            "symbol": "docs consistency suite",
            "why": "where the new checks go"
          }
        ],
        "change_surface": [
          {
            "path": "story-refinery/scripts/selftest.py",
            "role": "modify"
          },
          {
            "path": "story-refinery/references/codes.md",
            "role": "create"
          }
        ],
        "contracts_must_not_break": [],
        "conventions": [
          {
            "rule": "Scripts are stdlib-only, no network; selftest prints the assertion count rather than docs claiming one.",
            "evidence": "skills/story-refinery/SKILL.md:821"
          },
          {
            "rule": "The docs suite already verifies docs -> code with a regex over references and config; extend it, do not add a second suite.",
            "evidence": "skills/story-refinery/scripts/selftest.py:640"
          }
        ],
        "done_when": [
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/validate.py --codes --markdown | diff - story-refinery/references/codes.md",
            "expect": "no output, exit 0"
          },
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/selftest.py | grep -E 'registered|stale|codes.md'",
            "expect": "the new checks, each 'ok'"
          },
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/selftest.py",
            "expect": "PASS  0 failure(s)"
          },
          {
            "type": "assertion",
            "text": "Temporarily appending rep.error(\"ZZZ999\", \"x\", \"x\") to a check in validate.py makes selftest fail naming ZZZ999; reverting restores PASS"
          },
          {
            "type": "assertion",
            "text": "Editing one character in codes.md makes selftest fail with a message containing 'regenerate'; regenerating restores PASS"
          }
        ],
        "forbidden": [
          "Do not hand-edit references/codes.md - regenerate it.",
          "Do not modify validate.py or batch.py - S1 owns them; if the generator output is wrong, that is a finding on S1.",
          "Do not add a new suite; extend the docs-consistency suite."
        ],
        "out_of_scope": [
          "Any SKILL.md edit (Q1 open)",
          "Changing what --codes prints (S1)"
        ],
        "rollback": {
          "flag": "",
          "note": "additive; revert the commit"
        },
        "preflight": [
          {
            "type": "command",
            "cmd": "python3 story-refinery/scripts/validate.py --codes >/dev/null",
            "expect": "exit 0 - S1 has landed"
          },
          {
            "type": "command",
            "cmd": "grep -n 'no invented validator codes' story-refinery/scripts/selftest.py",
            "expect": "one hit"
          }
        ],
        "stop_and_ask": [
          "`--codes --markdown` output is not deterministic between runs (ordering) - stop; determinism is S1's to fix, not something to sort around here."
        ],
        "context_budget_hint": "read_first only; the two scripts and the one suite are the whole surface",
        "provenance": [
          "skills@a837f43"
        ]
      }
    }
  ]
}
```
