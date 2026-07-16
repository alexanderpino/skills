# GPU & Realtime

How the algorithm families actually land on a GPU, and which of them can run per-frame versus
amortised versus baked. This file is the bridge between the algorithm references (`01`–`13`)
and the runtime (`14`): the NodeDesc flags declared there get their values here.

Contents: [The realtime tiers](#the-realtime-tiers) · [GPU patterns by family](#gpu-patterns-by-family) ·
[Determinism on GPU](#determinism-on-gpu) · [Formats & memory](#formats--memory) ·
[Amortisation](#amortisation-spreading-simulation-over-frames) · [The realtime graph](#the-realtime-graph)

## The realtime tiers

Every node lands in exactly one tier, and the tier is decided by the algorithm's information
flow — not by how fast the kernel is. A fast kernel with global data flow is still not
realtime.

| Tier | Budget | What qualifies | Families |
|---|---|---|---|
| **T0 per-frame** | µs–low ms, every frame | LOCAL per-cell work, fixed small neighbourhoods | Noise & FBM (`01`), all operators/remaps (`10`), small blurs, slope/normals (`06`), analytic primitives |
| **T1 interactive** | 10–200 ms, on edit | NEIGHBOURHOOD work, bounded iteration, converging sims | Thermal (`05`), pipe erosion at working res (`04`), guided filter (`10`), Werner dunes (`05`), scatter (`07`), most analysis (`06`) |
| **T2 amortised** | spread over many frames | Long-running sims with checkpointable state | Droplet at scale (`04`), ecosystem sim (`13`), glacier SIA (`12`), lava CA (`19`), pipe at full res |
| **T3 baked** | offline, cached | GLOBAL data flow | Flow accumulation & everything downstream of it (`03`), stream power (`04`), full-domain AO at large radius (`06`), orographic precipitation (`13`) |

The line that matters is **T2/T3**: T2 is slow-but-local (tileable, streamable, resumable),
T3 is global (must see the whole domain). A "fully realtime" terrain tool is one whose graph
is T0–T2 only — which is achievable, and the cost is exactly the loss of everything drainage-
derived. That trade should be made knowingly: rivers, wetness, and stream-power landforms are
what T3 buys. The standard compromise is a baked T3 macro-terrain with T0–T2 detail layered on
top — see [The realtime graph](#the-realtime-graph).

## GPU patterns by family

The recurring implementation questions — write pattern, ping-pong, halo, atomics — answered
once per family.

### Noise, operators, remaps, analysis (`01`, `10`, `06`)

The trivial tier. **Gather-only, no neighbours or fixed 3×3, one output write per thread.**
8×8 thread groups, no shared memory needed below 5×5 kernels. Perlin/Simplex permutation
tables in constant memory or computed via hash (PCG/wang hash — cheaper than the table fetch
on modern GPUs, and removes the 256-cell period). FBM octaves loop in-register; do not
multi-pass octaves.

The only real decision: **analytic derivatives vs finite differences.** Perlin/Simplex have
cheap analytic gradients — computing height and gradient together in T0 is nearly free and
feeds normals without a second pass. But ridged noise is non-differentiable at the fold (`01`)
and warped noise needs the chain rule through the warp; when the graph gets complicated,
finite-differencing the final field (3 extra taps) is simpler and always correct. Pick per
node, declare in the NodeDesc.

### Grid simulations: pipe, thermal, Werner, SIA (`04`, `05`, `12`)

**The pattern: ping-pong + halo.** Read buffer A, write buffer B, swap. Never in-place — that
is the determinism bug from `05`, and on GPU it isn't even deterministic between *runs*.

- **Shared-memory halo:** each thread group loads its tile plus a 1-cell (or radius-r) apron
  into groupshared, syncs, then computes. Standard, and worth it from radius 1 up.
- **The pipe model is 3–4 passes per step** (flux → water/velocity → erosion-deposition →
  advection), each a full-screen dispatch. Fuse flux+scaling into one pass; do not try to fuse
  across the write-read boundary between flux and depth — that boundary is the algorithm.
- **Semi-Lagrangian advection** (`04` step 7) is a scattered *read* (bilinear sample at
  `p − vΔt`), which GPUs do natively via texture sampling. This is why pipe erosion is
  GPU-native and droplet is not: pipe scatters reads, droplet scatters *writes*.
- **Thermal:** the 8-neighbour redistribute becomes gather-form — each cell computes what it
  *receives* from each neighbour by re-evaluating the neighbour's give-away decision. Slightly
  redundant compute, zero atomics, fully deterministic. This gather transformation is the
  general trick for turning any local scatter into a GPU-friendly pass.
- **Convergence detection** (thermal, SIA): reduce `max|Δh|` with a two-pass reduction every
  N steps, not every step; readback of a single float still costs a sync. Better: run a fixed
  budget per frame and let T2 amortisation own completion.
- **SIA stiffness** (`12`): the `H⁴` diffusivity wants an implicit solve; on GPU, prefer
  adaptive subcycling of the explicit form (cheap, parallel, no linear solver) with the
  timestep from the current max diffusivity — one more reduction.

### Droplet erosion (`04`)

The awkward one: **scattered writes with overlap.** Three viable schemes:

1. **Atomic delta accumulation** — droplets `InterlockedAdd` into a fixed-point delta buffer
   (R32_SINT, height quantised at e.g. 1/1024 m); a second pass applies deltas. Deterministic
   *in sum* because integer addition is associative — this is the reason for fixed-point, since
   float atomics reorder and break bit-reproducibility. Contention is low after the first few
   steps because droplets disperse. **Default choice.**
2. **Tiled batching** — partition droplets by spawn cell into a checkerboard with gap ≥ brush
   radius + max travel; run same-colour tiles concurrently. No atomics, fully ordered, more
   passes. Choose when fixed-point quantisation is unacceptable.
3. **Sort-by-footprint (rasterisation-style)** — bin brush stamps, then one thread per *cell*
   gathers overlapping stamps. Most work, perfect determinism, rarely worth it.

Droplet paths are serial per droplet (~30–64 steps); parallelism is across droplets. Warp
divergence is real but acceptable — droplets in a warp have similar lifetimes. Spawn positions
from a seeded hash of droplet index, never from a shared RNG state.

### Flow routing & stream power (`03`, `04`)

The honest section: **these are the algorithms that resist the GPU**, and the reason is the
same reason they're T3 — global, ordered data flow.

- **Priority-Flood is a priority queue** — inherently serial. GPU alternatives exist
  (iterative flooding to fixpoint), but the practical answer at terrain scales: run it on CPU.
  An 8k fill is under a second; the graph runtime (`14`) overlaps it with GPU work.
- **Flow accumulation / Braun–Willett stack**: the stack order is a serial DFS, but the
  *levels* of the receiver tree can be processed breadth-parallel: iteratively, each cell adds
  its accumulated area to its receiver, level by level (O(depth) passes), or use pointer-
  doubling / parallel tree contraction for O(log n) passes. Depth of real drainage trees is
  large (the main river is long), so in practice: **CPU for the solve, GPU for everything
  around it.** Braun & Willett themselves parallelise over independent drainage basins —
  effective when there are many, useless for one big basin.
- Consequence for the substrate: the T3 pipeline is a **CPU-GPU pipeline**, and the runtime's
  placement logic (`14`) should expect these specific nodes to be CPU_ONLY without treating
  that as a defect.

### Scatter (`07`)

Poisson-disk parallelises by **phase groups** (Wei 2008; Ebeida 2011): cells at the same
position within a macro-tile can generate candidates concurrently without conflicts. But
honestly assess whether you need it: Ulichney tile thresholding is T0 (one texture fetch per
candidate cell) and covers ground cover; Bridson on CPU covers props. GPU Poisson-disk is for
millions of blue-noise samples per edit, which is rarer than it sounds.

Rule-based filtering and instance attribute derivation (`07`) is embarrassingly parallel T0:
one thread per candidate, stream-compact survivors (prefix sum) into the InstanceSet.

### AO & long-range analysis (`06`)

Timonen–Westerholm sweeps are 1D scans per azimuth — map each scanline to a thread, or better,
each azimuth to a pass with scanlines as threads. 8–16 azimuths = 8–16 passes over the field:
T1 at working resolution, T3 at 8k+ with large radius. Wave-exposure fetch (`12`) is the same
machinery.

## Determinism on GPU

The `14` cache-key promise (`device` excluded from the key) and the `09` CPU/GPU tolerance
test both depend on knowing exactly where GPU nondeterminism comes from. There are only three
sources:

1. **Float atomics / reduction order.** Float addition is not associative; any float atomic or
   unordered reduction gives run-to-run drift. Fix: fixed-point atomics (droplet scheme 1),
   ordered tree reductions, or per-tile ordered accumulation.
2. **In-place neighbour updates.** Already banned by ping-pong. On GPU also includes
   read-after-write hazards within a dispatch — never read a UAV you write in the same pass
   without a barrier structure that fully orders it.
3. **Cross-vendor float differences** (FMA contraction, transcendental precision, denormal
   handling). Not fixable — this is *why* the contract is bit-identical per device,
   tolerance-identical across devices (`14`). Keep transcendentals out of hot accumulation
   paths where their error compounds (use polynomial `fade`, not `pow`, in noise inner loops).

Practical corollary: **`precise`/`invariant` qualifiers on position-critical math** in shaders
that must agree between passes (e.g. the same height evaluated by two different kernels), or
the compiler's FMA choices will disagree per shader and violate the shared-edge rule of `08`.

## Formats & memory

| Field | Working (GPU) | Notes |
|---|---|---|
| height, water, sediment | **R32_FLOAT** | The `08` precision rule; R16F's 10-bit mantissa terraces within a sim, not just at export |
| flux (pipe) | RGBA32F (4 directions packed) | One fetch per neighbour exchange |
| velocity | RG32F | |
| droplet delta | R32_SINT fixed-point | Determinism, above |
| masks | R8_UNORM, packed ×4 | |
| A (drainage) | R32F, log-encoded if stored | Spans 6+ decades |

- **Pack the pipe model's per-cell state** (b, d, s + flux + v) into as few textures as
  possible; the sim is bandwidth-bound and every texture is a separate cache stream.
- **Halo size** = the NodeDesc NEIGHBOURHOOD radius (`14`) — one number serving tiling (`08`),
  shared-memory apron, and region invalidation. Keep them literally the same constant.
- **Transient aliasing:** ping-pong buffers of all T1 sims can share one pool at working
  resolution; lifetime analysis from `14`'s scheduler decides. This halves working-set memory,
  which matters at 8k (256 MB per R32F field).
- **Active-tile processing:** sims that converge locally (thermal, dunes, snow) maintain a
  dirty-tile list (append via one atomic per tile, not per cell) and dispatch indirect on it.
  Late-stage thermal touches <5% of tiles; this is a 20× win and it's the main reason T1 sims
  stay interactive on big fields.

## Amortisation: spreading simulation over frames

T2's contract with the runtime: a sim node exposes `(state, step(state, budget), progress)`
instead of `run()`. The runtime then owns scheduling:

- **Budget in milliseconds, not iterations** — measure a step, adapt the count. A fixed
  iteration count per frame is a frame-time landmine at 4k.
- **The cache (`14`) stores checkpoints**: params changed mid-sim → restart the cone from the
  last upstream-valid checkpoint, not from zero. For pipe/thermal, checkpoint = the ping-pong
  buffers; cheap.
- **Preview shows partial state honestly** — an erosion at 40% is a real intermediate terrain,
  and showing it evolving *is* the feature (it's half of Gaea's perceived interactivity).
  Downstream T0/T1 nodes just re-run on the moving input each frame; that's what T0 means.
- **Convergence beats iteration counts** here too (`14` parameter semantics): "erode until
  relief change < ε" makes progress meaningful and completion detectable.

## The realtime graph

The composition pattern for "partly or fully realtime" terrain, which is what the tiers exist
to support:

```
[T3, baked once]     uplift → stream power → flow/A → macro height + river/A fields
                        ↓ stored as tiles + manifest (08)
[T2, amortised]      pipe or droplet detail erosion per streamed region, apron per 08
                        ↓
[T1, on edit]        thermal touch-up, masks, analysis at working res
                        ↓
[T0, per frame]      detail noise (world-space, seamless by construction),
                     operators, materials, virtual-texture page fills
```

- The T3 bake produces the fields only T3 can: drainage-consistent macro relief and `A`.
  Everything below treats them as read-only inputs — which is the LOCAL/GLOBAL flag (`14`)
  expressed as pipeline structure.
- T0 detail noise on streamed tiles is seamless *for free* because of the world-space seed
  contract — the substrate's oldest invariant is what makes runtime generation viable at all.
- Region streaming: T2/T1 evaluate per-region with aprons; the NodeDesc radius drives the
  apron; RESOLUTION_BOUND nodes use their declared scaling policy for distant/LOD regions
  (`14`).
- **What "fully realtime, no bake" costs:** replace the T3 layer with authored macro shape
  (`02` uplift-style masks + warped noise) and accept no true drainage. Rivers become authored
  splines (`10`) with `A` faked from a distance field. Playable-quality terrain does this all
  the time; it just shouldn't be called erosion.
