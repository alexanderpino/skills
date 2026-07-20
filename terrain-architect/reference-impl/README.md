# Reference implementations

Runnable, **numpy-only, pytest-verified** mirrors of the simulation pseudocode in the
`terrain-architect` references. Every module is small and reads like its pseudocode block;
every module ships a test that asserts the *exact oracle* the skill's verification chapter
(`09-verification.md`) already specifies for it. Nothing here is production code — it exists
so a reader can **run the skill's own algorithms and watch `09`'s checks pass**, and so the
claims in the references are executable rather than merely asserted.

## Run

```bash
cd terrain-architect/reference-impl
pip install -r requirements.txt      # numpy, pytest
pytest -q                            # 37 tests, numpy-only, deterministic

# optional: cross-validate against mature libraries (RichDEM, pysheds).
pip install -r requirements-crossvalidate.txt
pytest -q                            # the 2 cross-checks now run instead of skipping
```

## What's here, and how each is verified

The verification design is **layered**: use the strongest oracle available per algorithm —
a closed-form value where one exists, otherwise `09`'s invariants (determinism, no NaN, mass
conservation, radial symmetry) and quantitative signatures, plus an optional cross-check
against an independent library.

| Module | Mirrors | Verified by (the oracle) |
|---|---|---|
| `analytic.py` — tephra thinning | `11` Pyle 1989 | `log(thickness)` linear in distance, slope `−k` |
| `analytic.py` — seafloor age–depth | `12` Parsons & Sclater 1977; Stein & Stein 1992 | matches `d₀+C√age`; GDH1 continuity + old-crust plateau |
| `analytic.py` — PDC energy cone | `11` Malin & Sheridan 1982 | runout `= Hc/μ`; inundates within runout, blocked by a ridge |
| `analytic.py` — avulsion criterion | `03` Mohrig et al. 2000 | fires at `SE≈1` with a trigger, not otherwise |
| `isostasy.py` — Airy + flexure + rebound | `02` Turcotte & Schubert; Watts; Molnar & England | exact single Fourier mode; Airy limit; analytic line-load kernel; `ρc/ρm` |
| `flow.py` — priority-flood fill | `03` Barnes et al. 2014 | no interior pit remains; fill never lowers · *xval: RichDEM* |
| `flow.py` — D8 / MFD + accumulation | `03` O'Callaghan & Mark 1984; Freeman 1991 | constant-slope routes downhill; Σarea conserved; MFD less grid-biased on a cone · *xval: pysheds* |
| `diffusion.py` — hillslope diffusion | `04`/`05` Culling 1960 | exact discrete single-mode decay; mass conserved |
| `erosion_thermal.py` — talus | `05` Musgrave et al. 1989 | converges below repose; distance-correction cuts grid bias; deterministic |
| `erosion_droplet.py` — droplet | `04` Beyer 2015 | deterministic; mass conserved; ensemble mean is radial (gullies are random, not grid) |
| `erosion_pipe.py` — virtual-pipe water | `04` Mei et al. 2007 | depth ≥ 0 (step-3 scaling) & finite on steep terrain; water conserved; 8-pipe more radial than 4-pipe |
| `erosion_streampower.py` — stream power | `04` Braun & Willett 2013; Cordonnier 2016 | **slope–area exponent = −m/n** at steady state |
| `dunes.py` — Werner slab CA | `05` Werner 1995 | slabs conserved; instability (`p_sand>p_bare`) sweeps ground bare; deterministic |

## Deliberately not reimplemented here

- **The geoscience backbone is already tested in mature libraries** — use those for
  production, don't reinvent them: **Landlab** (Hobley et al. 2017, *Earth Surf. Dynam.* 5,
  21–46), **fastscapelib / FastScape** (Braun & Willett 2013), **RichDEM** (Barnes 2016/2017),
  **pysheds** (Bartos 2020). The modules here are the pedagogical, `09`-checked mirror of the
  pseudocode, and they cross-validate against these libraries when installed.
- **D-infinity** (Tarboton 1997) — use RichDEM/pysheds; the D8/MFD pair here already shows the
  single-receiver-artefact vs dispersive contrast.
- **The pipe sediment/erosion coupling** — the water solver (where the documented NaN failure
  lives) is the verified core; the transport-capacity + semi-Lagrangian advection layer is best
  taken from a GPU implementation (the model was designed for one).
- **"Look, not a sim" processes** (coastal cliff/longshore, tides), the full MAGFLOW lava CA,
  the transient SIA glacier, and learned/ML synthesis are **excluded** — they have no decisive
  deterministic oracle, so they stay as pseudocode in the references rather than ship unverified.
