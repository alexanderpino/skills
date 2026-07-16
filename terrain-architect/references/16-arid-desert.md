# Arid & Desert Landforms

Contents: [The arid frame](#the-arid-frame) · [Yardangs](#yardangs-wind-abrasion) ·
[Inselbergs & bornhardts](#inselbergs--bornhardts) · [Alluvial fans & bajadas](#alluvial-fans--bajadas) ·
[Playas](#playas) · [Desert pavement](#desert-pavement) · [Wadis & aeolian deposits](#wadis--aeolian-deposits)

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
bevelled plain and no inselbergs; you need the fracture/hardness field.

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
