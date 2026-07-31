# Sprint 4 — Water & rivers (L3): authored sources, flow field, lakes `[K]`+`[E]`

**Goal.** Expose the complete hydrological backbone: explicit depression policy, physical routing,
authored source/guide features, lakes, and rivers. Sources carry `discharge` and seed the same
accumulation stack as rainfall; the simulation owns water geometry. Lakes come out flat-at-spill by
construction; rivers are discharge/width/depth fields — **never an implicit carve**.

**Depends on:** Sprint 2 (typed raster/feature/scalar ports), Sprint 3 (final solid-top stack), and L1
routing which is **done internally** (MFD8/MFD6 landed, `PROGRESS.md`). The missing product surface is
first-class policy/direction/area/discharge output: `hydrofix` is subtle downcut conditioning, not a
fill/breach/preserve policy, and `d_flow` is a log-compressed preview field. **Implements:** `BACKLOG
D5`, `BACKLOG W5`, D7 **L3**.

**Doctrine in force — this is the sprint where guardrail 1 earns its keep.** Gaea's `Rivers` writes
water into height "on any terrain, whether it can sustain rivers or not". `08:126-128` forbids it:
*water should not bake.* `03:696-701` (P-tier): *"A spring is not a bump in the height field — it is a
source term in the flow field."* We keep `water` as a layer that defines where fluid is; the only
legitimate height write remains `hydrofix` (bedrock drainage conditioning), which stays a distinct,
distinctly-labelled node.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S4.1 | Depression Policy: fill / breach / preserve | `[K]` | 5 | routing surface + signed conditioning delta + basin products; solid input unchanged |
| S4.2 | Physical Flow: direction / area / discharge | `[K]` | 5 | MFD8/MFD6; world units; `d_flow` remains preview |
| S4.3 | Authored sources and river guides as feature sets | `[E]` | 8 | movable point/spline objects; discharge; persistence/migration |
| S4.4 | Lake / Basin multi-output node | `[K]` | 5 | surface, depth, signed shore distance, basin/spill features |
| S4.5 | Rivers as discharge/width/depth fields (**no carve**) | `[K]` | 5 | geometry owned by sim; guides constrain intent, not elevation |
| S4.6 | Conflict surfacing and explicit conditioning branch | `[C]` | 3 | report deficit; user may invoke Policy/HydroFix explicitly |

---

### S4.1 — Depression Policy · `[K]` · 5 pts
**User story:** As a terrain author, I choose whether closed depressions fill, breach, or remain
endorheic before any flow result is interpreted.

Add a first-class node with `fill`, `breach`, and `preserve` modes. Emit original solid height,
conditioned routing surface, depression depth, basin IDs, and spill features. The conditioned product is explicitly a
`routingSurface`, not rendered/collision height; the primary solid height remains bit-identical in
all modes. Emit signed `conditioningDelta:m` so the author can inspect what an explicit conditioning
process would change. `preserve` makes `routingSurface` equal input and keeps closed basins explicit.
Keep **HydroFix** separate: it is low-amplitude accumulated-corridor conditioning and its inspector
says it does not fill the rendered terrain.

**Acceptance gate** — `tests/legacy/_verify_depression_policy.js`: on analytic single- and nested-
basin fixtures, Fill raises each basin exactly to its lowest spill, Breach produces a monotone outlet
path without raising the basin, and Preserve is bit-identical **on the routing surface**. The solid
height output is bit-identical for all three. Delta/depth use physical units and lattice cell area.
The modes must produce distinct routing topology on both lattices; mapping two modes to priority fill
or mutating solid height is the armed failure.

---

### S4.2 — Physical Flow · `[K]` · 5 pts
**User story:** As a terrain author, I can wire physical flow direction, drainage area, and discharge
without decoding a normalized preview image.

Wrap the existing MFD8/MFD6 routing as typed products over the chosen Depression Policy output.
`flowDirection` is the normalized first moment of MFD receiver weights (vector raster),
`drainageArea` is m², and `discharge` is m³/s from a typed `precipitation:mm/yr` scalar-raster input
plus authored sources. S4's analytic gates use a uniform precipitation fixture; S5's Orographic
Moisture is the production spatial source. The routing node never invents rain internally.
`d_flow` remains a log-compressed visualization for compatibility; do not relabel it as physical.

**Acceptance gate** — `tests/legacy/_verify_physical_flow.js`: on analytic planes the direction
vector matches steepest descent within one lattice angular quantum; drainage area at outlets matches
domain area within one cell area; zero-precipitation/zero-source discharge is exactly zero; a uniform
precipitation fixture integrates to rain rate × contributing area. Run the existing facet and resolution gates and assert
all output units/ranges.

---

### S4.3 — Authored water sources and guides · `[E]` · 8 pts
**User story:** As a terrain author, I can place/edit persistent springs, inflows, and river guides
whose discharge enters routing as a source term rather than a height stamp.

**Implements:** `D5`, `W5`. Sources are movable objects carrying `discharge` (m³/s), optional
`temperature`, and `kind`; river guides are editable splines carrying intent and optional target flow.
`discharge` seeds the **same** accumulation stack as area `A` — no new
algorithm, a different seed (`03:673-676`, P-tier). Under uniform rain `Q ∝ A` and nothing changes;
with sources they diverge and `Q` is the physically correct driver (stream power `K·Q^m·S^n`, river
width/depth scale on `Q`). The `kind` enum already exists in the corpus: distributed rain · boundary
inflow · spring · karst resurgence · oasis · glacial/snowmelt (`03:687-694`).

Sources/guides use Sprint 2 `featureSet` ports, world-metre coordinates, stable IDs, deterministic
serialization, copy/paste, undo/redo, and saved-document migration. **Salinity is not committed by
this story:** it remains a proposed registry extension in `BACKLOG §2`; include it only after a
separate decision fixes its unit, advection, and export contract.

**Acceptance gate** — `tests/legacy/_verify_water_sources.js`:
- **A big river crosses a desert:** with zero rainfall and one source, assert discharge immediately
  downstream equals the authored source flow within solver precision and remains conserved to the
  outlet absent sinks. Removing the source returns exactly zero. This is stronger than an arbitrary
  source/no-source ratio.
- Save/reload and move the source: stable ID/properties survive, and only the downstream flow cone
  changes. A fixture that stamps source discharge into height must fail the no-height-write fence.

---

### S4.4 — Lake / Basin node · `[K]` · 5 pts
**User story:** As a terrain author, I can route lake surface, depth, shore distance, basin identity,
and spill features as separate physical products.

**Needs Sprint 2's multi-output contract** — this node emits `waterSurface`, `waterDepth`, signed
`shoreDistance` (m), derived `basinId` label raster, and basin/spill feature sets. Lake surface is
`filledDem` out of priority-flood — **flat by construction** (`03:326-328`, P), not a constraint we
enforce.

**Acceptance gate** — `tests/legacy/_verify_lake.js`:
- **Flat-at-spill, armed:** assert the lake surface is constant across the whole water body to within
  1e-5, and that its level equals the spill elevation. The failing endpoint: a version that fills to
  a fixed slider level regardless of spill must fail the "level == spill" assertion.
- Assert `waterDepth = max(0, surface − solidTop)` exactly; signed shore distance is zero at the
  depth boundary and has correct sign/magnitude on an analytic circular basin; spill sits on the
  lowest rim. A shore mask may be derived downstream, but the primary production output is metres.
- Assert **no height was written** — the terrain field is bit-identical before and after the Lake
  node (guardrail 1). This is the single most important assertion in the sprint.

---

### S4.5 — Rivers as fields, not a carve · `[K]` · 5 pts
**User story:** As a terrain author, I can generate channel geometry drivers from discharge while
keeping solid terrain unchanged unless I add an explicit conditioning process.

A `Rivers` node emits a channel mask, width, and **water-depth** field, all scaled on `Q` — depth is
hydraulic water depth, never carve depth, and the node does **not** modify height. Width/depth scale
on discharge (hydraulic geometry). Braided/anastomosing
channels are available later from `terrain-architect/reference-impl/braided.py` (note the Gaea node is
a downcutting carve, so matching *reality* is the harder, correct target).

Hydraulic-geometry exponents/ranges are fixed from the cited source during Definition of Ready, not
tuned after the output is seen.

**Acceptance gate** — `tests/legacy/_verify_rivers.js`:
- Assert the terrain height output is **bit-identical** to the input (guardrail 1 — this is the
  negative control that would catch any accidental carve).
- Assert channel width/depth match the predeclared power-law oracle at three discharges and increase
  monotonically downstream; tolerances are fixed before implementation.
- On an analytic Y-valley, assert the channel skeleton stays within one cell of both known thalwegs,
  joins at the analytic confluence, and reaches the outlet; a guide-only straight line must fail.

---

### S4.6 — Conflict surfacing + explicit conditioning branch · `[C]` · 3 pts
**User story:** As a terrain author, an impossible guide tells me where and by how much it conflicts,
and any terrain conditioning remains an explicit undoable choice.

An authored **river guide** that climbs above the routed surface reports the elevation deficit
("needs 4 m of conditioning here") and offers to create an explicit Depression Policy/HydroFix
branch. The Rivers node itself never mutates height (`D5`: conflicts are surfaced, not corrected).

**Acceptance gate** — `tests/legacy/_verify_water_conflict.js`: place a guide with one analytic uphill
segment; assert the reported maximum deficit equals the sampled terrain-guide difference and height
is unchanged. A valid downhill guide emits no conflict. Accepting the offer adds a visible, undoable
conditioning node/branch; it never turns on a hidden carve inside Rivers.

---

## Sprint 4 exit gate

- Depression-policy, physical-flow, source/guide, lake, river, and conflict oracles are green, each
  with a demonstrated failing fixture.
- **Guardrail 1 regression fence:** a repo-wide assertion that no water-family node writes `height`
  (only `hydrofix` may) — armed by a fixture node that carves, which must fail.
- Feature serialization/migration and typed wiring gates are green; digest skips = 0.
- Digest bit-identical for pre-existing nodes; new types green. **D7 L3 verified.**
