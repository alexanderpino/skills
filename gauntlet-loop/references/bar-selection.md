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

## No bar, no run — and never a bar you invented mid-loop

The loop's entire output is "A or B is better". If B is a standard the agent
made up while building A, the comparison measures nothing: the builder is
grading itself with extra steps, and every round confirms a taste it already
held. **A run does not start without comparison material that exists outside
this run.** That is not a preference; it is what separates a gauntlet from an
elaborate self-review.

So when there is nothing to compare against, do not improvise one. **Say what
you need and stop** — `gauntlet.py bar-request` writes
`gauntlet/bar-request.md`: per dimension, what comparator would settle it,
which of the four properties it must satisfy, acceptable formats, and where
the files go. Hand that to the user, or to a scout agent whose only job is to
fetch it. Requesting the bar costs one message; discovering at wave 6 that the
bar was self-authored costs the run.

### When the artifact is genuinely new: a spec and an answer key

Some artifacts have no comparator because nothing like them exists — an
internal tool, a bespoke workflow. That is not permission to invent a
standard; it is a different *source* for one. Resolve the open questions into
research-backed decisions **before wave 1**, and write the result as a spec
plus an **answer key**: concrete, checkable statements the artifact must
satisfy, authored outside the loop and frozen into `gauntlet/bar/` like any
other bar. The answer key plays the part the reference product plays
elsewhere. Matt Pocock's `wayfinder` skill exists to produce exactly this —
it turns each undecided question into research rather than a default
(`https://github.com/mattpocock/skills`).

**The shape matters: one map and one answer key, not a ticket each.** Stock
wayfinder writes a ticket file per decision — fourteen decisions, fourteen
files. As a plan that is workable; as a *bar* it is fourteen mini-standards
nobody can hand a critic in one path, each one a separate cold read every
round pays for, and each one a separate surface for drift. The AI Labs
community runs wayfinder with one modification — literally the prompt
`change wayfinder: one map and one answer key, not a ticket each` — and that
is the shape this skill requires of the route: the **map** (the resolved
decisions and why — intake material, it feeds the contract and the plan) and
the **answer key** (the checkable statements — bar material, frozen at
`gauntlet/bar/answer-key.md`). Their proof run: a real HR system, built in
1h33 with every answer-key check passing. And its honest footnote — "the
design only came out okay" — is the second rule below, observed in the wild.

### Running the combination: wayfinder decides, the gauntlet builds

The two loops meet at a clean seam — one resolves decisions, the other closes
gaps — and the handoff is mechanical once the map is done:

| Wayfinder produces | The gauntlet consumes it as |
|---|---|
| Destination | GOAL in the contract |
| Notes (domain, standing preferences) | the contract's rules and constraints |
| Decisions so far (the resolved map) | intake context; what the lanes are cut around |
| **The answer key** | the bar — frozen at `gauntlet/bar/answer-key.md` |
| Not yet specified (the fog) | **must be empty first** — open fog is an unsettled bar |
| Out of scope | the contract's scope line and `backlog.md` |

### Handed stock wayfinder output? Collapse it, do not demand a re-run

The modification above is how to *run* wayfinder for this purpose. It is not a
precondition: plenty of maps were charted before anyone thought about a
gauntlet, and stock wayfinder writes a ticket per decision. That output is
perfectly usable — it is simply not a bar yet, because a bar is one frozen file
a critic opens, not a folder it must assemble.

Collapsing it is a **sort, not a rewrite**, and it is cheap: the judgement was
already spent in the tickets. Every *resolved* ticket lands in exactly one
destination:

| The resolution is… | It belongs in |
|---|---|
| a checkable statement about the artifact | `gauntlet/bar/answer-key.md` — cite the ticket it came from, so the collapse is auditable |
| a constraint or layering decision | the contract's rules — it binds builders; critics do not score against it (`decomposition.md`) |
| work ruled beyond the destination | `backlog.md`, and from there the report |
| still open | nothing yet: fog is an unsettled bar |

That last row is the one to be strict about. An open ticket at wave 1 does not
stay open — it quietly becomes whatever the first builder who trips over it
assumed. Resolve it, or rule it out of scope and say so. The same applies when
the map lives on an issue tracker rather than in a folder: collapse the closed
children, and treat the open ones as the fog they are.

What never happens: pointing critics at the ticket folder to "use it as the
bar". Fourteen mini-bars is fourteen cold reads per round, fourteen surfaces
for drift, and no single artifact anyone can freeze.

**The `.wayfinder/` folder convention.** Run locally, wayfinder leaves its
output as files in a `.wayfinder/` directory in the repo — that is where the
map and answer key land, and the AI Labs prompt extension points the critic
at exactly those files. This skill consumes them by **freezing a copy**:
`.wayfinder/` is a living planning surface, and the bar must not move while
the run judges against it — so the answer key is copied to
`gauntlet/bar/answer-key.md` at intake (note the source and date in
`contract.md`), never referenced in place. If planning later changes the map
materially, that is an announced bar-raise or re-cut conversation, not a bar
that drifted because its source kept evolving. `bar-request` detects the
folder and says so.

Two operational rules make the seam pay:

- **The answer key is a gate farm.** Every mechanically checkable item in it
  ("every list endpoint pages with an opaque cursor") becomes a gate in
  `config.json` at init — checked free every wave from day one, instead of
  costing a critic. The judgement-only items are what the critics keep.
- **A decision surfacing mid-run is escaped fog, and it goes back to the
  map.** When a builder or critic hits a question whose answer is a *choice*
  ("should sessions expire?"), that is not a gap to close — it is a decision
  nobody made. It goes back to the wayfinder map as a new ticket (or to the
  user, if no map exists), and the lane waits or parks. A builder resolving
  it ad hoc is the self-invented bar returning one fragment at a time.

Two rules keep an answer key honest:

- **It is authored before the loop and frozen.** An answer key the builder
  extends mid-run is a self-invented standard wearing a checklist.
- **It bars what it can check, and says what it cannot.** Answer keys are
  strong on function ("every list endpoint pages with an opaque cursor") and
  weak on taste. A run reported as fully passing its answer key while the
  design "came out okay" is the predictable result. So: answer key for the
  functional dimensions, external reference artifacts for the aesthetic ones,
  declared as separate dimensions with their own targets. Do not let a passing
  answer key stand in for a visual bar nobody set.

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
a mood: **the stretch is what the user may buy with a surplus.** When every lane
retires with waves unspent, the surplus is the run's deliverable — the same
result, cheaper — and it returns to the user by default; `status` says so. The
offer of a stretch block (the stretch re-armed as an announced target, same
guards, judged rounds) is one line in the report, priced in the returned waves.
A stretch written as "make it amazing" prices that offer at nothing; a stretch
written as an inspectable bar makes it a real purchase. Never spend the surplus
unasked — that converts the savings the run exists to produce into gold
plating.

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

The rungs have prices, and the user should see them before picking one:
`quote` prints what 7, 8 and 9 cost from the current score — each point above
usable costing roughly double the one before — and that 10 is not a rung at
all (`cost-discipline.md`). Ambition is welcome; unpriced ambition is how a
budget disappoints someone.

The ladder is also the **build order**, and the script enforces it: the
next-wave ranking funds dimensions below their usable line before any
dimension buys a rung above it, and `plan` renders the stages — bootstrap
until everything is judged, everything to usable, then the ambitious rungs,
then stretch on a grant. The skateboard rule at run level: a whole artifact
at 6 beats one dimension at 9 next to one at 2, because critics, smoothers
and users all judge the whole.

Each rung the menu offers carries an **anchor**: one agreed sentence of what
n/10 concretely is for this artifact (`intake.md`), recorded in `contract.md`
and copied into the plan. Anchors exist for choosing rungs; judging stays
with the frozen bar — an anchor handed to a critic is a rubric a builder can
learn to game.

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

## When the target is impossible — say so, with the number

Some targets fail the reachability property against physics, not against the
budget: a 2× speedup asked of an inner loop the profile already shows at the
memory-bandwidth floor, lossless compression below the measured entropy, a
latency target under one network round-trip. No wave count reaches those.
Taking the contract anyway converts an honest "no" at minute five into a
budget stop at wave 8 that breaks the same news for more money — and quietly
lowering the target instead delivers something the user did not ask for under
the name of what they did.

The refusal has to earn itself, in both directions:

- **Substantiate it.** "That is impossible" carries weight only with the
  measurement or the floor argument attached — the profile, the bandwidth
  arithmetic, the bound it hits. First light is where this evidence comes
  from: measure before arguing. An unsubstantiated "impossible" is the same
  failure as an unsubstantiated "amazing", pointed the other way.
- **Bound it.** Almost nothing is impossible outright; it is impossible
  *under stated constraints*. Say which: within this algorithm, this data
  layout, this hardware, this scope. The bounds tell the user which door is
  still open — and whether opening it is a re-cut, a new contract, or not
  worth it at all.
- **Offer the reachable target.** State the nearest target the measurement
  does support, and price it. "2× is not reachable inside this loop — it is
  bandwidth-bound at 94% of peak; 1.3× is, from the two measured stalls" is a
  contract. "Sorry, impossible" is a door closed on someone who still has a
  problem.

Then the user chooses: the reachable target, the structural change, or no run
at all. What is never on offer is accepting the impossible target and letting
the budget stop deliver the verdict later.

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

**Targets split the same way the bars do.** `--dimension-targets
"gameplay=8,graphics=6"` gives each dimension its own rung, and the script
judges each dimension's bar-met against its own number. This is the honest
answer to the blanket "10/10 like <AAA title>" request: decomposed with the
user, the 10 splits into rungs that are buyable (rules, systems, flows) and
rungs that iteration cannot reach against a production team's years of craft
(animation, shaders) — ask what n/10 each dimension must be, price the first
kind (`quote`), refuse the second with the measurement, and put the 10 in the
stretch line. Averaging the wish into one number prices nothing and
disappoints everyone.

## Freezing

Copy bar artifacts into `gauntlet/bar/` at intake and reference them by path
everywhere after. Bars described from memory drift; bars stored as files do not —
and pointing a subagent at a path is cheaper than pasting the bar into its prompt.
