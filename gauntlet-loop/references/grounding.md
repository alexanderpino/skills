# Grounding

A builder writes from the model's memory unless something stops it. Memory is a
lossy, undated copy of what was true when training ended — excellent for shape,
unreliable for detail, and silently confident about both. For anything a spec, a
maintainer or a named expert has already settled, reconstructing it from memory
is worse *and* more expensive than fetching it: the reconstruction looks right,
survives a critic that also runs on memory, and costs rounds when it turns out
to be a version behind.

This is the same rule as "no self-invented bar", applied to the build: do not
invent what a source has decided.

## When to ground

Ground when any of these is true:

- **It has a canonical answer.** A spec, an RFC, the official reference for the
  exact version in use, the dependency's own source. If the question is "what
  does this actually do", memory is a paraphrase of a document you could read.
- **It is version-dependent.** Flags, endpoints, defaults, deprecations, prices,
  model ids, config keys. These move after the cutoff, and memory cannot know
  that they did.
- **It is a well-trodden problem.** Auth flows, retries and idempotency, cursor
  pagination, time zones and DST, cache invalidation, float comparison, Unicode
  normalisation, concurrency primitives. Someone already paid for the edge
  cases; buy their receipts instead of rediscovering them one bug at a time.
- **Being wrong is expensive or invisible.** Security, money, data loss, or
  anything a critic cannot catch by looking at the output.

Do not ground what you would get right anyway and could confirm with one
command: standard-library names, syntax, textbook algorithms. The test is the
one every rule here answers to — does the fetch buy a gap, or is it ceremony?

## The source hierarchy

**Authority attaches to the author and the primary source, never to the venue.**

- **Tier 1 — normative.** The standard itself (RFC, W3C, ECMA, ISO), the
  official documentation for the version actually in use, and the dependency's
  own source. When docs and source disagree, source wins: docs describe intent,
  code is behaviour.
- **Tier 2 — named authority.** Maintainers writing about their own project,
  recognised domain experts with a public track record (Jon Skeet on C#, Andrew
  Lock on ASP.NET Core, MVPs, standards editors, the canonical text of a field),
  peer-reviewed work.
- **Tier 3 — community aggregate.** Stack Overflow threads, blogs, tutorials,
  forum posts, generated content. **A pointer, never a citation.** Follow it to
  tier 1 or 2 and cite that instead.

The distinction that matters in practice: a Stack Overflow *answer by Jon Skeet*
is tier 2 — the authority is the author, not the site. The reverse holds too: a
vendor-branded blog post by nobody in particular is not tier 1 because the
domain looks official. Ask who is accountable for the claim, not where it sits.

## Cite what you opened

The evidence rule, applied to sources: cite what you actually fetched, with the
version or date. A cited URL nobody opened is grounding theatre — progress
theatre in citation form, and worse, because it reads as diligence and so
survives review.

**Never invent a citation.** A plausible URL for a real-sounding document is the
most expensive failure in this file: it passes inspection precisely because it
looks like the thing that would have prevented the error. If a source cannot be
reached, say so in one line and mark the claim unverified — an honest gap is
cheap, a fabricated citation is not.

## Where it lands in the loop

- **Builders** ground before writing and name the source in the handoff — one
  line inside the five-line cap: what was opened, which version (`builder.md`).
- **Critics** may name an ungrounded claim as the round's gap when a canonical
  answer exists: "this reproduces the retry semantics from memory; the vendor's
  reference says otherwise" is a specific, actionable gap.
- **Gates.** A grounded fact that a command can re-check becomes a gate at the
  next wave boundary — the version pin, the flag's existence, the header name.
  Judgement is spent once; the check then runs free (`cost-discipline.md`).
- **A choice is not a fact.** If grounding surfaces a decision rather than an
  answer — two defensible approaches, no authority between them — that is
  escaped fog: back to the map or the user, not settled by the builder
  (`bar-selection.md`).

## Cost

One fetch is cheaper than a wrong build that survives three rounds and then
gets reverted. But grounding an entire area "to be safe" is the cold-re-read
pattern that cost rule 3 exists to stop: fetch the specific thing the round
needs, not the surrounding library.

And grounding is not a substitute for the bar. The bar says what good looks
like; a source says how the thing works. Both are external, and they answer
different questions.
