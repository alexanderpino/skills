# ADR 001 — Compose pipe and droplet erosion on WebGL2

**Status:** accepted
**Date:** 2026-07-30

## Context

The Hydraulic node previously exposed a hardware-dependent choice: square WebGL2 terrain used the
virtual-pipe model, while the particle/droplet model was a CPU scatter loop. The models produce
meaningfully different landforms, so hardware was silently changing authored output. Running both
models also required a CPU round trip between them.

WebGL2 fragment shaders cannot perform arbitrary floating-point atomic writes. Droplet erosion needs
overlapping particle brushes, while the existing synchronous graph evaluator cannot adopt an
asynchronous WebGPU compute boundary without a broader evaluator change.

## Decision

- Expose Pipe / grid and Droplet / particle as independent, serialised switches with separate,
  collapsible parameter panels.
- When both are enabled, use the fixed order **Pipe → Droplet**.
- Keep the pipe state in `RGBA32F` ping-pong textures.
- Keep droplet position/direction and speed/water/sediment in GPU particle textures. Update particles
  through multiple render targets, rasterise their signed terrain actions as additive point sprites
  into a float delta texture, then apply that delta in a gather pass.
- Treat droplet lifetime as a numerical work cap, not a physical settling event. Apply only
  capacity-driven deposition during integration. Never dump every surviving particle's remaining
  sediment at its terminal position.
- Report the heightfield deficit at truncation as the derived aggregate `exportedOrSuspended`. This
  deliberately names both open-boundary export and sediment still suspended when the work budget
  expires; WebGL2 cannot itemise those terms without another reduction/readback.
- Bound each GPU scatter batch to 0.1 particle per terrain cell. Complete one cohort before starting
  the next so later paths sample terrain containing earlier actions. Above 0.5 particle per cell,
  scale the represented water parcel inversely with density so capacity, sediment state, and terrain
  actions remain one budget. Clamp particle speed to bound the next-step capacity feedback.
- Spawn droplets far enough inside the field for the complete erosion brush and export them before
  that brush would become partial at the edge.
- Pipe transport capacity uses a signed downhill outlet, vector transport speed, and a shallow-water
  ramp. A local minimum has zero erosive capacity rather than being treated as a steep slope.
- Run pipe state on a bounded border-replicated continuation apron with an explicit no-flux wall at
  its outer edge, then crop the simulated result. Do not crossfade terrain output.
- In the combined path, pass the pipe height texture directly to the droplet stage and read back only
  the final heightfield.
- Require square-lattice WebGL2 float render targets plus `EXT_float_blend` for GPU droplets. Show the
  device path in the inspector. Retain the existing CPU compatibility path for unsupported contexts
  and hexagonal terrain.
- Treat the old `engine` parameter as saved-document migration data. New documents serialise the two
  switches and their model-specific controls.

## Consequences

Both hydraulic mechanisms now run on the GPU in the supported authoring viewport, can be composed in
one node, and incur one final readback. Disabling both is a passthrough. Panel expansion is UI-local;
switch changes participate in graph history and invalidation.

The GPU droplet solver is deterministic for the same seed on the tested device. Cross-vendor
bit-identical output is not promised because additive floating-point blending may accumulate in a
driver-dependent order; finite output, erosion/deposition, a named truncation budget, terrain-shape
bounds, and same-device seeded repeatability are gated. The CPU and hex fallbacks remain visibly
labelled rather than pretending they are the GPU path, and use the same no-forced-terminal-deposit
policy for the authored Droplet stage.

Two rejected particle schedules produced distinct failures:

1. Settling all surviving particles in one synchronized terminal pass generated narrow sediment
   cones. On the 96² fixture it produced 53 peaks above 0.02 local prominence (maximum 0.100287);
   the fixed path produces 0 (maximum 0.018229). At 192²/18k, the count falls 154 → 0 and maximum
   prominence 0.098667 → 0.006561.
2. Running every particle as one stale-read scatter batch was stable at some densities but crossed
   a sharp feedback threshold: at the real 512² Interactive scale, 30k UI particles become 120k GPU
   particles and produced finite terrain values around 10²¹. Cohorts plus weighted water parcels keep
   the reported 14,389 × 71 case and the 60k UI / 240k actual maximum finite, with zero peaks above
   0.02. Particle count above the saturation point now changes sampling convergence, not strength.

The pipe had two separate mechanisms. The old outside head `edgeBed - 0.03` forced an erosion trench.
The capacity law then used the absolute difference to every neighbour, so an already-low cell was
classified as a steep erodible slope and could deepen on every iteration. A post-output fade was
rejected: it made the outer-ring test tautological and violates the rule that transport boundaries are
solved, not cosmetically blended. The current solver uses signed downhill capacity and a cropped
continuation apron. At 279 authored iterations / Deposit 0.48, its 39-cell apron measures edge
p99/max slope 0.00384/0.00454 versus 0.00749/0.00849 on the input.

The verifier injects known positive and negative spikes to prove both detectors are armed and gates
finite values, absolute height change, local prominence, local pit depth, local slope, padded mass
closure, boundary continuity, the actual resolution-scaled particle counts, and the reported combined
Pipe 279 → Droplet 57,670 × 48 workload. It also starts the inspection camera below the open
heightfield and verifies the renderer guard moves it above the solid-surface maximum.

WebGPU compute was rejected for this change because it would introduce an asynchronous runtime and
capability boundary throughout the current synchronous evaluator. A CPU loop hidden behind a GPU
label and a forced choice between the two physical models were also rejected.
