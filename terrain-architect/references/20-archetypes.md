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
archetypes (Group J) change the *regime itself*: no liquid water switches the fluvial backbone
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

**The tells.** Tight meanders with oxbow lakes and scroll-bar ridges on a flat floodplain; natural
levees standing above backswamps; for Okavango, a fan of distributary channels dissolving into
reed-and-water wetland with *no outlet to the sea*; braided reaches where slope or sediment rises.

**Watch for.** Meanders on a *steep* slope — meandering is a *low-gradient floodplain* process
(Legal Order 9c, after the valley is cut). The wetland needs the *closed/flat + thin water layer*
(water as a dynamic layer, `08`), not a carved lakebed.

**Verify.** Sinuosity high on the low-slope reach; oxbows/scrolls present; the Okavango basin closed
(endorheic — flow terminates in the wetland); water modelled as a thin dynamic layer over near-flat
ground.

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

## Group J — Off-Earth

*The skill's off-Earth doctrine (`SKILL.md`) as worked assemblies. Two knobs reset the whole graph:
**is there liquid water**, and **what is the gravity**. No water switches the fluvial backbone
(`03`/`04`) OFF and lets **impact cratering** dominate; gravity rescales craters and dunes. The
unifying reading — **crater density is a clock**: a saturated surface is ancient, a sparse one
young, a crater-free one actively resurfaced. Per-crater morphology lives in `11`; these entries
build whole *surfaces*.*

### 23. Cratered highlands — lunar-type
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

### 24. Volcanic plains — lunar maria-type
*Lunar maria · Mercury's smooth plains · flood-basalt analogues off-Earth*

**Claim.** Vast dark low-lying **flood-basalt plains** that flooded and buried the older cratered
basins — so they are *younger* and carry **far fewer craters**, plus wrinkle ridges and rilles. The
mare/highland split is the Moon's fundamental dichotomy, and it is a **crater-density (age)**
contrast, not merely an albedo one.

**Diff from entry 23.** Flood the low basins with fissure-fed basalt sheets (`02` line source +
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

**Tier.** L — `02` fissure/basin flood + `11`/`19` basalt sheets + reset SFD (entry 23) + wrinkle
ridges / rilles (F/`19`/`02`).

### 25. The blended relict world — Mars-type
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
- **Impact overprint:** a crater population (entry 23) with the transition diameter scaled to Mars'
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

## Combining archetypes

Most real wonders are *two* of these overprinted: a fjord is a glaciated orogen (1) drowned (18);
Ha Long Bay is tower karst (14) drowned like a fjord; Kilimanjaro is a stratovolcano (15) wearing
entry 1's summit ice; the Grand Canyon (7) grows caprock-plunge knickpoints (4) in its side-streams;
a Saharan oasis (12) is 9's wind machinery run as *source*: a deflation basin floored at the water
table, its exported sand banked downwind as the dunes. The rule is `13`'s: read the two
archetypes, run **one substrate and one hydrology**, and let the regimes overprint in Legal Order —
never blend two finished terrains. Off-world the same rule holds in *time*: Mars (25) is five
archetypes layered oldest-to-youngest — relict fluvial, then rift, then giant shield, then dunes,
then craters — each overprinting the last on one shared surface, which is why the relative-age order
is the thing to get right.

## Screen worlds — fictional planets as recombined Earth archetypes

`13`'s fictional-world doctrine (Hyrule, Middle-earth) applied to a single alien *locale*. A film's
planet is never new physics — it is **Earth archetypes in costume**, and the **filming location
names the archetype**: a production designer scouts the real place whose *process* already reads as
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
- **Tatooine** *(filmed in Tunisia — Chott el Djerid, the Nefta/Tozeur dunes, the Sidi Bouhlel gorge
  — plus Death Valley in 1977)* — a **desert composite**, and a worked "combine": an **erg** (entry
  9) for the dune seas + a **chott / sabkha salt flat** (entry 22) for the homestead pan + a **wadi /
  slot canyon** (`16`, Further archetypes) for the canyon chase. Three archetypes already in this
  file, one substrate, one (dry) hydrology — exactly the combining rule.

**The through-line:** the alien-ness is set dressing; the *landforms* are Earth, chosen by process to
read as the story's world — which is the whole skill. Twin suns and a sarlacc don't change the graph;
they change the palette and the scatter.
