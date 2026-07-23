# Capability‑Grid Review Brief (for an external AI reviewer, e.g. Gemini)

**Companion image:** `capability_grid.png` — a 7×7 grid, 48 tiles, one per capability of the
`terrain-architect` reference implementation. **Read this brief first, then review the image against it.**

---

## 1. What you are reviewing

Each tile is a terrain field or map **generated live in pure NumPy** by a reference implementation of
a terrain‑generation skill (noise, erosion, hydrology, geology, analysis, rendering). Each caption has
two parts: **`[chapter] Capability`** and the **oracle/invariant** that the automated test suite uses to
verify it (e.g. "slope‑area exponent = −0.5 vs Landlab"). The whole suite (287 tests) passes; the
fluvial/tectonic core is cross‑validated against external libraries (RichDEM, Landlab); citations were
audited against primary sources.

Your job is **not** to check the code. It is to look at the **pictures** and tell us, per tile and
overall: does the visual match the claimed capability and its caption, is it physically plausible, what
is missing versus AAA tools, and where are the captions overclaiming.

---

## 2. Calibration — read this so you review the right thing

This is a **rigorously‑grounded reference implementation and citation authority**, deliberately **not a
shipping AAA engine**. Calibrate accordingly:

- **Resolution is intentionally small** (tiles are 120–220 px, CPU NumPy). Do **not** report low
  resolution, softness, or lack of micro‑detail as a defect — that is the sandbox tier, not the output tier.
- **Parity with Gaea / World Machine / Houdini / UE is node‑level** (same categories and phenomenology),
  **not** algorithm‑level or output‑level. Judge "does this reproduce the *kind* of landform/effect,"
  not "is this a 4K hero render."
- **Captions state the verifying *invariant*, not a beauty claim.** "Thermal ≤ repose; mass conserved"
  is a correctness statement, not "this is the prettiest talus."
- Several tiles are **explicitly illustrative** (see §6) — invariant‑checked, not benchmark‑accurate.

With that calibration, be **adversarial and specific** on everything else.

---

## 3. The five review lenses

Please evaluate the grid through these five lenses:

1. **Correctness / caption‑match** — For each tile, does the image visually support the claimed
   capability *and* its caption? Flag any tile where the picture **contradicts** the caption (e.g. a
   "concave‑up" volcano that is actually foot‑steepened, or "snow on shaded slopes" that is on the sunny
   side). These are the highest‑value findings.
2. **Physical plausibility** — Which tiles read as real geomorphology vs. procedural artifice? Call out
   artifacts: axis/grid‑aligned bias, tiling seams, unnatural regularity, hard quantise steps, radial
   symmetry that is too perfect, drainage that doesn't connect.
3. **Coverage / completeness** — Versus the Gaea/WM/Houdini node sets, which **generative, erosion, or
   analysis capabilities look missing or weak** here?
4. **Honesty** — Does any caption **overclaim** relative to what the tile shows? Is there any tile where
   the stated "test" plausibly would *not* catch a wrong result (a weak oracle)?
5. **Prioritised improvements** — The **top 5** changes that would most improve realism or coverage,
   ranked, each with the tile(s) it applies to.

---

## 4. Per‑tile checklist — what confirms it, and the red flag

Grid is row‑major (R1C1 = top‑left). For each tile: **✓** = what a correct result looks like; **✗** = the
failure mode to watch for.

### Row 1 — Noise bases (chapter 01)
| Cell | Tile | ✓ confirms | ✗ red flag |
|---|---|---|---|
| R1C1 | Perlin fBm | cloudy, natural multi‑scale relief | axis‑aligned creases; visible lattice grid |
| R1C2 | Simplex fBm | like Perlin but no directional bias | hexagonal/striped lattice showing through |
| R1C3 | Worley F2−F1 | cellular "cracked‑mud" network, thin cell edges | blobby with no cell structure |
| R1C4 | Ridged MF | sharp bright ridgelines, smooth valleys | rounded blobs (not ridged) |
| R1C5 | Hybrid MF | rough peaks, smooth basins (heterogeneous) | uniform roughness everywhere |
| R1C6 | Gabor (anisotropic) | clear **directional bands/streaks** | isotropic blobs (no orientation = broken) |
| R1C7 | Domain warp | fBm bent into swirled, flow‑like forms | undistorted plain fBm |

### Row 2 — Curl + primitives/ops (01 / 10)
| Cell | Tile | ✓ confirms | ✗ red flag |
|---|---|---|---|
| R2C1 | Curl noise | smooth swirling (divergence‑free) field | sources/sinks, blocky discontinuities |
| R2C2 | Convex‑poly SDF | clean polygonal distance field (concentric bands) | rounded circle; wrong sign inside |
| R2C3 | smooth‑min blend | two shapes fused with a smooth neck | hard crease at the join |
| R2C4 | Terrace | flat treads + sharp risers, steps that **wander** | perfectly straight contour steps |
| R2C5 | Morph closing | pit‑fill / pile‑depth map (bright in hollows) | negative values; noise unchanged |
| R2C6 | Bilateral filter | smooth regions but a **sharp preserved edge** | edge blurred away (that's a plain blur) |
| R2C7 | Twist deform | field rotated more toward the centre | uniform rotation; torn/pinched centre |

### Row 3 — Flow & erosion (03 / 04 / 05)
| Cell | Tile | ✓ confirms | ✗ red flag |
|---|---|---|---|
| R3C1 | D8 accumulation | **dendritic** drainage lines converging downslope | disconnected/parallel lines; no tree |
| R3C2 | MFD accumulation | softer, more diffuse drainage than D8 | identical to D8 (no multi‑flow spreading) |
| R3C3 | Stream power | incised valleys, concave long‑profiles | flat noise; no channel incision |
| R3C4 | Droplet erosion | carved gullies down the massif flanks | untouched terrain; or blown‑up spikes |
| R3C5 | Thermal (talus) | a cone relaxed so no slope exceeds repose | central spike, inverted pit, or explosion |
| R3C6 | Pipe erosion | incised channels **and** deposition fans/aprons | erosion only, no deposition; instability |
| R3C7 | Shallow water | water pooled/threaded in the low channels | uniform sheet; dry everywhere |
| R4C1 | Hillslope diffusion | an initial spike spread into a smooth Gaussian | still a spike; or ringing/negative halo |
| R4C2 | River meander (belt) | a sinuous channel with **asymmetric, downstream‑skewed** loops, **point/scroll bars** brightening the inner (convex) banks, and a detached **oxbow lake** (teal) | symmetric sine waves; no oxbow; a bare incised groove with no inner‑bank deposition |

### Row 4–5 — Landform generators (11) + analysis start (06)
| Cell | Tile | ✓ confirms | ✗ red flag |
|---|---|---|---|
| R4C3 | Mountain (basic) | a massif with **organised radial ridgelines** | isotropic "noise on a lump" |
| R4C4 | Mountain (eroded) | **dendritic** incised valleys (drainage network) | same as basic; or mush |
| R4C5 | Ridge (hogback) | a linear crest, **one flank steeper** than the other | symmetric ridge (asymmetry not showing) |
| R4C6 | Volcano (strato) | cone **steepest near the summit**, gentle apron, **summit crater** | foot‑steepest dome; no crater |
| R4C7 | Volcano (shield) | broad, low‑angle, convex dome | indistinguishable from the strato |
| R5C1 | Canyon | a **dominant plateau** cut by a sinuous incised gorge | whole tile carved; straight ditch |
| R5C2 | Fault‑block butte | flat top, near‑vertical cliff, talus apron, **polygonal** footprint | round hill; smooth blob |
| R5C3 | Impact crater | bowl + **raised rim** + central peak + ejecta apron | plain dimple; no rim/peak |
| R5C4 | Karst sinkholes | scattered pits **only on the soluble band** | pits everywhere; or none |
| R5C5 | Strata + fold | banded erodibility, bands **folded** (wavy), not flat | uniform field; ruler‑straight bands |
| R5C6 | Slope | steep faces bright, flats dark | inverted; uniform |
| R5C7 | Northness | pole‑/shade‑facing slopes highlighted (the snow side) | the sunny side highlighted (sign bug) |

### Row 6–7 — Masks, sims, geophysics, render (06 / 12 / 19 / 02 / 13 / 09)
| Cell | Tile | ✓ confirms | ✗ red flag |
|---|---|---|---|
| R6C1 | Curvature | ridges vs. valley floors separated by sign | flat/noisy; no ridge–valley structure |
| R6C2 | Wetness (TWI) | bright in convergent valley floors | bright on ridges (inverted) |
| R6C3 | Horizon AO | dark in hollows/valleys, ~0 (open) on peaks | uniform; or peaks darkest |
| R6C4 | Substances | snow on high/cold/**shaded**, veg on gentle, water low | snow on sunny side; colours ignore terrain |
| R6C5 | SIA glacier | smooth radial ice dome (Halfar profile) | lumpy; asymmetric; negative ice |
| R6C6 | Lava CA | a channelised flow tongue that **freezes** downstream | uniform flood; no directed flow |
| R6C7 | Coastal retreat | a notched, landward‑retreated cliff line | untouched coast; sea eroding uphill |
| R7C1 | Dunes (Werner) | dune‑like corridors/patches (deposition instability) | uniform sand; pure white noise |
| R7C2 | Isostatic flexure | a smooth broad deflection basin under the load | point‑spike; ringing |
| R7C3 | Mass‑consistent wind | smooth flow field (divergence removed) | blocky/noisy; obvious sources |
| R7C4 | Hero 3D raster | 3D massif, snow on the high core, **translucent** water, no holes | z‑fighting, gaps, opaque water, see‑through faces |

### AAA‑parity tranche (appended after the hero tile; earlier coordinates unchanged)
| Cell | Tile | ✓ confirms | ✗ red flag |
|---|---|---|---|
| R7C5 | Differential erosion (04+11) | terrain follows the **tilted beds** — resistant strata stand as **cuestas/strike ridges**, soft beds cut to valleys (anisotropic, structure‑controlled) | isotropic dendritic drainage with no bedding control (K did nothing) |
| R7C6 | Glacial carving (12) | **trunk glaciers** (pale ice) fill and flow down the valleys, thick in the trunks and thinning to their termini; ice‑free ridge between | ice sitting on ridge‑tops; uniform ice sheet; no valley‑filling flow |

---

## 5. Cross‑cutting questions we most want answered

- **Which tiles, if any, visually contradict their captions?** (Highest priority — these are real bugs.)
- **Which tiles look the most artificial**, and what specifically gives them away?
- **What generative or erosion capability is missing** that Gaea/WM/Houdini users would expect?
- **Do the landform generators** (Mountain/Ridge/Volcano/Canyon/Butte) read as their named landforms to
  a geologist's eye, or as generic bumps?
- **Is the erosion producing connected, realistic drainage networks**, or disconnected fragments?

---

## 6. Known limitations — please do NOT report these as defects

- Small reference resolution; pure‑NumPy CPU; no GPU/real‑time path implemented (design docs only).
- **Illustrative sims** — Lava CA (linear cooling, not σT⁴+crust), Coastal retreat, SIA glacier, Dunes
  (minimal Werner: no shadow‑zone/avalanche) — are **invariant‑checked, not benchmark‑accurate**, and are
  labelled as such.
- **Canyon benches** use a `floor()` quantise (a known slightly‑artificial "fake" step).
- The hero tile is a **software rasteriser** at reference resolution, not a production renderer.
- Single small tile per capability — composition/large‑extent scenes are out of scope for this grid.

---

## 7. Requested output format

1. **Per‑tile verdict table:** `tile → {matches | partial | contradicts} → one‑line note`. Only expand on
   `partial`/`contradicts`.
2. **Top‑5 ranked improvements** (biggest realism/coverage win first), each naming the tile(s) it targets.
3. **One‑paragraph overall assessment:** treating this as a *grounded reference implementation* (not a AAA
   output engine), how sound and complete is it, and what is the single most important gap?

Thank you — findings will be fed back into another audit/fix pass.
