# PBR Fundamentals & BRDF Theory

This is the shared mathematical foundation under every PBR material model and both
rendering pipelines. If a question isn't specific to one engine, one model, or one
pipeline, the answer usually lives here.

## Table of contents
1. Radiometry and the rendering equation
2. The BRDF/BSDF and its properties
3. Microfacet theory (the specular lobe)
4. The normal distribution function (GGX/Trowbridge-Reitz)
5. Masking-shadowing (Smith G) and the visibility term
6. Fresnel (Schlick, F82-tint, conductors)
7. Diffuse models (Lambert, Oren-Nayar, Burley)
8. Energy conservation and multiple scattering
9. Putting it together: a reference single-lobe BRDF

---

## 1. Radiometry and the rendering equation

PBR is built on **radiance** `L` (watts per steradian per square meter), the quantity
that is constant along a ray in a vacuum and is what a camera/eye integrates.

The **rendering equation** (Kajiya 1986) states that outgoing radiance from a point
`p` toward direction `ωo` is emitted radiance plus reflected radiance:

```
L_o(p, ωo) = L_e(p, ωo) + ∫_Ω  f(p, ωi, ωo) · L_i(p, ωi) · (n · ωi)  dωi
```

- `f(p, ωi, ωo)` — the BRDF/BSDF.
- `(n · ωi)` — the **cosine / foreshortening** term; light arriving at a grazing
  angle is spread over more area, so it contributes less per unit area.
- `∫_Ω` — integral over the hemisphere (BRDF) or full sphere (BSDF with transmission).

Every renderer is a strategy for evaluating this integral. Real-time rasterizers
approximate it with a few analytic light sources plus a prefiltered environment;
path tracers estimate it with Monte Carlo sampling. Same equation, different solvers.

**Solid angle and the cosine term** are the two things people most often get subtly
wrong. Highlights that are too bright at grazing angles or IBL that looks flat are
frequently a missing or doubled cosine term.

## 2. The BRDF/BSDF and its properties

The **BRDF** `f(ωi, ωo)` is the ratio of differential outgoing radiance to
differential incoming irradiance. A physically valid BRDF satisfies:

- **Non-negativity:** `f ≥ 0`.
- **Helmholtz reciprocity:** `f(ωi, ωo) = f(ωo, ωi)`. (Note: some practical layering
  models, including OpenPBR's albedo scaling, are intentionally *non-reciprocal* —
  this matters for bidirectional path tracing; see `debugging-testing.md`.)
- **Energy conservation:** the directional-hemispherical reflectance (albedo)
  `∫_Ω f(ωi, ωo)(n·ωi)dωi ≤ 1` for all `ωo`.

A **BSDF** generalizes the BRDF to include transmission (the integral covers the full
sphere). Real materials are modeled as a **sum of lobes**: specular + diffuse, plus
optional coat, sheen/fuzz, transmission, and subsurface. The art of a material model
is combining these lobes so the total still conserves energy.

## 3. Microfacet theory (the specular lobe)

The specular lobe of essentially every modern PBR model is a **Cook-Torrance
microfacet BRDF**. The surface is modeled as a statistical distribution of tiny
perfectly specular mirrors (microfacets). Only facets whose normal `m` equals the
**half-vector** `h = normalize(ωi + ωo)` reflect light from `ωi` to `ωo`.

```
f_spec(ωi, ωo) =  D(h) · G(ωi, ωo) · F(ωo, h)
                 ─────────────────────────────
                      4 · (n·ωi) · (n·ωo)
```

- **D** — Normal Distribution Function: what fraction of microfacets point along `h`.
  Controls highlight *shape*. → §4.
- **G** — geometric masking-shadowing: facets occluding each other. Controls
  grazing-angle *energy*. → §5.
- **F** — Fresnel: how reflectance rises toward grazing angles. Controls the *tint*
  and the rim. → §6.
- The `4(n·ωi)(n·ωo)` denominator comes from the change of variables between the
  half-vector and the reflection direction.

## 4. The normal distribution function (GGX/Trowbridge-Reitz)

**GGX** (a.k.a. Trowbridge-Reitz) is the industry-standard NDF because its long tail
matches real specular highlights better than Beckmann/Blinn-Phong. With roughness
`α` (commonly `α = perceptualRoughness²` — *always remap*; artists author perceptual
roughness, the math wants `α`):

```glsl
float D_GGX(float NoH, float alpha) {
    float a2 = alpha * alpha;
    float d  = (NoH * NoH) * (a2 - 1.0) + 1.0;
    return a2 / (PI * d * d);   // beware NoH→1, alpha→0 : clamp alpha
}
```

**Anisotropic GGX** uses separate `αx, αy` along the tangent/bitangent for brushed
metal, hair, and similar. Author anisotropy *rotation* as a `vec2(cos,sin)` direction,
never a scalar angle (a 0↔1 scalar interpolates through a 180° seam under filtering).

**Sampling** (for path tracers): sample the **visible normal distribution (VNDF,
Heitz 2018)** rather than the plain NDF — it produces far less variance, especially
at grazing angles, and never generates facets that face away from the viewer.

## 5. Masking-shadowing (Smith G) and the visibility term

`G` accounts for microfacets shadowing each other. The **Smith height-correlated**
form is the modern default (Heitz 2014); it's more accurate than the older separable
form. In practice you fold `G` and the `4(n·ωi)(n·ωo)` denominator into a single
**visibility term** `V = G / (4(n·ωi)(n·ωo))`:

```glsl
// Smith height-correlated visibility for GGX (Heitz 2014), as in Filament/Frostbite
float V_SmithGGXCorrelated(float NoV, float NoL, float alpha) {
    float a2 = alpha * alpha;
    float ggxV = NoL * sqrt(NoV*NoV * (1.0 - a2) + a2);
    float ggxL = NoV * sqrt(NoL*NoL * (1.0 - a2) + a2);
    return 0.5 / (ggxV + ggxL);   // already includes the 1/(4 NoV NoL)
}
// f_spec = D * V * F;
```

Use the height-correlated form unless you have a specific reason not to; the old
`G_SchlickGGX`/Smith-separable approximation is cheaper but loses energy and is rarely
worth it today.

## 6. Fresnel (Schlick, F82-tint, conductors)

Fresnel `F` is the fraction of light reflected (vs. refracted/absorbed) and rises to
1.0 at grazing angles for all materials. **Schlick's approximation** is near-universal:

```glsl
vec3 F_Schlick(vec3 F0, float VoH) {
    return F0 + (1.0 - F0) * pow(1.0 - VoH, 5.0);
}
```

- **Dielectrics** (non-metals): `F0` is a small achromatic value from IOR,
  `F0 = ((ior-1)/(ior+1))²`. For IOR 1.5 (most plastics/glass) `F0 ≈ 0.04`. Diffuse
  albedo comes from `base_color`; specular is uncolored.
- **Conductors** (metals): `F0` is chromatic and *is* the metal's color (gold, copper).
  There is no diffuse term. Reflectance at grazing can be slightly *below* the Schlick
  prediction for real metals — the **F82-tint** model (Kutz et al., used by OpenPBR)
  adds a tint control at ~82° to fit measured metals and lets artists color the rim
  independently without breaking energy. For ground-truth metals use the full complex
  IOR (n, k) Fresnel; F82-tint is the practical artist-facing fit.
- The **metallic** parameter interpolates a material between the dielectric and
  conductor interpretations of `base_color` (see `material-models.md`).

## 7. Diffuse models (Lambert, Oren-Nayar, Burley)

The diffuse lobe models light that refracts into the surface, scatters, and re-emerges.

- **Lambert** — constant `albedo/π`. Cheap, the real-time default, good enough for
  most surfaces. (The `1/π` normalization is mandatory and often forgotten.)
- **Oren-Nayar** — models microfacet *diffuse* roughness; rough surfaces (clay, the
  Moon) look flatter and retroreflect at grazing angles. Lambert makes them look too
  dark at the silhouette.
- **Burley / Disney diffuse** — an empirical model adding view/light-dependent
  retroreflection and a smooth roughness response; standard in film and many games.
- **Diffuse–specular energy balance:** a correct model scales diffuse by roughly
  `(1 − F)` (energy not reflected by the specular layer is what's available to
  scatter diffusely). Forgetting this double-counts energy at grazing angles.

## 8. Energy conservation and multiple scattering

Two separate problems, two separate fixes — keep them distinct:

1. **Single-scattering GGX loses energy at high roughness.** The microfacet BRDF
   models only *one* bounce off the microsurface; real rough surfaces bounce light
   multiple times between facets, and that energy is missing (rough metals look too
   dark). **Multiple-scattering compensation** adds it back:
   - *Offline:* precompute the **directional albedo** `E(θ, α)` (the hemispherical
     integral of the BRDF) and its average `E_avg(α)` into LUTs; add a compensation
     lobe (Kulla-Conty 2017). See `openpbr-luts-and-data.md`.
   - *Real time:* the same idea collapsed into a **single 2D LUT** `(N·V, roughness)`
     or a fully analytic fit (Lagarde/Karis). See `realtime-rasterization.md`.

2. **Layered lobes can double-count energy.** When stacking coat over base, or
   diffuse under specular, the lower layer must only receive the energy the upper
   layer *transmitted*. This is **albedo scaling**: `result = top + (1 − E_top)·base`,
   where `E_top` is the upper lobe's directional albedo. This is layering's energy
   conservation, distinct from the single-lobe compensation above.

The canonical correctness check for both is the **white furnace test** (uniform white
environment, white material → object vanishes). See `debugging-testing.md`.

## 9. Putting it together: a reference single-lobe BRDF

A minimal but correct opaque dielectric+metal point-light shading evaluation:

```glsl
vec3 BRDF(vec3 N, vec3 V, vec3 L, vec3 baseColor, float metallic, float perceptualRough) {
    vec3  H   = normalize(V + L);
    float NoV = max(dot(N, V), 1e-4);
    float NoL = max(dot(N, L), 0.0);
    float NoH = clamp(dot(N, H), 0.0, 1.0);
    float VoH = clamp(dot(V, H), 0.0, 1.0);
    if (NoL <= 0.0) return vec3(0.0);

    float alpha = max(perceptualRough * perceptualRough, 1e-3);   // remap + clamp

    // F0: 0.04 for dielectrics, baseColor for metals
    vec3 F0 = mix(vec3(0.04), baseColor, metallic);

    float D = D_GGX(NoH, alpha);
    float Vis = V_SmithGGXCorrelated(NoV, NoL, alpha);
    vec3  F = F_Schlick(F0, VoH);
    vec3  spec = D * Vis * F;                       // visibility already has 1/(4 NoV NoL)

    vec3 diffuseColor = baseColor * (1.0 - metallic);
    vec3 diff = (1.0 - F) * diffuseColor / PI;      // energy balance with specular

    return (diff + spec) * NoL;                     // caller multiplies by light radiance
}
```

This is the skeleton every model in `material-models.md` elaborates on (adding coat,
sheen, transmission, multiscatter compensation, etc.). Get this correct and stable
first — clamp `alpha`, clamp the dot products, remap roughness — then add lobes.
