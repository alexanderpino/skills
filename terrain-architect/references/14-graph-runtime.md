# Graph Runtime

The substrate layer of a terrain tool: what a node *is*, what a parameter *is*, and how
evaluation, caching and invalidation work. Everything Gaea, World Machine and Houdini's
heightfield SOPs have in common lives here; everything they differ on (UI, presets, branding)
deliberately does not.

Contents: [The node model](#the-node-model) · [The parameter model](#the-parameter-model) ·
[Parameter semantics](#parameter-semantics) · [Evaluation](#evaluation) ·
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
