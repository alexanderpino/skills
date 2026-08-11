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

## Finding the bar is your job, not the user's

The single laziest failure in this skill is to treat the references the user
happened to paste as the entire available world, and then to report a gap as
unjudgeable because *their* examples did not cover it. The user is not the
research department. If a case matters enough to be judged, it matters enough
to go and find something to judge it against.

Three rules, in order of how often they are broken:

**1. The user's examples are a seed, not the corpus.** Someone who wants
photorealistic water and hands you three screenshots has told you the
*direction*, not supplied the bar. Take those three, work out what class of
reference they are, and go get the rest — including the cases they did not
think to send. Coming back with a bar set that is strictly what was pasted is
the tell that no search happened.

**2. "No reference exists" is a claim, and it needs a search behind it.** Never
say a case cannot be barred until you have looked, and when you say it, say
what you looked for and where. Most of the time the honest sentence is not "no
reference exists" but "I did not look" — and a user who finds a counterexample
in two seconds has just proved which one it was. Record searches that came back
empty in `bar/SOURCES.md`; an empty search is real evidence, an unstated one is
not.

**3. For photorealism, the bar is reality, and reality is thoroughly
photographed.** This is the case where "no reference" is almost never true.
Any physical phenomenon a renderer might target — a breaking wave, a jetski
wake, caustics on a sandy bottom, wet sand at the waterline, spray in backlight
— exists in photographs and footage, in quantity, from people who chased it
deliberately. "There is no reference for how that looks at speed" is a claim
about a search that was not run. Reach for a photograph before reaching for
another shipped game: a game frame bars you against someone else's
approximation, a photograph bars you against the thing itself.

### Where to look, by artifact class

| Class | Reference sources worth searching before declaring absence |
|---|---|
| Photoreal rendering | Photography and video of the real phenomenon; stock/press libraries; high-end offline renders; ground-truth captures in papers; the physical measurement behind the look (a spectrum, a slope distribution, a coverage curve) |
| Stylized / game rendering | Shipped titles known for that effect; GDC/SIGGRAPH-Advances talk stills; engine sample scenes; capture galleries and photo-mode communities |
| UI and product | The two or three products in the category everyone benchmarks against; their real screens at your viewport, not their marketing pages; design-system docs for measurable rules |
| Prose and docs | Writers and reference docs with the specific property (clarity, density, structure) — chosen for the property, not for fame |
| Systems and code | Reference implementations, published benchmark suites, competitors' measured numbers, conformance tests |

### Bar coverage is checked case by case, before wave 1

A single reference rarely bars a whole dimension. Photorealistic water has a
calm case, a storm case, a shore-break case, an underwater case, a wake case —
and a reference set that only covers open ocean will hand a critic nothing the
moment a lane works on the shoreline.

So: before wave 1, list the cases the run will actually be judged on, and check
each has something to compare against. Fill the holes *then*, when it is cheap
and nothing has been built. Discovering an unbarred case mid-run costs a round
and usually produces the vague verdict that stalls a lane
(`failure-modes.md`, "Assumed-absent bar"). Write the covered and uncovered
cases into `bar/SOURCES.md` — the uncovered list is the shopping list.

### If it genuinely is not out there

Then say so *with the search attached*, and fall back deliberately: construct a
measurement that plays the same role (a number, a physical relation, a
tolerance), or generate three deliberately different candidates, have the user
pick, and use the winner as the champion the loop must beat. A self-generated
bar is weaker than an external one and you should say so — but the order
matters: it is the fallback after searching, never the first move.

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

`init` scaffolds `gauntlet/bar/SOURCES.md`: per dimension, what the bar is,
where it came from, what was searched (including empty searches), and which
cases it does and does not cover. It ships empty on purpose — an empty SOURCES
file is a visible "nobody went looking", which is exactly the state this
chapter exists to prevent. Adding a bar artifact mid-run means adding its row
here too, so the report can say what the artifact was actually held to.
