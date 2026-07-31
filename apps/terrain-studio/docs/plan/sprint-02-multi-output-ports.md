# Sprint 2 — Typed multi-output DAG + auxiliary-map registry `[E]` · the keystone

**Goal.** Replace the implicit one-source/one-scalar edge with a typed, multi-output, demand-driven
DAG while preserving every existing document and primary scalar result. This is the refactor that
unblocks Lake/Basin with real outputs (S4), Sediments-as-state (S3), declarative export sinks (S5),
vector fields, feature outputs, and a height `Layers` equivalent.

**Implements:** `BACKLOG W4` (auxiliary-map registry / three lenses) and the multi-output half of the
D7 **L2** gate. **Maps to** `GAEA-GAP §Part 3 #5`.

**The measured blast radius.** `definePlugin` accepts one `eval`; every edge is `{from,to,slot}` where
`slot` identifies only the destination input; the canvas draws and hits one output handle; evaluators
cache one `nd._field`; snapshots persist old edges; `evalExact`, progressive builds, thumbnails,
scene collection, quick-create, undo/redo, and the test bridge all assume that shape. This sprint
owns all of those changes. It is not a return-object tweak.

**Architecture gate:** accept the typed multi-output DAG ADR named in the roadmap before S2.1.

---

## Stories

| ID | Title | Cost | Pts | Notes |
|---|---|---|---|---|
| S2.1 | Typed port descriptors + result contract | `[E]` | 5 | scalar/vector raster, scalar, feature set; units/ranges; primary-output adapter |
| S2.2 | Source-port edges, graph UI, and saved-document migration | `[E]` | 8 | edge schema, handles, hit-testing, undo/redo, quick-create, versioned load |
| S2.3 | Demand-driven evaluation + per-output cache | `[E]` | 8 | `_outputs`, primary `_field` compatibility, lazy aux allocation, progressive/exact paths |
| S2.4 | Auxiliary-map registry with three lenses | `[E]` | 5 | derived / state / continued; declaration backfill and explicit debt ledger |
| S2.5 | Staged doctrine validators | `[C]` | 3 | enforce typed/lens rules now; co-evolution in S3; Snow Rule in L4 |
| S2.6 | Two-cut pilot + Normals vector derive | `[C]` | 5 | adapt oracle first, then migrate existing aux; prove vector/multi-output in production |

---

### S2.1 — Typed port descriptors + result contract · `[E]` · 5 pts
**User story:** As a node author, I declare what each edge carries, in what unit and range, and the
runtime rejects incompatible connections before evaluation.

Add descriptor arrays `inputs[]` and `outputs[]`. Each port has a stable `id`, display `name`, value
kind (`scalarRaster`, `vectorRaster`, `labelRaster`, `scalar`, `featureSet`), semantic field type
(`height`, `mask`, `normal`, `velocity`, `color`, ...), unit, component/storage format (`R32F`,
`RG32F`, `RGB32F`, integer labels), range contract, and required/default policy. One output is marked
`primary`. Existing `ins:[name]` and bare `Float32Array` results adapt to scalar-raster primary ports
without changing bytes. Typed nodes return `{values: Map<portId, value>}` or the ADR's equivalent;
do not use dotted property names as the public contract.

`labelRaster` is categorical: it carries no physical unit (`unit: none`), uses an integer storage
format, declares a finite label domain plus a reserved `noLabel` sentinel, and may not pass through
continuous interpolation/tonemap nodes. Its lifecycle lens is still declared normally (basin IDs are
derived from routing geometry).

Descriptors may declare an **atomic output group** when one physical solve necessarily produces
several values (for example Hydraulic height + sediment + velocity). Demanding one group member may
compute the group once; unrelated optional outputs remain lazy. This distinction is part of cache
and memory accounting, not an implementation accident.

**Acceptance gate** — `tests/legacy/_verify_port_contract.js`: incompatible semantic/value kinds
must fail at connection time with source and destination port names; missing required outputs,
duplicate IDs, invalid units, and range violations fail registration/evaluation. Adapted legacy
nodes remain bit-identical for **every pre-existing type at the measured sprint-start count**, with
zero digest skips. An illegal height→feature fixture is the armed negative control.

---

### S2.2 — Source-port edges, UI, and persistence migration · `[E]` · 8 pts
**User story:** As a graph author, I can see, connect, save, reload, undo, copy, and quick-create from
any named output without losing which value the wire carries.

Change edges to `{from, fromPort, to, toPort}` with stable port IDs. Migrate old `{from,to,slot}`
edges to the source's primary output and the destination input at that legacy index. Update edge keys,
cycle checks, dirty propagation, layout, drawing/hit-testing, rewiring, delete/auto-bridge,
quick-create compatibility, copy/paste, undo/redo, graph snapshots, and test bridge. Add a saved-
document schema version; migration is idempotent and unknown port IDs fail visibly.

**Acceptance gate** — `tests/legacy/_verify_port_migration.js`: load a frozen pre-Sprint-2 document,
migrate, save, reload, and assert topology, primary outputs, params, and final field are unchanged.
Connect two outputs from one node to two consumers and assert the source port survives undo/redo,
copy/paste, and reload. A fixture with `fromPort` discarded must fail. Run `_verify_workflow.js`,
`_verify_quick_create.js`, `_verify_edges.js`, `_verify_digest.js`, bridge check, and built-bundle
digest.

---

### S2.3 — Demand-driven evaluation + per-output cache · `[E]` · 8 pts
**User story:** As a graph author, an unused auxiliary output consumes no field-sized storage or
compute, while selected outputs remain deterministic and invalidate correctly.

Cache typed values under `nd._outputs` (or evaluator-owned cache); retain `nd._field` only as a
temporary compatibility alias to the primary scalar raster. Update recursive, progressive, and
exact evaluators, metadata propagation, thumbnails, scene collection, previews, and errors. Demand
propagates from connected ports, selected previews, output sinks, and explicitly requested
thumbnails. Adding an unconnected output must not dirty or allocate it. Content keys include node,
params, context, upstream **port** keys, output ID, and schema/substrate version.
Evaluation receives the demanded output ID/group so independent outputs can stay lazy; atomic groups
are cached and released as a unit under the declared policy.

Legacy evaluators that currently mutate `nd._wind`, `_temperatureC`, `_snowLayer`, preview masks, or
similar fields run through an isolated compatibility state bag whose declared products are extracted
into cache values. The debt ledger names every extractor and owner sprint; no new plugin may receive
the mutable node instance as semantic storage.

**Acceptance gate** — `tests/legacy/_verify_multiout.js`: a two-output fixture records which output
computes; request one and assert the other has no value/buffer/allocation, then request both and
assert each computes once. A second fixture declares two outputs atomic; requesting either computes
the group once and never recomputes for its sibling. Editing one upstream source invalidates exactly
the dependent output cones. An independent fixture that eagerly allocates both outputs must fail.
Existing primary-output digests remain bit-identical and skipped count is zero.

---

### S2.4 — Auxiliary-map registry, three lenses · `[E]` · 5 pts
**Implements:** `BACKLOG W4`, `BACKLOG §2`.

**User story:** As a node/engine integrator, every auxiliary product has one discoverable lifecycle,
unit, precision, driver set, and export meaning.

Register every aux map under exactly one lens, because the lens *is* the export contract:

| Lens | Lifecycle | Export means | Examples |
|---|---|---|---|
| Derived | recompute from final geometry | a finished answer | slope, curvature, ao, **aspect**, insolation, TWI |
| State | carried, co-updated in-pass | a finished accounting | soilDepth, sedimentDepth, sandDepth, strataHardness |
| Continued | evolves in time | initial condition + drivers + epoch | snowDepth, waterSurface/Depth, flowVelocity, ice |

Categorical products use the same lifecycle lenses: `basinId` is **derived** and encoded as a
`labelRaster`, while basin/spill locations use `featureSet`.

Two traps the registry must encode (both were caught by review, not reading, `BACKLOG §2`):
`insolation` is **derived** not state (pure function of final geometry + sun arc); `wetness` is
**split** not averaged (state saturation vs derived TWI stay separate fields).

Backfill declarations for every current side-channel field. Legacy exemptions are explicit records
`{node, rule, ownerSprint}`; new exemptions are forbidden and the count may only decrease.

**Acceptance gate** — `tests/legacy/_verify_auxregistry.js`:
- Assert every registered map declares a lens; a map with no lens is a registration error (negative
  control: a fixture map with the lens field removed must fail the run, proving the check bites).
- Assert `insolation.lens === 'derived'` and that a single `wetness` field cannot satisfy both the
  state and derived requirements (declaring one leaves the other unregistered → fail).
- Assert a continued-state declaration without an epoch **contract** and driver list fails
  registration. Runtime epoch values are validated when a continued-state value is emitted.
- Assert the exemption ledger contains only named existing debts and no unowned entry.

---

### S2.5 — Staged doctrine validators · `[C]` · 3 pts
**Implements:** the enforcement opportunities in `BACKLOG §2`.

**User story:** As a maintainer, illegal field lifecycles and graph order fail at the earliest point
where real production nodes can satisfy the rule.

Turn doctrines into executable validation in the sprint where real nodes can satisfy them:
- **Now:** typed compatibility, output/lens completeness, and Legal Order. A derived node upstream of
  any height write is a **graph validation** error, not a plugin registration error.
- **Sprint 3:** arm co-evolution for real material-moving nodes when their state outputs land. Until
  then only the enumerated existing nodes may carry an owned exemption; new nodes cannot.
- **L4 climate sprint:** arm the Snow Rule when `moisture` exists and Snow declares/uses it. Do not
  reject the shipping Snow node before its prerequisite exists.

**Acceptance gate** — `tests/legacy/_verify_doctrine_reg.js`: illegal typed/lens declarations fail
registration; an illegal graph ordering fails graph validation; every temporary exemption is listed
and owned. Separate Sprint 3/L4 gates must demonstrate the exemption removal and reject an illegal
real-equivalent fixture. A fixture-only rule that no production declaration invokes is not accepted.

---

### S2.6 — Two-cut pilot + Normals · `[C]` · 5 pts
**User story:** As a graph author, I can connect physical wind/solar outputs and a normal vector
through typed ports rather than hidden properties on a scalar field.

Use two reviewable cuts so the oracle never moves with existing behavior:
1. Add a port-aware digest adapter that reads the old side-channel representation, prove current
  expected bytes are unchanged, and commit it alone.
2. Migrate `d_sunshadow` and `d_wind` to typed outputs in separate implementation commits. Keep a
  temporary read-only metadata compatibility adapter for existing scene consumers, then remove it
  when those consumers use ports.

Add `Normals` as a new vector-raster derive. Its port carries three components, metres-per-cell
context, and unit-vector range validation; the thumbnail is an explicit visualization adapter, not
the graph value.

**Acceptance gate:** expected digests for the migrated existing nodes remain unchanged and zero types
are skipped. Wire Wind's vector output to a scalar input and assert the editor rejects it. On analytic
planes, Normals are finite, unit length within 1e-4, and have the analytic z component within 1e-4 on
square and hex. Removing a component or swapping source ports is the armed failing fixture.

---

## Sprint 2 exit gate

- Typed port, migration, multi-output, registry, doctrine, wind/solar, and Normals gates green, each
  with a demonstrated failing fixture.
- `npm run verify -- _verify_digest.js` and the built-bundle digest are bit-identical for every
  pre-existing type at the measured count; **skipped = 0**.
- `npm run plugins:check`, `npm run bridge:check`, production build, workflow/quick-create/edge
  oracles, and the full standalone sweep are green.
- The typed multi-output ADR reflects the implementation; old saved documents have a frozen migration
  fixture.
- **This is the gate for D7 L2** — the cover layer (Sprint 3) may not start until it is met.
