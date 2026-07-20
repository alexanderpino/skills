# Surface Materials

Contents: [A material is a property bundle](#a-material-is-a-property-bundle) ·
[The palette](#the-palette) · [Rock is a family](#rock-is-a-family) ·
[One field, many consumers](#one-field-many-consumers) ·
[Implementation contract](#implementation-contract)

## A material is a property bundle

Most of a planet's surface is rock — but "rock" is not one material, and a terrain needs far more
than one. The trap is to treat a material as *a colour* (an albedo, a splat channel). A material is
a **bundle of coupled properties** that the same `MaterialField` value carries into every part of
the pipeline:

| Property | Drives | Lives in |
|---|---|---|
| Erodibility `K` | how fast erosion cuts it | `11`, `04` |
| Repose angle | how steeply it stands (thermal) | `05` |
| Cohesion / permeability | slumping; how it holds vs sheds water | `05`, `13` moisture |
| Grain size / roundness | bedload, scree, sand, mud | `04` |
| Appearance (albedo family, roughness, jointing, emission) | the synthesised texture; glow for molten materials | `08` |
| Stack role (solid cover / fluid / transient) | walk / swim / melt | `08` layer stack |

Define a material and you must define *all of these, consistently*. Sand that erodes like sand but
stands at a rock's repose angle, or snow that renders white but never melts, is an **incoherent
material**. This is why `MaterialField` is a first-class type (`SKILL.md`): it is not a texture ID,
it is the tuple above, and every downstream node reads a different slice of it.

## The palette

The surface-material classes a generator needs, with where each property table already lives:

| Class | Members | Key properties |
|---|---|---|
| **Bedrock** | igneous (granite, basalt); sedimentary (sandstone, limestone, shale, chalk); metamorphic (schist, gneiss, marble, slate) | `K` by lithology (`11`); jointing → the Voronoi/Gabor pattern in synthesis (`08`); steep repose |
| **Regolith / soil** | USDA texture: sand → loam → clay (12 classes); plus laterite, podzol, peat | Produced by weathering (`11` soil production); cohesion & permeability by texture (clay holds water, sand drains); fertile → vegetation (`13`) |
| **Sand** | desert, beach, black volcanic | Loose; repose ~34° (`05`); migrates as dunes (`05`); grain 0.06–2 mm (`04` Wentworth) |
| **Gravel / scree / cobbles / boulders** | talus, river gravel, bar clasts | Coarse (`04` grain size); steep repose; angular (frost/talus, `17`/`05`) vs rounded (fluvial, `04`) |
| **Mud / silt / clay** | river banks, tidal flats, playa floor, lake bed | Fine, cohesive, low permeability, wet; desiccation cracks when it dries |
| **Vegetation ground cover** | grass, moss, lichen, tundra, forest-floor litter | The *ground* appearance (distinct from scatter `07`); placed by climate/biome (`13`); softens erosion (`13`, Cordonnier 2017) |
| **Snow / firn / ice** | seasonal snow, firn, glacier ice, sea ice | Transient/fluid stack role (`08`); accumulates & melts (`13`); flows (`12`) |
| **Water** | river, lake, sea | Fluid layer — swimmable, dynamic surface, tides (`08`, `03`, `12`) |
| **Crusts & evaporites** | salt flat, biological soil crust, desert varnish, coral | Thin surface layers; salt from endorheic evaporation (`16` playa); coral builds reefs (`12`) |
| **Char & ash (burned)** | charred soil, ash dusting, snag litter | A disturbance state, by burn severity (`13`); ash is a *transient* cover — blows and washes away; burned soil is water-repellent → erosion spike (`13`, `05`) |
| **Volcanic** | fresh basalt (pahoehoe / ʻaʻā / block — Macdonald 1953), tephra / ash, obsidian | Low `K` when fresh; ash mantles like snow (`11`); dark albedo; surface texture by flow type (`11`) |
| **Molten lava** | flows, lakes, lava-world "seas" | The one material that **changes stack role**: a fluid layer (`08`) that freezes into new bedrock (`11`, Hulme 1974 rheology); carries `T`; emissive crust cracks (`08`) |

Grain-size classes (boulder → clay) are the Wentworth scale (`04`); the soil-texture classes (the 12
sand/silt/clay mixtures) are the **USDA soil texture triangle** (Soil Survey Manual, USDA Handbook
18); repose angles per material are in `05`; erodibility `K` per lithology is in `11`.

## Rock is a family

"Rock" splits three ways, and the split shows up in *every* consumer — erosion, appearance, and form:

- **Igneous** (granite, basalt) — hard, low `K` (`11`), massive or columnar jointing, forms resistant
  highs; basalt dark, granite pale and often weathered to grus and boulders (inselbergs, `16`).
- **Sedimentary** (sandstone, limestone, shale, chalk) — layered (`11` strata), variable `K` (soft
  shale slopes, hard sandstone caprock → mesas), limestone dissolves (karst, `11`); *bedded* jointing
  → horizontal anisotropy (Gabor, `08`) in the synthesised texture.
- **Metamorphic** (schist, gneiss, marble, slate) — foliated and anisotropic; slate splits in sheets,
  gneiss is banded — an anisotropic appearance (`08` Gabor) and structurally-controlled erosion.

So a graph that ships one "rock" material is impoverished. Lithology *is* a field (`11`), and it
drives both the erosion (`K`) and the appearance (jointing pattern, colour) — the same field into two
consumers, which is the property-bundle point again.

## One field, many consumers

The material field is written once — from lithology (`11`), deposition (`04`, `05`, `12`, `16`), and
climate (`13`) — and read by everyone: erosion takes `K` and repose, moisture takes permeability, the
mask stack takes it for splat and colour (`06`), appearance synthesises from it (`08`), and the engine
takes the stack role and physics. Keep the slices consistent and a "sandy" region erodes, holds
water, looks, and walks like sand *everywhere*. Let them drift — a colour here, a `K` there — and you
get the classic incoherent terrain where the ground *looks* like one thing and *behaves* like another.

## Implementation contract

**Field layout.** Keep stable material identity separate from derived blend weights:

```text
MaterialDesc:
  stableId, stackRole
  erodibilityK, reposeTan, cohesion, permeability
  grainMinM, grainMaxM, densityKgM3
  albedoFamily, roughnessRange, normalFamily, emissivePolicy

MaterialField: stableId or compact mixture indices
MaterialWeights: per-cell soft weights, sum = 1
LayerField: bedrock + soilDepth:m + sandDepth:m + waterDepth:m + snowDepth:m
```

| Operation | Locality / tier | CPU/GPU placement | Oracle |
|---|---|---|---|
| Lithology/material lookup | LOCAL, T0 | constant/structured buffer lookup on CPU/GPU | same stable ID yields the same physical bundle on every backend |
| Analysis-driven weights | LOCAL or small NEIGHBOURHOOD, T0/T1 | compute after final geometry/analysis | finite weights in `[0,1]`, partition sums to 1 within tolerance |
| Layer erosion/deposition | NEIGHBOURHOOD, process tier | same staged transport pass as `04`/`05` | layer thickness never negative; source/sink mass closes |
| Climate/season overlay | LOCAL/T0 or amortised T1 | runtime compute over persistent base material | removing snow/wetness restores the unchanged base identity |
| Texture/map synthesis | LOCAL/T0/T1 | GPU-native LUT/noise/triplanar synthesis | albedo contains no directional lighting; normals are unit length; output is resolution-consistent |
| Physics/collision export | LOCAL, publish stage | CPU packing or GPU readback as engine requires | solid/fluid/transient stack role agrees with walk/swim/melt behavior |

Use structure-of-arrays or compact GPU tables rather than branching on large material objects per
cell. Version `MaterialDesc` independently from texture assets: changing `K`, repose or
permeability changes terrain behavior and invalidates process caches even when albedo is unchanged.
Material IDs survive palette reorder and serialisation.

**Runtime policy.** Base lithology and durable deposited layers are persistent/global truth.
Runtime may synthesize appearance, wetness, snow and local disturbance from them, but chunk unload
cannot regenerate away consumed soil or deposited sediment. Publish collision, material weights
and visible layers atomically with the refined height.

**Failure signatures:** weights do not sum to one → seams/energy gain in blends; sand appearance
with rock repose → property bundle split; water folded into collision height → unswimmable sea;
normal/AO baked after R16 quantisation → combs/rings; a texture-only material change alters erosion
cache → physical and appearance versions coupled incorrectly.
