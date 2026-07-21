# Archetype Blueprints

The **province** altitude of composition. `00`'s landform table composes *one landform*
("a waterfall = a knickpoint"); `13` composes *one world* (one substrate, masks vary
parameters). This file sits between them: *one recognisable place* — the Alps, the Grand Canyon,
the Namib, Niagara, Victoria Falls — as a **worked assembly** of the families in the Legal Order.

**These are regime settings over the Legal Order, not algorithms.** Read `SKILL.md` first. Every
blueprint here is that order run once with four things changed: the uplift field (`02`), the `K` /
lithology field (`11`), the climate (`13`), and the on/off of the optional branches — glacial
(`12`), karst (`11`), coastal (`12`), aeolian (`05`). The Alps and the Appalachians share every
node; they differ in *regime* — age, glaciation, lithology, uplift history. That is the whole
lesson, and it is why these belong in the skill instead of undercutting it.

**Prime directive: adapt, don't paste.** A blueprint pasted as a fixed pipeline is exactly the
landform-as-algorithm defect this skill exists to prevent (`SKILL.md`, `00`). Each entry is a
*starting regime and a set of tells* to tune to the brief's extent, resolution and story — not a
recipe to run unread. If you copy one without changing a parameter, stop.

**Every entry is tier L** — a composition. The *components* keep their cited tiers (`00`); the
assembly invents no new citation. Where a place's specific number would be nice (a retreat rate, a
dune height) and isn't verified here, the entry omits it — `00`'s citation discipline does not
relax because the subject is famous.

**Every entry carries a verification signature** (`09`). A blueprint without "here is what right
looks like" is the plausible-looking wrongness the skill is built to catch. The signatures lean on
`09`'s tools: the **slope histogram** (does it peak at the repose angle, or at the steeper
landslide threshold?), the **hypsometric (area–altitude) curve** (convex = youthful, sigmoid =
mature, concave = old — a one-glance maturity read; Strahler 1952, a `09` check),
**drainage continuity** (rivers reach base level, don't stop), and the **cross-valley profile**
(V = fluvial, U = glacial).

**Exemplars are illustrative, not targets.** "Alpine-type" is the transferable archetype; the
European Alps, the Southern Alps of New Zealand and the Caucasus are three instances. These
blueprints reproduce a *kind of place*, not a specific DEM — for a named real map, match a
heightfield or feature primitives first (`13`, Génevaux et al. 2015), then use the archetype for
the *process* that fills between the constraints.

## The baseline — a generic eroded range

Every mountain archetype below is a **diff from this**, so the file is regimes, not a stack of
near-identical pipelines:

```
uplift field (02) → base + detail noise (01) → depression fill (03) → flow routing (03)
→ erosion backbone by extent (04, the SKILL.md table) → thermal to repose (05)
→ analysis (06) → masks → materials (06) → scatter (07) → export (08)
```

The non-mountain archetypes (waterfalls, deserts, karst, coasts, reefs, salt flats) don't diff
from a range — they **switch the dominant agent** (aeolian, dissolution, wave, deposition) while
the order and the invariants hold. Same machine, different weights. And the **off-Earth**
archetypes (Group L) change the *regime itself*: no liquid water switches the fluvial backbone
(`03`/`04`) **off** and lets impact cratering dominate, and gravity rescales craters and dunes —
the planetary doctrine in `SKILL.md`, built out.

---

## Group A — Orogens (mountain ranges)

### 1. Alpine-type — young collisional, heavily glaciated
*European Alps · Southern Alps (NZ) · Caucasus · Alaska Range*

**Claim.** Continental collision built a linear uplift; Quaternary glaciers then overprinted a
fluvial range, carving troughs, cirques and horns faster than rivers could; below the glacial
trimline, fluvial dissection and large range-front fans with moraine-dammed piedmont lakes.

**Diff from baseline.** Uplift = linear/arcuate ridge (`02`), moderate–high, near erosional
equilibrium (*mature*). **Glacial branch ON, alongside fluvial** (`12`, Legal Order 6b) — the
defining switch. Lithology contrast: crystalline core (steep high massifs) vs. carbonate cover
nappes → the Dolomites read as vertical cliffs + tower/cone karst (`11`). Climate: strong
orographic gradient and a glacial-era snowline that put ice above ~1–2 km (`13`).

**The tells.** U-shaped cross-profiles, not V; cirque-and-arête headwalls with horn peaks
(a Matterhorn is three-plus cirques biting into one summit); hanging tributaries → wall waterfalls
(entry 6); paternoster/ribbon lakes strung along the troughs; moraine-dammed lakes at the mountain
front (Como, Garda); big alluvial fans where a trough meets the plain; a sharp trimline —
frost-shatter above, forest below.

**Watch for.** Running glacial *instead of* or *after* fluvial — a glaciated range has **both**,
interleaved. V-valleys everywhere means you forgot the ice.

**Verify.** Cross-valley profiles read U in glaciated reaches; slope histogram bimodal (steep
glacial headwalls + gentle trough floors); lakes present and *unfilled* (`03` no-fill list);
hypsometric curve mature.

**Tier.** L — `02` uplift + `04` fluvial + **`12` glacial** + `11` Dolomite karst + `12`
moraine/fan deposition.

### 2. Himalayan-type — active, uplift-dominated, extreme relief
*Himalaya · Karakoram · (subduction cousin: the high Andes — same uplift-dominated regime, a
different plate boundary)*

**Claim.** The fastest-uplift collisional orogen; uplift ≫ erosion, so relief is extreme and
slopes sit at the *landslide threshold*; the monsoon slams one flank (orographic) and leaves an
arid rain-shadow plateau (Tibet) behind; glaciers only above ~5 km; antecedent trunk rivers saw
through the range as it rises (Kali Gandaki, Indus, Sutlej).

**Diff from Alpine-type.** Uplift much higher and **not** at equilibrium (*young*). Slopes are
pinned at the **threshold-hillslope angle** by pervasive mass wasting (`05`, SHALSTAB /
landslide-limited), so the slope histogram spikes at the *failure* angle, not gentle repose. A
strong **one-sided** orographic precip field (`13`) → deep fluvial incision on the wet flank,
near-zero on the dry plateau. Glacial ON but only in the highest band. Route `Q` for the
antecedent trunks (`03`/`04`).

**The tells.** Knife-edge ridges; several km of relief over short distance; landslide scars
everywhere; a monsoon-wet front and an arid high plateau behind; gorges deeper than the peaks are
tall.

**Watch for.** Using gentle-repose thermal to set slopes — in an uplift-dominated range **mass
wasting** sets slope, and it is steeper. And erasing the rain-shadow asymmetry (both flanks
eroding equally is wrong).

**Verify.** Slope histogram peaks at the steep threshold/failure angle, not repose; erosion
strongly asymmetric across the divide (wet flank incised, dry flank preserved); hypsometric curve
convex (youthful — little area removed yet).

**Tier.** L — `02` high uplift + `04` incision on routed `Q` + `05` landslide-limited hillslopes +
`13` orographic asymmetry + `12` high-altitude glacial.

### 3. Appalachian-type — old, decayed, drainage-inherited
*Appalachians · Scottish Highlands · Urals*

**Claim.** An ancient orogen whose uplift *ceased*; hundreds of Myr of erosion wore it to
subdued, rounded relief; the drainage is *inherited* — it predates the present topography and cuts
across structure (water gaps), because it was superimposed from a former cover.

**Diff from baseline.** **Uplift OFF** — or a slow, uniform epeirogenic rise — the single defining
switch. Maturity maxed: long fluvial plus hillslope diffusion (`05` creep, `D·∇²h`) run to a
low-relief, concave-hypsometry landscape. Lithology sets the *fabric*: differential erosion of
folded/tilted strata → long strike-parallel ridges (resistant sandstone) and valleys (weak shale),
the Valley-and-Ridge signature (`11`). No glacial (mostly), no active tectonics.

**The tells.** Rounded summits at *accordant* heights (an old erosion surface remnant); long
strike-parallel ridges; trellis drainage with **water gaps** where an old river held its course
through a rising ridge; deep soils and full forest; gentle slopes near diffusion equilibrium.

**Watch for.** Reaching for ridged noise to make "old mountains" — the parallel ridges are
*lithology + folding + differential erosion* (`11`), not noise. And giving it dramatic slopes: an
old range is *subdued*.

**Verify.** Hypsometric curve concave (most area is low — much mass removed); low relief, gentle
slope-histogram peak; ridges follow structural strike, not random azimuths; drainage crosses
ridges at gaps.

**Tier.** L — `02` uplift-off + `11` folded lithology/differential erosion + `04` inherited
drainage + `05` creep to low relief.

---

## Group B — Waterfalls
*Three **mechanisms**, not three postcards. A waterfall is a knickpoint (`04`, `00`) — there is no
"waterfall algorithm". Which mechanism pins the knickpoint is the whole question.*

### 4. Caprock plunge — Niagara-type
*Niagara · Iguazú · Kaieteur · Gullfoss*

**Claim.** A river crosses a resistant caprock lying on weak rock; the weak rock undercuts, the
caprock fails in slabs, and the falls **retreat upstream**, leaving a gorge as long as the fall is
old × its retreat rate. The waterfall is a knickpoint pinned to a *lithologic contact*.

**Composition.** Flow routing (`03`) → a hard caprock layer over soft in the `K` field (`11`) →
stream-power / knickpoint retreat (`04`, Whipple & Tucker 1999; Crosby & Whipple 2006) → a
recession gorge carved downstream of the lip. The plunge pool undercuts (sapping) → caprock slab
failure (`05` mass wasting) feeds the retreat. Whitewater itself is the engine's job (`03`
whitewater rule); the *terrain* owns the lip, the gorge and the pool.

**The tells.** A straight or gently-curved lip along the caprock outcrop; a narrow gorge of
near-constant width running downstream from the falls (the retreat trail); a plunge pool; slab
talus at the base.

**Watch for.** Painting a waterfall as a texture on a random cliff — it must sit on a `K`-contrast
and *own a gorge downstream*, or it reads as fake.

**Verify.** Gorge length ≈ retreat-rate × age (a closed check); the knickpoint sits exactly on the
`K`-contact; flow accumulation is continuous through it (the river doesn't "stop" at the falls).

**Tier.** L — `04` knickpoint (P) + `11` lithology + `05` undercut failure.

### 5. Fault/joint-controlled — Victoria Falls-type
*Victoria Falls / Mosi-oa-Tunya*

**Claim.** Instead of retreating across a bedding contact, the river drops into a **tectonic
fissure** — a fault or master-joint set cutting a flat basalt sheet — then escapes through a narrow
slot; the falls retreat by *jumping to the next parallel joint*, leaving a **zigzag gorge** that
traces the joint pattern.

**Diff from Niagara-type.** The control is **structural** — a joint/fault set in a near-flat
flood-basalt sheet (`11` lithology + `02` fissure/flood basalt) — **not** a horizontal caprock.
Knickpoint retreat (`04`) is *guided by the joint network*, so the plan-view record is a series of
former fall-lines (a zigzag of abandoned gorges), not a single straight retreat trail.

**The tells.** A wide flat lava plateau; a full-width curtain falling into a slot *perpendicular*
to the river; a zigzag gorge below with sharp right-angle bends at each captured joint; successive
abandoned fall-lines stepping upstream.

**Watch for.** Modelling it as Niagara — the signature is the *zigzag*, which only appears if a
joint/fault set drives the retreat. No structural fabric → the wrong gorge.

**Verify.** Gorge planform zigzags along the joint azimuths; the lip spans the full channel width
on flat ground; each gorge segment is a former fall-line.

**Tier.** L — `04` knickpoint retreat gated by `11` structural jointing in `02` flood basalt.

### 6. Hanging-valley — Yosemite-type
*Yosemite Falls · Lauterbrunnen · the wall falls of Milford Sound*

**Claim.** A large glacier deepened the main trough faster than its small tributaries could keep
up; when the ice left, the tributaries were stranded **hanging** high on the trough wall, and their
streams leap off the lip as free-falling ribbons.

**Composition.** A *product of entry 1's glacial pass* (`12`): the main trough is over-deepened
(SIA ice discharge scales with catchment), tributaries under-deepened, leaving a step at each
confluence. The waterfall is that step — free-leaping, not gorge-cutting, because the wall is
near-vertical glaciated bedrock (too young for a recession gorge).

**The tells.** Falls emerging from a valley *mouth* partway up a sheer U-wall, not from a notch in
a ridge; multiple parallel hanging falls along one trough (Lauterbrunnen); no gorge below.

**Watch for.** Putting a hanging-valley fall in an *unglaciated* range — it requires the
trough/tributary depth mismatch that only ice makes. (The Angel Falls "leap off a wall" look is a
different maker — an escarpment rim, entry 8.)

**Verify.** The falls sit at a tributary–trunk confluence on a U-wall; trough profile U, tributary
floor perched; no downstream recession gorge.

**Tier.** L — `12` glacial over-deepening + differential trough/tributary incision (entry 1).

---

## Group C — Canyons & tablelands

### 7. Plateau canyon — Grand Canyon-type
*Grand Canyon · Zion · Canyonlands / Monument Valley · Blyde River*

**Claim.** A thick pile of near-horizontal, alternating hard/soft strata is uplifted as a broad
**plateau** (not a peaked range) and a through-flowing river incises it faster than the walls
retreat; differential erosion of the layers makes the stepped walls, mesas, buttes and spires.

**Composition.** Broad epeirogenic uplift (`02`, plateau not ridge) → a strong horizontally-layered
`K` field (`11` strata) → an antecedent trunk river with high stream power incises a deep slot
(`04`) → cliff-and-bench walls (hard layers stand as cliffs, soft as slopes — `11` differential
erosion) → detached remnants: mesas (broad caprock) → buttes (narrow) → spires. Arid climate keeps
walls bare and sharp (little soil/creep to round them).

**The tells.** A flat skyline (the intact plateau top) cut by a deep canyon; horizontally-banded,
stepped walls; the mesa→butte→spire size sequence of erosional outliers standing at the plateau
level; dendritic side-canyons; slot canyons (Antelope) where flash floods incise resistant
sandstone along joints.

**Watch for.** A V-notch in a *peaked* range is not this — the flat interfluves (the plateau) are
essential, and the walls must be *stepped by lithology*, not a smooth V.

**Verify.** Interfluves flat and accordant (the plateau top); wall profile a staircase keyed to the
`K`-layers; outliers sit at plateau elevation.

**Tier.** L — `02` plateau uplift + `11` horizontal strata / differential erosion + `04` incision.
True overhangs (arches) need `11`'s non-heightfield representation.

### 8. Tepui table-mountain — Roraima-type
*Mount Roraima & the Gran Sabana · Auyán-tepui (Angel Falls)*

**Claim.** An ancient, extremely resistant flat cap (quartzite) over weaker rock protects a high
tableland while the surroundings are stripped away, leaving **island-mountains with sheer ~1 km
walls**; rivers on top plunge straight off the rim (Angel Falls, the tallest, is a free leap off
Auyán-tepui).

**Diff from Grand Canyon-type.** The resistant layer is a **single very hard cap**, and erosion
works *inward from the edges* (**scarp retreat / escarpment backwearing**) rather than a river
slotting *down* — so you get isolated flat-topped massifs separated by lowland, not a canyon in a
continuous plateau. Very old, very low erodibility cap (`11`); humid climate etches the top into
ruiniform (karst-like) blocks.

**The tells.** Perfectly flat summits at *accordant* height (a former continuous surface); vertical
cliff walls; isolated massifs rising abruptly from lowland forest; rim waterfalls leaping clear
with no gorge (the wall is steeper/younger than any gorge); ruiniform sandstone on top.

**Watch for.** Rounding the walls — the defining feature is the *sheer* edge from cap resistance.
And confusing it with a mesa: a tepui is far larger and older, a remnant *plateau*, not a canyon
outlier.

**Verify.** Summits accordant and flat; walls near-vertical; massifs isolated by scarp-retreat
lowland; rim waterfalls free-leaping.

**Tier.** L — `11` hyper-resistant cap + escarpment retreat / differential erosion + `04` rim
knickpoint.

---

## Group D — Deserts

### 9. Erg / sand sea — Namib & Sahara-type
*Namib / Sossusvlei · Rub' al Khali · Grand Erg Oriental · Taklamakan*

**Claim.** An aeolian depositional system where sand supply, wind and (absent) vegetation build a
*sea of dunes* whose shapes encode the wind regime — barchans in unidirectional low-supply winds,
transverse ridges at high supply, linear/seif dunes in bimodal winds, star dunes where winds come
from all sides (Sossusvlei's giants).

**Composition.** **Aeolian branch dominant** (`05`, Werner 1995 slab CA) on a sand-supply field;
the wind field (`13`) sets dune type; dunes migrate downwind; interdune flats/playas where sand is
thin. The underlying bedrock/fluvial relief is subdued and mostly buried. Off-Earth: same Werner
CA, gravity/air-density-shifted (Kok et al. 2012).

**The tells.** Dune *type* matches the wind rose (unidirectional → barchan; bidirectional → linear;
multidirectional → fixed star dune, tallest); slip faces at the sand repose angle (~33°, range
30–35° — `05`'s numbers); wet interdune pans where the water table nears the surface (Sossusvlei's
dead vlei).

**Watch for.** Stamping dune *shapes* as noise — dunes are a *process*, and their type is
*diagnostic of the wind*. A field of random bumps is the classic tell. A slip face steeper than
repose is impossible.

**Verify.** Slip faces at the repose angle; dune type/spacing consistent with one wind regime
across the field; crest orientation obeys the wind rose; sand conserved — deflation source ↔ dune
sink (`09` mass check).

**Tier.** L — `05` Werner dunes (P) + `13` wind field + `16` sand sheets. Off-Earth: Kok et al.
2012.

### 10. Basin-and-Range playa — Death Valley-type
*Death Valley · Atacama basins · the Basin & Range province · Danakil*

**Claim.** Crustal *extension* pulls the surface into tilted fault blocks — parallel mountain
**horsts** and down-dropped **graben** basins; the ranges erode, their debris builds coalescing
**alluvial fans (bajada)** into closed basins with no outlet, and each basin floor is a
**playa / salt flat** where episodic water evaporates.

**Diff from a collisional range.** Uplift is **extensional horst-and-graben** (`02` fault blocks),
not a collisional dome; drainage is **endorheic** — the no-fill list keeps the basins closed
(`03`); deposition is fan-dominated (`16`, Blair & McPherson 1994) plus evaporites (`16` playa,
entry 22). Arid climate → bare sharp fans and a salt playa.

**The tells.** A repeating range–basin–range corrugation; triangular fan facets debouching from
every range-front canyon and merging into a bajada; a flat white salt playa at each basin's low
point; the whole scene *closed* — no river leaves.

**Watch for.** Letting the basins drain to the sea — they must be endorheic (closed sinks kept
unfilled, `03`), or the fans and playa never form. Fans need the *slope break* at the range front,
not random cones.

**Verify.** Basins closed (flow accumulation terminates in the playa, not the edge); fans at
range-front slope breaks, coalescing; evaporite material on the flats; block-faulted linear ranges.

**Tier.** L — `02` extensional faulting + `16` alluvial fans/bajada + `16` playa + `03` endorheic
no-fill.

### 11. Hoodoo / badlands — Bryce & Cappadocia-type
*Bryce Canyon · Cappadocia / Göreme · Badlands (SD)*

**Claim.** Rapid differential erosion of weak, flat-lying, poorly-consolidated layered rock:
capped columns (**hoodoos / fairy chimneys**) survive where a hard cap shields a soft column;
densely dissected **badlands** rills form where there is no cap and no vegetation.

**Composition.** Soft layered lithology (`11`) + a sparse hard-cap distribution → frost-wedging /
rain-splash / rilling (`05` thermal + `04` fine-scale fluvial) at high rate → capped columns where
a caprock clast shields, knife-edge rills and pinnacles where not. **True hoodoos need a
non-heightfield representation** — a column thinner than its hat overhangs (`11` Peytavie material
stack, `00`). Cappadocia variant: an ignimbrite/tuff column capped by a hard basalt boulder (`19`)
— same geometry, volcanic parent.

**The tells.** Forests of capped spires each wearing a visible harder hat; fluted, densely-rilled
slopes with almost no vegetation and *very high drainage density*; colour banding from the strata;
an amphitheatre form where a scarp is eaten headward (Bryce).

**Watch for.** Doing this on a *heightfield only* — a real hoodoo overhangs under its cap, which a
single-value height can't express (`11`). Heightfield gives pinnacles, not true hoodoos.

**Verify.** Each spire shows cap-controlled survival; drainage density extreme on uncapped slopes;
overhangs present only if a volume / material-stack representation is used.

**Tier.** L — `11` soft strata + hard cap (non-heightfield for overhangs) + `05`/`04` rapid
dissection. Cappadocia: + `19` tuff/ignimbrite.

### 12. Desert oasis — Saharan-type
*Siwa · Bahariya, Kharga & the Egyptian depressions · Qattara · (type: any deflation, fault-line or
artesian oasis)*

**Claim.** A green, watered hollow in a hyper-arid desert — not a rainfall feature but a
**groundwater** one. Wind deflates a closed basin *down to the water table* (damp sand resists, so
the table is the floor wind cannot cut below); where the table meets the surface there are springs,
a salt lake / **sabkha** at the sump, and a palm grove ringing the fresh margin — all fed by
**fossil groundwater** from a regional aquifer, under a bare plateau.

**Diff from the erg (entry 9) and the fault-block playa (entry 10).** The basin is cut by
**aeolian deflation** (`05`/`16`), not faulting — and its depth is **base-levelled by the water
table**: deflation stops where the ground is damp. The deflated sand piles **downwind as dunes**
(entry 9's Werner machinery, `05` — the mass the basin lost). The floor is an **endorheic** sink
(`03` no-fill), so evaporation concentrates an evaporite **sabkha** at the low point (`16` playa /
`18` crust, cf. entry 22). The **water table intersecting the surface** drives everything: springs,
and a **palm grove** as an ecosystem *gated by water-table depth and salinity* (`13`/`07`), not
painted. A bounding **escarpment** drops from a caprock plateau (`11`); the hamada above is bare,
with desert pavement and yardangs (`16`).

**The tells.** A closed depression floored at a *flat* water-table datum, below a plateau
escarpment; concentric zoning at the sump — open brine, salt crust, then a green fringe where the
table is shallow but fresh; deflation dunes banked downwind; a bare pavement/yardang plateau around
it. The water is the whole story — there may be no local rain at all.

**Watch for.** Modelling an oasis as a *rainfall/fluvial* feature — it is **groundwater-fed**, and
the water table does double duty: the *base level of deflation* (why the basin stopped sinking) and
the *source of the springs*. And the basin must be **closed** (`03`), or the salt never accumulates
and it is not a sabkha.

**Verify.** Basin closed (deflation/flow terminates at the sump, nothing drains out); floor sits at
a flat water-table level (deflation base-levelled, not a random pit); salinity and vegetation zoned
concentrically by table depth; deflated volume ≈ downwind dune volume (`09` mass check); surrounding
plateau bare (pavement, yardangs).

**Tier.** L — `05`/`16` deflation to the water table + `03` endorheic basin + `16` sabkha / `18`
crust + `13` groundwater-gated ecosystem + `11` bounding escarpment.

---

## Group E — Karst

### 13. Entrenched-meander karst gorge — Ardèche-type
*Gorges de l'Ardèche & the Pont d'Arc · Verdon · the goosenecks of the San Juan (canyon cousin)*

**Claim.** A river's meanders, inherited from a former low-relief surface, are **entrenched** deep
into a limestone plateau by uplift and bedrock incision — keeping the snaking planform while cutting
a sheer gorge; where an incising meander breaches its own neck it abandons a loop and leaves a
**natural arch** (the Pont d'Arc); the plateau is **karst** — caves, sinks, resurgent springs and
almost no surface drainage.

**Composition.**
- **Inherited meanders** — establish the sinuous planform on a low-gradient surface (`03`
  meandering, Ikeda et al. / Howard & Knutson). This is the *fossil* pattern the gorge will keep.
- **Uplift + bedrock incision** — `02` uplift (or a base-level fall) drives vertical **bedrock
  incision** (`04`, Sklar & Dietrich / stream power) *down* faster than the loops migrate sideways →
  **entrenched meanders**: a deep, sheer gorge that still goosenecks. (The `00` L-row "entrenched /
  incised meanders → in karst → the Ardèche", built out.)
- **Karst lithology** (`11`) — soluble limestone stands in vertical walls and dissolves: caves (a
  **volume**, `11` Paris et al. 2021), sinkholes, blind valleys, and **spring resurgences** in the
  walls; the *causse* plateau above carries little surface flow — its drainage is underground.
- **Neck cutoff through rock → natural arch** — where two loops nearly meet, the incising river cuts
  through the narrow rock neck; the through-cut leaves a **natural bridge** (Pont d'Arc) and the
  bypassed loop becomes an **abandoned dry meander**. The arch needs the **non-heightfield
  representation** (`11`) — a heightfield cannot hold a span with a void beneath it.

**The tells.** A gorge that *meanders* in tight goosenecks — the tell that it is inherited and
entrenched, not a straight fault/joint slot; near-vertical limestone walls; a natural arch at a
breached neck with an abandoned dry loop beside it; caves and springs in the walls; a dry karst
plateau above (sinks, no rivers).

**Watch for.** Making the meanders with a *floodplain* process — floodplain meandering (Legal Order
9c) is lateral migration on soft sediment; **entrenched** meanders are a fossil planform incised
*vertically into bedrock*, so the walls are rock, not cutbanks. And the Pont d'Arc is a **rock**
neck cutoff (`11` non-heightfield arch), not an oxbow (entry 21's floodplain lake) — the same cutoff
idea, through stone, leaving a bridge instead of a lake.

**Verify.** Gorge planform sinuous (inherited meanders), not straight; walls vertical in the
limestone; a breached neck shows an arch + an adjacent abandoned dry loop; the plateau shows karst
drainage (sinks/springs) and low surface flow accumulation; caves only if a volume representation is
used.

**Tier.** L — `03` inherited meanders + `02` uplift + `04` bedrock incision + `11` karst/limestone
(caves = volume) + `11` natural arch (non-heightfield). The `00` "entrenched meanders → Ardèche /
Pont d'Arc" row, built.

### 14. Tower karst — Guilin & Ha Long Bay-type
*Guilin / Li River (fenglin) · Ha Long Bay · Phang Nga · Guizhou (fengcong)*

**Claim.** Thick, pure limestone in a warm wet climate dissolves along joints; vertical corrosion
lowers the plain while residual **towers** (fenglin) or cone-clusters (fengcong) stand up; where
the sea floods a tower field you get the drowned version — a bay full of steep limestone islets
(Ha Long, Phang Nga).

**Composition.** A soluble-lithology-gated dissolution: fluvial/dissolution erosion *selective on a
carbonate `K` field* (`11` karst); vertical lowering to a base level (water table / floodplain)
leaves steep-sided residual towers (`00` tower/cone karst). Caves and underground drainage need a
**volume** representation (`11`, Paris et al. 2021). Drowned variant = tower karst + sea-level rise
(a karst ria, `12`).

**The tells.** Isolated steep-walled towers (fenglin) rising from a *flat* alluvial plain, or a
dissected upland of cones (fengcong); a plain at a common base level between towers; sinkholes,
blind valleys, springs, disappearing rivers; sea-flooded → steep limestone islets in a bay.

**Watch for.** Making towers by noise or by eroding *insoluble* rock — the mechanism is
*dissolution of a soluble layer to a base level*, and the flat inter-tower plain at a common level
is the tell. Caves are volumetric (`11`), not a heightfield dimple.

**Verify.** Towers share a common basal plain/level; steep walls, flat between; drainage partly
subsurface (springs/sinks); the drowned variant is the same geometry below sea level.

**Tier.** L — `11` karst dissolution on soluble lithology + base-level lowering; `11` caves
(volume, Paris et al. 2021); `12` sea-level for Ha Long Bay.

---

## Group F — Volcanic

### 15. Stratovolcano — Fuji & Kilimanjaro-type
*Mt Fuji · Kilimanjaro · Rainier · Mayon · Cotopaxi*

**Claim.** Repeated eruptions build a steep **conical edifice** of interlayered lava and ash;
radial drainage cuts it from the summit down; large ones grow their own ice cap and short glacial
valleys, and can fail catastrophically (sector collapse → lahars).

**Composition.** An edifice primitive with the height/width/slope of its *type* (`11`, Pike & Clow
1981) → radial drainage from the summit (`03`) → gullies/barrancas (`04`) → optional summit glacier
(`12`) where it pierces the snowline → lahars / sector collapse as mass wasting (`05`). Lava flows
and fields on the flanks per `19`.

**The tells.** A near-symmetric cone with a concave-up profile; a radial gully (barranca) pattern
from a summit crater; a small summit crater or caldera; a snow/ice cap and short glacial troughs on
high ones — an *equatorial* glacier on Kilimanjaro is a striking regime note; an apron of lahars
and fans at the base.

**Watch for.** A cone that is just a Gaussian bump — it needs *radial incision* and the edifice
slope of its type (a shield is broad and gentle, a cinder cone small and steep, a stratovolcano
intermediate — pick from Pike & Clow). Lava belongs on the flanks (`19`), not implied by shape
alone.

**Verify.** Radial drainage from the summit; edifice dimensions match the volcano type; crater/
caldera at top; glacial only above the snowline.

**Tier.** L — `11` edifice (Pike & Clow, P) + `03` radial drainage + `04` barrancas + `12` summit
ice + `19` lava + `05` lahars.

### 16. Caldera lake — Crater Lake & Santorini-type
*Crater Lake · Santorini · Ngorongoro · Toba*

**Claim.** A large eruption empties the magma chamber and the roof **collapses** into a broad
circular basin (a caldera, far larger than a vent crater); it fills with water (Crater Lake) or
floods from the sea (Santorini), often with a **post-collapse vent cone** as an island in the
middle (Wizard Island, Nea Kameni). (*Resurgence* proper — structural re-uplift of the caldera
floor — is a distinct feature of the largest calderas; don't use the word for a cone.)

**Composition.** Build the pre-collapse edifice (`11`, entry 15) → subtract a **collapse caldera**
(a broad, steep-walled circular depression, `11`) → fill: a closed lake kept unfilled by the
no-fill list at a set level (`03`), or breach to sea level (Santorini) → optional post-collapse
vent cone (a small edifice) on the floor → wave-cut shore on the caldera walls (`12` lacustrine).

**The tells.** A large circular basin with steep inner walls, far wider than any summit crater; a
flat water surface inside; sometimes a central island; exposed caldera-wall stratigraphy; if
marine, a flooded ring with a gap (Santorini's lagoon).

**Watch for.** Confusing a *collapse caldera* (broad, collapse-formed) with a *summit crater*
(small, vent/explosion) — scale and origin differ. The lake must be a *closed basin held at a
level* (`03`), not a fluvial pond.

**Verify.** Basin diameter ≫ a crater's, walls steep and near-circular; water level flat and
closed; any post-collapse cone sits on the caldera floor.

**Tier.** L — `11` edifice + collapse caldera + `03` closed lake/level + `12` shore + optional
post-collapse vent.

### 17. Columnar basalt & rift volcanism — Giant's Causeway & Iceland-type
*Giant's Causeway / Antrim · Iceland · Deccan / Columbia River basalts*

**Claim.** Fluid basalt erupts from **fissures** (not a cone) as vast flat sheets (flood basalt,
"traps"); as a thick flow cools it contracts into **polygonal columns**; stacked flows plus later
dissection give stepped **trap** topography; on a spreading rift (Iceland) fissures, grabens and
sub-glacial eruptions combine.

**Composition.** Line-source / fissure flows along a rift or fault (`02`) → stacked levéed sheets
(`11`/`19`) → *columnar jointing* as a **material/mesh detail** (like hoodoos, the columns are
sub-cell geometry, not a heightfield feature; and jointing is a *cooling* phenomenon, not a basalt
exclusive — Devils Tower is a columnar-jointed phonolite *intrusion*, no flood basalt in sight) → dissection of the stack → stepped traps (`11`).
Iceland adds an active rift graben (`02`), sub-glacial eruptions → flat-topped **tuyas**, and
braided outwash sandur (`03`).

**The tells.** Flat-topped stepped plateaus (traps) with columnar cliffs; polygonal column tops
(the Causeway); a rift valley with fissure rows and grabens (Þingvellir); flat-topped tuyas; black
sand and braided outwash.

**Watch for.** Expecting a *volcano shape* — flood basalt has **no edifice**; it is sheets from a
line source. The columns are a jointing texture, not something a heightfield resolves.

**Verify.** Topography stepped/tabular (stacked sheets), not conical; fissure/graben lineaments
present; columns only in a material/mesh layer; tuyas flat-topped where ice-confined.

**Tier.** L — `02` fissure/rift + `11`/`19` flood-basalt sheets + columnar jointing (material) +
`03` outwash; Iceland + `12` glaciovolcanic.

---

## Group G — Glacial & polar coasts

### 18. Fjordland — Norwegian & Fiordland-type
*Norway · Milford Sound / Fiordland (NZ) · Patagonia · Greenland · SE Alaska*

**Claim.** Glaciers over-deepened valleys **below** sea level; when the ice left and the sea rose,
it flooded the troughs into long, deep, steep-walled **fjords**, often with a shallow **sill**
(terminal moraine / reduced erosion) at the mouth and hanging-valley falls down the walls.

**Composition.** A glaciated range (entry 1, `12`) with troughs incised below the eustatic low →
sea-level rise floods them (`12`, glacial analogue of a ria) → a sill at the mouth (moraine, or
where the ice thinned and eroded less) → hanging tributaries → wall waterfalls (entry 6); a
wave-planed **strandflat** and skerries fringing old-shield coasts (Norway).

**The tells.** Long, narrow, deep, straight-ish arms with near-vertical walls following glacial
troughs; a shallow sill at the seaward end — *deeper inside than at the mouth*, the fjord
bathymetry tell; hanging waterfalls on the walls; a fretted island-fringed coast.

**Watch for.** Treating a fjord like a *ria* — a drowned *river* valley is V-shaped, dendritic and
*deepest at the mouth*. A fjord is glacial: U-walled, deepest *inside*, with a sill. That inverted
depth profile is the discriminator.

**Verify.** Cross-section U not V; long-profile deepest in the middle with a sill at the mouth;
walls carry hanging falls; planform follows glacial troughs, not a dendritic river net.

**Tier.** L — `12` glacial over-deepening + sea-level rise + sill (moraine) + `06`/`12` strandflat.

---

## Group H — Coastal & marine

### 19. Sea cliffs & stacks — Twelve Apostles & Cliffs of Moher-type
*Twelve Apostles (Vic) · Cliffs of Moher · Étretat · Old Man of Hoy · Durdle Door & the Jurassic
Coast*

**Claim.** Waves attack a rocky coast; a **wave-cut notch** undercuts the cliff, it retreats
leaving a **wave-cut platform** at its foot, and differential hardness/joints leave the sequence
headland → arch → **stack** → stump as erosional remnants.

**Composition.** Sea level exists (`03`) → a wave-erosion band at the waterline biting into a cliff
of varying hardness/jointing (`12`) → cliff retreat + platform → the arch→stack→stump progression
from a headland; longshore drift carries the debris to build beaches/spits downdrift (`12`). Mostly
*a look, not a full sim* (`12`), but the **mass budget closes**: the retreating cliff *is* the
downdrift beach.

**The tells.** A line of stacks standing off a retreating cliff on a common **platform**; arches
mid-transition; the platform bared at low tide; pocket beaches of the cliff's own debris downdrift;
jointing/hardness controlling where stacks survive.

**Watch for.** Stacks floating without a *platform* or a *retreating cliff line behind them* —
they are remnants of the former cliff and must sit on the planed platform. The eroded rock must go
*somewhere* (downdrift — `09` mass check).

**Verify.** Stacks aligned on the old cliff line, on a common platform level; arch→stack→stump
forms present; debris appears as downdrift deposition (mass closed).

**Tier.** L — `12` wave erosion / cliff retreat + hardness variation + `12` longshore deposition.

### 20. Coral reef & atoll — Great Barrier Reef & Maldives-type
*Great Barrier Reef · Maldives · Bora Bora · Bikini*

**Claim.** Reef-building coral grows up toward the light in warm shallow seas; **Darwin's
subsidence sequence** — a fringing reef on a young volcanic island → a barrier reef as the island
subsides → an **atoll** (a ring of reef around a lagoon) once the island sinks away entirely.

**Composition.** A volcanic edifice (`11`) that **subsides** through time (`02`) while **coral
accretes in the photic zone** and is shaped by **wave exposure** (`12` reefs & atolls, Darwin) →
fringing → barrier → atoll depending on how far subsidence has gone → a shallow lagoon (closed
basin) inside the ring, with passes where fresh water / wave energy break it. Bora Bora is the
textbook Darwin mid-stage (barrier ring, shrinking volcanic core); Maldives/Bikini the atoll
end-state. The Great Barrier Reef is the *shelf* variant — same photic-zone accretion on a
subsiding surface, but the surface is a continental margin, not a volcano, so it has the barrier
geometry without the Darwin cone-to-atoll sequence.

**The tells.** A ring or line of reef with a steep seaward drop and a shallow flat lagoon inside;
sand cays (motu) on the rim; the reef *keeps pace with sea level*; a central island only at the
fringing/barrier stage, gone at atoll stage.

**Watch for.** An atoll as a "ring-island algorithm" (`00` warns there is none) — it is *edifice +
subsidence + photic-zone accretion + wave exposure*. The ring is where coral kept up as the cone
sank.

**Verify.** The reef sits in the photic-depth band; the ring encloses a shallow lagoon with a steep
outer slope; the stage (fringing/barrier/atoll) matches the subsidence amount; passes where waves /
fresh water inhibit coral.

**Tier.** L — `11` edifice + `02` subsidence + `12` coral accretion / wave exposure (Darwin).

---

## Group I — Rivers & depositional wonders

### 21. Inland delta & meander wetland — Okavango & Amazon-type
*Okavango Delta · Amazon floodplain · Pantanal · lower Mississippi*

**Claim.** A large river on a very low gradient either spreads into a closed basin and evaporates
(an **inland delta** — Okavango, a delta that never reaches the sea) or wanders a broad floodplain,
leaving **meander scrolls, oxbow lakes and levees** (Amazon, Mississippi).

**Composition.** A low-slope reach (`03`) → meandering + bank erosion + neck cutoff → oxbows and
scroll bars (`03`, Ikeda et al. 1981 / Howard & Knutson 1984) → overbank deposition builds natural
levees and floodbasins. The Okavango variant routes the river into an **endorheic** graben (`02`/
`03` closed), where it splays into distributaries and evaporates in a wetland (`13` wetlands: high
TWI + flat + a thin dynamic water layer). Deposition-dominant — the river's *load* dropped on the
floodplain.

**The Amazon variant — the flood pulse is the landscape-builder.** On a basin this flat (the lower
river falls only a few cm per km) the organizing agent is not the channel but the **seasonal water
surface**. The annual **flood pulse** raises river level by ~10 m and inundates a forest belt tens
of km wide, then drains it — and that pulse, not relief, partitions the land into **terra firme**
(never flooded, upland), **várzea** (seasonally flooded by sediment-rich *whitewater*), and **igapó**
(flooded by *blackwater*). The three are an **ecosystem mosaic keyed to inundation depth and
duration** (`13`, `07`), not to height. Model it as a **thin dynamic water layer with a seasonal
level** (`08`) over near-zero relief, and read the biome bands off flood depth/duration exactly as
`13`'s wetlands read off TWI — here the flood pulse supplies the water regime the ecosystem sorts on.
This is why "the Amazon" is two problems: the *channel* geomorphology above (meanders, oxbows), and
this *floodbasin* mosaic, which is mostly a water-surface and ecosystem story.

**The tells.** Tight meanders with oxbow lakes and scroll-bar ridges on a flat floodplain; natural
levees standing above backswamps; for Okavango, a fan of distributary channels dissolving into
reed-and-water wetland with *no outlet to the sea*; braided reaches where slope or sediment rises;
for the Amazon, a flooded-forest belt that expands and contracts by tens of km each year — the
biome bands (terra firme / várzea / igapó) follow inundation, not contours.

**Watch for.** Meanders on a *steep* slope — meandering is a *low-gradient floodplain* process
(Legal Order 9c, after the valley is cut). The wetland needs the *closed/flat + thin water layer*
(water as a dynamic layer, `08`), not a carved lakebed.

**Verify.** Sinuosity high on the low-slope reach; oxbows/scrolls present; the Okavango basin closed
(endorheic — flow terminates in the wetland); water modelled as a thin dynamic layer over near-flat
ground; for the Amazon, the biome mosaic tracks a *seasonal water level* (dynamic layer, `08`), not
fixed height — the terra firme / várzea / igapó bands shift with the pulse.

**Tier.** L — `03` meandering/oxbows + overbank deposition + `02`/`03` endorheic basin (Okavango) +
`13` wetland.

### 22. Salt flat & mineral terraces — Uyuni & Pamukkale-type
*Salar de Uyuni · Bonneville salt flats · Danakil · Pamukkale / Huanglong travertine*

**Claim.** Two "chemical" beauties. An **evaporite playa** (Uyuni, Bonneville) — a closed basin
where a former lake evaporated to a mirror-flat salt crust. And **travertine terraces** (Pamukkale,
Huanglong, Mammoth) — mineral-saturated spring water deposits carbonate as it flows, building
rimstone dams of stepped pools.

**Composition.** *Playa* — an endorheic basin (`03` no-fill) + evaporite material (`16` playa, `18`
crust); optional former-lake **shorelines/terraces** ringing the basin (`12` lacustrine, Gilbert
1890 / Lake Bonneville). *Travertine* — a **depositional** process: spring discharge (`03` source)
supersaturated in carbonate precipitates at flow lips and self-builds rimstone pools — a deposition
CA gated by flow + chemistry, closest in spirit to lava's self-levéeing (`19`) but chemical, and a
genuinely different *building* agent from the erosion-dominated rest of this list.

**The tells.** Playa — a dead-flat, bright, cracked salt-polygon surface, closed, with horizontal
fossil shorelines on the surrounding slopes. Travertine — stacked scalloped rimstone dams of
turquoise pools cascading down a slope in brilliant white/coloured mineral.

**Watch for.** A salt flat that isn't *flat and closed* — it is the floor of an evaporated closed
lake (endorheic, `03`). Travertine terraces are *depositional* — built up by precipitation at flow
rims — not eroded; model them as deposition or they look carved and wrong.

**Verify.** Playa surface flat to millimetres and closed; fossil shorelines horizontal (a level
record); travertine rims follow flow contours and *build outward and up* (mass added, not removed).

**Tier.** L — `03` endorheic + `16` evaporite / `18` crust + `12` lacustrine shorelines (playa);
deposition CA + `03` source (travertine).

---

## Group J — Geothermal & stone forests

### 23. Geothermal field — Yellowstone-type
*Yellowstone · Rotorua–Taupō (NZ) · Iceland's Geysir & hverir · El Tatio (Chile)*

**Claim.** Shallow magmatic heat drives groundwater convection inside a volcanic system: geysers,
hot springs, mud pots and fumaroles cluster along fractures; silica-saturated water builds
**sinter** aprons and cones around alkaline springs; the vivid colours are **microbial mats zoned
by temperature** (Grand Prismatic's rings); and at Yellowstone the whole field sits inside a
supervolcano caldera whose floor carries **true resurgent domes** — the structural re-uplift that
entry 16 warns is *not* what a post-collapse cone is.

**Composition.** A caldera substrate (entry 16 at supervolcano scale, `11`) → hydrothermal
features placed along **fracture/fault gates** (`02` faults + `11` — springs are where the
plumbing reaches the surface, not a random scatter) → **deposition, not erosion**, builds the
landforms: sinter (silica) aprons, terraces and geyser cones by the same self-building rimstone
logic as entry 22's travertine — and where the bedrock is carbonate (Mammoth), it *is* entry 22's
travertine, stacked into terraced pools. Mud pots where acid alteration turns rock to clay
(`18` material change); **hydrothermal explosion craters** as occasional small `11` craters.
Colour is a **material story** (`06`/`08`): a temperature field around each vent drives an
albedo ramp — blue (hot, sterile) → yellow → orange → brown (cooler mats) — the biological
sibling of `08`'s blackbody ramp. Runoff channels braid across the sinter aprons (`03` at
micro-scale).

**The tells.** Features strung along lines (the fracture gates), not sprinkled; gently-sloped
white sinter aprons with scalloped terracelets; concentric colour rings around hot pools, hue
keyed to water temperature; steaming ground and bleached, altered rock; dead bleached trees at
apron edges (silica kills the roots — the scatter layer tells the story too); a caldera rim on
the skyline.

**Watch for.** Scattering geysers randomly — hydrothermal features are *plumbing outlets* and
line up along faults; and carving the terraces — sinter and travertine are **depositional**
(entry 22's rule): they build up and outward, and an eroded-looking terrace reads wrong. Active
eruption columns and steam are the engine's job (`03`'s whitewater rule); the terrain owns the
cones, aprons, pools and palette.

**Verify.** Feature positions correlate with the fracture/fault mask; sinter aprons slope gently
away from vents (deposition profile); colour rings concentric and monotone in temperature; the
`09` mass check reads *accretion* near vents (mass added over time, sourced from solution, like
entry 22).

**Tier.** L — entry 16 caldera + `02`/`11` fracture gating + entry 22's deposition CA (silica /
carbonate) + `06`/`08` temperature-driven material palette. The hydrothermal system itself is
geology (Old Faithful's plumbing), not a graphics algorithm — model its *surface products*.

### 24. Sandstone pillar forest — Zhangjiajie-type
*Zhangjiajie / Wulingyuan (the "Avatar mountains") · Meteora (conglomerate cousin)*

**Claim.** A thick, flat-lying, well-cemented **quartz sandstone** plateau cut by two near-
orthogonal vertical **joint sets** is dissected along the joints — streams, frost and rockfall
eat the joint corridors into deep slots and leave a *forest of freestanding rectangular pillars*,
hundreds of metres tall, their flat tops accordant with the old plateau surface and crowned with
pines. **Not karst**: quartz sandstone doesn't dissolve — this is mechanical, joint-controlled
erosion, which is why it earns an entry beside tower karst rather than inside it.

**Composition.** `11` strata — one thick resistant sandstone bed over a weaker base → an
**orthogonal joint fabric** (`02` jointing, two azimuth sets ~90° apart) as the process mask →
fluvial + frost erosion **gated to the joint corridors** (`04` + `05`, the process-mask pattern
from `SKILL.md`) widens the corridors downward → basal sapping in the weak underlayer + rockfall
(`05` mass wasting) keeps walls vertical and fells whole pillars (fresh scars, talus aprons) →
pillar tops keep soil and trees (`07`/`13` — the perched-ecosystem look). Meteora is the same
geometry from massive conglomerate, carved by a river system rather than a joint grid.

**The tells.** Pillar cross-sections quadrangular and *aligned* — plan-view edges follow the two
joint azimuths; tops accordant (one former surface); walls sheer with horizontal bedding visible;
slot corridors between pillars, floored with talus; trees on top of bare-walled pillars; fog
between pillars is the postcard, but the geometry is the tell.

**Watch for.** Building it as tower karst (14) — fenglin towers rise *rounded* from a dissolved
plain at base level; Zhangjiajie pillars are *rectangular*, joint-aligned, and stand in deep
dendritic ravines with no common basal plain. And random pillar placement — the joint grid is the
generator; pillars without a shared fabric read as noise columns. Overhangs and felled-pillar
arches need `11`'s non-heightfield stack.

**Verify.** Plan-view pillar edges cluster on two azimuths (the joint sets); summit heights
accordant with the remnant plateau; wall verticality maintained by an active rockfall/talus
budget (`09` mass check: wall retreat ↔ talus volume); no dissolution features (contrast 14).

**Tier.** L — `11` resistant strata + `02` orthogonal jointing (process mask) + `04`/`05`
joint-gated incision & rockfall + `07`/`13` perched ecosystem. No canonical paper — the
composition is the answer.

## Group K — Anthropogenic (the cultivated & engineered surface)

*The file's turn from a natural process to a human one. Everything above is "every landform is a
claim about a process" (`SKILL.md`) with a *natural* process; people are a geomorphic agent too —
they cut, fill, pond and dam — and the results obey the same field logic (contours, repose, water
layers, masks), which is why they belong in this skill rather than beside it. One entry today;
polders and reclaimed land, open-pit mines and quarries, cut-and-fill road grading, and dammed
reservoirs are the obvious neighbours as the category grows.*

### 25. Agricultural terraces — rice-paddy & dry-stone
*Rice: Banaue & the Cordilleras (Philippines) · Longji/Longsheng & Yuanyang (China) · Bali's subak ·
Tegallalang. Dry-stone: Inca Moray & Písac · the Douro & Cinque Terre vineyards*

**Claim.** The file's first **anthropogenic** landform — a hillside re-cut by people into a stair of
level benches. Every landform before this is a claim about a *natural* process; this is a claim
about a *human* one, and it obeys the same field logic: each terrace is a **flat bench at a constant
elevation** (a level set of the height field), its riser held at the material's repose, the flight
of them following the hill's **contours**. Wet-rice paddies pond each bench to a thin sheet —
turning the staircase into a cascade of mirrors; dry-stone terraces (vineyards, Inca beds) are the
same geometry without the water.

**Composition.**
- **Contours are the generator.** Terrace edges trace **iso-height lines** of the underlying slope
  (`06` — a contour *is* the level set of the height field), so the plan pattern is the hill's own
  topology. Steeper hill → narrower, more numerous benches (bench width ∝ 1/slope at a fixed riser
  height).
- **Cut-and-fill to a bench.** Each terrace is graded flat (a local `flatten` to a chosen datum,
  `10`), balancing cut against fill along the contour; the riser is a retaining wall (dry stone) or
  a packed-earth bund standing at the soil's repose (`05`).
- **Wet variant — water is the point.** Rice paddies hold a **thin dynamic water layer** (`08`) at
  each bench level, fed top-down and spilling bench to bench: a staircase of tiny closed basins
  (`03`), each ponded to its own spill level. Bali's subak even *schedules* the flow — the terrace
  is a hydrology as much as a landform.
- **Gated by slope and water (a process mask).** Terracing appears only in a slope band — too flat
  needs none, too steep won't hold — and, for rice, only where water can be routed (`06` slope mask
  ∩ a water-access mask). Outside the mask the hill is untouched; the sharp edge of a terraced zone
  against wild slope is a tell.
- **It is erosion control, i.e. the inverse of `04`.** Terraces exist to *stop* the natural process:
  they cut slope length and pond runoff, collapsing the hillslope's erosive power. Abandoned, they
  fail from the top down — riser blowouts, gullying through breaches — and the hill reclaims them; a
  maintenance/decay signature worth modelling if the brief is "old" or "ruined".

**The tells.** Nested, roughly-parallel level lines wrapping the hill's contours — bending around
every spur and re-entrant and *converging* where the slope steepens; benches flat, risers steep and
regular; for paddies, a stack of still water sheets brimming to their bunds and catching the sky;
a hard boundary where terracing stops and unmodified slope begins; keyed to a settlement and a water
source, not scattered.

**Watch for.** Drawing terraces as evenly-spaced *horizontal stripes* — they follow **contours**, so
parallel stripes read as corduroy, not agriculture; the convergence at spurs is the whole look. And
paddies need the **per-bench water level** (`08` dynamic layer over a `03` staircase of spill
basins), not a texture — dry the water and you have drawn dry-stone terraces (right for a vineyard,
wrong for Banaue).

**Verify.** Terrace edges coincide with iso-height contours of the base slope (they *are* level
sets); bench count and width scale with local slope; the terraced zone is bounded by a slope (and
water-access) mask, not the whole hill; paddy water sits level within each bench and steps down
bench to bench.

**Tier.** L — `06` contours (level sets) + slope/water process mask + `05` repose risers + `08`
per-bench water layer + a cut-and-fill `flatten` (`10`). No paper — a construction method, the
**anthropogenic sibling** of the natural terraces already in the file: river terraces (`03`), marine
terraces (`12`), travertine rimstone (entry 22). Those are cut or built *by a process*; these are
cut *by people to a plan*.

### 26. Field-mosaic farmland — large & small
*Large: the US Township-and-Range grid · High Plains center-pivot circles · the Canadian Prairies ·
Dutch polder fields. Small: English & Norman bocage · Cotswold strip fields · the vineyard mosaics
of Burgundy & the Mosel*

**Claim.** Cultivated *gentle* ground — what terraces (entry 25) are to slopes, field mosaics are to
plains. Farmland barely rewrites height; like Endor and the rainbow-strata note it is mostly a
**pattern-and-materials** story (fields, boundaries, crops, soil colour) over subtle natural relief —
but not *zero* height: hedge banks, terrace **lynchets**, ridge-and-furrow corrugation, drainage
ditches and land-grading are real micro-relief. Two scales, and the scale *is* a tell: **large**
fields are a geometry imposed *on* the land; **small** fields are a patchwork read *off* it.

**Composition.**
- **The base is gentle natural terrain** — a till plain, loess, a river terrace, a low plateau, a
  floodplain (`03`, `13`). Farmland makes no relief; it *dresses* whatever soft relief the natural
  pipeline left, so run the natural graph first and overprint.
- **Large / industrial — geometry over the land.** A survey grid (the Township-and-Range mile
  checkerboard) or a machine constraint (the center-pivot **circle**) tiles the surface regardless
  of its texture; drainage is engineered — the natural `03` network erased for straight tile-drains
  and ditches — and the land is often graded *flatter* to serve it. Reads as: large, rectilinear or
  circular, machine-scaled, indifferent to micro-terrain.
- **Small / smallholder — pattern off the land.** Small irregular fields follow slope, soil and
  water: contour strips, ridge-and-furrow, lynchets (soil crept downslope against a boundary over
  centuries), bounded by **hedgerows / bocage / dry-stone walls**. The field pattern is an *analysis
  mask made visible* — boundaries trace the terrain's own breaks (slope, wetness, lithology), so the
  mosaic is fine-grained and keyed to the ground.
- **Lithology is the hidden author — "terroir".** The rock under the soil sets **soil + drainage +
  relief**, which sets land use, which sets the pattern (`11` → `18` soil → `03` drainage → `13`
  land-use mask). **Limestone / chalk** (Burgundy's Côte d'Or, Champagne, the Cotswolds): well-
  drained, alkaline, thin soils, rounded relief with **dry valleys** (karst — surface water vanishes,
  so fields and villages cluster at springs and scarp-foot lines); the classic **vineyard /
  sheep-pasture** signature, walls and houses the same pale stone. **Sandstone** has two faces: a
  *hard* sandstone caps scarps and carries acid, sandy, infertile soil → heath, forest, rough grazing
  (thin, wooded pattern); a *soft* sandstone weathers to a warm arable loam → mixed farming. So
  "vineyard on limestone vs sandstone" is a real fork — the vine reads the drainage and warmth of its
  bedrock, and the field pattern, wall stone and crop change with the rock beneath.

**The tells.** Large: a grid or a field of circles, edges ignoring the land's grain, ruler-straight
ditches. Small: an irregular quilt whose seams follow contours, streams and soil lines, hedged or
walled, with lynchet steps and ridge-and-furrow. Across both: boundary, wall and building **stone
matches the local rock**, and a lithology contact often shows as a **land-use line** — vines or
pasture on the limestone, woodland on the sandstone — with no change in height, only in what grows.

**Watch for.** Painting farmland as *height* — it is ~90% a **materials/pattern overprint** (`06`
masks + `08` splat/satmap), not a heightfield edit; carve real relief for it and it reads wrong.
The two inverted tells: large-field geometry that *bends to follow* the terrain (it shouldn't — the
grid ignores the land), and small-field patchwork that is *regular* (it shouldn't — it follows the
land). And the terroir line is a land-use/material boundary on a **lithology mask** (`11`), not a
cliff.

**Verify.** Field pattern is a mask overprint with near-zero height change (only lynchets /
ridge-furrow / ditches perturb relief); large fields tile *independent* of terrain grain, small
fields *correlate* with slope/wetness/soil; land-use boundaries coincide with lithology/soil
contacts (`11`, `18`), not with elevation; wall and building material tracks the local rock.

**Tier.** L — gentle natural base (`03`, `13`) + `06`/`08` pattern-and-material overprint +
`11`→`18`→`03` lithology-driven land use (terroir) + micro-relief (lynchets, ridge-and-furrow,
ditches, `10`). The cultivated-*plain* sibling of entry 25's terraces: terraces re-cut *slopes*,
field mosaics dress *gentle ground*; both are human masks over a natural substrate.

### Earthworks — dams, mines & engineered ground *(compact)*

The cultivated surface (25, 26) has an engineered sibling: ground **moved by machines**, now the
dominant geomorphic agent on Earth by volume (Hooke 2000; Haff 2010 frames technology as a sediment-
transport process alongside rivers and hillslopes; Tarolli & Sofia 2016 is the review of human
topographic signatures in high-resolution DEMs). Mostly **L-tier** compositions — flat benches,
prisms and cones at a design angle — with two entries that carry a real quantitative model.

- **Reservoir & dammed river** *(any large dam)* — a dam turns a river into a settling basin. Inflow
  drops its load at the reservoir head as a **prograding delta**, fining toward the dam; the fraction
  trapped is the **trap efficiency** `TE(C/I)` keyed to the capacity-to-inflow ratio (Brune 1953 —
  `TE→0` for a tiny reservoir, `→ ~95–100%` once `C/I ≳ 0.5`; reference handbook Morris & Fan 1998).
  A fluctuating pool planes **bathtub-ring shorelines** — horizontal benches, the lacustrine terrace
  loop (`12`) at an authored level history. *Below* the dam runs **"hungry water"** (Kondolf 1997):
  sediment-starved release incises and coarsens the bed to an armour lag — the Exner budget (`04`)
  with upstream supply set to zero. The failure case is a **dam-break**: the dry-bed shallow-water
  solution (Ritter 1892) sends a wavefront downstream at `2·√(g·h₀)` with depth `4⁄9·h₀` at the dam
  site — an engineered megaflood, routed and eroded exactly like the natural outburst floods of `12`.
- **Mine & spoil** *(open-pit, mountaintop-removal)* — the **excavation** is nested benches: flat
  treads, risers battered at the design angle, an inverse terraced cone (the negative of a
  stratovolcano). The **waste** is its mass budget (`09`): spoil heaps, tailings and headwater
  **valley fills** (Palmer et al. 2010) deposited as cones/wedges relaxed to the **angle of repose**
  (`05` thermal) — bury the drainage line and the stream is gone. Cut and fill are one budget; a pit
  implies a pile.
- **Engineered ground** *(urban grading, road prisms, canals, levees)* — graded planar **benches**
  and slopes cut and filled to a **design surface**, tied to natural ground by batter slopes at a
  fixed angle. The governing rule is the **cut-and-fill balance** — excavated volume = placed volume
  (times a bulking factor) for a site that neither imports nor exports earth; solve for the datum that
  balances them. Levees, embankments and canals are prisms extruded along a polyline (`10` spline +
  SDF), spoil banked alongside the cut. All **L-tier** geometry over the volume-balance identity.

**Watch for** treating these as natural landforms — the tells are **unnatural planarity and constant
angles**: dead-flat benches, slopes at exactly the design grade, drainage that stops at a fill, and
delta/shoreline geometry pinned to authored pool levels rather than the natural base level. The mass
budget is strict: a cut is a fill somewhere, a trapped delta is a starved reach downstream.

**Verify.** Benches are dead-flat and slopes sit at a single design angle (a spike in the slope
histogram, `09`, not a repose-angle spread); reservoir shorelines are horizontal at authored pool
levels; the cut and fill volumes balance; below a dam the bed incises and coarsens. Naturalistic
scatter of slope angles = the earthworks look eroded, which is wrong.

**Tier.** L compositions over the Legal Order, with two P-tier quantitative hooks — Brune 1953 (trap
efficiency) and Ritter 1892 (dam-break wave) — plus the cut-fill and repose identities. Umbrella:
Hooke 2000; Haff 2010; Tarolli & Sofia 2016; Goudie, *The Human Impact*.

## Group L — Off-Earth

*The skill's off-Earth doctrine (`SKILL.md`) as worked assemblies. Two knobs reset the whole graph:
**is there liquid water**, and **what is the gravity**. No water switches the fluvial backbone
(`03`/`04`) OFF and lets **impact cratering** dominate; gravity rescales craters and dunes. The
unifying reading — **crater density is a clock**: a saturated surface is ancient, a sparse one
young, a crater-free one actively resurfaced. Per-crater morphology lives in `11`; these entries
build whole *surfaces*. For the whole *globe* — spherical grid, Euler-pole tectonics, global
circulation, planet-scale LOD, and how these regime knobs reset a planet-wide graph — see
`references/25-planetary-spherical.md`; these entries are the surface archetypes it assembles.*

### 27. Cratered highlands — lunar-type
*The Moon's highlands · Mercury · Callisto · any ancient airless surface*

**Claim.** The "Moon with different-sized craters." A surface with no water and no atmosphere
records **every impact it ever received**: craters of all sizes superimposed, older ones softened
and buried by younger ones and by micrometeorite gardening, until it reaches **saturation** — new
craters erase old ones as fast as they arrive. The size mix is not random; it is a **production
function**.

**Composition — this *replaces* the erosion backbone, it doesn't sit after it.**
- **Sample crater diameters from a size-frequency distribution:** `N(>D) ∝ D^(−b)`, a power law —
  many small, few large. (The planetary "production function"; the standard references are the
  Neukum and Hartmann–Neukum chronology functions — **verify before citing formally**. The graphics
  stamping is F.)
- **Stamp each crater with `11`'s size-dependent morphology:** bowl → central peak + terraces →
  peak-ring / multi-ring basin as `D` grows, the transition scaling **~1/g** (Melosh 1989, Pike
  1977, `11`). Each stamp is subtract-bowl + raise-rim + drape-ejecta (`11`), plus secondary chains
  and **rays** (`07` scatter + high-albedo streaks — rays are a *material*, not a height, feature).
- **Superpose in time order:** later craters cut earlier ones; accumulate many to saturate. Basins
  first (they set the macro), small craters last (the fine texture).
- **Degrade by gardening, which *is* diffusion:** micrometeorite churn softens relief exactly like
  hillslope creep — the same `D·∇²h` (`05`, Culling 1960) but driven by impacts, not water. Old
  craters go soft and rimless, fresh ones stay crisp. This also builds the **regolith**: an
  impact-comminuted cover (contrast `11`'s Heimsath *chemical* soil production) thickening with
  surface-exposure age.
- **Dry mass wasting only:** talus at the repose angle, which is **~gravity-independent** (`SKILL`
  doctrine — ~34° on the Moon too). No fluvial, no glacial, no coastal.

**The tells.** A power-law size mix (the eye reads "mostly small with a few big ones," not one
size); craters-on-craters with a clear *relative age* (crisp overlapping soft); ejecta blankets,
secondary chains and bright rays from the fresh ones; basins with peak rings; a soft,
regolith-mantled inter-crater surface; **no drainage network anywhere**.

**Watch for.** Craters as a Poisson scatter of one size — the SFD (many small, few large) *is* the
look, and superposition + degradation are the age story. And a fluvial pass sneaking in: on an
airless world, Legal Order steps 4–9 are OFF; cratering + gardening are the whole "erosion."

**Verify.** Crater size-frequency plots as a power law; overlapping craters show consistent
relative-age softening; morphology matches size (bowl/peak/ring at the right `D`, `11`); zero flow
accumulation; regolith thickest on the oldest terrain.

**Tier.** L — `11` per-crater morphology (Melosh/Pike, P) + F-tier SFD stamping & superposition +
`05` diffusion-as-gardening (Culling) + repose-angle invariant (`SKILL`).

### 28. Volcanic plains — lunar maria-type
*Lunar maria · Mercury's smooth plains · flood-basalt analogues off-Earth*

**Claim.** Vast dark low-lying **flood-basalt plains** that flooded and buried the older cratered
basins — so they are *younger* and carry **far fewer craters**, plus wrinkle ridges and rilles. The
mare/highland split is the Moon's fundamental dichotomy, and it is a **crater-density (age)**
contrast, not merely an albedo one.

**Diff from entry 27.** Flood the low basins with fissure-fed basalt sheets (`02` line source +
`11`/`19` stacked sheets — the Giant's-Causeway machinery of entry 17) → **reset the crater clock**:
the mare surface starts nearly crater-free and accumulates only the later, sparser population (same
SFD, far fewer stamps). Add **wrinkle ridges** (compressional buckles — low sinuous ridges, F) and
**rilles** (sinuous = collapsed lava tubes/channels, `19`; straight = graben, `02`).

**The tells.** Smooth dark plains embaying and drowning the cratered highlands (partly-buried
"ghost craters" show through); a sharp crater-density drop at the highland/mare contact; wrinkle
ridges snaking across the plain; sinuous rilles; a flat low datum.

**Watch for.** Giving the maria the *same* crater density as the highlands — the whole point is the
age contrast. And treating rilles as rivers — they are lava channels/tubes or graben (`19`/`02`),
on a world with no water.

**Verify.** Mare crater density markedly lower than adjacent highlands (the age contrast is the
check); ghost craters where basalt is thin; ridges compressional, rilles volcanic/tectonic; plains
flat and low.

**Tier.** L — `02` fissure/basin flood + `11`/`19` basalt sheets + reset SFD (entry 27) + wrinkle
ridges / rilles (F/`19`/`02`).

### 29. The blended relict world — Mars-type
*Mars · ancient-wet worlds generally*

**Claim.** The doctrine's hard case (`SKILL`): a world that *had* water and lost it. Ancient
**fluvial relics** — valley networks, outflow channels, deltas (Jezero) — sit **under a dominant
aeolian-and-impact overprint**, and low gravity makes everything bigger. You are layering a dead
Earth-style drainage beneath a live desert-and-cratering surface.

**Composition — a layered history, oldest to youngest.**
- **Old fluvial substrate, now relict:** run a *muted* `03`/`04` pass to carve valley networks and a
  delta or two, then **stop it** — the water is gone; these are eroded remnants, not active
  channels. Outflow channels / chaos = ancient catastrophic floods (`03` at extreme discharge, F).
- **Tectonic-volcanic macro:** **Valles Marineris** is a *rift graben* (extension over Tharsis),
  **not** a fluvial canyon (`02`); **Olympus Mons** is a shield edifice (`11`, Pike & Clow) grown
  huge by low gravity + a stationary hotspot — scale the edifice up, keep the shield's gentle flank.
- **Dominant aeolian overprint:** Werner dunes (`05`) with **Kok et al. 2012** gravity/air-density
  scaling (bigger dunes, transverse aeolian ridges, dust); mantling and exhumation.
- **Impact overprint:** a crater population (entry 27) with the transition diameter scaled to Mars'
  `g ≈ 0.38` → **bigger** craters (`11`).
- **Polar layered deposits:** ice + dust layering at the poles, paced by *orbital* (obliquity)
  cycles — climate strata, not seasonal snow (F).

**Regime knobs.** `g ≈ 0.38` → bigger craters, taller volcanoes, bigger/taller dunes; thin dry
atmosphere → aeolian **active**, fluvial **ancient only**. Set both and the same nodes produce Mars
instead of Earth.

**The tells.** Dendritic valley networks that are *degraded and dry*, not flowing; a delta debouching
into an empty crater (Jezero); a continent-long rift canyon (Valles Marineris) unrelated to the
drainage; an improbably broad, low-sloped giant volcano; dunes and dust mantling everything; big
craters.

**Watch for.** Making the valleys *active* rivers — they are relics; the live agents are wind +
impact (pick the dominant agent from the world, not habit — `SKILL`). And modelling Valles Marineris
as a river-cut canyon — it is tectonic.

**Verify.** Fluvial features present but degraded/dry (no current flow accumulation to a sea); dunes
and craters overprint the valleys (correct relative age); crater/dune sizes reflect Mars gravity
(`11`, Kok 2012); the giant shield's flank slope still matches its type despite the size.

**Tier.** L — muted `03`/`04` relict fluvial + `02` rift + `11` scaled edifice & craters + `05` /
Kok aeolian + polar layers (F). The `SKILL` doctrine paragraph, built.

**Other worlds (compact).** Same discipline, exotic regimes:

- **Titan — fluvial, but not water.** The one other body with an *active* fluvial cycle: **methane**
  rain carves dendritic networks and fills polar seas. Run `03`/`04` with a different fluid, add
  equatorial **organic-sand** dunes (Werner + Kok 2012 — dense atmosphere + low `g` → long
  longitudinal dunes) and hydrocarbon lakes as closed basins (`03`). Dominant agent = fluvial again
  — the lesson that "fluvial" is about a *liquid*, not about water.
- **Europa — a young ice shell, almost no craters.** Tidal resurfacing keeps it crater-*poor*, so by
  the crater-clock it is **young**: chaos terrain, double ridges and banded lineae, not erosional
  relief. Cryotectonic / cryovolcanic — the inverse of the lunar highlands.
- **Io — resurfaced so fast there are *zero* impact craters.** Relentless tidal volcanism erases
  them: paterae (volcanic depressions), extensive lava flows and fields (`19`), and tall *tectonic*
  mountains. The volcanic extreme of the crater-clock (density ≈ 0 → age ≈ now).

## Further archetypes (compact)

Same discipline, briefer — each still a composition, not an algorithm:

- **Slot canyon** *(Antelope, Buckskin Gulch)* — flash-flood incision of a narrow deep slot in
  resistant sandstone along a joint (`04` concentrated flow + `11` jointed sandstone); non-height-
  field where it overhangs.
- **Inselberg / monolith** *(Uluru, Devils Marbles, Sugarloaf)* — a resistant residual dome/bornhardt
  left by differential subsurface weathering + stripping (`16` bornhardt).
- **Fluted volcanic ridges (pali)** *(Nā Pali, the Ko'olau above Kualoa, Tahiti/Moorea)* — a young
  basalt shield flank (`11`) under extreme orographic rainfall (`13`): dense parallel gullies incise
  the steep flank into knife-edged fluted ridges with amphitheatre-headed valleys; wave trimming at
  the base only (`12`). The look people mislabel a "sea-cliff" — the fluting is *fluvial*, which is
  why it doesn't belong in entry 19.
- **Sandstone jebel desert** *(Wadi Rum — Lawrence of Arabia country)* — massive sandstone
  tower-massifs (jebels) on a hard basement plinth (`11` strata + `16` inselberg logic), rising
  sheer from red sand sheets: rounded slickrock domes on top, vertical joint-controlled walls,
  narrow siq fissures, talus at the base. The sand *is* the jebels' own waste (`09` mass budget) —
  weathered grain by grain, banked against the very towers it came from (`05`, `16`).
- **Braided outwash** *(Iceland sandur, Southern Alps NZ, Brahmaputra)* — high sediment + variable
  discharge + low cohesion → braid bars (`03` braided, Leopold & Wolman 1957); the depositional
  export of a glaciated / high-uplift range.
- **Rainbow strata** *(Zhangye Danxia, Painted Desert)* — a **material/colour** story, not a landform:
  tilted, differentially-coloured strata exposed by erosion; do it in the `K`/material + satmap
  layers (`11`, `08`), not the height.
- **Patterned ground & thermokarst** *(Siberian & Canadian Arctic)* — periglacial self-organisation
  and ground-ice collapse (`17`); the polar-plain archetype.
- **Cratonic shield / plains** *(Canadian Shield, Australian outback, Great Plains)* — the "quiet"
  archetype people forget: near-zero uplift on ancient rock → very low relief, old/deranged drainage,
  thin soil over scoured bedrock (`02` uplift-off + long erosion). Every world needs its calm
  interior.
- **Channeled scabland / megaflood tract** *(Columbia Plateau, Washington; Icelandic jökulhlaup
  sandurs)* — a catastrophic outburst flood (`12`) routed over jointed bedrock: anastomosing dry
  **coulees**, **cataracts** and plunge pools (Dry Falls), **giant current ripples** and streamlined
  **loess islands**, all sized to a flood hundreds of metres deep. The tell is **scale mismatch** —
  landforms far too big for any current stream. On a dry world the same suite with the water switched
  off is a fossil megaflood (entry 29, Beggar's Canyon).
- **Seamount chain & guyot** *(Hawaiian–Emperor chain, Pacific guyots)* — the deep-sea sibling of
  entry 20's atoll: an **age-progressive** line of hotspot volcanoes (`02`/`11`) subsiding on the
  **√age** curve (`12`), each wave-truncated flat and carried down as a **guyot**; the youngest still
  emergent, the oldest long drowned. Darwin's subsidence sequence continued past the reef, and a
  bathymetry archetype for a planet whose seafloor is visible terrain.
- **Desiccated sea basin** *(the Aralkum — the exposed floor of the dried Aral Sea; the Bonneville
  Salt Flats on the bed of Pleistocene Lake Bonneville)* — a former sea/lake floor laid bare. Start
  from the **shelf → slope → abyssal** profile with relict submarine canyons and guyots (`12`),
  remove the water, and floor the basin with an **evaporite crust** (`18`, entry 22) crazed by
  **desiccation mud-cracks** (a Worley F2−F1 pattern, `01`). Then aeolian erosion (`05`/`16`) blows
  the soft marine muds into dunes and leaves the resistant beds as **yardangs** (`16`, Ward &
  Greeley). The tell is a mirror-flat salt plain studded with wind-carved ridges over a *bathymetric
  ghost*. **Tier L.** *(This is the honest geology behind the "exposed ocean bed" look; Mad Max:
  Fury Road itself was shot in the Namib erg — entry 9 — not a dried sea.)*

## Combining archetypes

Most real wonders are *two* of these overprinted: a fjord is a glaciated orogen (1) drowned (18);
Ha Long Bay is tower karst (14) drowned like a fjord; Kilimanjaro is a stratovolcano (15) wearing
entry 1's summit ice; the Grand Canyon (7) grows caprock-plunge knickpoints (4) in its side-streams;
a Saharan oasis (12) is 9's wind machinery run as *source*: a deflation basin floored at the water
table, its exported sand banked downwind as the dunes. The rule is Chapter 13's: read the two
archetypes, run **one substrate and one hydrology**, and let the regimes overprint in Legal Order —
never blend two finished terrains. Off-world the same rule holds in *time*: Mars (29) is five
archetypes layered oldest-to-youngest — relict fluvial, then rift, then giant shield, then dunes,
then craters — each overprinting the last on one shared surface, which is why the relative-age order
is the thing to get right.

## Screen worlds — fictional planets as recombined Earth archetypes

Chapter 13's fictional-world doctrine (Hyrule, Middle-earth) applied to a single alien locale. A film's
planet — or lost island — is never new physics: it is **Earth archetypes in costume**, and the
**filming location names the archetype**: a production designer scouts the real place whose *process* already reads as
the story's world, and a terrain graph does the identical composition, changing only the **set
dressing** — materials, sky/light, and the scatter of props (`06`/`08`, `07`). So "make an ice
planet / a desert planet" is not a new recipe; it is *decompose the fiction into the archetypes
above, then re-dress.* There is no "Hoth algorithm" for the same reason there is no atoll one.

- **Hoth** *(filmed at Finse & the Hardangerjøkulen glacier, Norway)* — an **ice-sheet world**: the
  glacial machinery of entry 18 with **sea level off and the ice cap on**. Ice sheet + valley
  glaciers + crevasse fields, **nunataks** (rock islands piercing the ice), wind-scoured **sastrugi**
  (aeolian on snow), and periglacial ground where rock is bare (`12` glacier flow/erosion, `13` snow
  & avalanche, `17` blockfields). Hoth is the *un-drowned, still-glaciated* parent of the Fjordland
  entry — same ice, no sea.
- **Endor** *(filmed in the Californian coast redwoods; the speeder chase at Cheatham Grove)* — the
  lesson that some famous "places" are an **ecosystem, not a landform**. Gentle relief carries a
  giant-conifer **ecosystem** (`13` competition sim, `07` Deussen scatter) — the *biome* is the
  subject, the height almost incidental. Like the rainbow-strata note, this one lives in the
  material and foliage layers, not the heightfield.
- **Tatooine** *(filmed in Tunisia — Chott el Djerid, the Nefta/Tozeur dunes, and Maguer Gorge at
  Sidi Bouhlel — plus Death Valley in 1977)* — a **desert composite**, and a worked "combine": an **erg** (entry
  9) for the dune seas + a **chott / sabkha salt flat** (entry 22) for the homestead pan + a **wadi** (16) /
  **slot canyon** (Further archetypes) for the canyon chase. Three archetypes already in this
  file, one substrate, one (dry) hydrology — exactly the combining rule.
- **Pandora's Hallelujah Mountains** *(not filmed but modelled — on Zhangjiajie's pillar forest)* —
  the CG case proves the same rule: the designers reached for entry 24's joint-gated pillars, then
  applied exactly one impossible edit (cut the pillars free and float them). The terrain is Earth;
  the fiction is one constraint deleted.
- **Skull Island** *(Kong: Skull Island 2017, filmed in Vietnam — Ha Long Bay and the Tràng An /
  Tam Cốc karst of Ninh Bình — and on O'ahu at Kualoa, under the fluted Ko'olau ridges; Peter
  Jackson's 2005 island was soundstage + CG, the 1933 original matte paintings)* — a composite of
  **two archetypes an ocean apart**: drowned **tower karst** (entry 14 — Ha Long Bay is already its
  exemplar) for the fanged coastline, and **fluted volcanic ridges** (Further archetypes, the pali)
  for the interior walls, wrapped in a storm coast (entry 19) and a jungle **ecosystem** (`13`,
  `07`). Only a film can composite two continents by cutting between locations; a terrain graph
  building Skull Island must still run **one substrate and one hydrology** under both looks — karst
  lithology on the coast, basalt shield inland — or the seam will show exactly where the film hides
  its cut. The monsters are scatter.
- **Beggar's Canyon, Tatooine** *(the womp-rat run and podrace gorges; the canyon on screen is
  **Maguer Gorge** at Jebel Sidi Bouhlel near Tozeur — "Star Wars Canyon", a Campanian-age layered
  gorge that played THREE Tatooine places: the Jundland Wastes in Episode IV, the podrace's Canyon
  Dune Turn in Episode I, and Sluuce Canyon — plus the ark ambush in Raiders; the wider podrace
  canyons are digital, from the American-Southwest vocabulary, with Death Valley plates in 1977)* —
  one real gorge serving three fictional locales is the screen-worlds thesis in a single site: the
  archetype is constant, only the dressing changes. And it is the fictional case of entry 29's
  **relict-fluvial rule**: a deep dendritic canyon system on a waterless world *is a fossil* — it
  claims a wet past, exactly like a Martian valley network. Compose it dry: an entrenched-meander
  gorge (entry 13, goosenecks for a racing line) + slot narrows (Further archetypes, `16` wadi) +
  caprock steps and dry falls — relict knickpoints (entry 4) with no plunge pool — then **switch
  the water off** and overprint with aeolian sand and rockfall (`05`, `16`, entry 29's relative-age
  order). A canyon carved by *nothing* is the tell that breaks the fiction; a canyon carved by
  vanished water is Mars, and reads true.

- **Arrakis** *(Dune 2021/2024, filmed at Wadi Rum, Jordan, and the Liwa erg, Abu Dhabi)* — the
  desert planet is **two archetypes cut together**: the **sandstone jebel desert** (Further
  archetypes) for sietch country — towers to hide a civilisation in, walls to stage scale against —
  and the **erg** (entry 9) for the open sand where nothing stands. The same pairing Tatooine used
  (chott + gorge + dunes), chosen again fifty years later because the *processes* read instantly:
  rock country means shelter, sand sea means exposure. The worm's wake is set dressing on entry 9's
  dunes; Wadi Rum has also played Mars itself (The Martian) — the red jebel desert *is* the
  relict-fluvial look of entry 29 to a camera.
- **Crait** *(The Last Jedi, filmed at Salar de Uyuni, Bolivia)* — the rare case where the film's
  conceit **is the material stack**: entry 22's evaporite playa — a white salt crust (`18`) over
  red substrate — and every shot of a speeder skid scraping white to reveal red is the layer
  diagram of `08` rendered as drama. Nothing needed inventing: the terrain department's job was
  entry 22 plus one albedo swap underneath.
- **Interstellar's planets** *(both filmed in Iceland)* — one island plays two alien worlds,
  chosen by process: **Mann's frozen world** is the Svínafellsjökull glacier — crevasse fields
  and ice-fall chaos, entry 18's machinery with the sea nowhere in sight — and **Miller's ocean
  world** is a black-sand **braided outwash plain** (Further archetypes) under ankle-deep water:
  a sandur is the flattest large surface erosion ever builds, so flooding it centimetres deep
  makes an ocean with no shore in any direction. The wave is a set piece; the *shorelessness* is
  the sandur's real property, and it is why the location works.
- **Monument Valley** *(Stagecoach, The Searchers, Once Upon a Time in the West, Back to the
  Future III, Forrest Gump's stop on US-163)* — the **inverse case**, and the proof the section's
  thesis runs both directions: not a fiction decomposed onto Earth archetypes, but a real
  archetype so legible it became fictional shorthand — "the West" itself, though Ford's Texas is
  actually the Navajo Nation on the Utah–Arizona line. Terrain-wise it needs no decomposition: it
  **is entry 7's end-member** — the plateau almost wholly consumed, leaving the mesa → butte →
  spire remnant series standing on an open plain, each butte repeating the same three-layer
  anatomy (thin hard cap, cliff-forming sandstone, slope-forming shale). Cameras keep returning
  for the same reason the entry's Verify block works: the process history is readable at a
  glance, from horseback or a car window.
- **Avatar: The Way of Water** *(the reef world modelled on Raja Ampat / Palawan — drowned tower
  karst)* — entry 14's **drowned tower karst** (Ha Long Bay's mechanism) taken to a reef sea:
  limestone towers left by vertical dissolution to an old water table (`11`), then drowned by
  sea-level rise (`03`/`12`). Two edits separate it from Skull Island. **Wave-cut notches** at the
  waterline undercut each pillar into a top-heavy **mushroom** — a true overhang, so it needs the
  *Arches* non-heightfield representation (`11`, Peytavie 2009), not a heightfield. And **coral
  accretes as rings** around every tower (`12` photic-zone `reefStep`, the fringing stage of entry
  20). Same karst; the notch and the reef are the dressing. **Tier L.**
- **Prometheus / Death Stranding** *(the Icelandic highlands — Dettifoss, the Vatnajökull margins)* —
  **subglacial volcanism** as a whole landscape: entry 17's Iceland end-member built out. Basalt
  erupts under a thick ice mask (`19`) and quenches in meltwater instead of spreading, stacking into
  **tuyas** — flat-topped table mountains with steep **ice-confined quench flanks** (hyaloclastite /
  palagonite; *not* thermally-relaxed slopes) under a subaerial lava cap. Then a **jökulhlaup**
  (`12` outburst) routes catastrophically over the plains (`03`), cutting anastomosing **scabland**
  canyons (`12` megaflood), and the milled debris is **black basaltic sand** (`18`), not quartz — the
  signature dark beaches and mudflats. **Tier L** — `17` tuyas + `12` jökulhlaup + `18` sediment.
- **Up / The Lost World** *(Angel Falls & the Roraima tepuis — the Gran Sabana of entry 8)* —
  Paradise Falls *is* entry 8's **tepui**, worth two added mechanisms: incision follows an
  **orthogonal joint/fault network** (weak-`K` lines, `02`) so the quartzite is quarried into
  rectangular vertical-walled blocks with basal talus (`05`) — the joint-gated logic of the
  Zhangjiajie pillars (entry 24); and because the caprock is too resistant to incise, the summit
  lowers by **pseudo-karst dissolution** (`11`), sinkholes punching through the block to feed the
  sheer-drop waterfalls. Flat summits carry **isolated, contained ecosystems** (`13`). **Tier L.**
- **Blade Runner 2049's trash mesas** *(concept-designed, not a location — the honest case of an
  invented "geology")* — a **geological-scale landfill** eroded into badlands, the file's most
  extreme anthropogenic archetype (Group K). **Stack** compacted refuse as Voronoi terraces of cubes
  and walls (*deliberately not fractal noise*), then set the stratigraphy (`11`) by erodibility:
  rust (soft, high `K`), compressed plastic (low `K`, near-impermeable), scrap metal (hard).
  Near-zero permeability + **acid precipitation** (`13`) drives **stream-power badlands** (`04`) that
  wash out the soft layers and pond **toxic lakes** in the unfilled sinks (`03`), all mantled in
  aeolian dust and smog (`05`). The tell: *stratified* mesas whose "beds" are manufactured.
  **Tier L** — the landfill-badlands extension of Group K.
- **Nevarro** *(The Mandalorian — a basalt quarry dressed with CG)* — a **fissure flood-basalt
  plain**, entry 17's traps at rest: line-source eruptions along faults (`02` as *emission* lines,
  not weakness lines) stack levéed **Bingham** lobes (`19`) into a stepped plateau with **no fluvial
  dissection**. The look is the **emissive-crust** recipe (`08`): an F2−F1 Worley pattern (`01`) for
  the cooling-plate cracks, a temperature ramp mapped into the fissures for the glow. **Tier L** —
  entry 17 + `08`/`19` emissive crust.
- **Mordor** *(Mount Ngauruhoe / Tongariro as Mount Doom, beside the real Rangipo rain-shadow desert
  on the volcanic plateau's lee)* — a **rain-shadow volcanic basin**, a clean worked combine. A
  convergent orogen (`02`) rings the basin — make the ramparts *unnaturally angular* only if the
  story demands it, and know it is a **stylization** (real collision ranges are arcuate, not
  rectangular). The **orographic rain shadow** (`13`, Smith & Barstad) does the work: a strong
  prevailing wind dumps rain on the *outer* flanks (heavily incised by stream power, `04`) and
  starves the interior, leaving the inner walls steep, jagged and water-untouched. A central
  **stratovolcano** (`11`, entry 15) mantles the plain with a wind-dispersed **tephra** blanket
  (`11` exponential thinning) and feeds **Bingham lava lakes** (`19`). The tell: a dead, ash-choked
  basin whose walls are asymmetric — green and gullied outside, bare and sheer inside. **Tier L.**

**The through-line:** the alien-ness is set dressing; the *landforms* are Earth, chosen by process to
read as the story's world — which is the whole skill. Twin suns and a sarlacc don't change the graph;
they change the palette and the scatter.

## Worlds at another scale — the miniature POV

*A world seen by an insect, a Smurf, or from SpongeBob's Bikini Bottom. This is the sibling of the
off-Earth group: not a new landform but a **regime knob turned**, and the knob is **scale**. It is
the cell-size doctrine (`SKILL.md`, "derive the cell size") and "detail is recursive — but only
where the process is scale-free" taken to their limit — because at `cellSize` of millimetres,
**different physics dominates**, and the heightfield's assumptions quietly break.*

**Why it isn't just "zoom in".** Shrinking a mountain gives a *toy*, not a bug's world, because the
mountain's processes are **scale-bound** (`SKILL.md`): fluvial incision, tectonics and glaciers
carry real length scales and don't recur at millimetre size. Run the *small-scale* processes
instead and the world reads true:

- **Surface tension beats gravity.** At mm scale the dominant fluid force flips — a dewdrop is not a
  puddle but a **bulging lens with a curved meniscus** that beads and rolls; water climbs by
  capillarity; a "lake" has a skin an insect walks on. Model water as a **cohesive, meniscus-bounded
  blob**, not the thin flat sheet of `08`. (The same "which force wins" regime-swap as off-Earth
  gravity — here it's surface tension vs gravity, not g vs water.)
- **The continuum breaks — grains are boulders.** Sand stops being a smooth `05` field and becomes
  **individual clasts** the size of the viewer; "soil" is a jumble of pebble-boulders with caves
  between them. This is `07` scatter and the `11` material-stack (voids, overhangs everywhere)
  *replacing* the heightfield — a bug's ground is more cave than surface.
- **Biology is the macro-structure.** With no tectonics at this scale, the "mountains" are
  **organisms**: moss is a forest canopy, a leaf is a plain, bark is a canyon system, a root is a
  buttress, a mushroom is a tower (the Smurf case exactly — a village at fungal scale, forest-floor
  as terrain). Build the relief from an ecosystem (`13`, `07`), not from `02`/`04`.
- **Micro-erosion is a real process, and it's fast.** Rain-splash cratering (each drop an impact,
  `11` at mm scale), rill initiation on a mud bank, mud-crack polygons on a drying puddle
  (desiccation, the material sibling of `05` thermal), dew and frost heave. These *are* the bug's
  geomorphology — and they run in minutes, not millennia.

**The stylised cases fold in as before (a real regime + one edit).**
- **Bikini Bottom (SpongeBob)** — a **benthic / seafloor** world at human-town scale: subaqueous
  sand **ripples** (`05`'s dune machinery, run under water — the current is the wind), a coral bed
  (`12` reef, entry 20), kelp as forest (`13`/`07`), everything under a permanent water column with
  no free surface to walk on (`08` water as the medium, not a layer). The edit is the cartoon flatten
  plus a town; the substrate is a real reef-and-ripple seafloor.
- **A Smurf village / A Bug's Life / Honey-I-Shrunk-the-Kids** — the insect-POV regime above,
  art-directed: run moss-forest, grain-boulders, meniscus-water and rain-splash micro-erosion, then
  stylise. The convincing ones (Pixar's *A Bug's Life*, *Arrietty*) get the **physics** right — dew
  beads, translucency, grain scale — before the styling; the toy ones just shrink props.

**The through-line, restated for scale:** *pick the process from the scale, not from habit* — the
sibling of the off-Earth rule "pick the dominant agent from the world". A believable tiny world is
run with surface tension, granular mechanics, and biology-as-relief; a mountain shrunk to a
thumbnail is the tell that someone confused *zoom* with *regime*.
