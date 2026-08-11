# Water Rendering

Water on terrain — oceans, rivers, lakes — arrives from the generation side as *still data*: flat
surface datums, a depth field, a flow field. Everything that moves is made here. This chapter owns
the engine side of that handoff: water surface geometry and its LOD (meshed or the meshless
screen-space pass), ambient wave synthesis
(Gerstner and FFT), shoal- and shore-aware shallow-water waves (shoaling, refraction, breakers,
run-up), flow-driven river surfaces, local interactive simulation, man-made bodies (pools, tanks,
canals), water shading composition, caustics, shoreline integration, and the
transparency/pass-ordering discipline water forces on the frame. Deep BRDF/scattering math routes to the physically-based-rendering skill; generation of
water bodies, routing, and flow fields routes to terrain-architect (its `03`/`04` hydrology and the
`08`/`27` output contract).

Contents: [The handoff, seen from the render side](#the-handoff-seen-from-the-render-side) ·
[Sea states: the energy ladder](#sea-states-the-energy-ladder) ·
[Surface geometry & LOD](#surface-geometry--lod) ·
[Screen-space water: the fullscreen-triangle pass](#screen-space-water-the-fullscreen-triangle-pass) ·
[Ambient waves: Gerstner and FFT](#ambient-waves-gerstner-and-fft) ·
[Calm water: the low-energy regime](#calm-water-the-low-energy-regime) ·
[Shallow water: shoaling, refraction, and breakers](#shallow-water-shoaling-refraction-and-breakers) ·
[Aerated water: foam, spray and whitewater](#aerated-water-foam-spray-and-whitewater) ·
[Rivers: flow-driven surfaces](#rivers-flow-driven-surfaces) ·
[Interactive simulation patches](#interactive-simulation-patches) ·
[Man-made water: pools, tanks and channels](#man-made-water-pools-tanks-and-channels) ·
[Shading and optics](#shading-and-optics) ·
[Caustics: the other half of the light path](#caustics-the-other-half-of-the-light-path) ·
[Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic) ·
[Shoreline integration](#shoreline-integration) ·
[Transparency & pass ordering](#transparency--pass-ordering) ·
[Engine-native water](#engine-native-water-the-ue-water-plugin-read-as-architecture) ·
[Stylized water](#stylized-water-same-contracts-different-bands) · [Pitfalls](#pitfalls) ·
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
| `liquidBody[i]` | Per-body record (terrain-architect `28`, registered in its `08`/`27`): `bodyType` (sea / lake / pond / river / stream / estuary / wetland), `ior`, derived optics (`a_RGB`, `b_b_RGB`, `c_RGB`, `K_d_RGB`, scatter colour), the fetch/exposure field for enclosed water, causal state, QA fields (Secchi, Jerlov/Forel-Ule class) | **`bodyType` selects the surface model**: sea gets swell + tide + nearshore circulation; a lake gets **fetch-limited wind waves only** — no swell, no current (suppress the residual-swell component of [Calm water](#calm-water-the-low-energy-regime) on lakes, and scale the wave spectrum by the fetch field); rivers get flow. Also **the source of `sigmaPerBody`, `scatterColorPerBody`, and the Fresnel `F0`** — see [Water-body optical identity](#water-body-optical-identity-where-sigma-actually-comes-from). `ior` drives surface Fresnel and refraction bending (never hardcode 1.33); beam attenuation `c` drives sharp sightlines; `K_d` drives the diffuse depth column |

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

## Sea states: the energy ladder

Water is not one rendering problem. A mirror-calm lake and a storm sea share a surface model and
almost nothing else: which techniques matter, which dominate the frame, and which can be switched
off entirely all change with energy. The Beaufort scale — long since given standard wind-speed and
sea-state equivalents by the meteorological bodies — is the right spine, because its descriptors
are *visual observations* and therefore map directly onto rendering features.

| Bft | Wind (kt) | Observed sea (NOAA/WMO wording) | What the renderer must switch on |
|---|---|---|---|
| 0 | <1 | "Sea surface smooth and mirror-like" | Reflection fidelity is everything; **minimum slope-variance clamp** or the sun becomes a Dirac |
| 1 | 1–3 | "Scaly ripples, no foam crests" | Capillary detail only — normal-map band, no displacement |
| 2 | 4–6 | "Small wavelets, crests glassy, no breaking" | Displacement begins; still no foam anywhere |
| **3** | **7–10** | "Large wavelets, crests begin to break, **scattered whitecaps**" | **Foam turns on here** — the Jacobian/coverage path starts contributing |
| 4 | 11–16 | "Small waves, numerous whitecaps" | Whitecap coverage climbs steeply; glitter path widens |
| **5** | **17–21** | "Moderate waves, many whitecaps, **some spray**" | **Spray particles turn on**; foam becomes a major albedo term |
| 6 | 22–27 | "Larger waves, whitecaps common, more spray" | Aerated water is now a first-class material, not a decal |
| **7** | **28–33** | "Waves 13–19 ft, **white foam streaks off breakers**" | **Streaked, advected foam** — orientation along wind matters |
| 8 | 34–40 | "Edges of crests begin to break into **spindrift**, foam blown in streaks" | Wind-torn spray leaving the crest; strong aerial perspective |
| 9–11 | 41–63 | "Dense streaks of foam, spray may reduce visibility" → "foam patches cover sea" | Spray becomes atmospheric — a participating medium, not sprites |
| 12 | 64+ | "Sea completely white with driving spray" | Foam coverage saturates; the surface is barely water any more |

Three transitions are worth hard-coding as feature gates, because they are observational facts
rather than art direction: **whitecaps begin at Force 3**, **spray begins at Force 5**, and **foam
streaks begin at Force 7**. They also cross-validate the coverage model in
[Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic): Monahan's
`W = 3.84e-6·U^3.41` puts whitecap coverage at essentially zero around 5 m/s (~0.1%) and
conspicuous by 15 m/s (~4% of the surface), and Force 3 is 7–10 kt ≈ 3.6–5.1 m/s. An empirical formula and a 19th-century observational scale
agreeing on where foam starts is a good sign both are right — and a strong argument for driving
foam from wind rather than from a hand-tuned constant.

The **WMO sea state code** (built on the Douglas scale) is the parallel system, and
it classifies the *sea* rather than the *wind* — useful when swell arrives from a distant storm and
local wind does not explain the surface. Significant wave height `H_s` (the mean of the highest
third, and `≈ 4·sqrt(m₀)` from the spectrum's zeroth moment) is its currency and the natural
parameter to expose in a wave-spectrum UI.

**One wind, every consumer.** The same wind speed must drive the wave spectrum, the whitecap
coverage, the glitter slope variance, the spray rate and the foam streak direction. Wiring them
separately is how you get a mirror-calm sea covered in foam, or a gale with a needle-sharp sun
highlight — both instantly wrong, and both common.

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
infinitely far away. The moment the exported depth field says otherwise,
[Shallow water](#shallow-water-shoaling-refraction-and-breakers) owns the waves — and at the
opposite end of the energy ladder, the low-wind case has its own failure modes.

## Calm water: the low-energy regime

Beaufort 0–2 is not "the easy case with the waves turned down". It is a distinct regime that
breaks several assumptions the rest of this chapter relies on, and it is where a water renderer
most often looks *obviously* synthetic — because there is nothing left to hide behind. The
classic failure on a millpond is one of two: the sea goes to patent leather, or to a black void
with one searing highlight.

**There is a smallest possible wave, and it is not zero.** Including surface tension, the
dispersion relation is

```
omega^2 = ( g*k + (sigma/rho)*k^3 ) * tanh(k*h)      # sigma = surface tension, rho = density
```

The `k³` term means phase speed *rises* again for very short waves, so it has a **minimum: about
23.1 cm/s, at a wavelength of about 1.73 cm.** Below that wavelength you are in the capillary
regime (surface tension restoring), above it the gravity regime. Two consequences: a spectrum has
a natural high-frequency cutoff around a couple of centimetres — ripples finer than the minimum
are *damped out rather than supported*, so a renderer that keeps adding finer normal-map octaves
to "sharpen" calm water is fabricating detail the physics forbids, and will alias for its
trouble — and wind cannot raise waves at all until it can push past that minimum
speed, which is why a breeze produces *patches* of ripple ("cat's paws") separated by glassy
water rather than uniform texture.

**Dead calm is genuinely hard, for a specific reason.** As slope variance → 0, a microfacet
specular lobe collapses toward a Dirac, and energy conservation makes what survives brighter as it
narrows. The result is a single blown-out pixel-ish highlight instead of a sun reflection with
finite extent. The fix is the same one that saves distant water: **clamp the slope variance to a
minimum corresponding to the solar disc** (0.53°), so even a perfectly still surface produces a
sun image of the right angular size — Bruneton et al. state the clamp explicitly. This is the
low-energy end of the same machinery described in
[Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic), and the symmetry
is exact: the far sea is calm *in the pixel footprint*. Variance is the common currency at both
extremes.

**What actually sells calm water is reflection fidelity, not the surface.** With slope variance
near zero the water is a mirror, so every reflection error is presented at full strength and
undamped: SSR dropout at screen edges, missing off-screen geometry, a low-resolution cubemap
fallback, a reflection that disagrees with the real scene. Rough water hides all of these; calm
water audits them. Budget accordingly — for a still lake, planar reflection is often the honest
choice precisely because it is the case where SSR's failure modes are most visible.

**Slicks and wind shadows are variance features.** Surface films damp capillary and short gravity
waves — Cox & Munk measured slicked water at **2–3× lower** total mean-square slope than clean sea
(per [Sun glitter](#sun-glitter-the-sparkle-path)) — so an oil slick, a wind shadow behind an
island or a current convergence line renders as a
**smooth mirror patch against rougher water**, not as a dark decal. Modulate the local
slope-variance field; the albedo barely changes. This is also why calm water is rarely uniformly
calm: real still water is a patchwork of glassy and faintly-textured regions — much of what makes
a real calm sea look alive rather than like a plane — and a perfectly
uniform mirror reads as fake almost as strongly as a uniformly rough one.

**Residual swell survives dead calm — on the sea.** Long-period swell is generated by distant
weather and propagates for thousands of kilometres, so a glassy ocean still rises and falls on a
long, very low-amplitude undulation. Killing all displacement at low wind gives a rigid sheet;
keep a long-wavelength, low-amplitude component alive and **decouple it from local wind**, or
moored boats and shorelines stop breathing. (This is also the case the WMO sea-state code exists
for — sea classified by the *sea*, not the wind — see
[Sea states](#sea-states-the-energy-ladder).) **This is gated by `bodyType`**: a lake has no
distant storm feeding it, so it gets *no* residual swell — dead calm on a lake really is a mirror,
and its only waves are local, fetch-limited wind waves. Swell on a mountain tarn is a classic
misclassification tell (the handoff table above; terrain-architect `03`).

**Bands that vanish, and one that does not.** In this regime foam is *absent* (below Force 3),
spray is absent (below Force 5), whitecap machinery contributes nothing, and displacement is
negligible — so the geometry and foam budgets collapse and can be spent on reflection quality
instead. What does *not* vanish is the water-body optics of
[Water-body optical identity](#water-body-optical-identity-where-sigma-actually-comes-from):
with no surface agitation to scatter light, depth-dependent absorption and the bottom return are
the entire look of a calm shallow lake.

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

## Aerated water: foam, spray and whitewater

When a wave breaks, a fall lands, or a rapid churns, air is entrained and the result is **not water
with foam painted on it — it is a different material**. Treating it as a texture on a transparent
surface is the single most common reason breaking waves, rapids and waterfalls read as wet plastic:
the surface underneath keeps doing Fresnel and refraction when physically there is nothing left to
see through.

**The physics, and the numbers that matter.** Whitecaps and foam are weakly-absorbing,
strongly-scattering two-phase media. Measured **void fractions run 60–99%** in surface whitecaps —
i.e. liquid water is only ~1–40% of the volume — with **mean bubble diameters of 0.16–1 mm**.
Whiteness comes from **multiple scattering across thousands of air–water interfaces**, not from
pigment, which is why foam is broadband white in the visible where water barely absorbs.

**Foam albedo is a decay curve, not a constant** — and this is the most useful single fact here:

| State | Visible reflectance | Reads as |
|---|---|---|
| Fresh, intense breaking | **~50%** | Brilliant white, the moment of the break |
| Active whitecap | **~40%** | The body of the foam |
| Thin residual foam / bubble plume | **~18%** | The dissipating streak behind the crest |

The widely-quoted **~22% (Koepke 1984)** is a *time-averaged effective* whitecap reflectance
derived from film density, and it under-represents fresh foam — it is the right number for
averaging a whole sea over time, and the wrong number for a hero breaking wave. Ship the decay,
not the average: foam should be born bright and fade to a dim streak, with reflectance falling as
the bubble plume thins. A constant-albedo foam texture is why most game foam looks like paint.

**Foam is not spectrally flat.** Reflectance drops sharply into the near-infrared, with troughs at
roughly **750, 980 and 1200 nm** corresponding to liquid-water absorption bands — bubbles lengthen
the path through water and *enhance* its absorption. Visible-band rendering can treat foam as
white, but any NIR-sensitive pass (some sensor/thermal views, certain stylised looks) must not.

**Three classes, one seeding criterion.** Production splits aerated water into sets that behave
differently and cost differently — see `19` for the simulation side:

| Class | Where | Motion | Cheapest honest rendering |
|---|---|---|---|
| **Spray** | Above the surface | Ballistic — gravity + drag, decoupled from the fluid | Bright short-lived sprites; at high wind becomes a *participating medium*, not sprites |
| **Foam** | On the surface | Advected with the surface flow, decaying | Albedo layer that **kills the Fresnel term beneath it** |
| **Bubbles** | Below the surface | Buoyant, advected, rising to feed foam | Density term in the water volume; brightens *and* opacifies from below |

Seed all three from the same criterion — the Jacobian/folding signal of
[Ambient waves](#ambient-waves-gerstner-and-fft) offshore, the break mask of
[Shallow water](#shallow-water-shoaling-refraction-and-breakers) inshore, and turbulence
intensity in rivers — so the classes stay consistent with each other and with the wave that made
them.

**Aerated water changes the water's own optics, not just its albedo.** Where bubble density is
high, scattering swamps absorption: the body colour washes out toward white, transparency
collapses, and the depth-based colour ramp of
[Water-body optical identity](#water-body-optical-identity-where-sigma-actually-comes-from)
stops applying. Practically, blend `sigma`/scatter toward a high-albedo, high-scattering,
short-mean-free-path set as the aeration mask rises, and drive Fresnel to zero underneath. Foam
that still reflects the sky is an instant tell.

**Backlit crests.** A thin, sunlit-from-behind wave face glows green-turquoise because light is
transmitted through a thin water sheet carrying suspended scatterers. The standard cheap
approximation is view-dependent translucency (Barré-Brisebois & Bouchard, GDC 2011 / GPU Pro 2 —
shipped in Frostbite): compute transmitted light from `dot(V, −L)` distorted along the normal, and
scale it by a **thickness** proxy. For waves the thickness proxy is free: crest height above the
mean plane, or the inverse of the wave's local thickness at the crest. Gate it on the sun being
*behind* the wave relative to the camera, or every crest glows all day.

**Waterfalls are a construct, and the physics tells you how to build it.** A falling sheet does
not stay a sheet: aerodynamic waves grow on its surface until the sheet ruptures, fragments
contract into ligaments (Rayleigh–Taylor), and the ligaments break into droplets by the
**Rayleigh–Plateau** instability, whose most unstable mode for an inviscid column is around
**9× the radius**. So the correct visual cascade down a fall is
**coherent sheet → perforated/streaky sheet → ligaments → droplets and mist**, and the transition
distance shortens as discharge falls. Build a fall as that progression, not as one scrolling
texture:

```
lip        : coherent sheet - the nappe. Scrolling normals, high transparency, sharp edge
upper fall : sheet perforating - streaks and holes appear, foam mask climbs
lower fall : ligaments/droplets - switch to particle-dominated, sheet mesh fades out
impact     : maximum aeration - opaque white, ~50% albedo, Fresnel killed
plunge pool: bubble plume rising, foam disc advecting outward and decaying to ~18%
mist       : lit volumetric column; wets surrounding rock (13) and can carry a rainbow
```

All of it *steered* by the generator's exported discharge and drop height, none of it in the
export. Two consequences follow: a tall fall must be **particle-dominated at the bottom and
sheet-dominated at the top** (a single sheet mesh all the way down is the classic wet-ribbon
look), and the mist plume is a **lit participating medium**, not a billboard disc — it is the
element that grounds the fall in the scene, because it scatters sunlight and shadows the rock
behind it. The recurring structural defect remains the one in
[Rivers](#rivers-flow-driven-surfaces): a fall authored where the flow field does not support it.

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

## Man-made water: pools, tanks and channels

A swimming pool, a fountain basin, a lock chamber, a reservoir, an irrigation canal, an industrial
tank. These bodies never arrive from the generation handoff — terrain-architect *classifies*
`bodyType` from the fill mask and flow accumulation (its `03`), and no classifier turns a gunite
shell into a lake. They arrive **authored**, exactly as the engine-native water bodies do
([Bodies are splines](#bodies-are-splines-and-the-splines-carve-the-terrain)), the enum extends
renderer-side, and nearly every default in this chapter is wrong for them — structurally, not by a
tuning margin. The contracts hold (depth field, `liquidBody` optics, pass ordering, one wave
evaluator); most of the bands gate off.

```
bodyType += pool | basin | tank | canal | reservoir     # authored; never classified
```

| Machinery | Natural body | Man-made body |
|---|---|---|
| Shore distance, foam band, wet sand | The strongest shoreline cue there is | **Degenerate** — the waterline is a hard edge on a vertical wall. Gate shoreline foam and wet sand off; a static wet band and a meniscus on wall and coping replace them |
| Shoaling, refraction, breakers, run-up | Tier 2 shore band, the production default | **Off.** No sloping bed, no surf zone. A pool with breakers is an ungated body type, not a storm |
| Whitecaps (Jacobian foam) | Wind-driven, from Force 3 up | **Off.** No fetch reaches the breaking threshold across 10 m of water |
| Ambient wind-wave spectrum | Fetch-limited wind sea, or full swell | Fetch is *metres*, so the wind-driven part collapses onto the capillary–gravity floor ([Calm water](#calm-water-the-low-energy-regime)) — the **smallest** term on a sheltered pool, not the model |
| Wave sources | Wind, swell, current | **The return jets, then the walls** — a driven, reverberant basin response, not a spectrum: [The wave field is a driven basin](#the-wave-field-is-a-driven-basin-not-a-spectrum) |
| Sim-patch edge contract | Fade to zero over the outer ~15% | **Inverted** — the domain edge is a real wall. Reflect it, and keep the fade only where a sim domain ends inside a larger body |
| Depth ramp | The single strongest realism cue water has | 1–3 m of range, almost no dynamic range to spend. What reads instead is the wall/floor junction and the refracted straight-line grid |
| Reflection | Planar is a hero-body-only luxury | One small flat body: **planar reflection is genuinely affordable**, and SSR behaves unusually well because the reflected geometry is close and on screen |
| Caustics | A detail on the bed | **The dominant visual event** |
| Single-depth-layer limit | A real architectural constraint | A non-issue — one surface, nothing stacked |

The net effect is an inverted budget. On an ocean you spend on the surface and economize on the
bottom; on a pool you spend on the bottom — caustics, bed albedo, refraction fidelity — and the
surface is a nearly flat sheet with ripples on it.

### The wave field is a driven basin, not a spectrum

A directional wind spectrum on a sheltered pool is plausible and wrong in a way a photograph
exposes immediately. Pool water is organised by the plumbing and the walls.

- **The source is the filtration return; the walls send it all back.** The inlet jets inject a
  narrow band of gravity waves — order 10–30 cm — continuously from a fixed point whenever the pump
  runs, with swimmer transients on top; wind over metres of fetch is the smallest contributor. A
  tiled wall is a near-total reflector at these wavelengths (argued from the physics; no reflection
  coefficient was measured), so the result is a **reverberant basin response**: the field is **not
  statistically homogeneous**, the pattern is **stationary in the basin frame** — the same
  structure sits in the same place every day — and a train can be traced from the inlet to the far
  wall and back.
- **Damping sorts the field into two bands, and forcing sorts it the same way.** Deep-water viscous
  decay `α = 2νk²` (Lamb) against the group speed gives an e-folding distance `c_g/α` of ~90 m at
  16.5 cm — eleven lengths of an 8 m pool — but only ~2.1 m at 3 cm, which dies before the far wall.
  A surface film (sunscreen, body oils) shortens the short end by roughly 3–9× again — the
  inextensible-film limit, `α ≈ 0.35·k·√(νω)` against the clean-surface `2νk²`, with a prefactor
  that is unconfirmed (`P/?`), so treat the factor as indicative — and leaves the long end alone,
  because long waves stretch the film and see a clean surface. Wind meanwhile cannot force long
  waves at metre-scale fetch, so forcing limit and damping limit land in the same place: a pool
  surface is **two superposed fields, not one spectrum**.

| | Long band (≳10 cm) | Short band (≲5 cm) |
|---|---|---|
| Source | Return jets, swimmers — a fixed point | Wind, over the whole surface |
| Structure | Coherent, reverberant, basin-modal, stationary in the basin frame | Incoherent, statistically homogeneous |
| Reach | Rings around the basin many times | Dies in ~2 m; never reflects |
| Carries | The visible undulation, the trackable motion | Most of the slope: sparkle, fine caustic texture |
| Local shelter | **Unaffected** — passes straight through a lee | **Strongly modulated** — this is what a lee removes |

  Shading sees slope, and `slope = 2πa/λ`, so equal slope costs amplitude proportional to
  wavelength: a 1.5 mm ripple at 5 cm out-slopes a 3 mm jet wave at 16.5 cm (≈0.19 against ≈0.11).
  **Never budget the two bands by wave height** — and never let the short band own the bed pattern
  either: by the focusing number `F = 0.25·d·s·k` ([The focusing
  number](#the-focusing-number-which-regime-the-bed-is-in)) it sits past focus over a 1–3 m floor
  (`F ≈ 3` for a 3 cm ripple at 1.40 m) and writes an unresolvable wash, while the long band lands
  near `F ≈ 0.4` and writes the readable cell net.
- **Shelter modulates the short band only.** In the wind shadow of a sail or a hedge the surface
  goes glassy *but keeps undulating*: the lee kills the wind band while the jet waves cross it
  untouched. Multiply a lee mask into the whole field and long waves stop dead at the shadow line,
  which no water does.

```hlsl
// Pool surface in a raster pass: two band fetches, one baked-wake fetch, one mask.
float3 nLong   = BasinNormal(uv, t);         // >=10 cm: FFT cascade (flat spread) + image trains
float3 nShort  = WindRippleNormal(uv, t);    // <=5 cm: the existing short-wave detail set
float  shelter = SampleShelter(uv);          // painted/baked lee mask; 1 = exposed, 0 = full lee

// Combine as SLOPES, not normals: slopes add, and the short band is the slope budget.
float2 sLong   = nLong.xy  / max(nLong.z,  1e-4);
float2 sShort  = nShort.xy / max(nShort.z, 1e-4);

// The jet wake stands still in the basin frame, so it is a bake: one fetch in the fitting's own
// frame. .xy = slope, .z = the forcing envelope that also drives near-field roughness.
float3 wake    = WakeAtlas.SampleLevel(smp, WakeUV(worldPos, fitting), 0).xyz;
float3 N       = normalize(float3(-(sLong + shelter * sShort + wake.xy), 1));

// Same masks into the filtered-variance path, or distance filtering re-adds the sparkle the lee
// removed. Slope scales linearly with a mask, so variance scales with its square.
float mssShort = shelter * shelter * mssShortBase + wake.z * wake.z * mssJetBase;
```

- **A return jet, taken from the jet and not from an authored lobe.** A submerged round jet spreads
  linearly and decays as `1/s`, and cannot force the surface until it has spread far enough to reach
  it, so the disturbed patch is elongated along the aim and **starts downstream of the fitting
  rather than at it** — ~0.9 m downstream for a 20 mm restricted eyeball at ~13 m³/h set 15 cm deep,
  half-length ~0.7 m, local rms slope roughly **twice** the far field (a ratio, not an absolute: the
  surface-deformation scaling `η ~ C·u'²/g` carries an O(1) constant that is genuinely unknown,
  `?`). Its wake is a **narrow downstream band, not rings and not a Kelvin wedge**: the drift it
  drives, of order 1 m/s (0.8 bar through that eyeball is an 11.6 m/s jet), is strongly
  supercritical against water's minimum phase speed of 0.231 m/s
  ([Calm water](#calm-water-the-low-energy-regime)), so nothing propagates upstream — a ring system
  needs a source at rest in still water — and because energy travels with the current
  (`c_g ≤ U/2`) the fan is only **±19°** about the axis. The ship case, source moving through still
  water, is the mirror image and its wedge does not transfer. Three checks a reference photograph
  gives free: the pattern is **steady** in the pool frame (one that animates outward is a wrong
  model), its crest arcs are centred a metre or so **out in the water** because the forcing region
  is a stretch of the axis rather than the outlet, and what it launches fades out around **3 m in an
  8 m pool**. Forcing scales as `(U0·d)²`, so what you calibrate against an observed roughness
  contrast is the **flow rate through the fitting**, not a shape exponent — and none of it runs in
  the frame, it sizes the bake below.
- **What ships at frame rate.** Every band maps onto an evaluator this chapter already has, so
  nothing new runs in the frame. The **diffuse tail** is random-phase and isotropic — an FFT
  cascade with a flat directional spread, or a short Gerstner sum with scattered directions. The
  **early wall reflections** are the direct train plus its first-order mirror images across the
  walls (`1/√r` spreading, damping as above) — a handful of extra trains in the same sum; pushing
  the image count up instead buys a coherent lattice no basin shows and costs more. The **wind
  band** is the existing short-wave detail set. The **jet wake** is steady in the basin frame, so
  solve it once offline per fitting and bake slope plus forcing envelope into a small texture in
  the fitting's frame — one fetch at runtime, no solver, and it rotates and tiles with the fitting.
  The **lee** is a painted or baked mask. A height-field sim patch with reflecting walls and a
  driven source cell is the option that buys swimmer transients, at the usual patch cost
  ([Interactive simulation patches](#interactive-simulation-patches)); the steady field does not
  need it. The bed pattern then goes through the same caustics ladder as any other body
  ([The tier ladder](#the-tier-ladder)) — the driven basin changes which band feeds it, not the
  technique. And the tail's near-isotropy is a review test in its own right: a wind sea writes
  streaky, direction-aligned caustics; a reverberant tail writes isotropic cells.

### Pool optics: the colour is the bottom, not the water

The optical identity machinery in this chapter is built from oceanography — Jerlov types,
Forel-Ule index, chlorophyll and CDOM — and **a treated pool belongs to none of those classes**.
Filtration and flocculation remove precisely the particles that scatter: `b_b → ≈ 0`, `c → a`, and
Secchi depth exceeds the body depth by design. With `b_b ≈ 0` the **scatter-colour term is
essentially zero** — a pool has no body colour of its own, and a shader that derives its colour
from `scatterColor` is structurally incapable of rendering one.

The colour is **bottom albedo attenuated over the down-and-back path**. For a near-vertical view of
a 1.5 m floor the light crosses ~3.0 m of water, and pure-water absorption at this chapter's RGB
sample points ([Water-body optical
identity](#water-body-optical-identity-where-sigma-actually-comes-from)) does the rest:

```
depth 1.5 m -> round trip 3.0 m,  transmittance = exp(-a * 3.0)
  a(610 nm) = 0.25   m^-1  ->  0.47    red     more than halved
  a(550 nm) = 0.056  m^-1  ->  0.85    green   barely touched
  a(450 nm) = 0.0092 m^-1  ->  0.97    blue    untouched
```

A white liner at ~0.8 albedo therefore returns roughly `(0.38, 0.68, 0.78)` before any sky
reflection is composited on top: bright, cyan-leaning, and **desaturated** — because with `b_b ≈ 0`
the column is a pure Beer-Lambert filter that can only subtract. The deeply saturated turquoise
most people picture comes from a **blue liner**: a mid-blue PVC at roughly `(0.24, 0.54, 0.70)`
returns about `(0.11, 0.46, 0.68)`, far more saturated and about a third darker. Start a modern
domestic pool from a blue liner, not white plaster, and let the water *darken* it rather than
colour it; reaching for a saturation or tint control instead is compensating for a bottom albedo
that was never authored. Two consequences, both checkable against reference photography: **change
the liner and the water changes completely** (sand → green-teal, the fashionable dark-grey liner →
near-black, since nothing fills the column and only the Fresnel sky survives — a pool that looks
the same over every liner has no bottom-albedo term), and **colour is nearly depth-independent
within one pool**, since across 1–3 m blue hardly moves, green moves little, and red carries almost
all of the change. A strong hue shift across a pool floor is an artifact, not a depth cue.

### The rest of the man-made checklist

- **Straight lines are the fidelity test.** Tiled walls and rectangular coping hand the viewer a
  known-straight reference that the refracted surface visibly bends. It is also where the depth
  reject in [Shading and optics](#shading-and-optics) earns its place: deck, coping and everything
  standing on them sit *directly* adjacent to the water in screen space, so an unrejected
  refraction sample smears them into the pool every frame.
- **The waterline is geometry, not a fade.** On a vertical wall the shore-distance field carries no
  information. Author the band: wet tile below the line, a meniscus with its own small specular
  lift at it, a damp gradient above it from splash, and the static scale line at the tile course.
- **Inflows are the flow field.** Return jets and skimmer draw are the only steady flow, and they
  are small and local — author them as sim-patch injections rather than exporting a flow raster for
  a 10 m body.
- **The gameplay surface is trivially correct here** — flat datum plus a centimetre of ripple — so
  there is no excuse for the swim-volume mismatch in [Pitfalls](#pitfalls).

## Shading and optics

BRDF math routes to physically-based-rendering; what this skill owns is the *composition* — which
signals feed the water shader and where each comes from. The water pixel is:

```
color = lerp(refracted_underwater, reflected_environment, Fresnel(NdotV))
      + foam + sun_glint
```

- **Fresnel** is the blend, and its `F0` comes from the body's index of refraction — a
  **per-body** value, not a constant. Fresh water is IOR 1.33 → `F0 = ((1.33−1)/(1.33+1))² ≈ 0.02`,
  **half** the generic dielectric default of 0.04 (which is IOR 1.5, glass/plastic); ship the
  default and calm water reads too reflective and faintly plastic even before the
  distance-filtering problems compound it. But natural liquids span IOR ~1.31–1.47 (ice → seawater
  → brine → oil), i.e. `F0` from ~0.018 to ~0.036 — a **2× reflectance spread**, so a brine pool
  reflects visibly more than the lake beside it. Take `ior` from the `liquidBody` descriptor
  (terrain-architect `28`) rather than hardcoding 1.33. Use the roughness-aware
  form of [Distance and filtering](#distance-and-filtering-why-far-water-turns-to-plastic) at
  grazing angles; the `F0 = ((n−1)/(n+1))²` derivation and the amplitude-Fresnel details route to
  physically-based-rendering.
- **Reflection** is a fallback hierarchy, never a single source: SSR first (correct for local
  objects), planar reflection for the hero body when budget allows (see
  [Transparency & pass ordering](#transparency--pass-ordering)), distant cubemap/sky capture
  last. Blend by SSR confidence — SSR *will* drop out at grazing angles and screen edges (the
  reflected ray leaves the screen exactly where water is most reflective), and the fallback must
  match the SSR result in brightness or the dropout draws a line. Grazing-angle Fresnel makes
  water the most brutal SSR-consistency test in the frame.
- **Refraction**: the normal-driven UV distortion below is a **screen-space approximation of
  Snell's-law bending** at the surface (`n_air·sinθ_i = n_water·sinθ_t`, water IOR ≈ 1.33) — it
  offsets the lookup by the surface normal rather than tracing the bent ray, which is why it is
  cheap and why it cannot handle a surface steep enough to see *around* an obstacle. Sample the
  scene-color copy, clamped by view depth so near-surface distortion doesn't grab pixels metres
  away. The canonical artifact:
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
- **Caustics** are the light that got *through* the surface and focused on the bed. They carry
  their own pass, tier ladder and masking contract — see
  [Caustics](#caustics-the-other-half-of-the-light-path). The one-line version: caustic brightness
  is the inverse Jacobian of the refracted-ray map, it multiplies the sun term rather than the
  albedo, and it is gated by sun visibility **at the surface**, not at the receiver.
- **Underwater camera state** is a real state machine, not a fog tweak: on submersion switch to
  underwater fog (aggressive, chromatic, from the same `sigma`), render the surface from below
  (total internal reflection outside **Snell's window** — for water→air the critical angle is
  `arcsin(1/1.33) ≈ 48.6°`, so the whole above-water world compresses into a ~97°-wide bright
  circle overhead and everything outside it mirrors the bottom; a cheap, high-value cue), and
  handle the half-submerged frame explicitly. The waterline crossing is
  either a hard cut (acceptable, hide with a droplet/meniscus overlay for a frame or two) or a
  true split-screen meniscus (render both states, mask by the wave-displaced waterline in screen
  space — expensive, hero-camera only). The untreated version — one frame of neither-state
  garbage at the crossing — is a certified review catch.

### Water-body optical identity: where `sigma` actually comes from

Most water shaders expose `sigma` and a scatter colour as art-directed swatches. They are
measurable physical quantities, and picking them from oceanography instead of from a colour
picker is the cheapest realism win in the whole chapter — it is what separates "blue-tinted
glass" from *this specific water*. The generation-side producer of this descriptor is
terrain-architect's liquid property bundle (its `28`, exported as `liquidBody[i]` in its
`08`/`27` contract) — when the pipeline ships it, consume it rather than re-authoring; this
section is the theory for reviewing those values and the fallback for pipelines that lack them.

**Pure water is blue for a spectroscopic reason.** Its visible absorption is the high-order
overtone band of the O–H stretch — vibrational, not electronic — which is why absorption is
minimal in the blue and climbs steeply into the red. Pope & Fry's measurements put the minimum
at **0.0044 m⁻¹ at 418 nm**, against **0.62 m⁻¹ at 700 nm**: red is ~140× more strongly absorbed
than blue-violet. In practice red is gone by ~5 m, orange by ~10 m, yellow by ~20 m, green by
~40 m. That single ratio is the entire shallow→deep colour ramp, and it is *not* sky reflection.

```
sigma_RGB ~= (a + b_b) evaluated at ~610 / ~550 / ~450 nm
a_water   ~= (0.25, 0.056, 0.0092) m^-1     # pure water at 610/550/450 nm, Pope & Fry 1997
#   the absolute minimum is 0.0044 m^-1 at 418 nm - deep violet, below a typical B channel
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

**Check reachability before budgeting for glitter at all.** A glint needs the surface to supply the
normal that bisects sun and eye, and the surface can only supply what its slope distribution
contains. One half-vector settles it: `tilt = angle(normalize(L + V), up)`, read against the rms
slope `s`.

```
tilt < ~2s   a glitter path -- the classic shimmering road
tilt ~ 3s    sparse isolated glints; a 2D Gaussian slope field leaves ~1% of the
             surface above 3 sigma in magnitude, and far less pointing the right way
tilt > ~4s   nothing. What the water shows there is sky reflection, not sun
```

**At low sun the test is brutally azimuth-sensitive — and that makes it invertible.** With the sun
low, both `L` and `V` are near-horizontal, so an azimuth miss translates almost fully into required
tilt. Holding the eye at the mirror elevation, an 18.75° azimuth error costs **23° of tilt at a 21°
sun, 7.8° at 50°, and 3.4° at 70°**: low-sun sparkle is pinned inside a narrow azimuth wedge, while
a high sun forgives a lot. Run the test backwards and a photograph becomes a **measurement**. The
geometry fixes the tilt the surface must supply, so the mere presence of sparkle puts a floor under
the local rms slope:

```
required tilt 17.8 deg (measured sun + measured camera bearing)
  s = 0.055  ->  5.7 sigma  ->  0.000 % of the surface  -> nothing visible
  s = 0.090  ->  3.5 sigma  ->  0.25  %                 -> a sparse scatter of glints
  s = 0.110  ->  2.8 sigma  ->  1.8   %                 -> a well-populated patch
```

So a sparkle patch beside glassy water is not a lighting accident: it localizes water roughly twice
as rough as its surroundings, which is what a jet-stirred or gust-ruffled patch actually is. Use it
as a calibration handle rather than tuning sparkle by eye.

The common trap is a **low sun with a high camera**, because the two constraints multiply: the
mirror elevation equals the sun's, *and* the observer must be near the anti-solar azimuth. A 21°
sun viewed from a balcony 40° up and 70° off that azimuth needs ~47° of tilt — fifteen sigma, which
is not "rare" but *never*. Move the same camera into the anti-solar azimuth and the requirement
drops to ~9.5°, about 3 sigma, and sparse glints appear. Two payoffs: do not spend a glitter tier
on a shot that cannot show one, and when matching reference photography, the **presence, sparsity
or absence of sparkle reads back the camera's azimuth relative to the sun** — a free forensic
check on a plate before you start tuning anything.

**Glitter is a filter applied to the wave field, not a texture applied to the water.** Note what
separates tiers 1 and 2 from tier 3: the first two are *functions of the slope field*, the third
is not. That is the whole distinction, and it is the same structural argument the Voronoi caustic
fails ([Caustics](#caustics-the-other-half-of-the-light-path)) — applied above the surface instead
of below it. A glint appears exactly where the surface normal is the half-vector between sun and
eye, which is a **level set of the slope field**: the sparkle sits on crest and trough lines, not
at independent random points. Four things follow, and each is a review test:

1. **It is trackable.** Individual glints ride specific crests and travel with them. Over a second
   of footage a viewer can follow one crest across the glitter path. Cell noise has no crests to
   follow. Freeze a frame and the fake and the real thing look alike — which is precisely why a
   noise-perturbed specular survives a screenshot review and dies on video. **The test for glitter
   is temporal, not spatial**; judge it on a pan, never on a still.
2. **It is dispersive, and that is the cheapest tell in the frame.** The field carries many scales
   at once and each moves at its own speed: `c = ω/k` from `ω² = (gk + (σ/ρ)k³)·tanh(kh)`, with the
   minimum at 23.1 cm/s / 1.73 cm ([Calm water](#calm-water-the-low-energy-regime)) and rising in
   *both* directions from there. Across a pool-sized band — say 3 cm to 55 cm, entirely on the
   gravity side of that minimum — the long components outrun the short ones by roughly **4:1**
   (~0.25 m/s against ~0.93 m/s), so the eye sees fine ripples crawling while a longer swell
   sweeps through them. A scrolled texture — noise, Voronoi, authored caustic sheet — advects
   every scale at one velocity by construction and can never show this. Watch two scales at once
   for two seconds; that is the entire test.
3. **It is phase-locked to the caustics.** One slope field, two consumers: the same surface
   curvature that makes the glint above the water makes the fold below it. Drive glitter from a
   noise texture and the sparkle stops sitting above the bright line it caused — a mismatch that
   reads as wrong long before anyone can say why. This is the one-evaluator rule (`19`) applied to
   optics rather than to physics.
4. **The "cells" are interference, not cells.** With a single wave train the glitter is a set of
   parallel bands along the crests and the bed caustic is parallel stripes. Add trains from other
   directions and both become a mosaic that photographs like a cell tessellation. Nothing turned
   into noise — the components are all still there, still separable, still individually
   followable. Reading that mosaic as "a Voronoi pattern" and reaching for cell noise inverts
   cause and effect: the tessellated *look* is the output of a directional wave spectrum, and cell
   noise reproduces the look while discarding everything that generated it.

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

## Caustics: the other half of the light path

Sun glitter is the light that bounced *off* the surface; caustics are the same focusing mechanism
applied to the light that went *through* it. On open ocean they are a detail nobody looks at. On
any clear shallow body — a reef flat, a river bed, a pool — they are the most recognizable thing
water does, and the budget inverts accordingly ([Man-made water](#man-made-water-pools-tanks-and-channels)).

**The physics, in one equation.** Refraction maps each surface point `p` to the point `q(p)` it
illuminates on the bed. Flux is conserved along the ray tube, so receiver brightness is the
inverse of how much that map stretches area:

```
i      = -L                                    # propagation direction of the sunlight, z up
t(p)   = refract(i, n(p), 1.0/ior)             # Snell at the surface;  t.z < 0, heading down
q(p)   = p.xy + t(p).xy * (d(p) / -t(p).z)     # where that ray meets the bed, d = depth below p
E(q)   = E_sun / |det( dq/dp )|                # the caustic
```

Two consequences fall straight out, and both are load-bearing:

- **Caustics are a curvature quantity, not a normal quantity.** `dq/dp` contains `dn/dp` — the
  *second* derivative of the wave field, where surface shading is driven by the first. That is
  why a normal map with no coherent height behind it produces caustics that visibly do not belong
  to the surface above them, and why a normal map filtered one mip too far yields caustics that
  are far too smooth while the surface itself still looks fine.
- **The bright lines are where `det dq/dp` passes through zero** — the fold set of the map. This
  is catastrophe optics, and it fixes the *shape* of a real caustic network: for a map from a
  surface to a plane the only structurally stable singularities are **folds** (curves) and
  **cusps** (isolated points where two fold branches meet tangentially). A caustic network is
  therefore smooth bright curves that close, run off, or terminate in cusps. It is not a cell
  tessellation — which is the specific reason the Voronoi fake reads wrong.

### The focusing number: which regime the bed is in

Whether a body shows a crisp caustic net, a soft wash, or nothing much is not a matter of taste,
and it has a one-line estimate. A surface slope `s` turns the refracted ray by `s·(1 − 1/n)`, so at
depth `d` the receiver point moves by `d·s·(1 − 1/n)`; focusing happens when that displacement's
*gradient* reaches unity. With `k` the dominant wavenumber and `s` the rms slope:

```
F = d * (1 - 1/n) * s * k        # water: 1 - 1/1.333 = 0.25, so F ~= 0.25 * d * s * k
    F << 1   below focus  -> a soft, wide brightness modulation; no network
    F ~= 1   at focus     -> the crisp net, folds and cusps resolved
    F >> 1   past focus   -> branches overlap into an unresolvable wash
```

(Near-normal sun; at low sun an obliquity factor enters and the pattern stretches along the sun
azimuth.) Three practical readings:

- **Cell size on the receiver is of the order of the dominant wavelength**, so measuring caustic
  cells against a photograph is a direct readout of the wave field that produced them — a cheap
  calibration check when matching reference.
- **Lengthening the waves at fixed slope moves you *down* the ladder**, because `k` falls. "Lower
  the wave frequency" alone does not give bigger caustics; it gives fainter ones.
- **Holding the look while lengthening the waves costs `s ∝ λ`, i.e. amplitude `a = s/k ∝ λ²`.**
  Big crisp caustics require genuinely big waves — going from 16 cm to 50 cm at constant `F` is a
  ~10× rise in amplitude. A calm body cannot have a large-celled sharp net, and art direction that
  asks for one is asking for a contradiction.

### The tier ladder

| Tier | Mechanism | Verdict |
|---|---|---|
| **0 · Authored texture** | One or two scrolling caustic textures at different scales and speeds to hide the loop | What most engines' starter water ships. Wrong in one specific and visible way: uncorrelated with the surface above it — when the water goes calm, the caustics keep churning |
| **1 · Worley / Voronoi (`F2−F1`)** | Cellular noise, two octaves, animated feature points, small per-channel offset | The community default, and what most people mean by "a caustics shader". Cheap, passable in motion at distance, structurally wrong — below |
| **2 · Caustic map from the real wave field** | Rasterize the refracted receiver positions from the light's view and accumulate; folds appear for free wherever several rays land in one texel | **The recommended default.** Shah, Konttinen & Pattanaik's caustics mapping and Wyman & Davis's image-space technique are the canonical formulations; GPU Gems 1 ch. 2 is the water-specific version. Costs one light-view pass over the wave grid |
| **3 · Ray-traced / photon-mapped** | Photons traced through the surface (DXR), splatted or resampled | Hero water on RT hardware. Correct including multi-branch folds and the secondary caustics from total internal reflection. Theory routes to physically-based-rendering (`caustics.md`) |

**Why it resembles a caustic at all.** The resemblance is not a coincidence, and naming it tells
you exactly where the approximation stops. Propagate a wavefront and two different singular sets
appear: the **focal set**, where neighbouring rays cross and the ray-map Jacobian degenerates, and
the **cut locus**, where fronts of equal travel time arrive at a point from two directions. A
caustic is the focal set. `F2−F1` is the gap between the nearest and second-nearest seed distance,
so its ridge set is precisely the **cut locus** of a family of circular fronts expanding from those
seeds — and circular fronts never focus (the evolute of a circle is a single point), so a cell-noise
field contains no focal set whatsoever. Both are bright-line networks born of front propagation;
that is the whole of the similarity. The junction difference then follows by classification rather
than by tuning: a planar cut locus generically meets in **triple junctions**, a focal set
generically meets in **cusps**.

**Which is why the approximation does not converge.** Adding octaves, jittering the seeds harder,
or animating the feature points moves the field around *within the family of cut loci*; no amount
of refinement produces a focal set. Compare the physical path, where adding wave components makes
the fold network strictly more correct because they enter the same Jacobian. Voronoi is a
legitimate approximation of the **appearance** and not a low-order approximation of the
**mechanism** — budget it as a stand-in with a fixed quality ceiling, never as a base to improve
on. If the shot needs better caustics than the fake gives, the move is to change tier, not to
add octaves.

**What separates it on screen — and how to ship it anyway.** Worley `F2−F1` gives a
network of bright lines around dark cells, which is why it convinces on a still frame. Three
things separate it from the real thing, all of them consequences of the fold/cusp classification:

1. **The wrong junctions.** A Voronoi edge network meets in *triple junctions* — three edges at a
   vertex. A caustic network has none: fold curves meet only in **cusps**, where two branches join
   tangentially, and fold curves may also simply end. The eye reads the difference as "cracked
   glass" rather than "focused light" long before it can name it.
2. **Uniform brightness along an edge.** Real fold lines vary strongly in intensity along their
   length and blow out at cusps, because `det dq/dp` varies along the fold. Cell noise has no such
   structure — every edge is as bright as every other.
3. **No coupling to anything.** The pattern knows nothing of wind direction, wave anisotropy, or
   depth. The most visible symptom is the one Tier 0 shares: **on mirror-calm water it keeps
   animating**, where the correct answer is that a flat surface has a constant Jacobian and
   therefore produces no caustic structure at all — just uniform light on the bed.

If the budget demands it, ship it — but label it a fake in the material, scale cell size with
depth so it respects at least that one law, and drive its animation amplitude from the wave
amplitude so calm water goes flat.

### The masking contract — four gates, and the third is the one that gets skipped

```hlsl
float3 caustic = SampleCausticMap(worldPos, time) * causticStrength;
caustic *= 1.0 - saturate(verticalDepth / causticFadeDepth);  // 1. depth fade
caustic *= exp(-sigmaPerBody * lightPathLength);              // 2. extinction along the LIGHT path
caustic *= SunShadow(surfaceEntryPoint);                      // 3. sun must reach the SURFACE
sunLighting += caustic;                                       // 4. irradiance, never albedo
```

1. **Depth fade on `verticalDepth`**, not on `rayDistance` — the distinction drawn in
   [Shading and optics](#shading-and-optics). Two mechanisms converge on the same fade: extinction,
   and the fact that the fold pattern spreads and overlaps into an unresolvable wash past the
   focal depth.
2. **Extinction along the *light* path**, which is a different distance from the camera path
   already computed for refraction: `verticalDepth / cos(theta_t)` from surface to bed, with
   `theta_t` the refracted sun angle. Reuse `rayDistance` here and caustics fade with camera angle
   instead of sun angle — subtly wrong in every frame, and obviously wrong the moment the camera
   moves while the sun does not.
3. **Sun visibility sampled at the surface entry point, not at the receiver.** The occluder — a
   shade sail, a parasol, a diving board, a tree, the pool wall at low sun — blocks the ray
   *before* it enters the water, so the shadow test belongs to `p`, not `q`. Sampling the cascaded
   shadow map at the receiver is the near-miss version: near-correct at high sun, visibly wrong at
   low sun where entry and receiver points sit metres apart. Skipping the test altogether is the
   classic bug — **caustics crawling through the shadow on the bottom**. Nothing else in the frame
   announces "this is a scrolling texture" so loudly.
   **And the gate is fractional, not binary, whenever the occluder is fabric or foliage.** Shade
   cloth transmits roughly 15–30%, leaf canopy more, and the transmitted light is **diffuse** — so
   it lifts the shadowed water without putting any caustic structure into it. That splits this gate
   in two: the caustic term is still gated hard to zero, because no collimated beam survives the
   fabric, while an **ambient** term is added underneath it. Drive that term from the solid angle
   the panel subtends rather than from its footprint — a point two metres to the side still sees
   most of it, and a `1/(1 + (d/R)²)` falloff about the centroid is enough. Ship the binary
   version and the shadowed water goes far too dark, losing the cue that actually reads: under a
   shade sail the caustics vanish while the water stays luminous.
4. **Caustics are irradiance.** They multiply the sun's contribution to the receiver's BRDF; they
   are not added to albedo or to the final colour. Backwards, and they survive into shadow, into
   ambient-only lighting and into fog, and they stop responding to exposure.

**They fall on everything below the surface, not on the terrain.** Project in world space onto
whatever the pass finds under the water plane — bed, walls, steps, props, swimmers. A caustic
decal projected only onto the terrain heightfield leaves every object in the water conspicuously
unlit by the brightest thing in the scene. The above-water counterpart — surface-reflected light
dancing on a wall or a hull — is a second, weaker caustic on the reflection side, cheap from the
same map and a strong cue for pools and harbours.

**Sharpness has a physical floor, and it scales with depth.** The sun is not a point: its disc
subtends **0.53°**, and refraction compresses that cone on entry by `cos(theta_i)/(n·cos(theta_t))`
— near normal incidence simply `1/n`, so ≈ 0.53°/1.33 ≈ 0.40° ≈ 7.0 mrad. The penumbra grows
linearly with depth:

```
blur ~= 7.0e-3 * depth   ->   ~0.7 cm per metre of depth (near-normal sun)
  1.5 m pool floor -> ~1 cm      5 m -> ~3.5 cm      20 m reef -> ~14 cm
```

So caustic lines in a shallow pool are genuinely crisp and in deep water genuinely cannot be. A
caustic map still pin-sharp at 20 m is over-resolved; one blurred to 5 cm at 1.5 m has thrown the
effect away. Off-normal the compression is anisotropic, so a low sun stretches the blur along the
sun azimuth. This is the same 0.53° that sets the glitter path above the surface — above the water
it makes the highlight too *wide*, below it makes the caustic too *soft*.

**Dispersion is visible and cheap.** Water's index falls across the visible band — roughly 1.337
at 486 nm to 1.331 at 656 nm — so the three channels' fold sets do not coincide. The offset is
small, but it lands on the highest-contrast feature in the image, which is why real caustic edges
carry faint colour fringing. Refract per channel, or offset the sampled map per channel scaled
with depth, rather than shipping a grey caustic.

**Reusing the whitecap machinery — with one correction.** An FFT surface already computes a 2×2
Jacobian determinant per grid point for whitecap foam
([Aerated water](#aerated-water-foam-spray-and-whitewater)). That is **not** this Jacobian: the
foam one is the folding of the surface's own horizontal displacement map, this one is the folding
of the refracted-ray map onto the bed at depth `d`. Different maps, different fold sets. What
transfers is the machinery — the finite-difference stencil, the determinant, the clamp against the
`1/|det|` singularity, and the grid it runs on — so Tier 2 is usually a second dispatch over an
existing buffer rather than new infrastructure.

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
at 5 m/s (~0.1% coverage) and conspicuous by 15 m/s (~4%), so coverage must be driven by wind,
not by a constant.

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
7. **The dedicated single-layer pass**: a structural alternative to sorting rather than a rule
   about it, and the route Unreal's Single Layer Water takes. Draw the water surface as *opaque*
   geometry into the G-buffer, let
   it receive ordinary deferred lighting and shadows, then run one dedicated pass — after
   lighting, before regular translucency — that integrates a homogeneous participating medium
   between the surface and the opaque scene behind it. Sorting disappears (water is opaque
   geometry), the surface gets the full deferred light set for free, and the volume integration
   is one screen-space pass. The price is absolute: **one water depth layer per pixel**, so no
   water can be seen through water. Choose it when the world has one water surface per sightline
   and choose per-body sorted transparency when it does not; the decision is made at
   architecture time because it decides the shading model, not a material setting. Worked
   example, with its inputs and limits, in
   [Engine-native water](#engine-native-water-the-ue-water-plugin-read-as-architecture).

## Engine-native water: the UE Water plugin, read as architecture

Most teams inside a licensed engine never assemble the machinery above from parts — they inherit a
water system and then discover its contracts the hard way. Unreal's Water plugin is the most widely
deployed of these, and it is worth reading not as a feature list but as **one complete, shipped set
of answers to this chapter's questions**: its answers are mostly the ones recommended here, which
is corroboration; where they differ, the differences are load-bearing and teach something. Tier is
D/N throughout (engine docs and branded feature names), the facts below were checked against Epic's
documentation in 2026-08, and Water has moved substantially across releases — verify constants
against the version you ship on.

### The five parts, and this chapter's name for each

| Part | What it is | Read as |
|---|---|---|
| **Water Zone** | A *bounded* actor owning water rendering over a region: zone extent, render-target resolution, the water mesh, the info texture, optional local-only tessellation in a sliding window around the view (**?** whether and how several zones compose in one world is version-sensitive — check your release) | The water surface's **paging/streaming unit** — the camera-following overlay doctrine (`13`, `14`) applied to water |
| **Water Body actors** | Ocean / Lake / River / Island / Custom — splines (or a static mesh) with per-point metadata | `bodyType` plus per-body geometry: terrain-architect's `liquidBody` record (`28`), *authored* rather than generated |
| **Water mesh** | A quadtree of tiles over the zone, LOD as concentric rings around the camera, tiles morphing between levels | The world-space grid of [Surface geometry & LOD](#surface-geometry--lod) |
| **Water Info Texture** | One top-down capture of every water body **and the ground beneath them**, into a render-target array everything downstream samples | A runtime-rasterized version of the generator's handoff fields |
| **Single Layer Water** | A shading model: opaque surface in the base pass + a participating-medium pass beneath it | Option 7 of [Transparency & pass ordering](#transparency--pass-ordering) |

### The water mesh confirms the world-space grid — including the skirt

Documented behavior: the quadtree is traversed each frame to produce the visible tile set; tiles are
generated **only where a body's spline says water exists**, so open land costs nothing; each LOD is a
concentric ring around the camera, each successive ring carrying half the vertices of the one inside
it; and transitions **morph** rather than swap — Epic's wording is that four quads become a single
quad when dropping a level, or become sixteen when gaining one.

Defaults worth knowing as orders of magnitude: `Tile Size` 2400 uu (24 m) and `Extent in Tiles` 64
as a radius from the centre, so an untouched zone reaches roughly 1.5 km out and ~3 km across. That
number is the useful one: a *bounded* water zone must be sized against the game's view distance, and
the default is smaller than most open worlds need. `LODScale` sets where morphing begins;
`Tessellation Factor` sets vertex density inside a tile, and Epic notes lakes and oceans benefit most
from raising it — they are the bodies carrying real displacement.

The **Far Distance Mesh** is the infinite-ocean skirt, shipped, complete with the failure it exists
to fix: Epic states that an ocean body can hit its maximum extent "without completely filling the
level, leaving a gap between the horizon line and the water". It uses its own material slot — the
near field and the horizon ring are *different materials*, i.e. the three-bands doctrine expressed in
asset structure rather than as a shader branch. That is a pattern worth copying: when the far field
must be normal-map-only, make it a separate material so nobody accidentally ships displacement to
the horizon.

### The Water Info Texture: fuse the handoff into one sampleable field

The zone renders its water bodies top-down into a render target (a texture **array** in current
versions; the single-target form is deprecated). Knobs that reveal the design: a half-precision
toggle choosing **16 or 32 bits per channel**, a **capture Z offset** that places the capture plane
above the highest water in the zone, a **velocity blur radius** applied in a "finalize water info"
pass, and an explicit rebuild/update path. Everything downstream — the surface material, shore fade,
flow, gameplay queries — samples that one texture.

The capture is not water-only: the zone registers **ground actors** (landscape proxies intersecting
its bounds can be auto-included) and carries a `GroundZMin`, so the terrain beneath the water
participates. Epic's documentation does not spell out the channel layout, and this chapter
deliberately does not guess it — what the API surface establishes is that **water and ground are
captured into one field together**, which is the load-bearing architectural fact. Treat any specific
channel packing you read elsewhere as unverified.

Name the technique independently of the engine: **rasterize the water layer stack into one
view-independent field, and let every consumer read it.** The virtues are the ones `14` argues for —
one surface truth, one coordinate frame, no consumer re-deriving hydrology — and the fact that the
capture holds *ground* alongside water is terrain-architect's layer stack (`08`) made concrete: water
surface and solid top in one field, depth being their difference. Any engine can build this; a
project with no generator handoff can build it *from* its authored water and get most of the
chapter's depth-driven cues immediately.

One tension to resolve deliberately, because it cuts against
[the handoff](#the-handoff-seen-from-the-render-side): rasterizing bodies into a capture is
*re-deriving* depth and flow that a generator may already have shipped. Both can be true — the
capture is the right *delivery mechanism* (one field, one frame, sampled by everyone), and the
generator's fields are the right *content*. Where the handoff exists, the capture should be populated
from the exported depth, flow and shore-distance rather than recomputed from spline geometry, or the
two disagree at exactly the shoreline. Re-derivation is the fallback for pipelines with no generator,
not the default.

The costs are the price of any texture-shaped truth, and each is a review question:

- **Resolution is a whole-zone budget, spent uniformly.** One render-target resolution spans the
  entire zone extent, so a 5 m river inside a 4 km zone gets a handful of texels across its width:
  thin bodies alias, banks quantize, and near-bank flow blurs toward the ground value. There is no
  per-body detail level. Measure **texels across the narrowest body that matters**, not zone size —
  if the answer is under ~8, either the zone shrinks or the resolution rises.
- **Precision is a visible choice.** Half precision saves memory and spends Z accuracy in exactly
  the channels that drive shore fade and the wave-attenuation ramp — the two places the eye is
  already looking.
- **It is a cache, so it needs an invalidation contract** (`SKILL.md` Part 3). Moving a body, moving
  the zone, or editing the terrain beneath it must dirty the capture; a stale capture is a river
  whose flow field points at last frame's channel. Anything rendering outside the normal frame loop —
  offline movie-render paths are the documented case — has to force the update explicitly.

### Waves as a data asset, evaluated twice

Waves live in a **Water Waves** asset assigned per water body: a Gerstner generator with `Num Waves`
(default 16), min/max wavelength and amplitude with falloff curves, a dominant wind angle plus
angular spread, small/large-wave steepness, and a seed with a randomness term — a *parameterized
band*, not a sampled spectrum. That is squarely the Gerstner column of
[Ambient waves](#ambient-waves-gerstner-and-fft), with the documented consequences: visible
periodicity over open water and cost linear in wave count. Custom generators derive from the same
base class, which is where an FFT backend would go.

The load-bearing detail is the **second evaluation**: buoyancy re-evaluates the same Gerstner sum on
the CPU. That is the one-evaluator rule of `19` implemented for you — and the technique that makes it
affordable is worth stealing wholesale. The buoyancy component exposes **`N Points Per Frame`** and
**`N Frames Pause`**: probe points update round-robin across frames, and a body can idle for N frames
between updates. Wave queries are the CPU cost of floating anything, so amortizing them across frames
— with rigid-body integration carrying the object between updates — is how a fleet of floating props
stays affordable. Declare the latency it buys: a fast boat in a heavy sea is where it shows, and the
fix there is more points per frame for the hero body only, not a global raise.

### Single Layer Water: what the shipped shader interface asks for

The surface is drawn opaque/masked in the base pass; a dedicated pass **after deferred lighting and
before regular translucency** integrates a homogeneous participating medium beneath it. Its material
inputs are the physical ones: **scattering coefficients**, **absorption coefficients** — separately,
not one lumped extinction — a **phase-asymmetry term** (`PhaseG`, forward-scattering toward the sun
at positive values, isotropic at zero), and a colour-scale multiplier on what is seen through the
water; opacity blends the volume's response against the surface BRDF.

Two lessons, one of them a correction to the shorthand used earlier in this chapter:

- **The a/b split with a phase term is the right shader interface.** `sigma` as used in
  [Shading and optics](#shading-and-optics) is `a + b_b` already collapsed; the engine that shipped
  asks for `a` and `b` separately plus `g` — which is exactly what terrain-architect's `28` exports
  and this chapter's own optics section derives. Where the pipeline has that descriptor, wire
  absorption and scattering to their own inputs instead of pre-summing them: the sum discards the
  forward-scattering behaviour that separates a bright-but-murky silty river from a
  dark-but-transparent tannin one (the CDOM-darkens/sediment-brightens rule).
- **The single depth layer is an architectural limit, not a quality setting.** One water surface per
  pixel means no water seen through water: a river under a bridge over a lake, a fall crossing a
  pool, a pond on an island viewed at a grazing angle across the sea. Where the frame needs stacked
  bodies, this pass cannot express them and per-body sorted transparency is the fallback. Low-end
  paths drop the volume integration and revert to plain translucency, so the look must survive that
  degrade — check it on the lowest tier before art-directing on the highest.

### Bodies are splines, and the splines carve the terrain

Rivers are **open** splines with per-point depth, width and velocity, free to change elevation along
their length; lakes are **closed** loops whose points must all sit at **one elevation**; oceans are
closed loops around a shoreline; **Island** bodies exist only to push terrain above water; **Custom**
bodies are static meshes and — a real trap — do *not* carve terrain and do not use the water mesh.
Carving runs through a Landmass landscape brush writing into a Landscape **edit layer**: it is
non-destructive, and Epic documents that it only edits the landscape when edit layers are enabled —
which is the requirement behind the classic "my river hovers above the ground" symptom (the
symptom→cause link is this chapter's, not Epic's). The brush exposes a depth
curve multiplied by each spline point's depth, falloff by angle or by fixed width, an edge offset
producing a flat shore shelf, and blend modes (alpha / min / max / additive — the last preserving the
underlying detail rather than replacing it).

Three consequences matter on the rendering side. The Landscape-contract half — brush ordering, edit
layers, collision, and the fact that this brush family is not water-specific — is `03`; the
generation-side half is terrain-architect's `27`:

- **The bathymetry the water reads was authored by the same spline that drew the water.** Depth is
  self-consistent by construction, so shore fade, shoaling and the colour ramp cannot disagree with
  the mesh. This is why engine-native workflows get a plausible shoreline nearly for free, and why a
  generator-driven pipeline must be at least as careful: if the depth field and the water surface
  come from different passes, they can drift.
- **A carve is a terrain edit with an owner.** Keeping it in its own edit layer is `07`/`13`'s
  overlay doctrine applied to the *source* data rather than the runtime composite — the same reason
  RVT must not bake transient state.
- **Exclusion volumes carve the volume, not the surface** — a region where gameplay behaves as
  though it were not underwater. That is the one thing a 2.5D depth field structurally cannot
  express (an air pocket under a lake, a dry cave beneath a river), and any water contract shipping
  only a depth raster needs the same escape hatch.

River-to-lake and river-to-ocean junctions get dedicated **transition materials**. Generalize it: the
boundary between two water bodies is a contract like a LOD seam, and it needs a declared owner and
blend — surface height, flow direction, foam phase and optics all change across it, and left
unhandled it reads as two shaders arguing along a line.

### What to check when inheriting a water system

1. Does the zone's extent cover the **worst view** in the game, or does the water end inside the
   draw distance? If it ends, is the far ring present and does it share the atmosphere state (`10`)?
2. **Texels across the narrowest body that matters** in the shared info capture — not zone size.
3. Does the physics/gameplay wave query use the **same evaluator** as the surface, and at what
   amortization latency?
4. Is there **stacked water** anywhere in the level? Find it before an artist does; a single-layer
   path cannot draw it.
5. Are terrain carves in their **own edit layer**, and does re-running generation preserve them?
6. Does the underwater state key off collision that the body actually generates?
7. Is the capture **invalidated** by everything that can move a body, the zone, or the terrain
   beneath it?
8. Instrument it: the engine ships a water-mesh stat (`stat watermesh`) — tile counts and mesh cost
   belong in the budget sheet (`11`) like any other terrain pass.

Honesty about tier: this section is engine documentation (D/N), not measurement, and Water has
changed shape across releases — single render target → texture array, and a single Water Mesh actor
(as documented in the UE4-era pages) → bounded Water Zones with local-only tessellation. Community
reports of version-specific breakage (notably water interaction under World Partition) are F-tier
and worth checking against your release. Treat every
constant above as a shipped default, not a law, and treat the *architecture* — one paged zone, one
fused info capture, a sparse morphing quadtree, one wave evaluator, an opaque-surface volume pass —
as the transferable part.

## Stylized water: same contracts, different bands

Everything in this chapter up to here derives the water's look from physics. A large class of
shipped water — Nintendo's above all — *authors* the look instead, and the doctrine for it is
one sentence: **stylization replaces the band content, never the contracts.** The three bands
(geometry, material, shading) get hand-authored patterns, ramps and flat colour instead of
spectra and BRDFs — but the depth field, shore distance, flow field, `bodyType`, LOD/streaming,
pass ordering and the authority contract are exactly the same machinery, consuming the same
generator handoff. Answer a "make Wind Waker water" request by swapping band content, not by
reaching for FFT cascades and Cox–Munk glitter — that is the name-the-paradigm rule applied to
style.

- **The Wind Waker** (community-documented; Nathan Gordon's graphics analysis is the canonical
  breakdown): a flat-colour sea with **scrolling foam-ring patterns**, layered and wiggled by a
  displacement map, coarser layers at distance. The load-bearing observation: those foam rings
  are a **shore-distance band** — the *same exported field* our realistic shoreline foam
  consumes, drawn as an authored ring texture instead of an advected froth mask. Standard
  recreations use a Voronoi pattern with flow-offset UVs plus intersection foam. Depth still
  drives the colour split; shores still drive the foam; only the *content* is authored.
- **Tears of the Kingdom**: the cel look is community-observed (no first-party rendering talk),
  but the water *physics* has a real one — Nintendo's GDC 2024 talk describes computing **water
  resistance from the projected area along an object's velocity**: probe-style buoyancy/drag,
  i.e. `19`'s machinery, now with a shipped first-party citation.
- **Mario Kart World / Wave Race lineage**: the most instructive case, because it is not a look
  at all — the water is a **drivable gameplay surface**. Vehicles ride the wave geometry, waves
  serve as trick ramps, and surface explosions *raise new waves players trick off* — dynamic
  displacement that is gameplay-authoritative. Consequences, both owned by `19`: the
  one-evaluator rule (physics and renderer sample the same wave function) is **absolute** here —
  on drivable water a mismatch is not a floating-boat artifact, it is a broken road — and
  interactive waves are **gameplay liquid state** under the fluid authority contract:
  deterministic, CPU/server-owned, and network-synchronized in a multiplayer racer. The
  stylized look rides on top of that contract, not instead of it.

Honesty: Nintendo publishes almost nothing about rendering internals — every mechanism claim
above except the TotK physics talk is community reconstruction or press/footage observation
(F-tier), and Mario Kart World's is from launch-window coverage. Say so when citing.

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
- **Water too reflective / faintly plastic even when calm**: Fresnel `F0` left at the generic
  dielectric 0.04 (IOR 1.5). Water is IOR 1.33 → `F0 ≈ 0.02`; the default doubles surface
  reflectance.
- **Every liquid equally reflective**: `F0` hardcoded to water's value. Brine, oil and meltwater
  differ (IOR ~1.31–1.47, `F0` ~0.018–0.036); take `ior` from the `liquidBody` descriptor.
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
- **Stacked water through a single-depth-layer pass**: a river under a bridge over a lake, a fall
  crossing a pool, a pond on an island seen across the sea — the second surface simply is not there.
  This is the shading model's structural limit, not a bug to tune; either the level avoids stacked
  bodies or those bodies go through sorted transparency instead.
- **Absorption and scattering collapsed into one extinction**: a single `sigma` cannot distinguish
  bright-and-murky (sediment) from dark-and-clear (CDOM), and the phase asymmetry that aims
  scattering at the sun is gone with it. Wire `a`, `b` and `g` to their own inputs where the shader
  takes them, from the `liquidBody` descriptor (terrain-architect `28`).
- **Shared water capture sized to the zone, not the river**: one top-down info texture spanning
  kilometres gives a narrow river a handful of texels across, so banks quantize and flow smears into
  the ground value. Budget by texels-across-narrowest-body; shrink the zone or raise the resolution.
- **Stale water capture**: a body, the zone, or the terrain beneath moved, and nothing dirtied the
  top-down capture — flow points at last frame's channel and the shore fade sits off the bank. Every
  cached field needs its invalidation contract named, including this one; paths that render outside
  the frame loop must force the update.
- **Water hovering above the terrain it was supposed to carve**: the spline-driven brush is writing
  to a landscape edit-layer stack that is disabled, or to a layer the final composite doesn't
  include. Nothing about the water surface is wrong — the bathymetry under it was never written.
- **Two water bodies meeting with no junction contract**: river into lake, lake into sea. Surface
  height, flow, foam phase and optics all change across the line, and un-owned it reads as two
  shaders arguing. Declare a transition material and which side owns the boundary, exactly as for a
  LOD seam.
- **Every floating prop sampling waves every frame**: CPU wave queries are the real cost of buoyancy
  at fleet scale. Update probe points round-robin across frames and let rigid-body integration carry
  the object between samples; raise the rate for hero bodies only, and state the latency.
- **Ocean that stops short of the horizon**: a finite water body large enough to look infinite still
  ends, leaving a band of sky-coloured nothing between the water edge and the horizon line. That gap
  is what the far-distance ring exists for; it must share the datum and the atmosphere state (`10`).
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
- **Caustics crawling through a shadow**: the sun is occluded above the water — a shade sail, a
  tree, a diving board — and the caustic pattern plays across the shadow on the bed anyway. The
  sun-visibility gate is missing, or it was sampled at the receiver instead of at the surface
  entry point. Single most conspicuous caustics defect; see
  [the masking contract](#the-masking-contract--four-gates-and-the-third-is-the-one-that-gets-skipped).
- **Caustics added to albedo**: they then survive into shadow, into ambient-only lighting and into
  fog, and stop responding to exposure. Caustics multiply the sun term; they are irradiance.
- **Caustics projected onto terrain only**: the bed lights up and every swimmer, step, ladder and
  prop in the water stays conspicuously unlit by the brightest thing in the scene. Project in world
  space onto whatever the pass finds below the water plane.
- **Scrolled-texture water, revealed by dispersion**: every scale on the surface drifts at one
  speed, so fine ripples and long waves move in lockstep. Real water is dispersive and the long
  components outrun the short ones (~4:1 across a pool-sized band). Costs two seconds of footage
  to catch and no amount of still-frame polish hides it — see
  [Sun glitter](#sun-glitter-the-sparkle-path).
- **Glitter reviewed on a still**: a noise-perturbed specular is indistinguishable from real
  glitter in a screenshot and obviously wrong on a pan, because real glints ride crests and
  trackably travel with them. Judge sparkle on video, always.
- **Sparkle and caustics out of phase**: glitter driven from a noise texture, caustics from the
  wave field (or vice versa). The bright surface glint no longer sits above the bright fold it
  caused. One slope field feeds both, or neither is right.
- **Caustics that animate on flat water**: a Tier 0/1 fake with no coupling to the wave field. A
  flat surface has a constant Jacobian and produces *no* caustic structure — drive the pattern's
  amplitude from the wave amplitude, or the trick announces itself the moment the water settles.
- **A pool rendered with ocean defaults**: swell, whitecaps and a shoreline foam band on a 10 m
  body. The `bodyType` and fetch gates were never applied — see
  [Man-made water](#man-made-water-pools-tanks-and-channels).
- **A pool driven by a wind spectrum**: statistically homogeneous ripple everywhere, no source, no
  reflections, no standing structure. Plausible in isolation and obviously wrong beside a
  photograph, because real pool water is organised by the return jets and the walls. Model the
  basin response, not a sea — [The wave field is a driven
  basin](#the-wave-field-is-a-driven-basin-not-a-spectrum).
- **Sim patch faded out at a wall**: the open-water edge contract applied inside a basin, so wakes
  and jet trains dissolve exactly where they should bounce. In a closed body the domain edge is
  physical — reflect, do not fade.
- **Pool colour art-directed into `scatterColor`**: treated water has `b_b ≈ 0` and no body colour
  of its own; the cyan comes from bottom albedo attenuated over the down-and-back path. A pool
  tinted through the scattering term reads identically over every liner and at every depth, which
  is exactly the tell.

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
- **P/synthesis** — **Glacial-flour turquoise.** The popular Rayleigh/Tyndall explanation is
  physically wrong (rock flour is 2–65 µm, 10–100× the wavelength — Mie/geometric regime, where
  scattering is nearly wavelength-independent). The mechanism given in this chapter — flat
  backscatter shortens the photon path, over which `a_water` still removes red — is corroborated
  by measured-reflectance limnology: glacial-lake reflectance studies relate colour to suspended
  sediment and report that **finer grains at fixed concentration shift the reflectance peak
  shorter and brighten the water** (Everest-region in-situ + satellite study, *Mountain Research
  and Development* 37(1), 2017; high-elevation U.S. Rocky Mountain lakes, *Environmental Research
  Letters* 17, 2022). The full first-principles chain is assembled here rather than quoted from a
  single proglacial-lake IOP study; the mechanism is sound and now grounded.
- **D** — Beaufort wind force scale with its standard sea descriptions: the observational ladder
  used for [Sea states](#sea-states-the-energy-ladder). Descriptor wording taken verbatim from
  NOAA's Storm Prediction Center table (fetched 2026-08) — whitecaps first at Force 3, spray at
  Force 5, foam streaks at Force 7, spindrift at Force 8, "sea completely white" at Force 12.
  [NOAA SPC](https://www.spc.noaa.gov/faq/tornado/beaufort.html). The **WMO sea state code** (built
  on the Douglas scale) is the parallel sea-based classification; `H_s` as the mean of the highest
  third and `≈ 4·sqrt(m₀)` is standard oceanography. Adoption dates for the Douglas scale and the
  WMO codes conflict across secondary sources (Douglas 1921/1929; WMO wave codes 1946/1947/1970)
  and are deliberately **not** stated as fact here — only the NOAA descriptor wording is
  authoritative in this section.
- **P** — Capillary–gravity dispersion `ω² = (gk + (σ/ρ)k³)·tanh(kh)` and its **minimum phase speed
  ≈ 23.1 cm/s at ≈ 1.73 cm wavelength** — the hard short-wavelength bound used in
  [Calm water](#calm-water-the-low-energy-regime). Classical fluid mechanics; the constants were
  web-verified 2026-08 against standard references, the original derivation was not chased.
- **P** — Whitecap and foam optics: **void fraction 60–99%**, **mean bubble diameter 0.16–1 mm**,
  visible reflectance **~50% fresh breaking / ~40% active whitecap / ~18% thin residual foam**, and
  NIR reflectance troughs at **~750, 980, 1200 nm** from liquid-water absorption enhanced by
  multiple passes through bubble walls. Dierssen, H.M., "Hyperspectral Measurements,
  Parameterizations, and Atmospheric Correction of Whitecaps and Foam From Visible to Shortwave
  Infrared for Ocean Color Remote Sensing", *Frontiers in Earth Science* 7:14 (2019), fetched and
  extracted 2026-08; sole author verified 2026-08.
  [Open access](https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2019.00014/full).
  **Koepke (1984)'s ~22%** is a *time-averaged effective* whitecap reflectance from film-density
  measurements and under-represents fresh foam — correct for sea-average radiometry, wrong for a
  hero breaking wave. Earlier spectral work: Frouin et al. (JGR Oceans, 1996); Kokhanovsky
  (JGR Oceans, 2004).
- **T** — Barré-Brisebois & Bouchard, "Approximating Translucency for a Fast, Cheap and Convincing
  Subsurface Scattering Look" (GDC 2011; also GPU Pro 2; shipped in Frostbite 2): the
  view-dependent `dot(V, −L)` + thickness translucency approximation used for backlit wave crests.
  Verified 2026-08. [Frostbite](https://www.ea.com/frostbite/news/approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look).
- **P** — Liquid-sheet breakup cascade behind the waterfall progression: aerodynamic wave growth
  ruptures the sheet, fragments contract into ligaments (Rayleigh–Taylor), ligaments break into
  droplets by the **Rayleigh–Plateau** instability, most-unstable mode ≈ **9× the column radius**
  for an inviscid jet. Classical instability theory; mechanism chain web-verified 2026-08, no
  single canonical citation chased for the waterfall application specifically.
- **F** — The waterfall build (nappe → perforated sheet → ligaments → droplets → plunge-pool plume
  → lit mist), the three-class spray/foam/bubble split, and the sea-state feature gates as
  *rendering* triggers: production practice assembled over the physics above. The physics is P/D;
  the mapping to render features is this skill's composition.
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
- **P** — Optical refraction constants for water: IOR ≈ 1.33 → Fresnel `F0 = ((n−1)/(n+1))² ≈ 0.02`
  and Snell's-window critical angle `arcsin(1/1.33) ≈ 48.6°`. Standard optics (Snell, Fresnel);
  arithmetic verified 2026-08. IOR is a **per-body** property from `liquidBody` (terrain-architect
  `28`), not a constant: natural liquids span ~1.31–1.47 (`F0` ~0.018–0.036). Seawater/brine values
  (1.341 at 35 ‰ rising to 1.397 at 240 ‰) from Maykut & Light, "Refractive-index measurements in
  freezing sea-ice and sodium chloride brines", *Applied Optics* 34, 950–961 (1995); verified
  2026-08. The screen-space UV-distortion refraction is an approximation of
  Snell bending, not the ray-traced result — the amplitude-Fresnel and Snell derivations live in
  physically-based-rendering (`pbr-fundamentals`, `volumes-and-sss`).
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
- **D/N** — **Unreal Engine Water plugin** (the engine-native section): Epic documentation, fetched
  2026-08. Architecture and defaults —
  [Water System](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-system-in-unreal-engine);
  quadtree tiles, concentric-ring LOD, 4↔1 morphing, `Tile Size` 2400 uu, `Extent in Tiles` 64,
  `LODScale`, `Tessellation Factor`, far-distance mesh and the stated horizon-gap reason —
  [Water Meshing System and Surface Rendering](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-meshing-system-and-surface-rendering-in-unreal-engine);
  body types, spline metadata (river depth/width/velocity), the all-one-elevation lake rule, Island
  and Custom bodies, the Landmass brush with its depth curve / falloff modes / edge offset / blend
  modes, the edit-layers requirement, and exclusion volumes —
  [Water Body Actors](https://dev.epicgames.com/documentation/en-us/unreal-engine/water-body-actors-in-unreal-engine);
  the pass position, scattering/absorption/`PhaseG`/colour-scale inputs, the single-depth-layer limit
  and the low-end fallback —
  [Single Layer Water Shading Model](https://dev.epicgames.com/documentation/en-us/unreal-engine/single-layer-water-shading-model-in-unreal-engine);
  Gerstner generator parameters (`Num Waves` 16, wavelength/amplitude ranges and falloffs, dominant
  wind angle and spread, steepness, seed) and the custom-generator base class —
  [Water Waves Asset](https://dev.epicgames.com/documentation/en-us/unreal-engine/simulating-waves-using-the-water-waves-asset-in-unreal-engine);
  zone properties — water-info texture **array** (single-target form deprecated), half-precision
  toggle, capture Z offset, velocity-blur radius in the finalize pass, `ZoneExtent`,
  `RenderTargetResolution`, local-only tessellation with its sliding-window extent, auto-include
  landscapes as ground actors, `GroundZMin`, `MarkForRebuild`/`Update` —
  [AWaterZone API](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/Water/AWaterZone).
  ⚠️ Engine docs drift by release and Water has changed shape repeatedly; re-verify constants.
- **F/?** — The buoyancy amortization controls (`N Points Per Frame`, `N Frames Pause`) and the note
  that buoyancy is CPU-evaluated come from Epic's water-waves/buoyancy documentation as surfaced in
  search, not from a page-by-page read — the *technique* (round-robin probe updates with declared
  latency) is the transferable part and is standard practice. Community reports of version-specific
  Water breakage under World Partition are forum-tier and deliberately not asserted as fact.
- **?** — Attribution of specific shallow-water shoaling approximations to particular shipped
  titles beyond the two talks above: multiple GDC/SIGGRAPH-Advances talks cover it; treat any
  further specific title claim as unverified.
- **P** — Caustic brightness as the inverse Jacobian of the ray map (`E ∝ 1/|det ∂q/∂p|`):
  conservation of flux in a ray tube, classical geometrical optics. No specific citation is owed
  and none should be invented.
- **P** — Fold/cusp classification of caustic structure — the claim that a caustic network has no
  triple junctions, which is the load-bearing argument against the Voronoi fake. Whitney, "On
  Singularities of Mappings of Euclidean Spaces I: Mappings of the Plane into the Plane", *Annals
  of Mathematics* 62 (1955): the only structurally stable singularities of a smooth map of the
  plane into the plane are folds and cusps. The optics reading is Berry & Upstill, "Catastrophe
  Optics: Morphologies of Caustics and Their Diffraction Patterns", in E. Wolf (ed.), *Progress in
  Optics* 18, North-Holland (1980), 257–346 — venue, volume and pages verified 2026-08; Whitney's
  attribution is from model knowledge and was not re-checked against the paper.
  [ADS](https://ui.adsabs.harvard.edu/abs/1980PrOpt..18..257B/abstract).
- **P/F** — The focal-set vs cut-locus framing: that a Worley `F2−F1` ridge set is the cut locus of
  circular fronts expanding from the seeds (equivalently the Voronoi edge set, where the two
  nearest seeds tie), that circular fronts have a degenerate focal set (the evolute of a circle is
  its centre), and that a planar cut locus generically has degree-3 vertices while a focal set
  generically has cusps. Each piece is standard — singularity theory and computational geometry —
  and the statements were checked for internal consistency here, but **no source was chased for
  the combination**. It is this skill's account of why the fake resembles a caustic and why
  refining it cannot converge; present it as an argument, not as a cited theorem.
- **P** — Image-space caustic maps (Tier 2): Shah, Konttinen & Pattanaik, "Caustics Mapping: An
  Image-Space Technique for Real-Time Caustics", *IEEE TVCG* 13(2), 2007, 272–280
  ([IEEE Xplore](https://ieeexplore.ieee.org/document/4069236/)); Wyman & Davis, "Interactive
  Image-Space Techniques for Approximating Caustics", I3D 2006, 153–160
  ([ACM DL](https://dl.acm.org/doi/10.1145/1111411.1111439)). Both verified 2026-08.
- **D/F** — The water-specific practical build: Guardado & Sánchez-Crespo, "Rendering Water
  Caustics", *GPU Gems* 1 ch. 2 (2004) — explicitly an aesthetics-driven approximation, not a
  physical solution, and it says so itself. Verified 2026-08.
  [NVIDIA](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics).
- **P** — Caustic sharpness floor from the solar disc: 0.53° subtense (the same figure used in
  [Sun glitter](#sun-glitter-the-sparkle-path)), compressed on entry by `cos θ_i/(n cos θ_t)` —
  differentiated Snell, `≈ 1/n` near normal incidence. Arithmetic (0.53°/1.33 ≈ 0.40° ≈ 7.0 mrad,
  ≈ 0.7 cm blur per metre of depth) derived here and checked, not quoted from a source.
- **P/?** — Visible-band dispersion of water (`n ≈ 1.337 at 486 nm` to `≈ 1.331 at 656 nm`):
  standard optical data, quoted from model knowledge and **not** web-verified — treat the third
  decimal as indicative. The qualitative claim (fold sets separate per channel, so caustic edges
  fringe) is robust regardless.
- **P/F** — Glitter as a level set of the slope field, and the four review tests that follow
  (trackable crests, dispersive multi-scale motion, phase-lock with the caustics, interference
  rather than cells). The geometry — a glint occurs where the normal is the sun/eye half-vector —
  is definitional; the dispersion arithmetic (≈0.25 m/s at 3 cm against ≈0.93 m/s at 55 cm, from
  `c = sqrt(g/k + σk/ρ)`) was derived and checked here. Framing these as *review tests*, and the
  claim that a still frame cannot separate real glitter from noise-perturbed specular, is this
  skill's composition — production observation, not a cited result.
- **F** — The four-gate masking contract (depth fade, extinction along the light path, sun
  visibility at the surface entry point, irradiance-not-albedo) and the tier ladder as a whole:
  production practice assembled over the physics above. The shadow-at-entry-point rule is the one
  most often skipped and is stated here as doctrine, not as a cited result.
- **P** — Pool-water optics: pure-water absorption from the Pope & Fry dataset already cited above,
  sampled at this chapter's RGB points — `a ≈ (0.25, 0.056, 0.0092) m⁻¹` at 610/550/450 nm, as
  quoted in [Water-body optical identity](#water-body-optical-identity-where-sigma-actually-comes-from).
  Those three values come from that dataset by model knowledge and were **not** re-checked against
  the published table; the 418 nm absolute minimum is deliberately *not* used as a blue channel.
  The round-trip transmittances and the resulting `(0.38, 0.68, 0.78)` white-liner and
  `(0.11, 0.46, 0.68)` blue-liner returns are arithmetic done here, as are the liner albedos
  (`0.8` white, `(0.24, 0.54, 0.70)` mid-blue PVC), which are representative values, not measured
  product data.
- **P/F** — The driven-basin model for pool waves. Viscous decay `α = 2νk²` for deep-water gravity
  waves is Lamb's classical result (*Hydrodynamics*; attribution from model knowledge, not
  re-checked); `c_g = (g + 3(σ/ρ)k²)/(2ω)` follows from differentiating the capillary–gravity
  dispersion relation. The e-folding distances (~90 m at 16.5 cm, ~2.1 m at 3 cm, with
  ν = 1.004×10⁻⁶ m²/s) were computed here and are reproducible from those two formulas. That the
  filtration return is the dominant source, that tiled walls are near-total reflectors at these
  wavelengths, and the edge-contract inversion are this skill's framing from the physics plus
  direct observation — **no measurement of a wall reflection coefficient was chased**, so treat
  "near-total" as an argued approximation rather than a figure. The method-of-images construction
  and the early-reflections-plus-diffuse-tail split are standard room-acoustics practice carried
  over.
- **P/?** — The submerged-jet footprint. Linear spreading `r½ ≈ 0.094·s` and `1/s` centreline decay
  are textbook free-shear-flow results (Pope, *Turbulent Flows*, ch. 5; Rajaratnam, *Turbulent
  Jets*) and the structure was web-confirmed 2026-08; the numerical constants are from model
  knowledge and were **not** confirmed against a primary source — they vary by a few percent across
  experiments, which does not move the footprint qualitatively. The surface-deformation link
  `η ~ C·u'²/g` is a scaling argument (stagnation pressure of an eddy) whose **O(1) constant `C` is
  genuinely unknown**; `C = 1` was used, which is why the chapter states the near-field roughness as
  a ratio to the far field rather than as an rms slope. Free-surface turbulence is the weakest link
  in this subsection.
- **P** — The wake geometry. `c_min = (4gσ/ρ)^(1/4) = 0.231 m/s` at 17.1 mm is the standard
  capillary–gravity minimum already cited in [Calm water](#calm-water-the-low-energy-regime);
  `U0 = C_d√(2ΔP/ρ)` is Bernoulli with an orifice discharge coefficient (`C_d ≈ 0.92` assumed, a
  typical eyeball value from model knowledge); the stationary condition `c(k) = U·cos ψ` is textbook
  wave–current interaction, the same Doppler machinery this chapter cites for
  [rivers](#rivers-flow-driven-surfaces). That a running return's pattern is a narrow downstream
  band and cannot be a ring system follows from those with no free parameter, and is the durable
  part. The **±19° energy fan** is narrower than the ±78° range of stationary *wavevectors* because
  energy travels at `c_g·k̂ + U`; the figure is the output of integrating the ray equations
  (`H = σ(k) + k·U`, Hamilton's equations, wave-action conservation — standard geometrical wave
  optics in a moving medium, Whitham; attribution from model knowledge, not re-verified) through the
  jet's decaying drift field, as are the crest curvature and the downstream shortening. Reproducible
  from those equations plus a drift field; not a measured angle.
- **P/?** — Inextensible-film damping `α ≈ 0.35·k·√(νω)`. The *structure* follows from the Stokes
  layer an unstretchable surface forces beneath it and is not in doubt; the numerical prefactor is
  the classical Lamb/Levich result from model knowledge and **could not be confirmed against a
  primary source** in a 2026-08 search — the literature found (Jenkins & Jacobs 1997; the
  Alpers–Hühnerfuss slick line) confirms the clean-surface `2νk²` and the existence of strong
  film enhancement, not the prefactor. Treat the factor 3–9 as indicative. The restriction to short
  waves is physics, not caution: the inextensible limit needs film elasticity large against the
  wave, which fails for swell.
- **F** — That treated pool water sits outside every Jerlov class (`b_b ≈ 0`, `c ≈ a`, Secchi
  exceeding body depth), that pool colour is therefore a bottom-albedo property rather than a
  scattering one, and the man-made gating table: this skill's composition from the optics above
  plus standard pool-operation practice.
