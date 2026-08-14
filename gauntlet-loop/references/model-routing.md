# Model routing

Every subagent call picks a model and an effort level. Picking them per *role*
rather than running everything on one tier is the largest cost lever in the
method after the WIP limit — and the one place where economising can silently
destroy the run's evidence.

**The rule: the cheapest model that can do that role's job, and never cheaper on
the critic whose verdict decides something.**

## Prices, so the arithmetic is real

Per million tokens, input / output, on the Claude API (verify before quoting —
these move, and partner platforms price separately):

| Model | ID | Input | Output | Relative to Opus |
|---|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | $10 | $50 | 2× |
| Claude Opus 5 | `claude-opus-5` | $5 | $25 | 1× |
| Claude Sonnet 5 | `claude-sonnet-5` | $3 | $15 | 0.6× |
| Claude Haiku 4.5 | `claude-haiku-4-5` | $1 | $5 | 0.2× |

A wave that runs its mechanical builders on Haiku instead of Opus pays a fifth
for those calls. A wave that runs its deciding critic on Haiku saves the same
fifth and can hand you a retirement you cannot trust — which costs the whole
run. The asymmetry is the entire point of routing by role.

## The second dial: effort

`effort` (`low` / `medium` / `high` / `xhigh` / `max`) moves thinking depth and
token spend within a model, and on current models the low end is unusually
strong — `low` and `medium` often beat a previous generation's `xhigh`. Sweep it
rather than assuming; a role that needs Opus judgement at `medium` is cheaper
than the same role on a smaller model at `max`, and usually better.

Default: `high` for judgement roles, `low`/`medium` for mechanical ones,
`xhigh` on the hardest builder work only.

## Routing by role

| Role | Model | Effort | Why |
|---|---|---|---|
| **Machine gate** | none | — | A command decides it. This is the cheapest "call" in the method (`cost-discipline.md`). |
| **Builder, named gap, bounded** — apply a specific change, compress an asset, adjust spacing, run a codemod | cheap tier | low–medium | The judgement already happened; this is execution against a named gap. |
| **Builder, open-ended** — redesign after a revert, structural change, first version in a bootstrap wave | session tier | high–xhigh | The approach is the work. |
| **Critic, deciding** — any round that can retire a dimension, promote into a shared surface, or trigger a park | session tier or better | high | Its verdict spends or saves the rest of the budget. |
| **Critic, routine round** | session tier | medium–high | Still judgement; still not the place to bargain-hunt. |
| **Critic, screening pass** (optional) | cheap tier | low | Only when many rounds are obvious losses — see below. |
| **Smoother** | mid tier | medium | Consistency detection over a bounded diff, not redesign. |
| **Lead agent (you)** | session tier | — | You hold the contract, the log reads and the spending decisions. |

"Session tier" means the model the run is already on — inherit it rather than
naming one, so the routing survives a model release. In Claude Code, the `Agent`
tool takes a `model` override and workflow steps take `opts.model` / `opts.effort`;
omitting them inherits, which is the correct default for every judgement role.

## The screening critic — an option, not a default

When a lane produces many obviously-losing challengers, a cheap critic can run
first and reject the clear failures before a strong critic is spent. It is worth
it only when *both* hold:

- the strong-model call is much more expensive than the cheap one, and
- a real share of rounds are decided by an obvious defect, not by a fine margin

Otherwise it adds a call per round to save a call on some rounds, which is how a
cost optimisation becomes a cost increase. A screening critic **never retires or
parks anything** — it can only say "this challenger is broken", never "this is
good enough".

## Keep the tier fixed within a lane

This is the rule people break, and it corrupts the log rather than the budget.

Streaks, score trends and the stall detector all assume the *artifact* is what
changed between rounds. Swap the critic's model mid-lane and a flat score might
mean the artifact stopped moving — or that the new critic is stricter. The run
then parks a healthy lane, or funds a dead one, on a confounded reading.

So: pick the tier when the lane is cut, keep it for the lane's life, and change
it only at a re-cut, announced and recorded. Record it either way — `log-round
--critic-model <id>` puts the tier in the record, and `report` prints the
distribution so a reader can see which verdicts came from where.

A clean streak produced by a cheap critic is weaker evidence than one produced by
a strong critic, exactly as a rubric round is weaker than a blind round. Say so
in the report rather than letting the streak speak for itself.

## The bias routing cannot fix

LLM judges prefer text from their own model family — *self-enhancement bias*,
measured in Zheng et al. (`authorities.md`). In practice every agent in this run
is usually the same family, so you cannot route around it: builder and critic
share a lineage whatever tier you pick.

Do not pretend otherwise. What actually works is already in the method — the
critic judges an **external artifact** it did not generate, against a **frozen
bar** it cannot rewrite, with **randomised labels** and no builder rationale. A
same-family judge scoring a real artifact against a real reference is a far
weaker version of the effect than one scoring two candidate *texts*.

Two practical consequences. Where a dimension is machine-checkable, the gate
outranks any critic and the bias disappears entirely — one more reason cost rule
1 comes first. And where the user supplies a competing implementation as the bar,
say in the report that the comparison was same-family, so a reader can discount
it themselves.

## Anti-patterns

- **Cheap critic on a retirement round.** The one verdict that ends spending on a
  lane is the one to buy the best judgement for.
- **Expensive model on a machine-checkable dimension.** No model needed at all.
- **One tier for everything, chosen by habit.** Either you overpay on every
  mechanical call or you underbuy on every judgement.
- **Routing by lane instead of by role.** "Imagery is on Haiku" is not routing —
  it means the imagery lane's *critic* is on Haiku too.
- **Switching tiers to save a stalled lane.** A stronger critic does not make a
  parked lane worth funding; it just re-litigates a decision the log already made.
