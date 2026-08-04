# Engine Data Handoff & First-Class Auxiliary Maps

Contents: [Why this chapter exists](#why-this-chapter-exists) ·
[The First-Class Citizen Rule](#the-first-class-citizen-rule) ·
[State maps vs derived maps](#state-maps-vs-derived-maps) ·
[The Masking Doctrine](#the-masking-doctrine--cause-vs-effect) ·
[The Standard Map Registry](#the-standard-map-registry) ·
[Climate layer](#climate-layer) · [Geology layer](#geology-layer) ·
[Hydrology layer](#hydrology-layer) · [Geometry layer](#geometry-layer) ·
[Dynamic climate interplay — the Snow Rule](#dynamic-climate-interplay--the-snow-rule) ·
[The handoff contract](#the-handoff-contract) · [Verification](#verification)

## Why this chapter exists

Every mature terrain pipeline discovers the same defect, always too late: climate, geology, and
hydrology data bolted on after the heightmap was "done". The symptoms are canonical — a wetness
mask painted by hand because the erosion pass forgot where its water went; a soil map faked from
slope because nobody tracked what the sediment budget already knew; a snow mask on pre-erosion
aspect describing valleys that no longer exist (the Legal Order violation, `SKILL.md`). Retrofitted
auxiliary data is **brittle by construction**: it is derived from the *final* geometry when the
information it needed existed only *during* the simulation, and was thrown away.

This chapter formalises the alternative from day one: **auxiliary maps are first-class citizens of
the DAG.** They are typed, persistent, world-space fields (`SKILL.md`, Field types) that evolve
organically alongside the heightfield through every node, and they cross the tool/engine boundary
under the same contract discipline as height itself (`08`). It extends two existing doctrines to
their full generality:

- The **layer stack** (`SKILL.md`, Part 2; `08`): the surface is already a set of parallel fields,
  not one number. Auxiliary maps are the same idea applied to *everything the simulation knows* —
  not just thicknesses, but climate state, material state, and flow state.
- **"Caused, not carved"** (`SKILL.md`; the hydrology handoff): the tool exports drivers, the
  engine renders effects. This chapter is that rule promoted from a water-specific clause to the
  governing contract for the *entire* export surface.

## The First-Class Citizen Rule

**Every auxiliary layer exists as a persistent `R32F` field travelling through the DAG on a typed
port, from the node that first produces it to the emitter.** Vector-valued maps (wind, flow
velocity) travel as paired `R32F` channels (`RG32F`). No auxiliary layer is ever a private
temporary inside one node, a post-hoc raster painted at export time, or an 8-bit thumbnail of a
quantity the simulation computed at full precision and discarded. The golden precision rule of
`08` — compute in R32F, quantise once at export if at all — applies to every field in the registry
below, not only to height.

The rule has a corollary that carries most of its force:

**The co-evolution rule.** *When a node alters the terrain, it must simultaneously update every
auxiliary map its physical process touches — in the same pass, from the same intermediate state.*
Auxiliary maps are **parallel pipelines, not appended hacks**. A hydraulic erosion node does not
merely lower the height; the process it models moves soil, wets ground, and reshapes curvature,
and the node's output ports must say so:

| Node (chapter) | Writes height / layers | Must co-update |
|---|---|---|
| Hydraulic erosion — pipe / droplet / stream power (`04`) | `height`, `sedimentDepth` | `soilDepth` (cover stripped before bedrock, Št'ava layering), `wetness` (where water flowed and pooled), `flowVelocity` & `waterDepth` (the sim's own transport state) |
| Thermal / talus (`05`) | `height` | `soilDepth` (talus is loose debris — it *adds* to the cover it lands on), grain-size class of the deposit (`04`) |
| Aeolian transport / dunes (`05`) | `height`, `sandDepth` | `moisture` gating (transport stops where the bed is wet), snow redistribution where the transported medium is snow (below) |
| Glacial flow (`12`) | `height`, ice thickness | `soilDepth` (glaciers strip cover to bedrock), meltwater input to `wetness`/`flowVelocity` at the terminus |
| Surf-zone morphodynamics & tidal inlets (`12`) | `height` (breaker bars, rip channels, inlet throats, ebb/flood deltas) | `sedimentDepth`/`sandDepth` (the bar and deltas are deposits), **`flowVelocity`** (nearshore circulation — longshore current, rip feeders and jets, inlet jets), the longshore sediment budget downdrift |
| Weathering / soil production (`11`) | — | `soilDepth` (the Heimsath production function is *the* producer of this map) |
| Orographic precipitation (`13`) | — | `moisture` — and, coupled, the rainfall term of every erosion node downstream (`04`) |
| Snow & avalanche (`13`) | `snowDepth` | `wetness` (meltwater), `soilDepth` scour on avalanche tracks |

The test for a compliant node: **could the auxiliary maps have been reconstructed from the final
height alone?** If yes, they are derived maps (below) and recomputation is fine. If no — soil
depth, wetness, sediment provenance, snow load are all *path-dependent*; they encode the history
of the simulation, not its endpoint — then discarding them inside the node destroys information
that no analysis pass can recover. That destroyed information is exactly what the retrofitted
pipeline ends up faking.

State updates obey the same evaluation invariants as height (`SKILL.md`, Part 3): world units on
every map, double-buffered writes under parallelism (`15`), a closed budget for every conserved
quantity (soil and snow are *mass* — what leaves a cell arrives in another or is a named leak,
`09`), and declared boundary conditions.

## State maps vs derived maps

Two kinds of auxiliary map, with opposite lifecycle rules. Conflating them is this chapter's
version of the effect-mask/process-mask confusion (`SKILL.md`, Mask semantics):

- **State maps** are carried *through* the simulation and are path-dependent: `soilDepth`,
  `sedimentDepth`, `wetness`, `moisture`, `snowDepth`, `sandDepth`, strata exposure. They obey the
  co-evolution rule. They may **never** be recomputed from final geometry, because the geometry
  does not contain them.
- **Derived maps** are pure functions of the final fields: `curvature`, `ao`, `slope`, `aspect`,
  `insolation`, TWI. They obey the Legal Order instead: computed **after the last node that
  modifies height** (`SKILL.md`, step 10), and *recomputed, never patched* when geometry changes.
  A derived map is stale the moment any field in its input cone changes — the substrate's
  content-addressed caching (`14`) makes staleness detectable by construction; use it. A
  hand-patched curvature map is a lie with a checksum.

Some maps are hybrids and must be split explicitly: `wetness` has a state component (where water
actually flowed and infiltrated during the sim) and a derived component (TWI, the topographic
*potential* for wetness, `06`). Ship them as what they are — the state map is evidence, the
derived map is a prediction — and let the engine blend them; do not average them in the tool and
lose both meanings.

## The Masking Doctrine — cause vs effect

The separation of concerns at the boundary is absolute, and it is the whole point of the handoff:

1. **The tool defines the cause.** Static geometry, raw physical data, vector flow maps —
   world-space, unit-carrying, engine-agnostic.
2. **The engine handles the effect.** Real-time shading, SPH/FLIP particles, dynamic weather,
   foliage systems, seasonal change.

**Strict prohibition: the runtime handoff contains no baked diffuse/colour maps and no predefined
materials.** A baked albedo is a *decision* — this pixel is grass — made at bake time, at one
season, under one weather state, at one art direction, and frozen. Every one of those decisions is
the engine's to make, per frame, from the raw fields. The moment the tool ships "grass" instead of
"moisture 0.7, soil 0.4 m, slope 12°, insolation 0.8", the engine can no longer melt the snow,
brown the summer grass, or move the treeline — the cause has been discarded and only one effect
remains. (The satmap/colour-map emitter of `08` survives as a **preview and review product** —
`09`'s render modes need it — but it is not part of the runtime handoff, and no engine-side system
may depend on it.)

**The handoff:** the tool exports the raw `R32F` registry below, and the engine consumes those
buffers as **masks and drivers**:

| Engine system | Consumes |
|---|---|
| Terrain material shader | `moisture`, `temperature`, `insolation`, `soilDepth`, `strataHardness`, `curvature`, `ao`, `slope` — material resolved per-pixel, per-season, in the shader |
| Biome / foliage spawner | `moisture` (the gatekeeper), `temperature`, `soilDepth`, `insolation`, `wetness` — density functions over raw fields, not a baked biome ID (`07`, `13`) |
| Dynamic weather & snow | `moisture`, `temperature`, `insolation`, `windVector`, `snowDepth` (initial state) — the Snow Rule, below |
| Fluid / particle systems | `flowVelocity`, `waterDepth`, `waterSurface` — SPH seeding, flow-map shaders, waterfall emitters (`SKILL.md`, the hydrology handoff) |
| Engine wave synthesis (ocean/shore) | `waterSurface` (the datum), `waterDepth` (**and a wavelength-scale filtered copy** — raw bathymetry noise dithers the break line), `flowVelocity` (wave–current interaction), shore distance and beach slope — drives shoaling, refraction, breakers and run-up engine-side (`12`) |
| Wind-driven shaders (foliage sway, particles, cloth) | `windVector` — sampled directly as a flowfield |
| Audio / footsteps / physics | `soilDepth`, `sandDepth`, `wetness`, `snowDepth` — surface response from state, not from a material enum |

A biome ID map *may* be exported as a convenience product, but it is derived engine-side-esque
sugar: the contract obliges the raw fields to ship alongside it, so the engine can always
re-derive and never depends on the tool's classification.

## The Standard Map Registry

The registry the architecture must support. Every map: `R32F` (vectors `RG32F`), world-space,
unit-carrying, listed in the export manifest (below). Producers and the underlying algorithms are
routed to their chapters — this chapter owns the *contract*, not the maths.

### Climate layer

| Map | Unit / range | Producer | Notes |
|---|---|---|---|
| `moisture` | mm/yr (absolute); normalised [0,1] companion mask permitted | Orographic precipitation, Smith & Barstad (`13`); latitude bands from `25` on planets | **The absolute gatekeeper.** Biome classification (`13`), vegetation density (`07`), snow supply (below), and the rainfall term of hydraulic erosion (`04`) all read this map. No downstream system may invent its own precipitation. |
| `insolation` | received fraction vs flat unshadowed ground (can exceed 1 on equator-facing slopes; declare the range in the manifest) | The insolation pass of `06`: sun-arc sampling over precomputed per-azimuth horizon maps (Timonen & Westerholm sweep) | Terrain self-shadowing of solar radiation. Dictates where snow **melts** (sun-facing slopes — south-facing in the northern hemisphere) and where it **persists** (deep ravines, pole-facing walls that never see the sun). Distinct from `ao`: AO integrates the whole sky, insolation integrates the sun's arc. Do not substitute one for the other. |
| `temperature` | °C | Latitude base + lapse rate, 6.5 °C/km environmental (`13`) | `T(z, lat) = T_sea(lat) − Γz`, aspect-corrected by insolation. Snow line and permafrost are thresholds on this field, not separate maps (`13`, `17`). |
| `windVector` | m/s, 2D vector | Terrain-adjusted wind field: authored regional wind + crest speed-up, lee shelter, valley channelling, mass-consistent cleanup (`13`) | A **flowfield, not a parameter** — a constant wind has zero flux divergence and moves nothing (`13`). Drives wind-loading of snow (below), aeolian transport (`05`), wave fetch (`12`), fire (`13`) tool-side; drives foliage sway, particle advection, and cloth engine-side. |

### Geology layer

| Map | Unit / range | Producer | Notes |
|---|---|---|---|
| `soilDepth` | m | Soil production (Heimsath, `11`) as source; every erosion node as sink/redistributor (co-evolution rule) | Thickness of loose debris over bedrock. State map — the layered-erosion history (`04`, `11`) is unrecoverable from final height. Gates vegetation rooting (`13`), digging/deformation engine-side, and the rock-vs-cover material read. |
| `strataHardness` | erodibility `K` (yr⁻¹ in the stream-power convention, `04`) or normalised resistance | Lithology / strata stack (`11`) sampled at the current exposed surface | Resistance to erosion. As erosion exhumes deeper strata the *exposed* value changes — this map is the surface slice of the volumetric stack, re-sampled whenever height changes through a stratum boundary (`11`). Engine reads it for cliff-band materials and impact/destruction response. |

### Hydrology layer

| Map | Unit / range | Producer | Notes |
|---|---|---|---|
| `wetness` | state: [0,1] saturation; derived companion: TWI (`06`) | `13`'s `wetnessStep` — soak-where-water-stood + temperature/insolation/drainage drying (state); Beven & Kirkby TWI (derived) | **Puddling** — where water settles in the soil after flowing, not merely where it flowed. Drives mud materials, reeds and wetland vegetation (`13`), engine-side puddle shaders and rain response. Ship state and derived components separately (above). |
| `flowVelocity` | m/s, 2D vector | Routing discharge + hydraulic geometry (`03`), or the pipe sim's own velocity field (`04`), **plus the nearshore surface circulation — longshore current, rip feeders/jets, tidal-inlet and river-mouth jets (`12`)**, extended across the surf band rather than stopping at the waterline | With `waterDepth`, the complete driving data for engine-side fluid mechanics: flow-map shaders, SPH/FLIP seeding, **wave–current interaction in the engine's shore-wave band** (a rip exists for the player only if it is in this field), foam *generated by the engine* where the tool's data says the water is fast and shallow. The tool ships the vectors; it never ships the foam (`SKILL.md`). Ship the **ebb** (seaward) phase for tidal jets unless the engine carries the tidal oscillation. |
| `waterDepth` / `waterSurface` | m | Depression handling, lakes, sea level (`03`); bathymetry (`12`) | The hydrology handoff of `SKILL.md`, unchanged: separate fields, never folded into collision height. |

### Geometry layer

| Map | Unit / range | Producer | Notes |
|---|---|---|---|
| `curvature` | 1/m (profile & plan, signed) | Zevenbergen & Thorne (`06`) | Convex (ridges, exposure, erosion) vs concave (hollows, accumulation, deposition). Derived map — recompute after final geometry, from the R32F field, never from quantised height (`08`). Drives sediment/exposure material reads and engine-side detail placement. |
| `ao` | [0,1] | Horizon-angle sweep (`06`) | Sky occlusion. Derived; baked from R32F post-final-geometry. Engine uses it for ambient shading and as a "sheltered" mask (moss, debris accumulation). |

Slope and aspect ship implicitly (the engine can derive them from `height` in one pass) but *may*
ship explicitly when the engine's terrain system cannot be trusted to derive them at matching
precision; if shipped, they follow the same staleness discipline as every derived map.

## Dynamic climate interplay — the Snow Rule

Snow is where the auxiliary layers stop being independent rasters and become a coupled system —
and where a pipeline that treated them as afterthoughts visibly breaks (snow painted by altitude
alone, identical on wet windward and bone-dry leeward ranges).

**The climatic law: no moisture = no new snow.** Snowfall is precipitation that froze. The snow
*source* term is gated by both climate maps and only the climate maps:

```
snowfall(p) = moisture(p) · freezeFraction(temperature(p))     # zero wherever moisture ≈ 0
```

A rain-shadowed basin (`13`) gets no snowfall no matter how cold it is — cold deserts are deserts.
Altitude enters only through the lapse rate already inside `temperature`; any snow mask written
directly from elevation is the defect this rule exists to kill. Melt then consumes the pack where
`temperature` and `insolation` say so: sun-facing slopes clear first, shaded ravines hold snow
long after (`13`).

**The displacement exceptions.** Snow and ice *do* legitimately exist where no snow falls — but
only by **transport** of snow that fell somewhere wetter. Displacement is strictly limited to
three mechanisms, each a mass-conserving redistribution driven by maps already in the registry:

1. **Wind-loading.** `windVector` strips snow from windward slopes and crests and deposits it in
   leeward shelter — cornices at the crest line, loaded pillows in leeward ravines (`13`, the
   aeolian machinery of `05` with snow as the medium). This is how a dry lee slope carries deep
   drifts metres from bare wind-scoured rock.
2. **Avalanches.** Gravity displacement down steep slopes (Cordonnier et al. 2018, `13`): the
   pack fails above a slope threshold and runs out below, moving snow from high steep faces into
   valley floors — including dry ones — and scouring `soilDepth` along the track (co-evolution
   rule).
3. **Glacial flow.** Compressed ice flows downhill under the SIA (`12`), carrying accumulation
   from the wet, cold accumulation zone into valleys whose own climate could never sustain it.
   A glacier tongue in an arid valley is the textbook case: the ice is imported, its budget paid
   for upslope, its terminus set by melt (`temperature`, `insolation`), not by local snowfall.

Nothing else moves snow. Every cell of `snowDepth` in the export is therefore *auditable*: it is
either local snowfall (moisture-gated) or the traceable output of one of the three displacement
channels. That auditability is a verification hook (below), and it is what makes the snow read
*causal* — drifts sit leeward of the wind the `windVector` map actually contains, avalanche
deposits sit below the slopes that actually fail, glacier tongues descend from accumulation
zones that actually accumulate.

Engine-side, the same three mechanisms plus melt run in real time against the same fields — the
tool ships the initial `snowDepth` state and the driving maps (`moisture`, `temperature`,
`insolation`, `windVector`); the engine owns the falling snow, the drifting particles, and the
seasonal cycle. Cause, then effect.

## The handoff contract

The mechanics extend the Output Contract (`08`); nothing here overrides it.

- **Precision.** Every registry map ships `R32F` (vectors `RG32F`) by default. Quantisation below
  R32F is permitted per `08`'s ladder only for maps whose *sole* consumers are visual masks, and
  never for maps consumed by simulation (`snowDepth`, `flowVelocity`, `waterDepth`,
  `windVector`) or differentiated by the engine. When in doubt, ship float.
- **Manifest.** The `08` manifest gains a layer table — one entry per exported map: name, unit,
  range, format, state-vs-derived kind, and the content hash of the field it was derived from
  (derived maps only). The hash is the staleness contract made checkable engine-side: an engine
  that loads `curvature` whose parent hash does not match `height`'s is loading a lie, and can
  say so.
- **Naming.** The registry names above are the wire names. An engine adapter may re-map them; the
  tool never re-names per engine (`SKILL.md` — nothing engine-specific goes upstream, and the
  emitter is the only place engine conventions exist).
- **Tiling.** Auxiliary maps tile under exactly the height rules: aprons wider than the maximum
  transport distance for anything a sim wrote (`08`), GLOBAL fields (flow accumulation, anything
  downstream of routing) sliced from a global solve, never computed per-tile (`03`, `14`).
- **Vector encoding.** `windVector` and `flowVelocity` ship as world-space `(u, v)` in m/s,
  RG32F, +X east / +Y north, stated in the manifest. Never normalised (speed is data), never
  encoded into hue, never snapped to lattice directions (`26`, world-space rule).

## Verification

The `09` posture applies: every claim above is checkable, so check it.

- **Co-evolution budget.** Run any erosion node with soil tracking on a closed domain: total
  solid mass (`height` + `soilDepth` + `sedimentDepth` deltas) is invariant or the leak is named
  and measured (`09`, mass conservation; mechanised as
  `reference-impl/tests/asserts.py::assert_layer_budget`, which sums the *stack*, not the
  layers separately — the layers legitimately exchange mass). A node that changed height without
  touching the maps its process implies fails review by inspection — the output-port list is the
  tell.
- **Snow audit.** Assert: every cell with `snowDepth > 0` and `moisture ≈ 0` is attributable to
  wind-loading (leeward of `windVector`), an avalanche runout (below a failed slope), or glacial
  transport (connected to an accumulation zone through the ice-flow field). Unattributed dry snow
  is a broken Snow Rule. Mechanised as `reference-impl/snow.py::dry_snow_attribution` — a
  *necessary-condition* audit (a transport path must exist), which is exactly enough to catch the
  hand-painted snow mask it exists for.
- **Staleness.** Recompute every derived map from the final R32F fields and diff against the
  export; any mismatch means a patched or pre-final-geometry map escaped (`14`'s cache makes this
  cheap — the check is a hash compare).
- **Range & NaN sweep.** Every map within its declared range, `NaN` only where the manifest says
  `NaN` is the mask convention (`08`).
- **The cause test, by eye.** Render `moisture`, `snowDepth`, and `windVector` together (`09`
  review modes): drifts must sit leeward, snow must track moisture + altitude and not altitude
  alone, wet valleys must be the ones water actually reached. If the auxiliary maps look
  plausible in isolation but mutually contradictory, the co-evolution rule was skipped somewhere
  — find the node.
