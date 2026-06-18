# skills

Agent skills for graphics and rendering work.

## physically-based-rendering

Expert knowledge of **physically based rendering (PBR)** and photorealistic image
synthesis across both **offline path tracing** and **real-time rasterization**.

It started as an OpenPBR-only reference and was broadened into a general PBR /
photorealistic-rendering skill: the shared microfacet foundation, the full material-model
landscape, both rendering pipelines, and OpenPBR 1.1.1 as the modern reference model.

### What it covers

- **Fundamentals** — the rendering equation, radiometry, microfacet BRDF theory
  (GGX/Trowbridge-Reitz, Smith masking-shadowing, Fresnel/Schlick/F82), diffuse and
  sheen models, energy conservation and multiple-scattering compensation.
- **Material models** — Cook-Torrance, Disney Principled BSDF, glTF 2.0
  metallic-roughness, Unreal/Unity, Autodesk Standard Surface, and OpenPBR 1.1.1, with
  a cross-model parameter-mapping cheat sheet.
- **Real-time rasterization** — split-sum IBL, the BRDF LUT, analytic area lights (LTC),
  forward/deferred/clustered trade-offs, mobile approximations, cheap energy compensation.
- **Path tracing** — Monte Carlo estimators, VNDF sampling, next-event estimation and
  multiple importance sampling, Russian roulette, volumes, spectral rendering, denoising,
  wavefront vs. megakernel, and the OpenPBR reference "prepare" architecture.
- **Volumes, SSS & IOR**, **texture authoring & color management**, **scene integration**
  (lighting units, GI, anti-aliasing, tonemapping), and **debugging** (white furnace test,
  NaNs, energy loss).

### Layout

```
rendering/
├── physically-based-rendering.skill   # installable package (zip)
└── physically-based-rendering/        # same content, unpacked & reviewable
    ├── SKILL.md                       # router + core mental model
    └── references/                    # load-on-demand deep dives
```

The unpacked tree is the source of truth and is kept in sync with the `.skill` package.
It's plain Markdown, so any coding assistant — Claude (Sonnet/Opus), Gemini, Codex, etc.
— can read the files directly without unzipping.

### Using it

- **Claude / Agent Skills:** install `rendering/physically-based-rendering.skill`, or
  point a skill loader at the `physically-based-rendering/` directory.
- **Any assistant:** open `rendering/physically-based-rendering/SKILL.md`. It is a router:
  read it first for the core mental model, then open the reference file under
  `references/` that matches your task (it tells you which one).

### Maintaining

Edit files under `rendering/physically-based-rendering/`, then repackage:

```bash
python -m scripts.package_skill /path/to/rendering/physically-based-rendering ./rendering
# (scripts.package_skill ships with the skill-creator skill)
```
