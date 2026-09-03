---
type: Technique
title: River networks — the authored planform
description: "Synthesising a river as a thing you draw rather than a thing erosion leaves behind: width from discharge, the cross-section carve, the slope–discharge threshold that decides braided from meandering, and the structural reason a single-receiver network can express neither."
tags: [generation, hydrology, rivers, planform, channel-geometry, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: leopold1953, tier: P, locator: "p. 16 eqs. (1)–(3) — w = aQ^b, d = cQ^f, v = kQ^m, with the DOWNSTREAM averages b = 0.5, f = 0.4, m = 0.1 and the identity b+f+m = 1.0 that Q = wdv forces; p. 9 for the AT-A-STATION averages b = 0.26, f = 0.40, m = 0.34 over 20 cross sections, and for 'Width and depth for a given discharge vary widely from one cross section to another and, therefore, the intercept values, a, c, and k, will vary'; p. 36 for the same two triples restated as m/f = .85 at a station against .25 downstream; p. 51, 'Why this exponent b should so consistently be nearly equal to 0.5 in the downstream direction for widely different rivers is not known and constitutes an important unsolved problem'" }
  - { id: leopoldwolman1957, tier: P, locator: "p. 60 eq. (1), s = 0.06 Q^−0.44, 'a line described by the equation' separating braided from meandering channels, Q bankfull in cfs, plotted as fig. 46 on p. 59; p. 60 for the definitions — a braid is a reach with 'relatively stable alluvial islands, and hence two or more separate channels', a meander is sinuosity ≥ 1.5 and that value 'is an arbitrary one'; p. 60 for Cottonwood Creek, meandering at slope 0.0011 and braided at 0.004 with no tributary between them; p. 59 for the meander wavelength fit λ = 6.5 w^1.1 and 'the relation is not a constant ratio but a power function having an exponent slightly larger than 1.0'; p. 58 fig. 45B for the observed wavelength-to-width ratio 'from about 7 for small streams having widths of 1 to 10 feet, up to 15 for large rivers having widths in excess of 1,000 feet'" }
  - { id: strahler1957, tier: P, locator: "p. 914 §Order analysis — the ordering rule 'only slightly modified from Horton (1945, pp. 281-282)', finger-tip tributaries order 1, two of order k joining to make k+1; p. 914 §Bifurcation ratio for Horton's law of stream numbers as an inverse geometric sequence and for 'the number is highly stable and shows a small range of variation from region to region or environment to environment, except where powerful geologic controls dominate', with Coates (1956) ranges 4.0–5.1 and 2.8–4.9; p. 915 fig. 3 for the fitted regression b = 0.541, r_b = 3.52 and the segment counts 139/46/11/3/1 from Smith (1953, Plate 8); p. 915 fig. 4 for the stream-length regression b = 1.67" }
  - { id: candel2021, tier: P, locator: "Table 1 — the Leopold & Wolman discriminator classifies 79% of 126 rivers correctly, κ = 0.48, 'moderate' agreement (79% of 97 single-thread, 76% of 29 multi-thread), against 96% of 111 and κ = 0.95 for Kleinhans & Van den Berg read as lower limits; §2.2 eqs. (4)–(5) for potential specific stream power ω_pot = ρgQ_ef·S_v/W_r with reference width W_r = φ√Q_ef, φ = 4.7 sand-bed and 3.0 gravel-bed; eq. (6) ω_bm = 900 D50^0.42 for the braided–meandering transition and eq. (7) ω_ia = 90 D50^0.42, 'defined at a tenfold lower stream power', for the inactive–active transition anchored on the anastomosing upper Columbia; p. 9 eq. (10) for the bar mode m² = (0.17g(n−3)/√(((ρs−ρ)/ρ)D50)) · W³S/(CQ) with n = 4 sand and 10 gravel, and eq. (11) B_i = (m−1)/2 + 1" }
  - { id: genevaux2013, tier: P, locator: "§4 Table 1 and fig. 6 — the expansion grammar whose branching rules are Horton–Strahler symmetric (n−1, n−1) and asymmetric (n, m<n) junctions, applied with user probabilities Pc + Ps + Pa = 1, and fig. 8 for what those probabilities do to the order histogram (Ps = 0.7 gives >75% order-1 streams); §5.1 §River flow evaluation for φ = 0.42·A^0.69 with A in m² and φ in m³/s, 'This equation takes into account evaporation and infiltration, and that is why the volume flow is not preserved'; §7 for the river primitive h(p) = u_z(p) + δ(d(p)) — the elevation of the projection on the centreline plus a stored profile of signed distance — and for the replace operator h_C(A,B) = (1−w_B)h_A + w_B h_B that puts it into the terrain; §6.2 fig. 14 for terrain elevation as a distance-weighted combination of the projection on the river and the projection on the ridge; §6.1 fig. 12 for the junction-angle rule, 'nearly perpendicular' when the joining flows differ and a small angle when they are the same size" }
  - { id: peytavie2019, tier: P, locator: "§5.1 and its margin note — 'We check that the river height is monotonically decreasing. When this fails, we propagate the heights of the river trajectories downwards and perform local adjusments at the junctions'; §5.2 with fig. 8 for cross-section templates 'normalized in the sense that their scale assumes unit area for water in the cross section', scaled by a = φ/‖u‖ with φ = 0.42A^0.69; §5.2 with fig. 13 for Rosgen D — 'We first establish the number of channels based on the flow volume and width of the river', each thread on its own trajectory with width and depth 'determined by partitioning the aggregate flow between channels', and 'in order to preserve flow, the final height of the riverbed is set as the minimum height over all channels'; §5.2 fig. 12 for the asymmetric cross-section in high-curvature bends" }
  - { id: paris2023, tier: P, locator: "§4 — 'the width of the channel is related to the drainage by the power law w_Γ ∝ a^0.5' and the width–depth relation w_Γ = 18.8 d_Γ^1.41 attributed to Konsoer et al. 2013, both held constant per channel; §6.1 fig. 21 for the junction-angle rule, near perpendicular when the two flows differ and a small angle when they are similar; §6.2 fig. 22 for the three collision cases — upstream, downstream and disconnected — that a migrating network needs and a static tree does not" }
  - { id: braid_flow_split, tier: F, locator: "no artefact: how a reach's discharge is divided among the threads of a braid. peytavie2019 §5.2 says only that the parameters are 'determined by partitioning the aggregate flow between channels' and prints no rule" }
  - { id: subcell_channel, tier: F, locator: "no artefact: the rule that a channel narrower than about two cells cannot be carved into a heightfield at all. Universal in practice, unpublished as such" }
---
# River networks — the authored planform

Erosion gives you a drainage network for free, and it is the wrong object. It is a **tree**: one
receiver per cell, no width, no cross-section, no bank, and structurally incapable of the one
thing rivers visibly do at map scale — dividing around a bar and rejoining. If what you want is
a river the user placed, whose width is right for its discharge, that meanders where the ground
is flat and braids where it steepens, none of that is a by-product of `stream-power.md`. It is
an authoring operator, and it has its own literature.

This document owns the network **as an object you make**: its planform, its cross-section, its
width, and how a centreline becomes terrain. It does not re-derive routing (`flow-routing.md`),
incision (`stream-power.md`) or droplet and pipe erosion (`hydraulic-erosion.md`), and it cites
them where they are needed.

## Use this

**Author the network as an explicit graph of centrelines, carry `(discharge, width, type)` on
every edge, force the bed monotone downstream before you carve, then carve with
`h(p) = u_z(p) + δ(d(p))`** — the elevation of the point's projection on the centreline, plus a
stored cross-section profile evaluated at the signed distance from it [genevaux2013].

The three numbers that fill that graph:

- **Discharge from drainage area**: `φ = 0.42·A^0.69`, `A` in m², `φ` in m³/s [genevaux2013],
  used unchanged by [peytavie2019]. Or take `A` straight from `flow-routing.md`'s accumulation.
- **Width from discharge**: `w ∝ Q^0.5` [leopold1953]. The exponent is published; the
  coefficient is not, and you calibrate it from one river on your map (below).
- **Planform from slope and discharge**: braided above `S = 0.06·Q^−0.44` with `Q` bankfull in
  cfs, meandering below [leopoldwolman1957]. In SI that line is `S = 0.0125·Q^−0.44`, `Q` in
  m³/s — derived by unit conversion in `hydraulic_geometry.py` §3, not quoted from anywhere.

**What it beats.** *Taking the network from erosion output* — you get a tree with no width and
no planform control, and the user cannot move it. *Routing D8 at authoring time and calling the
result the river* — same tree, and see the next section for why that is fatal rather than
merely limited. *MFD as a channel network* — MFD is a wetness field; on the terrain measured
below, 99.2% of interior cells have more than one receiver, so it marks the whole hillslope as
river. *Sketching a path and subtracting a constant depth* — measured below: 32% of segments
run uphill. *Stamping a meander from a sine wave* — wavelength has to scale with width or the
river reads as wallpaper.

## A single-receiver network is a tree, and that is the whole problem

This is a structural claim, not a quality complaint, so it can be settled exactly.

D8 stores one receiver per cell. That makes out-degree ≤ 1 everywhere. A digraph on `N` nodes
with out-degree ≤ 1 has exactly `N − C` edges, where `C` is the number of self-receiving roots,
and a connected graph with `N − 1` edges is a tree. So the network is a **forest of `C` trees**,
and in a forest there is exactly one path from any cell to its outlet.

Now read Leopold & Wolman's definition of a braid: a reach with "relatively stable alluvial
islands, and hence two or more separate channels" [leopoldwolman1957]. Two separate channels
that leave a point and rejoin downstream *are* two distinct paths between the same pair of
nodes. That object does not exist in a forest. It is not that D8 braids badly — a braid is
**unrepresentable** in the data structure, at any resolution, for any terrain.

Measured on a 256×256 fractal dome, priority-flood filled, D8 routed
(`scratchpad/w4/d8_is_a_tree.py`):

| quantity | D8 | same terrain, MFD |
|---|---|---|
| edges | 64,516 | 259,190 |
| `edges == N − roots` | true (65,536 − 1,020) | — |
| cells with >1 receiver | **0** | 63,983 (99.2% of interior) |
| undirected cycles, `E − N + C` | **0** | 194,674 |
| confluences (in-degree ≥ 2) | 9,205 | — |
| max in-degree | 5 | — |
| longest flow path | 169 cells | — |

The two zeros are the argument. Confluences are plentiful — 9,205 of them — because *merging*
costs nothing in a tree; it is *splitting* that is impossible. Braiding and anastomosis are both
splitting.

⚠️ **MFD is not the fix.** The right-hand column has cycles, so it can in principle hold a
braid — but it puts a receiver split on essentially every cell, which is a diffuse wetness
field, not a channel network. `flow-routing.md` says exactly what you get if you try:
"thresholding an MFD field to get a network produces a smeared, braided mask". *Smeared* is
the operative word — those cycles are dispersion artefacts at cell scale, not islands.

The fix is not a different routing rule; it is **not deriving the planform from routing at
all**. Author the threads as separate edges in a graph that is allowed to be a DAG, and the
problem disappears — at the cost that [paris2023] §6.2 documents: a network that is no longer a
tree needs explicit collision handling, in three cases (upstream, downstream, disconnected).

## Width: the exponent is published, the coefficient is yours

[leopold1953] fits `w = aQ^b`, `d = cQ^f`, `v = kQ^m`, and because `Q = wdv` the exponents must
close: `b + f + m = 1`. Two triples, and confusing them is the most common error in this area:

| | b (width) | f (depth) | m (velocity) |
|---|---|---|---|
| **at a station** — one section, rising flood, p. 9 | 0.26 | 0.40 | 0.34 |
| **downstream** — many sections, constant frequency, p. 16 | **0.50** | 0.40 | 0.10 |

Both sum to 1.00 (checked in `hydraulic_geometry.py` §1). **Use the downstream triple.** An
authoring tool is comparing a headwater to a trunk, which is exactly the downstream comparison;
the at-a-station triple describes one gauge through one flood and would give you a river that
barely widens as it grows. Leopold & Maddock are candid that `b ≈ 0.5` has no explanation: "Why
this exponent `b` should so consistently be nearly equal to 0.5 in the downstream direction for
widely different rivers is not known and constitutes an important unsolved problem" (p. 51).

⚠️ **The paper does not give you a width.** It gives you a *ratio*. Of the coefficients it says
"Width and depth for a given discharge vary widely from one cross section to another and,
therefore, the intercept values, `a`, `c`, and `k`, will vary" (p. 9). So expose the anchor, not
the coefficient: the user names one river on the map and its width, and every other river
follows `w/w₀ = (Q/Q₀)^0.5`. A hard-coded `a` is a constant reconstructed from nothing.

**Two published chains disagree, and the gap is large.** [paris2023] §4 uses `w ∝ A^0.5` — width
against drainage *area*. Chaining `φ = 0.42A^0.69` [genevaux2013] into `w ∝ Q^0.5` gives
`w ∝ A^0.345` instead. Normalised to agree at 1 km², the two differ by 1.43× at 10 km² and 2.92×
at 1000 km² (`hydraulic_geometry.py` §5). Pick one and state it; do not mix them across a
pipeline, because on the trunk river the disagreement approaches a factor of three.

**Where the width stops existing.** Below about two cells there is no channel to carve
[subcell_channel] — no canonical source; standard practice is to stop carving and switch the
river to a decal, a spline or a shader once its width falls under ~2·Δx. With the `A^0.345`
chain, a river anchored at 16 cells wide reaches 2 cells at 2.4×10⁻³ of the anchor's drainage
area (`hydraulic_geometry.py` §8) — one four-hundredth of the anchor's basin. For scale on how
much of a network that is: in the basin Strahler fits, 139 of the 200 segments (69.5%) are
order 1 [strahler1957]. That is a rendering decision forced by geometry, and it is better made
deliberately than discovered as flicker.

**Depth and shape.** [paris2023] §4 pairs the width with `w = 18.8·d^1.41` (Konsoer et al. 2013,
not opened here) and holds both constant along a channel. That constancy is the approximation to
question first if a river looks uniform.

## The planform threshold, and how much to trust it

[leopoldwolman1957] p. 60 eq. (1): `s = 0.06·Q^−0.44`, with `Q` the bankfull discharge in cubic
feet per second. Above the line, braided; below it, meandering. Converted to SI:

```
S_crit = 0.0125 * Q^-0.44          # Q in m^3/s, S dimensionless
```

| bankfull Q (m³/s) | S_crit | | slope | Q above which it braids |
|---|---|---|---|---|
| 1 | 0.0125 | | 1% | 1.7 m³/s |
| 10 | 0.00454 | | 0.4% | 13.3 m³/s |
| 100 | 0.00165 | | 0.1% | 311 m³/s |
| 1,000 | 0.00060 | | 0.01% | 58,300 m³/s |

The paper's own demonstration is worth repeating because it isolates the variable: on Cottonwood
Creek the reach above the gage meanders at slope 0.0011 and the reach immediately below braids at
0.004, at the same 800 cfs, with no tributary between them. Fed into the SI line, 800 cfs is
22.7 m³/s and `S_crit = 0.00317` — the meandering reach falls below it and the braided reach
above it (`hydraulic_geometry.py` §4). The threshold reproduces its own worked example.

⚠️ **Do not present this as a law.** [candel2021] Table 1 scores it against six other
discriminators on a modern dataset: the Leopold–Wolman line classifies **79% of 126 rivers**
correctly, κ = 0.48, which they grade *moderate* agreement. The best discriminator in the table
reaches 96% and κ = 0.95, and it needs median grain size and valley slope, which an authoring
tool does not have. So: use the line, expose it as a bias the user can push, and do not build
anything that assumes it is right about a particular river.

**The better threshold, if you have a grain size.** [candel2021] §2.2 defines potential specific
stream power `ω_pot = ρgQ_ef·S_v/W_r` on a reference width `W_r = φ√Q_ef` (`φ = 4.7` sand-bed,
3.0 gravel-bed — note `√Q` is `b = 0.5` again, arriving from a different direction), then puts
the braided–meandering transition at `ω_bm = 900·D50^0.42`.

⚠️ **Both of those constants are unit-bound, and this document warns about exactly that trap two
sections later for `λ = 6.5·w^1.1`.** `W_r = φ√Q` is dimensionally `m = φ·(m³/s)^0.5`, so `φ`
carries `m^-0.5·s^0.5` and 4.7 is an SI number: feed it cfs and the width is wrong by
`√35.31 = 5.94×`. `ω_bm = 900·D50^0.42` likewise fixes a unit for `D50` that the expression does
not state — [candel2021] works in millimetres. Neither constant is dimensionless and neither
survives a unit change; convert the discharge and the grain size before you use them, or refit. The `√Q` reference width is what
makes this pattern-independent: it does not need to know the answer to compute the input.

## Two multi-thread planforms, and they are opposites

Both braided and anastomosing rivers have more than one thread, so both are unrepresentable in a
tree — and an authoring tool that lumps them will get both wrong, because they sit at opposite
ends of the energy axis.

[candel2021] eq. (7) puts the inactive–active transition at `ω_ia = 90·D50^0.42`, "defined at a
tenfold lower stream power than the ω_bm-discriminator", and anchors it on the laterally stable
reaches of the anastomosing upper Columbia. So:

| | braided | anastomosing / laterally stable |
|---|---|---|
| potential specific stream power | above `ω_bm = 900·D50^0.42` | below `ω_ia = 90·D50^0.42` |
| what holds the planform in place | nothing — it is reworked | cohesive banks |
| [candel2021] fig. 1 exemplar | Rakaia, New Zealand | Nqoga, Botswana |

An order of magnitude in stream power separates them, and it is bank strength that does it:
[candel2021] attributes the low-energy class's stability to the fact that "rivers with cohesive
banks are not able to form wide channels", and reports that this is exactly where every
discriminator does worst — 43% correct for rivers without bars. If your tool has one
"multi-channel" switch, it is authoring a braid.

⚠️ **Not verified.** The rest of the usual contrast — mobile gravel bars reworked each flood
against vegetated islands stable for centuries, a wide flat braid belt against narrow deep
channels in a wetland — is the standard landform description and appears in **no source opened
for this document**. Treat it as a sketch to design against, not as a citation.

**How many threads.** [candel2021] eq. (10) gives the bar mode `m` and eq. (11) converts it,
`B_i = (m−1)/2 + 1`. Everything in eq. (10) except `W`, `S` and `Q` is a property of the bed, so
holding the bed fixed, `m ∝ W^1.5·S^0.5·Q^−0.5`. Doubling the belt width at fixed slope and
discharge multiplies `m` by 2.83; starting from `m = 1` (bars only along the banks, `B_i` = 1)
that lands at `B_i` = 1.9, and it takes an eight-fold increase in discharge to undo it
(`hydraulic_geometry.py` §9). **Width is the strong control on
thread count**, which is convenient: it is the parameter an author already has a handle on.

**How the discharge is split between them** has no published rule [braid_flow_split] — no
canonical source; standard practice is to divide the aggregate flow among the threads by some
weighting the author sets and re-derive each thread's width from its share, which is what
[peytavie2019] §5.2 does without saying how the partition is chosen. Whatever you choose, keep
`Σ w_i·d_i·v_i = Q` so continuity survives; that is the invariant, not the split.

## Meander wavelength scales with width, not with discharge

[leopoldwolman1957] p. 59 fits `λ = 6.5·w^1.1` (feet), and is explicit that the relation is "not
a constant ratio but a power function having an exponent slightly larger than 1.0". Because the
exponent is not 1, **the coefficient is unit-dependent** — a detail that silently breaks a port.
Converted (`hydraulic_geometry.py` §2):

```
lambda = 7.32 * w^1.1              # metres, from 6.5 * w^1.1 in feet
```

Using 6.5 with metres understates every wavelength by 11.2% (`hydraulic_geometry.py` §6b). The
drift in the ratio is the whole content of that exponent: `λ/w` = 7.3 at `w` = 1 m, 9.2 at
10 m, 11.6 at 100 m, 14.6 at 1 km. Compare the paper's own reading of fig. 45B — the observed
ratio runs "from about 7 for small streams having widths of 1 to 10 feet, up to 15 for large
rivers having widths in excess of 1,000 feet" (p. 58). The fit and the eyeball agree.

The authoring consequence: a meander generator parameterised on wavelength directly will look
wrong the moment the river changes size. Parameterise on **width**, take wavelength from it, and
the trunk automatically gets long slow bends while the tributary gets tight ones. Sinuosity is a
separate knob; [leopoldwolman1957] uses ≥ 1.5 to call a reach a meander and says plainly that
"this value is an arbitrary one".

For bend geometry rather than bend spacing, [peytavie2019] §5.2 makes the cross-section
*asymmetric* where curvature is high and symmetric where it is low — deep on the outside of the
bend, shallow on the inside. That one change is most of what makes a carved meander read as a
river rather than as a bent pipe.

## Ordering: a generator, and a cheap check

[strahler1957] p. 914 gives the ordering rule, credited as only slightly modified from Horton
(1945, which could not be obtained — see `papers-flow.md`): finger-tip tributaries are order 1,
and two channels of order *k* joining make order *k*+1. Horton's law of stream numbers says the
counts per order form an inverse geometric sequence, whose ratio is the **bifurcation ratio**.

Two uses, and they are not equally good.

**As a check: excellent.** Count segments per order in whatever network you produced and plot
`log N` against order: it must be a straight line, of slope `−log₁₀ r_b`. Strahler's fig. 3 (Smith 1953
data) gives counts 139, 46, 11, 3, 1 for orders 1–5; refitting those by least squares reproduces
`b = 0.547` against the paper's printed 0.541 and `r_b = 3.53` against its 3.52
(`hydraulic_geometry.py` §7). This is the drainage-network analogue of the `log S` vs `log A`
check in `stream-power.md`: cheap, quantitative, and it catches networks that look plausible in
a hillshade.

**As a parameter: poor, and Strahler says so.** "The number is highly stable and shows a small
range of variation from region to region or environment to environment, except where powerful
geologic controls dominate" — with Coates' measured ranges of 4.0–5.1 (order 1→2) and 2.8–4.9
(2→3). A knob whose real-world range is 3 to 5 is not a knob; it is a constant with noise. Ship
it as a validation readout, not a slider.

⚠️ **Ordering is also not a generator on its own.** A five-order tree grown at exactly
`r_b = 3.52` has 154 leaves; the measured basin has 139. The law constrains counts, and says
nothing about where the channels go. [genevaux2013] §4 is the version that works as a generator:
Horton–Strahler *branching rules* inside an expansion grammar, with the user controlling the
probability of continuation, symmetric branching and asymmetric branching. Those probabilities
are the real knobs — their fig. 8 shows `Ps = 0.7` producing over 75% order-1 streams and highly
curved watersheds, while `Pa = 0.7` produces long main stems and watersheds of comparable size.

## Carving: centreline, profile, valley, and the order it must happen in

The carve itself is one line [genevaux2013] §7:

```
h(p) = u_z(p) + delta(d(p))
```

`u(p)` is the projection of `p` onto the centreline, `u_z` its bed elevation, `d(p)` the signed
distance, and `δ` a stored 1-D profile — piecewise, per river type, and it can carry layers for
bedrock, water and sand. Put it into the terrain with [genevaux2013]'s *replace* operator,
`h_C = (1−w_B)h_A + w_B h_B`. ⚠️ **That expression is a convex blend, and it only "replaces"
because `w_B` is compactly supported and saturates**: it is 1 inside the channel and 0 beyond the
support radius, so the channel wins where it is defined and the terrain is untouched outside it.
Written with a `w_B` that merely tapers — a Gaussian, or a falloff with no flat top — the same line
is an ordinary blend and the channel bed comes out a fraction of the depth you asked for. The name
is a property of the weight, not of the formula. **Valley widening is the same operator with a wider support and a shallower profile**
— [genevaux2013] §6.2 computes terrain elevation as a distance-weighted combination of the
projection on the river and the projection on the ridge, which is a valley cross-section by
construction. It is not a separate algorithm.

For the profile *scale*, [peytavie2019] §5.2 normalises each template to **unit water area** and
scales it by `a = φ/‖u‖` — cross-sectional area is discharge over velocity, which is continuity
and needs no calibration. Note what that fixes and what it leaves open: it fixes the *area*, so
the width–depth split inside the template is still yours. With [leopold1953]'s downstream
exponents, `A_xs = Q/v ∝ Q^0.9`, so a template of **fixed shape** scaled to that area gives
`w ∝ d ∝ Q^0.45` — where the measurements want `w ∝ Q^0.5` and `d ∝ Q^0.4`. Over three decades of
discharge that is 1.41× too narrow and 1.41× too deep, because `w/d` should grow as `Q^0.1` (a
factor of 2.0) and a fixed shape holds it constant (`hydraulic_geometry.py` §6). Vary the
template's aspect ratio with discharge, or accept a trunk river that is too deep for its width.

### The monotonicity problem, which is the part that actually bites

Sampling `terrain − depth` along an authored path does not give a bed that falls downstream, and
a bed that does not fall holds standing water and breaks every downstream consumer.
[peytavie2019] §5.1 states both the check and the fix in one sentence: "We check that the river
height is monotonically decreasing. When this fails, we propagate the heights of the river
trajectories downwards."

Measured on a 512×512 terrain with 170 m of relief along the path
(`scratchpad/w4/carve_monotone.py`):

| path | uphill segments | extra excavation, mean | deepest final channel |
|---|---|---|---|
| drawn across the grain (12.4 km sine) | **289 of 899 (32.1%)** | 107.9 m | 138.6 m |
| traced along a valley, ±3 cells of jitter | 4 of 71 (5.6%) | 0.03 m | 4.6 m |

Both were asked for a 4 m channel. The first got a 139 m canyon, because the running minimum has
to saw through every ridge the path crosses. So the rule is not "run the fix" — it is **the fix
tells you whether the path was authorable**. Report the deepest cut back to the user; when it
exceeds the requested depth by more than a small factor, the path is fighting the terrain and
the honest response is to say so, not to excavate.

⚠️ **Direction matters and the wrong one is silently plausible.** Enforcing monotonicity by
raising each cell above its receiver (an upstream pass) also produces zero uphill segments — and
on the same path it lifted 112 samples *above the original terrain*, i.e. it built an aqueduct.
Always relax **downstream**, in flow order.

**Ordering when rivers meet.** Carve in downstream order over the network so a tributary's mouth
is fixed before the tributary is cut, and adjust at junctions after propagating, as
[peytavie2019] §5.1 does. For multiple threads over the same ground, [peytavie2019] §5.2 gives
the rule outright: "in order to preserve flow, the final height of the riverbed is set as the
minimum height over all channels" — a `min`, never a blend, or the bar between two threads rises
into a dam.

**Junction angle** is not free either: near perpendicular when the two flows differ markedly,
narrow when they are similar. [genevaux2013] §6.1 and [paris2023] §6.1 print the same rule six
years apart; [paris2023] attributes it to Hooshyar et al. 2017, which was not opened here. The
two share authors, so treat this as one rule stated twice rather than as corroboration.

## The crossovers that change the answer

- **Braided or meandering** flips at `S = 0.0125·Q^−0.44` (SI). At 0.4% slope that is 13 m³/s; at
  0.1% it is 311 m³/s.
- **Braided or anastomosing** is not a fuzzy boundary but a *tenfold* gap in potential specific
  stream power: `ω_bm = 900·D50^0.42` above, `ω_ia = 90·D50^0.42` below [candel2021].
- **Carve or don't** flips at about two cells of width [subcell_channel]. Above it, geometry;
  below it, a decal.
- **Author the network or route it** flips on whether you need multi-thread planforms or user
  control of position. If you need neither, `flow-routing.md` is cheaper and always consistent.
- **Tree or DAG** flips the moment a second thread exists, and the cost is the collision handling
  of [paris2023] §6.2 — not a small addition.
- **Constant width per channel or width per node**: constant is what [paris2023] §4 ships. With
  `w ∝ A^0.345`, a reach spanning a factor 1.32 in drainage area varies 10% in width, a factor 2
  varies 27%, and a factor 10 varies 121% (`hydraulic_geometry.py` §10). Split the edge at every
  confluence and the question stops arising.

## Where this sits in the pipeline

Strictly authoring-time. Consumes drainage area from `flow-routing.md` (or replaces it entirely,
if the network is grown rather than extracted). Produces a heightfield that `stream-power.md`
can then relax — and note the direction of that interaction: a carved channel with uniform `K`
is a step the solver will erase, exactly as `stream-power.md` says about carved waterfalls. If
you want the carve to survive an erosion pass, either run the carve *after* it, or pin it with
lithology. The water surface itself belongs to `water-closed-vs-open.md` and `shallow-water.md`;
this document produces the bed the water sits in, not the water.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Rivers never divide around an island, at any resolution | The network is a single-receiver forest; out-degree ≤ 1 makes a split unrepresentable | Author threads as separate graph edges; stop deriving planform from routing |
| Marking "river" from MFD paints the whole hillslope | MFD splits at 99.2% of interior cells — it is a wetness field | Use MFD for masks (`flow-routing.md`); take channels from the authored graph |
| Trunk river barely wider than its tributaries | The at-a-station triple (`b = 0.26`) used where the downstream one belongs | `b = 0.5`, [leopold1953] p. 16 |
| Widths correct at one scale, wrong at another | `w ∝ A^0.5` and `w ∝ Q^0.5` chained through `φ = 0.42A^0.69` mixed in one pipeline; they differ 2.92× over three decades | Pick one exponent and state it |
| Absolute widths wrong everywhere by a constant factor | A hard-coded coefficient `a`; the paper publishes the exponent only | Anchor on one user-named river, scale by `(Q/Q₀)^0.5` |
| Carved river holds standing water | Bed sampled as `terrain − depth`; 32% of segments run uphill on a path drawn across the grain | Downstream running minimum with an epsilon slope [peytavie2019] §5.1 |
| Carved river becomes a canyon far deeper than requested | The monotone fix sawing through the ridges the path crosses | Report the deepest cut; treat a large excess as "this path is not authorable" |
| The channel floats above the terrain in places | Monotonicity enforced by an *upstream* pass, raising cells above their receivers | Relax downstream, in flow order, never upstream |
| A bar between two braid threads rises into a dam | Threads blended instead of combined | `min` over all threads' beds [peytavie2019] §5.2 |
| Meanders read as wallpaper | Wavelength authored directly instead of derived from width | `λ = 7.32·w^1.1` (m), and let width come from discharge |
| A ported meander generator produces wavelengths 11% short | `λ = 6.5·w^1.1` used with metres; the exponent ≠ 1, so the coefficient is unit-bound | 7.32 in metres, 6.5 in feet |
| Braid appears on a lowland river, or a meander on a mountain torrent | Planform authored by hand instead of from the slope–discharge line | `S = 0.0125·Q^−0.44`; expose it as a bias, not a truth |
| A "multi-channel" river in a flat wetland looks like a gravel braid | Braided and anastomosing conflated; they differ by 10× in stream power | Switch on `ω`: below `90·D50^0.42` it is the low-energy multi-thread, not a braid [candel2021] |
| Thread count insensitive to the parameters the user is moving | `m ∝ W^1.5·S^0.5·Q^−0.5` — width dominates | Drive thread count from belt width [candel2021] eqs. (10)–(11) |
| Bifurcation-ratio slider does nothing perceptible | Real-world `r_b` spans about 3–5; it is a constant with noise | Show it as a validation readout; author with branching *probabilities* [genevaux2013] §4 |
| Carved channel vanishes after the erosion pass | Uniform `K`; the solver erases a step nothing pins | Carve after erosion, or pin with lithology (`stream-power.md`) |
| Small tributaries flicker or disappear at distance | Their width has fallen below ~2 cells | Below ~2·Δx stop carving and switch representation [subcell_channel] |
| A meander bend looks like a bent pipe | Symmetric cross-section carried through the bend | Asymmetric profile where curvature is high [peytavie2019] §5.2 |
