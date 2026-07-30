# Roads, decals, runtime modification, and the physics handoff

This chapter owns everything that stamps onto, deforms, or reads back the rendered terrain at
runtime: roads and spline features riding the surface, decals persistent and projected, runtime
craters and trenches over streamed tiles, the collision mirror the physics engine simulates
against, and the point queries gameplay fires at the ground every footstep. Road *network
generation* — where roads go, grading and terrace carving during cook — is terrain-architect's
`20`; water surfaces and buoyancy fields are `12`; the runtime state layers roads and decals must
composite against are `13`, and the map registry that keeps render and gameplay reading the same
truth is `14`.

Contents: [Roads and splines on terrain](#roads-and-splines-on-terrain) ·
[The coplanar toolkit](#the-coplanar-toolkit-z-fighting-avoidance) ·
[Decals on terrain](#decals-on-terrain) ·
[Runtime terrain modification](#runtime-terrain-modification) ·
[The physics and collision handoff](#the-physics-and-collision-handoff) ·
[Gameplay readback and surface queries](#gameplay-readback-and-surface-queries) ·
[Tri-fold ladder](#tri-fold-ladder) · [Pitfalls](#pitfalls) ·
[Sources](#sources--provenance)

## Roads and splines on terrain

Three families render a road; every shipped scheme is one of them or a hybrid. Choose by what the
road must *be*: a paint job, a silhouette, or part of the ground.

| Family | Mechanism | Buys you | Costs you | Wins when |
|---|---|---|---|---|
| Splat / VT injection | Stamp road material along the spline into weightmaps or VT/RVT pages (`07`) | Perfect conformance, zero extra geometry, zero z-fighting, one material resolve | No silhouette, no camber, no crown; UV flow along the road is faked or absent; blurs at VT texel density | Trails, dirt paths, tire-worn tracks, anything flat and diffuse |
| Draped ribbon | Spline-swept mesh, vertices projected onto the heightfield + offset | Real silhouette, camber, curbs; authored UV flow (lane lines, wear strips); independent material | Coplanar with terrain → z-fighting; LOD crawl against the ground beneath; skinning cost per spline edit | Elevated detail (bridges' approaches, raised rails, curbs), indie budgets, roads over terrain you may not edit |
| Terrain-conforming integration | Flatten/carve the heightfield under the road (cook via terrain-architect `20`, or runtime height overlay `14`) and render road as terrain material layers | Road IS the ground: one vertex path, no z-fight, no crawl, physics agrees for free | Needs heightfield edit rights + re-cook or overlay machinery; camber limited to heightfield resolution; junction authoring tooling | Drivable roads in AAA open worlds — the default |

**Splat/VT injection.** Rasterize the spline's swept footprint into the weightmap (cook) or into
RVT pages as they render (`07`'s runtime composite — UE's RVT is the branded example, N/D: spline
and decal-like materials write into the page, meshes and grass sample the result back). The stamp
carries a cross-section profile — centerline material, edge blend, verge — as a function of
signed distance to the spline. Because it lives in the material domain it obeys `07`'s compositing
order and costs nothing per frame after the page is cached. It cannot change the silhouette: a
splat road over rough ground reads as painted-on rock the moment the sun grazes it.

**Draped ribbon.** Sweep a cross-section along the spline; project each vertex to the terrain and
offset upward. The two structural failure modes are the subject of the next section (coplanarity)
and this rule: **the ribbon must sample the height the terrain is drawing, not the source
heightfield.** The ground under the ribbon is LOD'd and morphed (`01`); the source data is not. A
ribbon seated on source heights floats or sinks as the terrain LOD changes under it and *crawls*
during geomorph — identical doctrine to `15`'s instance seating, same fix:

```hlsl
// Ribbon vertex conform — evaluate the terrain's OWN vertex path at the ribbon vertex XZ:
// same tile LOD selection, same morph factor, same displacement the ground applies.
float h = EvalTerrainVertexHeight(worldXZ, lodOf(tileAt(worldXZ)), morphOf(cameraDist));
pos.y   = h + crossSection.heightOffset;   // offset ≥ max residual error of that LOD
```

Recompute (or GPU-recompute) conforming when the tile under a ribbon segment changes LOD, and
give ribbons their own LOD ladder (cross-section vertex count, segment subdivision) driven by the
same screen-space-error currency τ (`01`) — a 16-vertex cross-section 2 km away is pure waste.

**Terrain-conforming integration.** The AAA default for anything drivable. The heightfield under
the road is flattened/graded to the spline's profile — at cook by terrain-architect `20` (which
owns grading, cut/fill, switchback legality), or at runtime as a height *delta overlay* (`14`,
same machinery as craters below) when roads are player-built. The road surface then renders as
terrain: either extra material layers stamped into the splat/VT domain (family a on top of the
carve) or a ribbon whose vertices are *exactly* the terrain's vertices (shared vertex path — see
next section). Physics, decals, snow (`13`), and vegetation suppression all inherit correctness
because there is only one surface. Far Cry 5's pipeline is the public example (T): roads are
splines baked into the terrain data and its material stack, not meshes floating above it.

**Junctions and intersections.** Splines model segments; junctions are patches. Author them as
small mesh patches or stamp masks that own their footprint and blend to each incoming segment's
cross-section over a handoff band — do not try to union ribbon geometry at runtime (self-overlap
double-draws decals and darkens; welding is `11`-grade seam denial). In the injection family,
junctions are just another stamp with priority ordering: later/higher-priority stamps win texels,
weights renormalize (`07`).

**Wear and detail layers.** Tire tracks, oil strips, patch repairs, gravel spill live as decals
(next section) or as secondary injected layers keyed to distance-along-spline — never as more
ribbon geometry. Wear is the cheapest realism a road gets; a pristine ribbon reads CG instantly.

**Road LOD sync.** Whatever family: the road's LOD schedule is a *function of* the terrain's, not
an independent controller. Ribbon subdivision follows the underlying tile LOD; injected stamps
must exist in every VT mip the terrain can sample (stamp into the mip chain, or re-stamp on page
generation at that mip); conforming roads inherit terrain LOD outright. Two controllers refining
on different schedules is the crawl artifact — the waterline-crawl of `12`, on land.

## The coplanar toolkit (z-fighting avoidance)

Anything rendered coplanar with terrain — ribbons, projected decal proxies, overlay quads —
fights the ground in depth at distance. Reversed-Z and camera-relative transforms (`09`) buy
precision headroom but do not remove coplanarity. The toolkit, in escalation order:

| Tool | Mechanism | Side effects — know before shipping |
|---|---|---|
| Constant + slope-scaled depth bias | Rasterizer adds `DepthBias·r + SlopeScaledDepthBias·MaxDepthSlope` (clamped by `DepthBiasClamp`) to primitive z (D3D semantics, D) | Bias is per-primitive and view-dependent; too much → road floats, contact shadows detach, shadows peek under the ribbon edge. Shadow pass needs its *own* bias policy — the base-pass bias does not apply there and double-biasing causes acne or peter-panning (`10`) |
| Pixel depth offset (PDO-style) | Shader pushes output depth toward the camera per-pixel, optionally scaled by height-map contact | Disables early-Z on that draw; breaks depth-equal prepass matching; TAA/velocity mismatch if depth moves but motion vectors don't |
| Shared vertex path | Road vertices ARE terrain vertices (same grid, same morph, y + ε or exact) with material swap | The only true fix — coplanarity becomes identity. Requires conforming family or heightfield edit rights |
| Stencil-masked suppression | Opaque road writes stencil; terrain pixels under it are stencil-rejected (or the tile mesh carries a hole mask) | No overdraw, no fight — but the mask must cover every terrain LOD's footprint of the road, or coarse LODs leak through at distance; the same watermask discipline `12` uses under opaque-deep water (`06` payload) |

Doctrine: bias is a *distance-limited* patch — the required bias grows with slope and distance
until it exceeds contact-shadow tolerance, so declare the range where bias is legal and switch
family beyond it (typically: ribbon+bias near, injection far, where silhouette no longer reads).
If a road must be correct at every distance, it must share the terrain's vertex path. That is the
whole argument for the conforming family.

## Decals on terrain

Two mechanisms, chosen by lifetime:

| | Projected/deferred decal | VT-page injection |
|---|---|---|
| Mechanism | Box/frustum projected into G-buffer per frame | Rasterized once into the RVT/VT page (`07`); sampled as ordinary terrain texture thereafter |
| Per-frame cost | Per decal, per pixel covered, every frame | Zero after injection (page cache hit) |
| Lifetime | Frames to seconds; count-limited | Persistent until page eviction/invalidation |
| Response to terrain LOD | Projects onto whatever geometry is there — immune to LOD | Lives in texture space — immune by construction |
| Best for | Transient: muzzle scorch this second, blood spray mid-fight, blast rings | Persistent: tire wear, scorched ground, oil stains, road grime — anything that should still be there in an hour |

The production pattern is a **promotion pipeline**: spawn transient effects as projected decals
(instant, no page churn), and if they persist past N seconds, bake them into the VT page and kill
the projector. Amortized cost collapses — a battlefield of 500 scorch marks is 500 page-space
rasterizations *once*, not 500 projectors per frame.

**Ordering contract.** Decals composite at a declared slot in the surface stack, and the slot is
law (`14` owns the registry): base splat resolve (`07`) → injected/persistent decals (they are
material, they belong in the page) → runtime state layers (`13` wetness/snow compose OVER the
resolved surface, projected decals for transients land here too) → lighting. Violating it is
visible: a scorch injected *after* wetness double-darkens when rain hits (`13`'s
double-darkening pitfall — porosity darkening applies to albedo once); snow that composites under
a projected decal leaves bloodstains floating on top of fresh snowfall.

**Budgets and eviction.** Projected decals get a hard count and screen-area budget with
oldest/smallest-first recycling — decal pools, never unbounded spawn. Injected decals cost page
*invalidations*, so budget injections per frame (they share `07`'s page-render budget) and defer
under load. And record every persistent decal in a CPU-side stamp list keyed by page footprint:
VT pages are a **cache** — eviction is normal operation — so when a page is re-rendered after
eviction, its stamp list replays into it. Injection without a replay list means every persistent
mark in the world silently disappears the first time the camera leaves and returns. That replay
list is also the save-game and network representation (below).

## Runtime terrain modification

### The destruction ladder

"Destructible terrain" spans five tiers, and the single most expensive mistake is building one
tier above what gameplay actually needs — each rung up multiplies the invalidation surface. Name
the tier first (it is the Paradigm procedure's *mutation* question, answered precisely):

| Tier | Mechanism | Owner | Buys | Cannot do |
|---|---|---|---|---|
| 0 · Cosmetic | Decals / VT-injected scorch, splat swaps | this chapter, `07` | Bullet marks, burn scars, at near-zero cost | Any geometry change |
| 1 · Surface state | Displacement in camera-following state targets | `13` | Trails, trampling, shallow ruts; refills over time | Persistence at scale, deep cuts |
| 2 · Height delta | Persistent delta overlays over immutable tiles (below) | this chapter | Craters, trenches, terraforming on heightfield worlds | Overhangs, tunnels — no y-fold |
| 3 · Voxel re-extraction | Field CSG + budgeted local remesh | `05` (smooth), `04` (blocky) | Arbitrary digging, caves, Minecraft-through-Deep-Rock digging | Heightfield's memory/streaming cheapness |
| 4 · Hybrid zones | Heightfield world + voxel representation in declared destructible regions | `05` §hybrids + this chapter | AAA compromise: voxel cost only where gameplay pays for it | Free-form destruction *anywhere* |

The Minecraft end (tier 3, blocky) is the *simple* case precisely because the whole world already
pays the voxel tax: edit → light update → remesh on the `04` budget queue, done. The 2026 AAA end
is almost never "voxels everywhere" — it is tier 2 for the open world plus tier 4 pockets where
design promises digging, because tiers 0-2 preserve the heightfield's streaming, LOD, and
collision economics that chapters `01`/`06` are built on.

**The invalidation checklist — where big destruction actually gets expensive.** A visible edit
must propagate to every consumer that ever cached the old ground, and the tier-3/4 rungs pay this
per edit, not per feature. Route each: collision commit and its latency window (below, item 5);
vegetation re-scatter of affected cells (`15`); VT page and decal re-composite over the area
(`07`, and the stamp-replay rule above); **far-field representation** — the distant LOD/HLOD tile
must show the crater too, so delta overlays must feed the coarse mip/HLOD path or a mountainside
bite vanishes at 500 m (`06`; the `11` teleport control catches this); **baked lighting** — baked
AO, horizon-shadow maps, and any lightmap over the region are now wrong: re-bake locally, fall
back to dynamic terms, or constrain edit depth below noticeability (`10`); navmesh/AI rebuild
(gameplay's problem, but *triggered* by this pipeline's commit event — publish it); and audio/
physics material queries against the *composed* surface (`14` single-source rule). A destruction
feature is shippable when every row of this list has an owner and a budget, not when the crater
appears.

Craters, trenches, tire ruts at world scale, player terraforming — on a heightfield paradigm,
runtime edits are **delta overlays composited over immutable streamed tiles**. The baked tile is
never mutated (`13`/`14` overlay doctrine: streaming a tile back in must not resurrect the
pre-crater ground, and evicting one must not erase the crater). The edit pipeline, in order:

1. **Height delta.** Rasterize the edit brush (crater profile, trench cross-section) into a
   world-space delta target (R16F — it will be differentiated; 8-bit terraces, `13`). The terrain
   vertex path samples `bakedHeight + delta` in every pass — base, depth, shadow, velocity — from
   the same composed data, or the crater self-shadows wrong and ghosts under TAA.
2. **Re-normal with apron.** Recompute normals over the affected region **plus one texel of
   apron** — normals are derivatives, and a derivative at the edit border needs neighbors outside
   it, or the crater ships with a visible rectangle (the same apron rule every chunk mesher obeys,
   `04`/`05`, and the seam contract's attribute clause).
3. **Splat/scorch co-update.** A crater that only moves geometry looks like denting a texture.
   Stamp the material response (exposed substrate ring, scorch center) via the decal pipeline
   above in the same operation.
4. **Vegetation invalidation.** Kill/re-scatter instances whose seating changed (`15`) — grass
   floating over a fresh crater at eye height is a certified screenshot bug.
5. **Collision co-update.** Push the delta into the physics heightfield (PhysX
   `modifySamples()` + shape refit, Jolt heightfield `SetHeights`-family updates — D). This is
   asynchronous with the visual in most engines; the window between visual crater and collider
   crater is the **falling-through-crater bug** (or its inverse: invisible ground). Rule: gameplay
   consequences of the edit (spawn debris, allow entry) key off the *collision* commit, not the
   VFX; if the window exceeds a frame or two, gate it.

**Persistence and networking.** Never save or replicate the composed buffers. The edit stream —
`(op, brush, position, params, seq)` — is the persistent and replicated representation: bounded,
mergeable, deterministic to replay on any peer against the same baked tiles. Late joiners replay
the log (or a consolidated per-tile delta snapshot past a threshold); save games store the same.
Replicating buffers desyncs the moment two peers stream different tile LODs.

**Voxels get this free; heightfields hit a wall.** In `04`/`05` worlds, edits are native — write
voxels, remesh the chunk; no overlay machinery. The height-delta approach is the non-voxel
compromise and inherits the heightfield's topology contract: depth-limited, **no tunnels, no
overhangs, no undermining**. If the design brief says "dig under the crater," the paradigm answer
is a local voxel patch hybrid (`05`) or a voxel world outright — not a cleverer delta.

## The physics and collision handoff

**The collider is built from source data, on the SOLID layer.** Physics engines ship dedicated
heightfield collider shapes — Jolt `HeightFieldShape` (NxN samples, static bodies, compressed
blocks, active-edge welding to suppress ghost collisions; D), PhysX `PxHeightField` (16-bit
samples, per-triangle materials, unified triangle-extraction contact gen; D). Feed them:

- **Source-resolution heights** (or a declared decimation of them), never the render mesh of the
  moment. A collider cooked from a visual LOD inherits its error and its refinement schedule.
- **The solid layer of terrain-architect's layer stack**: solid ground height, *not*
  solid-plus-water. Water surfaces go to volume/query systems (`12`); a lake in the collider is
  the "solid ocean" defect — terrain-architect's classic generation bug, recommitted render-side
  by whoever assembled the cook. Walkable ice or riverbed collision is still the solid layer;
  only the *datum and depth fields* describe the water.
- **Per-triangle/per-sample material IDs** from the dominant splat layer (`07`), so physics
  contacts report surface type without a second query.

**Collision streams separately** (`06`'s contract, restated because it is violated weekly):
its own coarser pyramid or flat grid, its own **guaranteed-resident ring** sized by
`maxActorSpeed × worstLoadLatency + margin` around every physics-active actor — synchronous-load
or freeze-the-actor if the guarantee is threatened. Render tiles never get that guarantee; blurry
is acceptable, falling through is not. Divergence between collider and rendered surface is
bounded and *asserted* (`11`'s render-vs-collision delta check); traces that must match pixels
(bullet impact decals) raycast the render heightfield, not the physics world.

**Visual-only displacement needs a declared penetration tolerance.** Tessellated micro-detail,
parallax, `13` snow accumulation and deformation — the collider does not see them. Ship the rule
as a number: visual displacement may depart from the collider by at most `p` (a few cm for feet,
tighter for wheels/aiming). Under `p`: IK, wheel suspension, and decal projection absorb it. Over
`p` (deep snow, sand dunes shifting, mud ruts): the displacement **feeds the collider** — push the
depth field into the heightfield samples on the collision tile schedule, or gameplay walks on an
invisible floor above the snow while the camera says knee-deep.

**Voxel collision** (`05`): the extracted isosurface mesh doubles as the collision mesh only if
extraction guarantees **manifold, watertight** output per chunk with sealed LOD transitions —
non-manifold slivers from an unpatched marching-cubes case become physics tunnels. Collide at a
fixed extraction LOD (usually LOD0 in the gameplay ring) regardless of what renders.

**Character controllers vs detail.** Step height interacts with detail displacement: a controller
with a 30 cm step offset glides over curbs and ruts the renderer lovingly displaced. Decide per
feature whether it is *terrain* (in the collider, felt by physics) or *texture* (under `p`,
absorbed by IK) — curbs on conforming roads usually belong in the collider; gravel never does.

## Gameplay readback and surface queries

Footsteps, tires, impacts, buoyancy, AI surface costs all ask: **at point P, what is (material,
wetness, snow depth, water depth, deformation)?** The single-source-of-truth rule (`14`): gameplay
reads the *same maps the renderer samples* — never a parallel gameplay copy that drifts, never a
per-pixel re-derivation ("is it raining") that diverges from what is on screen (`13`'s
feet-splash-on-dry-ground bug). Two legal transports:

1. **CPU mirrors** of gameplay-relevant maps, at coarse resolution — a 512² R8 material-ID +
   wetness mirror of the camera ring costs hundreds of KB and answers queries in nanoseconds with
   zero latency. Coarse is fine: a footstep does not need 5 cm precision. Maps that are
   CPU-authored anyway (baked splat IDs, water depth from the cook) are mirrored for free.
2. **Async GPU readback** for GPU-authored state (`13` deformation, dynamic wetness): ring-buffer
   the copy targets, fence, poll — accept the N-frame latency (typically 2-3) and design for it.
   **Never synchronous readback**; one blocking map of a state target stalls the pipe and costs
   more than the entire state system (Unity's `AsyncGPUReadback` documents exactly this contract:
   non-blocking, a few frames latent — D).

```text
frame N  : dispatch state update → copy region-of-interest to readback ring[N % 3]
frame N+2: fence signaled → map ring[(N-2) % 3] → publish to gameplay mirror
queries  : always answered from the last PUBLISHED mirror — latent but never stalling
```

Latency discipline: consumers must tolerate the staleness window (footstep audio 50 ms late on a
*change* of wetness is imperceptible; a kill volume keyed to readback is a bug). Anything
latency-critical belongs in a CPU mirror or in the edit log (the crater's gameplay effects key
off the CPU-side edit op, which is zero-latency by construction — above).

**Buoyancy and water queries** route to `12`'s contract: gameplay reads the analytic surface —
water datum + depth fields + the CPU-evaluable displacement approximation (Gerstner sum or
low-order FFT fit) — never a readback of the visual mesh. **Audio/VFX response tables** key off
the same queried tuple: `(materialID, wetness, snowDepth, waterDepth) → footstep bank, tire
particle, impact VFX` — one table, one query path, so what you hear always matches what you see.

## Tri-fold ladder

| Tier | Roads | Decals | Runtime edits | Physics/queries |
|---|---|---|---|---|
| Indie | Draped ribbon + slope-scaled bias, splat stamps for trails | Pooled projected decals only | Skip, or single global delta target, no persistence | One heightfield collider from source data; CPU height+material mirror for all queries |
| Tool (`16`) | Live spline preview as overlay pass (bias legal — it's a viewport, not a shipped frame); show carve preview before commit | Stamp preview with footprint gizmo | Brush preview on delta overlay, commit writes source | Collider rebuild on save, not per stroke; `11` delta check in the tool |
| AAA | Terrain-conforming + VT injection; ribbon only where silhouette demands and terrain can't be edited | Promotion pipeline: projected → VT-injected with replay list | Delta overlays, apron re-normal, edit-log persistence/replication, full co-update chain | Streamed collision ring, per-triangle materials, async readback + mirrors, buoyancy from `12` datum |

## Pitfalls

- **Ribbon LOD crawl**: road sampled source heights or a different LOD than the ground draws;
  floats/sinks on LOD change, slides during morph. Conform to the terrain's evaluated vertex
  path, post-morph (`15` seating doctrine).
- **Bias tuned in the base pass, shadows broken**: slope-scaled bias pushed until the road wins
  depth — and contact shadows detach, or the shadow pass (own bias policy, `10`) acnes. Bias
  budgets are declared per pass, and beyond the declared distance the family changes.
- **Decal double-darkening with wetness**: scorch/wear composited after `13`'s wetness layer, or
  darkening applied in both decal and state stacks; rain turns marks black. One albedo darkening,
  slot order per `14`'s registry.
- **VT-injected decals evicted and lost**: injection treated as storage; page cache evicts,
  camera returns, battlefield is clean. Pages are cache — keep the stamp replay list; it is also
  the save format.
- **Collision a frame (or a stream) late after a crater**: actor stands on the old collider
  inside the visual hole, or falls when the commit lands mid-step; kill volumes under the map
  fire. Key gameplay consequences to the collision commit; gate entry during the window.
- **Physics heightfield built from a visual LOD**: feet float at LOD boundaries, projectiles hit
  invisible hills — the `06` divergence pitfall self-inflicted at cook. Build from source data;
  assert the divergence bound (`11`).
- **Water in the collider ("solid ocean")**: cook consumed composed height instead of the solid
  layer; boats park on the surface, divers bounce off. Collide solid, query water via `12`.
- **Synchronous readback for surface queries**: one `Map()` on the deformation target and the
  frame is gone. Async ring + published mirror, always; latency-critical answers come from CPU
  mirrors or the edit log.
- **Edit persistence via buffer snapshots**: saves balloon, network desyncs across LOD, replays
  impossible. Persist and replicate the edit-op log; buffers are derived state.
- **Re-normal without the apron**: every crater framed by a lighting rectangle. Derivatives need
  neighbors; recompute region = edit region + 1 texel, same as every mesher (`04`/`05`).
- **Heightfield delta asked to make a tunnel**: overlays can only lower or raise one surface;
  undermining punches through to nothing. Topology change is a paradigm decision (`05` hybrid),
  not an edit-brush feature.

## Sources & provenance

| Claim | Tier | URL |
|---|---|---|
| Jolt `HeightFieldShape`: NxN static heightfield, block compression, active-edge threshold vs ghost collisions, height-update API | **D** | https://jrouwe.github.io/JoltPhysics/class_height_field_shape_settings.html |
| PhysX `PxHeightField`: 16-bit samples, per-triangle materials + tessellation flag, unified (triangle-extraction) contact gen, `modifySamples()` runtime edits | **D** | https://nvidia-omniverse.github.io/PhysX/physx/5.3.1/_api_build/class_px_height_field.html · https://archive.docs.nvidia.com/gameworks/content/gameworkslibrary/physx/guide/Manual/Geometry.html |
| D3D depth-bias semantics: `DepthBias·r + SlopeScaledDepthBias·MaxDepthSlope`, `DepthBiasClamp`, UNORM vs float-depth formulas, shadow-acne usage and its overshoot artifact | **D** | https://learn.microsoft.com/en-us/windows/win32/direct3d11/d3d10-graphics-programming-guide-output-merger-stage-depth-bias |
| UE Runtime Virtual Texturing: caches shading over large areas; fit for landscape with decal-like materials and splines; components composite into the page cache | **N/D** | https://dev.epicgames.com/documentation/en-us/unreal-engine/runtime-virtual-texturing-in-unreal-engine |
| UE Landscape Splines: spline features that conform to and can deform ("push and pull") the landscape; deform-to-spline + edit-layer workflow | **N/D** | https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-splines-in-unreal-engine |
| Far Cry 5 terrain: GPU pipeline for LOD/cull/stitch; roads and splines baked through the terrain/material pipeline of a 10×10 km world | **T** | https://gdcvault.com/play/1025480/Terrain-Rendering-in-Far-Cry (slides: https://media.gdcvault.com/gdc2018/presentations/TerrainRenderingFarCry5.pdf — listed, not read page-by-page) |
| Road generation (placement, grading, vegetation clearing) as a cook-time procedural pipeline | **T** | https://www.gdcvault.com/play/1025557/Procedural-World-Generation-of-Far (routed to terrain-architect `20`) |
| Async GPU readback: non-blocking GPU→CPU copies at a few frames' latency; the anti-stall contract | **D** | https://docs.unity3d.com/ScriptReference/Rendering.AsyncGPUReadback.html |
| Promotion pipeline (projected → VT-injected persistent decals); stamp replay lists surviving page eviction | **F** | — (standard practice in RVT-era titles; no single canonical citation) |
| Delta-overlay edits over immutable tiles; edit-op log as save/replication format; apron re-normal | **F** | — (overlay doctrine formalized in `13`/`14`; log-replay is ubiquitous multiplayer practice) |
| Collision ring sizing, divergence bounds, penetration tolerance `p`, coarse CPU mirrors | **F** | — (this skill's `06`/`11` contracts; numbers are per-title, assert per `11`) |
| Solid-layer-only colliders / "solid ocean" defect | **D** | — (terrain-architect layer-stack contract, restated render-side) |
