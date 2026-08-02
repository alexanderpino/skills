# ADR 010 - Walkaround traversal inspection and reachability

**Status:** accepted
**Date:** 2026-08-02
**Affects:** Sprint 9 streaming, Sprint 10 runtime heightfield, tool viewport

## Context

Terrain authors need to inspect a generated world at human scale and determine whether intended
areas are actually traversable. Orbit, pan, zoom, and flight cameras cannot answer whether a slope
can be climbed, a ledge can be jumped, a route is disconnected, or streamed collision has a hole.
The required interaction is analogous to placing the person marker in Google Street View: drag or
activate a doll tool, drop it onto visible terrain, and enter a grounded first/third-person
walkaround mode with walk, run, and jump. There is explicitly no flight mode.

ADR 009 forbids CPU terrain-field evaluation and whole-raster CPU materialization in high-resolution
mode. It does not prohibit a bounded local gameplay collision representation. A character controller
cannot depend on asynchronous WebGPU readback every fixed step without adding latency and stalls.
The renderer and collision systems therefore consume the same versioned height pages through
different bounded representations.

## Decision drivers

- Place the inspector directly on visible terrain with a clear Street-View-style doll interaction.
- Provide grounded walk, run, and jump only; never six-degree flight or noclip.
- Make movement deterministic and independent of render frame rate.
- Never fall through a missing streamed page or walk on stale collision.
- Measure reachability under the same locomotion profile used by the controller.
- Work on arbitrary dimensions and 16K/large streamed worlds without whole-world collision.
- Use a proven physics/controller library rather than hand-rolling collision resolution.

## Decision

### Tool interaction and modes

The viewport has two explicit modes:

- **Inspect**: current orbit/pan/zoom authoring camera.
- **Walkaround**: grounded character inspection. It has no ascend, descend, free-fly, noclip, or
  vertical camera-translation control.

A familiar person/doll icon is a draggable viewport tool and keyboard-accessible command. While
dragging, the viewport raycasts the rendered authoritative terrain and shows valid/invalid placement.
Dropping on a valid, collision-resident point places the capsule feet on the authoritative surface,
orients it along the projected camera heading, and enters Walkaround. Dropping over water, outside
the domain, on an incompatible visual-only displacement, or where collision is not ready is rejected
with a named reason. A pending page request may complete placement later only while the same drag
intent remains current.

Escape exits to Inspect at the last authoring camera. Reset returns the doll to its drop point. The
walkaround camera supports first-person and optional close third-person follow, but both use the same
controller state. Orbit controls cannot move the character.

### Controller and collision

Use the maintained `@dimforge/rapier3d-compat` WASM package, pinned and license-reviewed at
implementation kickoff, for capsule shape casts, contact resolution, grounded state, slopes, steps,
and a kinematic character controller. Do not implement a custom collision solver.

Movement runs at fixed 60 Hz with an accumulator and bounded catch-up count. Render frames
interpolate the previous/current controller pose. Input is snapshotted per fixed step. Walk and run
produce horizontal desired velocity; jump is an impulse/state transition allowed only by the
authored locomotion profile's grounded/coyote policy. Gravity always applies. The controller exposes
no vertical velocity command other than jump and gravity.

`LocomotionProfile/1` is authored/persisted and shared by controller and reachability:

```text
capsuleRadiusM, capsuleHeightM
walkSpeedMps, runSpeedMps
jumpApexM | jumpTakeoffSpeedMps
gravityMps2
maxWalkSlopeDeg
maxStepUpM, maxStepDownM
groundSnapM, skinWidthM
coyoteTimeS
```

Defaults are product look/feel inputs calibrated before implementation; they are not claimed as
physical constants. Hard validation requires finite positive dimensions/speeds/gravity, a slope in
`[0, 90)`, and non-negative step/snap/skin/coyote values.

Collision is a separately budgeted, pinned ring of versioned heightfield collider tiles around the
doll, built from the same authoritative `surfaceVersion`, posting, valid rectangles, shared posts,
and physical metre frame as rendering. It may hold bounded local sample data required by Rapier but
never the complete raster. Terrain processing remains WebGPU-only under ADR 009: CPU/WASM collision
consumes completed authoritative page values and does not generate, filter, erode, resample, or
otherwise transform terrain.

Collision tiles include a neighbour apron sufficient for capsule/step queries. Shared vertices are
copied exactly. A new surface version builds collision asynchronously and atomically swaps complete
tiles; stale tiles are visibly labelled and cannot become authoritative after supersession. The
controller may move only where the current collision ring covers the swept capsule plus braking
distance. At the ring boundary or a missing tile, movement is clamped against a temporary blocker
and loading is shown. Falling through or tunnelling into unloaded terrain is forbidden.

### Reachability analysis

The author can set a target marker or paint an analysis region from Walkaround or Inspect mode and
run **Traversal Reachability**. The result is not a generic navmesh claim; it is explicitly tied to
one `LocomotionProfile/1`, one `surfaceVersion`, and one analysis resolution.

WebGPU computes a bounded traversal graph over the selected region/page set:

1. derive finite walkable samples from authoritative height, slope, valid-domain mask, water/solid
   policy, and capsule clearance where obstacle data exists;
2. add walk/step edges that satisfy slope, `maxStepUpM`, `maxStepDownM`, and capsule sweep clearance;
3. add bounded jump edges only when a fixed-step ballistic arc under the profile clears terrain and
   lands on a walkable sample;
4. flood/compact from the drop point or selected start and emit reachable state, predecessor,
   traversal type, cost/distance, and rejection reason.

The analysis is page-bounded and cancellable, streams in required pages, and never allocates a
world-sized CPU graph. CPU reads only bounded summary/path records requested for display. Large or
whole-world analysis proceeds in budgeted page waves and reports partial/complete status honestly.
Changing terrain or the locomotion profile invalidates the result by content identity.

The viewport overlays reachable/unreachable regions, the selected route, walk/step/jump segments,
and named blockers (`slope`, `step`, `gap`, `water`, `clearance`, `domain-edge`, `missing-page`). A
successful path can be replayed through the actual fixed-step Rapier controller; analysis and replay
must agree within the authored path corridor. The tool does not claim AI navigation for arbitrary
dynamic obstacles.

### Streaming and rendering

Walkaround pins render and collision ancestors around the character and predicts pages from run
speed, jump envelope, and braking distance. Collision has priority over visual refinement. The
viewport may render a coarse resident ancestor, but collision and displayed authoritative ground
must name the same `surfaceVersion` and stay within a declared vertical error. If that cannot be
met, movement pauses rather than using a visually different surface.

Camera-relative precision remains in force. The controller's authoritative world position is
Float64 at the application boundary; the local Rapier world is rebased around streamed collision
tiles before Float32 precision becomes visible. Rebase preserves velocity, grounded state, and
contacts deterministically.

## Consequences

- Walkaround is an inspection/gameplay-quality feature, not another free camera.
- A bounded CPU/WASM collision ring is an explicit exception to "no CPU terrain work": it consumes
  completed local height samples for physics but performs no terrain generation or whole-field work.
- Rapier adds a runtime dependency and WASM asset; production/PWA offline caching and license review
  become acceptance requirements.
- Reachability is reproducible and profile-specific rather than inferred from slope colors alone.
- Dynamic obstacle navigation, crouch, mantle, climb, swim, fall damage, and multiplayer are outside
  this story unless added later.

## Required gates

- Doll drag/drop and keyboard placement hit the same authoritative point; invalid placement reasons
  are asserted and empty hit sets are red.
- Fixed-step replay is identical across 30/60/144 Hz render schedules for the same input snapshots.
- Walk/run speed, jump apex/time, gravity, slope rejection, step up/down, ground snap, head/side
  collision, and landing are measured against analytic fixtures.
- No input sequence can ascend without supporting collision except during the bounded jump arc; no
  flight/noclip command or vertical translation binding exists.
- Missing/stale collision clamps movement; teleports, page eviction, edits, and device loss never
  produce a fall-through or stale collider promotion.
- Reachability fixtures cover connected ramps, over-slope barriers, step limits, jumpable and
  unjumpable gaps, water policy, narrow clearance, domain edges, and partial pages. Every result has
  non-zero visited counts and named rejection evidence.
- Every reported reachable route replays successfully through the controller; deliberate mutation
  of slope, step, or jump policy makes the corresponding route red.
- `16384 x 16384` and `1573 x 13789` worlds keep bounded render/collision/analysis residency and
  never materialize whole-world CPU collision or traversal graphs.
- Built PWA works offline with the pinned Rapier WASM asset and desktop/mobile controls do not expose
  flight.

## Grounding

- Terrain Renderer streaming contract: collision streams separately, coarser, pinned, and is never
  gated by render LOD; camera-relative precision and complete ancestors remain mandatory.
- Game Engine Physics & Jobs: fixed-step physics, broad-phase before narrow-phase, immutable input
  snapshots, deterministic replay, and deferred streaming updates.
- Terrain Architect chapters 08/14/15: physical metre-space fields, bounded pages, cancellation,
  CPU/GPU placement, and no silent semantic fallback.