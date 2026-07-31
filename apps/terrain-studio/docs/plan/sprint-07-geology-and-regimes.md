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
| S7.5 | Debris runout path / reach | `[K]` | 5 | grounded Voellmy trajectory, speed and stop; deposition deferred |

---

## Technical refinement

### Locked geology and transport contract

- Strata use the chapter-11 stratigraphic coordinate
  `s = height + dot(tilt, worldXY) + fold + world-space warp`. Beds come from a non-uniform authored
  thickness table; a uniform sine/modulo stack is only the armed fake-terrace control.
  Emit positive dimensionless `strataErodibilityFactor` from the authored bed table. ADR 005's
  Stream Power/2 multiplies its physical `K0` by this factor; low factors resist and high factors
  erode faster. Do not normalize or invert it into ambiguous “hardness.” The bed
  table/coordinate are state; the exposed-surface slice co-updates when erosion reveals another bed.
- Stratify zones are explicit masks with stable priority. Each contact is either `hard` (fault/contact,
  zero blend) or `feathered` with an authored width in metres; there is no cell-sized production
  default. Outcrop expressions read erodibility, cover depth, slope/curvature, and fracture; they do
  not create conserved material.
- `DuneSea` uses the Werner slab/shadow/avalanche model for transverse organization. `Sand` uses the
  thresholded continuum Bagnold/Exner transport for finer response to the typed wind field. Boundary
  policy is required authored data: `periodic` reproduces the reference Werner/Exner fixtures;
  `open` reports source/outflow flux. There is no hidden production default. Wind direction is never
  quantized to lattice directions in the continuum branch.
- Aeolian transport is exactly zero below threshold or on fully immobilized wet/crusted cover.
  Moisture is an availability gate, not a multiplier that lets wet sand creep. Sand moves only from
  `sandDepth`; bedrock is not excavated by this first model.
- Scree consumes an explicit `weatheredRockDepth:m` source field. Following chapter 05, it gates the
  source by exposed cliff area (`slope > 55°`), dilates source to the cliff base in an authored metre
  radius, then relaxes that material at an authored scree repose angle in the cited 35–40° range.
  No source is exact identity; the node does not invent a weathering-rate law.
- Debris runout uses only the grounded chapter-05 / `reference-impl/runout.py` Voellmy path. It emits
  a feature set carrying the ordered world-space path, speed per sample, stop point, horizontal reach,
  and boundary-exit status. It does not write height or claim a deposition field. Lobate/depth-averaged
  deposition remains a named follow-up because the corpus marks the single-path terrain realization
  F-tier and supplies no defensible spreading/deposition law.

### Owning code surfaces and cut order

1. **R0:** execute every named reference symbol/test, freeze both-lattice fixtures, and record the
   S3 transport classification. Missing or square-only reference behavior is a planned adaptation,
   not assumed production support.
2. **S7.1:** implement bed table/coordinate and `strataErodibilityFactor`, then connect it to Stream
   Power in a separate cut. Do not begin outcrop expressions until differential incision is proven.
3. **S7.2:** add pure Surface/Geology expressions and close zero-exposure/covered identity first.
4. **S7.3:** land Werner and continuum modes separately against their own controls; combine only
   through explicit `sandDepth` state after each closes mass independently.
5. **S7.4–S7.5:** implement explicit-source scree transport and Voellmy path/reach separately; port
  each to D6 after the square analytic oracle is armed.

### Verification matrix and Ready condition

| Invariant | Passing endpoint | Mutation that must be red |
|---|---|---|
| Material convention | lower authored `K` incises less under equal forcing | normalized/inverted hardness |
| Real strata | non-uniform tilted/folded beds move <= one coarse cell | global terrace/modulo fixture |
| Aeolian threshold | below threshold/wet bed is exact identity | soft non-zero threshold ramp |
| Sand/scree mass | source = deposit + named boundary flux | hidden wrap or square area on hex |
| Runout physics | Coulomb reach, drag monotonicity, ordered legal path | stop-on-flat/terminal deposit claim |

Sprint 7 is Ready when S1–S5 exit, every reference symbol named above executes, the Stream Power
`K` integration is assigned to S7.1, and all boundary/source conventions are present in the
armed fixtures. It may run parallel to S6 after those prerequisites.

---

### S7.1 — Strata/Lithology + Stratify · `[K]` · 8 pts
**User story:** As a terrain author, I can define localized, folded/tilted rock beds whose resistance
changes erosion and whose exposed layers create non-global strata detail.

Use `terrain-architect/reference-impl/landforms.py::strat_coord` and `bed_erodibility` as grounded
atoms. Emit `strataErodibilityFactor:ratio` without inversion; sample the exposed bed as height
crosses strata. Stratify uses localized zones and nonlinear coordinates, not a global terrace. Feed
the factor to Stream Power/2 in the same story so the field is not decorative.

**Acceptance gate** — `tests/legacy/_verify_stratify.js`: two zones with different bed phase produce
intentional discontinuity while each zone follows its analytic coordinate; a global terrace fixture
fails. Beds with lower `K` under the same erosion forcing show lower incision and the direct
erodibility convention matches the manifest. Changing resolution on one world does not move bed
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
detail; exchanging high/low erodibility or cover moves detail to the analytic complementary region. World-space
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
bit-identical; above threshold a transverse crest's axial orientation, measured in 180 one-degree
bins over `[0°,180°)`, is perpendicular to wind within one bin, and rotating wind 90° rotates it by
90° ± one bin. Total sand
volume closes using lattice cell area; source/sink boundary flux is explicit. Resolution consistency
and square/hex legal-neighbour checks are armed before visual review.

---

### S7.4 — Scree/talus transport · `[K]` · 5 pts
**User story:** As a terrain author, loose fragments leave over-steep faces and accumulate as a
separate talus apron at their base.

Consume an explicit weathered-rock thickness, place it at the exposed cliff base, and relax it
downslope into `sedimentDepth`. This is not Thermal renamed: the source field and apron state are
first-class and selectable. Use legal lattice neighbours and metres/degrees.

**Acceptance gate** — `tests/legacy/_verify_scree.js`: disconnected/zero source is identity; an
exposed-cliff source loses source volume and gains the same apron volume (plus declared boundary export), with apron
centroid downslope and final active face at the authored repose angle within one lattice angular
quantum. Run square/hex and reject illegal-neighbour transport.

---

### S7.5 — Debris runout path / reach · `[K]` · 5 pts
**User story:** As a terrain author, I can route a failed mass along a physically bounded trajectory
and export its path, speed, stop, and reach without pretending a one-path model predicts deposition.

Use `reference-impl/runout.py::voellmy_runout` for path/reach behavior. Emit a typed feature set and
pass solid height through unchanged. Deposition is deliberately deferred to a future depth-averaged
or independently grounded lobe model.

**Acceptance gate** — `tests/legacy/_verify_debris_runout.js`: in the pure-Coulomb limit, horizontal
reach satisfies `D = H / mu` with strict error `< 2 * cellSize`, matching
`reference-impl/tests/test_runout.py`; increasing turbulent drag shortens reach monotonically. On a
flat with initial speed, stop distance matches `v0²/(2*mu*g)` under the same strict bound. Height is
bit-identical, path samples are adjacent legal neighbours, and a terminal-pixel deposit mutation fails.

---

## Sprint 7 exit gate

- Strata, outcrop, aeolian, scree, and debris oracles are green with armed failing fixtures and fixed
  pre-implementation thresholds.
- Sand/sediment volume closure holds with lattice cell area; no co-evolution exemption is added.
- Visual evidence covers two zoom levels and both lattices; numeric oracles remain the gate.
- Production build, built-bundle digest, and full sweep are green; digest skipped = 0.
