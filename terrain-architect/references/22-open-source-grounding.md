# Open-Source Grounding Ledger

The pre-computed comparison between this skill's neutral terrain contracts and mature
open-source implementations. Implementation answers consume these decisions directly; they do
not send the user to inspect upstream repositories. The machine-readable source of truth is
`references/open-source-grounding.json`.

Contents: [Grounding scale](#grounding-scale) · [Pinned upstreams](#pinned-upstreams) ·
[Hydrology and landscape evolution](#hydrology-and-landscape-evolution) ·
[Noise erosion and scatter](#noise-erosion-and-scatter) ·
[Engine-native decisions](#engine-native-decisions) · [Maintenance](#maintenance)

## Grounding scale

| State | Meaning |
|---|---|
| **Source-grounded** | Exact upstream revision, licence, source symbols and behavior inspected |
| **Cross-validated** | The local executable specification is also compared by test against upstream output |
| **Paper-grounded** | Primary source checked, but no trustworthy or policy-approved implementation is encoded |
| **Skill-stricter** | Public implementations exist, but the skill deliberately adopts a stronger invariant |

Grounding is not copying permission. The licence column records what was inspected; project policy
decides what may be reused. Neutral pseudocode records behavior and deliberate choices so an
engine implementation does not inherit a library's runtime architecture.

## Pinned upstreams

| ID | Repository @ revision | Licence | Grounding |
|---|---|---|---|
| Landlab | `landlab/landlab@0b0ef086` | MIT | Barnes fill, Braun–Willett stack, stream power, diffusion |
| RichDEM | `r-barnes/richdem@9a1c97bb` | GPL-3.0-only | Priority-Flood, D8 accumulation, D∞ safeguard; optional local cross-check |
| pysheds | `pysheds/pysheds@1949ce1d` | GPL-3.0-only | D8/D∞/MFD, flats/pits, pipeline order; optional local cross-check |
| fastscapelib | `fastscape-lem/fastscapelib@b85cc6b1` | GPL-3.0-only | sink resolution, O(N) flow stack, stream power, ADI diffusion |
| OpenSimplex2 | `KdotJPG/OpenSimplex2@4cd120d3` | CC0-1.0 | lattice rotation, gradients, hashing and normalisation |
| FastNoiseLite | `Auburn/FastNoiseLite@785f37a9` | MIT | compositional noise/fractal/warp API and variant differences |
| Hydraulic-Erosion | `SebLague/Hydraulic-Erosion@f245576d` | MIT | CPU/GPU droplet loop, brush and boundary/race deviations |
| UnityTerrainErosionGPU | `bshishov/UnityTerrainErosionGPU@0e59f7c4` | MIT | GPU virtual-pipe and thermal pipeline with known stencil defects |
| tph_poisson | `thinks/tph_poisson@e436117b` | MIT | Bridson grid/active-list hardening and deterministic sampling |

These are pinned default-branch revisions inspected on 2026-07-20, not claims about tagged
releases. Re-ground before publication-critical use or when changing a neutral contract.

## Hydrology and landscape evolution

### Priority-Flood

**Adopt:**

- Perimeter/open-boundary cells seed the queue.
- Production fill uses the Barnes priority queue plus pit FIFO.
- Epsilon fill raises each downstream flat cell by the smallest representable increment
  (`nextafter`) when raw DEM precision is authoritative.
- Game worlds may instead declare a fixed world-unit epsilon such as `1e-5 m`; that is an engine
  policy chosen for reproducibility and vertical scale, not the Barnes algorithm.
- Integer height fields cannot express epsilon drainage; route in floating working precision.

RichDEM and Landlab independently confirm machine-precision gradients. The readable local
`flow.py` uses a fixed epsilon deliberately; production code exposes the policy and reports when
precision cannot represent another increment.

### Flow direction and accumulation

**Adopt:**

- D8 tie-breaking is a declared, versioned policy. pysheds uses
  N→NE→E→SE→S→SW→W→NW with strict `>` first-wins; the local readable oracle uses another fixed
  order. Neither order is "the D8 algorithm."
- Flats and pits are explicit states; canonical order is fill/breach → resolve flats → route →
  accumulate.
- Production accumulation is O(N): indegree/Kahn or receiver/donor stack. The numpy `argsort`
  implementation is test-sized scalar truth, not the runtime path.
- D∞ snaps an angle within `1e-6 rad` of an exact D8 direction to one receiver to avoid
  floating-point two-receiver cycles.
- MFD normalises positive downslope `slope^p` weights; `p` is an exposed policy. Freeman's `1.1`
  and plain `1.0` are both used, so serialise the chosen value.

### Stream power

**Adopt:**

- `n=1` uses the Braun–Willett closed form and O(N) receiver order.
- If `n≠1` is exposed, use a guarded solver: bracketed Brent (Landlab) or guarded Newton
  (fastscapelib). Do not silently apply the linear formula.
- Treat nonlinear MFD as unsupported unless a separately verified formulation is implemented.
- The solver must not cut a node below its receiver or recreate a filled depression. Clamp/skip
  flooded nodes and count corrections as a diagnostic.
- Threshold stream power is an optional extension, not part of the minimal linear oracle.

### Hillslope diffusion

**Adopt:**

- Explicit five-point diffusion remains scalar truth because its single-mode decay is analytic.
- Runtime bounded steps obey the declared CFL margin.
- Long geological bakes should use an implicit/ADI production path when timestep cost matters.
- Landlab's explicit implementation uses an empirically conservative `0.15` prefactor versus the
  textbook two-dimensional `0.25`; expose the safety policy rather than hiding it.

## Noise erosion and scatter

### OpenSimplex and general noise

**Adopt:**

- Do not conflate textbook Gustavson simplex with OpenSimplex2. OpenSimplex2 uses its own lattice,
  128-entry 2D gradient table, seed hash and normalisation.
- Use `noise3_ImproveXY`-class orthonormal lattice rotation for 3D noise sampled on an XY terrain
  plane.
- FastNoiseLite demonstrates the right product API—base noise, fractal composition and domain
  warp as separate choices—but its 2D and 3D "OpenSimplex2" labels do not mean the same algorithm.
- Version the exact variant and constants in graph serialisation; equal node names do not imply
  equal output.

### Droplet erosion

**Adopt:**

- Inertia-blended direction, capacity from downhill delta/speed/water, radius-brush erosion and
  bilinear point deposition.
- Precompute one translation-invariant interior brush and explicit boundary brushes.
- Keep CPU and GPU boundary stopping policy identical.
- Do not inherit SebLague's overlapping non-atomic GPU writes as if deterministic. Use spatial
  batches, deterministic delta accumulation, or explicitly classify the node nondeterministic.

### Virtual-pipe and thermal GPU

**Adopt:**

- The outflow scale that prevents exporting more water than a cell owns is mandatory.
- Keep flux, water/velocity, erosion/deposition and transport as explicit staged passes.
- The Št'ava shallow-water `lmax` capacity ramp is a verified extension.
- The inspected Unity implementation is four-directional and contains a documented non-square-cell
  thermal bug. Do not port either defect. The skill adopts distance-correct eight-neighbour
  thermal and recommends eight-pipe radial flow where quality requires it: **skill-stricter**.

### Poisson disk

**Adopt:**

- Grid cell size `0.999*r/sqrt(dimensions)`; the `0.999` hardens numerical boundary cases.
- Default `k=30` candidate attempts.
- O(1) swap-with-last active-list removal.
- Deterministic candidate generation in `[r, 2r]`.
- Runtime chunks require stable region seeds and shared-border ownership in addition to Bridson's
  local minimum-distance rule.

## Engine-native decisions

| Library behavior | Neutral contract adopted by the skill | Engine translation |
|---|---|---|
| Python/C++ whole-domain arrays | Typed world-space fields with locality declaration | streamed resources plus explicit GLOBAL bake/domain |
| Dynamic allocation and containers | Algorithmic queue/stack/buffer requirements | pools, job-owned transients or render-graph resources |
| Blocking API | Ordered pass graph | jobs/dispatches, cancellation, progress and publish barrier |
| Host exceptions and NaN propagation | Explicit invalid-state and correction diagnostics | counters/status, deterministic failure policy |
| Library tie/default choices | Versioned parameter or declared invariant | serialised node implementation version |
| CPU implementation order | Determinism and tolerance contract | double buffers, stable reduction, CPU/GPU parity tests |
| Offline completion | T0–T3 locality/budget declaration | preview, amortisation, checkpoint and bake policy |

The answer should present this adopted contract directly. Upstream names belong in provenance and
explanation, not as an instruction for the user to finish the algorithm research.

## Maintenance

1. Update `references/open-source-grounding.json` first with a full 40-character revision, SPDX
   licence, source symbols, adopted behavior, deviations and engine translation.
2. Reconcile the affected algorithm chapter and its `09` oracle.
3. Add or update a capability eval that would fail if the adopted behavior regressed.
4. Run `python evals/validate.py` and the full `reference-impl` suite.
5. Never write "source-grounded" from a repository name alone; pin and inspect the source paths.
