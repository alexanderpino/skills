# ADR 009 - Arbitrary raster dimensions and GPU-native high-resolution authoring

**Status:** accepted
**Date:** 2026-08-02
**Amends:** ADR 007 and ADR 008

## Context

Terrain Studio must author imported and generated heightmaps at any positive rectangular sample
dimensions, including `16384 x 16384` and deliberately awkward shapes such as
`1573 x 13789`. The existing large-world design supports rectangular domains and partial terminal
regions, but it does not yet make these sample dimensions an explicit product gate. The existing
Extreme design also assigns field-page generation and some terrain algorithms to CPU/workers.

A `16384 x 16384` R32F field contains `268,435,456` samples and occupies
`1,073,741,824` bytes before auxiliary fields or scratch space. It cannot be represented as one
portable WebGPU buffer under the guaranteed `256 MiB` buffer limit, and a single 16384-wide texture
would exceed the accepted Extreme profile's guaranteed `8192` texture dimension. Supporting this
size therefore means paged processing, not raising one monolithic allocation limit.

"No CPU work" cannot literally include browser event handling, command encoding, file IO, or
residency bookkeeping. The enforceable product meaning is: **no CPU terrain-field computation, no
whole-raster CPU materialization, and no full-field GPU readback** in high-resolution mode. The CPU
remains a bounded control plane over metadata and transfers; WebGPU performs all per-sample terrain
evaluation.

## Decision drivers

- Accept independent arbitrary integer sample widths and heights without power-of-two rounding.
- Make `16384 x 16384` a required working fixture, not merely an import metadata case.
- Keep memory proportional to the active page set, not total raster area or aspect ratio.
- Prevent silent CPU fallback on large terrains.
- Preserve exact shared samples, apron semantics, physical units, and square/hex correctness.
- Keep the same graph behavior at ordinary and high-resolution dimensions.

## Decision

### Arbitrary dimensions

`WorldDomain/1.resolution.sampleCount` accepts independent integer `columns` and `rows >= 2`.
No product path rounds either axis to a power of two, forces a square, stretches the world, or crops
valid samples. Imported source dimensions are retained exactly.

Power-of-two page **cores** remain an internal scheduling choice. They do not constrain domain
dimensions. Each page carries a valid core rectangle and valid apron rectangle. Terminal pages may
be partial; samples outside their valid rectangle are neither authored data nor legal filter input.
Boundary conditions and apron synthesis operate from the valid domain edge, never from allocation
padding.

For 256-cell square page cores under vertex posting:

- `16384 x 16384` samples are `16383 x 16383` cells, decomposed into `64 x 64` pages; terminal
  pages contain `255` valid cells per terminal axis.
- `1573 x 13789` samples are `1572 x 13788` cells, decomposed into `7 x 54` pages; the terminal
  valid core is `36 x 220` cells.

Parent registration and deterministic downsampling include partial children through an explicit
validity mask/rectangle. Shared terminal posts are copied bit-identically. Odd-r hex pages retain
global row parity and their declared basis at partial edges.

### GPU-required high-resolution mode

The preflight selects `gpu-required-paged` whenever the requested raster cannot fit the complete
declared live field/scratch cone inside the authored monolithic budget. Both named fixtures above
must be supported in this mode; `16384²` is always tested paged.

In `gpu-required-paged` mode:

- WebGPU compute/render passes perform every per-sample generator, operator, filter, analysis, and
  simulation step;
- no `Float32Array` or equivalent CPU allocation may represent the complete heightmap, auxiliary
  map, or scratch field;
- no CPU loop may visit terrain samples or implement a fallback evaluator;
- no full-field readback is permitted; bounded asynchronous counters, request records, diagnostic
  samples, and chunked export transfers are allowed and byte-budgeted;
- file decode/upload and export may move bounded chunks, but may not transform terrain values on
  CPU;
- graph preflight enumerates the demanded node cone and rejects it before allocation if any node
  lacks a validated GPU implementation for its locality, lattice, formats, and boundary policy;
- a device loss pauses the graph and reports the failing stage. It never resumes through CPU.

GLOBAL semantics do not weaken. A GLOBAL node needs a GPU algorithm that sees the complete declared
global substrate through paged/multi-pass storage and produces the same contract. Until that exists,
the node is explicitly incompatible with `gpu-required-paged`; it is not run per page and is not
silently moved to CPU.

Registry metadata records `execution: gpu-native | cpu-only | either` plus the validated high-
resolution GPU capability. Completion of the GPU-only story requires every production terrain-field
node to be either GPU-native in the named mode or explicitly excluded from the production registry;
"supported" may not mean that a graph opens but later falls back.

### Boundary Landforms node

A new pure generator, **Boundary Landforms**, authors hills, mountain chains, or cliffs along
selected world edges. It uses exact distance to the valid rectangular domain boundary, selected
side masks, world-space asymmetric crest paths, and metre-authored profiles. It is not radial
envelope texture and does not claim a proprietary tool algorithm.

The node exposes selected north/east/south/west edges, style (`hills | mountains | cliffs`), inset,
band width, relief, falloff, crest wandering/detail wavelengths, corner join, strength, and seed.
It outputs `height:m`, `coverage:[0,1]`, and `boundaryDistance:m`. Hills are smooth; mountains build
an asymmetric crest mass before dissection; cliffs form a heightfield lip/face and explicitly do not
claim overhangs or open voids. Inactive edges and samples beyond the authored band are exact zero.

The node is LOCAL, world-coordinate deterministic, square/hex aware, arbitrary-dimension safe, and
GPU-native. Its normal-resolution story may ship before the high-resolution runtime, but the GPU-
only story must include it in the complete `16384²` registry gate.

## Consequences

- Arbitrary domain dimensions no longer inherit power-of-two restrictions from page allocation.
- A 16K terrain is a bounded page graph, never one texture, one buffer, or one CPU array.
- CPU-only nodes become visible graph compatibility errors in high-resolution mode until they gain a
  correct GPU implementation. This is stricter than the prior CPU/GPU split and may temporarily
  reduce which graphs can run at 16K, but it prevents hidden stalls and out-of-memory failures.
- Standard/ordinary-size execution may retain CPU reference implementations for testing and parity;
  they are never a runtime fallback for `gpu-required-paged`.
- ADR 007's bounded domain/evaluation contracts and ADR 008's field-page/clipmap representation
  remain in force except where this decision explicitly strengthens GPU ownership.

## Required gates

- Exact dimension round-trip for square/hex fixtures including `16384 x 16384`, `1573 x 13789`,
  `2 x N`, `N x 2`, prime dimensions, and both portrait/landscape orientation.
- Exact page/core/terminal arithmetic for the two named fixtures; no zero-area page.
- Allocation spies prove no monolithic 16K texture/buffer and no whole-field CPU typed array.
- GPU command/dispatch evidence is non-empty for every demanded node; CPU sample-loop and fallback
  spies remain zero.
- Active GPU/staging bytes plateau within the authored budget while processing more pages than fit.
- Partial-edge filters, aprons, shared posts, odd-r parity, cancellation, save/load, import/export,
  and schedule-order determinism remain correct.
- Device loss and a CPU-only-node mutation reject explicitly rather than falling back.
- Boundary Landforms localization, distinct profiles, resolution consistency, square/hex behavior,
  arbitrary dimensions, and 16K GPU page execution are asserted with cone/radial controls.

## Grounding

- Terrain Architect chapters 08, 10, 14, and 15: vertex posting, partial terminal regions, pages and
  aprons, world-space SDF/placement, asymmetric mountain mass, node locality, GPU placement, and the
  prohibition on silent LOCAL/GLOBAL semantic changes.
- ADR 007: independent rectangular domains, bounded evaluation, deterministic shared boundaries,
  and partial terminal regions.
- ADR 008: streamed field pages, bounded residency, WebGPU capability limits, cancellation, and
  cook-free runtime caches.