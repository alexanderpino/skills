---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Audit
title: "Are we using the best simulations? — a grounded SOTA audit"
description: A per-process SOTA scorecard against both the commercial and the academic frontier, with the metrics that would settle each verdict.
tags: [terrain, sota, simulation]
status: stable
generated: { by: process:claude-code, at: 2026-07-25T19:04:00Z }
# --- end okf v0.2 ----------------------------------------------------
---
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
| **Tectonic / orogeny** | isostasy + SPL uplift + **fault scarps, fault-as-K & a Voronoi plate sim** (`tectonics.py`) | Cordonnier 2016 uplift+fluvial; Sculpting Mountains 2018 | **SOTA & ahead of all commercial tools** | foreground it; optional flexural isostasy / folds |
| **Thermal / hillslope** | Musgrave 1989 angle-of-repose talus **+ linear hillslope diffusion coupled inside the SPL solver** (`stream_power_evolve(D=)`, Cordonnier's companion term; scalar or field `D`) | repose (rock) + linear diffusion (Culling) **+ nonlinear diffusion** Roering 1999 (soil creep) | **solid**; linear coupling done, nonlinear still missing | add the Roering 1999 nonlinear (slope-dependent) closure beside the linear term |
| **Aeolian (dunes + abrasion)** | Werner 1995 slab CA **+ yardang wind abrasion** (`aeolian.yardang`, Ward & Greeley 1984) | Desertscape (Paris 2019): abrasion, reptation, dune types; GPU 2023 | **solid, not SOTA** (still ahead of the tools) | adopt Desertscape extensions |
| **Glacial** | SIA shallow ice **+ `glacierStep` bed abrasion** (`glacier.glacier_carve`; ice was flow-only before) | Cordonnier 2023 *Forming Terrains by Glacial Erosion* + IGM learned flow (Jouvet 2022) | **solid, superseded for accuracy** | min: hybrid SIA+SSA + implicit solve (explicit is stiff on rough beds); frontier: IGM emulator + multi-scale advection |
| **Coastal** | simple cliff retreat | SCAPE (Walkden & Hall 2005) — no strong CG SOTA | **pragmatic / acceptable** | wave-energy platform down-wearing + talus feedback |
| **Sediment / deposition** | **now: `erosion_pipe.pipe_erode`** (Mei-2007 coupled flow+sediment, conserved) + droplet; SPL still detachment-only | conserved sediment field (Šťava 2008 … Schott 2024, McDonald 2026) | **gap closed** for the pipe model (fans/deltas/fill + mass conservation); SPL core still detachment-limited | add the transport-limited closure to the SPL stage too |
| **Flow routing / hydrology** | D8 + MFD + priority-flood (× RichDEM/pysheds/Landlab) | + D-infinity (Tarboton 1997); Fill-Spill-Merge (Barnes 2020) for real lakes; FastFlow 2024 | **current / solid** | optional D-∞; **Fill-Spill-Merge** for real lakes vs filled-flat |
| **Karst caves** | **surface karst only** — `landforms.karst_sinkholes` (dolines at blue-noise points on soluble rock, lognormal size distribution per Williams 1972 / Denizman 2003, returning the `sink_mask` of pits `03` must *not* fill) and `archetypes.tower_karst`; **no subsurface conduits** | Paris 2021 geologically-coherent cave networks | **gap** for the *caves* (if in scope) — the surface expression ships and is tested (`tests/test_landforms.py`); what is absent is the 3-D network | anisotropic-shortest-path conduits + SDF, coupled to the existing `sink_mask` as inlets |
| **Lava flow** | **thermo-rheological grid CA** — `sims_illustrative.lava_flow` (`19`): temperature-dependent Bingham yield gate `τ_y = max(τ_y0 + gain·(T_solidus − T), 1)`, flux `q = k(τ−τ_y)L²/η` only where `τ > τ_y`, heat advected with the mass, freeze-to-bedrock, mass budget closed (Miyamoto & Sasaki 1997, C&G 23:283) | MAGFLOW (flux law derived from a steady-state Bingham Navier–Stokes solution; INGV, operational at Etna) / MOLASSES; FLOWGO 1-D channel heat budget; SPH thermal flow | **solid, not SOTA** — the model class this row used to *ask for* already ships. Caveat: it is **illustrative-tier** (invariant-checked, no decisive oracle — the README coverage boundary), so "solid" is about the model, not about verified numbers | four *specific* deltas vs MAGFLOW / Miyamoto & Sasaki, none of them "write the CA": **(1) Monte-Carlo neighbour selection** — M&S's actual contribution, the fix for lattice quantisation; ours is a deterministic D8 proportional split. **(2) radiative cooling `εσ(T⁴−T_env⁴)` + crust insulation** — ours is a uniform linear `cool·dt`, so there is no margin/core cooling asymmetry and hence **no emergent levées**. **(3) `η(T)`** — ours is a constant `eta`. **(4)** MAGFLOW's NS-derived flux law — ours is the ad-hoc Bingham form |
| **Debris runout** | Voellmy 1955 | Jain/Beneš/Cordonnier 2024 debris-flow | **solid** | frontier watch |

⚠️ **The lava row was wrong on both halves, and it is the drift this document exists to avoid.** It
read *"ours = ejecta CA only … **gap** … upgrade: thermo-rheological CA"*. Verified 2026-08-30:

- **The thermo-rheological CA already ships.** `sims_illustrative.py:28–78` is a temperature-carrying
  Bingham CA (`tau_y = np.maximum(tau_y0 + tau_y_gain * (T_solidus - T), 1.0)` at line 47; the flux is
  gated on `tau > tau_y` at line 53). It is tested (`tests/test_sims_illustrative.py`, 7 passed),
  dimensionally audited (`tests/test_dimensional.py::test_lava_bingham_flux_is_area_per_time`, the
  Bingham-flux row of [`VALIDATION.md`](VALIDATION.md)'s rung-1 table), citation-audited to Miyamoto &
  Sasaki 1997 in that document's rung-4 table, drawn as **gallery panel 30** and as the
  `capability_grid.py` tile *"19 Lava CA"*, and written up as runnable pseudocode in
  `references/19-lava.md`.
- **There is no "ejecta CA" anywhere in the repo.** The only ejecta model is `crater.py`'s blanket —
  an analytic, mass-conserving `r^-3` deposit with an azimuthal weight (`crater.py:61,109–121`), not a
  cellular automaton, and unrelated to lava.

A reader planning work off the old row would have rebuilt a shipped, tested module — precisely the
failure `tests/test_audit_drift.py` was written for after the braided-river drift. That harness does
not currently cover `SIMULATION-AUDIT.md`; a row for it would have caught this one.

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

1. **Conserved sediment / deposition field** — **DONE** via `erosion_pipe.pipe_erode` (Mei-2007 coupled
   flow+sediment: fans, deltas, valley fill, mass-conserved). Remaining: add a transport-limited closure to
   the *stream-power* stage too, and feed the deposition field into the texture masks. (Landlab **SPACE** is
   the cross-validation oracle.)
2. **Layered material representation** (bedrock/regolith/sediment/water/snow). Unlocks #1 *and* seasons; it's the
   Houdini/Beneš-2001 representation. Prereq for dynamics.
3. **Nonlinear hillslope diffusion** (Roering 1999) beside the repose CA. The **linear** half is now done —
   `stream_power_evolve(D=)` couples `+D∇²h` inside the solver, giving the standard "SPL channels + diffusion
   hillslopes" LEM and a measured handle on valley spacing (3.32→9.76 cells) and divide roughness
   (1.41→0.05). What remains is the slope-dependent `q ∝ ∇h / (1 − |∇h|²/S_c²)` closure, which is what makes
   the **PSD spectral break** appear (Part 3's top discriminator).
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
Paris et al. 2021 *Caves* (CGF, 10.1111/cgf.14420); Miyamoto & Sasaki 1997 (Computers & Geosciences 23:283 — the lava CA this skill implements,
citation-audited ✅ in `VALIDATION.md`); Harris & Rowland 2001 *FLOWGO* (Bull. Volcanol. 63) and **MAGFLOW** (INGV Catania), both as named in
`references/19-lava.md`; Tarboton 1997 (WRR, 10.1029/96WR03137); Barnes et al. 2014 *Priority-Flood* (C&G);
Barnes et al. 2020 *Fill-Spill-Merge* (ESurf); Jain et al. 2024 *FastFlow* (CGF, 10.1111/cgf.15243); Walkden & Hall 2005 *SCAPE* (Coastal Eng.).
Metrics & validation: Hack 1957; Horton 1945; Strahler 1952; Montgomery & Dietrich 1992 (Science); Whipple & Tucker 1999 (JGR);
Rigon et al. 1996 (WRR); Perron et al. 2008 (JGR, 10.1029/2007JF000866); Jasiewicz & Stepinski 2013 (Geomorphology); Rajasekaran et al.
2022 *PTRM* (TAP, 10.1145/3514244); Hobley et al. 2017 & Barnhart et al. 2020 (Landlab, ESurf); Schwanghart & Scherler 2014 (TopoToolbox, ESurf);
Hawker et al. 2022 (FABDEM). Texture: Andersson 2007 *Frostbite* (SIGGRAPH courses); Heitz & Neyret 2018 (HPG); Mikkelsen 2022 (JCGT);
Guérin et al. 2017 (TOG, 10.1145/3130800.3130804); Higo et al. 2025 *TerraFusion*; Burley 2012 / Karis 2013 (PBR). Survey anchor: Galin et al.
2019 *A Review of Digital Terrain Modeling* (CGF, 10.1111/cgf.13657). Tool docs: QuadSpinner Gaea, SideFX Houdini (HeightField Erode), World Machine.
Full URLs are in the research transcripts backing this document.
