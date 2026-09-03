---
type: Technique
title: Node-graph runtime — scheduling, caching and invalidating a terrain graph
description: "Executing a terrain node graph: the scheduler and rebuilder that decide it, why early cutoff is the property that matters, and the determinism a shared cache silently assumes."
tags: [architecture, tooling, caching, evaluation, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: alacarte, tier: P, locator: "§4.1 the three schedulers — 4.1.1 topological, 4.1.2 restarting, 4.1.3 suspending; §4.2 the four rebuilders — 4.2.1 dirty bit, 4.2.2 verifying traces, 4.2.3 constructive traces, 4.2.4 deep constructive traces; §2.3 and Fig. 3 for early cutoff; §2.5 Table 1 for the classification of Make, Excel, Shake and Bazel; §5.4 for Bazel, CloudBuild, Buck and Nix, and the closing paragraph naming suspending + constructive traces" }
  - { id: adapton, tier: P, locator: "§2 Overview — recomputation driven by observation rather than by input change; §4.1 trace structure and propagation semantics" }
  - { id: acar2002, tier: P, locator: "§6 Change Propagation is Sound" }
  - { id: halide, tier: P, locator: "§4.2 Bounds Inference — required regions inferred backwards from consumers by interval analysis and composed up the pipeline; Fig. 5 for the worked tiled halo; §3.1 for the apron and the redundancy-versus-locality trade" }
  - { id: barnes2017, tier: P, locator: "§3.1 p.205 for why an apron cannot fix a global-ordered node and how a perimeter aggregate does; §3 p.203 for the three-stage structure and the single-tile residency claim; §2 p.203 for the restriction to non-divergent flow" }
  - { id: nuke_request, tier: F, locator: "the DD::Image::Iop reference for request() and _request(), and the NDK Developers Guide 'Basic Image Calls' paragraph on _request — requested regions are unioned, and a random-access node must request the input's whole bounding box" }
  - { id: barnes2016, tier: P, locator: "Abstract p.56 — the same tile-subdivision shape applied to Priority-Flood depression filling, with a fixed number of memory-access and communication events per subdivision" }
  - { id: hlsl_wg_removal, tier: F, locator: "proposals/0018-work-graphs.md — the header 'Version: SM 6.8 / Removed: SM 6.10' and the paragraph beneath it; proposals/0046-dxil110.md §'Removing Support for Node Shaders'" }
  - { id: dxc_wg_removal, tier: F, locator: "PR #8798, merged 2026-08-31 — the ASTContextHLSL.cpp comment 'available SM6.8, deprecated SM6.9, obsoleted SM6.10', the SemaHLSLDiagnoseTU.cpp guard, and the lib_6_x exemption with its sm6_10_lib_6x_no_diagnostics.hlsl test" }
  - { id: d3d_worklists, tier: F, locator: "d3d/WorkLists.md v0.851 — the Motivation section on ExecuteIndirect and PSO switching, and the closing statement that implementations are not ready and a preview is hoped for in 2027" }
  - { id: d3d12indirect, tier: F, locator: "ExecuteIndirect and the Vulkan indirect equivalents — the dispatch mechanism a GPU-resident graph still runs on in 2026" }
  - { id: haar2015, tier: F, locator: "the GPU-driven pipeline structure: persistent buffers, GPU-side culling and indirect submission" }
  - { id: wihlidal2016, tier: F, locator: "compute-shader replacement of fixed-function pipeline stages, and indirect dispatch chaining" }
  - { id: ta_graph_runtime, tier: F, locator: "§Evaluation for the demand-driven recursion; §Content-addressed caching for the recursive cacheKey and the exclusion of device; §Dirty propagation for the VALUE-versus-TOPOLOGY split" }
  - { id: simd_dispatch_drift, tier: F, locator: "the AVX512-on/AVX512-off comparison table and the paragraph beneath it giving the per-ufunc 1-ULP measurement over 10007 doubles and the droplet_erode amplification" }
---
# Node-graph runtime — scheduling, caching and invalidating a terrain graph

A tool in the Gaea / World Machine class is a node graph plus the machine that runs it. The nodes
are the subject of the rest of this skill; **this document is the machine**, and it is where a
studio actually loses days — to a rebuild that recomputes an erosion pass nobody changed, or to a
cache that serves a stale mask and produces a splatmap that is quietly wrong.

**Boundary.** This document owns evaluation, cache identity, invalidation, resolution independence
and tiling. `layering-filters-and-masks.md` owns how a filter is applied through a mask and what
that costs the runtime. `driver-fields.md` owns the non-height fields the graph carries.
`terrain-analysis-masks.md` and `flow-routing.md` own the operators themselves; this document
never restates what a node computes, only what the runtime must know about it.

## Use this

**A suspending scheduler with constructive traces** [alacarte].

That is one sentence in a vocabulary most terrain tools do not use, so unpack it:

- **Suspending scheduler** — when a node needs an input, evaluate that input *there*, suspending
  the caller, and remember what has already been built. Not a topological pre-pass.
- **Constructive traces** — after building a node, record its dependencies' hashes *and its
  resulting value*. Before building, look up whether a value produced from those same dependency
  hashes already exists; if so, take it and do no work.

**Why it wins.** These are the only two choices that give all three properties a terrain tool
needs at once — dynamic dependencies, **early cutoff**, and a cache that can be shared between
machines. [alacarte] §5.4 says so directly, closing with the observation that a suspending
scheduler combined with constructive traces was, in 2018, *"the most interesting build system as
yet unavailable"*. A terrain runtime is a small enough world to build it in.

**What it beats.** *Topological scheduling* [alacarte] §4.1.1 — a linear pre-pass, correct and
simple, but it can only extract dependencies from an applicative task, so a node whose inputs
depend on its parameters is out. *Restarting* [alacarte] §4.1.2 — build in an arbitrary order and
abort when you hit an unbuilt dependency; not minimal, because a task can do real work and then be
thrown away. *A dirty bit* [alacarte] §4.2.1 — one flag per node, propagated downstream; minimal,
but it cannot do early cutoff. *Deep constructive traces* [alacarte] §4.2.4 — the design almost
every terrain tool actually ships, and the one this document argues against below.

## The graph is a build system, and that is not an analogy

A build system takes a set of keys, a description of how each key is computed from others, and a
persistent store, and brings a requested key up to date doing as little work as possible. Replace
"key" with "node output" and every word still holds. That matters because the design space has
already been mapped, once, properly [alacarte], and terrain tools have been rediscovering corners
of it by hand.

The decomposition is the useful part. A runtime is **a scheduler crossed with a rebuilder**
[alacarte] §4: the scheduler decides *what order* to visit nodes in, the rebuilder decides
*whether a node needs to run at all*. They are independent, and almost every argument about
terrain graph performance is really an argument about one of the two with the other left implicit.

[alacarte] §2.5 Table 1 classifies four real systems on exactly the axes that matter here, and
the useful fact is that **no widely used system has all of them**:

| | Scheduler | Dependencies | Minimal | Cutoff | Cloud |
|---|---|---|---|---|---|
| Make | Topological | Static | Yes | No | No |
| Excel | Restarting | Dynamic | No | No | No |
| Shake | Suspending | Dynamic | Yes | Yes | No |
| Bazel | Restarting | Dynamic\* | No | Yes | Yes |

\* [alacarte]'s footnote: user-defined Bazel rules cannot have dynamic dependencies.

Make is minimal but static and has no cutoff. Excel is not even minimal. Shake gets minimality and
cutoff but cannot share. Bazel shares and cuts off but is not minimal. The empty cell in every row
is what a terrain tool is trying to fill.

## The scheduler: three options, and the terrain answer

| Scheduler | What it does | Why it fails here |
|---|---|---|
| **Topological** [alacarte] §4.1.1 | Pre-compute a linear order, then walk it | Requires static dependencies. A node whose input set depends on its own parameters — a "loop this subgraph N times", a mask registry, a switch between algorithm variants — cannot be expressed |
| **Restarting** [alacarte] §4.1.2 | Build in any order; abort and retry when an input turns out to be stale | Not minimal: a partially-completed erosion pass thrown away is minutes, not milliseconds |
| **Suspending** [alacarte] §4.1.3 | Evaluate an input at the point of demand, suspending the caller | **Use this.** Minimal, and it handles dynamic dependencies |

Suspending is also what the in-repo prior art arrived at independently: [ta_graph_runtime]'s
evaluation is a demand-driven recursion from the requested outputs, memoised, with cycles excluded
by construction. That is a suspending scheduler written without the name.

⚠️ **A genuine cycle is not a scheduling problem, and must not be solved in the scheduler.** Vegetation
and erosion that feed each other are a fixed-iteration outer loop around a subgraph, expressed as a
composite node, so the DAG invariant survives [ta_graph_runtime]. A runtime that permits cycles in
the graph proper has given up both a topological order and a cache key.

## Executing it on the GPU, and the 2026 answer

The scheduler above says *what order*; this says *what runs it*. For a content-generation graph in
2026 the honest answer is that **the 2016 answer still holds**: compute kernels over persistent
buffers, dispatched indirectly, with bindless resources and a better front end
[d3d12indirect] [haar2015] [wihlidal2016]. A document claiming novelty here would be inventing it.

That is worth saying because there *was* a genuinely different mechanism — GPU-scheduled recursive
node execution, where the GPU itself expands and schedules downstream work — and it has just been
withdrawn. **Work graphs shipped in Shader Model 6.8 and are removed as of SM 6.10.**
[hlsl_wg_removal] is unambiguous: *"Work Graphs was introduced in Shader Model 6.8, and has been
removed effective Shader Model 6.10. Driver support for Work Graphs is still available and
supported on many devices."* The compiler change records the lifecycle exactly — *"available SM6.8,
deprecated SM6.9, obsoleted SM6.10"* [dxc_wg_removal].

⚠️ **A ceiling, not a deletion.** SM 6.8 and 6.9 still compile and run, drivers still support it,
and `lib_6_x` targets are explicitly exempted from the new diagnostic [dxc_wg_removal]. Existing
work-graph code does not stop working; what stops is targeting it from 6.10 onward. So the
practical rule is narrow and clear: **do not architect a new terrain runtime on work graphs**, and
do not rewrite one that already uses them.

Its nearest successor is early. [d3d_worklists] is motivated by `ExecuteIndirect`'s inability to
switch PSOs from the GPU timeline and describes itself as an `ExecuteIndirect` analog; it says
plainly that "implementations are not ready" and hopes for a preview "some time in 2027". It does
not claim to replace work graphs — that framing is press narrative, not spec.

⚠️ **How this was established, because the method matters more than the conclusion.** The obvious
primary source is the `WorkGraphs.md` spec, and it contains **no deprecation language at all** —
its `## Shader target` even says node shaders target "lib_6_8 **or above**", an open floor. That
reads as evidence the feature is alive. It is not: that file's last edit was 2026-02-04 and the
decision landed in August 2026 in two different repositories. **Absence of a statement in a spec is
not evidence of absence when the spec is stale** — check the file's date before drawing an
inference from its silence, and prefer the repository that carries the change over the one that
carries the description.

## The rebuilder: where the days actually go

This is the consequential choice, and the one terrain tools get wrong.

The design almost every tool ships is a **recursive content hash**: a node's cache key is a hash of
its type and version, its canonicalised parameters, and *the keys of its upstream nodes*
[ta_graph_runtime]. The recursion is the appeal — the key of a node embeds its entire upstream
cone, so a change anywhere invalidates exactly the downstream cone and nothing else. Dirty
propagation stops being a mechanism you can get wrong and becomes a consequence of the key.

That is true. It is also a **deep constructive trace** [alacarte] §4.2.4, and it buys two problems
that the design's own framing hides.

### It cannot do early cutoff

**Early cutoff** is the property that if a node recomputes to the *same value*, its dependents do
not rerun [alacarte] §2.3, Fig. 3. It is the difference between a graph that feels responsive and
one that does not, and terrain is close to the worst case for lacking it, because the expensive
nodes sit downstream of the cheap ones.

[alacarte] §4.2.4 is explicit: *"A downside of deep constructive traces is that they cannot support
early cutoff, other than at n levels of dependencies."* The reason is structural. The key is
computed from **inputs**, so it changes whenever an input changes — whether or not the output did.

Concretely: nudge a parameter whose effect is clamped away, re-roll a seed on a node whose result
is masked to zero downstream, or change a value in the eighth decimal place of a quantised
parameter. The upstream key changes, so every downstream key changes, so the erosion pass reruns.
Nothing about the terrain changed.

**Verifying traces** [alacarte] §4.2.2 and **constructive traces** [alacarte] §4.2.3 both support
cutoff, because they compare the *result*: after building a node, record the hash of what it
produced, and if that hash is unchanged, stop. [alacarte] §4.2.2 states the property for the whole
family — all traces except deep ones support early cutoff.

The fix is one comparison, and it is not free: you must actually hash the output field, which for a
4k float heightfield is real work. That is the crossover, and it is stated below.

### It silently assumes determinism

The second problem is worse because it produces wrong results rather than slow ones.

[alacarte] §4.2.4 again: *"When n ≥ 2, deep constructive traces require the tasks to be
deterministic, as otherwise it is possible to violate correctness."* A key built from input hashes
asserts that those inputs *determine* the output. If the operation is not deterministic, the cache
holds one of several possible results and will hand it back as though it were the only one.

Terrain operations are not obviously deterministic, and one case is measured. [ta_graph_runtime]
excludes the execution device from the cache key and calls that "a promise that CPU and GPU produce
equivalent results". [simd_dispatch_drift] measures that promise failing on **one CPU**, between two
SIMD dispatch regimes of the same numpy build:

```
                    AVX512 on    AVX512 off
canyon relief         268.99       270.71
canyon pit-storage   5.2169e6     4.1597e6      <- 25% apart
badlands relief       260.52       258.63
```

The mechanism is a 1-ULP difference: transcendental ufunc loops (`pow`, `exp`, `log1p`, `tan`,
`arctan`) are dispatched by SIMD level and differ by exactly one unit in the last place, while
`add`, `mul`, `sqrt`, `sin` and `hypot` are bit-identical. Droplet erosion amplifies that by ~1e14,
because a steepest-descent step is a **discrete choice** and a tie flips [simd_dispatch_drift].

⚠️ **This is not a rounding curiosity, it is a cache-correctness argument.** A local cache on one
machine never notices. A shared cache across a studio serves another machine's result, and if that
machine dispatched differently the terrain is different. Either put the arithmetic regime in the
key, or make the promise real and test it — and note that "CPU versus GPU" is the easy version of
this problem; the measured failure was two code paths inside one CPU.

## Determinism is a runtime property, not a node property

The practical rules that follow, and none of them are optional if the cache is shared:

- **Quantise float parameters before hashing.** A UI slider otherwise generates thousands of
  never-reused entries per drag [ta_graph_runtime].
- **Hash the effective seed**, so re-rolling a stochastic node invalidates that node's cone and
  nothing else [ta_graph_runtime].
- **Anything that changes the arithmetic belongs in the key** — the dispatch regime, the device,
  the fast-math flags, the library version — unless you are prepared to test the equivalence you
  are asserting.
- **Iteration order counts as arithmetic.** A parallel reduction that sums in completion order is
  not deterministic, and floating-point addition is not associative.

## Demand-driven, and the memory it costs

A suspending scheduler is demand-driven: nothing is computed until something asks for it. That is
also [adapton]'s position — recomputation is driven by *observation* rather than by input change
(§2), with change propagation proved sound in the line's original form [acar2002] §6.

The cost is that a demand-driven runtime holds live intermediate values, and terrain intermediates
are field buffers of megabytes each. The mitigation is eviction with re-derivation: cache entries
are LRU by *bytes*, not by count, with the currently-viewed node's upstream cone pinned, and an
evicted entry is simply recomputed [ta_graph_runtime]. This is only safe because evaluation is
pure — which is the same assumption the cache key already makes.

## The crossover: an edit is not a build

The same graph is evaluated under two budgets, and the right answers differ. This is the general
rule in `simulation-time-budget.md` applied to authoring.

| | **Interactive edit** | **Farm build** |
|---|---|---|
| Wanted | Latency on one parameter | Throughput on the whole graph |
| Scheduler | Suspending, on the preview tier only | Suspending; parallelism across independent cones |
| Rebuilder | **Verifying traces** — hash the result, get cutoff, no value storage | **Constructive traces** — store values so other machines skip the work |
| Output hashing | Worth it: an avoided erosion pass costs seconds, a 4k hash costs milliseconds | Worth it: the hash is a rounding error against a farm job |
| Cheap nodes | **Do not hash.** A node that costs less than hashing its output should just rerun | Same |

That last row is the honest limit of early cutoff. Hashing a 4k float field is not free, and for a
node cheaper than its own output hash the comparison is pure overhead. The rule that follows:
**apply cutoff where a node is expensive and its output is stable** — erosion, flow accumulation,
long-baseline occlusion — and skip it on arithmetic combinators.

⚠️ **No millisecond figures are given here, deliberately.** They would depend on grid size, memory
bandwidth and hash function, and this skill has no benchmark to cite; writing one would be a `?`
wearing a `P`'s confidence. What is safe to say is the *shape*: hash cost is linear in field size
and independent of node cost, so the crossover is a property of the node, not of the machine.

## Two invalidations, not one

A parameter change and a graph edit are different events and cost different amounts
[ta_graph_runtime]. A **value** change reuses the execution plan — same nodes, same order, same
buffer allocations — and only reruns kernels. A **topology** change (rewiring, an octave count, an
enum that switches algorithm variant) must re-plan.

This distinction is most of the difference between a parameter drag that holds 60 fps and one that
stutters, because plan construction and buffer allocation are where the frame time hides. Debounce
the full-quality pass until the drag ends; re-evaluate at the current preview tier while it runs.

## Resolution independence

A preview at 512 and a build at 4096 must be the *same terrain at different sampling densities*,
not two different terrains. The runtime half of that rule is short and absolute:

**A parameter in cells is a bug; a parameter in world units is a parameter.** A 5-cell blur radius
is a different physical filter at every resolution. A 50-metre blur radius is the same filter
sampled differently. The runtime cannot fix a node that stores its radius in cells — it can only
refuse to have one.

The consequences for this document are the cache key and the plan: **resolution belongs in the
key** [ta_graph_runtime], so the 512 preview and the 4k build are different entries and neither
can serve the other. What must *not* be in the key is anything that would make two machines
computing the same terrain disagree — see determinism above.

`layering-filters-and-masks.md` carries the operator-side rule, which is where the failure is
usually visible.

## Tiling, and the operators that refuse it

Evaluating a graph tile by tile is what makes an out-of-memory build possible. For a **local**
operator a tile plus a halo suffices — the halo being the operator's support radius — and the
required region composes back up the pipeline. That composition is mechanical, not a heuristic:
[halide] §4.2 infers it by "interval analysis of the expressions in the caller which index that
dimension, given the previously computed bounds of all downstream functions", and its Fig. 5
carries the worked case where a consumer reading `blur_x(x, y-1)` mechanically produces a `-1` in
the producer's required bounds.

A second rule applies once a node has more than one consumer, and it is the one people forget:
**every region requested of an input is unioned**, and the union is what gets computed and cached
[nuke_request]. Two downstream nodes each asking for half a tile cost one evaluation of their
union, not two of a half — which is why a single node with random access to its input, which must
request the whole bounding box, silently defeats tiling for everything upstream of it.

**Some terrain operators are not local at any radius.** Flow accumulation is the example
(`flow-routing.md`): drainage area is a **global, topologically ordered** quantity, and a tile's
upstream cone can reach the far edge of the world. [barnes2017] §3.1 states the mechanism exactly —
"the fundamental problem each tile encounters is that it does not know how much flow it will
receive from each neighbouring tile", so "every cell along every flow path is offset from its true
value by an unknown amount".

⚠️ **That does not mean such nodes cannot tile, and assuming so is a real and common error.** The
same sentence continues: "this information can be calculated by considering in aggregate the
perimeters of all the tiles." [barnes2017] computes flow accumulation **exactly** over two trillion
cells with, in the limit, "only the producer's information and a single tile" resident. The fix is
not a bigger apron — no apron works — it is a **different contract**: a per-tile pass, an
O(perimeter) boundary digest, one global reduce over the digests, then a per-tile offset pass.
[barnes2016] applies the same three-stage shape to depression filling, which makes it a pattern
rather than one algorithm's trick.

So a tiled runtime classifies its nodes by **which contract they need**, not by whether they tile:

| Class | Contract | Examples |
|---|---|---|
| **Local** | Tile plus a halo, composed up the chain [halide] | Blur, slope, curvature, most filters |
| **Global-reduce** | One whole-domain reduction, then tile freely | Min/max normalisation, histogram equalisation |
| **Global-ordered** | Boundary-summary: per-tile pass → O(perimeter) digest → global reduce → per-tile offset [barnes2017] | Flow accumulation, depression filling [barnes2016] |

⚠️ **The receiver rule decides whether the third row is even available.** [barnes2017] §2 restricts
itself to non-divergent flow because "the one-to-many property of divergent flows makes developing
divide-and-conquer approaches difficult". Single-receiver D8 decomposes; multi-receiver MFD and D∞
resist the same decomposition. So the network-versus-field choice in `flow-routing.md` is *also* a
tiling decision, and picking MFD for a field may cost you out-of-core evaluation of that branch.

⚠️ **Do not over-read this into "erosion tiles".** [barnes2017] and [barnes2016] operate on a
**static** DEM. An erosion loop rebuilds the flow DAG every step, so the boundary digest would have
to be recomputed and re-reduced per iteration, and neither paper measures that. The honest claim is
that a *single* global-ordered pass tiles exactly; an iterated one is an open question this skill
does not have a source for.

A node's class is part of its description, alongside its type and its parameters, and the planner
needs it before it can decide anything. A runtime that discovers the class at evaluation time has
already allocated the wrong buffers.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| A parameter nudge reruns an erosion pass that produces identical output | Deep constructive trace: the key is over inputs, so it changes even when the value does not [alacarte] §4.2.4 | Compare the output hash — verifying or constructive traces [alacarte] §4.2.2 |
| Terrain differs between two machines from the same graph and the same seed | The cache key asserts determinism the operations do not have [alacarte] §4.2.4; measured across SIMD regimes on one CPU [simd_dispatch_drift] | Put the arithmetic regime in the key, or test the equivalence being promised |
| The cache fills with thousands of entries during a slider drag | Float parameters hashed unquantised [ta_graph_runtime] | Quantise before hashing |
| Parameter drag holds 60 fps, then stutters when one particular value changes | That value is a topology change, not a value change — it re-plans [ta_graph_runtime] | Classify parameters VALUE vs TOPOLOGY; debounce the re-plan |
| Adding cutoff made the graph slower | Output hashing applied to nodes cheaper than their own hash | Apply cutoff only where the node is expensive and its output stable |
| The 512 preview does not match the 4k build | A parameter stored in cells rather than world units | Store radii and lengths in world units; resolution stays in the key |
| Tiled build has a seam only in some places | A node's halo is smaller than its true support | Size the halo from the operator's support radius, summed along the chain |
| Tiled build's rivers stop at tile boundaries | Flow accumulation run per tile — it is global-ordered, and no halo fixes it (`flow-routing.md`) | Classify the node as global-ordered; route on the whole domain |
| Memory grows until the build dies | Demand-driven evaluation holding every intermediate | LRU by bytes with the viewed cone pinned; evicted entries re-derive [ta_graph_runtime] |
