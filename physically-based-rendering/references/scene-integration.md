# PBR Scene Integration

A PBR material model (any of those in `material-models.md`) is only one half of
achieving a photorealistic *image*. The material must be integrated with holistic
scene-level systems: color management, physically based lighting, global illumination,
anti-aliasing, shadows, and tonemapping. A perfectly correct BRDF still looks wrong if
the color pipeline, exposure, or tonemapper is wrong.

## 0. Color Management Pipeline (OCIO / ACES)
Photorealistic rendering must happen in a consistent, **scene-linear** working space,
with managed transforms at the boundaries:
*   **Working space:** do all lighting/shading math in linear, wide-gamut space —
    commonly **ACEScg** (or linear sRGB/Rec.709 for simpler real-time). Textures are
    converted *into* this space on input (albedo: sRGB→linear; data maps: stay RAW).
*   **OpenColorIO (OCIO):** the industry standard for managing these transforms
    consistently across DCCs and renderers. Use a single OCIO config so textures,
    render, and display all agree.
*   **View transform:** the final scene-linear HDR is mapped to the display via a view
    transform / tonemapper (ACES Output Transform, AgX, or a custom curve) — see §7.
    Never show raw linear values; never light with display-referred (already-tonemapped)
    textures.

## 1. Core Rendering Fundamentals
*   **Coordinate Systems & Handedness:** Be aware of whether your engine is Left-Handed (e.g., Unity, Unreal) or Right-Handed (e.g., OpenGL, Maya). This impacts cross products used to generate bitangents for normal mapping and anisotropy. MikkTSpace is the industry standard for tangent space generation.
*   **Depth Precision (Reverse-Z):** Standard depth buffers (near=0, far=1) lose precision exponentially as distance increases, causing severe z-fighting. Modern PBR engines use **Reverse-Z** (near=1, far=0) with a floating-point depth buffer. This distributes precision evenly across vast distances, which is critical for rendering thin layers like OpenPBR's Coat or Thin-Film without z-fighting artifacts.

## 2. Physical Lighting
*   **Light Units:** Lights should be authored in physical units: Lux (directional sun), Lumens (point/spot lights), or Candelas (area lights). Camera exposure should be controlled via EV100 (Exposure Value).
*   **Area Lights:** PBR materials look best under Area Lights (spheres, tubes, rectangles). Evaluating GGX under an area light requires specialized math (e.g., Linearly Transformed Cosines (LTC) or representative point approximations).
*   **Image-Based Lighting (IBL):** Ambient lighting must be evaluated using pre-filtered environment maps. The GGX specular lobe requires a Split-Sum approximation (evaluating the pre-filtered environment map and integrating it with the BRDF's directional albedo LUT).

## 3. Global Illumination (GI)
Indirect light (bounce light) is critical. If a red wall is next to a white PBR sphere, the sphere must reflect red light.
*   **Screen Space GI (SSGI):** Approximates bounce light using the depth buffer. Cheap but fails for off-screen geometry.
*   **Hardware Ray Traced GI (Lumen / RTX):** Traces rays into a simplified scene representation (BVH/SDF) to gather accurate indirect diffuse and specular bounce light. The indirect light must be evaluated through the OpenPBR BSDF to maintain correct roughness and Fresnel responses.

> **Engine-integration companion:** the GI *hierarchy and tiering* as an engine
> subsystem — choosing and falling back across Lumen (HW/SW) → DDGI probes → ReSTIR
> DI/GI → SDF → SSGI by platform and budget, and their memory/ms costs — is covered by
> the **`game-engine-guru`** skill (`references/RENDERING_AND_GRAPHICS.md`, "Global
> Illumination Hierarchy"). This file is responsible only for feeding that indirect
> light correctly through the BSDF.

## 4. Anti-Aliasing & Specular Aliasing
PBR materials, especially highly glossy ones (low roughness) or those with detailed normal maps, suffer from severe sub-pixel specular aliasing (shimmering/flickering).
*   **Temporal Anti-Aliasing (TAA):** Blends previous frames to smooth edges. Essential for PBR, but can cause ghosting on moving objects.
*   **Specular Aliasing Mitigation (Toksvig / LEAN / vR_m):** TAA alone cannot fix specular aliasing. The engine must dynamically increase the material's `roughness` based on the variance of the normal map within a pixel footprint, or based on geometric curvature (e.g., using `ddx(normal)` and `ddy(normal)` in the shader).

## 5. Shadows and Volumetrics
*   **Shadows (CSM / VSM / Ray Traced):** Shadows must properly occlude direct lighting. If an OpenPBR material has transmission enabled, the shadow it casts should be colored (tinted by the transmission color).
*   **Volumetric Fog:** Participating media (fog, smoke) scatters and absorbs light. The PBR lighting pass must account for the transmittance through the fog to the camera.

## 6. Material Layering (Engine Level)
Do not confuse OpenPBR's *internal* physical slabs (Fuzz, Coat, Base) with an engine's *Material Layering System*.
*   Engines often blend distinct PBR materials (e.g., painting a "Rust" material over a "Steel" material) using masks. This blending happens *before* the BSDF is evaluated. The resulting blended parameters (`base_color`, `roughness`, `metallic`) are then passed into the OpenPBR evaluation.

## 7. Post-Processing
*   **Tonemapping (ACES):** The output of the PBR lighting equation is High Dynamic Range (HDR) linear light. Monitors can only display Low Dynamic Range (LDR) sRGB. A tonemapper (like ACES) compresses the HDR values into LDR, ensuring bright highlights roll off smoothly to white rather than clipping harshly.
*   **Bloom:** Bright specular highlights or emissive OpenPBR surfaces scatter light in the camera lens. The Bloom pass must be energy conserving (it should blur the light, not arbitrarily multiply it) to maintain physical plausibility.