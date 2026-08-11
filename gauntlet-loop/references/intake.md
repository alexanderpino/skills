# Intake

The contract exists because an unattended loop cannot ask permission later. Every
field here is something that becomes expensive or impossible to change once the
loop is running.

## Phase 0: The Workbench (Must be step 1)

Before proposing a contract, set up the live progress board.

1. Copy `assets/workbench.html` from this skill to `gauntlet/workbench.html`.
   It is boilerplate — a generic renderer over one spec document, the way Swagger
   UI renders an OpenAPI document. Copy it once; never edit it.
2. `python3 scripts/gauntlet.py board` writes the spec (`state.json`, plus
   `state.js` so the page also works when opened straight off disk).
3. Open it in the user's browser (`start`, `open`, or `xdg-open`). For a live
   board during an unattended run, serve the directory instead —
   `python3 -m http.server` inside `gauntlet/` — and the page polls itself.

**Nobody edits the HTML, and nobody hand-writes the spec** — not you, not a
subagent. Regenerating the board is one deterministic command; a subagent that
has to open an HTML file to report progress pays for the whole file every round
it does so. → `workbench.md`

## How to run intake without interrogating anyone

Most of the contract you can propose. Only two things genuinely require the user:
**the stop conditions** and **the budget** — they encode how much of the user's
time and money this run may spend, and you cannot infer that.

So: infer or propose the rest, present the whole contract as a block, ask them to
confirm or correct it. One exchange, not seven questions.

If the user has given a bar already, say so and move on. If they have not, propose
one with a one-line justification and let them override it.

## The contract block

```
GOAL     <destination, one sentence — not an implementation plan>
BAR KIND <reference | acceptance criteria | hybrid>
BAR      <the concrete comparator, and where its files live>
INSPECT  <how a critic reaches the real output each round>
LANES    <your proposed initial split, or "to be cut after first look">
STOP     <which conditions are armed, with thresholds>
BUDGET   <tokens (and the money that is), plus waves — always set; whichever
         depletes first stops the run and triggers an extension offer.
         Optional hard cap: the ceiling extensions may not cross>
LADDER   <starting tier and what each escalation costs; default tier 0 (probe)>
MODELS   <which model each tier label uses, and what the top one costs relative
         to the cheapest — the roster is part of the agreement, not an internal
         detail. Default: haiku-4-5 / sonnet-5 / opus-5 at 1× / 3× / 5×>
AUTONOMY <unattended until stop | check in between waves>
BENCH    <where progress is visible>
```

## Field notes

**Goal.** Watch for users handing you an implementation plan and calling it a goal.
"Build the renderer with a deferred path and clustered lights" is a route. "Make
the lighting hold up against these three reference frames" is a destination. If
they insist on the route, take it — but note that you are giving up the model's
judgement about approach, which is where a lot of the method's value sits.

**Bar Kind.** Must be one of three explicit types:
- `reference`: compare against an existing product or URL.
- `acceptance criteria`: compare against a checklist or test suite.
- `hybrid`: a combination of both.

**Bar.** See `bar-selection.md`. Freeze the artifacts under `gauntlet/bar/` now,
before any lane runs — and **go and find them rather than waiting to be given
them**. Whatever the user pasted is the seed of your search, not its result:
list the cases the run will be judged on, get a reference for each, and record
in `bar/SOURCES.md` where each came from and what you searched for without
success. Presenting a contract whose bar is exactly the user's own examples,
with the uncovered cases unmentioned, is how a run reaches wave 4 and announces
that a case cannot be judged.

**Inspection.** This is the field that silently kills runs. Before wave one,
verify a critic can actually reach the output: the screenshot harness works, the
build runs, the benchmark produces numbers, the document renders. A loop where
critics grade descriptions is not a gauntlet, it is a conversation.

While you are there, note **which dimensions have a numeric oracle** — a frame
time, an LCP, a bundle size, a passing test. Those dimensions do not need a model
to judge them (`--mode oracle`, see `cost-model.md` §5), and knowing which they
are before wave 1 is often the single largest saving available in the whole
contract. Note the **no-change check** too: the command that tells you a builder
actually touched its owned paths, so a round is never spent judging nothing.

**Stop.** Ask explicitly. See `stop-conditions.md`. Users routinely want several
armed at once and that is correct — first to fire wins.

**Budget.** Always armed even when other conditions are. It is the backstop that
makes unattended running safe to agree to.

**Set it in tokens, and say what that is in money.** Waves are not a unit of
money: a wave costs whatever its lanes, dimensions and effort tier happen to
cost, and a budget denominated in waves is a budget the user cannot evaluate.

```bash
--budget-waves 8 --budget-tokens 20000000 --cost-per-mtok 9.0
```

Give the user the arithmetic behind it: calls per lane per round = 1 builder +
(critic calls × dimensions), times lanes, plus one smoother per wave. State the
projected total in the contract block — in their currency — so the budget line is
a number they can react to. Parallel lanes raise the burn rate, not the total.

Then stop estimating: **round zero prices the run.** Log its tokens, extrapolate,
and put the measured projection in front of the user before wave 1. If it comes
out disproportionate to the artifact, that is the cheapest possible moment to
say so.

Say what happens when it runs out, at intake, so nobody has to guess later: the
run **stops**, reports, and comes back with an extension offer — a next block of
waves, priced from the run's own measured cost, with the log's read on whether
the artifact is still improving. That makes the first budget a cheap first
checkpoint rather than a bet on the whole run, and users pick a realistic number
instead of an inflated one.

**Ladder.** Say where the run starts and what escalation costs, because it is the
line that makes an ambitious budget safe: the run begins at tier 0 (one lane, one
dimension, cheap models) and buys its way up only on evidence from the log. An
idea that does not work therefore costs a fifth of the budget, not all of it.
Full model: `cost-model.md`. Users who want to skip straight to tier 2 can — but
tell them what the ladder was protecting them from before they do.

**Models.** Put the roster in the contract. Which model runs builders, which runs
critics, and what the top tier costs relative to the cheapest — by default 5×,
which is the number that makes the routing worth having. The default is
`--models cheap=claude-haiku-4-5,mid=claude-sonnet-5,high=claude-opus-5`; propose
it, and let the user override it there rather than changing it mid-run.

Say plainly what the routing is for: **the most expensive model is not the
default.** Generation quality is the artifact and is worth paying for; deciding
which of two screenshots is closer to a reference usually is not. Say too that
the run will *check* that assumption — escalated verdicts are compared against
the ones they replaced, so the report can tell them whether the expensive critic
earned its multiplier on this artifact.

**Hard cap (optional).** For users who want long unattended running, pair a small
budget with a cap rather than setting one huge budget:
`--budget-waves 8 --hard-cap-waves 20 --hard-cap-tokens 60000000`. The budget is
where you stop and report; the cap is the ceiling no extension may cross. Cap
both units — a token cap without a wave cap (or the reverse) leaves the other one
free to run away. Without a cap, every extension needs the user again — which is
the safe default, not a shortcoming.

**Autonomy.** If the user wants check-ins, the natural boundary is the end of a
wave, after smoothing — the artifact is coherent there and a decision is cheap.
Mid-lane check-ins fragment the loop for no benefit.

## Cold start

When the artifact does not exist yet — the canonical from-scratch gauntlet —
"current artifact" in the contract is simply *empty*, and wave 1 is a bootstrap
wave: builders produce first versions, there is no champion to compare against,
and the first bar comparison runs as soon as there is output to inspect. Do not
manufacture a fake baseline to compare the first round against; the bar itself is
the comparison from round 1.

## Before wave one

Run a **round zero** — which is simply tier 0 of the effort ladder: one lane, one
dimension, one build, one critic, one verdict. It surfaces the two failures that
would otherwise waste hours — a broken inspection path, and a bar the critic
cannot actually compare against.

If round zero produces a vague verdict, the bar is too soft. Fix it before scaling
up to a full wave. `gauntlet.py tier` refuses the escalation for you.

Then price it. Log the tokens it cost, run `gauntlet.py status`, and give the user
the projection before wave 1:

> "Round zero cost ~420k tokens (≈ €3.80). At that rate the 8-wave budget lands
> around €150–190. Still want 8, or should the pilot decide?"

That sentence is worth more than every estimate in this file.

## Recording it

Initialise the state directory as part of confirming the contract:

```bash
python3 scripts/gauntlet.py init --lanes <a,b,c> --dimensions <d1,d2> \
    --bar-kind <kind> --bar-met-n 2 --clean-streak-n 2 \
    --budget-waves <N> --budget-tokens <T> --cost-per-mtok <rate> \
    [--hard-cap-waves <M>] [--hard-cap-tokens <C>] [--flat-rounds-n 3]
```


Write the confirmed contract to `gauntlet/contract.md`. Every subagent that needs
the goal, bar or rules reads it from there rather than from a paraphrase in a
prompt — paraphrase drift across a long run is real and compounds.
