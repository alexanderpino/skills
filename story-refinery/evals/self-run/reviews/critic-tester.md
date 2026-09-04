# Critic packet - The Tester (`tester`)

Story: **SKL-1 Every validator code can be looked up**
Bundle digest: `sha256:04bb171ad20e05880bb1980005206e03b4e345a2315d58915c7ed720924698b0`

You are a QA engineer who has to turn every criterion into a test that can fail.

## Your mandate

Try to write a failing test for each acceptance criterion. Any criterion you cannot make binary - pass here, fail there - is a finding, and so is any behaviour the criteria never pin down.

## What to hunt for

- a criterion with no observable outcome, or one that restates the title
- a missing boundary: the empty case, the maximum, the duplicate, the retry
- failure paths nobody specified - what happens when the dependency is down
- concurrency: two of these at once, or the same one twice
- a non-functional row left blank rather than answered 'unchanged'

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
  "acceptance_criteria": [
    {
      "id": "AC1",
      "rule": "`validate.py --codes` prints every code validate.py and batch.py can emit - one per line with its phase, severity and a one-line meaning - and needs no bundle argument.",
      "examples": [
        {
          "case": "`validate.py --codes` with no other argument",
          "expect": "exit 0; the BRF009 line carries phase '6 briefs'; a BAT004 line is present"
        },
        {
          "case": "DOD001, emitted as error or warn depending on the rule's severity",
          "expect": "listed exactly once, severity 'error | warn'"
        },
        {
          "case": "`validate.py bundle.json --codes` (a bundle given as well)",
          "expect": "the code list, the bundle is not validated, exit 0"
        }
      ]
    },
    {
      "id": "AC2",
      "rule": "references/codes.md is byte-identical to the output of `validate.py --codes --markdown`, grouped by phase in PHASE_OF order.",
      "examples": [
        {
          "case": "regenerate, then diff against the committed file",
          "expect": "empty diff, exit 0"
        },
        {
          "case": "one meaning hand-edited in codes.md",
          "expect": "selftest fails: 'references/codes.md is stale - regenerate it'"
        },
        {
          "case": "codes.md absent (boundary)",
          "expect": "selftest fails with the same message, does not crash"
        }
      ]
    },
    {
      "id": "AC3",
      "rule": "selftest fails when the set of codes the scripts emit and the set the registry declares differ in either direction.",
      "examples": [
        {
          "case": "a new rep.error(\"ZZZ999\", ...) call with no registry entry",
          "expect": "selftest fails naming ZZZ999 as unregistered"
        },
        {
          "case": "a registry entry QQQ001 that no script emits",
          "expect": "selftest fails naming QQQ001 as a dead entry"
        },
        {
          "case": "the two sets are equal (boundary)",
          "expect": "both checks pass and appear in the assertion count"
        }
      ]
    }
  ],
  "non_functional": {
    "performance": "unchanged - --codes reads a dict, no bundle, no scan",
    "concurrency": "unchanged",
    "failure": "unchanged - --codes cannot fail on bundle content; a registry gap fails selftest, never a validation run",
    "data": "none",
    "security": "none - no new input is parsed",
    "observability": "the two new selftest assertions are named and counted in its output",
    "compatibility": "the positional bundle argument and every existing flag keep their behaviour; --codes is additive"
  },
  "non_goals": [
    "Rewording any finding message - the registry carries a meaning, the call site keeps its message.",
    "Adding the codes.md row to SKILL.md's reference table: pending Q1; SKILL.md is not in the change surface."
  ],
  "done_when": [
    {
      "subtask": "S1",
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
      ]
    },
    {
      "subtask": "S2",
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
      ]
    }
  ]
}
```
