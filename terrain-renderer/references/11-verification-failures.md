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
  [`12`](12-water-rendering.md#radiance-is-not-conserved-across-the-interface).
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
[`12a`](12a-water-derivations.md#the-calibration); what it defends against a fitted-constants
objection is [`12`](12-water-rendering.md#radiance-is-not-conserved-across-the-interface).

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

## Sources & provenance

| Claim | Tier |
|---|---|
| Symptom → mechanism → minimal fix review discipline; control-test doctrine ("a metric with no control is not evidence") | **F** (house doctrine, mirrored from terrain-architect `09`) |
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
