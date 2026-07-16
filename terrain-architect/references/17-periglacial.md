# Periglacial & Permafrost Landforms

Contents: [The periglacial frame](#the-periglacial-frame) ·
[Patterned ground](#patterned-ground-kessler--werner-2003) · [Solifluction](#solifluction) ·
[Rock glaciers](#rock-glaciers) · [Thermokarst & pingos](#thermokarst--pingos) ·
[Blockfields](#blockfields)

## The periglacial frame

Cold ground that is **not glaciated** — the frost-dominated zone beyond the ice. Permafrost is only
a temperature threshold in `13`; this file is the *landforms* frost builds. One process underlies
most of them: **freeze–thaw**, which heaves, sorts, and creeps the regolith. Texts: **French 2018**,
*The Periglacial Environment* (4th ed., Wiley); **Washburn 1979**, *Geocryology*. Mostly **L/F-tier** —
frost geomorphology has process models but few graphics papers, so the honest move is the recipe.

## Patterned ground (Kessler & Werner 2003)

Stone circles, polygons, and stripes that **self-organize** on frost-heaved ground — and the
canonical model is by **B.T. Werner**, the *same* author as the dune model in `05`. **Kessler &
Werner 2003** (*Self-Organization of Sorted Patterned Ground*, Science 299) show the patterns emerge
from two feedbacks: freeze–thaw **sorts** stones from soil laterally, and expanding soil domains
**squeeze and align** the stone domains.

```
patternedGround(stones, soil):        # a cellular self-organization, like Werner's dunes (05)
    for iterations:
        # 1. Lateral sorting: frost heave pushes stones toward stone-rich neighbours
        move stones toward local stone concentration      # positive feedback → stone domains
        # 2. Squeezing: expanding soil domains elongate and confine the stone domains
        align stone domains under confinement
    # form is slope-selected: circles/polygons on flat ground → stripes on slopes
```

The payoff detail (Kessler & Werner): **slope is the control** — on flat ground the feedbacks make
circles and polygons; add a slope and the same feedbacks stretch them into downslope **stripes**.
It is the same "the feedback *is* the pattern" lesson as Werner's dunes (`05`), which is why the
same modeller found both.

## Solifluction

Slow downslope flow of water-saturated regolith over a frozen or impermeable base — **the
periglacial hillslope-transport process**. Quantitatively it is a diffusion-with-a-frost-term:
**Matsuoka 2001** (*Solifluction rates, processes and landforms: a global review*, Earth-Science
Reviews 55) compiles rates and shows they scale with frost penetration, moisture, and slope.

```
solifluction(h, soilMoisture, frostCycles):
    flux = K_soli * frostCycles * soilMoisture * sin(slope)     # cm/yr
    h = diffuse downslope with this flux                        # like thermal (05), frost-gated
    # depth-dependent: fastest at the surface, zero at depth → tongue-shaped LOBES, not uniform lowering
```

Same *shape* as thermal creep (`05`) — a slope-driven diffusion — but gated by **freeze–thaw
cycles and moisture**, so it runs only where it is cold and wet, and it builds **lobes**
(tongue-shaped fronts with steep risers) rather than lowering the slope uniformly.

## Rock glaciers

Tongues of ice-cemented talus (or debris-covered ice) that **creep** downslope like a glacier but
are made of rock + ice — the bridge between talus (`05`) and glacier flow (`12`). **Wahrhaftig &
Cox 1959** (*Rock glaciers in the Alaska Range*, GSA Bulletin 70) is the founding study: they flow
by internal ice deformation (Glen's law, `12`) at cm–m/yr and carry their surface into **transverse
ridges and furrows** with a steep frontal lobe at the debris repose angle.

```
rockGlacier: talus (05) + interstitial ice that creeps (Glen's law, 12 — but ice-poor and slow)
  source:  a frost-shattered headwall feeding debris (blockfields, below)
  flow:    slow SIA-style creep (12) of the rock+ice mass
  surface: transverse ridges/furrows (flow structures) + a steep frontal lobe at rock repose (05)
```

## Thermokarst & pingos

The two ground-ice landforms — one collapses, one bulges:

- **Thermokarst** — melt of ground ice makes the surface **collapse** into pits, hollows, and thaw
  lakes. Author it as *localized subsidence* where an ice-rich mask thaws: `h -= meltDepth *
  iceContent`. The thaw lakes are `03` closed basins — do not fill them.
- **Pingo** — a **mound** with an ice core, pushed up by water freezing beneath it — the inverse of
  thermokarst. A dome primitive (`10`) with an ice-core uplift; it collapses to a rampart-ringed
  crater when the core eventually melts.

Both are **F-tier** ground-ice features (French 2018); the heightfield captures the mound and the
pit but not the ice lens driving them.

## Blockfields

Felsenmeer — plains of frost-shattered angular blocks mantling gentle high-latitude or
high-altitude surfaces. A **scatter (`07`) + material (`06`)** result on low-slope, cold, high
terrain: dense **angular** clasts — *not* rounded, because there was no fluvial transport to round
them (contrast the river clasts of `04`, where `roundness` grows downstream). They are shattered in
place by freeze–thaw and feed the rock glaciers above.
