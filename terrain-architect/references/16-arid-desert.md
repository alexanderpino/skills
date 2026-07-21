# Arid & Desert Landforms

Contents: [The arid frame](#the-arid-frame) · [Yardangs](#yardangs-wind-abrasion) ·
[Inselbergs & bornhardts](#inselbergs--bornhardts) · [Alluvial fans & bajadas](#alluvial-fans--bajadas) ·
[Playas](#playas) · [Evaporite crusts & salterns](#evaporite-crusts--salterns) · [Desert pavement](#desert-pavement) · [Wadis & aeolian deposits](#wadis--aeolian-deposits) ·
[Implementation contract](#implementation-contract)

## The arid frame

Deserts are not "terrain with the water turned off" — they are terrain where **wind and rare,
violent water** do the work perennial rivers do elsewhere, and where **weathering products are
not flushed away**, so they pile up. Three consequences drive every landform below:

1. **Sparse, flashy runoff.** Rain is rare but arrives as flash floods; channels are dry most of
   the time (wadis) and braided/depositional when they run.
2. **Wind is a first-class agent.** Abrasion (yardangs) and deflation (pavement, playas) shape
   rock and strip fines — the `05` aeolian machinery, now *erosional*, not only depositional.
3. **No base-level flush.** Endorheic basins (playas) terminate drainage internally — there is no
   ocean to carry sediment away, so everything accumulates *in the basin*.

Standard text: **Cooke, Warren & Goudie 1993**, *Desert Geomorphology* (UCL Press). Most desert
landforms are **L-tier** compositions; the honest move is the recipe, not a fabricated "yardang
algorithm".

## Yardangs (wind abrasion)

Streamlined ridges carved from cohesive sediment or soft rock by **abrasion + deflation**, aligned
with the prevailing wind — the aeolian twin of a drumlin. **Ward & Greeley 1984** (*Evolution of
the yardangs at Rogers Lake, California*, GSA Bulletin 95(7)) is the field-plus-wind-tunnel
reference: mature yardangs approach a **teardrop 1:4 width:length**, with abrasion strongest at the
blunt windward nose and deflation down the flanks.

```
yardang(h, windDir, softMask):
    # carve streamlined ridges from a soft, cohesive substrate (playa clay, loess, tuff)
    align = anisotropic noise with its long axis ‖ windDir          # 01 domain-warp along wind
    for iterations:
        abr = K_abr * windExposure(p, windDir) * softMask
        h -= abr * saltationWeight(heightAboveFloor(p))             # abrasion is BOTTOM-weighted
        deflate loose fines below the Bagnold threshold (05)
    # teardrop ridges: steep blunt nose upwind, tapering lee tail
```

The detail that sells it: **abrasion is bottom-weighted** — saltating sand only reaches ~1 m up,
so yardangs are undercut at the base and the nose is steepest low down (Ward & Greeley). Which
grains are in the abrading stream comes from the `05` Bagnold threshold.

## Inselbergs & bornhardts

Isolated steep-sided hills standing above a plain — **bornhardts** (bald domes) and their
block/boulder variants. **L-tier**, and the mechanism is the same as tower karst (`11`) but in
*insoluble* rock: **differential subsurface weathering, then stripping** (Twidale 1982, *Granite
Landforms*, Elsevier). Massive, unfractured rock resists weathering at the weathering front while
fractured rock around it rots to regolith; strip the regolith (`03` fluvial + `05` deflation) and
the massive core stands out.

```
inselberg(h, fractureField, baseLevel):
    resistance = smoothstep(hi, lo, fractureField)     # low fracture = massive core (01/07 noise)
    weather    = (1 - resistance) * weatheringRate      # rot fractured rock → regolith (soil production, 11)
    strip regolith down toward baseLevel                # fluvial + deflation remove it
    # massive cores stand above the stripped plain
```

This is the same "differential lowering to a base level" pattern as tower karst (`11`) and
marine/lake terraces (`12`) — **base level is the master parameter**. With uniform rock you get a
bevelled plain and no inselbergs; you need the fracture/hardness field. The **same recipe at outcrop
scale**, keyed to joint spacing, makes **tors** (`11` weathering microforms).

## Alluvial fans & bajadas

Where a confined mountain channel debouches onto a basin floor, flow **unconfines, spreads, and
drops its load** → a semiconical **fan**; coalesced fans along a range front form a **bajada**.
Flagged L-tier in `00`; the process is deposition-dominant transport at a slope break, driven by
**debris flows and sheetfloods**, not perennial rivers (**Blair & McPherson 1994**, J. Sedimentary
Research A64; **Bull 1977**, *The alluvial-fan environment*, Progress in Physical Geography 1).

```
alluvialFan(h, apex, sedimentFlux):
    for cell p downfan of apex:
        r = |p - apex|
        h += sedimentFlux * exp(-r / L) * radialSpread(p, apex)   # deposit thins downfan
    # profile concave: steep near apex (debris-flow), gentler distal (sheetflood)
    # AVULSION: periodically switch the active lobe — a fan is built by a channel that wanders
```

Two details: **fan slope increases with debris-flow dominance and decreases with drainage-basin
size** (Blair & McPherson), and **avulsion** — the feeder channel periodically jumps to build a new
lobe — is what makes a fan a *fan* rather than a single incised gully. Coalesce several fans along a
front and you have a bajada.

## Playas

The floor of an **endorheic** (internally drained) basin — a dead-flat clay/salt pan that floods
thinly and evaporates. This is the terminal case of the `03` sink: a basin with **no outlet**,
where water leaves only by evaporation, so salts and the finest sediment accumulate to a
mirror-flat surface at the basin low point.

```
playa: an endorheic basin floor (03 sink, left UNFILLED)
  surface = dead flat at the basin minimum (evaporite + clay)
  no channel crosses it — drainage TERMINATES at the playa (accumulation ends here)
  salt/clay material (06); often below sea level and dry (Death Valley — the 03 sea-level note)
```

Do **not** breach or fill a playa basin in `03` (like karst and crater lakes, it is a genuine
closed basin). Mark it; drainage should terminate there, not route through it.

## Evaporite crusts & salterns

A playa (above) is the *dry* end of a closed salt basin; keep standing brine in it — a **salina**, a
coastal **solar saltern**, a supratidal **sabkha** — and evaporite chemistry paints it. As brine
concentrates it precipitates minerals **in order of increasing solubility**: carbonate first, then
**gypsum** (~130–150 g/L), then **halite** (~300–350 g/L), then the very soluble Mg–K "bittern" salts
(Warren 2016; Eugster & Hardie 1978). So a concentrating basin maps **mineralogy to salinity**, i.e. to
distance from the inflow: an outer carbonate/gypsum belt grading inward to a white halite pan. Three
settings differ by *where* the salt grows — a **sabkha** grows evaporites *displacively within the
sediment* (nodular "chicken-wire" gypsum), a **salina** grows *bottom crystals* under standing brine,
a continental **playa/salar** dries to an efflorescent surface crust (Kinsman 1969; Warren 2016).

**Surface texture.** A subaerial **halite crust buckles into polygons with upturned "tepee" thrust
ridges** — desiccation, thermal cycling and crystallisation pressure heave it, and ridges re-nucleate
over the same lows across crust generations (Lokier 2012). A `06`/`18` displacement texture, not a
heightfield landform — the arid cousin of mudflat desiccation cracks.

**Why a saltern goes pink — and why it's a *material*, not a mineral, colour.** Pure halite and gypsum
are white to clear; the electric pink of the Camargue *salins*, Great Salt Lake's north arm or the San
Francisco Bay ponds is **biogenic pigment in the brine**. At NaCl saturation the red comes from the
**bacterioruberin** carotenoids of halophilic **Archaea** plus the **β-carotene** of the alga
***Dunaliella salina***, which packs >10% of its dry weight as β-carotene under salt-and-light stress
(Oren & Rodríguez-Valera 2001; Oren 2005). Because it tracks salinity, the colour is **concentric
zoning**, not a flat tint: green/brown concentrator ponds → orange as *Dunaliella* stresses →
**pink/red crystalliser** at saturation. Treat it as an `18` material/biofilm property keyed to a
salinity field, layered over the white salt — the same "colour is a material property" rule as desert
varnish (pavement, above) or Yellowstone's microbial mats (`20`).

**Tier.** Evaporite mineral zonation, sabkha/salina/playa morphology and the salt-crust polygons are
**P** (Warren 2016; Eugster & Hardie 1978; Kinsman 1969; Lokier 2012); the pink is **P** for the
mechanism (Oren & Rodríguez-Valera 2001; Oren 2005), **L** for exact per-pond hues. **The tell:**
colour banded by salinity, not painted uniform — white where the brine is fresh or the crust dry, red
only at saturation.

## Desert pavement

A mosaic of tightly packed surface clasts over fine soil. The old model was a **lag** — deflation
strips fines and leaves the stones behind. The modern, correct model (**McFadden, Wells &
Jercinovich 1987**, Geology 15) is the opposite: pavement clasts are **born at the surface** and
stay there while wind-blown dust accumulates *beneath* them — the stones ride up on accreting
aeolian silt. For terrain this is a **material + scatter** result, not a height one:

```
desertPavement = clast scatter (07) on flat, stable, OLD surfaces (low slope, low erosion)
  clasts sit ON a fine aeolian / vesicular horizon (born-at-top, McFadden 1987) — not a deflation lag
  a 06 material mask + dense clast instances (07); it flattens and darkens (desert varnish) the surface
```

The tell that it's pavement and not scree: the surface is **smoother** than its surroundings and
the clasts are a single interlocking layer, because the fines came *up* under them rather than
being blown *out* from between them.

## Wadis & aeolian deposits

- **Wadi / arroyo** — a normally-dry channel that runs only in flash floods; braided,
  sediment-choked, flat-floored between steep cut banks. Route it with `03`, but expect
  **transmission loss**: the flood soaks into the bed and shrinks downstream, so discharge
  *decreases* downstream — the opposite of a humid river (`03` water sources & discharge).
- **Aeolian deposits — the deposition side of `05`, beyond dunes.** **Sand sheets**: flat,
  low-relief sand where vegetation or coarse grains suppress dune slip-faces. **Loess**:
  wind-blown silt that blankets terrain downwind of a source, draping relief like snow — a
  thickness field added over the existing height, thickest on upwind-facing slopes and thinning
  downwind, smoothing and rounding the landscape (the aeolian counterpart of a snow mantle, `13`).
- **Obstacle dunes — sand banked against topography.** Where the sand-transporting wind meets a
  fixed obstacle it drops **anchored** dunes instead of migrating ones: **echo** dunes upwind of a
  steep face, **climbing** dunes mantling a gentle windward slope, **falling** dunes cascading into
  the lee, and **sand ramps** — thick composite aeolian + colluvial + fluvial aprons banked against a
  range front (Lancaster & Tchakerian 1996). The full mechanism and the windward-angle gate live in
  `05` (anchored dunes); here it is a `16` deposit keyed to a mountain front, close kin to the bajada.

## Implementation contract

| Process | Fields and units | Locality / tier | CPU/GPU placement | Decisive oracle |
|---|---|---|---|---|
| Yardang abrasion | `height:m`, `wind:unit-vector+m/s`, `softness:[0,1]`, sediment thickness `m` | directional NEIGHBOURHOOD, T1/T2; bake for long fetch | GPU directional exposure sweep + ping-pong abrasion; scalar CPU truth | ridges align with wind; mature width:length approaches 1:4; removal is strongest near the base |
| Inselberg weather/strip | `height:m`, `fracture:[0,1]`, regolith `m`, base level `m` | NEIGHBOURHOOD plus regional base level, T2/T3 | CPU/GPU weathering and transport passes; regional base level is baked | low-fracture cores remain high; uniform fracture produces no isolated residual |
| Fan/bajada deposition | `sedimentFlux:m³/s`, channel curves, height/sediment `m` | channel-network GLOBAL, T3 bake | CPU graph traversal or staged GPU raster deposition after routing | deposit mass matches supplied load; thickness decays downfan; repeated avulsion creates distinct lobes |
| Playa | basin IDs, spill level `m`, water/salt/sediment thickness `m` | hydrological GLOBAL, T3 bake | CPU basin graph; runtime only updates shallow water/material state | basin has no outflow, floor is level within tolerance, salts/sediment accumulate rather than disappear |
| Pavement / loess | stability/age masks, clast `PointSet`, loess thickness `m` | LOCAL/NEIGHBOURHOOD, T0/T1 | GPU masks + deterministic scatter; directional loess gather | clasts stay on old low-erosion surfaces; minimum spacing holds; loess thins downwind and conserves deposited mass |
| Wadi transmission loss | discharge `m³/s`, permeability, channel graph | drainage GLOBAL, T3 or declared watershed job | CPU receiver stack; material/detail may refine at runtime | discharge may decrease along a reach but never becomes negative; channels still terminate at the declared sink |
| Obstacle dune / sand ramp | `sandDepth:m`, steered `wind:m/s` (`13`), obstacle mask, windward angle `θ` | aeolian NEIGHBOURHOOD keyed to a baked obstacle+wind field, T2/T3 | GPU Werner slabs (`05`) gated by a baked obstacle/wind field; ramp fill baked | echo deposit sits upwind of the face behind a bare corridor; climbing sand mantles the windward slope, falling sand only in the lee; slabs conserved |

**Boundary and determinism.** Wind fetch uses an explicit upwind boundary; endorheic basins are
marked before generic fill/breach; every avulsion and scatter decision derives from the root seed.
All transport uses double buffering or staged deltas. A runtime chunk may add pavement, loess
breakup and local abrasion only when its apron covers the declared fetch; basin topology, fans and
wadi discharge remain baked/global fields.

**Failure signatures:** yardangs cross the wind → exposure field wrong; plus-shaped abrasion →
stencil anisotropy; fans create sediment → source/sink budget broken; a river exits a playa →
closed-basin mask lost; pavement appears on active fans → stability/age gate missing; a falling
dune on the windward side → wind direction or the lee shadow test reversed.
