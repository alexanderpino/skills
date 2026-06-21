# PBR Texture Authoring Guide

Authoring textures for modern PBR (in Substance Painter/Designer, Mari, Quixel, etc.)
requires strict adherence to physical bounds, correct color management, and the right
channel/format conventions. The rules below apply to any PBR model
(`material-models.md`); OpenPBR-specific notes are flagged. Most "wrong-looking" PBR is
a texture/color-management bug, not a shader-math bug — check these first.

## 1. Color Management (Linear vs. sRGB)
The most common mistake in PBR texturing is incorrect color space handling.
*   **Color/Albedo Maps (`base_color`/albedo, `specular_color`, `coat_color`, `emission_color`):** These maps represent human-perceivable colors. They are almost always authored in an sRGB color space (or ACEScg). They *must* be converted to Linear space in the shader before any math is performed. Mark them sRGB on import.
*   **Data Maps (`roughness`, `metallic`, `normal`, AO, `anisotropy_rotation`, `thin_film_thickness`, height/displacement):** These maps represent raw math values, not colors. They must be saved and loaded as **Linear** (RAW) data — never sRGB. If a roughness map is accidentally gamma-corrected, the material will look entirely wrong (too glossy or too rough). Disabling sRGB on data textures at import is the single most common fix for "my metal looks plasticky."
*   **Albedo physical bounds:** real-world non-metal albedo rarely goes below ~0.02 (the darkest charcoal/asphalt, sRGB ~30–50) or above ~0.8–0.9 (fresh snow). Pure 0 or pure 1 albedo is non-physical and breaks GI/bounce lighting. Keep dielectric albedo within these bounds.

## 1b. Channel Packing & Map Conventions
*   **ORM / packing:** to save texture fetches, pack single-channel data maps into one
    RGB texture. The common **ORM** layout is R = ambient Occlusion, G = Roughness,
    B = Metallic (this matches glTF, which expects metallic in B and roughness in G).
    Packed data textures must be RAW/linear.
*   **Normal map handedness (the green-channel trap):** normal maps come in two
    conventions that differ in the **green (Y) channel sign**. **OpenGL** ("Y+",
    green points up) vs. **DirectX** ("Y−", green points down). Using the wrong one
    makes lighting look *inverted* — bumps read as dents. Unity/UE and many engines
    expect DirectX; glTF and most offline/OpenGL pipelines expect OpenGL. Either
    export the correct convention or flip the green channel on import. When unsure,
    render a known sphere and check that surface detail catches light correctly.
*   **Normal map color space:** RAW/linear. Encode/decode `n = 2·texel − 1`; renormalize
    after filtering/mip sampling.
*   **Metallic-roughness vs. specular-glossiness maps:** see `material-models.md` §1 for
    which set to author and how to convert. Metallic should be near-binary (0 or 1) for
    most real materials; intermediate values are for transition/wear masks, not "half
    metals."

## 2. The F82-Tint Metal Workflow
Traditional PBR uses `BaseColor` for metal reflectance and `Metallic` as a mask. The grazing edge Fresnel goes to white automatically. OpenPBR introduces `specular_color` to tint the grazing edge.
*   **`base_color`:** Defines reflectance at normal incidence (F0). For gold, this is yellow.
*   **`specular_color`:** Defines reflectance at the grazing edge (F82).
*   **Authoring:** For a physically accurate standard metal, leave `specular_color` at white (1.0, 1.0, 1.0). To create oxidized, coated, or stylized metal, tint the `specular_color`. Note: The F82 model mathematically prevents the grazing edge from being brighter than standard Schlick, preventing energy-breaking glowing edges.

## 3. Anisotropy: Rotation as Vectors
OpenPBR defines two anisotropy parameters for both the base and the coat: `roughness_anisotropy` (magnitude) and an implicit rotation.
*   **The Problem:** Traditional pipelines author rotation as a 0-1 grayscale map mapping to 0-360 degrees. When hardware texture filtering interpolates between a pixel at 0.0 (0 deg) and 1.0 (360 deg), it yields 0.5 (180 deg), resulting in a visible artifact seam.
*   **The OpenPBR Solution:** Rotation is provided as a `vec2(cos(theta), sin(theta))`.
*   **Authoring:** Export anisotropy rotation maps as 2-channel directional vectors (similar to a normal map) rather than a scalar angle.

## 4. Normal Maps & Displacement
*   **Tangent Space:** Normal maps are authored in Tangent Space. The engine must supply orthonormalized tangent and bitangent vectors to the BSDF.
*   **Displacement:** Displacement (Parallax Occlusion Mapping or tessellation) alters the macro-geometry. It must be evaluated *before* the BSDF, as it changes the `geometry_basis` normals and the effective view direction.

## 5. Thin-Film Iridescence
Thin-film interference creates rainbow patterns (e.g., soap bubbles, oil slicks).
*   **`thin_film_thickness`:** This map requires high precision (16-bit or 32-bit float). It represents the physical thickness of the film, usually scaled to nanometers (e.g., 0 to 1000nm). 8-bit maps will cause severe banding in the iridescence pattern.
*   **`thin_film_weight`:** Controls the presence/blend of the thin-film effect.

## 6. Fuzz vs. Roughness
The `fuzz_weight` and `fuzz_roughness` parameters replace the traditional "Sheen" lobe.
*   **`fuzz_roughness`:** Controls the shape of the SGGX microflakes.
    *   *Low (< 0.3):* Flakes align like threads. Use for shiny fabrics (silk, velvet).
    *   *High (> 0.7):* Flakes become spherical. Use for dust, peach fuzz, or matte felt.

## 7. Parameter Bounds
To prevent shader NaNs (Not a Number) and explosions, strictly enforce bounds during authoring or upon texture import:
*   `roughness`: Clamp to `[0.001, 1.0]`. Exact 0.0 causes division by zero in GGX.
*   `metallic`: Clamp to `[0.0, 1.0]`.
*   `ior`: Ensure $> 1.0$. (e.g., `[1.001, 3.0]`).