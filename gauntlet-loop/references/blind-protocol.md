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

## Champion versus challenger

The promotion comparison — this round's output against the current champion — is
the *most* blindable comparison in the whole method: both sides are ours, so no
branding, style, or provenance separates them. Run it under the same protocol:
randomised labels, normalised presentation, no history.

It is also the comparison to fall back on when no external artifact can be
compared at all (a bar that is purely numerical, or a category with no usable
reference): a run judged only champion-vs-challenger still catches regressions
and still climbs, it just loses the external ceiling. Log it as `--mode champion`;
it feeds promotion decisions, never bar-met or clean-streak counters.

## When blinding is impossible

Some comparisons cannot be blinded. Recognisable IP, a bar that is a numerical
target rather than an artifact, a running application with obvious branding, a
document in an unmistakable house style.

**First check whether it needs a model at all.** A bar that is a numerical target
is not a weak blind comparison — it is a *measurement*. Take the number and log
`--mode oracle`; that is cheaper than rubric mode and stronger evidence than
either model mode, because nothing was judged. Rubric mode is for comparisons a
model must make but cannot make blind, not for numbers.

For the rest, do not fake the blind. Switch to **rubric-against-reference**:

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
