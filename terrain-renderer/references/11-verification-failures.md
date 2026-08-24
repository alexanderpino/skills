---
type: Reference
title: "Verification, profiling & the failure catalogue"
description: "Verification, profiling and the failure catalogue: how each mechanism in this skill is checked, and the symptoms that say it is not."
tags: [terrain, verification, profiling, failures]
status: stable
generated: { by: process:claude-code, at: 2026-08-23T18:35:25Z }
---
# Verification, profiling & the failure catalogue

Terrain rendering is judged by eye at 60+ fps, which makes it uniquely vulnerable to **plausible
wrongness in motion**: a still frame that looks fine while cracks sparkle, LODs pop, and shadows
swim the moment the camera moves. This chapter is the review-and-debug authority for the whole
skill: every defect routes through the catalogue below as **symptom → mechanism → minimal fix**,
and every claim of correctness must survive a control test and a budget assertion — the same
discipline as terrain-architect `09`, applied to the renderer.

Contents: [Failure catalogue](#the-failure-catalogue) · [Metrics & budgets](#metrics--budgets) ·
[Test controls](#test-controls) · [Debug view modes](#debug-view-modes) ·
[Profiling method](#profiling-method) · [Regression testing](#regression-testing) ·
[Review checklist](#review-checklist) · [Sources](#sources--provenance)


## This chapter now applies to the skill that contains it

For twenty chapters this file told the reader to specify tests before implementation while nothing
in the skill was tested. That is the ninth way a verification fails — *the code no pixel reached* —
applied to a whole body of doctrine, and it had already cost something: the ring-residency column
of `06`'s worked example was wrong by about fifty tiles, and it was found by adding it up rather
than by reading it.

`reference-impl/validate_terrain.py` guards the arithmetic now: 30 rows over screen-space error and
its inverse, the CDLOD morph shortfall, the 2:1 crack contract, the clipmap scroll invariant, the
isosurface case analysis and the residency budget. Three tiers, every tolerance justified from the
estimator's own error, and `--bugs` re-runs the whole suite once per deliberately reintroduced
defect — currently **6 of 6 caught**, including the factor-of-two in the field-of-view halving and
`floor` for `ceil` in the HiZ mip rule.

⚠️ **It guards arithmetic, and nothing else.** There is no GPU behind it, so every claim in this
skill about throughput, bandwidth, driver behaviour or how a technique *looks* remains unguarded
practice with a provenance tier. The suite's honesty depends on saying which is which, which is
this chapter's own first rule.

**One row failed on its first run, and the fix is the point.** The mip-chain ratio cannot reach
`4/3` exactly, because tile sizes are integers and the byte count rounds. The tolerance is now half
a byte over the base — derived from the rounding — rather than widened until the row went green.
Widening is the move this chapter exists to name: it converts a finding into a decoration, and
`-v` prints every justification so the move is visible in a diff.

## The failure catalogue

Diagnose from the symptom column; the mechanism tells you *why* so you don't fix the wrong layer;
the minimal fix is deliberately minimal — do not rewrite the LOD system for one misconfigured
bias. Grouped by family. Everything here is reproducible with the controls in the next section;
a defect you cannot reproduce under a control is not yet diagnosed.

**Triage by discriminator before opening the table.** Three cheap questions cut the catalogue to a
handful of rows:

- **Still or motion?** Artifacts invisible in a screenshot but present in motion (sparkle, swim,
  shimmer, crawl) are temporal by nature: T-junctions, morph impurity, cascade snapping, normal
  aliasing, HiZ convention bugs. Artifacts present in a still are structural: cracks, seams,
  halos, banding, acne.
- **Distance-dependent?** Appears only in a distance band → LOD boundary machinery (morph range,
  adjacency, mip selection). Appears only far away → precision (`09`) or aliasing (`10`). Appears
  only close → detail-layer material or texel density (`07`).
- **Which pass?** Toggle passes off one at a time. Vanishes with shadows → `10` family. Vanishes
  with the depth prepass → cross-pass geometry mismatch. Vanishes with a screen-space effect →
  skirts/apron family. Survives everything on a flat plane → the pipeline itself, not content.

Then confirm against a control. The most common review failure is fixing the *symptom's location*
rather than its mechanism — biasing shadows to hide an LOD mismatch, welding vertices to hide a
missing boundary contract. Every such fix resurfaces under a different camera.

### Geometry & LOD

| Symptom | Mechanism | Minimal fix | Route |
|---|---|---|---|
| Hairline cracks / background pixels at chunk borders, often only at specific distances | LOD boundary contract violated: morph factor not exactly 1.0 at the range boundary, missing edge-permutation IB, or adjacency constraint (≤1 level) slipped | Enforce the crack contract at the boundary; assert adjacency; sweep the full distance range | `01` `05` `06` |
| Holes at LOD borders in voxel/isosurface terrain | Transition cells between resolutions absent or wrong-signed; two meshers disagree on the shared face | Stitch with the scheme's transition mechanism, never post-weld | `05` |
| Single-pixel shimmer along straight LOD seams (T-junction sparkle) | Vertex lies *on* the coarse edge but the edge is a different edge equation — watertight raster only holds for shared-vertex edges | Remove the T-junction structurally (stitch/morph/conforming subdivision); do not nudge positions | `01` |
| Geometry pops on LOD switch | Discrete LOD change with no morph or cross-fade | Geomorph from parent-LOD position, or dithered cross-fade under TAA | `01` |
| Vertices swim/jitter at large distances from origin | fp32 world-space positions beyond ~10-100 km; morph lerp amplifies quantized endpoints | Camera-relative rendering; chunk origin carries the large translation | `09` |
| Vertices swim only in the morph band | Morph factor a function of frame state, not (vertex, camera); or height not re-sampled at morphed position | Make morph a pure function of vertex+camera; re-sample height after morph | `01` |
| Geometry visibly pops in at screen edge while panning | Culling bounds not inflated for displacement/skirts/geomorph excursion | Conservative bounds with a named inflation term per contributor | `08` |
| Terrain silhouette differs between depth prepass and base pass (Z-fighting, TAA ghosting, decal misses) | LOD/morph selected independently per pass — two passes drew two different meshes | One LOD selection result per frame, shared by every pass | `01` `08` |
| Objects float/sink on distant terrain | Physics samples authoritative heightfield, render shows simplified LOD; divergence up to the error bound `e` | Bound `tau` where gameplay happens; match collision triangulation (incl. diagonal) to render grid | `01` |
| Non-manifold / flipped isosurface output (holes, inside-out patches) | Mesher case table or sign convention broken; ambiguous cases unresolved | Validate mesher against the case-table oracle before blaming LOD | `05` |
| Voxel edit visible only after a long delay | Remesh scheduled behind a full queue; upload waits on the render thread | Prioritize dirty-near-camera; async upload with fence, never same-frame stall | `04` `05` |

### Shadows & lighting

| Symptom | Mechanism | Minimal fix | Route |
|---|---|---|---|
| Shadow acne (surface stripes) on terrain | Depth bias smaller than shadow-map texel's world footprint on slopes | Slope-scaled bias sized to texel world size per cascade | `10` |
| Peter-panning (shadows detach from bases) | Bias overcorrected; or caster geometry (skirts) pulled from shadow pass | Reduce bias toward the texel-size bound; keep casters consistent | `10` |
| Far-cascade terrain alternates between acne and detached shadows no matter how bias is tuned | The cascade covers kilometers, so one shadow texel spans too much world space; no bias can preserve both contact and self-shadowing | Stop tuning the impossible cascade: bound CSM to near/mid field and use VSM pages or heightfield ray-marched/horizon shadows for the far field | `10` |
| Shadows shimmer/crawl as camera moves | Cascade frustum re-fit each frame without snapping projection to texel grid | Snap cascade origin to texel-size increments; stabilize cascade extents | `10` |
| Self-shadow banding that tracks LOD morphing | Shadow pass renders different LOD/morph than main view — depth mismatch oscillates with morph factor | Same geometry (same selection + morph) in shadow and main passes | `01` `10` |
| RT shadows/reflections pop when raster terrain changes LOD | RT BLAS follows raster topology or stale proxy bounds while the raster path geomorphs | Use a stable triangulated RT proxy or procedural AABB heightfield intersection; never camera-drive full BLAS rebuilds | `18` |
| Distant slopes sparkle/glitter in motion | Normal/specular aliasing: full-frequency normals + tight specular under-sampled at distance | Roughness-encoding normal mips (vMF/Toksvig-style specular AA) | `10` |
| Dark seams tracing chunk edges in AO/fog/screen-space passes | Skirt curtains visible to screen-space techniques; or normal/AO bake lacks cross-chunk apron | Exclude skirts from those passes or switch crack strategy; bake with apron | `01` `07` |
| AO/normal discontinuity exactly at tile borders | Per-tile bakes computed without neighbor apron — derivative kernels read the tile edge clamp | Re-bake with apron ≥ kernel radius | `06` `07` |
| Z-fighting on distant terrain / at the horizon | Depth precision exhausted: standard-Z with distant far plane | Reversed-Z + float depth; verify projection & clear conventions everywhere | `09` |

### Materials & texturing

| Symptom | Mechanism | Minimal fix | Route |
|---|---|---|---|
| Obvious tiling repetition on large surfaces | Single detail tile at one frequency; eye locks onto the repeat | Stochastic/hex tiling or multi-frequency blend; verify in the distance view | `07` |
| Dark/wrong-hue halos where splat layers meet, worse in mips | Weights and albedo mipped independently — non-premultiplied blend averages through zero-weight texels | Premultiply layer weights before mip generation (or blend in a premultiplied domain) | `07` |
| Blurry patches that sharpen visibly after a beat (VT page pop-in) | Feedback→request→upload latency; fallback mip shown meanwhile | Prefetch by camera velocity; verify feedback loop latency budget, not just correctness | `07` |
| Global season or rain transition causes a multi-frame RVT update spike | Time-varying season/wetness/snow was baked into cached pages, so one global parameter dirtied the world | Remove dynamic state from RVT; sample stable base composition, then apply season/weather as a post-RVT overlay | `07` `13` |
| Texture detail wrong only on steep slopes | Planar UVs stretched; triplanar absent or blend too narrow | Triplanar (or slope-projected) sampling with adequate blend width | `07` |
| Terrain color/normal detail pops with mesh LOD | Material inputs derived from current-LOD geometry (normals, slope masks) | Sample generator-baked maps at fixed resolution, independent of mesh LOD | `01` `07` |

### Streaming & residency

| Symptom | Mechanism | Minimal fix | Route |
|---|---|---|---|
| Frame hitches while moving through the world | Synchronous IO/decompress on a critical thread, or full-tile GPU upload in one frame | Async IO + budgeted per-frame upload slicing; assert worst-frame upload bytes | `06` |
| World visibly assembles after teleport | Cold start: nothing resident, all requests issued at once at equal priority | Priority by projected screen size; prefetch on teleport intent; budget the storm | `06` |
| Distant tiles never sharpen / stuck at low LOD | Feedback or request loop drops entries silently (overflow, recycled IDs) | Counter every drop; key requests by stable tile ID | `06` `08` |
| Chunks flicker between two LODs / requests oscillate | No hysteresis on a threshold-driven state | Split/merge thresholds separated by a hysteresis band | `08` |
| One-frame disappearances at silhouettes under motion | HiZ reduction convention wrong for the depth convention, or NPOT edge texels dropped | Fix reduce op (reversed-Z → min) and odd-dimension gather | `08` |
| GPU idle bubbles correlated with streaming | CPU maps an in-flight readback/upload buffer synchronously | N-deep ring, consume N frames late, never wait | `08` `06` |
| Overdraw spikes in valleys/water areas | Deep skirts, stacked transparency (water + decals), or dense cluster overlap | Overdraw heat view; shrink skirts to max-error depth; restrict transparent extents | `01` `08` |

### Dynamic surface & population

| Symptom | Mechanism | Minimal fix | Route |
|---|---|---|---|
| Waterline crawls/aliases as camera moves | Water surface LOD/tessellation cadence differs from the terrain tile LOD beneath; hard depth intersection | Depth-fade shore blend; align water and terrain LOD selection at the intersection band | `12` `06` |
| Water ghosts/smears under TAA | Fullscreen-triangle/analytic water writes no motion vectors | Output analytic velocity (reproject the previous frame's plane/ray hit) | `12` |
| Ocean tiling visible from altitude | A single FFT cascade's wavelength repeats across the view | 2-4 cascades at different world sizes + macro variation and foam breakup | `12` |
| Surf hits the beach diagonally at the wind angle | Deep-water cascades run unmodified to depth 0; no refraction cue | Depth-attenuate ambient waves and add a shore-wave band with refracted (travel-time/shore-aligned) phase | `12` |
| Offshore sandbars/reefs stay glassy while the beach breaks | Shoaling/breaking keyed to shore distance instead of depth | Key shoal gain, break mask, and travel-time phase off the filtered bathymetry field | `12` |
| Whole coastline breaks in metronome unison | Single global wave period/phase drives the shore band | Superpose 2-3 periods with a group envelope; jitter phase along-shore | `12` |
| Foam crawls up cliff faces like a beach break | Break mask fired on depth alone with one breaker type everywhere | Gate breaker type by the beach-slope/breaker-class mask (surging shores don't spill) | `12` |
| Surf crosses a river mouth unchanged; rip currents leave no lanes in the breaker line | Shore-wave band reads only depth; the exported flow field never modulates waves | Doppler-style opposition modulation: steepen/force-break against opposing flow, flatten with following flow | `12` |
| A wall of grass pops in at a fixed radius | Generation-radius cutoff with constant density to the edge | Staggered per-instance fade + density pre-rolloff approaching the radius | `15` |
| Props/grass float or sink at distance | Instances seated on the source heightfield while terrain renders a morphed/displaced LOD | Seat instances by sampling the same displaced/morphed height the terrain vertex path produces | `15` `01` |
| Road edges z-fight or hover after terrain LOD changes | A coplanar ribbon mesh relies on depth bias and samples a different surface than the terrain material | Integrate the road through conforming geometry or RVT/material injection; reserve bias for bounded residual overlap | `17` `07` |
| Snow/wetness on the ground but not on vegetation | State overlays sampled only by the terrain material — two weather systems | Sample the `13` state layers in vegetation (and prop) shaders too | `13` `15` |
| Snow under overhangs and cave mouths | Accumulation mask lacks top-down occlusion capture | Gate accumulation by a top-down occlusion target (same machinery as deformation capture) | `13` |
| Puddles on ridgelines and slopes | Wetness applied without curvature/flow gating | Drive puddles from the generator's curvature/flow/wetness maps, never raw rain intensity | `13` `14` |
| Deformation trails seam or snap on camera motion | Camera-following state window re-centers by non-texel offsets, or discards retained texels | Texel-aligned toroidal window scroll with retained-region copy | `13` |
| Footprints unexpectedly change collision, or a gameplay crater changes only the pixels | Cosmetic and authoritative deformation channels share storage without an ownership contract | Split GPU-only transient deformation from CPU/server-owned height deltas; replicate/version only the authoritative channel | `13` `17` |
| Persistent decals/scorch vanish sporadically | VT-injected stamps evicted with their pages and never re-applied | Keep a stamp replay list; re-apply on page (re)load | `17` `07` |
| Player falls through a fresh crater | Collision commit lags the visual height delta | Commit the collider before or with the visual delta; gate gameplay effects on collider version | `17` |
| Ground darkens to mud-black in rain | Wetness darkening × baked AO × decal/shadow terms multiply unbounded | One declared compositing order; clamp combined darkening | `13` `14` `07` |
| Rain or snow particles appear inside caves | Precipitation VFX ignores terrain/scene coverage and treats terrain as the particle owner | Keep particles in VFX; consume terrain-provided depth/top-down occlusion to reject covered regions | `13` `14` |

## Metrics & budgets

A renderer without numeric budgets cannot regress-test and cannot review. Set per platform tier,
assert in capture tests (below). The bands are starting points, not physics — but *having* the
band is non-negotiable.

| Metric | Target band | Notes |
|---|---|---|
| Pixels per triangle (main view) | ~4-16 px/tri classic raster; ≲1 px/tri only on virtualized geometry (`02`) | Below ~4 px/tri on fixed-function raster, quad overshading dominates — either coarsen `tau` or move to the visibility-buffer path (`08`) |
| Draws + dispatches, terrain total | O(passes), not O(chunks) — tens, not thousands | Thousands means GPU-driven submission (`08`) isn't actually on |
| GPU time, bucketed | Per pass: prepass/main/shadow-per-cascade/culling/VT feedback; each with its own budget | One "terrain" bucket hides every regression; culling compute creeping past ~0.3-0.5 ms deserves a look |
| Streaming bandwidth | Steady-state MB/s and worst-frame upload bytes; resident-set curve vs camera speed | The *curve* matters: resident set must plateau, not grow, on a soak (`06`) |
| Remesh latency (voxel) | Percentiles, edit→visible: p50 and p99 in frames | Report p99 — the p50 is always fine (`04` `05`) |
| VT feedback→resident latency | Frames from first request to page resident, p50/p99 | Perceived pop-in is this number, not cache hit rate (`07`) |
| Triangle count vs `tau` | Monotonic: halving `tau` should ≈ quadruple triangles | Non-monotonic response = the error metric is lying somewhere (`01`) |

Budgets are only meaningful against the **worst-case view** (see Profiling method) — an average
frame passes every budget while the vista frame ships broken.

**Assert budgets mechanically.** The vehicle is a capture test: replay a fixed camera path, sample
counters per bookmark, compare against the platform tier's table. Sketch:

```
for bookmark in vista_bookmarks:                  // worst-case views, not tourist shots
    warm(bookmark, frames=N_warmup)               // streaming + TAA history settle
    s = capture_counters(frames=K)                // draws, tris, pass GPU-ms, upload bytes, drops
    for metric, band in budgets[platform_tier]:
        assert band.min <= percentile(s[metric], p) <= band.max, report(bookmark, metric, s)
```

Report the *distribution*, assert the *percentile* (p95/p99 for hitch-class metrics, median for
steady-state ones). Asserting the mean is how a 100 ms hitch hides inside a green build.

**Pitfalls:**

- **Budgets with no owner.** A band nobody is on the hook to defend decays into a warning that is
  always yellow. Each budget line names the chapter/system that owns regressions against it.
- **GPU-time buckets measured with timestamps around async work.** Async compute overlapping a
  bucket makes timestamp deltas lie; either serialize for the capture build or measure with the
  vendor profiler and record both numbers.
- **Counting draws on the CPU.** With GPU-driven submission (`08`) the CPU doesn't know the draw
  count — read the culling stage counters from the GPU stats ring, N frames latent.
- **Budgets set from current behavior.** A budget snapshotted from an unreviewed build blesses its
  defects. Derive bands from the metric's rationale (px/tri from raster behavior, latency from
  perceptual tolerance), then tighten toward them.

## Test controls

Same doctrine as terrain-architect `09`: a metric with no control is not evidence. Each control
kills a family of confounds by construction:

| Control | Construction | What it isolates |
|---|---|---|
| Flat plane | Constant-height field, all systems on | Any visible seam, crack, shadow line, or splat border is *pipeline*-caused — content is innocent by construction. Run first, always. |
| Analytic sine terrain | `h = A·sin(kx)·sin(kz)` with closed-form normals | Diff rendered normals vs analytic → the whole normal pipeline (bake, mips, morph blending) with ground truth |
| Knife-edge ridge | Single sharp crest above smooth flanks | LOD collapse behavior: the crest must survive coarsening; silhouette pop magnitude is measurable here |
| Single-material world | One splat layer, weight = 1 everywhere | Isolates geometry/lighting from splat blending; halos that vanish here are the weight pipeline (`07`) |
| Teleport test | Instant jump to unvisited far region | Streaming cold start, visibility-history reset (`08`), request-storm budget |
| Max-speed flythrough soak | Scripted flight at max traversal speed, 30+ min | Resident-set leak, request oscillation, hitch census, remesh queue starvation |
| Freeze-camera + free-fly | Culling/LOD frozen from camera A; render from detached camera B | *See* what is culled and at what LOD — the single most valuable culling debug control (`08`). Ship it in the debug menu. |

Use controls to **bisect, not just to confirm**: an artifact present on real content and absent on
the flat plane implicates content-coupled systems (displacement bounds, splat weights, bakes); add
systems back one at a time until it reproduces. The first configuration where it appears names the
mechanism — that is the diagnosis, and it is faster than any amount of staring at captures. Keep
every control loadable in the shipping-adjacent build; a control that takes a day to set up will
not be run when the bug report lands.

**Pitfalls:**

- **Controls that drifted.** A "flat plane" scene someone decorated with props is no longer a
  control. Controls are generated, not authored — build them from code at load so they cannot rot.
- **Testing only the controls.** Controls isolate mechanisms; they do not exercise scale. The soak
  and vista tests on real content are the other half — a renderer can pass every control and fall
  over on resident-set growth.
- **Freeze-camera implemented by freezing *time*.** Frozen dt also freezes streaming, TAA jitter,
  and remesh queues — you are no longer inspecting the live culling result. Freeze only the
  culling/LOD camera inputs; let the frame run.

## Debug view modes

Every terrain renderer ships these or debugging is archaeology. Each is a false-color full-screen
mode toggled at runtime; each pairs with a catalogue family above.

| View | Shows | Catches |
|---|---|---|
| LOD level false-color | Per-chunk/cluster LOD index | Selection errors, hysteresis flicker, per-pass mismatch (toggle per pass) |
| Chunk/tile boundaries | Wireframe borders + IDs | Which seam artifact belongs to which tile; adjacency violations |
| Overdraw heat | Additive per-pixel draw count | Skirt/transparency storms, cluster overlap |
| Surface-state overlays | Wetness / snow depth / deformation targets as false color over terrain | State-window snapping, envelope violations (snow where forbidden), stale state |
| Aux-map inspector | Any `14` registry map as false color, point-sampled | Filtered biome-ID bleed, stale tiles, aux/splat resolution mismatch halos |
| Water depth & flow | Depth-band ramp + flow vectors as streaks | Bad shore fades, stagnant river flow, datum/bathymetry mismatches |
| Instance density heat | Instances per cell vs the density map's target | Scatter starvation, popping-radius cliffs, nondeterministic reseeding |
| Mip / texel density | Checker or gradient by sampled mip | Tiling frequency errors, mip bias mistakes, VT indirection bugs |
| VT page residency | Requested vs resident pages, age-colored | Pop-in latency, feedback drops (`07`) |
| HiZ occlusion result | Culled bounds re-projected in red over the frame | False occlusion at silhouettes, convention bugs (`08`) |
| Morph factor | Morph weight as gradient | Bands stuck at ≠1.0 at boundaries; per-pass morph divergence (`01`) |
| Shading vs geometric normal diff | Angle between the two, heat-mapped | Normal bake/apron errors, LOD-coupled normal derivation |
| Streaming state per tile | Resident/loading/wanted/evicted color code | Stuck requests, eviction thrash (`06`) |

**Pitfalls:** a debug view rendered through the path it is debugging inherits the bug — the LOD
false-color view must not itself morph or get culled by the system under suspicion (draw it from
the raw GPU scene buffers, unculled, in a separate pass). Views compiled out of optimized builds
are views you don't have when the platform-specific bug appears — keep them behind a runtime flag
in profile-capable builds. And a view with no legend or fixed scale invites misreading: pin the
color mapping (LOD 0 = red, always) so screenshots in bug reports are comparable across builds.

## Profiling method

- **Tools** (D): PIX (D3D12), Nsight Graphics (NV/Vulkan), RenderDoc (capture/inspection, all
  APIs), Radeon GPU Profiler (AMD wave-level). Capture-based inspection for correctness;
  hardware profilers for cost. RenderDoc is not a profiler — do not read its replay timings as
  production costs (F).
- **What to look at for terrain specifically:** raster/pixel-wave occupancy on small triangles
  (quad overshading shows as low pixel-shader efficiency with high rasterizer utilization);
  bandwidth on VT sampling, heightmap fetches, and streaming decompression (terrain is routinely
  bandwidth-bound, not ALU-bound); barrier/transition stalls around async remesh and streaming
  uploads (a serialized copy queue defeats "async" silently); culling dispatch tails (tiny
  level-by-level dispatches at the quadtree bottom, `08`).
- **CPU side:** mesh-gen/remesh thread-pool contention (voxel worlds: measure queue depth and
  worker starvation, `04`/`05`); streaming IO thread blocking on decompress; any per-frame
  CPU cost proportional to chunk count is a finding by itself (`08` doctrine).
- **The worst-case-view doctrine.** Profile the **peak-vista frame**: horizon view from the
  highest accessible point, maximum resident set, sun angle that maximizes shadowed cascades.
  Average frames lie — culling and LOD exist precisely to make typical frames cheap, so the
  regression always hides in the frame where they help least. Automate the vista: a bookmarked
  camera set flown every capture run, budgets asserted per bookmark.

**Pitfalls:** profiling a debug build (allocator and validation costs swamp the signal — profile
the profile/shipping config with markers); profiling with a cold streaming cache and attributing
IO latency to the renderer; attributing a GPU bubble to the pass *after* the bubble rather than
the fence or readback that caused it (walk backwards from the gap); and trusting one capture —
frame costs on streamed terrain are bimodal, so capture the same bookmark across the soak and
look at the distribution.

## Regression testing

- **Golden-image tests with perceptual tolerance.** Fixed camera bookmarks, fixed seed/content,
  compare with a perceptual metric (SSIM/FLIP-class), not exact pixels. TAA caveat: temporal
  accumulation is order- and history-dependent — either render N warm-up frames with fixed dt
  and jitter sequence before capture, or run golden tests with TAA off plus one TAA-on smoke
  test. An exact-match golden test on a TAA'd frame will cry wolf until it is deleted; a sloppy
  tolerance hides real cracks — calibrate tolerance against a known-bad crack capture.
- **Deterministic camera-path replays.** Scripted path, *fixed dt* (never wall-clock), fixed
  streaming decisions where possible; assert budgets (draws, triangles, GPU-time proxy, hitch
  count, worst upload bytes) per segment. This is the budget-assertion vehicle — run per change,
  fail loudly.
- **Mesh-gen determinism.** Same voxel field, 1 thread vs N threads → bit-identical meshes
  (`04`/`05`); same chunk remeshed twice → identical. Nondeterminism here poisons golden images
  and multiplayer both. Same discipline as terrain-architect's double-buffering check.
- **Streaming-order determinism.** Same replay must issue the same request sequence (log and
  diff request IDs). Nondeterministic ordering is often benign for the *final* image and fatal
  for reproducing a hitch report; where full determinism is impractical, at minimum make it
  deterministic under a test flag.
- **Culling equivalence.** Culling off vs on: identical final image (culling may only remove
  invisible work). Mesh-shader path vs ExecuteIndirect fallback: identical within raster
  tolerance (`08`). Any visible diff is a correctness bug found for free.
- **Where a reference implementation exists, match the diagnostics, not the pixels.** A cheap tier
  and an offline oracle use different estimators and will never agree pixel for pixel — that
  difference *is* the point of having tiers, so a perceptual image diff between them fails for the
  wrong reason and gets its tolerance widened until it means nothing. Contract on the printed
  physics instead: the quantities each tier claims to reproduce, with a published tolerance per row,
  and let a tier fail rows honestly rather than average its way to a passing image. This is also
  what makes a lookup table or a fitted approximation *defensible* rather than a guess — it was
  derived from the reference and is measured against it every run.

### Seven ways a measurement lies while looking like one

Each of these has shipped in this project's own reference work, survived review, and cost a round to
find. All of them produce a number that is *reproducible and wrong* — which is exactly the class a
golden-image test cannot catch, because nothing about the image is wrong.

- **Compare light to light.** A ratio read off sRGB-encoded luminance, checked against a claim about
  *radiance*, is wrong by the encoding and not by a little: one shadow ratio read 0.82 against a
  stated 0.5, where the same two colours are 0.546 apart in linear light. Most of the reported
  defect was the transfer function. Any brightness ratio, contrast figure or albedo check states
  which space it is in, and the tool that prints it does the conversion once.
- **A ratio of targets is not a measurement.** Two figures in one implementation's own comments
  turned out to be one *stated target* divided by another, presented as measured — and they were
  therefore immune to every change to the thing they claimed to measure. The test is mechanical: can
  the number be recomputed from a buffer the run actually produced? If it can only be recomputed
  from other published numbers, it is a restatement, and it will not move when the code breaks.
- **Name the convention once, upstream of every consumer.** Where two conventions differ by a factor
  both expressions divide by — a per-axis versus a total variance, a half-angle versus a full one —
  each consumer stays individually defensible while the budget summing them is wrong by that factor.
  In one slope budget here, two of five bands normalised per-axis and three in the total; it shipped
  for months. One named function, called by everything, is the fix; a comment on each call site is
  not.
- **A test and the code it checks must not share a premise.** The most expensive failure of the four,
  because it produces a *green suite pointing at the wrong number*. In this project a constant
  shipped at 0.563; the derivation written in the comment beside it evaluated to 0.635; the physics
  gave 0.885. Both of the suite's rows — a 2M-point quadrature *and* a 4M-sample Monte-Carlo, filed
  under different tiers as "independent methods" — had been transcribed from that comment's sentence
  rather than from the interface. They agreed with each other to four digits and were both wrong, and
  making the code satisfy them would have moved it onto the middle number with a passing run to
  certify it. **Two methods that read the same premise are one method**, and no amount of estimator
  independence rescues them. What breaks the tie is a check with nothing to transcribe: a **limit**
  (open the cone to the full hemisphere and the answer is forced to ½), a **conservation identity**
  (the angle at which a refraction routine stops returning a direction must equal the angle at which
  the reflectance reaches 1 — different code, same physics), an **analytic special case** (the
  Brewster reflectance is a closed-form number an approximation cannot hit), or the **same quantity
  reached by unrelated code elsewhere in the file**. The procedural rule: derive the value from
  physics, write the derivation down, and *then* pick a guard that could not have been written from
  it. Do not make the two sides agree — make each one right separately and observe that they agree.
- **An existence argument is not an arrival argument.** The newest of the five, and the cheapest to
  catch if the question is asked in the right order. A meniscus sweeps every surface tilt from 0 to
  90° across five millimetres, so any condition stated on the *normal* is met somewhere inside it by
  construction — that is what makes the waterline the one specular feature in a scene that cannot
  fail a reachability test. The same argument was then applied to total internal reflection off the
  fillet's **underside**: reflectance exactly 1 past 48.5°, 15–50× the external specular, and the
  critical angle certainly reached. It is reached, and the term is exactly zero. Writing the
  refracted direction as `t = η i + f n`, `f = η cos_i − cos_t` is negative for **every** incidence
  whenever `η < 1`, so a camera above the water sends `t_z < 0` identically: the ray descends and can
  never arrive at a surface above it. **Reachability of a tilt is not reachability of a position**,
  and the sweep argument only ever established the first. The procedural rule is to separate the two
  questions before building anything: *does the geometry admit the configuration* is a question about
  normals; *does a path from the source to the sensor pass through it* is a question about positions,
  and it is answered by tracing, not by sweeping. A refuted term with the geometry written down is a
  good outcome; a built one that is quietly zero, or quietly not, is not.
- **A boundary has two transports, and testing one is not testing the other.** The most recent, and
  the one with the widest reach outside graphics. This project's water suite covered the exact
  Fresnel equations about as thoroughly as a suite can — normal incidence, grazing, the s/p
  ordering, the Brewster zero as a closed-form value an approximation cannot reach, the critical
  angle from two directions, the shipped curve against the exact one — and not one of those rows
  could see that the renderer was missing the `1/n²` radiance compression on light *leaving* the
  water, an error of 1.78× that shipped for the project's whole run. The reason is mechanical and it
  generalises: **every one of those rows asked what happens to a *ratio***, and `n²` cancels in a
  ratio. Reflectance is a ratio; a transmittance is a ratio; the s-to-p ordering is a ratio. The
  quantity the interface actually transforms — the radiance itself, where `L/n²` is the invariant
  and `L` is not — was never on the stand. State it as a rule and it applies to any boundary a
  renderer has: **a test that only ever compares two things measured on the same side of a boundary
  cannot see a factor the boundary applies to both.** The guards that do see it are the ones that
  cross it — a **conservation identity written across the interface** (Walsh's relation
  `n²(1 − R_int) = 1 − R_ext`, which pins the exponent, not merely the presence of a factor) and a
  **closed energy audit end to end** (a lossless body must return exactly what fell on it; the
  right-hand side is the number 1 and no constant of the renderer appears in it). The procedural
  rule: for each interface, enumerate the transports across it, and check that each has a row that
  is not a ratio taken on one side. Water's case, with the arithmetic and the constants, is in
  [`12`](../../water-physics/references/12-water-physics.md#radiance-is-not-conserved-across-the-interface).
- **A phone photograph is not a colorimeter, and it fails on three separate axes.** The newest, the
  one most likely to cost a week, and the only entry here where the instrument is outside the
  codebase. A reference photograph is treated as ground truth about a renderer's chromaticity and
  level; it is neither, and the three reasons are independent, hit different quantities, and must be
  diagnosed apart. **Automatic white balance rescales the channels of the very thing being
  measured** — a frame dominated by cyan water is pushed toward neutral, so absolute sRGB triples
  read off it are not evidence about chromaticity, and the push is *largest exactly where the
  subject is most saturated*, which is where the measurement matters most. **A display-referred tone
  curve rescales level, non-uniformly** — inverting the sRGB EOTF recovers display-referred linear,
  not scene-referred linear, and the residual is an S-curve with a deepened toe. **And Display P3
  read as sRGB corrupts chromaticity again, downstream, in the reader's own pipeline** — iPhone
  captures have been tagged Display P3 since the iPhone 7, and any open that drops the ICC profile,
  any screenshot, any tool that assumes sRGB, silently reinterprets the numbers. All three are
  invisible in the file. The sorting table is the deliverable, because a reader with a failed
  comparison can use it to tell which one they have:

  | Failure | Where it happens | What it distorts | What survives it |
  |---|---|---|---|
  | Automatic white balance | in camera | **chromaticity**, worst at high saturation | luminance; within-frame pairs |
  | Display-referred tone curve | in camera | **level**, non-uniformly | pairs **close in level** |
  | Display P3 read as sRGB | in the reader's pipeline | **chromaticity**, worst at high saturation | luminance, to ~1% |

  The third is the only one that is fully computable, so compute it. Both spaces are D65, so the
  correction is one matrix on **linear** values (`D`, derived here from the two primary sets and the
  D65 white point, not quoted):

  ```
  P3 -> sRGB, linear      [ 1.224940  -0.224940   0.       ]
                          [-0.042057   1.042057   0.       ]
                          [-0.019638  -0.078636   1.098274 ]
  ```

  **The asymmetry is the part worth teaching, and it is structural rather than incidental.**
  Saturated colours sit near the sRGB gamut boundary, which is exactly where the wider P3 primaries
  have their extra room; warm near-neutrals sit well inside both gamuts. Worked on plausible triples
  (`D`, recomputed here; ratios in linear light, code shifts in 8-bit sRGB):

  | Subject, as 8-bit code values | R/B ratio error if read as sRGB | Red code shift | Luminance error |
  |---|---|---|---|
  | Pool water `(140, 200, 205)` | **−28.2%** | −19 levels | +0.97% |
  | Saturated water `(120, 205, 210)` | **−51.5%** | −34 levels | +1.29% |
  | Shaded water `(70, 165, 185)` | **outside the sRGB gamut** — the correct red is *negative* | clipped to 0 | +1.40% |
  | Warm sandstone `(210, 180, 150)` | +13.5% | +6 levels | −0.41% |
  | Grey stone `(180, 175, 170)` | +2.2% | +1 level | −0.06% |

  So the error is 13–23× larger on the subject than on the neutral reference surfaces beside it,
  and on a saturated cyan it is not an error at all but a **gamut failure**: that colour has no sRGB
  representation, so any sRGB-clamped comparison is measuring the clamp. Nothing in the image looks
  wrong while this happens, because the surfaces a reader would sanity-check against are the ones it
  leaves alone. Luminance, by contrast, survives to about **1%** — not because the transform
  preserves it (a colorimetric transform preserves `Y` exactly) but because the two spaces'
  luminance weights differ only modestly, `(0.2126, 0.7152, 0.0722)` against
  `(0.2290, 0.6917, 0.0793)` (`D`). A *luminance* ratio read off a P3 file misread as sRGB is still
  usable; a *chromaticity* read off it is not.

  **And the instrument does not have to be a camera: your own renderer's output is display-referred
  too.** The entry above is written about photographs because that is where it was learned, but the
  second failure — a display-referred tone curve rescaling level non-uniformly — is a property of
  the *file*, not of the optics that made it. A render's PNG has been through a view transform and a
  display-side curve exactly as a phone's JPEG has, and **inverting the sRGB EOTF on it recovers
  display-linear, not scene-linear.** This project committed that against its own frames within
  ninety minutes of writing the warning above: a water-to-stone ratio was read off the render's PNG
  with `colour_table`, after ACES and a display S-curve, and reported the render short by a factor
  of two. It was not short at all. The rule is one line — **measure in the render target, before the
  tone map, or you are measuring your grade** — and it costs nothing, because unlike a photograph
  the scene-linear buffer is *right there*.

  Two further distortions compounded it in that episode, and each is independently common enough to
  be worth naming, because the three multiply and none of them looks like an error on its own:

  | Distortion | Factor, on that frame | Why it is easy to take |
  |---|---|---|
  | A **median** over a right-skewed field | **×0.953** | A caustic net is bright folds over dim cells: median/mean is **0.786** on the transmitted column (`D`). A median is the standard defence against outliers, and here the outliers *are* the signal — the same median over smooth stone reads the stone, so it biases only one side of the ratio |
  | A **display-referred** read of the render's own PNG | **×0.996** here, **×0.966** on the hero frame | The two surfaces sat close in level on the wide frame and far apart on the hero — which is this section's own "prefer pairs close in level" precondition, observed running both ways |
  | A **region** that was not the quantity being predicted | **×0.590** | The closed form is about *sunlit bed under water*; the region was **all** water in the frame, including an occluder's shadow and the strip the refracted beam never reaches. That strip is physics, not a deficit |

  `0.706 × 0.953 × 0.996 × 0.590 = 0.395` against a true **0.706** on that frame — a factor of
  **1.79**, every link measured rather than argued (`D`, arithmetic recomputed here). **Note the
  ranking, because it is the opposite of what the episode felt like:** the tone curve was the
  *smallest* of the three on that frame and the region was the largest. The transferable lesson is
  therefore not "the curve got me" but the ordering rule — **check what was measured over before
  checking what space it was in** — and then check both, because a factor of two is rarely one
  mistake. A discrepancy that resolves into three independent factors of 0.6–1.0 was never going to
  be found by arguing about the physics.

**The remedy, stated as a method rather than as a warning: ratios internal to one frame, and pairs
close in level.** Two surfaces in one exposure share the white balance, the exposure and the colour
space, so those three factors divide out of their ratio — which is the same structural fact as the
sixth entry above, used the other way round: a ratio is blind to whatever multiplies both its terms,
a liability when that factor is the subject and an asset when it is the confound. **The precondition
is that a tone curve is not a multiplier.** It is a smooth nonlinearity, so locally it acts as a
gain plus a local gamma: a pair at *similar* levels rides nearly the same slope and comes through
close to intact, while a pair far apart in level — sunlit against shadowed — sits on two very
different slopes and is exactly where the curve does its damage. So prefer within-frame pairs, and
among them prefer pairs close in level; where the question genuinely is a shadow-to-lit ratio, a
photograph gives a sign and an ordering but not a number, and the limit is quoted with the number.
The choice of *which* pair is the rest of the method, and the rule is to **pick the pair that
cancels the thing you are not testing**. This project's water work found three, each cancelling
something different:

| Pair, in one exposure | What cancels | What it therefore tests |
|---|---|---|
| Lit subject / shaded subject | the material — one pigment, two illuminations | the ambient-to-direct balance |
| Two surfaces both seen **through** the medium | the interface, the Fresnel entry term and the `n²` | the two albedos and the two path lengths |
| The same material with and without the medium's path | the material, the interface and the `n²` | the **path alone** — an absorption measurement |

The third is a real technique and not a hypothetical: a liner pool's dry freeboard band above the
waterline is the same sheet of pigment as the submerged bed, lit directly, with no water path, no
interface and no `n²` between it and the eye, so it pins the albedo on its own and its ratio against
the bed then pins the absorption path — two measurements from one photograph, no reference chart,
and the target is in the frame for nothing. The arithmetic is
[`12a`](../../water-physics/references/12a-water-derivations.md#the-calibration); what it defends against a fitted-constants
objection is [`12`](../../water-physics/references/12-water-physics.md#radiance-is-not-conserved-across-the-interface).

**State which way each bias runs, so a bound survives even when the value does not.** A biased
instrument with a *known sign* still yields a one-sided bound, and recovering one is almost always
better than discarding the frame. Because the tone curve deepens the toe, a shaded-to-lit ratio read
off a photograph is a **lower bound** on the true ratio — the real shadow is lighter than it
looks — which is a usable measurement provided it is quoted as a bound. The same applies to white
balance once the scene's dominant hue is known, and it converts into the actionable rule for anyone
matching a render to a photograph: **a render tuned to hit a photograph's channel values exactly has
been tuned to the camera's white balance.** The correct target is displaced from the photograph in
the direction of the scene's dominant hue — a correct render of a cyan-dominated pool should land
slightly *more* cyan than the frame, not matched to it — and the same holds for any saturated
subject: foliage, skin, sand, a painted wall. This project got an independent confirmation of both
the direction and the magnitude: the observer who was present when the reference frames were shot,
asked nothing about colour management, volunteered that the photographs looked much like reality
with the water *perhaps slightly more cyan in life*. Prediction and report were arrived at
separately and agree on sign, and the hedging bounds the size — which is why the honest statement is
not "phone frames are useless for colour" but the sharper one that the frames stay usable as a
**reference** while staying unusable as a **colorimeter**.

Two habits that episode is worth keeping for. **Split a finding into the parts new evidence reaches
and the parts it does not** — "more cyan" is a statement about hue and says nothing about level, so
it moved that project's chromaticity finding and left its luminance finding, a water-to-sunlit-stone
ratio in one exposure, exactly where it was. And **do not fit a material constant to a camera.** On
learning that a render's shadow is deeper than the reference, the tempting move is to raise the
occluder's transmission constant; that fits a *fabric* parameter to a *tone curve*, two errors
compounded and invisible afterwards. A shadow's depth in frame is the fabric's transmission plus the
sky the shaded region still sees plus the bed's inter-reflection — attribute the discrepancy to one
of those three before anything moves.

**What to ask for instead**, in descending order of strength, because all three failures are
properties of the *deliverable* and not of the subject:

1. **A RAW/DNG capture.** Linear, no display tone curve, white balance carried as metadata rather
   than baked in — it retires two of the three failures outright and makes the third explicit.
2. **A neutral of known reflectance in the frame.** White copy paper is ≈0.85 diffuse and costs
   nothing; it fixes the white balance *and* supplies a level anchor, which no ratio can.
3. **The original file's EXIF.** From aperture, shutter and ISO the metered scene luminance follows
   as `L = K·N²/(ISO·t)` with `K ≈ 12.5`, which turns a source of ratios into a rough photometer.
   Weakest of the three — auto-exposure meters a scene average and multi-frame HDR blurs what "the"
   exposure was — but it costs nothing to obtain and is often still in the file.

The general lesson is the one that governs every comparison against a photograph: **without one of
those, the comparison is only ever *relative*.** A renderer can have every proportion in the frame
right and its absolute exposure wrong, and no amount of ratio discipline will discover it.

**Pitfalls:** goldens that were never verified correct (a golden captured from a broken build
enshrines the bug — review each golden by eye once, against the catalogue, before blessing it);
tolerance widening as a merge ritual (every tolerance bump gets a named justification or the
test is dead); replay scripts driven by wall-clock or physics-stepped cameras (nondeterministic
by construction — fixed dt, scripted transform); and platform-specific goldens diffed against a
reference platform (raster and filtering differ legitimately across vendors — golden per
platform tier, cross-platform diffs only as an informational report).

### An irradiance used as a radiance

This one belongs with the seven above rather than with the eighth, because it is an instrument
failure: the number is reproducible and wrong. It gets a heading because it is, in this project's
experience and in most light-transport code, **the most common unit error there is**, and because it
is nearly always a factor of about **π**.

**The two quantities.** Irradiance `E` is W/m² — flux arriving on a surface, integrated over a
hemisphere. Radiance `L` is W/m²/sr — flux per unit projected area *per unit solid angle*, and it is
what a shader must hand to a compositor, a lerp or a tone map. For a Lambertian receiver they are
related by

```
L = rho * E / pi
```

and that `1/π` is the whole of the confusion. Both are three floats. Neither carries a unit. A
renderer that adds them, lerps between them, or hands one to a function expecting the other produces
a picture with **one surface** out by π and everything else right — which reads as an art-direction
problem, not as a bug, and gets absorbed by whatever constants were fitted around it.

**How it looked here.** A shade sail's underside shipped as `albedo × (SKY_AMB × 1.6 + SUN_COL ×
0.22)`: an *irradiance* triple used where a radiance was wanted, with two invented multipliers on it.
Derived properly — what the fabric transmits plus what its underside reflects off the ground it
shades — the panel is `[0.627, 0.656, 0.796]` against the shipped `[2.062, 2.255, 2.695]`:
**×3.29 / 3.44 / 3.38**, i.e. π to within the two hand multipliers. A shade sail that read *brighter
than the sky it shades*, for the project's whole run (`D`).

**The checks, in order of cost.**

1. **A radiance and an irradiance cannot be compared, so any expression that does is the bug.** Grep
   for the operations that mix them — an add, a `lerp`, a `max`, a comparison — and check the two
   operands' kinds. This is a type error being carried by a language that has no such type.
2. **Any bare constant near 3.14 or 0.318 in a shading term, with no derivation beside it, is this
   error wearing a knob.** So is any pair of invented multipliers whose product lands near either.
   The rule is not that π may not appear — it appears legitimately in every diffuse BRDF — it is that
   it may not appear *undocumented*, because a documented π is a division and an undocumented one is
   a fit.
3. **Name the kind in the symbol and the error becomes unwritable.** `E_deck` and `L_deck` cost
   nothing and make the mixing sites visible at a glance; a shared `SKY_DECK` that is used as an
   irradiance in one call and a radiance in another is what allowed this one.

**Why a picture does not catch it.** π is **1.65 stops** — enormous on a chart, and entirely
plausible on a fabric panel nobody has a reference for. It survives every *ratio* check taken on one surface,
because it is a constant multiplier on that surface alone; it survives every energy audit that
composes its own irradiance; and if the surface is small or off-frame it survives everything, which
is the [ninth way](#the-ninth-way-the-code-no-pixel-reached) below. The guard that does see it is
the one that crosses the boundary between the two quantities: integrate the shaded radiance over a
hemisphere and check that it returns the irradiance you started from.

### The eighth way is about the test, not the measurement

This one earns its own heading rather than an eighth bullet above, and the reason is the useful
part of it. The seven are all failures of an **instrument**: each produces a number that is
reproducible and wrong, and the remedy is to fix the reading. This one produces a number that is
**right**, about the wrong thing. Nothing in it lies; the suite is honest, the assertion holds, the
physics it asserts is real. What fails is *coverage*, and coverage is not a property of a
measurement at all — it is a property of the test's relationship to the code. Filing it with the
seven would blur the list's own thesis, which is that a measurement can lie while looking like one.
This is the opposite failure: a test that tells the truth while touching nothing.

**A test's power is the surface area it shares with the thing under test.** That is the whole rule,
and it is worth stating before the story, because it inverts an instinct. Robustness and power pull
against each other: a test written to be independent of the implementation's details is written to
be blind to them, and the limit of that process is a test that shares one symbol with the code and
checks a law of nature.

**What it looked like here.** A water renderer carried a *closed energy audit of the whole pool*:
put a perfect white Lambertian bed under a flat surface, no absorption, uniform sky, compose it the
way the renderer composes, and the apparent albedo must come out **exactly 1** — energy
conservation, right-hand side the number 1, no constant of the renderer in it. That is a genuinely
good guard, it was written for a real bug (a missing `1/n²` on light leaving the medium, which it
catches: without the divisor the audit reads 1.73), and it passed for the project's whole run while
the transport it was named after carried a **truncated** interreflection series over the wrong cone,
no path lengths at all, and no basin — three things it was structurally incapable of noticing.

Read what it *borrowed* and the reason is mechanical — **one name**:

- it wrote its **own** irradiance and its **own** in-water radiance, so it never asked the renderer
  for the field it was auditing;
- it closed the interreflection series `1/(1 − ρ·R_int)` **itself**, so a renderer truncating that
  series at one bounce over the wrong cone could not register;
- it had **no absorption and no depth** — every path length in it is exactly 1 — so any error in a
  path length was invisible either way;
- it had **no scene**: no walls to intercept the beam, no occluder.

One function was on the stand. Everything else in the assertion was the test's own arithmetic, and
the right-hand side was a law that would hold for almost any implementation that composed
*something* through that one function. **It is a good unit test of one divisor wearing the title of
an audit** — and the title is what did the damage, because a suite containing a row called "closed
energy audit of the whole pool" is a suite nobody asks a second question of.

**The remedy is a pair chosen so each sees where the other is blind**, and it generalises past
water. The audit was replaced by two rows through the *shipped* chain:

- **a limit** — lossless white bed, zero absorption: `R(θ_sun) + ρ_water(1, a = 0) == 1`. Right-hand
  side the number 1, no constant of the renderer, and it pins the **shape** of the series. It is
  also blind to every path length in the chain, because at `a = 0` every path is 1.
- **a 400 000-photon analog walk** at the medium's own absorption. A photon enters at the refracted
  angle, crosses to the bed, is redrawn from a cosine law, attenuates over its **own** `1/μ`, meets
  the exact internal Fresnel and either escapes or returns. **Nothing in it is an average of
  anything**, which is the only way a *correlated* integral can be checked — a second quadrature
  would have shared the premise, which is the fourth way above. It agrees with the closed form to
  **0.15% at worst and under 0.1% in two of three channels** (`D`, both recomputed here).

**And then fire each one at the bug it was written for, by putting the bug back.** This is the part
that is transferable whatever the domain, and it is cheap: a reintroduced bug is a four-line patch
and the answer is a row number. Four were reintroduced here:

| Bug put back | Rows that FAIL | Does the limit alone catch it? |
|---|---|---|
| Drop the leading `2` in the `2·E₃` slab transmittance | 7 | **yes** — it reads 0.42 against 1 |
| Drop the up leg from the transport's numerator | 2 | **no** — only the walk, and only at nonzero absorption |
| A one-way transmittance where the round trip belongs | 1 | **no** — only the walk |
| Re-separate the joint escape integral into its two means | 2 | **no** — the two agree exactly at `a = 0` |

**The lossless limit alone passes three of the four** (`D`, verified here by evaluating each variant
against the limit). That is the same blindness the old audit had, caught before it shipped this
time, and it is why the discipline is *two* guards with named blind spots rather than one guard with
a good name. The physics case is [`12`'s water
transport](../../water-physics/references/12-water-physics.md#attenuation-and-escape-do-not-factorise-and-a-lut-is-where-you-will-separate-them);
the mechanism is general.

Three questions to ask of any test that has never failed, in the order they are cheapest to answer:

1. **How many symbols does it import from the code under test?** One is a warning, not a
   certificate. Count them literally.
2. **What does its right-hand side depend on?** A physics identity is a strength when the code has
   to reach it through the shipped path and a weakness when the test can compute both sides itself.
   `assert conservation(my_own_composition()) == 1` is a test of the assertion.
3. **Which of its inputs are at a degenerate value?** Zero absorption, unit albedo, normal
   incidence, one texel, a flat surface — every degeneracy silently deletes the terms that only
   exist away from it, and those terms are usually the ones a reviewer would have asked about.
   This one has since been paid for in the field: see the
   [tenth way](#the-tenth-way-a-ratio-cannot-see-a-common-factor), where every row touching one
   function called it at `spm = 0` and a deliberate defect at that argument was bit-identical to
   clean.

A fourth question belongs beside them and is answered against the *frame* rather than against the
suite: **how many subsamples reached the code at all?** That is the
[ninth way](#the-ninth-way-the-code-no-pixel-reached) below, and it is the failure the eighth cannot
see, because a test that touches nothing and a frame that reaches nothing are independent holes in
the same wall.

### The ninth way: the code no pixel reached

The eighth way is a test that touches nothing. This is its sibling and it fails one layer further
out: the **test is fine, and the coverage is zero.** Nothing is wrong with the assertion, the
tolerance, the physics or the estimator — the code under discussion is simply never executed by the
thing everyone is looking at.

**A frame is a sampling of the code, not a proof of it — and the sample is biased toward what the
author framed.** That is the whole rule. A golden-image suite's coverage is the union of its
viewpoints, and that union was chosen for how it looks. Every shortcut that lives outside it is
protected by the same taste that produced the shot.

**Measured here.** The shade sail of the entry above lands on **0 of 8 640 000 subsamples** of the
hero frame — its panel is behind and above the camera, and the water it shades is shaded by it
without ever showing it. Three rounds of review, a 268-row suite and a per-channel colour regression
all passed over a term that was 3.4× wrong, because no pixel had ever asked for it. What found it was
a **new viewpoint** — the same scene from under the water, where the whole panel is inside Snell's
window (`D`).

**The instruments, cheapest first.**

1. **Count the subsamples each branch receives, and print the count.** A branch with a zero count is
   a finding, not a curiosity: it says the frame cannot speak about that code either way. This costs
   one counter per branch and it turns "is it covered" from a judgement into a row.
2. **Add a viewpoint chosen for reach rather than for beauty.** In this project the rule fell out of
   the geometry: *every above-water shortcut that survives by being invisible from a downward view
   becomes visible from underneath.* The submerged camera is a coverage instrument that happens to
   also be a shot. The general form is to pick the camera that inverts the frame's own occlusion —
   behind the hero object, under the vehicle, inside the room the level never enters.
3. **Ask what the frame structurally cannot see.** Not what it happens to miss — what it is *unable*
   to reach: geometry behind the camera, surfaces whose normals face away everywhere in the shot,
   branches gated on a state the scene never enters. That list is short, it is writable in an
   afternoon, and each entry is either covered by another frame or marked.

**And do not let a green suite stand in for it**, because the two failures compound in one direction:
the eighth way says a test can be true about nothing, the ninth says a frame can be right about
nothing, and a project that has both believes it has two independent confirmations. It has none. The
question to ask of any suite plus any golden set is *which lines does the union of these actually
execute* — and the answer is a number, not an impression.

#### A second shape: derived, guarded, and never called

The instance above is coverage zero **by scene configuration** — the code is wired in, and this
frame's geometry happens never to ask for it. There is a harsher shape, and it was found three times
in one wave, in three separate subsystems, by three builders who never spoke to each other:

- **The foam.** A round diagnosed a smooth foam edge correctly, derived the fix, wrote it, and wired
  none of it. `grep` for its four new symbols returned **nothing outside the module that defined
  them**; the shader still blended by the mean.
- **The glitter.** Six rounds argued the resolved/unresolved slope split. `grep` for the class that
  implements it returned the class statement and two comments: **nothing had ever instantiated it.**
  The shader computed the two variances on one line and discarded them on the next.
- **The diffraction.** Ten Sommerfeld rows verified and green, and the renderer **does not import the
  module** — zero pixels of any frame carry a diffracted edge.

**The difference from the first shape is the detector, and it is why the first shape's instruments
all miss this one.** A per-branch subsample counter answers *did this frame reach that branch*. It
cannot answer *does any path connect that module to any frame*, because the branch it would count is
in a module nothing calls, so the counter is never compiled into the frame's execution at all. The
count is not zero; **there is no count.**

So the detector is a different instrument and it costs seconds:

- **`grep` for each new symbol and require a hit OUTSIDE the module that defines it.** A module whose
  every reference is internal is a library nobody imported, however correct it is.
- **Pair every row that tests a function with a row that tests that the frame reaches it**, in
  integers off the rendered buffer: how many pixels, what share, and where. A function row and a
  reach row are not redundant — this shape passes the first and fails the second by construction.
- **Distrust a docstring that says the suite checks something.** Seven such promises in one module
  were false on the tree that shipped them, and nine in another; they had been written when the rows
  were intended and never revisited when they were not written. A claim about a test is not a test.

**And the same failure has a version one level higher up**, which is how it survived so long here: a
round can land its *code* and never land its *rows*. The suite then reports a healthy total on the
next wave, computed over a suite that has never heard of the new code — green for the same reason an
empty test file is green. The ten-second check is `git log -- <the suite file>`: **a suite total is
not evidence that a wave landed**, and the wave's own entry either exists or it does not.

The compounding is worth stating plainly, because it is what makes this shape expensive. A module
that is derived, cited, figured, chaptered and guarded, and that no frame calls, produces a **perfect
score on every instrument the project owns** while contributing nothing. Nothing in the record is
false; the record is simply not about the artifact.

### Pick instruments whose parameters someone else has fixed

A scene object that exists to test physics is an **instrument**, and every free number in it is a
free number in the reading. The discipline is one line: **choose an object whose parameters someone
else has already standardised, so its state is an output rather than a setting.**

Worked, because the arithmetic is the argument. This project needed a floating body to read a wave
field and a waterline. The obvious choice — the inflatable ring in the reference photograph — is the
worst instrument available, and Archimedes says why. An air-filled PVC tube of radius `r` and skin
`t` has effective density `ρ_PVC·2t/r + ρ_air`; at `r = 90 mm`, `t = 0.25 mm` that is **8.42 kg/m³**,
so it floats with **0.842%** of its volume under — **5.27 mm of a 180 mm tube** — and its meniscus
climbs **0.93 mm**, i.e. **17.7% of the draught**. The waterline it draws is mostly capillary, and
nothing about its depth is a reading of anything. ⚠️ A figure of "9 mm" for that draught has been in
circulation for this geometry and does **not** reproduce: 9 mm needs an effective density of
18.7 kg/m³, and the 9 mm appears to come from applying a *sphere's* shell fraction `3t/R` to a tube,
where the tube's is `2t/r`. The companion figure for a beach ball — 17 mm of a 360 mm sphere — does
reproduce (17.2 mm at `3t/R`), which is what identifies the slip (`D`, both recomputed here).

What was taken instead is a **FINA size 5 water polo ball**, because both numbers that decide the
flotation are published: circumference **0.68–0.71 m** and mass **0.400–0.450 kg** (FINA Water Polo
Rules, equipment). Mid-range gives `R = 0.11061 m`, `m = 0.425 kg`, a mean density of **75 kg/m³**,
and a draught that is then *solved* rather than set — **39.61 mm of a 221.2 mm ball**, with the
contact line's own tension carrying **13.0%** of the weight (the balance, and the tangency condition
it then makes falsifiable, are
[`12a` §3](../../water-physics/references/12a-water-derivations.md#a-floating-body-and-the-split-its-own-meniscus-hides)).

**The standard supplies the tolerance as well as the value, and that is half the point.** Across the
published **mass** band the draught runs **38.40 → 40.79 mm** (±3.0%) and across the published
**circumference** band **40.15 → 39.10 mm** (±1.3%, and note the sign: a bigger ball floats
*shallower* at fixed mass). So a disagreement inside that envelope is the instrument and a
disagreement outside it is a finding. A chosen number gives a
value with no tolerance at all, which is why "I set the draught to 40 mm" cannot falsify anything.

Three tests for whether an object is an instrument or a prop:

1. **Is its state an output?** Can the quantity you intend to read be *computed* from the published
   parameters plus the physics, before the frame is rendered? If it has to be dialled until it looks
   right, it is a prop.
2. **Does the standard come with a range?** A single catalogue number with no tolerance is only half
   a standard, and the missing half is the error bar on every conclusion drawn from it.
3. **Is the effect you want to read the dominant term in its state?** The inflatable fails this one
   even before its parameters are questioned: with the meniscus at 18% of the draught, a waterline
   reading on it is a surface-tension measurement wearing a buoyancy label.

### The tenth way: a ratio cannot see a common factor

The eighth way is a test that touches nothing, the ninth a frame that reaches nothing. This one is
about the **whole suite's favourite instrument**, and it is the most uncomfortable of the three
because the instrument is right and this chapter recommends it.

**Ratios are this project's preferred reading and the reasons are good.** A ratio of two pixels in
one frame cancels the exposure, the white balance, the source spectrum and the tone curve's local
slope — that is the within-frame-ratio method in the seventh way, and it is why a ratio survives
being read off a photograph when an absolute level does not. Every argument for them is sound.

**And exactly that is what makes a suite built out of them blind.** A ratio cancels whatever
multiplies both of its terms — that is its purpose — and it therefore cannot see an error that is a
**common factor**. Wrong units, a missing or duplicated constant, the wrong one of two similarly
named quantities: these are the errors that scale a whole expression, and they are the class the
instrument is designed to remove.

**Measured, and it is not a subtle miss.** A coastal water renderer drove a Bagnold suspension
balance from the **wave's** dissipation instead of the **bed's** stream power — a factor of about
fifty in front of the whole load. It shipped, and it passed a fifty-three-row suite. The two rows
that owned the suspension were both ratios. Re-fired here, with the defect reintroduced as
`bed_dissipation × 50` (`terrain-renderer/reference-impl/`, `beach_optics.py` and
`validate_beach.py`; all four numbers recomputed):

| row | clean | with the ×50 defect | verdict |
|---|---|---|---|
| **ratio** — "the load goes as `u_orb³`": `M(2)/M(1)` vs 8 | 8.000000000000 | **8.000000000000** | **bit-identical.** The balance is linear in the stream power, so the factor divides out exactly |
| **ratio** — "the same stirring reads dark at 8 m and pale at 1.2 m": `R_shallow > 4·R_deep` | 0.2346 vs 0.0456 → pass | 0.2384 vs 0.0482 → **pass** | reflectance saturates in `b_b`, so a 50× load moves each side by 1–5% and the threshold never notices |
| **absolute** — the bed stream power at `u = 1 m/s`, against `ρ·c_f·⟨\|u\|³⟩` | 2.6101 W/m² | **130.5071 W/m²** | fails on the first digit |
| **absolute** — depth-averaged load in the breaking zone, against a published bracket | 373 mg/L | **18 671 mg/L** | fails; past the 1000 mg/L "opaque silt river" end of the bracket it is checked against |

The first ratio is the one to look at: **twelve significant figures, unchanged.** No tolerance
anywhere in that row could have caught it, because the defect is not small — it is *absent* from
the quantity the row computes.

**The rule.** ⚠️ **A suite needs at least one absolute row per quantity, and a suite made only of
ratios is blind to precisely the errors that are constant factors.** The absolute row does not have
to be hard to write — both of the ones that fired above are one line, one against a closed form at
a convenient argument, one against a published order-of-magnitude bracket. It has to *exist*, and
the bracket may be wide: the second row's range spans two decades and still caught a factor of
fifty, because a factor of fifty is bigger than most brackets.

**And an order-of-magnitude bracket is the cheapest absolute row there is.** It needs no
calibration and it is not a tuning target — it is a statement that the quantity is the *kind* of
thing it is named after. Turbid seawater is not silt slurry; a metre of water is not a millimetre
of it. That is enough resolution to catch every common-factor error worth the name, and it is
writable before the code is.

**The sibling from the same run, and it is the eighth way's third question earning its keep.** A
second defect in that suite also caught nothing: a `one-turbidity-slider` bug that ties the water
mass's absorption and CDOM to the mineral load — the architecture the physics chapter names as the
canonical wrong one. It passed because **every row that touched the function called it at
`spm = 0`**, where the defect multiplies by `1 + 0` and is bit-identical to clean:

| `spm` | absorption, clean | absorption, bugged |
|---|---|---|
| **0** | (0.2824, 0.0835, 0.1577) | **(0.2824, 0.0835, 0.1577)** — identical |
| 1 | (0.2824, 0.0835, 0.1577) | (0.3031, 0.1141, 0.3051) |
| 50 | (0.2824, 0.0835, 0.1577) | (1.3177, 1.6106, 7.5292) |

A guard that calls its function at the parameter value where the defect is inert is not a weak
guard; it is **not a guard**, and it will report a pass forever. That is question 3 of the eighth
way — *which of its inputs are at a degenerate value?* — answered in the field, and the answer cost
a shipped factor of fifty. The two failures are the same shape seen twice: **the first evaluates
the right expression at a point where the defect cancels; the second evaluates it at a point where
the defect is zero.** Both produce a number that is right, reproducible, and about nothing.

**A third shape of the same failure, from the pool scene, and it is the hardest of the three to
see by reading a row.** Here the degenerate argument is not a zero and the defect does not cancel
inside the row's expression: **two different expressions coincide, by an identity, over a whole
sub-manifold of the input domain — and every row lived on it.** `atmosphere._lobe_shape` convolves
a `cos^n` sun lobe with the reflection ellipse the unresolved slope variance puts on the mirror
direction, and wrote the widened lobe's exponent as the **projection** variance `1/(uᵀQu)` where
the convolved density along `u` wants `uᵀQ⁻¹u`. For an isotropic `Q = qI` the inverse is `(1/q)I`,
so `uᵀQ⁻¹u = 1/q` and `uᵀQu = q`: the two are not close, they are **the same number, for every
`u`, exactly** — and likewise on either principal axis. The suite carried **eleven rows on that
function** — the disc's solid angle, its flux against `2π/(n+1)`, `sky()`'s peak, the aureole, the
ellipse itself — and **every one of them was taken at `cov = None`, where `Q = (1/n)I`.** Re-fired
here (`terrain-renderer/reference-impl/`, `atmosphere.py` and `validate.py`), the widened lobe's
flux against the unwidened `2π/(n+1)`, at a fixed minor axis of `1e-5`:

| ellipse axis ratio | 1 — isotropic, the degeneracy all eleven rows sat inside | 10 | 1e4 (the raster path's grazing frame) |
|---|---|---|---|
| the correct `uᵀQ⁻¹u` | 1.0000 | 0.9999 | 0.9535 |
| the shipped `1/(uᵀQu)` | **1.0000** | 1.3725 | **32.36** |

Eleven rows, no tolerance anywhere in any of them, and **the first column is an identity rather
than an agreement** — which is why adding a twelfth row at `cov = None` would have bought nothing.
A degenerate case is not a weak test of the general one; it is **no test of it**. What found the
defect was not a row at all: it was a **second implementation** — the raster reference over the
same shared module — reaching an anisotropic `Q` that no consumer of that module had ever reached
in the project's history. That is the eighth way's third question again, asked at the level of the
whole suite instead of one row: ⚠️ **before trusting a function's rows, ask what region of its
input domain they occupy, and whether the shipped callers occupy the same one.** The pool's did
not, and the answer was a sun glint carrying up to **1378 in scene-linear radiance too much** —
77% of its own pixel — down one edge of the shipped hero frame.

**A fourth shape, and it is the one a reviewer is least likely to look for, because the row that is
blind is the suite's *strongest* row.** The first three shapes are a defect that cancels, a defect
that is zero, and two expressions that coincide over a sub-manifold. This one is: **the guard is
evaluated at a FIXED POINT of the operator that was wrongly inserted.**

**The case, from the same project's coastal scene, and it had survived six waves.** Two closed forms
describe one transport across an air/water interface. `a_wet(a) = R_ext + (1−R_ext)(1−R_int)a/(1−a
R_int)` maps a substrate's **water-side** reflectance to the **air-side** apparent albedo of
[water film + substrate]; `rho_water(rho_bed, …)` crosses the interface twice inside itself, so its
`rho_bed` is also water-side. A renderer passed `a_wet(a)` where `a` belonged — the interface model
applied twice, worth up to 35%.

**Why no guard saw it.** `a_wet` is a Möbius map of `a`, and every structural property the suite
checks is **closed under composition**: monotone stays monotone, `[0,1]` stays `[0,1]`, energy
conservation stays energy conservation. That alone would make a composition hard to see. What made
it *impossible* is sharper:

```
a_wet(1) = 1     exactly       and       a_wet(0) - R_ext = 0     exactly
```

**0 and 1 are the fixed points of the map — and 0 and 1 are where every energy guard in the project
was written.** The suite's strongest interface row is a *lossless white pool*: a perfect-white bed,
no absorption, and the assertion `R(sun) + rho_water(1, …) = 1`, whose right-hand side is the number
1 and which reads **1.73** if the `L/n²` divisor is dropped. Against this defect it is not merely
weak. Re-fired here (`terrain-renderer/reference-impl/`, `optics.py` and `validate.py`; both columns
recomputed at the pool's own 1.40 m depth, its own sun, green band, `rho_water` excluding the surface reflection):

| `rho_bed` | correct chain | with the spurious `a_wet` composed in | ratio |
|---|---|---|---|
| **1.000** — the lossless-white row, and both `a_wet` boundary rows | 0.563872 | **0.563872** | **1.000000000000** |
| 0.681 | 0.332328 | 0.259670 | 1.280 |
| 0.450 | 0.200103 | 0.148277 | **1.350** |
| 0.300 | 0.126130 | 0.097771 | 1.290 |

**Twelve significant figures at the point the suite chose, and 35% one step off it.** No tolerance
reaches that, because at `rho_bed = 1` the two chains are not close — they are the **same
expression**. `a_wet(0) = R_ext` closes the other end the same way. Every guard anybody thought to
write was written at one of those two arguments, because they are the two arguments where a closed
form is *self-checking*, and self-checking arguments are exactly the ones an inserted operator
fixes.

⚠️ **A boundary condition is where a formula proves itself, and therefore where an extra copy of the
formula is invisible.** The rule that follows is mechanical and costs one line: **for every map the
codebase can accidentally apply twice, find its fixed points, and require at least one guard
strictly away from them.** In this case any single row at any interior albedo — 0.15, 0.45, 0.9 —
would have caught it, in any of nine waves. None was written. The row that finally settled it is not
a numerical comparison at all but the **identity between the two forms**, evaluated on the interior:
`a_wet(a) − R_ext == (1−R_ext)·a·T_esc(0)·1/(1−a·G_rt(0))`, which states in code *which side of the
interface each function's argument lives on* — the thing the six defects all got wrong and no row
had ever said.

**And the interface-side question generalises past water.** Any pair (in-medium quantity, apparent
quantity) invites it: radiance and basic radiance `L/n²`; reflectance measured inside a dielectric
and the Saunderson-corrected one measured outside; linear and display-referred colour; energy
density and the flux crossing a boundary. The defect always looks like a plausible value of the
right type, and the type system cannot see it. ⚠️ **Put the side in the parameter's name.** It is
the only guard found so far that travels to the call site, where the mistake is actually made.

**The mechanical check, and it is cheaper than any of the above.** For every guard, ask what the
defect it is aimed at would multiply, and where the row evaluates. Three questions — the first two
answerable by reading one row, the third only by reading all of them together:

1. **Does the row's expression contain the defect's factor more than once?** If the quantity
   appears in both the numerator and the denominator, the row is structurally exempt from anything
   that scales it — no tolerance rescues that.
2. **Is the row's argument at a value where the defect vanishes?** Zero load, zero absorption,
   unit albedo, normal incidence: sweep the argument, or state in the row's own reason why the
   chosen value is where the defect is *largest* rather than where it is convenient.
3. **Is the row's argument a FIXED POINT of the operator the defect inserts or removes?** Unit
   albedo, zero load, a perfect reflector, an identity transform: these are where a formula proves
   itself, and therefore where a second copy of the formula is invisible. Find the fixed points of
   anything the code can apply twice, and put a guard strictly between them.
4. **Taking the rows on one function together, what region of its input domain do they cover, and
   do the shipped callers stay inside it?** This one is not answerable row by row and that is why
   it is separate: eleven individually reasonable rows can all sit on the same isotropic default,
   an identity can hold there that holds nowhere else, and a row count says nothing about it. The
   cheapest answer is a second implementation with different needs — it reaches arguments the
   first one never had a reason to.

**And the general rule this chapter already half-carries, now stated.** ⚠️ **Fire every deliberate
defect and record the rows it catches — a defect that catches nothing is a finding about the suite,
not a defect to delete.** Both silent bugs above were the most valuable output of the run that
found them; both would have been quietly removed as "not reproducible" by a project that read a
zero-catch as a bad bug rather than as a hole in the wall.

### The eleventh way: a test window pinned where the phenomenon is not

The eighth way is a test that touches nothing, the ninth a frame that reaches nothing, the tenth an
instrument that cancels the defect. This one is smaller than all three and it has a **signature**,
which is what makes it worth its own heading: the window a row measures in is part of the row, and
when it is pinned to the wrong place the row does not merely read low — it reads **easier the harder
the condition gets**, and that monotonicity is visible without knowing the right answer.

**Measured, and the row was this project's own.** A wave-refraction march is checked against Snell
taken about a *rotated* normal: a plane beach whose depth contours run at 10°, 20° and 30° to the
grid, with the marching integrator never told the rotation. Good test — the first refraction row in
that implementation that does not pass by construction. The first version pinned its measurement
window to the **grid centre**. On a rotated bed the ramp crosses each alongshore row over a
different span of `x`, so a centre-pinned window samples less and less of the ramp as the rotation
grows (`reference-impl/validate_beach.py`, both columns recomputed here):

| rotation | ramp cells in the centre row | centre-pinned window | window centred on the row that samples the ramp most fully |
|---|---|---|---|
| 0° | 234 | 0.000° | 0.000° — the test is an identity again |
| 10° | 236 | 0.186° | 0.186° |
| 20° | 123 | 0.059° | 0.310° |
| **30°** | **0** | **0.030°** | **0.277°** |

At 30° the centre row contains **no ramp at all**. The 5202 cells the window did hold were the deep
end, where the wave has barely turned, and the row reported **0.030°** — an order of magnitude
under the truth, with a tolerance of 0.5° that both columns pass. It is the fourth defect that suite
found in itself, and it was found by looking at the shape of the column rather than at any one cell.

⚠️ **The general form, and it is worse than a false pass: a test that gets easier as the condition
gets harder is reporting its own window, not the system.** A false pass is a number that is wrong.
This is a number that is wrong *and* carries a trend that argues for the code — the 0.030° column
reads as "the march handles obliquity beautifully, and better the more of it you apply", which is a
conclusion no one would state out loud and which the table states silently. The tell is
**monotone-in-the-wrong-direction**, and it costs nothing to look for:

1. **Sweep the parameter that makes the phenomenon harder, and plot the error against it.** Every
   row with a severity knob has one — rotation, incidence, contrast, velocity, depth. The expected
   shape is flat or rising. A falling curve is a finding *before* anyone checks the values.
2. **Ask where the row is looking, and whether the phenomenon is there.** Not "is the window big
   enough" — is it *where the effect lives*, given this parameter value? A window whose position is
   a constant and whose subject moves is a bug with a delay fuse: it is correct at the parameter
   value it was written at, which is invariably the easy one.
3. **Print the sample count with the number.** 5202 cells against 21 779 is the whole story, and it
   is one integer. A row whose population collapses as the condition sharpens is measuring
   something else, whatever its assertion says.

The sibling case is worth one line because it is the same failure with the sign the other way: the
same test excludes 60 rows at each alongshore edge, where the march's transverse differences go
one-sided and the error reaches **2.71°**. That exclusion is *also* a choice of window — and it is
legitimate only because it is stated, measured and attributed to a named boundary artefact rather
than trimmed until the row passed. **The difference between an exclusion and a fudge is entirely
whether the excluded region was measured and reported**, and a window is a claim either way.

### The twelfth way: a row that raises is worth less than a row that fails

Everything above is about rows that report the wrong thing. This one is about rows that report
**nothing**, and it lives in the harness rather than in any row — which is why it survives review
by every person who reviews rows.

**A test that raises an exception looks like a caught defect and is not.** It is worse than a
failure in one specific respect: a `FAIL` costs one row, and an unhandled exception costs that row
**and every row after it**, silently, with the run's own summary reporting the smaller number as
though it were the finding.

**Measured.** In this project's second reference suite, three deliberate defects destroyed the
morphological feature that later rows measured; those rows had no guard for a degenerate profile
and **raised** instead of failing; the deliberate-defect driver counted the exception as a single
catch and stopped. The defect `cap-not-dissipation` — which failed **eight** rows of that suite —
was recorded in the bug table as catching **one**. (Re-fired here on the current, larger suite it
catches **10 FAIL / 0 ERROR** in 408 s, which is the same defect against more guards; the 1-vs-8 is
that suite's own record and is quoted rather than re-measured, because the harness that produced the
1 no longer exists.) Note what did *not* go wrong: the defect was still caught, and
nothing was green that should have been red. That is exactly why it survived — **the harness lies in
a green-adjacent direction and the information it destroys is silent.** The suite had seven fewer
opinions than it believed, and the missing seven were the ones that would have described *how* the
defect propagates. A bug table is read as a map of which guards own which failure; this one had
seven blanks that looked like coverage decisions.

**And fixing the rows is not the fix.** That was the first response, and it left the harness able to
be lied to by the next such defect — which is a worse place to stand than it looks, because the
number that lies is green-adjacent and the information lost is silent. The structural fix is one
change: **the suite is a list of guarded sections, and an exception inside one costs that section
and nothing after it.**

```
def guard(fn, label, ctx):
    try:
        fn(ctx)
    except Exception as exc:            # the section, not the run
        error_row(label, exc)           # a fourth status: ERROR
    return ctx
```

Three properties, and each is load-bearing:

- **ERROR is a status distinct from FAIL**, because the two mean different things to a reader. FAIL
  says *this quantity is wrong*. ERROR says *this section did not finish, so its remaining rows were
  never evaluated* — and the summary line says exactly that, in those words. ⚠️ **A run that ends in
  ERROR is INCOMPLETE, not merely failing**, and a suite that cannot express that distinction will
  report a truncated run as a smaller problem than it is.
- **ERROR sets the exit code exactly as FAIL does.** A status that CI treats as passing is a comment.
- **The sections after it still run and still report their own failures**, which is the entire
  point: the run's information content stops being hostage to the first crash.

It earned its keep immediately and twice. On the first run after the refactor **four sections raised
at once** — a `NameError` from the refactor itself, a missing context key, a broadcast mismatch in a
new row, and a NumPy 2 API change — and the run still reported 58 passing rows and the two *real*
failures underneath them, instead of stopping at the first line and reporting nothing. On the next
run, the fix for the [eleventh way](#the-eleventh-way-a-test-window-pinned-where-the-phenomenon-is-not)
above introduced a loop variable `j` that collided with the row index used above it; the section died
on an `IndexError` **after its own row had passed**, and the guard let the run print 71 passing rows,
the ERROR, and the corrected measurement.

**The review test is one question of the harness, not of any row:** *what does this suite do when a
row throws?* If the answer is "stops", the suite's reported row count is an upper bound on what it
actually checked, and every defect that destroys a shared fixture will be under-reported by however
many rows sit downstream of it — which is exactly the defects that matter most, because a defect
that breaks one number breaks one row and a defect that breaks the scene breaks all of them.

### The thirteenth way: a tolerance the size of the thing it covers

Every way above is about a row that measures the wrong thing. This one measures the **right** thing,
in the right place, against an independent route, and reports nothing — because its tolerance was
sized from the disagreement it was written to accommodate. It is the smallest in this catalogue and it
is the one this project committed **against its own stated rule**: *a tolerance is justified from the
estimator's own error or a published uncertainty, **never** from the disagreement it is being asked
to excuse.* The rule was written down in `12`; the row below was written by the same hands.

**The row.** A closed-form exit transport is cross-checked at zero depth against a completely
different route: `slab_esc(0)` — a 2000-node Gauss–Legendre quadrature over the water-side cosine —
must equal `T_OUT_DIFFUSE = (1 − R_ext)/n²`, a 512-point midpoint rule over the **air**-side cosine
joined to it by Walsh's reciprocity relation. Two estimators, two variables, one identity, no shared
line: by the [eighth way](#the-eighth-way-is-about-the-test-not-the-measurement)'s standard this is a
good row. Its tolerance is `1e-4`, and its own justification string says why:

> *"the two disagree by 3e-5 and the tolerance is three of it"*

⚠️ **That sentence is the defect, written out in the row that contains it.** A tolerance set to three
times a *known* disagreement is a fixed report of the state the code was in on the day the row was
written. It passes at 3e-5. It also passes at 9e-5 — at which point the quantity has tripled its
error and the row has said nothing, in exactly the tone it says nothing when everything is fine.

**And the disagreement was not two estimators meeting at their joint accuracy — it was one estimator
being wrong** (`D`, all recomputed here on `reference-impl/optics.py`):

| | red | green | blue |
|---|---|---|---|
| `slab_esc(0)` − `T_OUT_DIFFUSE`, as shipped | +2.35e-5 | −3.30e-5 | +1.61e-5 |
| tolerance `1e-4`, as a multiple of that | **4.3×** | **3.0×** | **6.2×** |
| the air-side 512-point rule's *own* error (vs 4 000 000 nodes) | 1.8e-7 | 1.8e-7 | 1.8e-7 |
| the same row with the water-side rule **split at the kink** | +1.80e-7 | +1.79e-7 | +1.77e-7 |

The air-side side of the identity is converged to two parts in ten million. **The whole of the
disagreement belonged to the Gauss–Legendre rule**, and the corrected row lands exactly on the other
estimator's own residual — i.e. it stops being blind and starts being a test of the *only* remaining
approximation. Carried to the quantities that ship, the same rule is off by `+3.9 / −6.2 / +3.1 e-5`
relative on `slab_esc` and `−8.0 / +8.1 / −3.4 e-5` on `slab_trap`.

**Why the rule was wrong, and it is a numerical-methods lesson worth its own line.** The integrand
contains the internal Fresnel reflectance `R_int(μ)`, which **pins to exactly 1 past the critical
angle**. That is a *kink* — continuous, with a discontinuous first derivative, at
`μ = cos θ_c`. A Gauss–Legendre rule is built on the assumption of smoothness and spends its
accuracy on it; across a kink that assumption is void and the rule degrades to algebraic
convergence.

> ⚠️ **An integrand with a kink needs the interval split at the kink.** Not more nodes — the
> *interval*. Split at `cos θ_c` and use **400 nodes a side**, which is 800 against the shipped
> 2000, and the answer matches a converged reference to **eight digits** (2.3–3.9e-9). A fifth of
> the accuracy for 40% of the cost, purely from where the subdivision was put.

**The control, because a rate claim without one is a story.** Replace `R_int` with a smooth function
of the same range and change nothing else — same exponential, same `2μ` measure, same endpoints, same
rule. The single un-split 125-node rule then returns the integral to **6.7e-15**, i.e. machine
precision, and splitting it changes nothing. Put the kink back and 2000 nodes cannot reach 1e-4. The
endpoint behaviour of `exp(−τ/μ)` at `μ → 0`, the obvious other suspect, costs nothing at all.

**And here is the part that makes it a verification finding rather than a numerics footnote: a
convergence study would not obviously have caught it either.** The single rule's error against a
converged reference, per node count (green channel, `D`):

| N | 250 | 500 | 1000 | 2000 | 4000 | 8000 |
|---|---|---|---|---|---|---|
| relative error | +6.4e-4 | −3.0e-4 | +1.0e-4 | −6.2e-5 | +1.5e-5 | +5.2e-6 |

**It shrinks, and it changes sign almost every time.** Doubling the nodes always "improves" the
answer, so the usual informal test — *refine it and watch the digits settle* — reports success at
every step while the digits that settle are the wrong ones; and the sign flips mean two adjacent
refinements can straddle the truth and look like they bracket it. The test that does work is the one
that costs nothing here: **compare against a rule with a different structure, not a finer version of
the same rule.**

**The second guard was worse than the first, which is the point about coverage.** Beside that row
sits a 300 000-photon Monte-Carlo walk of the same slab, at a `6e-3` relative tolerance. That
tolerance is *correctly* justified — it names the estimator's own coefficient of variation and sits
under four standard errors, which is exactly the discipline this chapter asks for — and it is still
**97–196× too loose to see a 6e-5 effect.** So the quantity carried **two** independent guards, one
blind by a factor of 3–6 and one blind by a factor of 100–200, and a suite audit counting *rows*
would have scored it as unusually well covered.

**Three things to carry, and the first is the general form:**

1. ⚠️ **A tolerance chosen to accommodate a known imprecision cannot detect that imprecision
   growing.** This is the same failure as widening a tolerance to pass a row, committed *before*
   anything fails — which is why it never triggers the review ritual that catches the widening. The
   tell is textual and grep-able: any tolerance whose justification mentions the current
   disagreement rather than an estimator or a standard.
2. **A tolerance is a claim about the instrument, so state the instrument's error.** The Monte-Carlo
   row does this and the quadrature row does not, and the difference is that nobody ever computed
   the quadrature's error — it was inferred from the fact that the row passed. When the estimator's
   own error is genuinely below the interesting scale, say so and set the tolerance there; when it
   is not, that is a finding about the estimator.
3. **Count resolution, not rows.** Two guards whose resolutions are both coarser than the effect are
   zero guards. For every quantity a suite claims to cover, the reviewable number is *the smallest
   error any row on it could detect* — and it is the **minimum** over the rows, not the count of
   them.

The consolation, and it is real: **nothing shipped was wrong**. 6e-5 is four orders below anything
a frame resolves, and the chapter figures computed from these integrals are unaffected at the four
decimal places they are quoted to. What was wrong was the **suite's opinion of itself** — and a
suite that cannot resolve a defect four orders below the visible one is fine, while a suite that
*believes* it can is the thing this catalogue is about.

### The fourteenth way: two instruments agree, and could not have disagreed

Every way above is about one row. This one is about **two** rows that pass, cross-check each other,
and jointly establish less than either of them looks like it establishes on its own. It is the
cheapest kind of false confidence a suite can buy, because it is bought with a *correct* result.

**The case.** A rendered sea state has two independent readouts of the same wind `U₁₀`: the width of
the **sun glitter path**, which goes as `√mss` with Cox & Munk's `mss = 0.003 + 5.12×10⁻³ U`, and the
**whitecap coverage**, which goes as Monahan & O'Muircheartaigh's `W = 3.84×10⁻⁶ U^3.41`. One wind
drives both. Measured back off the scene-linear buffer they gave **5.84 m/s** and **6.00 m/s** —
**2.7% apart**. That reads like a cross-validation of the surface model. It is not.

**Compare the instruments before believing the agreement.** Two numbers per instrument: how hard the
observable pushes on `U`, and how well the observable can be measured.

| | `d(ln X)/dU` at 6 m/s | realistic measurement error | ⇒ `dU` |
|---|---|---|---|
| glitter path width | **0.0759** per m/s | 1% on a width read off a buffer | **0.13 m/s** |
| whitecap coverage | **0.5683** per m/s | a factor of **3**, which is inside the literature's own spread | **1.93 m/s** |

(`D`, both recomputed here; `d(ln W)/dU = n/U` exactly, and the width's derivative straight off Cox
& Munk's linear `mss`.) **The width is a 15× sharper wind instrument than the coverage**, so a 2.7%
agreement between them is *inside the coverage's own noise by a factor of fifty*. The two could not
have disagreed informatively. Nothing was learned.

⚠️ **And the trap has a second floor: the raw sensitivities run the *other way*.** Coverage is
`0.5683/0.0759` = **7.5× steeper** in `U` than the width is — by the sensitivity alone it is the
better instrument, and a reviewer who checks only `∂X/∂U` will pick it. What inverts the ranking is
the **measurement uncertainty**, and the useful quantity is the product. `dU = σ_lnX / |d(ln X)/dU|`
is the only figure that ranks instruments, and neither factor ranks them alone.

**Why the coverage's error really is a factor of three.** It is not sloppy measurement; it is the
published law. Monahan & O'Muircheartaigh (1980) is quoted everywhere as `3.84×10⁻⁶ U^3.41` while the
same paper's own optimal fit is `2.95×10⁻⁶ U^3.52`; Callaghan et al. (2008) is not a power law at all
but a piecewise fit with an onset at `U₁₀ = 3.70 m/s`. From the exponent's spread alone one coverage
maps to **5.67–7.66 m/s**, and the coefficient's spread across the literature is worse. **An
instrument calibrated against a quantity whose own law spans a factor of three cannot resolve better
than that**, however cleanly it is measured off the buffer — which is
[picking instruments whose parameters someone else has fixed](#pick-instruments-whose-parameters-someone-else-has-fixed)
read from the failure side.

**The rule, and it generalises past water:** *two instruments agreeing establishes nothing until
their `dU` are compared.* Before a cross-check is allowed to count as evidence, print the smallest
difference in the underlying quantity each side could have detected. If one is much larger than the
other, the agreement is a statement about the coarse instrument's tolerance and not about the
model — the same arithmetic as the [thirteenth way](#the-thirteenth-way-a-tolerance-the-size-of-the-thing-it-covers)'s
*count resolution, not rows*, applied across instruments rather than within one.

**And the level is the other half of it.** At `U₁₀ = 6 m/s` the whitecap coverage is **0.173%** of
the sea surface. A render with conspicuous open-water foam therefore has a *different* wind from the
one its glitter path reports — which is the check worth writing, because unlike the agreement above
it can fail.

## When the target is an approximation, the bar changes kind

Everything above is about verifying a renderer against the world. This section is about the other
job — verifying a **cheap** renderer against an expensive one — and the reason it needs its own
heading is that the bar for the two is not the same *kind* of thing, and using the first for the
second is the most common way an optimisation programme goes quietly wrong.

**For a photorealistic reference the bar is a photograph**, or a standard of the form *a viewer
should have to wonder whether it is one*. It is a good bar: it is holistic, it is impossible to
overfit to a single quantity, and it catches every error the eye is built to catch. **For an
approximation it is useless**, and the reason is not that it is subjective — it is that the errors
that matter to an approximation are, by selection, exactly the ones the eye does not catch. An
approximation that produced a visible error would have been rejected on the first frame.

**The evidence, and it is a bad enough result to be worth stating in full.** One project's water
work found four separate transport faults in a single session — a missing up leg, two correlated
integrals split apart and multiplied, a caustic read on the wrong coordinate, and an over-supplied
sky on a vertical face — at sizes of **5% to 25%** on named radiometric quantities. **Every one of
them looked fine.** Not "looked slightly off and was dismissed": looked fine, in frames that were
being stared at daily by people looking for exactly this. A perceptual image metric would have
scored all four as passes.

**Why, in one table.** A view transform compresses. Through the sRGB EOTF a *linear* error becomes
an encoded error roughly `(1 + e)^(1/2.4)`, so:

| scene-linear error | encoded levels of 255, at L = 0.05 | at L = 0.18 (mid grey) | at L = 0.40 |
|---|---|---|---|
| +5% | 1.6 | 2.7 | 3.8 |
| +10% | 3.1 | 5.3 | 7.4 |
| +25% | 7.5 | **12.8** | 17.9 |

(`D`, recomputed here through the exact sRGB transfer function.) A 5% radiometric error is **two to
four levels** — below the threshold for a *flat patch* and far below it in textured, caustic-lit,
noisy content where every local neighbourhood already varies by more than that. And a 25% error is
about **13 levels at mid grey**, which is visible as a difference *between two images shown side by
side* and is not visible as a property of one image. Both directions of that sentence matter: the
metric that would catch 25% is a *difference* metric, and a difference metric needs the reference
image, which is the thing this section is about acquiring.

**So the bar becomes the reference itself, and the question changes shape.** Not *does this look
right* but **how many percent off, per channel, on a named quantity**. That is what a reference
implementation is *for*, and it is the only formulation under which a 5% fault is a failing test
rather than a matter of opinion.

**It works only because the reference is deterministic.** A quadrature reference re-run twice
returns the same digits, so a 3% difference is a **number**; a Monte Carlo reference re-run twice
returns two different numbers, so a 3% difference is a number *plus noise*, and separating them
costs samples on every single score. That is not an argument against path-traced references in
general — it is an argument that the reference for an approximation loop should be the deterministic
one if a deterministic one is achievable, because the loop will read it thousands of times and the
variance is paid on every read. If it must be stochastic, freeze the seed and report the estimator's
own standard error next to every score, or the tolerance discussion above becomes unanswerable.

**Three things must be in place before the first approximation is written, and the ordering is not
negotiable.**

1. **A frozen ground-truth set, committed to the repository.** Scene-linear buffers *and* the
   derived scalars — the named quantities the approximation will be scored on, not just images.
   Without it every score costs a full reference render, which puts the slowest thing in the
   project in the innermost loop and guarantees the loop is run less often than it should be. Dump
   it, freeze it, and version it: a ground truth that moves is not one.
2. **An error metric fixed in advance.** Per channel, relative, on named quantities. Explicitly
   **not** a perceptual image metric, for the reason the table above gives. The ordering is the
   whole point: **decide the metric before the first approximation exists, so it cannot be chosen
   to flatter one.** A metric selected after the candidate is a fit, by the same argument that makes
   a tolerance widened to pass a row worthless — and it is harder to see, because choosing a metric
   feels like methodology rather than like tuning.
3. **A cost budget.** Platform, frame time, memory for LUTs. Without it "approximation" is unbounded
   and there is nothing to optimise against: every candidate can be improved by spending more, so
   the loop has no stopping rule and no way to compare two candidates that are both accurate
   enough. **An approximation is only meaningful relative to what it is allowed to cost**, and the
   budget is the half of the pair that gets deferred because it belongs to somebody else.

**Two more preconditions that are specific rather than general, and both are about the ground truth
rather than the metric.** Any quantity in the reference that is **itself unresolved** propagates
into every approximation scored against it — so an open 2× discrepancy in the reference is not a
row to close later, it is a reason not to start. And at least one **cross-consistency** reading
should be in the frozen set: a scene that exposes one underlying field through more than one path,
so that an approximation which passes each reading separately can still be caught failing their
agreement. That failure is invisible in any single view by construction, which is precisely why it
must be in the set before the loop starts rather than added when something looks wrong.

⚠️ **And the converse belongs in the same breath: such a scene has to be checked for whether its two
paths *could* have disagreed.** Two readings of one field whose resolutions differ by an order of
magnitude will agree whatever the approximation does, and the agreement will be reported as
corroboration — [the fourteenth way](#the-fourteenth-way-two-instruments-agree-and-could-not-have-disagreed).
Print each path's smallest detectable difference *in the underlying field* alongside the agreement,
or the multi-path scene is one path plus a decoration.

## Review checklist

Ordered by frequency of real defects in shipped terrain renderers. State findings as
symptom → mechanism → minimal fix; do not rewrite a renderer that has one wrong bias.

1. Is the LOD boundary crack contract explicit (which of `01`'s five), and is it asserted —
   adjacency constraints, morph = 1.0 at boundaries — rather than assumed?
2. Does every pass (depth, shadow cascades, velocity, main) consume the *same* LOD selection and
   morph result, computed once per frame?
3. Are shadow bias values derived from per-cascade texel world size, and are cascade projections
   snapped to texel increments?
4. Are splat weights premultiplied before mip generation, and are all per-tile bakes (normal,
   AO, splat) computed with a neighbor apron wider than the largest derivative kernel?
5. Is depth reversed-Z end-to-end (projection, clears, comparisons, HiZ reduce op), verified at
   the horizon-distance control?
6. Are culling bounds conservative under every displacement source — skirts, geomorph, WPO,
   in-flight remesh — with a named inflation owner per term?
7. Is all GPU→CPU feedback (streaming requests, counters) on an N-frame async ring, with zero
   synchronous maps anywhere in the frame?
8. Do normals and height-derived material inputs morph/fade with the same factor as geometry,
   and do normal mips encode roughness for distant specular?
9. Are there hysteresis bands on every threshold-driven binary state (LOD split/merge, residency
   wants, cascade membership)?
10. Do physics/collision and audio/gameplay queries sample the authoritative heightfield, with
    the render-vs-collision divergence bounded and stated?
11. Are the debug view modes and the freeze-camera control actually shipped in this build — not
    "planned"?
12. Is there a worst-case-view replay with budget assertions wired into CI, and did it run on
    this change?
13. If anything in this change is an **approximation of a reference**, do the three preconditions
    exist — a frozen ground-truth set, an error metric fixed before the candidate, and a cost
    budget — and was the metric chosen before the candidate rather than after?
14. Is any quantity the ground truth is scored on still open in the *reference*? An unresolved
    discrepancy there propagates into every approximation measured against it.
15. Does every triple that crosses between **irradiance and radiance** say which it is in its own
    name, and is every bare constant near 3.14 or 0.318 in a shading term accompanied by a
    derivation? ([An irradiance used as a radiance](#an-irradiance-used-as-a-radiance))
16. Which code does the golden set actually **reach**? A branch with zero subsamples across every
    frame in the suite is a finding, and a viewpoint chosen for reach — not for beauty — is the
    cheapest way to close it. ([The ninth way](#the-ninth-way-the-code-no-pixel-reached))
17. For every row with a severity knob, does the error **rise** as the condition hardens? A row
    that gets easier the harder the case is reporting its own window, and the sample count printed
    beside it will show the population collapsing.
    ([The eleventh way](#the-eleventh-way-a-test-window-pinned-where-the-phenomenon-is-not))
18. What does the suite do when a row **throws**? If the run stops, its reported row count is an
    upper bound on what it checked, and ERROR must be a status distinct from FAIL that still sets
    the exit code. ([The twelfth way](#the-twelfth-way-a-row-that-raises-is-worth-less-than-a-row-that-fails))

## Sources & provenance

| Claim | Tier |
|---|---|
| Symptom → mechanism → minimal fix review discipline; control-test doctrine ("a metric with no control is not evidence") | **F** (house doctrine, mirrored from terrain-architect `09`) |
| `L = ρE/π` for a Lambertian receiver, and therefore that an irradiance/radiance confusion is a factor of ~π | **P** (definitional radiometry). The ×3.29 / 3.44 / 3.38 measured on a shade sail, and the derived `[0.627, 0.656, 0.796]` behind it, are **D** — one panel in `12`'s reference implementation |
| The ninth way: a frame is a sampling of the code, and its coverage is the union of its framings | **F** (this skill's composition, stated as doctrine). The **0 of 8 640 000 subsamples** that let a 3.4× error stand for three rounds is **D**, measured on that implementation's hero frame |
| Instruments with published parameters: draught as an output, and the tolerance the standard itself supplies | **P/D** — FINA Water Polo Rules give the size 5 circumference (0.68–0.71 m) and mass (0.400–0.450 kg) bands (`P`, equipment schedule); every derived figure — 75 kg/m³, 39.61 mm, 38.40–40.79 mm across the mass band, and the inflatable's 8.42 kg/m³ / 5.27 mm — is arithmetic recomputed here (`D`), the last of which **corrects** a 9 mm figure in circulation |
| T-junction sparkle: watertight raster guaranteed only across shared-vertex edges | **D** (D3D/Vulkan raster rules) + **F** (terrain reading) |
| Slope-scaled shadow bias sized to texel world footprint; cascade texel snapping vs shimmer | **P/F** (standard shadow-map literature + practice) |
| Specular/normal aliasing fixed by roughness-encoding normal mips (Toksvig/vMF family) | **P** (Toksvig 2005; Olano & Baker 2010, LEAN/vMF family) |
| Non-premultiplied splat weights causing mip halos | **F** (standard practice; same mechanism as alpha premultiplication) |
| VT page pop-in as feedback→resident latency; latency percentile as the shipping metric | **F** |
| Reversed-Z + float depth for distant-terrain precision | **D/P** (documented depth-precision analyses) + **F** (adoption) |
| Quad overshading dominating below ~4 px/tri on fixed-function raster; ≲1 px/tri viable only with visibility-buffer-style shading | **P/F** (raster behavior documented; thresholds are judgment) — Burns & Hunt, JCGT 2013 for the deferred-material remedy | 
| Two-phase visibility history keyed by stable IDs; HiZ convention bugs presenting at silhouettes | **T/F** (Haar & Aaltonen 2015; Karis 2021; failure reading is practice) |
| Golden-image testing with perceptual metrics; TAA warm-up/determinism caveats | **F** (SSIM/FLIP are **P**-tier metrics; the testing recipe is practice) |
| Mesh-gen thread-count determinism as a CI gate | **F** (mirrors terrain-architect determinism doctrine) |
| Worst-case-view (peak vista) profiling doctrine | **F** |
| Budget bands (px/tri, culling-ms, latency percentiles) | **?** (directionally sound; exact numbers are per-title judgment) |
| PIX / Nsight / RenderDoc / Radeon GPU Profiler roles; RenderDoc replay timings not production costs | **D** + **F** (usage caveat) |
| Checklist ordering by defect frequency | **F** (experience-shaped, unverifiable) |
| That iPhone captures are tagged Display P3 (since iPhone 7), and that dropping the ICC profile reinterprets them as sRGB | **D** (Apple's documented capture behaviour) + **F** (that the drop is a common pipeline accident) |
| The `P3 → sRGB` linear matrix `[[1.224940, −0.224940, 0], [−0.042057, 1.042057, 0], [−0.019638, −0.078636, 1.098274]]` | **D** — derived here (2026-08) from the two primary sets and the shared D65 white point via XYZ, not quoted from a table; reproducible from those primaries alone |
| The misread-P3 error table — −28.2% / −51.5% R/B on water triples, +13.5% on warm sandstone, +2.2% on grey stone, `(70,165,185)` falling outside the sRGB gamut, luminance error ≈1% | **D** — arithmetic here on that matrix, in linear light, for *those* triples; the transferable claim is the **asymmetry** (largest on the saturated subject, smallest on the neutral references) and its cause, not the percentages |
| That the sRGB and Display P3 luminance weights are `(0.2126, 0.7152, 0.0722)` and `(0.2290, 0.6917, 0.0793)`, hence a ~1% luminance error from the misread | **P** (both are the `Y` rows of the standard primary matrices) + **D** (recomputed here) |
| That automatic white balance biases a saturated frame toward neutral, and that a display-referred tone curve deepens the toe — with the sign of each, and the resulting one-sided bounds | **F** (universal camera-pipeline behaviour; no single citation) + **D** (direction and rough magnitude independently confirmed by an observer present at the reference shoot, for *one* subject — a bounded corroboration, not a calibration) |
| The within-frame-ratio method, the "prefer pairs close in level" precondition, and the three cancelling pairs | **F/D** — the tone-curve precondition is the local-slope argument (arithmetic); which pairs cancel what is derivation (`12a`); that this is the right instrument is this skill's composition, and it was corrected mid-project after the tone curve was pointed out |
| `L = K·N²/(ISO·t)`, `K ≈ 12.5`, as the EXIF route to a scene luminance | **P** (the ISO 2720 / standard reflected-light-meter relation; `K` in 10.6–13.4 by manufacturer, 12.5 for Canon/Nikon — quoted from model knowledge, **not** re-verified against the standard, so treat it as ±10%) |
| That a *render's* own PNG is display-referred too, and that inverting the sRGB EOTF on it recovers display-linear rather than scene-linear | **F/D** — universal of any view-transformed output (no citation needed, and the same mechanism as the seventh way's second axis); **D** for the episode, committed on this project's own frames and reproduced from the render's scene-linear buffer |
| The three-factor chain `0.706 × 0.953 × 0.996 × 0.590 = 0.395` against a true 0.706, i.e. 1.79× | **D** — arithmetic recomputed here on the reference implementation's whole-basin frame; the median/mean skew ratio 0.786 and the region factor 0.590 are properties of *that* frame, that occluder and that sun. ⚠️ The chain had been quoted against a "true 0.735", which is the **hero** frame's ratio, not that frame's; the factor is 1.79, not 1.86. What transfers is the **ordering rule** — check the region before the colour space — and the observation that the tone curve was the smallest of the three here (×0.996) while being the one the episode was named after |
| That a photographic bar cannot verify an approximation, and that the bar becomes the reference plus a named-quantity per-channel metric | **F** (house doctrine, composed here) + **D** for the episode — four transport faults of 5–25% on one water renderer, every one of them invisible in the frame |
| The linear-error → encoded-level table (5% ≈ 2.7 levels and 25% ≈ 12.8 levels at L = 0.18 of 255) | **D** — computed here through the exact sRGB transfer function, 2026-08. It is a property of the *view transform*, so it carries to any sRGB-encoded output and not to a different one; recompute for PQ or for a filmic curve, where the toe and shoulder change it by more than the percentages do |
| That a deterministic quadrature reference makes a 3% difference a number while a Monte Carlo one makes it a number plus noise, hence the seed/standard-error requirement | **F** (elementary, but the *consequence for loop design* — variance paid on every read — is this skill's composition) |
| The three preconditions (frozen ground truth, metric fixed in advance, cost budget) and the two ground-truth preconditions (no open discrepancy, one cross-consistency reading) | **F** (house doctrine; the metric-before-candidate rule is the same argument as "never widen a tolerance to pass a row", and the cross-consistency requirement generalises `12`'s split shot) |
| The tenth way: a ratio cancels whatever multiplies both its terms, so a suite made only of ratios is blind to common-factor errors; and a guard evaluated where a defect is inert is not a guard | **F** (house doctrine, and the structural complement of the seventh way's within-frame-ratio method — the same cancellation, read as a cost) + **D** for the case: the ×50 bed-power defect passing a 53-row suite, the `u³` ratio row unchanged to twelve figures, the two absolute rows that fire (2.61 → 130.51 W/m², 373 → 18 671 mg/L), and the `spm = 0` degeneracy table are all `reference-impl/beach_optics.py` + `validate_beach.py`, **re-fired and recomputed here** (2026-08) rather than quoted. The third shape — the eleven lobe rows all sitting at `cov = None`, where `1/(uᵀQu)` and `uᵀQ⁻¹u` are equal by an identity — is `reference-impl/atmosphere.py` + `validate.py` (defect `7fe9538`, guards `f83b42c`); its flux table is **recomputed here** (2026-08) off `validate._lobe_flux` against both forms, and the 1378-in-radiance glint is measured in scene-linear off two full `render.py` hero passes, not read from a PNG. What transfers is the three-question check and the "one absolute row per quantity" rule; the numbers are those scenes' |
| The eighth way: a test's power is the surface area it shares with the code under test | **F** (house doctrine, and the general form of the fourth way's "two methods that read one premise are one method") + **D** for the case — the audit's one borrowed name, the lossless-limit/photon-walk pair agreeing to 0.15%, and the four-bug table are all `reference-impl/validate.py`, re-evaluated here; that **the lossless limit alone passes three of the four** was verified by evaluating each variant against the limit, not quoted |
| The eleventh way: a test window is part of the test, and a row that gets *easier* as the condition hardens is reporting its window rather than the system | **F** (house doctrine; the monotone-wrong-way tell and the three instruments are composed here) + **D** for the case — the oblique-Snell row in `reference-impl/validate_beach.py`, **both columns recomputed here** (2026-08) rather than quoted: 0.186 / 0.310 / 0.277° centred on the best-covered row against 0.186 / 0.059 / 0.030° centred on the grid, with 236 / 123 / **0** ramp cells in the centre row and 5202 window cells surviving at 30°. The 2.71° edge artefact and the 60-row exclusion were recomputed with them. Those numbers are that march, that grid and that bed; what transfers is the signature |
| The thirteenth way: a tolerance sized from the disagreement it accommodates reports the state the row was written in, and coverage is the *minimum resolution* over the rows rather than their count | **F** (house doctrine; the "count resolution, not rows" rule and the grep-able tell are composed here) + **D** for the case, all recomputed 2026-08 on `reference-impl/optics.py` and `validate.py` rather than quoted: the shipped 2000-node single Gauss–Legendre rule against a split rule (400 nodes either side of `μ = cos θ_c`) and a 4 000 000-node reference — `slab_esc(0) − T_OUT_DIFFUSE` = +2.35 / −3.30 / +1.61 e-5 as shipped against +1.80 / +1.79 / +1.77 e-7 split, the air-side 512-point midpoint's own error at 1.8e-7, and `+3.9 / −6.2 / +3.1 e-5` / `−8.0 / +8.1 / −3.4 e-5` relative on `slab_esc` / `slab_trap`. ⚠️ **The kink attribution is a control, not an inference**: substituting a smooth reflectance for `R_int` and changing nothing else returns the *un-split* 125-node rule to 6.7e-15, which is what rules out the `exp(−τ/μ)` endpoint as the cause. The sign-alternating convergence table (250 → 8000 nodes) is `D` on the same rule. The `1e-4` and `6e-3` tolerances and the quoted justification strings are that suite's own text; the 97–196× figure is arithmetic on them. **Nothing shipped was wrong** — the effect is four orders below anything a frame resolves and does not move any chapter figure at its quoted precision — which is stated in the section because the finding is about the suite's self-assessment, not about the render | 
| The fourteenth way: two instruments agreeing establishes nothing until their `dU` are compared, and the raw sensitivities can rank them the opposite way from the achievable precisions | **F** (house doctrine; the `dU = σ_lnX / |d(ln X)/dU|` framing and the "print each path's smallest detectable difference" rule are composed here) + **P/D** for the case. `P`: Cox & Munk's `mss = 0.003 + 5.12×10⁻³ U`; Monahan & O'Muircheartaigh (1980) `W = 3.84×10⁻⁶ U^3.41` **and the same paper's own optimal `2.95×10⁻⁶ U^3.52`**; Callaghan et al. (2008, GRL 35, L23609) piecewise with an onset at 3.70 m/s. `D`, all recomputed here (2026-08) on `reference-impl/beach_optics.py` and `beach_foam.py` rather than quoted: `d(ln width)/dU = 0.0759` and `d(ln W)/dU = 0.5683` per m/s at 6 m/s, `dU` of 0.132 and 1.933 m/s, ratio **14.7×**, `W(6) = 0.173%`, and the exponent-spread band **5.67–7.66 m/s**. ⚠️ **The sensitivity ratio is 7.49× the other way** — coverage is the steeper instrument and the *worse* one — and that inversion is this pass's, recomputed rather than carried; it is the half that makes the rule non-obvious. The two readouts' own agreement (5.84 vs 6.00 m/s, 2.7%) is that scene's; what transfers is the ranking arithmetic |
| The twelfth way: an unhandled exception costs its row *and every row after it*, so ERROR must be a status distinct from FAIL that still sets the exit code | **F** (house doctrine, and the harness-level sibling of the eighth way) + **D** for the remedy — the guarded-section harness is `reference-impl/validate_beach.py`, and `cap-not-dissipation` was **re-fired here** (2026-08): **10 FAIL / 0 ERROR** in 408 s, no section raising, which is what the fix is supposed to look like. ⚠️ Neither number in the 1-vs-8 is re-measured. The **8** is that defect's count against the *wave-2* suite and the **1** against the superseded harness that produced it; this run cannot reconstruct either, and the current suite has more rows, which is why re-firing gives 10 rather than 8. Both are quoted from that suite's own record. The transferable claim — that a raising row truncates a run, that the truncation is silent, and that ERROR must be a status — is structural and needs no measurement; the 1-vs-8 is an illustration and should be cited as one |
