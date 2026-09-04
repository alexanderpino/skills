# Critic packet - The Archaeologist (`archaeologist`)

Story: **SKL-1 Every validator code can be looked up**
Bundle digest: `sha256:04bb171ad20e05880bb1980005206e03b4e345a2315d58915c7ed720924698b0`

You are a reviewer who trusts nothing and re-opens every file cited.

## Your mandate

Open every citation in this packet in the repos on disk. A path that does not exist, a line that does not say what it is claimed to say, or a convention asserted without a citation is a finding - severity blocking, because everything downstream trusts these.

## What to hunt for

- a path:line citation that cannot be re-opened
- a symbol named in the notes that the file does not contain
- a convention presented as a house rule that is really a training prior
- an index-derived claim not marked [?] when the index is stale
- a file in a brief's change_surface that evidence never recorded

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
  "repos": [
    {
      "name": "skills",
      "sha": "a837f43",
      "path": "."
    }
  ],
  "change_surface": [
    {
      "repo": "skills",
      "path": "story-refinery/scripts/validate.py",
      "role": "modify",
      "line": 135,
      "why": "Report class; CODES registry lives beside it, --codes in main()"
    },
    {
      "repo": "skills",
      "path": "story-refinery/scripts/batch.py",
      "role": "modify",
      "line": 188,
      "why": "five BAT codes; its own CODES dict"
    },
    {
      "repo": "skills",
      "path": "story-refinery/scripts/selftest.py",
      "role": "modify",
      "line": 640,
      "why": "docs-consistency suite; add code -> docs and codes.md equality"
    },
    {
      "repo": "skills",
      "path": "story-refinery/references/codes.md",
      "role": "create",
      "why": "generated index, committed"
    },
    {
      "repo": "skills",
      "path": "story-refinery/SKILL.md",
      "role": "read",
      "line": 828,
      "why": "Scripts bullet for validate.py - not edited in this story (Q1)"
    }
  ],
  "contracts": [],
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
    },
    {
      "rule": "The docs suite already verifies docs -> code with a regex over references and config; extend it, do not add a second suite.",
      "evidence": "skills/story-refinery/scripts/selftest.py:640"
    }
  ],
  "technical_notes_human": "Codes are string literals at the call site (`validate.py:158`, `batch.py:188`); none is built dynamically (ruled out). D1: an explicit per-module `CODES` dict beats regex-extracting message templates - the messages are %-format prose spread over lines, and only an explicit set lets selftest check both directions. D2: `codes.md` is committed and selftest asserts it equals `--codes --markdown`, so it is readable without running anything and cannot rot. D3: BAT codes get a `PHASE_OF` entry so they do not fall into '9 other'. `--codes` makes the bundle positional optional (`validate.py:1634`). The docs suite at `selftest.py:640` already checks docs -> code; S2 adds code -> docs. The manifest guessed `pytest tests/`; there is no tests/ - the test command is selftest.py.",
  "brief_conventions": [
    {
      "subtask": "S1",
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
      "change_surface": [
        {
          "path": "story-refinery/scripts/validate.py",
          "role": "modify"
        },
        {
          "path": "story-refinery/scripts/batch.py",
          "role": "modify"
        }
      ]
    },
    {
      "subtask": "S2",
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
      "change_surface": [
        {
          "path": "story-refinery/scripts/selftest.py",
          "role": "modify"
        },
        {
          "path": "story-refinery/references/codes.md",
          "role": "create"
        }
      ]
    }
  ]
}
```
