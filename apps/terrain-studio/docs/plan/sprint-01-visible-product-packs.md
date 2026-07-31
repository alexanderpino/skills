# Sprint 1 — Visible-product packs `[C]`

**Goal.** Close the widest *visible* gap — Gaea output reads as finished, ours does not — without
changing the graph value contract. These stories may add local numerical routines, but every output
remains one scalar raster. It is Track A: parallelisable, blocks nothing, blocked by nothing.

**Maps to** `GAEA-GAP.md` Part 3 items **#1 (surface pack)**, **#2 (landform pack)**, **#3 (filter
completion)**, and the cheapest scalar derive.

**Doctrine in force.** Guardrail 7 (new `gen` nodes join the transform-commutes table). Surface nodes
are L5 dressing and stay out of any export profile (guardrail 2). Blur-derived filters inherit the
hex-native blur that already landed (`_verify_blur_isotropy.js` hex 1.0000; `BACKLOG W1`), so they do
not reintroduce the square-separable defect `C4`.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S1.0 | Add the Surface/Geology palette family; move Rock Fracture | `[C]` | 2 | **DONE** · `da2e583`; focused/built gates green |
| S1.1 | Surface-detail node (one plugin, `style` enum) | `[C]` | 5 | Roughen, Distress, GroundTexture, RockNoise, Bulbous, Pockmarks, Contours, Grid |
| S1.2 | Landform pack: Crater, CraterField, Island, Volcano, MountainSide, Rugged | `[C]` | 8 | six plugin types; radial SDF + profile + noise/scatter |
| S1.3 | Tone/morphology filters | `[C]` | 5 | Sharpen, Threshold, Dilate, Deflate, Match, SoftClip |
| S1.4 | Coordinate filters | `[C]` | 5 | Flip, Transpose, Fold, DirectionalWarp; lattice-aware semantics |
| S1.5 | Derive: Angle (aspect) | `[C]` | 2 | scalar field; Normals moves to Sprint 2 typed ports |

---

## Technical refinement

### Locked decisions

- Packaging is fixed at **18 new plugin types**: Surface Detail (1), landforms (6), filters (6),
  coordinate filters (4), and Aspect (1). S1.0 is a reclassification, not a new type. The exit count
  is still measured baseline + 18 rather than a hard-coded absolute total.
- Surface Detail is one plugin with eight styles. Style changes select an implementation strategy;
  they do not change the port contract. All wavelength/radius parameters are metres and all random
  styles derive their seed from `(rootSeed, nodeId, style)`.
- Coordinate operations are world transforms about the square world-extent centre. `Flip` reflects
  x or y; `Transpose` applies `(x,y) -> (y,x)`; `Fold` reflects one half-space onto the other about an
  authored world-space axis; `DirectionalWarp` offsets world coordinates along an authored bearing
  by a scalar field measured in metres. Square and hex both resample through the lattice sampler.
  Hex Transpose is therefore supported; a raw odd-row array transpose is never a valid path.
- `EXACT_TYPES` eligibility is decided per generator before registration. Crater, Island, and
  Volcano are eligible only if their evaluators are pure world-coordinate functions. CraterField,
  MountainSide, and Rugged default to raster evaluation because placement/global normalization does
  not commute with Transform. An implementation may promote one only by passing the existing
  non-integer transform oracle.
- Reference fixtures use the measured shipped convention: `terrainDef.scale = 5000 m` (the digest
  and more than a dozen focused oracles), 128 and 256 columns, both lattices, and deterministic seed
  `7` (the existing generator/oracle convention). Position-pure generators sample beyond the authored
  rectangle in world space; neighbourhood filters declare their own support/boundary policy. Review
  captures use the same world at traversal and close zoom.

### Implementation surfaces and cut order

1. **R0:** record plugin count, category membership, `EXACT_TYPES`, focused digest, and reference-
   implementation availability. Missing reference symbols fail the baseline.
2. **S1.0:** update category metadata/styling and Rock Fracture registration; run the category and
   digest gates before adding behavior.
3. **S1.1–S1.2:** add plugins under `src/plugins/surface/` and `src/plugins/gen/`; keep reusable
   world-space profile/scatter routines in `src/core/` only when two plugins actually share them.
4. **S1.3–S1.5:** add filter/derive plugins and update `EXACT_TYPES` in `src/legacy.js`; wire toolbox,
   quick-create, source-shape checks, and plugin indexes in the same slice as each type.
5. Add one focused oracle per story, then run the digest after each plugin pin so a drift bisects to
   one type rather than the whole pack.

### Verification matrix and Ready condition

| Risk | Passing endpoint | Mutation that must be red |
|---|---|---|
| Cell-space scale | dominant wavelength/radius stable across 128/256 | parameters interpreted as cells |
| Mask leakage | zero-mask samples are bit-identical; sampled style formula matches direct oracle | apply detail before the mask |
| Fake landform mass | crater floor/rim/ejecta and saturated scatter status | cone-only or silent under-fill |
| Hex coordinate shear | analytic centroid/gradient reaches world target | raw odd-row transpose |
| Circular aspect | modal/circular azimuth within one lattice quantum | arithmetic mean across north |

Sprint 1 is Ready when R0 has recorded the measured baseline and each reference symbol used by the
fixtures executes. It has no architecture dependency.

---

### S1.0 — Surface/Geology palette family · `[C]` · 2 pts
**User story:** As a terrain author, I can find surface processes separately from material-transport
simulations, so node placement communicates what the process does.

Add a first-class `surface` category to the category table, toolbox, search, styling, quick-create,
and source-text checks. Reclassify **Rock Fracture** from Erosion to Surface/Geology. Thermal stays
under Erosion because it transports material. This must land before the first surface-detail node;
do not create a temporary category and migrate it later.

**Acceptance gate** — `tests/legacy/_verify_surface_family.js`: assert the toolbox exposes the new
family and contains Rock Fracture; assert Thermal remains under Erosion; assert quick-create can find
compatible Surface nodes. The evaluator digest for Rock Fracture and Thermal must remain unchanged.
The armed control is a fixture category table with Rock Fracture left under Erosion, which must fail.

---

### S1.1 — Surface-detail node · `[C]` · 5 pts
**Maps to:** Gaea Surface family (21 nodes → 1). `GAEA-GAP §Part 3 #1`. D7 **L5**.

**User story:** As a terrain author, I can add process-aware finish detail without assembling the
same slope/curvature/noise chain repeatedly.

Build **one** `surface` plugin with a `style` enum (the pattern `mountain` already uses: many
landforms in one node). Cover Roughen, Distress, GroundTexture, RockNoise, Bulbous, Pockmarks,
Contours, Grid. Each style is masked high-frequency detail driven by fields we already emit
(`d_slope`, `d_curvature`, `d_wear`, `d_occlusion`) composited through `stampn` / mask apply. Do not
build 18 nodes.

**Acceptance gate** — new oracle `tests/legacy/_verify_surface.js`:
- **Negative control (must be seen to fail):** with `amount = 0` the output must equal the input
  bit-for-bit. With `amount > 0` on a deliberately smooth dome, every sample whose driver mask is
  exactly zero remains bit-identical. At fixed interior sample points, each style matches its direct
  scalar composition oracle within the Float32 forward-error bound for that formula and at least one
  non-zero-mask sample differs from input. Invert the mask and assert the sampled regions exchange
  roles.
- Assert finite output and seed determinism (same seed → bit-identical). For each world-frequency
  style, the measured dominant wavelength at 128² and 256² must differ by no more than one 128² cell
  on the same 5 km domain; this detects cell-space parameters without guessing an RMS tolerance.

---

### S1.2 — Landform pack · `[C]` · 8 pts
**Maps to:** Gaea Terrain family. `GAEA-GAP §Part 3 #2`. D7 **L0** (gen).

**User story:** As a terrain author, I can start from recognizable impact, volcanic, island, and
single-flank landforms instead of reconstructing each archetype from low-level nodes.

Six archetypes as compositions: `Crater` (radial profile through `shape` + `curve` + `stampn`),
`CraterField` (Poisson-disc scatter of Crater), `Island` (radial falloff × existing noise), `Volcano`
(cone + crater + flank noise — "central cone and crater structure"), `MountainSide` (`mountain` + a
directional gradient mask), `Rugged` (broken non-hero base). Reference profiles exist in
`terrain-architect/reference-impl/crater.py`.

**Guardrail 7 is a hard sub-task:** classify each new type against `EXACT_TYPES` in `src/legacy.js`.
Add only position-pure generators; deliberately exclude whole-field/self-normalising compositions
such as MountainSide if they inherit Mountain's non-commuting behavior.

**Acceptance gate** — `tests/legacy/_verify_landforms.js`:
- **Crater rim/floor profile:** on a flat base, assert the radial profile has a floor below datum, a
  rim above it, and ejecta decaying outside the rim — assert the three regions by radius, not just
  "output changed". Negative control: `amount = 0` returns the flat base exactly.
- **CraterField placement:** test the seeded placement planner directly. In a feasible case it must
  return the requested count and measured minimum spacing; in an overfull case it must return an
  explicit saturation result rather than silently placing fewer craters. Do not infer authored count
  from local minima, because overlap and flat floors make that observable unstable.
- **Transform eligibility:** assert every type declares an eligibility decision. For eligible types,
  a non-integer Transform matches direct coordinate evaluation under the existing transform oracle;
  excluded types must take the measured raster path and never claim exact evaluation.

---

### S1.3 — Tone/morphology filters · `[C]` · 5 pts
**Maps to:** Gaea Modify family (41 → 11). `GAEA-GAP §Part 3 #3`. D7 **L0**.

**User story:** As a terrain author, I can clean, select, and reshape scalar fields with standard
operations instead of routing through approximate combinations.

`Sharpen` = `in − blur(in)` (reuse `blurField`); `Threshold` (genuinely missing — `clampn` clips, it
does not threshold); `Dilate`/`Deflate` (reuse the morphological closing already inside `d_deposits`);
`Match` (histogram match, rides `histEqualizeField`); `SoftClip`.

**Acceptance gate** — `tests/legacy/_verify_filters_pack.js`, one armed control per node:
- `Threshold`: assert output is two-valued at the cut and that moving the cut moves the boundary by
  the predicted pixel count. Negative control: a cut below the field minimum yields all-high; above
  the maximum yields all-low — assert both, since a no-op threshold would pass a lazy test.
- `Sharpen`: assert edge contrast rises and a constant field matches the direct
  `input + amount * (input - blur(input))` Float32 oracle (so it sharpens edges, not noise).
  `Dilate`/`Deflate`: assert a known disc grows/shrinks by the structuring radius.
- `Match`: independently stable-sort source samples, assign each rank the corresponding sorted target
  quantile, and compare production output sample-for-sample to that rank oracle. A 256-level fixture
  with equal multiplicities must reproduce target bin counts exactly; matching a field to itself is
  bit-identical. Four moments or a bin-count-derived universal CDF tolerance are not sufficient.
- Morphology radius is authored in metres. On an analytic disc, square and hex physical growth must
  each be within one cell of the requested radius. Hex branch present for every blur/morphology node
  (guardrail: inherit W1, do not reintroduce `C4`).

---

### S1.4 — Coordinate filters · `[C]` · 5 pts
**Maps to:** Gaea Modify family. `GAEA-GAP §Part 3 #3`. D7 **L0**.

**User story:** As a terrain author, I can orient and deform fields predictably on either lattice.

Add `Flip`, `Transpose`, `Fold`, and `DirectionalWarp`. A raw array transpose is not a valid hex
transpose: define these in world space and resample through the lattice sampler using the locked
semantics above.

**Acceptance gate** — `tests/legacy/_verify_coordinate_filters.js`: evaluate analytic x/y ramps and
a centred impulse. Assert each operation moves their world-space centroid and gradient to the
analytic location on square and hex. Applying Flip twice must recover the source bit-for-bit where it
is index-exact. Bilinear affine-ramp samples use the direct interpolation formula and its Float32
forward-error bound; impulse-centroid localization is at most one destination cell. A raw odd-r
array transpose is the armed failing fixture.

---

### S1.5 — Aspect derive · `[C]` · 2 pts
**Maps to:** Gaea `Angle`. `GAEA-GAP §Part 3 ranked-below-top-8`. D7 **derived**.

**User story:** As a terrain author, I can route aspect as a physical scalar field for insolation,
snow, and vegetation decisions.

Aspect (compass direction of steepest descent) is a pure function of final geometry → **derived**
lens, recomputed never carried. Normals require a vector-raster port and move to Sprint 2; do not
smuggle them through node-instance side state.

**Acceptance gate** — `tests/legacy/_verify_aspect.js`:
- **Aspect:** on an analytic tilted plane facing a known azimuth, assert the modal aspect equals that
  azimuth within one lattice quantum; assert circular statistics (aspect is periodic — a naïve mean
  would fail on a north-facing slope straddling 0°/360°, which is the negative control).

---

## Sprint 1 exit gate

- `node scripts/sweep-oracles.mjs` green including the focused oracles above.
- Measure plugin count at sprint start. With the packaging above the target is **baseline + 18
  plugin types**; any packaging change updates this arithmetic before implementation. Pin each new
  node only after its behavioral oracle is green.
- Each new oracle's closing note records the measured failing endpoint and the measured passing
  endpoint (Definition of Done). No report-only probe is accepted.
