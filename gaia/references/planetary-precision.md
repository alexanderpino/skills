---
type: Technique
title: Planetary precision — big coordinates in small floats
description: "Camera-relative rendering, reversed-Z depth, and cube-sphere patch frames: the numerical architecture any world past ten kilometres already needs."
tags: [rendering, rasterizer, precision, planetary, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: cozzi2011, tier: F, locator: "the precision, depth and horizon-culling chapters" }
  - { id: upchurch2012, tier: P, locator: "the depth-transform error analysis" }
  - { id: reed2015, tier: F, locator: "the float-depth/reversed-Z interaction walkthrough" }
  - { id: epiclwc, tier: F, locator: "Large World Coordinates — the shader-side limits section" }
---
# Planetary precision — big coordinates in small floats

**Tier: real-time rasteriser, and it starts long before planetary scale.** float32 has a 24-bit
significand: the gap between representable values at magnitude `x` is about `x · 1.2e-7`.

| Distance from origin | float32 spacing | Consequence |
|---|---|---|
| 1 km | ~0.1 mm | fine |
| 10 km | ~1 mm | sub-pixel shimmer in close-ups |
| 100 km | ~1 cm | visible vertex swimming, normal-map crawl |
| 1 000 km | ~12 cm | geometry visibly quantized, physics jitter |
| 6 371 km | ~0.76 m | unusable — vertices snap by strides |

An open-world game hits this on a flat map without ever leaving the ground. Half of what gets
reported as "planet renderer bugs" is this table with scenery attached.

## Use this

**Camera-relative rendering, with authoritative positions in float64 and exactly one truncation to
float32 per frame** [cozzi2011]. Compute `relPos = float32(worldPos_f64 - cameraPos_f64)` — the
subtraction happens in double, *then* truncates. The view matrix carries no translation; model
matrices are camera-relative. Near the camera, where precision matters, magnitudes are small and
float32 is exact enough; error grows with distance exactly where a pixel already covers metres.

**Applied structurally, it becomes the per-patch local frame.** Each terrain patch stores its
origin on the ellipsoid in double and its vertices as float32 offsets in a local east/north/up
frame. Per draw, upload `float32(patchOrigin_f64 - cameraPos_f64)` and add in the shader. The GPU
then never sees a planet-radius coordinate — which is why a correctly built planet renderer needs
no fp64 on the GPU at all.

**And reversed-Z into a float depth buffer, with an infinite far plane** [upchurch2012]. Map near
to 1 and far to 0. A standard projection piles depth resolution near the near plane hyperbolically
while float32 piles representable values near zero; reversing aligns the two gradients instead of
opposing them, giving near-constant relative error across the whole range [reed2015]. It is free —
flip the comparison, clear to zero — and it is the 2026 default everywhere, not a planetary
special case. With reversed-Z, taking the far plane to infinity costs essentially nothing; a
planet renderer should not be tuning a far plane.

⚠️ Reversed-Z buys almost nothing on a **fixed-point** 24-bit depth buffer. The gain comes from the
float exponent, not the flip.

**What it beats.** *Periodic origin rebasing* — shift the world when the camera passes a threshold;
easier to retrofit, but the rebase touches every cached world-space quantity (physics state,
particles, audio emitters, nav data) and one missed cache is a teleporting object. Legitimate as a
transitional step; do it on a quiet frame, never mid-physics-step. *GPU double-single emulation* —
positions as a (high, low) float pair with error-compensated subtraction; correct, and reserved
for vertices generated on the GPU in absolute coordinates where CPU-side camera-relative cannot
reach [cozzi2011]. *fp64 in shaders* — a trap; 1/16 to 1/64 rate on consumer parts. *Logarithmic
depth* — writing depth in the pixel shader disables early-Z and hierarchical-Z unless conservative
depth output is used carefully, and per-vertex log depth interpolates wrongly across long near
triangles; it is the pre-float-depth era's answer, reached for only when float depth targets are
unavailable. *Engine-native large-world support* [epiclwc] — the same doctrine, engine-side, and
it does **not** exempt content: any shader doing maths on absolute world position still breaks.

## Precision is an architecture, not a patch

Decide three things once, globally, and audit every path that bypasses them: the authoritative
coordinate type (f64 or int64 fixed-point), the frame each subsystem works in, and where the
double→float truncation happens. Name the frames, or drown in bugs:

| Frame | Definition | Used for |
|---|---|---|
| Planet-fixed | Origin at the planet centre, rotating with the planet | Authoritative positions (f64), tile addressing |
| Local ENU | East/north/up tangent frame at a reference point | Gameplay, physics islands, local terrain |
| Camera-relative | Origin at the camera, axes world-aligned | Everything on the GPU |

Two consequences that catch people:

- **Physics engines are float32.** Do not hand them planet-absolute coordinates. Run simulation
  islands with local origins, rebase islands as actors move, and convert to f64 planet-fixed only
  at the boundary. Far from the origin the contact solver operates below its tolerance floor:
  jittering ragdolls, contacts that pop.
- **Geodetic "up" is not geocentric "up."** On an ellipsoid they differ by up to about 0.19°.
  Use the geodetic normal for ENU frames, gravity and shading up, or buildings lean and water
  runs slightly uphill with latitude. On a sphere they coincide — decide sphere versus ellipsoid
  once, globally.

## Drawing a globe: cube-sphere, and where its seams are

Renderers draw planets as six cube faces, each an independent quadtree projected to the
ellipsoid — because renderers want quads, per-face 2D parameter spaces, mip chains and texture
pages. A simulation lattice may be icosahedral or hexagonal; **do not couple the render lattice to
the simulation lattice.** Declare the resample as part of the bake.

- **Mapping.** The naive gnomonic cube→sphere mapping varies texel solid angle by roughly 5× from
  face centre to corner. A tangent-adjusted mapping (`u' = tan(u·π/4)` per axis) cuts that to
  around 1.3–1.4×. Pick once, bake it into tile addressing, and use the *same* mapping for
  geometry and texturing — a mismatch shows as texture swimming toward the corners.
- **Tangent frames rotate across the 12 cube edges, and at the 8 corners three faces meet with no
  consistent parameterization** — the hairy-ball theorem guarantees a singularity somewhere, and
  the cube puts it at the corners. Express normals, anisotropy and detail-UV directions in a
  world or local ENU frame, or carry explicit per-edge rotation tables. The symptom of getting it
  wrong is lighting seams exactly on cube edges and pinwheels at corners.
- **UV precision runs out before the pyramid does.** A face parameterized 0–1 in float32 dies
  around level 23–24. Make UVs patch-local with the offset and scale kept in double on the CPU —
  the same structural fix as positions.
- **Skirts extend toward the planet centre**, not world −Z, and must cover the chord-versus-arc
  error of flattening a curved patch as well as the LOD gap.

**Horizon culling is the cheapest large cut you will ever add** [cozzi2011]. Scale space so the
ellipsoid is the unit sphere, let `cv` be the camera in that space, and for a target point `t`:

```
vc = -cv                                          // camera to centre
vt = t - cv                                       // camera to target
occluded =  dot(vt, vc) > dot(vc, vc) - 1                        // beyond the horizon plane
         && dot(vt, vc)^2 / dot(vt, vt) > dot(vc, vc) - 1        // inside the occlusion cone
```

At surface level this kills nearly half of what the frustum keeps — the frustum happily contains
the far side of the planet through the ground. Run it *before* frustum and error tests. Use the
patch's *maximum* height so peaks over the horizon survive, and the ellipsoid minus the deepest
depression as the occluder radius, or valleys get culled while still visible. Terrain occluding
terrain is a different mechanism; see `gpu-driven-culling.md`.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Geometry wobbles as the camera moves, far from origin | fp32 world-space maths; view = big − big cancels the low bits | Camera-relative rendering; subtract in double, truncate once |
| Jitter returns on one subsystem only — decals, particles, vegetation | Middleware composed its own float32 world matrix from f64 positions | Audit every matrix build site; grep for float casts of authoritative positions |
| Shadows crawl on a completely static scene | Shadow matrices built in absolute coordinates | Same frame discipline in the shadow path as the main view |
| Z-fighting on distant terrain and at the horizon | Depth precision exhausted: standard-Z with a far plane | Reversed-Z, float depth buffer, infinite far; check clear values and comparison functions everywhere |
| Reversed-Z made no difference | A fixed-point 24-bit depth buffer — the gain was in the float exponent | Use a floating-point depth format |
| A one-frame depth-test flicker on ascent | Near plane moved discontinuously between regimes | Slide the near plane smoothly, or render in two depth partitions |
| Lighting seams exactly on cube-face edges, pinwheels at the corners | Per-face tangent bases used directly across a face boundary | Express directions in an ENU/world frame, or apply per-edge rotations |
| Texture swims toward face corners | Geometry and texturing used different cube→sphere mappings | One mapping, baked into tile addressing |
| Deep zoom quantizes UVs around level 20+ | Absolute face-wide UVs in float32 | Patch-local UVs with a double offset on the CPU |
| Valleys culled while still visible | Horizon test used the ellipsoid radius, not the deepest depression | Occluder radius = ellipsoid minus max depression; test with patch max height |
| Ragdolls jitter, contacts pop, only far from the origin | Physics fed planet-absolute float32 coordinates | Simulation islands with local origins; convert at the boundary |
| Parked objects drift on a rotating planet | Physics run in an inertial frame while the surface accelerates | Simulate in the planet-fixed frame; rotate the frame, not the objects |
| Everything works in the demo | The demo runs at (0,0,0) | Verify by teleporting to the antipode, soaking at max coordinate, and cycling orbit→surface→orbit |
