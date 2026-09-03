---
type: Technique
title: Seamless and periodic — output that tiles
description: "Making a heightfield wrap: modular lattice indexing is arithmetic and cheap, but an erosion solver's boundary condition decides whether the result can wrap at all, and a torus has no outlet."
tags: [generation, tiling, periodic, boundary-conditions, erosion, noise, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: lagae2010, tier: P, locator: "§2.3 Definition of procedural noise — the advantage list, whose third bullet makes NON-periodicity a defining virtue: a noise 'is unlimited in extent and can cover an arbitrary large area without seams and unwanted repetition'; §7 Comparison with Table 1, rows `storage requirements` and `non-periodic`, plus footnote 1, which defines storage in terms of THE PERIOD N — Perlin noise is O(N) and is not ticked non-periodic, Gabor and sparse convolution noise are O(1) and are; §7 paragraph opening 'Storage requirements and periodicity are generally linked', which names noise tiles and long-period hash functions as the two fixes. Read in the authors' preprint PDF, which paginates 1-20 rather than to the CGF 29(8) numbering, so sections are cited and pages are not" }
  - { id: perlin2002, tier: P, locator: "§2, the review of the 1985 construction — the eight lattice gradients are g at i,j,k = G of P of P of P of i, plus j, plus k, so the gradient is a lookup into a FINITE permutation table indexed by the lattice integers; §5 Conclusions — 'with the pseudo-random gradient table removed, the only pseudo-random component left is the ordering of the permutation table P'. Read in the 2-page SIGGRAPH sketch, which carries no appendix listing, so the reference implementation's 8-bit index mask is NOT cited to this paper" }
  - { id: mei2007, tier: P, locator: "§3.2.2 Water Surface and Velocity Field Update, the paragraph beginning 'For any fluid simulation method, boundary conditions should be taken into consideration' — 'we assume no water can flow out of the grid', implemented by setting the boundary cell's outward flux to zero; §4, 'the boundary cells require separate treatment from the interior cells of the grid'. Read in the authors' HAL deposit inria-00402079" }
  - { id: hobley2017, tier: P, locator: "§3.1.4 Grid boundary condition handling, p. 31 — a node has one of four boundary types, 'fixed value (Dirichlet), fixed gradient (Neumann), looped, or closed', with Table 4b giving looped the integer 3; Table 4a, p. 30, for which link carries flux under each pairing, where core-looped is Active and core-closed is Inactive; and the closing paragraph of §3.1.4, which describes a basin whose only outlet is 'a single node representing the outlet (flagged as a fixed-value or fixed-gradient boundary)' with every other perimeter node closed. Also §3.1.4 for the sentence 'The edges of a Landlab grid are always defined by boundary nodes'" }
  - { id: barnes2014, tier: P, locator: "§1, the Planchon-Darboux criteria the paper adopts — criterion 2 requires that from each cell 'there is a path that leads from c to the boundary by moving downwards', so correctness is DEFINED against a boundary; §3.1 History, 'the Priority-Flood Algorithm works by inserting the edge cells of a DEM into a priority-queue'; §3.2 The Algorithm, the paragraph following Algorithm 1, 'all of the edge cells are marked as resolved... by definition, edge cells have an epsilon-descending path to the DEM's edge'; and the NoData paragraph in the same section, where cells at an extremely negative value 'have no impact on terrain flooding and can be treated as normal data cells'" }
  - { id: periodic_lattice_practice, tier: F, locator: "no artefact: the modular-index construction for a wrapping lattice noise, the per-octave integer-period requirement it imposes on lacunarity, and the four-dimensional torus embedding used when the lattice cannot be reindexed. Standard practice with no canonical paper" }
  - { id: seam_fake_practice, tier: F, locator: "no artefact: the three constructions used to force a non-periodic field to tile — mirroring, cross-blending a margin against the field's own translate, and cropping an eroded field back from its boundary. Standard practice with no canonical paper" }
---
# Seamless and periodic — output that tiles

[lagae2010] §2.3 lists the properties a good procedural noise has, and the third one is that it
is **not periodic**: it "is unlimited in extent and can cover an arbitrary large area *without
seams and unwanted repetition*". You are about to ask for the defect on purpose. That is fine —
periodicity is a *requirement*, not a quality — but it means every source you will find is
optimising away from where you are going, and the survey's Table 1 says exactly what it costs:
storage is expressed "in function of the period N", so a lattice noise's memory *is* its period.

The topic splits cleanly and unevenly. **Making noise wrap is arithmetic** and takes one line.
**Making an eroded field wrap is a modelling decision made before the first timestep**, because a
simulation's boundary condition is not a post-process — it is part of the equations. [hobley2017]
§3.1.4 makes the choice explicit and enumerable: a node is `fixed value (Dirichlet)`, `fixed
gradient (Neumann)`, `looped`, or `closed`. Periodic is the third of four, chosen at setup, and
choosing it changes what the simulation *is*.

## Use this

**Decide periodicity at the domain, before the graph runs. Then: index the noise lattice modulo
the period; give every simulation wrapping neighbours; author exactly one sink; and make the
period a multiple of `2^L` for the deepest pyramid anywhere in the graph.**

```
period P                       # cells, chosen once, a multiple of 2^L_max
noise:  gradient(i mod P_l, j mod P_l)     # P_l = P * frequency_l, MUST be an integer
sim:    neighbour(i, j) = grid[(i + di) mod H, (j + dj) mod W]
route:  priority_flood(seeds = [the one authored sink])
filter: every convolution pads with `wrap`, never `reflect`
```

Four numbers, all measured below. The modular lattice wraps **bit-exactly** — `0.0` difference at
periods 7, 16, 64 and 300 — where the naive construction wraps only at 256, its hash table's own
period. Toroidal erosion conserves mass to `1.97e-16` and exports **0.000%**; open boundaries
export 2.18% of the terrain and flatten the seam to 0.39× the interior roughness. A torus with one
authored sink drains **100.00%** of the domain through it, against 30.41% for the largest of a
plane's 380 edge outlets. And a five-level band split with `reflect` padding leaves a seam **221×**
an ordinary step while its round-trip test still reads machine-precision-exact.

**What it beats.** *Mirroring* [seam_fake_practice] — free, and it makes **100.0%** of the seam
column a local extremum against 28.5% for an ordinary column, so every edge becomes an alternating
chain of ridges and troughs; §The three fakes. *Cross-blending a margin* [seam_fake_practice] —
fixes the step at `B = 4` and never fixes anything else; it costs half the detail variance at the
band centre and the band width you need scales as `2·D/s`. *Cropping an eroded field back from its
boundary* [seam_fake_practice] — correct, and the crop grows with simulated time: 3 cells at 100
steps, 13 at 1200, with no sign of converging. *Wang or corner tiles* — the real answer when you
want variation rather than repetition, named by [lagae2010] §7 as one of the two published fixes
for a noise's period; a different problem from making **one** tile wrap, and out of scope here.
*A four-dimensional torus embedding* — the only route when the lattice cannot be reindexed at all,
which is simplex; measured at `2.3e-14` for any period and 4× the gradient work.

`noise-and-warping.md` owns noise construction and `surface-and-scale-space.md` owns the band
split; this document owns only what makes each of them wrap. `tiled-streaming.md` and
`virtual-texturing.md` own runtime tiling, which is a different question with the same word in it:
they page a large world, this makes one small world close on itself.

## The easy half: periodic noise, in one page

A lattice noise is a table lookup interpolated between integer lattice points. [perlin2002] §2
writes the lookup as `g at i,j,k = G of P of P of P of i, plus j, plus k` — `P` a permutation
table, `G` a gradient table — and §5 notes that after the gradient table is fixed, "the only
pseudo-random component left is the ordering of the permutation table P". So the noise is a
deterministic function of the *integers* `i, j, k`, and it repeats exactly when those integers do.

⚠️ **There is no canonical source for the fix; standard practice is to reduce the lattice index
modulo the period before hashing** [periodic_lattice_practice]. One line, and it is exact:

```
i0 = floor(x) % P;  i1 = (floor(x) + 1) % P     # and likewise for y
```

Measured, `w8/m1_periodic_noise.py`, max `|f(x) − f(x+T)|` over 512² samples:

| construction | T = 7 | T = 16 | T = 64 | T = 256 | T = 300 |
|---|---|---|---|---|---|
| Perlin, naive hash of the raw index | 1.28 | 1.49 | 1.59 | **0.0** | 1.59 |
| Perlin, index mod T | **0.0** | **0.0** | **0.0** | **0.0** | **0.0** |
| 2-D simplex, same trick | 1.85 | 1.79 | 1.87 | 1.96 | — |

Three things fall out of that table.

**The period divides the domain, or there is no wrap.** The naive row is zero at exactly one
value, 256, which is the permutation table's own length — that is [lagae2010]'s Table 1 footnote 1
made visible, storage `O(N)` *in the period N*. A field is periodic at `T` if and only if `T`
divides the hash's period; the modular construction makes any `T` divide it by force.

**Simplex does not take the trick.** Simplex noise skews the square lattice by `F2 = (√3−1)/2`
before flooring, so the integers being hashed live on a triangular lattice whose relationship to
your rectangular tile is irrational. Reducing them modulo `T` reduces the *wrong* integers; the
measured error stays at full noise amplitude for every period tried. Simplex is periodic-hostile
by construction and the fix is not a fix to simplex.

**The general fix is a torus embedding, and it costs 4×.** Map the tile onto two circles in four
dimensions and evaluate a 4-D noise there [periodic_lattice_practice]:

```
a = 2*pi*x/T;  b = 2*pi*y/T
n(x, y) = noise4(r*cos a, r*sin a, r*cos b, r*sin b)
```

Periodic by construction, for any noise, with no modular indexing anywhere. Measured `2.3e-14` at
`T` = 7, 16, 64 and 300 — the residue is the `cos`/`sin` round-off, not a seam. It costs 16 lattice
corners per sample instead of 4. **Crossover: use modular indexing whenever you control the hash;
use the embedding only for a noise whose lattice you cannot reindex** — simplex, or any
third-party kernel you call as a black box.

⚠️ **Lacunarity is now a correctness parameter, and this contradicts `noise-and-warping.md`.**
That document recommends "a lacunarity that is not exactly 2", for good reasons about octave
alignment. But the modular construction needs an **integer lattice period at every octave**, so
`P · lacunarity^k` must stay an integer for every `k` you sum. Measured on a 6-octave fBm with
`P = 64` (`w8/m1_periodic_noise.py`, part M1b):

| lacunarity | 2.0 | 3.0 | 1.5 | 1.25 | 1.93 | 2.01 | 2.1 |
|---|---|---|---|---|---|---|---|
| max wrap error | 4.8e-14 | 3.5e-13 | 3.8e-14 | 4.7e-02 | 5.8e-01 | 5.5e-01 | 5.1e-01 |

`1.5` is exact because `64 · (3/2)^5 = 486`; `1.25` fails at the sixth octave because
`64 · (5/4)^5 = 195.3125`. ⚠️ Note that `1.25 = 5/4` has a denominator that *does* divide 64 and
fails anyway, so "a denominator dividing the period" is not the rule. **The rule is: write the
lacunarity in lowest terms as `p/q`, and for `n` octaves the period must be divisible by
`q^(n-1)`** — the highest octave is the binding one, because that is where the denominator has
compounded the most. Checked against the integrality of every octave for lacunarity 2, 3, 3/2,
5/4, 7/4, 9/8 and 5/2 at `T = 64`: the condition predicts the outcome in every case. It also
predicts the escape — `5/4` needs `4^5 = 1024`, so at a period of 1024 it wraps exactly, and it is
the *period* that has to grow, not the lacunarity that has to be abandoned. `3/2` on a power-of-two period buys back most
of the detuning the other document wants, and costs nothing.

## The hard half: the boundary condition IS the tiling decision

Everything above was arithmetic on a pure function. An erosion solver is not a pure function of
position; it is an initial-value problem, and its edges need a rule. [mei2007] §3.2.2 states the
one the reference GPU pipe model uses, in a sentence worth reading literally: *"Since the flow is
simulated on a 2D grid, we assume no water can flow out of the grid ('no slip' boundary
condition)"*, implemented by zeroing the boundary cell's outward flux. That is a **closed**
boundary — one of [hobley2017] §3.1.4's four, and not the one that tiles.

The three that matter here differ in one line of neighbour lookup:

| boundary | the line | mass | tiles? |
|---|---|---|---|
| **closed** [mei2007] §3.2.2 | outward flux at the edge set to `0` | conserved | no |
| **open** | the edge sees a ghost cell at base level | exported | no |
| **looped / toroidal** [hobley2017] §3.1.4 | `grid[(i+di) % H, (j+dj) % W]` | conserved | yes |

⚠️ **Mass conservation and periodicity are different properties, and a closed boundary has the
first without the second.** This is the single most common confusion on this topic. A wall
conserves mass perfectly and still produces a rim artefact, because a wall is a *landform* the
interior does not have.

`w8/m2_erosion_boundary.py` measures it. A 128² field is built by the modular construction above,
so it wraps bit-exactly before erosion starts (seam ratio 0.898 — the wrapped step is drawn from
the same distribution as every interior step). Then the [mei2007] pipe model runs on it under each
boundary condition. **Seam ratio** is the mean absolute step across the wrapped edge over the mean
absolute step between interior neighbours; 1.0 means the seam is indistinguishable from terrain.

| boundary | steps | seam ratio | rim bias | solver drift | exported |
|---|---|---|---|---|---|
| *seed* | 0 | 0.898 | 0.0 | 0 | 0.000% |
| torus | 100 / 400 / 1200 | 0.871 / 0.849 / 0.882 | −0.001 / −0.003 / −0.008 | **1.97e-16** | **0.000%** |
| closed | 100 / 400 / 1200 | 0.906 / 0.930 / **1.085** | −0.003 / −0.012 / **−0.042** | −8.5e-03 | 0.000% |
| open | 100 / 400 / 1200 | 0.766 / 0.530 / **0.389** | −0.000 / −0.003 / −0.009 | 2.1e-02 | **2.184%** |

- **The torus is the only row that does not move.** Its seam ratio wanders inside the noise band of
  the seed's own value and its mass drift is machine precision, because on a torus there is no
  edge for the solver to treat specially — [mei2007] §4's "the boundary cells require separate
  treatment from the interior cells" describes code that a toroidal solver does not have.
- **Closed opens the seam upward.** The wrapped step goes from 0.898 of an interior step to
  1.085 — a 21% relative rise — and the outer four cells drift 4.2% of relief away from the
  interior. The *sign* of that drift depends on your capacity law; its existence does not. Tiled,
  it reads as a ridge or trench repeating at exactly the tile pitch. Note the closed run's own
  solver drift, −8.5e-03: that is 0.85% of mass unaccounted for by my transport discretisation,
  not a physical export, so the "conserved" claim for `closed` rests on `exported = 0.000%` and
  not on that column.
- **Open planes the seam flat.** 0.389 means the seam is *smoother* than the terrain around it —
  everything within reach of the edge drained out. Tiled, that is a flat cross through the world
  every tile width, which is more visible than a crease because it is straight.

**How far in does the wrong boundary reach?** Against the torus run at the same step count,
`|b − b_torus|` by distance from the edge:

| boundary | 100 steps | 400 steps | 1200 steps |
|---|---|---|---|
| closed, depth where error > 1% of relief | 0 cells | 1 | 3 |
| closed, depth where error > 0.1% | 3 cells | 10 | 13 |
| open, depth where error > 0.1% | 3 cells | 10 | 13 |

**That is the crossover for the crop-a-margin approach, and it is bad news.** The margin is not a
function of the operator's support radius, the way `surface-and-scale-space.md`'s halo is; it is a
function of *simulated time*, and it grows monotonically with it. A halo you can size once from a
kernel width. A crop you must re-measure every time an artist adds iterations, and there is no
step count at which it stops growing.

## A torus has no outlet

This is the consequence people meet last and it is structural, not a tuning problem.

**Erosion on a torus cannot remove one gram of material from the tile.** Measured: `exported =
0.000%` and mass drift `1.97e-16` over 1200 steps. Every grain lifted off a hillside is deposited
somewhere else inside the same tile. That is not a bug in the solver — it is what "no boundary"
means. A landscape that is losing mass to the sea is not periodic, and cannot be made periodic,
because the sea is the thing it is not periodic *with*.

**Depression filling stops working, and the reason is in its definition.** [barnes2014] §1 adopts
the Planchon-Darboux criteria, whose second requires that from each cell "there is a path that
leads from `c` **to the boundary** by moving downwards". Correctness is defined against a boundary.
§3.1 seeds the algorithm accordingly: it "works by inserting **the edge cells** of a DEM into a
priority-queue", and §3.2's paragraph after Algorithm 1 explains why they are the right seeds — "by
definition, edge cells have an ε-descending path to the DEM's edge". [hobley2017] §3.1.4 says the
same from the other side: "the edges of a Landlab grid are **always** defined by boundary nodes".

On a torus that seed set is empty. `w8/m5_torus_flow.py`, 96² = 9216 cells:

| domain | seeds | cells reached | cells raised | fill volume | max accumulation |
|---|---|---|---|---|---|
| plane, open edges | 380 | 9216 | 2514 | 414.1 | 2803 = **30.41%** of domain |
| torus, one authored sink | 1 | 9216 | 3471 | 660.3 | 9216 = **100.00%** |
| torus, no sink | 0 | **0** | 0 | — | — |

The third row is not a failure to be worked around; it is the algorithm reporting that the problem
is underspecified. The queue starts empty and nothing is ever reached.

**So author a sink.** [barnes2014] §3.2 gives the mechanism: NoData cells are "some
extremely negative number", so they "have no impact on terrain flooding and can be treated as
normal data cells" — a pinned low cell is a legal seed. [hobley2017] §3.1.4 gives the modelling
form, describing a basin "with the basin's interior consisting of core nodes, **a single node
representing the outlet** (flagged as a fixed-value or fixed-gradient boundary), and the remainder
of the nodes flagged as closed boundaries". That single node is your sink, and it is a design
decision an artist should make, not a default.

⚠️ **Do not describe this as drainage "circulating".** A steepest-descent router cannot cycle —
elevation strictly decreases along every path — so flow does not go round the torus; it terminates
in interior basins. The problem is not a loop, it is that filling those basins needs somewhere to
*spill to*, and the torus has one such place only if you made one.

**And the one sink is expensive.** With 380 outlets sharing the load the largest catchment is 30%
of the domain; with one, it is 100% by definition — the tile has exactly one river and everything
is its tributary. Fill volume rises 59% and 38% more cells are raised, because every basin must now
be lifted until it finds a path to that single point. A tileable eroded terrain is *structurally*
a single-basin terrain, and that is a look, not a neutral choice.

## The three fakes, and what each costs

⚠️ **There is no canonical source for any of these; standard practice is one of three —
mirror the tile, cross-blend a margin, or simulate on a torus** [seam_fake_practice].

### Mirroring

Reflect the field and the copies meet at equal values. Free, exact, and it destroys the seam as a
place where terrain can exist. `w8/m3_mirroring.py`, 256² tiles:

| measurement | mirrored | periodic by construction |
|---|---|---|
| fraction of the seam column that is a local extremum along x | **100.0%** | 27.0% |
| fraction of an ordinary column that is | 28.5% | 27.0% |
| max correlation between the tile and its own left-right flip | **1.0000** | 0.3321 |
| spectral energy in the imaginary part of the DFT | **1.9e-32** | 4.65e-01 |
| local maxima with an exact mirror twin in the same tile | 1221 / 1221 = **100%** | 11 / 1114 = 1.0% |

Read those rows as one statement. `h(x0−d) = h(x0+d)` makes every cell on the axis a stationary
point in `x`, so the seam is *guaranteed* to be an unbroken alternating chain of ridges and
troughs — 100.0% against a 28.5% baseline is not a tendency, it is a certainty. The tile correlates
with its own reflection at exactly 1.0000, which is what "visible symmetry" means numerically.
And the field is even, so its transform is real: **half the spectral degrees of freedom are gone**,
and every feature in the tile has a twin. At a fixed tile size you generated half as much terrain.

**Use it for**: a background layer at a scale no one will inspect, or a normal map. **Never for**
anything a drainage network runs through: the x-gradient on the axis is identically zero, so every
routing decision along the entire seam is a tie broken by neighbour order rather than by terrain.
(I measured the critical line, not its effect on a routed network — that is asserted from the
symmetry, not from a run.)

### Cross-blending a margin

Fade the field into its own translate across a band of width `B`. `w8/m4_crossblend.py`, 192²,
smootherstep weights:

| B | 0 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|
| seam ratio | 4.686 | **1.149** | 1.154 | 1.166 | 1.189 | 1.228 |
| high-pass variance, band / interior | — | 1.71 | 0.94 | 0.71 | 0.75 | **0.66** |

**The step is fixed at `B = 4` and never gets better.** Everything past that width is spent on the
other problem, and buys detail loss: `a·h0 + (1−a)·h1` on two independent fields keeps
`a² + (1−a)²` of the variance, which is 0.500 at the band centre. Measured at the `a ≈ 0.5` rows of
a `B = 32` blend: **0.488**. The band is a strip where the terrain is half as detailed as the terrain
either side of it, and widening the band widens the strip.

**What the band is actually for is a *statistical* mismatch, and there the width has a formula.**
A blend does not remove a difference of `D` between the two sides; it converts a step of `D` into a
ramp of slope `D/B`. It is invisible once that ramp is below the terrain's own mean step `s`.
Measured `B*`, the smallest band at which the band's mean step falls to the terrain's:

| mismatch `D/s`, in cells | 1.3 | 2.6 | 5.2 | 7.8 | 13.0 | 25.9 | 51.9 |
|---|---|---|---|---|---|---|---|
| measured `B*`, cells | 14 | 15 | 20 | 24 | 28 | 51 | 106 |
| `B* / (D/s)` | 10.8 | 5.8 | 3.9 | 3.1 | 2.2 | **2.0** | **2.0** |

**Crossover: `B ≥ 2·D/s`, with a floor of about 14 cells.** Below the floor the blend's own detail
loss is the visible artefact rather than the ramp. Above `D/s ≈ 13` the factor is a clean 2.

⚠️ **One folk claim about cross-blending did not survive measurement, and it is the one usually
given as the reason not to use it.** The story is that the band kills rivers arriving at the seam.
Measured as total D8 accumulation crossing the seam cut, against the median interior cut, on a
torus with one authored sink: 0.90, 0.91 and 0.91 for `B` = 8, 16 and 32 — against **0.83** for a
terrain that is periodic by construction. Drainage crosses the blend band about as freely as it
crosses anywhere else, and I could not reproduce a loss. The real objection is the one that *is*
measured: the terrain in the band is a 50/50 average of two independent fields, so the landform
there belongs to neither, and the river that crosses is not the river that arrived.

### Simulating on a torus

Correct, and it constrains the simulation, in exactly the ways §A torus has no outlet lists: no
export, one authored sink, one basin, 59% more lake. It is also the cheapest of the three at run
time — a modulo in the neighbour lookup — and the only one whose cost is stated up front rather
than discovered in a screenshot.

**Crossover.** Mirror when the layer is decorative and no water runs on it. Cross-blend when you
are joining two fields you did not generate together and cannot re-run — it is a repair, not a
method. Simulate on a torus in every other case, and accept the single-basin look as the price.

## Everything downstream must wrap too, including the filters

A periodic input does not stay periodic through a non-periodic operator, and the operator's
padding mode is its boundary condition under a different name. `surface-and-scale-space.md`
recommends `reflect` padding for the Burt-Adelson band split, correctly, because on an open domain
zero padding asserts sea level one cell outside the field. **On a periodic domain that
recommendation inverts.** `w8/m6_pyramid_padding.py`, 256², `a = 0.4`, input seam-to-interior step
ratio 3.48:

| padding | L = 1 | L = 3 | L = 5 | round trip |
|---|---|---|---|---|
| `wrap` | 3.34 | 2.41 | **1.19** | 1.1e-16 |
| `reflect` | 10.4 | 35.5 | **221.5** | 1.1e-16 |
| `symmetric` | 18.8 | 76.7 | 397.7 | 1.1e-16 |
| `edge` | 23.0 | 94.7 | 523.0 | 1.1e-16 |
| `constant` (zero) | 5.5 | 13.9 | 49.4 | 1.1e-16 |

Cells are the low band's maximum wrapped step over its mean interior step. Only `wrap` keeps the
seam in the same population as the terrain. ⚠️ **The round-trip column is the point.** `lo + hi = h`
holds to machine precision for every mode, because it holds by construction — so the assertion
`surface-and-scale-space.md` recommends for validating a split **cannot see this failure at all**.
Assert the wrapped step separately, or the guard passes and the seam ships.

**And the phase rule has a periodic form.** `surface-and-scale-space.md` measured that a *tiled*
band split needs `halo ≥ 3·2^L − 2` **and** `(tile_origin − halo) ≡ 0 (mod 2^L)`, because the
decimation starts at the sub-array's origin. The same arithmetic binds the *domain*: with `wrap`
padding, the split reproduces the infinite-periodic answer only when the period is a multiple of
`2^L`. Comparing `low_band(h)` against the first block of `low_band(tile(h, 2x2))`:

| period N | 256 | 252 | 252 | 250 | 250 |
|---|---|---|---|---|---|
| L | 2, 3, 5 | 2 | 3 | 2 | 3 |
| `N mod 2^L` | 0 | 0 | 4 | 2 | 2 |
| max difference | **0.000e+00** | **0.000e+00** | 1.8e-01 | 2.2e-01 | 4.2e-01 |

Exact when `N ≡ 0 (mod 2^L)`, and wrong by up to 22% of relief when it is not. **Pick the domain
period as a multiple of `2^L` for the deepest pyramid anywhere in the graph, before anything else
is chosen.** 1024 or 2048 costs nothing and settles it.

## What cannot be made periodic

`node-graph-runtime.md` classifies operators as **local**, **global-reduce** and
**global-ordered**. Read against this document, that classification is a periodicity forecast:

- **Local** operators wrap the moment their padding does. One flag.
- **Global-reduce** operators — min/max normalisation, histogram equalisation — are periodic for
  free, because a reduction over the whole domain has no edge to be wrong at.
- **Global-ordered** operators are the ones that break, and flow accumulation is the canonical
  case (`flow-routing.md`). It is not that accumulation is *undefined* on a torus — §A torus has no
  outlet measures it perfectly well. It is that it has **no base level**, so the answer is
  determined entirely by where you put the sink, and every cell in the tile drains through it.

The honest statement is therefore narrow: **a global-ordered quantity on a torus is well defined
and is not a function of the terrain alone.** Move the sink one cell and the drainage network
reorganises. If two people generate "the same" tile with the same seed and different sink
placement, they get different rivers, and neither is wrong.

Two more things this document does **not** claim to have solved. An **iterated** global-ordered
pass out of core is open — `node-graph-runtime.md` states the limit and this document does not lift
it. And **coupling a periodic tile to a non-periodic neighbour** is a contradiction, not a
technique: a tile that wraps has already decided that nothing outside it exists.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| The noise wraps at 256 and at no other period | The lattice index is hashed raw, so the period is the permutation table's length; [lagae2010] Table 1 footnote 1 defines noise storage in terms of that period | Reduce the lattice index mod the period before hashing [periodic_lattice_practice] |
| Base octave wraps, the field does not | `period × lacunarity^k` stopped being an integer at some octave; measured 4.7e-02 at lacunarity 1.25 with period 64 | Lacunarity `p/q` in lowest terms with `q^(n-1)` dividing the period, `n` octaves — `3/2` at six octaves needs 32, so it wraps on any power-of-two period **of 32 or more** and not at 16, where `16·(3/2)^5 = 121.5`; `5/4` needs 1024 |
| Modular indexing has no effect on a simplex noise | Simplex floors a lattice skewed by an irrational constant, so the integers you reduced are not the tile's; measured full-amplitude error at every period | Four-dimensional torus embedding, at 4× the gradient work [periodic_lattice_practice] |
| A ridge or trench repeating at exactly the tile pitch after erosion | Closed boundary — the edge is a wall, and a wall is a landform. Mass is conserved and periodicity is not; measured seam ratio 1.085 and rim drift 4.2% of relief | Wrapping neighbours [hobley2017] §3.1.4 `looped` — not a wider blend |
| A straight flat cross through the world every tile width | Open boundary planed the edges; measured seam ratio 0.389 against an interior of 1.0, and 2.18% of terrain mass exported | Toroidal boundaries, or crop and re-measure the crop every time the iteration count changes |
| The crop margin that worked last week now seams | The margin is a function of simulated time, not of a kernel radius: 3 → 10 → 13 cells at 100 → 400 → 1200 steps | Stop cropping; simulate on a torus. There is no converged margin |
| Priority-flood returns instantly and nothing is filled | The seed set is "the edge cells" [barnes2014] §3.1, and a torus has none; measured 0 cells reached | Seed with the authored sink; a pinned low cell is a legal seed [barnes2014] §3.2 NoData |
| One river carries the entire tile and there are no others | A torus has one base level because you authored one; max accumulation is 100.00% of the domain by construction | Expected, not a bug. If you want several, author several sinks and accept several basins |
| Lakes everywhere after making the domain periodic | With a single outlet every basin must be raised until it finds a path to it; measured fill volume +59% and cells raised +38% against an open plane | Expected. Lower the sink, or breach rather than fill (`flow-routing.md`) |
| Terrain wraps, the erosion mask cut from the low band does not | The pyramid padded with `reflect`; measured seam 221× an interior step at L = 5 while `lo + hi == h` stayed exact to 1.1e-16 | `wrap` padding at every level, and assert the wrapped step — the round-trip test is blind to this |
| Seam appears only at deep pyramid levels, at a domain size that is not a power of two | The decimation lattice does not survive the wrap unless `N ≡ 0 (mod 2^L)`; measured exact at 256, wrong by 22% of relief at 250 | Choose the period as a multiple of `2^L` for the deepest split in the graph |
| Two artists' "identical" tiles have different rivers | Flow accumulation on a torus is well defined but has no base level, so it is a function of the sink placement as well as the terrain | Put the sink in the project file, next to the seed |
