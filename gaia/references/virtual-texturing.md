---
type: Technique
title: Virtual texturing — caching the material resolve
description: "Decoupling terrain texture address space from residency: which of the two virtual-texture problems you actually have, and the cache boundary that keeps it correct."
tags: [rendering, rasterizer, materials, virtual-texturing, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: epicrvt, tier: F, locator: "Runtime Virtual Texture — page composition and invalidation" }
  - { id: mittring2008, tier: F, locator: "§2.3.2.1 The Indirection Texture and §2.3.2.7 its update — the page table; §2.3.2.2 Efficient Filtering Through Borders; §2.3.6 Computing the Local LOD, where §2.3.6.4 is the feedback pre-pass and credits it to Barrett, and §2.3.6.5 is the texture-space alternative Mittring prefers" }
  - { id: barrett2008, tier: F, locator: "the software page-table indirection and feedback loop" }
  - { id: tanner1998, tier: P, locator: "§2, the nested toroidal clipmap stack" }
  - { id: mishkinis2013, tier: F, locator: "the height-based blend with a contrast term" }
---
# Virtual texturing — caching the material resolve

**Tier: real-time rasteriser.** Virtual texturing decouples texture *address space* from
*residency*: a huge logical mip pyramid divided into pages, a physical page pool holding the
resident ones, and an indirection texture translating virtual UV to physical UV. That plumbing
answers two different questions, and conflating them is the most common way the architecture gets
adopted for the wrong reason.

## Use this

**Runtime virtual texturing: cache the terrain's stable material composite into pages, and sample
the cache.** No canonical paper describes this architecture either; standard practice is the
branded instance documented for Unreal Engine [epicrvt] — engine documentation, `F`, and flagged in
the bibliography as needing re-verification per release because it has changed shape between
versions. The page-table and feedback plumbing underneath it is older and far better written up,
though still in course and conference talks rather than review [mittring2008] [barrett2008].

The splat or ID resolve, the macro colour, the static roads and persistent
decals are composited once per page, on demand, and every subsequent frame is one indirection plus
one filtered fetch instead of `active layers × maps × projections` samples.

**Cross over to streaming virtual texturing** — pages produced from disk rather than by the
GPU — only when the answer to "does my authored texel data exceed VRAM?" is yes *and* survives the
budget arithmetic below. They are different problems that happen to share plumbing:

| | Runtime VT | Streaming VT |
|---|---|---|
| The problem it solves | The per-pixel material resolve is too expensive to run every frame | The authored unique texels do not fit in memory |
| Page producer | GPU compositor | Disk, plus transcode |
| Invalidation | Whenever a composited input changes | Never — content is immutable |
| Cost centre | Page render (the full material graph) | IO and transcode |

⚠️ **Do the unique-texel arithmetic before promising streaming VT.** 100 km² at one texel per
centimetre is 10¹² texels — about a terabyte even at one compressed byte each. Nobody ships that.
Real worlds mix a sparse near-unique layer with tiling detail on top, or drop to texels per
decimetre in the far field. If the disk cannot hold it, no cache architecture will fix it.

## The cache boundary — the one rule that decides correctness

**A page may contain only what is spatially stable.** Runtime VT is a cache, not the terrain's
state database.

| Legal inside a page | Forbidden inside a page |
|---|---|
| Static splat/ID resolve, macro colour, stable geometry-derived masks | Season amount or season blend |
| Static roads, persistent replayable decals, mesh-to-terrain contact blend | Global wetness, rain response, puddle level |
| Any input whose dirty region is bounded and replayable | Snow accumulation, melt, footprints, tyre compression |

The composition is explicitly two-layer: sample the cached base, then apply everything driven by
global time, weather, camera or interaction *after* the sample. A slow season transition is still
dynamic global state; "solving" it by staggering a world-wide invalidation only spreads the
cache-coherency defect across more frames. Page invalidation exists for bounded persistent edits,
not for a parameter that touches every page at once.

## Plumbing that is not optional

- **Page borders.** Bilinear and anisotropic filtering read neighbours, and at a page edge the
  neighbour is unrelated pool memory. Each physical page stores a border duplicated from the
  adjacent virtual pages: **one texel is enough for bilinear on uncompressed data, four for DXT**,
  because DXT compresses in 4×4 blocks and anything short of a whole block still seams
  [mittring2008] §2.3.2.2. **Border width caps usable anisotropy** — a footprint wider than the
  border reads across the seam, so VT samplers clamp max aniso, typically 4–8×. ⚠️ That cap is
  **stated here from practice, not from a source**: §2.3.2.2 raises anisotropic filtering only to
  decline it — "*because we haven't done any implementation we skip it here*" — and no artefact in
  this set puts a number on it.
- **Gradients come from *virtual* UVs — and then they must be scaled into the pool's space.**
  Differentiating *after* the page-table lookup gives a garbage mip and aniso choice exactly at
  page boundaries, where `physUV` jumps; that draws the page grid as hairline seams, worst at
  grazing angles, which is how terrain is always viewed. Virtual UVs fix the jump and are only
  half the rule, because `SampleGrad` measures its gradients against the texture being
  **sampled** — the pool, not the virtual texture. Inside a page the virtual→physical map is
  linear, so the chain rule is one constant (derived here):
  `s = virtualSize / (poolSize × 2^pageMip)` — the virtual resolution *at the resident page's
  mip*, over the pool's — and the call is
  `SampleGrad(pool, physUV, ddx(virtualUV) × s, ddy(virtualUV) × s)`. `pageMip` costs nothing to
  carry: the page table hands it over, since `physUV` cannot be computed without it. Drop it and
  the formula is correct on mip-0 pages alone. A 256k² virtual over a 16k² pool gives `s = 16`
  there, so unscaled gradients state a footprint 16× too small — **`log2 16 = 4` LOD levels too
  fine**. In general the error is `pageMip − log2(virtualSize/poolSize)` levels: negative
  (aliasing) on the fine pages the near field uses, positive (over-blur) once `pageMip` passes
  `log2(virtualSize/poolSize)`, and **exactly zero at that one page mip** — which is how a single
  test view passes. ⚠️ The *LOD* half is clamped at pool mip 0 in the too-fine direction whatever
  the pool's chain depth, and by the chain's last mip in the other, so what survives is bounded by
  that last mip and a shallow chain hides most of it. The *aniso* half does not clamp, and it is
  the half that bites: the anisotropy ratio is scale-invariant, so the hardware still takes the
  right number of taps and then spreads them along the gradient vector you passed, across `1/s` of
  the footprint they should cover — under-filtering on the fine pages where `s > 1`, at exactly the
  grazing angles the border-capped aniso above exists to serve, and over-spread into blur on the
  coarse pages where `s < 1`.
- **A feedback pass** discovers which pages pixels want: render a reduced-resolution buffer of
  (pageID, mip), read it back, dedupe, prioritise coarse mips first [barrett2008]. Latency is 1–3
  frames minimum. Design for it — prefetch along predicted camera motion, prime requests before a
  hard cut — do not deny it. **And subtract its own downscale from the mip it asks for.** With
  `feedbackScale = fullResWidth / feedbackWidth` (so 4 at quarter res), adjacent pixels of that
  buffer stand `feedbackScale` full-res pixels apart, so its `ddx(virtualUV)` is that much larger
  and the mip it computes is `log2(feedbackScale)` too coarse for what the main pass will sample.
  Request `mip = computeMip(virtualUV) − log2(feedbackScale)`. At quarter res that is 2 mips, and
  two mips coarser is a quarter of the linear texel density — **6.25% of the areal density the
  main pass needs**, and over a fixed screen area about 6.25% of the pages, the same factor twice.
  The pages that would sharpen the image are never asked for at all, so the finest page the table
  can serve stays `log2(feedbackScale)` mips coarser than the pixel wants, permanently. A
  deliberate coarse bias for working-set control sits *on top of* this term, never instead of it.
- **Permanently resident top mips.** The page table stores the finest *available* ancestor, so a
  miss renders blurry rather than black or chequerboard. Every VT that ever showed a magenta page
  was missing this.
- **Sizing: the pool absorbs churn, not steady state.** A screen shows at most
  `screenPixels × overdraw × anisoSlack` unique texels; at 4K that is a few thousand pages of
  128². Size by measured eviction age, not by cache-hit rate: if pages are evicted younger than a
  couple of seconds of camera motion, the pool is too small or the mip bias too aggressive. Read
  the other direction too — pages living *longer* than that while the image stays blurry means the
  pool is not the constraint, and the mip the feedback pass is asking for is where to look.

**What it beats.** *Per-pixel weight splatting* — several tiling layers blended by painted
weights, resolved every frame; still correct, still the right answer below a handful of active
layers, but its cost is `layers × maps × projections` per pixel per frame and one chunk with
twelve active layers sets the whole frame budget. *ID maps plus texture arrays* — two IDs and a
ratio per texel, sampling array slices; a cheaper way to get a large palette, and complementary
rather than competing: it is a good thing to *put inside* a VT page. *Clipmap texturing*
[tanner1998] — the direct ancestor, a nested toroidal stack whose residency is a pure function of
view distance; VT generalises exactly that, from concentric rings to arbitrary sparse pages, and
the clipmap survives where the residency really is radial. *Baked unique textures per tile* — no
indirection, no feedback, and a fixed cost per tile that scales with world area rather than with
screen area.

## What still has to be right inside the page

Caching a bad resolve caches it faithfully. Two things carry most of the quality:

- **Height-based blending, not a linear weight lerp** [mishkinis2013]. Give each layer a height
  map, and let the more prominent material win the boundary with a contrast term: sand fills the
  cracks, stone tops stay bare. It is the largest visual return per line of code in terrain
  materials, and it is the thing most often missing.
- **Weights are data, not colour.** Weight maps, ID maps and page tables are linear, never sRGB;
  ID maps are point-sampled and blended manually, never bilinear — interpolated IDs address the
  wrong array slice. Renormalise weights after any quantization or filtering, with an epsilon
  guard, or blend edges band and all-zero texels produce NaN speckle.

Mip generation for a composite must happen in **premultiplied** space. Box-filtering weights and
albedo independently averages through zero-weight texels and draws a halo at every layer boundary
in the distance — a defect that is invisible in the near view where it was authored.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| The page grid appears as hairline seams, worst at grazing angles | Gradients computed after indirection, or aniso set above what the border supports | Take derivatives from virtual UVs; clamp aniso to the border width. That kills the seams and only the seams — the derivatives still have to be scaled, next row |
| The whole surface filters wrong with the page seams clean — aliasing on near pages, over-blur on far ones, and one distance where it looks right | Virtual-UV gradients handed to `SampleGrad` unscaled, so the pool measured the footprint against its own size: an error of `pageMip − log2(virtualSize/poolSize)` LOD levels, and the anisotropic taps spread across `1/s` of the footprint | Scale both gradients by `s = virtualSize/(poolSize × 2^pageMip)`. Test a view holding several page mips at once — the error passes through zero at one page mip, so a view sitting there proves nothing |
| Blurry patches that sharpen a beat later | Feedback → request → upload latency, showing the fallback mip meanwhile | Prefetch by camera velocity; budget the transcode burst, and measure the latency, not the hit rate |
| Permanent blur — and the IO queue says which of the two causes it is | **Thrash**: the working set exceeds the pool. IO saturated, eviction age under a couple of seconds of camera motion. **Or the feedback bias**: requests are `log2(feedbackScale)` mips too coarse, so the finest pages are never asked for. Live working set about `feedbackScale⁻²` of what the image needs, IO quiet, eviction age long | Read the eviction-age histogram and the IO queue before growing anything. Saturated: grow the pool or bias mips, or cut the aniso overshoot inflating the set. Quiet: subtract `log2(feedbackScale)` from the requested mip |
| A multi-frame spike when the season or rain level changes | Global dynamic state was composited into pages, so one parameter dirtied the world | Move it out of the cache; sample the base, apply the overlay after |
| Persistent decals vanish sporadically | Stamps injected into pages were evicted with them and never replayed | Keep a stamp replay list; re-apply on page load |
| Dark or wrong-hue halos at layer boundaries, only in the distance | Composite mips box-filtered in non-premultiplied space | Premultiply weights before generating mips |
| Banded darkening along blend edges; NaN speckle | Weights not renormalised after top-K, quantization or filtering | Renormalise with an epsilon guard |
| Garbage materials in thin bands | ID map bilinearly filtered | Point-sample and blend manually, or dither |
| Weight halos and page-table corruption look-alikes after enabling an upscaler | A negative texture LOD bias applied globally, including to data maps | Bias detail content only; never weight maps, ID maps or page tables |
| One chunk sets the whole frame budget | Worst-case active-layer count never measured | Heatmap active layers; that number is the budget |
