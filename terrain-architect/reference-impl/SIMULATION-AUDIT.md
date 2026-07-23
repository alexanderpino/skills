# Are we using the best simulations? — a grounded SOTA audit

*How to find out whether each simulation in this skill is best-in-class, how to measure it objectively,
and where the gap to Gaea / World Machine / Houdini (and to the academic frontier) actually is.*
Compiled from a survey of the terrain-modelling literature and the pro tools' documented behaviour
(sources at the end). It answers three questions: **what's SOTA per stage, what do we use, and how do we
measure the difference.**

## Two frontiers — don't conflate them

- **Commercial frontier (Gaea, World Machine, Houdini):** interactive, *elevation-domain*, artist-driven,
  and almost entirely **proprietary/undocumented**. We can claim *node-level* parity, not algorithm parity.
- **Academic frontier:** one lab cluster (Inria/LIRIS/Purdue — Cordonnier, Galin, Guérin, Paris, Peytavie,
  Beneš) plus the geoscience LEM community (Braun/Willett, Landlab/Fastscape). This is the **harder** bar,
  and it's what the verdicts below are measured against.

**Meta-finding:** our fluvial/tectonic/hydrology spine is genuinely strong — *ahead of every shipping
commercial tool* on tectonic-uplift LEM, aeolian, and glacial (none of the three ship those as real
process simulations) — but *behind the 2023–2026 academic frontier*, which sits almost entirely in
deposition-aware transport, learned glacial flow, and multi-scale erosion.

---

## Part 1 — Representation (and why "voxels" is the wrong default)

| Tier | Represents | Cannot | Who uses it |
|---|---|---|---|
| **Single heightfield (2.5D)** | one z per column; all fluvial/thermal erosion | overhangs, caves, arches | our sandbox today; the baseline |
| **Layered heightfield / material stack** | bedrock + regolith + sediment + **water** + **snow** as stacked 2D layers → deposition, seasons | still no true overhangs | **Houdini's actual model**; Beneš & Forsbach 2001; Šťava 2008; Cordonnier |
| **Voxel / SDF (true 3D)** | overhangs, caves, arches | (cost is the limit: O(n³)) | Infinigen, No Man's Sky; Houdini *only* via VDB for a specific feature; Paris 2019 does it as **local** implicit amplification |

**Verdict — "layered heightfield by default, local voxel/SDF only for genuine 3D features" is the published
SOTA position** (Beneš 2001 → Peytavie 2009 *Arches* → Paris 2019). Voxels-for-everything is wrong (unjustified
O(n³) when >95 % of a landscape is heightfield-expressible). **Seasons do NOT need voxels** — melting snow,
filling/drying rivers = extra *scalar layers + a time integrator*, not a third spatial dimension
(Cordonnier 2018 snow w/ 4 snow phases + degree-day melt; Argudo 2020 glaciers forced by temp/precip;
Šťava 2008 water layer that floods and dries). The only thing that forces voxels is a change of *topology*
(a collapsing arch, a newly opened cave). **Our gap:** we're at the single-heightfield rung — the upgrade
that unlocks both real deposition *and* seasons is a **layered material stack**.

---

## Part 2 — Per-process simulation scorecard

Verdict scale: **SOTA** · **solid (not SOTA)** · **superseded** · **gap**. "Upgrade" names the concrete next step.

| Process | Ours | Academic SOTA | Verdict | Upgrade |
|---|---|---|---|---|
| **Fluvial (large-scale)** | stream-power incision, Braun & Willett 2013 (×-validated vs Landlab) | Cordonnier 2016 uplift+SPL; Schott 2023 interactive; McDonald & Cordonnier 2026 momentum particles | **SOTA core** — but **detachment-limited: incises, never deposits** | add a transport-limited / sediment-flux closure (see deposition) |
| **Hydraulic (detail/interactive)** | Lagrangian droplet (Beyer/Lague) | Eulerian virtual-pipe (Mei 2007), SPH (Krištof 2009) | **solid, not SOTA** | keep as a fast detail pass; don't make physical claims on it |
| **Tectonic / orogeny** | (isostasy only) + SPL | Cordonnier 2016 uplift+fluvial; Sculpting Mountains 2018 | **SOTA & ahead of all commercial tools** | foreground it; optional flexural isostasy / folds |
| **Thermal / hillslope** | Musgrave 1989 angle-of-repose talus | repose (rock) **+ nonlinear diffusion** Roering 1999 (soil creep) | **solid, partly superseded** | add linear+nonlinear hillslope diffusion beside the repose CA |
| **Aeolian (dunes)** | Werner 1995 slab CA | Desertscape (Paris 2019): abrasion, reptation, dune types; GPU 2023 | **solid, not SOTA** (still ahead of the tools) | adopt Desertscape extensions |
| **Glacial** | SIA shallow ice (~2020 CG level) | Cordonnier 2023 *Forming Terrains by Glacial Erosion* + IGM learned flow (Jouvet 2022) | **solid, superseded for accuracy** | min: hybrid SIA+SSA; frontier: IGM emulator + multi-scale advection |
| **Coastal** | simple cliff retreat | SCAPE (Walkden & Hall 2005) — no strong CG SOTA | **pragmatic / acceptable** | wave-energy platform down-wearing + talus feedback |
| **Sediment / deposition** | droplet deposits; **SPL does not** | conserved sediment field is table-stakes (Šťava 2008 … Schott 2024, McDonald 2026) | **superseded (erosion-only)** | **#1 gap:** explicit conserved sediment/alluvium field → fans, deltas, valley fill |
| **Flow routing / hydrology** | D8 + MFD + priority-flood (× RichDEM/pysheds/Landlab) | + D-infinity (Tarboton 1997); Fill-Spill-Merge (Barnes 2020) for real lakes; FastFlow 2024 | **current / solid** | optional D-∞; **Fill-Spill-Merge** for real lakes vs filled-flat |
| **Karst caves** | — (prose only) | Paris 2021 geologically-coherent cave networks | **gap** (if in scope) | anisotropic-shortest-path conduits + SDF |
| **Lava flow** | ejecta CA only | MAGFLOW/MOLASSES CA or SPH thermal flow | **gap** (if in scope) | thermo-rheological CA or shallow-water thermal |
| **Debris runout** | Voellmy 1955 | Jain/Beneš/Cordonnier 2024 debris-flow | **solid** | frontier watch |

---

## Part 3 — How to measure it (the instrument, not opinion)

Realism isn't one number; it's a **coupled set of scaling laws** that erosion produces and fbm/noise does not.
Build (or extend `test_empirical.py`) a harness that computes this vector on our output **and** on matched real
DEM tiles, and report a per-metric distance:

| Metric | Real-Earth target | Source |
|---|---|---|
| **Slope–area concavity θ** (`S = k·A^−θ`) | **θ ≈ 0.4–0.6** *with a process-domain break* | Whipple & Tucker 1999; Montgomery & Dietrich 1992 |
| **Hack's law** (`L = c·A^h`) | **h ≈ 0.56–0.6** | Hack 1957; Rigon 1996 |
| **Horton ratios** (R_b, R_L, R_A) | **R_b 3–5, R_L 1.5–3.5, R_A 3–6**, ~const across orders | Horton 1945; Strahler 1952 |
| **Hypsometric integral** | **HI ≈ 0.3–0.6** | Strahler 1952 |
| **PSD slope β / fractal D** | **β ≈ 2–3 with a non-fractal spectral break** (a characteristic hillslope scale) | Perron et al. 2008 |
| **Drainage density** | climate/lithology-dependent; internal consistency + correct channel-head threshold | Montgomery & Dietrich 1992 |
| **Geomorphon histogram** | KL-divergence vs a matched real tile | Jasiewicz & Stepinski 2013 |
| **Perceived realism (PTRM)** | 2AFC / geomorphon features | Rajasekaran et al. 2022 |

**Strongest discriminators** ("real" vs "procedural"), in order: (1) **slope–area organization with a
process-domain break** — pure noise has *none*; (2) a **real channel network** passing Hack + Horton;
(3) a **non-fractal characteristic scale in the PSD** (the top reason multifractal terrain "looks procedural").

**Oracles.** Cross-validate correctness against **RichDEM** (priority-flood, accumulation), **TopoToolbox 2**
(networks, χ-analysis), **pysheds**, **Landlab** (FlowAccumulator, FastscapeEroder, LinearDiffuser, SPACE),
**fastscapelib** (SPL analytical steady state: `S=(U/K)^{1/n}A^{-m/n}`, straight χ–elevation). Compare
statistics against real tiles from **Copernicus GLO-30 / FABDEM / USGS 3DEP**. We already do the correctness
half for flow/erosion (`GROUNDING.md`, `test_crossvalidate*`, `test_empirical.py`) — the gap is the **full
metric vector vs matched real DEMs**, per stage.

**Per-stage scorecard shape:** base (PSD β, no channels yet) → flow routing (bit-compare vs RichDEM) →
fluvial (θ≈0.5, χ-linear, Hack h) → hillslope (spectral break appears) → deposition (fans, HI shift, mass
balance) → full-basin (metric vector vs real) → perceptual (PTRM). Each row names a *reference*, so the
verdict is "stage 2 SOTA, stage 4 partial", not one opaque score.

---

## Part 4 — Texture / material (what separates a pro splat from ours)

Five separable upgrades over a naive slope+height splat, all documented in the tools/literature:

1. **Simulation-driven masks**, not raw geometry: flow, sediment/deposition, wetness, curvature, cavity/AO,
   thermal debris, snow (Houdini exposes `flow`/`sediment`/`debris`/`water` for exactly this). *We do part of
   this* — our substance model uses slope+aspect+curvature+flow; it does **not** yet use a real deposition/wear
   field (we have no conserved sediment field — see Part 2).
2. **Real-world colour** (Gaea SatMaps = ~1400 CLUTs sampled from satellite imagery) *and/or* **PBR material
   sets** (albedo/normal/roughness/AO/height; Burley 2012, Karis 2013). *We have* a CLUT (`render.satmap`) and a
   substance model; *we lack* PBR channels.
3. **Height-based blending** (tallest material wins with a soft threshold), not alpha — interfingered, not decal.
4. **Macro / meso / micro detail** decomposition (Andersson/Frostbite 2007). *We have* macro only.
5. **Anti-tiling**: hex-tiling (Mikkelsen 2022) or histogram-preserving blending (Heitz & Neyret 2018) +
   triplanar. *N/A at our tile scale, needed for close-up.*

**Frontier:** example-based (Guérin 2017 cGAN) and coupled shape+texture diffusion (TerraFusion 2025).

---

## Part 5 — Prioritised gaps (the roadmap this audit produces)

1. **Conserved sediment / deposition field** on the stream-power core (fans, deltas, valley fill). *Highest value*
   — it's table-stakes SOTA, fixes the erosion-only tell, and feeds the texture masks. (Landlab **SPACE** is the
   cross-validation oracle.)
2. **Layered material representation** (bedrock/regolith/sediment/water/snow). Unlocks #1 *and* seasons; it's the
   Houdini/Beneš-2001 representation. Prereq for dynamics.
3. **Nonlinear hillslope diffusion** (Roering 1999) beside the repose CA → the standard "SPL channels + diffusion
   hillslopes" LEM, and it's what makes the **PSD spectral break** appear (Part 3's top discriminator).
4. **The realism-metric harness** (slope–area θ, Hack h, Horton, HI, PSD-break, geomorphons) vs matched real
   DEMs. *This is the instrument that answers "are we best" continuously* — build it before chasing more features.
5. **Texture:** feed the new deposition/wear field into the substance masks; add PBR channels + anti-tiling for
   close-up.
6. **Seasons (if pursued):** layered state + degree-day snowmelt + water-balance discharge (Cordonnier 2018;
   Hock 2003) — a genuine differentiator, since Gaea/WM only bake static snapshots (only Houdini iterates state).
7. **Frontier watch (adopt later):** Schott 2023/2024 (interactive + multi-scale erosion), McDonald & Cordonnier
   2026 (momentum particles, braided rivers), Cordonnier 2023 + IGM (glacial), Fill-Spill-Merge (real lakes).

**Honest ceiling:** the sandbox is an *illustrative, verified reference*, not an engine — the realistic goal is
that **every method it teaches is the SOTA-or-best-grounded one, with the gap measured**, which this audit now
makes explicit. True tool-parity output (multi-scale detail, PBR, streaming) is a separate engine, itemised in
`HYPERREALISM.md`'s ceiling.

---

## Sources

Representation & dynamics: Beneš & Forsbach 2001 (SCCG); Peytavie et al. 2009 *Arches* (CGF, 10.1111/j.1467-8659.2009.01385.x);
Šťava et al. 2008 (SCA); Becher et al. 2019 (TVCG); Paris et al. 2019 *Implicit 3D Features* (TOG, 10.1145/3342765);
Cordonnier et al. 2018 *Snow* (CGF, 10.1111/cgf.13379); Argudo et al. 2020 *Glaciers* (TOG, 10.1145/3414685.3417855);
Cordonnier et al. 2017 *Ecosystems+Erosion* (TOG); Losasso & Hoppe 2004 *Geometry Clipmaps*; Mei et al. 2007 (PG, 10.1109/PG.2007.15).
Process SOTA: Braun & Willett 2013 (Geomorphology, 10.1016/j.geomorph.2012.10.008); Cordonnier et al. 2016 (CGF, 10.1111/cgf.12820);
Schott et al. 2023 (TOG, 10.1145/3592787) & 2024 multi-scale (10.1145/3658200); McDonald & Cordonnier 2026 (TOG, 10.1145/3811336);
Musgrave et al. 1989 (SIGGRAPH); Roering et al. 1999 (WRR, 10.1029/1998WR900090); Werner 1995 (Geology); Paris et al. 2019 *Desertscape*
(CGF, 10.1111/cgf.13815); Cordonnier et al. 2023 *Glacial Erosion* (TOG, 10.1145/3592422); Jouvet et al. 2022 *IGM* (J. Glaciology);
Paris et al. 2021 *Caves* (CGF, 10.1111/cgf.14420); Tarboton 1997 (WRR, 10.1029/96WR03137); Barnes et al. 2014 *Priority-Flood* (C&G);
Barnes et al. 2020 *Fill-Spill-Merge* (ESurf); Jain et al. 2024 *FastFlow* (CGF, 10.1111/cgf.15243); Walkden & Hall 2005 *SCAPE* (Coastal Eng.).
Metrics & validation: Hack 1957; Horton 1945; Strahler 1952; Montgomery & Dietrich 1992 (Science); Whipple & Tucker 1999 (JGR);
Rigon et al. 1996 (WRR); Perron et al. 2008 (JGR, 10.1029/2007JF000866); Jasiewicz & Stepinski 2013 (Geomorphology); Rajasekaran et al.
2022 *PTRM* (TAP, 10.1145/3514244); Hobley et al. 2017 & Barnhart et al. 2020 (Landlab, ESurf); Schwanghart & Scherler 2014 (TopoToolbox, ESurf);
Hawker et al. 2022 (FABDEM). Texture: Andersson 2007 *Frostbite* (SIGGRAPH courses); Heitz & Neyret 2018 (HPG); Mikkelsen 2022 (JCGT);
Guérin et al. 2017 (TOG, 10.1145/3130800.3130804); Higo et al. 2025 *TerraFusion*; Burley 2012 / Karis 2013 (PBR). Survey anchor: Galin et al.
2019 *A Review of Digital Terrain Modeling* (CGF, 10.1111/cgf.13657). Tool docs: QuadSpinner Gaea, SideFX Houdini (HeightField Erode), World Machine.
Full URLs are in the research transcripts backing this document.
