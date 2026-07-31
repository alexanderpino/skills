# ADR 006 — Hybrid Gerstner water for the Terrain Studio viewport

**Status:** accepted
**Date:** 2026-07-31

## Context

Terrain Studio already renders water as a separate surface over real bathymetry. Its WebGL2 deferred
path writes an opaque terrain G-buffer, rasterizes a water mask/depth surface, then composites water
with screen-space refraction, Beer-Lambert absorption, Fresnel sky reflection, shoreline foam, and
ACES display mapping. The forward fallback draws the same water mesh translucently. Motion is only a
procedural normal perturbation; geometry, silhouettes, and water depth remain undisplaced.

The target visual reference has coherent displaced crests, broad and fine specular structure,
view-dependent white glints, dark troughs, and temporally stable non-repeating motion. The installed
Terrain Renderer `references/12-water-rendering.md` assigns all motion to the renderer and defines
Gerstner as a 4-16-wave analytic displacement/normal model. It identifies FFT as the general AAA
open-ocean default, but Gerstner as the correct choice for authored hero swells and constrained
budgets. Terrain Studio is a browser authoring viewport with finite lakes, rivers, and seas, not a
planet-scale shipping ocean. Water BRDF math routes to the installed Physically Based Rendering
`references/pbr-fundamentals.md`.

## Decision drivers

- Match the supplied hero-water quality in stills and motion on WebGL2.
- Preserve the terrain/hydrology boundary: graph fields remain still datum, depth, flow, and shore
  distance; no wave is written into `solidTop` or exported hydrology.
- Keep forward and deferred surfaces geometrically identical.
- Avoid a WebGPU/FFT compute dependency in Sprint 4.
- Remain stable under ACES, TAA-less camera motion, square and hex working lattices, and shallow shores.
- Expose physically meaningful wave controls without making artists author twelve arbitrary vectors.

## Considered options

### A. Keep the current normal-only fullscreen water

Cheapest and horizon-stable, but cannot produce crest silhouette, parallax, or displaced glint bands.
It cannot reach the target reference and is rejected as the final quality path.

### B. Spectral FFT cascades

Best statistical open-sea spectrum and the normal AAA ocean choice. It requires per-frame FFT
compute or several displacement textures, spectrum authoring, cascade tiling controls, and a WebGPU
or multi-pass WebGL2 subsystem. It is deferred as a later ocean-specific tier.

### C. Hybrid meshed Gerstner displacement plus screen-space optics — selected

Displace the existing finite water mesh with an analytic Gerstner sum, rasterize that exact displaced
surface into the water depth pass, and shade it through the existing fullscreen optical compositor.
Use analytic derivatives for geometric normals and distance-faded micro-normal cascades for detail
below the mesh Nyquist band. Rivers use flow-advection instead of ambient ocean displacement.

## Wave contract

### Authoring inputs

The renderer owns one immutable `WaterWavePreset` derived from these controls:

- wind direction in world degrees;
- wind speed in m/s;
- sea state `[0,1]`;
- root seed;
- maximum geometric amplitude in metres;
- body kind: `ocean | lake | river`.

The preset expands deterministically to 12 Gerstner terms, within chapter 12's grounded 4-16 range:
4 swell, 4 mid-band, and 4 capillary/chop terms. Wavelengths are logarithmically distributed across
body-appropriate authored ranges. Directions spread around wind direction with deterministic seeded
jitter; phases are seeded; no two wavelength or speed ratios are integer multiples. Per-term
steepness is clamped so `sum(Q_i * k_i * A_i) <= 0.85`. This is an accepted project safety choice,
not a universal water constant: installed water chapter 12 places the practical compression/foam
threshold in 0.5-0.9 and warns that choppiness past approximately 1.0 makes broad negative-Jacobian
folding visible. Selecting 0.85 keeps authored crests near the high-quality end of that grounded
range while retaining 0.15 margin before the documented fold regime. The preset gate also measures
the horizontal displacement Jacobian; a production preset with `J <= 0` outside its foam band fails.

For term `i`, with horizontal unit direction `D_i`, amplitude `A_i`, wavelength `lambda_i`,
`k_i = 2*pi/lambda_i`, deep-water angular frequency `omega_i = sqrt(g*k_i)`, phase `phi_i`, and
steepness allocation `Q_i`:

```text
theta_i = k_i * dot(D_i, xz) - omega_i * t + phi_i
x'      = x + sum(Q_i * A_i * D_i.x * cos(theta_i))
y'      = datum + sum(A_i * sin(theta_i))
z'      = z + sum(Q_i * A_i * D_i.y * cos(theta_i))
```

Analytic tangents `dP/dx` and `dP/dz` are accumulated from the same terms and
`N = normalize(cross(dP/dz, dP/dx))`. Finite differences are forbidden for the Gerstner normal.
The exact same function and time are used by forward color, deferred water-depth, and shadow/surface
passes.

### Depth, shore, and body behavior

Deep-water waves are modified near shore using graph-authored `waterDepth` and `shoreDistance`:

- displacement amplitude fades continuously to zero as depth approaches zero;
- wavelength and phase speed shorten toward the shallow-water approximation `sqrt(g*depth)`;
- a bounded shoaling gain steepens the band before the final fade;
- horizontal chop is reduced faster than vertical amplitude to prevent beach intersection.

These are plausibility approximations, not a shallow-water simulation. Lakes use lower amplitude and
narrower directional spread. Rivers do not use the ambient 12-term displacement: they advect two
phase-offset normal/detail samples along the graph `flowVelocity:m/s`, blend calm/ripple/turbulent
bands by speed, and derive foam only from shore distance, constriction/gradient, and speed causes.

## Shading contract

The deferred compositor remains the primary quality path:

1. reconstruct the exact displaced water surface from the water depth buffer;
2. compute analytic Gerstner normal plus two RNM/whiteout micro-normal bands that fade before
   undersampling;
3. reject refracted samples whose scene depth lies above the water surface;
4. apply Beer-Lambert absorption/scattering over view-ray thickness and vertical bathymetric depth;
5. evaluate dielectric water Fresnel with IOR 1.333 and derived
  `F0 = ((1.333-1)/(1.333+1))^2 = 0.02037`, using the installed PBR chapter's dielectric formula,
  plus GGX direct-sun glint;
6. increase roughness from screen-space normal variance to suppress sparkle;
7. reflect in this order: confident screen-space reflection when available, then the common analytic
   sky/environment fallback; both sources must share exposure and ACES mapping;
8. compose persistent crest/shore foam from causal masks, never from arbitrary white noise.

Sprint 4 does not add a full scene SSR ray marcher. The existing analytic sky is the grounded fallback;
the reflection interface and confidence input are defined so a later SSR pass can replace local
reflection without changing the water BRDF.

## Geometry, bounds, and LOD

The existing water mesh remains world-anchored and body-clipped. Deferred depth and forward color
share one displacement include/function. Culling bounds inflate by maximum vertical amplitude plus
maximum horizontal chop. Geometric displacement fades to zero when its projected parallax is below
one pixel; micro-normal bands continue farther and fade by derivative footprint. A coarse undisplaced
far datum remains the horizon fallback.

Ice and snow disable liquid displacement continuously using the existing phase masks. Wave time is
monotonic and independent of graph evaluation; pausing the viewport freezes it deterministically.

## Quality and performance gates

- Analytic plane control: zero amplitude is bit-identical to the existing datum/depth surface.
- Single-wave oracle: sampled displaced position and analytic normal match a double-precision CPU
  implementation at fixed `(x,z,t)` vectors.
- Pass parity: forward and deferred water-depth clip positions match for the same vertices/time.
- Conservative bounds: every sampled displacement lies inside the declared inflated bounds.
- Fold bound: the preset generator always satisfies `sum(Q*k*A) <= 0.85` and sampled Jacobian stays
  positive outside the declared foam band; a 1.05 mutation enters the documented fold regime and fails.
- Shore control: amplitude and horizontal chop reach exact zero on dry samples; no displaced vertex
  crosses below `solidTop` in the analytic beach fixture.
- Temporal control: same preset/time is bit-identical; phase advances continuously across a 60-second
  camera path with no reset pulse or integer beat in the sampled autocorrelation window.
- Specular stability: a roughness-from-normal-variance mutation demonstrably increases glint variance
  under sub-pixel waves; the production path remains below the fixed reference capture bound.
- Visual evidence: desktop 1440x900 and mobile 390x844 captures include overhead sun-glint, grazing
  reflection, shore, lake, fast river, ice transition, and the supplied-reference camera envelope.
- Pixel evidence: water mask is non-empty, finite, and changes under time advance while dry terrain
  pixels remain unchanged.
- Budget: after warm-up, the deferred Gerstner water pass is <= 2.0 ms p95 at 1440x900 on the project
  browser/GPU capture machine; forward fallback is <= 2.5 ms p95. The capture records hardware,
  browser, 120 measured frames, timer source, and percentile method. A budget miss blocks the preset
  count or requires an explicitly lower quality tier; it does not silently disable optics.

## Consequences

The viewport gains true wave displacement, crest parallax, analytic normals, and stable PBR glints
without changing the hydrology graph or adding FFT infrastructure. The cost is more vertex ALU, a
shared displacement contract across passes, conservative bounds, and a larger visual regression
suite. Open-ocean FFT, local interaction patches, wakes, planar reflections, and underwater Snell-
window rendering remain named later tiers, not hidden Sprint 4 scope.

## Grounding sources

- Installed Terrain Renderer `references/12-water-rendering.md`: still-data handoff, separate water
  surface, 4-16 Gerstner terms, FFT comparison, Jacobian folding/foam range, shore approximations,
  flow-map rivers, reflection/refraction/absorption composition, and displaced bounds.
- Installed Physically Based Rendering `references/pbr-fundamentals.md`: GGX/Smith microfacet BRDF,
  Schlick Fresnel, and dielectric `F0 = ((ior-1)/(ior+1))^2`.
- Current `src/legacy.js`: separate water mesh, forward water shader, deferred water-mask/depth pass,
  fullscreen optical compositor, depth rejection, absorption, Fresnel/sky fallback, foam, and ACES.
