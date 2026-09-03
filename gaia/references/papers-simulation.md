---
type: Bibliography
title: Papers — simulation and water
description: "Sources behind Gaia's water and simulation documents, each graded by provenance tier."
tags: [bibliography, provenance, water, simulation]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Papers — simulation and water

The bibliography family for the simulation axis: the time-budget spine, the closed/open taxonomy,
wave models, shallow-water solvers and water optics. **The tier table, the two non-negotiable rules
and the attribution corrections live in `papers-flow.md`** and are not repeated here; read them
before citing anything below.

Two tier decisions recur in this family and are stated once:

- **A book, a thesis, a set of course notes or a talk is graded `F`, not `P`**, however canonical it
  is. Tessendorf's ocean notes and Born & Wolf are the load-bearing examples. Naming them is right;
  dressing them as peer review is not.
- **A number that this repository's own sources record as unread or unverified is not cited at
  all.** The Elfouhaily unified spectrum is the case: `water-physics/references/12b-water-provenance.md`
  records that the paper is paywalled and was not read, so `wave-models.md` names it in prose rather
  than manufacturing a `P`.

⚠️ **`water-physics/` is not in this repository.** Three entries below (`bodytype_doctrine`,
`iop_split`, and the Elfouhaily note above) point into `water-physics/references/`, which exists
only on the unmerged branch `origin/claude/swimming-pool-voronoi-render-m22g6r` — not on `main` and
not on this branch. `check.py` checks the form of attribution and cannot detect a dangling
cross-skill path, so it is stated here in prose. Wherever such a pointer is load-bearing, the
substance is restated inline in the citing document, so nothing depends on that branch ever being
merged.

## Numerical stability and time stepping

- **courant1928** `P` — Courant, R., Friedrichs, K. & Lewy, H. (1928). *Über die partiellen Differenzengleichungen der mathematischen Physik.* Mathematische Annalen 100, 32–74. — The origin of the stability condition that carries their initials: a difference scheme's numerical domain of dependence must contain the physical one.
- **stam1999** `P` — Stam, J. (1999). *Stable Fluids.* SIGGRAPH '99 Conference Proceedings, 121–128. — Semi-Lagrangian advection by the method of characteristics; unconditionally stable in the advection term, at the price of numerical dissipation and a pressure projection that is still a global solve.
- **explicit_diffusion_limit** `F` — No canonical paper. Von Neumann stability analysis of the explicit (FTCS) discretisation of `∂u/∂t = ∇·(D∇u)` gives `Δt ≤ Δx²/(2D)` in one dimension and `Δx²/(4D)` in two; standard in any numerical-methods text. Quoted here because the 1-D form is the one that circulates, and using it on a 2-D grid is unstable by a factor of two. [no-artefact]
- **fiedler_timestep** `F` — No canonical paper. The fixed-step accumulator — integrate a constant `dt`, accumulate leftover wall-clock time, never integrate a frame-derived step — is universal game-loop practice; the reference most implementers have actually read is Glenn Fiedler's *Fix Your Timestep!* on gafferongames.com. A blog post, cited as one.

## Heightfield water solvers

- **kass1990** `P` — Kass, M. & Miller, G. (1990). *Rapid, Stable Fluid Dynamics for Computer Graphics.* SIGGRAPH '90, Computer Graphics 24(4), 49–57. — The founding heightfield water paper: the linearised shallow-water equations integrated implicitly with alternating tridiagonal sweeps. A global solve per step — that half is exact. It does **not** claim unconditional stability: it derives stability from implicitness, then *freezes the depth `d` within a step*, which it says "virtually ensures that the iteration will not diverge". That is a weaker and more honest claim than the one this entry used to make, and the frozen-depth linearisation is the reason for it.
- **steadystate_discharge** `F` — No canonical graphics paper. Under uniform runoff a mass-conserving surface-water solver converges to `Q = rain × upstream contributing area` — the rational method of engineering hydrology. Stated, implemented and tested as `discharge_from_area` in terrain-architect's `reference-impl/hydrology.py`, which is the checkable form. [no-artefact]
- **fluid_authority** `F` — No external source. The contract that every fluid effect is either cosmetic GPU state or authoritative gameplay liquid state, with no automatic promotion between them, is terrain-renderer `19-fluid-simulation.md`'s doctrine. [no-artefact]

## Body classification

- **bodytype_doctrine** `F` — No external source; a convention this repository recommends, not a finding. The authored `bodyType` enum, the gate table that flips nearly every water default between natural and man-made bodies, and the driven-basin model of a closed body's wave field are the doctrine of `water-physics/references/12-water-physics.md` — ⚠️ **a file that is not in this repository**: it is on the unmerged branch `origin/claude/swimming-pool-voronoi-render-m22g6r`, not on `main`. That chapter marks its own phrase "driven basin" as a term it coined rather than a term of art, and marks the wall reflection coefficient as unmeasured; both marks are carried into the prose of `water-closed-vs-open.md`, which also states the gate table's doctrinal status inline so it stands without the branch. [no-artefact]
- **beaufort** `F` — Observational scale, not a paper. The Beaufort wind force scale with the standard sea-state descriptions; the wording used in Gaia is NOAA's Storm Prediction Center table. Whitecaps first at Force 3, spray at Force 5, foam streaks at Force 7. Adoption dates for the related Douglas and WMO sea-state codes conflict across secondary sources and are deliberately not stated.
- **lamb_damping** `F` — Lamb, H. *Hydrodynamics.* — The deep-water viscous decay rate of a free-surface wave, `α = 2νk²`, from which the e-folding distance follows against the group speed. A textbook, not a paper.

## Waves

- **capillary_gravity** `F` — Classical fluid mechanics, no single canonical paper. The capillary–gravity dispersion relation `ω² = (gk + (σ/ρ)k³)·tanh(kh)` and its minimum phase speed, `c_min = (4gσ/ρ)^¼` at `λ_min = 2π√(σ/ρg)`. ⚠️ Declare `σ` once and derive both halves: the widely-quoted pair 23.1 cm/s at 1.73 cm implies two surface tensions 2.5% apart, and each half is defensible alone, which is why the mismatch survives being checked. [no-artefact]
- **gerstner_trochoid** `F` — Classical 19th-century fluid mechanics (F. J. Gerstner, 1802); no modern canonical paper. The trochoidal wave with coupled horizontal and vertical displacement. The standard practical implementation reference is Finch, M., *Effective Water Simulation from Physical Models*, GPU Gems ch. 1 (2004) — a book chapter, cited as one.
- **tessendorf_ocean** `F` — Tessendorf, J. *Simulating Ocean Water.* SIGGRAPH course notes (2004 revision public). — Spectrum sampling into a frequency grid, inverse-FFT displacement, choppiness, Jacobian folding: the canon for every spectral ocean shipped since. Course notes, not peer review, and graded accordingly.
- **airy_coastal** `F` — Linear (Airy) wave theory and coastal-engineering canon; no single citable paper for the set. The dispersion relation `ω² = gk·tanh(kh)`, Green's shoaling law `a ∝ h^(−1/4)`, the McCowan-type breaker index `H ≈ 0.78h`, and the surf-similarity (Iribarren) number `ξ = tanβ/√(H/L₀)`. Each has a 19th- or 20th-century origin; Gaia has verified none of those originals and grades the set as canon rather than attributing it. [no-artefact]
- **yuksel2007** `P` — Yuksel, C., House, D.H. & Keyser, J. (2007). *Wave Particles.* ACM TOG 26(3) (SIGGRAPH 2007). — Lagrangian carriers of wave energy advected over the domain and rasterised into a displacement field; each particle a wavefront segment that subdivides as fronts spread.

## Water optics

- **popefry1997** `P` — Pope, R.M. & Fry, E.S. (1997). *Absorption spectrum (380–700 nm) of pure water. II. Integrating cavity measurements.* Applied Optics 36(33), 8710–8723. — The modern pure-water absorption spectrum; minimum 0.0044 m⁻¹ at 417.5 nm rising to 0.624 m⁻¹ at 700 nm. ⚠️ Do **not** use Smith & Baker (1981) for blue absorption — scattering contamination puts its `a(420)` about 3.4× too high; Smith & Baker remains correct below 380 nm and for `K_d`.
- **braun1993** `P` — Braun, C.L. & Smirnov, S.N. (1993). *Why is water blue?* Journal of Chemical Education 70(8), 612. — Water's visible absorption is the high-order overtone band of the O–H stretch: vibrational spectroscopy, not sky reflection.
- **lee2015** `P` — Lee, Z., Shang, S., Hu, C., Du, K., Weidemann, A., Hou, W., Lin, J. & Lin, G. (2015). *Secchi disk depth: A new theory and mechanistic model for underwater visibility.* Remote Sensing of Environment 169, 139–149. — Shows the classical Secchi relation is not derivable from radiative transfer and replaces it with `Z_SD ≈ 1/min_λ K_d`: the bridge from an artist's visibility dial to inherent optical properties.
- **nicodemus1963** `P` — Nicodemus, F.E. (1963). *Radiance.* American Journal of Physics 31(5), 368–377. — The invariance of `L/n²` along a ray and across a smooth boundary between lossless media, a consequence of étendue `n²dAdΩ` being the conserved quantity. Radiance itself is not conserved across a refracting interface.
- **solonenko2015** `P` — Solonenko, M.G. & Mobley, C.D. (2015). *Inherent optical properties of Jerlov water types.* Applied Optics 54(17), 5392–5401. — The published inherent optical properties behind the water-type presets. ⚠️ The numeric `K_d(λ)` tables circulating in blog posts and asset packs are largely untraceable to this or to Jerlov's own tables; extract from source or generate from a published relation, and say which.
- **schlick1994** `P` — Schlick, C. (1994). *An Inexpensive BRDF Model for Physically-based Rendering.* Computer Graphics Forum 13(3), 233–246. — The Fresnel approximation, stated in the original as about 1% of `R` for common dielectrics. At water's low index it is not: measured against the exact equations it runs about +11% at grazing angles and 22% low at the Brewster angle.
- **bornwolf_optics** `F` — Born, M. & Wolf, E. *Principles of Optics*. ⚠️ **This entry used to assert `§1.5.2` and name no edition, and nobody has been able to verify it.** Two agents tried: Cambridge drops the tunnel on the front-matter PDF, `cambridge.org/core` returned 503, and all five archive.org scans are lending-restricted. A section number carried without an edition is barely a locator even when right, and this one is unchecked, so it is withdrawn rather than left looking verified. It is the highest-value locator still outstanding in this corpus. — The exact unpolarised Fresnel reflectance of a dielectric interface, and the Snell relation behind the critical angle. A textbook, not a paper, and graded accordingly; the physics is as canonical as physics gets.
- **iop_split** `F` — No single canonical source. The split between beam attenuation `c = a + b`, which governs a sharp sightline, and diffuse attenuation `K_d`, which governs the ambient light column — and the observation that `c` typically runs 5–20× `K_d` because natural water scatters strongly forward. Standard ocean optics; stated in this form in `terrain-architect/references/28-liquids.md` (present in this repository) and in `water-physics/references/12-water-physics.md` (⚠️ **not in this repository** — unmerged branch `origin/claude/swimming-pool-voronoi-render-m22g6r`). The claim itself is standard ocean optics and does not depend on either file. [no-artefact]
