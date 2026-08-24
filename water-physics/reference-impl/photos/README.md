---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Evidence
title: Generic reference set — nine openly-licensed photographs, and what each one is evidence for
description: Nine openly-licensed reference photographs and the full licence trail for each.
tags: [water, photographs, licences]
status: stable
generated: { by: process:claude-code, at: 2026-08-23T15:52:23Z }
# --- end okf v0.2 ----------------------------------------------------
---
# Generic reference set — nine openly-licensed photographs, and what each one is evidence for

**This is not the bar.** The bar is `../bar.md` and it is frozen. Nothing in this
directory is one of the owner's Aljezur photographs, nothing here was taken at
Aljezur, and no image here may be cited as if it were.

## Why it exists, and exactly what it can and cannot fix

Three critics, in separate contexts, reached the same conclusion unprompted:

> *"Gross failures against criteria the bar states IN WORDS need no pixel
> comparison. But a verdict in the 6–8 band would not be honest without the
> images, and I would refuse to write one."*

The bar describes fifteen-plus photographs that **exist only in a conversation
and are not on disk**. That is a hard cap on the visual dimension, and no amount
of building lifts it.

**What this set fixes.** The fine-calibration questions the critics named are
questions about *what real water, sand and foam look like at a given scale* —
morphology and texture statistics. Those do not require this place at this time.
Nine images and the numbers below answer several of them.

**What this set does not fix, and cannot.** The hyper-realism criterion asks for
a render *"shot from a viewpoint one of the owner's photographs was taken from,
at the same framing, so the two can sit side by side."* **That half stays
blocked and this directory does not touch it.** No image here is at Aljezur, at
37.3167 N 8.8000 W, on 11 or 12 August 2026, from the owner's cliff or beach
station. A critic who credits the render against Aljezur on the strength of
anything in this directory has made an error this file predicted.

## The standing of every image here, stated once

> **Default: an image of unknown provenance is evidence for MORPHOLOGY and
> TEXTURE STATISTICS, and is never evidence for ABSOLUTE RADIOMETRY** — because
> its illuminant, exposure, white balance, tone curve and post-processing are
> unknown, and each of those corrupts a different quantity.

This project has already paid for that lesson twice, and both write-ups are the
register this file is written in: `../../../../terrain-renderer/references/11-verification-failures.md`
(*"Seven ways a measurement lies while looking like one"*, and in particular
*"A phone photograph is not a colorimeter, and it fails on three separate
axes"*), and the frozen bar's own preamble on the three iPhone failures.

Restated for this set, because it applies to every camera, not only phones:

| Failure | Where | Distorts | Survives it |
|---|---|---|---|
| Automatic white balance | in camera | **chromaticity**, worst at high saturation | luminance; within-frame pairs |
| Display-referred tone curve | in camera | **level**, non-uniformly | pairs **close in level** |
| Raw development / creative grade | on the photographer's machine | **everything**, unrecorded | nothing, unless the grade is stated |
| Wide-gamut read as sRGB | in the reader's pipeline | **chromaticity** | luminance, to ~1% |

Five of the nine carry a `Software` tag naming Lightroom, Photoshop or GIMP
(g1, g2, b1, b2, r1). Those are **graded** images. Two more (f1, f2) carry only a
Nikon firmware string and one (s1) only DJI firmware, which is consistent with a
camera JPEG but does not prove one. A grade is a fourth failure axis that the bar's table does
not have, because the owner's frames were straight camera JPEGs and these are
not. **Where a grade is present, colour is unusable and level is unusable; only
geometry, texture and within-frame ordering survive.** `b1` below is the worked
example of a grade destroying a channel outright.

### The one thing this set has that the bar's own frames do not

The bar's sections H, I, J, K, L and M all record *"no time was given; illuminant
`?`; time requested."* **Eight of the nine here carry an EXIF timestamp to the
second, and six of those carry EXIF GPS.** (g3 carries no EXIF at all; f1 and f2
carry a time but no position, so their coordinates below are *inferred from the
place name* and every derived number inherits that.) So for eight frames the
illuminant *geometry* is computable, by the same
NOAA/Meeus + Bennett recipe the bar used on its own two dated frames. Run
`measure.py` for the table; it is reproduced in **§6** below.

That is a real gain and it is also a **derived** number resting on two
assumptions — the timezone, and the camera clock being right. It is marked as
derived everywhere it appears, and the check is the one the bar itself
prescribes: **look at the shadow directions in the frame before trusting it.**

---

## 1 · The index

Total 4.3 MB. Every file is a Wikimedia-rendered thumbnail at the stated width,
stored byte-for-byte as served, so the bytes are re-fetchable from the URL. No
image in this directory was re-encoded, cropped or resized by this project.

### g1 · `g1-glitter-lowsun-baltic.jpg` — 1280 × 853

Sun-glitter path over open water, sun on the horizon, from a pier.

- **Source** <https://commons.wikimedia.org/wiki/File:K%C3%BChlungsborn,_Blick_von_der_Seebr%C3%BCcke,_Sonnenuntergang_--_2024_--_4955.jpg>
- **Bytes** exact thumbnail URL and SHA-256 in §8.
- **Licence** CC BY-SA 4.0 — attribution required.
  *"Dietmar Rabich / Wikimedia Commons / «Kühlungsborn, Blick von der Seebrücke, Sonnenuntergang -- 2024 -- 4955» / CC BY-SA 4.0"*
- **Own metadata** Canon EOS 5D Mark IV, 105 mm, f/14, 1/800 s, ISO 400.
  `2024-07-29 21:08:36` local. GPS 54.154827 N, 11.762102 E, alt 15.6 m (raw GPS
  altitude; **not** a surveyed camera height). Kühlungsborn, Baltic Sea.
  **Graded: Adobe Lightroom Classic 13.4.**
- **Evidence FOR** the glitter path's **shape and granularity**: the taper
  direction, the width ratio between horizon and near field, and the size of
  the dark gaps between bright facets. See §2.
- **NOT evidence for** any level or colour on the path (a sunset frame,
  graded, and the path spans the brightest and darkest parts of the frame — the
  exact case the bar's K3 forbids reading a level from). Not evidence for
  Atlantic swell: this is the Baltic, a short fetch, with groynes in the near
  field. Rows below y≈615 contain groyne posts and are excluded from every
  measurement.

### g2 · `g2-glitter-highsun-bay.jpg` — 1280 × 850

Sun-glitter path, sun well above the horizon, sheltered bay.

- **Source** <https://commons.wikimedia.org/wiki/File:El_Guamache_Bay,_Margarita_island.jpg>
- **Licence** **CC0** — public domain dedication, no attribution required.
  Credited anyway: Wilfredo R. Rodriguez H. (Wilfredor).
- **Own metadata** Nikon D300, 18 mm (27 mm eq.), f/16, 1/1000 s, ISO 200.
  `2013-01-04 16:15:13` local. GPS 10.874759 N, 64.053718 W. El Guamache Bay,
  Isla Margarita, Venezuela. **Processed: GIMP 2.8.0.**
  *(The EXIF GPS longitude field carries no W reference; the Commons record and
  the place both give 64.05 **W**. Recorded because a sign error here would
  invert the derived solar azimuth.)*
- **Evidence FOR** the **granularity of a glitter path at a second sun
  elevation**: separated clipped facets with dark water between them, and the
  path's much greater width at high sun. See §2.
- **NOT evidence for** the taper direction — see the discrepancy recorded in
  §2.3, which is left as a discrepancy rather than explained away. Not evidence
  for open-ocean slope statistics: a sheltered bay, capillary-gravity ripple, no
  swell. Not evidence for any level or colour.

### g3 · `g3-glitter-satellite-modis.jpg` — 1280 × 1786

Sun glint over the Atlantic off West Africa, from orbit.

- **Source** <https://commons.wikimedia.org/wiki/File:Sunglint_off_the_Western_Coast_of_Africa_May_13_2012.jpg>
- **Licence** **Public domain** (NASA). Credit: NASA / MODIS Rapid Response
  System, Terra or Aqua MODIS, 2012-05-13. No attribution legally required;
  given anyway.
- **Own metadata** No EXIF. Date `2012-05-13`; time of day, sensor, and
  processing chain **`?`** beyond "MODIS corrected-reflectance true colour",
  which is a *product*, not a calibrated sRGB image.
- **Evidence FOR** exactly one thing, and it is a negative: **this is what the
  ensemble mean of the glint distribution looks like.** At 250 m per pixel no
  facet is resolved, so the glint band is smooth, broad and structureless —
  which is precisely what the optics verdict said the render is drawing at the
  *observer's* range. Hold g3 and g1 side by side: same physics, two scales, and
  the render is at the wrong one.
- **NOT evidence for** anything at observer scale, for water colour (a
  corrected-reflectance product), or for texture — the visible vertical striping
  in the glint band is **detector banding**, an instrument artefact, and anyone
  measuring texture off it will measure the sensor.

### f1 · `f1-breaker-three-whites.jpg` — 1920 × 1294

A spilling/plunging breaker from a cliff top, with a bather in frame for scale.

- **Source** <https://commons.wikimedia.org/wiki/File:Porto_Covo_Outubro_2014-3.jpg>
- **Licence** CC BY-SA 4.0 — attribution required. *"Alvesgaspar / Wikimedia
  Commons / «Porto Covo Outubro 2014-3» / CC BY-SA 4.0"*
- **Own metadata** Nikon D800E, 105 mm, f/10, 1/200 s, ISO 100.
  `2014-10-26 16:19:43` local. **No GPS.** Place from the file's own description:
  Porto Covo, Portugal. No `Software` tag — camera JPEG or minimally handled.
- **A relevance note that is an inference and is written as one.** Porto Covo is
  on the same south-west-facing Portuguese Atlantic coast as Aljezur, roughly
  60 km north, with the same swell exposure and the same quartz sand. **That
  makes it a good analogue and does not make it the bar.** The coordinates used
  for the solar calculation (37.8553 N, 8.7919 W) are **inferred from the place
  name, not read from the file**, and every number derived from them inherits
  that.
- **Evidence FOR** the **three whites of section C** as visibly different
  surfaces in one exposure; the **spread of level inside a single nominal
  "white"**; **the section-A green direction, at matched luminance** — the thin
  backlit crest is 1.13–1.15× greener in `G/B` than deep water of the same
  brightness in the same frame (§5); **whitewater reading strongly blue against
  sand metered in the same exposure**; and a metric scale via the bather.
  See §3, §4 and §5.
- **NOT evidence for** absolute foam reflectance, water colour, or the Aljezur
  wave field. Not evidence for the plunging lip's interior — the lip here is
  spilling forward, not enclosing air.

### f2 · `f2-swash-foam-lace.jpg` — 1920 × 1172

Swash and backwash on a sand beach from a cliff top; two walkers for scale.

- **Source** <https://commons.wikimedia.org/wiki/File:Porto_Covo_March_2010-2.jpg>
- **Licence** CC BY-SA **3.0** — attribution required, and note the version
  differs from f1. *"Alvesgaspar / Wikimedia Commons / «Porto Covo March 2010-2»
  / CC BY-SA 3.0"*
- **Own metadata** Nikon D80, 50 mm (75 mm eq.), f/13, 1/320 s, ISO 100.
  `2010-03-13 16:55:41` local. **No GPS.** Porto Covo, Portugal — same inference
  and the same caveat as f1.
- **Evidence FOR** the **foam-edge structure** the bar's section C and H2 name —
  cusps, scallops, lace stranded above the retreating water, foam fingers; the
  **wet/dry sand tonal step**, measured on a same-row pair so that range, slope
  and illumination are controlled; the **laden backwash**; and a metric scale via
  the walkers. See §3, §4.
- **NOT evidence for** colour or level in absolute terms, and not for the
  turbidity *concentration* — that the backwash sheet is grey-brown rather than
  clear is visible; how much sediment that is, is `?`.

### s1 · `s1-wetdry-nadir.jpg` — 1280 × 960

Nadir drone view of a beach, waterline, rock ledge and shallow water.

- **Source** <https://commons.wikimedia.org/wiki/File:Caspersen_Beach_top_down_aerial_view.jpg>
- **Licence** CC BY-SA 4.0 — attribution required. *"Grendelkhan / Wikimedia
  Commons / «Caspersen Beach top down aerial view» / CC BY-SA 4.0"*
- **Own metadata** DJI FC220 (Mavic Pro), 4.73 mm (26 mm eq.), f/2.2,
  1/406 s, ISO 100. `2018-12-24 16:21:43` local. GPS 27.055961 N, 82.442464 W.
  Caspersen Beach, Venice, Florida. Flight altitude **`?`** — not in the
  metadata this project retrieved, so there is **no ground sample distance** and
  no metric scale here.
- **Evidence FOR** the **wet/dry sand step measured without obliquity** — a nadir
  view removes the foreshortening that every oblique frame has, and the beach
  face is close to planar across the sampled strip, so wet and dry sand sit at
  nearly the same slope to the sun. Also for the bar's section-D confusable
  pair: the bed *showing through* shallow water, stationary, over sand and over
  dark rock in one exposure.
- **NOT evidence for** the brown wet sand the bar describes: this is white
  Florida quartz-shell sand, near-neutral wet and dry (`linR/B` 1.08 and 1.11).
  **The tonal step transfers; the hue does not.** Not evidence for any absolute
  level, and not for foam texture — the whitewater on the ledge is a thin band
  at the edge of resolution.

### b1 · `b1-headland-refraction.jpg` — 1280 × 719

Oblique drone view along a coast: headland, cliff, multiple shore-parallel
breaking lines wrapping the point.

- **Source** <https://commons.wikimedia.org/wiki/File:Punta_Mango_en_El_Salvador.jpg>
- **Licence** **CC0** — no attribution required. Credited anyway: Casa
  Presidencial El Salvador, via Flickr.
- **Own metadata** Hasselblad L2D-20c (DJI Mavic 3), 12.29 mm (24 mm eq.), f/4,
  1/240 s, ISO 100. `2025-04-02 17:30:13` local. GPS 13.174355 N, 88.167564 W.
  Punta Mango, El Salvador. **Graded: Adobe Lightroom 10.2.3 (iOS).**
- **Evidence FOR** **plan geometry only**: crests turning to stay parallel to a
  curving shore, several separated breaking lines seaward of one another,
  breaking concentrated on the point. That is the bar's H4 / J refraction check
  in a frame whose curvature differs from the bar's, so a render cannot satisfy
  both by coincidence.
- **NOT evidence for colour, and this frame is the set's worked example of why.**
  Measured on the stored file, the offshore water reads sRGB **(8.7, 113.1,
  155.8)** — a mean red of 8.7 out of 255. **A red channel at the floor is a
  grade, not an ocean.** Nothing about hue, saturation or the blue-to-teal ladder
  may be read here, and the same grade is on every pixel including the surf.

### b2 · `b2-embayed-colour-ladder.jpg` — 1920 × 1237

Cliff-top oblique of an embayed pocket beach: headland, cliff, curved sand
beach, surf lines following the curve, sea stacks.

- **Source** <https://commons.wikimedia.org/wiki/File:Chimney_Rock_Trail_Point_Reyes_December_2016_panorama_1.jpg>
- **Licence** CC BY-SA 4.0 — attribution required. *"King of Hearts / Wikimedia
  Commons / «Chimney Rock Trail Point Reyes December 2016 panorama 1» /
  CC BY-SA 4.0"*
- **Own metadata** Nikon D750, 35 mm, f/8, 1/200 s, ISO 100. `2016-12-03
  16:20:03` local. GPS 37.991378 N, 122.972403 W. Point Reyes, California.
  **Graded: Adobe Photoshop CS5.** Original 9000 × 5800 — **a stitched
  panorama.**
- **Evidence FOR** the **scene type**: this is the closest geomorphological
  analogue in the set to the bar's section J — cliff, headland, curved beach,
  pocket embayment, surf wrapping the curve, offshore stacks. Useful for
  *ordering* and for *what has to be in frame*.
- **NOT evidence for angles**, because a stitched panorama has been reprojected:
  a crest azimuth measured here is a property of the stitcher as much as of the
  sea. **Not evidence for colour or level either**, and the reason is visible:
  with the sun at ~5° elevation the left third carries heavy flare, and the
  measured "open sea" there (`linY` 0.388) comes out *brighter* than the surf
  (0.304), which is physically absurd and is the flare. **This frame was
  intended to serve the deep-blue-to-teal colour ladder and it cannot. See §5.**

### r1 · `r1-shore-platform-pockets.jpg` — 1280 × 720

Wave-cut shore platform with pockets and pools, sand infilling the hollows, dark
weed on wet rock, stratified cliff and a stack behind. Monochrome.

- **Source** <https://commons.wikimedia.org/wiki/File:Stratified_Chalk_Cliffs_and_Tidal_Pools_at_Flamborough_Head.jpg>
- **Licence** CC BY-SA 4.0 — attribution required. *"TXGemGem / Wikimedia
  Commons / «Stratified Chalk Cliffs and Tidal Pools at Flamborough Head» /
  CC BY-SA 4.0"*
- **Own metadata** Sony ILCE-7M2, 77 mm, f/8, 1/80 s, ISO 100. `2025-05-17
  12:55:04` local. GPS 54.116328 N, 0.124833 W. Flamborough Head, Yorkshire.
  **Graded: Adobe Lightroom 8.3.1, and converted to monochrome.**
- **Evidence FOR** the **morphology of the bar's H1**: a flat bench at sea level,
  deeply pocketed, sand in the hollows, weed banding the wet rock, and pocketing
  that requires spatially varying hardness — chapter `12`'s point that uniform
  rock gives a straight cliff and nothing else. The monochrome conversion is
  convenient rather than a defect: **it removes the temptation to read colour off
  a graded frame**, and the claim under test is geometric.
- **NOT evidence for** anything chromatic (there is no colour), for level, or for
  Algarve lithology — this is Cretaceous chalk, not the Algarve's limestone and
  schist. The *mechanism* transfers; the rock does not.

---

## 2 · The glitter path, measured

Reproduce with `python3 measure.py`. All lengths in pixels of the stored file.
`luma8` is Rec.709 luma on the stored 8-bit sRGB code values — **not** luminance
and **not** linear light. It is used here because every quantity in this section
is a *spread* or a *shape*, and both live in the code values.

### 2.1 The claim under test

From the optics verdict on the render: a glitter path clipping at 255 across
**144 px**, with an **interior standard deviation of 1.0–2.6 grey levels**, whose
edge falls 255 → 118 over 45 px **without one non-monotone step**, and which
tapers the wrong way. The bar's K1 says a real path *"narrows toward the horizon
and spreads toward the observer"* and is granular at every scale.

### 2.2 g1 — sun on the horizon, taper and granularity

Six bands from just under the horizon (top) to the near field (bottom). "half-max
width" is the width of the row-averaged cross-path profile at half its height
above the local background. "core" is a ±10 px strip on the path centre.

| band (rows) | half-max width | % of frame width | core mean | **core sd** | core p5 | core ≥ 250 |
|---|---|---|---|---|---|---|
| 333–379 (nearest horizon) | **38 px** | 3.0 % | 200.5 | **41.3** | 117.3 | 3.4 % |
| 379–426 | 43 px | 3.4 % | 185.9 | 50.4 | 103.6 | 4.4 % |
| 426–472 | 52 px | 4.1 % | 155.6 | 52.2 | 82.7 | 1.9 % |
| 472–519 | 53 px | 4.1 % | 143.0 | 59.6 | 53.8 | 2.0 % |
| 519–565 | 44 px | 3.4 % | 156.1 | 59.8 | 66.2 | 2.2 % |
| 565–612 (near field) | **75 px** | 5.9 % | 129.3 | 57.6 | 47.2 | 1.2 % |

**Three numbers a critic can hold the render against.**

1. **Taper: ×2.0, and it spreads toward the observer.** 38 px at the horizon,
   75 px in the near field, over 279 rows of an 853-row frame. One band
   (519–565) is non-monotone; it is reported rather than dropped, and it is
   where a long swell crest crosses the path.
   *The ratio is taken inside one frame at one focal length, so the pixel is a
   fair unit here.* Checked rather than assumed: at 105 mm the degrees-per-pixel
   at the top band's radius and at the bottom band's differ by **0.2 %**, which
   is nothing against ×2.0. That check does **not** carry between g1 and g2 —
   see §2.3.
2. **Interior sd: 41–60 grey levels.** The render reports **1.0–2.6**. That is a
   factor of **16 to 60**. This is the single strongest number in this directory,
   because it is a *within-frame spread* — the one instrument that survives white
   balance, tone curve and grade alike.
3. **Clipping is rare, not solid: 1.2–4.4 % of core pixels reach 250.** The
   render clips across the whole path. A real path at this sun elevation is
   mostly *not* clipped; the bright facets are a small minority.

### 2.3 g2 — sun at 17° (derived), granularity at a second elevation

| band (rows) | half-max width | core mean | **core sd** | core p5 | core ≥ 250 |
|---|---|---|---|---|---|
| 478–539 (nearest horizon) | 138 px | 214.8 | 49.0 | 98.7 | 5.9 % |
| 539–601 | 125 px | 221.2 | 36.3 | 140.6 | 11.8 % |
| 601–663 | 94 px | 214.7 | 41.9 | 119.5 | 12.7 % |
| 663–724 | 98 px | 208.6 | 46.6 | 103.9 | 12.9 % |
| 724–786 | 77 px | 190.4 | 63.4 | 64.5 | 18.7 % |
| 786–848 (near field) | 89 px | 177.3 | 70.4 | 55.8 | 17.5 % |

- **Interior sd 36–70 levels** — the g1 result reproduced on a different sea, a
  different camera, a different sun elevation and a different processing chain.
  Two independent frames agreeing that the interior sd is tens of levels is
  worth more than either alone.
- **Clipping 5.9–18.7 %** — higher than g1, still nowhere near solid.
- **Width 77–138 px against g1's 38–75 px — and a pixel width does not travel
  between these two frames.** g1 was shot at 105 mm and g2 at 27 mm equivalent,
  so a pixel subtends 0.0153° in one and 0.0527° in the other. Converted
  (`angular_scale` in `measure.py`, from the EXIF focal lengths):
  **g1's path is 0.58°–1.15° wide; g2's is 4.06°–7.27°.** The high-sun path is
  about **six times wider in angle**, not twice.
  **What that six does *not* mean.** The path's angular width reads mean square
  slope, i.e. the wind (Cox & Munk). The wind is `?` for both frames, the seas
  are different (Baltic swell against a sheltered bay), and the camera heights
  differ. **The factor of six cannot be attributed to sun elevation**, and is
  recorded as a spread between two unrelated conditions rather than as a trend.

**A discrepancy, recorded and not explained away.** g2's banded width runs
138 → 89 px, i.e. it *narrows* toward the observer, the opposite of g1. I do not
have the camera height for g2, the derived sun elevation rests on a timezone
assumption, and the near-field bands may be truncated by the frame edge and by
the mangrove at the right. There is a hypothesis consistent with both frames —
the glitter region on the surface is *bounded*, and with the sun near the horizon
its near boundary recedes to the observer's feet while with a high sun that
boundary is inside the picture, so the pattern closes — but **that is derived,
not measured here, and it must not be used to make g2 agree.** *The taper
criterion is tested by g1 only. g2 is offered for granularity and for width.*

### 2.4 Granularity as a dimensionless ratio — the figure that needs no scale

Above-half-max runs and gaps along image rows, and the 1/e lag of the row
autocorrelation of high-pass luma. `l/W` is that correlation length as a
percentage of the region's own width. **It is dimensionless, so it survives
every camera failure in the table above.**

**Read the `coverage` column carefully, because it is easy to misuse.** The
threshold is per box — `p10 + ½(p99 − p10)` of *that box's own* histogram — so
coverage describes the **shape** of a distribution, not a brightness. It is
reported for completeness. **It is not a comparison against the render**, and it
cannot be: a render clipping uniformly at 255 has `p10 = p99` and the statistic
degenerates. The three columns that do the work against the render are the
**interior sd** (§2.2, §2.3), the **run and gap medians**, and **`l/W`**.

| region | box W | coverage | run med | run q90 | gap med | acf 1/e | **l/W** |
|---|---|---|---|---|---|---|---|
| g1 path, near horizon | 150 px | 21.8 % | 2 px | 26 px | 3 px | 7.6 px | **5.1 %** |
| g1 path, mid | 160 px | 21.8 % | 3 px | 19 px | 6 px | 5.3 px | 3.3 % |
| g1 path, near field | 170 px | 22.5 % | 3 px | 15 px | 6 px | 4.8 px | 2.8 % |
| g1 off-path water (control) | 200 px | 44.6 % | 4 px | 24 px | 5 px | 4.6 px | 2.3 % |
| g2 path, near horizon | 220 px | 63.6 % | 2 px | 11 px | 2 px | 1.6 px | **0.7 %** |
| g2 path, mid | 220 px | 44.6 % | 3 px | 13 px | 3 px | 2.0 px | 0.9 % |
| g2 path, near field | 220 px | 33.3 % | 3 px | 10 px | 4 px | 2.5 px | 1.2 % |
| g2 off-path water (control) | 300 px | 37.6 % | 5 px | 17 px | 9 px | 4.0 px | 1.3 % |

**The result.** Inside the glitter path the bright runs have a **median of
2–3 px** and — the half that matters — **the dark gaps between them have a median
of 2–6 px**. There is dark water between the facets at the same scale as the
facets, everywhere along the path, in both frames. The correlation length is
**0.7 % to 5 %** of the path's own width.

**Against the render.** A path whose interior varies by 1.0–2.6 levels while
clipping at 255 is flat to about one part in a hundred; there is no structure in
it for a correlation length to find, so its effective `l/W` is that of the path
itself — order **100 %**. The measured **0.7–5 %** is one and a half to two
orders of magnitude away, and the figure is dimensionless, so no scale,
white balance, tone curve or grade enters the comparison.

---

## 3 · Foam, measured

Same instruments, same file conventions.

### 3.1 The claim under test

The render draws foam as *one soft grey with a smooth gradient edge*. The bar's
section C asks for **three visually different whites** — surface deck, entrained
air that hides the bed, airborne spray — plus cusps, scallops, lace and fingers
at the edge.

### 3.2 The scale, and exactly how far it goes

Neither f1 nor f2 has a scale bar. Both have people.

- **f2**: the right-hand walker measures **124 ± 4 px** head to heel. At an adult
  stature of 1.70–1.85 m that is **67–75 px/m**; the central value used below is
  **71 px/m** (≈ 14 mm per pixel).
- **f1**: the bather measures **131 ± 4 px** from the top of his head to the
  waterline at his ankles. Taking that as 1.60–1.81 m of a 1.70–1.85 m stature
  gives **72–85 px/m**; the central value used below is **78 px/m**
  (≈ 13 mm per pixel).

**What that scale is valid for, and this matters.** Both are oblique views from
a cliff. For a camera depressed by θ below horizontal, a vertical object of
height *h* subtends `f·h·cos θ / R` while a horizontal segment *L* **across** the
line of sight subtends `f·L / R`. So:

- **Alongshore (image-horizontal) ground distances are calibrated correctly** by
  a standing person's height, to within a factor `1/cos θ` — about **+10 % at
  θ = 25°**, in the direction of over-stating the metre.
- **Cross-shore (image-vertical) ground distances are foreshortened by tan θ.**
  A person-height calibration applied to them gives a **lower bound**, and a
  loose one.

Every metric foam figure below is therefore **an alongshore measurement only**,
with a combined uncertainty of roughly **−8 % / +15 %** from stature and
obliquity together. Cross-shore sizes are not quoted.

### 3.3 Foam texture

| region | box W | coverage | run med | run q90 | gap med | acf 1/e | **l/W** | acf 1/e in metres |
|---|---|---|---|---|---|---|---|---|
| f2 stranded lace over wet sand | 500 px | 56.9 % | 3 px | 52 px | 2 px | 4.0 px | **0.81 %** | ≈ 5.6 cm |
| f2 thin foam sheet on backwash | 500 px | 22.8 % | 4 px | 20 px | 7 px | 3.8 px | 0.76 % | ≈ 5.4 cm |
| f2 thick bore whitewater | 380 px | 44.2 % | 3 px | 18 px | 3 px | 3.1 px | 0.82 % | ≈ 4.4 cm |
| **f2 dry sand (resolution floor)** | 600 px | 43.4 % | 3 px | 14 px | 3 px | **2.2 px** | 0.37 % | ≈ 3.1 cm |
| f1 sunlit bore | 500 px | 18.4 % | 2 px | 8 px | 3 px | 1.5 px | 0.29 % | ≈ 1.9 cm |
| f1 swash foam deck | 500 px | 40.4 % | 4 px | 12 px | 4 px | 2.7 px | 0.54 % | ≈ 3.5 cm |
| f1 shadowed bore | 500 px | 31.1 % | 3 px | 24 px | 2 px | 2.1 px | 0.42 % | ≈ 2.7 cm |
| **f1 unbroken water offshore (control)** | 600 px | 48.4 % | 4 px | 22 px | 5 px | 4.4 px | 0.74 % | ≈ 5.6 cm |

**Read it in this order.**

1. **The dimensionless result is the strong one.** The correlation length inside
   a foam patch is **0.3 % to 0.8 % of that patch's own width**. A soft grey with
   a smooth gradient edge varies only on the scale of the patch, so its `l/W` is
   of order 100 %. **Two and a half orders of magnitude**, and no scale, no white
   balance and no tone curve enters it.
2. **The metric result is an upper bound, and says so.** The dry-sand control
   returns 2.2 px and the offshore-water control 4.4 px — these are the
   *combined* floor of sand grain, sensor noise and JPEG at this resolution. The
   foam values, 1.5–4.0 px, sit **at or below that floor**. So `≈ 2–6 cm` is
   **an upper bound on the foam correlation length**, and the honest statement is:
   *at 1920 px, i.e. ~14 mm per pixel, this photograph does not resolve the
   bottom of the foam's structure.* Which is itself the claim under test.
3. **The larger clots do have a length.** Run q90 is 8–52 px, i.e.
   **10 cm to 70 cm alongshore**, and that is above the floor and is a real
   number. The stranded lace (q90 52 px ≈ 73 cm) is the coarsest structure and
   the sunlit bore (q90 8 px ≈ 10 cm) the finest — **the same wave carries foam
   structure over a 7:1 range of clot size at one instant.**
4. **There are dark gaps inside every "white".** The gap median is **2–7 px**
   everywhere, including inside the thickest bore. The same caution as §2.4
   applies to the `coverage` column and for the same reason: the threshold is
   per box, so it reports histogram shape and is not a comparison against a
   render. The **gap median** and **`l/W`** are the columns that are.

---

## 4 · The wet/dry sand edge, and the three whites

### 4.1 The claim under test

The bar's H3: the waterline on sand is one of the strongest tonal edges in a
coastal frame; wet sand darkens because a film traps light between surface and
substrate (the trapped series, `wet_albedo`), and the wet band also goes
specular where dry sand is matte. The render had the sign of this **backwards**
until recently and has never had a number off a real photograph.

### 4.2 The measurement, and why it is a bracket rather than a value

`linY` below inverts the sRGB EOTF. **That recovers display-referred linear, not
scene-referred linear**, so every ratio is a bound and the direction of the bound
depends on where the pair sits on the transfer curve.

**s1, nadir — no obliquity, near-planar beach, one exposure:**

| surface | sRGB mean | luma8 | linY | linR/B |
|---|---|---|---|---|
| dry sand | (239.3, 229.5, 228.1) | 231.5 | 0.8067 | 1.114 |
| wet sand band | (187.3, 184.0, 181.4) | 184.5 | 0.4858 | 1.076 |
| sea, shallow over sand | (156.9, 186.4, 180.9) | 179.7 | 0.4588 | 0.731 |
| sea, over dark rock | (153.3, 176.5, 178.4) | 171.7 | 0.4194 | 0.721 |

dry / wet = **1.66×** in display-referred linear. Both values are bright and sit
on the **shoulder** of the tone curve, where a display-referred transfer
*compresses* them toward each other. **So 1.66 is a lower bound on the scene
ratio.**

**f2, same-row pair — same range, same beach-face slope, same illumination:**

| surface | sRGB mean | luma8 | linY | linR/B |
|---|---|---|---|---|
| dry sand, upper beach | (208.4, 190.3, 163.8) | 192.2 | 0.5324 | 1.706 |
| sand, row 400–450, x 1100–1500 | (178.3, 150.1, 120.6) | 153.9 | 0.3301 | 2.347 |
| sand, row 400–450, x 220–520 | (136.2, 111.0, 88.1) | 114.7 | 0.1791 | 2.531 |
| saturated sand, swash zone | (174.2, 139.7, 109.0) | 144.8 | 0.2899 | 2.763 |

The same-row pair gives **1.84×**; upper-beach dry against saturated swash-zone
sand gives **1.84×**; upper-beach dry against the wettest sample gives
**2.97×**. This pair spans the midtone into the **toe**, where a display-referred
transfer *stretches* the pair apart. **So 1.8–3.0 is an upper bound.**

**The bracket.** Two frames, two cameras, two continents, two opposite ends of the
transfer function:

> **The scene-referred dry-to-wet sand luminance ratio is bracketed at
> 1.7× ≤ ratio ≤ 3.0×.**

That contains the ≈ 2× the wet-albedo physics predicts, and — the point — **it is
a number the render must land inside, with the sign the right way round.**

**The hue moves too, and in two different ways that must not be confused.**

- **Wet sand not covered by standing water** goes darker *and more saturated in
  its own hue*: in f2 the dry upper beach reads `linR/B` **1.706** and all three
  wetter samples read **2.35 to 2.76**. Brown gets browner, by a factor of
  **1.4–1.6**. *The ordering among the three wet samples is not monotone in
  darkness* (2.763 at `linY` 0.290, 2.531 at 0.179) and is not claimed — the
  darkest sample is partly under a thin water film, which is the next bullet's
  mechanism, not this one.
- **Sand under a water film or a foam sheet** goes darker *and bluer*, because
  the film reflects sky: f1's dry sand `linR/B` 2.291 against sand under a swash
  film at **1.153**.
- **And on white quartz-shell sand neither hue shift happens at all**: s1's wet
  and dry both sit at `linR/B` ≈ 1.08–1.11.

**A renderer with one "wetness darkens and warms" rule will get one of these
three right and the other two wrong.**

**The confound, stated.** At a sun elevation of 15–19° a change of a few degrees
in beach-face slope moves `cos(incidence)` by tens of percent. That is why the
same-row pair is the instrument here and the cross-shore ramp is not: a same-row
pair holds slope, range and illumination fixed and lets only wetness vary. s1
escapes the problem a different way, by being nadir over a near-planar face.

### 4.3 Three whites, and a fourth thing nobody asked for

f1, one exposure, five regions:

| region | sRGB mean | luma8 | **sd** | linY | linR/B |
|---|---|---|---|---|---|
| sunlit bore (entrained air) | (125.5, 156.4, 180.7) | 151.6 | 28.3 | 0.3320 | 0.485 |
| shadowed bore | (124.6, 151.9, 177.5) | 148.0 | **39.8** | 0.3303 | 0.527 |
| swash foam deck | (150.1, 159.6, 180.2) | 159.1 | **44.6** | 0.3860 | 0.687 |
| green window in the crest | (131.8, 164.3, 176.7) | 158.3 | 37.1 | 0.3743 | 0.581 |
| unbroken water offshore | (80.0, 118.1, 142.0) | 111.7 | 23.8 | 0.1759 | 0.318 |

1. **The spread inside one "white" is 28–45 grey levels of standard deviation.**
   The three whitewater regions have means within 11 levels of each other and
   standard deviations two and a half to four times that separation. **The classes are not
   separated by their means; they are separated by their texture and by what is
   visible through them** — which is exactly what the bar's section C says
   (*"if a renderer whitens without hiding what is behind, it has modelled the
   symptom"*). Do not expect to sort the three whites by level. Sort them by
   opacity and by structure.
2. **Foam is only 1.9–2.2× the unbroken water** in display-referred linear
   (0.332–0.386 against 0.176). The two values are far apart on the curve so this
   is a bound and not a value, but the *direction* is worth having: a render that
   puts foam five or ten times above the water body is outside anything this
   frame supports.
3. **The fourth thing, which was not on the target list: whitewater in this frame
   is strongly blue, not neutral.** Every whitewater region reads `linR/B`
   0.49–0.69 while dry sand **in the same exposure** reads 2.29. That is a
   within-frame ordering and it survives the caveats: a foam shader whose output
   is a desaturated grey is outside this frame by a factor of three to five in
   R/B against a sand surface it is metered with.
   **What this frame does *not* separate** is sunlit foam from shadowed foam by
   colour: the two whitewater boxes differ by 0.04 in `linR/B` (0.485 against
   0.527), which is inside the box-placement uncertainty. Recorded as a null
   result rather than as a finding, and not to be cited either way.

---

## 5 · What could not be done honestly, and why

Four of the five targets are served above. **The fifth — open-ocean colour at
depth, the deep-blue-offshore to teal-green-nearshore ladder — is not, and this
section exists so that nobody thinks it was.**

It was flagged as the weakest target before the search began, on the grounds
that colour is exactly where an unknown illuminant hurts most. The search
confirmed it, twice, with measurements:

- **b1** was chosen for the ladder. Its offshore water measures sRGB
  **(8.7, 113.1, 155.8)**. A red-channel mean of 8.7/255 across a large water
  region is a Lightroom grade sitting on the floor, not an ocean. **Colour
  refused.**
- **b2** was chosen as the backup, because it holds all five of the bar's section-J
  surfaces in one exposure. It is a **stitched panorama** graded in Photoshop,
  shot with the sun at ~5°, and the flare across its left third makes the open sea
  measure **brighter than the surf** (`linY` 0.388 against 0.304). That is
  physically impossible and it disqualifies the frame for level as well as
  colour. **Colour refused.**

**Three things about colour that this set *can* say, and their limits.** The
second is the strongest colour result in the directory and it is not about the
ladder at all — it fell out of asking the refusal question properly.

1. **s1** gives a genuine within-frame shallow-water pair: the same column over
   sand (`linY` 0.4588, `linR/B` 0.731) and over dark rock (0.4194, 0.721). Two
   surfaces close in level, one exposure, nadir — the instrument the bar says
   survives. It shows the bed *revealing* structure through the column, which is
   the shallow-bottom half of section D's confusable pair. **It does not give a
   deep-to-shallow ladder** because there is no deep water in the frame.
2. **f1 gives the section-A direction, at matched luminance, and it is the
   soundest colour result in this directory.** Section A says a thin backlit
   wave face reads green while the same water metres away reads grey-blue.
   The absolute triples cannot test that — under an unknown white balance a
   channel triple is not evidence, and in fact **neither f1 nor f2 reaches
   `G > B` anywhere in the water**, so a naive reading would call the claim
   refused.
   It is not, because the plain box mean is the wrong instrument here. `G/B`
   rises with brightness *everywhere* in this frame, including inside a single
   deep-water box with no foam in it — level and chromaticity are coupled by the
   tone curve and by the sun/sky mix. **Compare at matched luminance and the
   coupling drops out:**

   | display-referred `linY` window | crest `G/B` | water `G/B` | ratio |
   |---|---|---|---|
   | 0.24–0.30 | 0.811 (n = 1 992) | 0.721 (n = 12 713) | **1.125** |
   | 0.26–0.32 | 0.829 (n = 1 831) | 0.727 (n = 7 599) | **1.141** |
   | 0.28–0.34 | 0.841 (n = 1 470) | 0.731 (n = 4 127) | **1.150** |

   **The thin backlit crest is 1.13–1.15× greener in `G/B` than deep water of
   the same brightness in the same exposure**, stable across three windows and
   thousands of pixels each. That is a within-frame ratio between surfaces close
   in level — the one instrument the bar says survives all three camera
   failures — and it is a *direction*, not a hue.
   **f2 does not reproduce it**: its thin face reads `G/B` 0.927 against deeper
   water at 0.870–0.930, i.e. a ratio of **1.00–1.07**, which is not a result.
   Both are recorded. One frame showing the effect and one not showing it is
   what this set has, and the reader is entitled to know which is which.
3. **g3** gives the ocean-basin colour ordering — deep Atlantic, green shelf,
   turquoise bank — but it is a corrected-reflectance product, so it is a
   **map of where the ladder is**, not a measurement of the ladder.

**Conclusion for target 4: an openly-licensed photograph whose colour can be
trusted was not found, and the reason is structural rather than bad luck.** Every
well-composed coastal photograph on Commons has been graded, and the grade is
not recorded. A trustworthy colour reference needs either a raw file with a
stated development, or a frame with a neutral chart in it. Neither exists in this
corpus. **Section D's colour ladder stays where the bar left it: `?`.**

Two further gaps, recorded so they are not rediscovered:

- **No image here shows a bar-and-trough system** — break, reform, break — which
  is the bar's section B central criterion. b1 and b2 show several *separated*
  breaking lines, which is adjacent but not the same thing: a reform requires a
  calm band between two whitewater lines, and neither frame resolves one.
- **No image here shows a barrel, a plunging lip enclosing air, or an
  underwater/split view.** The bar defers those in section F for a structural
  reason and this set does not disturb that.

---

## 6 · Derived solar geometry

NOAA/Meeus low order with Bennett refraction — the same recipe the frozen bar
used on its own two dated frames, so the two are directly comparable. Elevation
and azimuth in degrees, azimuth from north.

| | elevation | azimuth | provenance and what is assumed |
|---|---|---|---|
| g1 | **0.60°** | 302.6° | EXIF time + EXIF GPS; **assumed CEST (UTC+2)** |
| g2 | 17.32° | 242.0° | EXIF time + EXIF GPS; **assumed VET (UTC−4:30**, in force 2007–2016) |
| f1 | 14.54° | 241.0° | EXIF time; **assumed WET (UTC+0**, DST ended 26 Oct 2014); **coordinates inferred from the place name, not EXIF** |
| f2 | 19.38° | 250.3° | EXIF time; **assumed WET (UTC+0**, DST began 28 Mar 2010); **coordinates inferred** |
| s1 | 14.65° | 233.6° | EXIF time + EXIF GPS; **assumed EST (UTC−5)** |
| b1 | 7.58° | 273.7° | EXIF time + EXIF GPS; **assumed CST (UTC−6)** |
| b2 | 4.81° | 236.9° | EXIF time + EXIF GPS; **assumed PST (UTC−8)** |
| r1 | 55.34° | 179.2° | EXIF time + EXIF GPS; **assumed BST (UTC+1)** |

**These are derived, not measured, and every row rests on two assumptions**: the
timezone, and the camera clock. The check is the one the bar prescribes for its
own frames — *compare the shadow directions in the picture before trusting
anything else.* g1 is the one that validates the routine independently: 0.60°
against a photograph in which the sun's disc is straddling the horizon.

Where a frame carries a value here, **a render of a comparable scene has a stated
illuminant to match.** That is a capability the bar's own H-onward frames do not
have, and it is the single largest thing this directory adds beyond the numbers.

---

## 7 · How far this lifts the visual ceiling, stated plainly so a critic need not guess

**It does not unblock the hyper-realism criterion.** Side-by-side against an
owner photograph from the owner's viewpoint remains impossible, and no image or
number in this directory bears on it.

**It does supply falsifiable numbers for four of the five fine-calibration
questions**, each of which was previously a verbal claim with nothing behind it:

| target | served by | the number a critic can hold the render against |
|---|---|---|
| glitter granularity | g1, g2, g3 | interior sd **41–60** and **36–70** levels; dark-gap median **2–6 px**; `l/W` **0.7–5 %** |
| glitter taper | g1 **only** | **×2.0**, widening toward the observer, within one frame over 279 of 853 rows |
| glitter angular width | g1, g2 | **0.58–1.15°** and **4.06–7.27°** — a spread between two unknown winds, **not** a trend in sun elevation |
| foam structure | f1, f2 | `l/W` **0.3–0.8 %**; clot q90 **10–70 cm** alongshore, a **7:1** range within one wave |
| wet/dry sand edge | s1, f2, f1 | scene ratio bracketed **1.7×–3.0×**, and three distinct hue behaviours |
| ocean colour at depth | **nothing** | **refused** — see §5 |
| *(unasked, and it turned up)* section A's green direction | f1; **not** f2 | thin backlit crest **1.13–1.15×** greener in `G/B` than deep water **at matched luminance**, one exposure |

**What it still cannot judge.** Everything in the bar that is about *this* place:
the Aljezur bar-and-trough, the reform, the eclipse-affected illuminant of the
surf frames, the platform's actual lithology, the bay's actual plan form, the
actual sediment load, the actual wind. And everything about absolute radiometry
anywhere, for the reason stated at the top and demonstrated in §5.

A verdict written against this directory can honestly say *"the render's glitter
interior is 16 to 60 times too smooth, its foam is two orders of magnitude too
correlated, its glitter tapers the wrong way against a measured ×2.0, and its
sand edge is inside or outside a bracket measured from three photographs."*
It cannot say *"it looks like Aljezur."*

---

## 8 · The bytes

Every file is the Wikimedia thumbnail at the URL below, stored verbatim. Nothing
was re-encoded, cropped or resized here, so `curl` the URL and the SHA-256 must
match. If it does not, the upstream rendition changed and every number in this
file must be recomputed with `measure.py` before it is quoted again.

| file | stored | size | SHA-256 |
|---|---|---|---|
| `b1-headland-refraction.jpg` | 1280×719 | 447 KB | `527b5b77e6852752e6b8a27d8483d6a97aea142d0c370ef33f09b2300778834f` |
| `b2-embayed-colour-ladder.jpg` | 1920×1237 | 827 KB | `d51b8e3d286237317e3f608df279fa733f8ca6a8f55ec5c366027c8913485dab` |
| `f1-breaker-three-whites.jpg` | 1920×1294 | 754 KB | `d2c58f943d3262ca2378a87860a12740524abed83e1b2a43fc8b1c50876113ef` |
| `f2-swash-foam-lace.jpg` | 1920×1172 | 542 KB | `2f6ef6586f331c6130dc44ab45251d9f774350c7357c7485e58b906d2dda7cf9` |
| `g1-glitter-lowsun-baltic.jpg` | 1280×853 | 315 KB | `89ccdb7d48aec8342fa7857b599dfb161c84e9b800a0e48fa9ade3baba194945` |
| `g2-glitter-highsun-bay.jpg` | 1280×850 | 230 KB | `094605803115a7745f73ada35edb13149e4e7f63fd5b8de23c6b8b1dbf26ac90` |
| `g3-glitter-satellite-modis.jpg` | 1280×1786 | 463 KB | `f727e670f20d5202026844aa6cdb72bfcc5c810e93b65288be002cd589ec74f2` |
| `r1-shore-platform-pockets.jpg` | 1280×720 | 457 KB | `41340979dc5238c98b964e2731f6b3da116f71f3408133268c9196cf0d816cd3` |
| `s1-wetdry-nadir.jpg` | 1280×960 | 367 KB | `bee59b57e50b1c839e7718b3b2c59a85204d72fa777c8ab7d8b55d35a89a2239` |

Thumbnail URLs, all under `https://upload.wikimedia.org/wikipedia/commons/thumb/`:

- `g1` — `a/af/K%C3%BChlungsborn%2C_Blick_von_der_Seebr%C3%BCcke%2C_Sonnenuntergang_--_2024_--_4955.jpg/1280px-K%C3%BChlungsborn%2C_Blick_von_der_Seebr%C3%BCcke%2C_Sonnenuntergang_--_2024_--_4955.jpg`
- `g2` — `d/d8/El_Guamache_Bay%2C_Margarita_island.jpg/1280px-El_Guamache_Bay%2C_Margarita_island.jpg`
- `g3` — `d/d8/Sunglint_off_the_Western_Coast_of_Africa_May_13_2012.jpg/1280px-Sunglint_off_the_Western_Coast_of_Africa_May_13_2012.jpg`
- `f1` — `0/04/Porto_Covo_Outubro_2014-3.jpg/1920px-Porto_Covo_Outubro_2014-3.jpg`
- `f2` — `2/28/Porto_Covo_March_2010-2.jpg/1920px-Porto_Covo_March_2010-2.jpg`
- `s1` — `4/45/Caspersen_Beach_top_down_aerial_view.jpg/1280px-Caspersen_Beach_top_down_aerial_view.jpg`
- `b1` — `6/61/Punta_Mango_en_El_Salvador.jpg/1280px-Punta_Mango_en_El_Salvador.jpg`
- `b2` — `7/7d/Chimney_Rock_Trail_Point_Reyes_December_2016_panorama_1.jpg/1920px-Chimney_Rock_Trail_Point_Reyes_December_2016_panorama_1.jpg`
- `r1` — `1/13/Stratified_Chalk_Cliffs_and_Tidal_Pools_at_Flamborough_Head.jpg/1280px-Stratified_Chalk_Cliffs_and_Tidal_Pools_at_Flamborough_Head.jpg`

**Two notes learned the hard way, recorded so the next agent does not pay for
them again.** Wikimedia rejects non-standard thumbnail widths with a **400 and an
HTML body** — 2048 px is rejected where 1280 and 1920 are served, so use a width
the wiki already renders, and **always `file` the result to confirm it is a JPEG
and not an error page.** And the API's `iiurlwidth` will quietly return a
*larger* pre-rendered size than the one requested; the widths above are what was
actually served, not what was asked for.

## 9 · Licence obligations, in one place

Redistribution of this directory carries these obligations. **CC0 and public
domain items are credited anyway; that is courtesy, not a requirement.**

| file | licence | attribution required | required credit |
|---|---|---|---|
| `g1` | CC BY-SA 4.0 | **yes** | Dietmar Rabich / Wikimedia Commons / «Kühlungsborn, Blick von der Seebrücke, Sonnenuntergang -- 2024 -- 4955» / CC BY-SA 4.0 |
| `g2` | CC0 1.0 | no | Wilfredo R. Rodriguez H. (Wilfredor), via Wikimedia Commons |
| `g3` | Public domain | no | NASA / MODIS Rapid Response System |
| `f1` | CC BY-SA 4.0 | **yes** | Alvesgaspar / Wikimedia Commons / «Porto Covo Outubro 2014-3» / CC BY-SA 4.0 |
| `f2` | CC BY-SA **3.0** | **yes** | Alvesgaspar / Wikimedia Commons / «Porto Covo March 2010-2» / CC BY-SA 3.0 |
| `s1` | CC BY-SA 4.0 | **yes** | Grendelkhan / Wikimedia Commons / «Caspersen Beach top down aerial view» / CC BY-SA 4.0 |
| `b1` | CC0 1.0 | no | Casa Presidencial El Salvador, via Wikimedia Commons |
| `b2` | CC BY-SA 4.0 | **yes** | King of Hearts / Wikimedia Commons / «Chimney Rock Trail Point Reyes December 2016 panorama 1» / CC BY-SA 4.0 |
| `r1` | CC BY-SA 4.0 | **yes** | TXGemGem / Wikimedia Commons / «Stratified Chalk Cliffs and Tidal Pools at Flamborough Head» / CC BY-SA 4.0 |

Six of the nine are **share-alike**. That constrains *derivative images* — a crop,
a montage, an annotated overlay published from one of these — not this file's
text and not the render. **A figure built by pasting one of these next to a
render output is a derivative and inherits CC BY-SA**, with the version taken
from the strictest input in the figure. Recorded before anyone builds one.

Nothing in this set was taken whose licence could not be stated. Candidates
found during the search and rejected for licence reasons alone: one Free Art
Licence aerial (usable but an unusual copyleft this project has no reason to
take on), and everything on stock and photographer sites, which was not
searched at all.
