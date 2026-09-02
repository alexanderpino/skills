# Critic packet - The Stakeholder (`stakeholder`)

Story: **SKL-1 Every validator code can be looked up**
Bundle digest: `sha256:04bb171ad20e05880bb1980005206e03b4e345a2315d58915c7ed720924698b0`

You are the person who wrote the original ask and has not seen the refinement.

## Your mandate

Compare the original text against what is being planned. Name what was asked for and is missing, and what is being built that nobody asked for.

## What to hunt for

- an outcome in the source text that no criterion covers
- scope that appears in the plan but not in the source text or a non-goal
- a constraint from the source text quietly dropped
- a question answered by assumption where the answer was the point of asking

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
  "source_text": "When validate.py reports a code like BRF009 there is nowhere to look it up: 55 of the 153 codes the validator and batch.py can emit are documented in no reference file, so a maintainer or an implementer reading a finding has to open the validator source. Add `validate.py --codes` that lists every code with the phase it belongs to and what it means, generate references/codes.md from it, and make selftest's docs-consistency suite fail when a code can be emitted that codes.md does not list, so the index cannot rot. Maintainers only; nothing changes for someone running the validator today.",
  "title": "Every validator code can be looked up",
  "summary_human": "A finding like BRF009 is currently a dead end unless you open validate.py: 55 of 153 codes are documented nowhere. This adds an explicit registry of every code with a one-line meaning, a `--codes` flag that prints it, a generated `references/codes.md`, and two selftest checks that fail the moment a code is emitted without an entry or the file goes stale. Two subtasks, one repo, half a day each.",
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
  "non_goals": [
    "Rewording any finding message - the registry carries a meaning, the call site keeps its message.",
    "Adding the codes.md row to SKILL.md's reference table: pending Q1; SKILL.md is not in the change surface."
  ],
  "subtask_titles": [
    "[skills] Register every code behind validate.py --codes",
    "[skills] Gate references/codes.md in selftest"
  ],
  "open_questions": [
    {
      "id": "Q1",
      "text": "Should references/codes.md also get a row in SKILL.md's reference table, or is the Scripts bullet enough?",
      "owner": "alexander.pino",
      "blocking": false,
      "asked": {
        "to": "alexander.pino",
        "when": "alexander.pino",
        "channel": "alexander.pino"
      },
      "guess": "Yes, one row: 'Any time validate.py names a code you do not know'. Left out of this story so the table edit is not made while the answer is open."
    },
    {
      "id": "Q2",
      "text": "Is the success signal 'zero undocumented codes, enforced by selftest' - or is a generated index without the gate enough?",
      "owner": "alexander.pino",
      "blocking": false,
      "asked": {
        "to": "alexander.pino",
        "when": "alexander.pino",
        "channel": "alexander.pino"
      },
      "guess": "Enforced. An index without the gate is the state we are in now, one release later."
    },
    {
      "id": "Q3",
      "text": "Severity column: is 'error | warn' acceptable for a code emitted at both severities (DOD001, BAS003), or should such codes be split?",
      "owner": "alexander.pino",
      "blocking": false,
      "asked": {
        "to": "alexander.pino",
        "when": "alexander.pino",
        "channel": "alexander.pino"
      },
      "guess": "Keep one code with 'error | warn'; splitting renames codes people may already cite."
    }
  ]
}
```
