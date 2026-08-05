# Authoring a gauntlet prompt

Sometimes the deliverable is not a run — it is a prompt that will run a gauntlet
somewhere this skill is not installed. This file is how you write one without
shipping a weaker method under the same name.

## When to author instead of run

- The loop will run elsewhere: another agent (Codex, a plain chat), another
  machine, a teammate, a scheduled job
- The user asked for a prompt, not for a run
- The user wants to see what they would be agreeing to before spending the compute

If the loop is going to run *here*, run it. An emitted prompt is strictly weaker
than the skill — see "Degraded" below — and offering one in place of a run you
could have performed is a downgrade dressed as a deliverable.

## The input is a confirmed contract, not a wish

Authoring does **not** skip Phase 0. Run intake exactly as `intake.md` describes
and get the contract confirmed. What you skip is `init`, the waves, and the
script.

An unconfirmed contract produces a prompt with a soft bar and no inspection path
— the two failures round zero exists to catch, now shipped to someone who has no
round zero to catch them with.

## Element checklist

The reference shape is Shumer's original prompt. Nine elements. The contract
supplies eight of them directly.

| Element | Contract field | Cost of omitting it |
|---|---|---|
| Goal, as destination not route | `GOAL` | the reader optimises a route nobody validated |
| Bar, concrete and reachable by the reader | `BAR`, `BAR KIND` | "make it great"; unarguable becomes arguable |
| Inspection path | `INSPECT` | critics grade descriptions — not a gauntlet |
| Decomposition directive | `LANES` | one giant lane; verdicts go vague |
| Builder/critic separation | non-negotiable | the builder grades its own homework |
| Critic stance and verdict format | `critic.md` | sycophancy; gaps too vague to action |
| Blind protocol | `blind-protocol.md` | deference to the reference, gentleness toward ours |
| Champion/challenger guard | non-negotiable | downhill drift, one plausible round at a time |
| Stop condition and budget | `STOP`, `BUDGET` | an uncapped loop on someone else's money |

The original prompt carries goal, bar, decomposition, separation, stance, blind
comparison, and a stop of "until each sub-agent is utterly wowed". It carries no
inspection path, no budget, and no revert guard. Those three are this skill's
additions and they are the first things a shortening pass will try to cut. Do not
cut them.

## Two tiers

Ask which one before writing. It is a one-word question and it changes the entire
output.

**Attached** — the reader has this skill installed. Emit the confirmed contract
block, the `gauntlet.py init` line, and one instruction to run the gauntlet-loop
skill against it. Do **not** inline doctrine: they already have the references,
and inlining creates a second source of truth that will drift from the first.
Ten lines is a complete attached prompt.

**Standalone** — the reader has an agent with file and tool access but not this
skill. Everything must travel inside the file. Fill `assets/prompt-template.md`
from the contract. This is the tier the rules below exist for.

## Rules for the standalone tier

**Never emit an uncapped loop.** `until it's perfect` is the shape users copy,
and an unattended loop without a ceiling is the one thing this skill refuses to
offer. Every emitted prompt carries an explicit wave ceiling and an instruction
to stop there and ask. You are writing a prompt that will spend somebody else's
money while nobody is watching it.

**Render from the reference files, not from memory.** Open `critic.md` and
`blind-protocol.md` while you fill the template. Paraphrasing doctrine out of
context is exactly the drift `failure-modes.md` warns about, and here it is
permanent: the emitted file has no path back to the source.

**Stamp provenance.** Date, and which reference files it was rendered from. An
unstamped prompt is indistinguishable from a stale one a year later.

**One file, role sections inside it.** Do not emit separate builder/critic/
smoother prompt files. Multiple files get separated from each other, and the one
that goes missing is usually the critic.

**Keep the bar with the prompt.** A prompt that points at bar artifacts the
reader does not have is a prompt with no bar. Either ship the bar files alongside
it, or make the bar something the reader can independently reach (a public URL,
a named product, a stated measurement).

## Degraded — and say so in the prompt itself

A standalone prompt has no `gauntlet.py`. That costs two things:

1. **Counting.** Streaks, revert rate and budget consumption fall to the reading
   model — and a model counting its own streaks across a long context is the
   precise drift the script exists to prevent.
2. **Validation.** Nothing rejects a severity with no named gap, an undeclared
   dimension, or a clean verdict citing no evidence. Those rejections are load
   bearing; without them a lazy critic ends the run early and nobody notices.

So the emitted prompt asks the reader to keep a plain append-only log by hand,
and it states its own limitation in its own text. Writing the caveat only in chat
does not count — the chat will not travel with the file.

## What not to author

Per-run builder, critic or smoother prompt files **when this skill is
installed**. Those roles live at fixed paths and are pointed at, not copied
(`failure-modes.md`: never restate the bar from memory into a subagent prompt —
point at the path). Generating per-run copies gives you an artifact that drifts
from its source and a run that no longer benefits from fixing the source.

## Emission

Write to `gauntlet/prompt.md` when a state directory exists; otherwise wherever
the user asked. Then report four things and stop: the bar, the ceiling, the tier,
and the one-line degraded caveat. Do not paste a long prompt back into chat — the
file is the deliverable, and the chat copy is the one that goes stale.
