# The blind protocol

Blinding exists because knowing which side is "ours" changes the verdict. An agent
told it is grading its own team's work grades gently; an agent told it is grading a
famous reference grades reverently. Remove the label and you get judgement.

## Running an honest blind comparison

1. **Randomise the labels.** Our output is A or B by coin flip, per comparison, not
   per lane. A critic that notices ours is always B has learned the answer.
2. **Strip provenance.** Filenames, watermarks, directory structure, metadata,
   code comments naming the author, HUD text, debug overlays. Anything that
   identifies a side is a leak.
3. **Normalise presentation.** Same resolution, crop, framing, format, length. A
   difference in how the two are *presented* becomes a difference in how they are
   *judged*.
4. **Withhold history.** No changelog, no builder rationale, no "we recently
   improved X". The critic starts cold every round.
5. **Force a choice.** No ties. A tie is a refusal to judge dressed as fairness.
6. **Ask for the margin.** Decisive / clear / thin. Margins narrowing across rounds
   is the single best signal that the loop is approaching its ceiling.

## Verifying the blind held

Ask the critic, after the verdict, whether it believes it could tell which was
ours. A critic that guessed correctly *and* explains how it knew has just told you
where your leak is. Fix the leak, and treat that round's verdict as low confidence.

Common leaks: consistent file naming, one side always rendered at a different
resolution, our side having debug UI, the reference having compression artifacts
the critic recognises, one side being conspicuously shorter.

### The artifact can carry the history, and the two rules above do not meet

Rule 2 strips **provenance** — which side is ours. Rule 4 withholds **history** —
the builder's changelog and rationale. Both are about what you *hand* the critic.
Neither notices that the history can be **inside the thing being judged**, and
when it is, stripping provenance does not help: the leak is not "this is ours",
it is "here is the builder's own account of what is wrong with it".

Observed, and it is not a corner case. On a rendering run every evidence frame
carried a caption burned into the pixels — the wave number, what the builder held
open, and why each choice was made. Three critics in separate contexts, judging
three different lanes, each flagged it unprompted and each quoted the same kind of
line back: *"THE FOAM IS A PLACEHOLDER"*, *"STILL OPEN in this frame"*, *"WAVE 7
MEASURED 0.0% AND GAVE A REASON THAT IS NOW WRONG"*. All three reported grading
pixels only. That is three critics' discipline substituting for a protocol, which
is exactly the trade the blind exists to remove.

Captioning a figure is good practice everywhere else in a run — a diagnostic
without its provenance mark is worse than useless. So the rule is not "stop
captioning". It is:

- **Render the caption to a sidecar** (`frame.png` + `frame.caption.md`) and hand
  the critic the image alone. The caption keeps its audience; the critic keeps its
  independence.
- **A frame with text baked in is not a candidate for the artifact itself.** One
  critic had to crop before it could judge a hero frame at all. If the run's bar
  is "would a viewer wonder whether this is a photograph", a caption in the corner
  answers that question before the viewer reaches the image.

The general form, worth carrying past this instance: **ask what the critic must
open in order to judge, and assume everything inside it has been read.** A blind
that depends on a critic choosing not to look at something it is holding is not a
blind.

## Champion versus challenger

The promotion comparison — this round's output against the current champion — is
the *most* blindable comparison in the whole method: both sides are ours, so no
branding, style, or provenance separates them. **It runs blind by default, even
in runs whose bar comparison cannot be blinded.** The mechanics cost one copy:

```bash
d=$(mktemp -d) && flip=$((RANDOM % 2))
git show <champion-ref>:path/to/artifact > "$d/$([ $flip -eq 0 ] && echo A || echo B)"
cp path/to/artifact "$d/$([ $flip -eq 0 ] && echo B || echo A)"
# critic sees only $d — no repo, no history, no mtimes; you hold the flip
```

You hold the label mapping, log the verdict as `ours`/`other`, and add `--blind`
to the champion record so `status` can report the share honestly. A run whose
promotions all ran unblinded gets a nudge from `status` — that was this skill's
own first failure: its reference run logged six bar rounds and zero blind
anything, which made "blind where blindable" aspirational. The rest of the
protocol is unchanged: randomised labels, normalised presentation, no history.

By default it happens in the same critic call as the bar comparison — one
inspection, two verdict blocks, two log records (`critic.md`). Blinding survives
that perfectly well: the labels are randomised per comparison, and the critic
never learns which side is ours in either. Split into two calls only when the
round could retire a dimension, when the two verdicts point opposite ways, or
when a wrong promotion is expensive to undo.

It is also the comparison to fall back on when no external artifact can be
compared at all (a bar that is purely numerical, or a category with no usable
reference): a run judged only champion-vs-challenger still catches regressions
and still climbs, it just loses the external ceiling. Log it as `--mode champion`;
it feeds promotion decisions, never bar-met or clean-streak counters.

## When the bar is a number

A dimension whose bar is a measurement does not need a critic at all. Run the
command, compare the number to the target, and log the result with the
measurement as evidence:

```bash
python3 scripts/gauntlet.py log-round --wave 3 --lane imagery --dimension perf \
  --round 5 --mode rubric --winner other --margin clear --score 6 \
  --severity minor --gap "LCP 1.9s against a 1.5s budget" \
  --closed-when "LCP under 1.5s on the same Lighthouse profile" \
  --evidence gauntlet/bench/w3r5.json
```

Machine gates are the cheapest rounds in the method and the only ones immune to
sycophancy. Use one wherever the dimension allows it, and save the critic calls
for the dimensions that genuinely need judgement.

## When blinding is impossible

Some comparisons cannot be blinded. Recognisable IP, a bar that is a numerical
target rather than an artifact, a running application with obvious branding, a
document in an unmistakable house style.

Do not fake it. Switch to **rubric-against-reference**:

- The critic is told which is which, and instead of picking a winner it scores our
  output against explicitly enumerated properties of the reference
- Properties are drawn from the frozen bar files, not invented per round
- The output must be *better on a named property*, not merely acceptable
- Deference risk is higher here, so the critic's mandate is sharper: assume ours is
  worse and find where

Record the mode via `gauntlet.py log-round --mode rubric`. Blind and rubric
verdicts are not interchangeable evidence — `status` reports the rubric share per
dimension, and a clean-streak built from rubric rounds is weaker than one built
from blind rounds; say so in the report.

## Critic rotation

Over a long run, a builder can start writing to a particular critic's habits rather
than to the bar — passing rounds while the artifact stops improving.

Counter it by varying the critic framing between waves: sometimes a domain
specialist, sometimes a first-time user, sometimes a hostile reviewer looking for
reasons to reject. Same bar, different attack angle. If verdicts flip sharply
depending on framing, the artifact is fragile in a way a single critic was hiding.
