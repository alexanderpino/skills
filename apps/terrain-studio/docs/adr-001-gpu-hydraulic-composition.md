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
driver-dependent order; finite output, erosion/deposition, mass closure, and same-device seeded
repeatability are gated. The CPU and hex fallbacks remain visibly labelled rather than pretending
they are the GPU path.

WebGPU compute was rejected for this change because it would introduce an asynchronous runtime and
capability boundary throughout the current synchronous evaluator. A CPU loop hidden behind a GPU
label and a forced choice between the two physical models were also rejected.
