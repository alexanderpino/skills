# PBR for Path Tracing

Offline and hardware-accelerated (DXR/OptiX/Vulkan RT, Metal RT) path tracing solves
the rendering equation by Monte Carlo integration. Unlike rasterization it can follow
the physics closely — many bounces, accurate volumes, spectral effects — at the cost of
noise that must be reduced by sampling smartly and denoising. This file covers the
general path-tracing toolkit, then the OpenPBR reference architecture.

## Table of contents
1. The Monte Carlo estimator
2. Importance sampling the BSDF (and the VNDF)
3. Next-event estimation & multiple importance sampling (MIS)
4. Russian roulette & path termination
5. Volumes and participating media
6. Spectral rendering & dispersion
7. Denoising
8. Wavefront vs. megakernel
9. The OpenPBR reference "prepare" architecture

---

## 1. The Monte Carlo estimator

The hemispherical integral becomes an expectation: sample directions `ωi`, evaluate
`f·L·cosθ`, divide by the sampling pdf, average. The estimator's variance (visible as
noise) is minimized when the pdf is **proportional to the integrand** — hence
importance sampling. The whole craft of a path tracer is choosing good pdfs and
combining them.

```
L_o ≈ (1/N) Σ  f(ωi,ωo) · L_i(ωi) · (n·ωi) / pdf(ωi)
```

A path tracer extends this recursively: at each hit, sample a new direction from the
BSDF, carry a **throughput** (running product of `f·cos/pdf`), and add emission and
direct-light contributions along the way.

## 2. Importance sampling the BSDF (and the VNDF)

To sample the GGX specular lobe, **sample the visible normal distribution (VNDF,
Heitz 2018)**, not the plain NDF: it never produces microfacets facing away from the
viewer, dramatically lowers variance at grazing angles, and gives a simple pdf. For a
multi-lobe BSDF (diffuse + specular + coat + transmission), **stochastically select one
lobe** proportional to its estimated weight, sample that lobe, but return the
**combined pdf across all lobes** so MIS stays correct.

## 3. Next-event estimation & multiple importance sampling (MIS)

Sampling only the BSDF finds small/bright lights very inefficiently; sampling only the
lights handles sharp specular poorly. **Next-event estimation (NEE)** explicitly
samples a point on a light each bounce and adds its (shadow-ray-tested) contribution.
**MIS** (Veach) combines BSDF sampling and light sampling with the **balance** (or
**power**) **heuristic**, weighting each technique by how well it sampled that path:

```
w_bsdf = pdf_bsdf / (pdf_bsdf + pdf_light)   // balance heuristic
w_light = pdf_light / (pdf_bsdf + pdf_light)
```

This is the single biggest variance reducer in a production path tracer. For many
lights, add **light importance sampling** (light BVH, ReSTIR DI/GI) to pick *which*
light to sample. ReSTIR (spatiotemporal reservoir resampling) is increasingly used for
real-time path tracing too.

## 4. Russian roulette & path termination

To keep paths unbiased but finite, after a few bounces terminate each path with
probability `1 − p` and divide survivors' throughput by `p`, with `p` based on
throughput (so dim paths die sooner). Don't start roulette too early or you add
variance to the bright, important early bounces.

## 5. Volumes and participating media

For transmission and subsurface scattering, the BSDF only handles the *surface*
interface; the integrator must transport light *through* the medium. On transmission,
enter a homogeneous (or heterogeneous) volume and do a **random walk** using
**delta/Woodcock tracking** against `extinction`, `single_scattering_albedo`, and a
**phase function** (Henyey-Greenstein, parameter `g`). See `volumes-and-sss.md` for the
physical model. This is how glass, smoke, skin, and marble are rendered correctly.

## 6. Spectral rendering & dispersion

RGB rendering can't represent dispersion (prismatic splitting) or accurate thin-film.
A **spectral** path tracer draws one or a few **random wavelengths** per path and
tracks radiance per wavelength; IOR becomes wavelength-dependent
(`ior(λ)`), so refraction splits naturally into smooth rainbows over many samples
instead of RGB ghosting. Hero-wavelength sampling reduces the resulting color noise.

## 7. Denoising

Path tracing converges as `1/√N`, so production relies on **denoisers** to hit clean
images cheaply: **Intel Open Image Denoise (OIDN)** and **NVIDIA OptiX/NRD** denoisers
take noisy radiance plus **auxiliary feature buffers** (albedo, normal, depth) and
reconstruct a clean image. Output **demodulated/auxiliary buffers** (separate albedo so
the denoiser preserves texture detail) and feed linear HDR data. Real-time RT uses
temporal accumulation (SVGF, ReSTIR + spatiotemporal filtering).

## 8. Wavefront vs. megakernel

GPU path tracers come in two architectures: **megakernel** (one big kernel does the
whole path — simple, but divergent BSDFs and registers hurt occupancy) and
**wavefront** (Laine et al.: split into stages — generate, intersect, shade, connect —
communicating through buffers, sorting work to reduce divergence). Wavefront scales
better for complex layered BSDFs like OpenPBR; megakernel is fine for simpler material
sets and is easier to write.

## 9. The OpenPBR reference "prepare" architecture

The Adobe-style OpenPBR reference (`openpbr-bsdf`) is the gold-standard pattern for a
path-tracer BSDF (full detail in `openpbr-reference.md` §10):

- **`openpbr_prepare()`** resolves relative IORs, applies coat-over-base roughening,
  builds the homogeneous volume, and (spectral) adjusts per-wavelength IOR.
- It avoids GPU-hostile virtual dispatch via **nested lobe structs**
  (`Fuzz → Coat → BaseAggregate`).
- **`openpbr_sample(rand)`** stochastically picks one lobe by weight; **the returned
  pdf is the combined probability across all active lobes**, satisfying MIS internally.
- Use `OPENPBR_USE_TEXTURE_LUTS = 1` and bind the energy/LTC tables as hardware
  textures — the C-array fallback adds register pressure and manual interpolation
  (`openpbr-luts-and-data.md`). The 7 energy LUTs keep the layered BSDF strictly
  energy-conserving; the LTC table evaluates fuzz.

Watch reciprocity: OpenPBR's albedo-scaling layering is **non-reciprocal**, which is
correct for unidirectional path tracing but needs adjustment for BDPT/VCM
(`debugging-testing.md`).
