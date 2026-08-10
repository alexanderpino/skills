# Cutting the lanes

A lane is the smallest unit that can be improved and judged on its own.

The decomposition is yours to make, not the user's. You can see the artifact and
you know what a critic can hold in one context window; the user is guessing at
both. Take the goal, look at the artifact, then cut.

## The lane test

> Can a fresh critic look at this one thing, compare it against the bar, and say
> which of two versions is better — without needing the rest of the artifact?

Yes → a lane. No → too big, too entangled, or not independently judgeable.

"Make the game better" fails. "Make this tree compare favourably against this tree
in the reference frame" passes, and can be attacked repeatedly.

## Sizing

**Too big** is the common error. Symptoms: critics return several gaps instead of
one, verdicts get vague, gaps stop being attributable to specific changes, and a
lost round cannot be reverted cleanly because six things moved at once.

**Too small** is rarer but real. Symptoms: rounds pass immediately, the critic
strains to find any gap, wave overhead exceeds the work done. Merge upward.

Retirement itself is governed by the armed stop conditions, computed per
dimension by `gauntlet.py status` — not by feel. Your job here is the converse:
when a lane retires or a dimension is shelved, reallocate its compute to lanes
with gaps left, and when a merged or re-cut lane appears, register it before its
first round. Lane sets are not fixed for the run.

## Cut for the tier you are on

At tier 0 you cut **one** lane — the one whose verdict would tell you most about
whether the whole thing is worth funding. At tier 1, two. Only from tier 2 does
the full cut go live (`cost-model.md`).

This is not a watered-down decomposition. Cutting all six lanes and running one
of them is exactly right: the cut is a hypothesis either way, and the probe is
what tells you whether it was a good one before you pay for all six. Lanes that
have not run yet cost nothing and can be re-cut for free.

A lane's cost is `1 + (critic calls × dimensions)` calls per round. That is the
number to have in mind when deciding whether a seventh lane earns its place.

## Order by risk, not by comfort

Which lane does the probe run? Which lane gets the first serial pass? The same
answer both times: **the one whose failure would invalidate the most.**

A POC that proves the easy part proves nothing — the run finds its structural
problem at tier 2 prices instead of tier 0 prices, after other lanes have built
on top of it. The probe is a *tracer bullet*: one thin shot through the riskiest
part of the whole system — the hardest thing to inspect, the most novel work,
the foundational choice everything else assumes — precisely because that is
where a kill-verdict is cheapest and a pass-verdict is worth the most.

The same ordering governs the serial passes: **structure before cosmetics,
foundations before finish.** A lane whose outcome changes what "good" means for
other lanes (layout before imagery placement; data model before the views on
it; information architecture before paragraph polish) runs first, while the
budget can still respond to what it finds. Polishing a lane that a later
structural pass will invalidate is the most expensive kind of progress theatre.

The test, per lane: *if this lane's verdict came back "structurally wrong",
how much already-done work would it invalidate?* Rank by that number,
descending. Comfort-ordering — easiest first, to see quick wins on the board —
inverts it exactly.

## Breadth-first or depth-first — buy them with different tools

Both, and the method already owns the right instrument for each:

**Breadth is for information. Buy it with critics.** Before committing build
rounds across the full cut (the pilot → campaign escalation is the natural
moment), a **survey** prices the whole landscape: one bar comparison per
never-judged lane/dimension — the artifact *as it stands* against the bar, a
cheap critic or an oracle measurement, **no builders**. Cost: one cheap call per
pair. What it buys: `plan`'s first campaign ranking is measured instead of
assumed, and the biggest real gap — not the biggest guessed one — gets the
first build round. `plan` ranks a never-judged pair above every known major
until someone prices it, because an unknown is a risk, not a zero.

**Depth is for improvement. Buy it with builders.** Once the survey has mapped
the gaps, build depth-first down the risk ranking: serial single-owner passes,
one lane at a time, each driven by its named gap.

**Never buy breadth with builders.** That is fan-out — the shape the canonical
run measured as slower *and* worse (below). The failed pattern and the survey
differ in exactly one word: parallel *building* versus parallel *judging*.
Critics only read; six cheap verdicts in parallel cost less than one build
round and collide with nothing.

## Parallel or serial — serial is the default

Fan-out is the method's most visible feature and its most over-used one. The
canonical run's own write-up is blunt about it: **"Sequential single-owner passes
beat parallel fan-out decisively."** Its numbers, scored out of 10 across rounds,
were `3.59 → 4.14 → 4.05 → 5.05` — three rounds of six parallel agents each
owning one directory produced a net of about half a point *and a regression in
the middle*; the jump came from one sequential pass with a single owner per
coupled concern.

That is a cost finding as much as a quality one. Parallel fan-out over coupled
work costs many times more and scored worse. So:

- **Run serially by default** when lanes touch the same concern, even loosely —
  one owner, one pass, in order. Lighting before materials, information
  architecture before paragraph polish, data layout before the systems that walk
  it.
- **Fan out only for genuinely independent work**: disjoint files, disjoint parts
  of the output, and no lane whose result changes what "good" means for another.
- **When unsure, serialise.** Watch whether the second lane's critic keeps citing
  the first lane's territory — that is the dependency showing itself, and it is
  cheaper to discover in one serial wave than in three parallel ones.

Parallel lanes also raise the burn *rate*, so a fan-out that turns out to be
wrong costs its mistake faster than a serial pass would.

**Serial ownership is not serial time.** Single ownership serialises *writes* —
it does not require the run to idle between stages. While one lane's critics
judge, the next lane's builder can already run: builders write disjoint paths
and critics only read, so nothing about the regression guard or critic
independence is touched. Pipelining stages of independent work is free speed;
fan-out over coupled work is the thing the numbers above show to be slower
*and* worse. Keep the two apart. → `pace.md`

## File ownership

**One file, one owner, per wave.** Not per run — ownership can move between waves,
and often should.

Keep the ledger in `gauntlet/ownership.md`, refreshed at the start of each wave.
When a builder needs a file it does not own, it escalates rather than reaching
across; you either transfer ownership or serialise the lanes. Both are cheap.
A silent cross-lane write is not — it corrupts the champion/challenger revert,
because reverting one lane now undoes another lane's work.

Shared resources that genuinely cannot be split — a central registry, a shared
header, a document's table of contents — get owned by the smoother instead of by
any lane.

## Re-cutting

The decomposition is a hypothesis. Evidence that it is wrong:

- The smoother reports the same seam wave after wave
- Two lanes' critics keep citing each other's territory
- A lane's gaps never shrink no matter how many rounds it runs
- Every round in a lane requires files owned by another lane

Re-cut between waves, never mid-wave. Record the change and why in the workbench —
a re-cut resets the clean-streak counters for the affected lanes, and a reader of
the log needs to know that the counter reset was deliberate.
