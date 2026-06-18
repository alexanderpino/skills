# PBR Debugging and Testing Guide

Implementing any PBR shader or BSDF requires rigorous validation. A small math error in
Fresnel, NDF, the masking-shadowing term, or PDF calculations can break energy
conservation and ruin physical plausibility. These tests apply to any model
(`material-models.md`) and both pipelines. **Before suspecting the BRDF math, rule out a
color-management bug** (linear/sRGB on the wrong texture) — that's the most common cause
of "wrong-looking" PBR (see `texture-authoring.md` §1).

Triage order that catches most issues fastest:
1. **White furnace test** (§1) — is energy conserved?
2. **Isolate lobes** (§2) — which lobe is wrong?
3. **Compare to a reference** (§4) — is it wrong, or just different?

## 1. The White Furnace Test
The ultimate test for strict energy conservation, and the first thing to run on any new
BRDF. Works for both real-time and offline (set a constant white environment / uniform
incoming radiance).

**Setup:**
1.  Disable all direct lights.
2.  Set the environment map to a pure, uniform white color (RGB 1.0, 1.0, 1.0).
3.  Apply your material to a sphere.
4.  Set `base_color`, `specular_color`, and `coat_color` to pure white (1.0).
5.  Set `base_metalness` to 0.0, then test at 1.0.

**Expected Result:**
The sphere must disappear completely against the white background.
*   **Darker than background (Energy Loss):** You are missing multiple-scattering compensation (Kulla-Conty or LUTs), or your Smith masking-shadowing function is clipping energy.
*   **Brighter than background (Energy Creation):** Critical bug. Check your PDF calculations. Ensure you divide the BRDF value by the PDF correctly. Verify your non-reciprocal albedo-scaling $(1 - E_{top})$ logic during layering.

## 2. Parameter Isolation Debugging
When a material looks wrong, isolate the lobes.

### Base Dielectric Verification
*   **Inputs:** `metalness` = 0, `coat` = 0, `fuzz` = 0, `transmission` = 0.
*   **Test:** Sweep `roughness` from 0.0 to 1.0. The highlight should broaden smoothly. At 1.0, the grazing edge should show a faint, broad Fresnel reflection, but it should not look like a mirror.

### Metal (F82-Tint) Verification
*   **Inputs:** `metalness` = 1, `base_color` = Red (1,0,0), `specular_color` = Green (0,1,0).
*   **Test:** Look at the sphere head-on; it should be red. Look at the grazing edges (silhouettes); they should smoothly transition to green. If the transition is harsh or missing, the F82-Tint math is flawed.

### Coat Interfacial Darkening Verification
*   **Inputs:** `base_color` = Mid-Gray (0.5), `specular_roughness` = 1.0, `coat_weight` = 1.0, `coat_roughness` = 0.0, `coat_darkening` = 1.0.
*   **Test:** Compare this to a sphere with `coat_weight` = 0.0. The coated sphere should look significantly darker and richer in color due to light bouncing between the coat boundary and the rough base. If they look identical in brightness, the $\Delta$ darkening factor is broken.

## 4. Compare Against a Reference
"Looks off" is not a bug report. Pin it down by comparing against a trusted reference:
*   **Furnace/MERL/analytic:** validate a single GGX lobe against the analytic
    directional albedo, or against a brute-force Monte Carlo integration of your own
    BRDF (they must match — if not, your `eval` and `sample`/`pdf` disagree).
*   **Cross-renderer:** render the same glTF/USD asset in a known-good renderer (Blender
    Cycles, an online glTF viewer, Arnold) and diff. Differences localize the bug to
    tonemapping, color space, or a specific lobe.
*   **`eval` vs `pdf` consistency (path tracers):** the white furnace test in a path
    tracer simultaneously checks that `f/pdf` is unbiased. Energy that's wrong *only*
    under importance sampling but right under uniform sampling means a pdf bug, not a
    BRDF bug.
*   **Convergence:** if a path-traced image won't converge (stays noisy), suspect
    fireflies from a bad pdf, missing MIS weights, or unclamped values (§3).

## 3. Common Pitfalls

### Anisotropy Rotation Artifacts
*   **Symptom:** A harsh seam or glitch in the anisotropic highlight where UVs wrap or the rotation angle texture crosses from 0 to 1.
*   **Cause:** Hardware filtering a scalar angle (e.g., 0.0 and 1.0 interpolate to 0.5/180deg instead of wrapping).
*   **Fix:** Pass anisotropy rotation as a `vec2(cos(theta), sin(theta))`. Convert the scalar angle to a vector *before* filtering, or author the textures as vector maps.

### Black Pixels / NaNs (Fireflies)
*   **Symptom:** Random black pixels or NaN explosions in the renderer.
*   **Cause:** Division by zero in GGX/Smith functions when `roughness` approaches 0, or `sqrt()` of a negative number during refraction math.
*   **Fix:** Clamp roughness to a minimum safe value (e.g., `max(roughness, 0.001)`). Clamp dot products like `NoL` and `NoV` to `max(NoX, 0.00001)`.

### Missing Reciprocity (BDPT Failure)
*   **Symptom:** Bidirectional path tracing (BDPT) produces noise or incorrect results compared to unidirectional path tracing.
*   **Cause:** OpenPBR uses *non-reciprocal* albedo scaling for layering ($1 - E(\omega_o)$).
*   **Fix:** The specification is designed for unidirectional path tracing. If you require strict Helmholtz reciprocity for BDPT, the layering logic must be mathematically altered.