# Adversarial review

`validate.py` proves the bundle is *well-formed*. Nothing so far proves it is
*right*. A bundle can pass every gate and still send an implementer at the wrong
file, with criteria nobody can test and a wave plan that deadlocks on day one.

The gap is closed by readers who are hostile by assignment and blind by
construction. Reviewers reading a document from an assigned perspective find more
defects than reviewers reading it "carefully" `[P: Basili et al., Perspective-Based
Reading, 1996]`; distinct roles in an inspection is the older form of the same
finding `[P: Fagan, 1976]`. You are the author of this refinement, so you cannot
supply that perspective by trying harder - you already know what you meant.

Run this after Phase 7 validates, and before Phase 9 emits. The cost is one pass;
the thing it prevents is a whole team implementing the wrong plan correctly.

## The panel

Each critic exists to ask one question. Narrow mandates are what stop a panel
collapsing into four voices saying "looks fine" `[L]`.

| id | Who they are | The question they exist to ask |
|---|---|---|
| `implementer` | An engineer or agent with zero context who follows the brief literally | "Where does this send me wrong, and where must I guess?" |
| `tester` | QA, who must turn every criterion into a test that can fail | "Which criterion can I not make binary?" |
| `archaeologist` | A reviewer who trusts nothing and re-opens every citation | "Which claim is not in the file it cites?" |
| `sequencer` | The person who has to schedule this and watch it land | "Which subtask cannot actually start when the plan says it can?" |
| `stakeholder` | Whoever wrote the original ask, who has not seen the refinement | "What was asked for that is missing, and what is here that nobody asked for?" |

Default panel is the first four; `min_critics: 3` is the floor `[L]`. Add
`stakeholder` when the source text is long, when the refinement grew scope, or
when the requester is not in the room. The `archaeologist` is never optional on a
bundle with citations - fabricated evidence is the most damaging failure this
skill has, and it is the only one a downstream reader cannot detect.

On a greenfield story there are no files to open, so the archaeologist's mandate
turns around: it re-opens every *assumption* - the standard or ADR a convention
cites, the reuse search that `ruled_out` claims came back empty, the walking
skeleton that is supposed to go all the way through. Its packet carries
`evidence.greenfield` and `ruled_out` for that reason. The sequencer's packet
carries the complexity card, because a plan whose card says L and whose waves
look like a weekend is a finding.

## Blindness

A critic who can see why you chose something reviews the reasoning instead of the
artefact, and reasoning is persuasive in a way that a wrong file path is not.

```bash
python scripts/review.py brief --bundle bundle.json --out reviews/
```

That writes one sealed packet per critic: their mandate, the finding contract, and
**only the slice of the bundle their mandate covers**. The packet withholds the
conversation, the decision rationales and your self-score - not as etiquette, but
because the script simply never puts them in. Hand each packet to a separate
sub-agent in fresh context and take back findings.

If the session cannot spawn sub-agents, run the critics yourself, one at a time,
re-reading only that critic's packet before speaking as them. That is genuinely
weaker - you cannot unsee your own reasoning - so record `context: "same-session"`
on those critics and say so in the handover. Honest weak evidence beats a fresh
label on a review that was not fresh.

## The finding contract

Every finding carries:

| Field | |
|---|---|
| `id` | `F1`, `F2`, ... |
| `critic` | the critic who raised it; must be one you recorded |
| `severity` | `blocking` \| `major` \| `minor` |
| `locator` | a path into the bundle - `story.acceptance_criteria[1]`, `subtasks[3].agent_brief.done_when[0]`. It must resolve (`REV005`) |
| `claim` | what is wrong, in one sentence |
| `failure` | the concrete thing that goes wrong downstream if it ships as is |
| `status` | `open` \| `fixed` \| `accepted` \| `disputed` |
| `resolution` | what you did about it |

**Severity ladder** `[L]`:

- **blocking** - an implementer would build the wrong thing, or a stated fact is
  false. The bundle is not ready while one is open (`REV002`).
- **major** - real cost, not fatal. Fix now, or accept it with a written
  rationale and a named accepter.
- **minor** - cheap improvement. Fix or drop, but record the decision.

`failure` is the field that separates criticism from noise. Compare:

> **Weak.** "AC2 is unclear." - unactionable; the author reads it as taste.
>
> **Strong.** "AC2 says exports are 'complete'. An implementer will export the
> 1000 rows on the current page and pass; the requester means all 40k rows across
> pagination. Nothing in the bundle distinguishes them, so this ships wrong and
> passes its own test."

The second names who does what and what they get. Insist on it - from a
sub-agent, and from yourself when you are the duck.

## Resolving findings

You may not dismiss a finding silently. Every one ends in a recorded state:

- **fixed** - the bundle changed. Note what changed.
- **accepted** - real, not fixing now. Record the risk you are accepting and who
  accepted it. If nobody but you accepted it, that is an open question, not an
  acceptance.
- **disputed** - the critic was wrong. Write the rebuttal with its evidence
  (`REV003` requires the text).

One rule about rebuttals, and it is the most useful thing in this file: **if your
rebuttal is correct and rests on something not in the bundle, the critic was still
right.** The critic saw exactly what the implementer will see. Put the missing
fact in the bundle and mark the finding `fixed`, not `disputed`.

Fixing changes the content, which invalidates the stamp:

```bash
python scripts/validate.py bundle.json --config refinery.yaml   # re-run the gates
python scripts/review.py digest --bundle bundle.json --stamp    # re-stamp
```

Re-stamp only what you re-reviewed. Stamping to silence `REV007` after rewriting
half the bundle is how a review becomes decoration - if the fixes were
substantial, re-run the critics whose slice you touched.

## Rubber ducking

The solo fallback, and a cheap warm-up before the panel. Explaining a thing aloud
forces the gap into the open, which is why the duck works at all `[P: Hunt &
Thomas, The Pragmatic Programmer, 1999]`. Use it when the session cannot spawn
sub-agents, or when the story is small (`rubber_duck_max_subtasks`, default 3);
above that it is not enough on its own (`REV008`).

Speak as the executor, never as the author. Four passes:

1. **First move.** Read each subtask's `objective` aloud, then say which file you
   would open first and what you would change in it. If you cannot name it from
   the brief alone, the brief is missing a `read_first` entry.
2. **Run the check.** Narrate each `done_when` as if executing it, and say the
   output you expect. If you cannot predict the output, it is not a check, it is
   a wish.
3. **Both halves.** For each criterion, say "this passes when ___ and fails when
   ___". A blank half is a finding.
4. **Why separate.** Say why each subtask is its own subtask. "Different layer"
   under a vertical-slice profile means re-slice. "It was getting big" means you
   split by size instead of by rule.

Record the pass with `method: "rubber-duck"` and its findings. It is lower
assurance by construction - one voice, full context, no blindness - so say that
in the handover rather than letting a duck read as a panel.

## Recording it

```json
"review": {
  "method": "critics",
  "bundle_digest": "sha256:...",
  "critics": [
    {"id": "implementer", "context": "fresh",
     "attempted": "only set when this critic found nothing"}
  ],
  "findings": [
    {"id": "F1", "critic": "tester", "severity": "blocking",
     "locator": "story.acceptance_criteria[1]",
     "claim": "...", "failure": "...", "status": "fixed", "resolution": "..."}
  ]
}
```

```bash
python scripts/review.py brief  --bundle bundle.json --out reviews/   # sealed packets
python scripts/review.py check  --bundle bundle.json                  # summary; exit 1 if one blocks
python scripts/review.py digest --bundle bundle.json --stamp          # after fixes
```

| Code | Fires when |
|---|---|
| `REV001` | no review at all, or a method that is not `critics` \| `rubber-duck` \| `both` |
| `REV002` | a `blocking` finding is still `open` |
| `REV003` | `accepted` or `disputed` with no resolution text (error); `fixed` with no note (warning) |
| `REV004` | a critic found nothing and recorded no `attempted` note |
| `REV005` | a finding's `locator` does not resolve in the bundle |
| `REV006` | fewer critics than `review.min_critics` |
| `REV007` | the review is unstamped, or the bundle changed after it |
| `REV008` | rubber-duck alone on a story past `rubber_duck_max_subtasks` |
| `REV009` | a malformed finding: unknown severity or status, or an unrecorded critic |

`gates.adversarial_review: off` stops the gate from demanding a review at all - a
deliberate choice, made once in config, not a shrug at handover time. A review you
do record is still held to every rule above.

## Smells of the critique itself

**The agreeable panel.** Four critics, zero findings. *Tell:* `REV004`. *Fix:*
they were not blind, or their mandates were too broad to bite. A panel that
returns nothing on a first-pass refinement is reporting on itself, not on the
bundle.

**Critique theatre.** Findings recorded, every one `accepted`, bundle unchanged.
*Tell:* no `fixed` status anywhere and a digest that never moved. *Fix:* accepting
everything is dismissing everything with extra steps.

**Invented severity.** Harshness performed by manufacturing problems. *Tell:* a
`failure` that only restates the `claim`, or a locator pointing at something the
critic was never shown. *Fix:* the contract - locator, and a named downstream
consequence.

**The author defending.** Rebuttals that rest on context only you have. *Tell:*
`disputed` findings whose resolution explains what you meant. *Fix:* see the rule
above - the critic saw what the implementer will see.

**Reviewing the wrong draft.** Findings against a bundle you then rewrote.
*Tell:* `REV007`. *Fix:* re-run the critics whose slice changed; a stamp is not a
substitute for a reading.
