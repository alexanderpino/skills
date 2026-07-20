# Reference-Informed, Engine-Native Implementation

How to turn papers and open-source geoscience libraries into an engine-owned terrain stack when
the reference implementation is scientifically useful but architecturally wrong for a game
runtime. This chapter defines an engineering and provenance process, not a legal conclusion;
project counsel decides what source use is allowed and whether a particular isolation process is
legally sufficient.

Contents: [Choose the source boundary](#choose-the-source-boundary) ·
[How this skill is pre-grounded](#how-this-skill-is-pre-grounded) ·
[The implementation packet](#the-implementation-packet) ·
[Roles and evidence](#roles-and-evidence) · [Implementation workflow](#implementation-workflow) ·
[Verification without dependency](#verification-without-dependency) ·
[Game-engine delivery](#game-engine-delivery) · [Failure modes](#failure-modes) ·
[Release checklist](#release-checklist)

## Choose the source boundary

The default is not blind reimplementation. It is **reference-informed, engine-native**:
scientifically mature libraries and papers ground the behavior, while owned code supplies the
runtime shape the engine needs. Do not use *from scratch*, *dependency-free* and *clean-room* as
synonyms. State which boundary actually applies:

| Mode | Implementer may inspect | Shipped product contains | Use when |
|---|---|---|---|
| **Reference-informed, engine-native** | Papers and approved open-source code/tests | Owned engine code; required notices or permitted reused fragments only if policy allows | Normal game-engine path: ground behavior, then redesign the runtime |
| **Source-independent** | Papers, standards, equations, generated fixtures; no avoided implementation source | Only owned code | The team must show its expression was independently written |
| **Separated clean-room** | Implementer sees only an approved functional specification and oracle set written by a separate team | Only owned code | Counsel or contract requires role separation and a documented information barrier |

An algorithm paper, a source-code repository, a dataset, a shader snippet and a patent are five
different provenance surfaces. A paper describing an algorithm does not grant a licence to copy
its accompanying source; an open-source licence does not answer patent or data rights; a
public-domain implementation still needs its provenance recorded. Do not make legal conclusions
from a provenance tier. `P/F/L/N/?` says how the terrain claim is sourced, not whether code may be
copied or shipped.

## How this skill is pre-grounded

Approved open-source libraries are high-value references because they encode details papers often
omit: tie-breaking, boundary defaults, no-data handling, convergence guards, precision choices and
pathological fixtures. The skill maintainer performs that comparison once and records it in
`22-open-source-grounding.md`; the implementation answer consumes the result.

Each grounding entry records the exact upstream revision and licence, source paths/symbols,
paper lineage, adopted behavior, deliberate deviations, and engine-runtime translation. Algorithm
chapters then carry the neutral pseudocode and edge cases. **Do not answer an implementation
request with "inspect library X".** Read the grounding entry internally and deliver the adopted
behavior and engine-native implementation packet directly.

This distinction matters because research/GIS libraries usually assume heap arrays, CPU batch
execution, whole-domain ownership, dynamic dispatch, host-language exceptions and offline
latency. A game engine may require persistent GPU resources, frame-budgeted dispatches, job-system
CPU execution, fixed allocators, world streaming, deterministic multiplayer/replays,
platform-specific shaders, versioned assets and cancellation. The mathematics transfers; the
runtime rarely does.

## The implementation packet

Before code, produce one packet that an implementer can execute without reconstructing intent:

```text
AlgorithmIdentity
  family, provenance tier, primary papers, version/variant
Isolation
  reference-informed-engine-native | source-independent | separated-clean-room
  materials implementer may inspect; materials explicitly excluded
ReferenceBasis
  pre-grounded papers and approved library revisions from 22; adopted behavior; deviations
FieldContract
  inputs/outputs, units, coordinate convention, precision, invalid values
Parameters
  name, type, unit, valid range, default rationale
Algorithm
  equations, paper-derived pseudocode, update order, data layout
Numerics
  timestep/CFL rule, stability condition, convergence/termination
Boundaries
  open | closed | periodic; tile apron or GLOBAL declaration
Determinism
  seed derivation, buffering, parallel reduction/order policy
CPU/GPU
  gather/scatter pattern, passes, barriers, atomics, formats
Oracles
  analytic cases, invariants, quantitative signatures, tolerances
RuntimeFit
  allocation/lifetime, jobs, GPU resources, frame budget, streaming, cancellation, serialisation
ProvenanceRecord
  papers/specifications/libraries used, code reuse if any, fixtures, notices and authors
```

The algorithm chapters (`01`–`19`) supply the equations, pseudocode and parameter starts.
`14` supplies the node/runtime contract, `15` the GPU mapping, and `09` the oracle suite. The
packet joins them so implementation does not silently drop the unit, boundary or verification
rules while translating pseudocode into engine code.

## Roles and evidence

For **reference-informed engine-native** work, one engineer may study approved libraries, write
neutral pseudocode and implement, but must record consulted source and any reused expression. For
**source-independent** work, keep the avoided codebase out of the implementation workspace and
derive from papers/specifications. For **separated clean-room** work:

1. A specification team studies the approved materials and writes the implementation packet.
2. Counsel or the project's licence owner reviews what the packet may contain.
3. An implementation team that has not inspected the avoided source receives only the approved
   packet and oracle fixtures.
4. Review comments describe behavioural defects, not source-level similarities.
5. Preserve packet revisions, authorship, test results and the material-access record.

If the implementer has already read or translated the source being avoided, do not relabel the
work as clean-room. Escalate the process question instead of manufacturing provenance.

## Implementation workflow

1. **Identify the exact variant.** "Hydraulic erosion" is not implementable; Mei pipe, Beyer
   droplet and Braun–Willett stream power are. Resolve the `00` tier and version first.
2. **Consume the grounded specification.** Use the relevant algorithm chapter plus `22`; carry
   its adopted edge cases and deliberate deviations into the packet without asking the user to
   repeat the upstream research.
3. **Freeze field and unit contracts.** Height metres, drainage area m², slope rise/run, material
   thickness metres. Never let engine texture encoding become an algorithm unit.
4. **Write scalar CPU truth first.** Prefer obvious double-buffered code and deterministic
   traversal. It is the behavioural oracle for later SIMD/GPU versions.
5. **Pass synthetic oracles before visual terrain.** Flat, slope, cone, pit, basin, cross-tile
   river and extreme range come from `09`; add the family-specific signature.
6. **Optimise without changing the contract.** Move through SIMD, multithreaded CPU, then GPU.
   Compare every path to scalar truth with an explicit tolerance.
7. **Fit the engine runtime.** Replace library allocation, threading and whole-domain assumptions
   with engine resources, jobs/dispatches, streaming policy, cancellation and serialisation.
8. **Integrate as a typed pure node.** Declare locality, resolution policy, seed, boundaries and
   cache-key version (`14`).
9. **Retain the evidence.** Packet, paper/library source list, licences/notices, tests, benchmark
   inputs and review record stay with the source repository.

## Verification without dependency

An owned implementation must not depend on another library as its only proof. Use this order:

1. **Closed-form oracle** where one exists: diffusion single-mode decay, stream-power
   slope–area exponent, tephra exponential thinning, seafloor age–depth, Voellmy runout.
2. **Conservation/invariant:** no NaN/Inf, non-negative water/sediment, mass conservation,
   monotonic fill, deterministic seed, no height lowering during depression fill.
3. **Symmetry/signature:** cone remains radial, MFD reduces grid bias, dunes migrate, channels
   connect, long profiles are concave.
4. **Metamorphic test:** change resolution, tile layout, thread count or CPU/GPU path while
   preserving the world; only declared detail may change.
5. **Reference-library comparison:** compare outputs and edge cases with approved mature
   libraries in development tests. Keep the comparison versioned and explain disagreements;
   whether the library remains a test dependency is a project policy decision.

The numpy modules in `reference-impl/` are executable examples of these oracles. A strict
source-independent or separated process may regenerate equivalent fixtures from the equations
instead of exposing those modules to the implementation team.

The repository currently states no separate licence grant for `reference-impl/`. It is evidence
that the neutral algorithm contracts execute and pass their oracles, not an implied permission to
copy those Python files into a product. The engine implementation is written from the neutral
packet; code reuse requires an applicable project licence or explicit permission.

## Game-engine delivery

The production stack normally has four layers:

| Layer | Owned deliverable | Authority source |
|---|---|---|
| **Neutral specification** | Equations, edge cases, pseudocode and deliberate deviations | Algorithm chapter + pre-grounding ledger `22` |
| **Scalar truth** | Small deterministic CPU implementation and oracle tests | Algorithm chapter + `09` |
| **Production kernels** | SIMD/job-system CPU and HLSL/GLSL/Metal/compute implementations | Scalar truth + `15` |
| **Graph integration** | Typed node, cache/version key, preview policy, serialisation, diagnostics | `14`, `08` |

Do not ship Python/numpy as the terrain runtime merely because the executable specifications use
it. Port the contract into the engine's native stack. Keep CPU truth available in tools or tests:
GPU-only terrain code is difficult to debug, and a screenshot is not an oracle.

Translate runtime concepts explicitly rather than porting library structure:

| Reference-library assumption | Engine-native replacement |
|---|---|
| Whole-domain CPU array | Tiled/streamed resource plus an explicit GLOBAL-node bake path |
| Heap allocation per call | Persistent pools, render-graph or job-owned transient resources |
| Blocking function | Jobs or staged GPU dispatches with cancellation and progress |
| Host exception / NaN propagation | Validation status, debug counters and deterministic failure policy |
| Library object graph | Versioned node parameters and serialised field contracts |
| CPU iteration order | Declared deterministic reduction/buffering policy across CPU and GPU |
| Offline completion | T0–T3 budget, preview resolution and amortised checkpointing (`15`) |

Version the algorithm separately from the node UI. A numerical change that alters output gets a
new implementation version in the cache key and serialised graph, even if the node name stays
"Erosion". Old worlds must either retain the old implementation or migrate explicitly.

## Failure modes

| Failure | Why it breaks ownership or correctness | Fix |
|---|---|---|
| Translating an incompatible repository line-by-line | New syntax is not independent expression | Re-derive from the approved packet; reset roles if required |
| Porting the library's architecture | CPU arrays, allocators and blocking calls fight the engine | Preserve behavior; redesign lifetime, scheduling, GPU and streaming |
| Treating a paper's sample code as automatically licensed | Article access and code licence are separate | Record and review the code licence; exclude it if not approved |
| Calling reference-informed work clean-room | No evidence of information separation | Name the actual source boundary |
| Using a library output as the only oracle | Reproduces the library's defect and creates test dependence | Lead with analytic/invariant tests |
| Copying test fixtures from avoided source | Fixtures can carry expression and edge-case choices | Generate fixtures from equations and synthetic fields |
| GPU implementation first | Races and precision errors have no trusted baseline | Establish scalar CPU truth first |
| Omitting patent/data review | Source-code ownership is only one rights surface | Record the check and escalate conclusions to counsel |
| Removing attribution because code is owned | Papers still explain the algorithm and design lineage | Keep technical citations and required notices |

## Release checklist

- [ ] Source boundary named and approved
- [ ] Exact algorithm variant and provenance tier recorded
- [ ] Primary papers and approved library versions retained in the implementation packet
- [ ] Consulted, reused and excluded source materials recorded with required notices
- [ ] Code, data, shader, patent and trademark surfaces reviewed by the responsible owner
- [ ] Library-specific behavior is separated from the adopted algorithm contract
- [ ] Engine allocation, jobs, GPU resources, streaming, cancellation and serialisation specified
- [ ] Field units, boundaries, precision, determinism and locality declared
- [ ] Scalar CPU truth passes analytic, invariant and synthetic tests
- [ ] SIMD/GPU paths match scalar truth within a stated tolerance
- [ ] Resolution, tiling and thread-count metamorphic tests pass
- [ ] Reference-library comparison policy is explicit and approved
- [ ] Cache/serialisation version changes when numerical output changes
- [ ] Provenance packet and test evidence retained with the source
