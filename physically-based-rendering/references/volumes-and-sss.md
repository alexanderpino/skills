# PBR Volumes, SSS, and IOR

Transmission (glass, water), subsurface scattering (skin, marble, wax), and
participating media (fog, smoke) all require modeling light transport *inside* a medium,
not just at the surface. This file covers the general physics and the main
implementation strategies, then OpenPBR's unified volume. For how a path tracer
actually transports light through the medium (delta tracking, random walk), see
`path-tracing.md` §5.

## 0. Subsurface Scattering: the three implementation strategies
SSS models light that enters a translucent surface, scatters many times, and exits
nearby. There is a spectrum of approaches, trading accuracy for cost:
*   **Wrap / pre-integrated (real-time, cheap):** fake the effect by wrapping diffuse
    lighting around the terminator or using a pre-integrated skin BRDF LUT
    (curvature × NoL). No real transport; good enough for games at distance.
*   **Diffusion / BSSRDF (offline & high-end real-time):** approximate multiple
    scattering analytically with a diffusion profile. **Christensen-Burley** ("normalized
    diffusion") is the production standard — an artist-friendly profile driven by a
    scatter color and radius, used in Arnold/RenderMan/UE. Screen-space separable SSS
    (Jimenez) brings this to real time.
*   **Brute-force volumetric random walk (ground truth):** trace actual paths through
    the medium using `extinction`, `single_scattering_albedo`, and a phase function
    (§2). Most accurate, handles arbitrary geometry and heterogeneity, but noisy/slow.
    This is the direction modern path tracers (and OpenPBR's unified volume) take.

Choose by pipeline: wrap/pre-integrated for games, Christensen-Burley for most offline,
random walk when you need ground truth or complex geometry.

## 1. The Unified Volume (OpenPBR)
In OpenPBR, materials are not just surfaces; they have depth. When a ray transmits through the base surface, it enters the `OpenPBR_HomogeneousVolume`.
*   **Transmission (`transmission_weight`):** Represents light traveling through a clear or cloudy medium (e.g., glass, water).
*   **Subsurface Scattering (`subsurface_weight`):** Represents light entering a dense medium, scattering multiple times, and exiting near the entry point (e.g., skin, marble, wax).
*   **Unification:** The BSDF blends the parameters of Transmission and SSS to create a single set of volumetric properties: `extinction`, `single_scattering_albedo`, and `phase_function_anisotropy`.

## 2. Phase Functions (Henyey-Greenstein)
When light hits a particle inside a volume, it scatters. The *Phase Function* determines the directional distribution of that scattered light.
*   **Henyey-Greenstein (HG):** OpenPBR uses the HG phase function, parameterized by $g \in [-1, 1]$ (mapped from `transmission_scatter_anisotropy` or `subsurface_scatter_anisotropy`).
*   **$g = 0$:** Isotropic scattering. Light scatters equally in all directions.
*   **$g > 0$:** Forward scattering. Light tends to continue in its original direction (e.g., cloudy water).
*   **$g < 0$:** Backward scattering. Light bounces back towards the source.

## 3. Thin-Walled Geometry
The `geometry_thin_walled` boolean toggle fundamentally changes volume evaluation.
*   **Off (Solid):** Used for solid objects (bottles, statues). The ray enters the surface, refracts based on IOR, travels through the volume, and refracts again upon exiting.
*   **On (Thin):** Used for leaves, paper, or soap bubbles. Refraction is disabled (light passes straight through without bending). Volumetric absorption is converted into a view-dependent surface tint. The object is treated as having no internal depth.

## 4. Index of Refraction (IOR)
IOR dictates both how light bends (refraction) and how much light reflects (Fresnel).
*   **Absolute vs. Relative IOR:** Physical IORs are absolute (e.g., Water = 1.33, Glass = 1.5). When evaluating Fresnel at an interface, you must calculate the *relative* IOR ($\eta = IOR_{transmitted} / IOR_{incident}$).
*   **Layer Interactions:** In OpenPBR, if you have a Coat (IOR 1.6) over a Base (IOR 1.4), light reflecting off the Base must use the relative IOR ($1.4 / 1.6$). This can result in relative IORs $< 1.0$, which changes the shape of the Fresnel curve and can cause Total Internal Reflection (TIR) from the *outside* if not handled carefully.
*   **Fresnel to IOR Conversion:** Sometimes artists prefer to author specular reflectance at normal incidence ($F_0$) rather than IOR. The conversion is:
    $F_0 = \left( \frac{IOR - 1}{IOR + 1} \right)^2$
    $IOR = \frac{1 + \sqrt{F_0}}{1 - \sqrt{F_0}}$