# Sprint 3 — Cover layer (L2): soil / sediment / sand as **state** `[K]`+`[E]`

**Goal.** Make solid cover an explicit layer stack instead of a prediction. Hydraulic Pipe/Droplet
currently compute transport state and a ledger but expose only final height (`C2`, `C3`);
`d_deposits` is a morphological prediction; the shipping Weathering node is colour-only. This sprint
adds real regolith production, cover-aware transport, and explicit state outputs wired through Sprint
2 typed ports.

**Depends on:** Sprint 2 (multi-output ports + registry). **Implements:** D7 **L2**, closes `C2`,
`C3`. **Maps to** Gaea `Sediments` (Simulate) / `Soil` (Derive), which `GAEA-GAP §4.4` says to build
as **state, not a look-alike derived mask**.

**Doctrine in force.** Guardrail 4 (co-evolution): building a Gaea-shaped *derived* `Soil` node would
make the app look like it has soil while the accounting stays discarded — do it only as state, with a
lens. Guardrail 5: these are **state** lens (carried, co-updated), distinct from the **continued**
snow/water maps.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S3.1 | Hydraulic state outputs on CPU/GPU | `[E]` | 8 | Pipe/Droplet only; MRT/readback; height + sediment/deposition + physical velocity where defined |
| S3.2 | Regolith producer: `soilDepth` state | `[K]` | 5 | new physical node; do not reuse colour-only Weathering |
| S3.3 | Cover-aware hydraulic consumption/deposition | `[K]`+`[E]` | 8 | explicit soil/sediment inputs; cover before bedrock; co-update in-pass |
| S3.4 | Explicit state selectors + `d_deposits` prediction fallback | `[C]` | 3 | typed wires, never graph-global hidden lookup |
| S3.5 | Existing transport-node co-evolution | `[E]` | 8 | Thermal, Stream Power, Erosion 2, HydroFix; remove every transport exemption |

---

## Technical refinement

### Locked physical and data contract

- The solid stack is `solidTopM = bedrockHeightM + soilDepthM + sedimentDepthM + sandDepthM`.
  [ADR 005](../adr-005-physical-fields-and-climate-migration.md) keeps legacy terrain typed as
  `heightNormalized` and requires the explicit measured-frame adapter before a physical node. Cover
  fields are finite/non-negative; absolute bedrock elevation is finite and unbounded.
- Regolith production uses the Heimsath et al. 1997 law from reference chapter 11:
  `P(H) = P0 * exp(-H / hStar)`. Author `P0` in mm/yr, `hStar` in metres, and duration in years;
  hard ranges are the cited `P0 = 0.05–0.3 mm/yr` and `hStar = 0.3–0.5 m`. Initial values are
  transparently derived from those ranges: `P0 = sqrt(0.05 * 0.3) = 0.122474... mm/yr` (geometric
  midpoint for a rate) and `hStar = 0.4 m` (arithmetic midpoint). Duration is required authored data
  with no production default. The analytic update cannot produce negative depth. Climate modulation
  is an optional dimensionless multiplier, not a hidden required model.
- Hydraulic receives explicit cover plus precipitation. Until S5.2, old documents migrate their
  existing rainfall parameter to an explicit uniform-raster compatibility source owned by S5; no
  solver invents rainfall when the input is disconnected.
- ADR 002 preserves one GPU synchronization point. Height-only demand keeps ADR 001's current RGBA
  readback. State demand uses the accepted two-texel-per-cell `RGBA32F` atlas for `solidTop`,
  `soilDepth`, `sedimentDepth`, and Pipe velocity x/y. Droplet action channels distinguish erosion
  from capacity-driven deposition; unresolved terminal load remains `exportedOrSuspended`. No cell
  velocity is claimed for droplets.
- Transport accounting uses physical volume. Each process reports consumed cover, bedrock detached,
  deposited cover, and named boundary/exported/suspended loss. Effect masks and process masks remain
  distinct; the transport stories use process semantics inside the solve.

### Owning code surfaces and cut order

1. **R0:** freeze the S2 adapter/exemption ledger and enumerate every registered height writer as
   generator, surface expression, or material transport. Resolve disputes before implementation.
2. **S3.1:** extend `src/plugins/ero/hydraulic.js`, CPU hydraulic routines in `src/legacy.js`, and
  GPU kernels/wrappers in `src/core/gpu.js`; land the ADR 002 atlas and state oracle before cover-aware
   behavior changes primary height.
3. **S3.2:** add the Regolith producer and reference-law fixture. Keep the preview-only
   `src/plugins/effect/weathering.js` unchanged and label the distinction in search/inspector copy.
4. **S3.3:** add typed cover/precipitation inputs and change transport order to loose cover first,
   bedrock second. Re-bless Hydraulic only after mass/stack identities pass on GPU and compatibility
   paths.
5. **S3.4–S3.5:** add explicit readers, then migrate Thermal, Stream Power, Erosion 2, and HydroFix
   one at a time, removing the corresponding exemption after each focused oracle passes.

### Verification matrix and Ready condition

| Invariant | Passing endpoint | Mutation that must be red |
|---|---|---|
| Physical mass | consumed = deposited + named loss using lattice area | square area reused on hex |
| Cover precedence | bedrock unchanged while local loose cover remains | bedrock-first kernel |
| Regolith law | analytic Heimsath depth at 0, 1, and 2 `hStar` | constant production rate |
| State locality | selectors require explicit connected ports | graph-neighbour lookup/zero fallback |
| Complete classification | every height writer has one reviewed class | pre-S3 exemption manifest |

Sprint 3 is Ready when Sprint 2 exits, the R0 transport classification has no disputed entry, and
the Heimsath analytic fixture plus hydraulic state omission mutation have both been observed red.

---

### S3.1 — Hydraulic state outputs on CPU/GPU · `[E]` · 8 pts
**Closes:** `C3` ("erosion's mass budget is computed and discarded"), `C2` (velocity discarded).

**User story:** As a terrain author, I can route deposited sediment and physical flow independently
of the final height on both the shipping GPU path and compatibility path.

The hydraulic Pipe solver owns per-cell flux and suspended sediment; the Droplet solver owns
per-particle speed/load. Stream Power is a detachment-limited incision solver and is **out of scope**:
it has no sediment-transport state to expose. Extend the hydraulic CPU and square GPU paths so one
evaluation returns final solid height, deposited `sedimentDepth` (m), and Pipe `flowVelocity` (m/s,
vector raster). If a Droplet velocity field is wanted, define a trajectory-weighted raster and its
normalisation before implementation; never label raw per-particle terminal speed as a cell field.

This is GPU work: implement ADR 002's height-only RGBA and state-demand two-texel atlas paths, each
with exactly one `readPixels` call. The digest's CPU path is not evidence for the shipping square GPU
path.

**Acceptance gate** — `tests/legacy/_verify_sediment_state.js`, extending `_verify_erosion_mass.js`:
- **Volume closure, armed:** convert every depth sum with lattice cell area (square `s²`, hex
  `sqrt(3)/2·s²`) and assert `erodedVolume = depositedVolume + exportedOrSuspendedVolume`. The
  allowed reduction error is computed, not inherited: for `N` Float32 terms, use
  `gamma_(N-1) * sum(abs(term))`, where `gamma_n = (n * 2^-24)/(1 - n * 2^-24)`. Assert integrated
  `sedimentDepth` equals the deposited ledger under the same bound. A fixture that omits the hex area
  factor must fail.
- Assert `sedimentDepth` is zero where no deposition occurred (a prediction would smear it), and that
  the map is in metres (physical units, guardrail 6).
- Same-seed repeatability is bit-identical on one device. Run the independent closure/range gates on
  the real square GPU path and CPU/hex compatibility path; do not require those distinct numerical
  implementations to produce an identical state raster.

---

### S3.2 — Regolith producer: `soilDepth` state · `[K]` · 5 pts
**User story:** As a terrain author, I can produce a physical soil/regolith thickness field that
later processes consume, independently of preview colour ageing.

Add a physical Regolith/Soil Production node. Do **not** extend the existing `weathering` plugin: it
is an `effect` node whose description and evaluator explicitly pass height through for colour ageing.
The new process emits `soilDepth` in metres under the state lens and declares the bedrock/climate
drivers it reads. Use the locked Heimsath law, ranges, derived initial values, and required duration.

**Acceptance gate** — `tests/legacy/_verify_soildepth.js`:
- Assert the analytic zero-production controls (zero duration/rate or no eligible substrate) return
  zero soil bit-for-bit; eligible stable surfaces produce finite, non-negative depth in metres.
- Resolution consistency uses the 5 km measured fixture and evaluates the analytic Heimsath formula
  independently at the same world-space samples. Production Float32 values must lie within
  `gamma_8` of the double-precision oracle; no empirical post-result tolerance is selected.

---

### S3.3 — Cover-aware hydraulic transport · `[K]`+`[E]` · 8 pts
**User story:** As a terrain author, hydraulic erosion consumes loose cover before resistant
bedrock and deposits transported material into an explicit cover layer.

Add explicit typed `soilDepth`, `sedimentDepth`, and `precipitation:mm/yr` scalar-raster inputs to
Hydraulic. A uniform fixture supplies precipitation until S5's spatial Moisture producer lands.
Co-update cover and solid height in the same CPU/GPU pass. This intentionally changes hydraulic height and therefore requires
the `C3` stated baseline re-bless after the physical oracle passes; it is not a surprise digest
regression. Remove the hydraulic co-evolution exemption from Sprint 2 here and assert the exemption
ledger shrinks.

**Acceptance gate** — `tests/legacy/_verify_cover_erosion.js`: on a two-layer analytic slope, the
first eroded volume comes from cover and bedrock remains unchanged until local cover reaches zero;
deposition increases `sedimentDepth` at transport sinks. Solid-top identity
`bedrockHeightM + soilDepthM + sedimentDepthM + sandDepthM` closes before/after with the transport
ledger; this fixture also asserts `sandDepthM == 0`. Run on square
GPU and CPU/hex compatibility paths. A kernel that erodes bedrock while cover remains is the armed
failing fixture.

---

### S3.4 — Explicit state selectors + prediction fallback · `[C]` · 3 pts
**User story:** As a graph author, I can select carried cover state explicitly and distinguish it
from a derived prediction.

Add selector/pass-through nodes for `soilDepth`, `sedimentDepth`, and the registered-but-not-yet-
produced `sandDepth`. They consume explicit typed ports; the registry is metadata, not a global store
of instance values. Keep `d_deposits` as a clearly labelled prediction, and give it an optional
explicit `Sediment state` input. When connected it returns that input; otherwise it computes the
morphological prediction. Never search the graph for a nearby state implicitly.

**Acceptance gate** — `tests/legacy/_verify_cover_reader.js`: selectors return the exact bytes on
their connected typed ports; absent required state produces a typed missing-input error. For
`d_deposits`, a connected state returns identity, no connection returns the prediction, and the
inspector says "prediction". A disconnected selector silently returning zeros must fail.

---

### S3.5 — Existing transport-node co-evolution · `[E]` · 8 pts
**User story:** As a terrain author, every existing process that claims to move material reports where
that material went and updates the cover it consumes; no legacy erosion path bypasses L2 accounting.

Audit the shipping transport nodes against the Sprint 2 manifest and remove their owned exemptions:

- **Thermal:** consume loose cover before bedrock and move the same volume into downslope
  `sedimentDepth` in the relaxation pass.
- **Stream Power:** remain detachment-limited, but consume soil before bedrock and report detached
  volume as an explicit exported/suspended ledger; do not invent deposition it does not model.
- **Erosion 2:** expose/co-update the state of the hydraulic/thermal stages it composes rather than
  re-deriving deposits from final height.
- **HydroFix:** report the low-amplitude conditioning delta and its removed/exported volume; it may
  not silently discard carved bedrock.

Surface expressions/generators (including Rock Fracture if classified as an authored surface
expression) declare that classification and are not mislabeled as material transport. Any node whose
classification remains disputed blocks L2 promotion; an exemption without a later owner is forbidden.

**Acceptance gate** — `tests/legacy/_verify_transport_coevolution.js`: enumerate every registered
height-writing plugin and assert it is classified as generator/surface expression or compliant
transport. For each transport node, run an analytic fixture and close consumed/deposited/exported
volume with lattice cell area. The pre-S3 manifests form the armed failing fixture; the final
exemption ledger contains no material-transport entry.

---

## Sprint 3 exit gate

- `_verify_sediment_state.js`, `_verify_soildepth.js`, `_verify_cover_reader.js`,
  `_verify_cover_erosion.js` green, each with a demonstrated failing fixture.
- `_verify_erosion_mass.js` closes physical volume on GPU and compatibility paths and now covers the
  state map. The intentional Hydraulic result change is reviewed and re-blessed only after this gate.
- Hydraulic's co-evolution exemption is removed; no new exemption was added. Digest skips = 0.
- Thermal, Stream Power, Erosion 2, and HydroFix material-transport exemptions are removed; the
  registry enumeration proves no mover was missed.
- **D7 L2 is now verified** — the default document may promote to L2.
