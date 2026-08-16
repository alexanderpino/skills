# Setting the bar

The bar is the whole method. Everything else is machinery for repeatedly hitting it.

A usable target bar has four properties:

1. **External** — it exists independently of this run and of the agent's opinion
2. **Inspectable** — a critic can look at it, run it, or measure against it
3. **Unarguable** — the artifact cannot talk its way past it
4. **Reachable** — the distance from the current artifact to it can plausibly be
   closed inside the agreed budget

"Make it amazing", "production-ready", "polished", "best-in-class" fail the first
three. "Match Pixar" on a two-day budget fails the fourth, which is the one runs
usually get wrong.

## Bars by artifact class

**Rendering, graphics, games**
Reference frames from a real shipped product, captured at comparable framing and
resolution. Also: a reference implementation of the same effect, a ground-truth
offline render to compare a realtime approximation against, or a published
numerical reference for a BRDF or transport model. Frame time budgets belong here
too — a visual bar with no perf bar produces beautiful unusable output.

**UI, websites, product design**
Three to five real interfaces widely held to be excellent in the same category,
captured as screenshots at the same viewport. Interaction quality needs recordings
or a running build, not stills. Add measurable constraints — contrast ratios,
tap-target sizes, layout shift — so aesthetics do not swallow accessibility.

**Prose, documentation, writing**
Passages with the property you want, from writers who have it. Not to imitate
voice — the critic asks whether each of our paragraphs is at least as clear, as
dense, as free of throat-clearing. For docs, a framework's own reference docs make
a strong structural bar.

**Systems and engine code**
A test suite, a latency or throughput target, a failure-injection scenario the
code must survive, a reference implementation to diff behaviour against,
or a profile from a comparable production system. For code *quality* specifically,
a well-regarded codebase in the same domain works as a readability comparator.

**Research and analysis**
A published review or report of the standard you want to reach; a set of source
requirements the output must satisfy; a falsification pass where a critic tries to
break each claim against primary sources.

**Design specs and architecture docs**
A conformance standard, an exemplar document from a mature project, or a
reviewer's checklist derived from one. Structural completeness is measurable;
insight is not — bar both separately.

## When the user has no bar

Do not ask them to define "good". Go find a bar and propose it.

Search for the strongest real artifact in the category, or construct a measurement
that plays the same role. Then state, in one sentence, *why* it is the right bar —
that sentence is what the user is actually approving.

If nothing external exists, build one: generate three deliberately different
candidate versions first, have the user pick the best, and use it as the champion
the loop must beat. A self-generated bar is weaker than an external one and you
should say so, but it beats no bar at all.

## Target and stretch

Split ambition from the definition of done. They are different jobs and one bar
cannot do both.

**The target bar** is what retirement is judged against. It is where "good
enough to hand over" actually sits, and it must be reachable from the current
artifact inside the agreed budget. Set `--target-score` to the score it sits at
(default 7): a critic scoring against a target of 7 can tell you that a 6 is one
gap away, which is information. A target of 10 makes every round a failure, no
lane can ever retire, and the log stops discriminating between a near miss and a
disaster — the script warns you if you try.

**The stretch bar** is optional, and it is direction only. Record it in
`contract.md`, name it out loud as a heading rather than a promise, and report
the distance to it at the end. It never arms a stop condition, never blocks a
retirement, and never turns a lane that reached its target into a lane that keeps
spending.

It has one more job, which is why it should be written as a real bar rather than
a mood: **the stretch is what a surplus buys.** When every lane retires with
waves unspent, `status` prints the stretch-dividend offer — re-arm the surplus
with the stretch as the announced target, same guards, judged rounds, or stop
and return it. The user chooses. A stretch written as "make it amazing" prices
that offer at nothing; a stretch written as an inspectable bar makes the
surplus spendable. This is the deliberate version of what the original loop
does by accident when it overshoots: excellence as a budgeted decision, not a
lucky residue of grinding.

```
TARGET   hero reads as professionally art-directed — the three frozen references
         at gauntlet/bar/, score 7/10, reachable in ~2 rounds per lane
STRETCH  indistinguishable from reference 2 at full resolution (direction only)
```

## Where the target sits on the ladder

A gauntlet does not generate a POC, then an MVP, then an MLP. It runs *after* you
have something inspectable, and it moves one artifact up a quality ladder. But
the ladder is still the clearest way to say where a target belongs, so use it —
Kniberg's **earliest testable → usable → lovable** (`authorities.md`):

| Rung | What it means here |
|---|---|
| **Testable** | The artifact exists and a critic can reach it. This is the *precondition* for a gauntlet, not a phase of it. If you are not here yet, wave 1 is the bootstrap wave that gets you here. |
| **Usable / viable** | Where the **target bar** normally sits. Good enough to hand over; retirement is judged against it. |
| **Lovable** | Where a **stretch** normally sits. Direction, reported as distance, never a stop condition. |

Two consequences worth stating at intake:

- **The bootstrap wave builds a thin end-to-end slice, not one perfect part.**
  Kniberg's skateboard: something whole and crude beats one excellent wheel,
  because lanes cannot be judged independently until the whole thing exists to
  judge. A wave 1 that produces a beautiful header and no page has produced
  nothing a critic can compare against a reference page.
- **A gauntlet answers the quality question only.** It cannot tell you whether
  anyone wants the artifact, whether it is buildable at scale, or whether the
  business case holds. If what the user actually needs is a POC to decide
  *whether to build at all*, say so — that is discovery work, and running a
  quality loop against an unvalidated idea polishes something nobody ordered.

## The feasibility check

Ambitious is fine; unfunded is not. After first light you have one real data
point — the first gap and how big it is. Do the arithmetic before wave 1:

> rounds to close the first gap × lanes ÷ WIP limit ≈ waves needed

If that exceeds the budget, fix it now, and say which fix you chose:

- **Cut scope** — drop the lowest-ranked lane rather than starving all of them
- **Lower the target** — move it to where the budget can reach, and move the old
  target into the stretch line
- **Raise the budget** — the user's call, made before the money is spent instead
  of after

A run that starts knowing it cannot reach its target has already decided to
disappoint someone. The only cheap moment to fix that is before wave 1.

## Raising the bar mid-run

If the artifact passes the target with rounds left, the bar was set too low. That
is a good problem: raise it (announced, recorded in `contract.md`), and let the
stretch become the new target if it now looks reachable. Never lower a target
mid-run — that is bar erosion with paperwork.

## Multi-dimensional bars

Most real artifacts need more than one. A game frame has a visual bar and a frame
time bar; a document has a clarity bar and a completeness bar; an API has an
ergonomics bar and a latency bar.

Keep them separate and judge them separately. Collapsing them into one score is
how a loop quietly trades away the dimension nobody is watching — usually
performance, usually late in the run.

Mechanism: declare dimensions in `config.json` at init. Each dimension gets its
own critic comparison and its own `log-round` record (`--dimension`), its own
streaks, and its own retirement. A lane retires only when every one of its
dimensions has — so a decisive visual win cannot retire a lane whose frame time
still loses.

## Freezing

Copy bar artifacts into `gauntlet/bar/` at intake and reference them by path
everywhere after. Bars described from memory drift; bars stored as files do not —
and pointing a subagent at a path is cheaper than pasting the bar into its prompt.
