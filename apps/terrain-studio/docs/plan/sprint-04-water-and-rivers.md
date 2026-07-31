# Sprint 4 — Water, rivers & AAA rendering (L3): physical fields to pixels `[K]`+`[E]`

**Goal.** Expose the complete hydrological backbone: explicit depression policy, physical routing,
authored source/guide features, lakes, rivers, and a renderer that turns those physical causes into
the supplied hero-water quality. Sources carry `discharge` and seed the same
accumulation stack as rainfall; the simulation owns water geometry. Lakes come out flat-at-spill by
construction; rivers are discharge/width/depth fields — **never an implicit carve**. The graph emits
still water datum/depth/flow/shore fields; the viewport owns animated displacement, normals, optics,
foam, and reflections under [ADR 006](../adr-006-aaa-water-rendering.md).

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
| S4.7 | Shared Gerstner wave core + displaced water mesh | `[E]` | 5 | deterministic 12-term preset; analytic derivatives; shared forward/depth positions |
| S4.8 | AAA deferred water optics and stable sun glints | `[E]` | 5 | GGX/Fresnel, Beer-Lambert, depth rejection, micro-normal variance |
| S4.9 | Shore, river, lake, ice and foam regimes | `[K]` | 3 | depth fade/shoaling; flow-advection; causal foam; phase transition |
| S4.10 | Water evidence, parity and frame-budget gate | `[E]` | 3 | analytic vectors, screenshots/pixels, forward/deferred parity, GPU timings |

---

## Technical refinement

### Locked hydrology contract

- `routingSurface` is a derived working field; `solidTop` is passed through unchanged.
  `conditioningDelta = routingSurface - solidTop`: positive means fill, negative means breach/cut.
  `depressionDepth = max(0, routingSurface - solidTop)`. Preserve mode has exact zero delta.
- Fill uses priority-flood. Breach uses the chapter-03 least-cost outlet path and lowers only the
  routing surface. Preserve routes on the original surface and emits endorheic basins explicitly.
  Equal-elevation queue/basin ties resolve by stable lattice index; basin IDs are deterministic but
  carry no physical meaning across a topology change.
- MFD8/MFD6 receiver weights remain the existing production implementation. The first-moment vector
  is normalized only where outflow exists; sinks receive `(0,0)`. Drainage area starts at physical
  cell area. Per ADR 005, distributed input converts exactly once as
  `qRainCell = precipitationMmYr * 1e-3 * cellAreaM2 / 31_536_000`; discharge adds those cells and
  authored sources already in `m3/s`.
- Source/guide features are document-owned records with stable IDs, world-metre coordinates, kind,
  discharge, optional temperature, and ordered control points. Salinity is absent from schema,
  registry, UI, and profiles for S1–S8.
- River geometry uses Leopold–Maddock downstream exponents: `width = kw * Q^0.5` and
  `waterDepth = kd * Q^0.4`, with channel-forming/bankfull `Q` in m3/s. `kw` and `kd` are authored
  coefficients with units `m/(m3/s)^0.5` and `m/(m3/s)^0.4`; the chapter-03 equations are the direct
  three-discharge oracle.
- Guide control points are two-dimensional intent; elevation comes only from sampling
  `routingSurface`. Resample each guide at spacing `ds <= 0.5 * cellSize`. The current HydroFix
  descent is `epsCell = relief / (max(resolution,2) * 160)`. For sampled elevations `z[i]`, set
  `target[0] = z[0]` and
  `target[i] = min(z[i], target[i-1] - epsCell * ds[i]/cellSize)`; then
  `deficit[i] = z[i] - target[i]`. This is non-negative cut depth in terrain-normalized height,
  converted to metres for the report. Rivers reports it and never applies it. Accepting repair creates
  one explicit, undoable conditioning branch.
- Rendering follows ADR 006. Ocean/lake water uses one deterministic 12-term Gerstner preset with
  `sum(Q_i*k_i*A_i) <= 0.85`; position and analytic derivatives come from one shared GLSL function
  used by forward color and deferred water-depth passes. Rivers use `flowVelocity:m/s` phase
  advection rather than ambient ocean displacement. No wave, normal, foam, or reflection is written
  into graph fields, collision height, or exports.
- The target-quality path keeps the current separate water mesh and fullscreen optical compositor,
  replacing normal-only motion with displaced geometry, analytic normals, footprint-faded micro
  bands, dielectric Fresnel/GGX sun glints, depth-valid refraction, Beer-Lambert thickness, and the
  shared analytic sky fallback. Shore/crest/river foam is causal and persistent, never white noise.

### Owning code surfaces and cut order

1. **R0:** record existing MFD/facet readings, verify HydroFix still uses the documented
  `relief/(resolution*160)` descent family, and run analytic basin fixtures. Verify chapter-03
  reference symbols before port work.
2. **S4.1:** implement Depression Policy and its multi-output descriptors first; prove all modes keep
   `solidTop` identical before exposing Flow.
3. **S4.2:** wrap existing routing as physical outputs and keep `d_flow` as a visualization adapter.
4. **S4.3:** land feature schema/editor/persistence independently, then connect sources to the same
   accumulation stack. Source editing and flow invalidation are one integration cut.
5. **S4.4–S4.5:** add Lake products, then river geometry. Neither story receives a height-output
   writer capability.
6. **S4.6:** add conflict analysis and branch creation after guide persistence and Depression Policy
   are stable; branch creation is a single undo record.
7. **S4.7:** extract one side-effect-free Gerstner preset/evaluation contract and one shared GLSL
  displacement include; wire identical displaced positions into water mask/depth and forward water.
8. **S4.8:** upgrade the deferred optical compositor around the displaced surface while preserving
  the terrain G-buffer, depth rejection, ACES exposure, and analytic sky fallback.
9. **S4.9:** consume physical depth/shore/flow/ice causes for body-specific amplitudes, river motion,
  causal foam, and continuous liquid-to-ice suppression.
10. **S4.10:** arm analytic, parity, pixel, screenshot, temporal and GPU-budget gates before the
   renderer stories close. A quality reduction is an explicit preset decision, never silent fallback.

### Verification matrix and Ready condition

| Invariant | Passing endpoint | Mutation that must be red |
|---|---|---|
| Policy distinction | fill, breach, preserve produce expected topology | all modes mapped to fill |
| Water cause | zero rain/source gives zero Q; source Q reaches outlet | source stamped into height |
| Flat lakes | one spill level and exact depth identity | fixed slider water level |
| No carve | every water-family solid output is bit-identical | fixture Rivers writes height |
| Guide conflict | analytic uphill deficit and explicit branch | hidden in-node correction |
| Wave math | fixed CPU/GLSL position and normal vectors; fold sum <= 0.85 | finite-difference normal or 1.05 fold preset |
| Pass parity | forward and deferred clip positions match at one preset/time | duplicate wave implementations |
| Water quality | non-empty changing water pixels, stable glint, dry pixels unchanged | normal-only datum surface |
| Regime causality | exact dry/ice displacement zero; river motion follows flow | ocean waves on rivers or random foam |
| Frame budget | ADR 006 warm 120-frame p95 limits with hardware record | unmeasured preset reduction |

Sprint 4 is Ready when S2/S3 exit, the L1 routing/facet gates are still green, and the R0 basin and
source mutations have been observed red. S5 later replaces only the production precipitation source;
these analytic fixtures remain permanent. S4.7 may begin from the existing Water mesh after ADR 006's
CPU vectors are armed; S4.9's final river regime waits for S4.2/S4.5 physical flow products.

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
precipitation fixture integrates to
`precipitationMmYr * 1e-3 * contributingAreaM2 / 31_536_000`. Mutations omitting either conversion
factor must fail. Run the existing facet and resolution gates and assert
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
  downstream equals the authored source flow and remains conserved to the outlet absent sinks. The
  Float32 accumulation bound is `gamma_(N-1) * sum(abs(sourceQ))`, with `gamma` defined in S3;
  removing the source returns exactly zero. This is stronger than an arbitrary source/no-source ratio.
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
  exact Float32 identity because every wet cell receives the same computed spill value, and assert
  that value is bit-identical to the spill feature's elevation. A version that fills to a fixed
  slider level regardless of spill is the armed failure.
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

Hydraulic geometry uses the locked Leopold–Maddock downstream exponents and authored SI coefficients
above; they are not tuned after production output is seen.

**Acceptance gate** — `tests/legacy/_verify_rivers.js`:
- Assert the terrain height output is **bit-identical** to the input (guardrail 1 — this is the
  negative control that would catch any accidental carve).
- Assert channel width/depth match the predeclared power-law oracle at three discharges and increase
  monotonically downstream. Compare to double-precision `kw*sqrt(Q)` / `kd*Q^0.4` within `gamma_8`
  for the Float32 production path; no empirical tolerance is selected.
- On an analytic Y-valley, assert the channel skeleton stays within one cell of both known thalwegs,
  joins at the analytic confluence, and reaches the outlet; a guide-only straight line must fail.

---

### S4.6 — Conflict surfacing + explicit conditioning branch · `[C]` · 3 pts
**User story:** As a terrain author, an impossible guide tells me where and by how much it conflicts,
and any terrain conditioning remains an explicit undoable choice.

An authored **river guide** whose sampled route rises relative to the recurrence above reports the
per-sample and maximum elevation deficit and offers to create an explicit Depression Policy/HydroFix
branch. The Rivers node itself never mutates height (`D5`: conflicts are surfaced, not corrected).

**Acceptance gate** — `tests/legacy/_verify_water_conflict.js`: place a guide with one analytic uphill
segment; compute the recurrence independently and assert every deficit sample and maximum exactly,
with conversion to metres. Height remains unchanged. A valid downhill guide emits zero conflict.
Accepting the offer adds a visible, undoable conditioning branch; it never turns on a hidden carve.

---

### S4.7 — Shared Gerstner wave core + displaced mesh · `[E]` · 5 pts
**User story:** As a terrain reviewer, I see coherent crests, trough parallax, and a displaced water
silhouette instead of a flat plane with animated normal noise.

Implement ADR 006's deterministic `WaterWavePreset` expansion and 12-term Gerstner position/tangent
evaluation. Keep authoring at wind direction/speed, sea state, seed, maximum amplitude, and body kind;
artists do not edit twelve arbitrary vectors. Generate one GLSL source used by the forward water
vertex path and deferred water-mask/depth path. Inflate water bounds by declared vertical amplitude
and horizontal chop; fade geometric displacement below one projected pixel.

**Acceptance gate** — `tests/legacy/_verify_gerstner.js`: zero amplitude is bit-identical to the
existing datum. Fixed `(x,z,t)` vectors match a double-precision CPU oracle for position and analytic
normal under fixed Float32 vectors. Every generated preset is deterministic and obeys
`sum(Q*k*A) <= 0.85`; sampled horizontal Jacobian is positive outside the declared foam band, and an
injected 1.05 preset fails. Shader instrumentation proves both passes use the same displacement
source, and sampled displaced vertices remain inside inflated bounds.

---

### S4.8 — AAA deferred optics and stable glints · `[E]` · 5 pts
**User story:** As a terrain reviewer, ocean and lake water have the broad/fine white glints, dark
troughs, depth color, refraction, and grazing reflection quality of the supplied reference.

Shade the exact displaced surface through ADR 006: analytic Gerstner normal plus two footprint-faded
micro-normal bands; refraction with foreground/depth rejection; Beer-Lambert absorption/scattering;
water dielectric `F0 = 0.02037`; GGX direct-sun glint; derivative-variance roughness; analytic sky
reflection fallback; common scene-linear exposure and ACES. Keep the current fullscreen compositor;
SSR remains a later interchangeable reflection source.

**Acceptance gate** — `tests/legacy/_verify_water_aaa.js`: fixed normal/view/light vectors match the
CPU GGX/Fresnel oracle. Independently derive `((1.333-1)/(1.333+1))^2 = 0.02037` before evaluating
Schlick; refracted foreground samples are rejected; optical thickness darkens
monotonically; roughness variance lowers sub-pixel glint variance against the armed no-variance
mutation. Forward fallback and deferred output remain finite, phase-correct, and nonblank.

---

### S4.9 — Shore, river, lake, ice and foam regimes · `[K]` · 3 pts
**User story:** As a terrain author, each body reads correctly: ocean swell shoals at shore, lakes
stay restrained, rivers flow downstream, rapids foam from causes, and ice suppresses liquid motion.

Consume `waterDepth`, `shoreDistance`, `flowVelocity`, gradient/constriction, and existing ice masks.
Ocean/lake displacement uses ADR 006's depth fade, bounded shoaling, and faster chop suppression near
shore. Rivers advect two phase-offset detail bands by physical flow speed and blend calm/ripple/
turbulent regimes; they do not receive ocean Gerstner displacement. Crest, shore, and rapid foam use
causal masks with temporal persistence. Liquid displacement reaches exact zero on dry and fully iced
samples.

**Acceptance gate** — `tests/legacy/_verify_water_regimes.js`: analytic beach amplitude/chop reach
zero before land intersection; lake amplitude is lower than the same ocean preset; reversing a river
flow field reverses phase travel; zero speed removes rapid foam; constriction/gradient increases it;
ice 0→1 suppresses displacement continuously and exactly at 1. Random-noise foam and ocean-wave river
fixtures are armed failures.

---

### S4.10 — Water evidence, parity and frame budget · `[E]` · 3 pts
**User story:** As a maintainer, the AAA quality claim is reproducible rather than a favorable
screenshot.

Add Playwright captures and GPU timing instrumentation for the ADR 006 view envelope: overhead
sun-glint matching the supplied reference, grazing reflection, shore, lake, fast river, and ice
transition at 1440×900 and 390×844. Record hardware/browser and 120 warmed frames.

**Acceptance gate** — `tests/e2e/water-aaa.spec.ts` plus focused legacy oracle: canvas/water pixels
are nonblank, finite, and change under time advance while dry terrain pixels remain identical; no UI
overlap occurs; forward/deferred displaced clip positions match; same preset/time is bit-identical;
the sampled 60-second path has no reset pulse. Deferred water is `<= 2.0 ms` p95 and forward fallback
`<= 2.5 ms` p95 on the recorded project capture machine. A miss blocks closure or requires a named
lower preset through a superseding decision.

---

## Sprint 4 exit gate

- Depression-policy, physical-flow, source/guide, lake, river, and conflict oracles are green, each
  with a demonstrated failing fixture.
- **Guardrail 1 regression fence:** a repo-wide assertion that no water-family node writes `height`
  (only `hydrofix` may) — armed by a fixture node that carves, which must fail.
- Feature serialization/migration and typed wiring gates are green; digest skips = 0.
- Gerstner, AAA optics, body-regime, visual/pixel, parity, temporal and timing gates are green; the
  supplied-reference overhead glint capture is retained as review evidence.
- Digest bit-identical for pre-existing nodes; new types green. **D7 L3 verified.**
