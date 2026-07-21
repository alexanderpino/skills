# Worked Example: A Full End-to-End Run

This is one complete pass of the method, shown in full so the workflow is
concrete. The question is deliberately fuzzy and strategic — the kind where the
default answer is known and unsatisfying, which is exactly when the matrix earns
its cost.

---

## Phase 1 — Frame and name the default

**Inquiry:** Why do most knowledge-worker teams get *slower* as they add more
people, even when everyone is individually competent and motivated?

**Altitude check:** Is this a symptom of a higher question ("why do we grow
headcount at all")? No — the slowdown appears across orgs with very different
growth rationales, so the stated level is the right one. Proceed as posed.

**Insight type:** Causal.

**Default answer:** "Communication overhead grows with team size (Brooks's Law) —
more people means more coordination links, so throughput per person drops."
This is correct, well-known, and the thing we want to get *past*. Any insight has
to beat this.

---

## Phase 2 — Build the axes

**Anchors (rows)** — the load-bearing pieces of *this* problem:

1. The new hire (the marginal person added)
2. Shared context (what the team collectively knows)
3. The work itself (its divisibility)
4. The decision process (how the team commits to choices)
5. Individual incentives (what each person optimizes for)

**Lenses (columns)** — chosen for a causal insight type: Substrate, Inversion,
Second-order, Temporal, Reframe-the-unit.

---

## Phase 3 — Populate the matrix

| | Substrate | Inversion | Second-order | Temporal | Reframe unit |
|---|---|---|---|---|---|
| **New hire** | Onboarding assumes context is transferable; much of it is tacit | What guarantees a hire slows the team? Adding them before there's stable context to absorb | Existing members become teachers, losing their own output | A hire is negative-throughput for months before positive | Hire isn't "+1 worker," it's "−N teacher-hours" |
| **Shared context** | Requires every member to hold a model of the whole | What destroys shared context? Growth faster than context can propagate | Context fragments into sub-models that quietly diverge | Context decays as memory; constant re-sync cost | The unit isn't "knowledge," it's "synchronized knowledge" — perishable |
| **The work** | Assumes work is divisible without loss | What guarantees no speedup? Work whose parts can't be done independently | Splitting work creates integration work that didn't exist before | — | Unit isn't "tasks," it's "tasks + the seams between them" |
| **Decisions** | Assumes someone can still close decisions | What guarantees paralysis? Every voice gaining a veto as the group grows | More stakeholders → decisions get *safer*, i.e. worse and slower | Decision latency compounds: each delay delays dependents | Unit isn't "the decision," it's "the queue of decisions waiting on it" |
| **Incentives** | Assumes individual output is visible | What makes people optimize against the team? Rewarding visible individual work | People route around coordination to protect personal metrics | — | Unit isn't "the worker," it's "the worker's incentive gradient" |

(Two cells left `—` honestly: temporal on "the work" and on "incentives" didn't
produce anything that beat the default.)

---

## Phase 4 — Score and filter

Scoring each live cell on Novelty (vs. the Brooks's-Law default) × Validity:

- **New hire × Reframe** ("−N teacher-hours"): Novelty High (default counts links,
  not the *production-to-teaching conversion*), Validity High. → **INSIGHT**
- **Shared context × Reframe** ("synchronized knowledge is perishable"): Novelty
  High, Validity High. → **INSIGHT**
- **Decisions × Second-order** ("more stakeholders → safer, worse decisions"):
  Novelty Med-High, Validity High. → **INSIGHT**
- **Decisions × Reframe** ("the queue waiting on a decision"): Novelty High,
  Validity High. → **INSIGHT**
- **Work × Second-order** ("integration work that didn't exist"): Novelty Med,
  Validity High — close to the default's "coordination cost." → **CONFIRMATION**
- **Incentives × Inversion** ("rewarding visible work"): Novelty Med, Validity
  High. → borderline CONFIRMATION; keep as supporting.
- **Shared context × Inversion** ("growth faster than propagation"): Novelty
  High, Validity Med — plausible but hand-wavy as stated. → **PROVOCATION**,
  attached test: measure whether teams that pause hiring after doubling recover
  speed faster than teams that keep growing slowly.
- The rest: Noise or Confirmation, discarded.

**Demotion pass** (attack every candidate High before committing): the
"−N teacher-hours" cell is the most fluent of the four — tried to break it as a
relabel of ordinary onboarding cost. It held: the default treats teaching as
overhead *around* added capacity, this cell flips the sign of the hire itself
for months, which predicts something the default doesn't (senior output drops
*before* headcount shows in delivery). "Safer, worse decisions" wobbled hardest
— its mechanism is one sentence but its falsifier was weak — so it stays High
only with the single-decider test named in the synthesis.

---

## Phase 5 — Synthesize

**Look for convergence.** Three high-value cells reached by different lenses
(New-hire×Reframe, Shared-context×Reframe, Decisions×Reframe) all re-cut the
problem the same way: the team's true bottleneck isn't *people* or *links*, it's
a **perishable, shared resource** — synchronized context — that every added
person both *consumes* (must be brought up to speed) and *threatens* (adds a
model that can diverge). That convergence is the spine of the main insight.

**Crystallized insights:**

**Insight 1 — Teams don't slow from communication overhead; they slow from
context being a perishable resource that scales sub-linearly.**
*Why non-obvious:* Brooks's Law frames the cost as *links between people* (a
combinatorial but static structure). This reframes it as a *stock that decays and
must be continuously re-synchronized* — a flow problem, not a graph problem. The
fix implied is totally different: not "fewer links" but "cheaper re-sync and
slower context decay" (written artifacts, decision logs, durable docs).
*Rests on:* the three Reframe cells converging.
*Could be wrong if:* teams with excellent durable documentation slowed down just
as fast — that would push the cause back toward raw link-count.

**Insight 2 — The marginal hire's first-order cost is mispriced: they aren't +1
worker, they're −N teacher-hours drawn from your most knowledgeable people.**
*Why non-obvious:* The default treats the new person as added capacity with some
overhead. This says the *sign* is wrong for months: the hire subtracts from
exactly the people whose output matters most, and that cost is invisible because
teaching doesn't show up as a deliverable.
*Rests on:* New-hire × Reframe and × Temporal.
*Could be wrong if:* onboarding were fully self-serve (great docs again) — note
this is the same lever as Insight 1, which strengthens both.

**Insight 3 — Growth degrades decision quality before it degrades decision speed,
and the quality drop is the hidden slowdown.**
*Why non-obvious:* Everyone watches decision *latency*. The second-order cell
shows the quieter failure: more stakeholders make decisions *safer and more
compromised*, so the team executes mediocre choices efficiently — fast motion,
wrong direction, which reads as "slow" in outcomes but not in activity.
*Rests on:* Decisions × Second-order, supported by × Reframe (decision queues).
*Could be wrong if:* teams with a single empowered decider showed the same
outcome-quality drop with scale.

---

## Phase 6 — Stress test

- Insight 1 survives: the falsifier (well-documented teams slow equally) is
  empirically *not* what we observe — documentation-heavy teams scale better,
  consistent with the claim.
- Insight 2 survives and *reinforces* Insight 1 (same lever), which is a good
  sign — independent insights pointing at one intervention.
- Insight 3 survives but is the most contestable; flagged as such. The single-
  decider falsifier is a clean experiment a reader could actually run.

The Provocation (context propagation speed as a hard limit) is kept in its own
section, labeled unproven — it might be the deepest idea here, but it hasn't
earned Insight status yet.

---

## Distillation

The three surviving insights converge cleanly, so distillation is warranted (it
would be skipped if they'd pointed at separate levers):

- **Core variable:** *synchronized shared context* — a perishable stock that
  every added person both consumes and threatens. Insights 1 and 2 are two faces
  of it; Insight 3 is what happens when it fragments. Move this one variable and
  the others move.
- **Rule of thumb:** *When a group slows as it grows, suspect a decaying shared
  stock before you blame the links between people — and fix it with cheaper
  re-sync, not fewer connections. Unless* the team already has excellent durable
  artifacts and still slows, in which case the cause really is raw link-count and
  this heuristic fails (the same falsifier as Insight 1, which is why it's safe to
  carry forward).

---

## What this example demonstrates

- The **default** did real work: it's why "integration work" scored only
  Confirmation — too close to known coordination cost to count as new.
- The **biggest insight was a convergence**, not a single cell. Three lenses
  independently re-cut the problem the same way; that triangulation is what makes
  Insight 1 trustworthy rather than just clever.
- **Honesty about cell status** (Confirmations, the Provocation, the empty cells)
  is what separates this from a generator of plausible-sounding nonsense.
- The output a user actually reads is the three insights — the grid is shown for
  inspectability but lives below the answer.
- **Distillation rode on the convergence**, not on top of it: because three
  insights already triangulated on one structure, naming the core variable and a
  portable rule of thumb was a sharpening of the synthesis, not a new claim — and
  the rule carries its own falsifier, so it isn't fortune-cookie advice.

---

# A second run that *fails* — and why that's the method working

The example above lands three insights, which can leave the impression that the
matrix always pays out. It doesn't, and a method whose only virtue is honesty has
to show its own null result. Here is a run that correctly concludes **the default
was right** and returns nothing better.

## Phase 1 — Frame and name the default

**Inquiry:** Why do passwords have to be changed every 90 days at my company?

**Insight type:** Causal.

**Default answer:** "It's a legacy security policy. Forced rotation was once
standard advice, but modern guidance (NIST 800-63B) actively recommends *against*
mandatory periodic rotation — it pushes users toward weaker, incrementing
passwords. The honest answer is: it's cargo-cult compliance that current evidence
no longer supports." This is correct, well-supported, and complete.

**Gate check:** ...and that's a problem for the matrix. The default already fully
answers the question, including *why it's wrong*. By the default-first gate, this
should stop here. But suppose we don't notice, and build anyway — watch what the
filter does.

## Phases 2–4 — Build, populate, filter

Anchors: the policy, the user, the attacker, the compliance auditor. Lenses:
Inversion, Adversarial, Second-order, Substrate, Temporal.

The grid fills, but every live cell collapses under Phase 4's probes:

- *Policy × Second-order:* "Rotation makes users pick `Summer2024!` → `Summer2025!`"
  — **Reversal test fails as novelty**: this is the default *restated*, not past
  it. → CONFIRMATION.
- *Attacker × Adversarial:* "A leaked hash is exploited within hours, long before
  90 days" — true, but again **the default already says rotation is ineffective**.
  → CONFIRMATION.
- *Substrate × policy:* "The policy survives because auditors check for it" —
  plausible (it's why legacy policies persist), but **no named falsifier** that
  distinguishes it from generic institutional inertia, and zero novelty over
  "cargo-cult compliance." → NOISE.
- *Temporal × user:* "From the future, all knowledge-factor auth looks quaint next
  to passkeys" — **Mechanism check**: true but it answers a *different* question
  (what replaces passwords), not *why this company rotates them*. Off-target. → NOISE.

No cell clears High novelty × High validity. The few valid cells are all
Confirmations of the default; the few novel-sounding cells fail the reversal or
falsifier probe.

## Phase 5–6 — Synthesize / deliver

**Nothing to crystallize.** The honest output is: *"The default answer is the
answer — forced 90-day rotation is outdated, evidence-discouraged compliance
theater. The matrix found no deeper structure, because there isn't one to find
here: this is a settled question, not an open one."*

## What this null run demonstrates

- **The gate exists for exactly this.** A well-specified question with a known,
  satisfying answer is where the matrix burns cost for nothing. Naming the default
  in Phase 1 *is* the test — when it's already complete, stop.
- **A null result is a success, not a failure of the method.** A matrix that
  *always* produces three shiny insights is a bullshit generator; one that can
  return "the obvious answer wins" is trustworthy precisely because it can say no.
- **The probes did their job.** Every tempting cell was caught — by the reversal
  test (it was the default restated) or the falsifier check (unfalsifiable
  inertia). That's the Validity machinery earning its place.
