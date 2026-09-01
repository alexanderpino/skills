# Prompt caching in a fan-out

Read this before changing prompt shapes, the spawn sequence, or the brief.

## Contents
- [What the cache actually keys on](#what-the-cache-actually-keys-on)
- [The mechanics you can rely on](#the-mechanics-you-can-rely-on)
- [What an orchestrator controls, and what it doesn't](#what-an-orchestrator-controls-and-what-it-doesnt)
- [The three cache killers](#the-three-cache-killers)
- [Why the pathfinder goes first](#why-the-pathfinder-goes-first)
- [When caching is not worth engineering for](#when-caching-is-not-worth-engineering-for)
- [Checklist](#checklist)

## What the cache actually keys on

The cache is a **prefix** cache. A hit requires the request to match a previously cached
request from the very first token up to the cached breakpoint — exactly, byte for byte.
Not "mostly the same". Not "semantically equivalent".

The prefix includes, in order: tool definitions, system prompt, then messages. A change
invalidates its own tier and everything after it, so the earlier something sits, the more
expensive it is to touch. Swapping one tool changes the tool block, which sits in front of
everything, and invalidates the whole prefix — even if every message is identical. Editing
the system prompt leaves the tools cache intact but kills system and messages. Changing
only message content leaves both earlier tiers alone, which is exactly why the per-agent
delta belongs at the bottom.

Nearly all of that is the harness's business rather than yours, with one exception you do
choose: **a model switch invalidates everything**, because caches are model-scoped. That is
the tier control an orchestrator actually holds.

This is why the fan-out design puts the shared brief first and the per-agent delta last.
Two builders whose prompts differ only in the final line share their entire prefix. Two
builders whose prompts open with "You are agent 2 of 5" share nothing at all, even though
the difference is six characters.

## The mechanics you can rely on

- **Minimum cacheable prefix — model-dependent, and not monotonic.** 512 tokens on Opus 5
  and Fable 5; 1,024 on Opus 4.8, Sonnet 5 and the Sonnet 4.x line; 2,048 on Opus 4.7;
  **4,096 on Opus 4.6, Opus 4.5 and Haiku 4.5**. Below the threshold nothing caches and no
  error says so — the write count is simply zero. Note what that does to the intuition that
  a smaller model has a smaller minimum: a 3,000-token brief caches on Opus 5 and doesn't
  cache at all on Haiku 4.5, which is exactly the model you would reach for to make a wide
  fan-out affordable. A brief that clears ~4K tokens caches everywhere and needs no thought
  about which model the agents run on.
- **TTL — 5 minutes by default, 1 hour available, and the clock starts when the request
  starts.** A read refreshes the entry for free, but the lifetime runs from the *start* of
  the request that wrote or read it, so generation time is spent out of it: a builder that
  works for four minutes leaves about one minute for the next request to begin. This is the
  trap specific to agent fan-out — "keep the run moving" is not sufficient when one agent
  turn can outlast the whole TTL. What matters is the start-to-start gap between requests
  sharing the prefix: under five minutes the default is strictly cheaper, between five and
  sixty the 1-hour TTL is the only thing that helps, and in most harnesses you don't get to
  choose it.
- **Economics — 1.25x to write on the 5-minute TTL, 2x on the 1-hour one; ~0.1x to read.**
  Break-even is one read on the short TTL (1.25 + 0.1 = 1.35 against 2.0 uncached) and two
  reads on the long one. The design therefore earns out much earlier than "you need a big
  N": with 5 builders and 5 critics you write once and read nine times, but even N=2 is
  four requests against a single write once its critics run.
- **Breakpoints — at most 4 per request**, and each one walks backward at most **20 content
  blocks** looking for a prior entry. The second half bites agents specifically: a builder
  turn that racks up more than twenty tool-use/tool-result blocks pushes the previous entry
  out of the lookback, and the following request rewrites the prefix instead of reading it.
  Nothing you put in the brief prevents that — it's a property of how much tool traffic the
  agent generates, and it is the one cache killer the orchestrator cannot design away.
- **Cache reads mostly don't count toward input-token rate limits.** With N agents in
  flight against a shared quota that can be the difference between a wave that runs and a
  wave that 429s — a second reason to sequence the pathfinder rather than fire N cold.

Verify current numbers against Anthropic's caching docs before making a cost argument to
someone — these move, and the minimums in particular have moved in both directions.

## What an orchestrator controls, and what it doesn't

Be honest about the boundary. Inside an agent harness you generally do **not** set
`cache_control` breakpoints yourself; the harness decides where they go. What you control
is the *content and ordering* that determines whether a breakpoint can hit:

**You control:**
- Whether the shared context is byte-identical across agents (it should be)
- Whether it comes first (it must)
- Whether it changes mid-run (it must not)
- Whether agents are spawned cold-parallel or warm-then-parallel
- Whether agents read one prepared brief or each go discover context themselves
- Whether the whole wave runs on one model — caches are model-scoped

**You don't control:**
- Breakpoint placement, TTL selection, or whether the harness caches at all
- Whether a subagent's system prompt matches another's (it generally does for same-type
  agents, which is what makes prefix sharing possible)
- Whether any of it worked. The usage counters that would prove a hit belong to the
  subagent's request, not yours, so from the orchestrator's seat every rule here is an
  invariant you maintain blind rather than a measurement you can check

**Caches are model-scoped, and that is the easy one to break by accident.** Spawning the
critics on a cheaper model than the builders is an obvious economy and sometimes the right
call — but they then share no prefix with anything the builders wrote and each pays a fresh
write. The brief still saves you N exploration phases, which is the larger benefit anyway;
what evaporates is the reason to hurry the critics out while the prefix is warm. Make that
trade knowingly rather than discovering it in the bill.

So treat every rule here as *raising the probability and size of a hit*, not as a
guarantee. The secondary benefit is unconditional and often larger anyway: one prepared
brief means N agents skip N independent exploration phases. Even with the cache
completely disabled, that's a real saving — and it's why the brief is worth building
regardless.

## The three cache killers

**1. Personalisation at the top.** Anything identifying the agent — number, slice name,
role, assigned files — belongs after the shared block. This is the single most common
mistake because it reads so naturally: you want to tell the agent who it is before you
tell it what to do. Resist it. `YOUR SLICE: <x>` at the bottom works exactly as well.

**2. Volatile content inside the brief.** Timestamps, run IDs, generated UUIDs, "as of
today", random seeds, a file listing that includes `mtime`. Each of these makes the brief
unique per run, which is survivable, or unique per agent, which is not. `fanout.py seal`
exists to catch the second case.

**3. Mutating the brief mid-run.** The tempting move: a builder discovers something
important, so you append it to `brief.md` so the critics see it too. This invalidates the
prefix for every agent that hasn't started yet *and* silently splits the run into agents
working from two different ground truths — which is the more serious problem, because the
critics will now be comparing artifacts built against different specs and won't know it.

If something genuinely must be added mid-run, that's a signal the brief was incomplete.
Finish the round, then start a new sealed run with a corrected brief. New discoveries go
in the per-agent delta below the `---`, never in the shared block.

These three are all about how you *write* the brief, which is why they're grouped. The
fourth killer is about how you *spawn*: mixing models within a wave, covered above. It
costs the same as any of these and `seal` cannot catch it.

## Why the pathfinder goes first

If you spawn all N builders simultaneously from cold, every one of them races to write the
same cache entry and none of them reads it. You pay N cache writes (~1.25x each) instead
of one write plus N-1 reads (~0.1x each), which is close to the worst possible outcome for
a design that went to the trouble of sharing a prefix.

Running builder #1 alone first, then the rest in parallel, costs one agent's wall-clock
latency. Note the honest caveat, and note how large it is: an entry becomes readable once
the first response **begins streaming** — not when that request completes, and certainly
not when the agent finishes its task. The moment you actually need has passed within
seconds of the pathfinder starting, and a builder may then work for minutes. Waiting for it
to return is a conservative approximation: correct, and over-waiting by roughly the whole
task. You take it because a subagent harness gives you no way to observe first-token, not
because the wait is doing work.

Two consequences. If latency matters more than tokens, spawning everything at once is a
legitimate trade — just make it deliberately. And if the pathfinder is going to run long,
remember the TTL clock started when it did: on a 5-minute TTL, a pathfinder that works for
six minutes has expired its own entry before the wave it was meant to warm ever starts.

The same logic applies to the critic wave: spawn them together, immediately after the
builders, while the prefix is still warm.

## When caching is not worth engineering for

- Brief below the minimum for the model the agents run on — 512 tokens at best, 4,096 at
  worst, so a brief under ~4K needs you to know which model that is. A brief that short is
  usually a sign the agents will have to go exploring anyway, which is the bigger problem.
- N = 2 with no critics — one write, one read. Still cheaper than not caching, but not
  worth choreography. With critics, N=2 is four requests on one write and the pathfinder
  pays; skip it there for latency if you like, not for economics.
- Slices requiring genuinely different context — if agent A needs the renderer sources and
  agent B needs the audio sources, there may be no meaningful shared prefix. Put the truly
  common part (goal, constraints, conventions, acceptance criteria) in the brief and let
  each agent load its own domain files itself. A small real shared block beats a large
  fake one.
- One-shot runs with no critics — write-only, never read.

In these cases, drop the pathfinder step and optimise for latency instead. The brief is
still worth writing; the spawn choreography isn't.

## Checklist

Before spawning:

- [ ] `brief.md` is identical for every agent — no names, numbers, times, or IDs
- [ ] `brief.md` is the *first* thing in every prompt, builders and critics alike
- [ ] The brief clears the minimum for the model the agents will run on (~4K clears all of
      them; below that, check)
- [ ] Builders and critics run on the **same** model — caches don't cross models
- [ ] Per-agent text is below the `---` separator and is one or two lines
- [ ] `rubric.md` was written before any builder ran
- [ ] `fanout.py seal` has been run
- [ ] Builder #1 has returned before #2..N are spawned (or you've deliberately opted out)
- [ ] Critics are queued to go immediately after the builders, not after a human review
- [ ] `fanout.py check` passes at the fold
