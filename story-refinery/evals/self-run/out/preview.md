# Push preview — SKL-1 Every validator code can be looked up


Adapter: **markdown** · markup: markdown · subtasks: none · agent brief sink: **description_tail**

_Untailored: no team house rules were applied to this refinement._

## Execution waves

Everything inside a wave can run in parallel. No two subtasks in the same wave write the same file.

- **Wave 1**: S1
- **Wave 2**: S2

## Triage

Labels: documentation · components: story-refinery · type: Story · priority: Medium

No label on this item changes the refinement.

## Review

Method: **critics** · critics: implementer (fresh), tester (fresh), archaeologist (fresh), stakeholder (fresh) · findings: 39

Fixed before handover: ARC-F1, ARC-F2, ARC-F3, ARC-F4, ARC-F5, ARC-F6, ARC-F7, IMP-F1, IMP-F2, IMP-F3, IMP-F4, IMP-F5, IMP-F6, IMP-F7, IMP-F8, IMP-F9, IMP-F10, IMP-F11, TES-F1, TES-F2, TES-F3, TES-F4, TES-F5, TES-F6, TES-F7, TES-F8, TES-F9, TES-F10, STA-F1, STA-F2, STA-F3, STA-F4, STA-F5, STA-F6, STA-F7, STA-F8, STA-F9, STA-F10, ARC-F4b.


_Field names and issue types below are unverified `[?]` until probed against the live tracker._

---

## SKL-1 — Every validator code can be looked up (Story)

## Why / What

A finding like BRF009 is currently a dead end unless you open validate.py: 56 of 160 codes are documented nowhere. This adds an explicit registry of every code with a one-line meaning, a `--codes` flag (plain, JSON, markdown), a generated `references/codes.md`, a row for it in SKILL.md, and four selftest checks: emitted equals registered both ways, severity matches the call sites, the file is current, and each meaning is a meaning. Two subtasks, one repo, one day and a half.

## Acceptance criteria

**AC1 — `validate.py --codes` prints one line per code the three emitting scripts (validate.py, batch.py, criteria.py) can produce - `CODE<TAB>phase<TAB>severity<TAB>meaning`, sorted by phase label then code - and runs before any bundle is opened.**
- `validate.py --codes` alone → exit 0; a line `BRF009\t6 briefs\t...`; a line for BAT004 under `9 batch`; a line for AC012
- `validate.py nope.json --codes` (bundle path does not exist) → the code list, exit 0 - --codes dispatches before the bundle is read
- `validate.py --codes --json` → a JSON list of {code, phase, severity, meaning}; --strict, --flat and --config are ignored under --codes
- `validate.py --markdown` without --codes, or no bundle and no --codes (boundary) → argparse usage error, exit 2 - the documented usage error for a missing bundle is unchanged
- READY003, emitted as warn at two call sites and error at none → severity 'warn'; BAS003 (both) 'error | warn'; DOD001 (severity from the DoD rule) 'config'

**AC2 — references/codes.md equals `validate.py --codes --markdown` after normalising line endings: one `## <phase>` heading per phase label in sorted order, a table of code | severity | meaning under each.**
- regenerate, then diff against the committed file → empty diff, exit 0
- one meaning hand-edited in codes.md → selftest fails 'codes: references/codes.md is current' with 'regenerate with validate.py --codes --markdown' in the detail
- codes.md checked out with CRLF (boundary) → the check passes - comparison is on LF-normalised text
- codes.md absent (boundary) → the same check fails, selftest does not crash

**AC3 — selftest fails when the set of codes the three scripts emit and the set the registries declare differ in either direction, and when a registered severity disagrees with the call sites.**
- a new rep.error("ZZZ999", ...) with no registry entry → 'codes: every emitted code is registered' fails naming ZZZ999
- a registry entry QQQ001 no call site emits → 'codes: no registered code is dead' fails naming QQQ001 - registry literals are dict keys (`"QQQ001": (`), which the call-site regex does not match
- READY003 registered as 'error' while both call sites are rep.warn → 'codes: severity matches the call sites' fails naming READY003
- the sets and severities agree (boundary) → all four `codes:` checks print ok

**AC4 — Every registered meaning is a meaning: at least six words, not the code itself, and not a placeholder.**
- "BRF009": ("error", "BRF009") → 'codes: every meaning is a meaning' fails naming BRF009
- a meaning containing TODO or TBD → the same check fails
- a six-word meaning stating the condition (boundary) → passes

## Non-goals

- Rewording any finding message - the registry carries a meaning, the call site keeps its message.
- Changing what validate.py prints for a bundle - the phase grouping in main() is untouched; BAT's new PHASE_OF entry is never reached by a validation run because only batch.py emits BAT codes.

## Technical notes

Emitters are validate.py, batch.py and criteria.py (AC012 is criteria's alone, `criteria.py:106`); summary.py and selftest.py contain code literals as consumers, not emitters. 'Emitted' is mechanical: a code literal as first argument of error/warn/report/add or as a `("ERROR"|"WARN", "CODE", ...)` tuple in criteria.py - which is how DOD001, emitted via an alias at `validate.py:1129`, is counted. D1: explicit per-module `CODES` dicts, `"CODE": (severity, meaning)`; dict-key syntax is what keeps the dead-entry check from matching the registry itself. D2: codes.md committed, selftest asserts LF-normalised equality. D3: `PHASE_OF["BAT"] = "9 batch"`. D5: output sorted by phase label then code, like main()'s own grouping. D6: --codes dispatches before the bundle is opened; --json under --codes emits a list. The existing docs regex `[A-Z]{3,6}` skips AC/DT - S2 widens it to `{2,6}`. SKILL.md:843 still says 'six suites'; S2 fixes it with the reference-table row.

**Decisions**
- D1 Where does the meaning of a code come from? → **An explicit CODES dict per module with a one-line meaning**. A reader wants the condition, not the message; and the both-ways check in AC3 needs a set whose literals are syntactically distinct from call sites - dict keys are.
- D2 Is codes.md committed, or generated at test time? → **Committed, with selftest asserting it equals the generator's output**. The skill is installed as plain files and read by agents that may not run scripts; a committed file is the only one they see.
- D3 Where do batch.py's BAT codes sit in the phase grouping, and with which label? → **Add BAT to PHASE_OF as its own group**. 'other' is where meaning goes to die. Label '9 batch': the batch check runs before the push, alongside emit. A validation run never emits BAT, so main()'s grouped output is unchanged.
- D4 Which scripts count as emitters, and how does --codes reach their registries? → **validate.py, batch.py, criteria.py; --codes imports the other two lazily**. criteria.py:106 emits through a findings list; the archaeologist re-opened it. Consumers (summary.py, selftest.py) are excluded by the mechanical definition of 'emitted'.
- D5 What does --codes print, and in which order? → **One TSV line per code, sorted by (phase label, code); --markdown groups under headings in the same order; --json a list**. PHASE_OF insertion order is not phase order (ENB, BAS sit after IRR); sorting by label is the ordering main() already uses, and it is the only one two implementers would reproduce identically.
- D6 Where is the severity column from, given ten codes emitted at both severities and DOD001 whose severity a config rule decides? → **Authored in the registry, and selftest compares it to the call sites: error | warn | 'error | warn' | 'config' for an aliased emitter**. The tester found the column would be wrong for ten codes with nothing able to fail. Codes are never split - REV009 and PND001 are cited in existing findings.


**Risks**
- R1 Registry and emitters drift apart after the next gate is added → selftest compares the two sets both ways (AC3) _(detected by: selftest failure naming the code)_
- R2 codes.md goes stale because regeneration is a manual step → selftest asserts byte equality (AC2); the failure message says how to regenerate _(detected by: selftest failure 'codes.md is stale')_
- R3 Registry meanings become a paraphrase of the message and add nothing → a meaning states the condition that trips the gate, not the advice; reviewed in S1's PR _(detected by: none mechanical - reviewer judgement)_
- R4 Making the bundle positional optional breaks the documented `validate.py bundle.json` form → nargs='?' with an explicit error when neither --codes nor a bundle is given _(detected by: selftest 'flags valid' and the pipeline suite)_

## Subtasks

| # | Title | Repo | Covers | Depends on | Est |
|---|-------|------|--------|------------|-----|
| S1 | [skills] Register every code behind validate.py --codes | skills | AC1 | — | 1.0d |
| S2 | [skills] Gate references/codes.md in selftest | skills | AC2, AC3, AC4 | S1 | 0.5d |

## Non-functional

- **performance**: unchanged - --codes reads a dict, no bundle, no scan
- **concurrency**: unchanged
- **failure**: unchanged - --codes cannot fail on bundle content; a registry gap fails selftest, never a validation run
- **data**: none
- **security**: none - no new input is parsed
- **observability**: four selftest checks named `codes: ...` print ok/FAIL by name; there is no assertion count in selftest output
- **compatibility**: the positional bundle and every existing flag behave as today, including the usage error when the bundle is missing; --codes/--markdown are additive and dispatch before the bundle is opened

_Blast radius: 1 repo(s), 6 primary + 0 secondary file(s), 0 contract(s)._


## Subtask checklist

- [ ] [skills] Register every code behind validate.py --codes
- [ ] [skills] Gate references/codes.md in selftest


---

## S1 — [skills] Register every code behind validate.py --codes (Sub-task)

Parent: SKL-1 · Covers: AC1 · Depends on: — · Est: 1.0d · Kind: feature

## For the developer

Every code validate.py, batch.py and criteria.py can emit gets an entry in a per-module CODES dict - `"CODE": (severity, meaning)` (D1, D4, D6). `validate.py --codes` prints one TSV line per code sorted by phase label then code; `--markdown` groups under headings; `--json` a list (D5); all dispatch before any bundle is opened. `PHASE_OF["BAT"] = "9 batch"` (D3). No selftest, references or SKILL.md edits - S2.

## Done when

- [ ] `python3 story-refinery/scripts/validate.py --codes | grep -P '^BRF009\t6 briefs\t'` → one line
- [ ] `python3 story-refinery/scripts/validate.py --codes | grep -P '^BAT004\t9 batch\t'` → one line
- [ ] `python3 story-refinery/scripts/validate.py --codes | grep -cP '^(AC012|DOD001)\t'` → 2
- [ ] `python3 story-refinery/scripts/validate.py --codes | grep -P '^READY003\t[^\t]+\twarn\t'` → one line - severity derived from two rep.warn call sites
- [ ] `python3 story-refinery/scripts/validate.py --codes | wc -l` → 160
- [ ] `python3 story-refinery/scripts/validate.py nope.json --codes >/dev/null; echo $?` → 0 - dispatch happens before the bundle is read
- [ ] `python3 story-refinery/scripts/validate.py --codes --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d), sorted(d[0]))'` → 160 ['code', 'meaning', 'phase', 'severity']
- [ ] `python3 story-refinery/scripts/validate.py --markdown >/dev/null 2>&1; echo $?` → 2 - --markdown needs --codes
- [ ] `python3 story-refinery/scripts/validate.py >/dev/null 2>&1; echo $?` → 2 - the documented usage error for a missing bundle is unchanged
- [ ] `python3 story-refinery/scripts/validate.py story-refinery/assets/examples/example-bundle.json --config story-refinery/assets/refinery.example.yaml` → READY  0 error(s), 0 warning(s)
- [ ] `python3 story-refinery/scripts/selftest.py` → PASS  0 failure(s) - S2's checks are not in yet; the existing suites must stay green
- [ ] The union of CODES keys across the three modules equals the set of literals matched by the regex (?:\b(?:error|warn|report|add)\(\s*|"code"\s*:\s*|\(\s*"(?:ERROR|WARN)"\s*,\s*)"([A-Z]{2,6}\d{3})" over the same three files - 160 codes - and no key appears in two modules

_Shared context for every subtask on this story: `context/SKL-1-context.md`._

---

<!-- AGENT-BRIEF v1 BEGIN {"ticket": "SKL-1/S1", "hash": "sha256:33e5221c31dbd629"} -->
```json
{
  "objective": "Per-module CODES registries (validate.py, batch.py, criteria.py) covering every emitted code with severity and a one-line meaning, and a --codes flag with --markdown and --json variants, printed in (phase label, code) order, dispatching before the bundle is read.",
  "repo": "skills",
  "branch_hint": "skl-1-code-registry",
  "read_first": [
    {
      "path": "story-refinery/scripts/validate.py",
      "why": "Report (l.135), PHASE_OF/phase_of (l.74-93), the DOD001 alias (l.1129), main() (l.1631)"
    },
    {
      "path": "story-refinery/scripts/batch.py",
      "why": "the five BAT emitters (l.188-243)"
    },
    {
      "path": "story-refinery/scripts/criteria.py",
      "why": "the findings-list emitter (l.106) and AC012"
    },
    {
      "path": "story-refinery/scripts/selftest.py",
      "why": "read only: the docs suite (l.640) that S2 will extend; how check() prints (l.51)"
    }
  ],
  "entry_points": [
    {
      "path": "story-refinery/scripts/validate.py",
      "line": 1631,
      "symbol": "main",
      "why": "--codes is parsed and returns before the bundle is opened"
    },
    {
      "path": "story-refinery/scripts/validate.py",
      "line": 88,
      "symbol": "phase_of",
      "why": "the phase label per code"
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
    },
    {
      "path": "story-refinery/scripts/criteria.py",
      "role": "modify"
    }
  ],
  "contracts_must_not_break": [],
  "conventions": [
    {
      "rule": "A code is a string literal as the first argument of rep.error(...)/rep.warn(...), or of a local alias of them (report(...) at l.1129).",
      "evidence": "skills/story-refinery/scripts/validate.py:164"
    },
    {
      "rule": "batch.py reports through local error()/warn() closures, same literal-first shape.",
      "evidence": "skills/story-refinery/scripts/batch.py:188"
    },
    {
      "rule": "criteria.py reports through a findings list of (\"ERROR\"|\"WARN\", \"CODE\", message) tuples.",
      "evidence": "skills/story-refinery/scripts/criteria.py:106"
    },
    {
      "rule": "Phase grouping is the PHASE_OF prefix map; phase_of() picks the longest matching prefix; main() prints groups in sorted(phase) order.",
      "evidence": "skills/story-refinery/scripts/validate.py:74"
    },
    {
      "rule": "Scripts are stdlib-only, no network (SKILL.md:821); selftest prints ok/FAIL per named check and a failure total, never an assertion count (selftest.py:51, :1516).",
      "evidence": "skills/story-refinery/SKILL.md:821"
    }
  ],
  "done_when": [
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes | grep -P '^BRF009\\t6 briefs\\t'",
      "expect": "one line"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes | grep -P '^BAT004\\t9 batch\\t'",
      "expect": "one line"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes | grep -cP '^(AC012|DOD001)\\t'",
      "expect": "2"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes | grep -P '^READY003\\t[^\\t]+\\twarn\\t'",
      "expect": "one line - severity derived from two rep.warn call sites"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes | wc -l",
      "expect": "160"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py nope.json --codes >/dev/null; echo $?",
      "expect": "0 - dispatch happens before the bundle is read"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d), sorted(d[0]))'",
      "expect": "160 ['code', 'meaning', 'phase', 'severity']"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --markdown >/dev/null 2>&1; echo $?",
      "expect": "2 - --markdown needs --codes"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py >/dev/null 2>&1; echo $?",
      "expect": "2 - the documented usage error for a missing bundle is unchanged"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py story-refinery/assets/examples/example-bundle.json --config story-refinery/assets/refinery.example.yaml",
      "expect": "READY  0 error(s), 0 warning(s)"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py",
      "expect": "PASS  0 failure(s) - S2's checks are not in yet; the existing suites must stay green"
    },
    {
      "type": "assertion",
      "text": "The union of CODES keys across the three modules equals the set of literals matched by the regex (?:\\b(?:error|warn|report|add)\\(\\s*|\"code\"\\s*:\\s*|\\(\\s*\"(?:ERROR|WARN)\"\\s*,\\s*)\"([A-Z]{2,6}\\d{3})\" over the same three files - 160 codes - and no key appears in two modules"
    }
  ],
  "forbidden": [
    "Do not change any message text, code, severity or call site - the registry sits beside the emitters, not in them.",
    "Do not edit selftest.py, anything under references/, or SKILL.md - S2 owns them.",
    "Do not change what main() prints for a bundle; the BAT entry in PHASE_OF is unreachable from a validation run.",
    "Do not split a dual-severity code into two codes.",
    "Do not add a dependency; stdlib only."
  ],
  "out_of_scope": [
    "Generating references/codes.md and the selftest gates (S2)",
    "The SKILL.md row and the 'six suites' correction (S2)"
  ],
  "rollback": {
    "flag": "",
    "note": "additive; revert the commit"
  },
  "preflight": [
    {
      "type": "command",
      "cmd": "grep -n '^class Report' story-refinery/scripts/validate.py",
      "expect": "one hit, line 135"
    },
    {
      "type": "command",
      "cmd": "grep -n '^PHASE_OF = {' story-refinery/scripts/validate.py",
      "expect": "one hit"
    },
    {
      "type": "command",
      "cmd": "grep -n 'report = rep.error if' story-refinery/scripts/validate.py",
      "expect": "one hit, line 1129 - the aliased DOD001 emitter"
    },
    {
      "type": "command",
      "cmd": "grep -c 'rep\\.\\(error\\|warn\\)(\"' story-refinery/scripts/validate.py",
      "expect": "191 call-site lines; NOT the registry size, which is the distinct-code count in done_when"
    },
    {
      "type": "command",
      "cmd": "grep -n '\"AC012\"' story-refinery/scripts/criteria.py",
      "expect": "at least one hit"
    }
  ],
  "stop_and_ask": [
    "A *call* passing a code literal (error/warn/report/add, or a \"code\": value) exists in a script other than validate.py, batch.py or criteria.py - stop; the story scoped emitters to those three. Literals in summary.py and selftest.py are consumers and are expected.",
    "A code is emitted at both severities at different call sites - register it once as 'error | warn'. DOD001, whose severity a DoD rule decides, is 'config'. Do not split codes.",
    "The distinct-code count differs from 160 - the story was refined at 37ae4ae; report the difference rather than adjusting the assertion."
  ],
  "context_budget_hint": "read_first only; the two scripts and the one suite are the whole surface",
  "provenance": [
    "skills@a837f43"
  ]
}
```
<!-- AGENT-BRIEF v1 END -->


---

## S2 — [skills] Gate references/codes.md in selftest (Sub-task)

Parent: SKL-1 · Covers: AC2, AC3, AC4 · Depends on: S1 · Est: 0.5d · Kind: test

## For the developer

Commit `references/codes.md` as `validate.py --codes --markdown` output (D2) and add its row to SKILL.md's reference table - the docs suite requires every reference file be mentioned (selftest.py:609) - plus the `--codes` mention in the Scripts bullet and the 'six suites' fix at l.843. Extend the docs suite with four `codes:` checks and widen its code regex to `{2,6}`. Depends on S1. Never hand-edit codes.md.

## Done when

- [ ] `python3 story-refinery/scripts/validate.py --codes --markdown | diff <(tr -d '\r') <(tr -d '\r' < story-refinery/references/codes.md)` → no output, exit 0
- [ ] `python3 story-refinery/scripts/selftest.py | grep -cE '^ok +codes: '` → 5
- [ ] `python3 story-refinery/scripts/selftest.py` → PASS  0 failure(s)
- [ ] `grep -c 'references/codes.md' story-refinery/SKILL.md` → at least 1
- [ ] `grep -c 'six suites' story-refinery/SKILL.md` → 0
- [ ] Temporarily appending rep.error("ZZZ999", "x", "x") inside a check in validate.py makes 'codes: every emitted code is registered' FAIL naming ZZZ999; reverting restores PASS
- [ ] Temporarily adding "QQQ001": ("error", "a dead entry nothing emits at all") to CODES makes 'codes: no registered code is dead' FAIL naming QQQ001
- [ ] Editing one character in codes.md makes 'codes: references/codes.md is current' FAIL with 'regenerate' in the detail; regenerating restores PASS

_Shared context for every subtask on this story: `context/SKL-1-context.md`._

---

<!-- AGENT-BRIEF v1 BEGIN {"ticket": "SKL-1/S2", "hash": "sha256:eda9cf364dab9204"} -->
```json
{
  "objective": "references/codes.md committed with its SKILL.md row, and four named selftest checks - `codes: every emitted code is registered`, `codes: no registered code is dead`, `codes: severity matches the call sites`, `codes: references/codes.md is current` - plus `codes: every meaning is a meaning`, all in the existing docs suite, with the suite's code regex widened from {3,6} to {2,6} so AC/DT codes are covered.",
  "repo": "skills",
  "branch_hint": "skl-1-codes-index",
  "read_first": [
    {
      "path": "story-refinery/scripts/selftest.py",
      "why": "the docs suite (l.597-653): its regex at l.645/652 skips two-letter prefixes; check() at l.51 prints 'ok <name>'"
    },
    {
      "path": "story-refinery/scripts/validate.py",
      "why": "read only: CODES, --codes --markdown, and the call-site regex from S1's assertion"
    },
    {
      "path": "story-refinery/SKILL.md",
      "why": "the reference table (l.796-813), the Scripts bullet (l.828), 'six suites' (l.843)"
    }
  ],
  "entry_points": [
    {
      "path": "story-refinery/scripts/selftest.py",
      "line": 640,
      "symbol": "docs consistency suite",
      "why": "where the five checks go"
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
    },
    {
      "path": "story-refinery/SKILL.md",
      "role": "modify"
    }
  ],
  "contracts_must_not_break": [],
  "conventions": [
    {
      "rule": "Scripts are stdlib-only, no network (SKILL.md:821); selftest prints ok/FAIL per named check and a failure total, never an assertion count (selftest.py:51, :1516).",
      "evidence": "skills/story-refinery/SKILL.md:821"
    },
    {
      "rule": "The docs suite verifies docs -> code with a regex over references, config and SKILL.md; extend it, do not add a second suite.",
      "evidence": "skills/story-refinery/scripts/selftest.py:640"
    }
  ],
  "done_when": [
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes --markdown | diff <(tr -d '\\r') <(tr -d '\\r' < story-refinery/references/codes.md)",
      "expect": "no output, exit 0"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py | grep -cE '^ok +codes: '",
      "expect": "5"
    },
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/selftest.py",
      "expect": "PASS  0 failure(s)"
    },
    {
      "type": "command",
      "cmd": "grep -c 'references/codes.md' story-refinery/SKILL.md",
      "expect": "at least 1"
    },
    {
      "type": "command",
      "cmd": "grep -c 'six suites' story-refinery/SKILL.md",
      "expect": "0"
    },
    {
      "type": "assertion",
      "text": "Temporarily appending rep.error(\"ZZZ999\", \"x\", \"x\") inside a check in validate.py makes 'codes: every emitted code is registered' FAIL naming ZZZ999; reverting restores PASS"
    },
    {
      "type": "assertion",
      "text": "Temporarily adding \"QQQ001\": (\"error\", \"a dead entry nothing emits at all\") to CODES makes 'codes: no registered code is dead' FAIL naming QQQ001"
    },
    {
      "type": "assertion",
      "text": "Editing one character in codes.md makes 'codes: references/codes.md is current' FAIL with 'regenerate' in the detail; regenerating restores PASS"
    }
  ],
  "forbidden": [
    "Do not hand-edit references/codes.md - regenerate it.",
    "Do not modify validate.py, batch.py or criteria.py - S1 owns them; if --codes output is wrong, that is a finding on S1.",
    "Do not add a new suite; extend the docs-consistency suite.",
    "Do not weaken or special-case 'SKILL.md mentions every reference file' - add the row instead.",
    "In SKILL.md touch only the reference-table row, the validate.py Scripts bullet and the 'six suites' sentence."
  ],
  "out_of_scope": [
    "Changing what --codes prints (S1)",
    "Any other SKILL.md edit"
  ],
  "rollback": {
    "flag": "",
    "note": "additive; revert the commit"
  },
  "preflight": [
    {
      "type": "command",
      "cmd": "python3 story-refinery/scripts/validate.py --codes >/dev/null; echo $?",
      "expect": "0 - S1 has landed"
    },
    {
      "type": "command",
      "cmd": "grep -n 'no invented validator codes' story-refinery/scripts/selftest.py",
      "expect": "one hit"
    },
    {
      "type": "command",
      "cmd": "grep -n 'SKILL.md mentions every reference file' story-refinery/scripts/selftest.py",
      "expect": "one hit - the check that requires the SKILL.md row"
    },
    {
      "type": "command",
      "cmd": "grep -n 'six suites' story-refinery/SKILL.md",
      "expect": "one hit, line 843"
    }
  ],
  "stop_and_ask": [
    "`--codes --markdown` output differs between two runs - determinism is S1's to fix; do not sort around it here.",
    "The widened regex {2,6} surfaces a code cited in docs that no script emits - that is a real docs bug; report it, do not narrow the regex back."
  ],
  "context_budget_hint": "read_first only; the two scripts and the one suite are the whole surface",
  "provenance": [
    "skills@a837f43"
  ]
}
```
<!-- AGENT-BRIEF v1 END -->


---
