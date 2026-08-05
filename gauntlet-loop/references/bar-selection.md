# Setting the bar

The bar is the whole method. Everything else is machinery for repeatedly hitting it.

A usable bar has three properties:

1. **External** — it exists independently of this run and of the agent's opinion
2. **Inspectable** — a critic can look at it, run it, or measure against it
3. **Unarguable** — the artifact cannot talk its way past it

"Make it amazing", "production-ready", "polished", "best-in-class" fail all three.

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

If nothing external exists, build one: generate three deliberately different
candidate versions first, have the user pick the best, and use it as the champion
the loop must beat. A self-generated bar is weaker than an external one and you
should say so, but it beats no bar at all.

## Unreachable bars are fine

A bar does not need to be realistically achievable. Its job is to supply direction
and to prevent the loop from stopping at "good considering the circumstances".
Runs against very high bars typically stop while still improving — that is the
expected outcome, not a failure.

Say this explicitly when you propose an ambitious bar. The user should read it as
a heading, not as a promise.

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

## Freezing

Copy bar artifacts into `gauntlet/bar/` at intake and reference them by path
everywhere after. Bars described from memory drift; bars stored as files do not.
Raising a bar mid-run is legitimate and must be announced. Lowering one is how
long runs fail without anyone noticing.
