# s18-glitter-1to1 — the glitter path, 1:1, with one flag switched

**Left: waves 4–17. Right: wave 18.** One bed, one camera, one instant of phase, one exposure key,
one code path. The only difference between the panels is `Water.subgrid_on`, and what that flag
decides is whether the sub-footprint slope field is **drawn** or left inside the slope
distribution.

**1:1 means 1:1.** The crop is taken from the full-resolution radiance buffer — rows 600–1080,
columns 540–900 of frame K's 1440 × 1920 supersampled render — so one render sample is one image
pixel and no downsample can smooth structure into existence or out of it.

## What changed, and where every visible thing comes from

Waves 4–17 shaded every water pixel with `p_tot(z*)`: the Cox & Munk slope **distribution**
evaluated at the slope that mirrors the sun into the eye. That is the *ensemble mean* of the glint
— the fraction of facets, over a whole sea, at that slope — and using it once per pixel is the
statement that **this pixel contains the whole ensemble.** True for a pixel a kilometre across;
false for the 0.10–0.42 m footprints in the lower half of this crop.

Wave 18 splits the slope into what the pixel's own footprint resolves and what it does not, **draws**
the first, and gives the density only the second:

| what you see on the right | the number it came from | where it is computed |
|---|---|---|
| individual facets clipping | `p_sub(z* − z_res)`, the *unresolved* density at the drawn residual | `beach_optics.glitter_radiance(slope0=…, var=…)` |
| dark water between them | the residual variance is smaller, so the Gaussian is narrower and falls away faster off each facet | `SlopeRealisation.residual` |
| the scale of the grain | `k_res = π/L`, the wavenumber the footprint can carry, per pixel and per axis | `SlopeRealisation.slope(foot_c, foot_a, ea)` |
| the grain coarsening toward the near field | footprint 0.10 → 2.66 m up the crop; the resolved share follows `ln(k_res/k_lo)/ln(k_hi/k_lo)` | `beach_optics.mss_fraction_below` |
| the amplitude of each band | Phillips' `k⁻⁴` saturation range, total pinned to Cox & Munk **minus the swell the geometry already draws** | `subgrid_realisation` |
| the elongation along the view | the footprint is stretched `1/\|d_z\|` along the view and not at all across it | `beach_render.render` |

**Nothing here is a texture and nothing here was tuned.** There is no noise field, no detail normal
map, no roughness parameter. The seed is 1954 and no frame was drawn twice to pick a better draw.

## The numbers, scene-linear, off the buffer

Interior coefficient of variation on a core strip 15% of the path's own half-maximum width, and the
median bright-run length on a box 60% of it, both measured on `L` before any tone curve:

| rows | footprint | CV before | CV after | run before | run after |
|---|---|---|---|---|---|
| 600–720 | 2.66 m | 0.374 | **0.663** | 56 px | **3 px** |
| 720–840 | 0.42 m | 0.624 | **1.110** | 9 px | **2 px** |
| 840–960 | 0.15 m | 0.475 | **1.356** | 16 px | **2 px** |
| 960–1080 | 0.10 m | 0.413 | **1.016** | 10 px | **1 px** |

**The run median is the honest discriminator, not the CV.** The "before" CV is not zero, and saying
why matters: the left panel still carries the swell tilting the specular condition, the whitecap
coverage mask, and a strong vertical brightness gradient inside each band — all of which land in a
standard deviation. What it does *not* carry is facets, and that is what the run median reads: 56, 9,
16, 10 pixels of unbroken bright water become 3, 2, 2, 1.

`gauntlet/sea/bar/generic/` measures 2–3 px runs with 2–6 px gaps between them on two photographs of
real glitter paths. **Those pixel counts do not transfer** — different rasters, different focal
lengths — and this figure is not calibrated against them. What does transfer is the shape: runs and
gaps of the same order, neither dominating.

## The exposure, stated because this figure is display-referred

Both panels are divided by **one** key, 151.41 W·m⁻²·sr⁻¹ in the green band, and taken through
γ = 2.2. The key is the maximum green of the **left** panel over the crop, so the smooth path just
reaches white and nothing in the left panel is clipped by the choice; whatever the right panel does
above or below it is the change. The key is a display decision, it is identical between the panels,
and every number quoted above is taken from the scene-linear buffer before that division.

For completeness, and only because the reference photographs are 8-bit: through that same encode
the core strip's standard deviation goes **43.3 → 66.3**, **42.9 → 58.4**, **21.2 → 34.6** and
**14.2 → 11.2** grey levels down the four bands. Those are display-referred numbers, produced by a
declared exposure, and they are quoted here rather than used as evidence.

*Drawn by `terrain-renderer/reference-impl/glitter_evidence.py`. No burned-in text: the panels are
pixels and nothing else, so a critic can be shown them without being told which is which.*
