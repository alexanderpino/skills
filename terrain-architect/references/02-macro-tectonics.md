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

Practical version. Full geodynamics is not required and not useful at game scales.

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
