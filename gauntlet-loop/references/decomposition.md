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

### The order the loop enforces is not the order the artifact needs

Two different orderings run through a gauntlet, and only one of them is
mechanical:

- **Quality altitude — enforced.** Usable everywhere before lovable anywhere:
  `status` ranks dimensions below their usable line ahead of any dimension
  buying a rung above it, and `plan` stages it. This is what stops a run
  polishing shaders while gameplay sits at 2.
- **Technical dependency — not enforced, and the loop cannot infer it.** A
  graphics abstraction layer before renderer features; a fixed-timestep loop
  before netcode; a schema before the systems that walk it. The loop knows what
  is *behind* (evidence, trends, budget); it does not know what is *underneath*.
  It has no domain knowledge and will not acquire any by iterating.

Where the second ordering has to come from, most reliable first:

1. **Upstream planning.** The map and answer key settle the architecture
   decisions before wave 1 (`bar-selection.md`); the lane cut then inherits the
   order as serialised pairs. This is the cheapest place to get it right.
2. **A domain skill.** Where one exists for the artifact's field, consult it
   while cutting — it holds the layering this skill deliberately does not — and
   name it in the contract's Notes so every wave's agents load it.
3. **Grounding.** The layering of a long-solved domain is a settled question,
   not an invention (`grounding.md`). A renderer's architecture is not something
   to reconstruct from memory in the middle of a wave.
4. **Reactively, at full price.** Absent all three, the loop still finds out: a
   lane whose critic keeps naming a gap that "sits below the lane" is the
   missing foundation announcing itself, and the answer is a re-cut, not another
   round. It works — and it costs the rounds a plan would have saved.

The bootstrap wave forces a minimum of this on its own: you cannot screenshot a
frame without something that draws one, so a thin end-to-end slice drags the
load-bearing path into existence early. But a walking skeleton is not an
architecture. It proves the path exists; it says nothing about whether the layer
beneath it is the right one.

### The minimum architecture, before wave 1

So on a layered artifact, something *does* have to be written before the loop
runs — and the discipline is in how little.

**The test for what belongs in it: a decision no lane-level round could reach.**
Those are exactly the structural gaps the run would otherwise discover at wave 6
and answer with a re-cut. Buy them at wave 0, where they cost a paragraph.
Everything else — anything a builder can change inside its own files, judged by
a critic against the bar — stays out, because deciding it early is guessing with
extra confidence.

For a renderer that is a short list: where the abstraction boundary sits, what
owns the frame, how resources are addressed, what the update order is. It is not
a design document, and a full one at this point is the planning-fallacy version
of the same mistake — precise about what nobody has learned yet.

Three things make it worth the paragraph:

- **It decides the cut.** Lanes follow layers; a lane that straddles a boundary
  produces critics that keep citing each other's territory, which is the re-cut
  signal arriving the expensive way.
- **It becomes constraints, not suggestions.** Frozen in the contract's rules,
  it reaches every builder by path, like the bar.
- **Harvest it into gates.** This is the move that pays: layering is unusually
  machine-checkable — dependency direction, forbidden imports, where a file may
  live, what a module may reach. An architecture written as prose is advisory
  and drifts; the same architecture expressed as gates is enforced free every
  wave, and the run cannot violate it without the check going red
  (`cost-discipline.md`).

Where it comes from is the same list as the ordering above: the wayfinder map
and answer key, an architecture skill, a domain skill for the field, or
grounding for a solved domain. What it must never be is a builder's improvised
choice at wave 3, defended afterwards because the code already assumes it.

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

Re-cut between waves, never mid-wave. Re-run `init --force` with the new lane
set — the budget, stops, WIP limit, gates, parks and extensions all carry
across, so a re-cut can never quietly change the agreement — and note the
change in `contract.md`. Streaks follow the lane *name*: a lane that keeps its
name keeps its counters, so **rename any lane whose scope materially changed**
and the new name starts fresh. Keeping the old name on a new scope inherits a
streak the new scope never earned.

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
