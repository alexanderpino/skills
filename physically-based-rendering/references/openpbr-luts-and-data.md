# OpenPBR Lookup Tables (LUTs) and Data

The OpenPBR 1.1.1 reference implementation relies on precomputed data to maintain
strict energy conservation (compensating for multiple scattering in microfacet models)
and to evaluate complex volumetric phase functions (the SGGX microflake model for Fuzz).
This is implementation data, not part of the abstract spec — OpenPBR 1.1.1 explicitly
permits other approximations (see `openpbr-reference.md`). For the conceptual *why*
behind energy compensation, see `pbr-fundamentals.md` §8.

The Adobe reference implementation defines **8 required LUTs** (7 energy + 1 LTC).

## Dual-Mode Architecture
The reference code supports two modes via the `OPENPBR_USE_TEXTURE_LUTS` macro:
1.  **Array Mode (0):** LUTs are embedded as heavy C-arrays (`openpbr_energy_arrays.h`, `openpbr_ltc_array.h`). Interpolation is done manually in software. Highly portable, but increases binary size and is slower on GPUs.
2.  **Texture Mode (1):** LUTs are expected to be bound as hardware textures. The host application must define `OPENPBR_SAMPLE_2D_TEXTURE(id, uv)` and `OPENPBR_SAMPLE_3D_TEXTURE(id, uvw)`. This is mandatory for performance in hardware path tracing (DXR/OptiX).

## The 8 Required LUTs

The IDs below correspond to `OpenPBR_LutId_*` constants defined in `openpbr_data_constants.h`.

### Energy Compensation Tables (IDs 0-6)
These tables compensate for energy lost to multiple bounces within the microfacet structure. They are parameterized by combinations of Index of Refraction (IOR), Roughness ($\alpha$), and viewing angle ($\cos(\theta)$).

*   **ID 0: `IdealDielectricEnergyComplement` (3D)**
    *   **Dimensions:** 32 x 32 x 32
    *   **Axes:** $IOR, \alpha, \cos(\theta)$
    *   **Format:** 16-bit UNORM (C++/MSL/CUDA) or 32-bit UINT (GLSL).
*   **ID 1: `IdealDielectricAverageEnergyComplement` (2D)**
    *   **Dimensions:** 32 x 32
    *   **Axes:** $IOR, \alpha$
*   **ID 2: `IdealDielectricReflectionRatio` (2D)**
    *   **Dimensions:** 32 x 32
    *   **Axes:** $IOR, \alpha$
*   **ID 3: `OpaqueDielectricEnergyComplement` (3D)**
    *   **Dimensions:** 32 x 32 x 32
    *   **Axes:** $IOR, \alpha, \cos(\theta)$
*   **ID 4: `OpaqueDielectricAverageEnergyComplement` (2D)**
    *   **Dimensions:** 32 x 32
    *   **Axes:** $IOR, \alpha$
*   **ID 5: `IdealMetalEnergyComplement` (2D)**
    *   **Dimensions:** 32 x 32
    *   **Axes:** $\alpha, \cos(\theta)$
*   **ID 6: `IdealMetalAverageEnergyComplement` (2D)**
    *   **Dimensions:** 32 x 32
    *   **Note:** The data is conceptually 1D (dependent only on $\alpha$), but stored as a thin 2D texture (32x1) for API consistency.

### Fuzz / Sheen Table (ID 7)
*   **ID 7: `LTC` (2D)**
    *   **Dimensions:** 32 x 32
    *   **Axes:** $\cos(\theta_o), \alpha_{fuzz}$
    *   **Format:** `vec3` (Float or Half).
    *   **Usage:** Stores the Linearly Transformed Cosine (LTC) matrix coefficients and the directional albedo $E_{fuzz}$ required to approximate the volumetric SGGX microflake phase function.

## Implementation Note for Real-Time
If you are building a real-time rasterizer (e.g., Unreal Engine), you **cannot** afford to sample 3D textures for every pixel. You must replace LUTs 0-6 with an analytical approximation, such as the Kulla-Conty multiple scattering approximation, which only requires a single 2D LUT parameterized by $(N \cdot V, roughness)$ — or a fully analytic energy term with no extra fetch. LUT 7 (LTC) is still required and commonly used in real-time engines. See `realtime-rasterization.md` §3 and §7 for the substitutions.

## References
- Reference implementation & data: https://github.com/AcademySoftwareFoundation/OpenPBR
- Companion paper (energy compensation, coat darkening, thin-film derivations): *OpenPBR: Novel Features and Implementation Details*, arXiv:2512.23696.
- Kulla & Conty, "Revisiting Physically Based Shading at Imageworks" (multiple scattering).
- Heitz et al., "Real-Time Polygonal-Light Shading with Linearly Transformed Cosines" (LTC).