# Sprint 7 — Geology & regimes: strata, rock, aeolian, mass movement `[K]`

**Goal.** Add the geological finish and two missing transport regimes after state layers exist.
Reference implementations reduce research risk but are not drop-in production nodes: they use NumPy,
have square assumptions in places, and `runout.py` returns a path rather than a depositional field.
Each story owns its world-unit/lattice/runtime adaptation and validation.

**Depends on:** Sprint 1 Surface/Geology family, Sprint 2 typed ports, Sprint 3 cover state, Sprint 4
physical routing, Sprint 5 wind/moisture. **Maps to** `GAEA-GAP` Surface deepening, aeolian, and
mass-movement recommendations. D7 **L2/L5**.

**Doctrine in force.** Material-moving nodes co-update state in the same pass; repose is degrees and
depth is metres. Surface detail may modify height but must not masquerade as conserved transport.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S7.1 | Strata/Lithology + Stratify | `[K]` | 8 | stratigraphic coordinate, localized beds, hardness/erodibility state |
| S7.2 | Sandstone + Outcrops/Rockscape | `[K]` | 5 | surface expressions driven by exposed strata, slope, soil cover, fracture |
| S7.3 | Aeolian: DuneSea + Sand transport/detail | `[K]` | 8 | reference-informed port; wind/moisture; co-update sandDepth |
| S7.4 | Scree/talus transport | `[K]` | 5 | source-to-apron volume closure; distinguishable sediment state |
| S7.5 | Debris runout | `[K]` | 5 | Voellmy reach + new deposition law; not merely a path renderer |

---

### S7.1 — Strata/Lithology + Stratify · `[K]` · 8 pts
**User story:** As a terrain author, I can define localized, folded/tilted rock beds whose resistance
changes erosion and whose exposed layers create non-global strata detail.

Use `terrain-architect/reference-impl/landforms.py::strat_coord` and `bed_erodibility` as grounded
atoms. Emit `strataHardness`/erodibility with explicit convention and unit; sample the exposed bed as
height crosses strata. Stratify uses localized zones and nonlinear coordinates, not a global terrace.
Feed hardness to a differential-erosion consumer in the same sprint so the field is not decorative.

**Acceptance gate** — `tests/legacy/_verify_stratify.js`: two zones with different bed phase produce
intentional discontinuity while each zone follows its analytic coordinate; a global terrace fixture
fails. Hard/soft alternating beds under the same erosion forcing show lower incision in hard beds and
the sign/convention matches the manifest. Changing resolution on one world does not move bed
boundaries beyond one coarse cell.

---

### S7.2 — Sandstone + Outcrops/Rockscape · `[K]` · 5 pts
**User story:** As a terrain author, I can expose bedded rock where cover is thin and break it into
credible outcrops without manually combining half a dozen masks.

Build Surface/Geology expressions from exposed strata, slope/curvature, `soilDepth`, and Rock
Fracture. Sandstone adds bed-controlled face detail; Outcrops/Rockscape expose and break rock only
where cover and slope permit. They do not create or destroy conserved sediment unless explicitly
paired with a transport output.

**Acceptance gate** — `tests/legacy/_verify_outcrops.js`: zero exposure or positive soil cover above
the declared cutoff gives bit-identical input; exposed steep hard beds receive finite localized
detail; inverting hardness/cover moves the detail to the analytic complementary region. World-space
wavelength is resolution-consistent on square and hex. Capture close and traversal hillshades.

---

### S7.3 — Aeolian: DuneSea + Sand · `[K]` · 8 pts
**User story:** As a terrain author, I can evolve an arid sand layer with the same physical Wind and
Moisture fields used elsewhere, producing a base dune field and surface-scale ripples.

Use `reference-impl/dunes.py` and `aeolian.py` as reference behavior, then adapt seed contract,
physical slab/depth units, boundary policy, square/hex neighbours, performance, and typed state.
`DuneSea` is the transport/base mode; `Sand` is the finer surface mode. Wind drives transport;
moisture gates it; both co-update `sandDepth` and solid top. The first shipped style is **transverse**
so crest-orientation oracles are unambiguous.

**Acceptance gate** — `tests/legacy/_verify_aeolian.js`: below threshold shear or fully wet bed is
bit-identical; above threshold a transverse crest's dominant orientation is perpendicular to wind
within one orientation-analysis bin, and rotating wind 90° rotates it by 90° ± one bin. Total sand
volume closes using lattice cell area; source/sink boundary flux is explicit. Resolution consistency
and square/hex legal-neighbour checks are armed before visual review.

---

### S7.4 — Scree/talus transport · `[K]` · 5 pts
**User story:** As a terrain author, loose fragments leave over-steep faces and accumulate as a
separate talus apron at their base.

Implement repose-driven source removal and downslope deposition, emitting/co-updating
`sedimentDepth`. This is not just Thermal renamed: the output layer and apron are first-class and
selectable. Use legal lattice neighbours and metres/degrees.

**Acceptance gate** — `tests/legacy/_verify_scree.js`: below-repose fixture is identity; above-repose
cliff loses source volume and gains the same apron volume (plus declared boundary export), with apron
centroid downslope and final active face at the authored repose angle within one lattice angular
quantum. Run square/hex and reject illegal-neighbour transport.

---

### S7.5 — Debris runout · `[K]` · 5 pts
**User story:** As a terrain author, a failed mass follows a physically bounded runout path and leaves
an explicit deposit rather than a decorative trace.

Use `reference-impl/runout.py::voellmy_runout` for path/reach behavior. Add and document a deposition
law, source volume, width/spreading rule, and boundary export; the reference path alone is not a
production node. Emit final height and sediment state together.

**Acceptance gate** — `tests/legacy/_verify_debris_runout.js`: in the pure-Coulomb limit, horizontal
reach satisfies `D = H / mu` under the existing reference tolerance; increasing turbulent drag
shortens reach monotonically. Removed source volume equals deposited plus boundary-export volume, and
deposits lie on/around the routed track rather than at a terminal pixel. Same seed is deterministic;
square/hex use legal neighbours.

---

## Sprint 7 exit gate

- Strata, outcrop, aeolian, scree, and debris oracles are green with armed failing fixtures and fixed
  pre-implementation thresholds.
- Sand/sediment volume closure holds with lattice cell area; no co-evolution exemption is added.
- Visual evidence covers two zoom levels and both lattices; numeric oracles remain the gate.
- Production build, built-bundle digest, and full sweep are green; digest skipped = 0.
