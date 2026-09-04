---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Reference
title: Graph Runtime
description: "The node graph as an executable object: evaluation order, the resolution pyramid, memory and scheduling."
tags: [graph, runtime, scheduling]
status: stable
generated: { by: process:claude-code, at: 2026-07-30T20:39:48Z }
# --- end okf v0.2 ----------------------------------------------------
---
# Graph Runtime

The substrate layer of a terrain tool: what a node *is*, what a parameter *is*, and how
evaluation, caching and invalidation work. Everything Gaea, World Machine and Houdini's
heightfield SOPs have in common lives here; everything they differ on (UI, presets, branding)
deliberately does not.

Contents: [The node model](#the-node-model) · [The parameter model](#the-parameter-model) ·
[Parameter semantics](#parameter-semantics) · [Evaluation](#evaluation) ·
[Numerical contracts](#numerical-contracts) ·
[Content-addressed caching](#content-addressed-caching) · [Dirty propagation](#dirty-propagation) ·
[Preview & the resolution pyramid](#preview--the-resolution-pyramid) ·
[Region invalidation](#region-invalidation) · [Memory & scheduling](#memory--scheduling) ·
[Serialisation](#serialisation)

## The node model

A node is a **pure function from (parameters, inputs, context) to outputs**, plus metadata.
Purity is not a style preference — it is the property that makes caching, preview, undo,
distribution and determinism possible. Every capability of the runtime traces back to it.

```
NodeDesc:
    typeId          stable string, versioned: "erosion.pipe/2"
    inPorts[]       (name, FieldType, required | optional, default)
    outPorts[]      (name, FieldType)
    params[]        ParamDesc — see below
    flags           DETERMINISTIC | STOCHASTIC (takes seed)
                    LOCAL | NEIGHBOURHOOD(radius) | GLOBAL      ← the tiling contract
                    RESOLUTION_INVARIANT | RESOLUTION_BOUND     ← the preview contract
                    GPU_NATIVE | CPU_ONLY | EITHER

NodeInstance:
    id              stable uuid — survives rename, reorder, copy/paste
    desc            → NodeDesc
    paramValues     the record, all in world units
    seedOffset      per-instance; effective seed = hash(rootSeed, id, seedOffset)

EvalContext:                       # everything an evaluation depends on that isn't a port
    worldRegion     (origin, extent) in metres
    resolution      cells
    quality         preview tier (see pyramid)
    rootSeed
    device          CPU | GPU
```

Two flags carry the whole architecture and must be honest:

**LOCAL / NEIGHBOURHOOD(r) / GLOBAL** is the node's declaration of how far information travels,
and it is what the scheduler uses to decide whether a node can be tiled and with what apron
(`08`). A per-cell remap is LOCAL. A blur is NEIGHBOURHOOD(3σ). Droplet erosion is
NEIGHBOURHOOD(maxLifetime). **Flow accumulation and stream power are GLOBAL** — they cannot be
tiled, full stop, and a runtime that lets a GLOBAL node silently run per-tile has shipped the
seam bug as a feature. The flag makes the Legal Order's hardest law mechanical.

**RESOLUTION_INVARIANT / RESOLUTION_BOUND** is the node's declaration of whether the same
world region at a different resolution gives the same landscape (plus/minus detail). Noise in
world units: invariant. Thermal run to convergence: invariant. **Droplet erosion with a fixed
droplet count: bound** — the look changes with resolution. This flag is what makes preview
honest (below).

## The parameter model

**Parameters are data, not code.** A parameter is a typed, unit-carrying, range-constrained,
serialisable value. That single decision is what makes presets, undo, interpolation between
states, exposure to a macro/tool interface, optimisation loops, and automated testing all fall
out for free. Any parameter that exists only as a constant in a kernel is a parameter the tool
above the substrate cannot see.

```
ParamDesc:
    name            stable identifier ("talusAngle", not "p3")
    type            float | int | bool | enum | curve | gradient(colour ramp)
                  | vec2 | seed | fieldRef(FieldType)          # ← param-as-input, see below
    unit            m | m² | deg | tan | m/yr | 1/yr | cells⚠ | ratio | none
    range           (min, max)  hard;  (softMin, softMax)  UI hint
    default         a value that produces a sane result on the validation-suite cone
    invalidates     VALUE | TOPOLOGY      # does changing it just recompute, or restructure?
    interpolable    bool                  # can it be animated / lerped between presets?
```

Rules that keep the record honest:

- **Every spatial parameter is in world units.** This is the SKILL.md invariant made
  structural: the unit lives in the descriptor, the runtime converts to cells at dispatch time
  (`cells = metres / ctx.cellSize`). A parameter whose unit is honestly `cells` (marked ⚠) is
  a declared resolution-dependence — allowed, but it forces the node's RESOLUTION_BOUND flag.
  The type system catches at registration what code review would have to catch by eye.
- **`seed` is a type, not an int.** The runtime derives effective seeds
  (`hash(rootSeed, nodeId, seedOffset)`) so re-rolling one node never disturbs another, and a
  graph is reproducible from `rootSeed` alone. No node ever calls a global RNG.
- **`curve` and `gradient` are first-class.** Half of terrain authoring is remap curves
  (`10`). If curves aren't parameters, they end up as baked LUT inputs and stop being
  preset-able.
- **`fieldRef` makes "parameter vs input" a non-question.** Talus angle is a float — until
  the user wants it spatially varying (`05`, `11`). Declare scalar params as promotable to a
  field input; the runtime presents it as a param until something is wired in. This is the
  single most common node-library refactor, so design it in.

## Parameter semantics

The descriptor says what a parameter *is*; these conventions say what it *means*. They're what
make two hundred nodes feel like one tool.

- **Strength/amount is [0,1] and means `lerp(input, fullEffect, amount)`** — an effect mask's
  scalar twin (SKILL.md, mask semantics). Not a multiplier with an arbitrary ceiling.
- **Scale parameters are wavelengths in metres**, not frequencies. Artists think in "features
  about 300 m across", never in cycles per metre. Store wavelength, invert at dispatch.
- **Iteration counts are a smell.** Where convergence exists (thermal `05`, stream power to
  equilibrium `04`), expose *the physical target* (talus angle, relief) and iterate until
  converged; the count is then an internal budget, not a knob. Where the count genuinely is
  the look (droplet passes), it's RESOLUTION_BOUND and says so.
- **Ranges are part of correctness.** The pipe model's Δt has a CFL ceiling (`04`); encode it
  as the hard max rather than letting the user discover instability empirically. When a valid
  range depends on another parameter or on cellSize, validate at dispatch and clamp loudly.

## Evaluation

The graph is a DAG of instances. Evaluation is demand-driven from requested outputs:

```
evaluate(node, ctx):
    key = cacheKey(node, ctx)                    # below
    if cache.has(key): return cache.get(key)

    ins = [evaluate(upstream(port), ctx) for port in node.inPorts]

    ctx' = ctx adjusted for node:                # e.g. GLOBAL node forces full-domain region
    out = node.desc.fn(node.paramValues, ins, ctx')

    validate(out)                                # NaN/Inf sweep, range asserts — validation
    cache.put(key, out)                          # suite (09) as a runtime option, not just CI
    return out
```

Topological order, memoised, no cycles — with one exception: the vegetation–erosion coupling
(`13`) is a genuine cycle and is handled as a **fixed-iteration outer loop around a subgraph**,
never as a graph cycle. The runtime supports "loop this subgraph N times" as a composite node;
the DAG invariant survives.

## Numerical contracts

`validate(out)` above is the hook; this is what it enforces. A node that is individually correct
can still emit garbage the moment it is wired to another one, and combined **erosion** nodes are
where it shows up most: the reported symptom is almost always isolated spikes, or a field that
has quietly gone NaN.

### Ports carry a range, not just a type and a unit

SKILL.md's field types name the type and the unit on every edge. That is not enough to validate
against — add the **legal range and finiteness policy**, so a violation is caught on the edge
that produced it instead of three nodes downstream where it finally manifests.

| Field | Contract |
|---|---|
| `HeightField` (m) | Finite. No range — real terrain spans −11 km to +9 km, so a range check here is a bug, not a guard |
| `MaskField` | Finite, closed `[0, 1]` |
| `WaterField` (m) | Finite, `≥ 0` — it is a depth, not an elevation |
| `SedimentField` (m) | Finite, `≥ 0` |
| Drainage area (m²) | Finite, `≥ cellArea` — every cell drains at least itself (`03`) |
| Slope (tan) | Finite, `≥ 0` |
| `NormalField` | Finite, unit length within tolerance |
| `MaterialField` / layer weights | Finite, each `[0, 1]`, and **partitioning to exactly 1** — `= 1`, not `≤ 1`, and the difference from `MaskField` is the point: a `MaterialField` is a *closed* stack that names its base as a channel (`analysis.derive_materials` / `derive_substances` append `(base, 1 − Σ claimed)`, so they hit `1.0` everywhere), whereas a `MaskField` is one raw coverage mask with the base left implicit, asserted `Σ ≤ 1` at the fan-in below. Two assertions, two sites (`06`, `08`'s *Normalisation*) |

The sweep costs a fraction of any node's own evaluation, and it is the difference between "node 7
emitted a negative depth" and "the export has holes in it".

### Why the value goes bad at the seam

Six mechanisms, none of which need a single node to be wrong:

1. **An out-of-range input meets an operation with a restricted domain.** The classic is `S^n` in
   stream power with `S < 0` from an unfilled pit or a sign slip — for non-integer `n` that is NaN
   on the spot. `sqrt` of a marginally negative depth, `log(A)` where `A = 0`, and `acos` of a dot
   product floating point nudged past 1 are the same bug wearing different hats.
2. **Division by a quantity that is legitimately zero somewhere.** Slope on a flat, capacity in
   still water, drainage area at a divide, a normalising sum whose weights are all 0. Each is
   correct physics and an `Inf`.
3. **Stability limits do not compose.** Each node is stable at its own `Δt`; chained, or
   sub-cycled into a shared budget, they need not be. And **a limit met exactly is not met** — the
   explicit Laplacian at `c = 0.25` has checkerboard amplification `−1`, which neither decays nor
   blows up, so it passes every finite-and-conserved assertion while the pass *roughens* the
   terrain (`09`; `reference-impl`'s 0.9 safety factor exists for this).
4. **The grid-scale mode is what "weird spikes" usually are.** A ±alternating two-cell oscillation
   hides in a histogram and is unmistakable under a sun sweep (`09`). It survives anything
   marginally stable and is amplified by anything slope-driven.
5. **Spikes self-amplify under erosion.** A one-cell spike is a huge local slope, hence a huge
   local capacity, hence more erosion around it next step — the "tumour" in `09`'s catalogue. That
   is why one bad cell does not stay one bad cell, and why finding the step that *created* it
   beats smoothing the field that now contains it.
6. **NaN spreads spatially, not merely downstream.** Any neighbourhood operation — blur,
   Laplacian, the droplet's deposit brush, flow accumulation — mixes one NaN into all its
   neighbours, so the poisoned region grows by the stencil radius every pass. A NaN found at
   export tells you almost nothing about where it started. This is the entire reason `09` says to
   assert after **every** step rather than at the end.

### Guards are named, and clamps are counted

The guards themselves are per-node and specified where they belong — the pipe model's outflow
scaling `K` and its `α_min` floor (`04`), the multifractal's `min(weight, 1)` (`01`), the TWI
slope floor (`06`). Two rules govern all of them:

**A guard is a named constant with a unit and a reason**, not an epsilon sprinkled at the call
site. `sinα ≥ 0.05` is a guard; `+ 1e-9` in a denominator is a wish. The named form survives a
resolution change and can be argued about; the anonymous form quietly sets a different physical
threshold at every cell size.

**Count every clamp, and fail when the count grows.** This is the general form of the
erosion-created-pit check (`09`) and of the sediment-budget rule (SKILL.md): a clamp firing a few
times at start-up is a guard doing its job; the same clamp firing more often each iteration is a
guard **masking a divergence**, and it is the only thing standing between you and a visible
crash. A silent clamp converts a loud failure into a quiet wrong answer, which is strictly worse.
Report clamp counts per node per step and treat a rising trend as a failure.

### Do not despike the symptom

A median or despike pass over a simulation's output removes the evidence and leaves the cause. It
is the numerical twin of healing a seam by blending (SKILL.md): the artefact leaves the preview,
the graph stays wrong, and the next parameter change brings it back somewhere else. Median
filtering is legitimate on **imported** data, where salt-and-pepper genuinely is sensor noise with
no upstream to repair (`08`, `10`); it is illegitimate as a way to survive your own simulation.
When a spike appears, bisect — assert finiteness and range after each node, find the first node
that violates its contract, and fix it there.

## Content-addressed caching

The cache key is a hash of everything the output depends on — which purity makes enumerable:

```
cacheKey(node, ctx) =
    hash( node.desc.typeId,                      # includes version → algorithm changes invalidate
          canonical(node.paramValues),           # canonical: float quantised to ~1e-6, order fixed
          [cacheKey(upstream(p), ctx) for p in node.inPorts],   # ← recursive: Merkle tree
          relevant(ctx) )                        # region, resolution, quality — NOT device
```

The recursion is the point: the key of a node embeds the keys of its whole upstream cone, so
**a change anywhere invalidates exactly the downstream cone and nothing else**. Dirty
propagation isn't a separate mechanism you can get wrong — it's a consequence of the key.

Details that decide whether this works:

- **`device` is excluded from the key** — which is a *promise* that CPU and GPU produce
  equivalent results, and that promise must be enforced by the CPU/GPU tolerance test (`09`).
  If a node can't meet tolerance, it declares one device and the promise is kept vacuously.
- **Float params are quantised before hashing**, or a UI slider generates thousands of
  never-reused entries per drag.
- **Stochastic nodes hash the effective seed**, so re-roll = one node's cone invalidated.
- Cache entries are field buffers: big. LRU by bytes with pinning for the currently-viewed
  node's upstream cone. Evicted entries re-derive — purity again.

## Dirty propagation

With Merkle keys, "dirty" is just "key changed". What remains is scheduling:

- **Param drag:** invalidate the cone, re-evaluate at the *current preview tier only*, debounce
  the full-quality pass until the drag ends.
- **VALUE vs TOPOLOGY invalidation** (from ParamDesc): a VALUE change reuses the execution
  plan (same nodes, same order, same allocations — just re-run kernels); a TOPOLOGY change
  (octave count, enum switching algorithm variant, rewiring) re-plans. This distinction is
  most of the difference between a 60 fps param drag and a stuttering one, because plan
  construction and buffer allocation are where the frame time hides.
- **Upstream of the edit, nothing happens.** Obvious, but only true because keys are
  recursive. Runtimes with hand-rolled dirty flags invariably leak invalidation upstream or —
  worse — fail to propagate down.

## Side-channel masks & the accumulator pattern

Simulations emit more than their primary field. A snow sim (`13`) also produces a snow-cover mask, a
water sim (`03`, `12`) a water mask, debris (`05`, `07`) a debris mask, vegetation (`13`) a canopy
mask — and the consumers are always the same three: splatmap assembly (`08`), material selection
(`06`), and scatter suppression (`07`). Wired directly that is `N` producers × `M` consumers of long
edges, and adding one simulation means rewiring every consumer. Tools therefore ship a **registry
node** — Gaea calls it an Accumulator — that collects these masks by convention and updates itself
as simulations are added or removed. It is good ergonomics and it is a **hole in the node model**
unless two things are handled.

**It has an undeclared input set, which silently breaks the cache.** The whole of caching above rests
on the key enumerating a node's dependencies, and the recursion walks `node.inPorts`. A node whose
real dependency is "every simulation currently in the graph" has inputs that appear in no port list,
so **adding a simulation does not change the accumulator's key** — and every downstream consumer
serves a stale cache entry that is missing the new mask. Nothing crashes; the splatmap is just
quietly wrong, and it stays wrong until something unrelated evicts the entry. The rule that fixes it
is the one the chapter already implies: **the accumulator is editor sugar and must be desugared
before evaluation.** Resolve the collection at plan time into explicit edges, and fold the resolved
set into the identity:

```
cacheKey(accumulator, ctx) += hash( sorted( (producerNodeId, outPortName)
                                            for each collected mask ) )     # the RESOLVED set
```

Then adding, removing or renaming a producer changes the key, and normal Merkle invalidation does
the rest. Hash the *identities*, not the buffers — the upstream keys already cover the contents.

**Precedence must be explicit, or the output depends on node insertion order.** Collected masks
overlap: snow lies on debris, water sits over both. A registry that sums or `max`es its inputs
produces coverage above 1 and violates the partition rule (`06`, `09`'s checklist). Resolving by
traversal order is worse — it makes the result depend on the order nodes were created, so a reorder
or a copy/paste changes the terrain and determinism is gone. Carry a **documented total order** on
the registry (a sensible default being snow → water → vegetation → debris → base, top-down through
the layer stack of `08`) and resolve overlaps by it. It is the same `10` discipline as any other
combiner: never a bare `max`.

Two consequences worth stating because they surprise people:

- **The accumulator is `LOCAL`, but its cone is the whole graph.** The node itself just combines
  masks. Its *upstream* includes every simulation, so it can tile no better than its worst producer
  (`GLOBAL` if any producer is), region invalidation (below) stops being local, and cache pinning
  (Memory & scheduling) now pins nearly everything whenever a consumer is being viewed. Give it the
  tiling contract of its worst upstream, not its own.
- **It is a fan-in, so it is also the natural place for the partition assertion.** Since every
  coverage mask passes through one node, assert `Σ masks ≤ 1` there once, rather than hoping each
  consumer checks. **`≤`, not `=`** — these are the raw coverage masks, independent `[0, 1]`
  fields, and **any** shortfall is the base material's share. `≤` rather than `<` because a
  well-formed stack that names its base as a channel reaches exactly 1: that is the `MaterialField`
  contract in the table above, a *second* assertion at a *second* site, and it is `08`'s "splat
  weights must sum to 1" — a different object one stage later, after compositing has filled the
  remainder. Two assertions, two sites, no conflict.

  ⚠️ **And the assertion has to live here because whether it is detectable downstream depends on
  a choice this node cannot see.** If the consumer composites by laying each material over the
  last — `out·(1 − m) + colour·m`, the shipped `render.splat_blend` — the effective weights sum to
  exactly 1 no matter what the masks do, the base absorbing `Π(1 − mᵢ)`. Measured, masks summing
  to **1.8** still give effective weights summing to **1.0000000000**, and at **3.0** the output
  is still inside the convex hull of its inputs: under *that* operator two simulations claiming
  the same ground produce no artefact at all, and node insertion order quietly decides which one
  wins — the same order-dependence rule (1) above exists to forbid. But if the consumer is a
  base-less weighted sum — `render.material_rgb`, `Σ wᵢ·materialᵢ`, which ships beside
  `splat_blend` and is the default colorizer — the same masks can drive channels past 255 and clip:
  `Σ = 1.8` on a pale palette gives an unclipped `[369 380 401]`, shipped as `[255 255 255]`.

  ⚠️ **And even that one reports conditionally**, which strengthens the case for checking here
  rather than weakening it. Its sensitivity is set by the palette a consumer passes, another thing
  this node cannot see: on the palette the shipped call sites actually get
  (`render._MATERIAL_PALETTE`) a material leaves 8-bit range only at `Σ = 255 / max(channel)` —
  snow 1.02, sand 1.28, water 1.50, grass 1.93, rock 2.13 — so at `Σ = 1.8` a rock-and-grass
  hillside clips nothing, and a real producer bug doubling every mask can export entirely in gamut
  (0 of 4096 pixels clipped). So the defect is invisible, or a hard clip, depending on **two**
  downstream choices the producer cannot make and cannot see. That is exactly why the check belongs
  here — one place, independent of the consumer — and not in whichever compositor happens to be
  wired up. (`reference-impl/tests/test_mask_partition.py`)

**Tier.** **F** — an editor-ergonomics pattern, not a result. The correctness rules are not
discretionary though: they are the purity contract at the top of this chapter applied to a node that
appears to escape it.

## Preview & the resolution pyramid

The tool above the substrate lives or dies on preview latency, and preview correctness is a
substrate responsibility because of one fact: **naively evaluating the same graph at low
resolution produces a different landscape, not a smaller one** — unless every node cooperates.

```
quality tiers:   Q0 = 256²  (drag feedback)
                 Q1 = 1024² (working view)
                 Q2 = full  (final)
```

- World-unit parameters (enforced by the param model) make LOCAL and NEIGHBOURHOOD nodes
  resolution-invariant by construction.
- RESOLUTION_BOUND nodes (droplet with fixed count; anything with a `cells⚠` param) must
  declare a **scaling policy** in their NodeDesc: how to adjust at preview so Q0 *predicts* Q2.
  Droplet count scales with cell count; brush radius stays in metres. A node without a policy
  previews with a visible "preview differs" badge — honesty over silent wrongness.
- GLOBAL nodes evaluate at preview resolution over the **full domain**, never at full
  resolution over a crop — a cropped stream power has wrong drainage everywhere (`08`).
- The pyramid also serves the *pipeline*: run erosion at Q1, upsample, add RESOLUTION_INVARIANT
  detail at Q2. This is the standard structure of every production terrain graph, and the
  runtime should make it a first-class pattern (an explicit `resample` node with a stated
  filter, `08`) rather than an accident.

## Region invalidation

A brush stroke or stamp edit dirties a *region*, not the world. For LOCAL and
NEIGHBOURHOOD(r) nodes, recomputing `region ⊕ r` (dilated by each node's radius as it
propagates down) is sound and turns sculpting on a 4k terrain into a per-stroke cost
proportional to the stroke.

For GLOBAL nodes it is **not sound** — an edit that changes where water flows changes the
terrain arbitrarily far downstream. The honest options, in order of preference:

1. Recompute the GLOBAL node at Q1 immediately (fast, whole-domain, approximately right),
   full quality deferred to idle.
2. Localised approximation with an explicit staleness marker on everything downstream.

Never silently region-update through a GLOBAL node. That is the tool-scale version of the
tile-seam bug, and users learn to distrust the preview permanently after seeing it once.

## Memory & scheduling

- **Budget = working set of the active cone at current quality**, not the whole graph. Peak
  memory is minimised by evaluating in an order that frees dead buffers early — interval
  analysis over the topological order (classic register allocation, same maths).
- **Out-of-core:** at Q2 on big domains, LOCAL/NEIGHBOURHOOD spans tile with aprons per `08`;
  GLOBAL nodes get the whole (possibly memory-mapped) field. The LOCAL/GLOBAL flag *is* the
  out-of-core plan.
- **CPU/GPU placement:** minimise transfers, not kernel time — a graph that ping-pongs
  between devices loses to one that stays put. Prefer contiguous GPU runs; readback only at
  cache boundaries the user actually views. See `15` for what runs where.
- **Async:** param-drag evaluation must be cancellable mid-cone. Purity makes cancellation
  trivial (abandon, no rollback); the scheduler just needs to check a generation counter
  between nodes.

## Serialisation

The graph file is: node instances (typeId + version, id, paramValues, seedOffset), edges,
rootSeed, and the manifest conventions of `08`. Parameters serialise by *name*, not index —
node versions add parameters, and old files must load with new defaults filled in.

**Determinism contract for the file:** same file + same rootSeed + same substrate version =
bit-identical Q2 output on one device, tolerance-identical across devices (`09`). That
sentence is the product guarantee that lets users trust presets, share graphs, and file bug
reports — write the tests that enforce it before writing nodes, because retrofitting
determinism into a node library is a rewrite.
