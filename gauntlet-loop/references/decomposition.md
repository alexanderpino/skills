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

Retirement and parking are governed by the armed stop conditions, computed per
dimension by `gauntlet.py status` — not by feel. Your job here is the converse:
when a lane retires or parks, its slot goes to the next lane on the ranked list,
and a merged or re-cut lane is registered before its first round. The lane set is
frozen in size, not in shape: it can be merged, split, re-ranked or replaced
between waves, and it never *grows* (see "The scope is frozen" below).

## Ranking, and the WIP limit

A wave funds `wip_limit` lanes (default 3), not every lane you cut. So the cut is
only half the decision — the order is the other half.

Rank by, roughly:

> (value to the goal) × (how closeable the gap looks at lane level) ÷ (cost per round)

- **Value**: how much of the goal's quality this lane actually carries. The hero
  image usually outranks the footer.
- **Closeability**: a gap a builder can reach with the files this lane owns. A
  gap that needs a new source asset or an architecture change is not closeable
  here, whatever its value — flag it for the user instead of funding rounds
  against it.
- **Cost**: an expensive lane needs to be worth its rounds. Cheap lanes are worth
  running early because they retire fast and free their slot.

`status` prints the funded set and the queue behind it each wave: dimensions
still moving first, unread ones next, stalled ones last. Follow it unless you
have a reason you can state.

**Depth beats breadth.** Three rounds on one lane close a gap; one round on three
lanes gives you three half-closed gaps and a budget that is a third gone. The WIP
limit exists to stop the second pattern, which is the default temptation once
several lanes are open at once.

## Parking a lane

The counterpart to retirement: a lane that stopped moving stops getting funded.
The conditions and the command are in `stop-conditions.md` (`no-progress`); what
belongs here is the decomposition consequence.

A park usually says one of three things about the cut:

- **The gap is structural** — it sits below the lane, in a foundational choice.
  Re-cut to include that element, or accept it as an open gap and report it.
- **The gap is not a code problem** — a source asset, a licence, a data quality
  issue. Report it; more rounds cannot reach it.
- **The lane is cut wrong** — its critic keeps citing another lane's territory,
  so nothing inside its own files moves the verdict. Merge or re-cut.

Say which one it was when you park. That sentence is what makes the report
actionable, and it is what tells the next run how to cut better.

## Parallel or serial

Run lanes in parallel when they touch disjoint files and disjoint parts of the
output. Run them serially when one lane's result changes what "good" means for
another — lighting before materials, information architecture before paragraph
polish, data layout before the systems that walk it.

When unsure, serialise the pair for one wave and watch whether the second lane's
critic keeps citing the first lane's territory. That is the dependency showing
itself.

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
- More than one lane parks for the same underlying reason

Re-cut between waves, never mid-wave. Re-run `init --force` with the new lane set
(parks and extensions are carried across as run history) and note the change in
`contract.md` — a re-cut resets the streak counters for the affected lanes, and a
reader of the log needs to know that the reset was deliberate.

A re-cut is also the honest answer when a park was really a cutting mistake: park
the old lane, cut a new one that contains the structural element, and let the log
show both. Quietly re-running the same lane under a new name is not a re-cut.

## The scope is frozen — a re-cut redistributes, it never expands

The lane set is agreed in the contract. Between waves it can be **merged, split,
re-ranked, or replaced**; what it cannot do is grow because the run noticed more
work. This is the rule that stops a gauntlet becoming an unbounded improvement
project:

- **New lanes need a freed slot.** A lane enters the funded set when a retirement
  or a park makes room, or when a re-cut replaces an existing one. Never by
  addition.
- **Noticed work goes to `gauntlet/backlog.md`**, one line, and into the report's
  "noticed, deliberately not funded" section. Builders and critics put it there;
  nobody funds it this run.
- **Genuinely new scope is a new contract.** If the artifact turns out to need a
  whole area nobody cut a lane for, that is a conversation with the user and
  probably a new run — not a quiet ninth lane.
- **Raising the bar mid-run does not raise the budget.** It is allowed and
  announced, but the waves it needs come from the agreed budget or from an
  extension the user grants.

Reverse the test to catch it early: if the projected call count is higher at wave
5 than the projection you gave at intake, and no extension was granted, scope
grew while nobody was looking.
