# PBR for Real-Time Rasterization

Real-time PBR (Unreal, Unity, custom forward/deferred/clustered renderers, WebGL/WebGPU)
solves the rendering equation inside a hard frame budget (~16.6 ms at 60 fps). The
strategy is principled approximation: a handful of analytic light sources plus a
prefiltered environment, with energy conservation preserved as cheaply as possible.
This file covers the general real-time toolkit first, then OpenPBR-specific concerns.

## Table of contents
1. The real-time shading loop (analytic lights)
2. Image-based lighting & the split-sum approximation
3. Multiple-scattering energy compensation (cheap)
4. Analytic area lights (LTC)
5. Forward vs. deferred vs. clustered / Forward+
6. Mobile and bandwidth-constrained approximations
7. OpenPBR-specific real-time concerns

---

## 1. The real-time shading loop (analytic lights)

For each light, evaluate the Cook-Torrance BRDF (`pbr-fundamentals.md` §9) and
accumulate `BRDF · light_radiance · NoL`. Punctual lights (point/spot/directional) use
**physical falloff** (inverse-square with a smooth windowing function to reach zero at
the light's range) and physical intensity units (see `scene-integration.md`). Keep the
GGX visibility term height-correlated, remap perceptual roughness to `α = rough²`, and
clamp `α` and all dot products to avoid specular NaNs on smooth surfaces.

## 2. Image-based lighting & the split-sum approximation

Ambient/environment lighting is the hard part in real time because it's an integral
over the whole hemisphere weighted by the BRDF. Karis's **split-sum approximation**
(UE4) factors it into two precomputable pieces:

```
∫ L_i(l) f(l,v) NoL dl  ≈  PrefilteredEnv(R, roughness) · ( F0·scale + bias )
```

1. **Prefiltered environment map** — a mip chain of the environment cubemap, each mip
   pre-convolved with the GGX lobe for one roughness level. Sample by reflection vector
   `R` and roughness→mip.
2. **BRDF integration LUT** — a 2D texture indexed by `(N·V, roughness)` storing a
   `scale` and `bias` for `F0`. This is the directional-albedo term; it's tiny and
   environment-independent (bake once, ship with the engine).
3. **Diffuse irradiance** — a separate low-res irradiance map or spherical-harmonics
   (L2 SH, 9 coefficients) for the Lambert diffuse ambient.

```glsl
vec3 IBL(vec3 N, vec3 V, vec3 F0, float roughness, float NoV) {
    vec3 R = reflect(-V, N);
    vec3 prefiltered = textureLod(uPrefilterEnv, R, roughness * MAX_MIP).rgb;
    vec2 ab = texture(uBRDFLut, vec2(NoV, roughness)).rg;   // scale, bias
    vec3 specular = prefiltered * (F0 * ab.x + ab.y);
    vec3 irradiance = sampleSH(uDiffuseSH, N);              // or irradiance map
    vec3 diffuse = irradiance * albedo;                     // albedo = baseColor*(1-metal)
    return diffuse + specular;
}
```

Common bugs: forgetting to multiply specular by occlusion / a horizon term; using a
linear roughness→mip mapping (it should be perceptual); seams from non-seamless
cubemap filtering.

## 3. Multiple-scattering energy compensation (cheap)

The same energy loss that offline renderers fix with big LUTs (`pbr-fundamentals.md`
§8) is handled in real time with a single 2D LUT or an analytic fit:

- **Two-channel LUT:** store `E(N·V, roughness)` (directional albedo) and `E_avg(roughness)`
  in R/G of the BRDF LUT, then add a Kulla-Conty compensation term.
- **Analytic (Lagarde/Karis):** scale the specular by `1 + F0·(1/r − 1)` where `r` is
  the LUT's `scale+bias` energy — no extra texture fetch. Good enough for most games.

```hlsl
float2 E = EnergyLUT.Sample(s, float2(NoV, roughness)).rg;   // E(NoV), E_avg
float3 F_avg = F0 + (1.0 - F0) / 21.0;                        // avg Fresnel
float3 f_ms  = ((1.0 - E.r) * (1.0 - E.r)) / (PI * (1.0 - E.g));
float3 f_add = F_avg * F_avg * E.g / (1.0 - F_avg * (1.0 - E.g));
float3 specular = single_scattering + f_ms * f_add;
```

Without this, rough metals and rough dielectrics darken visibly — the white furnace
test (`debugging-testing.md`) makes it obvious.

## 4. Analytic area lights (LTC)

Real lights have area, and PBR materials look dramatically better under area lights
than under points. **Linearly Transformed Cosines** (Heitz et al. 2016) make GGX
tractable under polygonal/disk/line area lights: a small `(N·V, roughness)` LUT of
inverse 3×3 matrices transforms the area light into a space where the clamped-cosine
integral is analytic. The same LTC machinery is what OpenPBR's fuzz uses (§7). LTC is
the standard for rect/tube/sphere lights in UE and Unity HDRP.

## 5. Forward vs. deferred vs. clustered / Forward+

- **Forward:** shade each object against its lights directly. Easiest for *layered*
  materials (coat, sheen) and MSAA/transparency, but historically scaled poorly with
  light count. **Forward+ / clustered forward** fixes that by binning lights into
  screen-space tiles/clusters and is now the common choice.
- **Deferred:** write material attributes to a **G-buffer**, then shade in screen space.
  Great for many lights, but the G-buffer is a fixed, limited budget — you cannot store
  arbitrary per-pixel layered material data. Multi-lobe models (coat with its own
  normal, sheen color, transmission) must be **flattened**: blend `coat_normal` into
  `normal`, fold the coat into base roughness, drop or pack secondary colors. This
  violates strict layering but is mandatory for many-light deferred pipelines. UE5's
  **Substrate** addresses this with a variable-length, compressed material buffer.
- Choose deferred for many dynamic lights and simple materials; forward+/clustered for
  rich layered materials, transparency, and MSAA.

## 6. Mobile and bandwidth-constrained approximations

On mobile/WebGL, replace expensive terms aggressively but keep energy behavior sane:
use the optimized Karis GGX visibility approximation, mediump-safe formulations
(avoid `pow(x,5)` overflow — use a polynomial Fresnel), L2 SH instead of an irradiance
map, a smaller BRDF LUT or analytic energy term, and fewer prefilter mips. Tonemap and
do lighting in linear space but watch for mediump precision loss in HDR accumulation.

## 7. OpenPBR-specific real-time concerns

Implementing OpenPBR (`openpbr-reference.md`) in real time:

- **Replace the offline energy LUTs (0–6) with the single-2D-LUT or analytic
  compensation above.** OpenPBR 1.1.1 explicitly permits approximations.
- **Fuzz:** keep the LTC LUT (`openpbr-luts-and-data.md` ID 7) — LTC is already a
  real-time technique. Transform the light into LTC space and evaluate the cosine lobe.
- **F82-tint metal** is cheap enough for the lighting pass. In *deferred*, storing the
  full `specular_color` (RGB) costs G-buffer space — pack to a scalar tint or drop it
  for low-LOD materials.
- **Coat darkening:** evaluate the `Δ` factor analytically in-shader
  (`openpbr-reference.md` §6) rather than via a LUT.
- **Layering:** forward/forward+ can do true `Fuzz + (1−E)·(Coat + (1−E)·Base)`.
  Deferred must flatten as in §5 — true layered OpenPBR needs forward or a specialized
  clustered/Substrate-style pass.
