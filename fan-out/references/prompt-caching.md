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
anywhere in that chain invalidates everything after it. Swapping one tool changes the tool
block, which sits in front of everything, which invalidates the whole prefix — even if
every message is identical.

This is why the fan-out design puts the shared brief first and the per-agent delta last.
Two builders whose prompts differ only in the final line share their entire prefix. Two
builders whose prompts open with "You are agent 2 of 5" share nothing at all, even though
the difference is six characters.

## The mechanics you can rely on

- **Minimum cacheable prefix**: roughly 1,024 tokens on the larger models (about 2,048 on
  the small ones). Below that, nothing is cached and the design effort is wasted. A brief
  under ~1,000 tokens is usually a sign the agents will have to go exploring anyway, which
  is a bigger problem than the missed cache.
- **TTL**: 5 minutes by default, refreshed on every hit. A run that keeps moving stays
  warm indefinitely; a run that pauses for coffee between build and critique goes cold and
  pays the write again. A 1-hour TTL exists for cases where a human is in the loop.
- **Economics**: writing the cache costs more than an uncached read (~1.25x); reading it
  costs far less (~0.1x). The break-even is therefore around two reads. With N=5 builders
  plus 5 critics, you write once and read nine times — that's where the design earns out.
- **Breakpoints**: a handful per request, and the cache checks for hits at each one going
  backwards. More breakpoints means more chances of a partial hit when the tail changes.

Verify current numbers against Anthropic's caching docs before making a cost argument to
someone — these move.

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

**You don't control:**
- Breakpoint placement, TTL selection, or whether the harness caches at all
- Whether a subagent's system prompt matches another's (it generally does for same-type
  agents, which is what makes prefix sharing possible)

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

## Why the pathfinder goes first

If you spawn all N builders simultaneously from cold, every one of them races to write the
same cache entry and none of them reads it. You pay N cache writes (~1.25x each) instead
of one write plus N-1 reads (~0.1x each), which is close to the worst possible outcome for
a design that went to the trouble of sharing a prefix.

Running builder #1 alone first, then the rest in parallel, costs one agent's wall-clock
latency. Note the honest caveat: the cache is written when the first *request* completes,
not when the agent finishes its whole task, and you can't observe that moment from
outside. Waiting for the pathfinder to return is a conservative approximation — correct,
but it over-waits. If latency matters more than tokens, spawn everything at once and
accept the write cost; that trade is legitimate, just make it deliberately.

The same logic applies to the critic wave: spawn them together, immediately after the
builders, while the prefix is still warm.

## When caching is not worth engineering for

- Brief under ~1,000 tokens — below the minimum, nothing to cache.
- N = 2 — one write, one read, roughly break-even.
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
- [ ] Per-agent text is below the `---` separator and is one or two lines
- [ ] `rubric.md` was written before any builder ran
- [ ] `fanout.py seal` has been run
- [ ] Builder #1 has returned before #2..N are spawned (or you've deliberately opted out)
- [ ] Critics are queued to go immediately after the builders, not after a human review
- [ ] `fanout.py check` passes at the fold
