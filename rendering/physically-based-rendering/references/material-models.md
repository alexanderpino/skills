# Material Models & Parameterizations

There is no single "PBR material." There is a family of models that share the
microfacet foundation (`pbr-fundamentals.md`) but differ in parameterization, lobe
set, and target pipeline. This file maps the landscape and shows how to translate
between them — the most common real-world task is porting a material from one
engine/format to another without it changing appearance.

## Table of contents
1. The two parameterizations: metallic-roughness vs. specular-glossiness
2. Cook-Torrance (the academic baseline)
3. Disney Principled BSDF (the artist-friendly standard)
4. glTF 2.0 (the interchange standard)
5. Unreal Engine and Unity
6. Autodesk Standard Surface / Arnold
7. OpenPBR (the modern ASWF über-shader)
8. MaterialX — the node-graph / interchange form of these models
9. Cross-model parameter mapping cheat sheet
10. Choosing a model

---

## 1. The two parameterizations: metallic-roughness vs. specular-glossiness

Almost every model exposes one of two ways to describe reflectance:

- **Metallic-Roughness (metal-rough):** `base_color`, `metallic`, `roughness`. The
  dominant convention (glTF, UE4/5, Unity URP/HDRP, OpenPBR). `metallic` selects
  whether `base_color` means *diffuse albedo* (metallic=0, with fixed dielectric
  F0≈0.04) or *specular F0* (metallic=1, no diffuse). Fewer textures, harder to
  express exotic dielectric specular tints, and produces white-edge artifacts at
  metal/dielectric boundaries (the "metallic seam").
- **Specular-Glossiness (spec-gloss):** `diffuse`, `specular` (RGB F0), `glossiness`
  (= 1 − roughness). More expressive (independent diffuse and specular color) but
  easier to author non-physical (energy-violating) materials, and more texture
  memory. Legacy in glTF (`KHR_materials_pbrSpecularGlossiness`, now archived) and
  some DCC tools.

Convert spec-gloss → metal-rough by detecting whether `specular` ≈ 0.04 (dielectric →
metallic 0, base_color = diffuse) or `specular` is bright/chromatic (metallic 1,
base_color = specular), with a blend in between; `roughness = 1 − glossiness`. The
conversion is lossy in the ambiguous mid-range — flag that for the user.

## 2. Cook-Torrance (the academic baseline)

The 1982 microfacet model that everything descends from: `f = D·G·F / (4 NoV NoL)`
plus a Lambert diffuse term. Modern "Cook-Torrance" in practice means **GGX NDF +
Smith height-correlated G + Schlick F + Lambert/Burley diffuse** (see
`pbr-fundamentals.md` §3–7). When someone says "implement a basic PBR shader," this
is what they mean. It has no coat, sheen, transmission, or multiscatter compensation
out of the box — those are the additions the richer models below provide.

## 3. Disney Principled BSDF (the artist-friendly standard)

Disney's "Principled" BSDF (Burley 2012, extended 2015) prioritized **art
directability over strict physical accuracy** and became enormously influential
(Blender's Principled BSDF, the basis for glTF and UE). Design principles: intuitive
0–1 parameters, sensible defaults, robust combinations. Core parameters:

`base_color`, `metallic`, `roughness`, `specular` (a 0–1 dielectric F0 scale, default
0.5 ↔ F0 0.04), `specularTint`, `anisotropic`, `sheen`, `sheenTint`, `clearcoat`,
`clearcoatGloss`, `subsurface`, plus (2015) `transmission`, `IOR`, and a thin/volume
distinction.

Key quirks to know: the `specular` parameter is a *remap*, not a physical F0 (F0 =
`0.08 * specular`); `roughness` is **perceptual** (square it for `α`); the diffuse
term is Burley with retroreflection. Blender's modern Principled BSDF (4.x) tracks
this closely and is the most common place people meet it.

## 4. glTF 2.0 (the interchange standard)

glTF 2.0 is the runtime/interchange format; its core material is **metallic-roughness**
and is deliberately minimal so every engine can implement it identically. Core:
`baseColorFactor/Texture`, `metallicFactor`, `roughnessFactor`,
`normalTexture`, `occlusionTexture`, `emissiveFactor/Texture`. Metallic and roughness
are packed in **one texture: B = metallic, G = roughness** (R often used for occlusion
when ORM-packed).

Richness comes from ratified `KHR_materials_*` extensions, which map almost 1:1 onto
the richer models: `KHR_materials_clearcoat`, `_sheen`, `_transmission`, `_volume`,
`_ior`, `_specular`, `_emissive_strength`, `_iridescence` (thin-film),
`_anisotropy`, `_dispersion`. If a user is targeting glTF, prefer these extensions
over inventing custom parameters — they're what viewers and engines understand.
The `KHR_materials_pbrSpecularGlossiness` extension is **archived/deprecated**; new
content should be metallic-roughness.

## 5. Unreal Engine and Unity

- **Unreal Engine** uses a metallic-roughness model (`Base Color`, `Metallic`,
  `Specular` (0–1, default 0.5 ↔ F0 0.04), `Roughness`) descended from Disney, with
  GGX + Smith + a fully analytic multiscatter/energy term, and shading models for
  clear coat, cloth, subsurface, hair, eye, etc. UE5 adds **Lumen** (software/hardware
  RT GI + reflections), **Nanite**, and **Substrate** — a slab-based layered material
  system conceptually close to OpenPBR's layering (see `scene-integration.md`).
- **Unity** uses metallic-roughness in URP/HDRP (the built-in pipeline historically
  offered both metallic and specular workflows). HDRP adds clear coat, anisotropy,
  iridescence, transmission/translucency, and SSS via a unified "Lit"/"StackLit"
  shader.

When porting *from* these into glTF/OpenPBR, watch the `Specular` 0–1 remap (it is
not F0) and the perceptual-roughness convention.

## 6. Autodesk Standard Surface / Arnold

**Autodesk Standard Surface** (the predecessor concept to OpenPBR, used by Arnold and
formerly the Maya default) is a layered über-shader with `base`, `specular`,
`transmission`, `subsurface`, `coat`, `sheen`, `thin_film`, and `emission` groups —
a near-superset of Disney aimed at film. OpenPBR is its successor and largely
backward-compatible in spirit; Maya/3ds Max/Arnold 2026 made **OpenPBR the default**,
superseding Standard Surface. If a user has Standard Surface materials, mapping to
OpenPBR is mostly a rename plus the coat-darkening/fuzz upgrades (see
`openpbr-reference.md`).

## 7. OpenPBR (the modern ASWF über-shader)

**OpenPBR Surface 1.1.1** (Academy Software Foundation, current as of April 2026) is
the convergence of Autodesk Standard Surface and Adobe's Standard Material into one
open standard, now the default in Maya/3ds Max/Arnold 2026 and supported across DCCs.
It is the most complete model here: a glossy-diffuse/metal/subsurface **base**, plus
**thin-film**, **coat**, and **fuzz** layers combined by physical layering and
statistical mixing, with explicit coat darkening and multiple-scattering energy
compensation. Treat it as the reference target for "the most physically complete
material." Full details in `openpbr-reference.md`; for the broad picture, OpenPBR is
"Disney/Standard Surface, made rigorous, open, and energy-conserving."

## 8. MaterialX — the node-graph / interchange form of these models

The models above describe *what* a surface is; **MaterialX** (ASWF, originated at
ILM) describes it as a **node graph** and a portable XML document — the vendor-neutral
way to author and interchange materials between DCCs and renderers. It matters here
because it is not a separate material model but the **canonical graph form of models
this skill already covers**: OpenPBR Surface and Autodesk Standard Surface are *defined
and distributed as MaterialX node definitions* (`<open_pbr_surface>`,
`<standard_surface>`), and glTF's PBR has a MaterialX node too. When a DCC says it
"supports OpenPBR," it almost always means the MaterialX OpenPBR node.

What a MaterialX graph actually contains:

- **Pattern nodes** — `image`, `tiledimage`, math/remap (`mix`, `multiply`, `ramp`,
  `curveadjust`), `noise`, `normalmap` — the texture/value plumbing that feeds inputs.
- **BSDF/shading nodes** — primitives like `oren_nayar_diffuse_bsdf`,
  `generalized_schlick_bsdf`, `dielectric_bsdf`, plus `layer`/`mix` operators
  that combine lobes. The über-shader nodes (`open_pbr_surface`) are themselves
  nodegraphs built from these primitives. This is the **lobe decomposition and
  layering-vs-mixing** from the skill's core mental model, expressed as a graph.
- A **`surfaceshader`** output wired to a `surfacematerial`.

The crucial point for implementers: a MaterialX graph is **not just data — it
generates shader code.** MaterialX ships **shader generators** (GLSL, MSL, Vulkan,
HLSL, OSL, MDL) that compile a nodegraph into the BRDF code described in
`realtime-rasterization.md` and `path-tracing.md`. So "material graph" → "shader" is a
real compilation step, not a metaphor.

How it relates to engine graphs: Unreal's **Material Editor**, Unity **Shader Graph**,
and Blender's shader nodes are engine-specific node graphs that play the same authoring
role but are **not interchange formats** — MaterialX is the vendor-neutral bridge they
increasingly import/export through. When porting OpenPBR/Standard Surface materials,
the MaterialX document *is* the material; map its node inputs with the cheat sheet
below (the input names match the model parameters).

## 9. Cross-model parameter mapping cheat sheet

Common translations (approximate — always verify with a white furnace test and a
side-by-side render):

| Concept | Disney | glTF 2.0 | Unreal | OpenPBR |
|---|---|---|---|---|
| Albedo/diffuse | `baseColor` | `baseColorFactor` | `Base Color` | `base_color` |
| Metalness | `metallic` | `metallicFactor` | `Metallic` | `base_metalness` |
| Roughness (perceptual) | `roughness` | `roughnessFactor` | `Roughness` | `specular_roughness` |
| Dielectric F0 control | `specular` (×0.08) | `KHR_materials_specular` / `ior` | `Specular` (×0.08) | `specular_ior` / `specular_weight` |
| Clear coat | `clearcoat` | `KHR_materials_clearcoat` | Clear Coat model | `coat_weight` |
| Sheen/fuzz | `sheen` | `KHR_materials_sheen` | Cloth model | `fuzz_weight` |
| Transmission | `transmission` | `KHR_materials_transmission` | (Substrate/translucency) | `transmission_weight` |
| Subsurface | `subsurface` | (volume + scatter) | Subsurface model | `subsurface_weight` |
| Thin-film | (none) | `KHR_materials_iridescence` | Thin Film | `thin_film_weight` |
| IOR | `IOR` | `KHR_materials_ior` | (per-model) | `specular_ior` |

Pitfalls when mapping:
- **`specular` remaps differ.** Disney/UE `specular` is a 0–1 control where 0.5 ↔
  F0 0.04 (`F0 = 0.08·specular`). glTF/OpenPBR express the same thing via IOR. Don't
  copy the raw number across.
- **Roughness is perceptual in all of these** but some shading code wants linear `α`.
  Confirm you're not double-squaring.
- **Metallic-seam artifacts** appear wherever you blend metal↔dielectric in a texture;
  if the destination model exposes a specular color (OpenPBR/spec-gloss), you can
  avoid them.

## 10. Choosing a model

- **Learning / minimal engine / WebGL:** Cook-Torrance metallic-roughness
  (`pbr-fundamentals.md` §9). Smallest correct thing.
- **Interchange / web / cross-engine asset delivery:** glTF 2.0 + `KHR_materials_*`.
  It's the lingua franca and every major viewer reads it.
- **Game engine:** use the engine's native model (UE/Unity); don't reinvent it.
  Reach for its layered system (UE Substrate, Unity StackLit) only when you need coat
  or multi-material layering.
- **Film / offline / maximum fidelity / future-proofing:** OpenPBR. It's the open
  standard, energy-conserving by construction, and now the DCC default.
- **DCC authoring that must round-trip:** match whatever the DCC's default is
  (increasingly OpenPBR) to avoid lossy conversions.
