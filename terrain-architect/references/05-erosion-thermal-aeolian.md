# Thermal & Aeolian Erosion

Contents: [Thermal](#thermal-erosion-musgrave-et-al-1989) · [Repose angles](#repose-angles) ·
[Talus](#talus--scree-olsen-2004) · [Mass wasting](#mass-wasting-landslides--debris-flows) ·
[Aeolian overview](#aeolian-erosion) ·
[Bagnold physics](#bagnold-1941--the-physics) · [Werner dunes](#werner-1995--the-implementable-model) ·
[Anchored dunes](#anchored-dunes--when-sand-meets-an-obstacle)

## Thermal erosion (Musgrave et al. 1989)

*Runnable reference: `reference-impl/erosion_thermal.py`, verified by `tests/test_thermal.py` —
converges below the repose angle; the per-neighbour distance correction cuts the plus-shaped grid
artefact; double-buffered and deterministic (`09`).*

Material on a slope steeper than the repose angle collapses. Cheap, robust, and the fastest
way to make hydraulic erosion output look right.

```
thermalStep(h, talusAngle, c):
    Δ = zeros_like(h)                            # double-buffer: accumulate, then apply

    for each cell i:
        maxExcess = 0;  dTotal = 0;  steep = []
        for n in 8 neighbours:
            d = h[i] - h[n]
            dist = (n is diagonal) ? cellSize * SQRT2 : cellSize
            dLimit = tan(talusAngle) * dist      # per-neighbour, distance-correct
            if d > dLimit:
                steep.append((n, d, dLimit))
                dTotal += d
                maxExcess = max(maxExcess, d - dLimit)   # excess over that neighbour's OWN limit

        if dTotal == 0: continue
        moved = c * maxExcess / 2                # c ≈ 0.5; the /2 keeps the steepest pair stable
        for (n, d, dLimit) in steep:
            give = min(moved * d / dTotal, (d - dLimit) / 2)   # per-pair clamp — see below
            Δ[i] -= give
            Δ[n] += give

    h += Δ
```

**Details that matter:**

- **The per-neighbour distance correction.** Using a single `talus` value for all 8 neighbours
  means diagonals are held to a slope √2 times too steep, so material preferentially collapses
  along the cardinals and you get a plus-shaped artefact on every cone. Compute `dLimit` per
  neighbour.
- **Double-buffer.** In-place updates make the result order-dependent. This is the classic
  source of "my thermal erosion looks different when I enable multithreading".
- **`moved = c·maxExcess/2`, and the excess must be measured against the *right* limit.** The
  `/2` is a stability factor — without it, moving the full excess overshoots and the surface
  oscillates. `c ∈ [0.3, 0.7]`. And the excess is `d − dLimit` for that neighbour, not
  `d − talus` with a single cardinal limit: mixing a diagonal's `d` with the cardinal limit is
  the same distance bug as above, hiding in the volume term.
- **The per-pair clamp, or why `min(share, (d − dLimit)/2)` is there.** Sizing the total from
  the single steepest neighbour and splitting it `d/dTotal` is an abstraction (Olsen 2004's
  fast form), not physics — with several severely over-steepened neighbours the split can hand
  one pair more than its own excess while starving another, which on rough meshes shows up as
  micro-oscillation that never quite converges. Clamping each transfer to half *that pair's*
  excess makes every pair individually non-inverting, so the step is stable regardless of how
  many neighbours are steep — the convergence claim below then holds unconditionally. The cost
  is one `min`.
- **Iterations.** 20–100 passes, and it converges — running more does nothing once every
  slope is at or under repose. That convergence is a useful property: you can run it to a
  fixed point and the result is deterministic and resolution-independent.
- **It is diffusion in disguise.** Thermal erosion is a slope-limited diffusion, so it can
  stand in for the `D·∇²h` term in stream power (`04`) and give you the repose behaviour for
  free. Recommend this substitution — it's one node instead of two.

**In the graph: thermal goes *after* hydraulic.** Hydraulic over-steepens; thermal relaxes.
Reversed, hydraulic just re-steepens what thermal fixed and the thermal pass is wasted work.

**Št'ava's sediment slippage** (`04`) is thermal erosion restricted to the deposited sediment
layer, run inside the hydraulic loop. Same code, different input field, much lower talus angle
(loose sediment ~30° vs bedrock ~45°).

## Repose angles

Use real numbers. They are the difference between a landscape and a lumpy noise field.

| Material | Angle of repose | `tan` |
|---|---|---|
| Dry loose sand | 30–35° | 0.58–0.70 |
| Wet sand | 45° | 1.00 |
| Gravel | 35–40° | 0.70–0.84 |
| Scree / talus (angular rock) | 35–40° | 0.70–0.84 |
| Loose snow | 35–40° | 0.70–0.84 |
| Soil | 30–45° | 0.58–1.00 |
| Fractured bedrock | 45–55° | 1.00–1.43 |
| Competent rock face | up to vertical | — |

A **spatially varying talus angle** driven by a material mask is nearly free and buys a lot:
rock faces stay vertical, scree cones sit at 37°, sand at 33°. One extra input to the node.

## Talus / scree (Olsen 2004)

Olsen's contribution is a fast approximation for real-time use: rather than the full
8-neighbour redistribution, do a **two-pass sweep** (left-to-right then right-to-left, then
the same vertically), moving material down-gradient in a single pass per direction. It
converges to nearly the same result in a fraction of the iterations. Worth it if thermal is
in an inner loop; unnecessary as a one-off post-process.

The distinctive **scree cone** below a cliff needs one more thing than plain thermal: a
*source*. Thermal alone just relaxes what's there. To get real talus fans, add material at
the cliff base proportional to the cliff's exposed area, then run thermal:

```
screeSource = cliffMask * weatheringRate      # cliffMask = slope > ~55°
h += dilate(screeSource, radius)              # deposit at the base
run thermal with talusAngle = 37°
```

## Mass wasting: landslides & debris flows

Thermal is the *slow* hillslope process (grain-by-grain creep to repose). Mass wasting is the
*episodic* one — a slope fails all at once — and it is where the big mountain scars, debris fans,
and dammed lakes (`03`) come from. Two implementable pieces:

**Where slopes fail — wetness-coupled infinite-slope stability (Montgomery & Dietrich 1994).** The
canonical shallow-landslide model (the basis of SHALSTAB) couples the topographic wetness machinery
(`03`/`06`) to the standard infinite-slope criterion: a slope fails where it is **steep** and
**wet**, and the drainage area `A` is what makes it wet.

```
failureMask(slope, A, soilDepth):
    # cohesionless infinite slope: fails when driving stress exceeds friction
    wet = min(1, K_w * A_specific / sin(slope))      # relative saturation ∝ a/sinθ (TOPOG/TWI, 06)
    FS  = (1 - wet * ρw/ρs) * tan(φ) / tan(slope)    # factor of safety; φ ≈ internal friction ≈ repose
    return FS < 1                                     # unconditionally unstable where slope ≥ φ
```

The topographic result is exactly what you see in real ranges: failures concentrate in **steep,
convergent hollows** (high `A_specific`, high slope) — not on ridges. That is why the mask needs
`A` from `03`, not slope alone.

**What a failure does — slide, then flow.**

```
landslide(h, failureMask):
    scar   = evacuate soil/regolith (11) down to a failure plane inside failureMask
    runout = route the mass down steepest descent (03), stopping by a rule below
    run thermal (above) on scar + deposit                # both relax to repose
```

**How far it goes — the stop rules.** "Deposit where it flattens" is the crude default; two
grounded rules replace it:

- **Angle of reach (Fahrböschung — Corominas 1996).** The line from scar crown to deposit toe dips
  at a reach angle `α`, so the runout length is simply `L = H / tan(α)` for fall height `H` — and
  **`α` shrinks as volume grows** (mobility increases with size, measured across 204 landslides):
  rockfalls ~30–45°, small slides ~20–30°, large debris flows and rock avalanches well under 10°.
  One empirical number, P-tier, and it makes big failures dramatically longer than small ones —
  which is the visible difference between a scree chute and a valley-crossing rock avalanche.
- **Voellmy two-parameter friction (Voellmy 1955** — the rheology under RAMMS-class runout
  models): deceleration = `μ g cosθ` (Coulomb) `+ g v²/ξ` (turbulent drag). Integrate `v` along
  the steepest-descent path; the mass stops where `v` reaches 0. `μ ≈ 0.05–0.3` (lower = more
  mobile), `ξ ≈ 100–1000 m/s²`. Use this when the path matters (bends, run-up on the far valley
  wall — which the reach angle can't do); use the reach angle when only the footprint matters.

- A **shallow landslide** evacuates the *regolith* (the `11` soil layer — bedrock stays), leaving a
  spoon-shaped scar and a lobate deposit at the slope base. In the layer stack it is a transfer
  within the solid cover, and it is why the mass budget (`SKILL.md`) matters: scar volume = deposit
  volume.
- A **debris flow** is the wet, mobile case — the physics is **Iverson 1997** (*The physics of
  debris flows*, Rev. Geophys. 35): a solid–fluid mixture, not a landslide and not a river. For
  terrain, the honest realisation is a *look*: route the failed mass down the channel network
  (`03`), scouring the gully, and deposit it as **levéed lobes on the fan** below (`16` alluvial
  fans — debris-flow fans are the steep ones). Rounded levées flanking the runout path are the tell.
- **Rockfall** is the dry, steep end-member — the scree source above already models it.

**Integrating the Voellmy runout.** Step the mass down the path **in space, not time** — the
work–energy form drops the timestep entirely. With $\frac{dv}{dt}=v\frac{dv}{ds}$ (arc length $s$),
the Voellmy law $\frac{dv}{dt}=g\sin\theta-\mu g\cos\theta-\frac{g\,v^2}{\xi}$ becomes
$\frac{d}{ds}\!\left(\tfrac12 v^2\right)=a$, so each step updates $v^2$ over the **along-slope path
length** $\Delta s=\sqrt{\Delta x_{\text{horiz}}^2+\Delta h^2}$ — *not* the horizontal cell step, or
friction work is under-counted by $\cos\theta$:

$$v_{n+1}^2 = v_n^2 + 2\,\Delta s\left(g\sin\theta_n-\mu g\cos\theta_n-\frac{g\,v_n^2}{\xi}\right),\qquad \Delta s=\frac{\Delta x_{\text{horiz}}}{\cos\theta}$$

```
voellmyRunout(h, start, μ, ξ, cellSize, g=9.81, v0=0, dir=downslope):
    p = start;  v = v0;  track = [p]                # v0 from the scarp drop, or 0
    while p in bounds:
        # next cell: steepest-descent neighbour if any lies downhill, else COAST straight
        # on momentum — this carries the mass across a flat and partway up an opposing wall
        # (the run-up the reach angle can't reproduce). Stopping at a flat under-runs L.
        n, dir = steepestDescentElseMomentum(h, p, dir)     # 03 receiver, or keep dir
        horiz  = dist(p, n) * cellSize              # map step: cellSize or √2·cellSize
        Δh     = h[p] - h[n]                         # >0 downhill, <0 climbing
        θ      = atan2(Δh, horiz)
        Δs     = hypot(horiz, Δh)                    # ALONG-SLOPE path length — the integration step
        a      = g*sin(θ) - μ*g*cos(θ) - g*v*v/ξ     # drive − Coulomb − turbulent
        v2     = v*v + 2*a*Δs                        # d(½v²)/ds = a  →  v²_next = v² + 2·a·Δs
        if v2 <= 0: deposit(p); break                # decelerated to rest → the runout toe
        v = sqrt(v2);  p = n;  track.append(p)
    return track
```

An **uphill step** ($\theta<0$) makes $\sin\theta$ negative, so the flow decelerates climbing an
opposing wall and can stop partway up — the run-up the reach angle can't reproduce. In the
pure-Coulomb limit ($\xi\to\infty$) this reproduces $L=H/\tan\alpha$ with $\tan\alpha=\mu$ (Corominas,
above) — the verification to run. A single steepest-descent path is **F-tier**;
a spreading debris lobe wants the depth-averaged solver (Iverson).

*Runnable reference: `reference-impl/runout.py`, verified by `tests/test_runout.py` — runout length
on a constant ramp matches `L = H/tan(α)` (`09`).*

**Tier.** The susceptibility model is **P-tier** (Montgomery & Dietrich 1994); the debris-flow
physics is **P-tier** (Iverson 1997) but *not implementable as written* — like Bagnold, cite it for
*why*; the terrain realisation (scar + runout + thermal) is **F-tier**, no canonical graphics paper.

## Aeolian erosion

Two separable effects, and most graphs only need the second:

1. **Deflation** — wind stripping fines from exposed surfaces. Slow, subtle, mostly affects
   material masks rather than height.
2. **Dune formation** — sand transport and deposition. This is the one with visual payoff.

Wind erosion is ★★★★ mostly because the physics reference (Bagnold) is not implementable as
written and the implementable model (Werner) is rarely cited.

## Bagnold (1941) — the physics

The reference for *why*, not *how*. Two results worth knowing:

**Threshold friction velocity** — below this, no grains move at all:

```
u*_t = A * sqrt( ((ρ_s − ρ_a) / ρ_a) * g * d )
```

`A ≈ 0.1` for turbulent flow, `ρ_s` ≈ 2650 kg/m³ (quartz), `ρ_a` ≈ 1.22 kg/m³, `d` = grain
diameter. For 250 µm sand this gives `u*_t ≈ 0.2 m/s`, corresponding to roughly 5 m/s at 1 m
height. The practical consequence: **transport is threshold-driven and highly nonlinear**, so
a wind field that's uniformly just-below-threshold moves nothing, and one that's just-above
moves a lot. Averaging your wind field destroys the effect.

**Saltation flux** — the cubic law:

```
q = C * sqrt(d / D) * (ρ_a / g) * u*³
```

The `u*³` is the important part: transport scales with the *cube* of shear velocity. Doubling
the wind moves eight times the sand. This is why dunes form where they form.

You will not integrate this over a heightfield. Use it to justify parameter choices and to
tell the user why a linear wind-strength slider feels wrong.

## Werner (1995) — the implementable model

*Runnable reference: `reference-impl/dunes.py`, verified by `tests/test_dunes.py` — slabs conserved
exactly; the `p_sand > p_bare` instability sweeps ground bare between dunes; deterministic (`09`).*

*Eolian dunes: computer simulations and attractor interpretation.* A cellular automaton with
sand "slabs". This is what to actually build. It is remarkably short and it produces barchans,
transverse dunes, linear dunes and star dunes purely from the wind regime — no authoring.

```
werner(h, windDir, iterations):
    L = saltationHop                             # ~5 cells, fixed
    for it in 0..iterations:
        # 1. Pick a random cell with sand
        c = randomCellWithSand()

        # 2. Remove one slab
        h[c] -= slabHeight

        # 3. Transport downwind and try to deposit
        p = c
        loop:
            p = p + windDir * L
            if p out of bounds: wrap or discard
            if inShadowZone(h, p, windDir):
                deposit = true                   # shadow zone always captures
            else:
                prob = (h[p] > 0) ? p_sand : p_bare      # p_sand ≈ 0.6, p_bare ≈ 0.4
                deposit = (random() < prob)
            if deposit:
                h[p] += slabHeight
                break

        # 4. Avalanche both sites back to repose angle
        avalanche(h, c);  avalanche(h, p)        # = local thermal erosion, 33°
```

**The three ideas that make it work:**

1. **Shadow zone.** Cells in the lee of a crest, within a 15° angle downwind, are sheltered
   and always capture sand. This is what creates the slip face and makes dunes *migrate* and
   maintain their asymmetric profile rather than diffusing away.

```
inShadowZone(h, p, windDir):
    for k in 1..shadowLength:
        q = p - windDir * k
        if h[q] > h[p] + tan(15°) * k * cellSize: return true
    return false
```

2. **`p_sand > p_bare`.** Sand is more likely to stick to sand than to bedrock. This positive
   feedback is what breaks a flat sand sheet into discrete dunes — remove it (set both equal)
   and you get a featureless sheet forever. It is the whole instability.

3. **Avalanching after every move.** Keeps slip faces at repose. Without it the dune crest
   grows into a spike.

**Wind regime determines dune type** — this is Werner's actual result and it's free:

| Wind regime | Dune type |
|---|---|
| Unidirectional, limited sand | Barchans (crescents, horns downwind) |
| Unidirectional, abundant sand | Transverse ridges ⊥ to wind |
| Bimodal (two directions ~90–120° apart) | Linear / seif dunes, parallel to the resultant |
| Multidirectional | Star dunes |

So a wind direction that varies over the iterations (cycling between two modes, say) gives you
linear dunes for free. Expose the wind regime, not the dune type.

**Bedform hierarchy — ripples, dunes, draa (Wilson 1972).** Werner's dunes are one order of a **size
hierarchy**: wind ripples (~0.1–1 m spacing) ride on **dunes** (~10–1000 m), which in a big sand sea
ride on **draa** — mega-dunes ~1–3 km apart and hundreds of metres high. Each order correlates with
grain size, and the diagnostic is **superimposition**: smaller dunes on the flanks of a draa make a
**compound** (same-type) or **complex** (mixed-type) mega-bedform. You don't get draa from one Werner
pass — run the model at **two scales** (a coarse, slow draa field with a fine dune field riding it),
which is why a Namib-type erg (`20`) reads as dunes-on-dunes, not a single wavelength.

**Sand availability mask.** Werner assumes an infinite sand sheet. For terrain, gate it: sand
only exists where a mask says so (low elevation, low slope, downwind of a source). Slabs that
land outside the mask are lost.

**Cost.** One slab move per iteration is slow; a 1k map wants ~10⁷ iterations. Parallelise by
batching: pick many source cells at once, but ensure their transport paths don't overlap
within a batch, or accumulate with atomics as with droplets (`04`).

**Coupling to the rest of the graph.** Dunes are a surface layer, not bedrock. Keep them in a
separate `sandDepth` field added to `h` at the end, so that (a) the dune material mask is free,
and (b) hydraulic erosion in a later wet-phase can strip them correctly.

## Anchored dunes — when sand meets an obstacle

Werner (above) makes **free** dunes — barchans, transverse, linear, star — that self-organise on an
open sheet and *migrate*. Put a fixed obstacle in the transport path (a scarp, a hill, a mountain
front, a boulder, a bush) and the steered wind field (`13`) plus Werner's shadow zone pin the sand
*to the topography* instead: **anchored** (topographically controlled) dunes. This is the "wind
guided around a hill, dropping its sand against it" case, and it needs no new machinery — the wind
field already speeds up over crests and separates in the lee (`13`), the shadow zone already captures
sand behind a crest (above), and the `sandDepth` mask already gates where slabs survive. The one new
control is **how steep the windward face is**, because that decides whether the sand stops *in front
of*, climbs *over*, or falls *behind* the obstacle (Tsoar 1983, wind-tunnel echo and climbing dunes).

- **Echo dune — deposited upwind of a steep face.** When the windward slope is steep — above
  **~60°**, where the boundary layer separates into a fixed reverse eddy (Qian et al. 2011, wind
  tunnel, stoss slopes 35–90°) — grains drop in that stalled zone *ahead* of the obstacle, building a
  ridge parallel to the cliff and **separated from it by a near-bare corridor** whose width scales with
  obstacle height. It is the upwind stagnation the mass-consistent solve (`13`) already implies, made
  visible: streamlines that cannot climb the face pile their load in front of it.
- **Climbing dune — mantled on the windward slope.** On a gentler face — **≲50°** (Tsoar 1983), below
  the separation threshold — the sand-laden wind flows up and over, and sand **mantles the windward
  face**, thinning up-slope as the crest speed-up (`13`, Jackson & Hunt) holds the finest grains in
  transport. (The 50–60° band is transitional.) A climbing dune banks *onto* the hill; an echo dune
  stands *off* it.
- **Falling dune — cascaded into the lee.** Sand that crosses the crest drops into the wind shadow
  behind the obstacle and cascades down the lee slope — **Werner's shadow zone at hillslope scale** —
  a lee-side tongue pointing downwind, often fed through a gap or col.
- **Sand ramp — the composite apron.** A thick wedge of aeolian sand **plus** colluvium/talus (above)
  and fluvial debris (`16` fans) banked against a range front, usually relict. Its size and *mixed
  provenance* are what separate it from a climbing/falling dune (Lancaster & Tchakerian 1996): it is a
  `16` bajada-scale deposit with an aeolian fraction, not a live bedform, and reads as a paleoclimate
  archive rather than a moving dune.
- **Shadow dune / nabkha — the small-obstacle tail.** A single boulder or bush sheds a tapering
  **sand shadow** in its lee (Hesp 1981); anchored by vegetation it is a **nebkha** (`13`, Tengberg &
  Chen 1998). The same shadow-zone capture, one obstacle wide.

**Implementation.** Reuse the pipeline — steer the wind (`13`), run Werner with the `sandDepth` mask,
and add an **obstacle mask** (terrain the slabs cannot climb: high, steep bedrock) whose windward-face
angle selects the form:

```
anchoredDunes(h, sand, windField, obstacleMask):
    for each obstacle cell reached by a transport path:
        θ_w = windwardSlope(h, windField)              # 13 upwind gradient, at the face
        if θ_w > θ_separate:  deposit UPWIND   (echo)  — reverse eddy ahead of the face; θ_separate ≈ 60°
        else:                 climb the face (climbing) — sand mantles, thinning upslope (≲50°)
        deposit in the lee shadow zone         (falling) — Werner shadow (above), at hill scale
    # sand ramp = the above + colluvium (05) + 16 fan fill, banked and mostly relict (not a live dune)
```

**Tier.** The forms are **L** — there is no anchored-dune algorithm; they compose from `13` + the
shadow zone. The airflow/bedform behaviour that grounds the windward-angle gate is **P**: Tsoar 1983
and Qian et al. 2011 (echo/climbing — the windward-inclination control and the ~60° separation
threshold), Hesp 1981 (shadow dunes), Lancaster & Tchakerian 1996 (sand ramps); Pye & Tsoar 2009 is
the synthesis. **The tell:** an echo dune stands off the cliff
behind a bare strip, a climbing dune mantles the windward face, a falling dune tongues into the lee —
put the sand on the wrong side and the wind direction reads as reversed. Slabs stay conserved
(Werner).

**Vegetation can anchor a dune too — parabolics & blowouts.** Swap the fixed obstacle for **plant
cover** and you get the other anchored family. A **blowout** is an erosional deflation hollow bitten
into a vegetated dune where the cover breaks (Hesp 2002); it seeds a **parabolic dune** — a U-shape
whose **arms trail *upwind*, pinned by vegetation, while the bare nose migrates downwind** (the mirror
image of a barchan, whose horns point downwind). It is the same cover-vs-transport switch as the nebkha
(`13`, and the `sandDepth` availability mask above): cover below threshold releases sand, cover above
holds the arms. The parabolic geometry itself is textbook-standard but has **no single canonical
paper** — author the form (anchored arms + advancing nose) and cite Hesp 2002 for the blowout that
starts it. The full **coastal foredune / dune-belt** system — beach-fed, vegetation-built — and its
implementable DECAL model are worked in `12` (coastal dunes & foredunes).
