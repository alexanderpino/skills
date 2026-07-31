# Terrain Studio sprint grounding ledger

**Status:** candidate — independent review pending  
**Audit:** Mission Control `INV-SPRINT-GROUNDING`  
**Rule:** a claim is grounded only by exact corpus/reference behavior, measured current source/test
evidence, transparent derivation, or an accepted ADR with options and measurable consequences.
Future implementation, R0 measurement, or a planned mutation is not current provenance.

This ledger covers the technical claims that control implementation. Story outcomes and dependency
order come from `GAEA-GAP.md`, `BACKLOG.md`, and the sprint map; they do not establish physical
constants or runtime schemas by themselves.

## Evidence classes

| Code | Meaning |
|---|---|
| `C` | Terrain Architect corpus or runnable reference implementation |
| `M` | Measured current Terrain Studio source/test behavior |
| `D` | Transparent mathematical/units derivation from cited inputs |
| `A` | Accepted architecture decision with alternatives and measurable consequences |

## Shared contracts

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Working baseline is 61 plugins and digest must skip zero | M | `PROGRESS.md`; `src/plugins/**/*.js`; `_verify_digest.js` | Counts remain measured at kickoff, never hard-coded from old 60-node prose. |
| Square world uses equilateral hex deployment and physical units | C/M | `BACKLOG.md` D1–D2; chapters 26 and 08; current lattice helpers | Preserved in every sprint fixture. |
| Nodes are pure, typed, demand-driven field transforms | C/A | chapter 14; `adr-002-typed-multi-output-dag.md` | Exact Terrain Studio schema is ADR 002, not inferred from doctrine. |
| Export is pure declaration plus explicit side-effect executor | C/A | chapters 08/14; `adr-003-pure-export-emitter.md` | Exact request/package/schema boundary is ADR 003. |
| Variables, expressions, and subgraphs are bounded and pinned | C/A | chapter 14; `adr-004-graph-machinery.md` | Exact scope/parser/hash/import policy is ADR 004. |
| Physical fields and legacy climate/Snow migration | C/M/A | chapters 03/04/13/27; current source; `adr-005-physical-fields-and-climate-migration.md` | Exact unit bridges and version boundaries are ADR 005. |
| Dynamic water rendering remains renderer-owned | C/M/A | Terrain Architect water boundary; installed Terrain Renderer chapter 12; current water shaders; ADR 006 | Graph exports causes; viewport owns waves, optics, foam and reflection. |
| Continued state requires authored epoch and drivers | C | chapter 27; `BACKLOG.md` auxiliary-map lenses | Missing epoch/drivers blocks export; no epoch is fabricated. |
| Every numerical gate is analytic, cited, or measured red/green | M | `CLAUDE.md`; `BACKLOG.md` verification lessons | Generic “existing tolerance” and post-result thresholds are forbidden. |

## Sprint 1 — visible product packs

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Package adds 18 types | D | Story table: 1 surface + 6 landform + 6 filter + 4 coordinate + 1 aspect | S1.0 is reclassification, not a type. Exit count is measured baseline + 18. |
| Fixture world is 5 km at 128/256 with seed 7 | M | `src/legacy.js` terrain default; `_verify_digest.js`; existing generator oracles | Reuses shipped scale and deterministic test seed; no invented `0x51a7`. |
| Spatial controls are metres and noise is world-space | C | chapters 01, 10, 14; SKILL evaluation invariants | Cell-space mutation is the red control. |
| Surface styles are one explicit product composition, not claimed Gaea internals | C/D | `GAEA-GAP.md` marks branded internals unverified; chapters 01/06/10 provide atoms | Each style is verified against its documented direct scalar composition. |
| Crater profile and seeded placement use grounded atoms | C | `reference-impl/crater.py`; chapter 07 Poisson/blue-noise placement | Floor/rim/ejecta and saturation status are direct oracles. |
| Transform eligibility is behavioral | M/C | current `EXACT_TYPES`, `evalExact`, `_verify_exact_transform.js`; chapter 14 resolution invariants | Whole-field/self-normalizing nodes remain raster unless the exact oracle passes. |
| Histogram Match oracle | D | Stable rank-to-target-quantile mapping | Compare sample-for-sample to independent rank oracle; equal-multiplicity 256-level fixture reproduces counts exactly. |
| Resampled coordinate localization | D | Bilinear affine interpolation and destination sample spacing | Affine ramps use Float32 forward error; impulse centroid is within one destination cell. |
| Aspect uses circular statistics | C | chapter 06 analysis masks | Arithmetic mean across north is the red control. |

## Sprint 2 — typed multi-output DAG

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Port kinds, IDs, result Map, v2 edges and migration | A | ADR 002 | Closed five-kind set; new kinds require a later ADR/version. |
| Per-output demand and atomic groups | C/A | chapter 14 evaluation/cache model; ADR 002 | Independent outputs allocate lazily; physical solve groups compute once. |
| Cache identity | C/A | chapter 14 content-addressed cache; ADR 002 | Type/version, canonical params, effective seed, context, demand group, upstream port keys. |
| Semantic side-channel debt is complete | M/A | `src/plugins/**/*.js` `nd._*` scan; ADR 002 table | Six plugin families/fields have named S2/S5 owners; UI-only state is excluded. |
| Legal Order is path validation, not registration order | C | Terrain Architect SKILL Legal Order; ADR 002 | Registration checks descriptors; graph validation checks height writes downstream of derived fields. |
| Normals error bound | D | IEEE-754 unit roundoff `u=2^-24`, conservative 32-operation forward error | Component bound is `gamma_32=(32u)/(1-32u)` against a double analytic plane. |

## Sprint 3 — cover state

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Legacy height to physical stack | M/A | current `metricHeightField`; ADR 005 | Legacy remains `heightNormalized`; explicit frame metadata maps to absolute metres. |
| Solid surface is bedrock plus explicit cover thicknesses | C/A | Terrain Architect SKILL layer stack; chapters 27 and ADR 005 | Every term is metres, finite; cover is non-negative; sand is never omitted. |
| Soil production law and ranges | C | chapter 11, Heimsath et al. 1997 | `P=P0*exp(-H/hStar)`, `P0=0.05–0.3 mm/yr`, `hStar=0.3–0.5 m`. |
| Regolith initial values | D | Geometric midpoint of positive rate range; arithmetic midpoint of length range | `P0=sqrt(0.05*0.3)`, `hStar=0.4 m`; duration is required authored data. |
| Hydraulic one-readback state representation | A/M | ADR 001 current one-readback path; ADR 002 two-texel state atlas | Five demanded channels use two RGBA texels/cell and one `readPixels`. |
| Droplet deposition does not force terminal settling | A | ADR 001 terminal policy; ADR 002 separate erosion/deposition action channels | Capacity deposition updates state; lifetime remainder stays `exportedOrSuspended`. |
| Volume reduction bound | D | Standard Float32 summation error | `gamma_(N-1)*sum(abs(term))`; no generic legacy mass tolerance is inherited. |
| Regolith resolution oracle | D | Local analytic Heimsath formula | Compare world-coincident samples to double precision within `gamma_8`. |

## Sprint 4 — hydrology

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Fill, breach, preserve and basin products | C | chapter 03 priority-flood/breaching/closed basins | Routing surface is derived; solid top remains unchanged. |
| MFD8/MFD6 physical outputs | C/M | chapters 03/26; existing flow/facet gates | Area begins at physical cell area; sinks have zero direction. |
| Sources seed discharge, not height | C | chapter 03 authored sources, discharge accumulation and kind list | Zero rain/source is exact zero; no water-family height write. |
| Rainfall unit bridge | D/A | `mm/yr`, cell area, 365-day year; ADR 005 | `q=mmYr*1e-3*area/31_536_000`, once at Flow boundary. |
| Lake surface is one spill value | C/D | chapter 03 flat-at-spill construction | Wet cells and spill feature share one Float32 value; depth identity is exact. |
| River width/depth exponents | C | chapter 03 Leopold–Maddock section | `width=kw*Q^0.5`, `depth=kd*Q^0.4`; coefficient units are explicit. |
| River power-law error | D | Double oracle plus conservative eight-operation Float32 forward error | Uses `gamma_8`, not a fitted tolerance. |
| Guide conflict recurrence | M/D | Current `hydroFixField` epsilon `relief/(resolution*160)`; plan recurrence | Half-cell sampling, monotone target recurrence, and metre conversion are explicit. |
| Gerstner displacement and analytic normals | C/A | installed Terrain Renderer chapter 12; ADR 006 | Deterministic 12 terms inside grounded 4–16 range; one shared forward/depth implementation. |
| Water dielectric optics | C/A | installed Terrain Renderer chapter 12; dielectric Fresnel/GGX; ADR 006 | `F0=0.02037`, GGX sun, Beer-Lambert, depth-valid refraction, shared exposure/ACES. |
| Shore/river/ice regimes | C/A | physical depth/flow/shore handoff; ADR 006 | Depth-faded ocean/lake waves, flow-advected rivers, causal foam, exact dry/ice suppression. |
| AAA quality evidence | M/A | supplied target image; current WebGL2 deferred/forward paths; ADR 006 | Fixed captures, canvas pixels, pass parity, temporal continuity and recorded 120-frame GPU budgets. |

## Sprint 5 — climate and snow

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Orographic march, depletion and climate resolution | C/A | chapter 13 Smith–Barstad approximation; ADR 005 | Serialized 500–1000 m cell size, initial 1000 m, participates in cache identity. |
| Fallout time initial value | C/D | chapter 13 range 500–2000 s | `1000 s` is the geometric midpoint, not a quoted paper default. |
| Moisture boundaries and budget | C/D | Chapter-13 entering-ray march; mass accounting | Open upwind/downwind; `supply+recharge=rain+outflow` under Float32 reduction bound. |
| Moisture resolution result | C/D | Chapter-13 climate-grid range and sample support | Budget invariant; lagged peak may move by at most one coarse climate cell. |
| Legacy Snow migration | M/C/A | Current `snowfall:m`; chapter 27; ADR 005 | Preserve exact behavior as preview-only Snow/1; never infer moisture/density/epoch. |
| New snowfall unit bridge | D/A | ADR 005 SWE equations | Snow/2 requires positive density ratio, `mm SWE/(degC*day)` melt factor, epoch and drivers. |
| Holding depth | M/C | Current Snow `adhesion=0.6 m`; chapter 13 names authored holding-depth family | Compatibility value is a measured look control, explicitly not a physical constant. |
| Snow transport and dry-snow attribution | C | chapter 13 and `reference-impl/snow.py` | New local snow requires moisture; transported dry-cell snow must balance a source. |

## Sprint 6 — output and export

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Request/executor/package boundary and names | A | ADR 003 | Pure request; one explicit atomic package download. |
| Scalar/vector/label/scalar-value/feature encodings | C/A | chapters 08/27; ADR 003 | Discriminated formats; EXR outside S1–S8; R32F lossless master. |
| Manifest fields and continued-state validation | C/A | chapters 08/27; `docs/export-manifest.schema.json` | JSON Schema plus semantic validator enforce physical layout/provenance. |
| Staging budget | A | ADR 003 | Required authored `maxStagingBytes`; exact worst-case preflight, no impossible default. |
| Quantization error | D | Uniform 16-bit quantizer | `R/(2*65535)` plus oracle-computed Float32 rounding interval. |
| Tile posting, global-first and shared samples | C | chapter 08 tiling/seams | Vertex stride `tileSamples-1`; exact copied shared posts; one monolithic hex conversion. |
| Aprons | C/D | chapter 08 support-radius rule | Raw zero unless requested; normals one sample; other finite nodes use descriptor radius; GLOBAL slices output. |
| Bake closure and preview firewall | C/A | chapters 08/27, BACKLOG D6, ADR 003 | Port-level predecessor closure; only `raw` products enter production profiles. |
| Legacy 8-bit path | M/A | Current `exportHeightmap`; ADR 003 | Removed when PNG16 lands; not retained as interchange. |

## Sprint 7 — geology and regimes

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Stratigraphic coordinate and bed table | C | chapter 11; `reference-impl/landforms.py::strat_coord`, `bed_erodibility` | Non-uniform bed thickness; exposed slice re-evaluates as erosion cuts down. |
| Material port semantics | C/A | chapter 11; ADR 005 | Emit positive dimensionless `strataErodibilityFactor`; Stream Power/2 applies physical `K0`. |
| Zone contacts | C/D | Chapter 11 supports faults/contacts; physical-unit doctrine | Hard zero-width or authored feather width in metres; no cell default. |
| Werner and Bagnold/Exner branches | C | chapter 05; `reference-impl/dunes.py`, `aeolian.py` | Transverse Werner base and continuum typed-wind transport remain separate modes. |
| Aeolian boundaries | C | References use periodic transport; doctrine requires explicit boundaries | Required `periodic` or `open`; open reports flux; no hidden production default. |
| Aeolian orientation bin | D | Axial orientation spans 180 degrees | 180 one-degree bins; tolerance is one declared bin. |
| Scree source and repose | C | chapter 05 scree source and 35–40 degree table | Consume explicit weathered depth, gate cliff >55°, place at base, relax at authored repose. |
| Voellmy path/reach | C | chapter 05; `reference-impl/runout.py` and test | Reach error is strictly `<2*cellSize`; speed/stop/path emitted as features. |
| Runout deposition | C | Corpus says one-path terrain realization is F-tier and supplies no lobe law | Removed from S7; no height/state write or invented exponential spreading. |

## Sprint 8 — graph machinery

| Claim | Class | Evidence | Resolution |
|---|---|---|---|
| Product scope | M | `GAEA-GAP.md` verified Route/Edge/Switch/Var/Math/MacroPort need | Exact runtime semantics come from ADR 004. |
| Variables and lexical overrides | C/A | chapter 14 stable IDs/versioned parameters; ADR 004 | UUID bindings; child override shadows ID only. |
| Edge boundary policy | A | ADR 004 | Authored threshold, initial midpoint 0.5, D8/D6 adjacency, ties inside. |
| Bounded expression grammar and units | A | ADR 004 | Closed Pratt grammar with `@{uuid}` references; explicit dimensional rules. |
| Security budgets | A | ADR 004 | 512 UTF-16 units, depth 32, 256 evaluated nodes; exact boundary tests and `<1 ms` p95 target. |
| Subgraph ownership/version/recursion | C/A | chapter 14 serialization/cycles; ADR 004 | Embedded, pinned UUID/version/full hash; DFS rejects recursion. |
| Hash and import conflict | A | ADR 004 | RFC 8785 semantic bytes, full SHA-256, exact dedupe, visible conflict, fixed hash vectors. |
| Cache identity and immutability | C/A | chapter 14 Merkle cache; ADRs 002/004 | Full definition identity, overrides, effective seed, context, demand and upstream ports. |

## Closure gate

This ledger is sealed only when:

1. every linked ADR/schema exists and diagnostics are clean;
2. an unresolved-claim scan finds no future-decision or placeholder-tolerance language in S1–S8;
3. an independent read-only rubber-duck review reports no valid blocking finding;
4. every valid advisory finding is fixed or rejected with evidence; and
5. `PROGRESS.md` is updated only after 1–4 pass.
