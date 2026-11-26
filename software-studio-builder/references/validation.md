# Validation — the stage that starts when you think you are done

Every run reaches a moment where it believes the work is finished:

- the proposal is written and you are about to ask for approval (the hard stop),
- the studio is generated and you are about to show the handover card,
- or a smaller job — "add this rule", "change that role" — looks complete.

**That belief is the trigger for this stage, not its conclusion.** The feeling of being done
is formed by the same reasoning that did the work, so it shares that work's blind spots.
Validation exists to test the claim "done" before the user is told — against the files on
disk, against explicit acceptance criteria for the stop (`references/acceptance.md`), against
what you are about to tell the user, against what the user actually asked for, and, for a
generated studio, against actual use.

The stage has five steps and never more than three rounds:

1. mechanical checks (`validate.py`)
2. **trial and draft** — trial-run the studio (generated stop); draft the final message
3. **refutation critic** — assumes each change is wrong and tries to prove it
4. **validator** — traces every request item, every acceptance criterion and every claim in
   the final message to evidence
5. re-run `validate.py`, report, mark the state as reported

Steps 3 and 4 are independent of each other: spawn both in one message.

**What each step is told to verify** — and what enforces it:

| Step | Verifies | Enforced by |
|---|---|---|
| 1 | the fixed checks for the stop (tables below) | `validate.py` V01–V25 |
| 2 | that a gate owner, an implementing specialist and a catalog skill behave as their files promise | V26: every `trial.py pick` file has a row; a Fail fails |
| 2 | that the message to the user says nothing the files contradict | V92: counts and "nothing generated" cross-checked; the validator's `M` rows required |
| 3 | that no change since the last report can be shown wrong | V91: every changed path attacked; a Refuted row fails |
| 4 | the request, **every acceptance criterion of the stop** (P1–P10 / G1–G10), the message's claims | V90: a row per criterion id (derived from `acceptance.md`) or NOT ASSESSED |

## Step 1 — Mechanical checks

```bash
python3 <skill>/scripts/validate.py <target>
```

It reads the stopping point from `.ssb/state.json` and runs the checks for it.

**Stop `proposal`** (not approved yet):

| Check | What it proves |
|---|---|
| V01 | intake answers (or the defaults taken for an absent user) are on record |
| V10 | the ledger's chains hold: claim → verbatim quote with locator → tiered source |
| V11 | `research/report.md` exists and cites only claims that exist |
| V12 | `proposal.py check` has no FAIL |
| V13 | `proposal.md` is byte-identical to a fresh render — the user approves what will be built |
| V14 | nothing was generated before approval |
| V15 | the blind critic's findings are on record in `.ssb/critic.md` |
| V16 | open questions are listed |
| V91 | the refutation critic (step 3) attacked every changed path, after the last change, and none was refuted |
| V92 | `final-message.md` (step 2) is current, its counts and "nothing generated" claim match the files, and the validator checked its claims (`M` rows) |
| V90 | the validator's review (step 4) exists, carries a verdict, is newer than what it reviewed, and has a row for every P-criterion |

**Stop `generated`** (approved, files written):

| Check | What it proves |
|---|---|
| V01 | as above |
| V20 | the approval is valid for the current proposal |
| V21 | the files were generated from that same proposal (manifest hash) |
| V22 | all nine layers were generated |
| V23 | `check_template.py` (13 checks, including the reporting hierarchy and agent-readability) |
| V24 | the studio's own `studio-tests` pass |
| V25 | no generated file has drifted from what the approved proposal renders |
| V26 | the trial (step 2) covers every file `trial.py pick` chose, is current, and no row is Fail |
| V91, V92 | as above |
| V90 | as above, with a row for every G-criterion |

What C01–C13 inside V23 prove is in `references/verification.md` (the checker reference).

A **FAIL** sends you back to the phase that owns it (research, proposal or generation) —
fix it there, never by editing around the check. Re-run `validate.py` after each fix.

## Step 2 — Trial and draft

**Trial run (generated stop only).** Every other check reads files; this one uses them.

```bash
python3 <skill>/scripts/trial.py pick <target>    # what will be tried (deterministic)
python3 <skill>/scripts/trial.py brief <target>   # a ready brief per pick, with the expected behaviour
```

It picks the owner of the first gate (does it answer a gate run with the verdict token on
line one, using only that gate's words?), the first implementing specialist (does it follow
`### When You Are Spawned` — say NOT ASSESSED for a missing input, return in the promised
order?), and the first catalog skill (does it resolve the config first and ask "May I write"
before writing?). Spawn the briefs as subagents in one message; each works in a scratch copy
of the studio, never in the target. Record `.ssb/trial.md`:

   independent: yes
   | # | File | Brief | Expected | Observed | Result |
   |---|---|---|---|---|---|
   | T1 | `.claude/agents/compliance-lead.md` | gate CL-RULE-COMPLIANCE on a stub | verdict token line 1 | `CL-RULE-COMPLIANCE: CONCERNS`, gap found | Pass |
   Result is exactly one of: Pass · Fail · Could not test

A Fail goes back to the proposal (the text that rendered the file) or the skeleton. Without
an Agent tool, run each brief yourself as a separate pass and write `independent: no`.

**Draft the final message (every stop).** Write the message you intend to send — the summary
at the proposal stop, the handover card at the generated stop — to `.ssb/final-message.md`,
with the verdict line left as `VALIDATE <stop>: <pending>`. `validate.py` (V92)
cross-checks its numbers ("12 agents", "10 skills") and any "nothing was generated" against
the files, and the validator checks every other factual claim in it. What you finally send
is this draft with only the verdict line filled in.

## Step 3 — Refutation critic: try to prove the changes wrong

The validator (step 4) asks *"is everything the user asked for there?"* The critic asks the
opposite question: *"is anything that is there wrong?"* Its job is to **refute the
changes** — to treat each one as a claim and look for the evidence that breaks it.

Its target is exactly the change set:

```bash
python3 <skill>/scripts/validate.py <target> --changes
```

That lists every path added, modified or removed since the last stop you reported (since the
start of the run, the first time). Spawn one critic subagent with that list, read access to
the target, and the brief below — **not** your reasoning, your plan or your summary. A critic
that knows why you made a change will find reasons it is right.

```
You are a refutation critic. Someone made the changes listed below and believes they are
correct. Your job is to prove them wrong. You did not make them; assume nothing in them is
true until you have tried to break it.

Changes (from validate.py --changes): <the list>
Acceptance criteria for this stop: <skill>/references/acceptance.md (P… or G… table)
Target: <path>   Research ledger: <path>/.ssb/research/   (read-only for you)

For every changed path — or a folder of related paths at least two levels deep, e.g.
`.claude/agents/` — do this:
1. State what the change claims or does: a fact, a rule, a reporting line, a behaviour.
2. Decide what evidence would refute it, then go and look for that evidence. Prefer doing
   over reading: run the script, run the checker, construct the counter-example, open the
   cited source and check the quote, follow the reporting line to its end, try the edge case.
   Typical attacks: a claim whose cited source does not say it; a legal statement without a
   primary source; an agent-facing file (agent, skill, rule, gate, template, CLAUDE.md) that an
   agent arriving cold could not act on — read it as that agent would, with nothing but the
   file and its brief, against `references/writing-for-agents.md`; a role that reports sideways or owns nothing; a rule that contradicts
   another rule; a gate nobody can pass; a generated file that differs from the proposal; a
   change that breaks something that worked before (re-run what the change could affect).
3. Record the attempt — even when it fails to refute. "Looked, fine" is not an attempt; name
   what you tried.

Write <target>/.ssb/refutation.md:

   independent: yes
   # Refutation — <date>
   | # | Change | What it claims | How I tried to refute it | Result | Evidence |
   |---|---|---|---|---|---|
   | 1 | `.ssb/proposal.json` | qa-lead owns UAT sign-off | checked gate owner + roster | Not refuted | gate QL-UAT-SIGNOFF owner qa-lead |
   Result is exactly one of: Refuted · Not refuted · Could not test
   Name every changed path, or its folder, in backticks in the Change column.
   ## Verdict
   REFUTATION: REFUTED | CONCERNS | SURVIVED | NOT ASSESSED

   REFUTED if any row is Refuted; NOT ASSESSED if you could not attack some change at all;
   CONCERNS if any row is Could not test or you found something weak but not wrong;
   SURVIVED only when every change withstood a named attempt.

Return the verdict line and every Refuted / Could not test row, at most 150 words.
```

`validate.py` enforces the critic's discipline mechanically (V91):

- a row marked **Refuted** fails the stage, whatever the verdict line says;
- a changed path the critic never named (in backticks, at least two folder levels deep) is
  **not assessed** — a change nobody tried to refute has not survived anything;
- **Could not test** rows, and a critique without a subagent (`independent: no`), cap the
  result at CONCERNS;
- a refutation older than the newest change is stale.

A refuted change is fixed in the phase that owns it, and the next round's critic attacks the
fix too — it is a change.

## Step 4 — Independent review against the request, the criteria and the message

Spawn one validator subagent. Give it **only**:

1. The user's request, **verbatim** — every message in which they asked for something or
   changed what they asked for, quoted, not summarised.
2. The paths of the deliverable (`proposal.md` and `research/report.md` at the proposal
   stop; the studio folder and `.ssb/trial.md` at the generated stop), `.ssb/final-message.md`,
   and the output of `validate.py`.
3. `references/acceptance.md` — the table for this stop.
4. The brief below.

Do not give it your reasoning, your plan, or your summary of the work — it would inherit the
blind spots it is there to find.

```
You are validating a deliverable against the user's request. You did not produce it.

The request (verbatim): <quoted messages>
The deliverable: <paths>
The message the user will receive: <target>/.ssb/final-message.md
Acceptance criteria for this stop: <skill>/references/acceptance.md — the P… or G… table
Mechanical checks: <validate.py output>

1. Split the request into every distinct thing the user asked for, including constraints
   ("keep research small", "EU customers", "stop where you need my approval") and the
   implied ones a competent professional would assume (the studio must be usable; legal
   statements must be sourced; agent-facing files must be written for the agents that read
   them — see <skill>/references/writing-for-agents.md).
2. For each item, find the evidence in the files — open them; do not trust summaries.
   Mark it Met, Partly met, Not met or Not assessed (you could not check it), with the
   file and line or section as evidence.
3. Check every acceptance criterion of this stop the same way: one row per id (P1, P2, … or
   G1, G2, …), using its "How to check" column. Do not skip one; write Not assessed if you
   could not check it.
4. Check every factual claim in final-message.md — counts, verdicts, what was or was not
   generated, what is deferred — against the files: one row per claim, ids M1, M2, …
5. Look for anything else the deliverable claims that the files do not support.
6. Write the result to <target>/.ssb/validation.md:

   independent: yes
   # Validation — <stop> — <date>
   | # | Requested | Evidence | Status |
   |---|---|---|---|
   | 1 | ... | <file:section> | Met |
   | P1 | proposal.py check has no FAIL … | <output line> | Met |
   | M1 | "13 roles in scope" | proposal.json: 13 roles, 1 deferred | Met |
   ## Unsupported claims
   ## Verdict
   VALIDATION: PASS | CONCERNS | FAIL | NOT ASSESSED

   FAIL if any item is Not met; NOT ASSESSED if any could not be checked; CONCERNS if any
   is Partly met or a claim is unsupported; PASS only when every item is Met.

Return the verdict line and the Not met / Not assessed items, at most 150 words.
```

**No subagent available?** Do the review yourself, as a separate pass: re-read every file
from disk (not from memory), quote the user's request at the top, fill the same table, and
write `independent: no` as the first line. `validate.py` then caps the review at CONCERNS
and says so — a self-review is better than none, but it is not independent, and the user
should know.

## Step 5 — Re-run, report, mark

```bash
python3 <skill>/scripts/validate.py <target>
```

Now V26 reads the trial, V91 the refutation, V92 the message and V90 the review. Then, and
only then, send `final-message.md` — with its verdict line filled in from this run, and every
FAIL, NOT ASSESSED and CONCERNS item named. A message that says or implies "done" without
that line has skipped this stage.

Right after that message:

```bash
python3 <skill>/scripts/validate.py <target> --mark-reported
```

It records what the user was shown as the baseline, so the next round's critic attacks only
what changes after it. It refuses when no validation has run.

## Rounds

- Round 1: validate → fix → validate. Round 2 and 3 the same.
- After three rounds with a FAIL still standing, **stop**: report the remaining failures
  to the user as they are, with what you tried. Do not loop, and do not soften the verdict.
- A verdict is never edited by hand. `validation.json` and `validation.md` are records of
  what was checked, not text to tune.

## After a change

Any change after validation — an edit to the proposal, a regenerated layer — makes the
review stale; `validate.py` detects that by file times and reports V90 as NOT ASSESSED until
the review is run again.
