---
type: Technique
title: Layering, filters and masks — composition and what it costs the runtime
description: "Applying a filter through a mask: why masking is a post-process rather than a domain restriction, exactly where that equivalence stops holding, and the undeclared input sets that break a cache."
tags: [architecture, tooling, masks, layering, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: gaea_masks, tier: F, locator: "§'What is a Mask?' for the greyscale-weight definition; §'Creating and Applying Masks → Direct Masking' and '→ Post-Masking' for the Mask node, the claim of no difference in results, and the rebuild-versus-extremely-fast comparison" }
  - { id: gaea_accumulator, tier: F, locator: "the Accumulator node reference — the Type enum and Restrict to Group scoping, the sentence 'The Accumulator will only add nodes that have been built', and the paragraph instructing the user to wire an edge purely to force ordering" }
  - { id: gaea_mixer, tier: F, locator: "the Layering Textures page — Mixer's layer list, its built-in height and slope masks, and the Add Input command" }
  - { id: houdini_hdk, tier: F, locator: "HDK 'Cooking' — the OP_Node::addExtraInput() requirement for data cooked 'via some other means', and the statement that extra inputs are cleared as soon as they are traversed on dirty propagation, so they must be re-registered on every cook" }
  - { id: nuke_request, tier: F, locator: "DD::Image::Iop request() / _request() — every region requested of an input is unioned, and a random-access node must request the input's whole bounding box" }
  - { id: ta_ops_filters, tier: F, locator: "§'Placement & masking' for apply_masked, the metres-not-cells rule and the never-ship-a-binary-mask rule; §'Place before you sample, not after' for the coordinate-versus-raster transform measurement and the rule that a percentage is quoted with its metric" }
  - { id: alacarte, tier: P, locator: "§2.3 and Fig. 3 for early cutoff — the property this document buys by graph shape rather than by the rebuilder" }
---
# Layering, filters and masks — composition and what it costs the runtime

Masking is how a procedural terrain becomes art-directable: erode this valley, leave that plateau.
It looks like a UI convenience and it is actually a decision about **where the mask sits in the
graph**, which decides what your cache can reuse and what a mask tweak costs.

⚠️ **Everything on this axis rests on `F` sources.** There is no canonical paper for how a tool
composes layers, filters and masks; standard practice is vendor documentation, and the tiers below
say so. They are evidence about what shipping tools chose, never about what is correct.

**Boundary.** `terrain-analysis-masks.md` owns how a mask is *computed* — slope, curvature,
occlusion, wetness — and the selector stack that turns masks into materials. This document owns how
a mask is *applied*: the algebra of a masked operator, where it belongs in the graph, and the
runtime consequences. `node-graph-runtime.md` owns the scheduler and the cache itself.

## Use this

**Apply masks as a separate downstream node, not as a parameter on the operator.**

```
masked_f(h, m) = h + (f(h) - h) * m          # run f everywhere, then select
```

**Why it wins.** It is not about the picture — it is about the cache key. When the mask is an input
to the expensive node, changing the mask changes that node's key and the erosion reruns. When the
mask is a separate downstream node, changing it invalidates only the cheap compositing node and the
expensive result is reused. [gaea_masks] states both halves outright: there is **"no difference in
results between the Mask port on a node and the Mask node"**, and the reason to prefer the latter is
that **"when a node is masked directly, a change to the mask will force a rebuild of the entire
node. A Mask node, however, adds masking as a post-process and is extremely fast."**

That is **early cutoff** [alacarte] §2.3 obtained by *graph shape* rather than by the rebuilder. If
your runtime ships the recursive-hash design that cannot do cutoff (`node-graph-runtime.md`), this
is how you buy the case that matters anyway: factor the mask out of the operator.

**What it beats.** *A mask input port on every operator* — the same result, and every mask tweak
pays for the operator. *Restricting the operator's domain to the mask* — intuitively the "real"
masking, and for a transport operator it gives a **different answer**, quantified below. *Painting
the mask into the heightfield before the operator* — destroys the mask as a separate object, so
nothing downstream can reuse or invert it.

## What a masked operator actually is

The lerp above is not an approximation of masking; in a tool like Gaea it *is* masking. The
operator runs over the whole domain and the mask only chooses between the before and after fields
[gaea_masks]. Two consequences people find surprising:

- **The mask does not save any work in the operator.** A mask covering 5% of the map does not make
  erosion 20× cheaper; erosion still runs everywhere. What the mask saves is *downstream
  invalidation*, which is a different and usually larger win.
- **A masked node's cost is independent of the mask.** So there is no reason to fear a complicated
  mask, and no point optimising one for speed.

### The equivalence holds for pointwise operators, and stops for transport

⚠️ [gaea_masks]'s "no difference in results" is a statement about **Gaea's implementation** — that
its mask port is implemented as the post-blend — not a general theorem. `lerp(h, f(h), m)` equals
"`f` restricted to `m`" only when `f` is **pointwise**. An operator that *moves material across the
mask boundary* gives two different answers, and the difference grows with iteration count.

Measured on a 128² field: `default_rng(4)` uniform noise smoothed by 30 box passes and scaled to
relief 17.47, a binary mask over the left half, and a thermal-style transport step that moves
`0.15·Δh` to any neighbour more than 0.5 below. "Domain-restricted" here means the exterior is
frozen after every step. Percentages are of relief; "cells differing" uses a 1e-9 threshold:

| Operator | Iterations | max abs difference | as % of relief | cells differing |
|---|---|---|---|---|
| Pointwise (`h·0.5 + 10`) | — | **0.000000000** | 0.0000% | 0 |

| Transport (thermal-style) | 1 | **0.000000000** | 0.0000% | 0 |
| Transport | 5 | 0.206 | 1.18% | 257 |
| Transport | 20 | 0.664 | 3.80% | 517 |
| Transport | 80 | 1.162 | 6.65% | 775 |

At 80 iterations **45% of the total difference lies within four cells of the mask boundary**, which
is 6% of the domain. So the post-process form matched domain restriction exactly for the pointwise
operator on this field, and diverges at the mask edge as transport accumulates.

⚠️ **Three honest qualifications, because this measurement is easy to over-read.**

1. **"Exact" is algebraic, not bitwise-guaranteed.** `h + (f(h) − h)·m` is exactly `f(h)` where
   `m = 1` in real arithmetic, and IEEE-754 rounding can still separate them; it happened not to on
   this field. Given that this corpus elsewhere argues one ULP can matter, do not read the zero as
   a guarantee.
2. **The 1-iteration row is nearly a tautology.** With a binary mask, one step of *any* operator
   agrees, because nothing has yet crossed the boundary to be frozen.
3. **Freezing the exterior is not the only way to restrict a domain, and it is the pessimal one.**
   It imposes a no-flux wall. A runtime would instead evaluate on the mask's bounding box dilated by
   the operator's support radius and then post-blend — which is *the same computation* as the
   post-process form, just cheaper, and is where a masked expensive operator should actually go.

### It does not conserve mass, and that is the defect that matters

The divergence above is an edge effect. This one is not. `h + (f(h) − h)·m` **scales a transport
result**, so material the operator carried across the mask boundary is simply deleted.

Measured on the same field: the transport operator conserves mass to **1.2e-10**, while the
post-masked result changes total mass by **17.6 units** — 0.37% of all material moved at 20
iterations, settling to 0.22% by 200 as the relaxation reaches its fixed point. A soft mask does
not rescue it (0.12–0.19%). It plateaus here rather than growing without bound, because this
operator stops moving material; an operator that does not reach a fixed point has no such ceiling.

**Why it matters beyond tidiness:** `terrain-analysis-masks.md` uses deposition to drive sediment
materials, and a deposition field that quietly loses a fraction of a percent of its mass at every
mask edge is wrong in exactly the places an artist has been directing. If you need conservation,
restrict the domain properly — bounding box plus support radius — rather than scaling the result.

**What to do about it.** Nothing, usually — the post-process form is the one the tool defines as
correct, and the divergence is an edge effect. But do not claim the two are interchangeable for a
long-running simulation, and if you need a genuinely domain-restricted simulation, say so and pay
for it: that is a different node, not a mask.

## The layer stack lives inside the DAG

A layer stack — ordered layers, each with a mask and a blend mode — and a node graph are usually
presented as rival paradigms. In practice a tool ships both, with the stack **as a node**.
[gaea_mixer]'s Mixer holds a list of colour layers with built-in height and slope masks plus custom
mask inputs, and grows input ports on demand.

This is the right factoring, and the reason is cache identity. A stack is a fold — a chain of
binary blends — so as a single node it has one key covering all its layers, and editing layer 7
invalidates the whole stack. Expanded into the graph as N binary blends, editing layer 7 invalidates
only layers 7..N. **Use the stack node for authoring convenience where layers are small and cheap;
expand it into explicit nodes when a layer is expensive.** The stack is sugar over a fold, and the
runtime should be able to see through it.

## The undeclared input set, and why it silently breaks the cache

The strongest lesson on this axis comes from a node that exists in a shipping tool and documents its
own failure.

[gaea_accumulator] is a registry: a node that collects every snow mask, water mask or debris mask in
the graph so an artist need not wire N producers to M consumers. It is declared "a special type of standalone
Generator node" — the class of node that produces rather than transforms — while its output depends
on every matching node in the graph. It *does* expose an Accumulator Input, but only for the
ordering workaround below; nothing about the masks it collects arrives through it. Its
dependencies are expressed **intensionally**, by a `Type` predicate and a `Restrict to Group` scope,
rather than **extensionally**, by wires.

A cache key is built by walking a node's declared inputs. A node whose real inputs are not edges
therefore has a key that does not change when its real inputs do. **Adding a simulation does not
change the accumulator's key, so every downstream consumer serves a stale entry that is missing the
new mask.** Nothing crashes. The splatmap is quietly wrong, and stays wrong until something
unrelated evicts the entry.

The vendor documents the symptom exactly: **"The Accumulator will only add nodes that have been
built."** An intensional dependency the runtime cannot see cannot be used to *schedule*, so the node
returns whatever happened to be evaluated already. And the documented workaround is to have the
**user draw an edge whose only purpose is ordering** — a data wire carrying no data, existing purely
as a scheduling barrier [gaea_accumulator].

That is the whole lesson in one sentence: *if a node's real inputs are not edges, someone will end
up drawing the edges by hand, and getting them wrong.*

**The fix is not to ban the pattern — it is to register the discovered dependencies.**
[houdini_hdk] states the rule: a node that cooks another node's data "via some other means" **must**
call `OP_Node::addExtraInput()`, and must do it on *every* cook, because extra inputs are cleared as
soon as dirty propagation traverses them. The dependency graph is allowed to change on every cook;
what is not allowed is for it to be implicit. Resolve the query at plan time, turn it into explicit
edges, and fold the resolved set into the key:

```
key(accumulator) += hash(sorted (producerNodeId, outPortName) for each collected mask))
```

⚠️ **This is a house style, not one bad node.** [gaea_masks]'s own Mask node infers its "before"
input topologically — walking the graph to find it, with a second port to override the guess when it
is wrong. Convenience nodes that discover their inputs are attractive to build and each one is a
hole in the cache.

## Rules that decide whether a mask survives contact with a build

- **Never ship a binary mask** [ta_ops_filters]. A hard 0/1 edge prints its staircase through every
  downstream blend, and the artefact is blamed on the blend rather than the mask. Clamp the soft
  edge to at least one cell even when the falloff parameter is zero.
- **Author placements in metres, never cells** [ta_ops_filters]. A layout keyed to cell indices
  slides across the terrain the moment build resolution changes — the resolution rule from
  `node-graph-runtime.md`, in the place it usually bites.
- **A mask is also a shape.** The same disc that confines an erosion can be treated as a heightfield
  and eroded into a landform [ta_ops_filters]. That dual use is why placement belongs in the graph
  rather than in a brush tool.

## Place before you sample, not after

There are two ways to move a feature and only one is free [ta_ops_filters]. A **coordinate
transform** evaluates the generator at shifted coordinates — the same function sampled elsewhere, so
it moves the feature exactly. A **raster transform** moves the output, and bilinear resampling is a
low-pass filter, so detail is lost and the losses compound along a chain.

Measured on 6-octave fBm: one raster move loses ~29% of fine detail and four chained moves ~57%,
scored as mean |laplacian| [ta_ops_filters].

⚠️ **Always quote the metric with the number.** The same experiment scored on high-frequency band
energy reads ~9.8% and ~27.2% instead. Neither is wrong and a bare percentage is meaningless
[ta_ops_filters]. That chapter records two of its own measurement errors in place — a figure with no
provenance, and an extreme-value statistic standing in for a spread — which is a better argument for
the rule than the rule itself.

Use a raster transform only for a field you cannot re-evaluate: an imported DEM, or the output of a
simulation.

## Masks and tiling

A masked operator's required region is not the operator's alone. Every region requested of an input
is **unioned**, and the union is what gets computed and cached [nuke_request] — so a masked filter
pulls on both its source and its mask, and the tile it needs is the union of the two requests.

Two practical consequences:

- **A mask with detail near a tile boundary widens the halo** even when the filter's own support is
  small, which is why a tiled build can show a seam only in some places.
- **A node with random access to its input must request the whole bounding box** [nuke_request],
  which defeats tiling for everything upstream of it. One such node in a chain is enough.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Every mask tweak reruns the erosion | The mask is an input port on the expensive node, so it is in that node's key | Move masking to a downstream node [gaea_masks] |
| A masked simulation looks wrong at the mask edge, and worse the longer it runs | Post-process masking is exact only for pointwise operators; transport crosses the boundary — 6.65% of relief at 80 iterations, 45% of it within four cells of the edge | Accept the edge effect, or use a genuinely domain-restricted node and pay for it |
| Adding a new simulation leaves the splatmap missing its mask, with no error | A registry node's inputs are intensional, so its key did not change [gaea_accumulator] | Resolve the query at plan time into explicit edges; fold the resolved set into the key [houdini_hdk] |
| A registry node returns a partial result that changes between runs | "The Accumulator will only add nodes that have been built" — the runtime cannot schedule what it cannot see [gaea_accumulator] | Register discovered dependencies on every cook [houdini_hdk], rather than asking the user to wire a fake ordering edge |
| Editing one layer of a stack invalidates all of them | The stack is one node, so it has one key | Expand the stack into explicit binary blends where layers are expensive [gaea_mixer] |
| A staircase appears in a blend that has no hard edge of its own | A binary mask upstream [ta_ops_filters] | Clamp the mask's soft edge to at least one cell |
| A layout drifts across the terrain between preview and build | Placement authored in cells rather than metres [ta_ops_filters] | Author in world units |
| Detail softens each time a feature is repositioned | Raster transform instead of coordinate transform; bilinear resampling is a low-pass and the losses compound [ta_ops_filters] | Transform the generator's coordinates, not its output |
| Tiled build seams appear only where the mask has detail | The halo was sized from the filter's support, ignoring the mask's contribution to the union [nuke_request] | Size the halo from the union of all requested regions |
