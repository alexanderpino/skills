# Lava: Generation & Simulation

The technique file for lava — rheology, the implementable simulations, cooling, and verification.
The *landform* context (edifices, fissures, flood basalts, lava worlds) is `11`; the emissive
crust material is `08`; the palette entry is `18`. This file is how you actually make lava move.

Contents: [The three properties](#the-three-properties) · [Rheology](#rheology) ·
[Choosing a simulation](#choosing-a-simulation) · [The grid sim](#the-grid-sim-ca-with-temperature) ·
[Cooling & crust](#cooling--crust) · [Channel model](#the-channel-model-flowgo) ·
[Verification](#verification) · [GPU & tiers](#gpu--tiers) · [Parameters](#parameter-reference)

## The three properties

Water-with-a-red-texture fails because lava differs from water in three coupled ways, and each is
load-bearing:

1. **Yield stress (Bingham rheology, Hulme 1974).** Below a threshold stress lava does not flow at
   all → finite thickness, steep snouts, levées. This sets the *shape*.
2. **Temperature-dependent viscosity** (Stora 1999; FLOWGO). It stiffens as it cools — the flow
   *evolves* as it advances. This sets the *behaviour over distance*.
3. **Phase change.** Below the solidus it stops being a fluid and becomes new bedrock (`11`) — the
   one material in the skill that changes stack role (`08`, `18`). This sets the *output*: a lava
   sim's product is terrain.

## Rheology

```
Bingham:   flows only where  τ > τ_y ;   above yield, strain rate ∝ (τ − τ_y) / η
Thickness: t ≈ τ_y / (ρ g sinθ)          # Hulme 1974: Y = t·ρg·sinθ — thicker on GENTLE slopes (inverse of water)
Levée:     τ_y ≈ 2 ρ g w sin²θ            # Hulme 1974 — back out yield strength from observed levée width w
Viscosity: η(T) = η_0 · exp(−b · (T − T_erupt))     # rises steeply as it cools
Yield:     τ_y(T) rises as T falls        # cooling both stiffens and strengthens
```

**Surface style is a flow-rate result, not a paint choice.** Rowland & Walker 1990 (Hawaiʻi field
record): **pahoehoe** (smooth, ropey) forms below ~5–10 m³/s volumetric flow rate; **ʻaʻā**
(clinkery rubble) above it — high strain rate tears the crust faster than it can heal. Expose the
*eruption rate* and the surface material (`18`, Macdonald 1953 classes) falls out; the same vent
can produce ʻaʻā during its high-rate phase and pahoehoe as it wanes, which is exactly what the
paired Mauna Loa flows record.

## Choosing a simulation

| Family | Reference | Use when | Tier (`00`) |
|---|---|---|---|
| **Grid / cellular automaton** | Miyamoto & Sasaki 1997 (C&G 23); **MAGFLOW** (INGV Catania — CA from a steady-state Navier–Stokes solution for a Bingham fluid, run operationally at Etna) | The terrain-tool default: heightfield-native, GPU-friendly, produces the whole flow field | P |
| **Channel (1D thermo-rheological)** | Harris & Rowland 2001, *FLOWGO* (Bull. Volcanol. 63) | An *authored* flow along a spline (`10`): predicts where it stops, its width and state down-channel | P |
| **SPH / particles** | Stora et al. 1999 | Animation of the moving flow front; graphics-native | P |

The CA is to lava what the pipe model (`04`) is to water: per-cell state, neighbour fluxes,
GPU-native. Two grounded details from the volcanology models: Miyamoto & Sasaki's contribution is
a **Monte Carlo neighbour selection** that kills the square-lattice anisotropy (the same
grid-artefact disease as D8's 45° bias, `03`, solved stochastically); MAGFLOW's is deriving the
flux law from an actual **Bingham Navier–Stokes solution** rather than an ad-hoc rule.

## The grid sim (CA with temperature)

Per-cell state: bedrock `bed` (m), lava thickness `L` (m), temperature `T` (°C or K).

```
lavaStep(bed, L, T, Δt):                      # double-buffer, like every grid sim (04, 05)
    # 1. Source: vent (point) or fissure (line, along a 02 fault) injects L at T_erupt (11)

    # 2. Bingham flux to each lower neighbour
    for each cell with L > 0, neighbour n:
        Δh = (bed + L) − (bed_n + L_n)                 # surface head, like the pipe model
        if Δh ≤ 0: continue
        τ  = ρ g L · Δh / dist                          # driving stress τ = ρgL·sinθ [Pa]
        if τ ≤ τ_y(T): continue                         # BELOW YIELD: no flow — the whole point
        q  = k · (τ − τ_y(T)) · L² / η(T)               # Bingham flux PER UNIT WIDTH [m²/s]; k ~ O(1), dimensionless
        ΔL = q · Δt / cellSize                          # flux → thickness [m] (the pipe model's step, 04)
        move ΔL from cell to n  (cap so L stays ≥ 0)

    # 3. Cooling — radiation dominates, crust insulates (FLOWGO's heat budget)
    crust = crustFraction(age, strainRate)              # 0 = incandescent, 1 = fully crusted
    T -= Δt · ε σ (T⁴ − T_env⁴) · lerp(1, insulation, crust) / (ρ c_p L)     # insulation ~ 0.01–0.1
    T -= Δt · conductionToBed(L)

    # 4. Phase change: the sim's OUTPUT is terrain
    where T < T_solidus:
        bed += L                                        # freeze → new bedrock, low K (11)
        material = pahoehoe | ʻaʻā | block              # from local flow rate (above) → 18
        L = 0
```

The details that decide whether it works:

- **The yield gate (step 2) is the shape.** Remove it and lava spreads like dyed water. It is also
  the *stopping condition*: as `T` falls, `τ_y` rises until no neighbour exchange passes the gate —
  the flow front stalls with a steep snout of thickness `≈ τ_y/(ρg sinθ)` (Hulme), unprompted.
- **Levées are emergent, but only at flow margins that cool faster.** Margin cells have more
  exposed perimeter → cool faster → yield sooner → freeze into walls while the core stays mobile
  and channelises between them. If your sim cools uniformly, you get no levées; the margin/core
  cooling asymmetry is the mechanism.
- **Crust insulation is why lava goes far.** Bare incandescent lava radiates at `σT⁴` and would
  freeze within a few hundred metres; a crusted flow loses heat 10–100× slower (the FLOWGO heat
  budget), and a **tube-fed** flow (fully roofed) barely cools at all — which is why tube-fed
  pahoehoe reaches tens of km. `insulation` is the single most look-critical parameter.
- **Anisotropy.** A deterministic 4/8-neighbour CA prints the lattice into the flow outline (the
  `05` thermal plus-artefact, again). Miyamoto & Sasaki's fix: distribute flux over neighbours
  stochastically (Monte Carlo) in proportion to the computed flux — the expected flow is right and
  the lattice disappears.
- **Mass conservation is the sim's `09` check**: `Σ erupted = Σ still-molten + Σ frozen into bed`.
  Leaks come from the flux cap and the freeze step; measure them.

## Cooling & crust

The temperature field drives everything downstream:

- **`T` → the emissive material** (`08`): crack mask × blackbody ramp, hot in the cracks, dark on
  the plates. The sim's `T` and `crust` fields *are* the material inputs — do not paint them.
- **`T` → rheology** (above): the same field that glows is the one that stiffens. One field, many
  consumers — the `18` property-bundle rule, with `T` playing the role `K` plays for rock.
- **Crust age → surface style**: young crust re-tears (ʻaʻā clinker); old undisturbed crust ropes
  and smooths (pahoehoe); a drained crusted channel leaves a **lava tube** — a void, which the
  heightfield cannot hold (`11`'s representation warning; Peytavie's Arches or a volume).

## The channel model (FLOWGO)

For *authored* flows — "a lava river from this vent, down this valley" — the 1D model is the right
tool and it is P-tier: **Harris & Rowland 2001**. March a control volume down a channel spline
(`10`), evolving its heat budget (radiation, convection, conduction, crust cover) and rheology
(crystallinity, viscosity, yield strength) until motion stops. Validated against Mauna Loa,
Kīlauea, and Etna flows (modelled lengths matched measured within ~10–40%). In a graph: the spline
+ FLOWGO march gives the *centreline and stop point*; carve the channel and levées along it (`10`
spline tools) and hand the width/state to the material.

## Verification

Lava-specific checks, in the `09` spirit — cheap, quantitative, catch what eyeballing cannot:

| Check | Must show |
|---|---|
| **Snout thickness** | `t ≈ τ_y/(ρg sinθ)` at stalled fronts — thicker on gentler slopes. If thickness is slope-independent, the yield gate is broken |
| **Stop distance vs supply** | Flows lengthen with eruption rate and insulation (FLOWGO behaviour); a flow that always crosses the map has no cooling |
| **Levées** | Frozen ridges *flanking* the channel, core drained or mobile between them |
| **No uphill lava** | `(bed+L)` monotone along any active flux edge |
| **Lava lake flatness** | Ponded lava in a closed basin (`03` no-fill list) settles to a level fluid plane |
| **Mass budget** | erupted = molten + frozen, per step and cumulative (`09` mass conservation) |
| **Plan-view outline** | No lattice-aligned lobes (the Monte Carlo check) — sweep the light (`09` sun sweep) over the frozen field |

## GPU & tiers

The CA is grid-local: **NEIGHBOURHOOD(1)** in the `14` contract, ping-pong + halo like the pipe
model (`15` grid-sim pattern), **T1 at working res / T2 amortised** at full res — and the
precedent is real: MAGFLOW was ported to CUDA (*Porting and optimizing MAGFLOW on CUDA*, Annals of
Geophysics). The emissive material evaluation is T0 (per-frame, from the baked `T`/crust fields).
An *active* eruption is the rare case where a terrain sim runs live in the engine: keep the CA on
a small active window (the dirty-tile pattern, `15`) and freeze cells out of it aggressively.

## Parameter reference

Order-of-magnitude starting points; tune against the verification table, not by eye.

| Parameter | Basalt (Hawaiʻi/Etna-style) | Notes |
|---|---|---|
| `T_erupt` | ~1100–1200 °C | Silicic lavas erupt cooler and stiffer |
| `T_solidus` (stop) | ~980–1000 °C (basalt) | Freeze threshold for step 4; flows stall a little above it as yield strength climbs |
| `η` at eruption | ~10²–10³ Pa·s | Rises orders of magnitude as T falls |
| `τ_y` | ~10²–10⁴ Pa | Hulme measured up to 10⁴–10⁶ Pa on cooler/silicic flows |
| `ρ` | ~2600 kg/m³ | |
| `ε` (emissivity) | ~0.9 | |
| `insulation` (crusted) | 0.01–0.1 | The look-critical one — sets how far flows travel |
| pahoehoe ↔ ʻaʻā | ~5–10 m³/s eruption rate | Rowland & Walker 1990 |
