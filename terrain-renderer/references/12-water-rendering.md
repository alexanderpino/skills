# Water Rendering

Water on terrain — oceans, rivers, lakes — arrives from the generation side as *still data*: flat
surface datums, a depth field, a flow field. Everything that moves is made here. This chapter owns
the engine side of that handoff: water surface geometry and its LOD (meshed or the meshless
screen-space pass), ambient wave synthesis
(Gerstner and FFT), shoal- and shore-aware shallow-water waves (shoaling, refraction, breakers,
run-up), flow-driven river surfaces, local interactive simulation, water shading
composition, shoreline integration, and the transparency/pass-ordering discipline water forces on
the frame. Deep BRDF/scattering math routes to the physically-based-rendering skill; generation of
water bodies, routing, and flow fields routes to terrain-architect (its `03`/`04` hydrology and the
`08`/`27` output contract).

Contents: [The handoff, seen from the render side](#the-handoff-seen-from-the-render-side) ·
[Surface geometry & LOD](#surface-geometry--lod) ·
[Screen-space water: the fullscreen-triangle pass](#screen-space-water-the-fullscreen-triangle-pass) ·
[Ambient waves: Gerstner and FFT](#ambient-waves-gerstner-and-fft) ·
[Calm water: the low-energy regime](#calm-water-the-low-energy-regime) ·
[Shallow water: shoaling, refraction, and breakers](#shallow-water-shoaling-refraction-and-breakers) ·
[Rivers: flow-driven surfaces](#rivers-flow-driven-surfaces) ·
[Interactive simulation patches](#interactive-simulation-patches) ·
[Shading and optics](#shading-and-optics) ·
[Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic) ·
[Shoreline integration](#shoreline-integration) ·
[Transparency & pass ordering](#transparency--pass-ordering) · [Pitfalls](#pitfalls) ·
[Sources & provenance](#sources--provenance)

## The handoff, seen from the render side

Terrain-architect's hydrology handoff (its `08`, "caused, not carved") gives this chapter four
inputs, and the doctrine is that they are *sufficient*:

| Input | Form | What the renderer does with it |
|---|---|---|
| `waterSurface` | Flat elevation per body (sea level for oceans, spill level per lake, a downstream-monotone profile per river) | The datum every wave displaces from; the gameplay swim/buoyancy surface |
| Water depth | Scalar field: `waterSurface - solidTop`, 0 on dry land | Absorption ramp, shoaling, shoreline fade, sim boundary |
| Flow / velocity | 2D vector field (m/s), from routing + discharge, plus the nearshore surface circulation — longshore current, rip jets, inlet/river-mouth jets (terrain-architect `12`) | Flow-map advection, foam alignment, particle steering, sim boundary inflow, wave–current interaction |
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
  with terrain (`10`) or the sea/sky junction band mismatches the land horizon. "Share" means
  one atmosphere LUT/state and the same view-depth coordinate; a private water fog color creates
  a blue/orange seam at sunset precisely where water, land, and sky should agree.
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

**Waves on the analytic plane: layered normal cascades.** The flat datum reads as glass until it
carries wave detail, and on this pass the cheap tier is entirely in shading: perturb the plane
normal at the hit's world XZ with **two to four scrolling layers** at decade-spaced scales. Two
layers is the floor (swell + chop); three reads as open water; the fourth (fine ripple) exists
mainly near the camera and must fade with distance or it aliases into shimmer:

```hlsl
// world-XZ uv at the ray hit; layers decorrelated by scale, direction, AND speed
float3 n = float3(0, 1, 0);                                       // start at the datum normal
n = blend(n, sampleNormal(uv * 0.045 + dir0 * t * 0.35));         // swell   ~20 m
n = blend(n, sampleNormal(uv * 0.21  - dir1 * t * 0.60));         // chop    ~4 m
n = blend(n, sampleNormal(uv * 1.15  + dir2 * t * 0.95) * fade);  // ripple  ~1 m, distance-faded
```

`blend` is a real normal combine — RNM or whiteout from `07`, never a lerp. The layers can be
tiling noise-derived normal maps (indie tier), or the FFT cascades' normal outputs
([Ambient waves](#ambient-waves-gerstner-and-fft)) sampled as textures — the fullscreen pass
consumes either identically. Decorrelation rules: non-parallel directions, scale ratios off
integer multiples, speed ratios irrational-ish — any two layers that line up periodically
produce a visible beat pattern marching across the sea. An analytic Gerstner normal sum
(evaluate ∂h/∂x, ∂h/∂z of 3-6 Gerstner terms at the hit) substitutes for the texture layers
when fetch-bound; derive the foam/whitecap mask from the combined slope either way. None of
this moves the silhouette — crests do not rise, the horizon stays a line — which is exactly the
boundary where the next paragraph takes over.

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

Ambient synthesis as described above is a *deep-water* model: it assumes the bottom is
infinitely far away. The moment the exported depth field says otherwise, the next section owns
the waves.

## Calm water: the low-energy regime

Calm water is not "the easy case with the waves turned down". It is its own regime with its own
failure modes, and most ocean renderers that look superb in a stiff breeze fall apart on a
millpond — the sea goes to patent leather, or to a black void with one searing highlight.

**Why dead calm breaks a wave-based renderer.** Every technique in this chapter derives its
shading from *slope*. Drive the wave amplitude toward zero and slope variance goes with it; the
specular lobe collapses toward a Dirac, and energy conservation concentrates the surviving
highlight into something arbitrarily bright and arbitrarily small. That is the same mechanism as
the distance problem — the far sea is calm *in the pixel footprint* — and it takes the same fix,
in its simplest form: **clamp the slope variance from below at a value matching the solar disc**,
so a mirror sea produces a finite, correctly-sized reflection of the sun rather than a
one-pixel-wide singularity or nothing at all. Bruneton et al. do exactly this and say so.

**Water is never perfectly flat, and there is a smallest possible wave.** Below the gravity-wave
regime, surface tension takes over as the restoring force, giving the full dispersion relation

```
omega^2 = ( g*k + (sigma/rho)*k^3 ) * tanh(k*h)
#   g*k        gravity-restored  -> long waves
#   sigma/rho  surface-tension-restored -> capillary ripples (sigma = surface tension)
```

The two terms trade off, so phase speed has a **minimum** at a wavelength of order centimetres:
there is a shortest wave water can carry, and ripples finer than that are damped out rather than
supported. Practically this means the ripple cascade has a hard floor — a renderer that keeps
adding finer and finer normal-map octaves to "sharpen" calm water is fabricating detail the
physics forbids, and it will alias for its trouble. It also means the first thing a breath of wind
does is generate *capillary* ripples, which is why water visibly "darkens" and loses its mirror in
patches before any swell appears — the cat's paw.

**At low energy the reflection is the whole image.** With little slope to break it up, essentially
everything the viewer sees is the environment, mirrored. Budget accordingly: this is the one
regime where reflection *fidelity* — a real SSR/planar result rather than a coarse cubemap —
dominates perceived quality, and where SSR dropout is most visible because there is no wave chop
to hide the seam. Conversely the expensive wave machinery can be scaled back hard; spend the
saved budget on the reflection.

**Glassy patches are structure, not uniformity.** Real calm water is rarely uniformly calm. Wind
shadows behind headlands and vessels, surface films, and current-convergence lines all damp the
short waves locally, and — per [Sun glitter](#sun-glitter-the-sparkle-path) — a film cuts
mean-square slope by a factor of 2–3. Those patches read as mirror-smooth streaks against a
slightly textured background, and they are much of what makes a real calm sea look alive rather
than like a plane. Render them as *local reductions of the slope-variance field*.

**Residual swell survives dead calm.** Long-period swell is generated by distant weather and
propagates for thousands of kilometres, so a glassy surface still rises and falls on a long, very
low-amplitude undulation. Killing all displacement at low wind gives a rigid sheet; keep a
long-wavelength, low-amplitude component alive and decouple it from local wind, or moored boats
and shorelines stop breathing.

## Shallow water: shoaling, refraction, and breakers

Deep-water synthesis is wrong wherever the bottom matters, and the surf zone is exactly where
players judge water hardest — everyone has stood on a beach; almost no one has floated
mid-ocean. Real waves entering shallow water shorten, slow, steepen, bend until their crests
parallel the depth contours, grow just before they break, break where height outruns depth, and
run up the beach as foam. Every one of those cues is drivable from the exported depth field, and
a sea that ignores them — wind-aligned swell marching diagonally through knee-deep water onto
the sand — is the single most common realism failure in shipped water. Doctrine unchanged from
the ambient section: everything here is a *plausibility approximation driven by data*, not a
fluid simulation, and reviews should name the tier honestly so bug reports route correctly.

### The physics worth stealing

Linear (Airy) wave theory is coastal-engineering canon, cheap enough to evaluate per vertex,
and supplies the entire cue list:

- **Dispersion**: `ω² = g·k·tanh(k·h)` relates frequency ω, wavenumber `k = 2π/L`, and local
  depth `h`. Deep limit (`h > L/2`): `c ≈ sqrt(g/k)` — long waves travel faster. Shallow limit
  (`h < L/20`): `c ≈ sqrt(g·h)` — celerity depends on depth alone.
- **Period is conserved; wavelength is not.** A wave train keeps its ω as it crosses depth
  changes, so as `h` drops, `k` must rise: wavelengths compress and crests bunch toward shore.
  Solve `k(ω, h)` (a few Newton iterations) offline into a small 2D LUT — never per frame.
- **Shoaling**: energy-flux conservation through the slowdown pumps amplitude up; the shallow
  asymptote is Green's law, `a ∝ h^(-1/4)`. The visual: waves visibly *grow* just before
  breaking, then die. Amplitude ramps monotonically *up* then cuts — never a plain fade.
- **Refraction**: the end of a crest sitting in deeper water outruns the end in shallower
  water, so crests rotate toward alignment with depth contours — surf arrives near
  shore-parallel regardless of wind direction, wraps around headlands, and focuses on points.
  This is the strongest single cue in the list.
- **Breaking**: a wave breaks when its height reaches roughly the local depth —
  `H ≈ 0.78·h` (the McCowan-type criterion). *How* it breaks is classified by the
  surf-similarity (Iribarren) number `ξ = tanβ / sqrt(H/L₀)` (β = beach slope, L₀ = deep-water
  wavelength): low ξ → **spilling** (foam crumbling down the face — flat sandy beaches), mid ξ
  → **plunging** (the curling tube — steeper beaches, reef edges), high ξ → **surging /
  collapsing** (no real break, water sloshing up rock). Slope and depth are both in the
  handoff, so *breaker character per shore is data-driven authoring*, not a global setting.

| Visible cue | Physics | Real-time treatment | Driving data |
|---|---|---|---|
| Crests bunch and slow near shore | Dispersion, ω conserved | Wavelength/phase-speed from a `k(ω,h)` LUT | Filtered depth |
| Waves grow just before the break | Green's-law shoaling | `h^(-1/4)`-style amplitude gain, clamped, then cut at break | Filtered depth |
| Surf parallel to every shoreline | Refraction | Travel-time (eikonal) phase field; or blend wave direction toward −∇(shore distance) by shallowness | Depth + shore distance/normal |
| A line of breakers, type varies by coast | `H ≈ 0.78·h`; Iribarren ξ | Break mask where amplitude/depth crosses threshold; breaker profile (spill/plunge/surge) chosen by slope mask | Depth + beach-slope mask |
| Foam born at the break, dying up the beach | Turbulent bore, swash | Foam lifecycle keyed to break mask + phase; decays into run-up streaks | Break mask, shore distance |
| Wet dark sand band that follows the surf | Run-up / swash envelope | Max-recent-run-up envelope feeds the wetness overlay (`13`/`14`) | Run-up height, shore distance |
| Steep breaking chop at river mouths; rips cut smooth lanes through the surf | Wave–current interaction (Doppler-shifted dispersion) | Modulate amplitude, steepness, and break threshold by opposition `dot(waveDir, −flow)`; force chop where opposing flow approaches group speed | Flow field + depth |

### Tier 1 — depth-modulated ambient synthesis

The baseline that every water system should ship: keep the FFT/Gerstner cascades and modulate
them by the depth field at sample time — amplitude attenuated toward zero as depth → 0 (with
the shoaling bump first: gain, then cut), wavelength compressed by sampling the cascades
through a depth-driven UV warp or by cross-fading to a pre-generated "shallow" spectrum
variant, and chop/steepness raised as `a/h` grows so near-shore crests sharpen. For Gerstner
sums, per-wave depth response is direct: evaluate each wave's `k(ω,h)` and Green's gain at the
vertex. Honest limits, stated in review: phases stay wind-aligned (no true refraction — the
diagonal-surf tell survives anywhere the shore is visible), nothing breaks, and depth-warped
UVs shear the cascade textures if pushed hard. Tier 1 alone is acceptable only where the
camera never lingers on a beach.

### Tier 2 — the shore-wave band (production default)

The look players call "realistic waves" is a **separate, authored wave train owned by the surf
zone**, cross-faded with the ambient sea over a blend band offshore. Its components:

- **Phase from travel time, not from wind.** Precompute (at import/cook, from the bathymetry)
  a wave-travel-time field `τ(x)`: the arrival time of a wavefront propagating shoreward at
  depth-dependent speed `c(h) = sqrt(g·h)` (an eikonal/fast-marching solve, seeded from deep
  water). Iso-lines of τ *are* refracted wavefronts — crests wrap headlands, focus on points,
  and align to every shore for free. The cheap fallback — phase straight from the
  shore-distance field — is acceptable for simple coasts but cannot focus or wrap correctly;
  say which one shipped. Animate `phase = τ/T − t/T` and the crests march shoreward forever.
- **Profile, not sine.** Displace a crest profile (authored 1D shape or steepened Gerstner)
  along the phase; steepen it as `a/h` rises; asymmetrize it (steep front face, long back)
  approaching the break. Where the `H ≈ 0.78·h` mask trips, hand over to the breaker
  treatment: spilling = foam front crawling down the face (profile + animated foam, cheap,
  right answer for most beaches); plunging = an authored curl — flipbook, skinned mesh, or
  particle sheet — placed along the break line (hero-tier, budget it); surging = no break,
  boosted run-up against the slope mask that says "rock".
- **Sets and groupiness.** One global period reads as a metronome. Superpose two or three
  periods (7–14 s band) with a slow group envelope so big sets arrive irregularly, and jitter
  phase slightly along-shore. The group envelope is also the run-up driver: big set → big
  run-up → wet-sand band advances (`13`).
- **Foam lifecycle.** Foam is born on the break mask, advected shoreward with the bore, decays
  exponentially into streaks in the swash, and is dragged back by an ebb phase — one
  accumulating foam target with decay, exactly the machinery of the Jacobian whitecap
  accumulator, reused. Hand the *final* foam edge to the shoreline-foam band of
  [Shoreline integration](#shoreline-integration); they must share phase or the surf and the
  shore argue.
- **Energy bookkeeping in the blend band.** Cross-fade ambient cascades *down* as the
  shore-wave band fades *in* (by depth or τ), never add them — added energy doubles wave
  height exactly where shoaling is also boosting it, and the blend band becomes a wall of
  water.

```hlsl
// Shore-wave band evaluation, per vertex/pixel; all fields from the handoff + cook
float  h     = FilteredDepth(xz);                  // bathymetry smoothed at ~L scale
float  tau   = WaveTravelTime(xz);                 // eikonal precompute, speed sqrt(g*h)
float  A     = A0 * GroupEnvelope(tau, t)          // sets: slow multi-period envelope
             * ShoalGain(h)                        // Green's-law bump, clamped
             * saturate(h / hFade);                // and the final cut at the sand
float  phase = frac(tau / T - t / T);              // crests march shoreward
float  brk   = smoothstep(0.70, 0.85, A * profilePeak / max(h, 1e-3)); // H ~ 0.78 h
float  disp  = A * CrestProfile(phase, /*steepen by*/ A / max(h, 1e-3));
// brk gates the breaker treatment (spill foam / plunge construct / surge run-up by slope mask)
```

### Tier 3 — wave particles and packets

The simulation-grade tier: Lagrangian carriers of wave energy advected over the bathymetry and
rasterized into a displacement field each frame. **Wave particles** (Yuksel et al.) made it
real-time — each particle a small wavefront segment that subdivides as fronts spread. Production
water systems of that era are documented in Gonzalez-Ochoa's GDC 2012 *Uncharted* talk (ocean
mesh LOD, wave generation, flow shader); that the shipped technique was specifically wave
particles is commonly repeated but **not confirmed** against the talk — treat it as `?` and do
not cite it as the shipped implementation. **Wave packets / water surface wavelets** (Jeschke & Wojtan and successors) carry a
full dispersive wave *group* per carrier, so refraction, dispersion, and shoaling over
arbitrary bathymetry emerge rather than being painted. Cost honesty: this tier buys emergent
shore behavior and object interaction with research-grade machinery — tens of thousands of
carriers, a rasterization pass, careful LOD — and in production it is usually *targeted*
(wakes, a hero cove) while Tiers 1–2 still carry the open sea. It does not replace the
interactive sim patch: particles carry traveling waves; the patch owns local
splash-and-ripple response. They can share the rasterize-to-overlay stage.

### Shoal awareness is depth awareness, not distance awareness

Key the system off **depth**, never off distance-to-shore alone. An offshore sandbar or reef
must brighten the water color ramp, steepen and break its own line of surf — hundreds of
meters from any shoreline — and let the reformed, smaller wave travel on to break again at the
beach. Double surf lines over bars are a signature of real coasts, and they fall out for free
when shoaling, breaking, and the travel-time solve all read bathymetry; they are *impossible*
when the surf system is keyed to the shoreline distance field. Shore distance drives only what
genuinely belongs to the waterline: run-up, wet sand, and the final foam edge.

### Wave–current interaction: the flow field's part

The fourth handoff input — the flow field — modifies shallow-water waves, and the shore-wave
band must read it or the two water systems of this chapter visibly ignore each other where
they meet. The physics: in a current `U`, the observed frequency Doppler-shifts,
`ω = σ + k·U`, with the intrinsic frequency still obeying `σ² = g·k·tanh(k·h)`. Waves running
*against* a current shorten and steepen (energy piles into a slower-advancing train); when the
opposing current approaches the wave group speed, the waves are **blocked** — they cannot
propagate upstream and must steepen until they break. Waves riding a *following* current
lengthen and flatten. The visible cases are exactly the seams between this section and the
rivers section: a river mouth at outflow (a line of steep, breaking, directionless chop over
the bar, even in a mild sea), tidal inlets, and rip currents — narrow outbound flows that
block incoming surf locally and read as smooth dark lanes cutting through the breaker line,
with their foam streaked *seaward*.

The real-time treatment is modulation, not simulation — same doctrine as the rest of the
section. From the shore band's own quantities: wave direction is `normalize(∇τ)`, opposition
is its dot with the negated flow, and everything keys off that scalar:

```hlsl
float2 U    = DecodeFlow(FlowField.Sample(s, uv));        // handoff flow field, m/s
float  cg   = sqrt(9.81 * max(h, hMin));                  // shallow-water group speed: c_g = c
                                                          // (NO 1/2 — that is the deep-water
                                                          //  c_g = c/2 relation, wrong here)
float  opp  = dot(normalize(gradTau), -U) / cg;           // 1 ~ blocking
A          *= 1.0 + kSteepen * saturate(opp);             // shorten/steepen against flow
brk         = max(brk, smoothstep(0.8, 1.2, opp));        // blocked -> forced break/chop
// opp < 0 (following current): mild lengthen/flatten — scale A and steepness down slightly
```

Where `opp` crosses the blocking range, stop drawing a coherent marching wave train at all:
replace the band locally with steep short chop plus a persistent foam patch (the
river-mouth-bar look), and let the rivers section's flow-mapped surface own the water inside
the outflow. Foam in the surf zone advects by the *sum* of bore motion and the flow field, so
rip and outflow foam streaks point seaward for free. Two refinements, both honestly optional:
fold `U` into the travel-time solve as an anisotropic speed term (`c(h) + U·dir`) so current
refraction lands in the precompute — valid only for static flows like river mouths, since τ is
baked; and modulate at runtime for tidal flows if the game has them. State the limits in
review: this is Doppler-flavored amplitude/steepness shaping — there is no momentum exchange,
no actual blocking dynamics, and rip currents must exist in the exported flow field to appear
(inventing them renderer-side violates the handoff doctrine — route to terrain-architect).

### Data contract additions

Per the chapter's rule — extend the handoff, don't derive hydrology renderer-side — the
shore-wave system asks the pipeline for: **filtered depth** (bathymetry smoothed at roughly
the wavelength being modulated; raw bathymetry noise makes wave response flicker and the break
line dither), a **beach-slope / breaker-class mask** (from the generator's slope analysis —
this is what keeps spilling foam off cliff faces), the **shore normal** (gradient of the shore
distance field, for run-up direction and foam advection), and the **travel-time field** τ
(derived data, baked at import/cook from bathymetry — cheap to store, one R16 channel).
Wave–current interaction needs *no* new data — the flow field is already in the handoff; the
only optional addition is baking static flow into the τ solve as above.
Max shore-wave amplitude joins max ambient amplitude in the culling-bounds inflation.

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

```hlsl
float rayDistance   = max(SceneLinearDepth(bottomUV) - waterLinearDepth, 0.0); // metres in water
float verticalDepth = WaterDepth(worldXZ);                                     // bathymetry field
float3 T             = exp(-sigmaPerBody * rayDistance);                        // Beer-Lambert
float3 waterColor    = refracted * T + scatterColorPerBody * (1.0 - T);

shoreMask   = saturate(verticalDepth / shoreFadeDepth);
causticMask = 1.0 - saturate(verticalDepth / causticFadeDepth);
```

`rayDistance` controls optical extinction along the camera path; `verticalDepth` controls the
shore regime, caustic survival, and shallow-wave response. They are related but not
interchangeable. `sigma` and scatter color belong to the water-body descriptor — ocean, clear
lake, and turbid river must not share one global absorption constant. What that descriptor
contains, and where its numbers come from, is
[Water-body optical identity](#water-body-optical-identity-where-sigma-actually-comes-from)
at the end of this section.
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

### Water-body optical identity: where `sigma` actually comes from

Most water shaders expose `sigma` and a scatter colour as art-directed swatches. They are
measurable physical quantities, and picking them from oceanography instead of from a colour
picker is the cheapest realism win in the whole chapter — it is what separates "blue-tinted
glass" from *this specific water*.

**Pure water is blue for a spectroscopic reason.** Its visible absorption is the high-order
overtone band of the O–H stretch — vibrational, not electronic — which is why absorption is
minimal in the blue and climbs steeply into the red. Pope & Fry's measurements put the minimum
at **0.0044 m⁻¹ at 418 nm**, against **0.62 m⁻¹ at 700 nm**: red is ~140× more strongly absorbed
than blue-violet. In practice red is gone by ~5 m, orange by ~10 m, yellow by ~20 m, green by
~40 m. That single ratio is the entire shallow→deep colour ramp, and it is *not* sky reflection.

```
sigma_RGB ~= (a + b_b) evaluated at ~610 / ~550 / ~450 nm
a_water   ~= (0.29, 0.056, 0.0045) m^-1     # pure water, R/G/B, from Pope & Fry 1997
```

**Three constituents move water off pure blue,** and they are worth exposing as the shader's
actual authoring dials because each has a *distinct* visual signature:

| Constituent | Optical effect | Reads as |
|---|---|---|
| **Chlorophyll** (phytoplankton) | Absorbs blue (~440 nm) *and* red (~675 nm), leaving a transmission window at 550–570 nm | Green. Productive lakes, coastal blooms; pea-soup opaque at high load |
| **CDOM** / tannins / "gelbstoff" | Absorbs steeply toward blue, `a(λ) = a₄₄₀·exp[−S(λ−440)]`, `S ≈ 0.012–0.022 nm⁻¹`. **Scatters not at all** | Transparent but *dark*. Tea/amber shallow, near-black deep |
| **Suspended mineral sediment** | Scattering, near spectrally *flat* (`b_b ∝ λ^−0.5…−1` vs λ^−4.3 for water molecules) | Adds white → raises brightness. Turquoise → green → ochre as load climbs |

The critical distinction for a shader author: **CDOM darkens, sediment brightens.** They are not
interchangeable "murkiness" sliders. Blackwater (Rio Negro, `a_CDOM(440) ≈ 9 m⁻¹`) kills blue
within ~11 cm but passes red to ~1.4 m — so it reads amber in the shallows and, because CDOM
contributes *no* backscatter, near-black and mirror-like over the channel. Model that with a
turbidity slider and you get mud instead.

**Glacial turquoise is not Rayleigh scattering.** This is stated all over the web and is
physically impossible: rock flour is 2–65 µm, 10–100× the wavelength, firmly in the Mie/geometric
regime where scattering is nearly *wavelength-independent*. The real mechanism is a two-step:
flat-spectrum backscatter shortens the mean photon path to order a metre, and over that short
path `a_water` still removes red efficiently while barely touching blue-green. Concentration is
therefore the *hue* knob — more flour shifts it paler and greener, less goes deeper blue — which
is exactly why proglacial lake chains get bluer downstream as flour settles out, and why the same
lake drifts in hue across the melt season.

**Authoring handle: Secchi depth.** The cleanest bridge between an artist-legible dial and the
shader is `Z_SD ≈ 1 / min_λ K_d` (Lee et al. 2015) — "you can see four metres down" fixes the
minimum of the diffuse attenuation spectrum, and *which wavelength* that minimum sits at is the
water's hue. Author clarity plus a water class; solve for `sigma`.

**One trap worth stating:** `c = a + b` (beam attenuation) and `K_d` (diffuse attenuation) are
different coefficients, and `c` is typically 5–20× larger because forward scattering dominates
(`b_f` ≳ 50·`b_b`). Use `c` for a *sharp sightline* — how fast a submerged object's own radiance
is lost, i.e. refracted lookthrough — and `K_d` for the *diffuse light column*, i.e. depth-tinted
volumetric fog. Driving both from one constant makes water look far murkier than it is.

**Clear does not mean bright.** Reflectance goes as `b_b/a`; in the clearest water `b_b` is
molecular only and tiny, so deep clear water returns almost nothing and reads **near-black with a
blue cast**, with all apparent brightness coming off the surface. Shallow clear water over bright
sand is luminous cyan because the *bottom* is the return path. A shader that maps "clear →
bright cyan" gets the tropical shallows right and the drop-off catastrophically wrong; the reef
edge is exactly where `b_b` stops being bottom-dominated and becomes molecular.

**Presets.** Jerlov's water types (oceanic I, IA, IB, II, III; coastal 1C–9C) are the standard
classification, defined by the spectral shape of `K_d`, and Morel's chlorophyll ladder maps them
to a look (type I ≈ 0–0.01 mg/m³, deepest blue; III ≈ 1.5–2.0, green and productive). Ship them
as named presets rather than as sliders. Honest caveat: the numeric `K_d(λ)` tables live in
Jerlov (1976) Tables XXVI–XXVII and Solonenko & Mobley (2015), both paywalled — the values
circulating in blog posts and asset packs are mostly untraced. Either extract them from the
source, or generate the oceanic series by running the Solonenko & Mobley `K_d(a,b)` relation
forward from the chlorophyll ladder, and say which you did.

### Sun glitter: the sparkle path

`sun_glint` in the composition formula above is not a decorative extra — it is the single
brightest thing on a sunlit sea, and getting it wrong is the most common reason ocean renders
read as vinyl. The failure is structural, not a tuning problem.

**The physics.** The sun's disc subtends **0.53°** — about 1/8000 of the hemisphere. The
sea-surface slope distribution is enormously wider: Cox & Munk photographed sun glitter from
aircraft and fitted mean-square slope against wind speed,

```
sigma_c^2 = 0.003 + 1.92e-3 * W        # crosswind component
sigma_u^2 = 0.000 + 3.16e-3 * W        # up/downwind component
sigma_c^2 + sigma_u^2 = 0.003 + 5.12e-3 * W
#   W = wind speed in m/s AT 12.5 m (not the 10 m of standard wind data — convert)
#   valid 1-14 m/s; at 14 m/s total mss ~= (tan 16 deg)^2, i.e. rms slope ~= 0.28
```

so the reflected-direction spread is **tens of degrees** while the source is a fraction of one.
The distribution is *anisotropic* — `sigma_u^2/sigma_c^2` averages about 1.34, ranging 1.0–1.8
with steadier wind giving stronger anisotropy — so the glitter pattern is an ellipse elongated
along the wind, not a disc.

**Why the naive version inverts the physics.** A sharp specular lobe (high Blinn-Phong exponent,
low GGX alpha) on a normal-mapped surface produces one small blown-out highlight where the mirror
direction lands. Reality is the opposite: a *glitter path* stretching tens of degrees toward the
observer, made of thousands of individually resolvable facets winking on and off. A tight lobe is
not "glitter that needs more contrast" — it is the wrong shape of function.

**Three tiers, and the first two are not alternatives.**

| Tier | Mechanism | Use |
|---|---|---|
| Statistical BRDF | Evaluate a microfacet BRDF whose NDF **is** the Cox–Munk anisotropic Gaussian, with Smith masking. Ross et al. 2005 is the standard analytic form; it is what Bruneton's ocean uses | **The base. Always.** Correct energy and lobe width at every distance |
| Discrete glints | Count actual facets reflecting toward the eye within the pixel footprint — Deliot & Belcour's binomial-law method is the current real-time state of the art | Near-to-mid field, where individual sparkles resolve |
| Noise-perturbed specular | Scroll a noise texture through the specular term | Indie tier. Cheap, reads acceptably, physically unfounded |

Tier 1 gives correct *statistics*; tier 2 gives correct *granularity*. Shipping tier 2 alone
gives sparkle that does not integrate to the right brightness; shipping tier 1 alone gives a
correct but slightly too-smooth glitter path in the near field. Production is tier 1 everywhere
plus tier 2 within a fade radius.

**Wind is a rendering parameter here, not just an animation one.** Because mean-square slope is a
function of wind speed, the glitter path *widens and dulls* as wind rises, and *narrows and
intensifies* as it drops. Wire the same wind that drives the wave spectrum into the glitter
variance or the two disagree — a mirror-calm sea with a wide glitter path is an instant tell.

**Slicks are a slope-variance effect, not a colour effect.** Cox & Munk also measured oil-slicked
water: films damp capillary and short gravity waves, cutting total mean-square slope by a factor
of **2–3** and eliminating the skewness entirely. So an oil slick, a wind shadow behind an island,
or a current-convergence line should be rendered as a **local reduction of the slope-variance
field** — which makes it appear as a smooth mirror-like patch against rough sea — not as a dark
albedo decal. This is the mechanism behind every "glassy streak" on a real ocean.

## Distance and filtering: why far water turns to plastic

Water that reads beautifully at 50 m routinely reads as shrink-wrapped perspex at 5 km — a
glossy, uniform dome with one hot highlight. This is not an art problem and it is not fixed by
better textures. It is a filtering failure with four distinct causes, and it is the single most
common complaint about otherwise-good ocean renderers.

**The core mechanism: thrown-away slope variance.** As distance grows, the number of waves inside
one pixel footprint grows without bound. Per-pixel normals computed from displaced geometry
converge to the *mean* normal — vertical — and all the slope variance those waves carried is
silently discarded. With near-zero variance the specular lobe collapses toward a Dirac; energy
conservation then makes the surviving highlight *brighter* as it narrows. One shading sample per
pixel hits or misses it essentially at random as the camera moves, so you get sparkling fireflies
at best and a mirror-flat plastic sheet everywhere else. MSAA does not help — the highlight is
smaller than the geometry it sits on.

**The fix is to move the variance rather than lose it.** Bruneton, Neyret & Holzschuch's ocean
model is built exactly around this: wave trains are attenuated out of the geometry as their
wavelength drops below the projected grid cell, out of the normal map as it drops below the pixel,
and everything removed is accumulated into a **2×2 slope-variance tensor in the wind frame** that
widens the BRDF lobe. Because it is the *same* quantity moved between representations, the
transition is seamless by construction — displaced geometry near, normal detail mid, statistical
BRDF far, with no popping and no discontinuity.

```
# per wave train i, with w_r = the fraction NOT resolved by geometry or normals:
sigma_x^2, sigma_y^2  =  SUM_i  (k_i,x^2, k_i,y^2)/||k_i||^2 * (1 - sqrt(1 - ||k_i||^2 * w_r^2 * h_i^2))
#   axes are along/across the wind - i.e. exactly the Cox-Munk ellipse from the glitter section
#   practical trick: total variance for ALL waves on the CPU, subtract the RESOLVED waves in the
#   shader, so shader cost scales with resolved wave count and is MINIMAL for distant views
```

Two details worth stealing verbatim: Nyquist argues the geometry cutoff should be 2 grid cells,
but that over-blurs in practice — Bruneton et al. use **N_min = 1.0, N_max = 2.5** with a
smoothstep between. And the variance must be **clamped to a minimum** matching the solar disc,
or dead-calm water still produces a Dirac (see [Calm water](#calm-water-the-low-energy-regime)).

**Cause two: Fresnel that ignores roughness.** Plain Schlick assumes a *smooth* surface. On a
rough surface at grazing incidence, microfacet masking means the effective reflectance is
substantially lower than Schlick predicts. Ship plain Schlick on a low-variance distant ocean and
the horizon band goes to near-100% mirror — that is precisely the chrome-dome look. The fix is
one line, fitted for `sigma_v < 0.5`:

```hlsl
float  sigma_v2 = sigma_x2*cos2Phi + sigma_y2*sin2Phi;        // slope variance toward the viewer
float  sigma_v  = sqrt(sigma_v2);
float  F = R + (1.0-R) * pow(1.0-cosThetaV, 5.0)
             * exp(-2.69*sigma_v) / (1.0 + 22.7*pow(sigma_v, 1.5));   // Bruneton et al. 2010
```

Also make sure the Smith masking/shadowing term is present in the sun lobe — that is what stops
grazing-angle over-brightening, and with a statistical BRDF you get wave self-shadowing from it
for free rather than needing a shadow map.

**Cause three: binary whitecaps.** A per-pixel Jacobian threshold (as in
[Ambient waves](#ambient-waves-gerstner-and-fft)) is correct up close and *disintegrates* at
distance: sub-pixel foam either aliases into shimmer or vanishes, so the far sea loses the
speckle that tells the eye it is rough. The prefilterable fix assumes the Jacobian is normally
distributed within the footprint and integrates the coverage in closed form:

```
W  ~=  0.5 + 0.5 * erf( (sqrt(2)/(2*sigma_A)) * (eps - mu_A) )
#   mu_A, sigma_A^2 = mean and variance of the Jacobian over the pixel footprint
#   BOTH are linearly prefilterable -> free hardware mipmapping and aniso filtering
```

Foam then has a correct *fractional coverage* at every distance instead of a binary mask.
Ground-truth the amount against Monahan & O'Muircheartaigh's whitecap–wind relation,
`W = 3.84e-6 * U^3.41` (U at 10 m): the exponent is steep enough that foam is essentially absent
at 5 m/s and dominant by 15 m/s, so coverage must be driven by wind, not by a constant.

**Cause four: everything else that flattens distance.** Missing aerial perspective (the horizon
keeps full contrast and saturation and reads as a hard shell — share the atmosphere LUT with
terrain, per `10`); a constant sky tint instead of a *variance-filtered* environment fetch, which
throws away the sky gradient the reflection should carry; and missing water-leaving radiance
(`I_sea ≈ L_sea·(1 − F̄)`), without which the surface only reflects and never transmits, so it has
no volume at all — the literal shrink-wrap reading. A cheap trick worth knowing: put non-zero
radiance *below* the horizon in the environment map, since downward-reflected rays physically
re-reflect or refract; without it distant wave troughs go too dark.

**The unifying idea.** Cox & Munk's slope statistics, Bruneton's variance-fed BRDF, Toksvig and
LEAN and Kaplanyan-style NDF filtering, and prefilterable whitecap coverage are all the same
move: **carry a prefilterable statistic of unresolved sub-pixel surface variation alongside the
resolved geometry, and let the shading model consume it.** Build the pipeline around that one
principle and correct glitter, correct distant roughness, correct foam coverage and freedom from
specular aliasing all fall out together. Bruneton's analytic form is preferable where the
spectrum is known (no screen-space derivative error, exact at grazing angles); Kaplanyan/Tokuyoshi
geometric specular AA is the numerical fallback for residual curvature. Route the general
normal-variance-to-roughness math to physically-based-rendering.

## Shoreline integration

The waterline is where water rendering is actually judged, because it is where the water surface
meets `01`/`06` terrain at a shallow grazing angle — the worst case for every artifact class.

Historically, the shoreline was two polygons crossing: the water plane cut through terrain and
artists hid the z-fighting with a foam strip. The modern shoreline is data-driven. Bathymetry
defines the submerged shape and optical path; scene-depth difference softens the visible
intersection; shore distance/flow drive foam and run-up; the wetness overlay records the water's
reaction on land. A hard intersection ribbon is not a shoreline architecture.

- **Depth fade** ("soft intersection"): fade water opacity, distortion, and specular over the
  first few centimetres-to-metres of water depth, using scene-depth-vs-surface-depth (the "depth
  fade" node family in engine material editors). This removes the hard polygonal intersection
  line. It is a *cosmetic* fade — the swim volume still starts at the datum; do not let gameplay
  read the faded visual edge.
- **Wet-sand band**: drive a wetness band above the waterline from wave run-up (the max-recent
  run-up envelope of the shore-wave band —
  [Shallow water](#shallow-water-shoaling-refraction-and-breakers)) plus the exported wetness map — darkened albedo, boosted specular,
  handled by the surface-state system (`13`) consuming aux maps per `14`. The band must *move*
  with the waves' run-up envelope, lagging and drying, or the beach reads as painted.
- **Shoreline foam**: an advected foam texture in a band defined by shore distance, phase-driven
  so it pulses with the incoming wave cadence — tie its phase to the shore-wave band's
  travel-time phase (the same `τ/T − t/T`), or foam and waves visibly disagree; where a
  shore-wave foam lifecycle exists, this band is its final decay stage, not a second system.
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
- **Wind-aligned surf**: swell crosses shallow water at the wind angle and hits the beach
  diagonally — no shore-wave tier, or Tier 1 shipped where the camera lives on the coast. Add
  the shore-wave band; refraction (crests parallel to shore) is the cue the eye checks first.
- **Waves marching through the beach**: displacement still non-zero at depth 0; crests poke
  through the sand. The depth-attenuation ramp is missing or keyed to the wrong depth source
  (scene depth instead of the bathymetry field).
- **Metronome surf**: the whole coastline breaks in unison on one global period. Superpose 2–3
  periods with a group envelope and jitter phase along-shore; sets must arrive irregularly.
- **Sandbars and reefs stay glassy**: shoaling/breaking keyed to shore distance, so offshore
  shoals never shoal. Key everything off the (filtered) depth field; the double surf line over
  a bar should fall out for free.
- **Breakers on cliffs**: spilling foam crawling up rock faces — the break mask fired on depth
  alone. Gate breaker *type* by the beach-slope/breaker-class mask (Iribarren logic): steep
  shores surge, they don't spill.
- **Doubled energy in the blend band**: shore-wave band added on top of un-attenuated ambient
  cascades; a wall of water stands exactly where shoaling also boosts amplitude. Cross-fade
  energy between the systems, never sum them.
- **Break-line dither/flicker**: the `H ≈ 0.78·h` mask evaluated against raw bathymetry noise.
  Filter depth at the wavelength scale before it drives wave response.
- **Foam double-count in the surf zone**: Jacobian whitecaps and breaker foam both firing on
  the same crests. In the shore band, the breaker lifecycle owns foam; fade the Jacobian
  accumulator out with the ambient cascades.
- **One blown highlight instead of a glitter path**: a sharp specular lobe on water. The sun is
  0.53° wide; the sea-slope distribution is tens of degrees. The lobe shape is wrong, not its
  intensity — evaluate a Cox–Munk-width statistical BRDF and add discrete glints on top.
- **Glitter that ignores wind**: wave spectrum driven by wind speed, glitter variance hard-coded.
  Mean-square slope is a function of wind — a mirror-calm sea with a wide glitter path, or a gale
  with a needle highlight, both read as broken. One wind, both consumers.
- **Slicks painted as dark decals**: a surface film's real effect is halving-to-thirding the local
  mean-square slope, which makes it a *smooth mirror patch*, not a stain. Modulate the
  slope-variance field, not albedo.
- **Distant sea turns to plastic**: slope variance from sub-pixel waves discarded instead of being
  folded into BRDF roughness. The lobe collapses toward a Dirac and energy conservation brightens
  what survives. Track the variance tensor and feed it the leftovers (Bruneton).
- **Chrome-dome horizon**: plain Schlick Fresnel on a low-variance distant ocean drives grazing
  reflectance to ~100%. Use the roughness-aware Fresnel fit and keep Smith masking in the sun lobe.
- **Whitecaps shimmer or vanish at distance**: a binary per-pixel Jacobian threshold cannot be
  filtered. Switch to prefilterable statistical coverage over the footprint's Jacobian mean and
  variance; ground the amount against `W = 3.84e-6·U^3.41`.
- **Deep clear water rendered bright cyan**: reflectance goes as `b_b/a`, and in clear water `b_b`
  is molecular and tiny — deep clear water is near-black. Bright cyan is *shallow* water over a
  bright bottom. Getting this backwards kills every reef drop-off.
- **Tannin-stained water modelled with a turbidity slider**: CDOM absorbs and does not scatter, so
  blackwater is transparent-but-dark (amber shallow, near-black deep). Raising scattering gives
  mud. They are opposite controls.
- **Clear tropical water looks washed out**: blue absorption taken from Smith & Baker (1981),
  which is ~3.4× too high there due to scattering contamination. Use Pope & Fry (1997) above
  380 nm.
- **Surf marches unchanged across the river mouth**: the shore-wave band reads only depth, so
  incoming waves ignore the outflow that should steepen, block, and break them — and rip
  currents in the flow field leave no lanes in the breaker line. Modulate the band by
  opposition to the flow field (wave–current interaction, above); where flow data shows no
  rip/outflow, the missing feature is generation-side — route to terrain-architect.
- **Refraction leaking objects above water**: missing depth reject on the distorted sample. The
  single most common shipped water bug; the fix is four shader lines (above).
- **SSR dropout at grazing/screen edge**: mirror-bright water goes flat exactly at the horizon
  and screen borders. Mandatory fallback chain with brightness-matched cubemap; never ship SSR-only.
- **Waterline crawl on LOD change**: water and terrain refine on different schedules; the
  intersection line steps visibly. Shared SSE currency + shoreline LOD bias (`11` symptom table).
- **Water/land horizon color seam**: water applies a private fog constant while terrain samples
  `10`'s Rayleigh/Mie aerial-perspective state. One atmosphere LUT, one view-depth convention,
  sampled by both paths.
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
  treatment of wave detail crossing from geometry band to shading band — the slope-variance
  tensor, the roughness-aware Fresnel fit, and the variance-filtered environment fetch used in
  [Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic).
  [HAL open access](https://inria.hal.science/inria-00443630).
- **P** — Cox & Munk, "Measurement of the Roughness of the Sea Surface from Photographs of the
  Sun's Glitter" (Journal of the Optical Society of America 44(11), 838–850, 1954): the
  sea-surface slope distribution and its wind-speed regressions; the foundation of every
  statistical glitter model. Wind speed is referenced at **12.5 m**, and the fit is calibrated
  only over 1–14 m/s — do not extrapolate to storm winds. Verified 2026-08 against the paper.
  [DOI 10.1364/JOSA.44.000838](https://doi.org/10.1364/JOSA.44.000838).
- **P** — Ross, Dion & Potvin, "Detailed analytical approach to the Gaussian surface
  bidirectional reflectance distribution function specular component applied to the sea surface"
  (JOSA A 22(11), 2442–2453, 2005): the Gaussian-slope microfacet BRDF with Smith masking that
  Bruneton's model evaluates. The analytic base tier for glitter.
- **P** — Discrete-glint rendering lineage: Jakob, Hašan, Yan, Lawrence, Ramamoorthi & Marschner,
  "Discrete Stochastic Microfacet Models" (ACM TOG 33(4), SIGGRAPH 2014); Yan, Hašan, Jakob,
  Lawrence, Marschner & Ramamoorthi, "Rendering Glints on High-Resolution Normal-Mapped Specular
  Surfaces" (ACM TOG 33(4), 2014); Yan, Hašan, Marschner & Ramamoorthi, "Position-Normal
  Distributions for Efficient Rendering of Specular Microstructure" (ACM TOG 35(4), 2016);
  Zirr & Kaplanyan, "Real-time Rendering of Procedural Multiscale Materials" (I3D 2016);
  Chermain, Sauvage, Dischler & Dachsbacher (CGF 39(7), Pacific Graphics 2020) and Chermain,
  Lucas, Sauvage, Dischler & Dachsbacher (I3D 2021) for real-time procedural glints;
  **Deliot & Belcour, "Real-Time Rendering of Glinty Appearances using Distributed Binomial Laws
  on Anisotropic Grids" (HPG 2023, Best Paper; CGF 42(8))** — the current real-time state of the
  art. Author lists verified 2026-08.
- **P** — Dupuy & Bruneton, "Real-time Animation and Rendering of Ocean Whitecaps" (SIGGRAPH Asia
  2012 Technical Briefs, Article 15): the prefilterable statistical whitecap coverage
  (`W ≈ ½ + ½·erf(...)` over the Jacobian's footprint mean and variance). The direct sequel that
  fills the gap Bruneton et al. 2010 explicitly left open — that paper states it does **not**
  handle whitecaps. [Code](https://github.com/jdupuy/whitecaps).
- **P** — Monahan & O'Muircheartaigh, "Optimal Power-Law Description of Oceanic Whitecap Coverage
  Dependence on Wind Speed" (Journal of Physical Oceanography 10(12), 2094–2099, 1980):
  `W = 3.84×10⁻⁶·U^3.41` (U at 10 m). The oceanographic ground truth for how much foam a given
  wind should produce.
- **P** — Pope & Fry, "Absorption spectrum (380–700 nm) of pure water. II. Integrating cavity
  measurements" (Applied Optics 36(33), 8710–8723, 1997): the modern pure-water absorption
  spectrum; minimum **0.0044 m⁻¹ at 418 nm**. Use this above 380 nm.
  ⚠️ **Do not use Smith & Baker (1981) for blue absorption** — that era's measurements were
  scattering-contaminated and give `a(420)` ~3.4× too high, which desaturates clear water.
  Smith & Baker remains correct for UV (<380 nm) and for `K_d`.
- **P** — Braun & Smirnov, "Why is water blue?" (Journal of Chemical Education 70(8), 612, 1993):
  water's visible absorption is vibrational O–H overtone spectroscopy, not sky reflection.
- **P** — Lee et al., "Secchi disk depth: A new theory and mechanistic model for underwater
  visibility" (Remote Sensing of Environment 169, 139–149, 2015): shows the classical Secchi
  relation is not derivable from radiative transfer and replaces it with `Z_SD ≈ 1/min_λ K_d` —
  the artist-dial-to-`sigma` bridge. The classical `K_PAR = 1.44/Z_SD` constant is Holmes (1970),
  the best-performing of ~13 published constants spanning 1.27–1.86.
- **P** — Jerlov, *Marine Optics* 2nd ed. (Elsevier, 1976), Tables XXVI–XXVII; Solonenko & Mobley,
  "Inherent optical properties of Jerlov water types" (Applied Optics 54(17), 5392–5401, 2015);
  Morel (1988) for the Jerlov↔chlorophyll ladder. The water-type presets.
  ⚠️ **The numeric `K_d(λ)` tables in all three are paywalled and were NOT obtained** — values
  circulating in blog posts and asset packs are largely untraced. Either extract from source or
  generate the oceanic series from the Solonenko & Mobley `K_d(a,b)` relation, and say which.
- **P** — Babin, Morel, Fournier-Sicre, Fell & Stramski (Limnology & Oceanography 48(2), 843–859,
  2003): mass-specific scattering, ≈0.5 m²/g for mineral-dominated suspended matter at 555 nm —
  the concentration-to-optics bridge.
- **F/synthesis** — **Glacial-flour turquoise.** The popular Rayleigh/Tyndall explanation is
  physically wrong (rock flour is 2–65 µm, 10–100× the wavelength — Mie/geometric regime, where
  scattering is nearly wavelength-independent). The mechanism given in this chapter — flat
  backscatter shortens the photon path, over which `a_water` still removes red — is **synthesis
  from verified relations, not a quoted result**: a targeted search found *no* peer-reviewed
  optical study of proglacial-lake colour with measured reflectance, particle-size distribution
  and IOPs together. Treat the mechanism as sound but underived, and say so if challenged.
- **P** — Specular-aliasing / normal-variance-to-roughness lineage: Toksvig, "Mipmapping Normal
  Maps" (Journal of Graphics Tools 10(3), 65–71, 2005); Olano & Baker, "LEAN Mapping" (I3D 2010,
  181–188); Kaplanyan, Hill, Patney & Lefohn, "Filtering Distributions of Normals for Shading
  Antialiasing" (HPG 2016); **Tokuyoshi & Kaplanyan, "Improved Geometric Specular Antialiasing"
  (I3D 2019)** — the current default, and specifically better at grazing angles, which is where
  a water horizon lives. The math routes to physically-based-rendering.
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
- **P** — Linear (Airy) wave theory — dispersion `ω² = gk·tanh(kh)`, shallow-water celerity
  `sqrt(g·h)`, Green's-law shoaling `a ∝ h^(-1/4)`, refraction: coastal-engineering canon;
  textbook treatment in Dean & Dalrymple, *Water Wave Mechanics for Engineers and Scientists*
  (1991). Constants quoted from model knowledge of the textbooks, not re-derived.
- **P** — Breaker criterion `H ≈ 0.78·h` (McCowan lineage) and surf-similarity/breaker
  classification via the Iribarren number: Battjes, "Surf Similarity", *Proceedings of the 14th
  International Conference on Coastal Engineering*, Copenhagen, ASCE, 1974, 466–480 (verified
  2026-08 — note several citation databases propagate a wrong "Honolulu, 446–480"; Honolulu was
  the 15th ICCE, 1976).
- **P** — Wave–current interaction (Doppler-shifted dispersion `ω = σ + k·U`, steepening
  against opposing flow, blocking near group speed): Peregrine, "Interaction of Water Waves
  and Currents", *Advances in Applied Mechanics* 16, 1976.
  [Semantic Scholar (verified 2026-08)](https://www.semanticscholar.org/paper/Interaction-of-Water-Waves-and-Currents-Peregrine/ead4947119505f48eaa8adaa4a3d78da7c722fad).
  The renderer-side opposition-scalar treatment is F-tier practice, not from the paper.
- **P** — Yuksel, House & Keyser, "Wave Particles" (SIGGRAPH 2007, ACM TOG 26(3)): Lagrangian
  wave carriers rasterized to a height field; object interaction.
  [Author page (verified 2026-08)](https://www.cemyuksel.com/research/waveparticles/).
- **T** — Gonzalez-Ochoa, "Water Technology of Uncharted" (GDC 2012, Naughty Dog): shipped
  ocean/beach water — mesh LOD, wave generation, flow shader.
  [GDC Vault (verified 2026-08)](https://gdcvault.com/play/1015309/Water-Technology-of).
  Whether the shipped waves were specifically *wave particles* is **`?`** — widely repeated,
  not verified against the talk.
- **P** — Jeschke & Wojtan, "Water Wave Packets" (SIGGRAPH 2017); Jeschke, Skřivan,
  Müller-Fischer, Chentanez, Macklin & Wojtan, "Water Surface Wavelets" (SIGGRAPH 2018):
  dispersive Lagrangian wave groups; emergent refraction/shoaling over bathymetry.
  [ACM DL (verified 2026-08)](https://dl.acm.org/doi/10.1145/3197517.3201336).
- **T** — Ang, Catling, Ciardi & Kozin, "The Technical Art of Sea of Thieves" (SIGGRAPH 2018
  Talks): stylized FFT water and its supplements in a shipped open-sea title.
  [ACM DL (verified 2026-08)](https://dl.acm.org/doi/10.1145/3214745.3214820).
- **F** — The travel-time (eikonal) shore phase field, breaker-profile authoring
  (spill/plunge/surge constructs), group-envelope "sets", foam lifecycle, and blend-band
  widths: production practice assembled from multiple talks and community writeups; no single
  canonical source. The `0.70–0.85` break-mask window and `hFade` style constants are tuning
  ranges, not measured standards.
- **?** — Attribution of specific shallow-water shoaling approximations to particular shipped
  titles beyond the two talks above: multiple GDC/SIGGRAPH-Advances talks cover it; treat any
  further specific title claim as unverified.
