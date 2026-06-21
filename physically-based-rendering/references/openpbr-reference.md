# OpenPBR Surface — Deep Dive

OpenPBR Surface is the Academy Software Foundation's open über-shader standard, the
convergence of Autodesk Standard Surface and Adobe Standard Material. **Current
version: 1.1.1 (released 2026-04-17).** As of the 2026 releases it is the **default
material in Autodesk Maya, 3ds Max, and Arnold**, and is implemented across many DCCs
and renderers (it is a MaterialX subproject).

Authoritative sources:
- Specification: https://academysoftwarefoundation.github.io/OpenPBR/
- Reference implementation & changelog: https://github.com/AcademySoftwareFoundation/OpenPBR
- Companion paper: *OpenPBR: Novel Features and Implementation Details*, arXiv:2512.23696 (2025–2026).

For where OpenPBR sits among other models (Disney, glTF, UE), see `material-models.md`.
For the exact precomputed data tables, see `openpbr-luts-and-data.md`.

## Table of contents
1. Version history & what 1.1.1 changed
2. Architecture: layering vs. mixing
3. The layered structure (fuzz → coat → base)
4. The base substrate (glossy-diffuse / metal / subsurface)
5. F82-tint metal model
6. Coat layer & coat darkening
7. Fuzz (SGGX microflake via LTC)
8. Thin-film iridescence
9. Energy conservation in OpenPBR
10. The reference "prepare" architecture

---

## 1. Version history & what 1.1.1 changed

- **1.0 (2024-06-04):** initial release.
- **1.1 (2024-06-28):** added Zeltner sheen option; changed thin-film IOR defaults;
  subsurface color types vector3→color3; allowed fuzz to **darken as well as lighten**;
  clarified emission color formulas.
- **1.1.1 (2026-04-17):** clarifications and fixes — most importantly, **formalized
  that implementers may use approximations** ("for example for low-power constraints").
  Also: clarified thin-walled subsurface interactions, allowed **HDR emission colors
  > 1**, corrected MaterialX edge-tint multiplication and `geometry_thin_walled`
  connections, expanded the thin-film specification.

The 1.1.1 "approximations are permitted" clause is the official blessing for the
real-time vs. offline split this skill emphasizes: the spec defines the *model*, not a
mandatory implementation, so renderers may "trade off accuracy for efficiency."

## 2. Architecture: layering vs. mixing

OpenPBR builds materials from two physical operations:

1. **Layering (vertical):** stacking slabs — `fuzz` over `coat` over `base`. Layering
   must account for interface Fresnel, the upper slab's transmittance, **interfacial
   darkening**, and **base roughening** from a rough upper layer.
2. **Mixing (horizontal):** statistically blending slabs at the mesoscopic level by a
   weight — e.g. blending the dielectric and metal base interpretations via
   `base_metalness`, or mixing the opaque and translucent base via `transmission_weight`.

Keep these distinct from an *engine's* material-layering system (rust-over-steel
masks); those blend parameters *before* the BSDF runs (see `scene-integration.md`).

## 3. The layered structure (fuzz → coat → base)

Light hits the fuzz first, then the coat, then the base. Energy reaching a lower layer
is what the upper layer transmitted — implemented with non-reciprocal **albedo
scaling**:

```
result = Fuzz + (1 − E_fuzz) · ( Coat + (1 − E_coat) · Base )
```

where `E_x` is the directional albedo of layer `x`. The coat additionally absorbs
(`coat_color`), tints by view angle, and can roughen and darken the base.

## 4. The base substrate (glossy-diffuse / metal / subsurface)

The base is itself a mixture:
- A **dielectric glossy-diffuse** base: a GGX specular layer over a diffuse (or
  subsurface) substrate, with `specular_ior` driving Fresnel and `specular_roughness`
  the highlight.
- A **metal** base using the F82-tint conductor model (§5), selected as
  `base_metalness` → 1.
- A **subsurface/translucent** base when `transmission_weight` / `subsurface_weight`
  engage the unified volume (see `volumes-and-sss.md`).

`base_metalness` statistically mixes the dielectric and metal interpretations of
`base_color`; intermediate values are a true blend, which is how OpenPBR avoids hard
metallic seams better than a naive metallic-roughness lerp.

## 5. F82-tint metal model

OpenPBR uses the **F82-tint** conductor Fresnel (Kutz et al.) instead of plain
Schlick. It adds an artist control for the reflectance at ~82° (the angle of the
characteristic dip in real metals), letting you tint the grazing edge independently of
normal-incidence color **without** allowing the edge to exceed Schlick (so it can't
create energy). `base_color` is F0 (normal-incidence color); `specular_color` tints the
grazing region.

```hlsl
// VoH = dot(V, H). F0 = normal-incidence reflectance (base_color for metal).
// F82_Color = specular_color tint applied near 82 degrees.
float3 F82_Tint(float3 F0, float3 F82_Color, float VoH) {
    float3 F_S = F0 + (1.0 - F0) * pow(1.0 - VoH, 5.0);   // Schlick baseline
    float mu_bar = 1.0 / 7.0;                              // cos(~82 deg)
    float3 F_S_bar = F0 + (1.0 - F0) * pow(1.0 - mu_bar, 5.0);
    float3 F_bar   = F82_Color * F_S_bar;
    float k = (VoH * pow(1.0 - VoH, 6.0)) / (mu_bar * pow(1.0 - mu_bar, 6.0));
    return F_S - k * (F_S_bar - F_bar);
}
```

## 6. Coat layer & coat darkening

A clear (or colored) coat contributes a secondary Fresnel reflection, **volumetric
absorption** (`coat_color`), an angle-dependent tint, optional **roughening** of the
base, and **coat darkening** from internal inter-reflections. Coat darkening has two
mechanisms (paper Appendix F):

1. **Absorption traversed twice** — light entering and exiting the coat passes through
   the absorbing medium twice, contributing a `T_coat²` factor to the base term.
2. **Total internal reflection inter-reflections** — light bounces between the
   coat-air interface and the base, concentrating and darkening/saturating the base.

Effect strengthens with `coat_weight`. Real-time approximation:

```hlsl
// Approximate the base darkening factor Delta directly in-shader.
float K_r = 1.0 - (1.0 - AverageFresnel(coatIOR)) / (coatIOR * coatIOR); // internal diffuse refl
float K_s = F_Schlick(float3(0.04), VoH).r;                              // coat specular
float K   = lerp(K_s, K_r, base_roughness);
float3 Delta = (1.0 - K) / (1.0 - base_albedo * K);
float3 darkened_albedo = base_albedo * Delta;
```

## 7. Fuzz (SGGX microflake via LTC)

Fuzz replaces the old "sheen" lobe with a **volumetric microflake** layer using a
fiber-like **SGGX** phase function, approximated for evaluation with **Linearly
Transformed Cosines (LTC)** fitted to volumetric simulations. Because the microflakes
have a single-scattering albedo, multiple scattering tints the reflection with
`fuzz_color` and (since 1.1) fuzz can **darken as well as lighten**. A rough fuzz layer
also physically **roughens** the underlying surface. `fuzz_roughness` controls flake
shape (low → thread-like, shiny fabrics; high → spherical, dust/felt). Store the LTC
matrix coefficients + directional albedo in a 2D LUT (see `openpbr-luts-and-data.md`).

## 8. Thin-film iridescence

Thin-film (`thin_film_weight`, `thin_film_thickness`, `thin_film_ior`) models
wave-interference color shifts (soap bubbles, oil, anodized metal). Implemented from
first principles via Snell's law, amplitude Fresnel coefficients, and **Airy
summation** over the film (paper Appendix E). Author thickness in nanometers at high
precision (16/32-bit) to avoid banding (see `texture-authoring.md`).

## 9. Energy conservation in OpenPBR

OpenPBR is energy-conserving by construction via two mechanisms — keep them distinct:
- **Multiple-scattering compensation** for each rough GGX lobe (dielectric, metal,
  coat), driven by precomputed energy LUTs (`openpbr-luts-and-data.md`).
- **Albedo scaling** `(1 − E_top)` for the vertical layering (§3). This scaling is
  **non-reciprocal**, which is correct for unidirectional path tracing but needs care
  in BDPT (see `debugging-testing.md`).

## 10. The reference "prepare" architecture

The Adobe-style reference implementation (`openpbr-bsdf`) avoids GPU-hostile virtual
dispatch by resolving parameters up front, then using **nested lobe structs**:

1. `OpenPBR_ResolvedInputs` — raw parameters after texture sampling.
2. `openpbr_prepare()` — computes relative IORs, applies coat-over-base roughening,
   builds the `OpenPBR_HomogeneousVolume` for transmission/SSS, and (for spectral)
   adjusts per-wavelength IOR for dispersion.
3. `OpenPBR_PreparedBsdf` — caches the view direction and the nested lobe structure
   (`Fuzz → Coat → BaseAggregate`); `openpbr_eval()`/`openpbr_sample()` walk it.

This pattern (resolve once, evaluate/sample a nested lobe tree, stochastically pick one
lobe with a combined MIS PDF) is the recommended way to put OpenPBR in a path tracer;
see `path-tracing.md`.
