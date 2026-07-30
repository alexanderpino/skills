# Water Rendering

Water on terrain — oceans, rivers, lakes — arrives from the generation side as *still data*: flat
surface datums, a depth field, a flow field. Everything that moves is made here. This chapter owns
the engine side of that handoff: water surface geometry and its LOD (meshed or the meshless
screen-space pass), ambient wave synthesis
(Gerstner and FFT), flow-driven river surfaces, local interactive simulation, water shading
composition, shoreline integration, and the transparency/pass-ordering discipline water forces on
the frame. Deep BRDF/scattering math routes to the physically-based-rendering skill; generation of
water bodies, routing, and flow fields routes to terrain-architect (its `03`/`04` hydrology and the
`08`/`27` output contract).

Contents: [The handoff, seen from the render side](#the-handoff-seen-from-the-render-side) ·
[Surface geometry & LOD](#surface-geometry--lod) ·
[Screen-space water: the fullscreen-triangle pass](#screen-space-water-the-fullscreen-triangle-pass) ·
[Ambient waves: Gerstner and FFT](#ambient-waves-gerstner-and-fft) ·
[Rivers: flow-driven surfaces](#rivers-flow-driven-surfaces) ·
[Interactive simulation patches](#interactive-simulation-patches) ·
[Shading and optics](#shading-and-optics) · [Shoreline integration](#shoreline-integration) ·
[Transparency & pass ordering](#transparency--pass-ordering) · [Pitfalls](#pitfalls) ·
[Sources & provenance](#sources--provenance)

## The handoff, seen from the render side

Terrain-architect's hydrology handoff (its `08`, "caused, not carved") gives this chapter four
inputs, and the doctrine is that they are *sufficient*:

| Input | Form | What the renderer does with it |
|---|---|---|
| `waterSurface` | Flat elevation per body (sea level for oceans, spill level per lake, a downstream-monotone profile per river) | The datum every wave displaces from; the gameplay swim/buoyancy surface |
| Water depth | Scalar field: `waterSurface - solidTop`, 0 on dry land | Absorption ramp, shoaling, shoreline fade, sim boundary |
| Flow / velocity | 2D vector field (m/s), from routing + discharge | Flow-map advection, foam alignment, particle steering, sim boundary inflow |
| Shore distance | Signed/unsigned distance to the waterline | Shoreline foam bands, wet-sand band (`13`/`14`), LOD bias near the line |

The solid terrain below the water is real terrain — bathymetry generated to dry-land standards —
and it is the collision floor, the refraction target, and the depth source. Two hard rules fall
out of the contract, and both are load-bearing:

- **Never displace the terrain heightfield to fake water.** Water carved into `solidTop` is the
  "solid ocean" defect from the generation side, reproduced renderer-side: no swim volume, no
  tide, no transparency, and the material system now has to pretend rock is liquid. Water is a
  *separate surface* drawn over real bathymetry, always.
- **Never bake waves into any input.** If waves, ripples, or foam appear pre-painted in the
  height, normal, or color data, the pipeline is broken upstream — a baked wave cannot respond to
  wind, time, interaction, or camera, and it aliases under every condition the real synthesis
  handles. If an input arrives with waves in it, the fix is upstream (terrain-architect `08`),
  not a renderer workaround.

When the renderer needs something the contract lacks (per-body bounding volumes, max wave
amplitude for conservative culling bounds, river width fields), extend the contract; do not
derive hydrology renderer-side.

## Surface geometry & LOD

The water surface is a displaced plane (per body), and the geometry question is the same question
as `01`: how to spend vertices where projected error is visible. Two families:

| Scheme | Mechanism | Wins | Loses |
|---|---|---|---|
| Projected grid (Johanson) | Screen-space regular grid projected onto the water plane; vertex density automatically ∝ screen area | Near-perfect vertex distribution; one mesh for an infinite ocean; no LOD machinery | Vertices swim/flicker at the horizon edge as the camera turns; detail density is view-coupled and hard to art-direct; degenerate at near-vertical look-down; per-body clipping is awkward |
| World-space grid (clipmap / quadtree rings on the plane) | Reuse `01`'s LOD machinery flattened onto the water datum; concentric rings or SSE-refined quads | Stable world-anchored vertices (no reprojection swim); same crack/morph contracts as terrain; trivially clips to body extents; plays with `06` streaming | Needs the full LOD controller; wasted vertices at grazing angles that a projected grid gets free |

Production default in 2026 is the **world-space grid**: the reprojection instability of projected
grids under TAA and their poor authorability outweigh their elegance, and the LOD machinery is
already paid for by the terrain. Projected grids remain defensible for a single infinite ocean
with no other water bodies and a camera that never looks straight down. Whichever is chosen:

- **Near field**: tessellate or pre-subdivide to carry actual wave *displacement* (not just
  normals) out to the distance where displacement drops below ~1 px of parallax; beyond that,
  waves live in the normal/material band only (the three-bands doctrine, applied to water).
- **Far field**: an infinite-ocean skirt ring — a coarse annulus extended to the horizon at the
  sea datum, normal-mapped only. It must share the datum and the far fog/aerial-perspective path
  with terrain (`10`) or the sea/sky junction band mismatches the land horizon.
- **Lakes and rivers** are finite meshes streamed with their tiles under the same residency
  contract as `06` — a lake tile's water mesh loads/evicts with the terrain tile, carries `e(tile)`
  and SSE-refines in the same currency, and matches terrain tile LOD at the shoreline (see
  [Shoreline integration](#shoreline-integration)).
- **Planet-scale oceans** live on the cube-sphere as sphere-datum patches (`09`): patch-local
  frames, camera-relative wave displacement, and the wave textures sampled in a local tangent
  frame — world-space UV math at planetary coordinates shreds into precision noise long before
  the terrain does, because wave frequencies are centimetre-scale.

Culling note: wave displacement moves geometry outside its static bounds. Bounds submitted to
`08`'s culling must be inflated by max amplitude + max horizontal chop, per cascade settings —
un-inflated bounds cause tiles that pop at screen edges exactly when the sea is roughest.

## Screen-space water: the fullscreen-triangle pass

There is a third geometry answer for flat-datum water: draw no water geometry at all. A single
fullscreen triangle covers the screen; the pixel shader builds a per-pixel view ray, intersects
it analytically with the water plane, and shades water wherever the hit survives the depth
buffer. The entire surface-geometry problem — LOD, cracks, morphing, culling, horizon skirts —
evaporates because there is nothing to tessellate, and the horizon is pixel-exact by construction.

One *triangle*, not a quad — community canon with a real reason: a quad is two triangles whose
shared diagonal cuts 2×2 pixel quads in half, so the rasterizer runs partially-covered quads and
redundant helper lanes twice along the seam, and sets up interpolants for two primitives instead
of one. The triangle needs no vertex or index buffer; the vertex shader emits three oversized
verts straight from `SV_VertexID`:

```hlsl
// Draw(3), nothing bound; the oversized tri clips to exactly the screen
float4 FullscreenVS(uint id : SV_VertexID, out float2 uv : TEXCOORD0) : SV_Position {
    uv = float2((id << 1) & 2, id & 2);               // (0,0) (2,0) (0,2)
    return float4(uv.x * 2 - 1, 1 - uv.y * 2, 0, 1);  // spans NDC (-1,1)..(3,-3)
}
```

The pixel shader is the whole system:

1. **Ray**: unproject the pixel through the inverse view-projection (near/far points), or build
   `rayDir` from the camera basis and pixel NDC. Origin is the camera; keep everything
   camera-relative (`09`).
2. **Analytic hit**: for a horizontal datum at `h_water`,
   `t = (h_water - camPos.y) / rayDir.y`. Guard the degenerate cases explicitly: `|rayDir.y| < ε`
   (ray parallel to the plane — no hit), `t < 0` (plane behind the camera), and the sign flip
   when the camera is below the datum (underwater, below).
3. **Depth reject**: reconstruct the opaque scene's world position from the depth buffer along
   the same ray; if the scene hit is nearer than `t`, terrain or props occlude the water — output
   nothing. The reconstruction must use the frame's actual depth convention (reversed-Z, jitter).
4. **Shade**: everything in [Shading and optics](#shading-and-optics) applies unchanged at the
   hit point — traversal distance from scene depth vs `t` for absorption, shore fade from the
   depth field, normal detail from scrolling/FFT normal cascades sampled at the hit's world XZ,
   SSR/cubemap reflection, refraction from the scene-color copy.

The geometry of the pass, in section view:

```
 C  camera — one fullscreen triangle, one view ray per pixel
  \\
   \ \_____ ray B                             ____
    \      \_____                           _/    \_
     \ ray A     \_____                   _/        \_    terrain surface
      \                \_____           _/            \   from the depth
       \                     \_____   _/               \  buffer
        \                          \_X                  \
 ~~~~~~~~*~~~~~~~~~~~~~~~~~~~~~~~~~~/~~~~~~~~~~~~~~~~~~~~\~~~ water datum y = h_water
   ______________                  /
  /   sea floor  \_________________/
  * = ray A's plane hit, t = (h_water - camPos.y)/rayDir.y; the scene hit (sea
      floor) lies beyond t -> ACCEPT: shade water there, absorb over sceneHit - t
  X = ray B's scene hit is nearer than its t -> REJECT: terrain occludes the water
```

**Displaced surfaces: per-pixel raymarching.** The analytic plane carries waves in normals only —
flat silhouette, no parallax between crests. To show real displacement, march the ray against the
displaced height: start at the analytic hit of a crest-inflated plane, take fixed steps sampling
the summed cascades until the ray crosses the surface, then binary-refine 4–6 iterations. Cost
doctrine: that is N cascade fetch+sums per water pixel, and N grows brutally at grazing angles
where the ray travels far between height crossings — cap the step count and fall back to the
analytic plane beyond a distance. Raymarching is worth it for hero close-ups with no mesh budget;
the moment displacement must read everywhere on screen, a mesh is cheaper.

**Underwater is the same triangle.** `camPos.y < h_water` flips the intersection's sign logic and
the pass becomes a fullscreen underwater volume: every pixel starts in water, extinction fog runs
over the distance to the scene hit or the surface exit point, the datum seen from below gets
total internal reflection outside Snell's window, and the bright overhead circle comes from the
same ray-plane math. Same triangle, different branch — the underwater state machine in
[Shading and optics](#shading-and-optics) still owns the crossing frame.

Honest trade-off against meshed water:

| | Fullscreen-triangle pass | Mesh / projected grid |
|---|---|---|
| Horizon & LOD | pixel-exact plane; zero LOD/crack/skirt machinery | vertex-quantized; full crack/morph discipline |
| Displacement | raymarch-only; silhouettes cost per-pixel marching | free in the vertex shader; cheap silhouettes |
| Motion vectors | none rasterized — derive analytic velocity or TAA ghosts | rasterized like any other geometry |
| Multiple bodies | per-body planes + screen bounds; cost per body drawn | meshes clip to body extents naturally |
| Transparency | composites at one depth per pixel; other transparents need explicit ordering | sorts as ordinary transparent geometry |

Where it wins: indie flat oceans, single-datum seas, and tool viewports (`16`) that need "sea
level" visualized without buying the LOD apparatus. Where it strains: lakes and rivers at many
elevations (each body needs its own plane and screen-space bounds, and the depth-reject must pick
the nearest surface per pixel — the per-body sorting rule of
[Transparency & pass ordering](#transparency--pass-ordering) applies unchanged), and any frame
where wave silhouettes matter more than the saved machinery. The pass raises three traps of its
own — grazing-angle ray-plane precision, reversed-Z reconstruction mismatch, and the missing
motion vectors — catalogued in [Pitfalls](#pitfalls).

## Ambient waves: Gerstner and FFT

Ambient (wind-driven) waves are pure synthesis on top of the flat datum. Two families, honestly
compared:

| | Gerstner / trochoidal sum | Spectral FFT (Tessendorf) |
|---|---|---|
| Mechanism | Sum of 4–16 analytic trochoids; horizontal + vertical displacement per wave | Sample an oceanographic spectrum (Phillips, JONSWAP) into a frequency grid; inverse FFT per frame → displacement map |
| Look | Sharp, tunable crests; readable at low counts; visibly periodic and "gel-like" as counts drop | Full spectrum, statistically ocean-like; the AAA standard for open sea |
| Cost | Vertex-shader ALU, scales with wave count | 2–4 compute FFTs (e.g. 256²–512²) per frame; amortizable, cacheable |
| Authoring | Direct per-wave control — good for stylized/hero waves | Spectrum parameters (wind speed/direction, fetch); less direct |
| Outputs | Displacement + analytic normal | Displacement, normal, **and Jacobian** maps |

**Gerstner** is the right tool for stylized seas, small budgets, and gameplay-authored swells; its
loop artifact (the whole surface visibly repeating its motion) is inherent — mitigate with
irrational frequency ratios and per-wave phase, never expect it to vanish. **FFT** is the open-sea
default. Run **2–4 cascades** at different world-space patch sizes (e.g. ~400 m, ~60 m, ~10 m) and
sum them: a single tile visibly repeats from any altitude; overlapping cascades at co-prime-ish
sizes push the repeat beyond notice — but verify from max gameplay altitude (`11`), because
cascade tiling *returns* at height as the small cascades mip away and the large one dominates.

**The Jacobian is a free product; use it.** The horizontal displacement field's Jacobian
determinant measures local surface compression: `J = (1+∂Dx/∂x)(1+∂Dy/∂y) − (∂Dx/∂y)(∂Dy/∂x)`.
`J ≤ 0` means the surface self-intersects — a folding crest. Threshold slightly above zero
(practice: 0.5–0.9, tuned) → whitecap/foam mask, accumulated with decay so foam persists briefly
behind the crest. This is *the* whitecap signal; painting whitecaps any other way fights the
displacement. **Choppiness** (the horizontal displacement scale) sharpens crests toward trochoids
— and past ~1.0 it drives `J` negative over large areas, which reads as geometry
self-intersection shimmer. Clamp choppiness so folding stays rare-and-foamed, not constant.

**Shallow water is a modification, not a simulation.** Near shore, deep-water synthesis is
wrong: real waves shorten, slow, steepen, and refract toward the shoreline as depth drops. The
production treatment reads the depth field and applies approximations — depth-attenuated
amplitude (fade displacement to ~0 as depth → 0, or waves poke through the beach),
depth-shortened wavelength (dispersion: celerity ~ `sqrt(g·depth)` when shallow), and a
shoaling-style amplitude bump just before the fade. Be honest in review: these are *plausibility
approximations* driven by the exported depth field, not shallow-water simulation — they will not
produce true refraction patterns or breaking dynamics, and claiming otherwise misroutes bug
reports. Breaking-wave hero moments are authored (flipbooks, meshes, particles), keyed off depth
and shore distance.

## Rivers: flow-driven surfaces

Rivers cannot use ambient synthesis — their motion is *directed*, and the direction is exactly
what the generator's flow field encodes. The core technique is **flow mapping** (Vlachos, Portal
2): advect the surface detail UVs along the flow vector, and hide the inevitable UV stretch by
crossfading two phase-offset samples:

```hlsl
float2 flow   = DecodeFlow(FlowField.Sample(s, uv));      // m/s, world-aligned, from the generator
float  phase0 = frac(t / period);
float  phase1 = frac(t / period + 0.5);
float3 n0 = SampleDetailNormal(uv - flow * phase0 * advectScale);
float3 n1 = SampleDetailNormal(uv - flow * phase1 * advectScale);
float  w0 = 1 - abs(2 * phase0 - 1);      // 0 exactly when sample 0's UVs snap back
float3 n  = normalize(lerp(n1, n0, w0));  // each layer hidden at its own reset
```

Each sample's UVs periodically snap back to their origin; the triangle-wave blend guarantees a
sample has zero weight at its snap. The visible failure mode is **pulsing** — the surface appears
to breathe at `period` — worst where flow is fast and `advectScale·|flow|·period` approaches the
detail texture's feature size; shorten the period or scale advection down in fast reaches. Add a
per-pixel phase offset (noise) to break the global synchrony of the pulse.

Build the rest of the river surface from the same field: **flow-aligned foam** (advect a foam
texture the same way, masked by the generator's constriction/gradient masks — rapids foam where
the *cause* data says rapids exist), **speed-driven detail** (blend calm→rippled→turbulent normal
sets by `|flow|`), and small downstream normal-map scrolling as the cheapest baseline motion.

**River geometry** is either spline-swept ribbon meshes (the production default: explicit width,
banks, and UVs parameterized along-flow — best when the generator exports river centerlines) or
water quads carried in the terrain tiles (simpler, follows `06` streaming for free, but along-flow
UVs must be derived from the flow field). Ribbons LOD by spline subdivision against the same SSE
currency; their far LOD must not drop below the terrain tile's ability to hold the riverbed
silhouette, or distant rivers detach from their valleys.

**Waterfalls** are constructs, not surfaces: at a knickpoint (the generator marks these — its
`04`), the flow field ends on one level and resumes below. The renderer assembles a fall from a
mesh sheet (scrolling normals + foam, UV-parameterized top-to-bottom), particle spray at base and
lip, and a foam/mist pool disc — all *steered* by the exported discharge and drop height. None of
this is in the export; all of it is driven by it. The recurring defect is a waterfall authored
where the flow field doesn't support it — the river above visibly refuses to feed it. Fix the
generation graph, not the particles.

## Interactive simulation patches

Ambient synthesis and flow maps do not react to the player. Reaction comes from a **local
simulation patch**: a GPU heightfield fluid sim (pipe/virtual-pipe model or linearized
shallow-water — Kass–Miller lineage) over a small moving domain centered on the camera.

- **Domain**: a ring-buffer (toroidally addressed) grid, typically 256²–512² covering 30–100 m,
  that follows the camera in whole-texel steps (same discipline as clipmap ring updates, `01`).
  Content scrolls by offset, not copy; newly exposed texels initialize to rest + inflow from the
  flow field.
- **Injection**: characters, projectiles, and boats add impulses/displacement at their footprint
  each step. Keep injection in the sim's units (velocity or height delta), not "spawn a ripple
  sprite" — sprites don't interfere, reflect off banks, or advect with flow.
- **Coupling is one-way, by doctrine.** The sim *reads* terrain depth (banks and bed shape the
  ripples, waves reflect off shores) and *writes* surface detail (a displacement/normal overlay
  composited on top of ambient waves within a blend radius). It never modifies terrain, never
  moves the water datum, and never feeds gameplay height. Requests for the sim to erode banks or
  re-route rivers are generation-side fantasies — route them to terrain-architect.
- **Budget doctrine**: quarter-ish resolution relative to screen density, fixed timestep
  (decoupled from frame rate, accumulate-and-step) or the sim's stability constant changes with
  frame rate, explicit damping so energy dies in seconds, and clamp per-step injection so a
  physics glitch cannot detonate the surface. The whole patch should cost a fraction of a
  millisecond; it is a detail layer, not a fluid solver.
- **Edge contract**: fade the sim's contribution to zero over the outer ~15% of the domain. A
  hard edge where wakes stop existing is one of the most-reported water artifacts; the fade is
  the contract, not a cover-up, because the domain boundary is a budget decision the player must
  not see.

## Shading and optics

BRDF math routes to physically-based-rendering; what this skill owns is the *composition* — which
signals feed the water shader and where each comes from. The water pixel is:

```
color = lerp(refracted_underwater, reflected_environment, Fresnel(NdotV))
      + foam + sun_glint
```

- **Reflection** is a fallback hierarchy, never a single source: SSR first (correct for local
  objects), planar reflection for the hero body when budget allows (see
  [Transparency & pass ordering](#transparency--pass-ordering)), distant cubemap/sky capture
  last. Blend by SSR confidence — SSR *will* drop out at grazing angles and screen edges (the
  reflected ray leaves the screen exactly where water is most reflective), and the fallback must
  match the SSR result in brightness or the dropout draws a line. Grazing-angle Fresnel makes
  water the most brutal SSR-consistency test in the frame.
- **Refraction**: sample the scene-color copy with a normal-driven UV distortion, clamped by
  view depth so near-surface distortion doesn't grab pixels metres away. The canonical artifact:
  a distorted sample lands on an object *above* the water (a dock post, a character's torso),
  smearing it into the water. The fix is a depth reject — if the refracted sample's scene depth
  is closer than the water surface, fall back to the undistorted UV:

```hlsl
float2 uvR = uv + n.xz * distortStrength / viewDepth;
if (LinearEyeDepth(SceneDepth.Sample(s, uvR)) < waterViewDepth) uvR = uv;  // sample was above water
float3 refracted = SceneColor.Sample(s, uvR).rgb;
```

- **Absorption and scattering with depth**: extinguish the refracted color per channel with the
  water-traversal distance — `exp(-sigma * dist)` with `sigma.r > sigma.g > sigma.b` for natural
  water — and blend toward a scattering color as extinction saturates. The traversal distance
  comes from scene depth vs surface depth along the view ray *and* from the exported depth field
  for the vertical component; the shallow→deep color ramp is the single strongest realism cue
  water has, and it is entirely a function of the generator's bathymetry. Flat-colored water is
  almost always a missing/ignored depth field.
- **Foam** is three masks with one compositor: shoreline foam (depth + shore distance, advected
  along shore tangent), whitecaps (Jacobian, above), flow foam (rivers, above). Composite as an
  opaque-ish albedo layer that *kills* the Fresnel reflection under it — foam is scattering
  froth, not glossy water, and reflective foam is an instant fake tell.
- **Caustics**: an approximation, stated as such — an animated caustic texture (or a projection
  of the wave normal map's focusing) on underwater terrain, masked by depth (fade out deep),
  attenuated by the same extinction, and synced to the sun direction. Physically simulated
  caustics are out of budget scope; route the theory to physically-based-rendering.
- **Underwater camera state** is a real state machine, not a fog tweak: on submersion switch to
  underwater fog (aggressive, chromatic, from the same `sigma`), render the surface from below
  (total internal reflection outside Snell's window — the bright circle overhead is a cheap,
  high-value cue), and handle the half-submerged frame explicitly. The waterline crossing is
  either a hard cut (acceptable, hide with a droplet/meniscus overlay for a frame or two) or a
  true split-screen meniscus (render both states, mask by the wave-displaced waterline in screen
  space — expensive, hero-camera only). The untreated version — one frame of neither-state
  garbage at the crossing — is a certified review catch.

## Shoreline integration

The waterline is where water rendering is actually judged, because it is where the water surface
meets `01`/`06` terrain at a shallow grazing angle — the worst case for every artifact class.

- **Depth fade** ("soft intersection"): fade water opacity, distortion, and specular over the
  first few centimetres-to-metres of water depth, using scene-depth-vs-surface-depth (the "depth
  fade" node family in engine material editors). This removes the hard polygonal intersection
  line. It is a *cosmetic* fade — the swim volume still starts at the datum; do not let gameplay
  read the faded visual edge.
- **Wet-sand band**: drive a wetness band above the waterline from wave run-up (max recent
  shoreline wave amplitude) plus the exported wetness map — darkened albedo, boosted specular,
  handled by the surface-state system (`13`) consuming aux maps per `14`. The band must *move*
  with the waves' run-up envelope, lagging and drying, or the beach reads as painted.
- **Shoreline foam**: an advected foam texture in a band defined by shore distance, phase-driven
  so it pulses with the incoming wave cadence (tie its phase to the dominant shallow-water wave
  phase, or foam and waves visibly disagree).
- **LOD co-discipline**: the water mesh's LOD at the shoreline must be matched (or biased finer)
  relative to the terrain tile's LOD, and both must refine together, or the intersection line
  *crawls* on LOD transitions — a `11` catalogue symptom whose fix is contract (shared SSE
  currency, shoreline LOD bias), not blending. Terrain skirts at the shoreline must stay below
  the water surface minus max wave trough, or skirt walls surface at low tide.

## Transparency & pass ordering

Water is the classic hard transparency case, and the frame must be structured for it:

1. Render all opaque (terrain included) → copy scene color and depth. Water draws *after*
   opaque, reading the copies for refraction/absorption; it cannot refract what hasn't been
   drawn, and it cannot read the depth buffer it is about to write.
2. **Depth-write policy**: water writes depth (so later transparents and post-fog sort against
   it) *after* its own pass, or renders to depth in a prepass for particles to soft-clip
   against. Pick one, document it; ad-hoc per-effect choices produce spray that draws behind
   the surface it belongs on.
3. **Per-body sorting**: bodies at different datums (a lake above a river) sort back-to-front
   per body; the depth-reject refraction logic must use the *nearest* water surface per pixel or
   stacked bodies smear each other.
4. **TAA/upscalers**: refraction UVs computed from a jittered depth/scene buffer shimmer under
   TAA — sample with the current-frame jitter removed, and give water correct motion vectors
   for its *displaced* surface or the upscaler smears wave crests into ghosts. DLSS/FSR-era
   discipline: water normal detail that only exists at native resolution will boil; pre-filter
   the cascade mips (specular AA doctrine — route the math to physically-based-rendering).
5. **Planar reflection cost discipline**: a planar pass re-renders the scene — treat it as a
   scaled-down scene render (half-res, reduced LOD bias, terrain-only + hero set, no recursive
   water) with its own budget line. One planar body per frame is the classic ceiling; every
   additional body falls back to SSR + cubemap.
6. **Forward vs deferred**: water is effectively a forward pass even in a deferred renderer —
   it needs multiple light/environment sources, scene-color access, and a BRDF that doesn't fit
   the G-buffer. Budget it as forward: it pays full lighting cost per pixel, which is why water
   area on screen is a load-bearing profiling axis (`11`).

## Pitfalls

- **Baked-wave temptation**: waves painted into exported normals/height "to save runtime cost".
  They cannot respond to wind, shore, or time, alias at distance, and block every system in this
  chapter. Contract violation; fix upstream.
- **Terrain displaced to fake water**: the render-side solid-ocean defect. No swim volume, no
  transparency, no tide. Water is a separate surface, always.
- **Sim patch edge pop**: wakes vanish at an invisible wall. The domain-edge fade contract was
  skipped, or the ring buffer scrolls in fractional texels (must be whole-texel, as clipmaps).
- **FFT cascade tiling from altitude**: fine cascades mip away, the big tile repeats to the
  horizon. Verify from max flight height (`11`); add a cascade or break up with a large-scale
  spectrum/foam variation layer.
- **Choppiness self-intersection shimmer**: chop cranked past the folding limit; `J` negative
  everywhere; crests z-fight themselves. Clamp chop; spend `J` on foam instead.
- **Refraction leaking objects above water**: missing depth reject on the distorted sample. The
  single most common shipped water bug; the fix is four shader lines (above).
- **SSR dropout at grazing/screen edge**: mirror-bright water goes flat exactly at the horizon
  and screen borders. Mandatory fallback chain with brightness-matched cubemap; never ship SSR-only.
- **Waterline crawl on LOD change**: water and terrain refine on different schedules; the
  intersection line steps visibly. Shared SSE currency + shoreline LOD bias (`11` symptom table).
- **Z-fighting of distant flat water vs flat terrain**: at km distance, a lake 20 cm above its
  bed fights the bed in depth. Reversed-Z + camera-relative transforms (`09`); if it persists,
  depth-bias the water or mask terrain under opaque-deep water via the watermask (`06` payload).
- **Swim volume vs visual surface mismatch**: gameplay reads the flat datum while the eye reads
  datum + waves; characters float above troughs and clip through crests. Gameplay queries datum
  plus a cheap CPU-evaluable displacement approximation (the Gerstner sum, or a low-order fit of
  the FFT cascades) — never a GPU readback of the visual mesh, and never raw datum alone in
  heavy seas.
- **Jittered-refraction shimmer under TAA**: refraction UVs built from jittered buffers; the
  water fizzes. De-jitter the sample and provide displaced-surface motion vectors.
- **Waterfall without a feeding flow field**: the construct exists, the river above ignores it.
  Generation-graph defect — route to terrain-architect, do not patch with particles.
- **Screen-space water: grazing-ray precision**: near the horizon `rayDir.y → 0` and `t`
  explodes; float error shreds the last pixel rows into stripes. Camera-relative math (`09`),
  clamp `t` against the far plane, and fade into the sky/fog band before the guards ever trip.
- **Screen-space water: depth-reconstruction mismatch**: the ray hit is compared against a world
  position rebuilt with the wrong depth convention (reversed-Z, ∞ far, jitter) — water pokes
  through hills or vanishes hugging geometry. One shared reconstruction helper for every
  screen-space pass; never a per-shader reimplementation.
- **Screen-space water: no motion vectors**: nothing was rasterized, so TAA/upscalers see zero
  velocity where waves move — crests ghost and smear. Write analytic velocity: reproject the hit
  point through the previous frame's view-projection (plus wave advection) into the velocity
  buffer.

## Sources & provenance

- **P** — Gerstner trochoidal waves: classical fluid mechanics (19th-century); the closed-form
  crest-sharpening wave sum used across the industry.
- **P** — Tessendorf, "Simulating Ocean Water" (SIGGRAPH course notes, early 2000s): the FFT
  ocean — spectrum sampling, inverse-FFT displacement, choppiness, Jacobian folding. The canon
  for every spectral ocean shipped since. 2004 revision:
  [coursenotes2004.pdf (Clemson)](https://people.computing.clemson.edu/~jtessen/reports/papers_files/coursenotes2004.pdf).
- **P** — Phillips and JONSWAP spectra: oceanography literature, imported into graphics via
  Tessendorf's notes; parameter details in graphics use are simplified from the originals.
- **T** — Vlachos, "Water Flow in Portal 2" (SIGGRAPH 2010, Advances in Real-Time Rendering
  course): flow mapping — dual phase-offset samples with triangle-wave blend; the canonical
  river-surface technique.
  [Slides PDF (Valve)](https://cdn.akamai.steamstatic.com/apps/valve/2010/siggraph2010_vlachos_waterflow.pdf).
- **P** — Bruneton, Neyret & Holzschuch, "Real-time Realistic Ocean Lighting using Seamless
  Transitions from Geometry to BRDF" (Computer Graphics Forum 29(2), 2010): the principled
  treatment of wave detail crossing from geometry band to shading band.
  [HAL open access](https://inria.hal.science/inria-00443630).
- **P** — Johanson, "Real-time water rendering — introducing the projected grid concept" (MSc
  thesis, Lund University, 2004): the screen-space grid concept and its horizon-edge behavior,
  as compared in the geometry table.
  [Thesis PDF (Lund)](https://fileadmin.cs.lth.se/graphics/theses/projects/projgrid/projgrid-lq.pdf).
- **P** — Kass & Miller, "Rapid, Stable Fluid Dynamics for Computer Graphics" (SIGGRAPH 1990):
  the lineage behind interactive heightfield ripple sims; pipe-model variants are later
  community practice. [ACM DL](https://dl.acm.org/doi/10.1145/97880.97884).
- **P** — Finch, "Effective Water Simulation from Physical Models" (GPU Gems ch. 1, 2004): the
  standard practical Gerstner implementation reference.
  [Chapter online (NVIDIA)](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models).
- **F** — Cascade counts and sizes (2–4 cascades, ~400/60/10 m), Jacobian foam thresholds
  (0.5–0.9), sim patch sizes (256²–512² over 30–100 m), choppiness limits: standard-practice
  ranges from shipped-title talks and community writeups; tune per title, verify per `11`.
- **T** — Bilodeau, "Vertex Shader Tricks" (GDC 2014, AMD): the `SV_VertexID` fullscreen
  triangle among other bufferless draws.
  [Slides (SlideShare)](https://www.slideshare.net/DevCentralAMD/vertex-shader-tricks-bill-bilodeau).
- **F** — One fullscreen triangle over a two-triangle quad (diagonal partial-quad/helper-lane
  waste, double interpolant setup): community canon —
  [Wallis, "Optimizing Triangles for a Full-screen Pass"](https://wallisc.github.io/rendering/2021/04/18/Fullscreen-Pass.html);
  [d7samurai, minimal D3D11 fullscreen triangle](https://gist.github.com/d7samurai/5915956fb8ce6a63503cf8c85ffd1e84);
  [30fps.net, "Full screen triangle optimization"](https://30fps.net/pages/twotris/).
- **F** — Water as a fullscreen ray-plane/ray-heightfield pass: long-running community
  technique, no canonical paper —
  [GameDev.net, "Rendering Water as a Post-process Effect"](https://www.gamedev.net/articles/programming/graphics/rendering-water-as-a-post-process-effect-r2642/).
- **D** — Underwater as a fullscreen volume pass in shipped tooling:
  [Crest Ocean System underwater docs](https://crest.readthedocs.io/en/latest/user/underwater.html)
  (fullscreen effect between transparents and post, meniscus handling).
- **F** — Depth-reject refraction fix, SSR fallback hierarchy, underwater state machine, planar
  one-body ceiling: ubiquitous production practice; no single canonical citation.
- **?** — Attribution of specific shallow-water shoaling approximations to particular shipped
  titles: multiple GDC/SIGGRAPH-Advances talks cover it; treat any specific title claim as
  unverified.
