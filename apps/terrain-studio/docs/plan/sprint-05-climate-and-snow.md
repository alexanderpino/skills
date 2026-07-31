# Sprint 5 — Climate & snow (L4): moisture, typed climate, continued state `[K]`+`[E]`

**Goal.** Complete D7 L4 and make the Snow Rule real before export tries to enforce it. Terrain Studio
already computes temperature, sun visibility, wind, and snow, but several products live on hidden
node-instance/field properties and there is no `moisture` field. This sprint moves climate onto Sprint
2 typed ports, adds absolute precipitation, makes Snow moisture-driven, fixes known hex defects, and
emits auditable continued state.

**Depends on:** Sprint 2 typed ports/registry, Sprint 3 cover state, Sprint 4 hydrology (meltwater and
continued water drivers). **Implements:** D7 **L4**, removes the Snow Rule exemption created in Sprint
2, closes `C6`, and supplies the real prerequisites for export profiles.

**Doctrine in force.** `moisture` is absolute mm/yr; a normalized companion is optional. New snowfall
is `moisture × freezeFraction(temperature)`. Snow found in a dry cell must be attributable to
mass-conserving wind loading, avalanche transport, or glacial flow. `snowDepth` is continued state:
export means initial condition + drivers + epoch, not a frozen seasonal answer.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S5.1 | Typed climate ports + hidden-state retirement | `[E]` | 5 | Temperature °C, insolation, Wind RG32F; remove `_temperatureC`/metadata dependencies |
| S5.2 | Orographic Moisture / precipitation | `[K]` | 5 | mm/yr; terrain + wind; feeds Flow, Hydraulic, and Snow |
| S5.3 | Moisture-driven Snow multi-output | `[K]`+`[E]` | 8 | height passthrough, snowDepth, meltwater/wetness; epoch + drivers |
| S5.4 | Hex snow correctness + co-evolution | `[K]` | 5 | `C6`: cell area, gradients, D6 avalanche; soil scour/wetness outputs |
| S5.5 | L4 default promotion + causal visual audit | `[C]` | 3 | moisture/snow/wind overlays; dry-snow attribution |

---

## Technical refinement

### Locked climate and migration contract

- Orographic Moisture uses the chapter-13 practical Smith–Barstad approximation: march entering
    wind rays over a serialized `climateCellSizeM` in the cited 500–1,000 m range, initially 1,000 m
    per ADR 005, condense from positive along-wind height
    gradient, deplete the parcel, and apply downwind fallout lag `windSpeed * tau`. Default
    `tau = sqrt(500 * 2000) = 1,000 s`, the geometric midpoint of chapter 13's cited characteristic-
    time range; the user authors regional supply in mm/yr and the condensation coefficient.
- Boundaries are open: supply enters only at the upwind edge, residual vapour exits downwind, and no
    sample wraps. The budget is `input supply + declared recharge = precipitation + outflow`.
    A uniform background component remains uniform on flat terrain; the orographic fraction is the
    only redistributed component. Water-body recharge is optional and explicit.
- Wind is sampled as an RG32F world-space vector field. Rays use its local direction/speed; zero wind
    yields the uniform background and zero orographic redistribution. The production field is mm/yr;
    normalization exists only in a thumbnail adapter.
- Snow uses liquid-water-equivalent accounting for **new** precipitation. `accumulationDays = 365`
    initially means one climatological year, matching the `mm/yr` input unit. `Snow/2` requires
    `densityRatio = rhoSnow/rhoWater` (finite ratio `>0`),
    `meltFactor:mm SWE/(°C·day)`, and epoch with no fabricated defaults. Existing documents migrate
    to preview-only `Snow/1`, preserving exact settled-depth behavior; upgrade never reverse-engineers
    annual moisture. Continued-state export requires Snow/2 and all authored physical data.
- Avalanche transport runs on `solidTop + snowDepth` with legal lattice neighbours, a bounded
    transportable surface layer, and the measured current `adhesion` parameter (`0.6 m` compatibility
    initial value in `src/plugins/effect/snow.js`) so steep bedrock does not create an iteration-width
    bare band. Chapter 13 identifies this as an authored holding-depth family, not a physical constant.
    Wind redistribution deposits in the downwind shadow zone and never wraps the array edge.

### Owning code surfaces and cut order

1. **R0:** enumerate `_temperatureC`, `_wind`, `_snowLayer`, solar metadata, and every consumer;
     freeze old-document climate/snow outputs and the S2 adapter rows.
2. **S5.1:** migrate Temperature/Solar and Wind products/consumers one field at a time. Remove each
     semantic side-channel read immediately after its port-aware oracle passes.
3. **S5.2:** implement climate-grid march, conservative resampling, and budget diagnostics; then
     replace the S3/S4 production uniform fixture in one integration graph.
4. **S5.3:** land saved-document migration and SWE ledger before changing Snow evaluation. Add
     accumulation, melt, avalanche, wind transport, and provenance as separately asserted terms.
5. **S5.4–S5.5:** port the same terms to D6/hex metrics, remove the Snow Rule exemption, then promote
     the default only after built-app visual and numerical evidence agrees.

### Verification matrix and Ready condition

| Invariant | Passing endpoint | Mutation that must be red |
|---|---|---|
| Moisture cause | flat/zero-wind baseline; ridge swaps with wind | slope magnitude instead of along-wind lift |
| Water budget | supply + recharge = rain + outflow | omitted parcel depletion |
| Snow Rule | zero moisture gives zero local accumulation | temperature-only snowfall |
| SWE conversion | two authored intervals/densities match analytic supply | treat mm/yr as snow metres |
| Hex transport | volume closes with D6/cell area | D8 or square area on hex |
| No hidden state | migrated graph reads only typed products | `_snowLayer`/`_wind` semantic read |

Sprint 5 is Ready when S2–S4 exit, all climate side channels have named adapter owners, and the
flat/ridge moisture mutations plus no-moisture Snow mutation have been observed red.

---

### S5.1 — Typed climate ports · `[E]` · 5 pts
**User story:** As a graph author, I can connect Celsius temperature, insolation, and wind vectors as
physical values rather than encoded scalar thumbnails carrying hidden JavaScript properties.

Migrate Temperature's Celsius/solar products and remaining Wind consumers to typed outputs. The
legacy encoded primary rasters remain compatibility views until saved documents migrate; new physical
consumers wire the typed ports. Remove reads of node-instance fields such as `_temperatureC` and
`_wind` from graph semantics. Thumbnail/color views are explicit adapters.

**Acceptance gate** — `tests/legacy/_verify_climate_ports.js`: migrated existing-node expected digests
remain unchanged through the two-cut oracle sequence defined in S2.6; typed Celsius and wind values
survive Blur/Transform only where those operations preserve their semantic contract; incompatible
tonemaps drop/reject the type. Saved pre-Sprint-2 climate graphs migrate and evaluate identically.

---

### S5.2 — Orographic Moisture · `[K]` · 5 pts
**User story:** As a terrain author, I can generate absolute precipitation from regional supply,
terrain, and wind so Flow, Hydraulic erosion, and Snow share one climate cause; later vegetation and
materials consume the same field rather than inventing their own precipitation.

Add a Moisture/Orographic Precipitation node using the locked chapter-13 march above. Inputs are final
solid height, physical Wind, regional precipitation supply, and boundary conditions; output is
`moisture` in mm/yr with an optional normalized preview adapter. `climateCellSizeM` is serialized,
validated to 500–1,000 m, and participates in cache identity.
Wire this product into the precipitation inputs introduced in S3/S4 and into Snow; remove temporary
uniform production fixtures from the default graph (fixtures remain in analytic tests).

**Acceptance gate** — `tests/legacy/_verify_moisture.js`: zero regional supply returns exact zero;
zero relief under uniform wind returns the declared baseline; an analytic ridge produces greater
windward than leeward precipitation and closes the declared domain precipitation budget. Rotating
wind 180 degrees swaps the wet/dry sides. Budget closure uses the `gamma_(N-1)` Float32 reduction
bound. At 500 m and 1 km climate cells, integrated precipitation/outflow obeys the same budget and
the lagged precipitation maximum differs by at most one coarse climate cell, the sampling limit
declared by chapter 13. Run square and hex.
- In one integration graph, the same Moisture bytes reach Physical Flow, Hydraulic, and Snow typed
    inputs; changing the field invalidates those consumers and produces no hidden fallback rainfall.

---

### S5.3 — Moisture-driven Snow · `[K]`+`[E]` · 8 pts
**User story:** As a terrain author, snow accumulation responds to available precipitation as well as
temperature, and I can route the resulting depth and meltwater independently of terrain height.

Add required typed inputs `moisture:mm SWE/yr`, `temperature:°C`, `insolation:fraction`, and
`windVector:m/s`. Emit unchanged solid height as the compatibility primary, plus
`snowDepth:m` (continued), meltwater/wetness state, and provenance channels sufficient for the dry-
snow audit. The node no longer stores the only snow result in `nd._snowLayer`. Continued output
carries an authored epoch/date and declares all drivers.

Fix the unit bridge explicitly: moisture is annual **liquid-water equivalent**, while `snowDepth` is
settled snow thickness. The node requires an accumulation interval and snow density when new snowfall
is enabled, represented as required dimensionless `densityRatio = rhoSnow/rhoWater > 0`, and also
emits `snowWaterEquivalent:m`. Local accumulation is
`moisture(mm/yr) / 1000 · days / 365 · freezeFraction / densityRatio`; degree-day melt uses the same
water-equivalent ledger with authored `meltFactor:mm SWE/(°C·day)` before conversion back to depth.
Legacy Snow/1 remains compatibility-only; no silent reinterpretation is permitted. Epoch is required
before Snow/2 export.

**Acceptance gate** — `tests/legacy/_verify_snow_rule.js`: cold + zero moisture produces exactly zero
**new** local snowfall; cold + moisture produces the analytic water-equivalent and snow-depth supply
for two density ratios and two accumulation intervals; warm cells melt according to the same
water-equivalent degree-day ledger. Any snow in a dry cell must be matched by a transport provenance channel and
balanced by removal elsewhere (`reference-impl/snow.py::dry_snow_attribution`). Remove the Snow Rule
exemption and prove a fixture Snow declaration without moisture now fails registration.

---

### S5.4 — Hex snow correctness + co-evolution · `[K]` · 5 pts
**Closes:** `C6`.

**User story:** As a terrain author, the same snowfall and melt budget produces physically
consistent snow on square and hex lattices.

Correct hex cell volume (`sqrt(3)/2·s²`), world-y gradient metric, D6 avalanche neighbours, and
lattice-aware settling. Avalanche transport co-updates `soilDepth` scour; melt co-updates wetness.
Run square and hex through the same physical-unit contract without claiming identical arrays.

**Acceptance gate** — `tests/legacy/_verify_snow_hex.js`: accumulation/melt volume uses each lattice's
cell area and closes to the same physical supply; analytic north-south and diagonal slopes report the
same world angle within one lattice quantum; a repose fixture settles to the authored angle using
only legal neighbours. The known square-D8-on-hex and missing-area-factor implementations are armed
failing fixtures. Soil scour and wetness volume close with avalanche/melt ledgers.

---

### S5.5 — L4 promotion + causal visual audit · `[C]` · 3 pts
**User story:** As a new user/reviewer, the opening climate graph contains only layers already proven
correct and exposes the causal fields needed to judge snow.

Promote the opening default to L4 only after L2/L3/L4 gates pass. Keep dressing/Colorize branches out
of the correctness default. Capture moisture, temperature, snow depth, wind, and dry-snow attribution
overlays at two zoom levels on both lattices; drifts must be leeward and dry snow attributable.

**Acceptance gate:** the default document saves/reloads/migrates with no hidden node-instance climate
state; focused climate/snow oracles, built-bundle digest, and full sweep are green; skipped types = 0.

---

## Sprint 5 exit gate

- Typed climate, moisture, Snow Rule, hex snow, co-evolution, and default-document gates are green,
  each with an armed failing fixture.
- Snow's Sprint 2 exemption is removed; no new exemption is added.
- Every continued climate/water output has a driver list and epoch contract ready for export.
- **D7 L4 is verified** — export may enforce real driver completeness rather than fixture-only rules.
