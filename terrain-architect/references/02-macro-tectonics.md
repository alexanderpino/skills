# Macro Terrain & Tectonics

Contents: [What tectonics is for](#what-tectonics-is-for) · [Plate simulation](#plate-simulation) ·
[Uplift fields](#uplift-fields) · [Faults](#fault-formation) · [Islands & continents](#islands-and-continents)

## What tectonics is for

Tectonics produces the **uplift field `U(x,y)`**, in metres per year (or per timestep). It
does not produce terrain. `U` is an input to the erosion backbone — specifically to the stream
power equation (`04`), where the balance between uplift and incision produces the mountain
range.

This is the central insight of Cordonnier et al.'s work and the reason the tectonic node is
worth its ★★★★: the realism does not come from the plate simulation, which is crude. It comes
from **running fluvial erosion against a spatially varying uplift for long enough that the
landscape reaches a dynamic equilibrium**. In equilibrium, `U = K·A^m·S^n`, so slope
self-organises to `S = (U / (K·A^m))^(1/n)` — steep where uplift is high, gentle where drainage
area is large. That relationship *is* what makes a mountain range look like a mountain range,
and no amount of noise reproduces it.

**Consequence for the graph:** a tectonics node whose output goes anywhere except into the
uplift term of a long-running erosion simulation is decoration. If the user wants tectonic
plates but the graph runs 30 iterations of droplet erosion, the tectonics is doing nothing and
should be replaced with a cheaper large-scale mask.

## Plate simulation

Practical version. Full geodynamics is not required and not useful at game scales. This whole section
is **planar** — plates carry a 2D velocity vector. On a **whole sphere** the kinematics change: a plate
moves as a *rigid rotation about an Euler pole*, not a translation (transform faults trace small circles
about the pole; spreading rate ∝ sin of the angular distance from it). That is a different chapter —
`references/25-planetary-spherical.md` (McKenzie & Parker 1967; graphics realization Cortial et al.
2019). Use the planar model below for a flat patch, the spherical one for a globe.

```
1. Seed P plate centres (P ≈ 8–20 for a continent-scale map).
   Use Poisson disk (07) or relaxed random — pure random gives implausibly uneven plates.

2. Assign each cell to nearest centre → Voronoi partition = plates.
   Perturb the distance metric with low-frequency noise so boundaries are not straight:
       d(cell, centre) = |cell - centre| + warpAmp * fbm(cell * warpFreq)
   Straight Voronoi edges are the tell-tale of a bad plate node.

3. Give each plate:
       velocity v_p       (2D vector, magnitude ~cm/yr scaled to your timestep)
       type               oceanic | continental
       baseElevation      oceanic ≈ -4000 m, continental ≈ +200 m

4. For each boundary cell between plates a and b:
       n     = normalised vector from centre_a to centre_b
       vrel  = v_a - v_b
       conv  = dot(vrel, n)          // >0 converging, <0 diverging
       shear = |cross(vrel, n)|      // transform component

       if conv > 0:                  // convergent
           if both continental:      collision  → uplift ∝ conv          (Himalaya)
           if one oceanic:           subduction → uplift ∝ conv on the continental side,
                                                  trench on the oceanic side
           if both oceanic:          island arc → narrow uplift ridge
       elif conv < 0:                // divergent
           rift → negative uplift, thinned crust                          (East African Rift)
       if shear dominates:           transform → little uplift, strong lateral offset
                                                  (offset the height field across the boundary)

5. Diffuse the boundary uplift inland:
       U = gaussian_blur(boundaryUplift, sigma = orogenWidth / cellSize)
   Real orogens are 100–300 km wide, not one cell. Without this diffusion you get a razor
   ridge exactly on the Voronoi edge, which is the second tell-tale of a bad plate node.

6. Optional: iterate. Move plate centres by v_p, re-partition, accumulate uplift.
   3–8 iterations gives you crustal history (old inactive ranges beside young active ones)
   which reads as much more believable than a single snapshot.
```

**Parameter sanity.** Uplift rates in active orogens are 0.1–10 mm/yr. Over 10⁶ years that is
100–10000 m — the right order for a mountain range. If your uplift × time doesn't land in that
window, the erosion will not reach equilibrium and you'll get either a flat plain (too little)
or an unerodible plateau (too much).

*Runnable reference: `tectonics.plate_uplift` implements this loop — domain-warped Voronoi plates
(Lloyd-relaxed centres), per-boundary classification (collision / subduction / island-arc / rift /
transform), and the boundary uplift diffused inland over the orogen width; returns the elevation
field (per-plate base + orogens). Verified by `tests/test_tectonics.py`: oceans and continents both
present, orogens exceed the continental base, and — the decisive check — the highest ground is
concentrated **at plate boundaries** (orogens), not in plate interiors. F-tier (a plausible planar
plate sketch, not plate physics); the ★★★★ realism still comes from running erosion against it.*

## Uplift fields

You often don't need plates. If the user wants "a mountain range here", author `U` directly:

| Source | Produces |
|---|---|
| Painted / spline mask, blurred | Directed ranges, art-directable |
| Low-frequency FBM, remapped so most of the domain is ~0 | Scattered massifs |
| Distance field from a spline, `U = A·exp(-d²/2σ²)` | A single linear range with a natural cross-section |
| Constant `U` | Uniform plateau dissected into a dendritic drainage — surprisingly good, and the classic Braun–Willett test case |

A **constant uplift plus stream power** is the cheapest route to a genuinely realistic
dissected landscape. It is worth proposing whenever someone reaches for a 12-node noise stack
to get valleys.

Boundary condition matters more here than anywhere else: the domain edge is usually the base
level (`h = 0`, fixed). Erosion cuts headward from the edges inward. If all four edges are
fixed at zero, you get a dome. If one edge is the base level and the rest are no-flux, you get
a range draining one way — usually what you want.

## Fault formation

Cheap, and useful as a detail layer on top of tectonics.

```
faultIteration(h, N):
    repeat N times:
        pick a random line across the domain (point + direction)
        for each cell:
            side = sign(cross(direction, cell - point))
            h[cell] += side * displacement * falloff(distance_to_line)
```

With `falloff = 1` you get the classic fault-formation fractal (hard steps, poor). With
`falloff = 1/(1+d/w)` or a smoothstep over a width `w`, and `displacement` decaying as
iterations progress, you get plausible blocky/faulted terrain. It is a fractal, not a
simulation — it has no drainage either.

Real value: use faults to add **structural anisotropy** into an uplift field before erosion.
Erosion exploiting a fault-weakened line produces valleys that follow structure, which is
exactly what real faulted terrain looks like. Implement as a spatially varying erodibility
`K(x,y)` rather than as height displacement — that is the geologically correct coupling.

*Runnable reference: `reference-impl/tectonics.py` — `fault_scarp` is this `faultIteration`
(feathered offsets, decaying displacement → fault blocks); `fault_weakness` is the K(x,y) coupling
(fault traces set MORE erodible), fed to `erosion_streampower.stream_power_evolve`. Verified by
`tests/test_tectonics.py`: the scarp offsets a flat field finitely and deterministically, and the
decisive check — with the fault-weakened K, far more of the fault cells end up as valley floor than
chance (structure-controlled drainage). The scarp is an F-tier fractal; the K coupling is P-tier once
the erosion runs on it.*

## Islands and continents

```
continentMask(p):
    base   = fbm(p * lowFreq)                       // continent shapes
    base  -= radialFalloff(p)                       // pull edges below sea level (optional)
    land   = smoothstep(seaLevel - w, seaLevel + w, base)
    return land
```

The interesting part is the **shelf**. A landmass that goes from +500 m to −4000 m in two
cells reads as a papercraft cutout. Real margins have a shelf (~200 m deep, tens of km wide),
then a slope, then the abyssal plain. Model it as a remap curve on the base field with a
distinct flat section at shelf depth, not as a linear ramp.

Coastlines are an **erosion output, not an input**. A coastline authored by thresholding noise
has fractal wiggle but no relationship to the drainage — rivers will meet the sea at arbitrary
points instead of in estuaries. If coastline quality matters, set sea level *after* erosion and
let the drainage network define where the estuaries are.

## Isostasy & flexure

*Runnable reference: `reference-impl/isostasy.py`, verified by `tests/test_isostasy.py` — the FFT
flexure solver checked against exact single-mode response, the Airy limit, and the analytic
line-load kernel (`09`).*

Everything else in this file *adds or removes load*: uplift builds crust, erosion (`04`) strips it,
ice (`12`) piles on and melts off. **Isostasy is the vertical response to that load** — the crust
floats on a denser mantle, so it sinks under a load and rebounds when the load goes. Leave it out and
a range just erodes downward; put it in and the range *rises as it erodes*, which is the real
long-term behaviour and reshapes the whole profile.

**Airy (local) — the cheap baseline.** Each column floats independently; a topographic load of height
`h` presses a root of depth `r` into the mantle (Turcotte & Schubert 2014; Watts 2001):

```
r = ρc · h / (ρm − ρc)          # ρc ≈ 2700–2800, ρm ≈ 3300 kg/m³  →  r ≈ 5–6 · h
```

A per-cell multiply, no neighbour coupling — nearly free, but wrong at short wavelengths: a narrow
load doesn't sink as if it were infinitely wide, because the plate has strength.

**Flexural — the plate is stiff.** The lithosphere behaves as a thin elastic plate over an inviscid
mantle, so a load deflects it over a *region*, not one column (Watts 2001; Turcotte & Schubert 2014):

```
D · ∇⁴w + (ρm − ρinfill) · g · w = q(x,y)     # w = deflection (down +), q = load [Pa]
D = E · Te³ / [12(1 − ν²)]                      # flexural rigidity [N·m]
```

with `E ≈ 70–100 GPa` (Young's modulus), `ν ≈ 0.25` (Poisson), and `Te` the **effective elastic
thickness** — the one knob that matters, from a few km (weak, hot lithosphere) to tens of km (old,
cold). The response width is the flexural parameter `α = [4D / ((ρm − ρinfill)·g)]^¼`. The practical
way to solve it over a heightfield is **in the Fourier domain**, where `∇⁴` is a multiply:

```
q = ρc · g · h ;  Q = FFT2(q)
W = Q / (D · k⁴ + (ρm − ρinfill) · g)          # k = radial wavenumber; the plate transfer function
w = IFFT2(W) ;  h_isostatic = h − w             # subside under loads, rebound at deficits
```

This convolves the load with the plate's response kernel — long wavelengths compensate almost fully
(the Airy limit), short ones ride on the plate's stiffness, and `Te` sets where the crossover sits.

**Building the wavenumber grid `k`.** This is where the FFT solve is most often quietly wrong — a
`linspace(0, k_max)` ramp instead of the signed, Nyquist-wrapped frequencies. Use `fftfreq`, which
returns $[0,1,\dots,\tfrac{N}{2}-1,-\tfrac{N}{2},\dots,-1]/(N\Delta x)$, matching the FFT's own mode
ordering; the **angular** wavenumber is $2\pi$ times that:

$$k_x = 2\pi\,f_x,\quad f_x=\mathrm{fftfreq}(N_x,\Delta x),\qquad k=\sqrt{k_x^2+k_y^2}$$

```
# Δx, Δy = cell size in METRES;  Nx, Ny = grid dimensions
ky = 2π * fftfreq(Ny, d=Δy)        # rad/m, length Ny
kx = 2π * fftfreq(Nx, d=Δx)        # rad/m, length Nx
KX, KY = meshgrid(kx, ky)          # shape (Ny, Nx)
k  = sqrt(KX**2 + KY**2)           # radial wavenumber; k[0,0] = 0 (the DC / domain mean)
```

Two scales decide whether the solve is physical: the **fundamental** wavenumber $2\pi/L$ (with
$L=N\Delta x$ the physical domain length) must resolve the flexural wavelength — the domain has to
exceed a few $\alpha$, which is often *hundreds of km*, or the response wraps; and the **Nyquist**
wavenumber $\pi/\Delta x$ (two cells per wavelength) is the shortest resolvable. No $k=0$ guard is
needed: the denominator there is $D\cdot 0 + (\rho_m-\rho_{\text{infill}})g$, finite — the
domain-mean load subsides uniformly (the Airy limit). **The same grid drives the mass-consistent
wind Poisson solve (`13`).** (The grid and solver are runnable in `reference-impl/isostasy.py`.)

**Erosional rebound — why peaks can rise as a range wears down.** Erosion removes *mean* load, so the
range rebounds by ~`ρc/ρm ≈ 0.8` of the mean thickness stripped. Carve deep valleys but leave the
summits, and the summits go *up* with zero tectonic uplift — **Molnar & England 1990**'s chicken-or-
egg caution: measured peak uplift is not by itself proof of tectonic uplift. Couple it to the erosion
pass (`04`):

```
rebound = (ρc/ρm) · smoothOver(α, erodedThickness)     # spread over the flexural width α
h += rebound
```

**Glacial isostatic adjustment (rebound) — the mantle is viscous, so it lags.** Under an ice load the
crust sinks; when the ice melts it rebounds over *millennia*, because the mantle flows on a relaxation
timescale (Peltier 1974; Peltier 2004). Model it as exponential relaxation toward the new equilibrium,
fastest at long wavelengths:

```
τ(λ) = 4π·η / (ρm · g · λ)                      # η ≈ 10²¹ Pa·s mantle viscosity; long λ relax first
w(t+Δt) = w_eq + (w(t) − w_eq) · exp(−Δt/τ)
```

This is what strands raised beaches and tilts old shorelines around formerly glaciated coasts
(Fennoscandia, Hudson Bay) — the same lifted-shoreline signature the marine-terrace loop reads
(`12`), here driven by rebound rather than tectonics.

**Verify.** Deflection equals the load convolved with the flexural kernel, approaching the Airy
limit at long wavelengths; and through an erosion run the *mean* elevation drops while the peaks
*rise* by ~`ρc/ρm` — peaks that sink as valleys incise mean rebound is missing (`09`,
*Checks for the extended families*).

**Tier.** Airy and flexural isostasy and the GIA relaxation are standard geophysics, P-tier
(Turcotte & Schubert 2014; Watts 2001; Peltier 1974, 2004); erosional-unloading rebound is Molnar &
England 1990 (P). The spectral flexure solve is the standard F-tier implementation of that P-tier
equation — no separate paper, it's just where you compute `∇⁴` cheaply.
