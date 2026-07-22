# Archetype compositions

![archetypes](archetypes.png)

Six **complex archetypes** from `references/20-archetypes.md`, each assembled from the verified
Legal-Order blocks and rendered on a ~2 km tile. Regenerate with `python archetypes.py`.

These are the **province** altitude — *one recognisable place* — the level between `graph_demo.py`
(the generic baseline pipeline) and a single landform. The whole lesson of `20-archetypes.md` is
that these are **not new algorithms**: each is the same Legal Order with the dominant agent
switched. Adapt, don't paste — they are illustrative *kinds* of place at one small extent, not
scale models of the named exemplars.

| Tile | Archetype | The switch (diff from baseline) | `09` signature to look for |
|---|---|---|---|
| top-left | **Alpine orogen** | fbm+ridged uplift → droplet fluvial → talus to repose | dissected ridges & dendritic valleys; slopes pack toward repose |
| top-mid | **Canyon + strata** | plateau + one deeply-incised meandering trunk, then **terrace** (strata) on the walls | a deep trunk in high ground (high hypsometric integral); stepped benches |
| top-right | **Erg dune sea** | dominant agent → **aeolian** (Werner slab CA) | transverse dunes ⟂ wind; low relief; slopes ≤ sand repose |
| bot-left | **Fjord coast** | glacial **U-troughs** carved, then flooded to sea level (z=0) | long narrow drowned inlets reaching the open-ocean edge |
| bot-mid | **Lunar cratered** | regime switch: fluvial **OFF**, **impacts** dominate (power-law crater sizes) | a saturated field of overlapping pits; no connected drainage |
| bot-right | **Tower karst** | dominant agent → **dissolution** (lower ∝ fracture density) | residual towers over a low alluviated plain (bimodal elevation) |

The numbers printed by `archetypes.py` (relief, 99th-percentile slope, hypsometric integral,
depression storage) are those signatures made quantitative — the by-eye montage's numeric partner,
and the same tells `tests/test_archetypes.py` asserts. The most important assertion is the plainest:
**no composition blows up** — the guard that catches an erosion instability a thumbnail would hide
(the alpine talus step went unstable on razor ridges until its `factor` was lowered).

**Tier.** Every archetype is tier **L** — a composition. The *components* keep their cited tiers
(`00`); the assembly invents no new citation. The glacial-erosion agent of the real Alps and the
tower-karst dissolution law are approximated here from the available blocks, not verified sims — see
`references/12-glacial-coastal.md` and `references/11-geological.md` for the deeper treatments.
